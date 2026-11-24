# -*- coding: utf-8 -*-
"""Kurumsal araştırma raporu dili: başlık tezi, genel görüş, yönetici özeti, yatırım tezi,
senaryolar, katalizörler, riskler ve bölüm girişleri. Kural tabanlıdır; tüm cümleler
modelin ürettiği sayılara dayanır. Hedef: üst düzey bir analistin yazacağı netlikte ama
finans eğitimi olmayan bir okurun da anlayacağı sadelikte metin."""
import datetime as dt
import math
import pandas as pd

# ---------------------------------------------------------------- biçim yardımcıları
def _n(x, d=1):
    if x is None or (isinstance(x, float) and math.isnan(x)): return "–"
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def yuzde(x, d=1, isaret=False):
    if x is None or (isinstance(x, float) and math.isnan(x)): return "–"
    s = ("+" if x > 0 else "-" if x < 0 else "") if isaret else ("-" if x < 0 else "")
    return s + "%" + _n(abs(x) * 100, d)

PARA = "TL"


def EN():
    import bist_rapor as br
    return br.EN


def tutar(x, para=None):
    para = para or PARA
    """Büyük tutarlar için okunur biçim: 444,6 milyar TL."""
    if x is None: return "–"
    a = abs(x)
    for e, ad in ((1e12, "trilyon"), (1e9, "milyar"), (1e6, "milyon")):
        if a >= e: return f"{_n(x / e, 1)} {ad} {para}".strip()
    return f"{_n(x, 0)} {para}".strip()

def fiyat(x, para=None):
    para = para or PARA
    if x is None: return "–"
    import tasarim as TS
    return f"{_n(x, TS.basamak(x))} {para}".strip()

def kat(x):
    return "–" if x is None else _n(x, 1) + "x"

def kk(s):
    """Türkçe küçük harf (I→ı, İ→i)."""
    return str(s).replace("I", "ı").replace("İ", "i").lower() if s is not None else ""


AKIS_IFADE = {"GÜÇLÜ GİRİŞ": "güçlü para girişine", "GİRİŞ": "para girişine", "NÖTR": "dengeli bir görünüme",
              "ÇIKIŞ": "para çıkışına", "GÜÇLÜ ÇIKIŞ": "güçlü para çıkışına"}
TEKNIK_IFADE = {"GÜÇLÜ POZİTİF": "güçlü olumlu", "POZİTİF": "olumlu", "NÖTR": "nötr", "NEGATİF": "olumsuz", "GÜÇLÜ NEGATİF": "güçlü olumsuz"}


def ilk_kucuk(s):
    """Cümle içinde kullanmak için ilk harfi küçültür; kısaltmalar (OBO, MACD, BOS) korunur."""
    if not s: return s
    k = s.split(" ")[0]
    if len(k) > 1 and k[:2].isupper(): return s
    return ("i" if s[0] == "İ" else "ı" if s[0] == "I" else kk(s[0])) + s[1:]


def bas_buyuk(s):
    return s[:1].upper() + s[1:] if s else s

SEKTOR_TR = {"Industrials": "sanayi", "Financial Services": "finansal hizmetler", "Basic Materials": "temel malzemeler",
             "Consumer Cyclical": "dayanıklı/döngüsel tüketim", "Consumer Defensive": "temel tüketim", "Energy": "enerji",
             "Utilities": "elektrik ve kamu hizmetleri", "Real Estate": "gayrimenkul", "Technology": "teknoloji",
             "Communication Services": "iletişim", "Healthcare": "sağlık"}

SEKTOR_NOT = {
    "Bankacılık": (["faiz indirim döngüsünün net faiz marjı üzerindeki etkisi", "aktif kalitesinde bozulma ve artan karşılık giderleri",
                    "BDDK kredi büyüme sınırlamaları ve makro ihtiyati düzenlemeler"],
                   ["TCMB faiz kararları ve mevduat maliyetlerindeki gerileme", "kredi büyüme sınırlamalarının gevşetilmesi",
                    "çeyreklik net faiz marjı ve takipteki kredi açıklamaları"]),
    "Holding": (["iştirak değerlemelerindeki dalgalanma", "holding iskontosunun tarihsel ortalamaların üzerine açılması",
                 "holding seviyesindeki borçluluk ve nakit yönetimi"],
                ["iştirak satışları, birleşmeler veya halka arzlar", "pay geri alım programları", "iştiraklerin finansal sonuçları"]),
    "Havacılık": (["jet yakıtı fiyatlarındaki oynaklık", "turizm talebindeki olası yavaşlama", "kur ve maliyet enflasyonu"],
                  ["aylık yolcu ve doluluk oranı açıklamaları", "yaz sezonu rezervasyon eğilimleri", "filo ve kapasite planlaması"]),
    "Demir-Çelik": (["küresel çelik fiyatları ve Çin kaynaklı arz fazlası", "enerji maliyetleri", "AB Sınırda Karbon Düzenlemesi"],
                    ["küresel çelik fiyatlarında toparlanma", "inşaat ve altyapı talebi", "ihracat pazarlarındaki gelişmeler"]),
    "Otomotiv": (["iç pazarda kredi koşulları ve ÖTV düzenlemeleri", "Avrupa ihracat talebi", "EUR/TRY paritesi ve maliyet enflasyonu"],
                 ["aylık satış ve ihracat verileri", "yeni model lansmanları", "kredi koşullarında gevşeme"]),
    "Perakende": (["gıda enflasyonu kaynaklı marj baskısı", "asgari ücret ve personel maliyetleri", "rekabet ve fiyat düzenlemeleri"],
                  ["mağaza açılış planları", "benzer mağaza satış büyümesi", "enflasyonda düşüşle marj iyileşmesi"]),
    "Telekom": (["tarife ve regülasyon düzenlemeleri", "yüksek yatırım harcaması ihtiyacı", "kur riski"],
                ["fiyat artışlarının gelirlere yansıması", "abone başına gelir (ARPU) büyümesi", "5G süreci"]),
    "Enerji": (["emtia fiyatları ve rafineri/üretim marjları", "elektrik piyasası regülasyonları", "kur ve finansman maliyetleri"],
               ["marj ve fiyat ortamındaki iyileşme", "yeni kapasite devreye alımları", "temettü dağıtım kararları"]),
    "Savunma": (["kamu siparişlerinin zamanlaması ve tahsilat döngüsü", "işletme sermayesi ihtiyacı", "ihracat lisansları ve jeopolitik gelişmeler"],
                ["yeni sipariş ve ihracat sözleşmesi duyuruları", "sipariş bakiyesindeki artış", "teslimat takvimi"]),
    "Kimya-Cam": (["hammadde ve enerji maliyetleri", "Avrupa talebindeki zayıflık", "kapasite kullanım oranları"],
                  ["Avrupa talebinde toparlanma", "yeni yatırımların devreye girmesi", "maliyetlerde gevşeme"]),
    "Çimento": (["enerji maliyetleri", "inşaat sektöründeki yavaşlama", "ihracat fiyatları"],
                ["kentsel dönüşüm ve deprem bölgesi yapılaşması", "ihracat fiyatlarında artış", "enerji maliyetlerinde düşüş"]),
    "Gıda-İçecek": (["hammadde maliyetleri", "fiyat artışlarının talebe etkisi", "kur riski"],
                    ["hacim büyümesi", "fiyatlama gücüyle marj iyileşmesi", "yurt dışı operasyonlar"]),
    "Dayanıklı Tüketim": (["Avrupa talebi", "maliyet enflasyonu ve rekabet", "işletme sermayesi finansmanı"],
                          ["ihracat siparişleri", "maliyet verimliliği programları", "faiz indirimleriyle iç talep"]),
    "GYO": (["konut satışlarında yavaşlama", "yüksek faiz ortamı", "net aktif değere göre iskontonun sürmesi"],
            ["faiz indirimleri", "proje satış ve teslim takvimi", "kira gelirlerindeki artış"]),
}
GENEL_RISK_ABD = "Fed faiz politikası ve tahvil faizlerindeki oynaklık, yüksek değerlemeli teknoloji hisselerinde düzeltme riski, dolar endeksi ve küresel büyüme beklentilerindeki değişimler"
GENEL_RISK = GENEL_RISK_TR = "yüksek enflasyon ve sıkı para politikası ortamı, TL'deki değer kaybı ve küresel risk iştahındaki dalgalanmalar"


