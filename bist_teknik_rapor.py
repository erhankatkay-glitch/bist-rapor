# -*- coding: utf-8 -*-
"""Teknik analiz görselleri ve PDF raporları (tek varlık + toplu kapanış bülteni)."""
import os, io, math, datetime as dt
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether,
                                CondPageBreak, Flowable, Image)

import tasarim as TS
from tasarim import ST, Bolum, bilgi_kutusu, sayfa_cizici, kart_izgarasi
import bist_teknik as T
import analist as AN

C = TS.GRAFIK; R = TS.R; HEX = TS.HEX
YESIL, KIRMIZI = HEX["yesil"], HEX["kirmizi"]


_f = T.sayi


def _yz(x, d=1):
    if x is None or (isinstance(x, float) and math.isnan(x)): return "–"
    return ("+" if x > 0 else "-" if x < 0 else "") + f"%{abs(x) * 100:.{d}f}".replace(".", ",")


KISA = {"GÜÇLÜ AL": "G.AL", "AL": "AL", "NÖTR": "NÖTR", "SAT": "SAT", "GÜÇLÜ SAT": "G.SAT"}


def _png(fig, dpi=150):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=dpi, bbox_inches="tight"); plt.close(fig); b.seek(0); return b


def _img(b, gen, oran):
    return Image(b, width=gen, height=gen * oran)


