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
def islem_ac(defter, kod, piyasa, yon, adet, fiyat, komisyon=0.002, stop=None, hedef=None, para="TL", kaynak="elle", aciklama="", kontrol=None):
    if adet <= 0 or fiyat <= 0: raise ValueError("Adet ve fiyat pozitif olmalı.")
    if yon == -1 and piyasa != "kripto":
        raise ValueError("Açığa satış (SAT) yalnızca kripto vadeli işlemler için desteklenir.")
    o = {"id": uuid.uuid4().hex[:10], "t": _simdi(), "tip": "ac", "kod": kod, "piyasa": piyasa, "yon": int(yon), "adet": float(adet),
         "fiyat": float(fiyat), "komisyon": float(komisyon), "stop": stop, "hedef": hedef, "para": para, "kaynak": kaynak, "aciklama": aciklama}
    if kontrol: o["kontrol"] = {"puan": kontrol.get("puan"), "uyari": [m["ad"] for m in kontrol.get("maddeler", []) if m["durum"] != "ok"]}
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


# ============================================================================= Aşama 10c-3: disiplin araçları
AYAR_VARSAYILAN = {"sigorta_dd": 0.10, "sigorta_ardisik": 3, "maks_risk": 0.02, "maks_toplam_risk": 0.06, "min_kr": 2.0}
DUYGULAR = ["Sakin / planlı", "Korku", "Açgözlülük", "Sabırsızlık", "İntikam (kaybı geri alma)", "Sıkılma / FOMO"]
KAPANIS_SEBEP = ["Hedef geldi", "Stop çalıştı", "Plan dışı erken çıkış", "Plan dışı geç çıkış", "Senaryo bozuldu (plana uygun)", "Diğer"]


def ayarlar(defter):
    return {**AYAR_VARSAYILAN, **(defter.get("ayar") or {})}


def _ozkaynak_egrisi(defter):
    """Kapanış sırasına göre gerçekleşen özkaynak (başlangıç + birikimli K/Z). Para birimi karışıksa yaklaşık (TL kabul)."""
    kap = sorted(kapananlar(defter), key=lambda a: a["kapanis"][-1]["t"])
    e = [defter["baslangic"]]
    for a in kap: e.append(e[-1] + a["gerceklesen"])
    return e, kap


def dusus_sigortasi(defter, ozkaynak_simdi=None):
    """Düşüş sigortası: özkaynak tepeden `sigorta_dd` kadar düştüyse ya da son `sigorta_ardisik` işlem üst üste zararla
    kapandıysa yeni işlemden önce ara verme uyarısı. → {"aktif", "dd", "tepe", "ardisik", "neden"}"""
    A = ayarlar(defter); e, kap = _ozkaynak_egrisi(defter)
    simdi = float(ozkaynak_simdi if ozkaynak_simdi is not None else e[-1])
    tepe = max(e + [simdi]); dd = 1 - simdi / tepe if tepe > 0 else 0.0
    ard = 0
    for a in reversed(kap):
        if a["gerceklesen"] < 0: ard += 1
        else: break
    neden = []
    if dd >= A["sigorta_dd"]: neden.append(f"özkaynak tepeden %{dd * 100:.1f} geride (sınır %{A['sigorta_dd'] * 100:.0f})")
    if ard >= A["sigorta_ardisik"]: neden.append(f"son {ard} işlem üst üste zararla kapandı")
    return {"aktif": bool(neden), "dd": dd, "tepe": tepe, "ardisik": ard, "neden": neden}


