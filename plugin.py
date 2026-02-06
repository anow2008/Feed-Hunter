# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.SelectionList import SelectionList
from Components.NimManager import nimmanager
from enigma import eTimer
import re
import threading

try:
    import requests
except ImportError:
    requests = None

class FeedHunter(Screen):
    # سكين بسيط جداً يشتغل على كل الصور (HD & FHD)
    skin = """
    <screen position="center,center" size="800,500" title="Feed Hunter v1.4">
        <widget name="list" position="10,10" size="780,380" scrollbarMode="showOnDemand" />
        <widget name="status_label" position="10,400" size="780,40" font="Regular;22" halign="center" transparent="1" foregroundColor="#00FF00" />
        <widget name="hint_label" position="10,450" size="780,30" font="Regular;18" halign="left" transparent="1" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.feeds = []
        self["list"] = SelectionList([])
        self["status_label"] = Label("Starting...")
        self["hint_label"] = Label("RED: Close | GREEN: Reload | OK: Scan")
        
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.startScan,
            "cancel": self.close,
            "red": self.close,
            "green": self.reloadData
        }, -1)

        self.timer = eTimer()
        try:
            self.timer.timeout.connect(self.updateUI)
        except:
            self.timer.callback.append(self.updateUI)
            
        self.onLayoutFinish.append(self.reloadData)

    def reloadData(self):
        self["status_label"].setText("Fetching data... Please wait")
        self.feeds = []
        threading.Thread(target=self.fetchFeeds).start()

    def fetchFeeds(self):
        # محاكاة بيانات لو الموقع مقفول عشان نتأكد إن الشاشة شغالة
        test_feeds = []
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get("https://www.satelliweb.com/index.php?section=livef", timeout=10, headers=headers, verify=False)
            html = r.text
            
            # نمط بحث بسيط جداً
            pattern = r"(\d+\.\d°[EW]).*?(\d{5})\s+([HV])\s+(\d{4,5})"
            matches = re.findall(pattern, html, re.I)
            
            for (sat, freq, pol, sr) in matches:
                display = "Sat: %s | Freq: %s %s %s" % (sat, freq, pol, sr)
                test_feeds.append((display, {"freq": int(freq), "pol": pol, "sr": int(sr), "sat": sat}))
        except Exception as e:
            print("Error: ", str(e))
            
        self.feeds = test_feeds
        self.timer.start(100, True)

    def updateUI(self):
        self["list"].setList(self.feeds)
        if not self.feeds:
            self["status_label"].setText("No Data Found or Connection Error!")
        else:
            self["status_label"].setText("Found %d feeds" % len(self.feeds))

    def startScan(self):
        self["status_label"].setText("Scan feature triggered...")

def main(session, **kwargs):
    session.open(FeedHunter)

def Plugins(**kwargs):
    return PluginDescriptor(name="Feed Hunter", description="Satelliweb", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
