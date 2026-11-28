"""Canlı: Gemini yorum katmanı (Ekip özeti) geliyor mu."""
import os
os.makedirs("denetim_graf", exist_ok=True)
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = br.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2).new_page()
    pg.goto("https://cuz9rz7rlsx7bfwolrb8xq.streamlit.app", timeout=180000)
    fr = None
    for _ in range(100):
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
    for kod in ("BTC/USDT|kripto|seviye|",):
        ist = fr.evaluate("(()=>{const r=[...document.querySelectorAll('.oc')].find(x=>x.innerText.includes('BTC')); return r? r.getAttribute('data-kk') : null;})()") or "BTC/USDT|Kripto|seviye|"
        print("   istek:", ist)
        fr.evaluate(f"window.kkIstek('{ist}')")
        ok = False
        for _ in range(100):
            fr.wait_for_timeout(3000)
            if fr.evaluate("[...document.querySelectorAll('summary')].some(x=>x.innerText.includes('Araştırma ekibi'))") and \
               not fr.evaluate("!!document.querySelector('[data-testid=stStatusWidget]')"): ok = True; break
        fr.evaluate("(()=>{const s=[...document.querySelectorAll('summary')].find(x=>x.innerText.includes('Araştırma ekibi')); if(s && !s.parentElement.open){s.click();} s&&s.scrollIntoView();})()")
        fr.wait_for_timeout(3000)
        oz = fr.evaluate("(()=>{const k=[...document.querySelectorAll('.ko')].find(x=>x.innerText.includes('Ekip özeti')); return k? k.innerText : null;})()")
        print("CANLI", kod.split("|")[0], "| bölüm:", ok, "| Ekip özeti:", (oz or "YOK")[:900].replace("\n", " ‖ "))
        print("   teşhis:", fr.evaluate("[...document.querySelectorAll('[data-testid=stCaptionContainer]')].map(x=>x.innerText).filter(t=>t.includes('Yapay zekâ özeti'))"))
        print("   hata:", fr.evaluate("[...document.querySelectorAll('[data-testid=stException]')].map(x=>x.innerText.slice(0,200))"))
        pg.screenshot(path=f"denetim_graf/yz_{kod.split('|')[0].replace('/', '_')}.png")
    br.close()
