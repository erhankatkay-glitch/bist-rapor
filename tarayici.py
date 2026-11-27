# -*- coding: utf-8 -*-
"""Aşama 8: kendi taramanı kur.

Kapanış bültenleri her varlık için tek satırlık bir "tarama satırı" üretir (bulten/<piyasa>/tarama.csv).
Uygulama bu tabloyu okuyup kullanıcının birleştirdiği filtreleri anında uygular; tarama için veri yeniden indirilmez.

Sinyal tanımı: fırsat motorunun kurulumları (kırılım, geri çekilme, sıkışma, uyumsuzluk, likidite avı, SuperTrend,
Aşama 7'de onaylanan emir bloğu / kırıcı blok / harmonik). Son 60 mumdaki en yeni tetik "son sinyal"dir;
tarih, fiyat, yaş (mum) ve o günden bu yana değişim yazılır. Geleceğe bakmaz: tetikler yalnızca kapanmış mumlarla hesaplanır."""
import base64
import json
import zlib

import numpy as np
import pandas as pd

PIYASA_AD = {"bist": "BIST", "abd": "ABD", "kripto": "Kripto", "emtia": "Emtia"}
FIB_ORAN = (0.236, 0.382, 0.5, 0.618, 0.786)


# ----------------------------------------------------------------------------- satır üretimi
def son_sinyal(h, G, piyasa, tf="G", pencere=60):
    """Son `pencere` mumdaki en yeni kurulum tetiği → {yon, kurulum, tarih, fiyat, yas, degisim} ya da None."""
    import firsat as F
    A = F.diziler(h, G); n = len(A["Close"]); en = None
    for yon in (1, -1):
        M = F.ayna(A, yon)
        tet = F.tetikler(M, ek=F.ek_kurulumlar(piyasa, tf, yon) or None)
        for k, (m, _) in tet.items():
            idx = np.flatnonzero(m[max(0, n - pencere):]) + max(0, n - pencere)
            if len(idx) and (en is None or idx[-1] > en[0]):
                en = (int(idx[-1]), yon, k)
    if en is None: return None
    t, yon, k = en
    fiyat = float(h["Close"].iloc[t]); son = float(h["Close"].iloc[-1])
    ad = F.KURULUM.get(k, (k, k))[0 if yon == 1 else 1]
    return {"yon": yon, "kurulum": ad, "tarih": h.index[t], "fiyat": fiyat, "yas": n - 1 - t, "degisim": son / fiyat - 1}


def _ema_sirasi(G):
    e20, e50, s200 = (float(G[c].iloc[-1]) if np.isfinite(G[c].iloc[-1]) else None for c in ("EMA20", "EMA50", "SMA200"))
    if None in (e20, e50): return "–"
    if s200 is not None and e20 > e50 > s200: return "Boğa dizilimi"
    if s200 is not None and e20 < e50 < s200: return "Ayı dizilimi"
    return "Karışık"


def _fib(a):
    fb = a.get("fib")
    if not fb: return None, None
    c = a["fiyat"]; en = min(FIB_ORAN, key=lambda r: abs(fb["seviye"][r] - c))
    return f"%{en * 100:.1f}".replace(".", ","), abs(fb["seviye"][en] / c - 1)


