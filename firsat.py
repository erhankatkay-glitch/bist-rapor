# -*- coding: utf-8 -*-
"""Fırsat motoru: kapanan mumda TAZE oluşan işlem kurulumlarını bulur, her biri için işlem planı
(giriş bölgesi, yapısal + ATR stop, 3 hedef, R oranları, süre), varlığa ve piyasaya özgü geçmiş testi,
çoklu zaman dilimi teyidi, balina izleri ve risk notlarıyla 0–100 puan üretir. Açık kurulumları da izler.

Tüm kurulum kuralları nedenseldir (yalnızca o mumdaki ve öncesindeki veriyi kullanır); canlı sinyal ile
geçmiş testi AYNI fonksiyondan çıkar. SAT (short) kurulumları fiyat ekseni aynalanarak aynı kurallarla bulunur."""
import math, json, os, datetime as dt
import numpy as np
import pandas as pd

import bist_teknik as T

# ------------------------------------------------------------------ sabitler
KURULUM = {
    "KIRILIM": ("Hacimli kırılım", "Hacimli aşağı kırılım",
                "Fiyat son 20 mumun zirvesini ortalamanın üzerindeki hacimle aştı ve mumun üst bölgesinde kapattı.",
                "Fiyat son 20 mumun dibini ortalamanın üzerindeki hacimle kırdı ve mumun alt bölgesinde kapattı."),
    "GERI": ("Trend içi geri çekilme", "Düşüş trendinde tepki satışı",
             "Yükselen trendde EMA20 bölgesine gelen geri çekilme alıcıyla karşılandı; önceki mumun tepesi aşıldı.",
             "Düşen trendde EMA20 bölgesine gelen tepki satıcıyla karşılandı; önceki mumun dibi kırıldı."),
    "SIKISMA": ("Sıkışma kırılımı", "Sıkışma aşağı kırılımı",
                "Bollinger bantları son 120 mumun en dar %20'lik bölgesine sıkıştıktan sonra fiyat üst bandın dışına çıktı.",
                "Bollinger bantları son 120 mumun en dar %20'lik bölgesine sıkıştıktan sonra fiyat alt bandın dışına çıktı."),
    "UYUMSUZ": ("Pozitif uyumsuzluklu dönüş", "Negatif uyumsuzluklu dönüş",
                "Fiyat daha düşük dip yaptı, RSI yapmadı (pozitif uyumsuzluk); ardından önceki mumun tepesini aşan onay mumu geldi.",
                "Fiyat daha yüksek tepe yaptı, RSI yapmadı (negatif uyumsuzluk); ardından önceki mumun dibini kıran onay mumu geldi."),
    "AVI": ("Likidite avı dönüşü", "Tepe likidite avı dönüşü",
            "Son 20 mumun dibinin altındaki stoplar alındı, fiyat aynı mumda dibin üzerine döndü (uzun alt fitil).",
            "Son 20 mumun tepesinin üzerindeki stoplar alındı, fiyat aynı mumda tepenin altına döndü (uzun üst fitil)."),
    "ST": ("SuperTrend al dönüşü", "SuperTrend sat dönüşü",
           "Trend takip göstergesi güçlü trend ortamında (ADX ≥ 20) yukarı döndü.",
           "Trend takip göstergesi güçlü trend ortamında (ADX ≥ 20) aşağı döndü."),
    "FORM": ("Formasyon kırılımı", "Formasyon aşağı kırılımı", "", ""),
}
DURUM_AD = {"TEYİT": "teyit", "YUKARI KIRILIM": "yukarı kırılım", "AŞAĞI KIRILIM": "aşağı kırılım", "KIRILIM": "kırılım"}
KALITE = {"FORM": 15, "UYUMSUZ": 12, "KIRILIM": 12, "GERI": 12, "SIKISMA": 10, "AVI": 10, "ST": 8}
DONUS = {"UYUMSUZ", "AVI"}                  # üst zaman dilimine ters de olabilir (karşı trend)
MAKS_BAR = {"4S": 30, "G": 20, "H": 12, "A": 8}
MAKS_RISK = {"4S": 0.08, "G": 0.12, "H": 0.20, "A": 0.30}   # girişten stopa en fazla uzaklık
GIRIS_BAR = {"4S": 2, "G": 2, "H": 1, "A": 1}
SURE_AD = {"4S": lambda n: f"{n} adet 4 saatlik mum", "G": lambda n: f"{n} günlük mum", "H": lambda n: f"{n} hafta",
           "A": lambda n: f"{n} ay"}
BAR_GUN = {("kripto", "4S"): 6, ("kripto", "G"): 1, ("bist", "4S"): 2 * 5 / 7, ("bist", "G"): 5 / 7,
           ("emtia", "4S"): 6 * 5 / 7, ("emtia", "G"): 5 / 7, ("abd", "4S"): 2 * 5 / 7, ("abd", "G"): 5 / 7}
UST_TF = {"4S": "G", "G": "H", "H": "A", "A": "H"}
AGIRLIK = (0.5, 0.3, 0.2)                   # H1/H2/H3'te kapatılan pozisyon payı
GECMIS_BAR = 1500
MIN_PUAN = 55
BEKLENEN_R_MIN = 0.02                       # geçmiş testte işlem başına beklenen sonuç bunun altındaysa fırsat sayılmaz
PIYASA_ONCEL = 15                           # varlık örneği azken piyasa geneli istatistiğine verilen ağırlık


# ------------------------------------------------------------------ biçim
def fy(x):
    """Fiyat biçimi: büyüklüğe göre ondalık, Türkçe ayraçlar."""
    if x is None or not np.isfinite(x): return "–"
    a = abs(x)
    if a >= 1: d = 2
    elif a == 0: d = 2
    else: d = min(10, max(4, 3 - int(math.floor(math.log10(a)))))
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def yz(x, d=1, isaret=True):
    if x is None or not np.isfinite(x): return "–"
    s = f"{x * 100:+.{d}f}" if isaret else f"{x * 100:.{d}f}"
    return ("%" + s).replace(".", ",") if not isaret else (s[0] + "%" + s[1:]).replace(".", ",").replace("-", "−")


def rr(x):
    return f"{x:.1f}R".replace(".", ",")


