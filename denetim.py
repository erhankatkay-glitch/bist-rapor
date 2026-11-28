import subprocess, sys; subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "webkit"], check=True)
import asyncio, json, urllib.request
from playwright.async_api import async_playwright
R="https://raw.githubusercontent.com/erhankatkay-glitch/bist-rapor/bulten/"
d=json.load(urllib.request.urlopen(R+"canli/bist.json")); print("CANLI THYAO", d["fiyat"].get("THYAO"), d["zaman"])
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); c=await b.new_context(**p.devices["iPhone 13"]); pg=await c.new_page(); hata=[]
    pg.on("pageerror",lambda e:hata.append(str(e)))
    await pg.goto("https://erhankatkay-glitch.github.io/bist-rapor/"); await pg.wait_for_timeout(6000)
    for q in ["thyao","nvda","pepe"]:
      await pg.fill("#oara", q); await pg.wait_for_timeout(700); print("ARA", q, (await pg.inner_text("#osonuc"))[:110].replace("\n"," | "))
    await pg.fill("#oara","thyao"); await pg.wait_for_timeout(500); await pg.locator("#osonuc a").first.tap(); await pg.wait_for_timeout(3000)
    print("THYAO", (await pg.inner_text("#s-varlik"))[:230].replace("\n"," | "))
    await pg.tap("#yenile2"); await pg.wait_for_timeout(4000); print("YENILE", await pg.inner_text("#yenile"), (await pg.inner_text("#s-varlik"))[:60].replace("\n"," | "))
    print("HATA", hata); await b.close()
asyncio.run(main())
