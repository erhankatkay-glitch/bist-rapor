"""Aşama 14: gerçek veriyle ekip raporu + PDF + canlı uygulama."""
import os, sys, json, subprocess
os.makedirs("denetim_graf", exist_ok=True)
subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", "bulten", os.environ["GH_URL"], "onceki"])
oku = lambda y: json.load(open(os.path.join("onceki", y), encoding="utf-8")) if os.path.exists(os.path.join("onceki", y)) else None
import bist_teknik as T, bist_teknik_rapor as TR, arastirma_ekibi as EK
for kod, pz in (("THYAO", "bist"), ("NVDA.US", "abd"), ("BTC/USDT", "kripto")):
    s = T.analiz(kod)
    op = s.get("opsiyon") or ((oku("opsiyon/ozet.json") or {}).get("paralar") or {}).get("BTC") if pz == "kripto" else None
    e = EK.rapor(s, None, oku(f"firsat/{pz}/istatistik.json"), oku(f"rejim/{pz}.json") if pz in ("bist", "abd") else None, op)
    print(f"\n=== {kod}: {e['ozet']}")
    print("  bozucu:", e["tez_bozucular"][:3])
    for rl in e["roller"]:
        print(f"  [{rl['ad']}]", " | ".join(rl["bulgular"][:3])[:420])
    f = TR.teknik_pdf(s, f"denetim_graf/{kod.replace('/', '_')}.pdf", ekip=e); print("  PDF", os.path.getsize(f))
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = br.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2).new_page()
    pg.goto("https://cuz9rz7rlsx7bfwolrb8xq.streamlit.app/?kk=THYAO|hisse|seviye|", timeout=180000)
    fr = None
    for _ in range(90):
        pg.wait_for_timeout(3000)
        for f_ in pg.frames:
            try:
                if f_.evaluate("!!document.querySelector('[data-testid=stTab]')"): fr = f_; break
            except Exception: pass
        if fr: break
    for _ in range(40):
        if fr.evaluate("typeof window.kkIstek === 'function'"): break
        fr.wait_for_timeout(2000)
    fr.evaluate("localStorage.setItem('kk_gorulen', JSON.stringify(Array.from({length:80},(_, i)=>'x'+i)))")
    fr.evaluate("window.kkIstek && window.kkIstek('THYAO|hisse|seviye|')")
    for _ in range(60):
        fr.wait_for_timeout(3000)
        if fr.evaluate("[...document.querySelectorAll('summary')].some(x=>x.innerText.includes('Araştırma ekibi'))"): break
    print("CANLI ekip bölümü:", fr.evaluate("[...document.querySelectorAll('summary')].some(x=>x.innerText.includes('Araştırma ekibi'))"),
          "| hata:", fr.evaluate("[...document.querySelectorAll('[data-testid=stException]')].map(x=>x.innerText.slice(0,200))"))
    fr.evaluate("(()=>{const s=[...document.querySelectorAll('summary')].find(x=>x.innerText.includes('Araştırma ekibi')); if(s){s.click(); s.scrollIntoView();}})()")
    fr.wait_for_timeout(3000); pg.screenshot(path="denetim_graf/ekip1.png"); pg.mouse.wheel(0, 700); fr.wait_for_timeout(800); pg.screenshot(path="denetim_graf/ekip2.png")
    br.close()
