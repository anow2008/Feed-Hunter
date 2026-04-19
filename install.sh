#!/bin/sh
# Feed Hunter Installer - Created by Muhammad

# المسارات
PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/FeedHunter"
GITHUB_RAW="https://raw.githubusercontent.com/anow2008/Feed-Hunter/main"

echo "> جاري تثبيت بلجن Feed Hunter..."

# حذف النسخة القديمة إن وجدت لضمان تحديث نظيف
rm -rf $PLUGIN_PATH
mkdir -p $PLUGIN_PATH

# تحميل الملفات الأساسية
echo "> جاري تحميل الملفات من المستودع..."
wget --no-check-certificate "$GITHUB_RAW/plugin.py" -O "$PLUGIN_PATH/plugin.py"
wget --no-check-certificate "$GITHUB_RAW/__init__.py" -O "$PLUGIN_PATH/__init__.py"

# تأكد من إضافة أي ملفات أخرى (مثل الصور أو ملفات الـ XML) هنا بنفس الطريقة
# wget --no-check-certificate "$GITHUB_RAW/key.png" -O "$PLUGIN_PATH/key.png"

# إعطاء صلاحيات التشغيل
chmod -R 755 $PLUGIN_PATH

echo "> تم التثبيت بنجاح في: $PLUGIN_PATH"
echo "> جاري إعادة تشغيل Enigma2 لتفعيل البلجن..."

# إعادة تشغيل الواجهة
init 4
sleep 2
init 3

exit 0
