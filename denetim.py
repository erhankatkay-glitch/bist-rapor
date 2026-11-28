import sys; sys.path.insert(0, ".")
import pandas as pd, bist_kripto as K
parca = [K.binance_pariteler(), K.okx_pariteler()]
p = pd.concat(parca); p = p[~p["baz"].isin(K.STABIL)]
bazlar = sorted(set(p["baz"]))
eski = lambda b: (b in K._HISSE) or (b.startswith("X") and b[1:] in K._HISSE and len(b) >= 4) or (b[-1:] in "BX" and b[:-1] in K._HISSE and len(b) >= 4) or (b.endswith("ON") and b[:-2] in K._HISSE and len(b) >= 5)
yeni = [b for b in bazlar if K.hisse_tokeni_mu(b) and not eski(b)]
print("TOPLAM", len(bazlar), "ESKI", sum(map(eski, bazlar)), "YENI_ELENEN", len(yeni))
print("YENI", " ".join(yeni))
