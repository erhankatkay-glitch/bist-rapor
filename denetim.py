import yfinance as yf, pandas as pd
for s in ["XU100.IS","THYAO.IS","ASELS.IS","GARAN.IS"]:
    d=yf.Ticker(s).history(period="10d", interval="1d", auto_adjust=False)
    print("GUNLUK",s, [(str(i.date()), round(c,2)) for i,c in d["Close"].tail(4).items()])
    for per,ara in (("5d","15m"),("1d","1m")):
        g=yf.Ticker(s).history(period=per, interval=ara, auto_adjust=False)
        if g.empty: print("  ",ara,"bos"); continue
        g=g.dropna(subset=["Close"])
        gun=g.groupby(g.index.date)
        print("  ",ara,[(str(k), round(v["Close"].iloc[-1],2), str(v.index[-1].time()), len(v)) for k,v in gun])
    try:
        fi=yf.Ticker(s).fast_info; print("   fast last", fi.get("lastPrice"), "prev", fi.get("previousClose"))
    except Exception as e: print("   fast hata",e)
