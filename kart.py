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

# Uygulamayla aynı kimlik: siyah/antrasit zemin, altın vurgu, neon yeşil–kırmızı
C = {"bg": "#0B0B0C", "panel": "#17181B", "panel2": "#1E1F23", "cizgi": "#2A2B30", "yazi": "#F4F4F5", "soluk": "#A1A1AA",
     "silik": "#71717A", "altin": "#E8B84A", "yesil": "#22C55E", "yesil2": "#16A34A", "kirmizi": "#EF4444", "mavi": "#F5D27A",
     "mor": "#C4B5FD", "turkuaz": "#E8B84A"}
W, H = 1080, 1500


def _t(ax, x, y, s, size=20, color=None, weight="regular", ha="left", va="baseline", **kw):
    return ax.text(x, y, s, fontsize=size, color=color or C["yazi"], fontweight=weight, ha=ha, va=va, family=FONT, **kw)


_LOGO_IMG = None


_HERO_IMG = None


def _hero():
    """Uygulamadaki boğa–ayı görselinin karta uygun, aşağı doğru solan soluk hali."""
    global _HERO_IMG
    if _HERO_IMG is None:
        try:
            from PIL import Image
            im = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "varlik", "hero.jpg")).convert("RGB")
            a_ = np.asarray(im).astype(float) / 255.0
            h_ = a_.shape[0]; t = np.linspace(0, 1, h_)[:, None]
            alfa = (0.40 * (1 - t) ** 1.3)
            _HERO_IMG = np.dstack([a_, np.repeat(alfa, a_.shape[1], axis=1)])
        except Exception:
            _HERO_IMG = False
    return _HERO_IMG if _HERO_IMG is not False else None


def _marka(ax, H, x=48, boy=36):
    """Sol üst köşeye KATKAY logosu (bütün Telegram kartlarında ortak)."""
    global _LOGO_IMG
    try:
        if _LOGO_IMG is None:
            import matplotlib.image as mpimg, os
            _LOGO_IMG = mpimg.imread(os.path.join(os.path.dirname(os.path.abspath(__file__)), "varlik", "logo.png"))
        xl, yl = ax.get_xlim(), ax.get_ylim()
        ax.imshow(_LOGO_IMG, extent=[x, x + boy, H - 86, H - 86 + boy], aspect="auto", zorder=5, interpolation="lanczos")
        ax.set_xlim(*xl); ax.set_ylim(*yl)
        return x + boy + 12
    except Exception:
        return x


UYG_ADRES = "erhankatkay-glitch.github.io/bist-rapor"


def ust_bant(ax, H, ust, sag=None, vurgu=None):
    """Uygulamayla aynı üst bant: logo + KATKAY YATIRIM yazısı, altında kartın türü (altın, aralıklı büyük harf), sağda tarih.
    Eski 'altın şerit + logo + başlık' düzeninin yerini alır; aynı yükseklikte (H−38 … H−84) kalır."""
    import datetime as _dt
    vurgu = vurgu or C["altin"]
    x = _marka(ax, H, boy=44)
    t1 = _t(ax, x, H - 56, "KATKAY", 19, C["yazi"], "bold")
    _t(ax, _sag_kenar(ax, t1) + 6, H - 56, "YATIRIM", 19, C["altin"], "bold")
    _t(ax, x, H - 82, " ".join(str(ust).split()).replace(" · ", "  ·  "), 13.5, vurgu, "semibold")
    import re as _re
    m_ = _re.search(r"\s*·?\s*(\d{2}\.\d{2}\.\d{4})\s*$", str(ust))
    if m_ and sag is None: ust, sag = str(ust)[:m_.start()], m_.group(1)   # tarih başlıkta tekrar etmesin: sağa
    if sag is None:
        sag = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=3))).strftime("%d.%m.%Y · %H:%M TSİ")
    if sag: _t(ax, W - 48, H - 56, sag, 14, C["soluk"], ha="right")
    ax.add_patch(Rectangle((48, H - 100), W - 96, 1.2, color=C["cizgi"]))


