"""Aşama 14: altı rollü araştırma ekibi (kural tabanlı). Rol ilkeleri erhankatkay-glitch/agency-agents (MIT) dosyalarından uyarlandı:
finance-investment-researcher, finance-financial-analyst, academic-statistician, testing-test-results-analyzer,
testing-reality-checker; altıncı rol (risk yöneticisi) bu projenin ilkelerinden.

Raporlama ilkeleri (yol haritası, 27.11):
- Düşüş senaryosu yükseliş kadar ayrıntılı; tez bozucular (bu olursa görünüm bozulur);
- güven derecesi (veri kalitesi + geçmiş test); en kötü durumda rakamla kayıp; başarısız sinyaller de raporlanır.
Ücretsiz bir dil modeli anahtarı tanımlanırsa (ileride) yorum katmanı bu yapılandırılmış rapordan metin üretebilir;
şimdilik tüm metin kural tabanlıdır. Yatırım tavsiyesi değildir.
"""
import math, datetime as dt
import numpy as np
import pandas as pd

ROLLER = {
    "arastirmaci": ("Yatırım araştırmacısı", "Boğa ve ayı senaryosu eşit titizlikte; tez ölçülebilir olmalı, tez bozucular önceden yazılır."),
    "analist": ("Finansal analist", "Önce varsayımlar; tek nokta tahmin yok, baz/iyimser/kötümser senaryo; olgu ile tahmin ayrı."),
    "istatistikci": ("İstatistikçi", "Anlamlılık önem değildir; sonuç aralıkla verilir; az örnek 'bilemiyoruz' demektir; çok deneme yanlış pozitif üretir."),
    "test": ("Test sonuçları analisti", "Başarısız sinyaller de raporlanır; isabet oranı ve ortalama sonuç birlikte okunur."),
    "risk": ("Risk yöneticisi", "En kötü durum rakamla: stop gelirse kayıp, geçmiş en kötü günler (VaR), en büyük düşüş."),
    "denetci": ("Gerçeklik denetçisi", "Varsayılan tutum şüphecilik; çelişki ve veri sorunu varsa güven düşer, kusursuz görünüm kırmızı bayraktır."),
}
PIYASA = {"hisse": "bist", "abd": "abd", "kripto": "kripto", "emtia": "emtia", "endeks": "bist"}


def _tl(x, nd=2):
    if x is None or (isinstance(x, float) and not math.isfinite(x)): return "–"
    s = f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


SEBEP = {"hedef": "hedefe ulaştı", "stop": "stop oldu", "sure": "süre doldu", "süre": "süre doldu"}


def _r(x):
    return ("+" if x >= 0 else "-") + _tl(abs(x)) + "R"


def _y(x, nd=1):
    return ("+" if x >= 0 else "-") + "%" + _tl(abs(x) * 100, nd) if x is not None else "–"


# ------------------------------------------------------------------ yardımcı hesaplar
def getiri_istatistik(h):
    c = h["Close"].dropna(); r = np.log(c).diff().dropna()
    yil = r.tail(252)
    var = lambda q, n=1: float(np.exp(np.quantile(yil, q) * math.sqrt(n)) - 1) if len(yil) > 50 else None
    tepe = c.tail(252).cummax(); dd = float((c.tail(252) / tepe - 1).min()) if len(c) > 20 else None
    return {"sigma_g": float(yil.std()) if len(yil) > 20 else None, "var95": var(0.05), "var99": var(0.01), "var95_10": var(0.05, 10),
            "en_kotu_gun": float(np.exp(yil.min()) - 1) if len(yil) else None, "maks_dusus_1y": dd}


