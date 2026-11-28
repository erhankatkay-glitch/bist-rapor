import subprocess, sys, os, json
os.makedirs("denetim_graf",exist_ok=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","webkit"],check=True,capture_output=True)
from playwright.sync_api import sync_playwright
U="https://erhankatkay-glitch.github.io/bist-rapor/"
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices["iPhone 13"]); pg=ctx.new_page()
    hatalar=[]; pg.on("pageerror",lambda e:hatalar.append(str(e)))
    pg.goto(U+"#piyasa/temel/karne"); pg.wait_for_timeout(8000)
    pg.screenshot(path="denetim_graf/karne.png"); print("== karne", pg.inner_text("#py-ic")[:900].replace("\n"," | "))
    pg.evaluate("""()=>{localStorage.setItem('kk_pf_metin',JSON.stringify('THYAO 100 @ 280\\nBTC/USDT 0,05\\nALTIN 1'));
      localStorage.setItem('kk_temel_gordum',JSON.stringify({THYAO:{g:'DEĞERİNİN ÜZERİNDE',p:40},'BTC/USDT':{g:'NÖTR',p:40},ALTIN:{g:'GÜÇLÜ NEGATİF',p:34}}));}""")
    print("LS kontrol", pg.evaluate("()=>localStorage.getItem('kk_pf_metin')"))
    pg.goto(U+"#ozet"); pg.reload(); pg.wait_for_timeout(10000)
    t=pg.inner_text("#pf-temel") if pg.query_selector("#pf-temel") else "yok"; print("== pf-temel", t.replace("\n"," | "))
    e=pg.query_selector("#pf-temel")
    if e and t.strip(): e.scroll_into_view_if_needed(); pg.wait_for_timeout(600); pg.screenshot(path="denetim_graf/pf_temel.png")
    if pg.query_selector("#pft-tamam"): pg.click("#pft-tamam"); pg.wait_for_timeout(500); print("gördüm sonrası:", repr(pg.inner_text("#pf-temel")))
    print("JS hataları:",hatalar)
