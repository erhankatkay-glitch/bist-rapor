"""Canlı uygulama hata kontrolü + Aşama 12 gerçek veri."""
import os, sys, subprocess, time, json
os.makedirs("denetim_graf", exist_ok=True); os.makedirs("cikti", exist_ok=True)
from playwright.sync_api import sync_playwright
URL = "https://cuz9rz7rlsx7bfwolrb8xq.streamlit.app"
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = br.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2).new_page()
    pg.goto(URL, timeout=180000)
    fr = None
    for _ in range(90):
        pg.wait_for_timeout(3000)
        for f in pg.frames:
            try:
                if f.evaluate("!!document.querySelector('[data-testid=stTab]')"): fr = f; break
            except Exception: pass
        if fr: break
    if not fr: print("canlı uygulama açılmadı"); pg.screenshot(path="denetim_graf/canli.png")
    else:
        fr.wait_for_timeout(8000)
        for yol in ("Keşfet|Dünya", "Ana Sayfa|Ekonomi"):
            fr.evaluate(f"window.kkGitAlt && window.kkGitAlt('{yol}')"); fr.wait_for_timeout(15000)
            print("CANLI", yol, "hata:", fr.evaluate("[...document.querySelectorAll('[data-testid=stException]')].map(x=>x.innerText.slice(0,160))"),
                  "| dünya satırı:", fr.evaluate("document.querySelectorAll('.dn').length"), "| ilişki kartı:", fr.evaluate("document.querySelectorAll('.ko').length"),
                  "| okunamadı:", fr.evaluate("[...document.querySelectorAll('p')].map(x=>x.innerText).filter(t=>t.includes('okunamadı'))"))
            pg.screenshot(path=f"denetim_graf/canli_{yol.split('|')[1].replace(' ', '_')}.png")
    br.close()
