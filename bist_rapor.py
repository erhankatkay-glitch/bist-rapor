# -*- coding: utf-8 -*-
"""
BIST Hisse Araştırma Raporu – Profesyonel sürüm
Veri: Yahoo Finance (yfinance). Bu rapor yatırım tavsiyesi değildir.
"""
import os, io, math, datetime as dt, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, KeepTogether, CondPageBreak)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

warnings.filterwarnings("ignore")

# =====================================================================
# PARAMETRELER (Kasım 2026 piyasa koşullarına göre varsayılanlar)
# =====================================================================
PARAM = {
    "RF": 0.36,
    "MAKS_POTANSIYEL": 0.80,  # adil değer en fazla fiyatın %80 üstü (temkinli sınır)
    "MIN_POTANSIYEL": -0.60,          # Risksiz faiz: TR 10Y gösterge tahvil (~%36,6, 19.11.2026)
    "ERP": 0.07,         # Hisse senedi risk primi
    "TERMINAL_G": 0.15,  # DCF uç büyüme (nominal TL)
    "ENFLASYON": 0.2977, # TÜİK yıllık TÜFE (Ekim 2026)
    "VERGI": 0.25,       # Kurumlar vergisi
    "DCF_YIL": 5,
}

SURUM = "2026.11.24-7"

import bist_veri as BV

# Finansallarını döviz cinsinden raporlayan bilinen şirketler (Yahoo bilgi vermezse yedek)
DOVIZ_RAPORLAYAN = {"THYAO": "USD", "PGSUS": "USD", "TAVHL": "EUR"}

# BIST sektör emsal grupları (EMSALLER boş bırakılırsa buradan seçilir)
SEKTOR_GRUPLARI = {
    "Bankacılık": ["AKBNK", "GARAN", "YKBNK", "ISCTR", "HALKB", "VAKBN", "TSKB", "ALBRK"],
    "Holding": ["KCHOL", "SAHOL", "DOHOL", "AGHOL", "TKFEN", "ALARK"],
    "Havacılık": ["THYAO", "PGSUS", "TAVHL", "CLEBI"],
    "Demir-Çelik": ["EREGL", "KRDMD", "ISDMR", "KCAER", "BRSAN"],
    "Otomotiv": ["FROTO", "TOASO", "DOAS", "TTRAK", "OTKAR", "ASUZU"],
    "Perakende": ["BIMAS", "MGROS", "SOKM", "MAVI"],
    "Telekom": ["TCELL", "TTKOM"],
    "Enerji": ["TUPRS", "AKSEN", "ENJSA", "AYDEM", "ODAS", "ZOREN", "AYGAZ"],
    "Savunma": ["ASELS", "SDTTR", "ALTNY"],
    "Kimya-Cam": ["SISE", "PETKM", "SASA", "HEKTS", "GUBRF", "ALKIM"],
    "Çimento": ["CIMSA", "AKCNS", "OYAKC", "BTCIM", "NUHCM"],
    "Gıda-İçecek": ["ULKER", "CCOLA", "AEFES", "TATGD", "BANVT"],
    "Dayanıklı Tüketim": ["ARCLK", "VESTL", "VESBE"],
    "GYO": ["EKGYO", "ISGYO", "TRGYO"],
    "Sigorta": ["ANSGR", "AKGRT", "TURSG", "AGESA"],
    "Teknoloji": ["LOGO", "KAREL", "NETAS", "INDES", "ARDYZ"],
    "Madencilik": ["KOZAL", "KOZAA", "IPEKE"],
    "İnşaat-Taahhüt": ["ENKAI", "TKFEN"],
}