def sektor_adi(m):
    import bist_rapor as br
    g = next((g_ for g_, l_ in br.SEKTOR_GRUPLARI.items() if m["kod"] in l_), None)
    if g: return g, kk(g)
    s = m.get("sektor") or ""
    return None, SEKTOR_TR.get(s, kk(s) if s and s != "–" else "")


# ================================================================ HİSSE
def _surucular(m):
    """Raporu yönlendiren etkenler: (puan -2..+2, olumlu kısa ifade, olumsuz kısa ifade, ayrıntı cümlesi, başlık)."""
    import bist_rapor as br
    enf = br.PARAM["ENFLASYON"]; S = []; es = (m.get("emsal_stat") or {})
    pt = m.get("potansiyel")
    if pt is not None:
        p = 2 if pt > 0.25 else 1 if pt > 0.10 else -2 if pt < -0.25 else -1 if pt < -0.10 else 0
        S.append((p, "belirgin değerleme iskontosu" if p == 2 else "cazip değerleme", "yüksek değerleme primi" if p == -2 else "primli fiyatlama",
                  f"Birleşik adil değerimiz {fiyat(m['adil'])}, mevcut fiyata göre {yuzde(pt, 1, True)} fark gösteriyor"
                  + ("; piyasa şirketi temel değerinin belirgin altında fiyatlıyor." if p > 0 else "; beklentilerin önemli kısmı fiyata yansımış durumda." if p < 0 else "; fiyat makul değer bandında."),
                  "Değerleme"))
    if es.get("fk") and m.get("fk"):
        r = m["fk"] / es["fk"]["med"] - 1
        p = 1 if r < -0.3 else -1 if r > 0.3 else 0
        S.append((p, "emsallerine göre iskontolu çarpanlar", "emsallerine göre primli çarpanlar",
                  f"F/K {kat(m['fk'])} ile emsal medyanının ({kat(es['fk']['med'])}) {yuzde(abs(r), 0)} {'altında' if r < 0 else 'üzerinde'} işlem görüyor.",
                  "Göreli değerleme"))
    if m.get("roe") is not None:
        f = m["roe"] - enf
        p = 2 if f > 0.10 else 1 if f > 0 else -2 if f < -0.10 else -1
        S.append((p, "enflasyonun üzerinde güçlü kârlılık" if p == 2 else "reel bazda pozitif kârlılık",
                  "reel bazda negatif özkaynak getirisi" if p == -2 else "enflasyonun gerisinde kalan kârlılık",
                  f"Özkaynak kârlılığı {yuzde(m['roe'])}, yıllık enflasyon {yuzde(enf)}; şirket " +
                  ("ortaklarına reel değer yaratıyor." if f > 0 else "reel bazda sermaye maliyetini karşılayamıyor."), "Kârlılık"))
    rb = br.reel(m.get("ciro_b"))
    if rb is not None:
        p = 2 if rb > 0.10 else 1 if rb > 0.02 else -2 if rb < -0.10 else -1 if rb < -0.02 else 0
        S.append((p, "güçlü reel büyüme" if p == 2 else "reel büyüme", "reel bazda daralan satışlar" if p == -2 else "zayıflayan reel büyüme",
                  f"Hasılat nominal {yuzde(m['ciro_b'], 1, True)}, enflasyondan arındırıldığında {yuzde(rb, 1, True)} değişti.", "Büyüme"))
    qn = m.get("ceyrek_net_b")
    if qn is not None:
        p = 1 if qn > enf + 0.1 else -1 if qn < 0 else 0
        S.append((p, "son çeyrekte kâr ivmesi", "son çeyrekte kâr kaybı",
                  f"Son çeyrek net kârı yıllık bazda {yuzde(qn, 1, True)} değişti" + (" ve enflasyonu aştı." if qn > enf else "."), "Çeyreklik ivme"))
    if m.get("banka"):
        bk = m["banka"]; ov = bk.get("ozk_varlik")
        if ov is not None:
            p = 1 if ov > 0.10 else -1 if ov < 0.07 else 0
            S.append((p, "sağlam sermaye tamponu", "ince sermaye tamponu",
                      f"Özkaynak/aktif oranı {yuzde(ov)}" + (f", net faiz marjı {yuzde(bk.get('nim'))}" if bk.get("nim") is not None else "")
                      + (f", risk maliyeti {yuzde(bk.get('risk_maliyeti'))}" if bk.get("risk_maliyeti") is not None else "") + ".", "Sermaye"))
    else:
        if m.get("net_borc") is not None and m["net_borc"] < 0:
            S.append((2, "net nakit pozisyonu", "", f"Şirket {tutar(-m['net_borc'])} net nakde sahip; bilanço esnekliği yüksek.", "Bilanço"))
        elif m.get("nb_favok") is not None:
            x = m["nb_favok"]; p = 1 if x < 1.5 else -2 if x > 3.5 else -1 if x > 2.5 else 0
            S.append((p, "düşük kaldıraç", "yüksek kaldıraç", f"Net borç/FAVÖK {kat(x)}; " +
                      ("borç yükü rahat taşınabilir seviyede." if x < 1.5 else "kaldıraç yönetilebilir." if x <= 2.5 else "yüksek faiz ortamında finansman giderleri kârlılığı baskılayabilir."), "Bilanço"))
        sv = m.get("sna_verim")
        if sv is not None:
            p = 1 if sv > 0.06 else -1 if sv < 0 else 0
            S.append((p, "güçlü serbest nakit üretimi", "negatif serbest nakit akışı",
                      f"Serbest nakit akışı verimi {yuzde(sv)}" + ("; temettü ve borç azaltımı için alan yaratıyor." if sv > 0.06 else
                      "; yatırımlar ve işletme sermayesi dış finansmana dayanıyor." if sv < 0 else "."), "Nakit akışı"))
    tv = m.get("temettu_verim")
    if tv and tv > 0.05:
        S.append((1, "yüksek temettü verimi", "", f"Son 12 aylık temettü verimi {yuzde(tv)}.", "Temettü"))
    nav = m.get("nav")
    if nav and nav.get("iskonto") is not None:
        d = nav["iskonto"] - nav["hedef_iskonto"]
        p = 1 if d > 0.05 else -1 if d < -0.05 else 0
        S.append((p, "tarihsel ortalamanın üzerinde NAV iskontosu", "dar NAV iskontosu",
                  f"Holding, halka açık iştiraklerinin değerine göre {yuzde(nav['iskonto'], 0)} iskontolu (varsayımımız {yuzde(nav['hedef_iskonto'], 0)}).", "NAV"))
    ts_ = teknik_surucu(m.get("mta"))
    if ts_: S.append(ts_)
    tk = m.get("teknik_ozet") or ""
    p = 1 if "POZİTİF" in tk else -1 if "NEGATİF" in tk else 0
    if not ts_: S.append((p, "olumlu fiyat momentumu", "zayıf fiyat momentumu",
              f"Teknik göstergeler {TEKNIK_IFADE.get(tk, kk(tk))} sinyal veriyor; fiyat 200 günlük ortalamanın {'üzerinde' if m.get('ma200') and m['fiyat'] > m['ma200'] else 'altında'}.", "Momentum"))
    a = m.get("akis") or {}
    if a:
        p = 1 if a.get("puan", 0) > 0 else -1 if a.get("puan", 0) < 0 else 0
        S.append((p, "hacimle desteklenen para girişi", "hacim bazlı para çıkışı",
                  f"Hacim bazlı para akışı göstergeleri {AKIS_IFADE.get(a.get('ozet'), 'karışık bir görünüme')} işaret ediyor" +
                  (f"; yabancı payı {yuzde((m.get('yabanci') or {}).get('oran', 0) / 100)}." if m.get("yabanci") else "."), "Para akışı"))
    return S


def gorus(m):
    """Genel görüş: değerleme (%45), finansal sağlık (%35), momentum/akış (%20)."""
    pt = m.get("potansiyel") or 0; gs = m.get("genel_skor") or 2.75
    tk = {"GÜÇLÜ POZİTİF": 1, "POZİTİF": 0.5, "NÖTR": 0, "NEGATİF": -0.5, "GÜÇLÜ NEGATİF": -1}.get(m.get("teknik_ozet"), 0)
    if (m.get("mta") or {}).get("puan") is not None:
        tk = max(min((m["mta"]["puan"] - 50) / 35, 1), -1)
    ak = max(min((m.get("akis") or {}).get("puan", 0) / 2, 1), -1)
    s = 0.45 * max(min(pt / 0.3, 1), -1) + 0.35 * max(min((gs - 2.75) / 1.25, 1), -1) + 0.20 * (0.6 * tk + 0.4 * ak)
    et = "OLUMLU" if s > 0.35 else "ILIMLI OLUMLU" if s > 0.12 else "OLUMSUZ" if s < -0.35 else "TEMKİNLİ" if s < -0.12 else "NÖTR"
    return et, s


