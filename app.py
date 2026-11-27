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
ETK_RENK = {"GÜÇLÜ AL": "#22C55E", "AL": "#22C55E", "NÖTR": "#E8B84A", "SAT": "#EF4444", "GÜÇLÜ SAT": "#EF4444"}
br = importlib.reload(br)  # kod güncellemelerinin hemen devreye girmesi için

st.set_page_config(page_title="KATKAY YATIRIM A.Ş.", page_icon="varlik/favicon.png", layout="centered", initial_sidebar_state="collapsed")
import uygulama_stil as TS
TS = importlib.reload(TS)
st.markdown(TS.STIL, unsafe_allow_html=True)
REPO = "erhankatkay-glitch/bist-rapor"   # bülten dalının deposu (üst bant da kullanır)
_ust_yer = st.empty()   # üst bant + kayan fiyat şeridi (piyasa verisi gelince doldurulur)

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
# ---- (taşındı) sekmelerde kullanılan yardımcılar: sekmelerden ÖNCE tanımlanmalı ----
@st.cache_data(ttl=6 * 3600, show_spinner=False)
def evren_cek(gun, surum):
    """Güncel tüm BIST hisseleri (Borsa İstanbul + İş Yatırım), XHARZ kodları ve kaynak notu."""
    try:
        df, harz, not_ = EV.bist_listesi()
        return df, sorted(harz), not_
    except Exception as e:
        return pd.DataFrame({"Kod": list(bv.tum_sirketler()), "Ad": list(bv.tum_sirketler().values())}), [], f"Liste alınamadı: {e}"


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


def kart(col, etiket, deger, alt="", renk=None):
    vurgu = renk or "#E8B84A"; yazi = renk or "#F8FAFC"
    col.markdown(f'<div class="kart" style="--v:{vurgu}"><div class="e">{etiket}</div>'
                 f'<div class="d" style="color:{yazi}">{deger}</div><div class="a">{alt}</div></div>', unsafe_allow_html=True)


def ozet_goster(baslik, gorus, kisa, tam, tez, katalizor, risk, senaryo=None):
    """Kurumsal rapor tarzı yatırım özeti (uygulama ekranı)."""
    renk = {"OLUMLU": "#22C55E", "ILIMLI OLUMLU": "#22C55E", "NÖTR": "#E8B84A", "TEMKİNLİ": "#FB923C", "OLUMSUZ": "#EF4444",
            "GÜÇLÜ AL": "#22C55E", "AL": "#22C55E", "SAT": "#EF4444", "GÜÇLÜ SAT": "#EF4444"}.get(gorus, "#E8B84A")
    md = lambda s: s.replace("<b>", "**").replace("</b>", "**")
    st.markdown(f'<div class="kn" style="border-left:3px solid {renk}">'
                f'<div class="sv-b">YATIRIM ÖZETİ · GENEL GÖRÜNÜM '
                f'<span style="color:{renk}">{gorus}</span></div>'
                f'<div class="kn-t">{baslik}</div>'
                f'<div class="kn-y">{kisa}</div></div>', unsafe_allow_html=True)
    with st.expander(":material/article: Yönetici özeti, yatırım tezi ve senaryolar", expanded=False):
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
                     "Temettü verimi", "1Y getiri", "Teknik"] + [c for c in ("Para akışı", "Yabancı %", "Yabancı Δ1H", "Yabancı Δ1A", "Yabancı Δ3A", "Veri puanı", "Kaynak") if c in df]],
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
                     "Yabancı Δ1H": st.column_config.NumberColumn("Yabancı 1 hafta (puan)", format="%+.2f"),
                     "Yabancı Δ1A": st.column_config.NumberColumn("Yabancı 1 ay (puan)", format="%+.2f"),
                     "Yabancı Δ3A": st.column_config.NumberColumn("Yabancı 3 ay (puan)", format="%+.2f"),
                 })


def varlik_goster(r, on="v"):
    sym = "$" if r["para"] == "USD" else "₺"
    st.markdown(baslik_seridi(r.get("kod", r["ad"]), r["ad"], "kripto" if r.get("tur") == "kripto" else "emtia"), unsafe_allow_html=True)
    st.caption(f"🕒 Fiyat zamanı: {r.get('fiyat_zamani')} TSİ · Rapor üretimi: {r.get('uretim')}")
    renk = {"iyi": "#22C55E", "orta": "#E8B84A", "zayif": "#EF4444"}[V.durum_gorunum(r["gorunum"])]
    c1, c2 = st.columns(2)
    kart(c1, "SON FİYAT", f"{br.tl(r['fiyat'])} {sym}", f"≈ {br.tl(r['fiyat_tl'])} ₺" if r["para"] == "USD" else "")
    kart(c2, "GENEL GÖRÜNÜM", r["gorunum"], f"Skor {br.ond(r['skor'], 1)}/5", renk)
    c1, c2 = st.columns(2)
    kart(c1, "1 YIL ($)", br.yz(r["r_usd"].get("1Y")), f"TL reel: {br.yz(r['r_reel'])}", "#22C55E" if (r["r_usd"].get("1Y") or 0) > 0 else "#EF4444")
    kart(c2, "VOLATİLİTE", br.yz(r["vol"]), f"Zirveden: {br.yz(r['zirveden'])}")
    st.download_button(":material/download: PDF Raporu İndir", data=r["pdf"], file_name=r["dosya"], mime="application/pdf", type="primary", key=f"{on}_dl")
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
            "fiyat_zamani": ts.zaman_metni(s.get("fiyat_zamani")), "ileri": ileri_ozet(None, {"₺": "TL", "$": "$"}.get(s["para"], ""), s),
            "gun": _gun_ozeti(g.get("h"))}


def _gun_ozeti(h):
    try:
        x = h.iloc[-1]
        return {"yuksek": float(x["High"]), "dusuk": float(x["Low"]), "hacim": float(x["Volume"] * x["Close"]) if x.get("Volume") else None}
    except Exception:
        return {}


def _kisa_tutar(v, para):
    if not v: return "–"
    for b, e in ((1e9, "Mr"), (1e6, "Mn"), (1e3, "B")):
        if v >= b: return f"{para}{v / b:.1f} {e}".replace(".", ",")
    return f"{para}{v:.0f}"


def baslik_seridi(kod, ad, pz):
    """Rapor ekranlarının başı: logo + kod + ad (tasarımdaki varlık başlığı, fiyatsız)."""
    import logolar as LG
    u = LG.logo_url(kod, pz)
    lg = f'<img src="{u}" alt="" class="vb-l">' if u else f'<span class="vb-l vb-h">{str(kod)[:3]}</span>'
    return f'<div class="vb" style="padding:12px 14px"><div class="vb-k">{lg}<div><div class="vb-ad">{str(kod).replace(".US", "")}</div><div class="vb-e">{ad}</div></div></div></div>'


def varlik_baslik(r, pz):
    """Tasarımdaki varlık başlık kartı: logo, ad, büyük fiyat, değişim, gün aralığı ve üç zaman dilimi görünümü."""
    import logolar as LG
    u = LG.logo_url(r["kod"], pz)
    lg = f'<img src="{u}" alt="" class="vb-l">' if u else f'<span class="vb-l vb-h">{str(r["kod"])[:3]}</span>'
    d = r.get("degisim") or 0; renk = "#4ADE80" if d > 0 else "#F87171" if d < 0 else "#A1A1AA"
    g = r.get("gun") or {}
    tfk = ""
    for tf in ("G", "H", "A"):
        x = r["tf"].get(tf)
        if x:
            c = ETK_RENK.get(x["etiket"], "#A1A1AA")
            tfk += f'<div><div class="vb-e">{TK.TF_AD[tf]}</div><div class="vb-p" style="color:{c}">{x["etiket"]}</div><div class="vb-e">{x["puan"]:.0f}/100</div></div>'
    return (f'<div class="vb"><div class="vb-u"><div class="vb-k">{lg}<div><div class="vb-ad">{r["kod"]}</div><div class="vb-e">{r["ad"]}</div></div></div>'
            f'<div style="text-align:right"><div class="vb-f">{TK.sayi(r["fiyat"])}</div><div style="color:{renk};font-weight:800">{br.yz(d)}</div></div></div>'
            f'<div class="vb-3"><div><div class="vb-e">Gün yüksek</div><b>{TK.sayi(g.get("yuksek")) if g.get("yuksek") else "–"}</b></div>'
            f'<div><div class="vb-e">Gün düşük</div><b>{TK.sayi(g.get("dusuk")) if g.get("dusuk") else "–"}</b></div>'
            f'<div><div class="vb-e">Hacim</div><b>{_kisa_tutar(g.get("hacim"), r.get("para") or "")}</b></div></div>'
            f'<div class="vb-3">{tfk}</div></div>')


def seviye_karti(r):
    """Beklenen seviyeler: günlük destek/dirençler, fiyata uzaklık, seviye çubuğu, kazanç/risk."""
    x = r["tf"].get("G") or {}; f = r["fiyat"]
    if not x or not f: return ""
    ust = [v for v, _ in x.get("direnc", []) if v > f][:2]; alt = [v for v, _ in x.get("destek", []) if v < f][:2]
    sat = []
    if alt: sat.append(("Önce gelebilir" if len(alt) > 0 else "", "En yakın destek / tekrar test", alt[0], "#F87171"))
    for i, v in enumerate(ust): sat.append((f"{i + 1}. hedef", "Direnç / önceki tepe", v, "#4ADE80"))
    if len(alt) > 1: sat.append(("Risk bölgesi", "Altında görünüm bozulur", alt[1], "#F87171"))
    satir = "".join(f'<div class="sv-s"><div><b>{a}</b><div class="vb-e">{b}</div></div><div style="text-align:right"><b>{TK.sayi(v)}</b>'
                    f'<div class="vb-e" style="color:{c}">{br.yz(v / f - 1)} {"yukarıda" if v > f else "aşağıda"}</div></div></div>' for a, b, v, c in sat)
    kr = ""
    if ust and alt and f > alt[-1]:
        oran = (ust[0] - f) / (f - alt[-1]); kr = f"1 : {oran:.1f}".replace(".", ",")
    seviyeler = sorted([v for v in alt + ust] + [f])
    lo, hi = seviyeler[0], seviyeler[-1]; poz = (f - lo) / (hi - lo) * 100 if hi > lo else 50
    noktalar = "".join(f'<span class="sv-n" style="left:{(v - lo) / (hi - lo) * 100 if hi > lo else 50:.0f}%;background:{"#4ADE80" if v > f else "#F87171"}"></span>' for v in alt + ust)
    return (f'<div class="sv"><div class="sv-b">BEKLENEN SEVİYELER</div>{satir}'
            f'<div class="sv-c"><div class="sv-cz"></div>{noktalar}<span class="sv-f" style="left:{poz:.0f}%"></span></div>'
            f'<div class="vb-3"><div><div class="vb-e">KAZANÇ / RİSK</div><b style="color:#E8B84A">{kr or "–"}</b></div>'
            f'<div><div class="vb-e">RİSKE MESAFE</div><b>{br.yz(alt[-1] / f - 1) if alt else "–"}</b></div>'
            f'<div><div class="vb-e">GÜNLÜK</div><b>{br.yz(r.get("degisim") or 0)}</b></div></div></div>')


