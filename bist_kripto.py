# -*- coding: utf-8 -*-
"""Binance ve OKX spot piyasaları: tüm USDT ve TL (TRY) pariteleri, günlük mumlar, CoinGecko eşlemesi.
Binance'in ana API'si ABD'deki sunucuları engellediği için resmi herkese açık piyasa verisi adresi
(data-api.binance.vision) kullanılır. Anahtar gerekmez, ücretsizdir.

Kod biçimi: "PEPE/USDT", "BTC/TRY", "BTC/TRY@OKX" (borsa belirtilmezse Binance)."""
import time, datetime as dt
import numpy as np
import pandas as pd

BINANCE = "https://data-api.binance.vision/api/v3"
OKX = "https://www.okx.com/api/v5"
CG = "https://api.coingecko.com/api/v3"
UA = {"User-Agent": "Mozilla/5.0"}
PARITELER = ("USDT", "TRY")
BORSALAR = ("Binance", "OKX")
STABIL = {"USDT", "USDC", "FDUSD", "TUSD", "DAI", "BUSD", "USDP", "EUR", "EURI", "AEUR", "USD1", "XUSD", "BFUSD", "USDE", "PYUSD", "RLUSD"}
ESKI = {"BTC": "Bitcoin", "ETH": "Ethereum", "BNB": "BNB", "SOL": "Solana", "XRP": "XRP", "ADA": "Cardano", "DOGE": "Dogecoin",
        "AVAX": "Avalanche", "TRX": "TRON", "LINK": "Chainlink", "DOT": "Polkadot", "LTC": "Litecoin"}


# Borsalarda kripto gibi listelenen "tokenize hisse / ETF" ürünleri (ör. XQQQ, QQQB, AAPLX, TSLAON) kripto sayılmaz.
_HISSE = {"SPY", "QQQ", "IVV", "VOO", "VTI", "DIA", "IWM", "TQQQ", "SQQQ", "GLD", "SLV", "TLT", "ARKK", "AAPL", "MSFT", "NVDA",
          "AMZN", "GOOGL", "GOOG", "META", "TSLA", "NFLX", "AMD", "INTC", "COIN", "MSTR", "HOOD", "CRCL", "PLTR", "ORCL", "AVGO",
          "BABA", "JPM", "ABBV", "LLY", "UNH", "XOM", "CVX", "ACN", "CSCO", "IBM", "CRM", "ADBE", "PEP", "WMT", "COST", "DIS",
          "NKE", "BRK", "GME", "AMC", "PYPL", "SHOP", "UBER", "ABNB", "TSM", "ASML", "MU", "QCOM", "SMCI", "ARM", "RDDT", "SNOW",
          "CRWD", "PANW", "NVO", "MRVL", "APP", "SPOT", "BAC", "GS", "MS", "BLK", "SCHW", "TMO", "MRK", "PFE", "JNJ", "BA", "CAT"}


# Tokenleştirilmiş hisse / ETF (xStocks "X…", Backed "…B", Ondo "…ON"): kripto değil, ABD seans saatlerine bağlı ince likidite.
# Geniş ABD listesiyle yakalanır (Kasım 2026: XSPCX, SPCXB, XSTLL, XBRKB, XOKTA… kripto taramasına girip toplu stop olmuştu).
_GERCEK_KRIPTO = {"XAUT", "XVG", "XEM", "XNO", "XDC", "XCN", "XYO", "XLM", "XRP", "XTZ", "XEC", "XAI", "XVS", "XCH", "XPR", "XPRT", "XWG",
                  "XION", "XPL", "XNET", "XCAD", "XNY", "XTER", "XUSD", "XMR", "XDB", "XCV", "XEN", "XETA", "XRD", "XNC", "XPLA", "XBG", "XMW"}
_ETF = {"EWZ", "EWJ", "EEM", "EFA", "FXI", "KWEB", "XLF", "XLE", "XLK", "SOXX", "SMH", "IBIT", "ETHA", "GDX", "USO", "UNG", "HYG", "LQD",
        "SPCX", "STLL", "BRKB", "BRKA"}
