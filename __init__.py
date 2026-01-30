# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Sources.StaticText import StaticText
from Components.MultiContent import MultiContentEntryText
from enigma import (
    eServiceReference,
    eListboxPythonMultiContent,
    eDVBFrontendParametersSatellite,
    gFont,
    gRGB
)
import re

# ---- Safe imports ----
try:
    import requests
    from bs4 import BeautifulSoup
except:
    requests = None
    BeautifulSoup = None

URL = "https://www.satelliweb.com/index.php?section=livef"

# ==================================================
# Fetch & Parse Feeds
# ==================================================
def getFeeds():
    feeds = []

    if not requests or not BeautifulSoup:
        return feeds

    try:
        r = requests.get(URL, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        for div in soup.find_all("div", class_="feed"):
            text = div.get_text(separator="\n").strip()
            lines = [l.strip() for l in text.split("\n") if l.strip()]

            feed = {
                "sat": lines[0] if lines else "Unknown",
                "freq": 0,
                "pol": "H",
                "sr": 0,
                "fec": "Auto",
                "category": "N/A",
                "event": lines[-1] if len(lines) > 1 else "",
                "encrypted": False,
                "encryption": "FTA"
            }

            m = re.search(
                r"Frequency:\s*(\d+)\s*-\s*Pol:\s*([HV])\s*-\s*SR:\s*(\d+)\s*-\s*FEC:\s*([\w/]+|-)",
                text
            )
            if m:
                feed["freq"] = int(m.group(1))
                feed["pol"] = m.group(2)
                feed["sr"] = int(m.group(3))
                feed["fec"] = m.group(4) if m.group(4) != "-" else "Auto"

            c = re.search(r"Category:\s*(.+)", text)
            if c:
                feed["category"] = c.group(1)

            # ---- Encryption detection (UPDATED) ----
            if re.search(r"Encrypted|Scrambled|BISS|PowerVu|crypté|crypt", text, re.I):
                feed["encrypted"] = True
                feed["encryption"] = "BISS/Crypt"

            feeds.append(feed)

    except Exception as e:
        print("Feed error:", e)

    return feeds

# ==================================================
# MultiContent Entry
# ==================================================
def FeedEntry(feed):
    color = gRGB(0, 255, 0) if not feed["encrypted"] else gRGB(255, 0, 0)

    return [
        feed,
        MultiContentEntryText(
            pos=(10, 5), size=(860, 30),
            font=0,
            color=color,
            text="%s | %d %s %d | %s" % (
                feed["sat"], feed["freq"],
                feed["pol"], feed["sr"],
                feed["encryption"]
            )
        ),
        MultiContentEntryText(
            pos=(10, 35), size=(860, 25),
            font=1,
            text="%s - %s" % (feed["category"], feed["event"])
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

        self["status"] = StaticText("Loading feeds...")

        self.all_feeds = getFeeds()
        self.filtered_feeds = self.all_feeds[:]

        self["list"] = MenuList(
            [], enableWrapAround=True,
            content=eListboxPythonMultiContent
        )
        self["list"].l.setItemHeight(65)
        self["list"].l.setFont(0, gFont("Regular", 22))
        self["list"].l.setFont(1, gFont("Regular", 18))

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"], {
                "ok": self.tuneFeed,
                "cancel": self.close,
                "up": self["list"].up,
                "down": self["list"].down,
                "red": self.filterFTA,
                "green": self.filterSat,
                "yellow": self.filterCategory,
            }, -1
        )

        if not self.all_feeds:
            self["status"].setText("No feeds or missing libraries")
        else:
            self.loadFeeds()

    def loadFeeds(self):
        self["list"].setList([FeedEntry(f) for f in self.filtered_feeds])
        self["status"].setText("Feeds: %d" % len(self.filtered_feeds))

    # ------------------
    # Filters
    # ------------------
    def filterFTA(self):
        self.filtered_feeds = [f for f in self.all_feeds if not f["encrypted"]]
        self.loadFeeds()

    def filterSat(self):
        sats = sorted({f["sat"] for f in self.all_feeds})
        self.session.openWithCallback(
            lambda c: self.applyFilter("sat", c),
            ChoiceBox, title="Select Satellite", list=sats
        )

    def filterCategory(self):
        cats = sorted({f["category"] for f in self.all_feeds})
        self.session.openWithCallback(
            lambda c: self.applyFilter("category", c),
            ChoiceBox, title="Select Category", list=cats
        )

    def applyFilter(self, key, value):
        if value:
            value = value[0]
            self.filtered_feeds = [
                f for f in self.all_feeds if f[key] == value
            ]
            self.loadFeeds()

    # ------------------
    # Tune (PROPER DVB)
    # ------------------
    def tuneFeed(self):
        cur = self["list"].getCurrent()
        if not cur:
            return

        feed = cur[0]

        try:
            pol_map = {
                "H": eDVBFrontendParametersSatellite.Polarisation_Horizontal,
                "V": eDVBFrontendParametersSatellite.Polarisation_Vertical
            }

            fec_map = {
                "1/2": eDVBFrontendParametersSatellite.FEC_1_2,
                "2/3": eDVBFrontendParametersSatellite.FEC_2_3,
                "3/4": eDVBFrontendParametersSatellite.FEC_3_4,
                "5/6": eDVBFrontendParametersSatellite.FEC_5_6,
                "7/8": eDVBFrontendParametersSatellite.FEC_7_8,
                "Auto": eDVBFrontendParametersSatellite.FEC_Auto
            }

            feparm = eDVBFrontendParametersSatellite()
            feparm.frequency = feed["freq"] * 1000
            feparm.symbol_rate = feed["sr"] * 1000
            feparm.polarisation = pol_map.get(
                feed["pol"],
                eDVBFrontendParametersSatellite.Polarisation_Horizontal
            )
            feparm.fec = fec_map.get(
                feed["fec"],
                eDVBFrontendParametersSatellite.FEC_Auto
            )
            feparm.inversion = eDVBFrontendParametersSatellite.Inversion_Unknown
            feparm.system = eDVBFrontendParametersSatellite.System_DVB_S
            feparm.modulation = eDVBFrontendParametersSatellite.Modulation_QPSK
            feparm.orbital_position = 0

            ref = eServiceReference(
                eServiceReference.idDVB,
                eServiceReference.flagDirectory,
                0
            )
            ref.setData(0, feparm)

            self.session.nav.playService(ref)
            self["status"].setText("Tuned successfully")

        except Exception:
            self.session.open(
                MessageBox,
                "Tuning failed",
                MessageBox.TYPE_ERROR
            )

# ==================================================
# Plugin Entry
# ==================================================
def main(session, **kwargs):
    session.open(FeedsScreen)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="Feed-Hunter",
        description="Live Satellite Feeds Viewer",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="icon.png",
        fnc=main
    )
