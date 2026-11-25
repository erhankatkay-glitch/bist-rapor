"""Sesli sabah özeti — iki sunuculu, doğal Türkçe sohbet (NotebookLM tarzı).

* Metin, veriden sohbet olarak kurulur (Emel ve Ahmet karşılıklı konuşur).
* Kısaltmalar, semboller, sayılar ve yüzdeler okunuşlarına çevrilir; böylece hiçbir kelime harf harf okunmaz.
* Ses: Microsoft Edge'in ücretsiz nöral sesleri (edge-tts, tr-TR-EmelNeural / tr-TR-AhmetNeural).
  Ulaşılamazsa gTTS'e düşülür.
"""
import asyncio
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

SESLER = {"E": "tr-TR-EmelNeural", "A": "tr-TR-AhmetNeural"}
HIZ = "+14%"

# ----------------------------------------------------------------------------- sayılar
_B = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
_O = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]


def _uc(n):
    y, r = divmod(n, 100); o, b = divmod(r, 10)
    return " ".join(x for x in ((("" if y == 1 else _B[y] + " ") + "yüz") if y else "", _O[o], _B[b]) if x).strip()


def tam_oku(n):
    n = int(n)
    if n == 0: return "sıfır"
    if n < 0: return "eksi " + tam_oku(-n)
    parca = []
    for deger, ad in ((10 ** 12, "trilyon"), (10 ** 9, "milyar"), (10 ** 6, "milyon"), (1000, "bin")):
        k, n = divmod(n, deger)
        if k: parca.append("bin" if (ad == "bin" and k == 1) else f"{tam_oku(k)} {ad}")
    if n: parca.append(_uc(n))
    return " ".join(parca)


def sayi_oku(x, ondalik=1):
    """12,5 → 'on iki virgül beş'. Sondaki sıfırlar okunmaz."""
    x = round(float(x), ondalik)
    eksi = x < 0; x = abs(x)
    tam = int(x); kes = f"{x:.{ondalik}f}".split(".")[1].rstrip("0") if ondalik else ""
    s = tam_oku(tam)
    if kes:
        s += " virgül " + (" ".join(tam_oku(int(c)) for c in kes) if kes.startswith("0") else tam_oku(int(kes)))
    return ("eksi " if eksi else "") + s


def yuzde(x, ondalik=1):
    """0.0123 (oran) → 'yüzde bir virgül iki'."""
    return "yüzde " + sayi_oku(abs(x) * 100, ondalik)


# ----------------------------------------------------------------------------- sözlükler
KRIPTO = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "XRP": "Ripple", "BNB": "Binance Coin", "ADA": "Cardano",
          "DOGE": "Dogecoin", "AVAX": "Avalanche", "DOT": "Polkadot", "LINK": "Chainlink", "TRX": "Tron", "LTC": "Litecoin",
          "TON": "Toncoin", "SHIB": "Shiba", "MATIC": "Polygon", "POL": "Polygon", "NEAR": "Near", "SUI": "Sui", "APT": "Aptos",
          "ARB": "Arbitrum", "OP": "Optimism", "ATOM": "Cosmos", "UNI": "Uniswap", "PEPE": "Pepe", "XLM": "Stellar",
          "HBAR": "Hedera", "ICP": "İnternet Computer", "FIL": "Filecoin", "INJ": "İnjective", "RNDR": "Render",
          "RENDER": "Render", "AAVE": "Aave", "ETC": "Ethereum Classic", "BCH": "Bitcoin Cash", "KAS": "Kaspa",
          "TAO": "Bittensor", "FET": "Fetch", "SEI": "Sei", "TIA": "Celestia", "WIF": "Dogwifhat", "BONK": "Bonk",
          "HYPE": "Hyperliquid", "ENA": "Ethena", "ONDO": "Ondo", "JUP": "Jupiter", "XAUT": "Tether altın", "PAXG": "Pax altın"}
