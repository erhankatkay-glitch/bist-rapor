# -*- coding: utf-8 -*-
"""İleri analizler (hisse, kripto ve emtia için ortak):
- Sinyal karnesi: her teknik sinyalin bu varlıkta geçmişteki başarı oranı ve ortalama getirisi
- Hacim profili ve sabitlenmiş (anchored) VWAP seviyeleri
- Olası fiyat aralığı (volatiliteye dayalı olasılık bantları)
- Bilanço tepki analizi (hisseler)
- Göreli güç puanı ve sektör rotasyonu (RRG)
Hepsi yalnızca fiyat/hacim geçmişinden hesaplanır; ek veri gerektirmez."""
import math
import numpy as np
import pandas as pd


def _f(x, d=None):
    import tasarim as TS
    if x is None or (isinstance(x, float) and math.isnan(x)): return "–"
    d = TS.basamak(x) if d is None else d
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _y(x, d=1, isaret=True):
    if x is None or (isinstance(x, float) and math.isnan(x)): return "–"
    return (("+" if x > 0 else "-" if x < 0 else "") if isaret else ("-" if x < 0 else "")) + "%" + f"{abs(x) * 100:.{d}f}".replace(".", ",")


# =====================================================================
# SİNYAL KARNESİ (geçmiş başarı)
# =====================================================================
UFUK = (5, 20, 60)
REPO = "erhankatkay-glitch/bist-rapor"
_BULTEN = {}


def bulten_ozeti(piyasa="bist"):
    """Son kapanış bülteninin özet tablosu (göreli güç puanları vb. için)."""
    if piyasa in _BULTEN: return _BULTEN[piyasa]
    try:
        import requests, io
        r = requests.get(f"https://raw.githubusercontent.com/{REPO}/bulten/{piyasa}/ozet.csv", timeout=15); r.raise_for_status()
        _BULTEN[piyasa] = pd.read_csv(io.BytesIO(r.content))
    except Exception:
        _BULTEN[piyasa] = None
    return _BULTEN[piyasa]


