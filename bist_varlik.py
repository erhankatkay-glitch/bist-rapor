# -*- coding: utf-8 -*-
"""Emtia ve kripto para analizi + PDF raporu.
Bilanço olmadığı için analiz; trend, momentum, risk, para akışı, mevsimsellik, korelasyon ve
(kriptolarda) piyasa verisi / duyarlılık endeksine dayanır. Tasarım hisse raporuyla ortaktır."""
import os, math, datetime as dt
import numpy as np
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, CondPageBreak
import matplotlib.pyplot as plt

import tasarim as TS
import analist as AN
import bist_kripto as KR
from tasarim import ST, Bolum, kart_izgarasi, bilgi_kutusu, trafik_listesi, kapak, sayfa_cizici
import bist_rapor as br
from bist_rapor import yz, kat, ond, puan, ort, kucuk, reel, _png, _img, PARAM


def tl(x, d=2):
    """Varlık raporları için sayı biçimi: milyar üstü kısaltılır, küçük coin fiyatlarında basamak korunur."""
    x = br.sayi(x)
    if x is None: return "–"
    if abs(x) >= 1e9: return br.tl(x)
    return TS._sayi(x, d) if abs(x) >= 1 or d != 0 else TS._sayi(x, 0)

C = TS.GRAFIK

VARLIKLAR = {
    # kod: (yahoo, ad, tür, coingecko_id, haber sorgusu)
    "GRAMALTIN": (None, "Gram Altın (TL)", "emtia", None, "gram altın fiyatı"),
    "ALTIN": ("GC=F", "Altın (ons)", "emtia", None, "altın fiyatları ons"),
    "GUMUS": ("SI=F", "Gümüş (ons)", "emtia", None, "gümüş fiyatları"),
    "PLATIN": ("PL=F", "Platin", "emtia", None, "platin fiyatı"),
    "PALADYUM": ("PA=F", "Paladyum", "emtia", None, "paladyum fiyatı"),
    "BAKIR": ("HG=F", "Bakır", "emtia", None, "bakır fiyatları"),
    "BRENT": ("BZ=F", "Brent Petrol", "emtia", None, "Brent petrol fiyatı"),
    "WTI": ("CL=F", "WTI Petrol", "emtia", None, "WTI petrol"),
    "DOGALGAZ": ("NG=F", "Doğal Gaz", "emtia", None, "doğal gaz fiyatları"),
    "BUGDAY": ("ZW=F", "Buğday", "emtia", None, "buğday fiyatları"),
    "MISIR": ("ZC=F", "Mısır", "emtia", None, "mısır fiyatları emtia"),
    "SOYA": ("ZS=F", "Soya Fasulyesi", "emtia", None, "soya fiyatları"),
    "KAHVE": ("KC=F", "Kahve", "emtia", None, "kahve fiyatları emtia"),
    "KAKAO": ("CC=F", "Kakao", "emtia", None, "kakao fiyatları"),
    "SEKER": ("SB=F", "Şeker", "emtia", None, "şeker fiyatları emtia"),
    "PAMUK": ("CT=F", "Pamuk", "emtia", None, "pamuk fiyatları"),
    "BTC": ("BTC-USD", "Bitcoin", "kripto", "bitcoin", "Bitcoin"),
    "ETH": ("ETH-USD", "Ethereum", "kripto", "ethereum", "Ethereum"),
    "BNB": ("BNB-USD", "BNB", "kripto", "binancecoin", "BNB coin"),
    "SOL": ("SOL-USD", "Solana", "kripto", "solana", "Solana kripto"),
    "XRP": ("XRP-USD", "XRP", "kripto", "ripple", "XRP Ripple"),
    "ADA": ("ADA-USD", "Cardano", "kripto", "cardano", "Cardano ADA"),
    "DOGE": ("DOGE-USD", "Dogecoin", "kripto", "dogecoin", "Dogecoin"),
    "AVAX": ("AVAX-USD", "Avalanche", "kripto", "avalanche-2", "Avalanche AVAX"),
    "TRX": ("TRX-USD", "TRON", "kripto", "tron", "TRON TRX"),
    "LINK": ("LINK-USD", "Chainlink", "kripto", "chainlink", "Chainlink"),
    "DOT": ("DOT-USD", "Polkadot", "kripto", "polkadot", "Polkadot"),
    "LTC": ("LTC-USD", "Litecoin", "kripto", "litecoin", "Litecoin"),
}
AYLAR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]

SOZLUK_VARLIK = [
    ("Ons", "Altın ve gümüşte uluslararası fiyat birimi; 1 ons ≈ 31,1 gram."),
    ("200 günlük ortalama", "Son 200 işlem gününün ortalama fiyatı. Fiyat bunun üzerindeyse uzun vadeli eğilim yukarı kabul edilir."),
    ("Mayer çarpanı", "Fiyatın 200 günlük ortalamaya oranı. 1'in çok üstü 'ortalamaya göre pahalı', altı 'ucuz' anlamına gelir."),
    ("Volatilite", "Fiyatın yıllık ne kadar sert dalgalandığı. Yüksekse risk ve getiri potansiyeli birlikte yüksektir."),
    ("Zirveden düşüş", "Fiyatın son dönemdeki en yüksek seviyesinden ne kadar uzakta olduğu."),
    ("RSI", "0–100 arası momentum göstergesi. 70 üstü aşırı alım, 30 altı aşırı satım kabul edilir."),
    ("CMF / OBV", "Hacme dayalı para akışı göstergeleri. Pozitifse alıcıların baskın olduğuna işaret eder."),
    ("Korelasyon", "İki varlığın birlikte hareket etme eğilimi (-1 ile +1 arası). 1'e yakınsa birlikte yükselip düşerler."),
    ("Mevsimsellik", "Geçmiş yıllarda belirli aylarda görülen ortalama fiyat davranışı. Geleceği garanti etmez."),
    ("Korku ve Açgözlülük Endeksi", "Kripto piyasasının genel duyarlılığını 0 (aşırı korku) ile 100 (aşırı açgözlülük) arasında ölçer."),
    ("Reel getiri", "Enflasyondan arındırılmış getiri; paranın gerçekte değer kazanıp kazanmadığını gösterir."),
]

SOZLUK_KRIPTO = [
    ("FDV (tam seyreltilmiş değer)", "Tüm arz basılmış olsaydı oluşacak piyasa değeri. Piyasa değeri FDV'den çok küçükse ileride yeni token arzı fiyatı baskılayabilir."),
    ("Log-regresyon / güç yasası", "Fiyatın tüm geçmişine logaritmik ölçekte çizilen eğilim çizgisi. Uzun vadeli 'normal' fiyatı ve aşırı ısınma/birikim bantlarını gösterir."),
    ("200 haftalık ortalama", "Yaklaşık 4 yıllık ortalama fiyat; Bitcoin'de tarihsel olarak döngü diplerine yakın seviyedir."),
    ("Fonlama oranı", "Vadeli (perpetual) kontratlarda alıcı ile satıcı arasında periyodik ödenen ücret. Pozitif ve yüksekse alıcılar kalabalıktır."),
    ("Açık pozisyon", "Kapanmamış vadeli kontratların toplam büyüklüğü; kaldıracın piyasadaki seviyesini gösterir."),
    ("Bitcoin dominansı", "Bitcoin'in toplam kripto piyasa değeri içindeki payı. Düşüşü genellikle altcoinlere para akışına işaret eder."),
    ("Hash oranı", "Bitcoin ağını güvence altına alan toplam işlem gücü; madenci sağlığının göstergesidir."),
    ("Sharpe / Sortino", "Risk başına getiri ölçüleri. Sortino yalnızca aşağı yönlü dalgalanmayı risk sayar."),
]

# ------------------------------------------------------------------ veri
def fiyat_cek(yahoo, sure="5y"):
    import yfinance as yf
    h = yf.Ticker(yahoo).history(period=sure, auto_adjust=True)
    if h is None or h.empty:
        raise ValueError(f"{yahoo} için fiyat verisi yok")
    return br._naive(h)

