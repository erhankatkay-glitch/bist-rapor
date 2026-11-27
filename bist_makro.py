# -*- coding: utf-8 -*-
"""Makro panel: piyasa verileri (Yahoo, anahtarsız) + TCMB EVDS (isteğe bağlı API anahtarı)."""
import datetime as dt
import numpy as np
import pandas as pd
import veri_kalite as VK

PIYASA = {  # ad: (yahoo kodu, birim)
    "BIST 100": ("XU100.IS", "puan"),
    "S&P 500": ("^GSPC", "puan"),
    "Nasdaq": ("^IXIC", "puan"),
    "USD/TRY": ("TRY=X", "TL"),
    "EUR/TRY": ("EURTRY=X", "TL"),
    "Ons altın": ("GC=F", "$"),
    "Gümüş": ("SI=F", "$"),
    "Brent petrol": ("BZ=F", "$"),
    "Bitcoin": ("BTC-USD", "$"),
    "Ethereum": ("ETH-USD", "$"),
    "Dolar endeksi": ("DX-Y.NYB", ""),
    "ABD 10Y faiz": ("^TNX", "%"),
    "VIX": ("^VIX", ""),
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


def _yerel_tz(kod):
    k = str(kod)
    if k.endswith(".IS"): return "Europe/Istanbul"
    if k.endswith("-USD"): return "UTC"            # kripto: Yahoo günlük barı UTC gününe göredir
    return "America/New_York"


def gun_ici_tamamla(gunluk, gunici, kod):
    """Yahoo günlük verisi bazı piyasalarda (özellikle XU100 ve BIST hisseleri) bir-iki gün geride kalabiliyor.
    Gün içi (15 dk) verideki, günlükte olmayan günleri günlük bara çevirip ekler; son günün kapanışını en son fiyatla günceller.
    gunluk: Close serisi ya da OHLCV DataFrame (tz'siz, gün indeksli). gunici: aynı sembolün gün içi OHLCV DataFrame'i."""
    try:
        if gunici is None or len(gunici) == 0 or len(gunluk) == 0:
            return gunluk
        g = gunici.dropna(subset=["Close"])
        if g.empty:
            return gunluk
        idx = g.index.tz_convert(_yerel_tz(kod)) if g.index.tz is not None else g.index
        gun = pd.Series(idx.date, index=g.index)
        out = gunluk.astype(float) if isinstance(gunluk, pd.Series) else gunluk.astype({c: float for c in gunluk.columns if c in ("Open", "High", "Low", "Close", "Volume")})
        son_gun = pd.Timestamp(out.index[-1]).normalize()
        for d, parca in g.groupby(gun.values):
            t = pd.Timestamp(d)
            if t < son_gun:
                continue
            if isinstance(out, pd.Series):
                out.loc[t] = float(parca["Close"].iloc[-1])
            else:
                satir = {"Open": float(parca["Open"].iloc[0]), "High": float(parca["High"].max()), "Low": float(parca["Low"].min()),
                         "Close": float(parca["Close"].iloc[-1]), "Volume": float(parca["Volume"].sum()) if "Volume" in parca else 0.0}
                if t == son_gun and t in out.index:          # aynı gün: yalnız kapanışı/uçları güncelle
                    eski = out.loc[t]
                    satir = {"Open": eski["Open"], "High": max(eski["High"], satir["High"]), "Low": min(eski["Low"], satir["Low"]),
                             "Close": satir["Close"], "Volume": max(float(eski.get("Volume", 0) or 0), satir["Volume"])}
                for c, v in satir.items():
                    if c in out.columns: out.loc[t, c] = v
        return out.sort_index()
    except Exception:
        return gunluk


def _tazele(h, gi, kod):
    try:
        if gi is None or kod not in gi.columns.get_level_values(0):
            return h
        return gun_ici_tamamla(h, gi[kod], kod)
    except Exception:
        return h



def _son_zaman(gi, kod):
    """Gün içi (15 dk) verideki son mumun KAPANIŞ zamanı, UTC ISO."""
    try:
        if gi is None or kod not in gi.columns.get_level_values(0): return None
        g = gi[kod]["Close"].dropna()
        if g.empty: return None
        t = g.index[-1]
        t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
        return (t + pd.Timedelta(minutes=15)).to_pydatetime().isoformat()
    except Exception:
        return None


def _gun_sonu_zaman(gun, kod):
    """Gün içi veri yoksa: o günün seans kapanış saati (UTC)."""
    from zoneinfo import ZoneInfo
    tur = VK.tur_bul(kod)
    tz, saat = ((ZoneInfo("Europe/Istanbul"), dt.time(18, 10)) if tur == "bist" else
                (ZoneInfo("UTC"), dt.time(23, 59)) if tur == "kripto" else (ZoneInfo("America/New_York"), dt.time(16, 0)))
    try:
        return dt.datetime.combine(pd.Timestamp(gun).date(), saat, tz).astimezone(dt.timezone.utc).isoformat()
    except Exception:
        return None


def binance_fiyat(sym, zaman_asimi=8):
    """Binance herkese açık 24 saatlik özet: {"fiyat", "d24", "zaman"} (anahtarsız; ABD sunucularında da çalışan uç)."""
    import json, urllib.request
    u = f"https://data-api.binance.vision/api/v3/ticker/24hr?symbol={sym}"
    d = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=zaman_asimi).read())
    return {"fiyat": float(d["lastPrice"]), "d24": float(d["priceChangePercent"]) / 100,
            "zaman": dt.datetime.fromtimestamp(int(d["closeTime"]) / 1000, dt.timezone.utc)}

