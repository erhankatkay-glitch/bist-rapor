"""QuantDinger gösterge kütüphanesi sürücüsü (Apache-2.0 betikler; kaynak: github.com/erhankatkay-glitch/QuantDinger, library/indicators).

Her betik aynı sözleşmeyi kullanır: girdi `df` (open/high/low/close/volume) ve `params`; çıktı `output["signals"]` içinde
type="buy"/"sell" olay dizileri (olay olmayan mumda None). Bu modül betiği varsayılan ayarlarla çalıştırıp
AL/SAT olay indekslerini döndürür. Emir vermez; yalnızca sinyal okur.
"""
import math, os, glob, re, signal
import numpy as np
import pandas as pd

KLASOR = os.environ.get("QD_KLASOR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "qd_kutuphane"))
_DERLI = {}


def betikler(klasor=KLASOR):
    return sorted(glob.glob(os.path.join(klasor, "*.py")))


def ad(yol):
    return re.sub(r"^\d+_quantdinger_", "", os.path.basename(yol))[:-3]


def _derle(yol):
    if yol not in _DERLI:
        _DERLI[yol] = compile(open(yol, encoding="utf-8").read(), yol, "exec")
    return _DERLI[yol]


class _Sure(Exception):
    pass


def _alarm(*_):
    raise _Sure()


def sinyaller(yol, d, sure=8):
    """d: Open/High/Low/Close/Volume sütunlu DataFrame → (al_indeksleri, sat_indeksleri) ya da None (sinyal yok / hata)."""
    df = pd.DataFrame({"open": d["Open"].to_numpy(float), "high": d["High"].to_numpy(float), "low": d["Low"].to_numpy(float),
                       "close": d["Close"].to_numpy(float),
                       "volume": (d["Volume"] if "Volume" in d else pd.Series(0.0, index=d.index)).fillna(0).to_numpy(float)},
                      index=pd.RangeIndex(len(d)))
    try:
        zt = pd.DatetimeIndex(d.index)
        zt = zt.tz_localize("UTC") if zt.tz is None else zt.tz_convert("UTC")
        df["time"] = (zt.asi8 // 10**6).astype(float)          # ms
    except Exception:
        df["time"] = (np.arange(len(d)) * 86_400_000 + 1.6e12).astype(float)
    ns = {"df": df, "params": {}, "np": np, "pd": pd, "math": math, "__name__": "qd"}
    eski = signal.signal(signal.SIGALRM, _alarm); signal.alarm(sure)
    try:
        exec(_derle(yol), ns)
    finally:
        signal.alarm(0); signal.signal(signal.SIGALRM, eski)
    out = ns.get("output") or {}
    al, sat = set(), set()
    for s in out.get("signals") or []:
        tip = str(s.get("type", "")).lower()
        if tip not in ("buy", "sell"): continue
        idx = [i for i, v in enumerate(s.get("data") or []) if v is not None and v is not False]
        (al if tip == "buy" else sat).update(idx)
    if not al and not sat and not out.get("signals"): return None
    return np.array(sorted(al), dtype=int), np.array(sorted(sat), dtype=int)