def _sag_kenar(ax, t):
    """Yazının sağ kenarı (veri koordinatında) — iki renkli yazı ve başlık çizgisi için."""
    try:
        r = ax.figure.canvas.get_renderer()
        return ax.transData.inverted().transform(t.get_window_extent(renderer=r))[1][0]
    except Exception:
        return t.get_position()[0] + len(t.get_text()) * t.get_fontsize() * 0.6


def bolum_baslik(ax, x, y, metin, renk=None, x2=None, boy=17):
    """Uygulamadaki bölüm başlığı: aralıklı büyük harf + sağa doğru solan altın çizgi. renk verilirse başa renkli nokta."""
    x2 = x2 or W - 40
    if renk and renk != C["altin"]:
        ax.add_patch(Circle((x + 7, y + 7), 7, color=renk)); x += 22
    m = " ".join(str(metin).replace("i", "İ").replace("ı", "I").upper())
    bas = _sag_kenar(ax, _t(ax, x, y, m, boy * 0.78, C["yazi"], "bold")) + 14
    n = 24
    for i in range(n):   # altın → saydam degrade çizgi
        a0 = bas + (x2 - bas) * i / n
        ax.add_patch(Rectangle((a0, y + 6), (x2 - bas) / n + 0.5, 1.6, color=C["altin"], alpha=0.75 * (1 - i / n), lw=0))


def alt_bant(ax, y=18):
    """Ortak alt bilgi: uygulama adresi + yasal not."""
    _t(ax, W / 2, y + 26, "Tüm analizler ve canlı fiyatlar: " + UYG_ADRES, 14, C["altin"], "semibold", ha="center")
    _t(ax, W / 2, y, "KATKAY YATIRIM A.Ş. · Gösterge bazlı analizdir, yatırım tavsiyesi değildir.", 12.5, C["silik"], ha="center")


_LOGO_ON = {}


def logo_ciz(ax, kod, x, y_alt, boy, piyasa="kripto"):
    """Varlık logosu (kripto: yerel set, hisse: logo.dev) — (x, y_alt) sol alt köşe, boy piksel. Çizildiyse True."""
    try:
        import logolar, matplotlib.image as mpimg
        yol = logolar.logo_dosya(kod, piyasa)
        if not yol: return False
        if yol not in _LOGO_ON: _LOGO_ON[yol] = mpimg.imread(yol)
        xl, yl = ax.get_xlim(), ax.get_ylim()
        ax.imshow(_LOGO_ON[yol], extent=[x, x + boy, y_alt, y_alt + boy], aspect="auto", zorder=6, interpolation="lanczos")
        ax.set_xlim(*xl); ax.set_ylim(*yl)
        return True
    except Exception:
        return False


