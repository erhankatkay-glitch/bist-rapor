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
from tasarim import ST, Bolum, kart_izgarasi, bilgi_kutusu, trafik_listesi, kapak, sayfa_cizici
import bist_rapor as br
from bist_rapor import tl, yz, kat, ond, puan, ort, kucuk, reel, _png, _img, PARAM

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
    return {"sira": j.get("market_cap_rank"), "piy_deg": g("market_cap"), "hacim": g("total_volume"),
            "dolasim": md.get("circulating_supply"), "maks": md.get("max_supply"), "ath": g("ath"),
            "ath_tarih": (md.get("ath_date") or {}).get("usd"), "ath_fark": (md.get("ath_change_percentage") or {}).get("usd")}

def korku_endeksi():
    import requests
    r = requests.get("https://api.alternative.me/fng/", params={"limit": 30}, timeout=10)
    r.raise_for_status(); d = r.json()["data"]
    return {"deger": int(d[0]["value"]), "sinif": d[0]["value_classification"],
            "ort30": float(np.mean([int(x["value"]) for x in d]))}

KORKU_TR = {"Extreme Fear": "Aşırı korku", "Fear": "Korku", "Neutral": "Nötr", "Greed": "Açgözlülük", "Extreme Greed": "Aşırı açgözlülük"}

# ------------------------------------------------------------------ analiz
def mevsimsellik(k):
    ay = k.resample("ME").last().pct_change().dropna()
    if len(ay) < 24:
        return None
    df = pd.DataFrame({"r": ay.values, "ay": ay.index.month})
    g = df.groupby("ay")["r"]
    return pd.DataFrame({"ort": g.mean(), "pozitif": g.apply(lambda x: (x > 0).mean()), "n": g.size()}).reindex(range(1, 13))

def analiz(kod, fiyat_fn=None, fx_fn=None, haber_fn=None, cg_fn=None, korku_fn=None, kiyas_fn=None):
    kod = kod.upper()
    yahoo, ad, tur, cg_id, sorgu = VARLIKLAR[kod]
    fiyat_fn = fiyat_fn or fiyat_cek
    fx = (fx_fn or br.kur_cek)()
    if kod == "GRAMALTIN":
        o = fiyat_fn("GC=F"); f = fx.reindex(o.index, method="ffill")
        h = o[["Open", "High", "Low", "Close"]].mul(f, axis=0) / 31.1035
        h["Volume"] = o.get("Volume", 0); h = h.dropna(subset=["Close"]); para = "TL"
    else:
        h = fiyat_fn(yahoo); para = "USD"
    k = h["Close"].dropna()
    m = {"kod": kod, "ad": ad, "tur": tur, "para": para, "fiyat": float(k.iloc[-1]), "tarih": k.index[-1], "hist": h}
    f_al = fx.reindex(k.index, method="ffill")
    if para == "USD":
        m["seri_tl"] = (k * f_al).dropna(); m["fiyat_tl"] = float(m["seri_tl"].iloc[-1]); m["seri_usd"] = k
    else:
        m["seri_tl"] = k; m["fiyat_tl"] = float(k.iloc[-1]); m["seri_usd"] = (k / f_al).dropna()
    m["kur"] = float(fx.iloc[-1])
    def getiri(s):
        son = s.index[-1]; out = {}
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
    kiyas_fn = kiyas_fn or (lambda y: fiyat_fn(y, "2y")["Close"] if fiyat_fn is fiyat_cek else fiyat_fn(y)["Close"])
    kor, gor = {}, {}
    for ad_, y in kiyas.items():
        if y == yahoo or (kod == "GRAMALTIN" and y == "GC=F"):
            continue
        try:
            b = kiyas_fn(y).dropna()
            j = pd.concat([k.pct_change(), b.pct_change()], axis=1, join="inner").dropna().iloc[-252:]
            if len(j) > 60: kor[ad_] = float(j.corr().iloc[0, 1])
            b6 = b[b.index <= b.index[-1] - pd.Timedelta(days=182)]
            if len(b6) and m["r_usd"].get("6A") is not None: gor[ad_] = m["r_usd"]["6A"] - float(b.iloc[-1] / b6.iloc[-1] - 1)
        except Exception:
            continue
    m["korelasyon"], m["goreli"] = kor, gor
    ref = "Bitcoin" if tur == "kripto" and kod != "BTC" else "S&P 500"
    m["goreli_ref"] = ref; m["goreli_6a"] = gor.get(ref)
    # kripto / emtia özel
    m["cg"] = m["korku"] = None
    if tur == "kripto":
        try: m["cg"] = (cg_fn or coingecko)(cg_id)
        except Exception: m["cg"] = None
        try: m["korku"] = (korku_fn or korku_endeksi)()
        except Exception: m["korku"] = None
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
        "Risk (düşük risk = yüksek puan)": [("Yıllık volatilite", yz(m["vol"]), puan(m["vol"], v_esik, ters=True)),
                                            ("3 yıllık en büyük düşüş", yz(m["max_dd"]), puan(m["max_dd"], [-0.7, -0.5, -0.3, -0.15]))],
        "Para akışı": [("Chaikin para akışı", ond(a.get("cmf"), 2), puan(a.get("cmf"), [-0.15, -0.05, 0.05, 0.15])),
                       ("OBV eğimi", ond(a.get("obv_egim"), 2), puan(a.get("obv_egim"), [-0.3, -0.1, 0.1, 0.3])),
                       ("Yükselen/düşen gün hacmi", kat(a.get("hacim_oran_ud")), puan(a.get("hacim_oran_ud"), [0.7, 0.9, 1.1, 1.4]))] if a else [],
        "Göreli güç": [(f"6 ay, {m['goreli_ref']}'a göre", yz(m["goreli_6a"]), puan(m["goreli_6a"], [-0.2, -0.05, 0.05, 0.2]))],
    }
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
    S = []; enf = PARAM["ENFLASYON"]
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
    hb = m.get("haber") or {}
    if hb.get("ozet") == "OLUMLU": g.append("Son haberlerin tonu olumlu.")
    if hb.get("ozet") == "OLUMSUZ": z.append("Son haberlerin tonu olumsuz.")
    m["guclu"], m["zayif"] = g[:5], z[:5]

