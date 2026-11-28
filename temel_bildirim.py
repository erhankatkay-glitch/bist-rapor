# -*- coding: utf-8 -*-
"""Telegram sabah temel özeti (sabah özetinin hemen ardından tek kart):
BIST'te değerinin en altındaki 5 hisse (fırsat skoru), yeni halka arzlar (resmi bebekler, en yeni ilk işlem),
kripto temel puanı en yüksekler ve emtiada vadeli eğri / spekülatör konumu aşırılıkları.
Veri: bulten/temel/{bist,bebek,kripto,emtia}.json (temel.yml, 06:40 TSİ). 36 saatten eski dosyalar kullanılmaz."""
import datetime as dt
import json
import os
import sys
import tempfile

import tg

TSI = dt.timezone(dt.timedelta(hours=3))
ESKI_SAAT = 36


def _oku(ad):
    try:
        d = json.load(open(os.path.join(tg.KLON, "temel", f"{ad}.json"), encoding="utf-8"))
        z = dt.datetime.fromisoformat(d["zaman"])
        if (dt.datetime.now(dt.timezone.utc) - z).total_seconds() > ESKI_SAAT * 3600: print("temel eski:", ad, d["zaman"]); return None
        return d
    except Exception as x:
        print("temel okunamadı:", ad, x); return None


def _y(x, nd=0):
    if x is None: return "–"
    return (f"{'+' if x >= 0 else '-'}%{abs(x) * 100:.{nd}f}").replace(".", ",")


def _tarih(s):
    try: return dt.date.fromisoformat(str(s)[:10]).strftime("%d.%m.%Y")
    except Exception: return str(s or "")


def bolumler(C):
    """(kart bölümleri, Telegram metni satırları)"""
    B, M = [], []
    try: D = json.load(open(os.path.join(tg.CIKTI, "temel", "degisim.json"), encoding="utf-8"))   # temel_karne.py (aynı iş akışı)
    except Exception: D = {}
    O = [o for o in D.get("olaylar", []) if o["tur"] != "liste_cikti"]
    EA = {k: t.get("Ad") for k, t in ((_oku("emtia") or {}).get("satirlar") or {}).items()}
    for o in O: o["ad"] = EA.get(o["kod"]) or (o["kod"].split("/")[0] if o["pz"] == "kripto" else o["kod"])
    if O:
        O.sort(key=lambda o: {"cot": 0, "kpuan": 1, "liste": 2}.get(o["tur"], 3))
        B.append({"baslik": "DÜNDEN BUGÜNE DEĞİŞENLER", "renk": C["altin"],
                  "satirlar": [{"sol": o["ad"], "logo": (o["kod"], o["pz"]), "alt": o["metin"],
                                "nokta": C["yesil"] if o["yon"] > 0 else C["kirmizi"] if o["yon"] < 0 else None,
                                "sag": {"liste": "YENİ", "cot": "COT", "kpuan": "PUAN"}.get(o["tur"], ""), "sag_renk": C["yesil"] if o["yon"] > 0 else C["kirmizi"]}
                               for o in O[:6]]})
        M.append("🔔 <b>Değişenler:</b> " + "; ".join(f"{o['ad']} ({o['metin'].split(':')[0].split(' (')[0].lower()})" for o in O[:6]))
    T = _oku("bist")
    if T:
        R = [(k, t) for k, t in T["satirlar"].items() if "ALTINDA" in str(t.get("Görüş") or "") and t.get("Fırsat skoru") is not None
             and not (t.get("F/K") is not None and t["F/K"] < 1)]   # F/K < 1: veri hatası (ör. imtiyazlı pay fiyatı × tüm sermaye)
        R.sort(key=lambda x: -x[1]["Fırsat skoru"])
        if R:
            B.append({"baslik": "BIST · DEĞERİNİN EN ALTINDAKİ 5 HİSSE", "renk": C["yesil"],
                      "satirlar": [{"sol": f"{k} · {t.get('Şirket') or ''}", "sag": f"{t['Fırsat skoru']:.0f} · {_y(t.get('Potansiyel'))}", "sag_renk": C["yesil"],
                                    "logo": (k, "bist"), "alt": f"{t.get('Gerekçe') or ''} · sağlık {str(round(t['Sağlık skoru'], 1)).replace('.', ',') if t.get('Sağlık skoru') is not None else '–'}/5"
                                                                 + (f" · F/K {t['F/K']:.1f}".replace(".", ",") if t.get("F/K") else "")}
                                   for k, t in R[:5]]})
            M.append("📈 <b>Değerinin altında:</b> " + ", ".join(f"{k} ({_y(t.get('Potansiyel'))})" for k, t in R[:5]))
    BB = _oku("bebek")
    if BB:
        md = (BB.get("modlar") or {}).get("resmi") or {}
        derin = {x["Kod"]: x for x in md.get("derin", [])}
        L = sorted([x for x in md.get("liste", []) if x.get("İlk işlem")], key=lambda x: str(x["İlk işlem"]), reverse=True)[:5]
        if L:
            B.append({"baslik": "YENİ HALKA ARZLAR (BIST HALKA ARZ ENDEKSİ)", "renk": C["altin"],
                      "satirlar": [{"sol": f"{x['Kod']} · {x.get('Şirket') or ''}", "logo": (x["Kod"], "bist"),
                                    "sag": _y(x.get("İlk işlemden getiri")) if x.get("İlk işlemden getiri") is not None else "",
                                    "sag_renk": C["yesil"] if (x.get("İlk işlemden getiri") or 0) >= 0 else C["kirmizi"],
                                    "alt": f"İlk işlem {_tarih(x['İlk işlem'])}"
                                           + (f" · bebek skoru {derin[x['Kod']]['Bebek skoru']:.0f}" if derin.get(x["Kod"], {}).get("Bebek skoru") is not None else "")
                                           + (f" · Risk: {derin[x['Kod']]['Risk notu']}" if derin.get(x["Kod"], {}).get("Risk notu") else "")}
                                   for x in L]})
            M.append("🍼 <b>Yeni halka arzlar:</b> " + ", ".join(x["Kod"] for x in L))
    K = _oku("kripto")
    if K:
        R = [(k, t) for k, t in K["satirlar"].items() if t.get("Temel puan") is not None and (t.get("Sıra") or 999) <= 100]
        R.sort(key=lambda x: -x[1]["Temel puan"])
        g = K.get("genel") or {}
        if R:
            ac = None
            if g.get("Korku endeksi") is not None:
                ac = (f"Korku endeksi {g['Korku endeksi']} ({g.get('Korku sınıfı') or ''}) · BTC dominansı %{(g.get('BTC dominansı') or 0) * 100:.1f}").replace(".", ",")
            B.append({"baslik": "KRİPTO · TEMEL PUANI EN YÜKSEKLER (İLK 100)", "renk": C["altin"], "aciklama": ac,
                      "satirlar": [{"sol": f"{k.split('/')[0]} · {t.get('Ad') or ''}", "sag": f"{t['Temel puan']} · {_y(t.get('Potansiyel'))}",
                                    "sag_renk": C["yesil"] if (t.get("Potansiyel") or 0) > 0 else C["soluk"], "logo": (k, "kripto"),
                                    "alt": f"#{t.get('Sıra')} · {t.get('Görünüm') or ''} · dolaşımda %{(t.get('PD / FDV') or 0) * 100:.0f}".replace(".", ",")}
                                   for k, t in R[:3]]})
            M.append("🪙 <b>Kripto:</b> " + ", ".join(k.split("/")[0] for k, _ in R[:3]))
    E = _oku("emtia")
    if E:
        S = []
        for k, t in E["satirlar"].items():
            if k == "GRAMALTIN": continue
            c, v = t.get("COT") or {}, t.get("Vade yapısı") or {}
            if c.get("spek_yuzdelik_3y") is not None and (c["spek_yuzdelik_3y"] >= 0.9 or c["spek_yuzdelik_3y"] <= 0.1):
                S.append((abs(c["spek_yuzdelik_3y"] - 0.5), k, t, ("Spekülatörler 3 yılın en kalabalık alımında: ters haberde sert satış riski" if c["spek_yuzdelik_3y"] >= 0.9
                          else "Spekülatörler 3 yılın en karamsar konumunda: tarihsel dönüş bölgesi"), C["kirmizi"] if c["spek_yuzdelik_3y"] >= 0.9 else C["yesil"],
                          f"COT %{c['spek_yuzdelik_3y'] * 100:.0f}"))
            elif v.get("yapi") == "backwardation" and (v.get("yillik") or 0) < -0.05:
                S.append((0.3, k, t, "Vadeli eğri backwardation: yakın teslim primli, fiziksel talep güçlü", C["yesil"], f"eğri {_y(v['yillik'])}"))
        S.sort(key=lambda x: -x[0])
        if S:
            B.append({"baslik": "EMTİA · DİKKAT ÇEKEN KONUMLAR", "renk": C["altin"],
                      "satirlar": [{"sol": t.get("Ad") or k, "sag": e, "sag_renk": n, "logo": (k, "emtia"), "alt": f"{a} · genel görünüm {(t.get('Görünüm') or '–').lower()}"}
                                   for _, k, t, a, n, e in S[:3]]})
            M.append("🛢️ <b>Emtia:</b> " + ", ".join(E["satirlar"][k].get("Ad") or k for _, k, *_ in S[:3]))
    return B, M


