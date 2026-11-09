# SPDX-License-Identifier: AGPL-3.0-or-later
"""Akses kitab Shamela yang sudah diunduh: rekaman per juz/halaman, juz dan halaman yang tidak ada, teks
beberapa halaman yang disambung, bagian kitab (المقدمة، الكتاب…) tempat sebuah kutipan, dan letak bagian-bagian
kutipan di teks sebuah kitab (dipakai `cek` dan `cek --jejak`)."""
import bisect, functools, re

import norma
import shamela
from dasar import AD, BELUM_DIUNDUH, RENTANG_MAKS


@functools.cache
def kitab(sid):
    """Nomor rekaman kitab per juz ({part: [i]}, urut berkas; juz urut kemunculan pertamanya), dari shamela.indeks."""
    juz = {}
    for i, x in enumerate(shamela.indeks(sid)):
        juz.setdefault(x[0], []).append(i)
    return juz


def _nomor_juz(sid, juz):
    """Nomor rekaman juz itu (juz "-" = semua juz, urut juz lalu urut berkas), lihat `kitab`."""
    return [i for ii in kitab(sid).values() for i in ii] if juz == "-" else kitab(sid)[juz]


def rekaman(sid, juz, p1=0, p2=float("inf")):
    """Rekaman juz itu (juz "-" = semua) yang menyentuh halaman p1..p2. Hanya rekaman itu yang diurai."""
    ix = shamela.indeks(sid)
    semua = _nomor_juz(sid, juz)
    return [shamela.rekaman_ke(sid, i) for i in semua if ix[i][2] >= p1 and (ix[i][1] or 0) <= p2]


def urut_juz(j):
    """Juz berangka dulu menurut angkanya, lalu yang bernama (mis. المقدمة)."""
    return (not str(j).isdigit(), str(j).zfill(4))


def salah_juz(sid, juz, hal):
    """'' kalau kitab sid sudah diunduh dan punya juz itu; selain itu pesan kesalahannya."""
    if not (shamela.ROOT / str(sid) / "pages.jsonl.gz").exists():
        return f"{BELUM_DIUNDUH.format(sid)} ({shamela.perintah(f'ambil {sid}')})"
    juz_ada = set(kitab(sid))
    # kitab satu jilid = satu nilai juz saja, atau bagiannya hanya bernama (mis. المقدمة + الكتاب) tanpa juz berangka
    if juz == "-" and len(juz_ada) > 1 and any(str(j).isdigit() for j in juz_ada):
        rentang = shamela.rentang_juz(sid)
        p1 = int(hal.partition("-")[0]) if hal.partition("-")[0].isdigit() else 0
        # halaman bersambung antarjilid («متسلسلة الترقيم»): juz yang rentangnya memuat halaman itu
        contoh = next((j for j, (a, z) in rentang.items() if a <= p1 <= z), sorted(juz_ada, key=urut_juz)[0])
        return (f"kitab {sid} berjilid: tulis juz-nya, mis. <<{sid}|{contoh}|{hal}>>; yang ada: {shamela.daftar_juz(sid)} "
                f"(juz \"-\" hanya untuk kitab satu jilid; bentuk buktinya: `kartu {sid}`)")
    if juz != "-" and juz not in juz_ada:
        if juz_ada == {None}:
            return f"kitab {sid} satu jilid: tulis juz \"-\", mis. <<{sid}|-|{hal}>>"
        return f"kitab {sid} tidak punya juz {juz} (yang ada: {'، '.join(sorted(juz_ada - {None}, key=urut_juz))})"
    return ""


def rentang_halaman(hal):
    """Pasangan angka halaman «n» atau «n-m»; kebijakan rentang tetap diperiksa pemanggilnya."""
    a, _, z = hal.partition("-")
    return int(a), int(z or a)


def salah_halaman(hal):
    """'' kalau halaman bukti «n» atau «n-m» masuk akal; selain itu pesan kesalahannya."""
    p1, p2 = rentang_halaman(hal)
    if p1 < 1:
        return (f"halaman 0 tidak ada: teks tanpa nomor halaman (mukadimah, sampul jilid) tidak bisa dirujuk ke halaman "
                f"cetak: {hal}")
    if p2 < p1:
        return f"rentang halaman terbalik: {hal}"
    if p2 - p1 > RENTANG_MAKS:
        return f"rentang halaman bukti terlalu lebar (lebih dari {RENTANG_MAKS} halaman): {hal}"
    return ""


