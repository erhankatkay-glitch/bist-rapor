# -*- coding: utf-8 -*-
"""Sessiz Telegram gönderimi ve otomatik silme.

- Tüm mesajlar bildirim sesi olmadan (disable_notification) gönderilir.
- Her gönderilen mesajın kimliği, bir 'anahtar' (ör. firsat:kripto:4S) ve silinme zamanıyla defterde tutulur.
- Aynı anahtarla yeni mesaj gelince eskisi hemen silinir (yeni mesaj hâlâ açık kurulumları da içerir).
- Bağlı kurulumların hepsi kapanınca mesaj 1 saat sonra silinir.
- Telegram, botun kendi mesajlarını yalnızca 48 saat içinde silmesine izin verir: hiçbir mesaj 46,5 saatten uzun tutulmaz.

Defter dosyaları bulten dalında durum/tg_<kaynak>.json; her iş akışı yalnızca kendi defterini yazar.
Zamanı gelenleri silme işini 30 dakikada bir çalışan alarm iş akışı yapar (`python tg.py temizle`) ve
sildiklerini durum/tg_silinen.json'a yazar; diğer iş akışları açılışta bu listeyi okuyup defterlerinden düşer.

Ortam değişkenleri: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DURUM_KLON (bulten dalı kopyası), DURUM_CIKTI (çıktı klasörü)."""
import os, sys, json, glob, re, time, datetime as dt

MAKS_SAAT = 46.5
NOT = "⚠️ <b><i>Gösterge bazlı analizdir, yatırım tavsiyesi değildir.</i></b>"
KLON = os.environ.get("DURUM_KLON", "onceki")
CIKTI = os.environ.get("DURUM_CIKTI", "cikti")
UTC = dt.timezone.utc


def buyuk(s):
    """Türkçe büyük harf: i→İ, ı→I."""
    return str(s).replace("i", "İ").replace("ı", "I").upper()


AYRAC = "━━━━━━━━━━━━━━━━"
UYG = "https://erhankatkay-glitch.github.io/bist-rapor/"
# mesaj anahtarının başı → hızlı uygulamada açılacak bölüm (her mesajın altında "Uygulamada aç" düğmesi)
UYG_BOLUM = {"firsat": "firsat", "rejim": "piyasa", "dunya": "piyasa", "korelasyon": "piyasa", "opsiyon": "piyasa", "yabanci": "piyasa",
             "takvim": "piyasa", "haber": "haber", "sabah": "ozet", "alarm": "bildirim", "igne": "bildirim", "bulten": "piyasa",
             "teknik": "piyasa", "durum": "ozet", "portfoy": "portfoy", "pf": "portfoy", "takip": "firsat"}


def uygulama_dugme(anahtar="", kod=None, metin=None):
    """Telegram satır içi düğmesi: varlık verilirse hızlı uygulamada o varlığın sayfası, yoksa mesaj türüne uygun bölüm."""
    import urllib.parse as _u
    if kod:
        return {"inline_keyboard": [[{"text": metin or f"📲 {kod} analizini aç", "url": UYG + "#v/" + _u.quote(str(kod), safe="")}]]}
    bas = re.split(r"[:_]", str(anahtar or ""))[0]
    bolum = UYG_BOLUM.get(bas, "ozet")
    return {"inline_keyboard": [[{"text": metin or "📲 KATKAY uygulamasında aç", "url": UYG + "#" + bolum}]]}


def simdi():
    return dt.datetime.now(UTC)


def _oku(yol, vars_=None):
    try:
        with open(yol, encoding="utf-8") as f: return json.load(f)
    except Exception:
        return vars_


def _yaz(yol, veri):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f: json.dump(veri, f, ensure_ascii=False, indent=0)


def silinenler():
    s = _oku(os.path.join(CIKTI, "durum", "tg_silinen.json")) or _oku(os.path.join(KLON, "durum", "tg_silinen.json"), {})
    return s or {}


def _parcala(metin, sinir=3900):
    """Telegram 4096 karakter sınırı: blok (boş satır) sınırlarından böl."""
    if len(metin) <= sinir: return [metin]
    out, cur = [], ""
    for blok in metin.split("\n\n"):
        if len(cur) + len(blok) + 2 > sinir and cur:
            out.append(cur); cur = blok
        else:
            cur = (cur + "\n\n" + blok) if cur else blok
        while len(cur) > sinir:
            out.append(cur[:sinir]); cur = cur[sinir:]
    if cur: out.append(cur)
    return out