_ABD = None


def _abd_listesi():
    """ABD hisse kodları (tokenleştirilmiş hisse tespiti için): yerel liste, yoksa bülten dalındaki liste; olmazsa boş."""
    global _ABD
    if _ABD is None:
        _ABD = set()
        try:
            import io
            import os
            if os.path.exists("abd_listesi.csv"): df = pd.read_csv("abd_listesi.csv", dtype=str)
            else:
                import requests
                r = requests.get("https://raw.githubusercontent.com/erhankatkay-glitch/bist-rapor/bulten/firsat/abd/abd_listesi.csv", timeout=20)
                df = pd.read_csv(io.StringIO(r.text), dtype=str)
            _ABD = {str(x).upper().replace(".", "").replace("-", "") for x in df["Sembol"].dropna()}
        except Exception:
            _ABD = set()
    return _ABD


def hisse_tokeni_mu(baz):
    b = str(baz).upper().split("/")[0].split("@")[0]
    if b in _HISSE or b in _ETF: return True
    uz = lambda x: x in _HISSE and len(x) >= 3
    if (b.startswith("X") and uz(b[1:])) or (b[-1:] in "BX" and uz(b[:-1])) or (b.endswith("ON") and uz(b[:-2])): return True
    if b in _GERCEK_KRIPTO: return False
    genis = _abd_listesi() | _ETF
    return ((b.startswith("X") and len(b) >= 4 and b[1:] in genis) or (b[-1:] == "B" and len(b) >= 4 and b[:-1] in genis)
            or (b.endswith("ON") and len(b) >= 5 and b[:-2] in genis))


def _get(url, **params):
    import requests
    for deneme in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=20)
            if r.status_code == 429: time.sleep(2 + deneme * 3); continue
            r.raise_for_status(); return r.json()
        except Exception:
            if deneme == 2: raise
            time.sleep(1 + deneme)


# ------------------------------------------------------------------ kod biçimi
def coz(kod, varsayilan_parite="USDT"):
    """'PEPE' | 'PEPE/TRY' | 'PEPE/TRY@OKX' | 'OKX:PEPE/TRY' → (baz, parite, borsa)."""
    k = kod.upper().replace(" ", "")
    borsa = "Binance"
    if k.startswith("OKX:"): borsa, k = "OKX", k[4:]
    if "@" in k:
        k, b = k.split("@", 1); borsa = "OKX" if b.startswith("OKX") else "Binance"
    for ay in ("/", "-"):
        if ay in k:
            baz, par = k.split(ay, 1); return baz, ("TRY" if par in ("TRY", "TL") else "USDT"), borsa
    if k.endswith("-USD"): k = k[:-4]
    return k, varsayilan_parite, borsa


def kod_yap(baz, parite="USDT", borsa="Binance"):
    return f"{baz}/{parite}" + ("@OKX" if borsa == "OKX" else "")


def kripto_mu(kod):
    k = kod.upper()
    return "/" in k or "@OKX" in k or k.startswith("OKX:") or k.endswith("-USD")


# ------------------------------------------------------------------ evren
def binance_pariteler():
    j = _get(f"{BINANCE}/exchangeInfo", permissions="SPOT")
    return pd.DataFrame([{"baz": s["baseAsset"], "parite": s["quoteAsset"], "sembol": s["symbol"], "borsa": "Binance"}
                         for s in j["symbols"] if s["status"] == "TRADING" and s["quoteAsset"] in PARITELER])


def okx_pariteler():
    j = _get(f"{OKX}/public/instruments", instType="SPOT")
    return pd.DataFrame([{"baz": d["baseCcy"], "parite": d["quoteCcy"], "sembol": d["instId"], "borsa": "OKX"}
                         for d in j.get("data", []) if d.get("state") == "live" and d.get("quoteCcy") in PARITELER])


