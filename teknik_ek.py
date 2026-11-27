# -*- coding: utf-8 -*-
"""Aşama 7: teknik motorun eksikleri.

Göstergeler: WMA, HMA, Heikin Ashi, RVOL (göreli hacim).
SMC: emir bloğu (order block) ve kırıcı blok (breaker) — durumlarıyla (aktif / test edildi / geçersiz),
     eşit tepe/dip likidite havuzları, premium/iskonto bölgesi.
Harmonik: Gartley, Bat, Butterfly, Crab, Deep Crab, Shark, Cypher, ABCD (oran toleransı ayarlanabilir).

Hepsi geleceği görmeden çalışır: t anındaki karar yalnızca t'ye kadar kapanmış mumlara dayanır.
Salınımlar ATR tabanlı zigzag ile bulunur; bir tepe/dip ancak fiyat ondan k×ATR döndüğünde "teyitli" sayılır
ve teyit mumundan ÖNCE hiçbir hesapta kullanılmaz.

Dizi fonksiyonları AL yönlü yazılmıştır. SAT için firsat.ayna() ile aynalanmış diziler verilir."""
import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------- göstergeler
def wma(s, n):
    """Ağırlıklı hareketli ortalama (son değere en çok ağırlık), vektörel."""
    s = pd.Series(s, dtype=float); n = int(n)
    if n <= 1: return s.copy()
    w = np.arange(n, 0, -1, dtype=float)              # convolve ters çevirir: en yeni değer n ağırlık alır
    x = s.to_numpy(); out = np.full(len(x), np.nan)
    if len(x) >= n:
        v = np.convolve(np.nan_to_num(x), w, mode="valid") / w.sum()
        gecerli = pd.Series(x).rolling(n).count().to_numpy()[n - 1:] == n
        out[n - 1:] = np.where(gecerli, v, np.nan)
    return pd.Series(out, index=s.index)


