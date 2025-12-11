"""
Interrupt handler for voice-controlled browser.

This module handles user interruptions during browser operations,
providing smooth transitions between interrupted and new commands.
"""

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class InterruptState(Enum):
	"""States for the interrupt handler."""

	IDLE = 'idle'
	EXECUTING = 'executing'
	INTERRUPTED = 'interrupted'
	WAITING_FOR_NEW_COMMAND = 'waiting_for_new_command'
	RESUMING = 'resuming'


@dataclass
class PendingCommand:
	"""Represents a pending command in the queue."""

	task: str
	timestamp: datetime
	priority: int = 0
	cancelled: bool = False


@dataclass
class InterruptHandlerConfig:
	"""Configuration for the interrupt handler."""

	# Interrupt detection
	interrupt_keywords: List[str] = field(
		default_factory=lambda: ['stop', 'cancel', 'wait', 'hold on', 'pause', 'never mind', 'abort', 'halt']
	)

	# Timing
	interrupt_cooldown: float = 0.5  # Seconds to wait before accepting new interrupt
	transition_delay: float = 0.3  # Delay for smooth transitions

	# Queue management
	max_pending_commands: int = 5
	clear_queue_on_interrupt: bool = True

	# Callbacks
	on_interrupt: Optional[Callable[[], None]] = None
	on_resume: Optional[Callable[[], None]] = None
	on_state_change: Optional[Callable[[InterruptState], None]] = None
	on_command_cancelled: Optional[Callable[[str], None]] = None


class InterruptHandler:
	"""
	Handles user interruptions during voice-controlled browser operations.

	Features:
	- Detects interrupt keywords in speech
	- Manages command queue
	- Provides smooth transitions between operations
	- Supports cancellation and resumption

	Note: Uses threading.Lock for thread-safety since callbacks may come from
	speech recognition threads, combined with asyncio.Event for async coordination.
	"""

	def __init__(self, config: Optional[InterruptHandlerConfig] = None):
		"""
		Initialize the interrupt handler.

		Args:
			config: Configuration for the handler. Uses defaults if not provided.
		"""
		self.config = config or InterruptHandlerConfig()
		self.state = InterruptState.IDLE
		self._pending_commands: List[PendingCommand] = []
		self._current_task: Optional[asyncio.Task] = None
		self._current_command: Optional[str] = None
		# Use threading.Lock for thread-safety with speech recognition callbacks
		self._lock = threading.Lock()
		self._last_interrupt_time: Optional[float] = None
		# Use asyncio.Event for async coordination
		self._interrupt_event = asyncio.Event()

	def _set_state(self, state: InterruptState) -> None:
		"""Update state and trigger callback."""
		old_state = self.state
		self.state = state
		logger.debug(f'🛑 Interrupt state: {old_state.value} -> {state.value}')

		if self.config.on_state_change:
			try:
				self.config.on_state_change(state)
			except Exception as e:
				logger.error(f'Error in state change callback: {e}')

	def is_interrupt_keyword(self, text: str) -> bool:
		"""
		Check if the text contains an interrupt keyword.

		Args:
			text: The text to check.

		Returns:
			True if an interrupt keyword is found.
		"""
		text_lower = text.lower().strip()
		for keyword in self.config.interrupt_keywords:
			if keyword in text_lower:
				return True
		return False

	def check_and_handle_interrupt(self, text: str) -> bool:
		"""
		Check for interrupt in text and handle if found.

		Args:
			text: The recognized text.

		Returns:
			True if an interrupt was handled.
		"""
		if not self.is_interrupt_keyword(text):
			return False

		# Check cooldown
		import time

		current_time = time.time()
		if self._last_interrupt_time:
			if current_time - self._last_interrupt_time < self.config.interrupt_cooldown:
				logger.debug('🛑 Interrupt cooldown active, ignoring')
				return False

		self._last_interrupt_time = current_time
		self.trigger_interrupt()
		return True

	def trigger_interrupt(self) -> None:
		"""Trigger an interrupt of current operations."""
		logger.info('🛑 Interrupt triggered')

		with self._lock:
			self._set_state(InterruptState.INTERRUPTED)

			# Cancel current task if any
			if self._current_task and not self._current_task.done():
				self._current_task.cancel()
				logger.debug('🛑 Current task cancelled')

			# Clear queue if configured
			if self.config.clear_queue_on_interrupt:
				cancelled_commands = [cmd.task for cmd in self._pending_commands if not cmd.cancelled]
				self._pending_commands.clear()

				for cmd in cancelled_commands:
					if self.config.on_command_cancelled:
						self.config.on_command_cancelled(cmd)

			# Set interrupt event
			self._interrupt_event.set()

		if self.config.on_interrupt:
			self.config.on_interrupt()

		self._set_state(InterruptState.WAITING_FOR_NEW_COMMAND)

	async def wait_for_interrupt(self, timeout: Optional[float] = None) -> bool:
		"""
		Wait for an interrupt to occur.

		Args:
			timeout: Maximum time to wait in seconds.

		Returns:
			True if interrupted, False if timed out.
		"""
		try:
			await asyncio.wait_for(self._interrupt_event.wait(), timeout=timeout)
			return True
		except asyncio.TimeoutError:
			return False

	def clear_interrupt(self) -> None:
		"""Clear the interrupt event."""
		self._interrupt_event.clear()

	def start_execution(self, command: str, task: asyncio.Task) -> None:
		"""
		Mark the start of command execution.

		Args:
			command: The command being executed.
			task: The asyncio task for the execution.
		"""
		with self._lock:
			self._current_command = command
			self._current_task = task
			self._set_state(InterruptState.EXECUTING)
			self._interrupt_event.clear()

	def end_execution(self) -> None:
		"""Mark the end of command execution."""
		with self._lock:
			self._current_command = None
			self._current_task = None
			self._set_state(InterruptState.IDLE)

	def queue_command(self, task: str, priority: int = 0) -> bool:
		"""
		Add a command to the pending queue.

		Args:
			task: The command task.
			priority: Priority (higher = more important).

		Returns:
			True if added, False if queue is full.
		"""
		with self._lock:
			if len(self._pending_commands) >= self.config.max_pending_commands:
				logger.warning('🛑 Command queue full, rejecting command')
				return False

			command = PendingCommand(task=task, timestamp=datetime.now(), priority=priority)
			self._pending_commands.append(command)
			# Sort by priority (descending)
			self._pending_commands.sort(key=lambda x: x.priority, reverse=True)

			logger.debug(f'🛑 Command queued: {task}')
			return True

	def get_next_command(self) -> Optional[str]:
		"""
		Get the next pending command.

		Returns:
			The next command or None if queue is empty.
		"""
		with self._lock:
			while self._pending_commands:
				command = self._pending_commands.pop(0)
				if not command.cancelled:
					return command.task
			return None

	def cancel_pending_commands(self) -> List[str]:
		"""
		Cancel all pending commands.

		Returns:
			List of cancelled command tasks.
		"""
		with self._lock:
			cancelled = [cmd.task for cmd in self._pending_commands if not cmd.cancelled]

			for cmd in self._pending_commands:
				cmd.cancelled = True
				if self.config.on_command_cancelled:
					self.config.on_command_cancelled(cmd.task)

			self._pending_commands.clear()
			return cancelled

	def get_pending_count(self) -> int:
		"""Get the number of pending commands."""
		return len([cmd for cmd in self._pending_commands if not cmd.cancelled])

	def get_current_command(self) -> Optional[str]:
		"""Get the currently executing command."""
		return self._current_command

	def is_executing(self) -> bool:
		"""Check if currently executing a command."""
		return self.state == InterruptState.EXECUTING

	def is_interrupted(self) -> bool:
		"""Check if currently in interrupted state."""
		return self.state in (InterruptState.INTERRUPTED, InterruptState.WAITING_FOR_NEW_COMMAND)

	async def graceful_stop(self, timeout: float = 5.0) -> bool:
		"""
		Gracefully stop current execution.

		Args:
			timeout: Maximum time to wait for graceful stop.

		Returns:
			True if stopped gracefully, False if forced.
		"""
		if not self._current_task:
			return True

		self.trigger_interrupt()

		try:
			await asyncio.wait_for(asyncio.shield(self._current_task), timeout=timeout)
			return True
		except asyncio.TimeoutError:
			logger.warning('🛑 Graceful stop timed out, forcing cancellation')
			self._current_task.cancel()
			return False
		except asyncio.CancelledError:
			return True

	async def resume_execution(self) -> None:
		"""Resume execution after an interrupt."""
		if self.state != InterruptState.WAITING_FOR_NEW_COMMAND:
			return

		logger.info('🛑 Resuming execution')
		self._set_state(InterruptState.RESUMING)

		# Brief delay for smooth transition
		await asyncio.sleep(self.config.transition_delay)

		if self.config.on_resume:
			self.config.on_resume()

		self._set_state(InterruptState.IDLE)

	def reset(self) -> None:
		"""Reset the interrupt handler to initial state."""
		with self._lock:
			self._pending_commands.clear()
			self._current_task = None
			self._current_command = None
			self._interrupt_event.clear()
			self._last_interrupt_time = None
			self._set_state(InterruptState.IDLE)