def baslik_tezi(m):
    S = sorted(_surucular(m), key=lambda x: -abs(x[0]))
    pos = [x[1] for x in sorted([x for x in S if x[0] > 0], key=lambda x: -x[0])]
    neg = [x[2] for x in sorted([x for x in S if x[0] < 0], key=lambda x: x[0])]
    et, s = gorus(m)
    if s >= 0 and pos:
        t = bas_buyuk(pos[0]) + (f" ve {pos[1]}" if len(pos) > 1 else "")
        return t + (f"; {neg[0]} izlenmeli" if neg else "; temel görünüm dengeli")
    if neg:
        t = bas_buyuk(neg[0]) + (f" ve {neg[1]}" if len(neg) > 1 else "") + " baskı unsuru"
        return t + (f"; {pos[0]} sınırlı destek sağlıyor" if pos else "")
    return "Dengeli görünüm; belirgin bir değerleme ya da temel ayrışma yok"


def yonetici_ozeti(m, kisa=False):
    import bist_rapor as br
    enf = br.PARAM["ENFLASYON"]; g_, sektor = sektor_adi(m); C = []
    et, _ = gorus(m)
    fk_t = (f"{kat(m['fk'])} F/K ve {kat(m['pddd'])} PD/DD çarpanlarıyla" if m.get("fk") else
            f"{kat(m.get('pddd'))} PD/DD çarpanıyla (son 12 aylık zarar nedeniyle F/K anlamlı değil)")
    C.append(f"{m['ad']} ({m['kod']}), {(sektor + ' sektöründe ') if sektor else ''}{tutar(m['piy_deg'])} piyasa değeriyle işlem görüyor; "
             f"hisse son 12 aylık verilere göre {fk_t} fiyatlanıyor.")
    if m.get("adil"):
        dahil = [y for y in m["yontemler"] if y[6]]
        yay = (max(y[1] for y in dahil) / min(y[1] for y in dahil) - 1) if len(dahil) > 1 and min(y[1] for y in dahil) > 0 else None
        C.append(f"{len(dahil)} değerleme yönteminin birleşik sonucu hisse başına <b>{fiyat(m['adil'])}</b> adil değere işaret ediyor; bu, " +
                 (f"mevcut {fiyat(m['fiyat'])} fiyata göre <b>{yuzde(m['potansiyel'], 1, True)}</b> " +
                  ("yukarı yönlü potansiyel anlamına geliyor." if m["potansiyel"] > 0 else "aşağı yönlü risk anlamına geliyor.")
                  if abs(m["potansiyel"]) >= 0.02 else f"mevcut {fiyat(m['fiyat'])} fiyatla büyük ölçüde örtüşüyor.") +
                 (f" Yöntemler arasındaki dağılımın {'geniş' if yay > 1 else 'makul'} olması nedeniyle model güvenini {kk(m['guven'])} olarak değerlendiriyoruz." if yay is not None else ""))
    if kisa:
        S = _surucular(m); pos = [x for x in S if x[0] > 0]; neg = [x for x in S if x[0] < 0]
        if pos and neg:
            C.append(f"Güçlü yönler arasında {pos[0][1]} öne çıkarken, {neg[0][2]} temel risk unsuru olarak izlenmeli.")
        elif pos:
            C.append(f"Görünümü destekleyen başlıca unsur {pos[0][1]}.")
        elif neg:
            C.append(f"Görünüm üzerindeki başlıca baskı unsuru {neg[0][2]}.")
        if teknik_cumle(m.get("mta"), kisa=True): C.append(teknik_cumle(m.get("mta"), kisa=True))
        C.append(f"Genel görünümümüz <b>{kk(et)}</b>.")
        return " ".join(C)
    if m.get("roe") is not None:
        t = (f"Operasyonel tarafta şirket son 12 ayda {yuzde(m['roe'])} özkaynak kârlılığı üretti; bu oran {yuzde(enf)} seviyesindeki yıllık enflasyonun "
             + ("üzerinde kalarak ortaklar için reel değer yaratıldığını gösteriyor." if m["roe"] > enf else "altında kalarak kârlılığın reel bazda sermaye maliyetini karşılamadığına işaret ediyor."))
        rb = br.reel(m.get("ciro_b"))
        if rb is not None:
            t += (" Hasılatın enflasyondan arındırılmış büyümesi " + yuzde(rb, 1, True) + (" ile güçlü bir talep ve fiyatlama gücüne işaret ediyor." if rb > 0.05
                  else " ile sınırlı kaldı." if rb > -0.02 else " ile reel daralmayı yansıtıyor."))
        C.append(t)
    if m.get("banka"):
        bk = m["banka"]
        C.append("Bilanço tarafında " + ", ".join(x for x in [
            f"net faiz marjı {yuzde(bk.get('nim'))}" if bk.get("nim") is not None else "",
            f"risk maliyeti {yuzde(bk.get('risk_maliyeti'))}" if bk.get("risk_maliyeti") is not None else "",
            f"kredi/mevduat oranı {kat(bk.get('kredi_mevduat'))}" if bk.get("kredi_mevduat") is not None else "",
            f"özkaynak/aktif {yuzde(bk.get('ozk_varlik'))}" if bk.get("ozk_varlik") is not None else ""] if x) + " seviyesinde.")
    else:
        t = ""
        if m.get("net_borc") is not None and m["net_borc"] < 0: t = f"Bilanço {tutar(-m['net_borc'])} net nakit pozisyonuyla güçlü"
        elif m.get("nb_favok") is not None: t = f"Net borç/FAVÖK oranı {kat(m['nb_favok'])} ile kaldıraç " + ("düşük" if m["nb_favok"] < 1.5 else "yönetilebilir" if m["nb_favok"] <= 2.5 else "yüksek")
        if m.get("sna_verim") is not None:
            t += ("; " if t else "Şirketin ") + f"serbest nakit akışı verimi {yuzde(m['sna_verim'])}" + (" ile güçlü nakit üretimini teyit ediyor" if m["sna_verim"] > 0.05 else " ile negatif seyrediyor" if m["sna_verim"] < 0 else "")
        if t: C.append(t + ".")
    r1, e1 = m["r"].get("1Y"), m["r_endeks"].get("1Y")
    if r1 is not None:
        t = f"Hisse son 12 ayda {yuzde(r1, 1, True)} getiri sağladı" + (f" ve {EN()} endeksinin ({yuzde(e1, 1, True)}) {'üzerinde' if r1 > e1 else 'gerisinde'} kaldı" if e1 is not None else "")
        if (m.get("mta") or {}).get("puan") is None:
            t += f"; teknik göstergeler {TEKNIK_IFADE.get(m['teknik_ozet'], kk(m['teknik_ozet']))} sinyal veriyor" + (
                f", hacim bazlı göstergeler ise {AKIS_IFADE.get((m.get('akis') or {}).get('ozet'), 'karışık bir görünüme')} işaret ediyor" if m.get("akis") else "") + "."
        else:
            t += (f"; hacim bazlı göstergeler {AKIS_IFADE.get((m.get('akis') or {}).get('ozet'), 'karışık bir görünüme')} işaret ediyor." if m.get("akis") else ".")
        C.append(t)
    if teknik_cumle(m.get("mta")): C.append(teknik_cumle(m.get("mta")))
    C += ileri_cumleler(m, PARA)
    S = _surucular(m); pos = [x for x in sorted(S, key=lambda x: -x[0]) if x[0] > 0]; neg = [x for x in sorted(S, key=lambda x: x[0]) if x[0] < 0]
    son = f"Sonuç olarak genel görünümümüz <b>{kk(et)}</b>."
    if pos and neg: son += f" {bas_buyuk(pos[0][1])} görünümü desteklerken, {neg[0][2]} önümüzdeki dönemde izlenmesi gereken başlıca unsur olarak öne çıkıyor."
    elif pos: son += f" {bas_buyuk(pos[0][1])}" + (f" ve {pos[1][1]}" if len(pos) > 1 else "") + " hisseyi destekleyen başlıca unsurlar."
    elif neg: son += f" {bas_buyuk(neg[0][2])} görünüm üzerinde baskı oluşturuyor."
    C.append(son)
    return " ".join(C)


