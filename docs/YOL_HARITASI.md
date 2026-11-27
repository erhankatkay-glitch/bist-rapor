# KATKAY — 32 bölümlük talimata göre yol haritası (27 Kasım 2026)

Kaynak: kullanıcının "Küresel piyasa analizi, tarama ve yatırım platformu" talimatı.
Karar: sıfırdan yeniden yazmak yerine mevcut, geçmiş testle doğrulanmış Python motoru korunur;
talimattaki 32 bölüm eksik listesi olarak kullanılır ve aşama aşama tamamlanır.

## Mevcut durum (Var / Kısmen / Yok)

| # | Bölüm | Durum | Not |
|---|---|---|---|
| 1 | Ücretsizlik ilkeleri | Var | Tüm araçlar ücretsiz; ücretli servis yok |
| 2 | Ana araç + yedek | Kısmen | Yahoo + İş Yatırım + Binance var; yedek tablosu yazılmadı |
| 3 | iPhone'dan geliştirme / PWA | Kısmen | Streamlit ana ekrana eklenebiliyor; gerçek PWA yok |
| 4 | GitHub düzeni | Kısmen | Depo herkese açık (bilinçli, aşağıya bak); modüller kök klasörde |
| 5 | Ortak veri standardı | Kısmen | Kaynak/zaman var; "gecikmeli / gün sonu / bayat" etiketi her yerde yok |
| 6 | BIST | Var | BIST 100 evreni, sektörler, KAP sınıflandırma |
| 7 | ABD + dünya borsaları | Kısmen | ABD var; Londra, Frankfurt, Tokyo vb. yok |
| 8 | Kripto | Var | Spot, fonlama, açık pozisyon; borsalar arası fark yok |
| 9 | Emtia | Kısmen | Fiyatlar var; contango/backwardation, vade yok |
| 10 | Döviz, faiz, tahvil | Kısmen | USD/TRY, DXY, ABD 10Y; getiri eğrisi, reel faiz, TÜFE otomatik değil |
| 11 | Vadeli + opsiyon | Kısmen | Kripto vadeli var; opsiyon/Greeks yok |
| 12 | Teknik motor | Var | EMA/SMA/RSI/MACD/ADX/ATR/BB/Ichimoku/Supertrend/OBV/MFI/CMF/Donchian/PSAR; WMA, HMA, Heikin Ashi yok |
| 13 | Temel analiz | Kısmen | F/K, PD/DD vb. (İş Yatırım); banka/holding ayrımı, SEC yok |
| 14 | Grafik | Kısmen | Mum, hacim, indikatör; çizim araçları yok |
| 15 | Fibonacci + harmonik | Kısmen | Fibonacci var; harmonik formasyon yok |
| 16 | SMC | Kısmen | FVG, BOS, CHoCH var; order block, breaker, likidite süpürme yok |
| 17 | Hacim / VWAP / profil | Kısmen | VWAP, hacim profili var; RVOL taraması yok |
| 18 | Çoklu zaman dilimi | Var | 4 saat / gün / hafta teyidi |
| 19 | Tarama motoru | Kısmen | Hazır taramalar var; kullanıcının kendi filtresini kurması yok |
| 20 | 100 puanlık sinyal | Var | Geçmiş testli filtrelerle |
| 21 | Risk / hedef | Kısmen | Stop, H1–H3, R/R var; pozisyon büyüklüğü hesaplayıcı yok |
| 22 | Portföy + sanal işlem | Kısmen | Portföy var; sanal (paper) işlem yok |
| 23 | Alarm merkezi | Kısmen | Otomatik alarmlar var; kullanıcının kendi kuralını yazması yok |
| 24 | Ekonomik takvim | Var | |
| 25 | Haber | Var | KAP + genel; olumsuzlama düzeltildi |
| 26 | Korelasyon | Kısmen | Portföyde var; ayrı modül yok |
| 27 | Yapay zekâ asistanı | Kısmen | Kural tabanlı metin (analist.py); dil modeli yok |
| 28 | Raporlar | Var | Günlük, haftalık, aylık, PDF |
| 29 | Kişisel takip merkezi | Kısmen | Favoriler, alarmlar; not ve işlem günlüğü yok |
| 30 | Aracı kurum | Yok | En son aşama, önce salt okunur |
| 31 | Veri güvenliği | Var | Anahtarlar GitHub Secrets'ta; kişisel veri depoda yok |
| 32 | Altı rollü ekip | Yok | Kural tabanlı rol raporları olarak yapılabilir |