def genel_degerlendirme(m):
    B = []
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

# ------------------------------------------------------------------ PDF
def pdf_olustur(m, dosya):
    W = A4[0] - 3.0 * cm
    ipuclari(m)
    tur_ad = "Kripto Para Raporu" if m["tur"] == "kripto" else "Emtia Raporu"
    sayfa = sayfa_cizici(m["kod"], tur_ad, f"{dt.date.today():%d.%m.%Y}", kapak_yuk=4.7 * cm)
    doc = SimpleDocTemplate(dosya, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.6 * cm,
                            bottomMargin=1.4 * cm, title=f"{m['ad']} {tur_ad}")
    E = []; sym = "$" if m["para"] == "USD" else "₺"
    E += kapak(m["ad"], f"{tur_ad}  ·  {m['tarih']:%d.%m.%Y}  ·  Fiyatlar: {'ABD doları' if m['para'] == 'USD' else 'Türk lirası'}",
               f"Genel görünüm: {m['gorunum']}", durum_gorunum(m["gorunum"]), W)
    pr = lambda x: TS.R["yesil"] if (x or 0) > 0 else TS.R["kirmizi"] if (x or 0) < 0 else TS.R["murekkep"]
    kartlar = [("Son fiyat", f"{tl(m['fiyat'])} {sym}", f"≈ {tl(m['fiyat_tl'])} ₺" if m["para"] == "USD" else f"≈ ${tl(m['fiyat'] / m['kur'])}"),
               ("Genel skor", f"{ond(m['genel_skor'], 1)} / 5", kucuk(m["gorunum"]), TS.durum_rengi(durum_gorunum(m["gorunum"]))[0]),
               ("1 yıl ($)", yz(m["r_usd"].get("1Y")), f"TL: {yz(m['r_tl'].get('1Y'))}", pr(m["r_usd"].get("1Y"))),
               ("Yılbaşından beri", yz(m["r_usd"].get("YBB")), "dolar bazında", pr(m["r_usd"].get("YBB"))),
               ("Volatilite", yz(m["vol"]), "yıllık oynaklık"),
               ("Zirveden uzaklık", yz(m["zirveden"]), "son 3 yıl", pr(m["zirveden"] + 0.0001 if m["zirveden"] > -0.05 else -1)),
               ("Mayer çarpanı", ond(m["mayer"], 2), "fiyat / 200G ortalama"),
               ("RSI", ond(m["rsi"], 0), "aşırı alım >70, satım <30")]
    if m.get("cg") and m["cg"].get("piy_deg"):
        kartlar[6] = ("Piyasa değeri", f"${tl(m['cg']['piy_deg'])}", f"sıra: {m['cg'].get('sira')}")
    if m.get("oran"):
        kartlar[6] = ("Altın/Gümüş oranı", ond(m["oran"]["deger"], 1), f"5Y ort. {ond(m['oran']['ort5y'], 1)}")
    E.append(kart_izgarasi(kartlar, W)); E.append(Spacer(1, 4))
    E.append(bilgi_kutusu("Kısaca:", sade_ozet(m), W))
    E.append(Paragraph("Tek bakışta", ST["h2"])); E.append(trafik_listesi(tek_bakista(m), W))
    E.append(Paragraph("Öne çıkanlar", ST["h2"]))
    gl = [Paragraph(f'<font color="#16A34A"><b>↑</b></font>&nbsp; {x}', ST["madde"]) for x in m["guclu"]] or [Paragraph("–", ST["madde"])]
    zl = [Paragraph(f'<font color="#DC2626"><b>↓</b></font>&nbsp; {x}', ST["madde"]) for x in m["zayif"]] or [Paragraph("–", ST["madde"])]
    n = max(len(gl), len(zl)); gl += [""] * (n - len(gl)); zl += [""] * (n - len(zl))
    t = Table([[Paragraph('<font name="DVB" color="#16A34A">Olumlu</font>', ST["hucreB"]),
                Paragraph('<font name="DVB" color="#DC2626">Dikkat</font>', ST["hucreB"])]] + list(zip(gl, zl)), colWidths=[W / 2, W / 2])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (0, 0), 1.2, TS.R["yesil"]),
                           ("LINEBELOW", (1, 0), (1, 0), 1.2, TS.R["kirmizi"]), ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
    E.append(t)

    # 1 Fiyat ve trend
    E.append(PageBreak()); E.append(Bolum(1, "Fiyat ve trend", W))
    sv = m.get("seviye") or {}
    E.append(bilgi_kutusu("Kısaca:", f"Fiyat 200 günlük ortalamanın {'üzerinde' if m['ma200'] and m['fiyat'] > m['ma200'] else 'altında'}. "
                          + (f"En yakın destek {tl(sv['destek'][0][0])}, en yakın direnç {tl(sv['direnc'][0][0])} {sym}." if sv.get("destek") and sv.get("direnc") else ""), W))
    E.append(Spacer(1, 4)); E.append(_img(br.g_fiyat(m["hist"], None, m["kod"], sv), W, 5.6 / 7.5))
    per = [["Dönem", "1H", "1A", "3A", "6A", "YBB", "1Y", "3Y"],
           ["Dolar bazlı"] + [yz(m["r_usd"].get(k_)) for k_ in ("1H", "1A", "3A", "6A", "YBB", "1Y", "3Y")],
           ["TL bazlı"] + [yz(m["r_tl"].get(k_)) for k_ in ("1H", "1A", "3A", "6A", "YBB", "1Y", "3Y")]]
    E += [Spacer(1, 4), tablo_ := TS.tablo(per, [W * .16] + [W * .12] * 7, font=7.6)]
    if sv:
        v = [["Seviye", f"Fiyat ({sym})", "Uzaklık", "Güç"]]
        for lv, n_ in reversed(sv["direnc"]): v.append(["Direnç", tl(lv), yz(lv / m["fiyat"] - 1), "•" * min(n_, 5)])
        v.append(["Son fiyat", tl(m["fiyat"]), "–", ""])
        for lv, n_ in sv["destek"]: v.append(["Destek", tl(lv), yz(lv / m["fiyat"] - 1), "•" * min(n_, 5)])
        E.append(KeepTogether([Paragraph("Destek ve direnç seviyeleri", ST["h2"]), TS.tablo(v, [W * .2, W * .2, W * .15, W * .15], font=7.6)]))
    E.append(Spacer(1, 6)); E.append(_img(g_tl_usd(m), W, 2.4 / 7.5))

    # 2 Skor kartı
    E.append(CondPageBreak(10 * cm)); E.append(Bolum(2, "Skor kartı: Göstergeler ne diyor?", W))
    sr = sorted(m["saglik"].items(), key=lambda x: x[1])
    E.append(bilgi_kutusu("Kısaca:", f"Varlık {len(sr)} alanda 1–5 arası puanlandı. En güçlü alan <b>{kucuk(sr[-1][0])}</b>, en zayıf alan <b>{kucuk(sr[0][0])}</b>.", W))
    E.append(Spacer(1, 4)); E.append(_img(br.g_saglik(m, "Skor kartı – Kategoriler (1–5)"), W * 0.92, (0.42 * len(m["saglik"]) + 0.5) / 7.5))
    for kat_, liste in m["saglik_detay"].items():
        v = [[f"{kat_}  –  {ond(m['saglik'][kat_], 2)}/5", "Değer", "Puan"]] + [[a, b_, ond(p_, 0)] for a, b_, p_ in liste]
        t = TS.tablo(v, [W * .6, W * .25, W * .15], font=7.6)
        k_, a_ = TS.durum_rengi(TS.puan_durum(m["saglik"][kat_]))
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), a_), ("TEXTCOLOR", (0, 0), (-1, 0), k_)]))
        E.append(KeepTogether([t, Spacer(1, 5)]))

    # 3 Risk ve korelasyon
    E.append(CondPageBreak(9 * cm)); E.append(Bolum(3, "Risk ve diğer piyasalarla ilişki", W))
    E.append(bilgi_kutusu("Bu ne demek?", "Korelasyon +1'e yakınsa iki varlık birlikte hareket eder; 0'a yakınsa ilişkisizdir; "
                          "eksi değer ters yönlü hareketi gösterir. Portföy çeşitlendirmesi için düşük korelasyonlu varlıklar tercih edilir.", W, "turkuaz"))
    v = [["Gösterge", "Değer"], ["Yıllık volatilite", yz(m["vol"])], ["3 yıllık en büyük düşüş", yz(m["max_dd"])],
         ["Son 3 yılın zirvesi", f"{tl(m['zirve'])} {sym}"], ["Zirveden uzaklık", yz(m["zirveden"])],
         ["52 haftalık aralık", f"{tl(m['dip52'])} – {tl(m['zirve52'])} {sym}"]]
    kv = [["Korelasyon (1 yıl, günlük)", "Değer"]] + [[k_, ond(x, 2)] for k_, x in m["korelasyon"].items()]
    t = Table([[TS.tablo(v, [W * .3, W * .18], font=7.6), TS.tablo(kv, [W * .3, W * .16], font=7.6)]], colWidths=[W * .5, W * .5])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)])); E += [Spacer(1, 4), t]

    # 4 Para akışı
    if m.get("akis"):
        E.append(CondPageBreak(10 * cm)); E.append(Bolum(4, "Para akışı: Alıcılar mı satıcılar mı?", W))
        for x in br.akis_yorumlari(m): E.append(Paragraph("• " + x, ST["madde"]))
        ga = br.g_akis(m["hist"], m)
        if ga: E += [Spacer(1, 4), _img(ga, W, (1.55 * 2 + 0.4) / 7.5)]

    # 5 Mevsimsellik
    gm = g_mevsim(m)
    if gm:
        E.append(CondPageBreak(8 * cm)); E.append(Bolum(5, "Mevsimsellik", W))
        E.append(bilgi_kutusu("Bu ne demek?", "Geçmiş yıllarda her ay ortalama ne kadar değişim olduğunu gösterir. Çerçeveli çubuk içinde "
                              "bulunduğumuz aydır. Geçmiş eğilimler geleceği garanti etmez.", W, "turkuaz"))
        E += [Spacer(1, 4), _img(gm, W, 2.4 / 7.5)]

    # 6 Özel veriler
    if m.get("cg") or m.get("korku") or m.get("oran"):
        E.append(CondPageBreak(7 * cm)); E.append(Bolum(6, "Kripto piyasa verileri" if m["tur"] == "kripto" else "Emtia oranları", W))
        v = [["Gösterge", "Değer"]]
        if m.get("cg"):
            c_ = m["cg"]
            v += [["Piyasa değeri sırası", str(c_.get("sira") or "–")], ["Piyasa değeri", f"${tl(c_.get('piy_deg'))}"],
                  ["24 saatlik işlem hacmi", f"${tl(c_.get('hacim'))}"], ["Dolaşımdaki arz", tl(c_.get("dolasim"), 0)],
                  ["Maksimum arz", tl(c_.get("maks"), 0) if c_.get("maks") else "Sınırsız"],
                  ["Tüm zamanların zirvesi", f"${tl(c_.get('ath'))} ({str(c_.get('ath_tarih') or '')[:10]})"],
                  ["Zirveye uzaklık", yz((c_.get("ath_fark") or 0) / 100)]]
        if m.get("korku"):
            v += [["Korku ve Açgözlülük Endeksi", f"{m['korku']['deger']} – {KORKU_TR.get(m['korku']['sinif'], m['korku']['sinif'])}"],
                  ["30 günlük ortalama", ond(m["korku"]["ort30"], 0)]]
        if m.get("oran"):
            v += [[m["oran"]["ad"], ond(m["oran"]["deger"], 1)], ["5 yıllık ortalama", ond(m["oran"]["ort5y"], 1)]]
        E.append(TS.tablo(v, [W * .45, W * .3], font=7.6))
        if m.get("oran"): E.append(Spacer(1, 3)); E.append(bilgi_kutusu("Yorum:", m["oran"]["yorum"], W, "turkuaz"))

    # 7 Haberler
    hb = m.get("haber") or {}
    if hb.get("liste"):
        E.append(CondPageBreak(6 * cm)); E.append(Bolum(7, f"Haberler (genel ton: {kucuk(hb['ozet'])})", W))
        v = [["Tarih", "Başlık", "Kaynak"]] + [[f"{x['tarih']:%d.%m}" if x["tarih"] else "–", Paragraph(("↑ " if x["ton"] > 0 else "↓ " if x["ton"] < 0 else "") + x["baslik"][:140], ST["hucre"]), x["kaynak"][:22]] for x in hb["liste"]]
        E.append(TS.tablo(v, [W * .1, W * .68, W * .22], hizala_sol=(0, 1, 2), font=7.4))

    # 8 Genel değerlendirme
    E.append(PageBreak()); E.append(Bolum(8, "Genel değerlendirme", W))
    for bas, metin in genel_degerlendirme(m):
        E.append(KeepTogether([Paragraph(bas, ST["h2"]), Paragraph(metin, ST["p"])]))
    E.append(Spacer(1, 8)); E.append(Bolum(9, "Sözlük ve uyarılar", W))
    E.append(TS.tablo([["Terim", "Sade anlatım"]] + [[a, Paragraph(b, ST["hucre"])] for a, b in SOZLUK_VARLIK], [W * .28, W * .72], hizala_sol=(0, 1), font=7.6))
    E.append(Spacer(1, 6))
    E.append(Paragraph("Veriler: Yahoo Finance (fiyat), CoinGecko ve alternative.me (kripto), Google Haberler. Emtia fiyatları vadeli işlem "
                       "kontratlarına dayanır. Bu rapor otomatik bir model çıktısıdır; yatırım danışmanlığı kapsamında değildir.", ST["kucuk"]))
    doc.build(E, onFirstPage=sayfa, onLaterPages=sayfa)
    return dosya

