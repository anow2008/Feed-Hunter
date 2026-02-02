# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.NimManager import nimmanager
from Components.Listbox import Listbox
from Components.MultiContent import MultiContentEntryText
from enigma import eListboxPythonMultiContent, gFont, eTimer, getDesktop
import re, requests, threading

URL = "https://www.satelliweb.com/index.php?section=livef"

# التحقق من دقة الشاشة
dSize = getDesktop(0).size()
isFHD = dSize.width() > 1280

def satToOrbital(txt):
    try:
        m = re.search(r"(\d+(?:\.\d+)?)\s*([EW])", txt, re.I)
        if not m: return 0
        p = int(float(m.group(1)) * 10)
        return int(3600 - p if m.group(2).upper() == "W" else p)
    except:
        return 0

def FeedEntry(f):
    if isFHD:
        return [f,
            MultiContentEntryText(pos=(10, 5), size=(1100, 45), font=0, color=0xFFFFFF, text=f["event"]),
            MultiContentEntryText(pos=(10, 50), size=(1100, 40), font=1, color=0x00FF00, text="{} | {} {} {} | {}".format(f['sat'], f['freq'], f['pol'], f['sr'], f['desc']))]
    else:
        return [f,
            MultiContentEntryText(pos=(10, 5), size=(800, 30), font=0, color=0xFFFFFF, text=f["event"]),
            MultiContentEntryText(pos=(10, 35), size=(800, 25), font=1, color=0x00FF00, text="{} | {} {} {} | {}".format(f['sat'], f['freq'], f['pol'], f['sr'], f['desc']))]

class FeedHunter(Screen):
    if isFHD:
        skin = """
        <screen name="FeedHunter" position="center,center" size="1200,820" title="Feed Hunter Pro v1.7 (FHD)">
            <widget name="list" position="20,20" size="1160,650" scrollbarMode="showOnDemand" transparent="1" />
            <eLabel position="20,680" size="1160,2" backgroundColor="#555555" />
            <widget source="status" render="Label" position="20,700" size="1160,80" font="Regular;30" halign="center" valign="center" foregroundColor="#00FF00" />
        </screen>"""
    else:
        skin = """
        <screen name="FeedHunter" position="center,center" size="850,550" title="Feed Hunter Pro v1.7 (HD)">
            <widget name="list" position="15,15" size="820,420" scrollbarMode="showOnDemand" transparent="1" />
            <eLabel position="15,450" size="820,1" backgroundColor="#555555" />
            <widget source="status" render="Label" position="15,465" size="820,60" font="Regular;22" halign="center" valign="center" foregroundColor="#00FF00" />
        </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.feeds = []
        self.is_fetching = False
        self["list"] = Listbox([])
        self["list"].l.setBuildFunc(FeedEntry)
        
        if isFHD:
            self["list"].l.setItemHeight(100)
            self["list"].l.setFont(0, gFont("Regular", 34))
            self["list"].l.setFont(1, gFont("Regular", 28))
        else:
            self["list"].l.setItemHeight(70)
            self["list"].l.setFont(0, gFont("Regular", 24))
            self["list"].l.setFont(1, gFont("Regular", 18))
        
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
        self["status"].setText("Fetching latest feeds from Satelliweb...")
        threading.Thread(target=self.fetchFeeds).start()

    def fetchFeeds(self):
        new_feeds = []
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(URL, timeout=10, headers=headers)
            # النمط المطور لسحب كافة التفاصيل
            pattern = r"([\d\.]+°[EW]).*?Frequency:\s*(\d+).*?Pol:\s*([HV]).*?SR:\s*(\d+).*?Category:\s*([^-<]+).*?(?:Transmitted in:\s*([^<ℹ]+))?.*?ℹ\s*([^<]+)"
            matches = re.findall(pattern, response.text, re.S | re.I)
            
            for (sat, freq, pol, sr, cat, enc, event) in matches:
                try:
                    # تنظيف النص وتجهيز الوصف (النوع + التشفير)
                    category = cat.replace('&nbsp;', '').strip()
                    encryption = enc.replace('&nbsp;', '').strip() if enc else "FTA"
                    event_name = event.strip()
                    
                    new_feeds.append({
                        "sat": sat.strip(), 
                        "orbital": satToOrbital(sat),
                        "freq": int(freq), 
                        "pol": pol.upper(), 
                        "sr": int(sr),
                        "event": event_name if event_name else "Unknown Event",
                        "desc": "{} ({})".format(category, encryption)
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
        for slot in nimmanager.nim_slots:
            if slot.isCompatible("DVB-S") and not slot.empty:
                tuner_slot = slot.slot
                break
        
        if tuner_slot == -1:
            self["status"].setText("No Active Satellite Tuner Found!")
            return

        tp = {
            "type": "S2",
            "frequency": f["freq"] * 1000, 
            "symbol_rate": f["sr"] * 1000, 
            "polarization": 0 if f["pol"] == "H" else 1,
            "fec_inner": 0, "system": 1, "modulation": 2, "inversion": 2, "roll_off": 3, "pilot": 2,
            "orbital_position": int(f["orbital"])
        }
        
        try:
            from Screens.ServiceScan import ServiceScan
            self.session.open(ServiceScan, tuner_slot, transponder=tp, scanList=[tp])
        except Exception as e:
            self["status"].setText("Scan Error: Check Image Compatibility")

def main(session, **kwargs):
    session.open(FeedHunter)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="Feed Hunter",
        description="Satelliweb Live Feeds (Full Details Support)",
        where=PluginDescriptor.WHERE_PLUGINMENU, 
        fnc=main, 
        icon="plugin.png"
    )
