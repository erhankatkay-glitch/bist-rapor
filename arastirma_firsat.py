"""Aşama 2 araştırması: fırsat motorundaki her kurulumun geçmiş sonuçlarını, önerilen teyit filtreleriyle karşılaştırır.

Hiçbir şey göndermez. Test dalında çalıştırılır:  python arastirma_firsat.py [kripto4s|kriptog|bistg] ...
Çıktı: her kurulum × yön için olay sayısı, ilk hedef oranı (p1), ortalama R; filtreli ve filtresiz.

Filtreler (yalnızca o ana kadarki veriyi kullanır, ileriye bakmaz):
  rejim   : piyasa öncüsü (kripto: BTC, BIST: XU100) aynı yönde trendde (kapanış EMA50'nin, EMA20 EMA50'nin o tarafında)
  yapi    : piyasa yapısı işlem yönünde — AL için son teyitli dip bir öncekinden yüksek (HL) ya da kapanış son teyitli tepenin üstünde (BOS)
  mum     : tetik mumunda price action teyidi — yutan mum, iğne (pin bar) ya da mumun en iyi %25'lik bölgesinde kapanış
  oda     : işlem yönündeki en yakın karşı salınım seviyesi en az 1R uzakta (H1'e yer var)
  kume    : aynı mumda aynı yönde tetiklenen varlık sayısı piyasanın %15'ini geçmiyor (toplu, birbirine bağlı sinyal değil)
  genis   : stop en az 1,5 ATR (gürültüye karşı)
"""
import sys, time, json, itertools
import numpy as np
import pandas as pd
import bist_teknik as T
import firsat as F

RLER = (1.0, 2.0, 3.0)


def log(*a):
    print(*a, flush=True)


# ------------------------------------------------------------------ veri
def kripto_veri(aralik, adet=80):
    import kapanis as K
    ev = sorted(K.kripto_evren(), key=lambda e: -e["hacim"])[:adet]
    out = {}
    for e in ev:
        try:
            d = K.kripto_mum(e["baz"], e["borsa"], aralik, 1000)
            if len(d) >= 300: out[e["baz"]] = d
        except Exception as ex:
            log("veri", e["baz"], ex)
        time.sleep(0.05)
    return out, "BTC"


def bist_veri(adet=150):
    import yfinance as yf, bist_evren as EV
    df, _, _ = EV.bist_listesi()
    kodlar = sorted(df["Kod"])
    v = yf.download([k + ".IS" for k in kodlar] + ["XU100.IS"], period="6y", interval="1d", auto_adjust=True,
                    progress=False, group_by="ticker", threads=True)
    out = {}
    for k in kodlar + ["XU100"]:
        try:
            d = v[k + ".IS"].dropna(subset=["Close"])
            d.index = d.index.tz_localize(None) if d.index.tz is not None else d.index
            if len(d) >= 400: out[k] = d
        except Exception:
            pass
    # likiditeye göre en büyük 'adet' hisse + endeks
    hac = {k: float((d["Close"] * d["Volume"]).tail(60).mean()) for k, d in out.items() if k != "XU100"}
    sec = sorted(hac, key=lambda k: -hac[k])[:adet]
    return {k: out[k] for k in sec + ["XU100"] if k in out}, "XU100"


def abd_veri(adet=200):
    import yfinance as yf, bist_abd as AB
    lk, _ = AB.likit_hisseler(AB.tum_hisseler())
    lk = lk.sort_values("Dolar hacim", ascending=False).head(adet)
    sem = list(lk["Sembol"]) + ["^GSPC"]
    v = yf.download(sem, period="6y", interval="1d", auto_adjust=True, progress=False, group_by="ticker", threads=True)
    out = {}
    for s in sem:
        try:
            d = v[s].dropna(subset=["Close"]); d.index = d.index.tz_localize(None) if d.index.tz is not None else d.index
            if len(d) >= 400: out["SPX" if s == "^GSPC" else s] = d
        except Exception:
            pass
    return out, "SPX"


