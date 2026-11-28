"""Aşama 10c-1: piyasa rejimi paneli (BIST ve ABD). Ücretsiz veriyle; kapanış taramasının analizlerini yeniden kullanır.

- Piyasa genişliği: 50 ve 200 günlük ortalamanın üstündeki hisse oranı, 52 haftalık yeni zirve / yeni dip sayısı.
- Dağıtım günleri (O'Neil): endeks %0,2+ düşer ve hacim önceki günden yüksektir. Son 25 seansta sayılır; endeks o günün
  kapanışının %5 üstüne çıkarsa gün düşer. Takip günü (FTD) sonrası sayım sıfırlanır.
- Durum makinesi: Yükseliş → (4+ dağıtım) Baskı altında yükseliş → (6+ dağıtım ya da 50 günlüğün altında ve tepeden sert düşüş)
  Düzeltme → (ilk yükseliş günü) Ralli denemesi → (4. gün ve sonrası, eşik üstü artış + hacim artışı = FTD) Yükseliş.
  Ralli denemesi sırasında düzeltmenin dibi kırılırsa deneme biter. Takip gününden sonraki 25 seansta yükseliş yalnız ralli dibi
  kırılırsa ya da 6 dağıtım günü birikirse bozulur (endeks o sırada henüz 50 günlüğün altında olabilir).
- Tepe uyarısı: endeks zirveye %3 yakınken genişlik 20 günde 15+ puan bozulduysa ve 4+ dağıtım günü varsa.
- Maruziyet koçu: duruma, genişliğe, tepe uyarısına (ABD'de VIX'e) göre önerilen hisse oranı %0–100.
Yatırım tavsiyesi değildir; yöntem claude-trading-skills (MIT) fikirlerinden uyarlanmıştır.
"""
import json, os, datetime as dt
import numpy as np
import pandas as pd

AYAR = {"bist": {"ftd": 0.015, "dd": 0.10, "endeks": "BIST 100"}, "abd": {"ftd": 0.0125, "dd": 0.07, "endeks": "S&P 500"}}
DURUM_AD = {"yukselis": "Onaylı yükseliş", "baski": "Baskı altında yükseliş", "duzeltme": "Düzeltme", "ralli": "Ralli denemesi"}
DURUM_RENK = {"yukselis": "yesil", "baski": "altin", "duzeltme": "kirmizi", "ralli": "altin"}
TABAN = {"yukselis": 80, "baski": 50, "ralli": 30, "duzeltme": 15}


# ------------------------------------------------------------------ genişlik
def genislik(kapanislar, gun=130):
    """kapanislar: {kod: Close serisi (günlük)} → DataFrame(tarih: ust50, ust200, zirve, dip, n) son `gun` seans."""
    C = pd.DataFrame({k: s[~s.index.duplicated()] for k, s in kapanislar.items() if s is not None and len(s) >= 60}).sort_index()
    # Tek tük hissenin tatil/hafta sonu günündeki başıboş satırı (ör. Kurban Bayramı 30–31.05.2026) tüm hisseleri o gün boş bırakıyor,
    # 200 günlük ortalamayı 200 seans boyunca herkes için hesaplanamaz yapıyordu (genişlik %0 görünüyordu): yalnız seans günleri kalsın.
    say = C.notna().sum(axis=1)
    C = C[say >= 0.5 * say.max()]
    C = C.ffill(limit=3)
    s50 = C.rolling(50, min_periods=50).mean(); s200 = C.rolling(200, min_periods=200).mean()
    yz = C.rolling(252, min_periods=120).max(); yd = C.rolling(252, min_periods=120).min()
    var50 = s50.notna() & C.notna(); var200 = s200.notna() & C.notna()
    G = pd.DataFrame({
        "ust50": (C > s50).where(var50).sum(axis=1) / var50.sum(axis=1).replace(0, np.nan),
        "ust200": (C > s200).where(var200).sum(axis=1) / var200.sum(axis=1).replace(0, np.nan),
        "zirve": ((C >= yz) & yz.notna()).sum(axis=1), "dip": ((C <= yd) & yd.notna()).sum(axis=1),
        "n": C.notna().sum(axis=1)})
    return G.dropna(subset=["ust50"]).tail(gun)


