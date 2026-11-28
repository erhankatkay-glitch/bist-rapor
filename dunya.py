"""Aşama 12: dünya borsaları, döviz majörleri, ABD getiri eğrisi, emtia vade yapısı (ücretsiz kaynaklar).

- Borsalar ve döviz: Yahoo günlük kapanış; 1 gün / 1 hafta / 1 ay / yılbaşından beri, 50 ve 200 günlüğe göre trend.
- Getiri eğrisi: ABD Hazinesi'nin resmî günlük "par yield curve" CSV'si (home.treasury.gov); ulaşılamazsa Yahoo (^IRX, ^FVX, ^TNX, ^TYX).
  10Y–2Y ve 10Y–3A farkları; ters eğri (negatif fark) resesyon öncü göstergesi olarak bilinir, zamanlaması belirsizdir.
- Emtia vade yapısı: Yahoo vadeli kontratları (ör. CLF27.NYM). Uzak vade yakından pahalıysa contango (bol arz / taşıma maliyeti),
  ucuzsa backwardation (yakın arz sıkı).
Kullanım: python dunya.py <cikti_klasoru>  → dunya/ozet.json (+ Pazartesi özeti ya da eğri işareti değişince Telegram kartı)
"""
import os, sys, io, json, datetime as dt
import numpy as np
import pandas as pd

BORSALAR = [  # (ad, sembol, bölge, ülke)
    ("S&P 500", "^GSPC", "Amerika", "ABD"), ("Nasdaq", "^IXIC", "Amerika", "ABD"), ("Dow Jones", "^DJI", "Amerika", "ABD"),
    ("S&P/TSX", "^GSPTSE", "Amerika", "Kanada"), ("Bovespa", "^BVSP", "Amerika", "Brezilya"),
    ("DAX", "^GDAXI", "Avrupa", "Almanya"), ("FTSE 100", "^FTSE", "Avrupa", "İngiltere"), ("CAC 40", "^FCHI", "Avrupa", "Fransa"),
    ("Euro Stoxx 50", "^STOXX50E", "Avrupa", "Euro bölgesi"), ("BIST 100", "XU100.IS", "Avrupa", "Türkiye"),
    ("Nikkei 225", "^N225", "Asya", "Japonya"), ("Hang Seng", "^HSI", "Asya", "Hong Kong"), ("Şanghay", "000001.SS", "Asya", "Çin"),
    ("KOSPI", "^KS11", "Asya", "Güney Kore"), ("Sensex", "^BSESN", "Asya", "Hindistan"), ("ASX 200", "^AXJO", "Asya", "Avustralya")]
DOVIZ = [("EUR/USD", "EURUSD=X"), ("GBP/USD", "GBPUSD=X"), ("USD/JPY", "JPY=X"), ("USD/CHF", "CHF=X"), ("AUD/USD", "AUDUSD=X"),
         ("USD/CAD", "CAD=X"), ("USD/CNY", "CNY=X"), ("Dolar endeksi", "DX-Y.NYB"),
         ("USD/TRY", "TRY=X"), ("EUR/TRY", "EURTRY=X"), ("GBP/TRY", "GBPTRY=X")]
EMTIA = [("Ham petrol (WTI)", "CL", "NYM"), ("Brent petrol", "BZ", "NYM"), ("Doğal gaz", "NG", "NYM"), ("Altın", "GC", "CMX"),
         ("Gümüş", "SI", "CMX"), ("Bakır", "HG", "CMX"), ("Mısır", "ZC", "CBT"), ("Buğday", "ZW", "CBT")]
AY_KOD = "FGHJKMNQUVXZ"
VADE_AD = {"1 Mo": "1A", "2 Mo": "2A", "3 Mo": "3A", "4 Mo": "4A", "6 Mo": "6A", "1 Yr": "1Y", "2 Yr": "2Y", "3 Yr": "3Y", "5 Yr": "5Y",
           "7 Yr": "7Y", "10 Yr": "10Y", "20 Yr": "20Y", "30 Yr": "30Y"}
VADE_AY = {"1A": 1, "2A": 2, "3A": 3, "4A": 4, "6A": 6, "1Y": 12, "2Y": 24, "3Y": 36, "5Y": 60, "7Y": 84, "10Y": 120, "20Y": 240, "30Y": 360}


