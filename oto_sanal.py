# -*- coding: utf-8 -*-
"""Otomatik sanal hesaplar: sinyallere kendiliğinden giren paper-trading hesapları (gerçek para yok, emir gönderilmez).

İki bağımsız kaynak, her biri kendi hesaplarıyla:
- "firsat": normal Fırsatlar sisteminin işlemleri (bulten/firsat/<pz>/acik.json + gecmis.json). İşlem yaşam döngüsü (giriş, stop,
  kademeli hedefler, R) fırsat sisteminden birebir izlenir; hesap yalnız para yönetimini ekler.
- "fibo": FiboAyna sinyallerinin kendi defteri (bulten/fibo/kayit_<pz>.json).

Hesap kuralları (kullanıcının isteği):
- BIST: 100.000 TL, işlem başına 20.000 TL, aynı anda en çok 5 işlem (puanı en yüksek sinyaller).
- ABD ve emtia: 1.000 $, işlem başına 200 $, en çok 5.
- Kripto spot: 1.000 USDT, işlem başına 200 USDT, en çok 5; spotta açığa satış olmadığı için yalnız AL.
- Kripto vadeli (izole marjin): 1.000 USDT, işlem başına 200 USDT marjin, AL ve SAT. Kaldıraç ekip kararıyla işlem başına seçilir:
  5x / 10x / 20x içinden, stop gelirse marjinin en fazla yarısı gidecek (stop% × kaldıraç ≤ 0,5) ve tasfiye fiyatı stopun en az
  1,5 katı uzakta kalacak EN YÜKSEK kaldıraç. Hiçbiri uymuyorsa (stop çok uzak) işlem vadeliye girilmez. Sabit 20x'te tasfiye stoptan
  önce gelir: geçmiş testte işlemlerin yarıya yakını tasfiye oluyordu.
Komisyon: BIST %0,2 · ABD / emtia / kripto spot %0,1 · vadeli %0,05 (işlem tutarı üzerinden, giriş ve çıkış). Fonlama ücreti dahil değil.
Çıktı: bulten/oto/<kaynak>_<hesap>.json. Kullanım: python oto_sanal.py <cikti>"""
import datetime as dt
import json
import os
import sys

import requests

HAM = "https://raw.githubusercontent.com/erhankatkay-glitch/bist-rapor/bulten/"
HESAP = {
    "bist": {"piyasa": "bist", "para": "TL", "baslangic": 100_000.0, "tutar": 20_000.0, "maks": 5, "kom": 0.002, "vadeli": False},
    "abd": {"piyasa": "abd", "para": "USD", "baslangic": 1_000.0, "tutar": 200.0, "maks": 5, "kom": 0.001, "vadeli": False},
    "emtia": {"piyasa": "emtia", "para": "USD", "baslangic": 1_000.0, "tutar": 200.0, "maks": 5, "kom": 0.001, "vadeli": False},
    "kripto_spot": {"piyasa": "kripto", "para": "USDT", "baslangic": 1_000.0, "tutar": 200.0, "maks": 5, "kom": 0.001, "vadeli": False},
    "kripto_vadeli": {"piyasa": "kripto", "para": "USDT", "baslangic": 1_000.0, "tutar": 200.0, "maks": 5, "kom": 0.0005, "vadeli": True},
}
KALDIRAC = (20, 10, 5)
MMR = 0.005          # bakım marjini (tasfiye hesabı)
STOP_MARJIN = 0.5    # stopta marjinin en fazla yarısı
TASFIYE_PAY = 1.5    # tasfiye mesafesi ≥ 1,5 × stop mesafesi


def kaldirac_sec(stop_yuzde):
    for L in KALDIRAC:
        if stop_yuzde * L <= STOP_MARJIN and (1.0 / L - MMR) >= TASFIYE_PAY * stop_yuzde:
            return L
    return None


