"""
Voice control module for browser-use.

This module provides voice control capabilities for browser automation,
including continuous speech recognition, wake word detection, command parsing,
and interrupt handling.
"""

from browser_use.voice.command_parser import CommandParser, CommandType, VoiceCommand
from browser_use.voice.interrupt_handler import InterruptHandler, InterruptState
from browser_use.voice.speech_recognition import SpeechRecognizer, SpeechRecognizerConfig
from browser_use.voice.voice_agent import VoiceAgent, VoiceAgentConfig
from browser_use.voice.voice_feedback import VoiceFeedback, VoiceFeedbackConfig

__all__ = [
	'SpeechRecognizer',
	'SpeechRecognizerConfig',
	'CommandParser',
	'VoiceCommand',
	'CommandType',
	'VoiceFeedback',
	'VoiceFeedbackConfig',
	'InterruptHandler',
	'InterruptState',
	'VoiceAgent',
	'VoiceAgentConfig',
]
