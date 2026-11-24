# -*- coding: utf-8 -*-
"""Çok zaman dilimli teknik analiz motoru (günlük / haftalık / aylık).
Göstergeler, oylama özeti, mum formasyonları, grafik formasyonları, price action,
Fibonacci, pivot noktaları, destek/direnç ve uyumsuzluklar. Yalnızca pandas/numpy kullanır."""
import math
import datetime as dt
import numpy as np
import pandas as pd

def sayi(x, d=None):
    """Fiyata uygun basamakla Türkçe biçim (1.234,56)."""
    if x is None or (isinstance(x, float) and math.isnan(x)): return "–"
    import tasarim as TS
    d = d if d is not None else TS.basamak(x)
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def tr(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


KRIPTO_TAM_MUM = False   # True: kriptoda henüz kapanmamış (bugünkü UTC) mumu at — kapanış bültenleri için


TF_AD = {"1S": "1 saatlik", "4S": "4 saatlik", "G": "Günlük", "H": "Haftalık", "A": "Aylık"}
ETIKETLER = ["GÜÇLÜ SAT", "SAT", "NÖTR", "AL", "GÜÇLÜ AL"]


# =====================================================================
# VERİ
# =====================================================================
KURESEL = {"USDTRY": ("TRY=X", "Dolar/TL"), "EURTRY": ("EURTRY=X", "Euro/TL"), "DXY": ("DX-Y.NYB", "Dolar endeksi (DXY)"),
           "SP500": ("^GSPC", "S&P 500"), "NASDAQ": ("^IXIC", "Nasdaq"), "DOW": ("^DJI", "Dow Jones"), "DAX": ("^GDAXI", "DAX"),
           "VIX": ("^VIX", "VIX korku endeksi"), "US10Y": ("^TNX", "ABD 10 yıllık faiz")}


def yahoo_sembol(kod):
    """BIST kodu / emtia / kripto için Yahoo sembolü ve türü."""
    import bist_varlik as V, bist_kripto as KR
    k = kod.upper().strip()
    if k.endswith(".US"):
        import bist_abd as AB
        return AB.yahoo(k), "abd"
    if KR.kripto_mu(k):
        return f"{KR.coz(k)[0]}-USD", "kripto"
    if k in V.VARLIKLAR:
        y, _, tur, *_ = V.VARLIKLAR[k]
        return (y or "GC=F"), tur
    if k in ("XU100", "XU030", "XBANK", "XUSIN", "XHOLD"):
        return k + ".IS", "endeks"
    if k in KURESEL:
        return KURESEL[k][0], "endeks"
    return k.replace(".IS", "") + ".IS", "hisse"


def _kripto(kod):
    import bist_varlik as V, bist_kripto as KR
    k = kod.upper().strip()
    return KR.kripto_mu(k) or (k in V.VARLIKLAR and V.VARLIKLAR[k][2] == "kripto")


def gunluk_veri(kod, fiyat_fn=None):
    """Uzun günlük OHLCV (gün içi güncellemeli). GRAMALTIN: ons altın × USD/TRY / 31,1035.
    Kripto: Binance / OKX günlük mumları (USDT veya TL paritesi)."""
    import bist_rapor as br
    k = kod.upper().strip()
    if _kripto(k) and not fiyat_fn:
        import bist_kripto as KR
        baz, par, borsa = KR.coz(k)
        h, kul = KR.mumlar(baz, par, borsa)
        if KRIPTO_TAM_MUM:
            h = h[h.index.date < dt.datetime.now(dt.timezone.utc).date()]
        h.attrs["borsa"] = kul
        return h, "kripto"
    if _kripto(k) and fiyat_fn:
        import bist_kripto as KR
        baz, par, borsa = KR.coz(k)
        h = fiyat_fn(f"{baz}-USD")
        if par == "TRY":
            fx = fiyat_fn("TRY=X")["Close"].reindex(h.index, method="ffill")
            h = h.copy()
            for c in ("Open", "High", "Low", "Close"): h[c] = h[c] * fx
        return h.dropna(subset=["Close"]), "kripto"
    y, tur = yahoo_sembol(k)
    if fiyat_fn:
        h = fiyat_fn(y)
    else:
        import yfinance as yf
        h = br._naive(yf.Ticker(y).history(period="max" if tur == "kripto" else "15y", auto_adjust=True))
        if h is None or h.empty:
            raise ValueError(f"{k} için fiyat verisi bulunamadı.")
        h, _ = br.canli_guncelle(h, y)
    if k == "GRAMALTIN":
        fx = (br.kur_cek() if not fiyat_fn else fiyat_fn("TRY=X")["Close"])
        f = fx.reindex(h.index, method="ffill")
        h = h[["Open", "High", "Low", "Close"]].mul(f, axis=0) / 31.1035
        h["Volume"] = 0.0
    h = h[[c for c in ("Open", "High", "Low", "Close", "Volume") if c in h]].dropna(subset=["Close"])
    if "Volume" not in h: h["Volume"] = 0.0
    for c in ("Open", "High", "Low"):
        h[c] = h[c].fillna(h["Close"])
    h = h[h["Close"] > 0]
    return h, tur


def yeniden_ornekle(h, tf, tur="hisse"):
    if tf in ("G", "1S"):
        return h
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    if "TakerBuy" in h: agg["TakerBuy"] = "sum"
    if tf == "4S":
        if tur == "hisse":   # BIST 10:00–18:00 (+18:00–18:10 kapanış seansı son dilime): 10–14 ve 14–18
            idx = h.index; saat = idx.hour
            idx = idx.where(saat < 18, idx.normalize() + pd.Timedelta(hours=17, minutes=59))
            idx = idx.where(saat >= 10, idx.normalize() + pd.Timedelta(hours=10))
            h = h.set_axis(idx)
            return h.resample("4h", offset="2h").agg(agg).dropna(subset=["Close"])
        if tur == "abd":     # ET saatinde 09:30–13:30 ve 13:30–16:00
            dk = h.index.hour * 60 + h.index.minute
            h = h[(dk >= 570) & (h.index.hour < 16)]
            return h.resample("4h", origin="start_day", offset="9h30min").agg(agg).dropna(subset=["Close"])
        return h.resample("4h").agg(agg).dropna(subset=["Close"])
    kural = ("W-SUN" if tur == "kripto" else "W-FRI") if tf == "H" else "ME"
    g = h.resample(kural).agg(agg)
    return g.dropna(subset=["Close"])


# =====================================================================
# GÖSTERGELER
# =====================================================================
def _wilder(s, n):
    """Wilder (RMA) yumuşatması: ilk değer ilk n gözlemin basit ortalaması, sonrası (önceki*(n-1)+yeni)/n.
    TradingView ve Investing.com'daki RSI/ATR/ADX ile aynı sonucu verir."""
    s = pd.Series(s, dtype=float); v = s.to_numpy(); out = np.full(len(v), np.nan)
    ok = np.flatnonzero(~np.isnan(v))
    if len(ok) < n: return pd.Series(out, index=s.index)
    i0 = ok[0]
    if np.isnan(v[i0:i0 + n]).any():   # aralıklı eksik veri: ileri doldurup devam et
        v = s.ffill().to_numpy()
    kuyruk = v[i0 + n - 1:].copy(); kuyruk[0] = v[i0:i0 + n].mean()
    out[i0 + n - 1:] = pd.Series(kuyruk).ewm(alpha=1.0 / n, adjust=False, ignore_na=True).mean().to_numpy()
    return pd.Series(out, index=s.index)


def rsi(c, n=14):
    d = c.diff().iloc[1:]; up = _wilder(d.clip(lower=0), n); dn = _wilder(-d.clip(upper=0), n)
    r = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    r = r.where(~((dn == 0) & (up > 0)), 100.0).where(~((dn == 0) & (up == 0)), 50.0)
    return r.reindex(c.index)


def atr(h, n=14):
    pc = h["Close"].shift()
    tr = pd.concat([h["High"] - h["Low"], (h["High"] - pc).abs(), (h["Low"] - pc).abs()], axis=1).max(axis=1, skipna=True)
    return _wilder(tr, n)


def adx(h, n=14):
    up = h["High"].diff().fillna(0); dn = (-h["Low"].diff()).fillna(0)
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=h.index)
    mdm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=h.index)
    a = atr(h, n)
    pdi = 100 * _wilder(pdm, n) / a; mdi = 100 * _wilder(mdm, n) / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return _wilder(dx, n), pdi, mdi


def psar(h, af0=0.02, af_max=0.2):
    hi, lo = h["High"].values, h["Low"].values; n = len(h)
    sar = np.zeros(n); yon = 1; af = af0; ep = hi[0]; sar[0] = lo[0]
    for i in range(1, n):
        sar[i] = sar[i - 1] + af * (ep - sar[i - 1])
        if yon == 1:
            sar[i] = min(sar[i], lo[i - 1], lo[i - 2] if i > 1 else lo[i - 1])
            if lo[i] < sar[i]:
                yon, sar[i], ep, af = -1, ep, lo[i], af0
            elif hi[i] > ep:
                ep, af = hi[i], min(af + af0, af_max)
        else:
            sar[i] = max(sar[i], hi[i - 1], hi[i - 2] if i > 1 else hi[i - 1])
            if hi[i] > sar[i]:
                yon, sar[i], ep, af = 1, ep, hi[i], af0
            elif lo[i] < ep:
                ep, af = lo[i], min(af + af0, af_max)
    return pd.Series(sar, index=h.index)


