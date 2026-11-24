# -*- coding: utf-8 -*-
"""Rapor tasarım sistemi: yazı tipleri, renkler, stiller ve modern PDF bileşenleri.
Hisse, emtia ve kripto raporlarının hepsi bu bileşenleri kullanır."""
import os, logging
import matplotlib
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Paragraph, Table, TableStyle, Spacer

# ---------------------------------------------------------------- Yazı tipleri
_DIZIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
_DV = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")

def _kaydet():
    try:
        pdfmetrics.registerFont(TTFont("DV", os.path.join(_DIZIN, "FiraSans-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("DVM", os.path.join(_DIZIN, "FiraSans-Medium.ttf")))
        pdfmetrics.registerFont(TTFont("DVB", os.path.join(_DIZIN, "FiraSans-SemiBold.ttf")))
        pdfmetrics.registerFont(TTFont("DVX", os.path.join(_DIZIN, "FiraSans-Bold.ttf")))
        pdfmetrics.registerFont(TTFont("DVL", os.path.join(_DIZIN, "FiraSans-Light.ttf")))
        for f in ("Regular", "Medium", "SemiBold", "Bold", "Light"):
            fm.fontManager.addfont(os.path.join(_DIZIN, f"FiraSans-{f}.ttf"))
        aile = "Fira Sans"
    except Exception:  # yazı tipi yoksa DejaVu'ya dön
        for ad, dosya in (("DV", "DejaVuSans.ttf"), ("DVM", "DejaVuSans.ttf"), ("DVB", "DejaVuSans-Bold.ttf"),
                          ("DVX", "DejaVuSans-Bold.ttf"), ("DVL", "DejaVuSans.ttf")):
            pdfmetrics.registerFont(TTFont(ad, os.path.join(_DV, dosya)))
        aile = "DejaVu Sans"
    pdfmetrics.registerFont(TTFont("DJ", os.path.join(_DV, "DejaVuSans.ttf")))  # özel simgeler için
    addMapping("DV", 0, 0, "DV"); addMapping("DV", 1, 0, "DVB"); addMapping("DV", 0, 1, "DV"); addMapping("DV", 1, 1, "DVB")
    return aile

AILE = _kaydet()

# ---------------------------------------------------------------- Renkler
HEX = {
    "murekkep": "#0F172A", "metin": "#1E293B", "soluk": "#64748B", "cizgi": "#E2E8F0", "zemin": "#F8FAFC",
    "zemin2": "#F1F5F9", "ana": "#4F46E5", "ana_acik": "#EEF2FF", "turkuaz": "#0D9488", "turkuaz_acik": "#CCFBF1",
    "yesil": "#16A34A", "yesil_acik": "#DCFCE7", "kirmizi": "#DC2626", "kirmizi_acik": "#FEE2E2",
    "sari": "#D97706", "sari_acik": "#FEF3C7", "gri": "#94A3B8", "turuncu": "#EA580C", "mor": "#7C3AED",
}
R = {k: colors.HexColor(v) for k, v in HEX.items()}

def durum_rengi(durum):
    """'iyi' / 'orta' / 'zayif' → (koyu, açık) renk çifti."""
    return {"iyi": (R["yesil"], R["yesil_acik"]), "orta": (R["sari"], R["sari_acik"]),
            "zayif": (R["kirmizi"], R["kirmizi_acik"])}.get(durum, (R["soluk"], R["zemin2"]))

def puan_durum(p):
    if p is None: return "yok"
    return "iyi" if p >= 3.5 else "orta" if p >= 2.5 else "zayif"

# ---------------------------------------------------------------- Grafik teması
plt.rcParams.update({
    "font.family": [AILE, "DejaVu Sans"], "font.size": 8, "axes.titlesize": 10, "axes.titleweight": "semibold",
    "axes.titlecolor": HEX["murekkep"], "axes.labelcolor": HEX["soluk"], "axes.edgecolor": HEX["cizgi"],
    "xtick.color": HEX["soluk"], "ytick.color": HEX["soluk"], "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": HEX["cizgi"], "grid.linewidth": 0.6, "axes.axisbelow": True,
    "legend.frameon": False, "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.prop_cycle": matplotlib.cycler(color=[HEX["ana"], HEX["turkuaz"], HEX["turuncu"], HEX["mor"], HEX["sari"]]),
})
GRAFIK = {"lac": HEX["murekkep"], "mavi": HEX["ana"], "tur": HEX["turuncu"], "yesil": HEX["yesil"],
          "kirmizi": HEX["kirmizi"], "sari": HEX["sari"], "gri": HEX["gri"], "acik": "#C7D2FE", "turkuaz": HEX["turkuaz"]}

# ---------------------------------------------------------------- Metin stilleri
def _st(ad, **kw):
    b = dict(fontName="DV", fontSize=9.2, leading=13.4, textColor=R["metin"]); b.update(kw)
    return ParagraphStyle(ad, **b)

ST = {
    "h1": _st("h1", fontName="DVX", fontSize=15, leading=19, textColor=R["murekkep"], spaceBefore=2, spaceAfter=6),
    "h2": _st("h2", fontName="DVB", fontSize=11, leading=14, textColor=R["murekkep"], spaceBefore=9, spaceAfter=4),
    "p": _st("p", alignment=4),
    "kucuk": _st("k", fontSize=7.4, leading=10, textColor=R["soluk"]),
    "hucre": _st("c", fontSize=8, leading=10.4),
    "hucreB": _st("cb", fontName="DVB", fontSize=8, leading=10.4),
    "madde": _st("m", fontSize=8.8, leading=12.4, leftIndent=10, firstLineIndent=-8),
    "kutu": _st("kt", fontSize=8.8, leading=12.6, textColor=R["metin"]),
}

# ---------------------------------------------------------------- Bileşenler
class Bolum(Flowable):
    """Numara rozetli bölüm başlığı."""
    def __init__(self, no, baslik, genislik):
        super().__init__(); self.no, self.baslik, self.gen = str(no), baslik, genislik
    def wrap(self, *a):
        return self.gen, 30
    def draw(self):
        c = self.canv
        c.setFillColor(R["ana"]); c.roundRect(0, 6, 22, 22, 6, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("DVX", 11); c.drawCentredString(11, 12.5, self.no)
        c.setFillColor(R["murekkep"]); c.setFont("DVX", 15); c.drawString(32, 11, self.baslik)
        c.setStrokeColor(R["cizgi"]); c.setLineWidth(0.8); c.line(0, 1, self.gen, 1)


class Kart(Flowable):
    """Yuvarlak köşeli gösterge kartı."""
    def __init__(self, etiket, deger, alt="", vurgu=None, gen=120, yuk=58, zemin=None, deger_boyut=15):
        super().__init__()
        self.e, self.d, self.a, self.v = etiket, deger, alt, vurgu or R["murekkep"]
        self.gen, self.yuk, self.zemin, self.db = gen, yuk, zemin or R["zemin"], deger_boyut
    def wrap(self, *a):
        return self.gen, self.yuk
    def draw(self):
        c = self.canv
        c.setFillColor(self.zemin); c.setStrokeColor(R["cizgi"]); c.setLineWidth(0.6)
        c.roundRect(0, 0, self.gen, self.yuk, 8, stroke=1, fill=1)
        c.setFillColor(self.v); c.circle(11, self.yuk - 12, 3, stroke=0, fill=1)
        c.setFillColor(R["soluk"]); c.setFont("DVM", 7); c.drawString(19, self.yuk - 14.5, self.e.upper())
        c.setFillColor(self.v); c.setFont("DVX", self.db)
        d = self.d
        while pdfmetrics.stringWidth(d, "DVX", self.db) > self.gen - 18 and len(d) > 3:
            self.db -= 0.5; c.setFont("DVX", self.db)
        c.drawString(10, self.yuk - 34, d)
        if self.a:
            c.setFillColor(R["soluk"]); c.setFont("DV", 7)
            a = self.a
            while pdfmetrics.stringWidth(a, "DV", 7) > self.gen - 16 and len(a) > 4:
                a = a[:-2]
            if a != self.a: a = a.rstrip() + "…"
            c.drawString(10, 9, a)


def kart_izgarasi(kartlar, W, sutun=4, bosluk=6, yuk=58):
    g = (W - bosluk * (sutun - 1)) / sutun
    satirlar, s = [], []
    for k in kartlar:
        e, d, a, v = (list(k) + [None] * 4)[:4]
        s.append(Kart(e, d, a or "", v, gen=g, yuk=yuk))
        if len(s) == sutun: satirlar.append(s); s = []
    if s: satirlar.append(s + [""] * (sutun - len(s)))
    t = Table(satirlar, colWidths=[g + bosluk] * sutun)
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), bosluk),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), bosluk)]))
    t.hAlign = "LEFT"
    return t


