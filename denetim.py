"""Aşama 7 araştırması: yeni kurulumların (OB, BREAKER, HARM) ve RVOL filtresinin geçmiş testi."""
import subprocess, sys, os
os.makedirs("denetim_graf", exist_ok=True)
r = subprocess.run([sys.executable, "arastirma_firsat.py", "kripto4s", "kriptog", "bistg", "bist4s", "abdg", "abdh"], text=True)
for f in os.listdir("."):
    if f.startswith("arastirma_") and (f.endswith(".json")):
        os.system(f"cp {f} denetim_graf/")
