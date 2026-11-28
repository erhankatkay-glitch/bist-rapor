import subprocess, sys; subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "webkit"], check=True)
import asyncio, os, json, urllib.request
from playwright.async_api import async_playwright
os.makedirs("denetim_graf", exist_ok=True)
R="https://raw.githubusercontent.com/erhankatkay-glitch/bist-rapor/bulten/"
j=lambda y: json.load(urllib.request.urlopen(R+y))
d=j("dunya/ozet.json"); b=[x for x in d["borsalar"] if x["ad"]=="BIST 100"][0]; print("DUNYA BIST100", b["son"], b["d1"])
x=j("karne/bist/XU100.json"); print("KARNE XU100", x["tf"]["G"]["fiyat"], x["tf"]["G"]["degisim"], x["grafik"]["t"][-1])
t=j("karne/bist/THYAO.json"); print("KARNE THYAO", t["tf"]["G"]["fiyat"], t["grafik"]["t"][-1])
r=j("rejim/bist.json"); print("REJIM BIST", r["durum_ad"], r["maruziyet"], r["kapanis"], r["genislik"]["ust50"], r["genislik"]["ust200"])
for pz in ["bist","abd","kripto","emtia"]: print("LISTE", pz, len(j(f"karne/{pz}/liste.json")["varliklar"]))
async def main():
  async with async_playwright() as p:
    bw=await p.webkit.launch(); c=await bw.new_context(**p.devices["iPhone 13"]); pg=await c.new_page(); hata=[]
    pg.on("pageerror",lambda e:hata.append(str(e)))
    await pg.goto("https://erhankatkay-glitch.github.io/bist-rapor/"); await pg.wait_for_timeout(6000)
    for q in ["nvda","kchol","pepe","gumus"]:
      await pg.fill("#oara", q); await pg.wait_for_timeout(600)
      print("ARA", q, (await pg.inner_text("#osonuc"))[:90].replace("\n"," | "))
    await pg.fill("#oara","nvda"); await pg.wait_for_timeout(500); await pg.locator("#osonuc a").first.tap(); await pg.wait_for_timeout(3000)
    print("NVDA sayfa", (await pg.inner_text("#s-varlik"))[:160].replace("\n"," | "))
    await pg.screenshot(path="denetim_graf/nvda.png")
    await pg.go_back(); await pg.wait_for_timeout(800)
    await pg.tap("nav button[data-s=piyasa]"); await pg.wait_for_timeout(3000)
    print("PIYASA", (await pg.inner_text("#s-piyasa"))[:120].replace("\n"," | "))
    print("HATA", hata); await bw.close()
asyncio.run(main())