# =====================================================================
# STİL
# =====================================================================
_FD = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
pdfmetrics.registerFont(TTFont("DV", os.path.join(_FD, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB", os.path.join(_FD, "DejaVuSans-Bold.ttf")))
from reportlab.lib.fonts import addMapping
addMapping("DV", 0, 0, "DV"); addMapping("DV", 1, 0, "DVB"); addMapping("DV", 0, 1, "DV"); addMapping("DV", 1, 1, "DVB")

LAC = colors.HexColor("#14294B"); MAVI = colors.HexColor("#2F6DB5"); ACIK = colors.HexColor("#F1F4F9")
YESIL = colors.HexColor("#1E8E5A"); KIRMIZI = colors.HexColor("#C0392B"); SARI = colors.HexColor("#D9A21B")
GRI = colors.HexColor("#6B7280"); CIZGI = colors.HexColor("#D5DBE5")
C = {"lac": "#14294B", "mavi": "#2F6DB5", "tur": "#E07A1F", "yesil": "#1E8E5A", "kirmizi": "#C0392B",
     "sari": "#D9A21B", "gri": "#9CA3AF", "acik": "#BFD3EA"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 9.5,
                     "axes.titleweight": "bold", "axes.edgecolor": "#9CA3AF",
                     "axes.spines.top": False, "axes.spines.right": False})

def _st(ad, **kw):
    base = dict(fontName="DV", fontSize=8.8, leading=12.2, textColor=colors.HexColor("#1F2937"))
    base.update(kw); return ParagraphStyle(ad, **base)
ST = {
    "h1": _st("h1", fontName="DVB", fontSize=14, leading=18, textColor=LAC, spaceBefore=4, spaceAfter=6),
    "h2": _st("h2", fontName="DVB", fontSize=10.5, leading=14, textColor=MAVI, spaceBefore=8, spaceAfter=4),
    "p": _st("p", alignment=4),
    "kucuk": _st("k", fontSize=7.2, leading=9.5, textColor=GRI),
    "hucre": _st("c", fontSize=7.8, leading=10),
    "hucreB": _st("cb", fontName="DVB", fontSize=7.8, leading=10),
    "madde": _st("m", fontSize=8.2, leading=11, leftIndent=8, bulletIndent=0),
}

# =====================================================================
# YARDIMCILAR
# =====================================================================
def sayi(x):
    try:
        x = float(x)
        return None if (math.isnan(x) or math.isinf(x)) else x
    except Exception:
        return None

def bol(a, b):
    a, b = sayi(a), sayi(b)
    return a / b if a is not None and b not in (None, 0) else None

def buyume(a, b):
    a, b = sayi(a), sayi(b)
    return a / b - 1 if a is not None and b is not None and b > 0 else None

def cagr(son, ilk_, yil):
    son, ilk_ = sayi(son), sayi(ilk_)
    if son is None or ilk_ is None or ilk_ <= 0 or son <= 0 or yil <= 0:
        return None
    return (son / ilk_) ** (1 / yil) - 1

def reel(g):
    return None if g is None else (1 + g) / (1 + PARAM["ENFLASYON"]) - 1

def _tr(s):
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def ond(x, d=2):
    x = sayi(x)
    return "–" if x is None else _tr(f"{x:,.{d}f}")

def tl(x, d=2):
    x = sayi(x)
    if x is None:
        return "–"
    for e, ek in ((1e12, " tr"), (1e9, " mr"), (1e6, " mn")):
        if abs(x) >= e:
            return _tr(f"{x/e:,.1f}") + ek
    return _tr(f"{x:,.{d}f}")

def yz(x, d=1):
    x = sayi(x)
    return "–" if x is None else ("-" if x < 0 else "") + "%" + _tr(f"{abs(x)*100:,.{d}f}")

def kat(x):
    x = sayi(x)
    return "–" if x is None else _tr(f"{x:,.1f}") + "x"

def puan(x, esik, ters=False):
    x = sayi(x)
    if x is None:
        return None
    p = 1 + sum(x > e for e in esik)
    return float(6 - p if ters else p)

def ort(l):
    l = [x for x in l if x is not None]
    return round(float(np.mean(l)), 2) if l else None

def satir(df, *adlar):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    for a in adlar:
        if a in df.index:
            s = pd.to_numeric(df.loc[a], errors="coerce")
            s = s[~s.index.duplicated()].dropna()
            if len(s):
                return s.sort_index(ascending=False)
    return None

def deger(s, i=0):
    return sayi(s.iloc[i]) if s is not None and len(s) > i else None

def ttm(q, a, *adlar):
    """Son 4 çeyrek toplamı; yoksa son yıllık değer."""
    s = satir(q, *adlar)
    if s is not None and len(s) >= 4:
        return float(s.iloc[:4].sum())
    return deger(satir(a, *adlar))

def son_bilanco(q, a, *adlar):
    v = deger(satir(q, *adlar))
    return v if v is not None else deger(satir(a, *adlar))

def _naive(x):
    x = x.copy()
    try:
        x.index = x.index.tz_localize(None)
    except Exception:
        pass
    return x

# =====================================================================
# VERİ
# =====================================================================
def veri_cek(kod, hafif=False):
    import yfinance as yf
    kod = kod.upper().replace(".IS", "").strip()
    t = yf.Ticker(kod + ".IS")
    hist = t.history(period="2y" if hafif else "5y", auto_adjust=False)
    if hist is None or hist.empty:
        raise ValueError(f"{kod} için fiyat verisi bulunamadı. Kodu kontrol edin.")
    def g(attr):
        try:
            return getattr(t, attr)
        except Exception:
            return pd.DataFrame()
    try:
        info = t.info or {}
    except Exception:
        info = {}
    d = {"kod": kod, "info": info, "hist": _naive(hist),
         "gelir": g("income_stmt"), "bilanco": g("balance_sheet"), "nakit": g("cashflow"),
         "q_gelir": g("quarterly_income_stmt"), "q_bilanco": g("quarterly_balance_sheet"),
         "q_nakit": g("quarterly_cashflow")}
    try:
        d["temettu"] = _naive(t.dividends) if not hafif else pd.Series(dtype=float)
    except Exception:
        d["temettu"] = pd.Series(dtype=float)
    d["kaynak"], d["kaynak_hata"] = "Yahoo Finance", None
    # 1) Ana kaynak: İş Yatırım (KAP finansalları, TL)
    try:
        import bist_isyatirim as ISY
        isy = ISY.finansallar(kod)
        # Ölçek kontrolü: Yahoo ile karşılaştır (binlik/milyonluk birim farkına karşı)
        y_var = None
        try:
            yb = d["q_bilanco"] if isinstance(d["q_bilanco"], pd.DataFrame) and not d["q_bilanco"].empty else d["bilanco"]
            y_var = float(pd.to_numeric(yb.loc["Total Assets"]).dropna().iloc[0])
            fpb = (info.get("financialCurrency") or DOVIZ_RAPORLAYAN.get(kod, "TRY")).upper()
            if fpb != "TRY":
                y_var = None  # dövizli Yahoo verisiyle ölçek kıyası yapılmaz
        except Exception:
            y_var = None
        i_b = isy["q_bilanco"] if not isy["q_bilanco"].empty else isy["bilanco"]
        i_var = float(pd.to_numeric(i_b.loc["Total Assets"]).dropna().iloc[0])
        olcek = 1.0
        if y_var and i_var and y_var > 0 and i_var > 0:
            us = round(math.log10(y_var / i_var))
            if abs(us) >= 2:
                olcek = 10.0 ** us
        for k in ("gelir", "bilanco", "nakit", "q_gelir", "q_bilanco", "q_nakit"):
            df = isy[k]
            if olcek != 1.0 and not df.empty:
                df = df.copy(); m_ = [i != "Ordinary Shares Number" for i in df.index]
                df.loc[m_] = df.loc[m_] * olcek
            d[k] = df
        d["kaynak"] = f"İş Yatırım (KAP finansalları, {isy['grup']})" + (f", ölçek ×{olcek:g}" if olcek != 1.0 else "")
        d["kur_notu"] = None
        return d
    except Exception as ex:
        d["kaynak_hata"] = f"İş Yatırım verisi alınamadı ({type(ex).__name__}: {str(ex)[:1500]}); Yahoo kullanıldı."
    # 2) Yedek: Yahoo (gerekirse kur çevrimi)
    fin_pb = (info.get("financialCurrency") or DOVIZ_RAPORLAYAN.get(kod, "")).upper()
    pb = (info.get("currency") or "TRY").upper()
    d["kur_notu"] = None
    if fin_pb and fin_pb != pb:
        try:
            fx = _naive(yf.Ticker(f"{fin_pb}{pb}=X").history(period="10y"))["Close"]
            kur_cevir(d, fx)
            d["kur_notu"] = f"Finansallar {fin_pb} raporlanmış; dönem sonu {fin_pb}/{pb} kuruyla TL'ye çevrildi."
        except Exception as ex:
            d["kur_notu"] = f"UYARI: Finansallar {fin_pb} cinsinden, kur çevrimi yapılamadı ({ex}); oranlar hatalı olabilir."
    return d

_KUR_DISI = ("Share", "Shares", "Tax Rate", "Ordinary Shares Number")

def kur_cevir(d, fx):
    """Finansallar farklı para biriminde raporlanmışsa (örn. THYAO: USD) her dönemi
    o dönem sonu kuruyla TL'ye çevirir. Hisse adedi ve oran satırları çevrilmez."""
    fx = fx.dropna().sort_index()
    if fx.empty:
        return d
    def oran(t):
        s = fx[fx.index <= t]
        return float(s.iloc[-1]) if len(s) else float(fx.iloc[0])
    for k in ("gelir", "bilanco", "nakit", "q_gelir", "q_bilanco", "q_nakit"):
        df = d.get(k)
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            continue
        df = df.copy()
        maske = [not any(x in str(i) for x in _KUR_DISI) for i in df.index]
        for c in df.columns:
            try:
                r = oran(pd.Timestamp(c).tz_localize(None) if pd.Timestamp(c).tzinfo else pd.Timestamp(c))
            except Exception:
                continue
            df.loc[maske, c] = pd.to_numeric(df.loc[maske, c], errors="coerce") * r
        d[k] = df
    return d

def endeks_cek():
    import yfinance as yf
    h = yf.Ticker("XU100.IS").history(period="5y")
    return _naive(h) if h is not None and not h.empty else None

# =====================================================================
# METRİKLER
# =====================================================================
def finansal_mi(info, kod):
    s = (info.get("sector") or "") + " " + (info.get("industry") or "")
    if any(k in s for k in ("Bank", "Insurance", "Capital Markets", "Credit Services")):
        return True
    return kod in SEKTOR_GRUPLARI["Bankacılık"] + SEKTOR_GRUPLARI["Sigorta"]

def metrikler(d, endeks=None):
    info, h = d["info"], d["hist"]
    A, B, N = d["gelir"], d["bilanco"], d["nakit"]
    qA, qB, qN = d.get("q_gelir"), d.get("q_bilanco"), d.get("q_nakit")
    m = {"kod": d["kod"], "ad": BV.ad(d["kod"]) or info.get("longName") or info.get("shortName") or d["kod"],
         "sektor": info.get("sector") or "–", "sanayi": info.get("industry") or "–"}
    m["finansal"] = finansal_mi(info, d["kod"]); m["kur_notu"] = d.get("kur_notu")
    m["kaynak"] = d.get("kaynak", "Yahoo Finance"); m["kaynak_hata"] = d.get("kaynak_hata")
    kap = h["Close"].dropna(); p = float(kap.iloc[-1]); m["fiyat"] = p
    m["tarih"] = kap.index[-1]

    # --- TTM gelir/nakit ---
    T = {}
    T["ciro"] = ttm(qA, A, "Total Revenue", "Operating Revenue")
    T["brut"] = ttm(qA, A, "Gross Profit")
    T["ebit"] = ttm(qA, A, "Operating Income", "EBIT")
    T["favok"] = ttm(qA, A, "EBITDA", "Normalized EBITDA")
    T["net"] = ttm(qA, A, "Net Income Common Stockholders", "Net Income")
    T["faiz"] = abs(ttm(qA, A, "Interest Expense") or 0) or None
    T["vergi_once"] = ttm(qA, A, "Pretax Income")
    T["vergi"] = ttm(qA, A, "Tax Provision")
    T["isl_na"] = ttm(qN, N, "Operating Cash Flow")
    T["capex"] = ttm(qN, N, "Capital Expenditure")
    T["sna"] = ttm(qN, N, "Free Cash Flow")
    if T["sna"] is None and T["isl_na"] is not None and T["capex"] is not None:
        T["sna"] = T["isl_na"] + T["capex"]
    T["tem_odenen"] = ttm(qN, N, "Cash Dividends Paid", "Common Stock Dividend Paid")
    m["T"] = T

    # --- Son bilanço ---
    K = {}
    K["varlik"] = son_bilanco(qB, B, "Total Assets")
    K["yukum"] = son_bilanco(qB, B, "Total Liabilities Net Minority Interest")
    K["ozk"] = son_bilanco(qB, B, "Stockholders Equity", "Common Stock Equity")
    K["azinlik"] = son_bilanco(qB, B, "Minority Interest") or 0
    K["borc"] = son_bilanco(qB, B, "Total Debt") or 0
    K["nakit"] = son_bilanco(qB, B, "Cash Cash Equivalents And Short Term Investments",
                             "Cash And Cash Equivalents") or 0
    K["don_var"] = son_bilanco(qB, B, "Current Assets")
    K["kvy"] = son_bilanco(qB, B, "Current Liabilities")
    K["stok"] = son_bilanco(qB, B, "Inventory") or 0
    K["dag_kar"] = son_bilanco(qB, B, "Retained Earnings")
    K["isl_serm"] = son_bilanco(qB, B, "Working Capital")
    if K["isl_serm"] is None and K["don_var"] is not None and K["kvy"] is not None:
        K["isl_serm"] = K["don_var"] - K["kvy"]
    m["K"] = K

    hs = sayi(info.get("sharesOutstanding")) or son_bilanco(qB, B, "Ordinary Shares Number", "Share Issued")
    m["hisse"] = hs
    m["piy_deg"] = p * hs if hs else sayi(info.get("marketCap"))
    m["net_borc"] = K["borc"] - K["nakit"]
    m["fd"] = m["piy_deg"] + m["net_borc"] + K["azinlik"] if m["piy_deg"] else None
    m["hbk"] = bol(T["net"], hs); m["hbdd"] = bol(K["ozk"], hs)
    vergi_oran = bol(T["vergi"], T["vergi_once"])
    m["efektif_vergi"] = min(max(vergi_oran, 0), 0.4) if vergi_oran is not None else PARAM["VERGI"]

    # --- Çarpanlar ---
    pos = lambda x: x if x is not None and x > 0 else None
    m["fk"] = bol(m["piy_deg"], pos(T["net"]))
    m["pddd"] = bol(m["piy_deg"], pos(K["ozk"]))
    m["fd_favok"] = None if m["finansal"] else bol(m["fd"], pos(T["favok"]))
    m["fd_satis"] = None if m["finansal"] else bol(m["fd"], pos(T["ciro"]))
    m["f_satis"] = bol(m["piy_deg"], pos(T["ciro"]))
    m["f_sna"] = bol(m["piy_deg"], pos(T["sna"]))

    # --- Kârlılık ---
    m["brut_marj"] = bol(T["brut"], T["ciro"])
    m["favok_marj"] = None if m["finansal"] else bol(T["favok"], T["ciro"])
    m["faal_marj"] = bol(T["ebit"], T["ciro"])
    m["net_marj"] = bol(T["net"], T["ciro"])
    m["roe"] = bol(T["net"], K["ozk"]); m["roa"] = bol(T["net"], K["varlik"])
    yat_serm = (K["ozk"] or 0) + K["borc"] - K["nakit"]
    m["roic"] = None if m["finansal"] else bol((T["ebit"] or 0) * (1 - m["efektif_vergi"]) if T["ebit"] else None,
                                               yat_serm if yat_serm > 0 else None)
    # DuPont
    m["varlik_devir"] = bol(T["ciro"], K["varlik"]); m["kaldirac"] = bol(K["varlik"], K["ozk"])

    # --- Yıllık seriler ---
    S = {
        "Hasılat": satir(A, "Total Revenue", "Operating Revenue"),
        "Brüt Kâr": satir(A, "Gross Profit"),
        "Faaliyet Kârı": satir(A, "Operating Income", "EBIT"),
        "FAVÖK": satir(A, "EBITDA", "Normalized EBITDA"),
        "Net Kâr": satir(A, "Net Income Common Stockholders", "Net Income"),
        "Toplam Varlıklar": satir(B, "Total Assets"),
        "Nakit ve Benzerleri": satir(B, "Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"),
        "Toplam Borç": satir(B, "Total Debt"),
        "Özkaynaklar": satir(B, "Stockholders Equity", "Common Stock Equity"),
        "İşletme Nakit Akışı": satir(N, "Operating Cash Flow"),
        "Yatırım Harcamaları": satir(N, "Capital Expenditure"),
        "Serbest Nakit Akışı": satir(N, "Free Cash Flow"),
        "Ödenen Temettü": satir(N, "Cash Dividends Paid", "Common Stock Dividend Paid"),
    }
    m["S"] = S
    ciro, net = S["Hasılat"], S["Net Kâr"]
    m["ciro_b"] = buyume(deger(ciro), deger(ciro, 1))
    m["net_b"] = buyume(deger(net), deger(net, 1))
    n = len(ciro) - 1 if ciro is not None else 0
    m["ciro_cagr"] = cagr(deger(ciro), deger(ciro, n), n) if n >= 2 else None
    nn = len(net) - 1 if net is not None else 0
    m["net_cagr"] = cagr(deger(net), deger(net, nn), nn) if nn >= 2 else None
    qc, qn = satir(qA, "Total Revenue", "Operating Revenue"), satir(qA, "Net Income Common Stockholders", "Net Income")
    m["q_ciro"], m["q_net"] = qc, qn
    m["ceyrek_ciro_b"] = buyume(deger(qc), deger(qc, 4))
    m["ceyrek_net_b"] = buyume(deger(qn), deger(qn, 4))
    m["fk_buyume_peg"] = bol(m["fk"], m["net_cagr"] * 100) if m["net_cagr"] and m["net_cagr"] > 0 else None

    # --- Finansal güç ---
    m["borc_ozk"] = bol(K["borc"], K["ozk"])
    m["nb_favok"] = None if m["finansal"] else bol(m["net_borc"], pos(T["favok"]))
    m["cari"] = None if m["finansal"] else bol(K["don_var"], K["kvy"])
    m["likidite"] = None if m["finansal"] or K["don_var"] is None else bol(K["don_var"] - K["stok"], K["kvy"])
    m["faiz_karsilama"] = None if m["finansal"] else bol(T["ebit"], T["faiz"])

    # --- Nakit akışı kalitesi ---
    m["na_kalite"] = bol(T["isl_na"], T["net"]) if T["net"] and T["net"] > 0 else None
    m["sna_marj"] = bol(T["sna"], T["ciro"])
    m["sna_verim"] = bol(T["sna"], m["piy_deg"])
    m["capex_satis"] = bol(abs(T["capex"]) if T["capex"] else None, T["ciro"])

    # --- Piotroski F-Skoru ---
    m["piotroski"], m["piotroski_detay"] = piotroski(A, B, N) if not m["finansal"] else (None, [])
    # --- Altman Z'' (gelişmekte olan piyasa) ---
    m["altman"] = None
    if not m["finansal"] and K["varlik"]:
        x1 = bol(K["isl_serm"], K["varlik"]); x2 = bol(K["dag_kar"], K["varlik"])
        x3 = bol(T["ebit"], K["varlik"]); x4 = bol(K["ozk"], K["yukum"])
        if None not in (x1, x2, x3, x4):
            m["altman"] = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4

    # --- Temettü ---
    tm = d.get("temettu")
    m["temettu_yillik"] = None; m["dps_ttm"] = None
    if tm is not None and len(tm):
        m["temettu_yillik"] = tm.groupby(tm.index.year).sum()
        son = tm[tm.index > (m["tarih"] - pd.Timedelta(days=365))]
        m["dps_ttm"] = float(son.sum()) if len(son) else 0.0
    m["temettu_verim"] = bol(m["dps_ttm"], p) if m["dps_ttm"] else (bol(abs(T["tem_odenen"]), m["piy_deg"]) if T["tem_odenen"] else None)
    m["dagitim_orani"] = bol(abs(T["tem_odenen"]) if T["tem_odenen"] else (m["dps_ttm"] * hs if m["dps_ttm"] and hs else None), pos(T["net"]))

    # --- Banka göstergeleri ---
    m["banka"] = None
    if m["finansal"]:
        nii = ttm(qA, A, "Net Interest Income")
        ii = ttm(qA, A, "Interest Income", "Interest Income After Provision For Loan Loss")
        prov = ttm(qA, A, "Credit Losses Provision", "Provision For Doubtful Accounts", "Provision For Loan Losses")
        gider = ttm(qA, A, "Non Interest Expense", "Selling General And Administration", "Operating Expense")
        gelir = ttm(qA, A, "Total Revenue", "Operating Revenue")
        krediler = son_bilanco(qB, B, "Net Loan", "Gross Loan", "Loans Receivable", "Loans And Advances")
        mevduat = son_bilanco(qB, B, "Total Deposits", "Deposits", "Customer Accounts", "Current Deposits")
        va = satir(qB, "Total Assets"); va_once = deger(va, 4) if va is not None and len(va) > 4 else deger(satir(B, "Total Assets"), 1)
        ort_varlik = ((K["varlik"] or 0) + (va_once or K["varlik"] or 0)) / 2 or None
        m["banka"] = {
            "nim": bol(nii, ort_varlik), "faiz_geliri_payi": bol(nii, gelir),
            "risk_maliyeti": bol(abs(prov) if prov else None, krediler),
            "gider_gelir": bol(abs(gider) if gider else None, gelir),
            "kredi_mevduat": bol(krediler, mevduat),
            "ozk_varlik": bol(K["ozk"], K["varlik"]),
            "kredi_varlik": bol(krediler, K["varlik"]),
        }

    # --- Veri kalitesi ---
    def son_tarih(df):
        try:
            return max(pd.Timestamp(c) for c in df.columns) if isinstance(df, pd.DataFrame) and not df.empty else None
        except Exception:
            return None
    sb = son_tarih(qB) or son_tarih(B)
    anahtar = {"Hasılat": T["ciro"], "Net kâr": T["net"], "Özkaynak": K["ozk"], "Toplam varlık": K["varlik"],
               "Hisse sayısı": hs}
    if not m["finansal"]:
        anahtar["İşletme nakit akışı"] = T["isl_na"]  # bankalarda nakit akış tablosu analizde kullanılmaz
    if not m["finansal"]:
        anahtar.update({"FAVÖK": T["favok"], "Serbest nakit akışı": T["sna"]})
    eksik = [k for k, v in anahtar.items() if v is None]
    qs = satir(qA, "Total Revenue", "Operating Revenue", "Net Income")
    gun = (m["tarih"] - sb).days if sb is not None else None
    m["veri"] = {"fiyat_tarihi": m["tarih"], "son_donem": sb, "gun": gun,
                 "ceyrek": len(qs) if qs is not None else 0,
                 "yil": len(satir(A, "Total Revenue", "Operating Revenue", "Net Income")) if satir(A, "Total Revenue", "Operating Revenue", "Net Income") is not None else 0,
                 "eksik": eksik}
    puan_v = 100 - 12 * len(eksik) - (15 if gun is not None and gun > 200 else 0) - (10 if m["veri"]["ceyrek"] < 4 else 0)
    m["veri"]["puan"] = max(puan_v, 0)

    # --- Fiyat, risk, teknik ---
    m.update(fiyat_analizi(h, endeks))
    m["hedef_analist"] = sayi(info.get("targetMeanPrice"))
    m["hedef_yuksek"] = sayi(info.get("targetHighPrice")); m["hedef_dusuk"] = sayi(info.get("targetLowPrice"))
    m["analist_sayi"] = info.get("numberOfAnalystOpinions")
    return m

def piotroski(A, B, N):
    ni, ta = satir(A, "Net Income Common Stockholders", "Net Income"), satir(B, "Total Assets")
    cfo = satir(N, "Operating Cash Flow"); debt = satir(B, "Total Debt", "Long Term Debt")
    ca, cl = satir(B, "Current Assets"), satir(B, "Current Liabilities")
    sh = satir(B, "Ordinary Shares Number", "Share Issued")
    gp, rev = satir(A, "Gross Profit"), satir(A, "Total Revenue", "Operating Revenue")
    v = lambda s, i: deger(s, i)
    def kr(f):
        try:
            r = f(); return None if r is None else bool(r)
        except Exception:
            return None
    roa0, roa1 = bol(v(ni, 0), v(ta, 0)), bol(v(ni, 1), v(ta, 1))
    lev0, lev1 = bol(v(debt, 0), v(ta, 0)), bol(v(debt, 1), v(ta, 1))
    cr0, cr1 = bol(v(ca, 0), v(cl, 0)), bol(v(ca, 1), v(cl, 1))
    gm0, gm1 = bol(v(gp, 0), v(rev, 0)), bol(v(gp, 1), v(rev, 1))
    at0, at1 = bol(v(rev, 0), v(ta, 0)), bol(v(rev, 1), v(ta, 1))
    nz = lambda *a: None if any(x is None for x in a) else True
    kriter = [
        ("Net kâr pozitif", kr(lambda: v(ni, 0) > 0 if v(ni, 0) is not None else None)),
        ("İşletme nakit akışı pozitif", kr(lambda: v(cfo, 0) > 0 if v(cfo, 0) is not None else None)),
        ("Aktif kârlılığı (ROA) arttı", kr(lambda: roa0 > roa1 if nz(roa0, roa1) else None)),
        ("İşletme NA > Net kâr (kâr kalitesi)", kr(lambda: v(cfo, 0) > v(ni, 0) if nz(v(cfo, 0), v(ni, 0)) else None)),
        ("Borç/Varlık oranı azaldı", kr(lambda: lev0 < lev1 if nz(lev0, lev1) else None)),
        ("Cari oran arttı", kr(lambda: cr0 > cr1 if nz(cr0, cr1) else None)),
        ("Hisse sayısı artmadı (sulandırma yok)", kr(lambda: v(sh, 0) <= v(sh, 1) * 1.001 if nz(v(sh, 0), v(sh, 1)) else None)),
        ("Brüt marj arttı", kr(lambda: gm0 > gm1 if nz(gm0, gm1) else None)),
        ("Varlık devir hızı arttı", kr(lambda: at0 > at1 if nz(at0, at1) else None)),
    ]
    gecerli = [k for k in kriter if k[1] is not None]
    if len(gecerli) < 5:
        return None, kriter
    skor = sum(1 for k in gecerli if k[1]) * 9 / len(gecerli)
    return round(skor, 1), kriter

def rsi(s, n=14):
    d = s.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))

