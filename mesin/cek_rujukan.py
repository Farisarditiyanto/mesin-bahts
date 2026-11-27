# SPDX-License-Identifier: AGPL-3.0-or-later
"""Yang tercetak di catatan kaki dibandingkan dengan buktinya: juz/halaman dan nomor hadits, judul kitab dan
pengarang (kitab lain = GAGAL), dan judul kitab Shamela yang ditulis sebagai <<luar>>."""
import re
import typing

import norma
import shamela
import waqfeya
from dasar import ANGKA_LATIN, LUAR, RENTANG_MAKS, TAKHRIJ_AWAL, WAQFEYA_BUKTI, ekor, perintah
from kitab_lokal import bagian_kitab, kitab_meta, rekaman
from laporan import ringkas_rentang

# mukharrij yang namanya ditulis sesudah «أخرجه/رواه»: bentuk-bentuk tulisannya (i'rab, ejaan). Kitab bukti yang judul
# atau pengarangnya memuat salah satu bentuk itu = kitab mukharrij itu, syarahnya, atau takhrij/ringkasannya
MUKHARRIJ = (("البخاري",), ("مسلم",), ("أبو داود", "أبي داود", "أبا داود"), ("الترمذي",), ("النسائي",),
             ("ابن ماجه", "ابن ماجة"), ("أحمد",), ("مالك",), ("الدارمي",), ("ابن حبان",), ("الحاكم",), ("البيهقي",),
             ("الطبراني",), ("ابن خزيمة",), ("الدارقطني",), ("ابن أبي شيبة",), ("عبد الرزاق",))
TAKHRIJ_OLEH = re.compile(r"(?<!\w)(?:أخرج|خرج|رو[ىا])(?:ه|ها|هما|اه)?\s+(?:الإمام\s+|الحافظ\s+)?("
                          + "|".join(re.escape(b) for bb in MUKHARRIJ for b in sorted(bb, key=len, reverse=True)) + r")(?!\w)")


@shamela.cache_kitab()
def _nama_kitab_pasangan(title, author):
    judul, pengarang = [], []
    for j in shamela.judul_pokok(title):
        judul.append(" ".join(shamela.kata_judul(j)[:2]))
    for p in author.split("،"):
        pengarang += [p, p.split()[-1]] if p.split() else []
    rapi = lambda xx: frozenset(x for x in map(norma.padat, xx) if len(x) >= 3)
    return rapi(judul), rapi(pengarang)


def _nama_kitab(m):
    """(judul, pengarang): bentuk `padat` yang menandai kitab bukti (metadata m) disebut di catatan kaki. Judul = dua kata
    awal tiap judulnya (judul katalog bisa «تفسير السعدي = تيسير الكريم الرحمن»; pengarang yang ditempel di judul
    dibuang; judul satu kata = kata itu). Pengarang = nama utuh dan kata terakhirnya (nisbah: «أبو إسحاق الشاطبي» ditulis
    «الشاطبي»)."""
    return _nama_kitab_pasangan(m["title_ar"], m.get("main_author_name_ar") or "")


SYARAH = re.compile(r"شرح|حاشي|تعليق|(?<!\w)على(?!\w)")  # judul kitab bukti yang memuat matan kitab lain


