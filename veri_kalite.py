# -*- coding: utf-8 -*-
"""Veri kalite etiketi: her fiyatın ne kadar taze olduğunu dürüstçe söyler.

Dört durum:
  anlık    – kripto, son fiyat en fazla 20 dk önce
  gecikmeli – piyasa açık, veri borsanın ücretsiz gecikmesi içinde (~15 dk, en fazla 50 dk)
  gün sonu – piyasa kapalı, son seansın kapanış verisi
  bayat    – beklenenden eski (veri kesintisi ya da tatil olabilir)
Bütün zamanlar UTC tutulur, kullanıcıya Türkiye saatiyle gösterilir."""
import datetime as dt
from zoneinfo import ZoneInfo

TSI, NY, UTC = ZoneInfo("Europe/Istanbul"), ZoneInfo("America/New_York"), dt.timezone.utc

RENK = {"anlık": "#22C55E", "gecikmeli": "#E8B84A", "gün sonu": "#A1A1AA", "bayat": "#EF4444"}
AD = {"bist": "BIST", "abd": "ABD", "kripto": "Kripto", "emtia": "Emtia (vadeli)", "doviz": "Döviz", "faiz": "Faiz"}


DUNYA_SEANS = {  # Aşama 12: yerel saatle açılış–kapanış (tatiller dikkate alınmaz)
    "^GDAXI": ("Europe/Berlin", (9, 0), (17, 30)), "^STOXX50E": ("Europe/Berlin", (9, 0), (17, 30)), "^FCHI": ("Europe/Paris", (9, 0), (17, 30)),
    "^FTSE": ("Europe/London", (8, 0), (16, 30)), "^N225": ("Asia/Tokyo", (9, 0), (15, 30)), "^HSI": ("Asia/Hong_Kong", (9, 30), (16, 0)),
    "000001.SS": ("Asia/Shanghai", (9, 30), (15, 0)), "^KS11": ("Asia/Seoul", (9, 0), (15, 30)), "^BSESN": ("Asia/Kolkata", (9, 15), (15, 30)),
    "^AXJO": ("Australia/Sydney", (10, 0), (16, 0)), "^BVSP": ("America/Sao_Paulo", (10, 0), (17, 0)), "^GSPTSE": ("America/Toronto", (9, 30), (16, 0))}


def tur_bul(kod):
    """Yahoo / Binance kodundan piyasa türü."""
    k = str(kod).upper()
    if k in DUNYA_SEANS: return "dunya:" + k
    if k.endswith(".IS"): return "bist"
    if k.endswith("-USD") or "/" in k or k.endswith("USDT"): return "kripto"
    if k.endswith("=F"): return "emtia"
    if k.endswith("=X") or k.startswith("DX-Y"): return "doviz"
    if k in ("^TNX", "^IRX", "^FVX", "^TYX"): return "faiz"
    return "abd"


# Tatil ve yarım günler (kaynak: borsaistanbul.com resmi tatil tablosu, nyse.com holidays & trading hours).
# 2027 BIST dini bayram tarihleri tahminidir; Borsa İstanbul duyurusu çıkınca güncellenmeli.
TATIL = {
    "bist": {"2026-01-01", "2026-03-20", "2026-04-23", "2026-05-01", "2026-05-19", "2026-05-27", "2026-05-28", "2026-05-29",
             "2026-07-15", "2026-10-29",
             "2027-01-01", "2027-03-09", "2027-03-10", "2027-03-11", "2027-04-23", "2027-05-17", "2027-05-18", "2027-05-19",
             "2027-07-15", "2027-08-30", "2027-10-29"},
    "abd": {"2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07",
            "2026-11-26", "2026-12-25",
            "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18", "2027-07-05", "2027-09-06",
            "2027-11-25", "2027-12-24"},
}
TATIL["faiz"] = TATIL["abd"]
YARIM = {   # erken kapanış (yerel saat)
    "bist": {"2026-03-19": dt.time(13, 0), "2026-05-26": dt.time(13, 0), "2026-10-28": dt.time(13, 0),
             "2027-03-08": dt.time(13, 0), "2027-10-28": dt.time(13, 0)},
    "abd": {"2026-11-27": dt.time(13, 0), "2026-12-24": dt.time(13, 0), "2027-11-26": dt.time(13, 0)},
}
YARIM["faiz"] = YARIM["abd"]