def fiyat_analizi(h, endeks):
    k = h["Close"].dropna(); p = float(k.iloc[-1]); son = k.index[-1]; o = {}
    def ret(gun):
        t0 = son - pd.Timedelta(days=gun); s = k[k.index <= t0]
        return p / float(s.iloc[-1]) - 1 if len(s) else None
    o["r"] = {"1A": ret(30), "3A": ret(91), "6A": ret(182), "1Y": ret(365), "3Y": ret(365*3)}
    ybb = k[k.index < pd.Timestamp(son.year, 1, 1)]
    o["r"]["YBB"] = p / float(ybb.iloc[-1]) - 1 if len(ybb) else None
    o["r_endeks"] = {}
    if endeks is not None:
        e = endeks["Close"].dropna(); ep = float(e.iloc[-1]); es = e.index[-1]
        for a, gun in (("1A", 30), ("3A", 91), ("6A", 182), ("1Y", 365), ("3Y", 365*3)):
            s = e[e.index <= es - pd.Timedelta(days=gun)]
            o["r_endeks"][a] = ep / float(s.iloc[-1]) - 1 if len(s) else None
        yb = e[e.index < pd.Timestamp(es.year, 1, 1)]
        o["r_endeks"]["YBB"] = ep / float(yb.iloc[-1]) - 1 if len(yb) else None
        hw = k.resample("W-FRI").last().pct_change(); ew = e.resample("W-FRI").last().pct_change()
        j = pd.concat([hw, ew], axis=1, join="inner").dropna().iloc[-104:]
        o["beta"] = float(j.cov().iloc[0, 1] / j.iloc[:, 1].var()) if len(j) > 30 else None
        o["korelasyon"] = float(j.corr().iloc[0, 1]) if len(j) > 30 else None
    else:
        o["beta"] = o["korelasyon"] = None
    g = k.pct_change().dropna()
    o["vol"] = float(g.iloc[-252:].std() * math.sqrt(252))
    y = k.iloc[-252*3:]; o["max_dd"] = float((y / y.cummax() - 1).min())
    r1 = o["r"]["1Y"]
    o["sharpe"] = (r1 - PARAM["RF"]) / o["vol"] if r1 is not None and o["vol"] else None
    o["zirve52"] = float(k.iloc[-252:].max()); o["dip52"] = float(k.iloc[-252:].min())
    for n in (20, 50, 200):
        o[f"ma{n}"] = float(k.rolling(n).mean().iloc[-1]) if len(k) >= n else None
    o["rsi"] = float(rsi(k).iloc[-1])
    e12, e26 = k.ewm(span=12).mean(), k.ewm(span=26).mean(); macd = e12 - e26; sig = macd.ewm(span=9).mean()
    o["macd"], o["macd_sinyal"] = float(macd.iloc[-1]), float(sig.iloc[-1])
    ma20, sd20 = k.rolling(20).mean(), k.rolling(20).std()
    o["boll_b"] = float(((k - (ma20 - 2*sd20)) / (4*sd20)).iloc[-1])
    if "Volume" in h:
        v = h["Volume"].fillna(0)
        o["hacim_oran"] = bol(v.iloc[-20:].mean(), v.iloc[-90:].mean())
        o["ort_islem_tl"] = float((v * k).iloc[-20:].mean())
    else:
        o["hacim_oran"] = o["ort_islem_tl"] = None
    # Teknik sinyaller
    sin = []
    def ekle(ad, deger_, durum):
        sin.append((ad, deger_, durum))
    for n in (20, 50, 200):
        ma = o[f"ma{n}"]
        if ma:
            ekle(f"Fiyat / {n} günlük ort.", tl(ma), "Pozitif" if p > ma else "Negatif")
    if o["ma50"] and o["ma200"]:
        ekle("50G / 200G kesişimi", "Altın kesişim" if o["ma50"] > o["ma200"] else "Ölüm kesişimi",
             "Pozitif" if o["ma50"] > o["ma200"] else "Negatif")
    ekle("RSI (14)", _tr(f"{o['rsi']:.1f}"),
         "Aşırı alım" if o["rsi"] > 70 else "Aşırı satım" if o["rsi"] < 30 else "Pozitif" if o["rsi"] > 50 else "Negatif")
    ekle("MACD (12,26,9)", _tr(f"{o['macd']:.2f}"), "Pozitif" if o["macd"] > o["macd_sinyal"] else "Negatif")
    ekle("Bollinger %B", _tr(f"{o['boll_b']:.2f}"),
         "Üst banda yakın" if o["boll_b"] > 0.9 else "Alt banda yakın" if o["boll_b"] < 0.1 else "Nötr")
    if o["hacim_oran"]:
        ekle("Hacim (20G / 90G ort.)", kat(o["hacim_oran"]), "Artan ilgi" if o["hacim_oran"] > 1.2 else
             "Azalan ilgi" if o["hacim_oran"] < 0.8 else "Nötr")
    o["teknik"] = sin
    poz = sum(1 for s in sin if s[2] in ("Pozitif", "Aşırı satım")); neg = sum(1 for s in sin if s[2] in ("Negatif", "Aşırı alım"))
    fark = poz - neg
    o["teknik_ozet"] = ("GÜÇLÜ POZİTİF" if fark >= 4 else "POZİTİF" if fark >= 2 else
                        "GÜÇLÜ NEGATİF" if fark <= -4 else "NEGATİF" if fark <= -2 else "NÖTR")
    return o

# =====================================================================
# DEĞERLEME
# =====================================================================
def wacc_hesap(m):
    beta = m.get("beta"); beta = min(max(beta, 0.5), 2.0) if beta else 1.0
    ke = PARAM["RF"] + beta * PARAM["ERP"]
    kd_brut = bol(m["T"]["faiz"], m["K"]["borc"]) if m["K"]["borc"] else None
    kd_brut = min(max(kd_brut, PARAM["RF"]), PARAM["RF"] + 0.15) if kd_brut else PARAM["RF"] + 0.05
    kd = kd_brut * (1 - PARAM["VERGI"])
    E, D = m["piy_deg"] or 0, m["K"]["borc"] or 0
    we = E / (E + D) if E + D > 0 else 1
    return {"beta": beta, "ke": ke, "kd_brut": kd_brut, "kd": kd, "we": we, "wd": 1 - we,
            "wacc": we * ke + (1 - we) * kd}

def dcf(m, w, g0=None, marj=None, wacc=None, gT=None):
    S = m["S"]; ciro = m["T"]["ciro"]
    if not ciro or not m["hisse"] or m["finansal"]:
        return None
    if marj is None:
        r, f = S["Hasılat"], S["Serbest Nakit Akışı"]
        marjlar = []
        if r is not None and f is not None:
            for i in r.index[:3]:
                if i in f.index and r[i] > 0:
                    marjlar.append(f[i] / r[i])
        if m["sna_marj"] is not None:
            marjlar.append(m["sna_marj"])
        marj = float(np.median(marjlar)) if marjlar else None
        normalize = False
        if marj is None or marj <= 0:
            if m["favok_marj"] and m["favok_marj"] > 0:
                marj = m["favok_marj"] * 0.30; normalize = True
            else:
                return None
        marj = min(max(marj, 0.01), 0.35)
    else:
        normalize = False
    gT = PARAM["TERMINAL_G"] if gT is None else gT
    if g0 is None:
        g0 = m["ciro_cagr"] if m["ciro_cagr"] is not None else (m["ciro_b"] or PARAM["ENFLASYON"])
        g0 = min(max(g0, gT), 0.80)
    wacc = w["wacc"] if wacc is None else wacc
    if wacc <= gT + 0.01:
        return None
    n = PARAM["DCF_YIL"]; satir_ = []; pv = 0; r = ciro
    for t in range(1, n + 1):
        g = g0 - (g0 - gT) * t / n
        r = r * (1 + g); f = r * marj; df = (1 + wacc) ** t
        pv += f / df; satir_.append((dt.date.today().year + t, g, r, f, f / df))
    tv = satir_[-1][3] * (1 + gT) / (wacc - gT); pv_tv = tv / (1 + wacc) ** n
    fd = pv + pv_tv
    ozk = fd - m["net_borc"] - m["K"]["azinlik"]
    return {"deger": ozk / m["hisse"], "fd": fd, "pv_na": pv, "pv_tv": pv_tv, "tv_pay": pv_tv / fd,
            "g0": g0, "gT": gT, "marj": marj, "wacc": wacc, "projeksiyon": satir_, "normalize": normalize}

def emsal_istatistik(emsaller, alan, alt, ust):
    v = [e.get(alan) for e in emsaller if e.get(alan) is not None and alt < e.get(alan) < ust]
    if len(v) < 2:
        return None
    return {"med": float(np.median(v)), "q1": float(np.percentile(v, 25)), "q3": float(np.percentile(v, 75)), "n": len(v)}

def nav_hesapla(kod, pd_fn):
    """Holding net aktif değeri: halka açık iştiraklerin piyasa değeri × holding payı."""
    paylar = BV.HOLDING_PAYLARI.get(kod)
    if not paylar:
        return None
    kalem = []
    for ist, pay in paylar.items():
        try:
            mc = pd_fn(ist)
        except Exception:
            mc = None
        kalem.append({"kod": ist, "ad": BV.ad(ist) or ist, "pay": pay, "piy_deg": mc,
                      "deger": mc * pay if mc else None})
    top = sum(k["deger"] for k in kalem if k["deger"])
    if not top:
        return None
    for k in kalem:
        k["oran"] = k["deger"] / top if k["deger"] else None
    return {"kalemler": kalem, "toplam": top, "hedef_iskonto": PARAM.get("HOLDING_ISKONTO", {}).get(kod, BV.HOLDING_ISKONTO.get(kod, 0.35))}