def kitab_lain(isi, sid_bukti):
    """Catatan kaki yang menyebut kitab lain dari buktinya: (galat, perhatian).
    GAGAL: judul katalog kitab lain di tempat judul (bagian pertama; juga satu kata: «المغني، ص5» untuk bukti رسالة في
    القضاء والقدر), walau pengarangnya sama («شرح العقيدة الواسطية، ابن عثيمين»); dan, kalau judul maupun pengarang kitab
    bukti tidak disebut sama sekali, mukharrij lain sesudah «أخرجه/رواه» («أخرجه البخاري» untuk bukti صحيح مسلم) atau
    pengarang katalog lain di tempat pengarang («فتح الباري، ابن حجر» untuk bukti صحيح مسلم).
    Perhatian: judul kitab bukti disebut tetapi pengarang katalog lain di tempat pengarang («رسالة في القضاء والقدر، ابن
    تيمية»); dan bukti syarah/hasyiah yang judulnya memuat kata khas kitab lain itu («صحيح البخاري» untuk bukti فتح الباري
    بشرح البخاري): matan bisa dikutip dari syarahnya.
    Tidak ditandai: rujukan ringkas tanpa judul («المرجع السابق»), judul yang termuat di judul kitab bukti (disingkat,
    atau matan di dalam syarahnya: «زاد المستقنع، الحجاوي» untuk bukti الشرح الممتع على زاد المستقنع), dan perantara yang
    disebut («رواه البخاري، انظر: رياض الصالحين»)."""
    data = [shamela.info(s) for s in dict.fromkeys(sid_bukti)]
    if not data:
        return None, None
    pi = norma.padat(isi)
    nama = [_nama_kitab(m) for m in data]
    judul_disebut = any(x in pi for j, _ in nama for x in j)
    pengarang_disebut = any(x in pi for _, p in nama for x in p)
    milik_judul = norma.padat(" ".join(m["title_ar"] for m in data))
    milik = milik_judul + norma.padat(" ".join(m.get("main_author_name_ar") or "" for m in data))
    bagian = [b.strip() for b in PEMISAH_RUJUKAN.split(AWALAN_RUJUKAN.sub("", isi.strip())) if b.strip()]
    awal = (bagian or [""])[0].split()
    # pengarang di tempat pengarang (dua bagian pertama: «المغني، ابن قدامة», «ابن قدامة، المغني»); «أبو يعلى» = «القاضي
    # أبو يعلى ، ابن الفراء» (nama katalog kitab bukti memuatnya utuh sekata)
    bukti_pengarang = {str(m.get("main_author_id")) for m in data}
    nama_bukti = " " + " ".join(norma.norm(m.get("main_author_name_ar") or "") for m in data) + " "
    pengarang_lain = [f"«{b}»" for b in bagian[:2] if (lambda n: n and not n & bukti_pengarang)(shamela.nomor_pengarang(b))
                      and f" {norma.norm(b)} " not in nama_bukti]
    if judul_disebut:
        # pengarang dinilai hanya kalau bagian pertama judul kitab bukti itu sendiri («رسالة في القضاء والقدر، ابن تيمية»),
        # bukan matan yang disebut sebelum syarahnya («منهاج الطالبين، النووي، مع مغني المحتاج»), dan bukti bukan syarah
        # («الكسب، الشيباني» untuk bukti الكسب بشرح السرخسي) atau majalah (pengarangnya penulis makalah)
        pertama = norma.padat((bagian or [""])[0])
        dinilai = any(x in pertama for j, _ in nama for x in j) and not any(
            SYARAH.search(m["title_ar"]) or m["title_ar"].startswith(MAJALAH) for m in data)
        return None, (f"pengarang {' dan '.join(pengarang_lain)} di catatan kaki bukan pengarang kitab buktinya "
                      f"({'، '.join(m['title_ar'] for m in data)}): betulkan nama pengarangnya") if pengarang_lain and dinilai else None
    # matan di dalam syarahnya («أوضح المسالك، ابن هشام» untuk bukti ضياء السالك إلى أوضح المسالك, «زاد المستقنع في اختصار
    # المقنع، الحجاوي» untuk bukti الشرح الممتع على زاد المستقنع): judul dan pengarang matan, bukan kitab lain
    matan = len(awal) >= 2 and norma.padat(" ".join(awal[:2])) in milik_judul
    pengarang_lain = [] if matan else pengarang_lain
    lain = []
    # judul hanya dicari di tempat judul (bagian pertama catatan kaki), utuh atau disusul pengarang: bagian lain bisa
    # «كتاب الإيمان» (nama bab) yang kebetulan juga judul kitab
    for n in range(len(awal), 0, -1):
        judul = " ".join(awal[:n])
        nomor = shamela.nomor_judul_pokok(judul) if n == len(awal) or PENGARANG_SESUDAH.match(awal[n]) else []
        if nomor:
            # pengarang bukti disebut: judul itu kitab lain kalau ada kitab berjudul itu karya pengarang bukti sendiri
            # («شرح العقيدة الواسطية، ابن عثيمين» untuk bukti رسالة في القضاء والقدر). Judul yang hanya milik pengarang lain
            # («تفسير القرآن العظيم، ابن كثير»: judul katalog itu milik السخاوي) = nama lain kitab bukti sendiri.
            # Grup yang sama = edisi atau ringkasan kitab bukti.
            asal = [shamela.asal(x) for x in nomor]
            grup_bukti = {shamela.asal(x)[1] for x in sid_bukti} - {None}
            if (not matan and not set(nomor) & set(sid_bukti) and norma.padat(judul) not in milik_judul
                    and not any(g in grup_bukti for _, g in asal)
                    and (not pengarang_disebut or any(p in bukti_pengarang for p, _ in asal))):
                lain.append(f"«{judul}»")
            break
    mukharrij = []
    if not pengarang_disebut:
        for g in TAKHRIJ_OLEH.findall(isi):
            bentuk = next(bb for bb in MUKHARRIJ if g in bb)
            if not any(norma.padat(b) in milik for b in bentuk):
                mukharrij.append(f"«{g}»")
        lain += mukharrij + pengarang_lain
    if not lain:
        return None, None
    # bukti syarah kitab hadits yang mukharrij-nya juga disebut kitab lain itu («صحيح البخاري» untuk bukti فتح الباري
    # بشرح البخاري): matan dikutip dari syarahnya, cukup perhatian. Kitab lain apa pun untuk bukti syarah lain («المغني»
    # untuk bukti الشرح الممتع) = GAGAL.
    nama_mukharrij = {norma.padat(b) for bb in MUKHARRIJ for b in bb}
    khas = lambda t: {norma.padat(w) for w in t.split()} & nama_mukharrij
    ragu = not mukharrij and any(SYARAH.search(m["title_ar"]) and khas(m["title_ar"]) & khas(" ".join(lain)) for m in data)
    return (None, pesan_lain(lain, data)) if ragu else (pesan_lain(lain, data), None)


def pesan_lain(lain, data):
    return (f"catatan kaki menyebut {' dan '.join(dict.fromkeys(lain))}, tetapi buktinya kitab lain "
            f"({'، '.join(m['title_ar'] for m in data)}) yang judulnya tidak disebut: tulis kitab yang "
            f"benar-benar dibaca, atau sebut perantaranya («…، انظر: <judul>»)")


def tercetak(isi, juz):
    """Rentang halaman yang tercetak di catatan kaki untuk juz ini: [(awal, akhir)]. Angka ٠-٩ dibaca seperti 0-9.
    «ص» harus berdiri sebagai kata («النص 5» bukan halaman), boleh disambung و/ف («وص6»). Rentang boleh «-» atau «–»;
    «ص5، 7», «ص5 و7», «1/5، 7» = halaman 5 dan 7 (angka sesudah koma atau و yang bukan tahun atau juz/halaman).
    «ص: 5», «ص.5» (perhatian cek_tautsiq.titik_singkatan) dan «الصفحة 5» sama dengan «ص5».
    Halaman bahts sendiri («ص3 من هذا البحث», «ص3 من البحث», «ص3 من هذه الرسالة/المذكرة») bukan halaman kitab."""
    isi = re.sub(r"\d+(?:\s*(?:[-–]|[،,]\s*و?|\s+و)\s*\d+)*\s*(?=من\s+(?:(?:هذا\s+)?البحث|هذه\s+(?:الرسالة|المذكرة)))",
                 " ", isi.translate(ANGKA_LATIN))
    rentang = r"\d+(?!\d)(?:\s*[-–]\s*\d+(?!\d))?"
    tahun = r"(?:1[34]|19|20)\d\d(?!\d|\s*[-–])"  # «ص5، 1423»: tahun cetak tanpa هـ, bukan halaman kedua
    satu = rf"{rentang}(?![\d/]|(?:\s*[-–]\s*\d+)*\s*(?:/|هـ|ه(?!\w)|م(?!\w)))"
    daftar = rf"(?:\s*(?:[،,]\s*و?|\s+و)\s*(?!{tahun}){satu})*"
    if juz == "-":
        pola = rf"(?<![\wـ])(?:[وف]?ص|الصفحة)\s*[:.]?\s*({satu}{daftar})"
    else:
        pola = rf"(?<![\d/]){re.escape(juz)}\s*/\s*({satu}{daftar})"
    return [(int(a), int(b or a)) for m in re.findall(pola, isi) for a, b in re.findall(r"(\d+)(?:\s*[-–]\s*(\d+))?", m)]


