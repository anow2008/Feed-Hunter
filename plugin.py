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
    <screen position="center,center" size="850,550" title="Feed Hunter v2.1 - Real Data">
        <widget name="list" position="10,10" size="830,420" scrollbarMode="showOnDemand" />
        <widget name="status_label" position="10,440" size="830,40" font="Regular;24" halign="center" foregroundColor="#00FF00" />
        <eLabel text="OK: Scan | GREEN: Reload | RED: Exit" position="10,500" size="830,30" font="Regular;20" halign="left" transparent="1" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.feeds = []
        self["list"] = SelectionList([])
        self["status_label"] = Label("Searching for active feeds...")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.startScan, "cancel": self.close, "red": self.close, "green": self.reloadData
        }, -1)
        self.timer = eTimer()
        try: self.timer.timeout.connect(self.updateUI)
        except: self.timer.callback.append(self.updateUI)
        self.onLayoutFinish.append(self.reloadData)

    def reloadData(self):
        self["status_label"].setText("Fetching Live Feeds...")
        self.feeds = []
        threading.Thread(target=self.fetchFeeds).start()

    def fetchFeeds(self):
        new_feeds = []
        # المصدر ده أسرع وأخف حالياً
        url = "https://tfeed.net/index.php" 
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        try:
            r = requests.get(url, timeout=10, headers=headers, verify=False)
            html = r.text
            
            # نمط بحث متطور يجيب القمر والتردد والقطبية والترميز
            # بيبحث عن صيغ مثل: 7.0E 11126 V 7200
            pattern = re.findall(r"(\d+\.?\d*°?[EW]).*?(\d{5})\s+([HV])\s+(\d{4,5})", html, re.S)

            for (sat, freq, pol, sr) in pattern:
                display = "Sat: %s | Freq: %s %s %s" % (sat, freq, pol, sr)
                
                # استخراج الموقع المداري للتيونر
                m_pos = re.search(r"(\d+\.?\d*)", sat)
                m_dir = re.search(r"([EW])", sat, re.I)
                pos = float(m_pos.group(1)) if m_pos else 7.0
                direction = m_dir.group(1).upper() if m_dir else 'E'
                orb = int((360 - pos) * 10) if direction == 'W' else int(pos * 10)

                new_feeds.append((display, {"freq": int(freq), "pol": pol, "sr": int(sr), "orb": orb}))
        except:
            pass
            
        self.feeds = new_feeds
        self.timer.start(100, True)

    def updateUI(self):
        self["list"].setList(self.feeds)
        if self.feeds:
            self["status_label"].setText("Success! Found %d Active Feeds" % len(self.feeds))
        else:
            self["status_label"].setText("No feeds at the moment. Press GREEN to retry.")

    def startScan(self):
        item = self["list"].getCurrent()
        if not item or not item[1]: return
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
        except:
            self["status_label"].setText("Scan Error!")

def main(session, **kwargs): session.open(FeedHunter)
def Plugins(**kwargs):
    return PluginDescriptor(name="Feed Hunter Pro", description="Live Feed Scanner", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
