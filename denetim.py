import subprocess, sys; subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], check=True)
import asyncio, os, time
from playwright.async_api import async_playwright
os.makedirs("denetim_graf", exist_ok=True)
UYG="https://cuz9rz7rlsx7bfwolrb8xq.streamlit.app/"
JS="""()=>{const tl=[...document.querySelectorAll('.stTabs [role=tablist]')];
 const gor=e=>{const r=e.getBoundingClientRect();return r.height>0 && getComputedStyle(e).visibility!=='hidden' && getComputedStyle(document.querySelector('[data-testid=stMain]')||document.body).visibility!=='hidden'};
 return {hazir:document.body.classList.contains('kk-hazir'), sekme:tl.length, gorunen:tl.filter(gor).map(t=>t.innerText.slice(0,30).replace(/\\n/g,'/')), nav:!!document.getElementById('kk-nav')}}"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={"width":390,"height":844})
    for tur in range(2):
      q=await c.new_page(); t0=time.time(); await q.goto(UYG, timeout=120000)
      fr=None; kotu=0; son=None
      for i in range(120):
        for f in q.frames:
          try:
            r=await f.evaluate(JS)
            if r["sekme"]: fr=f; son=r; break
          except Exception: pass
        if son:
          if son["gorunen"]: kotu+=1; print(f"t={time.time()-t0:.1f} GORUNUR", son)
          if son["hazir"]: print(f"t={time.time()-t0:.1f} HAZIR", son); break
        await q.wait_for_timeout(250)
      await q.wait_for_timeout(1500); await q.screenshot(path=f"denetim_graf/acilis{tur}.png")
      print("TUR", tur, "kotu", kotu, "son", son); await q.close()
    await b.close()
asyncio.run(main())