def rrs(x):
    return f"{x:+.2f}R".replace(".", ",").replace("-", "−")


# ------------------------------------------------------------------ diziler (aynalama ile tek yönlü kurallar)
def _kaydir(x, k=1):
    o = np.full_like(x, np.nan, dtype=float)
    if k < len(x): o[k:] = x[:-k]
    return o


def _rmin(x, n):
    return pd.Series(x).rolling(n, min_periods=1).min().to_numpy()


def diziler(h, G):
    """Kural motoru için numpy dizileri. Dönen sözlük hem AL (yon=1) hem aynalanmış SAT (yon=-1) için kullanılır."""
    A = {k: h[k].to_numpy(float) for k in ("Open", "High", "Low", "Close", "Volume")}
    for k in ("ATR", "EMA20", "EMA50", "SMA200", "RSI", "BB_UST", "BB_ALT", "BB_ORTA", "BB_GEN", "DC_UST", "DC_ALT", "ST", "ST_YON", "ADX"):
        A[k] = G[k].to_numpy(float)
    A["hacim_var"] = bool(np.nansum(A["Volume"][-60:]) > 0)
    B = T.balina_serisi(h) if A["hacim_var"] else None
    A["vk"] = B["k"].to_numpy(float) if B is not None else np.full(len(h), np.nan)
    A["b_al"] = (B["al"] | B["emilim_al"]).to_numpy(bool) if B is not None else np.zeros(len(h), bool)
    A["b_sat"] = (B["sat"] | B["emilim_sat"]).to_numpy(bool) if B is not None else np.zeros(len(h), bool)
    A["tk"] = B["tk"].to_numpy(float) if B is not None else np.full(len(h), np.nan)
    A["bw_q"] = G["BB_GEN"].rolling(120, min_periods=60).quantile(0.2).shift().to_numpy(float)
    A["idx"] = h.index
    return A


def ayna(A, yon):
    """yon=-1 için fiyatları ters çevirir: SAT kurulumu = aynalanmış serideki AL kurulumu."""
    if yon == 1: return A
    M = dict(A)
    M["Open"], M["Close"] = -A["Open"], -A["Close"]
    M["High"], M["Low"] = -A["Low"], -A["High"]
    for k in ("EMA20", "EMA50", "SMA200", "BB_ORTA", "ST"): M[k] = -A[k]
    M["BB_UST"], M["BB_ALT"] = -A["BB_ALT"], -A["BB_UST"]
    M["DC_UST"], M["DC_ALT"] = -A["DC_ALT"], -A["DC_UST"]
    M["ST_YON"] = -A["ST_YON"]; M["RSI"] = 100 - A["RSI"]
    M["b_al"], M["b_sat"] = A["b_sat"], A["b_al"]
    M["tk"] = 1 - A["tk"]
    return M


def tetikler(M):
    """Aynalanmış (veya AL) dizilerde kurulum maskeleri ve ham stoplar: {kod: (maske, stop)}."""
    O, H, L, C = M["Open"], M["High"], M["Low"], M["Close"]; at = M["ATR"]; n = len(C)
    rng = np.where(H - L > 0, H - L, np.nan)
    clv = (C - L) / rng; alt_f = (np.minimum(O, C) - L) / rng
    hv = lambda x: (M["vk"] >= x) if M["hacim_var"] else np.ones(n, bool)
    pC, pH = _kaydir(C), _kaydir(H)
    with np.errstate(invalid="ignore"):
        out = {}
        m = (C > M["DC_UST"]) & (pC <= _kaydir(M["DC_UST"])) & hv(1.5) & (clv >= 0.6) & (C > M["EMA50"])
        out["KIRILIM"] = (m, M["DC_UST"] - 0.75 * at)
        s200 = M["SMA200"]
        trend = (M["EMA20"] > M["EMA50"]) & ((M["EMA50"] > s200) | np.isnan(s200)) & (M["EMA50"] > _kaydir(M["EMA50"], 5))
        dokun = np.fmin(L, _kaydir(L)) <= M["EMA20"] + 0.3 * at
        m = trend & dokun & (C > M["EMA20"]) & (C > O) & (C > pH) & (M["RSI"] >= 40) & (M["RSI"] <= 65)
        out["GERI"] = (m, _rmin(L, 4) - 0.3 * at)
        m = (_kaydir(M["BB_GEN"]) <= _kaydir(M["bw_q"])) & (C > M["BB_UST"]) & (pC <= _kaydir(M["BB_UST"])) & hv(1.3)
        out["SIKISMA"] = (m, M["BB_ORTA"] - 0.25 * at)
        onceki = _kaydir(pd.Series(L).rolling(20, min_periods=10).min().to_numpy())
        m = (L < onceki) & (C > onceki) & (alt_f >= 0.45) & (clv >= 0.55) & hv(1.2)
        out["AVI"] = (m, L - 0.2 * at)
        m = (M["ST_YON"] > 0) & (_kaydir(M["ST_YON"]) < 0) & (M["ADX"] >= 20) & (C > M["EMA50"])
        out["ST"] = (m, M["ST"] - 0.2 * at)
        # Uyumsuzluklu dönüş (döngü; yalnızca onay mumu adaylarında)
        m = np.zeros(n, bool); st = np.full(n, np.nan); R = M["RSI"]
        aday = np.flatnonzero((C > O) & (C > pH) & (R < 55))
        for t in aday:
            if t < 50: continue
            i1 = t - 6 + int(np.argmin(L[t - 6:t]))
            if L[i1] > np.min(L[i1:t + 1]) + 1e-12: continue
            w0 = L[t - 45:t - 10]
            if len(w0) < 10: continue
            i0 = t - 45 + int(np.argmin(w0))
            if L[i1] < L[i0] and R[i1] > R[i0] + 3 and R[i0] < 35:
                m[t] = True; st[t] = L[i1] - 0.3 * at[t]
        out["UYUMSUZ"] = (m, st)
    # tekrarları ayıkla (son 3 mumda aynı kurulum varsa yeni sayma), risk aralığı 1–3,5 ATR
    for k, (m, stop) in out.items():
        m = np.nan_to_num(m.astype(float)).astype(bool)
        once = pd.Series(m).rolling(3, min_periods=1).max().shift().fillna(0).to_numpy(bool)
        m = m & ~once
        risk = C - stop
        stop = np.where(risk < at, C - at, stop)
        m = m & np.isfinite(stop) & (C - stop <= 3.5 * at) & np.isfinite(at) & (at > 0)
        out[k] = (m, stop)
    return out