def yatirim_tezi(m, n=4):
    S = _surucular(m)
    pos = [(x[4], x[3]) for x in sorted(S, key=lambda x: -x[0]) if x[0] > 0][:n]
    neg = [(x[4], x[3]) for x in sorted(S, key=lambda x: x[0]) if x[0] < 0][:n]
    return pos, neg


def senaryolar(m):
    """Olumlu / olumsuz senaryo metinleri."""
    sc = m.get("senaryo") or {}; out = []
    iy, ko = sc.get("İyimser"), sc.get("Kötümser")
    if iy and ko:
        out.append(("Olumlu senaryo", fiyat(iy["deger"]), yuzde(iy["deger"] / m["fiyat"] - 1, 1, True),
                    f"Başlangıç büyümesinin {yuzde(iy['g0'])}, serbest nakit akışı marjının {yuzde(iy['marj'])} ve sermaye maliyetinin {yuzde(iy['wacc'])} "
                    "seviyesinde gerçekleşmesi; operasyonel verimlilik ve talebin beklentilerin üzerinde seyretmesi."))
        out.append(("Olumsuz senaryo", fiyat(ko["deger"]), yuzde(ko["deger"] / m["fiyat"] - 1, 1, True),
                    f"Büyümenin {yuzde(ko['g0'])} seviyesine gerilemesi, marjın {yuzde(ko['marj'])} düzeyinde kalması ve sermaye maliyetinin "
                    f"{yuzde(ko['wacc'])} seviyesine yükselmesi; maliyet baskılarının ve finansman giderlerinin artması."))
    elif m.get("adil_yuksek") and m.get("adil_dusuk"):
        out.append(("Olumlu senaryo", fiyat(m["adil_yuksek"]), yuzde(m["adil_yuksek"] / m["fiyat"] - 1, 1, True),
                    "Değerleme yöntemlerinin üst bandı: kârlılığın sürdürülmesi ve çarpanların emsal ortalamalarına yakınsaması."))
        out.append(("Olumsuz senaryo", fiyat(m["adil_dusuk"]), yuzde(m["adil_dusuk"] / m["fiyat"] - 1, 1, True),
                    "Değerleme yöntemlerinin alt bandı: kârlılıkta gerileme ve risk primlerinin yükselmesi."))
    return out


def katalizorler(m):
    import bist_rapor as br
    K = []; g_, _ = sektor_adi(m)
    sd = (m.get("veri") or {}).get("son_donem")
    if m.get("bilanco_sonraki") is not None:
        K.append(f"{m['bilanco_sonraki']:%d.%m.%Y} tarihinde beklenen finansal sonuç açıklaması")
        sd = None
    if sd is not None:
        nd = (pd.Timestamp(sd) + pd.offsets.QuarterEnd(1))
        ek = 70 if nd.month in (6, 12) else 60
        K.append(f"{nd:%Y}/{nd.month:02d} dönemi finansal sonuçları (yasal son açıklama tarihi yaklaşık {nd + pd.Timedelta(days=ek):%d.%m.%Y})")
    if m.get("temettu_verim"): K.append("genel kurul dönemindeki temettü dağıtım kararı")
    if g_ in SEKTOR_NOT: K += SEKTOR_NOT[g_][1][:2]
    sv = m.get("seviye") or {}
    if sv.get("direnc"): K.append(f"{fiyat(sv['direnc'][0][0])} direnç seviyesinin hacimli şekilde aşılması")
    if m.get("nav"): K.append("holding iskontosunun daralması")
    return K[:5]


def riskler(m):
    import bist_rapor as br
    R_ = []; g_, _ = sektor_adi(m); enf = br.PARAM["ENFLASYON"]
    if g_ in SEKTOR_NOT: R_ += SEKTOR_NOT[g_][0][:2]
    if m.get("nb_favok") is not None and m["nb_favok"] > 2.5: R_.append("yüksek kaldıraç nedeniyle finansman giderlerinin kârlılığı baskılaması")
    if m.get("roe") is not None and m["roe"] < enf: R_.append("özkaynak kârlılığının enflasyonun altında kalmaya devam etmesi")
    if m.get("ort_islem_tl") is not None and m["ort_islem_tl"] < 20e6: R_.append("düşük işlem hacmi kaynaklı likidite riski")
    if m.get("beta") is not None and m["beta"] > 1.3: R_.append("piyasa ortalamasının üzerinde fiyat oynaklığı")
    if (m.get("veri") or {}).get("eski"): R_.append("mali tablo verilerinin güncelliği")
    if ((m.get("aciga") or {}).get("oran") or 0) > 0.12: R_.append("yoğun açığa satış baskısı")
    if any(x.get("yon", 0) < 0 for x in (m.get("kap") or [])[:5]): R_.append("son KAP gündemindeki olumsuz başlıklar")
    R_.append(GENEL_RISK)
    return list(dict.fromkeys(R_))[:5]


def karne(m):
    """Temel göstergeler karnesi: [(alan, değerlendirme, durum)]"""
    import bist_rapor as br
    enf = br.PARAM["ENFLASYON"]; K = []
    if m.get("potansiyel") is not None:
        pt = m["potansiyel"]
        K.append(("Değerleme", f"Adil değer {fiyat(m['adil'])}; fiyata göre {yuzde(pt, 1, True)}. " +
                  ("Hisse temel değerinin altında fiyatlanıyor." if pt > 0.15 else "Fiyat temel değerin üzerinde; prim taşıyor." if pt < -0.15 else "Fiyat makul değer bandında."),
                  "iyi" if pt > 0.15 else "zayif" if pt < -0.15 else "orta"))
    if m.get("genel_skor"):
        gs = m["genel_skor"]; sr = sorted(m["saglik"].items(), key=lambda x: x[1])
        K.append(("Finansal sağlık", f"Skor {_n(gs, 2)}/5 ({kk(m['skor_etiket'])}); güçlü alan {kk(sr[-1][0])}, zayıf alan {kk(sr[0][0])}.",
                  "iyi" if gs >= 3.25 else "orta" if gs >= 2.5 else "zayif"))
    if m.get("roe") is not None:
        f = m["roe"] - enf
        K.append(("Kârlılık", f"Özkaynak kârlılığı {yuzde(m['roe'])}, enflasyon {yuzde(enf)}" + (f"; net kâr marjı {yuzde(m['net_marj'])}." if m.get("net_marj") is not None else "."),
                  "iyi" if f > 0.05 else "orta" if f > -0.05 else "zayif"))
    rb = br.reel(m.get("ciro_b"))
    if rb is not None:
        K.append(("Büyüme", f"Hasılat nominal {yuzde(m['ciro_b'], 1, True)}, reel {yuzde(rb, 1, True)}" +
                  (f"; son çeyrek net kâr yıllık {yuzde(m['ceyrek_net_b'], 1, True)}." if m.get("ceyrek_net_b") is not None else "."),
                  "iyi" if rb > 0.05 else "orta" if rb > -0.05 else "zayif"))
    if m.get("banka"):
        ov = (m["banka"] or {}).get("ozk_varlik")
        if ov is not None: K.append(("Sermaye yeterliliği", f"Özkaynak/aktif {yuzde(ov)}.", "iyi" if ov > 0.1 else "orta" if ov > 0.07 else "zayif"))
    elif m.get("net_borc") is not None:
        if m["net_borc"] < 0: K.append(("Bilanço", f"{tutar(-m['net_borc'])} net nakit; borç riski düşük.", "iyi"))
        elif m.get("nb_favok") is not None:
            x = m["nb_favok"]; K.append(("Bilanço", f"Net borç/FAVÖK {kat(x)}" + (f", cari oran {kat(m['cari'])}." if m.get("cari") else "."), "iyi" if x < 1.5 else "orta" if x < 3 else "zayif"))
    if m.get("sna_verim") is not None and not m.get("finansal"):
        K.append(("Nakit üretimi", f"Serbest nakit akışı verimi {yuzde(m['sna_verim'])}" + (f"; nakit/kâr dönüşümü {kat(m['na_kalite'])}." if m.get("na_kalite") is not None else "."),
                  "iyi" if m["sna_verim"] > 0.05 else "orta" if m["sna_verim"] >= 0 else "zayif"))
    if m.get("ma200"):
        ust = m["fiyat"] > m["ma200"]
        K.append(("Trend", f"Fiyat 200 günlük ortalamanın {'üzerinde' if ust else 'altında'}; teknik göstergeler {TEKNIK_IFADE.get(m['teknik_ozet'], kk(m['teknik_ozet']))}, RSI {_n(m['rsi'], 0)}.",
                  "iyi" if ust and "NEGATİF" not in m["teknik_ozet"] else "zayif" if not ust and "POZİTİF" not in m["teknik_ozet"] else "orta"))
    tkr = teknik_karne(m.get("mta"))
    if tkr: K.append(tkr)
    a = m.get("akis")
    if a:
        K.append(("Para akışı", f"Hacim göstergeleri {AKIS_IFADE.get(a['ozet'], 'karışık bir görünüme')} işaret ediyor" + (f"; yabancı payı {yuzde(m['yabanci']['oran'] / 100)}." if m.get("yabanci") else "."),
                  "iyi" if a["puan"] > 0 else "zayif" if a["puan"] < 0 else "orta"))
    tv = m.get("temettu_verim")
    K.append(("Temettü", f"Son 12 aylık verim {yuzde(tv)}." if tv else "Son 12 ayda nakit temettü dağıtılmadı.", "iyi" if tv and tv > 0.04 else "orta" if tv else "yok"))
    return K


