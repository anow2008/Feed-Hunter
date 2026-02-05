# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.NimManager import nimmanager
from Components.Label import Label
from Components.MenuList import MenuList
from enigma import eListboxPythonMultiContent, gFont, eTimer, getDesktop, RT_HALIGN_LEFT, RT_VALIGN_CENTER
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
        if direction == 'W':
            return int((360 - pos) * 10)
        return int(pos * 10)
    except:
        return 0

def FeedEntry(f):
    if f is None: return []
    width = 1100 if isFHD else 800
    res = [f]
    
    cat = f.get("category", "Feed")
    event = f.get("event", "No Name")
    display_name = "[{}] {}".format(cat, event)
    details = "{} | {} {} {} | {}".format(str(f.get('sat','')), str(f.get('freq','')), str(f.get('pol','')), str(f.get('sr','')), str(f.get('desc','')))
    
    res.append((eListboxPythonMultiContent.TYPE_TEXT, 10, 5, width, 45 if isFHD else 30, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, display_name, 0xFFFFFF))
    res.append((eListboxPythonMultiContent.TYPE_TEXT, 10, 50 if isFHD else 35, width, 40 if isFHD else 25, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, details, 0x00FF00))
    return res

class FeedHunter(Screen):
    skin = """
    <screen name="FeedHunter" position="center,center" size="{w},{h}" title="Feed Hunter v1.0 (Py3)">
        <widget name="list" position="20,20" size="{lw},{lh}" scrollbarMode="showOnDemand" transparent="1" />
        <eLabel position="20,{line_y}" size="{lw},2" backgroundColor="#555555" />
        <widget name="status_label" position="20,{stat_y}" size="{lw},80" font="Regular;{fs}" halign="center" valign="center" foregroundColor="#00FF00" />
    </screen>""".format(
        w=1200 if isFHD else 850, h=820 if isFHD else 550,
        lw=1160 if isFHD else 820, lh=650 if isFHD else 420,
        line_y=680 if isFHD else 450, stat_y=700 if isFHD else 465,
        fs=30 if isFHD else 22
    )

    def __init__(self, session):
        Screen.__init__(self, session)
        self.feeds = []
        self.is_fetching = False
        self["list"] = MenuList([])
        self["list"].l.setBuildFunc(FeedEntry)
        
        if isFHD:
            self["list"].l.setItemHeight(100)
            self["list"].l.setFont(0, gFont("Regular", 34))
            self["list"].l.setFont(1, gFont("Regular", 28))
        else:
            self["list"].l.setItemHeight(70)
            self["list"].l.setFont(0, gFont("Regular", 24))
            self["list"].l.setFont(1, gFont("Regular", 18))
        
        self["status_label"] = Label("Connecting to Satelliweb...")
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
            
        self.onClose.append(self.cleanup)
        self.onLayoutFinish.append(self.reloadData)

    def cleanup(self):
        if self.timer.isActive(): self.timer.stop()

    def reloadData(self):
        if not requests:
            self["status_label"].setText("Error: Python-requests not installed!")
            return
        if self.is_fetching: return
        self.is_fetching = True
        self["status_label"].setText("Fetching feeds, please wait...")
        threading.Thread(target=self.fetchFeeds, daemon=True).start()

    def fetchFeeds(self):
        new_feeds = []
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(URL, timeout=15, headers=headers)
            response.encoding = 'utf-8'
            html = response.text
            pattern = r"(\d+\.\d°[EW]).*?Frequency:.*?<b>(\d+)</b>.*?Pol:.*?<b>([HV])</b>.*?SR:.*?<b>(\d+)</b>.*?Category:.*?<b>(.*?)</b>.*?ℹ\s*(.*?)(?=<)"
            matches = re.findall(pattern, html, re.S | re.I)
            for (sat, freq, pol, sr, cat, event) in matches:
                new_feeds.append({
                    "sat": sat, "orbital": satToOrbital(sat), "freq": int(freq), "pol": pol.upper(),
                    "sr": int(sr), "category": re.sub(r'<[^>]+>', '', cat).strip() or "Feed",
                    "event": re.sub(r'<[^>]+>', '', event).strip() or "Live Event", "desc": "Feed"
                })
        except Exception as e: 
            print("[FeedHunter] Error: ", str(e))
        self.feeds = new_feeds
        self.is_fetching = False
        self.timer.start(100, True)

    def updateUI(self):
        self["list"].setList(self.feeds)
        status = "Found {} feeds | [OK] Scan | [GREEN] Refresh".format(len(self.feeds)) if self.feeds else "No feeds found!"
        self["status_label"].setText(status)

    def startScan(self):
        selection = self["list"].getCurrent()
        if not selection: return
        f = selection
        tuner_slot = -1
        for slot in nimmanager.nim_slots:
            if slot.isCompatible("DVB-S"):
                tuner_slot = slot.slot
                break
        if tuner_slot == -1: return
        tp = {
            "type": "S2", "frequency": f["freq"] * 1000, "symbol_rate": f["sr"] * 1000, 
            "polarization": 0 if f["pol"] == "H" else 1, "fec_inner": 0, "system": 1, 
            "modulation": 2, "inversion": 2, "roll_off": 3, "pilot": 2, "orbital_position": f["orbital"]
        }
        try:
            from Screens.ServiceScan import ServiceScan
            self.session.open(ServiceScan, tuner_slot, transponder=tp, scanList=[tp])
        except: 
            pass

def main(session, **kwargs):
    session.open(FeedHunter)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="Feed Hunter", 
        description="Satelliweb Live Feeds (Fixed Final)", 
        where=PluginDescriptor.WHERE_PLUGINMENU, 
        fnc=main, 
        icon="plugin.png"
    )
