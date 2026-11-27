"""Fiyat denetimi (düzeltme sonrası)."""
import os
os.makedirs("denetim_graf", exist_ok=True)
import bist_makro as mk, bist_teknik as T, alarm as AL
pv = mk.piyasa_paneli()
for ad in ("BIST 100", "Ons altın", "Gram altın", "USD/TRY", "Gümüş", "Brent petrol", "Bitcoin", "S&P 500", "BIST 100 ($)"):
    v = pv.get(ad); print(f"PV {ad:14s} {v['deger']:.2f} d1G={((v.get('d1G') or 0)*100):+.2f}% {v.get('kaynak')}")
for k in ("XU100", "XU030", "THYAO", "ASELS", "GARAN", "BIMAS", "TUPRS", "KCHOL", "AKBNK", "ALTIN", "GRAMALTIN"):
    try:
        h, _ = T.gunluk_veri(k); c = h["Close"]
        print(f"TEKNİK {k:10s} {c.index[-1]:%Y-%m-%d} {c.iloc[-1]:.2f} ({(c.iloc[-1]/c.iloc[-2]-1)*100:+.2f}%)", end=" | ")
        s, d = AL.anlik(k); print(f"ALARM {s:.2f} ({d*100:+.2f}%)")
    except Exception as ex:
        print(k, "HATA", ex)
