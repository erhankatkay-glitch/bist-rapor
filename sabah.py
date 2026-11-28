# -*- coding: utf-8 -*-
"""Sabah özeti: her sabah (09:00 TSİ) tek kartlık "bugün neyi izlemeli" özeti + kısa sesli anlatım.
İçerik: gece piyasalar (ABD kapanışı, kripto, altın, petrol, kur, VIX), günün ekonomik takvimi, açık kurulumlar ve
hedef/stopa yakın olanlar, son kapanışların en güçlü fırsatları, son 12 saatin önemli haberleri, portföy.
Ardından ayrı bir "Temel özet" kartı (temel_bildirim.py): BIST'te değerinin en altındaki 5 hisse, yeni halka arzlar, kripto ve emtia.
Çıktı: cikti/sabah/{kart.png, ozet.mp3, ozet.json}; Telegram'a kart (+ ses) gönderilir, 20 saat sonra silinir."""
import os, sys, json, textwrap, datetime as dt
import numpy as np
import pandas as pd

import tg

KLON, CIKTI = tg.KLON, tg.CIKTI
TSI = dt.timezone(dt.timedelta(hours=3))
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def oku(yol, v=None):
    try: return json.load(open(os.path.join(KLON, yol), encoding="utf-8"))
    except Exception: return v


def piyasalar():
    import bist_makro as mk
    return mk.piyasa_paneli()


def acik_kurulumlar():
    out = []
    for p in ("bist", "abd", "kripto", "emtia"):
        for k in oku(f"firsat/{p}/acik.json", []) or []:
            if p == "kripto":
                try:
                    import bist_kripto as BK
                    if BK.hisse_tokeni_mu(k["kod"]): continue
                except Exception:
                    pass
            c = k.get("son_fiyat") or k["giris"]; yon = k["yon"]
            hed = k["hedef"][min(k["asama"], 2)]
            yak_h = (hed - c) / c * yon; yak_s = (c - k["stop"]) / c * yon
            out.append({**k, "pz": p, "yak_h": yak_h, "yak_s": yak_s, "ger": (c - k["giris"]) / k["giris"] * yon})
    return out


def en_iyi_firsatlar(n=3):
    """Öne çıkan fırsatlar: önce Borsa İstanbul ve kripto (her birinin en iyisi), kalan yer emtia ile dolar.
    ABD hisseleri sabah özetinde gösterilmez (kendi bildirimlerinde zaten var)."""
    havuz = {}
    for p in ("bist", "kripto", "emtia"):
        son = oku(f"firsat/{p}/son.json", {}) or {}
        for tf, x in son.items():
            try:
                if dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(x["zaman"]) > dt.timedelta(hours=30 if p == "kripto" else 80): continue   # hafta sonu: cuma kapanışı
            except Exception:
                continue
            for f in x.get("firsatlar", []):
                if p == "kripto":
                    try:
                        import bist_kripto as BK
                        if BK.hisse_tokeni_mu(f["kod"]): continue   # tokenize hisse/ETF, gerçek kripto değil
                    except Exception:
                        pass
                k = (p, f["kod"])
                if k not in havuz or f["puan"] > havuz[k]["puan"]: havuz[k] = {**f, "pz": p}
    sirali = {p: sorted([f for (q, _), f in havuz.items() if q == p], key=lambda f: -f["puan"]) for p in ("bist", "kripto", "emtia")}
    out = [sirali[p].pop(0) for p in ("bist", "kripto") if sirali[p]]   # her birinin en iyisi garanti
    out += sorted(sirali["bist"] + sirali["kripto"] + sirali["emtia"], key=lambda f: -f["puan"])[:max(0, n - len(out))]
    return out[:n]


def haberler(n=3):
    son = oku("haber/son.json", []) or []
    t = dt.datetime.now(dt.timezone.utc)
    return [a for a in son if t - dt.datetime.fromisoformat(a["zaman"]) < dt.timedelta(hours=14)][:n]


def takvim_bugun():
    tk = oku("haber/takvim.json", {}) or {}
    bugun = dt.datetime.now(TSI).date()
    return [e for e in tk.get("liste", []) if dt.datetime.fromisoformat(e["zaman"]).date() == bugun]


