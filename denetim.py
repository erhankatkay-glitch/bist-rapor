"""Aşama 13: gerçek Deribit verisi + yayın + analiz/PDF + canlı uygulama."""
import os, sys, subprocess, time, json
os.makedirs("denetim_graf", exist_ok=True); os.makedirs("cikti", exist_ok=True)
import opsiyon as OP
o = OP.hesapla("cikti")
for c, p in o["paralar"].items():
    print(c, "endeks", round(p["endeks"]), "| DVOL", p["dvol"] and (p["dvol"]["deger"], round(p["dvol"]["yuzdelik"], 2)), "| RV", p["gerceklesen_30g"] and round(p["gerceklesen_30g"], 3),
          "| skew", p["skew_25d"] and round(p["skew_25d"], 2), "| P/C oi", round(p["pc_oi"], 2), "hacim", p["pc_hacim"] and round(p["pc_hacim"], 2), "| ters", p["ters_yapi"])
    for v in p["buyuk_vadeler"]: print("   ", v["vade_ad"], round(v["gun"], 1), "MP", v["max_pain"], "±", round(v["beklenen_hareket"], 4), "call", v["call_duvari"], "put", v["put_duvari"], "iv", round(v["atm_iv"], 3))
    print("   ", p["yorum"])
OP.kart_ciz(o, "denetim_graf/opsiyon.png")
subprocess.run([sys.executable, "yayinla.py", "cikti", "opsiyon ilk yayın (denetim)"])
import bist_teknik as T, bist_teknik_rapor as TR
s = T.analiz("BTC/USDT")
print("BTC karne:", [(d[0], d[1]) for d in s["tf"]["G"]["durum"] if d[0].startswith("Opsiyon")], s.get("opsiyon_hata"))
f = TR.teknik_pdf(s, "denetim_graf/BTC.pdf"); print("PDF", os.path.getsize(f))
time.sleep(30)
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
    fr.evaluate("localStorage.setItem('kk_gorulen', JSON.stringify(Array.from({length:80},(_, i)=>'x'+i)))")
    fr.evaluate("window.kkGitAlt('Keşfet|Emtia & Kripto')"); fr.wait_for_timeout(12000)
    fr.locator("summary:has-text('Opsiyon piyasası')").first.click(); fr.wait_for_timeout(4000)
    print("CANLI hata:", fr.evaluate("[...document.querySelectorAll('[data-testid=stException]')].map(x=>x.innerText.slice(0,200))"),
          "| okunamadı:", fr.evaluate("[...document.querySelectorAll('p')].map(x=>x.innerText).filter(t=>t.includes('okunamadı'))"),
          "| hücre:", fr.evaluate("[...document.querySelectorAll('.kl-g div')].map(x=>x.innerText.split('\\n')[0])"))
    fr.locator("summary:has-text('Opsiyon piyasası')").first.scroll_into_view_if_needed(); pg.wait_for_timeout(800); pg.screenshot(path="denetim_graf/op1.png")
    pg.mouse.wheel(0, 900); pg.wait_for_timeout(800); pg.screenshot(path="denetim_graf/op2.png")
    br.close()
