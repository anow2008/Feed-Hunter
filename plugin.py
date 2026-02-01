# -*- coding: utf-8 -*-
# Feed Hunter  - 
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.ServiceScan import ServiceScan
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.NimManager import nimmanager
from Components.Listbox import Listbox
from Components.MultiContent import MultiContentEntryText
from enigma import eListboxPythonMultiContent, gFont, eTimer
import re, requests, threading

# Data Source
URL = "https://www.satelliweb.com/index.php?section=livef"

def satToOrbital(txt):
    """ Converts satellite string (e.g. 10.0E) to orbital position integer """
    m = re.search(r"(\d+(?:\.\d+)?)\s*([EW])", txt, re.I)
    if not m: return 0
    p = int(float(m.group(1)) * 10)
    return 3600 - p if m.group(2).upper() == "W" else p

def FeedEntry(f):
    """ UI Layout for each list item """
    return [f,
        MultiContentEntryText(pos=(15, 5), size=(750, 30), font=0, color=0x00FF00, text=f"{f['sat']} | {f['freq']} {f['pol']} {f['sr']}"),
        MultiContentEntryText(pos=(15, 35), size=(750, 25), font=1, color=0xFFFFFF, text=f["event"])]

class FeedHunter(Screen):
    # Professional UI Skin
    skin = """
    <screen name="FeedHunter" position="center,center" size="850,550" title="Feed Hunter Pro v1.3">
        <widget name="list" position="15,15" size="820,430" scrollbarMode="showOnDemand" transparent="1" />
        <eLabel position="15,460" size="820,1" backgroundColor="#555555" />
        <widget source="status" render="Label" position="15,475" size="820,60" font="Regular;22" halign="center" valign="center" foregroundColor="#00FF00" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.feeds = []
        
        # UI Components
        self["list"] = Listbox([])
        self["list"].l.setBuildFunc(FeedEntry)
        self["list"].l.setItemHeight(75)
        self["list"].l.setFont(0, gFont("Regular", 24))
        self["list"].l.setFont(1, gFont("Regular", 20))
        
        self["status"] = StaticText("Connecting to Satelliweb...")
        
        # Key Mapping
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.startScan, 
            "cancel": self.close, 
            "red": self.close, 
            "green": self.reloadData
        }, -1)
        
        # UI Update Timer
        self.timer = eTimer()
        try: self.timer_conn = self.timer.timeout.connect(self.updateUI)
        except: self.timer.callback.append(self.updateUI)
        
        self.onClose.append(self.cleanup)
        self.reloadData()

    def cleanup(self):
        if self.timer.isActive():
            self.timer.stop()

    def reloadData(self):
        self["status"].setText("Fetching latest feeds, please wait...")
        self.feeds = []
        self["list"].setList([])
        threading.Thread(target=self.fetchFeeds, daemon=True).start()

    def fetchFeeds(self):
        new_feeds = []
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(URL, timeout=12, headers=headers)
            
            # Robust Regex to extract feed blocks
            matches = re.findall(r'<div class="feed".*?>(.*?)</div>', response.text, re.S | re.I)
            
            for html in matches:
                # Extract Params: Sat, Freq, Pol, SR
                data = re.search(r"(\d+(?:\.\d+)?[EW]).*?Frequency:\s*(\d+).*?Pol:\s*([HV]).*?SR:\s*(\d+)", html, re.S | re.I)
                if data:
                    clean_text = re.sub(r'<[^>]*>', '', html).replace('\n', ' ').replace('\r', '').strip()
                    event_title = clean_text.split('|')[0].strip()[:65]
                    
                    new_feeds.append({
                        "sat": data.group(1), 
                        "orbital": satToOrbital(data.group(1)),
                        "freq": int(data.group(2)), 
                        "pol": data.group(3).upper(), 
                        "sr": int(data.group(4)),
                        "event": event_title if event_title else "Unknown Event"
                    })
        except Exception as e:
            print(f"[FeedHunter] Error: {str(e)}")
            
        self.feeds = new_feeds
        self.timer.start(100, True)

    def updateUI(self):
        self["list"].setList(self.feeds)
        if not self.feeds:
            self["status"].setText("No feeds found! Check your internet connection.")
        else:
            self["status"].setText(f"Found {len(self.feeds)} Feeds\n[OK] Scan Frequency  |  [GREEN] Refresh List")

    def startScan(self):
        selection = self["list"].getCurrent()
        if not selection: return
        
        # Find available DVB-S Tuner
        tuner = [x for x in nimmanager.nim_slots if x.isCompatible("DVB-S")]
        if not tuner:
            self["status"].setText("Error: No satellite tuner detected!")
            return
            
        f = selection[0]
        self["status"].setText(f"Preparing Tuner for {f['freq']} {f['pol']}...")

        # Transponder Parameters (Auto-Lock optimized)
        tp_data = {
            "type": "S2",
            "frequency": f["freq"] * 1000, 
            "symbol_rate": f["sr"] * 1000, 
            "polarization": 0 if f["pol"] == "H" else 1,
            "fec_inner": 0,    # Auto FEC
            "system": 1,       # DVB-S2
            "modulation": 2,    # 8PSK
            "inversion": 2,    # Auto
            "roll_off": 3,     # Auto
            "pilot": 2,        # Auto
            "orbital_position": f["orbital"]
        }
        
        try:
            # Open Enigma2 Manual Scan Screen with pre-filled data
            self.session.open(ServiceScan, tuner[0].slot, transponder=tp_data, scanList=[tp_data])
        except Exception as err:
            print(f"[FeedHunter] Scan Launch Error: {err}")
            self["status"].setText("Error: Could not launch Manual Scan screen.")

def main(session, **kwargs):
    session.open(FeedHunter)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="Feed Hunter Pro", 
        description="Fetch Live Feeds from Satelliweb (No-BS4)", 
        where=PluginDescriptor.WHERE_PLUGINMENU, 
        fnc=main, 
        icon="plugin.png"
    )
