"""Aşama 13: BTC/ETH opsiyon piyasası — Deribit'in herkese açık API'si (anahtar gerekmez, yalnız okuma).

Hesaplananlar (para birimi başına):
- DVOL: Deribit 30 günlük zımni oynaklık endeksi ("kriptonun VIX'i"); 1 yıllık yüzdelik dilimi ve 1 haftalık değişim.
- Gerçekleşen oynaklık (30 gün, günlük kapanışlardan) ve oynaklık primi (DVOL − gerçekleşen).
- Vade yapısı: her vadenin ATM zımni oynaklığı; yakın vade uzaktan pahalıysa ters yapı (stres).
- 25 delta çarpıklığı (~30 günlük vade): put IV − call IV. Pozitif: koruma (put) pahalı, piyasa düşüşe prim ödüyor.
- Put/call oranları: açık pozisyon (OI) ve 24 saatlik hacim.
- Max pain: vade sonunda opsiyon alıcılarına en az ödemeyi yaptıran kullanım fiyatı (yakın büyük vadeler için).
- OI duvarları: en çok açık pozisyonlu call (direnç) ve put (destek) kullanım fiyatları.
- Beklenen hareket: ATM IV × √(gün/365) × fiyat (≈ 1 standart sapma, %68 olasılık bandı).
- ATM greeks (Black-Scholes, faiz 0): delta, gamma, vega, theta.
Kullanım: python opsiyon.py <cikti_klasoru> → opsiyon/ozet.json (+ Cuma vade günü / DVOL sıçramasında Telegram kartı)
Yatırım tavsiyesi değildir; opsiyon verisi beklentileri gösterir, yönü garanti etmez.
"""
import os, sys, json, math, datetime as dt
import numpy as np

API = "https://www.deribit.com/api/v2/public/"
AY = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}


def _al(yol, **p):
    import requests
    r = requests.get(API + yol, params=p, timeout=30, headers={"User-Agent": "KATKAY-arastirma"})
    r.raise_for_status()
    return r.json()["result"]


def vade_coz(s):
    """'27DEC26' → datetime (08:00 UTC, Deribit vade saati)."""
    g = int(s[:-5]); a = AY[s[-5:-2]]; y = 2000 + int(s[-2:])
    return dt.datetime(y, a, g, 8, 0, tzinfo=dt.timezone.utc)


def enstrumanlar(cur):
    """book summary → [{vade, strike, tip C/P, iv (ondalık), oi (coin), hacim (coin), alt (dayanak), mark (coin)}]"""
    out = []
    for x in _al("get_book_summary_by_currency", currency=cur, kind="option"):
        try:
            _, v, k, t = x["instrument_name"].split("-")
            out.append({"vade": vade_coz(v), "vade_ad": v, "strike": float(k), "tip": t, "iv": (x.get("mark_iv") or 0) / 100,
                        "oi": float(x.get("open_interest") or 0), "hacim": float(x.get("volume") or 0),
                        "alt": float(x.get("underlying_price") or 0), "mark": float(x.get("mark_price") or 0)})
        except Exception:
            pass
    return out


# ------------------------------------------------------------------ Black-Scholes (faiz 0, dayanak = vadeli fiyat)
def _N(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))
def _n(x): return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def bs(F, K, T, s, tip="C"):
    """→ (delta, gamma, vega (1 IV puanı için), theta (günlük)) — fiyat birimi dayanak cinsinden."""
    if T <= 0 or s <= 0: return (1.0 if (tip == "C" and F > K) else 0.0, 0.0, 0.0, 0.0)
    d1 = (math.log(F / K) + 0.5 * s * s * T) / (s * math.sqrt(T)); d2 = d1 - s * math.sqrt(T)
    delta = _N(d1) if tip == "C" else _N(d1) - 1
    gamma = _n(d1) / (F * s * math.sqrt(T)); vega = F * _n(d1) * math.sqrt(T) / 100
    theta = -(F * _n(d1) * s) / (2 * math.sqrt(T)) / 365
    return delta, gamma, vega, theta


