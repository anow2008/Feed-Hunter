# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from enigma import eServiceReference
import requests
from bs4 import BeautifulSoup
import re

URL = "https://www.satelliweb.com/index.php?section=livef"

# ==============================
# Parser للبيانات باستخدام BeautifulSoup
# ==============================
def getFeeds():
    feeds = []
    try:
        r = requests.get(URL, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        feed_divs = soup.find_all("div", class_="feed")

        if not feed_divs:
            print("Warning: feed structure might have changed!")

        for div in feed_divs:
            text = div.get_text(separator="\n").strip()
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            feed = {}

            # القمر
            feed["sat"] = lines[0] if len(lines) > 0 else "Unknown"

            # التردد + Pol + SR + FEC
            match = re.search(r"Frequency:\s*(\d+)\s*-\s*Pol:\s*([HV])\s*-\s*SR:\s*(\d+)\s*-\s*FEC:\s*([\w/]+|-)", text)
            if match:
                feed["freq"] = int(match.group(1))
                feed["pol"] = match.group(2)
                feed["sr"] = int(match.group(3))
                feed["fec"] = match.group(4) if match.group(4) != '-' else 'Auto'
            else:
                feed["freq"] = feed["sr"] = 0
                feed["pol"] = "H"
                feed["fec"] = "Auto"

            # الفئة
            match_cat = re.search(r"Category:\s*(.+)", text)
            feed["category"] = match_cat.group(1) if match_cat else "N/A"

            # الحدث
            feed["event"] = lines[-1] if len(lines) > 1 else ""

            # مشفر/FTA (نفترض FTA لأن الموقع الجديد لا يحدد)
            feed["encrypted"] = False

            feeds.append(feed)

    except Exception as e:
        print("Error fetching feeds:", e)

    return feeds

# ==============================
# شاشة العرض مع الفلاتر
# ==============================
class FeedsScreen(Screen):
    skin = """
    <screen position="center,center" size="900,550" title="Satelliweb Live Feeds">
        <widget name="list" position="10,10" size="880,440"/>
        <widget name="status" position="10,455" size="880,40" font="Regular;22"/>
        <widget name="buttons" position="10,500" size="880,40" font="Regular;22"/>
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.all_feeds = getFeeds()
        self.filtered_feeds = self.all_feeds.copy()
        self.list = []
        self["list"] = MenuList(self.list)
        self["status"] = StaticText("Ready")
        self["buttons"] = StaticText("Filters: [F1]FTA  [F2]By Sat  [F3]By Category")
        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.tuneFeed,
                "cancel": self.close,
                "up": self["list"].up,
                "down": self["list"].down,
                "red": self.filterFTA,
                "green": self.filterSat,
                "yellow": self.filterCategory
            },
            -1
        )
        self.loadFeeds()

    def loadFeeds(self):
        self.list.clear()
        if not self.filtered_feeds:
            self["status"].setText("No feeds found.")
            self["list"].setList([])
            return
        for f in self.filtered_feeds:
            txt = "%s | %d %s %d | %s" % (
                f["sat"],
                f["freq"],
                f["pol"],
                f["sr"],
                "Encrypted" if f["encrypted"] else "FTA"
            )
            details = "%s\n%s" % (f["category"], f["event"])
            self.list.append(((txt, details), f))
        self["list"].setList(self.list)
        self["status"].setText("Ready")

    # ==============================
    # التصفية
    # ==============================
    def filterFTA(self):
        self.filtered_feeds = [f for f in self.all_feeds if not f["encrypted"]]
        self["status"].setText("Filtered: FTA only")
        self.loadFeeds()

    def filterSat(self):
        sats = sorted(list({f["sat"] for f in self.all_feeds}))
        if not sats:
            return
        def onSelect(choice):
            if choice is not None:
                self.filtered_feeds = [f for f in self.all_feeds if f["sat"] == choice]
                self["status"].setText(f"Filtered: Sat {choice}")
                self.loadFeeds()
        self.session.openWithCallback(onSelect, ChoiceBox, title="Select Satellite", list=sats)

    def filterCategory(self):
        categories = sorted(list({f["category"] for f in self.all_feeds}))
        if not categories:
            return
        def onSelect(choice):
            if choice is not None:
                self.filtered_feeds = [f for f in self.all_feeds if f["category"] == choice]
                self["status"].setText(f"Filtered: Category {choice}")
                self.loadFeeds()
        self.session.openWithCallback(onSelect, ChoiceBox, title="Select Category", list=categories)

    # ==============================
    # تشغيل التردد
    # ==============================
    def tuneFeed(self):
        feed = self["list"].getCurrent()[1]
        self["status"].setText("Tuning...")
        try:
            pol_map = {"H": 0, "V": 1}
            pol = pol_map.get(feed["pol"].upper(), 0)
            freq = feed["freq"]
            sr = feed["sr"]
            fec_map = {"1/2": 2, "2/3": 3, "3/4": 4, "5/6": 5, "7/8": 6, "Auto": 0}
            fec = fec_map.get(feed["fec"], 0)
            ref_str = "1:0:1:%d:%d:%d:%d:0:0:0:" % (freq, pol, sr, fec)
            ref = eServiceReference(ref_str)
            self.session.nav.playService(ref)
            self["status"].setText("Tuned to %d %s" % (freq, feed["pol"]))
        except Exception as e:
            # fallback attempt for images that may not support direct tuning
            try:
                ref_str = "1:0:19:%d:%d:%d:%d:0:0:0:" % (freq, pol, sr, fec)
                ref = eServiceReference(ref_str)
                self.session.nav.playService(ref)
                self["status"].setText("Tuned (fallback) to %d %s" % (freq, feed["pol"]))
            except:
                self["status"].setText("Error tuning feed. Your image may not support it.")
                print("Error tuning feed:", e)

# ==============================
# دخول البلجن من Menu
# ==============================
def main(session, **kwargs):
    session.open(FeedsScreen)

def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="Live Feeds",
            description="Live Satellite Feeds from Satelliweb with Filters",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=main
        )
    ]
