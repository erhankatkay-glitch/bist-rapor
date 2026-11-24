# -*- coding: utf-8 -*-
"""Hafta içi sabah raporları: takip_listesi.txt'deki hisseler için PDF + özet tablo üretir.
GitHub Actions tarafından çalıştırılır; son 5 günün raporları saklanır."""
import os, sys, glob, shutil, datetime as dt
import pandas as pd
import bist_rapor as br

def yabanci_kaydet(gun):
    """Tüm listedeki hisselerin günlük yabancı oranını raporlar/yabanci_oran.csv'ye ekler (geçmiş birikir)."""
    import time
    import bist_veri as bv, bist_isyatirim as isy
    yol = os.path.join("raporlar", "yabanci_oran.csv")
    eski = pd.read_csv(yol) if os.path.exists(yol) else pd.DataFrame(columns=["tarih", "kod", "oran"])
    yeni = []
    for k in sorted(bv.SIRKETLER):
        try:
            yeni.append({"tarih": gun, "kod": k, "oran": isy.yabanci_orani(k)})
        except Exception as ex:
            print(f"yabancı {k}: {ex}", file=sys.stderr)
        time.sleep(0.5)
    df = pd.concat([eski, pd.DataFrame(yeni)]).drop_duplicates(["tarih", "kod"], keep="last")
    df["tarih"] = pd.to_datetime(df["tarih"])
    df = df[df["tarih"] >= pd.Timestamp(gun) - pd.Timedelta(days=400)].sort_values(["kod", "tarih"])
    df["tarih"] = df["tarih"].dt.strftime("%Y-%m-%d")
    df.to_csv(yol, index=False)
    print(f"Yabancı oranı kaydedildi: {len(yeni)} hisse")

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
    yabanci_kaydet(gun)
    for eski in sorted(glob.glob("raporlar/20*"))[:-5]:  # yabanci_oran.csv bu desene girmez
        shutil.rmtree(eski, ignore_errors=True)
    print(f"{len(satirlar)}/{len(kodlar)} rapor üretildi → {klasor}")

if __name__ == "__main__":
    main()
