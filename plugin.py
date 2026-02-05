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
except ImportError:
    requests = None

URL = "https://www.satelliweb.com/index.php?section=livef"
dSize = getDesktop(0).size()
isFHD = dSize.width() > 1280

class FeedHunter(Screen):
    # استخدام سكين مبسط جداً لضمان عدم حدوث تعارض مع Premium-FHD
    skin = """
    <screen name="FeedHunter" position="center,center" size="{w},{h}" title="Feed Hunter v1.0">
        <widget name="list" position="10,10" size="{lw},{lh}" scrollbarMode="showOnDemand" transparent="1" />
        <widget name="status_label" position="10,{stat_y}" size="{lw},60" font="Regular;{fs}" halign="center" valign="center" foregroundColor="#00FF00" backgroundColor="#000000" />
    </screen>""".format(
        w=1100 if isFHD else 800, h=700 if isFHD else 500,
        lw=1080 if isFHD else 780, lh=580 if isFHD else 400,
        stat_y=610 if isFHD else 420, fs=28 if isFHD else 20
    )

    def __init__(self, session):
        Screen.__init__(self, session)
        # استخدام MenuList عادية (نص فقط) لضمان الظهور
        self["list"] = MenuList([])
        self["status_label"] = Label("Connecting... Please wait")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.startScan,
            "cancel": self.close,
            "green": self.reloadData
        }, -1)

        self.feed_data = [] # لتخزين البيانات التقنية بعيداً عن العرض
        self.timer = eTimer()
        try:
            self.timer.timeout.connect(self.showResults)
        except:
            self.timer.callback.append(self.showResults)

        self.onLayoutFinish.append(self.reloadData)

    def reloadData(self):
        self["status_label"].setText("Fetching data from Satelliweb...")
        self["list"].setList([])
        threading.Thread(target=self.fetchFeeds, daemon=True).start()

    def fetchFeeds(self):
        display_list = []
        technical_data = []
        try:
            if requests:
                # محاكاة متصفح حقيقي لتجنب الحجب
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                r = requests.get(URL, timeout=15, headers=headers)
                r.encoding = 'utf-8'
                
                # نمط بحث أكثر دقة لبيانات الموقع
                pattern = r"(\d+\.\d°[EW]).*?Frequency:.*?<b>(\d+)</b>.*?Pol:.*?<b>([HV])</b>.*?SR:.*?<b>(\d+)</b>.*?Category:.*?<b>(.*?)</b>.*?ℹ\s*(.*?)(?=<)"
                matches = re.findall(pattern, r.text, re.S | re.I)
                
                for (sat, freq, pol, sr, cat, event) in matches:
                    c_event = re.sub(r'<[^>]+>', '', event).strip()
                    # نص العرض البسيط
                    display_list.append("{} - {} ({} {} {})".format(sat, c_event, freq, pol, sr))
                    
                    # البيانات التقنية للبحث
                    m = re.search(r"(\d+\.?\d*)\s*°?\s*([EW])", sat, re.I)
                    orb = 0
                    if m:
                        p = float(m.group(1))
                        orb = int((360 - p) * 10) if m.group(2).upper() == 'W' else int(p * 10)
                    
                    technical_data.append({"freq": int(freq), "pol": pol.upper(), "sr": int(sr), "orbital": orb})
            
            self.feed_data = technical_data
            self.final_list = display_list
        except Exception as e:
            print("Error: ", str(e))
            self.final_list = []

        self.timer.start(100, True)

    def showResults(self):
        if self.final_list:
            self["list"].setList(self.final_list)
            self["status_label"].setText("Found {} Feeds. Select and press OK".format(len(self.final_list)))
        else:
            self["status_label"].setText("Failed to get data. Try again later.")

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
            tp = {
                "type": "S2", "frequency": f["freq"] * 1000, "symbol_rate": f["sr"] * 1000,
                "polarization": 0 if f["pol"] == "H" else 1, "fec_inner": 0, "system": 1,
                "modulation": 2, "inversion": 2, "roll_off": 3, "pilot": 2, "orbital_position": f["orbital"]
            }
            try:
                from Screens.ServiceScan import ServiceScan
                self.session.open(ServiceScan, tuner_slot, transponder=tp, scanList=[tp])
            except: pass

def main(session, **kwargs):
    session.open(FeedHunter)

def Plugins(**kwargs):
    return PluginDescriptor(name="Feed Hunter", description="Satelliweb Live Feeds", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