def piyasa_paneli():
    import yfinance as yf
    out = {}
    kodlar = [k for k, _ in PIYASA.values()]
    try:
        df = yf.download(kodlar, period="2y", interval="1d", auto_adjust=True, progress=False, group_by="ticker", threads=True)
    except Exception:
        df = None
    # Yahoo'nun günlük barı bazı piyasalarda (özellikle XU100) bir gün geride kalabiliyor.
    # Son fiyat ve son gün, gün içi 15 dakikalık verilerle tazelenir.
    try:
        gi = yf.download(kodlar, period="5d", interval="15m", auto_adjust=True, progress=False, group_by="ticker", threads=True)
    except Exception:
        gi = None
    for ad, (kod, birim) in PIYASA.items():
        try:
            if df is not None and kod in df.columns.get_level_values(0):
                h = df[kod]["Close"].dropna()
            else:
                h = yf.Ticker(kod).history(period="2y")["Close"].dropna()
            h.index = h.index.tz_localize(None) if getattr(h.index, "tz", None) is not None else h.index
            h = _tazele(h, gi, kod)
            if len(h) < 5: continue
            yb = h[h.index < pd.Timestamp(h.index[-1].year, 1, 1)]
            zaman = _son_zaman(gi, kod) or _gun_sonu_zaman(h.index[-1], kod)
            out[ad] = {"deger": float(h.iloc[-1]), "birim": birim, "seri": h, "zaman": zaman, "kaynak": "Yahoo", "tur": VK.tur_bul(kod),
                       "d1G": float(h.iloc[-1] / h.iloc[-2] - 1), "d1A": _degisim(h, 30), "d1Y": _degisim(h, 365),
                       "YBB": float(h.iloc[-1] / yb.iloc[-1] - 1) if len(yb) else None}
        except Exception:
            continue
    for ad, sym in (("Bitcoin", "BTCUSDT"), ("Ethereum", "ETHUSDT")):   # kripto: birincil Binance (anlık), yedek Yahoo
        try:
            b = binance_fiyat(sym)
            if b and ad in out:
                o = out[ad]; s_ = o["seri"].copy()
                gun = pd.Timestamp(b["zaman"].astimezone(dt.timezone.utc).date())
                s_.loc[gun] = b["fiyat"]; s_ = s_.sort_index()
                o.update(deger=b["fiyat"], seri=s_, zaman=b["zaman"].isoformat(), kaynak="Binance",
                         d1G=b["d24"], d1A=_degisim(s_, 30), d1Y=_degisim(s_, 365))
        except Exception:
            pass
    # Türetilmiş: gram altın (TL) ve BIST 100 dolar bazlı
    try:
        ons, kur = out["Ons altın"]["seri"], out["USD/TRY"]["seri"]
        g = (ons / 31.1035 * kur.reindex(ons.index, method="ffill")).dropna()
        out["Gram altın"] = {"deger": float(g.iloc[-1]), "birim": "TL", "seri": g, "d1G": _degisim(g, 1), "tur": "emtia",
                             "zaman": min(out["Ons altın"].get("zaman") or "", out["USD/TRY"].get("zaman") or "") or None, "kaynak": "Yahoo (hesaplanan)",
                             "d1A": _degisim(g, 30), "d1Y": _degisim(g, 365), "YBB": None}
    except Exception:
        pass
    try:
        b, kur = out["BIST 100"]["seri"], out["USD/TRY"]["seri"]
        bu = (b / kur.reindex(b.index, method="ffill")).dropna()
        out["BIST 100 ($)"] = {"deger": float(bu.iloc[-1]), "birim": "$", "seri": bu, "d1G": _degisim(bu, 1), "tur": "bist",
                               "zaman": out["BIST 100"].get("zaman"), "kaynak": "Yahoo (hesaplanan)",
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