def max_pain(liste):
    """Vade sonunda tüm opsiyonların içsel değeri toplamını en aza indiren kullanım fiyatı."""
    K = sorted({x["strike"] for x in liste})
    if not K: return None
    C = [(x["strike"], x["oi"]) for x in liste if x["tip"] == "C"]; P = [(x["strike"], x["oi"]) for x in liste if x["tip"] == "P"]
    def odeme(s): return sum(max(0, s - k) * o for k, o in C) + sum(max(0, k - s) * o for k, o in P)
    return min(K, key=odeme)


def vade_ozeti(liste, simdi):
    v = liste[0]["vade"]; T = max((v - simdi).total_seconds() / (365 * 86400), 1e-6)
    F = float(np.median([x["alt"] for x in liste if x["alt"] > 0]))
    atm = sorted(liste, key=lambda x: abs(x["strike"] - F))
    ivs = [x["iv"] for x in atm[:4] if x["iv"] > 0]
    iv = float(np.mean(ivs)) if ivs else None
    oi_c = sum(x["oi"] for x in liste if x["tip"] == "C"); oi_p = sum(x["oi"] for x in liste if x["tip"] == "P")
    duvar = lambda t, kosul: max((x for x in liste if x["tip"] == t and kosul(x["strike"])), key=lambda x: x["oi"], default=None)
    dc, dp = duvar("C", lambda k: k > F), duvar("P", lambda k: k < F)
    hareket = iv * math.sqrt(T) if iv else None
    return {"vade": v.isoformat(), "vade_ad": liste[0]["vade_ad"], "gun": round(T * 365, 2), "vadeli": F, "atm_iv": iv,
            "oi": oi_c + oi_p, "pc_oi": (oi_p / oi_c) if oi_c else None, "max_pain": max_pain(liste),
            "call_duvari": dc["strike"] if dc else None, "call_duvari_oi": dc["oi"] if dc else None,
            "put_duvari": dp["strike"] if dp else None, "put_duvari_oi": dp["oi"] if dp else None,
            "beklenen_hareket": hareket, "aralik": [F * (1 - hareket), F * (1 + hareket)] if hareket else None}


def carpiklik(liste, F, T):
    """25 delta risk dönüşü: put(25Δ) IV − call(25Δ) IV (puan)."""
    c = [(abs(bs(F, x["strike"], T, x["iv"], "C")[0] - 0.25), x["iv"]) for x in liste if x["tip"] == "C" and x["iv"] > 0 and x["strike"] > F]
    p = [(abs(abs(bs(F, x["strike"], T, x["iv"], "P")[0]) - 0.25), x["iv"]) for x in liste if x["tip"] == "P" and x["iv"] > 0 and x["strike"] < F]
    if not c or not p: return None
    return (min(p)[1] - min(c)[1]) * 100


def gerceklesen(cur, gun=30):
    try:
        import requests
        r = requests.get("https://data-api.binance.vision/api/v3/klines", params={"symbol": f"{cur}USDT", "interval": "1d", "limit": gun + 1}, timeout=20)
        c = np.array([float(k[4]) for k in r.json()])
        return float(np.std(np.diff(np.log(c)), ddof=1) * math.sqrt(365))
    except Exception:
        return None


def dvol(cur):
    son = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000); bas = son - 400 * 86400 * 1000
    d = _al("get_volatility_index_data", currency=cur, start_timestamp=bas, end_timestamp=son, resolution="1D")["data"]
    k = [float(x[4]) for x in d]   # [zaman, açılış, yüksek, düşük, kapanış]
    if not k: return None
    yil = k[-365:]
    return {"deger": k[-1], "hafta_once": k[-8] if len(k) > 8 else None, "yuzdelik": float(np.mean(np.array(yil) <= k[-1])),
            "yil_min": min(yil), "yil_max": max(yil), "seri": [round(v, 2) for v in k[-120:]]}


