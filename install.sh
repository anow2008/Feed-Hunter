#!/bin/sh

# مسارات واضحة
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/FeedHunter"
URL="https://github.com/anow2008/Feed-Hunter/archive/refs/heads/main.tar.gz"

echo "------------------------------------------------"
echo "Starting Installation... Please Wait"
echo "------------------------------------------------"

# 1. تنظيف عميق
rm -rf "$PLUGIN_DIR"
rm -rf /tmp/fh_temp
mkdir -p /tmp/fh_temp

# 2. التحميل (wget بتجاهل الشهادة)
echo "[+] Downloading..."
wget --no-check-certificate "$URL" -O /tmp/feed.tar.gz

if [ ! -f /tmp/feed.tar.gz ]; then
    echo "[-] Download failed!"
    exit 1
fi

# 3. فك الضغط في مجلد مؤقت
echo "[+] Extracting..."
tar -xzf /tmp/feed.tar.gz -C /tmp/fh_temp

# 4. البحث عن المجلد الحقيقي (الضربة القاضية)
# بندور على المجلد اللي جواه ملف plugin.py فعلياً
REAL_PATH=$(find /tmp/fh_temp -name "plugin.py" | head -n 1 | xargs dirname)

if [ -z "$REAL_PATH" ]; then
    echo "[-] Could not find plugin.py inside the archive!"
    rm -rf /tmp/fh_temp /tmp/feed.tar.gz
    exit 1
fi

# 5. نقل الملفات للمسار الصحيح
echo "[+] Found files at: $REAL_PATH"
mkdir -p "$PLUGIN_DIR"
cp -r "$REAL_PATH"/* "$PLUGIN_DIR/"

# 6. صلاحيات وتنظيف
echo "[+] Setting permissions..."
chmod -R 755 "$PLUGIN_DIR"
rm -rf /tmp/fh_temp /tmp/feed.tar.gz

# 7. ريستارت "غصب عن التخين"
echo "[+] Success! Restarting Enigma2..."
sync
killall -9 enigma2
init 3