def supertrend(h, n=10, k=3.0):
    a = atr(h, n); hl2 = (h["High"] + h["Low"]) / 2
    ub = (hl2 + k * a).to_numpy(copy=True); lb = (hl2 - k * a).to_numpy(copy=True); c = h["Close"].to_numpy()
    st = np.full(len(h), np.nan); yon = np.ones(len(h))
    for i in range(1, len(h)):
        if np.isnan(ub[i - 1]): continue
        ub[i] = ub[i] if (ub[i] < ub[i - 1] or c[i - 1] > ub[i - 1]) else ub[i - 1]
        lb[i] = lb[i] if (lb[i] > lb[i - 1] or c[i - 1] < lb[i - 1]) else lb[i - 1]
        yon[i] = 1 if c[i] > ub[i - 1] else -1 if c[i] < lb[i - 1] else yon[i - 1]
        st[i] = lb[i] if yon[i] == 1 else ub[i]
    return pd.Series(st, index=h.index), pd.Series(yon, index=h.index)


def gostergeler(h):
    """Tüm gösterge serilerini hesaplar; DataFrame döndürür."""
    c, hi, lo, v = h["Close"], h["High"], h["Low"], h["Volume"]
    G = pd.DataFrame(index=h.index)
    for n in (5, 10, 20, 50, 100, 200):
        G[f"SMA{n}"] = c.rolling(n).mean(); G[f"EMA{n}"] = c.ewm(span=n, adjust=False).mean()
    G["RSI"] = rsi(c)
    ll, hh = lo.rolling(14).min(), hi.rolling(14).max()
    G["STOCH_K"] = (100 * (c - ll) / (hh - ll).replace(0, np.nan)).rolling(3).mean(); G["STOCH_D"] = G["STOCH_K"].rolling(3).mean()
    r = G["RSI"]; rl, rh = r.rolling(14).min(), r.rolling(14).max()
    G["STOCHRSI"] = (100 * (r - rl) / (rh - rl).replace(0, np.nan)).rolling(3).mean()
    e12, e26 = c.ewm(span=12, adjust=False).mean(), c.ewm(span=26, adjust=False).mean()
    G["MACD"] = e12 - e26; G["MACD_SIG"] = G["MACD"].ewm(span=9, adjust=False).mean(); G["MACD_HIST"] = G["MACD"] - G["MACD_SIG"]
    G["ADX"], G["PDI"], G["MDI"] = adx(h)
    tp = (hi + lo + c) / 3
    md = tp.rolling(20).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    G["CCI"] = (tp - tp.rolling(20).mean()) / (0.015 * md.replace(0, np.nan))
    G["WILLR"] = -100 * (hh - c) / (hh - ll).replace(0, np.nan)
    bp = c - pd.concat([lo, c.shift()], axis=1).min(axis=1)
    tr = pd.concat([hi, c.shift()], axis=1).max(axis=1) - pd.concat([lo, c.shift()], axis=1).min(axis=1)
    av = lambda n: bp.rolling(n).sum() / tr.rolling(n).sum().replace(0, np.nan)
    G["UO"] = 100 * (4 * av(7) + 2 * av(14) + av(28)) / 7
    G["ROC"] = 100 * (c / c.shift(12) - 1)
    G["MOM"] = c - c.shift(10)
    e13 = c.ewm(span=13, adjust=False).mean(); G["BULL"] = hi - e13; G["BEAR"] = lo - e13
    med = (hi + lo) / 2; G["AO"] = med.rolling(5).mean() - med.rolling(34).mean()
    G["ATR"] = atr(h)
    m20, s20 = c.rolling(20).mean(), c.rolling(20).std(ddof=0)
    G["BB_UST"], G["BB_ORTA"], G["BB_ALT"] = m20 + 2 * s20, m20, m20 - 2 * s20
    G["BB_GEN"] = (G["BB_UST"] - G["BB_ALT"]) / m20
    G["KC_UST"], G["KC_ALT"] = G["EMA20"] + 2 * G["ATR"], G["EMA20"] - 2 * G["ATR"]
    G["DC_UST"], G["DC_ALT"] = hi.rolling(20).max().shift(), lo.rolling(20).min().shift()
    t9 = (hi.rolling(9).max() + lo.rolling(9).min()) / 2; k26 = (hi.rolling(26).max() + lo.rolling(26).min()) / 2
    G["TENKAN"], G["KIJUN"] = t9, k26
    G["SPAN_A"] = ((t9 + k26) / 2).shift(26); G["SPAN_B"] = ((hi.rolling(52).max() + lo.rolling(52).min()) / 2).shift(26)
    G["PSAR"] = psar(h)
    G["ST"], G["ST_YON"] = supertrend(h)
    G["OBV"] = (np.sign(c.diff()).fillna(0) * v).cumsum()
    mf = tp * v; pos = mf.where(tp > tp.shift(), 0).rolling(14).sum(); neg = mf.where(tp < tp.shift(), 0).rolling(14).sum()
    G["MFI"] = (100 - 100 / (1 + pos / neg.replace(0, np.nan))).where(~((neg == 0) & (pos > 0)), 100.0)
    mfm = ((c - lo) - (hi - c)) / (hi - lo).replace(0, np.nan)
    G["CMF"] = (mfm * v).rolling(20).sum() / v.rolling(20).sum().replace(0, np.nan)
    n_ = 25
    G["AROON_UP"] = 100 * hi.rolling(n_ + 1).apply(lambda x: x.argmax(), raw=True) / n_
    G["AROON_DN"] = 100 * lo.rolling(n_ + 1).apply(lambda x: x.argmin(), raw=True) / n_
    e1 = c.ewm(span=15, adjust=False).mean(); e3 = e1.ewm(span=15, adjust=False).mean().ewm(span=15, adjust=False).mean()
    G["TRIX"] = 100 * e3.pct_change()
    G["VWMA20"] = (c * v).rolling(20).sum() / v.rolling(20).sum().replace(0, np.nan)
    G["HACIM_ORT"] = v.rolling(20).mean()
    return G


# =====================================================================
# OYLAMA ÖZETİ (hareketli ortalamalar + osilatörler)
# =====================================================================
def _son(s, i=-1):
    try:
        x = s.iloc[i]
        return None if pd.isna(x) else float(x)
    except Exception:
        return None


def oylama(h, G):
    c = float(h["Close"].iloc[-1]); ma, osc = [], []
    for t in ("SMA", "EMA"):
        for n in (5, 10, 20, 50, 100, 200):
            x = _son(G[f"{t}{n}"])
            if x is not None:
                ma.append((f"{t} {n}", x, "AL" if c > x else "SAT"))
    def ek(ad, deger, karar):
        if deger is not None: osc.append((ad, deger, karar))
    r = _son(G["RSI"])
    ek("RSI (14)", r, None if r is None else "SAT" if r > 70 else "AL" if r >= 50 else "AL" if r < 30 else "SAT")
    k, d = _son(G["STOCH_K"]), _son(G["STOCH_D"])
    ek("Stokastik (14,3,3)", k, None if k is None else "SAT" if k > 80 else "AL" if k < 20 else ("AL" if d is not None and k > d else "SAT"))
    s = _son(G["STOCHRSI"]); ek("Stokastik RSI", s, None if s is None else "SAT" if s > 80 else "AL" if s < 20 else "NÖTR")
    m, ms = _son(G["MACD"]), _son(G["MACD_SIG"]); ek("MACD (12,26,9)", m, None if m is None or ms is None else "AL" if m > ms else "SAT")
    a, p, n_ = _son(G["ADX"]), _son(G["PDI"]), _son(G["MDI"])
    ek("ADX (14)", a, None if a is None else "NÖTR" if a < 20 else "AL" if p > n_ else "SAT")
    cc = _son(G["CCI"]); ek("CCI (20)", cc, None if cc is None else "SAT" if cc > 200 else "AL" if cc < -200 else "AL" if cc > 0 else "SAT")
    w = _son(G["WILLR"]); ek("Williams %R", w, None if w is None else "SAT" if w > -20 else "AL" if w < -80 else "AL" if w > -50 else "SAT")
    u = _son(G["UO"]); ek("Ultimate Osilatör", u, None if u is None else "SAT" if u > 70 else "AL" if u < 30 else "AL" if u > 50 else "SAT")
    ro = _son(G["ROC"]); ek("ROC (12)", ro, None if ro is None else "AL" if ro > 0 else "SAT")
    mo = _son(G["MOM"]); ek("Momentum (10)", mo, None if mo is None else "AL" if mo > 0 else "SAT")
    bb_, be = _son(G["BULL"]), _son(G["BEAR"]); ek("Boğa/Ayı gücü", (bb_ or 0) + (be or 0), None if bb_ is None else "AL" if bb_ + be > 0 else "SAT")
    ao, ao1 = _son(G["AO"]), _son(G["AO"], -2)
    ek("Awesome Osilatör", ao, None if ao is None or ao1 is None else "AL" if ao > 0 and ao >= ao1 else "SAT" if ao < 0 and ao <= ao1 else "NÖTR")
    osc = [x for x in osc if x[2]]
    def skor(l):
        if not l: return 0.0
        return (sum(x[2] == "AL" for x in l) - sum(x[2] == "SAT" for x in l)) / len(l)
    sm, so = skor(ma), skor(osc)
    return {"ma": ma, "osc": osc, "ma_skor": sm, "osc_skor": so, "skor": 0.5 * sm + 0.5 * so,
            "ma_etiket": etiket(sm), "osc_etiket": etiket(so), "etiket": etiket(0.5 * sm + 0.5 * so),
            "sayim": {k_: sum(x[2] == k_ for x in ma + osc) for k_ in ("AL", "SAT", "NÖTR")}}