def kendi_gecmisi(s, piyasa, tf="G", son=8):
    """Bu varlığın kendi geçmişinde fırsat motorunun kurulumları: her olay simüle edilir (başarısızlar dahil)."""
    import firsat as F
    g = s["tf"].get(tf)
    if not g: return None
    A = F.diziler(g["h"], g["G"]); n = len(A["Close"]); bas = max(60, n - F.GECMIS_BAR)
    olaylar = []
    yonler = (1, -1) if piyasa == "kripto" else (1,)
    for y in yonler:
        M = F.ayna(A, y)
        tet = F.tetikler(M, ek=F.ek_kurulumlar(piyasa, tf, y) or None)
        H, L, C, O = M["High"].tolist(), M["Low"].tolist(), M["Close"].tolist(), M["Open"].tolist()
        for k, (m, stop) in tet.items():
            for t in np.flatnonzero(m):
                if t < bas or t >= n - 1: continue
                r = F.simule(H, L, C, t, C[t], stop[t], (1.0, 2.0, 3.0), F.MAKS_BAR[tf], O)
                if r is None: continue
                ad = F.KURULUM.get(k, (k, k))[0 if y == 1 else 1] or k
                olaylar.append({"tarih": g["h"].index[t], "kurulum": ad, "yon": y, "R": float(r[0]), "asama": r[1], "sebep": r[2]})
    if not olaylar: return {"n": 0, "olaylar": []}
    olaylar.sort(key=lambda x: x["tarih"])
    R = np.array([o["R"] for o in olaylar])
    ort = float(R.mean()); se = float(R.std(ddof=1) / math.sqrt(len(R))) if len(R) > 1 else None
    return {"n": len(R), "isabet": float((R > 0).mean()), "ort_R": ort, "ga": (ort - 1.96 * se, ort + 1.96 * se) if se else None,
            "en_kotu": float(R.min()), "olaylar": olaylar[-son:], "kurulum_sayisi": len({o["kurulum"] for o in olaylar})}


