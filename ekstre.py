"""Aşama 16: banka / aracı kurum portföy ekstresinden (Excel, CSV ya da PDF) hisse ve adetleri okur — yalnız okuma.

Bankaların ekstre biçimleri farklı olduğu için sabit şablon yok:
  1) Tablo dosyalarında (xlsx/xls/csv) başlık satırı aranır: kod sütunu (Menkul/Kıymet/Hisse/Sembol…), adet sütunu
     (Adet/Miktar/Nominal/Bakiye…), varsa maliyet sütunu (Ort. Maliyet/Alış Fiyatı…).
  2) Başlık bulunamazsa ya da PDF ise satır satır metin taranır: bilinen bir BIST kodu + ardından gelen ilk sayı = adet.
Dosya yalnız bellekte işlenir; hiçbir yere kaydedilmez, depoya yazılmaz.
"""
import io
import re

KOD_BAS = ("menkul", "kıymet", "kiymet", "hisse", "sembol", "enstrüman", "enstruman", "varlık", "varlik", "kod", "ürün", "urun", "araç", "arac")
ADET_BAS = ("adet", "miktar", "nominal", "lot", "bakiye", "kullanılabilir", "kullanilabilir", "toplam adet")
MAL_BAS = ("ort. maliyet", "ortalama maliyet", "maliyet fiyat", "ort.maliyet", "maliyet", "alış fiyat", "alis fiyat", "ortalama alış", "ort. alış")
_KOD = re.compile(r"\b([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ0-9]{2,5})(?:\.E)?\b")


def sayi(x):
    """'1.250,50' / '1,250.50' / '1250' / 1250.5 → float; olmazsa None."""
    if x is None: return None
    if isinstance(x, (int, float)): return float(x) if x == x else None
    s = re.sub(r"[^\d,.\-]", "", str(x))
    if not re.search(r"\d", s): return None
    if "," in s and "." in s:      # ikisi de var: sondaki ondalık ayıracıdır
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:                 # yalnız virgül: tek virgül ondalık (Türkçe), çok virgül binlik
        s = s.replace(",", ".") if s.count(",") == 1 else s.replace(",", "")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[1]) == 3 and s.split(".")[0] not in ("0", "-0")):
        s = s.replace(".", "")     # yalnız nokta, 3 haneli grup: Türkçe binlik (1.000 adet)
    try: return float(s)
    except ValueError: return None


def _kucuk(x): return str(x).strip().replace("İ", "i").replace("I", "ı").lower()


def kod_bul(metin, kodlar):
    for m in _KOD.finditer(str(metin).upper().replace("İ", "I")):
        if m.group(1) in kodlar: return m.group(1)
    return None


def _sutun(basliklar, adaylar, haric=()):
    for i, b in enumerate(basliklar):
        k = _kucuk(b)
        if any(a in k for a in adaylar) and not any(h in k for h in haric): return i
    return None


def _tablolar(veri, ad):
    import pandas as pd
    ad = ad.lower()
    if ad.endswith((".xlsx", ".xlsm", ".xls")):
        return list(pd.read_excel(io.BytesIO(veri), sheet_name=None, header=None, dtype=object).values())
    for kod in ("utf-8-sig", "cp1254", "latin-1"):
        try: metin = veri.decode(kod); break
        except UnicodeDecodeError: continue
    ayr = max((";", "\t", ","), key=lambda a: metin[:4000].count(a))
    return [pd.read_csv(io.StringIO(metin), sep=ayr, header=None, dtype=object, engine="python", on_bad_lines="skip")]


def _tablodan(df, kodlar):
    ham = df.where(df.notna(), "").values.tolist()
    satirlar = [[str(x) for x in r] for r in ham]
    for bi, r in enumerate(satirlar[:40]):    # başlık satırını bul
        ka = _sutun(r, KOD_BAS); aa = _sutun(r, ADET_BAS, haric=("tutar", "değer", "deger", "fiyat"))
        if ka is None or aa is None or ka == aa: continue
        ma = _sutun(r, MAL_BAS, haric=("tutar", "toplam"))
        out = []
        for s in ham[bi + 1:]:
            kod = kod_bul(s[ka], kodlar); adet = sayi(s[aa]) if aa < len(s) else None
            if kod and adet and adet > 0:
                out.append((kod, adet, sayi(s[ma]) if ma is not None and ma < len(s) else None))
        if out: return out
    return []


def _metinden(metin, kodlar):
    out = []
    for satir in metin.splitlines():
        kod = kod_bul(satir, kodlar)
        if not kod: continue
        sonra = satir.upper().replace("İ", "I").split(kod, 1)[1]
        sayilar = [sayi(x) for x in re.findall(r"-?\d[\d.,]*", sonra)]
        sayilar = [x for x in sayilar if x is not None]
        if sayilar and sayilar[0] > 0: out.append((kod, sayilar[0], None))
    return out


def coz(veri, ad, kodlar):
    """veri: dosya baytları, ad: dosya adı, kodlar: bilinen BIST kodları kümesi → [(kod, adet, maliyet|None)], notlar"""
    kodlar = set(kodlar); bulunan, not_ = [], ""
    if ad.lower().endswith(".pdf"):
        from pypdf import PdfReader
        metin = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(veri)).pages)
        bulunan = _metinden(metin, kodlar); not_ = "PDF metninden satır satır okundu"
    else:
        for df in _tablolar(veri, ad):
            bulunan = _tablodan(df, kodlar)
            if bulunan: not_ = "tablo başlıklarından okundu"; break
        if not bulunan and not ad.lower().endswith((".xlsx", ".xlsm", ".xls")):
            for kod in ("utf-8-sig", "cp1254", "latin-1"):
                try: metin = veri.decode(kod); break
                except UnicodeDecodeError: continue
            bulunan = _metinden(metin.replace(";", " ").replace("\t", " "), kodlar)
            if bulunan: not_ = "başlık bulunamadı, satır satır okundu"
        if not bulunan:
            for df in _tablolar(veri, ad):
                bulunan = _metinden("\n".join(" ".join(r) for r in df.fillna("").astype(str).values.tolist()), kodlar)
                if bulunan: not_ = "başlık bulunamadı, satır satır okundu"; break
    birlesik = {}   # aynı hisse birden çok satırda (farklı hesap/alt hesap) → adetler toplanır, maliyet adet ağırlıklı
    for kod, adet, mal in bulunan:
        a, m = birlesik.get(kod, (0.0, None))
        if mal and m is not None: m = (m * a + mal * adet) / (a + adet)
        elif mal and a == 0: m = mal
        birlesik[kod] = (a + adet, m)
    return [(k, a, m) for k, (a, m) in birlesik.items()], not_


def satirlar(liste):
    """→ portföy kutusuna yazılacak metin: 'THYAO 1000 @ 285,4'"""
    def f(x): return (f"{x:,.4f}".rstrip("0").rstrip(".") if x % 1 else f"{x:,.0f}").replace(",", "X").replace(".", ",").replace("X", "")
    return "\n".join(f"{k} {f(a)}" + (f" @ {f(round(m, 2))}" if m else "") for k, a, m in liste)
