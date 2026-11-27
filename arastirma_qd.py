"""Aşama 10b: QuantDinger gösterge kütüphanesinin sıkı geçmiş testi. Hiçbir şey göndermez.

Kullanım (iş akışı qd_arastirma.yml):
  python arastirma_qd.py olay  <pazar> <parça> <parça_sayısı>   → qd_olay_<pazar>_<parça>.csv (+ parça 0'da taban)
  python arastirma_qd.py ozet  <pazar>                           → qd_sonuc_<pazar>.json
pazar: bistg | abdg | kriptog | kripto4s

Yöntem (çok sayıda kural denendiğinde şans eseri iyi görünenleri elemek için):
  1. Her gösterge varsayılan ayarlarıyla çalışır (ayar taraması yok → aşırı uyum riski düşük).
  2. Her AL/SAT olayı fırsat motorunun simülasyonuyla (firsat.simule) R cinsinden ölçülür: giriş sinyal mumunun kapanışı,
     stop 2 ATR, hedefler 1R/2R/3R, süre sınırı motorla aynı.
  3. Kıyas tabanı: AYNI GÜN aynı piyasadaki rastgele bir varlığa aynı kuralla girilseydi alınacak R (tarih eşlemeli Monte Carlo,
     2000 tekrar). Böylece boğa piyasasında "her şey kazandırıyor" etkisi ayıklanır. p değeri tek yönlüdür.
  4. Veri zamana göre bölünür: ilk %80 geliştirme (4 ardışık parça = ileriye yürüyen kontrol), son %20 KÖR dönem.
     Seçim yalnız geliştirme dönemine bakar; kör dönem en sonda tek sefer kontrol edilir.
  5. Çoklu deneme düzeltmesi: piyasa içindeki tüm gösterge×yön testlerine Benjamini-Hochberg (q = 0,10).
  6. Gerçek zaman (boyama) testi: ZigZag/pivot/emir bloğu gibi göstergeler sinyali geriye dönük (dönüş mumuna) yazabilir;
     tam veriyle test geleceği görür. Her gösterge, olay mumuna KADARKİ veriyle de çalıştırılır: tam veride t mumunda olan
     sinyal, yalnız t'ye kadarki veriyle çalışınca da t'de çıkıyor mu? Eşleşme < %95 ise gösterge elenir.
  Kabul: boyama yok · BH anlamlı · fazla R ≥ +0,05 · 4 parçanın en az 3'ünde tabanı geçiyor · kör dönemde n ≥ 20, ortalama R > 0
  ve tabanı geçiyor.
"""
import sys, os, glob, json, time
import numpy as np
import pandas as pd
import bist_teknik as T
import firsat as F
import qd_calistir as Q
import arastirma_firsat as AF

STOP_ATR = 2.0
RLER = (1.0, 2.0, 3.0)
KAYNAK = os.environ.get("QD_KAYNAK", "qd")       # "qd": QuantDinger betikleri · "10c": yerli VCP/MOMENTUM/EP kurulumları
YERLI = ["VCP", "MOMENTUM", "EP"]


def kaynak_listesi():
    return [f"10c:{k}" for k in YERLI] if KAYNAK == "10c" else Q.betikler()


def kaynak_ad(b):
    return b[4:] if b.startswith("10c:") else Q.ad(b)


def kaynak_sinyal(b, d):
    """→ ((al_idx, sat_idx), {(yon, t): kurulumun kendi stopu (aynalı)} ya da None)."""
    if not b.startswith("10c:"): return Q.sinyaller(b, d), None
    k = b[4:]; G = T.gostergeler(d); A = F.diziler(d, G); idx = []; stoplar = {}
    for y in (1, -1):
        m, st = F.tetikler(F.ayna(A, y), ek={k})[k]
        ii = np.flatnonzero(m); idx.append(ii)
        for t in ii: stoplar[(y, int(t))] = float(st[t])
    return (idx[0], idx[1]), stoplar


PZ = {"bistg": "G", "abdg": "G", "kriptog": "G", "kripto4s": "4S"}


def log(*a):
    print(*a, flush=True)


