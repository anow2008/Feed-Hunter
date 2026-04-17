#!/bin/sh

# مسارات
TARGET="/usr/lib/enigma2/python/Plugins/Extensions/FeedHunter"
URL="https://github.com/anow2008/Feed-Hunter/archive/refs/heads/main.zip"

echo "Checking System..."

# 1. تنظيف عميق جداً
rm -rf $TARGET
rm -rf /tmp/Feed-Hunter-main
rm -f /tmp/fh.zip

# 2. التحميل
echo "Downloading..."
wget --no-check-certificate "$URL" -O /tmp/fh.zip

# 3. فك الضغط
echo "Unzipping..."
unzip -o /tmp/fh.zip -d /tmp/

# 4. النقل الذكي (هنا القفلة)
# هندور على الفولدر اللي جواه plugin.py وننقله مهما كان مكانه
SOURCE_PATH=$(find /tmp/Feed-Hunter-main -name "plugin.py" | head -n 1 | xargs dirname)

if [ -n "$SOURCE_PATH" ]; then
    echo "Found plugin at $SOURCE_PATH, moving..."
    mkdir -p $TARGET
    cp -rp "$SOURCE_PATH"/. $TARGET/
else
    echo "Plugin files not found in /tmp!"
fi

# 5. الصلاحيات
chmod -R 755 $TARGET

# 6. الريستارت الإجباري (بأكثر من طريقة)
echo "Forcing Restart..."
sync
# جرب يرستر الواجهة
killall -9 enigma2
# لو منفعش، جرب يرستر الجهاز كله بعد 3 ثواني
sleep 3
reboot