# =====================================================================
# MUM GRAFİĞİ
# =====================================================================
def g_teknik(a, baslik, kompakt=False, dpi=150):
    """Mum grafiği + EMA20/50, SMA200, Bollinger, destek/direnç, Fibonacci, formasyon çizgileri,
    FVG kutuları, mum formasyonu işaretleri; alt panellerde hacim, RSI, MACD."""
    h, G = a["h"], a["G"]; N = T.AYAR[a["tf"]]["goster"] if not kompakt else min(90, T.AYAR[a["tf"]]["goster"])
    bas = max(len(h) - N, 0); w = h.iloc[bas:]; g = G.iloc[bas:]; x = np.arange(len(w))
    if kompakt:
        fig = plt.figure(figsize=(7.5, 3.0)); gs = fig.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0.05)
    else:
        fig = plt.figure(figsize=(7.5, 6.4)); gs = fig.add_gridspec(4, 1, height_ratios=[4.2, 0.8, 1.1, 1.1], hspace=0.06)
    ax = fig.add_subplot(gs[0])
    yuk = w["Close"] >= w["Open"]
    renk = np.where(yuk, YESIL, KIRMIZI)
    ax.vlines(x, w["Low"], w["High"], color=renk, lw=0.7)
    govde = (w["Close"] - w["Open"]).abs().replace(0, (w["High"] - w["Low"]).mean() * 0.01)
    ax.bar(x, govde, bottom=np.minimum(w["Open"], w["Close"]), color=renk, width=0.62, lw=0)
    ax.fill_between(x, g["BB_ALT"], g["BB_UST"], color=C["acik"], alpha=0.18, lw=0, label="Bollinger (20,2)")
    for s_, r_, ad, lw in (("EMA20", C["tur"], "EMA 20", 1.0), ("EMA50", C["mavi"], "EMA 50", 1.0), ("SMA200", C["lac"], "SMA 200", 1.2)):
        if g[s_].notna().any(): ax.plot(x, g[s_], color=r_, lw=lw, label=ad)
    lo_, hi_ = float(w["Low"].min()), float(w["High"].max()); pad = (hi_ - lo_) * 0.08
    ax.set_ylim(lo_ - pad, hi_ + pad); ax.set_xlim(-1, len(w) + (10 if not kompakt else 6))
    xr = len(w) + 0.5
    # Destek / direnç
    for v, n_ in a["sr"]["destek"][:2]:
        if lo_ - pad < v < hi_ + pad:
            ax.axhline(v, color=YESIL, lw=0.9, alpha=0.8); ax.text(xr, v, f"D {_f(v)}", fontsize=6, color=YESIL, va="center")
    for v, n_ in a["sr"]["direnc"][:2]:
        if lo_ - pad < v < hi_ + pad:
            ax.axhline(v, color=KIRMIZI, lw=0.9, alpha=0.8); ax.text(xr, v, f"R {_f(v)}", fontsize=6, color=KIRMIZI, va="center")
    # Fibonacci
    fb = a.get("fib")
    if fb and not kompakt:
        for r_, v in fb["seviye"].items():
            if lo_ - pad < v < hi_ + pad and r_ not in (0, 1):
                ax.axhline(v, color=HEX["mor"], lw=0.6, ls=(0, (4, 3)), alpha=0.7)
                ax.text(-0.5, v, f"Fib {r_ * 100:.1f}", fontsize=5.5, color=HEX["mor"], va="bottom")
    # FVG
    if not kompakt:
        for ad, alt, ust, t in a["pa"]["fvg"]:
            try: xi = w.index.get_loc(t)
            except KeyError: continue
            ax.add_patch(plt.Rectangle((xi, alt), len(w) - xi, ust - alt, color=YESIL if "Boğa" in ad else KIRMIZI, alpha=0.08, lw=0))
    # Formasyon çizimleri
    def X(i): return i - bas
    for cz in a["cizim"]:
        r_ = YESIL if cz["yon"] > 0 else KIRMIZI if cz["yon"] < 0 else HEX["sari"]
        for anahtar in ("ust", "alt", "trend", "boyun"):
            if anahtar in cz:
                (i0, y0), (i1, y1) = cz[anahtar]
                if X(i1) >= 0:
                    if X(i0) < 0:
                        y0 = y0 + (y1 - y0) * (0 - X(i0)) / max(X(i1) - X(i0), 1); i0 = bas
                    ax.plot([X(i0), X(i1)], [y0, y1], color=r_, lw=1.3, ls="--")
        if "x" in cz and X(cz["x"][0]) >= 0:
            ax.plot([X(i) for i in cz["x"]], cz["y"], color=r_, lw=1.2, marker="o", ms=3)
            if "yatay" in cz: ax.plot([X(cz["x"][0]), len(w) - 1], [cz["yatay"]] * 2, color=r_, lw=1.0, ls=":")
        if cz.get("ad") and not kompakt:
            ax.text(0.01, 0.97 - 0.06 * a["cizim"].index(cz), cz["ad"], transform=ax.transAxes, fontsize=6.5, color=r_, va="top",
                    fontweight="bold")
    # Mum formasyonu işaretleri
    for m in a["mum"]:
        xi = m["bar"] - bas
        if xi < 0 or m["yon"] == 0: continue
        if m["yon"] > 0:
            ax.scatter([xi], [w["Low"].iloc[xi] - pad * 0.25], marker="^", color=YESIL, s=18, zorder=5)
        else:
            ax.scatter([xi], [w["High"].iloc[xi] + pad * 0.25], marker="v", color=KIRMIZI, s=18, zorder=5)
    ax.legend(fontsize=6, loc="lower left", ncol=4, frameon=False)
    ax.set_title(baslik, loc="left", fontsize=9)
    ax.yaxis.tick_right(); ax.tick_params(labelbottom=False, labelsize=6.5)
    son = float(w["Close"].iloc[-1])
    ax.annotate(_f(son), (len(w) - 1, son), xytext=(xr, son), fontsize=6.5, color="white", va="center",
                bbox=dict(boxstyle="round,pad=0.2", fc=YESIL if yuk.iloc[-1] else KIRMIZI, ec="none"))
    axs = [ax]
    a2 = fig.add_subplot(gs[1], sharex=ax)
    a2.bar(x, w["Volume"], color=renk, alpha=0.5, width=0.62); a2.plot(x, g["HACIM_ORT"], color=C["gri"], lw=0.8)
    a2.set_yticks([]); a2.set_ylabel("Hacim", fontsize=6); axs.append(a2)
    if not kompakt:
        a2.tick_params(labelbottom=False)
        a3 = fig.add_subplot(gs[2], sharex=ax)
        a3.plot(x, g["RSI"], color=HEX["mor"], lw=1); a3.axhspan(30, 70, color=C["acik"], alpha=0.15, lw=0)
        for y_ in (30, 70): a3.axhline(y_, color=C["gri"], lw=0.6, ls="--")
        a3.set_ylim(0, 100); a3.set_ylabel("RSI", fontsize=6); a3.tick_params(labelbottom=False, labelsize=6); a3.yaxis.tick_right()
        a4 = fig.add_subplot(gs[3], sharex=ax)
        hs = g["MACD_HIST"]; a4.bar(x, hs, color=np.where(hs >= 0, YESIL, KIRMIZI), alpha=0.6, width=0.62)
        a4.plot(x, g["MACD"], color=C["mavi"], lw=0.9); a4.plot(x, g["MACD_SIG"], color=C["tur"], lw=0.9)
        a4.set_ylabel("MACD", fontsize=6); a4.tick_params(labelsize=6); a4.yaxis.tick_right(); axs += [a3, a4]
    alt = axs[-1]
    adim = max(len(w) // 7, 1); tick = list(range(0, len(w), adim))
    bic = {"G": "%d.%m.%y", "1S": "%d.%m %H:%M", "4S": "%d.%m %H:%M"}.get(a["tf"], "%m.%Y")
    alt.set_xticks(tick); alt.set_xticklabels([w.index[i].strftime(bic) for i in tick], fontsize=6)
    for a_ in axs:
        a_.grid(alpha=0.25, lw=0.5)
        for s in ("top", "left"): a_.spines[s].set_visible(False)
    return _png(fig, dpi)


# =====================================================================
# GÖSTERGE (yarım daire)
# =====================================================================
class TeknikGosterge(Flowable):
    def __init__(self, baslik, puan, etiket, alt, gen=160, yuk=118):
        super().__init__(); self.b, self.p, self.e, self.a, self.gen, self.yuk = baslik, puan, etiket, alt, gen, yuk
    def wrap(self, *a):
        return self.gen, self.yuk
    def draw(self):
        c = self.canv
        c.setFillColor(colors.white); c.setStrokeColor(R["cizgi"]); c.setLineWidth(0.8)
        c.roundRect(0, 0, self.gen, self.yuk, 9, stroke=1, fill=1)
        c.setFillColor(R["altin"]); c.roundRect(10, self.yuk - 17, 3, 10, 1.5, stroke=0, fill=1)
        c.setFillColor(R["murekkep"]); c.setFont("DVB", 8); c.drawString(17, self.yuk - 15.5, self.b.upper())
        if self.p is None:
            c.setFont("DV", 8); c.setFillColor(R["soluk"]); c.drawCentredString(self.gen / 2, self.yuk / 2, "Veri yetersiz"); return
        cx, cy, r = self.gen / 2, 34, min(self.gen / 2 - 16, 50)
        renkler = [R["kirmizi"], colors.HexColor("#F87171"), colors.HexColor("#CBD5E1"), colors.HexColor("#4ADE80"), R["yesil"]]
        for i, rk in enumerate(renkler):
            c.setFillColor(rk); c.setStrokeColor(colors.white); c.setLineWidth(1.2)
            c.wedge(cx - r, cy - r, cx + r, cy + r, 180 - i * 36, -36, stroke=1, fill=1)
        c.setFillColor(colors.white); c.circle(cx, cy, r * 0.62, stroke=0, fill=1)
        c.rect(cx - r - 2, cy - r - 2, 2 * r + 4, r + 2, stroke=0, fill=1)
        aci = math.radians(180 - self.p / 100 * 180)
        c.setStrokeColor(R["murekkep"]); c.setLineWidth(2); c.setLineCap(1)
        c.line(cx, cy, cx + 0.88 * r * math.cos(aci), cy + 0.88 * r * math.sin(aci))
        c.setFillColor(R["murekkep"]); c.circle(cx, cy, 3, stroke=0, fill=1)
        renk = R["yesil"] if "AL" in self.e else R["kirmizi"] if "SAT" in self.e else R["sari"]
        c.setFillColor(renk); c.setFont("DVX", 11); c.drawCentredString(cx, cy - 15, self.e)
        c.setFillColor(R["soluk"]); c.setFont("DV", 6.6); c.drawCentredString(cx, 7, self.a[:42])
        c.setFont("DV", 5.8); c.drawString(cx - r - 2, cy - 7, "Sat"); c.drawRightString(cx + r + 2, cy - 7, "Al")


def gosterge_satiri(s, W, tfler=("G", "H", "A")):
    hucre = []
    for tf in tfler:
        a = s["tf"].get(tf)
        if a:
            sy = a["oy"]["sayim"]
            hucre.append(TeknikGosterge(T.TF_AD[tf], a["puan"], a["etiket"], f"Puan {a['puan']:.0f} · Al {sy['AL']} · Sat {sy['SAT']} · Nötr {sy['NÖTR']}",
                                        gen=(W - 16) / 3))
        else:
            hucre.append(TeknikGosterge(T.TF_AD[tf], None, "", "", gen=(W - 16) / 3))
    hucre = hucre + [""] * (3 - len(hucre))
    t = Table([hucre], colWidths=[(W - 16) / 3 + 8, (W - 16) / 3 + 8, (W - 16) / 3])
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (1, 0), 8), ("RIGHTPADDING", (2, 0), (2, 0), 0)]))
    t.hAlign = "LEFT"; return t


