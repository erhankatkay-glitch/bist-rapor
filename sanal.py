# -*- coding: utf-8 -*-
"""Aşama 9: pozisyon büyüklüğü (risk) hesaplayıcı ve sanal işlem (paper trading) defteri.

Sanal defter gerçek portföyden tamamen ayrıdır ve yalnızca kullanıcının cihazında (tarayıcı deposu) tutulur;
GitHub'a ya da bir sunucuya yazılmaz. Defter "yalnız ekleme" mantığıyla çalışır: işlemler silinmez,
yanlış girilen bir işlem "iptal" olayıyla geçersiz sayılır ve bu iz kalır (denetlenebilir geçmiş).

Olay biçimi: {"id", "t" (UTC ISO), "tip": "ac" | "kapat" | "iptal" | "not", ...}
  ac    : kod, piyasa, yon (+1/-1), adet, fiyat, komisyon (oran), stop?, hedef?, para ("TL"/"USD"), kaynak?, aciklama?
  kapat : ref (açılış id), fiyat, adet (kısmi kapatma olabilir), komisyon, sebep
  iptal : ref, sebep
"""
import datetime as dt
import math
import uuid

SURUM = 1
LOT = {"bist": 1, "abd": 1, "kripto": 1e-6, "emtia": 0.01}


def bos_defter(baslangic=100_000.0):
    return {"surum": SURUM, "baslangic": float(baslangic), "para": "TL", "olaylar": []}


def _simdi():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _yuvarla_asagi(x, lot):
    if lot >= 1: return float(math.floor(x / lot) * lot)
    basamak = max(0, -int(math.floor(math.log10(lot))))
    return math.floor(x * 10 ** basamak) / 10 ** basamak


# ----------------------------------------------------------------------------- pozisyon büyüklüğü
def pozisyon_boyutu(portfoy, risk_orani, giris, stop, yon=1, komisyon=0.002, kayma=0.001, piyasa="bist", maks_pay=1.0, hedefler=()):
    """Risk tutarı = portföy × risk oranı; adet = risk tutarı / birim başına toplam risk.
    Birim risk = |giriş − stop| + giriş × (2 × komisyon + kayma)  (alış + satış komisyonu ve tahmini kayma dahil).
    Pozisyon portföyün maks_pay katını aşarsa adet sınırlanır ve uyarı verilir."""
    if portfoy <= 0 or giris <= 0 or stop <= 0 or risk_orani <= 0:
        raise ValueError("Portföy, risk, giriş ve stop pozitif olmalı.")
    mesafe = (giris - stop) * yon
    if mesafe <= 0:
        raise ValueError("Stop, " + ("alış fiyatının altında" if yon == 1 else "satış fiyatının üstünde") + " olmalı.")
    maliyet = giris * (2 * komisyon + kayma)
    birim = mesafe + maliyet
    risk_tutar = portfoy * risk_orani
    lot = LOT.get(piyasa, 1)
    adet = _yuvarla_asagi(risk_tutar / birim, lot)
    uyari = []
    if adet * giris > portfoy * maks_pay:
        adet = _yuvarla_asagi(portfoy * maks_pay / giris, lot)
        uyari.append(f"Stop çok yakın: risk tutarı için gereken pozisyon portföyün %{maks_pay * 100:.0f}'ünü aşıyordu; "
                     f"pozisyon portföy büyüklüğüyle sınırlandı (gerçek risk hedeften düşük).")
    if adet <= 0:
        uyari.append("Risk tutarı bir birim almaya yetmiyor; risk oranını artırın ya da stopu yaklaştırın.")
    gercek_risk = adet * birim
    out = {"adet": adet, "pozisyon": adet * giris, "pay": adet * giris / portfoy, "risk_tutar": risk_tutar, "gercek_risk": gercek_risk,
           "gercek_risk_orani": gercek_risk / portfoy, "birim_risk": birim, "stop_mesafe": mesafe / giris, "maliyet": adet * maliyet,
           "uyari": uyari, "hedef": []}
    for h in hedefler or ():
        if h is None or h <= 0: continue
        kazanc = adet * ((h - giris) * yon - maliyet)
        out["hedef"].append({"fiyat": h, "kazanc": kazanc, "r": kazanc / gercek_risk if gercek_risk else None,
                             "getiri": (h - giris) * yon / giris})
    if stop_mesafe_yuksek(mesafe / giris, piyasa):
        out["uyari"].append(f"Stop mesafesi %{mesafe / giris * 100:.1f}: bu piyasa için geniş; pozisyon küçük kalır.")
    return out


def stop_mesafe_yuksek(oran, piyasa):
    return oran > {"bist": 0.12, "abd": 0.12, "kripto": 0.20, "emtia": 0.10}.get(piyasa, 0.12)


def atr_stop(giris, atr, kat=1.5, yon=1):
    return giris - yon * kat * atr


# ----------------------------------------------------------------------------- sanal defter
def islem_ac(defter, kod, piyasa, yon, adet, fiyat, komisyon=0.002, stop=None, hedef=None, para="TL", kaynak="elle", aciklama=""):
    if adet <= 0 or fiyat <= 0: raise ValueError("Adet ve fiyat pozitif olmalı.")
    if yon == -1 and piyasa != "kripto":
        raise ValueError("Açığa satış (SAT) yalnızca kripto vadeli işlemler için desteklenir.")
    o = {"id": uuid.uuid4().hex[:10], "t": _simdi(), "tip": "ac", "kod": kod, "piyasa": piyasa, "yon": int(yon), "adet": float(adet),
         "fiyat": float(fiyat), "komisyon": float(komisyon), "stop": stop, "hedef": hedef, "para": para, "kaynak": kaynak, "aciklama": aciklama}
    defter["olaylar"].append(o)
    return o


