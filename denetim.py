"""Ana sayfa yeni düzen testi (yerel Streamlit, telefon görünümü)."""
import os, sys, subprocess, time
os.makedirs("denetim_graf", exist_ok=True)
p = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501"],
                     stdout=open("st_log.txt", "w"), stderr=subprocess.STDOUT)
time.sleep(20)
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2).new_page()
    pg.on("pageerror", lambda e: print("pageerror:", str(e)[:300]))
    def bekle(sn=150):
        for i in range(sn // 2):
            pg.wait_for_timeout(2000)
            if not pg.evaluate("!!document.querySelector('[data-testid=stStatusWidget]')"): break
    pg.goto("http://localhost:8501", timeout=120000); pg.wait_for_selector('[data-testid="stTab"]', timeout=180000); bekle(); pg.wait_for_timeout(6000)
    pg.screenshot(path="denetim_graf/ana1.png")
    pg.mouse.wheel(0, 650); pg.wait_for_timeout(1200); pg.screenshot(path="denetim_graf/ana2.png")
    pg.mouse.wheel(0, 700); pg.wait_for_timeout(1200); pg.screenshot(path="denetim_graf/ana3.png")
    print("fırsat piyasaları:", pg.evaluate("[...document.querySelectorAll('.fk .fk-s:first-of-type')].map(x=>x.innerText.split(' · ')[0])"))
    print("kart başlıkları:", pg.evaluate("[...document.querySelectorAll('.mk-ad')].map(x=>x.innerText).slice(0,6)"))
    print("uyarı metni:", pg.evaluate("(document.querySelector('.kk-uyari')||{}).innerText"))
    print("öne çıkan satır:", pg.evaluate("[...document.querySelectorAll('.oc')].filter(x=>x.offsetParent).length"),
          "| mini grafik:", pg.evaluate("[...document.querySelectorAll('.oc-sp svg')].length"),
          "| kutu:", pg.evaluate("document.querySelectorAll('.kk-kutu span').length"),
          "| uyarı:", pg.evaluate("document.querySelectorAll('.kk-uyari').length"),
          "| gizli alt sekme:", pg.evaluate("[...document.querySelectorAll('[role=tablist]')].filter(t=>t.style.display==='none').length"))
    # kategori: Kripto
    try:
        pg.locator("label:has-text('Enerji')").first.click(); pg.wait_for_timeout(3000); bekle(60)
        print("kripto satırları:", pg.evaluate("[...document.querySelectorAll('.oc b')].filter(x=>x.offsetParent).map(x=>x.innerText).slice(0,8)"))
        pg.evaluate("window.scrollTo(0,0)"); pg.screenshot(path="denetim_graf/ana_kripto.png")
    except Exception as ex: print("kategori:", ex)
    # Takvim kutusu
    try:
        pg.locator(".kk-kutu span[data-git='Ana Sayfa|Ekonomi']").first.click(); pg.wait_for_timeout(3500)
        print("ekonomi seçili:", pg.evaluate("[...document.querySelectorAll('[data-testid=stTab]')].filter(x=>x.getAttribute('aria-selected')==='true').map(x=>x.innerText.trim()).slice(0,3)"))
        pg.screenshot(path="denetim_graf/takvim.png")
        pg.locator(".kk-geri:visible").first.click(); pg.wait_for_timeout(2500)
        print("geri sonrası:", pg.evaluate("[...document.querySelectorAll('[data-testid=stTab]')].filter(x=>x.getAttribute('aria-selected')==='true').map(x=>x.innerText.trim()).slice(0,3)"))
        pg.locator(".kk-kutu span[data-git='Takip|Alarmlar']").first.click(); pg.wait_for_timeout(2500)
        print("bildirimler:", pg.evaluate("[...document.querySelectorAll('[data-testid=stTab]')].filter(x=>x.getAttribute('aria-selected')==='true').map(x=>x.innerText.trim()).slice(0,6)"))
        pg.screenshot(path="denetim_graf/nav_aktif.png")
    except Exception as ex: print("kutu:", ex)
    print("HATA KUTUSU:", pg.evaluate("document.querySelectorAll('[data-testid=stException]').length"))
    b.close()
p.terminate()
print(open("st_log.txt").read()[-1500:])
