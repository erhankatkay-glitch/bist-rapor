"""Aşama 11: gerçek veri + yayın + uygulama + teknik karne."""
import os, sys, subprocess, time, json
os.makedirs("denetim_graf", exist_ok=True); os.makedirs("cikti", exist_ok=True)
subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", "bulten", os.environ["GH_URL"], "onceki"])
os.environ["DURUM_KLON"] = "onceki"
import korelasyon as KR
o = KR.hesapla("cikti", "onceki")
for c in o["ciftler"]: print(f"  {c['a']:13s} {c['b']:14s} 20g {c['c20']:+.2f} 60g {c['c60']:+.2f} 1y {c['c250']:+.2f} {'KIRILMA' if c['kirilma'] else ''}")
for g in o["goreceli"]: print("  RS", g["a"], "/", g["b"], round(g["d3"] or 0, 3), g["yorum"])
print("  sektör:", [(x["sektor"], x["rs"]) for x in o.get("sektor", [])[:4]], "…", [(x["sektor"], x["rs"]) for x in o.get("sektor", [])[-2:]])
KR.kart_ciz(o, "denetim_graf/korelasyon.png")
subprocess.run([sys.executable, "yayinla.py", "cikti", "korelasyon ilk yayın (denetim)"])
import bist_teknik as T
for kod in ("THYAO", "NVDA.US", "SOL/USDT"):
    s = T.analiz(kod); print(kod, [(d[0], d[1]) for d in s["tf"]["G"]["durum"] if "Göreceli" in d[0] or "beta" in d[0]])
time.sleep(5)
p = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501"],
                     stdout=open("st_log.txt", "w"), stderr=subprocess.STDOUT)
time.sleep(20)
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = br.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2).new_page()
    pg.on("pageerror", lambda e: print("pageerror:", str(e)[:300]))
    pg.goto("http://localhost:8501", timeout=120000); pg.wait_for_selector('[data-testid="stTab"]', timeout=180000, state="attached"); pg.wait_for_timeout(10000)
    pg.evaluate("localStorage.setItem('kk_gorulen', JSON.stringify(['x']))")
    pg.evaluate("window.kkGitAlt('Ana Sayfa|Ekonomi')"); pg.wait_for_timeout(8000)
    print("ilişki kartı:", pg.evaluate("document.querySelectorAll('.ko').length"), "| HATA:", pg.evaluate("document.querySelectorAll('[data-testid=stException]').length"))
    try:
        pg.locator(".ko").first.scroll_into_view_if_needed(); pg.wait_for_timeout(700); pg.screenshot(path="denetim_graf/ko1.png")
        pg.mouse.wheel(0, 1500); pg.wait_for_timeout(700); pg.screenshot(path="denetim_graf/ko2.png")
    except Exception as ex: print("ekran:", ex)
    br.close()
p.terminate()
