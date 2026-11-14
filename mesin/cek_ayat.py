# SPDX-License-Identifier: AGPL-3.0-or-later
"""Ayat {Q:}: teks mushaf yang dicetak, rujukan «سورة …، آية: n», ayat yang diketik sendiri, dan pencocokan ayat
yang dikutip kitab dengan ayat yang tercetak (termasuk salah ketik dan ayat tanpa ﴿﴾ di kitab)."""
import difflib, functools, json, re

import norma
from dasar import AD, ANGKA_LATIN, AYAT_KITAB, HERE, RUJUKAN_AYAT, SURAH, TandaRusak, perintah

try:
    from rapidfuzz.distance import Levenshtein
except ImportError:  # pustaka belum dipasang ulang sesudah `git pull`
    raise SystemExit("Pustaka Python belum terpasang; cara memasangnya disebut oleh: " + perintah("periksa"))
from petik import kutipan_semua

QURAN = json.loads((HERE / "quran_hafs_v22.json").read_text(encoding="utf8"))
BEDA_AYAT = 2  # huruf kerangka ayat tercetak yang boleh tidak ada di ayat bertanda kitab (ayat_tercetak)
# ﴿…﴾ (atau terbalik ﴾…﴿) berhuruf Arab yang diketik di naskah; {Q:} jadi «﴿2:255﴾» (angka), jadi ﴾ sesudah angka
# dan ﴿ sebelum angka = batas dua {Q:}, bukan kurung ayat terbalik
AYAT_KETIK = re.compile(r"﴿[^﴾]*[ء-ي][^﴾]*﴾|(?<![0-9٠-٩])﴾[^﴿﴾]*[ء-ي][^﴿﴾]*﴿(?![0-9٠-٩])")
# rujukan ayat yang tidak diawali «سورة»: «انظر: سورة الفاتحة، آية: 7», «الفاتحة، آية: 5», «[الفاتحة: 6]»
RUJUKAN_LAIN = re.compile(r"^(?:(?:انظر|ينظر)\s*:\s*)?[\[(]?\s*(?:سورة\s+)?([^،,:/()\[\]]+?)\s*(?:[،,:/]|\sآي)")
# «الآية ٥ من سورة الفاتحة»: nomor dulu, surat sesudahnya
AYAT_DARI_SURAH = re.compile(r"^(?:(?:انظر|ينظر)\s*:\s*)?(?:الآية|الآيات|آية)\s*:?\s*([0-9٠-٩][^م]*?)\s*من\s+سورة\s+([^.،,؛()\[\]]+)")
SURAH_PADAT = {norma.padat(x) for x in SURAH}
# huruf mushaf yang di ejaan imla'i jadi alif biasa: alif kecil («تَعَٰلَىٰ») dan alif wasl («ٱللَّهِ»)
IMLAI = str.maketrans({"ٰ": "ا", "ٱ": "ا"})


@functools.cache
def bentuk_ayat(teks):
    """Bentuk `padat` teks mushaf yang dicocokkan dengan teks kitab: tanpa lafaz ayat yang di ejaan imla'i berbentuk
    kalimat hormat («سبحانه وتعالى» 16:1, «رضي الله عنهم» 98:8, «سيرحمهم الله» 9:71), lalu teks utuhnya kalau beda.
    `norma.padat` membuang kalimat itu dari teks kitab dan naskah (norma.HORMAT), tetapi tidak dari ejaan mushaf, yang
    hurufnya beda («سُبۡحَٰنَهُۥ وَتَعَٰلَىٰ»), jadi ayat kitab yang persis tidak sama lagi dengan ayat yang tercetak.
    Kutipan kitab yang berhenti di tengah kalimat itu (39:67 sampai «سُبْحَانَهُ», الشرح الممتع ج3 ص23) tidak kehilangan
    apa pun, jadi cocok dengan teks utuhnya. Kalimat hormat dicari di ejaan imla'i-nya (huruf demi huruf sejajar dengan
    teks mushaf), lalu dibuang dari teks mushaf."""
    imlai = teks.translate(IMLAI)
    letak = [i for i, x in enumerate(imlai) if not norma.HARAKAT.match(x)]
    polos = "".join(imlai[i] for i in letak)
    huruf = list(teks)
    for m in norma.HORMAT.finditer(polos):
        for i in letak[m.start():m.end()]:
            huruf[i] = " "
    tanpa, utuh = norma.padat("".join(huruf)), norma.padat(teks)
    return (tanpa,) if tanpa == utuh else (tanpa, utuh)


