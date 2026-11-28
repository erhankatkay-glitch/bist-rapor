"""Aşama 14 yorum katmanı: araştırma ekibinin kural tabanlı raporunu akıcı Türkçe paragrafa çevirir (isteğe bağlı).

Sağlayıcı: Google Gemini (ücretsiz katman; anahtar GEMINI_API_KEY), yedek Groq (GROQ_API_KEY). Anahtar yoksa / sınır dolarsa /
hata olursa None döner ve kural tabanlı metin kullanılır.
Güvenlik: modele yalnız herkese açık piyasa verisinden üretilmiş rapor gider (portföy, sanal defter gönderilmez).
Model yeni rakam üretemez: çıktıdaki her sayı girdi metninde geçmiyorsa çıktı atılır.
"""
import os, re, json, time, urllib.request

_MODEL_ONB = {"zaman": 0, "ad": None}
TALIMAT = (
    "Sen bir yatırım araştırma ekibinin editörüsün. Aşağıdaki yapılandırılmış rapordan 5-7 cümlelik, sade ve akıcı Türkçe bir özet yaz.\n"
    "Kurallar: 1) YALNIZ raporda geçen sayıları aynen kullan; yeni sayı, hedef fiyat, yüzde ya da tarih UYDURMA. "
    "2) Düşüş senaryosunu ve riskleri yükseliş kadar açık yaz. 3) Güven derecesini ve neden o seviyede olduğunu söyle. "
    "4) En önemli tez bozucuyu belirt. 5) Al/sat tavsiyesi verme, emir cümlesi kurma. 6) Başlık, madde işareti, markdown kullanma. "
    "7) Son cümle tam olarak: 'Bu değerlendirme otomatik üretilmiştir, yatırım tavsiyesi değildir.'")


def _istek(url, veri=None, baslik=None, zaman_asimi=25):
    r = urllib.request.Request(url, data=json.dumps(veri).encode() if veri is not None else None,
                               headers={"Content-Type": "application/json", **(baslik or {})})
    return json.loads(urllib.request.urlopen(r, timeout=zaman_asimi).read())


def _g(yol, anahtar, veri=None):
    """Gemini isteği: anahtar biçiminden bağımsız. Önce API anahtarı başlığı (x-goog-api-key; "AIza…" ve yeni biçimler),
    olmazsa OAuth/erişim belirteci gibi Bearer olarak dener."""
    url = "https://generativelanguage.googleapis.com/v1beta/" + yol
    try:
        return _istek(url, veri, {"x-goog-api-key": anahtar.strip()})
    except Exception as ilk:
        try:
            return _istek(url, veri, {"Authorization": f"Bearer {anahtar.strip()}"})
        except Exception:
            raise ilk


def gemini_model(anahtar):
    """Açık 'flash' modellerinden en yenisini seçer (model adları sık değiştiği için sabit yazılmaz; 6 saat önbellek)."""
    if _MODEL_ONB["ad"] and time.time() - _MODEL_ONB["zaman"] < 6 * 3600: return _MODEL_ONB["ad"]
    d = _g("models?pageSize=200", anahtar)
    adaylar = [m["name"] for m in d.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])
               and "flash" in m["name"] and not any(k in m["name"] for k in ("image", "tts", "audio", "live", "embedding", "thinking-exp"))]
    def anahtar_(n):   # en yüksek sürüm; kararlı sürüm önizlemeden, tam "flash" "lite"tan önde
        v = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
        return ("preview" not in n and "exp" not in n, float(v.group(1)) if v else 0.0, "lite" not in n)
    ad = sorted(adaylar, key=anahtar_)[-1] if adaylar else "models/gemini-flash-latest"
    _MODEL_ONB.update(zaman=time.time(), ad=ad)
    return ad


def gemini(metin, anahtar):
    m = gemini_model(anahtar)
    d = _g(f"{m}:generateContent", anahtar,
               {"contents": [{"role": "user", "parts": [{"text": TALIMAT + "\n\nRAPOR:\n" + metin}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 700}})
    return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"]).strip(), m.split("/")[-1]


def groq(metin, anahtar):
    d = _istek("https://api.groq.com/openai/v1/chat/completions",
               {"model": "llama-3.3-70b-versatile", "temperature": 0.3, "max_tokens": 700,
                "messages": [{"role": "system", "content": TALIMAT}, {"role": "user", "content": "RAPOR:\n" + metin}]},
               {"Authorization": f"Bearer {anahtar}"})
    return d["choices"][0]["message"]["content"].strip(), "groq/llama-3.3-70b"


def rapor_metni(e):
    """Ekip raporunu modele verilecek düz metne çevirir (sayılar raporda göründüğü biçimde)."""
    s = [f"Varlık: {e.get('ad')} ({e.get('kod')})", f"Özet: {e['ozet']}", f"Görünüm: {e['gorunum']}; güven: {e['guven']}; ufuk: {e['ufuk']}",
         "Senaryolar: " + " | ".join(f"{x['ad']}: {x['kosul']}" for x in e["senaryolar"]), "Tez bozucular: " + " | ".join(e["tez_bozucular"])]
    for r in e["roller"]:
        s.append(f"{r['ad']}: " + " ".join(r["bulgular"]))
    return "\n".join(s)


def _sayilar(t):
    return {x.replace(".", "").replace(",", ".").strip(".") for x in re.findall(r"\d[\d.,]*\d|\d", t)}


def dogrula(cikti, girdi):
    """Çıktıdaki her sayı girdide geçmeli (uydurma rakam koruması)."""
    izin = _sayilar(girdi) | {"0", "1", "2", "3", "4", "5", "6", "7", "8", "10", "20"}
    fazla = [x for x in _sayilar(cikti) if x not in izin]
    return not fazla, fazla


def yorum(e, gemini_anahtar=None, groq_anahtar=None):
    """→ {"metin", "model"} ya da None. Anahtar yoksa ya da doğrulama geçmezse None (kural tabanlı metin kalır)."""
    return yorum_metinden(rapor_metni(e), gemini_anahtar, groq_anahtar) if e else None


def yorum_metinden(girdi, gemini_anahtar=None, groq_anahtar=None):
    gemini_anahtar = gemini_anahtar or os.environ.get("GEMINI_API_KEY"); groq_anahtar = groq_anahtar or os.environ.get("GROQ_API_KEY")
    if not (gemini_anahtar or groq_anahtar): return None
    for ad, fn, k in (("gemini", gemini, gemini_anahtar), ("groq", groq, groq_anahtar)):
        if not k: continue
        try:
            metin, model = fn(girdi, k)
            ok, fazla = dogrula(metin, girdi)
            if ok and len(metin) > 80: return {"metin": metin, "model": model}
            print(f"yorum katmanı ({ad}): doğrulanamayan sayı {fazla[:5]}; kural tabanlı metin kullanılıyor")
        except Exception as ex:
            print(f"yorum katmanı ({ad}):", str(ex)[:160])
    return None
