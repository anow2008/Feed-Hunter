#!/bin/sh
PLUGIN_NAME="FeedHunter"
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/$PLUGIN_NAME"
URL="https://github.com/anow2008/Feed-Hunter/archive/refs/heads/main.zip"

echo "[+] Forced Cleaning..."
rm -rf "$PLUGIN_DIR"
rm -f /tmp/fh.zip
mkdir -p "$PLUGIN_DIR"

echo "[+] Downloading & Extracting..."
wget --no-check-certificate "$URL" -O /tmp/fh.zip
unzip -o /tmp/fh.zip -d /tmp/

# النقل المباشر من المجلد الفرعي
cp -r /tmp/Feed-Hunter-main/FeedHunter/* "$PLUGIN_DIR/"

echo "[+] Fixing Permissions & Bytecode..."
# مسح أي ملفات بايثون قديمة مجمعة ممكن تسبب تعارض
find "$PLUGIN_DIR" -name "*.pyc" -delete
find "$PLUGIN_DIR" -name "*.pyo" -delete
chmod -R 755 "$PLUGIN_DIR"

# التأكد من وجود ملف التعريف
touch "$PLUGIN_DIR/__init__.py"

echo "[+] Installing Required Libraries..."
opkg update
opkg install python3-requests python3-beautifulsoup4 python3-xml python3-html

echo "[+] Checking for errors..."
python3 -m py_compile "$PLUGIN_DIR/plugin.py"

echo "[+] Restarting Enigma2..."
killall -9 enigma2
