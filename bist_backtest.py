# -*- coding: utf-8 -*-
"""Skorun geçmiş testi (backtest).

Sağlık skorunun geçmişe uygulanabilen sadeleştirilmiş hâli ("temel faktör skoru") her çeyrek sonu +60 gün
(finansalların açıklanmış olduğu tarih) itibarıyla hesaplanır; hisseler üç gruba ayrılır ve sonraki 3 aylık
getiriler karşılaştırılır. Faktörler: ROE, reel olmayan hasılat büyümesi (TTM), kâr verimi (E/P),
defter değeri/piyasa değeri (B/P) ve 6 aylık momentum.

Sınırlamalar: hayatta kalma yanlılığı (bugün listede olan hisseler), kısa örneklem, işlem maliyetleri yok."""
import json, datetime as dt
import numpy as np
import pandas as pd

FAKTORLER = ["ROE", "Büyüme", "E/P", "B/P", "Momentum"]


def _satir(df, *adlar):
    for a in adlar:
        if isinstance(df, pd.DataFrame) and a in df.index:
            s = pd.to_numeric(df.loc[a], errors="coerce")
            s.index = pd.to_datetime(s.index)
            return s.sort_index()
    return None


def _fiyat(px, t):
    s = px[px.index <= t]
    return float(s.iloc[-1]) if len(s) else None


def gozlemler(kod, fin, px, tarihler, ileri_gun=91, gecikme=60):
    """Bir hisse için her yeniden dengeleme tarihindeki faktör değerleri ve ileri getiri."""
    qg, qb = fin.get("q_gelir"), fin.get("q_bilanco")
    net = _satir(qg, "Net Income Common Stockholders", "Net Income")
    ciro = _satir(qg, "Total Revenue")
    ozk = _satir(qb, "Stockholders Equity")
    hisse = _satir(qb, "Ordinary Shares Number")
    out = []
    for q in tarihler:
        t = q + pd.Timedelta(days=gecikme)
        rec = {"kod": kod, "ceyrek": q, "tarih": t}
        if net is not None:
            n_ = net[net.index <= q].dropna()
            if len(n_) >= 4:
                ttm = n_.iloc[-4:].sum(); rec["_net"] = ttm
                if ozk is not None:
                    e_ = ozk[ozk.index <= q].dropna()
                    if len(e_) and e_.iloc[-1] > 0:
                        rec["ROE"] = ttm / e_.iloc[-1]; rec["_ozk"] = e_.iloc[-1]
        if ciro is not None:
            c_ = ciro[ciro.index <= q].dropna()
            if len(c_) >= 8 and c_.iloc[-8:-4].sum() > 0:
                rec["Büyüme"] = c_.iloc[-4:].sum() / c_.iloc[-8:-4].sum() - 1
        p0 = _fiyat(px, t); p1 = _fiyat(px, t + pd.Timedelta(days=ileri_gun)); pm = _fiyat(px, t - pd.Timedelta(days=182))
        if p0 is None or p1 is None:
            continue
        rec["ileri"] = p1 / p0 - 1
        if pm: rec["Momentum"] = p0 / pm - 1
        if hisse is not None:
            h_ = hisse[hisse.index <= q].dropna()
            if len(h_) and h_.iloc[-1] > 0:
                mc = p0 * h_.iloc[-1]
                if "_net" in rec: rec["E/P"] = rec["_net"] / mc
                if "_ozk" in rec: rec["B/P"] = rec["_ozk"] / mc
        out.append(rec)
    return out


