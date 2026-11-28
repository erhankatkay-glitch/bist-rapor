# -*- coding: utf-8 -*-
"""Temel listelerin karnesi ve günlük temel değişimleri (sabah özeti iş akışında, sabah.py'den önce çalışır).

1) Her sabah gece hesaplanan temel listelerin (bulten/temel/*.json) anlık görüntüsü arşive eklenir (temel/gecmis.json, son 100 gün):
   BIST ve ABD'de "değerinin altında" ilk 10, en yüksek bebek skorlu 10 halka arz, kripto temel puanı en yüksek 10 (ilk 100),
   emtia genel skoru en yüksek 3; ayrıca tüm evrenin fiyatları (kıyas için eşit ağırlıklı evren getirisi).
2) Karne (temel/karne.json): her liste için 1 hafta / 1 ay / 3 ay sonra ortalama getiri, aynı dönemde evrenin ortalama getirisi,
   fark (alfa) ve listenin evreni kaç kez geçtiği. Böylece puanların gerçekten işe yarayıp yaramadığı veriyle görülür.
3) Değişimler (temel/degisim.json): dünden bugüne listeye yeni girenler, spekülatör konumunda (COT) yeni aşırılık,
   kripto temel puanında sert düşüş. temel_bildirim.py bunları sabah temel özeti kartının başına koyar.
Kullanım: python temel_karne.py <cikti>   (önceki durum: DURUM_KLON, varsayılan "onceki")"""
import datetime as dt
import json
import os
import sys

KLON = os.environ.get("DURUM_KLON", "onceki")
TSI = dt.timezone(dt.timedelta(hours=3))
SAKLA_GUN = 100
ESKI_SAAT = 36
UFUK = {"1H": 7, "1A": 30, "3A": 91}
LISTE = {"bist_deger": ("BIST · değerinin altında (ilk 10)", "bist"), "abd_deger": ("ABD · değerinin altında (ilk 10)", "abd"),
         "bebek": ("Halka arzlar · bebek skoru (ilk 10)", "bist"), "kripto_puan": ("Kripto · temel puan (ilk 10, ilk 100 coin)", "kripto"),
         "emtia_skor": ("Emtia · genel skor (ilk 3)", "emtia")}


def _oku(yol, v=None):
    try: return json.load(open(yol, encoding="utf-8"))
    except Exception: return v


def _taze(d):
    try: return d and (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(d["zaman"])).total_seconds() < ESKI_SAAT * 3600
    except Exception: return False


def _f(x):
    try: return float(f"{float(x):.6g}") if x else None
    except Exception: return None


def deger_listesi(T, n=10):
    R = [(k, t) for k, t in (T or {}).get("satirlar", {}).items() if "ALTINDA" in str(t.get("Görüş") or "") and t.get("Fırsat skoru") is not None
         and not (t.get("F/K") is not None and t["F/K"] < 1)]
    return [k for k, _ in sorted(R, key=lambda x: -x[1]["Fırsat skoru"])[:n]]