def satir(s, piyasa, ek=None):
    """Tek varlığın tarama satırı (teknik_bulten analiz çıktısından)."""
    g = s["tf"].get("G"); hf = s["tf"].get("H")
    if not g: return None
    G, h, c = g["G"], g["h"], g["fiyat"]
    son = lambda k: float(G[k].iloc[-1]) if k in G and np.isfinite(G[k].iloc[-1]) else None
    vol = h["Volume"].iloc[-20:]
    hacim = float((h["Close"].iloc[-20:] * vol).median()) if vol.sum() > 0 else None
    d = g["sr"]["destek"][0][0] if g["sr"]["destek"] else None
    r = g["sr"]["direnc"][0][0] if g["sr"]["direnc"] else None
    pa = g["pa"]; harm = g.get("harm") or []
    fib_ad, fib_uz = _fib(g)
    ob_ici = next((b for b in pa.get("bloklar", []) if b["alt"] <= c <= b["ust"]), None)
    fvg_ici = next((f for f in pa.get("fvg", []) if f[1] <= c <= f[2]), None)
    sin = {}
    try:
        x = son_sinyal(h, G, piyasa)
        if x: sin = {"Sinyal yönü": "AL" if x["yon"] == 1 else "SAT", "Sinyal": x["kurulum"], "Sinyal tarihi": x["tarih"].strftime("%Y-%m-%d"),
                     "Sinyal fiyatı": x["fiyat"], "Sinyal yaşı": x["yas"], "Sinyalden beri": x["degisim"]}
    except Exception:
        pass
    olay = [o[0] for o in pa.get("olaylar", [])]
    out = {
        "Kod": s["kod"], "Ad": s.get("ad"), "Piyasa": PIYASA_AD.get(piyasa, piyasa), "Fiyat": c, "Değişim": g.get("degisim"),
        "1A": float(h["Close"].iloc[-1] / h["Close"].iloc[-22] - 1) if len(h) > 22 else None,
        "Hacim": hacim, "RVOL": son("RVOL"), "RSI": son("RSI"),
        "ATR %": (son("ATR") / c) if son("ATR") and c else None, "ADX": son("ADX"),
        "EMA sırası": _ema_sirasi(G), "Trend": g["pa"]["yapi"],
        "Günlük": g["etiket"], "Haftalık": hf["etiket"] if hf else "–",
        "Günlük puan": round(g["puan"], 1), "Haftalık puan": round(hf["puan"], 1) if hf else None,
        "Çoklu zaman uyumu": (hf is not None) and ((g["puan"] >= 50) == (hf["puan"] >= 50)) and abs(g["puan"] - 50) >= 8 and abs(hf["puan"] - 50) >= 8,
        "Fib seviyesi": fib_ad, "Fib uzaklık": fib_uz,
        "Destek": d, "Desteğe uzaklık": (c / d - 1) if d else None, "Direnç": r, "Dirence uzaklık": (r / c - 1) if r else None,
        "FVG içinde": bool(fvg_ici), "BOS": any("BOS" in o for o in olay), "CHoCH": any("CHoCH" in o for o in olay),
        "Likidite süpürme": any("Likidite avı" in o for o in olay),
        "Emir bloğu içinde": ("Boğa" if ob_ici["yon"] == 1 else "Ayı") if ob_ici else "",
        "Harmonik": ", ".join(f"{f['ad']} ({'boğa' if f['yon'] == 1 else 'ayı'}, {f['durum']})" for f in harm[:2]),
        "Bölge": (pa.get("bolge") or {}).get("bolge", ""),
        "Teknik puan": round(s["puan"], 1) if s.get("puan") is not None else None, "Genel": s.get("etiket"),
        "Veri zamanı": h.index[-1].strftime("%Y-%m-%d"),
    }
    out.update(sin)
    if ek: out.update({k: v for k, v in ek.items() if k in ("RS", "Sektör") and v is not None})
    return out


def tablo(analizler, piyasa, ekler_satir=None):
    ek = {r["Kod"]: r for r in (ekler_satir or [])}
    out = []
    for s in analizler:
        try:
            x = satir(s, piyasa, ek.get(s["kod"]))
            if x: out.append(x)
        except Exception:
            continue
    return pd.DataFrame(out)