def bilgi_kutusu(baslik, metin, W, tur="ana"):
    """'Kısaca' veya 'Bu ne demek?' kutusu."""
    koyu, acik = {"ana": (R["ana"], R["ana_acik"]), "turkuaz": (R["turkuaz"], R["turkuaz_acik"]),
                  "sari": (R["sari"], R["sari_acik"]), "yesil": (R["yesil"], R["yesil_acik"]),
                  "kirmizi": (R["kirmizi"], R["kirmizi_acik"])}[tur]
    p = Paragraph(f'<font name="DVB" color="{koyu.hexval().replace("0x", "#")}">{baslik}</font>&nbsp;&nbsp;{esc(metin)}', ST["kutu"])
    t = Table([[p]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), acik), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("ROUNDEDCORNERS", [7, 7, 7, 7]),
                           ("LINEBEFORE", (0, 0), (0, -1), 3, koyu)]))
    t.hAlign = "LEFT"
    return t


def trafik_listesi(satirlar, W, etiketler=None):
    """Karne listesi: [(alan, değerlendirme, durum)] → durum rozeti + alan + değerlendirme."""
    veri = []
    etiketler = etiketler or {"iyi": "OLUMLU", "orta": "NÖTR", "zayif": "OLUMSUZ"}
    for soru, cevap, durum in satirlar:
        koyu, acik = durum_rengi(durum)
        etiket = etiketler.get(durum, "–")
        rozet = Table([[Paragraph(f'<font name="DVB" size="6.6" color="{koyu.hexval().replace("0x", "#")}">{etiket}</font>',
                                  _st("r", alignment=1))]], colWidths=[50])
        rozet.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), acik), ("ROUNDEDCORNERS", [6, 6, 6, 6]),
                                   ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        veri.append([rozet, Paragraph(f'<font name="DVB">{soru}</font><br/>{esc(cevap)}', _st("tl", fontSize=8.6, leading=11.8))])
    t = Table(veri, colWidths=[58, W - 58])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -2), 0.5, R["cizgi"]),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                           ("LEFTPADDING", (0, 0), (0, -1), 0)]))
    t.hAlign = "LEFT"
    return t


