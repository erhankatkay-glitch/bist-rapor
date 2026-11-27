"""Arayüz testi: Analiz/Seviye düğmeleri, Teknik sekmesinde SMC çipleri ve Heikin Ashi."""
import subprocess, time, sys, os
os.makedirs("denetim_graf", exist_ok=True)
p = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501"],
                     stdout=open("st_log.txt", "w"), stderr=subprocess.STDOUT)
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
    bekle(); pg.wait_for_timeout(4000)
    sec = lambda: pg.evaluate("""[...document.querySelectorAll('[data-testid="stTab"]')].filter(x=>x.getAttribute('aria-selected')==='true').map(x=>x.innerText.trim())""")
    # ANALİZ
    pg.locator(".oc-b:visible", has_text="Analiz").first.click(); pg.wait_for_timeout(3000); bekle(150); pg.wait_for_timeout(6000)
    print("ANALİZ sonrası sekmeler:", sec())
    print("rapor başlığı görünür:", pg.evaluate("[...document.querySelectorAll('.vb')].filter(x=>x.offsetParent).map(x=>x.innerText.slice(0,40))"))
    pg.screenshot(path="denetim_graf/analiz.png")
    # SEVİYE
    pg.locator("#kk-nav button[data-sekme='Ana Sayfa']").tap(); pg.wait_for_timeout(2500)
    pg.locator(".oc-b:visible", has_text="Seviye").nth(1).click(); pg.wait_for_timeout(3000); bekle(150); pg.wait_for_timeout(8000)
    print("SEVİYE sonrası sekmeler:", sec())
    print("seviye kartı görünür:", pg.evaluate("[...document.querySelectorAll('.sv')].filter(x=>x.offsetParent).length"))
    pg.screenshot(path="denetim_graf/seviye.png")
    print("SMC çip:", pg.evaluate("[...document.querySelectorAll('.cip')].filter(x=>x.offsetParent).map(x=>x.innerText).slice(0,12)"))
    try:
        el = pg.locator("text=Akıllı para (SMC) ve harmonik").first
        el.scroll_into_view_if_needed(); pg.wait_for_timeout(800); pg.mouse.wheel(0, -500); pg.wait_for_timeout(600)
        pg.screenshot(path="denetim_graf/smc.png")
        pg.locator("label:has-text('Heikin Ashi')").first.click(); pg.wait_for_timeout(3000); bekle(60)
        pg.screenshot(path="denetim_graf/ha.png")
    except Exception as ex:
        print("SMC/HA:", ex)
    b.close()
p.terminate()
print(open("st_log.txt").read()[-2000:])