def coingecko(cg_id):
    import requests
    r = requests.get(f"https://api.coingecko.com/api/v3/coins/{cg_id}",
                     params={"localization": "false", "tickers": "false", "community_data": "false", "developer_data": "false"},
                     headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
    r.raise_for_status(); j = r.json(); md = j.get("market_data", {})
    g = lambda k: (md.get(k) or {}).get("usd") if isinstance(md.get(k), dict) else md.get(k)
    yz_ = lambda k: (md.get(k) / 100) if md.get(k) is not None else None
    return {"sira": j.get("market_cap_rank"), "piy_deg": g("market_cap"), "hacim": g("total_volume"),
            "fdv": g("fully_diluted_valuation"), "dolasim": md.get("circulating_supply"), "toplam": md.get("total_supply"),
            "maks": md.get("max_supply"), "ath": g("ath"), "ath_tarih": (md.get("ath_date") or {}).get("usd"),
            "ath_fark": (md.get("ath_change_percentage") or {}).get("usd"), "atl": g("atl"),
            "atl_tarih": (md.get("atl_date") or {}).get("usd"), "d24": yz_("price_change_percentage_24h"),
            "d7": yz_("price_change_percentage_7d"), "d30": yz_("price_change_percentage_30d"), "d1y": yz_("price_change_percentage_1y"),
            "kategori": [c for c in (j.get("categories") or []) if c][:3], "baslangic": j.get("genesis_date"),
            "algoritma": j.get("hashing_algorithm"), "fiyat": g("current_price"), "guncelleme": md.get("last_updated"), "oy": (j.get("sentiment_votes_up_percentage") or 0) / 100 or None}

def kripto_global():
    """CoinGecko /global: toplam piyasa değeri ve dominanslar."""
    import requests
    r = requests.get("https://api.coingecko.com/api/v3/global", headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
    r.raise_for_status(); d = r.json()["data"]; p = d.get("market_cap_percentage", {})
    return {"toplam": d["total_market_cap"].get("usd"), "hacim": d["total_volume"].get("usd"),
            "btc_dom": (p.get("btc") or 0) / 100, "eth_dom": (p.get("eth") or 0) / 100,
            "stable_dom": ((p.get("usdt") or 0) + (p.get("usdc") or 0)) / 100,
            "d24": (d.get("market_cap_change_percentage_24h_usd") or 0) / 100, "coin_sayi": d.get("active_cryptocurrencies")}

def korku_endeksi():
    import requests
    r = requests.get("https://api.alternative.me/fng/", params={"limit": 365}, timeout=10)
    r.raise_for_status(); d = r.json()["data"]
    seri = pd.Series([int(x["value"]) for x in d], index=pd.to_datetime([int(x["timestamp"]) for x in d], unit="s")).sort_index()
    return {"deger": int(d[0]["value"]), "sinif": d[0]["value_classification"],
            "ort30": float(seri.iloc[-30:].mean()), "ort90": float(seri.iloc[-90:].mean()), "seri": seri}

def turev_verisi(sembol):
    """OKX herkese açık API: fonlama oranı, açık pozisyon, long/short oranı (anahtar gerekmez)."""
    import requests
    inst = f"{sembol}-USDT-SWAP"; B = "https://www.okx.com/api/v5"; o = {}
    def al(yol, **p):
        r = requests.get(B + yol, params=p, timeout=8); r.raise_for_status(); j = r.json()
        if str(j.get("code")) != "0": raise ValueError(j.get("msg"))
        return j["data"]
    d = al("/public/funding-rate", instId=inst)[0]; o["fonlama"] = float(d["fundingRate"])
    try:
        hist = al("/public/funding-rate-history", instId=inst, limit=90)
        f = [float(x["realizedRate"] if x.get("realizedRate") else x["fundingRate"]) for x in hist]
        o["fonlama_7g"] = float(np.mean(f[:21])); o["fonlama_30g"] = float(np.mean(f[:90]))
    except Exception:
        o["fonlama_7g"] = o["fonlama_30g"] = None
    try:
        d = al("/public/open-interest", instType="SWAP", instId=inst)[0]
        o["oi_usd"] = float(d["oiUsd"]) if d.get("oiUsd") else None; o["oi_coin"] = float(d.get("oiCcy") or 0) or None
    except Exception:
        o["oi_usd"] = o["oi_coin"] = None
    try:
        d = al("/rubik/stat/contracts/long-short-account-ratio", ccy=sembol, period="1D")
        o["ls"] = float(d[0][1]); o["ls_7g"] = float(np.mean([float(x[1]) for x in d[:7]]))
    except Exception:
        o["ls"] = o["ls_7g"] = None
    o["yillik"] = o["fonlama"] * 3 * 365
    return o

def hash_orani():
    """blockchain.info: Bitcoin ağ hash oranı (madenci sağlığı)."""
    import requests
    r = requests.get("https://api.blockchain.info/charts/hash-rate", params={"timespan": "1year", "format": "json", "sampled": "true"}, timeout=10)
    r.raise_for_status(); v = r.json()["values"]
    s = pd.Series([x["y"] for x in v], index=pd.to_datetime([x["x"] for x in v], unit="s")).resample("D").mean().interpolate()
    ma30, ma60 = s.rolling(30).mean(), s.rolling(60).mean()
    return {"son": float(s.iloc[-1]), "d1y": float(s.iloc[-1] / s.iloc[0] - 1), "ribbon": bool(ma30.iloc[-1] >= ma60.iloc[-1]),
            "seri": s}

KORKU_TR = {"Extreme Fear": "Aşırı korku", "Fear": "Korku", "Neutral": "Nötr", "Greed": "Açgözlülük", "Extreme Greed": "Aşırı açgözlülük"}

# ------------------------------------------------------------------ analiz
def mevsimsellik(k):
    ay = k.resample("ME").last().pct_change().dropna()
    if len(ay) < 24:
        return None
    df = pd.DataFrame({"r": ay.values, "ay": ay.index.month})
    g = df.groupby("ay")["r"]
    return pd.DataFrame({"ort": g.mean(), "pozitif": g.apply(lambda x: (x > 0).mean()), "n": g.size()}).reindex(range(1, 13))

def degerleme_bantlari(k, kripto, kod):
    """Bilançosu olmayan varlıklar için fiyat bantlarına dayalı 'model değer' tahmini."""
    o = {"yontemler": [], "lr": None}; p = float(k.iloc[-1])
    ma200 = k.rolling(200).mean()
    if len(k) >= 200:
        o["ma200"] = float(ma200.iloc[-1])
        mayer = (k / ma200).dropna()
        o["mayer_seri"] = mayer
        o["yontemler"].append(("200 günlük ortalama (Mayer = 1)", o["ma200"], 0.30,
                               "Fiyatın uzun vadeli denge noktası kabul edilen 200 günlük ortalama."))
    w = k.resample("W").last()
    if len(w) >= 200:
        w200 = w.rolling(200).mean(); o["ma200w"] = float(w200.iloc[-1])
        oran = (w / w200).dropna()
        if len(oran) >= 52:
            med = float(oran.median()); o["w200_oran"] = med
            o["yontemler"].append(("200 haftalık trend", o["ma200w"] * med, 0.30,
                                   f"200 haftalık ortalama × tarihsel medyan oran ({ond(med, 2)}). Döngü tabanını ve normalini gösterir."))
    else:
        o["ma200w"] = None
    if kripto and len(k) >= 3 * 365:
        t0 = pd.Timestamp("2009-01-03") if kod.split("/")[0] == "BTC" else k.index[0] - pd.Timedelta(days=60)
        gun = np.array((k.index - t0).days, dtype=float); y = np.log10(k.values)
        b, a = np.polyfit(np.log10(gun), y, 1)
        uyum = a + b * np.log10(gun); art = y - uyum; sd = float(art.std())
        gun_s = float((k.index[-1] - t0).days); adil = 10 ** (a + b * np.log10(gun_s))
        o["lr"] = {"a": a, "b": b, "sd": sd, "t0": t0, "adil": adil, "z": float(art[-1] / sd) if sd else None,
                   "alt": adil * 10 ** (-sd), "ust": adil * 10 ** sd, "alt2": adil * 10 ** (-2 * sd), "ust2": adil * 10 ** (2 * sd),
                   "yil": len(k) / 365}
        o["yontemler"].append(("Log-regresyon (güç yasası)", adil, 0.40 if len(k) >= 5 * 365 else 0.25,
                               f"Tüm geçmiş fiyatın zamanla log-log ilişkisinden bulunan eğilim değeri ({len(k) / 365:.0f} yıllık veri)."))
    if not o["yontemler"]:
        o["adil"] = None; return o
    agr = sum(x[2] for x in o["yontemler"])
    o["adil"] = float(10 ** (sum(math.log10(x[1]) * x[2] for x in o["yontemler"]) / agr))
    o["dusuk"] = min(x[1] for x in o["yontemler"]); o["yuksek"] = max(x[1] for x in o["yontemler"])
    o["pot"] = o["adil"] / p - 1
    o["bant"] = 0.25 if kripto else 0.10
    o["etiket"] = ("UCUZ BÖLGEDE" if o["pot"] > o["bant"] else "PAHALI BÖLGEDE" if o["pot"] < -o["bant"] else "MAKUL BÖLGEDE")
    o["guven"] = "YÜKSEK" if len(o["yontemler"]) >= 3 and len(k) >= 5 * 365 else "ORTA" if len(o["yontemler"]) >= 2 else "DÜŞÜK"
    return o

def analiz(kod, fiyat_fn=None, fx_fn=None, haber_fn=None, cg_fn=None, korku_fn=None, kiyas_fn=None,
           global_fn=None, turev_fn=None, hash_fn=None, detay=True):
    kod = kod.upper().strip()
    borsa_kul = None; parite = None; seri_tl_gercek = None; seri_usd_gercek = None
    fx = (fx_fn or br.kur_cek)()
    if kod in VARLIKLAR:
        yahoo, ad, tur, cg_id, sorgu = VARLIKLAR[kod]
    else:
        yahoo, ad, tur, cg_id, sorgu = None, None, "kripto", None, None
    baz = kod
    if tur == "kripto":
        baz, parite, borsa = KR.coz(kod)
        yahoo = yahoo or f"{baz}-USD"
        if not cg_id or not ad:
            try: cg_id, ad = KR.cg_id(baz)
            except Exception: cg_id, ad = None, baz
        ad = ad or baz; sorgu = sorgu or f"{ad} kripto"
        kod = KR.kod_yap(baz, parite, borsa)
    fiyat_fn = fiyat_fn or fiyat_cek
    if kod == "GRAMALTIN":
        try: o = fiyat_fn("GC=F", "10y")
        except Exception: o = fiyat_fn("GC=F")
        if fiyat_fn is fiyat_cek: o, _ = br.canli_guncelle(o, "GC=F")
        f = fx.reindex(o.index, method="ffill")
        h = o[["Open", "High", "Low", "Close"]].mul(f, axis=0) / 31.1035
        h["Volume"] = o.get("Volume", 0); h = h.dropna(subset=["Close"]); para = "TL"
        zaman = h.index[-1]
    elif tur == "kripto" and fiyat_fn is fiyat_cek:
        # Borsa verisi (Binance / OKX): günlük mumlar canlıdır, son mum o anki fiyatı içerir
        h_usd, borsa_kul = KR.mumlar(baz, "USDT", borsa)
        seri_usd_gercek = h_usd["Close"]
        if parite == "TRY":
            try:
                h, borsa_kul = KR.mumlar(baz, "TRY", borsa); para = "TL"
            except Exception:
                f = fx.reindex(h_usd.index, method="ffill")
                h = h_usd[["Open", "High", "Low", "Close"]].mul(f, axis=0); h["Volume"] = h_usd["Volume"]; para = "TL"
                borsa_kul += " (USDT × USD/TRY)"
        else:
            h = h_usd; para = "USD"
            try: seri_tl_gercek = KR.mumlar(baz, "TRY", borsa)[0]["Close"]
            except Exception: seri_tl_gercek = None
        zaman = dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).replace(tzinfo=None)
    else:
        try: h = fiyat_fn(yahoo, "max" if tur == "kripto" else "10y")
        except Exception: h = fiyat_fn(yahoo)
        para = "TL" if parite == "TRY" else "USD"
        if parite == "TRY":
            f = fx.reindex(h.index, method="ffill"); h = h.copy()
            for c in ("Open", "High", "Low", "Close"): h[c] = h[c] * f
            h = h.dropna(subset=["Close"])
        zaman = h.index[-1]
        if fiyat_fn is fiyat_cek and parite != "TRY":
            h, zaman = br.canli_guncelle(h, yahoo)
    k = h["Close"].dropna()
    m = {"kod": kod, "baz": baz, "parite": parite, "borsa": borsa_kul, "ad": ad, "fiyat_zamani": zaman, "tur": tur, "para": para, "fiyat": float(k.iloc[-1]), "tarih": k.index[-1], "hist": h}
    f_al = fx.reindex(k.index, method="ffill")
    if para == "USD":
        m["seri_tl"] = seri_tl_gercek.dropna() if seri_tl_gercek is not None and len(seri_tl_gercek) > 30 else (k * f_al).dropna()
        m["fiyat_tl"] = float(m["seri_tl"].iloc[-1]); m["seri_usd"] = k
    else:
        m["seri_tl"] = k; m["fiyat_tl"] = float(k.iloc[-1])
        m["seri_usd"] = seri_usd_gercek.dropna() if seri_usd_gercek is not None and len(seri_usd_gercek) > 30 else (k / f_al).dropna()
    m["kur"] = float(fx.iloc[-1])
    def getiri(s):
        son = s.index[-1]; out = {"1G": float(s.iloc[-1] / s.iloc[-2] - 1) if len(s) > 1 else None}
        for e, g_ in (("1H", 7), ("1A", 30), ("3A", 91), ("6A", 182), ("1Y", 365), ("3Y", 1095)):
            x = s[s.index <= son - pd.Timedelta(days=g_)]
            out[e] = float(s.iloc[-1] / x.iloc[-1] - 1) if len(x) else None
        yb = s[s.index < pd.Timestamp(son.year, 1, 1)]
        out["YBB"] = float(s.iloc[-1] / yb.iloc[-1] - 1) if len(yb) else None
        return out
    m["r_usd"] = getiri(m["seri_usd"]); m["r_tl"] = getiri(m["seri_tl"])
    m["r_reel"] = reel(m["r_tl"].get("1Y"))
    # trend
    ma50, ma200 = k.rolling(50).mean(), k.rolling(200).mean()
    m["ma50"] = float(ma50.iloc[-1]) if len(k) >= 50 else None
    m["ma200"] = float(ma200.iloc[-1]) if len(k) >= 200 else None
    m["mayer"] = m["fiyat"] / m["ma200"] if m["ma200"] else None
    m["ma200_egim"] = float(ma200.iloc[-1] / ma200.iloc[-21] - 1) if len(k) >= 221 else None
    m["rsi"] = float(br.rsi(k).iloc[-1])
    e12, e26 = k.ewm(span=12).mean(), k.ewm(span=26).mean(); macd = e12 - e26
    m["macd_poz"] = bool(macd.iloc[-1] > macd.ewm(span=9).mean().iloc[-1])
    gunluk = k.pct_change().dropna()
    yil_gun = 365 if tur == "kripto" else 252
    m["vol"] = float(gunluk.iloc[-yil_gun:].std() * math.sqrt(yil_gun))
    son3 = k.iloc[-3 * yil_gun:]
    m["max_dd"] = float((son3 / son3.cummax() - 1).min())
    m["zirve"] = float(son3.max()); m["zirveden"] = m["fiyat"] / m["zirve"] - 1
    m["zirve_tum"] = float(k.max()); m["dip_tum"] = float(k.min())
    r1 = m["r_usd"].get("1Y"); g1 = gunluk.iloc[-yil_gun:]
    asagi = g1[g1 < 0].std() * math.sqrt(yil_gun) if (g1 < 0).sum() > 10 else None
    m["sharpe"] = (r1 - 0.04) / m["vol"] if r1 is not None and m["vol"] else None
    m["sortino"] = (r1 - 0.04) / asagi if r1 is not None and asagi else None
    m["deger"] = degerleme_bantlari(k, tur == "kripto", kod)
    m["adil"] = m["deger"].get("adil"); m["potansiyel"] = m["deger"].get("pot")
    m["dip52"], m["zirve52"] = float(k.iloc[-yil_gun:].min()), float(k.iloc[-yil_gun:].max())
    m["seviye"] = br.seviyeler(h)
    try:
        m["akis"] = br.para_akisi(h) if "Volume" in h and h["Volume"].iloc[-60:].sum() > 0 else None
    except Exception:
        m["akis"] = None
    m["yabanci"] = None
    m["mevsim"] = mevsimsellik(k)
    # korelasyonlar ve göreli güç
    kiyas = {"S&P 500": "^GSPC", "Altın": "GC=F", "Dolar endeksi": "DX-Y.NYB", "Bitcoin": "BTC-USD"}
    if tur == "kripto": kiyas["Ethereum"] = "ETH-USD"
    ref = "Bitcoin" if tur == "kripto" and baz != "BTC" else "S&P 500"
    ku = m["seri_usd"]  # korelasyonlar dolar bazında
    m["beta"] = None; m["ethbtc"] = None; seriler = {}
    kiyas_fn = kiyas_fn or (lambda y: fiyat_fn(y, "2y")["Close"] if fiyat_fn is fiyat_cek else fiyat_fn(y)["Close"])
    kor, gor = {}, {}
    for ad_, y in kiyas.items():
        if y == yahoo or (kod == "GRAMALTIN" and y == "GC=F") or (tur == "kripto" and y == f"{baz}-USD"):
            continue
        try:
            b = kiyas_fn(y).dropna()
            j = pd.concat([ku.pct_change(), b.pct_change()], axis=1, join="inner").dropna().iloc[-252:]
            if len(j) > 60:
                kor[ad_] = float(j.corr().iloc[0, 1])
                if ad_ == ref: m["beta"] = float(j.cov().iloc[0, 1] / j.iloc[:, 1].var())
            seriler[ad_] = b
            b6 = b[b.index <= b.index[-1] - pd.Timedelta(days=182)]
            if len(b6) and m["r_usd"].get("6A") is not None: gor[ad_] = m["r_usd"]["6A"] - float(b.iloc[-1] / b6.iloc[-1] - 1)
        except Exception:
            continue
    m["korelasyon"], m["goreli"] = kor, gor
    if tur == "kripto":
        try:
            e_ = ku if baz == "ETH" else seriler.get("Ethereum"); b_ = ku if baz == "BTC" else seriler.get("Bitcoin")
            if e_ is not None and b_ is not None:
                eb = (e_ / b_.reindex(e_.index, method="ffill")).dropna()
                x = eb[eb.index <= eb.index[-1] - pd.Timedelta(days=90)]
                m["ethbtc"] = {"deger": float(eb.iloc[-1]), "d90": float(eb.iloc[-1] / x.iloc[-1] - 1) if len(x) else None}
        except Exception:
            pass
    m["goreli_ref"] = ref; m["goreli_6a"] = gor.get(ref)
    # kripto / emtia özel
    m["cg"] = m["korku"] = m["global"] = m["turev"] = m["hash"] = None
    if tur == "kripto":
        try: m["cg"] = (cg_fn or coingecko)(cg_id) if cg_id else None
        except Exception:
            try: m["cg"] = KR.cg_kayit(cg_id) if cg_id else None
            except Exception: m["cg"] = None
        try: m["korku"] = (korku_fn or korku_endeksi)()
        except Exception: m["korku"] = None
        try: m["global"] = (global_fn or kripto_global)()
        except Exception: m["global"] = None
        if detay:
            try: m["turev"] = (turev_fn or turev_verisi)(baz)
            except Exception: m["turev"] = None
            if baz == "BTC":
                try: m["hash"] = (hash_fn or hash_orani)()
                except Exception: m["hash"] = None
    m["oran"] = None
    if kod in ("ALTIN", "GUMUS"):
        try:
            a, g_ = fiyat_fn("GC=F")["Close"], fiyat_fn("SI=F")["Close"]
            o_ = (a / g_.reindex(a.index, method="ffill")).dropna()
            m["oran"] = {"ad": "Altın/Gümüş oranı", "deger": float(o_.iloc[-1]), "ort5y": float(o_.mean()),
                         "yorum": "Oran 5 yıllık ortalamasının üzerinde: gümüş altına göre görece ucuz." if o_.iloc[-1] > o_.mean()
                         else "Oran 5 yıllık ortalamasının altında: altın gümüşe göre görece ucuz."}
        except Exception:
            pass
    try:
        m["haber"] = (haber_fn or br.haber_cek)(kod, sorgu)
    except Exception as ex:
        m["haber"] = {"liste": [], "ton": 0, "ozet": "–", "hata": str(ex)[:80]}
    try:
        import bist_teknik as TK
        m["mta"] = TK.analiz_h(kod, ad, h, tur if tur == "kripto" else "emtia", "$" if para == "USD" else "₺")
    except Exception:
        m["mta"] = None
    skorla(m)
    return m

def skorla(m):
    kr = m["tur"] == "kripto"
    v_esik = [0.4, 0.6, 0.8, 1.0] if kr else [0.15, 0.25, 0.35, 0.5]
    rsi = m["rsi"]
    rsi_p = 2 if rsi < 45 else 3 if rsi < 55 else 4 if rsi < 70 else 3
    a = m.get("akis") or {}
    D = {
        "Trend": [("Fiyat / 200G ortalama", yz(m["mayer"] - 1 if m["mayer"] else None), puan(m["mayer"] - 1 if m["mayer"] else None, [-0.15, -0.05, 0.05, 0.15])),
                  ("200G ortalamanın eğimi (1 ay)", yz(m["ma200_egim"]), puan(m["ma200_egim"], [-0.04, -0.01, 0.01, 0.04])),
                  ("50G / 200G ortalama", "50G üstte" if (m["ma50"] or 0) > (m["ma200"] or 1e18) else "50G altta",
                   5.0 if (m["ma50"] or 0) > (m["ma200"] or 1e18) else 1.0 if m["ma200"] else None)],
        "Momentum": [("3 aylık getiri ($)", yz(m["r_usd"].get("3A")), puan(m["r_usd"].get("3A"), [-0.15, -0.05, 0.05, 0.15])),
                     ("6 aylık getiri ($)", yz(m["r_usd"].get("6A")), puan(m["r_usd"].get("6A"), [-0.2, -0.05, 0.1, 0.25])),
                     ("RSI (14)", ond(rsi, 0), float(rsi_p)),
                     ("MACD", "Pozitif" if m["macd_poz"] else "Negatif", 4.0 if m["macd_poz"] else 2.0)],
        "Risk (düşük = iyi)": [("Yıllık volatilite", yz(m["vol"]), puan(m["vol"], v_esik, ters=True)),
                                            ("3 yıllık en büyük düşüş", yz(m["max_dd"]), puan(m["max_dd"], [-0.7, -0.5, -0.3, -0.15])),
                                            ("Sharpe oranı (1 yıl)", ond(m.get("sharpe"), 2), puan(m.get("sharpe"), [-0.5, 0, 0.5, 1.0]))],
        "Para akışı": [("Chaikin para akışı", ond(a.get("cmf"), 2), puan(a.get("cmf"), [-0.15, -0.05, 0.05, 0.15])),
                       ("OBV eğimi", ond(a.get("obv_egim"), 2), puan(a.get("obv_egim"), [-0.3, -0.1, 0.1, 0.3])),
                       ("Yükselen/düşen gün hacmi", kat(a.get("hacim_oran_ud")), puan(a.get("hacim_oran_ud"), [0.7, 0.9, 1.1, 1.4]))] if a else [],
        "Göreli güç": [(f"6 ay, {m['goreli_ref']}'a göre", yz(m["goreli_6a"]), puan(m["goreli_6a"], [-0.2, -0.05, 0.05, 0.2]))],
    }
    if kr:
        dg = m.get("deger") or {}; lr = dg.get("lr") or {}; cg = m.get("cg") or {}; kk = m.get("korku") or {}; tv = m.get("turev") or {}
        D = {"Değerleme (bantlar)": [
                 ("Model değere göre potansiyel", yz(dg.get("pot")), puan(dg.get("pot"), [-0.3, -0.1, 0.1, 0.3])),
                 ("Mayer çarpanı", ond(m["mayer"], 2), puan(m["mayer"], [0.8, 1.0, 1.3, 1.8], ters=True)),
                 ("Log-regresyon sapması (σ)", ond(lr.get("z"), 2), puan(lr.get("z"), [-1.0, -0.3, 0.5, 1.2], ters=True))],
             **{k_: v for k_, v in D.items() if k_ in ("Trend", "Momentum", "Risk (düşük = iyi)")},
             "Likidite ve arz": [
                 ("Hacim / piyasa değeri", yz(br.bol(cg.get("hacim"), cg.get("piy_deg"))), puan(br.bol(cg.get("hacim"), cg.get("piy_deg")), [0.01, 0.025, 0.05, 0.1])),
                 ("Piyasa değeri / FDV", yz(br.bol(cg.get("piy_deg"), cg.get("fdv"))), puan(br.bol(cg.get("piy_deg"), cg.get("fdv")), [0.5, 0.7, 0.85, 0.97])),
                 ("Piyasa değeri sırası", str(cg.get("sira") or "–"), puan(cg.get("sira"), [3, 10, 20, 50], ters=True))],
             "Duyarlılık ve akış": [
                 ("Korku & Açgözlülük (ters)", str(kk.get("deger") or "–"), puan(kk.get("deger"), [25, 45, 60, 75], ters=True)),
                 ("Fonlama oranı (yıllık)", yz(tv.get("yillik")), puan(tv.get("yillik"), [0.0, 0.08, 0.15, 0.3], ters=True)),
                 *D["Para akışı"][:2]],
             "Göreli güç": D["Göreli güç"]}
    D = {k_: [x for x in v if x[2] is not None] for k_, v in D.items()}
    m["saglik_detay"] = {k_: v for k_, v in D.items() if v}
    m["saglik"] = {k_: ort([x[2] for x in v]) for k_, v in m["saglik_detay"].items()}
    s_ = ort(list(m["saglik"].values())); m["genel_skor"] = s_
    m["gorunum"] = ("–" if s_ is None else "GÜÇLÜ POZİTİF" if s_ >= 3.8 else "POZİTİF" if s_ >= 3.2 else
                    "NÖTR" if s_ >= 2.6 else "NEGATİF" if s_ >= 2.0 else "GÜÇLÜ NEGATİF")

# ------------------------------------------------------------------ sade dil
def durum_gorunum(g):
    return "iyi" if "POZİTİF" in g else "zayif" if "NEGATİF" in g else "orta"

def tek_bakista(m):
    S = []; enf = PARAM["ENFLASYON"]; dg = m.get("deger") or {}
    if dg.get("adil"):
        sym = "$" if m["para"] == "USD" else "₺"
        S.append(("Fiyat bantlara göre ucuz mu, pahalı mı?", f"Model değer bandının ortası {tl(dg['adil'])} {sym}; fiyata göre {yz(dg['pot'])} fark var "
                  f"({kucuk(dg['etiket'])}).", "iyi" if dg["pot"] > dg["bant"] else "zayif" if dg["pot"] < -dg["bant"] else "orta"))
    if m["ma200"]:
        ust = m["fiyat"] > m["ma200"]
        S.append(("Ana eğilim ne yönde?", ("Fiyat 200 günlük ortalamasının üzerinde; uzun vadeli eğilim yukarı." if ust else
                  "Fiyat 200 günlük ortalamasının altında; uzun vadeli eğilim aşağı."), "iyi" if ust else "zayif"))
    r3 = m["r_usd"].get("3A")
    if r3 is not None:
        S.append(("Son aylarda güç kazanıyor mu?", f"Son 3 ayda dolar bazında {yz(abs(r3), 0)} {'yükseldi' if r3 >= 0 else 'düştü'}; RSI {ond(m['rsi'], 0)}" +
                  (" (aşırı alım bölgesi)." if m["rsi"] > 70 else " (aşırı satım bölgesi)." if m["rsi"] < 30 else "."),
                  "iyi" if r3 > 0.05 else "zayif" if r3 < -0.05 else "orta"))
    kr = m["tur"] == "kripto"; v = m["vol"]
    seviye = ("düşük" if v < (0.4 if kr else 0.15) else "orta" if v < (0.7 if kr else 0.3) else "yüksek")
    S.append(("Ne kadar riskli?", f"Fiyat yılda ortalama ±{yz(v, 0)} dalgalanıyor ({seviye} oynaklık); son 3 yılda zirveden en fazla {yz(-m['max_dd'], 0)} düştü.",
              "iyi" if seviye == "düşük" else "orta" if seviye == "orta" else "zayif"))
    if m["mayer"]:
        x = m["mayer"]
        S.append(("Ortalamasına göre pahalı mı?", f"Fiyat 200 günlük ortalamanın {ond(x, 2)} katı. " +
                  ("Ortalamanın çok üzerinde; geri çekilme riski artmış olabilir." if x > 1.5 else "Ortalamaya göre hafif yüksek." if x > 1.1 else
                   "Ortalamaya yakın." if x > 0.9 else "Ortalamanın altında; görece ucuz bölgede."),
                  "zayif" if x > 1.5 else "orta" if x > 1.1 else "iyi"))
    a = m.get("akis")
    if a:
        S.append(("Alıcılar mı, satıcılar mı baskın?", {"GÜÇLÜ GİRİŞ": "Alıcılar belirgin şekilde baskın.", "GİRİŞ": "Alıcılar hafif baskın.",
                  "NÖTR": "Denge var.", "ÇIKIŞ": "Satıcılar hafif baskın.", "GÜÇLÜ ÇIKIŞ": "Satıcılar belirgin şekilde baskın."}[a["ozet"]],
                  "iyi" if a["puan"] > 0 else "zayif" if a["puan"] < 0 else "orta"))
    if m["r_reel"] is not None:
        S.append(("TL bazında enflasyonu yendi mi?", f"Son 1 yılda TL bazında {yz(m['r_tl']['1Y'], 0)} getiri; enflasyondan arındırılmış {yz(m['r_reel'], 0)}.",
                  "iyi" if m["r_reel"] > 0.05 else "orta" if m["r_reel"] > -0.05 else "zayif"))
    ms = m.get("mevsim")
    if ms is not None:
        ay = dt.date.today().month; r_ = ms.loc[ay]
        if not pd.isna(r_["ort"]):
            S.append(("Mevsimsel olarak bu ay nasıl?", f"Geçmiş yıllarda {AYLAR[ay - 1]} ayında ortalama {yz(r_['ort'])} değişim; yılların {yz(r_['pozitif'], 0)}'inde yükseliş.",
                      "iyi" if r_["ort"] > 0.01 else "zayif" if r_["ort"] < -0.01 else "orta"))
    cg = m.get("cg") or {}
    if cg.get("piy_deg") and cg.get("fdv"):
        o = cg["piy_deg"] / cg["fdv"]
        S.append(("Yeni arz baskısı var mı?", f"Arzın yaklaşık {yz(o, 0)}'i piyasada. " + ("Seyrelme riski düşük." if o > 0.9 else
                  "Kilitli/basılacak arz orta düzeyde; zamanla satış baskısı yaratabilir." if o > 0.6 else
                  "Arzın önemli bölümü henüz piyasada değil; ileride ciddi seyrelme riski var."), "iyi" if o > 0.9 else "orta" if o > 0.6 else "zayif"))
    tv = m.get("turev") or {}
    if tv.get("yillik") is not None:
        f = tv["yillik"]
        S.append(("Kaldıraçlı işlemciler ne yapıyor?", f"Vadeli işlemlerde fonlama oranı yıllık {yz(f)}. " +
                  ("Uzun pozisyonlar çok kalabalık; ani tasfiye riski var." if f > 0.3 else "Hafif iyimser, normal seviyede." if f > 0 else
                   "Kısa pozisyonlar ağır basıyor; kalabalık açığa satış ani yükselişleri tetikleyebilir."),
                  "zayif" if f > 0.3 else "iyi" if f < 0 else "orta"))
    gl = m.get("global") or {}
    if gl.get("btc_dom") and m["tur"] == "kripto":
        eb = (m.get("ethbtc") or {}).get("d90")
        alt = eb is not None and eb > 0.05 and gl["btc_dom"] < 0.55
        S.append(("Piyasada para nereye akıyor?", f"Bitcoin dominansı {yz(gl['btc_dom'], 1)}" + (f", ETH/BTC son 90 günde {yz(eb)}" if eb is not None else "") + ". " +
                  ("Altcoinlere doğru bir kayma var (altcoin sezonu belirtisi)." if alt else "Para ağırlıkla Bitcoin'de; altcoinler için ortam daha zor." if gl["btc_dom"] > 0.55 else "Belirgin bir rotasyon yok."),
                  "iyi" if (alt or m["kod"] == "BTC" and gl["btc_dom"] > 0.55) else "orta"))
    if m.get("korku"):
        kd = m["korku"]["deger"]
        S.append(("Kripto piyasasının havası nasıl?", f"Korku ve Açgözlülük Endeksi {kd} ({KORKU_TR.get(m['korku']['sinif'], m['korku']['sinif'])}). " +
                  ("Aşırı açgözlülük dönemleri genellikle risklidir." if kd >= 75 else "Aşırı korku dönemleri tarihsel olarak fırsat da olabilmiştir." if kd <= 25 else ""),
                  "zayif" if kd >= 75 else "iyi" if kd <= 25 else "orta"))
    return S

def sade_ozet(m):
    g = m["gorunum"]
    t = {"GÜÇLÜ POZİTİF": "güçlü ve olumlu", "POZİTİF": "olumlu", "NÖTR": "kararsız", "NEGATİF": "olumsuz", "GÜÇLÜ NEGATİF": "belirgin şekilde olumsuz"}.get(g, "belirsiz")
    r1 = m["r_usd"].get("1Y")
    return (f"{m['ad']} için teknik ve piyasa göstergelerinin genel görünümü <b>{t}</b> (skor {ond(m['genel_skor'], 1)}/5). "
            + (f"Son 1 yılda dolar bazında {yz(r1, 0)}, TL bazında {yz(m['r_tl'].get('1Y'), 0)} değişti. " if r1 is not None else "")
            + "Emtia ve kriptoların bilançosu olmadığı için bu değerlendirme fiyat davranışına dayanır; ani haber ve politika değişikliklerine açıktır.")

def ipuclari(m):
    g, z = [], []
    if m["ma200"]:
        (g if m["fiyat"] > m["ma200"] else z).append(f"Fiyat 200 günlük ortalamanın {'üzerinde' if m['fiyat'] > m['ma200'] else 'altında'}.")
    if (m["ma50"] or 0) > (m["ma200"] or 1e18): g.append("50 günlük ortalama 200 günlüğün üzerinde (altın kesişim bölgesi).")
    elif m["ma200"]: z.append("50 günlük ortalama 200 günlüğün altında (ölüm kesişimi bölgesi).")
    if m["rsi"] > 70: z.append(f"RSI {ond(m['rsi'], 0)}: aşırı alım bölgesi, kısa vadeli düzeltme riski.")
    if m["rsi"] < 30: g.append(f"RSI {ond(m['rsi'], 0)}: aşırı satım bölgesi, tepki yükselişi gelebilir.")
    if m["mayer"] and m["mayer"] > 1.5: z.append(f"Fiyat 200G ortalamanın {ond(m['mayer'], 2)} katı; ortalamadan çok uzaklaşmış.")
    if m["zirveden"] > -0.05: g.append("Son 3 yılın zirvesine çok yakın.")
    if m["zirveden"] < -0.4: z.append(f"Son 3 yılın zirvesinin {yz(-m['zirveden'], 0)} altında.")
    a = m.get("akis") or {}
    if a.get("puan", 0) > 0: g.append(f"Hacim bazlı para akışı olumlu ({kucuk(a['ozet'])}).")
    if a.get("puan", 0) < 0: z.append(f"Hacim bazlı para akışı olumsuz ({kucuk(a['ozet'])}).")
    if m["goreli_6a"] is not None:
        (g if m["goreli_6a"] > 0 else z).append(f"Son 6 ayda {m['goreli_ref']}'a göre {yz(abs(m['goreli_6a']), 0)} {'daha iyi' if m['goreli_6a'] > 0 else 'daha kötü'}.")
    if m["r_reel"] is not None:
        (g if m["r_reel"] > 0 else z).append(f"TL bazında 1 yıllık reel getiri {yz(m['r_reel'])}.")
    if m.get("oran"): g.append(m["oran"]["yorum"])
    dg = m.get("deger") or {}; lr = dg.get("lr") or {}
    if dg.get("pot") is not None and dg["pot"] > dg["bant"]: g.append(f"Fiyat model değer bandının {yz(dg['pot'], 0)} altında (ucuz bölge).")
    if dg.get("pot") is not None and dg["pot"] < -dg["bant"]: z.append(f"Fiyat model değer bandının {yz(-dg['pot'], 0)} üzerinde (pahalı bölge).")
    if lr.get("z") is not None and lr["z"] > 1.2: z.append(f"Uzun vadeli log-regresyon eğiliminin {ond(lr['z'], 1)}σ üzerinde; döngü zirvesi riskine dikkat.")
    if lr.get("z") is not None and lr["z"] < -0.8: g.append(f"Uzun vadeli eğilimin {ond(-lr['z'], 1)}σ altında; tarihsel olarak birikim bölgesi.")
    cg = m.get("cg") or {}
    if cg.get("piy_deg") and cg.get("fdv") and cg["piy_deg"] / cg["fdv"] < 0.6: z.append(f"Arzın yalnızca {yz(cg['piy_deg'] / cg['fdv'], 0)}'i dolaşımda; seyrelme riski.")
    if cg.get("maks") and cg.get("dolasim") and cg["dolasim"] / cg["maks"] > 0.9: g.append(f"Arzın {yz(cg['dolasim'] / cg['maks'], 0)}'i basılmış; sınırlı ve öngörülebilir arz.")
    tv = m.get("turev") or {}
    if tv.get("yillik") is not None and tv["yillik"] > 0.3: z.append(f"Fonlama oranı yüksek (yıllık {yz(tv['yillik'], 0)}); kaldıraçlı alıcılar kalabalık.")
    if tv.get("yillik") is not None and tv["yillik"] < 0: g.append("Fonlama oranı negatif; piyasa aşırı karamsar, ani yükseliş (short squeeze) riski.")
    hs = m.get("hash") or {}
    if hs: (g if hs["ribbon"] else z).append("Ağ hash oranı " + ("yükselişte; madenciler güçlü." if hs["ribbon"] else "zayıflıyor (madenci kapitülasyonu sinyali)."))
    kk = m.get("korku") or {}
    if kk.get("deger") is not None and kk["deger"] <= 25: g.append(f"Korku endeksi {kk['deger']} (aşırı korku); tarihsel olarak alım fırsatı dönemleri.")
    if kk.get("deger") is not None and kk["deger"] >= 75: z.append(f"Korku endeksi {kk['deger']} (aşırı açgözlülük); düzeltme riski.")
    hb = m.get("haber") or {}
    if hb.get("ozet") == "OLUMLU": g.append("Son haberlerin tonu olumlu.")
    if hb.get("ozet") == "OLUMSUZ": z.append("Son haberlerin tonu olumsuz.")
    m["guclu"], m["zayif"] = g[:6], z[:6]

def genel_degerlendirme(m):
    B = []; dg = m.get("deger") or {}
    if dg.get("adil"):
        B.append(("Değerleme", "Model değer bandı ortası " + tl(dg["adil"]) + " (" + ", ".join(a.split(" (")[0] + ": " + tl(d) for a, d, *_ in dg["yontemler"]) + "). "
                  f"Fiyata göre fark {yz(dg['pot'])}, {kucuk(dg['etiket'])}; güven {kucuk(dg['guven'])}."))
    B.append(("Trend", f"Fiyat {tl(m['fiyat'])} {'$' if m['para'] == 'USD' else '₺'}; 200 günlük ortalama {tl(m['ma200'])}, Mayer çarpanı {ond(m['mayer'], 2)}. "
              f"Trend puanı {ond(m['saglik'].get('Trend'), 1)}/5."))
    B.append(("Momentum", f"3 ay {yz(m['r_usd'].get('3A'))}, 6 ay {yz(m['r_usd'].get('6A'))}, RSI {ond(m['rsi'], 0)}, MACD {'pozitif' if m['macd_poz'] else 'negatif'}."))
    B.append(("Risk", f"Yıllık volatilite {yz(m['vol'])}, 3 yıllık en büyük düşüş {yz(m['max_dd'])}, zirveden uzaklık {yz(m['zirveden'])}."))
    sv = m.get("seviye") or {}
    if sv.get("destek") or sv.get("direnc"):
        B.append(("Seviyeler", (f"En yakın destek {tl(sv['destek'][0][0])}" if sv.get("destek") else "") +
                  (f", en yakın direnç {tl(sv['direnc'][0][0])}." if sv.get("direnc") else ".")))
    ak = br.akis_yorumlari(m)
    if ak: B.append(("Para akışı", " ".join(x.replace("<b>", "").replace("</b>", "") for x in ak[:2])))
    if m["korelasyon"]:
        en = max(m["korelasyon"].items(), key=lambda x: abs(x[1]))
        B.append(("Korelasyon", f"Son 1 yılda en güçlü ilişki {en[0]} ile ({ond(en[1], 2)}). " + ", ".join(f"{k}: {ond(v, 2)}" for k, v in m["korelasyon"].items()) + "."))
    tv = m.get("turev") or {}
    if tv:
        B.append(("Türev piyasalar", f"Fonlama oranı yıllık {yz(tv.get('yillik'))}" + (f", açık pozisyon ${tl(tv['oi_usd'])}" if tv.get("oi_usd") else "")
                  + (f", hesap bazında long/short oranı {ond(tv['ls'], 2)}" if tv.get("ls") else "") + "."))
    if m.get("cg"):
        c_ = m["cg"]
        B.append(("Kripto piyasa verisi", f"Piyasa değeri sırası {c_.get('sira')}, piyasa değeri ${tl(c_.get('piy_deg'))}; tüm zamanların zirvesinin {yz(abs((c_.get('ath_fark') or 0) / 100), 0)} altında."))
    if m.get("korku"):
        B.append(("Piyasa duyarlılığı", f"Korku ve Açgözlülük Endeksi {m['korku']['deger']} ({KORKU_TR.get(m['korku']['sinif'], m['korku']['sinif'])}), 30 günlük ortalama {ond(m['korku']['ort30'], 0)}."))
    hb = m.get("haber") or {}
    if hb.get("liste"): B.append(("Haberler", f"Son {len(hb['liste'])} haberin tonu {kucuk(hb['ozet'])}."))
    if m.get("zayif"): B.append(("Öne çıkan riskler", " ".join(m["zayif"][:3])))
    B.append(("Sonuç", sade_ozet(m).replace("<b>", "").replace("</b>", "") + " Bu bir model çıktısıdır, yatırım tavsiyesi değildir."))
    return B

# ------------------------------------------------------------------ grafikler
def g_mevsim(m):
    ms = m.get("mevsim")
    if ms is None: return None
    fig, ax = plt.subplots(figsize=(7.5, 2.4))
    v = ms["ort"].fillna(0) * 100
    renk = [C["yesil"] if x >= 0 else C["kirmizi"] for x in v]
    bugun = dt.date.today().month - 1
    bars = ax.bar(AYLAR, v, color=renk, alpha=0.85)
    bars[bugun].set_edgecolor(C["lac"]); bars[bugun].set_linewidth(1.6)
    for i, (x, p) in enumerate(zip(v, ms["pozitif"].fillna(0))):
        ax.text(i, x + (0.3 if x >= 0 else -0.3), f"%{p * 100:.0f}", ha="center", va="bottom" if x >= 0 else "top", fontsize=6.5, color=C["gri"])
    ax.axhline(0, color=C["gri"], lw=0.6); ax.set_ylabel("Ort. aylık getiri %")
    ax.set_title("Mevsimsellik: Aylara göre ortalama getiri (çubuk üstü: yükseliş görülen yılların oranı)", loc="left")
    return _png(fig)

def g_tl_usd(m):
    s1, s2 = m["seri_usd"].iloc[-756:], m["seri_tl"].iloc[-756:]
    fig, ax = plt.subplots(figsize=(7.5, 2.4))
    ax.plot(s1.index, s1 / s1.iloc[0] * 100, color=C["mavi"], lw=1.3, label="Dolar bazlı")
    ax.plot(s2.index, s2 / s2.iloc[0] * 100, color=C["tur"], lw=1.3, label="TL bazlı")
    ax.axhline(100, color=C["gri"], lw=0.6); ax.legend(fontsize=7)
    ax.set_title("3 yıllık performans: Dolar ve TL bazında (başlangıç = 100)", loc="left")
    return _png(fig)

def g_logbant(m):
    """Logaritmik fiyat + güç yasası eğilimi ve ±1σ/±2σ bantları + 200 haftalık ortalama."""
    dg = m.get("deger") or {}; lr = dg.get("lr"); k = m["seri_usd"] if m["para"] == "USD" else m["hist"]["Close"]
    if not lr: return None
    k = k.dropna(); gun = np.array((k.index - lr["t0"]).days, dtype=float)
    uy = 10 ** (lr["a"] + lr["b"] * np.log10(gun)); sd = lr["sd"]
    fig, ax = plt.subplots(figsize=(7.5, 3.3))
    ax.fill_between(k.index, uy * 10 ** (-2 * sd), uy * 10 ** (2 * sd), color=C["acik"], alpha=0.25, lw=0, label="±2σ bandı")
    ax.fill_between(k.index, uy * 10 ** (-sd), uy * 10 ** sd, color=C["acik"], alpha=0.55, lw=0, label="±1σ bandı")
    ax.plot(k.index, uy, color=C["mavi"], lw=1.1, ls="--", label="Eğilim (adil)")
    w = k.resample("W").last(); w200 = w.rolling(200).mean()
    if w200.notna().sum() > 10: ax.plot(w200.index, w200, color=C["tur"], lw=1.1, label="200 haftalık ort.")
    ax.plot(k.index, k, color=C["lac"], lw=1.0, label="Fiyat")
    ax.set_yscale("log"); ax.legend(fontsize=6.5, ncol=5, loc="upper left", frameon=False)
    ax.set_title("Uzun vadeli değer bantları (log ölçek)", loc="left")
    return _png(fig)

def g_mayer(m):
    ms = (m.get("deger") or {}).get("mayer_seri")
    if ms is None or len(ms) < 100: return None
    ms = ms.iloc[-4 * 365:]
    fig, ax = plt.subplots(figsize=(7.5, 2.3))
    ax.axhspan(0, 0.8, color=C["yesil"], alpha=0.10); ax.axhspan(2.4, max(2.6, ms.max() * 1.05), color=C["kirmizi"], alpha=0.10)
    ax.plot(ms.index, ms, color=C["lac"], lw=1.1)
    for y_, r_ in ((0.8, C["yesil"]), (1.0, C["gri"]), (2.4, C["kirmizi"])): ax.axhline(y_, color=r_, lw=0.8, ls="--")
    ax.set_ylim(max(0, ms.min() * 0.9), max(2.6, ms.max() * 1.05))
    ax.set_title("Mayer çarpanı (fiyat / 200G ort.) · 0,8 altı tarihsel ucuz, 2,4 üstü aşırı ısınma", loc="left")
    return _png(fig)

def g_korku(m):
    s_ = (m.get("korku") or {}).get("seri")
    if s_ is None or len(s_) < 20: return None
    fig, ax = plt.subplots(figsize=(7.5, 2.1))
    for a_, b_, r_ in ((0, 25, C["kirmizi"]), (25, 45, C["tur"]), (45, 55, C["gri"]), (55, 75, C["yesil"]), (75, 100, C["yesil"])):
        ax.axhspan(a_, b_, color=r_, alpha=0.07 if b_ != 100 else 0.14)
    ax.plot(s_.index, s_, color=C["lac"], lw=1.1); ax.plot(s_.index, s_.rolling(30).mean(), color=C["mavi"], lw=1.0, ls="--")
    ax.set_ylim(0, 100); ax.set_title("Korku & Açgözlülük Endeksi (1 yıl) · 25 altı aşırı korku, 75 üstü aşırı açgözlülük", loc="left")
    return _png(fig)

# ------------------------------------------------------------------ PDF
def pdf_olustur(m, dosya):
    W = A4[0] - 3.0 * cm; PW = (W - 10) / 2
    ipuclari(m); kr = m["tur"] == "kripto"
    tur_ad = "Kripto Para Raporu" if kr else "Emtia Raporu"
    sayfa = sayfa_cizici(m["kod"], tur_ad, f"{dt.date.today():%d.%m.%Y}", kapak_yuk=4.7 * cm)
    doc = SimpleDocTemplate(dosya, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.6 * cm,
                            bottomMargin=1.4 * cm, title=f"{m['ad']} {tur_ad}")
    E = []; sym = "$" if m["para"] == "USD" else "₺"; dg = m.get("deger") or {}; cg = m.get("cg") or {}
    gl = m.get("global") or {}; tv = m.get("turev") or {}; kk = m.get("korku") or {}

    # ---------- SAYFA 1
    alt = f"{tur_ad}  ·  {m['kod']}" + (f"  ·  Veri: {m['borsa']}" if m.get("borsa") else "") + (f"  ·  Piyasa değeri sırası #{cg['sira']}" if cg.get("sira") else "") + \
          f"  ·  {m['tarih']:%d.%m.%Y}  ·  Fiyatlar: {'ABD doları (USDT)' if m['para'] == 'USD' else 'Türk lirası'}"
    E += TS.pro_kapak(m["ad"], alt, f"{tl(m['fiyat'])} {sym}", m["r_usd"].get("1G") if m["para"] == "USD" else m["r_tl"].get("1G"), W,
                      rozet=f"GENEL GÖRÜNÜM: {m['gorunum']}",
                      guncel=f"Fiyat: {TS.zaman_metni(m.get('fiyat_zamani'))} (TSİ)"
                             + (f"  ·  Piyasa verisi: {str(cg.get('guncelleme') or '')[:16].replace('T', ' ')} UTC" if cg.get("guncelleme") else ""))
    adil_b = "Model değer bandı" if kr else "Ortalamalara göre konum"
    nyon = len(dg.get("yontemler") or [])
    sol = TS.AdilDegerGostergesi(m["fiyat"], dg.get("adil"), dg.get("dusuk"), dg.get("yuksek"), sym, bant=dg.get("bant", 0.25), gen=PW, yuk=150,
                                 baslik=adil_b, alt_not=f"{nyon} bant modelinin ortalaması · güven: {kucuk(dg.get('guven', '–'))}")
    sag = TS.SkorGostergesi(m["genel_skor"], m["gorunum"], m["saglik"], gen=PW, yuk=150, baslik="Skor kartı")
    E.append(TS.yan_yana(sol, sag, W)); E.append(Spacer(1, 8))
    _gor = AN.varlik_gorus(m)[0]
    E.append(TS.ozet_paneli("Yatırım özeti", AN.varlik_baslik(m), _gor, AN.varlik_ozeti(m, kisa=True), W)); E.append(Spacer(1, 4))
    E.append(Paragraph("Temel göstergeler", ST["h2"]))
    if kr:
        ml = [("Piyasa değeri", f"${tl(cg.get('piy_deg'))}" if cg.get("piy_deg") else "–"),
              ("24 saatlik hacim", f"${tl(cg.get('hacim'))}" if cg.get("hacim") else "–"),
              ("Tam seyreltilmiş değer (FDV)", f"${tl(cg.get('fdv'))}" if cg.get("fdv") else "–"),
              ("Piyasa değeri / FDV", yz(br.bol(cg.get("piy_deg"), cg.get("fdv")), 0)),
              ("Fiyat (TL)", f"{tl(m['fiyat_tl'])} ₺"), ("1 yıllık getiri ($)", yz(m["r_usd"].get("1Y"))),
              ("Yılbaşından beri ($)", yz(m["r_usd"].get("YBB"))), ("Yıllık volatilite", yz(m["vol"], 0)),
              ("Sharpe / Sortino", f"{ond(m.get('sharpe'), 2)} / {ond(m.get('sortino'), 2)}"),
              (f"Beta ({m['goreli_ref']})", ond(m.get("beta"), 2)),
              ("Bitcoin dominansı", yz(gl.get("btc_dom"), 1)), ("Korku & Açgözlülük", f"{kk['deger']} · {KORKU_TR.get(kk['sinif'], kk['sinif'])}" if kk else "–")]
    else:
        ml = [("Fiyat (TL)", f"{tl(m['fiyat_tl'])} ₺"), ("1 yıllık getiri ($)", yz(m["r_usd"].get("1Y"))),
              ("Yılbaşından beri ($)", yz(m["r_usd"].get("YBB"))), ("1 yıl TL reel getiri", yz(m["r_reel"])),
              ("Yıllık volatilite", yz(m["vol"], 0)), ("Sharpe / Sortino", f"{ond(m.get('sharpe'), 2)} / {ond(m.get('sortino'), 2)}"),
              ("Mayer çarpanı", ond(m["mayer"], 2)), ("RSI (14)", ond(m["rsi"], 0)),
              ("Zirveden uzaklık (3Y)", yz(m["zirveden"])), (f"Beta ({m['goreli_ref']})", ond(m.get("beta"), 2))]
        if m.get("oran"): ml.append((m["oran"]["ad"], ond(m["oran"]["deger"], 1)))
    E.append(TS.metrik_listesi(ml, W)); E.append(Spacer(1, 8))
    r1 = TS.AralikCubugu("52 haftalık aralık", m["dip52"], m["zirve52"], m["fiyat"], gen=PW, sembol=sym)
    if cg.get("ath") and cg.get("atl"):
        r2 = TS.AralikCubugu("Tüm zamanlar (dip – zirve)", cg["atl"], cg["ath"], m["fiyat"], gen=PW, sembol=sym, ort=dg.get("adil"), ort_etiket="Model")
    else:
        r2 = TS.AralikCubugu("Tüm veri (dip – zirve)", m["dip_tum"], m["zirve_tum"], m["fiyat"], gen=PW, sembol=sym, ort=dg.get("adil"), ort_etiket="Model")
    E.append(TS.yan_yana(r1, r2, W)); E.append(Spacer(1, 6))

    # ---------- SAYFA 2: yönetici özeti
    E.append(PageBreak())
    E.append(TS.ozet_paneli("Yönetici özeti", AN.varlik_baslik(m), _gor, AN.varlik_ozeti(m), W,
                            alt_bilgi="Genel görünüm; skor kartı (%70) ve uzun vadeli değer bandına göre konumun (%30) birleşimidir."))
    E.append(Paragraph("Yatırım tezi", ST["h2"])); _p, _n = AN.varlik_tezi(m); E.append(TS.tez_tablosu(_p, _n, W))
    _t = m.get("mta")
    if _t and _t.get("puan") is not None:
        import bist_teknik_rapor as TKR
        _tb = [Paragraph("Teknik görünüm (günlük · haftalık · aylık)", ST["h2"]), TKR.gosterge_satiri(_t, W), Spacer(1, 5),
               Paragraph(TS.esc(AN.teknik_ozet(_t)), ST["p"])]
        _ts = AN.teknik_senaryo(_t)
        if _ts:
            _tb += [Spacer(1, 5), TS.senaryo_kartlari([(b_, f"Hedef {h_}", "", f"Tetikleyici: {t_}. {i_}.") for b_, t_, h_, i_ in _ts], W)]
        E.append(KeepTogether(_tb))
    _k, _r = AN.varlik_katalizor_risk(m)
    E.append(KeepTogether([Paragraph("Katalizörler ve riskler", ST["h2"]), TS.iki_liste("İzlenecek katalizörler", _k, "Başlıca riskler", _r, W)]))
    E.append(KeepTogether([Paragraph("Temel göstergeler karnesi", ST["h2"]), trafik_listesi(AN.karne_etiketle(tek_bakista(m), m.get("mta")), W)]))
    E.append(KeepTogether([Paragraph("Analist notları", ST["h2"]), TS.sinyal_listesi(m["guclu"], m["zayif"], W, n=6)]))
    n = 0
    def bolum(baslik, gerek=8):
        nonlocal n; n += 1; E.append(CondPageBreak(gerek * cm)); E.append(Bolum(n, baslik, W))

    # ---------- Değerleme
    if dg.get("adil"):
        bolum("Değerleme: Uzun vadeli fiyat bantları" if kr else "Konum: Uzun vadeli ortalamalara göre fiyat", 12)
        E.append(bilgi_kutusu("Analist yorumu:", f"Bilançosu olmayan {'kripto paralar' if kr else 'emtialar'} için 'adil değer' yerine uzun vadeli fiyat bantları kullanılır. "
                              f"Bantların ortası <b>{tl(dg['adil'])} {sym}</b>; fiyat buna göre <b>{yz(dg['pot'])}</b> farkla <b>{kucuk(dg['etiket'])}</b>.", W))
        E.append(Spacer(1, 4))
        v = [["Model", f"Değer ({sym})", "Fark", "Ağırlık", "Açıklama"]]
        tw = sum(x[2] for x in dg["yontemler"])
        for ad_, d_, w_, ac in dg["yontemler"]:
            v.append([Paragraph(ad_, ST["hucre"]), tl(d_), yz(d_ / m["fiyat"] - 1), yz(w_ / tw, 0), Paragraph(ac, ST["hucre"])])
        v.append(["Model değer (geometrik ort.)", tl(dg["adil"]), yz(dg["pot"]), "%100", Paragraph(f"Güven: <b>{kucuk(dg['guven'])}</b>", ST["hucre"])])
        E.append(TS.tablo(v, [W * .24, W * .13, W * .1, W * .09, W * .44], kalin_son=True, font=7.5, hizala_sol=(0, 4)))
        lr = dg.get("lr")
        if lr:
            E.append(Spacer(1, 4))
            bt = [["Log-regresyon bandı", f"Fiyat ({sym})", "Fiyata uzaklık"], ["Aşırı ısınma (+2σ)", tl(lr["ust2"]), yz(lr["ust2"] / m["fiyat"] - 1)],
                  ["Üst bant (+1σ)", tl(lr["ust"]), yz(lr["ust"] / m["fiyat"] - 1)], ["Eğilim (adil)", tl(lr["adil"]), yz(lr["adil"] / m["fiyat"] - 1)],
                  ["Alt bant (−1σ)", tl(lr["alt"]), yz(lr["alt"] / m["fiyat"] - 1)], ["Birikim bölgesi (−2σ)", tl(lr["alt2"]), yz(lr["alt2"] / m["fiyat"] - 1)]]
            E.append(TS.yan_yana(TS.tablo(bt, [PW * .48, PW * .27, PW * .25], font=7.4),
                                 Paragraph(f"Fiyat, uzun vadeli eğilimin <b>{ond(lr['z'], 2)} standart sapma</b> {'üzerinde' if (lr['z'] or 0) > 0 else 'altında'}. "
                                           "Tarihsel olarak +1σ üstü dönemler aşırı ısınmaya, −1σ altı dönemler birikim fırsatlarına denk gelmiştir. "
                                           f"Model {lr['yil']:.0f} yıllık veriye dayanır; genç projelerde güvenilirliği düşüktür.", ST["kucuk"]), W))
            g = g_logbant(m)
            if g: E += [Spacer(1, 6), _img(g, W, 3.3 / 7.5)]
        gm = g_mayer(m)
        if gm: E += [Spacer(1, 4), _img(gm, W, 2.3 / 7.5)]

    # ---------- Kripto: arz ve piyasa yapısı
    if kr and (cg or gl):
        bolum("Arz ve piyasa yapısı (tokenomik)", 9)
        sat = []
        if cg.get("piy_deg") and cg.get("fdv"):
            o = cg["piy_deg"] / cg["fdv"]
            sat.append(f"Piyasa değeri FDV'nin {yz(o, 0)}'i: " + ("arzın neredeyse tamamı dolaşımda." if o > 0.9 else "kilitli/basılacak tokenlar ileride satış baskısı yaratabilir."))
        if cg.get("hacim") and cg.get("piy_deg"):
            t_ = cg["hacim"] / cg["piy_deg"]; sat.append(f"Günlük hacim piyasa değerinin {yz(t_, 1)}'i: " + ("likidite güçlü." if t_ > 0.05 else "likidite yeterli." if t_ > 0.02 else "likidite zayıf; büyük işlemler fiyatı oynatabilir."))
        E.append(bilgi_kutusu("Analist yorumu:", " ".join(sat) or "Arz verisi sınırlı.", W))
        E.append(Spacer(1, 4))
        v = [["Gösterge", "Değer"], ["Piyasa değeri sırası", f"#{cg.get('sira') or '–'}"], ["Piyasa değeri", f"${tl(cg.get('piy_deg'))}"],
             ["Tam seyreltilmiş değer (FDV)", f"${tl(cg.get('fdv'))}" if cg.get("fdv") else "–"], ["24 saatlik hacim", f"${tl(cg.get('hacim'))}"],
             ["Dolaşımdaki arz", tl(cg.get("dolasim"), 0)], ["Toplam arz", tl(cg.get("toplam"), 0) if cg.get("toplam") else "–"],
             ["Maksimum arz", tl(cg.get("maks"), 0) if cg.get("maks") else "Sınırsız"],
             ["Tüm zamanların zirvesi", f"${tl(cg.get('ath'))} · {str(cg.get('ath_tarih') or '')[:10]}"],
             ["Tüm zamanların dibi", f"${tl(cg.get('atl'))} · {str(cg.get('atl_tarih') or '')[:10]}" if cg.get("atl") else "–"]]
        if cg.get("kategori"): v.append(["Kategori", ", ".join(cg["kategori"])[:48]])
        if cg.get("algoritma"): v.append(["Konsensüs / algoritma", str(cg["algoritma"])])
        v2 = [["Genel kripto piyasası", "Değer"], ["Toplam piyasa değeri", f"${tl(gl.get('toplam'))}" if gl else "–"],
              ["24 saatlik değişim", yz(gl.get("d24"))], ["Bitcoin dominansı", yz(gl.get("btc_dom"), 1)], ["Ethereum dominansı", yz(gl.get("eth_dom"), 1)],
              ["Stablecoin payı", yz(gl.get("stable_dom"), 1)], ["ETH/BTC (90 gün)", yz((m.get("ethbtc") or {}).get("d90"))],
              ["Fiyat değişimi 7g / 30g", f"{yz(cg.get('d7'))} / {yz(cg.get('d30'))}"]]
        E.append(TS.yan_yana(TS.tablo(v, [PW * .55, PW * .45], font=7.3), TS.tablo(v2, [PW * .6, PW * .4], font=7.3), W))
        if cg.get("dolasim") and (cg.get("maks") or cg.get("toplam")):
            E += [Spacer(1, 8), TS.AralikCubugu("Basılmış arz oranı", 0, cg.get("maks") or cg["toplam"], cg["dolasim"], gen=W * 0.6, deger_etiket="Dolaşımda")]

    # ---------- Duyarlılık ve türevler
    if kr and (kk or tv or m.get("hash")):
        bolum("Duyarlılık, türevler ve ağ", 9)
        E.append(bilgi_kutusu("Bu ne demek?", "Fonlama oranı, vadeli işlemlerde alıcıların satıcılara ödediği ücrettir; çok yüksekse kaldıraçlı alıcılar "
                              "kalabalıktır ve ani tasfiye riski artar. Long/short oranı 1'in üzerindeyse hesapların çoğu yükselişe oynuyor demektir. "
                              "Korku endeksi aşırı uçlarda genellikle tersine çalışır.", W, "turkuaz"))
        v = [["Gösterge", "Değer", "Yorum"]]
        if kk: v.append(["Korku & Açgözlülük", f"{kk['deger']} ({KORKU_TR.get(kk['sinif'], kk['sinif'])})",
                         Paragraph(f"30 gün ort. {ond(kk.get('ort30'), 0)}" + (f", 90 gün ort. {ond(kk.get('ort90'), 0)}" if kk.get("ort90") else ""), ST["hucre"])])
        if tv:
            v.append(["Fonlama oranı (8 saatlik)", yz(tv.get("fonlama"), 4), Paragraph(f"Yıllık karşılığı {yz(tv.get('yillik'))}; 7 gün ort. {yz(tv.get('fonlama_7g'), 4)}", ST["hucre"])])
            if tv.get("oi_usd") or tv.get("oi_coin"): v.append(["Açık pozisyon (OKX)", f"${tl(tv['oi_usd'])}" if tv.get("oi_usd") else tl(tv["oi_coin"]), Paragraph("Tek borsa verisidir; yön göstergesi olarak kullanın.", ST["hucre"])])
            if tv.get("ls"): v.append(["Long/short hesap oranı", ond(tv["ls"], 2), Paragraph(f"7 gün ort. {ond(tv.get('ls_7g'), 2)}; 2'nin üzeri kalabalık uzun pozisyon.", ST["hucre"])])
        hs = m.get("hash") or {}
        if hs: v.append(["Ağ hash oranı", f"{hs['son'] / 1e6:,.0f} EH/s".replace(",", "."), Paragraph(f"1 yılda {yz(hs['d1y'])}; hash ribbon {'olumlu' if hs['ribbon'] else 'olumsuz (kapitülasyon)'}.", ST["hucre"])])
        if len(v) > 1: E += [Spacer(1, 4), TS.tablo(v, [W * .28, W * .2, W * .52], font=7.5, hizala_sol=(0, 2))]
        g = g_korku(m)
        if g: E += [Spacer(1, 6), _img(g, W, 2.1 / 7.5)]
        if not tv: E.append(Paragraph("Türev verisi bu sunucudan alınamadı (borsa API'si erişimi kısıtlamış olabilir).", ST["kucuk"]))

    # ---------- Fiyat ve trend
    bolum("Fiyat performansı ve trend", 10)
    sv = m.get("seviye") or {}
    E.append(bilgi_kutusu("Analist yorumu:", f"Fiyat 200 günlük ortalamanın {'üzerinde' if m['ma200'] and m['fiyat'] > m['ma200'] else 'altında'}. "
                          + (f"En yakın destek {tl(sv['destek'][0][0])}, en yakın direnç {tl(sv['direnc'][0][0])} {sym}." if sv.get("destek") and sv.get("direnc") else ""), W))
    E.append(Spacer(1, 4)); E.append(_img(br.g_fiyat(m["hist"], None, m["kod"], sv), W, 5.6 / 7.5))
    per = [["Dönem", "1G", "1H", "1A", "3A", "6A", "YBB", "1Y", "3Y"],
           ["Dolar bazlı"] + [yz(m["r_usd"].get(k_)) for k_ in ("1G", "1H", "1A", "3A", "6A", "YBB", "1Y", "3Y")],
           ["TL bazlı"] + [yz(m["r_tl"].get(k_)) for k_ in ("1G", "1H", "1A", "3A", "6A", "YBB", "1Y", "3Y")]]
    E += [Spacer(1, 4), TS.tablo(per, [W * .16] + [W * .105] * 8, font=7.4)]
    if sv:
        v = [["Seviye", f"Fiyat ({sym})", "Uzaklık", "Güç"]]
        for lv, n_ in reversed(sv["direnc"]): v.append(["Direnç", tl(lv), yz(lv / m["fiyat"] - 1), "•" * min(n_, 5)])
        v.append(["Son fiyat", tl(m["fiyat"]), "–", ""])
        for lv, n_ in sv["destek"]: v.append(["Destek", tl(lv), yz(lv / m["fiyat"] - 1), "•" * min(n_, 5)])
        E.append(KeepTogether([Paragraph("Destek ve direnç seviyeleri", ST["h2"]), TS.tablo(v, [W * .2, W * .2, W * .15, W * .15], font=7.6)]))
    E.append(Spacer(1, 6)); E.append(_img(g_tl_usd(m), W, 2.4 / 7.5))

    # ---------- Skor kartı
    bolum("Skor kartı: Kategori bazında değerlendirme", 10)
    sr = sorted(m["saglik"].items(), key=lambda x: x[1])
    E.append(bilgi_kutusu("Analist yorumu:", f"Varlık {len(sr)} alanda 1–5 arası puanlandı. En güçlü alan <b>{kucuk(sr[-1][0])}</b>, en zayıf alan <b>{kucuk(sr[0][0])}</b>.", W))
    E.append(Spacer(1, 4)); E.append(_img(br.g_saglik(m, "Skor kartı – Kategoriler (1–5)"), W * 0.92, (0.42 * len(m["saglik"]) + 0.5) / 7.5))
    for kat_, liste in m["saglik_detay"].items():
        v = [[f"{kat_}  –  {ond(m['saglik'][kat_], 2)}/5", "Değer", "Puan"]] + [[a, b_, ond(p_, 0)] for a, b_, p_ in liste]
        t = TS.tablo(v, [W * .6, W * .25, W * .15], font=7.6)
        k_, a_ = TS.durum_rengi(TS.puan_durum(m["saglik"][kat_]))
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), a_), ("TEXTCOLOR", (0, 0), (-1, 0), k_)]))
        E.append(KeepTogether([t, Spacer(1, 5)]))

    # ---------- Risk
    bolum("Risk ve diğer piyasalarla ilişki", 9)
    E.append(bilgi_kutusu("Bu ne demek?", "Sharpe oranı, alınan her birim riske karşılık elde edilen getiriyi ölçer (1'in üzeri iyi). Sortino yalnızca aşağı yönlü "
                          "oynaklığı dikkate alır. Beta, karşılaştırılan varlık %1 hareket ettiğinde bu varlığın ortalama ne kadar hareket ettiğini gösterir. "
                          "Korelasyon +1'e yakınsa birlikte hareket ederler.", W, "turkuaz"))
    v = [["Gösterge", "Değer"], ["Yıllık volatilite", yz(m["vol"])], ["3 yıllık en büyük düşüş", yz(m["max_dd"])],
         ["Sharpe (1 yıl)", ond(m.get("sharpe"), 2)], ["Sortino (1 yıl)", ond(m.get("sortino"), 2)], [f"Beta ({m['goreli_ref']})", ond(m.get("beta"), 2)],
         ["Son 3 yılın zirvesi", f"{tl(m['zirve'])} {sym}"], ["Zirveden uzaklık", yz(m["zirveden"])],
         ["52 haftalık aralık", f"{tl(m['dip52'])} – {tl(m['zirve52'])}"]]
    kv = [["Korelasyon (1 yıl, günlük)", "Değer"]] + [[k_, ond(x, 2)] for k_, x in m["korelasyon"].items()]
    E += [Spacer(1, 4), TS.yan_yana(TS.tablo(v, [PW * .6, PW * .4], font=7.6), TS.tablo(kv, [PW * .65, PW * .35], font=7.6), W)]

    # ---------- Para akışı
    if m.get("akis"):
        bolum("Para akışı ve hacim analizi", 10)
        for x in br.akis_yorumlari(m): E.append(Paragraph("• " + x, ST["madde"]))
        ga = br.g_akis(m["hist"], m)
        if ga: E += [Spacer(1, 4), _img(ga, W, (1.55 * 2 + 0.4) / 7.5)]

    # ---------- Mevsimsellik
    gm = g_mevsim(m)
    if gm:
        bolum("Mevsimsellik", 8)
        E.append(bilgi_kutusu("Bu ne demek?", "Geçmiş yıllarda her ay ortalama ne kadar değişim olduğunu gösterir. Çerçeveli çubuk içinde "
                              "bulunduğumuz aydır. Geçmiş eğilimler geleceği garanti etmez.", W, "turkuaz"))
        E += [Spacer(1, 4), _img(gm, W, 2.4 / 7.5)]

    if m.get("oran"):
        bolum("Emtia oranları", 5)
        E.append(TS.tablo([["Gösterge", "Değer"], [m["oran"]["ad"], ond(m["oran"]["deger"], 1)], ["5 yıllık ortalama", ond(m["oran"]["ort5y"], 1)]], [W * .45, W * .3], font=7.6))
        E.append(Spacer(1, 3)); E.append(bilgi_kutusu("Yorum:", m["oran"]["yorum"], W, "turkuaz"))

    # ---------- Haberler
    hb = m.get("haber") or {}
    if hb.get("liste"):
        bolum(f"Haberler (genel ton: {kucuk(hb['ozet'])})", 6)
        v = [["Tarih", "Başlık", "Kaynak"]] + [[f"{x['tarih']:%d.%m}" if x["tarih"] else "–", Paragraph(("↑ " if x["ton"] > 0 else "↓ " if x["ton"] < 0 else "") + TS.esc(x["baslik"][:140]), ST["hucre"]), x["kaynak"][:22]] for x in hb["liste"]]
        E.append(TS.tablo(v, [W * .1, W * .68, W * .22], hizala_sol=(0, 1, 2), font=7.4))

    # ---------- Genel değerlendirme
    E.append(PageBreak()); n += 1; E.append(Bolum(n, "Sonuç ve analist değerlendirmesi", W))
    E.append(TS.ozet_paneli("Sonuç", AN.varlik_baslik(m), _gor, AN.varlik_ozeti(m), W))
    E.append(Paragraph("Başlıklar itibarıyla değerlendirme", ST["h2"]))
    for bas, metin in genel_degerlendirme(m):
        E.append(KeepTogether([Paragraph(bas, ST["h2"]), Paragraph(TS.esc(metin), ST["p"])]))
    E.append(Spacer(1, 8)); n += 1; E.append(Bolum(n, "Terimler sözlüğü ve uyarılar", W))
    E.append(TS.tablo([["Terim", "Sade anlatım"]] + [[a, Paragraph(b, ST["hucre"])] for a, b in SOZLUK_VARLIK + (SOZLUK_KRIPTO if kr else [])],
                      [W * .28, W * .72], hizala_sol=(0, 1), font=7.6))
    E.append(Spacer(1, 6))
    E.append(Paragraph("Veriler: Yahoo Finance (fiyat), CoinGecko (piyasa ve arz), alternative.me (korku endeksi), OKX herkese açık API (türevler), "
                       "blockchain.info (hash oranı), Google Haberler. Emtia fiyatları vadeli işlem kontratlarına dayanır. Değer bantları istatistiksel "
                       "modellerdir, gerçek değer garantisi vermez. Bu rapor otomatik bir model çıktısıdır; yatırım danışmanlığı kapsamında değildir.", ST["kucuk"]))
    doc.build(E, onFirstPage=sayfa, onLaterPages=sayfa)
    return dosya

