"""Aşama 11: korelasyon ve göreceli güç modülü (ücretsiz Yahoo verisi; sabah özeti iş akışında çalışır).

- Ana çiftlerin günlük getiri korelasyonu: 20, 60 ve 250 günlük. 20 günlük, 250 günlükten 0,4'ten fazla saparsa
  "korelasyon kırılması" sayılır (alışılmış ilişki bozuldu; çeşitlendirme ve risk varsayımları değişebilir).
- 12 varlıklı 60 günlük korelasyon matrisi.
- Göreceli güç (oran grafikleri): BIST 100 ($)/S&P 500, BTC/Nasdaq, altın/S&P 500, ETH/BTC, gümüş/altın, Nasdaq/S&P 500.
  Oran 50 günlük ortalamasının üstündeyse pay güçleniyor; 1 ve 3 aylık değişim.
- BIST sektör rotasyonu: kapanış taramasındaki hisse RS (0–100) ve 1 aylık değişimin sektör medyanları.
Kullanım: python korelasyon.py <cikti_klasoru>   → korelasyon/ozet.json (+ Pazartesi ya da kırılma varsa Telegram kartı)
"""
import os, sys, json, datetime as dt
import numpy as np
import pandas as pd

VARLIK = {"BTC": "BTC-USD", "ETH": "ETH-USD", "Nasdaq": "^IXIC", "S&P 500": "^GSPC", "BIST 100 ($)": None, "Altın": "GC=F",
          "Gümüş": "SI=F", "Dolar endeksi": "DX-Y.NYB", "ABD 10Y faiz": "^TNX", "Brent": "BZ=F", "USD/TRY": "TRY=X", "VIX": "^VIX"}
FARK = {"ABD 10Y faiz", "VIX"}            # seviye değişimi (faiz/oynaklık) — getiri yerine fark
CIFTLER = [("BTC", "Nasdaq", "Bitcoin teknoloji hisseleriyle birlikte mi hareket ediyor (risk iştahı varlığı mı)?"),
           ("Altın", "Dolar endeksi", "Altın güçlü dolarla ters mi hareket ediyor (klasik ilişki)?"),
           ("BIST 100 ($)", "S&P 500", "Borsa İstanbul (dolar bazında) küresel risk iştahını izliyor mu?"),
           ("Altın", "ABD 10Y faiz", "Faiz yükselince altın baskılanıyor mu (reel faiz etkisi)?"),
           ("BTC", "Altın", "Bitcoin 'dijital altın' gibi mi davranıyor?"),
           ("S&P 500", "VIX", "Korku endeksi yükselirken borsa düşüyor mu?"),
           ("Nasdaq", "ABD 10Y faiz", "Faiz artışı büyüme hisselerine baskı yapıyor mu?"),
           ("Brent", "USD/TRY", "Petrol fiyatı kuru etkiliyor mu (cari açık kanalı)?")]
RS_CIFT = [("BIST 100 ($)", "S&P 500"), ("BTC", "Nasdaq"), ("Altın", "S&P 500"), ("ETH", "BTC"), ("Gümüş", "Altın"), ("Nasdaq", "S&P 500")]
KIRILMA = 0.4


def veri_al(gun="3y"):
    import yfinance as yf
    sem = [s for s in VARLIK.values() if s] + ["XU100.IS"]
    v = yf.download(sem, period=gun, interval="1d", auto_adjust=True, progress=False, group_by="ticker", threads=True)
    K = {}
    for ad, s in VARLIK.items():
        if not s: continue
        try:
            x = v[s]["Close"].dropna(); x.index = pd.DatetimeIndex(x.index).tz_localize(None).normalize(); K[ad] = x
        except Exception:
            pass
    try:
        xu = v["XU100.IS"]["Close"].dropna(); xu.index = pd.DatetimeIndex(xu.index).tz_localize(None).normalize()
        K["BIST 100 ($)"] = (xu / K["USD/TRY"].reindex(xu.index, method="ffill")).dropna()
    except Exception:
        pass
    return pd.DataFrame(K).sort_index()


def getiriler(F):
    R = pd.DataFrame(index=F.index)
    for c in F.columns:
        s = F[c].dropna()
        R[c] = (s.diff() if c in FARK else np.log(s).diff()).reindex(F.index)
    return R


def korelasyon(R, a, b, n):
    x = R[[a, b]].dropna().tail(n)
    return float(x[a].corr(x[b])) if len(x) >= max(10, int(n * 0.7)) else None


