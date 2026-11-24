# -*- coding: utf-8 -*-
"""Portföy analizi: hisse, kripto ve emtiaları TL bazında birleştirir; dağılım, risk, korelasyon,
beta, riske maruz değer (VaR/CVaR), risk katkısı, getiri ve teknik görünüm. PDF raporu üretir."""
import io, re, math, datetime as dt
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, CondPageBreak, PageBreak, Image

import tasarim as TS
from tasarim import ST, Bolum, bilgi_kutusu, sayfa_cizici

C = TS.GRAFIK


def _y(x, d=1, isaret=True):
    if x is None or (isinstance(x, float) and math.isnan(x)): return "–"
    return (("+" if x > 0 else "-" if x < 0 else "") if isaret else ("-" if x < 0 else "")) + "%" + f"{abs(x) * 100:.{d}f}".replace(".", ",")


def _tl(x):
    return TS._sayi(x, 0) + " TL" if x is not None else "–"


def ayristir(metin):
    """'THYAO 1000', 'BTC/TRY 0,25 @ 2900000', 'GRAMALTIN 50' → [(kod, miktar, maliyet)]"""
    out = []
    for s in metin.splitlines():
        s = s.split("#")[0].strip().upper().replace(",", ".")
        if not s: continue
        m = re.match(r"^(\S+)\s+([\d.]+)(?:\s*@\s*([\d.]+))?$", s)
        if m: out.append((m.group(1), float(m.group(2)), float(m.group(3)) if m.group(3) else None))
    return out


def _seri_tl(kod, fx):
    """Varlığın TL bazında günlük kapanış serisi, türü ve adı."""
    import bist_teknik as T, bist_kripto as KR, bist_varlik as V, bist_veri as bv
    h, tur = T.gunluk_veri(kod)
    c = h["Close"].dropna()
    usd = (tur == "kripto" and KR.coz(kod)[1] == "USDT") or (tur == "emtia" and kod.upper() != "GRAMALTIN")
    if usd: c = (c * fx.reindex(c.index, method="ffill")).dropna()
    if tur == "kripto": ad = KR.kod_yap(*KR.coz(kod))
    elif kod.upper() in V.VARLIKLAR: ad = V.VARLIKLAR[kod.upper()][1]
    else: ad = bv.sirket_adi(kod)
    return c, h, tur, ad


def analiz(kalemler, gun=365):
    import bist_rapor as br, bist_teknik as T
    fx = br.kur_cek()
    endeks = br.endeks_cek()["Close"].dropna()
    seriler, bilgi, hata = {}, [], {}
    for kod, miktar, maliyet in kalemler:
        try:
            c, h, tur, ad = _seri_tl(kod, fx)
            fiyat = float(c.iloc[-1]); deger = fiyat * miktar
            try:
                tk = T.analiz_h(kod, ad, h, "kripto" if tur == "kripto" else tur, "₺")
                tek = (tk["etiket"], tk["puan"])
            except Exception:
                tek = ("–", None)
            seriler[kod] = c
            bilgi.append({"Kod": kod, "Ad": ad, "Tür": {"hisse": "Hisse", "kripto": "Kripto", "emtia": "Emtia", "endeks": "Endeks"}.get(tur, tur),
                          "Miktar": miktar, "Fiyat (TL)": fiyat, "Değer (TL)": deger, "Maliyet": maliyet,
                          "K/Z": (fiyat / maliyet - 1) if maliyet else None, "Teknik": tek[0], "Teknik puan": tek[1]})
        except Exception as ex:
            hata[kod] = str(ex)[:80]
    if not bilgi: raise ValueError("Portföydeki varlıkların hiçbirinin verisi alınamadı: " + "; ".join(f"{k}: {v}" for k, v in hata.items()))
    df = pd.DataFrame(bilgi); toplam = df["Değer (TL)"].sum(); df["Ağırlık"] = df["Değer (TL)"] / toplam
    # Getiriler: iş günlerine hizala (kripto hafta sonu fiyatları cuma kapanışına taşınır)
    P = pd.concat(seriler, axis=1).sort_index()
    P = P[P.index >= P.index[-1] - pd.Timedelta(days=gun + 30)].ffill()
    P = P[P.index.dayofweek < 5].dropna(how="any")
    R = P.pct_change().dropna()
    w = df.set_index("Kod")["Ağırlık"].reindex(R.columns).fillna(0).values
    rp = R.values @ w; rp = pd.Series(rp, index=R.index)
    cov = R.cov().values * 252; sig = float(np.sqrt(w @ cov @ w)); vol_i = np.sqrt(np.diag(cov))
    katki = (w * (cov @ w)) / (sig ** 2) if sig > 0 else np.zeros_like(w)
    e = endeks.reindex(R.index, method="ffill").pct_change().dropna(); j = pd.concat([rp, e], axis=1).dropna()
    beta = float(j.cov().iloc[0, 1] / j.iloc[:, 1].var()) if len(j) > 30 else None
    deger_seri = (1 + rp).cumprod(); dd = float((deger_seri / deger_seri.cummax() - 1).min())
    var95 = float(-np.percentile(rp, 5)); cvar95 = float(-rp[rp <= np.percentile(rp, 5)].mean())
    usd = fx.reindex(deger_seri.index, method="ffill")
    r1 = float(deger_seri.iloc[-1] - 1)
    r_usd = float((deger_seri.iloc[-1] / usd.iloc[-1]) / (deger_seri.iloc[0] / usd.iloc[0]) - 1)
    e_r = float(endeks.reindex(R.index, method="ffill").iloc[-1] / endeks.reindex(R.index, method="ffill").iloc[0] - 1)
    korel = R.corr()
    yuksek = [(a, b, float(korel.loc[a, b])) for i, a in enumerate(korel.columns) for b in korel.columns[i + 1:] if korel.loc[a, b] > 0.75]
    df["Risk katkısı"] = df["Kod"].map(dict(zip(R.columns, katki)))
    df["Volatilite"] = df["Kod"].map(dict(zip(R.columns, vol_i)))
    return {"tablo": df.sort_values("Değer (TL)", ascending=False).reset_index(drop=True), "toplam": toplam, "vol": sig, "beta": beta,
            "var95": var95, "cvar95": cvar95, "var95_tl": var95 * toplam, "max_dd": dd, "getiri": r1, "getiri_usd": r_usd, "endeks_getiri": e_r,
            "cesitlendirme": float((w * vol_i).sum() / sig) if sig > 0 else None, "hhi": float((df["Ağırlık"] ** 2).sum()),
            "korelasyon": korel, "yuksek_korelasyon": yuksek, "deger_seri": deger_seri, "gun": len(R), "hata": hata,
            "tarih": dt.datetime.now(dt.timezone(dt.timedelta(hours=3)))}