def rapor(kod, klasor=".", **kw):
    m = analiz(kod, **kw)
    dosya = os.path.join(klasor, f"{m['kod'].replace('/', '-').replace('@', '_')}_Rapor_{dt.date.today():%Y%m%d}.pdf")
    pdf_olustur(m, dosya)
    return dosya, m

def varsayilan_liste(kripto_adet=50):
    em = [k for k, v in VARLIKLAR.items() if v[2] == "emtia"]
    try:
        kr = KR.bulten_kodlari("USDT")[:kripto_adet]
    except Exception:
        kr = [k for k, v in VARLIKLAR.items() if v[2] == "kripto"]
    return em + kr


def tara(kodlar=None, **kw):
    """Emtia ve kriptoları skorlar; özet satırlar döndürür."""
    if kw.get("fiyat_fn") is None: kw.setdefault("cg_fn", KR.cg_kayit)
    satir, hata = [], {}
    fiyat_fn = kw.pop("fiyat_fn", None) or fiyat_cek
    on_bellek = {}
    def kiyas_fn(y):  # karşılaştırma serilerini bir kez indir
        if y not in on_bellek: on_bellek[y] = fiyat_fn(y)["Close"]
        return on_bellek[y]
    kw.setdefault("kiyas_fn", kiyas_fn)
    try:
        fx = (kw.pop("fx_fn", None) or br.kur_cek)(); kw["fx_fn"] = lambda: fx
    except Exception:
        pass
    try:
        kk = (kw.pop("korku_fn", None) or korku_endeksi)(); kw["korku_fn"] = lambda: kk
    except Exception:
        kw["korku_fn"] = lambda: None
    try:
        gg = (kw.pop("global_fn", None) or kripto_global)(); kw["global_fn"] = lambda: gg
    except Exception:
        kw["global_fn"] = lambda: None
    kw["detay"] = False
    for k in (kodlar or varsayilan_liste()):
        try:
            m = analiz(k, fiyat_fn=fiyat_fn, haber_fn=lambda *a: {"liste": [], "ton": 0, "ozet": "–"}, **kw)
            satir.append({"Kod": m["kod"], "Ad": m["ad"], "Tür": m["tur"], "Fiyat": m["fiyat"], "Para": m["para"],
                          "Skor": m["genel_skor"], "Görünüm": m["gorunum"], "1A $": m["r_usd"].get("1A"),
                          "YBB $": m["r_usd"].get("YBB"), "1Y $": m["r_usd"].get("1Y"), "1Y TL reel": m["r_reel"],
                          "Volatilite": m["vol"], "Mayer": m["mayer"], "RSI": m["rsi"],
                          "Model değer": m.get("adil"), "Bant farkı": m.get("potansiyel"), "Sharpe": m.get("sharpe"),
                          "Para akışı": (m.get("akis") or {}).get("ozet")})
        except Exception as ex:
            hata[k] = str(ex)[:100]
    return satir, hata
