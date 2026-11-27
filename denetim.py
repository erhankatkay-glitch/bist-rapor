"""1) Tarama tablolarını üret ve yayınla  2) Telegram kartlarını göndermeden üret (önizleme)  3) Tarayıcı arayüz testi."""
import os, sys, json, shutil, subprocess, time, datetime as dt
os.makedirs("denetim_graf", exist_ok=True)
import teknik_bulten as TB
os.makedirs("pub/tarama", exist_ok=True)
for p in ("bist", "abd", "kripto", "emtia"):
    t0 = time.time()
    try:
        r = TB.calistir(p, klasor="seed", zorla=True)
        f = os.path.join("seed", "tarama", f"{p}.csv")
        if os.path.exists(f): shutil.copy(f, f"pub/tarama/{p}.csv"); print("TARAMA", p, "tamam", round(time.time() - t0), "sn")
        else: print("TARAMA", p, "dosya yok")
    except Exception as ex:
        print("TARAMA", p, "HATA", ex)
print(subprocess.run([sys.executable, "yayinla.py", "pub", "Tarama tabloları (ilk)"], capture_output=True, text=True).stdout[-300:])
# --- Telegram önizleme (gönderim yok)
import tg
tg.Bot.aktif = property(lambda self: True)
tg.Bot._api = lambda self, *a, **k: {"ok": True, "result": {"message_id": 1} if a and a[0] != "sendMediaGroup" else [{"message_id": 1}]}
import alarm as AL
ornek = ["⚡THYAO bugün -4,2% hareket etti (fiyat 314,00)", "🔔ALTIN fiyatı 3600 üstüne çıktı: 3.613,68",
         "🟢 TSLA.US (Tesla): Simetrik üçgen – YUKARI KIRILIM (günlük, 27.11) · fiyat 396,46 (+%4,3)",
         "🔴 NVDA.US (Nvidia): Ölüm kesişimi (SMA50 < SMA200) (günlük, 27.11) · fiyat 146,96 (-%1,6)",
         "📈 BTC/USDT RSI 28 (< 30) · fiyat 60.000", "📰 ASELS · Yeni iş / sipariş / sözleşme: Aselsan 120 milyon dolarlık sözleşme imzaladı · fiyat 332,00 (+%5,4)⟦https://kap.org.tr⟧",
         "💼 GARAN: ⚠️ ters sinyal: Yapı kırılımı aşağı (BOS) · fiyat 138,10 (-%1,4)"]
AL.gonder(ornek)
for f in os.listdir("alarm_cikti"):
    if f.endswith(".png"): shutil.copy(os.path.join("alarm_cikti", f), f"denetim_graf/tg_alarm_{f}")
import haber as HB
try:
    import urllib.request
    son = json.loads(urllib.request.urlopen("https://raw.githubusercontent.com/erhankatkay-glitch/bist-rapor/bulten/haber/son.json").read())
    an = [x for x in son if x.get("varliklar")][:3]
    print("haber örnek:", len(an))
    b = tg.Bot("alarm"); print("haber kartı:", HB.haber_karti_gonder(b, an, dt.datetime.now(dt.timezone.utc)))
    shutil.copy(os.path.join(HB.CIKTI, "haber", "kart.png"), "denetim_graf/tg_haber.png")
except Exception as ex:
    print("haber önizleme HATA", ex)
for p in ("bist", "kripto"):
    f = os.path.join("seed", p, "kapanis_karti.png")
    try:
        import kart as KT, pandas as pd
        print("bülten", p, os.path.exists(f))
        if os.path.exists(f): shutil.copy(f, f"denetim_graf/tg_kapanis_{p}.png")
    except Exception as ex:
        print(ex)
