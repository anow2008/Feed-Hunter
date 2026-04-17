#!/bin/sh

# مسح شامل
rm -rf /usr/lib/enigma2/python/Plugins/Extensions/FeedHunter
rm -f /tmp/main.tar.gz

# التحميل باستخدام -k لتخطي أخطاء الشهادات في الصور القديمة
echo "Downloading..."
curl -Lk "https://github.com/anow2008/Feed-Hunter/archive/refs/heads/main.tar.gz" -o /tmp/main.tar.gz

# لو curl مش موجود، هيجرب wget بطريقة تانية
if [ ! -s /tmp/main.tar.gz ]; then
    wget --no-check-certificate "https://github.com/anow2008/Feed-Hunter/archive/refs/heads/main.tar.gz" -O /tmp/main.tar.gz
fi

# فك الضغط والنقل
cd /tmp
tar -xzf main.tar.gz
mkdir -p /usr/lib/enigma2/python/Plugins/Extensions/FeedHunter
cp -r Feed-Hunter-main/FeedHunter/* /usr/lib/enigma2/python/Plugins/Extensions/FeedHunter/

# صلاحيات
chmod -R 755 /usr/lib/enigma2/python/Plugins/Extensions/FeedHunter

# ريستارت "نووي"
echo "Restarting..."
sync
killall -9 enigma2
