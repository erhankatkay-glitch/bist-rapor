# -*- coding: utf-8 -*-
"""Haftalık ve aylık durum raporu: 10 ana varlık için dönem performansı, teknik görünüm, hedef ve destek seviyeleri.

Varlıklar: BIST 100, BIST 30, Dolar/TL, S&P 500, Nasdaq, VIX, ons altın, ons gümüş, Brent petrol, Bitcoin.
Çıktılar ({CIKTI}/donem/): haftalik.png / haftalik.pdf / haftalik.json (aylık için aylik.*).
Telegram: KATKAY kartı + PDF.

Zamanlama (durum_raporu.yml, her gün 09:41 TSİ):
  cumartesi → haftalık (hafta kapanışları tamam) · ayın 1'i → aylık (önceki ay tamam).
  Elle:  python durum_raporu.py haftalik|aylik [gonder]
"""
import datetime as dt
import json
import os
import sys

import pandas as pd

import bist_teknik as T

TSI = dt.timezone(dt.timedelta(hours=3))
CIKTI = os.environ.get("DURUM_CIKTI", "cikti")

GRUPLAR = [
    ("Türkiye", [("XU100", "BIST 100"), ("XU030", "BIST 30"), ("USDTRY", "Dolar/TL")]),
    ("ABD", [("SP500", "S&P 500"), ("NASDAQ", "Nasdaq"), ("VIX", "VIX korku endeksi")]),
    ("Emtia ve kripto", [("ALTIN", "Ons altın"), ("GUMUS", "Ons gümüş"), ("BRENT", "Brent petrol"), ("BTC", "Bitcoin")]),
]
DONEM = {"haftalik": {"tf": "H", "ad": "Haftalık", "ust": "A", "kapanis": "haftalık kapanış"},
         "aylik": {"tf": "A", "ad": "Aylık", "ust": "A", "kapanis": "aylık kapanış"}}


from bicim import sayi as fy, yuzde as yz


def veri(kod, tur_donem, bugun):
    """Tamamlanmış dönemlere kadar günlük veri (aylık raporda yeni ayın ilk günleri çıkarılır)."""
    h, tur = T.gunluk_veri(kod)
    h = h.copy()
    if tur_donem == "aylik":
        h = h[h.index < pd.Timestamp(bugun.year, bugun.month, 1)]
    elif tur_donem == "haftalik":
        # cumartesi/pazar çalışır; kripto hafta sonu mumlarını cuma kapanışına kadar kes ki tüm varlıklar aynı haftayı göstersin
        cuma = pd.Timestamp(bugun) - pd.Timedelta(days=(bugun.weekday() - 4) % 7)
        h = h[h.index <= cuma + pd.Timedelta(hours=23, minutes=59)]
    return h, tur


def seviyeler(a, fiyat):
    """Yukarı hedefler (direnç + formasyon hedefi) ve aşağı destekler, fiyata uzaklığa göre sıralı."""
    yukari = sorted({round(float(x[0]), 6) for x in a["sr"]["direnc"] if float(x[0]) > fiyat})[:2]
    asagi = sorted({round(float(x[0]), 6) for x in a["sr"]["destek"] if float(x[0]) < fiyat}, reverse=True)[:2]
    for f in a.get("form") or []:
        if f.get("hedef") and f.get("yon") == 1 and f["hedef"] > fiyat and len(yukari) < 3: yukari.append(float(f["hedef"]))
        if f.get("hedef") and f.get("yon") == -1 and f["hedef"] < fiyat and len(asagi) < 3: asagi.append(float(f["hedef"]))
    return sorted(set(yukari))[:3], sorted(set(asagi), reverse=True)[:3]