def _seans(tur):
    """(saat dilimi, açılış, kapanış, 7/24 mü, gün içi mola yok mu)"""
    if tur == "bist": return TSI, dt.time(10, 0), dt.time(18, 10)
    if tur in ("abd", "faiz"): return NY, dt.time(9, 30), dt.time(16, 0)
    if str(tur).startswith("dunya:"):
        tz_, a_, k_ = DUNYA_SEANS[tur[6:]]
        return ZoneInfo(tz_), dt.time(*a_), dt.time(*k_)
    return NY, None, None          # emtia ve döviz: pazar 18:00 – cuma 17:00 NY (her gün 17–18 arası mola)


def piyasa_acik(tur, simdi=None):
    t = (simdi or dt.datetime.now(UTC)).astimezone(UTC)
    if tur == "kripto": return True
    tz, ac, ka = _seans(tur)
    y = t.astimezone(tz)
    if ac is not None:
        g = y.date().isoformat()
        if g in TATIL.get(tur, ()): return False
        ka = YARIM.get(tur, {}).get(g, ka)
        return y.weekday() < 5 and ac <= y.time() < ka
    # emtia / döviz
    if y.weekday() == 5: return False                                   # cumartesi
    if y.weekday() == 6: return y.time() >= dt.time(18, 0)               # pazar akşamı açılır
    if y.weekday() == 4 and y.time() >= dt.time(17, 0): return False     # cuma 17:00 kapanır
    return not (dt.time(17, 0) <= y.time() < dt.time(18, 0))             # günlük mola


def son_kapanis(tur, simdi=None):
    """Şu andan önceki son seans kapanışı (UTC)."""
    t = (simdi or dt.datetime.now(UTC)).astimezone(UTC)
    tz, ac, ka = _seans(tur)
    ka = ka or dt.time(17, 0)
    y = t.astimezone(tz)
    for g in range(0, 8):
        gun = (y - dt.timedelta(days=g)).date()
        if gun.weekday() >= 5 or gun.isoformat() in TATIL.get(tur, ()): continue
        k = dt.datetime.combine(gun, YARIM.get(tur, {}).get(gun.isoformat(), ka), tz)
        if k <= y: return k.astimezone(UTC)
    return t - dt.timedelta(days=3)


def _utc(z):
    if z is None: return None
    if isinstance(z, str):
        try:
            z = dt.datetime.fromisoformat(z.replace("Z", "+00:00"))
        except ValueError:
            return None
    if hasattr(z, "to_pydatetime"): z = z.to_pydatetime()
    if isinstance(z, dt.date) and not isinstance(z, dt.datetime):
        z = dt.datetime.combine(z, dt.time(23, 59), UTC)
    return (z if z.tzinfo else z.replace(tzinfo=UTC)).astimezone(UTC)


def etiket(zaman, tur, simdi=None):
    """→ {"durum", "renk", "kisa", "aciklama", "yas_dk"}; zaman: son verinin zamanı (UTC ya da saat dilimli)."""
    t = (simdi or dt.datetime.now(UTC)).astimezone(UTC)
    z = _utc(zaman)
    if z is None:
        return {"durum": "bayat", "renk": RENK["bayat"], "kisa": "zaman yok", "aciklama": "Verinin zamanı bilinmiyor.", "yas_dk": None}
    yas = max(0.0, (t - z).total_seconds() / 60)
    saat = z.astimezone(TSI).strftime("%d.%m %H:%M")
    if tur == "kripto":
        d = "anlık" if yas <= 20 else "gecikmeli" if yas <= 120 else "bayat"
    elif piyasa_acik(tur, t):
        d = "gecikmeli" if yas <= 50 else "bayat"
    else:
        d = "gün sonu" if z >= son_kapanis(tur, t) - dt.timedelta(minutes=90) else "bayat"
    kisa = {"anlık": "anlık", "gecikmeli": "~15 dk" if yas <= 20 else f"{int(yas)} dk önce", "gün sonu": "kapanış", "bayat": saat}[d]
    ac = {"anlık": "Anlık fiyat.",
          "gecikmeli": "Piyasa açık; ücretsiz kaynak yaklaşık 15 dk gecikmeli.",
          "gün sonu": "Piyasa kapalı; son seansın kapanış verisi.",
          "bayat": "Veri beklenenden eski; kaynakta kesinti ya da tatil olabilir."}[d]
    return {"durum": d, "renk": RENK[d], "kisa": kisa, "aciklama": f"{ac} Son veri: {saat} TSİ.", "yas_dk": round(yas, 1)}