def degerleme(m, emsaller, nav=None):
    p = m["fiyat"]; hs = m["hisse"]; w = wacc_hesap(m); m["wacc"] = w
    Y = []  # (yöntem, değer, düşük, yüksek, ağırlık, not)
    fin = m["finansal"]
    holding = nav is not None
    m["nav"] = nav
    if holding and hs:
        nav["iskonto"] = 1 - m["piy_deg"] / nav["toplam"] if m["piy_deg"] else None
        hi = nav["hedef_iskonto"]
        v = nav["toplam"] * (1 - hi) / hs
        Y.append(["Net Aktif Değer (NAV)", v, nav["toplam"] * (1 - min(hi + 0.10, 0.9)) / hs, nav["toplam"] * (1 - max(hi - 0.10, 0)) / hs,
                  0.55, f"Halka açık iştirakler {tl(nav['toplam'])} TL, hedef iskonto {yz(hi, 0)} (mevcut {yz(nav['iskonto'], 0)})"])
    # 1) DCF
    m["dcf"] = None; m["senaryo"] = None; m["duyarlilik"] = None
    if not fin and not holding:
        b = dcf(m, w)
        if b:
            m["dcf"] = b
            ayi = dcf(m, w, g0=max(b["g0"] * 0.6, b["gT"]), marj=b["marj"] * 0.8, wacc=b["wacc"] + 0.02)
            boga = dcf(m, w, g0=min(b["g0"] * 1.3, 0.9), marj=b["marj"] * 1.15, wacc=b["wacc"] - 0.02)
            m["senaryo"] = {"Kötümser": ayi, "Baz": b, "İyimser": boga}
            wl = [b["wacc"] + x for x in (-0.04, -0.02, 0, 0.02, 0.04)]
            gl = [b["gT"] + x for x in (-0.04, -0.02, 0, 0.02, 0.04)]
            m["duyarlilik"] = (wl, gl, [[(dcf(m, w, g0=b["g0"], marj=b["marj"], wacc=ww, gT=gg) or {}).get("deger")
                                       for gg in gl] for ww in wl])
            Y.append(["İNA (DCF) – FCFF", b["deger"], ayi["deger"] if ayi else None, boga["deger"] if boga else None, 0.30,
                      f"AOSM {yz(b['wacc'])}, uç büyüme {yz(b['gT'])}" + (" (normalize marj)" if b["normalize"] else "")])
    # 2) Emsal çarpanları
    fk = emsal_istatistik(emsaller, "fk", 0, 80)
    pd_ = emsal_istatistik(emsaller, "pddd", 0, 30)
    ff = emsal_istatistik(emsaller, "fd_favok", 0, 40)
    m["emsal_stat"] = {"fk": fk, "pddd": pd_, "fd_favok": ff}
    if fk and m["hbk"] and m["hbk"] > 0:
        Y.append(["Emsal F/K", fk["med"] * m["hbk"], fk["q1"] * m["hbk"], fk["q3"] * m["hbk"], 0.20 if fin else 0.15,
                  f"Medyan F/K {kat(fk['med'])} (n={fk['n']})"])
    if ff and m["T"]["favok"] and m["T"]["favok"] > 0 and hs and not holding:
        cev = lambda x: (x * m["T"]["favok"] - m["net_borc"] - m["K"]["azinlik"]) / hs
        Y.append(["Emsal FD/FAVÖK", cev(ff["med"]), cev(ff["q1"]), cev(ff["q3"]), 0.20,
                  f"Medyan FD/FAVÖK {kat(ff['med'])} (n={ff['n']})"])
    if pd_ and m["hbdd"] and m["hbdd"] > 0:
        Y.append(["Emsal PD/DD", pd_["med"] * m["hbdd"], pd_["q1"] * m["hbdd"], pd_["q3"] * m["hbdd"], 0.20 if fin else 0.07,
                  f"Medyan PD/DD {kat(pd_['med'])} (n={pd_['n']})"])
    # 3) Gerekçeli PD/DD (finansal şirketler)
    gT = PARAM["TERMINAL_G"]
    if fin and m["roe"] and m["hbdd"] and w["ke"] > gT + 0.02:
        jpb = (m["roe"] - gT) / (w["ke"] - gT)
        if jpb > 0:
            Y.append(["Gerekçeli PD/DD", jpb * m["hbdd"], None, None, 0.35,
                      f"(ROE {yz(m['roe'])} − g) / (Ke {yz(w['ke'])} − g) = {kat(jpb)}"])
    # 4) Temettü indirgeme
    if m["dps_ttm"] and m["dps_ttm"] > 0 and w["ke"] > gT + 0.02:
        Y.append(["Temettü İndirgeme (Gordon)", m["dps_ttm"] * (1 + gT) / (w["ke"] - gT), None, None, 0.10 if fin else 0.05,
                  f"HBT {tl(m['dps_ttm'])} TL, Ke {yz(w['ke'])}"])
    # 5) Graham
    if m["hbk"] and m["hbdd"] and m["hbk"] > 0 and m["hbdd"] > 0 and not holding:
        Y.append(["Graham Sayısı", math.sqrt(22.5 * m["hbk"] * m["hbdd"]), None, None, 0.03, "√(22,5 × HBK × HBDD)"])
    # 6) Analist
    if m["hedef_analist"]:
        Y.append(["Analist Konsensüs Hedefi", m["hedef_analist"], m["hedef_dusuk"], m["hedef_yuksek"], 0.15,
                  f"{m['analist_sayi'] or '?'} analist"])
    # Temkinli birleştirme: aykırı filtre (fiyatın %40'ı – 2,5 katı), ağırlıklı ortalama ile
    # ağırlıklı medyanın ortalaması, ardından potansiyel sınırı.
    for y in Y:
        y.append(y[1] is not None and (y[0].startswith("Net Aktif") or 0.40 * p <= y[1] <= 2.5 * p))
    gec = [y for y in Y if y[6]]
    tw = sum(y[4] for y in gec)
    m["yontemler"] = Y
    m["sinirlandi"] = False
    if gec:
        ort_ = sum(y[1] * y[4] for y in gec) / tw
        sirali = sorted(gec, key=lambda y: y[1]); kum = 0; med_ = sirali[-1][1]
        for y in sirali:
            kum += y[4]
            if kum >= tw / 2:
                med_ = y[1]; break
        adil = 0.5 * ort_ + 0.5 * med_
        ust, alt = p * (1 + PARAM["MAKS_POTANSIYEL"]), p * (1 + PARAM["MIN_POTANSIYEL"])
        if adil > ust or adil < alt:
            adil = min(max(adil, alt), ust); m["sinirlandi"] = True
        m["adil"] = adil
        vals = [y[1] for y in gec]
        m["adil_dusuk"], m["adil_yuksek"] = min(vals), max(vals)
        cv = np.std(vals) / np.mean(vals) if len(vals) > 1 else 1
        m["guven"] = "YÜKSEK" if len(gec) >= 4 and cv < 0.25 else "ORTA" if len(gec) >= 3 and cv < 0.45 else "DÜŞÜK"
        if m["sinirlandi"] or (m.get("veri") and m["veri"]["puan"] < 60):
            m["guven"] = "DÜŞÜK"
    else:
        m["adil"] = m["adil_dusuk"] = m["adil_yuksek"] = None; m["guven"] = "–"
    m["potansiyel"] = buyume(m["adil"], p) if m["adil"] else None
    pt = m["potansiyel"]
    m["gorus"] = ("–" if pt is None else "DEĞERİNİN ALTINDA" if pt > 0.15 else
                  "DEĞERİNİN ÜZERİNDE" if pt < -0.15 else "MAKUL DEĞERDE")

# =====================================================================
# SAĞLIK SKORU
# =====================================================================
def saglik(m):
    fin = m["finansal"]; es = m.get("emsal_stat", {})
    def oran(x, st):
        return bol(x, st["med"]) if st and x else None
    rel = lambda k: (m["r"].get(k) - m["r_endeks"].get(k)) if m["r"].get(k) is not None and m["r_endeks"].get(k) is not None else None
    enf = PARAM["ENFLASYON"]
    bk = m.get("banka") or {}
    kmd = bk.get("kredi_mevduat")
    D = {
        "Kârlılık": ([("Net faiz marjı (aktif bazlı)", yz(bk.get("nim")), puan(bk.get("nim"), [0.02, 0.035, 0.05, 0.07]))] if fin else []) + [
            ("ROE − enflasyon (reel ROE)", yz(m["roe"] - enf if m["roe"] is not None else None), puan(m["roe"] - enf if m["roe"] is not None else None, [-0.15, 0, 0.1, 0.2])),
            ("Net kâr marjı", yz(m["net_marj"]), puan(m["net_marj"], [0, 0.05, 0.1, 0.2] if not fin else [0, 0.1, 0.2, 0.3])),
            ("Aktif kârlılığı (ROA)", yz(m["roa"]), puan(m["roa"], [0, 0.03, 0.07, 0.12] if not fin else [0, 0.01, 0.02, 0.035])),
        ] + ([] if fin else [
            ("FAVÖK marjı", yz(m["favok_marj"]), puan(m["favok_marj"], [0.05, 0.1, 0.2, 0.3])),
            ("Brüt kâr marjı", yz(m["brut_marj"]), puan(m["brut_marj"], [0.1, 0.2, 0.3, 0.45])),
            ("Yatırılan sermaye getirisi (ROIC)", yz(m["roic"]), puan(m["roic"], [0, 0.1, 0.25, 0.4])),
        ]),
        "Büyüme (reel)": [
            ("Reel hasılat büyümesi (yıllık)", yz(reel(m["ciro_b"])), puan(reel(m["ciro_b"]), [-0.1, 0, 0.1, 0.25])),
            ("Reel net kâr büyümesi (yıllık)", yz(reel(m["net_b"])), puan(reel(m["net_b"]), [-0.2, 0, 0.15, 0.35])),
            ("Reel hasılat YBBO (çok yıllık)", yz(reel(m["ciro_cagr"])), puan(reel(m["ciro_cagr"]), [-0.05, 0, 0.1, 0.2])),
            ("Son çeyrek hasılat (yıllık, reel)", yz(reel(m["ceyrek_ciro_b"])), puan(reel(m["ceyrek_ciro_b"]), [-0.1, 0, 0.1, 0.25])),
        ],
        "Nakit Akışı": [] if fin else [
            ("İşletme NA / Net kâr", kat(m["na_kalite"]), puan(m["na_kalite"], [0.5, 0.8, 1.0, 1.3])),
            ("Serbest nakit akışı marjı", yz(m["sna_marj"]), puan(m["sna_marj"], [-0.02, 0, 0.05, 0.12])),
            ("Serbest nakit akışı verimi", yz(m["sna_verim"]), puan(m["sna_verim"], [-0.02, 0, 0.04, 0.08])),
        ],
        "Finansal Güç": ([
            ("Borç / Özkaynak", kat(m["borc_ozk"]), puan(m["borc_ozk"], [0.3, 0.6, 1.0, 1.8], ters=True)),
            ("Net borç / FAVÖK", kat(m["nb_favok"]), puan(m["nb_favok"], [0, 1, 2, 3.5], ters=True)),
            ("Cari oran", kat(m["cari"]), puan(m["cari"], [0.8, 1.0, 1.3, 1.8])),
            ("Faiz karşılama (FVÖK/Faiz)", kat(m["faiz_karsilama"]), puan(m["faiz_karsilama"], [1, 2, 4, 8])),
            ("Altman Z'' skoru", _tr(f"{m['altman']:.2f}") if m["altman"] is not None else "–", puan(m["altman"], [1.1, 2.0, 2.6, 4.0])),
        ] if not fin else [
            ("Özkaynak / Varlık", yz(bol(m["K"]["ozk"], m["K"]["varlik"])), puan(bol(m["K"]["ozk"], m["K"]["varlik"]), [0.06, 0.08, 0.1, 0.13])),
            ("Risk maliyeti (karşılık / kredi)", yz(bk.get("risk_maliyeti")), puan(bk.get("risk_maliyeti"), [0.005, 0.01, 0.02, 0.035], ters=True)),
            ("Kredi / Mevduat", kat(kmd), puan(abs(kmd - 0.9) if kmd else None, [0.1, 0.2, 0.3, 0.45], ters=True)),
            ("Gider / Gelir", yz(bk.get("gider_gelir")), puan(bk.get("gider_gelir"), [0.35, 0.45, 0.55, 0.7], ters=True)),
        ]) + [("Piotroski F-skoru", f"{_tr(str(m['piotroski']))}/9" if m["piotroski"] is not None else "–", puan(m["piotroski"], [2, 4, 6, 7]))],
        "Fiyat Momentumu": [
            ("1Y getiri – BIST 100 farkı", yz(rel("1Y")), puan(rel("1Y"), [-0.2, -0.05, 0.05, 0.2])),
            ("6A getiri – BIST 100 farkı", yz(rel("6A")), puan(rel("6A"), [-0.15, -0.05, 0.05, 0.15])),
            ("Fiyat / 200G ortalama", yz(buyume(m["fiyat"], m["ma200"])), puan(buyume(m["fiyat"], m["ma200"]), [-0.15, -0.05, 0.05, 0.15])),
        ],
        "Göreli Değer": [
            ("F/K – emsal medyanına göre", kat(oran(m["fk"], es.get("fk"))), puan(oran(m["fk"], es.get("fk")), [0.6, 0.85, 1.15, 1.5], ters=True)),
            ("PD/DD – emsal medyanına göre", kat(oran(m["pddd"], es.get("pddd"))), puan(oran(m["pddd"], es.get("pddd")), [0.6, 0.85, 1.15, 1.5], ters=True)),
            ("FD/FAVÖK – emsal medyanına göre", kat(oran(m["fd_favok"], es.get("fd_favok"))), puan(oran(m["fd_favok"], es.get("fd_favok")), [0.6, 0.85, 1.15, 1.5], ters=True)),
            ("Adil değere göre potansiyel", yz(m["potansiyel"]), puan(m["potansiyel"], [-0.2, -0.05, 0.1, 0.25])),
        ],
    }
    D = {k: [x for x in v if x[2] is not None] for k, v in D.items()}
    m["saglik_detay"] = {k: v for k, v in D.items() if v}
    m["saglik"] = {k: ort([x[2] for x in v]) for k, v in m["saglik_detay"].items()}
    m["genel_skor"] = ort(list(m["saglik"].values()))
    s = m["genel_skor"]
    m["skor_etiket"] = ("–" if s is None else "MÜKEMMEL" if s >= 4 else "ÇOK İYİ" if s >= 3.25 else
                        "İYİ" if s >= 2.5 else "ORTA" if s >= 1.75 else "ZAYIF")