# ------------------------------------------------------------------ geçmiş testi
def simule(H, L, C, t, giris, stop, rler, maks, O=None):
    """AL yönlü (aynalanmış) simülasyon. Aynı mumda stop ve hedef görülürse stop varsayılır (temkinli).
    Fiyat stopun altında açılırsa (boşluk) çıkış açılış fiyatından yapılır — gerçekçi kayıp.
    Döner (R, aşama, sebep) ya da ufuk tamamlanmadıysa None."""
    risk = giris - stop
    if risk <= 0: return None
    hed = [giris + r * risk for r in rler]
    R, kalan, asama, s = 0.0, 1.0, 0, stop
    n = len(C); son = min(t + maks, n - 1)
    for j in range(t + 1, son + 1):
        if L[j] <= s:
            cikis = min(s, O[j]) if O is not None and O[j] == O[j] else s
            return R + kalan * (cikis - giris) / risk, asama, ("başabaş" if asama else "stop")
        while asama < 3 and H[j] >= hed[asama]:
            R += AGIRLIK[asama] * rler[asama]; kalan -= AGIRLIK[asama]; asama += 1
            if asama == 1: s = giris
        if asama == 3: return R, 3, "hedef"
    if t + maks > n - 1: return None
    return R + kalan * (C[son] - giris) / risk, asama, "süre"


def _istat(sonuc):
    s = [x for x in sonuc if x]
    if not s: return {"n": 0}
    R = np.array([x[0] for x in s]); a = np.array([x[1] for x in s])
    return {"n": len(s), "p1": float((a >= 1).mean()), "p2": float((a >= 2).mean()), "ort_R": float(R.mean()),
            "kazanc": float((R > 0).mean())}


def gecmis_testi(M, maske, stop, tf, rler=(1.0, 2.0, 3.0), hariç_son=True):
    H, L, C, O = M["High"].tolist(), M["Low"].tolist(), M["Close"].tolist(), M["Open"].tolist()
    n = len(C); bas = max(60, n - GECMIS_BAR)
    idx = [t for t in np.flatnonzero(maske) if t >= bas and (not hariç_son or t < n - 1)]
    return _istat([simule(H, L, C, t, C[t], stop[t], rler, MAKS_BAR[tf], O) for t in idx])


class PiyasaIstatistik:
    """Tüm varlıkların geçmiş olaylarını birleştirir: (kurulum, yön, tf) → 1R/2R/3R merdiveniyle sonuçlar."""
    def __init__(self): self.d = {}
    def ekle(self, anahtar, sonuc): self.d.setdefault(anahtar, []).extend(sonuc)
    def al(self, anahtar): return _istat(self.d.get(anahtar, []))
    def tablo(self):
        return {f"{k[0]}|{k[1]}|{k[2]}": self.al(k) for k in self.d}


def piyasa_olaylari(M, tetik, tf):
    H, L, C, O = M["High"].tolist(), M["Low"].tolist(), M["Close"].tolist(), M["Open"].tolist()
    n = len(C); bas = max(60, n - GECMIS_BAR); out = {}
    for k, (m, stop) in tetik.items():
        idx = [t for t in np.flatnonzero(m) if bas <= t < n - 1]
        out[k] = [simule(H, L, C, t, C[t], stop[t], (1.0, 2.0, 3.0), MAKS_BAR[tf], O) for t in idx]
    return out


# ------------------------------------------------------------------ formasyon kırılımları (canlı + örneklemli geçmiş)
_FORM_DISLA = ("dönem", "1 yıllık")
_TAZE = ("TEYİT", "KIRILIM")


def _form_kirilimlari(h, G, atr_k, tf="G"):
    piv = T.salinimlar(h, G, atr_k)
    form, _ = T.grafik_formasyonlari(h, G, piv, tf)
    return [f for f in form if any(x in f["durum"] for x in _TAZE) and not any(x in f["ad"] for x in _FORM_DISLA)], piv


def form_tetik(a, tf):
    """Son mumda TAZE gerçekleşen formasyon kırılımları (bir önceki mumda yoktu)."""
    h, G = a["h"], a["G"]
    if len(h) < 60: return []
    k = T.AYAR[tf]["atr_k"]
    simdi, _ = _form_kirilimlari(h, G, k, tf)
    if not simdi: return []
    once, _ = _form_kirilimlari(h.iloc[:-1], G.iloc[:-1], k, tf)
    eski = {(f["ad"], f["yon"]) for f in once}
    return [f for f in simdi if (f["ad"], f["yon"]) not in eski and f["yon"] != 0]


def form_gecmisi(a, tf, yon, rler, adim=2, pencere=400):
    """Formasyon kırılımlarının bu varlıktaki geçmişi (yalnızca o güne kadarki veriyle, örneklemli)."""
    h, G = a["h"], a["G"]; n = len(h); k = T.AYAR[tf]["atr_k"]
    H, L, C = h["High"].to_numpy(float), h["Low"].to_numpy(float), h["Close"].to_numpy(float)
    O = h["Open"].to_numpy(float); at = G["ATR"].to_numpy(float)
    if yon == -1: H, L, C, O = -L, -H, -C, -O
    once = set(); sonuc = []
    for t in range(max(80, n - pencere), n - 1, adim):
        try: fl, piv = _form_kirilimlari(h.iloc[:t + 1], G.iloc[:t + 1], k, tf)
        except Exception: continue
        simdi = {(f["ad"], f["yon"]) for f in fl if f["yon"] == yon}
        yeni = simdi - once; once = simdi
        if not yeni: continue
        st = _form_stop(piv[:-1], yon, C[t] * (1 if yon == 1 else -1), at[t])
        if st is None: continue
        sonuc.append(simule(H.tolist(), L.tolist(), C.tolist(), t, C[t], st * (1 if yon == 1 else -1), rler, MAKS_BAR[tf], O.tolist()))
    return _istat(sonuc)