@functools.cache
def halaman_janggal(sid, juz):
    """{halaman: (sebelum, sesudah)}: nomor halaman rekaman yang menyendiri jauh dari halaman lain juz itu (lebih dari
    RENTANG_MAKS di bawahnya dan di atasnya), biasanya salah ketik Shamela (ص3110 di antara ص310 dan ص312 di jilid
    ±520 halaman). sebelum/sesudah = nomor rekaman tetangganya di berkas."""
    ix = shamela.indeks(sid)
    semua = _nomor_juz(sid, juz)
    nomor = sorted({ix[i][1] for i in semua if ix[i][1]})
    sendiri = {n for k, n in enumerate(nomor) if k and n - nomor[k - 1] > RENTANG_MAKS
               and (k == len(nomor) - 1 or nomor[k + 1] - n > RENTANG_MAKS)}
    return {ix[i][1]: (ix[semua[k - 1]][1] if k else None, ix[semua[k + 1]][1] if k + 1 < len(semua) else None)
            for k, i in enumerate(semua) if ix[i][1] in sendiri}


def rekaman_dulu(sid, juz, p1, p2):
    """Rekaman tepat sebelum rekaman pertama yang menyentuh halaman p1..p2 (kata di akhir halaman sebelumnya); None kalau tidak ada."""
    ix = shamela.indeks(sid)
    semua = _nomor_juz(sid, juz)
    for k, i in enumerate(semua):
        if ix[i][2] >= p1 and (ix[i][1] or 0) <= p2:
            return shamela.rekaman_ke(sid, semua[k - 1]) if k else None
    return None


# tempat kutipan dicari, berurutan: (bagian rekaman, `catatan` shamela.tempat). Matan = body selain حاشية yang tertulis di
# body sesudah garis pemisah ___ (`shamela.catatan_body`); حاشية = ruas itu dan footnotes
SISI = (("body", False), ("body", True), ("footnotes", None))


def cari_di(sid, juz, p1, p2, q, utuh, kata=()):
    """Cari q (sudah `padat`) di juz/halaman p1..p2, matan dan حاشية per halaman.
    Kembalikan (jenis, None): jenis "matan", "hasyiah", atau "hasyiah?" (حاشية tanpa penanda halaman di rekaman
    banyak halaman); atau (None, (awal, akhir, tanda)) kalau hanya ada di halaman lain; atau (None, None)."""
    lain, hasyiah = None, None
    for r in rekaman(sid, juz, p1, p2):
        for bagian, catatan in SISI:
            h = shamela.tempat(r, q, bagian, utuh, kata, (p1, p2), catatan)  # q yang muncul dua kali: yang di p1..p2 didahulukan
            if not h:
                continue
            a, z = h[0] or 0, h[1] or 0
            if p1 <= a and z <= p2:
                if catatan is False:
                    return "matan", None
                hasyiah = "hasyiah"
            elif bagian != "body" and a <= p2 and z >= p1 and h[0] != h[1]:
                hasyiah = hasyiah or "hasyiah?"
            else:
                lain = lain or (h[0], h[1], "" if catatan is False else " [حاشية]")
            # Matan di halaman lain tidak menutup pencarian حاشية pada rekaman yang sama.
    if not hasyiah and len(rekaman(sid, juz, p1, p2)) > 1:  # kutipan yang menyambung dari satu rekaman ke berikutnya
        for bagian, catatan in SISI:  # حاشية yang bersambung («… =» lalu «= …» di halaman berikutnya)
            for g in gabung(sid, juz, p1, p2):
                h = shamela.tempat(g, q, bagian, utuh, kata, (p1, p2), catatan)
                if h and p1 <= (h[0] or 0) and (h[1] or 0) <= p2:
                    return ("matan" if catatan is False else "hasyiah"), None
    return (hasyiah, None) if hasyiah else (None, lain)


def akhir_rekaman(r):
    """Halaman cetak terakhir rekaman r (page_num, atau penanda ⦗n⦘ terbesar di matannya)."""
    return max([r.get("page_num") or 0] + [int(n) for n in norma.PENANDA.findall(r.get("body") or "")])