def _kutu(ax, x, y, w, h, renk, r=14, alpha=1.0, kenar=None):
    if kenar is None and renk in (C["panel"], C["panel2"]): kenar = C["cizgi"]   # uygulamadaki gibi ince çerçeve
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
    # teyit rozetlerinin kaç satır tutacağı (yeni teyitlerle 3 satıra çıkabilir) → kart buna göre uzar
    sat_, x_ = 1, 48
    for metin, _ in f["teyit"]:
        w_ = 30 + 11.2 * len(metin)
        if x_ + w_ > W - 40: sat_, x_ = sat_ + 1, 48
        x_ += w_ + 10
    ek = 50 * max(0, sat_ - 2)
    H = 1730 + ek; OF = 190 + ek   # alttaki "Basitçe" kutusu ve teyit satırları için ek alan
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100); fig.patch.set_facecolor(C["bg"])
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    yon = f["yon"]; ana = C["yesil"] if yon == 1 else C["kirmizi"]; p = f["plan"]; g = p["giris"]
    # ---- başlık
    import tg
    ust_bant(ax, H, f"{tg.buyuk(piyasa_ad)} · {tg.buyuk(tf_ad)} · FIRSAT")
    bx = 48
    if f.get("piyasa") in ("kripto", "bist", "abd") and logo_ciz(ax, f["kod"], 48, H - 187, 64, f["piyasa"]): bx = 128
    _t(ax, bx, H - 175, F.gorunen(f["kod"], None), 54, weight="bold")
    ad = f.get("ad") or ""
    if ad and ad not in f["kod"]: _t(ax, bx, H - 215, textwrap.shorten(ad, 44, placeholder="…"), 19, C["soluk"])
    _kutu(ax, 48, H - 285, 150, 48, ana, r=24)
    _t(ax, 123, H - 269, "AL" if yon == 1 else "SAT", 22, "#FFFFFF", "bold", ha="center")
    ku = f["kurulum_ad"]
    _t(ax, 214, H - 269, textwrap.shorten(ku, 40 if len(ku) <= 40 else 54, placeholder="…"), 18 if len(ku) <= 40 else 15, C["yazi"], "medium")
    _halka(ax, W - 125, H - 200, 82, f["puan"], ana)
    # ---- grafik
    _grafik(fig, f, a, [0.045, (757 + OF) / H, 0.90, 450 / H])
    # ---- işlem merdiveni
    y0 = 445 + OF; _kutu(ax, 40, y0, W - 80, 290, C["panel"])
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
        x = 40 + i * (bw + 16); _kutu(ax, x, 300 + OF, bw, 125, C["panel"])
        _t(ax, x + bw / 2, 392 + OF, b, 13, C["soluk"], "semibold", ha="center")
        _t(ax, x + bw / 2, 340 + OF, d, 30, C["yazi"], "bold", ha="center")
        _t(ax, x + bw / 2, 315 + OF, alt, 12, C["silik"], ha="center")
    # ---- teyit rozetleri
    bolum_baslik(ax, 48, 262 + OF, "Teyitler")
    x, y = 48, 210 + OF
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
    # ---- basitçe (bilmeyenin anlayacağı dil)
    _kutu(ax, 40, 70, W - 80, 172, C["panel2"], kenar=C["altin"])
    _t(ax, 68, 212, "BASİTÇE", 14, C["altin"], "semibold")
    for i_, sat_ in enumerate(textwrap.wrap(basitce(f), 82)[:4]):
        _t(ax, 68, 180 - i_ * 28, sat_, 17, C["yazi"])
    # ---- alt bilgi
    alt_bant(ax, 14)
    fig.savefig(dosya, dpi=100, facecolor=C["bg"]); plt.close(fig)
    return dosya


def basitce(f):
    """Teknik bilgisi olmayan biri için tek paragraflık işlem anlatımı."""
    p = f["plan"]; g, st = p["giris"], p["stop"]; h1, h2 = p["hedef"][0]["fiyat"], p["hedef"][1]["fiyat"]
    yz_ = lambda x: f"%{abs(x) * 100:.1f}".replace(".", ",")
    risk, k1, k2 = yz_(st / g - 1), yz_(h1 / g - 1), yz_(h2 / g - 1)
    if f["yon"] == 1:
        return (f"{_fy(g)} civarından alım düşünülebilir. Fiyat {_fy(st)} seviyesinin altına inerse işlem geçersiz sayılır ve zarar "
                f"kesilir (yaklaşık {risk}). Fiyat {_fy(h1)} seviyesine ulaşırsa ({k1}) pozisyonun yarısı satılarak kâr alınır ve "
                f"stop alış fiyatına çekilir; böylece kalan kısım zarar riski olmadan taşınır. Sonraki hedef {_fy(h2)} ({k2}).")
    return (f"Fiyatın düşmesi beklenir (vadeli işlemde açığa satış). {_fy(g)} civarından satış pozisyonu düşünülebilir. Fiyat {_fy(st)} "
            f"seviyesinin üzerine çıkarsa işlem kapatılır (yaklaşık {risk} zarar). Fiyat {_fy(h1)} seviyesine inerse ({k1}) "
            f"pozisyonun yarısı kapatılarak kâr alınır ve stop giriş fiyatına çekilir. Sonraki hedef {_fy(h2)} ({k2}).")


def baslik_metni(f):
    """Kartın altına kısa açıklama (medya kapalıyken de okunabilsin)."""
    import firsat as F
    p = f["plan"]; g = p["giris"]
    h = " · ".join(f"H{i + 1} <b>{F.fy(z['fiyat'])}</b>" for i, z in enumerate(p["hedef"]))
    return (f"{'🟢' if f['yon'] == 1 else '🔴'} <b>{F._e(F.gorunen(f['kod'], f.get('ad')))} · {'AL' if f['yon'] == 1 else 'SAT'}</b> · puan <b>{f['puan']:.0f}</b>\n"
            f"Giriş <b>{F.fy(g)}</b> · Stop <b>{F.fy(p['stop'])}</b> ({F.yz((p['stop'] - g) / g)})\n{h}")