def katkay_notu(r):
    sen = "".join(f'<div class="kn-s">{"▲" if "Yükseliş" in b_ else "▼"} <b>{b_}:</b> {t_} → hedef <b>{h_}</b></div>' for b_, t_, h_, i_ in (r.get("senaryo") or []))
    return (f'<div class="kn"><div class="sv-b">KATKAY NOTU</div><div class="kn-t">{r["baslik"]}</div>'
            f'<div class="kn-y">{r["yorum"]}</div>{sen}<div class="vb-e" style="margin-top:8px">Gösterge bazlı analizdir, yatırım tavsiyesi değildir. '
            f'Son veri: {r["fiyat_zamani"]}</div></div>')


@st.cache_data(ttl=10 * 60, show_spinner=False)
def bulten_oku(piyasa, zaman):
    import requests
    taban = f"https://raw.githubusercontent.com/{REPO}/bulten/{piyasa}/"; q = f"?t={zaman}"
    m = requests.get(taban + "meta.json" + q, timeout=20)
    if m.status_code != 200: return None
    meta = m.json(); al = lambda yol: requests.get(taban + yol + q, timeout=60).content
    ozet = pd.read_csv(io.BytesIO(al("ozet.csv")))
    kr_ = requests.get(taban + "kapanis_karti.png" + q, timeout=30)
    return {"meta": meta, "pdf": al("bulten.pdf"), "ozet": ozet, "kart": kr_.content if kr_.status_code == 200 else None,
            "graf": {g_["kod"]: al(g_["dosya"]) for g_ in meta.get("grafikler", [])[:10]},
            "rapor": {os.path.basename(r_): al(r_) for r_ in meta.get("raporlar", [])}}


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


@st.cache_data(ttl=900, show_spinner=False)
def json_oku(yol, zaman):
    import requests
    try:
        r = requests.get(f"https://raw.githubusercontent.com/{REPO}/bulten/{yol}?t={zaman}", timeout=20)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def _degisim_metni(v):
    parca = []
    for et, k in (("1G", "d1G"), ("1A", "d1A"), ("YBB", "YBB")):
        if v.get(k) is not None: parca.append(f"{et} {br.yz(v[k])}")
    return " · ".join(parca)


def spark_svg(seri, renk, w=150, h=58):
    """Son 60 günün mini fiyat grafiği: parlak çizgi + aşağı doğru solan alan."""
    v = [float(x) for x in seri.dropna().iloc[-60:]]
    if len(v) < 2: return ""
    lo, hi = min(v), max(v); hi = hi if hi > lo else lo + 1
    pts = " ".join(f"{i * (w - 2) / (len(v) - 1) + 1:.1f},{h - 3 - (x - lo) / (hi - lo) * (h - 8):.1f}" for i, x in enumerate(v))
    alan = f"1,{h} " + pts + f" {w - 1},{h}"
    gid = "g" + format(abs(hash((renk, round(v[-1], 6), len(v)))) % 10**8, "x")
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{renk}" stop-opacity=".45"/><stop offset="1" stop-color="{renk}" stop-opacity="0"/></linearGradient></defs>'
            f'<polygon points="{alan}" fill="url(#{gid})"/>'
            f'<polyline points="{pts}" fill="none" stroke="{renk}" stroke-width="2" stroke-linejoin="round" style="filter:drop-shadow(0 0 3px {renk})"/></svg>')


def _vk_tam(v):
    if not v.get("tur"): return ""
    e = VK.etiket(v.get("zaman"), v.get("tur"))
    return VK.rozet_html(e) + f'<div class="pk-alt">{v.get("kaynak", "")} · {e["aciklama"]}</div>'


def piyasa_karti(ad_, v):
    d = v.get("d1G") or 0; renk = "#22C55E" if d > 0 else "#EF4444" if d < 0 else "#A1A1AA"
    sinif = "y" if d > 0 else "k" if d < 0 else "n"; ok = "▲" if d > 0 else "▼" if d < 0 else "■"
    deger = br.ond(v["deger"], 2 if v["deger"] < 10000 else 0)
    birim = {"puan": "", "TL": " ₺", "$": " $", "%": "%"}.get(v["birim"], "")
    alt = " · ".join(x for x in (f"1A {br.yz(v['d1A'])}" if v.get("d1A") is not None else "", f"YBB {br.yz(v['YBB'])}" if v.get("YBB") is not None else "") if x)
    import logolar as LG
    lg = LG.logo_url({"Bitcoin": "BTC", "Ethereum": "ETH"}.get(ad_, ""), "kripto") if ad_ in ("Bitcoin", "Ethereum") else None
    if lg: ad_ = f'<img src="{lg}" alt="" style="width:18px;height:18px;vertical-align:-3px;margin-right:6px">{ad_}'
    return (f'<div class="pk"><div><div class="pk-ad">{ad_}</div><div class="pk-d">{deger}{birim}</div>'
            f'<span class="rozet {sinif}">{ok} {br.yz(d)}</span> {_vk_tam(v)}<div class="pk-alt">{alt}</div></div>'
            f'<div>{spark_svg(v["seri"], renk)}</div></div>')


MINI_LOGO = {"Bitcoin": ("BTC", "kripto"), "Ethereum": ("ETH", "kripto")}


def makro_karti(m):
    """TÜFE + politika faizi + reel faiz kartı (TCMB)."""
    t = m["tufe"]["seri"]; s = t[0]
    seri = list(reversed(t[:13]))
    mx = max(r["yillik"] for r in seri); mn = min(r["yillik"] for r in seri)
    w, h = 300, 60
    nok = " ".join(f"{i * w / max(1, len(seri) - 1):.1f},{h - 6 - (r['yillik'] - mn) / max(1e-9, mx - mn) * (h - 12):.1f}" for i, r in enumerate(seri))
    svg = (f'<svg width="100%" viewBox="0 0 {w} {h}" preserveAspectRatio="none" style="height:60px">'
           f'<polyline points="{nok}" fill="none" stroke="#E8B84A" stroke-width="2"/></svg>')
    onc = t[1]["yillik"] if len(t) > 1 else None
    yon = "" if onc is None else (f'<span class="rozet {"k" if s["yillik"] > onc else "y"}">'
                                  f'{"▲" if s["yillik"] > onc else "▼"} önceki ay %{br.ond(onc, 2)}</span>')
    f = m.get("faiz") or {}
    sat = []
    if s.get("aylik") is not None: sat.append(f'Aylık %{br.ond(s["aylik"], 2)}')
    if f: sat.append(f'Politika faizi <b>%{br.ond(f["oran"], 2)}</b> ({f["tarih"][8:10]}.{f["tarih"][5:7]}.{f["tarih"][:4]})')
    if m.get("reel_faiz") is not None: sat.append(f'Reel faiz <b>{"+" if m["reel_faiz"] >= 0 else "−"}%{br.ond(abs(m["reel_faiz"]), 1)}</b>')
    bayat = m["tufe"].get("bayat") or f.get("bayat")
    vk = VK.rozet_html({"durum": "bayat" if bayat else "aylık veri", "renk": "#EF4444" if bayat else "#A1A1AA",
                        "aciklama": "TCMB sitesine son denemede ulaşılamadı; son kayıtlı değer." if bayat else "Aylık açıklanan resmi veri."})
    return (f'<div class="pk" style="display:block"><div class="pk-ad">Yıllık enflasyon (TÜFE) · {MT.donem_adi(s["donem"])} {vk}</div>'
            f'<div class="pk-d">%{br.ond(s["yillik"], 2)}</div>{yon}'
            f'<div style="margin-top:8px">{svg}</div>'
            f'<div class="pk-alt">{" · ".join(sat)}<br>Kaynak: {m["tufe"]["kaynak"]} · son 13 ay. TÜFE her ayın 3\'ünde 10:00\'da açıklanır.</div></div>')


def mini_kart(ad_, v):
    """Ana sayfadaki yatay şerit için küçük piyasa kartı."""
    d = v.get("d1G") or 0; renk = "#22C55E" if d > 0 else "#EF4444" if d < 0 else "#A1A1AA"
    ok = "▲" if d > 0 else "▼" if d < 0 else "■"
    deger = br.ond(v["deger"], 2 if v["deger"] < 10000 else 0)
    lg = ""
    if ad_ in MINI_LOGO:
        import logolar as LG
        u = LG.logo_url(*MINI_LOGO[ad_])
        if u: lg = f'<img src="{u}" alt="" class="mk-l">'
    vk = VK.rozet_html(VK.etiket(v.get("zaman"), v.get("tur"))) if v.get("tur") else ""
    return (f'<div class="mk"><div class="mk-a">{lg}{ad_}</div><div class="mk-d">{deger}</div>'
            f'<div class="mk-y" style="color:{renk}">{ok} {br.yz(d)} {vk}</div>{spark_svg(v["seri"], renk, 116, 30)}</div>')


def _arama_secenekleri():
    import bist_abd as AB
    out = {}
    for s in bv.arama_secenekleri(): out[f"BIST · {s}"] = (bv.secimden_kod(s), "Hisse")
    for k, v in V.VARLIKLAR.items():
        if v[2] == "kripto": out[f"Kripto · {k} — {v[1]}"] = (f"{k}/USDT", "Kripto")
        elif v[2] == "emtia": out[f"Emtia · {k} — {v[1]}"] = (k, "Emtia")
    for k, ad in AB.DEV.items(): out[f"ABD · {k} — {ad}"] = (AB.kod_yap(k), "ABD")
    for k, ad in (("SP500", "S&P 500"), ("NASDAQ", "Nasdaq"), ("VIX", "VIX")): out[f"Endeks · {k} — {ad}"] = (k, "ABD")
    out["Endeks · XU100 — BIST 100"] = ("XU100", "Hisse"); out["Endeks · XU030 — BIST 30"] = ("XU030", "Hisse")
    return out


ARAMA_SECENEK = _arama_secenekleri()


def _ara_sec():
    s = st.session_state.get("ana_ara")
    if s and s in ARAMA_SECENEK:
        kod, tur = ARAMA_SECENEK[s]
        st.session_state["kk_istek"] = f"{kod}|{tur}||{dt.datetime.now().timestamp():.0f}"
        st.session_state["_kk_git"] = True
        st.session_state["ana_ara"] = None


ULKE_BAYRAK = {"USD": "🇺🇸", "EUR": "🇪🇺", "CNY": "🇨🇳", "GBP": "🇬🇧", "JPY": "🇯🇵", "TRY": "🇹🇷"}


def _veri_tr(baslik, ulke):
    try:
        import ses as SES
        return SES.veri_adi(baslik, None)
    except Exception:
        return baslik


def takvim_mini(e):
    t_ = pd.Timestamp(e["zaman"])
    return (f'<div class="mk" style="width:168px"><div class="mk-a">{ULKE_BAYRAK.get(e["ulke"], "")} {t_:%d.%m · %H:%M}</div>'
            f'<div style="font-size:.84rem;font-weight:750;margin-top:4px;line-height:1.25">{_veri_tr(e["baslik"], e["ulke"])[:60]}</div>'
            f'<div class="mk-a" style="margin:4px 0 6px">{("beklenti " + e["beklenti"]) if e.get("beklenti") else "&nbsp;"}</div></div>')


