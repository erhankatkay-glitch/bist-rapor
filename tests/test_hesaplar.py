"""Hesap doğruluğu testleri (ağ gerektirmez). Çalıştırma: python -m pytest -q"""
import numpy as np
import pandas as pd
import pytest

import bist_makro as MK
import firsat as F
import logolar as LG
import ses as SES


def _seri(n=300, tohum=1, egim=0.0):
    r = np.random.default_rng(tohum)
    c = 100 * np.exp(np.cumsum(r.normal(egim, 0.01, n)))
    o = c * np.exp(r.normal(0, 0.003, n))
    h = np.maximum(o, c) * 1.004
    l = np.minimum(o, c) * 0.996
    return pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c, "Volume": r.uniform(1e5, 1e6, n)},
                        index=pd.date_range("2025-01-01", periods=n, freq="D"))


# ---------------------------------------------------------------- veri tazeliği
def test_gun_ici_tamamla_eksik_gunleri_ekler():
    d = pd.DataFrame({"Open": [1.0, 2.0], "High": [1.0, 2.0], "Low": [1.0, 2.0], "Close": [1.0, 2.0], "Volume": [10, 10]},
                     index=pd.to_datetime(["2026-11-23", "2026-11-24"]))
    gi = pd.DataFrame({"Open": [3.0, 3.1, 4.0], "High": [3.5, 3.2, 4.5], "Low": [2.9, 3.0, 3.9], "Close": [3.1, 3.15, 4.25], "Volume": [1, 1, 2]},
                      index=pd.DatetimeIndex(["2026-11-25 07:00", "2026-11-25 14:45", "2026-11-26 07:00"], tz="UTC"))
    out = MK.gun_ici_tamamla(d, gi, "XU100.IS")
    assert list(out.index.strftime("%Y-%m-%d")) == ["2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26"]
    assert out.loc["2026-11-25", "Close"] == pytest.approx(3.15)
    assert out.loc["2026-11-25", "High"] == pytest.approx(3.5)
    assert out.loc["2026-11-26", "Close"] == pytest.approx(4.25)


def test_gun_ici_tamamla_eski_gunlere_dokunmaz():
    s = pd.Series([1.0, 2.0], index=pd.to_datetime(["2026-11-23", "2026-11-24"]))
    gi = pd.DataFrame({"Open": [9.0], "High": [9.0], "Low": [9.0], "Close": [9.0], "Volume": [1]},
                      index=pd.DatetimeIndex(["2026-11-20 10:00"], tz="UTC"))
    assert MK.gun_ici_tamamla(s, gi, "^GSPC").tolist() == [1.0, 2.0]


# ---------------------------------------------------------------- fırsat motoru
def test_simule_stop_ve_hedef():
    H = [10, 10.5, 11.6, 12.5, 13.5]; L = [9.5, 9.8, 10.2, 11.0, 12.0]; C = [10, 10.3, 11.4, 12.2, 13.2]
    R, asama, sebep = F.simule(H, L, C, 0, 10.0, 9.0, (1.0, 2.0, 3.0), 10, O=None) or (None, None, None)
    assert asama == 3 and sebep == "hedef"
    assert R == pytest.approx(0.5 * 1 + 0.3 * 2 + 0.2 * 3)


def test_simule_bosluklu_stop_acilistan_cikar():
    H = [10, 10.1, 8.6]; L = [9.8, 9.6, 8.0]; C = [10, 9.9, 8.2]; O = [10, 9.95, 8.5]
    R, asama, sebep = F.simule(H, L, C, 0, 10.0, 9.0, (1.0, 2.0, 3.0), 10, O=O)
    assert sebep == "stop" and R == pytest.approx((8.5 - 10) / 1.0)


def test_rejim_yonleri():
    assert F.rejim(_seri(egim=0.004)) == 1
    assert F.rejim(_seri(egim=-0.004)) == -1


def test_pa_ozellik_ileriye_bakmaz():
    d = _seri(400, 3)
    A = F.diziler(d, __import__("bist_teknik").gostergeler(d)); M = F.ayna(A, 1)
    t = 300; stop = float(M["Close"][t] * 0.97)
    once = F.pa_ozellik(M, stop, t)
    # t sonrasını bozmak t anındaki sonucu değiştirmemeli
    M2 = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in M.items()}
    for k in ("Open", "High", "Low", "Close"): M2[k][t + 1:] = M2[k][t + 1:] * 3
    assert F.pa_ozellik(M2, stop, t) == once


def test_filtre_yapilandirmasi_gecerli():
    for (pz, tf), f in F.FILTRE.items():
        assert pz in ("bist", "kripto", "abd", "emtia") and tf in ("4S", "G", "H", "A")
        assert set(f) <= {"rejim", "yapi", "mum", "oda", "kume"}


# ---------------------------------------------------------------- logolar
@pytest.mark.parametrize("kod,pz,beklenen", [("THYAO", "bist", "THYAO.IS"), ("AAPL.US", "abd", "AAPL"), ("BRK.B.US", "abd", "BRK-B"),
                                              ("BTC/USDT", "kripto", None), ("ALTIN", "emtia", None)])
