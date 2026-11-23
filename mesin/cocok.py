# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pencocok kutipan per kata di teks `padat` satu rekaman kitab: letak kutipan, batas kata kitab, halaman cetaknya,
dan matan atau حاشية. Dipakai `cek` (kutipan harus utuh per kata) dan `cari`/`teks`/`bab` (frasa sebagai kata utuh)."""
import re

from norma import BUKAN_ABJAD, PENANDA, TAGS, per_halaman, ruas_halaman, norm, padat

SAMBUNG = "وفبلك"  # huruf sambung di depan kata: kutipan boleh mulai sesudahnya («و"الإحياء"» = «والإحياء»)
NAFI_SAMBUNG = {"ما", "لا", "لم", "لن", "ليس"}  # kutipan tidak boleh mulai dengan kata ini kalau di kitab ia didahului ب/ل


def kunci_frasa(frasa):
    """Bentuk `padat` frasa pencarian; frasa tanpa huruf Arab ditolak dengan pesan."""
    q = padat(frasa)
    if not q:
        raise SystemExit("Frasa pencarian harus berhuruf Arab.")
    return q


def batas_kata(p, bagian):
    """Letak awal dan akhir tiap kata di teks `padat` bagian itu. Dihitung hanya untuk rekaman yang memuat kutipan."""
    kunci = "_kata_" + bagian
    if kunci not in p:
        awal, akhir, n = set(), set(), 0
        add_awal, add_akhir = awal.add, akhir.add
        for _, b in per_halaman(p, bagian):
            for w in norm(b).split():
                if not w.isalpha():
                    w = BUKAN_ABJAD.sub("", w)
                    if not w:
                        continue
                add_awal(n)
                n += len(w)
                add_akhir(n)
        p[kunci] = awal, akhir
    return p[kunci]


def kata_titik_dua(p, bagian="body"):
    """[(kata `padat`, diikuti «:»)] tiap kata bagian rekaman p («قال الشافعي (¬١):» -> الشافعي diikuti «:»).
    Urutannya sama dengan `batas_kata` kalau pemotongan katanya sama; pemakai membandingkan dulu."""
    out = []
    for _, b in per_halaman(p, bagian):
        for t in TAGS.sub(" ", b).split():
            out += [[w, False] for w in (BUKAN_ABJAD.sub("", x) for x in norm(t).split()) if w]
            if out:  # tanda tanpa huruf ikut kata sebelumnya: «(¬١):» -> «:»; «[يوسف: ٨٨] .» -> bukan «:» lagi
                out[-1][1] = bool(re.search(r":\W*$", t))
    return out


def kata_dalam(teks):
    """Letak awal tiap kata kutipan (selain kata pertama) di teks `padat`-nya, dihitung seperti `batas_kata`."""
    out, n = set(), 0
    for w in norm(teks).split():
        if not w.isalpha():
            w = BUKAN_ABJAD.sub("", w)
            if not w:
                continue
        if n:
            out.add(n)
        n += len(w)
    return frozenset(out)


def potongan_utuh(p, bagian, j, k, kata=()):
    """Potongan teks[j:k] mulai dan berakhir di batas kata kitab. Di depannya boleh ada huruf sambung (و ف ب ل ك, paling banyak dua).
    kata = letak awal kata di dalam kutipan (`kata_dalam`): batas kata yang bergeser dari batas kitab tidak dihitung."""
    awal, akhir = batas_kata(p, bagian)
    if k not in akhir or not _sebatas(awal, j, k, kata):
        return False
    if j in awal:
        return True
    teks = ruas_halaman(p, bagian)[0]
    for d in (1, 2):
        if j - d in awal and all(c in SAMBUNG for c in teks[j - d:j]):
            # ك hanya awalan kalau sesudahnya «ال» («كالله»); selain itu hurufnya milik kata («كان», «كأنه»). ب/ل (huruf jar:
            # «لأن»/«بأن» → «أن») bukan awalan di «لكن», «لله» (→ «له»), dan di depan kata nafi («لما», «بلا» → «ما», «لا»)
            awalan, sisa = teks[j - d:j], teks[j:min(a for a in akhir if a > j)]
            if "ك" in awalan:
                return teks.startswith("ال", j)
            if set(awalan) - set("وف") and sisa in NAFI_SAMBUNG:
                return False
            return not ("ل" in awalan and teks.startswith(("ل", "كن"), j))
    return False


def _sebatas(awal, j, k, kata):
    """Batas kata kutipan dan kitab tidak bergeser di antara dua batas yang sama-sama ada: «بل أشك» ≠ «بلا شك».
    Kata yang disambung atau dipisah di satu pihak saja boleh («عبد الله»/«عبدالله», «و الإحياء»)."""
    naskah = kitab = False
    for x in range(j + 1, k):
        di_naskah, di_kitab = x - j in kata, x in awal
        if di_naskah and di_kitab:
            naskah = kitab = False
        else:
            naskah, kitab = naskah or di_naskah, kitab or di_kitab
            if naskah and kitab:
                return False
    return True


def semua_letak(p, q, bagian="body", utuh=False, kata=()):
    """Tiap letak (awal, akhir) q di teks `padat` bagian rekaman p, berurutan."""
    teks = ruas_halaman(p, bagian)[0]
    j = teks.find(q)
    while j >= 0:
        if not utuh or potongan_utuh(p, bagian, j, j + len(q), kata):
            yield j, j + len(q)
        j = teks.find(q, j + 1)


def letak_pertama(p, q, bagian="body", utuh=False, kata=()):
    """Letak (awal, akhir) pertama q di teks `padat` bagian rekaman p; None kalau tidak ada."""
    return next(semua_letak(p, q, bagian, utuh, kata), None)


# Garis pemisah matan dan حاشية di cetakan. Sebagian kitab Shamela menaruh حاشية المحقق di body sesudah garis ini
# (footnotes kosong): teks sesudahnya sampai halaman cetak berikutnya bukan matan.
PEMISAH_CATATAN = re.compile(r"_{5,}")


def catatan_body(t):
    """Ruas [(awal, akhir)] teks asli body t yang sebenarnya حاشية: dari garis pemisah sampai penanda halaman ⦗n⦘
    berikutnya atau akhir teks."""
    out = []
    for m in PEMISAH_CATATAN.finditer(t):
        if not out or m.start() >= out[-1][1]:
            n = PENANDA.search(t, m.end())
            out.append((m.start(), n.start() if n else len(t)))
    return out


def _catatan_padat(p):
    """`catatan_body` rekaman p dalam letak teks `padat` body-nya; dihitung sekali per rekaman."""
    if "_catatan_padat" not in p:
        t = p.get("body") or ""
        p["_catatan_padat"] = [(len(padat(t[:a])), len(padat(t[:z]))) for a, z in catatan_body(t)] if "_" in t else []
    return p["_catatan_padat"]


def halaman_letak(p, bagian, c):
    """Halaman cetak (awal, akhir) letak c = (awal, akhir) di teks `padat` bagian rekaman p; halamannya None kalau rekaman
    itu tidak bernomor halaman."""
    batas = ruas_halaman(p, bagian)[1]
    return (next(h for a, z, h, _ in batas if a <= c[0] < z), next(h for a, z, _, h in batas if a <= c[1] - 1 < z))


def tempat(p, q, bagian="body", utuh=False, kata=(), dalam=None, catatan=None):
    """Halaman cetak (awal, akhir) tempat q (sudah `padat`) berada di rekaman p; None kalau tidak ada.
    bagian "footnotes" = حاشية, dihitung per penanda halaman seperti matan.
    utuh=True: q harus mulai dan berakhir di batas kata kitab (kutipan yang terpotong di tengah kata tidak dihitung).
    dalam=(p1, p2): q yang muncul lebih dari sekali di rekaman ini: yang di halaman p1..p2 didahulukan.
    catatan (body saja): False = hanya letak di luar `catatan_body` (matan), True = hanya yang menyentuhnya (حاشية).
    Halamannya None kalau rekaman itu tidak bernomor halaman."""
    pertama = None
    pilah = catatan is not None and bagian == "body"
    ruas = _catatan_padat(p) if pilah else []
    if pilah and catatan and not ruas:
        return None
    for c in semua_letak(p, q, bagian, utuh, kata):
        if pilah and catatan != any(a < c[1] and c[0] < z for a, z in ruas):
            continue
        h = halaman_letak(p, bagian, c)
        if dalam is None or dalam[0] <= (h[0] or 0) and (h[1] or 0) <= dalam[1]:
            return h
        pertama = pertama or h
    return pertama


# awalan yang boleh menempel di depan kata pertama frasa `cari`/`teks`/`bab` selain huruf sambung `potongan_utuh`: «ال» («عربان» →
# «العربان», «وبالعربان», «كالعربان»), dan «لل» («للعربان»)
AWALAN_KATA = re.compile(r"[وفبكل]{0,2}ال|[وف]?لل")
IBNU_SAMBUNG = re.compile(r"[وفبكل]{1,2}ا")


def frasa_utuh(p, bagian, j, k, kata):
    """Frasa `cari`/`teks`/`bab` di teks[j:k] cocok sebagai kata utuh: berakhir di akhir kata kitab, mulai di awal kata kitab
    (boleh sesudah huruf sambung seperti `potongan_utuh` di `cek`, atau sesudah «ال»/«لل»), dan tiap kata kitab yang mulai di dalamnya
    juga mulai di awal kata frasa (kata = `kata_dalam`): «العربان» tidak cocok dengan «العرب ان». Kitab yang memisah huruf
    sambung dari katanya («و الإحياء») tetap cocok, begitu juga frasa yang memisah kata yang di kitab tersambung."""
    awal, akhir = batas_kata(p, bagian)
    if k not in akhir:
        return False
    teks = ruas_halaman(p, bagian)[0]
    if any(x in awal and x - j not in kata and not (x - 1 in awal and teks[x - 1] in SAMBUNG) for x in range(j + 1, k)):
        return False
    if j in awal or potongan_utuh(p, bagian, j, k):
        return True
    a = next((j - d for d in range(1, 5) if j - d in awal), None)
    if a is None:
        return False
    # «ابن» sendirian di-`norm` jadi «بن», yang bersambung tidak («لابن»): frasa «ابن …» tetap menemukan «لابن …»
    return bool(AWALAN_KATA.fullmatch(teks[a:j]) or teks.startswith("بن", j) and IBNU_SAMBUNG.fullmatch(teks[a:j]))


def letak_asli(raw, q, ke=0):
    """Awal kata tempat q (sudah `padat`) yang ke-`ke` (mulai 0) mulai di teks asli raw. Dicari lewat panjang `padat` tiap
    awalan, karena norm() mengubah panjang teks (kalimat hormat dibuang, tanda baca jadi spasi)."""
    pr, j = padat(raw), -1
    for _ in range(ke + 1):
        j = pr.find(q, j + 1)
    if j < 0:  # bacaan raw berbeda dari teks `padat` rekaman: kembali ke yang pertama
        j = pr.find(q)
    awal = [m.start() for m in re.finditer(r"\S+", raw)]
    if j <= 0 or not awal:
        return 0
    lo, hi = 0, len(awal) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if len(padat(raw[:awal[mid]])) <= j:
            lo = mid
        else:
            hi = mid - 1
    return awal[lo]
