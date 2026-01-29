# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from enigma import eServiceReference, eListboxPythonMultiContent, gFont
from Components.MultiContent import MultiContentEntryText
from Components.MenuList import MenuList
import requests
from bs4 import BeautifulSoup
import re

URL = "https://www.satelliweb.com/index.php?section=livef"

# ==============================
# Fetch & Parse Feeds
# ==============================
def getFeeds():
    feeds = []
    try:
        r = requests.get(URL, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        feed_divs = soup.find_all("div", class_="feed")

        for div in feed_divs:
            text = div.get_text(separator="\n").strip()
            lines = [l.strip() for l in text.split("\n") if l.strip()]

            feed = {}
            feed["sat"] = lines[0] if lines else "Unknown"

            match = re.search(
                r"Frequency:\s*(\d+)\s*-\s*Pol:\s*([HV])\s*-\s*SR:\s*(\d+)\s*-\s*FEC:\s*([\w/]+|-)",
                text
            )
            if match:
                feed["freq"] = int(match.group(1))
                feed["pol"] = match.group(2)
                feed["sr"] = int(match.group(3))
                feed["fec"] = match.group(4) if match.group(4) != "-" else "Auto"
            else:
                feed["freq"], feed["sr"] = 0, 0
                feed["pol"], feed["fec"] = "H", "Auto"

            cat = re.search(r"Category:\s*(.+)", text)
            feed["category"] = cat.group(1) if cat else "N/A"
            feed["event"] = lines[-1] if len(lines) > 1 else ""
            feed["encrypted"] = False

            feeds.append(feed)

    except Exception as e:
        print("Feed error:", e)

    return feeds

# ==============================
# Build MultiContent Row
# ==============================
def FeedEntry(feed):
    line1 = "%s | %d %s %d | FTA" % (
        feed["sat"], feed["freq"], feed["pol"], feed["sr"]
    )
    line2 = "%s - %s" % (feed["category"], feed["event"])

    return [
        feed,
        MultiContentEntryText(
            pos=(10, 5), size=(950, 30),
            font=0, text=line1
        ),
        MultiContentEntryText(
            pos=(10, 35), size=(950, 25),
            font=1, text=line2
        ),
    ]

# ==============================
# Main Screen
# ==============================
class FeedsScreen(Screen):
    skin = """
    <screen name="FeedsScreen" title="Satelliweb Live Feeds" position="0,0" size="1000,600">

        <widget name="list" position="10,10" size="980,460" scrollbarMode="showOnDemand"/>

        <widget name="status" position="10,480" size="980,25" font="Regular;20"/>

        <!-- Colored buttons -->
        <ePixmap pixmap="buttons/red.png" position="10,520" size="35,25" alphatest="on"/>
        <widget name="key_red" position="50,520" size="150,25" font="Regular;20"/>

        <ePixmap pixmap="buttons/green.png" position="210,520" size="35,25" alphatest="on"/>
        <widget name="key_green" position="250,520" size="150,25" font="Regular;20"/>

        <ePixmap pixmap="buttons/yellow.png" position="410,520" size="35,25" alphatest="on"/>
        <widget name="key_yellow" position="450,520" size="200,25" font="Regular;20"/>

    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)

        self.all_feeds = getFeeds()
        self.filtered_feeds = self.all_feeds[:]

        self["list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self["list"].l.setItemHeight(65)
        self["list"].l.setFont(0, gFont("Regular", 22))
        self["list"].l.setFont(1, gFont("Regular", 18))

        self["status"] = StaticText("Ready")

        self["key_red"] = StaticText("FTA")
        self["key_green"] = StaticText("Satellite")
        self["key_yellow"] = StaticText("Category")

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.tuneFeed,
                "cancel": self.close,
                "up": self["list"].up,
                "down": self["list"].down,
                "red": self.filterFTA,
                "green": self.filterSat,
                "yellow": self.filterCategory,
            },
            -1
        )

        self.loadFeeds()

    def loadFeeds(self):
        lst = [FeedEntry(f) for f in self.filtered_feeds]
        self["list"].setList(lst)
        self["status"].setText("Feeds: %d" % len(lst))

    # ==============================
    # Filters
    # ==============================
    def filterFTA(self):
        self.filtered_feeds = [f for f in self.all_feeds if not f["encrypted"]]
        self.loadFeeds()

    def filterSat(self):
        sats = sorted(set(f["sat"] for f in self.all_feeds))
        self.session.openWithCallback(
            lambda c: self.applyFilter("sat", c),
            ChoiceBox, title="Select Satellite", list=sats
        )

    def filterCategory(self):
        cats = sorted(set(f["category"] for f in self.all_feeds))
        self.session.openWithCallback(
            lambda c: self.applyFilter("category", c),
            ChoiceBox, title="Select Category", list=cats
        )

    def applyFilter(self, key, value):
        if value:
            self.filtered_feeds = [f for f in self.all_feeds if f[key] == value]
            self.loadFeeds()

    # ==============================
    # Tune
    # ==============================
    def tuneFeed(self):
        feed = self["list"].getCurrent()[0]
        try:
            pol = 0 if feed["pol"] == "H" else 1
            fec_map = {"1/2": 2, "2/3": 3, "3/4": 4, "5/6": 5, "7/8": 6, "Auto": 0}
            fec = fec_map.get(feed["fec"], 0)

            ref = eServiceReference(
                "1:0:1:%d:%d:%d:%d:0:0:0:" %
                (feed["freq"], pol, feed["sr"], fec)
            )
            self.session.nav.playService(ref)
            self["status"].setText("Tuned successfully")
        except:
            self["status"].setText("Tuning failed")

# ==============================
# Plugin Entry
# ==============================
def main(session, **kwargs):
    session.open(FeedsScreen)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="Live Feeds (Satelliweb)",
        description="Professional Live Feeds Viewer",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        fnc=main
    )