# «j/n» juz mana saja; bukan tanggal («12/5/1420», «1420هـ/2000م») atau cetakan («ط2/1420»)
# nomor hadits «رقم (5/ 103)», «الحديث 5/103» (nomor bab/hadits seperti cetakan سبل السلام) bukan juz/halaman
NOMOR_HADITS = re.compile(r"(?:رقم|حديث)(?:\s*الحديث)?\s*:?\s*\(?\s*\d+\s*/\s*\d+\s*\)?")
JUZ_TERCETAK = re.compile(r"(?<![\w/])(\d{1,2})\s*/\s*\d+(?![\d/])(?!\s*(?:هـ|م(?!\w)))")
# «ج1، ص55», «ج1/ص55», «ج ١ ص ٥٥», «الجزء 1، ص55», «الجزء الأول، الصفحة 55» (sesudah ANGKA_LATIN) = «1/55»
URUTAN = {"الأول": 1, "الاول": 1, "الثاني": 2, "الثالث": 3, "الرابع": 4, "الخامس": 5, "السادس": 6, "السابع": 7,
          "الثامن": 8, "التاسع": 9, "العاشر": 10}
JUZ_ARAB = re.compile(rf"(?<![\wـ])(?:ج|الجزء)\s*[:.]?\s*(\d{{1,2}}|{'|'.join(URUTAN)})\s*[،,/]?\s*(?:ص|الصفحة)\s*[:.]?\s*(?=\d)")


def juz_arab(t):
    """«ج1، ص55» dan kawan-kawannya -> «1/55» (t sudah lewat ANGKA_LATIN)."""
    return JUZ_ARAB.sub(lambda m: f"{URUTAN.get(m[1], m[1])}/", t)


# rujukan ke halaman bahts sendiri, bukan kitab: «تقدم تخريجه ص5», «سيأتي في ص{P:x}», «ينظر: المبحث الثاني، ص 12»,
# «ينظر: التمهيد، ص 3». «الفصل في الملل» judul kitab: sesudah المبحث/المطلب/الفصل harus urutan «الثاني» atau angka;
# «المقدمة الحضرمية» juga: التمهيد/المقدمة/الخاتمة harus langsung disusul ص. «ص5 من (هذا) البحث» di tercetak().
RUJUKAN_DALAM = re.compile(r"(?:(?:(?<!\w)(?:سبق|تقدم|سيأتي|يأتي)(?!\w)|(?<!\w)(?:المبحث|المطلب|الفصل)\s+(?:ال\w+|\d+))[^.؛]*?"
                           r"|(?<!\w)(?:التمهيد|المقدمة|الخاتمة)\s*[،,:]?\s*)"
                           r"(?<![\wـ])ص\s*(?:\{P:[a-z]+\}|\d+(?:\s*[-–]\s*\d+)?)")


def rujukan_halaman(isi):
    """Catatan kaki yang mencetak juz/halaman kitab («1/55», «ص55», «ج1، ص55») atau nomor hadits («رقم الحديث»):
    rujukan kitab, jadi buktinya bisa ditulis. Takhrij bernomor tanpa halaman juga: «أخرجه البخاري، رقم (1901)»,
    «أخرجه البخاري (1901)», «صحيح البخاري، حديث رقم: 1901». Rujukan ke halaman bahts sendiri tidak dihitung."""
    t = juz_arab(RUJUKAN_DALAM.sub(" ", isi.translate(ANGKA_LATIN)))
    takhrij = re.search(r"أخرج|رواه|حديث|صحيح|سنن|مسند|البخاري|مسلم", t) and re.search(r"رقم\s*:?\s*\(?\s*\d|\(\s*\d+\s*\)", t)
    return bool(re.search(r"رقم\s+الحديث", t) or takhrij or tercetak(t, "-") or JUZ_TERCETAK.search(NOMOR_HADITS.sub(" ", t)))


MUJAM = 30  # bidang Shamela الغريب والمعاجم (لسان العرب، الصحاح، القاموس المحيط…)
# materi kamus yang dirujuk: «مادة (قدر)», «مادة: قدر», atau bentuk kitab 8350 «(قدر)» (الكلمة بين قوسين، ص142، 155)
MADDA = re.compile(r"(?<![ء-ي])مادة\s*:?\s*[(«\"]?\s*([ء-يً-ْ]+)")
MADDA_KURUNG = re.compile(r"\(\s*([ء-يً-ْ]+)\s*\)")


def madda(teks, bb):
    """Kamus yang dirujuk lewat materinya: (materi, ada di halaman bukti?) untuk materi pertama yang tertulis, atau None
    kalau bukan rujukan kamus. Materinya harus berdiri sebagai kata (boleh berawalan ال) di halaman tiap bukti."""
    if not bb or not all((kitab_meta(b.sid) or {}).get("kategori") == MUJAM for b in bb):
        return None
    m = MADDA.search(teks) or MADDA_KURUNG.search(teks)
    if not m:
        return None
    kata = norma.norm(m[1]).strip()
    ada = all(any(re.search(rf"(?<![ء-ي])(?:ال)?{re.escape(kata)}(?![ء-ي])", norma.norm(r.get("body") or ""))
                  for r in rekaman(*b.tempat)) for b in bb)
    return kata, ada