def bist4s_veri(adet=150):
    import kapanis as K, bist_evren as EV
    df, _, _ = EV.bist_listesi()
    h1 = K.yahoo_saatlik([k + ".IS" for k in sorted(df["Kod"])] + ["XU100.IS"], "Europe/Istanbul", sure="730d")
    simdi = pd.Timestamp.now(tz="Europe/Istanbul").tz_localize(None)
    out = {s[:-3]: K.bist_4s(d, simdi) for s, d in h1.items()}
    out = {k: d for k, d in out.items() if len(d) >= 300}
    hac = {k: float((d["Close"] * d["Volume"]).tail(120).mean()) for k, d in out.items() if k != "XU100"}
    sec = sorted(hac, key=lambda k: -hac[k])[:adet]
    return {k: out[k] for k in sec + ["XU100"] if k in out}, "XU100"


def emtia_veri():
    import yfinance as yf, bist_varlik as V
    sem = {k: v[0] for k, v in V.VARLIKLAR.items() if v[2] == "emtia" and v[0]}
    v = yf.download(list(sem.values()), period="10y", interval="1d", auto_adjust=True, progress=False, group_by="ticker", threads=True)
    out = {}
    for k, s in sem.items():
        try:
            d = v[s].dropna(subset=["Close"]); d.index = d.index.tz_localize(None) if d.index.tz is not None else d.index
            if len(d) >= 400: out[k] = d
        except Exception:
            pass
    return out, None


def haftalik(veri):
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    return {k: d[list(agg)].resample("W-FRI").agg(agg).dropna(subset=["Close"]) for k, d in veri.items()}


# ------------------------------------------------------------------ özellikler
def rejim_serisi(d):
    G = T.gostergeler(d)
    c, e20, e50 = d["Close"], G["EMA20"], G["EMA50"]
    r = np.where((c > e50) & (e20 > e50), 1, np.where((c < e50) & (e20 < e50), -1, 0))
    return pd.Series(r, index=d.index)


salinimlar = F.salinimlar


def ozellikler(M, stop, t, sal, at):
    """Canlı motorla aynı price action teyitleri (firsat.pa_ozellik) + geniş stop."""
    oz = F.pa_ozellik(M, stop[t], t, sal)
    oz["genis"] = bool(M["Close"][t] - stop[t] >= 1.5 * at[t])
    return oz


# ------------------------------------------------------------------ olaylar
def olaylar(veri, onder, tf):
    rejim = rejim_serisi(veri[onder]) if onder in veri else None
    kayit = []
    for kod, d in veri.items():
        if kod == onder: continue
        try:
            G = T.gostergeler(d); A = F.diziler(d, G)
        except Exception as ex:
            log("gösterge", kod, ex); continue
        n = len(A["Close"]); bas = max(60 if tf in ("H", "A") else 220, n - F.GECMIS_BAR)
        rj = rejim.reindex(d.index, method="ffill").to_numpy() if rejim is not None else np.zeros(n)
        for yon in (1, -1):
            M = F.ayna(A, yon); tet = F.tetikler(M)
            sal = salinimlar(M["High"], M["Low"])
            H, L, C, O = M["High"].tolist(), M["Low"].tolist(), M["Close"].tolist(), M["Open"].tolist()
            for k, (m, stop) in tet.items():
                for t in np.flatnonzero(m):
                    if t < bas or t >= n - 1: continue
                    s = F.simule(H, L, C, t, C[t], stop[t], RLER, F.MAKS_BAR[tf], O)
                    if not s: continue
                    oz = ozellikler(M, stop, t, sal, M["ATR"])
                    kayit.append({"kod": kod, "zaman": d.index[t], "kurulum": k, "yon": yon, "R": s[0], "asama": s[1],
                                  "rejim": int(rj[t] * yon) if np.isfinite(rj[t]) else 0, **oz})
    df = pd.DataFrame(kayit)
    if len(df):
        evren = max(1, len(veri) - 1)
        say = df.groupby(["zaman", "yon"])["kod"].transform("count")
        df["kume"] = (say / evren) <= 0.15
    return df


