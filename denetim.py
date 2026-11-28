import subprocess, sys; subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], check=True)
import asyncio, os
from playwright.async_api import async_playwright
os.makedirs("denetim_graf", exist_ok=True)
PWA="https://erhankatkay-glitch.github.io/bist-rapor/"
UYG="https://cuz9rz7rlsx7bfwolrb8xq.streamlit.app/?kk=BTC%2FUSDT%7CKripto%7Cseviye%7C"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={"width":390,"height":844},device_scale_factor=2)
    pg=await c.new_page(); hata=[]
    pg.on("pageerror",lambda e:hata.append(str(e)))
    await pg.goto(PWA); await pg.wait_for_timeout(5000)
    o=[]
    for _ in range(8):
      o.append(await pg.inner_text("#c-BTCUSDT b")); await pg.wait_for_timeout(1000)
    print("CANLI BTC", o, "farkli", len(set(o)), "bant", (await pg.inner_text("#dus"))[:90].replace("\n"," "))
    print("SW:", await pg.evaluate("navigator.serviceWorker.controller ? 'kontrol' : 'yok'"))
    print("manifest:", (await (await pg.request.get(PWA+"manifest.webmanifest")).json())["name"])
    for s in ["ozet","firsat","bildirim","haber","piyasa"]:
      await pg.click(f"nav button[data-s={s}]"); await pg.wait_for_timeout(2500)
      await pg.screenshot(path=f"denetim_graf/pwa_{s}.png")
      t=await pg.inner_text(f"#s-{s}"); print("SEKME",s,len(t),t[:200].replace("\n"," | "))
    await pg.reload(); await pg.wait_for_timeout(3000)
    print("SW2:", await pg.evaluate("navigator.serviceWorker.controller ? 'kontrol' : 'yok'"))
    await c.set_offline(True); await pg.reload(); await pg.wait_for_timeout(4000)
    t=await pg.inner_text("body"); print("CEVRIMDISI", len(t), "Ralli" in t or "rejim" in t.lower(), t[:250].replace("\n"," | "))
    await pg.screenshot(path="denetim_graf/pwa_cevrimdisi.png")
    print("PWA HATA", hata)
    await c.set_offline(False)
    # derin bağlantı
    q=await c.new_page(); await q.goto(UYG, timeout=120000)
    fr=None
    for _ in range(90):
      for f in q.frames:
        try:
          if await f.evaluate("!!window.kkIstek"): fr=f; break
        except Exception: pass
      if fr: break
      await q.wait_for_timeout(2000)
    print("UYG cerceve", bool(fr))
    if fr:
      for _ in range(40):
        t=await fr.inner_text("body")
        if "Hazır" in t or "Teknik analiz yapılamadı" in t: break
        await q.wait_for_timeout(3000)
      t=await fr.inner_text("body")
      i=t.find("BTC/USDT"); print("DERIN", "Hazır" in t, "yapılamadı" in t, t[i-50:i+300].replace("\n"," | ") if i>=0 else t[:300])
      print("URL", fr.url[:200])
      await q.screenshot(path="denetim_graf/derin.png", full_page=False)
    await b.close()
asyncio.run(main())
