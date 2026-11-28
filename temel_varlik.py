# -*- coding: utf-8 -*-
"""Kripto ve emtia için "temel" görünüm (hızlı uygulama ve Telegram için gece hazır hesaplanır).

Bilançoları olmadığından temel analiz, tam uygulamanın Varlık analizindeki (bist_varlik.analiz) veriler üzerine kurulur:
- Kripto (temel/kripto.json): CoinGecko arz ve likidite (piyasa değeri sırası, hacim / piyasa değeri, dolaşımdaki arz, FDV seyrelmesi,
  zirveden uzaklık), model değer bantları (200G / 200H ortalama, log-regresyon), genel görünüm skoru; en büyük coinlerde ek olarak
  OKX türev verisi (fonlama oranı, açık pozisyon, long/short), vadeli açık pozisyon değişimi ve DefiLlama ağ / protokol verisi (TVL, ücretler).
- Emtia (temel/emtia.json): genel görünüm skoru ve model değer, vadeli kontrat eğrisi (contango / backwardation),
  CFTC COT raporu (spekülatörlerin net pozisyonu ve 3 yıllık yüzdelik konumu), mevsimsellik (bu ay ve gelecek ay), altın/gümüş oranı.
Kullanım: temel.py <cikti> <kripto|emtia> (temel.yml)."""
import datetime as dt
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

KRIPTO_DERIN = 60          # türev / DeFi verisi çekilen en büyük coin sayısı
AY_TR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# Emtia vadeli kontrat kökleri (Yahoo) ve CFTC COT kodları (legacy, futures only)
EMTIA_VADE = {"ALTIN": ("GC", "CMX"), "GRAMALTIN": ("GC", "CMX"), "GUMUS": ("SI", "CMX"), "PLATIN": ("PL", "NYM"), "PALADYUM": ("PA", "NYM"),
              "BAKIR": ("HG", "CMX"), "BRENT": ("BZ", "NYM"), "WTI": ("CL", "NYM"), "DOGALGAZ": ("NG", "NYM"), "BUGDAY": ("ZW", "CBT"),
              "MISIR": ("ZC", "CBT"), "SOYA": ("ZS", "CBT"), "KAHVE": ("KC", "NYB"), "KAKAO": ("CC", "NYB"), "SEKER": ("SB", "NYB"),
              "PAMUK": ("CT", "NYB")}
COT_KOD = {"ALTIN": "088691", "GRAMALTIN": "088691", "GUMUS": "084691", "PLATIN": "076651", "PALADYUM": "075651", "BAKIR": "085692",
           "WTI": "067651", "BRENT": "06765T", "DOGALGAZ": "023651", "BUGDAY": "001602", "MISIR": "002602", "SOYA": "005602",
           "KAHVE": "083731", "KAKAO": "073732", "SEKER": "080732", "PAMUK": "033661"}
COT_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"


def _t(v):
    """JSON için temizlik: NaN/inf → None, numpy → Python, tarih → metin."""
    if isinstance(v, dict): return {str(k): _t(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)): return [_t(x) for x in v]
    if isinstance(v, (bool, np.bool_)): return bool(v)
    if isinstance(v, (int, np.integer)): return int(v)
    if isinstance(v, (float, np.floating)):
        return None if not math.isfinite(float(v)) else round(float(v), 6)
    if isinstance(v, (pd.Timestamp, dt.date, dt.datetime)): return str(v)[:10]
    return v


def _b(a, b):
    try: return a / b if a is not None and b else None
    except Exception: return None


