"""Aşama 10b: canlı fırsat motoru kuru çalışma — QD kurulumları tetikleniyor mu, plan doğru mu (gönderim yok)."""
import time, collections
import bist_teknik as T, firsat as F
ABD = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM", "V", "MA", "UNH", "HD", "PG", "XOM", "CVX", "KO", "PEP", "COST",
       "WMT", "BAC", "AVGO", "ORCL", "CRM", "AMD", "NFLX", "ADBE", "INTC", "CSCO", "QCOM", "TXN", "NKE", "MCD", "DIS", "BA", "CAT", "GE",
       "IBM", "GS", "MS", "LLY"]
t0 = time.time(); v = []
for k in ABD:
    try:
        h, _ = T.gunluk_veri(k + ".US"); h = h.iloc[-1600:]
        v.append({"kod": k + ".US", "ad": k, "para": "$", "a": F.hafif(h, "G"), "ust": T.tf_analiz(T.yeniden_ornekle(h, "H"), "H")})
    except Exception as ex:
        print("veri yok", k, ex)
print(len(v), "hisse veri", round(time.time() - t0), "sn"); t1 = time.time()
sec, aday, pist = F.tara(v, "G", "abd", yonler=(1,), adet=5)
print("tarama", round(time.time() - t1), "sn ·", len(aday), "aday,", len(sec), "seçilen")
qd = {k: s for k, s in pist.__dict__.items()} if hasattr(pist, "__dict__") else {}
for ad_, d in qd.items():
    if isinstance(d, dict):
        for kk, s in d.items():
            if "QD:" in str(kk): print("  geçmiş olay", kk, (len(s) if hasattr(s, "__len__") else s))
say = collections.Counter(f["kurulum_ad"] for f in aday)
print("aday kurulumları:", say.most_common(12))
for f in aday:
    if any(q["baslik"] in f["kurulum_ad"] for q in F.QD_KABUL["abd|G"]):
        p = f["plan"]; print("  QD:", f["kod"], f["kurulum_ad"], "puan", f["puan"], "beklenenR", f["beklenen_R"], "giriş", round(p["giris"], 2), "stop", round(p["stop"], 2))
# son 60 günde QD tetik sayısı (canlı gösterim için)
import numpy as np
for q in F.QD_KABUL["abd|G"]:
    n = 0
    for x in v:
        A = F.diziler(x["a"]["h"], x["a"]["G"]); M = F.ayna(A, 1); m, _ = F.qd_tetik(x["a"]["h"], M, q, 1); n += int(m[-60:].sum())
    print(f"  son 60 gün {q['ad']:28s} tetik {n}")