def kontrol_listesi(defter, deger, kod, piyasa, yon, fiyat, stop, hedef, adet, kur=1.0, para="TL", rejim=None, plan_giris=None, neden=""):
    """İşlem öncesi kontrol listesi. deger: degerle() çıktısı; rejim: {"maruziyet", "durum_ad"} (bist/abd).
    → {"maddeler": [{"ad", "durum": "ok"|"uyari"|"hata", "aciklama"}], "puan" (0–100), "engel" (hata var mı)}"""
    A = ayarlar(defter); M = []
    tl = kur if para == "USD" else 1.0
    oz = max(1e-9, float(deger["ozkaynak_tl"]))
    ek = lambda ad, d, ac: M.append({"ad": ad, "durum": d, "aciklama": ac})
    if not stop:
        ek("Stop belirlendi", "hata", "Stopsuz işlem açılmaz: nerede yanıldığını önceden bilmelisin.")
        risk = None
    elif (fiyat - stop) * yon <= 0:
        ek("Stop belirlendi", "hata", "Stop yanlış tarafta.")
        risk = None
    else:
        risk = abs(fiyat - stop) * adet * tl
        ek("Stop belirlendi", "ok", f"Stop {stop:g} · girişten %{abs(fiyat - stop) / fiyat * 100:.1f} uzakta.")
        ro = risk / oz
        ek("İşlem riski", "ok" if ro <= A["maks_risk"] / 2 else "uyari" if ro <= A["maks_risk"] else "hata",
           f"Stop gelirse kayıp ≈ {risk:,.0f} TL = özkaynağın %{ro * 100:.2f}'i (sınır %{A['maks_risk'] * 100:.0f}).".replace(",", "."))
    if hedef and stop and (hedef - fiyat) * yon > 0 and (fiyat - stop) * yon > 0:
        kr = (hedef - fiyat) * yon / ((fiyat - stop) * yon)
        ek("Kazanç / risk oranı", "ok" if kr >= A["min_kr"] else "uyari", f"1:{kr:.1f} (en az 1:{A['min_kr']:g} önerilir).".replace(".", ","))
    else:
        ek("Kazanç / risk oranı", "uyari", "Hedef girilmedi: nerede kâr alacağını önceden belirle.")
    acik_risk = sum(abs(p["fiyat"] - p["stop"]) * p["kalan"] * (kur if p["para"] == "USD" else 1.0)
                    for p in deger["pozisyonlar"] if p.get("stop"))
    toplam = (acik_risk + (risk or 0)) / oz
    ek("Toplam açık risk", "ok" if toplam <= A["maks_toplam_risk"] else "uyari",
       f"Tüm açık stoplar gelirse kayıp özkaynağın %{toplam * 100:.1f}'i (sınır %{A['maks_toplam_risk'] * 100:.0f}).")
    if any(p["kod"] == kod for p in deger["pozisyonlar"]):
        ek("Aynı varlıkta açık pozisyon", "uyari", f"{kod} için zaten açık pozisyon var; riski ikiye katlamış olabilirsin.")
    if rejim and piyasa in ("bist", "abd"):
        pay = (sum(p["deger_tl"] or 0 for p in deger["pozisyonlar"] if p["piyasa"] == piyasa) + fiyat * adet * tl) / oz
        ek(f"Piyasa rejimi ({rejim.get('durum_ad', '')})", "ok" if pay <= rejim["maruziyet"] / 100 + 1e-9 else "uyari",
           f"Bu işlemle {piyasa.upper()} hisse payı %{pay * 100:.0f}; rejime göre önerilen en çok %{rejim['maruziyet']}.")
    if plan_giris:
        kac = (fiyat - plan_giris) * yon / plan_giris
        ek("Kovalamıyorum", "ok" if kac <= 0.03 else "uyari", f"Fiyat plan girişinden %{kac * 100:+.1f} uzakta (%3'ten fazlası kovalama sayılır).")
    s = dusus_sigortasi(defter, deger["ozkaynak_tl"])
    ek("Düşüş sigortası", "hata" if s["aktif"] else "ok", ("Ara ver: " + "; ".join(s["neden"])) if s["aktif"] else "Sigorta devrede değil.")
    ek("Nedeni yazdım", "ok" if len((neden or "").strip()) >= 8 else "hata", "Bu işlemi neden açtığını bir cümleyle yaz (günlük için).")
    p = {"ok": 1.0, "uyari": 0.5, "hata": 0.0}
    puan = round(100 * sum(p[x["durum"]] for x in M) / len(M))
    return {"maddeler": M, "puan": puan, "engel": any(x["durum"] == "hata" for x in M)}


