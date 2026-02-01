# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.ServiceScan import ServiceScan
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.NimManager import nimmanager
from Components.Listbox import Listbox
from Components.MultiContent import MultiContentEntryText
from enigma import eListboxPythonMultiContent, gFont, gRGB, eTimer

import re, json, threading

# ================= SAFE IMPORTS =================
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

URL = "https://www.satelliweb.com/index.php?section=livef"

# ================= HELPERS =================
def satToOrbital(txt):
    m = re.search(r"(\d+(?:\.\d+)?)\s*([EW])", txt, re.I)
    if not m: return 0
    p = int(float(m.group(1)) * 10)
    return 3600 - p if m.group(2).upper() == "W" else p

def FeedEntry(f):
    return [
        f,
        # استخدام نظام الألوان Hex لضمان ثبات الشكل على كل الصور
        MultiContentEntryText(pos=(10, 5), size=(760, 30), font=0, color=0x00FF00, text=f"{f['sat']} | {f['freq']} {f['pol']} {f['sr']}"),
        MultiContentEntryText(pos=(10, 35), size=(760, 25), font=1, color=0xFFFFFF, text=f["event"]),
    ]

# ================= SCREEN =================
class FeedHunter(Screen):
    # سكين متوافق مع كافة الشاشات (Full HD & HD)
    skin = """
    <screen name="FeedHunter" position="center,center" size="800,520" title="Feed Hunter Pro">
        <widget name="list" position="10,10" size="780,420" scrollbarMode="showOnDemand" transparent="1" />
        <eLabel position="10,435" size="780,1" backgroundColor="#555555" />
        <widget source="status" render="Label" position="10,445" size="780,60" font="Regular;22" halign="center" valign="center" foregroundColor="#00FF00" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.feeds = []
        self["list"] = Listbox([])
        self["list"].l.setBuildFunc(FeedEntry)
        self["list"].l.setItemHeight(70)
        self["list"].l.setFont(0, gFont("Regular", 22))
        self["list"].l.setFont(1, gFont("Regular", 18))

        self["status"] = StaticText("جاري جلب البيانات من المصدر...")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.scan,
            "cancel": self.close,
            "red": self.close,
            "green": self.reload # تفعيل الزر الأخضر للتحديث
        }, -1)

        self.timer = eTimer()
        self.timer.callback.append(self.updateUI)
        
        # بدء التحميل عند الفتح
        self.reload()

    def reload(self):
        self["status"].setText("جاري التحديث... يرجى الانتظار")
        if requests is None:
            self["status"].setText("خطأ: مكتبة requests غير موجودة في الصورة!")
        else:
            threading.Thread(target=self.loadThread, daemon=True).start()

    def loadThread(self):
        self.feeds = self.getFeedsData()
        self.timer.start(100, True)

    def getFeedsData(self):
        feeds = []
        try:
            # إضافة User-Agent لتجنب الحظر من الموقع
            res = requests.get(URL, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(res.text, "html.parser")
            for div in soup.find_all("div", class_="feed"):
                text = div.get_text(" ", strip=True)
                m = re.search(r"(\d+(?:\.\d+)?[EW]).*?Frequency:\s*(\d+).*?Pol:\s*([HV]).*?SR:\s*(\d+)", text)
                if m:
                    # تنظيف النص من أي وسوم HTML متبقية
                    clean_text = re.sub(r'<[^>]*>', '', text)
                    # استخراج اسم الحدث بذكاء (أول جزء قبل الفاصل)
                    event_name = clean_text.split('|')[0].strip()[:65]
                    
                    feeds.append({
                        "sat": m.group(1),
                        "orbital": satToOrbital(m.group(1)),
                        "freq": int(m.group(2)),
                        "pol": m.group(3),
                        "sr": int(m.group(4)),
                        "event": event_name
                    })
        except Exception as e:
            print("[FeedHunter] Error fetching data:", str(e))
        return feeds

    def updateUI(self):
        self["list"].setList(self.feeds)
        status_msg = f"تم العثور على {len(self.feeds)} فيد\nOK للبحث | الأخضر للتحديث"
        self["status"].setText(status_msg)

    def scan(self):
        cur = self["list"].getCurrent()
        if not cur: return
        f = cur[0]

        nims = getattr(nimmanager, "getNimListOfType", lambda x: [])("DVB-S")
        if not nims:
            self["status"].setText("خطأ: لم يتم العثور على تيونر متاح")
            return

        # إعدادات التردد (DVB-S2 / 8PSK كافتراض ذكي للفيدات)
        tp = {
            "frequency": f["freq"] * 1000,
            "symbol_rate": f["sr"] * 1000,
            "polarization": 0 if f["pol"] == "H" else 1,
            "fec_inner": 0, # Auto
            "system": 1,    # DVB-S2
            "modulation": 2, # 8PSK
            "orbital_position": f["orbital"]
        }

        try:
            self.session.open(ServiceScan, nims[0], transponder=tp, scanList=[tp])
        except Exception as e:
            self["status"].setText("فشل فتح واجهة البحث الرسمية")

# ================= PLUGIN START =================
def main(session, **kwargs):
    session.open(FeedHunter)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="Feed Hunter Pro",
        description="جالب ومستخرج فيدات الأقمار الصناعية مباشر",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        fnc=main,
        icon="plugin.png" # 
    )
