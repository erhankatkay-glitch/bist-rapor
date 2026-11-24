# -*- coding: utf-8 -*-
"""Borsa İstanbul'un herkese açık veri dosyaları ve KAP konulu haber takibi.
- Açığa satış bülteni (haftalık, pay bazında): borsaistanbul.com/datum/acigasat.zip
- İlk işlem tarihleri ve ilk gün kapanış fiyatları: borsaistanbul.com/datum/ilkislem.zip
- KAP bildirimleriyle ilgili haber başlıkları (Google Haberler) ve konu sınıflandırması"""
import io, re, zipfile, datetime as dt
import pandas as pd

DATUM = "https://borsaistanbul.com/datum/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}


def _xlsx(ad):
    import requests
    r = requests.get(DATUM + ad, headers=UA, timeout=60); r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    ic = sorted(z.namelist())[-1]
    return pd.read_excel(io.BytesIO(z.read(ic)), header=None)


def _baslik_satiri(df, anahtar):
    for i in range(min(15, len(df))):
        if any(anahtar in str(x).upper() for x in df.iloc[i].tolist()):
            return i
    return None


def _kod(x):
    return re.sub(r"\.[A-Z0-9]+$", "", str(x).strip().upper())


# ------------------------------------------------------------------ açığa satış
def aciga_satis():
    """Son haftanın pay bazında açığa satış verisi. DataFrame[Kod, Açığa satış TL, Açığa satış adet, ...], dönem metni"""
    ham = _xlsx("acigasat.zip")
    donem = str(ham.iloc[0, 0])
    i = _baslik_satiri(ham, "KOD")
    df = ham.iloc[i + 1:].copy(); df.columns = [str(c) for c in ham.iloc[i].tolist()]
    kc = next(c for c in df.columns if "Kodu" in c or "KOD" in c.upper())
    hc = next((c for c in df.columns if "Hacmi" in c or "Value" in c), None)
    mc = next((c for c in df.columns if "Miktar" in c or "Volume" in c), None)
    out = pd.DataFrame({"Kod": df[kc].map(_kod), "Açığa satış TL": pd.to_numeric(df[hc], errors="coerce") if hc else None,
                        "Açığa satış adet": pd.to_numeric(df[mc], errors="coerce") if mc else None})
    for c in df.columns:
        if "Ağırlıklı" in c or "Weighted" in c: out["Ort. fiyat"] = pd.to_numeric(df[c], errors="coerce")
    out = out.dropna(subset=["Kod"]); out = out[out["Kod"].str.match(r"^[A-Z0-9]{3,6}$")]
    out = out.groupby("Kod", as_index=False).sum(numeric_only=True)
    m = re.findall(r"(\d{2}\.\d{2}\.\d{4})", donem)
    out.attrs["donem"] = f"{m[0]} – {m[1]}" if len(m) >= 2 else donem
    out.attrs["bas"] = pd.to_datetime(m[0], dayfirst=True) if m else None
    out.attrs["son"] = pd.to_datetime(m[1], dayfirst=True) if len(m) > 1 else None
    return out


def aciga_satis_orani(satir, h, bas=None, son=None):
    """Açığa satış hacminin aynı dönemdeki toplam işlem hacmine oranı (Yahoo günlük verisinden)."""
    if satir is None or h is None: return None
    w = h
    if bas is not None and son is not None:
        w = h[(h.index >= bas) & (h.index <= son + pd.Timedelta(days=1))]
    if len(w) == 0: w = h.iloc[-5:]
    toplam = float((w["Close"] * w["Volume"]).sum())
    return float(satir["Açığa satış TL"]) / toplam if toplam > 0 else None


def aciga_yorumu(kod, satir, oran, donem):
    if satir is None: return f"{kod} son haftalık açığa satış bülteninde ({donem}) yer almıyor; dönem içinde kayda değer açığa satış işlemi bulunmuyor."
    mn = f"{satir['Açığa satış TL'] / 1e6:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    t = f"{donem} haftasında {kod} paylarında {mn} milyon TL açığa satış işlemi gerçekleşti"
    if oran is not None:
        t += "; bu, aynı dönemdeki toplam işlem hacminin yaklaşık yüzde " + f"{oran * 100:.1f}".replace(".", ",") + " kadarına denk geliyor"
        t += ". " + ("Oran yüksek: kısa vadeli düşüş beklentisi veya riskten korunma işlemleri yoğun." if oran > 0.15 else
                     "Oran orta seviyede." if oran > 0.07 else "Oran düşük; açığa satış baskısı sınırlı.")
    else:
        t += "."
    return t


