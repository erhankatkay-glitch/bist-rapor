"""Çekmece menü görünümü."""
import os, sys, subprocess, time
os.makedirs("denetim_graf", exist_ok=True)
p = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501"],
                     stdout=open("st_log.txt", "w"), stderr=subprocess.STDOUT)
time.sleep(20)
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = br.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2).new_page()
    pg.on("pageerror", lambda e: print("pageerror:", str(e)[:300]))
    pg.goto("http://localhost:8501", timeout=120000); pg.wait_for_selector('[data-testid="stTab"]', timeout=180000); pg.wait_for_timeout(15000)
    pg.locator("#kk-cek").click(); pg.wait_for_timeout(900); pg.screenshot(path="denetim_graf/cek1.png")
    pg.locator("#kk-ckm a:has-text('Favoriler')").click(); pg.wait_for_timeout(3000)
    print("seçili:", pg.evaluate("[...document.querySelectorAll('[data-testid=stTab]')].filter(x=>x.getAttribute('aria-selected')==='true').map(x=>x.innerText.trim()).slice(0,2)"))
    pg.locator("#kk-cek").click(); pg.wait_for_timeout(900); pg.screenshot(path="denetim_graf/cek2.png")
    print("aktif:", pg.evaluate("[...document.querySelectorAll('#kk-ckm a.aktif')].map(x=>x.innerText.split('\\n')[0])"))
    pg.locator("#kk-ckm .kap").click(); pg.wait_for_timeout(700)
    print("kapandı:", pg.evaluate("!document.getElementById('kk-ckm').classList.contains('acik')"))
    br.close()
p.terminate()
