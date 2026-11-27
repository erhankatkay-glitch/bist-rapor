"""Aşama 9 arayüz testi: sanal işlem aç, sayfayı yenile (cihaz deposundan geri yükleme), risk hesaplayıcı."""
import os, sys, subprocess, time
os.makedirs("denetim_graf", exist_ok=True)
p = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501"],
                     stdout=open("st_log.txt", "w"), stderr=subprocess.STDOUT)
time.sleep(20)
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: print("pageerror:", str(e)[:300]))
    def bekle(sn=120):
        for i in range(sn // 2):
            pg.wait_for_timeout(2000)
            if not pg.evaluate("!!document.querySelector('[data-testid=stStatusWidget]')"): break
    def git_sanal():
        pg.locator("#kk-nav button[data-sekme='Portföy']").tap(); pg.wait_for_timeout(1500)
        pg.evaluate("""(()=>{const t=[...document.querySelectorAll('[data-testid=stTab]')].find(x=>x.innerText.trim().endsWith('Sanal işlem')); t&&t.click();})()""")
        pg.wait_for_timeout(4000); bekle()
    pg.goto("http://localhost:8501", timeout=120000); pg.wait_for_selector('[data-testid="stTab"]', timeout=180000); bekle(); pg.wait_for_timeout(3000)
    git_sanal()
    print("yükleniyor yazısı:", pg.get_by_text("Sanal defter bu cihazdan yükleniyor").count())
    try:
        pg.get_by_text("Yeni sanal işlem").first.click(); pg.wait_for_timeout(1500)
        def yaz(etiket, deger):
            el = [e for e in pg.get_by_label(etiket).all() if e.is_visible()][0]
            el.fill(str(deger)); el.press("Enter"); pg.wait_for_timeout(1500); bekle(30)
        yaz("Kod", "THYAO"); yaz("Fiyat (TL)", 314); yaz("Stop (isteğe bağlı)", 300); yaz("Hedef (isteğe bağlı)", 340); yaz("Adet", 70)
        pg.screenshot(path="denetim_graf/sanal_form.png")
        pg.get_by_role("button", name="Sanal işlemi aç").first.click(); pg.wait_for_timeout(5000); bekle()
        print("depo:", pg.evaluate("(localStorage.getItem('katkay_sanal')||'').slice(0,200)"))
        pg.screenshot(path="denetim_graf/sanal_acik.png")
    except Exception as ex:
        print("sanal form:", ex)
    pg.reload(); pg.wait_for_selector('[data-testid="stTab"]', timeout=180000); bekle(); pg.wait_for_timeout(3000)
    git_sanal(); pg.wait_for_timeout(4000); bekle()
    print("yenileme sonrası THYAO kartı:", pg.evaluate("[...document.querySelectorAll('.hb')].filter(x=>x.offsetParent).map(x=>x.innerText.slice(0,80))"))
    pg.screenshot(path="denetim_graf/sanal_yenile.png")
    pg.evaluate("""(()=>{const t=[...document.querySelectorAll('[data-testid=stTab]')].find(x=>x.innerText.trim().endsWith('Risk hesaplayıcı')); t&&t.click();})()""")
    pg.wait_for_timeout(2500)
    try:
        for et, dg in (("Giriş", 314), ("Stop", 300), ("Hedefler (virgülle, isteğe bağlı)", "330, 345")):
            el = [e for e in pg.get_by_label(et, exact=True).all() if e.is_visible()][0]
            el.fill(str(dg)); el.press("Enter"); pg.wait_for_timeout(1500); bekle(30)
        pg.wait_for_timeout(2000)
        print("risk kartları:", pg.evaluate("[...document.querySelectorAll('.kart')].filter(x=>x.offsetParent).map(x=>x.innerText.replace(/\\n/g,' | '))"))
        pg.screenshot(path="denetim_graf/risk.png", full_page=False)
        pg.mouse.wheel(0, 500); pg.wait_for_timeout(800); pg.screenshot(path="denetim_graf/risk2.png")
    except Exception as ex:
        print("risk:", ex)
    print("HATA KUTUSU:", pg.evaluate("document.querySelectorAll('[data-testid=stException]').length"))
    b.close()
p.terminate()
print(open("st_log.txt").read()[-2000:])