def veri_al(pazar):
    genis = KAYNAK == "10c"          # nadir kurulumlar (VCP, EP) için daha geniş evren
    if pazar == "bistg": return AF.bist_veri(400 if genis else 120)
    if pazar == "abdg": return AF.abd_veri(200 if genis else 120)
    if pazar == "kriptog": return AF.kripto_veri("1d", 60)
    if pazar == "kripto4s": return AF.kripto_veri("4h", 60)
    raise SystemExit("pazar?")


def hazirla(veri, tf):
    """Her varlık için motor dizileri ve iki yönün aynalanmış hali."""
    out = {}
    for kod, d in veri.items():
        try:
            G = T.gostergeler(d); A = F.diziler(d, G)
        except Exception as ex:
            log("gösterge", kod, ex); continue
        n = len(A["Close"]); bas = max(220, n - F.GECMIS_BAR)
        yon = {}
        for y in (1, -1):
            M = F.ayna(A, y)
            yon[y] = (M["High"].tolist(), M["Low"].tolist(), M["Close"].tolist(), M["Open"].tolist(), np.asarray(M["ATR"], float))
        out[kod] = (d, n, bas, yon)
    return out


def olc(yon_dizi, t, tf, stop=None):
    H, L, C, O, at = yon_dizi
    if not np.isfinite(at[t]) or at[t] <= 0: return None
    if stop is None or not np.isfinite(stop): stop = C[t] - STOP_ATR * at[t]
    if (C[t] - stop) / abs(C[t]) > F.MAKS_RISK[tf]: return None
    return F.simule(H, L, C, t, C[t], stop, RLER, F.MAKS_BAR[tf], O)


def olay(pazar, parca, toplam):
    tf = PZ[pazar]; t0 = time.time()
    veri, onder = veri_al(pazar)
    V = hazirla({k: d for k, d in veri.items() if k != onder}, tf)
    log(f"{pazar}: {len(V)} varlık, veri {time.time() - t0:.0f} sn")
    if parca == 0:   # tarih eşlemeli taban: her mumda girilseydi
        tb = []
        for kod, (d, n, bas, yon) in V.items():
            for y in (1, -1):
                for t in range(bas, n - 1):
                    s = olc(yon[y], t, tf)
                    if s: tb.append((kod, d.index[t], y, round(s[0], 4)))
        pd.DataFrame(tb, columns=["kod", "zaman", "yon", "R"]).to_csv(f"qd_taban_{pazar}.csv", index=False)
        log(f"taban {len(tb)} olay, {time.time() - t0:.0f} sn")
    betik = [b for i, b in enumerate(kaynak_listesi()) if i % toplam == parca]
    kayit = []
    for b in betik:
        t1 = time.time(); ad = kaynak_ad(b); say = 0; hata = 0
        for kod, (d, n, bas, yon) in V.items():
            try:
                r, stoplar = kaynak_sinyal(b, d)
            except Exception:
                hata += 1
                if hata >= 3: break
                continue
            if r is None: break
            for y, idx in ((1, r[0]), (-1, r[1])):
                for t in idx:
                    if t < bas or t >= n - 1: continue
                    s = olc(yon[y], int(t), tf, (stoplar or {}).get((y, int(t))))
                    if s: kayit.append((ad, kod, d.index[int(t)], y, round(s[0], 4), s[1])); say += 1
            if time.time() - t1 > 900: log("  süre sınırı", ad); break
        log(f"  {ad:42s} olay {say:6d}  hata {hata}  {time.time() - t1:5.1f} sn")
    pd.DataFrame(kayit, columns=["gosterge", "kod", "zaman", "yon", "R", "asama"]).to_csv(f"qd_olay_{pazar}_{parca}.csv", index=False)
    log(f"bitti {time.time() - t0:.0f} sn")


