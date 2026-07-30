#!/bin/bash
#
# install.sh — creates a desktop entry for Funnel-Forge. That's all it
# does: no dependency installation, no build step. Run build.sh first
# if you want the entry to launch the compiled single binary; otherwise
# it falls back to launching main.py with python3.

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICON_PATH="$PROJECT_DIR/assets/funnel-forge.png"
BINARY_PATH="$PROJECT_DIR/dist/funnel-forge"
APPLICATIONS_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$APPLICATIONS_DIR/funnel-forge.desktop"

if [ -x "$BINARY_PATH" ]; then
    EXEC_LINE="$BINARY_PATH"
    echo "Found built binary - the launcher will use it: $BINARY_PATH"
else
    EXEC_LINE="/usr/bin/env python3 \"$PROJECT_DIR/main.py\""
    echo "No built binary found at dist/funnel-forge - the launcher will"
    echo "run 'python3 main.py' directly instead (run build.sh any time"
    echo "to switch it to the compiled binary)."
fi

mkdir -p "$APPLICATIONS_DIR"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=Funnel-Forge
Comment=Tailscale Funnel Manager
Exec=$EXEC_LINE
Path=$PROJECT_DIR
Icon=$ICON_PATH
Terminal=false
Categories=Utility;Network;
EOF

chmod +x "$DESKTOP_FILE"

# Refresh the desktop database if the tool is available (safe to skip if not).
command -v update-desktop-database > /dev/null 2>&1 && \
    update-desktop-database "$APPLICATIONS_DIR" > /dev/null 2>&1

echo "Desktop entry created: $DESKTOP_FILE"
echo "Funnel-Forge should now show up in your application launcher/menu."