def guvenli_aciklama(s, limit=1000):
    """Görsel açıklaması: Telegram sınırına (1024) satır sonundan kesilir, açık kalan HTML etiketleri kapatılır.
    (Ortadan kesilen etiket 'can't parse entities' hatasıyla kartın hiç gitmemesine yol açıyordu.)"""
    s = str(s or "")
    if len(s) > limit:
        kes = s.rfind("\n", 0, limit - 20)
        s = (s[:kes] if kes > 0 else s[:limit - 20]).rstrip() + "\n…"
    s = re.sub(r"<[^>]*$", "", s); s = re.sub(r"&[a-z]{0,5}$", "", s)   # yarım kalmış etiket / varlık
    acik = []
    for m in re.finditer(r"<(/?)([a-z]+)[^>]*>", s):
        kapa, ad = m.group(1), m.group(2)
        if kapa:
            if ad in acik: acik.remove(ad) if acik[-1] != ad else acik.pop()
        elif ad not in ("br",):
            acik.append(ad)
    return s + "".join(f"</{a}>" for a in reversed(acik))


class Bot:
    def __init__(self, kaynak):
        self.kaynak = kaynak
        self.tok, self.chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
        self.aktif = bool(self.tok and self.chat)
        sil = silinenler()
        # aynı iş içinde daha önce yazılmış defter (ör. alarm → temizlik) varsa o esas alınır
        d0 = _oku(os.path.join(CIKTI, "durum", f"tg_{kaynak}.json"))
        if d0 is None: d0 = _oku(os.path.join(KLON, "durum", f"tg_{kaynak}.json"), [])
        self.defter = [d for d in (d0 or []) if str(d["id"]) not in sil]
        self.gonderilen = 0

    # ---------------------------------------------------------------- düşük seviye
    def _api(self, yontem, data=None, files=None, timeout=60):
        import requests
        for deneme in range(3):
            try:
                r = requests.post(f"https://api.telegram.org/bot{self.tok}/{yontem}", data=data, files=files, timeout=timeout)
                j = r.json()
                if r.status_code == 429:
                    time.sleep(int(j.get("parameters", {}).get("retry_after", 3)) + 1); continue
                return j
            except Exception as ex:
                if deneme == 2: return {"ok": False, "description": str(ex)}
                time.sleep(2)
        return {"ok": False}

    def _kaydet(self, ids, anahtar, omur_saat, bag):
        t = simdi(); omur = min(omur_saat, MAKS_SAAT)
        for i in ids:
            self.defter.append({"id": i, "anahtar": anahtar, "gonderim": t.isoformat(),
                                "sil": (t + dt.timedelta(hours=omur)).isoformat(), "bag": list(bag or [])})

    # ---------------------------------------------------------------- gönderim
    def mesaj(self, metin, anahtar, omur_saat, bag=None, yerine=True, notlu=True, dugme=None):
        """HTML metin; gerekirse birden çok parçaya bölünür. yerine=True: aynı anahtarlı eski mesajlar silinir.
        notlu=True: sona uyarı notu eklenir."""
        if notlu: metin = metin.rstrip() + "\n\n" + NOT
        if not self.aktif:
            print(f"[Telegram kapalı] {anahtar}:\n{re.sub('<[^>]+>', '', metin)[:1500]}\n"); return []
        ids = []
        parcalar = _parcala(metin)
        for i_, parca in enumerate(parcalar):
            veri = {"chat_id": self.chat, "text": parca, "parse_mode": "HTML", "disable_notification": True, "disable_web_page_preview": True}
            if i_ == len(parcalar) - 1: veri["reply_markup"] = json.dumps(dugme or uygulama_dugme(anahtar), ensure_ascii=False)
            j = self._api("sendMessage", veri)
            if not j.get("ok") and "reply_markup" in veri:   # düğme reddedildiyse düğmesiz dene
                veri.pop("reply_markup"); j = self._api("sendMessage", veri)
            if not j.get("ok"):   # HTML hatasında düz metin dene
                j = self._api("sendMessage", {"chat_id": self.chat, "text": re.sub("<[^>]+>", "", parca), "disable_notification": True})
            if j.get("ok"): ids.append(j["result"]["message_id"])
            else: print("Telegram mesajı gönderilemedi:", j.get("description"), file=sys.stderr)
        self._sonrasi(ids, anahtar, omur_saat, bag, yerine)
        return ids

    def album(self, dosyalar, anahtar, omur_saat, bag=None, yerine=False, dugme=None):
        dosyalar = [(y, guvenli_aciklama(b)) for y, b in dosyalar]
        return self._album(dosyalar, anahtar, omur_saat, bag, yerine, dugme)

    def _album(self, dosyalar, anahtar, omur_saat, bag=None, yerine=False, dugme=None):
        """dosyalar: [(yol, başlık)] — en fazla 10 görsel tek albümde."""
        if not self.aktif or not dosyalar: return []
        ids = []
        for i0 in range(0, len(dosyalar), 10):
            grup = dosyalar[i0:i0 + 10]; files, medya = {}, []
            try:
                for i, (yol, bas) in enumerate(grup):
                    files[f"f{i}"] = open(yol, "rb")
                    medya.append({"type": "photo", "media": f"attach://f{i}", "caption": bas[:1000], "parse_mode": "HTML"})
                if len(medya) == 1:
                    rm = json.dumps(dugme or uygulama_dugme(anahtar), ensure_ascii=False)
                    j = self._api("sendPhoto", {"chat_id": self.chat, "caption": medya[0]["caption"], "parse_mode": "HTML", "disable_notification": True,
                                                "reply_markup": rm}, files={"photo": files["f0"]}, timeout=120)
                    if not j.get("ok") and "parse" not in str(j.get("description", "")).lower():
                        files["f0"].seek(0)   # düğme reddedildiyse düğmesiz gönder (kart her durumda gitsin)
                        j = self._api("sendPhoto", {"chat_id": self.chat, "caption": medya[0]["caption"], "parse_mode": "HTML", "disable_notification": True},
                                      files={"photo": files["f0"]}, timeout=120)
                    if not j.get("ok") and "parse" in str(j.get("description", "")).lower():   # HTML hatası: düz metinle tekrar
                        files["f0"].seek(0)
                        j = self._api("sendPhoto", {"chat_id": self.chat, "caption": re.sub("<[^>]+>", "", medya[0]["caption"]),
                                                    "disable_notification": True, "reply_markup": rm}, files={"photo": files["f0"]}, timeout=120)
                    if j.get("ok"): ids.append(j["result"]["message_id"])
                else:
                    j = self._api("sendMediaGroup", {"chat_id": self.chat, "media": json.dumps(medya, ensure_ascii=False),
                                                     "disable_notification": True}, files=files, timeout=180)
                    if j.get("ok"): ids += [m["message_id"] for m in j["result"]]
                if not j.get("ok"): print("Telegram albümü gönderilemedi:", j.get("description"), file=sys.stderr)
            finally:
                for f in files.values(): f.close()
        self._sonrasi(ids, anahtar, omur_saat, bag, yerine)
        return ids

    def foto(self, yol, baslik, anahtar, omur_saat, bag=None, dugme=None):
        """Tek görsel + HTML açıklama (her kart ayrı mesaj: açıklaması sohbette görünür) + 'uygulamada aç' düğmesi."""
        return self.album([(yol, baslik)], anahtar, omur_saat, bag=bag, yerine=False, dugme=dugme)

    def belge(self, yol, ad, baslik, anahtar, omur_saat, yerine=False):
        if not self.aktif: return []
        with open(yol, "rb") as f:
            j = self._api("sendDocument", {"chat_id": self.chat, "caption": re.sub("<[^>]+>", "", baslik)[:1000], "disable_notification": True},
                          files={"document": (ad, f)}, timeout=180)
        ids = [j["result"]["message_id"]] if j.get("ok") else []
        if not ids: print("Telegram belgesi gönderilemedi:", j.get("description"), file=sys.stderr)
        self._sonrasi(ids, anahtar, omur_saat, None, yerine)
        return ids

    def _sonrasi(self, ids, anahtar, omur_saat, bag, yerine):
        if not ids: return
        if yerine: self.sil_anahtar(anahtar, haric=set(ids))
        self._kaydet(ids, anahtar, omur_saat, bag); self.gonderilen += len(ids)

    # ---------------------------------------------------------------- silme
    def _sil(self, ids):
        """Silinen (ya da artık silinemeyen) kimlikleri döndürür."""
        ids = [int(i) for i in ids]
        if not ids or not self.aktif: return set()
        bitti = set()
        for i0 in range(0, len(ids), 100):
            grup = ids[i0:i0 + 100]
            j = self._api("deleteMessages", {"chat_id": self.chat, "message_ids": json.dumps(grup)})
            if j.get("ok"): bitti |= set(grup); continue
            for i in grup:   # tek tek dene; bulunamayan/silinemeyen de defterden düşer
                j = self._api("deleteMessage", {"chat_id": self.chat, "message_id": i})
                if j.get("ok") or "not found" in str(j.get("description", "")) or "can't be deleted" in str(j.get("description", "")):
                    bitti.add(i)
        return bitti

    def sil_anahtar(self, anahtar, haric=()):
        hedef = [d["id"] for d in self.defter if d["anahtar"] == anahtar and d["id"] not in haric]
        bitti = self._sil(hedef)
        self.defter = [d for d in self.defter if d["id"] not in bitti]

    def bag_guncelle(self, acik_idler):
        """Bağlı tüm kurulumları kapanmış mesajların ömrünü 1 saate indirir."""
        acik = set(acik_idler); t = simdi() + dt.timedelta(hours=1)
        for d in self.defter:
            if d.get("bag") and not (set(d["bag"]) & acik) and dt.datetime.fromisoformat(d["sil"]) > t:
                d["sil"] = t.isoformat()

    def zamani_gelenleri_sil(self):
        t = simdi()
        hedef = [d["id"] for d in self.defter if dt.datetime.fromisoformat(d["sil"]) <= t
                 or t - dt.datetime.fromisoformat(d["gonderim"]) >= dt.timedelta(hours=MAKS_SAAT)]
        bitti = self._sil(hedef)
        self.defter = [d for d in self.defter if d["id"] not in bitti]
        return len(bitti)

    def kaydet(self):
        # 48 saati geçmiş kayıtlar zaten silinemez; defterden düşür
        t = simdi()
        self.defter = [d for d in self.defter if t - dt.datetime.fromisoformat(d["gonderim"]) < dt.timedelta(hours=48)]
        _yaz(os.path.join(CIKTI, "durum", f"tg_{self.kaynak}.json"), self.defter)


