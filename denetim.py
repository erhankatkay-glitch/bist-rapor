import sys, pandas as pd, numpy as np
sys.path.insert(0,".")
import teknik_bulten as TB, rejim as RJ, bist_teknik as T
kod=TB.evren("bist")
sem=[T.yahoo_sembol(k)[0] for k in kod+["XU100"]]
v=TB.gunu_tamamla(TB.toplu_veri(sem,"10y")); fn=lambda y,*a: v[y]
an=[]
for k in kod[:200]:
    try: an.append(T.analiz(k, fiyat_fn=fn))
    except Exception: pass
kap={s["kod"]: s["tf"]["G"]["h"]["Close"] for s in an}
L=pd.Series({k:len(c) for k,c in kap.items()}); print("analiz h uzunluk", L.describe().round(0).to_dict())
ham={k: v[T.yahoo_sembol(k)[0]]["Close"] for k in kap}; print("ham uzunluk", pd.Series({k:len(c.dropna()) for k,c in ham.items()}).describe().round(0).to_dict())
print("analiz G:", RJ.genislik(kap).tail(2)); print("ham G:", RJ.genislik(ham).tail(2))
C=pd.DataFrame({k:s[~s.index.duplicated()] for k,s in kap.items()}).sort_index().ffill(limit=3)
print("tarih sayisi", len(C), "son 3", [str(i) for i in C.index[-3:]]); print("satir basina NaN (son 250 satirda max)", int(C.iloc[-250:].isna().sum(axis=1).max()))
bad=C.iloc[-250:].isna().sum(axis=1); print(bad[bad>len(kap)*0.5].tail(5))
