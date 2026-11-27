# -*- coding: utf-8 -*-
"""Haber etkisi motoru: piyasayı etkileyebilecek haberleri toplar, türünü ve yönünü sınıflandırır,
etkilenecek varlıkları ve beklenen yönü gerekçesiyle çıkarır, haberden bu yana piyasanın gerçek tepkisini
(fiyat ve hacim) ölçer, varlığın teknik durumunu ve aynı tür geçmiş haberlerden sonraki ortalama
hareketi ekler. Ekonomik takvimden günün önemli verilerini sabah özetler.

Kaynaklar (ücretsiz): Google Haberler RSS (Türkçe), ForexFactory haftalık takvim JSON'u, fiyatlar için
Binance/Yahoo. 30 dakikada bir alarm iş akışıyla çalışır: python haber.py
Çıktı: cikti/haber/{son.json, gorulen.json, olaylar.json, takvim.json}"""
import os, re, sys, json, time, hashlib, datetime as dt
import numpy as np
import pandas as pd

KLON = os.environ.get("DURUM_KLON", "onceki")
CIKTI = os.environ.get("DURUM_CIKTI", "cikti")
UTC = dt.timezone.utc
TSI = dt.timezone(dt.timedelta(hours=3))
PENCERE_SAAT = 3          # en fazla bu kadar eski haberler değerlendirilir
MAKS_MESAJ = 6            # bir turda Telegram'a en fazla bu kadar haber analizi

# ---------------------------------------------------------------------------------- yardımcılar
def kk(s):
    return str(s).replace("İ", "i").replace("I", "ı").lower()


def var(b, *kel):
    return any(k in b for k in kel)


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def yz(x):
    import bicim
    return bicim.yuzde(x, 1, True)


VARLIK_AD = {"NASDAQ": "Nasdaq", "SP500": "S&P 500", "XU100": "BIST 100", "XBANK": "BIST Banka", "USDTRY": "Dolar/TL", "ALTIN": "Altın (ons)", "GRAMALTIN": "Gram altın",
             "BRENT": "Brent petrol", "BTC/USDT": "Bitcoin", "ETH/USDT": "Ethereum", "GUMUS": "Gümüş", "THYAO": "THY", "PGSUS": "Pegasus",
             "TUPRS": "Tüpraş", "FROTO": "Ford Otosan", "TOASO": "Tofaş", "ARCLK": "Arçelik", "XHOLD": "BIST Holding"}
YAHOO = {"NASDAQ": "^IXIC", "SP500": "^GSPC", "XU100": "XU100.IS", "XBANK": "XBANK.IS", "XHOLD": "XHOLD.IS", "USDTRY": "TRY=X", "ALTIN": "GC=F", "BRENT": "BZ=F", "GUMUS": "SI=F"}

def ysem(kod):
    if kod.endswith(".US"): return kod[:-3].replace(".", "-")
    return YAHOO.get(kod, kod + ".IS")


def vad(kod):
    if kod.endswith(".US"):
        import bist_abd as AB
        return f"{kod[:-3]} ({AB.ad(kod)})"
    return VARLIK_AD.get(kod, kod)


# ---------------------------------------------------------------------------------- sorgular
SORGULAR = [
    ("makro_tr", "Merkez Bankası faiz kararı"), ("makro_tr", "TCMB faiz"), ("makro_tr", "TÜİK enflasyon açıklandı"),
    ("makro_tr", "dolar TL kur rekor"), ("makro_tr", "Türkiye kredi notu"), ("makro_tr", "Borsa İstanbul günü"),
    ("makro_global", "Fed faiz kararı"), ("makro_global", "ABD enflasyon verisi"), ("makro_global", "ABD tarım dışı istihdam"),
    ("emtia", "petrol fiyatları OPEC"), ("emtia", "altın fiyatları ons rekor"),
    ("jeopolitik", "savaş saldırı piyasalar"), ("jeopolitik", "ateşkes anlaşması"),
    ("kripto", "Bitcoin ETF"), ("kripto", "kripto borsa hack"), ("kripto", "SEC kripto"), ("kripto", "Bitcoin rezerv"),
    ("sirket", "KAP bildirimi sipariş"), ("sirket", "KAP bedelsiz sermaye artırımı"), ("sirket", "KAP temettü kararı"),
    ("sirket", "KAP pay geri alım"), ("sirket", "SPK ceza işlem yasağı"), ("sirket", "KAP yeni iş ilişkisi"),
    ("abd", "bilanço beklentileri aştı hisse"), ("abd", "bilanço beklentilerin altında hisse"), ("abd", "Nvidia bilanço"),
    ("abd", "Wall Street hisse sert düştü"), ("abd", "Wall Street hisse rekor yükseldi"),
]
ABD_AD = {"nvidia": "NVDA.US", "apple": "AAPL.US", "microsoft": "MSFT.US", "amazon": "AMZN.US", "alphabet": "GOOGL.US", "google": "GOOGL.US",
          "meta": "META.US", "facebook": "META.US", "tesla": "TSLA.US", "broadcom": "AVGO.US", "netflix": "NFLX.US", "amd": "AMD.US",
          "palantir": "PLTR.US", "coinbase": "COIN.US", "microstrategy": "MSTR.US", "oracle": "ORCL.US", "jpmorgan": "JPM.US",
          "berkshire": "BRK.B.US", "intel": "INTC.US", "salesforce": "CRM.US", "walmart": "WMT.US", "boeing": "BA.US",
          "eli lilly": "LLY.US", "tsmc": "TSM.US", "micron": "MU.US", "adobe": "ADBE.US", "qualcomm": "QCOM.US"}