# =====================================================================
# GÜÇLÜ / ZAYIF YÖNLER ve YORUM
# =====================================================================
def ipuclari(m):
    g, z = [], []
    enf = PARAM["ENFLASYON"]; es = m.get("emsal_stat", {})
    if m["net_borc"] < 0 and not m["finansal"]:
        g.append(f"Net nakit pozisyonunda ({tl(-m['net_borc'])} TL); bilanço esnekliği yüksek.")
    if m["roe"] is not None:
        if m["roe"] > enf + 0.05: g.append(f"Özkaynak kârlılığı ({yz(m['roe'])}) enflasyonun belirgin üzerinde; reel değer yaratıyor.")
        elif m["roe"] < enf - 0.05: z.append(f"Özkaynak kârlılığı ({yz(m['roe'])}) enflasyonun altında; reel olarak değer kaybı riski.")
    rb = reel(m["ciro_b"])
    if rb is not None:
        if rb > 0.05: g.append(f"Hasılat enflasyondan arındırıldığında {yz(rb)} reel büyüdü.")
        elif rb < -0.05: z.append(f"Hasılat reel bazda {yz(rb)} daraldı; nominal büyüme enflasyonun gerisinde.")
    if m["net_b"] is not None and m["net_b"] < 0:
        z.append(f"Net kâr son yılda {yz(m['net_b'])} geriledi.")
    if m["ceyrek_net_b"] is not None:
        (g if m["ceyrek_net_b"] > enf else z).append(f"Son çeyrek net kâr bir önceki yılın aynı çeyreğine göre {yz(abs(m['ceyrek_net_b']))} {'arttı' if m['ceyrek_net_b'] >= 0 else 'geriledi'}" + ("." if m["ceyrek_net_b"] > enf else "; enflasyonun altında kaldı."))
    if m["na_kalite"] is not None and not m["finansal"]:
        if m["na_kalite"] > 1.1: g.append(f"Kâr kalitesi güçlü: işletme nakit akışı net kârın {kat(m['na_kalite'])} katı.")
        elif m["na_kalite"] < 0.6: z.append(f"Kâr kalitesi zayıf: işletme nakit akışı net kârın yalnızca {kat(m['na_kalite'])} katı.")
    if m["sna_verim"] is not None and not m["finansal"]:
        if m["sna_verim"] > 0.06: g.append(f"Serbest nakit akışı verimi yüksek ({yz(m['sna_verim'])}).")
        elif m["sna_verim"] < 0: z.append("Serbest nakit akışı negatif; büyüme/yatırım dış finansmana dayanıyor olabilir.")
    if m["nb_favok"] is not None and m["nb_favok"] > 3: z.append(f"Net borç/FAVÖK {kat(m['nb_favok'])}; kaldıraç yüksek.")
    if m["faiz_karsilama"] is not None and m["faiz_karsilama"] < 2: z.append(f"Faiz karşılama oranı düşük ({kat(m['faiz_karsilama'])}); yüksek faiz ortamında risk.")
    if m["cari"] is not None and m["cari"] < 1: z.append(f"Cari oran 1'in altında ({kat(m['cari'])}); kısa vadeli likidite baskısı olabilir.")
    if m["altman"] is not None:
        if m["altman"] > 2.6: g.append(f"Altman Z'' skoru ({ond(m['altman'], 2)}) güvenli bölgede.")
        elif m["altman"] < 1.1: z.append(f"Altman Z'' skoru ({ond(m['altman'], 2)}) finansal sıkıntı bölgesinde.")
    if m["piotroski"] is not None:
        if m["piotroski"] >= 7: g.append(f"Piotroski F-skoru yüksek ({_tr(str(m['piotroski']))}/9); temeller iyileşiyor.")
        elif m["piotroski"] <= 3: z.append(f"Piotroski F-skoru düşük ({_tr(str(m['piotroski']))}/9); temellerde bozulma sinyali.")
    if es.get("fk") and m["fk"]:
        r = m["fk"] / es["fk"]["med"]
        if r < 0.8: g.append(f"F/K ({kat(m['fk'])}) emsal medyanının ({kat(es['fk']['med'])}) belirgin altında.")
        elif r > 1.3: z.append(f"F/K ({kat(m['fk'])}) emsal medyanına ({kat(es['fk']['med'])}) göre primli.")
    if m["fk"] is None and m["T"]["net"] is not None and m["T"]["net"] <= 0:
        z.append("Son 12 ayda zarar açıklandı; F/K anlamsız.")
    if m["temettu_verim"] and m["temettu_verim"] > 0.04:
        g.append(f"Temettü verimi {yz(m['temettu_verim'])}.")
    ty = m.get("temettu_yillik")
    if ty is not None and len(ty) >= 3:
        son3 = [y for y in range(m["tarih"].year - 3, m["tarih"].year) if y in ty.index and ty[y] > 0]
        if len(son3) == 3: g.append("Son 3 yılın tamamında temettü dağıttı.")
    if m["ma200"]:
        (g if m["fiyat"] > m["ma200"] else z).append(
            f"Fiyat 200 günlük ortalamanın {'üzerinde' if m['fiyat'] > m['ma200'] else 'altında'}; ana trend {'yukarı' if m['fiyat'] > m['ma200'] else 'aşağı'} yönlü.")
    if m["rsi"] > 70: z.append(f"RSI {ond(m['rsi'], 0)} ile aşırı alım bölgesinde; kısa vadeli düzeltme riski.")
    elif m["rsi"] < 30: g.append(f"RSI {ond(m['rsi'], 0)} ile aşırı satım bölgesinde.")
    if m["beta"] is not None and m["beta"] > 1.3: z.append(f"Beta {ond(m['beta'], 2)}; piyasaya göre yüksek oynaklık.")
    if m["fiyat"] >= 0.95 * m["zirve52"]: g.append("52 haftalık zirvesine yakın işlem görüyor (güçlü momentum).")
    if m["fiyat"] <= 1.08 * m["dip52"]: z.append("52 haftalık dibine yakın işlem görüyor.")
    if m.get("ort_islem_tl") is not None and m["ort_islem_tl"] < 20e6: z.append("Günlük işlem hacmi düşük; likidite riski.")
    if m["potansiyel"] is not None:
        if m["potansiyel"] > 0.15: g.append(f"Model bazlı adil değer mevcut fiyatın {yz(m['potansiyel'])} üzerinde.")
        elif m["potansiyel"] < -0.15: z.append(f"Model bazlı adil değer mevcut fiyatın {yz(-m['potansiyel'])} altında.")
    nav = m.get("nav")
    if nav and nav.get("iskonto") is not None:
        if nav["iskonto"] > nav["hedef_iskonto"] + 0.05:
            g.append(f"Holding, iştiraklerinin piyasa değerine göre {yz(nav['iskonto'], 0)} iskontolu (hedef {yz(nav['hedef_iskonto'], 0)}).")
        elif nav["iskonto"] < nav["hedef_iskonto"] - 0.05:
            z.append(f"Holding iskontosu ({yz(nav['iskonto'], 0)}) tarihsel varsayımın ({yz(nav['hedef_iskonto'], 0)}) altında; prim alanı sınırlı.")
    bk = m.get("banka") or {}
    if bk.get("nim") is not None and bk["nim"] > 0.05:
        g.append(f"Net faiz marjı güçlü ({yz(bk['nim'])}).")
    if bk.get("risk_maliyeti") is not None and bk["risk_maliyeti"] > 0.03:
        z.append(f"Risk maliyeti yüksek ({yz(bk['risk_maliyeti'])}); aktif kalitesi izlenmeli.")
    if bk.get("kredi_mevduat") is not None and bk["kredi_mevduat"] > 1.1:
        z.append(f"Kredi/mevduat oranı {kat(bk['kredi_mevduat'])}; fonlama baskısı olabilir.")
    v = m.get("veri") or {}
    if v.get("gun") is not None and v["gun"] > 200:
        z.insert(0, f"Son finansal dönem {v['gun']} gün önce; veriler güncel olmayabilir.")
    if v.get("eksik"):
        z.append("Eksik veri: " + ", ".join(v["eksik"]) + ".")
    if m.get("sinirlandi"):
        z.append("Model sonuçları aşırı uçta olduğu için adil değer temkinli sınıra çekildi.")
    m["guclu"], m["zayif"] = g[:9], z[:9]

def yatirim_ozeti(m):
    c = []
    c.append(f"{m['ad']} ({m['kod']}), {tl(m['piy_deg'])} TL piyasa değeriyle {m['sektor']} sektöründe işlem görmektedir. "
             f"Hisse {tl(m['fiyat'])} TL seviyesinden, son 12 aylık verilere göre {kat(m['fk'])} F/K ve {kat(m['pddd'])} PD/DD çarpanlarıyla fiyatlanıyor.")
    if m["adil"]:
        c.append(f"{len([y for y in m['yontemler'] if y[6]])} farklı değerleme yönteminin ağırlıklı ortalamasıyla ulaşılan adil değer "
                 f"<b>{tl(m['adil'])} TL</b> (aralık {tl(m['adil_dusuk'])} – {tl(m['adil_yuksek'])} TL) olup mevcut fiyata göre "
                 f"<b>{yz(m['potansiyel'])}</b> potansiyele işaret ediyor; değerleme görüşü <b>{m['gorus'].lower()}</b>, model güveni <b>{m['guven'].lower()}</b>.")
    if m["genel_skor"]:
        en = sorted(m["saglik"].items(), key=lambda x: x[1])
        c.append(f"Finansal sağlık skoru <b>{ond(m['genel_skor'], 2)}/5 ({m['skor_etiket'].lower()})</b>; "
                 f"en güçlü alan {en[-1][0].lower()}, en zayıf alan {en[0][0].lower()}.")
    if m["roe"] is not None:
        c.append(f"Şirket son 12 ayda {yz(m['roe'])} özkaynak kârlılığı üretmiş olup bu oran %{ond(PARAM['ENFLASYON']*100, 1)} yıllık enflasyonla "
                 f"karşılaştırıldığında {'reel getiri yaratıldığını' if m['roe'] > PARAM['ENFLASYON'] else 'reel bazda getiri üretilemediğini'} gösteriyor.")
    if m["r"].get("1Y") is not None:
        e1 = m["r_endeks"].get("1Y")
        c.append(f"Hisse son bir yılda {yz(m['r']['1Y'])} getiri sağladı" + (f" (BIST 100: {yz(e1)})" if e1 is not None else "") +
                 f"; teknik görünüm <b>{m['teknik_ozet'].lower()}</b>.")
    return " ".join(c)

# =====================================================================
# GRAFİKLER
# =====================================================================
def _png(fig, dpi=170):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=dpi, bbox_inches="tight"); plt.close(fig); b.seek(0); return b

def _img(buf, gen, oran):
    return Image(buf, gen, gen * oran)

def g_saglik(m):
    k = list(m["saglik"].keys()); v = [m["saglik"][x] for x in k]
    fig, ax = plt.subplots(figsize=(7.5, 0.42 * len(k) + 0.5))
    renk = [C["yesil"] if s >= 3.5 else C["sari"] if s >= 2.5 else C["kirmizi"] for s in v]
    ax.barh(k[::-1], [5] * len(k), color="#EEF1F5", height=0.6)
    ax.barh(k[::-1], v[::-1], color=renk[::-1], height=0.6)
    for i, s in enumerate(v[::-1]):
        ax.text(s + 0.06, i, _tr(f"{s:.2f}"), va="center", fontsize=8, fontweight="bold")
    ax.set_xlim(0, 5.4); ax.set_xticks([1, 2, 3, 4, 5]); ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False); ax.set_title("Finansal Sağlık Skoru – Kategoriler (1–5)", loc="left")
    return _png(fig)

def g_futbol(m):
    Y = [y for y in m["yontemler"] if y[1] is not None]
    if not Y: return None
    fig, ax = plt.subplots(figsize=(7.5, 0.45 * len(Y) + 0.9))
    for i, y in enumerate(Y[::-1]):
        lo, hi = y[2], y[3]
        rk = C["mavi"] if y[6] else C["gri"]
        if lo is not None and hi is not None:
            ax.barh(i, hi - lo, left=lo, color=rk, alpha=0.35, height=0.55)
        ax.plot(y[1], i, "o", color=rk, ms=6)
        ax.text(y[1], i + 0.33, tl(y[1]), ha="center", fontsize=7)
    ax.set_yticks(range(len(Y)), [y[0] + ("" if y[6] else " *") for y in Y[::-1]])
    ax.axvline(m["fiyat"], color=C["kirmizi"], ls="--", lw=1.2, label=f"Fiyat {tl(m['fiyat'])}")
    if m["adil"]:
        ax.axvline(m["adil"], color=C["yesil"], lw=1.6, label=f"Adil değer {tl(m['adil'])}")
    ax.legend(fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2); ax.set_xlabel("TL / hisse")
    ax.set_title("Değerleme Aralıkları (Futbol Sahası Grafiği)", loc="left"); ax.grid(axis="x", alpha=0.25)
    return _png(fig)

def g_fiyat(h, endeks, kod):
    k = h["Close"].dropna(); son = k.index[-1]; bas = son - pd.Timedelta(days=365)
    ky = k[k.index >= bas]
    fig = plt.figure(figsize=(7.5, 5.6)); gs = fig.add_gridspec(4, 1, height_ratios=[3, 0.8, 1, 1], hspace=0.12)
    ax = fig.add_subplot(gs[0]); ax.plot(ky.index, ky, color=C["lac"], lw=1.4, label="Fiyat")
    for n, rk in ((50, C["tur"]), (200, C["yesil"])):
        ax.plot(ky.index, k.rolling(n).mean().reindex(ky.index), color=rk, lw=0.9, label=f"{n}G ort.")
    ma20, sd = k.rolling(20).mean().reindex(ky.index), k.rolling(20).std().reindex(ky.index)
    ax.fill_between(ky.index, ma20 - 2 * sd, ma20 + 2 * sd, color=C["acik"], alpha=0.35, label="Bollinger")
    ax.set_title(f"{kod} – Son 12 Ay Fiyat, Ortalamalar ve Göstergeler", loc="left"); ax.legend(fontsize=7, frameon=False, ncol=4)
    ax.grid(alpha=0.2); ax.tick_params(labelbottom=False)
    a2 = fig.add_subplot(gs[1], sharex=ax)
    if "Volume" in h:
        v = h["Volume"].reindex(ky.index); a2.bar(ky.index, v, color=C["gri"], width=1.0)
    a2.set_ylabel("Hacim", fontsize=7); a2.tick_params(labelbottom=False, labelsize=6); a2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: tl(x, 0)))
    a3 = fig.add_subplot(gs[2], sharex=ax); r = rsi(k).reindex(ky.index)
    a3.plot(ky.index, r, color=C["mavi"], lw=1); a3.axhline(70, color=C["kirmizi"], lw=0.7, ls="--"); a3.axhline(30, color=C["yesil"], lw=0.7, ls="--")
    a3.set_ylim(0, 100); a3.set_ylabel("RSI", fontsize=7); a3.tick_params(labelbottom=False, labelsize=6)
    a4 = fig.add_subplot(gs[3], sharex=ax)
    macd = (k.ewm(span=12).mean() - k.ewm(span=26).mean()); sig = macd.ewm(span=9).mean()
    hst = (macd - sig).reindex(ky.index)
    a4.bar(ky.index, hst, color=[C["yesil"] if x >= 0 else C["kirmizi"] for x in hst.fillna(0)], width=1.0)
    a4.plot(ky.index, macd.reindex(ky.index), color=C["lac"], lw=0.8); a4.plot(ky.index, sig.reindex(ky.index), color=C["tur"], lw=0.8)
    a4.set_ylabel("MACD", fontsize=7); a4.tick_params(labelsize=6)
    return _png(fig)

def g_goreli(h, endeks, kod):
    k = h["Close"].dropna(); son = k.index[-1]
    fig, axs = plt.subplots(1, 2, figsize=(7.5, 2.6), gridspec_kw={"wspace": 0.25})
    ax = axs[0]; ky = k[k.index >= son - pd.Timedelta(days=365)]
    ax.plot(ky.index, ky / ky.iloc[0] * 100, color=C["lac"], lw=1.3, label=kod)
    if endeks is not None:
        e = endeks["Close"].dropna(); e = e[e.index >= ky.index[0]]
        if len(e): ax.plot(e.index, e / e.iloc[0] * 100, color=C["tur"], lw=1.1, label="BIST 100")
    ax.axhline(100, color=C["gri"], lw=0.6); ax.legend(fontsize=7, frameon=False)
    ax.set_title("Göreli Performans (12 ay, 100 baz)", loc="left"); ax.tick_params(axis="x", labelsize=6, rotation=30); ax.grid(alpha=0.2)
    ax = axs[1]; k3 = k[k.index >= son - pd.Timedelta(days=365 * 3)]; dd = k3 / k3.cummax() - 1
    ax.fill_between(dd.index, dd * 100, 0, color=C["kirmizi"], alpha=0.35); ax.plot(dd.index, dd * 100, color=C["kirmizi"], lw=0.7)
    ax.set_title("Zirveden Düşüş (3 yıl, %)", loc="left"); ax.tick_params(axis="x", labelsize=6, rotation=30); ax.grid(alpha=0.2)
    return _png(fig)

