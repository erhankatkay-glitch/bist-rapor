import subprocess, sys; subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "webkit"], check=True)
import asyncio, os
from playwright.async_api import async_playwright
os.makedirs("denetim_graf", exist_ok=True)
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); c=await b.new_context(**p.devices["iPhone 13"]); pg=await c.new_page(); hata=[]
    pg.on("pageerror",lambda e:hata.append(str(e))); pg.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
    await pg.goto("https://erhankatkay-glitch.github.io/bist-rapor/"); await pg.wait_for_timeout(5000)
    await pg.tap("nav button[data-s=portfoy]"); await pg.wait_for_timeout(3000)
    await pg.fill("#pf-m","THYAO 100 @ 280\nNVDA 5\nBTC/USDT 0,05\nGRAMALTIN 10"); await pg.tap("#pf-k"); await pg.wait_for_timeout(800)
    print("VARLIK", (await pg.inner_text("#pf-ic"))[:300].replace("\n"," | "))
    await pg.screenshot(path="denetim_graf/pf_ios.png")
    await pg.tap("[data-p=sanal]"); await pg.wait_for_timeout(800); await pg.tap("#sn-yeni"); await pg.wait_for_timeout(300)
    await pg.fill("#sf-kod","ASELS"); await pg.fill("#sf-stop","315"); await pg.fill("#sf-hedef","370"); await pg.fill("#sf-neden","Test işlemi - formasyon")
    await pg.locator("#sf-neden").dispatch_event("change"); await pg.wait_for_timeout(1500)
    print("FORM", (await pg.inner_text("#sf-kl"))[:200].replace("\n"," | "))
    await pg.tap("#sf-ac"); await pg.wait_for_timeout(800); print("ACIK", (await pg.inner_text("#pf-ic"))[:220].replace("\n"," | "))
    await pg.tap("[data-p=risk]"); await pg.wait_for_timeout(500); await pg.fill("[data-r=kod]","SOL/USDT"); await pg.fill("[data-r=stop]","65"); await pg.wait_for_timeout(500)
    print("RISK", (await pg.inner_text("#rk-s"))[:150].replace("\n"," | "))
    print("HATA", hata); await b.close()
asyncio.run(main())
