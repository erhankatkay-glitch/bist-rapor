"""Emtia anlık veri kaynakları erişim testi (GitHub ABD sunucusu)."""
import requests, json, time
def dene(ad, url, f):
    try:
        t = time.time(); r = requests.get(url, timeout=20)
        print(f"{ad:28s} HTTP {r.status_code} {round(time.time()-t,2)}s ·", f(r.json()) if r.ok else r.text[:120])
    except Exception as ex: print(f"{ad:28s} HATA {str(ex)[:120]}")
dene("Binance fapi exchangeInfo", "https://fapi.binance.com/fapi/v1/exchangeInfo",
     lambda j: [s["symbol"] for s in j["symbols"] if s.get("underlyingType") not in ("COIN",) or s["symbol"][:3] in ("XAU", "XAG", "XPT", "XPD")][:60])
dene("Binance fapi XAG fiyat", "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=XAGUSDT", lambda j: (j["lastPrice"], j["priceChangePercent"], j["closeTime"]))
dene("Binance fapi XAU fiyat", "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=XAUUSDT", lambda j: (j["lastPrice"], j["priceChangePercent"], j["closeTime"]))
dene("Binance spot PAXG", "https://data-api.binance.vision/api/v3/ticker/price?symbol=PAXGUSDT", lambda j: j)
dene("OKX enstrüman XAU/XAG/oil", "https://www.okx.com/api/v5/public/instruments?instType=SWAP",
     lambda j: [x["instId"] for x in j["data"] if any(k in x["instId"] for k in ("XAU", "XAG", "OIL", "WTI", "BRENT", "CL-", "XPT", "NG-", "COPPER"))])
dene("Bybit tickers linear", "https://api.bybit.com/v5/market/tickers?category=linear",
     lambda j: [(x["symbol"], x["lastPrice"]) for x in j["result"]["list"] if any(k in x["symbol"] for k in ("XAU", "XAG", "OIL", "WTI", "BRENT", "XPT", "NATGAS", "COPPER"))])
dene("Bitget mix (TradFi)", "https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES",
     lambda j: [(x["symbol"], x["lastPr"]) for x in j["data"] if any(k in x["symbol"] for k in ("XAU", "XAG", "OIL", "WTI", "BRENT", "XPT", "NATGAS", "COPPER"))])
dene("Hyperliquid meta", "https://api.hyperliquid.xyz/info", lambda j: j) if False else None
try:
    r = requests.post("https://api.hyperliquid.xyz/info", json={"type": "perpDexs"}, timeout=20); print("Hyperliquid perpDexs", r.status_code, str(r.json())[:300])
except Exception as ex: print("Hyperliquid HATA", ex)