def test_hisse_sembol(kod, pz, beklenen):
    assert LG.hisse_sembol(kod, pz) == beklenen


def test_endekste_logo_yok():
    assert LG.hisse_logo_url("XU100", "bist") is None and LG.hisse_logo_url("XU030", "bist") is None


def test_kripto_logo_bulur():
    assert LG.kripto_logo("BTC/USDT") and LG.kripto_logo("ETH/USDT@OKX")


# ---------------------------------------------------------------- sesli özet okunuşu
@pytest.mark.parametrize("x,beklenen", [(0, "sıfır"), (1100, "bin yüz"), (1234567, "bir milyon iki yüz otuz dört bin beş yüz altmış yedi")])
def test_tam_oku(x, beklenen):
    assert SES.tam_oku(x) == beklenen


def test_normalle_kisaltma_ve_yuzde():
    t = SES.normalle("ABD'de S&P 500 +%0,4 yükseldi, VIX 16")
    assert "Amerika" in t and "Es en Pi beş yüz" in t and "yüzde sıfır virgül dört" in t and "viks" in t
    assert "%" not in t and "&" not in t


def test_ek_de_unlu_uyumu():
    assert SES.ek_de("on altı otuz") == "on altı otuzda"
    assert SES.ek_de("on yedi") == "on yedide"
    assert SES.ek_de("on üç") == "on üçte"


# ---------------------------------------------------------------- ortak biçimler
def test_yuzde_bicimi():
    import bicim, haber
    assert bicim.yuzde(0.0123) == "+%1,2" and bicim.yuzde(-0.05) == "−%5,0" and bicim.yuzde(None) == "–"
    assert F.yz(0.0123) == haber.yz(0.0123) == "+%1,2"
    assert F.yz(0.0123, isaret=False) == "%1,2"


def test_sayi_bicimi():
    import bicim
    assert bicim.sayi(10953.15) == "10.953" and bicim.sayi(50.783) == "50,78" and bicim.sayi(float("nan")) == "–"


# ---------------------------------------------------------------- haber yönü
@pytest.mark.parametrize("baslik,beklenen", [("REEDR bedelsiz sermaye artırımı başvurusunu geri çekti", True),
                                             ("THYAO temettü dağıtmayacak", True), ("KCHOL pay geri alımı yaptı", False),
                                             ("ASELS yeni sözleşme imzaladı", False)])
def test_haber_olumsuzlama(baslik, beklenen):
    import haber
    assert haber.olumsuzlama(baslik) is beklenen


# ---------------------------------------------------------------- Aşama 6: veri kalite etiketi + TCMB
def test_veri_kalite_etiketleri():
    import datetime as dt
    import veri_kalite as VK
    U = dt.timezone.utc
    # Cuma 27.11.2026 15:00 TSİ = 12:00 UTC: BIST açık
    simdi = dt.datetime(2026, 11, 27, 12, 0, tzinfo=U)
    assert VK.etiket(simdi - dt.timedelta(minutes=20), "bist", simdi)["durum"] == "gecikmeli"
    assert VK.etiket(simdi - dt.timedelta(hours=3), "bist", simdi)["durum"] == "bayat"
    assert VK.etiket(simdi - dt.timedelta(minutes=5), "kripto", simdi)["durum"] == "anlık"
    assert VK.etiket(simdi - dt.timedelta(hours=5), "kripto", simdi)["durum"] == "bayat"
    # Cumartesi: BIST kapalı, cuma 18:10 TSİ (15:10 UTC) verisi "gün sonu"
    cmt = dt.datetime(2026, 11, 28, 10, 0, tzinfo=U)
    assert VK.etiket(dt.datetime(2026, 11, 27, 15, 10, tzinfo=U), "bist", cmt)["durum"] == "gün sonu"
    assert VK.etiket(dt.datetime(2026, 11, 25, 15, 10, tzinfo=U), "bist", cmt)["durum"] == "bayat"
    # ABD: cuma kapanış 16:00 NY = 21:00 UTC; cumartesi "gün sonu"
    assert VK.etiket("2026-11-27T21:00:00+00:00", "abd", cmt)["durum"] == "gün sonu"
    assert VK.etiket(None, "abd", cmt)["durum"] == "bayat"
    assert VK.piyasa_acik("emtia", dt.datetime(2026, 11, 28, 12, tzinfo=U)) is False      # cumartesi
    assert VK.tur_bul("XU100.IS") == "bist" and VK.tur_bul("BTC-USD") == "kripto" and VK.tur_bul("GC=F") == "emtia"
    assert VK.tur_bul("TRY=X") == "doviz" and VK.tur_bul("^TNX") == "faiz" and VK.tur_bul("^GSPC") == "abd"


