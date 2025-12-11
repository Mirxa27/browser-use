"""
Speech recognition module for voice-controlled browser.

This module provides continuous speech recognition with wake word detection,
using the SpeechRecognition library as the primary backend.
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class RecognitionState(Enum):
	"""State of the speech recognizer."""

	IDLE = 'idle'
	LISTENING_FOR_WAKE_WORD = 'listening_for_wake_word'
	LISTENING_FOR_COMMAND = 'listening_for_command'
	PROCESSING = 'processing'
	ERROR = 'error'


@dataclass
class SpeechRecognizerConfig:
	"""Configuration for the speech recognizer."""

	# Wake word configuration
	wake_words: List[str] = field(default_factory=lambda: ['hey suno mirza', 'hey browser', 'hey assistant'])
	wake_word_sensitivity: float = 0.7  # 0.0 to 1.0, higher = more sensitive

	# Recognition settings
	language: str = 'en-US'
	timeout: float = 5.0  # Seconds to wait for speech
	phrase_time_limit: float = 15.0  # Max seconds for a single phrase
	energy_threshold: int = 300  # Minimum audio energy to consider for recording
	dynamic_energy_threshold: bool = True  # Adjust energy threshold dynamically
	pause_threshold: float = 0.8  # Seconds of silence to consider phrase complete

	# Callback settings
	on_wake_word_detected: Optional[Callable[[], None]] = None
	on_command_recognized: Optional[Callable[[str], None]] = None
	on_state_change: Optional[Callable[[RecognitionState], None]] = None
	on_error: Optional[Callable[[str], None]] = None

	# Backend settings
	recognizer_backend: str = 'google'  # 'google', 'sphinx', 'whisper'


class SpeechRecognizer:
	"""
	Continuous speech recognizer with wake word detection.

	This class provides:
	- Continuous listening for wake words
	- Command recognition after wake word detection
	- State management and callbacks
	- Error handling and recovery
	"""

	def __init__(self, config: Optional[SpeechRecognizerConfig] = None):
		"""
		Initialize the speech recognizer.

		Args:
			config: Configuration for the recognizer. Uses defaults if not provided.
		"""
		self.config = config or SpeechRecognizerConfig()
		self.state = RecognitionState.IDLE
		self._running = False
		self._recognition_thread: Optional[threading.Thread] = None
		self._loop: Optional[asyncio.AbstractEventLoop] = None
		self._recognizer = None
		self._microphone = None
		self._last_error: Optional[str] = None

		# Initialize speech recognition
		self._init_recognizer()

	def _init_recognizer(self) -> None:
		"""Initialize the speech recognition engine."""
		try:
			import speech_recognition as sr

			self._recognizer = sr.Recognizer()
			self._microphone = sr.Microphone()

			# Configure recognizer settings
			self._recognizer.energy_threshold = self.config.energy_threshold
			self._recognizer.dynamic_energy_threshold = self.config.dynamic_energy_threshold
			self._recognizer.pause_threshold = self.config.pause_threshold

			# Adjust for ambient noise initially
			with self._microphone as source:
				logger.info('🎤 Adjusting for ambient noise...')
				self._recognizer.adjust_for_ambient_noise(source, duration=1)
				logger.info(f'🎤 Energy threshold set to: {self._recognizer.energy_threshold}')

			logger.info('🎤 Speech recognizer initialized successfully')

		except ImportError:
			error_msg = 'SpeechRecognition library not installed. Install with: pip install SpeechRecognition'
			logger.error(error_msg)
			self._last_error = error_msg
			raise ImportError(error_msg)
		except Exception as e:
			error_msg = f'Failed to initialize speech recognizer: {str(e)}'
			logger.error(error_msg)
			self._last_error = error_msg
			raise RuntimeError(error_msg)

	def _set_state(self, state: RecognitionState) -> None:
		"""Update the recognizer state and trigger callback."""
		old_state = self.state
		self.state = state
		logger.debug(f'🎤 State changed: {old_state.value} -> {state.value}')

		if self.config.on_state_change:
			try:
				self.config.on_state_change(state)
			except Exception as e:
				logger.error(f'Error in state change callback: {e}')

	def _check_wake_word(self, text: str) -> bool:
		"""Check if the recognized text contains a wake word."""
		text_lower = text.lower().strip()
		for wake_word in self.config.wake_words:
			if wake_word.lower() in text_lower:
				logger.info(f'🎤 Wake word detected: "{wake_word}" in "{text}"')
				return True
		return False

	def _recognize_speech(self, audio) -> Optional[str]:
		"""
		Recognize speech from audio data.

		Args:
			audio: Audio data from the microphone.

		Returns:
			Recognized text or None if recognition failed.
		"""
		import speech_recognition as sr

		try:
			if self.config.recognizer_backend == 'google':
				text = self._recognizer.recognize_google(audio, language=self.config.language)
			elif self.config.recognizer_backend == 'sphinx':
				text = self._recognizer.recognize_sphinx(audio)
			elif self.config.recognizer_backend == 'whisper':
				text = self._recognizer.recognize_whisper(audio, language=self.config.language[:2])
			else:
				text = self._recognizer.recognize_google(audio, language=self.config.language)

			logger.debug(f'🎤 Recognized: "{text}"')
			return text

		except sr.UnknownValueError:
			logger.debug('🎤 Speech not understood')
			return None
		except sr.RequestError as e:
			error_msg = f'Speech recognition service error: {e}'
			logger.error(error_msg)
			if self.config.on_error:
				self.config.on_error(error_msg)
			return None
		except Exception as e:
			error_msg = f'Recognition error: {e}'
			logger.error(error_msg)
			return None

	def _listen_loop(self) -> None:
		"""Main listening loop running in a separate thread."""
		import speech_recognition as sr

		logger.info('🎤 Starting voice listening loop...')
		self._set_state(RecognitionState.LISTENING_FOR_WAKE_WORD)

		while self._running:
			try:
				with self._microphone as source:
					if self.state == RecognitionState.LISTENING_FOR_WAKE_WORD:
						logger.debug('🎤 Waiting for wake word...')
						try:
							audio = self._recognizer.listen(
								source, timeout=self.config.timeout, phrase_time_limit=self.config.phrase_time_limit
							)
						except sr.WaitTimeoutError:
							continue

						text = self._recognize_speech(audio)
						if text and self._check_wake_word(text):
							if self.config.on_wake_word_detected:
								self.config.on_wake_word_detected()
							self._set_state(RecognitionState.LISTENING_FOR_COMMAND)

					elif self.state == RecognitionState.LISTENING_FOR_COMMAND:
						logger.info('🎤 Listening for command...')
						try:
							audio = self._recognizer.listen(
								source, timeout=self.config.timeout, phrase_time_limit=self.config.phrase_time_limit
							)
						except sr.WaitTimeoutError:
							logger.info('🎤 Command timeout, returning to wake word mode')
							self._set_state(RecognitionState.LISTENING_FOR_WAKE_WORD)
							continue

						self._set_state(RecognitionState.PROCESSING)
						text = self._recognize_speech(audio)

						if text:
							logger.info(f'🎤 Command recognized: "{text}"')
							if self.config.on_command_recognized:
								self.config.on_command_recognized(text)

						# Return to wake word mode after processing
						self._set_state(RecognitionState.LISTENING_FOR_WAKE_WORD)

			except Exception as e:
				error_msg = f'Error in listen loop: {e}'
				logger.error(error_msg)
				self._set_state(RecognitionState.ERROR)
				if self.config.on_error:
					self.config.on_error(error_msg)
				time.sleep(1)  # Brief pause before retry
				self._set_state(RecognitionState.LISTENING_FOR_WAKE_WORD)

		logger.info('🎤 Voice listening loop stopped')

	async def start(self) -> None:
		"""Start the speech recognizer asynchronously."""
		if self._running:
			logger.warning('🎤 Speech recognizer already running')
			return

		self._running = True
		self._loop = asyncio.get_event_loop()

		# Start listening in a separate thread
		self._recognition_thread = threading.Thread(target=self._listen_loop, daemon=True)
		self._recognition_thread.start()

		logger.info('🎤 Speech recognizer started')

	async def stop(self) -> None:
		"""Stop the speech recognizer."""
		if not self._running:
			return

		self._running = False
		self._set_state(RecognitionState.IDLE)

		if self._recognition_thread and self._recognition_thread.is_alive():
			self._recognition_thread.join(timeout=2.0)

		logger.info('🎤 Speech recognizer stopped')

	def is_running(self) -> bool:
		"""Check if the recognizer is running."""
		return self._running

	def get_state(self) -> RecognitionState:
		"""Get the current recognition state."""
		return self.state

	def get_last_error(self) -> Optional[str]:
		"""Get the last error message."""
		return self._last_error

	def skip_to_command_mode(self) -> None:
		"""Skip wake word detection and go directly to command mode."""
		if self._running:
			self._set_state(RecognitionState.LISTENING_FOR_COMMAND)

	def reset_to_wake_word_mode(self) -> None:
		"""Reset to listening for wake word."""
		if self._running:
			self._set_state(RecognitionState.LISTENING_FOR_WAKE_WORD)

	async def listen_once(self, timeout: Optional[float] = None) -> Optional[str]:
		"""
		Listen for a single command (bypassing wake word detection).

		Args:
			timeout: Optional timeout in seconds.

		Returns:
			Recognized text or None.
		"""
		import speech_recognition as sr

		try:
			with self._microphone as source:
				logger.info('🎤 Listening for single command...')
				audio = self._recognizer.listen(
					source, timeout=timeout or self.config.timeout, phrase_time_limit=self.config.phrase_time_limit
				)
				return self._recognize_speech(audio)
		except sr.WaitTimeoutError:
			logger.debug('🎤 Listen once timeout')
			return None
		except Exception as e:
			logger.error(f'🎤 Listen once error: {e}')
			return None