def abd_sinifla(baslik):
    b = kk(baslik)
    hisseler = list(dict.fromkeys(k for ad, k in ABD_AD.items() if re.search(rf"(^|\W){re.escape(ad)}", b)))[:2]
    if not hisseler: return None
    if var(b, "beklentileri aştı", "beklentilerin üzerinde", "rekor gelir", "rekor kâr", "güçlü bilanço", "tahminleri aştı", "yükseltti", "sert yükseldi", "rekor kırdı"):
        y = 1
    elif var(b, "beklentilerin altında", "hayal kırıklığı", "tahminlerin altında", "zayıf bilanço", "sert düştü", "çakıldı", "düşürdü", "soruşturma", "dava"):
        y = -1
    else:
        return None
    bil = var(b, "bilanço", "gelir", "kâr", "kar ", "çeyrek")
    gerekce = ("bilanço beklentileri aştı; kazanç tahminleri yukarı revize edilebilir" if y > 0 else "bilanço beklentilerin altında; tahminler aşağı revize edilebilir") if bil \
        else ("hisseye yönelik olumlu gelişme" if y > 0 else "hisseye yönelik olumsuz gelişme")
    etki = [(h, y, gerekce) for h in hisseler]
    etki.append(("NASDAQ", y, "endeksteki ağırlığı yüksek dev şirket; endeksi aynı yönde etkiler"))
    return {"tur": "ABD şirket haberi" if not bil else "ABD bilançosu", "yon": y, "etki": etki, "onem": 2}

# ---------------------------------------------------------------------------------- sınıflandırma kuralları
# Her kural: (ad, koşul(b) -> bool, yön(b) -> +1/-1/0, etki listesi [(varlık, işaret, gerekçe)], önem 1-3)
def _yon_faiz(b):
    if var(b, "indir", "düşür", "indirim"): return 1        # gevşeme
    if var(b, "artır", "yükselt", "artış"): return -1        # sıkılaşma
    return 0


def _yon_enf(b):
    if var(b, "beklentinin altında", "beklentilerin altında", "geriledi", "düştü", "yavaşladı"): return 1
    if var(b, "beklentinin üzerinde", "beklentilerin üzerinde", "beklentileri aştı", "hızlandı", "yükseldi", "arttı"): return -1
    return 0


