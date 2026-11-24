# -*- coding: utf-8 -*-
"""Tüm BIST evreni ve 'bebek şirketler' (yeni halka arzlar / küçük ölçekli şirketler) taraması.
Kaynaklar (ücretsiz): İş Yatırım 'Temel Değerler ve Oranlar' sayfası (tüm hisseler, sektör, piyasa değeri,
halka açıklık) ve Yahoo Finance aylık fiyat geçmişi (ilk işlem tarihi)."""
import io, re, datetime as dt
import numpy as np
import pandas as pd

URL = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Temel-Degerler-Ve-Oranlar.aspx"


def _sade(s):
    return re.sub(r"\s+", " ", str(s)).strip()


def tum_hisseler(oturum=None):
    """Borsada işlem gören tüm hisseler: Kod, Ad, Sektör, Kapanış, PD (mn TL), PD ($ mn), Halka açıklık (%)."""
    import requests
    r = (oturum or requests).get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    tablolar = pd.read_html(io.StringIO(r.text), thousands=".", decimal=",")
    aday = []
    for t in tablolar:
        if isinstance(t.columns, pd.MultiIndex):
            t.columns = [_sade(" ".join(str(x) for x in c if "Unnamed" not in str(x))) for c in t.columns]
        t.columns = [_sade(c) for c in t.columns]
        if any(c == "Kod" for c in t.columns) and any("Piyasa Değeri" in c for c in t.columns):
            aday.append(t)
    if not aday:
        raise ValueError("İş Yatırım hisse listesi tablosu bulunamadı (sayfa yapısı değişmiş olabilir).")
    t = max(aday, key=len)
    ad = {}
    for c in t.columns:
        if c == "Kod": ad[c] = "Kod"
        elif "Hisse Adı" in c: ad[c] = "Ad"
        elif "Sektör" in c: ad[c] = "Sektör"
        elif "Kapanış" in c: ad[c] = "Kapanış"
        elif "Piyasa Değeri" in c and "$" in c: ad[c] = "PD $ mn"
        elif "Piyasa Değeri" in c: ad[c] = "PD mn"
        elif "Halka" in c: ad[c] = "Halka açıklık %"
        elif "Sermaye" in c: ad[c] = "Sermaye mn"
    t = t.rename(columns=ad)[list(dict.fromkeys(ad.values()))]
    t["Kod"] = t["Kod"].astype(str).str.extract(r"([A-Z0-9]{3,6})", expand=False)
    t = t.dropna(subset=["Kod"]).drop_duplicates("Kod")
    for c in ("Kapanış", "PD mn", "PD $ mn", "Halka açıklık %", "Sermaye mn"):
        if c in t: t[c] = pd.to_numeric(t[c], errors="coerce")
    return t.reset_index(drop=True)


def ilk_islemler(kodlar, parca=80):
    """Yahoo aylık geçmişinden her hissenin ilk işlem ayı, ilk fiyatı (bölünme/bedelsiz düzeltilmiş),
    son fiyatı ve zirvesi."""
    import yfinance as yf
    out = {}
    kodlar = list(kodlar)
    for i in range(0, len(kodlar), parca):
        grup = kodlar[i:i + parca]
        try:
            df = yf.download([k + ".IS" for k in grup], period="max", interval="1mo", auto_adjust=True,
                             progress=False, group_by="ticker", threads=True)
        except Exception:
            continue
        for k in grup:
            try:
                d = df[k + ".IS"] if isinstance(df.columns, pd.MultiIndex) else df
                c = d["Close"].dropna()
                if c.empty: continue
                o = d["Open"].reindex(c.index).dropna()
                out[k] = {"ilk": pd.Timestamp(c.index[0]).tz_localize(None) if c.index.tz is not None else pd.Timestamp(c.index[0]),
                          "ilk_fiyat": float(o.iloc[0]) if len(o) else float(c.iloc[0]), "son": float(c.iloc[-1]),
                          "zirve": float(d["High"].reindex(c.index).max())}
            except Exception:
                continue
    return out