def boyama(parca, toplam):
    """Göstergelerin gerçek zaman uyumu: tam veri olaylarının, yalnız o mumdaki veriye kadar çalıştırıldığında da çıkma oranı."""
    import yfinance as yf
    v = yf.download(["THYAO.IS", "GARAN.IS", "AAPL", "MSFT", "BTC-USD"], period="6y", interval="1d", auto_adjust=True,
                    progress=False, group_by="ticker", threads=True)
    veri = {}
    for k in ("THYAO.IS", "GARAN.IS", "AAPL", "MSFT", "BTC-USD"):
        d = v[k].dropna(subset=["Close"]); d.index = d.index.tz_localize(None) if d.index.tz is not None else d.index
        veri[k] = d.tail(1200)
    rng = np.random.default_rng(11); out = {}
    for i, b in enumerate(kaynak_listesi()):
        if i % toplam != parca: continue
        ad = kaynak_ad(b); t1 = time.time(); es = top = fazla = rast = 0
        for k, d in veri.items():
            try:
                r = kaynak_sinyal(b, d)[0]
            except Exception:
                continue
            if r is None: break
            olay = sorted(set(r[0].tolist()) | set(r[1].tolist()))
            olay = [t for t in olay if 300 <= t < len(d) - 1]
            sec = list(rng.choice(olay, min(12, len(olay)), replace=False)) if olay else []
            bos = [t for t in rng.integers(300, len(d) - 1, 8) if t not in olay]
            for t in sec + bos:
                try:
                    p = kaynak_sinyal(b, d.iloc[:t + 1])[0]
                except Exception:
                    continue
                son = p is not None and (t in set(p[0].tolist()) | set(p[1].tolist()))
                if t in olay:
                    top += 1; es += son
                else:
                    rast += 1; fazla += son
            if time.time() - t1 > 400: break
        out[ad] = {"olay_test": top, "eslesme": round(es / top, 3) if top else None, "bos_test": rast, "fazla": fazla}
        log(f"  {ad:42s} eşleşme {es}/{top}  boşta sinyal {fazla}/{rast}  {time.time() - t1:5.1f} sn")
    json.dump(out, open(f"qd_boya_{parca}.json", "w"), ensure_ascii=False, indent=1)


# ------------------------------------------------------------------ istatistik
def bh(p, q=0.10):
    p = np.asarray(p, float); m = len(p)
    if not m: return np.zeros(0, bool)
    sira = np.argsort(p); esik = q * (np.arange(1, m + 1) / m)
    gec = p[sira] <= esik
    k = np.max(np.flatnonzero(gec)) + 1 if gec.any() else 0
    sonuc = np.zeros(m, bool); sonuc[sira[:k]] = True
    return sonuc


def taban_havuz(tb):
    """(yon, zaman) → R dizisi (tarih eşlemeli rastgele giriş havuzu)."""
    return {k: g["R"].to_numpy(float) for k, g in tb.groupby(["yon", "zaman"])}


def monte_carlo(olaylar, havuz, yon, tekrar=2000, rng=None):
    """Olayların ortalama R'si, aynı günlerde rastgele girişlerin ortalamasından büyük mü? → (taban ort., p)."""
    rng = rng or np.random.default_rng(7)
    parcalar = [havuz.get((yon, z)) for z in olaylar["zaman"]]
    tut = [i for i, x in enumerate(parcalar) if x is not None and len(x)]
    if len(tut) < 10: return np.nan, 1.0
    R = olaylar["R"].to_numpy(float)[tut]
    boy = np.array([len(parcalar[i]) for i in tut]); bas = np.concatenate(([0], np.cumsum(boy)[:-1]))
    hepsi = np.concatenate([parcalar[i] for i in tut])
    sim = np.empty(tekrar)
    for j in range(0, tekrar, 250):
        u = rng.random((min(250, tekrar - j), len(tut)))
        sim[j:j + len(u)] = hepsi[bas + (u * boy).astype(int)].mean(axis=1)
    return float(sim.mean()), float((1 + (sim >= R.mean()).sum()) / (tekrar + 1))


