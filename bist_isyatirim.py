# -*- coding: utf-8 -*-
"""İş Yatırım mali tablo verisi (KAP finansallarının standart tablo hâli).
Kişisel, düşük hacimli kullanım içindir. Başarısız olursa çağıran taraf Yahoo verisine döner.

Çıktı, yfinance ile aynı biçimdedir: satırlar İngilizce kalem adları, sütunlar dönem sonu tarihleri
(en yeni solda). Gelir tablosu ve nakit akışı değerleri çeyreklik ayrıştırılır (İş Yatırım kümülatif verir)."""
import re, datetime as dt
import numpy as np
import pandas as pd

URL = "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo"
BASLIK = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
                        "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
          "Accept": "application/json, text/javascript, */*; q=0.01",
          "Referer": "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/sirket-karti.aspx"}

_TR = str.maketrans("çğıöşüÇĞİÖŞÜâîû", "cgiosucgiosuaiu")

def _norm(s):
    s = (s or "").translate(_TR).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = " ".join(s.split())
    # Banka tablolarındaki "XVI.", "2.1.3", "A)" gibi numaralandırmaları at
    s = re.sub(r"^(?:(?:[ivxlc]{1,6}|\d{1,3}|[a-h])\s)+", "", s)
    return s

# anahtar: (desenler, akış mı?, toplama mı?)
KALEMLER = {
    # ---- Bilanço (stok) ----
    "don_var": (["donen varliklar", "current assets"], False, False),
    "nakit": (["nakit ve nakit benzerleri", "cash and cash equivalents"], False, False),
    "kv_fin_yat": (["finansal yatirimlar", "financial investments"], False, False),
    "stok": (["stoklar", "inventories"], False, False),
    "varlik": (["toplam varliklar", "total assets", "aktif toplami", "toplam aktifler", "aktifler toplami",
                "varliklar toplami", "toplam aktif", "aktif toplam"], False, False),
    "kvy": (["kisa vadeli yukumlulukler", "short term liabilities", "current liabilities"], False, False),
    "uvy": (["uzun vadeli yukumlulukler", "long term liabilities", "non current liabilities"], False, False),
    "fin_borc": (["finansal borclar", "financial liabilities", "financial loans", "borrowings"], False, True),
    "ozk_ana": (["ana ortakliga ait ozkaynaklar", "equity attributable to equity holders of the parent",
                 "ana ortakliga ait ozsermaye"], False, False),
    "ozk": (["ozkaynaklar", "shareholders equity", "total equity", "ozsermaye", "ozkaynaklar toplami",
             "toplam ozkaynaklar", "equity"], False, False),
    "azinlik": (["kontrol gucu olmayan paylar", "azinlik paylari", "minority interest", "non controlling interests"], False, False),
    "gecmis": (["gecmis yillar kar zararlari", "gecmis yillar karlari", "retained earnings"], False, False),
    "sermaye": (["odenmis sermaye", "paid in capital", "share capital"], False, False),
    "krediler": (["krediler", "loans", "krediler net", "toplam krediler"], False, False),
    "mevduat": (["mevduat", "deposits", "toplanan fonlar", "mevduat toplami"], False, False),
    # ---- Gelir tablosu (akış, kümülatif) ----
    "ciro": (["satis gelirleri", "hasilat", "net satislar", "sales", "revenue", "net sales"], True, False),
    "brut": (["brut kar zarar", "ticari faaliyetlerden brut kar zarar", "gross profit"], True, False),
    "faal": (["faaliyet kari zarari", "net faaliyet kar zarari", "esas faaliyet kari zarari", "operating profit",
              "operating income"], True, False),
    "vergi_once": (["surdurulen faaliyetler vergi oncesi kari zarari", "vergi oncesi kar zarar",
                    "surdurulen faaliyetler vergi oncesi kar zarar", "profit before tax"], True, False),
    "vergi": (["surdurulen faaliyetler vergi geliri gideri", "donem vergi geliri gideri", "tax expense"], True, False),
    "net": (["donem kari zarari", "net donem kari zarari", "donem net kari zarari", "net profit",
             "profit for the period", "net donem kari", "donem net kari", "surdurulen faaliyetler donem net k z",
             "net kar zarar", "net income"], True, False),
    "net_ana": (["ana ortaklik paylari", "ana ortakliga ait net kar", "attributable to equity holders of the parent",
                 "equity holders of the parent"], True, False),
    "fin_gider": (["finansman giderleri", "esas faaliyet disi finansal giderler", "financial expenses",
                   "finansman gideri"], True, False),
    "amort": (["amortisman giderleri", "amortisman ve itfa giderleri", "depreciation and amortization",
               "amortisman"], True, False),
    "nfg": (["net faiz geliri", "net faiz geliri gideri", "net interest income", "net faiz gelirleri"], True, False),
    "faiz_gel": (["faiz gelirleri", "toplam faiz gelirleri", "faiz gelirleri toplami", "interest income"], True, False),
    "net_ucret": (["net ucret ve komisyon gelirleri giderleri", "net ucret ve komisyon gelirleri",
                   "net fees and commissions income"], True, False),
    "karsilik": (["beklenen zarar karsiliklari", "kredi ve diger alacaklar deger dusus karsiligi",
                  "karsilik giderleri", "provisions"], True, False),
    # ---- Nakit akışı (akış, kümülatif) ----
    "isl_na": (["isletme faaliyetlerinden kaynaklanan net nakit", "isletme faaliyetlerinden nakit akislari",
                "isletme faaliyetlerinden net nakit", "cash flows from operating activities",
                "net cash from operating activities", "bankacilik faaliyetlerinden kaynaklanan net nakit akimi",
                "bankacilik faaliyetlerinden kaynaklanan net nakit", "esas faaliyetlerden kaynaklanan net nakit akimi",
                "esas faaliyetlerden kaynaklanan net nakit"], True, False),
    "capex": (["maddi ve maddi olmayan duran varliklarin alimindan kaynaklanan nakit cikislari",
               "maddi ve maddi olmayan duran varlik alimlari", "sabit sermaye yatirimlari",
               "maddi duran varlik alimlari", "capital expenditure", "purchase of property plant and equipment"], True, False),
    "sna": (["serbest nakit akim", "serbest nakit akimi", "serbest nakit akisi", "free cash flow"], True, False),
    "temettu": (["odenen temettuler", "odenen kar paylari", "odenen temettu", "dividends paid"], True, False),
}