def ozet(p):
    t = p["tablo"]; C_ = []
    en = t.iloc[0]
    C_.append(f"Portföyün toplam değeri <b>{_tl(p['toplam'])}</b>; {len(t)} varlıktan oluşuyor ve en büyük pozisyon {en['Kod']} (%{en['Ağırlık'] * 100:.0f}).")
    tur = t.groupby("Tür")["Ağırlık"].sum().sort_values(ascending=False)
    C_.append("Varlık sınıfı dağılımı: " + ", ".join(f"{k} %{v * 100:.0f}" for k, v in tur.items()) + ".")
    C_.append(f"Son {p['gun']} işlem gününde mevcut ağırlıklarla portföy TL bazında {_y(p['getiri'])} (dolar bazında {_y(p['getiri_usd'])}) getiri sağlardı; "
              f"aynı dönemde BIST 100 {_y(p['endeks_getiri'])}.")
    seviye = "düşük" if p["vol"] < 0.2 else "orta" if p["vol"] < 0.35 else "yüksek"
    C_.append(f"Yıllık oynaklık %{p['vol'] * 100:.0f} ile {seviye} risk profiline işaret ediyor"
              + (f"; BIST 100'e göre beta {p['beta']:.2f}".replace(".", ",") if p["beta"] is not None else "") + ".")
    C_.append(f"Tarihsel verilere göre normal piyasa koşullarında bir günde %95 olasılıkla en fazla yaklaşık {_tl(p['var95_tl'])} "
              f"({_y(p['var95'], 1, False)}) kayıp beklenir; en kötü %5'lik günlerde ortalama kayıp {_y(p['cvar95'], 1, False)}.")
    rk = t.sort_values("Risk katkısı", ascending=False).iloc[0]
    if rk["Risk katkısı"] > 0.4:
        C_.append(f"Portföy riskinin yaklaşık %{rk['Risk katkısı'] * 100:.0f} kadarı tek bir varlıktan ({rk['Kod']}) geliyor; yoğunlaşma riski yüksek.")
    else:
        C_.append(f"En yüksek risk katkısı {rk['Kod']} (%{rk['Risk katkısı'] * 100:.0f}); risk dağılımı görece dengeli.")
    if p["cesitlendirme"]:
        C_.append(f"Çeşitlendirme oranı {p['cesitlendirme']:.2f}".replace(".", ",") + (" — varlıklar birbirinin riskini anlamlı ölçüde dengeliyor." if p["cesitlendirme"] > 1.4
                  else " — varlıklar büyük ölçüde birlikte hareket ediyor, çeşitlendirme faydası sınırlı."))
    if p["yuksek_korelasyon"]:
        a, b, k = sorted(p["yuksek_korelasyon"], key=lambda x: -x[2])[0]
        C_.append(f"{a} ile {b} arasındaki korelasyon {k:.2f}".replace(".", ",") + "; bu iki pozisyon pratikte aynı riski taşıyor.")
    tk = t.dropna(subset=["Teknik puan"])
    if len(tk):
        al = int((tk["Teknik puan"] >= 58).sum()); sat = int((tk["Teknik puan"] <= 42).sum())
        C_.append(f"Teknik açıdan {len(tk)} varlığın {al} tanesi al, {sat} tanesi sat görünümünde; ağırlıklı teknik puan "
                  f"{(tk['Teknik puan'] * tk['Ağırlık']).sum() / tk['Ağırlık'].sum():.0f}/100.")
    return " ".join(C_)