def seviye(c):
    if c is None: return "veri yok"
    if c >= 0.7: return "güçlü aynı yönlü"
    if c >= 0.4: return "orta aynı yönlü"
    if c > -0.4: return "zayıf / ilişkisiz"
    if c > -0.7: return "orta ters yönlü"
    return "güçlü ters yönlü"


def ciftler(R):
    out = []
    for a, b, soru in CIFTLER:
        if a not in R or b not in R: continue
        c20, c60, c250 = (korelasyon(R, a, b, n) for n in (20, 60, 250))
        kir = c20 is not None and c250 is not None and abs(c20 - c250) >= KIRILMA
        x = R[[a, b]].dropna().tail(260)
        seri = x[a].rolling(60).corr(x[b]).dropna().tail(180)
        out.append({"a": a, "b": b, "soru": soru, "c20": c20, "c60": c60, "c250": c250, "kirilma": bool(kir), "seviye": seviye(c60),
                    "yorum": yorum(a, b, c20, c60, c250, kir), "seri": [round(float(v), 3) for v in seri]})
    return out


def _tr(x, nd=2):
    return f"{x:+.{nd}f}".replace(".", ",") if x is not None else "–"


def yorum(a, b, c20, c60, c250, kir):
    if c60 is None: return "Yeterli ortak veri yok."
    s = f"Son 60 günde {a} ile {b} {seviye(c60)} ({_tr(c60)})."
    if kir: s += f" Dikkat: son 20 günde ilişki belirgin değişti ({_tr(c20)}; 1 yıllık ortalama {_tr(c250)}) — alışılmış davranış bozuldu."
    elif c250 is not None and abs(c60 - c250) >= 0.25: s += f" 1 yıllık ortalamadan ({_tr(c250)}) farklı."
    return s


def matris(R, n=60, sira=None):
    sira = [c for c in (sira or list(VARLIK)) if c in R]
    M = R[sira].tail(int(n * 1.6)).corr(min_periods=int(n * 0.6))
    return {"varliklar": sira, "deger": [[None if not np.isfinite(M.loc[i, j]) else round(float(M.loc[i, j]), 2) for j in sira] for i in sira]}


def goreceli(F):
    out = []
    for a, b in RS_CIFT:
        if a not in F or b not in F: continue
        x = F[[a, b]].dropna()
        if len(x) < 80: continue
        o = (x[a] / x[b]).tail(260); s50 = o.rolling(50).mean()
        d1 = float(o.iloc[-1] / o.iloc[-22] - 1) if len(o) > 22 else None
        d3 = float(o.iloc[-1] / o.iloc[-64] - 1) if len(o) > 64 else None
        guc = bool(o.iloc[-1] > s50.iloc[-1]) if np.isfinite(s50.iloc[-1]) else None
        lider = a if (d3 or 0) > 0 else b
        out.append({"a": a, "b": b, "d1": d1, "d3": d3, "guc": guc, "lider": lider,
                    "yorum": (f"Son 3 ayda {lider} daha güçlü ({_y(abs(d3))} fark)" if d3 is not None else "")
                             + (f"; oran 50 günlük ortalamasının {'üstünde — ' + a + ' güçleniyor' if guc else 'altında — ' + b + ' güçleniyor'}." if guc is not None else "."),
                    "seri": [round(float(v), 6) for v in (o / o.iloc[0]).tail(120)]})
    return out


def _y(x):
    return f"%{x * 100:.1f}".replace(".", ",") if x is not None else "–"


def sektor_rotasyonu(tarama_yolu):
    """Kapanış taramasından (tarama/bist.csv) sektör medyan RS ve 1 aylık değişim."""
    try:
        t = pd.read_csv(tarama_yolu)
    except Exception:
        return []
    if "Sektör" not in t or "RS" not in t: return []
    t = t.dropna(subset=["Sektör", "RS"])
    g = t.groupby("Sektör").agg(rs=("RS", "median"), d1a=("1A", "median"), n=("Kod", "count"),
                                 lider=("Kod", lambda s: ", ".join(t.loc[s.index].sort_values("RS", ascending=False)["Kod"].head(3))))
    g = g[g["n"] >= 3].sort_values("rs", ascending=False)
    return [{"sektor": i, "rs": round(float(r["rs"]), 1), "d1a": None if not np.isfinite(r["d1a"]) else float(r["d1a"]), "n": int(r["n"]),
             "lider": r["lider"]} for i, r in g.iterrows()]


