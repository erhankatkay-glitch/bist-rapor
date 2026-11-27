# -*- coding: utf-8 -*-
"""Alarm sistemi: alarmlar.txt'deki kuralları kontrol eder, tetiklenenleri Telegram'a gönderir.
GitHub Actions ile 30 dakikada bir çalışır. Durum (aynı alarmın tekrar gönderilmemesi için) bulten
dalındaki alarm/durum.json dosyasında tutulur; tetiklenen son alarmlar alarm/son.json'a yazılır.

Kural örnekleri (alarmlar.txt):
  THYAO > 350            fiyat 350'nin üzerine çıkınca
  BTC/TRY < 3000000      fiyat 3.000.000'un altına inince
  PEPE/USDT %5           günlük değişim ±%5'i aşınca
  ASELS RSI < 30         günlük RSI 30'un altına inince
  ETH/USDT PUAN > 70     teknik puan 70'in üzerine çıkınca
  THYAO FORMASYON        yeni formasyon teyidi / kırılım / yapı kırılımı
  ASELS KAP              KAP konulu yeni önemli haber
  OTOMATIK               takip listelerindeki tüm varlıklar için formasyon ve KAP alarmları"""
import os, re, sys, json, datetime as dt


def _s(x):
    import tasarim as TS
    return TS._sayi(x)


def _p(x):
    return ("+" if x > 0 else "-" if x < 0 else "") + "%" + f"{abs(x) * 100:.1f}".replace(".", ",")

TSI = dt.timezone(dt.timedelta(hours=3))
DOSYA = "alarmlar.txt"
DURUM = os.path.join("alarm_cikti", "durum.json")
SON = os.path.join("alarm_cikti", "son.json")


def kurallar(metin):
    K = []
    for satir in metin.splitlines():
        s = satir.split("#")[0].strip().upper().replace(",", ".")
        if not s: continue
        if s == "OTOMATIK": K.append({"tip": "otomatik", "metin": s}); continue
        m = re.match(r"^(\S+)\s+(RSI|PUAN)\s*([<>])\s*([\d.]+)$", s)
        if m: K.append({"tip": m.group(2).lower(), "kod": m.group(1), "op": m.group(3), "deger": float(m.group(4)), "metin": s}); continue
        m = re.match(r"^(\S+)\s*([<>])\s*([\d.]+)$", s)
        if m: K.append({"tip": "fiyat", "kod": m.group(1), "op": m.group(2), "deger": float(m.group(3)), "metin": s}); continue
        m = re.match(r"^(\S+)\s+%\s*([\d.]+)$", s)
        if m: K.append({"tip": "yuzde", "kod": m.group(1), "deger": float(m.group(2)) / 100, "metin": s}); continue
        m = re.match(r"^(\S+)\s+(FORMASYON|KAP)$", s)
        if m: K.append({"tip": m.group(2).lower(), "kod": m.group(1), "metin": s}); continue
        # Aşama 10: kullanıcı tanımlı teknik alarmlar
        m = re.match(r"^(\S+)\s+EMA\s*(\d+)\s*/\s*(\d+)$", s)
        if m: K.append({"tip": "ema", "kod": m.group(1), "hizli": int(m.group(2)), "yavas": int(m.group(3)), "metin": s}); continue
        m = re.match(r"^(\S+)\s+(HACIM|RVOL)\s*>\s*([\d.]+)$", s)
        if m: K.append({"tip": "hacim", "kod": m.group(1), "deger": float(m.group(3)), "metin": s}); continue
        m = re.match(r"^(\S+)\s+FIB\s*([\d.]+)$", s)
        if m: K.append({"tip": "fib", "kod": m.group(1), "deger": float(m.group(2)), "metin": s}); continue
        m = re.match(r"^(\S+)\s+(DESTEK|DIRENC|DİRENÇ|KIRILIM|FVG|BOS|CHOCH|HARMONIK|HARMONİK|SINYAL|SİNYAL|TEMEL)$", s)
        if m:
            t = {"DİRENÇ": "DIRENC", "HARMONİK": "HARMONIK", "SİNYAL": "SINYAL"}.get(m.group(2), m.group(2))
            K.append({"tip": t.lower(), "kod": m.group(1), "metin": s}); continue
        m = re.match(r"^(\S+)\s+(IGNE|İĞNE|IĞNE)$", s)
        if m: K.append({"tip": "igne", "kod": m.group(1), "metin": s}); continue
        m = re.match(r"^TAKVIM(?:\s+(\S+))?$", s.replace("TAKVİM", "TAKVIM"))
        if m: K.append({"tip": "takvim", "kod": m.group(1) or "HEPSI", "metin": s}); continue
        m = re.match(r"^PORTFOY\s+RISK\s*([\d.]+)$", s.replace("PORTFÖY", "PORTFOY").replace("RİSK", "RISK"))
        if m: K.append({"tip": "pfrisk", "deger": float(m.group(1)) / 100, "metin": s}); continue
        print("Anlaşılamayan kural:", satir, file=sys.stderr)
    return K


