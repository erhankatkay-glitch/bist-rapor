import subprocess, sys, os
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","webkit"],check=True,capture_output=True)
from playwright.sync_api import sync_playwright
os.makedirs("denetim_graf",exist_ok=True)
U="https://erhankatkay-glitch.github.io/bist-rapor/"
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices["iPhone 13"]); pg=ctx.new_page()
    hatalar=[]; pg.on("pageerror",lambda e:hatalar.append(str(e)))
    pg.goto(U); pg.wait_for_timeout(4000)
    for kod in ("THYAO","AAPL.US","BTCUSDT"):
        pg.goto(U+"#v/"+kod); pg.reload(); pg.wait_for_timeout(9000)
        t=pg.inner_text("body"); i=t.find("TEMEL ANALİZ"); i=i if i>=0 else t.find("Temel analiz")
        print("==",kod, t[i:i+700].replace("\n"," | ") if i>=0 else "temel yok")
        print("pdf linkleri",pg.eval_on_selector_all("a[href*='releases/download']","e=>e.map(x=>x.href)"))
        h=pg.locator("h2",has_text="Temel analiz")
        if h.count(): h.first.scroll_into_view_if_needed(); pg.wait_for_timeout(500); pg.screenshot(path=f"denetim_graf/v_{kod.replace('.','_')}.png")
    pg.goto(U+"#piyasa"); pg.wait_for_timeout(5000)
    pg.click("[data-py=temel]"); pg.wait_for_timeout(6000)
    for mod in ("bist","abd","resmi","genc","kucuk"):
        pg.click(f"[data-tz={mod}]"); pg.wait_for_timeout(5000)
        pg.screenshot(path=f"denetim_graf/p_{mod}.png")
        t=pg.inner_text("#py-ic"); print("== Piyasa/Temel",mod, t[:700].replace("\n"," | "))
    print("JS hataları:",hatalar)
