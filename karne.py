"""Hızlı uygulama (PWA) varlık karneleri: piyasadaki TÜM varlıkların teknik karnesi → karne/<piyasa>/<kod>.json + karne/<piyasa>/liste.json.

Kaynak: kapanış taramasının (teknik_bulten.calistir) zaten hesapladığı analizler; ek veri çekmez. Kapanış taraması her piyasada
(BIST, ABD, kripto, emtia) karneleri de yazar (teknik_bulten._yaz → yaz_piyasa). Ayrıca bu dosya tek başına çalıştırılabilir:
    python karne.py <cikti> <piyasa>      (piyasa: bist | abd | kripto | emtia)
Hızlı uygulama karneyi okuyup varlık sayfasını sunucusuz gösterir: genel görünüm, zaman dilimleri, grafik (son 160 gün mum + SMA20/50/200
+ destek/direnç), seviyeler, pivot, Fibonacci, sinyaller, gösterge durumları ve araştırma ekibi (kural tabanlı).
"""
import datetime as dt
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

REPO = "erhankatkay-glitch/bist-rapor"
TUR_PZ = {"hisse": "bist", "abd": "abd", "kripto": "kripto", "emtia": "emtia"}


def dosya_adi(kod):
    return str(kod).replace("/", "-").replace("\\", "-").replace("@", "_").replace(":", "-")


def _f(x, anlamli=6):
    """Sayıyı 6 anlamlı basamağa yuvarlar (dosyalar küçük kalsın)."""
    try:
        x = float(x)
        if not math.isfinite(x): return None
        if x == 0: return 0.0
        return round(x, max(0, anlamli - 1 - int(math.floor(math.log10(abs(x))))))
    except Exception:
        return None


def _j(o):
    if isinstance(o, dict): return {str(k): _j(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_j(v) for v in o]
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (float, np.floating)): return _f(o)
    if isinstance(o, (pd.Timestamp, dt.datetime, dt.date)): return str(o)[:16]
    if isinstance(o, (np.bool_,)): return bool(o)
    return o


def bulten(yol):
    import requests
    try:
        r = requests.get(f"https://raw.githubusercontent.com/{REPO}/bulten/{yol}?t={int(time.time())}", timeout=20)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def tf_ozet(a):
    G = a["G"]
    son = lambda c: _f(G[c].iloc[-1]) if c in G else None
    return {"etiket": a["etiket"], "puan": round(a["puan"], 1), "fiyat": _f(a["fiyat"]), "degisim": _f(a.get("degisim")),
            "sayim": a["oy"].get("sayim"), "ma": a["oy"].get("ma_etiket"), "osc": a["oy"].get("osc_etiket"),
            "rsi": son("RSI"), "atr": son("ATR"), "sma50": son("SMA50"), "sma200": son("SMA200"),
            "destek": [[_f(p), int(g)] for p, g in a["sr"]["destek"]], "direnc": [[_f(p), int(g)] for p, g in a["sr"]["direnc"]],
            "pivot": {k: _f(v) for k, v in a["pivot"]["Klasik"].items()},
            "fib": ({"yukari": a["fib"]["yukari"], "tepe": _f(a["fib"]["tepe"]), "dip": _f(a["fib"]["dip"]),
                     "seviye": {str(k): _f(v) for k, v in dict(a["fib"]["seviye"]).items()}} if a.get("fib") else None),
            "yapi": a["pa"].get("yapi"),
            "sinyal": [{"ad": x[0], "yon": int(x[1]), "aciklama": x[2], "guc": int(x[3])} for x in sorted(a["sinyal"], key=lambda x: -x[3])[:14]],
            "durum": [{"ad": d[0], "deger": d[1], "aciklama": d[2], "yon": int(d[3]) if len(d) > 3 and d[3] is not None else 0} for d in a["durum"][:40]]}


def grafik(a, n=160):
    h = a["h"].iloc[-n:]; G = a["G"].iloc[-n:]
    return {"t": [x.strftime("%Y-%m-%d") for x in h.index], "o": [_f(x) for x in h["Open"]], "h": [_f(x) for x in h["High"]],
            "l": [_f(x) for x in h["Low"]], "c": [_f(x) for x in h["Close"]],
            "sma20": [_f(x) for x in G["SMA20"]], "sma50": [_f(x) for x in G["SMA50"]], "sma200": [_f(x) for x in G["SMA200"]]}


def ek_veri(pz):
    """Araştırma ekibi için piyasa bağlamı (bulten dalından): fırsat istatistikleri, rejim, kripto opsiyon."""
    return {"ist": bulten(f"firsat/{pz}/istatistik.json"), "rejim": bulten(f"rejim/{pz}.json") if pz in ("bist", "abd") else None,
            "opsiyon": bulten("opsiyon/ozet.json") if pz == "kripto" else None}


