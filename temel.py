"""Hızlı uygulama için temel analiz özetleri: temel/<bist|abd>.json = {zaman, pz, satirlar: {kod: özet satırı}}.

Tam uygulamanın "Hisse" sekmesindeki değerleme / finansal sağlık hesabının toplu (hafif) hâli: bist_rapor.tara — adil değer ve
potansiyel, sağlık skoru, F/K, PD/DD, ROE, temettü, büyüme modeli, para akışı, yabancı payı, fırsat skoru ve gerekçesi.
BIST: tüm hisseler (kapanış taraması evreni). ABD: en likit ilk 300 hisse. Her gece çalışır (temel.yml); bilançolar seyrek değişir.
Kullanım: python temel.py <cikti> <bist|abd>
"""
import datetime as dt
import json
import math
import os
import sys

import numpy as np

ABD_ADET = 300


def _temiz(v):
    if isinstance(v, (float, np.floating)):
        return None if not math.isfinite(float(v)) else round(float(v), 6)
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (dt.date, dt.datetime)): return str(v)[:10]
    return v


def main(klasor, pz):
    import bist_rapor as br
    import teknik_bulten as TB
    kodlar = TB.evren(pz)
    if pz == "abd":
        kodlar = kodlar[:ABD_ADET]                       # evren likiditeye göre sıralı
        br.baglam("AAPL.US")
    else:
        br.baglam("THYAO")
    print(pz, len(kodlar), "hisse taranıyor…")
    satirlar, hatalar = br.tara(kodlar, isci=6)
    out = {}
    for r in satirlar:
        kod = str(r.get("Kod"))
        if pz == "abd" and not kod.endswith(".US"): kod += ".US"
        out[kod] = {k: _temiz(v) for k, v in r.items() if not str(k).startswith("_")}
    os.makedirs(os.path.join(klasor, "temel"), exist_ok=True)
    with open(os.path.join(klasor, "temel", f"{pz}.json"), "w", encoding="utf-8") as f:
        json.dump({"zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "pz": pz, "satirlar": out,
                   "hata": len(hatalar)}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Temel ({pz}): {len(out)} hisse, {len(hatalar)} hata")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "cikti", sys.argv[2] if len(sys.argv) > 2 else "bist")
