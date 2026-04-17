#!/bin/sh

# مسارات واضحة ومباشرة
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/FeedHunter"
URL="https://github.com/anow2008/Feed-Hunter/archive/refs/heads/main.tar.gz"

echo "Starting..."

# 1. مسح شامل لأي حاجة قديمة عشان ميعلقش
rm -rf "$PLUGIN_DIR"
rm -rf /tmp/Feed-Hunter-main
rm -f /tmp/main.tar.gz

# 2. التحميل مع تجاهل الشهادات تماماً وبأمر مباشر
cd /tmp
wget --no-check-certificate "$URL" -O main.tar.gz

# 3. التأكد إن الملف نزل فعلاً قبل ما نكمل
if [ ! -f main.tar.gz ]; then
    echo "Download Failed! Check Internet."
    killall -9 enigma2 # حتى لو فشل خليه يعمل ريستارت عشان تشوف إنه شغال
    exit 1
fi

# 4. فك الضغط
tar -xzf main.tar.gz

# 5. نقل المجلد (بالمسار اللي شفناه في المستودع بتاعك)
mkdir -p "$PLUGIN_DIR"
if [ -d "Feed-Hunter-main/FeedHunter" ]; then
    cp -r Feed-Hunter-main/FeedHunter/* "$PLUGIN_DIR/"
else
    cp -r Feed-Hunter-main/* "$PLUGIN_DIR/"
fi

# 6. صلاحيات ومسح كاش
chmod -R 755 "$PLUGIN_DIR"
find "$PLUGIN_DIR" -name "*.pyc" -delete

# 7. ريستارت "غصب" (Force)
echo "Done. Rebooting Enigma2..."
sync
killall -9 enigma2
init 3
