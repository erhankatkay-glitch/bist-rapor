# -*- coding: utf-8 -*-
"""İleri analiz bölümlerinin PDF yapı taşları (hisse, kripto/emtia ve teknik raporlarda ortak)."""
import pandas as pd
from reportlab.platypus import Paragraph, Spacer, KeepTogether, CondPageBreak
from reportlab.lib.units import cm

import tasarim as TS
from tasarim import ST, bilgi_kutusu
import bist_ileri as IL


def _img(b, W, oran):
    from reportlab.platypus import Image
    return Image(b, width=W, height=W * oran)


def _ad(s):
    return s.replace("Mum: ", "Mum · ").replace("Formasyon: ", "")


def karne_blogu(karne, W, para=""):
    """Sinyal karnesi: aktif sinyallerin geçmiş başarısı + en güvenilir sinyaller tablosu."""
    if karne is None or karne.empty: return []
    E = [Paragraph("Sinyal karnesi: Bu varlıkta hangi sinyaller geçmişte işe yaradı?", ST["h2"]),
         bilgi_kutusu("Analist yorumu:", IL.karne_yorumu(karne), W), Spacer(1, 4)]
    goster = pd.concat([karne[karne["Aktif"]], karne[(~karne["Aktif"]) & (karne["Örnek"] >= 5)].sort_values("İsabet (20g)", ascending=False)]).head(14)
    v = [["Sinyal", "Yön", "Örnek", "İsabet 20g", "Ort. 5g", "Ort. 20g", "Ort. 60g", "Son"]]
    for _, r in goster.iterrows():
        ad = ("→ " if r["Aktif"] else "") + _ad(r["Sinyal"])
        v.append([Paragraph(TS.esc(ad[:60]), ST["hucre"]), "Al" if r["Yön"] > 0 else "Sat", str(r["Örnek"]), f"%{r['İsabet (20g)'] * 100:.0f}",
                  IL._y(r["5g ort"]), IL._y(r["20g ort"]), IL._y(r["60g ort"]), f"{r['Son']:%d.%m.%y}"])
    E.append(TS.tablo(v, [W * .36, W * .06, W * .07, W * .1, W * .1, W * .1, W * .1, W * .11], hizala_sol=(0,), font=7.0))
    E.append(Paragraph("→ şu anda aktif olan sinyal. İsabet: sinyal yönünde 20 işlem günü sonra kâr eden örneklerin oranı. "
                       f"Karşılaştırma için herhangi bir gün alınıp 20 gün tutulduğunda pozitif getiri oranı %{karne.attrs.get('taban_pozitif', 0) * 100:.0f}. "
                       "Geçmiş başarı geleceği garanti etmez; az örnekli sinyallerde sonuç güvenilir değildir.", ST["kucuk"]))
    return [CondPageBreak(9 * cm)] + E


def profil_blogu(h, profil, avwap, W, para=""):
    if not profil and not avwap: return []
    E = [Paragraph("Hacim profili ve sabitlenmiş VWAP seviyeleri", ST["h2"])]
    if profil:
        t = (f"Son {profil['gun']} işlem gününde en çok işlemin yoğunlaştığı fiyat (POC) <b>{IL._f(profil['poc'])} {para}</b>; işlemlerin %70'i "
             f"{IL._f(profil['val'])}–{IL._f(profil['vah'])} {para} değer alanında gerçekleşti. Fiyat şu anda {profil['konum']}. "
             "Yoğun işlem bölgeleri güçlü destek/direnç, seyrek bölgeler ise fiyatın hızlı geçtiği alanlardır.")
        E.append(bilgi_kutusu("Analist yorumu:", t, W)); E.append(Spacer(1, 4))
    E.append(_img(IL.g_profil(h, profil, avwap or {}, "Fiyat, hacim profili ve VWAP seviyeleri", 250 if not para == "$" else 365), W, 3.6 / 7.5 * 0.97))
    if avwap:
        p = float(h["Close"].iloc[-1])
        v = [["VWAP (başlangıç noktası)", f"Seviye ({para})", "Fiyata uzaklık", "Yorum"]]
        for ad, x in avwap.items():
            v.append([ad, IL._f(x), IL._y(p / x - 1), "Fiyat üzerinde: bu noktadan alanlar kârda" if p > x else "Fiyat altında: bu noktadan alanlar zararda"])
        E += [Spacer(1, 3), TS.tablo(v, [W * .32, W * .18, W * .16, W * .34], hizala_sol=(0, 3), font=7.2)]
    return [CondPageBreak(10 * cm)] + E


