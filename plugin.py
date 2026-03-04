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
    <screen position="center,center" size="850,550" title="Feed Hunter Pro - ID & Data">
        <widget name="list" position="10,10" size="830,420" scrollbarMode="showOnDemand" />
        <widget name="status_label" position="10,440" size="830,40" font="Regular;24" halign="center" foregroundColor="#00FF00" />
        <eLabel text="OK: Scan | GREEN: Reload | RED: Exit" position="10,500" size="830,30" font="Regular;20" halign="left" transparent="1" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.feeds = []
        self["list"] = SelectionList([])
        self["status_label"] = Label("Loading Feeds with IDs...")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.startScan, "cancel": self.close, "red": self.close, "green": self.reloadData
        }, -1)
        self.timer = eTimer()
        try: self.timer.timeout.connect(self.updateUI)
        except: self.timer.callback.append(self.updateUI)
        self.onLayoutFinish.append(self.reloadData)

    def reloadData(self):
        self["status_label"].setText("Fetching from Telegram...")
        self.feeds = []
        threading.Thread(target=self.fetchFeeds).start()

    def fetchFeeds(self):
        new_feeds = []
        url = "https://t.me/s/live_sat_feeds" 
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        try:
            r = requests.get(url, timeout=15, headers=headers, verify=False)
            # تقسيم الصفحة لرسائل
            messages = r.text.split('<div class="tgme_widget_message_text')
            
            for msg in messages:
                # 1. استخراج القمر (مثال: 7.0E)
                sat_match = re.search(r"(\d+\.?\d*)°?\s*([EW])", msg)
                orb = 70
                sat_name = "7.0E"
                if sat_match:
                    pos = float(sat_match.group(1))
                    direction = sat_match.group(2).upper()
                    orb = int((360 - pos) * 10) if direction == 'W' else int(pos * 10)
                    sat_name = "%s%s" % (sat_match.group(1), direction)

                # 2. استخراج التردد والقطبية والترميز
                tp_match = re.search(r"(\d{5})\s+([HVhv])\s+(\d{4,5})", msg)
                if tp_match:
                    freq = int(tp_match.group(1))
                    pol = tp_match.group(2).upper()
                    sr = int(tp_match.group(3))
                    
                    # 3. استخراج الـ ID (اسم القناة)
                    # بيبحث عن كلمة ID: وياخد الكلام اللي بعدها لحد نهاية السطر أو أول علامة <
                    id_match = re.search(r"ID:\s*(.*?)($|<|#)", msg, re.I)
                    channel_id = id_match.group(1).strip() if id_match else "No Name"

                    # 4. تفاصيل البث
                    sys = 1 if "DVB-S2" in msg.upper() else 0
                    mod = 2 if "8PSK" in msg.upper() else 1

                    # شكل العرض في القائمة (اسم القناة + التردد + القمر)
                    display = "[%s] %s | %d %s %d" % (sat_name, channel_id, freq, pol, sr)
                    
                    if not any(f[1]["freq"] == freq for f in new_feeds):
                        new_feeds.append((display, {
                            "freq": freq, "pol": pol, "sr": sr, "orb": orb,
                            "sys": sys, "mod": mod, "name": channel_id
                        }))
                    
        except: pass
            
        self.feeds = new_feeds
        self.timer.start(100, True)

    def updateUI(self):
        self.feeds.reverse() # الأحدث فوق
        self["list"].setList(self.feeds)
        self["status_label"].setText("Found %d Feeds. Press OK to Scan." % len(self.feeds))

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
            "system": f["sys"], "modulation": f["mod"], "inversion": 2, 
            "roll_off": 3, "pilot": 2, "orbital_position": f["orb"]
        }
        
        try:
            from Screens.ServiceScan import ServiceScan
            self.session.open(ServiceScan, tuner_slot, transponder=tp, scanList=[tp])
        except:
            self["status_label"].setText("Scan Error!")

def main(session, **kwargs): session.open(FeedHunter)
def Plugins(**kwargs):
    return PluginDescriptor(name="Feed Hunter ID", description="Auto Scan with Channel ID", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
