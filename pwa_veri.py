"""Hızlı uygulamanın (docs/) tam uygulamayla aynı sözlükleri kullanması için sabit veri dosyası üretir → docs/pwa_veri.json.
Ekonomik takvim Türkçe adları (ses.VERI, ses.ULKE), tarayıcı alanları / hazır taramalar (tarayici.ALANLAR, tarayici.HAZIR)
ve logo eşlemeleri (logolar.OZEL_ALAN: endeks / emtia borsaları, PARA_ULKE: döviz bayrakları).
Bu sözlüklerden biri değişince yeniden çalıştırılır: python pwa_veri.py   (testler de güncelliğini denetler)."""
import json

import logolar
import ses
import tarayici


def veri():
    return {"veri": [list(x) for x in ses.VERI], "ulke": ses.ULKE,
            "alanlar": {k: list(v) for k, v in tarayici.ALANLAR.items()}, "hazir": tarayici.HAZIR,
            "logo": {"token": logolar.LOGO_DEV, "ozel": logolar.OZEL_ALAN, "para": logolar.PARA_ULKE, "esle": logolar.ESLE}}


if __name__ == "__main__":
    json.dump(veri(), open("docs/pwa_veri.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("docs/pwa_veri.json yazıldı")