YF_AD = {  # bizim anahtar -> yfinance satır adı
    "don_var": "Current Assets", "nakit": "Cash And Cash Equivalents", "stok": "Inventory",
    "varlik": "Total Assets", "kvy": "Current Liabilities", "azinlik": "Minority Interest",
    "gecmis": "Retained Earnings", "krediler": "Net Loan", "mevduat": "Total Deposits",
    "ciro": "Total Revenue", "brut": "Gross Profit", "faal": "Operating Income", "vergi_once": "Pretax Income",
    "vergi": "Tax Provision", "net": "Net Income", "net_ana": "Net Income Common Stockholders",
    "fin_gider": "Interest Expense", "nfg": "Net Interest Income", "karsilik": "Credit Losses Provision",
    "isl_na": "Operating Cash Flow", "capex": "Capital Expenditure", "sna": "Free Cash Flow",
    "temettu": "Cash Dividends Paid",
}


def _ceyrek_sonlari(n=16, bugun=None):
    bugun = bugun or dt.date.today()
    y, q = bugun.year, (bugun.month - 1) // 3  # q: tamamlanmış çeyrek sayısı
    out = []
    for _ in range(n):
        if q == 0:
            y, q = y - 1, 4
        out.append((y, q * 3)); q -= 1
    return out  # en yeni önce


def _cek(kod, grup, donemler, oturum, zaman_asimi=15):
    import requests
    s = oturum or requests.Session()
    satirlar = {}
    for i in range(0, len(donemler), 4):
        parca = donemler[i:i + 4]
        prm = {"companyCode": kod, "exchange": "TRY", "financialGroup": grup}
        for j, (yy, pp) in enumerate(parca, 1):
            prm[f"year{j}"] = yy; prm[f"period{j}"] = pp
        r = s.get(URL, params=prm, headers=BASLIK, timeout=zaman_asimi)
        r.raise_for_status()
        js = r.json()
        liste = js.get("value") if isinstance(js, dict) else js
        if not liste:
            continue
        for sira, it in enumerate(liste):
            anahtar = (sira, it.get("itemCode"), it.get("itemDescTr"), it.get("itemDescEng"))
            dd = satirlar.setdefault(anahtar, {})
            for j, (yy, pp) in enumerate(parca, 1):
                v = it.get(f"value{j}")
                try:
                    v = float(str(v).replace(",", ".")) if v not in (None, "", "null") else np.nan
                except Exception:
                    v = np.nan
                dd[(yy, pp)] = v
    return satirlar