def hesapla(klasor=None, onceki=None, F=None):
    F = veri_al() if F is None else F
    R = getiriler(F)
    o = {"zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "ciftler": ciftler(R), "matris": matris(R),
         "goreceli": goreceli(F), "son_tarih": str(F.index[-1].date())}
    if onceki: o["sektor"] = sektor_rotasyonu(os.path.join(onceki, "tarama", "bist.csv"))
    o["kirilmalar"] = [f"{c['a']}–{c['b']}" for c in o["ciftler"] if c["kirilma"]]
    if klasor:
        os.makedirs(os.path.join(klasor, "korelasyon"), exist_ok=True)
        json.dump(o, open(os.path.join(klasor, "korelasyon", "ozet.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return o


def kart_ciz(o, yol):
    import kart as K
    tr2 = lambda x: _tr(x) if x is not None else "–"
    bol = [{"baslik": "ANA İLİŞKİLER (60 GÜN)", "renk": K.C["altin"], "satirlar": [
        {"sol": f"{c['a']} – {c['b']}", "sag": tr2(c["c60"]), "sag_renk": K.C["yesil"] if (c["c60"] or 0) >= 0.4 else K.C["kirmizi"] if (c["c60"] or 0) <= -0.4 else K.C["soluk"],
         "nokta": K.C["kirmizi"] if c["kirilma"] else None, "alt": c["seviye"] + (f" · KIRILMA: 20 gün {tr2(c['c20'])}, 1 yıl {tr2(c['c250'])}" if c["kirilma"] else "")}
        for c in o["ciftler"]]},
           {"baslik": "GÖRECELİ GÜÇ (3 AY)", "renk": K.C["altin"], "satirlar": [
        {"sol": f"{g['a']} / {g['b']}", "sag": (("+" if (g["d3"] or 0) >= 0 else "") + _y(g["d3"])).replace("+-", "-"),
         "sag_renk": K.C["yesil"] if (g["d3"] or 0) > 0 else K.C["kirmizi"], "alt": f"lider: {g['lider']}" + (" · güçleniyor" if g["guc"] else " · zayıflıyor" if g["guc"] is False else "")}
        for g in o["goreceli"]]}]
    if o.get("sektor"):
        s = o["sektor"]
        bol.append({"baslik": "BIST SEKTÖR ROTASYONU", "renk": K.C["altin"], "satirlar":
                    [{"sol": x["sektor"], "sag": f"RS {x['rs']:.0f}", "sag_renk": K.C["yesil"], "alt": f"öne çıkan: {x['lider']}"} for x in s[:3]] +
                    [{"sol": x["sektor"], "sag": f"RS {x['rs']:.0f}", "sag_renk": K.C["kirmizi"]} for x in s[-2:]]})
    alt = (f"{len(o['kirilmalar'])} ilişkide kırılma: {', '.join(o['kirilmalar'])}" if o["kirilmalar"] else "Alışılmış ilişkilerde kırılma yok")
    K.bildirim_karti(f"KORELASYON VE GÖRECELİ GÜÇ  ·  {dt.date.fromisoformat(o['son_tarih']):%d.%m.%Y}", "Piyasalar arası ilişkiler", alt, bol, yol,
                     vurgu=K.C["altin"], not_="Korelasyon günlük getirilerden hesaplanır; nedensellik göstermez. Yatırım tavsiyesi değildir.")
    return yol


if __name__ == "__main__":
    import tg
    klasor = sys.argv[1] if len(sys.argv) > 1 else "cikti"
    o = hesapla(klasor, tg.KLON)
    print("korelasyon:", len(o["ciftler"]), "çift, kırılma:", o["kirilmalar"], "| RS:", [(g["a"], g["b"], g["d3"]) for g in o["goreceli"]])
    try:
        eski = json.load(open(os.path.join(tg.KLON, "korelasyon", "ozet.json"), encoding="utf-8"))
    except Exception:
        eski = {}
    yeni_kir = [k for k in o["kirilmalar"] if k not in (eski.get("kirilmalar") or [])]
    if dt.date.today().weekday() == 0 or yeni_kir:   # Pazartesi özeti ya da yeni kırılma
        try:
            b = tg.Bot("sabah")
            if b.aktif:
                yol = kart_ciz(o, os.path.join(klasor, "korelasyon", "kart.png"))
                ac = "🔗 <b>Korelasyon ve göreceli güç</b>" + (f"\n⚠️ Yeni kırılma: {', '.join(yeni_kir)}" if yeni_kir else "")
                b.foto(yol, ac, f"korelasyon:{dt.date.today()}", 72); b.kaydet()
        except Exception as ex:
            print("korelasyon kartı:", ex)
