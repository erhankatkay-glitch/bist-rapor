import sys, pandas as pd, numpy as np
sys.path.insert(0,".")
import teknik_bulten as TB, rejim as RJ, bist_teknik as T
kod=TB.evren("bist")
sem=[T.yahoo_sembol(k)[0] for k in kod]
v=TB.gunu_tamamla(TB.toplu_veri(sem,"10y"))
ham={k: v[s]["Close"] for k,s in zip(kod,sem) if s in v and v[s] is not None and len(v[s])}
G=RJ.genislik(ham); print(G.tail(4))
C=pd.DataFrame({k:s[~s.index.duplicated()] for k,s in ham.items() if len(s)>=60}).sort_index()
print("son 4 tarih", [str(i) for i in C.index[-4:]], "son satir dolu", int(C.iloc[-1].notna().sum()))
C2=C.ffill(limit=3); s200=C2.rolling(200,min_periods=200).mean()
print("s200 gecerli son", int(s200.iloc[-1].notna().sum()), "ust", int((C2.iloc[-1]>s200.iloc[-1]).sum()))
print("s200 gecerli 5 gun once", int(s200.iloc[-6].notna().sum()))
r=C2.iloc[-260:]; nn=r.isna().sum(axis=1); print("NaN cok olan satirlar", nn[nn>50].tail(8).to_dict())
