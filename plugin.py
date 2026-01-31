# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.ServiceScan import ServiceScan
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.NimManager import nimmanager
from Components.Listbox import Listbox
from Components.MultiContent import MultiContentEntryText
from enigma import (
    eListboxPythonMultiContent,
    gFont, gRGB, eTimer, eDVBFrontendParametersSatellite,
    eServiceReference
)

import re, os, json, threading

# ================= SAFE IMPORTS =================
try:
    import requests
    from bs4 import BeautifulSoup
except:
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
        return json.load(open(CACHE))
    except:
        return []

def saveCache(d):
    try:
        json.dump(d, open(CACHE, "w"))
    except:
        pass

# ================= FETCH =================
def getFeeds():
    if not requests or not BeautifulSoup:
        return [], False

    feeds = []
    try:
        html = requests.get(URL, timeout=8).text
        soup = BeautifulSoup(html, "html.parser")
        for div in soup.find_all("div", class_="feed"):
            t = div.get_text(" ")
            m = re.search(
                r"(\d+(?:\.\d+)?[EW]).*?Frequency:\s*(\d+).*?Pol:\s*([HV]).*?SR:\s*(\d+)",
                t
            )
            if not m:
                continue
            feeds.append({
                "sat": m.group(1),
                "orbital": satToOrbital(m.group(1)),
                "freq": int(m.group(2)),
                "pol": m.group(3),
                "sr": int(m.group(4)),
                "event": t.strip()[-50:],
            })
        if feeds:
            saveCache(feeds)
        return feeds, False
    except:
        return loadCache(), True

# ================= LIST ENTRY =================
def FeedEntry(f):
    return [
        f,
        MultiContentEntryText(
            pos=(10, 5), size=(860, 30),
            font=0, color=gRGB(0, 200, 0),
            text="%s | %d %s %d" %
            (f["sat"], f["freq"], f["pol"], f["sr"])
        ),
        MultiContentEntryText(
            pos=(10, 40), size=(860, 25),
            font=1, text=f["event"]
        ),
    ]

# ================= SCREEN =================
class FeedHunter(Screen):
    skin = """
    <screen position="center,center" size="900,550" title="Feed-Hunter (OpenATV)">
        <widget name="list" position="10,10" size="880,460" />
        <widget name="status" position="10,480" size="880,30" font="Regular;20"/>
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)

        self.feeds = []

        self["list"] = Listbox([])
        self["list"].l.setBuildFunc(FeedEntry)
        self["list"].l.setItemHeight(70)
        self["list"].l.setFont(0, gFont("Regular", 22))
        self["list"].l.setFont(1, gFont("Regular", 18))

        self["status"] = StaticText("Loading feeds...")

        self["actions"] = ActionMap(
            ["OkCancelActions"], {
                "ok": self.scan,
                "cancel": self.close
            }, -1
        )

        self.timer = eTimer()
        self.timer.callback.append(self.updateUI)

        threading.Thread(target=self.loadThread, daemon=True).start()

    def loadThread(self):
        self.feeds, cached = getFeeds()
        self.timer.start(0, True)

    def updateUI(self):
        self["list"].setList(self.feeds)
        self["status"].setText("Feeds: %d" % len(self.feeds))

    def scan(self):
        cur = self["list"].getCurrent()
        if not cur:
            return
        f = cur[0]

        nims = nimmanager.getNimListOfType("DVB-S")
        if not nims:
            return

        tp = {
            "frequency": f["freq"],
            "symbol_rate": f["sr"],
            "polarization": 0 if f["pol"] == "H" else 1,
            "fec_inner": 0,
            "system": 0,
            "modulation": 0,
            "orbital_position": f["orbital"]
        }

        self.session.open(ServiceScan, nims[0],
                          transponder=tp, scanList=[tp])

# ================= PLUGIN =================
def main(session, **kwargs):
    session.open(FeedHunter)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="Feed-Hunter",
        description="OpenATV compatible feed scanner",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        fnc=main
    )