def _olaylar(h, G):
    """Geçmişteki tüm sinyal olayları: {ad: (yön, [bar indeksleri])}. Göstergeler nedensel olduğundan
    tüm seri üzerinde bir kez hesaplanır; formasyonlar ise yalnızca o güne kadarki veriyle aranır."""
    import bist_teknik as T
    c = h["Close"]; O = {}
    def ekle(ad, yon, maske):
        idx = np.flatnonzero(np.asarray(maske.fillna(False), dtype=bool))
        if len(idx): O[ad] = (yon, list(idx))
    def kes_yukari(a, b): return (a > b) & (a.shift() <= b.shift())
    ekle("Altın kesişim (SMA50 > SMA200)", 1, kes_yukari(G["SMA50"], G["SMA200"]))
    ekle("Ölüm kesişimi (SMA50 < SMA200)", -1, kes_yukari(G["SMA200"], G["SMA50"]))
    ekle("EMA20 EMA50'yi yukarı kesti", 1, kes_yukari(G["EMA20"], G["EMA50"]))
    ekle("EMA20 EMA50'yi aşağı kesti", -1, kes_yukari(G["EMA50"], G["EMA20"]))
    ekle("MACD al kesişimi", 1, kes_yukari(G["MACD"], G["MACD_SIG"]))
    ekle("MACD sat kesişimi", -1, kes_yukari(G["MACD_SIG"], G["MACD"]))
    ekle("RSI aşırı satımdan çıkış (30 üstü)", 1, (G["RSI"] > 30) & (G["RSI"].shift() <= 30))
    ekle("RSI aşırı alımdan dönüş (70 altı)", -1, (G["RSI"] < 70) & (G["RSI"].shift() >= 70))
    ekle("SuperTrend al sinyaline döndü", 1, (G["ST_YON"] > 0) & (G["ST_YON"].shift() < 0))
    ekle("SuperTrend sat sinyaline döndü", -1, (G["ST_YON"] < 0) & (G["ST_YON"].shift() > 0))
    ekle("20 dönem zirve kırılımı", 1, (c > G["DC_UST"]) & (c.shift() <= G["DC_UST"].shift()))
    ekle("20 dönem dip kırılımı", -1, (c < G["DC_ALT"]) & (c.shift() >= G["DC_ALT"].shift()))
    z52 = h["High"].rolling(252).max().shift()
    ekle("52 dönem zirvesi aşıldı", 1, (c > z52) & (c.shift() <= z52.shift()))
    bw = G["BB_GEN"]; sik = bw <= bw.rolling(126).quantile(0.1)
    ekle("Bollinger sıkışması sonrası yukarı kırılım", 1, sik.shift(1).fillna(False).astype(bool) & (c > G["BB_UST"]))
    ekle("Fiyat SMA200 üzerine çıktı", 1, kes_yukari(c, G["SMA200"]))
    ekle("Fiyat SMA200 altına indi", -1, kes_yukari(G["SMA200"], c))
    # Mum formasyonları (tüm geçmiş)
    for m in T.mum_formasyonlari(h, G, son_n=len(h)):
        if m["yon"] != 0: O.setdefault("Mum: " + m["ad"], (m["yon"], []))[1].append(m["bar"])
    # Grafik formasyonları: son ~4 yılda her 3 barda bir, yalnızca o güne kadarki veriyle
    n = len(h); bas = max(120, n - 1000)
    son_gorulme = {}
    for t in range(bas, n, 3):
        hh, GG = h.iloc[:t + 1], G.iloc[:t + 1]
        try:
            piv = T.salinimlar(hh, GG, 1.5)
            form, _ = T.grafik_formasyonlari(hh, GG, piv)
        except Exception:
            continue
        for f_ in form:
            if f_["durum"] in ("oluşumda", "içinde") or f_["ad"].startswith(("20 dönem", "52 dönem")): continue
            ad = "Formasyon: " + f_["ad"] + (" (teyit)" if "TEYİT" in f_["durum"] else " (kırılım)")
            if t - son_gorulme.get(ad, -99) <= 15: son_gorulme[ad] = t; continue
            son_gorulme[ad] = t
            O.setdefault(ad, (f_["yon"], []))[1].append(t)
    return O


def sinyal_karnesi(h, G=None, aktif=None):
    """Her sinyal için: adet, 5/20/60 bar sonraki ortalama getiri, isabet oranı (yön doğru mu).
    aktif: şu an görülen sinyal adları (bist_teknik sinyal listesinden) → bunların geçmişi öne çıkarılır."""
    import bist_teknik as T
    h = h.dropna(subset=["Close"])
    if len(h) < 250: return None
    G = G if G is not None else T.gostergeler(h)
    c = h["Close"].values; n = len(c); sat = []
    for ad, (yon, idx) in _olaylar(h, G).items():
        idx = sorted(set(i for i in idx if i < n))
        if len(idx) < 3: continue
        r = {}
        for u in UFUK:
            v = [c[i + u] / c[i] - 1 for i in idx if i + u < n]
            r[u] = v
        if len(r[20]) < 3: continue
        isabet = np.mean([(x > 0) if yon > 0 else (x < 0) for x in r[20]])
        sat.append({"Sinyal": ad, "Yön": yon, "Adet": len(idx), "Son": h.index[idx[-1]],
                    "5g ort": float(np.mean(r[5])) if r[5] else None, "20g ort": float(np.mean(r[20])),
                    "60g ort": float(np.mean(r[60])) if len(r[60]) >= 2 else None, "20g medyan": float(np.median(r[20])),
                    "İsabet (20g)": float(isabet), "Örnek": len(r[20])})
    if not sat: return None
    df = pd.DataFrame(sat)
    # Karşılaştırma: herhangi bir günde 20 bar sonraki getiri (taban oran)
    taban = pd.Series(c).pct_change(20).shift(-20).dropna()
    df.attrs["taban_20"] = float(taban.mean()); df.attrs["taban_pozitif"] = float((taban > 0).mean())
    if aktif:
        def eslesir(ad):
            a = ad.replace("Mum: ", "").replace("Formasyon: ", "").split(" (")[0].lower()
            for x in aktif:
                xl = x.lower()
                if a not in xl: continue
                if ad.startswith("Formasyon:"):
                    if "(teyit)" in ad and "teyit" not in xl: continue
                    if "(kırılım)" in ad and "kırılım" not in xl: continue
                return True
            return False
        df["Aktif"] = df["Sinyal"].apply(eslesir)
    else:
        df["Aktif"] = False
    df["Güven"] = np.where(df["Örnek"] >= 15, "yüksek", np.where(df["Örnek"] >= 7, "orta", "düşük"))
    return df.sort_values(["Aktif", "Örnek"], ascending=[False, False]).reset_index(drop=True)


