import subprocess, sys, os, json
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","webkit"],check=True,capture_output=True)
from playwright.sync_api import sync_playwright
os.makedirs("denetim_graf",exist_ok=True)
U="https://erhankatkay-glitch.github.io/bist-rapor/"
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices["iPhone 13"]); pg=ctx.new_page()
    hatalar=[]; pg.on("pageerror",lambda e:hatalar.append(str(e)))
    def git(h,ad,bekle=6000):
        pg.goto(U+h); pg.wait_for_timeout(bekle)
        pg.screenshot(path=f"denetim_graf/{ad}.png",full_page=True)
        return pg.inner_text("body")
    for kod in ("THYAO","AAPL.US","BTCUSDT"):
        t=git("#v/"+kod,"v_"+kod.replace(".","_"),9000)
        print("==",kod,"temel:", "Temel" in t, "PDF:", "PDF" in t)
        i=t.find("Temel"); print(t[i:i+500].replace("\n"," | ") if i>=0 else "-")
        hrefs=pg.eval_on_selector_all("a[href*='releases/download']","e=>e.map(x=>x.href)"); print("pdf linkleri",hrefs)
    git("#piyasa","piyasa",5000)
    for el in pg.query_selector_all("button, .sekme, [data-alt]"):
        try:
            if el.inner_text().strip()=="Temel": el.click(); break
        except Exception: pass
    pg.wait_for_timeout(6000); pg.screenshot(path="denetim_graf/p_temel.png",full_page=True)
    t=pg.inner_text("body"); i=t.find("Fırsat"); print("== Piyasa Temel:", t[:1500].replace("\n"," | "))
    for mod in ("ABD","Resmi","Genç","Küçük"):
        for el in pg.query_selector_all("button"):
            try:
                if mod.lower() in el.inner_text().strip().lower(): el.click(); break
            except Exception: pass
        pg.wait_for_timeout(4000); pg.screenshot(path=f"denetim_graf/p_temel_{mod}.png",full_page=True)
        t=pg.inner_text("body"); print("==",mod, t[t.find("skor")-200:t.find("skor")+600].replace("\n"," | "))
    # PDF link HEAD
    import urllib.request
    try:
        r=urllib.request.urlopen(urllib.request.Request("https://github.com/erhankatkay-glitch/bist-rapor/releases/download/raporlar/AAPL_US_Teknik.pdf",method="HEAD"));print("PDF HEAD",r.status,r.headers.get("Content-Type"),r.headers.get("Content-Length"))
    except Exception as x: print("PDF HEAD hata",x)
    print("JS hataları:",hatalar)