def portfoy_kontrol(yeni, durum, teknik, bugun):
    """Kayıtlı portföy (portfoy.txt) için kişisel uyarılar; varlık başına tek satır, her uyarı türü günde bir kez."""
    import portfoy as P
    out = []
    for kod, miktar, maliyet in P.takip():
        try:
            s = teknik(kod); g = s["tf"]["G"]; p = float(g["fiyat"]); d = g.get("degisim") or 0.0
        except Exception as ex:
            print(f"Portföy {kod}: {ex}", file=sys.stderr); continue
        parca = []
        def bir(tur, metin):
            a = f"PF|{kod}|{tur}|{bugun}"
            if not durum.get(a) and not yeni.get(a):
                yeni[a] = True; parca.append(metin)
        ters = [ad_.split(": ", 1)[-1].split(" – ")[0] for ad_, yon, ac, guc in g["sinyal"] if yon < 0 and any(
            w in ad_ for w in ("TEYİT", "KIRILIM", "BOS", "CHoCH", "Ölüm kesişimi", "SuperTrend sat", "Balina satışı", "dağıtım",
                               "Harmonik:", "emir bloğu testi", "Kırıcı blok", "QD:", "Kurulum:"))]
        yeni_ters = [x for x in dict.fromkeys(ters) if not durum.get(f"PF|{kod}|sin|{x[:40]}|{bugun}")]
        for x in yeni_ters: yeni[f"PF|{kod}|sin|{x[:40]}|{bugun}"] = True
        if yeni_ters: parca.append("ters sinyal: " + ", ".join(yeni_ters[:4]))
        onceki = durum.get(f"PFET|{kod}"); yeni[f"PFET|{kod}"] = g["etiket"]
        if g["etiket"] in ("SAT", "GÜÇLÜ SAT") and onceki not in (None, "SAT", "GÜÇLÜ SAT"):
            bir("etiket", f"teknik görünüm {onceki} → {g['etiket']} ({g['puan']:.0f})")
        ds = durum.get(f"PFDS|{kod}")
        if ds and p < ds * 0.997: bir("destek", f"destek {_s(ds)} kırıldı")
        if g["sr"]["destek"]: yeni[f"PFDS|{kod}"] = float(g["sr"]["destek"][0][0])
        if d <= (-0.07 if _kripto(kod) else -0.04): bir("dusus", f"sert düşüş {_p(d)}")
        if maliyet:
            kz = p / maliyet - 1
            if kz <= -0.08: bir("zarar", f"maliyete göre {_p(kz)} (maliyet {_s(maliyet)})")
            elif kz >= 0.15: bir("kar", f"maliyete göre {_p(kz)} kârda, kâr koruma düşünülebilir")
        if parca:
            out.append(f"💼 {_ad(kod)}: ⚠️ " + " · ".join(parca) + f" · fiyat {_s(p)} ({_p(d)})")
    return out


def _ad(kod):
    import bist_teknik as T
    if kod.endswith(".US"):
        import bist_abd as AB
        return f"{kod[:-3]} ({AB.ad(kod)})"
    return T.KURESEL[kod][1] if kod in T.KURESEL else {"XU100": "BIST 100", "XU030": "BIST 30", "XBANK": "BIST Banka"}.get(kod, kod)


def _kripto(kod):
    import bist_kripto as KR, bist_varlik as V
    return KR.kripto_mu(kod) or (kod in V.VARLIKLAR and V.VARLIKLAR[kod][2] == "kripto")


