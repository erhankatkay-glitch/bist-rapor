# -*- coding: utf-8 -*-
"""Gerçek veriyle kalite denetimi (yalnızca test dalında çalışır, Telegram'a bir şey göndermez).
1) Göstergeler: bağımsız 'ta' kütüphanesiyle karşılaştırma
2) Teknik analiz tutarlılığı: destek < fiyat < direnç, Fibonacci/pivot sırası, etiketler
3) Temel analiz: oranlar, pay adedi, piyasa değeri (Yahoo ile kıyas), vergi, FAVÖK, adil değer uç değerleri
Çıktı: denetim/ klasörü (CSV + ozet.txt)."""
import os, sys, traceback, math, json
import numpy as np
import pandas as pd

OUT = "denetim"; os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, "ozet.txt"), "w", encoding="utf-8")


def yaz(*a):
    s = " ".join(str(x) for x in a); print(s); LOG.write(s + "\n"); LOG.flush()


import yfinance as yf
import bist_teknik as T

# ------------------------------------------------------------------ 1) göstergeler
def gosterge_kiyas():
    import ta
    yaz("=== 1) GÖSTERGE KIYASI (bist_teknik vs ta kütüphanesi), son 100 mumda en büyük göreli fark ===")
    satir = []
    for s in ("THYAO.IS", "ASELS.IS", "AAPL", "NVDA", "BTC-USD", "GC=F"):
        try:
            h = yf.Ticker(s).history(period="3y", auto_adjust=True)[["Open", "High", "Low", "Close", "Volume"]].dropna()
            h.index = h.index.tz_localize(None)
            G = T.gostergeler(h); c, hi, lo, v = h.Close, h.High, h.Low, h.Volume
            ref = {
                "RSI": ta.momentum.RSIIndicator(c, 14).rsi(),
                "ATR": ta.volatility.AverageTrueRange(hi, lo, c, 14).average_true_range(),
                "ADX": ta.trend.ADXIndicator(hi, lo, c, 14).adx(),
                "PDI": ta.trend.ADXIndicator(hi, lo, c, 14).adx_pos(),
                "MACD": ta.trend.MACD(c).macd(), "MACD_SIG": ta.trend.MACD(c).macd_signal(),
                "BB_UST": ta.volatility.BollingerBands(c, 20, 2).bollinger_hband(),
                "STOCH_K": ta.momentum.StochasticOscillator(hi, lo, c, 14, 3).stoch().rolling(3).mean(),
                "CCI": ta.trend.CCIIndicator(hi, lo, c, 20).cci(),
                "WILLR": ta.momentum.WilliamsRIndicator(hi, lo, c, 14).williams_r(),
                "MFI": ta.volume.MFIIndicator(hi, lo, c, v, 14).money_flow_index(),
                "CMF": ta.volume.ChaikinMoneyFlowIndicator(hi, lo, c, v, 20).chaikin_money_flow(),
                "UO": ta.momentum.UltimateOscillator(hi, lo, c).ultimate_oscillator(),
                "TENKAN": ta.trend.IchimokuIndicator(hi, lo, 9, 26, 52).ichimoku_conversion_line(),
                "KIJUN": ta.trend.IchimokuIndicator(hi, lo, 9, 26, 52).ichimoku_base_line(),
                "PSAR": ta.trend.PSARIndicator(hi, lo, c).psar(),
                "AO": ta.momentum.AwesomeOscillatorIndicator(hi, lo).awesome_oscillator(),
                "TRIX": ta.trend.TRIXIndicator(c, 15).trix(),
                "AROON_UP": ta.trend.AroonIndicator(hi, lo, 25).aroon_up(),
                "OBV": ta.volume.OnBalanceVolumeIndicator(c, v).on_balance_volume(),
            }
            for k, r in ref.items():
                a = G[k].iloc[-100:]; b = r.iloc[-100:]
                if k == "OBV":   # başlangıç noktası farklı olabilir: değişimleri kıyasla
                    a, b = a.diff(), b.diff()
                olcek = max(float(b.abs().median()), 1e-9)
                fark = float((a - b).abs().max() / olcek)
                satir.append({"sembol": s, "gosterge": k, "goreli_fark": round(fark, 5), "biz": float(G[k].iloc[-1]), "ta": float(r.iloc[-1])})
        except Exception as ex:
            yaz("  hata", s, ex)
    df = pd.DataFrame(satir); df.to_csv(os.path.join(OUT, "gosterge.csv"), index=False)
    if len(df):
        ozet = df.groupby("gosterge")["goreli_fark"].max().sort_values(ascending=False)
        for k, x in ozet.items(): yaz(f"  {k:10s} en büyük göreli fark {x:.4%}" + ("   <-- İNCELE" if x > 0.01 else ""))


