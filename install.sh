#!/bin/sh
# ==============================================
# Feed-Hunter Ultimate One-Line Installer
# ==============================================

PLUGIN_NAME="Feed-Hunter"
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/$PLUGIN_NAME"
REMOTE_REPO="https://github.com/anow2008/Feed-Hunter"
LOG_FILE="/tmp/feedhunter_install.log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "=============================================="
echo " Feed-Hunter Installer Started"
echo "=============================================="

# ---- Check internet ----
echo "[+] Checking internet connection..."
if ! ping -c 1 github.com >/dev/null 2>&1; then
    echo "[!] No internet connection. Aborting."
    exit 1
fi

# ---- Detect image ----
IMAGE="Unknown"
[ -f /etc/image-version ] && IMAGE=$(grep -i "distro" /etc/image-version | cut -d= -f2)
[ -z "$IMAGE" ] && IMAGE=$(cat /etc/issue 2>/dev/null | head -n1)

echo "[+] Detected Image: $IMAGE"

echo "[+] Installing / Updating $PLUGIN_NAME..."

mkdir -p "$PLUGIN_DIR"

if command -v git >/dev/null 2>&1; then
    if [ -d "$PLUGIN_DIR/.git" ]; then
        echo "[+] Updating existing plugin..."
        cd "$PLUGIN_DIR" && git pull || exit 1
    else
        echo "[+] Fresh install via Git..."
        rm -rf "$PLUGIN_DIR"
        git clone "$REMOTE_REPO" "$PLUGIN_DIR" || exit 1
    fi
else
    echo "[+] Git not found, using ZIP method..."
    TMP_ZIP="/tmp/feedhunter.zip"
    wget -q "$REMOTE_REPO/archive/refs/heads/main.zip" -O "$TMP_ZIP" || exit 1
    unzip -o "$TMP_ZIP" -d /tmp >/dev/null 2>&1
    rm -rf "$PLUGIN_DIR"
    mkdir -p "$PLUGIN_DIR"
    cp -r /tmp/Feed-Hunter-main/* "$PLUGIN_DIR"
    rm -rf /tmp/Feed-Hunter-main "$TMP_ZIP"
fi

# ---- Permissions ----
echo "[+] Setting permissions..."
find "$PLUGIN_DIR" -type d -exec chmod 755 {} \;
find "$PLUGIN_DIR" -type f -exec chmod 644 {} \;
find "$PLUGIN_DIR" -type f -name "*.sh" -exec chmod 755 {} \;

# ---- Restart Enigma2 ----
echo "[+] Restarting Enigma2..."
sleep 2
init 4
sleep 3
init 3

echo "=============================================="
echo " Installation completed successfully"
echo " Log saved at: $LOG_FILE"
echo "=============================================="