KURALLAR = [
    # (ad, koşul, yön, [(varlık, işaret, (olumlu durumda gerekçe, olumsuz durumda gerekçe))], önem)
    ("TCMB faiz kararı",
     lambda b: var(b, "merkez bankası", "tcmb", "ppk") and var(b, "politika faiz", "faiz kararı", "faizi yüzde", "faizi %", "faizleri yüzde", "ppk", "faiz indirim", "faiz artır")
               and not var(b, "fed", "avrupa merkez", "ecb", "japonya", "kredi kartı", "mevduat", "konut kredisi", "zorunlu karşılık"),
     _yon_faiz,
     [("XU100", 1, ("faiz indirimi hisselerin iskontosunu düşürür, mevduattan borsaya geçişi destekler", "faiz artışı mevduatı cazip kılar, hisse değerlemelerini baskılar")),
      ("XBANK", 1, ("bankalarda fonlama maliyeti düşer, tahvil portföyü değer kazanır", "fonlama maliyeti artar, tahvil portföyünde değer kaybı")),
      ("USDTRY", 1, ("düşük faiz TL'nin getiri avantajını azaltır, kur yukarı baskılanır", "yüksek faiz TL'yi cazip kılar, kur baskısı azalır")),
      ("GRAMALTIN", 1, ("TL faizinin düşmesi ve kur artışı gram altını destekler", "TL'nin güçlenmesi gram altını baskılar"))], 3),
    ("Fed faiz kararı", lambda b: var(b, "fed ", "fed'", "fed,", "federal reserve", "powell") and "faiz" in b,
     _yon_faiz,
     [("ALTIN", 1, ("düşen dolar faizi altının fırsat maliyetini azaltır", "yükselen dolar faizi altının fırsat maliyetini artırır")),
      ("BTC/USDT", 1, ("gevşek para politikası risk iştahını ve likiditeyi artırır", "sıkı para politikası likiditeyi daraltır")),
      ("XU100", 1, ("gelişmekte olan piyasalara sermaye girişi beklentisi", "gelişmekte olan piyasalardan sermaye çıkışı riski")),
      ("USDTRY", -1, ("küresel dolar zayıflığı kur baskısını hafifletir", "küresel dolar güçlenmesi kuru yukarı iter"))], 3),
    ("Türkiye enflasyon verisi", lambda b: var(b, "tüik", "türkiye'de enflasyon", "yıllık enflasyon", "aylık enflasyon") and "enflasyon" in b and not var(b, "abd", "amerika", "euro bölgesi"),
     _yon_enf,
     [("XU100", 1, ("düşük enflasyon faiz indirimi beklentisini güçlendirir", "yüksek enflasyon faiz indirimlerini geciktirebilir")),
      ("XBANK", 1, ("faiz indirimi beklentisi bankalara olumlu", "sıkı para politikasının uzaması bankaları baskılar")),
      ("USDTRY", -1, ("dezenflasyon TL varlıklarına güveni artırır", "yüksek enflasyon TL'nin reel değerini aşındırır"))], 3),
    ("ABD enflasyon verisi", lambda b: var(b, "abd", "amerika") and var(b, "enflasyon", "tüfe", "cpi", "pce"),
     _yon_enf,
     [("ALTIN", 1, ("düşük enflasyon Fed'in faiz indirme olasılığını artırır", "yüksek enflasyon Fed'i sıkı tutar, altını baskılar")),
      ("BTC/USDT", 1, ("faiz indirimi beklentisi riskli varlıkları destekler", "sıkı Fed beklentisi riskli varlıkları baskılar")),
      ("XU100", 1, ("küresel risk iştahı artar", "küresel risk iştahı azalır"))], 3),
    ("ABD istihdam verisi", lambda b: var(b, "tarım dışı", "istihdam") and var(b, "abd", "amerika"),
     lambda b: 1 if var(b, "beklentinin altında", "zayıf", "geriledi", "azaldı") else -1 if var(b, "beklentinin üzerinde", "güçlü", "arttı") else 0,
     [("ALTIN", 1, ("zayıf istihdam faiz indirimi beklentisini artırır, doları zayıflatır", "güçlü istihdam faiz indirimlerini geciktirir")),
      ("BTC/USDT", 1, ("gevşeme beklentisi riskli varlıklara olumlu", "sıkı para beklentisi riskli varlıklara olumsuz"))], 2),
    ("Kredi notu", lambda b: var(b, "kredi notu", "not görünümü") and var(b, "türkiye", "moody", "fitch", "s&p"),
     lambda b: 1 if var(b, "yükseltti", "pozitif", "artırdı", "yükseldi") else -1 if var(b, "düşürdü", "negatif", "indirdi") else 0,
     [("XU100", 1, ("not artışı yabancı girişini ve risk primi düşüşünü destekler", "not indirimi yabancı çıkışı ve risk primi artışı getirir")),
      ("XBANK", 1, ("bankaların dış borçlanma maliyeti düşer", "bankaların dış borçlanma maliyeti artar")),
      ("USDTRY", -1, ("ülke risk priminin düşmesi TL'yi destekler", "ülke risk priminin artması TL'yi baskılar"))], 3),
    ("Petrol arz / fiyat gelişmesi", lambda b: var(b, "petrol", "brent", "opec"),
     lambda b: 1 if var(b, "kesinti", "yükseldi", "sert yükseliş", "arz endişe", "üretimi azalt") else -1 if var(b, "düştü", "geriledi", "üretimi artır", "arz fazlası") else 0,
     [("BRENT", 1, ("arz daralması / fiyat artışı", "arz artışı / fiyat düşüşü")),
      ("TUPRS", 1, ("rafineri marjları ve stok kazancı artar", "stok zararı ve marj baskısı")),
      ("THYAO", -1, ("yakıt maliyeti artar", "yakıt maliyeti düşer")),
      ("PGSUS", -1, ("yakıt maliyeti kârlılığı baskılar", "yakıt maliyeti kârlılığı destekler")),
      ("USDTRY", 1, ("enerji ithalatçısı Türkiye'nin cari açığı büyür", "enerji faturası ve cari açık hafifler"))], 2),
    ("Jeopolitik gelişme", lambda b: var(b, "savaş", "saldırı", "füze", "çatışma", "işgal", "bombal", "gerilim tırman", "ateşkes", "barış anlaşması") and not var(b, "kripto", "borsası saldır", "siber"),
     # Can kaybı / ihlal haberleri "olumlu" sayılamaz; yeni bir tırmanma yoksa piyasa etkisi zayıf kabul edilip gönderilmez.
     lambda b: (0 if var(b, "ihlal", "öldür", "hayatını kaybet", "can kaybı", "yaralan", "katliam", "sivil") and not var(b, "savaş ilan", "füze", "işgal", "tırman", "hava saldırısı başlat", "kapsamlı saldırı")
                else 1 if var(b, "ateşkes", "barış", "anlaşma sağlandı", "gerilim azal") else -1),
     [("ALTIN", -1, ("güvenli liman talebi azalır", "güvenli liman talebi artar")),
      ("BRENT", -1, ("arz kesintisi risk primi azalır", "arz kesintisi risk primi artar")),
      ("XU100", 1, ("risk iştahı geri döner", "riskten kaçış, yabancı satışı")),
      ("BTC/USDT", 1, ("risk iştahı geri döner", "riskli varlıklardan kaçış"))], 3),
    ("Kripto ETF / kurumsal akış", lambda b: var(b, "etf", "rezerv", "kurumsal alım", "microstrategy", "blackrock") and var(b, "bitcoin", "kripto", "ethereum", "btc", "eth"),
     lambda b: -1 if var(b, "reddetti", "reddedildi", "çıkış", "çıktı", "satış", "sattı", "erteledi", "düştü", "geriledi", "kaçış") else
               1 if var(b, "giriş", "onay", "aldı", "alım", "rekor talep", "yükseldi") else 0,
     [("BTC/USDT", 1, ("kurumsal talep ve fon girişi", "fon çıkışı ve kurumsal satış baskısı")),
      ("ETH/USDT", 1, ("piyasa geneline yayılan talep", "piyasa geneline yayılan satış baskısı"))], 2),
    ("Kripto güvenlik / düzenleme riski", lambda b: var(b, "hack", "saldırıya uğra", "çalındı", "sec dava", "yasakla", "soruşturma", "iflas") and var(b, "kripto", "bitcoin", "borsa", "coin", "token", "ethereum", "binance"),
     lambda b: -1,
     [("BTC/USDT", 1, ("", "güven kaybı ve olası zorunlu satışlar")), ("ETH/USDT", 1, ("", "piyasa geneline yayılan risk algısı"))], 2),
    ("Dolar/TL hareketi", lambda b: var(b, "dolar/tl", "dolar kuru", "dolar/türk", "usd/try", "türk lirası", "dolar tl", "dolar rekor") and var(b, "rekor", "sert", "yükseldi", "geriledi", "düştü", "değer kaybı", "değer kazan"),
     lambda b: -1 if var(b, "rekor", "yükseldi", "sert yükseliş", "değer kaybı") else 1 if var(b, "geriledi", "düştü", "değer kazan") else 0,
     [("USDTRY", -1, ("TL değer kazanıyor, kur geriliyor", "TL değer kaybediyor, kur yükseliyor")),
      ("GRAMALTIN", -1, ("kurun gerilemesi gram altını baskılar", "kur artışı gram altını doğrudan yükseltir")),
      ("FROTO", -1, ("güçlü TL ihracatçıların TL gelirini azaltır", "ihracatçılar kur artışından gelir tarafında fayda görür")),
      ("XBANK", 1, ("kur istikrarı bankalarda risk algısını azaltır", "kur oynaklığı bankalarda risk algısını artırır"))], 2),
]


GRUP_KURAL = {"makro_tr": ("TCMB faiz kararı", "Türkiye enflasyon verisi", "Kredi notu", "Dolar/TL hareketi", "Fed faiz kararı"),
              "makro_global": ("Fed faiz kararı", "ABD enflasyon verisi", "ABD istihdam verisi"),
              "emtia": ("Petrol arz / fiyat gelişmesi", "Jeopolitik gelişme"),
              "jeopolitik": ("Jeopolitik gelişme", "Petrol arz / fiyat gelişmesi"),
              "kripto": ("Kripto güvenlik / düzenleme riski", "Kripto ETF / kurumsal akış", "Fed faiz kararı")}