def _y(x):
    s = f"{x * 100:+.1f}".replace(".", ",")
    return ("+%" + s[1:]) if s[0] == "+" else ("−%" + s[1:])


def izlenecekler(PV, tk, acik, firs, hab):
    """Bilmeyenin de anlayacağı 3–4 maddelik 'bugün neyi izlemeli' listesi."""
    m = []
    sp, vx = PV.get("S&P 500"), PV.get("VIX")
    if sp:
        d = sp["d1G"]
        m.append(f"ABD borsaları dün {'yükselişle' if d > 0.003 else 'düşüşle' if d < -0.003 else 'yatay'} kapandı (S&P 500 {_y(d)})"
                 + (f"; korku endeksi VIX {vx['deger']:.0f} ile {'yüksek, temkin gerekli' if vx['deger'] > 25 else 'sakin'}." if vx else "."))
    try:
        import yabanci_akis as YA
        c_ = YA.cumle(YA.ozet(YA.arsiv_oku(KLON)))
        if c_: m.append(c_)
    except Exception:
        pass
    try:
        import makro_tr as MT
        yol_ = os.path.join(CIKTI, "makro", "tr_makro.json")
        mm = json.load(open(yol_, encoding="utf-8")) if os.path.exists(yol_) else MT.oku()
        oz = MT.ozet_satiri(mm)
        if oz: m.append(f"Türkiye: {oz}" + (" (son kayıtlı değer)" if (mm.get("tufe") or {}).get("bayat") else "") + ".")
    except Exception:
        pass
    try:   # Aşama 13: BTC opsiyon piyasası (kripto iş akışı 4 saatte bir üretir)
        op = (oku("opsiyon/ozet.json") or {}).get("paralar", {}).get("BTC")
        if op and op.get("dvol"):
            v = (op.get("buyuk_vadeler") or [None])[0]
            m.append(f"BTC opsiyon: DVOL {op['dvol']['deger']:.0f} (1 yıllık sıra {op['dvol']['yuzdelik'] * 100:.0f}/100)"
                     + (f", {v['vade_ad']} vadesinde max pain {v['max_pain']:,.0f} $".replace(",", ".") if v and v.get("max_pain") else "")
                     + (f", beklenen hareket ±%{v['beklenen_hareket'] * 100:.1f}".replace(".", ",") if v and v.get("beklenen_hareket") else "") + ".")
    except Exception:
        pass
    try:   # Aşama 12: gece Asya seansı ve ABD getiri eğrisi
        yd = os.path.join(CIKTI, "dunya", "ozet.json")
        do = json.load(open(yd, encoding="utf-8")) if os.path.exists(yd) else oku("dunya/ozet.json")
        asya = [x for x in (do or {}).get("borsalar", []) if x["ad"] in ("Nikkei 225", "Hang Seng", "Şanghay") and x.get("d1") is not None]
        if asya:
            m.append("Asya bu sabah: " + ", ".join(f"{x['ad']} {_y(x['d1'])}" for x in asya) + ".")
        e = (do or {}).get("egri") or {}
        f_ = e.get("f10_2") if e.get("f10_2") is not None else e.get("f10_3a")
        if f_ is not None and f_ < 0: m.append(f"ABD getiri eğrisi ters ({f_:+.2f} puan)".replace(".", ",") + "; resesyon riski fiyatlanıyor olabilir.")
    except Exception:
        pass
    try:   # Aşama 11: korelasyon kırılması (alışılmış piyasalar arası ilişki bozulduysa)
        yk = os.path.join(CIKTI, "korelasyon", "ozet.json")
        ko = json.load(open(yk, encoding="utf-8")) if os.path.exists(yk) else oku("korelasyon/ozet.json")
        kc = [c for c in (ko or {}).get("ciftler", []) if c.get("kirilma")]
        if kc:
            c = kc[0]
            m.append(f"{c['a']} ile {c['b']} arasındaki alışılmış ilişki bozuldu (20 günlük korelasyon {c['c20']:+.2f}, 1 yıllık "
                     f"{c['c250']:+.2f})".replace(".", ",") + "; çeşitlendirme varsayımlarını gözden geçirin.")
    except Exception:
        pass
    try:   # Aşama 10c: piyasa rejimi (kapanışta hesaplanır)
        rj = [r for r in (oku("rejim/bist.json"), oku("rejim/abd.json")) if r]
        if rj: m.append("Piyasa rejimi: " + "; ".join(f"{r['endeks']} {r['durum_ad'].lower()}, önerilen hisse oranı %{r['maruziyet']}"
                                                       + (" (tepe uyarısı)" if r.get("tepe_uyarisi") else "") for r in rj) + ".")
    except Exception:
        pass
    if tk:
        e = tk[0]; t = dt.datetime.fromisoformat(e["zaman"])
        import ses as SES; ek = "'" + SES.ek_de(SES._saat_metni(t))[-2:]
        m.append(f"Saat {t:%H:%M}{ek} {e['baslik']} verisi açıklanacak; altın, Bitcoin ve borsalarda oynaklık artabilir."
                 if len(tk) == 1 else f"Bugün {len(tk)} önemli veri var; ilki {t:%H:%M}{ek} ({e['baslik']}). Açıklama saatlerinde sert hareket olabilir.")
    yakin = sorted([k for k in acik if k["yak_h"] < 0.02], key=lambda k: k["yak_h"])
    risk = sorted([k for k in acik if k["yak_s"] < 0.02], key=lambda k: k["yak_s"])
    if yakin: m.append(f"{_kod(yakin[0]['kod'])} açık kurulumu hedefe çok yakın; kâr alma seviyesini takip edin.")
    if risk: m.append(f"{_kod(risk[0]['kod'])} açık kurulumu stop seviyesine yakın; zarar kesme planını gözden geçirin.")
    if firs: m.append(f"Son kapanışların en güçlü fırsatı: {_kod(firs[0]['kod'])} ({'AL' if firs[0]['yon'] == 1 else 'SAT'}, puan {firs[0]['puan']:.0f}).")
    if hab:
        import haber as H; a = hab[0]; m.append(f"Öne çıkan haber: {a['tur']} ({H.etki_ad(a)}).")
    return m[:8]