EMTIA = {"GC=F": "ons altın", "SI=F": "gümüş", "CL=F": "WTI petrol", "BZ=F": "Brent petrol", "HG=F": "bakır",
         "NG=F": "doğal gaz", "PL=F": "platin", "PA=F": "paladyum", "GRAMALTIN": "gram altın", "ALTIN": "altın",
         "GUMUS": "gümüş", "XAUUSD": "ons altın", "XAGUSD": "gümüş"}
ULKE = {"USD": "Amerika", "EUR": "Euro Bölgesi", "GBP": "İngiltere", "JPY": "Japonya", "CNY": "Çin", "TRY": "Türkiye",
        "CAD": "Kanada", "AUD": "Avustralya", "NZD": "Yeni Zelanda", "CHF": "İsviçre", "ALL": "küresel"}
# ForexFactory başlıkları → Türkçe (uzun eşleşmeler önce)
VERI = [
    ("Core PCE Price Index", "çekirdek kişisel tüketim harcamaları fiyat endeksi"), ("PCE Price Index", "kişisel tüketim harcamaları fiyat endeksi"),
    ("Non-Farm Employment Change", "tarım dışı istihdam"), ("Non-Farm Payrolls", "tarım dışı istihdam"),
    ("ADP Non-Farm Employment Change", "özel sektör istihdamı"), ("Unemployment Claims", "haftalık işsizlik başvuruları"),
    ("Unemployment Rate", "işsizlik oranı"), ("Average Hourly Earnings", "saatlik ortalama kazançlar"),
    ("JOLTS Job Openings", "açık iş ilanları"), ("Core CPI", "çekirdek enflasyon"), ("CPI", "enflasyon"),
    ("Core PPI", "çekirdek üretici fiyatları"), ("PPI", "üretici fiyatları"), ("Prelim GDP", "öncü büyüme"),
    ("Advance GDP", "öncü büyüme"), ("Final GDP", "kesin büyüme"), ("GDP", "büyüme"),
    ("FOMC Meeting Minutes", "Fed toplantı tutanakları"), ("FOMC Statement", "Fed faiz kararı metni"),
    ("FOMC Press Conference", "Fed basın toplantısı"), ("Federal Funds Rate", "Fed faiz kararı"),
    ("Fed Chair", "Fed Başkanı"), ("Main Refinancing Rate", "Avrupa Merkez Bankası faiz kararı"),
    ("Monetary Policy Statement", "para politikası metni"), ("Official Bank Rate", "İngiltere Merkez Bankası faiz kararı"),
    ("BOJ Policy Rate", "Japonya Merkez Bankası faiz kararı"), ("One-week Repo Rate", "Merkez Bankası politika faizi"),
    ("ISM Manufacturing PMI", "imalat sanayi endeksi"), ("ISM Services PMI", "hizmet sektörü endeksi"),
    ("Flash Manufacturing PMI", "öncü imalat endeksi"), ("Flash Services PMI", "öncü hizmet endeksi"),
    ("Manufacturing PMI", "imalat endeksi"), ("Services PMI", "hizmet endeksi"),
    ("CB Consumer Confidence", "tüketici güveni"), ("Prelim UoM Consumer Sentiment", "Michigan tüketici güveni"),
    ("Revised UoM Consumer Sentiment", "Michigan tüketici güveni"), ("Consumer Confidence", "tüketici güveni"),
    ("Core Retail Sales", "çekirdek perakende satışlar"), ("Retail Sales", "perakende satışlar"),
    ("Durable Goods Orders", "dayanıklı mal siparişleri"), ("Core Durable Goods Orders", "çekirdek dayanıklı mal siparişleri"),
    ("New Home Sales", "yeni konut satışları"), ("Pending Home Sales", "bekleyen konut satışları"),
    ("Existing Home Sales", "ikinci el konut satışları"), ("Building Permits", "inşaat izinleri"), ("Housing Starts", "konut başlangıçları"),
    ("Industrial Production", "sanayi üretimi"), ("Trade Balance", "dış ticaret dengesi"), ("Current Account", "cari denge"),
    ("Crude Oil Inventories", "ham petrol stokları"), ("Natural Gas Storage", "doğal gaz stokları"),
    ("Empire State Manufacturing Index", "New York imalat endeksi"), ("Philly Fed Manufacturing Index", "Philadelphia imalat endeksi"),
    ("German", "Almanya"), ("French", "Fransa"), ("Italian", "İtalya"), ("Spanish", "İspanya"), ("Chinese", "Çin"),
    ("Speaks", "konuşması"), ("Testifies", "sunumu"),
]
# Serbest metin içi kısaltmalar → okunuş
KISALTMA = [
    (r"\bS&P\s*500\b", "Es en Pi beş yüz"), (r"\bBIST\s*100\b", "Bist yüz"), (r"\bBIST\s*30\b", "Bist otuz"),
    (r"\bXU100\b", "Bist yüz"), (r"\bBIST'?(\w*)", r"Bist\1"), (r"\bNasdaq\b", "Nazdak"), (r"\bNASDAQ\b", "Nazdak"),
    (r"\bDow Jones\b", "Dav Cons"), (r"\bVIX'?(\w*)", r"viks\1"), (r"\bUSD/TRY\b", "dolar lira"), (r"\bEUR/TRY\b", "euro lira"),
    (r"\bUSD\b", "dolar"), (r"\bEUR\b", "euro"), (r"\bABD'?(\w*)", r"Amerika\1"), (r"\bTCMB'?(\w*)", r"Merkez Bankası\1"),
    (r"\bFED\b|\bFed\b", "Fed"), (r"\bFOMC\b", "Fed toplantısı"), (r"\bECB\b", "Avrupa Merkez Bankası"),
    (r"\bAMB\b", "Avrupa Merkez Bankası"), (r"\bTÜFE\b", "enflasyon"), (r"\bÜFE\b", "üretici enflasyonu"),
    (r"\bGSYH\b", "büyüme"), (r"\bPMI\b", "satın alma yöneticileri endeksi"), (r"\bKAP\b", "Kap"), (r"\bSPK\b", "Sermaye Piyasası Kurulu"),
    (r"\bTL\b", "lira"), (r"\bmn \$", "milyon dolar"), (r"\bmlr \$", "milyar dolar"), (r"\bmilyar \$", "milyar dolar"),
    (r"\$", " dolar"), (r"\bAL\b", "al"), (r"\bSAT\b", "sat"), (r"\bTSİ\b", "Türkiye saatiyle"), (r"\bvs\.?\b", "ve benzeri"),
    (r"\bA\.Ş\.?", ""), (r"\bT\.A\.Ş\.?", ""), (r"\bAI\b", "yapay zekâ"), (r"\bETF\b", "borsa yatırım fonu"),
    (r"\bOPEC\+?", "Opek"), (r"\bNATO\b", "Nato"), (r"\bAB\b", "Avrupa Birliği"), (r"\bBM\b", "Birleşmiş Milletler"),
    (r"\bIMF\b", "Uluslararası Para Fonu"), (r"\bCEO\b", "genel müdür"), (r"\bH1\b", "birinci hedef"), (r"\bH2\b", "ikinci hedef"),
]


