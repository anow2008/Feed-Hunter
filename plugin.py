# -*- coding: utf-8 -*-
# Feed-Hunter Plugin for Enigma2
# Scrape Satelliweb Feeds + Quick Watch + Auto Bouquet (No Duplicates)

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
import os

URL = "https://www.satelliweb.com/index.php?section=livef"

# ==================================================
# Helpers
# ==================================================

def satToOrbital(text):
    """
    Convert '7.0°E' -> 70
    Convert '7.0°W' -> 3600 - 70
    """
    m = re.search(r"(\d+(?:\.\d+)?)°\s*([EW])", text)
    if not m:
        return 0
    pos = int(float(m.group(1)) * 10)
    if m.group(2) == "W":
        pos = 3600 - pos
    return pos


def feedKey(feed):
    """ Unique key to prevent duplicates in bouquet """
    return "#FHKEY:%s:%d:%s:%d\n" % (
        feed["orbital"],
        feed["freq"],
        feed["pol"],
        feed["sr"]
    )

# ==================================================
# Fetch Feeds (Thread-safe)
# ==================================================

def getFeeds():
    feeds = []
    try:
        r = requests.get(URL, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        for div in soup.find_all("div", class_="feed"):
            text = div.get_text("\n").strip()
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            satname = lines[0] if lines else "Unknown"

            feed = {
                "sat": satname,
                "orbital": satToOrbital(satname),
                "freq": 0,
                "pol": "H",
                "sr": 0,
                "event": lines[-1] if len(lines) > 1 else "No Title",
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
        print("[Feed-Hunter] Fetch error:", e)

    return feeds

# ==================================================
# List Entry
# ==================================================

def FeedEntry(feed):
    color = gRGB(0, 220, 0) if not feed["encrypted"] else gRGB(220, 0, 0)

    return [
        feed,
        MultiContentEntryText(
            pos=(10, 5), size=(860, 30),
            font=0, color=color,
            text="%s | %d %s %d" % (
                feed["sat"],
                feed["freq"],
                feed["pol"],
                feed["sr"]
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

        self["status"] = StaticText("Connecting to Satelliweb...")

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"], {
                "ok": self.actionOk,
                "green": self.saveToBouquet,
                "blue": self.quickTune,
                "cancel": self.close,
                "up": self["list"].up,
                "down": self["list"].down,
            }, -1
        )

        self.uiTimer = eTimer()
        self.uiTimer.callback.append(self.updateUI)

        threading.Thread(
            target=self.loadFeedsThread,
            daemon=True
        ).start()

    # ------------------
    # Thread Worker
    # ------------------
    def loadFeedsThread(self):
        self.feeds = getFeeds()
        self.uiTimer.start(0, True)

    # ------------------
    # UI Update
    # ------------------
    def updateUI(self):
        self["list"].setList([FeedEntry(f) for f in self.feeds])
        self["status"].setText(
            "OK: Save+Scan | GREEN: Save | BLUE: Watch"
        )

    # ------------------
    # Save to Bouquet (No duplicates)
    # ------------------
    def saveToBouquet(self, show_msg=True):
        cur = self["list"].getCurrent()
        if not cur:
            return False

        feed = cur[0]
        b_name = "userbouquet.feed_hunter.tv"
        b_path = "/etc/enigma2/" + b_name
        key = feedKey(feed)

        try:
            # Ensure bouquet is listed
            if os.path.exists("/etc/enigma2/bouquets.tv"):
                with open("/etc/enigma2/bouquets.tv", "r+") as f:
                    content = f.read()
                    if b_name not in content:
                        f.write(
                            '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet\n'
                            % b_name
                        )

            # Prevent duplicates
            if os.path.exists(b_path):
                with open(b_path, "r") as f:
                    if key in f.read():
                        if show_msg:
                            self["status"].setText("Feed already saved")
                        return False

            # Append feed
            with open(b_path, "a") as f:
                if os.path.getsize(b_path) == 0:
                    f.write("#NAME Feed-Hunter\n")

                namespace = (feed["orbital"] << 16)
                s_ref = "1:0:1:1:1:1:%X:0:0:0:" % (namespace & 0xFFFFFFFF)

                f.write(key)
                f.write("#SERVICE %s\n" % s_ref)
                f.write("#DESCRIPTION %s (%s)\n" %
                        (feed["event"], feed["sat"]))

            if show_msg:
                self["status"].setText("Saved to Feed-Hunter bouquet")
            return True

        except Exception as e:
            print("[Feed-Hunter] Save error:", e)
            if show_msg:
                self["status"].setText("Save failed")
            return False

    # ------------------
    # OK = Save + Scan
    # ------------------
    def actionOk(self):
        cur = self["list"].getCurrent()
        if not cur:
            return

        self.saveToBouquet(show_msg=False)
        feed = cur[0]

        try:
            nim = nimmanager.getNimListOfType("DVB-S")[0]
            tp = {
                "frequency": feed["freq"],
                "symbol_rate": feed["sr"],
                "polarization": 0 if feed["pol"] == "H" else 1,
                "fec_inner": 0,
                "system": 0,
                "modulation": 0,
                "orbital_position": feed["orbital"]
            }
            self.session.open(ServiceScan, nim, transponder=tp, scanList=[tp])
        except:
            self["status"].setText("No tuner available")

    # ------------------
    # BLUE = Quick Watch
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
            fe.orbital_position = feed["orbital"]
            fe.polarisation = 0 if feed["pol"] == "H" else 1
            fe.fec = 0
            fe.system = 0
            fe.modulation = 0

            ref = eServiceReference(
                eServiceReference.idDVB,
                eServiceReference.flagDirectory,
                0
            )
            ref.setData(0, fe)

            self.session.nav.playService(ref)
            self["status"].setText("Watching: %s" % feed["event"])
        except:
            self["status"].setText("Tuning failed")

# ==================================================
# Plugin Descriptor
# ==================================================

def main(session, **kwargs):
    session.open(FeedsScreen)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="Feed-Hunter",
        description="Scrape, Watch & Save Satellite Feeds",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="icon.png",
        fnc=main
    )