class SalahHalaman(typing.NamedTuple):
    """Hasil cocok_halaman yang tidak cocok: satu galat untuk satu catatan kaki."""
    pesan: str
    tanpa_bukti: bool  # ada halaman tercetak yang tidak punya bukti sama sekali


def _saring_klausa_luar(isi):
    if "<<" not in isi:
        return isi
    bukti_tok = []
    bertanda = re.sub(r"<<[^>]*>>", lambda m: (bukti_tok.append(m.group(0)), f"\x00{len(bukti_tok) - 1}\x00")[1], isi)
    pola_luar = re.compile(rf"<<{LUAR}(?:\||>>)")
    pola_shamela = re.compile(r"<<\d+\|")
    klausa = []
    for k in re.split(r"[؛;]|(?<=\x00)\s*[،,.]\s*", bertanda):
        asli = re.sub(r"\x00(\d+)\x00", lambda m: bukti_tok[int(m.group(1))], k)
        if pola_luar.search(asli) and not pola_shamela.search(asli):
            continue
        if bersih := re.sub(r"\s*<<[^>]*>>", "", asli).strip():
            klausa.append(bersih)
    return "؛ ".join(klausa)


def cocok_halaman(isi, bukti, perhatian):
    """Bandingkan juz/halaman yang tercetak dengan bukti [Bukti]; kembalikan SalahHalaman, atau None kalau cocok.
    Tiap halaman tercetak harus di dalam rentang bukti kitabnya, dan tiap bukti harus tercetak (kecuali kamus yang
    dirujuk lewat «مادة …»).
    «سبق تخريجه» mencetak halaman bahts ({P:}), bukan halaman kitab: yang dicek hanya halaman kitab yang tercetak."""
    if not bukti:
        return None
    isi = _saring_klausa_luar(isi)
    if not isi:
        return None
    galat, tanpa_bukti = [], False
    bagian = bagian_kitab(isi, bukti)
    if len(bagian) == 1 and len({b.sid for b in bukti}) > 1 and "سبق تخريجه" not in isi:
        perhatian.append(f"catatan kaki merujuk {len({b.sid for b in bukti})} kitab, tetapi judul kitabnya tidak dikenali, jadi "
                         f"halaman tiap kitab tidak bisa dicocokkan dengan buktinya sendiri: tulis judul kitab seperti di "
                         f"katalog (`kartu`), atau pastikan sendiri halaman tiap kitab{ekor(isi)}")
    for teks, bb in bagian:
        kitabnya = f" (kitab {bb[0].sid})" if len(bagian) > 1 else ""
        juz_bukti = {b.juz for b in bb}
        # juz yang tidak punya bukti sama sekali («3/77» di kitab satu jilid, «ص900» di kitab berjilid)
        utuh = teks.translate(ANGKA_LATIN)  # «عند شرحه للحديث (1/ 222)»: bukti yang tercetak di sini tetap terbaca
        if juz_bukti - {"-"}:  # kitab satu jilid (juz «-»): «ج1، ص55» tetap dibaca «ص55» seperti dulu
            utuh = juz_arab(utuh)
        bernama = [j for j in juz_bukti if j != "-" and not j.isdigit()]
        for j in bernama:  # «المقدمة، ص1» = halaman 1 bagian المقدمة, sama dengan «المقدمة/1»
            utuh = re.sub(rf"(?<!\w){re.escape(j)}\s*[،,:]?\s*(?:ص|الصفحة)\s*:?\s*(?=\d)", f"{j}/", utuh)
        if len(bernama) == 1 and "-" not in juz_bukti:  # «ص5» tanpa nama bagian = halaman bagian buktinya (<<id|الكتاب|5>>)
            utuh = re.sub(r"(?<![\wـ])(?:([وف]?)ص|([وف]?)الصفحة)\s*:?\s*(?=\d)",
                          lambda m: f"{m.group(1) or m.group(2) or ''}{bernama[0]}/", utuh)
        teks = NOMOR_HADITS.sub(" ", utuh)
        lain = {j for j in JUZ_TERCETAK.findall(teks)} | {"-"}
        for juz in juz_bukti | (lain - juz_bukti):
            ada = {n for x in bb if x.juz == juz for n in range(x.p1, x.p2 + 1)}
            for a, b in tercetak(teks, juz):
                if a < 1 or b < a or b - a > RENTANG_MAKS:
                    galat.append(f"halaman tercetak {juz}/{a}-{b} tidak punya bukti{kitabnya}"); tanpa_bukti = True
                    continue  # tolak sebelum range dibuat: salah ketik jangan menghabiskan memori
                kurang = sorted(set(range(a, b + 1)) - ada)
                if not kurang:
                    continue
                if len(kurang) == b - a + 1:
                    galat.append(f"halaman tercetak {juz}/{a}{'-' + str(b) if b != a else ''} tidak punya bukti{kitabnya}")
                    tanpa_bukti = True
                else:  # «1/36-37» dengan bukti 36 saja
                    sid = next(x.sid for x in bb if x.juz == juz)
                    galat.append(f"halaman tercetak {juz}/{a}-{b}: bukti belum mencakup {ringkas_rentang(kurang)}{kitabnya}: "
                                 f"lebarkan buktinya (<<{sid}|{juz}|{a}-{b}>>) atau cetak halaman buktinya saja "
                                 f"({juz}/{ringkas_rentang(sorted(set(range(a, b + 1)) & ada))})")
        # kamus yang tersusun menurut huruf (bidang Shamela الغريب والمعاجم) boleh dirujuk lewat materinya «مادة (قدر)»
        # tanpa juz/halaman (أبو سليمان، كتابة البحث العلمي، ص142، 155); materinya harus ada di halaman bukti, dan halaman
        # yang tetap tercetak dicek seperti biasa
        # Materi hanya dinilai kalau halamannya memang tidak tercetak: «(بيروت)» di data cetak bukan materi.
        tak_tercetak = []
        for s, z, p1, p2 in dict.fromkeys(x.tempat for x in bb) if "سبق تخريجه" not in isi else ():
            # gabungan halaman yang tercetak: «1/102، 103» untuk bukti 102-103
            if not any(set(range(p1, p2 + 1)) <= {n for a, b in t if b - a <= RENTANG_MAKS for n in range(a, b + 1)}
                       for t in (tercetak(teks, z), tercetak(utuh, z))):
                tak_tercetak.append(f"juz/halaman bukti kitab {s} ({z}/{p1}{'-' + str(p2) if p2 != p1 else ''}) tidak tercetak di catatan kaki")
        materi = madda(teks, bb) if tak_tercetak else None
        if materi and not materi[1]:
            galat.append(f"materi kamus «{materi[0]}» tidak ada di halaman bukti{kitabnya}: tulis materi yang dibahas di "
                         f"halaman itu, atau betulkan buktinya")
        elif not materi:
            galat += tak_tercetak
    # satu catatan kaki = satu galat
    return SalahHalaman('; '.join(dict.fromkeys(galat)) + ekor(isi, rapat=True, lebar=60), tanpa_bukti) if galat else None