def islem_kapat(defter, ref, fiyat, adet=None, komisyon=None, sebep="elle"):
    p = {x["id"]: x for x in pozisyonlar(defter)}.get(ref)
    if not p: raise ValueError("Açık pozisyon bulunamadı.")
    adet = float(adet or p["kalan"])
    if adet <= 0 or adet > p["kalan"] + 1e-12: raise ValueError("Kapatılacak adet açık adetten fazla olamaz.")
    o = {"id": uuid.uuid4().hex[:10], "t": _simdi(), "tip": "kapat", "ref": ref, "fiyat": float(fiyat), "adet": adet,
         "komisyon": float(p["komisyon"] if komisyon is None else komisyon), "sebep": sebep}
    defter["olaylar"].append(o)
    return o


def iptal(defter, ref, sebep=""):
    o = {"id": uuid.uuid4().hex[:10], "t": _simdi(), "tip": "iptal", "ref": ref, "sebep": sebep or "kullanıcı iptali"}
    defter["olaylar"].append(o)
    return o


def _islemler(defter):
    """Olaylardan işlem kayıtları (iptaller hariç): açılış + kapanış parçaları."""
    iptal_ = {o["ref"] for o in defter["olaylar"] if o["tip"] == "iptal"}
    acilis = {o["id"]: dict(o, kapanis=[]) for o in defter["olaylar"] if o["tip"] == "ac" and o["id"] not in iptal_}
    for o in defter["olaylar"]:
        if o["tip"] == "kapat" and o["ref"] in acilis and o["id"] not in iptal_:
            acilis[o["ref"]]["kapanis"].append(o)
    for a in acilis.values():
        a["kalan"] = a["adet"] - sum(k["adet"] for k in a["kapanis"])
        a["gerceklesen"] = sum(k["adet"] * ((k["fiyat"] - a["fiyat"]) * a["yon"]) - k["adet"] * (k["fiyat"] * k["komisyon"] + a["fiyat"] * a["komisyon"])
                               for k in a["kapanis"])
        if a.get("stop"):
            r1 = abs(a["fiyat"] - a["stop"]) * a["adet"]
            a["R"] = a["gerceklesen"] / r1 if r1 and not a["kalan"] > 1e-12 else None
        else:
            a["R"] = None
    return list(acilis.values())


def pozisyonlar(defter):
    return [a for a in _islemler(defter) if a["kalan"] > 1e-12]


def kapananlar(defter):
    return [a for a in _islemler(defter) if a["kalan"] <= 1e-12]


def degerle(defter, fiyat_fn, kur=1.0):
    """Açık pozisyonları güncel fiyatla değerler. fiyat_fn(kod) → son fiyat; kur: USD/TRY.
    → {"pozisyonlar": [...], "gerceklesen_tl", "acik_kz_tl", "ozkaynak_tl", "kazanma", "ort_R", "islem_sayisi"}"""
    tl = lambda x, para: x * (kur if para == "USD" else 1.0)
    acik = []
    for p in pozisyonlar(defter):
        try: f = float(fiyat_fn(p["kod"]))
        except Exception: f = None
        kz = None if f is None else p["kalan"] * ((f - p["fiyat"]) * p["yon"]) - p["kalan"] * p["fiyat"] * p["komisyon"]
        uyari = ""
        if f is not None and p.get("stop") and (f - p["stop"]) * p["yon"] <= 0: uyari = "stop seviyesinde / altında"
        elif f is not None and p.get("hedef") and (f - p["hedef"]) * p["yon"] >= 0: uyari = "hedefe ulaştı"
        acik.append(dict(p, son=f, kz=kz, kz_oran=None if f is None else (f - p["fiyat"]) * p["yon"] / p["fiyat"], uyari=uyari,
                         kz_tl=None if kz is None else tl(kz, p["para"]), deger_tl=None if f is None else tl(p["kalan"] * f, p["para"])))
    kap = kapananlar(defter)
    gerc = sum(tl(a["gerceklesen"], a["para"]) for a in _islemler(defter))
    acik_kz = sum(x["kz_tl"] or 0 for x in acik)
    rler = [a["R"] for a in kap if a.get("R") is not None]
    return {"pozisyonlar": acik, "kapananlar": kap, "gerceklesen_tl": gerc, "acik_kz_tl": acik_kz,
            "ozkaynak_tl": defter["baslangic"] + gerc + acik_kz, "getiri": (gerc + acik_kz) / defter["baslangic"],
            "kazanma": (sum(1 for a in kap if a["gerceklesen"] > 0) / len(kap)) if kap else None,
            "ort_R": (sum(rler) / len(rler)) if rler else None, "islem_sayisi": len(kap)}


def dogrula(defter):
    """Yüklenen/yedekten gelen defterin biçimini denetler; bozuksa ValueError."""
    if not isinstance(defter, dict) or "olaylar" not in defter or not isinstance(defter["olaylar"], list):
        raise ValueError("Geçerli bir sanal defter değil.")
    for o in defter["olaylar"]:
        if o.get("tip") not in ("ac", "kapat", "iptal", "not") or "id" not in o:
            raise ValueError("Defterde tanınmayan kayıt var.")
    defter.setdefault("baslangic", 100_000.0); defter.setdefault("para", "TL"); defter.setdefault("surum", SURUM)
    return defter