def _form_stop(piv, yon, fiyat, at):
    """Formasyon için yapısal stop: son onaylı karşı salınım ± 0,3 ATR; 1–3,5 ATR aralığına sığdırılır."""
    sal = [p for p in piv if p[2] == -yon]
    if not sal or not np.isfinite(at) or at <= 0: return None
    st = sal[-1][1] - yon * 0.3 * at
    risk = (fiyat - st) * yon
    if risk < at: st = fiyat - yon * at
    if (fiyat - st) * yon > 3.5 * at: st = fiyat - yon * 3.0 * at
    return st


# ------------------------------------------------------------------ hedefler
def hedef_adaylari(a, yon, giris, at):
    h = a["h"]; out = []
    def ek(p, et, tur):
        if p is not None and np.isfinite(p) and (p - giris) * yon > 0: out.append((float(p), et, tur))
    for p, n_ in (a["sr"]["direnc"] if yon == 1 else a["sr"]["destek"]):
        ek(p - yon * 0.1 * at, f"{'direnç' if yon == 1 else 'destek'} ({n_} temas)", "sr")
    C = h["Close"].to_numpy(float); n = len(C)
    for i, p, tip in a["piv"][:-1]:
        # yalnızca son ~250 mumdaki ve sonradan kapanışla aşılmamış (hâlâ geçerli) salınımlar
        if tip == yon and i >= n - 250 and i + 1 < n and ((C[i + 1:].max() < p) if yon == 1 else (C[i + 1:].min() > p)):
            ek(p - yon * 0.1 * at, f"önceki {'tepe' if yon == 1 else 'dip'} ({h.index[i]:%d.%m.%Y})", "sr")
    f = a.get("fib")
    if f:
        for r, p in f["seviye"].items():
            if 0 < r < 1: ek(p, f"Fib %{r * 100:.1f}".replace(".", ",").replace(",0", ""), "fib")
        for r, p in f["uzanti"].items(): ek(p, f"Fib uzantı %{r * 100:.1f}".replace(".", ","), "fib")
    if a["tf"] in ("4S", "G"):
        for k in ("R1", "R2", "R3") if yon == 1 else ("S1", "S2", "S3"):
            ek(a["pivot"]["Klasik"][k], f"pivot {k}", "pivot")
    yil = {"G": 365 if (pd.DatetimeIndex(h.index[-30:]).dayofweek >= 5).sum() > 4 else 252, "H": 52, "A": 12}.get(a["tf"])
    if yil and len(h) > yil:
        ek(float(h["High"].iloc[-yil:].max()) if yon == 1 else float(h["Low"].iloc[-yil:].min()),
           "1 yıllık zirve" if yon == 1 else "1 yıllık dip", "sr")
    return sorted(out, key=lambda x: (x[0] - giris) * yon)


def plan_kur(a, kod_k, yon, stop, olcu=None):
    """İşlem planı: giriş bölgesi, stop, 3 hedef (yapısal seviyeler; yoksa R hedefi), engeller."""
    h, G = a["h"], a["G"]
    giris = float(h["Close"].iloc[-1]); at = float(G["ATR"].iloc[-1]); risk = (giris - stop) * yon
    if not (risk > 0 and np.isfinite(risk)): return None
    ad = [(p, et, tur, (p - giris) * yon / risk) for p, et, tur in hedef_adaylari(a, yon, giris, at)]
    if olcu is not None and np.isfinite(olcu):
        d = (olcu - giris) * yon / risk
        if d > 0: ad.append((float(olcu), "formasyonun ölçtüğü hedef", "olcu", d))
    ad.sort(key=lambda x: x[3])
    engel = next((x for x in ad if x[2] == "sr" and 0.25 < x[3] < 0.9), None)
    def sec(lo, hi, tercih=None):
        if tercih:
            x = next((x for x in ad if x[2] == tercih and lo <= x[3] <= hi), None)
            if x: return x
        return next((x for x in ad if lo <= x[3] <= hi), None)
    def sentetik(r): return (giris + yon * r * risk, f"{rr(r)} hedefi", "R", r)
    h1 = sec(1.0, 2.2) or sentetik(1.5)
    h2 = (sec(max(h1[3] + 0.5, 1.8), 6.0, "olcu") if olcu else None) or sec(max(h1[3] + 0.5, 2.0), 4.5) or sentetik(max(h1[3] + 1.0, 2.5))
    h3 = sec(max(h2[3] + 0.6, 3.0), 7.0) or sentetik(max(h2[3] + 1.0, 3.5))
    # giriş bölgesi
    seviye = {"KIRILIM": a["G"]["DC_UST" if yon == 1 else "DC_ALT"].iloc[-1],
              "SIKISMA": a["G"]["BB_UST" if yon == 1 else "BB_ALT"].iloc[-1]}.get(kod_k)
    if seviye is not None and np.isfinite(seviye) and 0 < (giris - seviye) * yon <= 1.5 * at:
        bolge = sorted([float(seviye), giris])
    else:
        bolge = sorted([giris - yon * 0.3 * at, giris + yon * 0.1 * at])
    uzak = seviye is not None and np.isfinite(seviye) and (giris - seviye) * yon > 1.5 * at
    return {"giris": giris, "bolge": [float(x) for x in bolge], "stop": float(stop), "risk": float(risk), "atr": at,
            "hedef": [{"fiyat": float(x[0]), "etiket": x[1], "r": float(x[3])} for x in (h1, h2, h3)],
            "engel": {"fiyat": float(engel[0]), "etiket": engel[1], "r": float(engel[3])} if engel else None,
            "uzak": bool(uzak), "seviye": float(seviye) if seviye is not None and np.isfinite(seviye) else None}


# ------------------------------------------------------------------ ana tarama
def _blend(varlik, piyasa, alan="p1"):
    n = varlik.get("n", 0); pm = piyasa.get(alan) if piyasa.get("n", 0) >= 20 else 0.5
    if pm is None: pm = 0.5
    return ((varlik.get(alan) or 0) * n + pm * PIYASA_ONCEL) / (n + PIYASA_ONCEL)


def hafif(h, tf):
    """Ön tarama için yalnızca göstergeler (tam teknik analiz sadece kurulum bulunan varlıklarda yapılır)."""
    return {"h": h, "G": T.gostergeler(h), "tf": tf}


