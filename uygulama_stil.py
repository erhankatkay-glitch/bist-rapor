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
/* üst bant çerçevesinin altındaki boşluk */
.stElementContainer:has(> iframe[height="160"]) {margin-bottom:-26px !important;}
/* yüksekliği 0 olan betik çerçeveleri (alt menü, kaydetme, yükleme) sayfada boşluk bırakmasın */
.stElementContainer:has(> iframe[height="0"]), [data-testid="stElementContainer"]:has(iframe[height="0"]) {position:absolute !important; width:0 !important; height:0 !important; overflow:hidden !important; margin:0 !important; padding:0 !important;}

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

/* Bölüm içi sekmeler (Piyasalar / Haberler / Takvim …): tasarımdaki hap düğmeler */
.stTabs .stTabs [role="tablist"] {gap:8px !important; padding:2px 0 8px !important;}
.stTabs .stTabs [data-testid="stTab"] {border-radius:20px !important; border:1px solid #2A2B30 !important; background:#17181B !important;
       padding:7px 14px !important; clip-path:none !important;}
.stTabs .stTabs [data-testid="stTab"]:before {display:none !important;}
.stTabs .stTabs [aria-selected="true"] {background:#E8B84A !important; border-color:#E8B84A !important; box-shadow:none !important;}
.stTabs .stTabs [aria-selected="true"] p, .stTabs .stTabs [aria-selected="true"] [data-testid="stIconMaterial"] {color:#0B0B0C !important;}
/* üçüncü düzey (ör. Fırsatlar içi) alt çizgili kalır */
.stTabs .stTabs .stTabs [data-testid="stTab"] {border:none !important; background:transparent !important; border-radius:0 !important; padding:8px 12px !important;}
.stTabs .stTabs .stTabs [aria-selected="true"] {background:transparent !important; box-shadow:inset 0 -2px 0 var(--altin) !important;}
.stTabs .stTabs .stTabs [aria-selected="true"] p {color:var(--altin) !important;}
/* Yatay seçimler (Piyasa: BIST / ABD / Kripto / Emtia …) → tasarımdaki hap düğmeler */
[data-testid="stRadio"] [role="radiogroup"] {display:flex; flex-wrap:nowrap; overflow-x:auto; gap:8px; scrollbar-width:none; padding-bottom:2px;}
[data-testid="stRadio"] [role="radiogroup"]::-webkit-scrollbar {display:none;}
[data-testid="stRadio"] [role="radiogroup"] > label {flex:none; margin:0 !important; padding:7px 14px !important; border-radius:20px;
       border:1px solid #2A2B30; background:#17181B; cursor:pointer;}
[data-testid="stRadio"] [role="radiogroup"] > label > div:first-child {display:none !important;}
[data-testid="stRadio"] [role="radiogroup"] > label p {font-weight:700 !important; font-size:.86rem !important; color:#E4E4E7;}
[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {background:#E8B84A; border-color:#E8B84A;}
[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) p {color:#0B0B0C !important;}
[data-testid="stRadio"] > label p {font-size:.72rem !important; letter-spacing:.1em; text-transform:uppercase; color:var(--soluk) !important; font-weight:800 !important;}
/* Streamlit 1.6x radyo yapısı (stRadioGroup / stRadioOption) */
[data-testid="stRadioGroup"] {display:flex !important; flex-wrap:nowrap !important; overflow-x:auto; gap:8px !important; scrollbar-width:none; padding-bottom:2px;}
[data-testid="stRadioGroup"]::-webkit-scrollbar {display:none;}
[data-testid="stRadioOption"] {padding:7px 14px !important; margin:0 !important; border-radius:20px; border:1px solid #2A2B30; background:#17181B; cursor:pointer;}
[data-testid="stRadioOption"] > div > div:first-child {display:none !important;}
[data-testid="stRadioOption"] p {font-weight:700 !important; font-size:.86rem !important; color:#E4E4E7; white-space:nowrap;}
[data-testid="stRadioOption"][data-selected="true"] {background:#E8B84A; border-color:#E8B84A;}
[data-testid="stRadioOption"][data-selected="true"] p {color:#0B0B0C !important;}
/* gizli istek kutusu (satır düğmeleri) */
.st-key-kk_gizli, .st-key-kk_gizli2 {position:absolute !important; left:-9999px !important; height:0 !important; overflow:hidden !important;}
.kk-uyari {position:relative; background:linear-gradient(135deg,rgba(232,184,74,.22),rgba(232,184,74,.08)); border:1px solid rgba(232,184,74,.55);
  border-radius:18px; padding:12px 44px 12px 14px; margin:2px 0 10px; box-shadow:0 10px 26px rgba(0,0,0,.4);}
.kk-uyari-k {background:linear-gradient(135deg,rgba(239,68,68,.92),rgba(185,28,28,.88)); border-color:rgba(255,255,255,.18);}
.rj {background:radial-gradient(120% 90% at 100% 0%, color-mix(in srgb, var(--v) 16%, transparent), transparent 60%),linear-gradient(180deg,#18191C,#111214);
  border:1px solid color-mix(in srgb, var(--v) 45%, #2A2B30); border-radius:18px; padding:14px 14px 10px; margin-bottom:12px;}
.rj-u {display:flex; justify-content:space-between; gap:10px; align-items:flex-start;}
.rj-u small {display:block; font-size:.62rem; font-weight:900; letter-spacing:.12em; color:var(--soluk);}
.rj-u b {display:block; font-size:1.25rem; font-weight:900; color:var(--v); margin-top:2px;}
.rj-u span {font-size:.74rem; color:#D4D4D8;}
.rj-m {text-align:right;} .rj-m b {display:block; font-size:1.7rem; font-weight:900; color:#F4F4F5; line-height:1;}
.rj-m span {font-size:.62rem; color:var(--soluk); line-height:1.2; display:block; margin-top:3px;}
.rj-b {height:7px; border-radius:4px; background:#2A2B30; margin:10px 0 8px; overflow:hidden;}
.rj-b div {height:100%; border-radius:4px; background:linear-gradient(90deg,#B8862B,#F5D27A);}
.rj-t {background:rgba(239,68,68,.14); border:1px solid rgba(239,68,68,.45); color:#FCA5A5; font-size:.76rem; font-weight:700; border-radius:10px; padding:7px 9px; margin-bottom:8px;}
.rj-g {display:grid; grid-template-columns:repeat(3,1fr); gap:6px;}
.rj-g div {background:#141518; border:1px solid var(--cizgi); border-radius:12px; padding:7px 6px; text-align:center;}
.rj-g b {display:block; font-size:1rem; font-weight:850;} .rj-g span {font-size:.62rem; color:var(--soluk);}
.rj-sp {width:100%; height:70px; margin-top:10px;} .rj-alt {font-size:.62rem; color:var(--soluk); margin-top:2px;}
.rj details {margin-top:8px;} .rj summary {font-size:.78rem; font-weight:800; color:#E8B84A; cursor:pointer;}
.rj ul {margin:6px 0 4px 16px; padding:0; font-size:.76rem; color:#D4D4D8;} .rj p {font-size:.7rem; color:var(--soluk); margin:6px 0 0;}
.rj-k {display:flex; flex-wrap:wrap; align-items:center; gap:6px 10px; background:linear-gradient(90deg, color-mix(in srgb, var(--v) 16%, #17181B), #121315);
  border:1px solid color-mix(in srgb, var(--v) 45%, #2A2B30); border-left:3px solid var(--v); border-radius:12px; padding:8px 11px; margin:4px 0 10px; cursor:pointer; font-size:.8rem;}
.rj-k b {font-weight:900;} .rj-k span {color:var(--v); font-weight:800;} .rj-k em {font-style:normal; color:#D4D4D8;} .rj-k i {font-style:normal; color:#FCA5A5; font-weight:800;}
.kl {background:linear-gradient(180deg,#18191C,#111214); border:1px solid var(--cizgi); border-radius:16px; padding:10px 12px; margin:6px 0 10px;}
.kl-b {display:flex; justify-content:space-between; align-items:baseline; margin-bottom:6px;} .kl-b b {color:#E8B84A; font-size:.86rem;} .kl-b span {font-size:.74rem; color:var(--soluk); font-weight:800;}
.kl-m {display:flex; gap:10px; align-items:flex-start; padding:6px 0; border-top:1px solid rgba(255,255,255,.05);}
.kl-m i {flex:none; width:20px; height:20px; border-radius:50%; color:#0B0B0C; font-style:normal; font-weight:900; font-size:.72rem; display:flex; align-items:center; justify-content:center; margin-top:1px;}
.kl-m b {display:block; font-size:.82rem;} .kl-m span {font-size:.74rem; color:var(--soluk);}
.kl-g {display:grid; grid-template-columns:repeat(3,1fr); gap:6px;} .kl-g div {background:#141518; border:1px solid var(--cizgi); border-radius:12px; padding:8px 6px; text-align:center;}
.kl-g b {display:block; font-size:1rem; font-weight:850;} .kl-g span {font-size:.62rem; color:var(--soluk);}
.kl-o {font-size:.78rem; color:#D4D4D8; margin-top:7px;}
.kk-bild {display:none !important;} .stElementContainer:has(.kk-bild) {display:none !important;}
#kk-toast {position:fixed; left:10px; right:10px; max-width:620px; margin:0 auto; top:calc(10px + env(safe-area-inset-top)); z-index:999999;
  transform:translateY(-160%); opacity:0; transition:transform .38s cubic-bezier(.2,.9,.25,1.15), opacity .3s; pointer-events:none;}
#kk-toast.acik {transform:none; opacity:1; pointer-events:auto;}
#kk-toast .kk-uyari {margin:0; cursor:pointer; box-shadow:0 18px 40px rgba(0,0,0,.6); backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px); overflow:hidden;}
#kk-toast .kk-uyari:not(.kk-uyari-k) {background:linear-gradient(135deg,rgba(58,46,18,.97),rgba(24,22,16,.97));}
#kk-toast .kk-uyari:after {content:""; position:absolute; left:0; bottom:0; height:3px; width:100%; background:linear-gradient(90deg,#F5D27A,#C99A2E);
  transform-origin:left; animation:kkSure var(--sure,9000ms) linear forwards;}
#kk-toast .kk-uyari-k:after {background:rgba(255,255,255,.75);}
#kk-toast .say {position:absolute; right:46px; top:12px; font-size:.68rem; font-weight:800; color:rgba(255,255,255,.75);}
@keyframes kkSure {from {transform:scaleX(1)} to {transform:scaleX(0)}}
.kk-uyari b {display:block; font-size:.95rem; font-weight:850; color:#fff;} .kk-uyari div {font-size:.82rem; color:#F4F4F5; margin-top:3px; line-height:1.35;}
.kk-x {position:absolute; right:10px; top:10px; width:26px; height:26px; border-radius:50%; background:rgba(255,255,255,.18); color:#fff;
  display:flex; align-items:center; justify-content:center; font-size:1rem; cursor:pointer;}
.kk-kutu {display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin:12px 0 4px;}
.kk-kutu span {display:flex; flex-direction:column; align-items:center; gap:6px; padding:12px 4px 10px; border-radius:16px; cursor:pointer;
  background:linear-gradient(180deg,#18191C,#111214); border:1px solid var(--cizgi);} .kk-kutu svg {width:26px; height:26px;}
.kk-kutu b {font-size:.74rem; font-weight:750; color:#E4E4E7;}
.kk-kutu span:active {border-color:rgba(232,184,74,.6);}
.kk-alt2 {font-size:.92rem; color:var(--altin); font-weight:700;}
.kk-alt {font-size:.8rem; color:var(--soluk); line-height:1.35;} .kk-alt b {color:var(--altin);}
.kk-kalem {color:var(--altin); font-weight:750; cursor:pointer; white-space:nowrap; margin-left:4px;}
.kk-geri {display:inline-block; color:var(--altin); font-weight:800; font-size:.85rem; cursor:pointer; padding:4px 2px 8px;}
.oc-sp {margin-top:4px; height:24px;}
.oc-d2 {display:flex; gap:6px; flex:none;}
.oc-t {display:flex; flex-direction:column; align-items:center; justify-content:center; gap:3px; width:52px; height:52px; border-radius:13px; cursor:pointer;
  background:rgba(232,184,74,.1); border:1px solid rgba(232,184,74,.45); color:var(--altin);} .oc-t i {font-style:normal; font-size:.62rem; font-weight:800;}
.oc-t2 {background:#111214; border-color:#2A2B30; color:#E4E4E7;}
.oc-d {display:flex; flex-direction:column; gap:5px; flex:none;}
.oc-b {background:rgba(232,184,74,.1); border:1px solid rgba(232,184,74,.4); color:var(--altin); border-radius:10px; font-size:.7rem;
       font-weight:800; padding:6px 9px; text-align:center; cursor:pointer; -webkit-tap-highlight-color:transparent; user-select:none;}
.oc-b2 {background:#111214; border-color:#2A2B30; color:#E4E4E7;}
/* tasarımdaki bölüm başlığı: ÖNE ÇIKANLAR ———— */
.bb {display:flex; align-items:center; gap:10px; margin:18px 2px 8px; font-size:.8rem; font-weight:850; letter-spacing:.14em;}
.bb:after {content:""; flex:1; height:1px; background:linear-gradient(90deg, rgba(232,184,74,.6), transparent);}
/* Öne çıkanlar listesi */
.oc {display:flex; align-items:center; gap:10px; background:linear-gradient(180deg,#18191C,#111214); border:1px solid var(--cizgi);
     border-radius:16px; padding:10px 12px; margin-bottom:8px;}
.oc-l {width:38px; height:38px; border-radius:11px; background:#fff; object-fit:contain; flex:none;}
.oc-h {width:38px; height:38px; border-radius:11px; background:#1F2937; color:var(--altin); font-weight:850; font-size:.72rem;
       display:flex; align-items:center; justify-content:center; flex:none;}
.oc-a {flex:1; min-width:0;} .oc-a b {font-size:.98rem;} .oc-a div {font-size:.72rem; color:var(--soluk); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.oc-f {text-align:right;} .oc-f b {font-size:1rem; font-variant-numeric:tabular-nums;}
.oc-p {display:inline-block; margin-top:3px; font-size:.74rem; font-weight:800; border-radius:8px; padding:2px 8px;}

/* Haber ve takvim kartları */
.cip {display:inline-flex; align-items:center; gap:4px; font-size:.72rem; font-weight:700; border:1px solid #2A2B30; background:#111214;
      color:#E4E4E7; border-radius:20px; padding:3px 9px; margin:4px 5px 0 0;}
.cip-a {border-color:rgba(232,184,74,.5); color:var(--altin);}
.cipler {margin-top:4px;}
.hb {background:linear-gradient(180deg,#18191C,#111214); border:1px solid var(--cizgi); border-left:3px solid var(--v); border-radius:16px;
     padding:11px 13px; margin-bottom:9px;}
.hb-u {display:flex; justify-content:space-between; align-items:center; gap:8px;} .hb-u .cip {margin:0;}
.hb-b {font-weight:750; font-size:.95rem; line-height:1.35; margin:7px 0 4px;}
.hb-e {font-size:.76rem; font-weight:800;}
.hb-l {display:inline-block; margin-top:8px; font-size:.78rem; font-weight:800; color:var(--altin) !important; text-decoration:none;}
.tk {display:flex; gap:12px; background:linear-gradient(180deg,#18191C,#111214); border:1px solid var(--cizgi); border-radius:16px;
     padding:11px 13px; margin-bottom:9px;}
.tk-g {opacity:.62;}
.tk-s {flex:none; width:62px; font-weight:850; font-size:1.05rem; color:var(--altin); font-variant-numeric:tabular-nums;}
.tk-s small {display:block; font-size:.66rem; color:var(--soluk); font-weight:600; margin-top:2px;}
.tk-i {flex:1; min-width:0;} .tk-i > b {font-size:.92rem; line-height:1.3;}
.tk-k {display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:6px; margin-top:7px;}
.tk-k > div {background:#111214; border-radius:10px; padding:5px 8px;}

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
.mk-a {font-size:.7rem; color:var(--soluk); font-weight:700; display:flex; justify-content:space-between; align-items:center; gap:4px;}
.mk-ad {white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0;}
.vk-k {font-size:.52rem; padding:0 5px; flex:none;}
.mk-d {font-size:1.06rem; font-weight:850; margin-top:2px; font-variant-numeric:tabular-nums;}
.mk-y {font-size:.72rem; font-weight:800;}
.vk {display:inline-flex; align-items:center; gap:4px; font-size:.6rem; font-weight:800; letter-spacing:.3px; border:1px solid; border-radius:20px; padding:1px 6px; vertical-align:1px; text-transform:uppercase; white-space:nowrap;}
.vk i {width:5px; height:5px; border-radius:50%; display:inline-block;}
.mk-l {width:15px; height:15px; border-radius:50%; vertical-align:-3px; margin-right:5px; background:#fff;}
/* referans: 4 mini kart tek ekranda */
.serit-mk .mk {width:calc((100% - 27px) / 4); min-width:80px; padding:8px 7px 3px; border-radius:14px;}
.serit-mk .mk-d {font-size:.92rem;} .serit-mk .mk-y {font-size:.66rem;} .serit-mk .mk-a {font-size:.68rem;}
.serit-mk .mk svg {width:100%; height:34px;}
.kk-kutu {margin-top:-12px;}
/* Öne çıkanlar: açıklama + kalem + liste seçimi referanstaki gibi tek satırda */
[data-testid="stHorizontalBlock"]:has(.kk-alt2) {flex-wrap:nowrap !important; gap:8px !important; align-items:center !important;}
[data-testid="stHorizontalBlock"]:has(.kk-alt2) > [data-testid="stColumn"] {min-width:0 !important; width:auto !important; flex:1.25 1 0 !important;}
[data-testid="stHorizontalBlock"]:has(.kk-alt2) > [data-testid="stColumn"]:last-child {flex:1 1 0 !important;}
[data-testid="stHorizontalBlock"]:has(.kk-alt2) .kk-alt2 {font-size:.78rem; line-height:1.3;}
.mk-n {width:6px; height:6px; border-radius:50%; flex:none; display:inline-block;}
/* arama kutusu: referanstaki gibi düz, ok yok */
.st-key-ana_ara [data-baseweb="select"] > div {border-radius:24px !important; background:#141517 !important;}
.st-key-ana_ara svg {display:none !important;}
.fk {flex:none; width:228px; background:linear-gradient(160deg, color-mix(in srgb, var(--v) 14%, #17181B), #121315 60%);
     border:1px solid color-mix(in srgb, var(--v) 45%, transparent); border-radius:16px; padding:11px 12px; scroll-snap-align:start;}
.fk-u {display:flex; justify-content:space-between; align-items:center; gap:6px; font-size:.98rem;}
.fk-u .mk-l {width:18px; height:18px;}
.fk-e {color:#0B0B0C; font-size:.62rem; font-weight:900; border-radius:6px; padding:2px 6px; letter-spacing:.04em;}
.fk-s {font-size:.7rem; color:var(--soluk); margin-top:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.fk-c {height:5px; border-radius:3px; background:#2A2B30; margin:8px 0 2px;}
.fk-c div {height:100%; border-radius:3px; background:linear-gradient(90deg,#B8862B,#E8B84A);}
.fl-b {display:flex; justify-content:space-between; align-items:baseline; margin:12px 2px 5px; font-size:.8rem; font-weight:800;
  color:var(--altin,#E8B84A); letter-spacing:.03em; text-transform:uppercase;}
.fl-b span {font-size:.68rem; font-weight:600; color:var(--soluk); text-transform:none; letter-spacing:0;}
.fl {background:linear-gradient(100deg, color-mix(in srgb, var(--v) 10%, #17181B), #121315 55%); border:1px solid rgba(255,255,255,.07);
  border-left:3px solid var(--v); border-radius:12px; padding:8px 10px 6px; margin-bottom:6px;}
.fl-u {display:flex; align-items:center; gap:8px; font-size:.92rem;}
.fl-u b {display:flex; align-items:center; gap:6px; white-space:nowrap;} .fl-u .mk-l {width:18px; height:18px;}
.fl-k {flex:1; min-width:0; font-size:.68rem; color:var(--soluk); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.fl-a {display:flex; justify-content:space-between; gap:8px; margin-top:4px; font-size:.7rem; font-variant-numeric:tabular-nums;}
.fl-p {color:#E4E4E7; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;} .fl-n {color:#E8B84A; font-weight:800; white-space:nowrap;}
.fl .fk-c {margin:5px 0 0; height:3px;}
.fk-p {font-size:.7rem; color:#E4E4E7; margin-top:5px; font-variant-numeric:tabular-nums;}

/* ---------- Varlık sayfası ---------- */
.vb, .sv, .kn {background:linear-gradient(180deg,#18191C,#111214); border:1px solid var(--cizgi); border-radius:20px; padding:15px; margin:4px 0 12px;
               box-shadow:0 10px 26px rgba(0,0,0,.4);}
.vb-u {display:flex; justify-content:space-between; align-items:flex-start; gap:10px;}
.vb-k {display:flex; gap:10px; align-items:center;}
.vb-l {width:44px; height:44px; border-radius:12px; background:#fff; object-fit:contain; flex:none;}
.vb-h {background:#1F2937; color:var(--altin); font-weight:850; font-size:.8rem; display:flex; align-items:center; justify-content:center;}
.vb-ad {font-weight:850; font-size:1.25rem;}
.vb-f {font-weight:850; font-size:1.75rem; letter-spacing:-.02em; font-variant-numeric:tabular-nums;}
.vb-e {font-size:.7rem; color:var(--soluk);}
.vb-p {font-weight:850; font-size:.86rem;}
.vb-3 {display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; margin-top:12px; padding-top:11px; border-top:1px solid var(--cizgi); text-align:center;}
.sv-b {font-size:.72rem; font-weight:850; letter-spacing:.12em; color:var(--altin); margin-bottom:4px;}
.sv-s {display:flex; justify-content:space-between; align-items:center; padding:9px 0; border-bottom:1px solid var(--cizgi);}
.sv-c {position:relative; height:26px; margin:10px 4px 0;}
.sv-cz {position:absolute; left:0; right:0; top:11px; height:4px; border-radius:2px; background:linear-gradient(90deg,#EF4444,#E8B84A 45%,#22C55E);}
.sv-n {position:absolute; top:6px; width:13px; height:13px; margin-left:-6px; border-radius:50%; border:2px solid #0B0B0C;}
.sv-f {position:absolute; top:2px; width:21px; height:21px; margin-left:-10px; border-radius:50%; background:var(--altin); border:3px solid #0B0B0C;}
.kn {background:linear-gradient(160deg, rgba(232,184,74,.12), #17181B 60%); border-color:rgba(232,184,74,.4);}
.kn-t {font-weight:800; font-size:1rem; margin:4px 0 6px;}
.kn-y {font-size:.88rem; color:#E4E4E7; line-height:1.55;}
.kn-s {font-size:.84rem; margin-top:6px;}

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
#kk-nav{position:fixed;left:6px;right:6px;margin:0 auto;max-width:640px;bottom:calc(64px + env(safe-area-inset-bottom));z-index:999999;
  /* Streamlit'in sağ alttaki yönetim düğmesinin üstünde durur, onunla çakışmaz */display:flex;justify-content:space-around;align-items:stretch;padding:7px 4px 6px;border-radius:22px;
  background:linear-gradient(180deg,rgba(26,27,30,.94),rgba(12,13,15,.97));border:1px solid rgba(255,255,255,.10);
  box-shadow:0 16px 40px rgba(0,0,0,.65),inset 0 1px 0 rgba(255,255,255,.06);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
  font-family:'Inter',-apple-system,sans-serif}
#kk-nav button{flex:1;touch-action:manipulation;background:none;border:none;color:#9A9BA3;display:flex;flex-direction:column;align-items:center;gap:4px;
  font-size:10px;font-weight:600;padding:4px 0;min-width:0;white-space:nowrap;letter-spacing:-.1px;cursor:pointer;position:relative;-webkit-tap-highlight-color:transparent}
#kk-nav button+button:before{content:"";position:absolute;left:0;top:18%;bottom:18%;width:1px;background:rgba(255,255,255,.08)}
#kk-nav svg{width:21px;height:21px}
#kk-cek{position:fixed;left:0;top:46%;z-index:999998;width:16px;height:62px;opacity:.92;border-radius:0 14px 14px 0;border:none;cursor:pointer;
  background:linear-gradient(180deg,#F5D27A,#C99A2E);box-shadow:4px 6px 18px rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;padding:0}
#kk-cek i{display:block;width:8px;height:2px;background:#0B0B0C;border-radius:2px;box-shadow:0 -5px 0 #0B0B0C,0 5px 0 #0B0B0C}
#kk-ckm{position:fixed;inset:0;z-index:1000000;visibility:hidden}
#kk-ckm.acik{visibility:visible}
#kk-ckm .ort{position:absolute;inset:0;background:rgba(0,0,0,.62);backdrop-filter:blur(3px);-webkit-backdrop-filter:blur(3px);opacity:0;transition:opacity .25s}
#kk-ckm.acik .ort{opacity:1}
#kk-ckm .pan{position:absolute;left:0;top:0;height:100vh;height:100dvh;width:min(84vw,330px);overflow-y:auto;font-family:'Inter',-apple-system,sans-serif;
  background:radial-gradient(120% 60% at 0% 0%,rgba(232,184,74,.16),transparent 60%),linear-gradient(180deg,#141518,#0B0B0C);
  border-right:1px solid rgba(232,184,74,.45);border-radius:0 26px 26px 0;box-shadow:16px 0 50px rgba(0,0,0,.7);
  transform:translateX(-104%);transition:transform .28s cubic-bezier(.2,.8,.2,1);padding:0 12px calc(150px + env(safe-area-inset-bottom));overscroll-behavior:contain}
#kk-ckm.acik .pan{transform:none}
#kk-ckm .bas{display:flex;align-items:center;gap:11px;padding:calc(18px + env(safe-area-inset-top)) 6px 16px;border-bottom:1px solid rgba(232,184,74,.22);margin-bottom:4px}
#kk-ckm .bas img{width:42px;height:42px;border-radius:13px;border:1px solid rgba(232,184,74,.6);box-shadow:0 4px 14px rgba(232,184,74,.25)}
#kk-ckm .bas b{display:block;color:#F4F4F5;font-size:16px;font-weight:900;letter-spacing:.2px}#kk-ckm .bas b span{color:#E8B84A}
#kk-ckm .bas i{display:block;font-style:normal;color:#8E8F96;font-size:9.5px;font-weight:800;letter-spacing:1.3px;margin-top:2px}
#kk-ckm .kap{margin-left:auto;width:34px;height:34px;border-radius:50%;border:1px solid rgba(255,255,255,.12);background:#1B1C20;color:#D4D4D8;
  font-size:19px;line-height:1;display:flex;align-items:center;justify-content:center;cursor:pointer}
#kk-ckm small{display:flex;align-items:center;gap:8px;color:#E8B84A;font-size:10px;font-weight:900;letter-spacing:1.6px;margin:13px 6px 6px}
#kk-ckm small:after{content:"";flex:1;height:1px;background:linear-gradient(90deg,rgba(232,184,74,.45),transparent)}
#kk-ckm a{display:flex;align-items:center;gap:12px;text-decoration:none;padding:6px 10px;margin:0 0 5px;border-radius:15px;cursor:pointer;
  background:linear-gradient(180deg,#18191C,#121315);border:1px solid rgba(255,255,255,.06);-webkit-tap-highlight-color:transparent}
#kk-ckm a .ik{flex:none;width:34px;height:34px;border-radius:11px;display:flex;align-items:center;justify-content:center;
  background:rgba(232,184,74,.10);border:1px solid rgba(232,184,74,.28)}
#kk-ckm a .ik svg{width:19px;height:19px}
#kk-ckm a .yz{min-width:0;flex:1}#kk-ckm a .yz b{display:block;color:#F4F4F5;font-size:14px;font-weight:750}
#kk-ckm a .yz em{display:block;font-style:normal;color:#8E8F96;font-size:11px;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#kk-ckm a .ok{color:#5A5B62;font-size:18px}
#kk-ckm a:active{transform:scale(.985)}
#kk-ckm a.aktif{background:linear-gradient(135deg,rgba(232,184,74,.22),rgba(232,184,74,.06));border-color:rgba(232,184,74,.6)}
#kk-ckm a.aktif .ik{background:linear-gradient(180deg,#F5D27A,#C99A2E);border-color:transparent}
#kk-ckm a.aktif .ik svg{stroke:#0B0B0C}#kk-ckm a.aktif .yz b{color:#F5D27A}#kk-ckm a.aktif .ok{color:#E8B84A}
#kk-ckm .alt{margin:18px 8px 0;color:#5F6068;font-size:10.5px;line-height:1.45;text-align:center}
"""

# Alt menü (referansla aynı 6 sekme). (etiket, gidilecek "Üst|Alt", simge, aktif sayılacağı alt sekmeler)
# Portföy ve Takip ana sayfadaki "Benim" / "Bildirimler" kutularından açılır.
NAV_OGE = [
    ("Ana sayfa", "Ana Sayfa|Piyasalar", '<path d="M3 11.5 12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z" fill="#E8B84A"/>',
     ["Ana Sayfa|Piyasalar", "Ana Sayfa|Takvim", "Ana Sayfa|Ekonomi"]),
    ("Piyasalar", "Keşfet|Emtia & Kripto", '<path d="M3 20h18" stroke="#E8B84A" stroke-width="2.2" stroke-linecap="round"/><path d="M6 17v-6M10 17V7M14 17v-4M18 17V5" stroke="#E8B84A" stroke-width="2.6" stroke-linecap="round"/>',
     ["Keşfet|Emtia & Kripto", "Keşfet|Karşılaştır"]),
    ("Harita", "Keşfet|Teknik", '<path d="M3 3v18h18" fill="none" stroke="#E8B84A" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><path d="M7.5 17v-3M11 17v-7M14.5 17v-5M18 17V7" stroke="#E8B84A" stroke-width="2.4" stroke-linecap="round"/>',
     ["Keşfet|Teknik", "Keşfet|Tarayıcı"]),
    ("Seçki", "Keşfet|Fırsatlar", '<circle cx="12" cy="12" r="9" fill="none" stroke="#E8B84A" stroke-width="2.2"/><circle cx="12" cy="12" r="5" fill="none" stroke="#E8B84A" stroke-width="2.2"/><circle cx="12" cy="12" r="1.8" fill="#E8B84A"/>',
     ["Keşfet|Fırsatlar"]),
    ("BIST", "Keşfet|Hisse", '<path d="M3 9.5 12 4l9 5.5M4.5 20h15M3 22h18" fill="none" stroke="#E8B84A" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/><path d="M6.5 11v7M10.5 11v7M13.5 11v7M17.5 11v7" stroke="#E8B84A" stroke-width="2.2" stroke-linecap="round"/>',
     ["Keşfet|Hisse", "Keşfet|Bebek"]),
    ("Haberler", "Ana Sayfa|Haberler", '<path d="M4 5h13a2 2 0 0 1 2 2v12H6a2 2 0 0 1-2-2z" fill="none" stroke="#E8B84A" stroke-width="2"/><path d="M8 9h7M8 13h7M8 17h4" stroke="#E8B84A" stroke-width="2" stroke-linecap="round"/>',
     ["Ana Sayfa|Haberler"]),
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
    const W=window.parent, P=W.document, OGE=__OGE__, SIMGE=__SIMGE__;
    let st=P.getElementById("kk-nav-stil");
    if(!st){st=P.createElement("style"); st.id="kk-nav-stil"; P.head.appendChild(st);} st.textContent=__STIL__;
    if(!P.getElementById("kk-nav-js8")){
      const sc=P.createElement("script"); sc.id="kk-nav-js8";
      sc.textContent=`
        window.kkSekmeler=function(){return [...document.querySelectorAll('.stTabs [data-testid="stTab"], .stTabs [role="tab"], .stTabs [data-baseweb="tab"]')];};
        window.kkAd=function(t){const p=t.querySelector('[data-testid="stMarkdownContainer"] p')||t; return (p.innerText||p.textContent||"").trim();};
        window.kkGit=function(ad){
          const t=window.kkSekmeler().find(x=>window.kkAd(x).endsWith(ad));
          if(!t) return;
          if(ad==="Ana Sayfa") setTimeout(function(){const p=window.kkSekmeler().find(x=>window.kkAd(x).endsWith("Piyasalar")); if(p) p.click();},120);
          t.scrollIntoView({block:"nearest",inline:"center"});
          t.dispatchEvent(new MouseEvent("mousedown",{bubbles:true})); t.click();
          const k=document.querySelector('[data-testid="stAppScrollToBottomContainer"],[data-testid="stMain"],section.main,[data-testid="stAppViewContainer"]');
          try{(k||window).scrollTo({top:0,behavior:"smooth"});}catch(e){} try{window.scrollTo({top:0,behavior:"smooth"});}catch(e){}
          setTimeout(window.kkIsaretle,80);
        };
        window.kkTeknikGit=function(bolum){
          window.kkGit("Keşfet");
          setTimeout(function(){
            const t=window.kkSekmeler().find(x=>window.kkAd(x).endsWith("Teknik")); if(t) t.click();
            let n=0; const iv=setInterval(function(){ n++;
              const h=[...document.querySelectorAll(bolum==="seviye"?".sv":".vb")].find(x=>x.offsetParent);
              if(h){h.scrollIntoView({behavior:"smooth",block:"start"}); clearInterval(iv);} if(n>90) clearInterval(iv); },700);
          },350);
        };
        window.kkSekmeGit=function(sekme,secici){
          window.kkGit("Keşfet");
          setTimeout(function(){
            const t=window.kkSekmeler().find(x=>window.kkAd(x).endsWith(sekme)); if(t) t.click();
            let n=0; const iv=setInterval(function(){ n++;
              const calisiyor=!!document.querySelector('[data-testid="stStatusWidget"]');
              const hs=[...document.querySelectorAll(secici)].filter(x=>x.offsetParent);
              if(hs.length && !calisiyor){
                hs[0].scrollIntoView({behavior:"smooth",block:"start"}); clearInterval(iv);
                setTimeout(function(){ try{hs[0].scrollIntoView({behavior:"smooth",block:"start"});}catch(e){} },1500);
              } if(n>140) clearInterval(iv); },700);
          },350);
        };
        window.kkIstek=function(deger){
          const inp=document.querySelector(".st-key-kk_gizli input"); if(!inp) return false;
          const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set;
          inp.focus({preventScroll:true}); set.call(inp, deger+Date.now()); inp.dispatchEvent(new Event("input",{bubbles:true}));
          inp.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",code:"Enter",keyCode:13,which:13,bubbles:true}));
          inp.blur(); return true;
        };
        window.kkGitAlt=function(yol){
          const p=yol.split("|"); window.kkGit(p[0]);
          if(p[1]) setTimeout(function(){const t=window.kkSekmeler().find(x=>window.kkAd(x).endsWith(p[1])); if(t){t.click(); setTimeout(window.kkIsaretle,80);}},220);
        };
        if(!window.kkTikDinle2){ window.kkTikDinle2=1;
          document.addEventListener("click",function(e){
            const k=e.target.closest("[data-kapat]");
            if(k){ e.preventDefault(); e.stopPropagation(); try{localStorage.setItem("kk_uyari_kapali",k.dataset.kapat);}catch(x){}
                   if(k.closest("#kk-toast")){ window.kkToastSonraki && window.kkToastSonraki(); return; }
                   const u=k.closest(".kk-uyari"); if(u) u.style.display="none"; return; }
            const g=e.target.closest("[data-git]"); if(g){ e.preventDefault(); e.stopPropagation(); window.kkGitAlt(g.dataset.git);
              if(g.closest("#kk-toast")){ clearTimeout(window.kkToastZ); document.getElementById("kk-toast").classList.remove("acik"); } }
          },true);
        }
        if(!window.kkTikDinle){ window.kkTikDinle=1;
          document.addEventListener("click",function(e){
            const b=e.target.closest("[data-kk]"); if(!b) return; e.preventDefault(); e.stopPropagation();
            const bolum=(b.dataset.kk.split("|")[2]||"");
            if(window.kkIstek(b.dataset.kk)){ if(bolum==="rapor") window.kkSekmeGit("Hisse",".vb"); else window.kkTeknikGit(bolum); }
          },true);
        }
        window.kkBildirim=function(){
          const k=document.querySelector('.kk-bild:not([data-kkb])'); if(!k) return; k.dataset.kkb="1";
          let gor=[]; try{gor=JSON.parse(localStorage.getItem("kk_gorulen")||"[]");}catch(e){}
          const liste=[...k.querySelectorAll('.kk-uyari')].filter(u=>!gor.includes(u.dataset.id)).reverse();   // eskiden yeniye: en yeni en son kalır
          if(!liste.length) return;
          let t=document.getElementById("kk-toast"); if(!t){t=document.createElement("div"); t.id="kk-toast"; document.body.appendChild(t);}
          clearTimeout(window.kkToastZ); let i=0;
          window.kkToastSonraki=function(){
            clearTimeout(window.kkToastZ);
            if(i>=liste.length){ t.classList.remove("acik"); return; }
            const u=liste[i++], sure=+(u.dataset.sure||9000), kalan=liste.length-i;
            const koy=function(){ t.innerHTML=u.outerHTML+(kalan?'<span class="say">+'+kalan+'</span>':''); void t.offsetWidth; t.classList.add("acik");
              gor.push(u.dataset.id); gor=gor.slice(-80); try{localStorage.setItem("kk_gorulen",JSON.stringify(gor));}catch(e){}
              window.kkToastZ=setTimeout(window.kkToastSonraki,sure); };
            if(t.classList.contains("acik")){ t.classList.remove("acik"); setTimeout(koy,420); } else setTimeout(koy,600);
          };
          window.kkToastSonraki();
        };
        window.kkIsaretle=function(){
          try{ window.kkBildirim(); }catch(e){}
          const T0=document.querySelector('[data-testid="stMain"] .stTabs'); if(T0 && !T0.dataset.kkM){T0.dataset.kkM="1"; T0.style.marginTop="-34px";}
          const ilk=document.querySelector('.stTabs [role="tablist"]');
          if(ilk&&!ilk.dataset.kkGizli){ilk.dataset.kkGizli="1"; ilk.style.display="none";
            {let e=ilk; while(e.parentElement && !e.parentElement.querySelector('[role="tabpanel"]')) e=e.parentElement; e.style.display="none";}
            const ust=ilk.parentElement; if(ust) ust.querySelectorAll(':scope > [data-baseweb="tab-border"], :scope > [data-baseweb="tab-highlight"]').forEach(e=>e.style.display="none");}
          // ana sayfanın alt sekme şeridi (Piyasalar/Haberler/Takvim) gizli: kutularla açılır
          document.querySelectorAll('.stTabs [role="tablist"]').forEach(function(tl){
            if(tl.dataset.kkGizli) return;
            const ad=[...tl.querySelectorAll('[role="tab"]')].map(x=>window.kkAd(x));
            if(ad.some(x=>x.endsWith("Piyasalar")) && ad.some(x=>x.endsWith("Takvim"))){ tl.dataset.kkGizli="1"; tl.style.display="none";
              let e=tl; while(e.parentElement && !e.parentElement.querySelector('[role="tabpanel"]')) e=e.parentElement; e.style.display="none";
              const ust=tl.parentElement; if(ust) ust.querySelectorAll(':scope > [data-baseweb="tab-border"], :scope > [data-baseweb="tab-highlight"]').forEach(e=>e.style.display="none"); }
          });
          try{ const kp=localStorage.getItem("kk_uyari_kapali"); if(kp) document.querySelectorAll('.kk-uyari[data-id="'+kp+'"]').forEach(u=>u.style.display="none"); }catch(x){}
          const nav=document.getElementById("kk-nav"); if(!nav) return;
          // seçili sekme yolu: üst sekme + açık paneldeki seçili alt sekme ("Keşfet|Teknik")
          const gorunur=function(t){let e=t; while(e){ if(e.getAttribute && e.getAttribute("role")==="tabpanel" && (e.hidden||e.style.display==="none")) return false; e=e.parentElement;} return true;};
          const sec=window.kkSekmeler().filter(x=>x.getAttribute("aria-selected")==="true" && gorunur(x)).map(window.kkAd);
          const ust=["Ana Sayfa","Keşfet","Portföy","Takip"].find(u=>sec.some(x=>x.endsWith(u)))||"";
          const alt=sec.filter(x=>!["Ana Sayfa","Keşfet","Portföy","Takip"].some(u=>x.endsWith(u)));
          const yol=t=>{const p=t.split("|"); return ust.length && p[0]===ust && alt.some(x=>x.endsWith(p[1]));};
          nav.querySelectorAll("button").forEach(b=>b.classList.toggle("aktif", JSON.parse(b.dataset.es).some(yol)));
        };
        if(!window.kkIsaretZaman) window.kkIsaretZaman=setInterval(window.kkIsaretle,500);`;
      P.head.appendChild(sc);
    }
    const eski=P.getElementById("kk-nav"); if(eski) eski.remove();
    const nav=P.createElement("nav"); nav.id="kk-nav";
    nav.innerHTML=OGE.map(o=>'<button type="button" data-sekme="'+o[1]+'" data-es="'+JSON.stringify(o[3]).replace(/"/g,"&quot;")+'" onclick="window.kkGitAlt(this.dataset.sekme)">'+
      '<svg viewBox="0 0 24 24">'+o[2]+'</svg><span>'+o[0]+'</span></button>').join("");
    P.body.appendChild(nav);
    // sol kenar çekmecesi: alt menüde olmayan bölümler
    ["kk-cek","kk-ckm"].forEach(i=>{const e=P.getElementById(i); if(e) e.remove();});
    const IK={pie:'<path d="M12 3v9h9"/><path d="M20.5 15A9 9 0 1 1 9 3.5"/>',
      perf:'<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>', sanal:'<path d="M7 7h13l-4-4M17 17H4l4 4"/>',
      risk:'<rect x="5" y="3" width="14" height="18" rx="2.5"/><path d="M8.5 7h7M8.5 11h1M12 11h1M15.5 11h0M8.5 14.5h1M12 14.5h1M8.5 18h1M12 18h1M15.5 14.5V18"/>',
      fav:'<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
      alarm:'<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
      tara:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m20 20-4.6-4.6M7.5 10.5h6M10.5 7.5v6"/>',
      kars:'<path d="M12 3v18M5 7h14M5 7l-3 7a3 3 0 0 0 6 0zM19 7l-3 7a3 3 0 0 0 6 0zM8 21h8"/>',
      okul:'<path d="m2 9 10-5 10 5-10 5z"/><path d="M6 11v5c3 2.5 9 2.5 12 0v-5M22 9v6"/>',
      eko:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18"/>',
      tak:'<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
      hab:'<path d="M4 5h13a2 2 0 0 1 2 2v12H6a2 2 0 0 1-2-2z"/><path d="M8 9h7M8 13h7M8 17h4"/>'};
    const CK=[["PORTFÖY",[["Varlıklarım","Portföy|Varlıklarım","pie","Pozisyonlar, dağılım, kâr/zarar"],["Performans","Portföy|Performans","perf","Getiri, risk ve kıyas"],
                          ["Sanal işlem","Portföy|Sanal işlem","sanal","Parasız deneme defteri"],["Risk hesaplayıcı","Portföy|Risk hesaplayıcı","risk","Lot, stop ve risk tutarı"]]],
              ["TAKİP",[["Favoriler","Takip|Favoriler","fav","İzleme listen"],["Alarmlar ve bildirimler","Takip|Alarmlar","alarm","Fiyat, teknik ve iğne uyarıları"]]],
              ["ARAÇLAR",[["Tarayıcı","Keşfet|Tarayıcı","tara","Kurala göre hisse/coin süz"],["Karşılaştır","Keşfet|Karşılaştır","kars","Varlıkları yan yana koy"],
                          ["Yeni başlayanlar","Keşfet|Bebek","okul","Adım adım, sade anlatım"]]],
              ["PİYASA",[["Ekonomi","Ana Sayfa|Ekonomi","eko","Faiz, enflasyon, yabancı akışı"],["Takvim","Ana Sayfa|Takvim","tak","Önemli veri ve bilanço günleri"],
                         ["Haberler","Ana Sayfa|Haberler","hab","Son dakika ve KAP özetleri"]]]];
    const cek=P.createElement("button"); cek.id="kk-cek"; cek.type="button"; cek.setAttribute("aria-label","Menü"); cek.innerHTML="<i></i>";
    const ckm=P.createElement("div"); ckm.id="kk-ckm";
    ckm.innerHTML='<div class="ort"></div><div class="pan"><div class="bas"><img src='+JSON.stringify(SIMGE)+' alt=""><div><b>KATKAY <span>YATIRIM</span></b>'+
      '<i>BIST · ABD · KRİPTO · EMTİA</i></div><span class="kap" role="button" aria-label="Kapat">×</span></div>'+
      CK.map(g=>'<small>'+g[0]+'</small>'+g[1].map(x=>'<a data-yol="'+x[1]+'"><span class="ik"><svg viewBox="0 0 24 24" fill="none" stroke="#E8B84A" '+
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+IK[x[2]]+'</svg></span><span class="yz"><b>'+x[0]+'</b><em>'+x[3]+
        '</em></span><span class="ok">›</span></a>').join("")).join("")+
      '<div class="alt">Veriler bilgilendirme amaçlıdır, yatırım tavsiyesi değildir.</div></div>';
    const isaretle=function(){   // açık bölümü vurgula
      const sec=[...P.querySelectorAll('.stTabs [role="tab"][aria-selected="true"]')].filter(t=>{let e=t; while(e){ if(e.getAttribute&&e.getAttribute("role")==="tabpanel"&&(e.hidden||e.style.display==="none")) return false; e=e.parentElement;} return true;})
        .map(t=>(t.innerText||"").trim());
      ckm.querySelectorAll("a[data-yol]").forEach(a=>{const p=a.dataset.yol.split("|");
        a.classList.toggle("aktif", sec.some(x=>x.endsWith(p[0])) && sec.some(x=>x.endsWith(p[1])));});
    };
    cek.addEventListener("click",()=>{isaretle(); ckm.classList.add("acik");});
    ckm.addEventListener("click",e=>{const a=e.target.closest("a[data-yol]");
      if(a||e.target.closest(".ort")||e.target.closest(".kap")){ ckm.classList.remove("acik"); if(a && W.kkGitAlt) setTimeout(()=>W.kkGitAlt(a.dataset.yol),120); }});
    P.body.appendChild(cek); P.body.appendChild(ckm);
    if(typeof W.kkGit!=="function"){   // ana sayfaya betik eklenemezse (güvenlik politikası) yedek yol
      nav.querySelectorAll("button").forEach(b=>{b.removeAttribute("onclick"); b.addEventListener("click",()=>{
        const t=[...P.querySelectorAll('.stTabs [data-testid="stTab"], .stTabs [role="tab"], .stTabs [data-baseweb="tab"]')].find(x=>x.innerText.trim().endsWith(b.dataset.sekme.split("|")[0])); if(t) t.click();});});
    }
    if(W.kkIsaretle) W.kkIsaretle();
  }catch(e){console.log("kk-nav",e);}
})();
</script>"""


KOMPAKT_STIL = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800;900&display=swap');
*{box-sizing:border-box} body{margin:0;background:transparent;font-family:'Inter',-apple-system,sans-serif;color:#F4F4F5}
.ku{display:flex;align-items:center;justify-content:space-between;padding:8px 4px 10px}
.km{display:flex;align-items:center;gap:10px;min-width:0;flex:1;overflow:hidden}
.km img{width:36px;height:36px;border-radius:11px;border:1px solid rgba(232,184,74,.5);flex:none}
.ka{font-weight:900;font-size:15px;letter-spacing:.1px;white-space:nowrap}.ka span{color:#E8B84A}
.kt{font-size:9.5px;color:#A1A1AA;letter-spacing:1.2px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.km>div{min-width:0}
.ks{display:flex;align-items:center;gap:7px;flex:none;margin-left:8px}
.saat{font-weight:800;font-size:15px;text-align:right;line-height:1.05}.saat small{display:block;font-size:9px;color:#A1A1AA;font-weight:600}
.canli{display:flex;align-items:center;gap:5px;background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.45);color:#4ADE80;
  font-size:10.5px;font-weight:800;border-radius:20px;padding:5px 9px}.canli i{width:7px;height:7px;border-radius:50%;background:#22C55E;box-shadow:0 0 8px #22C55E}
.sd{display:flex;align-items:center;height:36px;background:#17181B;border:1px solid #2A2B30;border-radius:13px;overflow:hidden}
.sd b.e{background:#EF4444;color:#fff;font-size:10.5px;font-weight:900;letter-spacing:1px;padding:0 11px;height:100%;display:flex;align-items:center;flex:none;z-index:2}
.sd .k{overflow:hidden;flex:1;mask-image:linear-gradient(90deg,transparent,#000 4%,#000 96%,transparent)}
.sd .ic{display:inline-flex;gap:26px;white-space:nowrap;padding-left:100%;animation:kay 70s linear infinite;font-size:12.5px;color:#E4E4E7}
.sd .ic em{font-style:normal;color:#E8B84A;font-weight:800;margin-right:6px}
@keyframes kay{to{transform:translateX(-100%)}}
.hap{display:none}
.hk{height:96px;margin:0 -4px -34px;background-size:cover;background-position:center 45%;opacity:.95;
  -webkit-mask-image:linear-gradient(180deg,transparent 0,#000 25%,#000 55%,transparent 100%);mask-image:linear-gradient(180deg,transparent 0,#000 25%,#000 55%,transparent 100%)}
.ku{position:relative;z-index:1}
</style>"""


def ust_kompakt(pv=None, haberler=None):
    """Tasarımdaki kompakt üst kısım: logo + KATKAY + saat + CANLI, altında kayan SON DAKİKA şeridi."""
    import html as _h
    t = dt.datetime.now(ZoneInfo("Europe/Istanbul"))
    gun = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"][t.weekday()]
    ay = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"][t.month - 1]
    kim = {"BIST": "d_bist", "ABD": "d_abd", "Kripto 7/24": "d_kr"}
    dur = "".join(f'<span class="hap" id="{kim[ad]}"><span></span></span>' for ad in kim)
    hab = []
    for x in sorted(haberler or [], key=lambda x: x.get("zaman", ""), reverse=True)[:10]:
        try:
            z = dt.datetime.fromisoformat(x["zaman"]).astimezone(ZoneInfo("Europe/Istanbul"))
            hab.append(f'<span><em>{z:%H:%M}</em>{_h.escape(x["baslik"][:110])}</span>')
        except Exception:
            continue
    if not hab and pv:
        for ad_ in ("BIST 100", "S&P 500", "Bitcoin", "Ons altın", "USD/TRY"):
            v = pv.get(ad_)
            if v: hab.append(f'<span><em>{ad_}</em>{v["deger"]:,.2f} ({(v.get("d1G") or 0) * 100:+.2f}%)</span>'.replace(",", "X").replace(".", ",").replace("X", "."))
    logo = f'<img src="{_logo_url()}" alt="KATKAY">' if _logo_url() else ""
    hero = _hero_url()
    return ((f'<div class="hk" style="background-image:url({hero})"></div>' if hero else '') +
            f'<div class="ku"><div class="km">{logo}<div><div class="ka">KATKAY <span>YATIRIM</span></div>'
            f'<div class="kt">BIST · ABD · KRİPTO · EMTİA</div></div></div>'
            f'<div class="ks"><div class="saat" id="saat">{t:%H:%M}<small id="tarih">{t.day} {ay} {gun} · TSİ</small></div>'
            f'<span class="canli"><i></i>CANLI</span></div></div>'
            f'<div class="sd" onclick="try{{window.parent.kkGitAlt(\'Ana Sayfa|Haberler\')}}catch(e){{}}" style="cursor:pointer"><b class="e">SON DAKİKA</b><div class="k"><div class="ic">{"".join(hab) or "<span>Haber akışı yükleniyor…</span>"}</div></div></div>{dur}')


def ust_kompakt_sayfa(pv=None, haberler=None):
    import json
    js = (CANLI_JS.replace("__OGE__", json.dumps(NAV_OGE)).replace("__STIL__", json.dumps(NAV_STIL))
          .replace("__SIMGE__", json.dumps(SIMGE_URL)))
    return "<!DOCTYPE html><html><head><meta charset='utf-8'>" + KOMPAKT_STIL + "</head><body>" + ust_kompakt(pv, haberler) + js + "</body></html>"


def ust_bant_sayfa(pv=None):
    import json
    js = (CANLI_JS.replace("__OGE__", json.dumps(NAV_OGE)).replace("__STIL__", json.dumps(NAV_STIL))
          .replace("__SIMGE__", json.dumps(SIMGE_URL)))
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'>" + BANT_STIL + "</head><body>" + ust_bant(pv) + js + "</body></html>")


def bb(baslik):
    return f'<div class="bb">{baslik.upper()}</div>'


def bolum(baslik, ikon="public"):
    ik = {"public": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8"><circle cx="12" cy="12" r="9"/>'
                    '<path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18"/></svg>'}.get(ikon, "")
    return f'<div class="bolum"><span class="ik">{ik}</span>{baslik}</div>'