def hacimler():
    """24 saatlik USDT karşılığı hacim (sıralama ve likidite için)."""
    h = {}
    try:
        for t in _get(f"{BINANCE}/ticker/24hr", type="MINI"):
            s = t["symbol"]
            if s.endswith("USDT"): h[("Binance", s[:-4])] = float(t.get("quoteVolume") or 0)
    except Exception:
        pass
    try:
        for t in _get(f"{OKX}/market/tickers", instType="SPOT").get("data", []):
            if t["instId"].endswith("-USDT"):
                h[("OKX", t["instId"][:-5])] = float(t.get("volCcy24h") or 0)
    except Exception:
        pass
    return h


def evren():
    """Tüm coinler: DataFrame[Kod, Binance USDT, Binance TRY, OKX USDT, OKX TRY, Hacim $]. Hacme göre sıralı."""
    parca, notlar = [], []
    for ad, fn in (("Binance", binance_pariteler), ("OKX", okx_pariteler)):
        try:
            d = fn(); parca.append(d); notlar.append(f"{ad}: {len(d)} parite")
        except Exception as ex:
            notlar.append(f"{ad} alınamadı ({str(ex)[:50]})")
    if not parca:
        raise ValueError("Borsa listeleri alınamadı: " + "; ".join(notlar))
    p = pd.concat(parca)
    p = p[~p["baz"].isin(STABIL)]
    p = p[~p["baz"].map(hisse_tokeni_mu)]
    pv = p.assign(var=True).pivot_table(index="baz", columns=["borsa", "parite"], values="var", aggfunc="any", fill_value=False)
    pv.columns = [f"{b} {q}" for b, q in pv.columns]
    for c in ("Binance USDT", "Binance TRY", "OKX USDT", "OKX TRY"):
        if c not in pv: pv[c] = False
    hc = hacimler()
    pv["Hacim $"] = [max(hc.get(("Binance", b), 0), hc.get(("OKX", b), 0)) for b in pv.index]
    pv = pv.reset_index().rename(columns={"baz": "Kod"}).sort_values("Hacim $", ascending=False).reset_index(drop=True)
    pv.attrs["not"] = " · ".join(notlar)
    return pv


# ------------------------------------------------------------------ mumlar
def binance_mumlar(sembol, gun=3000):
    """Günlük mumlar (UTC), sayfalayarak geriye doğru; en fazla `gun` gün."""
    out, son = [], None
    while len(out) < gun:
        prm = {"symbol": sembol, "interval": "1d", "limit": 1000}
        if son: prm["endTime"] = son - 1
        k = _get(f"{BINANCE}/klines", **prm)
        if not k: break
        out = k + out; son = int(k[0][0])
        if len(k) < 1000: break
    if not out: raise ValueError(f"Binance {sembol} için mum verisi yok")
    df = pd.DataFrame(out, columns=["t", "Open", "High", "Low", "Close", "Volume", "tk", "QuoteVol", "n", "a", "b", "c"])
    df.index = pd.to_datetime(df["t"], unit="ms").dt.normalize(); df.index.name = None
    df["TakerBuy"] = df["a"]
    return df[["Open", "High", "Low", "Close", "Volume", "TakerBuy"]].astype(float).iloc[-gun:]


def okx_mumlar(inst, gun=1500):
    out, sonra = [], None
    while len(out) < gun:
        prm = {"instId": inst, "bar": "1Dutc", "limit": 100}
        if sonra: prm["after"] = sonra
        d = _get(f"{OKX}/market/history-candles", **prm).get("data", [])
        if not d: break
        out += d; sonra = d[-1][0]
        if len(d) < 100: break
        time.sleep(0.12)
    if not out: raise ValueError(f"OKX {inst} için mum verisi yok")
    df = pd.DataFrame(out, columns=["t", "Open", "High", "Low", "Close", "Volume", "vq", "vqq", "ok"])
    df.index = pd.to_datetime(df["t"].astype("int64"), unit="ms").dt.normalize(); df.index.name = None
    return df[["Open", "High", "Low", "Close", "Volume"]].astype(float).sort_index().iloc[-gun:]


