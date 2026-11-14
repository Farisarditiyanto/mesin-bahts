# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hadits: kepala hadits bernomor di kitab, nomor takhrij «رقم الحديث (n)», derajat hadits dan penghukumnya,
serta طرف/rawi {H:} yang harus terbaca di halaman bukti."""
import functools, re

import norma
import shamela
from dasar import ANGKA_LATIN, ELIPSIS, POTONGAN_MIN, TAKHRIJ_AWAL
from kitab_lokal import bagian_kitab, bersih_hadits, kepala_hadits, rekaman

# «رقم الحديث (2408)، 4/1873», «برقم 2205، 2/262», «رقم: 27، ص24» (kitab satu jilid): nomor tepat sebelum juz/halaman
# tercetak, jadi bukan nomor riwayat kitab lain di takhrij itu. Dibaca sesudah angka Arab diganti 0-9.
TAKHRIJ = re.compile(r"رقم(?:\s+الحديث)?\s*:?\s*(?:\(\s*(\d+)[^()]*\)|(\d+))[،,\s]*(?:(\d+)\s*/\s*(\d+)|ص\.?\s*(\d+))")
# derajat hadits, kata utuh di teks `norm`: bentuk tertulis -> derajatnya. «صحيح البخاري», «ضعيف الجامع» = judul kitab;
# «الحسن»/«الصحيح» (ber-ال) = nama atau «kitab sahih», bukan derajat
DERAJAT = {"صحيح": "صحيح", "صححه": "صحيح", "حسن": "حسن", "حسنه": "حسن", "ضعيف": "ضعيف", "ضعفه": "ضعيف",
           "موضوع": "موضوع", "منكر": "منكر"}
DITERIMA = frozenset(("صحيح", "حسن"))  # lawannya: ضعيف، موضوع، منكر
# Judul hanya untuk kata benda: «صحيح ابن حبان» judul, «صححه ابن حبان»/«حسنه الترمذي» derajat. `norm` menulis «ابن» «بن».
KATA_DERAJAT = re.compile(r"(?<![ء-ي])[وف]?(?:(%s)(?![ء-ي])(?!\s+(?:البخاري|مسلم|الجامع|سنن|ا?بن|ابي|الامام|الترمذي"
                          r"|النسا[يئ]ي|الترغيب|الادب|المسند|موارد))|(%s)(?![ء-ي]))"
                          % ("|".join(k for k in DERAJAT if not k.endswith("ه")), "|".join(k for k in DERAJAT if k.endswith("ه"))))
SHAHIHAIN = re.compile(r"(?<![ء-ي])(?:البخاري|مسلم|الشيخان|الشيخين|الصحيحين|متفق عليه)(?![ء-ي])")  # teks `norm`
# «ولم أقف على حكم لأهل العلم على إسناده»: derajat yang memang tidak ditemukan, ditulis terus terang
DERAJAT_TIDAK_ADA = re.compile(r"لم (?:اقف|اجد) علي (?:من )?(?:حكم|صحح|ضعف|درج)")
MUNDUR_KEPALA = 3  # halaman ke belakang tempat kepala hadits yang dinukil masih dicari


@functools.cache
def hadits_bernomor(sid, juz, p1, p2, nomor):
    """(rr, ruas): rekaman di sekitar juz/p1-p2 (hadits bisa mulai beberapa halaman sebelum lafaz yang dinukil) dan
    [(matan, حاشية)] tiap kepala `nomor`: matan dari kepala itu sampai kepala hadits berikutnya, حاشية = catatan rekaman
    yang memuat matan itu (di سنن أبي داود ط. الألباني derajat tiap hadits ada di situ). ruas None = halaman tanpa kepala
    hadits (tidak bisa dinilai); [] = nomor itu bukan kepala di sana."""
    # urut halaman: rekaman Shamela kadang tidak berurutan (Ahmad 29: ص299 sebelum ص296)
    rr = sorted(rekaman(sid, juz, max(1, p1 - MUNDUR_KEPALA), p2), key=lambda r: r.get("page_num") or 0)
    tubuh = [r.get("body") or "" for r in rr]
    baris, kepala, batas = kepala_hadits("\n".join(tubuh))
    if not kepala:
        return rr, None
    awal = [0]  # letak awal tiap rekaman di `baris` (_bersih tidak melintasi pemisah «\n»)
    for t in tubuh:
        awal.append(awal[-1] + len(bersih_hadits(t)) + 1)
    catatan = []
    for r, pos in zip(rr, awal):
        halaman = []
        for hal, t in norma.per_halaman(r):
            akhir = pos + len(bersih_hadits(t))
            halaman.append((pos, akhir, hal))
            pos = akhir + 1  # penanda halaman menjadi satu spasi dalam _bersih
        catatan.append((halaman, norma.per_halaman(r, "footnotes")))
    ruas = []
    for a, n in kepala:
        if n == nomor:  # batas hadits = nomor lebih besar: angka kecil di awal baris sesudahnya biasanya daftar dalam syarah
            z = next((x for x, m in batas if x > a and m > nomor), len(baris))
            hasyiah = []
            for halaman, potongan in catatan:
                dipakai = {hal for x, y, hal in halaman if x < z and y > a and baris[max(x, a):min(y, z)].strip()}
                if dipakai:
                    # Tanpa penanda halaman, letak tiap catatan memang tidak tercatat di Shamela.
                    hasyiah += [t for hal, t in potongan if len(potongan) == 1 or hal in dipakai]
            ruas.append((baris[a:z], " ".join(hasyiah)))
    return rr, ruas


def takhrij_janggal(sid, juz, p1, p2, nomor, lafaz):
    """Nomor takhrij tidak cocok dengan kepala hadits di halaman bukti, atau lafaz bukti di hadits lain; None kalau cocok.
    Halaman tanpa kepala hadits tidak bisa dinilai."""
    rr, ruas = hadits_bernomor(sid, juz, p1, p2, nomor)
    if ruas is None:
        return None
    if not ruas:
        return f"nomor takhrij ({nomor}) bukan kepala hadits di sekitar {juz}/{p1}: cocokkan nomornya ke kitab"
    hasyiah = norma.padat(" ".join(r.get("footnotes") or "" for r in rr))  # kalimat muhaqqiq (derajat) bukan bagian hadits
    if any(not any(norma.padat(x) in norma.padat(s) for s, _ in ruas) and norma.padat(x) not in hasyiah for x in lafaz):
        return f"lafaz bukti tidak ada di hadits ({nomor}) sekitar {juz}/{p1}: mungkin nomornya milik hadits lain"


def periksa_takhrij(isi, bukti, terbukti, kutipan, perhatian):
    """Nomor takhrij yang tercetak tepat di depan juz/halaman sebuah bukti dicocokkan ke kitabnya; lafaz = potongan bukti, atau kutipan.
    Hasilnya {bukti (sid, juz, p1, p2): nomor takhrijnya}, untuk periksa_derajat."""
    bernomor = {}
    for bagian, bb in bagian_kitab(isi, terbukti) if re.search("أخرج|رواه", isi) else ():
        for m in TAKHRIJ.finditer(bagian.translate(ANGKA_LATIN)):
            nomor, juz, hal = m[1] or m[2], m[3], m[4] or m[5]  # «ص n» (juz None): kitab satu jilid, juz bukti apa saja
            for f in map(lambda b: b.split("|"), bukti):
                p1, _, p2 = f[2].partition("-") if len(f) > 2 else ("", "", "")
                if len(f) < 3 or juz not in (None, f[1]) or p1 != hal or (f[0], f[1], int(p1), int(p2 or p1)) not in bb:
                    continue
                bernomor.setdefault((f[0], f[1], int(p1), int(p2 or p1)), int(nomor))
                # kutipan hanya diikutkan kalau memang dicek ke bukti ini; #nomor tidak membawa lafaz
                sumber = (kutipan or "") if len(f) == 3 else "" if f[3].startswith("#") else f[3]
                lafaz = [x for x in ELIPSIS.split(re.sub(r"\{Q:[^}]*\}", " ", sumber)) if len(norma.padat(x)) >= POTONGAN_MIN]
                pesan = takhrij_janggal(int(f[0]), f[1], int(p1), int(p2 or p1), int(nomor), lafaz)
                if pesan and f"{pesan}  || fn: {isi[:45]}" not in perhatian:
                    perhatian.append(f"{pesan}  || fn: {isi[:45]}")
    return bernomor


def derajat(teks):
    """Derajat hadits yang tertulis di teks (lihat KATA_DERAJAT): {صحيح, حسن, ضعيف, موضوع, منكر}."""
    return {DERAJAT[m[1] or m[2]] for m in KATA_DERAJAT.finditer(norma.norm(teks))}


def periksa_derajat(isi, terbukti, bernomor, galat, perhatian):
    """Catatan kaki takhrij («أخرجه/رواه …», AGENTS.md aturan takhrij): di luar Shahihain derajatnya wajib ditulis, dan
    derajat yang ditulis harus terbaca di salah satu halaman buktinya. Bukti bernomor takhrij: di matan dan حاشية hadits
    nomor itu; bukti lain (mis. «صححه الألباني في …» dengan buktinya sendiri): di seluruh halamannya, matan dan حاشية.
    Yang terbaca hanya derajat lawannya (صحيح/حسن vs ضعيف/موضوع/منكر) = GAGAL; tidak terbaca sama sekali = perhatian.
    Derajat yang tidak ditulis sama sekali = GAGAL: selalu bisa dibereskan, kalau perlu dengan «ولم أقف على حكم …»."""
    if not TAKHRIJ_AWAL.match(isi) or not terbukti:
        return
    tulis = derajat(re.sub(r"<<[^>]*>>", " ", isi))
    if not tulis:
        n = norma.norm(isi)
        if not SHAHIHAIN.search(n) and not DERAJAT_TIDAK_ADA.search(n):
            galat.append(f"derajat hadits belum ditulis: di luar Shahihain tulis derajatnya beserta siapa yang menghukumi "
                         f"(«وصححه الألباني»، «وقال الترمذي: حديث حسن») dari kitab yang dibaca sendiri, atau terus terang "
                         f"«ولم أقف على حكم لأهل العلم على إسناده»  || fn: {isi[:45]}")
        return
    terbaca = set()
    for b in terbukti:
        ruas = hadits_bernomor(int(b[0]), b[1], b[2], b[3], bernomor[b])[1] if b in bernomor else None
        if ruas:
            teks = " ".join(m + " " + h for m, h in ruas)
        else:  # tanpa nomor, atau nomornya tidak terbaca di sana (sudah jadi perhatian nomor takhrij)
            # حاشية tanpa penanda halaman (satu potongan) milik seluruh rekaman, sama dengan hadits_bernomor
            teks = " ".join(t for r in rekaman(int(b[0]), b[1], b[2], b[3]) for sisi, _ in norma.BAGIAN
                            for pp in [norma.per_halaman(r, sisi)] for hal, t in pp
                            if hal is None or b[2] <= hal <= b[3] or (sisi == "footnotes" and len(pp) == 1))
        terbaca |= derajat(teks)
    if tulis <= terbaca:
        return
    tulis_ = "، ".join(sorted(tulis - terbaca))
    if terbaca and not terbaca & {d for d in DERAJAT.values() if (d in DITERIMA) == bool(tulis & DITERIMA)}:
        galat.append(f"derajat hadits «{tulis_}» berlawanan dengan yang terbaca di halaman bukti («{'، '.join(sorted(terbaca))}»): "
                     f"tulis derajat dari kitabnya, atau beri bukti <<sid|juz|hal>> kitab yang menghukuminya begitu  || fn: {isi[:45]}")
    else:
        perhatian.append(f"derajat hadits «{tulis_}» tidak terbaca di halaman bukti (matan atau حاشية dekat hadits itu): beri bukti "
                         f"<<sid|juz|hal>> kitab yang menghukuminya, atau betulkan derajatnya  || fn: {isi[:45]}")


BUKAN_NAMA_RAWI = frozenset(map(norma.padat, "بن ابن بنت أبو أبي أبا أم عبد الله الرحمن رضي عنه عنها عنهما عنهم".split()))
DIA = re.compile(r"\s*[وف]?(?:عنه|عنها|عنهما|عنهم|بهذا|به)(?![ء-ي])")  # awal hadits yang menunjuk rawi hadits sebelumnya
TARAF_KATA = 3  # huruf `padat` paling sedikit kata طرف yang dihitung («لا», «من» ada di mana-mana)
TARAF_SEPARUH = 0.5  # bagian kata طرف yang harus terbaca; kurang dari ini = GAGAL (hadits lain)


def hadits_janggal(h, terbukti, sekitar):
    """{H:طرف|راوٍ|kunci} dicocokkan ke teks naskah sejak catatan kaki sebelumnya (`sekitar`: kutipan hadits dan
    pengantarnya) dan halaman bukti catatan kaki berikutnya (dari MUNDUR_KEPALA halaman sebelumnya, karena awal hadits bisa
    di halaman sebelum lafaz yang dinukil, sampai satu halaman sesudahnya): (galat, perhatian). طرف boleh gabungan potongan hadits («كخ كخ، أما شعرت…»),
    jadi yang dihitung katanya: semua terbaca = cocok; kurang dari TARAF_SEPARUH = GAGAL (فهرس الأحاديث mencetak hadits
    lain); di antaranya = perhatian. Rawi dicari di hadits yang memuat kutipan itu (dipotong di nomor hadits), menurut
    namanya yang khas («أبو هريرة» → «هريرة»); «ابن مسعود» dan «عبد الله بن عمر» juga cocok dengan «عبد الله» (kitab
    hadits menyebut العبادلة begitu). Tidak terbaca = perhatian."""
    # sanad dan lafaz hadits bisa berlanjut ke halaman sesudah halaman bukti (Muslim 2/943: «سمع جابر» di 944)
    rujukan = [rekaman(int(s), z, max(1, a - MUNDUR_KEPALA), b + 1) for s, z, a, b in terbukti]
    teks = " ".join(r.get(b) or "" for rr in rujukan for r in rr for b in ("body", "footnotes"))
    kata = lambda t: [norma.padat(w) for w in norma.norm(t).split()]  # norm: «عز وجل»/«﷿» dibuang di kedua sisi
    lepas = lambda ww: ww | {w[1:] for w in ww if w[:1] in shamela.SAMBUNG}  # «وإني» di kitab = «إني» di طرف
    di_kitab = lepas(set(kata(teks)))
    ada = di_kitab | lepas(set(kata(sekitar)))
    terbaca = lambda w, ada: w in ada or w[:1] in shamela.SAMBUNG and w[1:] in ada
    taraf = [w for w in dict.fromkeys(kata(h["t"])) if len(w) >= TARAF_KATA]
    hilang = [w for w in taraf if not terbaca(w, ada)]
    galat = perhatian = None
    if taraf and hilang:
        pesan = f"طرف {{H:{h['t'][:30]}|…}}: {len(hilang)} dari {len(taraf)} katanya tidak terbaca di kutipan maupun di halaman bukti catatan kakinya"
        if len(hilang) > len(taraf) * (1 - TARAF_SEPARUH):
            galat = f"{pesan}: فهرس الأحاديث akan mencetak hadits lain; salin طرف dari awal lafaz hadits yang dikutip"
        else:
            perhatian = f"{pesan}: pastikan طرف memang lafaz hadits ini"
    # rawi dicari di hadits itu sendiri: halaman bukti (dan sekitarnya) dipotong di nomor hadits («٣ - وعن عائشة…»), lalu
    # dipakai potongan yang memuat awal kutipan (atau طرف). «أنس» di hadits lain sehalaman, atau «مالك» di isnad halaman
    # sesudahnya, bukan rawi hadits ini. Tanpa potongan yang memuat kutipan: seluruh halaman bukti itu sendiri.
    # Rekaman disambung tanpa spasi: Shamela bisa memotong satu kata di batas halaman («جابر|َ» di Muslim 2/943-944)
    jejak = norma.padat(h.get("kutipan") or h["t"])[:20]
    blok = []
    for rr in rujukan:
        raw = norma.TAGS.sub(" ", "".join(r.get("body") or "" for r in rr))
        pp = NOMOR_DI_KITAB.split(raw)
        for i, x in enumerate(pp):
            if jejak and jejak in norma.padat(x):
                k = i  # «وعنه قال…» (berantai): rawinya disebut di hadits sebelumnya (مجمع الزوائد)
                while k and DIA.match(norma.HARAKAT.sub("", pp[k])):
                    k -= 1
                blok.append("".join(pp[k:i + 1]))
    if not blok:
        blok = ["".join(r.get("body") or "" for s, z, a, b_ in terbukti for r in rekaman(int(s), z, a, b_))]
    rawi = kata(h["r"])
    # nama khas: kata pertama dan kata sesudah «بن/أبي/أم…» («أنس بن مالك» → أنس، مالك; «أبو هريرة» → هريرة); satu saja
    # cukup, karena isnad sering hanya «عن أنس» atau «عن المقدام»
    wajib = [w for i, w in enumerate(rawi) if w not in BUKAN_NAMA_RAWI and (i == 0 or rawi[i - 1] in BUKAN_NAMA_RAWI)]
    abadilah = rawi[:1] == kata("ابن") or rawi[:2] == kata("عبد الله")

    def di_blok(x):
        ww = lepas(set(kata(x)))
        ww |= {w[:-1] for w in ww if w.endswith("ا")}  # «سمع جابرا»
        return any(terbaca(w, ww) for w in wajib) or abadilah and norma.padat("عبد الله") in norma.padat(x)
    if not galat and terbukti and wajib and not any(map(di_blok, blok)):
        perhatian = perhatian or (f"rawi «{h['r']}» di {{H:…|{h['r']}|…}} tidak terbaca di halaman bukti catatan kakinya: "
                                  f"pastikan sahabat yang meriwayatkan hadits itu")
    return galat, perhatian


NOMOR_DI_KITAB = re.compile(r"(?<![\d٠-٩/])[\d٠-٩]+(?:\s*/\s*[\d٠-٩]+)?\s*-\s*(?=[ء-ي(])")  # «٢٤٢ - وعنه»


def hadits_lain(sid, juz, p1, p2, kutipan_h, mk):
    """Di halaman p1..p2, kutipan {H:} dan mk hanya ditemukan di hadits bernomor yang berbeda («٢٤٢ - …» vs «٢٤٤ - …»)."""
    raw = norma.TAGS.sub(" ", "\n".join(r.get("body") or "" for r in rekaman(sid, juz, p1, p2)))
    blok = [norma.padat(x) for x in NOMOR_DI_KITAB.split(raw)]
    qh, qm = norma.padat(kutipan_h)[:20], norma.padat(mk)[:20]
    ih, im = {i for i, x in enumerate(blok) if qh and qh in x}, {i for i, x in enumerate(blok) if qm and qm in x}
    return len(blok) > 1 and bool(ih) and bool(im) and not ih & im
