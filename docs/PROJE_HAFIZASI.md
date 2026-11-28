# KATKAY YATIRIM A.Ş. — Proje hafızası

Bu dosya her aşamada güncellenir. Amaç: neyin nerede olduğunu, hangi kararların alındığını ve sıradaki işi tek yerde tutmak.

## Değişmeyen kurallar
- Ücretsiz kalır: ücretli API, lisans, abonelik veya sunucu yok.
- Tasarım: siyah-altın KATKAY teması (kullanıcı kararı, 27.11.2026).
- Gizli bilgiler (Telegram, ileride Gemini anahtarı) yalnız GitHub Secrets'ta durur; kodda ve kayıtlarda yer almaz.
- Takas/AKD lisanslıdır, kazınmaz. KAP'ın iç API'si kullanılmaz.
- Çalışan özellik izinsiz kaldırılmaz. Her değişiklik gerçek veriyle (test dalında GitHub Actions) denenir, sonra ana dala alınır.
- Aşama aşama ilerlenir; her aşama sonunda kullanıcı onayı alınır.

## Mimari özet
- **Uygulama:** Streamlit (`app.py`, görünüm `uygulama_stil.py`), Streamlit Cloud'da çalışır. Ağır hesap yapmaz; GitHub Actions'ın ürettiği çıktıları `bulten` dalından okur.
- **Zamanlanmış işler:** GitHub Actions. Çıktılar `yayinla.py` ile yetim `bulten` dalına yazılır (her birim kendi klasörü).
- **Bildirim:** Telegram (`tg.py`: sessiz gönderim, süre sonunda otomatik silme).
- **Veri kaynakları:** Yahoo Finance (yfinance), Binance (data-api.binance.vision) ve OKX, İş Yatırım (mali tablolar), KAP/Borsa İstanbul açık dosyaları, TCMB (haftalık menkul kıymet istatistikleri), ForexFactory takvimi, haber RSS'leri.

## Zamanlanmış işler (TSİ)
| İş | Zaman | Ne yapar |
|---|---|---|
| alarm.yml | 30 dakikada bir | Fiyat alarmları, haber etkisi, yabancı akışı, eski mesajları silme |
| kapanis_bist.yml | 14:17 ve 18:26, hafta içi | 4 saatlik ve günlük fırsatlar, açık kurulum takibi, kapanış bülteni |
| kapanis_abd.yml | ABD 13:34 ve 16:12 ET | Aynısı, ABD için |
| kapanis_kripto.yml | 4 saatte bir | Kripto fırsatları ve takip |
| kapanis_emtia.yml | 4 saatte bir + 01:12 | Emtia fırsatları, günlük bülten |
| sabah_ozet.yml | 09:00 her gün | Sabah kartı + sesli özet (Merve ve Erhan) |
| sabah_raporu.yml | 08:17 hafta içi | Takip listesindeki hisselerin PDF raporları, yabancı oranı toplama |
| backtest.yml | Pazar 09:41 | Skor gruplarının geçmiş testi |

## Modüller
| Modül | Görev |
|---|---|
| bist_teknik.py | Çok zaman dilimli teknik analiz motoru (göstergeler, formasyonlar, destek/direnç, puan) |
| firsat.py | Fırsat motoru: kurulum bulma, işlem planı, takip, performans |
| kapanis.py | Kapanış sonrası çalıştırıcı (fırsat turu, takip, kartlar) |
| teknik_bulten.py | Piyasa geneli kapanış bülteni (PDF + kart) |
| bist_rapor.py | Temel analiz ve değerleme (hisse raporu) |
| bist_varlik.py | Emtia ve kripto analizi |
| bist_kripto.py, bist_abd.py, bist_evren.py, bist_veri.py | Evrenler ve semboller |
| bist_makro.py | Piyasa paneli (+ `gun_ici_tamamla`: geride kalan günlük barları tamamlar) |
| haber.py | Haber sınıflandırma ve piyasa tepkisi, ekonomik takvim |
| alarm.py | Fiyat alarmları (`anlik`: son fiyat ve günlük değişim) |
| sabah.py, ses.py | Sabah kartı ve sesli özet |
| yabanci_akis.py | TCMB haftalık yabancı akışı |
| kart.py, tasarim.py, bist_teknik_rapor.py, ileri_rapor.py, analist.py | Telegram kartları ve PDF tasarımı |
| portfoy.py | Portföy analizi |

## Aşama 1 — Bulgular (27.11.2026)

