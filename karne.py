"""PWA 1. adım: seçili varlıkların teknik karnesini önceden hesaplar → karne/<kod>.json + karne/liste.json (bulten dalı).

Hızlı uygulama (docs/index.html) bu dosyaları okuyup varlık sayfasını sunucusuz gösterir: genel görünüm, zaman dilimi puanları,
grafik (son 160 günlük mum + SMA20/50/200 + destek/direnç), seviyeler, pivot, Fibonacci, sinyaller, durum tablosu ve araştırma ekibi.
Varlık listesi: sabit çekirdek liste + açık fırsatlar + son alarmlardaki varlıklar + portföy.txt.
Kullanım: python karne.py <cikti_klasoru>
"""
import concurrent.futures as cf
import datetime as dt
import json
import math
import os
import re
import sys
import time

import numpy as np
import pandas as pd

REPO = "erhankatkay-glitch/bist-rapor"
BIST = ["XU100", "XU030", "AKBNK", "ALARK", "ASELS", "ASTOR", "BIMAS", "EKGYO", "ENKAI", "EREGL", "FROTO", "GARAN", "GUBRF", "ISCTR", "KCHOL",
        "KONTR", "KOZAL", "KRDMD", "MGROS", "PETKM", "PGSUS", "SAHOL", "SASA", "SISE", "TAVHL", "TCELL", "THYAO", "TOASO", "TUPRS", "YKBNK"]
KRIPTO = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT", "ADA/USDT", "AVAX/USDT"]
EMTIA = ["GRAMALTIN", "ALTIN", "GUMUS", "PLATIN", "BAKIR", "BRENT", "WTI", "DOGALGAZ"]
ABD = ["SP500", "NASDAQ", "AAPL.US", "MSFT.US", "NVDA.US", "TSLA.US", "AMZN.US", "GOOGL.US", "META.US", "AVGO.US"]
TUR_PZ = {"hisse": "bist", "abd": "abd", "kripto": "kripto", "emtia": "emtia"}


def dosya_adi(kod):
    return str(kod).replace("/", "-").replace("\\", "-").replace("@", "_").replace(":", "-")


def _f(x, nd=6):
    try:
        x = float(x)
        return None if not math.isfinite(x) else round(x, nd)
    except Exception:
        return None


def _j(o):
    """JSON'a güvenli dönüştürme (numpy, zaman damgası, NaN)."""
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


def varliklar():
    v = list(BIST) + KRIPTO + EMTIA + ABD
    for pz in ("bist", "abd", "kripto", "emtia"):
        for x in bulten(f"firsat/{pz}/acik.json") or []:
            if x.get("durum") == "açık": v.append(x["kod"])
    for x in (bulten("alarm/son.json") or [])[:60]:
        m = re.match(r"^\W*\s*([A-Z0-9]{2,10}(?:/USDT)?)\s*[:·(]", x.get("mesaj", ""))
        if m and (m.group(1) in EMTIA or "/" in m.group(1) or re.fullmatch(r"[A-Z]{4,6}", m.group(1))): v.append(m.group(1))
    try:
        for s in open("portfoy.txt", encoding="utf-8"):
            if s.strip() and not s.startswith("#"): v.append(s.split()[0].upper())
    except Exception:
        pass
    gor, out = set(), []
    for k in v:
        if k not in gor: gor.add(k); out.append(k)
    return out


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


def karne(kod, ek):
    import analist as AN
    import arastirma_ekibi as EK
    import bist_teknik as TK
    s = TK.analiz(kod)
    g = s["tf"].get("G")
    if not g: return None
    pz = TUR_PZ.get(s.get("tur"), "bist")
    op = None
    if s.get("tur") == "kripto":
        op = ((ek.get("opsiyon") or {}).get("paralar") or {}).get(str(s["kod"]).split("/")[0])
    e = None
    try: e = EK.rapor(s, None, ek.get("ist_" + pz), ek.get("rejim_" + pz), op)
    except Exception as x: print("  ekip:", kod, x)
    if e and os.environ.get("GEMINI_API_KEY") or e and os.environ.get("GROQ_API_KEY"):
        try:
            import llm_katman as LLM
            yz = LLM.yorum(e)
            if yz and yz.get("metin"): e["yz"] = yz
        except Exception as x:
            print("  yz:", kod, x)
    return _j({"kod": s["kod"], "ad": s["ad"], "tur": s.get("tur"), "pz": pz, "para": s["para"], "zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
               "fiyat_zamani": str(s.get("fiyat_zamani"))[:16], "etiket": s["etiket"], "puan": round(s["puan"], 1),
               "baslik": AN.teknik_baslik(s), "yorum": AN.teknik_ozet(s), "senaryo": AN.teknik_senaryo(s),
               "tf": {tf: tf_ozet(a) for tf, a in s["tf"].items() if a}, "grafik": grafik(g),
               "gun": {"yuksek": _f(g["h"]["High"].iloc[-1]), "dusuk": _f(g["h"]["Low"].iloc[-1])}, "ekip": e})


def main(klasor):
    os.makedirs(os.path.join(klasor, "karne"), exist_ok=True)
    ek = {"opsiyon": bulten("opsiyon/ozet.json")}
    for pz in ("bist", "abd", "kripto", "emtia"):
        ek["ist_" + pz] = bulten(f"firsat/{pz}/istatistik.json")
        if pz in ("bist", "abd"): ek["rejim_" + pz] = bulten(f"rejim/{pz}.json")
    liste, hata, bas = [], [], time.time()
    v = varliklar(); print(len(v), "varlık")
    yz_var = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY"))

    def is_(kod):
        try:
            k = karne(kod, ek)
            if yz_var: time.sleep(4)   # ücretsiz dil modeli dakika sınırı
            return kod, k, None
        except Exception as x:
            return kod, None, str(x)[:200]

    with cf.ThreadPoolExecutor(2 if yz_var else 4) as hav:
        for kod, k, h in hav.map(is_, v):
            if not k: hata.append({"kod": kod, "hata": h}); print("  ✗", kod, h); continue
            json.dump(k, open(os.path.join(klasor, "karne", dosya_adi(k["kod"]) + ".json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
            liste.append({"kod": k["kod"], "ad": k["ad"], "pz": k["pz"], "etiket": k["etiket"], "puan": k["puan"], "fiyat": k["tf"]["G"]["fiyat"],
                          "degisim": k["tf"]["G"]["degisim"], "para": k["para"], "dosya": dosya_adi(k["kod"]),
                          "seri": [x for x in k["grafik"]["c"][-30:]], "gorunum": (k.get("ekip") or {}).get("gorunum")})
            print("  ✓", kod, k["etiket"])
    json.dump({"zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "varliklar": liste, "hatalar": hata, "sure_sn": round(time.time() - bas)},
              open(os.path.join(klasor, "karne", "liste.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{len(liste)} karne, {len(hata)} hata, {time.time() - bas:.0f} sn")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "cikti")