def ozet(pazar):
    tb = pd.read_csv(f"qd_taban_{pazar}.csv", parse_dates=["zaman"])
    ol = pd.concat([pd.read_csv(f, parse_dates=["zaman"]) for f in sorted(glob.glob(f"qd_olay_{pazar}_*.csv"))], ignore_index=True)
    tarihler = np.sort(tb["zaman"].unique())
    kor_bas = tarihler[int(len(tarihler) * 0.8)]
    gel = tarihler[tarihler < kor_bas]; sinir = [gel[int(len(gel) * k / 4)] for k in range(1, 4)]
    havuz = taban_havuz(tb)
    log(f"{pazar}: {ol['gosterge'].nunique()} gösterge, {len(ol)} olay; kör dönem {pd.Timestamp(kor_bas):%Y-%m-%d} sonrası")
    satirlar = []
    for (g, y), x in ol.groupby(["gosterge", "yon"]):
        dev = x[x["zaman"] < kor_bas]; kor = x[x["zaman"] >= kor_bas]
        if len(dev) < 50: continue
        tab, p = monte_carlo(dev, havuz, y)
        parca_ok = 0
        for a, b in zip([gel[0]] + sinir, sinir + [kor_bas]):
            dp = dev[(dev["zaman"] >= a) & (dev["zaman"] < b)]
            if len(dp) >= 10:
                tp, _ = monte_carlo(dp, havuz, y, tekrar=200)
                if dp["R"].mean() > tp: parca_ok += 1
        ktab, kp = monte_carlo(kor, havuz, y, tekrar=1000) if len(kor) >= 10 else (np.nan, 1.0)
        satirlar.append({"gosterge": g, "yon": int(y), "n": len(dev), "ortR": round(dev["R"].mean(), 4), "taban": round(tab, 4),
                         "fazla": round(dev["R"].mean() - tab, 4), "p": p, "p1": round(float((dev["asama"] >= 1).mean()), 3),
                         "parca_ok": parca_ok, "kor_n": len(kor), "kor_ortR": round(kor["R"].mean(), 4) if len(kor) else None,
                         "kor_fazla": round(kor["R"].mean() - ktab, 4) if len(kor) >= 10 else None, "kor_p": kp})
    S = pd.DataFrame(satirlar)
    boya = {}
    for f in glob.glob("qd_boya_*.json"): boya.update(json.load(open(f, encoding="utf-8")))
    S["eslesme"] = S["gosterge"].map(lambda g: (boya.get(g) or {}).get("eslesme"))
    S["boyamasiz"] = S["gosterge"].map(lambda g: bool((boya.get(g) or {}).get("olay_test", 0) >= 10 and boya[g]["eslesme"] >= 0.95
                                                       and boya[g]["fazla"] <= max(1, 0.1 * boya[g]["bos_test"])))
    log(f"boyama testi: {len(boya)} gösterge, boyamasız {sum(1 for g in boya.values() if g.get('olay_test', 0) >= 10 and g['eslesme'] >= 0.95)}")
    S["bh"] = bh(S["p"].to_numpy())
    S["kabul"] = (S["boyamasiz"] & S["bh"] & (S["fazla"] >= 0.05) & (S["parca_ok"] >= 3) & (S["kor_n"] >= 20)
                  & (S["kor_ortR"].fillna(-1) > 0) & (S["kor_fazla"].fillna(-1) > 0))
    S = S.sort_values(["kabul", "fazla"], ascending=False)
    log(f"\n{len(S)} test · BH anlamlı {int(S['bh'].sum())} · KABUL {int(S['kabul'].sum())}")
    with pd.option_context("display.width", 220, "display.max_rows", 80):
        log(S.head(40).to_string(index=False))
    taban_ort = {int(y): round(float(g["R"].mean()), 4) for y, g in tb[tb["zaman"] < kor_bas].groupby("yon")}
    json.dump({"pazar": pazar, "kor_bas": str(pd.Timestamp(kor_bas).date()), "taban_ort": taban_ort,
               "test": len(S), "bh": int(S["bh"].sum()), "kabul": S[S["kabul"]].to_dict("records"),
               "tum": S.to_dict("records")}, open(f"qd_sonuc_{pazar}.json", "w"), ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    if sys.argv[1] == "boya": boyama(int(sys.argv[2]), int(sys.argv[3]))
    elif sys.argv[1] == "olay": olay(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    else: ozet(sys.argv[2])