def karne_yorumu(df, ad=""):
    """Sinyal karnesi için kısa analist cümleleri."""
    if df is None or df.empty: return ""
    C = []; tb = df.attrs.get("taban_pozitif")
    ak = df[df["Aktif"]]
    for _, r in ak.head(3).iterrows():
        yon = "yükseliş" if r["Yön"] > 0 else "düşüş"
        C.append(f"Şu anda aktif olan '{r['Sinyal'].replace('Mum: ', '').replace('Formasyon: ', '')}' sinyali bu varlıkta geçmişte {r['Örnek']} kez oluştu; "
                 f"20 işlem günü içinde {yon} yönünde isabet oranı %{r['İsabet (20g)'] * 100:.0f}, ortalama getiri {_y(r['20g ort'])} "
                 f"(güvenilirlik {r['Güven']}).")
    guv = df[(df["Örnek"] >= 7)]
    if len(guv):
        en_i = guv.sort_values("İsabet (20g)", ascending=False).iloc[0]
        C.append(f"Geçmişte en güvenilir çalışan sinyal '{en_i['Sinyal'].replace('Mum: ', '').replace('Formasyon: ', '')}' oldu "
                 f"(%{en_i['İsabet (20g)'] * 100:.0f} isabet, {en_i['Örnek']} örnek).")
    if tb is not None:
        C.append(f"Karşılaştırma için: rastgele bir günde alıp 20 gün tutmanın pozitif getiri olasılığı %{tb * 100:.0f}.")
    return " ".join(C)


# =====================================================================
# HACİM PROFİLİ ve ANCHORED VWAP
# =====================================================================
def hacim_profili(h, gun=250, kutu=40):
    w = h.iloc[-gun:].dropna(subset=["Close"])
    if len(w) < 40 or w["Volume"].sum() <= 0: return None
    lo, hi = float(w["Low"].min()), float(w["High"].max())
    if hi <= lo: return None
    kenar = np.linspace(lo, hi, kutu + 1); orta = (kenar[:-1] + kenar[1:]) / 2; hac = np.zeros(kutu)
    for _, r in w.iterrows():   # her mumun hacmi high–low aralığına eşit dağıtılır
        a, b = np.searchsorted(kenar, r["Low"], "right") - 1, np.searchsorted(kenar, r["High"], "right") - 1
        a, b = max(a, 0), min(max(b, a), kutu - 1)
        hac[a:b + 1] += r["Volume"] / (b - a + 1)
    poc = int(hac.argmax()); toplam = hac.sum(); sec = {poc}; s = hac[poc]
    while s < 0.7 * toplam:
        sol, sag = min(sec) - 1, max(sec) + 1
        aday = [(hac[i], i) for i in (sol, sag) if 0 <= i < kutu]
        if not aday: break
        v, i = max(aday); sec.add(i); s += v
    c = float(w["Close"].iloc[-1])
    yerel = [i for i in range(1, kutu - 1) if hac[i] > hac[i - 1] and hac[i] > hac[i + 1] and hac[i] > np.percentile(hac, 70)]
    hvn = sorted([float(orta[i]) for i in yerel], key=lambda x: abs(x - c))[:4]
    lvn = [float(orta[i]) for i in range(1, kutu - 1) if hac[i] < np.percentile(hac, 20)]
    return {"orta": orta, "hacim": hac, "poc": float(orta[poc]), "vah": float(kenar[max(sec) + 1]), "val": float(kenar[min(sec)]),
            "hvn": hvn, "lvn": lvn, "fiyat": c, "gun": len(w),
            "konum": "değer alanının üzerinde" if c > kenar[max(sec) + 1] else "değer alanının altında" if c < kenar[min(sec)] else "değer alanı içinde"}