def varlik_tara(v, tf, yonler, pist, olay_topla=True):
    """Tek varlık, tek zaman dilimi. v: {kod, ad, para, a (tf_analiz ya da hafif), ust | ust_fn, rs, ...}.
    Son mumdaki taze kurulumları döndürür; ayrıca piyasa istatistiğine geçmiş olayları ekler."""
    a = v["a"]
    if a is None or len(a["h"]) < 80: return []
    A = diziler(a["h"], a["G"]); n = len(A["Close"]); son = n - 1
    bulunan = []
    for yon in yonler:
        M = ayna(A, yon); tet = tetikler(M)
        if olay_topla:
            for k, s in piyasa_olaylari(M, tet, tf).items(): pist.ekle((k, yon, tf), s)
        for k, (m, stop) in tet.items():
            if m[son]: bulunan.append({"kod_k": k, "yon": yon, "stop": float(stop[son]) * yon, "M": M, "tet": (m, stop)})
    # formasyon kırılımları
    try:
        for f in form_tetik(a, tf):
            if f["yon"] not in yonler: continue
            piv = a.get("piv") or T.salinimlar(a["h"], a["G"], T.AYAR[tf]["atr_k"])
            st = _form_stop(piv[:-1], f["yon"], float(a["h"]["Close"].iloc[-1]), float(a["G"]["ATR"].iloc[-1]))
            if st is not None: bulunan.append({"kod_k": "FORM", "yon": f["yon"], "stop": st, "form": f})
    except Exception:
        pass
    return bulunan


def degerlendir(v, tf, bulunan, pist, piyasa):
    """Aynı varlıktaki kurulumları yön bazında birleştirir, plan kurar, geçmişi test eder, puanlar."""
    a = v["a"]; out = []
    for yon in (1, -1):
        ks = [b for b in bulunan if b["yon"] == yon]
        if not ks: continue
        # en sıkı (en yakın) geçerli stop yerine en anlamlı kurulumun stopu: kaliteye göre sırala
        ks.sort(key=lambda b: -KALITE[b["kod_k"]])
        ana = ks[0]; form = next((b["form"] for b in ks if b["kod_k"] == "FORM"), None)
        p = plan_kur(a, ana["kod_k"], yon, ana["stop"], form.get("hedef") if form else None)
        if not p or p["risk"] / p["giris"] > MAKS_RISK[tf]: continue   # stop çok uzak: bu zaman dilimi için makul değil
        rler = tuple(round(x["r"], 2) for x in p["hedef"])
        # geçmiş: bu varlıkta aynı kurulum, bu planın R hedefleriyle
        if ana["kod_k"] == "FORM":
            try: vt = form_gecmisi(a, tf, yon, rler)
            except Exception: vt = {"n": 0}
        else:
            M = ana["M"]; m, st = ana["tet"]
            vt = gecmis_testi(M, m, st, tf, rler)
        pm = pist.al((ana["kod_k"], yon, tf)) if ana["kod_k"] != "FORM" else {"n": 0}
        p1 = _blend(vt, pm, "p1"); ortR = _blend(vt, pm, "ort_R") if (vt.get("n") or pm.get("n", 0) >= 20) else 0.0
        # Kalite kapısı: geçmişte (bu varlık + piyasa geneli harmanı) ortalama sonucu pozitif olmayan kurulum gönderilmez.
        if ortR <= BEKLENEN_R_MIN: continue
        # teyitler
        G = a["G"]; c = p["giris"]; at = p["atr"]
        if "ust" not in v and v.get("ust_fn"):
            try: v["ust"] = v["ust_fn"]()
            except Exception: v["ust"] = None
        ust = v.get("ust"); ust_puan = ust["puan"] if ust else None
        if ust_puan is not None:
            ters = (ust_puan < 35) if yon == 1 else (ust_puan > 65)
            if ters and ana["kod_k"] not in DONUS: continue
        else:
            ters = False
        rsi = float(G["RSI"].iloc[-1]); adx = float(G["ADX"].iloc[-1]); vk = float(ana["M"]["vk"][-1]) if "M" in ana else float(diziler(a["h"], G)["vk"][-1])
        bal, bal_oz = a.get("balina") or [], a.get("balina_ozet") or {}
        bal_yon = sum(x[1] for x in bal)
        e50, s200 = float(G["EMA50"].iloc[-1]), float(G["SMA200"].iloc[-1]) if np.isfinite(G["SMA200"].iloc[-1]) else None
        trend_uyum = (c - e50) * yon > 0 and (s200 is None or (e50 - s200) * yon > 0)
        # puan
        s_bt = float(np.clip((p1 - 0.35) / 0.35, 0, 1)) * 15 + float(np.clip(ortR / 0.40, 0, 1)) * 15
        s_mtf = (float(np.clip(((ust_puan - 40) if yon == 1 else (60 - ust_puan)) / 35, 0, 1)) * 20) if ust_puan is not None else 10
        s_tf = float(np.clip(((a["puan"] - 45) if yon == 1 else (55 - a["puan"])) / 35, 0, 1)) * 10
        s_hb = (float(np.clip((vk - 1) / 2, 0, 1)) * 8 if np.isfinite(vk) else 4) + (7 if bal_yon * yon > 0 else -7 if bal_yon * yon < 0 else 0)
        s_tr = (5 if trend_uyum else 0) + (5 if adx >= 20 else 2 if adx >= 15 else 0)
        s_k = KALITE[ana["kod_k"]] + min(5, 3 * (len(ks) - 1))
        riskler, ceza = [], 0
        if (rsi >= 75 and yon == 1) or (rsi <= 25 and yon == -1):
            riskler.append(f"RSI {rsi:.0f}: kısa vadede {'aşırı alım' if yon == 1 else 'aşırı satım'} bölgesinde"); ceza += 8
        if p["engel"]:
            riskler.append(f"{fy(p['engel']['fiyat'])} seviyesinde {p['engel']['etiket']} H1'den önce engel ({rr(p['engel']['r'])})"); ceza += 10
        uzak_e20 = (c - float(G["EMA20"].iloc[-1])) * yon / at
        if uzak_e20 > 3: riskler.append(f"Fiyat EMA20'den {uzak_e20:.1f} ATR uzaklaşmış; geri çekilme riski".replace(".", ",")); ceza += 5
        if p["uzak"]: riskler.append(f"Fiyat kırılım seviyesinden ({fy(p['seviye'])}) uzaklaştı; bu bölgeye geri çekilmede giriş daha iyi risk/ödül sağlar")
        if bal_yon * yon < 0: riskler.append("Balina izleri ters yönde")
        if ters: riskler.append(f"Üst zaman dilimi ({T.TF_AD[UST_TF[tf]].lower()}) ters yönde: karşı trend işlem, pozisyon küçük tutulmalı")
        if vt.get("n", 0) and vt.get("ort_R", 0) < 0: riskler.append(f"Bu varlıkta bu kurulumun geçmiş ortalaması negatif ({rrs(vt['ort_R'])})"); ceza += 6
        puan = float(np.clip(s_bt + s_mtf + s_tf + s_hb + s_tr + s_k - ceza, 0, 100))
        teyit = []
        if ust_puan is not None:
            teyit.append((f"{T.TF_AD[UST_TF[tf]]} {T.puan_etiket(ust_puan)} ({ust_puan:.0f})", (ust_puan >= 50) == (yon == 1)))
        teyit.append((f"{T.TF_AD[tf]} puanı {a['puan']:.0f}", (a["puan"] >= 50) == (yon == 1)))
        if np.isfinite(vk): teyit.append((f"Hacim {vk:.1f}x".replace(".", ","), vk >= 1.5))
        teyit.append((f"RSI {rsi:.0f}", (50 <= rsi < 75) if yon == 1 else (25 < rsi <= 50)))
        teyit.append((f"ADX {adx:.0f}", adx >= 20))
        if trend_uyum: teyit.append(("EMA50/SMA200 trend uyumlu", True))
        if v.get("rs") is not None: teyit.append((f"RS {v['rs']:.0f}", (v["rs"] >= 60) if yon == 1 else (v["rs"] <= 40)))
        adlar = []
        for b in ks:
            if b["kod_k"] == "FORM": adlar.append(f"{b['form']['ad']} – {DURUM_AD.get(b['form']['durum'].split(' (')[0], 'kırılım')}")
            else: adlar.append(KURULUM[b["kod_k"]][0 if yon == 1 else 1])
        aciklama = (form["aciklama"] if ana["kod_k"] == "FORM" else KURULUM[ana["kod_k"]][2 if yon == 1 else 3])
        out.append({"kod": v["kod"], "ad": v.get("ad", v["kod"]), "para": v.get("para", ""), "piyasa": piyasa, "tf": tf, "yon": yon,
                    "kurulum": ana["kod_k"], "kurulum_ad": " + ".join(dict.fromkeys(adlar)), "aciklama": aciklama,
                    "plan": p, "puan": round(puan, 1), "gecmis": vt, "piyasa_gecmis": pm, "p1_harman": p1, "beklenen_R": ortR,
                    "teyit": teyit, "risk": riskler, "balina": [(x[0], x[1], x[2]) for x in bal], "balina_ozet": bal_oz,
                    "ust_puan": ust_puan, "rsi": rsi, "adx": adx, "hacim_k": vk if np.isfinite(vk) else None,
                    "mum": a["tarih"].isoformat() if hasattr(a["tarih"], "isoformat") else str(a["tarih"]),
                    "ekstra": {}})
    return out


