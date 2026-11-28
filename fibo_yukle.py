# -*- coding: utf-8 -*-
"""FiboAyna modüllerini şifreli paketten (ozel/fibo.enc) açar ve çalıştırır.
Göstergenin kuralları kullanıcıya aittir: depoda yalnız şifreli hâli durur; anahtar GitHub Secrets'ta (FIBO_ANAHTAR).
Açılan dosyalar yalnız çalışan makinenin geçici klasörüne yazılır, depoya / yayına girmez.
Kullanım: python fibo_yukle.py <modul> [argümanlar...]   (ör. python fibo_yukle.py fibo_arastirma cikti bist 150)"""
import io
import os
import runpy
import sys
import tempfile
import zipfile

PAKET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ozel", "fibo.enc")


def ac():
    """Paketi açar, klasörünü sys.path'e ekler; klasör yolunu döndürür."""
    from cryptography.fernet import Fernet
    anahtar = os.environ.get("FIBO_ANAHTAR", "").strip()
    if not anahtar: raise SystemExit("FIBO_ANAHTAR tanımlı değil (GitHub Secrets).")
    veri = Fernet(anahtar.encode()).decrypt(open(PAKET, "rb").read())
    hedef = tempfile.mkdtemp(prefix="fibo_")
    zipfile.ZipFile(io.BytesIO(veri)).extractall(hedef)
    sys.path.insert(0, hedef)
    if os.getcwd() not in sys.path: sys.path.insert(1, os.getcwd())
    return hedef


def sifrele_klasor(klasor, hedef):
    """Sonuç klasörünü aynı anahtarla şifreler (iş çıktısı açık depoda herkese görünebildiği için)."""
    from cryptography.fernet import Fernet
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for kok, _, dosyalar in os.walk(klasor):
            for f in dosyalar:
                yol = os.path.join(kok, f); z.write(yol, os.path.relpath(yol, klasor))
    open(hedef, "wb").write(Fernet(os.environ["FIBO_ANAHTAR"].strip().encode()).encrypt(b.getvalue()))


if __name__ == "__main__":
    if sys.argv[1] == "sifrele":      # python fibo_yukle.py sifrele <klasör> <hedef.enc>
        sifrele_klasor(sys.argv[2], sys.argv[3]); sys.exit(0)
    ac()
    mod = sys.argv[1]; sys.argv = [mod + ".py"] + sys.argv[2:]
    runpy.run_module(mod, run_name="__main__")