def para_ozeti(cur):
    simdi = dt.datetime.now(dt.timezone.utc)
    E = [x for x in enstrumanlar(cur) if x["vade"] > simdi]
    vadeler = {}
    for x in E: vadeler.setdefault(x["vade"], []).append(x)
    V = [vade_ozeti(vadeler[v], simdi) for v in sorted(vadeler)]
    endeks = float(_al("get_index_price", index_name=f"{cur.lower()}_usd")["index_price"])
    # büyük vadeler: OI'si toplamın %5'inden büyük ilk 4 vade (haftalıkların çoğu küçük kalır)
    top = sum(v["oi"] for v in V) or 1
    buyuk = [v for v in V if v["oi"] / top >= 0.05][:4]
    # ~30 günlük vade: çarpıklık ve greeks
    v30 = min(sorted(vadeler), key=lambda v: abs((v - simdi).days - 30))
    L30 = vadeler[v30]; T30 = (v30 - simdi).total_seconds() / (365 * 86400); F30 = float(np.median([x["alt"] for x in L30]))
    sk = carpiklik(L30, F30, T30)
    o30 = vade_ozeti(L30, simdi)
    g = bs(F30, min({x["strike"] for x in L30}, key=lambda k: abs(k - F30)), T30, o30["atm_iv"] or 0.5, "C") if o30["atm_iv"] else None
    oi_c = sum(x["oi"] for x in E if x["tip"] == "C"); oi_p = sum(x["oi"] for x in E if x["tip"] == "P")
    h_c = sum(x["hacim"] for x in E if x["tip"] == "C"); h_p = sum(x["hacim"] for x in E if x["tip"] == "P")
    try: dv = dvol(cur)
    except Exception as ex: print("DVOL:", ex); dv = None
    rv = gerceklesen(cur)
    yakin, uzak = (V[0]["atm_iv"] if V else None), next((v["atm_iv"] for v in V if v["gun"] >= 80 and v["atm_iv"]), None)
    o = {"para": cur, "endeks": endeks, "zaman": simdi.isoformat(timespec="seconds"), "dvol": dv, "gerceklesen_30g": rv,
         "oynaklik_primi": (dv["deger"] / 100 - rv) if dv and rv else None,
         "vade_yapisi": [{"vade_ad": v["vade_ad"], "gun": v["gun"], "atm_iv": v["atm_iv"]} for v in V if v["atm_iv"]],
         "ters_yapi": bool(yakin and uzak and yakin > uzak * 1.05), "skew_25d": sk, "skew_vade": o30["vade_ad"],
         "pc_oi": (oi_p / oi_c) if oi_c else None, "pc_hacim": (h_p / h_c) if h_c else None,
         "oi_toplam": oi_c + oi_p, "oi_usd": (oi_c + oi_p) * endeks,
         "buyuk_vadeler": buyuk, "yakin_vade": V[0] if V else None, "ay_vade": o30,
         "greeks_atm_30g": {"delta": g[0], "gamma": g[1], "vega": g[2], "theta": g[3], "strike": min({x["strike"] for x in L30}, key=lambda k: abs(k - F30))} if g else None}
    o["yorum"] = yorumla(o)
    return o


def _y(x, nd=1):
    return f"%{x * 100:.{nd}f}".replace(".", ",") if x is not None else "–"