def rujukan_ayat(isi):
    """(nama surat, teks nomornya) rujukan ayat di awal catatan kaki «سورة X، آية: n», «انظر: سورة X…», «X، آية: n»,
    «X: n», «(X: n)», «[X: n]», «X/n», «الآية n من سورة X»; None kalau awalnya bukan nama surat atau tanpa nomor."""
    m = RUJUKAN_LAIN.match(isi)
    nama, angka = (m[1], isi[m.end():]) if m else (None, "")
    if not m or norma.padat(nama) not in SURAH_PADAT:
        m = AYAT_DARI_SURAH.match(isi)
        nama, angka = (m[2], m[1]) if m else (None, "")
    if nama is None or norma.padat(nama) not in SURAH_PADAT or not re.search(r"[0-9٠-٩۰-۹]", angka):
        return None
    return nama, angka.translate(ANGKA_LATIN)


def mirip_ayat(spec, teks):
    """Teks kitab (tanpa tanda ﴿﴾) memuat sepotong ayat {Q:spec}: sama paling sedikit 10 huruf `padat` berturut-turut."""
    b = norma.padat(teks)
    if not b or len(b) > 3000:
        return False
    return any(difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b)).size
               >= min(10, len(a)) for a in bentuk_ayat(ayat(spec)[0]))


def ayat_sama(spec, antara, rujukan):
    """Ayat kitab di celah {Q:} bisa ayat {Q:spec}: nama surat di rujukan [سورة: n] sama, atau teks salah satu ayat
    bertanda ﴿﴾ (atau seluruh celah) memuat sepotong ayat itu. False kalau keduanya ada dan tidak ada yang sama, atau
    kalau ayat bertanda di kitab lebih mirip dengan potongan ayat lain. Teks = lolos dengan perhatian itu."""
    surat = {norma.padat(SURAH[int(x.split(":")[0]) - 1]) for x in spec}
    nama = [norma.padat(re.sub(r"سورة|الآية|الآيات|آية", " ", x)) for x in rujukan]
    if any(n and any(n in t or t in n for t in surat) for n in nama):
        return True
    sama = lambda a, b, n: b and len(b) <= 3000 and difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(
        0, len(a), 0, len(b)).size >= min(n, len(a), len(b))
    tanda = [m.group()[1:-1] for m in AYAT_KITAB.finditer(antara)]
    kalah = False
    for teks in tanda:
        b = norma.padat(teks)
        for x, a in ((x, a) for x in spec for a in bentuk_ayat(ayat(x)[0])):
            # «والليل إذا يسر» (89:4) imla'i, «وَٱلَّيۡلِ إِذَا يَسۡرِ» di mushaf: kerangkanya terlalu pendek untuk ditandingkan
            if b in a or tanpa_lam_sandang(b) in tanpa_lam_sandang(a):
                return True
            # ayat bertanda ﴿﴾ ditulis kitab dengan ejaan imla'i («الصراط»/«الصرط», «الصلاة»/«الصلوة»): dibandingkan
            # juga tanpa huruf alif, waw, ya, dan hamzah
            # kerangka 3-4 huruf («نهل» dari «إن هؤلاء») termuat di banyak ayat: paling sedikit 5 huruf, lalu ditandingkan
            kb = kerangka(b)
            cocok = len(kb) >= 5 and kb in kerangka(a) or sama(a, b, 10) or _kerangka_sama(a, b)
            ketik = not cocok and _salah_ketik(a, b)
            if not (cocok or ketik):
                continue
            # yang tidak termuat persis ditandingkan dengan ayat lain; kitab yang mengutip jauh lebih panjang dari {Q:}
            # (seluruh ayat untuk {Q:s:a:i-j}) tidak: ayat utuhnya pasti lebih mirip daripada potongan {Q:}
            hasil, saingan = _tanding(x, b) if len(b) <= len(a) + 3 else ("menang", None)
            if hasil == "kalah":  # «وإنا على آثارهم مهتدون» (43:22) bukan {Q:43:23} «…مقتدون»
                kalah = True
                continue
            if hasil == "seri":
                return (f"ayat di kitab sama miripnya dengan {{Q:{x}}} dan {{Q:{saingan}}}: pastikan sendiri ayatnya "
                        "(`scan`), lalu nomornya ke mushaf")
            return SALAH_KETIK.format(x) if ketik else True
    if kalah:
        return False
    # ayat tanpa tanda ﴿﴾ di kitab: sepotong ayat itu ada di celah
    b = norma.padat(antara)
    return any(sama(a, b, 10) for x in spec for a in bentuk_ayat(ayat(x)[0]))


