"""Aşama 13: yeniden yayın + canlı Emtia & Kripto opsiyon bölümü."""
import os, sys, subprocess
os.makedirs("denetim_graf", exist_ok=True); os.makedirs("cikti", exist_ok=True)
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = br.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2).new_page()
    pg.goto("https://cuz9rz7rlsx7bfwolrb8xq.streamlit.app", timeout=180000)
    fr = None
    for _ in range(90):
        pg.wait_for_timeout(3000)
        for f_ in pg.frames:
            try:
                if f_.evaluate("!!document.querySelector('[data-testid=stTab]')"): fr = f_; break
            except Exception: pass
        if fr: break
    for _ in range(40):
        if fr.evaluate("typeof window.kkGitAlt === 'function'"): break
        fr.wait_for_timeout(2000)
    fr.evaluate("localStorage.setItem('kk_gorulen', JSON.stringify(Array.from({length:80},(_, i)=>'x'+i)))")
    fr.evaluate("window.kkGitAlt('Keşfet|Emtia & Kripto')"); fr.wait_for_timeout(15000)
    print("özetler:", fr.evaluate("[...document.querySelectorAll('summary')].map(x=>x.innerText.slice(0,45))"))
    fr.evaluate("(()=>{const s=[...document.querySelectorAll('summary')].find(x=>x.innerText.includes('Opsiyon')); if(s){s.click(); s.scrollIntoView();}})()")
    fr.wait_for_timeout(5000)
    print("CANLI hata:", fr.evaluate("[...document.querySelectorAll('[data-testid=stException]')].map(x=>x.innerText.slice(0,200))"),
          "| hücre:", fr.evaluate("[...document.querySelectorAll('.kl-g div')].map(x=>x.innerText.split('\\n').slice(0,2).join(' '))"))
    pg.screenshot(path="denetim_graf/op1.png"); pg.mouse.wheel(0, 800); pg.wait_for_timeout(800); pg.screenshot(path="denetim_graf/op2.png")
    br.close()
