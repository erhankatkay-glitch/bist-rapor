# -*- coding: utf-8 -*-
"""Türkiye makro verisi: TÜFE (yıllık/aylık) ve TCMB politika faizi.

Birincil kaynak: TCMB'nin herkese açık internet tabloları (anahtar gerekmez).
Yedek: TCMB EVDS (EVDS_KEY varsa), ardından bülten dalındaki son kayıtlı değer ("bayat" etiketiyle).
Kullanım (Actions): python makro_tr.py <cikti_klasoru>  → <cikti>/makro/tr_makro.json"""
import datetime as dt
import json
import os
import re
import sys
import urllib.request

TUFE_URL = "https://www.tcmb.gov.tr/wps/wcm/connect/tr/tcmb+tr/main+menu/istatistikler/enflasyon+verileri"
FAIZ_URL = ("https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Temel+Faaliyetler/Para+Politikasi/"
            "Merkez+Bankasi+Faiz+Oranlari/1+Hafta+Repo")
BULTEN_URL = "https://raw.githubusercontent.com/erhankatkay-glitch/bist-rapor/bulten/makro/tr_makro.json"
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def _getir(url, zaman_asimi=30):
    r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (KATKAY arastirma)", "Accept-Language": "tr-TR,tr;q=0.9"})
    return urllib.request.urlopen(r, timeout=zaman_asimi).read().decode("utf-8", "replace")


def _satirlar(html):
    """HTML tablolarındaki satırları hücre metinleri listesi olarak döndürür (bağımlılıksız)."""
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S | re.I):
        hucre = [re.sub(r"<[^>]+>|&nbsp;", " ", h) for h in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S | re.I)]
        hucre = [re.sub(r"\s+", " ", h).strip() for h in hucre]
        if any(hucre): out.append(hucre)
    return out


def _sayi(x):
    x = (x or "").replace("%", "").strip()
    if not x or x == "-": return None
    if "," in x and "." in x: x = x.replace(".", "").replace(",", ".")
    else: x = x.replace(",", ".")
    try:
        return float(x)
    except ValueError:
        return None


def tufe_coz(html):
    """TCMB enflasyon tablosu → [{"donem": "2026-10", "yillik": 29.77, "aylik": 2.58}, …] yeniden eskiye."""
    out = []
    for h in _satirlar(html):
        if len(h) < 3: continue
        m = re.fullmatch(r"(\d{1,2})-(\d{4})", h[0])
        if not m: continue
        y, a = _sayi(h[1]), _sayi(h[2])
        if y is None or not (-50 < y < 500): continue
        out.append({"donem": f"{m.group(2)}-{int(m.group(1)):02d}", "yillik": y, "aylik": a})
    # aynı sayfada ÜFE tablosu da olabilir: ilk (TÜFE) tablonun dönemleri tekrar ederse kes
    gorulen, temiz = set(), []
    for r in out:
        if r["donem"] in gorulen: break
        gorulen.add(r["donem"]); temiz.append(r)
    return sorted(temiz, key=lambda r: r["donem"], reverse=True)


def faiz_coz(html):
    """TCMB 1 hafta repo tablosu → {"tarih": "2026-10-23", "oran": 39.5, "onceki": 40.5, "onceki_tarih": …}."""
    kay = []
    for h in _satirlar(html):
        if len(h) < 2: continue
        m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", h[0])
        if not m: continue
        oran = _sayi(h[-1]) if _sayi(h[-1]) is not None else _sayi(h[1])
        if oran is None or not (0 <= oran < 200): continue
        kay.append((f"{m.group(3)}-{m.group(2)}-{m.group(1)}", oran))
    if not kay: return None
    kay.sort()
    son = kay[-1]; onc = kay[-2] if len(kay) > 1 else (None, None)
    return {"tarih": son[0], "oran": son[1], "onceki_tarih": onc[0], "onceki": onc[1]}


