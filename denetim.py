import subprocess, sys; subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "webkit"], check=True)
import os, json, urllib.request, asyncio
sys.path.insert(0, ".")
os.makedirs("denetim_graf", exist_ok=True)
import logolar as LG
for k in ["XU100", "S&P 500", "Nasdaq", "Dow Jones", "DAX", "FTSE 100", "CAC 40", "Euro Stoxx 50", "Nikkei 225", "Hang Seng", "Şanghay", "KOSPI", "Sensex", "ASX 200", "S&P/TSX", "Bovespa", "VIX", "ALTIN", "BRENT", "USD/TRY", "EUR/USD", "Dolar endeksi", "US10Y"]:
    print("LOGO", k, "OK" if LG.logo_dosya(k, None) else "YOK")
R = "https://raw.githubusercontent.com/erhankatkay-glitch/bist-rapor/bulten/"
import dunya, rejim, opsiyon
dunya.kart_ciz(json.load(urllib.request.urlopen(R + "dunya/ozet.json")), "denetim_graf/dunya.png")
rejim.kart_ciz(json.load(urllib.request.urlopen(R + "rejim/abd.json")), "denetim_graf/rejim.png")
opsiyon.kart_ciz(json.load(urllib.request.urlopen(R + "opsiyon/ozet.json")), "denetim_graf/opsiyon.png")
from playwright.async_api import async_playwright
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); c=await b.new_context(**p.devices["iPhone 13"]); pg=await c.new_page()
    await pg.goto("https://erhankatkay-glitch.github.io/bist-rapor/"); await pg.wait_for_timeout(8000)
    print("PWA logo", await pg.evaluate("(()=>{const l=[...document.querySelectorAll('img.lg')];return {toplam:l.length, yuklu:l.filter(i=>i.complete&&i.naturalWidth>0).length}})()"))
    await pg.screenshot(path="denetim_graf/pwa_ozet.png")
    await pg.tap("nav button[data-s=piyasa]"); await pg.wait_for_timeout(5000)
    print("PWA piyasa", await pg.evaluate("(()=>{const l=[...document.querySelectorAll('#s-piyasa img.lg')];return {toplam:l.length, yuklu:l.filter(i=>i.complete&&i.naturalWidth>0).length}})()"))
    await b.close()
asyncio.run(main())