def g_finansal(m):
    S = m["S"]; c, n = S["Hasılat"], S["Net Kâr"]
    if c is None: return None
    idx = list(c.index[:5])[::-1]; yil = [str(i.year) for i in idx]
    fig, axs = plt.subplots(1, 2, figsize=(7.5, 2.7), gridspec_kw={"wspace": 0.3})
    ax = axs[0]; x = np.arange(len(idx)); w = 0.38
    ax.bar(x - w/2, [c[i] / 1e9 for i in idx], w, color=C["lac"], label="Hasılat")
    if n is not None: ax.bar(x + w/2, [n.get(i, np.nan) / 1e9 for i in idx], w, color=C["tur"], label="Net kâr")
    ax.set_xticks(x, yil); ax.set_ylabel("milyar TL"); ax.legend(fontsize=7, frameon=False); ax.grid(axis="y", alpha=0.2)
    ax.set_title("Yıllık Hasılat ve Net Kâr", loc="left")
    ax = axs[1]
    for ad, rk in (("Brüt Kâr", C["mavi"]), ("FAVÖK", C["yesil"]), ("Net Kâr", C["tur"])):
        s = S[ad]
        if s is not None and not (m["finansal"] and ad != "Net Kâr"):
            ax.plot(yil, [s.get(i, np.nan) / c[i] * 100 for i in idx], marker="o", ms=3, color=rk, label=ad.replace(" Kâr", ""))
    ax.set_title("Marj Gelişimi (%)", loc="left"); ax.legend(fontsize=7, frameon=False); ax.grid(alpha=0.2)
    return _png(fig)

def g_ceyrek(m):
    qc, qn = m["q_ciro"], m["q_net"]
    if qc is None or len(qc) < 3: return None
    idx = list(qc.index[:8])[::-1]; et = [f"{i.year % 100}/Ç{(i.month - 1)//3 + 1}" for i in idx]
    fig, ax = plt.subplots(figsize=(7.5, 2.4))
    ax.bar(et, [qc[i] / 1e9 for i in idx], color=C["acik"], edgecolor=C["mavi"], label="Hasılat (mr TL)")
    ax.set_ylabel("milyar TL"); ax.grid(axis="y", alpha=0.2)
    if qn is not None:
        a2 = ax.twinx(); a2.spines["right"].set_visible(True)
        a2.plot(et, [qn.get(i, np.nan) / qc[i] * 100 for i in idx], color=C["tur"], marker="o", ms=3, label="Net marj %")
        a2.set_ylabel("Net marj %"); a2.legend(fontsize=7, frameon=False, loc="upper right")
    ax.legend(fontsize=7, frameon=False, loc="upper left"); ax.set_title("Çeyreklik Hasılat ve Net Kâr Marjı", loc="left")
    return _png(fig)

def g_emsal(m, emsaller):
    P = [e for e in emsaller if e.get("pddd") and e.get("roe") is not None and 0 < e["pddd"] < 30]
    if len(P) < 2 or m["pddd"] is None or m["roe"] is None: return None
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    ax.scatter([e["roe"] * 100 for e in P], [e["pddd"] for e in P], s=40, color=C["mavi"], alpha=0.7)
    for e in P: ax.annotate(e["kod"], (e["roe"] * 100, e["pddd"]), fontsize=7, xytext=(4, 3), textcoords="offset points")
    ax.scatter([m["roe"] * 100], [m["pddd"]], s=90, color=C["tur"], edgecolor=C["lac"], zorder=5)
    ax.annotate(m["kod"], (m["roe"] * 100, m["pddd"]), fontsize=8, fontweight="bold", xytext=(5, 4), textcoords="offset points")
    xs = np.array([e["roe"] * 100 for e in P] + [m["roe"] * 100]); ys = np.array([e["pddd"] for e in P] + [m["pddd"]])
    if len(xs) >= 3 and np.std(xs) > 0:
        a, b = np.polyfit(xs, ys, 1); xx = np.linspace(xs.min(), xs.max(), 10); ax.plot(xx, a * xx + b, ls="--", color=C["gri"], lw=0.9)
    ax.set_xlabel("ROE (%)"); ax.set_ylabel("PD/DD (x)"); ax.grid(alpha=0.2)
    ax.set_title("Emsal Konumlandırma: ROE vs PD/DD (regresyon çizgisinin altı = görece ucuz)", loc="left")
    return _png(fig)

def g_temettu(m):
    ty = m.get("temettu_yillik")
    if ty is None or len(ty) == 0: return None
    ty = ty[ty.index >= m["tarih"].year - 9]
    fig, ax = plt.subplots(figsize=(7.5, 2.2))
    ax.bar([str(y) for y in ty.index], ty.values, color=C["yesil"])
    for i, v in enumerate(ty.values): ax.text(i, v, tl(v), ha="center", va="bottom", fontsize=7)
    ax.set_title("Yıllık Hisse Başına Temettü (TL, brüt)", loc="left"); ax.grid(axis="y", alpha=0.2)
    return _png(fig)

# =====================================================================
# PDF
# =====================================================================
def tablo(veri, gen, baslik=True, hizala_sol=(0,), kalin_son=False, renkli_kolon=None, font=7.8):
    veri = [[c if not isinstance(c, str) or len(c) < 60 else Paragraph(c, ST["hucre"]) for c in r] for r in veri]
    t = Table(veri, colWidths=gen, repeatRows=1 if baslik else 0, hAlign="LEFT")
    s = [("FONTNAME", (0, 0), (-1, -1), "DV"), ("FONTSIZE", (0, 0), (-1, -1), font),
         ("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
         ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
         ("LINEBELOW", (0, 0), (-1, -1), 0.3, CIZGI)]
    for c in hizala_sol: s.append(("ALIGN", (c, 0), (c, -1), "LEFT"))
    if baslik:
        s += [("BACKGROUND", (0, 0), (-1, 0), LAC), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
              ("FONTNAME", (0, 0), (-1, 0), "DVB")]
    s.append(("ROWBACKGROUNDS", (0, 1 if baslik else 0), (-1, -1), [colors.white, ACIK]))
    if kalin_son: s += [("FONTNAME", (0, -1), (-1, -1), "DVB"), ("LINEABOVE", (0, -1), (-1, -1), 0.8, LAC)]
    t.setStyle(TableStyle(s)); return t

def puan_renk(p):
    return YESIL if p >= 3.5 else SARI if p >= 2.5 else KIRMIZI

def kutu(etiket, deger_, alt=None, renk=LAC):
    icerik = [[Paragraph(f'<font size="6.8" color="#6B7280">{etiket}</font>', ST["hucre"])],
              [Paragraph(f'<font name="DVB" size="11.5" color="{renk.hexval().replace("0x", "#")}">{deger_}</font>', ST["hucre"])]]
    if alt: icerik.append([Paragraph(f'<font size="6.8" color="#6B7280">{alt}</font>', ST["hucre"])])
    t = Table(icerik); t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACIK), ("LEFTPADDING", (0, 0), (-1, -1), 6),
                                              ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                                              ("LINEBEFORE", (0, 0), (0, -1), 2.2, renk)]))
    return t