# ------------------------------------------------------------------ dağıtım günleri + durum makinesi
def durum_makinesi(h, ftd_esik=0.0125, dd_esik=0.08, dagitim_esik=-0.002):
    """h: endeks günlük OHLCV → her gün için durum + son gün ayrıntıları."""
    h = h.dropna(subset=["Close"]).copy()
    C = h["Close"].to_numpy(float); L = h["Low"].to_numpy(float); n = len(C)
    V = h["Volume"].fillna(0).to_numpy(float) if "Volume" in h else np.zeros(n)
    hacim_var = (V[-60:] > 0).mean() > 0.8
    s50 = pd.Series(C).rolling(50, min_periods=50).mean().to_numpy()
    s200 = pd.Series(C).rolling(200, min_periods=200).mean().to_numpy()
    tepe63 = pd.Series(C).rolling(63, min_periods=20).max().to_numpy()
    bas = min(220, n - 1)
    durum = "duzeltme" if np.isfinite(s200[bas]) and C[bas] < s200[bas] else "yukselis"
    dip = L[bas]; ralli_bas = None; ftd_i = None; dag = []   # dağıtım günü indeksleri
    seri = []
    for i in range(bas + 1, n):
        r = C[i] / C[i - 1] - 1
        if hacim_var and r <= dagitim_esik and V[i] > V[i - 1]: dag.append(i)
        # 25 seans penceresi, %5 yükselişle düşen günler, FTD sonrası sıfırlama
        dag = [j for j in dag if i - j < 25 and C[i] < C[j] * 1.05 and (ftd_i is None or j > ftd_i)]
        say = len(dag)
        if durum in ("yukselis", "baski"):
            dd = 1 - C[i] / tepe63[i] if np.isfinite(tepe63[i]) else 0
            taze_ftd = ftd_i is not None and i - ftd_i <= 25   # takip gününden sonraki 25 seans: yalnız ralli dibi kırılırsa bozulur
            if say >= 6 or (taze_ftd and L[i] < dip) or (not taze_ftd and np.isfinite(s50[i]) and C[i] < s50[i] and dd >= dd_esik):
                durum, dip, ralli_bas = "duzeltme", L[i], None
            else:
                durum = "baski" if say >= 4 else "yukselis"
        else:
            if L[i] < dip:
                dip, durum, ralli_bas = L[i], "duzeltme", None
            elif durum == "duzeltme" and r > 0:
                durum, ralli_bas = "ralli", i
            elif durum == "ralli":
                gun = i - ralli_bas + 1
                if gun >= 4 and r >= ftd_esik and (V[i] > V[i - 1] or not hacim_var):
                    durum, ftd_i, dag = "yukselis", i, []
        seri.append((h.index[i], durum, say))
    S = pd.DataFrame(seri, columns=["tarih", "durum", "dagitim"]).set_index("tarih")
    son = {"durum": durum, "dagitim": len(dag), "dagitim_gunleri": [str(h.index[j].date()) for j in dag],
           "ftd": str(h.index[ftd_i].date()) if ftd_i is not None else None,
           "ralli_gunu": (n - ralli_bas) if durum == "ralli" and ralli_bas is not None else None,
           "kapanis": float(C[-1]), "degisim": float(C[-1] / C[-2] - 1),
           "sma50_ust": bool(np.isfinite(s50[-1]) and C[-1] > s50[-1]), "sma200_ust": bool(np.isfinite(s200[-1]) and C[-1] > s200[-1]),
           "tepeye_uzaklik": float(1 - C[-1] / np.nanmax(C[-252:])), "hacim_var": bool(hacim_var)}
    return S, son


