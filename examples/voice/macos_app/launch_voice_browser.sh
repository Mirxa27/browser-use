#!/bin/bash
#
# Voice Browser - macOS One-Click Launcher
# 
# This script starts the voice-controlled browser application.
# It handles virtual environment setup and dependency installation.
#

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

# Terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║           🎤 Voice-Controlled Browser for macOS 🌐               ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if Python 3.11+ is installed
check_python() {
    echo -e "${BLUE}Checking Python version...${NC}"
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
            echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
            return 0
        else
            echo -e "${RED}✗ Python 3.11+ required, found $PYTHON_VERSION${NC}"
            echo -e "${YELLOW}Please install Python 3.11+ from https://python.org${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Python 3 not found${NC}"
        echo -e "${YELLOW}Please install Python 3.11+ from https://python.org${NC}"
        return 1
    fi
}

# Check for Homebrew and portaudio (required for PyAudio on macOS)
check_audio_deps() {
    echo -e "${BLUE}Checking audio dependencies...${NC}"
    
    if command -v brew &> /dev/null; then
        echo -e "${GREEN}✓ Homebrew found${NC}"
        
        if brew list portaudio &> /dev/null; then
            echo -e "${GREEN}✓ PortAudio found${NC}"
        else
            echo -e "${YELLOW}Installing PortAudio...${NC}"
            brew install portaudio
        fi
    else
        echo -e "${YELLOW}⚠ Homebrew not found. You may need to install PortAudio manually.${NC}"
        echo -e "${YELLOW}  Install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"${NC}"
    fi
}

# Setup virtual environment
setup_venv() {
    VENV_DIR="$PROJECT_ROOT/.venv"
    
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${BLUE}Creating virtual environment...${NC}"
        python3 -m venv "$VENV_DIR"
    fi
    
    echo -e "${BLUE}Activating virtual environment...${NC}"
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip -q
}

# Install dependencies
install_deps() {
    echo -e "${BLUE}Installing dependencies...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Install the package with voice dependencies
    pip install -e ".[voice]" -q
    
    # Ensure PyAudio is installed (sometimes needs special handling on macOS)
    if ! pip install pyaudio -q 2>&1; then
        echo -e "${YELLOW}⚠ PyAudio installation failed.${NC}"
        echo -e "${YELLOW}  This usually means PortAudio is missing.${NC}"
        echo -e "${YELLOW}  Run: brew install portaudio${NC}"
        echo -e "${YELLOW}  Then try again.${NC}"
    fi
    
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

# Check for .env file
check_env() {
    ENV_FILE="$PROJECT_ROOT/.env"
    
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}⚠ .env file not found${NC}"
        echo -e "${BLUE}Creating .env file...${NC}"
        
        # Prompt for API key
        echo -e "${CYAN}Please enter your OpenAI API key (or press Enter to skip):${NC}"
        read -s API_KEY
        
        if [ -n "$API_KEY" ]; then
            echo "OPENAI_API_KEY=$API_KEY" > "$ENV_FILE"
            echo -e "${GREEN}✓ .env file created${NC}"
        else
            cp "$PROJECT_ROOT/.env.example" "$ENV_FILE" 2>/dev/null || echo "# Add your API keys here" > "$ENV_FILE"
            echo -e "${YELLOW}⚠ Please edit $ENV_FILE and add your OPENAI_API_KEY${NC}"
        fi
    else
        echo -e "${GREEN}✓ .env file found${NC}"
    fi
}

# Run the voice browser
run_voice_browser() {
    echo ""
    echo -e "${GREEN}Starting Voice Browser...${NC}"
    echo -e "${CYAN}Say 'Hey Suno Mirza' or 'Hey Browser' to activate!${NC}"
    echo ""
    
    cd "$PROJECT_ROOT"
    python examples/voice/voice_browser_demo.py
}

# Main function
main() {
    print_banner
    
    echo -e "${BLUE}Initializing Voice Browser...${NC}"
    echo ""
    
    # Run checks and setup
    check_python || exit 1
    check_audio_deps
    setup_venv
    install_deps
    check_env
    
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}                    Setup Complete!                            ${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    run_voice_browser
}

# Run main
main
