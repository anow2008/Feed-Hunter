# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.NimManager import nimmanager
from enigma import eTimer
import re
import threading
import json

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    requests = None

# استخدام رابط بروكسي لتجاوز الحظر
TARGET_URL = "https://www.satelliweb.com/index.php?section=livef"
PROXY_GATEWAY = "https://api.allorigins.win/get?url="

class FeedHunter(Screen):
    skin = """
    <screen name="FeedHunter" position="center,center" size="900,600" title="Feed Hunter v1.2">
        <widget name="list" position="20,20" size="860,460" scrollbarMode="showOnDemand" transparent="1" />
        <widget name="status_label" position="20,500" size="860,60" font="Regular;24" halign="center" valign="center" foregroundColor="#00FF00" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self["list"] = MenuList([])
        self["status_label"] = Label("Connecting to server...")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.startScan,
            "cancel": self.close,
            "green": self.reloadData
        }, -1)

        self.feed_data = []
        self.final_list = []
        self.timer = eTimer()
        try: self.timer.timeout.connect(self.showResults)
        except: self.timer.callback.append(self.showResults)

        self.onLayoutFinish.append(self.reloadData)

    def reloadData(self):
        self["status_label"].setText("Refreshing feeds via Proxy...")
        self["list"].setList([])
        threading.Thread(target=self.fetchFeeds, daemon=True).start()

    def fetchFeeds(self):
        d_list = []
        t_data = []
        try:
            # محاولة الجلب عبر البروكسي لتجنب حظر الـ IP
            full_url = PROXY_GATEWAY + requests.utils.quote(TARGET_URL)
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(full_url, timeout=20, verify=False)
            
            if r.status_code == 200:
                html = json.loads(r.text).get('contents', '')
                pattern = r"(\d+\.\d°[EW]).*?Frequency:.*?<b>(\d+)</b>.*?Pol:.*?<b>([HV])</b>.*?SR:.*?<b>(\d+)</b>.*?Category:.*?<b>(.*?)</b>.*?ℹ\s*(.*?)(?=<)"
                matches = re.findall(pattern, html, re.S | re.I)
                
                for (sat, freq, pol, sr, cat, event) in matches:
                    event_name = re.sub(r'<[^>]+>', '', event).strip()
                    d_list.append("{} - {} ({} {} {})".format(sat, event_name, freq, pol, sr))
                    
                    # حساب الموضع المداري
                    m = re.search(r"(\d+\.?\d*)\s*°?\s*([EW])", sat, re.I)
                    orb = 0
                    if m:
                        p = float(m.group(1))
                        orb = int((360 - p) * 10) if m.group(2).upper() == 'W' else int(p * 10)
                    t_data.append({"freq": int(freq), "pol": pol.upper(), "sr": int(sr), "orbital": orb})
        except Exception as e:
            print("[FeedHunter] Error:", str(e))

        self.feed_data = t_data
        self.final_list = d_list
        self.timer.start(100, True)

    def showResults(self):
        if self.final_list:
            self["list"].setList(self.final_list)
            self["status_label"].setText("Found {} Feeds | OK to Scan".format(len(self.final_list)))
        else:
            self["status_label"].setText("Connection Failed. Check Internet or try again.")

    def startScan(self):
        idx = self["list"].getSelectedIndex()
        if idx < 0 or idx >= len(self.feed_data): return
        f = self.feed_data[idx]
        tuner_slot = -1
        for slot in nimmanager.nim_slots:
            if slot.isCompatible("DVB-S"):
                tuner_slot = slot.slot
                break
        if tuner_slot != -1:
            tp = {"type": "S2", "frequency": f["freq"] * 1000, "symbol_rate": f["sr"] * 1000, "polarization": 0 if f["pol"] == "H" else 1, "fec_inner": 0, "system": 1, "modulation": 2, "inversion": 2, "roll_off": 3, "pilot": 2, "orbital_position": f["orbital"]}
            try:
                from Screens.ServiceScan import ServiceScan
                self.session.open(ServiceScan, tuner_slot, transponder=tp, scanList=[tp])
            except: pass

def main(session, **kwargs):
    session.open(FeedHunter)

def Plugins(**kwargs):
    return PluginDescriptor(name="Feed Hunter", description="Satelliweb Live Feeds (Proxy Mode)", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
