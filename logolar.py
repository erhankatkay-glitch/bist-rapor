# -*- coding: utf-8 -*-
"""Varlık logoları.
Kripto: spothq/cryptocurrency-icons (CC0 1.0, kamu malı) — varlik/kripto/<sembol>.png (128 px, renkli).
Set 2022'de güncellenmeyi bıraktı; daha yeni coinlerde logo yoksa None döner ve çağıran baş harf rozeti kullanır.
Hisseler (BIST ve ABD): logo.dev ücretsiz planı (ayda 500 bin görüntüleme). Anahtar 'publishable' türündedir:
logo.dev'e göre tarayıcı kodunda açıkça kullanılması güvenlidir; gizli anahtar (sk_) burada YOKTUR ve kullanılmaz."""
import base64
import functools
import os
import re
import tempfile
import urllib.request

LOGO_DEV = os.environ.get("LOGO_DEV_KEY") or "pk_NiCo4KhNTEezBYR82hG_6Q"
_ONBELLEK = os.path.join(tempfile.gettempdir(), "katkay_logolar")

KOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "varlik", "kripto")
ESLE = {"POL": "matic", "WBTC": "wbtc", "XBT": "btc"}   # yeniden adlandırılan coinler


def kripto_baz(kod):
    k = str(kod).upper()
    for ek in ("@OKX", "@BINANCE"):
        k = k.replace(ek, "")
    for ek in ("/USDT", "/TRY", "/USD", "-USD", "USDT"):
        if k.endswith(ek) and len(k) > len(ek): k = k[: -len(ek)]
    return k.split("/")[0]


@functools.lru_cache(maxsize=1024)
def kripto_logo(kod):
    """Logo dosyasının yolu ya da None."""
    b = kripto_baz(kod)
    ad = ESLE.get(b, b).lower()
    yol = os.path.join(KOK, f"{ad}.png")
    return yol if os.path.exists(yol) else None


@functools.lru_cache(maxsize=1024)
def kripto_logo_uri(kod):
    """Uygulama için data: adresi (HTML <img> ya da st.column_config.ImageColumn)."""
    yol = kripto_logo(kod)
    if not yol: return None
    return "data:image/png;base64," + base64.b64encode(open(yol, "rb").read()).decode()


def hisse_sembol(kod, piyasa):
    k = str(kod).upper().strip()
    if piyasa == "bist" or k.endswith(".IS"):
        return k.replace(".IS", "") + ".IS"
    if piyasa == "abd" or k.endswith(".US"):
        return k.replace(".US", "").replace(".", "-")
    return None


def hisse_logo_url(kod, piyasa, boy=128):
    s = hisse_sembol(kod, piyasa)
    if not s or s.startswith("X") and s.endswith(".IS") and s[:-3] in ("XU100", "XU030", "XBANK", "XUSIN", "XHOLD"):
        return None
    return f"https://img.logo.dev/ticker/{s}?token={LOGO_DEV}&size={boy}&format=png&fallback=404"


def kripto_logo_url(kod, boy=128):
    """Logo.dev kripto logosu (sembolle): img.logo.dev/crypto/btc."""
    b = kripto_baz(kod)
    return f"https://img.logo.dev/crypto/{b.lower()}?token={LOGO_DEV}&size={boy}&format=png&fallback=404" if b else None


def logo_url(kod, piyasa):
    """Uygulama (tarayıcı) için: kripto ve hisse → logo.dev adresi (kriptoda yedek: yerel CC0 set), diğer → None."""
    if piyasa == "kripto": return kripto_logo_url(kod)
    if piyasa in ("bist", "abd"): return hisse_logo_url(kod, piyasa)
    return None


