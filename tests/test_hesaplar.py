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


def test_gun_ici_tamamla_resmi_kapanisi_ezmez():
    """27.11.2026: Yahoo günlük XU100 kapanışı 10.977,01 (resmi, kapanış seansı dahil); son 15 dk mumu 10.970,81.
    Günlük bar varken gün içi fiyat kapanışı ezmemeli."""
    d = pd.DataFrame({"Open": [10737.18], "High": [11046.28], "Low": [10615.74], "Close": [10977.01], "Volume": [1]},
                     index=pd.to_datetime(["2026-11-27"]))
    gi = pd.DataFrame({"Open": [10950.0], "High": [10975.0], "Low": [10945.0], "Close": [10970.81], "Volume": [1]},
                      index=pd.DatetimeIndex(["2026-11-27 14:45"], tz="UTC"))
    assert MK.gun_ici_tamamla(d, gi, "XU100.IS").loc["2026-11-27", "Close"] == pytest.approx(10977.01)
    assert MK.gun_ici_tamamla(d["Close"], gi, "XU100.IS").iloc[-1] == pytest.approx(10977.01)


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


# ---------------------------------------------------------------- Aşama 9: risk hesaplayıcı ve sanal defter
def test_pozisyon_boyutu():
    import sanal as S
    # 100.000 TL, %1 risk, giriş 100, stop 95, komisyon/kayma yok → 1.000 TL / 5 = 200 adet
    r = S.pozisyon_boyutu(100_000, 0.01, 100, 95, komisyon=0, kayma=0, hedefler=(110,))
    assert r["adet"] == 200 and r["pozisyon"] == 20_000 and abs(r["gercek_risk"] - 1000) < 1e-9
    assert abs(r["hedef"][0]["kazanc"] - 2000) < 1e-9 and abs(r["hedef"][0]["r"] - 2) < 1e-9
    # maliyet dahil: birim risk 5 + 100×(0,004+0,001)=5,5 → 181 adet (aşağı yuvarlanır)
    assert S.pozisyon_boyutu(100_000, 0.01, 100, 95)["adet"] == 181
    # çok yakın stop: pozisyon portföyle sınırlanır
    r = S.pozisyon_boyutu(10_000, 0.02, 100, 99.9, komisyon=0, kayma=0)
    assert r["adet"] == 100 and r["uyari"]
    # kripto küsuratlı adet
    assert S.pozisyon_boyutu(1000, 0.01, 60000, 58000, komisyon=0, kayma=0, piyasa="kripto")["adet"] == 0.005
    import pytest as _pt
    with _pt.raises(ValueError): S.pozisyon_boyutu(1000, 0.01, 100, 105)          # AL'da stop girişin üstünde


def test_sanal_defter():
    import sanal as S
    d = S.bos_defter(100_000)
    a = S.islem_ac(d, "THYAO", "bist", 1, 100, 300, komisyon=0.001, stop=290, hedef=330)
    b = S.islem_ac(d, "ASELS", "bist", 1, 50, 320, komisyon=0)
    S.islem_kapat(d, a["id"], 320, adet=40)                     # kısmi
    assert abs(S.pozisyonlar(d)[0]["kalan"] - 60) < 1e-9
    S.islem_kapat(d, a["id"], 310)                              # kalan 60
    S.iptal(d, b["id"], "yanlış giriş")
    assert S.pozisyonlar(d) == []                               # iptal edilen açık sayılmaz
    k = S.kapananlar(d)[0]
    beklenen = 40 * 20 + 60 * 10 - (40 * (320 * 0.001 + 300 * 0.001) + 60 * (310 * 0.001 + 300 * 0.001))
    assert abs(k["gerceklesen"] - beklenen) < 1e-9 and k["R"] > 0
    assert len(d["olaylar"]) == 5                               # hiçbir kayıt silinmedi
    v = S.degerle(d, lambda kod: 999)
    assert abs(v["ozkaynak_tl"] - (100_000 + beklenen)) < 1e-9 and v["islem_sayisi"] == 1
    import pytest as _pt
    with _pt.raises(ValueError): S.islem_ac(d, "THYAO", "bist", -1, 1, 300)   # BIST'te açığa satış yok
    assert S.dogrula({"olaylar": []})["baslangic"] == 100_000