def donem_adi(donem):
    y, a = donem.split("-")
    return f"{AYLAR[int(a) - 1]} {y}"


def _evds_tufe(anahtar):
    try:
        import bist_makro as mk
        e, _ = mk.evds_paneli(anahtar)
        t = e.get("TÜFE (yıllık %)")
        if t: return [{"donem": f"{t['tarih']:%Y-%m}", "yillik": round(float(t["deger"]), 2), "aylik": None}]
    except Exception:
        pass
    return None


def topla(onceki=None, evds_anahtar=None):
    """Kaynakları sırayla dener; her alanın kaynağını ve çekilme zamanını yazar."""
    simdi = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    sonuc = {"guncellendi": simdi, "hatalar": {}}
    try:
        t = tufe_coz(_getir(TUFE_URL))
        if not t: raise ValueError("tablo boş")
        sonuc["tufe"] = {"seri": t[:25], "kaynak": "TCMB", "url": TUFE_URL, "cekildi": simdi}
    except Exception as ex:
        sonuc["hatalar"]["tufe"] = str(ex)[:160]
        t = _evds_tufe(evds_anahtar) if evds_anahtar else None
        if t: sonuc["tufe"] = {"seri": t, "kaynak": "TCMB EVDS", "url": "https://evds3.tcmb.gov.tr", "cekildi": simdi}
        elif onceki and onceki.get("tufe"): sonuc["tufe"] = dict(onceki["tufe"], bayat=True)
    try:
        f = faiz_coz(_getir(FAIZ_URL))
        if not f: raise ValueError("tablo boş")
        sonuc["faiz"] = dict(f, kaynak="TCMB", url=FAIZ_URL, cekildi=simdi)
    except Exception as ex:
        sonuc["hatalar"]["faiz"] = str(ex)[:160]
        if onceki and onceki.get("faiz"): sonuc["faiz"] = dict(onceki["faiz"], bayat=True)
    if sonuc.get("tufe") and sonuc.get("faiz"):
        y = sonuc["tufe"]["seri"][0]["yillik"]
        sonuc["reel_faiz"] = round(((1 + sonuc["faiz"]["oran"] / 100) / (1 + y / 100) - 1) * 100, 2)
    return sonuc


def ozet_satiri(m):
    """Telegram / uygulama için tek satır: 'TÜFE %29,77 (Ekim 2026) · Politika faizi %39,50 · Reel faiz +%7,4'."""
    if not m: return ""
    p = []
    if m.get("tufe"):
        r = m["tufe"]["seri"][0]
        p.append(f"TÜFE %{r['yillik']:.2f} ({donem_adi(r['donem'])})".replace(".", ","))
    if m.get("faiz"):
        p.append(f"Politika faizi %{m['faiz']['oran']:.2f}".replace(".", ","))
    if m.get("reel_faiz") is not None:
        p.append(f"Reel faiz {'+' if m['reel_faiz'] >= 0 else '−'}%{abs(m['reel_faiz']):.1f}".replace(".", ","))
    return " · ".join(p)


def oku(zaman_asimi=10):
    """Bülten dalındaki son makro dosyası (uygulama ve diğer işler için)."""
    try:
        return json.loads(_getir(BULTEN_URL, zaman_asimi))
    except Exception:
        return None


if __name__ == "__main__":
    cikti = sys.argv[1] if len(sys.argv) > 1 else "cikti"
    m = topla(oku(), os.environ.get("EVDS_KEY") or None)
    print(json.dumps({k: v for k, v in m.items() if k != "tufe"}, ensure_ascii=False))
    print(ozet_satiri(m))
    if m.get("tufe") or m.get("faiz"):
        os.makedirs(os.path.join(cikti, "makro"), exist_ok=True)
        json.dump(m, open(os.path.join(cikti, "makro", "tr_makro.json"), "w"), ensure_ascii=False, indent=1)