def _ortak(m):
    """bist_varlik.analiz çıktısının kripto ve emtiada ortak, hafif özeti."""
    import bist_varlik as V
    try: V.ipuclari(m)
    except Exception: m.setdefault("guclu", []); m.setdefault("zayif", [])
    dg = m.get("deger") or {}
    return {"Kod": m["kod"], "Ad": m["ad"], "Fiyat": m["fiyat"], "Para": m["para"], "Skor": m.get("genel_skor"), "Görünüm": m.get("gorunum"),
            "Bölümler": {k: v for k, v in (m.get("saglik") or {}).items() if v is not None},
            "Model değer": dg.get("adil"), "Potansiyel": dg.get("pot"), "Değer etiketi": dg.get("etiket"), "Değer güveni": dg.get("guven"),
            "Değer yöntemleri": [[a.split(" (")[0], d] for a, d, *_ in dg.get("yontemler", [])],
            "Mayer": m.get("mayer"), "RSI": m.get("rsi"), "Volatilite": m.get("vol"), "En büyük düşüş 3Y": m.get("max_dd"),
            "Zirveden": m.get("zirveden"), "Sharpe": m.get("sharpe"),
            "Getiri $": {k: m["r_usd"].get(k) for k in ("1A", "3A", "YBB", "1Y")}, "1Y TL reel": m.get("r_reel"),
            "Göreli 6A": m.get("goreli_6a"), "Göreli ref": m.get("goreli_ref"),
            "Korelasyon": m.get("korelasyon") or {}, "Para akışı": (m.get("akis") or {}).get("ozet"),
            "Güçlü": m.get("guclu", [])[:5], "Zayıf": m.get("zayif", [])[:5]}


def _mevsim(m):
    ms = m.get("mevsim")
    if ms is None or not len(ms): return None
    b = dt.date.today().month; s = b % 12 + 1
    al = lambda a: {"ay": AY_TR[a - 1], "ort": ms.loc[a, "ort"], "pozitif": ms.loc[a, "pozitif"], "n": ms.loc[a, "n"]} if a in ms.index and not pd.isna(ms.loc[a, "ort"]) else None
    return {"bu_ay": al(b), "gelecek_ay": al(s)}


def _ortam(V):
    """Tek sefer indirilen ortak veriler (kur, korku endeksi, kripto geneli, kıyas serileri)."""
    import bist_rapor as br
    kw = {}
    try: fx = br.kur_cek(); kw["fx_fn"] = lambda: fx
    except Exception as x: print("kur:", x)
    on = {}
    def kiyas_fn(y):
        if y not in on: on[y] = V.fiyat_cek(y, "2y")["Close"]
        return on[y]
    kw["kiyas_fn"] = kiyas_fn
    return kw


