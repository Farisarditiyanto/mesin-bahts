# SPDX-License-Identifier: AGPL-3.0-or-later
"""Yang tercetak di catatan kaki dibandingkan dengan buktinya: juz/halaman dan nomor hadits, judul kitab dan
pengarang (kitab lain = GAGAL), dan judul kitab Shamela yang ditulis sebagai <<luar>>."""
import re

import norma
import shamela
from dasar import ANGKA_LATIN, RENTANG_MAKS
from kitab_lokal import bagian_kitab, kitab_meta, rekaman
from laporan import ringkas_rentang

# mukharrij yang namanya ditulis sesudah «أخرجه/رواه»: bentuk-bentuk tulisannya (i'rab, ejaan). Kitab bukti yang judul
# atau pengarangnya memuat salah satu bentuk itu = kitab mukharrij itu, syarahnya, atau takhrij/ringkasannya
MUKHARRIJ = (("البخاري",), ("مسلم",), ("أبو داود", "أبي داود", "أبا داود"), ("الترمذي",), ("النسائي",),
             ("ابن ماجه", "ابن ماجة"), ("أحمد",), ("مالك",), ("الدارمي",), ("ابن حبان",), ("الحاكم",), ("البيهقي",),
             ("الطبراني",), ("ابن خزيمة",), ("الدارقطني",), ("ابن أبي شيبة",), ("عبد الرزاق",))
TAKHRIJ_OLEH = re.compile(r"(?<!\w)(?:أخرج|خرج|رو[ىا])(?:ه|ها|هما|اه)?\s+(?:الإمام\s+|الحافظ\s+)?("
                          + "|".join(re.escape(b) for bb in MUKHARRIJ for b in sorted(bb, key=len, reverse=True)) + r")(?!\w)")