def tablo(veri, gen, baslik=True, hizala_sol=(0,), kalin_son=False, renkli_kolon=None, font=7.9):
    veri = [[c if not isinstance(c, str) or len(c) < 60 else Paragraph(c, ST["hucre"]) for c in r] for r in veri]
    t = Table(veri, colWidths=gen, repeatRows=1 if baslik else 0, hAlign="LEFT")
    s = [("FONTNAME", (0, 0), (-1, -1), "DV"), ("FONTSIZE", (0, 0), (-1, -1), font), ("TEXTCOLOR", (0, 0), (-1, -1), R["metin"]),
         ("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
         ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
         ("LINEBELOW", (0, 0), (-1, -1), 0.4, R["cizgi"])]
    for c in hizala_sol: s.append(("ALIGN", (c, 0), (c, -1), "LEFT"))
    if baslik:
        s += [("BACKGROUND", (0, 0), (-1, 0), R["zemin2"]), ("TEXTCOLOR", (0, 0), (-1, 0), R["soluk"]),
              ("FONTNAME", (0, 0), (-1, 0), "DVB"), ("FONTSIZE", (0, 0), (-1, 0), font - 0.6),
              ("LINEBELOW", (0, 0), (-1, 0), 0.8, R["cizgi"])]
    if kalin_son: s += [("FONTNAME", (0, -1), (-1, -1), "DVB"), ("LINEABOVE", (0, -1), (-1, -1), 0.8, R["murekkep"])]
    t.setStyle(TableStyle(s)); return t


def sayfa_cizici(kod, baslik, tarih, kapak_yuk=0):
    """Üst bilgi / alt bilgi. Kapak sayfasında koyu başlık bandını da çizer."""
    def ciz(c, doc):
        c.saveState(); W_, H_ = A4
        if doc.page == 1 and kapak_yuk:
            c.setFillColor(R["gece"]); c.rect(0, H_ - kapak_yuk, W_, kapak_yuk, fill=1, stroke=0)
            c.setFillColor(R["gece2"]); c.rect(W_ * 0.62, H_ - kapak_yuk, W_ * 0.38, kapak_yuk, fill=1, stroke=0)
            c.setFillColor(R["altin"]); c.rect(0, H_ - kapak_yuk, W_, 2.5, fill=1, stroke=0)
            c.setFillColor(R["altin"]); c.setFont("DVB", 7); c.drawString(1.5 * cm, H_ - 0.75 * cm, baslik.upper())
            c.setFillColor(colors.HexColor("#94A3B8")); c.setFont("DV", 7); c.drawRightString(W_ - 1.5 * cm, H_ - 0.75 * cm, tarih)
        else:
            c.setFillColor(R["altin"]); c.roundRect(1.5 * cm, H_ - 1.02 * cm, 4, 10, 1.5, fill=1, stroke=0)
            c.setFillColor(R["murekkep"]); c.setFont("DVB", 8.5); c.drawString(1.5 * cm + 9, H_ - 1.0 * cm, kod)
            c.setFillColor(R["soluk"]); c.setFont("DV", 8)
            c.drawString(1.5 * cm + 9 + pdfmetrics.stringWidth(kod, "DVB", 8.5) + 8, H_ - 1.0 * cm, baslik)
            c.drawRightString(W_ - 1.5 * cm, H_ - 1.0 * cm, tarih)
            c.setStrokeColor(R["cizgi"]); c.setLineWidth(0.6); c.line(1.5 * cm, H_ - 1.2 * cm, W_ - 1.5 * cm, H_ - 1.2 * cm)
        c.setFillColor(R["soluk"]); c.setFont("DV", 6.8)
        c.drawString(1.5 * cm, 0.8 * cm, "Otomatik model çıktısıdır; yatırım tavsiyesi değildir.")
        c.setFillColor(R["zemin2"]); c.roundRect(W_ - 1.5 * cm - 34, 0.62 * cm, 34, 13, 6, fill=1, stroke=0)
        c.setFillColor(R["murekkep"]); c.setFont("DVB", 7); c.drawCentredString(W_ - 1.5 * cm - 17, 0.62 * cm + 4, str(doc.page))
        c.restoreState()
    return ciz


def kapak(baslik, alt_satir, rozet, rozet_durum, W):
    """Koyu bant üzerindeki kapak içeriği (sayfa_cizici bandı çizer)."""
    koyu, acik = durum_rengi(rozet_durum)
    b = Paragraph(f'<font name="DVX" size="22" color="#FFFFFF">{baslik}</font>', _st("kb", leading=27))
    a = Paragraph(f'<font color="#CBD5E1">{alt_satir}</font>', _st("ka", fontSize=9.5, leading=13))
    gen_rz = pdfmetrics.stringWidth(rozet, "DVB", 8.5) + 24
    rz = Table([[Paragraph(f'<font name="DVB" size="8.5" color="{koyu.hexval().replace("0x", "#")}">{rozet}</font>',
                           _st("rz", alignment=1))]], colWidths=[gen_rz])
    rz.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), acik), ("ROUNDEDCORNERS", [9, 9, 9, 9]),
                            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    rz.hAlign = "LEFT"
    return [Spacer(1, 4), b, Spacer(1, 4), a, Spacer(1, 8), rz, Spacer(1, 26)]


