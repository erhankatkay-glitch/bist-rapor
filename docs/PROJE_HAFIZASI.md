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

## Sıradaki aşamalar
1. ~~Aşama 1: envanter ve veri denetimi~~ (bu dosya)
2. Aşama 2: Fırsat motoru
   - Rejim filtresi, price action ve piyasa yapısı teyidi, oynaklığa göre stop, 100 puanlık model.
   - Her kural geçmiş testle doğrulanır (vectorbt).
3. Aşama 3: Yeni raporlar
   - BIST kapanış özeti uygulamada.
   - 10 varlık için haftalık ve aylık durum raporu, hedef fiyatlarla.
4. Aşama 4: Tüm Telegram bildirimleri KATKAY tasarımında.
5. Aşama 5: Ortak veri katmanı, 4 ana bölüm (Ana Sayfa, Keşfet, Portföy, Takip), testler (pytest, ruff).
6. Gemini anahtarı eklenince: yapay zekâ yorumu (OmniRoute üzerinden ya da doğrudan).