def hma(s, n=20):
    """Hull hareketli ortalaması: WMA(2·WMA(n/2) − WMA(n), √n)."""
    return wma(2 * wma(s, max(1, n // 2)) - wma(s, n), max(1, int(np.sqrt(n))))


def heikin_ashi(h):
    """Heikin Ashi mumları (Open/High/Low/Close). İlk açılış = (O+C)/2."""
    c = (h["Open"] + h["High"] + h["Low"] + h["Close"]) / 4
    o = np.empty(len(h)); oo, cc = h["Open"].to_numpy(float), c.to_numpy(float)
    if len(h): o[0] = (oo[0] + h["Close"].iloc[0]) / 2
    for i in range(1, len(h)): o[i] = (o[i - 1] + cc[i - 1]) / 2
    o = pd.Series(o, index=h.index)
    return pd.DataFrame({"Open": o, "High": pd.concat([h["High"], o, c], axis=1).max(axis=1),
                         "Low": pd.concat([h["Low"], o, c], axis=1).min(axis=1), "Close": c, "Volume": h.get("Volume", 0)})


def rvol(v, n=20):
    """Göreli hacim: bu mumun hacmi / önceki n mumun ortalama hacmi (bu mum ortalamaya dahil değil)."""
    ort = v.shift(1).rolling(n, min_periods=max(5, n // 2)).mean()
    return (v / ort.replace(0, np.nan)).astype(float)


# ----------------------------------------------------------------------------- zigzag (teyitli salınımlar)
def zigzag(H, L, at, k=1.5):
    """[(pivot_i, fiyat, tip, teyit_i)], tip +1 tepe / −1 dip. Pivot, fiyat ondan k×ATR döndüğü mumda (teyit_i) teyitlenir."""
    n = len(H); out = []
    if n < 3: return out
    yon, ext = 1, 0
    for t in range(1, n):
        a = at[t]
        if not np.isfinite(a) or a <= 0:
            if yon == 1 and H[t] > H[ext]: ext = t
            if yon == -1 and L[t] < L[ext]: ext = t
            continue
        if yon == 1:
            if H[t] >= H[ext]: ext = t
            elif L[t] <= H[ext] - k * a:
                out.append((ext, float(H[ext]), 1, t)); yon, ext = -1, t
        else:
            if L[t] <= L[ext]: ext = t
            elif H[t] >= L[ext] + k * a:
                out.append((ext, float(L[ext]), -1, t)); yon, ext = 1, t
    return out


# ----------------------------------------------------------------------------- harmonik formasyonlar
# Oranlar (AL / boğa formu; X dip, A tepe, B dip, C tepe, D dip):
#   b: AB / XA geri çekilmesi · c: BC / AB geri çekilmesi · d: D'nin XA'ya göre geri çekilmesi (1'den büyükse X'in altı)
#   bc: CD / BC uzaması
DESEN = {
    "Gartley": {"b": (0.618, 0.618), "c": (0.382, 0.886), "d": (0.786, 0.786), "bc": (1.13, 1.618)},
    "Bat": {"b": (0.382, 0.50), "c": (0.382, 0.886), "d": (0.886, 0.886), "bc": (1.618, 2.618)},
    "Butterfly": {"b": (0.786, 0.786), "c": (0.382, 0.886), "d": (1.27, 1.618), "bc": (1.618, 2.618)},
    "Crab": {"b": (0.382, 0.618), "c": (0.382, 0.886), "d": (1.618, 1.618), "bc": (2.24, 3.618)},
    "Deep Crab": {"b": (0.886, 0.886), "c": (0.382, 0.886), "d": (1.618, 1.618), "bc": (2.0, 3.618)},
}
# C'nin A'yı aştığı formlar: D, XC bacağının geri çekilmesidir
DESEN_XC = {
    "Cypher": {"b": (0.382, 0.618), "cx": (1.13, 1.414), "d": (0.786, 0.786)},     # cx: XC / XA
    "Shark": {"b": (0.382, 0.618), "cab": (1.13, 1.618), "d": (0.886, 1.13)},      # cab: BC / AB
}
TOL = 0.05              # oran toleransı (mutlak); kullanıcı ayarlayabilir
DESEN_AD = {"Gartley": "Gartley", "Bat": "Yarasa (Bat)", "Butterfly": "Kelebek (Butterfly)", "Crab": "Yengeç (Crab)",
            "Deep Crab": "Derin yengeç (Deep Crab)", "Cypher": "Cypher", "Shark": "Köpekbalığı (Shark)", "ABCD": "AB=CD"}


def _ici(x, ar, tol):
    return ar[0] - tol <= x <= ar[1] + tol


def harmonik_aday(X, A, B, C, tol=TOL):
    """X(dip) A(tepe) B(dip) C(tepe) fiyatlarından olası boğa formları → [(ad, d_alt, d_ust)] (D için olası dönüş bölgesi, PRZ)."""
    xa = A - X
    if xa <= 0 or not (B < A and C > B): return []
    out = []
    b = (A - B) / xa
    ab = A - B
    if C < A and B > X - 0.0 * xa:
        c = (C - B) / ab
        for ad, r in DESEN.items():
            if _ici(b, r["b"], tol) and _ici(c, r["c"], tol):
                d1, d2 = A - (r["d"][1] + tol / 2) * xa, A - (r["d"][0] - tol / 2) * xa
                bc = C - B; e1, e2 = C - (r["bc"][1] + 2 * tol) * bc, C - (r["bc"][0] - 2 * tol) * bc
                lo, hi = max(d1, e1), min(d2, e2)
                if lo < hi: out.append((ad, lo, hi))
    if C > A:
        xc = C - X
        r = DESEN_XC["Cypher"]
        if _ici(b, r["b"], tol) and _ici(xc / xa, r["cx"], tol):
            out.append(("Cypher", C - (r["d"][1] + tol / 2) * xc, C - (r["d"][0] - tol / 2) * xc))
        r = DESEN_XC["Shark"]
        if _ici(b, r["b"], tol) and _ici((C - B) / ab, r["cab"], tol):
            out.append(("Shark", C - (r["d"][1] + tol / 2) * xc, C - (r["d"][0] - tol / 2) * xc))
    return out


def abcd_aday(A, B, C, tol=TOL):
    """A(tepe) B(dip) C(tepe): C, AB'nin %38,2–88,6'sı; D = C − AB × (1–1,272)."""
    ab = A - B
    if ab <= 0 or not (B < C < A): return []
    if not _ici((C - B) / ab, (0.382, 0.886), tol): return []
    return [("ABCD", C - (1.272 + tol) * ab, C - (1.0 - tol) * ab)]


def harmonik_tetik(M, k=1.5, tol=TOL, maks_bekle=40):
    """AL yönlü dizilerde harmonik dönüş kurulumu: fiyat D bölgesine (PRZ) girdi ve aynı mumda alıcı onayı geldi.
    → (maske, stop, ad dizisi). Bir C tepesinden en fazla bir tetik."""
    O, H, L, C = M["Open"], M["High"], M["Low"], M["Close"]; at = M["ATR"]; n = len(C)
    m = np.zeros(n, bool); st = np.full(n, np.nan); ad = np.empty(n, dtype=object)
    zz = zigzag(H, L, at, k)
    for p in range(3, len(zz)):
        ci, cp, ctip, conay = zz[p]
        if ctip != 1: continue
        bp, ap = zz[p - 1][1], zz[p - 2][1]
        aday = abcd_aday(ap, bp, cp, tol)
        if p >= 3 and zz[p - 3][2] == -1:
            aday = harmonik_aday(zz[p - 3][1], ap, bp, cp, tol) + aday
        if not aday: continue
        son = zz[p + 1][3] if p + 1 < len(zz) else n - 1          # bir sonraki salınımın teyidine kadar ara
        son = min(son, conay + maks_bekle, n - 1)
        en_dusuk = np.inf
        for t in range(ci + 1, son + 1):
            en_dusuk = min(en_dusuk, L[t])
            if t <= conay: continue                                 # C henüz teyitli değilken karar yok
            a = at[t]
            if not np.isfinite(a) or a <= 0: continue
            uygun = [x for x in aday if x[1] - 0.25 * a <= en_dusuk <= x[2]]
            if not uygun:
                if all(en_dusuk < x[1] - 0.25 * a for x in aday): break   # bölge aşağı kırıldı: form geçersiz
                continue
            rng = H[t] - L[t]
            if rng <= 0: continue
            if C[t] > O[t] and (C[t] - L[t]) / rng >= 0.6 and C[t] >= min(x[1] for x in uygun):
                m[t] = True; st[t] = en_dusuk - 0.3 * a; ad[t] = uygun[0][0]
                break
    return m, st, ad


def harmonik_bul(h, G, k=1.5, tol=TOL, son_n=40):
    """Analiz sayfası için: son salınımlardan tamamlanmış ya da tamamlanmak üzere olan formlar (iki yön)."""
    out = []
    A0 = {c: h[c].to_numpy(float) for c in ("Open", "High", "Low", "Close")}
    at = G["ATR"].to_numpy(float); n = len(h); son_fiyat = float(h["Close"].iloc[-1])
    for yon in (1, -1):
        H, L = (A0["High"], A0["Low"]) if yon == 1 else (-A0["Low"], -A0["High"])
        zz = zigzag(H, L, at, k)
        if len(zz) < 3: continue
        # tamamlanmış form: son pivot D ise (dip) ve öncesi X A B C
        for son_d in (True, False):
            if son_d:
                if zz[-1][2] != -1 or len(zz) < 5: continue
                X, A_, B_, C_, D = [z[1] for z in zz[-5:]]
                if zz[-5][2] != -1: continue
                for ad, lo, hi in harmonik_aday(X, A_, B_, C_, tol) + abcd_aday(A_, B_, C_, tol):
                    if lo - 0.25 * at[-1] <= D <= hi and n - zz[-1][0] <= son_n:
                        out.append({"ad": DESEN_AD[ad], "yon": yon, "durum": "tamamlandı", "d": D * yon,
                                    "bolge": tuple(sorted((lo * yon, hi * yon))), "tarih": h.index[zz[-1][0]]})
            else:
                if zz[-1][2] != 1 or len(zz) < 4: continue
                X, A_, B_, C_ = [z[1] for z in zz[-4:]]
                if zz[-4][2] != -1: continue
                for ad, lo, hi in harmonik_aday(X, A_, B_, C_, tol) + abcd_aday(A_, B_, C_, tol):
                    p = son_fiyat * yon
                    if p > hi:
                        out.append({"ad": DESEN_AD[ad], "yon": yon, "durum": "oluşuyor", "d": None,
                                    "bolge": tuple(sorted((lo * yon, hi * yon))), "tarih": h.index[zz[-1][0]]})
    gorulen, temiz = set(), []
    for f in out:
        anahtar = (f["ad"], f["yon"], f["durum"])
        if anahtar not in gorulen: gorulen.add(anahtar); temiz.append(f)
    return temiz[:4]


# ----------------------------------------------------------------------------- emir bloğu / kırıcı blok (SMC)
def _sal_kesisim(C, seviye):
    """Kapanışın teyitli salınım seviyesini YUKARI kestiği mumlar."""
    pc = np.r_[np.nan, C[:-1]]; ps = np.r_[np.nan, seviye[:-1]]
    with np.errstate(invalid="ignore"):
        return np.isfinite(seviye) & (C > seviye) & (pc <= ps)


def bloklar(M, sal, pencere=10, itki_atr=1.5, omur=60):
    """AL yönlü dizilerde boğa emir blokları. Her yapı kırılımında (BOS), kırılımdan önceki son düşüş mumu blok olur.
    → [{"i", "bos", "alt", "ust", "durum", "test", "gecersiz"}]: durum 'aktif' | 'test edildi' | 'geçersiz' (kapanış blok altı)."""
    O, H, L, C = M["Open"], M["High"], M["Low"], M["Close"]; at = M["ATR"]; n = len(C)
    tepe = sal[0]
    out = []
    for tb in np.flatnonzero(_sal_kesisim(C, tepe)):
        if not np.isfinite(at[tb]): continue
        j = next((j for j in range(tb - 1, max(tb - pencere, 0) - 1, -1) if C[j] < O[j]), None)
        if j is None: continue
        if np.max(H[j + 1:tb + 1]) - H[j] < itki_atr * at[tb]: continue      # güçlü itki yoksa blok sayılmaz
        b = {"i": j, "bos": int(tb), "alt": float(L[j]), "ust": float(H[j]), "durum": "aktif", "test": None, "gecersiz": None}
        for t in range(tb + 1, min(n, tb + omur + 1)):
            if C[t] < b["alt"]:
                b["durum"], b["gecersiz"] = "geçersiz", t; break
            if b["test"] is None and t - tb >= 3 and L[t] <= b["ust"]:
                b["test"] = t; b["durum"] = "test edildi"
        out.append(b)
    return out


def ob_tetik(M, sal):
    """Emir bloğu geri testi: kırılımdan sonra fiyat ilk kez bloğa döndü, blok altında kapatmadı ve alıcı mumu geldi."""
    O, H, L, C = M["Open"], M["High"], M["Low"], M["Close"]; at = M["ATR"]; n = len(C)
    m = np.zeros(n, bool); st = np.full(n, np.nan)
    for b in bloklar(M, sal):
        t = b["test"]
        if t is None or (b["gecersiz"] is not None and b["gecersiz"] <= t): continue
        rng = H[t] - L[t]
        if rng > 0 and C[t] > O[t] and (C[t] - L[t]) / rng >= 0.5 and C[t] >= b["alt"]:
            m[t] = True; st[t] = b["alt"] - 0.3 * at[t]
    return m, st


def breaker_tetik(M, sal, pencere=10, itki_atr=1.5, omur=80):
    """Kırıcı blok (breaker): aşağı yapı kırılımından önceki son yükseliş mumu (ayı bloğu), fiyat üstünde kapatınca
    desteğe döner; yukarıdan ilk geri testte alıcı mumu → AL."""
    O, H, L, C = M["Open"], M["High"], M["Low"], M["Close"]; at = M["ATR"]; n = len(C)
    dip = sal[2]
    m = np.zeros(n, bool); st = np.full(n, np.nan)
    with np.errstate(invalid="ignore"):
        pc = np.r_[np.nan, C[:-1]]; pd_ = np.r_[np.nan, dip[:-1]]
        asagi = np.isfinite(dip) & (C < dip) & (pc >= pd_)
    for tb in np.flatnonzero(asagi):
        if not np.isfinite(at[tb]): continue
        j = next((j for j in range(tb - 1, max(tb - pencere, 0) - 1, -1) if C[j] > O[j]), None)
        if j is None or L[j] - np.min(L[j + 1:tb + 1]) < itki_atr * at[tb]: continue
        alt, ust = L[j], H[j]; donus = None
        for t in range(tb + 1, min(n, tb + omur + 1)):
            if donus is None:
                if C[t] > ust: donus = t                              # blok kırıldı: artık destek
                continue
            if C[t] < alt: break                                      # destek de kırıldı: geçersiz
            if t - donus >= 2 and L[t] <= ust + 0.1 * at[t]:
                rng = H[t] - L[t]
                if rng > 0 and C[t] > O[t] and C[t] > ust and (C[t] - L[t]) / rng >= 0.5:
                    m[t] = True; st[t] = min(L[t], alt) - 0.3 * at[t]
                break
    return m, st


# ----------------------------------------------------------------------------- likidite ve bölge (analiz sayfası)
def esit_seviyeler(piv, at, tol_atr=0.15, son_n=8):
    """Eşit tepe / eşit dip (likidite havuzları): son salınımlarda birbirine ATR×tol kadar yakın iki tepe ya da dip."""
    out = []
    for tip, ad in ((1, "Eşit tepeler (üstte likidite)"), (-1, "Eşit dipler (altta likidite)")):
        p = [x for x in piv if x[2] == tip][-son_n:]
        for i in range(len(p) - 1):
            for j in range(i + 1, len(p)):
                if abs(p[i][1] - p[j][1]) <= tol_atr * at:
                    out.append((ad, tip, (p[i][1] + p[j][1]) / 2))
    gorulen, temiz = set(), []
    for x in sorted(out, key=lambda x: -x[2] if x[1] == 1 else x[2]):
        k = (x[1], round(x[2], 6))
        if k not in gorulen: gorulen.add(k); temiz.append(x)
    return temiz[:3]


def premium_iskonto(piv, fiyat):
    """Son salınım aralığına göre (dealing range) fiyatın yeri: iskonto (<%50), denge, premium (>%50)."""
    tep = [p[1] for p in piv if p[2] == 1][-1:]; dip = [p[1] for p in piv if p[2] == -1][-1:]
    if not tep or not dip or tep[0] <= dip[0]: return None
    y = (fiyat - dip[0]) / (tep[0] - dip[0])
    bolge = "premium (pahalı yarı)" if y > 0.55 else "iskonto (ucuz yarı)" if y < 0.45 else "denge"
    return {"oran": float(y), "bolge": bolge, "ust": tep[0], "alt": dip[0], "orta": (tep[0] + dip[0]) / 2}


# ============================================================ Aşama 10c: VCP, momentum patlaması, episodic pivot
# Aynalanmış dizilerde çalışır (SAT için fiyatlar negatif): yüzdeler hep fark / |önceki| ile hesaplanır.
def _ort(x, n):
    return pd.Series(x).rolling(n, min_periods=n).mean().to_numpy(float)


def _enb(x, n):
    return pd.Series(x).rolling(n, min_periods=n).max().to_numpy(float)


def _enk(x, n):
    return pd.Series(x).rolling(n, min_periods=n).min().to_numpy(float)


def _kaydir_(x, k=1):
    y = np.full(len(x), np.nan); y[k:] = x[:-k]; return y


def vcp_tetik(M):
    """Minervini VCP: 2. evre trend + son 60 mumda daralan 3 geri çekilme + kuruyan hacim → pivotun hacimli kırılımı.
    → (maske, stop: son 10 mumun dibi − 0,2 ATR)."""
    O, H, L, C, V, at = (np.asarray(M[k], float) for k in ("Open", "High", "Low", "Close", "Volume", "ATR")); n = len(C)
    m = np.zeros(n, bool); stop = np.full(n, np.nan)
    if not M.get("hacim_var") or n < 260: return m, stop
    s50, s150, s200 = _ort(C, 50), _ort(C, 150), _ort(C, 200)
    hi, lo = _enb(C, 252), _enk(C, 252)
    v50, v10 = _kaydir_(_ort(V, 50)), _kaydir_(_ort(V, 10))
    piv = _kaydir_(_enb(H, 15)); dip10 = _kaydir_(_enk(L, 10))
    with np.errstate(invalid="ignore", divide="ignore"):
        trend = (C > s50) & (s50 > s150) & (s150 > s200) & (s200 > _kaydir_(s200, 20)) & ((hi - C) / np.abs(hi) <= 0.25) & ((C - lo) / np.abs(lo) >= 0.30)
        kir = (C > piv) & (_kaydir_(C) <= piv) & (V >= 1.4 * v50) & (v10 < 0.85 * v50) & ((C - L) / np.where(H - L > 0, H - L, np.nan) >= 0.5)
    for t in np.flatnonzero(trend & kir):
        if t < 61: continue
        d = []
        for a in (t - 60, t - 40, t - 20):
            hh, ll = H[a:a + 20].max(), L[a:a + 20].min(); d.append((hh - ll) / abs(hh))
        if d[0] > d[1] > d[2] and d[2] <= 0.10 and d[0] >= 0.06:
            m[t] = True; stop[t] = dip10[t] - 0.2 * at[t]
    return m, stop


def momentum_tetik(M):
    """Momentum patlaması (Stockbee): sakin günün ardından ≥ %4 (ve ≥ 1,5 ATR) yükseliş, hacim önceki günden yüksek, üst bölgede kapanış,
    fiyat 50 günlüğün üstünde. → (maske, stop: patlama mumunun dibi − 0,1 ATR)."""
    H, L, C, V, at = (np.asarray(M[k], float) for k in ("High", "Low", "Close", "Volume", "ATR")); n = len(C)
    pC = _kaydir_(C); ppC = _kaydir_(C, 2); s50 = _ort(C, 50)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (C - pC) / np.abs(pC); r1 = (pC - ppC) / np.abs(ppC)
        clv = (C - L) / np.where(H - L > 0, H - L, np.nan)
        hv = (V > _kaydir_(V)) if M.get("hacim_var") else np.ones(n, bool)
        m = (r >= 0.04) & ((C - pC) >= 1.5 * at) & hv & (clv >= 0.7) & (np.abs(r1) <= 0.02) & (C > s50)
    m = np.nan_to_num(m, nan=0).astype(bool)
    return m, L - 0.1 * at


def ep_tetik(M):
    """Episodic pivot: ≥ %6 boşlukla açılış, hacim 50 günlük ortalamanın ≥ 3 katı, gün boyu boşluk korunur (üst yarıda kapanış,
    önceki kapanışın üstünde). → (maske, stop: günün dibi − 0,1 ATR)."""
    O, H, L, C, V, at = (np.asarray(M[k], float) for k in ("Open", "High", "Low", "Close", "Volume", "ATR")); n = len(C)
    if not M.get("hacim_var"): return np.zeros(n, bool), np.full(n, np.nan)
    pC = _kaydir_(C); v50 = _kaydir_(_ort(V, 50))
    with np.errstate(invalid="ignore", divide="ignore"):
        bosluk = (O - pC) / np.abs(pC)
        clv = (C - L) / np.where(H - L > 0, H - L, np.nan)
        m = (bosluk >= 0.06) & (V >= 3 * v50) & (clv >= 0.5) & (C > pC + 0.5 * (O - pC))
    return np.nan_to_num(m, nan=0).astype(bool), L - 0.1 * at
