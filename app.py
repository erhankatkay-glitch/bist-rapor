# -*- coding: utf-8 -*-
"""BIST Hisse Araştırma – mobil uyumlu web uygulaması (Streamlit)."""
import os, glob, tempfile, datetime as dt, importlib
import pandas as pd
import streamlit as st
import json
import bist_veri as bv
import bist_isyatirim as isy
import bist_makro as mk
import tasarim as ts
import bist_rapor as br
import bist_varlik as V
import bist_evren as EV
import bist_kripto as KR
import bist_borsa as BB
import bist_ileri as IL
import analist as AN
import bist_teknik as TK
import bist_teknik_rapor as TKR
import firsat as FR
import haber as HB
import io
ts = importlib.reload(ts)
bv = importlib.reload(bv)
isy = importlib.reload(isy)  # alt modüller de güncellensin
mk = importlib.reload(mk)
br = importlib.reload(br)
V = importlib.reload(V)
EV = importlib.reload(EV)
KR = importlib.reload(KR)
BB = importlib.reload(BB)
IL = importlib.reload(IL)
AN = importlib.reload(AN)
TK = importlib.reload(TK)
TKR = importlib.reload(TKR)
FR = importlib.reload(FR)
HB = importlib.reload(HB)
DURUM_EMOJI = {"iyi": "🟢", "orta": "🟡", "zayif": "🔴", "yok": "⚪"}
ETK_RENK = {"GÜÇLÜ AL": "#16A34A", "AL": "#22C55E", "NÖTR": "#D97706", "SAT": "#EF4444", "GÜÇLÜ SAT": "#DC2626"}
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
if st.button("🔄 Verileri yenile (önbelleği temizle)", key="yenile"):
    st.cache_data.clear()
    for k_ in ("sonuc", "v_sonuc", "v_tablo", "tarama", "kars", "bebek", "bebek_derin", "tk_sonuc", "pf"):
        st.session_state.pop(k_, None)
    st.rerun()

# ---------------- Makro veriler ----------------
@st.cache_data(ttl=3600, show_spinner=False)
def piyasa_verisi(saat):
    return mk.piyasa_paneli()

@st.cache_data(ttl=6 * 3600, show_spinner=False)
def evds_verisi(anahtar, gun):
    return mk.evds_paneli(anahtar)

def _evds_anahtar():
    try:
        k = st.secrets.get("EVDS_KEY", "")
    except Exception:
        k = ""
    return st.session_state.get("evds_key") or k

EVDS_KEY = _evds_anahtar()
EVDS, EVDS_HATA = evds_verisi(EVDS_KEY, dt.date.today().isoformat()) if EVDS_KEY else ({}, {})
OTO = mk.oto_varsayim(EVDS) if EVDS else {}

# ---------------- Ortak ayarlar ----------------
with st.expander("⚙️ Varsayımlar"):
    c1, c2 = st.columns(2)
    rf = c1.number_input("Risksiz faiz (TR 10Y)", value=0.36, step=0.01, format="%.4f")
    enf = c2.number_input("Yıllık enflasyon" + (" (EVDS)" if "enflasyon" in OTO else ""), value=float(OTO.get("enflasyon", 0.2977)),
                          step=0.01, format="%.4f")
    erp = c1.number_input("Hisse risk primi", value=0.07, step=0.005, format="%.3f")
    g = c2.number_input("DCF uç büyüme", value=0.15, step=0.01, format="%.3f")
    st.caption("Enflasyon, EVDS anahtarı girildiyse TCMB verisinden otomatik alınır; diğerleri Kasım 2026 piyasa verilerine göre ayarlıdır.")
    yeni_k = st.text_input("TCMB EVDS API anahtarı (isteğe bağlı)", value="", type="password",
                           help="evds3.tcmb.gov.tr → Benim Sayfam → API anahtarı. Kalıcı olması için Streamlit Secrets'a EVDS_KEY olarak ekleyin.")
    if yeni_k:
        st.session_state["evds_key"] = yeni_k
