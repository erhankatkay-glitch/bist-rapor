# -*- coding: utf-8 -*-
"""Hafta içi sabah raporları: takip_listesi.txt'deki hisseler için PDF + özet tablo üretir.
GitHub Actions tarafından çalıştırılır; son 5 günün raporları saklanır."""
import os, sys, glob, shutil, datetime as dt
import pandas as pd
import bist_rapor as br

def main():
    kodlar = [s.strip().upper() for s in open("takip_listesi.txt", encoding="utf-8")
              if s.strip() and not s.strip().startswith("#")]
    gun = dt.date.today().isoformat()
    klasor = os.path.join("raporlar", gun)
    os.makedirs(klasor, exist_ok=True)
    satirlar = []
    for k in kodlar:
        try:
            d, m, emsaller, endeks = br.analiz_et(k, log=print)
            br.pdf_olustur(d, m, emsaller, endeks, os.path.join(klasor, f"{k}_Arastirma_Raporu_{gun.replace('-', '')}.pdf"))
            satirlar.append(br.ozet_satir(m))
        except Exception as ex:
            print(f"{k} atlandı: {ex}", file=sys.stderr)
    pd.DataFrame(satirlar).to_csv(os.path.join(klasor, "ozet.csv"), index=False)
    for eski in sorted(glob.glob("raporlar/20*"))[:-5]:
        shutil.rmtree(eski, ignore_errors=True)
    print(f"{len(satirlar)}/{len(kodlar)} rapor üretildi → {klasor}")

if __name__ == "__main__":
    main()
