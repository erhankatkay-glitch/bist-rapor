# -*- coding: utf-8 -*-
"""Varlık logoları.
Kripto: spothq/cryptocurrency-icons (CC0 1.0, kamu malı) — varlik/kripto/<sembol>.png (128 px, renkli).
Set 2022'de güncellenmeyi bıraktı; daha yeni coinlerde logo yoksa None döner ve çağıran baş harf rozeti kullanır.
Hisseler (BIST ve ABD): logo.dev ücretsiz planı (ayda 500 bin görüntüleme). Anahtar 'publishable' türündedir:
logo.dev'e göre tarayıcı kodunda açıkça kullanılması güvenlidir; gizli anahtar (sk_) burada YOKTUR ve kullanılmaz."""
import base64
import functools
import os
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


def logo_url(kod, piyasa):
    """Uygulama (tarayıcı) için: kripto → data: adresi, hisse → logo.dev adresi, diğer → None."""
    if piyasa == "kripto": return kripto_logo_uri(kod)
    if piyasa in ("bist", "abd"): return hisse_logo_url(kod, piyasa)
    return None


@functools.lru_cache(maxsize=512)
def logo_dosya(kod, piyasa):
    """Kart çizimi için yerel PNG yolu (hisseler indirilip önbelleğe alınır) ya da None."""
    if piyasa == "kripto": return kripto_logo(kod)
    u = hisse_logo_url(kod, piyasa)
    if not u: return None
    os.makedirs(_ONBELLEK, exist_ok=True)
    yol = os.path.join(_ONBELLEK, f"{hisse_sembol(kod, piyasa)}.png")
    if os.path.exists(yol): return yol
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=10)
        if r.status != 200: return None
        open(yol, "wb").write(r.read())
        return yol
    except Exception:
        return None
