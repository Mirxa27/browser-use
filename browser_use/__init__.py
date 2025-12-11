from browser_use.logging_config import setup_logging

setup_logging()

from browser_use.agent.prompts import SystemPrompt as SystemPrompt
from browser_use.agent.service import Agent as Agent
from browser_use.agent.views import ActionModel as ActionModel
from browser_use.agent.views import ActionResult as ActionResult
from browser_use.agent.views import AgentHistoryList as AgentHistoryList
from browser_use.browser.browser import Browser as Browser
from browser_use.browser.browser import BrowserConfig as BrowserConfig
from browser_use.browser.context import BrowserContextConfig
from browser_use.controller.service import Controller as Controller
from browser_use.dom.service import DomService as DomService

# Voice control module (optional - requires voice dependencies)
try:
	from browser_use.voice import VoiceAgent as VoiceAgent
	from browser_use.voice import VoiceAgentConfig as VoiceAgentConfig

	_voice_available = True
except ImportError:
	_voice_available = False

__all__ = [
	'Agent',
	'Browser',
	'BrowserConfig',
	'Controller',
	'DomService',
	'SystemPrompt',
	'ActionResult',
	'ActionModel',
	'AgentHistoryList',
	'BrowserContextConfig',
]

# Add voice exports if available
if _voice_available:
	__all__.extend(['VoiceAgent', 'VoiceAgentConfig'])