def _al(yol):
    try:
        r = requests.get(HAM + yol, timeout=30)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def kaynak_islemler(kaynak, pz):
    """Kaynağın işlemleri tek biçimde: {id, kod, yon, giris, risk_yuzde, puan, acilis, acik, R_simdi, R_son, sebep}"""
    out = {}
    if kaynak == "firsat":
        acik = _al(f"firsat/{pz}/acik.json") or []; gec = _al(f"firsat/{pz}/gecmis.json") or []
        for x in list(gec) + list(acik):
            try:
                g, st = float(x["giris"]), float(x.get("stop_ilk") or x["stop"])
                risk = abs(g - st)
                if not (g > 0 and risk > 0): continue
                yon = int(x.get("yon", 1)); kalan = float(x.get("kalan", 1) or 0); Rr = float(x.get("R") or 0)
                son = x.get("son_fiyat")
                Rs = Rr + (kalan * (float(son) - g) * yon / risk if son is not None and kalan > 0 else 0.0)
                kapali = x.get("durum") != "açık"
                out[x["id"]] = {"id": x["id"], "kod": x["kod"], "yon": yon, "giris": g, "risk_yuzde": risk / g, "puan": x.get("puan"),
                                "acilis": x.get("acilis_utc") or x.get("olusma"), "acik": not kapali, "R_simdi": Rs,
                                "R_son": Rr if kapali else None, "sebep": x.get("sebep"), "ad": x.get("kurulum")}
            except Exception:
                continue
    else:
        K = _al(f"fibo/kayit_{pz}.json") or {}
        for x in K.get("acik", []) + K.get("kapali", []):
            if x.get("giris") is None: continue          # giriş ertesi açılışta dolacak
            g, st = float(x["giris"]), float(x["stop"]); risk = g - st
            if not risk > 0: continue
            kapali = "sonuc_tarih" in x
            out[x["id"]] = {"id": x["id"], "kod": x["kod"], "yon": 1, "giris": g, "risk_yuzde": risk / g, "puan": x.get("puan"),
                            "acilis": x.get("tarih"), "acik": not kapali, "R_simdi": x.get("R") if kapali else x.get("anlik_R"),
                            "R_son": x.get("R") if kapali else None, "sebep": x.get("neden"), "ad": x.get("ad")}
    return out


def _pnl(p, R, H):
    """İşlemin kâr/zararı (para) ve sonuç: R × risk% = fiyat getirisi; vadelide × kaldıraç, kayıp marjinle sınırlı."""
    r = (R or 0.0) * p["risk_yuzde"]
    L = p.get("kaldirac") or 1
    brut = p["tutar"] * max(-1.0, r * L)
    kom = p["tutar"] * L * H["kom"] * 2
    return brut - kom


