# -*- coding: utf-8 -*-
"""Telegram için görsel kartlar (PNG): fırsat kartı. Koyu tema, telefon ekranına göre (1080 px genişlik)."""
import os, textwrap
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch, Rectangle, Wedge, Circle

_K = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
for f in ("FiraSans-Regular.ttf", "FiraSans-Medium.ttf", "FiraSans-SemiBold.ttf", "FiraSans-Bold.ttf", "FiraSans-Light.ttf"):
    try: fm.fontManager.addfont(os.path.join(_K, f))
    except Exception: pass
FONT = "Fira Sans"

C = {"bg": "#0B1220", "panel": "#111A2E", "panel2": "#16223B", "cizgi": "#22304D", "yazi": "#F1F5F9", "soluk": "#94A3B8",
     "silik": "#64748B", "altin": "#F59E0B", "yesil": "#22C55E", "yesil2": "#16A34A", "kirmizi": "#EF4444", "mavi": "#3B82F6",
     "mor": "#A78BFA", "turkuaz": "#22D3EE"}
W, H = 1080, 1500


def _t(ax, x, y, s, size=20, color=None, weight="regular", ha="left", va="baseline", **kw):
    return ax.text(x, y, s, fontsize=size, color=color or C["yazi"], fontweight=weight, ha=ha, va=va, family=FONT, **kw)


def _kutu(ax, x, y, w, h, renk, r=14, alpha=1.0, kenar=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=renk, ec=kenar or "none", lw=1.5 if kenar else 0,
                                alpha=alpha))


def _fy(x):
    import firsat as F
    return F.fy(x)


def _yz(x):
    s = f"{x * 100:+.1f}".replace(".", ",")
    return ("+%" + s[1:]) if s[0] == "+" else ("−%" + s[1:])


def _halka(ax, cx, cy, r, puan, renk):
    ax.add_patch(Wedge((cx, cy), r, 0, 360, width=r * 0.18, fc=C["cizgi"], ec="none"))
    ax.add_patch(Wedge((cx, cy), r, 90 - 360 * puan / 100, 90, width=r * 0.18, fc=renk, ec="none"))
    _t(ax, cx, cy - 4, f"{puan:.0f}", 40, weight="bold", ha="center", va="center")
    _t(ax, cx, cy - r * 0.55, "PUAN", 12, C["soluk"], ha="center", va="center")