SOZLUK_HISSE = [
    ("F/K (Fiyat/Kazanç)", "Hissenin fiyatının, şirketin hisse başına yıllık kârına oranı. Düşükse kâra göre ucuz demektir."),
    ("PD/DD (Piyasa Değeri/Defter Değeri)", "Şirketin borsadaki değerinin, muhasebedeki özkaynağına oranı. 1'in altı, şirketin defter değerinden ucuza işlem gördüğünü gösterir."),
    ("FAVÖK", "Faiz, vergi ve amortisman öncesi kâr; şirketin ana faaliyetlerinden ne kadar nakit ürettiğinin yaklaşık ölçüsü."),
    ("ROE (Özkaynak kârlılığı)", "Ortakların koyduğu her 100 TL sermayeye yılda ne kadar kâr üretildiği. Enflasyonun üzerinde olması istenir."),
    ("Serbest nakit akışı", "Şirketin yatırımlarını yaptıktan sonra elinde kalan nakit. Temettü ve borç ödemesinin kaynağıdır."),
    ("Adil değer", "Farklı değerleme yöntemlerinin ortalamasıyla bulunan, modelin 'olması gereken' fiyat tahmini."),
    ("İNA / DCF", "Şirketin gelecekte üreteceği nakitlerin bugüne indirgenmesiyle yapılan değerleme."),
    ("NAV (Net aktif değer)", "Holdinglerde, iştiraklerin piyasa değerlerinden holdinge düşen payların toplamı."),
    ("Beta", "Hissenin piyasaya göre oynaklığı. 1'den büyükse endeksten daha sert hareket eder."),
    ("RSI", "0–100 arası momentum göstergesi. 70 üstü 'aşırı alım', 30 altı 'aşırı satım' kabul edilir."),
    ("CMF / OBV", "Hacme dayalı para akışı göstergeleri. Pozitifse hisseye para girdiğine işaret eder."),
    ("Destek / Direnç", "Fiyatın geçmişte düşüşte durduğu (destek) ve yükselişte zorlandığı (direnç) seviyeler."),
    ("Piotroski F-skoru", "Şirketin temellerinin iyileşip iyileşmediğini ölçen 0–9 arası puan."),
    ("Altman Z skoru", "Şirketin finansal sıkıntı riskini ölçer. Yüksek değer daha güvenlidir."),
]


# =====================================================================
# PRO TARZI BİLEŞENLER
# =====================================================================
HEX.update({"altin": "#F59E0B", "altin_acik": "#FEF3C7", "gece": "#0B1220", "gece2": "#111A2E"})
R.update({k: colors.HexColor(HEX[k]) for k in ("altin", "altin_acik", "gece", "gece2")})

import re as _re
def esc(x):
    """Paragraph içinde çıplak & işaretlerini kaçışlar (S&P 500 gibi)."""
    return _re.sub(r"&(?!amp;|lt;|gt;|nbsp;|quot;|#)", "&amp;", str(x))

def _hex(c):
    return c.hexval().replace("0x", "#")

def basamak(x, d=2):
    """Fiyata uygun ondalık: küçük coin fiyatlarında anlamlı basamaklar korunur (0,00000312)."""
    import math as _m
    a = abs(x)
    if a == 0 or a >= 1: return d if a < 100000 else 0
    return min(max(d, -int(_m.floor(_m.log10(a))) + 3), 10)


def _sayi(x, d=2):
    if x is None: return "–"
    for e, ek in ((1e12, " tr"), (1e9, " mr")):
        if abs(x) >= e: return f"{x / e:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") + ek
    d = basamak(x, d)
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _yuzde(x, d=1):
    if x is None: return "–"
    return ("+" if x > 0 else "-" if x < 0 else "") + "%" + f"{abs(x) * 100:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


class Panel(Flowable):
    """Başlıklı, yuvarlak köşeli panel çerçevesi; içerik alt sınıfta çizilir."""
    def __init__(self, baslik, gen, yuk):
        super().__init__(); self.baslik, self.gen, self.yuk = baslik, gen, yuk
    def wrap(self, *a):
        return self.gen, self.yuk
    def cerceve(self):
        c = self.canv
        c.setFillColor(colors.white); c.setStrokeColor(R["cizgi"]); c.setLineWidth(0.8)
        c.roundRect(0, 0, self.gen, self.yuk, 9, stroke=1, fill=1)
        c.setFillColor(R["altin"]); c.roundRect(12, self.yuk - 19, 3, 11, 1.5, stroke=0, fill=1)
        c.setFillColor(R["murekkep"]); c.setFont("DVB", 8.6); c.drawString(20, self.yuk - 17, self.baslik.upper())


