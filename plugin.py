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
    eServiceReference,
    eListboxPythonMultiContent,
    gFont,
    gRGB,
    eTimer,
    eDVBFrontendParametersSatellite
)

import threading
import requests
from bs4 import BeautifulSoup
import re

URL = "https://www.satelliweb.com/index.php?section=livef"

# ==================================================
# Fetch feeds (NO UI here)
# ==================================================
def getFeeds():
    feeds = []
    try:
        r = requests.get(URL, timeout=8)
        soup = BeautifulSoup(r.text, "html.parser")

        for div in soup.find_all("div", class_="feed"):
            text = div.get_text("\n").strip()
            lines = [l.strip() for l in text.split("\n") if l.strip()]

            feed = {
                "sat": lines[0] if lines else "Unknown",
                "freq": 0,
                "pol": "H",
                "sr": 0,
                "event": lines[-1] if len(lines) > 1 else "",
                "encrypted": False
            }

            m = re.search(
                r"Frequency:\s*(\d+)\s*-\s*Pol:\s*([HV])\s*-\s*SR:\s*(\d+)",
                text
            )
            if m:
                feed["freq"] = int(m.group(1))
                feed["pol"] = m.group(2)
                feed["sr"] = int(m.group(3))

            if re.search(
                r"Encrypted|Scrambled|BISS|PowerVu|crypté|crypt",
                text, re.I
            ):
                feed["encrypted"] = True

            feeds.append(feed)

    except Exception as e:
        print("Feed error:", e)

    return feeds

# ==================================================
# List Entry
# ==================================================
def FeedEntry(feed):
    color = gRGB(0, 200, 0) if not feed["encrypted"] else gRGB(220, 0, 0)

    return [
        feed,
        MultiContentEntryText(
            pos=(10, 5), size=(860, 30),
            font=0,
            color=color,
            text="%s | %d %s %d" % (
                feed["sat"], feed["freq"], feed["pol"], feed["sr"]
            )
        ),
        MultiContentEntryText(
            pos=(10, 35), size=(860, 25),
            font=1,
            text=feed["event"]
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

        self["list"] = MenuList(
            [],
            enableWrapAround=True,
            content=eListboxPythonMultiContent
        )
        self["list"].l.setItemHeight(65)
        self["list"].l.setFont(0, gFont("Regular", 22))
        self["list"].l.setFont(1, gFont("Regular", 18))

        self["status"] = StaticText("Loading feeds...")

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"], {
                "ok": self.openManualScan,
                "blue": self.quickTune,
                "cancel": self.close,
                "up": self["list"].up,
                "down": self["list"].down,
            }, -1
        )

        # Timer to safely update UI
        self.uiTimer = eTimer()
        self.uiTimer.callback.append(self.updateUI)

        # Start background thread
        threading.Thread(
            target=self.loadFeedsThread,
            daemon=True
        ).start()

    # ------------------
    # Thread worker
    # ------------------
    def loadFeedsThread(self):
        self.feeds = getFeeds()
        self.uiTimer.start(0, True)

    # ------------------
    # UI update (Main Thread)
    # ------------------
    def updateUI(self):
        self["list"].setList([FeedEntry(f) for f in self.feeds])
        self["status"].setText(
            "OK: Scan | Blue: Watch | Feeds: %d" % len(self.feeds)
        )

    # ------------------
    # OK = Manual Scan
    # ------------------
    def openManualScan(self):
        cur = self["list"].getCurrent()
        if not cur:
            return

        feed = cur[0]
        nim = nimmanager.getNimListOfType("DVB-S")[0]

        transponder = {
            "frequency": feed["freq"],
            "symbol_rate": feed["sr"],
            "polarization": 0 if feed["pol"] == "H" else 1,
            "fec_inner": 0,
            "system": 0,
            "modulation": 0,
            "orbital_position": 0
        }

        self.session.open(
            ServiceScan,
            nim,
            transponder=transponder,
            scanList=[transponder]
        )

    # ------------------
    # Blue = Quick Watch
    # ------------------
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
                eDVBFrontendParametersSatellite.Polarisation_Horizontal
                if feed["pol"] == "H"
                else eDVBFrontendParametersSatellite.Polarisation_Vertical
            )
            fe.fec = eDVBFrontendParametersSatellite.FEC_Auto
            fe.inversion = eDVBFrontendParametersSatellite.Inversion_Unknown
            fe.system = eDVBFrontendParametersSatellite.System_Auto
            fe.modulation = eDVBFrontendParametersSatellite.Modulation_Auto
            fe.orbital_position = 0

            ref = eServiceReference(
                eServiceReference.idDVB,
                eServiceReference.flagDirectory,
                0
            )
            ref.setData(0, fe)

            self.session.nav.playService(ref)
            self["status"].setText("Watching (not saved)")

        except Exception:
            self["status"].setText("Tune failed")

# ==================================================
# Plugin Entry
# ==================================================
def main(session, **kwargs):
    session.open(FeedsScreen)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="Feed-Hunter",
        description="Feed Scanner + Quick Watch",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="icon.png",
        fnc=main
    )
