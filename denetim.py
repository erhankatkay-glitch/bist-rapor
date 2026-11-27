"""10c-3 disiplin ekranı."""
import os, sys, subprocess, time, json
os.makedirs("denetim_graf", exist_ok=True)
D = open("ornek_defter.json").read()
p = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501"],
                     stdout=open("st_log.txt", "w"), stderr=subprocess.STDOUT)
time.sleep(20)
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = br.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2).new_page()
    pg.on("pageerror", lambda e: print("pageerror:", str(e)[:300]))
    pg.goto("http://localhost:8501", timeout=120000); pg.wait_for_selector('[data-testid="stTab"]', timeout=180000); pg.wait_for_timeout(8000)
    pg.evaluate("(d)=>{localStorage.setItem('katkay_sanal', d); localStorage.setItem('kk_gorulen', JSON.stringify(['x']));}", D)
    pg.reload(); pg.wait_for_selector('[data-testid="stTab"]', timeout=180000); pg.wait_for_timeout(8000)
    pg.evaluate("window.kkGitAlt('Portföy|Sanal işlem')"); pg.wait_for_timeout(12000)
    def bekle():
        for _ in range(40):
            pg.wait_for_timeout(1500)
            if not pg.evaluate("!!document.querySelector('[data-testid=stStatusWidget]')"): break
    bekle()
    print("sigorta bandı:", pg.evaluate("[...document.querySelectorAll('.kk-uyari')].map(x=>x.innerText).find(t=>t.includes('sigorta'))"))
    print("haftalık:", pg.evaluate("(document.querySelector('.kl-g')||{}).innerText"), "|", pg.evaluate("[...document.querySelectorAll('.kl-o')].map(x=>x.innerText)"))
    pg.screenshot(path="denetim_graf/s1.png")
    # yeni işlem: kod, fiyat, adet
    pg.locator("summary:has-text('Yeni sanal işlem'), [data-testid=stExpander] :text('Yeni sanal işlem')").first.click(); pg.wait_for_timeout(1500)
    def yaz(etiket, deger):
        el = pg.locator(f"[data-testid=stTextInput]:has-text('{etiket}') input, [data-testid=stNumberInput]:has-text('{etiket}') input").first
        el.fill(str(deger)); el.press("Enter"); pg.wait_for_timeout(1800); bekle()
    yaz("Kod", "THYAO"); yaz("Fiyat", 314); yaz("Stop", 300); yaz("Hedef", 345); yaz("Adet", 50)
    print("kontrol (neden yokken):", pg.evaluate("[...document.querySelectorAll('.kl-m')].map(x=>x.querySelector('i').innerText+' '+x.querySelector('b').innerText)"))
    print("aç düğmesi pasif mi:", pg.evaluate("[...document.querySelectorAll('button')].find(b=>b.innerText.includes('Sanal işlemi aç')).disabled"))
    yaz("Neden bu işlem", "BIST günlük kırılım denemesi")
    print("kontrol (nedenle):", pg.evaluate("(document.querySelector('.kl-b')||{}).innerText"), pg.evaluate("[...document.querySelectorAll('.kl-m')].filter(x=>x.querySelector('i').innerText!=='✓').map(x=>x.querySelector('b').innerText)"))
    print("esnetme kutusu:", pg.evaluate("!![...document.querySelectorAll('label')].find(l=>l.innerText.includes('esnetiyorum'))"))
    pg.locator(".kl").first.scroll_into_view_if_needed(); pg.wait_for_timeout(600); pg.screenshot(path="denetim_graf/s2.png")
    print("değerlendirilmemiş:", pg.evaluate("[...document.querySelectorAll('[data-testid=stExpander] summary')].map(x=>x.innerText).filter(t=>t.includes('Değerlendirilmemiş'))"))
    print("HATA:", pg.evaluate("document.querySelectorAll('[data-testid=stException]').length"))
    br.close()
p.terminate()
