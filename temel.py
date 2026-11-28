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
    if hatalar:   # hız sınırına takılanlar için yavaş ikinci tur
        import collections
        print("hata nedenleri:", collections.Counter(str(v)[:70] for v in hatalar.values()).most_common(6))
        s2, hatalar = br.tara(list(hatalar), isci=2)
        satirlar += s2
        if hatalar: print("ikinci tur sonrası:", collections.Counter(str(v)[:70] for v in hatalar.values()).most_common(4))
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
    if pz == "bist":
        try: bebek(klasor, satirlar)
        except Exception as x: print("Bebek listesi üretilemedi:", x, file=sys.stderr)


def bebek(klasor, satirlar):
    """Tam uygulamanın Bebek sekmesi (resmi XHARZ bebekleri, genç ve küçük şirketler) + derin analiz (bebek skoru), hazır hesaplanmış.
    Derin analiz için yukarıdaki temel taramanın satırları kullanılır (aynı hesap)."""
    import copy
    import bist_borsa as BB
    import bist_evren as EV
    df, harz, not_ = EV.bist_listesi()
    ilk = EV.ilk_islemler(list(df["Kod"]))
    try: resmi_ilk = BB.ilk_islem()
    except Exception: resmi_ilk = {}
    by = {str(r.get("Kod")): r for r in satirlar}
    out = {"zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "evren": len(df), "not": not_, "modlar": {}}
    for mod in ("resmi", "genc", "kucuk"):
        liste, resmi = EV.bebekler(df, ilk if mod != "kucuk" else {}, set(harz), resmi_ilk=resmi_ilk, mod=mod)
        derin = [copy.deepcopy(by[x["Kod"]]) for x in liste[:150] if x["Kod"] in by]
        derin = EV.bebek_skoru(derin)
        ek = {x["Kod"]: x for x in liste}
        for x in derin:
            x.update({k: v for k, v in ek.get(x["Kod"], {}).items() if k not in x})
            x["Risk notu"] = EV.risk_notlari(x)
        temiz = lambda d: {k: _temiz(v) for k, v in d.items() if not str(k).startswith("_")}
        out["modlar"][mod] = {"resmi": bool(resmi), "liste": [temiz(x) for x in liste],
                              "derin": sorted([temiz(x) for x in derin], key=lambda x: -(x.get("Bebek skoru") or -1))}
        print(f"Bebek ({mod}): {len(liste)} şirket, {len(derin)} derin")
    with open(os.path.join(klasor, "temel", "bebek.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"), default=str)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "cikti", sys.argv[2] if len(sys.argv) > 2 else "bist")