def anchored_vwap(h):
    """Önemli noktalardan başlatılmış VWAP seviyeleri."""
    c = h["Close"]; tp = (h["High"] + h["Low"] + h["Close"]) / 3; v = h["Volume"].replace(0, np.nan)
    if v.dropna().sum() <= 0: return {}
    def vwap(bas):
        s = h.index >= bas; vv = v[s].fillna(0)
        return float((tp[s] * vv).sum() / vv.sum()) if vv.sum() > 0 else None
    son = h.index[-1]; out = {}
    yb = h.index[h.index >= pd.Timestamp(son.year, 1, 1)]
    if len(yb) > 3: out["Yılbaşından (YTD) VWAP"] = vwap(yb[0])
    w = h.iloc[-252:]
    out["52 hafta dibinden VWAP"] = vwap(w["Low"].idxmin())
    out["52 hafta zirvesinden VWAP"] = vwap(w["High"].idxmax())
    w3 = h.iloc[-63:]
    out["Son 3 ay dibinden VWAP"] = vwap(w3["Low"].idxmin())
    return {k: x for k, x in out.items() if x}


# =====================================================================
# OLASI FİYAT ARALIĞI
# =====================================================================
def fiyat_araligi(h, kripto=False):
    c = h["Close"].dropna()
    if len(c) < 120: return None
    r = np.log(c).diff().dropna()
    ew = float(np.sqrt((r ** 2).ewm(alpha=0.06).mean().iloc[-1]))          # RiskMetrics benzeri
    tarihsel = float(r.iloc[-252:].std())
    sigma = 0.6 * ew + 0.4 * tarihsel
    p = float(c.iloc[-1]); out = {"sigma_gun": sigma, "fiyat": p, "ufuklar": []}
    for ad, n in ((("1 hafta", 7), ("1 ay", 30), ("3 ay", 90)) if kripto else (("1 hafta", 5), ("1 ay", 21), ("3 ay", 63))):
        s = sigma * math.sqrt(n)
        hist = (c.shift(-n) / c - 1).dropna().iloc[-1500:]
        out["ufuklar"].append({"ad": ad, "gun": n,
                               "68_alt": p * math.exp(-s), "68_ust": p * math.exp(s), "95_alt": p * math.exp(-1.96 * s), "95_ust": p * math.exp(1.96 * s),
                               "olasilik_10_ust": float((hist > 0.10).mean()) if len(hist) > 50 else None,
                               "olasilik_10_alt": float((hist < -0.10).mean()) if len(hist) > 50 else None})
    out["yillik_vol"] = sigma * math.sqrt(365 if kripto else 252)
    return out


def aralik_yorumu(fa, para=""):
    if not fa: return ""
    u = fa["ufuklar"][1]
    return (f"Güncel oynaklığa göre fiyatın 1 ay içinde %68 olasılıkla {_f(u['68_alt'])}–{_f(u['68_ust'])} {para}, %95 olasılıkla "
            f"{_f(u['95_alt'])}–{_f(u['95_ust'])} {para} aralığında kalması beklenir. Geçmişte 1 aylık dönemlerin "
            f"yüzde {(u['olasilik_10_ust'] or 0) * 100:.0f} kadarında %10'dan fazla yükseliş, yüzde {(u['olasilik_10_alt'] or 0) * 100:.0f} kadarında %10'dan fazla düşüş görüldü.")