def _indir(semboller, gun="2y"):
    import yfinance as yf
    v = yf.download(list(semboller), period=gun, interval="1d", auto_adjust=False, progress=False, group_by="ticker", threads=True)
    out = {}
    for s in semboller:
        try:
            x = v[s]["Close"].dropna() if len(semboller) > 1 else v["Close"].dropna()
            x.index = pd.DatetimeIndex(x.index).tz_localize(None).normalize()
            if len(x): out[s] = x[~x.index.duplicated(keep="last")]
        except Exception:
            pass
    try:   # Yahoo günlük barı geride kalabiliyor (ör. XU100 27.11'i sabah hâlâ boş): gün içi 15 dk veriyle tamamla
        import bist_makro as MK
        gi = yf.download(list(out), period="5d", interval="15m", auto_adjust=False, progress=False, group_by="ticker", threads=True)
        for s in list(out):
            try:
                out[s] = MK.gun_ici_tamamla(out[s], gi[s] if len(out) > 1 else gi, s)
            except Exception:
                pass
    except Exception:
        pass
    return out


def ozet_satir(ad, s, ek=None):
    s = s.dropna(); c = float(s.iloc[-1])
    deg = lambda n: float(c / s.iloc[-1 - n] - 1) if len(s) > n else None
    yb = s[s.index >= pd.Timestamp(s.index[-1].year, 1, 1)]
    ytd = float(c / s[s.index < pd.Timestamp(s.index[-1].year, 1, 1)].iloc[-1] - 1) if len(yb) < len(s) else None
    s50, s200 = s.rolling(50).mean().iloc[-1], s.rolling(200).mean().iloc[-1]
    trend = ("yükseliş" if c > s50 > s200 else "düşüş" if c < s50 < s200 else "karışık") if np.isfinite(s200) else "–"
    return {"ad": ad, "son": c, "tarih": str(s.index[-1].date()), "d1": deg(1), "d5": deg(5), "d21": deg(21), "ytd": ytd, "trend": trend,
            "seri": [round(float(v), 4) for v in (s.tail(60) / s.tail(60).iloc[0])], **(ek or {})}


# ------------------------------------------------------------------ getiri eğrisi
def hazine_egrisi(yillar=None):
    """ABD Hazinesi günlük par getiri eğrisi → DataFrame(tarih × vade)."""
    import requests
    yillar = yillar or [dt.date.today().year - 1, dt.date.today().year]
    parcalar = []
    for y in yillar:
        url = (f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{y}/all"
               f"?type=daily_treasury_yield_curve&field_tdr_date_value={y}&page&_format=csv")
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (KATKAY arastirma)"})
        r.raise_for_status()
        d = pd.read_csv(io.StringIO(r.text)); d["Date"] = pd.to_datetime(d["Date"]); parcalar.append(d)
    D = pd.concat(parcalar).set_index("Date").sort_index()
    D = D[[c for c in VADE_AD if c in D.columns]].rename(columns=VADE_AD)
    return D.dropna(how="all")


def yahoo_egrisi():
    K = _indir(["^IRX", "^FVX", "^TNX", "^TYX"])
    m = {"^IRX": "3A", "^FVX": "5Y", "^TNX": "10Y", "^TYX": "30Y"}
    return pd.DataFrame({m[k]: v for k, v in K.items()}).sort_index().dropna(how="all")


def egri_ozeti(D, kaynak):
    D = D.ffill(limit=3)
    son = D.iloc[-1].dropna()
    def gecmis(gun):
        hedef = D.index[-1] - pd.Timedelta(days=gun); x = D[D.index <= hedef]
        return x.iloc[-1].dropna() if len(x) else None
    a1, y1 = gecmis(30), gecmis(365)
    fark = lambda r, a, b: float(r[a] - r[b]) if r is not None and a in r and b in r else None
    s102, s103 = fark(son, "10Y", "2Y"), fark(son, "10Y", "3A")
    tarih_s = (D["10Y"] - D["2Y"]).dropna().tail(520) if "2Y" in D else (D["10Y"] - D["3A"]).dropna().tail(520)
    ters_gun = 0
    for v in reversed(tarih_s.tolist()):
        if v < 0: ters_gun += 1
        else: break
    noktalar = lambda r: [{"vade": k, "ay": VADE_AY[k], "getiri": round(float(r[k]), 3)} for k in VADE_AY if r is not None and k in r]
    durum = ("ters (kısa vade faizi uzundan yüksek)" if (s102 if s102 is not None else s103) < 0 else
             "yatay" if abs(s102 if s102 is not None else s103) < 0.25 else "normal (pozitif eğimli)")
    return {"kaynak": kaynak, "tarih": str(D.index[-1].date()), "bugun": noktalar(son), "ay_once": noktalar(a1), "yil_once": noktalar(y1),
            "f10_2": s102, "f10_3a": s103, "f10_2_ay_once": fark(a1, "10Y", "2Y"), "durum": durum, "ters_gun": ters_gun,
            "fark_seri": {"tarih": [str(x.date()) for x in tarih_s.index[::5]], "deger": [round(float(v), 3) for v in tarih_s.iloc[::5]]},
            "yorum": egri_yorum(s102, s103, ters_gun)}


