# -*- coding: utf-8 -*-
"""Sabah özeti: her sabah (09:00 TSİ) tek kartlık "bugün neyi izlemeli" özeti + kısa sesli anlatım.
İçerik: gece piyasalar (ABD kapanışı, kripto, altın, petrol, kur, VIX), günün ekonomik takvimi, açık kurulumlar ve
hedef/stopa yakın olanlar, son kapanışların en güçlü fırsatları, son 12 saatin önemli haberleri, portföy.
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
            c = k.get("son_fiyat") or k["giris"]; yon = k["yon"]
            hed = k["hedef"][min(k["asama"], 2)]
            yak_h = (hed - c) / c * yon; yak_s = (c - k["stop"]) / c * yon
            out.append({**k, "yak_h": yak_h, "yak_s": yak_s, "ger": (c - k["giris"]) / k["giris"] * yon})
    return out


def en_iyi_firsatlar(n=3):
    out = []
    for p in ("bist", "abd", "kripto", "emtia"):
        son = oku(f"firsat/{p}/son.json", {}) or {}
        for tf, x in son.items():
            try:
                if dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(x["zaman"]) > dt.timedelta(hours=30): continue
            except Exception:
                continue
            for f in x.get("firsatlar", []): out.append({**f, "pz": p})
    return sorted(out, key=lambda f: -f["puan"])[:n]


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
    if tk:
        e = tk[0]; t = dt.datetime.fromisoformat(e["zaman"])
        m.append(f"Saat {t:%H:%M}'de {e['baslik']} verisi açıklanacak; altın, Bitcoin ve borsalarda oynaklık artabilir."
                 if len(tk) == 1 else f"Bugün {len(tk)} önemli veri var; ilki {t:%H:%M}'de ({e['baslik']}). Açıklama saatlerinde sert hareket olabilir.")
    yakin = sorted([k for k in acik if k["yak_h"] < 0.02], key=lambda k: k["yak_h"])
    risk = sorted([k for k in acik if k["yak_s"] < 0.02], key=lambda k: k["yak_s"])
    if yakin: m.append(f"{_kod(yakin[0]['kod'])} açık kurulumu hedefe çok yakın; kâr alma seviyesini takip edin.")
    if risk: m.append(f"{_kod(risk[0]['kod'])} açık kurulumu stop seviyesine yakın; zarar kesme planını gözden geçirin.")
    if firs: m.append(f"Son kapanışların en güçlü fırsatı: {_kod(firs[0]['kod'])} ({'AL' if firs[0]['yon'] == 1 else 'SAT'}, puan {firs[0]['puan']:.0f}).")
    if hab:
        import haber as H; a = hab[0]; m.append(f"Öne çıkan haber: {a['tur']} ({H.etki_ad(a)}).")
    return m[:5]


def _kod(k):
    k = str(k)
    return k[:-3] if k.endswith(".US") else k.replace("/USDT", "").replace("@OKX", "")


# ---------------------------------------------------------------- kart
def kart(PV, tk, acik, firs, hab, madde, dosya):
    import kart as K
    from matplotlib.patches import Rectangle
    import matplotlib.pyplot as plt
    C = K.C; W, H = 1080, 1620
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100); fig.patch.set_facecolor(C["bg"])
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    t = dt.datetime.now(TSI)
    ax.add_patch(Rectangle((0, H - 8), W, 8, color=C["altin"]))
    K._t(ax, K._marka(ax, H), H - 58, "SABAH ÖZETİ", 15, C["altin"], "semibold")
    K._t(ax, 48, H - 140, f"{t.day} {AYLAR[t.month - 1]} {GUNLER[t.weekday()]}", 44, weight="bold")
    K._t(ax, 48, H - 182, "Bugün neyi izlemeli?", 20, C["soluk"])
    # piyasa ızgarası
    sira = ["BIST 100", "S&P 500", "Nasdaq", "USD/TRY", "Gram altın", "Ons altın", "Brent petrol", "Bitcoin", "VIX"]
    goster = [x for x in sira if x in PV][:9]
    bw, bh = (W - 80 - 2 * 14) / 3, 112
    for i, ad in enumerate(goster):
        v = PV[ad]; x = 40 + (i % 3) * (bw + 14); y = H - 340 - (i // 3) * (bh + 14)
        K._kutu(ax, x, y, bw, bh, C["panel"])
        d = v.get("d1G") or 0; renk = C["yesil"] if d > 0 else C["kirmizi"] if d < 0 else C["soluk"]
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
    K._kutu(ax, 40, y - 250, W - 80, 260, C["panel2"], kenar=C["altin"])
    K._t(ax, 68, y - 22, "BUGÜN NEYİ İZLEMELİ", 14, C["altin"], "semibold")
    yy = y - 58
    for mm in madde:
        for j, sat in enumerate(textwrap.wrap(mm, 78)[:2]):
            K._t(ax, 68 if j == 0 else 92, yy, ("•  " if j == 0 else "") + sat, 17, C["yazi"]); yy -= 27
        yy -= 4
    y = y - 290
    # takvim
    K._t(ax, 48, y, "BUGÜNÜN VERİLERİ (TSİ)", 14, C["altin"], "semibold"); y -= 38
    if tk:
        for e in tk[:4]:
            t_ = dt.datetime.fromisoformat(e["zaman"])
            K._t(ax, 48, y, f"{t_:%H:%M}", 18, C["yazi"], "bold"); K._t(ax, 130, y, textwrap.shorten(f"{e['ulke']} · {e['baslik']}", 50, placeholder="…"), 17, C["yazi"])
            if e.get("beklenti"): K._t(ax, W - 48, y, f"beklenti {e['beklenti']}", 15, C["soluk"], ha="right")
            y -= 32
    else:
        K._t(ax, 48, y, "Bugün yüksek etkili veri yok.", 17, C["soluk"]); y -= 32
    y -= 18
    # fırsatlar ve açık kurulumlar
    K._t(ax, 48, y, "ÖNE ÇIKAN FIRSATLAR", 14, C["altin"], "semibold"); K._t(ax, 580, y, "AÇIK KURULUMLAR", 14, C["altin"], "semibold"); y -= 40
    y0 = y
    for f in firs[:3]:
        renk = C["yesil"] if f["yon"] == 1 else C["kirmizi"]
        K._t(ax, 48, y, _kod(f["kod"]), 20, weight="bold"); K._t(ax, 210, y, f"{'AL' if f['yon'] == 1 else 'SAT'} · {f['puan']:.0f}", 17, renk, "semibold")
        K._t(ax, 340, y, {"4S": "4 saatlik", "G": "günlük", "H": "haftalık", "A": "aylık"}.get(f["tf"], ""), 15, C["soluk"]); y -= 36
    if not firs: K._t(ax, 48, y, "Son kapanışlarda eşiği geçen fırsat yok.", 16, C["soluk"])
    y = y0
    acik_s = sorted(acik, key=lambda k: min(k["yak_h"], k["yak_s"]))[:3]
    for k in acik_s:
        renk = C["yesil"] if k["ger"] >= 0 else C["kirmizi"]
        K._t(ax, 580, y, _kod(k["kod"]), 20, weight="bold"); K._t(ax, W - 48, y, _y(k["ger"]), 17, renk, "semibold", ha="right"); y -= 36
    if not acik: K._t(ax, 580, y, "Açık kurulum yok.", 16, C["soluk"])
    y = min(y, y0 - 36 * 3) - 20
    # haberler
    if hab and y > 120:
        K._t(ax, 48, y, "SON HABERLER", 14, C["altin"], "semibold"); y -= 36
        for a in hab[:3]:
            if y < 70: break
            renk = C["yesil"] if a["yon"] > 0 else C["kirmizi"]
            from matplotlib.patches import Circle
            ax.add_patch(Circle((58, y + 7), 7, color=renk))
            K._t(ax, 76, y, textwrap.shorten(a["baslik"], 70, placeholder="…"), 16, C["yazi"]); y -= 32
    K._t(ax, W / 2, 18, "KATKAY YATIRIM A.Ş. · Gösterge bazlı analizdir, yatırım tavsiyesi değildir.", 13, C["silik"], ha="center")
    fig.savefig(dosya, dpi=100, facecolor=C["bg"]); plt.close(fig)
    return dosya


def ses_metni(PV, tk, madde):
    t = dt.datetime.now(TSI)
    s = [f"Günaydın. {t.day} {AYLAR[t.month - 1]} {GUNLER[t.weekday()]} sabah özeti."]
    for ad in ("BIST 100", "S&P 500", "Bitcoin", "Ons altın", "USD/TRY"):
        v = PV.get(ad)
        if v and v.get("d1G") is not None:
            d = v["d1G"] * 100
            ad_s = {"S&P 500": "Es en Pi beş yüz", "USD/TRY": "Dolar TL", "BIST 100": "Borsa İstanbul yüz endeksi", "Ons altın": "Ons altın"}.get(ad, ad)
            s.append(f"{ad_s} yüzde {abs(d):.1f}".replace(".", ",") + (" yükseldi." if d > 0 else " geriledi."))
    s += [m_.replace("%", "yüzde ") for m_ in madde]
    s.append("Bu bir gösterge bazlı analizdir, yatırım tavsiyesi değildir. İyi günler.")
    return " ".join(s)


def calistir():
    os.makedirs(os.path.join(CIKTI, "sabah"), exist_ok=True)
    PV = piyasalar(); tk = takvim_bugun(); acik = acik_kurulumlar(); firs = en_iyi_firsatlar(); hab = haberler()
    madde = izlenecekler(PV, tk, acik, firs, hab)
    yol = kart(PV, tk, acik, firs, hab, madde, os.path.join(CIKTI, "sabah", "kart.png"))
    ses = None
    try:
        from gtts import gTTS
        ses = os.path.join(CIKTI, "sabah", "ozet.mp3")
        gTTS(ses_metni(PV, tk, madde), lang="tr").save(ses)
    except Exception as ex:
        print("Sesli özet üretilemedi:", ex, file=sys.stderr); ses = None
    json.dump({"zaman": dt.datetime.now(TSI).isoformat(), "madde": madde}, open(os.path.join(CIKTI, "sabah", "ozet.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    b = tg.Bot("sabah")
    t = dt.datetime.now(TSI)
    alt = f"☀️ <b>SABAH ÖZETİ</b> · {t:%d.%m.%Y}\n" + "\n".join("• " + tg_kac(m_) for m_ in madde)
    b.sil_anahtar("sabah")
    if b.foto(yol, alt[:1000], "sabah", 20) and ses:
        try:
            with open(ses, "rb") as f:
                j = b._api("sendAudio", {"chat_id": b.chat, "title": f"Sabah özeti {t:%d.%m}", "performer": "KATKAY Yatırım",
                                         "disable_notification": True}, files={"audio": ("sabah_ozeti.mp3", f)}, timeout=120)
            if j.get("ok"): b._kaydet([j["result"]["message_id"]], "sabah", 20, None)
        except Exception as ex:
            print("Ses gönderilemedi:", ex, file=sys.stderr)
    b.kaydet()
    print("Sabah özeti hazır:", madde)


def tg_kac(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


if __name__ == "__main__":
    calistir()
