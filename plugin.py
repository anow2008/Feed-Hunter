# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Sources.StaticText import StaticText
from Components.MultiContent import MultiContentEntryText
from enigma import (
    eServiceReference,
    eListboxPythonMultiContent,
    gFont
)
import requests
from bs4 import BeautifulSoup
import re

URL = "https://www.satelliweb.com/index.php?section=livef"

# ==================================================
# Fetch & Parse Feeds
# ==================================================
def getFeeds():
    feeds = []
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
                "encrypted": False
            }

            m = re.search(
                r"Frequency:\s*(\d+)\s*-\s*Pol:\s*([HV])\s*-\s*SR:\s*(\d+)\s*-\s*FEC:\s*([\w/]+|-)",
                text
            )
            if m:
                feed.update({
                    "freq": int(m.group(1)),
                    "pol": m.group(2),
                    "sr": int(m.group(3)),
                    "fec": m.group(4) if m.group(4) != "-" else "Auto"
                })

            c = re.search(r"Category:\s*(.+)", text)
            if c:
                feed["category"] = c.group(1)

            feeds.append(feed)
    except Exception as e:
        print("Feed error:", e)
    return feeds

# ==================================================
# MultiContent Entry
# ==================================================
def FeedEntry(feed):
    return [
        feed,
        MultiContentEntryText(
            pos=(10, 5), size=(860, 30),
            font=0,
            text="%s | %d %s %d | FTA" % (
                feed["sat"], feed["freq"], feed["pol"], feed["sr"]
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

        <widget name="list"
                position="10,10"
                size="880,450"
                scrollbarMode="showOnDemand" />

        <widget name="status"
                position="10,470"
                size="880,30"
                font="Regular;20" />

    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)

        self.all_feeds = getFeeds()
        self.filtered_feeds = self.all_feeds[:]

        self["list"] = MenuList(
            [],
            enableWrapAround=True,
            content=eListboxPythonMultiContent
        )
        self["list"].l.setItemHeight(65)
        self["list"].l.setFont(0, gFont("Regular", 22))
        self["list"].l.setFont(1, gFont("Regular", 18))

        self["status"] = StaticText("Ready")

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
            self.filtered_feeds = [f for f in self.all_feeds if f[key] == value]
            self.loadFeeds()

    # ------------------
    # Tune
    # ------------------
    def tuneFeed(self):
        feed = self["list"].getCurrent()[0]
        try:
            pol = 0 if feed["pol"] == "H" else 1
            fec = {"1/2": 2, "2/3": 3, "3/4": 4,
                   "5/6": 5, "7/8": 6}.get(feed["fec"], 0)

            ref = eServiceReference(
                "1:0:1:%d:%d:%d:%d:0:0:0:" %
                (feed["freq"], pol, feed["sr"], fec)
            )
            self.session.nav.playService(ref)
            self["status"].setText("Tuned successfully")
        except:
            self["status"].setText("Tuning failed")

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
