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


@functools.lru_cache(maxsize=512)
def logo_dosya(kod, piyasa):
    """Kart çizimi için yerel PNG yolu (hisseler indirilip önbelleğe alınır) ya da None."""
    if piyasa not in ("kripto", "bist", "abd"): return None
    if piyasa == "kripto":
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
    """Koddan piyasa: 'BTC/USDT' → kripto, 'AAPL.US' → abd, 'THYAO' → bist; endeks ve emtia → None (logo yok)."""
    k = str(kod).upper()
    if "/" in k or k.endswith("-USD") or "@" in k: return "kripto"
    if k.endswith(".US"): return "abd"
    if k in _LOGOSUZ: return None
    return "bist" if re.fullmatch(r"[A-Z0-9]{3,6}", k.replace(".IS", "")) else None
