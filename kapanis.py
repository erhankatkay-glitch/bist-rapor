# -*- coding: utf-8 -*-
"""Kapanış sonrası çalıştırıcı: açık kurulumları takip eder, kapanan mumlarda fırsat arar, Telegram'a sessiz
gönderir (otomatik silinir), kapanış bültenlerini üretir ve her şeyi uygulamanın okuyacağı klasöre yazar.

Kullanım: python kapanis.py <slot> [--zorla]
  bist-ogle      BIST 10:00–14:00 dilimi kapanışı (14:20 TSİ)      → 4 saatlik
  bist-kapanis   BIST kapanışı (18:27 TSİ)                         → 4 saatlik + günlük (+ haftalık/aylık) + bülten
  kripto         Her 4 saatlik mum kapanışı (03/07/11/15/19/23 TSİ) → 4 saatlik; 03:xx'te + günlük (+H/A) + bültenler
  emtia-4s       Hafta içi 4 saatlik mum kapanışları                → 4 saatlik
  emtia-kapanis  ABD vadeli kapanışı (01:35 TSİ)                    → günlük (+ haftalık/aylık) + bülten
  abd-ogle       ABD 09:30–13:30 ET dilimi kapanışı                 → 4 saatlik
  abd-kapanis    ABD kapanışı (16:00 ET)                            → 4 saatlik + günlük (+H/A) + bülten
--zorla: tatil/tazelik kontrollerini atlar ve haftalık/aylık taramayı da yapar (deneme için)."""
import os, re, sys, json, time, shutil, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd

import bist_teknik as T
import bist_varlik as V
import firsat as F
import tg
import teknik_bulten as TB

TSI = dt.timezone(dt.timedelta(hours=3)); UTC = dt.timezone.utc
KLON, CIKTI = tg.KLON, tg.CIKTI
PIYASA_AD = {"bist": "BIST", "kripto": "Kripto", "emtia": "Emtia", "abd": "ABD"}
ADET = 5
MIN_TL_HACIM = 20e6       # BIST: 20 günlük medyan işlem hacmi
MIN_USD_HACIM = 2e6       # Kripto: 24 saatlik USDT hacmi
YONLER = {"bist": (1,), "kripto": (1, -1), "emtia": (1,), "abd": (1,)}
MIN_USD_HISSE = 20e6      # ABD: 20 günlük medyan dolar hacmi
ZORLA = False
try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:
    ET = None
OMUR = {"4S": 46.5, "G": 46.5, "H": 46.5, "A": 46.5}   # üst sınır; asıl silme: yeni mesaj gelince / kurulumlar kapanınca
TAKIP_OMUR = 24


def log(*a):
    print(*a, flush=True)