def test_tcmb_tablolari():
    import makro_tr as MT
    html = ("<table><tr><th>Ay-Yıl</th><th>TÜFE (Yıllık % Değişim)</th><th>TÜFE (Aylık % Değişim)</th></tr>"
            "<tr><td>10-2026</td><td>29.77</td><td>2.58</td></tr><tr><td>09-2026</td><td>29.73</td><td>1.84</td></tr></table>"
            "<table><tr><td>10-2026</td><td>27.00</td><td>1.00</td></tr></table>")   # ikinci tablo (ÜFE) alınmaz
    t = MT.tufe_coz(html)
    assert [r["donem"] for r in t] == ["2026-10", "2026-09"] and t[0]["yillik"] == 29.77 and t[0]["aylik"] == 2.58
    f = MT.faiz_coz("<table><tr><th>Tarih</th><th>Borç Alma</th><th>Borç Verme</th></tr>"
                    "<tr><td>11.09.2026</td><td>-</td><td>40.50</td></tr><tr><td>23.10.2026</td><td>-</td><td>39.50</td></tr></table>")
    assert f["oran"] == 39.5 and f["tarih"] == "2026-10-23" and f["onceki"] == 40.5
    m = {"tufe": {"seri": t}, "faiz": f, "reel_faiz": round((1.395 / 1.2977 - 1) * 100, 2)}
    assert MT.ozet_satiri(m) == "TÜFE %29,77 (Ekim 2026) · Politika faizi %39,50 · Reel faiz +%7,5"


# ---------------------------------------------------------------- Aşama 7: harmonik, SMC, göstergeler
def _yapay(n=900, tohum=3):
    import numpy as np, pandas as pd
    r = np.random.default_rng(tohum)
    c = 100 * np.exp(np.cumsum(r.normal(0, 0.02, n))); o = c * np.exp(r.normal(0, 0.005, n))
    return pd.DataFrame({"Open": o, "High": np.maximum(o, c) * np.exp(abs(r.normal(0, 0.01, n))),
                         "Low": np.minimum(o, c) * np.exp(-abs(r.normal(0, 0.01, n))), "Close": c,
                         "Volume": r.integers(1000, 5000, n).astype(float)}, index=pd.date_range("2022-01-01", periods=n))


def test_harmonik_oranlar():
    import teknik_ek as TE
    # Gartley: X=100, A=200, B=138.2 (0.618), C=176.4 (BC/AB 0.618) → D ≈ 121.4 (0.786 XA)
    ad = {a: (lo, hi) for a, lo, hi in TE.harmonik_aday(100, 200, 138.2, 176.4)}
    assert "Gartley" in ad and ad["Gartley"][0] <= 121.4 <= ad["Gartley"][1]
    assert "Bat" not in ad                                   # B 0.618: yarasa için fazla derin
    # Bat: B=0.45, D=0.886
    ad = {a: (lo, hi) for a, lo, hi in TE.harmonik_aday(100, 200, 155, 185)}
    assert "Bat" in ad and ad["Bat"][0] <= 111.4 <= ad["Bat"][1]
    # Crab: D X'in altında (1.618)
    ad = {a: (lo, hi) for a, lo, hi in TE.harmonik_aday(100, 200, 138.2, 185)}
    assert "Crab" in ad and ad["Crab"][1] < 100
    assert TE.abcd_aday(200, 150, 180)[0][0] == "ABCD"
    assert TE.harmonik_aday(100, 90, 95, 97) == []           # A, X'in altında: geçersiz


def test_yeni_kurulumlar_ileriye_bakmaz():
    """t'ye kadar kesilmiş veriyle hesaplanan tetikler, tam veriyle hesaplananlarla t öncesinde aynı olmalı."""
    import numpy as np, bist_teknik as T, firsat as F
    h = _yapay()
    def tet(d):
        G = T.gostergeler(d); A = F.diziler(d, G); out = {}
        for y in (1, -1):
            for k, (m, s) in F.tetikler(F.ayna(A, y), ek={"OB", "BREAKER", "HARM"}).items():
                if k in ("OB", "BREAKER", "HARM"): out[(k, y)] = (m, s)
        return out
    tam = tet(h)
    for kes in (500, 650, 800):
        kisa = tet(h.iloc[:kes])
        for anahtar, (m, s) in kisa.items():
            assert np.array_equal(m, tam[anahtar][0][:kes]), (anahtar, kes)
            assert np.allclose(s[m], tam[anahtar][1][:kes][m]), (anahtar, kes)


def test_gostergeler_ek():
    import numpy as np, pandas as pd, teknik_ek as TE
    s = pd.Series(np.arange(1, 31, dtype=float))
    assert abs(TE.wma(s, 3).iloc[2] - (1 * 1 + 2 * 2 + 3 * 3) / 6) < 1e-9
    assert abs(TE.hma(s, 9).iloc[-1] - 30) < 1e-6            # doğrusal seride HMA gecikmesizdir
    v = pd.Series([100.0] * 25 + [300.0])
    assert abs(TE.rvol(v).iloc[-1] - 3.0) < 1e-9
    h = _yapay(50)
    ha = TE.heikin_ashi(h)
    assert np.allclose(ha["Close"], (h["Open"] + h["High"] + h["Low"] + h["Close"]) / 4)
    assert (ha["High"] >= ha[["Open", "Close"]].max(axis=1) - 1e-9).all()
