# -*- coding: utf-8 -*-
"""Kapanış sonrası teknik bülten: bir piyasadaki tüm varlıkları günlük/haftalık/aylık analiz eder,
bülten PDF'i, özet tablo, grafik görselleri ve takip listesi raporlarını cikti/<piyasa>/ altına yazar;
TELEGRAM_TOKEN ve TELEGRAM_CHAT_ID tanımlıysa telefona gönderir.
Kullanım: python teknik_bulten.py bist|kripto|emtia"""
import os, sys, json, time, shutil, datetime as dt
import numpy as np
import pandas as pd

import bist_rapor as br
import bist_varlik as V
import bist_veri as bv
import bist_teknik as T
import bist_teknik_rapor as TR

TSI = dt.timezone(dt.timedelta(hours=3))
BASLIK = {"bist": "Kapanış Teknik Bülteni – BIST", "kripto": "Kapanış Teknik Bülteni – Kripto (USDT)",
          "kripto_tl": "Kapanış Teknik Bülteni – Kripto TL Pariteleri", "emtia": "Kapanış Teknik Bülteni – Emtia",
          "abd": "Kapanış Teknik Bülteni – ABD Borsaları"}
SON = {}   # piyasa → {"analizler", "endeks", "satir"}: fırsat motoru aynı analizleri yeniden kullanır
REFERANS = {"bist": "XU100", "kripto": "BTC/USDT", "kripto_tl": "BTC/TRY", "emtia": "ALTIN", "abd": "SP500"}
ABD_EVREN = None   # likit ABD listesi (DataFrame); kapanis.py durum klasörüne kaydeder


def evren(piyasa):
    if piyasa in ("kripto", "kripto_tl"):
        import bist_kripto as KR
        try:
            ev = KR.evren(); print("Kripto evreni:", len(ev), "coin ·", ev.attrs.get("not"))
            return KR.bulten_kodlari("TRY" if piyasa == "kripto_tl" else "USDT", ev)
        except Exception as ex:
            print("Kripto evreni alınamadı, yedek liste:", ex, file=sys.stderr)
            return [k + ("/TRY" if piyasa == "kripto_tl" else "/USDT") for k, v in V.VARLIKLAR.items() if v[2] == "kripto"]
    if piyasa == "emtia":
        return [k for k, v in V.VARLIKLAR.items() if v[2] == "emtia"]
    if piyasa == "abd":
        global ABD_EVREN
        import bist_abd as AB
        tum = AB.tum_hisseler()
        AB.liste_kaydet(tum)
        ABD_EVREN, not_ = AB.likit_hisseler(tum)
        print(not_)
        return list(ABD_EVREN["Kod"])
    try:
        import bist_evren as EV
        df, harz, not_ = EV.bist_listesi()
        print("Hisse evreni:", len(df), "·", not_)
        bv.guncelle({r["Kod"]: r.get("Ad") for _, r in df.iterrows()})
        if len(df) > 200: return sorted(df["Kod"])
    except Exception as ex:
        print("Tam hisse listesi alınamadı, yedek liste:", ex, file=sys.stderr)
    return sorted(bv.tum_sirketler())


def toplu_veri(semboller, sure="10y", parca=100):
    """Yahoo'dan toplu günlük OHLCV. {sembol: DataFrame}"""
    import yfinance as yf
    out = {}
    semboller = list(dict.fromkeys(semboller))
    for i in range(0, len(semboller), parca):
        grup = semboller[i:i + parca]
        for deneme in range(3):
            try:
                df = yf.download(grup, period=sure, interval="1d", auto_adjust=True, progress=False, group_by="ticker", threads=True)
                break
            except Exception as ex:
                print("indirme hatası, tekrar:", ex, file=sys.stderr); time.sleep(5); df = None
        if df is None: continue
        for s in grup:
            try:
                d = df[s] if isinstance(df.columns, pd.MultiIndex) else df
                d = br._naive(d.dropna(subset=["Close"]))
                if len(d) > 40: out[s] = d
            except Exception:
                continue
    return out


