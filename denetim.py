"""Canlı uygulamada GH_TOKEN kontrolü: Alarmlar > Yeni alarm ekle bölümünde Kaydet düğmesi var mı (hiçbir şey kaydetmez)."""
import os, time
os.makedirs("denetim_graf", exist_ok=True)
from playwright.sync_api import sync_playwright
URL = "https://cuz9rz7rlsx7bfwolrb8xq.streamlit.app/?embed=true"
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2).new_page()
    pg.goto(URL, timeout=180000)
    try:
        btn = pg.get_by_role("button", name="Yes, get this app back up!")
        if btn.count(): btn.first.click(); print("uyku: uyandırıldı")
    except Exception: pass
    pg.wait_for_selector('[data-testid="stTab"]', timeout=300000)
    for i in range(60):
        pg.wait_for_timeout(2000)
        if not pg.evaluate("!!document.querySelector('[data-testid=stStatusWidget]')"): break
    pg.wait_for_timeout(4000)
    pg.evaluate("""(()=>{const t=[...document.querySelectorAll('[data-testid=stTab]')].find(x=>x.innerText.trim().endsWith('Takip')); t&&t.click();})()""")
    pg.wait_for_timeout(2000)
    pg.evaluate("""(()=>{const t=[...document.querySelectorAll('[data-testid=stTab]')].find(x=>x.innerText.trim().endsWith('Alarmlar')); t&&t.click();})()""")
    pg.wait_for_timeout(3000)
    s = [e for e in pg.locator("summary").all() if e.is_visible() and "Yeni alarm ekle" in e.inner_text()]
    if s: s[0].click(); pg.wait_for_timeout(2500)
    print("KAYDET düğmesi:", len([e for e in pg.get_by_role("button", name="Kaydet").all() if e.is_visible()]))
    print("GH_TOKEN uyarısı:", pg.get_by_text("GH_TOKEN eklenmeli").count())
    pg.screenshot(path="denetim_graf/canli_alarm.png")
    b.close()
