"""10c-2 entegrasyon kontrolü (gönderim yok)."""
import os, numpy as np
import bist_teknik as T, bist_teknik_rapor as TR, firsat as F, tarayici as TRY
os.makedirs("denetim_graf", exist_ok=True)
for kod in ("NVDA.US", "TSLA.US", "THYAO", "SASA"):
    s = T.analiz(kod); g = s["tf"]["G"]
    print(kod, "karne:", [(d[0], d[1]) for d in g["durum"] if d[0] in ("Momentum patlaması", "Aşağı momentum patlaması", "Aşağı haber boşluğu")],
          "| sinyal:", [x[0] for x in g["sinyal"] if x[0].startswith("Kurulum:")])
    if kod == "NVDA.US":
        f = TR.teknik_pdf(s, "denetim_graf/NVDA.pdf")
        print("  PDF üretildi:", os.path.getsize(f) > 10000)  # "  PDF: momentum satırı", "Momentum patlaması" in t, "| sözlük VCP", "VCP (Minervini)" in t)
# son 250 günde kaç tetik (piyasada ne sıklıkla çıkıyor) + tarayıcı + motor geçmiş istatistiği
ABD = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD", "NFLX", "AVGO", "PLTR", "COIN", "SHOP", "UBER", "CRM", "ORCL", "INTC", "MU", "SMCI", "ARM"]
v = []; tet = 0
for k in ABD:
    h, _ = T.gunluk_veri(k + ".US"); h = h.iloc[-1600:]
    a = F.hafif(h, "G"); v.append({"kod": k + ".US", "ad": k, "para": "$", "a": a, "ust": T.tf_analiz(T.yeniden_ornekle(h, "H"), "H")})
    A = F.diziler(a["h"], a["G"]); m, _ = F.tetikler(A, ek={"MOMENTUM"})["MOMENTUM"]; tet += int(m[-250:].sum())
    x = TRY.son_sinyal(a["h"], a["G"], "abd", pencere=250)
print("ABD 20 hisse son 250 günde momentum tetiği:", tet)
sec, aday, pist = F.tara(v, "G", "abd", yonler=(1,), adet=5)
print("motor:", len(aday), "aday ·", [(f["kod"], f["kurulum_ad"][:40]) for f in aday[:6]])
for kk, s_ in pist.__dict__.items():
    if isinstance(s_, dict):
        for k2, val in s_.items():
            if "MOMENTUM" in str(k2): print("  geçmiş olay", k2, len(val) if hasattr(val, "__len__") else val)
# portföy SAT taraması (BIST): EP/MOMENTUM SAT varlik_tara ile
pv = []
for k in ("THYAO", "SASA", "ASELS", "HEKTS", "KONTR", "ASTOR", "PGSUS", "TUPRS"):
    h, _ = T.gunluk_veri(k); pv.append({"kod": k, "ad": k, "para": "₺", "a": F.hafif(h.iloc[-1600:], "G")})
say = 0
for x in pv:
    A = F.diziler(x["a"]["h"], x["a"]["G"]); M = F.ayna(A, -1)
    t_ = F.tetikler(M, ek=F.ek_kurulumlar("bist", "G", -1))
    say += sum(int(t_[k][0][-250:].sum()) for k in ("EP", "MOMENTUM") if k in t_)
print("BIST 8 hisse son 250 günde EP/MOMENTUM SAT tetiği:", say, "| açık:", sorted(F.ek_kurulumlar("bist", "G", -1)))
