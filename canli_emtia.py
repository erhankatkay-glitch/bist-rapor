"""Emtialar için anlık (7/24) fiyat: kripto borsalarının herkese açık, anahtarsız "TradFi" sürekli vadeli kontrat verisi.

Yahoo'nun vadeli emtia fiyatları ~10 dk gecikmeli ve hafta sonu durur. OKX ve Bitget bu emtiaları izleyen sürekli (perpetual)
kontratları 7/24 işler; fiyat normalde vadeli/spot fiyata çok yakındır, resmî piyasa kapalıyken (hafta sonu) aradaki fark açılabilir.
Bu yüzden kaynak etiketi "7/24 türev fiyatı" olarak gösterilir. Binance'in XAU/XAG kontratları ABD sunucularından erişilemediği
(HTTP 451) için kullanılmaz; ons altın zaten Binance PAXG (fiziki altın tokeni) ile anlık.
Brent için açık anlık kaynak yok (Yahoo gecikmeli kalır).
"""
import json, datetime as dt, urllib.request

KAYNAK = {  # varlık kodu: [(borsa, sembol), …] — sırayla denenir
    "GUMUS": [("okx", "XAG-USDT-SWAP"), ("bitget", "XAGUSDT")],
    "PLATIN": [("okx", "XPT-USDT-SWAP"), ("bitget", "XPTUSDT")],
    "BAKIR": [("bitget", "COPPERUSDT")],
    "WTI": [("okx", "CL-USDT-SWAP")],
    "DOGALGAZ": [("okx", "NG-USDT-SWAP"), ("bitget", "NATGASUSDT")],
}
BORSA_AD = {"okx": "OKX", "bitget": "Bitget"}


def _json(u, zaman_asimi=8):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=zaman_asimi).read())


def okx(sembol):
    d = _json(f"https://www.okx.com/api/v5/market/ticker?instId={sembol}")["data"][0]
    son, ac = float(d["last"]), float(d["open24h"])
    return {"fiyat": son, "d24": son / ac - 1 if ac else None, "zaman": dt.datetime.fromtimestamp(int(d["ts"]) / 1000, dt.timezone.utc)}


def bitget(sembol):
    d = _json(f"https://api.bitget.com/api/v2/mix/market/ticker?symbol={sembol}&productType=USDT-FUTURES")["data"][0]
    son = float(d["lastPr"]); ch = d.get("change24h")
    return {"fiyat": son, "d24": float(ch) if ch not in (None, "") else None, "zaman": dt.datetime.fromtimestamp(int(d["ts"]) / 1000, dt.timezone.utc)}


def fiyat(kod, referans=None, sapma=0.10):
    """→ {"fiyat", "d24", "zaman", "kaynak"} ya da None. referans verilirse (ör. Yahoo son fiyatı) %10'dan fazla sapan kaynak atlanır
    (birim farkı / hatalı veri koruması)."""
    for borsa, sem in KAYNAK.get(str(kod).upper(), []):
        try:
            r = (okx if borsa == "okx" else bitget)(sem)
            if not r["fiyat"] or r["fiyat"] <= 0: continue
            if (dt.datetime.now(dt.timezone.utc) - r["zaman"]).total_seconds() > 900: continue    # 15 dk'dan eski: anlık değil
            if referans and abs(r["fiyat"] / referans - 1) > sapma: continue
            r["kaynak"] = f"{BORSA_AD[borsa]} 7/24 türev"
            return r
        except Exception:
            continue
    return None
