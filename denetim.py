"""6'lı alt menü + iğne tetiği testi (yerel Streamlit, telefon görünümü)."""
import os, sys, subprocess, time, json
os.makedirs("denetim_graf", exist_ok=True)
# --- iğne: canlı Binance verisiyle tetik durumu + alarm kuralı
import igne as IG, alarm as A
for b in ("BTC", "ETH"):
    H, L, C = IG.mumlar(f"{b}USDT", "1h", 300)
    print(b, "fiyat", C[-1], "uyarı var mı:", bool(IG.uyari(H, L, C)), "| TETİK:", IG.tetik(H, L, C))
K = [k for k in A.kurallar(open("alarmlar.txt").read()) if k["tip"] == "igne"]
bl, yeni = A.tara(K, {}); print("iğne kuralı:", len(K), "bildirim:", bl, "aktif:", A.IGNE_AKTIF)
# sahte aktif iğne ile bant gösterimi testi için bulten yerine yerel dosya kullanılamaz; uygulama testi yalnız menü
p = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501"],
                     stdout=open("st_log.txt", "w"), stderr=subprocess.STDOUT)
time.sleep(20)
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = br.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True, device_scale_factor=2).new_page()
    pg.on("pageerror", lambda e: print("pageerror:", str(e)[:300]))
    def bekle(sn=150):
        for i in range(sn // 2):
            pg.wait_for_timeout(2000)
            if not pg.evaluate("!!document.querySelector('[data-testid=stStatusWidget]')"): break
    sec = "[...document.querySelectorAll('[data-testid=stTab]')].filter(x=>x.getAttribute('aria-selected')==='true').map(x=>x.innerText.trim())"
    akt = "[...document.querySelectorAll('#kk-nav button.aktif')].map(x=>x.innerText.trim())"
    pg.goto("http://localhost:8501", timeout=120000); pg.wait_for_selector('[data-testid="stTab"]', timeout=180000); bekle(); pg.wait_for_timeout(5000)
    print("menü:", pg.evaluate("[...document.querySelectorAll('#kk-nav button')].map(x=>x.innerText.trim())"), "aktif:", pg.evaluate(akt))
    print("bant:", pg.evaluate("(document.querySelector('.kk-uyari')||{}).innerText"))
    pg.screenshot(path="denetim_graf/m0_ana.png")
    try:
        pg.locator(".fl-b").first.scroll_into_view_if_needed(); pg.wait_for_timeout(1200); pg.screenshot(path="denetim_graf/firsat.png")
        print("fırsat grupları:", pg.evaluate("[...document.querySelectorAll('.fl-b')].map(x=>x.innerText.replace(/\\n/g,' '))"),
              "satır:", pg.evaluate("document.querySelectorAll('.fl').length"))
    except Exception as ex: print("fırsat:", ex)
    for i, ad in enumerate(["Piyasalar", "Harita", "Seçki", "BIST", "Haberler", "Ana sayfa"]):
        pg.locator(f"#kk-nav button:has-text('{ad}')").first.click(); pg.wait_for_timeout(2500); bekle(90); pg.wait_for_timeout(1500)
        print(f"{ad:10} seçili:", pg.evaluate(sec)[:3], "| aktif:", pg.evaluate(akt), "| hata:", pg.evaluate("document.querySelectorAll('[data-testid=stException]').length"))
        pg.screenshot(path=f"denetim_graf/m{i+1}_{ad}.png")
    pg.locator(".kk-kutu span[data-git='Takip|Alarmlar']").first.click(); pg.wait_for_timeout(2500)
    print("Bildirimler kutusu:", pg.evaluate(sec)[:3], "| aktif:", pg.evaluate(akt))
    br.close()
p.terminate()
print(open("st_log.txt").read()[-1200:])
