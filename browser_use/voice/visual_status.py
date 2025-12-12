"""
Visual status indicator for voice-controlled browser.

This module provides visual feedback showing listening status,
recognized commands, and action progress.
"""

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)


class StatusType(Enum):
	"""Types of status indicators."""

	IDLE = 'idle'
	LISTENING = 'listening'
	PROCESSING = 'processing'
	EXECUTING = 'executing'
	SUCCESS = 'success'
	ERROR = 'error'


@dataclass
class StatusEvent:
	"""Represents a status event."""

	status_type: StatusType
	message: str
	timestamp: float
	details: Optional[str] = None


@dataclass
class VisualStatusConfig:
	"""Configuration for visual status indicator."""

	# Display settings
	show_in_terminal: bool = True
	use_colors: bool = True
	show_timestamps: bool = False

	# History settings
	max_history: int = 50

	# Callbacks
	on_status_change: Optional[Callable[[StatusEvent], None]] = None


class VisualStatusIndicator:
	"""
	Provides visual feedback for voice control status.

	Features:
	- Real-time status display in terminal
	- Color-coded status messages
	- Command history tracking
	- Customizable callbacks for UI integration
	"""

	# ANSI color codes
	COLORS = {
		StatusType.IDLE: '\033[90m',  # Gray
		StatusType.LISTENING: '\033[94m',  # Blue
		StatusType.PROCESSING: '\033[93m',  # Yellow
		StatusType.EXECUTING: '\033[96m',  # Cyan
		StatusType.SUCCESS: '\033[92m',  # Green
		StatusType.ERROR: '\033[91m',  # Red
	}
	RESET = '\033[0m'
	BOLD = '\033[1m'

	# Status icons
	ICONS = {
		StatusType.IDLE: '⏸️ ',
		StatusType.LISTENING: '🎤',
		StatusType.PROCESSING: '🔄',
		StatusType.EXECUTING: '⚙️ ',
		StatusType.SUCCESS: '✅',
		StatusType.ERROR: '❌',
	}

	def __init__(self, config: Optional[VisualStatusConfig] = None):
		"""
		Initialize the visual status indicator.

		Args:
			config: Configuration for the indicator. Uses defaults if not provided.
		"""
		self.config = config or VisualStatusConfig()
		self._current_status = StatusType.IDLE
		self._current_message = 'Ready'
		self._history: List[StatusEvent] = []
		self._lock = threading.Lock()

	def update_status(self, status_type: StatusType, message: str, details: Optional[str] = None) -> None:
		"""
		Update the current status.

		Args:
			status_type: The type of status.
			message: The status message.
			details: Optional additional details.
		"""
		with self._lock:
			event = StatusEvent(status_type=status_type, message=message, timestamp=time.time(), details=details)

			self._current_status = status_type
			self._current_message = message

			# Add to history
			self._history.append(event)
			if len(self._history) > self.config.max_history:
				self._history.pop(0)

		# Display in terminal
		if self.config.show_in_terminal:
			self._print_status(event)

		# Trigger callback
		if self.config.on_status_change:
			try:
				self.config.on_status_change(event)
			except Exception as e:
				logger.error(f'Error in status change callback: {e}')

	def _print_status(self, event: StatusEvent) -> None:
		"""Print the status to terminal."""
		icon = self.ICONS.get(event.status_type, '•')
		color = self.COLORS.get(event.status_type, '') if self.config.use_colors else ''
		reset = self.RESET if self.config.use_colors else ''

		timestamp = ''
		if self.config.show_timestamps:
			from datetime import datetime

			dt = datetime.fromtimestamp(event.timestamp)
			timestamp = f'[{dt.strftime("%H:%M:%S")}] '

		status_line = f'{timestamp}{color}{icon} {event.message}{reset}'

		if event.details:
			status_line += f'\n   {event.details}'

		print(status_line)

	def set_listening(self, command: Optional[str] = None) -> None:
		"""Set status to listening mode."""
		message = 'Listening...'
		if command:
			message = f'Heard: "{command}"'
		self.update_status(StatusType.LISTENING, message)

	def set_processing(self, command: str) -> None:
		"""Set status to processing mode."""
		self.update_status(StatusType.PROCESSING, f'Processing: "{command}"')

	def set_executing(self, task: str) -> None:
		"""Set status to executing mode."""
		self.update_status(StatusType.EXECUTING, f'Executing: {task}')

	def set_success(self, message: str = 'Done') -> None:
		"""Set status to success."""
		self.update_status(StatusType.SUCCESS, message)

	def set_error(self, error: str) -> None:
		"""Set status to error."""
		self.update_status(StatusType.ERROR, f'Error: {error}')

	def set_idle(self, message: str = 'Ready') -> None:
		"""Set status to idle."""
		self.update_status(StatusType.IDLE, message)

	def get_current_status(self) -> Tuple[StatusType, str]:
		"""Get the current status."""
		with self._lock:
			return self._current_status, self._current_message

	def get_history(self) -> List[StatusEvent]:
		"""Get the status history."""
		with self._lock:
			return self._history.copy()

	def clear_history(self) -> None:
		"""Clear the status history."""
		with self._lock:
			self._history.clear()

	def print_summary(self) -> None:
		"""Print a summary of recent activity."""
		with self._lock:
			if not self._history:
				print('No activity recorded.')
				return

			print('\n' + '=' * 50)
			print('Recent Activity Summary')
			print('=' * 50)

			# Count by status type
			counts = {}
			for event in self._history:
				counts[event.status_type] = counts.get(event.status_type, 0) + 1

			for status_type, count in counts.items():
				icon = self.ICONS.get(status_type, '•')
				print(f'{icon} {status_type.value}: {count}')

			# Show last 5 events
			print('\nLast 5 events:')
			for event in self._history[-5:]:
				icon = self.ICONS.get(event.status_type, '•')
				print(f'  {icon} {event.message}')

			print('=' * 50 + '\n')
