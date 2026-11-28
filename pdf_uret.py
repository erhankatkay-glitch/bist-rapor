"""Hızlı uygulamadan indirilebilen PDF raporlar: önceden üretilir, GitHub Releases'e ("raporlar" sürümü) yüklenir.

  teknik     → Teknik analiz PDF'i (tam uygulamadaki "Teknik" raporu, araştırma ekibi dahil): BIST 30 + XU100, en likit 60 ABD hissesi
               + S&P 500 / Nasdaq, en büyük 25 kripto, tüm emtialar, takip ve portföy listeleri.
  arastirma  → Şirket araştırma raporu PDF'i (tam uygulamadaki "Hisse" raporu): BIST 30 + takip listesi, en likit 20 ABD hissesi.
Dosyalar depo dalına değil sürüm eklerine konur (dal küçük kalsın); dizin bulten/pdf/<tur>.json'a yazılır:
  {"zaman", "dosyalar": {kod: {"url", "ad", "zaman"}}}
Kullanım: python pdf_uret.py <cikti> <teknik|arastirma>   (GH_TOKEN ve GITHUB_REPOSITORY ortam değişkenleriyle yükler)
"""
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile

SURUM_ETIKETI = "raporlar"
BIST30 = ["XU100", "AKBNK", "ALARK", "ASELS", "ASTOR", "BIMAS", "EKGYO", "ENKAI", "EREGL", "FROTO", "GARAN", "GUBRF", "ISCTR", "KCHOL",
          "KONTR", "KRDMD", "MGROS", "PETKM", "PGSUS", "SAHOL", "SASA", "SISE", "TAVHL", "TCELL", "THYAO", "TOASO", "TUPRS", "YKBNK"]


def dosya_adi(kod):
    return str(kod).replace("/", "-").replace("\\", "-").replace("@", "_").replace(":", "-").replace(".", "_")


def _liste(yol):
    try: return [s.split("#")[0].split()[0].upper() for s in open(yol, encoding="utf-8") if s.split("#")[0].strip()]
    except Exception: return []


def hedefler(tur):
    import teknik_bulten as TB
    takip = _liste("takip_listesi.txt") + _liste("teknik_takip.txt") + _liste("portfoy.txt")
    abd = TB.evren("abd")
    if tur == "arastirma":
        bist = [k for k in dict.fromkeys(BIST30[1:] + [k for k in takip if "/" not in k and "." not in k])]
        return bist + abd[:20]
    kripto = TB.evren("kripto")[:25]
    emtia = TB.evren("emtia")
    return list(dict.fromkeys(BIST30 + abd[:60] + ["SP500", "NASDAQ"] + kripto + emtia + takip))


def teknik_pdf(kod, klasor):
    import arastirma_ekibi as EK
    import bist_teknik as T
    import bist_teknik_rapor as TKR
    s = T.analiz(kod)
    try: e = EK.rapor(s, None, None, None, None)
    except Exception: e = None
    yol = os.path.join(klasor, f"{dosya_adi(s['kod'])}_Teknik.pdf")
    TKR.teknik_pdf(s, yol, ekip=e)
    return s["kod"], yol


def arastirma_pdf(kod, klasor):
    import bist_rapor as br
    br.baglam(kod)
    d, m, emsaller, endeks = br.analiz_et(kod, log=lambda x: None)
    yol = os.path.join(klasor, f"{dosya_adi(m.get('kod_tam') or kod)}_Arastirma.pdf")
    br.pdf_olustur(d, m, emsaller, endeks, yol)
    return kod, yol


def yukle(dosyalar):
    """Sürüm eklerine yükler (aynı adlı ek değiştirilir). → başarıyla yüklenenler."""
    repo = os.environ.get("GITHUB_REPOSITORY", "erhankatkay-glitch/bist-rapor")
    if subprocess.run(["gh", "release", "view", SURUM_ETIKETI, "-R", repo], capture_output=True).returncode != 0:
        subprocess.run(["gh", "release", "create", SURUM_ETIKETI, "-R", repo, "--title", "KATKAY raporları (otomatik)",
                        "--notes", "Hızlı uygulamanın indirdiği PDF raporlar; her gece yenilenir."], check=True)
    ok = []
    for i in range(0, len(dosyalar), 20):
        grup = dosyalar[i:i + 20]
        r = subprocess.run(["gh", "release", "upload", SURUM_ETIKETI, *grup, "--clobber", "-R", repo], capture_output=True, text=True)
        if r.returncode == 0: ok += grup
        else: print("yükleme hatası:", r.stderr[:300], file=sys.stderr)
    return ok, repo


def main(cikti, tur):
    klasor = tempfile.mkdtemp()
    kodlar = hedefler(tur); print(tur, len(kodlar), "rapor")
    uret = teknik_pdf if tur == "teknik" else arastirma_pdf
    sonuc = {}
    for k in kodlar:
        try:
            kod, yol = uret(k, klasor); sonuc[kod] = yol; print("  ✓", kod)
        except Exception as x:
            print("  ✗", k, str(x)[:120])
    ok, repo = yukle(list(sonuc.values()))
    z = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
    dizin = {kod: {"ad": os.path.basename(y), "url": f"https://github.com/{repo}/releases/download/{SURUM_ETIKETI}/{os.path.basename(y)}", "zaman": z}
             for kod, y in sonuc.items() if y in ok}
    os.makedirs(os.path.join(cikti, "pdf"), exist_ok=True)
    with open(os.path.join(cikti, "pdf", f"{tur}.json"), "w", encoding="utf-8") as f:
        json.dump({"zaman": z, "dosyalar": dizin}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(dizin)} PDF yüklendi")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "cikti", sys.argv[2] if len(sys.argv) > 2 else "teknik")
