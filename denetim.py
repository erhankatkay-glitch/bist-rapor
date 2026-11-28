import subprocess, sys, os
os.makedirs("denetim_graf",exist_ok=True)
subprocess.run("git clone -q --depth 1 --branch bulten $GH_URL onceki",shell=True)
os.environ["DURUM_KLON"]="onceki"
print(subprocess.run([sys.executable,"temel_karne.py","cikti_k"],capture_output=True,text=True).stdout[-600:])
print(subprocess.run([sys.executable,"yayinla.py","cikti_k","Temel karne ilk arşiv"],capture_output=True,text=True))
