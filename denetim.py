"""Ana sayfa referans karşılaştırması (yerel Streamlit, telefon)."""
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
    def bekle(sn=150):
        for i in range(sn // 2):
            pg.wait_for_timeout(2000)
            if not pg.evaluate("!!document.querySelector('[data-testid=stStatusWidget]')"): break
    pg.goto("http://localhost:8501", timeout=120000); pg.wait_for_selector('[data-testid="stTab"]', timeout=180000); bekle(); pg.wait_for_timeout(5000)
    pg.screenshot(path="denetim_graf/a1.png")
    # boşluk teşhisi: görünür blokların üst/yükseklik listesi (ilk 700px)
    print(pg.evaluate("""[...document.querySelectorAll('[data-testid=stMain] [data-testid=stElementContainer], [data-testid=stMain] .stTabs, [data-testid=stMain] [data-testid=stVerticalBlock]')]
      .map(e=>{const r=e.getBoundingClientRect(); return [Math.round(r.top),Math.round(r.height),(e.getAttribute('data-testid')||'')+'.'+(e.className||'').toString().slice(0,40)]})
      .filter(x=>x[0]>=0&&x[0]<760&&x[1]>=0).slice(0,40)"""))
    print("mini kart genişlik:", pg.evaluate("[...document.querySelectorAll('.serit-mk .mk')].slice(0,5).map(x=>Math.round(x.getBoundingClientRect().width)+'@'+Math.round(x.getBoundingClientRect().left))"))
    pg.mouse.wheel(0, 600); pg.wait_for_timeout(1200); pg.screenshot(path="denetim_graf/a2.png")
    pg.locator("#kk-cek").click(); pg.wait_for_timeout(800); pg.screenshot(path="denetim_graf/cekmece.png")
    pg.locator("#kk-ckm a:has-text('Sanal işlem')").click(); pg.wait_for_timeout(3000); bekle(60)
    print("çekmece → Sanal işlem:", pg.evaluate("[...document.querySelectorAll('[data-testid=stTab]')].filter(x=>x.getAttribute('aria-selected')==='true').map(x=>x.innerText.trim()).slice(0,2)"))
    pg.locator("#kk-nav button:has-text('Seçki')").click(); pg.wait_for_timeout(2500); pg.screenshot(path="denetim_graf/secki.png")
    print("HATA:", pg.evaluate("document.querySelectorAll('[data-testid=stException]').length"))
    br.close()
p.terminate()