def aralik_blogu(h, fa, W, para=""):
    if not fa: return []
    E = [Paragraph("Olası fiyat aralığı (volatiliteye dayalı)", ST["h2"]), bilgi_kutusu("Analist yorumu:", IL.aralik_yorumu(fa, para), W), Spacer(1, 4),
         _img(IL.g_aralik(h, fa, "Olasılık bantları (koyu: %68, açık: %95)"), W * 0.9, 2.8 / 7.5 * 0.9)]
    v = [["Süre", "%68 alt", "%68 üst", "%95 alt", "%95 üst", ">%10 yükseliş*", ">%10 düşüş*"]]
    for u in fa["ufuklar"]:
        v.append([u["ad"], IL._f(u["68_alt"]), IL._f(u["68_ust"]), IL._f(u["95_alt"]), IL._f(u["95_ust"]),
                  f"%{(u['olasilik_10_ust'] or 0) * 100:.0f}", f"%{(u['olasilik_10_alt'] or 0) * 100:.0f}"])
    E += [Spacer(1, 3), TS.tablo(v, [W * .12, W * .14, W * .14, W * .14, W * .14, W * .16, W * .16], font=7.2),
          Paragraph(f"Yıllık volatilite tahmini %{fa['yillik_vol'] * 100:.0f}. *Geçmişteki aynı uzunluktaki dönemlerde görülme sıklığı. "
                    "Bantlar istatistikseldir; haber ve olay riski bu aralığın dışına taşabilir.", ST["kucuk"])]
    return [KeepTogether(E)]


def bilanco_blogu(bt, sonraki, W):
    if not bt: return []
    E = [Paragraph("Bilanço tepki analizi", ST["h2"]), bilgi_kutusu("Analist yorumu:", IL.bilanco_yorumu(bt, sonraki), W), Spacer(1, 4)]
    v = [["Açıklama", "1 gün", "5 gün", "20 gün", "1g BIST 100'e göre", "5g BIST 100'e göre"]]
    for _, r in bt["tablo"].head(10).iterrows():
        v.append([f"{r['Tarih']:%d.%m.%Y}", IL._y(r.get("1g")), IL._y(r.get("5g")), IL._y(r.get("20g")), IL._y(r.get("1g fark")), IL._y(r.get("5g fark"))])
    E.append(TS.tablo(v, [W * .16, W * .14, W * .14, W * .14, W * .21, W * .21], font=7.2))
    return [CondPageBreak(7 * cm)] + E


def aciga_blogu(kod, ac, W):
    if not ac: return []
    import bist_borsa as BB
    E = [Paragraph("Açığa satış görünümü", ST["h2"]), bilgi_kutusu("Analist yorumu:", BB.aciga_yorumu(kod, ac.get("satir"), ac.get("oran"), ac.get("donem")), W),
         Paragraph("Kaynak: Borsa İstanbul haftalık açığa satış bülteni. Yüksek açığa satış oranı düşüş beklentisine işaret edebileceği gibi, "
                   "açığa satanların pozisyon kapatması (geri alım) ani yükselişleri de tetikleyebilir.", ST["kucuk"])]
    return [KeepTogether(E)]


def kap_blogu(liste, W):
    if liste is None: return []
    import bist_borsa as BB
    E = [Paragraph("KAP gündemi (bildirim konulu haberler)", ST["h2"]), bilgi_kutusu("Analist yorumu:", BB.kap_yorumu(liste), W)]
    if liste:
        v = [["Tarih", "Konu", "Başlık", "Etki"]]
        for x in liste[:10]:
            v.append([f"{x['tarih']:%d.%m}" if x.get("tarih") else "–", Paragraph(x["konu"], ST["hucre"]), Paragraph(TS.esc(x["baslik"][:120]), ST["hucre"]),
                      "Olumlu" if x["yon"] > 0 else "Olumsuz" if x["yon"] < 0 else "Nötr"])
        E += [Spacer(1, 4), TS.tablo(v, [W * .08, W * .22, W * .58, W * .12], hizala_sol=(0, 1, 2), font=7.0)]
    E.append(Paragraph("Başlıklar Google Haberler üzerinden KAP bildirimleriyle ilişkili haberlerden derlenir ve konuya göre otomatik sınıflandırılır; "
                       "resmi metin için kap.org.tr'yi kontrol edin.", ST["kucuk"]))
    return [CondPageBreak(6 * cm)] + E