@functools.cache
def _dalam(p, k):
    """Huruf beda paling sedikit (diganti, dibuang, atau ditambah) antara p dan sepotong k (panjang potongan bebas), dengan
    paling banyak BEDA_AYAT huruf p yang dibuang (tanpa huruf k di tempatnya); None kalau tidak bisa."""
    if p in k:
        return 0
    tak = float("inf")
    # jarak[r][j] = beda p[:i] dengan sepotong k yang berakhir di j, dengan r huruf p dibuang
    jarak = [[0] * (len(k) + 1)] + [[tak] * (len(k) + 1) for _ in range(BEDA_AYAT)]  # potongan boleh mulai di mana saja
    for x in p:
        baru = [[tak] * (len(k) + 1) for _ in range(BEDA_AYAT + 1)]
        for r in range(BEDA_AYAT + 1):
            atas, isi = jarak[r], baru[r]
            for j in range(len(k) + 1):
                n = atas[j - 1] + (k[j - 1] != x) if j else tak  # dipasangkan dengan k[j-1] (sama atau diganti)
                if r:
                    n = min(n, jarak[r - 1][j] + 1)  # dibuang
                if j:
                    n = min(n, isi[j - 1] + 1)  # huruf k yang tidak ada di p
                isi[j] = n
        jarak = baru
    beda = min(min(b) for b in jarak)  # dan berakhir di mana saja
    return None if beda == tak else beda


def ayat_tercetak(spec, kitab, celah=""):
    """Ayat yang tercetak untuk {Q:spec} (kata ke-i s.d. j kalau ada) dibandingkan dengan ayat bertanda ﴿﴾ yang dikutip
    kitab di tempat itu (isi tandanya, berurutan): «lebih» kalau yang tercetak tidak termuat di ayat kitab (lebih panjang,
    atau lafaz lain), «kurang» kalau termuat tetapi kitab mengutip lebih panjang, "" kalau sama. Ejaan utsmani dan imla'i
    tidak dihitung beda (kerangka: tanpa alif, waw, ya, dan hamzah). Salah ketik, salah baca OCR kitab, dan qiraat boleh:
    huruf yang diganti, paling banyak seperlima kerangka yang tercetak; huruf tercetak yang tidak ada di kitab (kata yang
    ditambah, ayat lain) paling banyak BEDA_AYAT. Tanda ﴿﴾ kitab yang
    rusak (jumlah ﴿ dan ﴾ di celah tidak sama: «﴿فإذا قرأته فاتبع قرءانه﴾ (١٨) ثم إن علينا بيانه﴾»): yang termuat di
    seluruh celah kitab (tanpa rujukan [سورة: n]) dianggap sama. Tanda yang utuh tidak: kata kitab sesudahnya («الآية»)
    bukan lanjutan ayat."""
    k = kerangka(norma.padat(kitab))
    hasil = [_tercetak(kerangka(p), k, celah) for p in bentuk_ayat(" ".join(ayat(x)[0] for x in spec))]
    return min(hasil, key=("", "kurang", "lebih").index)