def tara(varliklar, tf, piyasa, yonler=(1,), adet=5, min_puan=MIN_PUAN, ilerleme=None):
    """varliklar: [{kod, ad, para, a, ust, rs}] → (seçilen fırsatlar, tüm adaylar, piyasa istatistiği)."""
    pist = PiyasaIstatistik(); bulunanlar = []
    for i, v in enumerate(varliklar):
        try:
            b = varlik_tara(v, tf, yonler, pist)
            if b: bulunanlar.append((v, b))
        except Exception as ex:
            if ilerleme: ilerleme(f"{v.get('kod')}: {str(ex)[:60]}")
    adaylar = []
    for v, b in bulunanlar:
        try:
            if "sr" not in v["a"]: v["a"] = T.tf_analiz(v["a"]["h"], tf)   # hafif ön tarama → tam analiz
            adaylar += degerlendir(v, tf, b, pist, piyasa)
        except Exception as ex:
            if ilerleme: ilerleme(f"{v.get('kod')} değerlendirme: {str(ex)[:60]}")
    adaylar.sort(key=lambda x: -x["puan"])
    secilen = [x for x in adaylar if x["puan"] >= min_puan][:adet]
    return secilen, adaylar, pist


# ------------------------------------------------------------------ açık kurulum takibi
def kayit(f, simdi):
    """Seçilen fırsatı takip kaydına çevirir. Zamanlar mum verisinin saat dilimindedir (kripto UTC, BIST TSİ, emtia UTC)."""
    p = f["plan"]; tf = f["tf"]
    mum = pd.Timestamp(f["mum"])
    # Mum etiketi: 4S/G başlangıç, H/A (pandas W/ME) bitiş günüdür
    kapanis = mum + {"4S": pd.Timedelta(hours=4), "G": pd.Timedelta(days=1), "H": pd.Timedelta(days=1), "A": pd.Timedelta(days=1)}[tf]
    if tf in ("H", "A"): gun = MAKS_BAR[tf] * (7 if tf == "H" else 30.5)
    else: gun = MAKS_BAR[tf] / BAR_GUN.get((f["piyasa"], tf), 1)
    kid = f"{f['piyasa']}-{f['kod']}-{tf}-{'AL' if f['yon'] == 1 else 'SAT'}-{mum:%Y%m%d%H%M}"
    return {"id": kid, "piyasa": f["piyasa"], "kod": f["kod"], "ad": f["ad"], "para": f["para"], "tf": tf, "yon": f["yon"],
            "kurulum": f["kurulum_ad"], "puan": f["puan"], "giris": p["giris"], "stop": p["stop"], "stop_ilk": p["stop"],
            "risk": float(p["risk"]), "hedef": [float(x["fiyat"]) for x in p["hedef"]], "r": [float(x["r"]) for x in p["hedef"]],
            "olusma": kapanis.isoformat(), "son_kontrol": kapanis.isoformat(),
            "bitis": (kapanis + pd.Timedelta(days=gun)).isoformat(),
            "acilis_utc": simdi.isoformat(), "durum": "açık", "asama": 0, "R": 0.0, "kalan": 1.0, "son_fiyat": p["giris"]}