def mumlar(baz, parite="USDT", borsa="Binance", gun=3000):
    """Tercih edilen borsadan, olmazsa diğerinden günlük OHLCV. (df, kullanılan borsa)"""
    sira = [borsa] + [b for b in BORSALAR if b != borsa]
    son_hata = None
    for b in sira:
        try:
            if b == "Binance": return binance_mumlar(f"{baz}{parite}", gun), "Binance"
            return okx_mumlar(f"{baz}-{parite}", min(gun, 1500)), "OKX"
        except Exception as ex:
            son_hata = ex
    raise ValueError(f"{baz}/{parite} için Binance ve OKX'te veri bulunamadı ({son_hata})")


# ------------------------------------------------------------------ CoinGecko eşlemesi
_CG = {}


def cg_piyasa(sayfa=4):
    """CoinGecko piyasa değeri ilk ~1000 coin: {SEMBOL: kayıt} (aynı sembolde en büyük piyasa değeri)."""
    if _CG: return _CG
    for p in range(1, sayfa + 1):
        try:
            for c in _get(f"{CG}/coins/markets", vs_currency="usd", order="market_cap_desc", per_page=250, page=p):
                s = c["symbol"].upper()
                if s not in _CG: _CG[s] = c
        except Exception:
            break
        time.sleep(1.2)
    return _CG


def cg_id(baz):
    k = cg_piyasa().get(baz.upper())
    if k: return k["id"], k["name"]
    try:
        for c in _get(f"{CG}/search", query=baz).get("coins", []):
            if c["symbol"].upper() == baz.upper(): return c["id"], c["name"]
    except Exception:
        pass
    return None, ESKI.get(baz.upper(), baz.upper())


def cg_kayit(cid):
    """CoinGecko /coins/markets kaydını rapor biçimine çevirir (tek tek /coins/{id} çağrısına gerek bırakmaz)."""
    c = next((x for x in cg_piyasa().values() if x.get("id") == cid), None)
    if not c: raise KeyError(cid)
    p = lambda x: (x / 100) if x is not None else None
    return {"sira": c.get("market_cap_rank"), "piy_deg": c.get("market_cap"), "hacim": c.get("total_volume"),
            "fdv": c.get("fully_diluted_valuation"), "dolasim": c.get("circulating_supply"), "toplam": c.get("total_supply"),
            "maks": c.get("max_supply"), "ath": c.get("ath"), "ath_tarih": c.get("ath_date"), "ath_fark": c.get("ath_change_percentage"),
            "atl": c.get("atl"), "atl_tarih": c.get("atl_date"), "d24": p(c.get("price_change_percentage_24h")),
            "fiyat": c.get("current_price"), "guncelleme": c.get("last_updated"), "kategori": [], "algoritma": None}


def bulten_kodlari(parite="USDT", ev=None):
    """Bülten için tüm coinler: USDT'de Binance öncelikli, TL'de Binance TR / OKX TR."""
    ev = ev if ev is not None else evren()
    out = []
    for _, r in ev.iterrows():
        if r.get(f"Binance {parite}"): out.append(kod_yap(r["Kod"], parite, "Binance"))
        elif r.get(f"OKX {parite}"): out.append(kod_yap(r["Kod"], parite, "OKX"))
    return out