# =====================================================================
# BİLANÇO TEPKİ ANALİZİ (hisseler)
# =====================================================================
def bilanco_tarihleri(kod):
    """Yahoo'dan geçmiş ve beklenen bilanço açıklama tarihleri."""
    import yfinance as yf
    e = yf.Ticker(kod.upper() + ".IS").get_earnings_dates(limit=24)
    if e is None or len(e) == 0: return [], None
    idx = pd.to_datetime(e.index)
    try: idx = idx.tz_convert("Europe/Istanbul").tz_localize(None)
    except Exception:
        try: idx = idx.tz_localize(None)
        except Exception: pass
    bugun = pd.Timestamp.today().normalize()
    gecmis = sorted({d.normalize() for d in idx if d.normalize() <= bugun})
    gelecek = sorted({d.normalize() for d in idx if d.normalize() > bugun})
    return gecmis, (gelecek[0] if gelecek else None)


def bilanco_tepkisi(h, tarihler, endeks=None):
    """Her açıklama sonrası 1/5/20 işlem günlük getiri (ve endekse göre fark)."""
    c = h["Close"].dropna()
    if not tarihler or len(c) < 60: return None
    e = endeks["Close"].dropna().reindex(c.index, method="ffill") if endeks is not None else None
    sat = []
    for d in tarihler:
        once = c[c.index < d]
        if len(once) == 0: continue
        i0 = c.index.get_loc(once.index[-1])
        satir = {"Tarih": d}
        for n in (1, 5, 20):
            if i0 + n < len(c):
                r = c.iloc[i0 + n] / c.iloc[i0] - 1
                satir[f"{n}g"] = float(r)
                if e is not None and not pd.isna(e.iloc[i0]) and not pd.isna(e.iloc[i0 + n]):
                    satir[f"{n}g fark"] = float(r - (e.iloc[i0 + n] / e.iloc[i0] - 1))
        if "1g" in satir: sat.append(satir)
    if not sat: return None
    df = pd.DataFrame(sat).sort_values("Tarih", ascending=False)
    oz = {"adet": len(df), "1g_ort": float(df["1g"].mean()), "5g_ort": float(df["5g"].mean()) if "5g" in df else None,
          "20g_ort": float(df["20g"].mean()) if "20g" in df else None, "1g_pozitif": float((df["1g"] > 0).mean()),
          "5g_pozitif": float((df["5g"] > 0).mean()) if "5g" in df else None,
          "ort_mutlak_1g": float(df["1g"].abs().mean())}
    return {"tablo": df, "ozet": oz}


def bilanco_yorumu(bt, sonraki=None):
    if not bt: return ""
    o = bt["ozet"]
    t = (f"Son {o['adet']} bilanço açıklamasında hisse ertesi gün ortalama {_y(o['1g_ort'])}, 5 gün içinde ortalama {_y(o['5g_ort'])} "
         f"tepki verdi. İlk gün tepkisi açıklamaların %{o['1g_pozitif'] * 100:.0f} oranında pozitif oldu; ortalama ilk gün hareketi "
         f"±{_y(o['ort_mutlak_1g'], 1, False)}.")
    if sonraki is not None: t += f" Bir sonraki beklenen açıklama tarihi: {sonraki:%d.%m.%Y}."
    return t


# =====================================================================
# GÖRELİ GÜÇ PUANI ve SEKTÖR ROTASYONU
# =====================================================================
def rs_ham(c):
    """IBD tarzı ağırlıklı göreli performans: 3 ay %40, 6 ay %20, 9 ay %20, 12 ay %20."""
    c = c.dropna()
    def r(n): return c.iloc[-1] / c.iloc[-n - 1] - 1 if len(c) > n else np.nan
    return 0.4 * r(63) + 0.2 * r(126) + 0.2 * r(189) + 0.2 * r(252)


def rs_puanlari(seriler):
    """{kod: kapanış serisi} → {kod: 1–99 göreli güç puanı}"""
    ham = pd.Series({k: rs_ham(s) for k, s in seriler.items()}).dropna()
    if ham.empty: return {}
    return {k: int(round(1 + 98 * v)) for k, v in ham.rank(pct=True).items()}