def ilerlet(k, bars, simdi):
    """Açık kaydı yeni mumlarla ilerletir. bars: index=mum başlangıcı (kaydın saat dilimiyle aynı), High/Low/Close.
    Döner: olay listesi [(tür, metin)]."""
    olay = []
    if k["durum"] != "açık": return olay
    yon = k["yon"]; g = k["giris"]; risk = k["risk"]
    son = pd.Timestamp(k["son_kontrol"])
    if bars is not None and len(bars):
        sure = pd.Series(bars.index[-50:]).diff().median() if len(bars) > 2 else pd.Timedelta(hours=1)
        sure = min(sure if pd.notna(sure) else pd.Timedelta(hours=1), pd.Timedelta(hours=4))
        b = bars[(bars.index >= son) & (bars.index + sure <= pd.Timestamp(simdi))]   # bitmemiş mum işlenmez
        for t, r in b.iterrows():
            hi, lo = (r["High"], r["Low"]) if yon == 1 else (-r["Low"], -r["High"])
            s = k["stop"] * yon; gg = g * yon
            if lo <= s:
                op = r.get("Open", np.nan); op = op * yon if op == op else np.nan
                cikis = min(s, op) if op == op else s            # stopun altında açıldıysa açılıştan çıkış
                k["R"] += k["kalan"] * (cikis - gg) / risk; k["kalan"] = 0
                k["durum"] = "kapandı"; k["sebep"] = "başabaş (H1 sonrası stop girişte)" if k["asama"] else "stop"
                k["kapanis"] = str(t); k["cikis"] = float(cikis * yon)
                olay.append(("stop" if not k["asama"] else "basabas", k["sebep"])); break
            while k["asama"] < 3 and hi >= k["hedef"][k["asama"]] * yon:
                i = k["asama"]; k["R"] += AGIRLIK[i] * k["r"][i]; k["kalan"] -= AGIRLIK[i]; k["asama"] += 1
                olay.append((f"H{i + 1}", f"H{i + 1} ({fy(k['hedef'][i])}) görüldü"))
                if k["asama"] == 1: k["stop"] = g
            if k["asama"] == 3:
                k["durum"] = "kapandı"; k["sebep"] = "tüm hedefler"; k["kapanis"] = str(t); k["cikis"] = k["hedef"][2]; break
            k["son_fiyat"] = float(r["Close"])
        if len(b): k["son_kontrol"] = str(b.index[-1] + sure)
    if k["durum"] == "açık" and simdi >= pd.Timestamp(k["bitis"]):
        c = k["son_fiyat"]
        k["R"] += k["kalan"] * (c - g) * yon / risk; k["kalan"] = 0
        k["durum"] = "kapandı"; k["sebep"] = "süre doldu"; k["kapanis"] = str(simdi); k["cikis"] = c
        olay.append(("sure", "süre doldu, son fiyattan kapatıldı"))
    return olay


def getiri(k):
    return k["R"] * k["risk"] / k["giris"]


