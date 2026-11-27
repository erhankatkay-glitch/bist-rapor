"""Canlı uygulama: normal ve ?embed=true modları (hiçbir şey kaydetmez)."""
import os
os.makedirs("denetim_graf", exist_ok=True)
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
def dene(pw, url, ad):
    b = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2, user_agent=UA).new_page()
    pg.goto(url, timeout=180000); fr = None
    for i in range(80):
        pg.wait_for_timeout(3000)
        for f in pg.frames:
            try:
                if f.locator('[data-testid="stTab"]').count(): fr = f; break
            except Exception: pass
        if fr: break
    print(ad, "çerçeve:", [f.url[:70] for f in pg.frames][:4], "| uygulama bulundu:", bool(fr))
    if fr:
        for i in range(40):
            pg.wait_for_timeout(2000)
            if not fr.evaluate("!!document.querySelector('[data-testid=stStatusWidget]')"): break
        pg.wait_for_timeout(5000)
        pg.screenshot(path=f"denetim_graf/{ad}_1.png")
        print(ad, "alt menü:", fr.evaluate("!!document.getElementById('kk-nav')"), "| rozet/araç çubuğu:",
              pg.evaluate("document.querySelectorAll('[class*=viewerBadge],[data-testid=stToolbar],[class*=_profileContainer],[class*=profile]').length"))
        try:
            fr.locator("#kk-nav button[data-sekme='Takip']").tap(); pg.wait_for_timeout(2500)
            print(ad, "Takip seçili:", fr.evaluate("[...document.querySelectorAll('[data-testid=stTab]')].filter(x=>x.getAttribute('aria-selected')==='true').map(x=>x.innerText.trim())"))
            pg.screenshot(path=f"denetim_graf/{ad}_2.png")
        except Exception as ex:
            print(ad, "menü:", ex)
    b.close()
with sync_playwright() as pw:
    dene(pw, "https://cuz9rz7rlsx7bfwolrb8xq.streamlit.app/?embed=true", "embed")
    dene(pw, "https://cuz9rz7rlsx7bfwolrb8xq.streamlit.app/", "normal")
