"""Arayüz testi: Streamlit'i başlatır, telefon boyutunda ana sayfayı ve alt menüyü dener."""
import subprocess, time, sys, os
p = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501"],
                     stdout=open("st_log.txt", "w"), stderr=subprocess.STDOUT)
time.sleep(20)
from playwright.sync_api import sync_playwright
os.makedirs("denetim_graf", exist_ok=True)
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2).new_page()
    pg.on("pageerror", lambda e: print("pageerror:", str(e)[:300]))
    pg.goto("http://localhost:8501", timeout=120000)
    pg.wait_for_selector('[data-testid="stTab"]', timeout=180000)
    for i in range(90):
        if not pg.evaluate("!!document.querySelector('[data-testid=stStatusWidget]')"): break
        pg.wait_for_timeout(2000)
    pg.wait_for_timeout(6000)
    sec = lambda: pg.evaluate("""[...document.querySelectorAll('[data-testid="stTab"]')].filter(x=>x.getAttribute('aria-selected')==='true').map(x=>x.innerText.trim())""")
    print("başta:", sec())
    print("mini kart:", pg.evaluate("document.querySelectorAll('.mk').length"), "fırsat kartı:", pg.evaluate("document.querySelectorAll('.fk').length"))
    pg.screenshot(path="denetim_graf/ana.png", full_page=False)
    pg.mouse.wheel(0, 700); pg.wait_for_timeout(800); pg.screenshot(path="denetim_graf/ana2.png")
    pg.mouse.wheel(0, 700); pg.wait_for_timeout(800); pg.screenshot(path="denetim_graf/ana3.png")
    print("öne çıkan:", pg.evaluate("document.querySelectorAll('.oc').length"), "ana sekme gizli:",
          pg.evaluate("(()=>{const t=document.querySelector('.stTabs [role=tablist]'); return t? getComputedStyle(t).display : 'yok'})()"))
    for ad in ["Keşfet", "Takip"]:
        pg.locator(f"#kk-nav button[data-sekme='{ad}']").tap(); pg.wait_for_timeout(2500)
        pg.evaluate("window.scrollTo(0,0)"); pg.screenshot(path=f"denetim_graf/{ad}.png")
    b.close()
p.terminate()
print(open("st_log.txt").read()[-2500:])