def goruntu(klasor_temel):
    """Bugünün listeleri ve fiyatları; taze olmayan piyasa atlanır."""
    T = {p: _oku(os.path.join(klasor_temel, f"{p}.json")) for p in ("bist", "abd", "kripto", "emtia", "bebek")}
    T = {p: d for p, d in T.items() if _taze(d)}
    g = {"listeler": {}, "fiyat": {}, "cot": {}, "kpuan": {}}
    for p in ("bist", "abd", "kripto", "emtia"):
        if p in T: g["fiyat"][p] = {k: _f(t.get("Fiyat")) for k, t in T[p]["satirlar"].items() if _f(t.get("Fiyat"))}
    if "bist" in T: g["listeler"]["bist_deger"] = deger_listesi(T["bist"])
    if "abd" in T: g["listeler"]["abd_deger"] = deger_listesi(T["abd"])
    if "bebek" in T and "bist" in g["fiyat"]:
        d = sorted([x for x in ((T["bebek"].get("modlar") or {}).get("resmi") or {}).get("derin", []) if x.get("Bebek skoru") is not None],
                   key=lambda x: -x["Bebek skoru"])
        g["listeler"]["bebek"] = [x["Kod"] for x in d if x["Kod"] in g["fiyat"]["bist"]][:10]
    if "kripto" in T:
        S = T["kripto"]["satirlar"]
        ilk = {k: t for k, t in S.items() if t.get("Temel puan") is not None and (t.get("Sıra") or 999) <= 100}
        g["listeler"]["kripto_puan"] = [k for k, _ in sorted(ilk.items(), key=lambda x: -x[1]["Temel puan"])[:10]]
        g["kpuan"] = {k: t["Temel puan"] for k, t in ilk.items()}
        g["fiyat"]["kripto"] = {k: v for k, v in g["fiyat"]["kripto"].items() if S[k].get("Temel puan") is not None}   # kıyas: puanlanan coinler
    if "emtia" in T:
        S = {k: t for k, t in T["emtia"]["satirlar"].items() if k != "GRAMALTIN"}
        g["fiyat"]["emtia"] = {k: v for k, v in g["fiyat"]["emtia"].items() if k in S}
        g["listeler"]["emtia_skor"] = [k for k, _ in sorted([x for x in S.items() if x[1].get("Skor") is not None], key=lambda x: -x[1]["Skor"])[:3]]
        g["cot"] = {k: round(t["COT"]["spek_yuzdelik_3y"], 3) for k, t in S.items() if (t.get("COT") or {}).get("spek_yuzdelik_3y") is not None}
    return g, T


def _getiri(f0, f1, kodlar):
    r = [f1[k] / f0[k] - 1 for k in kodlar if f0.get(k) and f1.get(k)]
    return (sum(r) / len(r), r) if r else (None, [])


