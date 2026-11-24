# -*- coding: utf-8 -*-
"""Makro panel: piyasa verileri (Yahoo, anahtarsız) + TCMB EVDS (isteğe bağlı API anahtarı)."""
import datetime as dt
import numpy as np
import pandas as pd

PIYASA = {  # ad: (yahoo kodu, birim)
    "USD/TRY": ("TRY=X", "TL"),
    "EUR/TRY": ("EURTRY=X", "TL"),
    "BIST 100": ("XU100.IS", "puan"),
    "Ons altın": ("GC=F", "$"),
    "Brent petrol": ("BZ=F", "$"),
    "ABD 10Y faiz": ("^TNX", "%"),
}

# EVDS serileri: her kalem için aday kodlar (ilk çalışan kullanılır)
EVDS_SERILER = {
    "TÜFE (yıllık %)": (["TP.TUKFIY2025.GENEL", "TP.FG.J0"], "endeks_yillik"),
    "TCMB ağırlıklı ort. fonlama maliyeti (%)": (["TP.APIFON4"], "seviye"),
    "USD/TRY (TCMB satış)": (["TP.DK.USD.S.YTL"], "seviye"),
    "TCMB brüt rezerv (milyon $)": (["TP.AB.TOPLAM", "TP.AB.C1"], "seviye"),
}


def _degisim(s, gun):
    s = s.dropna()
    if len(s) < 2:
        return None
    hedef = s.index[-1] - pd.Timedelta(days=gun)
    once = s[s.index <= hedef]
    return float(s.iloc[-1] / once.iloc[-1] - 1) if len(once) else None


def piyasa_paneli():
    import yfinance as yf
    out = {}
    for ad, (kod, birim) in PIYASA.items():
        try:
            h = yf.Ticker(kod).history(period="2y")["Close"].dropna()
            h.index = h.index.tz_localize(None) if h.index.tz is not None else h.index
            yb = h[h.index < pd.Timestamp(h.index[-1].year, 1, 1)]
            out[ad] = {"deger": float(h.iloc[-1]), "birim": birim, "seri": h,
                       "d1G": _degisim(h, 1), "d1A": _degisim(h, 30), "d1Y": _degisim(h, 365),
                       "YBB": float(h.iloc[-1] / yb.iloc[-1] - 1) if len(yb) else None}
        except Exception:
            continue
    # Türetilmiş: gram altın (TL) ve BIST 100 dolar bazlı
    try:
        ons, kur = out["Ons altın"]["seri"], out["USD/TRY"]["seri"]
        g = (ons / 31.1035 * kur.reindex(ons.index, method="ffill")).dropna()
        out["Gram altın"] = {"deger": float(g.iloc[-1]), "birim": "TL", "seri": g, "d1G": _degisim(g, 1),
                             "d1A": _degisim(g, 30), "d1Y": _degisim(g, 365), "YBB": None}
    except Exception:
        pass
    try:
        b, kur = out["BIST 100"]["seri"], out["USD/TRY"]["seri"]
        bu = (b / kur.reindex(b.index, method="ffill")).dropna()
        out["BIST 100 ($)"] = {"deger": float(bu.iloc[-1]), "birim": "$", "seri": bu, "d1G": _degisim(bu, 1),
                               "d1A": _degisim(bu, 30), "d1Y": _degisim(bu, 365), "YBB": None}
    except Exception:
        pass
    return out


def _evds_oku(kod, anahtar):
    import tcmb
    df = tcmb.read(kod, api_key=anahtar)
    if df is None or len(df) == 0:
        raise ValueError("boş")
    df = pd.DataFrame(df)
    # Tarih indeksini ve sayısal sütunu bul
    if not isinstance(df.index, pd.DatetimeIndex):
        for c in df.columns:
            if "tarih" in str(c).lower() or "date" in str(c).lower():
                df.index = pd.to_datetime(df[c], errors="coerce", dayfirst=True); break
    sayisal = df.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
    if sayisal.empty:
        raise ValueError("sayısal sütun yok")
    s = sayisal.iloc[:, 0].dropna()
    s.index = pd.to_datetime(s.index, errors="coerce")
    return s[s.index.notna()].sort_index()


def evds_paneli(anahtar):
    out, hatalar = {}, {}
    if not anahtar:
        return out, {"EVDS": "API anahtarı girilmedi"}
    for ad, (kodlar, tur) in EVDS_SERILER.items():
        for kod in kodlar:
            try:
                s = _evds_oku(kod, anahtar)
                if tur == "endeks_yillik":
                    aylik = s.resample("ME").last().dropna()
                    yillik = (aylik / aylik.shift(12) - 1) * 100
                    s = yillik.dropna()
                out[ad] = {"deger": float(s.iloc[-1]), "tarih": s.index[-1], "seri": s, "kod": kod}
                break
            except Exception as ex:
                hatalar[ad] = f"{kod}: {str(ex)[:80]}"
        else:
            continue
        hatalar.pop(ad, None)
    return out, hatalar


def oto_varsayim(evds):
    """EVDS'den gelen verilerle model varsayımlarını günceller (yalnızca güvenilir olanlar)."""
    v = {}
    t = evds.get("TÜFE (yıllık %)")
    if t and 0 < t["deger"] < 150:
        v["enflasyon"] = round(t["deger"] / 100, 4)
    return v