def takvim_karti(t_, e, arsiv, simdi_):
    x = [a_ for a_ in arsiv if a_["baslik"] == e["baslik"] and a_["ulke"] == e["ulke"] and a_.get("tepki")]
    tep = []
    for v in ("Altın", "S&P 500 vadeli", "Bitcoin", "Dolar/TL"):
        d = [a_["tepki"][v]["1s"] for a_ in x if v in a_["tepki"] and "1s" in a_["tepki"][v]]
        if d: tep.append(f'<span class="cip">{v} ±%' + f"{sum(abs(z) for z in d) / len(d) * 100:.1f}".replace(".", ",") + "</span>")
    gecti = t_ < simdi_
    dk = int((t_ - simdi_).total_seconds() // 60)
    durum = ('<span class="cip">açıklandı</span>' if gecti else
             f'<span class="cip cip-a">{dk // 60} sa {dk % 60} dk sonra</span>' if dk < 24 * 60 else f'<span class="cip cip-a">yaklaşıyor</span>')
    kutu = "".join(f'<div><div class="vb-e">{ad}</div><b>{e.get(k) or "–"}</b></div>' for ad, k in (("Beklenti", "beklenti"), ("Önceki", "onceki")))
    return (f'<div class="tk{" tk-g" if gecti else ""}"><div class="tk-s">{t_:%H:%M}<small>{ULKE_BAYRAK.get(e["ulke"], "")} {HB.ULKE_AD.get(e["ulke"], e["ulke"])}</small></div>'
            f'<div class="tk-i"><b>{_veri_tr(e["baslik"], e["ulke"])}</b><div class="vb-e">{e["baslik"]}</div>'
            f'<div class="tk-k">{kutu}</div>'
            f'<div class="cipler">{durum}{"".join(tep)}</div>'
            f'{f"<div class=vb-e>Geçmişte açıklamadan sonraki 1 saatteki ortalama hareket ({len(x)} açıklama)</div>" if tep else ""}</div></div>')


def haber_karti(a):
    import html as _h
    try: z = pd.Timestamp(a["zaman"]).tz_convert("Europe/Istanbul")
    except Exception: z = None
    jeo = a["tur"].startswith("Jeopolitik")
    renk = "#E8B84A" if jeo else "#22C55E" if a["yon"] > 0 else "#EF4444"
    etki = HB.etki_ad(a)
    var = []
    for v in a.get("varliklar") or []:
        ad = HB.VARLIK_AD.get(v["kod"], v["kod"]); ok = "▲" if v["isaret"] > 0 else "▼"
        r = v.get("tepki") or {}; dg = r.get("degisim")
        rk = "#4ADE80" if v["isaret"] > 0 else "#F87171"
        var.append(f'<span class="cip" title="{_h.escape(v.get("gerekce", ""))}"><b style="color:{rk}">{ok}</b> {ad}'
                   f'{(" · " + br.yz(dg)) if dg not in (None, 0) else ""}</span>')
    yildiz = "●" * int(a.get("onem") or 1)
    link = f'<a href="{_h.escape(a["link"])}" target="_blank" rel="noopener" class="hb-l">Habere git ›</a>' if a.get("link") else ""
    return (f'<div class="hb" style="--v:{renk}"><div class="hb-u"><span class="cip" style="color:{renk};border-color:{renk}55">{_h.escape(a["tur"])}</span>'
            f'<span class="vb-e">{z:%d.%m %H:%M} · {_h.escape(a.get("kaynak") or "")} <span style="color:#E8B84A">{yildiz}</span></span></div>'
            f'<div class="hb-b">{_h.escape(a["baslik"])}</div>'
            f'<div class="hb-e" style="color:{renk}">{etki}</div>'
            f'<div class="cipler">{"".join(var)}</div>{link}</div>')


@st.cache_data(ttl=600, show_spinner=False)
def bist_ozet(zaman):
    import requests
    r = requests.get(f"https://raw.githubusercontent.com/{REPO}/bulten/bist/ozet.csv?t={zaman}", timeout=20)
    return pd.read_csv(io.BytesIO(r.content)).set_index("Kod") if r.status_code == 200 else None


def one_cikanlar(PV):
    import logolar as LG
    fav = [x for x in st.query_params.get("takip", "").split(",") if x] or ["THYAO", "ASELS", "GARAN", "BIMAS", "TUPRS", "KCHOL"]
    oz = bist_ozet(ZAMAN); satir = []
    def _sat(logo, kis, ad, fiyat, deg, alt="", istek=None):
        renk = "#4ADE80" if (deg or 0) > 0 else "#F87171" if (deg or 0) < 0 else "#A1A1AA"
        zem = "rgba(34,197,94,.16)" if (deg or 0) > 0 else "rgba(239,68,68,.16)" if (deg or 0) < 0 else "rgba(255,255,255,.06)"
        lg = f'<img src="{logo}" alt="" class="oc-l">' if logo else f'<span class="oc-h">{kis[:3]}</span>'
        return (f'<div class="oc">{lg}<div class="oc-a"><b>{kis}</b><div>{ad}{(" · " + alt) if alt else ""}</div></div>'
                f'<div class="oc-f"><b>{fiyat}</b><br><span class="oc-p" style="color:{renk};background:{zem}">{br.yz(deg) if deg is not None else "–"}</span></div>'
                + (f'<div class="oc-d"><span class="oc-b" role="button" data-kk="{istek}||">Analiz</span>'
                   f'<span class="oc-b oc-b2" role="button" data-kk="{istek}|seviye|">Seviye</span></div>' if istek else "") + '</div>')
    for k in fav[:8]:
        if oz is not None and k in oz.index:
            r = oz.loc[k]
            satir.append(_sat(LG.logo_url(k, "bist"), k, str(r.get("Ad", ""))[:30], TK.sayi(r["Fiyat"]), r.get("Değişim"), str(r.get("Genel", "")),
                              istek=f"{k}|Hisse"))
    for ad_, kis, pz in (("Bitcoin", "BTC", "kripto"), ("Ethereum", "ETH", "kripto"), ("Gram altın", "ALTIN", "emtia")):
        v = PV.get(ad_)
        if v: satir.append(_sat(LG.logo_url(kis, pz) if pz == "kripto" else None, kis if pz == "kripto" else "Gram", ad_,
                                 br.ond(v["deger"], 2 if v["deger"] < 10000 else 0), v.get("d1G"),
                                 istek=f"{kis}/USDT|Kripto" if pz == "kripto" else "GRAMALTIN|Emtia"))
    return "".join(satir)


@st.cache_data(ttl=600, show_spinner=False)
def gunun_firsatlari(zaman, n=8):
    """Tüm piyasalardaki son taramalardan taze fırsatlar, puana göre."""
    import requests
    out = []
    simdi = pd.Timestamp.now(tz="UTC")
    for pz in ("bist", "kripto", "abd", "emtia"):
        try:
            r = requests.get(f"https://raw.githubusercontent.com/{REPO}/bulten/firsat/{pz}/son.json?t={zaman}", timeout=15)
            son = r.json() if r.status_code == 200 else {}
        except Exception:
            son = {}
        for tf, x in (son or {}).items():
            try:
                z = pd.Timestamp(x["zaman"]); z = z if z.tzinfo else z.tz_localize("UTC")
                if simdi - z > pd.Timedelta(hours=30 if pz == "kripto" else 80): continue
            except Exception:
                continue
            for f in x.get("firsatlar", []): out.append({**f, "pz": pz})
    return sorted(out, key=lambda f: -f.get("puan", 0))[:n]


def firsat_mini(f):
    import logolar as LG
    al = f["yon"] == 1; renk = "#22C55E" if al else "#EF4444"
    pz_ad = {"bist": "BIST", "kripto": "Kripto", "abd": "ABD", "emtia": "Emtia"}[f["pz"]]
    u = LG.logo_url(f["kod"], f["pz"]); lg = f'<img src="{u}" alt="" class="mk-l">' if u else ""
    p = f.get("plan") or {}; g = p.get("giris"); st_ = p.get("stop"); h1 = (p.get("hedef") or [{}])[0].get("fiyat")
    rr = (p.get("hedef") or [{}, {}])[1].get("r") if len(p.get("hedef") or []) > 1 else None
    plan = f"giriş {FR.fy(g)} · stop {FR.fy(st_)} · H1 {FR.fy(h1)}" if g else ""
    puan = float(f.get("puan", 0))
    kis = str(f["kod"]).replace(".US", "").split("/")[0].split("@")[0]
    return (f'<div class="fk" style="--v:{renk}"><div class="fk-u"><b>{lg}{kis}</b>'
            f'<span class="fk-e" style="background:{renk}">{"AL" if al else "SAT"}</span></div>'
            f'<div class="fk-s">{pz_ad} · {TK.TF_AD.get(f["tf"], f["tf"])} · {f.get("kurulum_ad", "")[:34]}</div>'
            f'<div class="fk-c"><div style="width:{min(puan, 100):.0f}%"></div></div>'
            f'<div class="fk-s"><span>Puan {puan:.0f}/100</span>{f" · K/R 1:{rr:.1f}".replace(".", ",") if rr else ""}</div>'
            f'<div class="fk-p">{plan}</div></div>')


@st.cache_data(ttl=600, show_spinner=False)
def gorsel_oku(yol, zaman):
    import requests
    try:
        r = requests.get(f"https://raw.githubusercontent.com/{REPO}/bulten/{yol}?t={zaman}", timeout=20)
        return r.content if r.status_code == 200 else None
    except Exception:
        return None


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def ilk_cek(kodlar, gun, surum):
    return EV.ilk_islemler(list(kodlar))


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def resmi_ilk_cek(gun, surum):
    try: return BB.ilk_islem()
    except Exception: return {}


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


@st.cache_data(ttl=5 * 60, show_spinner=False)
def alarm_son(zaman):
    import requests
    try:
        s = requests.get(f"https://raw.githubusercontent.com/{REPO}/bulten/alarm/son.json?t={zaman}", timeout=15).json()
        k = requests.get(f"https://raw.githubusercontent.com/{REPO}/bulten/alarm/son_kontrol.json?t={zaman}", timeout=15).json()
        return s, k
    except Exception:
        return [], {}


def radar_png(S):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt, numpy as np, io as _io
    kat = list(next(iter(S.values()))["saglik"].keys())
    if not kat: return None
    ac = np.linspace(0, 2 * np.pi, len(kat), endpoint=False).tolist(); ac += ac[:1]
    fig = plt.figure(figsize=(5.2, 4.6), dpi=130, facecolor="#0B0B0C"); ax = fig.add_subplot(111, polar=True, facecolor="#17181B")
    ax.tick_params(colors="#D4D4D8"); ax.spines["polar"].set_color("#2A2B30"); ax.grid(color="#2A2B30", lw=.6)
    renk = ["#E8B84A", "#60A5FA", "#22C55E"]
    for (k, r), c in zip(S.items(), renk):
        v = [float(r["saglik"].get(x) or 0) for x in kat]; v += v[:1]
        ax.plot(ac, v, color=c, lw=2, label=k); ax.fill(ac, v, color=c, alpha=0.12)
    ax.set_xticks(ac[:-1]); ax.set_xticklabels(kat, fontsize=8); ax.set_ylim(0, 5); ax.set_yticks([1, 2, 3, 4, 5]); ax.tick_params(axis="y", labelsize=6)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.12), fontsize=8, frameon=False, labelcolor="#F4F4F5")
    b = _io.BytesIO(); fig.tight_layout(); fig.savefig(b, format="png", facecolor=fig.get_facecolor()); plt.close(fig)
    return b.getvalue()


# Dört ana bölüm (alt menüyle aynı): Ana Sayfa · Keşfet · Portföy · Takip. Eski sekmeler bunların altında.
ana_b, kesfet_b, portfoy_b, takip_b = st.tabs([":material/home: Ana Sayfa", ":material/explore: Keşfet",
                                               ":material/account_balance_wallet: Portföy", ":material/star: Takip"])