# ---------------------------------------------------------------- Aşama 10: kullanıcı tanımlı alarmlar
def test_alarm_kurallari_ayristirma():
    import alarm as AL
    K = AL.kurallar("THYAO EMA 20/50\nASELS HACIM > 2\nBTC/USDT FIB 0.618\nGARAN DESTEK\nTUPRS DİRENÇ\nAKBNK KIRILIM\n"
                    "XU100 FVG\nNVDA.US BOS\nETH/USDT HARMONİK\nKCHOL SİNYAL\nTHYAO TEMEL\nTAKVİM USD\nTAKVIM\nPORTFÖY RİSK 8\nTHYAO > 350")
    tip = [k["tip"] for k in K]
    assert tip == ["ema", "hacim", "fib", "destek", "direnc", "kirilim", "fvg", "bos", "harmonik", "sinyal", "temel", "takvim", "takvim", "pfrisk", "fiyat"]
    assert K[0]["hizli"] == 20 and K[0]["yavas"] == 50 and K[1]["deger"] == 2 and K[11]["kod"] == "USD" and abs(K[13]["deger"] - 0.08) < 1e-12


def test_teknik_alarm_ema_kesisimi():
    import numpy as np, pandas as pd, alarm as AL, bist_teknik as T
    # düşüş sonra son mumda sert yükseliş: EMA5, EMA10'u yukarı keser
    c = np.r_[np.linspace(120, 100, 80), [100.5, 101, 120]]
    h = pd.DataFrame({"Open": c, "High": c * 1.01, "Low": c * 0.99, "Close": c, "Volume": np.r_[np.full(82, 1000.0), [5000.0]]},
                     index=pd.bdate_range("2026-06-01", periods=len(c)))
    g = T.tf_analiz(h, "G")
    olay = AL.teknik_alarm({"tip": "ema", "kod": "TEST", "hizli": 5, "yavas": 10}, g)
    assert olay and olay[0][0] == "🟢" and "yukarı kesti" in olay[0][1]
    hv = AL.teknik_alarm({"tip": "hacim", "kod": "TEST", "deger": 2.0}, g)
    assert hv and hv[0][0] == "📊"
    assert AL.teknik_alarm({"tip": "hacim", "kod": "TEST", "deger": 9.0}, g) == []


def test_tatil_ve_yarim_gun():
    import datetime as dt, veri_kalite as VK
    U = dt.timezone.utc
    # 27.11.2026: ABD 13:00 ET (18:00 UTC) erken kapanış; 18:30 UTC'de kapalı, son kapanış 18:00 UTC
    t = dt.datetime(2026, 11, 27, 18, 30, tzinfo=U)
    assert VK.piyasa_acik("abd", t) is False and VK.piyasa_acik("abd", dt.datetime(2026, 11, 27, 17, 0, tzinfo=U)) is True
    assert VK.etiket("2026-11-27T18:00:00+00:00", "abd", t)["durum"] == "gün sonu"
    assert VK.piyasa_acik("abd", dt.datetime(2026, 11, 26, 16, 0, tzinfo=U)) is False        # Şükran Günü
    assert VK.piyasa_acik("bist", dt.datetime(2026, 10, 29, 9, 0, tzinfo=U)) is False        # 29 Ekim
    assert VK.piyasa_acik("bist", dt.datetime(2026, 10, 28, 10, 30, tzinfo=U)) is False      # 13:30 TSİ, yarım gün bitti