def senaryo(ad, a, ust, yukari, asagi, donem, kod=""):
    et = a["etiket"]; kap = DONEM[donem]["kapanis"]
    yon = 1 if a["puan"] >= 58 else -1 if a["puan"] <= 42 else 0
    p = []
    vix = kod == "VIX"
    if yon > 0:
        p.append(f"Yükseliş eğiliminde ({et.lower()}); piyasalarda tedirginlik artıyor." if vix else f"Görünüm olumlu ({et.lower()}).")
        if yukari: p.append(f"{fy(yukari[0])} üzerinde {kap} yükselişi {fy(yukari[1]) if len(yukari) > 1 else 'daha yukarı'} seviyesine taşır.")
        else: p.append("Fiyat zirve bölgesinde; üzerinde bilinen bir direnç yok.")
        if asagi: p.append(f"{fy(asagi[0])} altına inmesi görünümü zayıflatır.")
    elif yon < 0:
        p.append(f"Düşüş eğiliminde ({et.lower()}); piyasalar sakinleşiyor." if vix else f"Görünüm zayıf ({et.lower()}).")
        if asagi: p.append(f"{fy(asagi[0])} altında {kap} düşüşü {fy(asagi[1]) if len(asagi) > 1 else 'daha alt seviyelere'} doğru sürdürebilir.")
        if yukari: p.append(f"Toparlanma için {fy(yukari[0])} üzerinde kapanış gerekir.")
    else:
        p.append("Yön kararsız (nötr).")
        if yukari and asagi: p.append(f"{fy(asagi[0])} – {fy(yukari[0])} bandının kırıldığı yön belirleyici olur.")
    if ust and ust.get("etiket") and donem == "haftalik":
        p.append(f"Aylık görünüm {ust['etiket'].lower()}.")
    return " ".join(p)


def analiz_et(donem, bugun=None):
    bugun = bugun or dt.datetime.now(TSI).date()
    tf = DONEM[donem]["tf"]; sonuc = []
    for grup, liste in GRUPLAR:
        for kod, ad in liste:
            try:
                h, tur = veri(kod, donem, bugun)
                s = T.analiz_h(kod, ad, h, "kripto" if tur == "kripto" else tur, "", tfler=("G", "H", "A"))
                a = s["tf"].get(tf)
                if not a: raise ValueError("dönem analizi yok")
                fiyat = a["fiyat"]; yukari, asagi = seviyeler(a, fiyat)
                ust = s["tf"].get("A") if tf == "H" else None
                rsi = float(a["G"]["RSI"].iloc[-1])
                sonuc.append({"grup": grup, "kod": kod, "ad": ad, "fiyat": fiyat, "degisim": a["degisim"], "puan": round(a["puan"], 1),
                              "etiket": a["etiket"], "ust_etiket": ust["etiket"] if ust else None, "rsi": round(rsi, 1),
                              "yapi": a["pa"].get("yapi"), "yukari": yukari, "asagi": asagi,
                              "senaryo": senaryo(ad, a, ust, yukari, asagi, donem, kod), "tarih": str(a["tarih"].date()), "_s": s})
            except Exception as ex:
                print(f"{kod}: {ex}", file=sys.stderr)
    return sonuc


def kart(donem, sonuc, dosya, bugun):
    import kart as K
    C = K.C; ad = DONEM[donem]["ad"]
    renk = lambda e: C["yesil"] if "AL" in e else C["kirmizi"] if "SAT" in e else C["soluk"]
    bolumler = []
    for grup, _ in GRUPLAR:
        sat = []
        for r in [x for x in sonuc if x["grup"] == grup]:
            hd = " / ".join(fy(x) for x in r["yukari"][:2]) or "zirvede"; ds = " / ".join(fy(x) for x in r["asagi"][:2]) or "–"
            et = r["etiket"] if r["kod"] != "VIX" else ("YÜKSELİŞTE" if "AL" in r["etiket"] else "DÜŞÜŞTE" if "SAT" in r["etiket"] else "NÖTR")
            sat.append({"sol": f"{r['ad']} · {et}", "nokta": renk(r["etiket"]) if r["kod"] != "VIX" else C["altin"],
                        "sag": f"{fy(r['fiyat'])}  {yz(r['degisim'])}", "sag_renk": C["yesil"] if (r["degisim"] or 0) > 0 else C["kirmizi"],
                        "alt": f"Hedef {hd} · Destek {ds}. {r['senaryo']}"})
        if sat: bolumler.append({"baslik": grup, "renk": C["altin"], "satirlar": sat})
    al = sum(1 for r in sonuc if "AL" in r["etiket"] and r["kod"] != "VIX"); sat_ = sum(1 for r in sonuc if "SAT" in r["etiket"] and r["kod"] != "VIX")
    baslik = f"{al} varlık olumlu, {sat_} zayıf"
    tarih = f"{bugun:%d.%m.%Y}"
    K.bildirim_karti(f"{ad.upper()} DURUM RAPORU · {tarih}", baslik,
                     f"{ad} kapanışlar · değişim, teknik görünüm, hedef ve destek seviyeleri", bolumler, dosya,
                     not_="Hedefler en yakın teknik direnç ve formasyon hedefleridir; destekler en yakın talep bölgeleridir. "
                          "Gösterge bazlı analizdir, yatırım tavsiyesi değildir.")
    return dosya


