"""
Voice-controlled browser demo.

This example demonstrates how to use the voice-controlled browser agent
to control a web browser using voice commands.

Requirements:
    - pip install SpeechRecognition pyttsx3 pyaudio
    - A working microphone
    - Set up your LLM API key in .env file

Usage:
    python examples/voice/voice_browser_demo.py

Supported commands (after saying the wake word "Hey Suno Mirza" or "Hey Browser"):
    - "Go to google.com"
    - "Search for Python tutorials"
    - "Scroll down"
    - "Click on the first result"
    - "Open new tab"
    - "Close tab"
    - "Go back"
    - "Compose email to john@example.com"
    - And many more natural language commands!

To stop: Say "stop" or "cancel", or press Ctrl+C
"""

import asyncio
import os
import sys

# Add parent directory to path for local development
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from browser_use.voice import VoiceAgent, VoiceAgentConfig

load_dotenv()


def print_banner():
	"""Print welcome banner with instructions."""
	banner = """
╔══════════════════════════════════════════════════════════════════╗
║           🎤 Voice-Controlled Browser Demo 🌐                   ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Wake Words: "Hey Suno Mirza" or "Hey Browser"                  ║
║                                                                  ║
║  Example Commands:                                               ║
║    • "Go to google.com"                                         ║
║    • "Search for Python tutorials"                              ║
║    • "Scroll down"                                              ║
║    • "Click on settings"                                        ║
║    • "Open new tab"                                             ║
║    • "Go back"                                                  ║
║                                                                  ║
║  Control:                                                        ║
║    • Say "stop" or "cancel" to interrupt                        ║
║    • Say "help" for more commands                               ║
║    • Press Ctrl+C to exit                                       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
	print(banner)


def on_command_start(command: str):
	"""Callback when a command starts."""
	print(f'\n🎯 Starting: {command}')


def on_command_complete(command: str, success: bool):
	"""Callback when a command completes."""
	status = '✅' if success else '❌'
	print(f'{status} Completed: {command}\n')


def on_listening_change(is_listening: bool):
	"""Callback when listening state changes."""
	if is_listening:
		print('🎤 Listening for your command...')


async def main():
	"""Main function to run the voice browser demo."""
	print_banner()

	# Check for API key
	if not os.environ.get('OPENAI_API_KEY'):
		print('⚠️  Warning: OPENAI_API_KEY not found in environment.')
		print('   Please set it in your .env file or environment.')
		print('   Example: OPENAI_API_KEY=sk-...\n')

	# Check for audio dependencies
	try:
		import speech_recognition as sr  # noqa: F401

		print('✓ SpeechRecognition library found')
	except ImportError:
		print('❌ SpeechRecognition library not found.')
		print('   Install with: pip install SpeechRecognition')
		return

	try:
		import pyttsx3  # noqa: F401

		print('✓ pyttsx3 library found')
	except ImportError:
		print('⚠️  pyttsx3 not found - voice feedback disabled')
		print('   Install with: pip install pyttsx3')

	# Check for microphone
	try:
		import speech_recognition as sr

		mic = sr.Microphone()
		print('✓ Microphone detected')
		del mic
	except OSError as e:
		print(f'❌ Microphone error: {e}')
		print('   Please ensure a microphone is connected and working.')
		return

	print('\n' + '=' * 60)
	print('Starting voice-controlled browser...')
	print('=' * 60 + '\n')

	# Initialize LLM
	try:
		llm = ChatOpenAI(
			model='gpt-4o',
			temperature=0.0,
		)
	except Exception as e:
		print(f'❌ Error initializing LLM: {e}')
		return

	# Configure voice agent
	config = VoiceAgentConfig(
		wake_words=['hey suno mirza', 'hey browser', 'hey assistant'],
		enable_voice_feedback=True,
		voice_feedback_rate=175,
		use_vision=True,
		continuous_mode=True,
		auto_start_listening=True,
		require_confirmation_for_destructive=True,
		on_command_start=on_command_start,
		on_command_complete=on_command_complete,
		on_listening_state_change=on_listening_change,
	)

	# Create and run voice agent
	voice_agent = VoiceAgent(llm=llm, config=config)

	try:
		await voice_agent.run()
	except KeyboardInterrupt:
		print('\n\n👋 Goodbye!')
	finally:
		await voice_agent.stop()


if __name__ == '__main__':
	asyncio.run(main())
