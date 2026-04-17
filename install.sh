#!/bin/sh
# ==============================================
# Feed-Hunter Ultimate One-Line Installer (Optimized)
# ==============================================

PLUGIN_NAME="FeedHunter"
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/$PLUGIN_NAME"
REMOTE_REPO="https://github.com/anow2008/Feed-Hunter"
LOG_FILE="/tmp/feedhunter_install.log"

echo "=============================================="
echo " Feed-Hunter Installer Started"
echo "==============================================" | tee -a "$LOG_FILE"

# ---- تحديث الفيد وتثبيت المكتبات الأساسية ----
echo "[+] Updating system feeds & installing dependencies..." | tee -a "$LOG_FILE"
opkg update
opkg install python3-requests python3-six python3-beautifulsoup4 python3-xml python3-html || \
opkg install python-requests python-six python-beautifulsoup4 python-xml python-html

# ---- تحديد نسخة بايثون للتأكد ----
PYTHON_VER=$(python -c 'import sys; print(sys.version_info[0])' 2>/dev/null)
PY_PREFIX=$([ "$PYTHON_VER" = "3" ] && echo "python3" || echo "python")

# ---- فحص وتثبيت المكتبات المطلوبة للتأكيد فقط ----
echo "[+] Double checking dependencies for $PY_PREFIX..." | tee -a "$LOG_FILE"
for pkg in requests bs4 six; do
    if ! $PY_PREFIX -c "import $pkg" 2>/dev/null; then
        echo "[!] $pkg missing. Trying to install $PY_PREFIX-$pkg..." | tee -a "$LOG_FILE"
        opkg install $PY_PREFIX-$pkg
    fi
done

# ---- تنظيف المجلد القديم ----
echo "[+] Preparing installation directory..." | tee -a "$LOG_FILE"
[ -d "$PLUGIN_DIR" ] && rm -rf "$PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR"

# ---- تحميل وتثبيت البلجن ----
if command -v git >/dev/null 2>&1; then
    echo "[+] Installing via Git..." | tee -a "$LOG_FILE"
    git clone "$REMOTE_REPO" "$PLUGIN_DIR"
else
    echo "[+] Git not found, using ZIP method..." | tee -a "$LOG_FILE"
    TMP_ZIP="/tmp/feedhunter.zip"
    # تحميل الملف مع تخطي فحص الشهادة لضمان التحميل
    wget --no-check-certificate -q "$REMOTE_REPO/archive/refs/heads/main.zip" -O "$TMP_ZIP"
    
    if [ -f "$TMP_ZIP" ]; then
        unzip -o "$TMP_ZIP" -d /tmp >/dev/null
        # التأكد من نقل الملفات سواء كان المجلد اسمه Feed-Hunter-main أو غيره
        SOURCE_DIR=$(ls -d /tmp/Feed-Hunter-* 2>/dev/null)
        if [ -d "$SOURCE_DIR" ]; then
            cp -r "$SOURCE_DIR"/* "$PLUGIN_DIR"
            rm -rf "$SOURCE_DIR"
        fi
        rm -f "$TMP_ZIP"
    else
        echo "[!] Failed to download the plugin. Check your internet connection." | tee -a "$LOG_FILE"
        exit 1
    fi
fi

# ---- ضبط الصلاحيات (مهم جداً للتشغيل) ----
echo "[+] Setting permissions (755)..." | tee -a "$LOG_FILE"
chmod -R 755 "$PLUGIN_DIR"

# ---- الانتهاء وعمل ريستارت ----
echo "==============================================" | tee -a "$LOG_FILE"
echo "[+] Installation completed successfully." | tee -a "$LOG_FILE"
echo "[+] Log saved at: $LOG_FILE"
echo "[+] Restarting Enigma2..." | tee -a "$LOG_FILE"
echo "==============================================" | tee -a "$LOG_FILE"

sleep 3

# إعادة تشغيل الواجهة (Enigma2)
if [ -f /usr/bin/enigma2 ]; then
    killall -9 enigma2
else
    init 4 && sleep 2 && init 3
fi
