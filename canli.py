"""Hızlı uygulama için gün içi canlı fiyatlar: canli/<piyasa>.json = {zaman, fiyat: {kod: [son, gunluk_degisim, "SS:DD"]}}.

Seans açıkken (ve kapanıştan sonraki ilk yarım saatte) 15 dakikada bir çalışır (canli.yml). Kod listesi karnelerden
(bulten/karne/<pz>/liste.json) alınır; Yahoo'dan toplu 15 dk veri çekilir (BIST ~15 dk gecikmeli — tam uygulamayla aynı kaynak).
Değişim = son fiyat / önceki seans kapanışı − 1. Kripto bu dosyada yok: uygulama kripto fiyatlarını doğrudan Binance'ten alır.
Kullanım: python canli.py <cikti> [bist abd emtia]   (piyasa verilmezse seansı açık olanlar)
"""
import datetime as dt
import json
import os
import sys

import pandas as pd

import karne as KA


def acik_mi(pz, simdi=None):
    import veri_kalite as VK
    simdi = simdi or dt.datetime.now(dt.timezone.utc)
    tur = {"bist": "bist", "abd": "abd", "emtia": "emtia"}[pz]
    if VK.piyasa_acik(tur, simdi): return True
    try:   # kapanıştan sonraki 40 dk: kapanış fiyatı da yansısın
        return dt.timedelta(0) <= simdi - VK.son_kapanis(tur, simdi) <= dt.timedelta(minutes=40)
    except Exception:
        return False


def fiyatlar(pz):
    import yfinance as yf
    import bist_teknik as T
    L = (KA.bulten(f"karne/{pz}/liste.json") or {}).get("varliklar") or []
    kod_sem = {}
    for v in L:
        try: kod_sem[v["kod"]] = T.yahoo_sembol(v["kod"])[0]
        except Exception: pass
    if not kod_sem: return {}
    sem = list(dict.fromkeys(kod_sem.values())); out = {}
    son_k = {v["kod"]: (v.get("fiyat"), v.get("tarih")) for v in L}   # karnedeki son günlük kapanış
    for i in range(0, len(sem), 200):
        grup = sem[i:i + 200]
        try:
            gi = yf.download(grup, period="5d", interval="15m", auto_adjust=False, progress=False, group_by="ticker", threads=True)
            gd = yf.download(grup, period="10d", interval="1d", auto_adjust=False, progress=False, group_by="ticker", threads=True)
        except Exception as x:
            print("indirme:", x, file=sys.stderr); continue
        for kod, s in kod_sem.items():
            if s not in grup: continue
            try:
                d = (gi[s] if isinstance(gi.columns, pd.MultiIndex) else gi).dropna(subset=["Close"])
                if d.empty: continue
                z = d.index[-1]
                yerel = z.tz_convert("Europe/Istanbul") if z.tzinfo else z
                gun_yerel = (z.tz_convert(KA_tz(pz)) if z.tzinfo else z).date()
                p = float(d["Close"].iloc[-1])
                g = (gd[s] if isinstance(gd.columns, pd.MultiIndex) else gd)["Close"].dropna()
                g.index = pd.DatetimeIndex(g.index).tz_localize(None).normalize() if g.index.tz is not None else pd.DatetimeIndex(g.index).normalize()
                onceki = g[g.index.date < gun_yerel]
                ref = float(onceki.iloc[-1]) if len(onceki) else None
                if ref is None and son_k.get(kod, (None, None))[0]: ref = son_k[kod][0]
                out[kod] = [KA._f(p), KA._f(p / ref - 1) if ref else None, yerel.strftime("%H:%M"), str(gun_yerel)]
            except Exception:
                continue
    return out


def KA_tz(pz):
    import veri_kalite as VK
    return VK._seans({"bist": "bist", "abd": "abd", "emtia": "emtia"}[pz])[0]


def main(klasor, piyasalar):
    os.makedirs(os.path.join(klasor, "canli"), exist_ok=True)
    for pz in piyasalar:
        if not acik_mi(pz) and len(sys.argv) <= 2:
            print(pz, "seans kapalı, atlandı"); continue
        f = fiyatlar(pz)
        if not f: print(pz, "veri yok"); continue
        json.dump({"zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "pz": pz, "fiyat": f},
                  open(os.path.join(klasor, "canli", f"{pz}.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print(pz, len(f), "fiyat")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "cikti", sys.argv[2:] or ["bist", "abd", "emtia"])
