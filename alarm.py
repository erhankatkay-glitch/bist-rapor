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
        print("Anlaşılamayan kural:", satir, file=sys.stderr)
    return K


def _ad(kod):
    import bist_teknik as T
    return f"{kod} ({T.KURESEL[kod][1]})" if kod in T.KURESEL else {"XU100": "BIST 100", "XU030": "BIST 30", "XBANK": "BIST Banka"}.get(kod, kod)


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
    y, _ = T.yahoo_sembol(kod)
    g = yf.Ticker(y).history(period="5d", interval="15m")
    d = yf.Ticker(y).history(period="5d")
    if g is None or g.empty: raise ValueError(f"{kod} fiyatı alınamadı")
    son = float(g["Close"].iloc[-1]); onceki = float(d["Close"].iloc[-2]) if len(d) > 1 else son
    return son, son / onceki - 1


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
            for yol in ("takip_listesi.txt", "teknik_takip.txt"):
                if os.path.exists(yol):
                    for s in open(yol, encoding="utf-8"):
                        s = s.split("#")[0].strip().upper()
                        if s:
                            import bist_varlik as V
                            hedefler.append({"tip": "formasyon", "kod": s, "metin": f"{s} FORMASYON (otomatik)"})
                            if not _kripto(s) and s not in V.VARLIKLAR: hedefler.append({"tip": "kap", "kod": s, "metin": f"{s} KAP (otomatik)"})
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
                        bildir.append(f"🔔 {k['kod']} fiyatı {_s(k['deger'])} seviyesinin {'üzerine çıktı' if k['op'] == '>' else 'altına indi'}: {_s(p)}")
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
                    bildir.append(f"📈 {k['kod']} {'RSI' if k['tip'] == 'rsi' else 'teknik puan'} {x:.0f} ({k['op']} {k['deger']:g})")
                yeni[anahtar] = bool(kosul)
            elif k["tip"] == "formasyon":
                s = teknik(k["kod"]); g = s["tf"]["G"]
                for ad, yon, ac, guc in g["sinyal"]:
                    if not any(w in ad for w in ("TEYİT", "KIRILIM", "BOS", "CHoCH", "Altın kesişim", "Ölüm kesişimi")): continue
                    a2 = f"{k['kod']}|{ad}|{g['tarih']:%Y-%m-%d}"
                    if not durum.get(a2):
                        bildir.append(f"{'🟢' if yon > 0 else '🔴'} {k['kod']}: {ad.split(': ', 1)[-1]} (günlük, {g['tarih']:%d.%m})")
                        yeni[a2] = True
            elif k["tip"] == "kap":
                import bist_borsa as BB, bist_veri as bv, bist_varlik as V
                if _kripto(k["kod"]) or k["kod"] in V.VARLIKLAR: continue
                for x in BB.kap_haberleri(k["kod"], bv.sirket_adi(k["kod"]), gun=3, adet=6):
                    a2 = f"{k['kod']}|KAP|{x['baslik'][:80]}"
                    konu_gun = f"{k['kod']}|KAPKONU|{x['konu']}|{bugun}"   # aynı konuda günde tek bildirim
                    if not durum.get(a2) and not durum.get(konu_gun) and not yeni.get(konu_gun):
                        yeni[konu_gun] = True
                        bildir.append(f"📰 {k['kod']} · {x['konu']}: {x['baslik'][:140]}")
                        yeni[a2] = True
        except Exception as ex:
            print(f"{anahtar}: {ex}", file=sys.stderr)
    bildir = list(dict.fromkeys(bildir))
    # eski günlük anahtarları temizle
    sinir = (dt.datetime.now(TSI) - dt.timedelta(days=30)).strftime("%Y-%m-%d")
    yeni = {k: v for k, v in yeni.items() if not re.search(r"\d{4}-\d{2}-\d{2}", k) or max(re.findall(r"\d{4}-\d{2}-\d{2}", k)) >= sinir}
    return bildir, yeni


def gonder(mesajlar):
    """Alarmlar sessiz gönderilir ve 12 saat sonra otomatik silinir."""
    if not mesajlar: return False
    import tg
    b = tg.Bot("alarm")
    if not b.aktif: return False
    z = dt.datetime.now(TSI).strftime("%Y%m%d%H%M")
    for i in range(0, len(mesajlar), 20):
        b.mesaj("🔔 <b>Alarm</b>\n" + "\n".join(tg_kac(m) for m in mesajlar[i:i + 20]) + "\n\n<i>Model çıktısıdır, yatırım tavsiyesi değildir.</i>",
                f"alarm:{z}:{i}", 12, yerine=False)
    b.kaydet()
    return True


def tg_kac(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
    json.dump(son[:100], open(SON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"kontrol": zaman, "kural": len(K)}, open(os.path.join("alarm_cikti", "son_kontrol.json"), "w"), ensure_ascii=False)
    print(f"{len(K)} kural, {len(bildir)} yeni alarm. Telegram: {'gönderildi' if gonder(bildir) else 'ayarlı değil / gönderilecek alarm yok'}")
    for m in bildir: print(" ", m)


if __name__ == "__main__":
    main()
