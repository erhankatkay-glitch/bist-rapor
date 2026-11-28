"""Anlık emtia: kaynak karşılaştırma + panel + alarm + canlı uygulama."""
import os
os.makedirs("denetim_graf", exist_ok=True)
import canli_emtia as CE, alarm as A, bist_makro as MK
for kod in ("GUMUS", "PLATIN", "BAKIR", "WTI", "DOGALGAZ"):
    ref, _ = None, None
    try: ref = float(__import__("yfinance").Ticker(A._yahoo(kod)).fast_info["lastPrice"])
    except Exception as ex: print(kod, "yahoo", ex)
    r = CE.fiyat(kod, referans=ref)
    print(f"{kod:9s} Yahoo {ref} | anlık {r and round(r['fiyat'], 4)} {r and r['kaynak']} d24 {r and round(r['d24'] or 0, 4)} zaman {r and r['zaman']:%H:%M:%S}" if r else f"{kod} anlık yok (yahoo {ref})")
    print("   alarm.anlik:", A.anlik(kod))
PV = MK.piyasa_paneli()
for ad in ("Ons altın", "Gümüş", "Platin", "Bakır", "WTI petrol", "Doğal gaz", "Brent petrol"):
    v = PV.get(ad, {}); print(f"PANEL {ad:12s} {v.get('deger')} · {v.get('kaynak')} · d1G {v.get('d1G') and round(v['d1G'], 4)}")
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
    for _ in range(40):
        if fr.evaluate("typeof window.kkGitAlt === 'function'"): break
        fr.wait_for_timeout(2000)
    fr.evaluate("localStorage.setItem('kk_gorulen', JSON.stringify(Array.from({length:80},(_, i)=>'x'+i)))")
    fr.wait_for_timeout(5000)
    fr.locator("[data-testid=stRadio] label:has-text('Emtia')").first.click(); fr.wait_for_timeout(8000)
    print("CANLI kartlar:", fr.evaluate("[...document.querySelectorAll('.serit-mk .mk')].map(x=>x.innerText.replace(/\\n/g,' ')+' ['+((x.querySelector('.mk-n')||{}).title||'')+']').slice(0,8)"))
    print("CANLI hata:", fr.evaluate("document.querySelectorAll('[data-testid=stException]').length"))
    pg.screenshot(path="denetim_graf/emtia.png")
    br.close()