def _grafik(fig, f, a, kutu):
    """Mum grafiği + seviyeler (kutu: figür koordinatlarında [x, y, w, h])."""
    ax = fig.add_axes(kutu); ax.set_facecolor(C["panel"])
    h = a["h"].iloc[-70:]; G = a["G"].iloc[-70:]; p = f["plan"]
    x = np.arange(len(h)); ileri = 12; x0 = len(h) - 1; x1 = x0 + ileri
    for i, (o, hi, lo, c) in enumerate(zip(h["Open"], h["High"], h["Low"], h["Close"])):
        col = C["yesil"] if c >= o else C["kirmizi"]
        ax.vlines(i, lo, hi, color=col, lw=1.1)
        ax.add_patch(Rectangle((i - 0.32, min(o, c)), 0.64, max(abs(c - o), (hi - lo) * 0.02 + 1e-12), color=col, lw=0))
    ax.plot(x, G["EMA20"], color=C["altin"], lw=1.4, alpha=0.9)
    ax.plot(x, G["EMA50"], color=C["mor"], lw=1.4, alpha=0.9)
    g, s = p["giris"], p["stop"]; hd = [z["fiyat"] for z in p["hedef"]]
    ax.add_patch(Rectangle((x0, min(g, s)), ileri, abs(g - s), color=C["kirmizi"], alpha=0.16, lw=0))
    ax.add_patch(Rectangle((x0, min(g, hd[-1])), ileri, abs(hd[-1] - g), color=C["yesil"], alpha=0.10, lw=0))
    for y, renk, et, ls in [(s, C["kirmizi"], "STOP", "-"), (g, C["mavi"], "GİRİŞ", "-")] + [(y, C["yesil"], f"H{i + 1}", "--") for i, y in enumerate(hd)]:
        ax.hlines(y, x0 - 10, x1, color=renk, lw=1.6, ls=ls)
        ax.text(x1 + 0.6, y, f" {et}  {_fy(y)}", color=renk, fontsize=13, va="center", family=FONT, fontweight="bold")
    lo_ = min(h["Low"].min(), s, *hd); hi_ = max(h["High"].max(), s, *hd); pad = (hi_ - lo_) * 0.05
    ax.set_ylim(lo_ - pad, hi_ + pad); ax.set_xlim(-1, x1 + 11)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.tick_params(colors=C["silik"], labelsize=11, length=0)
    ax.grid(color=C["cizgi"], lw=0.6, alpha=0.7)
    adim = max(1, len(h) // 5); fmt = "%d.%m %H:%M" if f["tf"] == "4S" else "%d.%m.%y"
    ax.set_xticks(x[::adim]); ax.set_xticklabels([t.strftime(fmt) for t in h.index[::adim]], family=FONT)
    for lb in ax.get_yticklabels(): lb.set_family(FONT)
    ax.text(0.01, 0.97, "EMA20", transform=ax.transAxes, color=C["altin"], fontsize=11, va="top", family=FONT)
    ax.text(0.09, 0.97, "EMA50", transform=ax.transAxes, color=C["mor"], fontsize=11, va="top", family=FONT)


def firsat_karti(f, a, dosya, piyasa_ad, tf_ad):
    import firsat as F
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100); fig.patch.set_facecolor(C["bg"])
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    yon = f["yon"]; ana = C["yesil"] if yon == 1 else C["kirmizi"]; p = f["plan"]; g = p["giris"]
    # ---- başlık
    ax.add_patch(Rectangle((0, H - 8), W, 8, color=C["altin"]))
    import tg
    _t(ax, 48, H - 70, f"{tg.buyuk(piyasa_ad)}  ·  {tg.buyuk(tf_ad)}  ·  FIRSAT", 15, C["altin"], "semibold")
    _t(ax, 48, H - 140, F.gorunen(f["kod"], None), 54, weight="bold")
    ad = f.get("ad") or ""
    if ad and ad not in f["kod"]: _t(ax, 48, H - 180, textwrap.shorten(ad, 44, placeholder="…"), 19, C["soluk"])
    _kutu(ax, 48, H - 250, 150, 48, ana, r=24)
    _t(ax, 123, H - 234, "AL" if yon == 1 else "SAT", 22, "#FFFFFF", "bold", ha="center")
    _t(ax, 214, H - 234, textwrap.shorten(f["kurulum_ad"], 40, placeholder="…"), 18, C["yazi"], "medium")
    _halka(ax, W - 125, H - 150, 82, f["puan"], ana)
    # ---- grafik
    _grafik(fig, f, a, [0.045, 0.505, 0.90, 0.30])
    # ---- işlem merdiveni
    y0 = 445; _kutu(ax, 40, y0, W - 80, 290, C["panel"])
    _t(ax, 68, y0 + 252, "İŞLEM PLANI", 15, C["altin"], "semibold")
    _t(ax, W - 68, y0 + 252, f"süre: en fazla {F.SURE_AD[f['tf']](F.MAKS_BAR[f['tf']])}", 14, C["soluk"], ha="right")
    satir = [(f"H{i + 1}", z["fiyat"], C["yesil"], f"{F.rr(z['r'])} · " + ("risk katı hedefi" if z["etiket"].endswith("R hedefi") else z["etiket"]))
             for i, z in reversed(list(enumerate(p["hedef"])))]
    satir += [("GİRİŞ", g, C["mavi"], f"bölge {_fy(p['bolge'][0])} – {_fy(p['bolge'][1])}"), ("STOP", p["stop"], C["kirmizi"], "son yapı + ATR payı")]
    for j, (et, fiyat, renk, acik) in enumerate(satir):
        yy = y0 + 210 - j * 40
        ax.add_patch(Rectangle((68, yy - 9), 6, 26, color=renk))
        _t(ax, 90, yy, et, 19, renk, "bold")
        _t(ax, 210, yy, _fy(fiyat), 22, C["yazi"], "bold")
        if et != "GİRİŞ": _t(ax, 400, yy, _yz((fiyat - g) / g), 19, renk, "semibold")
        _t(ax, 520, yy, textwrap.shorten(acik, 46, placeholder="…"), 15, C["soluk"])
    # ---- istatistik kutuları
    vt, pm = f["gecmis"], f["piyasa_gecmis"]
    kutular = [("H1 BAŞARISI", f"%{vt['p1'] * 100:.0f}" if vt.get("n") else "–", f"{vt.get('n', 0)} geçmiş örnek"),
               ("ORT. SONUÇ", F.rrs(vt["ort_R"]) if vt.get("n") else "–", "bu varlıkta"),
               ("PİYASA GENELİ", f"%{pm['p1'] * 100:.0f}" if pm.get("n", 0) >= 20 else "–", f"{pm.get('n', 0):,} örnek".replace(",", ".")),
               ("RİSK / ÖDÜL", f"1 : {p['hedef'][1]['r']:.1f}".replace(".", ","), "H2'ye göre")]
    bw = (W - 80 - 3 * 16) / 4
    for i, (b, d, alt) in enumerate(kutular):
        x = 40 + i * (bw + 16); _kutu(ax, x, 300, bw, 125, C["panel"])
        _t(ax, x + bw / 2, 392, b, 13, C["soluk"], "semibold", ha="center")
        _t(ax, x + bw / 2, 340, d, 30, C["yazi"], "bold", ha="center")
        _t(ax, x + bw / 2, 315, alt, 12, C["silik"], ha="center")
    # ---- teyit rozetleri
    _t(ax, 48, 262, "TEYİTLER", 15, C["altin"], "semibold")
    x, y = 48, 210
    for metin, ok in f["teyit"]:
        w_ = 30 + 11.2 * len(metin)
        if x + w_ > W - 40: x, y = 48, y - 50
        _kutu(ax, x, y, w_, 38, "#0F2A1C" if ok else C["panel2"], r=19, kenar=C["yesil2"] if ok else C["cizgi"])
        _t(ax, x + w_ / 2, y + 12, metin, 15, C["yesil"] if ok else C["silik"], "medium", ha="center")
        x += w_ + 10
    # ---- balina ve riskler
    y = y - 40
    bal = f.get("balina") or []
    canli = (f["ekstra"].get("balina_canli") or "").split("→")[-1].strip()
    canli = canli if canli in ("net alış", "net satış") else ""
    if bal or canli:
        b = ", ".join(dict.fromkeys(x_[0] for x_ in bal[-3:]))
        if canli: b = (b + " · " if b else "") + "canlı büyük işlemler: " + canli
        ax.add_patch(Circle((58, y + 7), 7, color=C["turkuaz"])); _t(ax, 76, y, textwrap.shorten("Balina: " + b, 92, placeholder="…"), 16, C["turkuaz"])
        y -= 34
    for r_ in (f.get("risk") or [])[:2]:
        ax.add_patch(Circle((58, y + 7), 7, color=C["altin"])); _t(ax, 76, y, textwrap.shorten(r_, 92, placeholder="…"), 16, C["altin"])
        y -= 34
    # ---- alt bilgi
    _t(ax, W / 2, 22, "Gösterge bazlı analizdir, yatırım tavsiyesi değildir.", 13, C["silik"], ha="center")
    fig.savefig(dosya, dpi=100, facecolor=C["bg"]); plt.close(fig)
    return dosya


def baslik_metni(f):
    """Kartın altına kısa açıklama (medya kapalıyken de okunabilsin)."""
    import firsat as F
    p = f["plan"]; g = p["giris"]
    h = " · ".join(f"H{i + 1} <b>{F.fy(z['fiyat'])}</b>" for i, z in enumerate(p["hedef"]))
    return (f"{'🟢' if f['yon'] == 1 else '🔴'} <b>{F._e(F.gorunen(f['kod'], f.get('ad')))} · {'AL' if f['yon'] == 1 else 'SAT'}</b> · puan <b>{f['puan']:.0f}</b>\n"
            f"Giriş <b>{F.fy(g)}</b> · Stop <b>{F.fy(p['stop'])}</b> ({F.yz((p['stop'] - g) / g)})\n{h}")