def _bul(satirlar, desenler, topla):
    adlar = [(k, _norm(k[2]), _norm(k[3])) for k in satirlar]
    for mod in ("esit", "baslar"):
        bulunan = []
        for k, tr, en in adlar:
            for d in desenler:
                if (mod == "esit" and (tr == d or en == d)) or (mod == "baslar" and (tr.startswith(d) or en.startswith(d))):
                    bulunan.append(k); break
        if bulunan:
            return bulunan if topla else bulunan[:1]
    return []


def _tarih(yy, pp):
    return pd.Timestamp(yy, pp, 1) + pd.offsets.MonthEnd(0)


def finansallar(kod, oturum=None, bugun=None, ceyrek_sayi=8):
    """İş Yatırım'dan finansalları çeker. Başarısızsa istisna fırlatır."""
    donemler = _ceyrek_sonlari(16, bugun)
    satirlar, grup = {}, None
    for g in ("XI_29", "UFRS"):
        satirlar = _cek(kod, g, donemler, oturum)
        dolu = {k: v for k, v in satirlar.items() if any(not np.isnan(x) for x in v.values())}
        if len(dolu) > 10:
            satirlar, grup = dolu, g
            break
    if not grup:
        raise ValueError("İş Yatırım'da bu hisse için mali tablo bulunamadı")
    # Veri olan dönemler
    donem_dolu = [p for p in donemler if any(not np.isnan(v.get(p, np.nan)) for v in satirlar.values())]
    if not donem_dolu:
        raise ValueError("İş Yatırım boş veri döndürdü")

    ham = {}
    for anahtar, (desen, akis, topla) in KALEMLER.items():
        bul = _bul(satirlar, desen, topla)
        if not bul:
            continue
        seri = {}
        for p in donem_dolu:
            vals = [satirlar[k].get(p, np.nan) for k in bul]
            vals = [v for v in vals if not np.isnan(v)]
            seri[p] = sum(vals) if vals else np.nan
        ham[anahtar] = (seri, akis)

    # Türetilmiş kalemler
    def stok(k):
        return ham.get(k, ({}, False))[0]
    if "ozk_ana" not in ham and "ozk" in ham:
        ozk_toplam = stok("ozk"); az = stok("azinlik")
        ham["ozk_ana"] = ({p: ozk_toplam.get(p, np.nan) - (az.get(p) if not np.isnan(az.get(p, np.nan)) else 0)
                           for p in donem_dolu}, False)
    if "ciro" not in ham and grup == "UFRS":
        # Banka gelirleri: net faiz geliri + net ücret/komisyon (yoksa brüt faiz gelirleri)
        if "nfg" in ham:
            nu = stok("net_ucret")
            ham["ciro"] = ({p: stok("nfg").get(p, np.nan) + (nu.get(p) if not np.isnan(nu.get(p, np.nan)) else 0)
                            for p in donem_dolu}, True)
        elif "faiz_gel" in ham:
            ham["ciro"] = ham["faiz_gel"]
    if "kvy" in ham and "uvy" in ham:
        ham["yukum"] = ({p: stok("kvy").get(p, np.nan) + stok("uvy").get(p, np.nan) for p in donem_dolu}, False)
    if "nakit" in ham:
        fy = stok("kv_fin_yat")
        ham["nakit_yat"] = ({p: stok("nakit").get(p, np.nan) + (fy.get(p) if not np.isnan(fy.get(p, np.nan)) else 0)
                             for p in donem_dolu}, False)

    # Kümülatif → çeyreklik
    def ceyreklik(seri):
        out = {}
        for (yy, pp), v in seri.items():
            if pp == 3:
                out[(yy, pp)] = v
            else:
                once = seri.get((yy, pp - 3), np.nan)
                out[(yy, pp)] = v - once if not (np.isnan(v) or np.isnan(once)) else np.nan
        return out

    yil_sonlari = [p for p in donem_dolu if p[1] == 12]
    def df_yap(anahtarlar, yillik):
        veri = {}
        for k in anahtarlar:
            if k not in ham:
                continue
            seri, akis = ham[k]
            if yillik:
                d = {p: seri.get(p, np.nan) for p in yil_sonlari}
            else:
                d = ceyreklik(seri) if akis else seri
                d = {p: d.get(p, np.nan) for p in donem_dolu[:ceyrek_sayi]}
            veri[k] = d
        if not veri:
            return pd.DataFrame()
        df = pd.DataFrame(veri).T
        df.columns = [_tarih(*c) for c in df.columns]
        df = df.dropna(axis=1, how="all")
        return df[sorted(df.columns, reverse=True)]

    BIL = ["don_var", "nakit", "nakit_yat", "stok", "varlik", "kvy", "yukum", "fin_borc", "ozk_ana", "azinlik",
           "gecmis", "sermaye", "krediler", "mevduat"]
    GEL = ["ciro", "brut", "faal", "vergi_once", "vergi", "net", "net_ana", "fin_gider", "amort", "nfg", "karsilik"]
    NAK = ["isl_na", "capex", "sna", "temettu"]

    def yf_bicim(df):
        if df.empty:
            return df
        df = df.copy()
        # FAVÖK = faaliyet kârı + amortisman
        if "faal" in df.index and "amort" in df.index:
            df.loc["ebitda"] = df.loc["faal"] + df.loc["amort"].abs()
        if "capex" in df.index:
            df.loc["capex"] = -df.loc["capex"].abs()
        if "temettu" in df.index:
            df.loc["temettu"] = -df.loc["temettu"].abs()
        if "fin_gider" in df.index:
            df.loc["fin_gider"] = df.loc["fin_gider"].abs()
        if "sna" not in df.index and "isl_na" in df.index and "capex" in df.index:
            df.loc["sna"] = df.loc["isl_na"] + df.loc["capex"]
        ad = dict(YF_AD, ebitda="EBITDA", fin_borc="Total Debt", ozk_ana="Stockholders Equity",
                  yukum="Total Liabilities Net Minority Interest",
                  nakit_yat="Cash Cash Equivalents And Short Term Investments", sermaye="Ordinary Shares Number")
        df.index = [ad.get(i, i) for i in df.index]
        if "Total Assets" in df.index and "Total Debt" not in df.index:
            df.loc["Total Debt"] = 0.0
        return df

    sonuc = {
        "gelir": yf_bicim(df_yap(GEL, True)), "q_gelir": yf_bicim(df_yap(GEL, False)),
        "bilanco": yf_bicim(df_yap(BIL, True)), "q_bilanco": yf_bicim(df_yap(BIL, False)),
        "nakit": yf_bicim(df_yap(NAK, True)), "q_nakit": yf_bicim(df_yap(NAK, False)),
        "grup": grup, "son_donem": _tarih(*donem_dolu[0]),
    }
    # Sermaye satırı TL cinsindendir (nominal 1 TL); hisse adedi yedeği olarak kullanılır
    for k in ("bilanco", "q_bilanco"):
        if "Ordinary Shares Number" in sonuc[k].index and grup == "UFRS":
            sonuc[k] = sonuc[k].drop(index="Ordinary Shares Number")
    ornek = " | ".join(str(k[2])[:28] for k in list(satirlar)[:40])
    zorunlu = {"Total Assets", "Stockholders Equity"}
    eksik = zorunlu - (set(sonuc["q_bilanco"].index) | set(sonuc["bilanco"].index))
    if eksik:
        raise ValueError(f"{grup}: {', '.join(sorted(eksik))} eşleşmedi. Kalemler: {ornek}")
    if "Net Income" not in sonuc["gelir"].index and "Net Income Common Stockholders" not in sonuc["gelir"].index:
        raise ValueError(f"{grup}: net kâr eşleşmedi. Kalemler: {ornek}")
    return sonuc


# ---------------------------------------------------------------------------
# Yabancı oranı (şirket kartındaki "Yabancı Oranı (%)" güncel değeri)
# ---------------------------------------------------------------------------
KART_URL = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/sirket-karti.aspx"

def yabanci_orani(kod, oturum=None, zaman_asimi=15):
    """Hissenin güncel yabancı oranını (%) döndürür; bulunamazsa istisna fırlatır."""
    import requests, html as _html
    s = oturum or requests.Session()
    r = s.get(KART_URL, params={"hisse": kod.upper()}, headers=BASLIK, timeout=zaman_asimi)
    r.raise_for_status()
    metin = _html.unescape(re.sub(r"<[^>]+>", " ", r.text))
    metin = " ".join(metin.split())
    m = re.search(r"Yabanc[ıi] Oran[ıi]\s*\(%\)\s*([0-9]{1,3}(?:[.,][0-9]+)?)", metin)
    if not m:
        raise ValueError("Yabancı oranı sayfada bulunamadı")
    v = float(m.group(1).replace(",", "."))
    if not 0 <= v <= 100:
        raise ValueError(f"Yabancı oranı geçersiz: {v}")
    return v