def gonder(b=None):
    """b: sabah özetinin Bot nesnesi (aynı durum dosyası); verilmezse kendi nesnesini açıp kaydeder."""
    import kart as KT
    B, M = bolumler(KT.C)
    if not B: print("Temel özet: veri yok, gönderilmedi."); return False
    t = dt.datetime.now(TSI)
    yol = os.path.join(tempfile.mkdtemp(), "temel_ozet.png")
    KT.bildirim_karti(f"TEMEL ÖZET  ·  {t:%d.%m.%Y}", "Bugün temelde öne çıkanlar", "Gece hesaplanan değerleme, halka arz, kripto ve emtia verileri",
                      B, yol, not_="Değerleme ve skorlar model çıktısıdır, yatırım tavsiyesi değildir. Ayrıntılar ve tüm liste uygulamada: Piyasa › Temel.")
    kendi = b is None
    b = b or tg.Bot("sabah")
    b.sil_anahtar("temel_ozet")
    ok = b.foto(yol, "📊 <b>Temel özet</b> · " + t.strftime("%d.%m.%Y") + "\n" + "\n".join(M), "temel_ozet", 20, dugme=tg.uygulama_dugme("temel", metin="📲 Temel analizi uygulamada aç"))
    if kendi: b.kaydet()
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kart":     # yalnız kart çiz (test)
        import kart as KT
        B, M = bolumler(KT.C)
        KT.bildirim_karti("TEMEL ÖZET  ·  TEST", "Bugün temelde öne çıkanlar", "test", B, sys.argv[2] if len(sys.argv) > 2 else "temel_ozet.png")
        print("\n".join(M))
    else:
        gonder()
