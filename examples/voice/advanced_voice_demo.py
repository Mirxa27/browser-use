"""
Advanced voice-controlled browser demo.

This example demonstrates advanced voice control features including:
- Visual status indicators
- Custom callbacks
- Multi-step workflows
- Command history

Requirements:
    - pip install browser-use[voice]
    - A working microphone
    - Set up your LLM API key in .env file

Usage:
    python examples/voice/advanced_voice_demo.py
"""

import asyncio
import os
import sys

# Add parent directory to path for local development
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from browser_use.voice import (
	StatusType,
	VisualStatusConfig,
	VisualStatusIndicator,
	VoiceAgent,
	VoiceAgentConfig,
)

load_dotenv()


class VoiceBrowserApp:
	"""Advanced voice-controlled browser application."""

	def __init__(self):
		"""Initialize the application."""
		self.voice_agent = None
		self.status_indicator = None
		self.command_count = 0
		self.success_count = 0
		self.error_count = 0

	def setup_status_indicator(self) -> VisualStatusIndicator:
		"""Set up the visual status indicator."""
		config = VisualStatusConfig(
			show_in_terminal=True,
			use_colors=True,
			show_timestamps=True,
			on_status_change=self.on_status_change,
		)
		return VisualStatusIndicator(config)

	def on_status_change(self, event):
		"""Handle status change events."""
		# Track statistics
		if event.status_type == StatusType.SUCCESS:
			self.success_count += 1
		elif event.status_type == StatusType.ERROR:
			self.error_count += 1

	def on_command_start(self, command: str):
		"""Handle command start."""
		self.command_count += 1
		if self.status_indicator:
			self.status_indicator.set_executing(command)

	def on_command_complete(self, command: str, success: bool):
		"""Handle command completion."""
		if self.status_indicator:
			if success:
				self.status_indicator.set_success(f'Completed: {command[:30]}...')
			else:
				self.status_indicator.set_error(f'Failed: {command[:30]}...')

	def on_listening_change(self, is_listening: bool):
		"""Handle listening state changes."""
		if self.status_indicator:
			if is_listening:
				self.status_indicator.set_listening()
			else:
				self.status_indicator.set_idle()

	def print_banner(self):
		"""Print welcome banner."""
		banner = """
╔════════════════════════════════════════════════════════════════════════╗
║            🎤 Advanced Voice-Controlled Browser 🌐                     ║
╠════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  🆕 NEW FEATURES:                                                      ║
║    📸 "Take screenshot" - Capture the page                            ║
║    📄 "Save as PDF" - Export to PDF                                   ║
║    📖 "Read page" - Summarize content                                 ║
║    🔍 "Zoom in/out" - Adjust zoom level                               ║
║    🐦 "Post tweet" - Social media integration                         ║
║    🛒 "Add to cart" / "Checkout" - Shopping support                   ║
║                                                                        ║
║  💬 NATURAL LANGUAGE:                                                  ║
║    "Find hotels in Paris and book the cheapest one"                   ║
║    "Read my emails and reply to the first one"                        ║
║    "Search for Python tutorials and scroll down"                      ║
║                                                                        ║
║  ⚡ QUICK TIPS:                                                        ║
║    - Chain commands: "Go to twitter and post a tweet"                 ║
║    - Use natural phrases: "What's the weather today?"                 ║
║    - Say "help" for all commands                                      ║
║                                                                        ║
╚════════════════════════════════════════════════════════════════════════╝
"""
		print(banner)

	def print_statistics(self):
		"""Print usage statistics."""
		print('\n' + '=' * 50)
		print('📊 Session Statistics')
		print('=' * 50)
		print(f'  Total commands: {self.command_count}')
		print(f'  ✅ Successful: {self.success_count}')
		print(f'  ❌ Failed: {self.error_count}')
		if self.command_count > 0:
			success_rate = (self.success_count / self.command_count) * 100
			print(f'  📈 Success rate: {success_rate:.1f}%')
		print('=' * 50 + '\n')

	async def run(self):
		"""Run the voice browser application."""
		self.print_banner()

		# Check for API key
		if not os.environ.get('OPENAI_API_KEY'):
			print('❌ Error: OPENAI_API_KEY not found.')
			print('   Please set it in your .env file.')
			return

		# Check dependencies
		try:
			import speech_recognition as sr  # noqa: F401
		except ImportError:
			print('❌ SpeechRecognition not found.')
			print('   Install with: pip install browser-use[voice]')
			return

		# Set up status indicator
		self.status_indicator = self.setup_status_indicator()
		self.status_indicator.set_idle('Initializing...')

		# Initialize LLM
		try:
			llm = ChatOpenAI(model='gpt-4o', temperature=0.0)
		except Exception as e:
			print(f'❌ Error initializing LLM: {e}')
			return

		# Configure voice agent with callbacks
		# Using default values from VoiceAgentConfig for most settings
		config = VoiceAgentConfig(
			wake_words=['hey suno mirza', 'hey browser', 'hey assistant'],
			enable_voice_feedback=True,
			use_vision=True,
			continuous_mode=True,
			auto_start_listening=True,
			require_confirmation_for_destructive=True,
			on_command_start=self.on_command_start,
			on_command_complete=self.on_command_complete,
			on_listening_state_change=self.on_listening_change,
		)

		# Create voice agent
		self.voice_agent = VoiceAgent(llm=llm, config=config)
		self.status_indicator.set_success('Voice agent ready!')

		try:
			# Run the voice agent
			await self.voice_agent.run()

		except KeyboardInterrupt:
			print('\n\n👋 Shutting down...')

		finally:
			# Clean up
			if self.voice_agent:
				await self.voice_agent.stop()

			# Show statistics
			self.print_statistics()

			# Show activity summary
			if self.status_indicator:
				self.status_indicator.print_summary()


async def main():
	"""Main entry point."""
	app = VoiceBrowserApp()
	await app.run()


if __name__ == '__main__':
	asyncio.run(main())
