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
import requests
from bs4 import BeautifulSoup

# ==================================================
# CONFIG
# ==================================================
URL = "https://www.satelliweb.com/index.php?section=livef"
CACHE_FILE = "/tmp/feedhunter_cache.json"
SETTINGS_FILE = "/etc/enigma2/feedhunter.conf"
AUTO_REFRESH = 1200000  # 20 minutes

# ==================================================
# Settings
# ==================================================
def loadAutoSetting():
    try:
        if os.path.exists(SETTINGS_FILE):
            for l in open(SETTINGS_FILE):
                if l.startswith("auto="):
                    return l.strip().endswith("1")
    except:
        pass
    return True

def saveAutoSetting(v):
    try:
        open(SETTINGS_FILE, "w").write("auto=%d" % (1 if v else 0))
    except:
        pass

# ==================================================
# Helpers
# ==================================================
def satToOrbital(text):
    """
    Supports:
    19.2E , 19.2°E , 19E , 7W
    """
    try:
        m = re.search(r"(\d+(?:\.\d+)?)\s*°?\s*([EW])", text, re.I)
        if not m:
            return 0
        pos = int(float(m.group(1)) * 10)
        return 3600 - pos if m.group(2).upper() == "W" else pos
    except:
        return 0

def saveCache(feeds):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(feeds, f)
    except:
        pass

def loadCache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                return json.load(f)
    except:
        pass
    return []

# ==================================================
# Fetch Feeds (Safe Scraper)
# ==================================================
def getFeeds():
    feeds = []
    fromCache = False

    try:
        html = requests.get(URL, timeout=8).text
        soup = BeautifulSoup(html, "html.parser")
        blocks = soup.find_all("div", class_="feed")

        for div in blocks:
            try:
                text = div.get_text("\n").strip()
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if not lines:
                    continue

                satname = lines[0]

                feed = {
                    "sat": satname,
                    "orbital": satToOrbital(satname),
                    "freq": 0,
                    "pol": "H",
                    "sr": 0,
                    "event": lines[-1],
                    "encrypted": False
                }

                m = re.search(
                    r"Frequency:\s*(\d+)\s*-\s*Pol:\s*([HV])\s*-\s*SR:\s*(\d+)",
                    text
                )
                if not m:
                    continue

                feed["freq"] = int(m.group(1))
                feed["pol"] = m.group(2)
                feed["sr"] = int(m.group(3))

                if re.search(
                    r"Encrypted|Scrambled|BISS|PowerVu|crypté|crypt",
                    text, re.I
                ):
                    feed["encrypted"] = True

                feeds.append(feed)

            except:
                continue

        if feeds:
            saveCache(feeds)

    except:
        feeds = loadCache()
        fromCache = True

    return feeds, fromCache

# ==================================================
# List Entry
# ==================================================
def FeedEntry(feed):
    color = gRGB(0, 200, 0) if not feed["encrypted"] else gRGB(220, 0, 0)
    lock = "🔒 " if feed["encrypted"] else "🔓 "

    return [
        feed,
        MultiContentEntryText(
            pos=(10, 5), size=(860, 30),
            font=0, color=color,
            text="%s%s | %d %s %d" % (
                lock, feed["sat"],
                feed["freq"], feed["pol"], feed["sr"]
            )
        ),
        MultiContentEntryText(
            pos=(10, 35), size=(860, 25),
            font=1, text=feed["event"]
        ),
    ]

# ==================================================
# Main Screen
# ==================================================
class FeedsScreen(Screen):
    skin = """
    <screen name="FeedsScreen" title="Feed-Hunter"
        position="center,center" size="900,550">
        <widget name="list" position="10,10"
            size="880,450" scrollbarMode="showOnDemand" />
        <widget name="status" position="10,470"
            size="880,30" font="Regular;20" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)

        self.feeds = []
        self.fromCache = False
        self.autoEnabled = loadAutoSetting()
        self.lastUpdate = "--:--"

        self["list"] = MenuList([], True, content=eListboxPythonMultiContent)
        self["list"].l.setItemHeight(65)
        self["list"].l.setFont(0, gFont("Regular", 22))
        self["list"].l.setFont(1, gFont("Regular", 18))

        self["status"] = StaticText("Loading feeds...")

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"], {
                "ok": self.openManualScan,
                "blue": self.quickTune,
                "red": self.refreshFeeds,
                "yellow": self.toggleAutoRefresh,
                "cancel": self.close,
                "up": self["list"].up,
                "down": self["list"].down,
            }, -1
        )

        self.uiTimer = eTimer()
        self.uiTimer.callback.append(self.updateUI)

        self.autoTimer = eTimer()
        self.autoTimer.callback.append(self.autoRefresh)
        if self.autoEnabled:
            self.autoTimer.start(AUTO_REFRESH, False)

        threading.Thread(target=self.loadFeedsThread, daemon=True).start()

    def loadFeedsThread(self):
        self.feeds, self.fromCache = getFeeds()
        self.lastUpdate = time.strftime("%H:%M")
        self.uiTimer.start(0, True)

    def refreshFeeds(self):
        self["status"].setText("Refreshing feeds...")
        threading.Thread(target=self.loadFeedsThread, daemon=True).start()

    def autoRefresh(self):
        if not self.autoEnabled:
            return
        self["status"].setText("Auto refreshing feeds...")
        threading.Thread(target=self.loadFeedsThread, daemon=True).start()

    def toggleAutoRefresh(self):
        self.autoEnabled = not self.autoEnabled
        saveAutoSetting(self.autoEnabled)
        if self.autoEnabled:
            self.autoTimer.start(AUTO_REFRESH, False)
        else:
            self.autoTimer.stop()
        self.updateUI()

    def updateUI(self):
        self["list"].setList([FeedEntry(f) for f in self.feeds])
        src = "Cached" if self.fromCache else "Live"
        auto = "ON" if self.autoEnabled else "OFF"
        self["status"].setText(
            "%s feeds: %d | Auto: %s | Updated: %s"
            % (src, len(self.feeds), auto, self.lastUpdate)
        )

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

    def quickTune(self):
        cur = self["list"].getCurrent()
        if not cur:
            return
        feed = cur[0]

        try:
            fe = eDVBFrontendParametersSatellite()
            fe.frequency = feed["freq"] * 1000
            fe.symbol_rate = feed["sr"] * 1000
            fe.polarisation = (
                fe.Polarisation_Horizontal
                if feed["pol"] == "H"
                else fe.Polarisation_Vertical
            )
            fe.fec = fe.FEC_Auto
            fe.system = fe.System_Auto
            fe.modulation = fe.Modulation_Auto
            fe.orbital_position = feed["orbital"]

            ref = eServiceReference(
                eServiceReference.idDVB,
                eServiceReference.flagDirectory,
                0
            )
            ref.setData(0, fe)

            self.session.nav.playService(ref)
            self["status"].setText("Watching (not saved)")
        except:
            self["status"].setText("Tune failed")

    def close(self):
        try:
            self.autoTimer.stop()
        except:
            pass
        saveAutoSetting(self.autoEnabled)
        Screen.close(self)

# ==================================================
# Plugin Entry
# ==================================================
def main(session, **kwargs):
    session.open(FeedsScreen)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="Feed-Hunter",
        description="Feed Scanner + Quick Watch (Python 3)",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="icon.png",
        fnc=main
    )
