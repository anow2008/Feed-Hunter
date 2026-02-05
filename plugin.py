# -*- coding: utf-8 -*-
# السطر أعلاه ضروري جداً لقراءة الحروف العربية ورموز الدرجات المدارية

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.NimManager import nimmanager
from Components.Listbox import Listbox
from Components.MultiContent import MultiContentEntryText
from enigma import eListboxPythonMultiContent, gFont, eTimer, getDesktop
import re
import threading

# محاولة استدعاء مكتبة requests
try:
    import requests
except ImportError:
    requests = None

URL = "https://www.satelliweb.com/index.php?section=livef"
dSize = getDesktop(0).size()
isFHD = dSize.width() > 1280

def satToOrbital(txt):
    try:
        # البحث عن الموقع المداري مثل 7.0°E أو 30.0°W
        m = re.search(r"(\d+\.?\d*)\s*°?\s*([EW])", str(txt), re.I)
        if not m: return 0
        pos = float(m.group(1))
        direction = m.group(2).upper()
        if direction == 'W':
            return int((360 - pos) * 10)
        return int(pos * 10)
    except:
        return 0

def FeedEntry(f):
    width = 1100 if isFHD else 800
    res = [f]
    # التأكد من تحويل كل القيم إلى نصوص (String) لتجنب كراش Py3
    title = str(f.get("event", "No Name"))
    details = "{} | {} {} {} | {}".format(str(f['sat']), str(f['freq']), str(f['pol']), str(f['sr']), str(f['desc']))
    
    res.append(MultiContentEntryText(pos=(10, 5), size=(width, 45 if isFHD else 30), font=0, color=0xFFFFFF, text=title))
    res.append(MultiContentEntryText(pos=(10, 50 if isFHD else 35), size=(width, 40 if isFHD else 25), font=1, color=0x00FF00, text=details))
    return res

class FeedHunter(Screen):
    if isFHD:
        skin = """
        <screen name="FeedHunter" position="center,center" size="1200,820" title="Feed Hunter Pro v1.7 (Py3)">
            <widget name="list" position="20,20" size="1160,650" scrollbarMode="showOnDemand" transparent="1" />
            <eLabel position="20,680" size="1160,2" backgroundColor="#555555" />
            <widget source="status" render="Label" position="20,700" size="1160,80" font="Regular;30" halign="center" valign="center" foregroundColor="#00FF00" />
        </screen>"""
    else:
        skin = """
        <screen name="FeedHunter" position="center,center" size="850,550" title="Feed Hunter Pro v1.7 (Py3)">
            <widget name="list" position="15,15" size="820,420" scrollbarMode="showOnDemand" transparent="1" />
            <eLabel position="15,450" size="820,1" backgroundColor="#555555" />
            <widget source="status" render="Label" position="15,465" size="820,60" font="Regular;22" halign="center" valign="center" foregroundColor="#00FF00" />
        </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.feeds = []
        self.is_fetching = False
        self["list"] = Listbox([])
        self["list"].l.setBuildFunc(FeedEntry)
        
        if isFHD:
            self["list"].l.setItemHeight(100)
            self["list"].l.setFont(0, gFont("Regular", 34))
            self["list"].l.setFont(1, gFont("Regular", 28))
        else:
            self["list"].l.setItemHeight(70)
            self["list"].l.setFont(0, gFont("Regular", 24))
            self["list"].l.setFont(1, gFont("Regular", 18))
        
        self["status"] = StaticText("جاري الاتصال بالموقع...")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.startScan, 
            "cancel": self.close, 
            "red": self.close, 
            "green": self.reloadData
        }, -1)
        
        self.timer = eTimer()
        # التعديل هنا ليتوافق مع جميع اصدارات الصور
        try:
            self.timer.timeout.connect(self.updateUI)
        except:
            self.timer_conn = self.timer.timeout.connect(self.updateUI)

        self.onClose.append(self.cleanup)
        # تشغيل جلب البيانات تلقائياً عند الفتح
        self.reloadData()

    def cleanup(self):
        if self.timer.isActive(): self.timer.stop()

    def reloadData(self):
        if not requests:
            self["status"].setText("خطأ: مكتبة requests غير مثبتة!")
            return
        if self.is_fetching: return
        self.is_fetching = True
        self["status"].setText("جاري جلب الفيدات من Satelliweb...")
        threading.Thread(target=self.fetchFeeds, daemon=True).start()

    def fetchFeeds(self):
        new_feeds = []
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(URL, timeout=15, headers=headers)
            response.encoding = 'utf-8' # ضمان قراءة الحروف الخاصة صحيحة
            html = response.text
            
            # نمط بحث Regex أكثر مرونة لاصطياد البيانات حتى لو تغير تصميم الموقع قليلاً
            pattern = r"(\d+\.\d°[EW]).*?Frequency:.*?<b>(\d+)</b>.*?Pol:.*?<b>([HV])</b>.*?SR:.*?<b>(\d+)</b>.*?ℹ\s*(.*?)(?=<)"
            matches = re.findall(pattern, html, re.S | re.I)
            
            for (sat, freq, pol, sr, event) in matches:
                # تنظيف اسم الحدث من اي اكواد HTML
                clean_event = re.sub(r'<[^>]+>', '', event).strip()
                new_feeds.append({
                    "sat": sat,
                    "orbital": satToOrbital(sat),
                    "freq": int(freq),
                    "pol": pol.upper(),
                    "sr": int(sr),
                    "event": clean_event if clean_event else "Live Feed",
                    "desc": "Feed"
                })
        except Exception as e:
            print("[FeedHunter] Error: ", str(e))
            
        self.feeds = new_feeds
        self.is_fetching = False
        self.timer.start(100, True)

    def updateUI(self):
        self["list"].setList(self.feeds)
        if self.feeds:
            status = "تم العثور على {} فيد | [OK] بحث | [GREEN] تحديث".format(len(self.feeds))
        else:
            status = "لم يتم العثور على فيدات حالياً!"
        self["status"].setText(status)

    def startScan(self):
        selection = self["list"].getCurrent()
        if not selection: return
        f = selection[0]
        
        tuner_slot = -1
        for slot in nimmanager.nim_slots:
            if slot.isCompatible("DVB-S"):
                tuner_slot = slot.slot
                break
        
        if tuner_slot == -1: return

        # إعدادات التيونر للبحث عن الفيد
        tp = {
            "type": "S2",
            "frequency": f["freq"] * 1000, 
            "symbol_rate": f["sr"] * 1000, 
            "polarization": 0 if f["pol"] == "H" else 1,
            "fec_inner": 0, "system": 1, "modulation": 2, "inversion": 2, "roll_off": 3, "pilot": 2,
            "orbital_position": f["orbital"]
        }
        
        try:
            from Screens.ServiceScan import ServiceScan
            self.session.open(ServiceScan, tuner_slot, transponder=tp, scanList=[tp])
        except:
            pass

def main(session, **kwargs):
    session.open(FeedHunter)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="Feed Hunter",
        description="Satelliweb Live Feeds (Py3 Ready)",
        where=PluginDescriptor.WHERE_PLUGINMENU, 
        fnc=main, 
        icon="plugin.png"
    )