def rrg(gruplar, benchmark, hafta=10):
    """Sektör rotasyon grafiği (JdK RS-Ratio / RS-Momentum benzeri). gruplar: {sektör: [kapanış serileri]}.
    Döner: {sektör: DataFrame[ratio, momentum]} (son `hafta` hafta)."""
    b = benchmark.resample("W-FRI").last().dropna(); out = {}
    for ad, seriler in gruplar.items():
        if len(seriler) < 2: continue
        haf = pd.concat([s.resample("W-FRI").last() for s in seriler], axis=1).dropna(how="all")
        haf = haf.pct_change().mean(axis=1).fillna(0).add(1).cumprod()   # eşit ağırlıklı sektör endeksi
        rs = (haf / b.reindex(haf.index, method="ffill")).dropna()
        if len(rs) < 40: continue
        ratio = 100 + ((rs.rolling(10).mean() / rs.rolling(30).mean() - 1) * 100)
        z = (ratio - ratio.rolling(26).mean()) / ratio.rolling(26).std()
        ratio_n = 100 + z
        mom = 100 + ((ratio_n - ratio_n.shift(4)) / ratio_n.rolling(26).std().replace(0, np.nan))
        d = pd.DataFrame({"ratio": ratio_n, "momentum": mom}).dropna().iloc[-hafta:]
        if len(d) >= 3: out[ad] = d
    return out


def rrg_bolge(r, m):
    return "Lider" if r >= 100 and m >= 100 else "Zayıflayan" if r >= 100 else "Toparlanan" if m >= 100 else "Geride"


def g_rrg(rr):
    import matplotlib.pyplot as plt
    import tasarim as TS
    C = TS.GRAFIK
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    tum = pd.concat(rr.values()) if rr else pd.DataFrame({"ratio": [100], "momentum": [100]})
    lx = max(abs(tum["ratio"] - 100).max(), 1.5) * 1.15; ly = max(abs(tum["momentum"] - 100).max(), 1.5) * 1.15
    ax.axhspan(100, 100 + ly, xmin=0.5, xmax=1, color=C["yesil"], alpha=0.07); ax.axhspan(100 - ly, 100, xmin=0.5, xmax=1, color=C["sari"], alpha=0.08)
    ax.axhspan(100 - ly, 100, xmin=0, xmax=0.5, color=C["kirmizi"], alpha=0.07); ax.axhspan(100, 100 + ly, xmin=0, xmax=0.5, color=C["mavi"], alpha=0.07)
    ax.axhline(100, color=C["gri"], lw=0.7); ax.axvline(100, color=C["gri"], lw=0.7)
    for ad, d in rr.items():
        ax.plot(d["ratio"], d["momentum"], lw=1, alpha=0.6, color=C["lac"])
        ax.scatter(d["ratio"].iloc[-1], d["momentum"].iloc[-1], s=28, zorder=5, color=C["mavi"])
        ax.annotate(ad, (d["ratio"].iloc[-1], d["momentum"].iloc[-1]), xytext=(4, 3), textcoords="offset points", fontsize=6.5)
    for x, y, t in ((100 + lx * 0.95, 100 + ly * 0.92, "LİDER"), (100 + lx * 0.95, 100 - ly * 0.92, "ZAYIFLAYAN"),
                    (100 - lx * 0.95, 100 - ly * 0.92, "GERİDE"), (100 - lx * 0.95, 100 + ly * 0.92, "TOPARLANAN")):
        ax.text(x, y, t, fontsize=7, color=C["gri"], ha="right" if x > 100 else "left", va="top" if y > 100 else "bottom", fontweight="bold")
    ax.set_xlim(100 - lx, 100 + lx); ax.set_ylim(100 - ly, 100 + ly)
    ax.set_xlabel("Göreli güç (endekse göre)"); ax.set_ylabel("Göreli güç ivmesi")
    ax.set_title("Sektör rotasyon haritası (son 10 hafta, BIST 100'e göre)", loc="left")
    import io
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=140, bbox_inches="tight"); plt.close(fig); b.seek(0); return b


