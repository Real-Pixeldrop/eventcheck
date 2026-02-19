#!/bin/bash
# EventCheck - Install script
# Usage: curl -sSL https://raw.githubusercontent.com/Real-Pixeldrop/eventcheck/main/install.sh | bash

set -e

INSTALL_DIR="$HOME/.eventcheck"
REPO="https://github.com/Real-Pixeldrop/eventcheck.git"

echo "🔍 Installing EventCheck..."

# Clone or update
if [ -d "$INSTALL_DIR" ]; then
    echo "   Updating existing installation..."
    cd "$INSTALL_DIR" && git pull --quiet
else
    echo "   Downloading..."
    git clone --quiet "$REPO" "$INSTALL_DIR"
fi

# Make scripts executable
chmod +x "$INSTALL_DIR/scripts/verify-event.py"
chmod +x "$INSTALL_DIR/scripts/search-events.sh"

# Create wrapper script
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/eventcheck" << 'EOF'
#!/bin/bash
python3 "$HOME/.eventcheck/scripts/verify-event.py" "$@"
EOF
chmod +x "$HOME/.local/bin/eventcheck"

# Add to PATH if needed
SHELL_RC="$HOME/.zshrc"
[ -f "$HOME/.bashrc" ] && [ ! -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.bashrc"

if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    echo "   Added ~/.local/bin to PATH in $SHELL_RC"
fi

echo ""
echo "✅ EventCheck installed!"
echo ""
echo "Usage:"
echo "   eventcheck <url>                    # Verify an event"
echo "   eventcheck <url> 2026-03-15         # Verify + check date"
echo ""
echo "Optional: Add your Eventbrite API key for double verification:"
echo "   mkdir -p ~/.config/eventbrite"
echo "   echo 'YOUR_TOKEN' > ~/.config/eventbrite/api_key"
echo ""
echo "Restart your terminal or run: source $SHELL_RC"