def baslik(p):
    seviye = "Düşük riskli" if p["vol"] < 0.2 else "Orta riskli" if p["vol"] < 0.35 else "Yüksek riskli"
    yog = p["tablo"]["Risk katkısı"].max() > 0.4
    return f"{seviye} portföy; " + ("risk tek varlıkta yoğunlaşıyor" if yog else "risk dağılımı dengeli") + \
           ("; dolar bazında değer kazandı" if p["getiri_usd"] > 0 else "; dolar bazında değer kaybetti")


# ------------------------------------------------------------------ grafikler
def _png(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=150, bbox_inches="tight"); plt.close(fig); b.seek(0); return b


def g_agirlik(p):
    t = p["tablo"].sort_values("Ağırlık")
    fig, ax = plt.subplots(figsize=(7.5, 0.32 * len(t) + 0.8))
    y = np.arange(len(t))
    ax.barh(y - 0.18, t["Ağırlık"] * 100, height=0.36, color=C["mavi"], label="Ağırlık %")
    ax.barh(y + 0.18, t["Risk katkısı"] * 100, height=0.36, color=C["tur"], label="Risk katkısı %")
    ax.set_yticks(y); ax.set_yticklabels(t["Kod"], fontsize=7); ax.legend(fontsize=7, frameon=False)
    ax.set_title("Ağırlık ve risk katkısı (%)", loc="left"); ax.grid(axis="x", alpha=0.3)
    return _png(fig)


def g_deger(p):
    s = p["deger_seri"] * 100
    fig, ax = plt.subplots(figsize=(7.5, 2.6))
    ax.plot(s.index, s, color=C["lac"], lw=1.3); ax.axhline(100, color=C["gri"], lw=0.7)
    dd = (s / s.cummax() - 1) * 100
    ax2 = ax.twinx(); ax2.fill_between(dd.index, dd, 0, color=C["kirmizi"], alpha=0.12); ax2.set_ylim(min(dd.min() * 3, -5), 0); ax2.set_yticks([])
    ax.set_title("Mevcut ağırlıklarla portföy değeri (başlangıç = 100) ve düşüşler", loc="left"); ax.grid(alpha=0.25)
    return _png(fig)


def g_korelasyon(p):
    k = p["korelasyon"]
    n = len(k); fig, ax = plt.subplots(figsize=(min(7.5, 0.5 * n + 2), min(6.5, 0.45 * n + 1.8)))
    im = ax.imshow(k.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(n)); ax.set_yticks(range(n)); ax.set_xticklabels(k.columns, rotation=60, fontsize=6.5); ax.set_yticklabels(k.columns, fontsize=6.5)
    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{k.values[i, j]:.1f}".replace(".", ","), ha="center", va="center", fontsize=5.5, color="white" if abs(k.values[i, j]) > 0.6 else "black")
    ax.set_title("Korelasyon matrisi (günlük getiriler)", loc="left"); fig.colorbar(im, fraction=0.04)
    return _png(fig)


