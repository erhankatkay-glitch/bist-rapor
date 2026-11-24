# -*- coding: utf-8 -*-
"""BIST Hisse Araştırma – mobil uyumlu web uygulaması (Streamlit)."""
import os, glob, tempfile, datetime as dt, importlib
import pandas as pd
import streamlit as st
import bist_veri as bv
import bist_isyatirim as isy
import bist_rapor as br
bv = importlib.reload(bv)
isy = importlib.reload(isy)  # alt modüller de güncellensin
br = importlib.reload(br)  # kod güncellemelerinin hemen devreye girmesi için

st.set_page_config(page_title="BIST Rapor", page_icon="📊", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 640px;}
div.stButton > button, div.stDownloadButton > button {width: 100%; height: 3rem; font-size: 1.02rem; font-weight: 600; border-radius: 12px;}
.kart {background:#F1F4F9; border-left:4px solid #14294B; border-radius:10px; padding:10px 12px; margin-bottom:8px;}
.kart .e {font-size:0.72rem; color:#6B7280;} .kart .d {font-size:1.2rem; font-weight:700;} .kart .a {font-size:0.72rem; color:#6B7280;}
.stTabs [data-baseweb="tab"] {font-size: 0.95rem; padding: 6px 10px;}
</style>""", unsafe_allow_html=True)

st.markdown("## 📊 BIST Hisse Araştırma")

# ---------------- Ortak ayarlar ----------------
with st.expander("⚙️ Varsayımlar"):
    c1, c2 = st.columns(2)
    rf = c1.number_input("Risksiz faiz (TR 10Y)", value=0.36, step=0.01, format="%.4f")
    enf = c2.number_input("Yıllık enflasyon", value=0.2977, step=0.01, format="%.4f")
    erp = c1.number_input("Hisse risk primi", value=0.07, step=0.005, format="%.3f")
    g = c2.number_input("DCF uç büyüme", value=0.15, step=0.01, format="%.3f")
    st.caption("Varsayılanlar Kasım 2026 piyasa verilerine göre ayarlıdır.")
PRM = dict(rf=rf, enflasyon=enf, erp=erp, terminal_g=g)
GUN = dt.date.today().isoformat()


def hisse_sec(etiket, key):
    """Ad veya kodla arama; listede olmayan kodlar da yazılabilir."""
    secenek = bv.arama_secenekleri()
    try:
        s = st.selectbox(etiket, secenek, index=None, key=key, accept_new_options=True,
                         placeholder="Şirket adı veya kodu yazın (örn. aselsan, THYAO)")
    except TypeError:
        s = st.text_input(etiket, key=key, placeholder="Örn. THYAO veya Aselsan")
    return bv.secimden_kod(s) if s else ""


def kart(col, etiket, deger, alt="", renk="#14294B"):
    col.markdown(f'<div class="kart" style="border-left-color:{renk}"><div class="e">{etiket}</div>'
                 f'<div class="d" style="color:{renk}">{deger}</div><div class="a">{alt}</div></div>', unsafe_allow_html=True)


def renk_pot(p):
    return "#1E8E5A" if p is not None and p > 0.15 else "#C0392B" if p is not None and p < -0.15 else "#D9A21B"


def renk_skor(s):
    s = s or 0
    return "#1E8E5A" if s >= 3.5 else "#D9A21B" if s >= 2.5 else "#C0392B"


@st.cache_data(ttl=6 * 3600, show_spinner=False, max_entries=200)
def analiz(kod, emsal, prm, gun, surum):
    klasor = tempfile.mkdtemp()
    d, m, emsaller, endeks = br.analiz_et(kod, emsal, log=lambda x: None, **dict(prm))
    dosya = os.path.join(klasor, f"{m['kod']}_Arastirma_Raporu_{dt.date.today():%Y%m%d}.pdf")
    br.pdf_olustur(d, m, emsaller, endeks, dosya)
    with open(dosya, "rb") as f:
        pdf = f.read()
    k = d["hist"]["Close"].dropna()
    return {
        "dosya": os.path.basename(dosya), "pdf": pdf, "ozet": br.ozet_satir(m), "grafik": br.grafikler(d, m, endeks),
        "fiyat": k[k.index >= k.index[-1] - pd.Timedelta(days=365)],
        "guclu": m["guclu"], "zayif": m["zayif"], "kur_notu": m.get("kur_notu"), "guven": m["guven"],
        "kaynak": m.get("kaynak"), "kaynak_hata": m.get("kaynak_hata"),
        "sinirlandi": m.get("sinirlandi"), "skor_etiket": m["skor_etiket"], "veri": m.get("veri"),
        "yontemler": [{"Yöntem": y[0], "Değer (TL)": y[1], "Ağırlık": y[4], "Dahil": "✓" if y[6] else "hariç", "Not": y[5]}
                      for y in m["yontemler"]],
        "saglik": m["saglik"],
        "akis_ozet": (m.get("akis") or {}).get("ozet"), "akis_yorum": br.akis_yorumlari(m),
        "yabanci": (m.get("yabanci") or {}).get("oran"),
    }


@st.cache_data(ttl=6 * 3600, show_spinner=False, max_entries=30)
def tarama(kodlar, prm, gun, surum):
    return br.tara(list(kodlar), **dict(prm))


def tablo_goster(satirlar, sirala="Sağlık skoru"):
    if not satirlar:
        st.info("Sonuç yok."); return
    df = pd.DataFrame(satirlar)
    for c in ("Potansiyel", "ROE", "Temettü verimi", "1Y getiri"):
        df[c] = df[c].apply(lambda x: None if x is None else round(x * 100, 1))
    df = df.sort_values(sirala, ascending=sirala in ("F/K", "PD/DD"), na_position="last")
    st.dataframe(df[["Kod", "Şirket", "Sağlık skoru", "Potansiyel", "Fiyat", "Adil değer", "F/K", "PD/DD", "ROE",
                     "Temettü verimi", "1Y getiri", "Teknik"] + [c for c in ("Para akışı", "Yabancı %", "Yabancı Δ1A", "Veri puanı", "Kaynak") if c in df]],
                 hide_index=True, use_container_width=True,
                 column_config={
                     "Sağlık skoru": st.column_config.ProgressColumn("Skor", min_value=0, max_value=5, format="%.2f"),
                     "Potansiyel": st.column_config.NumberColumn("Potansiyel %", format="%.1f"),
                     "Fiyat": st.column_config.NumberColumn(format="%.2f"),
                     "Adil değer": st.column_config.NumberColumn(format="%.2f"),
                     "F/K": st.column_config.NumberColumn(format="%.1f"),
                     "PD/DD": st.column_config.NumberColumn(format="%.2f"),
                     "ROE": st.column_config.NumberColumn("ROE %", format="%.1f"),
                     "Temettü verimi": st.column_config.NumberColumn("Temettü %", format="%.1f"),
                     "1Y getiri": st.column_config.NumberColumn("1Y %", format="%.1f"),
                     "Yabancı %": st.column_config.NumberColumn(format="%.2f"),
                     "Yabancı Δ1A": st.column_config.NumberColumn("Yabancı Δ1A (puan)", format="%+.2f"),
                 })


tab_r, tab_t, tab_k, tab_w = st.tabs(["📄 Rapor", "🔎 Tarayıcı", "⚖️ Karşılaştır", "⭐ Takip"])

# ================= RAPOR =================
with tab_r:
    kod = hisse_sec("Hisse", "r_kod")
    with st.expander("Emsal hisseler (isteğe bağlı)"):
        emsal = st.text_input("Virgülle ayırın; boş bırakılırsa sektör grubu otomatik seçilir", "", key="r_emsal")
    if st.button("📄 Rapor Oluştur", type="primary", disabled=not kod, key="r_btn"):
        try:
            with st.status(f"{kod} analiz ediliyor… (30–60 sn)") as s:
                st.session_state.sonuc = analiz(kod, emsal, tuple(PRM.items()), GUN, br.SURUM)
                s.update(label="Rapor hazır ✓", state="complete", expanded=False)
        except Exception as e:
            st.error(f"Rapor oluşturulamadı: {e}\n\nKodu kontrol edin veya biraz sonra tekrar deneyin.")

    if "sonuc" in st.session_state:
        r = st.session_state.sonuc; o = r["ozet"]
        st.markdown(f"### {o['Şirket']} ({o['Kod']})")
        st.caption("📚 Finansal veri kaynağı: " + (r.get("kaynak") or "Yahoo Finance"))
        if r.get("kaynak_hata"): st.caption("⚠️ " + r["kaynak_hata"])
        if r.get("kur_notu"): st.caption("ⓘ " + r["kur_notu"])
        c1, c2 = st.columns(2)
        kart(c1, "SON FİYAT", f"{br.tl(o['Fiyat'])} TL", f"F/K {br.kat(o['F/K'])} · PD/DD {br.kat(o['PD/DD'])}")
        kart(c2, "ADİL DEĞER", f"{br.tl(o['Adil değer'])} TL" if o["Adil değer"] else "–",
             f"Güven: {r['guven']}" + (" · sınırlandı" if r.get("sinirlandi") else ""), "#2F6DB5")
        c1, c2 = st.columns(2)
        kart(c1, "POTANSİYEL", br.yz(o["Potansiyel"]), o["Görüş"], renk_pot(o["Potansiyel"]))
        kart(c2, "SAĞLIK SKORU", f"{br.ond(o['Sağlık skoru'], 2)}/5" if o["Sağlık skoru"] else "–", r["skor_etiket"],
             renk_skor(o["Sağlık skoru"]))
        st.download_button("⬇️ PDF Raporu İndir", data=r["pdf"], file_name=r["dosya"], mime="application/pdf", type="primary")
        v = r.get("veri") or {}
        if v:
            st.caption(f"Veri kalitesi {v.get('puan')}/100 · son finansal dönem "
                       f"{v['son_donem']:%d.%m.%Y}" if v.get("son_donem") is not None else f"Veri kalitesi {v.get('puan')}/100")
        a1, a4, a2, a3 = st.tabs(["Özet", "Para Akışı", "Grafikler", "Değerleme"])
        with a4:
            if r.get("akis_ozet"):
                kart(st, "PARA AKIŞI GÖRÜNÜMÜ", r["akis_ozet"],
                     f"Yabancı payı %{br.ond(r['yabanci'], 2)}" if r.get("yabanci") is not None else "",
                     "#1E8E5A" if "GİRİŞ" in r["akis_ozet"] else "#C0392B" if "ÇIKIŞ" in r["akis_ozet"] else "#D9A21B")
            for x in r.get("akis_yorum") or []:
                st.markdown(f"- {x}")
            if "akis" in r["grafik"]:
                st.image(r["grafik"]["akis"], use_container_width=True)
            st.caption("Takas ve aracı kurum dağılımı lisanslı veri olduğundan kullanılmaz; analiz fiyat-hacim verisi ve "
                       "kamuya açık yabancı payına dayanır.")
        with a1:
            if r["guclu"]: st.markdown("**Güçlü yönler**\n" + "\n".join(f"- 🟢 {x}" for x in r["guclu"]))
            if r["zayif"]: st.markdown("**Dikkat edilmesi gerekenler**\n" + "\n".join(f"- 🔴 {x}" for x in r["zayif"]))
        with a2:
            gr = r["grafik"]
            for ad_ in ("saglik", "fiyat", "goreli", "finansal"):
                if ad_ in gr: st.image(gr[ad_], use_container_width=True)
        with a3:
            if "degerleme" in r["grafik"]: st.image(r["grafik"]["degerleme"], use_container_width=True)
            dfv = pd.DataFrame(r["yontemler"])
            if not dfv.empty:
                st.dataframe(dfv, hide_index=True, use_container_width=True,
                             column_config={"Değer (TL)": st.column_config.NumberColumn(format="%.2f"),
                                            "Ağırlık": st.column_config.NumberColumn(format="%.2f")})

# ================= TARAYICI =================
with tab_t:
    st.caption("Seçtiğiniz gruptaki hisseleri tarar; sağlık skoru ve potansiyele göre sıralar. "
               "Hisse sayısına göre 1–5 dakika sürebilir; sonuç 6 saat saklanır.")
    gruplar = {"Büyük hisseler (30)": bv.BUYUK_HISSELER}
    gruplar.update({f"Sektör: {k}": v for k, v in br.SEKTOR_GRUPLARI.items()})
    gruplar[f"Tüm liste ({len(bv.SIRKETLER)} hisse – yavaş)"] = sorted(bv.SIRKETLER)
    secim = st.selectbox("Evren", list(gruplar), key="t_grup")
    sirala = st.selectbox("Sırala", ["Sağlık skoru", "Potansiyel", "F/K", "PD/DD", "Temettü verimi", "1Y getiri"], key="t_sira")
    if st.button("🔎 Taramayı Başlat", type="primary", key="t_btn"):
        with st.spinner(f"{len(gruplar[secim])} hisse taranıyor… Ekranı kapatmayın."):
            try:
                satirlar, hatalar = tarama(tuple(gruplar[secim]), tuple(PRM.items()), GUN, br.SURUM)
                st.session_state.tarama = (secim, satirlar, hatalar)
            except Exception as e:
                st.error(f"Tarama yapılamadı: {e}")
    if "tarama" in st.session_state:
        ad_, satirlar, hatalar = st.session_state.tarama
        st.markdown(f"**{ad_}** – {len(satirlar)} hisse")
        tablo_goster(satirlar, sirala)
        if hatalar:
            st.caption("Veri alınamayanlar: " + ", ".join(hatalar))

# ================= KARŞILAŞTIR =================
with tab_k:
    secenek = bv.arama_secenekleri()
    try:
        secili = st.multiselect("2–3 hisse seçin", secenek, max_selections=3, key="k_sec", accept_new_options=True,
                                placeholder="Şirket adı veya kodu")
    except TypeError:
        secili = st.multiselect("2–3 hisse seçin", secenek, max_selections=3, key="k_sec")
    kodlar = [bv.secimden_kod(x) for x in secili]
    if st.button("⚖️ Karşılaştır", type="primary", disabled=len(kodlar) < 2, key="k_btn"):
        sonuc = {}
        with st.status("Hisseler analiz ediliyor…") as s:
            for k in kodlar:
                try:
                    sonuc[k] = analiz(k, "", tuple(PRM.items()), GUN, br.SURUM)
                except Exception as e:
                    st.warning(f"{k}: {e}")
            s.update(label="Hazır ✓", state="complete", expanded=False)
        st.session_state.kars = sonuc
    if "kars" in st.session_state and st.session_state.kars:
        S = st.session_state.kars
        satir = {
            "Fiyat (TL)": lambda o: br.tl(o["Fiyat"]), "Adil değer (TL)": lambda o: br.tl(o["Adil değer"]),
            "Potansiyel": lambda o: br.yz(o["Potansiyel"]), "Sağlık skoru": lambda o: br.ond(o["Sağlık skoru"], 2),
            "F/K": lambda o: br.kat(o["F/K"]), "PD/DD": lambda o: br.kat(o["PD/DD"]), "ROE": lambda o: br.yz(o["ROE"]),
            "Temettü verimi": lambda o: br.yz(o["Temettü verimi"]), "1Y getiri": lambda o: br.yz(o["1Y getiri"]),
            "Görüş": lambda o: o["Görüş"], "Teknik": lambda o: o["Teknik"],
            "Para akışı": lambda o: o.get("Para akışı") or "–",
            "Yabancı payı": lambda o: f"%{br.ond(o.get('Yabancı %'), 2)}" if o.get("Yabancı %") is not None else "–",
        }
        tbl = pd.DataFrame({k: {ad_: f(r["ozet"]) for ad_, f in satir.items()} for k, r in S.items()})
        st.dataframe(tbl, use_container_width=True)
        fy = pd.DataFrame({k: r["fiyat"] / r["fiyat"].iloc[0] * 100 for k, r in S.items()}).dropna(how="all")
        st.markdown("**Son 12 ay performans (100 baz)**")
        st.line_chart(fy, height=260)
        sk = pd.DataFrame({k: r["saglik"] for k, r in S.items()})
        if not sk.empty:
            st.markdown("**Sağlık skoru kategorileri**")
            st.bar_chart(sk, height=260, stack=False)
        for k, r in S.items():
            st.download_button(f"⬇️ {k} PDF", data=r["pdf"], file_name=r["dosya"], mime="application/pdf", key=f"k_dl_{k}")

# ================= TAKİP =================
with tab_w:
    qp = st.query_params.get("takip", "")
    liste = [x for x in qp.split(",") if x] if qp else []
    st.caption("Takip listeniz sayfa adresinde saklanır. Listeyi değiştirdikten sonra simgeyi ana ekrana "
               "yeniden eklerseniz liste kalıcı olur.")
    yeni = hisse_sec("Listeye ekle", "w_ekle")
    if st.button("➕ Listeye Ekle", disabled=not yeni, key="w_btn"):
        if yeni not in liste:
            liste.append(yeni); st.query_params["takip"] = ",".join(liste); st.rerun()
    def _cikar(k):
        yeni_liste = [x for x in liste if x != k]
        st.query_params["takip"] = ",".join(yeni_liste)
    if liste:
        st.markdown("**Takip listeniz** (çıkarmak için dokunun):")
        sutun = st.columns(4)
        for i, k in enumerate(liste):
            sutun[i % 4].button(f"✖ {k}", key=f"rm_{k}", on_click=_cikar, args=(k,))
        if st.button("🔄 Listeyi Güncelle", type="primary", key="w_tara"):
            with st.spinner("Takip listesi taranıyor…"):
                st.session_state.takip = tarama(tuple(liste), tuple(PRM.items()), GUN, br.SURUM)
        if "takip" in st.session_state:
            tablo_goster(st.session_state.takip[0], "Potansiyel")
    else:
        st.info("Henüz takip ettiğiniz hisse yok.")

    st.divider()
    st.markdown("#### ☀️ Sabah raporları")
    klasorler = sorted(glob.glob("raporlar/20*"), reverse=True)
    if klasorler:
        son = klasorler[0]
        st.caption(f"Son üretim: {os.path.basename(son)} · Liste: takip_listesi.txt")
        ozet_dosya = os.path.join(son, "ozet.csv")
        if os.path.exists(ozet_dosya):
            tablo_goster(pd.read_csv(ozet_dosya).to_dict("records"), "Potansiyel")
        for f in sorted(glob.glob(os.path.join(son, "*.pdf"))):
            with open(f, "rb") as fh:
                st.download_button(f"⬇️ {os.path.basename(f)}", data=fh.read(), file_name=os.path.basename(f),
                                   mime="application/pdf", key=f"s_{f}")
    else:
        st.caption("Hafta içi her sabah 08:17'de takip_listesi.txt'deki hisseler için raporlar otomatik hazırlanır. "
                   "İlk raporlar oluşunca burada görünecek.")

st.divider()
st.caption(f"Veri: Yahoo Finance (gecikmeli olabilir). Otomatik model çıktısıdır, yatırım tavsiyesi değildir. · Sürüm {br.SURUM}")
