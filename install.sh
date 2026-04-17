#!/bin/sh

PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/FeedHunter"
URL="https://github.com/anow2008/Feed-Hunter/archive/refs/heads/main.zip"

echo "[+] Starting Deep Clean..."
rm -rf "$PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR"

echo "[+] Downloading & Re-arranging..."
wget --no-check-certificate "$URL" -O /tmp/fh.zip
unzip -o /tmp/fh.zip -d /tmp/
cp -r /tmp/Feed-Hunter-main/FeedHunter/* "$PLUGIN_DIR/"

echo "[+] Installing ALL potential dependencies..."
opkg update
opkg install python3-requests python3-beautifulsoup4 python3-six python3-json python3-netclient python3-core

echo "[+] Fixing Bytecode..."
find "$PLUGIN_DIR" -name "*.pyc" -delete
chmod -R 755 "$PLUGIN_DIR"

echo "[+] Testing Plugin Logic..."
python3 -m py_compile "$PLUGIN_DIR/plugin.py" 2>&1 | tee /tmp/fh_error.log

if [ -s /tmp/fh_error.log ]; then
    echo "--- !!! ERROR DETECTED IN CODE !!! ---"
    cat /tmp/fh_error.log
else
    echo "[+] Code seems OK. Restarting..."
    killall -9 enigma2
fi