# ================================================================== SAATLİK MUMLAR
def saatlik_mumlar(baz, parite="USDT", borsa="Binance", bar=1500):
    """1 saatlik mumlar (UTC). Önce tercih edilen borsa, olmazsa diğeri."""
    for b in [borsa] + [x for x in BORSALAR if x != borsa]:
        try:
            if b == "Binance":
                out, son = [], None
                while len(out) < bar:
                    prm = {"symbol": f"{baz}{parite}", "interval": "1h", "limit": 1000}
                    if son: prm["endTime"] = son - 1
                    k_ = _get(f"{BINANCE}/klines", **prm)
                    if not k_: break
                    out = k_ + out; son = int(k_[0][0])
                    if len(k_) < 1000: break
                df = pd.DataFrame(out, columns=["t", "Open", "High", "Low", "Close", "Volume", "tk", "q", "n", "a", "b", "c"])
                df.index = pd.to_datetime(df["t"], unit="ms"); df.index.name = None
                return df[["Open", "High", "Low", "Close", "Volume"]].astype(float).iloc[-bar:], "Binance"
            out, sonra = [], None
            while len(out) < bar:
                prm = {"instId": f"{baz}-{parite}", "bar": "1H", "limit": 100}
                if sonra: prm["after"] = sonra
                d = _get(f"{OKX}/market/history-candles", **prm).get("data", [])
                if not d: break
                out += d; sonra = d[-1][0]
                if len(d) < 100: break
                time.sleep(0.12)
            if not out: raise ValueError("veri yok")
            df = pd.DataFrame(out, columns=["t", "Open", "High", "Low", "Close", "Volume", "vq", "vqq", "ok"])
            df.index = pd.to_datetime(df["t"].astype("int64"), unit="ms"); df.index.name = None
            return df[["Open", "High", "Low", "Close", "Volume"]].astype(float).sort_index().iloc[-bar:], "OKX"
        except Exception:
            continue
    raise ValueError(f"{baz}/{parite} için saatlik veri bulunamadı")


# ================================================================== EMİR DEFTERİ ve BÜYÜK İŞLEMLER
def emir_defteri(baz, parite="USDT", borsa="Binance"):
    """Derinlik: ±%1/±%2/±%5 bantlarında alış-satış tutarı, dengesizlik ve en büyük emir duvarları."""
    if borsa == "Binance":
        j = _get(f"{BINANCE}/depth", symbol=f"{baz}{parite}", limit=1000)
        bids = [(float(p), float(q)) for p, q in j["bids"]]; asks = [(float(p), float(q)) for p, q in j["asks"]]
    else:
        d = _get(f"{OKX}/market/books", instId=f"{baz}-{parite}", sz=400)["data"][0]
        bids = [(float(x[0]), float(x[1])) for x in d["bids"]]; asks = [(float(x[0]), float(x[1])) for x in d["asks"]]
    if not bids or not asks: raise ValueError("emir defteri boş")
    orta = (bids[0][0] + asks[0][0]) / 2; o = {"orta": orta, "spread": (asks[0][0] - bids[0][0]) / orta, "bant": {}}
    for b in (0.01, 0.02, 0.05):
        al = sum(p * q for p, q in bids if p >= orta * (1 - b)); sat = sum(p * q for p, q in asks if p <= orta * (1 + b))
        o["bant"][b] = {"alis": al, "satis": sat, "denge": (al - sat) / (al + sat) if al + sat else 0}
    def duvar(liste, yon):
        adim = orta * 0.0025; kova = {}
        for p, q in liste:
            if abs(p / orta - 1) > 0.05: continue
            k_ = round(p / adim) * adim; kova[k_] = kova.get(k_, 0) + p * q
        return sorted(kova.items(), key=lambda x: -x[1])[:3]
    o["alis_duvarlari"] = duvar(bids, 1); o["satis_duvarlari"] = duvar(asks, -1)
    return o