class InterruptibleExecution:
	"""
	Context manager for interruptible command execution.

	Usage:
		async with InterruptibleExecution(handler) as exec:
			exec.check_interrupted()  # Check periodically
			await some_operation()
	"""

	def __init__(self, handler: InterruptHandler, command: str):
		"""
		Initialize the interruptible execution context.

		Args:
			handler: The interrupt handler.
			command: The command being executed.
		"""
		self.handler = handler
		self.command = command
		self._task: Optional[asyncio.Task] = None

	async def __aenter__(self) -> 'InterruptibleExecution':
		"""Enter the execution context."""
		self._task = asyncio.current_task()
		self.handler.start_execution(self.command, self._task)
		return self

	async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
		"""Exit the execution context."""
		self.handler.end_execution()

		# Don't suppress CancelledError from interrupts
		if exc_type is asyncio.CancelledError and self.handler.is_interrupted():
			return False

		return False

	def check_interrupted(self) -> None:
		"""
		Check if execution has been interrupted.

		Raises:
			asyncio.CancelledError if interrupted.
		"""
		if self.handler.is_interrupted():
			raise asyncio.CancelledError('Execution interrupted by user')

	async def sleep_interruptible(self, seconds: float) -> bool:
		"""
		Sleep that can be interrupted.

		Args:
			seconds: Duration to sleep.

		Returns:
			True if slept fully, False if interrupted.
		"""
		try:
			await asyncio.wait_for(self.handler.wait_for_interrupt(timeout=seconds), timeout=seconds)
			return False  # Interrupted
		except asyncio.TimeoutError:
			return True  # Completed sleep
