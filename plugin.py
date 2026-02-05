# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.NimManager import nimmanager
from enigma import eTimer, getDesktop
import re
import threading

try:
    import requests
    # تعطيل تحذيرات شهادات الأمان لضمان الاتصال
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    requests = None

URL = "https://www.satelliweb.com/index.php?section=livef"

class FeedHunter(Screen):
    skin = """
    <screen name="FeedHunter" position="center,center" size="850,550" title="Feed Hunter v1.1 (Multi-Source)">
        <widget name="list" position="20,20" size="810,420" scrollbarMode="showOnDemand" transparent="1" />
        <widget name="status_label" position="20,460" size="810,60" font="Regular;22" halign="center" valign="center" foregroundColor="#00FF00" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self["list"] = MenuList([])
        self["status_label"] = Label("Initialising connection...")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.startScan,
            "cancel": self.close,
            "green": self.reloadData
        }, -1)

        self.feed_data = []
        self.final_list = []
        self.timer = eTimer()
        try:
            self.timer.timeout.connect(self.showResults)
        except:
            self.timer.callback.append(self.showResults)

        self.onLayoutFinish.append(self.reloadData)

    def reloadData(self):
        self["status_label"].setText("Fetching data... Please wait up to 20s")
        self["list"].setList([])
        threading.Thread(target=self.fetchFeeds, daemon=True).start()

    def fetchFeeds(self):
        display_list = []
        technical_data = []
        
        # محاولة الاتصال عبر أكثر من وسيلة
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'}
        
        success = False
        try:
            # المحاولة الأولى: مباشر مع تعطيل التحقق من الشهادة
            r = requests.get(URL, timeout=15, headers=headers, verify=False)
            if r.status_code == 200:
                success = True
                html = r.text
            else:
                # المحاولة الثانية: استخدام بروكسي خارجي لتجاوز الحظر
                proxy_url = "https://api.allorigins.win/get?url=" + requests.utils.quote(URL)
                r = requests.get(proxy_url, timeout=15, verify=False)
                import json
                html = json.loads(r.text)['contents']
                success = True
        except Exception as e:
            print("Fetch Error:", str(e))
            success = False

        if success:
            try:
                pattern = r"(\d+\.\d°[EW]).*?Frequency:.*?<b>(\d+)</b>.*?Pol:.*?<b>([HV])</b>.*?SR:.*?<b>(\d+)</b>.*?Category:.*?<b>(.*?)</b>.*?ℹ\s*(.*?)(?=<)"
                matches = re.findall(pattern, html, re.S | re.I)
                
                for (sat, freq, pol, sr, cat, event) in matches:
                    c_event = re.sub(r'<[^>]+>', '', event).strip()
                    display_list.append("{} - {} ({} {} {})".format(sat, c_event, freq, pol, sr))
                    
                    m = re.search(r"(\d+\.?\d*)\s*°?\s*([EW])", sat, re.I)
                    orb = 0
                    if m:
                        p = float(m.group(1))
                        orb = int((360 - p) * 10) if m.group(2).upper() == 'W' else int(p * 10)
                    technical_data.append({"freq": int(freq), "pol": pol.upper(), "sr": int(sr), "orbital": orb})
            except:
                pass

        self.feed_data = technical_data
        self.final_list = display_list
        self.timer.start(100, True)

    def showResults(self):
        if self.final_list:
            self["list"].setList(self.final_list)
            self["status_label"].setText("Found {} feeds. Select & OK".format(len(self.final_list)))
        else:
            self["status_label"].setText("Error: Website Blocked or No Internet!")

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
    return PluginDescriptor(name="Feed Hunter", description="Satelliweb Live Feeds", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