def bolum_girisi(m, bolum):
    """Her bölümün başındaki kısa analist yorumu."""
    import bist_rapor as br
    if bolum == "degerleme" and m.get("adil"):
        dahil = sorted([y for y in m["yontemler"] if y[6]], key=lambda y: -y[4])
        t = f"Birleşik adil değerimiz <b>{fiyat(m['adil'])}</b> ({yuzde(m['potansiyel'], 1, True)}). "
        if dahil:
            t += f"En yüksek ağırlığı taşıyan {dahil[0][0]} yöntemi {fiyat(dahil[0][1])} seviyesine işaret ediyor"
            if len(dahil) > 1:
                lo, hi = min(dahil, key=lambda y: y[1]), max(dahil, key=lambda y: y[1])
                t += f"; sonuçlar {fiyat(lo[1])} ({lo[0]}) ile {fiyat(hi[1])} ({hi[0]}) arasında dağılıyor"
            t += ". "
        if m.get("sinirlandi"): t += "Uç model sonuçları nedeniyle potansiyel temkinli üst sınırla sınırlandırıldı. "
        return t + "Aralığın genişliği tahmin belirsizliğinin bir ölçüsüdür."
    if bolum == "saglik" and m.get("saglik"):
        sr = sorted(m["saglik"].items(), key=lambda x: x[1])
        return (f"Finansal sağlık skoru <b>{_n(m['genel_skor'], 2)}/5</b> ile '{kk(m['skor_etiket'])}' seviyesinde. "
                f"{sr[-1][0]} ({_n(sr[-1][1], 1)}) skoru destekleyen başlıca alan iken, {kk(sr[0][0])} ({_n(sr[0][1], 1)}) iyileşme gerektiren alan olarak öne çıkıyor. "
                "Puanlar 1 (zayıf) ile 5 (güçlü) arasındadır; büyüme metrikleri enflasyondan arındırılmıştır.")
    if bolum == "tablolar":
        T = m["T"]; t = f"Son 12 aylık hasılat <b>{tutar(T['ciro'])}</b>, net kâr <b>{tutar(T['net'])}</b>"
        mar = [f"FAVÖK marjı {yuzde(m['favok_marj'])}" if m.get("favok_marj") is not None and not m.get("finansal") else "",
               f"net kâr marjı {yuzde(m['net_marj'])}" if m.get("net_marj") is not None else ""]
        mar = [x for x in mar if x]
        t += (" (" + ", ".join(mar) + ")" if mar else "") + ". "
        if m.get("ciro_b") is not None: t += f"Hasılat yıllık nominal {yuzde(m['ciro_b'], 1, True)}, reel {yuzde(br.reel(m['ciro_b']), 1, True)} değişti."
        return t
    if bolum == "emsal":
        es = (m.get("emsal_stat") or {}).get("fk")
        if es and m.get("fk"):
            r_ = m["fk"] / es["med"] - 1
            return (f"Emsal grubunun medyan F/K çarpanı {kat(es['med'])}; {m['kod']} {kat(m['fk'])} ile medyana göre <b>{yuzde(abs(r_), 0)} "
                    f"{'iskontolu' if r_ < 0 else 'primli'}</b> işlem görüyor. Çarpan farkı, kârlılık ve büyüme farklarıyla birlikte değerlendirilmelidir.")
        return "Şirket benzer ölçek ve faaliyet alanındaki emsalleriyle temel çarpanlar üzerinden karşılaştırılmıştır."
    if bolum == "fiyat":
        sv = m.get("seviye") or {}; r1, e1 = m["r"].get("1Y"), m["r_endeks"].get("1Y")
        t = (f"Hisse son 12 ayda {yuzde(r1, 1, True)} getiri sağladı" + (f"; aynı dönemde {EN()} {yuzde(e1, 1, True)}" if e1 is not None else "") + ". ") if r1 is not None else ""
        if sv.get("destek") and sv.get("direnc"):
            t += f"Fiyat <b>{fiyat(sv['destek'][0][0])}</b> destek ve <b>{fiyat(sv['direnc'][0][0])}</b> direnç bandında hareket ediyor."
        return t
    if bolum == "akis":
        a = m.get("akis") or {}
        return ("Hacim ağırlıklı göstergeler (CMF, MFI, OBV) son dönemde <b>" + AKIS_IFADE.get(a.get("ozet"), "karışık bir görünüme") + "</b> işaret ediyor. "
                + (f"Yabancı yatırımcıların payı {yuzde(m['yabanci']['oran'] / 100)}." if m.get("yabanci") else "")
                + " Takas (AKD) verisi lisanslı olduğundan analiz hacim bazlı göstergelere dayanır.")
    if bolum == "temettu":
        return (f"Son 12 ayda hisse başına {fiyat(m['dps_ttm'])} temettü dağıtıldı; bu, mevcut fiyata göre {yuzde(m['temettu_verim'])} verim anlamına geliyor."
                if m.get("dps_ttm") else "Şirket son 12 ayda nakit temettü dağıtmadı.")
    return ""


# ================================================================ EMTİA / KRİPTO
VARLIK_NOT = {
    "kripto": (["düzenleyici gelişmeler ve borsa kaynaklı riskler", "kaldıraçlı pozisyonların tasfiyesiyle ani fiyat düşüşleri",
                "küresel likidite koşullarındaki sıkılaşma"],
               ["ABD Merkez Bankası faiz kararları ve enflasyon verileri", "spot kripto ETF fon akımları", "kurumsal benimseme ve düzenleyici netlik"]),
    "altin": (["reel faizlerin yükselmesi", "ABD dolarının güçlenmesi", "jeopolitik risklerin azalmasıyla güvenli liman talebinin gerilemesi"],
              ["merkez bankalarının altın alımları", "ABD faiz indirimleri", "jeopolitik gerginlikler"]),
    "enerji": (["OPEC+ üretim politikasındaki değişiklikler", "küresel büyümede yavaşlama ve talep kaybı", "stok artışları"],
               ["OPEC+ toplantı kararları", "ABD haftalık stok verileri", "jeopolitik arz riskleri"]),
    "metal": (["Çin talebindeki yavaşlama", "küresel sanayi üretiminde gerileme", "ABD dolarının güçlenmesi"],
              ["Çin teşvik paketleri", "enerji dönüşümü kaynaklı talep", "arz kesintileri"]),
    "tarim": (["hava koşulları ve hasat beklentileri", "küresel stok seviyeleri", "ticaret politikaları"],
              ["USDA arz-talep raporları", "hasat dönemi verileri", "hava olayları"]),
}
GRUP = {"ALTIN": "altin", "GRAMALTIN": "altin", "GUMUS": "altin", "PLATIN": "metal", "PALADYUM": "metal", "BAKIR": "metal",
        "BRENT": "enerji", "WTI": "enerji", "DOGALGAZ": "enerji"}


