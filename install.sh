#!/bin/sh
# ==============================================
# Feed-Hunter Plugin Manager for Enigma2
# ==============================================

PLUGIN_NAME="Feed-Hunter"
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/$PLUGIN_NAME"
REMOTE_REPO="https://github.com/anow2008/Feed-Hunter"

echo "=============================================="
echo "Feed-Hunter Plugin Manager"
echo "1) Install / Update Plugin"
echo "2) Remove Plugin"
echo "=============================================="
read -p "Choose an option (1 or 2): " OPTION

install_plugin() {
    echo "Installing / Updating $PLUGIN_NAME..."
    mkdir -p "$PLUGIN_DIR"

    if command -v git >/dev/null 2>&1; then
        if [ -d "$PLUGIN_DIR/.git" ]; then
            echo "Updating existing Git repo..."
            cd "$PLUGIN_DIR" && git pull
        else
            echo "Cloning repository..."
            rm -rf "$PLUGIN_DIR"
            git clone "$REMOTE_REPO" "$PLUGIN_DIR"
        fi
    else
        echo "Git not found. Using ZIP download..."
        TMP_ZIP="/tmp/feedhunter.zip"
        wget -q "$REMOTE_REPO/archive/refs/heads/main.zip" -O "$TMP_ZIP"
        unzip -o "$TMP_ZIP" -d /tmp
        rm -rf "$PLUGIN_DIR"
        cp -r /tmp/Feed-Hunter-main/* "$PLUGIN_DIR"
    fi

    # ضبط الصلاحيات بشكل آمن
    find "$PLUGIN_DIR" -type d -exec chmod 755 {} \;
    find "$PLUGIN_DIR" -type f -exec chmod 644 {} \;

    echo "$PLUGIN_NAME installed/updated successfully!"
    echo "Restart Enigma2 or reload plugins to see it in the menu."
}

remove_plugin() {
    echo "Removing $PLUGIN_NAME plugin..."
    if [ -d "$PLUGIN_DIR" ]; then
        rm -rf "$PLUGIN_DIR"
        echo "$PLUGIN_NAME has been removed successfully."
        echo "Restart Enigma2 to apply changes."
    else
        echo "$PLUGIN_NAME is not installed."
    fi
}

case "$OPTION" in
    1) install_plugin ;;
    2) remove_plugin ;;
    *) echo "Invalid option. Exiting." ;;
esac