### Veri doğruluğu
1. **Düzeltildi — BIST 100 bir gün geride.** Yahoo'nun XU100 günlük verisi bazı günler son günü içermiyor. Uygulama 26.11 gecesi 24.11 kapanışını (10.966, −%1,25) gösterdi; doğrusu 10.655,74 (−%2,83). Artık eksik günler 15 dakikalık veriden tamamlanıyor (`bist_makro.gun_ici_tamamla`). Bunu piyasa paneli, kapanış bültenleri ve alarmlar kullanıyor.
2. **Düzeltildi — BIST kapanış bülteni atlanıyordu.** Aynı gecikme yüzünden bülten "tatil" sanılıp üretilmiyordu. Uygulamadaki "BIST son kapanış özeti" bu yüzden eksikti.
3. **Düzeltildi — Alarmlarda eski altın fiyatı.** Vadeli altın ve gümüşte (GC=F, SI=F) 15 dakikalık akış tatil sonrası durdu. Alarm gram altını 2 gün önceki fiyatla 5.911 TL hesapladı; panel 6.035 TL gösteriyordu. Artık iki yol da aynı sonucu veriyor.
4. **Açık — Gram altın vadeli fiyattan hesaplanıyor.** Türkiye'deki gram altın spot onsa dayanır; vadeli ile spot arasında küçük bir fark olur. Ücretsiz ve güvenilir bir spot kaynağı bulunursa değiştirilecek (Stooq artık çalışmıyor).
5. **Açık — Tatil sonrası "günlük değişim".** ABD tatilinde (26.11) vadeli metallerin "günlük" değişimi iki seansı kapsıyor. Kartlarda bu durumun belirtilmesi gerekiyor.

