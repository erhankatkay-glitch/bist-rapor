# -*- coding: utf-8 -*-
"""Tüm BIST evreni ve 'bebek şirketler' (yeni halka arzlar / küçük ölçekli şirketler) taraması.
Kaynaklar (ücretsiz): İş Yatırım 'Temel Değerler ve Oranlar' sayfası (tüm hisseler, sektör, piyasa değeri,
halka açıklık) ve Yahoo Finance aylık fiyat geçmişi (ilk işlem tarihi)."""
import io, os, re, datetime as dt
import numpy as np
import pandas as pd

URL = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Temel-Degerler-Ve-Oranlar.aspx"
BIST_ENDEKS_URL = "https://borsaistanbul.com/datum/hisse_endeks_ds.csv"   # tüm BIST endekslerinin bileşenleri
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
KOD_RE = re.compile(r"^[A-Z0-9]{3,6}(\.E)?$")


def _endeks_cozumle(ham):
    """Borsa İstanbul bileşen dosyasını biçimden bağımsız çözer → DataFrame[Kod, Ad, Endeks]."""
    import gzip
    if ham[:2] == b"\x1f\x8b": ham = gzip.decompress(ham)
    if ham[:2] == b"PK":
        df = pd.read_excel(io.BytesIO(ham), dtype=str)
    else:
        for enc in ("utf-8-sig", "cp1254", "iso-8859-9", "latin-1"):
            try: metin = ham.decode(enc); break
            except UnicodeDecodeError: continue
        satirlar = [s for s in metin.splitlines() if s.strip()]
        sep = max([";", ",", "\t", "|"], key=lambda c: satirlar[0].count(c))
        df = pd.read_csv(io.StringIO("\n".join(satirlar)), sep=sep, dtype=str, engine="python")
    df.columns = [_sade(c).upper() for c in df.columns]
    df = df.apply(lambda s: s.astype(str).str.strip())
    def oran(c, desen): return df[c].str.match(desen).mean()
    kod_c = next((c for c in df.columns if "BILE" in c and "KOD" in c), None)
    end_c = next((c for c in df.columns if "ENDEKS" in c and "KOD" in c), None)
    if end_c is None:
        end_c = max(df.columns, key=lambda c: oran(c, r"^X[A-Z0-9]{2,6}$"))
    if kod_c is None:
        aday = [c for c in df.columns if c != end_c]
        kod_c = max(aday, key=lambda c: oran(c, KOD_RE.pattern) - oran(c, r"^X[A-Z0-9]{2,6}$"))
    ad_c = next((c for c in df.columns if ("BULTEN" in c or "UNVAN" in c or c == "AD" or ("ADI" in c and "ENDEKS" not in c))
                 and c not in (kod_c, end_c)), None)
    out = pd.DataFrame({"Kod": df[kod_c].str.replace(r"\.E$|\.IS$", "", regex=True).str.upper(),
                        "Ad": df[ad_c] if ad_c else df[kod_c], "Endeks": df[end_c].str.upper()})
    return out[out["Kod"].str.match(r"^[A-Z0-9]{3,6}$")]


def bist_endeks_bilesenleri(oturum=None):
    import requests
    r = (oturum or requests).get(BIST_ENDEKS_URL, headers=UA, timeout=30)
    r.raise_for_status()
    return _endeks_cozumle(r.content)


def bist_listesi(oturum=None):
    """Güncel tüm BIST hisseleri. (DataFrame[Kod, Ad, Sektör, PD mn, ...], XHARZ kodları kümesi, kaynak notu)."""
    notlar, harz = [], set()
    bilesen = None
    try:
        bilesen = bist_endeks_bilesenleri(oturum)
        harz = set(bilesen.loc[bilesen["Endeks"] == "XHARZ", "Kod"])
        tum = bilesen[bilesen["Endeks"] == "XUTUM"]
        tum = tum if len(tum) > 300 else bilesen
        bdf = tum.drop_duplicates("Kod")[["Kod", "Ad"]]
        notlar.append(f"Borsa İstanbul endeks bileşenleri ({len(bdf)} hisse)")
    except Exception as ex:
        bdf = None; notlar.append(f"Borsa İstanbul listesi alınamadı ({str(ex)[:60]})")
    try:
        idf = tum_hisseler(oturum); notlar.append(f"İş Yatırım ({len(idf)} hisse)")
    except Exception as ex:
        idf = None; notlar.append(f"İş Yatırım listesi alınamadı ({str(ex)[:60]})")
    if bdf is not None and idf is not None:
        df = idf.merge(bdf.rename(columns={"Ad": "Ad_bist"}), on="Kod", how="outer")
        df["Ad"] = df["Ad"].fillna(df["Ad_bist"]); df = df.drop(columns=["Ad_bist"])
    else:
        df = idf if idf is not None else bdf
    if df is None or len(df) < 200:
        import bist_veri as bv
        yedek = pd.read_csv(bv.LISTE_DOSYA, dtype=str) if os.path.exists(bv.LISTE_DOSYA) else \
            pd.DataFrame({"Kod": list(bv.SIRKETLER), "Ad": list(bv.SIRKETLER.values())})
        df = yedek if df is None else pd.concat([df, yedek[~yedek["Kod"].isin(df["Kod"])]])
        notlar.append(f"yedek liste ({len(yedek)} hisse)")
    df = df.dropna(subset=["Kod"]).drop_duplicates("Kod").sort_values("Kod").reset_index(drop=True)
    for c in ("PD mn", "PD $ mn", "Halka açıklık %", "Kapanış"):
        if c in df: df[c] = pd.to_numeric(df[c], errors="coerce")
    df["XHARZ"] = df["Kod"].isin(harz)
    endeks_ici = len(bdf) if bdf is not None else None
    ozet = f"Toplam {len(df)} hisse" + (f" (BIST Tüm endeksinde {endeks_ici}, endeks dışı / yeni halka arz {len(df) - endeks_ici})" if endeks_ici else "")
    return df, harz, ozet + " · kaynaklar: " + " · ".join(notlar)


