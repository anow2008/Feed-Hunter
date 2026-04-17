#!/bin/sh
# ==============================================
# Feed-Hunter ZIP Installer & Path Fixer
# ==============================================

PLUGIN_NAME="FeedHunter"
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/$PLUGIN_NAME"
REMOTE_REPO="https://github.com/anow2008/Feed-Hunter/archive/refs/heads/main.zip"
TMP_ZIP="/tmp/feedhunter.zip"
TMP_EXTRACT="/tmp/fh_temp"

echo "=============================================="
echo " Installing $PLUGIN_NAME from ZIP..."
echo "=============================================="

# 1. تنظيف أي مخلفات قديمة
rm -rf "$PLUGIN_DIR"
rm -rf "$TMP_EXTRACT"
mkdir -p "$TMP_EXTRACT"

# 2. تحميل ملف الـ ZIP
echo "[+] Downloading ZIP file..."
wget --no-check-certificate -q "$REMOTE_REPO" -O "$TMP_ZIP"

if [ ! -f "$TMP_ZIP" ]; then
    echo "[!] Failed to download ZIP. Check internet connection."
    exit 1
fi

# 3. فك الضغط
echo "[+] Extracting..."
unzip -o "$TMP_ZIP" -d "$TMP_EXTRACT" > /dev/null

# 4. تحديد مكان المجلد المستخرج (عشان نتجنب مشكلة اسم -main)
# بندور على أول مجلد جواه ملف اسمه plugin.py
REAL_PATH=$(find "$TMP_EXTRACT" -name "plugin.py" | head -n 1 | xargs dirname)

if [ -z "$REAL_PATH" ]; then
    echo "[!] Could not find plugin files inside the ZIP!"
    rm -rf "$TMP_EXTRACT" "$TMP_ZIP"
    exit 1
fi

# 5. نقل الملفات للمسار الصحيح
echo "[+] Moving files to $PLUGIN_DIR..."
mkdir -p "$PLUGIN_DIR"
cp -r "$REAL_PATH"/* "$PLUGIN_DIR/"

# 6. التأكد من ملف الـ __init__.py عشان البلجن يظهر
[ ! -f "$PLUGIN_DIR/__init__.py" ] && touch "$PLUGIN_DIR/__init__.py"

# 7. ضبط الصلاحيات
chmod -R 755 "$PLUGIN_DIR"

# 8. تنظيف المؤقت
rm -rf "$TMP_EXTRACT" "$TMP_ZIP"

# 9. ريستارت الإنيجما
echo "[+] Installation finished. Restarting Enigma2..."
if [ -f /usr/bin/enigma2 ]; then
    killall -9 enigma2
else
    init 4 && sleep 2 && init 3
fi
