# -*- coding: utf-8 -*-
# تم التطوير بواسطة محمد - نسخة بايثون 3 حصرياً
# نظام عرض جدولي احترافي - سحب بيانات من Satelliweb

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.NimManager import nimmanager
from enigma import eTimer, gFont, RT_HALIGN_LEFT
import re
import threading
import urllib.request as urllib2

# دالة رسم السطر في القائمة ليظهر كأعمدة منظمة
def FeedListEntry(sat, freq, pol, sr, enc):
    res = [(sat, freq, pol, sr)] # البيانات المخفية للاستخدام عند الضغط على OK
    # تصميم الأعمدة: (النص، المسافة من اليسار، المسافة من الأعلى، العرض، الارتفاع، رقم الخط، المحاذاة)
    res.append((sat, 10, 0, 150, 30, 0, RT_HALIGN_LEFT))  # عمود القمر
    res.append((freq, 170, 0, 120, 30, 0, RT_HALIGN_LEFT)) # عمود التردد
    res.append((pol, 300, 0, 50, 30, 0, RT_HALIGN_LEFT))   # عمود القطبية
    res.append((sr, 360, 0, 120, 30, 0, RT_HALIGN_LEFT))   # عمود الترميز
    res.append((enc, 490, 0, 200, 30, 0, RT_HALIGN_LEFT))  # عمود التشفير
    return res

class FeedHunter(Screen):
    # تصميم الواجهة - السكين
    skin = """
    <screen position="center,center" size="900,600" title="Feed Hunter Pro Table (PY3)">
        <eLabel text="Satellite" position="20,10" size="150,30" font="Regular;22" foregroundColor="#F0CA00" />
        <eLabel text="Frequency" position="180,10" size="120,30" font="Regular;22" foregroundColor="#F0CA00" />
        <eLabel text="Pol" position="310,10" size="50,30" font="Regular;22" foregroundColor="#F0CA00" />
        <eLabel text="SR" position="370,10" size="120,30" font="Regular;22" foregroundColor="#F0CA00" />
        <eLabel text="Encryption" position="500,10" size="200,30" font="Regular;22" foregroundColor="#F0CA00" />
        
        <eLabel position="10,45" size="880,2" backgroundColor="#555555" />
        
        <widget name="list" position="10,50" size="880,420" scrollbarMode="showOnDemand" selectionColor="#333333" />
        
        <eLabel position="10,480" size="880,2" backgroundColor="#555555" />
        
        <widget name="status_label" position="10,490" size="880,40" font="Regular;24" halign="center" foregroundColor="#00FF00" />
        <eLabel text="OK: Start Scan | GREEN: Refresh | RED: Exit" position="10,550" size="880,30" font="Regular;20" halign="center" transparent="1" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self["list"] = MenuList([])
        self["status_label"] = Label("جاري الاتصال بـ Satelliweb...")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.startScan,
            "cancel": self.close,
            "red": self.close,
            "green": self.reloadData
        }, -1)
        
        self.timer = eTimer()
        self.timer.timeout.connect(self.updateUI)
        self.onLayoutFinish.append(self.reloadData)

    def reloadData(self):
        self["status_label"].setText("جاري تحديث جدول الفيدات...")
        self.feeds_data = []
        threading.Thread(target=self.fetchData).start()

    def fetchData(self):
        new_list = []
        url = "https://www.satelliweb.com/index.php?section=livef"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            req = urllib2.Request(url, headers=headers)
            with urllib2.urlopen(req, timeout=15) as response:
                html = response.read().decode('utf-8', 'ignore')
                
                # Regex لسحب البيانات من صفوف الجدول في الموقع
                # يبحث عن التردد، القطبية، والترميز
                pattern = r'(\d{5})\s+([HV])\s+(\d{4,5})'
                matches = re.finditer(pattern, html)

                for m in matches:
                    f_val = m.group(1)
                    p_val = m.group(2).upper()
                    sr_val = m.group(3)
                    
                    # استخراج حالة التشفير (BISS, Clear, etc)
                    enc_match = re.search(r'>(BISS|Clear|Encrypted|Nagravision|PowerVU)', html[m.end():m.end()+200], re.I)
                    enc_val = enc_match.group(1) if enc_match else "Unknown"
                    
                    # استخراج اسم القمر القريب من التردد
                    sat_match = re.search(r"(\d+\.?\d*)\s*°\s*([EW])", html[m.start()-200:m.start()])
                    s_name = f"{sat_match.group(1)}{sat_match.group(2)}" if sat_match else "7.0E"
                    
                    # إضافة السطر للقائمة بالتنسيق الجديد
                    new_list.append(FeedListEntry(s_name, f_val, p_val, sr_val, enc_val))
        except Exception as e:
            print(f"[FeedHunter] Error: {e}")
            
        self.feeds_data = new_list
        self.timer.start(100, True)

    def updateUI(self):
        self["list"].setList(self.feeds_data)
        self["status_label"].setText(f"تم العثور على {len(self.feeds_data)} فيد مباشر")

    def startScan(self):
        sel = self["list"].getCurrent()
        if not sel: return
        # استخراج القيم من البيانات المخفية في السطر
        sat_name, freq, pol, sr = sel[0]
        
        # البحث عن الموقع المداري
        orb_pos = 70 # الافتراضي 7 شرق
        m = re.match(r"(\d+\.?\d*)([EW])", sat_name)
        if m:
            pos = float(m.group(1))
            orb_pos = int((360 - pos) * 10) if m.group(2) == 'W' else int(pos * 10)

        tuner_slot = -1
        for slot in nimmanager.nim_slots:
            if slot.isCompatible("DVB-S2"):
                tuner_slot = slot.slot
                break
        
        if tuner_slot != -1:
            # تحضير بيانات التردد للحقن في شاشة البحث
            tp = {
                "type": "S2",
                "frequency": int(freq) * 1000,
                "symbol_rate": int(sr) * 1000,
                "polarization": 0 if pol == "H" else 1,
                "fec_inner": 0,
                "system": 1,
                "modulation": 2,
                "inversion": 2,
                "roll_off": 3,
                "pilot": 2,
                "orbital_position": orb_pos
            }
            try:
                from Screens.ServiceScan import ServiceScan
                self.session.open(ServiceScan, tuner_slot, transponder=tp, scanList=[tp])
            except:
                self["status_label"].setText("خطأ في تشغيل البحث!")

def main(session, **kwargs):
    session.open(FeedHunter)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="Feed Hunter",
        description="Satelliweb Feeds Table (PY3)",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        fnc=main
    )
