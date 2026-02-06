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
import os

try:
    import requests
except ImportError:
    requests = None

# الرابط وتحديد جودة الشاشة
URL = "https://www.satelliweb.com/index.php?section=livef"
dSize = getDesktop(0).size()
isFHD = dSize.width() > 1280

def satToOrbital(txt):
    try:
        m = re.search(r"(\d+\.?\d*)\s*°?\s*([EW])", str(txt), re.I)
        if not m: return 0
        pos = float(m.group(1))
        direction = m.group(2).upper()
        if direction == 'W':
            return int((360 - pos) * 10)
        return int(pos * 10)
    except:
        return 0

class FeedHunter(Screen):
    skin = """
    <screen name="FeedHunter" position="center,center" size="{w},{h}" title="Feed Hunter v1.3 - Diagnostic Mode">
        <widget name="list" position="20,20" size="{lw},{lh}" scrollbarMode="showOnDemand" />
        <eLabel position="20,{line_y}" size="{lw},2" backgroundColor="#555555" />
        <widget name="status_label" position="20,{stat_y}" size="{lw}" font="Regular;{fs}" halign="center" valign="center" foregroundColor="#00FF00" />
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
        self["status_label"] = Label("Starting...")
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
        self["status_label"].setText("Connecting to Satelliweb...")
        self.feeds = []
        self["list"].setList([])
        threading.Thread(target=self.fetchFeeds, daemon=True).start()

    def fetchFeeds(self):
        new_feeds = []
        msg = ""
        try:
            if requests:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                }
                # جلب الصفحة
                response = requests.get(URL, timeout=15, headers=headers, verify=False)
                html = response.text
                
                # حفظ نسخة للتشخيص في مسار /tmp
                with open("/tmp/sat_page.html", "w") as f:
                    f.write(html.encode('utf-8'))

                # نمط البحث (Pattern)
                # الموقع أحياناً يضع البيانات في كلاسات CSS، هذا النمط يبحث عن التنسيق: 12.5°W ... 11450 H 7500
                pattern = r"(\d+\.\d°[EW]).*?(\d{5})\s+([HV])\s+(\d{4,5})"
                matches = re.findall(pattern, html, re.S | re.I)

                if matches:
                    for (sat, freq, pol, sr) in matches:
                        display = "Sat: {} | {} {}-{}".format(sat, freq, pol, sr)
                        new_feeds.append((display, {
                            "freq": int(freq), "pol": pol.upper(),
                            "sr": int(sr), "orbital": satToOrbital(sat)
                        }))
                    msg = "Found {} Feeds".format(len(new_feeds))
                else:
                    msg = "No matches! Check /tmp/sat_page.html"
            else:
                msg = "python-requests is missing!"
        except Exception as e:
            msg = "Error: " + str(e)

        self.feeds = new_feeds
        self.debug_msg = msg
        self.timer.start(100, True)

    def updateUI(self):
        self["list"].setList(self.feeds)
        self["status_label"].setText(self.debug_msg)

    def startScan(self):
        item = self["list"].getCurrent()
        if not item: return
        f = item[1]
        tuner_slot = -1
        for slot in nimmanager.nim_slots:
            if slot.isCompatible("DVB-S2"):
                tuner_slot = slot.slot; break
        
        if tuner_slot == -1:
            self["status_label"].setText("No DVB-S2 Tuner!"); return

        tp = {
            "type": "S2", "frequency": f["freq"] * 1000,
            "symbol_rate": f["sr"] * 1000, "polarization": 0 if f["pol"] == "H" else 1,
            "fec_inner": 0, "system": 1, "modulation": 2,
            "inversion": 2, "roll_off": 3, "pilot": 2,
            "orbital_position": f["orbital"]
        }
        try:
            from Screens.ServiceScan import ServiceScan
            self.session.open(ServiceScan, tuner_slot, transponder=tp, scanList=[tp])
        except: pass

def main(session, **kwargs):
    session.open(FeedHunter)

def Plugins(**kwargs):
    return PluginDescriptor(name="Feed Hunter Pro", description="Satelliweb Live Scanner", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