def _kod(k):
    k = str(k)
    return k[:-3] if k.endswith(".US") else k.replace("/USDT", "").replace("@OKX", "")


# ---------------------------------------------------------------- kart
def _veri_ad(e):
    """Takvim verisinin Türkçe adı (uygulamadaki gibi)."""
    try:
        import ses as SES
        return SES.veri_adi(e["baslik"], e.get("ulke"))
    except Exception:
        return f"{e.get('ulke', '')} · {e['baslik']}"


def kart(PV, tk, acik, firs, hab, madde, dosya):
    import kart as K
    from matplotlib.patches import Rectangle
    import matplotlib.pyplot as plt
    C = K.C; W, H = 1080, 1620
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100); fig.patch.set_facecolor(C["bg"])
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    t = dt.datetime.now(TSI)
    K.ust_bant(ax, H, "SABAH ÖZETİ")
    K._t(ax, 48, H - 160, f"{t.day} {AYLAR[t.month - 1]} {GUNLER[t.weekday()]}", 44, weight="bold")
    K._t(ax, 48, H - 200, "Bugün neyi izlemeli?", 20, C["soluk"])
    # piyasa ızgarası
    sira = ["BIST 100", "S&P 500", "Nasdaq", "USD/TRY", "Gram altın", "Ons altın", "Brent petrol", "Bitcoin", "VIX"]
    goster = [x for x in sira if x in PV][:9]
    bw, bh = (W - 80 - 2 * 14) / 3, 112
    for i, ad in enumerate(goster):
        v = PV[ad]; x = 40 + (i % 3) * (bw + 14); y = H - 340 - (i // 3) * (bh + 14)
        K._kutu(ax, x, y, bw, bh, C["panel"])
        d = v.get("d1G") or 0; renk = C["yesil"] if d > 0 else C["kirmizi"] if d < 0 else C["soluk"]
        K.logo_ciz(ax, ad if ad not in ("USD/TRY", "Bitcoin") else {"Bitcoin": "BTC/USDT"}.get(ad, ad), x + bw - 44, y + bh - 44, 28,
                   "kripto" if ad == "Bitcoin" else None)
        K._t(ax, x + 18, y + 80, ad.upper(), 13, C["soluk"], "semibold")
        K._t(ax, x + 18, y + 40, K._fy(v["deger"]) if v["deger"] < 1e5 else f"{v['deger']:,.0f}".replace(",", "."), 26, weight="bold")
        K._t(ax, x + 18, y + 14, _y(d), 16, renk, "semibold")
        s = v["seri"].dropna().iloc[-30:]
        if len(s) > 2:
            xs = np.linspace(x + bw * 0.55, x + bw - 16, len(s)); lo, hi = s.min(), s.max(); hi = hi if hi > lo else lo + 1
            ys = y + 22 + (s.values - lo) / (hi - lo) * 50
            ax.plot(xs, ys, color=renk, lw=1.8)
    y = H - 340 - 2 * (bh + 14) - 40
    # bugün neyi izlemeli
    satirlar = [textwrap.wrap(mm, 78)[:2] for mm in madde]
    kh = max(260, 58 + sum(len(x) * 27 + 4 for x in satirlar) + 14)
    K._kutu(ax, 40, y + 10 - kh, W - 80, kh, C["panel2"], kenar=C["altin"])
    K._t(ax, 68, y - 22, "BUGÜN NEYİ İZLEMELİ", 14, C["altin"], "semibold")
    yy = y - 58
    for sl in satirlar:
        for j, sat in enumerate(sl):
            K._t(ax, 68 if j == 0 else 92, yy, ("•  " if j == 0 else "") + sat, 17, C["yazi"]); yy -= 27
        yy -= 4
    y = y - kh - 30
    # takvim
    K.bolum_baslik(ax, 48, y, "Bugünün verileri (TSİ)", boy=15); y -= 38
    if tk:
        for e in tk[:4]:
            t_ = dt.datetime.fromisoformat(e["zaman"])
            K._t(ax, 48, y, f"{t_:%H:%M}", 18, C["yazi"], "bold"); K._t(ax, 130, y, textwrap.shorten(_veri_ad(e), 54, placeholder="…"), 17, C["yazi"])
            if e.get("beklenti"): K._t(ax, W - 48, y, f"beklenti {e['beklenti']}", 15, C["soluk"], ha="right")
            y -= 32
    else:
        K._t(ax, 48, y, "Bugün yüksek etkili veri yok.", 17, C["soluk"]); y -= 32
    y -= 18
    # fırsatlar ve açık kurulumlar
    K.bolum_baslik(ax, 48, y, "Öne çıkan fırsatlar", x2=540, boy=15); K.bolum_baslik(ax, 580, y, "Açık kurulumlar", x2=W - 40, boy=15); y -= 40
    y0 = y
    for f in firs[:3]:
        renk = C["yesil"] if f["yon"] == 1 else C["kirmizi"]
        kx = 82 if K.logo_ciz(ax, f["kod"], 48, y - 6, 26, f.get("pz")) else 48
        K._t(ax, kx, y, _kod(f["kod"]), 20, weight="bold"); K._t(ax, 210, y, f"{'AL' if f['yon'] == 1 else 'SAT'} · {f['puan']:.0f}", 17, renk, "semibold")
        K._t(ax, 340, y, {"bist": "BIST", "kripto": "Kripto", "emtia": "Emtia", "abd": "ABD"}.get(f.get("pz"), "") + " · " +
             {"4S": "4 saatlik", "G": "günlük", "H": "haftalık", "A": "aylık"}.get(f["tf"], ""), 15, C["soluk"]); y -= 36
    if not firs: K._t(ax, 48, y, "Son kapanışlarda eşiği geçen fırsat yok.", 16, C["soluk"])
    y = y0
    acik_s = sorted(acik, key=lambda k: min(k["yak_h"], k["yak_s"]))[:3]
    for k in acik_s:
        renk = C["yesil"] if k["ger"] >= 0 else C["kirmizi"]
        kx = 614 if K.logo_ciz(ax, k["kod"], 580, y - 6, 26, k.get("pz")) else 580
        K._t(ax, kx, y, _kod(k["kod"]), 20, weight="bold"); K._t(ax, W - 48, y, _y(k["ger"]), 17, renk, "semibold", ha="right"); y -= 36
    if not acik: K._t(ax, 580, y, "Açık kurulum yok.", 16, C["soluk"])
    y = min(y, y0 - 36 * 3) - 20
    # haberler
    if hab and y > 120:
        K.bolum_baslik(ax, 48, y, "Son haberler", boy=15); y -= 36
        for a in hab[:3]:
            if y < 70: break
            renk = C["yesil"] if a["yon"] > 0 else C["kirmizi"]
            from matplotlib.patches import Circle
            ax.add_patch(Circle((58, y + 7), 7, color=renk))
            K._t(ax, 76, y, textwrap.shorten(a["baslik"], 70, placeholder="…"), 16, C["yazi"]); y -= 32
    K.alt_bant(ax, 14)
    fig.savefig(dosya, dpi=100, facecolor=C["bg"]); plt.close(fig)
    try:   # içerik bittiği yerin altındaki boşluğu kırp (alt bilgi korunur)
        from PIL import Image
        im = Image.open(dosya); bos_ust, bos_alt = int(H - max(y, 60) + 20), H - 50
        if bos_alt - bos_ust > 80:
            ust_, alt_ = im.crop((0, 0, W, bos_ust)), im.crop((0, bos_alt, W, H))
            yeni = Image.new(im.mode, (W, ust_.height + alt_.height)); yeni.paste(ust_, (0, 0)); yeni.paste(alt_, (0, ust_.height)); yeni.save(dosya)
    except Exception:
        pass
    return dosya


def ses_parcalari(PV, tk, acik, firs, hab):
    import ses as SES
    t = dt.datetime.now(TSI)
    yab = None
    try:
        import yabanci_akis as YA
        yab = YA.ozet(YA.arsiv_oku(KLON))
    except Exception:
        pass
    return SES.senaryo(PV, tk, acik, firs, hab, yab, f"{t.day} {AYLAR[t.month - 1]} {GUNLER[t.weekday()]}")


def calistir():
    os.makedirs(os.path.join(CIKTI, "sabah"), exist_ok=True)
    PV = piyasalar(); tk = takvim_bugun(); acik = acik_kurulumlar(); firs = en_iyi_firsatlar(); hab = haberler()
    madde = izlenecekler(PV, tk, acik, firs, hab)
    yol = kart(PV, tk, acik, firs, hab, madde, os.path.join(CIKTI, "sabah", "kart.png"))
    ses = None
    try:
        import ses as SES
        ses = os.path.join(CIKTI, "sabah", "ozet.mp3")
        parca = ses_parcalari(PV, tk, acik, firs, hab)
        open(os.path.join(CIKTI, "sabah", "ozet_metin.txt"), "w", encoding="utf-8").write("\n".join(f"{k}: {m}" for k, m in parca))
        print("ses motoru:", SES.seslendir(parca, ses))
    except Exception as ex:
        print("Sesli özet üretilemedi:", ex, file=sys.stderr); ses = None
    json.dump({"zaman": dt.datetime.now(TSI).isoformat(), "madde": madde}, open(os.path.join(CIKTI, "sabah", "ozet.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    b = tg.Bot("sabah")
    t = dt.datetime.now(TSI)
    alt = f"☀️ <b>Sabah özeti</b> · {t:%d.%m.%Y} · sesli özet aşağıda"
    b.sil_anahtar("sabah")
    if b.foto(yol, alt, "sabah", 20) and ses:
        try:
            with open(ses, "rb") as f:
                j = b._api("sendAudio", {"chat_id": b.chat, "title": f"Sabah özeti {t:%d.%m}", "performer": "KATKAY Yatırım",
                                         "disable_notification": True}, files={"audio": ("sabah_ozeti.mp3", f)}, timeout=120)
            if j.get("ok"): b._kaydet([j["result"]["message_id"]], "sabah", 20, None)
        except Exception as ex:
            print("Ses gönderilemedi:", ex, file=sys.stderr)
    try:   # sabah temel özeti kartı (BIST değer, halka arzlar, kripto, emtia)
        import temel_bildirim as TBL
        TBL.gonder(b)
    except Exception as ex:
        print("Temel özet gönderilemedi:", ex, file=sys.stderr)
    b.kaydet()
    print("Sabah özeti hazır:", madde)


def tg_kac(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


if __name__ == "__main__":
    calistir()