# ------------------------------------------------------------------ 2) teknik tutarlılık
def teknik_tutarlilik():
    yaz("\n=== 2) TEKNİK ANALİZ TUTARLILIĞI ===")
    sorun = []; n = 0
    for kod in ("THYAO", "ASELS", "GARAN", "BIMAS", "SASA", "KCHOL", "EREGL", "TUPRS", "XU100", "GRAMALTIN", "USDTRY",
                "NVDA.US", "AAPL.US", "TSLA.US", "BTC", "ETH", "SOL"):
        try:
            s = T.analiz(kod); n += 1
            for tf, a in s["tf"].items():
                if not a: continue
                c = a["fiyat"]
                for p, _ in a["sr"]["destek"]:
                    if p >= c: sorun.append(f"{kod} {tf}: destek {p:.4g} ≥ fiyat {c:.4g}")
                for p, _ in a["sr"]["direnc"]:
                    if p <= c: sorun.append(f"{kod} {tf}: direnç {p:.4g} ≤ fiyat {c:.4g}")
                if a["sr"]["destek"] and (c - a["sr"]["destek"][0][0]) / c > 0.5:
                    sorun.append(f"{kod} {tf}: en yakın destek fiyattan %{(c - a['sr']['destek'][0][0]) / c * 100:.0f} uzak")
                if a["sr"]["direnc"] and (a["sr"]["direnc"][0][0] - c) / c > 1.0:
                    sorun.append(f"{kod} {tf}: en yakın direnç fiyattan %{(a['sr']['direnc'][0][0] - c) / c * 100:.0f} uzak")
                pv = a["pivot"]["Klasik"]
                if not (pv["S3"] <= pv["S2"] <= pv["S1"] <= pv["P"] <= pv["R1"] <= pv["R2"] <= pv["R3"]):
                    sorun.append(f"{kod} {tf}: pivot sırası bozuk {pv}")
                for ad, y, ac, g in [(x[0], x[1], x[2], x[3]) for x in a["sinyal"]]:
                    if "Pozitif" in ad and y < 0 or "Negatif" in ad and y > 0: sorun.append(f"{kod} {tf}: yön çelişkisi {ad}")
                for f in a["form"]:
                    if f.get("hedef") is not None and f["yon"] == 1 and f["hedef"] < c * 0.98 and "KIRILIM" in f["durum"]:
                        sorun.append(f"{kod} {tf}: yukarı kırılım hedefi fiyatın altında ({f['ad']})")
                if not (0 <= a["puan"] <= 100): sorun.append(f"{kod} {tf}: puan aralık dışı {a['puan']}")
            yaz(f"  {kod:10s} puan {s['puan']:.0f} {s['etiket']:9s} | {s['yorum'][:150]}")
        except Exception as ex:
            sorun.append(f"{kod}: HATA {ex}")
    yaz(f"  {n} varlık incelendi, {len(sorun)} sorun")
    for x in sorun: yaz("  !", x)


# ------------------------------------------------------------------ 3) temel analiz
BIST = ["THYAO", "ASELS", "BIMAS", "EREGL", "TUPRS", "KCHOL", "SAHOL", "GARAN", "AKBNK", "YKBNK", "ISCTR", "FROTO", "TOASO",
        "TCELL", "TTKOM", "SISE", "PGSUS", "MGROS", "ENKAI", "AEFES", "ULKER", "KOZAL", "PETKM", "SASA", "HEKTS", "ARCLK",
        "VESTL", "EKGYO", "OYAKC", "CIMSA", "TAVHL", "DOAS", "ENJSA", "AKSEN", "ASTOR", "KONTR", "MAVI", "SOKM", "TKFEN", "ALARK"]
ABD = ["AAPL.US", "MSFT.US", "NVDA.US", "AMZN.US", "JPM.US", "XOM.US", "KO.US", "TSLA.US", "BRK-B.US", "TSM.US"]


