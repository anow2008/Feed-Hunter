#!/bin/sh
# ==============================================
# Feed-Hunter Ultimate One-Line Installer
# ==============================================

PLUGIN_NAME="Feed-Hunter"
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/$PLUGIN_NAME"
REMOTE_REPO="https://github.com/anow2008/Feed-Hunter"
LOG_FILE="/tmp/feedhunter_install.log"

# توجيه المخرجات للملف وللشاشة
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=============================================="
echo " Feed-Hunter Installer Started"
echo "=============================================="

# ---- فحص الإنترنت ----
if ! ping -c 1 github.com >/dev/null 2>&1; then
    echo "[!] No internet connection. Aborting."
    exit 1
fi

# ---- تحديد نسخة بايثون ----
PYTHON_VER=$(python -c 'import sys; print(sys.version_info[0])' 2>/dev/null)
PY_PREFIX=$([ "$PYTHON_VER" = "3" ] && echo "python3" || echo "python")

# ---- فحص وتثبيت المكتبات المطلوبة فقط إذا نقصت ----
echo "[+] Checking system dependencies..."
NEEDS_INSTALL=false

# فحص requests
if ! $PY_PREFIX -c "import requests" 2>/dev/null; then
    echo "[!] $PY_PREFIX-requests missing."
    NEEDS_INSTALL=true
fi

# فحص beautifulsoup4
if ! $PY_PREFIX -c "import bs4" 2>/dev/null; then
    echo "[!] $PY_PREFIX-beautifulsoup4 missing."
    NEEDS_INSTALL=true
fi

if [ "$NEEDS_INSTALL" = true ]; then
    echo "[+] Installing missing libraries..."
    opkg update > /dev/null 2>&1
    opkg install $PY_PREFIX-requests $PY_PREFIX-beautifulsoup4
else
    echo "[+] All dependencies are already met. Skipping opkg update."
fi

# ---- تثبيت أو تحديث البلجن ----
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
    wget --no-check-certificate -q "$REMOTE_REPO/archive/refs/heads/main.zip" -O "$TMP_ZIP" || exit 1
    unzip -o "$TMP_ZIP" -d /tmp >/dev/null 2>&1
    rm -rf "$PLUGIN_DIR"
    mkdir -p "$PLUGIN_DIR"
    cp -r /tmp/Feed-Hunter-main/* "$PLUGIN_DIR"
    rm -rf /tmp/Feed-Hunter-main "$TMP_ZIP"
fi

# ---- الصلاحيات ----
echo "[+] Setting permissions..."
find "$PLUGIN_DIR" -type d -exec chmod 755 {} \;
find "$PLUGIN_DIR" -type f -exec chmod 644 {} \;
find "$PLUGIN_DIR" -type f -name "*.sh" -exec chmod 755 {} \;

# ---- ريستارت الإنيجما ----
echo "[+] Installation completed."
echo "[+] Restarting Enigma2 to apply changes..."
sleep 2
killall -9 enigma2

echo "=============================================="
echo " Log saved at: $LOG_FILE"
echo "=============================================="
