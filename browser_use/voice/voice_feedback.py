"""
Voice feedback module for voice-controlled browser.

This module provides text-to-speech capabilities for giving
audio feedback to users during voice-controlled browsing.
"""

import logging
import queue
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
	"""Types of voice feedback."""

	ACKNOWLEDGMENT = 'acknowledgment'  # Short confirmations
	STATUS = 'status'  # Status updates
	RESULT = 'result'  # Action results
	ERROR = 'error'  # Error messages
	CONFIRMATION_REQUEST = 'confirmation_request'  # Asking for confirmation
	HELP = 'help'  # Help messages


@dataclass
class VoiceFeedbackConfig:
	"""Configuration for voice feedback."""

	enabled: bool = True
	rate: int = 175  # Words per minute
	volume: float = 1.0  # 0.0 to 1.0
	voice_id: Optional[str] = None  # Use system default if None

	# Feedback preferences
	enable_acknowledgments: bool = True
	enable_status_updates: bool = True
	enable_results: bool = True
	enable_errors: bool = True

	# Customization
	acknowledgment_sound: bool = True  # Play a sound for quick acknowledgments
	max_result_length: int = 500  # Max characters to speak for results
	truncation_suffix: str = '... and more.'  # Suffix for truncated results

	# Callbacks
	on_speaking_start: Optional[Callable[[str], None]] = None
	on_speaking_end: Optional[Callable[[], None]] = None
	on_interrupted: Optional[Callable[[], None]] = None