def anlik(kod):
    """(son fiyat, günlük değişim) — kripto borsadan, diğerleri Yahoo'dan (BIST ~15 dk gecikmeli)."""
    if _kripto(kod):
        import bist_kripto as KR
        baz, par, borsa = KR.coz(kod)
        if borsa == "Binance":
            t = KR._get(f"{KR.BINANCE}/ticker/24hr", symbol=f"{baz}{par}")
            return float(t["lastPrice"]), float(t["priceChangePercent"]) / 100
        t = KR._get(f"{KR.OKX}/market/ticker", instId=f"{baz}-{par}")["data"][0]
        return float(t["last"]), float(t["last"]) / float(t["sodUtc0"]) - 1
    import yfinance as yf, bist_teknik as T
    def _son_ve_onceki(y):
        g = yf.Ticker(y).history(period="5d", interval="15m")
        d = yf.Ticker(y).history(period="10d")
        if g is None or g.empty or d is None or d.empty: raise ValueError(f"{kod} fiyatı alınamadı")
        g = g.dropna(subset=["Close"]); son = float(g["Close"].iloc[-1]); gun = g.index[-1].date()
        gd0 = d["Close"].dropna()
        if len(gd0) and gd0.index[-1].date() == gun:
            son = float(gd0.iloc[-1])   # günlük bar o günü içeriyorsa onun kapanışı esas (BIST kapanış seansı dahil resmi fiyat)
        if len(gd0) and gd0.index[-1].date() > gun:
            # Gün içi akış durmuş (ör. vadeli metallerde tatil sonrası 15 dk veri gelmiyor) ama günlük bar daha yeni:
            # son fiyat anlık özetten / günlükten, önceki kapanış günlük seriden alınır.
            gun = gd0.index[-1].date()
            try: son = float(yf.Ticker(y).fast_info["lastPrice"]) or float(gd0.iloc[-1])
            except Exception: son = float(gd0.iloc[-1])
            once = gd0[[t.date() < gun for t in gd0.index]]
            return son, (float(once.iloc[-1]) if len(once) else son)
        # önceki kapanış: son işlem gününden ÖNCEKİ işlem gününün kapanışı. Yahoo günlük verisi o günü henüz içermiyorsa
        # (XU100'de sık olur) gün içi verideki o günün son fiyatı kullanılır.
        gunler = sorted({t.date() for t in g.index if t.date() < gun})
        once_gun = gunler[-1] if gunler else None
        gd = d["Close"].dropna(); gd_gun = {t.date(): float(v) for t, v in gd.items()}
        if once_gun and once_gun in gd_gun:
            return son, gd_gun[once_gun]
        if once_gun:
            return son, float(g[[t.date() == once_gun for t in g.index]]["Close"].iloc[-1])
        once = gd[[t.date() < gun for t in gd.index]]
        return son, (float(once.iloc[-1]) if len(once) else son)
    if kod.upper() in ("ALTIN", "GRAMALTIN"):    # spot ons: Binance PAXG (vadeli GC=F spotun ~%1 üstünde olabilir)
        try:
            import bist_makro as MK
            b = MK.binance_fiyat("PAXGUSDT"); son, onceki = b["fiyat"], b["fiyat"] / (1 + b["d24"])
            if kod.upper() == "GRAMALTIN":
                k_son, k_once = _son_ve_onceki("TRY=X")
                son, onceki = son * k_son / 31.1035, onceki * k_once / 31.1035
            return son, son / onceki - 1
        except Exception:
            pass
    y, _ = T.yahoo_sembol(kod)
    son, onceki = _son_ve_onceki(y)
    if kod.upper() == "GRAMALTIN":   # ons altın ($) × USD/TRY / 31,1035
        k_son, k_once = _son_ve_onceki("TRY=X")
        son, onceki = son * k_son / 31.1035, onceki * k_once / 31.1035
    return son, son / onceki - 1