def yorumla(o):
    m = []
    dv = o.get("dvol")
    if dv:
        dil = dv["yuzdelik"]
        m.append(f"DVOL {dv['deger']:.0f}: son 1 yılın %{dil * 100:.0f}'lik diliminde — opsiyonlar "
                 + ("pahalı (piyasa büyük hareket bekliyor)." if dil >= 0.8 else "ucuz (sakin beklenti; ani hareket riski fiyatlanmamış olabilir)." if dil <= 0.2 else "normal fiyatlı."))
    if o.get("oynaklik_primi") is not None:
        p = o["oynaklik_primi"]
        m.append(f"Zımni oynaklık gerçekleşenden {abs(p) * 100:.0f} puan {'yüksek: piyasa geçmişten fazla hareket fiyatlıyor' if p > 0 else 'düşük: opsiyonlar geçmiş harekete göre ucuz'}.")
    if o.get("skew_25d") is not None:
        s = o["skew_25d"]
        m.append(f"25Δ çarpıklık {s:+.1f} puan ({o['skew_vade']}): ".replace(".", ",", 1)
                 + ("put'lar pahalı — düşüşe karşı korunma talebi güçlü." if s > 2 else "call'lar pahalı — yükseliş için prim ödeniyor." if s < -2 else "dengeli."))
    if o.get("ters_yapi"): m.append("Vade yapısı ters: yakın vade oynaklığı uzaktan yüksek — kısa vadeli stres işareti.")
    if o.get("pc_oi") is not None: m.append(f"Put/call (açık pozisyon) {o['pc_oi']:.2f}".replace(".", ",") + (" — korunma ağırlıklı." if o["pc_oi"] > 0.8 else " — call ağırlıklı (iyimser konumlanma)." if o["pc_oi"] < 0.5 else "."))
    return m