def pdf_olustur(d, m, emsaller, endeks, dosya):
    W = A4[0] - 3.0 * cm
    def sayfa(c, doc):
        c.saveState()
        c.setFillColor(LAC); c.rect(0, A4[1] - 0.9 * cm, A4[0], 0.9 * cm, fill=1, stroke=0)
        c.setFillColor(colors.white); c.setFont("DVB", 8.5)
        c.drawString(1.5 * cm, A4[1] - 0.58 * cm, f"{m['kod']}  |  HİSSE ARAŞTIRMA RAPORU")
        c.setFont("DV", 8); c.drawRightString(A4[0] - 1.5 * cm, A4[1] - 0.58 * cm, f"{dt.date.today():%d.%m.%Y}")
        c.setFillColor(GRI); c.setFont("DV", 6.8)
        c.drawString(1.5 * cm, 0.8 * cm, "Kaynak: Yahoo Finance, KAP verileri; hesaplamalar otomatik model. Yatırım tavsiyesi değildir.")
        c.drawRightString(A4[0] - 1.5 * cm, 0.8 * cm, f"Sayfa {doc.page}")
        c.restoreState()
    doc = SimpleDocTemplate(dosya, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            topMargin=1.4 * cm, bottomMargin=1.3 * cm, title=f"{m['kod']} Araştırma Raporu")
    E = []
    pt = m["potansiyel"]; pr = YESIL if pt and pt > 0.15 else KIRMIZI if pt and pt < -0.15 else SARI

    # ---------------- SAYFA 1: ÖZET ----------------
    E.append(Paragraph(f"{m['ad']}", ST["h1"]))
    E.append(Paragraph(f'<font color="#6B7280">BIST: {m["kod"]}  ·  {m["sektor"]} / {m["sanayi"]}  ·  Veri tarihi {m["tarih"]:%d.%m.%Y}</font>', ST["p"]))
    E.append(Paragraph(f'<font color="#6B7280">Finansal veri kaynağı: {m.get("kaynak", "Yahoo Finance")}'
                       + (f' · {m["kur_notu"]}' if m.get("kur_notu") else "") + '</font>', ST["kucuk"]))
    E.append(Spacer(1, 7))
    kw = W / 4 - 3
    satir1 = [kutu("SON FİYAT", f"{tl(m['fiyat'])} TL", f"52H: {tl(m['dip52'])} – {tl(m['zirve52'])}"),
              kutu("ADİL DEĞER", f"{tl(m['adil'])} TL" if m["adil"] else "–", f"Aralık {tl(m['adil_dusuk'])} – {tl(m['adil_yuksek'])}" if m["adil"] else None, MAVI),
              kutu("POTANSİYEL", yz(pt), m["gorus"], pr),
              kutu("SAĞLIK SKORU", f"{ond(m['genel_skor'], 2)}/5" if m["genel_skor"] else "–", m["skor_etiket"], puan_renk(m["genel_skor"] or 0))]
    satir2 = [kutu("PİYASA DEĞERİ", f"{tl(m['piy_deg'])} TL", f"FD: {tl(m['fd'])} TL"),
              kutu("F/K  ·  PD/DD", f"{kat(m['fk'])} · {kat(m['pddd'])}", f"FD/FAVÖK {kat(m['fd_favok'])}" if not m["finansal"] else f"Özkaynak/Varlık {yz(bol(m['K']['ozk'], m['K']['varlik']))}"),
              kutu("ROE  ·  NET MARJ", f"{yz(m['roe'])} · {yz(m['net_marj'])}", f"ROA {yz(m['roa'])}"),
              kutu("TEMETTÜ VERİMİ  ·  BETA", f"{yz(m['temettu_verim'])} · {ond(m['beta'], 2) if m['beta'] is not None else '–'}", f"Teknik: {m['teknik_ozet']}")]
    g = Table([satir1, satir2], colWidths=[kw + 3] * 4, rowHeights=None)
    g.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    E += [g, Spacer(1, 4)]
    E.append(Paragraph("Yatırım Özeti", ST["h2"])); E.append(Paragraph(yatirim_ozeti(m), ST["p"]))
    E.append(Paragraph("Öne Çıkanlar", ST["h2"]))
    gl = [Paragraph(f'<font color="#1E8E5A">▲</font> {x}', ST["madde"]) for x in m["guclu"]] or [Paragraph("–", ST["madde"])]
    zl = [Paragraph(f'<font color="#C0392B">▼</font> {x}', ST["madde"]) for x in m["zayif"]] or [Paragraph("–", ST["madde"])]
    n = max(len(gl), len(zl)); gl += [""] * (n - len(gl)); zl += [""] * (n - len(zl))
    t = Table([[Paragraph("<b>Güçlü Yönler</b>", ST["hucreB"]), Paragraph("<b>Dikkat Edilmesi Gerekenler</b>", ST["hucreB"])]] +
              list(zip(gl, zl)), colWidths=[W / 2, W / 2])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (0, 0), 1.2, YESIL),
                           ("LINEBELOW", (1, 0), (1, 0), 1.2, KIRMIZI), ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]))
    E.append(t)
    if m["saglik"]:
        E.append(Spacer(1, 6)); E.append(_img(g_saglik(m), W * 0.92, (0.42 * len(m["saglik"]) + 0.5) / 7.5))

    # ---------------- SAYFA 2: DEĞERLEME ----------------
    E.append(PageBreak()); E.append(Paragraph("1. Değerleme Analizi", ST["h1"]))
    E.append(Paragraph("Adil değer, şirketin yapısına uygun yöntemlerin ağırlıklı ortalaması ile ağırlıklı medyanının ortalamasıdır. "
                       "Fiyatın %40'ının altında veya 2,5 katının üzerinde sonuç veren yöntemler aykırı sayılıp hariç tutulur (*). "
                       f"Temkinli yaklaşım gereği potansiyel {yz(PARAM['MIN_POTANSIYEL'], 0)} ile +{yz(PARAM['MAKS_POTANSIYEL'], 0)} arasında sınırlanır"
                       + (" — <b>bu raporda sınır uygulandı</b>." if m.get("sinirlandi") else "."), ST["kucuk"]))
    tw_ = sum(y[4] for y in m["yontemler"] if y[6]) or 1
    v = [["Yöntem", "Değer (TL)", "Potansiyel", "Ağırlık", "Açıklama"]]
    for y in m["yontemler"]:
        v.append([y[0] + ("" if y[6] else " *"), tl(y[1]), yz(buyume(y[1], m["fiyat"])),
                  yz(y[4] / tw_, 0) if y[6] else "hariç", Paragraph(y[5], ST["hucre"])])
    v.append(["Ağırlıklı Adil Değer", tl(m["adil"]), yz(pt), "%100", Paragraph(f"Görüş: <b>{m['gorus']}</b> · Güven: <b>{m['guven']}</b>", ST["hucre"])])
    E.append(tablo(v, [W * .25, W * .13, W * .12, W * .09, W * .41], kalin_son=True))
    f = g_futbol(m)
    if f: E += [Spacer(1, 6), _img(f, W, (0.45 * len([y for y in m["yontemler"] if y[1]]) + 0.9) / 7.5)]
    nav = m.get("nav")
    if nav:
        v = [["İştirak", "Holding payı", "Piyasa değeri (TL)", "Holdinge düşen (TL)", "NAV payı"]]
        for k in sorted(nav["kalemler"], key=lambda k: -(k["deger"] or 0)):
            v.append([f"{k['kod']} – {k['ad']}", yz(k["pay"]), tl(k["piy_deg"]), tl(k["deger"]), yz(k["oran"], 0)])
        v.append(["Halka açık iştirakler toplamı", "", "", tl(nav["toplam"]), "%100"])
        ozet = (f"Holdingin piyasa değeri {tl(m['piy_deg'])} TL; halka açık iştiraklerinin holdinge düşen değeri {tl(nav['toplam'])} TL. "
                f"Mevcut iskonto <b>{yz(nav.get('iskonto'), 0)}</b>, değerlemede kullanılan hedef iskonto <b>{yz(nav['hedef_iskonto'], 0)}</b>. "
                "Halka açık olmayan şirketler ve holdingin kendi net nakdi dahil edilmediği için hesap temkinlidir. "
                "Paylar KAP genel bilgi formlarından alınmıştır; değişiklikleri KAP'tan teyit edin.")
        E.append(KeepTogether([Paragraph("Holding Net Aktif Değer (NAV) Analizi", ST["h2"]),
                               tablo(v, [W * .36, W * .14, W * .18, W * .18, W * .14], kalin_son=True, font=7.4),
                               Spacer(1, 3), Paragraph(ozet, ST["kucuk"])]))
    if m["dcf"]:
        b = m["dcf"]; w = m["wacc"]
        E.append(Paragraph("İndirgenmiş Nakit Akışı (İNA / DCF) Detayı", ST["h2"]))
        sol = tablo([["AOSM (WACC) Bileşeni", "Değer"],
                     ["Risksiz faiz (TR 10Y)", yz(PARAM["RF"])], ["Beta (BIST 100'e göre)", _tr(f"{w['beta']:.2f}")],
                     ["Hisse risk primi", yz(PARAM["ERP"])], ["Özkaynak maliyeti (Ke)", yz(w["ke"])],
                     ["Vergi sonrası borç maliyeti", yz(w["kd"])], ["Özkaynak / Borç ağırlığı", f"{yz(w['we'], 0)} / {yz(w['wd'], 0)}"],
                     ["AOSM", yz(b["wacc"])], ["Uç büyüme (nominal TL)", yz(b["gT"])],
                     ["SNA marjı varsayımı", yz(b["marj"])], ["Uç değerin FD içindeki payı", yz(b["tv_pay"])]],
                    [W * .3, W * .17])
        pv = [["Yıl", "Büyüme", "Hasılat", "SNA", "BD"]] + [[str(r[0]), yz(r[1]), tl(r[2]), tl(r[3]), tl(r[4])] for r in b["projeksiyon"]]
        pv += [["Uç değer (BD)", "", "", "", tl(b["pv_tv"])], ["Firma değeri", "", "", "", tl(b["fd"])],
               ["(−) Net borç ve azınlık", "", "", "", tl(m["net_borc"] + m["K"]["azinlik"])],
               ["Hisse başına değer", "", "", "", tl(b["deger"])]]
        sag = tablo(pv, [W * .1, W * .08, W * .1, W * .1, W * .1], kalin_son=True, font=7.2)
        t = Table([[sol, sag]], colWidths=[W * .49, W * .51]); t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        E.append(t)
        sc = m["senaryo"]
        if sc:
            v = [["Senaryo", "Başlangıç büyüme", "SNA marjı", "AOSM", "Değer (TL)", "Potansiyel"]]
            for ad, s in sc.items():
                if s: v.append([ad, yz(s["g0"]), yz(s["marj"]), yz(s["wacc"]), tl(s["deger"]), yz(buyume(s["deger"], m["fiyat"]))])
            E.append(KeepTogether([Paragraph("Senaryo Analizi", ST["h2"]), tablo(v, [W * .2, W * .17, W * .15, W * .14, W * .17, W * .17])]))
        if m["duyarlilik"]:
            wl, gl_, M = m["duyarlilik"]
            v = [["AOSM \\ g"] + [yz(x) for x in gl_]] + [[yz(wl[i])] + [tl(x) for x in M[i]] for i in range(len(wl))]
            t = tablo(v, [W * .2] + [W * .16] * 5)
            st = [("BACKGROUND", (3, 3), (3, 3), colors.HexColor("#FFE8C7")), ("FONTNAME", (3, 3), (3, 3), "DVB"),
                  ("BACKGROUND", (0, 1), (0, -1), ACIK), ("FONTNAME", (0, 1), (0, -1), "DVB")]
            for i in range(len(wl)):
                for j in range(len(gl_)):
                    x = M[i][j]
                    if x is not None:
                        st.append(("TEXTCOLOR", (j + 1, i + 1), (j + 1, i + 1), YESIL if x > m["fiyat"] * 1.1 else KIRMIZI if x < m["fiyat"] * 0.9 else colors.black))
            t.setStyle(TableStyle(st)); E.append(KeepTogether([Paragraph("Duyarlılık Analizi – Hisse Başına Değer (TL): AOSM × Uç Büyüme", ST["h2"]), t]))
    elif m["finansal"]:
        E.append(Paragraph("Finansal kuruluşlarda (banka/sigorta) nakit akışı tabanlı İNA uygun olmadığından "
                           "gerekçeli PD/DD (ROE–Ke yaklaşımı), emsal çarpanları ve temettü modeli kullanılmıştır.", ST["p"]))

    # ---------------- SAYFA 3: FİNANSAL SAĞLIK ----------------
    E.append(CondPageBreak(9 * cm)); E.append(Paragraph("2. Finansal Sağlık Analizi", ST["h1"]))
    E.append(Paragraph(f"Her metrik 1 (zayıf) – 5 (güçlü) arası puanlanır. Büyüme metrikleri %{ond(PARAM['ENFLASYON']*100, 2)} "
                       "yıllık TÜFE ile reelleştirilmiştir. Kategori skoru, alt metriklerin ortalamasıdır.", ST["kucuk"]))
    for kat_, liste in m["saglik_detay"].items():
        v = [[f"{kat_}  –  {ond(m['saglik'][kat_], 2)}/5", "Değer", "Puan"]] + [[a, b_, _tr(f"{p_:.0f}")] for a, b_, p_ in liste]
        t = tablo(v, [W * .6, W * .25, W * .15])
        st = []
        for i, (_, _, p_) in enumerate(liste, 1):
            st += [("TEXTCOLOR", (2, i), (2, i), puan_renk(p_)), ("FONTNAME", (2, i), (2, i), "DVB")]
        st.append(("BACKGROUND", (0, 0), (-1, 0), puan_renk(m["saglik"][kat_])))
        t.setStyle(TableStyle(st)); E += [KeepTogether([t, Spacer(1, 5)])]
    pk = m["piotroski_detay"]
    dup = [["DuPont ROE Ayrıştırması", "Değer"], ["Net kâr marjı", yz(m["net_marj"])],
           ["× Varlık devir hızı", kat(m["varlik_devir"])], ["× Finansal kaldıraç", kat(m["kaldirac"])],
           ["= Özkaynak kârlılığı (ROE)", yz(m["roe"])]]
    if m["altman"] is not None:
        dup += [["", ""], ["Altman Z'' (gelişmekte olan piyasa)", ond(m["altman"], 2)],
                ["Bölge", "Güvenli (>2,6)" if m["altman"] > 2.6 else "Gri (1,1–2,6)" if m["altman"] > 1.1 else "Sıkıntı (<1,1)"]]
    dupont = tablo(dup, [W * .32, W * .16], font=7.2)
    if pk:
        v = [["Piotroski F-Skoru Kriteri", "Sonuç"]] + [[a, "✓" if r is True else "✗" if r is False else "veri yok"] for a, r in pk]
        v.append(["Toplam (9 üzerinden, eksik veriye göre ölçeklenmiş)", ond(m["piotroski"], 1) if m["piotroski"] is not None else "–"])
        t = tablo(v, [W * .38, W * .1], kalin_son=True, font=7.2)
        t.setStyle(TableStyle([("TEXTCOLOR", (1, i + 1), (1, i + 1), YESIL if r else KIRMIZI) for i, (_, r) in enumerate(pk) if r is not None]))
        t2 = Table([[t, dupont]], colWidths=[W * .5, W * .5])
    else:
        t2 = Table([[dupont]], colWidths=[W]); 
    t2.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)])); t2.hAlign = "LEFT"
    E.append(KeepTogether([Paragraph("Kalite Skorları", ST["h2"]), t2]))
    bk = m.get("banka")
    if bk:
        v = [["Banka Göstergesi", "Değer", "Açıklama"],
             ["Net faiz marjı (aktif bazlı)", yz(bk["nim"]), "Net faiz geliri / ortalama aktifler"],
             ["Faiz gelirinin toplam gelirdeki payı", yz(bk["faiz_geliri_payi"]), "Gelir yapısının faize bağımlılığı"],
             ["Risk maliyeti", yz(bk["risk_maliyeti"]), "Kredi karşılıkları / krediler"],
             ["Gider / Gelir", yz(bk["gider_gelir"]), "Operasyonel verimlilik (düşük iyi)"],
             ["Kredi / Mevduat", kat(bk["kredi_mevduat"]), "Fonlama dengesi (~0,8–1,0 sağlıklı)"],
             ["Kredi / Aktif", yz(bk["kredi_varlik"]), "Bilançonun krediye dönüşümü"],
             ["Özkaynak / Aktif", yz(bk["ozk_varlik"]), "Sermaye tamponu (SYR yerine yaklaşık gösterge)"]]
        E.append(KeepTogether([Paragraph("Bankacılık Göstergeleri", ST["h2"]), tablo(v, [W * .35, W * .15, W * .5], font=7.4, hizala_sol=(0, 2)),
                               Paragraph("Sermaye yeterlilik rasyosu ve takipteki kredi oranı Yahoo verisinde yer almadığı için gösterilemiyor; "
                                         "bu oranlar için bankanın KAP'taki faaliyet raporuna bakın.", ST["kucuk"])]))

    # ---------------- SAYFA 4: FİNANSAL TABLOLAR ----------------
    E.append(CondPageBreak(12 * cm)); E.append(Paragraph("3. Finansal Tablolar ve Trendler", ST["h1"]))
    S = m["S"]; c = S["Hasılat"]
    if c is not None:
        idx = list(c.index[:4]); T = m["T"]
        bas = ["(TL)", "Son 12 Ay"] + [str(i.year) for i in idx]
        def sat(ad, s, ttm_v=None):
            return [ad, tl(ttm_v)] + [tl(s.get(i)) if s is not None and i in s.index else "–" for i in idx]
        def msat(ad, pay, ttm_v):
            return [ad, yz(ttm_v)] + [yz(bol(pay.get(i), c.get(i))) if pay is not None and i in pay.index else "–" for i in idx]
        gw = [W * .28] + [W * .144] * 5
        v = [bas, sat("Hasılat", c, T["ciro"])]
        if not m["finansal"]:
            v += [sat("Brüt kâr", S["Brüt Kâr"], T["brut"]), sat("Faaliyet kârı", S["Faaliyet Kârı"], T["ebit"]), sat("FAVÖK", S["FAVÖK"], T["favok"])]
        v += [sat("Net kâr (ana ortaklık)", S["Net Kâr"], T["net"])]
        if not m["finansal"]:
            v += [msat("Brüt marj", S["Brüt Kâr"], m["brut_marj"]), msat("FAVÖK marjı", S["FAVÖK"], m["favok_marj"])]
        v += [msat("Net marj", S["Net Kâr"], m["net_marj"]),
              ["Hasılat büyümesi", "–"] + [yz(buyume(c.get(idx[i]), c.get(c.index[i + 1]))) if i + 1 < len(c) else "–" for i in range(len(idx))]]
        E.append(KeepTogether([Paragraph("Gelir Tablosu Özeti", ST["h2"]), tablo(v, gw)]))
        K = m["K"]
        v = [["(TL)", "Son Dönem"] + [str(i.year) for i in idx],
             sat("Toplam varlıklar", S["Toplam Varlıklar"], K["varlik"]), sat("Nakit ve benzerleri", S["Nakit ve Benzerleri"], K["nakit"]),
             sat("Toplam finansal borç", S["Toplam Borç"], K["borc"]), sat("Özkaynaklar", S["Özkaynaklar"], K["ozk"]),
             ["Borç / Özkaynak", kat(m["borc_ozk"])] + [kat(bol(S["Toplam Borç"].get(i) if S["Toplam Borç"] is not None else None,
                                                             S["Özkaynaklar"].get(i) if S["Özkaynaklar"] is not None else None)) for i in idx]]
        E.append(KeepTogether([Paragraph("Bilanço Özeti", ST["h2"]), tablo(v, gw)]))
        v = [bas, sat("İşletme faaliyetlerinden NA", S["İşletme Nakit Akışı"], T["isl_na"]),
             sat("Yatırım harcamaları", S["Yatırım Harcamaları"], T["capex"]),
             sat("Serbest nakit akışı", S["Serbest Nakit Akışı"], T["sna"]),
             sat("Ödenen temettü", S["Ödenen Temettü"], T["tem_odenen"])]
        if not m["finansal"]:
            E.append(KeepTogether([Paragraph("Nakit Akış Özeti", ST["h2"]), tablo(v, gw)]))
    fg = g_finansal(m)
    if fg: E += [Spacer(1, 6), _img(fg, W, 2.7 / 7.5)]
    cg = g_ceyrek(m)
    if cg: E += [Spacer(1, 4), _img(cg, W, 2.4 / 7.5)]

    # ---------------- SAYFA 5: EMSAL ----------------
    E.append(CondPageBreak(11 * cm)); E.append(Paragraph("4. Emsal Karşılaştırması", ST["h1"]))
    if emsaller:
        E.append(Paragraph(f"Emsal grubu: {', '.join(e['kod'] for e in emsaller)}. Çarpanlar son 12 aylık verilerle hesaplanmıştır.", ST["kucuk"]))
        v = [["Hisse", "Piy. Değ.", "F/K", "PD/DD", "FD/FAVÖK", "ROE", "Net Marj", "Reel Büy.", "1Y Getiri"]]
        tum = [m] + emsaller
        for e in tum:
            v.append([e["kod"], tl(e["piy_deg"]), kat(e["fk"]), kat(e["pddd"]), kat(e.get("fd_favok")), yz(e["roe"]),
                      yz(e["net_marj"]), yz(reel(e.get("ciro_b"))), yz(e["r"].get("1Y"))])
        med = lambda k_, f_: f_(float(np.median([e[k_] for e in emsaller if e.get(k_) is not None]))) if any(e.get(k_) is not None for e in emsaller) else "–"
        v.append(["Emsal medyanı", med("piy_deg", tl), med("fk", kat), med("pddd", kat), med("fd_favok", kat), med("roe", yz),
                  med("net_marj", yz), "–", "–"])
        t = tablo(v, [W * .12] + [W * .11] * 8, kalin_son=True, font=7.3)
        t.setStyle(TableStyle([("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#FFE8C7")), ("FONTNAME", (0, 1), (-1, 1), "DVB")]))
        E.append(t)
        ge = g_emsal(m, emsaller)
        if ge: E += [Spacer(1, 6), _img(ge, W, 2.8 / 7.5)]
        es = m["emsal_stat"]; cumle = []
        for ad, k_ in (("F/K", "fk"), ("PD/DD", "pddd"), ("FD/FAVÖK", "fd_favok")):
            if es.get(k_) and m.get(k_):
                r = m[k_] / es[k_]["med"] - 1
                cumle.append(f"{ad} bazında emsal medyanına göre {yz(abs(r))} {'iskontolu' if r < 0 else 'primli'}")
        if cumle: E.append(Paragraph("Hisse " + "; ".join(cumle) + " işlem görmektedir.", ST["p"]))
    else:
        E.append(Paragraph("Emsal verisi alınamadı. EMSALLER alanına aynı sektörden hisse kodları girerek bu bölümü doldurabilirsiniz.", ST["p"]))

    # ---------------- SAYFA 6: FİYAT, RİSK, TEKNİK ----------------
    E.append(CondPageBreak(17 * cm)); E.append(Paragraph("5. Fiyat Performansı, Risk ve Teknik Görünüm", ST["h1"]))
    E.append(_img(g_fiyat(d["hist"], endeks, m["kod"]), W, 5.6 / 7.5))
    per = [["Dönem"] + list(m["r"].keys()), [m["kod"]] + [yz(x) for x in m["r"].values()]]
    if m["r_endeks"]:
        per.append(["BIST 100"] + [yz(m["r_endeks"].get(k_)) for k_ in m["r"]])
        per.append(["Göreli fark"] + [yz(m["r"][k_] - m["r_endeks"][k_]) if m["r"][k_] is not None and m["r_endeks"].get(k_) is not None else "–" for k_ in m["r"]])
    E += [Spacer(1, 4), tablo(per, [W * .2] + [W * .8 / 6] * 6, font=7.3)]
    risk = tablo([["Risk Metriği", "Değer"], ["Beta (2Y haftalık, BIST 100)", _tr(f"{m['beta']:.2f}") if m["beta"] is not None else "–"],
                  ["Endeksle korelasyon", _tr(f"{m['korelasyon']:.2f}") if m["korelasyon"] is not None else "–"],
                  ["Yıllık volatilite", yz(m["vol"])], ["Maks. düşüş (3Y)", yz(m["max_dd"])],
                  ["Sharpe (1Y, RF=TR10Y)", _tr(f"{m['sharpe']:.2f}") if m["sharpe"] is not None else "–"],
                  ["Ort. günlük işlem hacmi", f"{tl(m['ort_islem_tl'])} TL"]], [W * .3, W * .17], font=7.2)
    tk = tablo([["Teknik Gösterge", "Değer", "Sinyal"]] + [list(s) for s in m["teknik"]] +
               [["TEKNİK ÖZET", "", m["teknik_ozet"]]], [W * .22, W * .13, W * .15], kalin_son=True, font=7.2)
    st = [("TEXTCOLOR", (2, i + 1), (2, i + 1), YESIL if s[2] in ("Pozitif", "Aşırı satım", "Artan ilgi") else KIRMIZI if s[2] in ("Negatif", "Aşırı alım") else colors.black)
          for i, s in enumerate(m["teknik"])]
    tk.setStyle(TableStyle(st))
    t = Table([[risk, tk]], colWidths=[W * .49, W * .51]); t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    E += [Spacer(1, 6), t, Spacer(1, 6), _img(g_goreli(d["hist"], endeks, m["kod"]), W, 2.6 / 7.5)]

    # ---------------- SAYFA 7: TEMETTÜ + METODOLOJİ ----------------
    E.append(CondPageBreak(9 * cm)); E.append(Paragraph("6. Temettü Analizi", ST["h1"]))
    gt = g_temettu(m)
    if gt:
        ty = m["temettu_yillik"]; yillar = [y for y in ty.index if ty[y] > 0]
        tg = cagr(ty.iloc[-2] if len(ty) >= 2 else None, ty.iloc[max(0, len(ty) - 6)], min(4, len(ty) - 2)) if len(ty) >= 3 else None
        E.append(tablo([["Temettü Göstergesi", "Değer"], ["Son 12 ay hisse başına temettü", f"{tl(m['dps_ttm'])} TL"],
                        ["Temettü verimi", yz(m["temettu_verim"])], ["Dağıtım oranı (temettü / net kâr)", yz(m["dagitim_orani"])],
                        ["Temettü ödenen yıl sayısı (son 10 yıl)", str(len([y for y in yillar if y >= m['tarih'].year - 10]))],
                        ["Temettü YBBO (son ~4 yıl)", yz(tg)]], [W * .45, W * .2]))
        E += [Spacer(1, 6), _img(gt, W, 2.2 / 7.5)]
    else:
        E.append(Paragraph("Şirketin kayıtlı nakit temettü geçmişi bulunamadı.", ST["p"]))
    E.append(CondPageBreak(8 * cm)); E.append(Paragraph("7. Metodoloji ve Önemli Uyarılar", ST["h1"]))
    met = [
        f"<b>Veri:</b> Mali tablolar öncelikle İş Yatırım'ın KAP finansallarından derlediği tablolardan, alınamazsa Yahoo Finance'ten çekilir; fiyat, temettü ve analist verileri Yahoo Finance kaynaklıdır. Gecikme veya eksiklik olabilir. "
        "TMS 29 (enflasyon muhasebesi) kapsamında yeniden düzenlenen tablolar ile nominal tablolar arasında yıllar arası kıyaslama sapmaları olabilir.",
        "<b>Son 12 ay (TTM):</b> Gelir tablosu ve nakit akışı kalemleri son dört çeyreğin toplamıdır; bilanço kalemleri son açıklanan dönemdir.",
        f"<b>İNA (DCF):</b> {PARAM['DCF_YIL']} yıllık açık tahmin dönemi; hasılat büyümesi tarihsel bileşik büyümeden uç büyümeye doğrusal azalır, "
        f"serbest nakit akışı marjı son yılların medyanıdır. AOSM = Ke×E/(D+E) + Kd×(1−t)×D/(D+E), Ke = Rf ({yz(PARAM['RF'])}) + β × ERP ({yz(PARAM['ERP'])}). "
        f"Uç büyüme nominal TL bazında {yz(PARAM['TERMINAL_G'])} varsayılmıştır.",
        "<b>Emsal çarpanları:</b> Emsal grubunun medyan F/K, PD/DD ve FD/FAVÖK çarpanları şirket metriklerine uygulanır; aralık 1. ve 3. çeyrek değerleridir.",
        "<b>Gerekçeli PD/DD (finansallar):</b> (ROE − g)/(Ke − g). <b>Gordon:</b> D1/(Ke − g). <b>Graham:</b> √(22,5 × HBK × HBDD).",
        "<b>Sağlık skoru:</b> Kârlılık, reel büyüme, nakit akışı, finansal güç, fiyat momentumu ve göreli değer kategorilerinde eşik bazlı 1–5 puanlama.",
        "<b>Piotroski F-skoru</b> (0–9) temel iyileşmeyi, <b>Altman Z''</b> (gelişmekte olan piyasa versiyonu) iflas riskini ölçer.",
        "<b>UYARI:</b> Bu rapor otomatik bir model çıktısıdır; yatırım danışmanlığı kapsamında değildir ve alım-satım tavsiyesi içermez. "
        "Yatırım kararları kişisel risk ve getiri tercihlerinize uygun olarak, yetkili kuruluşlardan alınacak danışmanlıkla verilmelidir.",
    ]
    for x in met:
        E.append(Paragraph(x, ST["p"])); E.append(Spacer(1, 3))
    vk = m.get("veri") or {}
    v = [["Veri Kalitesi Kontrolü", "Durum"],
         ["Fiyat verisi tarihi", f"{vk.get('fiyat_tarihi'):%d.%m.%Y}" if vk.get("fiyat_tarihi") is not None else "–"],
         ["Son finansal dönem", (f"{vk['son_donem']:%d.%m.%Y} ({vk['gun']} gün önce)" if vk.get("son_donem") is not None else "–")],
         ["Kullanılabilir çeyrek / yıl sayısı", f"{vk.get('ceyrek', 0)} / {vk.get('yil', 0)}"],
         ["Eksik ana kalemler", ", ".join(vk.get("eksik") or []) or "Yok"],
         ["Finansal veri kaynağı", m.get("kaynak", "Yahoo Finance")],
         ["Para birimi", m.get("kur_notu") or "Finansallar ve fiyat aynı para biriminde (TL)"],
         ["Veri kalite puanı", f"{vk.get('puan', '–')}/100"]]
    E.append(KeepTogether([Spacer(1, 4), tablo(v, [W * .35, W * .65], font=7.4)]))
    doc.build(E, onFirstPage=sayfa, onLaterPages=sayfa)
    return dosya

