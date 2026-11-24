# -*- coding: utf-8 -*-
"""Haftalık backtest: tüm listedeki hisseler için skor gruplarının geçmiş performansı."""
import os, json, time
import pandas as pd
import bist_veri as bv, bist_isyatirim as isy, bist_backtest as bt, bist_rapor as br

def main():
    import yfinance as yf
    def fin_fn(k):
        time.sleep(0.3)
        return isy.finansallar(k, ceyrek_sayi=16)
    def fiyat_fn(k):
        h = yf.Ticker(k + ".IS").history(period="5y", auto_adjust=True)["Close"].dropna()
        return br._naive(h)
    endeks = br._naive(yf.Ticker("XU100.IS").history(period="5y")["Close"].dropna())
    sonuc = bt.calistir(sorted(bv.SIRKETLER), fin_fn, fiyat_fn, endeks, ceyrek=12)
    os.makedirs("raporlar", exist_ok=True)
    with open(os.path.join("raporlar", "backtest.json"), "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=1, default=str)
    bt.grafik(sonuc, os.path.join("raporlar", "backtest.png"))
    print(sonuc["ozet"]["yorum"])

if __name__ == "__main__":
    main()
