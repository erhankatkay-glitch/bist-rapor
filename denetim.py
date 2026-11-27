"""Fiyat denetimi: Yahoo günlük/15dk, İş Yatırım resmi kapanış, Binance PAXG, bülten özet.csv karşılaştırması."""
import json, urllib.request, datetime as dt, os
import pandas as pd, yfinance as yf
os.makedirs("denetim_graf", exist_ok=True)
pd.set_option("display.width", 250)
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.isyatirim.com.tr/"}), timeout=20).read()
BIST = ["XU100", "XU030", "THYAO", "ASELS", "GARAN", "BIMAS", "TUPRS", "KCHOL", "AKBNK", "ASTOR", "VAKBN", "KATMR"]
print("=== Yahoo günlük (son 3) ve 15 dk (son 3)")
for k in BIST:
    try:
        d = yf.Ticker(k + ".IS").history(period="7d", interval="1d", auto_adjust=False)
        g = yf.Ticker(k + ".IS").history(period="2d", interval="15m", auto_adjust=False)
        print(k, "GÜNLÜK", [(str(i)[:10], round(float(c), 3)) for i, c in d["Close"].tail(3).items()],
              "| 15DK", [(str(i)[11:16], round(float(c), 3)) for i, c in g["Close"].tail(3).items()])
    except Exception as ex:
        print(k, "HATA", ex)
print("\n=== İş Yatırım HisseTekil (resmi kapanış)")
bug = dt.date.today(); bas = bug - dt.timedelta(days=7)
for k in BIST:
    try:
        u = f"https://www.isyatirim.com.tr/_layouts/15/Isyatirim.Website/Common/Data.aspx/HisseTekil?hisse={k}&startdate={bas:%d-%m-%Y}&enddate={bug:%d-%m-%Y}.json"
        j = json.loads(get(u))
        v = j.get("value") or []
        print(k, [(x.get("HGDG_TARIH"), x.get("HGDG_KAPANIS"), x.get("HGDG_AOF")) for x in v[-3:]])
    except Exception as ex:
        print(k, "HATA", str(ex)[:120])
print("\n=== Bülten bist/ozet.csv")
try:
    oz = pd.read_csv("https://raw.githubusercontent.com/erhankatkay-glitch/bist-rapor/bulten/bist/ozet.csv")
    print(oz[oz["Kod"].isin(BIST)][[c for c in oz.columns if c in ("Kod", "Fiyat", "Değişim", "Tarih", "tarih", "Zaman")]].to_string())
    print("sütunlar:", list(oz.columns)[:20])
except Exception as ex:
    print("ozet HATA", ex)
print("\n=== Altın / döviz / emtia")
for s in ["GC=F", "SI=F", "BZ=F", "TRY=X", "EURTRY=X", "^GSPC", "^IXIC", "DX-Y.NYB", "^TNX", "^VIX", "BTC-USD"]:
    try:
        g = yf.Ticker(s).history(period="2d", interval="15m")
        d = yf.Ticker(s).history(period="5d", interval="1d")
        print(s, "son15", str(g.index[-1])[:16], round(float(g["Close"].iloc[-1]), 4), "| günlük", [(str(i)[:10], round(float(c), 4)) for i, c in d["Close"].tail(2).items()])
    except Exception as ex:
        print(s, "HATA", ex)
for sym in ("PAXGUSDT", "BTCUSDT", "XAUTUSDT"):
    try:
        j = json.loads(get(f"https://data-api.binance.vision/api/v3/ticker/24hr?symbol={sym}")); print(sym, j["lastPrice"], j["priceChangePercent"])
    except Exception as ex:
        print(sym, "HATA", str(ex)[:80])
import bist_makro as mk
pv = mk.piyasa_paneli()
for ad, v in pv.items(): print(f"PV {ad:14s} {v['deger']:.4f} d1G={((v.get('d1G') or 0)*100):+.2f}% {v.get('kaynak')} {v.get('zaman')}")
