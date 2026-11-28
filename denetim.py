import subprocess, sys; subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium", "webkit"], check=True)
import asyncio, os, io
from playwright.async_api import async_playwright
os.makedirs("denetim_graf", exist_ok=True)
PWA="https://erhankatkay-glitch.github.io/bist-rapor/?ac=1"
async def main():
  async with async_playwright() as p:
    ip=p.devices["iPhone 13"]
    b=await p.webkit.launch(); c=await b.new_context(**ip); pg=await c.new_page(); hata=[]
    pg.on("pageerror",lambda e:hata.append(str(e)))
    await pg.goto(PWA); await pg.wait_for_timeout(5000)
    print("SURUM canli:", await pg.locator(".canli").count(), "bant:", await pg.locator("#dus.ac").count(), "cuzdan:", (await pg.inner_text("#cuzdan"))[:40].replace("\n"," "))
    for s in ["firsat","bildirim","haber","piyasa","ozet"]:
      await pg.tap(f"nav button[data-s={s}]"); await pg.wait_for_timeout(1500)
      acik=await pg.evaluate("document.querySelector('.sayfa.ac').id")
      print("DOKUN", s, "->", acik, len(await pg.inner_text("#s-"+s)))
    await pg.tap("nav button[data-s=firsat]"); await pg.wait_for_timeout(800); await pg.tap("[data-f=Kripto]"); await pg.wait_for_timeout(400)
    print("SUZGEC kripto kart:", await pg.locator("#s-firsat a.kart").count())
    await pg.tap("nav button[data-s=ozet]"); await pg.wait_for_timeout(1500); await pg.tap("#bn-bagla"); await pg.wait_for_timeout(500)
    print("BN panel:", await pg.locator("#bn-k").count())
    await pg.screenshot(path="denetim_graf/ios_ozet.png")
    b1=await pg.inner_text("#c-BTCUSDT b"); await pg.wait_for_timeout(6000); print("BTC", b1, await pg.inner_text("#c-BTCUSDT b"))
    print("HATA", hata); await b.close()
    # Streamlit: ekstre yükleme
    import pandas as pd
    df=pd.DataFrame([["Portföy Ekstresi",None,None],["Menkul Kıymet","Kullanılabilir Adet","Ort. Maliyet"],["THYAO.E",100,280.5],["ASELS.E",25,300]])
    df.to_excel("ekstre_test.xlsx",index=False,header=False)
    b=await p.chromium.launch(); c=await b.new_context(viewport={"width":390,"height":844}); q=await c.new_page()
    await q.goto("https://cuz9rz7rlsx7bfwolrb8xq.streamlit.app/?p=BTC%2FUSDT%200%2C05", timeout=120000)
    fr=None
    for _ in range(90):
      for f in q.frames:
        try:
          if await f.evaluate("!!window.kkGitAlt"): fr=f; break
        except Exception: pass
      if fr: break
      await q.wait_for_timeout(2000)
    await q.wait_for_timeout(4000)
    await fr.evaluate("window.kkGitAlt('Portföy|Varlıklarım')"); await q.wait_for_timeout(4000)
    print("PF kutu:", repr(await fr.locator("textarea").first.input_value()))
    await fr.get_by_text("ekstresinden aktar").first.click(); await q.wait_for_timeout(1000)
    await fr.locator("input[type=file]").first.set_input_files("ekstre_test.xlsx")
    for _ in range(20):
      await q.wait_for_timeout(1500)
      v=await fr.locator("textarea").first.input_value()
      if "THYAO" in v: break
    print("PF sonra:", repr(v)); t=await fr.inner_text("body"); i=t.find("hisse aktarıldı"); print("NOT:", t[i-5:i+120].replace("\n"," "))
    await q.screenshot(path="denetim_graf/ekstre.png", full_page=False); await b.close()
asyncio.run(main())
