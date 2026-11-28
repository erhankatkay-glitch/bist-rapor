import os, sys, json, urllib.request, pandas as pd
sys.path.insert(0, ".")
os.makedirs("denetim_graf", exist_ok=True)
import kart as K, alarm as A
R = "https://raw.githubusercontent.com/erhankatkay-glitch/bist-rapor/bulten/"
for pz, ad in [("bist", "BIST"), ("abd", "ABD")]:
    meta = json.load(urllib.request.urlopen(R + f"{pz}/meta.json")); satir = pd.read_csv(R + f"{pz}/ozet.csv").to_dict("records")
    K.bulten_karti(meta, satir, f"denetim_graf/bulten_{pz}.png", ad); print("bulten", pz)
msj = ["🟢 SOL/USDT: Alçalan kama – YUKARI KIRILIM (günlük, 28.11) · fiyat 71,78 (+%0,2)", "🔴 ASELS: AB=CD (ayı) (günlük, 27.11) · fiyat 332,00 (+%5,4)",
       "🔴 NVDA (Nvidia): Ölüm kesişimi (günlük, 27.11) · fiyat 150,62 (+%0,9)", "⚡ THYAO bugün +%1,4 hareket etti (fiyat 314,00)"]
sat = [A._satir(m) for m in msj]
for _, sx, _u in sat:
    lk = A._logo_kod(sx.get("sol", ""))
    if lk: sx["logo"] = lk
bol = [{"baslik": a, "renk": K.C[r], "satirlar": [x[1] for x in sat if x[0] == g]} for g, a, r in A.GRUP_KART]
K.bildirim_karti("ALARMLAR · 28.11 12:30", "4 yeni alarm", "Fiyat, formasyon ve şirket haberleri", [x for x in bol if x["satirlar"]], "denetim_graf/alarm.png")
import logolar as LG
for k, p in [("ASELS", "bist"), ("NVDA.US", "abd"), ("THYAO", "bist"), ("BTC/USDT", "kripto")]: print("LOGO", k, LG.logo_dosya(k, p))