def sinifla(baslik, grup=None):
    b = kk(baslik)
    izin = GRUP_KURAL.get(grup)
    kurallar = sorted((k for k in KURALLAR if not izin or k[0] in izin), key=lambda k: izin.index(k[0]) if izin else 0)
    for ad, kosul, yon_fn, etki, onem in kurallar:
        try:
            if kosul(b):
                y = yon_fn(b)
                if y == 0: return None
                return {"tur": ad, "yon": y, "etki": [(v, y * s_, (g[0] if y > 0 else g[1]) if isinstance(g, tuple) else g) for v, s_, g in etki], "onem": onem}
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------------- şirket haberleri
_STOP = {"yeni", "büyük", "ilk", "mega", "birleşik", "türk", "türkiye", "anadolu", "yapı", "global", "doğu", "ege", "marmara", "akdeniz", "petrol", "enerji", "gıda", "turizm",
         "yatırım", "holding", "sanayi", "tekstil", "kimya", "çimento", "metal", "kağıt", "faktoring", "finans", "sigorta", "gayrimenkul"}


def sirket_sozlugu():
    try:
        df = pd.read_csv("hisse_listesi.csv", dtype=str)
    except Exception:
        return []
    out = []
    for _, r in df.iterrows():
        k = [kk(w).strip(".,'’") for w in str(r.get("Ad") or "").split()]
        if not k: out.append((r["Kod"], "", None)); continue
        # ayırt edici ad: tek kelime yeterince özgünse o, değilse ilk iki kelime ("koza altın", "türk hava")
        anahtar = k[0] if len(k[0]) >= 6 and k[0] not in _STOP else (" ".join(k[:2]) if len(k) > 1 and len(" ".join(k[:2])) >= 7 else None)
        out.append((r["Kod"], r.get("Ad"), anahtar))
    return out


def sirket_bul(baslik, sozluk):
    b = kk(baslik); bulunan = []
    for kod, ad, ilk in sozluk:
        if re.search(rf"\b{kod}\b", baslik) or (ilk and re.search(rf"(^|\W){re.escape(ilk)}", b)):
            bulunan.append((kod, ad))
    return bulunan[:2]


def sirket_sinifla(baslik, sozluk):
    import bist_borsa as BB
    konu, yon = BB.kap_siniflandir(baslik)
    if not konu or yon == 0: return None
    s = sirket_bul(baslik, sozluk)
    if not s: return None
    gerekce = {"Bedelsiz sermaye artırımı": "bedelsiz kararı genellikle kısa vadeli talep yaratır",
               "Bedelli sermaye artırımı": "bedelli artırım pay sulanması ve nakit ihtiyacı sinyali",
               "Temettü / kâr payı": "nakit getiri ve güçlü bilanço sinyali",
               "Pay geri alımı": "şirketin kendi hissesini ucuz bulduğu sinyali, talep desteği",
               "Yeni iş / sipariş / sözleşme": "gelir görünürlüğünü artırır; etki, tutarın şirket büyüklüğüne oranına bağlı",
               "Yatırım / kapasite": "orta vadeli büyüme beklentisi",
               "Ceza / dava / soruşturma": "belirsizlik ve olası nakit çıkışı"}.get(konu, konu)
    return {"tur": f"Şirket: {konu}", "yon": yon, "etki": [(k, yon, gerekce) for k, _ in s], "onem": 2 if konu != "Yeni iş / sipariş / sözleşme" else 1}


# ---------------------------------------------------------------------------------- fiyat tepkisi
_FIYAT = {}