def test_igne_seviyeleri():
    import numpy as np, igne as IG
    # yatay seyir: 61.000 civarı, altında süpürülmemiş iki dip (60.830 ve 60.640), üstte seviye yok
    C = np.full(60, 61900.0); H = C + 60; L = C - 60
    L[20] = 60640; L[40] = 60830; C[-1] = 61990; H[-1] = 62010
    u = IG.uyari(H, L, C)
    assert u and u["yon"] == -1 and 60830 in u["seviyeler"] and 60640 in u["seviyeler"]
    b, a = IG.metin(u)
    assert "aşağı iğne" in b and "60.830" in a and "yatırım tavsiyesi değildir" in a


def test_igne_tetik():
    import numpy as np, igne as IG
    # seviyelere doğru düşüş ivmesi: tetiklenir
    C = np.r_[np.full(57, 61900.0), [61700.0, 61500.0, 61200.0]]; H = C + 60; L = C - 60
    L[20] = 60640; L[40] = 60830
    u = IG.tetik(H, L, C)
    assert u and u["yon"] == -1 and "düşüş" in u["neden"]
    # aynı seviyeler ama fiyat yatay / yukarı gidiyor: tetiklenmez (sürekli uyarı yok)
    C2 = np.r_[np.full(57, 61100.0), [61150.0, 61200.0, 61250.0]]; H2 = C2 + 60; L2 = C2 - 60
    L2[20] = 60640; L2[40] = 60830
    assert IG.tetik(H2, L2, C2) is None


def test_qd_kabul_ve_tetik():
    """Aşama 10b: kabul listesi yüklenir, betikler depoda, tetik hem ana hem yan iş parçacığında çalışır."""
    import os, threading
    import firsat as F, qd_calistir as Q, bist_teknik as T
    assert F.QD_KABUL and all(os.path.exists(os.path.join(Q.KLASOR, q["dosya"])) for l in F.QD_KABUL.values() for q in l)
    rng = np.random.default_rng(5); idx = pd.date_range("2022-01-01", periods=700)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.025, len(idx)))); o = c * (1 + rng.normal(0, .005, len(idx)))
    d = pd.DataFrame({"Open": o, "High": np.maximum(o, c) * 1.01, "Low": np.minimum(o, c) * .99, "Close": c,
                      "Volume": np.full(len(idx), 1e5)}, index=idx)
    A = F.diziler(d, T.gostergeler(d)); M = F.ayna(A, 1); q = F.qd_kurulumlar("kripto", "G", 1)[0]
    m, st = F.qd_tetik(d, M, q, 1)
    assert m.sum() > 0 and len(st) == len(m)
    sonuc = {}
    F._QD_ONB.clear()
    th = threading.Thread(target=lambda: sonuc.setdefault("m", F.qd_tetik(d, M, q, 1)[0])); th.start(); th.join()
    assert sonuc["m"].sum() == m.sum()


def test_rejim_durum_makinesi():
    """Aşama 10c: düzeltme → ralli denemesi → takip günü (FTD) → yükseliş; dağıtım günleri sayılır."""
    import rejim as RJ
    idx = pd.bdate_range("2024-01-01", periods=330)
    c = list(np.linspace(100, 130, 240))                     # yükseliş
    c += list(np.linspace(130, 105, 40))                     # sert düşüş (düzeltme)
    c += [106, 107, 107.5, 109.5]                            # ralli: 4. gün +%1,9
    c += list(np.linspace(110, 118, 330 - len(c)))
    c = np.array(c); v = np.full(len(c), 1e6); v[283] = 2e6   # FTD günü hacim artışı
    h = pd.DataFrame({"Open": c, "High": c * 1.005, "Low": c * 0.995, "Close": c, "Volume": v}, index=idx)
    S, son = RJ.durum_makinesi(h, 0.0125, 0.07)
    assert "duzeltme" in set(S["durum"]) and "ralli" in set(S["durum"])
    assert son["durum"] == "yukselis" and son["ftd"] == str(idx[283].date())
    # dağıtım: hacim artışıyla %0,2+ düşüş
    h2 = h.copy(); cc = h2["Close"].to_numpy().copy(); vv = h2["Volume"].to_numpy().copy()
    for i in (320, 323, 326, 328):
        cc[i] = cc[i - 1] * 0.995; vv[i] = vv[i - 1] * 1.5
    h2["Close"] = cc; h2["Low"] = cc * 0.995; h2["Volume"] = vv
    _, son2 = RJ.durum_makinesi(h2, 0.0125, 0.07)
    assert son2["dagitim"] == 4 and son2["durum"] == "baski"
    p, neden, _ = RJ.maruziyet(son2, None, vix=35)
    assert p == 40 and any("VIX" in x for x in neden)


