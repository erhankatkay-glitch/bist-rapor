import yfinance as yf
for k in ["NETGL","BKRGY","INTET","KPEKS","TKNKA","EGEGY"]:
    d=yf.Ticker(k+".IS").history(period="max",auto_adjust=True)
    m=yf.Ticker(k+".IS").history(period="max",interval="1mo",auto_adjust=True)
    print(k, "gunluk ilk:", d.index[0].date(), round(d["Open"].iloc[0],2), round(d["Close"].iloc[0],2), "max", round(d["High"].max(),2), "son", round(d["Close"].iloc[-1],2), "| aylik ilk open", round(m["Open"].iloc[0],2), m.index[0].date(), "| splits", list(yf.Ticker(k+".IS").splits.items())[-2:])