def saatlik(kod):
    if kod in _FIYAT: return _FIYAT[kod]
    h = None
    try:
        if "/" in kod:
            import bist_kripto as KR
            h = KR.saatlik_mumlar(kod.split("/")[0], "USDT", "Binance", bar=200)[0]
            h.index = h.index.tz_localize(UTC)
        else:
            import yfinance as yf
            if kod == "GRAMALTIN":
                g = yf.Ticker("GC=F").history(period="5d", interval="60m"); f = yf.Ticker("TRY=X").history(period="5d", interval="60m")
                f = f["Close"].reindex(g.index, method="ffill")
                h = g[["Open", "High", "Low", "Close"]].mul(f, axis=0) / 31.1035; h["Volume"] = 0.0
            else:
                h = yf.Ticker(ysem(kod)).history(period="5d", interval="60m")
            h.index = h.index.tz_convert(UTC)
            h = h[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
    except Exception as ex:
        print("fiyat alınamadı:", kod, ex, file=sys.stderr); h = None
    _FIYAT[kod] = h
    return h


def tepki(kod, t0):
    """Haber zamanından bu yana değişim ve hacim oranı. (değişim, hacim_k, fiyat_t0, fiyat_son)"""
    h = saatlik(kod)
    if h is None or len(h) < 5: return None
    sure = pd.Series(h.index[-30:]).diff().median()
    sure = sure if pd.notna(sure) and sure <= pd.Timedelta(hours=4) else pd.Timedelta(hours=1)
    once = h[h.index + sure <= t0]            # haberden ÖNCE kapanmış son mum (tepkinin tamamı ölçülsün)
    if not len(once): return None
    p0 = float(once["Close"].iloc[-1]); p1 = float(h["Close"].iloc[-1])
    sonra = h[h.index + sure > t0]
    vk = None
    if len(sonra) and h["Volume"].sum() > 0:
        ort = float(once["Volume"].iloc[-48:].mean() or 0)
        if ort > 0: vk = float(sonra["Volume"].mean()) / ort
    oyn = float(h["Close"].pct_change().iloc[-48:].std() or 0)
    return {"degisim": p1 / p0 - 1, "hacim_k": vk, "p0": p0, "p1": p1, "oyn": oyn, "saat": len(sonra)}


_TEK = {}


def teknik_ozet(kod):
    """Güncel fiyat üzerinden canlı teknik özet: fiyat, günlük teknik görünüm, en yakın destek ve direnç."""
    if kod in _TEK: return _TEK[kod]
    o = None
    try:
        import bist_teknik as T
        k = {"USDTRY": "USDTRY", "NASDAQ": "NASDAQ", "SP500": "SP500"}.get(kod, kod)
        s_ = T.analiz(k, tfler=("G",)); g = s_["tf"]["G"]
        o = {"fiyat": g["fiyat"], "etiket": g["etiket"], "puan": g["puan"],
             "destek": g["sr"]["destek"][0][0] if g["sr"]["destek"] else None,
             "direnc": g["sr"]["direnc"][0][0] if g["sr"]["direnc"] else None}
    except Exception as ex:
        print("teknik özet alınamadı:", kod, ex, file=sys.stderr)
    _TEK[kod] = o
    return o


# ---------------------------------------------------------------------------------- olay çalışması (zamanla biriken)
def olaylari_guncelle(olaylar):
    """Kaydedilmiş haberlerin 1 ve 5 gün sonraki getirilerini doldurur."""
    simdi = dt.datetime.now(UTC)
    for o in olaylar:
        t0 = dt.datetime.fromisoformat(o["zaman"])
        for v in o["varliklar"]:
            for gun, alan in ((1, "g1"), (5, "g5")):
                if v.get(alan) is not None or simdi - t0 < dt.timedelta(days=gun) or v.get("p0") is None: continue
                try:
                    h = gunluk(v["kod"])
                    hedef = t0 + dt.timedelta(days=gun)
                    s = h[h.index <= hedef]
                    if len(s): v[alan] = float(s["Close"].iloc[-1]) / v["p0"] - 1
                except Exception:
                    pass
    return [o for o in olaylar if simdi - dt.datetime.fromisoformat(o["zaman"]) < dt.timedelta(days=400)]


_GUN = {}


def gunluk(kod):
    if kod in _GUN: return _GUN[kod]
    if "/" in kod:
        import bist_kripto as KR
        h = KR.saatlik_mumlar(kod.split("/")[0], "USDT", "Binance", bar=1000)[0]; h.index = h.index.tz_localize(UTC)
    else:
        import yfinance as yf
        h = yf.Ticker(ysem(kod) if kod != "GRAMALTIN" else "GC=F").history(period="60d", interval="60m")
        h.index = h.index.tz_convert(UTC)
    _GUN[kod] = h
    return h


def gecmis_istatistik(olaylar, tur, kod, yon):
    x = [v for o in olaylar if o["tur"] == tur and o["yon"] == yon for v in o["varliklar"] if v["kod"] == kod and v.get("g1") is not None]
    if len(x) < 3: return None
    g1 = np.array([v["g1"] for v in x]); g5 = np.array([v["g5"] for v in x if v.get("g5") is not None])
    return {"n": len(x), "g1": float(g1.mean()), "pozitif": float((g1 > 0).mean()), "g5": float(g5.mean()) if len(g5) >= 3 else None}


# ---------------------------------------------------------------------------------- takvim
def takvim(hafta="thisweek"):
    import requests
    j = requests.get(f"https://nfs.faireconomy.media/ff_calendar_{hafta}.json", headers={"User-Agent": "Mozilla/5.0"}, timeout=20).json()
    out = []
    for e in j:
        if e.get("impact") != "High" or e.get("country") not in ("USD", "EUR", "CNY", "GBP", "JPY"): continue
        try: t = dt.datetime.fromisoformat(e["date"]).astimezone(TSI)
        except Exception: continue
        out.append({"zaman": t.isoformat(), "baslik": e.get("title"), "ulke": e.get("country"),
                    "beklenti": e.get("forecast") or "", "onceki": e.get("previous") or ""})
    return out


TEPKI_VARLIK = {"Altın": "GC=F", "S&P 500 vadeli": "ES=F", "Bitcoin": "BTC/USDT", "Dolar/TL": "TRY=X"}


def _tepki_olc(sembol, t0):
    """Veri açıklanmadan önceki son fiyata göre 1 saat ve 1 gün sonraki değişim."""
    if "/" in sembol:
        import bist_kripto as KR
        h = KR.saatlik_mumlar(sembol.split("/")[0], "USDT", "Binance", bar=1000)[0]; h.index = h.index.tz_localize(UTC)
    else:
        import yfinance as yf
        h = yf.Ticker(sembol).history(period="60d", interval="60m"); h.index = h.index.tz_convert(UTC)
    c = h["Close"].dropna()
    once = c[c.index < t0]
    if not len(once): return None
    p0 = float(once.iloc[-1]); o = {}
    for ad, dlt in (("1s", dt.timedelta(hours=1)), ("1g", dt.timedelta(days=1))):
        s_ = c[(c.index >= t0) & (c.index <= t0 + dlt)]
        if len(s_) and dt.datetime.now(UTC) >= t0 + dlt: o[ad] = float(s_.iloc[-1]) / p0 - 1
    return o or None


def takvim_arsivi(arsiv, liste):
    """Geçmiş veri açıklamalarının piyasa tepkisini ölçer ve biriktirir."""
    simdi = dt.datetime.now(UTC); anahtar = {(a["zaman"], a["baslik"]) for a in arsiv}
    for e in liste:
        if (e["zaman"], e["baslik"]) not in anahtar and dt.datetime.fromisoformat(e["zaman"]) < simdi:
            arsiv.append({**e, "tepki": {}}); anahtar.add((e["zaman"], e["baslik"]))
    olcum = 0
    for a in arsiv:
        if olcum >= 12: break
        t0 = dt.datetime.fromisoformat(a["zaman"]).astimezone(UTC)
        if simdi - t0 < dt.timedelta(hours=1) or simdi - t0 > dt.timedelta(days=55): continue
        if all(len(a["tepki"].get(v, {})) == 2 for v in TEPKI_VARLIK): continue
        for v, sem in TEPKI_VARLIK.items():
            if len(a["tepki"].get(v, {})) == 2: continue
            try:
                r = _tepki_olc(sem, t0)
                if r: a["tepki"][v] = r
            except Exception:
                pass
        olcum += 1
    return [a for a in arsiv if simdi - dt.datetime.fromisoformat(a["zaman"]).astimezone(UTC) < dt.timedelta(days=800)]


def tepki_ozeti(arsiv, baslik, ulke):
    """Aynı verinin geçmiş açıklamalarında varlık başına ortalama mutlak 1 saatlik hareket."""
    x = [a for a in arsiv if a["baslik"] == baslik and a["ulke"] == ulke and a.get("tepki")]
    out = {}
    for v in TEPKI_VARLIK:
        d = [a["tepki"][v]["1s"] for a in x if v in a["tepki"] and "1s" in a["tepki"][v]]
        if d: out[v] = {"n": len(d), "ort_mutlak": float(np.mean(np.abs(d))), "yukari": float(np.mean(np.array(d) > 0))}
    return out


ULKE_AD = {"USD": "ABD", "EUR": "Euro Bölgesi", "CNY": "Çin", "GBP": "İngiltere", "JPY": "Japonya"}


ETKI = {"USD": "altın, Bitcoin, Nasdaq ve BIST", "EUR": "EUR/TRY, altın ve Avrupa borsaları", "CNY": "emtia (bakır, petrol) ve risk iştahı",
        "GBP": "sterlin ve küresel risk iştahı", "JPY": "yen ve küresel risk iştahı"}


def takvim_karti_gonder(b, liste, bugun, metin, arsiv=None):
    try:
        import kart as K
        gun = [e for e in liste if dt.datetime.fromisoformat(e["zaman"]).date() == bugun]
        bol = {}
        for e in gun:
            t = dt.datetime.fromisoformat(e["zaman"])
            alt = " · ".join(x for x in (f"önceki {e['onceki']}" if e.get("onceki") else "", f"etkilenir: {ETKI.get(e['ulke'], 'küresel piyasalar')}") if x)
            to = tepki_ozeti(arsiv or [], e["baslik"], e["ulke"])
            if to:
                alt += " · geçmişte 1 saatte ort. " + ", ".join(f"{v.lower()} ±%{x['ort_mutlak'] * 100:.1f}".replace(".", ",") for v, x in list(to.items())[:3])
            bol.setdefault(ULKE_AD.get(e["ulke"], e["ulke"]), []).append(
                {"sol": f"{t:%H:%M}  ·  {e['baslik']}", "sag": f"beklenti {e['beklenti']}" if e.get("beklenti") else "", "sag_renk": K.C["altin"],
                 "nokta": K.C["altin"], "alt": alt})
        yol = os.path.join(CIKTI, "haber", "takvim.png"); os.makedirs(os.path.dirname(yol), exist_ok=True)
        K.bildirim_karti(f"EKONOMİK TAKVİM  ·  {bugun:%d.%m.%Y}", f"Bugün {len(gun)} önemli veri", "Saatler Türkiye saatiyle",
                         [{"baslik": u, "renk": K.C["mavi"], "satirlar": v} for u, v in bol.items()], yol, vurgu=K.C["mavi"],
                         not_="Beklentiden güçlü ABD verisi: dolar ve faiz beklentisi yukarı, altın ve kripto üzerinde baskı. Zayıf veri: tersi. "
                              "Açıklama anlarında oynaklık artar; stoplar sık tetiklenebilir.")
        b.sil_anahtar("takvim")
        alt = "🗓 <b>BUGÜNÜN ÖNEMLİ VERİLERİ</b>\n" + "\n".join(f"{dt.datetime.fromisoformat(e['zaman']):%H:%M} · {esc(ULKE_AD.get(e['ulke'], e['ulke']))} – {esc(e['baslik'])}" for e in gun[:10])
        return bool(b.foto(yol, alt[:1000], "takvim", 20))
    except Exception as ex:
        print("Takvim kartı çizilemedi:", ex, file=sys.stderr); return False


def takvim_mesaji(liste, bugun):
    gun = [e for e in liste if dt.datetime.fromisoformat(e["zaman"]).date() == bugun]
    if not gun: return None
    import tg as _tg
    s = [f"🗓 <b>BUGÜNÜN ÖNEMLİ VERİLERİ</b> · {bugun:%d.%m.%Y}", _tg.AYRAC]
    for e in gun:
        t = dt.datetime.fromisoformat(e["zaman"])
        ek = " · ".join(x for x in (f"beklenti {e['beklenti']}" if e["beklenti"] else "", f"önceki {e['onceki']}" if e["onceki"] else "") if x)
        s.append(f"🕐 <b>{t:%H:%M}</b> · {ULKE_AD.get(e['ulke'], e['ulke'])} – {esc(e['baslik'])}" + (f"\n      <i>{esc(ek)}</i>" if ek else ""))
    s.append("\n<blockquote>ABD verileri özellikle altın, Bitcoin ve BIST'i etkiler: beklentiden güçlü veri → dolar ve faiz beklentisi yukarı, "
             "altın/kripto üzerinde baskı; zayıf veri → tersi. Açıklama saatlerinde oynaklık artar, stoplar sık tetiklenebilir.</blockquote>")
    return "\n".join(s)


# ---------------------------------------------------------------------------------- ana akış
def oku(yol, vars_):
    try: return json.load(open(yol, encoding="utf-8"))
    except Exception: return vars_


def calistir():
    import bist_rapor as br
    kok_eski = os.path.join(KLON, "haber"); kok = os.path.join(CIKTI, "haber"); os.makedirs(kok, exist_ok=True)
    gorulen = oku(os.path.join(kok_eski, "gorulen.json"), {})
    son = oku(os.path.join(kok_eski, "son.json"), [])
    # kurallar sıkılaştıkça eski hatalı sınıflamaları listeden düş
    son = [a for a in son if a["tur"].startswith(("Şirket", "ABD")) or (sinifla(a["baslik"]) or {}).get("tur") == a["tur"]]
    olaylar = oku(os.path.join(kok_eski, "olaylar.json"), [])
    tk = oku(os.path.join(kok_eski, "takvim.json"), {})
    simdi = dt.datetime.now(UTC)
    sozluk = sirket_sozlugu()
    aday = []
    for grup, q in SORGULAR:
        try: liste = br.haber_cek(None, None, adet=15, gun=1, sorgu=q + " when:1d")["liste"]
        except Exception as ex:
            print("sorgu başarısız:", q, ex, file=sys.stderr); continue
        for x in liste:
            if not x["tarih"] or simdi - x["tarih"] > dt.timedelta(hours=PENCERE_SAAT): continue
            anahtar = hashlib.md5(kk(re.sub(r"\W+", " ", x["baslik"]))[:90].encode()).hexdigest()[:16]
            if anahtar in gorulen: continue
            gorulen[anahtar] = simdi.isoformat()
            s = sirket_sinifla(x["baslik"], sozluk) if grup == "sirket" else abd_sinifla(x["baslik"]) if grup == "abd" else sinifla(x["baslik"], grup)
            if s: aday.append({**x, **s, "anahtar": anahtar})
        time.sleep(0.5)
    # aynı tür + aynı yön + aynı varlıklar: tek olay, kaynak sayısı artar
    birlesik = {}
    for x in sorted(aday, key=lambda x: x["tarih"]):
        k = (x["tur"], x["yon"], tuple(sorted(v for v, _, _ in x["etki"])))
        if k in birlesik: birlesik[k]["kaynak_sayi"] += 1
        else: birlesik[k] = {**x, "kaynak_sayi": 1}
    # son 6 saatte aynı tür/yön zaten gönderildiyse tekrar etme
    yakin = {(o["tur"], o["yon"]) for o in son if simdi - dt.datetime.fromisoformat(o["zaman"]) < dt.timedelta(hours=6)}
    olaylar_yeni = [x for k, x in birlesik.items() if (x["tur"], x["yon"]) not in yakin or x["tur"].startswith(("Şirket", "ABD"))]
    olaylar_yeni.sort(key=lambda x: (-x["onem"], -x["kaynak_sayi"]))
    analizler = []
    for x in olaylar_yeni[:MAKS_MESAJ]:
        t0 = x["tarih"]; v_ = []
        for kod, isaret, gerekce in x["etki"]:
            r = tepki(kod, t0); te = teknik_ozet(kod)
            v_.append({"kod": kod, "isaret": isaret, "gerekce": gerekce, "tepki": r, "teknik": te,
                       "gecmis": gecmis_istatistik(olaylar, x["tur"], kod, x["yon"]),
                       "p0": r["p0"] if r else None})
        analizler.append({"zaman": t0.isoformat(), "baslik": x["baslik"], "kaynak": x.get("kaynak"), "link": x.get("link"),
                          "tur": x["tur"], "yon": x["yon"], "onem": x["onem"], "kaynak_sayi": x["kaynak_sayi"], "varliklar": v_})
    # Telegram
    import tg
    b = tg.Bot("alarm")
    if analizler:
        import tg as _tg
        if not haber_karti_gonder(b, analizler, simdi):
          b.mesaj(f"📰 <b>HABER ETKİSİ</b> · {simdi.astimezone(TSI):%d.%m %H:%M}\n{_tg.AYRAC}\n" + "\n\n".join(mesaj(a) for a in analizler),
                f"haber:{simdi:%Y%m%d%H%M}", 12, yerine=False)
    # takvim (günde bir, 07:00 TSİ sonrası ilk turda)
    bugun = simdi.astimezone(TSI).date()
    arsiv = oku(os.path.join(kok_eski, "takvim_arsiv.json"), []) or []
    try:
        if not arsiv:
            arsiv = takvim_arsivi(arsiv, takvim("lastweek"))
        arsiv = takvim_arsivi(arsiv, tk.get("liste", []))
    except Exception as ex:
        print("takvim arşivi:", ex, file=sys.stderr)
    json.dump(arsiv, open(os.path.join(kok, "takvim_arsiv.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0, default=str)
    if simdi.astimezone(TSI).hour >= 7 and tk.get("gonderildi") != str(bugun):
        try:
            liste = takvim(); tk = {"liste": liste, "gonderildi": str(bugun)}
            m = takvim_mesaji(liste, bugun)
            if m and not takvim_karti_gonder(b, liste, bugun, m, arsiv): b.mesaj(m, "takvim", 20, yerine=True)
        except Exception as ex:
            print("takvim alınamadı:", ex, file=sys.stderr)
    b.kaydet()
    # olay çalışması ve kayıtlar
    for a in analizler:
        olaylar.append({"zaman": a["zaman"], "tur": a["tur"], "yon": a["yon"],
                        "varliklar": [{"kod": v["kod"], "p0": v["p0"]} for v in a["varliklar"] if v["p0"]]})
    try: olaylar = olaylari_guncelle(olaylar)
    except Exception as ex: print("olay güncellemesi:", ex, file=sys.stderr)
    son = (analizler + son)[:150]
    gorulen = {k: v for k, v in gorulen.items() if simdi - dt.datetime.fromisoformat(v) < dt.timedelta(days=3)}
    for ad, veri in (("gorulen", gorulen), ("son", son), ("olaylar", olaylar), ("takvim", tk)):
        json.dump(veri, open(os.path.join(kok, ad + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0, default=str)
    print(f"Haber: {len(aday)} sınıflanan başlık, {len(analizler)} analiz gönderildi.")


def kart_bolumu(a):
    """Bir haber analizini görsel kart bölümüne çevirir."""
    import kart as K, firsat as F
    C = K.C; pf = _pf(); t = dt.datetime.fromisoformat(a["zaman"]).astimezone(TSI)
    sat = []
    for v in a["varliklar"]:
        yuk = v["isaret"] > 0
        alt = [v["gerekce"][:1].upper() + v["gerekce"][1:] + "."]
        r = v.get("tepki")
        if r and r["saat"] >= 1:
            yonlu = r["degisim"] * v["isaret"]; esik = max(r["oyn"] * 1.5, 0.002)
            alt.append(f"Haberden beri {yz(r['degisim'])} → " + ("fiyatlandı" if yonlu > esik else "ters yönde" if yonlu < -esik else "henüz tepki yok"))
        te = v.get("teknik")
        if te and te.get("fiyat"):
            p = te["fiyat"]; e = f"Fiyat {F.fy(p)} · teknik {te['etiket']} ({float(te['puan']):.0f})"
            if te.get("destek"): e += f" · destek {F.fy(te['destek'])} ({yz(te['destek'] / p - 1)})"
            if te.get("direnc"): e += f" · direnç {F.fy(te['direnc'])} ({yz(te['direnc'] / p - 1)})"
            alt.append(e)
        sat.append({"sol": ("Portföy · " if _pfk(v["kod"]) in pf else "") + vad(v["kod"]), "sag": "↑ yükseliş" if yuk else "↓ düşüş",
                    "sag_renk": C["yesil"] if yuk else C["kirmizi"], "nokta": C["yesil"] if yuk else C["kirmizi"], "alt": "  ".join(alt)})
    jeo = a["tur"].startswith("Jeopolitik")
    return {"baslik": f"{a['tur']} · {etki_ad(a)} · {t:%H:%M}",
            "renk": (C["mavi"] if a["yon"] > 0 else C["altin"]) if jeo else (C["yesil"] if a["yon"] > 0 else C["kirmizi"]),
            "aciklama": f"“{a['baslik'][:160]}”" + (f" — {a['kaynak']}" if a.get("kaynak") else ""), "satirlar": sat}


def haber_karti_gonder(b, analizler, simdi):
    try:
        import kart as K, tg as _tg
        yol = os.path.join(CIKTI, "haber", "kart.png"); os.makedirs(os.path.dirname(yol), exist_ok=True)
        K.bildirim_karti(f"HABER ETKİSİ  ·  {simdi.astimezone(TSI):%d.%m %H:%M}",
                         f"{len(analizler)} önemli haber", "Etkilenen varlıklar, beklenen yön ve piyasanın tepkisi",
                         [kart_bolumu(a) for a in analizler], yol, vurgu=K.C["turkuaz"])
        alt = f"📰 <b>HABER ETKİSİ</b> · {simdi.astimezone(TSI):%H:%M}\n" + "\n".join(
            f"{'🟢' if a['yon'] > 0 else '🔴'} <b>{esc(a['tur'])}</b>: " + (f'<a href="{esc(a["link"])}">{esc(a["baslik"][:90])}</a>' if a.get("link") else esc(a["baslik"][:90]))
            for a in analizler)
        return bool(b.foto(yol, alt[:1000], f"haber:{simdi:%Y%m%d%H%M}", 12))
    except Exception as ex:
        print("Haber kartı çizilemedi:", ex, file=sys.stderr); return False


def _pfk(kod):
    k = str(kod).upper()
    return ("K", k.split("/")[0]) if "/" in k else ("H", k)


def _pf():
    try:
        import portfoy as P
        return {_pfk(k) for k, _, _ in P.takip()}
    except Exception:
        return set()


def etki_ad(a):
    """Haberin piyasa açısından yönü. İnsani/jeopolitik haberlerde 'olumlu/olumsuz' yerine tarafsız dil kullanılır."""
    if a["tur"].startswith("Jeopolitik"):
        return "gerilim azalıyor · piyasa etkisi" if a["yon"] > 0 else "gerilim artıyor · piyasa etkisi"
    return "piyasaya olumlu" if a["yon"] > 0 else "piyasaya olumsuz"


def mesaj(a):
    ikon = ("🕊" if a["yon"] > 0 else "⚠️") if a["tur"].startswith("Jeopolitik") else ("🟢" if a["yon"] > 0 else "🔴")
    t = dt.datetime.fromisoformat(a["zaman"]).astimezone(TSI)
    s = [f"{ikon} <b>{esc(a['tur'])}</b> · {etki_ad(a)} · {t:%H:%M}",
         f"<i>“{esc(a['baslik'][:200])}”</i>" + (f"\n— {esc(a['kaynak'])}" if a.get("kaynak") else "") +
         (f" (+{a['kaynak_sayi'] - 1} kaynak)" if a["kaynak_sayi"] > 1 else "")]
    vl = []; pf = _pf()
    if any(_pfk(v["kod"]) in pf for v in a["varliklar"]):
        s.insert(1, "💼 <b>Portföyünüzdeki bir varlığı etkiliyor</b>")
    for v in a["varliklar"]:
        ok = "⬆️" if v["isaret"] > 0 else "⬇️"
        satir = f"{ok} {'💼 ' if _pfk(v['kod']) in pf else ''}<b>{esc(vad(v['kod']))}</b> — {esc(v['gerekce'])}"
        r = v.get("tepki")
        if r and r["saat"] >= 1:
            yonlu = r["degisim"] * v["isaret"]
            esik = max(r["oyn"] * 1.5, 0.002)
            durum = ("✅ fiyatlandı" if yonlu > esik else "↩️ ters yönde" if yonlu < -esik else "⏳ henüz tepki yok")
            satir += f"\n   Haberden beri {yz(r['degisim'])}" + (f", hacim {r['hacim_k']:.1f}x".replace(".", ",") if r.get("hacim_k") else "") + f" · {durum}"
        te = v.get("teknik")
        if te and te.get("fiyat"):
            import firsat as F
            p = te["fiyat"]
            ek = f"\n   Fiyat <code>{F.fy(p)}</code> · {te['etiket']} ({float(te['puan']):.0f})"
            if te.get("destek"): ek += f" · destek <code>{F.fy(te['destek'])}</code> ({yz(te['destek'] / p - 1)})"
            if te.get("direnc"): ek += f" · direnç <code>{F.fy(te['direnc'])}</code> ({yz(te['direnc'] / p - 1)})"
            satir += ek
        g = v.get("gecmis")
        if g:
            satir += f"\n   Geçmiş {g['n']} benzer haber: 1 günde ort. {yz(g['g1'])} (%{g['pozitif'] * 100:.0f} yükseldi)" + (f", 5 günde {yz(g['g5'])}" if g.get("g5") is not None else "")
        vl.append(satir)
    s.append("<blockquote>" + "\n".join(vl) + "</blockquote>")
    if a.get("link"): s.append(f'<a href="{esc(a["link"])}">Habere git ›</a>')
    return "\n".join(s)


if __name__ == "__main__":
    calistir()