def etiket(s):
    return "GÜÇLÜ AL" if s > 0.5 else "AL" if s > 0.1 else "GÜÇLÜ SAT" if s < -0.5 else "SAT" if s < -0.1 else "NÖTR"


# =====================================================================
# MUM FORMASYONLARI
# =====================================================================
def mum_formasyonlari(h, G, son_n=3):
    o, hi, lo, c = (h[x].values for x in ("Open", "High", "Low", "Close"))
    n = len(c); bul = []
    if n < 10: return bul
    at = G["ATR"].values
    for i in range(max(n - son_n, 3), n):
        rng = hi[i] - lo[i]
        if rng <= 0: continue
        body = abs(c[i] - o[i]); ust = hi[i] - max(c[i], o[i]); alt = min(c[i], o[i]) - lo[i]
        egim = c[i - 1] - c[max(i - 6, 0)]; dusus, yukselis = egim < 0, egim > 0
        b1 = abs(c[i - 1] - o[i - 1]); yesil = c[i] > o[i]; yesil1 = c[i - 1] > o[i - 1]
        buyuk = lambda j: abs(c[j] - o[j]) > 0.6 * (at[j] if not np.isnan(at[j]) else (hi[j] - lo[j]))
        def ekle(ad, yon, aciklama, guc=1):
            bul.append({"ad": ad, "yon": yon, "tarih": h.index[i], "aciklama": aciklama, "guc": guc, "bar": i})
        if body <= 0.1 * rng:
            if alt > 2 * max(ust, 1e-12) and dusus: ekle("Yusufçuk doji", 1, "Düşüşte satıcıların gücünü kaybettiğine işaret eder.")
            elif ust > 2 * max(alt, 1e-12) and yukselis: ekle("Mezar taşı doji", -1, "Yükselişte alıcıların zayıfladığına işaret eder.")
            else: ekle("Doji", 0, "Kararsızlık mumu; yön teyidi beklenmeli.", 0)
        elif alt >= 2 * body and ust <= 0.35 * body + 0.1 * rng:
            if dusus: ekle("Çekiç", 1, "Düşüş sonrası alıcıların fiyatı geri ittiği dönüş mumu.", 2)
            elif yukselis: ekle("Asılı adam", -1, "Yükselişin sonunda satış baskısının başladığını gösterebilir.")
        elif ust >= 2 * body and alt <= 0.35 * body + 0.1 * rng:
            if yukselis: ekle("Kayan yıldız", -1, "Yükseliş sonrası satıcıların fiyatı geri ittiği dönüş mumu.", 2)
            elif dusus: ekle("Ters çekiç", 1, "Düşüşte alıcıların denemeye başladığını gösterir; teyit gerekir.")
        if body >= 0.95 * rng and buyuk(i):
            ekle("Marubozu (" + ("boğa" if yesil else "ayı") + ")", 1 if yesil else -1, "Gölgesiz güçlü mum; tek yönlü baskı.")
        if i >= 1:
            if yesil and not yesil1 and c[i] >= o[i - 1] and o[i] <= c[i - 1] and body > b1 and dusus:
                ekle("Yutan boğa", 1, "Yeşil mum önceki kırmızı mumu tamamen yuttu; güçlü dönüş sinyali.", 2)
            if not yesil and yesil1 and o[i] >= c[i - 1] and c[i] <= o[i - 1] and body > b1 and yukselis:
                ekle("Yutan ayı", -1, "Kırmızı mum önceki yeşil mumu tamamen yuttu; güçlü dönüş sinyali.", 2)
            if yesil and not yesil1 and o[i] > c[i - 1] and c[i] < o[i - 1] and body < 0.6 * b1 and dusus:
                ekle("Boğa haramisi", 1, "Büyük kırmızı mumun içinde küçük yeşil mum; düşüş yavaşlıyor.")
            if not yesil and yesil1 and o[i] < c[i - 1] and c[i] > o[i - 1] and body < 0.6 * b1 and yukselis:
                ekle("Ayı haramisi", -1, "Büyük yeşil mumun içinde küçük kırmızı mum; yükseliş yavaşlıyor.")
            if yesil and not yesil1 and o[i] < c[i - 1] and c[i] > (o[i - 1] + c[i - 1]) / 2 and c[i] < o[i - 1] and dusus:
                ekle("Delen çizgi", 1, "Aşağı açılıp önceki mumun yarısının üzerinde kapattı.")
            if not yesil and yesil1 and o[i] > c[i - 1] and c[i] < (o[i - 1] + c[i - 1]) / 2 and c[i] > o[i - 1] and yukselis:
                ekle("Kara bulut", -1, "Yukarı açılıp önceki mumun yarısının altında kapattı.")
            tol = 0.1 * (at[i] if not np.isnan(at[i]) else rng)
            if abs(lo[i] - lo[i - 1]) <= tol and dusus and yesil and not yesil1: ekle("Cımbız dip", 1, "Aynı seviyeden iki kez dönüş; destek teyidi.")
            if abs(hi[i] - hi[i - 1]) <= tol and yukselis and not yesil and yesil1: ekle("Cımbız tepe", -1, "Aynı seviyeden iki kez geri dönüş; direnç teyidi.")
            if hi[i] < hi[i - 1] and lo[i] > lo[i - 1]: ekle("İçeride çubuk (inside bar)", 0, "Sıkışma; kırılım yönü takip edilmeli.", 0)
            if hi[i] > hi[i - 1] and lo[i] < lo[i - 1] and buyuk(i):
                ekle("Dışarıda çubuk (outside bar)", 1 if yesil else -1, "Önceki mumun iki ucunu da aştı; volatil yön değişimi.")
        if i >= 2:
            k2 = abs(c[i - 1] - o[i - 1]) < 0.35 * abs(c[i - 2] - o[i - 2])
            if c[i - 2] < o[i - 2] and buyuk(i - 2) and k2 and yesil and c[i] > (o[i - 2] + c[i - 2]) / 2:
                ekle("Sabah yıldızı", 1, "Üç mumlu dip dönüş formasyonu.", 2)
            if c[i - 2] > o[i - 2] and buyuk(i - 2) and k2 and not yesil and c[i] < (o[i - 2] + c[i - 2]) / 2:
                ekle("Akşam yıldızı", -1, "Üç mumlu tepe dönüş formasyonu.", 2)
            if all(c[j] > o[j] and buyuk(j) for j in (i - 2, i - 1, i)) and c[i] > c[i - 1] > c[i - 2]:
                ekle("Üç beyaz asker", 1, "Art arda üç güçlü yeşil mum; alıcılar kontrolde.", 2)
            if all(c[j] < o[j] and buyuk(j) for j in (i - 2, i - 1, i)) and c[i] < c[i - 1] < c[i - 2]:
                ekle("Üç kara karga", -1, "Art arda üç güçlü kırmızı mum; satıcılar kontrolde.", 2)
    return bul


# =====================================================================
# PİVOT (SALINIM) NOKTALARI ve ZİGZAG
# =====================================================================
def salinimlar(h, G, esik_atr=1.5):
    """ATR tabanlı zigzag: anlamlı tepe (+1) ve dipleri (-1) sırayla döndürür: [(i, fiyat, tip)].
    Son eleman henüz onaylanmamış güncel uçtur."""
    hi, lo = h["High"].values, h["Low"].values; at = G["ATR"].bfill().values
    n = len(hi)
    if n < 10: return []
    piv = []; yon = 0; ext_hi, ihi, ext_lo, ilo = hi[0], 0, lo[0], 0; ext_p = ext_i = None
    for i in range(1, n):
        e = esik_atr * at[i]
        if yon == 0:
            if hi[i] > ext_hi: ext_hi, ihi = hi[i], i
            if lo[i] < ext_lo: ext_lo, ilo = lo[i], i
            if ext_hi - lo[i] > e and ihi < i:
                piv.append((ihi, ext_hi, 1)); yon, ext_p, ext_i = -1, lo[i], i
            elif hi[i] - ext_lo > e and ilo < i:
                piv.append((ilo, ext_lo, -1)); yon, ext_p, ext_i = 1, hi[i], i
        elif yon == 1:
            if hi[i] >= ext_p: ext_p, ext_i = hi[i], i
            elif ext_p - lo[i] > e:
                piv.append((ext_i, ext_p, 1)); yon, ext_p, ext_i = -1, lo[i], i
        else:
            if lo[i] <= ext_p: ext_p, ext_i = lo[i], i
            elif hi[i] - ext_p > e:
                piv.append((ext_i, ext_p, -1)); yon, ext_p, ext_i = 1, hi[i], i
    if yon != 0: piv.append((ext_i, ext_p, 1 if yon == 1 else -1))
    return piv


