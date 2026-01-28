
# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
import requests
import re

URL = "https://www.satelliweb.com/index.php?section=livef"

# ==============================
# Parser للبيانات
# ==============================
def getFeeds():
    feeds = []
    try:
        r = requests.get(URL, timeout=10)
        text = r.text

        # تقسيم الصفحة على كل block لكل feed
        blocks = re.findall(r'(?:Eutelsat.*?ℹW:.*?)(?=<)', text, flags=re.DOTALL)

        for b in blocks:
            feed = {}
            # القمر
            sat = re.search(r'\(([\d\.]+°[EW])\)', b)
            feed["sat"] = sat.group(1) if sat else "Unknown"

            # التردد
            freq = re.search(r'Frequency:\s*(\d+)', b)
            feed["freq"] = int(freq.group(1)) if freq else 0

            # Polarisation
            pol = re.search(r'Pol:\s*([HV])', b)
            feed["pol"] = pol.group(1) if pol else "H"

            # Symbol Rate
            sr = re.search(r'SR:\s*(\d+)', b)
            feed["sr"] = int(sr.group(1)) if sr else 0

            # FEC
            fec = re.search(r'FEC:\s*([^\n\r]*)', b)
            feed["fec"] = fec.group(1).strip() if fec else "Auto"

            # التشفير
            feed["encrypted"] = "crypté" in b.lower() or "encrypted" in b.lower()

            # Category
            cat = re.search(r'Category:\s*([^\n\r]+)', b)
            feed["category"] = cat.group(1).strip() if cat else "N/A"

            # Event name
            event = re.search(r'ℹW:(.+)', b)
            feed["event"] = event.group(1).strip() if event else ""

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
            # السطر الرئيسي
            txt = "%s | %d %s %d | %s" % (
                f["sat"],
                f["freq"],
                f["pol"],
                f["sr"],
                "Encrypted" if f["encrypted"] else "FTA"
            )
            # تفاصيل الحدث
            details = "%s\n%s" % (f["category"], f["event"])
            self.list.append(((txt, details), f))
        self["list"].setList(self.list)

    def tuneFeed(self):
        feed = self["list"].getCurrent()[1]
        print("TUNING TO:", feed)
        # هنا ممكن تضيف التردد مباشرة إلى الـ frontend
        # مثال: self.session.nav.playService(...) 
        # أو blind scan على التردد

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