AWALAN_RUJUKAN = re.compile(r"^(?:انظر|ينظر|راجع|كتاب)\s*:?\s*")
PEMISAH_RUJUKAN = re.compile(r"[،,.():؛«»\"\-–]")
MAJALAH = "مجلة"  # judul jurnal: terbitannya belum tentu ada di Shamela, jadi kemiripan judul cukup perhatian
PENGARANG_SESUDAH = shamela.PENGARANG_SESUDAH  # «… للشيخ ابن عثيمين»


@shamela.cache_kitab()
def _lokal():
    """Himpunan nomor kitab lokal; dikosongkan otomatis oleh `shamela.lepas`."""
    return frozenset(shamela.punya())


def judul_shamela(isi):
    """Judul kitab Shamela yang disebut di catatan kaki: (judul, nomor yang persis, nomor yang mirip).
    Persis = bagian pertama catatan kaki (sampai tanda baca; tempat judul) utuh sama dengan judul katalog, atau judul
    itu disusul pengarang («رسالة في القضاء والقدر للشيخ …»). Selain itu = mirip: banyak judul penelitian diawali
    istilah yang juga judul kitab («الزواج» di «الزواج لدى المسلمين»), dan bagian lain bisa nama orang (muhaqqiq)."""
    mirip_awal = ("", [], [])
    bagian_isi = [b for b in PEMISAH_RUJUKAN.split(AWALAN_RUJUKAN.sub("", isi.strip())) if b.strip()]  # «…»/(…) di awal
    for i, bagian in enumerate(bagian_isi):
        kata = bagian.split()
        for n in range(len(kata), 0, -1):
            judul = " ".join(kata[:n])
            persis, mirip = shamela.nomor_judul(judul)
            # judul satu kata (السعادة، الخلافة) terlalu umum: buku luar bisa berjudul sama. Di bagian sesudah yang pertama
            # (mis. «ابن عثيمين، رسالة في القضاء والقدر») hanya judul kitab yang sudah diunduh: yang itu pasti bisa dicek
            utuh = persis and n >= 2 and (n == len(kata) or PENGARANG_SESUDAH.match(kata[n])) and (i == 0 or any(s in _lokal() for s in persis))
            if utuh and not judul.startswith(MAJALAH):
                return judul, persis, []
            if (persis or mirip) and not mirip_awal[0]:
                mirip_awal = (judul, [], persis + mirip)
    return mirip_awal


def judul_kitab(k, sid_bukti):
    """Kutipan di catatan kaki yang berupa judul kitab Shamela (boleh disusul pengarang: «"شرح … لابن عثيمين"»): judul
    itu persis di awal kutipan, dan sisa sesudah tanda bacanya pendek (bukan teks lain yang diselipi judul). Judul cetak
    lengkap kitab buktinya sendiri («رياض الصالحين من كلام سيد المرسلين») juga judul."""
    judul, persis, mirip = judul_shamela(k)
    if not (persis or mirip) or not k.strip().startswith(judul):
        return False
    sisa = PEMISAH_RUJUKAN.split(k.strip()[len(judul):], 1)
    if len(sisa[0].split()) > 5:  # sesudah judul hanya pengarang («للشيخ محمد بن صالح العثيمين»), bukan kalimat
        return False
    if not persis:  # awal judul katalog («شرح العقيدة الواسطية»): hanya kalau sisanya pengarang, bukan kalimat lain
        kata = sisa[0].split()
        if len(judul.split()) < 2 or kata and not PENGARANG_SESUDAH.match(kata[0]) and not (len(kata) <= 4 and set(mirip) & {int(x) for x in sid_bukti if x.isdigit()}):
            return False
    return len(sisa) < 2 or len(sisa[1].split()) < 4


def kata_rujukan(teks):
    """Kata bentuk sama (`norma.norm`) sebuah judul atau baris #R, tanpa tanda baca dan tanda tebal/miring: «التنزيل،»
    = «التنزيل»; angka dipisah dari huruf («1407هـ» = «1407» + «هـ»); kata Latin (judul penelitian, nomor fatwa
    «DSN-MUI») tanpa besar-kecil, di tempatnya (`norma.norm` membuang huruf Latin)."""
    kata = []
    for k in re.findall(r"[0-9]+|[A-Za-z]+|[^\sA-Za-z0-9]+", teks.translate(ANGKA_LATIN).replace("ـ", "")):
        kata += [k.lower()] if k.isascii() and k.isalnum() else re.findall(r"[0-9]+|[ء-ي]+", norma.norm(k))
    return kata


def termuat(bagian, baris):
    """Deret kata `bagian` (judul, pengarang) ada utuh dan berurutan di `baris` (keduanya hasil `kata_rujukan`)."""
    n = len(bagian)
    return bool(n) and any(baris[i:i + n] == bagian for i in range(len(baris) - n + 1))


