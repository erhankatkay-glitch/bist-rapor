# 📊 BIST Hisse Araştırma Raporu

BIST hisseleri için profesyonel PDF araştırma raporu üreten mobil uyumlu web uygulaması.

**İçerik:** DCF ve emsal çarpanlarıyla değerleme, senaryo ve duyarlılık analizi, 6 kategorili finansal sağlık skoru,
Piotroski F / Altman Z'' skorları, finansal tablolar (TTM + 4 yıl), emsal karşılaştırma, BIST 100'e göre performans,
risk metrikleri, teknik göstergeler ve temettü analizi.

## Çalıştırma
- Streamlit Community Cloud: ana dosya `app.py`
- Yerel: `pip install -r requirements.txt && streamlit run app.py`

Veri: Yahoo Finance. Otomatik model çıktısıdır, yatırım tavsiyesi değildir.

## 🎯 Fırsat motoru ve Telegram

Kapanan her mumda (4 saatlik, günlük, haftalık, aylık) taze oluşan işlem kurulumları taranır. Her fırsat şunları içerir:
giriş bölgesi, stop (yapı + ATR), 3 hedef (R oranlarıyla), süre, geçmiş başarı, üst zaman dilimi teyidi, balina izleri ve riskler.
Kriptoda AL ve SAT (vadeli), BIST ve emtiada yalnızca AL. Her piyasa ve zaman diliminde en fazla 5 fırsat (puan ≥ 55).

| Tur | Zaman (TSİ) | İş akışı |
|---|---|---|
| BIST 4 saatlik | 14:17 · 18:26 | kapanis_bist.yml |
| BIST günlük + bülten (+ cuma haftalık, ay sonu aylık) | 18:26 | kapanis_bist.yml |
| Kripto 4 saatlik | 03:02 · 07:02 · 11:02 · 15:02 · 19:02 · 23:02 | kapanis_kripto.yml |
| Kripto günlük + bültenler (+ pazartesi haftalık ve karne, ayın 1'i aylık) | 03:02 | kapanis_kripto.yml |
| Emtia 4 saatlik (hafta içi) | 03:12 · 07:12 · 11:12 · 15:12 · 19:12 · 23:12 | kapanis_emtia.yml |
| Emtia günlük + bülten | 01:12 | kapanis_emtia.yml |
| ABD 4 saatlik | 13:34 ET (kış 21:34, yaz 20:34 TSİ) | kapanis_abd.yml |
| ABD günlük + bülten (+H/A) | 16:12 ET (kış 00:12, yaz 23:12 TSİ) | kapanis_abd.yml |
| Alarm + haber + Telegram temizliği | 30 dakikada bir | alarm.yml |

İşler kapanıştan 35–100 dk önce başlar ve veri hazır olana kadar bekler; GitHub'ın başlatma gecikmesi mesajları geciktirmez.

**Telegram mesajları** bildirim sesi olmadan gönderilir ve kendiliğinden silinir:
- Fırsat mesajı: aynı piyasa/zaman diliminde yeni mesaj gelince (yeni mesaj hâlâ açık kurulumları da listeler) ya da kurulumların hepsi kapanınca 1 saat sonra; en geç 46,5 saat.
- Takip (H1/H2/H3, stop, süre doldu) mesajı: yenisi gelince ya da 24 saat sonra.
- Bülten özeti ve PDF: bir sonraki bülten gelince; en geç 30 saat.
- Alarmlar: 12 saat. Haftalık karne: bir sonraki hafta ya da 46,5 saat.
Telegram, botların kendi mesajlarını yalnızca 48 saat içinde silmesine izin verir. Silinen her şey uygulamanın 🎯 Fırsatlar sekmesinde kalır.

### Telegram kurulumu
1. Telegram'da **@BotFather** → `/newbot` → bir ad ve `_bot` ile biten kullanıcı adı verin; size verilen **token**'ı kopyalayın.
2. Oluşan botunuzla sohbeti açıp **Başlat**'a basın ve bir mesaj yazın.
3. Tarayıcıda `https://api.telegram.org/bot<TOKEN>/getUpdates` adresini açın; `"chat":{"id":…}` içindeki sayı **chat ID**'nizdir.
4. GitHub'da depo → **Settings → Secrets and variables → Actions → New repository secret**: `TELEGRAM_TOKEN` ve `TELEGRAM_CHAT_ID`.
5. Test: Actions → *Alarm kontrolü ve Telegram temizliği* → **Run workflow**. Ya da yerelde `python tg.py dene`.

## 📰 Haber etkisi

30 dakikada bir (alarm kontrolüyle birlikte) Google Haberler taranır. TCMB/Fed faiz kararları, Türkiye ve ABD enflasyonu, ABD istihdamı,
kredi notu, dolar/TL, petrol ve OPEC, jeopolitik gelişmeler, kripto ETF/kurumsal talep ve hack/düzenleme haberleri ile
KAP kaynaklı şirket haberleri (sipariş, temettü, bedelsiz, geri alım, ceza) sınıflandırılır.
Her önemli haber için etkilenecek varlıklar beklenen yön ve gerekçesiyle, haberden bu yana fiyat/hacim tepkisi
("fiyatlandı / henüz tepki yok / ters yönde"), son bültendeki teknik durum ve zamanla biriken geçmiş benzer haber istatistiği verilir.
Her sabah 07:00'den sonra ABD/Euro/Çin önemli veri takvimi gönderilir. Mesajlar sessizdir; haberler 12, takvim 20 saat sonra silinir.

## 🇺🇸 ABD borsaları

NYSE, Nasdaq ve NYSE American'daki tüm hisseler (Nasdaq Trader sembol dizini; ETF, varant, hak, tercihli hariç) taranır;
20 günlük medyan işlem hacmi ≥ 20 mn $ ve fiyatı ≥ 3 $ olan ~1.900 likit hisse için kapanış bülteni (sektör ETF'leriyle
rotasyon grafiği dahil), 4 saatlik/günlük/haftalık/aylık fırsatlar, takip ve karne üretilir. Kod biçimi: `NVDA.US`, `BRK.B.US`.
Alarm listesinde ABD devleri (NVDA, AAPL, MSFT, AMZN, GOOGL, META, TSLA, AVGO) ve Nasdaq/S&P 500 yer alır; haber motoru
dev şirketlerin bilanço ve önemli haberlerini de sınıflar.
