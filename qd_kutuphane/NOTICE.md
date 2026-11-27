# QuantDinger göstergeleri

Bu klasördeki `*_quantdinger_*.py` dosyaları QuantDinger projesinin gösterge kütüphanesinden
(github.com/erhankatkay-glitch/QuantDinger, `library/indicators`) değiştirilmeden alınmıştır.
Lisans: Apache License 2.0 (bkz. `LICENSE-APACHE-2.0`).

Yalnızca Aşama 10b sıkı geçmiş testini (`arastirma_qd.py`: gerçek zaman/boyama testi, tarih eşlemeli Monte Carlo,
4 dönem ileriye yürüyen kontrol, Benjamini-Hochberg, kör dönem) geçenler alındı; hangi piyasada hangi yönde
kullanıldıkları `qd_kabul.json` dosyasındadır. Betikler `qd_calistir.py` ile varsayılan ayarlarla çalıştırılır;
yalnızca AL/SAT sinyali okunur, emir verilmez.
