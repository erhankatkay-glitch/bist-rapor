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
    for k in sorted(bv.tum_sirketler()):
        try:
            yeni.append({"tarih": gun, "kod": k, "oran": isy.yabanci_orani(k)})
        except Exception as ex:
            print(f"yabancı {k}: {ex}", file=sys.stderr)
        time.sleep(0.3)
    df = pd.concat([eski, pd.DataFrame(yeni)]).drop_duplicates(["tarih", "kod"], keep="last")
    df["tarih"] = pd.to_datetime(df["tarih"])
    df = df[df["tarih"] >= pd.Timestamp(gun) - pd.Timedelta(days=400)].sort_values(["kod", "tarih"])
    df["tarih"] = df["tarih"].dt.strftime("%Y-%m-%d")
    df.to_csv(yol, index=False)
    print(f"Yabancı oranı kaydedildi: {len(yeni)} hisse")

def tum_liste():
    """Güncel tüm BIST hisseleri; depodaki hisse_listesi.csv'yi de günceller."""
    import bist_veri as bv, bist_evren as EV
    try:
        df, harz, not_ = EV.bist_listesi()
        if len(df) > 300: EV.liste_kaydet(df)
        print("Hisse listesi:", len(df), "·", not_, "· XHARZ:", len(harz))
        return sorted(df["Kod"])
    except Exception as ex:
        print("Tam liste alınamadı:", ex, file=sys.stderr)
        return sorted(bv.tum_sirketler())

def piyasa_taramasi(gun, kodlar=None):
    """Tüm BIST hisselerini tarar; fırsat skoru ve sektör özetiyle raporlar/tarama.csv'ye yazar."""
    import bist_veri as bv
    satirlar, hatalar = br.tara(kodlar or sorted(bv.tum_sirketler()), isci=6)
    df = pd.DataFrame(satirlar)
    df.insert(0, "tarih", gun)
    df.to_csv(os.path.join("raporlar", "tarama.csv"), index=False)
    print(f"Piyasa taraması: {len(satirlar)} hisse, {len(hatalar)} hata")

def main():
    kodlar = [s.strip().upper() for s in open("takip_listesi.txt", encoding="utf-8")
              if s.strip() and not s.strip().startswith("#")]
    gun = dt.date.today().isoformat()
    os.makedirs("raporlar", exist_ok=True)
    anahtar = os.environ.get("EVDS_KEY")
    if anahtar:  # varsayımları TCMB verisiyle güncelle
        try:
            import bist_makro as mk
            evds, _ = mk.evds_paneli(anahtar)
            prm = mk.oto_varsayim(evds)
            br.PARAM.update({k.upper(): v for k, v in prm.items()})
            print("EVDS varsayımları:", prm)
        except Exception as ex:
            print(f"EVDS okunamadı: {ex}", file=sys.stderr)
    try:
        tum_liste()                  # tüm BIST listesini güncelle (hisse_listesi.csv)
        yabanci_kaydet(gun)          # önce yabancı oranları (rapor ve tarama bunları kullanır)
    except Exception as ex:
        print(f"Yabancı oranı kaydı başarısız: {ex}", file=sys.stderr)
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
    for eski in sorted(glob.glob("raporlar/20*"))[:-5]:  # yalnızca tarihli klasörler
        shutil.rmtree(eski, ignore_errors=True)
    print(f"{len(satirlar)}/{len(kodlar)} rapor üretildi → {klasor}")
    try:
        piyasa_taramasi(gun)
    except Exception as ex:
        print(f"Piyasa taraması başarısız: {ex}", file=sys.stderr)

if __name__ == "__main__":
    main()
