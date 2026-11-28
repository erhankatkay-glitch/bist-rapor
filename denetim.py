import subprocess, sys, os
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","webkit"],check=True,capture_output=True)
from playwright.sync_api import sync_playwright
os.makedirs("denetim_graf",exist_ok=True)
U="https://erhankatkay-glitch.github.io/bist-rapor/"
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices["iPhone 13"]); pg=ctx.new_page()
    hatalar=[]; pg.on("pageerror",lambda e:hatalar.append(str(e)))
    pg.goto(U); pg.wait_for_timeout(5000)
    for kod in ("THYAO","BTC%2FUSDT","ALTIN"):
        pg.goto(U+"#v/"+kod); pg.reload(); pg.wait_for_timeout(12000)
        k=pg.query_selector("#tv-kutu")
        if k:
            k.scroll_into_view_if_needed(); pg.wait_for_timeout(800)
            pg.screenshot(path=f"denetim_graf/grafik_{kod.replace('%2F','_')}.png")
            print("==",kod,"canvas:",pg.eval_on_selector_all("#tv-kutu canvas","e=>e.length"),"araç:",pg.inner_text("#tv-arac")[:80].replace("\n"," | "))
        t=pg.inner_text("body"); i=t.find("FIBOAYNA"); print("fibo kart:", t[i:i+400].replace("\n"," | ") if i>=0 else "yok")
        h=pg.locator("h2",has_text="FiboAyna")
        if h.count(): h.first.scroll_into_view_if_needed(); pg.wait_for_timeout(500); pg.screenshot(path=f"denetim_graf/fibokart_{kod.replace('%2F','_')}.png")
    pg.goto(U+"#firsat/fibo"); pg.reload(); pg.wait_for_timeout(9000)
    pg.screenshot(path="denetim_graf/fibo_liste.png"); print("== fibo liste", pg.inner_text("#fr-ic")[:900].replace("\n"," | "))
    pg.evaluate("()=>localStorage.setItem('kk_fibo_alt',JSON.stringify('perf'))"); pg.goto(U+"#firsat/fibo"); pg.reload(); pg.wait_for_timeout(7000)
    pg.screenshot(path="denetim_graf/fibo_perf.png"); print("== fibo perf", pg.inner_text("#fr-ic")[:500].replace("\n"," | "))
    pg.goto(U+"#portfoy"); pg.wait_for_timeout(4000); pg.click("[data-p=oto]"); pg.wait_for_timeout(6000)
    pg.screenshot(path="denetim_graf/oto.png"); print("== oto", pg.inner_text("#pf-ic")[:500].replace("\n"," | "))
    print("JS hataları:",hatalar[:6])