# ================================================================== KAPANIŞ BÜLTENİ KARTI
ETIKET_RENK = {"GÜÇLÜ AL": "#16A34A", "AL": "#4ADE80", "NÖTR": "#64748B", "SAT": "#F87171", "GÜÇLÜ SAT": "#DC2626"}


def _kod(k):
    k = str(k)
    return k[:-3] if k.endswith(".US") else k.replace("/USDT", "").replace("/TRY", "").replace("@OKX", "")


def piyasa_yorumu(df, meta):
    """Bilmeyenin de anlayacağı 2–3 cümlelik günün özeti."""
    n = len(df); E = meta.get("endeks") or {}
    if "Değişim" in df: df = df[df["Değişim"].abs() <= 0.6]
    yuk = int((df["Değişim"] > 0).sum()) if "Değişim" in df else 0; dus = int((df["Değişim"] < 0).sum()) if "Değişim" in df else 0
    al = int(df["Genel"].isin(["AL", "GÜÇLÜ AL"]).sum()); sat = int(df["Genel"].isin(["SAT", "GÜÇLÜ SAT"]).sum())
    if E.get("puan") is not None:
        p = E["puan"]
        ton = ("alıcılar güçlü" if p >= 70 else "alıcılar önde" if p >= 58 else "kararsız bir görünüm hâkim" if p > 42 else "satıcılar önde" if p > 30 else "satıcılar güçlü")
        c1 = f"{E['ad']} teknik puanı {p:.0f}/100: {ton}."
    else:
        c1 = ""
    c2 = (f"Bugün {n} varlıktan {yuk} tanesi yükseldi, {dus} tanesi düştü" if n else "") + (
        f"; teknik görünümü AL olanların oranı %{al / n * 100:.0f}, SAT olanların %{sat / n * 100:.0f}." if n else "")
    k = int(df["Kırılım"].sum()) if "Kırılım" in df else 0; k2 = int(df["Kırılım −"].sum()) if "Kırılım −" in df else 0
    c3 = (f"{k} yukarı ve {k2} aşağı kırılım var; " if k or k2 else "") + (
        "yukarı kırılımların fazlası alıcıların toparlandığına işaret ediyor." if k > k2 * 1.3 else
        "aşağı kırılımların fazlası satış baskısının sürdüğünü gösteriyor." if k2 > k * 1.3 else "iki taraf dengede.")
    return " ".join(x for x in (c1, c2, c3) if x)