def egri_yorum(f102, f103, ters_gun):
    f = f102 if f102 is not None else f103
    if f is None: return ""
    ad = "10Y–2Y" if f102 is not None else "10Y–3A"
    if f < 0:
        return (f"{ad} farkı {f:+.2f} puan: eğri ters. Tarihte resesyonlardan önce sıkça görülmüştür ama zamanlaması belirsizdir"
                f" ({ters_gun} işlem günüdür ters).").replace(".", ",", 1)
    if f < 0.25:
        return f"{ad} farkı {f:+.2f} puan: eğri yataya yakın; ters eğriden çıkış dönemleri de dikkatle izlenir.".replace(".", ",", 1)
    return f"{ad} farkı {f:+.2f} puan: eğri normal (uzun vade faizi kısadan yüksek).".replace(".", ",", 1)


# ------------------------------------------------------------------ emtia vade yapısı
def kontratlar(kok, borsa, bugun=None, ay=14):
    b = bugun or dt.date.today(); out = []
    for i in range(1, ay + 1):
        m = (b.month - 1 + i) % 12; y = b.year + (b.month - 1 + i) // 12
        out.append((f"{kok}{AY_KOD[m]}{y % 100:02d}.{borsa}", dt.date(y, m + 1, 1)))
    return out


def vade_yapisi():
    hepsi = {ad: kontratlar(kok, borsa) for ad, kok, borsa in EMTIA}
    K = _indir([s for l in hepsi.values() for s, _ in l] + [f"{kok}=F" for _, kok, _ in EMTIA], gun="10d")
    out = []
    for ad, kok, borsa in EMTIA:
        pts = []
        for s, ay in hepsi[ad]:
            x = K.get(s)
            if x is not None and len(x) and (pd.Timestamp.now().normalize() - x.index[-1]).days <= 7:
                pts.append({"vade": f"{ay:%m.%y}", "ay": ay.isoformat(), "fiyat": float(x.iloc[-1])})
        if len(pts) < 3: continue
        on = K.get(f"{kok}=F"); on = float(on.iloc[-1]) if on is not None and len(on) else pts[0]["fiyat"]
        p0 = pts[0]; uz = [p for p in pts if (dt.date.fromisoformat(p["ay"]) - dt.date.fromisoformat(p0["ay"])).days <= 370][-1]
        aylar = max(1, (dt.date.fromisoformat(uz["ay"]) - dt.date.fromisoformat(p0["ay"])).days / 30.4)
        egim = uz["fiyat"] / p0["fiyat"] - 1; yillik = (1 + egim) ** (12 / aylar) - 1
        yapi = "contango" if yillik > 0.01 else "backwardation" if yillik < -0.01 else "düz"
        out.append({"ad": ad, "kok": kok, "on": on, "noktalar": pts, "egim": egim, "yillik": yillik, "yapi": yapi, "ay": round(aylar, 1),
                    "yorum": {"contango": "Uzak vadeler pahalı: arz bol / depolama-taşıma maliyeti fiyatlanıyor; vadeli üzerinden uzun pozisyon devri maliyetli.",
                              "backwardation": "Yakın vade pahalı: bugünkü arz sıkı, alıcılar hemen teslime prim ödüyor; genelde güçlü fiziksel talep işareti.",
                              "düz": "Vadeler arasında belirgin fark yok."}[yapi]})
    return out