class AdilDegerGostergesi(Panel):
    """Adil değer kartı: büyük değer, potansiyel ve ucuz/makul/pahalı bölgeli ölçek."""
    def __init__(self, fiyat, adil, dusuk, yuksek, sembol="₺", bant=0.15, gen=250, yuk=150, baslik="Adil değer",
                 etiketler=("Ucuz", "Makul", "Pahalı"), alt_not=""):
        super().__init__(baslik, gen, yuk)
        self.f, self.a, self.dsk, self.yks, self.s, self.b, self.et, self.alt = fiyat, adil, dusuk, yuksek, sembol, bant, etiketler, alt_not
    def draw(self):
        self.cerceve(); c = self.canv
        if not self.a:
            c.setFont("DV", 9); c.setFillColor(R["soluk"]); c.drawString(14, self.yuk / 2, "Yeterli veri yok"); return
        pot = self.a / self.f - 1
        durum = "iyi" if pot > self.b else "zayif" if pot < -self.b else "orta"
        koyu, acik = durum_rengi(durum)
        c.setFillColor(R["murekkep"]); c.setFont("DVX", 22); c.drawString(14, self.yuk - 48, f"{_sayi(self.a)} {self.s}")
        c.setFont("DV", 8); c.setFillColor(R["soluk"]); c.drawString(14, self.yuk - 61, f"Son fiyat {_sayi(self.f)} {self.s}")
        etiket = self.et[0] if durum == "iyi" else self.et[2] if durum == "zayif" else self.et[1]
        rz = f"{_yuzde(pot)}  {etiket.upper()}"; gw = pdfmetrics.stringWidth(rz, "DVB", 8.5) + 16
        c.setFillColor(acik); c.roundRect(self.gen - gw - 12, self.yuk - 48, gw, 17, 8, stroke=0, fill=1)
        c.setFillColor(koyu); c.setFont("DVB", 8.5); c.drawString(self.gen - gw - 4, self.yuk - 42.5, rz)
        # ölçek
        x0, x1, yb = 16, self.gen - 16, 44
        lo = min(self.f, self.a) * (1 - self.b) * 0.80
        hi = max(self.f, self.a) * (1 + self.b) * 1.15
        X = lambda v: x0 + min(max((v - lo) / (hi - lo), 0), 1) * (x1 - x0)
        z1, z2 = X(self.a * (1 - self.b)), X(self.a * (1 + self.b))
        for xa, xb, renk in ((x0, z1, R["yesil_acik"]), (z1, z2, R["sari_acik"]), (z2, x1, R["kirmizi_acik"])):
            c.setFillColor(renk); c.rect(xa, yb, max(xb - xa, 0), 9, stroke=0, fill=1)
        c.setFont("DV", 6.3)
        for (xa, xb), et, renk in (((x0, z1), self.et[0], R["yesil"]), ((z1, z2), self.et[1], R["sari"]), ((z2, x1), self.et[2], R["kirmizi"])):
            if xb - xa > 26: c.setFillColor(renk); c.drawCentredString((xa + xb) / 2, yb - 10, et)
        if self.dsk and self.yks:
            c.setStrokeColor(R["ana"]); c.setLineWidth(1.4); c.setLineCap(1)
            c.line(X(self.dsk), yb + 4.5, X(self.yks), yb + 4.5)
            for v_ in (self.dsk, self.yks): c.line(X(v_), yb + 2, X(v_), yb + 7)
        c.setStrokeColor(R["murekkep"]); c.setLineWidth(1.4); c.line(X(self.a), yb - 2, X(self.a), yb + 11)
        # Fiyat işareti
        xf = X(self.f); c.setFillColor(koyu)
        p = c.beginPath(); p.moveTo(xf, yb + 10); p.lineTo(xf - 5, yb + 19); p.lineTo(xf + 5, yb + 19); p.close(); c.drawPath(p, stroke=0, fill=1)
        c.setFont("DVB", 6.5); c.drawCentredString(xf, yb + 22, "Fiyat")
        if abs(X(self.a) - xf) > 24:
            c.setFillColor(R["murekkep"]); c.drawCentredString(X(self.a), yb + 14, "Adil")
        if self.alt:
            c.setFont("DV", 6.4); c.setFillColor(R["soluk"]); c.drawString(14, 9, self.alt[:110])


class SkorGostergesi(Panel):
    """Sağlık skoru kartı: büyük skor + etiket + 5 dilimli çubuk + kategori çubukları."""
    def __init__(self, skor, etiket, kategoriler, gen=250, yuk=150, baslik="Finansal sağlık"):
        super().__init__(baslik, gen, yuk); self.s, self.e, self.k = skor, etiket, kategoriler
    def draw(self):
        self.cerceve(); c = self.canv
        if self.s is None:
            c.setFont("DV", 9); c.setFillColor(R["soluk"]); c.drawString(14, self.yuk / 2, "Yeterli veri yok"); return
        koyu, acik = durum_rengi(puan_durum(self.s))
        metin = f"{self.s:.2f}".replace(".", ",")
        c.setFillColor(R["murekkep"]); c.setFont("DVX", 22); c.drawString(14, self.yuk - 48, metin)
        w = pdfmetrics.stringWidth(metin, "DVX", 22)
        c.setFont("DV", 9); c.setFillColor(R["soluk"]); c.drawString(16 + w, self.yuk - 48, "/ 5")
        gw = pdfmetrics.stringWidth(self.e, "DVB", 8.5) + 16
        c.setFillColor(acik); c.roundRect(self.gen - gw - 12, self.yuk - 48, gw, 17, 8, stroke=0, fill=1)
        c.setFillColor(koyu); c.setFont("DVB", 8.5); c.drawString(self.gen - gw - 4, self.yuk - 42.5, self.e)
        # 5 dilim
        x0, y0, sw = 14, self.yuk - 63, (self.gen - 28 - 8) / 5
        for i in range(5):
            dolu = self.s >= i + 1 or (self.s > i and self.s - i >= 0.5)
            c.setFillColor(koyu if dolu else R["zemin2"]); c.roundRect(x0 + i * (sw + 2), y0, sw, 5, 2.5, stroke=0, fill=1)
        # kategoriler
        n = len(self.k); y = y0 - 14; satir = min(13, (y0 - 14) / max(n, 1))
        for ad, v in list(self.k.items())[:7]:
            c.setFont("DV", 7.4); c.setFillColor(R["metin"]); c.drawString(14, y, ad[:24])
            bx, bw = self.gen * 0.50, self.gen * 0.36
            c.setFillColor(R["zemin2"]); c.roundRect(bx, y, bw, 5, 2.5, stroke=0, fill=1)
            k2, _ = durum_rengi(puan_durum(v)); c.setFillColor(k2)
            c.roundRect(bx, y, bw * max(min(v / 5, 1), 0.04), 5, 2.5, stroke=0, fill=1)
            c.setFont("DVB", 7.2); c.setFillColor(R["murekkep"]); c.drawRightString(self.gen - 12, y, f"{v:.1f}".replace(".", ","))
            y -= satir