def bulten_karti(meta, satir, dosya, piyasa_ad):
    import pandas as pd, tg
    df = pd.DataFrame(satir)
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100); fig.patch.set_facecolor(C["bg"])
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    ust_bant(ax, H, f"{tg.buyuk(piyasa_ad)} · KAPANIŞ ÖZETİ", sag="")
    import datetime as _dt
    try: tarih = _dt.date.fromisoformat(str(meta["kapanis"])[:10]).strftime("%d.%m.%Y")
    except Exception: tarih = str(meta["kapanis"])
    _t(ax, W - 48, H - 58, tarih, 15, C["soluk"], ha="right")
    E = meta.get("endeks") or {}
    # --- endeks paneli
    _kutu(ax, 40, H - 330, W - 80, 230, C["panel"])
    _t(ax, 72, H - 150, E.get("ad", ""), 22, C["soluk"], "medium")
    if E.get("fiyat"):
        _t(ax, 72, H - 225, _fy(E["fiyat"]), 58, weight="bold")
        if E.get("degisim") is not None:
            d = E["degisim"]; _t(ax, 72, H - 280, _yz(d) + "  bugün", 24, C["yesil"] if d >= 0 else C["kirmizi"], "semibold")
    if E.get("puan") is not None:
        renk = ETIKET_RENK.get(E.get("etiket"), C["altin"])
        _halka(ax, W - 170, H - 215, 88, E["puan"], renk)
        _t(ax, W - 170, H - 322, E.get("etiket", ""), 17, renk, "bold", ha="center")
    # --- piyasa genişliği
    n = len(df); y0 = H - 470
    bolum_baslik(ax, 48, y0 + 105, "Piyasa genişliği", x2=W - 190)
    _t(ax, W - 48, y0 + 105, f"{n:,} varlık".replace(",", "."), 15, C["soluk"], ha="right")
    if n:
        x = 48; ws = W - 96
        for et in ("GÜÇLÜ AL", "AL", "NÖTR", "SAT", "GÜÇLÜ SAT"):
            k = int((df["Genel"] == et).sum()); w_ = ws * k / n
            if w_ > 0:
                ax.add_patch(Rectangle((x, y0 + 40), w_, 34, color=ETIKET_RENK[et]))
                if w_ > 70: _t(ax, x + w_ / 2, y0 + 50, f"%{k / n * 100:.0f}", 15, "#FFFFFF", "bold", ha="center")
            x += w_
        xs = 48
        for et in ("GÜÇLÜ AL", "AL", "NÖTR", "SAT", "GÜÇLÜ SAT"):
            ax.add_patch(Rectangle((xs, y0 + 8), 14, 14, color=ETIKET_RENK[et])); _t(ax, xs + 22, y0 + 9, et.title().replace("Güçlü", "Güçlü"), 13, C["soluk"])
            xs += 190
    # --- günün özeti
    yor = piyasa_yorumu(df, meta)
    y1 = y0 - 190; _kutu(ax, 40, y1, W - 80, 170, C["panel2"], kenar=C["altin"])
    _t(ax, 68, y1 + 135, "GÜNÜN ÖZETİ", 14, C["altin"], "semibold")
    for i, sat_ in enumerate(textwrap.wrap(yor, 78)[:4]):
        _t(ax, 68, y1 + 100 - i * 30, sat_, 18, C["yazi"])
    # --- en güçlüler & günün en çok yükselen/düşenleri
    y2 = y1 - 40
    lp = {"BIST": "bist", "ABD": "abd", "KRİPTO": "kripto", "KRIPTO": "kripto"}.get(str(piyasa_ad).upper().replace("İ", "I").replace("I", "I"), None)
    lp = lp or {"bist": "bist", "abd": "abd", "kripto": "kripto"}.get(str(meta.get("piyasa", "")).replace("kripto_tl", "kripto"))

    def lg_(kod, x, y, boy=28):   # varlık logosu çizildiyse yazının kayacağı x
        if not lp: return x
        logo_ciz(ax, kod, x, y - 6, boy, lp)
        return x + boy + 8   # logosu olmayan da aynı hizada başlasın
    bolum_baslik(ax, 48, y2, "En güçlü görünüm", x2=540, boy=15)
    bolum_baslik(ax, 580, y2, "Günün hareketlileri", x2=W - 40, boy=15)
    top = df.nlargest(5, "Teknik puan") if n else df
    for i, (_, r) in enumerate(top.iterrows()):
        yy = y2 - 50 - i * 46
        _t(ax, lg_(r["Kod"], 48, yy), yy, _kod(r["Kod"]), 20, weight="bold")
        ax.add_patch(Rectangle((210, yy - 2), 260, 18, color=C["cizgi"]))
        ax.add_patch(Rectangle((210, yy - 2), 260 * r["Teknik puan"] / 100, 18, color=C["yesil"]))
        _t(ax, 485, yy, f"{r['Teknik puan']:.0f}", 18, C["yesil"], "bold")
    if n and "Değişim" in df:
        g = df.dropna(subset=["Değişim"])
        # Veri hatası / bölünme-bedelsiz düzeltmesi kaynaklı uç değerleri ele (BIST günlük limit ±%10, yeni arzlarda ±%20)
        g = g[g["Değişim"].abs() <= (0.205 if piyasa_ad == "BIST" else 0.6)]
        hk = list(g.nlargest(3, "Değişim").itertuples()) + list(g.nsmallest(2, "Değişim").itertuples())
        for i, r in enumerate(hk):
            yy = y2 - 50 - i * 46
            _t(ax, lg_(r.Kod, 580, yy), yy, _kod(r.Kod), 20, weight="bold")
            _t(ax, W - 48, yy, _yz(r.Değişim), 20, C["yesil"] if r.Değişim >= 0 else C["kirmizi"], "bold", ha="right")
    # --- sinyal rozetleri
    y3 = y2 - 300
    def satir_(baslik, kodlar, renk, y):
        _t(ax, 48, y, baslik, 15, renk, "semibold")
        x = 48; y_ = y - 50
        for k in kodlar[:8]:
            m = _kod(k); w_ = 28 + 13 * len(m) + (26 if lp else 0)
            if x + w_ > W - 40: break
            _kutu(ax, x, y_, w_, 36, C["panel2"], r=18, kenar=renk)
            logolu = bool(lp) and logo_ciz(ax, k, x + 9, y_ + 7, 22, lp)
            bas_ = x + 35 if logolu else x
            _t(ax, bas_ + (x + w_ - bas_) / 2 - (4 if logolu else 0), y_ + 11, m, 16, renk, "semibold", ha="center")
            x += w_ + 10
        return y - 95
    if n:
        dg = df["Değişim"].fillna(0) if "Değişim" in df else pd.Series(0, index=df.index)
        # çelişkili görünmesin: yukarı kırılımlar günü artıda, aşağı kırılımlar ekside kapatanlardan seçilir
        k = df[df["Kırılım"] & (dg >= 0)].nlargest(8, "Teknik puan")["Kod"].tolist() if "Kırılım" in df else []
        if k: y3 = satir_("YUKARI KIRILIMLAR", k, C["yesil"], y3)
        if "Balina" in df:
            b = df["Balina"].fillna("").astype(str)
            k = df[b.str.contains("alımı|birikim|Alım emilimi")].nlargest(8, "Teknik puan")["Kod"].tolist()
            if k: y3 = satir_("BALİNA ALIMI / BİRİKİM", k, C["turkuaz"], y3)
        k = df[df["Kırılım −"] & (dg <= 0)].nsmallest(8, "Teknik puan")["Kod"].tolist() if "Kırılım −" in df else []
        if k and y3 > 140: y3 = satir_("AŞAĞI KIRILIMLAR", k, C["kirmizi"], y3)
        k = df[df["RSI"] < 30].nsmallest(8, "RSI")["Kod"].tolist() if "RSI" in df else []
        if k and y3 > 140: y3 = satir_("AŞIRI SATIM (TEPKİ ADAYI)", k, C["altin"], y3)
    alt_bant(ax, 16)
    fig.savefig(dosya, dpi=100, facecolor=C["bg"]); plt.close(fig)
    return dosya