def temel():
    import bist_rapor as br
    yaz("\n=== 3) TEMEL ANALİZ ===")
    sat = []
    for kod in BIST + ABD:
        try:
            d, m, em, _ = br.analiz_et(kod, log=lambda *a: None)
            info = d["info"]
            mc_y = br.sayi(info.get("marketCap"))
            r = {"kod": kod, "kaynak": m.get("kaynak", "")[:40], "fiyat": m["fiyat"], "hisse": m["hisse"],
                 "hisse_y": br.sayi(info.get("sharesOutstanding")), "piy_deg": m["piy_deg"], "mc_yahoo": mc_y,
                 "pd_fark": (m["piy_deg"] / mc_y - 1) if m["piy_deg"] and mc_y else None,
                 "fk": m["fk"], "fk_yahoo": br.sayi(info.get("trailingPE")), "pddd": m["pddd"], "pb_yahoo": br.sayi(info.get("priceToBook")),
                 "fd_favok": m["fd_favok"], "roe": m["roe"], "net_marj": m["net_marj"], "favok_marj": m["favok_marj"],
                 "efektif_vergi": m["efektif_vergi"], "ciro": m["T"]["ciro"], "net": m["T"]["net"], "favok": m["T"]["favok"],
                 "ebit": m["T"]["ebit"], "son_donem": str(m["veri"]["son_donem"])[:10], "veri_puan": m["veri"]["puan"],
                 "adil": m.get("adil"), "potansiyel": m.get("potansiyel"), "gorus": m.get("gorus"), "guven": m.get("guven"),
                 "sinirlandi": m.get("sinirlandi"), "hisse_notu": m.get("hisse_notu"), "eski": (m["veri"].get("eski") or "")[:80],
                 "yontem": " | ".join(f"{y[0]}={y[1]:.4g}{'' if y[6] else '(x)'}" for y in m.get("yontemler", []) if y[1] is not None)}
            sat.append(r)
            uyari = []
            if r["pd_fark"] is not None and abs(r["pd_fark"]) > 0.10: uyari.append(f"piyasa değeri Yahoo'dan %{r['pd_fark']*100:+.0f} farklı")
            if r["fk"] and r["fk_yahoo"] and abs(r["fk"] / r["fk_yahoo"] - 1) > 0.35: uyari.append(f"F/K {r['fk']:.1f} vs Yahoo {r['fk_yahoo']:.1f}")
            if r["efektif_vergi"] is not None and r["efektif_vergi"] == 0: uyari.append("efektif vergi 0")
            if r["favok_marj"] and r["favok_marj"] > 0.8: uyari.append(f"FAVÖK marjı %{r['favok_marj']*100:.0f}")
            if r["roe"] and abs(r["roe"]) > 1.5: uyari.append(f"ROE %{r['roe']*100:.0f}")
            if r["sinirlandi"]: uyari.append("adil değer sınırlandı")
            yaz(f"  {kod:9s} F/K {br.kat(r['fk']):>7s} PD/DD {br.kat(r['pddd']):>6s} FD/FAVÖK {br.kat(r['fd_favok']):>6s} "
                f"ROE {br.yz(r['roe']):>7s} vergi {br.yz(r['efektif_vergi']):>6s} adil {br.ond(r['adil'])} ({br.yz(r['potansiyel'])}) {r['gorus']}"
                + ("  <-- " + "; ".join(uyari) if uyari else ""))
        except Exception as ex:
            yaz(f"  {kod}: HATA {type(ex).__name__}: {ex}"); traceback.print_exc()
    pd.DataFrame(sat).to_csv(os.path.join(OUT, "temel.csv"), index=False)


def firsat_kuru():
    import firsat as F
    yaz("\n=== 4) FIRSAT MOTORU KURU ÇALIŞMA (BIST günlük, 40 hisse) ===")
    v = []
    for kod in BIST_F:
        try:
            h, _ = T.gunluk_veri(kod); h = h.iloc[-1600:]
            v.append({"kod": kod, "ad": kod, "para": "₺", "a": F.hafif(h, "G"), "ust": T.tf_analiz(T.yeniden_ornekle(h, "H"), "H")})
        except Exception as ex:
            yaz("  veri yok", kod, ex)
    sec, aday, pist = F.tara(v, "G", "bist", yonler=(1, -1), adet=5)
    yaz(f"  {len(v)} hisse, {len(aday)} aday, {len(sec)} seçilen")
    for f in aday[:12]:
        p = f["plan"]
        yaz(f"  {f['kod']:6s} {'AL' if f['yon'] == 1 else 'SAT'} {f['kurulum_ad'][:40]:40s} puan {f['puan']:.0f} beklenenR {f['beklenen_R']:+.2f} "
            f"giriş {p['giris']:.2f} stop {p['stop']:.2f} H {[round(x['fiyat'], 2) for x in p['hedef']]} R {[round(x['r'], 2) for x in p['hedef']]}")
        if (p["stop"] - p["giris"]) * f["yon"] >= 0: yaz("    ! stop yanlış tarafta")
        if any((x["fiyat"] - p["giris"]) * f["yon"] <= 0 for x in p["hedef"]): yaz("    ! hedef yanlış tarafta")
        if not all(p["hedef"][i]["r"] < p["hedef"][i + 1]["r"] for i in range(2)): yaz("    ! hedefler sıralı değil")


BIST_F = ["THYAO", "ASELS", "BIMAS", "EREGL", "TUPRS", "KCHOL", "SAHOL", "GARAN", "AKBNK", "YKBNK", "ISCTR", "FROTO", "TOASO",
          "TCELL", "TTKOM", "SISE", "PGSUS", "MGROS", "ENKAI", "AEFES", "ULKER", "TRALT", "PETKM", "SASA", "HEKTS", "ARCLK",
          "VESTL", "EKGYO", "OYAKC", "CIMSA", "TAVHL", "DOAS", "ENJSA", "AKSEN", "ASTOR", "KONTR", "MAVI", "SOKM", "TKFEN", "ALARK"]

if os.environ.get("HIZLI"):
    BIST = ["THYAO", "GARAN"]
    ABD = ["AMZN.US", "MSFT.US", "JPM.US"]

if __name__ == "__main__":
    for f in ((firsat_kuru, temel) if os.environ.get("HIZLI") else (gosterge_kiyas, teknik_tutarlilik, temel)):
        try: f()
        except Exception as ex:
            yaz(f"{f.__name__} HATA: {ex}"); traceback.print_exc()
    LOG.close()
