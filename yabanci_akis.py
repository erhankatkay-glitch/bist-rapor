# -*- coding: utf-8 -*-
"""Yabancı yatırımcı akışı (BIST, hisse senedi) — TCMB Haftalık Menkul Kıymet İstatistikleri.
Kaynak: TCMB'nin herkese açık yayımladığı 'Menkul Kıymet İstatistikleri' dosyası (Tablo 1):
yurt dışında yerleşik kişilerin haftalık NET hisse senedi alım/satımı ve stok (milyon ABD $).
TCMB her perşembe 14:30'da bir önceki haftanın (cuma) verisini yayımlar. Dosyada son 5 hafta bulunur;
daha uzun geçmiş (4 hafta = aylık, 13 hafta = 3 aylık toplam) haftalık arşivde biriktirilir.
Arşiv: {DURUM}/yabanci/akis.json (yalnızca alarm iş akışı yazar; diğerleri okur)"""
import os, re, io, json, zipfile, datetime as dt
import pandas as pd
import requests

SAYFA = ("https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Istatistikler/"
         "Parasal+ve+Finansal+Istatistikler/Menkul+Kiymet+Istatistikleri")
H = {"User-Agent": "Mozilla/5.0 (KATKAY Yatirim veri istemcisi)"}
YOL = os.path.join("yabanci", "akis.json")


def _klon():
    return os.environ.get("DURUM_KLON", "onceki")


def _cikti():
    return os.environ.get("DURUM_CIKTI", "cikti")


def _tarih(x):
    if isinstance(x, (pd.Timestamp, dt.datetime, dt.date)): return pd.Timestamp(x).date().isoformat()
    try: return dt.datetime.strptime(str(x).strip()[:10], "%d.%m.%Y").date().isoformat()
    except Exception:
        try: return pd.Timestamp(str(x)).date().isoformat()
        except Exception: return None


def cek(timeout=40):
    """TCMB dosyasını indirip haftalık seriyi döndürür: [{tarih, hisse_net, hisse_stok, dibs_net}] (milyon $)."""
    r = requests.get(SAYFA, headers=H, timeout=timeout); r.raise_for_status()
    z = [l.replace("&amp;", "&") for l in re.findall(r'href="([^"]+?\.zip[^"]*)"', r.text, re.I)]
    if not z: raise ValueError("TCMB sayfasında veri dosyası bulunamadı")
    u = z[0] if z[0].startswith("http") else "https://www.tcmb.gov.tr" + z[0]
    b = requests.get(u, headers=H, timeout=60); b.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(b.content))
    ad = next(n for n in zf.namelist() if n.lower().endswith((".xlsx", ".xls")))
    T = pd.read_excel(io.BytesIO(zf.read(ad)), sheet_name=None, header=None)
    df = T.get("T1")
    if df is None: df = next(v for k, v in T.items() if str(k).strip().upper() == "T1")
    etiket = df.iloc[:, 1].astype(str).str.strip()

    def blok(baslik):
        i = next(k for k, e in enumerate(etiket) if e.upper().startswith(baslik))
        tarihler = [_tarih(x) for x in df.iloc[i, 2:].tolist()]
        j = next(k for k in range(i + 1, len(df)) if etiket.iloc[k].lower().startswith("hisse senet"))
        dibs = next((k for k in range(i + 1, len(df)) if "kesin al" in etiket.iloc[k].lower()), None)
        return tarihler, df.iloc[j, 2:].tolist(), (df.iloc[dibs, 2:].tolist() if dibs is not None else [None] * len(tarihler))

    t_s, stok, _ = blok("A. STOK")
    t_n, net, dibs = blok("B. NET DE")
    S = dict(zip(t_s, stok))
    out = []
    for t, n, d in zip(t_n, net, dibs):
        if not t or n is None or pd.isna(n): continue
        out.append({"tarih": t, "hisse_net": round(float(n), 2), "hisse_stok": (round(float(S[t]), 2) if S.get(t) is not None and not pd.isna(S.get(t)) else None),
                    "dibs_net": (round(float(d), 2) if d is not None and not pd.isna(d) else None)})
    if not out: raise ValueError("TCMB tablosunda hisse senedi satırı okunamadı")
    return sorted(out, key=lambda x: x["tarih"])