def varlik_grup(m):
    return "kripto" if m["tur"] == "kripto" else GRUP.get(m["kod"], "tarim")


def varlik_surucular(m):
    S = []; dg = m.get("deger") or {}; cg = m.get("cg") or {}; kr = m["tur"] == "kripto"
    if dg.get("pot") is not None:
        p = dg["pot"]; b = dg.get("bant", 0.25); v = 2 if p > 2 * b else 1 if p > b else -2 if p < -2 * b else -1 if p < -b else 0
        S.append((v, "uzun vadeli değer bantlarının altında fiyatlama", "değer bantlarının üzerinde aşırı fiyatlama",
                  f"Uzun vadeli bant modelleri {fiyat(dg['adil'], '$' if m['para'] == 'USD' else 'TL')} seviyesine işaret ediyor; fiyata göre {yuzde(p, 1, True)}.", "Değerleme bandı"))
    if m.get("ma200"):
        ust = m["fiyat"] > m["ma200"]; S.append((1 if ust else -1, "yukarı yönlü ana trend", "aşağı yönlü ana trend",
                  f"Fiyat 200 günlük ortalamanın {yuzde(abs(m['fiyat'] / m['ma200'] - 1), 1)} {'üzerinde' if ust else 'altında'}.", "Trend"))
    r3 = m["r_usd"].get("3A")
    if r3 is not None:
        v = 1 if r3 > 0.1 else -1 if r3 < -0.1 else 0
        S.append((v, "güçlü orta vadeli momentum", "zayıf orta vadeli momentum", f"Son 3 ayda dolar bazında {yuzde(r3, 1, True)}; RSI {_n(m['rsi'], 0)}.", "Momentum"))
    if m.get("sharpe") is not None:
        v = 1 if m["sharpe"] > 1 else -1 if m["sharpe"] < 0 else 0
        S.append((v, "risk başına güçlü getiri", "risk başına negatif getiri", f"1 yıllık Sharpe oranı {_n(m['sharpe'], 2)}, yıllık volatilite {yuzde(m['vol'], 0)}.", "Risk/getiri"))
    if kr and cg.get("piy_deg") and cg.get("fdv"):
        o = cg["piy_deg"] / cg["fdv"]; v = 1 if o > 0.9 else -1 if o < 0.6 else 0
        S.append((v, "sınırlı arz seyrelmesi", "yüksek arz seyrelme riski", f"Dolaşımdaki arz tam seyreltilmiş değerin {yuzde(o, 0)} kadarını oluşturuyor.", "Arz yapısı"))
    tv = m.get("turev") or {}
    if tv.get("yillik") is not None:
        f = tv["yillik"]; v = -1 if f > 0.3 else 1 if f < 0 else 0
        S.append((v, "kaldıraçta temkinli konumlanma", "kalabalık kaldıraçlı uzun pozisyonlar", f"Vadeli fonlama oranı yıllık {yuzde(f)}.", "Türev piyasalar"))
    ko = m.get("korku") or {}
    if ko.get("deger") is not None:
        d = ko["deger"]; v = 1 if d <= 25 else -1 if d >= 75 else 0
        S.append((v, "aşırı korku kaynaklı ters yönlü fırsat", "aşırı iyimserlik", f"Korku & Açgözlülük Endeksi {d}.", "Duyarlılık"))
    a = m.get("akis") or {}
    if a:
        v = 1 if a.get("puan", 0) > 0 else -1 if a.get("puan", 0) < 0 else 0
        S.append((v, "hacimle desteklenen alım", "hacim bazlı satış baskısı", f"Hacim göstergeleri {AKIS_IFADE.get(a.get('ozet'), 'karışık bir görünüme')} işaret ediyor.", "Para akışı"))
    ts_ = teknik_surucu(m.get("mta"))
    if ts_: S.append(ts_)
    if m.get("r_reel") is not None:
        v = 1 if m["r_reel"] > 0.05 else -1 if m["r_reel"] < -0.05 else 0
        S.append((v, "TL bazında enflasyon üzerinde getiri", "TL bazında reel kayıp", f"TL bazında 1 yıllık reel getiri {yuzde(m['r_reel'], 1, True)}.", "Reel getiri"))
    return S


def varlik_gorus(m):
    s_ = m.get("genel_skor") or 2.75; dg = (m.get("deger") or {}).get("pot") or 0
    s = 0.7 * max(min((s_ - 2.75) / 1.25, 1), -1) + 0.3 * max(min(dg / 0.5, 1), -1)
    if (m.get("mta") or {}).get("puan") is not None:
        s = 0.8 * s + 0.2 * max(min((m["mta"]["puan"] - 50) / 35, 1), -1)
    return ("OLUMLU" if s > 0.35 else "ILIMLI OLUMLU" if s > 0.12 else "OLUMSUZ" if s < -0.35 else "TEMKİNLİ" if s < -0.12 else "NÖTR"), s


def varlik_baslik(m):
    S = varlik_surucular(m)
    pos = [x[1] for x in sorted([x for x in S if x[0] > 0], key=lambda x: -x[0])]
    neg = [x[2] for x in sorted([x for x in S if x[0] < 0], key=lambda x: x[0])]
    et, s = varlik_gorus(m)
    if s >= 0 and pos: return bas_buyuk(pos[0]) + (f" ve {pos[1]}" if len(pos) > 1 else "") + (f"; {neg[0]} izlenmeli" if neg else "")
    if neg: return bas_buyuk(neg[0]) + (f" ve {neg[1]}" if len(neg) > 1 else "") + " baskı unsuru" + (f"; {pos[0]} destekleyici" if pos else "")
    return "Dengeli görünüm; belirgin bir yön sinyali yok"


def varlik_ozeti(m, kisa=False):
    sym = "$" if m["para"] == "USD" else "TL"; cg = m.get("cg") or {}; dg = m.get("deger") or {}; et, _ = varlik_gorus(m); C = []
    t = f"{m['ad']} {fiyat(m['fiyat'], sym)} seviyesinde işlem görüyor"
    if cg.get("piy_deg"): t += f"; {tutar(cg['piy_deg'], '$')} piyasa değeriyle kripto piyasasında {cg.get('sira')}. sırada yer alıyor"
    r1 = m["r_usd"].get("1Y")
    if r1 is not None: t += f". Varlık son 12 ayda dolar bazında {yuzde(r1, 1, True)}, TL bazında {yuzde(m['r_tl'].get('1Y'), 1, True)} getiri sağladı"
    C.append(t + ".")
    if dg.get("adil"):
        C.append(f"Uzun vadeli değer bantlarının ({len(dg['yontemler'])} model) birleşik orta noktası <b>{fiyat(dg['adil'], sym)}</b>; fiyat bu seviyeye göre "
                 f"<b>{yuzde(dg['pot'], 1, True)}</b> farkla {kk(dg['etiket'])}.")
    if kisa:
        if teknik_cumle(m.get("mta"), kisa=True): C.append(teknik_cumle(m.get("mta"), kisa=True))
        C.append(f"Genel görünümümüz <b>{kk(et)}</b>."); return " ".join(C)
    tr = []
    if m.get("ma200"): tr.append(f"fiyat 200 günlük ortalamanın {'üzerinde' if m['fiyat'] > m['ma200'] else 'altında'}")
    tr.append(f"RSI {_n(m['rsi'], 0)}"); tr.append(f"MACD {'pozitif' if m['macd_poz'] else 'negatif'}")
    C.append("Teknik açıdan " + ", ".join(tr) + f"; yıllık volatilite {yuzde(m['vol'], 0)} ve son 3 yıldaki en büyük düşüş {yuzde(m['max_dd'], 0)}.")
    tv = m.get("turev") or {}; ko = m.get("korku") or {}; gl = m.get("global") or {}
    ek = []
    if tv.get("yillik") is not None: ek.append(f"vadeli fonlama oranı yıllık {yuzde(tv['yillik'])}")
    if ko.get("deger") is not None: ek.append(f"Korku & Açgözlülük Endeksi {ko['deger']}")
    if gl.get("btc_dom"): ek.append(f"Bitcoin dominansı {yuzde(gl['btc_dom'])}")
    if ek: C.append("Piyasa yapısında " + ", ".join(ek) + ".")
    if teknik_cumle(m.get("mta")): C.append(teknik_cumle(m.get("mta")))
    C += ileri_cumleler(m, "$" if m.get("para") == "USD" else "TL")
    S = varlik_surucular(m); pos = [x for x in sorted(S, key=lambda x: -x[0]) if x[0] > 0]; neg = [x for x in sorted(S, key=lambda x: x[0]) if x[0] < 0]
    son = f"Sonuç olarak genel görünümümüz <b>{kk(et)}</b>."
    if pos and neg: son += f" {bas_buyuk(pos[0][1])} destekleyici olurken, {neg[0][2]} temel risk unsuru olarak izlenmeli."
    elif pos: son += f" {bas_buyuk(pos[0][1])} görünümü destekleyen başlıca unsur."
    elif neg: son += f" {bas_buyuk(neg[0][2])} görünüm üzerinde baskı oluşturuyor."
    C.append(son)
    return " ".join(C)