def _nama_kitab(m):
    """(judul, pengarang): bentuk `padat` yang menandai kitab bukti (metadata m) disebut di catatan kaki. Judul = dua kata
    awal tiap judulnya (judul katalog bisa «تفسير السعدي = تيسير الكريم الرحمن»; pengarang yang ditempel di judul
    dibuang; judul satu kata = kata itu). Pengarang = nama utuh dan kata terakhirnya (nisbah: «أبو إسحاق الشاطبي» ditulis
    «الشاطبي»)."""
    judul, pengarang = [], []
    for j in shamela.judul_pokok(m["title_ar"]):
        judul.append(" ".join(shamela.kata_judul(j)[:2]))
    for p in (m.get("main_author_name_ar") or "").split("،"):
        pengarang += [p, p.split()[-1]] if p.split() else []
    rapi = lambda xx: {x for x in map(norma.padat, xx) if len(x) >= 3}
    return rapi(judul), rapi(pengarang)


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
    data = [shamela.info(int(s)) for s in dict.fromkeys(sid_bukti)]
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
            if (not matan and not set(nomor) & {int(s) for s in sid_bukti} and norma.padat(judul) not in milik_judul
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
    «ص: 5» dan «الصفحة 5» sama dengan «ص5».
    Halaman bahts sendiri («ص3 من هذا البحث», «ص3 من البحث», «ص3 من هذه الرسالة/المذكرة») bukan halaman kitab."""
    isi = re.sub(r"\d+(?:\s*(?:[-–]|[،,]\s*و?|\s+و)\s*\d+)*\s*(?=من\s+(?:(?:هذا\s+)?البحث|هذه\s+(?:الرسالة|المذكرة)))",
                 " ", isi.translate(ANGKA_LATIN))
    rentang = r"\d+(?:\s*[-–]\s*\d+)?"
    tahun = r"(?:1[34]|19|20)\d\d(?!\d|\s*[-–])"  # «ص5، 1423»: tahun cetak tanpa هـ, bukan halaman kedua
    daftar = rf"(?:\s*(?:[،,]\s*و?|\s+و)\s*(?!{tahun}){rentang}(?![\d/]|\s*/|\s*(?:هـ|ه(?!\w)|م(?!\w))))*"
    if juz == "-":
        pola = rf"(?<![\wـ])(?:[وف]?ص|الصفحة)\s*:?\s*({rentang}{daftar})"
    else:
        pola = rf"(?<![\d/]){re.escape(juz)}\s*/\s*({rentang}{daftar})"
    return [(int(a), int(b or a)) for m in re.findall(pola, isi) for a, b in re.findall(r"(\d+)(?:\s*[-–]\s*(\d+))?", m)]


# «j/n» juz mana saja; bukan tanggal («12/5/1420», «1420هـ/2000م») atau cetakan («ط2/1420»)
# nomor hadits «رقم (5/ 103)», «الحديث 5/103» (nomor bab/hadits seperti cetakan سبل السلام) bukan juz/halaman
NOMOR_HADITS = re.compile(r"(?:رقم|حديث)(?:\s*الحديث)?\s*:?\s*\(?\s*\d+\s*/\s*\d+\s*\)?")
JUZ_TERCETAK = re.compile(r"(?<![\w/])(\d{1,2})\s*/\s*\d+(?![\d/])(?!\s*(?:هـ|م(?!\w)))")
# «ج1، ص55», «ج1/ص55», «ج ١ ص ٥٥», «الجزء 1، ص55», «الجزء الأول، الصفحة 55» (sesudah ANGKA_LATIN) = «1/55»
URUTAN = {"الأول": 1, "الاول": 1, "الثاني": 2, "الثالث": 3, "الرابع": 4, "الخامس": 5, "السادس": 6, "السابع": 7,
          "الثامن": 8, "التاسع": 9, "العاشر": 10}
JUZ_ARAB = re.compile(rf"(?<![\wـ])(?:ج|الجزء)\s*:?\s*(\d{{1,2}}|{'|'.join(URUTAN)})\s*[،,/]?\s*(?:ص|الصفحة)\s*:?\s*(?=\d)")


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
MADDA = re.compile(r"(?<![ء-ي])مادة\s*:?\s*[(«\"]?\s*([ء-يً-ْ]+)|\(\s*([ء-يً-ْ]+)\s*\)")


def madda(teks, bb):
    """Kamus yang dirujuk lewat materinya: (materi, ada di halaman bukti?) untuk materi pertama yang tertulis, atau None
    kalau bukan rujukan kamus. Materinya harus berdiri sebagai kata (boleh berawalan ال) di halaman tiap bukti."""
    if not bb or not all((kitab_meta(int(b[0])) or {}).get("kategori") == MUJAM for b in bb):
        return None
    m = MADDA.search(teks)
    if not m:
        return None
    kata = norma.norm(m[1] or m[2]).strip()
    ada = all(any(re.search(rf"(?<![ء-ي])(?:ال)?{re.escape(kata)}(?![ء-ي])", norma.norm(r.get("body") or ""))
                  for r in rekaman(int(s), z, p1, p2)) for s, z, p1, p2 in bb)
    return kata, ada


def cocok_halaman(isi, bukti, perhatian=None):
    """Bandingkan juz/halaman yang tercetak dengan bukti [(sid, juz, p1, p2)]; kembalikan daftar galat.
    Tiap halaman tercetak harus di dalam rentang bukti kitabnya, dan tiap bukti harus tercetak (kecuali kamus yang
    dirujuk lewat «مادة …»).
    «سبق تخريجه» mencetak halaman bahts ({P:}), bukan halaman kitab: yang dicek hanya halaman kitab yang tercetak."""
    if not bukti:
        return []
    galat = []
    bagian = bagian_kitab(isi, bukti)
    if len(bagian) == 1 and len({b[0] for b in bukti}) > 1 and perhatian is not None and "سبق تخريجه" not in isi:
        perhatian.append(f"catatan kaki merujuk {len({b[0] for b in bukti})} kitab, tetapi judul kitabnya tidak dikenali, jadi "
                         f"halaman tiap kitab tidak bisa dicocokkan dengan buktinya sendiri: tulis judul kitab seperti di "
                         f"katalog (`kartu`), atau pastikan sendiri halaman tiap kitab  || fn: {isi[:45]}")
    for teks, bb in bagian:
        kitabnya = f" (kitab {bb[0][0]})" if len(bagian) > 1 else ""
        juz_bukti = {b[1] for b in bb}
        # juz yang tidak punya bukti sama sekali («3/77» di kitab satu jilid, «ص900» di kitab berjilid)
        utuh = teks.translate(ANGKA_LATIN)  # «عند شرحه للحديث (1/ 222)»: bukti yang tercetak di sini tetap terbaca
        if juz_bukti - {"-"}:  # kitab satu jilid (juz «-»): «ج1، ص55» tetap dibaca «ص55» seperti dulu
            utuh = juz_arab(utuh)
        bernama = [j for j in juz_bukti if j != "-" and not j.isdigit()]
        for j in bernama:  # «المقدمة، ص1» = halaman 1 bagian المقدمة, sama dengan «المقدمة/1»
            utuh = re.sub(rf"(?<!\w){re.escape(j)}\s*[،,:]?\s*ص\s*(?=\d)", f"{j}/", utuh)
        if len(bernama) == 1 and "-" not in juz_bukti:  # «ص5» tanpa nama bagian = halaman bagian buktinya (<<id|الكتاب|5>>)
            utuh = re.sub(r"(?<![\wـ])([وف]?)ص\s*(?=\d)", lambda m: f"{m.group(1)}{bernama[0]}/", utuh)
        teks = NOMOR_HADITS.sub(" ", utuh)
        lain = {j for j in JUZ_TERCETAK.findall(teks)} | {"-"}
        for juz in juz_bukti | (lain - juz_bukti):
            ada = {n for _, z, p1, p2 in bb if z == juz for n in range(p1, p2 + 1)}
            for a, b in tercetak(teks, juz):
                if a < 1 or b < a or b - a > RENTANG_MAKS:
                    galat.append(f"halaman tercetak {juz}/{a}-{b} tidak punya bukti{kitabnya}")
                    continue  # tolak sebelum range dibuat: salah ketik jangan menghabiskan memori
                kurang = sorted(set(range(a, b + 1)) - ada)
                if not kurang:
                    continue
                if len(kurang) == b - a + 1:
                    galat.append(f"halaman tercetak {juz}/{a}{'-' + str(b) if b != a else ''} tidak punya bukti{kitabnya}")
                else:  # «1/36-37» dengan bukti 36 saja
                    sid = next(s for s, z, _, _ in bb if z == juz)
                    galat.append(f"halaman tercetak {juz}/{a}-{b}: bukti belum mencakup {ringkas_rentang(kurang)}{kitabnya}: "
                                 f"lebarkan buktinya (<<{sid}|{juz}|{a}-{b}>>) atau cetak halaman buktinya saja "
                                 f"({juz}/{ringkas_rentang(sorted(set(range(a, b + 1)) & ada))})")
        # kamus yang tersusun menurut huruf (bidang Shamela الغريب والمعاجم) boleh dirujuk lewat materinya «مادة (قدر)»
        # tanpa juz/halaman (أبو سليمان، كتابة البحث العلمي، ص142، 155); materinya harus ada di halaman bukti, dan halaman
        # yang tetap tercetak dicek seperti biasa
        # Materi hanya dinilai kalau halamannya memang tidak tercetak: «(بيروت)» di data cetak bukan materi.
        tak_tercetak = []
        for s, z, p1, p2 in dict.fromkeys(bb) if "سبق تخريجه" not in isi else ():
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
    return [f"{'; '.join(dict.fromkeys(galat))} || fn: {isi[:60]}"] if galat else []  # satu catatan kaki = satu galat


AWALAN_RUJUKAN = re.compile(r"^(?:انظر|ينظر|راجع|كتاب)\s*:?\s*")
PEMISAH_RUJUKAN = re.compile(r"[،,.():؛«»\"\-–]")
MAJALAH = "مجلة"  # judul jurnal: terbitannya belum tentu ada di Shamela, jadi kemiripan judul cukup perhatian
PENGARANG_SESUDAH = shamela.PENGARANG_SESUDAH  # «… للشيخ ابن عثيمين»


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
            utuh = n >= 2 and (n == len(kata) or PENGARANG_SESUDAH.match(kata[n])) and (i == 0 or set(persis) & set(shamela.punya()))
            if persis and utuh and not judul.startswith(MAJALAH):
                return judul, persis, []
            if (persis or mirip) and not mirip_awal[0]:
                mirip_awal = (judul, [], persis + mirip)
    return mirip_awal


def judul_kitab(k, sid_bukti=()):
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