# =====================================================================
# DESTEK / DİRENÇ, FİBONACCİ, PİVOT NOKTALARI
# =====================================================================
def destek_direnc(h, G, piv, n_max=3, pencere=400):
    """Güncel fiyata göre en yakın destek ve dirençler: [(seviye, güç)].
    Adaylar: son `pencere` mumdaki onaylı salınım tepe/dipleri + son 20 ve 60 mumun en yüksek/en düşüğü.
    Birbirine 0,5 ATR'den yakın adaylar tek seviyede birleşir (küme ortalamasına göre; zincirleme büyüme yok).
    Güç = temas sayısı; yakın zamanda oluşan seviyeler önce gelir. Fiyata 0,25 ATR'den yakın seviyeler atlanır."""
    c = float(h["Close"].iloc[-1]); at = _son(G["ATR"]) or c * 0.02; tol = 0.5 * at; n = len(h)
    aday = [(float(p), i) for i, p, _ in piv[:-1] if i >= n - pencere]
    for k in (20, 60):
        if n > k:
            w = h.iloc[-k:]
            aday.append((float(w["High"].max()), n - k + int(w["High"].values.argmax())))
            aday.append((float(w["Low"].min()), n - k + int(w["Low"].values.argmin())))
    kume = []   # [toplam, adet, son_indeks]
    for p, i in sorted(aday):
        if kume and abs(p - kume[-1][0] / kume[-1][1]) <= tol:
            kume[-1][0] += p; kume[-1][1] += 1; kume[-1][2] = max(kume[-1][2], i)
        else:
            kume.append([p, 1, i])
    lv = [(k[0] / k[1], k[1]) for k in kume]
    dest = sorted([x for x in lv if x[0] < c - 0.25 * at], key=lambda x: -x[0])[:n_max]
    dir_ = sorted([x for x in lv if x[0] > c + 0.25 * at], key=lambda x: x[0])[:n_max]
    return {"destek": dest, "direnc": dir_}


def fibonacci(h, pencere):
    w = h.iloc[-pencere:]
    i_hi, i_lo = w["High"].values.argmax(), w["Low"].values.argmin()
    hi, lo = float(w["High"].iloc[i_hi]), float(w["Low"].iloc[i_lo])
    if hi <= lo: return None
    yukari = i_lo < i_hi  # dipten tepeye hareket: düzeltme seviyeleri tepeden aşağı ölçülür
    oran = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
    if yukari:
        sev = {r: hi - r * (hi - lo) for r in oran}; uz = {r: hi + (r - 1) * (hi - lo) for r in (1.272, 1.618)}
    else:
        sev = {r: lo + r * (hi - lo) for r in oran}; uz = {r: lo - (r - 1) * (hi - lo) for r in (1.272, 1.618)}
    c = float(h["Close"].iloc[-1])
    duz = (hi - c) / (hi - lo) if yukari else (c - lo) / (hi - lo)
    alt = max([v for v in list(sev.values()) + list(uz.values()) if v < c], default=None)
    ust = min([v for v in list(sev.values()) + list(uz.values()) if v > c], default=None)
    return {"yukari": yukari, "tepe": hi, "dip": lo, "tepe_t": w.index[i_hi], "dip_t": w.index[i_lo], "seviye": sev, "uzanti": uz,
            "duzeltme": duz, "alt": alt, "ust": ust}


def pivot_noktalari(h):
    """Son tamamlanan mumdan bir sonraki dönem için klasik ve Fibonacci pivotları."""
    H, L, C = (float(h[x].iloc[-1]) for x in ("High", "Low", "Close"))
    P = (H + L + C) / 3; R = H - L
    return {"Klasik": {"R3": H + 2 * (P - L), "R2": P + R, "R1": 2 * P - L, "P": P, "S1": 2 * P - H, "S2": P - R, "S3": L - 2 * (H - P)},
            "Fibonacci": {"R3": P + R, "R2": P + 0.618 * R, "R1": P + 0.382 * R, "P": P, "S1": P - 0.382 * R, "S2": P - 0.618 * R, "S3": P - R}}


# =====================================================================
# GRAFİK FORMASYONLARI
# =====================================================================
def _dogru(xs, ys):
    b, a = np.polyfit(xs, ys, 1)
    return b, a


