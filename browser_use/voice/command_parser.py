"""
Command parser module for voice-controlled browser.

This module parses voice commands into structured browser actions,
supporting natural language variations and command chaining.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class CommandType(Enum):
	"""Types of browser commands."""

	# Navigation
	NAVIGATE = 'navigate'
	SEARCH = 'search'
	GO_BACK = 'go_back'
	GO_FORWARD = 'go_forward'
	REFRESH = 'refresh'

	# Tab management
	NEW_TAB = 'new_tab'
	CLOSE_TAB = 'close_tab'
	SWITCH_TAB = 'switch_tab'

	# Page interaction
	SCROLL_DOWN = 'scroll_down'
	SCROLL_UP = 'scroll_up'
	CLICK = 'click'
	TYPE = 'type'
	FILL_FORM = 'fill_form'

	# Browser controls
	BOOKMARK = 'bookmark'
	OPEN_BOOKMARKS = 'open_bookmarks'
	OPEN_HISTORY = 'open_history'
	OPEN_SETTINGS = 'open_settings'

	# Email actions
	COMPOSE_EMAIL = 'compose_email'
	REPLY_EMAIL = 'reply_email'
	SEND_EMAIL = 'send_email'

	# General actions
	STOP = 'stop'
	CANCEL = 'cancel'
	HELP = 'help'
	REPEAT = 'repeat'
	CONFIRM = 'confirm'

	# Custom/LLM-handled
	CUSTOM = 'custom'
	UNKNOWN = 'unknown'


@dataclass
class VoiceCommand:
	"""Represents a parsed voice command."""

	command_type: CommandType
	raw_text: str
	parameters: Dict[str, Any] = field(default_factory=dict)
	confidence: float = 1.0
	requires_confirmation: bool = False
	is_destructive: bool = False


class CommandParser:
	"""
	Parses voice commands into structured browser actions.

	Supports:
	- Natural language variations of commands
	- Command chaining (multiple commands in one utterance)
	- Parameter extraction
	- Confidence scoring
	"""

	# Pattern definitions for command matching
	PATTERNS = {
		# Navigation patterns
		CommandType.NAVIGATE: [
			r'(?:go to|navigate to|open|visit)\s+(.+)',
			r'(?:take me to|show me)\s+(.+)',
		],
		CommandType.SEARCH: [
			r'(?:search for|search|google|find|look up|look for)\s+(.+)',
			r'(?:what is|who is|where is)\s+(.+)',
		],
		CommandType.GO_BACK: [
			r'go back',
			r'back',
			r'previous page',
			r'navigate back',
		],
		CommandType.GO_FORWARD: [
			r'go forward',
			r'forward',
			r'next page',
			r'navigate forward',
		],
		CommandType.REFRESH: [
			r'refresh',
			r'reload',
			r'refresh page',
			r'reload page',
		],
		# Tab management patterns
		CommandType.NEW_TAB: [
			r'(?:open|create)\s+(?:a\s+)?new tab',
			r'new tab',
		],
		CommandType.CLOSE_TAB: [
			r'close\s+(?:this\s+)?tab',
			r'close\s+(?:the\s+)?(?:current\s+)?tab',
		],
		CommandType.SWITCH_TAB: [
			r'switch to tab\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)',
			r'go to tab\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)',
			r'tab\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)',
		],
		# Page interaction patterns
		CommandType.SCROLL_DOWN: [
			r'scroll down',
			r'scroll down\s+(\d+)(?:\s+pixels)?',
			r'page down',
			r'go down',
		],
		CommandType.SCROLL_UP: [
			r'scroll up',
			r'scroll up\s+(\d+)(?:\s+pixels)?',
			r'page up',
			r'go up',
		],
		CommandType.CLICK: [
			r'click\s+(?:on\s+)?(.+)',
			r'press\s+(?:the\s+)?(.+)',
			r'tap\s+(?:on\s+)?(.+)',
			r'select\s+(.+)',
		],
		CommandType.TYPE: [
			r'type\s+(.+)',
			r'enter\s+(.+)',
			r'input\s+(.+)',
			r'write\s+(.+)',
		],
		CommandType.FILL_FORM: [
			r'fill\s+(?:the\s+)?form\s+with\s+(.+)',
			r'fill\s+(?:out\s+)?(?:the\s+)?form',
			r'complete\s+(?:the\s+)?form',
		],
		# Browser control patterns
		CommandType.BOOKMARK: [
			r'bookmark\s+(?:this\s+)?page',
			r'add\s+(?:to\s+)?bookmark',
			r'save\s+(?:this\s+)?(?:page|site)',
		],
		CommandType.OPEN_BOOKMARKS: [
			r'(?:open|show)\s+bookmarks',
			r'bookmarks',
			r'my bookmarks',
		],
		CommandType.OPEN_HISTORY: [
			r'(?:open|show)\s+history',
			r'browsing history',
			r'my history',
		],
		CommandType.OPEN_SETTINGS: [
			r'(?:open|show)\s+settings',
			r'browser settings',
			r'preferences',
		],
		# Email patterns
		CommandType.COMPOSE_EMAIL: [
			r'(?:compose|write|create)\s+(?:an?\s+)?email(?:\s+to\s+(.+))?',
			r'(?:send|draft)\s+(?:an?\s+)?email(?:\s+to\s+(.+))?',
			r'email\s+(.+)',
		],
		CommandType.REPLY_EMAIL: [
			r'reply\s+(?:to\s+)?(?:this\s+)?email',
			r'respond\s+(?:to\s+)?(?:this\s+)?email',
			r'reply',
		],
		CommandType.SEND_EMAIL: [
			r'send\s+(?:the\s+)?email',
			r'send\s+it',
			r'send\s+(?:the\s+)?message',
		],
		# Control patterns
		CommandType.STOP: [
			r'stop',
			r'halt',
			r'pause',
			r'wait',
		],
		CommandType.CANCEL: [
			r'cancel',
			r'abort',
			r'never mind',
			r'forget it',
		],
		CommandType.HELP: [
			r'help',
			r'what can you do',
			r'show commands',
			r'list commands',
		],
		CommandType.REPEAT: [
			r'repeat',
			r'say that again',
			r'what did you say',
			r'again',
		],
		CommandType.CONFIRM: [
			r'yes',
			r'confirm',
			r'okay',
			r'ok',
			r'do it',
			r'proceed',
			r'go ahead',
		],
	}

	# Word to number mapping for tab switching
	WORD_TO_NUMBER = {
		'one': 1,
		'two': 2,
		'three': 3,
		'four': 4,
		'five': 5,
		'six': 6,
		'seven': 7,
		'eight': 8,
		'nine': 9,
		'ten': 10,
		'first': 1,
		'second': 2,
		'third': 3,
		'fourth': 4,
		'fifth': 5,
	}

	# Commands that require confirmation
	DESTRUCTIVE_COMMANDS = {
		CommandType.CLOSE_TAB,
		CommandType.SEND_EMAIL,
	}

	# Priority order for command matching (more specific patterns first)
	PATTERN_PRIORITY = [
		# Tab management first (to match "open new tab" before "open [url]")
		CommandType.NEW_TAB,
		CommandType.CLOSE_TAB,
		CommandType.SWITCH_TAB,
		# Control commands
		CommandType.STOP,
		CommandType.CANCEL,
		CommandType.HELP,
		CommandType.REPEAT,
		CommandType.CONFIRM,
		# Navigation with specific keywords
		CommandType.GO_BACK,
		CommandType.GO_FORWARD,
		CommandType.REFRESH,
		CommandType.SEARCH,
		# Page interaction
		CommandType.SCROLL_DOWN,
		CommandType.SCROLL_UP,
		CommandType.CLICK,
		CommandType.TYPE,
		CommandType.FILL_FORM,
		# Email commands
		CommandType.COMPOSE_EMAIL,
		CommandType.REPLY_EMAIL,
		CommandType.SEND_EMAIL,
		# Browser controls
		CommandType.BOOKMARK,
		CommandType.OPEN_BOOKMARKS,
		CommandType.OPEN_HISTORY,
		CommandType.OPEN_SETTINGS,
		# Generic navigation last (catches "open [anything]")
		CommandType.NAVIGATE,
	]

	def __init__(self):
		"""Initialize the command parser."""
		self._compiled_patterns: Dict[CommandType, List[re.Pattern]] = {}
		self._compile_patterns()

	def _compile_patterns(self) -> None:
		"""Compile regex patterns for faster matching."""
		for cmd_type, patterns in self.PATTERNS.items():
			self._compiled_patterns[cmd_type] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

	def _word_to_number(self, word: str) -> int:
		"""Convert a word number to integer."""
		word = word.lower().strip()
		if word.isdigit():
			return int(word)
		return self.WORD_TO_NUMBER.get(word, 0)

	def _extract_url(self, text: str) -> str:
		"""Extract and normalize a URL from text."""
		text = text.strip()

		# Common website shortcuts
		shortcuts = {
			'google': 'https://www.google.com',
			'youtube': 'https://www.youtube.com',
			'facebook': 'https://www.facebook.com',
			'twitter': 'https://www.twitter.com',
			'github': 'https://www.github.com',
			'linkedin': 'https://www.linkedin.com',
			'amazon': 'https://www.amazon.com',
			'reddit': 'https://www.reddit.com',
			'gmail': 'https://mail.google.com',
			'outlook': 'https://outlook.live.com',
		}

		# Check for shortcuts
		text_lower = text.lower()
		for name, url in shortcuts.items():
			if text_lower == name or text_lower == f'{name}.com':
				return url

		# Add https:// if no protocol specified
		if not text.startswith(('http://', 'https://')):
			if '.' in text:
				return f'https://{text}'
			# Assume it's a search query if no dots
			return text

		return text

	def parse(self, text: str) -> VoiceCommand:
		"""
		Parse a voice command from text.

		Args:
			text: The recognized speech text.

		Returns:
			A VoiceCommand object with the parsed command.
		"""
		text = text.strip()

		if not text:
			return VoiceCommand(command_type=CommandType.UNKNOWN, raw_text=text, confidence=0.0)

		# Try to match against known patterns in priority order
		for cmd_type in self.PATTERN_PRIORITY:
			if cmd_type not in self._compiled_patterns:
				continue
			patterns = self._compiled_patterns[cmd_type]
			for pattern in patterns:
				match = pattern.match(text)
				if match:
					params = self._extract_parameters(cmd_type, match, text)
					is_destructive = cmd_type in self.DESTRUCTIVE_COMMANDS

					return VoiceCommand(
						command_type=cmd_type,
						raw_text=text,
						parameters=params,
						confidence=0.9,
						requires_confirmation=is_destructive,
						is_destructive=is_destructive,
					)

		# No exact match - treat as custom command for LLM
		return VoiceCommand(command_type=CommandType.CUSTOM, raw_text=text, parameters={'task': text}, confidence=0.7)

	def _extract_parameters(self, cmd_type: CommandType, match: re.Match, full_text: str) -> Dict[str, Any]:
		"""Extract parameters from a matched pattern."""
		params: Dict[str, Any] = {}

		try:
			groups = match.groups()

			if cmd_type == CommandType.NAVIGATE and groups:
				params['url'] = self._extract_url(groups[0])

			elif cmd_type == CommandType.SEARCH and groups:
				params['query'] = groups[0]

			elif cmd_type == CommandType.SWITCH_TAB and groups:
				params['tab_number'] = self._word_to_number(groups[0])

			elif cmd_type == CommandType.CLICK and groups:
				params['element'] = groups[0]

			elif cmd_type == CommandType.TYPE and groups:
				params['text'] = groups[0]

			elif cmd_type in (CommandType.SCROLL_DOWN, CommandType.SCROLL_UP) and groups:
				if groups[0]:
					params['amount'] = int(groups[0])

			elif cmd_type == CommandType.COMPOSE_EMAIL and groups:
				if groups[0]:
					params['recipient'] = groups[0]

			elif cmd_type == CommandType.FILL_FORM and groups:
				if groups[0]:
					params['data'] = groups[0]

		except Exception as e:
			logger.error(f'Error extracting parameters: {e}')

		return params

	def parse_chained(self, text: str) -> List[VoiceCommand]:
		"""
		Parse a text that may contain multiple chained commands.

		Args:
			text: The recognized speech text.

		Returns:
			A list of VoiceCommand objects.
		"""
		# Split by common conjunction words
		separators = [' and then ', ' then ', ' and ', ' after that ']

		commands = []
		parts = [text]

		for sep in separators:
			new_parts = []
			for part in parts:
				new_parts.extend(part.split(sep))
			parts = new_parts

		for part in parts:
			part = part.strip()
			if part:
				command = self.parse(part)
				if command.command_type != CommandType.UNKNOWN:
					commands.append(command)

		# If no valid commands found, treat the whole text as a custom command
		if not commands:
			commands.append(
				VoiceCommand(command_type=CommandType.CUSTOM, raw_text=text, parameters={'task': text}, confidence=0.7)
			)

		return commands

	def get_help_text(self) -> str:
		"""Get help text describing available commands."""
		help_text = """