# ------------------------------------------------------------------ rapor
def rapor(s, temel=None, piyasa_ist=None, rejim=None, opsiyon=None, sermaye=10_000):
    """s: bist_teknik.analiz / analiz_h sonucu. temel: BIST ozet_satir sözlüğü (isteğe bağlı). piyasa_ist: firsat/<pz>/istatistik.json.
    rejim: rejim/<pz>.json. opsiyon: opsiyon/ozet.json içindeki para özeti. → yapılandırılmış rapor sözlüğü."""
    tur = s.get("tur", "hisse"); piyasa = PIYASA.get(tur, "bist"); sym = s.get("para", "")
    g, hf, ay = (s["tf"].get(k) for k in ("G", "H", "A"))
    if not g: return None
    p = g["fiyat"]; at = float(g["G"]["ATR"].iloc[-1]) if "ATR" in g["G"] else p * 0.02
    st_ = getiri_istatistik(g["h"])
    sr = g.get("sr") or {}
    dest = [d[0] for d in sr.get("destek", []) if d[0] < p][:2]; dire = [d[0] for d in sr.get("direnc", []) if d[0] > p][:2]
    sig20 = (st_["sigma_g"] or 0.02) * math.sqrt(20)
    R = {k: [] for k in ROLLER}
    # --- 1) yatırım araştırmacısı: ufuk, boğa/ayı tezi, katalizör, tez bozucular
    al = [x for x in g["sinyal"] if x[1] > 0]; sat = [x for x in g["sinyal"] if x[1] < 0]
    ufuk = "Kısa–orta vade (2–6 hafta), günlük ve haftalık grafik"
    boga = [x[0].split(": ", 1)[-1] for x in sorted(al, key=lambda x: -x[3])[:4]]
    ayi = [x[0].split(": ", 1)[-1] for x in sorted(sat, key=lambda x: -x[3])[:4]]
    if temel:
        if temel.get("Potansiyel") is not None: (boga if temel["Potansiyel"] > 0.15 else ayi if temel["Potansiyel"] < -0.1 else []).append(
            f"Temel değerleme potansiyeli {_y(temel['Potansiyel'], 0)} (adil değer {_tl(temel.get('Adil değer'))} {sym})")
        if temel.get("Sağlık skoru") is not None: (boga if temel["Sağlık skoru"] >= 65 else ayi if temel["Sağlık skoru"] < 45 else []).append(
            f"Finansal sağlık skoru {temel['Sağlık skoru']:.0f}/100")
        if temel.get("Reel büyüme") is not None: (boga if temel["Reel büyüme"] > 0.05 else ayi if temel["Reel büyüme"] < 0 else []).append(
            f"Reel satış büyümesi {_y(temel['Reel büyüme'], 0)}")
    if not boga: boga.append("Belirgin yükseliş sinyali yok")
    if not ayi: ayi.append("Belirgin düşüş sinyali yok")
    R["arastirmaci"] += [f"Ufuk: {ufuk}.", "Boğa tezi: " + "; ".join(boga) + ".", "Ayı tezi: " + "; ".join(ayi) + "."]
    bozucu = []
    if dest: bozucu.append(f"Günlük kapanış {_tl(dest[0] - 0.5 * at)} {sym} altına inerse (en yakın destek {_tl(dest[0])} kırılır) yükseliş tezi bozulur.")
    if dire: bozucu.append(f"Günlük kapanış {_tl(dire[0] + 0.5 * at)} {sym} üstüne çıkarsa (direnç {_tl(dire[0])} aşılır) düşüş tezi bozulur.")
    if hf: bozucu.append(f"Haftalık görünüm şu an {hf['etiket']}; {'SAT' if hf['puan'] >= 50 else 'AL'} bölgesine dönerse orta vade tezi değişir.")
    if rejim: bozucu.append(f"Piyasa rejimi şu an '{rejim.get('durum_ad')}'; 'Düzeltme'ye geçerse yeni alımlar için ortam bozulur.")
    if opsiyon and (opsiyon.get("buyuk_vadeler") or []):
        v = opsiyon["buyuk_vadeler"][0]
        if v.get("put_duvari"): bozucu.append(f"Opsiyon put duvarı {_tl(v['put_duvari'], 0)} kırılırsa korunma satışları hızlanabilir ({v['vade_ad']} vadesi).")
    # --- 2) finansal analist: varsayımlar + senaryolar + duyarlılık
    varsayim = [f"Günlük oynaklık son 1 yılın ortalaması (σ ≈ %{_tl((st_['sigma_g'] or 0) * 100)}) gibi devam eder.",
                "20 işlem günü ufkunda 1 standart sapma bandı kullanılır (%68 olasılık; kesinlik değildir).",
                "Destek/direnç geçmiş fiyat yığılmalarından hesaplanır; haber ve bilanço sürprizleri modele dahil değildir."]
    hedef_up = max(dire[0] if dire else p * (1 + sig20), p * (1 + 0.5 * sig20)); hedef_dn = min(dest[0] if dest else p * (1 - sig20), p * (1 - 0.5 * sig20))
    senaryo = [
        {"ad": "İyimser", "fiyat": max(hedef_up, p * (1 + sig20)), "kosul": (f"{_tl(dire[0])} direnci aşılır, " if dire else "") + "yükseliş sinyalleri teyit edilir"},
        {"ad": "Baz", "fiyat": p * (1 + 0.25 * sig20 * (1 if g["puan"] >= 58 else -1 if g["puan"] <= 42 else 0)),
         "kosul": f"mevcut görünüm ({g['etiket']}) sürer, fiyat bant içinde hareket eder"},
        {"ad": "Kötümser", "fiyat": min(hedef_dn, p * (1 - sig20)), "kosul": (f"{_tl(dest[0])} desteği kırılır, " if dest else "") + "satış baskısı artar"}]
    for x in senaryo: x["degisim"] = x["fiyat"] / p - 1
    duyarlilik = f"Oynaklık %15 yüksek varsayılırsa kötümser senaryo {_y(senaryo[2]['degisim'] * 1.15, 1)} olur; sonuç tablosu bu farka dayanıklı değilse güven düşük okunmalı."
    R["analist"] += ["Varsayımlar: " + " ".join(varsayim),
                     "Senaryolar (20 gün): " + " · ".join(f"{x['ad']} {_tl(x['fiyat'])} {sym} ({_y(x['degisim'])}): {x['kosul']}" for x in senaryo) + ".",
                     duyarlilik, "Olgu: son fiyat ve geçmiş göstergeler. Tahmin: senaryo fiyatları — ikisi karıştırılmamalı."]
    # --- 3) istatistikçi: kanıt gücü (piyasa istatistiği + bu varlığın geçmişi)
    kg = None
    try: kg = kendi_gecmisi(s, piyasa)
    except Exception: kg = None
    if piyasa_ist:
        eslesen = []
        import firsat as F
        for k_, v_ in (piyasa_ist.get("G") or {}).items():
            kk, yon, _ = k_.split("|")
            ad_ = F.KURULUM.get(kk, (kk, kk))[0 if yon == "1" else 1]
            if any(ad_ and ad_ in x[0] for x in g["sinyal"]):
                eslesen.append(f"{ad_}: piyasa genelinde {v_['n']} olay, ortalama {v_['ort_R']:+.2f}R, 1. hedefe ulaşma %{v_['p1'] * 100:.0f}".replace(".", ",", 1))
        if eslesen: R["istatistikci"].append("Taze kurulumların piyasa geneli kanıtı: " + "; ".join(eslesen[:3]) + ".")
    if kg and kg["n"]:
        ga = kg.get("ga")
        guc = ("zayıf (az örnek)" if kg["n"] < 20 else "orta" if kg["n"] < 60 else "makul")
        R["istatistikci"].append(f"Bu varlığın kendi geçmişinde {kg['n']} kurulum olayı ({kg['kurulum_sayisi']} farklı kurulum): ortalama {kg['ort_R']:+.2f}R".replace(".", ",", 1)
                                 + (f", %95 güven aralığı [{ga[0]:+.2f}, {ga[1]:+.2f}]R".replace(".", ",") if ga else "") + f"; kanıt gücü {guc}.")
        if ga and ga[0] < 0 < ga[1]: R["istatistikci"].append("Güven aralığı sıfırı kapsıyor: bu varlıkta kurulumların kazandırdığı istatistiksel olarak gösterilemiyor (\"bilemiyoruz\").")
    else:
        R["istatistikci"].append("Bu varlığın geçmişinde yeterli kurulum olayı yok; kanıt yalnız piyasa genelinden.")
    R["istatistikci"].append(f"Not: {len(g['sinyal'])} gösterge/kurulum birlikte tarandı; tek bir sinyalin öne çıkması şans eseri olabilir. "
                             "Göstergeler ilişki gösterir, nedensellik değil.")
    # --- 4) test sonuçları analisti: başarısız sinyaller dahil son olaylar
    if kg and kg.get("olaylar"):
        R["test"].append(f"Son {len(kg['olaylar'])} kurulumun sonucu (kazananlar ve kaybedenler):")
        for o in reversed(kg["olaylar"]):
            sonuc = "kazandı" if o["R"] > 0.05 else "kaybetti" if o["R"] < -0.05 else "başabaş"
            R["test"].append(f"{o['tarih']:%d.%m.%Y} · {o['kurulum']} · {sonuc} ({_r(o['R'])}, {SEBEP.get(o['sebep'], o['sebep'] or '—')})")
        R["test"].append(f"İsabet oranı %{kg['isabet'] * 100:.0f}, en kötü sonuç {_r(kg['en_kotu'])}.")
    # --- 5) risk yöneticisi: rakamla kayıp
    stop = (dest[0] - 0.5 * at) if dest else p - 2 * at
    kayip = (p - stop) / p
    R["risk"] += [f"Stop {_tl(stop)} {sym} (en yakın destek − 0,5 ATR) gelirse kayıp {_y(-kayip)} → {_tl(sermaye, 0)} TL'lik pozisyonda ≈ {_tl(sermaye * kayip, 0)} TL.",
                  (f"Geçmiş 1 yılın en kötü %5'lik günlerinde kayıp {_y(st_['var95'])} ({_tl(sermaye * abs(st_['var95']), 0)} TL), en kötü %1'de {_y(st_['var99'])}; "
                   f"10 günlük %5 VaR {_y(st_['var95_10'])}.") if st_["var95"] is not None else "VaR için yeterli geçmiş yok.",
                  f"Son 1 yılın en kötü günü {_y(st_['en_kotu_gun'])}, en büyük düşüş {_y(st_['maks_dusus_1y'])}." if st_["maks_dusus_1y"] is not None else ""]
    if rejim and rejim.get("maruziyet") is not None:
        R["risk"].append(f"Piyasa rejimi önerisi: portföyde en çok %{rejim['maruziyet']} hisse ({rejim.get('durum_ad')}).")
    # --- 6) gerçeklik denetçisi: çelişkiler, veri kalitesi, güven
    cel = []; puan = 2
    etk = [x["etiket"] for x in (g, hf, ay) if x]
    yon = lambda e: 1 if "AL" in e else -1 if "SAT" in e else 0
    if len({yon(e) for e in etk if yon(e) != 0}) > 1: cel.append(f"Zaman dilimleri çelişiyor ({' / '.join(etk)}).")
    if rejim and g["puan"] >= 58 and rejim.get("durum") in ("duzeltme", "ralli"): cel.append(f"Teknik görünüm AL ama piyasa rejimi '{rejim.get('durum_ad')}'.")
    if temel and g["puan"] >= 58 and (temel.get("Sağlık skoru") or 50) < 45: cel.append("Teknik AL, temel sağlık zayıf.")
    if temel and g["puan"] <= 42 and (temel.get("Potansiyel") or 0) > 0.3: cel.append("Teknik SAT, temel değerleme belirgin ucuz.")
    try:
        rsi = float(g["G"]["RSI"].iloc[-1])
        if g["puan"] >= 80 and rsi > 70: cel.append(f"Puan çok yüksek ({g['puan']:.0f}) ve RSI {rsi:.0f}: kusursuz görünüm geç kalma / aşırı alım riskidir.")
    except Exception:
        pass
    eski = None
    try:
        z = pd.Timestamp(s.get("fiyat_zamani") or g["tarih"])
        z = z.tz_localize("UTC") if z.tzinfo is None else z
        gun = (pd.Timestamp.now(tz="UTC") - z).days
        if gun > 4: eski = f"Fiyat verisi {gun} gün eski."
    except Exception:
        pass
    if eski: cel.append(eski)
    if kg and kg["n"] >= 20 and kg["ort_R"] > 0 and (kg.get("ga") or (0, 0))[0] > 0: puan += 1
    if kg and kg["n"] >= 20 and kg["ort_R"] < 0: puan -= 1; cel.append("Bu varlıkta kurulumların geçmiş ortalaması negatif.")
    puan -= min(2, len(cel))
    if len(etk) >= 2 and len({yon(e) for e in etk}) == 1 and yon(etk[0]) != 0: puan += 1
    guven = "Yüksek" if puan >= 3 else "Orta" if puan == 2 else "Düşük"
    if guven == "Yüksek" and cel: guven = "Orta"   # şüphecilik: çelişki varken yüksek güven verilmez
    R["denetci"] += (cel or ["Belirgin çelişki bulunmadı; yine de tek bir analiz kesinlik sağlamaz."]) + [f"Güven derecesi: {guven}."]
    gorunum = "AL eğilimli" if g["puan"] >= 58 else "SAT eğilimli" if g["puan"] <= 42 else "Nötr / kararsız"
    if guven == "Düşük" and gorunum != "Nötr / kararsız": gorunum += " (kanıt zayıf)"
    return {"kod": s.get("kod"), "ad": s.get("ad"), "fiyat": p, "para": sym, "gorunum": gorunum, "guven": guven, "ufuk": ufuk,
            "senaryolar": senaryo, "tez_bozucular": bozucu, "roller": [{"rol": k, "ad": ROLLER[k][0], "ilke": ROLLER[k][1], "bulgular": [x for x in R[k] if x]}
                                                                      for k in ROLLER],
            "risk": {"stop": stop, "kayip": kayip, **st_}, "gecmis": kg,
            "ozet": f"{gorunum} · güven {guven.lower()} · ufuk 2–6 hafta. Kötümser senaryoda {_y(senaryo[2]['degisim'])}, stop gelirse {_y(-kayip)}.",
            "uyari": "Kural tabanlı otomatik değerlendirmedir; yatırım tavsiyesi değildir."}