def grafik_formasyonlari(h, G, piv, tf="G"):
    c = h["Close"].values; n = len(c); son = c[-1]; at = _son(G["ATR"]) or son * 0.02
    bul = []; cizim = []
    P = piv[:-1] if len(piv) > 1 else []   # onaylanmış salınımlar
    tep = [p for p in P if p[2] == 1]; dip = [p for p in P if p[2] == -1]
    def ekle(ad, yon, durum, aciklama, hedef=None, guc=2, cizgi=None):
        bul.append({"ad": ad, "yon": yon, "durum": durum, "aciklama": aciklama, "hedef": hedef, "guc": guc})
        if cizgi: cizim.append({"ad": ad, "yon": yon, **cizgi})
    tol = max(0.6 * at, 0.02 * son)
    # İkili tepe / dip
    if len(tep) >= 2 and len(dip) >= 1:
        t1, t2 = tep[-2], tep[-1]; ara = [d for d in dip if t1[0] < d[0] < t2[0]]
        if ara and abs(t1[1] - t2[1]) <= tol and n - t2[0] <= 40 and son <= max(t1[1], t2[1]) + 0.25 * at:
            boyun = min(d[1] for d in ara); yuk = max(t1[1], t2[1]) - boyun
            if yuk > 1.5 * at:
                d_ = "TEYİT (boyun çizgisi kırıldı)" if son < boyun else "oluşumda"
                ekle("İkili tepe", -1, d_, "Fiyat aynı direnci iki kez aşamadı.", boyun - yuk, 3 if son < boyun else 2,
                     {"x": [t1[0], t2[0]], "y": [t1[1], t2[1]], "yatay": boyun})
    if len(dip) >= 2 and len(tep) >= 1:
        d1, d2 = dip[-2], dip[-1]; ara = [t for t in tep if d1[0] < t[0] < d2[0]]
        if ara and abs(d1[1] - d2[1]) <= tol and n - d2[0] <= 40 and son >= min(d1[1], d2[1]) - 0.25 * at:
            boyun = max(t[1] for t in ara); yuk = boyun - min(d1[1], d2[1])
            if yuk > 1.5 * at:
                d_ = "TEYİT (boyun çizgisi kırıldı)" if son > boyun else "oluşumda"
                ekle("İkili dip", 1, d_, "Fiyat aynı desteği iki kez kıramadı.", boyun + yuk, 3 if son > boyun else 2,
                     {"x": [d1[0], d2[0]], "y": [d1[1], d2[1]], "yatay": boyun})
    # Omuz-baş-omuz / Ters OBO
    if len(tep) >= 3 and len(dip) >= 2:
        s1, b, s2 = tep[-3:]
        if b[1] > s1[1] + 0.5 * at and b[1] > s2[1] + 0.5 * at and abs(s1[1] - s2[1]) <= 1.5 * tol and n - s2[0] <= 50 and son < b[1]:
            lows = [d for d in dip if s1[0] < d[0] < s2[0]]
            if len(lows) >= 2:
                l1, l2 = lows[0], lows[-1]; eg = (l2[1] - l1[1]) / max(l2[0] - l1[0], 1); boyun = l2[1] + eg * (n - 1 - l2[0])
                yuk = b[1] - (l1[1] + eg * (b[0] - l1[0]))
                d_ = "TEYİT (boyun çizgisi kırıldı)" if son < boyun else "oluşumda"
                ekle("Omuz-baş-omuz (OBO)", -1, d_, "Klasik tepe dönüş formasyonu.", boyun - yuk, 3,
                     {"x": [s1[0], b[0], s2[0]], "y": [s1[1], b[1], s2[1]], "boyun": [(l1[0], l1[1]), (n - 1, boyun)]})
    if len(dip) >= 3 and len(tep) >= 2:
        s1, b, s2 = dip[-3:]
        if b[1] < s1[1] - 0.5 * at and b[1] < s2[1] - 0.5 * at and abs(s1[1] - s2[1]) <= 1.5 * tol and n - s2[0] <= 50 and son > b[1]:
            highs = [t for t in tep if s1[0] < t[0] < s2[0]]
            if len(highs) >= 2:
                h1, h2 = highs[0], highs[-1]; eg = (h2[1] - h1[1]) / max(h2[0] - h1[0], 1); boyun = h2[1] + eg * (n - 1 - h2[0])
                yuk = (h1[1] + eg * (b[0] - h1[0])) - b[1]
                d_ = "TEYİT (boyun çizgisi kırıldı)" if son > boyun else "oluşumda"
                ekle("Ters omuz-baş-omuz (TOBO)", 1, d_, "Klasik dip dönüş formasyonu.", boyun + yuk, 3,
                     {"x": [s1[0], b[0], s2[0]], "y": [s1[1], b[1], s2[1]], "boyun": [(h1[0], h1[1]), (n - 1, boyun)]})
    # Üçgen / kama / kanal (son 3'er salınımdan çizgi)
    T, D = tep[-3:], dip[-3:]
    if len(T) >= 2 and len(D) >= 2 and n - min(T[0][0], D[0][0]) <= 120:
        bu, au = _dogru([p[0] for p in T], [p[1] for p in T]); bl, al = _dogru([p[0] for p in D], [p[1] for p in D])
        ust_s, alt_s = bu * (n - 1) + au, bl * (n - 1) + al
        if ust_s > alt_s:
            nb = lambda b_: b_ / at  # bar başına ATR cinsinden eğim
            du, dl = nb(bu), nb(bl); yatay = 0.02
            gen_bas = (bu * min(T[0][0], D[0][0]) + au) - (bl * min(T[0][0], D[0][0]) + al); gen_son = ust_s - alt_s
            daralan = gen_son < 0.75 * gen_bas
            ad = yon = None
            if abs(du) <= yatay and dl > yatay and daralan: ad, yon = "Yükselen üçgen", 1
            elif abs(dl) <= yatay and du < -yatay and daralan: ad, yon = "Alçalan üçgen", -1
            elif du < -yatay and dl > yatay and daralan: ad, yon = "Simetrik üçgen", 0
            elif du > yatay and dl > yatay and daralan and dl > du: ad, yon = "Yükselen kama", -1
            elif du < -yatay and dl < -yatay and daralan and du < dl: ad, yon = "Alçalan kama", 1
            elif not daralan and abs(du - dl) <= 0.03:
                ad, yon = ("Yükselen kanal", 1) if du > yatay else ("Düşen kanal", -1) if du < -yatay else ("Yatay bant", 0)
            if ad:
                kirilim = son > ust_s + 0.1 * at; asagi = son < alt_s - 0.1 * at
                d_ = "YUKARI KIRILIM" if kirilim else "AŞAĞI KIRILIM" if asagi else "içinde"
                y_ = 1 if kirilim else -1 if asagi else yon
                hedef = (son + gen_bas) if kirilim else (son - gen_bas) if asagi else None
                aciklama = {"Yükselen üçgen": "Yatay direnç + yükselen dipler; genellikle yukarı kırılır.",
                            "Alçalan üçgen": "Yatay destek + alçalan tepeler; genellikle aşağı kırılır.",
                            "Simetrik üçgen": "Daralan sıkışma; kırılım yönü belirleyici.",
                            "Yükselen kama": "Daralan yükseliş; genellikle aşağı kırılır.",
                            "Alçalan kama": "Daralan düşüş; genellikle yukarı kırılır.",
                            "Yükselen kanal": "Paralel yükselen trend kanalı.", "Düşen kanal": "Paralel düşen trend kanalı.",
                            "Yatay bant": "Fiyat yatay bir aralıkta dalgalanıyor."}[ad]
                x0 = min(T[0][0], D[0][0])
                ekle(ad, y_, d_, aciklama, hedef, 3 if d_ != "içinde" else 2,
                     {"ust": [(x0, bu * x0 + au), (n - 1, ust_s)], "alt": [(x0, bl * x0 + al), (n - 1, alt_s)]})
    # Bayrak / flama: güçlü direk + dar konsolidasyon
    if n > 40:
        for L in (8, 12):
            kons = h.iloc[-L:]; direk = h.iloc[-L - 12:-L]
            hareket = float(direk["Close"].iloc[-1] - direk["Close"].iloc[0]); gen = float(kons["High"].max() - kons["Low"].min())
            if abs(hareket) > 4 * at and gen < 0.5 * abs(hareket):
                y_ = 1 if hareket > 0 else -1
                kir = (son > kons["High"].iloc[:-1].max()) if y_ == 1 else (son < kons["Low"].iloc[:-1].min())
                ekle("Boğa bayrağı" if y_ == 1 else "Ayı bayrağı", y_, "KIRILIM" if kir else "oluşumda",
                     "Sert hareket sonrası dar dinlenme; trend yönünde devam ihtimali.", son + y_ * abs(hareket), 3 if kir else 2)
                break
    # Donchian / 52 dönem zirve-dip kırılımı
    dc_u, dc_l = _son(G["DC_UST"]), _son(G["DC_ALT"])
    if dc_u and son > dc_u: ekle("20 dönem zirve kırılımı", 1, "KIRILIM", "Fiyat son 20 dönemin en yükseğini aştı.", None, 1)
    if dc_l and son < dc_l: ekle("20 dönem dip kırılımı", -1, "KIRILIM", "Fiyat son 20 dönemin en düşüğünün altına indi.", None, 1)
    yil = {"G": 252, "H": 52, "A": 12}.get(tf)
    if yil and n > yil + 5:
        if tf == "G" and pd.Series(h.index[-30:]).diff().dt.days.max() <= 1: yil = 365   # kripto: 7/24 işlem
        z52 = float(h["High"].iloc[-yil - 1:-1].max()); d52 = float(h["Low"].iloc[-yil - 1:-1].min())
        if son > z52: ekle("1 yıllık zirve aşıldı (52 hafta)", 1, "KIRILIM", "Fiyat son 1 yılın en yüksek seviyesinin üzerinde.", None, 2)
        if son < d52: ekle("1 yıllık dip kırıldı (52 hafta)", -1, "KIRILIM", "Fiyat son 1 yılın en düşük seviyesinin altında.", None, 2)
    # Trend çizgisi kırılımı
    if len(dip) >= 2:
        d1, d2 = dip[-2], dip[-1]
        if d2[1] > d1[1] and d2[0] > d1[0]:
            eg = (d2[1] - d1[1]) / (d2[0] - d1[0]); cz = d2[1] + eg * (n - 1 - d2[0])
            if son < cz - 0.2 * at and c[-2] >= cz - eg - 0.2 * at:
                ekle("Yükselen trend çizgisi kırıldı", -1, "KIRILIM", "Yükselen dipleri birleştiren çizginin altına inildi.", None, 2,
                     {"trend": [(d1[0], d1[1]), (n - 1, cz)]})
    if len(tep) >= 2:
        t1, t2 = tep[-2], tep[-1]
        if t2[1] < t1[1] and t2[0] > t1[0]:
            eg = (t2[1] - t1[1]) / (t2[0] - t1[0]); cz = t2[1] + eg * (n - 1 - t2[0])
            if son > cz + 0.2 * at and c[-2] <= cz - eg + 0.2 * at:
                ekle("Düşen trend çizgisi kırıldı", 1, "KIRILIM", "Alçalan tepeleri birleştiren çizginin üzerine çıkıldı.", None, 2,
                     {"trend": [(t1[0], t1[1]), (n - 1, cz)]})
    return bul, cizim


# =====================================================================
# PRICE ACTION
# =====================================================================
def price_action(h, G, piv):
    hi, lo, c = h["High"].values, h["Low"].values, h["Close"].values; n = len(c); son = c[-1]
    P = piv[:-1]; tep = [p for p in P if p[2] == 1]; dip = [p for p in P if p[2] == -1]
    o = {"yapi": "belirsiz", "olaylar": [], "fvg": [], "ob": None}
    if len(tep) >= 2 and len(dip) >= 2:
        yt, yd = tep[-1][1] > tep[-2][1], dip[-1][1] > dip[-2][1]
        o["yapi"] = ("YÜKSELEN (YT + YD)" if yt and yd else "DÜŞEN (AT + AD)" if not yt and not yd else "KARARSIZ / YATAY")
        o["yapi_yon"] = 1 if yt and yd else -1 if not yt and not yd else 0
        st, sd = tep[-1], dip[-1]
        if son > st[1]:
            o["olaylar"].append(("Yapı kırılımı yukarı (BOS)" if o["yapi_yon"] >= 0 else "Karakter değişimi yukarı (CHoCH)", 1,
                                 f"Son salınım tepesi {sayi(st[1])} aşıldı."))
        if son < sd[1]:
            o["olaylar"].append(("Yapı kırılımı aşağı (BOS)" if o["yapi_yon"] <= 0 else "Karakter değişimi aşağı (CHoCH)", -1,
                                 f"Son salınım dibi {sayi(sd[1])} kırıldı."))
        if hi[-1] > st[1] and son < st[1]: o["olaylar"].append(("Likidite avı (tepe)", -1, "Tepe üzeri stoplar alınıp geri dönüldü."))
        if lo[-1] < sd[1] and son > sd[1]: o["olaylar"].append(("Likidite avı (dip)", 1, "Dip altı stoplar alınıp geri dönüldü."))
    else:
        o["yapi_yon"] = 0
    # Doldurulmamış adil değer boşlukları (FVG)
    bas = max(2, n - 60)
    for i in range(bas, n):
        if lo[i] > hi[i - 2]:
            ust_, alt_ = lo[i], hi[i - 2]
            if lo[i + 1:].min(initial=np.inf) > alt_: o["fvg"].append(("Boğa FVG", alt_, ust_, h.index[i]))
        if hi[i] < lo[i - 2]:
            ust_, alt_ = lo[i - 2], hi[i]
            if hi[i + 1:].max(initial=-np.inf) < ust_: o["fvg"].append(("Ayı FVG", alt_, ust_, h.index[i]))
    o["fvg"] = sorted(o["fvg"], key=lambda x: abs((x[1] + x[2]) / 2 - son))[:3]
    # Basit emir bloğu: son yükselen yapı kırılımından önceki son kırmızı mum
    if tep:
        hedef_i = tep[-1][0]
        for j in range(hedef_i - 1, max(hedef_i - 15, 0), -1):
            if c[j] < h["Open"].values[j]:
                if lo[j + 1:].min(initial=np.inf) >= lo[j] and son > hi[j]:
                    o["ob"] = ("Boğa emir bloğu", lo[j], hi[j], h.index[j])
                break
    return o