def pdf(donem, sonuc, dosya):
    import bist_teknik_rapor as TR
    satir = []
    for r in sonuc:
        x = T.ozet_satir(r["_s"]); x["Fiyat"] = r["fiyat"]; x["Değişim"] = r["degisim"]; satir.append(x)
    TR.bulten_pdf(f"{DONEM[donem]['ad']} Durum Raporu", satir, [r["_s"] for r in sonuc], dosya, endeks=None, sym="")
    return dosya


def calistir(donem, gonder=True):
    bugun = dt.datetime.now(TSI).date()
    sonuc = analiz_et(donem, bugun)
    if len(sonuc) < 6:
        print("Yeterli varlık analiz edilemedi:", len(sonuc)); return None
    klasor = os.path.join(CIKTI, "donem"); os.makedirs(klasor, exist_ok=True)
    png = kart(donem, sonuc, os.path.join(klasor, f"{donem}.png"), bugun)
    try: pd_ = pdf(donem, sonuc, os.path.join(klasor, f"{donem}.pdf"))
    except Exception as ex: pd_ = None; print("PDF üretilemedi:", ex, file=sys.stderr)
    json.dump({"donem": donem, "tarih": str(bugun), "varliklar": [{k: v for k, v in r.items() if k != "_s"} for r in sonuc]},
              open(os.path.join(klasor, f"{donem}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    if gonder:
        import tg
        b = tg.Bot("durum"); ad = DONEM[donem]["ad"]; omur = 24 * 8 if donem == "haftalik" else 24 * 32
        al = [r["ad"] for r in sonuc if "AL" in r["etiket"] and r["kod"] != "VIX"]; zay = [r["ad"] for r in sonuc if "SAT" in r["etiket"] and r["kod"] != "VIX"]
        alt = (f"📊 <b>{ad.upper()} DURUM RAPORU</b>\nOlumlu: {', '.join(al) or '–'}\nZayıf: {', '.join(zay) or '–'}\n"
               f"Ayrıntılar ve grafikler PDF'te.")
        b.sil_anahtar(f"durum_{donem}")
        b.foto(png, alt[:1000], f"durum_{donem}", omur)
        if pd_: b.belge(pd_, f"KATKAY_{ad}_Durum_{bugun:%Y%m%d}.pdf", f"{ad} durum raporu (PDF)", f"durum_{donem}", omur)
        b.kaydet()
    print(f"{donem} durum raporu üretildi: {len(sonuc)} varlık")
    return sonuc


if __name__ == "__main__":
    arg = sys.argv[1:]
    gonder = "gonder" in arg or not any(a in ("haftalik", "aylik") for a in arg)
    if "haftalik" in arg or "aylik" in arg:
        for d in ("haftalik", "aylik"):
            if d in arg: calistir(d, gonder="gonder" in arg)
    else:   # zamanlanmış çağrı
        t = dt.datetime.now(TSI).date()
        if t.weekday() == 5: calistir("haftalik")
        if t.day == 1: calistir("aylik")
        if t.weekday() != 5 and t.day != 1: print("Bugün rapor günü değil.")
