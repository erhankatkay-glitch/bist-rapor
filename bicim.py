# -*- coding: utf-8 -*-
"""Ortak sayı biçimleri (Türkçe). Birden çok modülde aynı işi gören yardımcılar burada toplanır."""
import math


def yuzde(x, d=1, isaret=True):
    """0,0123 → '+%1,2' · −0,05 → '−%5,0' · isaret=False → '%1,2'. Geçersiz değer → '–'."""
    try:
        if x is None or not math.isfinite(float(x)): return "–"
    except (TypeError, ValueError):
        return "–"
    x = float(x)
    if not isaret: return ("%" + f"{x * 100:.{d}f}").replace(".", ",")
    s = f"{x * 100:+.{d}f}"
    return (s[0] + "%" + s[1:]).replace(".", ",").replace("-", "−")


def sayi(x, d=None):
    """Binlik nokta, ondalık virgül: 10953,15 → '10.953' (≥1000 ise 0 ondalık, değilse 2)."""
    try:
        if x is None or not math.isfinite(float(x)): return "–"
    except (TypeError, ValueError):
        return "–"
    d = (0 if abs(x) >= 1000 else 2) if d is None else d
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