def liste_kaydet(df, yol=None):
    import bist_veri as bv
    kol = [c for c in ("Kod", "Ad", "Sektör", "PD mn", "Halka açıklık %", "XHARZ") if c in df]
    df[kol].to_csv(yol or bv.LISTE_DOSYA, index=False)


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
                             progress=False, group_by="ticker", threads=4)
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


HARZ_YIL = 2  # BIST Halka Arz Endeksi: şirket işlem görmeye başladığı ilk gün endekse alınır ve 2 yıl kalır


def bebekler(evren, ilk, harz=None, bugun=None, resmi_ilk=None, mod="resmi", yil=5, pd_esik=15.0):
    """mod: 'resmi' → BIST'in resmi bebek tanımı (XHARZ, son 2 yıl); 'genc' → son `yil` yılda halka arz olan tüm BIST
    şirketleri; 'kucuk' → tüm BIST'te piyasa değeri `pd_esik` milyar TL altındaki şirketler (yaşından bağımsız)."""
    if mod != "resmi":
        harz = None
    """Bebek şirketler = Borsa İstanbul'un resmi tanımıyla son 2 yılda halka arz edilip işlem görmeye başlayan
    şirketler (BIST Halka Arz Endeksi / XHARZ kapsamı). Resmi bileşen listesi alınabildiyse o kullanılır;
    alınamadıysa Yahoo'daki ilk işlem tarihi 2 yıldan yeni olan hisseler seçilir."""
    bugun = pd.Timestamp(bugun or dt.date.today())
    resmi = bool(harz)
    sat = []
    for _, r in evren.iterrows():
        k = r["Kod"]; b = ilk.get(k); rs = (resmi_ilk or {}).get(k) or {}
        ilk_t = rs.get("tarih") if rs.get("tarih") is not None and not pd.isna(rs.get("tarih")) else (b["ilk"] if b else None)
        yas = (bugun - pd.Timestamp(ilk_t)).days / 365.25 if ilk_t is not None else None
        pd_mr = r.get("PD mn") / 1000 if pd.notna(r.get("PD mn")) else None
        if mod == "kucuk":
            if pd_mr is None or pd_mr > pd_esik: continue
        elif mod == "genc":
            if yas is None or yas > yil: continue
        elif resmi:
            if k not in harz: continue
        elif yas is None or yas > HARZ_YIL:
            continue
        ay = round(yas * 12) if yas is not None else None
        sat.append({"Kod": k, "Şirket": r.get("Ad"), "Sektör": r.get("Sektör"),
                    "İlk işlem": pd.Timestamp(ilk_t).date() if ilk_t is not None else None, "Borsadaki süre (ay)": ay,
                    "İlk gün kapanışı": rs.get("ilk_kapanis"),
                    "Endekste kalan (ay)": (max(24 - ay, 0) if ay is not None else None) if mod == "resmi" else None,
                    "Piyasa değeri (mr TL)": round(pd_mr, 2) if pd_mr is not None else None,
                    "Halka açıklık %": r.get("Halka açıklık %"),
                    "İlk işlemden getiri": (b["son"] / b["ilk_fiyat"] - 1) if b and b["ilk_fiyat"] else None,
                    "Zirveden uzaklık": (b["son"] / b["zirve"] - 1) if b and b["zirve"] else None})
    if mod == "kucuk":
        return sorted(sat, key=lambda x: x["Piyasa değeri (mr TL)"] or 0, reverse=True), resmi
    return sorted(sat, key=lambda x: (x["İlk işlem"] or dt.date(2100, 1, 1)), reverse=True), resmi and mod == "resmi"


BEBEK_AGIRLIK = {"Reel büyüme": 0.30, "Sağlık skoru": 0.25, "Büyüme potansiyeli": 0.20, "Çeyrek büyüme (reel)": 0.15, "Akış puanı": 0.10}
BEBEK_AD = {"Reel büyüme": "hızlı reel büyüme", "Sağlık skoru": "sağlam temeller", "Büyüme potansiyeli": "büyümesine göre ucuz",
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