# ================================================================== KRİPTO
def kripto(klasor):
    import bist_kripto as KR
    import bist_varlik as V
    import teknik_bulten as TB
    kodlar = TB.evren("kripto")
    print("kripto", len(kodlar), "coin")
    # CoinGecko piyasa listesi (ilk 1000; 7g / 30g / 1y değişimleriyle)
    cg = {}
    for p in range(1, 5):
        try:
            for c in KR._get(f"{KR.CG}/coins/markets", vs_currency="usd", order="market_cap_desc", per_page=250, page=p,
                             price_change_percentage="7d,30d,1y"):
                s = c["symbol"].upper()
                if s not in cg: cg[s] = c
                if s not in KR._CG: KR._CG[s] = c          # analiz() içindeki cg_kayit aynı listeyi kullansın
        except Exception as x:
            print("CoinGecko sayfa", p, x); break
        time.sleep(2.5)
    print("CoinGecko:", len(cg))
    kw = _ortam(V)
    kk = gg = None
    try: kk = V.korku_endeksi()
    except Exception as x: print("korku:", x)
    try: gg = V.kripto_global()
    except Exception as x: print("global:", x)
    kw.update(korku_fn=lambda: kk, global_fn=lambda: gg, cg_fn=KR.cg_kayit, detay=False,
              haber_fn=lambda *a: {"liste": [], "ton": 0, "ozet": "–"})
    from concurrent.futures import ThreadPoolExecutor
    def bir(kod):
        try: return kod, V.analiz(kod, **kw), None
        except Exception as x: return kod, None, str(x)[:90]
    bir(kodlar[0])  # kıyas serilerini ısıt
    satir, hata = {}, {}
    with ThreadPoolExecutor(4) as ex:
        for kod, m, h in ex.map(bir, kodlar):
            if m is None: hata[kod] = h; continue
            r = _ortak(m); baz = m["baz"]; c = cg.get(baz.upper()) or {}
            mc, fdv, vol = c.get("market_cap"), c.get("fully_diluted_valuation"), c.get("total_volume")
            mx = c.get("max_supply") or c.get("total_supply")
            r.update({"Baz": baz, "Sıra": c.get("market_cap_rank"), "Piyasa değeri": mc, "FDV": fdv, "Hacim 24s": vol,
                      "Hacim / PD": _b(vol, mc), "PD / FDV": _b(mc, fdv), "Dolaşım": c.get("circulating_supply"), "Maks arz": c.get("max_supply"),
                      "Dolaşım oranı": _b(c.get("circulating_supply"), mx), "ATH": c.get("ath"),
                      "ATH farkı": (c.get("ath_change_percentage") / 100) if c.get("ath_change_percentage") is not None else None,
                      "ATH tarihi": str(c.get("ath_date") or "")[:10] or None,
                      "Değişim": {k: (c.get(f"price_change_percentage_{k}_in_currency") / 100) if c.get(f"price_change_percentage_{k}_in_currency") is not None else None
                                  for k in ("7d", "30d", "1y")},
                      "LR sapma": ((m.get("deger") or {}).get("lr") or {}).get("z")})
            satir[kod] = r
    # Derin veri: en büyük coinler (piyasa değeri sırasına göre)
    sirali = sorted(satir, key=lambda k: satir[k].get("Sıra") or 10 ** 6)[:KRIPTO_DERIN]
    for kod in sirali:
        r = satir[kod]; baz = r["Baz"]
        try: tv = V.turev_verisi(baz)
        except Exception: tv = None
        try: vd = KR.vadeli(baz)
        except Exception: vd = {}
        try: pr = KR.protokol(baz, (cg.get(baz.upper()) or {}).get("id"))
        except Exception: pr = None
        if tv: r["Türev"] = {"Fonlama yıllık": tv.get("yillik"), "Fonlama 30g yıllık": (tv.get("fonlama_30g") or 0) * 3 * 365 if tv.get("fonlama_30g") is not None else None,
                             "Açık pozisyon $": tv.get("oi_usd"), "Long/short": tv.get("ls"), "Long/short 7g": tv.get("ls_7g")}
        if vd:
            r.setdefault("Türev", {}).update({"AP 7g": vd.get("oi_7g"), "AP 30g": vd.get("oi_30g"), "Agresif alım 7g": vd.get("taker_7g")})
            try: r["Türev yorumu"] = KR.vadeli_yorum(vd, (r.get("Değişim") or {}).get("7d"))
            except Exception: pass
        if pr: r["Ağ / protokol"] = {k: pr.get(k) for k in ("ad", "kategori", "tvl", "d7", "mcap_tvl", "ucret_30g", "fiyat_ucret")}
        # türev / arz bilgisiyle güçlü-zayıf yönleri tamamla (tam uygulamadaki ipuclari ile aynı eşikler)
        fy = (r.get("Türev") or {}).get("Fonlama yıllık")
        if fy is not None and fy > 0.3: r["Zayıf"].append(f"Fonlama oranı yüksek (yıllık %{fy * 100:.0f}); kaldıraçlı alıcılar kalabalık.".replace(".", ",", 1))
        if fy is not None and fy < 0: r["Güçlü"].append("Fonlama oranı negatif; piyasa aşırı karamsar, ani yükseliş (short squeeze) riski.")
        time.sleep(0.3)
    # Arz & likidite puanı (tüm coinler, 0–100, liste içi yüzdelik): büyüklük, likidite, seyrelme, model değer potansiyeli
    df = pd.DataFrame({k: {"sira": v.get("Sıra"), "lik": v.get("Hacim / PD"), "sey": v.get("PD / FDV"), "pot": v.get("Potansiyel"), "skor": v.get("Skor")}
                       for k, v in satir.items()}).T.astype(float)
    if len(df):
        yp = lambda s, ters=False: (s.rank(pct=True, ascending=not ters)).fillna(0.5)
        lik = df["lik"].clip(upper=0.5)
        puan = 0.25 * yp(df["sira"], ters=True) + 0.20 * yp(lik) + 0.20 * yp(df["sey"]) + 0.15 * yp(df["pot"]) + 0.20 * yp(df["skor"])
        for k, p in puan.items(): satir[k]["Temel puan"] = round(float(p) * 100)
    genel = None
    if gg or kk:
        genel = {"Toplam piyasa değeri": (gg or {}).get("toplam"), "BTC dominansı": (gg or {}).get("btc_dom"), "ETH dominansı": (gg or {}).get("eth_dom"),
                 "Stablecoin payı": (gg or {}).get("stable_dom"), "24s değişim": (gg or {}).get("d24"),
                 "Korku endeksi": (kk or {}).get("deger"), "Korku sınıfı": V.KORKU_TR.get((kk or {}).get("sinif"), (kk or {}).get("sinif")),
                 "Korku 30g ort": (kk or {}).get("ort30")}
        for ad, fn in (("Stablecoin", KR.stablecoin_ozet), ("DeFi TVL", KR.tvl_ozet)):
            try: x = fn(); genel[ad] = {"toplam": x["toplam"], "d30": x["d30"]}
            except Exception: pass
    _yaz(klasor, "kripto", satir, hata, genel)