# =====================================================================
# TEK VARLIK PDF
# =====================================================================
def _karar_renkli(k):
    r = YESIL if k == "AL" else KIRMIZI if k == "SAT" else HEX["sari"]
    return Paragraph(f'<font name="DVB" color="{r}">{k}</font>', TS._st("kr", fontSize=7.6, alignment=1, leading=9))


def _yon(y):
    return Paragraph(f'<font name="DVB" color="{YESIL if y > 0 else KIRMIZI if y < 0 else HEX["sari"]}">'
                     f'{"Olumlu" if y > 0 else "Olumsuz" if y < 0 else "Nötr"}</font>', TS._st("yn", fontSize=7.4, leading=9))


SOZLUK_TEKNIK = [
    ("Hareketli ortalama (SMA/EMA)", "Belirli dönemin ortalama fiyatı. Fiyat ortalamanın üzerindeyse eğilim yukarı kabul edilir. EMA son fiyatlara daha fazla ağırlık verir."),
    ("RSI / Stokastik / Williams %R", "Momentum osilatörleri. Aşırı alım (RSI>70) ve aşırı satım (RSI<30) bölgelerini gösterir."),
    ("MACD", "İki üssel ortalama farkı; sinyal çizgisini yukarı kesmesi al, aşağı kesmesi sat sinyali sayılır."),
    ("ADX / DMI", "Trendin gücünü (ADX>25 güçlü) ve yönünü (+DI / −DI) ölçer."),
    ("Bollinger / Keltner", "Fiyatın ortalamadan sapma bantları. Bantların daralması sert hareket öncesi sıkışmayı gösterir."),
    ("Ichimoku", "Bulut, Tenkan ve Kijun çizgilerinden oluşan trend sistemi. Fiyat bulutun üzerindeyse olumlu."),
    ("SuperTrend / Parabolik SAR", "ATR tabanlı trend takip göstergeleri; takip eden stop seviyesi olarak da kullanılır."),
    ("OBV / MFI / CMF", "Hacme dayalı para akışı göstergeleri."),
    ("Fibonacci", "Son büyük hareketin %23,6–38,2–50–61,8–78,6 düzeltme seviyeleri; sık izlenen destek/direnç bölgeleridir."),
    ("Pivot noktaları", "Önceki mumun en yüksek, en düşük ve kapanışından hesaplanan bir sonraki dönemin destek (S) ve direnç (R) seviyeleri."),
    ("Formasyon", "İkili tepe/dip, OBO/TOBO, üçgen, kama, bayrak gibi grafik şekilleri. 'Teyit/kırılım' durumunda daha anlamlıdır."),
    ("Price action (BOS / CHoCH)", "Yapı kırılımı (BOS) trendin devamını; karakter değişimi (CHoCH) olası dönüşü gösterir."),
    ("FVG (adil değer boşluğu)", "Hızlı hareketlerde oluşan, fiyatın sıklıkla geri dönüp doldurduğu boşluk bölgesi."),
    ("Uyumsuzluk", "Fiyat ile göstergenin farklı yönde tepe/dip yapması; ivme kaybına işaret eder."),
]


