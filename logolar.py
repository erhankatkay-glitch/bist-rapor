# -*- coding: utf-8 -*-
"""Varlık logoları.
Kripto: spothq/cryptocurrency-icons (CC0 1.0, kamu malı) — varlik/kripto/<sembol>.png (128 px, renkli).
Set 2022'de güncellenmeyi bıraktı; daha yeni coinlerde logo yoksa None döner ve çağıran baş harf rozeti kullanır.
Hisse logoları henüz yok (bkz. docs/PROJE_HAFIZASI.md)."""
import base64
import functools
import os

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
