"""Canlı uygulamada GH_TOKEN kontrolü (hiçbir şey kaydetmez)."""
import os
os.makedirs("denetim_graf", exist_ok=True)
from playwright.sync_api import sync_playwright
URL = "https://cuz9rz7rlsx7bfwolrb8xq.streamlit.app/"
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2,
                       user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1").new_page()
    pg.goto(URL, timeout=180000)
    fr = None
    for i in range(90):
        pg.wait_for_timeout(3000)
        if i == 2: pg.screenshot(path="denetim_graf/canli_0.png"); print("başlık:", pg.title(), "| çerçeveler:", [f.url[:80] for f in pg.frames])
        for btn in ("Yes, get this app back up!",):
            try:
                x = pg.get_by_role("button", name=btn)
                if x.count(): x.first.click(); print("uyandırıldı")
            except Exception: pass
        for f in pg.frames:
            try:
                if f.locator('[data-testid="stTab"]').count(): fr = f; break
            except Exception: pass
        if fr: break
    if not fr:
        pg.screenshot(path="denetim_graf/canli_yok.png"); print("uygulama yüklenmedi"); raise SystemExit
    for i in range(60):
        pg.wait_for_timeout(2000)
        if not fr.evaluate("!!document.querySelector('[data-testid=stStatusWidget]')"): break
    pg.wait_for_timeout(3000)
    for ad in ("Takip", "Alarmlar"):
        fr.evaluate(f"""(()=>{{const t=[...document.querySelectorAll('[data-testid=stTab]')].find(x=>x.innerText.trim().endsWith('{ad}')); t&&t.click();}})()""")
        pg.wait_for_timeout(2500)
    s = [e for e in fr.locator("summary").all() if e.is_visible() and "Yeni alarm ekle" in e.inner_text()]
    if s: s[0].click(); pg.wait_for_timeout(2500)
    print("KAYDET düğmesi:", len([e for e in fr.get_by_role("button", name="Kaydet").all() if e.is_visible()]))
    print("GH_TOKEN uyarısı:", fr.get_by_text("GH_TOKEN eklenmeli").count())
    pg.screenshot(path="denetim_graf/canli_alarm.png")
    b.close()