def teknik_pdf(s, dosya):
    W = A4[0] - 3.0 * cm; PW = (W - 10) / 2; sym = s["para"]
    sayfa = sayfa_cizici(s["kod"], "Teknik Analiz Raporu", f"{dt.date.today():%d.%m.%Y}", kapak_yuk=4.7 * cm)
    doc = SimpleDocTemplate(dosya, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.6 * cm,
                            bottomMargin=1.4 * cm, title=f"{s['kod']} Teknik Analiz")
    E = []; g = s["tf"].get("G") or next(a for a in s["tf"].values() if a)
    E += TS.pro_kapak(s["ad"], f"Teknik Analiz Raporu  ·  {s['kod']}  ·  Günlük, haftalık ve aylık kapanışlar",
                      f"{_f(g['fiyat'])} {sym}", g.get("degisim"), W, rozet=f"TEKNİK GÖRÜNÜM: {s['etiket']}",
                      guncel=f"Son kapanış verisi: {TS.zaman_metni(s.get('fiyat_zamani'))}  ·  Rapor: {dt.datetime.now(dt.timezone(dt.timedelta(hours=3))):%d.%m.%Y %H:%M} TSİ")
    E.append(gosterge_satiri(s, W)); E.append(Spacer(1, 8))
    if s["tf"].get("1S") or s["tf"].get("4S"):
        E.append(Paragraph("Kısa vade (gün içi)", ST["h2"])); E.append(gosterge_satiri(s, W, ("1S", "4S"))); E.append(Spacer(1, 6))
    E.append(TS.ozet_paneli("Teknik görünüm özeti", AN.teknik_baslik(s), s["etiket"], AN.teknik_ozet(s), W)); E.append(Spacer(1, 4))
    # Önemli seviyeler
    E.append(Paragraph("Önemli seviyeler", ST["h2"]))
    satir = [["", "Günlük", "Haftalık", "Aylık"]]
    def hucre(tf, f):
        a = s["tf"].get(tf)
        try: return f(a) if a else "–"
        except Exception: return "–"
    satir.append(["Direnç 2"] + [hucre(t, lambda a: _f(a["sr"]["direnc"][1][0])) for t in "GHA"])
    satir.append(["Direnç 1"] + [hucre(t, lambda a: _f(a["sr"]["direnc"][0][0])) for t in "GHA"])
    satir.append(["Son fiyat"] + [hucre(t, lambda a: _f(a["fiyat"])) for t in "GHA"])
    satir.append(["Destek 1"] + [hucre(t, lambda a: _f(a["sr"]["destek"][0][0])) for t in "GHA"])
    satir.append(["Destek 2"] + [hucre(t, lambda a: _f(a["sr"]["destek"][1][0])) for t in "GHA"])
    satir.append(["Pivot (klasik P)"] + [hucre(t, lambda a: _f(a["pivot"]["Klasik"]["P"])) for t in "GHA"])
    satir.append(["Fibonacci alt / üst"] + [hucre(t, lambda a: f"{_f(a['fib']['alt'])} / {_f(a['fib']['ust'])}") for t in "GHA"])
    satir.append(["Piyasa yapısı"] + [hucre(t, lambda a: a["pa"]["yapi"].split(" (")[0]) for t in "GHA"])
    E.append(TS.tablo(satir, [W * .28, W * .24, W * .24, W * .24], font=7.6))
    E.append(Spacer(1, 6))
    _sn = AN.teknik_senaryo(s)
    if _sn:
        E.append(KeepTogether([Paragraph("İşlem senaryoları (günlük)", ST["h2"]),
                               TS.senaryo_kartlari([(b_, f"Hedef {h_}", "", f"Tetikleyici: {t_}. {i_}.") for b_, t_, h_, i_ in _sn], W)]))
    _baslik_sinyal = Paragraph("Öne çıkan sinyaller (günlük + haftalık)", ST["h2"])
    tum = []
    for tf in ("G", "H"):
        a = s["tf"].get(tf)
        if a: tum += [(f"[{T.TF_AD[tf][0]}] " + x[0].split(": ", 1)[-1], x[1], x[3]) for x in a["sinyal"]]
    pos = [x[0] for x in sorted([x for x in tum if x[1] > 0], key=lambda x: -x[2])]
    neg = [x[0] for x in sorted([x for x in tum if x[1] < 0], key=lambda x: -x[2])]
    E.append(KeepTogether([_baslik_sinyal, TS.sinyal_listesi(pos, neg, W, n=5)]))

    # Her zaman dilimi
    for n, tf in enumerate([t for t in ("1S", "4S", "G", "H", "A") if s["tf"].get(t)], 1):
        a = s["tf"].get(tf)
        if not a: continue
        E.append(PageBreak()); E.append(Bolum(n, f"{T.TF_AD[tf]} grafik: {a['etiket'].lower()} (puan {a['puan']:.0f}/100)", W))
        E.append(_img(g_teknik(a, f"{s['kod']} · {T.TF_AD[tf]} · son kapanış {a['tarih']:%d.%m.%Y}"), W, 6.4 / 7.5 * 0.97))
        oy = a["oy"]
        mt = [["Hareketli ortalama", "Değer", "Karar"]] + [[x[0], _f(x[1]), _karar_renkli(x[2])] for x in oy["ma"]]
        mt.append([f"Özet: {oy['ma_etiket']}", "", ""])
        ot = [["Osilatör", "Değer", "Karar"]] + [[x[0], _f(x[1], 2), _karar_renkli(x[2])] for x in oy["osc"]]
        ot.append([f"Özet: {oy['osc_etiket']}", "", ""])
        E.append(CondPageBreak(7 * cm))
        E.append(TS.yan_yana(TS.tablo(mt, [PW * .46, PW * .3, PW * .24], font=7.2, kalin_son=True),
                             TS.tablo(ot, [PW * .5, PW * .26, PW * .24], font=7.2, kalin_son=True), W))
        E.append(Paragraph("Trend, volatilite ve hacim", ST["h2"]))
        E.append(TS.tablo([["Gösterge", "Değer", "Yorum", "Yön"]] + [[d_[0], d_[1], Paragraph(d_[2], ST["hucre"]), _yon(d_[3])] for d_ in a["durum"]],
                          [W * .26, W * .18, W * .42, W * .14], hizala_sol=(0, 2), font=7.2))
        if a["sinyal"]:
            E.append(KeepTogether([Paragraph("Formasyonlar, mumlar ve sinyaller", ST["h2"]),
                                   TS.tablo([["Sinyal", "Yön", "Açıklama"]] + [[Paragraph(x[0], ST["hucre"]), _yon(x[1]), Paragraph(TS.esc(x[2]), ST["hucre"])] for x in a["sinyal"]],
                                            [W * .34, W * .12, W * .54], hizala_sol=(0, 1, 2), font=7.2)]))
        fb = a["fib"]; pv = a["pivot"]
        if fb:
            ft = [["Fibonacci", f"Seviye ({sym})"]] + [[f"%{r_ * 100:.1f}".replace(".", ","), _f(v)] for r_, v in fb["seviye"].items()] + \
                 [[f"Uzantı %{r_ * 100:.1f}".replace(".", ","), _f(v)] for r_, v in fb["uzanti"].items()]
            pt = [["Pivot", "Klasik", "Fibonacci"]] + [[k_, _f(pv["Klasik"][k_]), _f(pv["Fibonacci"][k_])] for k_ in ("R3", "R2", "R1", "P", "S1", "S2", "S3")]
            yon = "dipten tepeye yükseliş" if fb["yukari"] else "tepeden dibe düşüş"
            E.append(KeepTogether([Paragraph("Fibonacci ve pivot seviyeleri", ST["h2"]),
                                   Paragraph(f"Son {T.AYAR[tf]['pencere_fib']} mumdaki ana hareket: {yon} ({_f(fb['dip'])} – {_f(fb['tepe'])}). "
                                             f"Fiyat bu hareketin %{fb['duzeltme'] * 100:.0f}'i kadar geri çekilmiş durumda.", ST["kucuk"]),
                                   Spacer(1, 3),
                                   TS.yan_yana(TS.tablo(ft, [PW * .5, PW * .5], font=7.2), TS.tablo(pt, [PW * .3, PW * .35, PW * .35], font=7.2), W)]))
        pa = a["pa"]; sat = [f"Piyasa yapısı: <b>{pa['yapi']}</b>."]
        for ad, alt_, ust_, t_ in pa["fvg"]: sat.append(f"{ad}: {_f(alt_)} – {_f(ust_)} ({t_:%d.%m.%Y}).")
        if pa.get("ob"): sat.append(f"{pa['ob'][0]}: {_f(pa['ob'][1])} – {_f(pa['ob'][2])} ({pa['ob'][3]:%d.%m.%Y}).")
        E.append(KeepTogether([Paragraph("Price action", ST["h2"])] + [Paragraph("• " + x, ST["madde"]) for x in sat]))
    gg = s["tf"].get("G")
    if gg is not None:
        try:
            import ileri_rapor as IR, bist_ileri as IL
            paket = IL.ileri_paket(gg["h"], kripto=s.get("tur") == "kripto", aktif=[x[0] for x in gg["sinyal"]], G=gg["G"])
            s["ileri"] = paket; n += 1
            E += IR.ileri_bolum(gg["h"], paket, W, {"₺": "TL", "$": "$"}.get(sym, ""), n)
        except Exception as ex:
            print("ileri analiz atlandı:", ex)
    E.append(PageBreak()); E.append(Bolum(n + 1, "Sözlük ve uyarılar", W))
    E.append(TS.tablo([["Terim", "Sade anlatım"]] + [[a_, Paragraph(b_, ST["hucre"])] for a_, b_ in SOZLUK_TEKNIK], [W * .28, W * .72], hizala_sol=(0, 1), font=7.4))
    E.append(Spacer(1, 6))
    E.append(Paragraph("Teknik puan: hareketli ortalama ve osilatör oylaması (%55), formasyon/mum/kesişim/uyumsuzluk sinyalleri (%30) ve "
                       "piyasa yapısının (%15) birleşimidir; 0–100 arasıdır. Genel puan günlük (%30), haftalık (%40) ve aylık (%30) puanların "
                       "ağırlıklı ortalamasıdır. Formasyonlar algoritmik olarak tespit edilir ve hatalı olabilir. Veriler Yahoo Finance kaynaklıdır. "
                       "Bu rapor otomatik bir model çıktısıdır; yatırım tavsiyesi değildir.", ST["kucuk"]))
    doc.build(E, onFirstPage=sayfa, onLaterPages=sayfa)
    return dosya