with ana_b:
    tab_p, tab_h, tab_tk = st.tabs([":material/dashboard: Piyasalar", ":material/newspaper: Haberler", ":material/event: Takvim"])
with kesfet_b:
    tab_f, tab_r, tab_x, tab_t, tab_v, tab_b, tab_k = st.tabs(
        [":material/my_location: Fırsatlar", ":material/description: Hisse", ":material/candlestick_chart: Teknik",
         ":material/manage_search: Tarayıcı", ":material/currency_bitcoin: Emtia & Kripto", ":material/school: Bebek",
         ":material/balance: Karşılaştır"])
with portfoy_b:
    tab_pf, tab_pr = st.tabs([":material/pie_chart: Varlıklarım", ":material/insights: Performans"])
with takip_b:
    tab_w, tab_al = st.tabs([":material/bookmark: Favoriler", ":material/notifications_active: Alarmlar"])


import makro_tr as MT
import veri_kalite as VK
_MAKRO = json_oku("makro/tr_makro.json", dt.datetime.now().strftime("%Y%m%d%H"))
_ENF_TCMB = (_MAKRO or {}).get("tufe", {}).get("seri", [{}])[0].get("yillik") if _MAKRO else None
with takip_b:
  with st.expander(":material/tune: Ayarlar ve varsayımlar"):
      if st.button(":material/refresh: Verileri yenile (önbelleği temizle)", key="yenile"):
          st.cache_data.clear()
          for k_ in ("sonuc", "v_sonuc", "v_tablo", "tarama", "kars", "bebek", "bebek_derin", "tk_sonuc", "pf"):
              st.session_state.pop(k_, None)
          st.rerun()
      c1, c2 = st.columns(2)
      rf = c1.number_input("Risksiz faiz (TR 10Y)", value=0.366, step=0.01, format="%.4f")
      _enf_v = OTO.get("enflasyon") or (round(_ENF_TCMB / 100, 4) if _ENF_TCMB else 0.2977)
      enf = c2.number_input("Yıllık enflasyon" + (" (EVDS)" if "enflasyon" in OTO else " (TCMB)" if _ENF_TCMB else ""), value=float(_enf_v),
                            step=0.01, format="%.4f")
      erp = c1.number_input("Hisse risk primi", value=0.07, step=0.005, format="%.3f")
      g = c2.number_input("DCF uç büyüme", value=0.15, step=0.01, format="%.3f")
      st.caption("Enflasyon her sabah TCMB'nin sitesinden otomatik alınır (EVDS anahtarı varsa o öncelikli); diğerleri Kasım 2026 piyasa verilerine göre ayarlıdır.")
      yeni_k = st.text_input("TCMB EVDS API anahtarı (isteğe bağlı)", value="", type="password",
                             help="evds3.tcmb.gov.tr → Benim Sayfam → API anahtarı. Kalıcı olması için Streamlit Secrets'a EVDS_KEY olarak ekleyin.")
      if yeni_k:
          st.session_state["evds_key"] = yeni_k
with takip_b:
  with st.expander(":material/database: Veri kaynakları ve gecikmeler"):
      st.markdown("".join(
          f'<div class="hb" style="--v:#E8B84A"><div class="hb-u"><b>{alan}</b><span class="cip">{gec}</span></div>'
          f'<div style="font-size:.8rem;margin-top:6px;line-height:1.45">Birincil: {bir}<br>Yedek: {yed}' + (f'<br><span style="color:#A1A1AA">{not_}</span>' if not_ else "") + '</div></div>'
          for alan, bir, yed, gec, not_ in VK.KAYNAKLAR), unsafe_allow_html=True)
      st.caption("Kartlardaki etiketler: anlık (yeşil) · gecikmeli (altın, ~15 dk) · kapanış (gri, piyasa kapalı) · bayat (kırmızı, veri beklenenden eski).")
