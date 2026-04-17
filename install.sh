#!/bin/sh
# ==========================================
#  Feed-Hunter Smart Installer (Forced Fix)
#  Author : anow2008
# ==========================================

PLUGIN="FeedHunter"
BASE_DIR="/usr/lib/enigma2/python/Plugins/Extensions"
TARGET="$BASE_DIR/$PLUGIN"
ZIP_URL="https://github.com/anow2008/Feed-Hunter/archive/refs/heads/main.tar.gz"
LOG="/tmp/feedhunter_install.log"

echo "🔧 Starting Forced Installation..." | tee $LOG

# دالة الريستارت القوية جداً
force_restart() {
    echo "▶ Rebooting Enigma2 UI..."
    killall -9 enigma2 > /dev/null 2>&1
    init 3 > /dev/null 2>&1
}

# 1. تنظيف شامل
rm -rf "$TARGET"
rm -rf /tmp/fh_work
rm -f /tmp/main.tar.gz
mkdir -p /tmp/fh_work

# 2. التحميل
echo "⬇ Downloading..."
wget --no-check-certificate -O /tmp/main.tar.gz "$ZIP_URL" >> $LOG 2>&1

# 3. فك الضغط في مجلد مؤقت
echo "📦 Extracting..."
tar -xzf /tmp/main.tar.gz -C /tmp/fh_work || exit 1

# 4. البحث الذكي عن الملفات (هنا الحل)
# السطر ده بيدور على ملف plugin.py في أي مكان جوه الملف اللي نزل
REAL_SRC=$(find /tmp/fh_work -name "plugin.py" | head -n 1 | xargs dirname)

if [ -z "$REAL_SRC" ]; then
    echo "❌ ERROR: Could not find plugin.py!" | tee -a $LOG
    force_restart
    exit 1
fi

echo "✅ Found files at: $REAL_SRC" | tee -a $LOG

# 5. النقل للمسار النهائي
mkdir -p "$TARGET"
cp -r "$REAL_SRC"/* "$TARGET/"

# 6. الصلاحيات وتنظيف الكاش
chmod -R 755 "$TARGET"
find "$TARGET" -name "*.pyc" -delete
touch "$TARGET/__init__.py"

# 7. تثبيت المكتبات (مهمة جداً لظهور البلجن)
echo "📚 Installing dependencies..."
opkg update > /dev/null
opkg install python3-requests python3-beautifulsoup4 > /dev/null 2>&1

# 8. الريستارت الإجباري
echo "✅ Finished. Restarting..."
sync
force_restart

echo "================================="
echo " Done! Check your plugin list."
echo "================================="