# =====================================================================
# TOPLU KAPANIŞ BÜLTENİ
# =====================================================================
def kategoriler(satirlar, n=12):
    df = pd.DataFrame(satirlar)
    if df.empty: return {}
    df = df.sort_values("Teknik puan", ascending=False)
    K = {}
    K["En güçlü teknik görünüm"] = df.head(n)
    K["Yukarı kırılımlar ve formasyon teyitleri"] = df[df["Kırılım"]].head(n)
    K["Boğa mum formasyonları (son kapanış)"] = df[df["Mum +"].astype(str).str.len() > 0].head(n)
    K["Altın kesişim / pozitif uyumsuzluk"] = df[df.get("Sinyal +", df["Kesişim/Uyumsuzluk"]).astype(str).str.contains("Altın kesişim|Pozitif uyumsuzluk|al kesişimi|yukarı kesti|al sinyaline")].head(n)
    if "Balina" in df:
        b = df["Balina"].fillna("").astype(str)
        K["Balina alımı / birikim izleri"] = df[b.str.contains("alımı|Alım emilimi|birikim")].head(n)
        K["Balina satışı / dağıtım izleri"] = df[b.str.contains("satışı|Satış emilimi|dağıtım")].sort_values("Teknik puan").head(n)
    K["Aşırı satım (RSI < 30)"] = df[df["RSI"] < 30].sort_values("RSI").head(n)
    K["Aşırı alım (RSI > 70)"] = df[df["RSI"] > 70].sort_values("RSI", ascending=False).head(n)
    K["Aşağı kırılımlar"] = df[df["Kırılım −"]].sort_values("Teknik puan").head(n)
    K["Ayı mum formasyonları (son kapanış)"] = df[df["Mum −"].astype(str).str.len() > 0].sort_values("Teknik puan").head(n)
    K["En zayıf teknik görünüm"] = df.sort_values("Teknik puan").head(n)
    return {k: v for k, v in K.items() if len(v)}


