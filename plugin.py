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

import re, json, threading

# ================= SAFE IMPORTS =================
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

URL = "https://www.satelliweb.com/index.php?section=livef"
CACHE = "/tmp/feedhunter_cache.json"

# ================= HELPERS =================
def satToOrbital(txt):
    m = re.search(r"(\d+(?:\.\d+)?)\s*([EW])", txt, re.I)
    if not m:
        return 0
    p = int(float(m.group(1)) * 10)
    return 3600 - p if m.group(2).upper() == "W" else p

def loadCache():
    try:
        with open(CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def saveCache(d):
    try:
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
    except:
        pass

# ================= LIST ENTRY =================
def FeedEntry(f):
    return [
        f,
        MultiContentEntryText(
            pos=(5, 5), size=(770, 30),
            font=0, color=gRGB(0, 200, 0),
            text=f"{f['sat']} | {f['freq']} {f['pol']} {f['sr']}"
        ),
        MultiContentEntryText(
            pos=(5, 35), size=(770, 25),
            font=1, text=f["event"]
        ),
    ]

# ================= SCREEN =================
class FeedHunter(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)

        self.feeds = []

        # إنشاء الـ Listbox و Status بدون Skin
        self["list"] = Listbox([])
        self["list"].l.setBuildFunc(FeedEntry)
        self["list"].l.setItemHeight(70)
        self["list"].l.setFont(0, gFont("Regular", 18))
        self["list"].l.setFont(1, gFont("Regular", 16))

        self["status"] = StaticText("Loading feeds...")

        # أفعال OK / Cancel / Red
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"], {
                "ok": self.scan,
                "cancel": self.close,
                "red": self.close
            }, -1
        )

        # Timer لتحديث UI بعد تحميل البيانات
        self.timer = eTimer()
        self.timer.callback.append(self.updateUI)

        # التأكد من وجود المكتبات قبل البدء
        if requests is None or BeautifulSoup is None:
            self["status"].setText("Error: requests/bs4 missing!")
        else:
            threading.Thread(target=self.loadThread, daemon=True).start()

    def loadThread(self):
        self.feeds = self.getFeedsData()
        self.timer.start(100, True)

    def getFeedsData(self):
        feeds = []
        try:
            res = requests.get(URL, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            for div in soup.find_all("div", class_="feed"):
                text = div.get_text(" ")
                m = re.search(
                    r"(\d+(?:\.\d+)?[EW]).*?Frequency:\s*(\d+).*?Pol:\s*([HV]).*?SR:\s*(\d+)",
                    text
                )
                if m:
                    feeds.append({
                        "sat": m.group(1),
                        "orbital": satToOrbital(m.group(1)),
                        "freq": int(m.group(2)),
                        "pol": m.group(3),
                        "sr": int(m.group(4)),
                        "event": text.strip()[-50:]  # آخر 50 حرف
                    })
            if feeds:
                saveCache(feeds)
            else:
                feeds = loadCache()
        except Exception as e:
            print("Error fetching feeds:", e)
            feeds = loadCache()
        return feeds

    def updateUI(self):
        self["list"].setList(self.feeds)
        self["status"].setText(f"Found {len(self.feeds)} feeds - Press OK to Scan")

    def scan(self):
        cur = self["list"].getCurrent()
        if not cur:
            return
        f = cur[0]

        nims = getattr(nimmanager, "getNimListOfType", lambda x: [])("DVB-S")
        if not nims:
            self["status"].setText("No DVB-S NIM found!")
            return

        tp = {
            "frequency": f["freq"] * 1000,        # تحويل إلى KHz
            "symbol_rate": f["sr"] * 1000,        # تحويل إلى KHz
            "polarization": 0 if f["pol"] == "H" else 1,
            "fec_inner": 0,
            "system": 1,       # DVB-S2
            "modulation": 2,   # 8PSK
            "orbital_position": f["orbital"]
        }

        self.session.open(ServiceScan, nims[0], transponder=tp, scanList=[tp])

# ================= PLUGIN =================
def main(session, **kwargs):
    session.open(FeedHunter)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="Feed-Hunter",
        description="Feed scanner for any Enigma2 Py3 image (No Skin)",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        fnc=main
    )
