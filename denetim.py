import subprocess, sys; subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "webkit"], check=True)
import asyncio, os
from playwright.async_api import async_playwright
os.makedirs("denetim_graf", exist_ok=True)
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); c=await b.new_context(**p.devices["iPhone 13"]); pg=await c.new_page(); hata=[]
    pg.on("pageerror",lambda e:hata.append(str(e)))
    await pg.goto("https://erhankatkay-glitch.github.io/bist-rapor/"); await pg.wait_for_timeout(5000)
    await pg.tap("#c-BTCUSDT"); await pg.wait_for_timeout(2500)
    print("KRIPTO", await pg.evaluate("location.hash"), (await pg.inner_text("#s-varlik"))[:150].replace("\n"," | "))
    await pg.screenshot(path="denetim_graf/v_btc.png")
    await pg.tap(".geri"); await pg.wait_for_timeout(1000)
    await pg.tap("nav button[data-s=firsat]"); await pg.wait_for_timeout(2000)
    await pg.locator("#s-firsat a.kart").first.tap(); await pg.wait_for_timeout(2500)
    print("FIRSAT->", await pg.evaluate("location.hash"), (await pg.inner_text("#s-varlik"))[:120].replace("\n"," | "))
    await pg.go_back(); await pg.wait_for_timeout(800)
    await pg.tap("nav button[data-s=piyasa]"); await pg.wait_for_timeout(2500)
    await pg.fill("#kara", "asel"); await pg.wait_for_timeout(400)
    await pg.locator("#kliste a").first.tap(); await pg.wait_for_timeout(2500)
    t=await pg.inner_text("#s-varlik"); print("ASELS", len(t), "ekip" , "Araştırma ekibi" in t.lower() or "ARAŞTIRMA" in t, t[:120].replace("\n"," | "))
    await pg.screenshot(path="denetim_graf/v_asels.png", full_page=True)
    print("HATA", hata); await b.close()
asyncio.run(main())