def takip(piyasa):
    yol = "teknik_takip.txt"
    kod = [s.strip().upper() for s in open(yol, encoding="utf-8") if s.strip() and not s.startswith("#")] if os.path.exists(yol) else []
    import bist_kripto as KR
    kr = lambda k: KR.kripto_mu(k) or (k in V.VARLIKLAR and V.VARLIKLAR[k][2] == "kripto")
    if piyasa == "bist": return [k for k in kod if k not in V.VARLIKLAR and not kr(k) and not k.endswith(".US")]
    if piyasa in ("kripto", "kripto_tl"):
        par = "TRY" if piyasa == "kripto_tl" else "USDT"
        out = []
        for k in kod:
            if not kr(k): continue
            b, p, bo = KR.coz(k)
            if p == par: out.append(KR.kod_yap(b, p, bo))
        return out
    if piyasa == "abd": return [k for k in kod if k.endswith(".US")]
    return [k for k in kod if k in V.VARLIKLAR and V.VARLIKLAR[k][2] == "emtia"]


def calistir(piyasa, klasor="cikti", veri_fn=None, zorla=False):
    bugun = dt.datetime.now(TSI).date()
    kodlar = evren(piyasa); ref = REFERANS[piyasa]
    if piyasa in ("kripto", "kripto_tl") and veri_fn is None:
        return _kripto_calistir(piyasa, kodlar, ref, klasor)
    semboller = [T.yahoo_sembol(k)[0] for k in kodlar + [ref]] + (["TRY=X", "GC=F"] if piyasa in ("emtia", "kripto_tl") else [])
    print(f"{piyasa}: {len(kodlar)} varlık, veri indiriliyor…")
    veri = veri_fn(semboller) if veri_fn else toplu_veri(semboller, "10y")
    utc_bugun = dt.datetime.now(dt.timezone.utc).date()
    if piyasa in ("kripto", "kripto_tl"):   # 00:00 UTC'de kapanan mum tamamlandı; yeni açılan yarım mumu at
        veri = {k_: d[d.index.date < utc_bugun] for k_, d in veri.items()}
    fn = lambda y, *a: veri[y]
    # Tatil kontrolü: referansın son mumu beklenen kapanış gününe ait değilse bülten üretme
    try:
        son = veri[T.yahoo_sembol(ref)[0]].index[-1].date()
        beklenen = {"bist": bugun, "kripto": utc_bugun - dt.timedelta(days=1), "kripto_tl": utc_bugun - dt.timedelta(days=1), "emtia": utc_bugun,
                    "abd": utc_bugun}[piyasa]
        if not zorla and son < beklenen:
            print(f"Son veri {son}, beklenen {beklenen}: piyasa kapalı/tatil ya da veri gecikmeli. Bülten atlandı.")
            return None
    except Exception as ex:
        print("Tarih kontrolü yapılamadı:", ex, file=sys.stderr)
    analizler, hata = [], {}
    for k in kodlar:
        try:
            s = T.analiz(k, fiyat_fn=fn); analizler.append(s)
        except Exception as ex:
            hata[k] = str(ex)[:80]
    try:
        endeks = T.analiz(ref, fiyat_fn=fn)
        if ref == "XU100": endeks["ad"] = "BIST 100"
        if ref == "SP500": endeks["ad"] = "S&P 500"
    except Exception as ex:
        endeks = None; print("Referans analizi yapılamadı:", ex, file=sys.stderr)
    print(f"Analiz: {len(analizler)} tamam, {len(hata)} hata")
    return _yaz(piyasa, analizler, endeks, ref, klasor, hata)


