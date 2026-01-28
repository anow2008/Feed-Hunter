# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Button import Button
from enigma import eServiceReference, eSystemInfo
import requests
from bs4 import BeautifulSoup

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

        for div in feed_divs:
            feed = {}
            feed["sat"] = div.find("span", class_="sat").text.strip() if div.find("span", class_="sat") else "Unknown"

            freq_tag = div.find("span", class_="freq")
            feed["freq"] = int(freq_tag.text.strip()) if freq_tag and freq_tag.text.strip().isdigit() else 0

            feed["pol"] = div.find("span", class_="pol").text.strip() if div.find("span", class_="pol") else "H"

            sr_tag = div.find("span", class_="sr")
            feed["sr"] = int(sr_tag.text.strip()) if sr_tag and sr_tag.text.strip().isdigit() else 0

            feed["fec"] = div.find("span", class_="fec").text.strip() if div.find("span", class_="fec") else "Auto"

            enc_tag = div.find("span", class_="enc")
            feed["encrypted"] = "crypté" in enc_tag.text.lower() or "encrypted" in enc_tag.text.lower() if enc_tag else False

            feed["category"] = div.find("span", class_="category").text.strip() if div.find("span", class_="category") else "N/A"

            feed["event"] = div.find("span", class_="event").text.strip() if div.find("span", class_="event") else ""

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
        sats = list({f["sat"] for f in self.all_feeds})
        if not sats:
            return
        # نختار أول قمر كفلتر مؤقت (ممكن تطور لاحقاً لاختيار المستخدم)
        selected_sat = sats[0]
        self.filtered_feeds = [f for f in self.all_feeds if f["sat"] == selected_sat]
        self["status"].setText(f"Filtered: Sat {selected_sat}")
        self.loadFeeds()

    def filterCategory(self):
        categories = list({f["category"] for f in self.all_feeds})
        if not categories:
            return
        # نختار أول فئة كفلتر مؤقت (ممكن تطور لاحقاً لاختيار المستخدم)
        selected_cat = categories[0]
        self.filtered_feeds = [f for f in self.all_feeds if f["category"] == selected_cat]
        self["status"].setText(f"Filtered: Category {selected_cat}")
        self.loadFeeds()

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
            fec_map = {
                "1/2": 2, "2/3": 3, "3/4": 4, "5/6": 5, "7/8": 6,
                "Auto": 0
            }
            fec = fec_map.get(feed["fec"], 0)

            ref_str = "1:0:1:%d:%d:%d:%d:0:0:0:" % (freq, pol, sr, fec)
            ref = eServiceReference(ref_str)

            self.session.nav.playService(ref)
            self["status"].setText("Tuned to %d %s" % (freq, feed["pol"]))

        except Exception as e:
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