def mikro_blogu(mk, vd, df_, W, para="$"):
    """Kripto: emir defteri, büyük işlemler, vadeli piyasa ve DeFi."""
    import bist_kripto as KR
    E = []
    ed, bi, tk = (mk or {}).get("defter"), (mk or {}).get("islem"), (mk or {}).get("taker")
    if ed or bi or tk is not None:
        E += [Paragraph("Piyasa mikro yapısı: emir defteri ve işlem akışı", ST["h2"]), bilgi_kutusu("Analist yorumu:", KR.mikro_yorum(ed, bi, tk, para), W), Spacer(1, 4)]
        if ed:
            v = [["Bant", f"Alış emirleri ({para})", f"Satış emirleri ({para})", "Denge"]]
            for b, x in ed["bant"].items():
                v.append([f"±%{b * 100:.0f}", TS._sayi(x["alis"], 0), TS._sayi(x["satis"], 0), IL._y(x["denge"], 0)])
            v2 = [["Emir duvarı", "Fiyat", f"Tutar ({para})"]] + [["Alış", TS._sayi(p), TS._sayi(t, 0)] for p, t in ed["alis_duvarlari"]] + \
                 [["Satış", TS._sayi(p), TS._sayi(t, 0)] for p, t in ed["satis_duvarlari"]]
            PW = (W - 10) / 2
            E.append(TS.yan_yana(TS.tablo(v, [PW * .2, PW * .3, PW * .3, PW * .2], font=7.2), TS.tablo(v2, [PW * .3, PW * .35, PW * .35], font=7.2), W))
    if vd:
        E += [Spacer(1, 6), Paragraph("Vadeli piyasa: açık pozisyon, agresif işlemler ve likidasyonlar (OKX)", ST["h2"]),
              bilgi_kutusu("Analist yorumu:", KR.vadeli_yorum(vd, (mk or {}).get("fiyat_7g")), W)]
        v = [["Gösterge", "Değer"]]
        if vd.get("oi_son") is not None: v.append(["Açık pozisyon", f"{TS._sayi(vd['oi_son'], 0)} $"])
        if vd.get("oi_7g") is not None: v.append(["Açık pozisyon değişimi (7g / 30g)", f"{IL._y(vd['oi_7g'])} / {IL._y(vd.get('oi_30g'))}"])
        if vd.get("taker_7g") is not None: v.append(["Agresif alım payı (7g)", f"%{vd['taker_7g'] * 100:.0f}"])
        lq = vd.get("likidasyon")
        if lq: v.append(["Son likidasyonlar (long / short)", f"{TS._sayi(lq['long'], 0)} $ / {TS._sayi(lq['short'], 0)} $"])
        if len(v) > 1: E += [Spacer(1, 3), TS.tablo(v, [W * .5, W * .3], font=7.2)]
    if df_ and any(df_.values()):
        E += [Spacer(1, 6), Paragraph("Likidite ve DeFi verileri (DefiLlama)", ST["h2"]),
              bilgi_kutusu("Analist yorumu:", KR.defi_yorum(df_.get("stable"), df_.get("tvl"), df_.get("protokol")), W)]
        pr = df_.get("protokol")
        if pr and pr.get("tvl"):
            v = [["Gösterge", "Değer"], ["Protokol / zincir", f"{pr['ad']} ({pr.get('kategori') or '–'})"], ["TVL", f"{TS._sayi(pr['tvl'], 0)} $"],
                 ["TVL değişimi (7g)", IL._y(pr.get("d7"))], ["Piyasa değeri / TVL", f"{pr['mcap_tvl']:.2f}".replace(".", ",") if pr.get("mcap_tvl") else "–"],
                 ["Ücretler (30 gün)", f"{TS._sayi(pr['ucret_30g'], 0)} $" if pr.get("ucret_30g") else "–"],
                 ["Fiyat / ücret (yıllık)", f"{pr['fiyat_ucret']:.1f}x".replace(".", ",") if pr.get("fiyat_ucret") else "–"]]
            v = [x for x in v if x[1] != "–" or x[0] == "Gösterge"]
            E += [Spacer(1, 3), TS.tablo(v, [W * .4, W * .4], font=7.2)]
    return ([CondPageBreak(9 * cm)] + E) if E else []


def ileri_bolum(h, paket, W, para="", baslik_no=None, baslik="İleri teknik analiz: sinyal geçmişi, hacim profili ve olasılık bantları"):
    from tasarim import Bolum
    E = [CondPageBreak(10 * cm)]
    if baslik_no is not None: E.append(Bolum(baslik_no, baslik, W))
    E += karne_blogu(paket.get("karne"), W, para)
    E += profil_blogu(h, paket.get("profil"), paket.get("avwap"), W, para)
    E += aralik_blogu(h, paket.get("aralik"), W, para)
    return E