def _ekler(piyasa, analizler, endeks, satir):
    """Bülten ekleri: göreli güç puanı (RS), sektör rotasyonu (BIST), açığa satış (BIST), likidite (kripto)."""
    import bist_ileri as IL
    ek = {}
    seriler = {s["kod"]: s["tf"]["G"]["h"]["Close"] for s in analizler if s["tf"].get("G")}
    rs = IL.rs_puanlari(seriler)
    for r in satir: r["RS"] = rs.get(r["Kod"])
    if piyasa == "bist":
        try:
            sek = pd.read_csv(bv.LISTE_DOSYA, dtype=str).set_index("Kod")["Sektör"].to_dict() if os.path.exists(bv.LISTE_DOSYA) else {}
            for r in satir: r["Sektör"] = sek.get(r["Kod"])
            gruplar = {}
            for k, c in seriler.items():
                if sek.get(k) and isinstance(sek.get(k), str): gruplar.setdefault(sek[k], []).append(c)
            gruplar = dict(sorted(((k, v) for k, v in gruplar.items() if len(v) >= 5), key=lambda x: -len(x[1]))[:14])
            if endeks and endeks["tf"].get("G"):
                ek["rrg"] = IL.rrg(gruplar, endeks["tf"]["G"]["h"]["Close"])
        except Exception as ex:
            print("RRG hesaplanamadı:", ex, file=sys.stderr)
        try:
            import bist_borsa as BB
            ac = BB.aciga_satis(); sat_ = []
            hs = {s["kod"]: s["tf"]["G"]["h"] for s in analizler if s["tf"].get("G")}
            for _, r in ac.iterrows():
                if r["Kod"] in hs:
                    o = BB.aciga_satis_orani(r, hs[r["Kod"]], ac.attrs.get("bas"), ac.attrs.get("son"))
                    sat_.append({"Kod": r["Kod"], "Açığa satış TL": r["Açığa satış TL"], "Oran": o})
            ek["aciga"] = pd.DataFrame(sat_); ek["aciga_donem"] = ac.attrs.get("donem")
            for r in satir:
                x = ek["aciga"][ek["aciga"]["Kod"] == r["Kod"]]
                r["Açığa satış oranı"] = float(x["Oran"].iloc[0]) if len(x) and pd.notna(x["Oran"].iloc[0]) else None
        except Exception as ex:
            print("Açığa satış verisi alınamadı:", ex, file=sys.stderr)
    if piyasa == "abd":
        try:
            import yfinance as yf, bist_abd as AB
            d = yf.download(list(AB.SEKTOR_ETF), period="2y", interval="1d", auto_adjust=True, progress=False, group_by="ticker")
            gruplar = {AB.SEKTOR_ETF[e]: [br._naive(d[e]["Close"].dropna())] * 2 for e in AB.SEKTOR_ETF if e in d.columns.get_level_values(0)}
            if endeks and endeks["tf"].get("G") and gruplar:
                ek["rrg"] = IL.rrg(gruplar, endeks["tf"]["G"]["h"]["Close"])
        except Exception as ex:
            print("ABD sektör rotasyonu hesaplanamadı:", ex, file=sys.stderr)
    if piyasa in ("kripto", "kripto_tl"):
        try:
            import bist_kripto as KR
            ek["likidite"] = KR.defi_yorum(KR.stablecoin_ozet(), KR.tvl_ozet(), None)
        except Exception:
            pass
    return ek


