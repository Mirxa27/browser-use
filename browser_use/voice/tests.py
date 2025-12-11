"""
Tests for the voice control module.
"""

import pytest

from browser_use.voice.command_parser import CommandParser, CommandType, VoiceCommand
from browser_use.voice.interrupt_handler import InterruptHandler, InterruptState


class TestCommandParser:
	"""Tests for the command parser."""

	def setup_method(self):
		"""Set up test fixtures."""
		self.parser = CommandParser()

	def test_parse_navigate_command(self):
		"""Test parsing navigation commands."""
		command = self.parser.parse('go to google.com')
		assert command.command_type == CommandType.NAVIGATE
		assert command.parameters.get('url') == 'https://google.com'

	def test_parse_search_command(self):
		"""Test parsing search commands."""
		command = self.parser.parse('search for Python tutorials')
		assert command.command_type == CommandType.SEARCH
		assert command.parameters.get('query') == 'Python tutorials'

	def test_parse_go_back_command(self):
		"""Test parsing go back command."""
		command = self.parser.parse('go back')
		assert command.command_type == CommandType.GO_BACK

	def test_parse_go_forward_command(self):
		"""Test parsing go forward command."""
		command = self.parser.parse('go forward')
		assert command.command_type == CommandType.GO_FORWARD

	def test_parse_refresh_command(self):
		"""Test parsing refresh command."""
		command = self.parser.parse('refresh')
		assert command.command_type == CommandType.REFRESH

	def test_parse_new_tab_command(self):
		"""Test parsing new tab command."""
		command = self.parser.parse('open new tab')
		assert command.command_type == CommandType.NEW_TAB

	def test_parse_close_tab_command(self):
		"""Test parsing close tab command."""
		command = self.parser.parse('close tab')
		assert command.command_type == CommandType.CLOSE_TAB
		assert command.requires_confirmation is True

	def test_parse_switch_tab_command(self):
		"""Test parsing switch tab command."""
		command = self.parser.parse('switch to tab 2')
		assert command.command_type == CommandType.SWITCH_TAB
		assert command.parameters.get('tab_number') == 2

	def test_parse_switch_tab_word_number(self):
		"""Test parsing switch tab with word numbers."""
		command = self.parser.parse('switch to tab three')
		assert command.command_type == CommandType.SWITCH_TAB
		assert command.parameters.get('tab_number') == 3

	def test_parse_scroll_down_command(self):
		"""Test parsing scroll down command."""
		command = self.parser.parse('scroll down')
		assert command.command_type == CommandType.SCROLL_DOWN

	def test_parse_scroll_up_command(self):
		"""Test parsing scroll up command."""
		command = self.parser.parse('scroll up')
		assert command.command_type == CommandType.SCROLL_UP

	def test_parse_click_command(self):
		"""Test parsing click command."""
		command = self.parser.parse('click on the submit button')
		assert command.command_type == CommandType.CLICK
		assert command.parameters.get('element') == 'the submit button'

	def test_parse_type_command(self):
		"""Test parsing type command."""
		command = self.parser.parse('type hello world')
		assert command.command_type == CommandType.TYPE
		assert command.parameters.get('text') == 'hello world'

	def test_parse_compose_email_command(self):
		"""Test parsing compose email command."""
		command = self.parser.parse('compose email to john@example.com')
		assert command.command_type == CommandType.COMPOSE_EMAIL
		assert command.parameters.get('recipient') == 'john@example.com'

	def test_parse_stop_command(self):
		"""Test parsing stop command."""
		command = self.parser.parse('stop')
		assert command.command_type == CommandType.STOP

	def test_parse_cancel_command(self):
		"""Test parsing cancel command."""
		command = self.parser.parse('cancel')
		assert command.command_type == CommandType.CANCEL

	def test_parse_help_command(self):
		"""Test parsing help command."""
		command = self.parser.parse('help')
		assert command.command_type == CommandType.HELP

	def test_parse_unknown_command(self):
		"""Test parsing unknown command becomes custom."""
		command = self.parser.parse('do something special for me')
		assert command.command_type == CommandType.CUSTOM
		assert command.parameters.get('task') == 'do something special for me'

	def test_parse_chained_commands(self):
		"""Test parsing chained commands."""
		commands = self.parser.parse_chained('go to google and then search for news')
		assert len(commands) >= 1
		# First command should be navigation
		assert commands[0].command_type == CommandType.NAVIGATE

	def test_format_command_for_agent_navigate(self):
		"""Test formatting navigate command for agent."""
		test_url = 'https://www.google.com'
		command = VoiceCommand(command_type=CommandType.NAVIGATE, raw_text='go to google', parameters={'url': test_url})
		task = self.parser.format_command_for_agent(command)
		assert 'Navigate to' in task
		# Verify the URL is included in the formatted task
		assert test_url in task

	def test_format_command_for_agent_search(self):
		"""Test formatting search command for agent."""
		command = VoiceCommand(command_type=CommandType.SEARCH, raw_text='search for news', parameters={'query': 'news'})
		task = self.parser.format_command_for_agent(command)
		assert 'Search' in task
		assert 'news' in task

	def test_get_help_text(self):
		"""Test getting help text."""
		help_text = self.parser.get_help_text()
		assert 'Navigation' in help_text
		assert 'Tab Management' in help_text
		assert 'Page Interaction' in help_text