# ------------------------------------------------------------------ grafik
def grafik(f, a, dosya, n=90):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    h = a["h"].iloc[-n:]; G = a["G"].iloc[-n:]; p = f["plan"]; yon = f["yon"]
    x = np.arange(len(h)); ileri = 14
    fig, ax = plt.subplots(figsize=(7.2, 4.1), dpi=90)
    fig.patch.set_facecolor("white")
    yuk = h["Close"] >= h["Open"]
    w = 0.62
    for i, (o, hi, lo, c, u) in enumerate(zip(h["Open"], h["High"], h["Low"], h["Close"], yuk)):
        col = "#16a34a" if u else "#dc2626"
        ax.vlines(i, lo, hi, color=col, lw=0.8)
        ax.add_patch(Rectangle((i - w / 2, min(o, c)), w, max(abs(c - o), 1e-12), color=col, lw=0))
    ax.plot(x, G["EMA20"], color="#f59e0b", lw=1.0, label="EMA20")
    ax.plot(x, G["EMA50"], color="#6366f1", lw=1.0, label="EMA50")
    if G["SMA200"].notna().any(): ax.plot(x, G["SMA200"], color="#64748b", lw=1.0, ls="--", label="SMA200")
    x0, x1 = len(h) - 1, len(h) - 1 + ileri
    g, s = p["giris"], p["stop"]; hd = [z["fiyat"] for z in p["hedef"]]
    ax.add_patch(Rectangle((x0, min(g, s)), ileri, abs(g - s), color="#dc2626", alpha=0.10, lw=0))
    ax.add_patch(Rectangle((x0, min(g, hd[-1])), ileri, abs(hd[-1] - g), color="#16a34a", alpha=0.07, lw=0))
    def cizgi(y, renk, et, ls="-"):
        ax.hlines(y, x0 - 8, x1, color=renk, lw=1.1, ls=ls)
        ax.text(x1 + 0.3, y, f" {et} {fy(y)}", va="center", fontsize=7.5, color=renk, fontweight="bold")
    cizgi(g, "#1d4ed8", "Giriş"); cizgi(s, "#dc2626", "Stop")
    for i_, y in enumerate(hd): cizgi(y, "#15803d", f"H{i_ + 1}", "--")
    for i, r in enumerate(T.balina_serisi(h).itertuples()):
        if r.al or r.emilim_al: ax.annotate("B", (i, h["Low"].iloc[i]), xytext=(0, -10), textcoords="offset points",
                                           ha="center", fontsize=7, color="#0e7490", fontweight="bold")
        if r.sat or r.emilim_sat: ax.annotate("B", (i, h["High"].iloc[i]), xytext=(0, 6), textcoords="offset points",
                                             ha="center", fontsize=7, color="#9f1239", fontweight="bold")
    ax.set_xlim(-1, x1 + 9)
    lo_ = min(h["Low"].min(), s, *hd); hi_ = max(h["High"].max(), s, *hd); pad = (hi_ - lo_) * 0.04
    ax.set_ylim(lo_ - pad, hi_ + pad)
    adim = max(1, len(h) // 6)
    fmt = "%d.%m %H:%M" if f["tf"] == "4S" else "%d.%m.%y"
    ax.set_xticks(x[::adim]); ax.set_xticklabels([t.strftime(fmt) for t in h.index[::adim]], fontsize=7)
    ax.tick_params(axis="y", labelsize=7); ax.grid(alpha=0.18)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    yon_ad = "AL" if yon == 1 else "SAT"
    ax.set_title(f"{gorunen(f['kod'], f.get('ad'))} · {T.TF_AD[f['tf']]} · {yon_ad} · {f['kurulum_ad']}  (puan {f['puan']:.0f})", fontsize=9, loc="left", fontweight="bold")
    ax.legend(fontsize=7, loc="upper left", frameon=False)
    ax.text(0.0, -0.13, "B: balina hacmi (mavi alım/emilim, kırmızı satış/dağıtım) · yeşil alan hedef, kırmızı alan risk",
            transform=ax.transAxes, fontsize=6.5, color="#64748b")
    fig.tight_layout()
    fig.savefig(dosya, dpi=90); plt.close(fig)
    return dosya


# ------------------------------------------------------------------ mesaj metni (Telegram HTML)
def gorunen(kod, ad=None):
    """ABD hisselerinde '.US' eki yerine şirket adı: 'NVDA (Nvidia)'."""
    if str(kod).endswith(".US"):
        a = ad if ad and ad != kod and ad != kod[:-3] else None
        return f"{kod[:-3]} ({a[:28]})" if a else kod[:-3]
    return kod


def _e(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def firsat_metni(f, tl=None):
    p = f["plan"]; yon = f["yon"]; g = p["giris"]; para = f["para"]
    b = []
    renk = "🟢" if yon == 1 else "🔴"
    b.append(f"{renk} <b>{_e(gorunen(f['kod'], f.get('ad')))} · {'AL' if yon == 1 else 'SAT'}</b> · Puan <b>{f['puan']:.0f}</b>/100")
    b.append(f"Kurulum: {_e(f['kurulum_ad'])}")
    bol = p["bolge"]
    b.append(f"Giriş: <b>{fy(g)}</b> (bölge {fy(bol[0])} – {fy(bol[1])})")
    b.append(f"Stop: <b>{fy(p['stop'])}</b> ({yz((p['stop'] - g) / g)}) · {'son yapı' if f['kurulum'] != 'ST' else 'SuperTrend'} + ATR payı")
    notlar = ["yarısını kapat, stopu girişe çek", "%30'unu kapat", "kalanı kapat"]
    for i, z in enumerate(p["hedef"]):
        b.append(f"H{i + 1}: <b>{fy(z['fiyat'])}</b> ({yz((z['fiyat'] - g) / g)}) · {rr(z['r'])} · {_e(z['etiket'])} — {notlar[i]}")
    b.append(f"Süre: giriş {GIRIS_BAR[f['tf']]} mum içinde; plan en fazla {SURE_AD[f['tf']](MAKS_BAR[f['tf']])}")
    vt, pm = f["gecmis"], f["piyasa_gecmis"]
    gs = []
    if vt.get("n"): gs.append(f"bu varlıkta {vt['n']} örnek, H1'e stoptan önce ulaşma %{vt['p1'] * 100:.0f}, ort. {rrs(vt['ort_R'])}")
    else: gs.append("bu varlıkta yeterli örnek yok")
    if pm.get("n", 0) >= 20: gs.append(f"piyasa geneli %{pm['p1'] * 100:.0f} ({pm['n']:,} örnek)".replace(",", "."))
    b.append("Geçmiş: " + " | ".join(gs))
    b.append("Teyit: " + " · ".join(f"{_e(t)} {'✓' if ok else '✗'}" for t, ok in f["teyit"]))
    bal = [x for x in f["balina"]]
    canli = f["ekstra"].get("balina_canli")
    if bal or canli:
        parca = [f"{_e(x[0])} ({_e(x[2].split(': ', 1)[0]) if ': ' in x[2] and x[2][:2].isdigit() else 'son 20 mum'})" for x in bal[-3:]]
        if canli: parca.append(canli)
        b.append("🐋 Balina: " + " · ".join(parca))
    if f["ekstra"].get("turev"): b.append("Türev: " + _e(f["ekstra"]["turev"]))
    if tl: b.append(tl)
    if f["risk"]: b.append("⚠️ " + " · ".join(_e(r) for r in f["risk"]))
    return "\n".join(b)


def acik_satiri(k):
    yon = k["yon"]; c = k.get("son_fiyat", k["giris"])
    ger = (c - k["giris"]) / k["giris"] * yon
    asama = " ".join("✅" if i < k["asama"] else "▫️" for i in range(3))
    stop_not = "stop girişte" if k["asama"] else f"stop {fy(k['stop'])}"
    return (f"• {_e(gorunen(k['kod'], k.get('ad')))} {'AL' if yon == 1 else 'SAT'} ({T.TF_AD[k['tf']].lower()}) · giriş {fy(k['giris'])} · {stop_not} · {asama} · şu an {yz(ger)}")


def kapanis_satiri(k):
    ikon = {"stop": "⛔", "tüm hedefler": "🏁", "süre doldu": "⌛"}.get(k.get("sebep"), "↩️")
    return (f"{ikon} {_e(gorunen(k['kod'], k.get('ad')))} {'AL' if k['yon'] == 1 else 'SAT'} ({T.TF_AD[k['tf']].lower()}) kapandı: {_e(k.get('sebep'))} · "
            f"sonuç {rrs(k['R'])} ({yz(getiri(k))})")


def performans(gecmis):
    """gecmis: kapanmış kayıt listesi → özet."""
    if not gecmis: return None
    R = np.array([x["R"] for x in gecmis]); a = np.array([x["asama"] for x in gecmis])
    return {"n": len(R), "h1": float((a >= 1).mean()), "kazanc": float((R > 0).mean()), "ort_R": float(R.mean()), "top_R": float(R.sum()),
            "ort_getiri": float(np.mean([getiri(x) for x in gecmis]))}
