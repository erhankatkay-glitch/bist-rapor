# -*- coding: utf-8 -*-
"""Kısa süreli "iğne" (likidite süpürme) uyarısı.

Fiyat çoğu zaman stop emirlerinin biriktiği seviyelere kısa bir fitille uğrayıp geri döner.
Bu modül 1 saatlik mumlarda fiyata en yakın, henüz süpürülmemiş likidite seviyelerini bulur:
  - süpürülmemiş salınım dipleri / tepeleri (sonradan fiyatın inmediği/çıkmadığı pivotlar)
  - eşit dipler / tepeler (birbirine çok yakın iki pivot: stoplar yoğunlaşır)
  - yuvarlak seviyeler (ör. 60.000, 60.500)
Hangi tarafta, fiyata %3 içinde daha çok ve daha yakın seviye varsa iğnenin o yöne olması beklenir.
Bu bir olasılık değerlendirmesidir; kesin sonuç değildir."""
import json
import urllib.request

import numpy as np

BINANCE = "https://data-api.binance.vision/api/v3/klines"


def mumlar(sembol="BTCUSDT", aralik="1h", adet=300):
    u = f"{BINANCE}?symbol={sembol}&interval={aralik}&limit={adet}"
    k = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=10).read())
    a = np.array([[float(x[2]), float(x[3]), float(x[4])] for x in k])
    return a[:, 0], a[:, 1], a[:, 2]      # H, L, C


def _pivotlar(H, L, n=3):
    tep, dip = [], []
    for i in range(n, len(H) - n):
        w_h, w_l = H[i - n:i + n + 1], L[i - n:i + n + 1]
        if H[i] == w_h.max() and (w_h == H[i]).sum() == 1: tep.append(i)       # düz platolar pivot sayılmaz
        if L[i] == w_l.min() and (w_l == L[i]).sum() == 1: dip.append(i)
    return tep, dip


def seviyeler(H, L, C, yon, aralik=0.03, adim=None):
    """yon=-1: fiyatın altındaki, yon=1: üstündeki süpürülmemiş likidite seviyeleri (yakından uzağa)."""
    p = C[-1]; tep, dip = _pivotlar(H, L)
    aday = []
    if yon == -1:
        for i in dip:
            v = L[i]
            if v < p and L[i + 1:].min(initial=np.inf) > v and (p - v) / p <= aralik: aday.append(v)
    else:
        for i in tep:
            v = H[i]
            if v > p and H[i + 1:].max(initial=-np.inf) < v and (v - p) / p <= aralik: aday.append(v)
    adim = adim or (500 if p > 20000 else 100 if p > 2000 else 10 ** int(np.floor(np.log10(p))) / 2)
    r = (np.floor(p / adim) * adim) if yon == -1 else (np.ceil(p / adim) * adim)
    if r != p and abs(r - p) / p <= aralik: aday.append(float(r))
    aday = sorted(set(aday), key=lambda v: abs(v - p))
    temiz = []
    for v in aday:                       # çok yakın (binde 1) seviyeleri birleştir
        if all(abs(v - t) / p > 0.001 for t in temiz): temiz.append(v)
    return temiz[:3]


def uyari(H, L, C):
    """→ {"yon": -1/1, "fiyat", "seviyeler": [...]} ya da None."""
    alt, ust = seviyeler(H, L, C, -1), seviyeler(H, L, C, 1)
    if not alt and not ust: return None
    p = C[-1]
    puan = lambda s: (len(s), -abs(s[0] - p) / p if s else -1)
    yon = -1 if puan(alt) >= puan(ust) else 1
    s = alt if yon == -1 else ust
    if len(s) < 2: return None
    return {"yon": yon, "fiyat": float(p), "seviyeler": [float(x) for x in s]}


def metin(u, ad="BTC"):
    def f(x): return f"{x:,.0f}".replace(",", ".") if x >= 1000 else f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return (f"{ad}'de kısa süreli {'aşağı' if u['yon'] == -1 else 'yukarı'} iğne bekleniyor",
            f"Şu an {f(u['fiyat'])} · olası iğne bölgeleri {' / '.join(f(x) for x in u['seviyeler'])} · "
            "Algoritmik değerlendirmedir, yatırım tavsiyesi değildir.")


def atr(H, L, C, n=14):
    tr = np.maximum(H[1:] - L[1:], np.maximum(abs(H[1:] - C[:-1]), abs(L[1:] - C[:-1])))
    return float(np.mean(tr[-n:])) if len(tr) >= n else float(np.mean(tr))


def tetik(H, L, C, saat=3):
    """Uyarının TETİKLENME koşulu (sürekli gösterilmez):
      1) seçilen tarafta fiyata %2 içinde en az 2 süpürülmemiş likidite seviyesi var,
      2) en yakın seviye 1,5 saatlik ATR kadar yakın (fiyat seviyeye dayanmış),
      3) son `saat` mumda fiyat o yöne hareket etmiş (en az %0,4) — yani seviyeye doğru ivme var.
    → uyari() sözlüğü + "neden" ya da None."""
    u = uyari(H, L, C)
    if not u: return None
    p = C[-1]; a = atr(H, L, C)
    yakin = [s for s in u["seviyeler"] if abs(s - p) / p <= 0.02]
    if len(yakin) < 2: return None
    if abs(u["seviyeler"][0] - p) > 1.5 * a: return None
    ivme = (C[-1] / C[-1 - saat] - 1) * u["yon"]
    if ivme < 0.004: return None
    u["neden"] = f"son {saat} saatte %{abs(ivme) * 100:.1f} {'düşüş' if u['yon'] == -1 else 'yükseliş'}, en yakın seviye {abs(u['seviyeler'][0] - p) / a:.1f} ATR uzakta"
    return u