# ================================================================== EMTİA
def cot(kodlar=None, yil=3):
    """CFTC Commitments of Traders (legacy, yalnız vadeli): spekülatör (non-commercial) ve ticari (commercial) net pozisyonlar.
    {emtia_kodu: {tarih, spek_net, spek_net_oi, spek_yuzdelik_3y, spek_d1h, ticari_net, oi}}"""
    import requests
    kodlar = kodlar or COT_KOD
    cftc = sorted(set(COT_KOD[k] for k in kodlar if k in COT_KOD))
    bas = (dt.date.today() - dt.timedelta(days=int(365 * yil) + 14)).isoformat()
    q = {"$where": f"cftc_contract_market_code in({','.join(repr(c) for c in cftc)}) AND report_date_as_yyyy_mm_dd >= '{bas}T00:00:00'",
         "$select": "cftc_contract_market_code,market_and_exchange_names,report_date_as_yyyy_mm_dd,open_interest_all,"
                    "noncomm_positions_long_all,noncomm_positions_short_all,comm_positions_long_all,comm_positions_short_all",
         "$limit": 50000, "$order": "report_date_as_yyyy_mm_dd"}
    r = requests.get(COT_URL, params=q, timeout=60, headers={"User-Agent": "Mozilla/5.0"}); r.raise_for_status()
    d = pd.DataFrame(r.json())
    if d.empty: return {}
    for c in d.columns:
        if c.endswith("_all"): d[c] = pd.to_numeric(d[c], errors="coerce")
    d["t"] = pd.to_datetime(d["report_date_as_yyyy_mm_dd"])
    out = {}
    for k in kodlar:
        x = d[d["cftc_contract_market_code"] == COT_KOD.get(k)].sort_values("t")
        if len(x) < 20: continue
        net = x["noncomm_positions_long_all"] - x["noncomm_positions_short_all"]
        tic = x["comm_positions_long_all"] - x["comm_positions_short_all"]
        son = float(net.iloc[-1]); oi = float(x["open_interest_all"].iloc[-1])
        out[k] = {"tarih": str(x["t"].iloc[-1].date()), "piyasa": x["market_and_exchange_names"].iloc[-1],
                  "spek_net": son, "spek_net_oi": _b(son, oi), "spek_yuzdelik_3y": float((net <= son).mean()),
                  "spek_d1h": float(son - net.iloc[-2]), "spek_d4h": float(son - net.iloc[-5]) if len(net) > 5 else None,
                  "ticari_net": float(tic.iloc[-1]), "oi": oi, "hafta": len(x)}
    return out


def cot_yorum(c):
    if not c: return None
    y = c["spek_yuzdelik_3y"]
    if y >= 0.9: s = "Spekülatörler son 3 yılın en kalabalık alım (long) tarafında: kalabalık pozisyon, ters haberde sert satış riski."
    elif y <= 0.1: s = "Spekülatörler son 3 yılın en karamsar konumunda: tarihsel olarak dönüş fırsatı aranan bölge."
    elif y >= 0.7: s = "Spekülatörler alım tarafında ağırlıklı (3 yıllık aralığın üst kısmı)."
    elif y <= 0.3: s = "Spekülatörler zayıf / satış tarafında ağırlıklı (3 yıllık aralığın alt kısmı)."
    else: s = "Spekülatör konumu 3 yıllık aralığın ortasında: belirgin bir aşırılık yok."
    return s + (" Son hafta net alım artırdılar." if c["spek_d1h"] > 0 else " Son hafta net pozisyon azalttılar." if c["spek_d1h"] < 0 else "")