KISA_AD = {"anlık": "canlı", "gecikmeli": "15 dk", "gün sonu": "kapanış", "bayat": "bayat"}


def rozet_kucuk(e):
    """Mini kartlar için: nokta + tek kelime."""
    return (f'<span class="vk vk-k" style="color:{e["renk"]};border-color:{e["renk"]}55"><i style="background:{e["renk"]}"></i>'
            f'{KISA_AD.get(e["durum"], e["durum"])}</span>')


def rozet_html(e):
    """Uygulama kartları için küçük renkli etiket."""
    return (f'<span class="vk" title="{e["aciklama"]}" style="color:{e["renk"]};border-color:{e["renk"]}55">'
            f'<i style="background:{e["renk"]}"></i>{e["durum"]}</span>')


# ---------------------------------------------------------------- kaynak ve yedek tablosu (talimat bölüm 2)
KAYNAKLAR = [
    # (alan, birincil, yedek, gecikme, not)
    ("BIST fiyatları", "Yahoo Finance (yfinance)", "Yahoo 15 dk mumları (günlük bar gecikirse)", "~15 dk", "Kapanış: 18:00–18:10 kapanış seansı dahil resmi fiyat. Anlık BIST verisi lisanslıdır."),
    ("ABD hisse ve endeksleri", "Yahoo Finance", "Yahoo tek tek sorgu", "~15 dk", "Seans öncesi/sonrası dahil değildir."),
    ("Kripto", "Binance (data-api.binance.vision)", "OKX, ardından Yahoo", "anlık", "Anahtarsız, ücretsiz herkese açık uçlar."),
    ("Ons altın ve gram altın", "Binance PAXG (spot ons, 7/24)", "Yahoo altın vadeli (GC=F)", "anlık", "Gram altın = spot ons × USD/TRY ÷ 31,1035; Kapalıçarşı fiyatı yerel prim nedeniyle biraz farklı olabilir."),
    ("Gümüş, petrol", "Yahoo vadeli kontratlar (=F)", "—", "~10–15 dk", "Spot değil, en yakın vadeli kontrat fiyatıdır."),
    ("Döviz", "Yahoo (=X)", "TCMB EVDS (anahtar girilirse)", "dakikalar", "TCMB kuru günde bir kez yayımlanır."),
    ("Türkiye enflasyonu, politika faizi", "TCMB internet sitesi (herkese açık tablo)", "TCMB EVDS, ardından son kayıtlı değer", "aylık / karar günü", "TÜFE her ayın 3'ünde açıklanır."),
    ("Temel analiz (BIST)", "İş Yatırım mali tablolar", "—", "çeyreklik", ""),
    ("Haberler", "Google Haberler RSS", "—", "dakikalar", "KAP'ın iç API'si kullanılmaz; başlık + kaynak bağlantısı gösterilir."),
    ("Ekonomik takvim", "Forex Factory haftalık takvim (faireconomy)", "—", "—", "Beklenti/önceki/açıklanan ayrı."),
    ("Kripto ek veriler", "CoinGecko, DefiLlama, alternative.me, blockchain.info", "—", "dakikalar–saat", ""),
    ("Logolar", "logo.dev (yayınlanabilir anahtar)", "Yerel CC0 kripto ikon seti", "—", ""),
]
