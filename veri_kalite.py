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


def tur_bul(kod):
    """Yahoo / Binance kodundan piyasa türü."""
    k = str(kod).upper()
    if k.endswith(".IS"): return "bist"
    if k.endswith("-USD") or "/" in k or k.endswith("USDT"): return "kripto"
    if k.endswith("=F"): return "emtia"
    if k.endswith("=X") or k.startswith("DX-Y"): return "doviz"
    if k in ("^TNX", "^IRX", "^FVX", "^TYX"): return "faiz"
    return "abd"


def _seans(tur):
    """(saat dilimi, açılış, kapanış, 7/24 mü, gün içi mola yok mu)"""
    if tur == "bist": return TSI, dt.time(10, 0), dt.time(18, 10)
    if tur in ("abd", "faiz"): return NY, dt.time(9, 30), dt.time(16, 0)
    return NY, None, None          # emtia ve döviz: pazar 18:00 – cuma 17:00 NY (her gün 17–18 arası mola)


def piyasa_acik(tur, simdi=None):
    t = (simdi or dt.datetime.now(UTC)).astimezone(UTC)
    if tur == "kripto": return True
    tz, ac, ka = _seans(tur)
    y = t.astimezone(tz)
    if ac is not None:
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
        if gun.weekday() >= 5: continue
        k = dt.datetime.combine(gun, ka, tz)
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
    kisa = {"anlık": "anlık", "gecikmeli": f"{int(yas)} dk önce" if yas < 120 else saat, "gün sonu": "kapanış", "bayat": saat}[d]
    ac = {"anlık": "Anlık fiyat.",
          "gecikmeli": "Piyasa açık; ücretsiz kaynak yaklaşık 15 dk gecikmeli.",
          "gün sonu": "Piyasa kapalı; son seansın kapanış verisi.",
          "bayat": "Veri beklenenden eski; kaynakta kesinti ya da tatil olabilir."}[d]
    return {"durum": d, "renk": RENK[d], "kisa": kisa, "aciklama": f"{ac} Son veri: {saat} TSİ.", "yas_dk": round(yas, 1)}


def rozet_html(e):
    """Uygulama kartları için küçük renkli etiket."""
    return (f'<span class="vk" title="{e["aciklama"]}" style="color:{e["renk"]};border-color:{e["renk"]}55">'
            f'<i style="background:{e["renk"]}"></i>{e["durum"]}</span>')


# ---------------------------------------------------------------- kaynak ve yedek tablosu (talimat bölüm 2)
KAYNAKLAR = [
    # (alan, birincil, yedek, gecikme, not)
    ("BIST fiyatları", "Yahoo Finance (yfinance)", "Yahoo tek tek sorgu", "~15 dk", "Anlık BIST verisi lisanslıdır, ücretsiz değildir."),
    ("ABD hisse ve endeksleri", "Yahoo Finance", "Yahoo tek tek sorgu", "~15 dk", "Seans öncesi/sonrası dahil değildir."),
    ("Kripto", "Binance (data-api.binance.vision)", "OKX, ardından Yahoo", "anlık", "Anahtarsız, ücretsiz herkese açık uçlar."),
    ("Emtia (altın, gümüş, petrol)", "Yahoo vadeli kontratlar (=F)", "—", "~10–15 dk", "Spot değil, en yakın vadeli kontrat fiyatıdır."),
    ("Döviz", "Yahoo (=X)", "TCMB EVDS (anahtar girilirse)", "dakikalar", "TCMB kuru günde bir kez yayımlanır."),
    ("Türkiye enflasyonu, politika faizi", "TCMB internet sitesi (herkese açık tablo)", "TCMB EVDS, ardından son kayıtlı değer", "aylık / karar günü", "TÜFE her ayın 3'ünde açıklanır."),
    ("Temel analiz (BIST)", "İş Yatırım mali tablolar", "—", "çeyreklik", ""),
    ("Haberler", "Google Haberler RSS", "—", "dakikalar", "KAP'ın iç API'si kullanılmaz; başlık + kaynak bağlantısı gösterilir."),
    ("Ekonomik takvim", "Forex Factory haftalık takvim (faireconomy)", "—", "—", "Beklenti/önceki/açıklanan ayrı."),
    ("Kripto ek veriler", "CoinGecko, DefiLlama, alternative.me, blockchain.info", "—", "dakikalar–saat", ""),
    ("Logolar", "logo.dev (yayınlanabilir anahtar)", "Yerel CC0 kripto ikon seti", "—", ""),
]
