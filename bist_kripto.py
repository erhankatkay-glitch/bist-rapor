# -*- coding: utf-8 -*-
"""Binance ve OKX spot piyasaları: tüm USDT ve TL (TRY) pariteleri, günlük mumlar, CoinGecko eşlemesi.
Binance'in ana API'si ABD'deki sunucuları engellediği için resmi herkese açık piyasa verisi adresi
(data-api.binance.vision) kullanılır. Anahtar gerekmez, ücretsizdir.

Kod biçimi: "PEPE/USDT", "BTC/TRY", "BTC/TRY@OKX" (borsa belirtilmezse Binance)."""
import time, datetime as dt
import numpy as np
import pandas as pd

BINANCE = "https://data-api.binance.vision/api/v3"
OKX = "https://www.okx.com/api/v5"
CG = "https://api.coingecko.com/api/v3"
UA = {"User-Agent": "Mozilla/5.0"}
PARITELER = ("USDT", "TRY")
BORSALAR = ("Binance", "OKX")
STABIL = {"USDT", "USDC", "FDUSD", "TUSD", "DAI", "BUSD", "USDP", "EUR", "EURI", "AEUR", "USD1", "XUSD", "BFUSD", "USDE", "PYUSD", "RLUSD"}
ESKI = {"BTC": "Bitcoin", "ETH": "Ethereum", "BNB": "BNB", "SOL": "Solana", "XRP": "XRP", "ADA": "Cardano", "DOGE": "Dogecoin",
        "AVAX": "Avalanche", "TRX": "TRON", "LINK": "Chainlink", "DOT": "Polkadot", "LTC": "Litecoin"}


def _get(url, **params):
    import requests
    for deneme in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=20)
            if r.status_code == 429: time.sleep(2 + deneme * 3); continue
            r.raise_for_status(); return r.json()
        except Exception:
            if deneme == 2: raise
            time.sleep(1 + deneme)


# ------------------------------------------------------------------ kod biçimi
def coz(kod, varsayilan_parite="USDT"):
    """'PEPE' | 'PEPE/TRY' | 'PEPE/TRY@OKX' | 'OKX:PEPE/TRY' → (baz, parite, borsa)."""
    k = kod.upper().replace(" ", "")
    borsa = "Binance"
    if k.startswith("OKX:"): borsa, k = "OKX", k[4:]
    if "@" in k:
        k, b = k.split("@", 1); borsa = "OKX" if b.startswith("OKX") else "Binance"
    for ay in ("/", "-"):
        if ay in k:
            baz, par = k.split(ay, 1); return baz, ("TRY" if par in ("TRY", "TL") else "USDT"), borsa
    if k.endswith("-USD"): k = k[:-4]
    return k, varsayilan_parite, borsa


def kod_yap(baz, parite="USDT", borsa="Binance"):
    return f"{baz}/{parite}" + ("@OKX" if borsa == "OKX" else "")


def kripto_mu(kod):
    k = kod.upper()
    return "/" in k or "@OKX" in k or k.startswith("OKX:") or k.endswith("-USD")


# ------------------------------------------------------------------ evren
def binance_pariteler():
    j = _get(f"{BINANCE}/exchangeInfo", permissions="SPOT")
    return pd.DataFrame([{"baz": s["baseAsset"], "parite": s["quoteAsset"], "sembol": s["symbol"], "borsa": "Binance"}
                         for s in j["symbols"] if s["status"] == "TRADING" and s["quoteAsset"] in PARITELER])


def okx_pariteler():
    j = _get(f"{OKX}/public/instruments", instType="SPOT")
    return pd.DataFrame([{"baz": d["baseCcy"], "parite": d["quoteCcy"], "sembol": d["instId"], "borsa": "OKX"}
                         for d in j.get("data", []) if d.get("state") == "live" and d.get("quoteCcy") in PARITELER])


def hacimler():
    """24 saatlik USDT karşılığı hacim (sıralama ve likidite için)."""
    h = {}
    try:
        for t in _get(f"{BINANCE}/ticker/24hr", type="MINI"):
            s = t["symbol"]
            if s.endswith("USDT"): h[("Binance", s[:-4])] = float(t.get("quoteVolume") or 0)
    except Exception:
        pass
    try:
        for t in _get(f"{OKX}/market/tickers", instType="SPOT").get("data", []):
            if t["instId"].endswith("-USDT"):
                h[("OKX", t["instId"][:-5])] = float(t.get("volCcy24h") or 0)
    except Exception:
        pass
    return h


def evren():
    """Tüm coinler: DataFrame[Kod, Binance USDT, Binance TRY, OKX USDT, OKX TRY, Hacim $]. Hacme göre sıralı."""
    parca, notlar = [], []
    for ad, fn in (("Binance", binance_pariteler), ("OKX", okx_pariteler)):
        try:
            d = fn(); parca.append(d); notlar.append(f"{ad}: {len(d)} parite")
        except Exception as ex:
            notlar.append(f"{ad} alınamadı ({str(ex)[:50]})")
    if not parca:
        raise ValueError("Borsa listeleri alınamadı: " + "; ".join(notlar))
    p = pd.concat(parca)
    p = p[~p["baz"].isin(STABIL)]
    pv = p.assign(var=True).pivot_table(index="baz", columns=["borsa", "parite"], values="var", aggfunc="any", fill_value=False)
    pv.columns = [f"{b} {q}" for b, q in pv.columns]
    for c in ("Binance USDT", "Binance TRY", "OKX USDT", "OKX TRY"):
        if c not in pv: pv[c] = False
    hc = hacimler()
    pv["Hacim $"] = [max(hc.get(("Binance", b), 0), hc.get(("OKX", b), 0)) for b in pv.index]
    pv = pv.reset_index().rename(columns={"baz": "Kod"}).sort_values("Hacim $", ascending=False).reset_index(drop=True)
    pv.attrs["not"] = " · ".join(notlar)
    return pv