def jsonla(x):
    if isinstance(x, dict): return {str(k): jsonla(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [jsonla(v) for v in x]
    if isinstance(x, (np.floating, float)): return None if not np.isfinite(x) else float(x)
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (np.bool_,)): return bool(x)
    if isinstance(x, (pd.Timestamp, dt.datetime, dt.date)): return x.isoformat()
    return x


# ====================================================================== durum
class Durum:
    DOSYA = ("acik", "gecmis", "olaylar", "son", "istatistik", "islenen")

    def __init__(self, p):
        self.p = p; self.kok = os.path.join(CIKTI, "firsat", p)
        onceki = os.path.join(KLON, "firsat", p)
        if not os.path.isdir(self.kok):
            if os.path.isdir(onceki): shutil.copytree(onceki, self.kok)
            else: os.makedirs(self.kok)
        os.makedirs(os.path.join(self.kok, "grafik"), exist_ok=True)
        bos = {"acik": [], "gecmis": [], "olaylar": [], "son": {}, "istatistik": {}, "islenen": {}}
        for d in self.DOSYA:
            try: setattr(self, d, json.load(open(os.path.join(self.kok, d + ".json"), encoding="utf-8")))
            except Exception: setattr(self, d, bos[d])

    def kaydet(self):
        t = dt.datetime.now(UTC)
        self.gecmis = self.gecmis[-3000:]
        self.olaylar = [o for o in self.olaylar if t - dt.datetime.fromisoformat(o["zaman"]) < dt.timedelta(days=5)]
        for d in self.DOSYA:
            json.dump(jsonla(getattr(self, d)), open(os.path.join(self.kok, d + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        kullan = {g for s in self.son.values() for g in s.get("grafik", {}).values()}
        for f in os.listdir(os.path.join(self.kok, "grafik")):
            if f"grafik/{f}" not in kullan: os.remove(os.path.join(self.kok, "grafik", f))


# ====================================================================== veri
def yahoo_saatlik(semboller, tz, sure="180d"):
    import yfinance as yf
    out = {}
    semboller = list(dict.fromkeys(semboller))
    for i in range(0, len(semboller), 80):
        grup = semboller[i:i + 80]; df = None
        for deneme in range(3):
            try:
                df = yf.download(grup, period=sure, interval="60m", auto_adjust=True, progress=False, group_by="ticker", threads=True); break
            except Exception as ex:
                log("saatlik indirme hatası, tekrar:", ex); time.sleep(5)
        if df is None or df.empty: continue
        for s in grup:
            try:
                d = (df[s] if isinstance(df.columns, pd.MultiIndex) else df).dropna(subset=["Close"])
                if len(d) < 40: continue
                d = d[["Open", "High", "Low", "Close", "Volume"]].astype(float).copy()
                if d.index.tz is not None: d.index = d.index.tz_convert(tz).tz_localize(None)
                d["Volume"] = d["Volume"].fillna(0)
                out[s] = d
            except Exception:
                continue
    return out


def tamamlanan(g, bar, simdi):
    """Bitiş zamanı henüz gelmemiş (yarım) mumları at."""
    return g[g.index + bar <= simdi + pd.Timedelta(minutes=2)]


def bist_4s(h1, simdi_tsi):
    h = h1.copy(); idx = h.index
    saat = idx.hour
    idx = idx.where(saat < 18, idx.normalize() + pd.Timedelta(hours=17, minutes=59))
    idx = idx.where(saat >= 10, idx.normalize() + pd.Timedelta(hours=10))
    h.index = idx
    return tamamlanan(T.yeniden_ornekle(h, "4S", "hisse"), pd.Timedelta(hours=4), simdi_tsi)


def resmi_kapanis_uygula(h1, semboller, simdi_tsi):
    """Saatlik veride son mum kapanış seansından (18:00–18:10) önceki son işlemdir; resmi kapanış değildir.
    Seans bittiyse (18:12 sonrası) günlük bardaki resmi kapanışı o günün son saatlik mumuna yazar.
    h1: {kod: DataFrame (TSİ, tz'siz)}; semboller: {kod: yahoo_sembolu}."""
    if simdi_tsi.time() < dt.time(18, 12) or simdi_tsi.weekday() >= 5: return 0
    import yfinance as yf
    bugun = simdi_tsi.normalize(); duzelen = 0
    liste = [semboller[k] for k in h1 if k in semboller]
    for i in range(0, len(liste), 150):
        try:
            g = yf.download(liste[i:i + 150], period="5d", interval="1d", auto_adjust=True, progress=False, group_by="ticker", threads=True)
        except Exception as ex:
            log("resmi kapanış indirilemedi:", ex); continue
        for k, s_ in semboller.items():
            if s_ not in liste[i:i + 150] or k not in h1: continue
            try:
                d = (g[s_] if isinstance(g.columns, pd.MultiIndex) else g).dropna(subset=["Close"])
                d.index = d.index.tz_localize(None) if d.index.tz is not None else d.index
                if not len(d) or d.index[-1].normalize() != bugun: continue
                c = float(d["Close"].iloc[-1]); h = h1[k]
                gun_i = h.index[h.index.normalize() == bugun]
                if not len(gun_i): continue
                t = gun_i[-1]
                h.loc[t, "Close"] = c
                h.loc[t, "High"] = max(float(h.loc[t, "High"]), c); h.loc[t, "Low"] = min(float(h.loc[t, "Low"]), c)
                duzelen += 1
            except Exception:
                continue
    log(f"Resmi kapanış uygulandı: {duzelen} sembol")
    return duzelen


def bist_gunluk_hacim(h1):
    tl = (h1["Close"] * h1["Volume"]).groupby(h1.index.normalize()).sum()
    return float(tl.iloc[-20:].median()) if len(tl) else 0.0


def kripto_mum(baz, borsa, aralik="4h", limit=1000):
    """Binance/OKX USDT paritesi mumları (UTC, TakerBuy dahil — Binance)."""
    import bist_kripto as KR
    if borsa == "Binance":
        k = KR._get(f"{KR.BINANCE}/klines", symbol=f"{baz}USDT", interval=aralik, limit=limit)
        df = pd.DataFrame(k, columns=["t", "Open", "High", "Low", "Close", "Volume", "tk", "QuoteVol", "n", "TakerBuy", "b", "c"])
        df.index = pd.to_datetime(df["t"], unit="ms"); df.index.name = None
        return df[["Open", "High", "Low", "Close", "Volume", "TakerBuy"]].astype(float)
    bar = {"4h": "4H", "1d": "1Dutc", "1h": "1H"}[aralik]; out, sonra = [], None
    while len(out) < limit:
        prm = {"instId": f"{baz}-USDT", "bar": bar, "limit": 100}
        if sonra: prm["after"] = sonra
        d = KR._get(f"{KR.OKX}/market/history-candles", **prm).get("data", [])
        if not d: break
        out += d; sonra = d[-1][0]
        if len(d) < 100: break
        time.sleep(0.12)
    df = pd.DataFrame(out, columns=["t", "Open", "High", "Low", "Close", "Volume", "vq", "vqq", "ok"])
    df.index = pd.to_datetime(df["t"].astype("int64"), unit="ms"); df.index.name = None
    return df[["Open", "High", "Low", "Close", "Volume"]].astype(float).sort_index()


def kripto_evren():
    import bist_kripto as KR
    ev = KR.evren()
    ev = ev[(ev["Binance USDT"] | ev["OKX USDT"]) & (ev["Hacim $"] >= MIN_USD_HACIM)]
    out = []
    for _, r in ev.iterrows():
        out.append({"baz": r["Kod"], "borsa": "Binance" if r["Binance USDT"] else "OKX",
                    "try": "Binance" if r.get("Binance TRY") else ("OKX" if r.get("OKX TRY") else None), "hacim": float(r["Hacim $"])})
    return out


def usdttry():
    import bist_kripto as KR
    try: return float(KR._get(f"{KR.BINANCE}/ticker/price", symbol="USDTTRY")["price"])
    except Exception: return None


def emtia_saatlik():
    kod = [k for k, v in V.VARLIKLAR.items() if v[2] == "emtia"]
    sym = {k: V.VARLIKLAR[k][0] for k in kod if V.VARLIKLAR[k][0]}
    ham = yahoo_saatlik(list(sym.values()) + ["GC=F", "TRY=X"], "UTC")
    out = {k: ham[s] for k, s in sym.items() if s in ham}
    if "GC=F" in ham and "TRY=X" in ham:
        fx = ham["TRY=X"]["Close"].reindex(ham["GC=F"].index, method="ffill")
        g = ham["GC=F"][["Open", "High", "Low", "Close"]].mul(fx, axis=0) / 31.1035
        g["Volume"] = 0.0; out["GRAMALTIN"] = g.dropna()
    return out


# ====================================================================== takip
def usd(x):
    if x >= 1e6: return f"{x / 1e6:.1f} mn $".replace(".", ",")
    return f"{x / 1e3:,.0f} bin $".replace(",", ".")


def _yon(k): return "AL" if k["yon"] == 1 else "SAT"


def takip_et(D, bars_fn, simdi):
    """Açık kurulumları yeni mumlarla ilerletir; olay metinleri döndürür."""
    yeni_olay = []; kalan = []
    for k in D.acik:
        try: bars = bars_fn(k)
        except Exception as ex:
            log("takip verisi alınamadı:", k["kod"], ex); bars = None
        for tur, _ in F.ilerlet(k, bars, simdi):
            g = k["giris"]; ad = f"<b>{F._e(F.gorunen(k['kod'], k.get('ad')))}</b> {_yon(k)} ({T.TF_AD[k['tf']].lower()})"
            if tur.startswith("H"):
                i = int(tur[1]) - 1; f = k["hedef"][i]
                ek = " → pozisyonun yarısını kapat, stopu girişe (" + F.fy(g) + ") çek" if i == 0 else " → %30'unu kapat" if i == 1 else ""
                m = f"✅ {ad} H{i + 1} görüldü: {F.fy(f)} ({F.yz((f - g) / g * k['yon'])}){ek}"
            elif tur == "stop":
                m = f"⛔ {ad} stop oldu: {F.fy(k['cikis'])} · sonuç {F.rrs(k['R'])} ({F.yz(F.getiri(k))})"
            elif tur == "basabas":
                m = f"↩️ {ad} H1 sonrası girişte kapandı · sonuç {F.rrs(k['R'])} ({F.yz(F.getiri(k))})"
            else:
                m = f"⌛ {ad} süre doldu, {F.fy(k['cikis'])} seviyesinden kapatıldı · sonuç {F.rrs(k['R'])} ({F.yz(F.getiri(k))})"
            if k["durum"] == "kapandı" and k.get("sebep") == "tüm hedefler":
                m += f"\n🏁 {ad} tüm hedefler tamamlandı · sonuç {F.rrs(k['R'])} ({F.yz(F.getiri(k))})"
            yeni_olay.append(m)
            sol = f"{F.gorunen(k['kod'], k.get('ad'))} · {_yon(k)} · {T.TF_AD[k['tf']].lower()}"
            if tur.startswith("H"):
                i = int(tur[1]) - 1; f_ = k["hedef"][i]
                ne = ["pozisyonun yarısını kapat, stopu girişe (" + F.fy(g) + ") çek", "pozisyonun %30'unu kapat", "kalan pozisyonu kapat"][i]
                kk = {"tur": "hedef", "sol": sol, "sag": f"H{i + 1} görüldü",
                      "alt": f"H{i + 1} seviyesi {F.fy(f_)} ({F.yz((f_ - g) / g * k['yon'])}) · {ne}"
                             + (f" · kurulum tamamlandı, sonuç {F.rrs(k['R'])} ({F.yz(F.getiri(k))})" if k["durum"] == "kapandı" else "")}
            else:
                kk = {"tur": tur, "sol": sol, "sag": F.rrs(k["R"]), "alt": {"stop": "Stop oldu", "basabas": "İlk hedef sonrası girişte kapandı",
                       "sure": "Süre doldu, piyasadan kapatıldı"}.get(tur, "") + f" · çıkış {F.fy(k.get('cikis'))} · sonuç {F.yz(F.getiri(k))}"}
            D.olaylar.append({"zaman": dt.datetime.now(UTC).isoformat(), "id": k["id"], "metin": m, "kart": kk})
        (D.gecmis if k["durum"] == "kapandı" else kalan).append(k)
    D.acik = kalan
    return yeni_olay


def _duz(h):
    return re.sub(r"<[^>]+>", "", str(h)).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")


def kart_gonder(bot, anahtar, omur, ust, baslik, alt, bolumler, aciklama, vurgu="altin", not_=None, yedek=None, bag=None):
    """Bildirimi görsel kart olarak gönderir (önce aynı anahtarlı eskiyi siler); çizilemezse yedek metni gönderir."""
    try:
        import kart as KT
        os.makedirs(os.path.join(CIKTI, "kartlar"), exist_ok=True)
        yol = os.path.join(CIKTI, "kartlar", re.sub(r"[^a-z0-9]+", "_", anahtar.lower()) + ".png")
        KT.bildirim_karti(ust, baslik, alt, bolumler, yol, vurgu=KT.C.get(vurgu, vurgu), not_=not_)
        bot.sil_anahtar(anahtar)
        if bot.foto(yol, aciklama, anahtar, omur, bag=bag): return True
    except Exception as ex:
        log("kart çizilemedi:", anahtar, ex)
    if yedek: return bool(bot.mesaj(yedek, anahtar, omur, bag=bag, yerine=True))
    return False


def acik_kart_satirlari(acik, n=10):
    import kart as KT
    C = KT.C; out = []
    for k in acik[:n]:
        c = k.get("son_fiyat", k["giris"]); ger = (c - k["giris"]) / k["giris"] * k["yon"]
        durum = " · ".join(f"H{i + 1} {'görüldü' if i < k['asama'] else F.fy(k['hedef'][i])}" for i in range(3))
        out.append({"logo": (k["kod"], k.get("piyasa")), "sol": f"{F.gorunen(k['kod'], k.get('ad'))} · {'AL' if k['yon'] == 1 else 'SAT'} · {T.TF_AD[k['tf']].lower()}",
                    "sag": F.yz(ger), "sag_renk": C["yesil"] if ger >= 0 else C["kirmizi"], "nokta": C["yesil"] if k["yon"] == 1 else C["kirmizi"],
                    "alt": f"giriş {F.fy(k['giris'])} · stop {'girişte' if k['asama'] else F.fy(k['stop'])} · {durum}"})
    return out


def takip_mesaji(bot, D):
    t = dt.datetime.now(UTC)
    son = [o for o in D.olaylar if t - dt.datetime.fromisoformat(o["zaman"]) < dt.timedelta(hours=TAKIP_OMUR)]
    if not son: return
    satir = [f"📌 <b>{tg.buyuk(PIYASA_AD[D.p])} · KURULUM TAKİBİ</b>", tg.AYRAC, f"<i>Son {TAKIP_OMUR} saatteki gelişmeler</i>"]
    gov = []
    for o in reversed(son[-25:]):
        z = dt.datetime.fromisoformat(o["zaman"]).astimezone(TSI)
        gov.append(f"<code>{z:%d.%m %H:%M}</code>  {o['metin']}")
    satir.append("<blockquote>" + "\n".join(gov) + "</blockquote>")
    if D.acik:
        satir.append(f"📂 Açık kurulum: <b>{len(D.acik)}</b>")
        satir.append("<blockquote expandable>" + "\n".join(F.acik_satiri(k) for k in D.acik[:20]) + "</blockquote>")
    import kart as KT
    C = KT.C; sat = []
    renk_tur = {"hedef": C["yesil"], "stop": C["kirmizi"], "basabas": C["soluk"], "sure": C["soluk"]}
    for o in reversed(son[-12:]):
        z = dt.datetime.fromisoformat(o["zaman"]).astimezone(TSI); kk = o.get("kart")
        if not kk: kk = {"tur": "", "sol": _duz(o["metin"])[2:60], "sag": "", "alt": ""}
        sag_r = C["yesil"] if kk["tur"] == "hedef" or str(kk.get("sag", "")).startswith("+") else C["kirmizi"] if kk["tur"] == "stop" else C["yazi"]
        sat.append({"sol": kk["sol"], "sag": kk.get("sag"), "sag_renk": sag_r, "nokta": renk_tur.get(kk["tur"], C["altin"]),
                    "alt": f"{z:%d.%m %H:%M} · {kk['alt']}"})
    bol = [{"baslik": "Son gelişmeler", "renk": C["altin"], "satirlar": sat}]
    if D.acik: bol.append({"baslik": f"Açık kurulumlar ({len(D.acik)})", "renk": C["mavi"], "satirlar": acik_kart_satirlari(D.acik)})
    aciklama = f"📌 <b>{PIYASA_AD[D.p]} kurulum takibi</b> · {len(son)} yeni gelişme"
    kart_gonder(bot, f"takip:{D.p}", TAKIP_OMUR, f"{tg.buyuk(PIYASA_AD[D.p])}  ·  KURULUM TAKİBİ", "Hedef ve stop gelişmeleri",
                f"Son {TAKIP_OMUR} saat", bol, aciklama, "altin", yedek="\n".join(satir))


# ====================================================================== fırsat turu
def mum_metni(p, tf, mum):
    m = pd.Timestamp(mum)
    if tf == "4S":
        bit = m + pd.Timedelta(hours=4)
        if p == "abd":
            bit = min(bit, m.normalize() + pd.Timedelta(hours=16))
            bit = pd.Timestamp(bit.to_pydatetime().replace(tzinfo=ET)).tz_convert("Europe/Istanbul").tz_localize(None)
        elif p != "bist": bit = bit + pd.Timedelta(hours=3)
        return f"{bit:%d.%m.%Y %H:%M} TSİ"
    if tf == "H": return f"{m:%d.%m.%Y} haftası"
    if tf == "A": return f"{m:%m.%Y} ayı"
    return f"{m:%d.%m.%Y}"


def rejim_turu(p, analizler, endeks, bot):
    """Aşama 10c: piyasa rejimi (genişlik, dağıtım günleri, takip günü, maruziyet koçu) → rejim/{p}.json + Telegram kartı."""
    try:
        import rejim as RJ
        r = RJ.hesapla(p, analizler, endeks["tf"]["G"]["h"], CIKTI, vix=RJ.vix_al() if p == "abd" else None)
        log("Rejim:", r["ozet"])
        try: eski = json.load(open(os.path.join(KLON, "rejim", f"{p}.json"), encoding="utf-8"))
        except Exception: eski = None
        # kart yalnız anlamlı değişimde ya da Cuma özetinde (her kapanışta aynı kart kalabalık yapmasın)
        if (eski is None or eski.get("durum") != r["durum"] or abs(eski.get("maruziyet", 0) - r["maruziyet"]) >= 20
                or (r.get("tepe_uyarisi") and not eski.get("tepe_uyarisi")) or dt.date.today().weekday() == 4):
            RJ.telegram(p, r, CIKTI, bot, onceki=eski)
    except Exception as ex:
        log("rejim:", ex)


REJIM = {}   # (piyasa, tf) → piyasa öncüsünün yönü (+1/0/-1); fırsat filtresi için (firsat.FILTRE)


def firsat_turu(bot, D, tf, varliklar, ekstra_fn=None, tl_fn=None):
    """Bir zaman dilimi için tarama → seçim → takip kaydı → grafik → Telegram."""
    if not varliklar: log(f"{D.p} {tf}: taranacak varlık yok"); return []
    son_mum = str(max(v["a"]["h"].index[-1] for v in varliklar))
    if not ZORLA and D.islenen.get(f"{tf}_mum") == son_mum:
        log(f"{D.p} {tf}: {son_mum} mumu zaten işlendi, atlandı."); return []
    D.islenen[f"{tf}_mum"] = son_mum
    t0 = time.time()
    rj = REJIM.get((D.p, tf))
    if (D.p, tf) in F.FILTRE: log(f"{D.p} {tf}: piyasa yönü {rj}")
    secilen, adaylar, pist = F.tara(varliklar, tf, D.p, YONLER[D.p], adet=ADET + 4, ilerleme=log, rejim_degeri=rj)
    try: portfoy_uyari(bot, D, tf, varliklar, adaylar)
    except Exception as ex: log("portföy uyarısı:", ex)
    acik_anahtar = {(k["kod"], k["tf"], k["yon"]) for k in D.acik}
    secilen = [f for f in secilen if (f["kod"], f["tf"], f["yon"]) not in acik_anahtar][:ADET]
    log(f"{D.p} {tf}: {len(varliklar)} varlık, {len(adaylar)} aday, {len(secilen)} fırsat ({time.time() - t0:.0f} sn)")
    by = {v["kod"]: v for v in varliklar}
    for f in secilen:
        if ekstra_fn:
            try: ekstra_fn(f)
            except Exception as ex: log("ek bilgi alınamadı:", f["kod"], ex)
    simdi = dt.datetime.now(UTC)
    yeni = [F.kayit(f, simdi) for f in secilen]
    grafik = {}
    import kart as KT
    for f in secilen:
        ad = f"{tf}_{f['kod'].replace('/', '-').replace('@', '_')}.png"
        try:
            KT.firsat_karti(f, by[f["kod"]]["a"], os.path.join(D.kok, "grafik", ad), PIYASA_AD[D.p], T.TF_AD[tf]); grafik[f["kod"]] = f"grafik/{ad}"
        except Exception as ex:
            log("kart çizilemedi:", f["kod"], ex)
    D.istatistik[tf] = pist.tablo()
    mum = secilen[0]["mum"] if secilen else (adaylar[0]["mum"] if adaylar else None)
    D.son[tf] = {"zaman": simdi.isoformat(), "mum": mum, "taranan": len(varliklar),
                 "firsatlar": [jsonla({k: v for k, v in f.items() if k != "balina_ozet"}) for f in secilen],
                 "adaylar": [{"kod": a["kod"], "yon": a["yon"], "kurulum": a["kurulum_ad"], "puan": a["puan"]} for a in adaylar[:20]],
                 "grafik": grafik}
    # Telegram
    acik_tf = [k for k in D.acik if k["tf"] == tf]
    if secilen:
        bas = [f"🎯 <b>{tg.buyuk(PIYASA_AD[D.p])} · {tg.buyuk(T.TF_AD[tf])} FIRSATLAR</b>", tg.AYRAC,
               f"🕯 Mum: {mum_metni(D.p, tf, mum)}",
               f"🔎 {len(varliklar):,} likit varlık tarandı → <b>{len(secilen)} fırsat</b>".replace(",", ".")]
        if any(f["yon"] == -1 for f in secilen):
            bas.append("🔴 SAT fırsatları vadeli (kaldıraçlı) işlem içindir; spotta açığa satış yapılamaz.")
        bas.append("")
        bas += [f"{'🟢' if f['yon'] == 1 else '🔴'} <b>{F._e(F.gorunen(f['kod'], f.get('ad')))}</b> · {F._e(f['kurulum_ad'][:48])} · puan <b>{f['puan']:.0f}</b>" for f in secilen]
        if acik_tf:
            bas.append("\n📂 <b>Önceki mesajlardan açık kurulumlar</b>")
            bas.append("<blockquote expandable>" + "\n".join(F.acik_satiri(k) for k in acik_tf[:15]) + "</blockquote>")
        bas.append("\n<i>Plan: H1'de yarısı, H2'de %30'u, H3'te kalanı kapatılır; H1 görülünce stop girişe çekilir.</i>")
        bag = [k["id"] for k in yeni] + [k["id"] for k in acik_tf]
        anahtar = f"firsat:{D.p}:{tf}"
        import kart as KT
        C = KT.C
        satl = [{"logo": (f["kod"], D.p), "sol": f"{F.gorunen(f['kod'], f.get('ad'))} · {'AL' if f['yon'] == 1 else 'SAT'}", "sag": f"puan {f['puan']:.0f}",
                 "sag_renk": C["yesil"] if f["yon"] == 1 else C["kirmizi"], "nokta": C["yesil"] if f["yon"] == 1 else C["kirmizi"],
                 "alt": f"{f['kurulum_ad'][:60]} · giriş {F.fy(f['plan']['giris'])} · stop {F.fy(f['plan']['stop'])} · H1 {F.fy(f['plan']['hedef'][0]['fiyat'])}"}
                for f in secilen]
        bol = [{"baslik": "Yeni fırsatlar (ayrıntılı kartlar aşağıda)", "renk": C["altin"], "satirlar": satl}]
        if acik_tf: bol.append({"baslik": f"Önceki mesajlardan açık kurulumlar ({len(acik_tf)})", "renk": C["mavi"], "satirlar": acik_kart_satirlari(acik_tf, 8)})
        not_ = "Plan: H1'de pozisyonun yarısı, H2'de %30'u, H3'te kalanı kapatılır; H1 görülünce stop girişe çekilir."
        if any(f["yon"] == -1 for f in secilen): not_ += " SAT fırsatları vadeli (kaldıraçlı) işlem içindir; spotta açığa satış yapılamaz."
        ids = kart_gonder(bot, anahtar, OMUR[tf], f"{tg.buyuk(PIYASA_AD[D.p])}  ·  {tg.buyuk(T.TF_AD[tf])} FIRSATLAR",
                          f"{len(secilen)} yeni fırsat", f"Mum: {mum_metni(D.p, tf, mum)} · {len(varliklar):,} likit varlık tarandı".replace(",", "."),
                          bol, f"🎯 <b>{PIYASA_AD[D.p]} · {T.TF_AD[tf].lower()} fırsatlar</b> · {len(secilen)} yeni · ayrıntılı kartlar aşağıda",
                          "altin", not_=not_, yedek="\n".join(bas), bag=bag)
        if ids:
            for f in secilen:
                ek = []
                if tl_fn and tl_fn(f): ek.append("💱 " + F._e(tl_fn(f)))
                if f["ekstra"].get("turev"): ek.append("📊 " + F._e(f["ekstra"]["turev"]))
                alt = KT.baslik_metni(f) + ("\n" + "\n".join(ek) if ek else "")
                if f["kod"] in grafik: bot.foto(os.path.join(D.kok, grafik[f["kod"]]), alt, anahtar, OMUR[tf], bag=bag)
                else: sade_firsat_gonder(bot, f, anahtar, OMUR[tf], bag, alt, tl_fn)
    D.acik += yeni
    return secilen


def sade_firsat_gonder(bot, f, anahtar, omur, bag, alt, tl_fn=None):
    """Grafikli fırsat kartı çizilemediğinde: grafiksiz KATKAY kartı; o da olmazsa düz metin."""
    import kart as KT
    C = KT.C; p = f["plan"]; g = p["giris"]
    try:
        plan = [{"sol": f"H{i + 1}", "sag": f"{F.fy(z['fiyat'])}  {F.yz((z['fiyat'] - g) / g)}", "sag_renk": C["yesil"], "nokta": C["yesil"],
                 "alt": f"{F.rr(z['r'])} · {z['etiket']}"} for i, z in enumerate(p["hedef"])]
        plan = [{"sol": "Giriş", "sag": F.fy(g), "nokta": C["mavi"], "alt": f"bölge {F.fy(p['bolge'][0])} – {F.fy(p['bolge'][1])}"},
                {"sol": "Stop", "sag": f"{F.fy(p['stop'])}  {F.yz((p['stop'] - g) / g)}", "sag_renk": C["kirmizi"], "nokta": C["kirmizi"]}] + plan
        tey = [{"sol": t, "sag": "evet" if ok else "hayır", "sag_renk": C["yesil"] if ok else C["soluk"]} for t, ok in f["teyit"]]
        bol = [{"baslik": "İşlem planı", "renk": C["altin"], "satirlar": plan}, {"baslik": "Teyitler", "renk": C["mavi"], "satirlar": tey}]
        if f.get("risk"): bol.append({"baslik": "Riskler", "renk": C["kirmizi"], "satirlar": [{"sol": f"Risk {i_ + 1}", "nokta": C["altin"], "alt": r_} for i_, r_ in enumerate(f["risk"][:4])]})
        os.makedirs(os.path.join(CIKTI, "kartlar"), exist_ok=True)
        yol = os.path.join(CIKTI, "kartlar", re.sub(r"[^A-Za-z0-9]+", "_", f"sade_{f['kod']}_{f['tf']}") + ".png")
        KT.bildirim_karti(f"{tg.buyuk(PIYASA_AD.get(f['piyasa'], f['piyasa']))}  ·  {tg.buyuk(T.TF_AD[f['tf']])}  ·  FIRSAT",
                          f"{F.gorunen(f['kod'], f.get('ad'))} · {'AL' if f['yon'] == 1 else 'SAT'} · puan {f['puan']:.0f}",
                          f["kurulum_ad"][:70], bol, yol, vurgu=C["yesil"] if f["yon"] == 1 else C["kirmizi"],
                          not_=KT.basitce(f))
        if bot.foto(yol, alt, anahtar, omur, bag=bag): return True
    except Exception as ex:
        log("sade fırsat kartı çizilemedi:", f.get("kod"), ex)
    return bool(bot.mesaj(F.firsat_metni(f, tl_fn(f) if tl_fn else None), anahtar, omur, bag=bag, yerine=False, notlu=False))


def _pf_anahtar(kod):
    import bist_kripto as KR
    return ("K", KR.coz(kod)[0]) if KR.kripto_mu(kod) else ("H", kod.upper())


def portfoy_uyari(bot, D, tf, varliklar, adaylar):
    """Portföydeki varlıklarda ters yönlü (SAT) kurulum oluştuysa kişisel uyarı gönderir."""
    import portfoy as P
    pf = {_pf_anahtar(k) for k, _, _ in P.takip()}
    if not pf: return
    sat = [a for a in adaylar if a["yon"] == -1 and _pf_anahtar(a["kod"]) in pf and a["puan"] >= 45]
    if -1 not in YONLER[D.p]:   # yalnız AL taranan piyasalarda portföy varlıklarını SAT yönünde ayrıca tara
        pist = F.PiyasaIstatistik()
        for v in varliklar:
            if _pf_anahtar(v["kod"]) not in pf: continue
            b = F.varlik_tara(v, tf, (-1,), pist, olay_topla=False, piyasa=D.p)
            if not b: continue
            if "sr" not in v["a"]: v["a"] = T.tf_analiz(v["a"]["h"], tf)
            sat += [a for a in F.degerlendir(v, tf, b, pist, D.p) if a["puan"] >= 45]
    if not sat: return
    sat_liste = sat
    s = [f"💼 <b>PORTFÖY UYARISI · {tg.buyuk(T.TF_AD[tf])}</b>", tg.AYRAC,
         "Portföyünüzdeki varlıklarda ters yönlü (satış) kurulum oluştu:"]
    for a in sorted(sat, key=lambda x: -x["puan"])[:6]:
        p_ = a["plan"]
        s.append(f"\n🔴 <b>{F._e(F.gorunen(a['kod'], a.get('ad')))}</b> · {F._e(a['kurulum_ad'][:60])} · puan <b>{a['puan']:.0f}</b>")
        s.append(f"<blockquote>Fiyat <code>{F.fy(p_['giris'])}</code> · aşağı hedefler {F.fy(p_['hedef'][0]['fiyat'])} / {F.fy(p_['hedef'][1]['fiyat'])}"
                 f"\nGeçersizlik (yukarı stop): <code>{F.fy(p_['stop'])}</code> ({F.yz((p_['stop'] - p_['giris']) / p_['giris'])})"
                 + (f"\n⚠️ " + F._e(" · ".join(a["risk"][:2])) if a.get("risk") else "") + "</blockquote>")
    s.append("<i>Pozisyonu korumak için stop seviyenizi gözden geçirmeniz, kısmi kâr almanız ya da yükseliş teyidi beklemeniz düşünülebilir.</i>")
    import kart as KT
    C = KT.C; sat = []
    for a in sorted(sat_liste, key=lambda x: -x["puan"])[:6]:
        p_ = a["plan"]
        sat.append({"sol": F.gorunen(a["kod"], a.get("ad")), "sag": f"puan {a['puan']:.0f}", "sag_renk": C["kirmizi"], "nokta": C["kirmizi"],
                    "alt": f"{a['kurulum_ad'][:60]} · fiyat {F.fy(p_['giris'])} · aşağı hedefler {F.fy(p_['hedef'][0]['fiyat'])} / "
                           f"{F.fy(p_['hedef'][1]['fiyat'])} · yükseliş teyidi (geçersizlik) {F.fy(p_['stop'])}"})
    aciklama = f"💼 <b>Portföy uyarısı</b> · {T.TF_AD[tf].lower()} · {len(sat_liste)} varlıkta satış yönlü kurulum"
    kart_gonder(bot, f"portfoy:{D.p}:{tf}", 24, f"PORTFÖY UYARISI  ·  {tg.buyuk(T.TF_AD[tf])}", "Satış yönlü kurulum",
                "Portföyünüzdeki varlıklarda ters sinyal oluştu", [{"baslik": "Dikkat edilmesi gerekenler", "renk": C["kirmizi"], "satirlar": sat}],
                aciklama, "kirmizi", not_="Pozisyonu korumak için stop seviyenizi gözden geçirmeniz, kısmi kâr almanız ya da yükseliş teyidi beklemeniz düşünülebilir.",
                yedek="\n".join(s))


# ====================================================================== ortak yardımcılar
def tazelik_tamam(son_bitis, simdi, zorla, saat=3):
    if zorla: return True
    return son_bitis is not None and simdi - son_bitis <= pd.Timedelta(hours=saat)


def donem_tamam(tf, son_gun, kripto):
    """Son günlük mumdan sonraki işlem günü yeni bir haftaya/aya düşüyorsa haftalık/aylık mum tamamlanmıştır."""
    son_gun = pd.Timestamp(son_gun).normalize()
    sonraki = son_gun + (pd.Timedelta(days=1) if kripto else pd.offsets.BDay(1))
    if tf == "H": return sonraki.isocalendar()[1] != son_gun.isocalendar()[1]
    return sonraki.month != son_gun.month


def rs_haritasi(p):
    s = TB.SON.get(p) or {}
    return {r["Kod"]: r.get("RS") for r in s.get("satir", []) if r.get("RS") is not None}


def ust_gunluk(h, tur):
    """4 saatlik fırsat için üst zaman dilimi (günlük) analizi; saatlik/4 saatlik veriden türetilir."""
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    g = h[list(agg)].resample("1D").agg(agg).dropna(subset=["Close"])
    return T.tf_analiz(g, "G") if len(g) >= 30 else None


def gunluk_tf_turu(bot, D, analizler, tfler, zorla, kripto, para_fn, likit_fn, ekstra_fn=None, tl_fn=None):
    """Bülten analizlerinden (G/H/A) fırsat turları."""
    if not analizler: return
    rs = rs_haritasi(D.p if D.p != "kripto" else "kripto")
    son_gun = max(s["tf"]["G"]["h"].index[-1] for s in analizler if s["tf"].get("G"))
    for tf in tfler:
        if tf in ("H", "A"):
            if not zorla and (not donem_tamam(tf, son_gun, kripto) or D.islenen.get(tf) == str(son_gun.date())):
                continue
        V_ = []
        for s in analizler:
            a = s["tf"].get(tf)
            if not a or not likit_fn(s): continue
            V_.append({"kod": s["kod"], "ad": s["ad"], "para": para_fn(s), "a": a, "ust": s["tf"].get(F.UST_TF[tf]), "rs": rs.get(s["kod"])})
        firsat_turu(bot, D, tf, V_, ekstra_fn, tl_fn)
        if tf in ("H", "A"): D.islenen[tf] = str(son_gun.date())


def bist_bilanco_riski(f):
    try:
        import bist_ileri as IL
        _, sonraki = IL.bilanco_tarihleri(f["kod"])
        if sonraki is not None:
            gun = (pd.Timestamp(sonraki) - pd.Timestamp.today().normalize()).days
            if 0 <= gun <= 7: f["risk"].append(f"Bilanço {gun} gün içinde ({pd.Timestamp(sonraki):%d.%m}); sert fiyat hareketi riski")
    except Exception:
        pass


# ====================================================================== piyasa slotları
def bist(slot, zorla):
    bot = tg.Bot("bist"); D = Durum("bist")
    simdi = pd.Timestamp(dt.datetime.now(TSI).replace(tzinfo=None))
    kodlar = TB.evren("bist")
    acik_kod = {k["kod"] for k in D.acik}
    log(f"BIST: {len(kodlar)} hisse için saatlik veri indiriliyor…")
    h1 = {s[:-3]: d for s, d in yahoo_saatlik([k + ".IS" for k in list(kodlar) + list(acik_kod) + ["XU100"]], "Europe/Istanbul").items()}
    try:
        resmi_kapanis_uygula(h1, {k: k + ".IS" for k in h1}, simdi)
    except Exception as ex:
        log("resmi kapanış:", ex)
    xu = h1.pop("XU100", None)
    log(f"Saatlik veri: {len(h1)} hisse")
    # 1) takip
    olay = takip_et(D, lambda k: h1.get(k["kod"]), simdi)
    # 2) 4 saatlik
    h4 = {k: bist_4s(d, simdi) for k, d in h1.items()}
    if xu is not None and len(xu):
        try: REJIM[("bist", "4S")] = F.rejim(bist_4s(xu, simdi))
        except Exception as ex: log("BIST 100 4S yönü:", ex)
    son_bitis = max((d.index[-1] + pd.Timedelta(hours=4) for d in h4.values() if len(d)), default=None)
    if tazelik_tamam(son_bitis, simdi, zorla):
        V_ = []
        for k, d in h4.items():
            if len(d) < 80 or d.index[-1] + pd.Timedelta(hours=4) != son_bitis: continue
            if bist_gunluk_hacim(h1[k]) < MIN_TL_HACIM: continue
            V_.append({"kod": k, "ad": k, "para": "₺", "a": F.hafif(d, "4S"), "ust_fn": (lambda hh=h1[k]: ust_gunluk(hh, "hisse"))})
        firsat_turu(bot, D, "4S", V_, ekstra_fn=bist_bilanco_riski)
    else:
        log("BIST 4 saatlik: taze mum yok (tatil/seans dışı), atlandı.")
    # 3) kapanış: bülten + günlük/haftalık/aylık
    if slot == "bist-kapanis":
        r = TB.calistir("bist", klasor=CIKTI, zorla=zorla)
        if r:
            analizler = TB.SON["bist"]["analizler"]
            try: REJIM[("bist", "G")] = F.rejim(TB.SON["bist"]["endeks"]["tf"]["G"]["h"])
            except Exception as ex: log("BIST 100 günlük yönü:", ex)
            likit = lambda s: float((s["tf"]["G"]["h"]["Close"] * s["tf"]["G"]["h"]["Volume"]).iloc[-20:].median()) >= MIN_TL_HACIM
            gunluk_tf_turu(bot, D, analizler, ("G", "H", "A"), zorla, False, lambda s: "₺", likit, ekstra_fn=bist_bilanco_riski)
            TB.telegram_gonder("bist", *r, klasor=CIKTI, bot=bot)
            rejim_turu("bist", analizler, TB.SON["bist"]["endeks"], bot)
    if olay: takip_mesaji(bot, D)
    bot.bag_guncelle([k["id"] for k in D.acik])
    D.kaydet(); bot.kaydet()


def kripto(zorla):
    import bist_kripto as KR
    bot = tg.Bot("kripto"); D = Durum("kripto")
    simdi = pd.Timestamp(dt.datetime.now(UTC).replace(tzinfo=None))
    gunluk = simdi.hour < 4 or zorla
    ev = kripto_evren(); kur = usdttry()
    log(f"Kripto: {len(ev)} likit coin (24s hacim ≥ {MIN_USD_HACIM / 1e6:.0f} mn $), USDT/TRY {kur}")
    tl_var = {e["baz"]: e["try"] for e in ev}
    borsa = {e["baz"]: e["borsa"] for e in ev}

    def tl_fn(f):
        baz = KR.coz(f["kod"])[0]
        if not kur or not tl_var.get(baz): return None
        p = f["plan"]
        return (f"TL paritesi {baz}/TRY ({tl_var[baz]}) ≈ giriş {F.fy(p['giris'] * kur)} ₺ · stop {F.fy(p['stop'] * kur)} ₺ · "
                f"H1 {F.fy(p['hedef'][0]['fiyat'] * kur)} ₺ (USDT/TRY {F.fy(kur)} ile)")

    def ekstra(f):
        baz, _, b = KR.coz(f["kod"])
        try:
            bi = KR.buyuk_islemler(baz, "USDT", b)
            ba, bs = bi["buyuk_alis"], bi["buyuk_satis"]
            net = ("alış" if ba >= 1.5 * bs else "satış" if bs >= 1.5 * ba else "dengeli") if ba + bs >= 1e5 else "anlamlı büyük işlem yok"
            f["ekstra"]["balina_canli"] = (f"canlı akış: son {bi['adet']} işlemde (~{bi['sure_dk']:.0f} dk) {bi['buyuk_adet']} büyük işlem "
                                           f"(≥{usd(bi['buyuk_esik'])}); büyük alış {usd(bi['buyuk_alis'])} / satış {usd(bi['buyuk_satis'])} → net {net}")
            if net in ("alış", "satış") and (net == "alış") != (f["yon"] == 1): f["risk"].append("Canlı işlem akışında büyük oyuncular ters yönde")
        except Exception:
            pass
        if f["tf"] != "4S":
            try:
                v = KR.vadeli(baz); p = []
                if v.get("oi_7g") is not None: p.append(f"açık pozisyon 7g {F.yz(v['oi_7g'])}")
                if v.get("taker_7g") is not None: p.append(f"vadeli agresif alış %{v['taker_7g'] * 100:.0f}")
                lk = v.get("likidasyon")
                if lk: p.append(f"son tasfiyeler: long {usd(lk['long'])} / short {usd(lk['short'])}")
                if p: f["ekstra"]["turev"] = " · ".join(p)
            except Exception:
                pass

    # 1) takip (1 saatlik mumlarla)
    def bars(k):
        baz = KR.coz(k["kod"])[0]
        return KR.saatlik_mumlar(baz, "USDT", borsa.get(baz, "Binance"), bar=1000)[0]
    olay = takip_et(D, bars, simdi)

    # 2) 4 saatlik
    def al4(e):
        try:
            d = tamamlanan(kripto_mum(e["baz"], e["borsa"], "4h", 1000), pd.Timedelta(hours=4), simdi)
            return e, d
        except Exception:
            return e, None
    with ThreadPoolExecutor(max_workers=6) as ex: veri4 = list(ex.map(al4, ev))
    son_bitis = max((d.index[-1] + pd.Timedelta(hours=4) for _, d in veri4 if d is not None and len(d)), default=None)
    REJIM[("kripto", "4S")] = next((F.rejim(d) for e, d in veri4 if e["baz"] == "BTC" and d is not None and len(d) > 60), None)
    if tazelik_tamam(son_bitis, simdi, zorla):
        V_ = [{"kod": KR.kod_yap(e["baz"], "USDT", e["borsa"]), "ad": e["baz"], "para": "$", "a": F.hafif(d, "4S"),
               "ust_fn": (lambda dd=d: ust_gunluk(dd, "kripto"))}
              for e, d in veri4 if d is not None and len(d) >= 120 and d.index[-1] + pd.Timedelta(hours=4) == son_bitis]
        firsat_turu(bot, D, "4S", V_, ekstra, tl_fn)
    # 3) günlük (03:xx TSİ turu): taze günlük mumlarla, ardından bültenler ve haftalık/aylık
    if gunluk:
        def al1(e):
            try:
                d = kripto_mum(e["baz"], e["borsa"], "1d", 1000); d.index = d.index.normalize()
                return e, d[d.index < simdi.normalize()]
            except Exception:
                return e, None
        with ThreadPoolExecutor(max_workers=6) as ex: veri1 = list(ex.map(al1, ev))
        dun = simdi.normalize() - pd.Timedelta(days=1)
        REJIM[("kripto", "G")] = next((F.rejim(d) for e, d in veri1 if e["baz"] == "BTC" and d is not None and len(d) > 60), None)
        V_ = [{"kod": KR.kod_yap(e["baz"], "USDT", e["borsa"]), "ad": e["baz"], "para": "$", "a": F.hafif(d, "G"),
               "ust_fn": (lambda dd=d: T.tf_analiz(T.yeniden_ornekle(dd, "H", "kripto"), "H"))}
              for e, d in veri1 if d is not None and len(d) >= 120 and (zorla or d.index[-1] == dun)]
        firsat_turu(bot, D, "G", V_, ekstra, tl_fn)
        for p in ("kripto", "kripto_tl"):
            try:
                r = TB.calistir(p, klasor=CIKTI, zorla=zorla)
                if r: TB.telegram_gonder(p, *r, klasor=CIKTI, bot=bot)
            except Exception as ex:
                log(f"{p} bülteni başarısız:", ex)
        an = (TB.SON.get("kripto") or {}).get("analizler", [])
        likit = {KR.kod_yap(e["baz"], "USDT", e["borsa"]) for e in ev}
        gunluk_tf_turu(bot, D, an, ("H", "A"), zorla, True, lambda s: "$", lambda s: s["kod"] in likit, ekstra, tl_fn)
        if simdi.weekday() == 0 or zorla: karne_mesaji(bot, D)
    if olay: takip_mesaji(bot, D)
    bot.bag_guncelle([k["id"] for k in D.acik])
    D.kaydet(); bot.kaydet()


def emtia(slot, zorla):
    bot = tg.Bot("emtia"); D = Durum("emtia")
    simdi = pd.Timestamp(dt.datetime.now(UTC).replace(tzinfo=None))
    h1 = emtia_saatlik()
    log(f"Emtia: {len(h1)} varlık saatlik veri")
    olay = takip_et(D, lambda k: h1.get(k["kod"]), simdi)
    if slot == "emtia-4s":
        h4 = {k: tamamlanan(T.yeniden_ornekle(d, "4S", "emtia"), pd.Timedelta(hours=4), simdi) for k, d in h1.items()}
        son_bitis = max((d.index[-1] + pd.Timedelta(hours=4) for d in h4.values() if len(d)), default=None)
        if tazelik_tamam(son_bitis, simdi, zorla):
            V_ = [{"kod": k, "ad": V.VARLIKLAR[k][1], "para": "₺" if k == "GRAMALTIN" else "$", "a": F.hafif(d, "4S"),
                   "ust_fn": (lambda hh=h1[k]: ust_gunluk(hh, "emtia"))}
                  for k, d in h4.items() if len(d) >= 120 and simdi - (d.index[-1] + pd.Timedelta(hours=4)) <= pd.Timedelta(hours=5)]
            firsat_turu(bot, D, "4S", V_)
        else:
            log("Emtia 4 saatlik: taze mum yok, atlandı.")
    else:
        r = TB.calistir("emtia", klasor=CIKTI, zorla=zorla)
        if r:
            an = TB.SON["emtia"]["analizler"]
            gunluk_tf_turu(bot, D, an, ("G", "H", "A"), zorla, False, lambda s: s["para"] or "$", lambda s: True)
            TB.telegram_gonder("emtia", *r, klasor=CIKTI, bot=bot)
    if olay: takip_mesaji(bot, D)
    bot.bag_guncelle([k["id"] for k in D.acik])
    D.kaydet(); bot.kaydet()


def abd_4s(h1, simdi_et):
    """ABD seansı 09:30–16:00 (ET): 09:30–13:30 ve 13:30–16:00 dilimleri."""
    h = h1[(h1.index.hour * 60 + h1.index.minute >= 570) & (h1.index.hour < 16)]
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    g = h.resample("4h", origin="start_day", offset="9h30min").agg(agg).dropna(subset=["Close"])
    bitis = pd.Series([min(t + pd.Timedelta(hours=4), t.normalize() + pd.Timedelta(hours=16)) for t in g.index], index=g.index)
    return g[bitis <= simdi_et + pd.Timedelta(minutes=2)]


def abd_bilanco_riski(f):
    try:
        import yfinance as yf, bist_abd as AB
        e = yf.Ticker(AB.yahoo(f["kod"])).get_earnings_dates(limit=8)
        if e is None or not len(e): return
        bugun = pd.Timestamp.now(tz="UTC").normalize()
        gelecek = sorted(t for t in pd.to_datetime(e.index, utc=True) if t >= bugun)
        if gelecek:
            gun = (gelecek[0].normalize() - bugun).days
            if gun <= 7: f["risk"].append(f"Bilanço {gun} gün içinde ({gelecek[0]:%d.%m}); bilanço sonrası açılış boşluğu riski")
    except Exception:
        pass


def abd(slot, zorla):
    import bist_abd as AB
    simdi_et = pd.Timestamp(dt.datetime.now(ET).replace(tzinfo=None))
    dk = simdi_et.hour * 60 + simdi_et.minute
    if not zorla:
        if simdi_et.weekday() >= 5: log("ABD: hafta sonu, atlandı."); return
        if slot == "abd-ogle" and not (13 * 60 + 32 <= dk < 16 * 60): log(f"ABD öğle turu için saat uygun değil ({simdi_et:%H:%M} ET)."); return
        if slot == "abd-kapanis" and dk < 16 * 60 + 10: log(f"ABD piyasası henüz kapanmadı ({simdi_et:%H:%M} ET)."); return
    bot = tg.Bot("abd"); D = Durum("abd")
    if slot == "abd-kapanis" and not zorla:
        if D.islenen.get("kapanis_gun") == str(simdi_et.date()):
            log("ABD kapanış turu bugün zaten yapıldı (yaz/kış saati için iki zamanlama var)."); return
        D.islenen["kapanis_gun"] = str(simdi_et.date())
    # likit evren: kapanış turunda yeniden hesaplanır, öğle turunda kayıtlıdan okunur
    evren_yol = os.path.join(D.kok, "evren.csv")
    analizler = None; r = None
    if slot == "abd-kapanis":
        r = TB.calistir("abd", klasor=CIKTI, zorla=zorla)
        if TB.ABD_EVREN is not None:
            TB.ABD_EVREN.to_csv(evren_yol, index=False)
            try: shutil.copy(AB.LISTE_DOSYA, os.path.join(D.kok, "abd_listesi.csv"))
            except Exception: pass
        analizler = (TB.SON.get("abd") or {}).get("analizler")
    if not os.path.exists(AB.LISTE_DOSYA) and os.path.exists(os.path.join(D.kok, "abd_listesi.csv")):
        shutil.copy(os.path.join(D.kok, "abd_listesi.csv"), AB.LISTE_DOSYA)   # şirket adları için
    try: kodlar = list(pd.read_csv(evren_yol)["Kod"])
    except Exception:
        lk, _ = AB.likit_hisseler(); lk.to_csv(evren_yol, index=False); kodlar = list(lk["Kod"])
    acik_kod = {k["kod"] for k in D.acik}
    log(f"ABD: {len(kodlar)} likit hisse için saatlik veri indiriliyor…")
    ham = yahoo_saatlik([AB.yahoo(k) for k in list(kodlar) + list(acik_kod)], "America/New_York")
    h1 = {AB.kod_yap(s_): d for s_, d in ham.items()}
    log(f"Saatlik veri: {len(h1)} hisse")
    olay = takip_et(D, lambda k: h1.get(k["kod"]), simdi_et)
    h4 = {k: abd_4s(d, simdi_et) for k, d in h1.items()}
    son = max((d.index[-1] for d in h4.values() if len(d)), default=None)
    if son is not None and (zorla or simdi_et - son <= pd.Timedelta(hours=7)):
        V_ = [{"kod": k, "ad": AB.ad(k), "para": "$", "a": F.hafif(d, "4S"), "ust_fn": (lambda hh=h1[k]: ust_gunluk(hh, "hisse"))}
              for k, d in h4.items() if len(d) >= 80 and d.index[-1] == son]
        firsat_turu(bot, D, "4S", V_, ekstra_fn=abd_bilanco_riski)
    if r and analizler:
        likit = set(kodlar)
        for tf_ in ("G", "H"):
            try: REJIM[("abd", tf_)] = F.rejim(TB.SON["abd"]["endeks"]["tf"][tf_]["h"])
            except Exception as ex: log(f"S&P 500 {tf_} yönü:", ex)
        gunluk_tf_turu(bot, D, analizler, ("G", "H", "A"), zorla, False, lambda s: "$", lambda s: s["kod"] in likit, ekstra_fn=abd_bilanco_riski)
        TB.telegram_gonder("abd", *r, klasor=CIKTI, bot=bot)
        rejim_turu("abd", analizler, TB.SON["abd"]["endeks"], bot)
    if olay: takip_mesaji(bot, D)
    bot.bag_guncelle([k["id"] for k in D.acik])
    D.kaydet(); bot.kaydet()


# ====================================================================== haftalık karne
def karne_mesaji(bot, D_kripto):
    import kart as KT
    C = KT.C; t = dt.datetime.now(UTC); satir = ["📒 <b>HAFTALIK FIRSAT KARNESİ</b>", tg.AYRAC]; kart_s = []
    for p in ("bist", "abd", "kripto", "emtia"):
        if p == "kripto": gec = D_kripto.gecmis; acik = D_kripto.acik
        else:
            try:
                gec = json.load(open(os.path.join(KLON, "firsat", p, "gecmis.json"), encoding="utf-8"))
                acik = json.load(open(os.path.join(KLON, "firsat", p, "acik.json"), encoding="utf-8"))
            except Exception:
                gec, acik = [], []
        hafta = [k for k in gec if k.get("kapanis") and _utc(k) >= t - dt.timedelta(days=7)]
        ph, pt = F.performans(hafta), F.performans(gec)
        if ph:
            alt = f"7 günde {ph['n']} kapanan · ilk hedefe ulaşma %{ph['h1'] * 100:.0f} · kazanan %{ph['kazanc'] * 100:.0f} · toplam {F.rrs(ph['top_R'])}"
            sag, sr = F.rrs(ph["ort_R"]), (C["yesil"] if ph["ort_R"] >= 0 else C["kirmizi"])
        else:
            alt, sag, sr = "Son 7 günde kapanan kurulum yok", "–", C["soluk"]
        if pt: alt += f" · başlangıçtan beri {pt['n']} kurulum, ort. {F.rrs(pt['ort_R'])}"
        kart_s.append({"sol": f"{PIYASA_AD[p]} · açık {len(acik)}", "sag": sag, "sag_renk": sr, "nokta": sr, "alt": alt})
        satir.append(f"• <b>{PIYASA_AD[p]}</b>: {alt} · ort. {sag}")
    satir.append("\n<i>R: stop mesafesi kadar risk birimi.</i>")
    kart_gonder(bot, "karne", 46.5, "HAFTALIK FIRSAT KARNESİ", "Sistem nasıl performans gösterdi?", f"{t.astimezone(TSI):%d.%m.%Y} itibarıyla",
                [{"baslik": "Piyasalara göre", "renk": C["altin"], "satirlar": kart_s}], f"📈 <b>Haftalık fırsat karnesi</b> · {t.astimezone(TSI):%d.%m.%Y}", "altin",
                not_="R: stop mesafesi kadar risk birimi. +1R, riske edilen tutar kadar kazanç; −1R, stop olunca kaybedilen tutardır. "
                     "Ortalama R sıfırın üzerindeyse sistem uzun vadede kazandırıyor demektir.", yedek="\n".join(satir))


def _utc(k):
    """Kapanış zamanı (kayıt saat diliminde) → yaklaşık UTC."""
    z = pd.Timestamp(k["kapanis"])
    if k["piyasa"] == "bist": z = z - pd.Timedelta(hours=3)
    return z.to_pydatetime().replace(tzinfo=UTC)


def hedef_zaman(slot, simdi_utc):
    """Zamanlanmış işin veriyi beklemesi gereken an (UTC). GitHub zamanlanmış işleri 5–40 dk gecikmeli başlatabildiği için
    iş akışları kapanıştan önce başlar ve burada bekler; geç başlarsa beklemeden çalışır."""
    u = pd.Timestamp(simdi_utc).tz_convert("UTC") if pd.Timestamp(simdi_utc).tzinfo else pd.Timestamp(simdi_utc).tz_localize("UTC")
    def tsi(saat, dk): return (pd.Timestamp(u.tz_convert("Europe/Istanbul").date(), tz="Europe/Istanbul") + pd.Timedelta(hours=saat, minutes=dk)).tz_convert("UTC")
    def et(saat, dk): return (pd.Timestamp(u.tz_convert("America/New_York").date(), tz="America/New_York") + pd.Timedelta(hours=saat, minutes=dk)).tz_convert("UTC")
    def sinir4(ek):   # en yakın 4 saatlik sınır (geç başladıysa geçmiş sınır) + ek dakika
        s = u.floor("4h")
        if u - s > pd.Timedelta(minutes=45): s = s + pd.Timedelta(hours=4)
        return s + pd.Timedelta(minutes=ek)
    return {"bist-ogle": lambda: tsi(14, 17), "bist-kapanis": lambda: tsi(18, 26), "kripto": lambda: sinir4(2),
            "emtia-4s": lambda: sinir4(12), "emtia-kapanis": lambda: (u.normalize() + pd.Timedelta(hours=22, minutes=12)),
            "abd-ogle": lambda: et(13, 34), "abd-kapanis": lambda: et(16, 12), "sabah": lambda: tsi(9, 0)}[slot]()


def bekle(slot, sinir_dk=130):
    simdi = pd.Timestamp.now(tz="UTC"); h = hedef_zaman(slot, simdi)
    sn = (h - simdi).total_seconds()
    if 0 < sn <= sinir_dk * 60:
        log(f"{slot}: veri için {h.tz_convert('Europe/Istanbul'):%H:%M} TSİ bekleniyor ({sn / 60:.0f} dk)…"); time.sleep(sn)
    else:
        log(f"{slot}: beklemeden çalışılıyor (hedef {h.tz_convert('Europe/Istanbul'):%H:%M} TSİ).")


class _Kayit:
    """Hata olsa bile durum ve Telegram defteri kaydedilsin (gönderilen mesajlar silinebilsin)."""
    nesneler = []


_eski_bot, _eski_durum = tg.Bot.__init__, Durum.__init__
def _bot_init(self, *a, **k): _eski_bot(self, *a, **k); _Kayit.nesneler.append(self)
def _durum_init(self, *a, **k): _eski_durum(self, *a, **k); _Kayit.nesneler.append(self)
tg.Bot.__init__, Durum.__init__ = _bot_init, _durum_init


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "bekle":
        bekle(sys.argv[2]); sys.exit(0)
    slot = sys.argv[1] if len(sys.argv) > 1 else ""
    zorla = "--zorla" in sys.argv
    ZORLA = zorla
    os.makedirs(CIKTI, exist_ok=True)
    try:
        if slot in ("bist-ogle", "bist-kapanis"): bist(slot, zorla)
        elif slot == "kripto": kripto(zorla)
        elif slot in ("emtia-4s", "emtia-kapanis"): emtia(slot, zorla)
        elif slot in ("abd-ogle", "abd-kapanis"): abd(slot, zorla)
        else: sys.exit(__doc__)
    except Exception:
        import traceback; traceback.print_exc()
        for n in _Kayit.nesneler:
            try: n.kaydet()
            except Exception: pass
        sys.exit(1)
