# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.SelectionList import SelectionList
from Components.NimManager import nimmanager
from enigma import eTimer, getDesktop
import re
import threading

try:
    import requests
except ImportError:
    requests = None

URL = "https://www.satelliweb.com/index.php?section=livef"
dSize = getDesktop(0).size()
isFHD = dSize.width() > 1280

def satToOrbital(txt):
    try:
        m = re.search(r"(\d+\.?\d*)\s*°?\s*([EW])", str(txt), re.I)
        if not m: return 0
        pos = float(m.group(1))
        direction = m.group(2).upper()
        return int((360 - pos) * 10) if direction == 'W' else int(pos * 10)
    except:
        return 0

class FeedHunter(Screen):
    skin = """
    <screen name="FeedHunter" position="center,center" size="{w},{h}" title="Feed Hunter v1.2">
        <widget name="list" position="20,20" size="{lw},{lh}" scrollbarMode="showOnDemand" />
        <eLabel position="20,{line_y}" size="{lw},2" backgroundColor="#555555" />
        <widget name="status_label" position="20,{stat_y}" size="{lw},80" font="Regular;{fs}" halign="center" valign="center" foregroundColor="#00FF00" />
        <eLabel text="RED: Close | GREEN: Reload | OK: Scan" position="20,{hint_y}" size="{lw},40" font="Regular;20" halign="left" transparent="1" />
    </screen>""".format(
        w=1100 if isFHD else 850, h=800 if isFHD else 550,
        lw=1060 if isFHD else 810, lh=600 if isFHD else 400,
        line_y=630 if isFHD else 420, stat_y=650 if isFHD else 435,
        hint_y=740 if isFHD else 500, fs=28 if isFHD else 20
    )

    def __init__(self, session):
        Screen.__init__(self, session)
        self.feeds = []
        self["list"] = SelectionList([])
        self["status_label"] = Label("Initializing...")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.startScan,
            "cancel": self.close,
            "red": self.close,
            "green": self.reloadData
        }, -1)
        self.timer = eTimer()
        try: self.timer.timeout.connect(self.updateUI)
        except: self.timer.callback.append(self.updateUI)
        self.onLayoutFinish.append(self.reloadData)

    def reloadData(self):
        self["status_label"].setText("Fetching feeds from Satelliweb...")
        self.feeds = []
        self["list"].setList([])
        threading.Thread(target=self.fetchFeeds, daemon=True).start()

    def fetchFeeds(self):
        new_feeds = []
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.satelliweb.com/'
            }
            # طلب الصفحة مع تجاوز التحقق من الشهادة لتجنب مشاكل الصور القديمة
            r = requests.get(URL, timeout=20, headers=headers, verify=False)
            html = r.text
            
            # نمط بحث جديد وأكثر مرونة لجلب السطر بالكامل
            # بيبحث عن الموقع المداري + التردد + القطبية + معدل الترميز
            pattern = r"(\d+\.\d°[EW]).*?(\d{5})\s+(V|H)\s+(\d{4,5})"
            matches = re.findall(pattern, html, re.S)

            for (sat, freq, pol, sr) in matches:
                display_text = "Sat: {} | Freq: {} | Pol: {} | SR: {}".format(sat, freq, pol, sr)
                new_feeds.append((display_text, {"freq": int(freq), "pol": pol.upper(), "sr": int(sr), "orbital": satToOrbital(sat)}))
                
        except Exception as e:
            print("[FeedHunter] Error:", str(e))

        self.feeds = new_feeds
        self.timer.start(100, True)

    def updateUI(self):
        self["list"].setList(self.feeds)
        if self.feeds:
            self["status_label"].setText("Found {} Feeds | Select & Press OK".format(len(self.feeds)))
        else:
            self["status_label"].setText("No data! Site might be blocking us or no active feeds.")

    def startScan(self):
        item = self["list"].getCurrent()
        if not item or not isinstance(item, tuple): return
        f = item[1]
        tuner_slot = -1
        for slot in nimmanager.nim_slots:
            if slot.isCompatible("DVB-S2"): # يفضل S2 للفيدات
                tuner_slot = slot.slot
                break
        
        if tuner_slot == -1: return

        tp = {
            "type": "S2",
            "frequency": f["freq"] * 1000,
            "symbol_rate": f["sr"] * 1000,
            "polarization": 0 if f["pol"] == "H" else 1,
            "fec_inner": 0,
            "system": 1, # DVB-S2
            "modulation": 2, # 8PSK غالبا للفيدات
            "inversion": 2,
            "roll_off": 3,
            "pilot": 2,
            "orbital_position": f["orbital"]
        }
        try:
            from Screens.ServiceScan import ServiceScan
            self.session.open(ServiceScan, tuner_slot, transponder=tp, scanList=[tp])
        except: pass

def main(session, **kwargs): session.open(FeedHunter)
def Plugins(**kwargs):
    return PluginDescriptor(name="Feed Hunter", description="Satelliweb Scanner", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