PRM = dict(rf=rf, enflasyon=enf, erp=erp, terminal_g=g)
GUN = dt.date.today().isoformat()
_s = dt.datetime.now()
ZAMAN = _s.strftime("%Y%m%d%H") + str(_s.minute // 15)   # fiyatlı analizler en fazla 15 dk önbellekte kalır
SAAT2 = _s.strftime("%Y%m%d") + str(_s.hour // 2)        # taramalar en fazla 2 saat


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def evren_cek(gun, surum):
    """Güncel tüm BIST hisseleri (Borsa İstanbul + İş Yatırım), XHARZ kodları ve kaynak notu."""
    try:
        df, harz, not_ = EV.bist_listesi()
        return df, sorted(harz), not_
    except Exception as e:
        return pd.DataFrame({"Kod": list(bv.tum_sirketler()), "Ad": list(bv.tum_sirketler().values())}), [], f"Liste alınamadı: {e}"


EVREN, HARZ, EVREN_NOT = evren_cek(GUN, br.SURUM)
try:
    bv.guncelle({r["Kod"]: r.get("Ad") for _, r in EVREN.iterrows()})
except Exception:
    pass


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def kripto_evren_cek(gun, surum):
    """Binance + OKX'teki tüm coinler (USDT ve TL pariteleri), hacme göre sıralı."""
    try:
        ev = KR.evren(); return ev, ev.attrs.get("not", "")
    except Exception as e:
        kr = [k for k, v in V.VARLIKLAR.items() if v[2] == "kripto"]
        return pd.DataFrame({"Kod": kr, "Binance USDT": True, "Binance TRY": True, "OKX USDT": True, "OKX TRY": False, "Hacim $": 0.0}), f"Borsa listesi alınamadı: {e}"


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def abd_listesi_cek(gun):
    import bist_abd as AB
    try:
        df = AB.tum_hisseler()
    except Exception:
        df = pd.DataFrame(columns=["Kod", "Sembol", "Ad", "Borsa"])
    return df


def abd_sec(key):
    """ABD hissesi seçimi (NYSE + Nasdaq) → 'AAPL.US' gibi kod. Endeksler: SP500, NASDAQ, DOW, VIX."""
    import bist_abd as AB
    df = abd_listesi_cek(GUN)
    dev = [f"{k} — {v}" for k, v in AB.DEV.items()]
    ops = dev + [f"{r.Sembol} — {r.Ad}" for r in df.itertuples() if r.Sembol not in AB.DEV] + \
        ["SP500 — S&P 500 endeksi", "NASDAQ — Nasdaq endeksi", "DOW — Dow Jones", "VIX — Korku endeksi"]
    sec = st.selectbox(f"ABD hissesi ({len(df):,} hisse, sembol veya ad yazın)".replace(",", "."), ops, index=None, key=key, placeholder="ör. NVDA, Apple")
    if not sec: return ""
    sem = sec.split(" — ")[0]
    return sem if sem in ("SP500", "NASDAQ", "DOW", "VIX") else AB.kod_yap(sem)


def kripto_sec(key):
    """Coin + parite (USDT / TL) + borsa (Binance / OKX) seçimi → 'PEPE/TRY' gibi kod."""
    ev, not_ = kripto_evren_cek(GUN, br.SURUM)
    def etiket(r):
        b = [x for x, c in (("Binance", "Binance USDT"), ("OKX", "OKX USDT")) if r.get(c)]
        tl = [x for x, c in (("Binance", "Binance TRY"), ("OKX", "OKX TRY")) if r.get(c)]
        return f"{r['Kod']} — {' · '.join(b) or '–'}" + (f" · TL: {'/'.join(tl)}" if tl else "")
    sec = {etiket(r): r for _, r in ev.iterrows()}
    s = st.selectbox(f"Coin ({len(ev)} coin, hacme göre sıralı)", list(sec), index=None, key=f"{key}_c",
                     placeholder="Örn. BTC, PEPE, SOL")
    c1, c2 = st.columns(2)
    par = c1.radio("Parite", ["USDT", "TL (TRY)"], horizontal=True, key=f"{key}_p")
    borsa = c2.radio("Borsa", ["Binance", "OKX"], horizontal=True, key=f"{key}_b")
    if not s: return ""
    r = sec[s]; p = "TRY" if par.startswith("TL") else "USDT"
    if not r.get(f"{borsa} {p}"):
        diger = "OKX" if borsa == "Binance" else "Binance"
        if r.get(f"{diger} {p}"):
            st.caption(f"ⓘ {r['Kod']}/{p} {borsa}'ta yok; {diger} verisi kullanılacak."); borsa = diger
        elif p == "TRY":
            st.caption(f"ⓘ {r['Kod']} için TL paritesi yok; fiyatlar USDT × USD/TRY ile TL'ye çevrilecek.")
    return KR.kod_yap(r["Kod"], p, borsa)


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


def ozet_goster(baslik, gorus, kisa, tam, tez, katalizor, risk, senaryo=None):
    """Kurumsal rapor tarzı yatırım özeti (uygulama ekranı)."""
    renk = {"OLUMLU": "#16A34A", "ILIMLI OLUMLU": "#22C55E", "NÖTR": "#D97706", "TEMKİNLİ": "#EA580C", "OLUMSUZ": "#DC2626",
            "GÜÇLÜ AL": "#16A34A", "AL": "#22C55E", "SAT": "#EF4444", "GÜÇLÜ SAT": "#DC2626"}.get(gorus, "#D97706")
    md = lambda s: s.replace("<b>", "**").replace("</b>", "**")
    st.markdown(f'<div style="border-left:4px solid #F59E0B;background:#F8FAFC;border-radius:10px;padding:10px 12px;margin:6px 0">'
                f'<div style="font-size:0.7rem;color:#F59E0B;font-weight:700">YATIRIM ÖZETİ · GENEL GÖRÜNÜM '
                f'<span style="color:{renk}">{gorus}</span></div>'
                f'<div style="font-size:1.02rem;font-weight:800;color:#0F172A;margin:4px 0 6px">{baslik}</div>'
                f'<div style="font-size:0.88rem;color:#334155">{kisa}</div></div>', unsafe_allow_html=True)
    with st.expander("📑 Yönetici özeti, yatırım tezi ve senaryolar", expanded=False):
        st.markdown(md(tam))
        pos, neg = tez
        if pos: st.markdown("**Yatırım tezini destekleyenler**\n" + "\n".join(f"{i}. **{a_}.** {b_}" for i, (a_, b_) in enumerate(pos, 1)))
        if neg: st.markdown("**Riskler ve izlenecekler**\n" + "\n".join(f"{i}. **{a_}.** {b_}" for i, (a_, b_) in enumerate(neg, 1)))
        for b_, d_, p_, ac in senaryo or []:
            st.markdown(f"**{b_}: {d_}** ({p_}) — {ac}")
        if katalizor: st.markdown("**İzlenecek katalizörler**\n" + "\n".join(f"- {AN.bas_buyuk(x)}" for x in katalizor))
        if risk: st.markdown("**Başlıca riskler**\n" + "\n".join(f"- {AN.bas_buyuk(x)}" for x in risk))


def ileri_ozet(m, para="TL", s=None):
    """İleri analizlerin ekranda gösterilecek özeti (önbelleğe alınabilir sade veri)."""
    il = (m or {}).get("ileri") if m is not None else (s or {}).get("ileri")
    il = il or {}
    o = {}
    k = il.get("karne")
    if k is not None and not k.empty:
        o["karne_yorum"] = IL.karne_yorumu(k)
        g = pd.concat([k[k["Aktif"]], k[(~k["Aktif"]) & (k["Örnek"] >= 5)].sort_values("İsabet (20g)", ascending=False)]).head(10)
        o["karne"] = [{"Sinyal": ("→ " if r["Aktif"] else "") + r["Sinyal"].replace("Mum: ", "").replace("Formasyon: ", ""), "Yön": "Al" if r["Yön"] > 0 else "Sat",
                       "Örnek": int(r["Örnek"]), "İsabet %": round(r["İsabet (20g)"] * 100), "Ort. 20g %": round(r["20g ort"] * 100, 1)} for _, r in g.iterrows()]
    if il.get("aralik"): o["aralik_yorum"] = IL.aralik_yorumu(il["aralik"], para)
    pr = il.get("profil")
    if pr: o["profil_yorum"] = (f"En çok işlem gören fiyat (POC) {IL._f(pr['poc'])} {para}; değer alanı {IL._f(pr['val'])}–{IL._f(pr['vah'])} {para}. "
                                f"Fiyat {pr['konum']}.")
    if il.get("avwap"): o["avwap"] = {k_: IL._f(v) for k_, v in il["avwap"].items()}
    if m:
        if m.get("bilanco"): o["bilanco_yorum"] = IL.bilanco_yorumu(m["bilanco"], m.get("bilanco_sonraki"))
        if m.get("aciga"): o["aciga_yorum"] = BB.aciga_yorumu(m["kod"], m["aciga"].get("satir"), m["aciga"].get("oran"), m["aciga"].get("donem"))
        if m.get("kap") is not None:
            o["kap_yorum"] = BB.kap_yorumu(m["kap"])
            o["kap"] = [{"Tarih": f"{x['tarih']:%d.%m}" if x.get("tarih") else "", "Konu": x["konu"], "Başlık": x["baslik"], "link": x.get("link")} for x in m["kap"][:8]]
        if m.get("rs") is not None: o["rs"] = m["rs"]
        if m.get("mikro"):
            mk = m["mikro"]; o["mikro_yorum"] = KR.mikro_yorum(mk.get("defter"), mk.get("islem"), mk.get("taker"), "$" if m.get("para") == "USD" else "TL")
        if m.get("vadeli"): o["vadeli_yorum"] = KR.vadeli_yorum(m["vadeli"], (m.get("mikro") or {}).get("fiyat_7g"))
        if m.get("defi"): o["defi_yorum"] = KR.defi_yorum(m["defi"].get("stable"), m["defi"].get("tvl"), m["defi"].get("protokol"))
    return o


def ileri_goster(o, baslik="🔬 İleri analiz"):
    if not o: return
    with st.expander(baslik, expanded=False):
        if o.get("rs") is not None: st.markdown(f"**Göreli güç puanı:** {o['rs']}/99 (piyasadaki tüm hisseler içinde)")
        if o.get("karne_yorum"):
            st.markdown("**Sinyal karnesi (geçmiş başarı)**  \n" + o["karne_yorum"])
            st.dataframe(pd.DataFrame(o["karne"]), hide_index=True, use_container_width=True)
        if o.get("aralik_yorum"): st.markdown("**Olası fiyat aralığı**  \n" + o["aralik_yorum"])
        if o.get("profil_yorum"):
            st.markdown("**Hacim profili**  \n" + o["profil_yorum"])
            if o.get("avwap"): st.caption(" · ".join(f"{k}: {v}" for k, v in o["avwap"].items()))
        for k_, b_ in (("bilanco_yorum", "Bilanço tepkisi"), ("aciga_yorum", "Açığa satış"), ("mikro_yorum", "Emir defteri ve işlem akışı"),
                       ("vadeli_yorum", "Vadeli piyasa"), ("defi_yorum", "Likidite ve DeFi")):
            if o.get(k_): st.markdown(f"**{b_}**  \n{o[k_]}")
        if o.get("kap_yorum"):
            st.markdown("**KAP gündemi**  \n" + o["kap_yorum"])
            for x in o.get("kap") or []:
                st.markdown(f"- {x['Tarih']} · *{x['Konu']}* · [{x['Başlık'][:100]}]({x['link']})")


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
        "pb": br.PB, "yontemler": [{"Yöntem": y[0], "Değer": y[1], "Ağırlık": y[4], "Dahil": "✓" if y[6] else "hariç", "Not": y[5]}
                      for y in m["yontemler"]],
        "saglik": m["saglik"],
        "akis_ozet": (m.get("akis") or {}).get("ozet"), "akis_yorum": br.akis_yorumlari(m),
        "genel": br.genel_degerlendirme(m), "haber": m.get("haber"), "seviye": m.get("seviye"), "ileri": ileri_ozet(m, br.PB),
        "tek": AN.karne(m), "sade": br.sade_ozet(m),
        "baslik": AN.baslik_tezi(m), "gorus": AN.gorus(m)[0], "ozet_kisa": AN.yonetici_ozeti(m, kisa=True), "ozet_tam": AN.yonetici_ozeti(m),
        "tez": AN.yatirim_tezi(m), "katalizor": AN.katalizorler(m), "risk": AN.riskler(m), "senaryo": AN.senaryolar(m),
        "teknik": {tf: (a_["etiket"], a_["puan"]) for tf, a_ in ((m.get("mta") or {}).get("tf") or {}).items() if a_},
        "usd": {k: v for k, v in (m.get("usd") or {}).items() if k != "seri"} if m.get("usd") else None,
        "yabanci": (m.get("yabanci") or {}).get("oran"),
        "fiyat_zamani": ts.zaman_metni(m.get("fiyat_zamani") or m["tarih"]), "veri_eski": (m.get("veri") or {}).get("eski"),
        "uretim": dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).strftime("%d.%m.%Y %H:%M"),
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


tab_r, tab_x, tab_f, tab_h, tab_v, tab_p, tab_t, tab_b, tab_pf, tab_al, tab_k, tab_w = st.tabs(
    ["📄 Hisse", "📐 Teknik", "🎯 Fırsatlar", "📰 Haberler", "🪙 Emtia & Kripto", "🌍 Piyasa", "🔎 Tarayıcı", "👶 Bebek", "💼 Portföy", "🔔 Alarm", "⚖️ Karşılaştır", "⭐ Takip"])

# ================= RAPOR =================
def varlik_goster(r, on="v"):
    sym = "$" if r["para"] == "USD" else "₺"
    st.markdown(f"### {r['ad']}")
    st.caption(f"🕒 Fiyat zamanı: {r.get('fiyat_zamani')} TSİ · Rapor üretimi: {r.get('uretim')}")
    renk = {"iyi": "#16A34A", "orta": "#D97706", "zayif": "#DC2626"}[V.durum_gorunum(r["gorunum"])]
    c1, c2 = st.columns(2)
    kart(c1, "SON FİYAT", f"{br.tl(r['fiyat'])} {sym}", f"≈ {br.tl(r['fiyat_tl'])} ₺" if r["para"] == "USD" else "")
    kart(c2, "GENEL GÖRÜNÜM", r["gorunum"], f"Skor {br.ond(r['skor'], 1)}/5", renk)
    c1, c2 = st.columns(2)
    kart(c1, "1 YIL ($)", br.yz(r["r_usd"].get("1Y")), f"TL reel: {br.yz(r['r_reel'])}", "#16A34A" if (r["r_usd"].get("1Y") or 0) > 0 else "#DC2626")
    kart(c2, "VOLATİLİTE", br.yz(r["vol"]), f"Zirveden: {br.yz(r['zirveden'])}")
    st.download_button("⬇️ PDF Raporu İndir", data=r["pdf"], file_name=r["dosya"], mime="application/pdf", type="primary", key=f"{on}_dl")
    ozet_goster(r["baslik"], r["gorus_v"], r["ozet_kisa"], r["ozet_tam"], r["tez"], r["kr"][0], r["kr"][1])
    b1, b2, b3 = st.tabs(["Göstergeler karnesi", "Grafikler", "Değerlendirme"])
    with b1:
        for soru, cevap, durum in r["tek"]:
            st.markdown(f"{DURUM_EMOJI.get(durum, '⚪')} **{soru}**  \n{cevap}")
        if r["guclu"]: st.markdown("**Analist notları – olumlu**\n" + "\n".join(f"- 🟢 {x}" for x in r["guclu"]))
        if r["zayif"]: st.markdown("**Analist notları – dikkat**\n" + "\n".join(f"- 🔴 {x}" for x in r["zayif"]))
    with b2:
        for ad_ in ("logbant", "mayer", "fiyat", "korku", "tlusd", "mevsim", "akis"):
            if ad_ in r["graf"]: st.image(r["graf"][ad_], use_container_width=True)
    ileri_goster(r.get("ileri"))
    with b3:
        for bas, metin in r["genel"]:
            st.markdown(f"**{bas}.** {metin}")


with tab_r:
    r_tur = st.radio("Piyasa", ["BIST", "ABD", "Kripto", "Emtia"], horizontal=True, key="r_tur")
    if r_tur in ("Kripto", "Emtia"):
        if r_tur == "Kripto":
            r_vk = kripto_sec("r_k"); r_vs = r_vk
        else:
            r_vs = st.selectbox("Emtia", [f"{k} — {v[1]}" for k, v in V.VARLIKLAR.items() if v[2] == "emtia"], index=None,
                                placeholder="Örn. Altın, Brent, Gümüş", key="r_vsec")
            r_vk = r_vs.split(" — ")[0] if r_vs else ""
        if st.button("📄 Rapor Oluştur", type="primary", disabled=not r_vk, key="r_vbtn"):
            try:
                with st.status(f"{r_vs} analiz ediliyor…") as s_:
                    st.session_state.rv_sonuc = varlik_analiz(r_vk, tuple(PRM.items()), ZAMAN, br.SURUM)
                    s_.update(label="Hazır ✓", state="complete", expanded=False)
            except Exception as e:
                st.error(f"Analiz yapılamadı: {e}")
        if "rv_sonuc" in st.session_state: varlik_goster(st.session_state.rv_sonuc, "rv")
    else:
        kod = hisse_sec("Hisse", "r_kod") if r_tur == "BIST" else abd_sec("r_abd")
        with st.expander("Emsal hisseler (isteğe bağlı)"):
            emsal = st.text_input("Virgülle ayırın; boş bırakılırsa sektör grubu otomatik seçilir", "", key="r_emsal")
        if st.button("📄 Rapor Oluştur", type="primary", disabled=not kod, key="r_btn"):
            try:
                with st.status(f"{kod} analiz ediliyor… (30–60 sn)") as s:
                    st.session_state.sonuc = analiz(kod, emsal, tuple(PRM.items()), ZAMAN, br.SURUM)
                    s.update(label="Rapor hazır ✓", state="complete", expanded=False)
            except Exception as e:
                st.error(f"Rapor oluşturulamadı: {e}\n\nKodu kontrol edin veya biraz sonra tekrar deneyin.")

        if "sonuc" in st.session_state:
            r = st.session_state.sonuc; o = r["ozet"]
            st.markdown(f"### {o['Şirket']} ({o['Kod']})")
            st.caption("📚 Finansal veri kaynağı: " + (r.get("kaynak") or "Yahoo Finance"))
            st.caption(f"🕒 Fiyat zamanı: {r.get('fiyat_zamani')} (Yahoo, ~15 dk gecikmeli) · Rapor üretimi: {r.get('uretim')}")
            if r.get("veri_eski"): st.warning("Veri uyarısı: " + r["veri_eski"])
            if r.get("kaynak_hata"): st.caption("⚠️ " + r["kaynak_hata"])
            if r.get("kur_notu"): st.caption("ⓘ " + r["kur_notu"])
            c1, c2 = st.columns(2)
            kart(c1, "SON FİYAT", f"{br.tl(o['Fiyat'])} {r.get('pb', 'TL')}", f"F/K {br.kat(o['F/K'])} · PD/DD {br.kat(o['PD/DD'])}")
            kart(c2, "ADİL DEĞER", f"{br.tl(o['Adil değer'])} {r.get('pb', 'TL')}" if o["Adil değer"] else "–",
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
            a1, a4, a5, a2, a3 = st.tabs(["Özet", "Para Akışı", "Haberler", "Grafikler", "Değerleme"])
            with a5:
                hb = r.get("haber") or {}
                if hb.get("liste"):
                    st.markdown(f"**Genel ton: {hb['ozet']}** · son 30 gün")
                    for x in hb["liste"]:
                        isaret = "🟢" if x["ton"] > 0 else "🔴" if x["ton"] < 0 else "⚪"
                        tarih = f"{x['tarih']:%d.%m}" if x.get("tarih") else ""
                        st.markdown(f"{isaret} [{x['baslik']}]({x['link']})  \n<small>{tarih} · {x['kaynak']}</small>", unsafe_allow_html=True)
                    st.caption("Ton, başlıktaki kelimelere dayalı basit bir sınıflandırmadır.")
                else:
                    st.info("Son 30 günde haber bulunamadı." + (f" ({hb.get('hata')})" if hb.get("hata") else ""))
            with a4:
                if r.get("akis_ozet"):
                    kart(st, "PARA AKIŞI GÖRÜNÜMÜ", r["akis_ozet"],
                         f"Yabancı payı %{br.ond(r['yabanci'], 2)}" if r.get("yabanci") is not None else "",
                         "#1E8E5A" if "GİRİŞ" in r["akis_ozet"] else "#C0392B" if "ÇIKIŞ" in r["akis_ozet"] else "#D9A21B")
                for x in r.get("akis_yorum") or []:
                    st.markdown("- " + x.replace("<b>", "**").replace("</b>", "**"))
                if "akis" in r["grafik"]:
                    st.image(r["grafik"]["akis"], use_container_width=True)
                st.caption("Takas ve aracı kurum dağılımı lisanslı veri olduğundan kullanılmaz; analiz fiyat-hacim verisi ve "
                           "kamuya açık yabancı payına dayanır.")
            with a1:
                sv = r.get("seviye") or {}; u = r.get("usd") or {}
                c1, c2 = st.columns(2)
                if sv.get("destek"): kart(c1, "EN YAKIN DESTEK", f"{br.tl(sv['destek'][0][0])} {r.get('pb', 'TL')}", br.yz(sv["destek"][0][0] / o["Fiyat"] - 1), "#1E8E5A")
                if sv.get("direnc"): kart(c2, "EN YAKIN DİRENÇ", f"{br.tl(sv['direnc'][0][0])} {r.get('pb', 'TL')}", br.yz(sv["direnc"][0][0] / o["Fiyat"] - 1), "#C0392B")
                if u.get("r"):
                    c1, c2 = st.columns(2)
                    kart(c1, "DOLAR FİYAT", f"${br.ond(u['fiyat_usd'], 2)}", f"Kur {br.ond(u['kur'], 2)}", "#2F6DB5")
                    kart(c2, "1Y GETİRİ ($)", br.yz(u["r"].get("1Y")), f"TL reel: {br.yz(br.reel(o['1Y getiri']))}",
                         "#1E8E5A" if (u["r"].get("1Y") or 0) > 0 else "#C0392B")
                if r.get("baslik"):
                    ozet_goster(r["baslik"], r["gorus"], r["ozet_kisa"], r["ozet_tam"], r["tez"], r["katalizor"], r["risk"], r.get("senaryo"))
                if r.get("teknik"):
                    cols = st.columns(3)
                    for c_, tf in zip(cols, ("G", "H", "A")):
                        if tf in r["teknik"]:
                            e_, p_ = r["teknik"][tf]
                            kart(c_, f"TEKNİK · {TK.TF_AD[tf].upper()}", e_, f"Puan {p_:.0f}/100", ETK_RENK.get(e_, "#14294B"))
                if r.get("tek"):
                    st.markdown("**Temel göstergeler karnesi**")
                    for soru, cevap, durum in r["tek"]:
                        st.markdown(f"{DURUM_EMOJI.get(durum, '⚪')} **{soru}**  \n{cevap}")
                ileri_goster(r.get("ileri"))
                with st.expander("🧾 Başlıklar itibarıyla değerlendirme", expanded=False):
                    for bas, metin in r.get("genel") or []:
                        st.markdown(f"**{bas}.** {metin}")
                if r["guclu"]: st.markdown("**Analist notları – olumlu**\n" + "\n".join(f"- 🟢 {x}" for x in r["guclu"]))
                if r["zayif"]: st.markdown("**Analist notları – dikkat**\n" + "\n".join(f"- 🔴 {x}" for x in r["zayif"]))
            with a2:
                gr = r["grafik"]
                for ad_ in ("saglik", "fiyat", "goreli", "finansal"):
                    if ad_ in gr: st.image(gr[ad_], use_container_width=True)
            with a3:
                if "degerleme" in r["grafik"]: st.image(r["grafik"]["degerleme"], use_container_width=True)
                dfv = pd.DataFrame(r["yontemler"])
                if not dfv.empty:
                    st.dataframe(dfv, hide_index=True, use_container_width=True,
                                 column_config={"Değer": st.column_config.NumberColumn(format="%.2f"),
                                                "Ağırlık": st.column_config.NumberColumn(format="%.2f")})

# ================= TEKNİK ANALİZ =================
REPO = "erhankatkay-glitch/bist-rapor"

@st.cache_data(ttl=15 * 60, show_spinner=False, max_entries=40)
def teknik_analiz(kod, zaman, surum, kisa=False):
    s = TK.analiz(kod, kisa_vade=kisa)
    klasor = tempfile.mkdtemp(); yol = os.path.join(klasor, f"{s['kod']}_Teknik_{dt.date.today():%Y%m%d}.pdf")
    TKR.teknik_pdf(s, yol)
    with open(yol, "rb") as f: pdf = f.read()
    graf = {tf: TKR.g_teknik(a, f"{s['kod']} · {TK.TF_AD[tf]} · {a['etiket']}", dpi=130).getvalue() for tf, a in s["tf"].items() if a}
    tfo = {tf: {"etiket": a["etiket"], "puan": a["puan"], "sayim": a["oy"]["sayim"], "sinyal": [(x[0], x[1], x[2]) for x in a["sinyal"]],
                "destek": a["sr"]["destek"], "direnc": a["sr"]["direnc"], "yapi": a["pa"]["yapi"], "ma": a["oy"]["ma_etiket"],
                "osc": a["oy"]["osc_etiket"], "pivot": a["pivot"]["Klasik"]} for tf, a in s["tf"].items() if a}
    g = s["tf"].get("G") or {}
    return {"kod": s["kod"], "ad": s["ad"], "etiket": s["etiket"], "puan": s["puan"], "yorum": AN.teknik_ozet(s), "baslik": AN.teknik_baslik(s),
            "senaryo": AN.teknik_senaryo(s), "pdf": pdf,
            "dosya": os.path.basename(yol), "graf": graf, "tf": tfo, "para": s["para"], "fiyat": g.get("fiyat"), "degisim": g.get("degisim"),
            "fiyat_zamani": ts.zaman_metni(s.get("fiyat_zamani")), "ileri": ileri_ozet(None, {"₺": "TL", "$": "$"}.get(s["para"], ""), s)}

@st.cache_data(ttl=10 * 60, show_spinner=False)
def bulten_oku(piyasa, zaman):
    import requests
    taban = f"https://raw.githubusercontent.com/{REPO}/bulten/{piyasa}/"; q = f"?t={zaman}"
    m = requests.get(taban + "meta.json" + q, timeout=20)
    if m.status_code != 200: return None
    meta = m.json(); al = lambda yol: requests.get(taban + yol + q, timeout=60).content
    ozet = pd.read_csv(io.BytesIO(al("ozet.csv")))
    return {"meta": meta, "pdf": al("bulten.pdf"), "ozet": ozet,
            "graf": {g_["kod"]: al(g_["dosya"]) for g_ in meta.get("grafikler", [])[:10]},
            "rapor": {os.path.basename(r_): al(r_) for r_ in meta.get("raporlar", [])}}

with tab_x:
    st.caption("Günlük, haftalık ve aylık kapanışlara göre 30'a yakın gösterge, mum formasyonları, grafik formasyonları "
               "(ikili tepe/dip, OBO/TOBO, üçgen, kama, bayrak, kanal), price action, Fibonacci, pivot ve uyumsuzluk analizi.")
    tk_tur = st.radio("Varlık türü", ["Hisse", "ABD", "Emtia", "Kripto"], horizontal=True, key="tk_tur")
    if tk_tur == "Hisse":
        tk_kod = hisse_sec("Hisse (endeks için XU100 yazabilirsiniz)", "tk_kod")
    elif tk_tur == "ABD":
        tk_kod = abd_sec("tk_abd")
    elif tk_tur == "Kripto":
        tk_kod = kripto_sec("tk_k")
    else:
        tk_s = st.selectbox("Emtia", [f"{k} — {v[1]}" for k, v in V.VARLIKLAR.items() if v[2] == "emtia"], index=None, key="tk_v",
                            placeholder="Seçin")
        tk_kod = tk_s.split(" — ")[0] if tk_s else ""
    st.checkbox("Kısa vade dahil (1 saatlik ve 4 saatlik grafikler)", key="tk_kisa")
    if st.button("📐 Teknik analiz yap", type="primary", disabled=not tk_kod, key="tk_btn"):
        try:
            with st.status(f"{tk_kod} teknik analizi yapılıyor… (15–40 sn)") as s_:
                st.session_state.tk_sonuc = teknik_analiz(tk_kod, ZAMAN, br.SURUM, st.session_state.get("tk_kisa", False))
                s_.update(label="Hazır ✓", state="complete", expanded=False)
        except Exception as e:
            st.error(f"Teknik analiz yapılamadı: {e}")
    if "tk_sonuc" in st.session_state:
        r = st.session_state.tk_sonuc
        st.markdown(f"### {r['ad']} ({r['kod']})")
        st.caption(f"🕒 Son fiyat verisi: {r['fiyat_zamani']} · Fiyat {TK.sayi(r['fiyat'])} {r['para']} ({br.yz(r['degisim'])})")
        kart(st, "GENEL TEKNİK GÖRÜNÜM", r["etiket"], f"Puan {r['puan']:.0f}/100 (günlük %30, haftalık %40, aylık %30)", ETK_RENK.get(r["etiket"], "#14294B"))
        cols = st.columns(3)
        for c_, tf in zip(cols, ("G", "H", "A")):
            x = r["tf"].get(tf)
            if x: kart(c_, TK.TF_AD[tf].upper(), x["etiket"], f"{x['puan']:.0f} · Al {x['sayim']['AL']} / Sat {x['sayim']['SAT']}", ETK_RENK.get(x["etiket"], "#14294B"))
        if r["tf"].get("1S") or r["tf"].get("4S"):
            cols = st.columns(2)
            for c_, tf in zip(cols, ("1S", "4S")):
                x = r["tf"].get(tf)
                if x: kart(c_, TK.TF_AD[tf].upper(), x["etiket"], f"{x['puan']:.0f} · Al {x['sayim']['AL']} / Sat {x['sayim']['SAT']}", ETK_RENK.get(x["etiket"], "#14294B"))
        st.markdown(f'<div style="border-left:4px solid #F59E0B;background:#F8FAFC;border-radius:10px;padding:10px 12px;margin:6px 0">'
                    f'<div style="font-size:0.7rem;color:#F59E0B;font-weight:700">TEKNİK GÖRÜNÜM ÖZETİ</div>'
                    f'<div style="font-size:1.0rem;font-weight:800;color:#0F172A;margin:4px 0 6px">{r["baslik"]}</div>'
                    f'<div style="font-size:0.88rem;color:#334155">{r["yorum"]}</div></div>', unsafe_allow_html=True)
        for b_, t_, h_, i_ in r.get("senaryo") or []:
            st.markdown(f"{'🟢' if 'Yükseliş' in b_ else '🔴'} **{b_}:** {t_} → hedef **{h_}** · {i_}")
        st.download_button("⬇️ Teknik PDF raporu", data=r["pdf"], file_name=r["dosya"], mime="application/pdf", type="primary", key="tk_dl")
        ileri_goster(r.get("ileri"))
        sira = [t for t in ("1S", "4S", "G", "H", "A") if t in r["tf"]]
        sek = st.tabs([TK.TF_AD[t] for t in sira])
        for sk, tf in zip(sek, sira):
            with sk:
                x = r["tf"][tf]
                if tf in r["graf"]: st.image(r["graf"][tf], use_container_width=True)
                st.markdown(f"**Ortalamalar:** {x['ma']} · **Osilatörler:** {x['osc']} · **Yapı:** {x['yapi']}")
                d_ = " · ".join(TK.sayi(v) for v, _ in x["destek"][:3]) or "–"; r_ = " · ".join(TK.sayi(v) for v, _ in x["direnc"][:3]) or "–"
                st.markdown(f"🟢 **Destek:** {d_}  \n🔴 **Direnç:** {r_}  \n⚖️ **Pivot:** P {TK.sayi(x['pivot']['P'])} · R1 {TK.sayi(x['pivot']['R1'])} · S1 {TK.sayi(x['pivot']['S1'])}")
                for ad_, y_, ac in x["sinyal"]:
                    st.markdown(f"{'🟢' if y_ > 0 else '🔴' if y_ < 0 else '🟡'} **{ad_}**  \n<span style='font-size:0.85rem;color:#6B7280'>{ac}</span>", unsafe_allow_html=True)
                if not x["sinyal"]: st.caption("Bu zaman diliminde belirgin bir formasyon veya sinyal yok.")

    st.divider()
    st.markdown("#### 📬 Kapanış bültenleri")
    st.caption("Otomatik üretilir: BIST 19:07, emtia 02:07, kripto (USDT ve TL pariteleri) 04:07 TSİ — kapanıştan yaklaşık 1 saat sonra. Tüm BIST hisseleri ile Binance ve OKX'teki tüm coinler taranır.")
    b_p = st.radio("Bülten", ["BIST", "ABD", "Kripto USDT", "Kripto TL", "Emtia"], horizontal=True, key="bul_p")
    try:
        B = bulten_oku({"BIST": "bist", "ABD": "abd", "Kripto USDT": "kripto", "Kripto TL": "kripto_tl", "Emtia": "emtia"}[b_p], ZAMAN)
    except Exception as e:
        B = None; st.caption(f"Bülten okunamadı: {e}")
    if not B:
        st.info("Bu piyasa için henüz bülten yok. İlk bülten bir sonraki kapanıştan sonra burada görünecek.")
    else:
        mt = B["meta"]
        st.markdown(f"**{mt['baslik']}** · kapanış {mt['kapanis']} · üretim {mt['uretim']} · {mt['adet']} varlık")
        if mt.get("endeks"): st.caption(f"{mt['endeks']['ad']}: {mt['endeks']['etiket']} ({mt['endeks']['puan']:.0f}/100)")
        st.download_button("⬇️ Bülten PDF", data=B["pdf"], file_name=f"{mt['piyasa']}_bulten_{mt['kapanis']}.pdf", mime="application/pdf", key="bul_dl")
        oz = B["ozet"].sort_values("Teknik puan", ascending=False)
        st.dataframe(oz[["Kod", "Teknik puan", "Genel", "Günlük", "Haftalık", "Aylık", "RSI", "Formasyon +", "Formasyon −"]].head(25),
                     hide_index=True, use_container_width=True,
                     column_config={"Teknik puan": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
                                    "RSI": st.column_config.NumberColumn(format="%.0f")})
        with st.expander("Grafikler"):
            for g_ in mt.get("grafikler", []):
                if g_["kod"] in B["graf"]:
                    st.image(B["graf"][g_["kod"]], use_container_width=True); st.caption(g_["yorum"])
        if B["rapor"]:
            with st.expander("Takip listesi teknik raporları"):
                for ad_, b_ in B["rapor"].items():
                    st.download_button(f"⬇️ {ad_}", data=b_, file_name=ad_, mime="application/pdf", key=f"bul_{ad_}")

# ================= EMTİA & KRİPTO =================
@st.cache_data(ttl=3 * 3600, show_spinner=False, max_entries=60)
def varlik_analiz(kod, prm, saat, surum):
    br.PARAM.update({k.upper(): v for k, v in dict(prm).items()})
    klasor = tempfile.mkdtemp()
    dosya, m = V.rapor(kod, klasor=klasor)
    with open(dosya, "rb") as f:
        pdf = f.read()
    graf = {}
    for ad_, fn in (("fiyat", lambda: br.g_fiyat(m["hist"], None, m["kod"], m.get("seviye"))), ("tlusd", lambda: V.g_tl_usd(m)),
                    ("mevsim", lambda: V.g_mevsim(m)), ("akis", lambda: br.g_akis(m["hist"], m)),
                    ("logbant", lambda: V.g_logbant(m)), ("mayer", lambda: V.g_mayer(m)), ("korku", lambda: V.g_korku(m))):
        try:
            b_ = fn()
            if b_: graf[ad_] = b_.getvalue()
        except Exception:
            pass
    return {"pdf": pdf, "dosya": os.path.basename(dosya), "ad": m["ad"], "kod": m["kod"], "para": m["para"], "tur": m["tur"],
            "fiyat": m["fiyat"], "fiyat_tl": m["fiyat_tl"], "skor": m["genel_skor"], "gorunum": m["gorunum"],
            "r_usd": m["r_usd"], "r_tl": m["r_tl"], "r_reel": m["r_reel"], "vol": m["vol"], "mayer": m["mayer"],
            "zirveden": m["zirveden"], "tek": AN.karne_etiketle(V.tek_bakista(m), m.get("mta")), "sade": V.sade_ozet(m),
            "baslik": AN.varlik_baslik(m), "gorus_v": AN.varlik_gorus(m)[0], "ozet_kisa": AN.varlik_ozeti(m, kisa=True), "ozet_tam": AN.varlik_ozeti(m),
            "tez": AN.varlik_tezi(m), "kr": AN.varlik_katalizor_risk(m), "guclu": m["guclu"], "zayif": m["zayif"],
            "genel": V.genel_degerlendirme(m), "ileri": ileri_ozet(m, "$" if m["para"] == "USD" else "TL"), "graf": graf, "korku": {k: v for k, v in (m.get("korku") or {}).items() if k != "seri"} or None,
            "cg": m.get("cg"), "global": m.get("global"), "turev": m.get("turev"), "sharpe": m.get("sharpe"),
            "adil": m.get("adil"), "pot": m.get("potansiyel"), "etiket": (m.get("deger") or {}).get("etiket"),
            "saglik": m.get("saglik"), "fiyat_zamani": ts.zaman_metni(m.get("fiyat_zamani")),
            "uretim": dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).strftime("%d.%m.%Y %H:%M")}

@st.cache_data(ttl=6 * 3600, show_spinner=False)
def varlik_tarama(gun, surum, n_kripto=50):
    return V.tara(V.varsayilan_liste(n_kripto))

# ================= FIRSATLAR =================
@st.cache_data(ttl=900, show_spinner=False)
def firsat_oku(piyasa, zaman):
    import requests
    taban = f"https://raw.githubusercontent.com/{REPO}/bulten/firsat/{piyasa}/"; q = f"?t={zaman}"
    out = {}
    for d in ("son", "acik", "gecmis", "olaylar", "istatistik"):
        try:
            r = requests.get(taban + d + ".json" + q, timeout=20)
            out[d] = r.json() if r.status_code == 200 else None
        except Exception:
            out[d] = None
    out["graf"] = {}
    for tf, x in (out.get("son") or {}).items():
        for kod, yol in x.get("grafik", {}).items():
            try:
                r = requests.get(taban + yol + q, timeout=30)
                if r.status_code == 200: out["graf"][(tf, kod)] = r.content
            except Exception:
                pass
    return out


def _md(html):
    import re
    return re.sub("<[^>]+>", "", html.replace("<b>", "**").replace("</b>", "**")).replace("\n", "  \n")


with tab_f:
    st.caption("Kapanan her mumda (4 saatlik, günlük, haftalık, aylık) taze oluşan işlem kurulumları; giriş, stop, 3 hedef, "
               "geçmiş başarı ve balina izleriyle. Aynı içerik Telegram'a sessiz gönderilir ve süresi dolunca oradan silinir; burada kalır.")
    fp = st.radio("Piyasa", ["BIST", "ABD", "Kripto", "Emtia"], horizontal=True, key="fr_p")
    fk = {"BIST": "bist", "ABD": "abd", "Kripto": "kripto", "Emtia": "emtia"}[fp]
    with st.spinner("Fırsatlar yükleniyor…"):
        FD = firsat_oku(fk, ZAMAN)
    son = FD.get("son") or {}
    if not son:
        st.info("Bu piyasa için henüz fırsat taraması yayınlanmadı. Tarama kapanışlardan ~30 dk sonra otomatik çalışır.")
    f1, f2, f3, f4 = st.tabs(["Son fırsatlar", "Açık kurulumlar", "Performans karnesi", "Kurulum istatistikleri"])
    with f1:
        for tf in ("4S", "G", "H", "A"):
            x = son.get(tf)
            if not x: continue
            z = pd.Timestamp(x["zaman"]).tz_convert("Europe/Istanbul") if pd.Timestamp(x["zaman"]).tzinfo else pd.Timestamp(x["zaman"])
            st.markdown(f"#### {TK.TF_AD[tf]} · {len(x['firsatlar'])} fırsat")
            st.caption(f"Tarama: {z:%d.%m.%Y %H:%M} TSİ · {x.get('taranan', 0)} likit varlık")
            if not x["firsatlar"]:
                st.write("Bu turda eşiği (puan ≥ 55, risk/ödül ≥ 2R) geçen yeni kurulum çıkmadı.")
            for f in x["firsatlar"]:
                with st.container(border=True):
                    try: st.markdown(_md(FR.firsat_metni(f)))
                    except Exception as ex: st.write(f.get("kod"), ex)
                    if (tf, f["kod"]) in FD["graf"]: st.image(FD["graf"][(tf, f["kod"])], use_container_width=True)
                    with st.expander("Kurulum açıklaması"):
                        st.write(f.get("aciklama", ""))
                        for b in f.get("balina", []): st.markdown(f"🐋 **{b[0]}** — {b[2]}")
            if x.get("adaylar"):
                with st.expander(f"Eşik altında kalan adaylar ({len(x['adaylar'])})"):
                    st.dataframe(pd.DataFrame(x["adaylar"]).rename(columns={"kod": "Kod", "yon": "Yön", "kurulum": "Kurulum", "puan": "Puan"}),
                                 hide_index=True, use_container_width=True)
        ol = FD.get("olaylar") or []
        if ol:
            st.markdown("#### Son takip olayları")
            for o in reversed(ol[-15:]):
                z = pd.Timestamp(o["zaman"]).tz_convert("Europe/Istanbul")
                st.markdown(f"`{z:%d.%m %H:%M}` " + _md(o["metin"]))
    with f2:
        ac = FD.get("acik") or []
        if not ac: st.info("Açık kurulum yok.")
        else:
            st.dataframe(pd.DataFrame([{"Kod": k["kod"], "Dilim": TK.TF_AD[k["tf"]], "Yön": "AL" if k["yon"] == 1 else "SAT", "Kurulum": k["kurulum"],
                                        "Giriş": FR.fy(k["giris"]), "Stop": FR.fy(k["stop"]) + (" (girişte)" if k["asama"] else ""),
                                        "H1": FR.fy(k["hedef"][0]), "H2": FR.fy(k["hedef"][1]), "H3": FR.fy(k["hedef"][2]),
                                        "Görülen hedef": k["asama"], "Son fiyat": FR.fy(k.get("son_fiyat")),
                                        "Getiri": FR.yz((k.get("son_fiyat", k["giris"]) - k["giris"]) / k["giris"] * k["yon"]),
                                        "Bitiş": str(k["bitis"])[:16].replace("T", " ")} for k in ac]), hide_index=True, use_container_width=True)
    with f3:
        gc = FD.get("gecmis") or []
        pf = FR.performans(gc)
        if not pf: st.info("Henüz kapanmış kurulum yok. Karne, kurulumlar kapandıkça burada oluşur.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Kapanan", pf["n"]); c2.metric("H1 başarı", f"%{pf['h1'] * 100:.0f}")
            c3.metric("Kazanan", f"%{pf['kazanc'] * 100:.0f}"); c4.metric("Ort. sonuç", FR.rrs(pf["ort_R"]))
            st.caption(f"Toplam {FR.rrs(pf['top_R'])} · işlem başına ortalama getiri {FR.yz(pf['ort_getiri'])}. "
                       "R = stop mesafesi kadar risk; +1R, riske edilen tutar kadar kazanç demektir.")
            df = pd.DataFrame(gc)
            grp = []
            for (tf, ku), g in df.groupby(["tf", "kurulum"]):
                p_ = FR.performans(g.to_dict("records"))
                grp.append({"Dilim": TK.TF_AD.get(tf, tf), "Kurulum": ku, "Adet": p_["n"], "H1 %": round(p_["h1"] * 100), "Kazanan %": round(p_["kazanc"] * 100),
                            "Ort. R": round(p_["ort_R"], 2)})
            st.dataframe(pd.DataFrame(grp).sort_values("Adet", ascending=False), hide_index=True, use_container_width=True)
            st.markdown("**Son kapananlar**")
            for k in reversed(gc[-15:]): st.markdown("- " + _md(FR.kapanis_satiri(k)))
    with f4:
        ist = FD.get("istatistik") or {}
        sat = []
        for tf, d in ist.items():
            for anahtar, v in d.items():
                ku, yon, _ = anahtar.split("|")
                if v.get("n", 0) < 20: continue
                ad_ = FR.KURULUM.get(ku, (ku, ku))[0 if yon == "1" else 1]
                sat.append({"Dilim": TK.TF_AD.get(tf, tf), "Kurulum": ad_, "Örnek": v["n"], "1R'ye ulaşma %": round(v["p1"] * 100),
                            "2R'ye ulaşma %": round(v["p2"] * 100), "Ort. R": round(v["ort_R"], 2)})
        if sat:
            st.caption("Son taramadaki tüm likit varlıkların geçmişinde aynı kuralların sonucu (stoptan önce 1R/2R hedefe ulaşma, "
                       "H1'de yarısı kapatılıp stop girişe çekilerek ortalama sonuç). Puanlamada bu oranlar kullanılır.")
            st.dataframe(pd.DataFrame(sat).sort_values(["Dilim", "Ort. R"], ascending=[True, False]), hide_index=True, use_container_width=True)
        else:
            st.info("İstatistik ilk taramadan sonra oluşur.")
    with st.expander("ℹ️ Fırsatlar nasıl seçiliyor?"):
        st.markdown(
            "- **Taze sinyal:** Yalnızca az önce kapanan mumda oluşan kurulumlar: hacimli kırılım, trend içi geri çekilme, sıkışma kırılımı, "
            "uyumsuzluklu dönüş, likidite avı dönüşü, SuperTrend dönüşü, formasyon (ikili dip/tepe, OBO/TOBO, üçgen, kama, bayrak, trend çizgisi) kırılımı.\n"
            "- **Stop:** Kurulumu bozan yapı seviyesi + ATR payı (en az 1, en fazla 3,5 ATR).\n"
            "- **Hedefler:** Direnç/destek, aşılmamış önceki tepeler, Fibonacci seviye ve uzantıları, pivotlar ve formasyonun ölçtüğü hedef; "
            "her biri R (risk katı) ile. H1'de yarısı, H2'de %30'u, H3'te kalanı kapatılır; H1 sonrası stop girişe çekilir.\n"
            "- **Geçmiş testi:** Aynı kural ve aynı stop/hedef mesafeleriyle o varlığın geçmişinde ve tüm piyasada stoptan önce hedefe ulaşma oranı.\n"
            "- **Puan (0–100):** geçmiş başarı, üst zaman dilimi teyidi, hacim ve balina izleri, trend gücü, kurulum kalitesi; "
            "aşırı alım, yakın direnç, yaklaşan bilanço gibi riskler puanı düşürür. 55 altı gönderilmez, her piyasa ve dilimde en fazla 5 fırsat.\n"
            "- **Balina:** Hacmin 20 mumluk medyanın 3 katını aşıp yönün net olduğu mumlar (kriptoda gerçek agresif alış/satış oranıyla), "
            "yüksek hacimli emilim fitilleri, fiyat yatayken tek yönlü hacim akışı (sessiz birikim/dağıtım); kriptoda ayrıca canlı büyük işlemler.\n"
            "- **Kripto SAT:** Vadeli/kaldıraçlı işlem içindir; spot piyasada açığa satış yapılamaz.")

# ================= HABERLER =================
@st.cache_data(ttl=600, show_spinner=False)
def haber_oku(zaman):
    import requests
    taban = f"https://raw.githubusercontent.com/{REPO}/bulten/haber/"; q = f"?t={zaman}"
    out = {}
    for d in ("son", "takvim"):
        try:
            r = requests.get(taban + d + ".json" + q, timeout=20); out[d] = r.json() if r.status_code == 200 else None
        except Exception:
            out[d] = None
    return out


with tab_h:
    st.caption("Piyasayı etkileyebilecek haberler 30 dakikada bir taranır: türü ve yönü sınıflandırılır, etkilenecek varlıklar "
               "gerekçesiyle gösterilir, haberden bu yana fiyat/hacim tepkisi ve teknik durum eklenir.")
    HD = haber_oku(ZAMAN)
    tkv = (HD.get("takvim") or {}).get("liste") or []
    simdi_ = pd.Timestamp.now(tz="Europe/Istanbul")
    yaklasan = [e for e in tkv if pd.Timestamp(e["zaman"]) >= simdi_ - pd.Timedelta(hours=2)]
    if yaklasan:
        with st.expander(f"🗓 Bu haftanın önemli verileri ({len(yaklasan)})", expanded=False):
            for e in yaklasan[:20]:
                t_ = pd.Timestamp(e["zaman"])
                st.markdown(f"- `{t_:%d.%m %H:%M}` **{HB.ULKE_AD.get(e['ulke'], e['ulke'])}** – {e['baslik']}"
                            + (f" (beklenti {e['beklenti']}, önceki {e['onceki']})" if e.get("beklenti") else ""))
    son_h = HD.get("son") or []
    if not son_h:
        st.info("Henüz analiz edilmiş haber yok. İlk tarama alarm kontrolüyle birlikte yapılır.")
    tur_sec = st.multiselect("Haber türü", sorted({x["tur"] for x in son_h}), key="hb_tur")
    for a in son_h[:60]:
        if tur_sec and a["tur"] not in tur_sec: continue
        with st.container(border=True):
            st.markdown(_md(HB.mesaj(a)))
            if a.get("link"): st.markdown(f"[Habere git]({a['link']})")

with tab_v:
    st.caption("Altın, gümüş, petrol, tarım ürünleri ve önde gelen kripto paralar. Bilançosu olmayan bu varlıklar için analiz "
               "trend, momentum, risk, para akışı, mevsimsellik ve piyasa verilerine dayanır.")
    v_tur = st.radio("Tür", ["Kripto", "Emtia"], horizontal=True, key="v_tur")
    if v_tur == "Kripto":
        v_kod = kripto_sec("v_k"); v_sec = v_kod
    else:
        v_sec = st.selectbox("Emtia", [f"{k} — {v[1]}" for k, v in V.VARLIKLAR.items() if v[2] == "emtia"], index=None,
                             placeholder="Örn. Altın, Brent, Gümüş", key="v_sec")
        v_kod = v_sec.split(" — ")[0] if v_sec else ""
    if st.button("📄 Analiz Et", type="primary", disabled=not v_kod, key="v_btn"):
        try:
            with st.status(f"{v_sec} analiz ediliyor…") as s:
                st.session_state.v_sonuc = varlik_analiz(v_kod, tuple(PRM.items()), ZAMAN, br.SURUM)
                s.update(label="Hazır ✓", state="complete", expanded=False)
        except Exception as e:
            st.error(f"Analiz yapılamadı: {e}")
    if "v_sonuc" in st.session_state: varlik_goster(st.session_state.v_sonuc, "v")
    with st.expander("📊 Tüm emtia ve kriptoları karşılaştır"):
        n_k = st.select_slider("Kripto sayısı (hacme göre)", options=[25, 50, 100, 200, 400], value=50, key="v_n")
        if st.button("Karşılaştırmayı oluştur", key="v_tara"):
            with st.spinner(f"16 emtia + {n_k} kripto taranıyor… (birkaç dakika)"):
                st.session_state.v_tablo = varlik_tarama(SAAT2, br.SURUM, n_k)
        if "v_tablo" in st.session_state:
            sat, hat = st.session_state.v_tablo
            if sat:
                dfv = pd.DataFrame(sat).sort_values("Skor", ascending=False)
                for c in ("1A $", "YBB $", "1Y $", "1Y TL reel", "Volatilite"):
                    dfv[c] = dfv[c].apply(lambda x: None if x is None or pd.isna(x) else round(x * 100, 1))
                dfv["Bant farkı"] = dfv["Bant farkı"].apply(lambda x: None if x is None or pd.isna(x) else round(x * 100, 1))
                st.dataframe(dfv[["Kod", "Ad", "Skor", "Görünüm", "Bant farkı", "1A $", "YBB $", "1Y $", "1Y TL reel", "Volatilite", "Sharpe", "RSI", "Para akışı"]],
                             hide_index=True, use_container_width=True,
                             column_config={"Skor": st.column_config.ProgressColumn(min_value=0, max_value=5, format="%.1f"),
                                            "RSI": st.column_config.NumberColumn(format="%.0f"),
                                            "Sharpe": st.column_config.NumberColumn(format="%.2f")})
                st.caption("Bant farkı: model değer bandının ortasına uzaklık (pozitif = ucuz bölge). Getiri ve volatilite sütunları yüzde olarak gösterilir. Sıralama teknik model çıktısıdır, tavsiye değildir.")
            if hat: st.caption("Alınamayanlar: " + ", ".join(hat))

# ================= PİYASA =================
def _degisim_metni(v):
    parca = []
    for et, k in (("1G", "d1G"), ("1A", "d1A"), ("YBB", "YBB")):
        if v.get(k) is not None: parca.append(f"{et} {br.yz(v[k])}")
    return " · ".join(parca)

with tab_p:
    st.markdown("#### 📈 Makro panel")
    try:
        PV = piyasa_verisi(ZAMAN)
    except Exception as e:
        PV = {}; st.caption(f"Piyasa verisi alınamadı: {e}")
    sira = ["USD/TRY", "EUR/TRY", "Gram altın", "BIST 100", "BIST 100 ($)", "Brent petrol", "Ons altın", "ABD 10Y faiz"]
    goster = [x for x in sira if x in PV]
    for i in range(0, len(goster), 2):
        cols = st.columns(2)
        for c, ad_ in zip(cols, goster[i:i + 2]):
            v = PV[ad_]; d1 = v.get("d1G")
            kart(c, ad_.upper(), f"{br.ond(v['deger'], 2)} {v['birim']}", _degisim_metni(v),
                 "#1E8E5A" if (d1 or 0) > 0 else "#C0392B" if (d1 or 0) < 0 else "#14294B")
    if EVDS:
        st.markdown("**TCMB (EVDS)**")
        for ad_, v in EVDS.items():
            st.markdown(f"- {ad_}: **{br.ond(v['deger'], 2)}** ({v['tarih']:%m.%Y})")
        if OTO: st.caption("Model varsayımlarındaki enflasyon EVDS'den otomatik alındı.")
        if EVDS_HATA: st.caption("Okunamayan seriler: " + "; ".join(f"{k} ({h})" for k, h in EVDS_HATA.items()))
    else:
        st.caption("TCMB verileri (enflasyon, fonlama maliyeti, rezerv) için ⚙️ Varsayımlar bölümüne ücretsiz EVDS API anahtarınızı girin.")

    st.divider()
    st.markdown("#### 🎯 Günlük piyasa taraması ve fırsat listeleri")
    st.caption("Tüm listedeki hisseler her iş günü sabahı otomatik taranır. Listeler model sıralamasıdır; yatırım tavsiyesi değildir.")
    tarama_dosya = "raporlar/tarama.csv"
    P_SATIR = None
    if os.path.exists(tarama_dosya):
        _df = pd.read_csv(tarama_dosya)
        P_SATIR = _df.drop(columns=["tarih"]).to_dict("records")
        st.caption(f"Son tarama: {_df['tarih'].iloc[0]} · {len(_df)} hisse")
        try:
            if (pd.Timestamp.today() - pd.Timestamp(str(_df["tarih"].iloc[0])[:10])).days > 3:
                st.warning("Otomatik tarama 3 günden eski. Güncel liste için aşağıdaki Tarayıcı sekmesini kullanın veya GitHub Actions'ı kontrol edin.")
        except Exception:
            pass
    elif "p_tarama" in st.session_state:
        P_SATIR = st.session_state.p_tarama
    else:
        st.info("İlk otomatik tarama bir sonraki iş günü sabahı hazır olacak. İsterseniz şimdi elle başlatabilirsiniz (tüm BIST, 15–30 dakika).")
        if st.button("🌍 Tüm piyasayı şimdi tara", key="p_btn"):
            with st.spinner(f"{len(EVREN)} hisse taranıyor (15–30 dk)… Ekranı kapatmayın."):
                st.session_state.p_tarama = tarama(tuple(sorted(EVREN["Kod"])), tuple(PRM.items()), SAAT2, br.SURUM)[0]
            st.rerun()
    if P_SATIR:
        for baslik, liste in br.kategoriler(P_SATIR).items():
            with st.expander(baslik, expanded=baslik.startswith("⭐")):
                dfk = pd.DataFrame(liste)
                dfk["Potansiyel %"] = (dfk["Potansiyel"] * 100).round(1)
                kol = [c for c in ["Kod", "Şirket", "Fırsat skoru", "Sağlık skoru", "Potansiyel %", "Gerekçe"] if c in dfk]
                st.dataframe(dfk[kol], hide_index=True, use_container_width=True,
                             column_config={"Fırsat skoru": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
                                            "Sağlık skoru": st.column_config.NumberColumn(format="%.2f")})
        st.caption("Fırsat skoru: sağlık skoru (%35), potansiyel (%30), 6 aylık göreli güç (%20) ve para akışının (%15) "
                   "taranan hisseler içindeki yüzdelik sıralamasıdır. Bir hisse hakkında karar vermeden önce tam raporunu inceleyin.")

        st.divider()
        st.markdown("#### 🗺️ Sektör ısı haritası")
        so = br.sektor_ozet(P_SATIR)
        if not so.empty:
            yesil = [c for c in ["Sağlık skoru", "Potansiyel %", "1Y getiri %", "6A göreli %", "Para girişi oranı %"] if c in so]
            kirmizi = [c for c in ["F/K", "PD/DD"] if c in so]
            try:
                sty = so.style.format("{:.1f}", subset=[c for c in so.columns if c != "Hisse"])
                sty = sty.background_gradient(cmap="RdYlGn", subset=yesil, axis=0).background_gradient(cmap="RdYlGn_r", subset=kirmizi, axis=0)
                st.dataframe(sty, use_container_width=True)
            except Exception:
                st.dataframe(so, use_container_width=True)
            st.caption("Değerler sektördeki hisselerin medyanıdır. Yeşil olumlu, kırmızı olumsuz (F/K ve PD/DD'de düşük değer yeşil).")

    st.divider()
    st.markdown("#### 🧪 Skorun geçmiş testi (backtest)")
    if os.path.exists("raporlar/backtest.json"):
        bt_ = json.load(open("raporlar/backtest.json", encoding="utf-8"))
        oz = bt_["ozet"]
        c1, c2 = st.columns(2)
        kart(c1, "YÜKSEK – DÜŞÜK SKOR FARKI", br.yz(oz["ort_fark"]), "3 aylık dönem ortalaması",
             "#1E8E5A" if oz["ort_fark"] > 0 else "#C0392B")
        kart(c2, "İSABET ORANI", br.yz(oz["isabet"], 0), f"{oz['donem_sayisi']} dönem",
             "#1E8E5A" if oz["isabet"] >= 0.6 else "#D9A21B" if oz["isabet"] >= 0.5 else "#C0392B")
        st.markdown(oz["yorum"])
        if os.path.exists("raporlar/backtest.png"): st.image("raporlar/backtest.png", use_container_width=True)
        st.caption(f"Güncelleme: {oz['uretim']}. Test, sağlık skorunun geçmişe uygulanabilen sadeleştirilmiş hâlini kullanır "
                   "(ROE, büyüme, kâr verimi, defter değeri/piyasa değeri, momentum). Bugün listede olan hisselerle yapıldığı için "
                   "hayatta kalma yanlılığı içerir ve işlem maliyetleri dahil değildir. Geçmiş performans geleceğin garantisi değildir.")
    else:
        st.info("Backtest her Pazar sabahı otomatik çalışır; ilk sonuç ilk Pazar günü burada görünecek.")

# ================= TARAYICI =================
with tab_t:
    st.caption(f"Hisse evreni: {len(EVREN)} BIST hissesi ({EVREN_NOT}). Seçtiğiniz gruptaki hisseleri tarar; sağlık skoru ve potansiyele göre sıralar. "
               "Hisse sayısına göre 1–5 dakika sürebilir; sonuç en fazla 2 saat saklanır.")
    gruplar = {"Büyük hisseler (30)": bv.BUYUK_HISSELER}
    gruplar.update({f"Sektör: {k}": v for k, v in br.SEKTOR_GRUPLARI.items()})
    gruplar["Bebek şirketler (BIST Halka Arz Endeksi)"] = sorted(HARZ) if HARZ else []
    gruplar[f"Tüm BIST ({len(EVREN)} hisse – 15–30 dk)"] = sorted(EVREN["Kod"])
    gruplar = {k: v for k, v in gruplar.items() if v}
    secim = st.selectbox("Evren", list(gruplar), key="t_grup")
    sirala = st.selectbox("Sırala", ["Sağlık skoru", "Potansiyel", "F/K", "PD/DD", "Temettü verimi", "1Y getiri"], key="t_sira")
    if st.button("🔎 Taramayı Başlat", type="primary", key="t_btn"):
        with st.spinner(f"{len(gruplar[secim])} hisse taranıyor… Ekranı kapatmayın."):
            try:
                satirlar, hatalar = tarama(tuple(gruplar[secim]), tuple(PRM.items()), SAAT2, br.SURUM)
                st.session_state.tarama = (secim, satirlar, hatalar)
            except Exception as e:
                st.error(f"Tarama yapılamadı: {e}")
    if "tarama" in st.session_state:
        ad_, satirlar, hatalar = st.session_state.tarama
        st.markdown(f"**{ad_}** – {len(satirlar)} hisse")
        tablo_goster(satirlar, sirala)
        if hatalar:
            st.caption("Veri alınamayanlar: " + ", ".join(hatalar))

# ================= BEBEK ŞİRKETLER =================
@st.cache_data(ttl=24 * 3600, show_spinner=False)
def ilk_cek(kodlar, gun, surum):
    return EV.ilk_islemler(list(kodlar))


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def resmi_ilk_cek(gun, surum):
    try: return BB.ilk_islem()
    except Exception: return {}

with tab_b:
    st.caption("Bebek şirketler, Borsa İstanbul'un resmi tanımıyla belirlenir: halka arz edilip işlem görmeye başladığı ilk günden itibaren "
               "2 yıl boyunca BIST Halka Arz Endeksi'nde (XHARZ) yer alan şirketler. Liste otomatik güncellenir; ayar gerekmez.")
    if st.button("👶 Bebek şirketleri getir", type="primary", key="b_btn"):
        with st.spinner("Resmi halka arz endeksi ve ilk işlem tarihleri alınıyor…"):
            hedef = list(HARZ) if HARZ else list(EVREN["Kod"])
            ilk = ilk_cek(tuple(sorted(hedef)), GUN, br.SURUM)
            liste, resmi = EV.bebekler(EVREN, ilk, set(HARZ), resmi_ilk=resmi_ilk_cek(GUN, br.SURUM))
            st.session_state.bebek = (liste, resmi, len(EVREN)); st.session_state.pop("bebek_derin", None)
    if "bebek" in st.session_state:
        liste, resmi, n_ev = st.session_state.bebek
        st.markdown(f"**{len(liste)} bebek şirket** ({n_ev} BIST hissesi içinden)")
        st.caption("Kaynak: " + ("Borsa İstanbul resmi XHARZ bileşen listesi." if resmi else
                   "Resmi liste bu sefer alınamadı; ilk işlem tarihi 2 yıldan yeni olan hisseler seçildi (Yahoo).") + f" Hisse evreni: {EVREN_NOT}")
        if liste:
            dfb = pd.DataFrame(liste)
            for c in ("İlk işlemden getiri", "Zirveden uzaklık"):
                dfb[c] = dfb[c].apply(lambda x: None if x is None or pd.isna(x) else round(x * 100, 1))
            st.dataframe(dfb, hide_index=True, use_container_width=True,
                         column_config={"Halka açıklık %": st.column_config.NumberColumn(format="%.1f"),
                                        "İlk işlemden getiri": st.column_config.NumberColumn("İlk işlemden getiri %", format="%.1f"),
                                        "Zirveden uzaklık": st.column_config.NumberColumn("Zirveden %", format="%.1f")})
            st.caption("İlk işlem tarihi ve ilk gün kapanışı Borsa İstanbul'un resmi listesinden alınır (ilk gün kapanışı düzeltilmemiş fiyattır). "
                       "'İlk işlemden getiri' bedelsiz/bölünme düzeltilmiş Yahoo verisinden hesaplanır. "
                       "'Endekste kalan' süre dolduğunda şirket bebek statüsünden çıkar.")
            n_derin = min(len(liste), 120)
            if st.button(f"🔬 Derin analiz: bilanço, büyüme ve bebek skoru ({n_derin} şirket, 2–6 dk)", key="b_derin"):
                with st.spinner("Şirketlerin finansalları taranıyor… Ekranı kapatmayın."):
                    kodlar = tuple(x["Kod"] for x in liste[:n_derin])
                    sat, hat = tarama(kodlar, tuple(PRM.items()), SAAT2, br.SURUM)
                    sat = EV.bebek_skoru([dict(x) for x in sat])
                    ek = {x["Kod"]: x for x in liste}
                    for x in sat:
                        x.update({k: v for k, v in ek.get(x["Kod"], {}).items() if k not in x})
                        x["Risk notu"] = EV.risk_notlari(x)
                    st.session_state.bebek_derin = (sat, hat)
        if "bebek_derin" in st.session_state:
            sat, hat = st.session_state.bebek_derin
            if sat:
                dfd = pd.DataFrame(sat).sort_values("Bebek skoru", ascending=False, na_position="last")
                for c in ("Reel büyüme", "Çeyrek büyüme (reel)", "Potansiyel", "ROE"):
                    if c in dfd: dfd[c] = dfd[c].apply(lambda x: None if x is None or pd.isna(x) else round(x * 100, 1))
                kol = [c for c in ["Kod", "Şirket", "Bebek skoru", "Neden", "Sağlık skoru", "Reel büyüme", "Çeyrek büyüme (reel)",
                                   "Potansiyel", "ROE", "F/K", "Para akışı", "Borsadaki süre (ay)", "Endekste kalan (ay)", "Risk notu"] if c in dfd]
                st.markdown("**🏆 Bebek skoru sıralaması**")
                st.dataframe(dfd[kol], hide_index=True, use_container_width=True,
                             column_config={"Bebek skoru": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
                                            "Sağlık skoru": st.column_config.NumberColumn(format="%.2f"),
                                            "F/K": st.column_config.NumberColumn(format="%.1f")})
                st.caption("Bebek skoru: reel hasılat büyümesi (%30), sağlık skoru (%30), değerleme potansiyeli (%15), son çeyrek büyümesi (%15) "
                           "ve para akışının (%10) bebek şirketler içindeki yüzdelik sırasıdır. Detay için kodu 📄 Hisse sekmesine yazıp tam rapor alın. "
                           "Yatırım tavsiyesi değildir.")
            if hat: st.caption("Verisi alınamayanlar: " + ", ".join(hat))

# ================= PORTFÖY =================
import portfoy as PF
PF = importlib.reload(PF)


@st.cache_data(ttl=15 * 60, show_spinner=False, max_entries=20)
def portfoy_analiz(metin, zaman, surum):
    p = PF.analiz(PF.ayristir(metin))
    yol = os.path.join(tempfile.mkdtemp(), f"Portfoy_Analizi_{dt.date.today():%Y%m%d}.pdf"); PF.pdf(p, yol)
    with open(yol, "rb") as f: pdf = f.read()
    t = p["tablo"].copy()
    return {"pdf": pdf, "dosya": os.path.basename(yol), "tablo": t.to_dict("records"), "ozet": PF.ozet(p), "baslik": PF.baslik(p),
            "toplam": p["toplam"], "vol": p["vol"], "getiri": p["getiri"], "getiri_usd": p["getiri_usd"], "var95_tl": p["var95_tl"], "beta": p["beta"],
            "max_dd": p["max_dd"], "hata": p["hata"], "g_deger": PF.g_deger(p).getvalue(), "g_agirlik": PF.g_agirlik(p).getvalue(),
            "g_kor": PF.g_korelasyon(p).getvalue()}

with tab_pf:
    st.caption("Elinizdeki hisse, kripto ve emtiaları yazın; portföyün TL değeri, dağılımı, riski (oynaklık, VaR), korelasyonları, "
               "risk katkıları ve teknik görünümü hesaplanır. Her satıra: KOD MİKTAR (isteğe bağlı @ maliyet).")
    varsayilan = st.query_params.get("p", "").replace(";", "\n") or "THYAO 100\nASELS 50\nBTC/TRY 0,01\nGRAMALTIN 10"
    pf_metin = st.text_area("Portföy", varsayilan, height=160, key="pf_metin",
                            help="Örnekler: THYAO 1000 @ 280 · BTC/TRY 0,05 · ETH/USDT 1,2 · GRAMALTIN 50 (gram) · ALTIN 2 (ons)")
    if st.button("💼 Portföyü analiz et", type="primary", key="pf_btn"):
        try:
            with st.status("Portföy analiz ediliyor… (her varlık için veri çekilir)") as s_:
                st.session_state.pf = portfoy_analiz(pf_metin.strip(), ZAMAN, br.SURUM)
                st.query_params["p"] = ";".join(x.strip() for x in pf_metin.strip().splitlines() if x.strip())
                s_.update(label="Hazır ✓", state="complete", expanded=False)
        except Exception as e:
            st.error(f"Portföy analiz edilemedi: {e}")
    with st.expander("📌 Telegram'da kişisel portföy uyarıları"):
        st.caption("Kaydettiğiniz portföy için 30 dakikada bir kontrol yapılır: ters (satış) sinyal, teknik görünümün SAT'a dönmesi, "
                   "destek kırılması, sert düşüş, maliyete göre −%8 zarar / +%15 kâr; kapanışlarda SAT yönlü kurulum ve ilgili haberler "
                   "💼 işaretiyle Telegram'a gelir.")
        try:
            import requests as _rq
            _kay = _rq.get(f"https://raw.githubusercontent.com/{REPO}/main/portfoy.txt?t={ZAMAN}", timeout=15).text
            _kay = "\n".join(x for x in _kay.splitlines() if x.strip() and not x.startswith("#"))
        except Exception:
            _kay = ""
        st.markdown("**Şu an takip edilen:** " + (", ".join(x.split()[0] for x in _kay.splitlines()) if _kay else "henüz yok"))
        try: gh = st.secrets.get("GH_TOKEN", "")
        except Exception: gh = ""
        if gh:
            if st.button("📌 Yukarıdaki portföyü Telegram takibine al", key="pf_kaydet"):
                import requests, base64
                u = f"https://api.github.com/repos/{REPO}/contents/portfoy.txt"; hd = {"Authorization": f"Bearer {gh}", "Accept": "application/vnd.github+json"}
                j = requests.get(u, headers=hd, timeout=20).json()
                bas = "\n".join(x for x in base64.b64decode(j["content"]).decode("utf-8").splitlines() if x.startswith("#"))
                yeni = bas + "\n" + pf_metin.strip() + "\n"
                r_ = requests.put(u, headers=hd, json={"message": "Portföy takibi güncellendi", "content": base64.b64encode(yeni.encode()).decode(),
                                                       "sha": j["sha"]}, timeout=20)
                st.success("Kaydedildi; uyarılar en geç 30 dk içinde başlar.") if r_.status_code in (200, 201) else st.error(f"Kaydedilemedi: {r_.text[:200]}")
        else:
            st.info("Uygulamadan kaydetmek için Streamlit ayarlarına GH_TOKEN eklenmeli. O zamana kadar portföyünüzü sohbette yazmanız yeterli.")
    if "pf" in st.session_state:
        r = st.session_state.pf
        c1, c2 = st.columns(2)
        kart(c1, "TOPLAM DEĞER", f"{br.tl(r['toplam'])} TL", f"Getiri: {br.yz(r['getiri'])} · $: {br.yz(r['getiri_usd'])}")
        kart(c2, "YILLIK OYNAKLIK", br.yz(r["vol"]), f"Günlük VaR %95: {br.tl(r['var95_tl'])} TL",
             "#16A34A" if r["vol"] < 0.2 else "#D97706" if r["vol"] < 0.35 else "#DC2626")
        st.markdown(f'<div style="border-left:4px solid #F59E0B;background:#F8FAFC;border-radius:10px;padding:10px 12px;margin:6px 0">'
                    f'<div style="font-size:1.0rem;font-weight:800;color:#0F172A;margin-bottom:6px">{r["baslik"]}</div>'
                    f'<div style="font-size:0.88rem;color:#334155">{r["ozet"]}</div></div>', unsafe_allow_html=True)
        st.download_button("⬇️ Portföy PDF raporu", data=r["pdf"], file_name=r["dosya"], mime="application/pdf", type="primary", key="pf_dl")
        t = pd.DataFrame(r["tablo"])
        for c in ("Ağırlık", "Risk katkısı", "Volatilite", "K/Z"):
            t[c] = t[c].apply(lambda x: None if x is None or pd.isna(x) else round(x * 100, 1))
        st.dataframe(t[["Kod", "Tür", "Değer (TL)", "Ağırlık", "Risk katkısı", "Volatilite", "K/Z", "Teknik"]], hide_index=True, use_container_width=True,
                     column_config={"Değer (TL)": st.column_config.NumberColumn(format="%.0f")})
        st.caption("Ağırlık, risk katkısı, volatilite ve K/Z yüzde olarak gösterilir.")
        for g_ in ("g_deger", "g_agirlik", "g_kor"): st.image(r[g_], use_container_width=True)
        if r["hata"]: st.caption("Verisi alınamayanlar: " + ", ".join(r["hata"]))

# ================= ALARM =================
@st.cache_data(ttl=5 * 60, show_spinner=False)
def alarm_son(zaman):
    import requests
    try:
        s = requests.get(f"https://raw.githubusercontent.com/{REPO}/bulten/alarm/son.json?t={zaman}", timeout=15).json()
        k = requests.get(f"https://raw.githubusercontent.com/{REPO}/bulten/alarm/son_kontrol.json?t={zaman}", timeout=15).json()
        return s, k
    except Exception:
        return [], {}

with tab_al:
    st.caption("Alarmlar 30 dakikada bir otomatik kontrol edilir; tetiklenince Telegram'a bildirim gider (Telegram kuruluysa). "
               "Son tetiklenen alarmlar aşağıda da görünür.")
    son_al, kontrol = alarm_son(ZAMAN)
    if kontrol: st.caption(f"Son kontrol: {kontrol.get('kontrol')} · {kontrol.get('kural')} kural")
    st.markdown("**Son alarmlar**")
    if son_al:
        import re as _re
        for x in son_al[:20]:
            m_ = _re.sub(r"⟦(.+?)⟧$", r" · [habere git](\1)", x["mesaj"])
            st.markdown(f"- `{x['zaman']}` {m_}")
    else:
        st.info("Henüz tetiklenen alarm yok.")
    st.markdown("**Kurallar**")
    mevcut = open("alarmlar.txt", encoding="utf-8").read() if os.path.exists("alarmlar.txt") else ""
    st.code("\n".join(s for s in mevcut.splitlines() if s.strip() and not s.startswith("#")) or "(kural yok)")
    with st.expander("➕ Yeni alarm ekle"):
        tip = st.selectbox("Alarm türü", ["Fiyat üstüne çıkınca", "Fiyat altına inince", "Günlük % hareket", "RSI altına inince", "RSI üstüne çıkınca",
                                          "Teknik puan üstüne çıkınca", "Yeni formasyon / kırılım", "KAP haberi"], key="al_tip")
        kod_a = st.text_input("Kod (örn. THYAO, NVDA.US, BTC/TRY, PEPE/USDT@OKX, ALTIN, SP500)", key="al_kod").strip().upper()
        deger = st.text_input("Değer (fiyat, yüzde veya RSI/puan)", key="al_deger").strip().replace(",", ".") if tip not in ("Yeni formasyon / kırılım", "KAP haberi") else ""
        kural = {"Fiyat üstüne çıkınca": f"{kod_a} > {deger}", "Fiyat altına inince": f"{kod_a} < {deger}", "Günlük % hareket": f"{kod_a} %{deger}",
                 "RSI altına inince": f"{kod_a} RSI < {deger}", "RSI üstüne çıkınca": f"{kod_a} RSI > {deger}", "Teknik puan üstüne çıkınca": f"{kod_a} PUAN > {deger}",
                 "Yeni formasyon / kırılım": f"{kod_a} FORMASYON", "KAP haberi": f"{kod_a} KAP"}.get(tip, "")
        if kod_a: st.code(kural)
        try: gh = st.secrets.get("GH_TOKEN", "")
        except Exception: gh = ""
        if gh:
            if st.button("Kaydet", disabled=not kod_a, key="al_kaydet"):
                import requests, base64
                u = f"https://api.github.com/repos/{REPO}/contents/alarmlar.txt"; hd = {"Authorization": f"Bearer {gh}", "Accept": "application/vnd.github+json"}
                j = requests.get(u, headers=hd, timeout=20).json()
                yeni = base64.b64decode(j["content"]).decode("utf-8").rstrip("\n") + "\n" + kural + "\n"
                r_ = requests.put(u, headers=hd, json={"message": f"Alarm eklendi: {kural}", "content": base64.b64encode(yeni.encode()).decode(), "sha": j["sha"]}, timeout=20)
                st.success("Alarm eklendi; bir sonraki kontrolde (en geç 30 dk) devreye girer.") if r_.status_code in (200, 201) else st.error(f"Kaydedilemedi: {r_.text[:200]}")
        else:
            st.info("Uygulamadan doğrudan kaydetmek için Streamlit ayarlarına GH_TOKEN eklenmeli. Şimdilik yukarıdaki satırı kopyalayıp GitHub'da "
                    "alarmlar.txt dosyasına ekleyebilirsiniz.")

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
                    sonuc[k] = analiz(k, "", tuple(PRM.items()), ZAMAN, br.SURUM)
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
                st.session_state.takip = tarama(tuple(liste), tuple(PRM.items()), SAAT2, br.SURUM)
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
