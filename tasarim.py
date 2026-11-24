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
    p = Paragraph(f'<font name="DVB" color="{koyu.hexval().replace("0x", "#")}">{baslik}</font>&nbsp;&nbsp;{metin}', ST["kutu"])
    t = Table([[p]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), acik), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("ROUNDEDCORNERS", [7, 7, 7, 7]),
                           ("LINEBEFORE", (0, 0), (0, -1), 3, koyu)]))
    t.hAlign = "LEFT"
    return t


def trafik_listesi(satirlar, W):
    """Tek bakışta listesi: [(soru, cevap, durum)] → renkli nokta + soru + sade cevap."""
    veri = []
    for soru, cevap, durum in satirlar:
        koyu, acik = durum_rengi(durum)
        etiket = {"iyi": "İYİ", "orta": "ORTA", "zayif": "ZAYIF"}.get(durum, "–")
        rozet = Table([[Paragraph(f'<font name="DVB" size="7" color="{koyu.hexval().replace("0x", "#")}">{etiket}</font>',
                                  _st("r", alignment=1))]], colWidths=[40])
        rozet.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), acik), ("ROUNDEDCORNERS", [6, 6, 6, 6]),
                                   ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        veri.append([rozet, Paragraph(f'<font name="DVB">{soru}</font><br/>{cevap}', _st("tl", fontSize=8.6, leading=11.8))])
    t = Table(veri, colWidths=[48, W - 48])
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
            c.setFillColor(R["murekkep"]); c.rect(0, H_ - kapak_yuk, W_, kapak_yuk, fill=1, stroke=0)
            c.setFillColor(R["ana"]); c.rect(0, H_ - kapak_yuk, W_, 3, fill=1, stroke=0)
        else:
            c.setFillColor(R["ana"]); c.roundRect(1.5 * cm, H_ - 1.02 * cm, 4, 10, 1.5, fill=1, stroke=0)
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