# =====================================================================
# UYUMSUZLUKLAR ve KESİŞİMLER
# =====================================================================
def uyumsuzluklar(h, G, piv):
    bul = []; n = len(h)
    P = piv[:-1]; tep = [p for p in P if p[2] == 1][-2:]; dip = [p for p in P if p[2] == -1][-2:]
    for ad, s in (("RSI", G["RSI"]), ("MACD", G["MACD_HIST"])):
        if len(dip) == 2 and n - dip[1][0] <= 30:
            a, b = s.iloc[dip[0][0]], s.iloc[dip[1][0]]
            if dip[1][1] < dip[0][1] and b > a: bul.append((f"Pozitif uyumsuzluk ({ad})", 1, "Fiyat daha düşük dip yaptı ama gösterge yapmadı; düşüş ivmesi zayıflıyor."))
            if dip[1][1] > dip[0][1] and b < a: bul.append((f"Gizli pozitif uyumsuzluk ({ad})", 1, "Yükselen trendde devam sinyali."))
        if len(tep) == 2 and n - tep[1][0] <= 30:
            a, b = s.iloc[tep[0][0]], s.iloc[tep[1][0]]
            if tep[1][1] > tep[0][1] and b < a: bul.append((f"Negatif uyumsuzluk ({ad})", -1, "Fiyat daha yüksek tepe yaptı ama gösterge yapmadı; yükseliş ivmesi zayıflıyor."))
            if tep[1][1] < tep[0][1] and b > a: bul.append((f"Gizli negatif uyumsuzluk ({ad})", -1, "Düşen trendde devam sinyali."))
    return bul


def kesisimler(G, son_n=10):
    bul = []
    def kes(a, b, ad_al, ad_sat, guc):
        x, y = G[a], G[b]; d = (x - y).iloc[-son_n - 1:]
        if len(d.dropna()) < 2: return
        isaret = np.sign(d.dropna()); isaret = isaret[isaret != 0]
        degis = isaret.diff().fillna(0); kes_ = degis[degis != 0]
        if not len(kes_): return
        yon = 1 if kes_.iloc[-1] > 0 else -1
        if np.sign(d.iloc[-1]) != yon: return            # kesişim geri alınmış
        once = len(d) - 1 - list(d.index).index(kes_.index[-1])
        zaman = "son mumda" if once == 0 else f"{once} mum önce"
        bul.append((ad_al if yon > 0 else ad_sat, yon, f"Kesişim {zaman} gerçekleşti ve geçerliliğini koruyor.", guc))
    kes("SMA50", "SMA200", "Altın kesişim (SMA50 > SMA200)", "Ölüm kesişimi (SMA50 < SMA200)", 3)
    kes("EMA20", "EMA50", "EMA20 EMA50'yi yukarı kesti", "EMA20 EMA50'yi aşağı kesti", 2)
    kes("MACD", "MACD_SIG", "MACD al kesişimi", "MACD sat kesişimi", 1)
    kes("TENKAN", "KIJUN", "Ichimoku Tenkan/Kijun al kesişimi", "Ichimoku Tenkan/Kijun sat kesişimi", 1)
    st = G["ST_YON"].iloc[-son_n - 1:]; dg = st.diff(); dg = dg[dg.fillna(0) != 0]
    if len(dg) and np.sign(dg.iloc[-1]) == np.sign(st.iloc[-1]):
        if st.iloc[-1] > 0: bul.append(("SuperTrend al sinyaline döndü", 1, "Trend takip göstergesi yukarı döndü ve yönünü koruyor.", 2))
        else: bul.append(("SuperTrend sat sinyaline döndü", -1, "Trend takip göstergesi aşağı döndü ve yönünü koruyor.", 2))
    return bul


# =====================================================================
# BALİNA İZLERİ (büyük oyuncu hacmi)
# =====================================================================
def balina_serisi(h):
    """Her mum için balina göstergeleri (nedensel). Döner: DataFrame[k (hacim/medyan), tk (agresif alış oranı veya NaN),
    al, sat, emilim_al, emilim_sat]. Kripto (Binance) mumlarında gerçek agresif alış hacmi (taker) kullanılır;
    diğerlerinde mumun kapanış konumu yaklaşık olarak kullanılır."""
    o, hi, lo, c, v = (h[x].astype(float) for x in ("Open", "High", "Low", "Close", "Volume"))
    med = v.rolling(20, min_periods=10).median().shift()
    k = (v / med.replace(0, np.nan))
    rng = (hi - lo).replace(0, np.nan)
    clv = (c - lo) / rng; govde = (c - o).abs() / rng
    alt_f = (np.minimum(o, c) - lo) / rng; ust_f = (hi - np.maximum(o, c)) / rng
    tk = (h["TakerBuy"] / v.replace(0, np.nan)) if "TakerBuy" in h else pd.Series(np.nan, index=h.index)
    var_tk = tk.notna()
    buyuk = k >= 3
    al = buyuk & ((var_tk & (tk >= 0.58)) | (~var_tk & (clv >= 0.65) & (c > o)))
    sat = buyuk & ((var_tk & (tk <= 0.42)) | (~var_tk & (clv <= 0.35) & (c < o)))
    em_al = (k >= 2.5) & ~al & ~sat & (alt_f >= 0.5) & (govde <= 0.35)
    em_sat = (k >= 2.5) & ~al & ~sat & (ust_f >= 0.5) & (govde <= 0.35)
    return pd.DataFrame({"k": k, "tk": tk, "al": al.fillna(False), "sat": sat.fillna(False),
                         "emilim_al": em_al.fillna(False), "emilim_sat": em_sat.fillna(False)}, index=h.index)


def balina_izleri(h, G=None, son_n=5):
    """Son mumlardaki balina izleri: [(ad, yön, açıklama, güç)] ve özet sözlüğü."""
    if "Volume" not in h or h["Volume"].iloc[-60:].sum() <= 0 or len(h) < 30:
        return [], {"var": False}
    B = balina_serisi(h); bul = []
    gun_ici = len(h) > 10 and pd.Series(h.index[-11:]).diff().median() < pd.Timedelta(hours=20)
    fmt = "%d.%m %H:%M" if gun_ici else "%d.%m.%Y"
    for i in range(max(0, len(h) - son_n), len(h)):
        r = B.iloc[i]; t = h.index[i].strftime(fmt)
        if not (r["k"] == r["k"]): continue
        akis = f", işlemlerin %{r['tk'] * 100:.0f}'i agresif alış" if r["tk"] == r["tk"] else ""
        if r["al"]: bul.append(("Balina alımı", 1, f"{t}: hacim 20 dönem medyanının {tr(r['k'])} katı{akis}; büyük alıcı girişi.", 2))
        elif r["sat"]: bul.append(("Balina satışı", -1, f"{t}: hacim 20 dönem medyanının {tr(r['k'])} katı{akis}; büyük satıcı çıkışı.", 2))
        elif r["emilim_al"]: bul.append(("Alım emilimi (absorption)", 1, f"{t}: {tr(r['k'])} kat hacimle gelen satışlar karşılandı, uzun alt fitil.", 1))
        elif r["emilim_sat"]: bul.append(("Satış emilimi (dağıtım)", -1, f"{t}: {tr(r['k'])} kat hacimle gelen alışlar karşılandı, uzun üst fitil.", 1))
    # Sessiz birikim / dağıtım: fiyat yatayken hacim dengesi tek yöne akıyor
    c = h["Close"]; v = h["Volume"]
    if len(h) > 25:
        dp = float(c.iloc[-1] / c.iloc[-21] - 1)
        at = float(atr(h).iloc[-1]) / float(c.iloc[-1]) if G is None else float(G["ATR"].iloc[-1]) / float(c.iloc[-1])
        if "TakerBuy" in h and v.iloc[-20:].sum() > 0:
            denge = float((2 * h["TakerBuy"].iloc[-20:] - v.iloc[-20:]).sum() / v.iloc[-20:].sum()); kaynak = "agresif alış-satış farkı"
        else:
            ob = (np.sign(c.diff()).fillna(0) * v)
            denge = float(ob.iloc[-20:].sum() / v.iloc[-20:].sum()) if v.iloc[-20:].sum() > 0 else 0; kaynak = "OBV"
        esik = 0.12 if kaynak != "OBV" else 0.25
        if abs(dp) < 2.5 * at:
            if denge > esik: bul.append(("Sessiz birikim", 1, f"Son 20 mumda fiyat yatay (%{tr(dp * 100)}) ama {kaynak} alıcılardan yana (+{tr(denge, 2)}).", 1))
            elif denge < -esik: bul.append(("Sessiz dağıtım", -1, f"Son 20 mumda fiyat yatay (%{tr(dp * 100)}) ama {kaynak} satıcılardan yana ({tr(denge, 2)}).", 1))
    ozet = {"var": bool(bul), "k_son": float(B["k"].iloc[-1]) if B["k"].iloc[-1] == B["k"].iloc[-1] else None,
            "tk_son": float(B["tk"].iloc[-1]) if B["tk"].iloc[-1] == B["tk"].iloc[-1] else None,
            "net": sum(x[1] for x in bul)}
    return bul, ozet


