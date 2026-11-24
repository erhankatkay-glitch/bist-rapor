# -*- coding: utf-8 -*-
"""Statik BIST verileri: şirket adları, hisse evrenleri, holding iştirak payları.
Bu listeler elle güncellenir; değişiklik olduğunda buradan düzeltin."""

# Türkçe karakterli şirket adları (arama ve rapor başlığı için)
SIRKETLER = {
    "AEFES": "Anadolu Efes", "AGESA": "AgeSA Hayat ve Emeklilik", "AGHOL": "AG Anadolu Grubu Holding",
    "AKBNK": "Akbank", "AKCNS": "Akçansa Çimento", "AKGRT": "Aksigorta", "AKSA": "Aksa Akrilik",
    "AKSEN": "Aksa Enerji", "ALARK": "Alarko Holding", "ALBRK": "Albaraka Türk", "ALFAS": "Alfa Solar Enerji",
    "ALKIM": "Alkim Kimya", "ALTNY": "Altınay Savunma", "ANSGR": "Anadolu Sigorta", "ARCLK": "Arçelik",
    "ARDYZ": "ARD Bilişim", "ASELS": "Aselsan", "ASTOR": "Astor Enerji", "ASUZU": "Anadolu Isuzu",
    "AYDEM": "Aydem Enerji", "AYGAZ": "Aygaz", "BANVT": "Banvit", "BIMAS": "BİM Birleşik Mağazalar",
    "BRISA": "Brisa Bridgestone Sabancı", "BRSAN": "Borusan Boru", "BRYAT": "Borusan Yatırım",
    "BTCIM": "Batıçim", "CANTE": "Çan2 Termik", "CCOLA": "Coca-Cola İçecek", "CIMSA": "Çimsa Çimento",
    "CLEBI": "Çelebi Hava Servisi", "CRFSA": "CarrefourSA", "CWENE": "CW Enerji", "DOAS": "Doğuş Otomotiv",
    "DOHOL": "Doğan Holding", "ECILC": "EİS Eczacıbaşı İlaç", "EGEEN": "Ege Endüstri",
    "EKGYO": "Emlak Konut GYO", "ENERY": "Enerya Enerji", "ENJSA": "Enerjisa Enerji", "ENKAI": "Enka İnşaat",
    "EREGL": "Ereğli Demir Çelik", "EUPWR": "Europower Enerji", "FROTO": "Ford Otosan",
    "GARAN": "Garanti BBVA", "GENIL": "Gen İlaç", "GESAN": "Girişim Elektrik", "GUBRF": "Gübre Fabrikaları",
    "HALKB": "Halkbank", "HEKTS": "Hektaş", "INDES": "İndeks Bilgisayar", "TRENJ": "TR Doğal Enerji",
    "ISCTR": "İş Bankası (C)", "ISDMR": "İskenderun Demir Çelik", "ISGYO": "İş GYO", "ISMEN": "İş Yatırım",
    "KAREL": "Karel Elektronik", "KCAER": "Kocaer Çelik", "KCHOL": "Koç Holding", "KONTR": "Kontrolmatik",
    "KORDS": "Kordsa Teknik Tekstil", "TRMET": "TR Anadolu Metal Madencilik", "TRALT": "Türk Altın İşletmeleri",
    "KRDMD": "Kardemir (D)", "KTLEV": "Katılımevim", "LOGO": "Logo Yazılım", "MAVI": "Mavi Giyim",
    "MGROS": "Migros", "MIATK": "Mia Teknoloji", "MPARK": "MLP Sağlık", "NETAS": "Netaş",
    "NUHCM": "Nuh Çimento", "ODAS": "Odaş Elektrik", "OTKAR": "Otokar", "OYAKC": "Oyak Çimento",
    "PASEU": "Pasifik Eurasia", "PETKM": "Petkim", "PGSUS": "Pegasus", "REEDR": "Reeder Teknoloji",
    "SAHOL": "Sabancı Holding", "SASA": "SASA Polyester", "SDTTR": "SDT Uzay ve Savunma", "SISE": "Şişecam",
    "SKBNK": "Şekerbank", "SMRTG": "Smart Güneş Enerjisi", "SOKM": "Şok Marketler", "TABGD": "TAB Gıda",
    "TATGD": "Tat Gıda", "TAVHL": "TAV Havalimanları", "TCELL": "Turkcell", "THYAO": "Türk Hava Yolları",
    "TKFEN": "Tekfen Holding", "TKNSA": "Teknosa", "TOASO": "Tofaş", "TRGYO": "Torunlar GYO", "TSKB": "TSKB",
    "TTKOM": "Türk Telekom", "TTRAK": "Türk Traktör", "TUPRS": "Tüpraş", "TURSG": "Türkiye Sigorta",
    "ULKER": "Ülker", "VAKBN": "VakıfBank", "VESBE": "Vestel Beyaz Eşya", "VESTL": "Vestel",
    "YKBNK": "Yapı Kredi", "ZOREN": "Zorlu Enerji",
}