class AralikCubugu(Flowable):
    """Düşük–yüksek aralığında bir değerin konumu (52 hafta, analist hedefleri, ATL–ATH)."""
    def __init__(self, baslik, dusuk, yuksek, deger, gen=250, ort=None, sembol="", deger_etiket="Fiyat", ort_etiket="Ort."):
        super().__init__(); self.b, self.lo, self.hi, self.v, self.gen, self.o, self.s = baslik, dusuk, yuksek, deger, gen, ort, sembol
        self.ve, self.oe = deger_etiket, ort_etiket
    def wrap(self, *a):
        return self.gen, 50
    def draw(self):
        c = self.canv; c.translate(0, 6)
        c.setFont("DVB", 7.6); c.setFillColor(R["murekkep"]); c.drawString(0, 34, self.b.upper())
        if None in (self.lo, self.hi, self.v) or self.hi <= self.lo:
            c.setFont("DV", 7.5); c.setFillColor(R["soluk"]); c.drawString(0, 16, "Veri yok"); return
        x0, x1, y = 0, self.gen, 16
        X = lambda v: x0 + min(max((v - self.lo) / (self.hi - self.lo), 0), 1) * (x1 - x0)
        c.setStrokeColor(R["cizgi"]); c.setLineWidth(4); c.setLineCap(1); c.line(x0 + 2, y, x1 - 2, y)
        c.setStrokeColor(R["ana"]); c.line(x0 + 2, y, X(self.v), y)
        if self.o is not None:
            c.setStrokeColor(R["murekkep"]); c.setLineWidth(1); c.line(X(self.o), y - 5, X(self.o), y + 5)
            c.setFont("DV", 6.2); c.setFillColor(R["murekkep"]); c.drawCentredString(X(self.o), y + 7, f"{self.oe} {_sayi(self.o)}")
        c.setFillColor(colors.white); c.setStrokeColor(R["ana"]); c.setLineWidth(1.6); c.circle(X(self.v), y, 4, stroke=1, fill=1)
        c.setFont("DV", 6.8); c.setFillColor(R["soluk"])
        c.drawString(x0, 3, f"{_sayi(self.lo)} {self.s}"); c.drawRightString(x1, 3, f"{_sayi(self.hi)} {self.s}")
        c.setFont("DVB", 6.8); c.setFillColor(R["ana"])
        c.drawCentredString(min(max(X(self.v), 28), x1 - 28), -6, f"{self.ve} {_sayi(self.v)}")


class _Ikon(Flowable):
    def __init__(self, yon):
        super().__init__(); self.yon = yon
    def wrap(self, *a):
        return 14, 14
    def draw(self):
        c = self.canv; koyu, acik = (R["yesil"], R["yesil_acik"]) if self.yon > 0 else (R["kirmizi"], R["kirmizi_acik"])
        c.setFillColor(acik); c.circle(7, 7, 7, stroke=0, fill=1)
        c.setFillColor(koyu); p = c.beginPath()
        if self.yon > 0: p.moveTo(7, 11); p.lineTo(3.5, 5); p.lineTo(10.5, 5)
        else: p.moveTo(7, 3); p.lineTo(3.5, 9); p.lineTo(10.5, 9)
        p.close(); c.drawPath(p, stroke=0, fill=1)


def sinyal_listesi(guclu, zayif, W, n=5):
    """Pro ipuçları tarzı iki sütunlu sinyal listesi."""
    sutun = []
    for liste, yon, bas in ((guclu, 1, "Olumlu sinyaller"), (zayif, -1, "Dikkat gerektirenler")):
        koyu = R["yesil"] if yon > 0 else R["kirmizi"]
        satir = [[Paragraph(f'<font name="DVB" color="{_hex(koyu)}">{bas}</font>', ST["hucreB"]), ""]]
        for x in liste[:n]:
            satir.append([_Ikon(yon), Paragraph(esc(x), _st("sg", fontSize=8.2, leading=11))])
        if not liste:
            satir.append(["", Paragraph(f'<font color="{HEX["soluk"]}">Belirgin bir sinyal yok.</font>', _st("sg", fontSize=8.2, leading=11))])
        t = Table(satir, colWidths=[18, W / 2 - 26])
        t.setStyle(TableStyle([("SPAN", (0, 0), (1, 0)), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5), ("LINEBELOW", (0, 0), (-1, 0), 1, koyu)]))
        sutun.append(t)
    t = Table([sutun], colWidths=[W / 2, W / 2]); t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    t.hAlign = "LEFT"; return t


