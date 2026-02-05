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

try:
    import requests
except ImportError:
    requests = None

URL = "https://www.satelliweb.com/index.php?section=livef"
dSize = getDesktop(0).size()
isFHD = dSize.width() > 1280

class FeedHunter(Screen):
    # تم إضافة ألوان صريحة للنص (foregroundColor) لضمان ظهوره على أي سكين
    skin = """
    <screen name="FeedHunter" position="center,center" size="{w},{h}" title="Feed Hunter v1.0">
        <widget name="list" position="20,20" size="{lw},{lh}" scrollbarMode="showOnDemand" itemHeight="60" foregroundColor="#ffffff" foregroundColorSelected="#ffffff" backgroundColorSelected="#002d5d" />
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
        self["list"] = SelectionList([])
        self["status_label"] = Label("Initialising...")
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

        self.onLayoutFinish.append(self.reloadData)

    def reloadData(self):
        self["status_label"].setText("Connecting to Satelliweb...")
        threading.Thread(target=self.fetchFeeds, daemon=True).start()

    def fetchFeeds(self):
        new_feeds = []
        try:
            if requests:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                r = requests.get(URL, timeout=15, headers=headers)
                r.encoding = 'utf-8'
                # نمط البحث (Pattern) معدل ليكون أكثر مرونة
                pattern = r"(\d+\.\d°[EW]).*?Frequency:.*?<b>(\d+)</b>.*?Pol:.*?<b>([HV])</b>.*?SR:.*?<b>(\d+)</b>.*?Category:.*?<b>(.*?)</b>.*?ℹ\s*(.*?)(?=<)"
                matches = re.findall(pattern, r.text, re.S | re.I)
                
                for (sat, freq, pol, sr, cat, event) in matches:
                    clean_cat = re.sub(r'<[^>]+>', '', cat).strip()
                    clean_event = re.sub(r'<[^>]+>', '', event).strip()
                    display_text = "{} - {} ({} {} {})".format(sat, clean_event, freq, pol, sr)
                    
                    # تحويل القمر لإحداثيات رقمية للجهاز
                    m = re.search(r"(\d+\.?\d*)\s*°?\s*([EW])", sat, re.I)
                    orbital = 0
                    if m:
                        pos = float(m.group(1))
                        orbital = int((360 - pos) * 10) if m.group(2).upper() == 'W' else int(pos * 10)

                    new_feeds.append((display_text, {
                        "freq": int(freq), "pol": pol.upper(), "sr": int(sr), "orbital": orbital
                    }))
            else:
                print("Requests module missing")
        except Exception as e:
            print("Fetch Error:", str(e))
            
        self.feeds = new_feeds
        self.timer.start(100, True)

    def updateUI(self):
        if len(self.feeds) > 0:
            self["list"].setList(self.feeds)
            self["status_label"].setText("Found {} feeds | Press OK to Scan".format(len(self.feeds)))
        else:
            self["status_label"].setText("No feeds found! Press GREEN to retry.")

    def startScan(self):
        item = self["list"].getCurrent()
        if not item: return
        f = item[1]
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
        except: pass

def main(session, **kwargs):
    session.open(FeedHunter)

def Plugins(**kwargs):
    return PluginDescriptor(name="Feed Hunter", description="Satelliweb Live Feeds", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
