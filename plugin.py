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
except:
    requests = None

# استخدام رابط وسيط مختلف وأكثر سرعة
URL = "https://api.allorigins.win/get?url=" + requests.utils.quote("https://www.satelliweb.com/index.php?section=livef")

class FeedHunter(Screen):
    skin = """
    <screen name="FeedHunter" position="center,center" size="900,600" title="Feed Hunter v1.4">
        <widget name="list" position="20,20" size="860,460" scrollbarMode="showOnDemand" transparent="1" />
        <widget name="status_label" position="20,500" size="860,60" font="Regular;24" halign="center" valign="center" foregroundColor="#00FF00" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self["list"] = MenuList([])
        self["status_label"] = Label("Searching for active feeds...")
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
        self["status_label"].setText("Fetching feeds... please wait")
        self["list"].setList([])
        threading.Thread(target=self.fetchFeeds, daemon=True).start()

    def fetchFeeds(self):
        d_list = []
        t_data = []
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(URL, timeout=20, verify=False)
            if r.status_code == 200:
                # فك تشفير محتوى البروكسي
                content = json.loads(r.text).get('contents', '')
                
                # نمط بحث (Regex) جديد وشامل جداً
                # يبحث عن: الموقع المداري، التردد، القطبية، ومعدل الترميز
                pattern = r"(\d+\.\d°[EW]).*?Frequency:.*?<b>(\d+)</b>.*?Pol:.*?<b>([HV])</b>.*?SR:.*?<b>(\d+)</b>.*?Category:.*?<b>(.*?)</b>.*?ℹ\s*(.*?)(?=<)"
                matches = re.findall(pattern, content, re.S | re.I)
                
                for (sat, freq, pol, sr, cat, event) in matches:
                    clean_event = re.sub(r'<[^>]+>', '', event).strip()
                    if not clean_event: clean_event = "Live Feed"
                    
                    # تحويل الموضع المداري لعملية البحث
                    m_orb = re.search(r"(\d+\.?\d*)\s*°?\s*([EW])", sat, re.I)
                    orbital = 0
                    if m_orb:
                        pos = float(m_orb.group(1))
                        orbital = int((360 - pos) * 10) if m_orb.group(2).upper() == 'W' else int(pos * 10)
                    
                    d_list.append("{} | {} {} {} | {}".format(sat, freq, pol, sr, clean_event[:35]))
                    t_data.append({"freq": int(freq), "pol": pol.upper(), "sr": int(sr), "orbital": orbital})
        except Exception as e:
            print("Error:", str(e))

        self.feed_data = t_data
        self.final_list = d_list
        self.timer.start(100, True)

    def showResults(self):
        if self.final_list:
            self["list"].setList(self.final_list)
            self["status_label"].setText("Found {} feeds | OK to Scan".format(len(self.final_list)))
        else:
            self["status_label"].setText("No active feeds at the moment. Press Green to refresh.")

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
    return PluginDescriptor(name="Feed Hunter", description="Satelliweb Live Feeds v1.4", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
