# Voice-Controlled Browser

This example demonstrates how to use the voice-controlled browser agent to control a web browser using voice commands.

## Features

- **Wake Word Detection**: Activate the assistant by saying "Hey Suno Mirza" or "Hey Browser"
- **Continuous Listening**: The browser continuously listens for voice commands
- **Natural Language Commands**: Use natural language to control the browser
- **Voice Feedback**: Get audio confirmation of your commands
- **Interrupt Support**: Say "stop" or "cancel" at any time to interrupt

## Requirements

Install the required dependencies:

```bash
pip install SpeechRecognition pyttsx3 pyaudio
```

On some systems, you may need additional packages:

### macOS
```bash
brew install portaudio
pip install pyaudio
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get install python3-pyaudio portaudio19-dev
```

### Windows
```bash
pip install pyaudio
```

## Setup

1. Set up your OpenAI API key in `.env`:
```
OPENAI_API_KEY=sk-your-key-here
```

2. Ensure you have a working microphone connected

3. Run the demo:
```bash
python voice_browser_demo.py
```

## Usage

### Wake Words
Start by saying one of the wake words:
- "Hey Suno Mirza"
- "Hey Browser"
- "Hey Assistant"

### Supported Commands

#### Navigation
- "Go to google.com"
- "Navigate to youtube"
- "Search for Python tutorials"
- "Go back"
- "Go forward"
- "Refresh"

#### Tab Management
- "Open new tab"
- "Close tab"
- "Switch to tab 2"

#### Page Interaction
- "Scroll down"
- "Scroll up"
- "Click on the search button"
- "Type hello world"

#### Email (when on email sites)
- "Compose email to john@example.com"
- "Reply to email"
- "Send email"

#### Control
- "Stop" / "Cancel" - Interrupt current action
- "Help" - Show available commands

### Chaining Commands
You can chain multiple commands:
- "Go to gmail and then compose email"
- "Search for news then scroll down"

## Programmatic Usage

```python
import asyncio
from langchain_openai import ChatOpenAI
from browser_use.voice import VoiceAgent, VoiceAgentConfig

async def main():
    llm = ChatOpenAI(model='gpt-4o')
    
    config = VoiceAgentConfig(
        wake_words=['hey browser'],
        enable_voice_feedback=True,
        continuous_mode=True,
    )
    
    agent = VoiceAgent(llm=llm, config=config)
    await agent.run()

asyncio.run(main())
```

## Configuration Options

```python
VoiceAgentConfig(
    # Wake word settings
    wake_words=['hey suno mirza', 'hey browser'],
    wake_word_sensitivity=0.7,
    
    # Voice settings
    language='en-US',
    speech_timeout=5.0,
    phrase_time_limit=15.0,
    
    # Feedback settings
    enable_voice_feedback=True,
    voice_feedback_rate=175,
    voice_feedback_volume=1.0,
    
    # Agent settings
    max_steps_per_command=50,
    use_vision=True,
    require_confirmation_for_destructive=True,
    
    # Continuous mode
    continuous_mode=True,
    auto_start_listening=True,
)
```

## Troubleshooting

### "No microphone found"
Ensure your microphone is connected and working. Test it with your system's audio settings.

### "Speech not understood"
- Speak clearly and at a normal pace
- Reduce background noise
- Adjust the `energy_threshold` in the configuration

### "Voice feedback not working"
Install pyttsx3: `pip install pyttsx3`

On Linux, you may also need:
```bash
sudo apt-get install espeak
```

### "PyAudio installation failed"
On macOS:
```bash
brew install portaudio
pip install pyaudio
```

On Linux:
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
```
