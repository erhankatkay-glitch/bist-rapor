import subprocess, sys, os
os.makedirs("denetim_graf",exist_ok=True)
subprocess.run("git clone -q --depth 1 --branch bulten $GH_URL onceki",shell=True)
os.environ["DURUM_KLON"]="onceki"
r=subprocess.run([sys.executable,"temel_bildirim.py","kart","denetim_graf/tg_temel.png"],capture_output=True,text=True); print(r.stdout[-800:], r.stderr[-800:])
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","webkit"],check=True,capture_output=True)
from playwright.sync_api import sync_playwright
U="https://erhankatkay-glitch.github.io/bist-rapor/"
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices["iPhone 13"]); pg=ctx.new_page()
    hatalar=[]; pg.on("pageerror",lambda e:hatalar.append(str(e)))
    pg.goto(U); pg.wait_for_timeout(4000)
    for kod in ("BTC/USDT","ALTIN","WTI"):
        pg.goto(U+"#v/"+kod.replace("/","%2F")); pg.reload(); pg.wait_for_timeout(9000)
        t=pg.inner_text("body"); i=t.find("TEMEL GÖRÜNÜM")
        print("==",kod, t[i:i+900].replace("\n"," | ") if i>=0 else "temel yok")
        h=pg.locator("h2",has_text="Temel görünüm")
        if h.count():
            h.first.scroll_into_view_if_needed(); pg.wait_for_timeout(800); pg.screenshot(path=f"denetim_graf/v_{kod.replace('/','_')}.png")
            pg.evaluate("window.scrollBy(0,650)"); pg.wait_for_timeout(500); pg.screenshot(path=f"denetim_graf/v_{kod.replace('/','_')}_2.png")
    pg.goto(U+"#piyasa/temel/kripto"); pg.reload(); pg.wait_for_timeout(8000)
    pg.screenshot(path="denetim_graf/p_kripto.png"); print("== kripto liste", pg.inner_text("#py-ic")[:700].replace("\n"," | "))
    print("logo sayısı", pg.eval_on_selector_all("#py-ic img.lg","e=>e.filter(x=>x.complete&&x.naturalWidth>0).length"))
    pg.click("[data-tz=emtia]"); pg.wait_for_timeout(5000)
    pg.screenshot(path="denetim_graf/p_emtia.png"); print("== emtia liste", pg.inner_text("#py-ic")[:600].replace("\n"," | "))
    print("logo sayısı", pg.eval_on_selector_all("#py-ic img.lg","e=>e.filter(x=>x.complete&&x.naturalWidth>0).length"))
    print("JS hataları:",hatalar)
