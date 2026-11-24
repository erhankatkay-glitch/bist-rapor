"""Uygulama görsel kimliği: koyu 'işlem terminali' teması, üst bant ve kayan fiyat şeridi.
Telegram kartlarıyla aynı palet (lacivert zemin, altın vurgu, yeşil/kırmızı yön)."""
import datetime as dt
from zoneinfo import ZoneInfo

STIL = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
:root {--zemin:#070C18; --panel:#0F1729; --panel2:#131D33; --cizgi:rgba(148,163,184,.14); --yazi:#E2E8F0; --soluk:#8A9BB5;
       --altin:#F59E0B; --turuncu:#F97316; --yesil:#22C55E; --kirmizi:#EF4444; --mavi:#38BDF8;}
html, body, .stApp, .stMarkdown, button, input, textarea, select, [data-testid="stWidgetLabel"] {font-family:'Inter',-apple-system,sans-serif !important;}
.stApp {background:
   radial-gradient(900px 480px at -10% -8%, rgba(56,189,248,.10), transparent 60%),
   radial-gradient(800px 460px at 115% -4%, rgba(245,158,11,.10), transparent 55%), var(--zemin) !important;}
#MainMenu, footer, header[data-testid="stHeader"] {visibility:hidden; height:0;}
.block-container {padding-top:.7rem; padding-bottom:3rem; max-width:720px;}
h1, h2, h3 {color:#F8FAFC !important; font-weight:800 !important; letter-spacing:-.015em;}
h3 {font-size:1.25rem !important;}
[data-testid="stCaptionContainer"], .stCaption {color:var(--soluk) !important;}
hr {border:none !important; height:1px !important; background:linear-gradient(90deg, transparent, rgba(148,163,184,.35), transparent) !important;}
[data-testid="stMarkdownContainer"] p, li {font-variant-numeric: tabular-nums;}

/* ---------- Üst bant ---------- */
.ub {position:relative; overflow:hidden; border-radius:20px; padding:14px 16px 0; margin-bottom:12px;
     background:linear-gradient(140deg, #0F1A33 0%, #0A1226 55%, #111C36 100%); border:1px solid var(--cizgi);
     box-shadow:0 18px 40px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.04);}
.ub:before {content:""; position:absolute; inset:0; background:
     radial-gradient(420px 160px at 100% 0%, rgba(245,158,11,.16), transparent 70%),
     radial-gradient(300px 140px at 0% 100%, rgba(56,189,248,.10), transparent 70%); pointer-events:none;}
.ub-ust {display:flex; justify-content:space-between; align-items:center; position:relative;}
.ub-marka {display:flex; align-items:center; gap:10px;}
.ub-logo {width:38px; height:38px; border-radius:11px; display:flex; align-items:center; justify-content:center;
          background:linear-gradient(135deg, #F59E0B, #F97316); box-shadow:0 6px 16px rgba(245,158,11,.35);}
.ub-ad {color:#F8FAFC; font-weight:900; font-size:1.06rem; letter-spacing:-.01em; line-height:1.1;}
.ub-ad span {color:var(--altin);}
.ub-alt {color:var(--soluk); font-size:.7rem; font-weight:600; letter-spacing:.04em; margin-top:2px;}
.ub-saat {text-align:right; color:#F8FAFC; font-weight:800; font-size:.95rem; font-variant-numeric:tabular-nums;}
.ub-saat small {display:block; color:var(--soluk); font-weight:600; font-size:.62rem; letter-spacing:.08em;}
.ub-durum {display:flex; gap:6px; flex-wrap:wrap; margin:12px 0 10px; position:relative;}
.ub-p {font-size:.66rem; font-weight:700; letter-spacing:.03em; padding:4px 9px; border-radius:999px; color:#CBD5E1;
       background:rgba(255,255,255,.04); border:1px solid var(--cizgi); display:inline-flex; align-items:center; gap:6px;}
.ub-p i {width:7px; height:7px; border-radius:50%; background:#64748B; display:inline-block;}
.ub-p.acik i {background:var(--yesil); box-shadow:0 0 0 3px rgba(34,197,94,.18); animation:nabiz 1.8s infinite;}
.ub-p.acik {color:#BBF7D0; border-color:rgba(34,197,94,.30);}
@keyframes nabiz {0%,100% {box-shadow:0 0 0 2px rgba(34,197,94,.25);} 50% {box-shadow:0 0 0 5px rgba(34,197,94,.05);}}
.serit {position:relative; margin:0 -16px; border-top:1px solid var(--cizgi); background:rgba(3,7,18,.45); overflow:hidden;
        -webkit-mask-image:linear-gradient(90deg, transparent, #000 6%, #000 94%, transparent);}
.serit-ic {display:inline-flex; white-space:nowrap; padding:9px 0; animation:kay 55s linear infinite;}
.serit:hover .serit-ic {animation-play-state:paused;}
@keyframes kay {from {transform:translateX(0);} to {transform:translateX(-50%);}}
.si {display:inline-flex; align-items:baseline; gap:7px; padding:0 16px; border-right:1px solid rgba(148,163,184,.10); font-variant-numeric:tabular-nums;}
.si b {color:#94A3B8; font-size:.68rem; font-weight:700; letter-spacing:.05em;}
.si em {font-style:normal; color:#F8FAFC; font-weight:700; font-size:.82rem;}
.si u {text-decoration:none; font-weight:800; font-size:.74rem;}
.y {color:var(--yesil) !important;} .k {color:var(--kirmizi) !important;} .n {color:#94A3B8 !important;}

/* ---------- Sekmeler ---------- */
.stTabs [data-baseweb="tab-list"] {gap:6px; overflow-x:auto; flex-wrap:nowrap; scrollbar-width:none; padding:2px 2px 8px; background:transparent;}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {display:none;}
.stTabs [data-baseweb="tab"] {background:rgba(255,255,255,.035); border:1px solid var(--cizgi); border-radius:999px;
       padding:8px 14px !important; margin:0 !important; height:auto !important; white-space:nowrap; transition:all .15s ease;}
.stTabs [data-baseweb="tab"] p {font-weight:650; font-size:.84rem; color:#A8B6CC; margin:0;}
.stTabs [data-baseweb="tab"]:hover {border-color:rgba(245,158,11,.45);}
.stTabs [aria-selected="true"] {background:linear-gradient(135deg, #F59E0B, #F97316) !important; border-color:transparent !important;
       box-shadow:0 6px 18px rgba(245,158,11,.28);}
.stTabs [aria-selected="true"] p, .stTabs [aria-selected="true"] span {color:#0B1220 !important; font-weight:800;}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {display:none;}
.stTabs [data-baseweb="tab-panel"] {padding-top:10px;}
/* iç sekmeler (alt başlıklar) daha sade: alt çizgili */
.stTabs .stTabs [data-baseweb="tab"] {background:transparent; border:none; border-radius:0; padding:6px 10px !important;}
.stTabs .stTabs [aria-selected="true"] {background:transparent !important; box-shadow:inset 0 -2px 0 var(--altin);}
.stTabs .stTabs [aria-selected="true"] p {color:var(--altin) !important;}

/* ---------- Butonlar ---------- */
div.stButton > button, div.stDownloadButton > button, div.stLinkButton > a, div.stFormSubmitButton > button {
       width:100%; min-height:3rem; border-radius:14px; font-weight:700; font-size:.96rem;
       background:var(--panel2); color:var(--yazi); border:1px solid var(--cizgi); transition:all .15s ease;}
div.stButton > button:hover, div.stDownloadButton > button:hover {border-color:rgba(245,158,11,.55); color:#FDE68A;}
div.stButton > button[kind="primary"], div.stDownloadButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] {
       background:linear-gradient(135deg, #F59E0B 0%, #F97316 100%) !important; border:none !important;
       box-shadow:0 10px 24px rgba(245,158,11,.28), inset 0 1px 0 rgba(255,255,255,.25);}
div.stButton > button[kind="primary"] *, div.stDownloadButton > button[kind="primary"] *, div.stFormSubmitButton > button[kind="primary"] * {
       color:#0B1220 !important; font-weight:800 !important;}
div.stButton > button[kind="primary"]:hover {filter:brightness(1.06); transform:translateY(-1px);}
div.stButton > button:disabled {opacity:.45;}

/* ---------- Seçim kutuları, giriş alanları ---------- */
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="textarea"], .stNumberInput input {
       background:var(--panel) !important; border-color:var(--cizgi) !important; border-radius:12px !important;}
[data-baseweb="select"] > div:focus-within, [data-baseweb="input"]:focus-within {border-color:var(--altin) !important; box-shadow:0 0 0 3px rgba(245,158,11,.15);}
[data-testid="stWidgetLabel"] p {color:#A8B6CC !important; font-weight:650; font-size:.8rem !important; letter-spacing:.02em;}

/* radyo düğmeleri → bölmeli seçici */
div[role="radiogroup"] {gap:4px !important; background:var(--panel); border:1px solid var(--cizgi); border-radius:14px; padding:4px; flex-wrap:wrap;}
div[role="radiogroup"] > label {margin:0 !important; padding:7px 14px; border-radius:10px; flex:1 1 auto; justify-content:center; transition:all .15s ease;}
div[role="radiogroup"] > label > div:first-child {display:none !important;}
div[role="radiogroup"] > label p {font-weight:700; font-size:.86rem; color:#A8B6CC;}
div[role="radiogroup"] > label:has(input:checked) {background:linear-gradient(135deg, rgba(245,158,11,.22), rgba(249,115,22,.16));
       box-shadow:inset 0 0 0 1px rgba(245,158,11,.55);}
div[role="radiogroup"] > label:has(input:checked) p {color:#FDE68A !important;}

/* ---------- Açılır bölmeler, tablolar, uyarılar ---------- */
[data-testid="stExpander"] details {background:linear-gradient(180deg, var(--panel2), var(--panel)); border:1px solid var(--cizgi) !important;
       border-radius:16px !important; overflow:hidden;}
[data-testid="stExpander"] summary {padding:12px 14px;}
[data-testid="stExpander"] summary p {font-weight:700; color:#F1F5F9;}
[data-testid="stExpander"] summary:hover p {color:#FDE68A;}
[data-testid="stDataFrame"], [data-testid="stTable"] {border:1px solid var(--cizgi); border-radius:14px; overflow:hidden;}
[data-testid="stAlert"] {border-radius:14px; border:1px solid var(--cizgi);}
[data-testid="stImage"] img {border-radius:16px; box-shadow:0 14px 34px rgba(0,0,0,.45);}
[data-testid="stMetric"] {background:var(--panel); border:1px solid var(--cizgi); border-radius:14px; padding:10px 12px;}
[data-testid="stMetricValue"] {font-weight:800;}
[data-testid="stVerticalBlockBorderWrapper"] > div[style*="border"] {border-color:var(--cizgi) !important; border-radius:16px !important;}
.stProgress > div > div > div > div {background:linear-gradient(90deg, #F59E0B, #F97316);}

/* ---------- Bilgi kartları ---------- */
.kart {position:relative; background:linear-gradient(180deg, #131D33 0%, #0F1729 100%); border:1px solid var(--cizgi);
       border-radius:16px; padding:12px 14px 11px 16px; margin-bottom:10px; overflow:hidden;
       box-shadow:0 10px 26px rgba(0,0,0,.30), inset 0 1px 0 rgba(255,255,255,.03);}
.kart:before {content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--v, #F59E0B);
       box-shadow:0 0 14px var(--v, #F59E0B);}
.kart .e {font-size:.64rem; color:var(--soluk); font-weight:800; letter-spacing:.09em; text-transform:uppercase;}
.kart .d {font-size:1.34rem; font-weight:850; letter-spacing:-.015em; margin:3px 0 1px; font-variant-numeric:tabular-nums;}
.kart .a {font-size:.74rem; color:var(--soluk);}
.pk {background:linear-gradient(180deg, #131D33 0%, #0F1729 100%); border:1px solid var(--cizgi); border-radius:16px;
     padding:11px 12px 9px; margin-bottom:10px; box-shadow:0 10px 26px rgba(0,0,0,.28); transition:border-color .15s ease;}
.pk:hover {border-color:rgba(245,158,11,.40);}
.bolum {display:flex; align-items:center; gap:8px; margin:14px 0 8px; color:#F8FAFC; font-weight:800; font-size:1.02rem;}
.bolum:before {content:""; width:4px; height:18px; border-radius:3px; background:linear-gradient(180deg, #F59E0B, #F97316);}
.alt-not {color:var(--soluk); font-size:.72rem; text-align:center; margin-top:18px; line-height:1.5;}
</style>"""

LOGO = ('<svg width="22" height="22" viewBox="0 0 24 24" fill="none">'
        '<rect x="3" y="9" width="3.4" height="9" rx="1" fill="#0B1220"/><path d="M4.7 6v3M4.7 18v2.5" stroke="#0B1220" stroke-width="1.6" stroke-linecap="round"/>'
        '<rect x="10.3" y="5" width="3.4" height="10" rx="1" fill="#0B1220"/><path d="M12 2.5V5M12 15v3" stroke="#0B1220" stroke-width="1.6" stroke-linecap="round"/>'
        '<rect x="17.6" y="7.5" width="3.4" height="7" rx="1" fill="#0B1220" fill-opacity=".55"/><path d="M19.3 4.5v3M19.3 14.5v4" stroke="#0B1220" stroke-width="1.6" stroke-linecap="round" stroke-opacity=".55"/></svg>')

SERIT = ["BIST 100", "USD/TRY", "Gram altın", "Ons altın", "Bitcoin", "S&P 500", "Nasdaq", "Brent", "Gümüş", "EUR/TRY", "Ethereum", "Dolar endeksi", "VIX"]


def piyasa_durumu(simdi=None):
    """BIST / ABD / Kripto açık mı (tatiller hariç basit seans kontrolü)."""
    t = simdi or dt.datetime.now(ZoneInfo("Europe/Istanbul"))
    e = t.astimezone(ZoneInfo("America/New_York"))
    hi = t.weekday() < 5
    bist = hi and dt.time(10, 0) <= t.time() < dt.time(18, 10)
    abd = e.weekday() < 5 and dt.time(9, 30) <= e.time() < dt.time(16, 0)
    return {"BIST": bist, "ABD": abd, "Kripto 7/24": True}


def _sayi(x, nd=2):
    s = f"{x:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def ust_bant(pv=None):
    t = dt.datetime.now(ZoneInfo("Europe/Istanbul"))
    gun = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"][t.weekday()]
    ay = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"][t.month - 1]
    dur = "".join(f'<span class="ub-p{" acik" if a else ""}"><i></i>{ad} · {"Açık" if a else "Kapalı"}</span>'
                  for ad, a in piyasa_durumu(t).items())
    serit = ""
    if pv:
        ogeler = []
        for ad in SERIT:
            v = pv.get(ad)
            if not v: continue
            d = v.get("d1G") or 0
            c = "y" if d > 0 else "k" if d < 0 else "n"
            ok = "▲" if d > 0 else "▼" if d < 0 else "•"
            nd = 0 if v["deger"] >= 10000 else 2 if v["deger"] >= 1 else 4
            ogeler.append(f'<span class="si"><b>{ad.upper()}</b><em>{_sayi(v["deger"], nd)}</em>'
                          f'<u class="{c}">{ok} %{_sayi(abs(d) * 100, 2)}</u></span>')
        if ogeler:
            ic = "".join(ogeler)
            serit = f'<div class="serit"><div class="serit-ic">{ic}{ic}</div></div>'
    return (f'<div class="ub"><div class="ub-ust"><div class="ub-marka"><div class="ub-logo">{LOGO}</div>'
            f'<div><div class="ub-ad">Piyasa <span>Merkezi</span></div>'
            f'<div class="ub-alt">BIST · ABD · KRİPTO · EMTİA</div></div></div>'
            f'<div class="ub-saat">{t:%H:%M}<small>{t.day} {ay} {gun} · TSİ</small></div></div>'
            f'<div class="ub-durum">{dur}</div>{serit}</div>')


def bolum(baslik):
    return f'<div class="bolum">{baslik}</div>'


SAAT_JS = """
<script>
(function(){
  const gunler=["Paz","Pzt","Sal","Çar","Per","Cum","Cmt"], aylar=["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"];
  function parca(tz){
    const f=new Intl.DateTimeFormat("en-GB",{timeZone:tz,year:"numeric",month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit",hour12:false,weekday:"short"});
    const o={}; f.formatToParts(new Date()).forEach(p=>o[p.type]=p.value);
    const wd={"Sun":0,"Mon":1,"Tue":2,"Wed":3,"Thu":4,"Fri":5,"Sat":6}[o.weekday];
    return {g:+o.day,a:+o.month,s:+o.hour%24,d:+o.minute,wd:wd};
  }
  function durum(id,acik){
    const e=document.getElementById(id); if(!e) return;
    e.className="ub-p"+(acik?" acik":""); e.querySelector("span").textContent=acik?"Açık":"Kapalı";
  }
  function guncelle(){
    const t=parca("Europe/Istanbul"), n=parca("America/New_York");
    const dk=t.s*60+t.d, ndk=n.s*60+n.d;
    document.getElementById("saat").firstChild.nodeValue=String(t.s).padStart(2,"0")+":"+String(t.d).padStart(2,"0");
    document.getElementById("tarih").textContent=t.g+" "+aylar[t.a-1]+" "+gunler[t.wd]+" · TSİ";
    durum("d_bist", t.wd>=1&&t.wd<=5 && dk>=600 && dk<1090);
    durum("d_abd", n.wd>=1&&n.wd<=5 && ndk>=570 && ndk<960);
  }
  guncelle(); setInterval(guncelle,10000);
})();
</script>"""


def ust_bant_sayfa(pv=None):
    """Canlı saatli üst bant (iframe içinde çalışır; saat ve piyasa durumu telefonun saatine göre her 10 sn güncellenir)."""
    h = ust_bant(pv)
    h = h.replace('<div class="ub-saat">', '<div class="ub-saat" id="saat">', 1)
    h = h.replace("<small>", '<small id="tarih">', 1)
    # piyasa durum hapları: kimlikli ve güncellenebilir
    import re
    for ad, kim in (("BIST", "d_bist"), ("ABD", "d_abd")):
        h = re.sub(rf'<span class="ub-p( acik)?"><i></i>{ad} · (Açık|Kapalı)</span>',
                   lambda m: f'<span class="ub-p{m.group(1) or ""}" id="{kim}"><i></i>{ad} · <span>{m.group(2)}</span></span>', h)
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'>" + STIL +
            "<style>html,body{margin:0;padding:0;background:transparent!important;overflow:hidden}.ub{margin:2px 2px 6px}.ub-p span{margin-left:-3px}</style>"
            "</head><body>" + h + SAAT_JS + "</body></html>")
