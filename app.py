# -*- coding: utf-8 -*-
"""BIST Hisse Araştırma – mobil uyumlu web uygulaması (Streamlit)."""
import os, tempfile, datetime as dt
import streamlit as st
import bist_rapor as br

st.set_page_config(page_title="BIST Rapor", page_icon="📊", layout="centered",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 560px;}
div.stButton > button, div.stDownloadButton > button {
    width: 100%; height: 3.1rem; font-size: 1.05rem; font-weight: 600; border-radius: 12px;}
.kart {background:#F1F4F9; border-left:4px solid #14294B; border-radius:10px; padding:10px 12px; margin-bottom:8px;}
.kart .e {font-size:0.75rem; color:#6B7280;} .kart .d {font-size:1.25rem; font-weight:700; color:#14294B;}
.kart .a {font-size:0.75rem; color:#6B7280;}
</style>""", unsafe_allow_html=True)

st.markdown("## 📊 BIST Hisse Araştırma")
st.caption("Hisse kodunu yazın, profesyonel PDF araştırma raporunu indirin.")

TUM = sorted({k for v in br.SEKTOR_GRUPLARI.values() for k in v})
if "son" not in st.session_state:
    st.session_state.son = []

kod = st.text_input("Hisse kodu", placeholder="Örn. THYAO, ASELS, AKBNK", max_chars=10).strip().upper()
if st.session_state.son:
    st.caption("Son raporlar: " + " · ".join(st.session_state.son[-6:][::-1]))

with st.expander("⚙️ Gelişmiş ayarlar"):
    emsal = st.text_input("Emsal hisseler (virgülle, boş = otomatik)", "")
    c1, c2 = st.columns(2)
    rf = c1.number_input("Risksiz faiz (TR 10Y)", value=0.36, step=0.01, format="%.4f")
    enf = c2.number_input("Yıllık enflasyon", value=0.2977, step=0.01, format="%.4f")
    erp = c1.number_input("Hisse risk primi", value=0.07, step=0.005, format="%.3f")
    g = c2.number_input("DCF uç büyüme", value=0.15, step=0.01, format="%.3f")
    st.caption("Sektör grubunda tanımlı hisseler: " + ", ".join(TUM))


@st.cache_data(ttl=3600, show_spinner=False)
def uret(kod, emsal, rf, enf, erp, g, gun):
    """Aynı gün aynı parametrelerle tekrar istenirse önbellekten döner."""
    klasor = tempfile.mkdtemp()
    dosya, m = br.rapor(kod, emsal, log=lambda x: None, klasor=klasor, detay=True,
                        rf=rf, enflasyon=enf, erp=erp, terminal_g=g)
    with open(dosya, "rb") as f:
        pdf = f.read()
    ozet = {k: m.get(k) for k in ("ad", "fiyat", "adil", "potansiyel", "gorus", "genel_skor", "skor_etiket",
                                   "fk", "pddd", "roe", "teknik_ozet", "guven")}
    ozet["guclu"], ozet["zayif"] = m["guclu"][:4], m["zayif"][:4]
    return os.path.basename(dosya), pdf, ozet


def kart(col, etiket, deger, alt="", renk="#14294B"):
    col.markdown(f'<div class="kart" style="border-left-color:{renk}"><div class="e">{etiket}</div>'
                 f'<div class="d" style="color:{renk}">{deger}</div><div class="a">{alt}</div></div>',
                 unsafe_allow_html=True)


if st.button("📄 Rapor Oluştur", type="primary", disabled=not kod):
    try:
        with st.status(f"{kod} analiz ediliyor… (30–60 sn)", expanded=False) as s:
            ad, pdf, o = uret(kod, emsal, rf, enf, erp, g, dt.date.today().isoformat())
            s.update(label="Rapor hazır ✔", state="complete")
        st.session_state.sonuc = (ad, pdf, o)
        if kod not in st.session_state.son:
            st.session_state.son.append(kod)
    except Exception as e:
        st.error(f"Rapor oluşturulamadı: {e}\n\nKodu kontrol edin (örn. THYAO) veya biraz sonra tekrar deneyin.")

if "sonuc" in st.session_state:
    ad, pdf, o = st.session_state.sonuc
    st.markdown(f"### {o['ad']}")
    pt = o["potansiyel"]
    renk = "#1E8E5A" if pt and pt > 0.15 else "#C0392B" if pt and pt < -0.15 else "#D9A21B"
    c1, c2 = st.columns(2)
    kart(c1, "SON FİYAT", f"{br.tl(o['fiyat'])} TL", f"F/K {br.kat(o['fk'])} · PD/DD {br.kat(o['pddd'])}")
    kart(c2, "ADİL DEĞER", f"{br.tl(o['adil'])} TL" if o["adil"] else "–", f"Güven: {o['guven']}", "#2F6DB5")
    c1, c2 = st.columns(2)
    kart(c1, "POTANSİYEL", br.yz(pt), o["gorus"], renk)
    sk = o["genel_skor"] or 0
    kart(c2, "SAĞLIK SKORU", f"{br.ond(o['genel_skor'], 2)}/5" if o["genel_skor"] else "–", o["skor_etiket"],
         "#1E8E5A" if sk >= 3.5 else "#D9A21B" if sk >= 2.5 else "#C0392B")
    st.download_button("⬇️ PDF Raporu İndir", data=pdf, file_name=ad, mime="application/pdf", type="primary")
    if o["guclu"]:
        st.markdown("**Güçlü yönler**\n" + "\n".join(f"- 🟢 {x}" for x in o["guclu"]))
    if o["zayif"]:
        st.markdown("**Dikkat edilmesi gerekenler**\n" + "\n".join(f"- 🔴 {x}" for x in o["zayif"]))

st.divider()
st.caption("Veri: Yahoo Finance (gecikmeli olabilir). Otomatik model çıktısıdır, yatırım tavsiyesi değildir.")