def temizle():
    """Tüm defterlerde zamanı gelen mesajları siler (alarm iş akışı, 30 dakikada bir)."""
    b = Bot("alarm")
    if not b.aktif:
        print("Telegram ayarlı değil; temizlik atlandı."); return
    n = b.zamani_gelenleri_sil(); b.kaydet()
    sil = silinenler(); t = simdi()
    for yol in glob.glob(os.path.join(KLON, "durum", "tg_*.json")):
        ad = os.path.basename(yol)[3:-5]
        if ad in ("alarm", "silinen"): continue
        defter = [d for d in (_oku(yol, []) or []) if str(d["id"]) not in sil]
        hedef = [d["id"] for d in defter if dt.datetime.fromisoformat(d["sil"]) <= t
                 or t - dt.datetime.fromisoformat(d["gonderim"]) >= dt.timedelta(hours=MAKS_SAAT)]
        bitti = b._sil(hedef); n += len(bitti)
        for i in bitti: sil[str(i)] = t.isoformat()
    sil = {k: v for k, v in sil.items() if t - dt.datetime.fromisoformat(v) < dt.timedelta(days=4)}
    _yaz(os.path.join(CIKTI, "durum", "tg_silinen.json"), sil)
    print(f"Telegram temizliği: {n} mesaj silindi.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "temizle":
        temizle()
    elif len(sys.argv) > 1 and sys.argv[1] == "dene":
        b = Bot("deneme")
        ids = b.mesaj("✅ <b>Bağlantı testi</b>\nBu mesaj sessiz gönderildi ve 1 saat sonra otomatik silinecek.", "deneme", 1, notlu=False)
        print("Gönderildi:", ids)
        try:   # yeni tasarımlı örnek kart + "uygulamada aç" düğmesi (rejim kartı, bülten verisiyle)
            import urllib.request
            import rejim as RJ
            r = json.loads(urllib.request.urlopen("https://raw.githubusercontent.com/erhankatkay-glitch/bist-rapor/bulten/rejim/bist.json", timeout=20).read())
            yol = RJ.kart_ciz(r, os.path.join(CIKTI, "telegram_test", "ornek_kart.png"))
            print("Örnek kart:", b.foto(yol, "🧪 <b>Yeni tasarım örneği</b> · piyasa rejimi kartı\nAltındaki düğme hızlı uygulamayı açar. 1 saat sonra silinir.",
                                       "deneme_kart", 1, dugme=uygulama_dugme(kod="XU100", metin="📲 BIST 100 analizini aç")))
        except Exception as ex:
            print("Örnek kart gönderilemedi:", ex)
        b.kaydet()