def buyuk_islemler(baz, parite="USDT", borsa="Binance"):
    """Son ~1000 işlemde agresif alış/satış dengesi ve büyük işlemler (balina hareketi)."""
    if borsa == "Binance":
        t = _get(f"{BINANCE}/aggTrades", symbol=f"{baz}{parite}", limit=1000)
        islem = [(float(x["p"]) * float(x["q"]), -1 if x["m"] else 1, int(x["T"])) for x in t]
    else:
        t = _get(f"{OKX}/market/trades", instId=f"{baz}-{parite}", limit=500).get("data", [])
        islem = [(float(x["px"]) * float(x["sz"]), 1 if x["side"] == "buy" else -1, int(x["ts"])) for x in t]
    if not islem: raise ValueError("işlem yok")
    tutar = np.array([x[0] for x in islem]); yon = np.array([x[1] for x in islem])
    esik = max(float(np.percentile(tutar, 99)), 10000.0)
    b = tutar >= esik
    sure_dk = (max(x[2] for x in islem) - min(x[2] for x in islem)) / 60000
    return {"adet": len(islem), "sure_dk": sure_dk, "alis": float(tutar[yon > 0].sum()), "satis": float(tutar[yon < 0].sum()),
            "buyuk_esik": esik, "buyuk_alis": float(tutar[b & (yon > 0)].sum()), "buyuk_satis": float(tutar[b & (yon < 0)].sum()),
            "buyuk_adet": int(b.sum())}


def mikro_yorum(ed, bi, taker=None, para="$"):
    C = []
    if ed:
        b = ed["bant"][0.02]
        C.append(f"Emir defterinde fiyatın ±%2'lik bandında {b['alis'] / 1e3:,.0f} bin {para} alış, {b['satis'] / 1e3:,.0f} bin {para} satış emri bekliyor".replace(",", ".")
                 + (" — alıcı tarafı belirgin şekilde daha derin." if b["denge"] > 0.2 else " — satıcı tarafı belirgin şekilde daha derin." if b["denge"] < -0.2 else " — denge görünümü var."))
        if ed["alis_duvarlari"] and ed["satis_duvarlari"]:
            import tasarim as TS
            C.append(f"En güçlü alış duvarı ~{TS._sayi(ed['alis_duvarlari'][0][0])}, en güçlü satış duvarı ~{TS._sayi(ed['satis_duvarlari'][0][0])} seviyesinde.")
    if bi:
        top = bi["alis"] + bi["satis"]
        if top: C.append(f"Son {bi['adet']} işlemin (~{bi['sure_dk']:.0f} dk) %{bi['alis'] / top * 100:.0f} kadarı agresif alış; "
                         f"büyük işlemlerde ({bi['buyuk_adet']} adet) net {'alış' if bi['buyuk_alis'] >= bi['buyuk_satis'] else 'satış'} ağırlığı var.")
    if taker is not None:
        C.append(f"Son 7 günde agresif alım oranı ortalama %{taker * 100:.0f}" + (" (alıcılar baskın)." if taker > 0.53 else " (satıcılar baskın)." if taker < 0.47 else " (dengeli)."))
    return " ".join(C)


# ================================================================== VADELİ PİYASA (OKX)
def vadeli(baz):
    o = {}
    try:
        d = _get(f"{OKX}/rubik/stat/contracts/open-interest-volume", ccy=baz, period="1D").get("data", [])
        s = pd.Series({pd.to_datetime(int(x[0]), unit="ms"): float(x[1]) for x in d}).sort_index()
        if len(s) > 8:
            o["oi"] = s; o["oi_son"] = float(s.iloc[-1]); o["oi_7g"] = float(s.iloc[-1] / s.iloc[-8] - 1)
            o["oi_30g"] = float(s.iloc[-1] / s.iloc[-31] - 1) if len(s) > 31 else None
    except Exception:
        pass
    try:
        d = _get(f"{OKX}/rubik/stat/taker-volume", ccy=baz, instType="CONTRACTS", period="1D").get("data", [])
        df = pd.DataFrame([(pd.to_datetime(int(x[0]), unit="ms"), float(x[1]), float(x[2])) for x in d], columns=["t", "sat", "al"]).set_index("t").sort_index()
        if len(df) > 7:
            o["taker"] = df; s7 = df.iloc[-7:]; o["taker_7g"] = float(s7["al"].sum() / (s7["al"].sum() + s7["sat"].sum()))
    except Exception:
        pass
    try:
        d = _get(f"{OKX}/public/liquidation-orders", instType="SWAP", uly=f"{baz}-USDT", state="filled", limit=100).get("data", [])
        lng = sht = 0.0; ilk = None
        for blok in d:
            for x in blok.get("details", []):
                v = float(x["sz"]) * float(x["bkPx"]); ts = int(x["ts"]); ilk = ts if ilk is None else min(ilk, ts)
                if x.get("posSide") == "long": lng += v
                else: sht += v
        if lng + sht > 0: o["likidasyon"] = {"long": lng, "short": sht, "saat": (time.time() * 1000 - ilk) / 3.6e6 if ilk else None}
    except Exception:
        pass
    return o


