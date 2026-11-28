# -*- coding: utf-8 -*-
"""Çıktıları 'bulten' dalına yayınlar (tek commit'lik yetim dal; dal hep küçük kalır).

Birden çok iş akışı aynı anda yayınlayabildiği için: dalın son hâli klonlanır, yalnızca bu işin
birimleri değiştirilir ve --force-with-lease ile itilir; arada başka iş yayınladıysa baştan denenir.
Birimler: cikti/ altındaki her klasör bütün olarak değiştirilir; 'firsat' ve 'durum' altında ise
alt klasör/dosya bazında değiştirilir (diğer piyasaların durumu korunur).
Kullanım: python yayinla.py <cikti_klasoru> "<mesaj>"   (GH_URL ortam değişkeni: kimlikli depo adresi)"""
import os, sys, shutil, subprocess, tempfile, time, random

ALT_BIRIM = {"firsat", "durum", "donem", "tarama", "rejim", "karne", "canli", "temel", "pdf", "fibo"}


def sh(*a, cwd=None, kontrol=True):
    r = subprocess.run(a, cwd=cwd, capture_output=True, text=True)
    if kontrol and r.returncode != 0:
        raise RuntimeError(f"{' '.join(a[:3])}…: {r.stderr.strip()[:300]}")
    return r


def birimler(cikti):
    out = []
    for ad in sorted(os.listdir(cikti)):
        yol = os.path.join(cikti, ad)
        if ad in ALT_BIRIM and os.path.isdir(yol):
            out += [os.path.join(ad, x) for x in sorted(os.listdir(yol))]
        else:
            out.append(ad)
    return out


def yayinla(cikti, mesaj):
    url = os.environ["GH_URL"]; dal = os.environ.get("YAYIN_DAL", "bulten")
    if not os.path.isdir(cikti) or not os.listdir(cikti):
        print("Yayınlanacak çıktı yok."); return
    B = birimler(cikti)
    for deneme in range(8):
        tmp = tempfile.mkdtemp()
        try:
            r = sh("git", "clone", "-q", "--depth", "1", "--branch", dal, url, tmp, kontrol=False)
            if r.returncode == 0:
                eski = sh("git", "rev-parse", "HEAD", cwd=tmp).stdout.strip()
            else:
                shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp); eski = ""
            for b in B:
                hedef, kaynak = os.path.join(tmp, b), os.path.join(cikti, b)
                if os.path.isdir(hedef): shutil.rmtree(hedef)
                elif os.path.exists(hedef): os.remove(hedef)
                os.makedirs(os.path.dirname(hedef) or tmp, exist_ok=True)
                (shutil.copytree if os.path.isdir(kaynak) else shutil.copy2)(kaynak, hedef)
            kd = os.path.join(tmp, "karne")   # karne/ altında yalnız piyasa klasörleri durur (eski düz dosyalar temizlenir)
            if any(b.startswith("karne" + os.sep) for b in B) and os.path.isdir(kd):
                for x in os.listdir(kd):
                    if os.path.isfile(os.path.join(kd, x)): os.remove(os.path.join(kd, x))
            shutil.rmtree(os.path.join(tmp, ".git"), ignore_errors=True)
            sh("git", "init", "-q", cwd=tmp); sh("git", "checkout", "-q", "-b", dal, cwd=tmp)
            sh("git", "add", "-A", cwd=tmp)
            sh("git", "-c", "user.name=bulten-bot", "-c", "user.email=actions@users.noreply.github.com",
               "commit", "-q", "-m", mesaj, cwd=tmp)
            r = sh("git", "push", f"--force-with-lease={dal}:{eski}", url, dal, cwd=tmp, kontrol=False)
            if r.returncode == 0:
                print(f"Yayınlandı ({len(B)} birim): {', '.join(B)}"); return
            print(f"Yayın çakıştı, tekrar deneniyor ({deneme + 1}): {r.stderr.strip()[:160]}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        time.sleep(4 + random.random() * 8)
    raise SystemExit("Yayınlanamadı.")


if __name__ == "__main__":
    yayinla(sys.argv[1] if len(sys.argv) > 1 else "cikti", sys.argv[2] if len(sys.argv) > 2 else "Güncelleme")