def metrik_listesi(ciftler, W, sutun=2):
    """'Temel göstergeler' listesi: etiket solda, değer sağda; ince ayırıcılar."""
    hucre = []
    for etiket, deger in ciftler:
        hucre += [Paragraph(f'<font color="{HEX["soluk"]}">{etiket}</font>', _st("ml", fontSize=8, leading=10)),
                  Paragraph(f'<font name="DVB">{deger}</font>', _st("mv", fontSize=8.4, leading=10, alignment=2))]
    n = 2 * sutun; satir = [hucre[i:i + n] for i in range(0, len(hucre), n)]
    if satir and len(satir[-1]) < n: satir[-1] += [""] * (n - len(satir[-1]))
    g = (W - (sutun - 1) * 14) / sutun
    cw = []
    for i in range(sutun): cw += [g * 0.58, g * 0.42 + (14 if i < sutun - 1 else 0)]
    t = Table(satir, colWidths=cw)
    st_ = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
           ("LEFTPADDING", (0, 0), (-1, -1), 0)]
    for i in range(sutun):
        st_ += [("LINEBELOW", (2 * i, 0), (2 * i + 1, -1), 0.5, R["cizgi"]), ("RIGHTPADDING", (2 * i + 1, 0), (2 * i + 1, -1), 14 if i < sutun - 1 else 0)]
    t.setStyle(TableStyle(st_)); t.hAlign = "LEFT"; return t


def yan_yana(sol, sag, W, bosluk=10):
    t = Table([[sol, sag]], colWidths=[(W - bosluk) / 2 + bosluk, (W - bosluk) / 2])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (0, -1), bosluk), ("RIGHTPADDING", (1, 0), (1, -1), 0)]))
    t.hAlign = "LEFT"; return t


def zaman_metni(z):
    if z is None: return "–"
    z = __import__("pandas").Timestamp(z)
    return f"{z:%d.%m.%Y}" if (z.hour, z.minute) == (0, 0) else f"{z:%d.%m.%Y %H:%M}"

def pro_kapak(ad, alt_satir, fiyat_metni, degisim, W, rozet=None, guncel=None):
    """Koyu bant içinde: solda ad ve alt bilgi, sağda büyük fiyat ve günlük değişim."""
    renk = HEX["yesil"] if (degisim or 0) > 0 else HEX["kirmizi"] if (degisim or 0) < 0 else "#CBD5E1"
    ok = "↑" if (degisim or 0) > 0 else "↓" if (degisim or 0) < 0 else ""
    sol = [Paragraph(f'<font name="DVX" size="21" color="#FFFFFF">{ad}</font>', _st("pk", leading=26)),
           Spacer(1, 3), Paragraph(f'<font color="#94A3B8">{alt_satir}</font>', _st("pa", fontSize=8.6, leading=11.5))]
    if guncel:
        sol.append(Paragraph(f'<font color="{HEX["altin"]}">•</font> <font color="#CBD5E1">{guncel}</font>', _st("pg", fontSize=7.4, leading=10)))
    if rozet:
        rw = pdfmetrics.stringWidth(rozet, "DVB", 7.6) + 18
        rz = Table([[Paragraph(f'<font name="DVB" size="7.6" color="{HEX["gece"]}">{rozet}</font>', _st("pr", alignment=1, leading=10))]], colWidths=[rw])
        rz.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), R["altin"]), ("ROUNDEDCORNERS", [7, 7, 7, 7]),
                                ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        rz.hAlign = "LEFT"; sol += [Spacer(1, 7), rz]
    sag = [Paragraph(f'<font name="DVX" size="20" color="#FFFFFF">{fiyat_metni}</font>', _st("pf", alignment=2, leading=24)),
           Paragraph((f'<font name="DVB" color="{renk}">{ok} {_yuzde(degisim, 2)}</font><font color="#94A3B8"> son gün</font>'
                      if degisim is not None else '<font color="#94A3B8">son fiyat</font>'), _st("pd", alignment=2, fontSize=9, leading=12))]
    t = Table([[sol, sag]], colWidths=[W * 0.64, W * 0.36])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    t.hAlign = "LEFT"
    return [Spacer(1, 2), t, Spacer(1, 30)]



# =====================================================================
# KURUMSAL ARAŞTIRMA BİLEŞENLERİ
# =====================================================================
GORUS_RENK = {"OLUMLU": ("yesil", "yesil_acik"), "ILIMLI OLUMLU": ("yesil", "yesil_acik"), "NÖTR": ("sari", "sari_acik"),
              "TEMKİNLİ": ("turuncu", "sari_acik"), "OLUMSUZ": ("kirmizi", "kirmizi_acik"),
              "GÜÇLÜ AL": ("yesil", "yesil_acik"), "AL": ("yesil", "yesil_acik"), "SAT": ("kirmizi", "kirmizi_acik"),
              "GÜÇLÜ SAT": ("kirmizi", "kirmizi_acik"), "GÜÇLÜ POZİTİF": ("yesil", "yesil_acik"), "POZİTİF": ("yesil", "yesil_acik"),
              "NEGATİF": ("kirmizi", "kirmizi_acik"), "GÜÇLÜ NEGATİF": ("kirmizi", "kirmizi_acik")}


