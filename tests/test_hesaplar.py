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