def karne(s, ek):
    """Hazır analizden (bist_teknik.analiz çıktısı) karne sözlüğü."""
    import analist as AN
    import arastirma_ekibi as EK
    g = s["tf"].get("G")
    if not g: return None
    pz = TUR_PZ.get(s.get("tur"), "bist")
    op = ((ek.get("opsiyon") or {}).get("paralar") or {}).get(str(s["kod"]).split("/")[0]) if pz == "kripto" else None
    try: e = EK.rapor(s, None, ek.get("ist"), ek.get("rejim"), op)
    except Exception: e = None
    return _j({"kod": s["kod"], "ad": s["ad"], "tur": s.get("tur"), "pz": pz, "para": s["para"],
               "zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "fiyat_zamani": str(s.get("fiyat_zamani"))[:16],
               "etiket": s["etiket"], "puan": round(s["puan"], 1), "baslik": AN.teknik_baslik(s), "yorum": AN.teknik_ozet(s),
               "senaryo": AN.teknik_senaryo(s), "tf": {tf: tf_ozet(a) for tf, a in s["tf"].items() if a}, "grafik": grafik(g),
               "gun": {"yuksek": _f(g["h"]["High"].iloc[-1]), "dusuk": _f(g["h"]["Low"].iloc[-1])}, "ekip": e})


def yaz_piyasa(pz, analizler, klasor, endeks=None):
    """Bir piyasanın tüm analizlerini karne/<pz>/ altına yazar (klasör yayında bütün olarak değişir)."""
    hedef = os.path.join(klasor, "karne", pz)
    os.makedirs(hedef, exist_ok=True)
    ek = ek_veri(pz); liste = []
    for s in ([endeks] if endeks else []) + list(analizler):
        try:
            k = karne(s, ek)
        except Exception as x:
            print("  karne", s.get("kod"), x, file=sys.stderr); continue
        if not k or any(v["kod"] == k["kod"] for v in liste): continue
        k["pz"] = pz
        with open(os.path.join(hedef, dosya_adi(k["kod"]) + ".json"), "w", encoding="utf-8") as f:
            json.dump(k, f, ensure_ascii=False, separators=(",", ":"))
        G = k["tf"]["G"]
        liste.append({"kod": k["kod"], "ad": k["ad"], "etiket": k["etiket"], "puan": k["puan"], "fiyat": G["fiyat"], "degisim": G["degisim"],
                      "para": k["para"], "seri": k["grafik"]["c"][-30:], "tarih": k["grafik"]["t"][-1], "gorunum": (k.get("ekip") or {}).get("gorunum")})
    with open(os.path.join(hedef, "liste.json"), "w", encoding="utf-8") as f:
        json.dump({"zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "pz": pz, "varliklar": liste},
                  f, ensure_ascii=False, separators=(",", ":"))
    print(f"Karne ({pz}): {len(liste)} varlık → {hedef}")
    return len(liste)


def main(klasor, pz):
    """Kapanış taramasından bağımsız tam yenileme (ör. elle ya da gün ortası)."""
    import concurrent.futures as cf
    import bist_teknik as T
    import teknik_bulten as TB
    kodlar = TB.evren(pz); ref = TB.REFERANS[pz]
    print(pz, len(kodlar), "varlık")
    if pz == "kripto":
        def is_(k):
            try: return T.analiz(k)
            except Exception as x: print("  ✗", k, str(x)[:80]); return None
        with cf.ThreadPoolExecutor(4) as hav:
            analizler = [s for s in hav.map(is_, kodlar) if s]
        try: endeks = T.analiz(ref)
        except Exception: endeks = None
    else:
        semboller = [T.yahoo_sembol(k)[0] for k in kodlar + [ref]] + (["TRY=X", "GC=F"] if pz == "emtia" else [])
        veri = TB.gunu_tamamla(TB.toplu_veri(semboller, "10y"))
        fn = lambda y, *a: veri[y]
        analizler = []
        for k in kodlar:
            try: analizler.append(T.analiz(k, fiyat_fn=fn))
            except Exception as x: print("  ✗", k, str(x)[:80])
        try:
            endeks = T.analiz(ref, fiyat_fn=fn)
            endeks["ad"] = {"XU100": "BIST 100", "SP500": "S&P 500"}.get(ref, endeks["ad"])
        except Exception: endeks = None
    yaz_piyasa(pz, analizler, klasor, endeks)
    if pz in ("bist", "abd") and endeks:   # piyasa rejimini de aynı (tamamlanmış) veriyle tazele — Telegram göndermez
        try:
            import rejim as RJ
            r = RJ.hesapla(pz, analizler, endeks["tf"]["G"]["h"], klasor, vix=RJ.vix_al() if pz == "abd" else None)
            print("Rejim:", r["durum_ad"], r["maruziyet"], r.get("kapanis"))
        except Exception as x:
            print("Rejim tazelenemedi:", x, file=sys.stderr)
    if pz == "bist":   # dünya piyasaları özeti (Telegram göndermez)
        try:
            import dunya as DN
            DN.hesapla(klasor)
        except Exception as x:
            print("Dünya özeti tazelenemedi:", x, file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "cikti", sys.argv[2] if len(sys.argv) > 2 else "bist")