@functools.lru_cache(maxsize=4096)
def gabung(sid, juz, p1, p2):
    """Rekaman-rekaman yang menyentuh halaman p1..p2 sebagai rangkaian rekaman: awal tiap rekaman diberi penanda
    halaman ⦗n⦘, jadi kutipan yang menyambung lintas rekaman tetap dicek per kata dan halamannya tetap tercatat.
    Rekaman diurutkan menurut halamannya (urutan berkas Shamela bisa melompat: mukadimah diselipkan di tengah, dua
    rangkaian halaman berselang-seling), dan hanya rekaman yang halamannya bersambung (sama atau +1) yang dirangkai:
    teks dua halaman yang tidak bersambung tidak boleh jadi satu kutipan."""
    hasil = []
    for r in sorted(rekaman(sid, juz, p1, p2), key=lambda r: r.get("page_num") or 0):
        n = r.get("page_num")
        if hasil and n and hasil[-1]["akhir_rekaman"] <= n <= hasil[-1]["akhir_rekaman"] + 1:
            g = hasil[-1]
            for bagian, _ in norma.BAGIAN:
                g[bagian] += f" ⦗{str(n).translate(AD)}⦘ " + (r.get(bagian) or "")
        else:
            g = {bagian: r.get(bagian) or "" for bagian, _ in norma.BAGIAN} | {"page_num": n}
            hasil.append(g)
        g["akhir_rekaman"] = max(g.get("akhir_rekaman", 0), akhir_rekaman(r))
    return hasil


def bagian_kitab(isi, bukti):
    """Catatan kaki berbukti beberapa kitab: [(teks, bukti kitab itu)] dipotong di judul tiap kitab, supaya halaman yang
    tercetak dicocokkan dengan bukti kitabnya sendiri. Judul yang tidak ketemu (disingkat lain) = tidak dipotong."""
    sids = list(dict.fromkeys(b[0] for b in bukti))
    if len(sids) < 2:
        return [(isi, bukti)]
    letak, terpakai = {}, {}
    data = {sid: shamela.info(int(sid)) for sid in sids}
    # pengarang di dalam judul katalog bukan bagian judul: «المغني لابن قدامة» ditulis «المغني، ابن قدامة»
    judul = {sid: shamela.kata_judul(data[sid]["title_ar"].split(" - ")[0]) for sid in sids}
    cari = lambda teks, luar: next((m for m in re.finditer(rf"(?<!\w)و?{re.escape(teks)}(?!\w)", isi)  # «ورياض الصالحين»
                                    if not any(a <= m.start() < z for a, z in luar)), None)
    # judul terpanjang dulu: «زاد المستقنع» di dalam «الشرح الممتع على زاد المستقنع» bukan tempat kitab متن-nya
    for sid in sorted(sids, key=lambda x: -len(judul[x])):
        kata = judul[sid]
        for n in range(len(kata), min(2, len(kata)) - 1, -1):
            m = cari(" ".join(kata[:n]), terpakai.values())
            if m:
                letak[sid] = m.start(); terpakai[sid] = m.span(); break
    # nama pengarang juga tempat kitabnya: takhrij «أخرجه البخاري، …، 7/2، ومسلم، …، 2/1020» (judul lengkapnya, kalau
    # ada, baru di data cetak di ujung), «المغني، ابن قدامة، …؛ والذخيرة، القرافي، …». Yang paling depan yang dipakai.
    # Pengarang yang sama untuk dua kitab di catatan kaki ini tidak menunjuk kitab mana pun.
    nama = {sid: (data[sid].get("main_author_name_ar") or "").strip() for sid in sids}
    for sid in sids:
        if nama[sid] and list(nama.values()).count(nama[sid]) == 1:
            m = cari(nama[sid], [z for s, z in terpakai.items() if s != sid])
            if m and m.start() < letak.get(sid, len(isi)):
                letak[sid] = m.start()
    if len(letak) < len(sids):
        return [(isi, bukti)]
    urut = sorted(sids, key=letak.get)
    if len(set(letak.values())) < len(sids):
        return [(isi, bukti)]
    batas = [0] + [letak[s] for s in urut[1:]] + [len(isi)]
    return [(isi[batas[i]:batas[i + 1]], [b for b in bukti if b[0] == s]) for i, s in enumerate(urut)]


@functools.cache
def kitab_meta(sid):
    try:
        m = shamela.info(sid)
    except (SystemExit, LookupError, OSError, ValueError):
        return None
    try:
        wafat = int(m.get("main_author_death_hijri") or 99999)
    except ValueError:
        wafat = 99999
    return {"wafat": wafat, "kategori": int(m.get("category_id") or 0), "judul": m.get("title_ar") or str(sid)}


