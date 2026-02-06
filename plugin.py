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
except:
    requests = None

class FeedHunter(Screen):
    skin = """
    <screen position="center,center" size="900,600" title="Feed Hunter v1.6 - Multi-Source">
        <widget name="list" position="10,10" size="880,480" scrollbarMode="showOnDemand" />
        <widget name="status_label" position="10,500" size="880,40" font="Regular;24" halign="center" foregroundColor="#00FF00" />
        <widget name="hint_label" position="10,550" size="880,30" font="Regular;20" halign="left" transparent="1" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.feeds = []
        self["list"] = SelectionList([])
        self["status_label"] = Label("Searching in multiple sources...")
        self["hint_label"] = Label("RED: Exit | GREEN: Reload | OK: Scan Selected")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.startScan, "cancel": self.close, "red": self.close, "green": self.reloadData
        }, -1)
        self.timer = eTimer()
        try: self.timer.timeout.connect(self.updateUI)
        except: self.timer.callback.append(self.updateUI)
        self.onLayoutFinish.append(self.reloadData)

    def reloadData(self):
        self["status_label"].setText("Scanning Satelliweb/LiveFeeds via Proxy...")
        self.feeds = []
        threading.Thread(target=self.fetchFeeds).start()

    def fetchFeeds(self):
        new_feeds = []
        # مصفوفة الروابط (هنحاول في كذا مكان)
        urls = [
            "https://www.satelliweb.com/index.php?section=livef",
            "https://www.live-feeds.com/",
            "http://api.satelliweb.com/feeds.php" # محاولة لرابط API قديم
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
        }

        for url in urls:
            try:
                r = requests.get(url, timeout=10, headers=headers, verify=False)
                html = r.text
                
                # البحث عن الترددات بنمط "المنقذ" (بيجيب أي 5 أرقام جنبهم H أو V)
                # صيغة: 12.5 W 11500 H 7200
                pattern = r"(\d+\.?\d*°?[EW]?)\s.*?(\d{5})\s+([HV])\s+(\d{4,5})"
                matches = re.findall(pattern, html, re.I | re.S)

                for (sat, freq, pol, sr) in matches:
                    sat_clean = sat.replace("°", "").strip()
                    display = "Sat: %s | %s %s %s" % (sat_clean, freq, pol, sr)
                    
                    # تحويل الموقع المداري لرقم يفهمه التيونر
                    m_pos = re.search(r"(\d+\.?\d*)", sat_clean)
                    m_dir = re.search(r"([EW])", sat_clean, re.I)
                    pos = float(m_pos.group(1)) if m_pos else 0
                    direction = m_dir.group(1).upper() if m_dir else 'E'
                    orb = int((360 - pos) * 10) if direction == 'W' else int(pos * 10)

                    new_feeds.append((display, {"freq": int(freq), "pol": pol.upper(), "sr": int(sr), "orb": orb}))
                
                if new_feeds: break # لو لقينا في أول رابط خلاص نكتفي بيه
            except:
                continue
            
        self.feeds = new_feeds
        self.timer.start(100, True)

    def updateUI(self):
        self["list"].setList(self.feeds)
        if not self.feeds:
            self["status_label"].setText("Site Blocked! Try again or check Internet.")
        else:
            self["status_label"].setText("Bingo! Found %d Active Feeds" % len(self.feeds))

    def startScan(self):
        item = self["list"].getCurrent()
        if not item: return
        f = item[1]
        tuner_slot = -1
        for slot in nimmanager.nim_slots:
            if slot.isCompatible("DVB-S2"):
                tuner_slot = slot.slot; break
        if tuner_slot == -1: return

        tp = {
            "type": "S2", "frequency": f["freq"] * 1000, "symbol_rate": f["sr"] * 1000,
            "polarization": 0 if f["pol"] == "H" else 1, "fec_inner": 0,
            "system": 1, "modulation": 2, "inversion": 2, "roll_off": 3,
            "pilot": 2, "orbital_position": f["orb"]
        }
        try:
            from Screens.ServiceScan import ServiceScan
            self.session.open(ServiceScan, tuner_slot, transponder=tp, scanList=[tp])
        except: pass

def main(session, **kwargs): session.open(FeedHunter)
def Plugins(**kwargs):
    return PluginDescriptor(name="Feed Hunter Ultimate", description="Ultimate Feed Scanner", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
