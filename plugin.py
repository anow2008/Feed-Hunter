# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from enigma import eServiceReference
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
# شاشة العرض
# ==============================
class FeedsScreen(Screen):
    skin = """
    <screen position="center,center" size="900,500" title="Satelliweb Live Feeds">
        <widget name="list" position="10,10" size="880,480"/>
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.list = []
        self["list"] = MenuList(self.list)

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions"],
            {
                "ok": self.tuneFeed,
                "cancel": self.close,
                "up": self["list"].up,
                "down": self["list"].down
            },
            -1
        )

        self.loadFeeds()

    def loadFeeds(self):
        feeds = getFeeds()
        for f in feeds:
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

    def tuneFeed(self):
        feed = self["list"].getCurrent()[1]

        # -------------------------
        # إعداد ServiceReference للتردد
        # -------------------------
        # الصيغة: '1:0:1:frequency:polarization:symbolrate:fec:...'
        # polarization: H=0, V=1
        pol_map = {"H": 0, "V": 1}
        pol = pol_map.get(feed["pol"].upper(), 0)
        freq = feed["freq"]
        sr = feed["sr"]
        fec_map = {
            "1/2": 2, "2/3": 3, "3/4": 4, "5/6": 5, "7/8": 6,
            "Auto": 0
        }
        fec = fec_map.get(feed["fec"], 0)

        # إنشاء ServiceReference
        ref_str = "1:0:1:%d:%d:%d:%d:0:0:0:" % (freq, pol, sr, fec)
        ref = eServiceReference(ref_str)

        # تشغيل التردد على الرسيفر
        self.session.nav.playService(ref)

# ==============================
# دخول البلجن من Menu
# ==============================
def main(session, **kwargs):
    session.open(FeedsScreen)

def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="Live Feeds",
            description="Live Satellite Feeds from Satelliweb",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=main
        )
    ]