# ---- hisse ve kripto dışındaki bütün piyasalar: endeksler (borsanın / endeks sağlayıcısının logosu), emtialar (işlem gördüğü
#      borsanın logosu), döviz (ülke bayrağı), tahvil (hazine). Anahtar: kod ya da uygulamadaki görünen ad.
OZEL_ALAN = {
    # Türkiye
    "XU100": "borsaistanbul.com", "XU030": "borsaistanbul.com", "XBANK": "borsaistanbul.com", "XUSIN": "borsaistanbul.com",
    "XHOLD": "borsaistanbul.com", "XUTEK": "borsaistanbul.com", "XHARZ": "borsaistanbul.com", "BIST 100": "borsaistanbul.com",
    "BIST 30": "borsaistanbul.com", "BIST Banka": "borsaistanbul.com",
    # ABD
    "SP500": "spglobal.com", "S&P 500": "spglobal.com", "NASDAQ": "nasdaq.com", "Nasdaq": "nasdaq.com", "NDX": "nasdaq.com",
    "DOW": "dowjones.com", "Dow Jones": "dowjones.com", "VIX": "cboe.com", "RUSSELL": "lseg.com", "Russell 2000": "lseg.com",
    "US10Y": "treasury.gov", "ABD 10Y faiz": "treasury.gov", "S&P/TSX": "tmx.com", "Bovespa": "b3.com.br",
    # Avrupa
    "DAX": "deutsche-boerse.com", "FTSE 100": "lseg.com", "FTSE": "lseg.com", "CAC 40": "euronext.com", "Euro Stoxx 50": "stoxx.com",
    # Asya-Pasifik
    "Nikkei 225": "nikkei.com", "NIKKEI": "nikkei.com", "Hang Seng": "hsi.com.hk", "HSI": "hsi.com.hk", "Şanghay": "sse.com.cn",
    "KOSPI": "krx.co.kr", "Sensex": "bseindia.com", "ASX 200": "asx.com.au",
    # emtia: işlem gördüğü vadeli borsa (COMEX / NYMEX / CBOT = CME Group; Brent ve yumuşak emtialar = ICE)
    "ALTIN": "cmegroup.com", "GRAMALTIN": "cmegroup.com", "GUMUS": "cmegroup.com", "PLATIN": "cmegroup.com", "PALADYUM": "cmegroup.com",
    "BAKIR": "cmegroup.com", "WTI": "cmegroup.com", "DOGALGAZ": "cmegroup.com", "BUGDAY": "cmegroup.com", "MISIR": "cmegroup.com",
    "SOYA": "cmegroup.com", "BRENT": "ice.com", "KAHVE": "ice.com", "KAKAO": "ice.com", "SEKER": "ice.com", "PAMUK": "ice.com",
    "Altın": "cmegroup.com", "Ons altın": "cmegroup.com", "Gram altın": "cmegroup.com", "Gümüş": "cmegroup.com", "Platin": "cmegroup.com",
    "Bakır": "cmegroup.com", "Ham petrol (WTI)": "cmegroup.com", "Doğal gaz": "cmegroup.com", "Mısır": "cmegroup.com", "Buğday": "cmegroup.com",
    "Brent petrol": "ice.com", "Dolar endeksi": "ice.com", "DXY": "ice.com",
}
PARA_ULKE = {"USD": "us", "EUR": "eu", "GBP": "gb", "JPY": "jp", "CHF": "ch", "AUD": "au", "CAD": "ca", "CNY": "cn", "TRY": "tr",
             "NZD": "nz", "SEK": "se", "NOK": "no", "RUB": "ru", "INR": "in", "BRL": "br", "MXN": "mx", "ZAR": "za", "KRW": "kr"}


def doviz_ulke(kod):
    """'USD/TRY' → 'tr' (TL paritelerinde Türkiye), 'EUR/USD' → 'eu', 'USD/JPY' → 'jp' (doların karşısındaki para)."""
    k = str(kod).upper().replace(" ", "")
    m = re.fullmatch(r"([A-Z]{3})/?([A-Z]{3})(=X)?", k)
    if not m or m.group(1) not in PARA_ULKE or m.group(2) not in PARA_ULKE: return None
    a, b = m.group(1), m.group(2)
    if b == "TRY" and a == "USD": return "tr"
    return PARA_ULKE[a] if a != "USD" else PARA_ULKE[b]


def ozel_url(kod, boy=128):
    """Hisse/kripto dışı varlığın logo adresi (endeks, emtia, döviz, tahvil) ya da None."""
    k = str(kod).strip()
    alan = OZEL_ALAN.get(k) or OZEL_ALAN.get(k.upper())
    if alan: return f"https://img.logo.dev/{alan}?token={LOGO_DEV}&size={boy}&format=png&fallback=404"
    u = doviz_ulke(k)
    return f"https://flagcdn.com/w160/{u}.png" if u else None


@functools.lru_cache(maxsize=512)
def logo_dosya(kod, piyasa):
    """Kart çizimi için yerel PNG yolu (indirilip önbelleğe alınır) ya da None. Hisse, kripto, endeks, emtia, döviz, tahvil."""
    oz = ozel_url(kod)
    if oz:
        u = oz; ad = "ozel_" + re.sub(r"[^A-Za-z0-9]+", "_", str(kod))
    elif piyasa not in ("kripto", "bist", "abd"): return None
    elif piyasa == "kripto":
        u = kripto_logo_url(kod); ad = "kripto_" + kripto_baz(kod)
    else:
        u = hisse_logo_url(kod, piyasa); ad = hisse_sembol(kod, piyasa) if u else None
    if not u: return None
    os.makedirs(_ONBELLEK, exist_ok=True)
    yol = os.path.join(_ONBELLEK, f"{ad}.png")
    if os.path.exists(yol): return yol
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=10)
        if r.status != 200: raise ValueError(r.status)
        open(yol, "wb").write(r.read())
        return yol
    except Exception:
        return kripto_logo(kod) if piyasa == "kripto" else None   # kriptoda yedek: yerel CC0 set


_LOGOSUZ = {"XU100", "XU030", "XBANK", "XUSIN", "XHOLD", "XUTEK", "SP500", "NASDAQ", "DOW", "VIX", "DAX", "USDTRY", "EURTRY", "DXY", "US10Y",
            "ALTIN", "GRAMALTIN", "GUMUS", "BRENT", "WTI", "BAKIR", "PLATIN", "PALADYUM", "DOGALGAZ", "BUGDAY", "MISIR", "SOYA", "KAHVE",
            "KAKAO", "SEKER", "PAMUK"}


def tahmin_piyasa(kod):
    """Koddan piyasa: 'BTC/USDT' → kripto, 'AAPL.US' → abd, 'THYAO' → bist; endeks / emtia / döviz → 'ozel' (kendi logosu)."""
    if ozel_url(kod): return "ozel"
    k = str(kod).upper()
    if "/" in k or k.endswith("-USD") or "@" in k: return "kripto"
    if k.endswith(".US"): return "abd"
    if k in _LOGOSUZ: return None
    return "bist" if re.fullmatch(r"[A-Z0-9]{3,6}", k.replace(".IS", "")) else None