def ozet(df, maske=None):
    x = df if maske is None else df[maske]
    if not len(x): return {"n": 0}
    return {"n": int(len(x)), "p1": round(float((x["asama"] >= 1).mean()), 3), "ortR": round(float(x["R"].mean()), 3),
            "kazanc": round(float((x["R"] > 0).mean()), 3)}


def rapor(df, ad):
    log(f"\n==================== {ad}: {len(df)} olay ====================")
    if not len(df): return {}
    filtreler = {
        "taban": None,
        "rejim": df["rejim"] > 0,
        "rejim≥0": df["rejim"] >= 0,
        "yapi": df["yapi"],
        "mum": df["mum"],
        "oda": df["oda"],
        "kume": df["kume"],
        "genis": df["genis"],
        "rejim+yapi": (df["rejim"] > 0) & df["yapi"],
        "rejim+yapi+mum": (df["rejim"] > 0) & df["yapi"] & df["mum"],
        "rejim+yapi+oda": (df["rejim"] > 0) & df["yapi"] & df["oda"],
        "rejim≥0+yapi+mum+oda+kume": (df["rejim"] >= 0) & df["yapi"] & df["mum"] & df["oda"] & df["kume"],
        "hepsi": (df["rejim"] > 0) & df["yapi"] & df["mum"] & df["oda"] & df["kume"],
    }
    sonuc = {}
    for (k, y), g in df.groupby(["kurulum", "yon"]):
        satir = {}
        for fa, mk in filtreler.items():
            satir[fa] = ozet(g, None if mk is None else mk.loc[g.index])
        sonuc[f"{k}|{'AL' if y == 1 else 'SAT'}"] = satir
    satir = {fa: ozet(df, mk) for fa, mk in filtreler.items()}
    sonuc["TÜMÜ"] = satir
    # Aşırı uyum kontrolü: filtre hem eski hem yeni yarıda işe yarıyor mu?
    orta = df["zaman"].sort_values().iloc[len(df) // 2]
    for yari, mk_y in (("ESKİ YARI", df["zaman"] < orta), ("YENİ YARI", df["zaman"] >= orta)):
        sonuc[f"TÜMÜ · {yari}"] = {fa: ozet(df, mk_y if mk is None else (mk & mk_y)) for fa, mk in filtreler.items()}
    for anahtar, satir in sonuc.items():
        log(f"\n-- {anahtar}")
        for fa, o in satir.items():
            if o.get("n", 0) >= 15: log(f"   {fa:28s} n={o['n']:5d}  p1={o['p1']:.2f}  ortR={o['ortR']:+.3f}  kazanç={o['kazanc']:.2f}")
    return sonuc


if __name__ == "__main__":
    isler = sys.argv[1:] or ["kripto4s", "kriptog", "bistg"]
    tum = {}
    for i in isler:
        t0 = time.time()
        if i == "kripto4s": veri, onder = kripto_veri("4h"); tf = "4S"
        elif i == "kriptog": veri, onder = kripto_veri("1d"); tf = "G"
        elif i == "bistg": veri, onder = bist_veri(); tf = "G"
        elif i == "bist4s": veri, onder = bist4s_veri(); tf = "4S"
        elif i == "bisth": veri, onder = bist_veri(); veri = haftalik(veri); tf = "H"
        elif i == "abdg": veri, onder = abd_veri(); tf = "G"
        elif i == "abdh": veri, onder = abd_veri(); veri = haftalik(veri); tf = "H"
        elif i == "emtiag": veri, onder = emtia_veri(); tf = "G"
        else: continue
        log(f"{i}: {len(veri)} varlık, veri {time.time() - t0:.0f} sn")
        df = olaylar(veri, onder, tf)
        tum[i] = rapor(df, i)
        df.to_csv(f"arastirma_{i}.csv", index=False)
        log(f"{i} süre {time.time() - t0:.0f} sn")
    json.dump(tum, open("arastirma_ozet.json", "w"), ensure_ascii=False, indent=1, default=str)