class TestInterruptHandler:
	"""Tests for the interrupt handler."""

	def setup_method(self):
		"""Set up test fixtures."""
		self.handler = InterruptHandler()

	def test_initial_state(self):
		"""Test initial state is IDLE."""
		assert self.handler.state == InterruptState.IDLE

	def test_is_interrupt_keyword(self):
		"""Test interrupt keyword detection."""
		assert self.handler.is_interrupt_keyword('stop')
		assert self.handler.is_interrupt_keyword('cancel')
		assert self.handler.is_interrupt_keyword('pause')
		assert self.handler.is_interrupt_keyword('halt')
		assert not self.handler.is_interrupt_keyword('go to google')

	def test_trigger_interrupt(self):
		"""Test triggering an interrupt."""
		self.handler.trigger_interrupt()
		assert self.handler.state == InterruptState.WAITING_FOR_NEW_COMMAND

	def test_queue_command(self):
		"""Test queueing commands."""
		result = self.handler.queue_command('go to google')
		assert result is True
		assert self.handler.get_pending_count() == 1

	def test_get_next_command(self):
		"""Test getting next command from queue."""
		self.handler.queue_command('go to google')
		command = self.handler.get_next_command()
		assert command == 'go to google'
		assert self.handler.get_pending_count() == 0

	def test_cancel_pending_commands(self):
		"""Test cancelling pending commands."""
		self.handler.queue_command('command 1')
		self.handler.queue_command('command 2')
		cancelled = self.handler.cancel_pending_commands()
		assert len(cancelled) == 2
		assert self.handler.get_pending_count() == 0

	def test_reset(self):
		"""Test resetting the handler."""
		self.handler.queue_command('test')
		self.handler.trigger_interrupt()
		self.handler.reset()
		assert self.handler.state == InterruptState.IDLE
		assert self.handler.get_pending_count() == 0

	def test_check_and_handle_interrupt(self):
		"""Test checking and handling interrupt from text."""
		result = self.handler.check_and_handle_interrupt('please stop')
		assert result is True
		assert self.handler.state == InterruptState.WAITING_FOR_NEW_COMMAND

	def test_is_executing(self):
		"""Test is_executing check."""
		assert not self.handler.is_executing()

	def test_is_interrupted(self):
		"""Test is_interrupted check."""
		assert not self.handler.is_interrupted()
		self.handler.trigger_interrupt()
		assert self.handler.is_interrupted()


@pytest.mark.asyncio
class TestInterruptHandlerAsync:
	"""Async tests for interrupt handler."""

	async def test_resume_execution(self):
		"""Test resuming execution."""
		handler = InterruptHandler()
		handler.trigger_interrupt()
		await handler.resume_execution()
		assert handler.state == InterruptState.IDLE


class TestVoiceCommand:
	"""Tests for the VoiceCommand dataclass."""

	def test_voice_command_creation(self):
		"""Test creating a voice command."""
		command = VoiceCommand(
			command_type=CommandType.NAVIGATE,
			raw_text='go to google',
			parameters={'url': 'https://www.google.com'},
			confidence=0.9,
		)
		assert command.command_type == CommandType.NAVIGATE
		assert command.raw_text == 'go to google'
		assert command.parameters['url'] == 'https://www.google.com'
		assert command.confidence == 0.9
		assert command.requires_confirmation is False

	def test_destructive_command(self):
		"""Test destructive command flags."""
		command = VoiceCommand(
			command_type=CommandType.CLOSE_TAB, raw_text='close tab', requires_confirmation=True, is_destructive=True
		)
		assert command.requires_confirmation is True
		assert command.is_destructive is True