def varlik_tezi(m, n=4):
    S = varlik_surucular(m)
    return ([(x[4], x[3]) for x in sorted(S, key=lambda x: -x[0]) if x[0] > 0][:n],
            [(x[4], x[3]) for x in sorted(S, key=lambda x: x[0]) if x[0] < 0][:n])


def varlik_katalizor_risk(m):
    r, k = VARLIK_NOT[varlik_grup(m)]
    sv = m.get("seviye") or {}; sym = "$" if m["para"] == "USD" else "TL"
    k = list(k)
    if sv.get("direnc"): k.append(f"{fiyat(sv['direnc'][0][0], sym)} direncinin hacimli aşılması")
    r = list(r)
    if sv.get("destek"): r.append(f"{fiyat(sv['destek'][0][0], sym)} desteğinin kapanış bazında kırılması")
    return k[:4], r[:4]


# ================================================================ TEKNİK
def teknik_baslik(s):
    g, h = s["tf"].get("G"), s["tf"].get("H")
    a = h or g
    if not a: return "Yeterli fiyat geçmişi yok"
    ana = {"GÜÇLÜ AL": "Güçlü yükseliş eğilimi", "AL": "Olumlu teknik görünüm", "NÖTR": "Yön arayışı", "SAT": "Zayıf teknik görünüm",
           "GÜÇLÜ SAT": "Belirgin düşüş eğilimi"}[s["etiket"]]
    oz = sorted([x for x in (g or a)["sinyal"] if x[1] != 0 and x[3] >= 2], key=lambda x: -x[3])
    if oz: ana += "; " + ilk_kucuk(oz[0][0].split(": ", 1)[-1].split(" – ")[0]) + " öne çıkıyor"
    return ana


def teknik_ozet(s):
    import bist_teknik as T
    g = s["tf"].get("G"); h = s["tf"].get("H"); a_ = s["tf"].get("A"); para = {"₺": "TL", "$": "$"}.get(s["para"], ""); C = []
    if not g: return "Teknik analiz için yeterli fiyat geçmişi bulunmuyor."
    yapi = kk(g["pa"]["yapi"].split(" (")[0])
    C.append(f"{s['ad']} günlük grafikte {fiyat(g['fiyat'], para)} seviyesinde, {yapi} bir piyasa yapısı içinde işlem görüyor. "
             f"Günlük göstergelerin {g['oy']['sayim']['AL']} tanesi al, {g['oy']['sayim']['SAT']} tanesi sat yönünde sinyal veriyor.")
    t = []
    if h: t.append(f"haftalık zaman diliminde görünüm {kk(h['etiket'])} (puan {h['puan']:.0f})")
    if a_: t.append(f"aylık zaman diliminde {kk(a_['etiket'])} (puan {a_['puan']:.0f})")
    yon = lambda e: 1 if "AL" in e else -1 if "SAT" in e else 0
    if t:
        if h and yon(h["etiket"]) != 0 and yon(h["etiket"]) == yon(g["etiket"]): son = "; kısa vadeli hareket orta vadeli trendle uyumlu."
        elif h and yon(h["etiket"]) == 0: son = "; orta vadede belirgin bir yön oluşmadığından kısa vadeli sinyallerin teyidi önem taşıyor."
        elif h: son = "; kısa ve orta vadeli sinyaller ayrışıyor, bu da trend dönüşü ya da düzeltme ihtimaline işaret ediyor."
        else: son = "."
        C.append(bas_buyuk("; ".join(t)) + son)
    k1, k4 = s["tf"].get("1S"), s["tf"].get("4S")
    if k1 or k4:
        C.append("Gün içi zaman dilimlerinde " + ", ".join(f"{ad_} grafik {kk(x['etiket'])} (puan {x['puan']:.0f})" for ad_, x in (("1 saatlik", k1), ("4 saatlik", k4)) if x)
                 + "; " + _kisa_uyum(s, k1, k4))
    ozel = sorted([x for x in g["sinyal"] if x[1] != 0], key=lambda x: -x[3])[:2]
    if ozel: C.append("Öne çıkan sinyaller: " + "; ".join(ilk_kucuk(x[0].split(": ", 1)[-1]) for x in ozel) + ".")
    sr = g["sr"]; d1 = sr["destek"][0][0] if sr["destek"] else None; r1 = sr["direnc"][0][0] if sr["direnc"] else None
    d2 = sr["destek"][1][0] if len(sr["destek"]) > 1 else None; r2 = sr["direnc"][1][0] if len(sr["direnc"]) > 1 else None
    if r1:
        C.append(f"Yukarıda {fiyat(r1, para)} direncinin hacimli kapanışla aşılması halinde {fiyat(r2, para) if r2 else 'yeni zirveler'} seviyesine doğru hareket alanı açılabilir.")
    if d1:
        C.append(f"Aşağıda {fiyat(d1, para)} desteği kritik; bu seviyenin altında kalıcılık {fiyat(d2, para) if d2 else 'daha derin bir düzeltme'} seviyesini gündeme getirebilir.")
    return " ".join(C)


def _kisa_uyum(s, k1, k4):
    yon = lambda p: 1 if p >= 58 else -1 if p <= 42 else 0
    if k1 and k4 and yon(k1["puan"]) * yon(k4["puan"]) < 0:
        return "gün içi sinyaller karışık; işlem zamanlaması için netleşme beklenmeli."
    kp, gp = s.get("kisa_puan"), s.get("puan")
    if kp is None or gp is None: return "gün içi görünüm izlenmeli."
    if yon(kp) == yon(gp) and yon(kp) != 0: return "kısa vadeli ivme ana görünümü destekliyor."
    if yon(kp) == 0: return "gün içi ivme yön arayışında."
    return "gün içi ivme ana görünümle ayrışıyor; giriş-çıkış zamanlaması için kısa vadeli teyit beklenmeli."


def teknik_senaryo(s):
    g = s["tf"].get("G"); para = {"₺": "TL", "$": "$"}.get(s["para"], "")
    if not g: return []
    sr = g["sr"]; at = float(g["G"]["ATR"].iloc[-1]); c = g["fiyat"]
    r1 = sr["direnc"][0][0] if sr["direnc"] else c + 2 * at; d1 = sr["destek"][0][0] if sr["destek"] else c - 2 * at
    r2 = sr["direnc"][1][0] if len(sr["direnc"]) > 1 else r1 + 2 * at; d2 = sr["destek"][1][0] if len(sr["destek"]) > 1 else d1 - 2 * at
    return [("Yükseliş senaryosu", f"{fiyat(r1, para)} üzerinde günlük kapanış", f"{fiyat(r2, para)}", f"Görünümü bozan seviye: {fiyat(d1, para)}"),
            ("Düşüş senaryosu", f"{fiyat(d1, para)} altında günlük kapanış", f"{fiyat(d2, para)}", f"Görünümü bozan seviye: {fiyat(r1, para)}")]