def gunluk_ekle(defter, ref, plana_uydum=None, duygu=None, ders="", sebep=None):
    """Kapanan işlem değerlendirmesi (işlem günlüğü) → "not" olayı (yalnız ekleme)."""
    o = {"id": uuid.uuid4().hex[:10], "t": _simdi(), "tip": "not", "ref": ref, "plana_uydum": plana_uydum, "duygu": duygu,
         "ders": (ders or "").strip(), "sebep": sebep}
    defter["olaylar"].append(o)
    return o


def gunlukler(defter):
    """ref → son değerlendirme."""
    out = {}
    for o in defter["olaylar"]:
        if o["tip"] == "not" and o.get("ref"): out[o["ref"]] = o
    return out


def haftalik_ozet(defter, kur=1.0, bugun=None, gun=7):
    """Son `gun` günde kapanan işlemlerin özeti + kural tabanlı öneriler."""
    bugun = bugun or dt.datetime.now(dt.timezone.utc)
    sinir = (bugun - dt.timedelta(days=gun)).isoformat(timespec="seconds")
    G = gunlukler(defter); acilis = {o["id"]: o for o in defter["olaylar"] if o["tip"] == "ac"}
    kap = [a for a in kapananlar(defter) if a["kapanis"][-1]["t"] >= sinir]
    acilan = [o for o in defter["olaylar"] if o["tip"] == "ac" and o["t"] >= sinir]
    tl = lambda a: a["gerceklesen"] * (kur if a["para"] == "USD" else 1.0)
    rler = [a["R"] for a in kap if a.get("R") is not None]
    deg = [G[a["id"]] for a in kap if a["id"] in G]
    uyum = [g["plana_uydum"] for g in deg if g.get("plana_uydum") is not None]
    duygu = {}
    for g in deg:
        if g.get("duygu"): duygu[g["duygu"]] = duygu.get(g["duygu"], 0) + 1
    kpuan = [acilis[a["id"]].get("kontrol", {}).get("puan") for a in kap if acilis.get(a["id"], {}).get("kontrol")]
    o = {"gun": gun, "kapanan": len(kap), "acilan": len(acilan), "kz_tl": sum(tl(a) for a in kap),
         "kazanma": (sum(1 for a in kap if a["gerceklesen"] > 0) / len(kap)) if kap else None,
         "ort_R": (sum(rler) / len(rler)) if rler else None, "plana_uyum": (sum(uyum) / len(uyum)) if uyum else None,
         "degerlendirilen": len(deg), "duygu": duygu, "kontrol_puani": (sum(kpuan) / len(kpuan)) if kpuan else None,
         "en_iyi": max(kap, key=tl)["kod"] if kap else None, "en_kotu": min(kap, key=tl)["kod"] if kap else None}
    oneri = []
    if kap and o["degerlendirilen"] < len(kap): oneri.append(f"{len(kap) - o['degerlendirilen']} kapanan işlem değerlendirilmedi; günlüğü doldur, ders çıkar.")
    if o["plana_uyum"] is not None and o["plana_uyum"] < 0.7: oneri.append("İşlemlerin %30'undan fazlasında plana uyulmadı: girişten önce çıkış kuralını yaz ve ona uy.")
    kayip_r = [r for r in rler if r < 0]
    if kayip_r and min(kayip_r) < -1.3: oneri.append("Bir zarar 1R'yi belirgin aştı: stopu kaydırmamak ve boşluk riskini küçük pozisyonla yönetmek gerekir.")
    if len(acilan) > 10: oneri.append(f"Bu hafta {len(acilan)} işlem açıldı: aşırı işlem riski; yalnız en yüksek puanlı kurulumları seç.")
    olumsuz = sum(v for k, v in duygu.items() if not k.startswith("Sakin"))
    if olumsuz and olumsuz >= max(1, len(deg) // 2): oneri.append("İşlemlerin yarısında duygusal karar (korku/açgözlülük/intikam) işaretlendi: işlem boyutunu küçült.")
    if o["kontrol_puani"] is not None and o["kontrol_puani"] < 70: oneri.append("Kontrol listesi puanı düşük: uyarılara rağmen açılan işlemler var.")
    if kap and not oneri: oneri.append("Kurallara uyum iyi; aynı disiplinle devam.")
    o["oneri"] = oneri
    return o