# =====================================================================
# DURUM ÖZETİ (trend, momentum, volatilite, hacim)
# =====================================================================
def durumlar(h, G):
    c = float(h["Close"].iloc[-1]); S = []
    def ek(ad, deger, yorum, yon): S.append((ad, deger, yorum, yon))
    s50, s200 = _son(G["SMA50"]), _son(G["SMA200"])
    if s200: ek("Fiyat / SMA200", ("+" if c > s200 else "") + "%" + tr((c / s200 - 1) * 100), "Uzun vadeli trend yukarı" if c > s200 else "Uzun vadeli trend aşağı", 1 if c > s200 else -1)
    if s50: ek("Fiyat / SMA50", ("+" if c > s50 else "") + "%" + tr((c / s50 - 1) * 100), "Orta vadeli trend yukarı" if c > s50 else "Orta vadeli trend aşağı", 1 if c > s50 else -1)
    a, p, m = _son(G["ADX"]), _son(G["PDI"]), _son(G["MDI"])
    if a is not None: ek("ADX (trend gücü)", f"{a:.0f}", ("Güçlü trend" if a > 25 else "Zayıf / trendsiz piyasa") + (", alıcılar baskın" if p > m else ", satıcılar baskın"), 0 if a < 20 else (1 if p > m else -1))
    sa, sb = _son(G["SPAN_A"]), _son(G["SPAN_B"])
    if sa and sb:
        ust, alt = max(sa, sb), min(sa, sb)
        ek("Ichimoku bulutu", "Bulut üstü" if c > ust else "Bulut altı" if c < alt else "Bulut içi",
           "Olumlu trend bölgesi" if c > ust else "Olumsuz trend bölgesi" if c < alt else "Kararsız bölge", 1 if c > ust else -1 if c < alt else 0)
    st = _son(G["ST_YON"])
    if st is not None: ek("SuperTrend (10,3)", "AL" if st > 0 else "SAT", f"Takip seviyesi {sayi(_son(G['ST']))}", 1 if st > 0 else -1)
    ps = _son(G["PSAR"])
    if ps: ek("Parabolik SAR", f"{sayi(ps)}", "Fiyat SAR üzerinde (yükseliş)" if c > ps else "Fiyat SAR altında (düşüş)", 1 if c > ps else -1)
    au, ad_ = _son(G["AROON_UP"]), _son(G["AROON_DN"])
    if au is not None: ek("Aroon (25)", f"{au:.0f} / {ad_:.0f}", "Yükseliş trendi baskın" if au > ad_ else "Düşüş trendi baskın", 1 if au > ad_ else -1)
    bw = G["BB_GEN"].dropna()
    if len(bw) > 120:
        yuzde = float((bw.iloc[-120:] < bw.iloc[-1]).mean())
        ek("Bollinger genişliği", "%" + tr(bw.iloc[-1] * 100), "Sıkışma: sert hareket yaklaşabilir" if yuzde < 0.15 else "Genişlemiş volatilite" if yuzde > 0.85 else "Normal volatilite", 0)
    bu, bl_ = _son(G["BB_UST"]), _son(G["BB_ALT"])
    if bu and bl_:
        pb = (c - bl_) / (bu - bl_) if bu > bl_ else 0.5
        ek("Bollinger konumu (%B)", tr(pb, 2), "Üst bant dışında (aşırı uzama)" if pb > 1 else "Alt bant dışında (aşırı satım)" if pb < 0 else "Bant içinde", -1 if pb > 1 else 1 if pb < 0 else 0)
    at = _son(G["ATR"])
    if at: ek("ATR (14)", f"{sayi(at)} (%{at / c * 100:.1f})", "Ortalama dönemlik fiyat aralığı; stop mesafesi için kullanılır", 0)
    mfi = _son(G["MFI"])
    if mfi is not None and h["Volume"].iloc[-20:].sum() > 0:
        ek("MFI (para akışı)", f"{mfi:.0f}", "Aşırı alım" if mfi > 80 else "Aşırı satım" if mfi < 20 else ("Para girişi" if mfi > 50 else "Para çıkışı"), -1 if mfi > 80 else 1 if mfi < 20 else (1 if mfi > 50 else -1))
        cmf = _son(G["CMF"])
        if cmf is not None: ek("Chaikin para akışı", ("+" if cmf > 0 else "") + tr(cmf, 2), "Alıcı baskısı" if cmf > 0.05 else "Satıcı baskısı" if cmf < -0.05 else "Dengeli", 1 if cmf > 0.05 else -1 if cmf < -0.05 else 0)
        ob = G["OBV"];
        if len(ob) > 20: ek("OBV eğilimi (20)", "Yukarı" if ob.iloc[-1] > ob.iloc[-20] else "Aşağı", "Hacim fiyatı destekliyor" if (ob.iloc[-1] > ob.iloc[-20]) == (c > h["Close"].iloc[-20]) else "Hacim ile fiyat ayrışıyor", 1 if ob.iloc[-1] > ob.iloc[-20] else -1)
        vo, va = float(h["Volume"].iloc[-1]), _son(G["HACIM_ORT"])
        if va: ek("Hacim / 20 dönem ort.", tr(vo / va) + "x", "Ortalamanın çok üzerinde hacim" if vo > 1.8 * va else "Normal hacim" if vo > 0.6 * va else "Düşük hacim", 0)
    tr_ = _son(G["TRIX"])
    if tr_ is not None: ek("TRIX (15)", ("+" if tr_ > 0 else "") + tr(tr_, 3), "Pozitif momentum" if tr_ > 0 else "Negatif momentum", 1 if tr_ > 0 else -1)
    return S


# =====================================================================
# ANA ANALİZ
# =====================================================================
AYAR = {"1S": {"pencere_fib": 120, "goster": 120, "atr_k": 2.0}, "4S": {"pencere_fib": 120, "goster": 120, "atr_k": 1.7},
        "G": {"pencere_fib": 120, "goster": 130, "atr_k": 1.5}, "H": {"pencere_fib": 104, "goster": 110, "atr_k": 1.3},
        "A": {"pencere_fib": 96, "goster": 120, "atr_k": 1.0}}


def tf_analiz(h, tf):
    if len(h) < 30:
        return None
    G = gostergeler(h); piv = salinimlar(h, G, AYAR[tf]["atr_k"])
    oy = oylama(h, G); mum = mum_formasyonlari(h, G); form, cizim = grafik_formasyonlari(h, G, piv, tf)
    pa = price_action(h, G, piv); uy = uyumsuzluklar(h, G, piv); kes = kesisimler(G)
    sr = destek_direnc(h, G, piv); fib = fibonacci(h, min(AYAR[tf]["pencere_fib"], len(h))); pv = pivot_noktalari(h)
    dr = durumlar(h, G)
    # Sinyal listesi (yön: +1/-1/0, güç 0–3)
    sinyal = []
    for m in mum: sinyal.append(("Mum: " + m["ad"], m["yon"], m["aciklama"] + f" ({m['tarih']:%d.%m.%Y})", m["guc"]))
    for f in form:
        sinyal.append((f"Formasyon: {f['ad']} – {f['durum']}", f["yon"], f["aciklama"] + (f" Ölçülen hedef ≈ {sayi(f['hedef'])}." if f.get("hedef") else ""), f["guc"]))
    for ad, y, ac in pa["olaylar"]: sinyal.append(("Price action: " + ad, y, ac, 2))
    for ad, y, ac in uy: sinyal.append((ad, y, ac, 2))
    for ad, y, ac, g in kes: sinyal.append((ad, y, ac, g))
    try: bal, bal_oz = balina_izleri(h, G)
    except Exception: bal, bal_oz = [], {"var": False}
    for ad, y, ac, g in bal: sinyal.append(("Balina: " + ad, y, ac, g))
    net = sum(s[1] * s[3] for s in sinyal); toplam = sum(s[3] for s in sinyal if s[1] != 0) or 1
    pa_y = pa.get("yapi_yon", 0)
    puan = 50 + 50 * (0.55 * oy["skor"] + 0.30 * (net / toplam if sinyal else 0) + 0.15 * pa_y)
    puan = float(min(max(puan, 0), 100))
    return {"tf": tf, "h": h, "G": G, "piv": piv, "oy": oy, "mum": mum, "form": form, "cizim": cizim, "pa": pa, "uy": uy,
            "kes": kes, "balina": bal, "balina_ozet": bal_oz, "sr": sr, "fib": fib, "pivot": pv, "durum": dr, "sinyal": sinyal, "puan": puan,
            "etiket": puan_etiket(puan), "fiyat": float(h["Close"].iloc[-1]), "tarih": h.index[-1],
            "degisim": float(h["Close"].iloc[-1] / h["Close"].iloc[-2] - 1) if len(h) > 1 else None}