# ------------------------------------------------------------------ ana giriş
def hesapla(klasor=None):
    K = _indir([s for _, s, _, _ in BORSALAR] + [s for _, s in DOVIZ])
    import veri_kalite as VK
    bors = []
    for ad, s, bolge, ulke in BORSALAR:
        if s in K and len(K[s]) > 30:
            bors.append(ozet_satir(ad, K[s], {"sembol": s, "bolge": bolge, "ulke": ulke, "acik": VK.piyasa_acik(VK.tur_bul(s))}))
    dov = [ozet_satir(ad, K[s], {"sembol": s}) for ad, s in DOVIZ if s in K and len(K[s]) > 30]
    try:
        egri = egri_ozeti(hazine_egrisi(), "ABD Hazinesi (resmî günlük par getiri eğrisi)")
    except Exception as ex:
        print("Hazine eğrisi alınamadı, Yahoo yedeği:", ex)
        try: egri = egri_ozeti(yahoo_egrisi(), "Yahoo Finance (^IRX, ^FVX, ^TNX, ^TYX; 2Y yok)")
        except Exception as ex2: print("eğri:", ex2); egri = None
    try: vy = vade_yapisi()
    except Exception as ex: print("vade yapısı:", ex); vy = []
    o = {"zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "borsalar": bors, "doviz": dov, "egri": egri, "vade": vy}
    if klasor:
        os.makedirs(os.path.join(klasor, "dunya"), exist_ok=True)
        json.dump(o, open(os.path.join(klasor, "dunya", "ozet.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return o


def _y(x):
    return ("+" if x >= 0 else "-") + f"%{abs(x) * 100:.1f}".replace(".", ",") if x is not None else "–"


def kart_ciz(o, yol):
    import kart as K
    rk = lambda x: K.C["yesil"] if (x or 0) > 0 else K.C["kirmizi"] if (x or 0) < 0 else K.C["soluk"]
    bol = []
    for bolge in ("Asya", "Avrupa", "Amerika"):
        b = [x for x in o["borsalar"] if x["bolge"] == bolge]
        if b: bol.append({"baslik": bolge.upper() + " (1 HAFTA)", "renk": K.C["altin"], "satirlar": [
            {"sol": x["ad"], "sag": _y(x["d5"]), "sag_renk": rk(x["d5"]), "alt": f"{x['ulke']} · günlük {_y(x['d1'])} · yılbaşından beri {_y(x['ytd'])} · trend {x['trend']}"}
            for x in b]})
    bol.append({"baslik": "DÖVİZ (1 HAFTA)", "renk": K.C["altin"], "satirlar": [
        {"sol": x["ad"], "sag": _y(x["d5"]), "sag_renk": K.C["soluk"], "alt": f"{x['son']:.4g}".replace(".", ",")} for x in o["doviz"][:8]]})
    e = o.get("egri")
    if e:
        bol.append({"baslik": "ABD GETİRİ EĞRİSİ", "renk": K.C["kirmizi"] if (e["f10_2"] if e["f10_2"] is not None else e["f10_3a"] or 0) < 0 else K.C["altin"],
                    "satirlar": [{"sol": "Durum: " + e["durum"], "alt": e["yorum"]}]})
    if o.get("vade"):
        bol.append({"baslik": "EMTİA VADE YAPISI", "renk": K.C["altin"], "satirlar": [
            {"sol": v["ad"], "sag": v["yapi"], "sag_renk": K.C["yesil"] if v["yapi"] == "backwardation" else K.C["soluk"],
             "alt": f"12 aylık eğim {_y(v['yillik'])} (yıllık)"} for v in o["vade"]]})
    K.bildirim_karti(f"DÜNYA PİYASALARI  ·  {dt.date.today():%d.%m.%Y}", "Haftalık dünya özeti", "Borsalar, döviz, faiz eğrisi, emtia vadeleri",
                     bol, yol, vurgu=K.C["altin"], not_="Kaynak: Yahoo Finance, ABD Hazinesi. Yatırım tavsiyesi değildir.")
    return yol


if __name__ == "__main__":
    import tg
    klasor = sys.argv[1] if len(sys.argv) > 1 else "cikti"
    o = hesapla(klasor)
    e = o.get("egri") or {}
    print("dünya:", len(o["borsalar"]), "borsa,", len(o["doviz"]), "döviz, eğri:", e.get("durum"), e.get("f10_2"), "| vade:", [(v["ad"], v["yapi"]) for v in o["vade"]])
    try: eski = json.load(open(os.path.join(tg.KLON, "dunya", "ozet.json"), encoding="utf-8"))
    except Exception: eski = {}
    ef = lambda x: (x or {}).get("f10_2") if (x or {}).get("f10_2") is not None else (x or {}).get("f10_3a")
    isaret_degisti = ef(e) is not None and ef(eski.get("egri")) is not None and (ef(e) < 0) != (ef(eski.get("egri")) < 0)
    if dt.date.today().weekday() == 0 or isaret_degisti:
        try:
            b = tg.Bot("sabah")
            if b.aktif:
                yol = kart_ciz(o, os.path.join(klasor, "dunya", "kart.png"))
                ac = "🌍 <b>Dünya piyasaları</b>" + (f"\n⚠️ ABD getiri eğrisi {'tersine döndü' if ef(e) < 0 else 'normale döndü'} (10Y–2Y {ef(e):+.2f})" if isaret_degisti else "")
                b.foto(yol, ac, f"dunya:{dt.date.today()}", 72); b.kaydet()
        except Exception as ex:
            print("dünya kartı:", ex)