def _tercetak(p, k, celah):
    """ayat_tercetak untuk satu bentuk kerangka ayat tercetak p dan kerangka ayat kitab k."""
    beda = _dalam(p, k) if k else None
    if beda is None or beda > max(BEDA_AYAT, len(p) // 5):
        rusak = celah.count("﴿") != celah.count("﴾") or celah.count("{") != celah.count("}")
        luas = rusak and kerangka(norma.padat(RUJUKAN_AYAT.sub(" ", celah)))
        beda = _dalam(p, luas) if luas else None
        return "" if beda is not None and beda <= max(BEDA_AYAT, len(p) // 5) else "lebih"
    return "kurang" if len(k) - len(p) > BEDA_AYAT + beda else ""


def pesan_tercetak(hasil, spec, kitab):
    """(galat, perhatian) untuk hasil ayat_tercetak."""
    q = "".join(f"{{Q:{x}}}" for x in spec)
    dikutip = re.sub(r"\s+", " ", norma.HARAKAT.sub("", kitab)).strip()
    if hasil == "lebih":
        return (f"ayat yang tercetak untuk {q} tidak sama dengan ayat yang dikutip kitab di tempat itu («{dikutip[:60]}»): "
                "cetak hanya lafaz yang dikutip kitab ({Q:surat:ayat:i-j} untuk kata ke-i s.d. j)"), ""
    if hasil == "kurang":
        return "", (f"ayat dipotong: kitab mengutip lebih panjang («{dikutip[:60]}») daripada {q} yang tercetak: pastikan "
                    "potongannya tidak mengubah makna, atau cetak sebatas lafaz kitab")
    return "", ""


SALAH_KETIK = ("ayat di kitab tidak sama dengan ayat mushaf mana pun (salah ketik?), paling mirip dengan {{Q:{0}}}: "
               "pastikan sendiri ayatnya (`scan`), lalu nomornya ke mushaf")


def _salah_ketik(a, b):
    """Ayat bertanda ﴿﴾ yang pendek salah ketik di kitab («﴿وَءَاثُوا الزَّكَاةَ﴾» untuk «وءاتوا الزكوة», «﴿فِيهِدْنَهُمْ
    أَقْتَدَةً﴾» untuk «فبهداهم اقتده»): satu-dua huruf beda sudah memutus 10 huruf berturut-turut. Paling sedikit 8
    huruf `padat`, tidak termuat di ayat mana pun, dan 4/5 hurufnya sama dengan sepotong ayat {Q:} sepanjang itu."""
    if len(b) < 8 or _di_quran(b):  # teks kitab yang memang ayat lain («مهتدون» 43:22 untuk «مقتدون» 43:23) bukan salah ketik
        return False
    sm = difflib.SequenceMatcher(None, "", b, autojunk=False)
    for i in range(max(1, len(a) - len(b) + 1)):
        sm.set_seq1(a[i:i + len(b)])
        if sm.ratio() >= 0.8:
            return True
    return False


def _calon(x, b, beda):
    """Potongan ayat x sepanjang b yang mungkin berbeda paling banyak `beda` huruf dari b: b dibagi beda+1 bagian, dan
    tiap potongan seperti itu pasti memuat salah satu bagiannya persis (satu huruf beda merusak paling banyak satu
    bagian). Dicari dengan str.find, bukan dengan membandingkan semua potongan."""
    if len(x) <= len(b):
        return [x]
    ukuran = len(b) // (beda + 1)
    if ukuran < 2:
        return [x[i:i + len(b)] for i in range(len(x) - len(b) + 1)]
    awal = set()
    for i in range(beda + 1):
        bagian, letak = b[i * ukuran:(i + 1) * ukuran], i * ukuran
        j = x.find(bagian)
        while j >= 0:
            awal |= set(range(max(0, j - letak - beda), min(len(x) - len(b), j - letak + beda) + 1))
            j = x.find(bagian, j + 1)
    return [x[s:s + len(b)] for s in sorted(awal)]


def _tanding(spec, b):
    """Ayat bertanda di kitab b (`padat`) dibandingkan dengan ayat {Q:spec} dan semua ayat mushaf. Ayat lain yang
    memuat b persis menang. Selain itu dibandingkan kerangkanya (tanpa alif, waw, ya, dan hamzah: ejaan imla'i dan
    utsmani tidak dihitung beda) sepanjang kerangka b: jumlah huruf yang beda («القحيم» satu huruf dari «الرحيم», dua
    dari «الحكيم»). ("kalah", nomor) kalau ada ayat lain yang lebih dekat, ("seri", nomor) kalau sama dekatnya,
    ("menang", None) kalau tidak ada. Potongan {Q:} diambil dari ayat utuhnya (kitab yang menambah satu huruf di depan
    potongan {Q:} yang pendek tidak boleh menang hanya karena potongannya pendek). Ayat {Q:} sendiri dan potongan
    yang kerangkanya sama dengan potongan {Q:} (ayat yang berulang) bukan saingan."""
    nomor = ":".join(spec.split(":")[:2])
    s, _, ayat_ = nomor.partition(":")
    x1, _, x2 = ayat_.partition("-")
    sendiri = {f"{s}:{n}" for n in range(int(x1), int(x2 or x1) + 1)}
    lain = next((k for k, x in _quran_padat_nomor() if k not in sendiri and b in x), None)
    if lain:  # «وقاتلوا في سبيل الله» (2:190) bukan {Q:2:154} «يقتل في سبيل الله», walau kerangkanya sama
        return "kalah", lain
    kb = kerangka(b)
    if len(kb) < 5:  # kerangka 3-4 huruf termuat di banyak ayat: tidak bisa ditandingkan
        return "menang", None
    milik = None
    for a in map(kerangka, bentuk_ayat(ayat(nomor)[0])):
        for i in range(max(1, len(a) - len(kb) + 1)):
            w = a[i:i + len(kb)]
            n = (Levenshtein.distance(w, kb, score_cutoff=milik[0] if milik else None), w)
            milik = min(milik, n) if milik else n
    beda, saingan = milik[0], None
    bentuk = {}
    for k, x in _quran_padat_nomor():
        bentuk.setdefault(k, []).append(x)
    jarak = lambda k: min(_jarak_ayat(x, b) for x in bentuk[k])  # noqa: E731
    jauh = functools.cache(lambda: min(_jarak_ayat(x, b) for x in bentuk_ayat(ayat(nomor)[0])))  # huruf lengkap {Q:}
    for k, x in _quran_kerangka_nomor():
        for w in _calon(x, kb, beda) if k not in sendiri else ():
            if w == milik[1]:
                # kerangka sama («الله للكافرين» 4:141, «والله للكافرين» 58:4): ayat berulang, kecuali huruf lengkapnya
                # lebih dekat ke ayat lain. Ejaan imla'i bisa begitu juga, jadi cukup seri (perhatian)
                if saingan is None and jarak(k) < jauh():
                    saingan = k
                continue
            n = Levenshtein.distance(w, kb, score_cutoff=beda)
            if n < beda:
                # salah ketik huruf mati bisa mendekatkan kerangka ke ayat lain: kalah hanya kalau ayat lain itu juga
                # lebih dekat dalam huruf lengkap («الرسل حلا»: 1 huruf dari 46:35 dan dari 16:35); selain itu seri
                if jarak(k) < jauh():
                    return "kalah", k
                saingan = saingan or k
            elif n == beda and saingan is None and jarak(k) <= jauh():  # seri di keduanya
                saingan = k
    return ("seri", saingan) if saingan else ("menang", None)


def _jarak_ayat(a, b):
    """Jumlah huruf beda terkecil antara b dan potongan ayat a (`padat`) sepanjang b."""
    terbaik = None
    for i in range(max(1, len(a) - len(b) + 1)):
        n = Levenshtein.distance(a[i:i + len(b)], b, score_cutoff=terbaik)
        terbaik = n if terbaik is None else min(terbaik, n)
    return terbaik


@functools.cache
def _quran_kerangka_nomor():
    return [(k, kerangka(x)) for k, x in _quran_padat_nomor()]


@functools.cache
def _quran_padat_nomor():
    return [(k, x) for k, v in QURAN.items() for x in bentuk_ayat(v)]


def _di_quran(b):
    """Teks `padat` b termuat di salah satu ayat mushaf (juga tanpa alif, waw, ya, dan hamzah: ejaan imla'i)."""
    kb = kerangka(b)
    return any(b in x or kb in kerangka(x) for _, x in _quran_padat_nomor())


def _kerangka_sama(a, b):
    """Tanpa alif, waw, ya, dan hamzah, 8 huruf berturut-turut gampang sama di ayat lain («مرضى أو على سفر» di 2:184
    dan 4:43): yang sama harus paling sedikit 8 huruf dan 4/5 kerangka yang lebih pendek; potongan kitab yang
    kerangkanya 5-7 huruf harus termuat utuh."""
    ka, kb = kerangka(a), kerangka(b)
    if not ka or not kb:
        return False
    n = difflib.SequenceMatcher(None, ka, kb, autojunk=False).find_longest_match(0, len(ka), 0, len(kb)).size
    return n >= max(8, -(-4 * min(len(ka), len(kb)) // 5)) or 5 <= len(kb) < 8 and n == len(kb)


KERANGKA = re.compile(r"[اويىءأإآؤئ]")
# «ال» + lam kata: imla'i menulis dua lam («الليل»، «اللاتي»، «اللائي»), mushaf satu («ٱلَّيۡلِ»، «ٱلَّٰتِي»). Lafaz
# الجلالة tidak (lam-lam-ha): «الله» tetap beda dari «إله»، «له»، «لله». Lam berderet lain tidak disatukan, karena
# «إلا الله» dan «إلا هو» jadi sama kerangkanya.
LAM_SANDANG = re.compile("الل(?!ه)")


def tanpa_lam_sandang(s):
    """Teks `padat` dengan «الل» (bukan lafaz الجلالة) jadi «ال»: ejaan imla'i «الليل» = ejaan mushaf «ٱلَّيۡلِ»."""
    return LAM_SANDANG.sub("ال", s)


def kerangka(s):
    """Huruf `padat` tanpa alif, waw, ya, dan hamzah, dan tanpa lam kedua «الل» (tanpa_lam_sandang): ejaan mushaf dan
    imla'i yang hanya beda di huruf itu sama kerangkanya («الصلوة/الصلاة», «ٱلَّيۡلِ/الليل», «ٱلَّٰتِي/اللاتي»)."""
    return KERANGKA.sub("", tanpa_lam_sandang(s))


def ayat_persis(spec, teks):
    """Teks ayat bertanda di kitab (paling sedikit 12 huruf `padat`) termuat utuh di ayat {Q:spec} (juga tanpa alif, waw,
    ya, dan hamzah: ejaan imla'i): nomor di rujukan kitab yang berbeda berarti rujukan kitabnya yang salah."""
    b = norma.padat(teks)
    if len(b) < 12:
        return False
    a = [a for x in spec for a in bentuk_ayat(ayat(x)[0])]
    return any(b in x or kerangka(b) in kerangka(x) for x in a)


def ayat(spec):
    """'s:a' | 's:a-b' | 's:a:i-j' -> (teks_utsmani, surah, 'a' atau 'a-b')."""
    p = spec.split(":")
    if len(p) not in (2, 3) or not re.fullmatch(r"\d+", p[0]) or not all(re.fullmatch(r"\d+(-\d+)?", x) for x in p[1:]):
        raise TandaRusak(f"{{Q:{spec}}}: bentuknya {{Q:surat:ayat}}, {{Q:surat:a-b}}, atau {{Q:surat:ayat:i-j}}")
    if len(p) == 3 and "-" in p[1]:
        raise TandaRusak(f"{{Q:{spec}}}: kata ke-i s.d. j hanya untuk satu ayat ({{Q:surat:ayat:i-j}})")
    p[1] = "-".join(str(int(x)) for x in p[1].split("-"))  # «٢» dan «02» = ayat 2
    s = int(p[0])
    if any(f"{s}:{n}" not in QURAN for n in map(int, p[1].split("-"))):
        raise TandaRusak(f"{{Q:{spec}}}: surat/ayat itu tidak ada")
    if "-" in p[1]:
        a, b = map(int, p[1].split("-"))
        if a > b:
            raise TandaRusak(f"{{Q:{spec}}}: rentang ayat harus dari kecil ke besar")
        bagian = []
        for n in range(a, b + 1):
            bagian.append(QURAN[f"{s}:{n}"])
            if n < b:
                bagian.append(" " + str(n).translate(AD))
        return " ".join(bagian).replace("  ", " "), s, p[1]
    t = QURAN[f"{s}:{p[1]}"]
    if len(p) > 2:
        i, _, j = p[2].partition("-")
        i = int(i); j = int(j or i)
        if not 1 <= i <= j <= len(t.split()):
            raise TandaRusak(f"{{Q:{spec}}}: ayat itu hanya {len(t.split())} kata")
        t = " ".join(t.split()[i - 1: j])
    return t, s, p[1]


def penanda_ayat(spec):
    """{Q:spec} di teks polos yang dicek (AYAT_DI_KUTIPAN): « ﴿s:a﴾ », « ﴿s:a-b﴾ », atau « ﴿s:a:i-j﴾ » dengan angka Latin.
    Kata ke-i s.d. j ikut dibawa: yang dibandingkan dengan ayat di kitab adalah ayat yang tercetak."""
    _, s, a = ayat(spec)
    p = spec.split(":")
    if len(p) > 2:
        i, _, j = p[2].partition("-")
        a += f":{int(i)}-{int(j or i)}"
    return f" ﴿{s}:{a}﴾ "


def ayat_ketik(teks):
    """﴿…﴾ berhuruf Arab pertama yang diketik di luar tanda petik (di dalam petik, kutipannya dicek ke kitab), atau None."""
    dikutip = " ".join(kutipan_semua(teks))
    return next((k for k in AYAT_KETIK.findall(teks) if k not in dikutip), None)