Available Voice Commands:

📍 Navigation:
  • "Go to [website]" - Navigate to a website
  • "Search for [query]" - Search in Google
  • "Go back" / "Go forward" - Navigate history
  • "Refresh" - Reload current page

📑 Tab Management:
  • "Open new tab" - Create a new tab
  • "Close tab" - Close current tab
  • "Switch to tab [number]" - Switch to specific tab

📜 Page Interaction:
  • "Scroll down/up" - Scroll the page
  • "Click on [element]" - Click an element
  • "Type [text]" - Enter text

📧 Email:
  • "Compose email to [recipient]" - Start new email
  • "Reply to email" - Reply to current email
  • "Send email" - Send the email

🎤 Control:
  • "Stop" / "Cancel" - Stop current action
  • "Help" - Show available commands
  • "Yes" / "Confirm" - Confirm an action

💡 Tip: You can chain commands with "and then" or "then"
   Example: "Go to gmail and then compose email"
"""
		return help_text

	def format_command_for_agent(self, command: VoiceCommand) -> str:
		"""
		Format a voice command as a task for the browser-use Agent.

		Args:
			command: The parsed voice command.

		Returns:
			A task string for the Agent.
		"""
		if command.command_type == CommandType.NAVIGATE:
			url = command.parameters.get('url', '')
			return f'Navigate to {url}'

		elif command.command_type == CommandType.SEARCH:
			query = command.parameters.get('query', '')
			return f'Search for "{query}" in Google'

		elif command.command_type == CommandType.GO_BACK:
			return 'Go back to the previous page'

		elif command.command_type == CommandType.GO_FORWARD:
			return 'Go forward to the next page'

		elif command.command_type == CommandType.REFRESH:
			return 'Refresh the current page'

		elif command.command_type == CommandType.NEW_TAB:
			return 'Open a new tab'

		elif command.command_type == CommandType.CLOSE_TAB:
			return 'Close the current tab'

		elif command.command_type == CommandType.SWITCH_TAB:
			tab_num = command.parameters.get('tab_number', 1)
			return f'Switch to tab number {tab_num}'

		elif command.command_type == CommandType.SCROLL_DOWN:
			amount = command.parameters.get('amount')
			if amount:
				return f'Scroll down {amount} pixels'
			return 'Scroll down the page'

		elif command.command_type == CommandType.SCROLL_UP:
			amount = command.parameters.get('amount')
			if amount:
				return f'Scroll up {amount} pixels'
			return 'Scroll up the page'

		elif command.command_type == CommandType.CLICK:
			element = command.parameters.get('element', '')
			return f'Click on the element that says "{element}" or is related to "{element}"'

		elif command.command_type == CommandType.TYPE:
			text = command.parameters.get('text', '')
			return f'Type the following text: "{text}"'

		elif command.command_type == CommandType.COMPOSE_EMAIL:
			recipient = command.parameters.get('recipient')
			if recipient:
				return f'Compose a new email to {recipient}'
			return 'Compose a new email'

		elif command.command_type == CommandType.REPLY_EMAIL:
			return 'Reply to the current email'

		elif command.command_type == CommandType.SEND_EMAIL:
			return 'Send the email'

		elif command.command_type == CommandType.BOOKMARK:
			return 'Bookmark this page'

		elif command.command_type == CommandType.CUSTOM:
			task = command.parameters.get('task', command.raw_text)
			return task

		else:
			return command.raw_text