def _yaz(piyasa, analizler, endeks, ref, klasor, hata=None):
    hata = hata or {}
    satir = [T.ozet_satir(s) for s in analizler]
    try: ekler = _ekler(piyasa, analizler, endeks, satir)
    except Exception as ex: ekler = {}; print("Bülten ekleri:", ex, file=sys.stderr)
    SON[piyasa] = {"analizler": analizler, "endeks": endeks, "satir": satir}
    hedef = os.path.join(klasor, piyasa)
    shutil.rmtree(hedef, ignore_errors=True); os.makedirs(os.path.join(hedef, "grafik"), exist_ok=True); os.makedirs(os.path.join(hedef, "rapor"), exist_ok=True)
    one = sorted(analizler, key=lambda s: -(s["puan"] or 0))
    kirilim = [s for s in one if T.ozet_satir(s)["Kırılım"]]
    secim = list(dict.fromkeys([s["kod"] for s in kirilim[:4]] + [s["kod"] for s in one[:4]]))
    bulten_secim = [s for s in analizler if s["kod"] in secim]
    TR.bulten_pdf(BASLIK[piyasa], satir, bulten_secim, os.path.join(hedef, "bulten.pdf"), endeks=endeks, ekler=ekler,
                  sym="₺" if piyasa in ("bist", "kripto_tl") else "$")
    pd.DataFrame(satir).to_csv(os.path.join(hedef, "ozet.csv"), index=False)
    gorsel = []
    by = {s["kod"]: s for s in analizler}
    if endeks: by[ref] = endeks
    tk = takip(piyasa)
    for k in list(dict.fromkeys(([ref] if endeks else []) + tk + secim))[:14]:
        s = by.get(k)
        if not s or not s["tf"].get("G"): continue
        a = s["tf"]["G"]; yol = os.path.join(hedef, "grafik", f"{_dosya(k)}.png")
        with open(yol, "wb") as f:
            f.write(TR.g_teknik(a, f"{k} · {s['ad']} · Günlük · {s['etiket']} (puan {s['puan']:.0f})", dpi=130).getvalue())
        gorsel.append({"kod": k, "ad": s["ad"], "etiket": s["etiket"], "puan": round(s["puan"], 1), "dosya": f"grafik/{_dosya(k)}.png",
                       "yorum": s["yorum"].replace("<b>", "").replace("</b>", "")})
    for k in tk:
        if k in by:
            try: TR.teknik_pdf(by[k], os.path.join(hedef, "rapor", f"{_dosya(k)}_Teknik.pdf"))
            except Exception as ex: print("rapor", k, ex, file=sys.stderr)
    meta = {"piyasa": piyasa, "baslik": BASLIK[piyasa], "uretim": dt.datetime.now(TSI).strftime("%d.%m.%Y %H:%M"),
            "kapanis": str(max((s["fiyat_zamani"] for s in analizler), default="")).split(" ")[0], "adet": len(analizler),
            "hata": len(hata), "grafikler": gorsel, "raporlar": [f"rapor/{_dosya(k)}_Teknik.pdf" for k in tk if k in by],
            "endeks": {"ad": endeks["ad"], "etiket": endeks["etiket"], "puan": round(endeks["puan"], 1),
                       "fiyat": (endeks["tf"].get("G") or {}).get("fiyat"), "degisim": (endeks["tf"].get("G") or {}).get("degisim"),
                       "para": endeks.get("para")} if endeks else None}
    json.dump(meta, open(os.path.join(hedef, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("Yazıldı:", hedef)
    return meta, satir


def _dosya(k):
    return k.replace("/", "-").replace("@", "_")


def _kripto_calistir(piyasa, kodlar, ref, klasor):
    """Kripto bültenleri: veriler doğrudan Binance / OKX'ten, yalnızca kapanmış günlük mumlarla."""
    from concurrent.futures import ThreadPoolExecutor
    T.KRIPTO_TAM_MUM = True
    analizler, hata = [], {}
    def is_(k):
        try: return T.analiz(k), None
        except Exception as ex: return None, str(ex)[:80]
    with ThreadPoolExecutor(max_workers=4) as ex:
        for k, (s, h) in zip(kodlar, ex.map(is_, kodlar)):
            if s: analizler.append(s)
            else: hata[k] = h
    print(f"Analiz: {len(analizler)} tamam, {len(hata)} hata")
    try: endeks = T.analiz(ref)
    except Exception: endeks = None
    return _yaz(piyasa, analizler, endeks, ref, klasor, hata)


# --------------------------------------------------------------------- Telegram
def telegram_gonder(piyasa, meta, satir, klasor="cikti", bot=None):
    """Kısa bülten özeti + bülten PDF'i; sessiz gönderilir, bir sonraki bülten gelince silinir (en fazla 30 saat)."""
    import tg
    bot = bot or tg.Bot(piyasa)
    df = pd.DataFrame(satir)
    import tg
    kod = lambda l: ", ".join(f"<b>{x}</b>" for x in l)
    satirlar = [f"📊 <b>{tg.buyuk(meta['baslik'].replace('Kapanış Teknik Bülteni – ', ''))} · KAPANIŞ BÜLTENİ</b>", tg.AYRAC,
                f"🗓 Kapanış: {meta['kapanis']} · {meta['adet']:,} varlık".replace(",", ".")]
    if meta.get("endeks"):
        e = meta["endeks"]; ik = "🟢" if e["puan"] >= 58 else "🔴" if e["puan"] <= 42 else "🟡"
        satirlar.append(f"{ik} {e['ad']}: <b>{e['etiket']}</b> ({e['puan']:.0f}/100)")
    if len(df):
        bl = [f"🏆 <b>En güçlü</b>\n" + ", ".join(f"<b>{r.Kod}</b> ({r['Teknik puan']:.0f})" for _, r in df.nlargest(6, "Teknik puan").iterrows())]
        dg = df["Değişim"].fillna(0) if "Değişim" in df else 0
        k = df[df["Kırılım"] & (dg >= 0)]
        if len(k): bl.append("🚀 <b>Yukarı kırılım</b>\n" + kod(k.nlargest(8, "Teknik puan")["Kod"]))
        k = df[df["Kırılım −"] & (dg <= 0)]
        if len(k): bl.append("⚠️ <b>Aşağı kırılım</b>\n" + kod(k.nsmallest(8, "Teknik puan")["Kod"]))
        if "Balina" in df:
            b = df["Balina"].fillna("").astype(str)
            k = df[b.str.contains("alımı|birikim|Alım emilimi")]
            if len(k): bl.append("🐋 <b>Balina alımı / birikim</b>\n" + kod(k.nlargest(8, "Teknik puan")["Kod"]))
            k = df[b.str.contains("satışı|dağıtım|Satış emilimi")]
            if len(k): bl.append("🐋 <b>Balina satışı / dağıtım</b>\n" + kod(k.nsmallest(8, "Teknik puan")["Kod"]))
        k = df[df["RSI"] < 30]
        if len(k): bl.append("🔻 <b>Aşırı satım (RSI &lt; 30)</b>\n" + kod(k.nsmallest(8, "RSI")["Kod"]))
        satirlar.append("<blockquote>" + "\n\n".join(bl) + "</blockquote>")
    satirlar.append("📎 Tam liste, grafikler ve raporlar ekteki PDF'te ve uygulamanın Teknik sekmesinde.")
    anahtar = f"bulten:{piyasa}"
    metin = "\n".join(satirlar)
    if piyasa == "abd": metin = metin.replace(".US</b>", "</b>")
    ad = {"bist": "BIST", "abd": "ABD", "kripto": "Kripto", "kripto_tl": "Kripto TL", "emtia": "Emtia"}.get(piyasa, piyasa)
    ids = []
    try:   # görsel kapanış kartı + kısa açıklama; kart çizilemezse metin
        import kart as KT
        yol = os.path.join(klasor, piyasa, "kapanis_karti.png"); os.makedirs(os.path.dirname(yol), exist_ok=True)
        KT.bulten_karti(meta, satir, yol, ad)
        alt = f"📊 <b>{tg.buyuk(ad)} · KAPANIŞ ÖZETİ</b> · {meta['kapanis']}\n{KT.piyasa_yorumu(pd.DataFrame(satir), meta)}"
        bot.sil_anahtar(anahtar)
        ids = bot.foto(yol, alt[:1000], anahtar, 30)
    except Exception as ex:
        print("Bülten kartı çizilemedi:", ex, file=sys.stderr)
    if not ids: ids = bot.mesaj(metin, anahtar, 30, yerine=True)
    try:
        yol = os.path.join(klasor, piyasa, "bulten.pdf")
        if ids and os.path.exists(yol):
            bot.belge(yol, f"{piyasa}_bulten_{meta['kapanis']}.pdf", f"{ad} kapanış bülteni (PDF)", anahtar, 30)
    except Exception as ex:
        print("Bülten PDF'i gönderilemedi:", ex, file=sys.stderr)
    return bot


if __name__ == "__main__":
    piyasa = (sys.argv[1] if len(sys.argv) > 1 else "bist").lower()
    zorla = "--zorla" in sys.argv
    s = calistir(piyasa, zorla=zorla)
    if s:
        b = telegram_gonder(piyasa, *s); b.kaydet()