def vadeli_yorum(v, fiyat_7g=None):
    if not v: return ""
    C = []
    if v.get("oi_7g") is not None:
        t = f"Vadeli açık pozisyon son 7 günde {'+' if v['oi_7g'] > 0 else '-'}%{abs(v['oi_7g']) * 100:.1f}".replace(".", ",")
        if fiyat_7g is not None:
            if v["oi_7g"] > 0.05 and fiyat_7g > 0: t += " arttı ve fiyat da yükseldi: yeni para girişiyle desteklenen bir yükseliş."
            elif v["oi_7g"] > 0.05 and fiyat_7g < 0: t += " arttı ancak fiyat düştü: açığa (short) pozisyonlar artıyor."
            elif v["oi_7g"] < -0.05 and fiyat_7g > 0: t += " azaldı ancak fiyat yükseldi: yükseliş kısa pozisyon kapanışlarından geliyor olabilir."
            elif v["oi_7g"] < -0.05 and fiyat_7g < 0: t += " azaldı ve fiyat düştü: uzun pozisyonlar tasfiye ediliyor."
            else: t += " değişti; belirgin bir kaldıraç değişimi yok."
        C.append(t)
    if v.get("taker_7g") is not None:
        C.append(f"Vadeli piyasada son 7 günde agresif alım payı %{v['taker_7g'] * 100:.0f}" + (" (alıcılar baskın)." if v["taker_7g"] > 0.52 else " (satıcılar baskın)." if v["taker_7g"] < 0.48 else "."))
    lq = v.get("likidasyon")
    if lq:
        b_ = lambda x: f"{x / 1e3:,.0f}".replace(",", ".")
        C.append(f"Son likidasyonların {'uzun (long)' if lq['long'] > lq['short'] else 'kısa (short)'} pozisyonlarda yoğunlaştığı görülüyor "
                 f"(long {b_(lq['long'])} bin $, short {b_(lq['short'])} bin $).")
    return " ".join(C)


# ================================================================== DeFi / STABLECOIN (DefiLlama)
LLAMA = "https://api.llama.fi"
_PROT = []


def stablecoin_ozet():
    d = _get("https://stablecoins.llama.fi/stablecoincharts/all")
    s = pd.Series({pd.to_datetime(int(x["date"]), unit="s"): float(x["totalCirculatingUSD"].get("peggedUSD", 0)) for x in d}).sort_index()
    return {"toplam": float(s.iloc[-1]), "d30": float(s.iloc[-1] / s.iloc[-31] - 1), "d90": float(s.iloc[-1] / s.iloc[-91] - 1), "seri": s.iloc[-365:]}


def tvl_ozet():
    d = _get(f"{LLAMA}/v2/historicalChainTvl")
    s = pd.Series({pd.to_datetime(int(x["date"]), unit="s"): float(x["tvl"]) for x in d}).sort_index()
    return {"toplam": float(s.iloc[-1]), "d30": float(s.iloc[-1] / s.iloc[-31] - 1)}


_ZINCIR = []


