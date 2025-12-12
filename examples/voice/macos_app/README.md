# Voice Browser - macOS One-Click Startup App

This folder contains everything you need to create a one-click macOS application for the voice-controlled browser.

## Quick Start

### Option 1: Create the App Bundle (Recommended)

Run the app builder script to create a proper macOS .app bundle:

```bash
cd examples/voice/macos_app
chmod +x create_app.sh
./create_app.sh
```

This will create a `Voice Browser.app` that you can:
- **Double-click** to launch the voice browser
- **Drag to Applications** folder for easy access
- **Add to Dock** for one-click startup

### Option 2: Direct Launch

If you prefer to run the launcher script directly:

```bash
cd examples/voice/macos_app
chmod +x launch_voice_browser.sh
./launch_voice_browser.sh
```

## Files

| File | Description |
|------|-------------|
| `create_app.sh` | Creates the macOS .app bundle |
| `launch_voice_browser.sh` | Main launcher script with dependency management |
| `README.md` | This documentation file |

## What the App Does

When you launch Voice Browser.app, it will:

1. **Check Python** - Ensures Python 3.11+ is installed
2. **Check Audio Dependencies** - Verifies/installs PortAudio via Homebrew
3. **Setup Virtual Environment** - Creates and activates a Python venv
4. **Install Dependencies** - Installs browser-use with voice support
5. **Check Configuration** - Prompts for OpenAI API key if not set
6. **Start Voice Browser** - Launches the voice-controlled browser

## Prerequisites

### Required
- **macOS 10.15+** (Catalina or later)
- **Python 3.11+** - Download from [python.org](https://python.org)
- **Microphone** - Built-in or external

### Recommended
- **Homebrew** - For easy installation of PortAudio
  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```

## First-Time Setup

1. **Install Homebrew** (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install PortAudio** (required for microphone access):
   ```bash
   brew install portaudio
   ```

3. **Run the app builder**:
   ```bash
   cd examples/voice/macos_app
   ./create_app.sh
   ```

4. **Set your API key**:
   - The app will prompt for your OpenAI API key on first run
   - Or create a `.env` file in the project root:
     ```
     OPENAI_API_KEY=sk-your-key-here
     ```

## Microphone Permissions

When you first run Voice Browser, macOS will ask for microphone permission:

1. Click **"OK"** when prompted
2. Go to **System Preferences > Privacy & Security > Microphone**
3. Ensure **Terminal** (or your terminal app) has microphone access

## Troubleshooting

### "Python not found"
Install Python 3.11+ from [python.org](https://python.org) or via Homebrew:
```bash
brew install python@3.11
```

### "PortAudio not found"
Install via Homebrew:
```bash
brew install portaudio
```

### "Microphone not detected"
1. Check System Preferences > Sound > Input
2. Ensure a microphone is selected
3. Check Privacy & Security permissions

### "PyAudio installation failed"
This usually means PortAudio isn't installed:
```bash
brew install portaudio
pip install pyaudio
```

### App won't open (security warning)
Right-click the app and select "Open", then click "Open" in the dialog.
Or go to System Preferences > Privacy & Security and allow the app.

## Adding to Dock

1. Double-click `Voice Browser.app` to open it
2. Right-click the app icon in the Dock
3. Select **Options > Keep in Dock**

## Adding to Login Items (Start on Boot)

1. Open **System Preferences > Users & Groups**
2. Select your user, then click **Login Items**
3. Click **+** and add `Voice Browser.app`

## Voice Commands

Once running, say **"Hey Suno Mirza"** or **"Hey Browser"** to activate, then:

| Command | Action |
|---------|--------|
| "Go to google.com" | Navigate to website |
| "Search for Python" | Search the web |
| "Scroll down" | Scroll the page |
| "Click on login" | Click an element |
| "Open new tab" | Open a new tab |
| "Close tab" | Close current tab |
| "Go back" | Navigate back |
| "Take screenshot" | Capture the page |
| "Stop" or "Cancel" | Interrupt action |
| "Help" | Show all commands |

## Architecture

```
Voice Browser.app
├── Contents/
│   ├── MacOS/
│   │   └── Voice Browser     # Executable launcher
│   ├── Resources/
│   │   └── AppIcon.icns      # App icon
│   └── Info.plist            # App metadata
└── launch_voice_browser.sh   # Main script
```

## Uninstalling

Simply delete `Voice Browser.app` and optionally the virtual environment:
```bash
rm -rf Voice\ Browser.app
rm -rf /path/to/browser-use/.venv
```