## Talimatla çelişen ve bilinçli değiştirilen noktalar
- **Özel (private) depo:** Özel depoda GitHub Actions ayda 2.000 dakika ile sınırlı.
  Yalnız 30 dakikalık alarm işi ayda yaklaşık 3.000 dakika harcar.
  Depo açık kalır; anahtarlar Secrets'ta, kişisel portföy depoda tutulmaz.
- **Sıfırdan Vite/PWA:** Çalışan motoru atmak yerine, ileride `bulten` dalındaki JSON'u okuyan hafif bir PWA ön yüzü (Cloudflare Pages, ücretsiz) eklenebilir.
- **Gerçek zamanlı BIST:** Ücretsiz değil, lisanslı; gecikmeli veri açıkça yazılır.
- **KAP iç API'si:** Kullanılmaz (pykap ve borsa-mcp bunu kullanıyor).

## Önerilen aşamalar
- ~~6. Veri kalite etiketi + yedek kaynak tablosu + TCMB enflasyonu ve politika faizi~~ (27.11.2026 tamam)
- ~~7. Teknik motoru tamamla: WMA, HMA, Heikin Ashi, RVOL, order block/breaker, harmonik formasyonlar~~ (27.11.2026 tamam)
- ~~8. Kendi taramanı kur: filtre birleştirme, kayıtlı şablonlar, sinyal yaşı / sinyalden beri değişim~~ (27.11.2026 tamam)
- ~~9. Risk hesaplayıcı (pozisyon büyüklüğü, komisyon) + sanal işlem portföyü~~ (27.11.2026 tamam)
- ~~10. Kullanıcı tanımlı alarmlar (RSI, EMA kesişimi, seviye kırılımı) + alarm geçmişi~~ (27.11.2026 tamam)
- 10b. ✅ TAMAM (28.11): 445 göstergenin 223–228'i sinyal üretti; 4 piyasada (BIST G, ABD G, kripto G/4S) test edildi.
  Gerçek zaman (boyama) testi ZigZag/pivot/emir bloğu bulucularının geleceği gördüğünü ortaya çıkardı (eşleşme %0; elendi).
  Kabul: 12 gösterge (qd_kabul.json) → BIST G fincan; ABD G pivot kırılımı, pivot SuperTrend, RSI-T3 PMax, Mavilim;
  kripto G medyan trend SAT, itki tutunması, Hull bandı, Fibonacci bant, yüzde stop SAT; kripto 4S AlphaTrend SAT, sıfır gecikmeli trend SAT.
  Yeniden çalıştırma: Actions › "Aşama 10b — QuantDinger gösterge testi" (arastirma_qd.py; sonuç arastirma-cikti dalında).