def maruziyet(son, G, vix=None):
    """→ (önerilen hisse oranı %, gerekçeler, tepe_uyarisi)."""
    p = TABAN[son["durum"]]; neden = [f"{DURUM_AD[son['durum']]}: taban %{p}"]
    tepe = False
    if G is not None and len(G):
        u50 = float(G["ust50"].iloc[-1]); u200 = float(G["ust200"].iloc[-1]) if np.isfinite(G["ust200"].iloc[-1]) else None
        if u50 >= 0.60: p += 10; neden.append(f"genişlik güçlü (hisselerin %{u50 * 100:.0f}'i 50 günlüğün üstünde): +10")
        elif u50 <= 0.35: p -= 10; neden.append(f"genişlik zayıf (yalnız %{u50 * 100:.0f}'i 50 günlüğün üstünde): −10")
        if u200 is not None and u200 < 0.40: p -= 10; neden.append(f"uzun vade zayıf (%{u200 * 100:.0f}'i 200 günlüğün üstünde): −10")
        if len(G) > 20:
            bozulma = float(G["ust50"].iloc[-21] - u50)
            if son["tepeye_uzaklik"] <= 0.03 and bozulma >= 0.15 and son["dagitim"] >= 4:
                tepe = True; p -= 20
                neden.append(f"TEPE UYARISI: endeks zirveye yakınken genişlik 20 günde {bozulma * 100:.0f} puan bozuldu: −20")
    if vix is not None:
        if vix >= 30: p -= 10; neden.append(f"VIX {vix:.0f} (korku yüksek): −10")
        elif vix <= 15: p += 5; neden.append(f"VIX {vix:.0f} (sakin): +5")
    p = int(max(0, min(100, round(p / 10) * 10)))
    return p, neden, tepe


def ozet_cumle(piyasa, r):
    ad = AYAR[piyasa]["endeks"]
    s = f"{ad}: {DURUM_AD[r['durum']]}"
    if r["durum"] in ("yukselis", "baski"): s += f" · {r['dagitim']} dağıtım günü"
    if r["durum"] == "ralli" and r.get("ralli_gunu"): s += f" · ralli {r['ralli_gunu']}. gün (takip günü bekleniyor)"
    if r.get("genislik"): s += f" · genişlik %{r['genislik']['ust50'] * 100:.0f}"
    return s + f" · önerilen hisse oranı %{r['maruziyet']}"


