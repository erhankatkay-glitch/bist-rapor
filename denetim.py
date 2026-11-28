import sys, datetime as dt, traceback, pandas as pd
sys.path.insert(0,".")
import alarm as A, veri_kalite as VK
s=dt.datetime(2026,11,27,21,36,tzinfo=dt.timezone.utc)
for f in [lambda: A._yahoo("ASELS"), lambda: VK.tur_bul(A._yahoo("ASELS")), lambda: VK._seans("bist"), lambda: VK.son_kapanis("bist", s), lambda: A.son_tamam_seans("ASELS", s), lambda: A.son_tamam_seans("ASELS")]:
    try: print("OK", f())
    except Exception: traceback.print_exc()
g={"tarih": pd.Timestamp("2026-11-26")}
print("bayat", A.bayat("ASELS", g))