def karne(G):
    """G: {tarih: görüntü}. Her liste ve ufuk için: dönem sayısı, ort. getiri, ort. evren getirisi, ort. fark, evreni geçme oranı."""
    tarihler = sorted(G); out = {}
    for ad, (baslik, pz) in LISTE.items():
        o = {"baslik": baslik, "pz": pz, "ufuklar": {}}
        for u, gun in UFUK.items():
            D = []
            for t0 in tarihler:
                g0 = G[t0]
                if ad not in g0["listeler"] or pz not in g0["fiyat"]: continue
                hedef = dt.date.fromisoformat(t0) + dt.timedelta(days=gun)
                aday = [t for t in tarihler if abs((dt.date.fromisoformat(t) - hedef).days) <= 3 and pz in G[t]["fiyat"]]
                if not aday: continue
                t1 = min(aday, key=lambda t: abs((dt.date.fromisoformat(t) - hedef).days))
                f0, f1 = g0["fiyat"][pz], G[t1]["fiyat"][pz]
                lg, rl = _getiri(f0, f1, g0["listeler"][ad]); eg, re_ = _getiri(f0, f1, list(f0))
                if lg is None or eg is None: continue
                med = sorted(re_)[len(re_) // 2]
                D.append({"t0": t0, "t1": t1, "liste": lg, "evren": eg, "fark": lg - eg, "isabet": sum(x > med for x in rl) / len(rl)})
            if D:
                n = len(D)
                o["ufuklar"][u] = {"n": n, "liste": sum(x["liste"] for x in D) / n, "evren": sum(x["evren"] for x in D) / n,
                                   "fark": sum(x["fark"] for x in D) / n, "gecti": sum(x["fark"] > 0 for x in D) / n,
                                   "isabet": sum(x["isabet"] for x in D) / n, "son": D[-1]}
        # en son listenin bugüne kadarki durumu (en yeni 7+ günlük görüntü)
        bugun = tarihler[-1] if tarihler else None
        if bugun:
            eski = [t for t in tarihler if (dt.date.fromisoformat(bugun) - dt.date.fromisoformat(t)).days >= 7 and ad in G[t]["listeler"] and pz in G[t]["fiyat"]]
            if eski and pz in G[bugun]["fiyat"]:
                t0 = eski[-1]; f0, f1 = G[t0]["fiyat"][pz], G[bugun]["fiyat"][pz]
                o["izlenen"] = {"t0": t0, "kodlar": [[k, f1[k] / f0[k] - 1 if f0.get(k) and f1.get(k) else None] for k in G[t0]["listeler"][ad]],
                                "evren": _getiri(f0, f1, list(f0))[0]}
        o["guncel"] = G[bugun]["listeler"].get(ad, []) if bugun else []
        out[ad] = o
    return out


def degisim(G):
    """Dünden (en yakın önceki görüntü) bugüne değişenler."""
    tarihler = sorted(G)
    if len(tarihler) < 2: return {"onceki": None, "olaylar": []}
    b, o_ = G[tarihler[-1]], G[tarihler[-2]]; O = []
    for ad, pz, ad_tr in (("bist_deger", "bist", "BIST değerinin altında listesine girdi"), ("abd_deger", "abd", "ABD değerinin altında listesine girdi")):
        if ad in b["listeler"] and ad in o_["listeler"]:
            for k in b["listeler"][ad]:
                if k not in o_["listeler"][ad]: O.append({"tur": "liste", "kod": k, "pz": pz, "metin": ad_tr, "yon": 1})
            for k in o_["listeler"][ad]:
                if k not in b["listeler"][ad]: O.append({"tur": "liste_cikti", "kod": k, "pz": pz, "metin": ad_tr.replace("girdi", "çıktı"), "yon": 0})
    for k, y in b.get("cot", {}).items():
        y0 = o_.get("cot", {}).get(k)
        if y0 is None: continue
        if y >= 0.9 and y0 < 0.9: O.append({"tur": "cot", "kod": k, "pz": "emtia", "yon": -1, "metin": f"Spekülatörler 3 yılın en kalabalık alım konumuna geldi (COT %{y * 100:.0f})"})
        if y <= 0.1 and y0 > 0.1: O.append({"tur": "cot", "kod": k, "pz": "emtia", "yon": 1, "metin": f"Spekülatörler 3 yılın en karamsar konumuna geldi (COT %{y * 100:.0f})"})
    for k, p in b.get("kpuan", {}).items():
        p0 = o_.get("kpuan", {}).get(k)
        if p0 is not None and p - p0 <= -20: O.append({"tur": "kpuan", "kod": k, "pz": "kripto", "yon": -1, "metin": f"Temel puanı sert düştü: {p0} → {p}"})
        if p0 is not None and p - p0 >= 20: O.append({"tur": "kpuan", "kod": k, "pz": "kripto", "yon": 1, "metin": f"Temel puanı sert yükseldi: {p0} → {p}"})
    return {"onceki": tarihler[-2], "bugun": tarihler[-1], "olaylar": O}


def calistir(cikti):
    eski = _oku(os.path.join(KLON, "temel", "gecmis.json"), {}) or {}
    G = eski.get("gunler", {})
    g, T = goruntu(os.path.join(KLON, "temel"))
    bugun = dt.datetime.now(TSI).date().isoformat()
    if g["listeler"]: G[bugun] = g
    sinir = (dt.datetime.now(TSI).date() - dt.timedelta(days=SAKLA_GUN)).isoformat()
    G = {t: v for t, v in sorted(G.items()) if t >= sinir}
    zaman = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
    K = karne(G); D = degisim(G)
    os.makedirs(os.path.join(cikti, "temel"), exist_ok=True)
    for ad, veri in (("gecmis", {"zaman": zaman, "gunler": G}), ("karne", {"zaman": zaman, "gun_sayisi": len(G), "ilk": min(G) if G else None, "listeler": K}),
                     ("degisim", dict(D, zaman=zaman))):
        json.dump(veri, open(os.path.join(cikti, "temel", f"{ad}.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"Temel karne: {len(G)} gün arşiv, {len(D['olaylar'])} değişim;",
          {a: {u: round(v["fark"], 4) for u, v in o["ufuklar"].items()} for a, o in K.items()})
    return D


if __name__ == "__main__":
    calistir(sys.argv[1] if len(sys.argv) > 1 else "cikti")