def bebekler(evren, ilk, maks_yil=3.0, maks_pd_mr=None, bugun=None):
    """Filtre: borsada en fazla `maks_yil` yıldır işlem gören (yeni halka arz) ve/veya
    piyasa değeri en fazla `maks_pd_mr` milyar TL olan şirketler. Yahoo verisi 2000 öncesine gitmediği
    için çok eski şirketler zaten elenir."""
    bugun = pd.Timestamp(bugun or dt.date.today())
    sat = []
    for _, r in evren.iterrows():
        k = r["Kod"]; b = ilk.get(k)
        yas = (bugun - b["ilk"]).days / 365.25 if b else None
        pd_mr = r.get("PD mn") / 1000 if pd.notna(r.get("PD mn")) else None
        if maks_yil and (yas is None or yas > maks_yil): continue
        if maks_pd_mr and (pd_mr is None or pd_mr > maks_pd_mr): continue
        if not maks_yil and not maks_pd_mr: continue
        sat.append({"Kod": k, "Şirket": r.get("Ad"), "Sektör": r.get("Sektör"),
                    "İlk işlem": b["ilk"].date() if b else None, "Borsadaki süre (ay)": round(yas * 12) if yas is not None else None,
                    "Piyasa değeri (mr TL)": round(pd_mr, 2) if pd_mr is not None else None,
                    "Halka açıklık %": r.get("Halka açıklık %"),
                    "İlk işlemden getiri": (b["son"] / b["ilk_fiyat"] - 1) if b and b["ilk_fiyat"] else None,
                    "Zirveden uzaklık": (b["son"] / b["zirve"] - 1) if b and b["zirve"] else None})
    return sorted(sat, key=lambda x: (x["İlk işlem"] or dt.date(1900, 1, 1)), reverse=True)


BEBEK_AGIRLIK = {"Reel büyüme": 0.30, "Sağlık skoru": 0.30, "Potansiyel": 0.15, "Çeyrek büyüme (reel)": 0.15, "Akış puanı": 0.10}
BEBEK_AD = {"Reel büyüme": "hızlı reel büyüme", "Sağlık skoru": "sağlam temeller", "Potansiyel": "değerleme iskontosu",
            "Çeyrek büyüme (reel)": "son çeyrekte ivme", "Akış puanı": "para girişi"}


def bebek_skoru(satirlar):
    """Derin tarama satırlarına, bebek şirketler kendi içinde kıyaslanarak 0–100 'Bebek skoru' ekler."""
    if not satirlar: return satirlar
    df = pd.DataFrame(satirlar)
    uygun = df.get("Veri puanı", pd.Series([100] * len(df))).fillna(0) >= 50
    yuzde = {c: df.loc[uygun, c].rank(pct=True) for c in BEBEK_AGIRLIK if c in df}
    for i in range(len(df)):
        if not uygun.iloc[i]:
            satirlar[i]["Bebek skoru"] = None; satirlar[i]["Neden"] = "finansal veri yetersiz"; continue
        top = w = 0.0; ned = []
        for c, ag in BEBEK_AGIRLIK.items():
            p = yuzde.get(c, pd.Series(dtype=float)).get(i)
            if p is not None and not pd.isna(p):
                top += p * ag; w += ag
                if p >= 0.75: ned.append(BEBEK_AD[c])
        satirlar[i]["Bebek skoru"] = round(100 * top / w, 1) if w >= 0.5 else None
        satirlar[i]["Neden"] = ", ".join(ned) if ned else "dengeli profil"
    return satirlar


def risk_notlari(satir):
    """Yeni/küçük şirketlere özgü uyarılar."""
    n = []
    if (satir.get("Borsadaki süre (ay)") or 99) < 12: n.append("1 yıldan kısa geçmiş: analiz için az veri")
    if (satir.get("Halka açıklık %") or 100) < 25: n.append("düşük halka açıklık: fiyat kolay oynayabilir")
    if (satir.get("Piyasa değeri (mr TL)") or 99) < 2: n.append("çok küçük ölçek: likidite riski")
    if (satir.get("İlk işlemden getiri") or 0) > 3: n.append("ilk işlemden bu yana çok yükselmiş")
    return "; ".join(n)
