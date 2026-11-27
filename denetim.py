"""Telegram kart önizlemesi (gönderim yok) + tarayıcı arayüz testi."""
import os, sys, json, shutil, subprocess, time, datetime as dt
os.makedirs("denetim_graf", exist_ok=True)
os.environ["TELEGRAM_TOKEN"] = "x"; os.environ["TELEGRAM_CHAT_ID"] = "1"
import tg
tg.Bot._api = lambda self, *a, **k: {"ok": True, "result": [{"message_id": 1}] if a and a[0] == "sendMediaGroup" else {"message_id": 1}}
import alarm as AL
ornek = ["⚡THYAO bugün -4,2% hareket etti (fiyat 314,00)", "🔔ALTIN fiyatı 3600 üstüne çıktı: 3.613,68",
         "🟢 TSLA.US (Tesla): Simetrik üçgen – YUKARI KIRILIM (günlük, 27.11) · fiyat 396,46 (+%4,3)",
         "🔴 NVDA.US (Nvidia): Ölüm kesişimi (SMA50 < SMA200) (günlük, 27.11) · fiyat 146,96 (-%1,6)",
         "📈 BTC/USDT RSI 28 (< 30) · fiyat 60.000",
         "📰 ASELS · Yeni iş / sipariş / sözleşme: Aselsan 120 milyon dolarlık sözleşme imzaladı · fiyat 332,00 (+%5,4)⟦https://kap.org.tr⟧",
         "💼 GARAN: ⚠️ ters sinyal: Yapı kırılımı aşağı (BOS) · fiyat 138,10 (-%1,4)"]
try:
    AL.gonder(ornek)
    for f in os.listdir("alarm_cikti"):
        if f.endswith(".png"): shutil.copy(os.path.join("alarm_cikti", f), f"denetim_graf/tg_alarm_{f}")
except Exception as ex:
    print("alarm önizleme HATA", ex)
import haber as HB
try:
    import urllib.request
    son = json.loads(urllib.request.urlopen("https://raw.githubusercontent.com/erhankatkay-glitch/bist-rapor/bulten/haber/son.json").read())
    an = [x for x in son if x.get("varliklar")][:3]
    b = tg.Bot("alarm"); print("haber kartı:", len(an), HB.haber_karti_gonder(b, an, dt.datetime.now(dt.timezone.utc)))
    shutil.copy(os.path.join(HB.CIKTI, "haber", "kart.png"), "denetim_graf/tg_haber.png")
except Exception as ex:
    print("haber önizleme HATA", ex)
p = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501"],
                     stdout=open("st_log.txt", "w"), stderr=subprocess.STDOUT, env={k: v for k, v in os.environ.items() if not k.startswith("TELEGRAM")})
time.sleep(20)
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2).new_page()
    pg.on("pageerror", lambda e: print("pageerror:", str(e)[:300]))
    pg.goto("http://localhost:8501", timeout=120000)
    pg.wait_for_selector('[data-testid="stTab"]', timeout=180000)
    def bekle(sn=120):
        for i in range(sn // 2):
            pg.wait_for_timeout(2000)
            if not pg.evaluate("!!document.querySelector('[data-testid=stStatusWidget]')"): break
    bekle(); pg.wait_for_timeout(3000)
    pg.locator("#kk-nav button[data-sekme='Keşfet']").tap(); pg.wait_for_timeout(1500)
    pg.evaluate("""(()=>{const t=[...document.querySelectorAll('[data-testid=stTab]')].find(x=>x.innerText.trim().endsWith('Tarayıcı')); t&&t.click();})()""")
    pg.wait_for_timeout(4000); bekle()
    pg.screenshot(path="denetim_graf/tarayici1.png")
    try:
        sb = pg.locator("[data-testid=stSelectbox]:visible").filter(has_text="Şablon").first
        sb.click(); pg.wait_for_timeout(800)
        pg.locator("li[role=option]", has_text="Güçlü trend").first.click(); pg.wait_for_timeout(3000); bekle()
        print("SONUÇ:", pg.evaluate("[...document.querySelectorAll('.bb')].filter(x=>x.offsetParent).map(x=>x.innerText)"))
        pg.screenshot(path="denetim_graf/tarayici2.png")
        pg.mouse.wheel(0, 700); pg.wait_for_timeout(1500); pg.screenshot(path="denetim_graf/tarayici3.png")
    except Exception as ex:
        print("şablon:", ex)
    b.close()
p.terminate()
print(open("st_log.txt").read()[-1500:])
