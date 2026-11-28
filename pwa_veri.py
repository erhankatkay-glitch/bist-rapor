"""Hızlı uygulamanın (docs/) tam uygulamayla aynı sözlükleri kullanması için sabit veri dosyası üretir → docs/pwa_veri.json.
Ekonomik takvim Türkçe adları (ses.VERI, ses.ULKE) ve tarayıcı alanları / hazır taramalar (tarayici.ALANLAR, tarayici.HAZIR).
Bu sözlüklerden biri değişince yeniden çalıştırılır: python pwa_veri.py   (testler de güncelliğini denetler)."""
import json

import ses
import tarayici


def veri():
    return {"veri": [list(x) for x in ses.VERI], "ulke": ses.ULKE,
            "alanlar": {k: list(v) for k, v in tarayici.ALANLAR.items()}, "hazir": tarayici.HAZIR}


if __name__ == "__main__":
    json.dump(veri(), open("docs/pwa_veri.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("docs/pwa_veri.json yazıldı")
