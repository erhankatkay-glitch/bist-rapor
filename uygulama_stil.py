"""KATKAY YATIRIM A.Ş. — uygulama görsel kimliği.
Siyah / antrasit zemin, altın vurgu, neon yeşil (boğa) ve kırmızı (ayı); üstte boğa–ayı görseli,
canlı saat, piyasa durum hapları, kayan fiyat şeridi ve telefon için alt gezinme çubuğu."""
import base64, datetime as dt, os, re
from zoneinfo import ZoneInfo

MARKA_1, MARKA_2 = "KATKAY", "YATIRIM A.Ş."
ALTIN, ALTIN_A, ALTIN_K = "#E8B84A", "#F7D98B", "#B8862B"

STIL = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
:root {--zemin:#070708; --panel:#121315; --panel2:#18191C; --cizgi:rgba(255,255,255,.08); --yazi:#E7E7EA; --soluk:#9A9BA3;
       --altin:#E8B84A; --altin-a:#F7D98B; --altin-k:#B8862B; --yesil:#22C55E; --kirmizi:#EF4444;}
html, body, .stApp, .stMarkdown, button, input, textarea, select, [data-testid="stWidgetLabel"] {font-family:'Inter',-apple-system,sans-serif !important;}
.stApp {background:
   radial-gradient(700px 380px at 0% 0%, rgba(34,197,94,.06), transparent 60%),
   radial-gradient(700px 380px at 100% 0%, rgba(239,68,68,.06), transparent 60%),
   linear-gradient(180deg, #0B0B0C 0%, #070708 100%) !important;}
#MainMenu, footer, header[data-testid="stHeader"] {visibility:hidden; height:0;}
.block-container {padding-top:.4rem; padding-bottom:10rem; max-width:720px;}
h1, h2, h3, h4 {color:#F5F5F7 !important; font-weight:800 !important; letter-spacing:-.015em;}
h3 {font-size:1.25rem !important;}
[data-testid="stCaptionContainer"], .stCaption {color:var(--soluk) !important;}
hr {border:none !important; height:1px !important; background:linear-gradient(90deg, transparent, rgba(232,184,74,.35), transparent) !important;}
[data-testid="stMarkdownContainer"] p, li {font-variant-numeric: tabular-nums;}
iframe[title="st.iframe"], .stElementContainer:has(> iframe) {border:none;}

/* ---------- Sekmeler: bölmeli çubuk, etkin sekme eğik yeşil + altın çerçeve ---------- */
.stTabs [data-baseweb="tab-list"] {gap:0; overflow-x:auto; flex-wrap:nowrap; scrollbar-width:none; padding:5px;
       background:linear-gradient(180deg, #17181B, #0F1012); border:1px solid var(--cizgi); border-radius:18px;
       box-shadow:0 10px 26px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.04);}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {display:none;}
.stTabs [data-baseweb="tab"] {background:transparent; border:none; border-radius:0; padding:9px 15px !important; margin:0 !important;
       height:auto !important; white-space:nowrap; position:relative; transition:all .15s ease;}
.stTabs [data-baseweb="tab"] + [data-baseweb="tab"]:before {content:""; position:absolute; left:0; top:22%; bottom:22%; width:1px; background:rgba(255,255,255,.10);}
.stTabs [data-baseweb="tab"] p {font-weight:600; font-size:.86rem; color:#D4D4D8; margin:0;}
.stTabs [data-baseweb="tab"] [data-testid="stIconMaterial"] {color:var(--altin) !important;}
.stTabs [aria-selected="true"] {background:linear-gradient(135deg, #0F3D24 0%, #166534 55%, #14532D 100%) !important;
       clip-path:polygon(0 0, 100% 0, 92% 100%, 0 100%); border-radius:12px 0 0 12px;
       box-shadow:inset 0 0 0 1.5px var(--altin), 0 0 18px rgba(34,197,94,.35);}
.stTabs [aria-selected="true"]:before, .stTabs [aria-selected="true"] + [data-baseweb="tab"]:before {display:none;}
.stTabs [aria-selected="true"] p {color:#FFFFFF !important; font-weight:800; padding-right:6px;}
.stTabs [aria-selected="true"] [data-testid="stIconMaterial"] {color:var(--altin-a) !important;}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {display:none;}
.stTabs [data-baseweb="tab-panel"] {padding-top:12px;}
.stTabs .stTabs [data-baseweb="tab-list"] {background:transparent; border:none; box-shadow:none; padding:0 0 6px;}
.stTabs .stTabs [aria-selected="true"] {background:transparent !important; clip-path:none; box-shadow:inset 0 -2px 0 var(--altin);}
.stTabs .stTabs [aria-selected="true"] p {color:var(--altin) !important;}
/* Streamlit 1.5x+ sekme yapısı (data-testid) */
.stTabs [role="tablist"] {gap:0; overflow-x:auto; flex-wrap:nowrap; scrollbar-width:none; padding:5px;
       background:linear-gradient(180deg, #17181B, #0F1012); border:1px solid var(--cizgi); border-radius:18px;
       box-shadow:0 10px 26px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.04);}
.stTabs [role="tablist"]::-webkit-scrollbar {display:none;}
.stTabs [data-testid="stTab"] {background:transparent; border:none; border-radius:0; padding:9px 15px !important; margin:0 !important;
       height:auto !important; white-space:nowrap; position:relative; transition:all .15s ease;}
.stTabs [data-testid="stTab"] + [data-testid="stTab"]:before {content:""; position:absolute; left:0; top:22%; bottom:22%; width:1px; background:rgba(255,255,255,.10);}
.stTabs [data-testid="stTab"] p {font-weight:600; font-size:.86rem; color:#D4D4D8; margin:0;}
.stTabs [data-testid="stTab"] [data-testid="stIconMaterial"] {color:var(--altin) !important;}
.stTabs [aria-selected="true"] {background:linear-gradient(135deg, #0F3D24 0%, #166534 55%, #14532D 100%) !important;
       clip-path:polygon(0 0, 100% 0, 92% 100%, 0 100%); border-radius:12px 0 0 12px;
       box-shadow:inset 0 0 0 1.5px var(--altin), 0 0 18px rgba(34,197,94,.35);}
.stTabs [aria-selected="true"]:before, .stTabs [aria-selected="true"] + [data-testid="stTab"]:before {display:none;}
.stTabs [aria-selected="true"] p {color:#FFFFFF !important; font-weight:800; padding-right:6px;}
.stTabs [aria-selected="true"] [data-testid="stIconMaterial"] {color:var(--altin-a) !important;}
.stTabs [data-testid="stTabPanel"] {padding-top:12px;}
.stTabs .stTabs [role="tablist"] {background:transparent; border:none; box-shadow:none; padding:0 0 6px;}
.stTabs .stTabs [aria-selected="true"] {background:transparent !important; clip-path:none; box-shadow:inset 0 -2px 0 var(--altin);}
.stTabs .stTabs [aria-selected="true"] p {color:var(--altin) !important;}

/* ---------- Butonlar ---------- */
div.stButton > button, div.stDownloadButton > button, div.stLinkButton > a, div.stFormSubmitButton > button {
       width:100%; min-height:3rem; border-radius:14px; font-weight:700; font-size:.96rem;
       background:linear-gradient(180deg, #1A1B1E, #121315); color:var(--yazi); border:1px solid var(--cizgi); transition:all .15s ease;}
div.stButton > button:hover, div.stDownloadButton > button:hover {border-color:rgba(232,184,74,.6); color:var(--altin-a);}
div.stButton > button [data-testid="stIconMaterial"], div.stDownloadButton > button [data-testid="stIconMaterial"] {color:var(--altin);}
div.stButton > button[kind="primary"], div.stDownloadButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] {
       background:linear-gradient(135deg, #F7D98B 0%, #E8B84A 45%, #B8862B 100%) !important; border:none !important;
       box-shadow:0 10px 24px rgba(232,184,74,.25), inset 0 1px 0 rgba(255,255,255,.45);}
div.stButton > button[kind="primary"] *, div.stDownloadButton > button[kind="primary"] *, div.stFormSubmitButton > button[kind="primary"] * {
       color:#141414 !important; font-weight:800 !important;}
div.stButton > button[kind="primary"]:hover {filter:brightness(1.06); transform:translateY(-1px);}
div.stButton > button:disabled {opacity:.45;}

/* ---------- Giriş alanları ---------- */
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="textarea"], .stNumberInput input {
       background:#111214 !important; border-color:var(--cizgi) !important; border-radius:14px !important;}
[data-baseweb="select"] > div:focus-within, [data-baseweb="input"]:focus-within {border-color:var(--altin) !important; box-shadow:0 0 0 3px rgba(232,184,74,.15);}
[data-testid="stWidgetLabel"] p {color:#B4B5BC !important; font-weight:650; font-size:.8rem !important; letter-spacing:.02em;}
div[role="radiogroup"] {gap:4px !important; background:#111214; border:1px solid var(--cizgi); border-radius:16px; padding:4px; flex-wrap:wrap;}
div[role="radiogroup"] > label {margin:0 !important; padding:8px 14px; border-radius:12px; flex:1 1 auto; justify-content:center; transition:all .15s ease;}
div[role="radiogroup"] > label > div:first-child {display:none !important;}
div[role="radiogroup"] > label p {font-weight:700; font-size:.86rem; color:#B4B5BC;}
div[role="radiogroup"] > label:has(input:checked) {background:linear-gradient(135deg, rgba(232,184,74,.22), rgba(184,134,43,.14));
       box-shadow:inset 0 0 0 1px rgba(232,184,74,.65);}
div[role="radiogroup"] > label:has(input:checked) p {color:var(--altin-a) !important;}

/* ---------- Açılır bölmeler, tablolar ---------- */
[data-testid="stExpander"] details {background:linear-gradient(180deg, #17181B, #111214); border:1px solid var(--cizgi) !important;
       border-radius:18px !important; overflow:hidden; box-shadow:0 8px 22px rgba(0,0,0,.35);}
[data-testid="stExpander"] summary {padding:13px 16px;}
[data-testid="stExpander"] summary p {font-weight:700; color:#F1F1F3;}
[data-testid="stExpander"] summary svg, [data-testid="stExpander"] summary [data-testid="stIconMaterial"] {color:var(--altin) !important; fill:var(--altin);}
[data-testid="stDataFrame"], [data-testid="stTable"] {border:1px solid var(--cizgi); border-radius:14px; overflow:hidden;}
[data-testid="stAlert"] {border-radius:14px; border:1px solid var(--cizgi);}
[data-testid="stImage"] img {border-radius:16px; box-shadow:0 14px 34px rgba(0,0,0,.5);}
[data-testid="stMetric"] {background:var(--panel); border:1px solid var(--cizgi); border-radius:14px; padding:10px 12px;}
[data-testid="stMetricValue"] {font-weight:800;}
.stProgress > div > div > div > div {background:linear-gradient(90deg, #F7D98B, #B8862B);}

/* ---------- Ana sayfa şeritleri (yana kaydırılır) ---------- */
.serit-k {display:flex; gap:9px; overflow-x:auto; padding:2px 2px 8px; scroll-snap-type:x proximity; -webkit-overflow-scrolling:touch;}
.serit-k::-webkit-scrollbar {height:0;}
.mk {flex:none; width:132px; background:linear-gradient(180deg,#18191C,#111214); border:1px solid var(--cizgi); border-radius:16px;
     padding:9px 10px 4px; scroll-snap-align:start; box-shadow:0 8px 20px rgba(0,0,0,.35);}
.mk-a {font-size:.7rem; color:var(--soluk); font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.mk-d {font-size:1.06rem; font-weight:850; margin-top:2px; font-variant-numeric:tabular-nums;}
.mk-y {font-size:.72rem; font-weight:800;}
.mk-l {width:15px; height:15px; border-radius:50%; vertical-align:-3px; margin-right:5px; background:#fff;}
.fk {flex:none; width:228px; background:linear-gradient(160deg, color-mix(in srgb, var(--v) 14%, #17181B), #121315 60%);
     border:1px solid color-mix(in srgb, var(--v) 45%, transparent); border-radius:16px; padding:11px 12px; scroll-snap-align:start;}
.fk-u {display:flex; justify-content:space-between; align-items:center; gap:6px; font-size:.98rem;}
.fk-u .mk-l {width:18px; height:18px;}
.fk-e {color:#0B0B0C; font-size:.62rem; font-weight:900; border-radius:6px; padding:2px 6px; letter-spacing:.04em;}
.fk-s {font-size:.7rem; color:var(--soluk); margin-top:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.fk-c {height:5px; border-radius:3px; background:#2A2B30; margin:8px 0 2px;}
.fk-c div {height:100%; border-radius:3px; background:linear-gradient(90deg,#B8862B,#E8B84A);}
.fk-p {font-size:.7rem; color:#E4E4E7; margin-top:5px; font-variant-numeric:tabular-nums;}

/* ---------- Kartlar ---------- */
.kart {position:relative; background:linear-gradient(180deg, #18191C 0%, #111214 100%); border:1px solid var(--cizgi);
       border-radius:18px; padding:12px 14px 11px 16px; margin-bottom:10px; overflow:hidden; box-shadow:0 10px 26px rgba(0,0,0,.4);}
.kart:before {content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--v, #E8B84A); box-shadow:0 0 14px var(--v, #E8B84A);}
.kart .e {font-size:.64rem; color:var(--soluk); font-weight:800; letter-spacing:.09em; text-transform:uppercase;}
.kart .d {font-size:1.34rem; font-weight:850; letter-spacing:-.015em; margin:3px 0 1px; font-variant-numeric:tabular-nums;}
.kart .a {font-size:.74rem; color:var(--soluk);}
.pk {position:relative; display:flex; justify-content:space-between; align-items:center; gap:10px;
     background:linear-gradient(180deg, #1A1B1E 0%, #111214 100%); border:1px solid var(--cizgi); border-radius:20px;
     padding:14px 14px 12px 18px; margin-bottom:12px; box-shadow:0 12px 28px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.04);}
.pk-ad {font-size:.86rem; color:#E4E4E7; font-weight:600;}
.pk-d {font-size:1.7rem; font-weight:800; color:#FFFFFF; letter-spacing:-.02em; line-height:1.15; margin:2px 0 6px; font-variant-numeric:tabular-nums;}
.rozet {display:inline-flex; align-items:center; gap:5px; padding:2px 10px; border-radius:999px; font-weight:800; font-size:.8rem; font-variant-numeric:tabular-nums;}
.rozet.y {background:linear-gradient(180deg, rgba(34,197,94,.30), rgba(21,128,61,.30)); color:#86EFAC; box-shadow:inset 0 0 0 1px rgba(34,197,94,.55);}
.rozet.k {background:linear-gradient(180deg, rgba(239,68,68,.32), rgba(153,27,27,.32)); color:#FCA5A5; box-shadow:inset 0 0 0 1px rgba(239,68,68,.6);}
.rozet.n {background:rgba(255,255,255,.06); color:#D4D4D8; box-shadow:inset 0 0 0 1px rgba(255,255,255,.12);}
.pk-alt {font-size:.74rem; color:var(--soluk); margin-top:6px;}
.bolum {display:flex; align-items:center; gap:10px; margin:16px 0 12px; color:#F5F5F7; font-weight:800; font-size:1.32rem;}
.bolum .ik {width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center;
     background:radial-gradient(circle at 35% 30%, #22C55E, #14532D); box-shadow:0 0 14px rgba(34,197,94,.45);}
.bolum:after {content:""; flex:1; height:1px; margin-left:6px; background:linear-gradient(90deg, rgba(255,255,255,.18), transparent);}
.alt-not {color:var(--soluk); font-size:.72rem; text-align:center; margin-top:18px; line-height:1.5;}
</style>"""

# ----------------------------------------------------------------------------- üst bant (iframe)
BANT_STIL = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
*{box-sizing:border-box} html,body{margin:0;padding:0;background:transparent;overflow:hidden;font-family:'Inter',-apple-system,sans-serif}
.hero{height:118px;background-size:cover;background-position:center 45%;position:relative;
      -webkit-mask-image:linear-gradient(180deg,transparent 0,#000 30%,#000 62%,transparent 100%);mask-image:linear-gradient(180deg,transparent 0,#000 30%,#000 62%,transparent 100%)}
.ub{position:relative;margin:-30px 3px 6px;border-radius:22px;padding:14px 16px 0;overflow:hidden;
    background:linear-gradient(180deg,rgba(28,29,32,.92),rgba(14,15,17,.96));border:1px solid rgba(255,255,255,.10);
    box-shadow:0 18px 40px rgba(0,0,0,.6),inset 0 1px 0 rgba(255,255,255,.06);backdrop-filter:blur(6px)}
.ust{display:flex;justify-content:space-between;align-items:center}
.marka{display:flex;align-items:center;gap:10px;min-width:0}
.logo{flex:0 0 auto;width:42px;height:42px;border-radius:12px;display:flex;align-items:center;justify-content:center;
      background:linear-gradient(145deg,#F7D98B 0%,#E8B84A 45%,#9C6F1E 100%);
      box-shadow:0 6px 18px rgba(232,184,74,.35),inset 0 1px 0 rgba(255,255,255,.55),inset 0 -2px 0 rgba(0,0,0,.25)}
.logo-img{flex:0 0 auto;width:46px;height:46px;border-radius:12px;display:block;
          box-shadow:0 6px 18px rgba(232,184,74,.25),0 0 0 1px rgba(232,184,74,.35)}
.ad{color:#fff;font-weight:900;font-size:clamp(.86rem,4.3vw,1.12rem);letter-spacing:.01em;line-height:1.1;white-space:nowrap}
.ad span{color:#E8B84A}
.alt{white-space:nowrap;color:#9A9BA3;font-size:clamp(.56rem,2.6vw,.68rem);font-weight:600;letter-spacing:.05em;margin-top:3px}
.saat{flex:0 0 auto;white-space:nowrap;text-align:right;color:#fff;font-weight:800;font-size:1.02rem;font-variant-numeric:tabular-nums}
.saat small{display:block;color:#9A9BA3;font-weight:600;font-size:clamp(.54rem,2.5vw,.64rem);letter-spacing:.04em;margin-top:2px}
.durum{display:flex;gap:6px;flex-wrap:nowrap;margin:12px 0 11px}
.hap{white-space:nowrap;font-size:clamp(.58rem,2.8vw,.7rem);font-weight:700;padding:5px 9px;border-radius:999px;display:inline-flex;align-items:center;gap:6px;color:#fff;
     background:linear-gradient(180deg,#7F1D1D,#B91C1C);box-shadow:inset 0 0 0 1px rgba(248,113,113,.7),0 0 14px rgba(239,68,68,.35)}
.hap i{width:8px;height:8px;border-radius:50%;background:#FCA5A5;box-shadow:0 0 6px #F87171;display:inline-block}
.hap.acik{background:linear-gradient(180deg,#14532D,#15803D);box-shadow:inset 0 0 0 1px rgba(74,222,128,.7),0 0 14px rgba(34,197,94,.35)}
.hap.acik i{background:#86EFAC;box-shadow:0 0 6px #4ADE80;animation:nb 1.8s infinite}
@keyframes nb{0%,100%{opacity:1}50%{opacity:.35}}
.serit{margin:0 -16px;border-top:1px solid rgba(255,255,255,.08);overflow:hidden;
       -webkit-mask-image:linear-gradient(90deg,transparent,#000 6%,#000 94%,transparent)}
.serit-ic{display:inline-flex;white-space:nowrap;padding:10px 0;animation:kay 60s linear infinite}
@keyframes kay{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.si{display:inline-flex;align-items:baseline;gap:8px;padding:0 16px;border-right:1px solid rgba(255,255,255,.10);font-variant-numeric:tabular-nums}
.si b{color:#A1A1AA;font-size:.72rem;font-weight:600;letter-spacing:.03em}
.si em{font-style:normal;color:#fff;font-weight:800;font-size:.86rem}
.si u{text-decoration:none;font-weight:800;font-size:.78rem}
.y{color:#4ADE80}.k{color:#F87171}.n{color:#A1A1AA}
</style>"""

LOGO = ('<svg width="28" height="28" viewBox="0 0 24 24" fill="none">'
        '<rect x="3.2" y="8" width="3.6" height="9" rx="1" fill="#1A1206"/><path d="M5 4.5V8M5 17v3" stroke="#1A1206" stroke-width="1.6" stroke-linecap="round"/>'
        '<rect x="10.2" y="5" width="3.6" height="10" rx="1" fill="#1A1206"/><path d="M12 2v3M12 15v4" stroke="#1A1206" stroke-width="1.6" stroke-linecap="round"/>'
        '<rect x="17.2" y="9" width="3.6" height="7" rx="1" fill="#1A1206"/><path d="M19 6v3M19 16v3.5" stroke="#1A1206" stroke-width="1.6" stroke-linecap="round"/></svg>')

SERIT = ["BIST 100", "USD/TRY", "Gram altın", "Ons altın", "Bitcoin", "S&P 500", "Nasdaq", "Brent petrol", "Brent", "Gümüş", "EUR/TRY", "Ethereum", "Dolar endeksi", "VIX"]

_HERO = None
_LOGO = None
SIMGE_URL = "https://raw.githubusercontent.com/erhankatkay-glitch/bist-rapor/main/varlik/apple-touch-icon.png"


def _logo_url():
    global _LOGO
    if _LOGO is None:
        yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "varlik", "logo_96.png")
        try:
            _LOGO = "data:image/png;base64," + base64.b64encode(open(yol, "rb").read()).decode()
        except Exception:
            _LOGO = ""
    return _LOGO


def _hero_url():
    global _HERO
    if _HERO is None:
        yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "varlik", "hero.jpg")
        try:
            _HERO = "data:image/jpeg;base64," + base64.b64encode(open(yol, "rb").read()).decode()
        except Exception:
            _HERO = ""
    return _HERO


def piyasa_durumu(simdi=None):
    t = simdi or dt.datetime.now(ZoneInfo("Europe/Istanbul"))
    e = t.astimezone(ZoneInfo("America/New_York"))
    bist = t.weekday() < 5 and dt.time(10, 0) <= t.time() < dt.time(18, 10)
    abd = e.weekday() < 5 and dt.time(9, 30) <= e.time() < dt.time(16, 0)
    return {"BIST": bist, "ABD": abd, "Kripto 7/24": True}


def _sayi(x, nd=2):
    return f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _serit(pv):
    if not pv: return ""
    og = []
    for ad in SERIT:
        v = pv.get(ad)
        if not v or v.get("deger") is None: continue
        d = v.get("d1G") or 0
        c = "y" if d > 0 else "k" if d < 0 else "n"; ok = "▲" if d > 0 else "▼" if d < 0 else "•"
        nd = 0 if v["deger"] >= 10000 else 2 if v["deger"] >= 1 else 4
        og.append(f'<span class="si"><b>{ad.upper()}</b><em>{_sayi(v["deger"], nd)}</em><u class="{c}">{ok} %{_sayi(abs(d) * 100, 2)}</u></span>')
    if not og: return ""
    ic = "".join(og)
    return f'<div class="serit"><div class="serit-ic">{ic}{ic}</div></div>'


def ust_bant(pv=None):
    t = dt.datetime.now(ZoneInfo("Europe/Istanbul"))
    gun = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"][t.weekday()]
    ay = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"][t.month - 1]
    kim = {"BIST": "d_bist", "ABD": "d_abd", "Kripto 7/24": "d_kr"}
    dur = "".join(f'<span class="hap{" acik" if a else ""}" id="{kim[ad]}"><i></i>{ad}&nbsp;·&nbsp;<span>{"Açık" if a else "Kapalı"}</span></span>'
                  for ad, a in piyasa_durumu(t).items())
    hero = _hero_url()
    return ((f'<div class="hero" style="background-image:url({hero})"></div>' if hero else '<div style="height:36px"></div>') +
            f'<div class="ub"><div class="ust"><div class="marka">'
            + (f'<img class="logo-img" src="{_logo_url()}" alt="KATKAY">' if _logo_url() else f'<div class="logo">{LOGO}</div>') +
            f'<div><div class="ad">{MARKA_1} <span>{MARKA_2}</span></div><div class="alt">BIST · ABD · KRİPTO · EMTİA</div></div></div>'
            f'<div class="saat" id="saat">{t:%H:%M}<small id="tarih">{t.day} {ay} {gun} · TSİ</small></div></div>'
            f'<div class="durum">{dur}</div>{_serit(pv)}</div>')


# ----------------------------------------------------------------------------- canlı saat + alt gezinme (JS)
NAV_STIL = """
#kk-nav{position:fixed;left:10px;right:10px;margin:0 auto;max-width:640px;bottom:calc(64px + env(safe-area-inset-bottom));z-index:999999;
  /* Streamlit'in sağ alttaki yönetim düğmesinin üstünde durur, onunla çakışmaz */display:flex;justify-content:space-around;align-items:stretch;padding:8px 6px 7px;border-radius:22px;
  background:linear-gradient(180deg,rgba(26,27,30,.94),rgba(12,13,15,.97));border:1px solid rgba(255,255,255,.10);
  box-shadow:0 16px 40px rgba(0,0,0,.65),inset 0 1px 0 rgba(255,255,255,.06);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
  font-family:'Inter',-apple-system,sans-serif}
#kk-nav button{flex:1;touch-action:manipulation;background:none;border:none;color:#9A9BA3;display:flex;flex-direction:column;align-items:center;gap:4px;
  font-size:11px;font-weight:600;padding:4px 0;cursor:pointer;position:relative;-webkit-tap-highlight-color:transparent}
#kk-nav button+button:before{content:"";position:absolute;left:0;top:18%;bottom:18%;width:1px;background:rgba(255,255,255,.08)}
#kk-nav svg{width:24px;height:24px}
#kk-nav button.aktif{color:#E8B84A}
#kk-nav button.aktif:after{content:"";position:absolute;bottom:-3px;width:34px;height:3px;border-radius:3px;background:#E8B84A;box-shadow:0 0 10px #E8B84A}
"""

NAV_OGE = [
    ("Ana Sayfa", "Ana Sayfa", '<path d="M3 11.5 12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z" fill="#E8B84A"/>'),
    ("Keşfet", "Keşfet", '<circle cx="11" cy="11" r="6.5" fill="none" stroke="#E8B84A" stroke-width="2.4"/><path d="m16 16 4.5 4.5" stroke="#E8B84A" stroke-width="2.6" stroke-linecap="round"/>'),
    ("Portföy", "Portföy", '<rect x="3" y="7" width="18" height="13" rx="2.5" fill="#E8B84A"/><path d="M8.5 7V5.5A1.5 1.5 0 0 1 10 4h4a1.5 1.5 0 0 1 1.5 1.5V7" fill="none" stroke="#E8B84A" stroke-width="2"/>'),
    ("Takip", "Takip", '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z" fill="#E8B84A"/>'),
]

CANLI_JS = """
<script>
(function(){
  const gunler=["Paz","Pzt","Sal","Çar","Per","Cum","Cmt"], aylar=["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"];
  function parca(tz){
    const f=new Intl.DateTimeFormat("en-GB",{timeZone:tz,year:"numeric",month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit",hour12:false,weekday:"short"});
    const o={}; f.formatToParts(new Date()).forEach(p=>o[p.type]=p.value);
    return {g:+o.day,a:+o.month,s:+o.hour%24,d:+o.minute,wd:{"Sun":0,"Mon":1,"Tue":2,"Wed":3,"Thu":4,"Fri":5,"Sat":6}[o.weekday]};
  }
  function durum(id,acik){const e=document.getElementById(id); if(!e) return; e.className="hap"+(acik?" acik":""); e.querySelector("span").textContent=acik?"Açık":"Kapalı";}
  function saat(){
    const t=parca("Europe/Istanbul"), n=parca("America/New_York"), dk=t.s*60+t.d, ndk=n.s*60+n.d;
    document.getElementById("saat").firstChild.nodeValue=String(t.s).padStart(2,"0")+":"+String(t.d).padStart(2,"0");
    document.getElementById("tarih").textContent=t.g+" "+aylar[t.a-1]+" "+gunler[t.wd]+" · TSİ";
    durum("d_bist",t.wd>=1&&t.wd<=5&&dk>=600&&dk<1090); durum("d_abd",n.wd>=1&&n.wd<=5&&ndk>=570&&ndk<960);
  }
  saat(); setInterval(saat,10000);
  // ---- ana ekran simgesi / sekme simgesi
  [window.parent, window.top].forEach(w=>{try{
    const D=w.document; if(D.getElementById("kk-simge")) return;
    const ek=(rel,extra)=>{const l=D.createElement("link"); l.rel=rel; l.href=__SIMGE__; Object.assign(l,extra||{}); D.head.appendChild(l); return l;};
    ek("apple-touch-icon").id="kk-simge"; ek("icon",{type:"image/png"});
    [["apple-mobile-web-app-title","KATKAY"],["application-name","KATKAY Yatırım"],["apple-mobile-web-app-capable","yes"],
     ["apple-mobile-web-app-status-bar-style","black-translucent"],["theme-color","#0B0B0C"]].forEach(([n,c])=>{
       const m=D.createElement("meta"); m.name=n; m.content=c; D.head.appendChild(m);});
    D.title="KATKAY YATIRIM A.Ş.";
  }catch(e){}});
  // ---- alt gezinme çubuğu
  // Düğmeler ana sayfanın kendi kodu ile çalışır (bu iframe her yenilemede değişse de düğmeler ölmez).
  try{
    const W=window.parent, P=W.document, OGE=__OGE__;
    let st=P.getElementById("kk-nav-stil");
    if(!st){st=P.createElement("style"); st.id="kk-nav-stil"; P.head.appendChild(st);} st.textContent=__STIL__;
    if(!P.getElementById("kk-nav-js")){
      const sc=P.createElement("script"); sc.id="kk-nav-js";
      sc.textContent=`
        window.kkSekmeler=function(){return [...document.querySelectorAll('.stTabs [data-testid="stTab"], .stTabs [role="tab"], .stTabs [data-baseweb="tab"]')];};
        window.kkAd=function(t){const p=t.querySelector('[data-testid="stMarkdownContainer"] p')||t; return (p.innerText||p.textContent||"").trim();};
        window.kkGit=function(ad){
          const t=window.kkSekmeler().find(x=>window.kkAd(x).endsWith(ad));
          if(!t) return;
          t.scrollIntoView({block:"nearest",inline:"center"});
          t.dispatchEvent(new MouseEvent("mousedown",{bubbles:true})); t.click();
          const k=document.querySelector('[data-testid="stAppScrollToBottomContainer"],[data-testid="stMain"],section.main,[data-testid="stAppViewContainer"]');
          try{(k||window).scrollTo({top:0,behavior:"smooth"});}catch(e){} try{window.scrollTo({top:0,behavior:"smooth"});}catch(e){}
          setTimeout(window.kkIsaretle,80);
        };
        window.kkIsaretle=function(){
          const nav=document.getElementById("kk-nav"); if(!nav) return;
          const s=window.kkSekmeler().find(x=>x.getAttribute("aria-selected")==="true"); const ad=s?window.kkAd(s):"";
          nav.querySelectorAll("button").forEach(b=>b.classList.toggle("aktif", ad.endsWith(b.dataset.sekme)));
        };
        if(!window.kkIsaretZaman) window.kkIsaretZaman=setInterval(window.kkIsaretle,500);`;
      P.head.appendChild(sc);
    }
    const eski=P.getElementById("kk-nav"); if(eski) eski.remove();
    const nav=P.createElement("nav"); nav.id="kk-nav";
    nav.innerHTML=OGE.map(o=>'<button type="button" data-sekme="'+o[1]+'" onclick="window.kkGit(this.dataset.sekme)">'+
      '<svg viewBox="0 0 24 24">'+o[2]+'</svg><span>'+o[0]+'</span></button>').join("");
    P.body.appendChild(nav);
    if(typeof W.kkGit!=="function"){   // ana sayfaya betik eklenemezse (güvenlik politikası) yedek yol
      nav.querySelectorAll("button").forEach(b=>{b.removeAttribute("onclick"); b.addEventListener("click",()=>{
        const t=[...P.querySelectorAll('.stTabs [data-testid="stTab"], .stTabs [role="tab"], .stTabs [data-baseweb="tab"]')].find(x=>x.innerText.trim().endsWith(b.dataset.sekme)); if(t) t.click();});});
    }
    if(W.kkIsaretle) W.kkIsaretle();
  }catch(e){console.log("kk-nav",e);}
})();
</script>"""


def ust_bant_sayfa(pv=None):
    import json
    js = (CANLI_JS.replace("__OGE__", json.dumps(NAV_OGE)).replace("__STIL__", json.dumps(NAV_STIL))
          .replace("__SIMGE__", json.dumps(SIMGE_URL)))
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'>" + BANT_STIL + "</head><body>" + ust_bant(pv) + js + "</body></html>")


def bolum(baslik, ikon="public"):
    ik = {"public": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8"><circle cx="12" cy="12" r="9"/>'
                    '<path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18"/></svg>'}.get(ikon, "")
    return f'<div class="bolum"><span class="ik">{ik}</span>{baslik}</div>'
