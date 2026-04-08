# -*- coding: utf-8 -*-
# تم التطوير بواسطة محمد - نسخة بايثon 3
# عرض تفصيلي للفيدات (Sat, Freq, Pol, SR, Category, Encryption)

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.NimManager import nimmanager
from enigma import eTimer, gFont, RT_HALIGN_LEFT, RT_VALIGN_CENTER
import re
import threading
import urllib.request as urllib2

# دالة تنسيق السطر الواحد ليعرض البيانات في سطرين (أكثر تفصيلاً)
def FeedListEntry(sat, freq, pol, sr, category, enc, info):
    res = [(sat, freq, pol, sr)] # بيانات مخفية للاستخدام التقني
    
    # السطر الأول: القمر (باللون الأصفر)
    res.append((sat, 10, 2, 800, 25, 0, RT_HALIGN_LEFT, 0xF0CA00))
    
    # السطر الثاني: التردد والقطبية والترميز
    detail_text = f"Frequency: {freq} - Pol: {pol} - SR: {sr} - Category: {category}"
    res.append((detail_text, 10, 27, 800, 25, 1, RT_HALIGN_LEFT))
    
    # السطر الثالث: التشفير والمعلومات الإضافية
    extra_text = f"Transmitted in: {enc}  ℹ {info}"
    res.append((extra_text, 10, 52, 800, 25, 1, RT_HALIGN_LEFT, 0xAAAAAA))
    
    return res

class FeedHunter(Screen):
    skin = """
    <screen position="center,center" size="900,600" title="Feed Hunter Pro - Detailed View">
        <widget name="list" position="10,10" size="880,480" scrollbarMode="showOnDemand" selectionColor="#333333" />
        <eLabel position="10,500" size="880,2" backgroundColor="#555555" />
        <widget name="status_label" position="10,510" size="880,30" font="Regular;22" halign="center" foregroundColor="#00FF00" />
        <eLabel text="OK: Scan | GREEN: Reload | RED: Exit" position="10,550" size="880,30" font="Regular;20" halign="center" transparent="1" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self["list"] = MenuList([])
        # تحديد حجم الخطوط في القائمة (خط كبير للقمر وخط أصغر للتفاصيل)
        self["list"].l.setFont(0, gFont("Regular", 22))
        self["list"].l.setFont(1, gFont("Regular", 18))
        self["list"].l.setItemHeight(80) # زيادة ارتفاع السطر ليستوعب 3 أسطر بيانات
        
        self["status_label"] = Label("جاري جلب البيانات التفصيلية...")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.startScan, "cancel": self.close, "red": self.close, "green": self.reloadData
        }, -1)
        
        self.timer = eTimer()
        self.timer.timeout.connect(self.updateUI)
        self.onLayoutFinish.append(self.reloadData)

    def reloadData(self):
        self.feeds_data = []
        threading.Thread(target=self.fetchData).start()

    def fetchData(self):
        new_list = []
        url = "https://www.satelliweb.com/index.php?section=livef&langue=en"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            req = urllib2.Request(url, headers=headers)
            with urllib2.urlopen(req, timeout=15) as response:
                html = response.read().decode('utf-8', 'ignore')
                
                # تقطيع الـ HTML إلى بلوكات (كل بلوك يمثل فيد واحد)
                blocks = re.findall(r'<tr>(.*?)</tr>', html, re.DOTALL)
                
                for block in blocks:
                    # البحث عن الأرقام الأساسية
                    m = re.search(r'(\d{5})\s+([HV])\s+(\d{4,5})', block)
                    if m:
                        freq, pol, sr = m.groups()
                        
                        # استخراج اسم القمر
                        sat_m = re.search(r"(\d+\.?\d*)\s*°\s*([EW])", block)
                        sat_name = f"sat {sat_m.group(1)}{sat_m.group(2)} ({sat_m.group(1)}°{sat_m.group(2)})" if sat_m else "Unknown Sat"
                        
                        # استخراج التصنيف (Sport, News, etc)
                        cat_m = re.search(r'Category:\s*</b>\s*([^<]+)', block)
                        category = cat_m.group(1).strip() if cat_m else "General"
                        
                        # استخراج التشفير
                        enc_m = re.search(r'MPEG-4\s*([^<]+)', block)
                        enc = enc_m.group(1).strip() if enc_m else "Clear"
                        
                        # استخراج المعلومات الإضافية (ℹ)
                        info_m = re.search(r'ℹ\s*</b>\s*([^<]+)', block)
                        info = info_m.group(1).strip() if info_m else ""

                        new_list.append(FeedListEntry(sat_name, freq, pol, sr, category, enc, info))
        except: pass
        self.feeds_data = new_list
        self.timer.start(100, True)

    def updateUI(self):
        self["list"].setList(self.feeds_data)
        self["status_label"].setText(f"تم تحديث {len(self.feeds_data)} فيد بنجاح")

    def startScan(self):
        sel = self["list"].getCurrent()
        if not sel: return
        sat_name, freq, pol, sr = sel[0]
        
        # استخراج الموقع المداري للتيونر
        orb_pos = 70 
        orb_m = re.search(r"(\d+\.?\d*)", sat_name)
        if orb_m:
            pos = float(orb_m.group(1))
            orb_pos = int((360 - pos) * 10) if 'W' in sat_name else int(pos * 10)

        tuner_slot = -1
        for slot in nimmanager.nim_slots:
            if slot.isCompatible("DVB-S2"):
                tuner_slot = slot.slot
                break
        
        if tuner_slot != -1:
            tp = {"type": "S2", "frequency": int(freq)*1000, "symbol_rate": int(sr)*1000,
                  "polarization": 0 if pol == "H" else 1, "fec_inner": 0, "system": 1,
                  "modulation": 2, "inversion": 2, "roll_off": 3, "pilot": 2, "orbital_position": orb_pos}
            try:
                from Screens.ServiceScan import ServiceScan
                self.session.open(ServiceScan, tuner_slot, transponder=tp, scanList=[tp])
            except: pass

def main(session, **kwargs): session.open(FeedHunter)
def Plugins(**kwargs):
    return PluginDescriptor(name="Feed Hunter", description="Detailed Feeds View (PY3)", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