def teknik_alarm(k, g):
    """Kullanıcı tanımlı teknik koşullar → [(ikon, olay metni, günde_bir_mi)]. g: tf_analiz (günlük).
    Gün içinde (mum kapanmadan) oluşan durumlar 'kapanış teyidi bekleniyor' notuyla gelir."""
    import veri_kalite as VK
    G, h = g["G"], g["h"]; c = h["Close"]; n = len(c); out = []
    acik = VK.piyasa_acik(VK.tur_bul(_yahoo(k["kod"])))
    not_ = " · mum kapanmadı, kapanış teyidi bekleniyor" if acik else ""
    tarih = f"(günlük, {g['tarih']:%d.%m})"
    if k["tip"] == "ema":
        e1 = c.ewm(span=k["hizli"], adjust=False).mean(); e2 = c.ewm(span=k["yavas"], adjust=False).mean()
        if n > 2:
            if e1.iloc[-1] > e2.iloc[-1] and e1.iloc[-2] <= e2.iloc[-2]:
                out.append(("🟢", f"EMA{k['hizli']} EMA{k['yavas']}'yi yukarı kesti {tarih}{not_}", True))
            if e1.iloc[-1] < e2.iloc[-1] and e1.iloc[-2] >= e2.iloc[-2]:
                out.append(("🔴", f"EMA{k['hizli']} EMA{k['yavas']}'yi aşağı kesti {tarih}{not_}", True))
    elif k["tip"] == "hacim":
        rv = float(G["RVOL"].iloc[-1]) if "RVOL" in G and G["RVOL"].notna().iloc[-1] else None
        if rv is not None and rv >= k["deger"]:
            out.append(("📊", f"Göreli hacim {rv:.1f}x (eşik {k['deger']:g}x) {tarih}".replace(".", ","), True))
    elif k["tip"] == "fib":
        fb = g.get("fib")
        if fb:
            r = k["deger"] if k["deger"] < 1.0001 else k["deger"] / 100
            sev = fb["seviye"].get(min(fb["seviye"], key=lambda x: abs(x - r)))
            if sev and float(h["Low"].iloc[-1]) <= sev * 1.003 and float(h["High"].iloc[-1]) >= sev * 0.997:
                out.append(("🟢" if fb["yukari"] else "🔴", f"Fibonacci %{r * 100:.1f} seviyesine ({_s(sev)}) geldi {tarih}".replace(".", ","), True))
    elif k["tip"] in ("destek", "direnc", "kirilim"):
        p0, p1 = float(c.iloc[-2]), float(c.iloc[-1])
        ds = [v for v, _ in g["sr"]["destek"]] + [v for v, _ in g["sr"]["direnc"]]
        for v in ds:
            if k["tip"] in ("destek", "kirilim") and p0 >= v > p1:
                out.append(("🔴", f"{_s(v)} desteği aşağı kırıldı {tarih}{not_}", True))
            if k["tip"] in ("direnc", "kirilim") and p0 <= v < p1:
                out.append(("🟢", f"{_s(v)} direnci yukarı kırıldı {tarih}{not_}", True))
    elif k["tip"] == "fvg":
        for ad, alt, ust, t in g["pa"].get("fvg", []):
            if t == h.index[-1] or t == h.index[-2]:
                out.append(("🟢" if "Boğa" in ad else "🔴", f"Yeni {ad} oluştu: {_s(alt)}–{_s(ust)} {tarih}", False))
    elif k["tip"] in ("bos", "choch"):
        for ad, y, ac in g["pa"].get("olaylar", []):
            if ("BOS" in ad and k["tip"] == "bos") or ("CHoCH" in ad and k["tip"] == "choch") or (k["tip"] == "bos" and "CHoCH" in ad):
                out.append(("🟢" if y > 0 else "🔴", f"{ad} {tarih}{not_}", True))
    elif k["tip"] == "harmonik":
        for f in g.get("harm", []):
            if f["durum"] == "tamamlandı":
                out.append(("🟢" if f["yon"] == 1 else "🔴", f"Harmonik {f['ad']} tamamlandı · dönüş bölgesi {_s(f['bolge'][0])}–{_s(f['bolge'][1])} {tarih}", False))
    elif k["tip"] == "sinyal":
        try:
            import tarayici as TRY
            x = TRY.son_sinyal(h, G, _piyasa(k["kod"]))
            if x and x["yas"] == 0:
                out.append(("🟢" if x["yon"] == 1 else "🔴", f"Yeni kurulum: {x['kurulum']} {tarih}{not_}", True))
        except Exception as ex:
            print("sinyal alarmı:", ex, file=sys.stderr)
    return out


def _yahoo(kod):
    try:
        import bist_teknik as T
        return T.yahoo_sembol(kod)[0]
    except Exception:
        return kod


def _piyasa(kod):
    k = kod.upper()
    if _kripto(k): return "kripto"
    if k.endswith(".US"): return "abd"
    import bist_varlik as V
    return "emtia" if k in V.VARLIKLAR else "bist"


def yaklasan_veriler(ulke="HEPSI", dakika=75):
    """Ekonomik takvimde önümüzdeki `dakika` içinde açıklanacak yüksek etkili veriler (bülten dalındaki haber/takvim.json)."""
    try:
        import urllib.request
        tk = json.loads(urllib.request.urlopen("https://raw.githubusercontent.com/erhankatkay-glitch/bist-rapor/bulten/haber/takvim.json", timeout=15).read())
    except Exception:
        return []
    simdi = dt.datetime.now(dt.timezone.utc); out = []
    for e in tk.get("liste", []) if isinstance(tk, dict) else tk:
        try:
            t = dt.datetime.fromisoformat(e["zaman"])
            if t.tzinfo is None: t = t.replace(tzinfo=TSI)
            if 0 <= (t - simdi).total_seconds() <= dakika * 60 and (ulke == "HEPSI" or str(e.get("ulke", "")).upper() == ulke):
                out.append(e)
        except Exception:
            continue
    return out


def portfoy_riski(esik, fiyat_fn):
    """portfoy.txt'teki pozisyonların toplam maliyete göre zararı eşiği aşarsa uyarı metni."""
    try:
        import portfoy as P
        tm = td = 0.0; en_kotu = None
        for kod, miktar, maliyet in P.takip():
            if not (miktar and maliyet): continue
            p, _ = fiyat_fn(kod); tm += miktar * maliyet; td += miktar * p
            kz = p / maliyet - 1
            if en_kotu is None or kz < en_kotu[1]: en_kotu = (kod, kz)
        if tm and td / tm - 1 <= -esik:
            return (f"💼 PORTFÖY: ⚠️ toplam zarar {_p(td / tm - 1)} (eşik −%{esik * 100:.0f})"
                    + (f"; en çok kaybettiren {en_kotu[0]} {_p(en_kotu[1])}" if en_kotu else ""))
    except Exception as ex:
        print("portföy riski:", ex, file=sys.stderr)
    return None


