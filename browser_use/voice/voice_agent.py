"""
Voice-controlled browser agent.

This module provides the main VoiceAgent class that integrates
speech recognition, command parsing, voice feedback, and interrupt handling
with the browser-use Agent for voice-controlled browser automation.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from browser_use.agent.service import Agent
from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext
from browser_use.controller.service import Controller
from browser_use.voice.command_parser import CommandParser, CommandType, VoiceCommand
from browser_use.voice.interrupt_handler import (
	InterruptHandler,
	InterruptHandlerConfig,
	InterruptibleExecution,
	InterruptState,
)
from browser_use.voice.speech_recognition import (
	RecognitionState,
	SpeechRecognizer,
	SpeechRecognizerConfig,
)
from browser_use.voice.voice_feedback import FeedbackType, VoiceFeedback, VoiceFeedbackConfig

logger = logging.getLogger(__name__)


@dataclass
class VoiceAgentConfig:
	"""Configuration for the voice-controlled browser agent."""

	# Wake word settings
	wake_words: List[str] = field(default_factory=lambda: ['hey suno mirza', 'hey browser', 'hey assistant'])
	wake_word_sensitivity: float = 0.7

	# Voice settings
	language: str = 'en-US'
	speech_timeout: float = 5.0
	phrase_time_limit: float = 15.0

	# Feedback settings
	enable_voice_feedback: bool = True
	voice_feedback_rate: int = 175
	voice_feedback_volume: float = 1.0

	# Agent settings
	max_steps_per_command: int = 50
	use_vision: bool = True
	require_confirmation_for_destructive: bool = True

	# Continuous mode
	continuous_mode: bool = True  # Keep listening after each command
	auto_start_listening: bool = True

	# Callbacks
	on_command_start: Optional[Callable[[str], None]] = None
	on_command_complete: Optional[Callable[[str, bool], None]] = None
	on_listening_state_change: Optional[Callable[[bool], None]] = None


class VoiceAgent:
	"""
	Voice-controlled browser agent.

	This class provides a complete voice-controlled browsing experience:
	- Continuous speech recognition with wake word detection
	- Natural language command parsing
	- Voice feedback for actions and results
	- Interrupt handling for user control
	- Integration with browser-use Agent for browser automation
	"""

	def __init__(
		self,
		llm: BaseChatModel,
		config: Optional[VoiceAgentConfig] = None,
		browser: Optional[Browser] = None,
		browser_context: Optional[BrowserContext] = None,
		controller: Optional[Controller] = None,
	):
		"""
		Initialize the voice agent.

		Args:
			llm: The language model for the browser agent.
			config: Voice agent configuration.
			browser: Optional browser instance.
			browser_context: Optional browser context.
			controller: Optional controller instance.
		"""
		self.config = config or VoiceAgentConfig()
		self.llm = llm
		self.browser = browser
		self.browser_context = browser_context
		self.controller = controller or Controller()

		self._running = False
		self._current_agent: Optional[Agent] = None
		self._command_history: List[Dict[str, Any]] = []
		self._last_command: Optional[VoiceCommand] = None
		self._awaiting_confirmation = False

		# Initialize components
		self._init_components()

	def _init_components(self) -> None:
		"""Initialize all voice control components."""

		# Speech recognizer
		speech_config = SpeechRecognizerConfig(
			wake_words=self.config.wake_words,
			wake_word_sensitivity=self.config.wake_word_sensitivity,
			language=self.config.language,
			timeout=self.config.speech_timeout,
			phrase_time_limit=self.config.phrase_time_limit,
			on_wake_word_detected=self._on_wake_word_detected,
			on_command_recognized=self._on_command_recognized,
			on_state_change=self._on_recognition_state_change,
			on_error=self._on_recognition_error,
		)
		self.speech_recognizer = SpeechRecognizer(speech_config)

		# Command parser
		self.command_parser = CommandParser()

		# Voice feedback
		feedback_config = VoiceFeedbackConfig(
			enabled=self.config.enable_voice_feedback,
			rate=self.config.voice_feedback_rate,
			volume=self.config.voice_feedback_volume,
		)
		self.voice_feedback = VoiceFeedback(feedback_config)

		# Interrupt handler
		interrupt_config = InterruptHandlerConfig(
			on_interrupt=self._on_interrupt,
			on_resume=self._on_resume,
			on_state_change=self._on_interrupt_state_change,
			on_command_cancelled=self._on_command_cancelled,
		)
		self.interrupt_handler = InterruptHandler(interrupt_config)

		logger.info('🎤 Voice agent components initialized')

	def _on_wake_word_detected(self) -> None:
		"""Handle wake word detection."""
		logger.info('🎤 Wake word detected!')
		self.voice_feedback.speak('Yes?', FeedbackType.ACKNOWLEDGMENT)

		if self.config.on_listening_state_change:
			self.config.on_listening_state_change(True)

	def _on_command_recognized(self, text: str) -> None:
		"""Handle recognized command."""
		logger.info(f'🎤 Command received: "{text}"')

		# Check for interrupts first
		if self.interrupt_handler.check_and_handle_interrupt(text):
			self.voice_feedback.speak('Stopped', FeedbackType.ACKNOWLEDGMENT)
			return

		# Check for confirmation response
		if self._awaiting_confirmation:
			self._handle_confirmation_response(text)
			return

		# Parse and handle the command
		asyncio.create_task(self._process_command(text))

	def _on_recognition_state_change(self, state: RecognitionState) -> None:
		"""Handle recognition state changes."""
		logger.debug(f'🎤 Recognition state: {state.value}')

		if state == RecognitionState.LISTENING_FOR_COMMAND:
			logger.info('🎤 Listening for your command...')

	def _on_recognition_error(self, error: str) -> None:
		"""Handle recognition errors."""
		logger.error(f'🎤 Recognition error: {error}')
		self.voice_feedback.speak_error('Sorry, I had trouble hearing that.')

	def _on_interrupt(self) -> None:
		"""Handle user interrupts."""
		logger.info('🛑 Interrupt detected')

		# Stop voice feedback
		self.voice_feedback.interrupt()

		# Stop current agent if running
		if self._current_agent:
			self._current_agent.stop()

	def _on_resume(self) -> None:
		"""Handle resume after interrupt."""
		logger.info('▶️ Resuming voice control')
		self.voice_feedback.speak('Ready for next command', FeedbackType.STATUS)

	def _on_interrupt_state_change(self, state: InterruptState) -> None:
		"""Handle interrupt state changes."""
		logger.debug(f'🛑 Interrupt state: {state.value}')

	def _on_command_cancelled(self, command: str) -> None:
		"""Handle cancelled command."""
		logger.info(f'❌ Command cancelled: {command}')

	def _handle_confirmation_response(self, text: str) -> None:
		"""Handle response to confirmation request."""
		text_lower = text.lower().strip()

		confirmed = any(word in text_lower for word in ['yes', 'confirm', 'okay', 'ok', 'do it', 'proceed'])
		cancelled = any(word in text_lower for word in ['no', 'cancel', 'abort', 'never mind'])

		if confirmed and self._last_command:
			self._awaiting_confirmation = False
			self.voice_feedback.acknowledge('ok')
			asyncio.create_task(self._execute_command(self._last_command))
		elif cancelled:
			self._awaiting_confirmation = False
			self._last_command = None
			self.voice_feedback.speak('Cancelled', FeedbackType.ACKNOWLEDGMENT)
		else:
			self.voice_feedback.speak('Please say yes to confirm or cancel to abort', FeedbackType.CONFIRMATION_REQUEST)

	async def _process_command(self, text: str) -> None:
		"""Process a recognized command."""
		# Parse the command
		commands = self.command_parser.parse_chained(text)

		if not commands:
			self.voice_feedback.speak("Sorry, I didn't understand that command", FeedbackType.ERROR)
			return

		# Process each command
		for command in commands:
			if command.command_type == CommandType.HELP:
				self._show_help()
				continue

			if command.command_type == CommandType.REPEAT:
				await self._repeat_last_command()
				continue

			# Check if confirmation is needed
			if command.requires_confirmation and self.config.require_confirmation_for_destructive:
				self._last_command = command
				self._awaiting_confirmation = True
				action_desc = self._get_command_description(command)
				self.voice_feedback.ask_confirmation(action_desc)
				return

			# Execute the command
			await self._execute_command(command)

	async def _execute_command(self, command: VoiceCommand) -> None:
		"""Execute a parsed voice command."""
		logger.info(f'🚀 Executing command: {command.command_type.value}')

		# Notify start
		if self.config.on_command_start:
			self.config.on_command_start(command.raw_text)

		self.voice_feedback.acknowledge('working')

		success = False
		result_message = ''

		try:
			async with InterruptibleExecution(self.interrupt_handler, command.raw_text):
				# Handle special commands
				if command.command_type in (CommandType.STOP, CommandType.CANCEL):
					self.interrupt_handler.trigger_interrupt()
					success = True
					result_message = 'Stopped'

				elif command.command_type == CommandType.HELP:
					self._show_help()
					success = True
					result_message = 'Help shown'

				else:
					# Execute via browser-use Agent
					success, result_message = await self._execute_with_agent(command)

		except asyncio.CancelledError:
			logger.info('🛑 Command execution cancelled')
			result_message = 'Command cancelled'

		except Exception as e:
			logger.error(f'❌ Command execution error: {e}')
			result_message = f'Error: {str(e)}'
			self.voice_feedback.speak_error(str(e))

		# Record command history
		self._command_history.append(
			{
				'command': command.raw_text,
				'type': command.command_type.value,
				'success': success,
				'result': result_message,
			}
		)
		self._last_command = command

		# Notify completion
		if self.config.on_command_complete:
			self.config.on_command_complete(command.raw_text, success)

		if success:
			self.voice_feedback.acknowledge('done')
		else:
			self.voice_feedback.speak_status(result_message)

	async def _execute_with_agent(self, command: VoiceCommand) -> tuple[bool, str]:
		"""Execute a command using the browser-use Agent."""

		# Format the command as a task for the Agent
		task = self.command_parser.format_command_for_agent(command)
		logger.info(f'📋 Agent task: {task}')

		try:
			# Create agent for this command
			self._current_agent = Agent(
				task=task,
				llm=self.llm,
				browser=self.browser,
				browser_context=self.browser_context,
				controller=self.controller,
				use_vision=self.config.use_vision,
			)

			# Run the agent
			history = await self._current_agent.run(max_steps=self.config.max_steps_per_command)

			# Extract result
			success = history.is_successful()
			final_result = history.final_result() if hasattr(history, 'final_result') else ''

			if success:
				return True, final_result or 'Task completed'
			else:
				errors = history.errors()
				return False, errors[0] if errors else 'Task not completed'

		except Exception as e:
			logger.error(f'Agent execution error: {e}')
			return False, str(e)

		finally:
			# Keep browser open for next command
			if self._current_agent and hasattr(self._current_agent, 'browser'):
				self.browser = self._current_agent.browser
				self.browser_context = self._current_agent.browser_context

			self._current_agent = None

	def _get_command_description(self, command: VoiceCommand) -> str:
		"""Get human-readable description of a command."""
		if command.command_type == CommandType.CLOSE_TAB:
			return 'close this tab'
		elif command.command_type == CommandType.SEND_EMAIL:
			return 'send this email'
		else:
			return command.raw_text

	def _show_help(self) -> None:
		"""Show help information."""
		help_text = self.command_parser.get_help_text()
		logger.info(help_text)
		self.voice_feedback.speak_help(help_text)

	async def _repeat_last_command(self) -> None:
		"""Repeat the last executed command."""
		if self._last_command:
			self.voice_feedback.speak(f'Repeating: {self._last_command.raw_text}', FeedbackType.STATUS)
			await self._execute_command(self._last_command)
		else:
			self.voice_feedback.speak('No previous command to repeat', FeedbackType.STATUS)

	async def start(self) -> None:
		"""Start the voice agent."""
		if self._running:
			logger.warning('Voice agent already running')
			return

		logger.info('🎤 Starting voice-controlled browser agent...')
		self._running = True

		# Start components
		await self.voice_feedback.start()
		await self.speech_recognizer.start()

		# Initial feedback
		wake_words_str = ' or '.join(self.config.wake_words)
		self.voice_feedback.speak(f'Voice browser ready. Say {wake_words_str} to activate.', FeedbackType.STATUS)

		logger.info(f'🎤 Voice agent started. Wake words: {self.config.wake_words}')

		# If auto-start listening is enabled, skip wake word initially
		if self.config.auto_start_listening:
			self.speech_recognizer.skip_to_command_mode()
			self.voice_feedback.speak('Listening for commands.', FeedbackType.STATUS)

	async def stop(self) -> None:
		"""Stop the voice agent."""
		if not self._running:
			return

		logger.info('🎤 Stopping voice agent...')
		self._running = False

		# Stop current agent if running
		if self._current_agent:
			self._current_agent.stop()

		# Stop components
		await self.speech_recognizer.stop()
		await self.voice_feedback.stop()

		# Clean up browser
		if self.browser and not self.browser_context:
			await self.browser.close()

		logger.info('🎤 Voice agent stopped')

	async def run(self) -> None:
		"""Run the voice agent in continuous mode."""
		await self.start()

		try:
			# Keep running until stopped
			while self._running:
				await asyncio.sleep(0.1)

				# Check for pending commands in queue
				next_command = self.interrupt_handler.get_next_command()
				if next_command:
					await self._process_command(next_command)

		except KeyboardInterrupt:
			logger.info('🎤 Keyboard interrupt received')

		finally:
			await self.stop()

	async def execute_single_command(self, text: str) -> Dict[str, Any]:
		"""
		Execute a single voice command (for testing or programmatic use).

		Args:
			text: The command text.

		Returns:
			Result dictionary with success status and message.
		"""
		command = self.command_parser.parse(text)
		await self._execute_command(command)

		if self._command_history:
			return self._command_history[-1]
		return {'success': False, 'result': 'No result'}

	def get_command_history(self) -> List[Dict[str, Any]]:
		"""Get the command history."""
		return self._command_history.copy()

	def is_running(self) -> bool:
		"""Check if the voice agent is running."""
		return self._running

	def get_listening_state(self) -> RecognitionState:
		"""Get the current speech recognition state."""
		return self.speech_recognizer.get_state()

	def skip_wake_word(self) -> None:
		"""Skip wake word detection and listen for command immediately."""
		self.speech_recognizer.skip_to_command_mode()

	def get_available_commands(self) -> str:
		"""Get a description of available commands."""
		return self.command_parser.get_help_text()