def calistir(kodlar, fin_fn, fiyat_fn, endeks, ceyrek=12, ileri_gun=91, gecikme=60, bugun=None, log=print):
    bugun = pd.Timestamp(bugun or dt.date.today())
    son_q = (bugun - pd.Timedelta(days=gecikme + ileri_gun)).to_period("Q").end_time.normalize()
    if son_q + pd.Timedelta(days=gecikme + ileri_gun) > bugun:
        son_q = (son_q - pd.offsets.QuarterEnd(1)).normalize()
    tarihler = [(son_q - pd.offsets.QuarterEnd(i)).normalize() if i else son_q for i in range(ceyrek)][::-1]
    tarihler = [pd.Timestamp(t.date()) for t in tarihler]
    kayit = []
    for k in kodlar:
        try:
            kayit += gozlemler(k, fin_fn(k), fiyat_fn(k), tarihler, ileri_gun, gecikme)
        except Exception as ex:
            log(f"backtest {k}: {str(ex)[:80]}")
    df = pd.DataFrame(kayit)
    if df.empty:
        raise ValueError("Backtest için yeterli veri yok")
    donemler = []
    for t, g in df.groupby("tarih"):
        if len(g) < 9:
            continue
        rk = pd.DataFrame({f: g[f].rank(pct=True) for f in FAKTORLER if f in g})
        g = g.assign(skor=rk.mean(axis=1, skipna=True), n_f=rk.notna().sum(axis=1))
        g = g[g["n_f"] >= 3]
        if len(g) < 9:
            continue
        g["grup"] = pd.qcut(g["skor"].rank(method="first"), 3, labels=["Düşük", "Orta", "Yüksek"])
        ort = g.groupby("grup", observed=False)["ileri"].mean()
        e0 = _fiyat(endeks, t); e1 = _fiyat(endeks, t + pd.Timedelta(days=ileri_gun))
        donemler.append({"tarih": t.strftime("%Y-%m-%d"), "n": int(len(g)), "Yüksek": float(ort["Yüksek"]),
                         "Orta": float(ort["Orta"]), "Düşük": float(ort["Düşük"]),
                         "BIST 100": float(e1 / e0 - 1) if e0 and e1 else None})
    if not donemler:
        raise ValueError("Yeterli dönem oluşmadı")
    d = pd.DataFrame(donemler)
    fark = d["Yüksek"] - d["Düşük"]
    ozet = {
        "donem_sayisi": int(len(d)), "ort_hisse": float(d["n"].mean()),
        "ort_yuksek": float(d["Yüksek"].mean()), "ort_orta": float(d["Orta"].mean()), "ort_dusuk": float(d["Düşük"].mean()),
        "ort_endeks": float(d["BIST 100"].mean()) if d["BIST 100"].notna().any() else None,
        "ort_fark": float(fark.mean()), "isabet": float((fark > 0).mean()),
        "kum_yuksek": float((1 + d["Yüksek"]).prod() - 1), "kum_dusuk": float((1 + d["Düşük"]).prod() - 1),
        "kum_endeks": float((1 + d["BIST 100"].fillna(0)).prod() - 1),
        "uretim": dt.date.today().isoformat(), "ileri_gun": ileri_gun, "gecikme": gecikme,
    }
    t_ist = fark.mean() / (fark.std(ddof=1) / np.sqrt(len(fark))) if len(fark) > 2 and fark.std(ddof=1) > 0 else None
    ozet["t_istatistigi"] = float(t_ist) if t_ist is not None else None
    ozet["yorum"] = yorumla(ozet)
    return {"ozet": ozet, "donemler": donemler}


def yorumla(o):
    p = lambda x: f"%{x * 100:.1f}".replace(".", ",") if x is not None else "–"
    t = (f"{o['donem_sayisi']} çeyreklik dönemde (ortalama {o['ort_hisse']:.0f} hisse) skoru yüksek grup 3 aylık dönemlerde ortalama "
         f"{p(o['ort_yuksek'])}, düşük grup {p(o['ort_dusuk'])} getiri sağladı; fark {p(o['ort_fark'])}. "
         f"Yüksek grup dönemlerin {p(o['isabet'])}'inde düşük gruptan iyi performans gösterdi. ")
    ts = o.get("t_istatistigi")
    if ts is not None:
        tsf = f"{ts:.1f}".replace(".", ",")
        t += (f"Fark istatistiksel olarak anlamlı görünüyor (t ≈ {tsf})." if abs(ts) >= 2 else
              f"Ancak örneklem kısa olduğu için fark istatistiksel olarak güçlü değil (t ≈ {tsf}).")
    return t


def grafik(sonuc, yol):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = pd.DataFrame(sonuc["donemler"])
    d["tarih"] = pd.to_datetime(d["tarih"])
    fig, ax = plt.subplots(figsize=(7.5, 3))
    for c, rk in (("Yüksek", "#1E8E5A"), ("Orta", "#D9A21B"), ("Düşük", "#C0392B"), ("BIST 100", "#6B7280")):
        if d[c].notna().any():
            ax.plot(d["tarih"], ((1 + d[c].fillna(0)).cumprod() - 1) * 100, marker="o", ms=3, lw=1.4, color=rk, label=f"{c} skor" if c != "BIST 100" else c)
    ax.axhline(0, color="#9CA3AF", lw=0.6); ax.set_ylabel("Kümülatif getiri %")
    ax.set_title("Backtest: Skor Gruplarının Kümülatif Getirisi (3 aylık tutma)", loc="left", fontsize=9.5, fontweight="bold")
    ax.legend(fontsize=7, frameon=False); ax.grid(alpha=0.2)
    for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
    fig.savefig(yol, dpi=160, bbox_inches="tight"); plt.close(fig)