IGNE_AKTIF = []     # bu turda tetiklenen iğne uyarıları (uygulamadaki üst bant için alarm/igne.json'a yazılır)


def tara(K, durum):
    """Kuralları değerlendirir → (bildirimler, yeni durum)."""
    import bist_teknik as T
    bildir, yeni = [], dict(durum)
    analiz_onb = {}
    def teknik(kod):
        if kod not in analiz_onb: analiz_onb[kod] = T.analiz(kod, tfler=("G",))
        return analiz_onb[kod]
    bugun = dt.datetime.now(TSI).strftime("%Y-%m-%d")
    hedefler = []
    for k in K:
        if k["tip"] == "otomatik":
            for yol in ("takip_listesi.txt", "teknik_takip.txt", "portfoy.txt"):
                if os.path.exists(yol):
                    for s in open(yol, encoding="utf-8"):
                        s = s.split("#")[0].strip().upper()
                        s = s.split()[0] if s else ""   # portföy satırı: KOD MİKTAR @ MALİYET
                        if s:
                            import bist_varlik as V
                            hedefler.append({"tip": "formasyon", "kod": s, "metin": f"{s} FORMASYON (otomatik)"})
                            if not _kripto(s) and s not in V.VARLIKLAR and not s.endswith(".US"): hedefler.append({"tip": "kap", "kod": s, "metin": f"{s} KAP (otomatik)"})
        else:
            hedefler.append(k)
    tekil = {}
    for k in hedefler: tekil.setdefault((k["tip"], k.get("kod"), k.get("op"), k.get("deger")), k)
    hedefler = list(tekil.values())
    for k in hedefler:
        anahtar = k["metin"]
        try:
            if k["tip"] in ("fiyat", "yuzde"):
                p, d = anlik(k["kod"])
                if k["tip"] == "fiyat":
                    kosul = p > k["deger"] if k["op"] == ">" else p < k["deger"]
                    if kosul and not durum.get(anahtar):
                        bildir.append(f"🔔 {_ad(k['kod'])} fiyatı {_s(k['deger'])} seviyesinin {'üzerine çıktı' if k['op'] == '>' else 'altına indi'}: {_s(p)}")
                    yeni[anahtar] = bool(kosul)
                else:
                    gun_anahtar = f"{anahtar}|{bugun}"
                    if abs(d) >= k["deger"] and not durum.get(gun_anahtar):
                        bildir.append(f"⚡ {_ad(k['kod'])} bugün {_p(d)} hareket etti (fiyat {_s(p)})")
                        yeni[gun_anahtar] = True
            elif k["tip"] in ("rsi", "puan"):
                s = teknik(k["kod"]); g = s["tf"]["G"]
                x = float(g["G"]["RSI"].iloc[-1]) if k["tip"] == "rsi" else float(s["puan"])
                kosul = x > k["deger"] if k["op"] == ">" else x < k["deger"]
                if kosul and not durum.get(anahtar):
                    bildir.append(f"📈 {_ad(k['kod'])} {'RSI' if k['tip'] == 'rsi' else 'teknik puan'} {x:.0f} ({k['op']} {k['deger']:g}) · fiyat {_s(g['fiyat'])}")
                yeni[anahtar] = bool(kosul)
            elif k["tip"] == "formasyon":
                s = teknik(k["kod"]); g = s["tf"]["G"]
                for ad, yon, ac, guc in g["sinyal"]:
                    if yon == 0 or not any(w in ad for w in ("TEYİT", "KIRILIM", "BOS", "CHoCH", "Altın kesişim", "Ölüm kesişimi",
                                                            "Harmonik:", "emir bloğu testi", "Kırıcı blok")): continue
                    a2 = f"{k['kod']}|{ad}|{g['tarih']:%Y-%m-%d}"
                    if not durum.get(a2):
                        fy = f" · fiyat {_s(g['fiyat'])}" + (f" ({_p(g['degisim'])})" if g.get("degisim") is not None else "")
                        bildir.append(f"{'🟢' if yon > 0 else '🔴'} {_ad(k['kod'])}: {ad.split(': ', 1)[-1]} (günlük, {g['tarih']:%d.%m}){fy}")
                        yeni[a2] = True
            elif k["tip"] in ("ema", "hacim", "fib", "destek", "direnc", "kirilim", "fvg", "bos", "choch", "harmonik", "sinyal"):
                s = teknik(k["kod"]); g = s["tf"]["G"]
                for ikon, olay, gun_tek in teknik_alarm(k, g):
                    a2 = f"{k['metin']}|{olay[:40]}|{g['tarih']:%Y-%m-%d}" if gun_tek else f"{k['metin']}|{olay[:40]}"
                    if not durum.get(a2) and not yeni.get(a2):
                        fy = f" · fiyat {_s(g['fiyat'])}" + (f" ({_p(g['degisim'])})" if g.get("degisim") is not None else "")
                        bildir.append(f"{ikon} {_ad(k['kod'])}: {olay}{fy}")
                    yeni[a2] = True
            elif k["tip"] == "temel":
                gun_k = f"{k['metin']}|kontrol|{bugun}"
                if not durum.get(gun_k):                       # mali tablolar günde bir kez kontrol edilir
                    yeni[gun_k] = True
                    try:
                        import bist_isyatirim as IY
                        f_ = IY.finansallar(k["kod"], ceyrek_sayi=2)
                        donem = str(f_.get("son_donem") or (f_.get("donemler") or [""])[-1]) if isinstance(f_, dict) else ""
                    except Exception as ex:
                        donem = ""; print(f"temel {k['kod']}: {ex}", file=sys.stderr)
                    once = durum.get(f"{k['metin']}|donem")
                    if donem:
                        yeni[f"{k['metin']}|donem"] = donem
                        if once and donem != once:
                            bildir.append(f"📰 {k['kod']} · Yeni finansal tablo: {donem} dönemi açıklandı (önceki {once}); temel analizi güncelleyin.")
            elif k["tip"] == "igne":
                import igne as IG
                baz = k["kod"].split("/")[0].split("-")[0]
                H, L, C = IG.mumlar(f"{baz}USDT", "1h", 300)
                u = IG.tetik(H, L, C)
                if u:
                    a2 = f"IGNE|{baz}|{u['yon']}|{round(u['seviyeler'][0], -1)}"
                    baslik, ayr = IG.metin(u, baz)
                    if not durum.get(a2) and not yeni.get(a2):
                        bildir.append(f"⚡ {baz}: {baslik} · {ayr.split(' · Algoritmik')[0]}")
                        IGNE_AKTIF.append({"kod": baz, "yon": u["yon"], "baslik": baslik, "metin": ayr, "neden": u.get("neden", ""),
                                           "seviyeler": u["seviyeler"], "fiyat": u["fiyat"],
                                           "zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                                           "bitis": (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=4)).isoformat(timespec="seconds")})
                    yeni[a2] = True
            elif k["tip"] == "takvim":
                for e in yaklasan_veriler(k["kod"]):
                    a2 = f"TAKVIM|{e['zaman']}|{e['baslik'][:40]}"
                    if not durum.get(a2) and not yeni.get(a2):
                        t_ = dt.datetime.fromisoformat(e["zaman"]).astimezone(TSI)
                        bildir.append(f"🗓 {e['ulke']} · {e['baslik']}: {t_:%H:%M}'de açıklanacak"
                                      + (f" · beklenti {e['beklenti']}" if e.get("beklenti") else "") + (f" · önceki {e['onceki']}" if e.get("onceki") else ""))
                    yeni[a2] = True
            elif k["tip"] == "pfrisk":
                m_ = portfoy_riski(k["deger"], anlik)
                gun_k = f"{k['metin']}|{bugun}"
                if m_ and not durum.get(gun_k):
                    bildir.append(m_); yeni[gun_k] = True
            elif k["tip"] == "kap":
                import bist_borsa as BB, bist_veri as bv, bist_varlik as V
                if _kripto(k["kod"]) or k["kod"] in V.VARLIKLAR or k["kod"].endswith(".US"): continue
                for x in BB.kap_haberleri(k["kod"], bv.sirket_adi(k["kod"]), gun=3, adet=6):
                    a2 = f"{k['kod']}|KAP|{x['baslik'][:80]}"
                    # bilgi taşımayan başlıklar (rakamsız pay işlemi / sipariş bildirimi) gönderilmez
                    if x["konu"] in ("Ortak / yönetici pay işlemi", "Yeni iş / sipariş / sözleşme", "Finansal sonuçlar") and not re.search(r"\d", x["baslik"].replace(k["kod"], "")):
                        yeni[a2] = True; continue
                    konu_gun = f"{k['kod']}|KAPKONU|{x['konu']}|{bugun}"   # aynı konuda günde tek bildirim
                    if not durum.get(a2) and not durum.get(konu_gun) and not yeni.get(konu_gun):
                        yeni[konu_gun] = True
                        try:
                            p_, d_ = anlik(k["kod"]); fy = f" · fiyat {_s(p_)} ({_p(d_)})"
                        except Exception:
                            fy = ""
                        bildir.append(f"📰 {k['kod']} · {x['konu']}: {x['baslik'][:140]}{fy}" + (f"⟦{x['link']}⟧" if x.get("link") else ""))
                    yeni[a2] = True   # gönderilmese de görüldü say (aynı haberin diğer başlıkları ertesi gün gelmesin)
        except Exception as ex:
            print(f"{anahtar}: {ex}", file=sys.stderr)
    try:
        bildir += portfoy_kontrol(yeni, durum, teknik, bugun)
    except Exception as ex:
        print("Portföy kontrolü:", ex, file=sys.stderr)
    bildir = list(dict.fromkeys(bildir))
    # eski günlük anahtarları temizle
    sinir = (dt.datetime.now(TSI) - dt.timedelta(days=30)).strftime("%Y-%m-%d")
    yeni = {k: v for k, v in yeni.items() if not re.search(r"\d{4}-\d{2}-\d{2}", k) or max(re.findall(r"\d{4}-\d{2}-\d{2}", k)) >= sinir}
    return bildir, yeni


GRUP = [("💼", "💼 <b>PORTFÖYÜNÜZ</b>"), ("⚡🔔", "⚡ <b>Sert hareket ve fiyat seviyeleri</b>"), ("🟢🔴", "🧭 <b>Formasyon ve kırılımlar</b>"),
        ("📈", "📈 <b>RSI ve teknik puan</b>"), ("📊", "📊 <b>Hacim</b>"),
        ("🗓", "🗓 <b>Ekonomik takvim</b>"), ("📰", "📰 <b>Şirket haberleri (KAP)</b>")]


def _satir(m):
    g, sat, url = _satir_ham(m)
    if isinstance(sat, dict) and not sat.get("logo"):
        ilk = str(sat.get("sol", "")).split(" ")[0].strip("()·")
        if ilk: sat["logo"] = (ilk, None)
    return g, sat, url


def _satir_ham(m):
    """Alarm metnini kart satırına çevirir: (grup, satır sözlüğü, bağlantı)."""
    import kart as K
    C = K.C; url = None
    if "⟦" in m and m.endswith("⟧"): m, url = m[:-1].split("⟦", 1)
    ik, govde = m[:1], m[1:].strip()
    fiyat = degis = None
    mt = re.search(r" · fiyat (\S+)(?: \(([^)]+)\))?$", govde)
    if mt: fiyat, degis = mt.group(1), mt.group(2); govde = govde[:mt.start()]
    renk_d = (C["kirmizi"] if degis and degis.startswith("-") else C["yesil"]) if degis else None
    if ik == "⚡":
        mm = re.match(r"(.+?) bugün (\S+) hareket etti \(fiyat (\S+)\)", govde)
        if mm:
            d = mm.group(2); dus = d.startswith("-")
            return "⚡", {"sol": mm.group(1), "sag": d.replace("-", "−"), "sag_renk": C["kirmizi"] if dus else C["yesil"],
                          "nokta": C["kirmizi"] if dus else C["yesil"], "alt": f"Gün içinde sert {'düşüş' if dus else 'yükseliş'} · fiyat {mm.group(3)}"}, url
    if ik == "🔔":
        mm = re.match(r"(.+?) fiyatı (.+?): (\S+)$", govde)
        if mm: return "⚡", {"sol": mm.group(1), "sag": mm.group(3), "nokta": C["altin"], "alt": "Fiyat " + mm.group(2)}, url
    if ":" in govde:
        sol, alt = govde.split(":", 1)
    else:
        sol, alt = govde, ""
    alt = alt.strip().replace("⚠️ ", "").replace("-%", "−%")
    if degis: alt += f" · günlük {degis.replace('-', '−')}"
    nokta = {"🟢": C["yesil"], "🔴": C["kirmizi"], "📈": C["mavi"], "📰": C["turkuaz"], "💼": C["altin"]}.get(ik, C["soluk"])
    if ik == "📰" and degis: nokta = renk_d
    if ik in ("📊", "🗓"): nokta = C["altin"]
    if ik == "⚡": nokta = C["altin"]
    return ik if ik in ("💼", "📈", "📰", "📊", "🗓", "⚡") else "🟢" if ik in ("🟢", "🔴") else "•", {"sol": sol.strip(), "sag": fiyat, "nokta": nokta, "alt": alt}, url


GRUP_KART = [("💼", "Portföyünüz", "altin"), ("⚡", "Sert hareket ve fiyat seviyeleri", "altin"), ("🟢", "Formasyon ve kırılımlar", "mavi"),
             ("📈", "RSI ve teknik puan", "altin"), ("📊", "Hacim", "altin"), ("🗓", "Ekonomik takvim", "altin"),
             ("📰", "Şirket haberleri (KAP)", "altin"), ("•", "Diğer", "soluk")]


def gonder(mesajlar):
    """Alarmlar görsel kart olarak (konu başlıklarına göre gruplu) sessiz gönderilir; 12 saat sonra silinir."""
    if not mesajlar: return False
    import tg
    b = tg.Bot("alarm")
    if not b.aktif: return False
    z = dt.datetime.now(TSI)
    for i in range(0, len(mesajlar), 14):
        parca = mesajlar[i:i + 14]; anahtar = f"alarm:{z:%Y%m%d%H%M}:{i}"
        gonderildi = False
        try:
            import kart as K
            sat = [_satir(m) for m in parca]
            bol = [{"baslik": ad, "renk": K.C[r], "satirlar": [x[1] for x in sat if x[0] == g]} for g, ad, r in GRUP_KART]
            bol = [x for x in bol if x["satirlar"]]
            os.makedirs("alarm_cikti", exist_ok=True); yol = os.path.join("alarm_cikti", f"kart_{i}.png")
            pf = any(x[0] == "💼" for x in sat)
            K.bildirim_karti(f"ALARMLAR  ·  {z:%d.%m %H:%M}", f"{len(parca)} yeni alarm" if not pf else "Portföy uyarısı",
                             "Fiyat, formasyon ve şirket haberleri", bol, yol, vurgu=K.C["altin"])
            linkler = [(x[1]["sol"], x[2]) for x in sat if x[2]]
            alt = f"🔔 <b>{len(parca)} yeni alarm</b> · {z:%d.%m %H:%M}"
            if linkler: alt += "\n📰 " + " · ".join(f'<a href="{u}">{tg_kac(s_)[:24]}</a>' for s_, u in linkler[:6])
            gonderildi = bool(b.foto(yol, alt, anahtar, 12))
        except Exception as ex:
            print("Alarm kartı çizilemedi:", ex, file=sys.stderr)
        if not gonderildi:
            s_ = [f"🔔 <b>ALARMLAR</b> · {z:%d.%m %H:%M}", tg.AYRAC]
            for ikonlar, baslik in GRUP:
                g = [m for m in parca if m[:1] in ikonlar]
                if g: s_ += [baslik, "<blockquote>" + "\n".join(tg_kac(m) for m in g) + "</blockquote>"]
            b.mesaj("\n".join(s_), anahtar, 12, yerine=False)
    b.kaydet()
    return True


def tg_kac(s):
    """Metni HTML'e çevirir; '⟦url⟧' ile eklenmiş bağlantıyı 'habere git' linkine dönüştürür."""
    s = str(s); url = None
    if "⟦" in s and s.endswith("⟧"):
        s, url = s[:-1].split("⟦", 1)
    t = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # varlık adını kalın yaz: "<ikon> VARLIK: …", "⚡ VARLIK bugün …", "🔔 VARLIK fiyatı …", "📰 KOD · konu: …"
    t = re.sub(r"^(\S+) (.+?)(?=: | bugün | fiyatı | RSI | teknik puan | · )", r"\1 <b>\2</b>", t, count=1)
    if url: t += f' · <a href="{url.replace(chr(34), "")}">habere git</a>'
    return t


def main():
    if not os.path.exists(DOSYA):
        print("alarmlar.txt yok."); return
    K = kurallar(open(DOSYA, encoding="utf-8").read())
    os.makedirs("alarm_cikti", exist_ok=True)
    durum = json.load(open(DURUM, encoding="utf-8")) if os.path.exists(DURUM) else {}
    bildir, yeni = tara(K, durum)
    son = json.load(open(SON, encoding="utf-8")) if os.path.exists(SON) else []
    # geçmiş temizliği: emtia/kripto için yanlış eşleşmiş KAP haberleri ve aynı dakikadaki tekrarlar
    import bist_varlik as V
    gor, temiz = set(), []
    for x in son:
        kod = x["mesaj"].split(" ", 2)[1] if x["mesaj"].startswith("📰") and len(x["mesaj"].split(" ")) > 1 else None
        if kod and (kod in V.VARLIKLAR or _kripto(kod)): continue
        a = (x["zaman"], x["mesaj"])
        if a in gor: continue
        gor.add(a); temiz.append(x)
    son = temiz
    zaman = dt.datetime.now(TSI).strftime("%d.%m.%Y %H:%M")
    son = [{"zaman": zaman, "mesaj": m} for m in bildir] + son
    json.dump(yeni, open(DURUM, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    json.dump(son[:300], open(SON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    try:   # tetiklenmiş, süresi dolmamış iğne uyarıları (uygulamanın üst bandı yalnız bunları gösterir)
        yol_ig = os.path.join("alarm_cikti", "igne.json")
        eski = json.load(open(yol_ig, encoding="utf-8")) if os.path.exists(yol_ig) else []
        simdi_ = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        json.dump([x for x in eski + IGNE_AKTIF if x.get("bitis", "") > simdi_], open(yol_ig, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception as ex:
        print("iğne kaydı:", ex, file=sys.stderr)
    json.dump({"kontrol": zaman, "kural": len(K)}, open(os.path.join("alarm_cikti", "son_kontrol.json"), "w"), ensure_ascii=False)
    print(f"{len(K)} kural, {len(bildir)} yeni alarm. Telegram: {'gönderildi' if gonder(bildir) else 'ayarlı değil / gönderilecek alarm yok'}")
    for m in bildir: print(" ", m)


if __name__ == "__main__":
    main()