# ------------------------------------------------------------------ ilk işlem (halka arz) verisi
def ilk_islem():
    """Resmi ilk işlem günü ve ilk gün kapanış fiyatları (yalnızca paylar). {kod: {"tarih", "ilk_kapanis", "unvan"}}"""
    ham = _xlsx("ilkislem.zip")
    i = _baslik_satiri(ham, "CARİ KOD") or _baslik_satiri(ham, "CURRENT CODE") or 0
    df = ham.iloc[i + 1:].copy(); df.columns = [str(c).upper() for c in ham.iloc[i].tolist()]
    cari = next(c for c in df.columns if "CARİ KOD" in c or "CURRENT CODE" in c)
    unvan = next((c for c in df.columns if "ÜNVAN" in c or "NAME" in c), None)
    ilkgun = next((c for c in df.columns if "İLK İŞLEM GÜNÜ" in c and "FİYAT" not in c), None) or \
             next((c for c in df.columns if "FIRST TRADING DAY" in c and "PRICE" not in c), None)
    fiyat = next((c for c in df.columns if "FİYAT" in c or "PRICE" in c), None)
    out = {}
    for _, r in df.iterrows():
        k = str(r[cari]).strip().upper()
        if not k.endswith(".E"): continue
        try: t = pd.to_datetime(r[ilkgun], dayfirst=True)
        except Exception: t = None
        out[_kod(k)] = {"tarih": t, "ilk_kapanis": pd.to_numeric(r[fiyat], errors="coerce") if fiyat else None,
                        "unvan": str(r[unvan]).strip() if unvan else None}
    return out


# ------------------------------------------------------------------ KAP konulu haberler
KAP_KONU = [
    ("Bedelsiz sermaye artırımı", 1, ("bedelsiz",)),
    ("Bedelli sermaye artırımı", -1, ("bedelli",)),
    ("Temettü / kâr payı", 1, ("temettü", "kar payı", "kâr payı")),
    ("Pay geri alımı", 1, ("geri alım", "geri alim")),
    ("Yeni iş / sipariş / sözleşme", 1, ("sipariş", "ihale", "sözleşme", "anlaşma imzal", "iş ilişkisi", "ihracat anlaşması")),
    ("Ortak / yönetici pay işlemi", 0, ("pay alım", "pay satış", "hisse alım", "hisse satış", "pay satışı", "pay alımı")),
    ("Finansal sonuçlar", 0, ("bilanço", "net kâr", "net kar", "finansal sonuç", "çeyrek", "dönem kârı", "zarar açıkla")),
    ("Yatırım / kapasite", 1, ("yatırım kararı", "kapasite", "fabrika", "tesis", "yatırıma başla")),
    ("Birleşme / satın alma", 0, ("satın al", "birleşme", "devral", "iştirak edin")),
    ("Ceza / dava / soruşturma", -1, ("ceza", "dava", "soruşturma", "tedbir", "işlem yasağı", "kredili işlem")),
    ("Derecelendirme", 0, ("kredi notu", "derecelendirme", "fitch", "moody", "jcr")),
    ("Halka arz / borsa işlemleri", 0, ("halka arz", "pazar değişikliği", "endekse dahil")),
]


def kap_siniflandir(baslik):
    b = str(baslik).replace("I", "ı").replace("İ", "i").lower()
    for ad, yon, kelimeler in KAP_KONU:
        if any(k in b for k in kelimeler): return ad, yon
    return None, 0


def kap_haberleri(kod, ad=None, gun=45, adet=12):
    """KAP bildirimleriyle ilgili haber başlıkları (Google Haberler) → konu ve yön etiketi."""
    import bist_rapor as br
    sonuc = []
    for sorgu in (f"{kod} KAP", f'"{ad}" KAP' if ad else None):
        if not sorgu: continue
        try:
            for x in br.haber_cek(kod, None, adet=adet, gun=gun, sorgu=sorgu)["liste"]:
                k, y = kap_siniflandir(x["baslik"])
                if k: sonuc.append({**x, "konu": k, "yon": y})
        except Exception:
            continue
    # Haber gerçekten bu şirketle ilgili mi? Başlıkta kod ya da unvanın ilk kelimesi geçmeli
    def _k(t): return str(t).replace("İ", "i").replace("I", "ı").lower()
    anahtarlar = {_k(kod)}
    if ad:
        ilk = _k(str(ad).split()[0]).strip(".,")
        if len(ilk) >= 3: anahtarlar.add(ilk)
    sonuc = [x for x in sonuc if any(a in _k(x["baslik"]) for a in anahtarlar)]
    gor, tekil = set(), []
    for x in sorted(sonuc, key=lambda x: x["tarih"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc), reverse=True):
        anahtar = x["baslik"][:60]
        if anahtar in gor: continue
        gor.add(anahtar); tekil.append(x)
    return tekil[:adet]


def kap_yorumu(liste):
    if not liste: return "Son 45 günde KAP bildirimleriyle ilişkilendirilebilen kayda değer bir haber başlığı bulunamadı."
    konular = pd.Series([x["konu"] for x in liste]).value_counts()
    t = "Son 45 günde öne çıkan bildirim konuları: " + ", ".join(f"{k} ({v})" for k, v in konular.head(4).items()) + "."
    olumlu = [x for x in liste if x["yon"] > 0]; olumsuz = [x for x in liste if x["yon"] < 0]
    if olumlu: t += f" Olumlu nitelikteki en güncel başlık: “{olumlu[0]['baslik'][:90]}”."
    if olumsuz: t += f" Dikkat gerektiren başlık: “{olumsuz[0]['baslik'][:90]}”."
    return t
