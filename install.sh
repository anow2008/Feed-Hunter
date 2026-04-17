#!/bin/sh
# ==========================================
#  Feed-Hunter Online Installer (No Git)
#  Author : anow2008
# ==========================================

PLUGIN="FeedHunter"
BASE_DIR="/usr/lib/enigma2/python/Plugins/Extensions"
TARGET="$BASE_DIR/$PLUGIN"
# الرابط الصحيح لمستودع Feed-Hunter بصيغة tar.gz
ZIP_URL="https://github.com/anow2008/Feed-Hunter/archive/refs/heads/main.tar.gz"
LOG="/tmp/feedhunter_install.log"

echo "🔧 Feed-Hunter Installer Started" | tee $LOG

# --- Detect Python ---
if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
else
    PYTHON=python
fi

stop_enigma2() {
    echo "⏹ Stopping Enigma2..." | tee -a $LOG
    if command -v systemctl >/dev/null 2>&1; then
        systemctl stop enigma2
    else
        init 4
    fi
    sleep 2
}

start_enigma2() {
    echo "▶ Starting Enigma2..." | tee -a $LOG
    if command -v systemctl >/dev/null 2>&1; then
        systemctl start enigma2
    else
        init 3
    fi
}

install_plugin() {
    stop_enigma2

    mkdir -p "$BASE_DIR"
    cd /tmp || exit 1
    # تنظيف أي بقايا قديمة
    rm -rf Feed-Hunter-main main.tar.gz

    echo "⬇ Downloading plugin..." | tee -a $LOG
    if ! wget --no-check-certificate -O main.tar.gz "$ZIP_URL" >> $LOG 2>&1; then
        echo "❌ Download failed" | tee -a $LOG
        start_enigma2
        exit 1
    fi

    echo "📦 Extracting..." | tee -a $LOG
    tar -xzf main.tar.gz || {
        echo "❌ Extract failed" | tee -a $LOG
        start_enigma2
        exit 1
    }

    rm -rf "$TARGET"
    
    # التعديل الجوهري هنا: الدخول للمجلد المستخرج ثم نقل محتوى فولدر FeedHunter 
    # لأن مستودع Feed-Hunter جواه فولدر فرعي بنفس الاسم
    if [ -d "Feed-Hunter-main/FeedHunter" ]; then
        mv Feed-Hunter-main/FeedHunter "$TARGET"
        echo "✅ Moved internal FeedHunter folder to $TARGET" | tee -a $LOG
    else
        # حل احتياطي لو الملفات في الجذر مباشرة
        mv Feed-Hunter-main "$TARGET"
    fi

    chmod -R 755 "$TARGET"
    find "$TARGET" -name "*.pyc" -delete

    # التأكد من وجود ملف التعريف الأساسي
    [ ! -f "$TARGET/__init__.py" ] && touch "$TARGET/__init__.py"

    if [ -f "$TARGET/plugin.py" ]; then
        echo "⚙️ Compiling plugin..." | tee -a $LOG
        $PYTHON -m py_compile "$TARGET/plugin.py" >> $LOG 2>&1
    else
        echo "❌ plugin.py missing in $TARGET" | tee -a $LOG
    fi

    # تثبيت التبعيات الضرورية بصمت
    echo "📚 Checking dependencies..." | tee -a $LOG
    opkg update > /dev/null
    opkg install python3-requests python3-beautifulsoup4 > /dev/null 2>&1

    sync
    start_enigma2

    echo "================================="
    echo " ✅ Feed-Hunter Installed Successfully"
    echo " 📄 Log: $LOG"
    echo "================================="
}

install_plugin
exit 0
