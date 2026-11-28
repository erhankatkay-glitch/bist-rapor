import subprocess, sys; subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "webkit"], check=True)
import asyncio
from playwright.async_api import async_playwright
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); c=await b.new_context(**p.devices["iPhone 13"]); pg=await c.new_page(); hata=[]
    pg.on("pageerror",lambda e:hata.append(str(e)))
    await pg.goto("https://erhankatkay-glitch.github.io/bist-rapor/"); await pg.wait_for_timeout(6000)
    print("SABAH", await pg.locator("#s-ozet details").count())
    await pg.tap("nav button[data-s=piyasa]"); await pg.wait_for_timeout(3000)
    for k in ["takvim","ekonomi","tarayici","karsilastir","genel"]:
      await pg.tap(f"[data-py={k}]"); await pg.wait_for_timeout(3500)
      print(k.upper(), (await pg.inner_text("#py-ic"))[:160].replace("\n"," | "))
    await pg.tap("[data-py=tarayici]"); await pg.wait_for_timeout(2500); await pg.locator("[data-th]").nth(1).tap(); await pg.wait_for_timeout(1500)
    t=await pg.inner_text("#py-ic"); i=t.find("SONUÇ"); print("HAZIR", t[i-6:i+120].replace("\n"," | "))
    await pg.tap("nav button[data-s=firsat]"); await pg.wait_for_timeout(2500)
    for k in ["son","perf"]:
      await pg.tap(f"[data-fr={k}]"); await pg.wait_for_timeout(3000); print("FR", k, (await pg.inner_text("#fr-ic"))[:140].replace("\n"," | "))
    print("HATA", hata); await b.close()
asyncio.run(main())
