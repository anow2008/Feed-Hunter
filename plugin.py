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

# مصدر جديد أسهل في السحب
URL = "https://www.live-feeds.com/"

def satToOrbital(txt):
    try:
        # تحويل صيغ مثل 7E أو 10.0W إلى رقم مداري للإنجما
        m = re.search(r"(\d+\.?\d*)\s*°?\s*([EW])", str(txt), re.I)
        if not m: return 0
        pos = float(m.group(1))
        direction = m.group(2).upper()
        return int((360 - pos) * 10) if direction == 'W' else int(pos * 10)
    except: return 0

class FeedHunter(Screen):
    skin = """
    <screen position="center,center" size="850,550" title="Feed Hunter v1.5 - New Source">
        <widget name="list" position="10,10" size="830,420" scrollbarMode="showOnDemand" />
        <widget name="status_label" position="10,440" size="830,40" font="Regular;24" halign="center" foregroundColor="#00FF00" />
        <widget name="hint_label" position="10,490" size="830,30" font="Regular;18" halign="left" transparent="1" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.feeds = []
        self["list"] = SelectionList([])
        self["status_label"] = Label("Connecting...")
        self["hint_label"] = Label("RED: Close | GREEN: Reload | OK: Scan")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.startScan, "cancel": self.close, "red": self.close, "green": self.reloadData
        }, -1)
        self.timer = eTimer()
        try: self.timer.timeout.connect(self.updateUI)
        except: self.timer.callback.append(self.updateUI)
        self.onLayoutFinish.append(self.reloadData)

    def reloadData(self):
        self["status_label"].setText("Fetching feeds from Live-Feeds...")
        self.feeds = []
        threading.Thread(target=self.fetchFeeds).start()

    def fetchFeeds(self):
        new_feeds = []
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            r = requests.get(URL, timeout=15, headers=headers, verify=False)
            html = r.text
            
            # نمط بحث يناسب الموقع الجديد
            # بيبحث عن الموقع المداري والتردد والقطبية ومعدل الترميز في جدول الموقع
            pattern = r"(\d+\.?\d*°[EW]).*?(\d{5})\s+([HV])\s+(\d{4,5})"
            matches = re.findall(pattern, html, re.S)

            for (sat, freq, pol, sr) in matches:
                display = "Sat: %s | %s %s %s" % (sat, freq, pol, sr)
                new_feeds.append((display, {
                    "freq": int(freq), "pol": pol.upper(),
                    "sr": int(sr), "orbital": satToOrbital(sat)
                }))
        except Exception as e:
            print("[FeedHunter] Error:", str(e))
            
        self.feeds = new_feeds
        self.timer.start(100, True)

    def updateUI(self):
        self["list"].setList(self.feeds)
        if not self.feeds:
            self["status_label"].setText("No feeds found. Try again later.")
        else:
            self["status_label"].setText("Found %d Active Feeds" % len(self.feeds))

    def startScan(self):
        item = self["list"].getCurrent()
        if not item: return
        f = item[1]
        tuner_slot = -1
        for slot in nimmanager.nim_slots:
            if slot.isCompatible("DVB-S2"):
                tuner_slot = slot.slot
                break
        if tuner_slot == -1: return

        tp = {
            "type": "S2", "frequency": f["freq"] * 1000, "symbol_rate": f["sr"] * 1000,
            "polarization": 0 if f["pol"] == "H" else 1, "fec_inner": 0,
            "system": 1, "modulation": 2, "inversion": 2, "roll_off": 3,
            "pilot": 2, "orbital_position": f["orbital"]
        }
        try:
            from Screens.ServiceScan import ServiceScan
            self.session.open(ServiceScan, tuner_slot, transponder=tp, scanList=[tp])
        except: pass

def main(session, **kwargs): session.open(FeedHunter)
def Plugins(**kwargs):
    return PluginDescriptor(name="Feed Hunter", description="Live-Feeds Scanner", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
