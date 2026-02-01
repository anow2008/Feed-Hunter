# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.NimManager import nimmanager
from Components.Listbox import Listbox
from Components.MultiContent import MultiContentEntryText
from enigma import eListboxPythonMultiContent, gFont, eTimer
import re, requests, threading

URL = "https://www.satelliweb.com/index.php?section=livef"

def satToOrbital(txt):
    try:
        m = re.search(r"(\d+(?:\.\d+)?)\s*([EW])", txt, re.I)
        if not m: return 0
        p = int(float(m.group(1)) * 10)
        return int(3600 - p if m.group(2).upper() == "W" else p)
    except:
        return 0

def FeedEntry(f):
    return [f,
        MultiContentEntryText(pos=(15, 5), size=(750, 30), font=0, color=0x00FF00, text=u"{} | {} {} {}".format(f['sat'], f['freq'], f['pol'], f['sr'])),
        MultiContentEntryText(pos=(15, 35), size=(750, 25), font=1, color=0xFFFFFF, text=f["event"])]

class FeedHunter(Screen):
    skin = """
    <screen name="FeedHunter" position="center,center" size="850,550" title="Feed Hunter Pro v1.6 (Stable)">
        <widget name="list" position="15,15" size="820,430" scrollbarMode="showOnDemand" transparent="1" />
        <eLabel position="15,460" size="820,1" backgroundColor="#555555" />
        <widget source="status" render="Label" position="15,475" size="820,60" font="Regular;22" halign="center" valign="center" foregroundColor="#00FF00" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.feeds = []
        self.is_fetching = False
        
        self["list"] = Listbox([])
        self["list"].l.setBuildFunc(FeedEntry)
        self["list"].l.setItemHeight(75)
        self["list"].l.setFont(0, gFont("Regular", 24))
        self["list"].l.setFont(1, gFont("Regular", 20))
        
        self["status"] = StaticText("Initializing...")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.startScan, 
            "cancel": self.close, 
            "red": self.close, 
            "green": self.reloadData
        }, -1)
        
        self.timer = eTimer()
        try: self.timer_conn = self.timer.timeout.connect(self.updateUI)
        except: self.timer.callback.append(self.updateUI)
        
        self.onClose.append(self.cleanup)
        self.reloadData()

    def cleanup(self):
        if self.timer.isActive(): self.timer.stop()

    def reloadData(self):
        if self.is_fetching: return
        self.is_fetching = True
        self["status"].setText("Fetching latest feeds...")
        threading.Thread(target=self.fetchFeeds).start()

    def fetchFeeds(self):
        new_feeds = []
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(URL, timeout=10, headers=headers)
            matches = re.findall(r'<div class="feed".*?>(.*?)</div>', response.text, re.S | re.I)
            
            for html in matches:
                try:
                    data = re.search(r"(\d+(?:\.\d+)?[EW]).*?Frequency:\s*(\d+).*?Pol:\s*([HV]).*?SR:\s*(\d+)", html, re.S | re.I)
                    if data:
                        event_title = re.sub(r'<[^>]*>', '', html.split('|')[0]).strip()[:60]
                        new_feeds.append({
                            "sat": data.group(1), 
                            "orbital": satToOrbital(data.group(1)),
                            "freq": int(data.group(2)), 
                            "pol": data.group(3).upper(), 
                            "sr": int(data.group(4)),
                            "event": event_title if event_title else "Unknown Match"
                        })
                except: continue
        except Exception as e:
            print("[FeedHunter] Error:", str(e))
            
        self.feeds = new_feeds
        self.is_fetching = False
        self.timer.start(100, True)

    def updateUI(self):
        self["list"].setList(self.feeds)
        status = "Found {} Feeds. [OK] Scan | [GREEN] Refresh".format(len(self.feeds)) if self.feeds else "No Feeds Found!"
        self["status"].setText(status)

    def startScan(self):
        selection = self["list"].getCurrent()
        if not selection or not selection[0]: return
        
        f = selection[0]
        tuner_slot = -1
        # Check for available tuner slot
        for slot in nimmanager.nim_slots:
            if slot.isCompatible("DVB-S") and not slot.empty:
                tuner_slot = slot.slot
                break
        
        if tuner_slot == -1:
            self["status"].setText("No Active Satellite Tuner Found!")
            return

        # Prepare transponder settings
        tp = {
            "type": "S2",
            "frequency": f["freq"] * 1000, 
            "symbol_rate": f["sr"] * 1000, 
            "polarization": 0 if f["pol"] == "H" else 1,
            "fec_inner": 0,    # Auto
            "system": 1,       # DVB-S2
            "modulation": 2,   # 8PSK
            "inversion": 2,    # Auto
            "roll_off": 3,     # Auto
            "pilot": 2,        # Auto
            "orbital_position": int(f["orbital"])
        }
        
        try:
            from Screens.ServiceScan import ServiceScan
            self.session.open(ServiceScan, tuner_slot, transponder=tp, scanList=[tp])
        except Exception as e:
            print("[FeedHunter] Scan Error:", str(e))
            self["status"].setText("Scan Error: Check Image Compatibility")

def main(session, **kwargs):
    session.open(FeedHunter)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="Feed Hunter",
        description="Satelliweb Live Feeds v1.0",
        where=PluginDescriptor.WHERE_PLUGINMENU, 
        fnc=main, 
        icon="plugin.png"
    )
