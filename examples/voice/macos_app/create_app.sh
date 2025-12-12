#!/bin/bash
#
# Voice Browser - macOS App Builder
#
# This script creates a macOS .app bundle that can be double-clicked
# to start the voice-controlled browser.
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_NAME="Voice Browser"
APP_BUNDLE="$SCRIPT_DIR/$APP_NAME.app"

# Terminal colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║        Creating Voice Browser macOS Application                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Remove existing app bundle
if [ -d "$APP_BUNDLE" ]; then
    echo -e "${BLUE}Removing existing app bundle...${NC}"
    rm -rf "$APP_BUNDLE"
fi

# Store the absolute project root path for embedding in the app
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

# Create app bundle structure
echo -e "${BLUE}Creating app bundle structure...${NC}"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# Create the executable script with embedded project path
cat > "$APP_BUNDLE/Contents/MacOS/$APP_NAME" << LAUNCHER_EOF
#!/bin/bash
# Voice Browser Launcher
# Auto-generated with embedded project path

# Embedded project root path (set during app creation)
PROJECT_ROOT="$PROJECT_ROOT"

# Get the app bundle location
APP_DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )/../.." && pwd )"

# Verify project root exists, fall back to searching if not
if [ ! -f "\$PROJECT_ROOT/pyproject.toml" ]; then
    # Show error and offer to locate manually
    osascript -e 'display alert "Project Not Found" message "The browser-use project was not found at the expected location. Please ensure the project directory still exists at: $PROJECT_ROOT"'
    exit 1
fi

# Open Terminal and run the launcher
osascript << EOF
tell application "Terminal"
    activate
    do script "cd '\$PROJECT_ROOT/examples/voice/macos_app' && bash '\$PROJECT_ROOT/examples/voice/macos_app/launch_voice_browser.sh'"
end tell
EOF
LAUNCHER_EOF

chmod +x "$APP_BUNDLE/Contents/MacOS/$APP_NAME"

# Create Info.plist
cat > "$APP_BUNDLE/Contents/Info.plist" << 'PLIST_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Voice Browser</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.browseruse.voicebrowser</string>
    <key>CFBundleName</key>
    <string>Voice Browser</string>
    <key>CFBundleDisplayName</key>
    <string>Voice Browser</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>Voice Browser needs access to your microphone to listen for voice commands.</string>
    <key>NSSpeechRecognitionUsageDescription</key>
    <string>Voice Browser uses speech recognition to process your voice commands.</string>
</dict>
</plist>
PLIST_EOF

# Create a simple icon (using emoji as placeholder)
# In a real app, you would include a proper .icns file
echo -e "${BLUE}Creating placeholder icon...${NC}"

# Create iconset directory
ICONSET="$SCRIPT_DIR/AppIcon.iconset"
mkdir -p "$ICONSET"

# Create a simple PNG icon using Python (if available with PIL)
# Note: Pillow is optional - the app will work without a custom icon
python3 << 'ICON_PYTHON' 2>/dev/null || echo -e "${YELLOW}Note: App icon generation skipped (Pillow not installed - this is optional)${NC}"
import os
try:
    from PIL import Image, ImageDraw, ImageFont
    
    sizes = [16, 32, 64, 128, 256, 512]
    iconset_path = os.environ.get('ICONSET', 'AppIcon.iconset')
    
    for size in sizes:
        # Create image with gradient background
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw a circle with gradient-like colors
        for i in range(size//2, 0, -1):
            # Blue gradient
            r = int(30 + (100-30) * (1 - i/(size//2)))
            g = int(144 + (200-144) * (1 - i/(size//2)))
            b = int(255)
            draw.ellipse([size//2-i, size//2-i, size//2+i, size//2+i], fill=(r, g, b, 255))
        
        # Add microphone symbol (simple representation)
        center = size // 2
        mic_height = size // 3
        mic_width = size // 6
        
        # Microphone body
        draw.rectangle([
            center - mic_width//2, 
            center - mic_height//2,
            center + mic_width//2,
            center + mic_height//3
        ], fill=(255, 255, 255, 255))
        
        # Microphone top (rounded)
        draw.ellipse([
            center - mic_width//2,
            center - mic_height//2 - mic_width//2,
            center + mic_width//2,
            center - mic_height//2 + mic_width//2
        ], fill=(255, 255, 255, 255))
        
        # Save icons
        img.save(f'{iconset_path}/icon_{size}x{size}.png')
        img.save(f'{iconset_path}/icon_{size}x{size}@2x.png')
    
    print("Icons generated successfully!")
except ImportError:
    pass
ICON_PYTHON

# Try to create .icns file if iconutil is available
if [ -d "$ICONSET" ] && [ "$(ls -A $ICONSET)" ]; then
    iconutil -c icns "$ICONSET" -o "$APP_BUNDLE/Contents/Resources/AppIcon.icns" 2>/dev/null || true
fi

# Clean up iconset
rm -rf "$ICONSET"

# Copy the launcher script to the app bundle directory
cp "$SCRIPT_DIR/launch_voice_browser.sh" "$APP_BUNDLE/"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Voice Browser.app created successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "You can now:"
echo -e "  1. Double-click '${CYAN}Voice Browser.app${NC}' to launch"
echo -e "  2. Drag it to your ${CYAN}Applications${NC} folder"
echo -e "  3. Add it to your ${CYAN}Dock${NC} for quick access"
echo ""
echo -e "${BLUE}Location:${NC} $APP_BUNDLE"
echo ""

# Optionally open the folder in Finder
if [ "$1" != "--no-open" ]; then
    open "$SCRIPT_DIR"
fi