# ----------------------------------------------------------------------------- filtreler
# alan: (etiket, tür, birim çarpanı). Tür: "sayi" (min/max), "secim" (değerlerden biri), "evet" (doğru olanlar)
ALANLAR = {
    "Fiyat": ("Fiyat", "sayi", 1), "Değişim": ("Günlük değişim %", "sayi", 100), "1A": ("1 aylık değişim %", "sayi", 100),
    "Hacim": ("Günlük işlem hacmi (medyan)", "sayi", 1), "RVOL": ("Göreli hacim (RVOL, x)", "sayi", 1),
    "RSI": ("RSI", "sayi", 1), "ATR %": ("ATR % (oynaklık)", "sayi", 100), "ADX": ("ADX (trend gücü)", "sayi", 1),
    "EMA sırası": ("EMA sıralaması", "secim", None), "Trend": ("Piyasa yapısı", "secim", None),
    "Günlük": ("Günlük görünüm", "secim", None), "Haftalık": ("Haftalık görünüm", "secim", None),
    "Teknik puan": ("Teknik puan (0–100)", "sayi", 1), "RS": ("Göreli güç (RS, 0–100)", "sayi", 1),
    "Çoklu zaman uyumu": ("Günlük ve haftalık aynı yönde", "evet", None),
    "Fib uzaklık": ("Fibonacci seviyesine uzaklık %", "sayi", 100),
    "Desteğe uzaklık": ("Desteğe uzaklık %", "sayi", 100), "Dirence uzaklık": ("Dirence uzaklık %", "sayi", 100),
    "FVG içinde": ("Fiyat FVG içinde", "evet", None), "BOS": ("Yapı kırılımı (BOS)", "evet", None),
    "CHoCH": ("Karakter değişimi (CHoCH)", "evet", None), "Likidite süpürme": ("Likidite süpürme", "evet", None),
    "Emir bloğu içinde": ("Fiyat emir bloğunda", "secim", None), "Harmonik": ("Harmonik formasyon var", "var", None),
    "Bölge": ("Premium / iskonto", "secim", None),
    "Sinyal yönü": ("Son sinyal yönü", "secim", None), "Sinyal yaşı": ("Sinyal yaşı (mum)", "sayi", 1),
    "Sinyalden beri": ("Sinyalden beri değişim %", "sayi", 100),
}


def uygula(df, kosullar):
    """kosullar: [{"alan", "min"?, "max"?, "deger"?}] → filtrelenmiş tablo (tüm koşullar VE ile)."""
    m = pd.Series(True, index=df.index)
    for k in kosullar:
        a = k.get("alan")
        if a not in df.columns or a not in ALANLAR: continue
        tur, carp = ALANLAR[a][1], ALANLAR[a][2] or 1
        x = df[a]
        if tur == "sayi":
            x = pd.to_numeric(x, errors="coerce") * carp
            if k.get("min") is not None: m &= x >= float(k["min"])
            if k.get("max") is not None: m &= x <= float(k["max"])
        elif tur == "secim":
            dg = k.get("deger")
            if dg: m &= x.astype(str).isin(dg if isinstance(dg, list) else [dg])
        elif tur == "evet":
            m &= x.astype(str).str.lower().isin(("true", "1", "evet"))
        elif tur == "var":
            m &= x.fillna("").astype(str).str.len() > 0
    return df[m]


HAZIR = {
    "Güçlü trend + taze AL sinyali": [{"alan": "EMA sırası", "deger": ["Boğa dizilimi"]}, {"alan": "ADX", "min": 20},
                                      {"alan": "Sinyal yönü", "deger": ["AL"]}, {"alan": "Sinyal yaşı", "max": 3}],
    "Aşırı satımdan dönüş adayları": [{"alan": "RSI", "max": 35}, {"alan": "Desteğe uzaklık", "max": 4}],
    "Hacimli kırılım": [{"alan": "RVOL", "min": 1.8}, {"alan": "BOS", "deger": True}, {"alan": "Değişim", "min": 1}],
    "Harmonik dönüş bölgesi": [{"alan": "Harmonik"}],
    "Emir bloğunda alıcı bölgesi": [{"alan": "Emir bloğu içinde", "deger": ["Boğa"]}, {"alan": "Bölge", "deger": ["iskonto (ucuz yarı)"]}],
    "Likidite süpürüp dönenler": [{"alan": "Likidite süpürme", "deger": True}],
    "Çoklu zaman dilimi AL uyumu": [{"alan": "Çoklu zaman uyumu", "deger": True}, {"alan": "Günlük", "deger": ["AL", "GÜÇLÜ AL"]}],
    "Endeksten güçlü (RS ≥ 80)": [{"alan": "RS", "min": 80}, {"alan": "Teknik puan", "min": 55}],
    "Sıkışma (düşük oynaklık)": [{"alan": "ATR %", "max": 2.0}, {"alan": "ADX", "max": 18}],
}


def kodla(sablon):
    """Şablonu adres satırına sığacak kısa metne çevirir."""
    return base64.urlsafe_b64encode(zlib.compress(json.dumps(sablon, ensure_ascii=False, separators=(",", ":")).encode())).decode().rstrip("=")


def coz(metin):
    try:
        p = metin + "=" * (-len(metin) % 4)
        return json.loads(zlib.decompress(base64.urlsafe_b64decode(p)).decode())
    except Exception:
        return None