def ozet_paneli(etiket, baslik, gorus, metin, W, alt_bilgi=None):
    """Yatırım özeti paneli: üst etiket, başlık tezi, görüş rozeti ve yönetici özeti paragrafı."""
    k, a = GORUS_RENK.get(gorus, ("sari", "sari_acik")); koyu = HEX.get(k, HEX["sari"]); acik = R[a]
    rw = pdfmetrics.stringWidth(gorus, "DVB", 7.6) + 16
    rozet = Table([[Paragraph(f'<font name="DVB" size="7.6" color="{koyu}">{gorus}</font>', _st("gz", alignment=1, leading=9.5))]], colWidths=[rw])
    rozet.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), acik), ("ROUNDEDCORNERS", [6, 6, 6, 6]),
                               ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]))
    ust = Table([[Paragraph(f'<font name="DVB" size="7.2" color="{HEX["altin"]}">{etiket.upper()}</font>', _st("oe", leading=9)),
                  Paragraph(f'<font size="7" color="{HEX["soluk"]}">GENEL GÖRÜNÜM</font>', _st("og", alignment=2, leading=9)), rozet]],
                colWidths=[W - 24 - rw - 70, 66, rw + 4])
    ust.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    icerik = [ust, Spacer(1, 4), Paragraph(f'<font name="DVX" size="12.5" color="{HEX["murekkep"]}">{esc(baslik)}</font>', _st("ob", leading=16)),
              Spacer(1, 5), Paragraph(esc(metin), _st("om", fontSize=8.9, leading=13, alignment=4, textColor=R["metin"]))]
    if alt_bilgi:
        icerik += [Spacer(1, 4), Paragraph(f'<font color="{HEX["soluk"]}">{alt_bilgi}</font>', _st("oa", fontSize=7, leading=9))]
    t = Table([[icerik]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")), ("LINEBEFORE", (0, 0), (0, -1), 3, R["altin"]),
                           ("BOX", (0, 0), (-1, -1), 0.6, R["cizgi"]), ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                           ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    t.hAlign = "LEFT"; return t


def tez_tablosu(olumlu, olumsuz, W, b1="Yatırım tezini destekleyenler", b2="Riskler ve izlenecekler"):
    """İki sütunlu yatırım tezi: her madde kalın başlık + açıklama."""
    def sutun(liste, bas, renk):
        s = [[Paragraph(f'<font name="DVB" color="{renk}">{bas}</font>', _st("tzb", fontSize=9, leading=12))]]
        for i, (lead, txt) in enumerate(liste, 1):
            s.append([Paragraph(f'<font name="DVB" color="{HEX["murekkep"]}">{i}. {lead}.</font> {esc(txt)}', _st("tzm", fontSize=8.2, leading=11.4))])
        if not liste:
            s.append([Paragraph(f'<font color="{HEX["soluk"]}">Bu başlıkta öne çıkan bir unsur bulunmuyor.</font>', _st("tzm", fontSize=8.2, leading=11.4))])
        t = Table(s, colWidths=[W / 2 - 10])
        t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 1.2, colors.HexColor(renk)), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        return t
    t = Table([[sutun(olumlu, b1, HEX["yesil"]), sutun(olumsuz, b2, HEX["kirmizi"])]], colWidths=[W / 2 + 10, W / 2 - 10])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, 0), 20)]))
    t.hAlign = "LEFT"; return t


def senaryo_kartlari(liste, W):
    """[(başlık, değer, potansiyel, açıklama)] → yan yana senaryo kartları."""
    if not liste: return Spacer(1, 0)
    hucre = []; gw = (W - 10 * (len(liste) - 1)) / len(liste)
    for bas, deger, pot, ac in liste:
        renk = (HEX["yesil"] if ("Olumlu" in bas or "Yükseliş" in bas) else
                HEX["kirmizi"] if ("Olumsuz" in bas or "Düşüş" in bas) else HEX["ana"])
        ic = [Paragraph(f'<font name="DVB" size="7.4" color="{renk}">{bas.upper()}</font>', _st("sk1", leading=9)), Spacer(1, 2),
              Paragraph(f'<font name="DVX" size="14" color="{HEX["murekkep"]}">{deger}</font>&nbsp;&nbsp;<font name="DVB" size="9" color="{renk}">{pot}</font>', _st("sk2", leading=18)),
              Spacer(1, 2), Paragraph(esc(ac), _st("sk3", fontSize=7.8, leading=10.6, textColor=R["metin"]))]
        k = Table([[ic]], colWidths=[gw])
        k.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, R["cizgi"]), ("LINEABOVE", (0, 0), (-1, 0), 2.5, colors.HexColor(renk)),
                               ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 7),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        hucre.append(k)
    t = Table([hucre], colWidths=[gw + (10 if i < len(liste) - 1 else 0) for i in range(len(liste))])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    t.hAlign = "LEFT"; return t


def iki_liste(b1, l1, b2, l2, W):
    """Katalizörler / riskler gibi iki sütunlu madde listesi."""
    def sutun(bas, l, renk):
        s = [[Paragraph(f'<font name="DVB" color="{renk}">{bas}</font>', _st("ilb", fontSize=9, leading=12))]]
        for x in l or ["–"]:
            s.append([Paragraph(f'<font color="{renk}">•</font>&nbsp; {esc(bas_buyuk_(x))}', _st("ilm", fontSize=8.2, leading=11.2))])
        t = Table(s, colWidths=[W / 2 - 10])
        t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 1.2, colors.HexColor(renk)), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
        return t
    t = Table([[sutun(b1, l1, HEX["ana"]), sutun(b2, l2, HEX["turuncu"])]], colWidths=[W / 2 + 10, W / 2 - 10])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, 0), 20)]))
    t.hAlign = "LEFT"; return t


def bas_buyuk_(s):
    return s[:1].upper() + s[1:] if s else s