PRM = dict(rf=rf, enflasyon=enf, erp=erp, terminal_g=g)
GUN = dt.date.today().isoformat()
_s = dt.datetime.now()
ZAMAN = _s.strftime("%Y%m%d%H") + str(_s.minute // 15)   # fiyatlı analizler en fazla 15 dk önbellekte kalır
SAAT2 = _s.strftime("%Y%m%d") + str(_s.hour // 2)        # taramalar en fazla 2 saat
import streamlit.components.v1 as _bil
try:
    _pv_ust = piyasa_verisi(ZAMAN)
except Exception:
    _pv_ust = None
# Ana sayfadaki satır düğmeleri (Analiz / Seviye) bu gizli kutuya "KOD|TÜR|BÖLÜM|zaman" yazar (uygulama_stil.CANLI_JS → kkIstek)
with st.container(key="kk_gizli"):
    st.text_input("istek", key="kk_istek", label_visibility="collapsed")
_ist = st.session_state.get("kk_istek") or ""
if _ist and _ist != st.session_state.get("_kk_son"):
    st.session_state["_kk_son"] = _ist
    _p = (_ist.split("|") + ["", "", ""])[:3]
    if _p[0]:
        st.session_state["tk_tur"] = _p[1] if _p[1] in ("Hisse", "ABD", "Emtia", "Kripto") else "Hisse"
        st.session_state["_kk_analiz"] = (_p[0], _p[2])
with _ust_yer.container():
    try: _hb_ust = json_oku("haber/son.json", ZAMAN) or []
    except Exception: _hb_ust = []
    _bil.html(TS.ust_kompakt_sayfa(_pv_ust, _hb_ust), height=176)




EVREN, HARZ, EVREN_NOT = evren_cek(GUN, br.SURUM)
try:
    bv.guncelle({r["Kod"]: r.get("Ad") for _, r in EVREN.iterrows()})
except Exception:
    pass






























# ================= RAPOR =================


with tab_r:
    r_tur = st.radio("Piyasa", ["BIST", "ABD", "Kripto", "Emtia"], horizontal=True, key="r_tur")
    if r_tur in ("Kripto", "Emtia"):
        if r_tur == "Kripto":
            r_vk = kripto_sec("r_k"); r_vs = r_vk
        else:
            r_vs = st.selectbox("Emtia", [f"{k} — {v[1]}" for k, v in V.VARLIKLAR.items() if v[2] == "emtia"], index=None,
                                placeholder="Örn. Altın, Brent, Gümüş", key="r_vsec")
            r_vk = r_vs.split(" — ")[0] if r_vs else ""
        if st.button(":material/description: Rapor Oluştur", type="primary", disabled=not r_vk, key="r_vbtn"):
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
        if st.button(":material/description: Rapor Oluştur", type="primary", disabled=not kod, key="r_btn"):
            try:
                with st.status(f"{kod} analiz ediliyor… (30–60 sn)") as s:
                    st.session_state.sonuc = analiz(kod, emsal, tuple(PRM.items()), ZAMAN, br.SURUM)
                    s.update(label="Rapor hazır ✓", state="complete", expanded=False)
            except Exception as e:
                st.error(f"Rapor oluşturulamadı: {e}\n\nKodu kontrol edin veya biraz sonra tekrar deneyin.")

        if "sonuc" in st.session_state:
            r = st.session_state.sonuc; o = r["ozet"]
            st.markdown(baslik_seridi(o["Kod"], o["Şirket"], "abd" if str(o["Kod"]).endswith(".US") else "bist"), unsafe_allow_html=True)
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
            st.download_button(":material/download: PDF Raporu İndir", data=r["pdf"], file_name=r["dosya"], mime="application/pdf", type="primary")
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
                            kart(c_, f"TEKNİK · {TK.TF_AD[tf].upper()}", e_, f"Puan {p_:.0f}/100", ETK_RENK.get(e_))
                if r.get("tek"):
                    st.markdown("**Temel göstergeler karnesi**")
                    for soru, cevap, durum in r["tek"]:
                        st.markdown(f"{DURUM_EMOJI.get(durum, '⚪')} **{soru}**  \n{cevap}")
                ileri_goster(r.get("ileri"))
                with st.expander(":material/receipt_long: Başlıklar itibarıyla değerlendirme", expanded=False):
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
    if st.session_state.get("_kk_analiz"):
        _kk, _bo = st.session_state.pop("_kk_analiz")
        try:
            with st.status(f"{_kk} teknik analizi yapılıyor… (15–40 sn)") as s_:
                st.session_state.tk_sonuc = teknik_analiz(_kk, ZAMAN, br.SURUM, False)
                s_.update(label="Hazır ✓", state="complete", expanded=False)
        except Exception as e:
            st.error(f"Teknik analiz yapılamadı: {e}")
    if st.button(":material/candlestick_chart: Teknik analiz yap", type="primary", disabled=not tk_kod, key="tk_btn"):
        try:
            with st.status(f"{tk_kod} teknik analizi yapılıyor… (15–40 sn)") as s_:
                st.session_state.tk_sonuc = teknik_analiz(tk_kod, ZAMAN, br.SURUM, st.session_state.get("tk_kisa", False))
                s_.update(label="Hazır ✓", state="complete", expanded=False)
        except Exception as e:
            st.error(f"Teknik analiz yapılamadı: {e}")
    if "tk_sonuc" in st.session_state:
        r = st.session_state.tk_sonuc
        _pz = {"Hisse": "bist", "ABD": "abd", "Kripto": "kripto", "Emtia": "emtia"}.get(st.session_state.get("tk_tur"), "bist")
        try:
            st.markdown(varlik_baslik(r, _pz), unsafe_allow_html=True)
            kart(st, "GENEL TEKNİK GÖRÜNÜM", r["etiket"], f"Puan {r['puan']:.0f}/100 (günlük %30, haftalık %40, aylık %30)", ETK_RENK.get(r["etiket"]))
            st.markdown(seviye_karti(r), unsafe_allow_html=True)
            st.markdown(katkay_notu(r), unsafe_allow_html=True)
        except Exception as ex:
            st.markdown(f"### {r['ad']} ({r['kod']})"); st.caption(f"Görünüm kartı çizilemedi: {ex}")
        if r["tf"].get("1S") or r["tf"].get("4S"):
            cols = st.columns(2)
            for c_, tf in zip(cols, ("1S", "4S")):
                x = r["tf"].get(tf)
                if x: kart(c_, TK.TF_AD[tf].upper(), x["etiket"], f"{x['puan']:.0f} · Al {x['sayim']['AL']} / Sat {x['sayim']['SAT']}", ETK_RENK.get(x["etiket"]))
        st.download_button(":material/download: Teknik PDF raporu", data=r["pdf"], file_name=r["dosya"], mime="application/pdf", type="primary", key="tk_dl")
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
    st.markdown(TS.bb("Kapanış bültenleri"), unsafe_allow_html=True)
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
        if B.get("kart"): st.image(B["kart"], use_container_width=True)
        st.download_button(":material/download: Bülten PDF", data=B["pdf"], file_name=f"{mt['piyasa']}_bulten_{mt['kapanis']}.pdf", mime="application/pdf", key="bul_dl")
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
                    st.download_button(f":material/download: {ad_}", data=b_, file_name=ad_, mime="application/pdf", key=f"bul_{ad_}")

# ================= EMTİA & KRİPTO =================


# ================= FIRSATLAR =================




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
            st.markdown(TS.bb(f"{TK.TF_AD[tf]} · {len(x['firsatlar'])} fırsat"), unsafe_allow_html=True)
            st.caption(f"Tarama: {z:%d.%m.%Y %H:%M} TSİ · {x.get('taranan', 0)} likit varlık")
            if not x["firsatlar"]:
                st.write("Bu turda eşiği (puan ≥ 55, risk/ödül ≥ 2R) geçen yeni kurulum çıkmadı.")
            for f in x["firsatlar"]:
                with st.container(border=True):
                    if (tf, f["kod"]) in FD["graf"]:
                        st.image(FD["graf"][(tf, f["kod"])], use_container_width=True)
                    else:
                        try: st.markdown(_md(FR.firsat_metni(f)))
                        except Exception as ex: st.write(f.get("kod"), ex)
                    with st.expander("Kurulum açıklaması ve tüm ayrıntılar"):
                        try: st.markdown(_md(FR.firsat_metni(f)))
                        except Exception: pass
                        st.write(f.get("aciklama", ""))
                        for b in f.get("balina", []): st.markdown(f"🐋 **{b[0]}** — {b[2]}")
            if x.get("adaylar"):
                with st.expander(f"Eşik altında kalan adaylar ({len(x['adaylar'])})"):
                    st.dataframe(pd.DataFrame(x["adaylar"]).rename(columns={"kod": "Kod", "yon": "Yön", "kurulum": "Kurulum", "puan": "Puan"}),
                                 hide_index=True, use_container_width=True)
        ol = FD.get("olaylar") or []
        if ol:
            st.markdown(TS.bb("Son takip olayları"), unsafe_allow_html=True)
            for o in reversed(ol[-15:]):
                z = pd.Timestamp(o["zaman"]).tz_convert("Europe/Istanbul")
                st.markdown(f"`{z:%d.%m %H:%M}` " + _md(o["metin"]))
    with f2:
        ac = FD.get("acik") or []
        if not ac: st.info("Açık kurulum yok.")
        else:
            import logolar as LG
            st.dataframe(pd.DataFrame([{**({"": LG.logo_url(k["kod"], fk)} if fk != "emtia" else {}), "Kod": k["kod"], "Dilim": TK.TF_AD[k["tf"]], "Yön": "AL" if k["yon"] == 1 else "SAT", "Kurulum": k["kurulum"],
                                        "Giriş": FR.fy(k["giris"]), "Stop": FR.fy(k["stop"]) + (" (girişte)" if k["asama"] else ""),
                                        "H1": FR.fy(k["hedef"][0]), "H2": FR.fy(k["hedef"][1]), "H3": FR.fy(k["hedef"][2]),
                                        "Görülen hedef": k["asama"], "Son fiyat": FR.fy(k.get("son_fiyat")),
                                        "Getiri": FR.yz((k.get("son_fiyat", k["giris"]) - k["giris"]) / k["giris"] * k["yon"]),
                                        "Bitiş": str(k["bitis"])[:16].replace("T", " ")} for k in ac]), hide_index=True, use_container_width=True,
                         column_config={"": st.column_config.ImageColumn("", width="small")} if fk != "emtia" else None)
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


with tab_h:
    st.caption("Piyasayı etkileyebilecek haberler 30 dakikada bir taranır: türü ve yönü sınıflandırılır, etkilenecek varlıklar "
               "gerekçesiyle gösterilir, haberden bu yana fiyat/hacim tepkisi ve teknik durum eklenir.")
    HD = haber_oku(ZAMAN)
    tkv = (HD.get("takvim") or {}).get("liste") or []
    simdi_ = pd.Timestamp.now(tz="Europe/Istanbul")
    yaklasan = [e for e in tkv if pd.Timestamp(e["zaman"]) >= simdi_ - pd.Timedelta(hours=2)]
    if yaklasan:
        st.markdown(TS.bb("Yaklaşan veriler"), unsafe_allow_html=True)
        st.markdown('<div class="serit-k">' + "".join(takvim_mini(e) for e in yaklasan[:12]) + "</div>", unsafe_allow_html=True)
    st.markdown(TS.bb("Haber akışı"), unsafe_allow_html=True)
    son_h = HD.get("son") or []
    if not son_h:
        st.info("Henüz analiz edilmiş haber yok. İlk tarama alarm kontrolüyle birlikte yapılır.")
    tur_sec = st.multiselect("Haber türü", sorted({x["tur"] for x in son_h}), key="hb_tur", placeholder="Tümü")
    st.markdown("".join(haber_karti(a) for a in son_h[:60] if not tur_sec or a["tur"] in tur_sec), unsafe_allow_html=True)

# ================= TAKVİM =================


with tab_tk:
    st.caption("Bu haftanın yüksek etkili ekonomik verileri (ABD, Euro Bölgesi, Çin, İngiltere, Japonya). Saatler Türkiye saatidir. "
               "Geçmiş tepki, aynı veri daha önce açıklandığında altın, S&P 500 vadeli, Bitcoin ve dolar/TL'nin ilk 1 saatteki ortalama hareketidir.")
    tkv = (json_oku("haber/takvim.json", ZAMAN) or {}).get("liste") or []
    arsiv = json_oku("haber/takvim_arsiv.json", ZAMAN) or []
    if not tkv:
        st.info("Takvim verisi henüz yok; her sabah 07:00'den sonra güncellenir.")
    simdi_ = pd.Timestamp.now(tz="Europe/Istanbul")
    gunler_ = {}
    for e in tkv:
        t_ = pd.Timestamp(e["zaman"])
        if t_ < simdi_ - pd.Timedelta(days=7): continue   # bu haftanın açıklanmış verileri de (soluk) görünür
        gunler_.setdefault(t_.strftime("%d.%m.%Y %A"), []).append((t_, e))
    if tkv and not any(pd.Timestamp(e["zaman"]) >= simdi_ for e in tkv):
        st.info("Bu hafta açıklanacak yüksek etkili veri kalmadı; yeni haftanın takvimi pazartesi sabahı gelir. Bu haftanın açıklanmış verileri aşağıda.")
    GUN_TR = {"Monday": "Pazartesi", "Tuesday": "Salı", "Wednesday": "Çarşamba", "Thursday": "Perşembe", "Friday": "Cuma", "Saturday": "Cumartesi", "Sunday": "Pazar"}
    for g_, liste_ in gunler_.items():
        tarih_, gun_ = g_.split(" ")
        st.markdown(TS.bb(f"{GUN_TR.get(gun_, gun_)} · {tarih_}"), unsafe_allow_html=True)
        st.markdown("".join(takvim_karti(t_, e, arsiv, simdi_) for t_, e in liste_), unsafe_allow_html=True)
    st.caption("Kural: beklentiden güçlü ABD verisi genellikle doları ve faiz beklentisini yükseltir, altın ve kripto üzerinde baskı yaratır; zayıf veri tersini yapar.")

# ================= PERFORMANS =================
with tab_pr:
    st.caption("Sistemin gönderdiği fırsatların gerçek sonuçları. Her kurulum giriş fiyatından izlenir; H1'de yarısı, H2'de %30'u, H3'te kalanı "
               "kapatılır, H1 sonrası stop girişe çekilir. R: stop mesafesi kadar risk birimi (+1R = riske edilen kadar kazanç).")
    tum, acik_t = [], []
    for pz, ad_ in (("bist", "BIST"), ("abd", "ABD"), ("kripto", "Kripto"), ("emtia", "Emtia")):
        for k in json_oku(f"firsat/{pz}/gecmis.json", ZAMAN) or []: tum.append({**k, "Piyasa": ad_})
        for k in json_oku(f"firsat/{pz}/acik.json", ZAMAN) or []: acik_t.append({**k, "Piyasa": ad_})
    pf_ = FR.performans(tum)
    c1, c2, c3, c4 = st.columns(4)
    if pf_:
        kart(c1, "KAPANAN", f"{pf_['n']}", f"açık {len(acik_t)}")
        kart(c2, "İLK HEDEF", f"%{pf_['h1'] * 100:.0f}", "stoptan önce", "#22C55E" if pf_["h1"] >= 0.5 else "#E8B84A")
        kart(c3, "KAZANAN", f"%{pf_['kazanc'] * 100:.0f}", "R > 0", "#22C55E" if pf_["kazanc"] >= 0.5 else "#E8B84A")
        kart(c4, "ORT. SONUÇ", FR.rrs(pf_["ort_R"]), f"toplam {FR.rrs(pf_['top_R'])}", "#1E8E5A" if pf_["ort_R"] > 0 else "#C0392B")
        df_ = pd.DataFrame(tum)
        df_["kapanis_t"] = pd.to_datetime(df_["kapanis"].astype(str).str[:19], errors="coerce")
        df_ = df_.sort_values("kapanis_t")
        st.markdown("**Birikimli sonuç (R)**")
        st.line_chart(df_.set_index("kapanis_t")["R"].cumsum().rename("Toplam R"), height=220)
        df_["Ay"] = df_["kapanis_t"].dt.strftime("%Y-%m")
        tablolar = []
        for ad_, grp in (("Piyasa", "Piyasa"), ("Zaman dilimi", "tf"), ("Kurulum", "kurulum"), ("Ay", "Ay")):
            t_ = []
            for kk, g in df_.groupby(grp):
                p_ = FR.performans(g.to_dict("records"))
                t_.append({ad_: TK.TF_AD.get(kk, kk) if grp == "tf" else kk, "Adet": p_["n"], "İlk hedef %": round(p_["h1"] * 100),
                           "Kazanan %": round(p_["kazanc"] * 100), "Ort. R": round(p_["ort_R"], 2), "Toplam R": round(p_["top_R"], 1)})
            tablolar.append((ad_, pd.DataFrame(t_)))
        for ad_, t_ in tablolar:
            with st.expander({"Piyasa": "Piyasaya göre", "Zaman dilimi": "Zaman dilimine göre", "Kurulum": "Kurulum türüne göre", "Ay": "Aylara göre"}[ad_],
                             expanded=ad_ == "Piyasa"):
                st.dataframe(t_.sort_values("Adet", ascending=False), hide_index=True, use_container_width=True,
                             column_config={"Ort. R": st.column_config.NumberColumn(format="%+.2f")})
        st.markdown("**Kapanan kurulumlar** (en yeniden eskiye)")
        import logolar as LG
        _sebep = {"stop": "Stop", "tüm hedefler": "Tüm hedefler", "süre doldu": "Süre doldu"}
        st.dataframe(pd.DataFrame([{
            "": LG.logo_url(r.kod, {"BIST": "bist", "ABD": "abd", "Kripto": "kripto"}.get(r.Piyasa, "")),
            "Kapanış": r.kapanis_t.strftime("%d.%m %H:%M") if pd.notna(r.kapanis_t) else "", "Piyasa": r.Piyasa,
            "Varlık": FR.gorunen(r.kod, r.ad), "Dilim": TK.TF_AD.get(r.tf, r.tf), "Yön": "AL" if r.yon == 1 else "SAT",
            "Kurulum": r.kurulum, "Giriş": r.giris, "Çıkış": r.cikis, "Sonuç": _sebep.get(r.sebep, str(r.sebep).capitalize()),
            "R": r.R, "Açılış": str(r.olusma)[:16].replace("T", " ")} for r in df_.iloc[::-1].itertuples()]),
            hide_index=True, use_container_width=True,
            column_config={"": st.column_config.ImageColumn("", width="small"), "R": st.column_config.NumberColumn(format="%+.2f"), "Giriş": st.column_config.NumberColumn(format="%.4g"),
                           "Çıkış": st.column_config.NumberColumn(format="%.4g")})
        en_ = df_.nlargest(3, "R"); kt_ = df_.nsmallest(3, "R")
        c1, c2 = st.columns(2)
        c1.markdown("**En iyi sonuçlar**\n" + "\n".join(f"- {FR.gorunen(r.kod, r.ad)} {FR.rrs(r.R)}" for r in en_.itertuples()))
        c2.markdown("**En kötü sonuçlar**\n" + "\n".join(f"- {FR.gorunen(r.kod, r.ad)} {FR.rrs(r.R)}" for r in kt_.itertuples()))
    else:
        kart(c1, "KAPANAN", "0", f"açık {len(acik_t)}")
        st.info("Henüz kapanmış kurulum yok. Kurulumlar hedefe, stopa ya da süre sonuna ulaştıkça bu sayfa dolacak; anlamlı bir tablo için 1–2 hafta gerekir.")
    if acik_t:
        st.markdown("**Açık kurulumlar**")
        st.dataframe(pd.DataFrame([{"Piyasa": k["Piyasa"], "Kod": FR.gorunen(k["kod"], k.get("ad")), "Dilim": TK.TF_AD[k["tf"]],
                                    "Yön": "AL" if k["yon"] == 1 else "SAT", "Getiri": round((k.get("son_fiyat", k["giris"]) / k["giris"] - 1) * k["yon"] * 100, 1),
                                    "Görülen hedef": k["asama"]} for k in acik_t]), hide_index=True, use_container_width=True,
                     column_config={"Getiri": st.column_config.NumberColumn(format="%+.1f%%")})
    st.markdown("**Geçmiş testi (tüm piyasa, aynı kurallar)**")
    sat_ = []
    for pz, ad_ in (("bist", "BIST"), ("abd", "ABD"), ("kripto", "Kripto"), ("emtia", "Emtia")):
        for tf, d in (json_oku(f"firsat/{pz}/istatistik.json", ZAMAN) or {}).items():
            for an_, v in d.items():
                ku, yon, _ = an_.split("|")
                if v.get("n", 0) < 50: continue
                sat_.append({"Piyasa": ad_, "Dilim": TK.TF_AD.get(tf, tf), "Kurulum": FR.KURULUM.get(ku, (ku, ku))[0 if yon == "1" else 1],
                             "Örnek": v["n"], "1R %": round(v["p1"] * 100), "Ort. R": round(v["ort_R"], 2)})
    if sat_:
        st.dataframe(pd.DataFrame(sat_).sort_values("Ort. R", ascending=False), hide_index=True, use_container_width=True,
                     column_config={"Ort. R": st.column_config.NumberColumn(format="%+.2f")})
        st.caption("Son taramadaki likit varlıkların geçmişinde aynı kurulumların sonucu. Ort. R sıfırın üzerindeyse kural geçmişte kazandırmış.")

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
    if st.button(":material/description: Analiz Et", type="primary", disabled=not v_kod, key="v_btn"):
        try:
            with st.status(f"{v_sec} analiz ediliyor…") as s:
                st.session_state.v_sonuc = varlik_analiz(v_kod, tuple(PRM.items()), ZAMAN, br.SURUM)
                s.update(label="Hazır ✓", state="complete", expanded=False)
        except Exception as e:
            st.error(f"Analiz yapılamadı: {e}")
    if "v_sonuc" in st.session_state: varlik_goster(st.session_state.v_sonuc, "v")
    with st.expander(":material/bar_chart: Tüm emtia ve kriptoları karşılaştır"):
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







with tab_p:
    sabah_k = gorsel_oku("sabah/kart.png", ZAMAN)
    if sabah_k:
        with st.expander(":material/wb_sunny: Bugünün sabah özeti (kart + sesli)", expanded=False):
            st.image(sabah_k, use_container_width=True)
            ses = gorsel_oku("sabah/ozet.mp3", ZAMAN)
            if ses: st.audio(ses, format="audio/mp3")
    st.selectbox("Varlık ara", list(ARAMA_SECENEK), index=None, key="ana_ara", on_change=_ara_sec, label_visibility="collapsed",
                 placeholder="🔎  Varlık ara (ör. THYAO, Aselsan, BTC, altın, NVDA)")
    if st.session_state.pop("_kk_git", None):
        _bil.html(f"<script>try{{window.parent.kkTeknikGit && window.parent.kkTeknikGit('')}}catch(e){{}}</script>", height=0)
    st.markdown(TS.bb("Piyasalar"), unsafe_allow_html=True)
    try:
        PV = piyasa_verisi(ZAMAN)
    except Exception as e:
        PV = {}; st.caption(f"Piyasa verisi alınamadı: {e}")
    sira = ["BIST 100", "S&P 500", "Nasdaq", "USD/TRY", "EUR/TRY", "Gram altın", "Ons altın", "Gümüş", "Brent petrol",
            "Bitcoin", "Ethereum", "Dolar endeksi", "ABD 10Y faiz", "VIX", "BIST 100 ($)"]
    goster = [x for x in sira if x in PV]
    st.markdown('<div class="serit-k">' + "".join(mini_kart(ad_, PV[ad_]) for ad_ in goster) + "</div>", unsafe_allow_html=True)
    st.caption("Yana kaydırın · Etiket: anlık / gecikmeli (~15 dk) / kapanış / bayat. Kaynaklar: Takip › Veri kaynakları. Mini grafik son 60 işlem günü.")
    # ---- Günün fırsatları (tüm piyasalar, puana göre)
    try:
        _gf = gunun_firsatlari(ZAMAN)
        if _gf:
            st.markdown(TS.bb("Günün fırsatları"), unsafe_allow_html=True)
            st.markdown('<div class="serit-k">' + "".join(firsat_mini(f) for f in _gf) + "</div>", unsafe_allow_html=True)
            st.caption("Ayrıntılar: Keşfet › Fırsatlar. Puan, işlem planı ve teyitler Telegram kartlarında da var.")
    except Exception as ex:
        st.caption(f"Fırsatlar okunamadı: {ex}")
    # ---- Öne çıkanlar: takip listesi (yoksa seçili büyük hisseler) + kripto + gram altın
    try:
        st.markdown(TS.bb("Öne çıkanlar"), unsafe_allow_html=True)
        st.markdown(one_cikanlar(PV), unsafe_allow_html=True)
        st.caption("Liste: Takip › Favoriler'e eklediğiniz hisseler (boşsa BIST'in büyükleri). Hisse fiyatları son kapanış bülteninden.")
    except Exception as ex:
        st.caption(f"Öne çıkanlar okunamadı: {ex}")
    with st.expander(":material/view_agenda: Piyasa kartları (büyük görünüm)"):
        for i in range(0, len(goster), 2):
            cols = st.columns(2)
            for c, ad_ in zip(cols, goster[i:i + 2]):
                c.markdown(piyasa_karti(ad_, PV[ad_]), unsafe_allow_html=True)
    # ---- Yabancı yatırımcı akışı (TCMB haftalık)
    try:
        import yabanci_akis as YA
        _ya = json_oku("yabanci/akis.json", ZAMAN)
        _yo = YA.ozet(_ya) if _ya else None
    except Exception:
        _yo = None
    if _yo:
        st.markdown(TS.bb("Yabancı yatırımcı akışı"), unsafe_allow_html=True)
        _s = _yo["seri"]; _mx = max(abs(x["net"]) for x in _s) or 1; _w = 300; _h = 90; _bw = _w / len(_s)
        _bar = "".join(
            f'<rect x="{i * _bw + 3:.1f}" y="{(_h / 2 - x["net"] / _mx * (_h / 2 - 4)) if x["net"] > 0 else _h / 2:.1f}" width="{_bw - 6:.1f}" '
            f'height="{abs(x["net"]) / _mx * (_h / 2 - 4):.1f}" rx="2" fill="{"#22C55E" if x["net"] > 0 else "#EF4444"}"/>' for i, x in enumerate(_s))
        _svg = (f'<svg width="100%" viewBox="0 0 {_w} {_h}" preserveAspectRatio="none" style="height:90px">'
                f'<line x1="0" y1="{_h / 2}" x2="{_w}" y2="{_h / 2}" stroke="rgba(255,255,255,.15)"/>{_bar}</svg>')
        _r = lambda v: ("y" if (v or 0) > 0 else "k" if (v or 0) < 0 else "n")
        st.markdown(
            f'<div class="pk" style="display:block"><div class="pk-ad">{YA._gun(_yo["tarih"])} haftası · net hisse alımı</div>'
            f'<div class="pk-d">{YA.mn(_yo["hafta"])}</div>'
            f'<span class="rozet {_r(_yo["dort"])}">4 hafta {YA.mn(_yo["dort"])}</span> '
            f'<span class="rozet {_r(_yo["onuc"])}">13 hafta {YA.mn(_yo["onuc"]) if _yo["onuc"] is not None else "birikiyor"}</span>'
            f'<div style="margin-top:10px">{_svg}</div>'
            f'<div class="pk-alt">{YA.cumle(_yo)} Kaynak: TCMB Haftalık Menkul Kıymet İstatistikleri (her perşembe 14:30). '
            f'Hisse bazında değil, tüm BIST için toplamdır.</div></div>', unsafe_allow_html=True)
    if _MAKRO and _MAKRO.get("tufe"):
        st.markdown(TS.bb("Türkiye makro"), unsafe_allow_html=True)
        st.markdown(makro_karti(_MAKRO), unsafe_allow_html=True)
    for d_, ad_ in (("haftalik", "Haftalık"), ("aylik", "Aylık")):
        k_ = gorsel_oku(f"donem/{d_}.png", ZAMAN)
        if k_:
            with st.expander(f":material/calendar_month: {ad_} durum raporu (10 ana varlık)"):
                st.image(k_, use_container_width=True)
                p_ = gorsel_oku(f"donem/{d_}.pdf", ZAMAN)
                if p_: st.download_button(f":material/download: {ad_} durum raporu (PDF)", data=p_, file_name=f"KATKAY_{ad_}_Durum.pdf",
                                          mime="application/pdf", key=f"donem_{d_}")
    for pz, ad_ in (("bist", "BIST"), ("abd", "ABD"), ("kripto", "Kripto")):
        k_ = gorsel_oku(f"{pz}/kapanis_karti.png", ZAMAN)
        if k_:
            with st.expander(f":material/bar_chart: {ad_} son kapanış özeti"):
                st.image(k_, use_container_width=True)
    if EVDS:
        st.markdown("**TCMB (EVDS)**")
        for ad_, v in EVDS.items():
            st.markdown(f"- {ad_}: **{br.ond(v['deger'], 2)}** ({v['tarih']:%m.%Y})")
        if OTO: st.caption("Model varsayımlarındaki enflasyon EVDS'den otomatik alındı.")
        if EVDS_HATA: st.caption("Okunamayan seriler: " + "; ".join(f"{k} ({h})" for k, h in EVDS_HATA.items()))

    st.divider()
    st.markdown(TS.bb("Günlük tarama ve fırsat listeleri"), unsafe_allow_html=True)
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
        if st.button(":material/public: Tüm piyasayı şimdi tara", key="p_btn"):
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
        st.markdown(TS.bb("Sektör ısı haritası"), unsafe_allow_html=True)
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
    st.markdown(TS.bb("Skorun geçmiş testi"), unsafe_allow_html=True)
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
    if st.button(":material/search: Taramayı Başlat", type="primary", key="t_btn"):
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



with tab_b:
    b_mod = st.radio("Kapsam", ["Resmi bebekler", "Genç şirketler", "Küçük şirketler"], horizontal=True, key="b_mod",
                     help="Resmi: son 2 yılda halka arz olup BIST Halka Arz Endeksi'nde (XHARZ) yer alanlar. "
                          "Genç: tüm BIST'te son 5 yılda halka arz olanlar. Küçük: tüm BIST'te piyasa değeri 5 milyar TL altındakiler.")
    MOD = {"Resmi bebekler": "resmi", "Genç şirketler": "genc", "Küçük şirketler": "kucuk"}[b_mod]
    st.caption({"resmi": "Borsa İstanbul'un resmi tanımı: halka arz edilip işlem görmeye başladığı günden itibaren 2 yıl boyunca "
                         "BIST Halka Arz Endeksi'nde (XHARZ) yer alan şirketler.",
                "genc": "Tüm BIST hisseleri içinden son 5 yılda halka arz olan şirketler (resmi bebekler dahil).",
                "kucuk": "Tüm BIST hisseleri içinden piyasa değeri 5 milyar TL'nin altındaki şirketler; yaşına bakılmaz."}[MOD])
    if st.button(":material/school: Şirketleri getir", type="primary", key="b_btn"):
        with st.spinner("Halka arz endeksi, ilk işlem tarihleri ve piyasa değerleri alınıyor…"):
            hedef = list(HARZ) if (HARZ and MOD == "resmi") else list(EVREN["Kod"])
            ilk = ilk_cek(tuple(sorted(hedef)), GUN, br.SURUM) if MOD != "kucuk" else {}
            liste, resmi = EV.bebekler(EVREN, ilk, set(HARZ), resmi_ilk=resmi_ilk_cek(GUN, br.SURUM), mod=MOD)
            st.session_state.bebek = (liste, resmi, len(EVREN), MOD); st.session_state.pop("bebek_derin", None)
    if "bebek" in st.session_state and st.session_state.bebek[3] == MOD:
        liste, resmi, n_ev, _ = st.session_state.bebek
        st.markdown(f"**{len(liste)} şirket** ({n_ev} BIST hissesi içinden)")
        if MOD == "resmi":
            st.caption("Kaynak: " + ("Borsa İstanbul resmi XHARZ bileşen listesi." if resmi else
                       "Resmi liste bu sefer alınamadı; ilk işlem tarihi 2 yıldan yeni olan hisseler seçildi (Yahoo).") + f" Hisse evreni: {EVREN_NOT}")
        if liste:
            dfb = pd.DataFrame(liste)
            for c in ("İlk işlemden getiri", "Zirveden uzaklık"):
                dfb[c] = dfb[c].apply(lambda x: None if x is None or pd.isna(x) else round(x * 100, 1))
            if MOD != "resmi": dfb = dfb.drop(columns=[c for c in ("Endekste kalan (ay)",) if c in dfb])
            st.dataframe(dfb, hide_index=True, use_container_width=True,
                         column_config={"Halka açıklık %": st.column_config.NumberColumn(format="%.1f"),
                                        "İlk işlemden getiri": st.column_config.NumberColumn("İlk işlemden getiri %", format="%.1f"),
                                        "Zirveden uzaklık": st.column_config.NumberColumn("Zirveden %", format="%.1f")})
            st.caption("İlk işlem tarihi ve ilk gün kapanışı Borsa İstanbul'un resmi listesinden alınır (ilk gün kapanışı düzeltilmemiş fiyattır). "
                       "'İlk işlemden getiri' bedelsiz/bölünme düzeltilmiş Yahoo verisinden hesaplanır.")
            n_derin = min(len(liste), 80)
            if len(liste) > n_derin:
                st.caption(f"Derin analiz süre sınırı nedeniyle listedeki ilk {n_derin} şirketi kapsar (resmi/genç: en yeni halka arzlar, küçük: en büyükleri).")
            if st.button(f":material/biotech: Derin analiz: büyüme modeli ve bebek skoru ({n_derin} şirket, {max(2, n_derin // 10)}–{max(4, n_derin // 6)} dk)", key="b_derin"):
                with st.spinner("Şirketlerin finansalları taranıyor ve büyüme modeli kuruluyor… Ekranı kapatmayın."):
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
                for c in ("Reel büyüme", "Çeyrek büyüme (reel)", "Büyüme potansiyeli", "ROE"):
                    if c in dfd: dfd[c] = dfd[c].apply(lambda x: None if x is None or pd.isna(x) else round(x * 100, 1))
                kol = [c for c in ["Kod", "Şirket", "Bebek skoru", "Neden", "Fiyat", "Büyüme adil değeri", "Büyüme potansiyeli",
                                   "Model güveni", "Reel büyüme", "Çeyrek büyüme (reel)", "PEG (reel)", "FD/Satış", "F/K", "Sağlık skoru", "ROE",
                                   "Para akışı", "Borsadaki süre (ay)", "Endekste kalan (ay)", "Risk notu", "Büyüme modeli"] if c in dfd]
                st.markdown(TS.bolum("Bebek skoru sıralaması"), unsafe_allow_html=True)
                st.dataframe(dfd[kol], hide_index=True, use_container_width=True,
                             column_config={"Bebek skoru": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
                                            "Fiyat": st.column_config.NumberColumn(format="%.2f"),
                                            "Büyüme adil değeri": st.column_config.NumberColumn("Büyüme adil değeri", format="%.2f"),
                                            "Büyüme potansiyeli": st.column_config.NumberColumn("Büyüme potansiyeli %", format="%+.1f"),
                                            "Reel büyüme": st.column_config.NumberColumn("Reel büyüme %", format="%+.1f"),
                                            "Çeyrek büyüme (reel)": st.column_config.NumberColumn("Çeyrek reel %", format="%+.1f"),
                                            "PEG (reel)": st.column_config.NumberColumn(format="%.2f"),
                                            "FD/Satış": st.column_config.NumberColumn(format="%.2f"),
                                            "Sağlık skoru": st.column_config.NumberColumn(format="%.2f"),
                                            "F/K": st.column_config.NumberColumn(format="%.1f"),
                                            "ROE": st.column_config.NumberColumn("ROE %", format="%.1f")})
                with st.expander(":material/school: Büyüme şirketi modeli nasıl çalışıyor?"):
                    st.markdown(
                        "Genç ve küçük şirketler çoğu zaman bugünkü kârıyla değil **büyümesiyle** değerlenir. Bu yüzden bu sekmede klasik "
                        "değerleme yerine büyüme şirketlerine uygun üç yöntem birlikte kullanılır. Hepsi **reel** (enflasyondan arındırılmış) "
                        "rakamlarla çalışır; böylece TL'deki yüksek enflasyon büyümeyi olduğundan büyük göstermez.\n\n"
                        "1. **Büyüme İNA (%45):** Son 12 ayın hasılatı 5 yıl boyunca şirketin reel büyümesiyle büyütülür; büyüme her yıl yavaşlayarak "
                        "uzun vadede %2'ye iner. Kâr marjı ölçek büyüdükçe sektör ortalamasına yaklaşır. Büyümek için gereken yatırım düşülür ve "
                        "bugüne indirgenir.\n"
                        "2. **Büyüme ayarlı FD/Satış (%35):** Benzer şirketlerin satışlarına göre değeri, şirketin onlardan ne kadar hızlı ya da yavaş "
                        "büyüdüğüne göre yukarı ya da aşağı düzeltilir.\n"
                        "3. **PEG (%20):** 'Büyüme kadar F/K' kuralı. Kârı reel olarak %20 büyüyen bir şirket için 20x F/K makul sayılır. "
                        "**PEG 1'in altındaysa** şirket büyümesine göre ucuz demektir.\n\n"
                        "**Model güveni:** üç yöntem birbirine yakın sonuç veriyorsa YÜKSEK, aralarında büyük fark varsa ya da sonuçlar uç olduğu için "
                        "sınırlandıysa DÜŞÜK yazar. Düşük güvenli potansiyele temkinli yaklaşın.\n\n"
                        "**Bebek skoru:** reel hasılat büyümesi (%30), sağlık skoru (%25), büyüme potansiyeli (%20), son çeyrek büyümesi (%15) ve "
                        "para akışının (%10), listedeki şirketler içindeki sırasıdır.")
                st.caption("Ayrıntılı rapor için kodu Hisse sekmesine yazın. Genç şirketlerin geçmiş verisi kısa olduğundan tahminler daha belirsizdir. "
                           "Yatırım tavsiyesi değildir.")
            if hat: st.caption("Verisi alınamayanlar: " + ", ".join(hat))

# ================= PORTFÖY =================
import portfoy as PF
PF = importlib.reload(PF)



with tab_pf:
    st.caption("Elinizdeki hisse, kripto ve emtiaları yazın; portföyün TL değeri, dağılımı, riski (oynaklık, VaR), korelasyonları, "
               "risk katkıları ve teknik görünümü hesaplanır. Her satıra: KOD MİKTAR (isteğe bağlı @ maliyet).")
    varsayilan = st.query_params.get("p", "").replace(";", "\n") or "THYAO 100\nASELS 50\nBTC/TRY 0,01\nGRAMALTIN 10"
    pf_metin = st.text_area("Portföy", varsayilan, height=160, key="pf_metin",
                            help="Örnekler: THYAO 1000 @ 280 · BTC/TRY 0,05 · ETH/USDT 1,2 · GRAMALTIN 50 (gram) · ALTIN 2 (ons)")
    if st.button(":material/work: Portföyü analiz et", type="primary", key="pf_btn"):
        try:
            with st.status("Portföy analiz ediliyor… (her varlık için veri çekilir)") as s_:
                st.session_state.pf = portfoy_analiz(pf_metin.strip(), ZAMAN, br.SURUM)
                st.query_params["p"] = ";".join(x.strip() for x in pf_metin.strip().splitlines() if x.strip())
                s_.update(label="Hazır ✓", state="complete", expanded=False)
        except Exception as e:
            st.error(f"Portföy analiz edilemedi: {e}")
    with st.expander(":material/push_pin: Telegram'da kişisel portföy uyarıları"):
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
            if st.button(":material/push_pin: Yukarıdaki portföyü Telegram takibine al", key="pf_kaydet"):
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
             "#22C55E" if r["vol"] < 0.2 else "#E8B84A" if r["vol"] < 0.35 else "#EF4444")
        st.markdown(f'<div class="kn"><div class="sv-b">PORTFÖY ÖZETİ</div><div class="kn-t">{r["baslik"]}</div>'
                    f'<div class="kn-y">{r["ozet"]}</div></div>', unsafe_allow_html=True)
        st.download_button(":material/download: Portföy PDF raporu", data=r["pdf"], file_name=r["dosya"], mime="application/pdf", type="primary", key="pf_dl")
        t = pd.DataFrame(r["tablo"])
        for c in ("Ağırlık", "Risk katkısı", "Volatilite", "K/Z"):
            t[c] = t[c].apply(lambda x: None if x is None or pd.isna(x) else round(x * 100, 1))
        st.dataframe(t[["Kod", "Tür", "Değer (TL)", "Ağırlık", "Risk katkısı", "Volatilite", "K/Z", "Teknik"]], hide_index=True, use_container_width=True,
                     column_config={"Değer (TL)": st.column_config.NumberColumn(format="%.0f")})
        st.caption("Ağırlık, risk katkısı, volatilite ve K/Z yüzde olarak gösterilir.")
        for g_ in ("g_deger", "g_agirlik", "g_kor"): st.image(r[g_], use_container_width=True)
        if r["hata"]: st.caption("Verisi alınamayanlar: " + ", ".join(r["hata"]))

# ================= ALARM =================

with tab_al:
    st.caption("Alarmlar 30 dakikada bir otomatik kontrol edilir; tetiklenince Telegram'a bildirim gider (Telegram kuruluysa). "
               "Son tetiklenen alarmlar aşağıda da görünür.")
    son_al, kontrol = alarm_son(ZAMAN)
    if kontrol: st.caption(f"Son kontrol: {kontrol.get('kontrol')} · {kontrol.get('kural')} kural")
    st.markdown(TS.bb("Son alarmlar"), unsafe_allow_html=True)
    if son_al:
        import re as _re, html as _h
        _kart = []
        for x in son_al[:20]:
            m_ = x["mesaj"]; link = _re.search(r"⟦(.+?)⟧$", m_); m_ = _re.sub(r"⟦(.+?)⟧$", "", m_).strip()
            ik = m_[:1]; renk = "#22C55E" if ("+" in m_ and "%" in m_) or ik == "🟢" else "#EF4444" if ik in ("🔴", "⛔") or "-%" in m_ else "#E8B84A"
            _kart.append(f'<div class="hb" style="--v:{renk}"><div class="hb-u"><span class="vb-e">{_h.escape(x["zaman"])}</span></div>'
                         f'<div class="hb-b" style="font-size:.9rem">{_h.escape(m_)}</div>'
                         + (f'<a class="hb-l" href="{_h.escape(link.group(1))}" target="_blank" rel="noopener">Habere git ›</a>' if link else "") + "</div>")
        st.markdown("".join(_kart), unsafe_allow_html=True)
    else:
        st.info("Henüz tetiklenen alarm yok.")
    st.markdown(TS.bb("Kurallar"), unsafe_allow_html=True)
    mevcut = open("alarmlar.txt", encoding="utf-8").read() if os.path.exists("alarmlar.txt") else ""
    st.code("\n".join(s for s in mevcut.splitlines() if s.strip() and not s.startswith("#")) or "(kural yok)")
    with st.expander(":material/add: Yeni alarm ekle"):
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
    st.caption("BIST ve ABD hisselerini (karışık da olabilir) değerleme, kârlılık, büyüme, teknik ve risk açısından yan yana koyar; "
               "her kriterde öne çıkanı işaretler ve sade bir sonuç yazar.")
    _abd = abd_listesi_cek(GUN)
    secenek = bv.arama_secenekleri() + [f"{r.Sembol} — {r.Ad} (ABD)" for r in _abd.itertuples()]
    try:
        secili = st.multiselect("2–3 hisse seçin", secenek, max_selections=3, key="k_sec", accept_new_options=True,
                                placeholder="Şirket adı veya kodu (örn. THYAO, Nvidia)")
    except TypeError:
        secili = st.multiselect("2–3 hisse seçin", secenek, max_selections=3, key="k_sec")
    import bist_abd as _AB
    kodlar = [(_AB.kod_yap(x.split(" — ")[0]) if x.endswith("(ABD)") else bv.secimden_kod(x)) for x in secili]
    if st.button(":material/balance: Karşılaştır", type="primary", disabled=len(kodlar) < 2, key="k_btn"):
        sonuc = {}
        with st.status("Hisseler analiz ediliyor… (hisse başına 30–60 sn)") as s:
            for k in kodlar:
                try:
                    r_ = analiz(k, "", tuple(PRM.items()), ZAMAN, br.SURUM); sonuc[r_["ozet"]["Kod"]] = r_
                except Exception as e:
                    st.warning(f"{k}: {e}")
            s.update(label="Hazır ✓", state="complete", expanded=False)
        st.session_state.kars = sonuc
    if "kars" in st.session_state and len(st.session_state.kars) >= 2:
        S = st.session_state.kars
        cols = st.columns(len(S))
        for c_, (k, r) in zip(cols, S.items()):
            o = r["ozet"]; pt = o.get("Potansiyel")
            kart(c_, k, f"{br.tl(o['Fiyat'])} {r.get('pb', 'TL')}", f"Adil {br.tl(o['Adil değer'])} · {br.yz(pt)}",
                 "#22C55E" if (pt or 0) > 0.1 else "#EF4444" if (pt or 0) < -0.1 else "#E8B84A")
        kriter = [("Potansiyel (adil değere göre)", "Potansiyel", 1, br.yz), ("Finansal sağlık (1–5)", "Sağlık skoru", 1, lambda x: br.ond(x, 2)),
                  ("F/K (düşük = ucuz)", "F/K", -1, br.kat), ("PD/DD (düşük = ucuz)", "PD/DD", -1, br.kat),
                  ("Özkaynak kârlılığı (ROE)", "ROE", 1, br.yz), ("Temettü verimi", "Temettü verimi", 1, br.yz),
                  ("1 yıllık getiri", "1Y getiri", 1, br.yz), ("Teknik puan (günlük)", "_tek", 1, lambda x: f"{x:.0f}")]
        def deger_(r, alan):
            if alan == "_tek": return ((r.get("teknik") or {}).get("G") or (None, None))[1]
            return r["ozet"].get(alan)
        kazan = {k: 0 for k in S}; satirlar_ = {}
        for ad_, alan, yon, fmt in kriter:
            v = {k: deger_(r, alan) for k, r in S.items()}
            gecerli = {k: x for k, x in v.items() if x is not None and (alan not in ("F/K", "PD/DD") or x > 0)}
            en = (max if yon > 0 else min)(gecerli, key=gecerli.get) if len(gecerli) >= 2 else None
            if en: kazan[en] += 1
            satirlar_[ad_] = {k: ("🏆 " if k == en else "") + (fmt(x) if x is not None else "–") for k, x in v.items()}
        satirlar_["Model görüşü"] = {k: r["ozet"].get("Görüş") or "–" for k, r in S.items()}
        satirlar_["Teknik görünüm"] = {k: r["ozet"].get("Teknik") or "–" for k, r in S.items()}
        st.dataframe(pd.DataFrame(satirlar_).T, use_container_width=True)
        # sade sonuç
        sira_ = sorted(kazan.items(), key=lambda x: -x[1])
        def en_iyi(alan, yon):
            v = {k: deger_(r, alan) for k, r in S.items() if deger_(r, alan) is not None and (alan not in ("F/K",) or deger_(r, alan) > 0)}
            return (max if yon > 0 else min)(v, key=v.get) if len(v) >= 2 else None
        c_ = []
        e = en_iyi("Potansiyel", 1)
        if e: c_.append(f"**Değerleme:** modele göre en fazla yukarı potansiyel {e}'de ({br.yz(S[e]['ozet']['Potansiyel'])}).")
        e = en_iyi("ROE", 1)
        if e: c_.append(f"**Kârlılık:** özkaynak kârlılığı en yüksek {e} ({br.yz(S[e]['ozet']['ROE'])}).")
        e = en_iyi("Sağlık skoru", 1)
        if e: c_.append(f"**Finansal sağlık:** en güçlü bilanço ve nakit akışı {e} ({br.ond(S[e]['ozet']['Sağlık skoru'], 2)}/5).")
        e = en_iyi("_tek", 1)
        if e: c_.append(f"**Teknik:** grafikte en güçlü görünüm {e} (puan {deger_(S[e], '_tek'):.0f}).")
        c_.append(f"**Genel:** {sira_[0][0]} {len(kriter)} kriterin {sira_[0][1]} tanesinde önde"
                  + (f"; {sira_[1][0]} {sira_[1][1]} kriterde öne çıkıyor." if len(sira_) > 1 else "."))
        import re as _re
        _sat = ["<div class='kn-s'>• " + _re.sub(r"[*][*](.+?)[*][*]", r"<b>\1</b>", x) + "</div>" for x in c_]
        st.markdown('<div class="kn"><div class="sv-b">SADE SONUÇ</div>' + "".join(_sat) + "</div>", unsafe_allow_html=True)
        st.caption("Karşılaştırma modelin göstergelerine dayanır; şirketlerin farklı sektör ve para biriminde olması kıyası etkileyebilir.")
        rp = radar_png(S)
        if rp:
            st.markdown("**Finansal sağlık profili**"); st.image(rp, use_container_width=True)
        fy = pd.DataFrame({k: r["fiyat"] / r["fiyat"].iloc[0] * 100 for k, r in S.items()}).dropna(how="all")
        st.markdown("**Son 12 ay performans (100 baz)**")
        st.line_chart(fy, height=240)
        for k, r in S.items():
            st.download_button(f":material/download: {k} raporu (PDF)", data=r["pdf"], file_name=r["dosya"], mime="application/pdf", key=f"k_dl_{k}")

# ================= TAKİP =================
with tab_w:
    qp = st.query_params.get("takip", "")
    liste = [x for x in qp.split(",") if x] if qp else []
    st.caption("Takip listeniz sayfa adresinde saklanır. Listeyi değiştirdikten sonra simgeyi ana ekrana "
               "yeniden eklerseniz liste kalıcı olur.")
    yeni = hisse_sec("Listeye ekle", "w_ekle")
    if st.button(":material/add: Listeye Ekle", disabled=not yeni, key="w_btn"):
        if yeni not in liste:
            liste.append(yeni); st.query_params["takip"] = ",".join(liste); st.rerun()
    def _cikar(k):
        yeni_liste = [x for x in liste if x != k]
        st.query_params["takip"] = ",".join(yeni_liste)
    if liste:
        st.markdown("**Takip listeniz** (çıkarmak için dokunun):")
        sutun = st.columns(4)
        for i, k in enumerate(liste):
            sutun[i % 4].button(f":material/close: {k}", key=f"rm_{k}", on_click=_cikar, args=(k,))
        if st.button(":material/refresh: Listeyi Güncelle", type="primary", key="w_tara"):
            with st.spinner("Takip listesi taranıyor…"):
                st.session_state.takip = tarama(tuple(liste), tuple(PRM.items()), SAAT2, br.SURUM)
        if "takip" in st.session_state:
            tablo_goster(st.session_state.takip[0], "Potansiyel")
    else:
        st.info("Henüz takip ettiğiniz hisse yok.")

    st.divider()
    st.markdown(TS.bb("Sabah raporları"), unsafe_allow_html=True)
    klasorler = sorted(glob.glob("raporlar/20*"), reverse=True)
    if klasorler:
        son = klasorler[0]
        st.caption(f"Son üretim: {os.path.basename(son)} · Liste: takip_listesi.txt")
        ozet_dosya = os.path.join(son, "ozet.csv")
        if os.path.exists(ozet_dosya):
            tablo_goster(pd.read_csv(ozet_dosya).to_dict("records"), "Potansiyel")
        for f in sorted(glob.glob(os.path.join(son, "*.pdf"))):
            with open(f, "rb") as fh:
                st.download_button(f":material/download: {os.path.basename(f)}", data=fh.read(), file_name=os.path.basename(f),
                                   mime="application/pdf", key=f"s_{f}")
    else:
        st.caption("Hafta içi her sabah 08:17'de takip_listesi.txt'deki hisseler için raporlar otomatik hazırlanır. "
                   "İlk raporlar oluşunca burada görünecek.")

st.divider()
st.markdown(f'<div class="alt-not">Veriler Yahoo Finance, Binance ve OKX kaynaklıdır, gecikmeli olabilir.<br>Gösterge bazlı otomatik analizdir, yatırım tavsiyesi değildir · Sürüm {br.SURUM}</div>', unsafe_allow_html=True)
