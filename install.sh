#!/bin/sh
# ==============================================
# Feed-Hunter Targeted Installer for anow2008
# ==============================================

PLUGIN_NAME="FeedHunter"
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/$PLUGIN_NAME"
URL="https://github.com/anow2008/Feed-Hunter/archive/refs/heads/main.zip"

echo "----------------------------------------------"
echo "Installing Feed-Hunter for Mohamed..."
echo "----------------------------------------------"

# 1. تنظيف قديم وتحميل
rm -rf "$PLUGIN_DIR" /tmp/fh_extract
mkdir -p /tmp/fh_extract
wget --no-check-certificate "$URL" -O /tmp/fh.zip

# 2. فك الضغط
unzip -o /tmp/fh.zip -d /tmp/fh_extract

# 3. النقل الذكي (هنا التعديل اللي هيحلك المشكلة)
# إحنا هندخل جوه المجلد المزدوج وناخد الملفات اللي جواه
if [ -d "/tmp/fh_extract/Feed-Hunter-main/FeedHunter" ]; then
    cp -r /tmp/fh_extract/Feed-Hunter-main/FeedHunter/* "$PLUGIN_DIR/"
    echo "[+] Files moved successfully to Extensions/$PLUGIN_NAME"
else
    # حل احتياطي لو غيرت اسم المجلد
    SOURCE=$(find /tmp/fh_extract -name "plugin.py" | head -n 1 | xargs dirname)
    cp -r "$SOURCE"/* "$PLUGIN_DIR/"
fi

# 4. التأكد من الملفات الأساسية والصلاحيات
[ ! -f "$PLUGIN_DIR/__init__.py" ] && touch "$PLUGIN_DIR/__init__.py"
chmod -R 755 "$PLUGIN_DIR"

# 5. تنظيف
rm -rf /tmp/fh.zip /tmp/fh_extract

# 6. تثبيت المكتبات (عشان البلجن يشتغل مش بس يظهر)
echo "[+] Installing dependencies..."
opkg update > /dev/null
opkg install python3-requests python3-beautifulsoup4 python3-six > /dev/null 2>&1

echo "----------------------------------------------"
echo "Done! Restarting Enigma2 now..."
echo "----------------------------------------------"

killall -9 enigma2
