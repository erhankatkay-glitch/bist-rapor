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
