import subprocess, sys; subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "webkit"], check=True)
import asyncio
from playwright.async_api import async_playwright
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); c=await b.new_context(**p.devices["iPhone 13"]); pg=await c.new_page(); hata=[]
    pg.on("pageerror",lambda e:hata.append(str(e)))
    await pg.goto("https://erhankatkay-glitch.github.io/bist-rapor/"); await pg.wait_for_timeout(5000)
    l=pg.locator("#s-ozet a.bild"); print("OZET bildirim link:", await l.count(), await l.first.get_attribute("href"))
    async with c.expect_page() as yp: await l.first.tap()
    y=await yp.value; print("ACILAN:", y.url[:160])
    await pg.tap("nav button[data-s=bildirim]"); await pg.wait_for_timeout(1500)
    hs=[await x.get_attribute("href") for x in await pg.locator("#s-bildirim a.bild").all()][:8]; print("BILDIRIM hrefs:", hs)
    print("HATA", hata); await b.close()
asyncio.run(main())