RUJUK_ULANG = re.compile(r"السابق|نفسه|المرجع|المصدر")  # «المرجع السابق»، «المصدر نفسه»: bukan judul


def _bagian(isi):
    """Bagian catatan kaki atau baris #R di antara tanda baca, tanpa «انظر:» dan bukti <<…>>."""
    isi = AWALAN_RUJUKAN.sub("", re.sub(r"<<[^<>]*>>", " ", isi).replace("**", "").replace("__", "").strip())
    return [b.strip() for b in PEMISAH_RUJUKAN.split(isi) if b.strip()]


def _tertulis(isi):
    """(judul, pengarang) seperti ditulis di catatan kaki: bagian pertama dan kedua sesudah «انظر:». Catatan kaki takhrij
    («أخرجه البخاري، كتاب …») dan rujukan ulang tidak menulis judul."""
    bagian = _bagian(isi)
    if not bagian or TAKHRIJ_OLEH.search(bagian[0]) or re.match(r"(?:أخرج|رو[ىا])", bagian[0]) or RUJUK_ULANG.search(bagian[0]):
        return None, None
    return bagian[0], (bagian[1] if len(bagian) > 1 and not RUJUK_ULANG.search(bagian[1]) else None)


def _judul_baris(teks):
    """Judul sebuah baris #R: yang bergaris miring «__…__» (@pustaka_gaya: muallif), atau bagian pertamanya."""
    m = re.search(r"__(.+?)__", teks)
    return kata_rujukan(m[1] if m else (_bagian(teks) or [""])[0])


def _tanpa_judul(teks):
    """Kata baris #R di luar judulnya: tempat nama pengarang («البخاري» di judul «فتح الباري بشرح صحيح البخاري» bukan
    pengarang baris itu)."""
    m = re.search(r"__(.+?)__", teks)
    if m:
        return kata_rujukan(teks[:m.start()] + " " + teks[m.end():])
    bagian = PEMISAH_RUJUKAN.split(AWALAN_RUJUKAN.sub("", teks.replace("**", "").strip()), 1)
    return kata_rujukan(bagian[1] if len(bagian) > 1 else "")


def _judul_kartu(m):
    """Bentuk isi baris «الكتاب:» kartu Shamela (judul cetak lengkap): tanpa keterangan kurung siku, dan (bila ada
    kurung siku seperti «[العِبَر و] ديوان المبتدأ…») juga bentuk tanpa tanda kurungnya dengan «و» tersambung."""
    for b in (m.get("betaka_text") or "").replace("\r", "\n").splitlines():
        label, titik, nilai = b.replace("：", ":").partition(":")
        if titik and norma.HARAKAT.sub("", label).strip() == "الكتاب":
            tanpa = re.sub(r"\[[^\[\]]*\]", " ", nilai).strip()
            if "[" not in nilai:
                return [tanpa] if tanpa else []
            buka = re.sub(r"(?<![ء-ي])و\s+(?=[ء-ي])", "و", nilai.replace("[", " ").replace("]", " ")).strip()
            return [j for j in dict.fromkeys((tanpa, buka)) if j]
    return []


def bentuk_judul(m, tertulis=()):
    """Bentuk judul kitab Shamela `m` (hasil `kata_rujukan`) yang dicari di baris #R: judul katalog dan judul kartu
    (`judul_pokok`: tanpa keterangan edisi dan pengarang tempelan), dan judul seperti ditulis di catatan kakinya
    («الكشاف عن حقائق غوامض التنزيل» untuk kartu «… وعيون الأقاويل في وجوه التأويل»)."""
    judul = shamela.judul_pokok(m.get("title_ar") or "")
    for jk in _judul_kartu(m):
        judul += shamela.judul_pokok(jk)
    judul += list(tertulis)
    return [list(k) for k in dict.fromkeys(tuple(kata_rujukan(j)) for j in judul if j) if k]


def judul_di_baris(bentuk, teks):
    """Baris #R `teks` menyebut kitab berjudul `bentuk` (`bentuk_judul`): salah satu bentuknya termuat utuh, atau judul
    baris itu (dua kata atau lebih) awal salah satu bentuknya: «سلسلة الأحاديث الضعيفة والموضوعة» untuk katalog «… وأثرها
    السيئ في الأمة». Dipakai juga `pustaka`."""
    return skor_judul(bentuk, teks) > 0


def _skor_judul_siap(bentuk, kata, awal):
    return max([len(j) for j in bentuk if termuat(j, kata)]
               + [len(awal) - 0.5 for j in bentuk if len(awal) >= 2 and j[:len(awal)] == awal], default=0)


def skor_judul(bentuk, teks):
    """Panjang padanan judul terbaik `bentuk` di `teks` (jumlah kata; 0 = tidak menyebut): bentuk yang termuat utuh,
    atau judul `teks` yang jadi awal sebuah bentuk (setengah kata lebih rendah: «معاني القرآن» lebih dekat ke kitab
    berjudul persis itu daripada ke «معاني القرآن وإعرابه»)."""
    return _skor_judul_siap(bentuk, kata_rujukan(teks), _judul_baris(teks))


def _kitab_bukti(kunci):
    """(nama untuk pesan, bentuk judul, ciri pengarang) kitab bukti Shamela atau Waqfeya; None kalau belum diunduh
    (`cek` sudah GAGAL di buktinya). Bentuk judul dan ciri pengarang = hasil `kata_rujukan`."""
    if kunci.isdecimal():
        try:
            m = shamela.info(int(kunci))
        except (LookupError, OSError, ValueError, SystemExit):
            return None
        nama, bentuk = m["title_ar"], bentuk_judul(m)
        pengarang = [x.strip() for x in (m.get("main_author_name_ar") or "").split("،")]
    else:
        if not WAQFEYA_BUKTI.fullmatch(f"{kunci}|1|1") or not waqfeya.ada(kunci):
            return None
        d = waqfeya.data(kunci)
        nama, pengarang = d["judul"], [d.get("pengarang") or ""]
        bentuk = [k for k in (kata_rujukan(waqfeya.pokok(d["judul"])), kata_rujukan(d["judul"])) if k]
    ciri = _nama(pengarang)
    return f"«{nama}» (<<{kunci}|…>>)", bentuk, ciri