def ek_de(metin):
    """Bulunma eki (-de/-da/-te/-ta), ünlü ve ünsüz uyumuna göre."""
    w = metin.rstrip()
    son_unlu = next((c for c in reversed(w.lower()) if c in "aeıioöuü"), "e")
    unlu = "a" if son_unlu in "aıou" else "e"
    unsuz = "t" if w[-1].lower() in "fstkçşhp" else "d"
    return w + unsuz + unlu


def _saat(m):
    h, d = int(m.group(1)), int(m.group(2))
    return ek_de(tam_oku(h) + ("" if d == 0 else (" " + tam_oku(d))))


def _yuzde_m(m):
    isaret = m.group(1) or ""; sayi = m.group(2).replace(".", "").replace(",", ".")
    try:
        v = float(sayi)
    except ValueError:
        return m.group(0)
    on = "artı " if isaret == "+" else "eksi " if isaret in "−-" and isaret else ""
    return on + "yüzde " + sayi_oku(v, 1)


def _sayi_m(m):
    s = m.group(0)
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", s):
        s = s.replace(".", "")
    s = s.replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return m.group(0)
    return sayi_oku(v, 2 if abs(v) < 10 and "." in s else 1)


def normalle(t):
    """Serbest metni sesli okumaya uygun hale getirir (kısaltma, sembol, sayı, yüzde, saat)."""
    t = re.sub(r"[•·→←↑↓★☀️🟢🔴🕊⚠️📈📉💼]", " ", t)
    t = re.sub(r"\(([^()]*)\)", r", \1,", t)
    for a, b in KISALTMA:
        t = re.sub(a, b, t)
    t = re.sub(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b(?:'?(?:de|da|te|ta))?", _saat, t)
    t = re.sub(r"([+−-])?%\s*(\d+(?:[.,]\d+)*)", _yuzde_m, t)
    t = re.sub(r"([+−-])?(\d+(?:[.,]\d+)*)\s*%", _yuzde_m, t)
    t = re.sub(r"(?<![\w])\d+(?:[.,]\d+)*", _sayi_m, t)
    t = re.sub(r"\+(?=\s*[a-zçğıöşü])", "artı ", t)
    t = t.replace("−", " eksi ").replace("&", " ve ").replace("/", " ")
    # Tamamı büyük harfli kalan kelimeler (ör. sembol) harf harf okunmasın
    t = re.sub(r"\b([A-ZÇĞİÖŞÜ]{2,6})\b", lambda m: m.group(1).capitalize(), t)
    t = re.sub(r"\s+([,;.])", r"\1", t); t = re.sub(r",\s*([,;.])", r"\1", t); t = re.sub(r"\s{2,}", " ", t)
    return t.strip(" ,")


def veri_adi(baslik, ulke=None):
    b = baslik or ""
    for a, c in VERI:
        if a.lower() in b.lower():
            b = re.sub(re.escape(a), c, b, flags=re.I)
    b = re.sub(r"\b[mqy]/[mqy]\b", "", b).strip()
    u = ULKE.get(ulke or "", "")
    return (f"{u} {b}" if u and u not in b else b).strip()


def varlik_adi(kod, pazar=None):
    """Sembol yerine şirket / varlık adı (harf harf okunmasın)."""
    k = str(kod).upper()
    if pazar == "kripto" or "/USDT" in k or "@OKX" in k:
        s = k.replace("/USDT", "").replace("@OKX", "").replace("-USD", "")
        return KRIPTO.get(s, s.capitalize())
    if pazar == "emtia" or k in EMTIA:
        return EMTIA.get(k, k.capitalize())
    ad = None
    try:
        if k.endswith(".US") or pazar == "abd":
            import bist_abd as BA; ad = BA.ad(k)
        else:
            import bist_veri as BV; ad = BV.ad(k)
    except Exception:
        ad = None
    if not ad or ad.upper() == k.replace(".US", ""):
        return k.replace(".US", "").capitalize()
    ad = re.sub(r"\b(A\.?Ş\.?|T\.?A\.?Ş\.?|T\.?A\.?O\.?|SANAYİ VE TİCARET|SAN\.?|TİC\.?|VE|Inc\.?|Corp\.?|Corporation|"
                r"Holdings?|Ltd\.?|plc|N\.V\.|S\.A\.|Co\.?|Company|Class [A-C]|Common Stock)\b", " ", ad, flags=re.I)
    ad = re.sub(r"[.,]+", " ", ad); ad = re.sub(r"\s{2,}", " ", ad).strip()
    kel = ad.split()
    kel = kel[:1] + [w for w in kel[1:3] if not (w.isupper() and len(w) <= 4)]
    return " ".join(w.capitalize() if w.isupper() and len(w) > 3 else w for w in kel) or k.capitalize()


# ----------------------------------------------------------------------------- senaryo
TF = {"4S": "dört saatlik", "G": "günlük", "H": "haftalık", "A": "aylık"}


def _yon(d, yuk="yükseldi", dus="geriledi", yatay="yatay seyretti"):
    return yuk if d > 0.0015 else dus if d < -0.0015 else yatay


def senaryo(PV, tk, acik, firs, hab, yab=None, tarih_metni=""):
    """[(konuşmacı, metin), ...] — iki sunuculu doğal sohbet."""
    r = random.Random(tarih_metni)
    sec = lambda *x: r.choice(x)
    S = []
    E = lambda m: S.append(("E", m)); A = lambda m: S.append(("A", m))

    E(sec(f"Günaydın! KATKAY Yatırım sabah özetine hoş geldiniz. Bugün {tarih_metni}.",
          f"Herkese günaydın, KATKAY Yatırım'la güne başlıyoruz. Bugün {tarih_metni}."))
    A(sec("Günaydın Emel. Kahveler hazırsa hızlıca piyasalara bakalım.", "Günaydın. Vakit kaybetmeden gelelim piyasalara.",
          "Günaydın Emel, bugün de konuşacak epey şey var."))

    sp, vx, nq = PV.get("S&P 500"), PV.get("VIX"), PV.get("Nasdaq")
    if sp:
        d = sp["d1G"] or 0
        E(sec("Önce Amerika. Dün kapanış nasıldı?", "Amerika'dan başlayalım, dün nasıl kapandı?"))
        c = f"Es en Pi beş yüz {yuzde(d)} {_yon(d, 'yükselişle', 'düşüşle', 'yataya yakın')} kapattı"
        if nq and nq.get("d1G") is not None: c += f", Nazdak tarafında da {yuzde(nq['d1G'])} {_yon(nq['d1G'], 'artı', 'eksi', 'yatay')} var"
        c += "."
        if vx:
            v = vx["deger"]
            c += (f" Korku endeksi viks {sayi_oku(v, 0)} civarında, yani ortam sakin." if v < 18 else
                  f" Korku endeksi viks {sayi_oku(v, 0)} seviyesinde; biraz tedirginlik var." if v <= 25 else
                  f" Korku endeksi viks {sayi_oku(v, 0)} seviyesine çıkmış, bu temkinli olmak gerektiğini gösteriyor.")
        A(c)

    bi, usd = PV.get("BIST 100"), PV.get("USD/TRY")
    if bi:
        d = bi["d1G"] or 0
        E(f"Bizim tarafta Bist yüz dün {yuzde(d)} {_yon(d)}." + (" Güzel bir gündü." if d > 0.01 else " Biraz satış baskısı vardı." if d < -0.01 else ""))
        if usd:
            kur = usd["deger"]; lira = int(kur); kurus = int(round((kur - lira) * 100))
            A(f"Dolar da {tam_oku(lira)} lira" + (f" {tam_oku(kurus)} kuruş" if kurus else "") + " civarında"
              + ("; kurda sakin bir seyir var." if abs(usd.get("d1G") or 0) < 0.003 else f", günlük {yuzde(usd['d1G'])} {_yon(usd['d1G'], 'yukarıda', 'aşağıda')}."))

    gr, ons, bt = PV.get("Gram altın"), PV.get("Ons altın"), PV.get("Bitcoin")
    if ons or bt:
        E(sec("Altın ve Bitcoin cephesinde neler var?", "Peki altın ve kripto?"))
        p = []
        if ons and ons.get("d1G") is not None:
            p.append(f"Ons altın {yuzde(ons['d1G'])} {_yon(ons['d1G'])}"
                     + (f", gram altın da {tam_oku(round(gr['deger']))} lira civarında" if gr else ""))
        if bt and bt.get("d1G") is not None:
            p.append(f"Bitcoin ise {yuzde(bt['d1G'])} {_yon(bt['d1G'], 'artıda', 'ekside', 'yatay')}, "
                     f"{sayi_oku(bt['deger'] / 1000, 0)} bin dolar civarında işlem görüyor")
        A(". ".join(p) + ".")

    if yab:
        h = yab["hafta"]
        E("Yabancı yatırımcılardan haber var mı?")
        c = (f"Merkez Bankası'nın son verisine göre yabancılar geçen hafta Bist'te net {sayi_oku(abs(h), 0)} milyon dolarlık hisse "
             f"{'aldı' if h > 0 else 'sattı'}.")
        if abs(yab.get("ardisik") or 0) >= 3:
            c += f" Üstelik {tam_oku(abs(yab['ardisik']))} haftadır üst üste {'alıcı' if yab['ardisik'] > 0 else 'satıcı'} taraftalar."
        A(c + (" Bu borsa için olumlu bir işaret." if h > 0 else " Bu da borsa üzerinde baskı demek."))

    import datetime as _dt
    if tk:
        E(sec("Bugün takvimde neler var?", "Gün içinde takip etmemiz gereken veriler neler?"))
        sat = []
        for e in tk[:3]:
            t = _dt.datetime.fromisoformat(e["zaman"])
            sat.append(f"saat {ek_de(_saat_metni(t))} {veri_adi(e['baslik'], e.get('ulke'))}")
        c = ("Bugün " + (sat[0] if len(sat) == 1 else ", ".join(sat[:-1]) + " ve " + sat[-1]) + " verisi var.")
        A(c + sec(" Açıklama anlarında altında, dolarda ve borsalarda sert hareketler görebiliriz.",
                  " O saatlerde oynaklık artabilir, dikkatli olmakta fayda var."))
    else:
        E("Takvim bugün nasıl?"); A("Bugün yüksek etkili bir veri yok; piyasalar daha çok haber akışına bakacak.")

    if firs:
        E(sec("Peki öne çıkan fırsatlar neler?", "Gelelim fırsatlara. Sistem bu sabah neleri öne çıkarıyor?"))
        p = []
        for i, f in enumerate(firs[:3]):
            yer = {"bist": ("Borsa İstanbul'da", "Borsa İstanbul'da"), "kripto": ("Kriptoda", "kriptoda"),
                   "emtia": ("Emtiada", "emtiada"), "abd": ("Amerika'da", "Amerika'da")}.get(f.get("pz"), ("", ""))
            ad = varlik_adi(f["kod"], f.get("pz"))
            yon = "al" if f["yon"] == 1 else "sat"
            p.append((f"{yer[0]} {ad}, {TF.get(f['tf'], '')} grafikte {yon} sinyali veriyor, puanı {tam_oku(round(f['puan']))}"
                      if i == 0 else f"{'bir de ' if i == len(firs[:3]) - 1 else ''}{yer[1]} {ad} {TF.get(f['tf'], '')} grafikte {yon} yönlü, puanı {tam_oku(round(f['puan']))}"))
        A(". ".join(x[0].upper() + x[1:] for x in p) + ".")
        E("Tabii bunlar kesin bilgi değil; stop seviyesine uymak şart.")
    yakin = sorted([k for k in acik if k["yak_h"] < 0.02], key=lambda k: k["yak_h"])
    risk = sorted([k for k in acik if k["yak_s"] < 0.02], key=lambda k: k["yak_s"])
    if yakin or risk:
        p = []
        if yakin: p.append(f"{varlik_adi(yakin[0]['kod'], yakin[0].get('pz'))} hedefine çok yakın, kâr alma seviyesini takip etmek lazım")
        if risk: p.append(f"{varlik_adi(risk[0]['kod'], risk[0].get('pz'))} ise stop seviyesine yaklaştı, zarar kesme planını gözden geçirmekte fayda var")
        A("Açık kurulumlara da bakalım: " + "; ".join(p) + ".")

    if hab:
        a = hab[0]
        jeo = a.get("tur", "").startswith("Jeopolitik")
        ham = a.get("tur", "")
        konu = ("Jeopolitik tarafta" if jeo else
                "Şirket haberlerinde " + ham.split(":", 1)[-1].strip().replace(" / ", ", ").lower() + " başlığında" if ham.startswith("Şirket") else
                ham.replace(" gelişmesi", "").replace(" gelişme", "") + " tarafında")
        E(sec("Son olarak öne çıkan bir haber var mı?", "Haber akışında neler var?"))
        etki = ("gerilimin azaldığına işaret ediyor" if a["yon"] > 0 else "gerilimin arttığına işaret ediyor") if jeo else \
               ("piyasa için olumlu okunuyor" if a["yon"] > 0 else "piyasa için olumsuz okunuyor")
        A(f"{konu} bir gelişme var ve {etki}. Detayını haber bildirimlerinde bulabilirsiniz.")

    E(sec("Bugünlük bu kadar. Hatırlatalım, bunlar gösterge bazlı analizlerdir, yatırım tavsiyesi değildir.",
          "Özetimiz bu kadar. Unutmayın, bu bir gösterge bazlı analizdir, yatırım tavsiyesi değildir."))
    A(sec("Herkese bereketli ve kazançlı bir gün dileriz. Görüşmek üzere!", "İyi günler, yarın sabah yine buradayız!"))
    return [(k, normalle(m)) for k, m in S]


def _saat_metni(t):
    return tam_oku(t.hour) + ("" if t.minute == 0 else " " + tam_oku(t.minute))


# ----------------------------------------------------------------------------- sentez
async def _edge(parcalar, klasor):
    import edge_tts
    yollar = []
    for i, (k, m) in enumerate(parcalar):
        y = os.path.join(klasor, f"{i:03d}.mp3")
        for den in range(3):
            try:
                await edge_tts.Communicate(m, SESLER[k], rate=HIZ).save(y)
                break
            except Exception:
                if den == 2: raise
                await asyncio.sleep(2)
        yollar.append(y)
    return yollar


def _birlestir(yollar, hedef, klasor):
    if shutil.which("ffmpeg"):
        # kısa bir sessizlik ile konuşmacı geçişleri doğal olsun
        ses = os.path.join(klasor, "sus.mp3")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.25",
                        "-c:a", "libmp3lame", "-b:a", "48k", ses], check=True)
        liste = os.path.join(klasor, "liste.txt")
        with open(liste, "w") as f:
            for i, y in enumerate(yollar):
                if i: f.write(f"file '{ses}'\n")
                f.write(f"file '{y}'\n")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-c:a", "libmp3lame", "-b:a", "64k", "-ar", "24000", "-ac", "1", hedef], check=True)
    else:
        with open(hedef, "wb") as o:
            for y in yollar:
                o.write(open(y, "rb").read())
    return hedef


def seslendir(parcalar, hedef):
    """parcalar: [(konuşmacı, metin)]. Önce edge-tts (nöral), olmazsa gTTS. Hangi motorun kullanıldığını döndürür."""
    with tempfile.TemporaryDirectory() as kl:
        try:
            yollar = asyncio.run(_edge(parcalar, kl))
            _birlestir(yollar, hedef, kl)
            return "edge"
        except Exception as ex:
            print("edge-tts kullanılamadı, gTTS'e geçiliyor:", ex, file=sys.stderr)
        from gtts import gTTS
        gTTS(" ".join(m for _, m in parcalar), lang="tr").save(hedef)
        return "gtts"