def hesapla(klasor=None, paralar=("BTC", "ETH")):
    o = {"zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "kaynak": "Deribit herkese açık API", "paralar": {}}
    for c in paralar:
        try: o["paralar"][c] = para_ozeti(c)
        except Exception as ex: print("opsiyon", c, ex)
    if klasor and o["paralar"]:
        os.makedirs(os.path.join(klasor, "opsiyon"), exist_ok=True)
        json.dump(o, open(os.path.join(klasor, "opsiyon", "ozet.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    return o


def karne_satirlari(p):
    """Teknik analiz karnesi satırları (ad, değer, yorum, yön)."""
    s = []; tl = lambda x: f"{x:,.0f}".replace(",", ".")
    if p.get("dvol"):
        d = p["dvol"]; s.append(("Opsiyon: DVOL (30 gün zımni oynaklık)", f"{d['deger']:.0f} · 1 yılın %{d['yuzdelik'] * 100:.0f}'i",
                                 "Opsiyon piyasasının beklediği yıllık oynaklık; yüksekse büyük hareket bekleniyor.", 0))
    if p.get("skew_25d") is not None:
        k = p["skew_25d"]; s.append(("Opsiyon: 25Δ çarpıklık", f"{k:+.1f} puan".replace(".", ","),
                                      "Pozitif: put'lar pahalı (düşüş korkusu); negatif: call'lar pahalı (yükseliş beklentisi).",
                                      -1 if k > 2 else 1 if k < -2 else 0))
    if p.get("pc_oi") is not None:
        s.append(("Opsiyon: put/call oranı (OI)", f"{p['pc_oi']:.2f}".replace(".", ","), "0,5 altı call ağırlıklı (iyimser), 0,8 üstü korunma ağırlıklı.", 0))
    for v in (p.get("buyuk_vadeler") or [])[:2]:
        if v.get("max_pain"):
            s.append((f"Opsiyon vadesi {v['vade_ad']} ({v['gun']:.0f} gün)", f"max pain {tl(v['max_pain'])}",
                      f"Beklenen hareket ±{_y(v['beklenen_hareket'])} ({tl(v['aralik'][0])}–{tl(v['aralik'][1])}); "
                      f"call duvarı {tl(v['call_duvari'] or 0)}, put duvarı {tl(v['put_duvari'] or 0)}." if v.get("aralik") else "", 0))
    return s


def kart_ciz(o, yol):
    import kart as K
    tl = lambda x: f"{x:,.0f}".replace(",", ".") if x else "–"
    bol = []
    for c, p in o["paralar"].items():
        d = p.get("dvol") or {}
        sat = [{"sol": "DVOL", "sag": f"{d.get('deger', 0):.0f}", "sag_renk": K.C["altin"],
                "alt": f"1 yılın %{d.get('yuzdelik', 0) * 100:.0f}'lik dilimi · gerçekleşen 30g {_y(p.get('gerceklesen_30g'), 0)}"},
               {"sol": "25Δ çarpıklık", "sag": f"{p['skew_25d']:+.1f}".replace(".", ",") if p.get("skew_25d") is not None else "–",
                "sag_renk": K.C["kirmizi"] if (p.get("skew_25d") or 0) > 2 else K.C["yesil"] if (p.get("skew_25d") or 0) < -2 else K.C["soluk"],
                "alt": "pozitif = put'lar pahalı"},
               {"sol": "Put/call (OI)", "sag": f"{p['pc_oi']:.2f}".replace(".", ",") if p.get("pc_oi") else "–", "alt": f"toplam açık pozisyon ≈ ${tl(p.get('oi_usd'))}"}]
        for v in (p.get("buyuk_vadeler") or [])[:2]:
            sat.append({"sol": f"Vade {v['vade_ad']}", "sag": f"MP {tl(v['max_pain'])}", "sag_renk": K.C["altin"],
                        "alt": f"±{_y(v['beklenen_hareket'])} beklenen hareket · call duvarı {tl(v['call_duvari'])} · put duvarı {tl(v['put_duvari'])}"})
        bol.append({"baslik": f"{c} · {tl(p['endeks'])} $", "renk": K.C["altin"], "satirlar": sat})
    K.bildirim_karti(f"KRİPTO OPSİYON PİYASASI  ·  {dt.datetime.now():%d.%m.%Y}", "BTC ve ETH opsiyonları", "Deribit verisi: oynaklık, çarpıklık, vade seviyeleri",
                     bol, yol, vurgu=K.C["altin"], not_="Max pain ve OI duvarları mıknatıs/engel olabilir ama garanti değildir. Yatırım tavsiyesi değildir.")
    return yol


if __name__ == "__main__":
    import tg
    klasor = sys.argv[1] if len(sys.argv) > 1 else "cikti"
    o = hesapla(klasor)
    for c, p in o["paralar"].items():
        print(c, p["endeks"], "DVOL", (p.get("dvol") or {}).get("deger"), "skew", p.get("skew_25d"), "P/C", p.get("pc_oi"), "|", p["yorum"])
    try: eski = json.load(open(os.path.join(tg.KLON, "opsiyon", "ozet.json"), encoding="utf-8"))
    except Exception: eski = {}
    simdi = dt.datetime.now(dt.timezone.utc)
    sicrama = []
    for c, p in o["paralar"].items():
        a, b = (eski.get("paralar", {}).get(c, {}).get("dvol") or {}).get("deger"), (p.get("dvol") or {}).get("deger")
        if a and b and b / a - 1 >= 0.15: sicrama.append(f"{c} DVOL {a:.0f} → {b:.0f}")
    cuma_sabah = simdi.weekday() == 4 and simdi.hour < 8 and not (eski.get("cuma_karti") == str(simdi.date()))
    if cuma_sabah: o["cuma_karti"] = str(simdi.date())
    elif eski.get("cuma_karti"): o["cuma_karti"] = eski["cuma_karti"]
    json.dump(o, open(os.path.join(klasor, "opsiyon", "ozet.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    if cuma_sabah or sicrama:
        try:
            b = tg.Bot("kripto")
            if b.aktif:
                yol = kart_ciz(o, os.path.join(klasor, "opsiyon", "kart.png"))
                ac = "🎯 <b>Kripto opsiyon piyasası</b>" + (" · bugün 11:00 TSİ'de haftalık vade sonu" if cuma_sabah else "") \
                     + (f"\n⚠️ Oynaklık sıçraması: {', '.join(sicrama)}" if sicrama else "")
                b.foto(yol, ac, f"opsiyon:{simdi:%Y-%m-%d-%H}", 72); b.kaydet()
        except Exception as ex:
            print("opsiyon kartı:", ex)