### Fırsat motoru (Aşama 2'nin konusu)
- Kapanan 19 kurulumun 18'i stop oldu (toplam −17 R). 18'i kripto, çoğu 4 saatlik "düşüş trendinde tepki satışı".
- Nedenler: piyasa rejimi (Bitcoin yönü) filtresi yok; price action teyidi yok; stoplar 4 saatlik kripto oynaklığına göre dar.
- Tokenize hisseler (XQQQ, QQQB) kripto taramasına giriyordu (25.11'de filtrelendi).

### Telegram tasarımı (Aşama 4)
Henüz düz metin giden bildirimler:
- `kapanis.py` fırsat metni (grafik yoksa)
- `alarm.py` yedek metni
- `haber.py` haber etkisi yedek metni ve takvim yedek metni
- `teknik_bulten.py` ve `yabanci_akis.py` yedek metinleri

### Tekrarlanan veri çekme
- Yahoo'dan veri çeken 11 modül var. Ortak bir veri ve önbellek katmanı yok; aynı sembol farklı işlerde ayrı ayrı indiriliyor.
- Hedef: tek bir veri katmanı (Aşama 5).

### Dış kaynak denemeleri
- ortakalan.io/mcp otomatik erişimi engelliyor (Cloudflare 1010, "tekrar denemeyin"). Enflasyon için TCMB'nin açık sayfası önerildi.
- Binance ana adresi GitHub sunucularından 451 veriyor; sistem zaten data-api.binance.vision kullanıyor.
- OmniRoute GitHub Actions'ta çalışıyor ama ücretsiz bir sağlayıcı anahtarı (Gemini) olmadan yanıt üretmiyor.

## Aşama 2 — Fırsat motoru (27.11.2026, ilk adım)
Araştırma aracı: `arastirma_firsat.py`. Mevcut kurulumların tüm geçmiş olaylarını önerilen teyitlerle ve teyitsiz karşılaştırır. Aşırı uyuma karşı her filtre hem eski hem yeni yarıda ayrı ayrı kontrol edildi.

| Piyasa | Olay | Teyitsiz ort. R | Seçilen filtre | Filtreli ort. R (eski / yeni yarı) |
|---|---|---|---|---|
| Kripto 4S | 8.135 | +0,005 | BTC yönü + yapı + mum + oda + toplu sinyal değil | +0,104 (+0,077 / +0,170) |
| Kripto G | 4.644 | +0,010 | BTC ters değil + yapı | +0,058 (+0,070 / +0,047) |
| BIST G | 17.910 | +0,048 | BIST 100 yönü | +0,250 (+0,359 / +0,115) |

- BIST'te SAT kurulumları geçmişte açıkça zararlı (GERI SAT −0,67 R); BIST zaten yalnız AL tarıyor.
- 26.11'deki kripto kaybı tam olarak "toplu sinyal" durumuydu: aynı mumda 12 coin aynı yönde.
- Canlıya alındı: `firsat.FILTRE`, `firsat.pa_ozellik`, `firsat.rejim`; `kapanis.REJIM`. Fırsat kartlarının teyit listesinde yeni maddeler görünür.
- İkinci tur testleri (ABD 197 hisse, BIST 4S, BIST/ABD haftalık, emtia):

| Piyasa | Olay (AL) | Teyitsiz | Seçilen filtre | Filtreli (eski / yeni yarı) |
|---|---|---|---|---|
| BIST 4S | 9.618 | +0,138 | BIST 100 ters değil + yapı | +0,163 (+0,162 / +0,164) |
| ABD G | 14.705 | +0,065 | S&P 500 ters değil | +0,073 (+0,041 / +0,097) |
| ABD H | 3.225 | +0,181 | S&P 500 aynı yönde | +0,219 (+0,237 / +0,208) |
| BIST H | 2.343 | +0,377 | filtre yok (hiçbiri iyileştirmedi) | — |
| Emtia G | 1.104 | +0,102 | filtre yok (hiçbiri iyileştirmedi) | — |

- SAT yönü ABD, emtia ve BIST'te her filtreyle zararlı (ABD G −0,14, ABD H −0,23, emtia −0,14, BIST H −0,23); bu piyasalarda SAT taranmaya devam etmeyecek (zaten taranmıyordu).
- Aylık (A) dilimde örnek az; filtre yok.

## Kod haritası (graphify, 27.11.2026)
- graphify GitHub Actions'ta yalnızca kod modunda çalıştırıldı (yapay zekâ anahtarı gerekmez; kod dışarı gitmez): 44 dosya, 1.379 düğüm, 2.799 bağlantı, 54 alt sistem.
- En merkezi dosyalar: bist_rapor.py, app.py, kapanis.py, bist_varlik.py, tasarim.py, firsat.py.
- Aynı işi gören tekrarlı yardımcılar (Aşama 5'te tek yere toplanacak):
  - Biçimleme: yz(), _img(), _png(), _yon()
  - Analiz girişleri: tara(), analiz()

## Aşama 3 — Raporlar (27.11.2026)
- `durum_raporu.py` + `durum_raporu.yml` (her gün 09:41 TSİ):
  - cumartesi haftalık, ayın 1'i aylık rapor.
  - 10 varlık: BIST 100, BIST 30, Dolar/TL, S&P 500, Nasdaq, VIX, ons altın, ons gümüş, Brent, BTC.
  - Kart + PDF Telegram'a gider; `donem/` altında yayınlanır; uygulamada Piyasalar sekmesinde görünür.
- Elle tetik: `.github/tetik/durum` dosyasına `haftalik` ya da `aylik` yazıp main'e push.
- BIST kapanış özeti: uygulama zaten gösteriyordu; eksikliğin sebebi Yahoo gecikmesiyle atlanan bültendi (Aşama 1'de düzeldi).
- Logolar:
  - Kripto: spothq/cryptocurrency-icons (CC0) uygun.
  - Hisse logoları (BIST + ABD): logo.dev ücretsiz plan, publishable anahtar `logolar.LOGO_DEV`. 12/12 test hissesinde gerçek logo geldi.
  - Kişisel kullanımda atıf gerekmiyor; ticari kullanıma geçilirse sayfaya "Logos provided by Logo.dev" bağlantısı eklenmeli.
  - Gizli anahtar (sk_) kullanılmaz; kullanıcıya yenilemesi söylendi.

## Aşama 4 — Telegram tasarımı (27.11.2026)
- Bildirimlerin hepsi KATKAY kartıyla gidiyor:
  - fırsat, toplu fırsat, takip, karne, portföy uyarısı
  - alarm, haber etkisi, takvim
  - kapanış bülteni, yabancı akışı, sabah özeti, durum raporu
- Düz metin yalnızca kart çizilemezse son çare.
- Fırsat kartı: yeni teyitler gösteriliyor ve kart teyit satırı arttıkça uzuyor. Grafik çizilemezse `kapanis.sade_firsat_gonder` grafiksiz kart gönderir.
- Kripto logoları: `logolar.py` + `varlik/kripto/` (CC0).

## Aşama 5 — Arayüz ve kod sağlığı (27.11.2026)
- Uygulama dört ana bölümde; alt menü bunlara gidiyor:
  - Ana Sayfa: Piyasalar, Haberler, Takvim
  - Keşfet: Fırsatlar, Hisse, Teknik, Tarayıcı, Emtia & Kripto, Bebek, Karşılaştır
  - Portföy: Varlıklarım, Performans
  - Takip: Favoriler, Alarmlar
- Ana sayfa: yatay piyasa şeridi (`mini_kart`), günün fırsatları (`gunun_firsatlari`, `firsat_mini`).
- Varlık sayfası (Keşfet › Teknik): `varlik_baslik`, `seviye_karti`, `katkay_notu`. Stiller `uygulama_stil.py` içinde (.vb, .sv, .kn, .mk, .fk).
- Testler: `tests/test_hesaplar.py` (pytest).
  - Kapsam: veri tazeliği, işlem simülasyonu (boşluklu stop dahil), rejim, ileriye bakmama, logolar, sesli özet okunuşu, biçimler.
  - Her push'ta `testler.yml` içinde ruff (tanımsız ad, sözdizimi) ile birlikte çalışır.
- Ortak biçimler: `bicim.py` (yuzde, sayi). firsat.yz, haber.yz ve durum_raporu bunu kullanır.
- Veri katmanı kararı: ayrı bir katman kurulmadı.
  - Uygulamada her veri okuması `st.cache_data` ile zaten önbellekte.
  - GitHub işleri birbirinden bağımsız süreçler; aynı süreç içinde aynı veri iki kez indirilmiyor.
  - Gerçek sorun veri tazeliğiydi; o `gun_ici_tamamla` ile tek yerde çözüldü.
- Arayüz testleri GitHub Actions'ta gerçek tarayıcıyla (playwright, 390 px telefon) yapıldı.

## Sıradaki aşamalar
1. ~~Aşama 1: envanter ve veri denetimi~~ (bu dosya)
2. Aşama 2: Fırsat motoru
   - Rejim filtresi, price action ve piyasa yapısı teyidi, oynaklığa göre stop, 100 puanlık model.
   - Her kural geçmiş testle doğrulanır (vectorbt).
3. Aşama 3: Yeni raporlar
   - BIST kapanış özeti uygulamada.
   - 10 varlık için haftalık ve aylık durum raporu, hedef fiyatlarla.
4. Aşama 4: Tüm Telegram bildirimleri KATKAY tasarımında.
5. ~~Aşama 5: 4 ana bölüm, varlık sayfası, testler (pytest, ruff)~~
6. Gemini anahtarı eklenince: yapay zekâ yorumu (OmniRoute üzerinden ya da doğrudan).

## 27 Kasım 2026
- Kripto logoları artık logo.dev'den (`logolar.kripto_logo_url`); hata olursa yerel CC0 set.
- Tüm Telegram kartlarında satır başında varlık logosu (`bildirim_karti` satırında "logo": (kod, piyasa)).
  Endeks ve emtiada logo yok, renkli nokta kalır.
  Kapsam: alarm, takip, toplu fırsat, haber, durum raporu.
- Tema altın-siyah (`.streamlit/config.toml`); radyolar hap görünümünde.
- Ana sayfa üstüne boğa-ayı görseli geri eklendi (`.hk`, `varlik/hero.jpg`).
- 32 bölümlük talimatın eksik analizi ve yeni aşamalar: `docs/YOL_HARITASI.md`.

## Aşama 6 (27 Kasım 2026)
- `veri_kalite.py`: her fiyata anlık / gecikmeli / kapanış / bayat etiketi; seans saatleri (BIST, ABD, emtia/döviz 24/5, kripto 7/24).
  Ayrıca kaynak + yedek tablosu (`KAYNAKLAR`).
- `bist_makro.piyasa_paneli`: her kalemde zaman (UTC), kaynak ve tür var.
  Bitcoin ve Ethereum için birincil kaynak Binance (anlık), yedek Yahoo.
- `makro_tr.py`: TCMB'nin herkese açık tablolarından TÜFE (yıllık/aylık) ve politika faizi; reel faiz hesabı.
  Yedekler: EVDS, ardından son kayıtlı değer ("bayat").
  Sabah özeti işi her gün `makro/tr_makro.json`'u bülten dalına yazar.
- Uygulama:
  - Mini kartlarda etiket.
  - Ana sayfada "Türkiye makro" kartı.
  - Takip altında "Veri kaynakları ve gecikmeler".
  - Model enflasyonu TCMB'den otomatik alınır.
- Telegram sabah özetine "Türkiye: TÜFE … · Politika faizi … · Reel faiz …" maddesi eklendi.
- Doğrulama (27.11):
  - TCMB'den TÜFE %29,77 (Ekim) ve faiz %36 (23.10) çekildi; faiz haberlerle teyitli.
  - ABD 10Y faizi Yahoo'da 25.11'de kalmış, doğru biçimde "bayat" etiketlendi.

## Aşama 7 (27 Kasım 2026)
- `teknik_ek.py`:
  - Göstergeler: WMA, HMA, Heikin Ashi, RVOL.
  - ATR zigzag (teyitli salınımlar).
  - Harmonik formasyonlar: Gartley, Bat, Butterfly, Crab, Deep Crab, Shark, Cypher, AB=CD; tolerans `TOL`.
  - Emir bloğu (aktif / test edildi / geçersiz), kırıcı blok, eşit tepe/dip, premium/iskonto.
  - Test: kesilmiş veriyle tam veri aynı tetikleri veriyor, yani geleceğe bakmıyor.
- Geçmiş test (Actions, 6 piyasa/dilim, 100 bin+ olay). Canlıda açılanlar `firsat.EK_KURULUM`'da:
  - BIST G: OB, BREAKER, HARM (AL).
  - BIST 4S: BREAKER, HARM.
  - ABD G/H: BREAKER, HARM.
  - Kripto G: HARM SAT.
  - Kripto 4S'te hiçbiri tutmadı.
  - RVOL ayrı filtre olmadı; mevcut "Hacim x" teyidiyle aynı bilgi.
- Analiz sayfası ve PDF:
  - SMC çipleri, grafikte OB kutuları, harmonik PRZ ve eşit tepe/dip çizgileri.
  - Heikin Ashi seçeneği.
  - Sinyaller kart görünümünde.
- Alarmlar: "Yeni formasyon / kırılım" alarmı ve portföy uyarıları harmonik, emir bloğu ve kırıcı blok sinyallerini de kapsıyor.
- Ana sayfa düğmeleri: "Analiz" Keşfet › Hisse araştırma raporunu açar; "Seviye" Keşfet › Teknik'in seviyeler bölümünü açar.

## Fiyat düzeltmesi (27 Kasım 2026 akşam)
- Sorun: BIST'in resmi kapanışı 18:00–18:10 kapanış seansında oluşur, Yahoo'nun 15 dk ve 1 dk verisinde bu seans yok.
  `gun_ici_tamamla` ve `canli_guncelle`, günlük bardaki doğru kapanışı gün içi son fiyatla eziyordu.
  Örnek: XU100 10.970,81 yerine 10.977,01; THYAO 313 yerine 314.
- Düzeltme:
  - Günlük bar varsa gün içi veri yalnız eksik günleri tamamlar.
  - `canli_guncelle` piyasa kapalıyken dokunmaz.
  - `alarm.anlik` günlük kapanışı esas alır.
  - Kapanış işinde saatlik BIST verisinin son mumuna resmi kapanış yazılır (`kapanis.resmi_kapanis_uygula`).
- Altın: Yahoo GC=F vadeli, spotun yaklaşık %1 üstünde.
  Ons altın artık Binance PAXG (spot); GC=F serisi spota ölçekleniyor (`bist_makro.altin_spot_olcekle`).
  Gram altın = spot ons × USD/TRY ÷ 31,1035. Kapalıçarşı fiyatı yerel prim nedeniyle yaklaşık %1–1,5 yüksek olabilir.
- Doğrulama (Actions, 27.11 akşam):
  - Endeksler: XU100 10.977,01 (+%2,18), XU030 13.763,83 (+%2,31); ikisi de resmi kapanışla aynı.
  - Hisseler: THYAO 314, ASELS 332, GARAN 138,10, BIMAS 370,75, TUPRS 330, KCHOL 189,40, AKBNK 59,95.
- Bilinen: Gümüş ve petrol vadeli kontrat; ABD'de Şükran Günü'nde (26.11) günlük bar olmadığı için günlük değişim iki günlük.

## Aşama 8 ve Telegram düzeltmesi (27 Kasım 2026)
- `tarayici.py`: her kapanış bülteni `tarama/<piyasa>.csv` yazar (yayinla ALT_BIRIM'de "tarama", dosya bazında birleşir).
  - Sütunlar: fiyat, değişim, hacim, RVOL, RSI, ATR%, ADX, EMA sırası, yapı, günlük/haftalık görünüm ve çoklu zaman uyumu, RS, Fib, destek/direnç uzaklığı, FVG, BOS/CHoCH, likidite süpürme, emir bloğu, harmonik, premium/iskonto.
  - Son sinyal: kurulum, tarih, fiyat, yaş, sinyalden beri değişim.
- Uygulama Keşfet › Tarayıcı › "Teknik tarama":
  - Piyasa seçimi, 9 hazır şablon, istediğin koşulları VE ile birleştirme, sıralama.
  - Satırdan teknik analize geçiş.
  - Şablon kaydetme: adres satırında `?tarama=` olarak saklanır.
- İlk tablolar Actions'ta üretildi (BIST 628, ABD, kripto, emtia).
- Telegram:
  - Kart açıklaması 1000 karakterden HTML etiketinin ortasından kesiliyordu. Telegram kartı reddediyor, sistem düz metne düşüyordu (haber etkisi).
  - Düzeltme: `tg.guvenli_aciklama` (satır sonundan keser, açık etiketleri kapatır) ve HTML hatasında düz metinle tekrar deneme.
  - Açıklamalar tek satırlık başlık ve bağlantılar oldu; içerik kartta.
  - Kartlarda mavi/turkuaz yerine altın. Sabah kartındaki alt boşluk kırpılıyor.

## Aşama 9 (27 Kasım 2026)
- `sanal.py`:
  - `pozisyon_boyutu`: risk tutarı = portföy × risk %; birim risk = stop mesafesi + giriş × (2×komisyon + kayma).
    Adet piyasaya göre aşağı yuvarlanır (BIST/ABD tam adet, kripto 6 hane). Pozisyon portföyü aşarsa sınırlanır; hedeflerin R'si hesaplanır.
  - Sanal defter yalnız ekleme mantığında: açılış, kısmi/tam kapanış, iptal (silme yok).
    Değerleme `alarm.anlik` fiyatıyla; USD pozisyonlar USD/TRY ile TL'ye çevrilir.
- Saklama:
  - Defter yalnız cihazın tarayıcı deposunda (localStorage "katkay_sanal").
  - İlk açılışta gizli kutu `kk_sanal` üzerinden Python'a aktarılır (yeniden denemeli); her değişiklikte depoya yazılır.
  - JSON yedek indirme/yükleme var. GitHub'a ya da sunucuya hiçbir şey yazılmaz.
- Uygulama:
  - Portföy › "Sanal işlem" ve "Risk hesaplayıcı" sekmeleri.
  - Fırsat kartlarında "Sanal işlem aç" (plan aktarılır, %1 riske göre adet önerilir).
  - Teknik analiz sonucunda "Pozisyon büyüklüğü hesapla" (giriş = fiyat, stop = en yakın destek, ATR stop önerileri, hedef = dirençler).
- Test (Actions, telefon görünümü):
  - İşlem açıldı, sayfa yenilendi, işlem cihaz deposundan geri geldi.
  - Hesaplayıcı: 100.000 TL, %1, 314/300 → 64 adet, risk 996 TL.

## Aşama 10 (27 Kasım 2026)
- `alarm.kurallar` yeni sözdizimi:
  - Teknik: `KOD EMA 20/50`, `KOD HACIM > 2`, `KOD FIB 0.618`, `KOD DESTEK|DIRENC|KIRILIM`, `KOD FVG`, `KOD BOS`, `KOD HARMONIK`, `KOD SINYAL`.
  - Diğer: `KOD TEMEL`, `TAKVIM [ÜLKE]`, `PORTFOY RISK 10`.
- `alarm.teknik_alarm` günlük `tf_analiz` çıktısından değerlendirir.
  - Mum kapanmadıysa mesaja "kapanış teyidi bekleniyor" eklenir.
  - Aynı olay aynı gün tekrar gönderilmez (durum anahtarı).
- Diğer türlerin çalışması:
  - TEMEL: İş Yatırım'daki son dönem günde bir kontrol edilir.
  - TAKVIM: bülten dalındaki `haber/takvim.json`'dan, açıklamaya 75 dk kala.
  - PORTFOY RISK: portfoy.txt toplam zararı.
- Alarm geçmişi 300 kayıt; uygulamada arama var. Kural ekleme ekranı tüm türleri kapsar.
- Varsayılan kurallara `TAKVIM` eklendi.
- Kuru çalıştırma (Actions, gerçek veri): 13 kural 15 sn; ikinci turda tekrar bildirim 0.


## Aşama 10b — QuantDinger göstergeleri (28.11.2026)
- `qd_calistir.py`: QuantDinger betiklerini (df/params → output.signals) varsayılan ayarla çalıştırır; ana iş parçacığında 8 sn zaman aşımı.
- `arastirma_qd.py` + `.github/workflows/qd_arastirma.yml`: boyama (gerçek zaman) testi, tarih eşlemeli Monte Carlo, 4 dönem kontrolü, BH-FDR, kör %20.
- Kabul edilen 12 gösterge `qd_kabul.json`'da; betikler `qd_kutuphane/` (NOTICE + Apache-2.0).
- Bağlı olduğu yerler: fırsat motoru (`firsat.varlik_tara` → kapanış taramaları, Telegram fırsat kartları, Seçki, Günün fırsatları,
  portföy ters sinyal uyarısı), tarayıcı (`tarayici.son_sinyal` → SINYAL alarmı), teknik analiz gösterge karnesi ve sinyal listesi
  (`bist_teknik.tf_analiz(..., tur)` → uygulama Teknik sekmesi ve teknik PDF), PDF sözlüğü, portföy alarmında ters sinyal anahtarı "QD:".

## Aşama 10c (28.11.2026)
- `rejim.py`: kapanis.rejim_turu (BIST/ABD kapanış bülteninden sonra) → `rejim/{p}.json` (yayinla ALT_BIRIM'de), kart değişimde/Cuma.
  Uygulama: rejim_paneli (Ekonomi; kısa satır Seçki ve Günün fırsatları), sabah.py izlenecekler maddesi.
- `teknik_ek.vcp_tetik / momentum_tetik / ep_tetik` → `firsat.tetikler(ek=...)`; açık olanlar EK_KURULUM'da.
  Bağlı yerler: fırsat motoru (kapanış, Telegram kartı, Seçki, Günün fırsatları, kurulum istatistikleri, portföy SAT uyarısı),
  tarayıcı + SINYAL alarmı, teknik analiz karnesi/sinyal listesi (firsat.yeni_kurulum_durumu → tf_analiz), PDF sözlüğü, alarm anahtarı "Kurulum:".
- arastirma_qd.py: R [−5, +3] kırpılır, bozuk fiyatlı varlıklar atlanır (±%60 günlük sıçrama / ≤0 fiyat).
- Disiplin araçları: sanal.kontrol_listesi / dusus_sigortasi / gunluk_ekle ("not" olayı, ref) / haftalik_ozet; defter["ayar"].
  Açılışta "kontrol" (puan + uyarılar) olaya yazılır; stop ve neden zorunlu, diğer kırmızılar "bilerek esnetiyorum" onayıyla.

## Aşama 11 (28.11.2026)
- korelasyon.py (sabah_ozet.yml adımı) → korelasyon/ozet.json; app.korelasyon_bolumu (Ekonomi); sabah.izlenecekler kırılma maddesi;
  bist_teknik.goreceli_satirlar (tf_analiz G, tur ile) → karne + PDF. Sayfa dili "tr" (CSS büyük harfte İ).

## Anlık emtia (28.11.2026, kullanıcı isteği; Firecrawl değerlendirmesi sonrası)
- Firecrawl/firecrawl-mcp-server değerlendirildi: genel web kazıyıcı, piyasa verisi yok; BIST anlık veri lisanslı → kazınmaz (kural).
  Firecrawl AGPL-3.0 ve ağır öz-barındırma (Playwright, Redis, RabbitMQ, PostgreSQL); kullanılmadı.
- canli_emtia.py: OKX / Bitget herkese açık TradFi sürekli vadeli kontratları (GUMUS, PLATIN, BAKIR, WTI, DOGALGAZ); Yahoo'ya göre %10 sapma
  ve 15 dk tazelik koruması, yedek Yahoo. Binance XAU/XAG ABD'den 451 (kullanılmaz); Bybit 403. Brent için açık anlık kaynak yok.
  Bağlı: bist_makro.piyasa_paneli (kaynak "OKX/Bitget 7/24 türev", tur kripto), alarm.anlik, app.ana_satirlar emtia satırları, veri_kalite.KAYNAKLAR.

## Yorum katmanı (28.11.2026)
- llm_katman.py: Gemini (ücretsiz katman, GEMINI_API_KEY; açık "flash" modeli API'den seçilir) → yedek Groq (GROQ_API_KEY).
  Anahtarlar YALNIZ Streamlit Secrets / GitHub Secrets'ta; kullanıcıdan değer istenmez. Modele yalnız herkese açık piyasa raporu gider.
  dogrula(): çıktıdaki her sayı girdide geçmeli, yoksa metin atılır. app.ekip_yorum 6 saat önbellek. Anahtar yoksa kural tabanlı metin.

## Aşama 16 — aracı kurum, yalnız okuma (28.11.2026)
- ekstre.py: coz(bayt, ad, kodlar) → [(kod, adet, maliyet)]; başlık sütunu arama, olmazsa satır satır (PDF: pypdf). app._ekstre_aktar → pf_metin.
- PWA Binance cüzdanı: localStorage "kk_binance_okuma"; wss://ws-api.binance.com:443/ws-api/v3 account.status (omitZeroBalances);
  zaman damgası data-api /api/v3/time'dan. Anahtar değerleri asla depoya/sunucuya/sohbete gelmez.
- PWA güncelleme: sw.js SURUM her değişiklikte artırılır; sayfa ağ-önce, controllerchange'de bir kez yenilenir.

## Hızlı uygulama 1. adım + veri düzeltmeleri (28.11.2026)
- Karneler: karne.py → bulten/karne/<bist|abd|kripto|emtia>/<kod>.json + liste.json. Kapanış taraması (teknik_bulten._yaz) her piyasada
  tüm evrenin karnesini yazar; karne.yml (4'lü matris, 12:10 TSİ + elle) gün ortası tazeler, rejim ve dünya özetini de günceller (Telegram yok).
  Evren: BIST ~630, ABD ~1900 (likit), kripto ~660, emtia 16. yayinla ALT_BIRIM'e "karne" eklendi.
- VERİ HATASI (düzeltildi): Yahoo bazı günlerin satırını kapanışı NaN verir (27.11.2026 BIST hisseleri). gun_ici_tamamla ve canli_guncelle
  bu satırı "var" sayıp günü tamamlamıyordu → analizler bir önceki günde kalıyordu. Artık NaN satırlar atılıp gün içi veriden kuruluyor;
  BIST piyasa kapalıyken tek varlıkta resmi kapanış fast_info.lastPrice ile. dunya._indir de 15 dk veriyle tamamlanıyor.
- VERİ HATASI (düzeltildi): rejim.genislik — tek hissenin tatil satırı (30–31.05.2026) 200 günlük genişliği aylarca %0 yapıyordu;
  yalnız hisselerin en az yarısının işlem gördüğü günler kullanılıyor.

- Canlı fiyatlar (canli.py, canli.yml): seans açıkken 15 dk'da bir canli/<bist|abd|emtia>.json; BIST kapanış sonrası resmi kapanış (fast_info).
  Hızlı uygulama canlı fiyatı yalnız karneden yeniyse gösterir; kripto fiyatları tarayıcıda Binance'ten. Analiz metni kapanış/12:10/18:10 karnesinden.
- Hızlı uygulama 2. adım (28.11.2026): Portföy sekmesi — Varlıklarım (kk_pf_metin), Sanal işlem (kk_sanal: sanal.py ile aynı olay biçimi,
  pozisyon_boyutu/kontrol_listesi/dusus_sigortasi JS karşılıkları; yedek dosyası tam uygulamayla iki yönlü uyumlu), Takip (kk_takip), Risk hesap.
  Hepsi localStorage'da, yalnız telefonda.
- Hızlı uygulama 3. adım (28.11.2026): Piyasa sekmesi alt bölümleri — Genel, Takvim (haber/takvim*.json, Türkçe adlar), Ekonomi (makro/tr_makro,
  yabanci/akis, donem/haftalik), Tarayıcı (tarama/<pz>.csv; tarayici.ALANLAR/HAZIR → docs/pwa_veri.json, pwa_veri.py ile üretilir, test denetler),
  Karşılaştır (karnelerden, tarihe göre hizalı). Fırsatlar: Açık / Son taramalar / Performans (gecmis + istatistik). Özet: sabah özeti + ses.
  Tam uygulamada kalan (sunucu gerektiren): Hisse temel analizi, Bebek taraması, PDF raporlar, alarm tanımlama.
- Telegram A–Z yeni tasarım (28.11.2026): kart.ust_bant (logo + KATKAY YATIRIM + kart türü, sağda tarih), kart.bolum_baslik (aralıklı başlık +
  solan altın çizgi), kart.alt_bant (uygulama adresi + yasal not); bildirim_karti ızgara bölümü (izgara=True). Bütün kartlar bunları kullanır
  (fırsat, bülten, bildirim tabanlı tüm kartlar, sabah). Her mesajın altında hızlı uygulamayı açan düğme: tg.uygulama_dugme (fırsat → #v/KOD,
  alarm → #bildirim, rejim/dünya/… → #piyasa). Düğme reddedilirse mesaj düğmesiz gider.
- Fırsat performansı incelemesi (28.11.2026): kapanan 21 fırsatın 20'si kripto 4S, 17'si SAT; 24–27.11 kripto toparlanmasında birlikte stop
  (BTC rejim filtresi SAT'a izin veriyordu). 4'ü tokenleştirilmiş hisseydi (XSPCX, SPCXB, QQQB, XQQQ). Önlemler: bist_kripto.hisse_tokeni_mu
  geniş ABD listesiyle (142 token daha elendi, _GERCEK_KRIPTO istisnaları), kapanis.yogunluk_siniri (YON_YENI / YON_ACIK). Kurulum
  istatistikleri (geçmiş test) değiştirilmedi: GERI|-1|4S n=2793, H1 %51, ort +0,09R — canlı örnek henüz istatistiksel olarak anlamlı değil.
- Temel / Bebek / PDF (28.11.2026): temel.py (temel.yml, 06:40 TSİ) → bulten/temel/{bist,abd,bebek}.json (br.tara; ABD en likit 300; Yahoo hız sınırı için _sabirli sarmalayıcı: bekle-yeniden dene, BIST isci=3 → 629/629;
  bebek: EV.bebekler + bebek_skoru, derin analiz temel satırlarından). pdf_uret.py (pdf.yml, 05:20 TSİ) → teknik ve araştırma PDF'leri
  GitHub sürüm "raporlar" eklerine (--clobber), dizin bulten/pdf/{teknik,arastirma}.json. Hızlı uygulama: varlık sayfasında temel bölüm ve
  PDF düğmeleri, Piyasa › Temel (değer sıralaması, bebekler, genç, küçük).
