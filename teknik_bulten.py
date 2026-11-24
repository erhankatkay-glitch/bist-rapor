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
BASLIK = {"bist": "Kapanış Teknik Bülteni – BIST", "kripto": "Kapanış Teknik Bülteni – Kripto", "emtia": "Kapanış Teknik Bülteni – Emtia"}
REFERANS = {"bist": "XU100", "kripto": "BTC", "emtia": "ALTIN"}


def evren(piyasa):
    if piyasa == "kripto":
        return [k for k, v in V.VARLIKLAR.items() if v[2] == "kripto"]
    if piyasa == "emtia":
        return [k for k, v in V.VARLIKLAR.items() if v[2] == "emtia"]
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
    if piyasa == "bist": return [k for k in kod if k not in V.VARLIKLAR]
    tur = "kripto" if piyasa == "kripto" else "emtia"
    return [k for k in kod if k in V.VARLIKLAR and V.VARLIKLAR[k][2] == tur]


def calistir(piyasa, klasor="cikti", veri_fn=None, zorla=False):
    bugun = dt.datetime.now(TSI).date()
    kodlar = evren(piyasa); ref = REFERANS[piyasa]
    semboller = [T.yahoo_sembol(k)[0] for k in kodlar + [ref]] + (["TRY=X", "GC=F"] if piyasa == "emtia" else [])
    print(f"{piyasa}: {len(kodlar)} varlık, veri indiriliyor…")
    veri = veri_fn(semboller) if veri_fn else toplu_veri(semboller, "max" if piyasa == "kripto" else "10y")
    utc_bugun = dt.datetime.now(dt.timezone.utc).date()
    if piyasa == "kripto":   # 00:00 UTC'de kapanan mum tamamlandı; yeni açılan yarım mumu at
        veri = {k_: d[d.index.date < utc_bugun] for k_, d in veri.items()}
    fn = lambda y, *a: veri[y]
    # Tatil kontrolü: referansın son mumu beklenen kapanış gününe ait değilse bülten üretme
    try:
        son = veri[T.yahoo_sembol(ref)[0]].index[-1].date()
        beklenen = {"bist": bugun, "kripto": utc_bugun - dt.timedelta(days=1), "emtia": utc_bugun}[piyasa]
        if not zorla and son < beklenen:
            print(f"Son veri {son}, beklenen {beklenen}: piyasa kapalı/tatil ya da veri gecikmeli. Bülten atlandı.")
            return None
    except Exception as ex:
        print("Tarih kontrolü yapılamadı:", ex, file=sys.stderr)
    analizler, satir, hata = [], [], {}
    for k in kodlar:
        try:
            s = T.analiz(k, fiyat_fn=fn); analizler.append(s); satir.append(T.ozet_satir(s))
        except Exception as ex:
            hata[k] = str(ex)[:80]
    try:
        endeks = T.analiz(ref, fiyat_fn=fn)
        if ref == "XU100": endeks["ad"] = "BIST 100"
    except Exception as ex:
        endeks = None; print("Referans analizi yapılamadı:", ex, file=sys.stderr)
    print(f"Analiz: {len(analizler)} tamam, {len(hata)} hata")
    hedef = os.path.join(klasor, piyasa)
    shutil.rmtree(hedef, ignore_errors=True); os.makedirs(os.path.join(hedef, "grafik"), exist_ok=True); os.makedirs(os.path.join(hedef, "rapor"), exist_ok=True)
    one = sorted(analizler, key=lambda s: -(s["puan"] or 0))
    kirilim = [s for s in one if T.ozet_satir(s)["Kırılım"]]
    secim = list(dict.fromkeys([s["kod"] for s in kirilim[:4]] + [s["kod"] for s in one[:4]]))
    bulten_secim = [s for s in analizler if s["kod"] in secim]
    TR.bulten_pdf(BASLIK[piyasa], satir, bulten_secim, os.path.join(hedef, "bulten.pdf"), endeks=endeks)
    pd.DataFrame(satir).to_csv(os.path.join(hedef, "ozet.csv"), index=False)
    gorsel = []
    by = {s["kod"]: s for s in analizler}
    if endeks: by[ref] = endeks
    tk = takip(piyasa)
    for k in list(dict.fromkeys(([ref] if endeks else []) + tk + secim))[:14]:
        s = by.get(k)
        if not s or not s["tf"].get("G"): continue
        a = s["tf"]["G"]; yol = os.path.join(hedef, "grafik", f"{k}.png")
        with open(yol, "wb") as f:
            f.write(TR.g_teknik(a, f"{k} · {s['ad']} · Günlük · {s['etiket']} (puan {s['puan']:.0f})", dpi=130).getvalue())
        gorsel.append({"kod": k, "ad": s["ad"], "etiket": s["etiket"], "puan": round(s["puan"], 1), "dosya": f"grafik/{k}.png",
                       "yorum": s["yorum"].replace("<b>", "").replace("</b>", "")})
    for k in tk:
        if k in by:
            try: TR.teknik_pdf(by[k], os.path.join(hedef, "rapor", f"{k}_Teknik.pdf"))
            except Exception as ex: print("rapor", k, ex, file=sys.stderr)
    meta = {"piyasa": piyasa, "baslik": BASLIK[piyasa], "uretim": dt.datetime.now(TSI).strftime("%d.%m.%Y %H:%M"),
            "kapanis": str(max((s["fiyat_zamani"] for s in analizler), default="")).split(" ")[0], "adet": len(analizler),
            "hata": len(hata), "grafikler": gorsel, "raporlar": [f"rapor/{k}_Teknik.pdf" for k in tk if k in by],
            "endeks": {"ad": endeks["ad"], "etiket": endeks["etiket"], "puan": round(endeks["puan"], 1)} if endeks else None}
    json.dump(meta, open(os.path.join(hedef, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("Yazıldı:", hedef)
    return meta, satir


# --------------------------------------------------------------------- Telegram
def telegram_gonder(piyasa, meta, satir, klasor="cikti"):
    tok, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        print("Telegram ayarlı değil; gönderim atlandı."); return
    import requests
    api = f"https://api.telegram.org/bot{tok}"
    df = pd.DataFrame(satir)
    satirlar = [f"📊 {meta['baslik']}", f"Kapanış: {meta['kapanis']} · {meta['adet']} varlık"]
    if meta.get("endeks"): satirlar.append(f"{meta['endeks']['ad']}: {meta['endeks']['etiket']} ({meta['endeks']['puan']:.0f}/100)")
    if len(df):
        satirlar.append("\n🟢 En güçlü: " + ", ".join(f"{r.Kod} ({r['Teknik puan']:.0f})" for _, r in df.nlargest(6, "Teknik puan").iterrows()))
        k = df[df["Kırılım"]]
        if len(k): satirlar.append("🚀 Yukarı kırılım: " + ", ".join(k.nlargest(8, "Teknik puan")["Kod"]))
        k = df[df["Kırılım −"]]
        if len(k): satirlar.append("⚠️ Aşağı kırılım: " + ", ".join(k.nsmallest(8, "Teknik puan")["Kod"]))
        k = df[df["RSI"] < 30]
        if len(k): satirlar.append("🔻 Aşırı satım: " + ", ".join(k.nsmallest(8, "RSI")["Kod"]))
    satirlar.append("\nModel çıktısıdır, yatırım tavsiyesi değildir.")
    try:
        requests.post(f"{api}/sendMessage", data={"chat_id": chat, "text": "\n".join(satirlar)}, timeout=30)
        hedef = os.path.join(klasor, piyasa)
        with open(os.path.join(hedef, "bulten.pdf"), "rb") as f:
            requests.post(f"{api}/sendDocument", data={"chat_id": chat, "caption": meta["baslik"]},
                          files={"document": (f"{piyasa}_bulten_{meta['kapanis']}.pdf", f)}, timeout=120)
        g = meta["grafikler"][:10]
        if g:
            files, medya = {}, []
            for i, x in enumerate(g):
                files[f"f{i}"] = open(os.path.join(hedef, x["dosya"]), "rb")
                medya.append({"type": "photo", "media": f"attach://f{i}", "caption": f"{x['kod']} · {x['etiket']} ({x['puan']:.0f})"})
            requests.post(f"{api}/sendMediaGroup", data={"chat_id": chat, "media": json.dumps(medya, ensure_ascii=False)}, files=files, timeout=180)
            for f in files.values(): f.close()
        for r_ in meta.get("raporlar", [])[:6]:
            with open(os.path.join(hedef, r_), "rb") as f:
                requests.post(f"{api}/sendDocument", data={"chat_id": chat}, files={"document": (os.path.basename(r_), f)}, timeout=120)
        print("Telegram'a gönderildi.")
    except Exception as ex:
        print("Telegram gönderimi başarısız:", ex, file=sys.stderr)


if __name__ == "__main__":
    piyasa = (sys.argv[1] if len(sys.argv) > 1 else "bist").lower()
    zorla = "--zorla" in sys.argv
    s = calistir(piyasa, zorla=zorla)
    if s:
        telegram_gonder(piyasa, *s)