def bulten_pdf(baslik, satirlar, analizler, dosya, endeks=None, sym="₺", ekler=None):
    ekler = ekler or {}
    W = A4[0] - 3.0 * cm
    sayfa = sayfa_cizici("BÜLTEN", baslik, f"{dt.date.today():%d.%m.%Y}", kapak_yuk=4.7 * cm)
    doc = SimpleDocTemplate(dosya, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.6 * cm,
                            bottomMargin=1.4 * cm, title=baslik)
    df = pd.DataFrame(satirlar); E = []
    ek = endeks["tf"]["G"] if endeks and endeks["tf"].get("G") else None
    E += TS.pro_kapak(baslik, f"{len(df)} varlık  ·  günlük, haftalık ve aylık kapanış analizi",
                      f"{_f(ek['fiyat'])}" if ek else f"{len(df)} varlık", ek["degisim"] if ek else None, W,
                      rozet=f"{endeks['ad'].upper()}: {endeks['etiket']}" if endeks else None,
                      guncel=f"Üretim: {dt.datetime.now(dt.timezone(dt.timedelta(hours=3))):%d.%m.%Y %H:%M} TSİ")
    if len(df):
        al = int(df["Genel"].isin(["AL", "GÜÇLÜ AL"]).sum()); sat = int(df["Genel"].isin(["SAT", "GÜÇLÜ SAT"]).sum())
        E.append(kart_izgarasi([("Al görünümünde", str(al), f"%{al / len(df) * 100:.0f}", TS.R["yesil"]),
                                ("Sat görünümünde", str(sat), f"%{sat / len(df) * 100:.0f}", TS.R["kirmizi"]),
                                ("Yukarı kırılım", str(int(df["Kırılım"].sum())), "formasyon / yapı"),
                                ("Ort. teknik puan", f"{df['Teknik puan'].mean():.0f}", "0–100")], W, sutun=4))
        E.append(Spacer(1, 6))
    if len(df):
        _al = int(df["Genel"].isin(["AL", "GÜÇLÜ AL"]).sum()); _sat = int(df["Genel"].isin(["SAT", "GÜÇLÜ SAT"]).sum())
        _et = "OLUMLU" if _al > 1.5 * _sat else "OLUMSUZ" if _sat > 1.5 * _al else "NÖTR"
        _bas = {"OLUMLU": "Geniş tabanlı alım iştahı; teknik görünüm olumlu", "OLUMSUZ": "Satış baskısı geniş tabana yayılmış; temkinli duruş",
                "NÖTR": "Seçici piyasa; teknik sinyaller dengeli"}[_et]
        E.append(TS.ozet_paneli("Piyasa yorumu", _bas, _et, AN.bulten_yorumu(baslik, satirlar, endeks), W)); E.append(Spacer(1, 4))
    if endeks:
        E.append(Paragraph(f"{endeks['ad']} teknik görünümü", ST["h2"])); E.append(gosterge_satiri(endeks, W)); E.append(Spacer(1, 4))
        E.append(TS.ozet_paneli("Endeks görünümü", AN.teknik_baslik(endeks), endeks["etiket"], AN.teknik_ozet(endeks), W))
    K = kategoriler(satirlar)
    for ad, d in K.items():
        v = [["Kod", "Puan", "G / H / A", "Fiyat", "Değ.", "Öne çıkan"]]
        for _, r in d.iterrows():
            g_ = lambda c: r.get(c) if isinstance(r.get(c), str) else ""
            one = (g_("Formasyon +") or g_("Mum +") or g_("Sinyal +")) if r["Teknik puan"] >= 50 else (g_("Formasyon −") or g_("Mum −") or g_("Sinyal −"))
            v.append([r["Kod"], f"{r['Teknik puan']:.0f}", f"{KISA.get(r['Günlük'], '–')} / {KISA.get(r['Haftalık'], '–')} / {KISA.get(r['Aylık'], '–')}", _f(r["Fiyat"]), _yz(r["Değişim"]),
                      Paragraph(TS.esc(str(one or "–"))[:110], ST["hucre"])])
        E.append(KeepTogether([Paragraph(ad, ST["h2"]), TS.tablo(v, [W * .1, W * .08, W * .24, W * .12, W * .1, W * .36], hizala_sol=(0, 5), font=7.0)]))
    if ekler.get("likidite"):
        E.append(KeepTogether([Paragraph("Kripto piyasası likiditesi", ST["h2"]), bilgi_kutusu("Analist yorumu:", ekler["likidite"], W)]))
    if "RS" in df and df["RS"].notna().any():
        g = df.dropna(subset=["RS"]).sort_values("RS", ascending=False).head(15)
        v = [["Kod", "RS puanı", "Teknik puan", "G / H / A", "Değ."]] + [[r_["Kod"], f"{int(r_['RS'])}", f"{r_['Teknik puan']:.0f}",
             f"{KISA.get(r_['Günlük'], '–')} / {KISA.get(r_['Haftalık'], '–')} / {KISA.get(r_['Aylık'], '–')}", _yz(r_["Değişim"])] for _, r_ in g.iterrows()]
        E.append(KeepTogether([Paragraph("Göreli güç liderleri (RS puanı 1–99)", ST["h2"]),
                               Paragraph("RS puanı; 3, 6, 9 ve 12 aylık getirilerin (son çeyrek %40 ağırlıklı) taranan tüm varlıklar içindeki yüzdelik sırasıdır. "
                                         "80 üzeri, piyasanın en güçlü %20'lik dilimini gösterir.", ST["kucuk"]),
                               TS.tablo(v, [W * .18, W * .14, W * .16, W * .34, W * .18], font=7.2)]))
    rr = ekler.get("rrg")
    if rr:
        import bist_ileri as IL
        v = [["Sektör", "Bölge", "Göreli güç", "İvme"]] + [[k_, IL.rrg_bolge(d_["ratio"].iloc[-1], d_["momentum"].iloc[-1]),
             f"{d_['ratio'].iloc[-1]:.1f}".replace(".", ","), f"{d_['momentum'].iloc[-1]:.1f}".replace(".", ",")]
             for k_, d_ in sorted(rr.items(), key=lambda x: -x[1]["ratio"].iloc[-1])]
        lider = [k_ for k_, d_ in rr.items() if IL.rrg_bolge(d_["ratio"].iloc[-1], d_["momentum"].iloc[-1]) == "Lider"]
        topar = [k_ for k_, d_ in rr.items() if IL.rrg_bolge(d_["ratio"].iloc[-1], d_["momentum"].iloc[-1]) == "Toparlanan"]
        yorum = (f"Lider bölgede {', '.join(lider[:5]) or 'sektör yok'}; endekse göre güç kazanmaya başlayan (toparlanan) sektörler: {', '.join(topar[:5]) or 'yok'}. "
                 "Saat yönünde dönüş tipiktir: toparlanan → lider → zayıflayan → geride.")
        E.append(PageBreak()); E.append(Paragraph("Sektör rotasyonu", ST["h2"])); E.append(bilgi_kutusu("Analist yorumu:", yorum, W))
        E.append(Spacer(1, 4)); E.append(_img(IL.g_rrg(rr, "S&P 500" if sym == "$" and baslik.endswith("ABD Borsaları") else "BIST 100"), W * 0.9, 5.2 / 7.5 * 0.9))
        E.append(TS.tablo(v, [W * .4, W * .2, W * .2, W * .2], hizala_sol=(0, 1), font=7.0))
    ac = ekler.get("aciga")
    if ac is not None and len(ac):
        g = ac.dropna(subset=["Oran"]).sort_values("Oran", ascending=False).head(15)
        v = [["Kod", "Açığa satış (mn TL)", "Toplam hacme oranı"]] + [[r_["Kod"], f"{r_['Açığa satış TL'] / 1e6:,.1f}".replace(",", "X").replace(".", ",").replace("X", "."),
             _yz(r_["Oran"], 1)] for _, r_ in g.iterrows()]
        E.append(KeepTogether([Paragraph(f"Açığa satış yoğunluğu ({ekler.get('aciga_donem') or 'son hafta'})", ST["h2"]),
                               Paragraph("Kaynak: Borsa İstanbul haftalık açığa satış bülteni. Oran, açığa satış tutarının aynı haftadaki toplam işlem hacmine bölünmesiyle bulunur.", ST["kucuk"]),
                               TS.tablo(v, [W * .2, W * .3, W * .3], font=7.2)]))
    if analizler:
        E.append(PageBreak()); E.append(Bolum(1, "Öne çıkanların günlük grafikleri", W))
        for s in analizler[:8]:
            a = s["tf"].get("G")
            if not a: continue
            E.append(KeepTogether([_img(g_teknik(a, f"{s['kod']} · {s['ad']} · {s['etiket']} (puan {s['puan']:.0f})", kompakt=True, dpi=120), W, 3.0 / 7.5 * 0.97),
                                   Paragraph(TS.esc(AN.teknik_ozet(s)), ST["kucuk"]), Spacer(1, 6)]))
    # "Tüm liste" bölümü kaldırıldı: tam tablo uygulamanın Teknik sekmesinde (ozet.csv) duruyor
    E.append(Spacer(1, 6))
    E.append(Paragraph("Bu bülten kapanış fiyatlarıyla otomatik üretilmiştir; formasyonlar algoritmik tespit edilir ve hatalı olabilir. "
                       "Gösterge bazlı analizdir, yatırım tavsiyesi değildir. Tüm varlıkların tam listesi uygulamanın Teknik sekmesindedir.", ST["kucuk"]))
    doc.build(E, onFirstPage=sayfa, onLaterPages=sayfa)
    return dosya
