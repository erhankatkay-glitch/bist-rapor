"""Aşama 10 kuru çalıştırma: yeni alarm türleri gerçek veriyle (Telegram'a gönderilmez)."""
import os, time
os.makedirs("denetim_graf", exist_ok=True)
import alarm as AL
K = AL.kurallar("""THYAO EMA 5/10
ASELS EMA 20/50
ASTOR HACIM > 1.5
BTC/USDT FIB 0.618
GARAN KIRILIM
XU100 FVG
NVDA.US BOS
ETH/USDT HARMONIK
KCHOL SINYAL
AKBNK SINYAL
THYAO TEMEL
TAKVIM
PORTFOY RISK 1""")
t0 = time.time()
b, y = AL.tara(K, {})
print("süre", round(time.time() - t0), "sn ·", len(b), "bildirim")
for m in b: print("  ", m)
b2, _ = AL.tara(K, y)
print("ikinci tur (tekrar engeli):", len(b2), "bildirim", b2[:3])