# ------------------------------------------------------------------ PDF
def pdf(p, dosya):
    W = A4[0] - 3.0 * cm; t = p["tablo"]
    sayfa = sayfa_cizici("PORTFÖY", "Portföy Analizi", f"{dt.date.today():%d.%m.%Y}", kapak_yuk=4.7 * cm)
    doc = SimpleDocTemplate(dosya, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.6 * cm, bottomMargin=1.4 * cm, title="Portföy Analizi")
    E = TS.pro_kapak("Portföy Analizi", f"{len(t)} varlık  ·  hisse, kripto ve emtia TL bazında", _tl(p["toplam"]), None, W,
                     rozet=f"YILLIK OYNAKLIK %{p['vol'] * 100:.0f}", guncel=f"Hesaplama: {p['tarih']:%d.%m.%Y %H:%M} TSİ · son {p['gun']} işlem günü", fiyat_etiket="toplam değer")
    gor = "NÖTR" if p["vol"] < 0.35 else "TEMKİNLİ"
    E.append(TS.ozet_paneli("Portföy özeti", baslik(p), gor, ozet(p), W, alt_bilgi="Görünüm etiketi risk seviyesini yansıtır; yatırım tavsiyesi değildir."))
    E.append(Paragraph("Temel göstergeler", ST["h2"]))
    E.append(TS.metrik_listesi([("Toplam değer", _tl(p["toplam"])), ("Getiri (TL)", _y(p["getiri"])), ("Getiri ($)", _y(p["getiri_usd"])),
                                ("BIST 100 (aynı dönem)", _y(p["endeks_getiri"])), ("Yıllık oynaklık", _y(p["vol"], 0, False)),
                                ("Beta (BIST 100)", f"{p['beta']:.2f}".replace(".", ",") if p["beta"] is not None else "–"),
                                ("Günlük VaR %95", f"{_tl(p['var95_tl'])} ({_y(p['var95'], 1, False)})"), ("CVaR %95", _y(p["cvar95"], 1, False)),
                                ("En büyük düşüş", _y(p["max_dd"])), ("Çeşitlendirme oranı", f"{p['cesitlendirme']:.2f}".replace(".", ",") if p["cesitlendirme"] else "–")], W))
    E += [Spacer(1, 6), Image(g_deger(p), width=W, height=W * 2.6 / 7.5)]
    E.append(PageBreak()); E.append(Bolum(1, "Pozisyonlar", W))
    v = [["Kod", "Tür", "Değer (TL)", "Ağırlık", "Risk katkısı", "Volatilite", "K/Z", "Teknik"]]
    for _, r in t.iterrows():
        v.append([r["Kod"], r["Tür"], TS._sayi(r["Değer (TL)"], 0), _y(r["Ağırlık"], 0, False), _y(r["Risk katkısı"], 0, False),
                  _y(r["Volatilite"], 0, False), _y(r["K/Z"]) if r["K/Z"] is not None and not pd.isna(r["K/Z"]) else "–",
                  f"{r['Teknik']} ({r['Teknik puan']:.0f})" if r["Teknik puan"] is not None and not pd.isna(r["Teknik puan"]) else "–"])
    E.append(TS.tablo(v, [W * .16, W * .09, W * .15, W * .09, W * .11, W * .1, W * .1, W * .2], font=7.2))
    E += [Spacer(1, 6), Image(g_agirlik(p), width=W, height=W * (0.32 * len(t) + 0.8) / 7.5)]
    E.append(CondPageBreak(10 * cm)); E.append(Bolum(2, "Korelasyon ve çeşitlendirme", W))
    E.append(bilgi_kutusu("Bu ne demek?", "Korelasyon +1'e yakın olan varlıklar birlikte yükselip düşer; böyle iki pozisyon tek bir büyük pozisyon gibi risk taşır. "
                          "Çeşitlendirme oranı 1'in ne kadar üzerindeyse varlıklar birbirinin riskini o kadar dengeler.", W, "turkuaz"))
    kk = p["korelasyon"]; n = len(kk)
    E.append(Image(g_korelasyon(p), width=min(W, (0.5 * n + 2) / 7.5 * W), height=min(W, (0.5 * n + 2) / 7.5 * W) * min(6.5, 0.45 * n + 1.8) / min(7.5, 0.5 * n + 2)))
    if p["hata"]:
        E.append(Paragraph("Verisi alınamayanlar: " + ", ".join(p["hata"]), ST["kucuk"]))
    E.append(Spacer(1, 6))
    E.append(Paragraph("VaR (riske maruz değer): tarihsel günlük getirilere göre %95 güvenle bir günde aşılmaması beklenen kayıp. CVaR: en kötü %5'lik günlerin ortalama kaybı. "
                       "Risk katkısı: portföy oynaklığının her pozisyondan gelen payı. Hesaplar mevcut ağırlıkların geçmişe uygulanmasıyla yapılır; "
                       "bu rapor yatırım tavsiyesi değildir.", ST["kucuk"]))
    doc.build(E, onFirstPage=sayfa, onLaterPages=sayfa)
    return dosya
