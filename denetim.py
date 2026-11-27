"""Telegram kart önizlemesi (gönderim yok) + tarayıcı arayüz testi."""
import os, sys, json, shutil, subprocess, time, datetime as dt
os.makedirs("denetim_graf", exist_ok=True)
os.environ["TELEGRAM_TOKEN"] = "x"; os.environ["TELEGRAM_CHAT_ID"] = "1"
import tg
tg.Bot._api = lambda self, *a, **k: {"ok": True, "result": [{"message_id": 1}] if a and a[0] == "sendMediaGroup" else {"message_id": 1}}
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
        sel = [e for e in pg.locator('[data-testid=stSelectbox]').all() if e.is_visible()]
        print("görünür seçim kutusu:", len(sel), [e.inner_text()[:30] for e in sel])
        hedef = next(e for e in sel if "Şablon" in e.inner_text())
        print("iç:", hedef.inner_html()[:600])
        hedef.locator("input, [role=combobox]").first.click(force=True); pg.wait_for_timeout(1000); pg.keyboard.type("Güçlü trend"); pg.wait_for_timeout(800); pg.keyboard.press("Enter")
        pg.wait_for_timeout(3000); bekle()
        print("HATA KUTUSU:", pg.evaluate("document.querySelectorAll('[data-testid=stException]').length"))
        print("SONUÇ:", pg.evaluate("[...document.querySelectorAll('.bb')].filter(x=>x.offsetParent).map(x=>x.innerText)"))
        pg.screenshot(path="denetim_graf/tarayici2.png")
        pg.mouse.wheel(0, 700); pg.wait_for_timeout(1500); pg.screenshot(path="denetim_graf/tarayici3.png")
    except Exception as ex:
        print("şablon:", ex)
    b.close()
p.terminate()
print(open("st_log.txt").read()[-1500:])