# ------------------------------------------------------------------ ana giriş
def hesapla(piyasa, analizler, endeks_h, klasor=None, vix=None):
    """analizler: teknik_bulten.SON[piyasa]['analizler'] (her biri tf.G.h içerir); endeks_h: endeks günlük OHLCV."""
    kap = {}
    for s in analizler or []:
        try: kap[s["kod"]] = s["tf"]["G"]["h"]["Close"]
        except Exception: pass
    G = genislik(kap) if kap else None
    S, son = durum_makinesi(endeks_h, AYAR[piyasa]["ftd"], AYAR[piyasa]["dd"])
    p, neden, tepe = maruziyet(son, G, vix)
    r = {**son, "piyasa": piyasa, "endeks": AYAR[piyasa]["endeks"], "durum_ad": DURUM_AD[son["durum"]], "maruziyet": p,
         "gerekce": neden, "tepe_uyarisi": tepe, "vix": vix, "zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    if G is not None and len(G):
        g = G.iloc[-1]
        r["genislik"] = {"ust50": float(g["ust50"]), "ust200": float(g["ust200"]) if np.isfinite(g["ust200"]) else None,
                         "zirve": int(g["zirve"]), "dip": int(g["dip"]), "n": int(g["n"]),
                         "ust50_20g_once": float(G["ust50"].iloc[-21]) if len(G) > 20 else None}
        r["gecmis"] = {"tarih": [str(x.date()) for x in G.index], "ust50": [round(float(x), 4) for x in G["ust50"]],
                       "ust200": [round(float(x), 4) if np.isfinite(x) else None for x in G["ust200"]],
                       "zirve": [int(x) for x in G["zirve"]], "dip": [int(x) for x in G["dip"]]}
    Sx = S.tail(130)
    r["durum_gecmis"] = {"tarih": [str(x.date()) for x in Sx.index], "durum": list(Sx["durum"]),
                         "kapanis": [round(float(x), 2) for x in endeks_h["Close"].reindex(Sx.index)]}
    r["ozet"] = ozet_cumle(piyasa, r)
    if klasor:
        os.makedirs(os.path.join(klasor, "rejim"), exist_ok=True)
        json.dump(r, open(os.path.join(klasor, "rejim", f"{piyasa}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return r


def vix_al():
    try:
        import yfinance as yf
        return float(yf.Ticker("^VIX").history(period="5d")["Close"].dropna().iloc[-1])
    except Exception:
        return None


def _tr_tarih(s):
    try: return dt.date.fromisoformat(s).strftime("%d.%m.%Y")
    except Exception: return s or ""


def durum_alt(r):
    """Dağıtım sayısı ve takip günü yalnız yükseliş dönemlerinde anlamlıdır; düzeltme/rallide rallinin günü ve beklenen şart yazılır."""
    if r["durum"] in ("yukselis", "baski"):
        return f"{r['dagitim']} dağıtım günü (son 25 seans)" + (f" · takip günü {_tr_tarih(r['ftd'])}" if r.get("ftd") else "")
    if r["durum"] == "ralli":
        esik = {"bist": "%1,5", "abd": "%1,25"}.get(r.get("piyasa"), "")
        return (f"Ralli denemesinin {r.get('ralli_gunu') or '?'}. günü · yeni yükseliş için 4. günden sonra hacimli {esik}+ artış (takip günü) gerekli; "
                f"düzeltme dibi kırılırsa deneme biter")
    return "Endeks düzeltmede · ilk yükseliş günüyle ralli denemesi başlar"


def kart_ciz(r, yol):
    import kart as K
    g = r.get("genislik") or {}
    tr = lambda x: f"%{x * 100:.0f}" if x is not None else "–"
    renk = K.C.get({"yesil": "yesil", "altin": "altin", "kirmizi": "kirmizi"}[DURUM_RENK[r["durum"]]], K.C["altin"])
    bol = [{"baslik": "DURUM", "renk": renk, "satirlar": [
               {"sol": r["durum_ad"], "sag": f"%{r['maruziyet']} hisse", "sag_renk": renk, "nokta": renk,
                "alt": durum_alt(r)}]},
           {"baslik": "PİYASA GENİŞLİĞİ", "renk": K.C["altin"], "satirlar": [
               {"sol": "50 günlüğün üstündeki hisseler", "sag": tr(g.get("ust50")),
                "alt": f"20 gün önce {tr(g.get('ust50_20g_once'))}" if g.get("ust50_20g_once") is not None else ""},
               {"sol": "200 günlüğün üstündeki hisseler", "sag": tr(g.get("ust200"))},
               {"sol": "52 haftalık yeni zirve / yeni dip", "sag": f"{g.get('zirve', '–')} / {g.get('dip', '–')}"}]},
           {"baslik": "MARUZİYET KOÇU", "renk": K.C["altin"], "satirlar": [{"sol": x.split(":")[0], "alt": x.split(":", 1)[1].strip() if ":" in x else ""}
                                                                         for x in r["gerekce"]]}]
    if r.get("tepe_uyarisi"):
        bol.insert(0, {"baslik": "TEPE UYARISI", "renk": K.C["kirmizi"], "satirlar": [{"sol": "Genişlik bozuluyor, dağıtım artıyor", "nokta": K.C["kirmizi"]}]})
    K.bildirim_karti(f"PİYASA REJİMİ  ·  {r['endeks'].upper()}", r["durum_ad"], f"Önerilen hisse oranı %{r['maruziyet']} · kapanış {r['kapanis']:,.0f}".replace(",", "."),
                     bol, yol, vurgu=renk, not_="Kural tabanlı bir değerlendirmedir, yatırım tavsiyesi değildir.", baslik_logo=(r["endeks"], None))
    return yol


def telegram(piyasa, r, klasor, bot, onceki=None):
    try:
        yol = kart_ciz(r, os.path.join(klasor, "rejim", f"{piyasa}.png"))
        alt = f"🧭 <b>Piyasa rejimi</b> · {r['ozet']}"
        if onceki and onceki.get("durum") != r["durum"]:
            alt += f"\n🔄 Durum değişti: {DURUM_AD.get(onceki['durum'], onceki['durum'])} → <b>{r['durum_ad']}</b>"
        if r.get("tepe_uyarisi"): alt += "\n⚠️ Tepe uyarısı: genişlik bozuluyor, dağıtım günleri artıyor."
        bot.foto(yol, alt, f"rejim:{piyasa}:{dt.date.today()}", 30)
    except Exception as ex:
        print("rejim kartı:", ex)