# =====================================================================
# ANA FONKSİYON
# =====================================================================
def emsal_bul(kod, info):
    for grup, liste in SEKTOR_GRUPLARI.items():
        if kod in liste:
            return [x for x in liste if x != kod][:6], grup
    return [], None

def piyasa_degeri(kod):
    """İştirak piyasa değeri (TL). Hızlı kaynak: yfinance fast_info."""
    import yfinance as yf
    t = yf.Ticker(kod.upper() + ".IS")
    try:
        v = t.fast_info.get("market_cap") if hasattr(t.fast_info, "get") else t.fast_info.market_cap
        if v:
            return float(v)
    except Exception:
        pass
    info = t.info or {}
    return sayi(info.get("marketCap"))

def analiz_et(kod, emsal_kodlar="", veri_fn=None, endeks_fn=None, pd_fn=None, log=print, endeks=None, **param):
    """Veriyi çeker, tüm analizleri yapar; (d, m, emsaller, endeks) döndürür."""
    PARAM.update({k.upper(): v for k, v in param.items()})
    veri_fn = veri_fn or veri_cek; endeks_fn = endeks_fn or endeks_cek; pd_fn = pd_fn or piyasa_degeri
    kod = kod.upper().replace(".IS", "").strip()
    log(f"{kod} verileri çekiliyor...")
    d = veri_fn(kod)
    if endeks is None:
        try:
            endeks = endeks_fn()
        except Exception:
            endeks = None
    liste = [x.strip().upper() for x in emsal_kodlar.split(",") if x.strip()]
    if not liste:
        liste, grup = emsal_bul(kod, d["info"])
        if grup: log(f"Otomatik emsal grubu: {grup} → {', '.join(liste)}")
    emsaller = []
    for e in liste:
        try:
            log(f"Emsal verisi: {e}"); emsaller.append(metrikler(veri_fn(e, hafif=True), endeks))
        except Exception as ex:
            log(f"{e} atlandı ({ex})")
    log("Analiz ve değerleme yapılıyor...")
    m = metrikler(d, endeks)
    nav = nav_hesapla(kod, pd_fn) if kod in BV.HOLDING_PAYLARI else None
    degerleme(m, emsaller, nav); saglik(m); ipuclari(m)
    return d, m, emsaller, endeks

def rapor(kod, emsal_kodlar="", veri_fn=None, endeks_fn=None, log=print, klasor=".", detay=False, pd_fn=None, **param):
    d, m, emsaller, endeks = analiz_et(kod, emsal_kodlar, veri_fn, endeks_fn, pd_fn, log, **param)
    dosya = os.path.join(klasor, f"{m['kod']}_Arastirma_Raporu_{dt.date.today():%Y%m%d}.pdf")
    log("PDF oluşturuluyor...")
    pdf_olustur(d, m, emsaller, endeks, dosya)
    log(f"Tamamlandı: {dosya} | Adil değer {tl(m['adil'])} TL | Potansiyel {yz(m['potansiyel'])} | Skor {m['genel_skor']}")
    return (dosya, m) if detay else dosya

def grafikler(d, m, endeks):
    """Uygulama içinde gösterilecek grafiklerin PNG baytları."""
    out = {}
    for ad_, fn in (("saglik", lambda: g_saglik(m) if m["saglik"] else None),
                    ("degerleme", lambda: g_futbol(m)),
                    ("fiyat", lambda: g_fiyat(d["hist"], endeks, m["kod"])),
                    ("goreli", lambda: g_goreli(d["hist"], endeks, m["kod"])),
                    ("finansal", lambda: g_finansal(m))):
        try:
            b = fn()
            if b: out[ad_] = b.getvalue()
        except Exception:
            pass
    return out

def ozet_satir(m):
    return {"Kod": m["kod"], "Şirket": m["ad"], "Fiyat": m["fiyat"], "Adil değer": m["adil"],
            "Potansiyel": m["potansiyel"], "Sağlık skoru": m["genel_skor"], "F/K": m["fk"], "PD/DD": m["pddd"],
            "ROE": m["roe"], "Temettü verimi": m["temettu_verim"], "1Y getiri": m["r"].get("1Y"),
            "Görüş": m["gorus"], "Teknik": m["teknik_ozet"], "Veri puanı": (m.get("veri") or {}).get("puan"),
            "Kaynak": "İş Yatırım" if str(m.get("kaynak", "")).startswith("İş") else "Yahoo"}

def tara(kodlar, veri_fn=None, endeks_fn=None, pd_fn=None, isci=5, ilerleme=None, **param):
    """Birden çok hisseyi tarar, özet tablo döndürür. Emsaller tarama içindeki aynı sektör hisseleridir."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    PARAM.update({k.upper(): v for k, v in param.items()})
    veri_fn = veri_fn or veri_cek; pd_fn = pd_fn or piyasa_degeri
    try:
        endeks = (endeks_fn or endeks_cek)()
    except Exception:
        endeks = None
    ham, hatalar = {}, {}
    def is_(k):
        for deneme in range(2):
            try:
                return k, metrikler(veri_fn(k, hafif=True), endeks), None
            except Exception as ex:
                hata = ex
        return k, None, str(hata)
    with ThreadPoolExecutor(max_workers=isci) as ex:
        isler = [ex.submit(is_, k) for k in kodlar]
        for n, f in enumerate(as_completed(isler), 1):
            k, mm, h = f.result()
            if mm: ham[k] = mm
            else: hatalar[k] = h
            if ilerleme: ilerleme(n / len(kodlar), k)
    grup_of = {k: g for g, l in SEKTOR_GRUPLARI.items() for k in l}
    pdeg = {k: mm["piy_deg"] for k, mm in ham.items()}
    satirlar = []
    for k, mm in ham.items():
        emsal = [ham[e] for e in ham if e != k and grup_of.get(e) and grup_of.get(e) == grup_of.get(k)]
        nav = nav_hesapla(k, lambda x: pdeg.get(x) or pd_fn(x)) if k in BV.HOLDING_PAYLARI else None
        try:
            degerleme(mm, emsal, nav); saglik(mm)
            satirlar.append(ozet_satir(mm))
        except Exception as ex:
            hatalar[k] = str(ex)
    return satirlar, hatalar