def _nama(daftar):
    """Ciri pengarang (kata tanpa «ال»: «ابن عثيمين» = «… العثيمين»): nama utuh dan kata terakhirnya (nisbah)."""
    return [c for c in (_tanpa_al(kata_rujukan(x)) for x in daftar + [x.split()[-1] for x in daftar if x.split()]) if c]


def _tanpa_al(kata):
    return [k[2:] if k.startswith("ال") and len(k) > 4 else k for k in kata]


def _padanan(penunjuk, pustaka_baris):
    """(kitab, calon, ciri) tiap kitab berbukti (<<sid|…>>, <<w…|…>>, <<luar|berkas|…>>) di catatan kaki: catatan kaki
    pertamanya, nomor baris #R (`pustaka_baris`: [(nomor, teks)] tanpa القرآن الكريم) yang menyebutnya, dan ciri
    pengarangnya.
    Catatan kaki dipecah di «؛» (beberapa sumber satu hal); tiap bukti dipasangkan dengan bagian yang menyebut judulnya,
    atau dengan satu-satunya bagian kalau catatan kaki itu hanya berbukti satu kitab. Kitab Shamela dan Waqfeya ada di
    #R kalau satu baris menyebut judulnya (`judul_di_baris`: katalog, kartu, atau judul seperti di catatan kakinya) dan
    baris itu menyebut pengarangnya (di luar judulnya: `_tanpa_judul`) atau tidak disebut judul kitab berbukti lain (dua «معاني القرآن»: الفراء dan
    الأخفش). PDF luar (tanpa kartu) ada kalau judul seperti ditulis di catatan kakinya disebut satu baris #R
    (`judul_di_baris`), atau satu bagian catatan kakinya yang tiga kata atau lebih (judul penelitian, nama peneliti), di
    luar bagian milik kitab lain, termuat utuh di tepat satu baris #R."""
    baris = {n: kata_rujukan(t) for n, t in pustaka_baris}
    awal_baris = {n: _judul_baris(t) for n, t in pustaka_baris}
    kitab, data = {}, {}  # kunci -> catatan kaki pertama, judul/pengarang tertulis, bagian; kunci -> _kitab_bukti
    for p in penunjuk:
        if "bukti" not in p:
            continue
        sumber = [[x.strip() for x in b.split("|")] for b in p["bukti"]]
        bagian = [b for b in re.sub(r"<<[^<>]*>>", " ", p.get("catatan") or "").split("؛") if b.strip()]
        # <<luar>> tanpa berkas: sumbernya dikenali dari dua bagian pertama catatan kakinya (lembaga + judul keputusan)
        tanpa_berkas = "، ".join(_bagian(bagian[0] if bagian else "")[:2])
        semua = list(dict.fromkeys(f"{LUAR}|{s[1] if len(s) > 1 and s[1] else tanpa_berkas}" if s[0] == LUAR else s[0]
                                   for s in sumber))
        for kunci in semua:
            if kunci not in data:
                data[kunci] = None if kunci.startswith(f"{LUAR}|") else _kitab_bukti(kunci)
        # tiap bagian milik kitab dengan padanan judul terpanjang; seri diputus pengarang katalog yang disebut bagian itu
        punya = {k: [] for k in semua}
        for b in bagian:
            kb_b, aw_b = kata_rujukan(b), _judul_baris(b)
            skor = {k: _skor_judul_siap(data[k][1], kb_b, aw_b) for k in semua if data[k]}
            puncak = [k for k, v in skor.items() if v and v == max(skor.values())]
            if len(puncak) > 1:
                kb = _tanpa_al(kb_b)
                puncak = [k for k in puncak if any(termuat(c, kb) for c in data[k][2])]
            if len(puncak) == 1:
                punya[puncak[0]].append(b)
        diklaim = {id(b) for bb in punya.values() for b in bb}
        # PDF luar: bagian yang tidak milik kitab lain; beberapa PDF dengan bagian sebanyak itu = berpasangan urut
        luar = [k for k in semua if k.startswith(f"{LUAR}|")]
        sisa = [b for b in bagian if id(b) not in diklaim]
        for kunci in semua:
            k = kitab.setdefault(kunci, {"n": p["n"], "tertulis": [], "pengarang": [], "bagian": []})
            if kunci.startswith(f"{LUAR}|"):
                milik = [sisa[luar.index(kunci)]] if len(luar) > 1 and len(sisa) == len(luar) else sisa
            else:
                milik = punya[kunci] or (bagian if len(semua) == 1 else [])
            for b in milik:
                judul, pengarang = _tertulis(b)
                k["tertulis"] += [judul] if judul else []
                k["pengarang"] += [pengarang] if pengarang else []
                k["bagian"] += _bagian(b)
    calon, ciri = {}, {}
    for kunci, k in kitab.items():
        if data.get(kunci):
            k["nama"], bentuk, ciri[kunci] = data[kunci]
            bentuk = bentuk + [kb for kb in map(kata_rujukan, k["tertulis"]) if kb]
            ciri[kunci] = ciri[kunci] + _nama(k["pengarang"])
            calon[kunci] = {n for n, _ in pustaka_baris if _skor_judul_siap(bentuk, baris[n], awal_baris[n]) > 0}
        elif kunci.startswith(f"{LUAR}|"):
            judul = [kb for kb in map(kata_rujukan, k["tertulis"]) if kb]
            if sum(_skor_judul_siap(judul, baris[n], awal_baris[n]) > 0 for n, _ in pustaka_baris) > 1:
                judul = []  # «بنك إندونيسيا»: lembaga atau peneliti di tempat judul, disebut banyak baris
            bentuk = [kb for kb in map(kata_rujukan, k["bagian"]) if sum(not x.isdecimal() for x in kb) >= 3]
            if not judul and not bentuk:
                continue  # catatan kakinya hanya merujuk ulang atau ringkas: tidak ada judul untuk dicari
            # bagian yang ada di banyak baris (penerbit, nama jurnal, kampus) tidak menunjuk satu sumber
            bentuk = [j for j in bentuk if sum(termuat(j, kb) for kb in baris.values()) == 1]
            k["nama"] = f"«{(k['tertulis'] or k['bagian'])[0]}» (<<{kunci}|…>>)"
            calon[kunci] = {n for n, _ in pustaka_baris if judul and _skor_judul_siap(judul, baris[n], awal_baris[n]) > 0
                            or any(termuat(j, baris[n]) for j in bentuk)}
    return kitab, calon, ciri


