"""Bildirim kuyruğu + çekmece testi."""
import os, sys, subprocess, time
os.makedirs("denetim_graf", exist_ok=True)
p = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501"],
                     stdout=open("st_log.txt", "w"), stderr=subprocess.STDOUT)
time.sleep(20)
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = br.new_context(viewport={"width": 390, "height": 700}, is_mobile=True, has_touch=True, device_scale_factor=2).new_page()
    pg.on("pageerror", lambda e: print("pageerror:", str(e)[:300]))
    pg.goto("http://localhost:8501", timeout=120000); pg.wait_for_selector('[data-testid="stTab"]', timeout=180000); pg.wait_for_timeout(15000)
    print("gerçek bildirim sayısı:", pg.evaluate("document.querySelectorAll('.kk-bild .kk-uyari').length"),
          "toast:", pg.evaluate("!!document.getElementById('kk-toast') && document.getElementById('kk-toast').className"))
    pg.evaluate("""localStorage.removeItem('kk_gorulen'); const d=document.createElement('div'); d.className='kk-bild';
      d.innerHTML='<div class="kk-uyari kk-uyari-k" data-id="t2" data-sure="4000" data-git="Takip|Alarmlar" style="--sure:4000ms"><span class="kk-x" data-kapat="t2">×</span><b>⚡ BTC\\'de kısa süreli aşağı iğne bekleniyor</b><div>Şu an 61.992 · olası iğne bölgeleri 60.828 / 60.800 · 00:31</div></div>'+
      '<div class="kk-uyari" data-id="t1" data-sure="4000" data-git="Takip|Alarmlar" style="--sure:4000ms"><span class="kk-x" data-kapat="t1">×</span><b>⚡ S&P 500</b><div>İkili dip – TEYİT · 21:46</div></div>';
      document.querySelector('[data-testid=stMain]').appendChild(d);""")
    pg.wait_for_timeout(1800); pg.screenshot(path="denetim_graf/t1.png"); print("1:", pg.evaluate("document.getElementById('kk-toast').innerText.slice(0,40)"))
    pg.wait_for_timeout(4600); pg.screenshot(path="denetim_graf/t2.png"); print("2:", pg.evaluate("document.getElementById('kk-toast').innerText.slice(0,40)"))
    pg.wait_for_timeout(4800); print("bitti, açık mı:", pg.evaluate("document.getElementById('kk-toast').classList.contains('acik')"))
    print("görülen:", pg.evaluate("localStorage.getItem('kk_gorulen')"))
    # yeniden aynı liste → düşmemeli
    pg.evaluate("document.querySelectorAll('.kk-bild').forEach(x=>{const y=x.cloneNode(true); y.removeAttribute('data-kkb'); x.remove(); document.querySelector('[data-testid=stMain]').appendChild(y);})")
    pg.wait_for_timeout(2000); print("tekrar düştü mü:", pg.evaluate("document.getElementById('kk-toast').classList.contains('acik')"))
    pg.locator("#kk-cek").click(); pg.wait_for_timeout(900)
    pg.evaluate("document.querySelector('#kk-ckm .pan').scrollTo(0, 99999)"); pg.wait_for_timeout(500); pg.screenshot(path="denetim_graf/cek_alt.png")
    br.close()
p.terminate()