- 10b. QuantDinger (kullanıcının fork'u, Apache-2.0) kütüphanesinden aktarım (27.11 değerlendirmesi):
  - Platformun kendisi kurulmaz: Docker, PostgreSQL, Redis ve sürekli açık sunucu gerekir; BIST desteği yok; canlı emir modülü var.
  - Alınacaklar: library/indicators (54 gösterge: OTT, Mavilim, AlphaTrend, QQE, Half Trend, Schaff vb.) ve library/strategies (206 strateji).
    Bizim motora uyarlanır; her biri geçmiş testten geçerse kullanılır. Dosya başına kaynak ve lisans notu eklenir (NOTICE).
  - Geçmiş test yöntemi güçlendirilir:
    - İki yarı yerine ileriye yürüyen test (walk-forward) ve son kör dönem.
    - Çoklu deneme düzeltmesi (Benjamini-Hochberg) ve Monte Carlo.
    - Böylece çok sayıda kural denendiğinde şans eseri iyi görünenler elenir.
- 10c. ✅ TAMAM (28.11):
  - Piyasa rejimi (rejim.py): genişlik, dağıtım günleri, FTD durum makinesi, tepe uyarısı, maruziyet koçu.
    Kapanışta rejim/{bist,abd}.json; Telegram kartı yalnız durum/oran değişiminde ve Cuma; Ekonomi paneli, Seçki ve Günün fırsatları satırı, sabah özeti.
  - Kurulumlar (aynı sıkı test, QD_KAYNAK=10c): ABD G Momentum AL; BIST G EP SAT ve Momentum SAT (portföy uyarısı/karne). VCP: yetersiz olay, kapalı.
  - Disiplin (sanal.py + Sanal işlem): işlem öncesi kontrol listesi, düşüş sigortası, kapanışta işlem günlüğü, haftalık özet + öneriler, ayarlar.
    Defter cihazda tutulduğundan haftalık özet Telegram'a gitmez.
- 10c. claude-trading-skills (kullanıcının fork'u, MIT) değerlendirmesi (27.11):
  - Bu repo Claude için yazılmış iş akışı talimatları (74 skill); ABD odaklı.
    20 skill ücretli FMP/Finviz verisi istiyor. Kod olarak kurulmaz; yöntemleri kendi ücretsiz verimizle uyarlanır.
  - Piyasa rejimi paneli (Aşama 11 ile):
    - Piyasa genişliği: BIST'te 50/200 günlük ortalamanın üstündeki hisse oranı, yeni zirve/dip sayısı.
    - Dağıtım günleri ve takip günü (O'Neil FTD) — XU100 ve S&P 500.
    - Tepe uyarısı ve "maruziyet koçu" (hisse oranı önerisi %0–100).
  - Kurulumlar (Aşama 10b testinden geçerse): VCP (Minervini), momentum patlaması, episodic pivot.
  - Disiplin: işlem öncesi kontrol listesi, düşüş sigortası (sanal portföyde %X kayıpta yeni işlem uyarısı),
    işlem günlüğü ve kapanan işlem sonrası değerlendirme (bölüm 29), haftalık performans özeti.
- 11. ✅ TAMAM (28.11): korelasyon.py — 8 ana çift (20/60/250 gün, kırılma ≥ 0,4), 12'li matris, 6 oran (göreceli güç), BIST sektör rotasyonu.
  Sabah iş akışında korelasyon/ozet.json; Telegram kartı Pazartesi ve yeni kırılmada; sabah özeti maddesi; Ekonomi bölümü;
  teknik karne/PDF: endekse göre 3 aylık göreceli güç + 60 günlük korelasyon/beta (hisse→XU100, ABD→S&P 500, kripto→BTC).
- 12. Dünya borsaları, döviz majörleri, getiri eğrisi, emtia vade yapısı.
- 13. Opsiyon: BTC/ETH için Deribit'in herkese açık verisi (IV, Greeks).
- 14. Altı rollü araştırma ekibi (kural tabanlı; ücretsiz dil modeli anahtarı gelirse yorum katmanı).
  - Kullanıcının yüklediği erhankatkay-glitch/agency-agents (MIT) rol dosyaları şablon olarak kullanılacak (kullanıcı isteği, 27.11):
    finance-investment-researcher, finance-financial-analyst, academic-statistician, testing-test-results-analyzer, testing-reality-checker.
  - Raporlara eklenecek ilkeler: düşüş senaryosu yükseliş kadar ayrıntılı; "tez bozucular" (bu olursa görünüm bozulur);
    güven derecesi (veri kalitesi + geçmiş test); en kötü durumda rakamla kayıp; başarısız sinyaller de raporlanır.
- 15. PWA ön yüzü (isteğe bağlı).
- 16. Aracı kurum araştırması, yalnız salt okunur.

## Değerlendirilen KAP repoları
- **cemsinano/pykap (MIT):** KAP'ın iç `/tr/api` uçlarını kullanıyor. Kuralımız gereği eklenmez.
- **saidsurucu/borsa-mcp (MIT):** Geniş bir MCP sunucusu; KAP kısmı yine iç API.
  Fikir alınabilecek ve kurallara uyan parça: TCMB'nin herkese açık enflasyon sayfası (Aşama 6).
  Sunucunun tamamı kurulmaz.
- **zer0dayf/Bist-KAP-Dataset-Builder (MIT):** Haberleri elle girip 5 gün sonraki fiyata göre etiketleyen küçük bir araç.
  Bizde `haber.py` haber sonrası fiyat tepkisini zaten otomatik ölçüyor; eklenmez.

## Son aşama (hepsi bitince)
Telegram'da paylaşılan her şey baştan sona yeni tasarıma ve yeni modüllere göre güncellenecek (kullanıcı isteği).