def _rangkaian(padat_, ix):
    """Rangkaian rekaman kitab dari teks `padat`-nya (`norma.Padat`): [(juz, tanda, teks, ruas)], teks dalam `bait`.
    Aturannya sama dengan `gabung`: urut halaman, dan hanya rekaman yang halamannya bersambung (sama atau +1) di juz
    yang sama yang dirangkai. ruas = (padat_, bagian, awal tiap rekaman di teks, nomor rekamannya), dibaca `halaman_di`."""
    hasil = []
    juz = {}
    for i, x in enumerate(ix):
        juz.setdefault(x[0], []).append(i)
    for j, ii in juz.items():
        urut = sorted(ii, key=lambda i: ix[i][1] or 0)
        for s, (_, tanda) in enumerate(norma.BAGIAN):
            t, mulai = padat_.teks[s], padat_.deret[s]["mulai"]
            rek, awal, panjang, akhir = [], [], 0, 0
            for i in urut:
                n = ix[i][1]
                if panjang and not (n and akhir <= n <= akhir + 1):
                    hasil.append((j, tanda, b"".join(t[mulai[r]:mulai[r + 1]] for r in rek), (padat_, s, awal, rek)))
                    rek, awal, panjang, akhir = [], [], 0, 0
                rek.append(i); awal.append(panjang)
                panjang += mulai[i + 1] - mulai[i]
                akhir = max(akhir, ix[i][2])
            if panjang:
                hasil.append((j, tanda, b"".join(t[mulai[r]:mulai[r + 1]] for r in rek), (padat_, s, awal, rek)))
    return hasil


@functools.lru_cache(maxsize=4)  # banyak GAGAL di kitab yang sama tidak membaca ulang; memori tetap kecil
def rangkaian_kitab(sid):
    """`_rangkaian` kitab sid; `jejak` melepasnya tiap kitab."""
    return _rangkaian(shamela._cache(sid), shamela.indeks(sid))


def halaman_di(ruas, a, z):
    """Rentang halaman cetak (kecil-besar) potongan teks[a:z] rangkaian yang ruasnya `ruas` (lihat `_rangkaian`):
    halaman awal ruas pertama yang berakhir sesudah a, halaman akhir ruas pertama yang berakhir di z atau sesudahnya."""
    padat_, s, awal, rek = ruas
    d = padat_.deret[s]

    def ruas_di(x, cari):  # ruas rekaman yang memuat letak x (rekaman kosong tidak memuat apa pun)
        k = bisect.bisect_right(awal, x) - 1
        i = rek[k]
        return d["h1"], d["h2"], cari(d["akhir"], x - awal[k], d["ruas"][i], d["ruas"][i + 1])
    h1s, _, k1 = ruas_di(a, bisect.bisect_right)
    _, h2s, k2 = ruas_di(z - 1, lambda deret, x, lo, hi: bisect.bisect_left(deret, x + 1, lo, hi))
    h1, h2 = (None if x == norma.TANPA_HAL else x for x in (h1s[k1], h2s[k2]))
    return (h2, h1) if (h1 or 0) > (h2 or 0) else (h1, h2)  # penanda halaman yang menurun di satu rekaman


def tempat_kitab(rangkaian, bagian):
    """Juz, rentang halaman, dan tanda (matan/حاشية) tempat SEMUA bagian kutipan berurutan: boleh menyambung ke halaman
    berikutnya, paling lebar RENTANG_MAKS halaman. None kalau tidak ada. Hanya petunjuk: putusannya tetap milik `cek`.
    Yang ditunjuk rentang tersempit: kutipan ber-... tidak boleh ditunjuk di tempat bagian umumnya kebetulan berjauhan."""
    terbaik = None
    for juz, tanda, teks, ruas in rangkaian:
        for letak in susunan_bagian(teks, bagian, len(teks)):
            h1, h2 = halaman_di(ruas, letak[0][0], letak[-1][1])
            lebar = (h2 or 0) - (h1 or 0)
            if lebar <= RENTANG_MAKS and (terbaik is None or lebar < terbaik[0]):
                terbaik = lebar, ("-" if juz is None else juz), (h1, h2), tanda
            if lebar == 0:
                return terbaik[1:]
    return terbaik[1:] if terbaik else None


def susunan_bagian(pd, q, maks=50, cocok=None):
    """Tiap susunan letak [(awal, akhir)] bagian-bagian q di pd: bagian berikutnya yang terdekat dan lolos `cocok`,
    kalau diberikan (halaman/batas kata); calon yang ditolak tidak menutupi kemunculan sah sesudahnya."""
    def berikut(i, awal):
        j = pd.find(q[i], awal)
        while j >= 0 and cocok is not None and not cocok(i, j, j + len(q[i])):
            j = pd.find(q[i], j + 1)
        return j
    j = berikut(0, 0)
    while j >= 0 and maks:
        letak, k = [(j, j + len(q[0]))], j + len(q[0])
        for i, b in enumerate(q[1:], 1):
            n = berikut(i, k)
            if n < 0:
                return
            letak.append((n, n + len(b))); k = n + len(b)
        yield letak
        maks -= 1
        j = berikut(0, j + 1)
