# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.ServiceScan import ServiceScan
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Sources.StaticText import StaticText
from Components.MultiContent import MultiContentEntryText
from Components.NimManager import nimmanager
from enigma import (
    eServiceReference, eListboxPythonMultiContent,
    gFont, gRGB, eTimer, eDVBFrontendParametersSatellite
)

import threading, re, json, os, time

# ================= SAFE IMPORTS =================
try:
    import requests
except:
    requests = None

try:
    from bs4 import BeautifulSoup
except:
    BeautifulSoup = None

# ================= CONFIG =================
URL = "https://www.satelliweb.com/index.php?section=livef"
CACHE_FILE = "/tmp/feedhunter_cache.json"

# ================= HELPERS =================
def satToOrbital(text):
    try:
        m = re.search(r"(\d+(?:\.\d+)?)\s*([EW])", text, re.I)
        if not m:
            return 0
        pos = int(float(m.group(1)) * 10)
        return 3600 - pos if m.group(2).upper() == "W" else pos
    except:
        return 0

def loadCache():
    try:
        if os.path.exists(CACHE_FILE):
            return json.load(open(CACHE_FILE))
    except:
        pass
    return []

def saveCache(feeds):
    try:
        json.dump(feeds, open(CACHE_FILE, "w"))
    except:
        pass

# ================= FETCH =================
def getFeeds():
    if not requests or not BeautifulSoup:
        return [], False

    feeds = []
    fromCache = False

    try:
        html = requests.get(URL, timeout=8).text
        soup = BeautifulSoup(html, "html.parser")
        blocks = soup.find_all("div", class_="feed")

        for div in blocks:
            text = div.get_text("\n")
            m = re.search(
                r"(\d+(?:\.\d+)?[EW]).*?Frequency:\s*(\d+).*?Pol:\s*([HV]).*?SR:\s*(\d+)",
                text, re.S
            )
            if not m:
                continue

            feeds.append({
                "sat": m.group(1),
                "orbital": satToOrbital(m.group(1)),
                "freq": int(m.group(2)),
                "pol": m.group(3),
                "sr": int(m.group(4)),
                "event": text.splitlines()[-1],
                "encrypted": bool(re.search("crypt|biss|power", text, re.I))
            })

        if feeds:
            saveCache(feeds)

    except:
        feeds = loadCache()
        fromCache = True

    return feeds, fromCache

# ================= LIST ENTRY =================
def FeedEntry(feed):
    color = gRGB(0, 200, 0) if not feed["encrypted"] else gRGB(220, 0, 0)
    status = "FTA" if not feed["encrypted"] else "ENC"

    return [
        feed,
        MultiContentEntryText(
            pos=(10, 5), size=(860, 30),
            font=0, color=color,
            text="%s | %s %d %s %d" % (
                status, feed["sat"],
                feed["freq"], feed["pol"], feed["sr"]
            )
        ),
        MultiContentEntryText(
            pos=(10, 35), size=(860, 25),
            font=1,
            text=feed["event"]
        ),
    ]

# ================= SCREEN =================
class FeedsScreen(Screen):
    skin = """
    <screen position="center,center" size="900,550" title="Feed-Hunter">
        <widget name="list" position="10,10" size="880,450" />
        <widget name="status" position="10,470" size="880,30" font="Regular;20" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)

        self.feeds = []
        self.fromCache = False

        self["list"] = MenuList([], True, content=eListboxPythonMultiContent)
        self["list"].l.setItemHeight(65)
        self["list"].l.setFont(0, gFont("Regular", 22))
        self["list"].l.setFont(1, gFont("Regular", 18))
        self["list"].l.setBuildFunc(FeedEntry)

        self["status"] = StaticText("Loading feeds...")

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"], {
                "ok": self.openManualScan,
                "red": self.refresh,
                "cancel": self.close,
            }, -1
        )

        self.timer = eTimer()
        self.timer.callback.append(self.updateUI)

        threading.Thread(target=self.loadThread, daemon=True).start()

    def loadThread(self):
        self.feeds, self.fromCache = getFeeds()
        self.timer.start(0, True)

    def refresh(self):
        self["status"].setText("Refreshing...")
        threading.Thread(target=self.loadThread, daemon=True).start()

    def updateUI(self):
        self["list"].setList(self.feeds)
        src = "CACHE" if self.fromCache else "LIVE"
        self["status"].setText("%s | feeds: %d" % (src, len(self.feeds)))

    def openManualScan(self):
        cur = self["list"].getCurrent()
        if not cur:
            return
        feed = cur[0]

        nims = nimmanager.getNimListOfType("DVB-S")
        if not nims:
            return

        tp = {
            "frequency": feed["freq"],
            "symbol_rate": feed["sr"],
            "polarization": 0 if feed["pol"] == "H" else 1,
            "fec_inner": 0,
            "system": 0,
            "modulation": 0,
            "orbital_position": feed["orbital"]
        }

        self.session.open(ServiceScan, nims[0],
                          transponder=tp, scanList=[tp])

# ================= PLUGIN =================
def main(session, **kwargs):
    session.open(FeedsScreen)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="Feed-Hunter",
        description="Satellite Feed Scanner",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        fnc=main
    )
