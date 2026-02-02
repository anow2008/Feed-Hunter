# Feed-Hunter
wget -qO- https://raw.githubusercontent.com/anow2008/Feed-Hunter/main/install.sh | sh

rm -rf /usr/lib/enigma2/python/Plugins/Extensions/FeedHunter && find /usr/lib/enigma2/python/Plugins/Extensions/ -name "__pycache__" -type d -exec rm -rf {} + && killall -9 enigma2