# Tarayıcı için büyük ve likit hisseler (BIST 30'a benzer; endeks bileşimi dönemsel değişir)
BUYUK_HISSELER = ["AKBNK", "ASELS", "ASTOR", "BIMAS", "CCOLA", "EKGYO", "ENKAI", "EREGL", "FROTO", "GARAN",
                  "GUBRF", "ISCTR", "KCHOL", "KONTR", "TRALT", "KRDMD", "MGROS", "OYAKC", "PETKM", "PGSUS",
                  "SAHOL", "SASA", "SISE", "TAVHL", "TCELL", "THYAO", "TOASO", "TTKOM", "TUPRS", "YKBNK"]

# Holdinglerin halka açık iştiraklerindeki ekonomik payları (%).
# Kaynak: KAP şirket genel bilgi formları (doğrudan paylar). Dolaylı paylar notta açıklandı.
# Not: KCHOL'ün Tüpraş payı = %4,27 doğrudan + Enerji Yatırımları A.Ş. (%77 Koç) üzerinden %46,4 × 0,77;
#      Yapı Kredi payı = %20,22 doğrudan + Koç Finansal Hizmetler üzerinden %40,95.
HOLDING_PAYLARI = {
    "KCHOL": {"TUPRS": 0.0427 + 0.464 * 0.77, "FROTO": 0.3865, "ARCLK": 0.4853, "YKBNK": 0.2022 + 0.4095,
              "TOASO": 0.3762, "AYGAZ": 0.4068, "OTKAR": 0.4738, "TTRAK": 0.3750},
    "SAHOL": {"AKBNK": 0.4075, "ENJSA": 0.40, "AKGRT": 0.36, "AGESA": 0.40, "KORDS": 0.7111,
              "BRISA": 0.4362, "TKNSA": 0.50, "CIMSA": 0.5454},
    "AGHOL": {"AEFES": 0.4305, "MGROS": 0.50},  # CCOLA, AEFES üzerinden dolaylıdır (AEFES değerine dahil)
}
# Hedef holding iskontosu varsayımları (tarihsel aralıklara göre; formdan değiştirilebilir)
HOLDING_ISKONTO = {"KCHOL": 0.30, "SAHOL": 0.40, "AGHOL": 0.40}


import os as _os

LISTE_DOSYA = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "hisse_listesi.csv")
_TUM = {}


def tum_sirketler():
    """Tüm BIST hisseleri {kod: ad}. Kaynak: depodaki hisse_listesi.csv (her sabah güncellenir) + canlı liste
    (guncelle() ile eklenir) + elle seçilmiş adlar."""
    if not _TUM:
        try:
            import pandas as pd
            df = pd.read_csv(LISTE_DOSYA, dtype=str)
            _TUM.update({r["Kod"]: (r.get("Ad") or r["Kod"]) for _, r in df.iterrows() if isinstance(r.get("Kod"), str)})
        except Exception:
            pass
        _TUM.update(SIRKETLER)
    return _TUM


def guncelle(sozluk):
    """Canlı alınan tam listeyi ekler (elle seçilmiş adlar korunur)."""
    tum_sirketler()
    for k, v in sozluk.items():
        if k and k not in SIRKETLER: _TUM[k] = v or k


def sirket_adi(kod):
    return tum_sirketler().get(kod.upper(), kod.upper())


def ad(kod):
    return tum_sirketler().get(kod.upper())


def arama_secenekleri():
    return [f"{k} — {v}" for k, v in sorted(tum_sirketler().items())]


def secimden_kod(metin):
    """'THYAO — Türk Hava Yolları' veya 'aselsan' veya 'asels' → 'ASELS'."""
    if not metin:
        return ""
    t = metin.strip()
    if "—" in t:
        return t.split("—")[0].strip().upper()
    u = t.upper().replace(".IS", "")
    T_ = tum_sirketler()
    if u in T_:
        return u
    norm = lambda s: str(s).replace("I", "ı").replace("İ", "i").lower().replace("ı", "i")
    low = norm(t)
    for k, v in sorted(T_.items(), key=lambda x: (x[0] not in SIRKETLER, x[0])):
        if low and low in norm(v):
            return k
    return u.split()[0] if u else ""