def protokol(baz, cg_id=None):
    """Coine ait zincir veya DeFi protokolü: TVL, piyasa değeri/TVL, ücretler ve fiyat/ücret oranı.
    Önce zincir listesi (ETH → Ethereum ağı), sonra TVL'si olan protokoller aranır."""
    global _PROT, _ZINCIR
    if not _ZINCIR:
        try: _ZINCIR = _get(f"{LLAMA}/v2/chains")
        except Exception: _ZINCIR = []
    z = [c for c in _ZINCIR if (cg_id and c.get("gecko_id") == cg_id) or str(c.get("tokenSymbol") or "").upper() == baz.upper()]
    z = [c for c in z if (c.get("tvl") or 0) > 0]
    if z:
        c = max(z, key=lambda x: x["tvl"])
        o = {"ad": f"{c['name']} ağı", "tvl": c["tvl"], "d7": None, "mcap": None, "kategori": "Blokzincir", "slug": None}
        try:
            mc = cg_piyasa().get(baz.upper(), {}).get("market_cap")
            if mc: o["mcap"] = mc; o["mcap_tvl"] = mc / c["tvl"]
        except Exception:
            pass
        return o
    if not _PROT: _PROT = _get(f"{LLAMA}/protocols")
    adaylar = [p for p in _PROT if ((cg_id and p.get("gecko_id") == cg_id) or (str(p.get("symbol", "")).upper() == baz.upper()))
               and (p.get("tvl") or 0) > 0 and p.get("category") not in ("CEX", "Foundation")]
    if not adaylar: return None
    p = max(adaylar, key=lambda x: x.get("tvl") or 0)
    o = {"ad": p.get("name"), "tvl": p.get("tvl"), "d7": (p.get("change_7d") or 0) / 100 if p.get("change_7d") is not None else None,
         "mcap": p.get("mcap"), "kategori": p.get("category"), "slug": p.get("slug")}
    if not o["mcap"]:
        try: o["mcap"] = cg_piyasa().get(baz.upper(), {}).get("market_cap")
        except Exception: pass
    if o["mcap"] and o["tvl"]: o["mcap_tvl"] = o["mcap"] / o["tvl"]
    try:
        f = _get(f"{LLAMA}/summary/fees/{p['slug']}", dataType="dailyFees")
        o["ucret_30g"] = f.get("total30d"); o["ucret_24s"] = f.get("total24h")
        if o["ucret_30g"] and o["mcap"]: o["fiyat_ucret"] = o["mcap"] / (o["ucret_30g"] * 12)
    except Exception:
        pass
    return o


def defi_yorum(st_, tv, pr):
    C = []
    if st_:
        C.append(f"Stablecoin arzı {st_['toplam'] / 1e9:,.0f} milyar $; son 30 günde {'+' if st_['d30'] > 0 else ''}%{st_['d30'] * 100:.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
                 + (" — kripto piyasasına taze likidite girişi sürüyor." if st_["d30"] > 0.01 else " — likidite girişi yavaşladı." if st_["d30"] < 0 else "."))
    if tv: C.append(f"DeFi'de kilitli toplam değer (TVL) son 30 günde {'+' if tv['d30'] > 0 else ''}%{tv['d30'] * 100:.1f}".replace(".", ",") + " değişti.")
    if pr and pr.get("tvl"):
        t = f"{pr['ad']} {'üzerinde' if 'ağı' in str(pr['ad']) else 'protokolünde'} {pr['tvl'] / 1e6:,.0f} milyon $ kilitli varlık bulunuyor".replace(",", ".")
        if pr.get("mcap_tvl"): t += f"; piyasa değeri/TVL oranı {pr['mcap_tvl']:.2f}".replace(".", ",")
        if pr.get("fiyat_ucret"): t += f", yıllıklandırılmış ücretlere göre fiyat/ücret oranı {pr['fiyat_ucret']:.1f}x".replace(".", ",")
        C.append(t + ".")
    return " ".join(C)


def taker_orani(h, gun=7):
    if "TakerBuy" not in h or h["Volume"].iloc[-gun:].sum() <= 0: return None
    return float(h["TakerBuy"].iloc[-gun:].sum() / h["Volume"].iloc[-gun:].sum())