def arsiv_oku(kok=None):
    for k in ([kok] if kok else [_cikti(), _klon()]):
        try: return json.load(open(os.path.join(k, YOL), encoding="utf-8"))
        except Exception: pass
    return {"seri": [], "guncelleme": None}


def guncelle():
    """Yeni veriyi arşive ekler ve {CIKTI}/yabanci/akis.json'a yazar. Döner: (arşiv, yeni_hafta_eklendi_mi).
    Yalnızca alarm iş akışında çağrılmalı (yayın birimi 'yabanci' her yayında baştan yazılır)."""
    A = arsiv_oku()
    eski = {x["tarih"]: x for x in A.get("seri", [])}
    onceki_son = max(eski) if eski else None
    try:
        for x in cek():
            eski[x["tarih"]] = x            # TCMB revizyonları da işlenir
    except Exception as ex:
        print("Yabancı akışı alınamadı:", ex)
        return A, False
    A = {"seri": [eski[k] for k in sorted(eski)][-260:], "guncelleme": dt.datetime.now(dt.timezone.utc).isoformat(),
         "kaynak": "TCMB Haftalık Menkul Kıymet İstatistikleri"}
    os.makedirs(os.path.join(_cikti(), "yabanci"), exist_ok=True)
    json.dump(A, open(os.path.join(_cikti(), YOL), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    yeni = bool(A["seri"]) and A["seri"][-1]["tarih"] != onceki_son
    return A, yeni


def _ardisik(seri):
    """Son haftadan geriye aynı yönde kaç hafta üst üste (+ alış, - satış)."""
    if not seri: return 0
    yon = 1 if seri[-1]["hisse_net"] > 0 else -1; n = 0
    for x in reversed(seri):
        if (x["hisse_net"] > 0) == (yon > 0) and x["hisse_net"] != 0: n += 1
        else: break
    return n * yon


def ozet(A=None):
    A = A or arsiv_oku(); s = A.get("seri", [])
    if not s: return None
    son = s[-1]
    def topla(k):
        return round(sum(x["hisse_net"] for x in s[-k:]), 1) if len(s) >= k else None
    return {"tarih": son["tarih"], "hafta": son["hisse_net"], "dort": topla(4), "onuc": topla(13),
            "stok": son.get("hisse_stok"), "ardisik": _ardisik(s), "hafta_sayisi": len(s),
            "seri": [{"tarih": x["tarih"], "net": x["hisse_net"]} for x in s[-13:]]}


def mn(x, isaret=True):
    if x is None: return "–"
    s = f"{abs(x):,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return (("+" if x > 0 else "−" if x < 0 else "") if isaret else "") + s + " mn $"


def _gun(t):
    d = dt.date.fromisoformat(t)
    return f"{d.day} {['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'][d.month - 1]}"


def cumle(o):
    """Bilmeyenin de anlayacağı tek cümle."""
    if not o: return None
    yon = "aldı" if o["hafta"] > 0 else "sattı"
    c = f"Yabancılar {_gun(o['tarih'])} haftasında BIST'te net {mn(abs(o['hafta']), False)} hisse {yon}"
    if o["dort"] is not None: c += f" (son 4 hafta {mn(o['dort'])})"
    a = o["ardisik"]
    if abs(a) >= 3: c += f"; {abs(a)} haftadır üst üste {'alıcı' if a > 0 else 'satıcı'}"
    return c + "."


def kart_bolumu(o, C):
    """Telegram bildirim kartı için bölüm."""
    if not o: return None
    sat = [{"sol": f"{_gun(o['tarih'])} haftası", "sag": mn(o["hafta"]), "sag_renk": C["yesil"] if o["hafta"] > 0 else C["kirmizi"],
            "nokta": C["yesil"] if o["hafta"] > 0 else C["kirmizi"],
            "alt": "Yurt dışında yerleşiklerin BIST'teki haftalık net hisse alımı (+) / satımı (−)."}]
    if o["dort"] is not None:
        sat.append({"sol": "Son 4 hafta (aylık)", "sag": mn(o["dort"]), "sag_renk": C["yesil"] if o["dort"] > 0 else C["kirmizi"]})
    if o["onuc"] is not None:
        sat.append({"sol": "Son 13 hafta (3 aylık)", "sag": mn(o["onuc"]), "sag_renk": C["yesil"] if o["onuc"] > 0 else C["kirmizi"]})
    else:
        sat.append({"sol": "Son 13 hafta (3 aylık)", "sag": "birikiyor", "sag_renk": C["soluk"],
                    "alt": f"Arşivde {o['hafta_sayisi']} hafta var; 13 haftaya ulaşınca 3 aylık toplam gösterilecek."})
    if o.get("stok"):
        stok = f"{o['stok'] / 1000:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") + " milyar $"
        sat.append({"sol": "Yabancının elindeki BIST hisseleri", "sag": stok, "sag_renk": C["yazi"]})
    return {"baslik": "Yabancı yatırımcı akışı (TCMB)", "renk": C["mavi"], "satirlar": sat}


def zamani_mi(A):
    """TCMB perşembe 14:30'da yayımlar: perşembe 14:00 – cuma sonu arası ya da arşiv boş/eskiyse kontrol edilir."""
    t = dt.datetime.now(dt.timezone(dt.timedelta(hours=3)))
    if not A.get("seri"): return True
    son = dt.date.fromisoformat(A["seri"][-1]["tarih"])
    if (t.date() - son).days >= 13: return True          # bir haftalık veri kaçmışsa
    return (t.weekday() == 3 and t.hour >= 14) or t.weekday() == 4


def bildir():
    """Yeni hafta verisi geldiyse Telegram'a kart gönderir (alarm iş akışından yarım saatte bir çağrılır)."""
    import tg, kart as K
    A0 = arsiv_oku()
    if not zamani_mi(A0):
        if A0.get("seri"):   # arşivi bir sonraki yayına taşı
            os.makedirs(os.path.join(_cikti(), "yabanci"), exist_ok=True)
            json.dump(A0, open(os.path.join(_cikti(), YOL), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("Yabancı akışı: kontrol zamanı değil."); return
    A, yeni = guncelle()
    if not yeni: print("Yabancı akışı: yeni hafta yok."); return
    o = ozet(A); b = tg.Bot("yabanci")
    import tempfile
    yol = os.path.join(tempfile.mkdtemp(), "yabanci_akis.png")   # yayın klasörüne yazılmaz
    alt = "Haftalık net alım (+) / satım (−) · milyon ABD $"
    yorum = ("Yabancı alımı genelde BIST 100 ve bankacılık hisselerini destekler; satış ise baskı yaratabilir."
             " Haftalık veri tek başına al-sat sinyali değildir, eğilimle birlikte okunmalıdır.")
    try:
        K.bildirim_karti(f"YABANCI AKIŞI · {tg.buyuk(_gun(o['tarih']))} HAFTASI", "Yabancılar BIST'te " + ("alıcı" if o["hafta"] > 0 else "satıcı"),
                         alt, [kart_bolumu(o, K.C)], yol, vurgu=K.C["mavi"], not_=yorum)
        b.sil_anahtar("yabanci_akis")
        b.foto(yol, "🌍 <b>YABANCI AKIŞI</b>\n" + cumle(o), "yabanci_akis", 46)
    except Exception as ex:
        print("Kart gönderilemedi:", ex)
        b.mesaj("🌍 <b>YABANCI AKIŞI</b>\n" + cumle(o), "yabanci_akis", 46, yerine=True)
    b.kaydet()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "bildir":
        bildir()
    else:
        A, yeni = guncelle(); o = ozet(A)
        print("yeni hafta:", yeni); print(cumle(o)); print(json.dumps(o, ensure_ascii=False)[:600])
