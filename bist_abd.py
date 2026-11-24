# -*- coding: utf-8 -*-
"""ABD borsaları (NYSE, Nasdaq, NYSE American): tam hisse listesi, likidite filtresi, sektör ETF'leri.
Kod biçimi uygulama genelinde: AAPL.US, BRK.B.US (Yahoo'da BRK-B).
Kaynak: Nasdaq Trader sembol dizini (ücretsiz, günlük güncellenir)."""
import io, os, time, datetime as dt
import pandas as pd

NASDAQ = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
DIGER = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"
BORSA = {"N": "NYSE", "A": "NYSE American", "P": "NYSE Arca", "Z": "Cboe BZX", "V": "IEX", "Q": "Nasdaq"}
HARIC = ("warrant", "right", " unit", "units", "preferred", "depositary share", "notes due", "% notes", "debenture",
         "trust preferred", "subordinated", "when issued", "acquisition corp")
SEKTOR_ETF = {"XLK": "Teknoloji", "XLF": "Finans", "XLV": "Sağlık", "XLY": "Tüketici (isteğe bağlı)", "XLP": "Temel tüketim",
              "XLE": "Enerji", "XLI": "Sanayi", "XLB": "Malzeme", "XLU": "Kamu hizmetleri", "XLRE": "Gayrimenkul", "XLC": "İletişim"}
DEV = {"AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia", "AMZN": "Amazon", "GOOGL": "Alphabet (Google)", "META": "Meta",
       "TSLA": "Tesla", "AVGO": "Broadcom", "BRK.B": "Berkshire Hathaway", "JPM": "JPMorgan", "LLY": "Eli Lilly", "V": "Visa",
       "NFLX": "Netflix", "AMD": "AMD", "PLTR": "Palantir", "COIN": "Coinbase", "MSTR": "MicroStrategy", "TSM": "TSMC", "ORCL": "Oracle"}
LISTE_DOSYA = "abd_listesi.csv"


def abd_mu(kod):
    return str(kod).upper().endswith(".US")


def yahoo(kod):
    """AAPL.US → AAPL, BRK.B.US → BRK-B"""
    return str(kod).upper()[:-3].replace(".", "-")


def kod_yap(sembol):
    return sembol.upper().replace("-", ".").replace("$", "") + ".US"


def _oku(url):
    import requests
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30); r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text), sep="|")


def tum_hisseler():
    """DataFrame[Kod, Sembol, Ad, Borsa] — ETF, test ihracı, varant, hak, tercihli hisse ve tahviller hariç."""
    parca = []
    try:
        n = _oku(NASDAQ); n = n[n["Symbol"].notna() & ~n["Symbol"].astype(str).str.startswith("File Creation")]
        n = n[(n["ETF"] == "N") & (n["Test Issue"] == "N")]
        parca.append(pd.DataFrame({"Sembol": n["Symbol"], "Ad": n["Security Name"], "Borsa": "Nasdaq"}))
    except Exception as ex:
        print("Nasdaq listesi alınamadı:", ex)
    try:
        o = _oku(DIGER); o = o[o["ACT Symbol"].notna() & ~o["ACT Symbol"].astype(str).str.startswith("File Creation")]
        o = o[(o["ETF"] == "N") & (o["Test Issue"] == "N")]
        parca.append(pd.DataFrame({"Sembol": o["ACT Symbol"], "Ad": o["Security Name"], "Borsa": o["Exchange"].map(BORSA).fillna("Diğer")}))
    except Exception as ex:
        print("NYSE listesi alınamadı:", ex)
    if not parca:
        if os.path.exists(LISTE_DOSYA): return pd.read_csv(LISTE_DOSYA, dtype=str)
        return pd.DataFrame({"Kod": [k + ".US" for k in DEV], "Sembol": list(DEV), "Ad": list(DEV.values()), "Borsa": "?"})
    df = pd.concat(parca)
    df["Sembol"] = df["Sembol"].astype(str).str.strip()
    ad = df["Ad"].astype(str).str.lower()
    df = df[~ad.apply(lambda a: any(h in a for h in HARIC))]
    df = df[~df["Sembol"].str.contains(r"[\$\^\s]", regex=True)]
    df["Ad"] = df["Ad"].astype(str).str.replace(r"\s*-\s*(Class [A-Z] )?(Common Stock|Ordinary Shares|Common Shares).*$", "", regex=True).str.strip()
    df["Kod"] = df["Sembol"].map(kod_yap)
    return df.drop_duplicates("Kod")[["Kod", "Sembol", "Ad", "Borsa"]].reset_index(drop=True)


def likit_hisseler(df=None, min_dolar=20e6, min_fiyat=3.0, parca=250):
    """Son 3 ayın verisiyle 20 günlük medyan dolar hacmi ≥ min_dolar ve fiyat ≥ min_fiyat olanlar.
    Döner: (DataFrame[Kod, Sembol, Ad, Borsa, Dolar hacim], not)."""
    import yfinance as yf
    df = df if df is not None else tum_hisseler()
    ys = [yahoo(k) for k in df["Kod"]]; hacim = {}
    for i in range(0, len(ys), parca):
        grup = ys[i:i + parca]
        for deneme in range(3):
            try:
                d = yf.download(grup, period="3mo", interval="1d", auto_adjust=True, progress=False, group_by="ticker", threads=True); break
            except Exception:
                d = None; time.sleep(5)
        if d is None or d.empty: continue
        for s in grup:
            try:
                x = (d[s] if isinstance(d.columns, pd.MultiIndex) else d).dropna(subset=["Close"])
                if len(x) < 15 or float(x["Close"].iloc[-1]) < min_fiyat: continue
                hacim[s] = float((x["Close"] * x["Volume"]).iloc[-20:].median())
            except Exception:
                continue
    df = df.assign(**{"Dolar hacim": [hacim.get(yahoo(k)) for k in df["Kod"]]})
    lk = df[df["Dolar hacim"].fillna(0) >= min_dolar].sort_values("Dolar hacim", ascending=False).reset_index(drop=True)
    return lk, f"ABD: {len(df)} hisse, {len(lk)} likit (20g medyan hacim ≥ {min_dolar / 1e6:.0f} mn $, fiyat ≥ {min_fiyat:.0f} $)"


def liste_kaydet(df, yol=LISTE_DOSYA):
    df[["Kod", "Sembol", "Ad", "Borsa"]].to_csv(yol, index=False)


_AD = {}


def ad(kod):
    if not _AD:
        try:
            for _, r in pd.read_csv(LISTE_DOSYA, dtype=str).iterrows(): _AD[r["Kod"]] = r["Ad"]
        except Exception:
            pass
    s = kod.upper()[:-3] if abd_mu(kod) else kod
    return _AD.get(kod.upper()) or DEV.get(s) or s
