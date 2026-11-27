"""10c-1: gerçek veriyle rejim hesabı + ilk yayın + uygulama görünümü."""
import os, sys, json, subprocess, time, shutil
import pandas as pd, yfinance as yf
import rejim as RJ, arastirma_firsat as AF
os.makedirs("denetim_graf", exist_ok=True); os.makedirs("cikti", exist_ok=True)
def an(veri): return [{"kod": k, "tf": {"G": {"h": d}}} for k, d in veri.items()]
def endeks(sem):
    d = yf.download(sem, period="3y", interval="1d", auto_adjust=False, progress=False)
    d.columns = [c[0] if isinstance(c, tuple) else c for c in d.columns]; d.index = d.index.tz_localize(None) if d.index.tz else d.index
    return d.dropna(subset=["Close"])
for p, veri_fn, sem in (("bist", lambda: AF.bist_veri(700), "XU100.IS"), ("abd", lambda: AF.abd_veri(200), "^GSPC")):
    t = time.time(); veri, onder = veri_fn(); veri.pop(onder, None)
    h = endeks(sem)
    r = RJ.hesapla(p, an(veri), h, "cikti", vix=RJ.vix_al() if p == "abd" else None)
    print(p, len(veri), "hisse,", round(time.time() - t), "sn ·", r["ozet"])
    print("  ", r["gerekce"], "| dağıtım günleri:", r["dagitim_gunleri"], "| FTD:", r["ftd"], "| hacim:", r["hacim_var"])
    import collections; print("   son 130 gün:", collections.Counter(r["durum_gecmis"]["durum"]))
    RJ.kart_ciz(r, f"denetim_graf/rejim_{p}.png")
subprocess.run([sys.executable, "yayinla.py", "cikti", "rejim ilk yayın (denetim)"], check=False)
# uygulama: Ekonomi paneli
time.sleep(5)
p = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501"],
                     stdout=open("st_log.txt", "w"), stderr=subprocess.STDOUT)
time.sleep(20)
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = br.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2).new_page()
    pg.on("pageerror", lambda e: print("pageerror:", str(e)[:300]))
    pg.goto("http://localhost:8501", timeout=120000); pg.wait_for_selector('[data-testid="stTab"]', timeout=180000); pg.wait_for_timeout(12000)
    pg.evaluate("localStorage.setItem('kk_gorulen', JSON.stringify(Array(1)))")
    pg.evaluate("window.kkGitAlt('Ana Sayfa|Ekonomi')"); pg.wait_for_timeout(6000)
    el = pg.locator(".rj").first
    try:
        el.scroll_into_view_if_needed(); pg.wait_for_timeout(800); pg.screenshot(path="denetim_graf/ekonomi_rejim.png")
    except Exception as ex: print("panel yok:", ex)
    print("panel sayısı:", pg.evaluate("document.querySelectorAll('.rj').length"))
    pg.evaluate("window.kkGitAlt('Keşfet|Fırsatlar')"); pg.wait_for_timeout(6000); pg.screenshot(path="denetim_graf/secki_rejim.png")
    print("seçki satırı:", pg.evaluate("(document.querySelector('.rj-k')||{}).innerText"))
    br.close()
p.terminate()
