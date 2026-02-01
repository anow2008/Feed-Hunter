# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.ServiceScan import ServiceScan
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.NimManager import nimmanager
from Components.Listbox import Listbox
from Components.MultiContent import MultiContentEntryText
from enigma import eListboxPythonMultiContent, gFont, gRGB, eTimer
import re, requests, threading

URL = "https://www.satelliweb.com/index.php?section=livef"

def satToOrbital(txt):
    m = re.search(r"(\d+(?:\.\d+)?)\s*([EW])", txt, re.I)
    if not m: return 0
    p = int(float(m.group(1)) * 10)
    return 3600 - p if m.group(2).upper() == "W" else p

def FeedEntry(f):
    return [f,
        MultiContentEntryText(pos=(10, 5), size=(760, 30), font=0, color=0x00FF00, text=f"{f['sat']} | {f['freq']} {f['pol']} {f['sr']}"),
        MultiContentEntryText(pos=(10, 35), size=(760, 25), font=1, color=0xFFFFFF, text=f["event"])]

class FeedHunter(Screen):
    skin = """
    <screen name="FeedHunter" position="center,center" size="800,520" title="Feed Hunter Pro (No-BS4)">
        <widget name="list" position="10,10" size="780,420" scrollbarMode="showOnDemand" transparent="1" />
        <eLabel position="10,435" size="780,1" backgroundColor="#555555" />
        <widget source="status" render="Label" position="10,445" size="780,60" font="Regular;22" halign="center" valign="center" foregroundColor="#00FF00" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.feeds = []
        self["list"] = Listbox([])
        self["list"].l.setBuildFunc(FeedEntry)
        self["list"].l.setItemHeight(70)
        self["list"].l.setFont(0, gFont("Regular", 22))
        self["list"].l.setFont(1, gFont("Regular", 18))
        self["status"] = StaticText("جاري جلب البيانات بالـ Regex...")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"ok": self.scan, "cancel": self.close, "red": self.close, "green": self.reload}, -1)
        self.timer = eTimer()
        self.timer.callback.append(self.updateUI)
        self.reload()

    def reload(self):
        self["status"].setText("جاري التحديث السريع...")
        threading.Thread(target=self.loadThread, daemon=True).start()

    def loadThread(self):
        feeds = []
        try:
            res = requests.get(URL, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            # استخراج الـ divs مباشرة بالـ Regex
            matches = re.findall(r'<div class="feed">(.*?)</div>', res.text, re.DOTALL)
            for html in matches:
                m = re.search(r"(\d+(?:\.\d+)?[EW]).*?Frequency:\s*(\d+).*?Pol:\s*([HV]).*?SR:\s*(\d+)", html)
                if m:
                    clean = re.sub(r'<[^>]*>', '', html).strip()
                    feeds.append({
                        "sat": m.group(1), "orbital": satToOrbital(m.group(1)),
                        "freq": int(m.group(2)), "pol": m.group(3), "sr": int(m.group(4)),
                        "event": clean.split('|')[0].strip()[:65]
                    })
        except: pass
        self.feeds = feeds
        self.timer.start(100, True)

    def updateUI(self):
        self["list"].setList(self.feeds)
        self["status"].setText(f"تم العثور على {len(self.feeds)} فيد\nOK للبحث | الأخضر للتحديث")

    def scan(self):
        cur = self["list"].getCurrent()
        if not cur or not (nims := getattr(nimmanager, "getNimListOfType", lambda x: [])("DVB-S")): return
        f = cur[0]
        tp = {"frequency": f["freq"] * 1000, "symbol_rate": f["sr"] * 1000, "polarization": 0 if f["pol"] == "H" else 1,
              "fec_inner": 0, "system": 1, "modulation": 2, "orbital_position": f["orbital"]}
        try: self.session.open(ServiceScan, nims[0], transponder=tp, scanList=[tp])
        except: self["status"].setText("فشل في تشغيل البحث")

def main(session, **kwargs): session.open(FeedHunter)
def Plugins(**kwargs):
    return PluginDescriptor(name="Feed Hunter Pro", description="جالب الفيدات السريع (بدون BS4)", 
                            where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main, icon="plugin.png")