# ================================================================== GENEL BİLDİRİM KARTI
def _sar(s, n):
    return textwrap.wrap(str(s), n) or [""]


def bildirim_karti(ust, baslik, alt, bolumler, dosya, vurgu=None, not_=None):
    """Bildirimler için ortak tasarım (uygulamayla aynı: üst bant, aralıklı bölüm başlıkları, ince çerçeveli kartlar, alt bilgi).
    bolumler: [{"baslik", "renk", "aciklama"(ops.), "izgara"(ops.: satırlar 3'lü kutucuk), "satirlar": [
    {"sol", "sag"(ops.), "sag_renk"(ops.), "nokta"(renk, ops.), "logo"((kod, piyasa), ops.), "alt"(ops.)}]}]. Yükseklik içeriğe göre ayarlanır."""
    vurgu = vurgu or C["altin"]
    IZ_H, IZ_S = 112, 3          # ızgara kutucuk yüksekliği, sütun sayısı
    # --- yükseklik hesabı (çizimle birebir aynı ölçüler)
    ust_y = 250; h = ust_y
    for b in bolumler:
        h += 50
        if b.get("aciklama"): h += 30 * len(_sar(b["aciklama"], 70)[:3]) + 10
        if b.get("izgara"):
            h += ((len(b["satirlar"]) + IZ_S - 1) // IZ_S) * (IZ_H + 12)
        else:
            for s in b["satirlar"]:
                h += 44 + 26 * (len(_sar(s.get("alt", ""), 80)[:4]) if s.get("alt") else 0) + 14
        h += 20
    if not_: h += 30 * len(_sar(not_, 82)[:4]) + 30
    H_ = int(h + 100)
    fig = plt.figure(figsize=(W / 100, H_ / 100), dpi=100); fig.patch.set_facecolor(C["bg"])
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H_); ax.axis("off")
    ust_bant(ax, H_, ust, vurgu=vurgu)
    _t(ax, 48, H_ - 160, baslik, 40, weight="bold")
    if alt: _t(ax, 48, H_ - 200, alt, 18, C["soluk"])
    y = H_ - ust_y
    for b in bolumler:
        renk = b.get("renk") or vurgu
        bolum_baslik(ax, 44, y, b["baslik"], renk if renk != vurgu else None)
        y -= 50
        if b.get("aciklama"):
            for sat in _sar(b["aciklama"], 70)[:3]:
                _t(ax, 48, y, sat, 18, C["yazi"], style="italic"); y -= 30
            y -= 10
        if b.get("izgara"):
            kw = (W - 80 - (IZ_S - 1) * 12) / IZ_S
            for i, s in enumerate(b["satirlar"]):
                sx = 40 + (i % IZ_S) * (kw + 12); sy = y - (i // IZ_S) * (IZ_H + 12) - IZ_H + 30
                _kutu(ax, sx, sy, kw, IZ_H, C["panel"], r=14)
                _t(ax, sx + 16, sy + IZ_H - 30, textwrap.shorten(str(s["sol"]), 20, placeholder="…"), 15, C["soluk"], "semibold")
                _t(ax, sx + 16, sy + IZ_H - 66, str(s.get("sag", "")), 23, s.get("sag_renk") or C["yazi"], "bold")
                if s.get("alt"): _t(ax, sx + 16, sy + 16, textwrap.shorten(str(s["alt"]), 26, placeholder="…"), 12.5, C["silik"])
            y -= ((len(b["satirlar"]) + IZ_S - 1) // IZ_S) * (IZ_H + 12)
        else:
            for s in b["satirlar"]:
                alt_s = _sar(s.get("alt", ""), 80)[:4] if s.get("alt") else []
                kh = 44 + 26 * len(alt_s)
                _kutu(ax, 40, y - kh + 30, W - 80, kh, C["panel"], r=14)
                lg = False
                if s.get("logo"):
                    kod_, pz_ = s["logo"] if isinstance(s["logo"], (tuple, list)) else (s["logo"], None)
                    import logolar as _LG
                    pz_ = pz_ or _LG.tahmin_piyasa(kod_)
                    lg = bool(pz_) and logo_ciz(ax, kod_, 50, y - 7, 32, pz_)
                if not lg and s.get("nokta"): ax.add_patch(Circle((66, y + 8), 8, color=s["nokta"]))
                if lg and s.get("nokta"):   # logonun köşesinde yön rozeti
                    ax.add_patch(Circle((80, y - 4), 7.5, color=C["panel"])); ax.add_patch(Circle((80, y - 4), 5.5, color=s["nokta"]))
                _t(ax, 92 if lg else 86 if s.get("nokta") else 62, y, textwrap.shorten(str(s["sol"]), 52, placeholder="…"), 20, weight="bold")
                if s.get("sag"): _t(ax, W - 62, y, str(s["sag"]), 20, s.get("sag_renk") or C["yazi"], "bold", ha="right")
                yy = y - 30
                for sat in alt_s:
                    _t(ax, 86 if s.get("nokta") else 62, yy, sat, 15.5, C["soluk"]); yy -= 26
                y -= kh + 14
        y -= 20
    if not_:
        nl = _sar(not_, 82)[:4]
        _kutu(ax, 40, y - 30 * len(nl) - 10, W - 80, 30 * len(nl) + 40, C["panel2"], kenar=C["cizgi"])
        yy = y - 4
        for sat in nl:
            _t(ax, 62, yy, sat, 15.5, C["soluk"]); yy -= 30
    alt_bant(ax, 16)
    fig.savefig(dosya, dpi=100, facecolor=C["bg"]); plt.close(fig)
    return dosya