# ------------------------------------------------------------------ mumlar
def binance_mumlar(sembol, gun=3000):
    """Günlük mumlar (UTC), sayfalayarak geriye doğru; en fazla `gun` gün."""
    out, son = [], None
    while len(out) < gun:
        prm = {"symbol": sembol, "interval": "1d", "limit": 1000}
        if son: prm["endTime"] = son - 1
        k = _get(f"{BINANCE}/klines", **prm)
        if not k: break
        out = k + out; son = int(k[0][0])
        if len(k) < 1000: break
    if not out: raise ValueError(f"Binance {sembol} için mum verisi yok")
    df = pd.DataFrame(out, columns=["t", "Open", "High", "Low", "Close", "Volume", "tk", "QuoteVol", "n", "a", "b", "c"])
    df.index = pd.to_datetime(df["t"], unit="ms").dt.normalize(); df.index.name = None
    return df[["Open", "High", "Low", "Close", "Volume"]].astype(float).iloc[-gun:]


def okx_mumlar(inst, gun=1500):
    out, sonra = [], None
    while len(out) < gun:
        prm = {"instId": inst, "bar": "1Dutc", "limit": 100}
        if sonra: prm["after"] = sonra
        d = _get(f"{OKX}/market/history-candles", **prm).get("data", [])
        if not d: break
        out += d; sonra = d[-1][0]
        if len(d) < 100: break
        time.sleep(0.12)
    if not out: raise ValueError(f"OKX {inst} için mum verisi yok")
    df = pd.DataFrame(out, columns=["t", "Open", "High", "Low", "Close", "Volume", "vq", "vqq", "ok"])
    df.index = pd.to_datetime(df["t"].astype("int64"), unit="ms").dt.normalize(); df.index.name = None
    return df[["Open", "High", "Low", "Close", "Volume"]].astype(float).sort_index().iloc[-gun:]


def mumlar(baz, parite="USDT", borsa="Binance", gun=3000):
    """Tercih edilen borsadan, olmazsa diğerinden günlük OHLCV. (df, kullanılan borsa)"""
    sira = [borsa] + [b for b in BORSALAR if b != borsa]
    son_hata = None
    for b in sira:
        try:
            if b == "Binance": return binance_mumlar(f"{baz}{parite}", gun), "Binance"
            return okx_mumlar(f"{baz}-{parite}", min(gun, 1500)), "OKX"
        except Exception as ex:
            son_hata = ex
    raise ValueError(f"{baz}/{parite} için Binance ve OKX'te veri bulunamadı ({son_hata})")


# ------------------------------------------------------------------ CoinGecko eşlemesi
_CG = {}


def cg_piyasa(sayfa=4):
    """CoinGecko piyasa değeri ilk ~1000 coin: {SEMBOL: kayıt} (aynı sembolde en büyük piyasa değeri)."""
    if _CG: return _CG
    for p in range(1, sayfa + 1):
        try:
            for c in _get(f"{CG}/coins/markets", vs_currency="usd", order="market_cap_desc", per_page=250, page=p):
                s = c["symbol"].upper()
                if s not in _CG: _CG[s] = c
        except Exception:
            break
        time.sleep(1.2)
    return _CG


def cg_id(baz):
    k = cg_piyasa().get(baz.upper())
    if k: return k["id"], k["name"]
    try:
        for c in _get(f"{CG}/search", query=baz).get("coins", []):
            if c["symbol"].upper() == baz.upper(): return c["id"], c["name"]
    except Exception:
        pass
    return None, ESKI.get(baz.upper(), baz.upper())


def cg_kayit(cid):
    """CoinGecko /coins/markets kaydını rapor biçimine çevirir (tek tek /coins/{id} çağrısına gerek bırakmaz)."""
    c = next((x for x in cg_piyasa().values() if x.get("id") == cid), None)
    if not c: raise KeyError(cid)
    p = lambda x: (x / 100) if x is not None else None
    return {"sira": c.get("market_cap_rank"), "piy_deg": c.get("market_cap"), "hacim": c.get("total_volume"),
            "fdv": c.get("fully_diluted_valuation"), "dolasim": c.get("circulating_supply"), "toplam": c.get("total_supply"),
            "maks": c.get("max_supply"), "ath": c.get("ath"), "ath_tarih": c.get("ath_date"), "ath_fark": c.get("ath_change_percentage"),
            "atl": c.get("atl"), "atl_tarih": c.get("atl_date"), "d24": p(c.get("price_change_percentage_24h")),
            "fiyat": c.get("current_price"), "guncelleme": c.get("last_updated"), "kategori": [], "algoritma": None}


def bulten_kodlari(parite="USDT", ev=None):
    """Bülten için tüm coinler: USDT'de Binance öncelikli, TL'de Binance TR / OKX TR."""
    ev = ev if ev is not None else evren()
    out = []
    for _, r in ev.iterrows():
        if r.get(f"Binance {parite}"): out.append(kod_yap(r["Kod"], parite, "Binance"))
        elif r.get(f"OKX {parite}"): out.append(kod_yap(r["Kod"], parite, "OKX"))
    return out
