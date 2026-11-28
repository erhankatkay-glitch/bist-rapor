import sys, pandas as pd, numpy as np
sys.path.insert(0,".")
import yfinance as yf, teknik_bulten as TB, rejim as RJ, bist_teknik as T
d=yf.Ticker("XU100.IS").history(period="15d", interval="1d", auto_adjust=True)
print("XU100 GUNLUK\n", d[["Open","High","Low","Close","Volume"]].tail(6).round(1))
kod=TB.evren("bist")[:120]
sem=[T.yahoo_sembol(k)[0] for k in kod+["XU100"]]
v=TB.gunu_tamamla(TB.toplu_veri(sem,"2y"))
x=v["XU100.IS"]; print("XU100 tamamlanmis\n", x[["Open","High","Low","Close","Volume"]].tail(4).round(1))
S,son=RJ.durum_makinesi(x, RJ.AYAR["bist"]["ftd"], RJ.AYAR["bist"]["dd"]); print("SON", son["durum"], son["kapanis"])
# dip izleme
h=x.dropna(subset=["Close"]); print("Low son 12:", h["Low"].tail(12).round(1).tolist())
kap={k: v[s]["Close"] for k,s in zip(kod,sem[:-1]) if s in v}
C=pd.DataFrame({k:s[~s.index.duplicated()] for k,s in kap.items() if len(s)>=60}).sort_index()
print("C sekil", C.shape, "son satirda NaN orani", round(C.iloc[-1].isna().mean(),3), "son 5 tarih", [str(i.date()) for i in C.index[-5:]])
na=C.isna().sum(); print("NaN sayisi dagilimi", na.describe().round(1).to_dict())
G=RJ.genislik(kap); print(G.tail(3))
C2=C.ffill(limit=3); s200=C2.rolling(200,min_periods=200).mean(); print("s200 gecerli son satir", int(s200.iloc[-1].notna().sum()), "C>s200", int((C2.iloc[-1]>s200.iloc[-1]).sum()))