def kitab_tanpa_pustaka(penunjuk, pustaka_baris):
    """Perhatian tiap kitab berbukti (<<sid|…>>, <<w…|…>>, <<luar|berkas|…>>) di catatan kaki yang tidak ada di baris #R
    (`pustaka_baris`: [(nomor, teks)] tanpa القرآن الكريم); padanannya: `_padanan`."""
    kitab, calon, ciri = _padanan(penunjuk, pustaka_baris)
    pengarang_baris = {n: _tanpa_al(_tanpa_judul(t)) for n, t in pustaka_baris}
    hasil = []
    for kunci, nn in calon.items():
        lain = set().union(*(v for x, v in calon.items() if x != kunci))
        disebut = any(termuat(c, pengarang_baris[n]) for n in nn for c in ciri.get(kunci, ()))
        if disebut or nn - lain or nn and kunci not in ciri:
            continue
        hasil.append(f"baris {kitab[kunci]['n']}: kitab {kitab[kunci]['nama']} dirujuk di catatan kaki tetapi tidak ada di "
                     "المصادر والمراجع (#R)" + (" (judulnya ada di #R, tetapi barisnya milik kitab lain berjudul sama)" if nn else "")
                     + ": tambahkan barisnya ke #R; draf dan data cetaknya: " + perintah("pustaka <folder>"))
    return hasil


def kitab_waqfeya(isi, kitab, *, cek_shamela=True):
    """Perhatian catatan kaki yang buktinya memuat kitab Waqfeya (kitab = nomor «w…»-nya): judul kitab bukti yang tidak
    disebut (seperti kitab_lain untuk bukti Shamela), dan judul yang ternyata ada di Shamela (bila bukan campuran)."""
    hasil = []
    for w in kitab:
        if waqfeya.ada(w) and not waqfeya.judul_disebut(w, isi):
            hasil.append(f"catatan kaki tidak menyebut judul kitab buktinya «{waqfeya.data(w)['judul']}» "
                         f"(<<{w}|…>>): tulis judulnya, atau betulkan nomor kitab di bukti{ekor(isi)}")
    if cek_shamela:
        judul, persis, _ = judul_shamela(isi)
        if persis:  # Waqfeya hanya untuk kitab yang tidak ada di Shamela: teks Shamela dicek `cek`, OCR tidak
            hasil.append(f"«{judul}» ada di Shamela (nomor {'، '.join(map(str, persis))}): kalau edisinya sama, "
                         f"ambil kitab Shamela itu lalu tulis <<sid|juz|hal>> (dicek `cek`); edisi Waqfeya sengaja "
                         f"dipakai (mis. edisi yang diminta dosen) → «terima <kode> <alasan>»{ekor(isi)}")
    return hasil


MUKHARRIJ_KATA = [kata_rujukan(b) for bb in MUKHARRIJ for b in bb]


def pustaka_tak_dirujuk(penunjuk, pustaka_baris, catatan):
    """Perhatian baris #R (`pustaka_baris`) yang tidak dirujuk catatan kaki mana pun (`catatan`: teks tiap catatan kaki):
    kitab yang «ليست لها صلة بالبحث؛ وإنما توضع لمجرد شهرتها» (أبو سليمان، كتابة البحث العلمي، ص203-204). Dirujuk = dipadankan ke kitab berbukti (`_padanan`),
    judulnya utuh, dua kata pertamanya (judul ringkas), atau empat kata berurutan darinya ada di sebuah catatan kaki,
    atau judulnya memuat nama
    mukharrij yang disebut catatan kaki takhrij («صحيح البخاري» untuk «أخرجه البخاري»). Satu kalimat untuk semua baris
    (gabung_kembar menjadikannya satu baris «baris n, m: …»)."""
    _, calon, _ = _padanan(penunjuk, pustaka_baris)
    terpakai = set().union(*calon.values())
    kata_fn = [kata_rujukan(re.sub(r"<<[^<>]*>>", " ", t)) for t in catatan]
    takhrij = [k for t, k in zip(catatan, kata_fn) if TAKHRIJ_AWAL.match(t)]
    mukharrij = [m for m in MUKHARRIJ_KATA if any(termuat(m, k) for k in takhrij)]
    hasil = []
    for n, t in pustaka_baris:
        judul = _judul_baris(t)
        if n in terpakai or not judul or any(termuat(m, judul) for m in mukharrij):
            continue
        # judul utuh, dua kata pertamanya, atau empat kata berurutan darinya («قرار مجمع الفقه الإسلامي الدولي رقم 139»
        # untuk catatan kaki «مجمع الفقه الإسلامي الدولي، قرار رقم 139»)
        potong = [judul, judul[:2]] + [judul[i:i + 4] for i in range(len(judul) - 3)]
        if any(termuat(p, k) for k in kata_fn for p in potong):
            continue
        hasil.append(f"baris {n}: baris المصادر والمراجع ini tidak dirujuk di catatan kaki mana pun: hapus kalau memang "
                     f"tidak dipakai, atau rujuk di tempat yang memakainya (أبو سليمان، كتابة البحث العلمي، ص203-204)")
    return hasil