# ================================================================ BÜLTEN
def bulten_yorumu(baslik, satirlar, endeks=None):
    df = pd.DataFrame(satirlar)
    if df.empty: return ""
    n = len(df); al = int(df["Genel"].isin(["AL", "GÜÇLÜ AL"]).sum()); sat = int(df["Genel"].isin(["SAT", "GÜÇLÜ SAT"]).sum())
    ort = df["Teknik puan"].mean(); C = []
    if endeks and endeks["tf"].get("G"):
        e = endeks["tf"]["G"]
        C.append(f"{endeks['ad']} günü {fiyat(e['fiyat'], '')} seviyesinden {yuzde(e['degisim'], 2, True)} değişimle tamamladı; teknik görünüm günlükte "
                 f"{kk(e['etiket'])}, genel puan {endeks['puan']:.0f}/100.")
    C.append(f"Taranan {n} varlığın {al} tanesi ({yuzde(al / n, 0)}) al, {sat} tanesi ({yuzde(sat / n, 0)}) sat görünümünde; ortalama teknik puan {ort:.0f}. "
             + ("Piyasa genişliği olumlu, yükseliş geniş tabana yayılmış durumda." if al > 1.5 * sat else
                "Piyasa genişliği zayıf, satış baskısı geniş tabanlı." if sat > 1.5 * al else "Piyasa genişliği dengeli; seçici bir görünüm hâkim."))
    k = df[df["Kırılım"]]; kn = df[df["Kırılım −"]]
    if len(k): C.append(f"Gün içinde {len(k)} varlıkta yukarı yönlü formasyon kırılımı ya da yapı kırılımı tespit edildi; öne çıkanlar {', '.join(k.nlargest(4, 'Teknik puan')['Kod'])}.")
    if len(kn): C.append(f"Aşağı yönlü kırılım görülen {len(kn)} varlık arasında {', '.join(kn.nsmallest(3, 'Teknik puan')['Kod'])} dikkat çekiyor.")
    os_ = df[df["RSI"] < 30]; ob = df[df["RSI"] > 70]
    if len(os_) or len(ob): C.append(f"Aşırı satım bölgesinde {len(os_)}, aşırı alım bölgesinde {len(ob)} varlık bulunuyor.")
    return " ".join(C)


KARNE_ETIKET = {"Fiyat bantlara göre ucuz mu, pahalı mı?": "Değerleme bandı", "Ana eğilim ne yönde?": "Ana trend",
                "Son aylarda güç kazanıyor mu?": "Momentum", "Ne kadar riskli?": "Risk profili", "Ortalamasına göre pahalı mı?": "Mayer çarpanı",
                "Alıcılar mı, satıcılar mı baskın?": "Para akışı", "TL bazında enflasyonu yendi mi?": "Reel getiri (TL)",
                "Mevsimsel olarak bu ay nasıl?": "Mevsimsellik", "Yeni arz baskısı var mı?": "Arz yapısı",
                "Kaldıraçlı işlemciler ne yapıyor?": "Türev piyasalar", "Piyasada para nereye akıyor?": "Piyasa rotasyonu",
                "Kripto piyasasının havası nasıl?": "Piyasa duyarlılığı"}


def karne_etiketle(liste, t=None):
    out = [(KARNE_ETIKET.get(q, q), c, d) for q, c, d in liste]
    tk = teknik_karne(t)
    if tk: out.insert(2, tk)
    return out


# ================================================================ TEKNİK ENTEGRASYON
def _tf_et(t, k):
    x = (t.get("tf") or {}).get(k)
    return x["etiket"] if x else None


def teknik_cumle(t, kisa=False):
    """Özetlere eklenen çok zaman dilimli teknik analiz cümlesi."""
    if not t or t.get("puan") is None: return ""
    g, h, a_ = _tf_et(t, "G"), _tf_et(t, "H"), _tf_et(t, "A")
    parca = [f"{ad_} {kk(e)}" for ad_, e in (("günlükte", g), ("haftalıkta", h), ("aylıkta", a_)) if e]
    if kisa:
        return f"Teknik görünüm {', '.join(parca)} (teknik puan {t['puan']:.0f}/100)."
    s = f"Çok zaman dilimli teknik analizimiz {', '.join(parca)} görünüme işaret ediyor; birleşik teknik puan {t['puan']:.0f}/100."
    gg = (t.get("tf") or {}).get("G") or (t.get("tf") or {}).get("H")
    if gg:
        oz = sorted([x for x in gg["sinyal"] if x[1] != 0 and x[3] >= 2], key=lambda x: -x[3])[:2]
        if oz: s += " Öne çıkan teknik sinyaller: " + "; ".join(ilk_kucuk(x[0].split(": ", 1)[-1]) for x in oz) + "."
        para = {"₺": "TL", "$": "$"}.get(t.get("para"), "")
        sr = gg["sr"]
        if sr["destek"] and sr["direnc"]:
            s += f" Günlük grafikte {fiyat(sr['destek'][0][0], para)} destek, {fiyat(sr['direnc'][0][0], para)} direnç seviyesi izlenmeli."
    return s


def teknik_karne(t):
    if not t or t.get("puan") is None: return None
    g, h, a_ = _tf_et(t, "G"), _tf_et(t, "H"), _tf_et(t, "A")
    p = t["puan"]
    return ("Teknik görünüm", f"Günlük {kk(g or '–')}, haftalık {kk(h or '–')}, aylık {kk(a_ or '–')}; teknik puan {p:.0f}/100.",
            "iyi" if p >= 58 else "zayif" if p <= 42 else "orta")


def teknik_surucu(t):
    if not t or t.get("puan") is None: return None
    p = t["puan"]; v = 2 if p >= 75 else 1 if p >= 58 else -2 if p <= 25 else -1 if p <= 42 else 0
    return (v, "güçlü teknik görünüm" if v == 2 else "olumlu teknik görünüm", "belirgin teknik zayıflık" if v == -2 else "zayıf teknik görünüm",
            teknik_cumle(t, kisa=True), "Teknik analiz")



# ================================================================ İLERİ ANALİZ CÜMLELERİ
def ileri_cumleler(m, para="TL", kisa=False):
    """Yönetici özetine eklenen ileri analiz cümleleri (sinyal geçmişi, olasılık bandı, bilanço, açığa satış, KAP, göreli güç)."""
    import bist_ileri as IL
    C = []; il = m.get("ileri") or {}
    kr = il.get("karne")
    if kr is not None and not kr.empty:
        ak = kr[kr["Aktif"] & (kr["Örnek"] >= 5)]
        if len(ak):
            r = ak.sort_values("Örnek", ascending=False).iloc[0]
            C.append(f"Aktif '{r['Sinyal'].replace('Mum: ', '').replace('Formasyon: ', '')}' sinyali bu varlıkta geçmişte {r['Örnek']} kez görüldü ve "
                     f"20 gün içinde %{r['İsabet (20g)'] * 100:.0f} isabetle ortalama {IL._y(r['20g ort'])} getiri sağladı.")
    fa = il.get("aralik")
    if fa and not kisa:
        u = fa["ufuklar"][1]
        C.append(f"Oynaklığa dayalı modelimize göre 1 aylık %68 olasılık bandı {IL._f(u['68_alt'])}–{IL._f(u['68_ust'])} {para}.")
    if m.get("rs") is not None:
        C.append(f"Göreli güç puanı {m['rs']}/99" + (" ile piyasanın en güçlü hisseleri arasında." if m["rs"] >= 80 else " ile piyasanın zayıf kalan hisseleri arasında." if m["rs"] <= 20 else "."))
    if kisa: return C[:2]
    bt = m.get("bilanco")
    if bt:
        o = bt["ozet"]
        C.append(f"Hisse son {o['adet']} bilanço açıklamasında ilk gün ortalama {IL._y(o['1g_ort'])} tepki verdi"
                 + (f"; bir sonraki açıklama {m['bilanco_sonraki']:%d.%m.%Y} tarihinde bekleniyor." if m.get("bilanco_sonraki") is not None else "."))
    ac = m.get("aciga") or {}
    if ac.get("oran") is not None and ac["oran"] > 0.1:
        C.append(f"Son haftada açığa satışın toplam işlem hacmindeki payı yüzde {ac['oran'] * 100:.0f} ile dikkat çekici seviyede.")
    kp = m.get("kap") or []
    if kp:
        C.append(f"KAP gündeminde son dönemde '{kp[0]['konu'].lower()}' başlığı öne çıkıyor.")
    mk = m.get("mikro") or {}
    if mk.get("defter"):
        d_ = mk["defter"]["bant"][0.02]["denge"]
        if abs(d_) > 0.2: C.append(f"Emir defterinde ±%2 bandında {'alıcı' if d_ > 0 else 'satıcı'} tarafı belirgin şekilde daha derin.")
    vd = m.get("vadeli") or {}
    if vd.get("oi_7g") is not None and abs(vd["oi_7g"]) > 0.08:
        C.append(f"Vadeli açık pozisyon son 7 günde {IL._y(vd['oi_7g'])} değişti.")
    return C
