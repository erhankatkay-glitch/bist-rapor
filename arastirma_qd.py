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
  Kabul: BH anlamlı · fazla R ≥ +0,05 · 4 parçanın en az 3'ünde tabanı geçiyor · kör dönemde n ≥ 20, ortalama R > 0
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
PZ = {"bistg": "G", "abdg": "G", "kriptog": "G", "kripto4s": "4S"}


def log(*a):
    print(*a, flush=True)


def veri_al(pazar):
    if pazar == "bistg": return AF.bist_veri(120)
    if pazar == "abdg": return AF.abd_veri(120)
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


def olc(yon_dizi, t, tf):
    H, L, C, O, at = yon_dizi
    if not np.isfinite(at[t]) or at[t] <= 0: return None
    stop = C[t] - STOP_ATR * at[t]
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
    betik = [b for i, b in enumerate(Q.betikler()) if i % toplam == parca]
    kayit = []
    for b in betik:
        t1 = time.time(); ad = Q.ad(b); say = 0; hata = 0
        for kod, (d, n, bas, yon) in V.items():
            try:
                r = Q.sinyaller(b, d)
            except Exception:
                hata += 1
                if hata >= 3: break
                continue
            if r is None: break
            for y, idx in ((1, r[0]), (-1, r[1])):
                for t in idx:
                    if t < bas or t >= n - 1: continue
                    s = olc(yon[y], int(t), tf)
                    if s: kayit.append((ad, kod, d.index[int(t)], y, round(s[0], 4), s[1])); say += 1
            if time.time() - t1 > 900: log("  süre sınırı", ad); break
        log(f"  {ad:42s} olay {say:6d}  hata {hata}  {time.time() - t1:5.1f} sn")
    pd.DataFrame(kayit, columns=["gosterge", "kod", "zaman", "yon", "R", "asama"]).to_csv(f"qd_olay_{pazar}_{parca}.csv", index=False)
    log(f"bitti {time.time() - t0:.0f} sn")


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
    S["bh"] = bh(S["p"].to_numpy())
    S["kabul"] = (S["bh"] & (S["fazla"] >= 0.05) & (S["parca_ok"] >= 3) & (S["kor_n"] >= 20)
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
    if sys.argv[1] == "olay": olay(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    else: ozet(sys.argv[2])