def guncelle(onceki, kaynak, ad, H, I, simdi):
    S = onceki if isinstance(onceki, dict) and onceki.get("hesap") == ad else {
        "kaynak": kaynak, "hesap": ad, "para": H["para"], "baslangic": H["baslangic"], "nakit": H["baslangic"],
        "acik": [], "kapali": [], "egri": [], "alinan": [], "baslama": simdi[:10]}
    # 1) açık pozisyonları güncelle / kapat
    kalan = []
    for p in S["acik"]:
        x = I.get(p["id"])
        if x is None: kalan.append(p); continue          # kaynak geçici olarak okunamadı
        if not x["acik"]:
            pnl = _pnl(p, x["R_son"], H)
            S["nakit"] += p["tutar"] + pnl
            S["kapali"].append({**p, "R": x["R_son"], "kar": round(pnl, 2), "getiri": round(pnl / p["tutar"], 4), "sebep": x.get("sebep"), "kapanis": simdi})
        else:
            p["R_simdi"] = x["R_simdi"]; p["kar_simdi"] = round(_pnl(p, x["R_simdi"], H), 2); kalan.append(p)
    S["acik"] = kalan
    # 2) yeni girişler: kaynakta açık, hesaba daha önce alınmamış, en yüksek puanlı; boş yer ve nakit kadar
    alinan = set(S["alinan"])
    aday = [x for x in I.values() if x["acik"] and x["id"] not in alinan and x["acilis"] and str(x["acilis"])[:10] >= S["baslama"]]
    if not H["vadeli"] and H["piyasa"] == "kripto": aday = [x for x in aday if x["yon"] == 1]     # spotta açığa satış yok
    aday.sort(key=lambda x: -(x["puan"] or 0))
    for x in aday:
        if len(S["acik"]) >= H["maks"] or S["nakit"] < H["tutar"]: break
        if any(p["kod"] == x["kod"] for p in S["acik"]): continue
        L = None
        if H["vadeli"]:
            L = kaldirac_sec(x["risk_yuzde"])
            if L is None:
                alinan.add(x["id"]); S.setdefault("atlanan", []).append({"id": x["id"], "kod": x["kod"], "neden": f"stop çok uzak (%{x['risk_yuzde'] * 100:.1f}): 5x bile güvenli değil"}); continue
        p = {"id": x["id"], "kod": x["kod"], "ad": x.get("ad"), "yon": x["yon"], "giris": x["giris"], "risk_yuzde": round(x["risk_yuzde"], 5),
             "puan": x["puan"], "tutar": H["tutar"], "kaldirac": L, "acilis": simdi, "R_simdi": x["R_simdi"]}
        p["kar_simdi"] = round(_pnl(p, x["R_simdi"], H), 2)
        S["nakit"] -= H["tutar"]; S["acik"].append(p); alinan.add(x["id"])
    S["alinan"] = sorted(alinan)[-3000:]
    S["atlanan"] = (S.get("atlanan") or [])[-100:]
    S["kapali"] = S["kapali"][-500:]
    # 3) özkaynak ve özet
    ozk = S["nakit"] + sum(p["tutar"] + (p.get("kar_simdi") or 0) for p in S["acik"])
    gun = simdi[:10]
    if S["egri"] and S["egri"][-1][0] == gun: S["egri"][-1] = [gun, round(ozk, 2)]
    else: S["egri"].append([gun, round(ozk, 2)])
    S["egri"] = S["egri"][-730:]
    kp = S["kapali"]
    tepe, dd = H["baslangic"], 0.0
    for _, v in S["egri"]:
        tepe = max(tepe, v); dd = min(dd, v / tepe - 1)
    S["ozet"] = {"ozkaynak": round(ozk, 2), "getiri": round(ozk / H["baslangic"] - 1, 4), "acik": len(S["acik"]), "kapanan": len(kp),
                 "kazanma": round(sum(1 for x in kp if x["kar"] > 0) / len(kp), 3) if kp else None,
                 "toplam_kar": round(sum(x["kar"] for x in kp), 2), "en_buyuk_dusus": round(dd, 4)}
    S["kurallar"] = {k: H[k] for k in ("baslangic", "tutar", "maks", "kom", "vadeli")}
    if H["vadeli"]: S["kurallar"]["kaldirac"] = "5x/10x/20x içinden: stopta marjin kaybı ≤ %50 ve tasfiye ≥ 1,5 × stop mesafesi olan en yüksek"
    S["zaman"] = simdi
    return S


def calistir(cikti):
    simdi = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
    os.makedirs(os.path.join(cikti, "oto"), exist_ok=True)
    for kaynak in ("firsat", "fibo"):
        onbellek = {}
        for ad, H in HESAP.items():
            pz = H["piyasa"]
            if pz not in onbellek: onbellek[pz] = kaynak_islemler(kaynak, pz)
            onceki = _al(f"oto/{kaynak}_{ad}.json") or {}
            S = guncelle(onceki, kaynak, ad, H, onbellek[pz], simdi)
            json.dump(S, open(os.path.join(cikti, "oto", f"{kaynak}_{ad}.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
            print(kaynak, ad, S["ozet"])


if __name__ == "__main__":
    calistir(sys.argv[1] if len(sys.argv) > 1 else "cikti")