class VoiceFeedback:
	"""
	Provides text-to-speech feedback for voice-controlled browsing.

	Features:
	- Asynchronous speech synthesis
	- Interruptible speech
	- Different feedback types with appropriate handling
	- Speech queue management
	"""

	# Predefined responses
	ACKNOWLEDGMENTS = {
		'understood': 'Got it',
		'working': 'Working on it',
		'done': 'Done',
		'ok': 'Okay',
		'yes': 'Yes',
		'no': 'No',
		'cancelled': 'Cancelled',
		'stopped': 'Stopped',
	}

	def __init__(self, config: Optional[VoiceFeedbackConfig] = None):
		"""
		Initialize the voice feedback system.

		Args:
			config: Configuration for voice feedback. Uses defaults if not provided.
		"""
		self.config = config or VoiceFeedbackConfig()
		self._engine = None
		self._speaking = False
		self._speech_queue: queue.Queue = queue.Queue()
		self._current_utterance: Optional[str] = None
		self._stop_speaking = False
		self._speech_thread: Optional[threading.Thread] = None
		self._running = False

		self._init_engine()

	def _init_engine(self) -> None:
		"""Initialize the text-to-speech engine."""
		if not self.config.enabled:
			logger.info('🔊 Voice feedback disabled')
			return

		try:
			import pyttsx3

			self._engine = pyttsx3.init()

			# Configure engine
			self._engine.setProperty('rate', self.config.rate)
			self._engine.setProperty('volume', self.config.volume)

			# Set voice if specified
			if self.config.voice_id:
				self._engine.setProperty('voice', self.config.voice_id)

			logger.info('🔊 Voice feedback engine initialized')

		except ImportError:
			logger.warning('🔊 pyttsx3 not installed. Voice feedback will be disabled. Install with: pip install pyttsx3')
			self.config.enabled = False
		except Exception as e:
			logger.error(f'🔊 Failed to initialize TTS engine: {e}')
			self.config.enabled = False

	def _speech_worker(self) -> None:
		"""Worker thread for processing speech queue."""
		while self._running:
			try:
				# Get next item from queue with timeout
				try:
					text, feedback_type = self._speech_queue.get(timeout=0.5)
				except queue.Empty:
					continue

				if self._stop_speaking:
					self._speech_queue.task_done()
					continue

				self._speaking = True
				self._current_utterance = text

				if self.config.on_speaking_start:
					self.config.on_speaking_start(text)

				try:
					self._engine.say(text)
					self._engine.runAndWait()
				except Exception as e:
					logger.error(f'🔊 Speech error: {e}')

				self._speaking = False
				self._current_utterance = None

				if self.config.on_speaking_end:
					self.config.on_speaking_end()

				self._speech_queue.task_done()

			except Exception as e:
				logger.error(f'🔊 Speech worker error: {e}')

	async def start(self) -> None:
		"""Start the voice feedback system."""
		if not self.config.enabled or self._running:
			return

		self._running = True
		self._stop_speaking = False
		self._speech_thread = threading.Thread(target=self._speech_worker, daemon=True)
		self._speech_thread.start()
		logger.info('🔊 Voice feedback system started')

	async def stop(self) -> None:
		"""Stop the voice feedback system."""
		self._running = False
		self._stop_speaking = True

		if self._engine:
			try:
				self._engine.stop()
			except Exception:
				pass

		if self._speech_thread and self._speech_thread.is_alive():
			self._speech_thread.join(timeout=2.0)

		logger.info('🔊 Voice feedback system stopped')

	def speak(self, text: str, feedback_type: FeedbackType = FeedbackType.STATUS) -> None:
		"""
		Queue text to be spoken.

		Args:
			text: The text to speak.
			feedback_type: The type of feedback.
		"""
		if not self.config.enabled:
			logger.debug(f'🔊 [Disabled] Would say: {text}')
			return

		# Check if this type of feedback is enabled
		if feedback_type == FeedbackType.ACKNOWLEDGMENT and not self.config.enable_acknowledgments:
			return
		if feedback_type == FeedbackType.STATUS and not self.config.enable_status_updates:
			return
		if feedback_type == FeedbackType.RESULT and not self.config.enable_results:
			return
		if feedback_type == FeedbackType.ERROR and not self.config.enable_errors:
			return

		# Truncate long results
		if feedback_type == FeedbackType.RESULT and len(text) > self.config.max_result_length:
			text = text[: self.config.max_result_length] + self.config.truncation_suffix

		logger.debug(f'🔊 Queuing: {text}')
		self._speech_queue.put((text, feedback_type))

	def acknowledge(self, key: str = 'understood') -> None:
		"""
		Speak a quick acknowledgment.

		Args:
			key: The acknowledgment key (e.g., 'understood', 'working', 'done').
		"""
		text = self.ACKNOWLEDGMENTS.get(key, self.ACKNOWLEDGMENTS['understood'])
		self.speak(text, FeedbackType.ACKNOWLEDGMENT)

	def speak_error(self, error_message: str) -> None:
		"""
		Speak an error message.

		Args:
			error_message: The error to speak.
		"""
		self.speak(f'Error: {error_message}', FeedbackType.ERROR)

	def speak_status(self, status: str) -> None:
		"""
		Speak a status update.

		Args:
			status: The status message.
		"""
		self.speak(status, FeedbackType.STATUS)

	def speak_result(self, result: str) -> None:
		"""
		Speak an action result.

		Args:
			result: The result to speak.
		"""
		self.speak(result, FeedbackType.RESULT)

	def ask_confirmation(self, action: str) -> None:
		"""
		Ask for confirmation before a destructive action.

		Args:
			action: Description of the action to confirm.
		"""
		self.speak(
			f'Are you sure you want to {action}? Say yes to confirm or cancel to abort.', FeedbackType.CONFIRMATION_REQUEST
		)

	def speak_help(self, help_text: str) -> None:
		"""
		Speak help information.

		Args:
			help_text: The help text to speak.
		"""
		# Summarize help for speech
		summary = (
			'You can say commands like: go to a website, search for something, '
			'scroll up or down, click on elements, open or close tabs, '
			'compose or reply to emails. Say help at any time for more information.'
		)
		self.speak(summary, FeedbackType.HELP)

	def interrupt(self) -> None:
		"""Interrupt current speech immediately."""
		if not self._speaking:
			return

		logger.debug('🔊 Interrupting speech')
		self._stop_speaking = True

		# Clear the queue
		while not self._speech_queue.empty():
			try:
				self._speech_queue.get_nowait()
				self._speech_queue.task_done()
			except queue.Empty:
				break

		# Stop current speech
		if self._engine:
			try:
				self._engine.stop()
			except Exception:
				pass

		self._speaking = False
		self._current_utterance = None
		self._stop_speaking = False

		if self.config.on_interrupted:
			self.config.on_interrupted()

	def is_speaking(self) -> bool:
		"""Check if currently speaking."""
		return self._speaking

	def get_current_utterance(self) -> Optional[str]:
		"""Get the currently spoken text."""
		return self._current_utterance

	def clear_queue(self) -> None:
		"""Clear all pending speech."""
		while not self._speech_queue.empty():
			try:
				self._speech_queue.get_nowait()
				self._speech_queue.task_done()
			except queue.Empty:
				break

	def get_available_voices(self) -> list:
		"""Get list of available voices."""
		if not self._engine:
			return []

		try:
			voices = self._engine.getProperty('voices')
			return [{'id': v.id, 'name': v.name, 'languages': v.languages} for v in voices]
		except Exception as e:
			logger.error(f'Error getting voices: {e}')
			return []

	def set_voice(self, voice_id: str) -> bool:
		"""
		Set the voice for speech synthesis.

		Args:
			voice_id: The ID of the voice to use.

		Returns:
			True if successful, False otherwise.
		"""
		if not self._engine:
			return False

		try:
			self._engine.setProperty('voice', voice_id)
			self.config.voice_id = voice_id
			return True
		except Exception as e:
			logger.error(f'Error setting voice: {e}')
			return False

	def set_rate(self, rate: int) -> None:
		"""Set speech rate in words per minute."""
		if self._engine:
			self._engine.setProperty('rate', rate)
			self.config.rate = rate

	def set_volume(self, volume: float) -> None:
		"""Set speech volume (0.0 to 1.0)."""
		if self._engine:
			volume = max(0.0, min(1.0, volume))
			self._engine.setProperty('volume', volume)
			self.config.volume = volume