def vade(kodlar):
    """Emtia vadeli eğrileri (dunya.vade_yapisi ile aynı hesap; tüm emtialar için)."""
    import dunya as DN
    liste = []; gor = set()
    for k in kodlar:
        if k in EMTIA_VADE and EMTIA_VADE[k] not in gor:
            gor.add(EMTIA_VADE[k]); liste.append((k,) + EMTIA_VADE[k])
    vy = DN.vade_yapisi(liste)
    by = {x["kok"]: x for x in vy}
    return {k: by.get(EMTIA_VADE[k][0]) for k in kodlar if k in EMTIA_VADE and by.get(EMTIA_VADE[k][0])}


def emtia(klasor):
    import bist_varlik as V
    import teknik_bulten as TB
    kodlar = TB.evren("emtia")
    kw = _ortam(V); kw.update(detay=False, haber_fn=lambda *a: {"liste": [], "ton": 0, "ozet": "–"}, korku_fn=lambda: None, global_fn=lambda: None)
    try: VY = vade(kodlar)
    except Exception as x: print("vade yapısı:", x); VY = {}
    try: CT = cot(kodlar)
    except Exception as x: print("COT:", x); CT = {}
    print(f"vade eğrisi {len(VY)}, COT {len(CT)} emtia")
    satir, hata = {}, {}
    for kod in kodlar:
        try: m = V.analiz(kod, **kw)
        except Exception as x: hata[kod] = str(x)[:90]; continue
        r = _ortak(m)
        r["Mevsimsellik"] = _mevsim(m)
        if m.get("oran"): r["Oran"] = m["oran"]
        v = VY.get(kod)
        if v:
            r["Vade yapısı"] = {"yapi": v["yapi"], "yillik": v["yillik"], "ay": v["ay"], "yorum": v["yorum"],
                                "noktalar": [[p["vade"], p["fiyat"]] for p in v["noktalar"]]}
            (r["Güçlü"] if v["yapi"] == "backwardation" else r["Zayıf"] if v["yapi"] == "contango" and v["yillik"] > 0.08 else []).append(
                "Vadeli eğri backwardation: yakın teslim primli, fiziksel talep güçlü." if v["yapi"] == "backwardation"
                else f"Vadeli eğri dik contango (yıllık %{v['yillik'] * 100:.0f}): arz bol, uzun pozisyon taşımak maliyetli.".replace(".", ",", 1))
        c = CT.get(kod)
        if c:
            c["yorum"] = cot_yorum(c); r["COT"] = c
            if c["spek_yuzdelik_3y"] >= 0.9: r["Zayıf"].append("Spekülatörler 3 yılın en kalabalık alım konumunda (COT).")
            if c["spek_yuzdelik_3y"] <= 0.1: r["Güçlü"].append("Spekülatörler 3 yılın en karamsar konumunda (COT): dönüş adayı.")
        mv = (r.get("Mevsimsellik") or {}).get("bu_ay")
        if mv and mv["n"] >= 5 and mv["pozitif"] >= 0.7: r["Güçlü"].append(f"{mv['ay']} tarihsel olarak güçlü ay (yılların %{mv['pozitif'] * 100:.0f}'inde yükseliş).")
        if mv and mv["n"] >= 5 and mv["pozitif"] <= 0.3: r["Zayıf"].append(f"{mv['ay']} tarihsel olarak zayıf ay (yılların yalnız %{mv['pozitif'] * 100:.0f}'inde yükseliş).")
        satir[kod] = r
    _yaz(klasor, "emtia", satir, hata, None)


def _yaz(klasor, pz, satir, hata, genel):
    os.makedirs(os.path.join(klasor, "temel"), exist_ok=True)
    o = {"zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "pz": pz, "genel": genel, "satirlar": satir, "hata": len(hata)}
    with open(os.path.join(klasor, "temel", f"{pz}.json"), "w", encoding="utf-8") as f:
        json.dump(_t(o), f, ensure_ascii=False, separators=(",", ":"))
    if hata:
        import collections
        print("hata nedenleri:", collections.Counter(hata.values()).most_common(5))
    print(f"Temel ({pz}): {len(satir)} varlık, {len(hata)} hata")


if __name__ == "__main__":
    k = sys.argv[1] if len(sys.argv) > 1 else "cikti"; p = sys.argv[2] if len(sys.argv) > 2 else "emtia"
    (kripto if p == "kripto" else emtia)(k)