# =====================================================================
# GRAFİKLER
# =====================================================================
def g_profil(h, hp, avw, baslik, gun=250):
    """Fiyat + sağda hacim profili + anchored VWAP çizgileri."""
    import matplotlib.pyplot as plt, io
    import tasarim as TS
    C = TS.GRAFIK
    w = h.iloc[-gun:]
    fig = plt.figure(figsize=(7.5, 3.6)); gs = fig.add_gridspec(1, 2, width_ratios=[4, 1.1], wspace=0.02)
    ax = fig.add_subplot(gs[0]); ap = fig.add_subplot(gs[1], sharey=ax)
    ax.plot(w.index, w["Close"], color=C["lac"], lw=1.1, label="Fiyat")
    renk = [C["tur"], C["mavi"], C["sari"], C["turkuaz"]]
    for (ad, v), r in zip(avw.items(), renk):
        ax.axhline(v, color=r, lw=0.9, ls="--", label=ad.replace(" VWAP", ""))
    if hp:
        ax.axhspan(hp["val"], hp["vah"], color=C["acik"], alpha=0.25, lw=0, label="Değer alanı (%70)")
        ax.axhline(hp["poc"], color=C["kirmizi"], lw=1.2, label="POC (en çok işlem)")
        ap.barh(hp["orta"], hp["hacim"], height=(hp["orta"][1] - hp["orta"][0]) * 0.9, color=C["mavi"], alpha=0.45)
        ap.barh([hp["poc"]], [hp["hacim"].max()], height=(hp["orta"][1] - hp["orta"][0]) * 0.9, color=C["kirmizi"], alpha=0.7)
    ap.axis("off"); ax.legend(fontsize=5.8, loc="upper left", ncol=2, frameon=False)
    ax.set_title(baslik, loc="left"); ax.grid(alpha=0.25)
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=150, bbox_inches="tight"); plt.close(fig); b.seek(0); return b


def g_aralik(h, fa, baslik, gun=180):
    import matplotlib.pyplot as plt, io
    import tasarim as TS
    C = TS.GRAFIK
    w = h["Close"].iloc[-gun:]
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    ax.plot(w.index, w, color=C["lac"], lw=1.1)
    son = w.index[-1]; p = float(w.iloc[-1])
    gunluk = (pd.Timedelta(days=1))
    for u, alfa in zip(fa["ufuklar"], (0.35, 0.25, 0.15)):
        t = son + gunluk * (u["gun"] * (7 / 5) if u["gun"] in (5, 21, 63) else u["gun"])
        ax.fill_between([son, t], [p, u["95_alt"]], [p, u["95_ust"]], color=C["acik"], alpha=alfa, lw=0)
        ax.fill_between([son, t], [p, u["68_alt"]], [p, u["68_ust"]], color=C["mavi"], alpha=alfa * 0.8, lw=0)
        ax.annotate(u["ad"], (t, u["95_ust"]), fontsize=6.5, color=C["gri"], ha="right", va="bottom")
    ax.set_title(baslik, loc="left"); ax.grid(alpha=0.25)
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=150, bbox_inches="tight"); plt.close(fig); b.seek(0); return b


# =====================================================================
# TOPLU PAKET
# =====================================================================
def _ohlcv(h):
    h = h.copy()
    for c in ("Open", "High", "Low"):
        if c not in h: h[c] = h["Close"]
        h[c] = h[c].fillna(h["Close"])
    if "Volume" not in h: h["Volume"] = 0.0
    h["Volume"] = h["Volume"].fillna(0)
    return h.dropna(subset=["Close"])


def ileri_paket(h, kripto=False, aktif=None, G=None):
    """Tek çağrıda: sinyal karnesi, hacim profili, anchored VWAP, olası fiyat aralığı."""
    h = _ohlcv(h); out = {}
    for ad, fn in (("karne", lambda: sinyal_karnesi(h, G, aktif)), ("profil", lambda: hacim_profili(h, 365 if kripto else 250)),
                   ("avwap", lambda: anchored_vwap(h)), ("aralik", lambda: fiyat_araligi(h, kripto))):
        try: out[ad] = fn()
        except Exception as ex: out[ad] = None; out[ad + "_hata"] = str(ex)[:100]
    return out