def test_disiplin_kontrol_sigorta_gunluk():
    """Aşama 10c-3: kontrol listesi, düşüş sigortası (dd ve ardışık kayıp), işlem günlüğü, haftalık özet."""
    import sanal as SN
    d = SN.bos_defter(100_000)
    v = SN.degerle(d, lambda k: 100.0)
    # stopsuz ve nedensiz işlem engellenir
    k = SN.kontrol_listesi(d, v, "THYAO", "bist", 1, 100, None, None, 100, neden="")
    assert k["engel"] and {m["ad"] for m in k["maddeler"] if m["durum"] == "hata"} == {"Stop belirlendi", "Nedeni yazdım"}
    # düzgün işlem: risk %0,5, K/R 1:2,5, rejim %80 → engel yok
    k = SN.kontrol_listesi(d, v, "THYAO", "bist", 1, 100, 95, 112.5, 100, rejim={"maruziyet": 80, "durum_ad": "Onaylı yükseliş"},
                           neden="BIST günlük kırılım fırsatı")
    assert not k["engel"] and k["puan"] == 100
    # risk sınırı: %3 risk → hata
    k = SN.kontrol_listesi(d, v, "THYAO", "bist", 1, 100, 90, 130, 300, neden="deneme işlemi")
    assert any(m["ad"] == "İşlem riski" and m["durum"] == "hata" for m in k["maddeler"])
    # 3 ardışık zarar → sigorta
    for i in range(3):
        o = SN.islem_ac(d, f"K{i}", "bist", 1, 100, 100, 0, 95, 110, aciklama="test"); SN.islem_kapat(d, o["id"], 95)
    s = SN.dusus_sigortasi(d)
    assert s["aktif"] and s["ardisik"] == 3
    v = SN.degerle(d, lambda k: 100.0)
    k = SN.kontrol_listesi(d, v, "THYAO", "bist", 1, 100, 95, 112.5, 100, neden="bir işlem daha")
    assert any(m["ad"] == "Düşüş sigortası" and m["durum"] == "hata" for m in k["maddeler"])
    # dd sigortası: tek büyük zarar %12
    d2 = SN.bos_defter(100_000); o = SN.islem_ac(d2, "X", "bist", 1, 1000, 100, 0, 90); SN.islem_kapat(d2, o["id"], 88)
    assert SN.dusus_sigortasi(d2)["aktif"] and SN.dusus_sigortasi(d2)["dd"] > 0.11
    # günlük + haftalık özet
    kap = SN.kapananlar(d)
    SN.gunluk_ekle(d, kap[0]["id"], plana_uydum=False, duygu="Korku", ders="stopu erken kaydırdım")
    SN.gunluk_ekle(d, kap[1]["id"], plana_uydum=True, duygu="Sakin / planlı")
    h = SN.haftalik_ozet(d)
    assert h["kapanan"] == 3 and h["degerlendirilen"] == 2 and h["kazanma"] == 0 and abs(h["ort_R"] + 1) < 1e-9
    assert h["plana_uyum"] == 0.5 and any("değerlendirilmedi" in x for x in h["oneri"])
    SN.dogrula(d)   # "not" olayları geçerli