def puan_etiket(p):
    return "GÜÇLÜ AL" if p >= 75 else "AL" if p >= 58 else "GÜÇLÜ SAT" if p <= 25 else "SAT" if p <= 42 else "NÖTR"


def analiz_h(kod, ad, h, tur="hisse", para="₺", tfler=("G", "H", "A")):
    """Zaten indirilmiş günlük OHLCV üzerinden çok zaman dilimli analiz (ek veri çekmez)."""
    h = h[[c for c in ("Open", "High", "Low", "Close", "Volume") if c in h]].dropna(subset=["Close"]).copy()
    if "Volume" not in h: h["Volume"] = 0.0
    for c in ("Open", "High", "Low"):
        if c not in h: h[c] = h["Close"]
        h[c] = h[c].fillna(h["Close"])
    h["Volume"] = h["Volume"].fillna(0)
    s = {"kod": kod, "ad": ad, "tur": tur, "para": para, "tf": {}, "fiyat_zamani": h.index[-1]}
    for tf in tfler:
        try: s["tf"][tf] = tf_analiz(yeniden_ornekle(h, tf, tur), tf)
        except Exception: s["tf"][tf] = None
    ag = {"G": 0.3, "H": 0.4, "A": 0.3}
    v = [(ag[t], a["puan"]) for t, a in s["tf"].items() if a]
    s["puan"] = sum(w * p for w, p in v) / sum(w for w, _ in v) if v else None
    s["etiket"] = puan_etiket(s["puan"]) if s["puan"] is not None else "–"
    s["yorum"] = sade_yorum(s) if v else ""
    return s


def saatlik_veri(kod, tur):
    """1 saatlik OHLCV: kripto Binance/OKX, diğerleri Yahoo (60 dk, ~2 yıl)."""
    import bist_rapor as br
    if tur == "kripto":
        import bist_kripto as KR
        baz, par, borsa = KR.coz(kod)
        return KR.saatlik_mumlar(baz, par, borsa)[0]
    import yfinance as yf
    y, _ = yahoo_sembol(kod)
    h = yf.Ticker(y).history(period="730d", interval="60m", auto_adjust=True)
    if h is None or h.empty: raise ValueError("saatlik veri yok")
    try: h.index = h.index.tz_convert("America/New_York" if tur == "abd" else "Europe/Istanbul").tz_localize(None)
    except Exception: h = br._naive(h)
    return h[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"]).iloc[-2500:]


def analiz(kod, fiyat_fn=None, tfler=("G", "H", "A"), kisa_vade=False):
    import bist_varlik as V, bist_veri as bv
    kod = kod.upper().strip().replace(".IS", "")
    h, tur = gunluk_veri(kod, fiyat_fn)
    para_k = None
    if tur == "kripto":
        import bist_kripto as KR
        baz, par, borsa = KR.coz(kod)
        kod = KR.kod_yap(baz, par, borsa); para_k = "₺" if par == "TRY" else "$"
        ad = V.VARLIKLAR[baz][1] if baz in V.VARLIKLAR else KR.ESKI.get(baz, baz)
        ad = f"{ad} ({baz}/{par}{', ' + h.attrs['borsa'] if h.attrs.get('borsa') else ''})"
    else:
        import bist_abd as AB
        ad = V.VARLIKLAR[kod][1] if kod in V.VARLIKLAR else KURESEL[kod][1] if kod in KURESEL else AB.ad(kod) if tur == "abd" else \
            {"XU100": "BIST 100", "XU030": "BIST 30", "XBANK": "BIST Banka", "XHOLD": "BIST Holding"}.get(kod, bv.sirket_adi(kod))
    sonuc = {"kod": kod, "ad": ad, "tur": tur, "para": para_k or ("₺" if tur == "hisse" or kod == "GRAMALTIN" else "" if tur == "endeks" else "$"),
             "tf": {}, "fiyat_zamani": h.index[-1]}
    for tf in tfler:
        sonuc["tf"][tf] = tf_analiz(yeniden_ornekle(h, tf, tur), tf)
    if kisa_vade and not fiyat_fn:
        try:
            hs = saatlik_veri(kod, tur)
            tur_s = "hisse" if tur == "endeks" and kod.startswith("X") else tur
            for tf in ("1S", "4S"):
                sonuc["tf"][tf] = tf_analiz(yeniden_ornekle(hs, tf, tur_s), tf)
        except Exception as ex:
            sonuc["kisa_hata"] = str(ex)[:100]
    ag = {"G": 0.3, "H": 0.4, "A": 0.3}
    v = [(ag[t], a["puan"]) for t, a in sonuc["tf"].items() if a and t in ag]
    kv = [a["puan"] for t, a in sonuc["tf"].items() if a and t in ("1S", "4S")]
    sonuc["kisa_puan"] = float(np.mean(kv)) if kv else None
    sonuc["puan"] = sum(w * p for w, p in v) / sum(w for w, _ in v) if v else None
    sonuc["etiket"] = puan_etiket(sonuc["puan"]) if sonuc["puan"] is not None else "–"
    sonuc["yorum"] = sade_yorum(sonuc)
    return sonuc


def sade_yorum(s):
    t = s["tf"]; parca = []
    ad = {"G": "kısa vadede (günlük)", "H": "orta vadede (haftalık)", "A": "uzun vadede (aylık)"}
    for k in ("G", "H", "A"):
        if t.get(k): parca.append(f"{ad[k]} <b>{t[k]['etiket'].lower()}</b>")
    metin = f"{s['ad']} teknik olarak " + ", ".join(parca) + " görünümde. "
    g = t.get("G") or t.get("H")
    if g:
        en = sorted([x for x in g["sinyal"] if x[1] != 0], key=lambda x: -x[3])[:2]
        if en: metin += "Öne çıkan: " + "; ".join(x[0].split(": ", 1)[-1] for x in en) + ". "
        sr = g["sr"]; sv = []
        if sr["destek"]: sv.append(f"en yakın destek {sayi(sr['destek'][0][0])}")
        if sr["direnc"]: sv.append(f"en yakın direnç {sayi(sr['direnc'][0][0])}")
        if sv: metin += (", ".join(sv) + ".")[0].upper() + (", ".join(sv) + ".")[1:]
    return metin


def ozet_satir(s):
    """Toplu tarama için tek satır."""
    g, hf = s["tf"].get("G"), s["tf"].get("H")
    def adlar(a, yon, anahtar):
        if not a: return ""
        return ", ".join(x[0].split(": ", 1)[-1] for x in a["sinyal"] if x[1] == yon and x[0].startswith(anahtar))[:120]
    sat = {"Kod": s["kod"], "Ad": s["ad"], "Fiyat": g["fiyat"] if g else None, "Değişim": g["degisim"] if g else None,
           "Teknik puan": round(s["puan"], 1) if s["puan"] is not None else None, "Genel": s["etiket"],
           "Günlük": g["etiket"] if g else "–", "Haftalık": hf["etiket"] if hf else "–",
           "Aylık": s["tf"]["A"]["etiket"] if s["tf"].get("A") else "–",
           "RSI": _son(g["G"]["RSI"]) if g else None,
           "Formasyon +": adlar(g, 1, "Formasyon"), "Formasyon −": adlar(g, -1, "Formasyon"),
           "Mum +": adlar(g, 1, "Mum"), "Mum −": adlar(g, -1, "Mum"),
           "Kesişim/Uyumsuzluk": ", ".join(x[0] for x in (g["sinyal"] if g else []) if not x[0].startswith(("Mum", "Formasyon", "Price")))[:120],
           "Sinyal +": ", ".join(x[0] for x in (g["sinyal"] if g else []) if x[1] > 0 and not x[0].startswith(("Mum", "Formasyon", "Price")))[:120],
           "Sinyal −": ", ".join(x[0] for x in (g["sinyal"] if g else []) if x[1] < 0 and not x[0].startswith(("Mum", "Formasyon", "Price")))[:120],
           "Balina": ", ".join(x[0] for x in (g["balina"] if g else []))[:80],
           "Yapı": g["pa"]["yapi"] if g else "–",
           "Destek": g["sr"]["destek"][0][0] if g and g["sr"]["destek"] else None,
           "Direnç": g["sr"]["direnc"][0][0] if g and g["sr"]["direnc"] else None}
    sat["Kırılım"] = any(("KIRILIM" in x[0] or "TEYİT" in x[0] or "BOS" in x[0]) and x[1] > 0 for x in (g["sinyal"] if g else []))
    sat["Kırılım −"] = any(("KIRILIM" in x[0] or "TEYİT" in x[0] or "BOS" in x[0]) and x[1] < 0 for x in (g["sinyal"] if g else []))
    return sat
