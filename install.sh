#!/bin/sh
# ==============================================
# Feed-Hunter Ultimate One-Line Installer
# ==============================================

PLUGIN_NAME="FeedHunter"
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/$PLUGIN_NAME"
REMOTE_REPO="https://github.com/anow2008/Feed-Hunter"
LOG_FILE="/tmp/feedhunter_install.log"

# توجيه المخرجات للملف وللشاشة
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=============================================="
echo " Feed-Hunter Installer Started"
echo "=============================================="

# ---- تحديث الفيد وتثبيت المكتبات (طلبك هنا) ----
echo "[+] Updating system feeds & installing Python3-Requests..."
opkg update
opkg install python3-requests python3-six python3-beautifulsoup4

# ---- تحديد نسخة بايثون للتأكد ----
PYTHON_VER=$(python -c 'import sys; print(sys.version_info[0])' 2>/dev/null)
PY_PREFIX=$([ "$PYTHON_VER" = "3" ] && echo "python3" || echo "python")

# ---- فحص وتثبيت المكتبات المطلوبة للتأكيد فقط ----
echo "[+] Double checking system dependencies..."
for pkg in requests bs4; do
    if ! $PY_PREFIX -c "import $pkg" 2>/dev/null; then
        echo "[!] $pkg still missing. Trying to force install..."
        opkg install $PY_PREFIX-$pkg
    fi
done

# ---- تثبيت أو تحديث البلجن ----
echo "[+] Installing / Updating $PLUGIN_NAME..."
[ -d "$PLUGIN_DIR" ] && rm -rf "$PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR"

if command -v git >/dev/null 2>&1; then
    echo "[+] Fresh install via Git..."
    git clone "$REMOTE_REPO" "$PLUGIN_DIR" || exit 1
else
    echo "[+] Git not found, using ZIP method..."
    TMP_ZIP="/tmp/feedhunter.zip"
    wget --no-check-certificate -q "$REMOTE_REPO/archive/refs/heads/main.zip" -O "$TMP_ZIP" || exit 1
    unzip -o "$TMP_ZIP" -d /tmp >/dev/null 2>&1
    
    # نقل الملفات بعد فك الضغط
    if [ -d "/tmp/Feed-Hunter-main" ]; then
        cp -r /tmp/Feed-Hunter-main/* "$PLUGIN_DIR"
        rm -rf /tmp/Feed-Hunter-main
    fi
    rm -f "$TMP_ZIP"
fi

# ---- الصلاحيات ----
echo "[+] Setting permissions..."
chmod -R 755 "$PLUGIN_DIR"

# ---- ريستارت الإنيجما ----
echo "[+] Installation completed."
echo "[+] Restarting Enigma2 to apply changes..."
sleep 2
killall -9 enigma2

echo "=============================================="
echo " Log saved at: $LOG_FILE"
echo "=============================================="
