"""10b entegrasyon: teknik analiz karnesi + PDF."""
import os
import bist_teknik as T, bist_teknik_rapor as TR
os.makedirs("denetim_graf", exist_ok=True)
for kod in ("BTC/USDT", "NVDA.US", "THYAO"):
    s = T.analiz(kod)
    g = s["tf"]["G"]
    qd = [d for d in g["durum"] if "QuantDinger" in d[2]]
    print(kod, s["tur"], "QD satırı:", [(d[0], d[1]) for d in qd], "| taze QD sinyal:", [x[0] for x in g["sinyal"] if x[0].startswith("QD:")])
    try:
        f = TR.teknik_pdf(s, "denetim_graf/" + kod.replace("/", "_") + ".pdf") if hasattr(TR, "teknik_pdf") else None
        print("  PDF:", f)
    except Exception as ex:
        print("  PDF hata:", ex)
print([n for n in dir(TR) if "pdf" in n.lower() or "rapor" in n.lower()][:10])