def rapor(kod, klasor=".", **kw):
    m = analiz(kod, **kw)
    dosya = os.path.join(klasor, f"{kod.upper()}_Rapor_{dt.date.today():%Y%m%d}.pdf")
    pdf_olustur(m, dosya)
    return dosya, m

def tara(kodlar=None, **kw):
    """Tüm emtia ve kriptoları skorlar; özet satırlar döndürür."""
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
    for k in (kodlar or list(VARLIKLAR)):
        try:
            m = analiz(k, fiyat_fn=fiyat_fn, haber_fn=lambda *a: {"liste": [], "ton": 0, "ozet": "–"}, **kw)
            satir.append({"Kod": k, "Ad": m["ad"], "Tür": m["tur"], "Fiyat": m["fiyat"], "Para": m["para"],
                          "Skor": m["genel_skor"], "Görünüm": m["gorunum"], "1A $": m["r_usd"].get("1A"),
                          "YBB $": m["r_usd"].get("YBB"), "1Y $": m["r_usd"].get("1Y"), "1Y TL reel": m["r_reel"],
                          "Volatilite": m["vol"], "Mayer": m["mayer"], "RSI": m["rsi"],
                          "Para akışı": (m.get("akis") or {}).get("ozet")})
        except Exception as ex:
            hata[k] = str(ex)[:100]
    return satir, hata
