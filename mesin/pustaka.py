# SPDX-License-Identifier: AGPL-3.0-or-later
"""`pustaka <folder>`: susun draf baris `#R` (المصادر والمراجع) siap tempel langsung dari metadata `kartu` kitab lokal
yang benar-benar berbukti di catatan kaki naskah (tanpa internet, tidak mengubah berkas), sekaligus menampilkan
kitab yang belum masuk `#R` dan baris `#R` yang tidak terhubung ke bukti catatan kaki."""
import re
from collections import Counter

from rapidfuzz import fuzz

import gelar
import norma
import shamela
import waqfeya
from cek_rujukan import bentuk_judul, judul_di_baris
from dasar import ANGKA_LATIN, WAQFEYA_BUKTI
from olah import adalah_mushaf, kunci_urut, periksa

_BIDANG = (
    ("judul", re.compile(r"^الكتاب$")),
    ("pengarang", re.compile(r"^(?:المؤلف|المؤلفون)$")),
    ("muhaqqiq", re.compile(r"^(?:المحقق|المحققون|تحقيق(?:\s.*)?|حققه|دراسة وتحقيق|اعتنى به|أشرف على طبعه)$")),
    ("penerbit", re.compile(r"^(?:الناشر|دار النشر|مطبعة|صادر عن|تصدر عن)$")),
    ("cetakan", re.compile(r"^الطبعة$")),
    ("tahun", re.compile(r"^(?:سنة النشر|عام النشر|تاريخ النشر|النشر)$")),
)
_TITIK_DUA = re.compile(r"[:：]")
_H = r"[\u064b-\u065f\u0670\u0640]*"
_ANGKA = r"[0-9٠-٩]{1,4}"
_HIJRI = rf"(?:ه{_H})?"
_TA_WAFAT = rf"(?:ال{_H}م{_H}ت{_H}و{_H}ف{_H}[ىي]{_H}|(?<![ء-ي])ت{_H})\s*[:：]?\s*"
# Tahun wafat di nama: «(ت ٢٧٩ هـ)», «[ت ١٣٨٨ هـ]», «(المتوفى: ٧٢٨ هـ)», rentang lahir-wafat «(٧٠٠ - ٧٧٤ هـ)», atau
# kurung wafat berketerangan «[ت ٨٦١ هـ، خلافًا لما جاء على غلاف … ٦٨١ هـ]» (kartu 21744): satu kurung dibuang utuh.
_WAFAT = re.compile(
    rf"\s*(?:[(\[]\s*{_TA_WAFAT}(?P<kurung>{_ANGKA})[^()\[\]]*[)\]]"
    rf"|[(\[]\s*{_ANGKA}\s*{_HIJRI}\s*-\s*(?P<akhir>{_ANGKA})\s*ه{_H}\s*[)\]]"
    rf"|{_TA_WAFAT}(?P<wafat>{_ANGKA})\s*{_HIJRI})"
)
_KURUNG_KOSONG = re.compile(r"\s*(?:\[\s*\]|\(\s*\))")
# Baris kartu sesudah label berisi kosong adalah isinya, hanya untuk muhaqqiq («تحقيق وتعليق:» lalu satu nama per baris,
# kartu 1435) dan tahun («عام النشر:» lalu «جـ ١ - ٤: ١٤١٥ هـ …», kartu 9442). Label pengarang/cetakan yang kosong diikuti
# daftar lain (kartu 954, 1000), jadi tidak disambung. Berhenti di baris «label: …» lain (kecuali label jilid), «[…]»,
# «عدد».
_BERSAMBUNG = ("muhaqqiq", "tahun")
_LABEL_JUZ = re.compile(r"^(?:ال)?ج(?:زء)?[\u0640\s.]*(?:[0-9٠-٩]|ال)")  # «جـ ١ - ٤:»، «جزء ١، ٨:»، «الجزء الأول:»
_LANJUT_MAKS = 4
_MIRIP = 85  # rapidfuzz.fuzz.ratio: «مصفي»/«مصطفي» 89, «العلميه»/«العربيه» 71
# Label jilid di depan nama muhaqqiq per jilid («جزء ١، ٨، ١٣: محمد حجي، جزء ٢: …», kartu 1717; «الجزء الأول: …»)
_LABEL_JILID = re.compile(r"(?:^|(?<=،))\s*(?:ال)?ج(?:زء)?[\u0640\s.][^:]{0,30}:")


_KOMA_TUTUP = re.compile(r"\s*[،,;:-]+\s*([)\]])")


def _bersih(nilai):
    return _KOMA_TUTUP.sub(r"\1", _KURUNG_KOSONG.sub("", nilai)).strip().rstrip(" .،")


def _label(baris):
    m_col = _TITIK_DUA.search(baris)
    if not m_col:
        return None, "", ""
    kunci_teks = baris[:m_col.start()].strip()
    kunci_polos = norma.HARAKAT.sub("", kunci_teks)
    nama = next((k for k, pola in _BIDANG if pola.match(kunci_polos)), None)
    return nama, kunci_teks, baris[m_col.end():].strip()


def _baris_kartu(teks):
    """[(bidang, label asli, nilai)] dari betaka; label berisi kosong mengambil baris lanjutannya."""
    baris = [b.strip() for b in (teks or "").replace("\r", "\n").splitlines()]
    out = []
    for i, b in enumerate(baris):
        nama, kunci_teks, nilai = _label(b)
        if not nama:
            continue
        if not nilai and nama in _BERSAMBUNG:
            lanjut = []
            for b2 in baris[i + 1:i + 1 + _LANJUT_MAKS]:
                if (not b2 or b2.startswith(("[", "•", "-", "عدد"))
                        or _TITIK_DUA.search(b2) and not _LABEL_JUZ.match(b2)):
                    break
                lanjut.append(b2)
            nilai = "، ".join(lanjut)
        if nilai:
            out.append((nama, kunci_teks, nilai))
    return out


def _tanpa_wafat(nama):
    """(nama tanpa tahun wafat, tahun wafat atau "")."""
    wafat = ""
    for m in _WAFAT.finditer(nama):
        wafat = m["kurung"] or m["akhir"] or m["wafat"]
    return _bersih(_WAFAT.sub("", nama)).strip(" ،,-"), wafat


def _ekstrak_kartu(m):
    """Ambil (judul, pengarang, wafat, muhaqqiq, penerbit, cetakan, tahun) bersih tanpa gelar dari metadata Shamela."""
    data = {}
    for kunci, kunci_teks, nilai_mentah in _baris_kartu(m.get("betaka_text")):
        if kunci in data:
            continue
        # `gelar.buang_gelar` hanya mengenali «:» ASCII; kirim dengan «:» agar label ber-«：» tetap bersih dari gelar
        nilai = nilai_mentah if kunci == "judul" else gelar.buang_gelar(f"{kunci_teks}: {nilai_mentah}").partition(":")[2].strip()
        if nilai:
            data[kunci] = nilai
    judul = data.get("judul") or (m.get("title_ar") or "").split(" - ")[0].strip()
    pengarang = data.get("pengarang") or gelar.buang_gelar("المؤلف: " + (m.get("main_author_name_ar") or "")).partition(":")[2].strip()
    pengarang, wafat = _tanpa_wafat(pengarang)
    if wafat:
        wafat += "هـ"
    elif m.get("death_year_hijri"):
        wafat = f"{m['death_year_hijri']}هـ"
    return {
        "judul": _bersih(judul),
        "pengarang": _bersih(pengarang),
        "wafat": wafat,
        # Tahun wafat muhaqqiq («محمد فؤاد عبد الباقي [ت ١٣٨٨ هـ]») bukan data cetak
        "muhaqqiq": _tanpa_wafat(data.get("muhaqqiq") or "")[0],
        "penerbit": _bersih(data.get("penerbit") or ""),
        "cetakan": _bersih(data.get("cetakan") or ""),
        "tahun": _bersih(data.get("tahun") or ""),
    }


def format_baris(info_kartu, gaya="judul"):
    """Susun satu baris `#R` siap tempel dari kamus `_ekstrak_kartu` sesuai `@pustaka_gaya` (`judul` atau `muallif`)."""
    rinci = []
    if info_kartu["muhaqqiq"]:
        rinci.append(f"تحقيق: {info_kartu['muhaqqiq']}")
    if info_kartu["penerbit"]:
        rinci.append(info_kartu["penerbit"])
    if info_kartu["cetakan"]:
        c = info_kartu["cetakan"]
        butuh_prefix = not c.startswith(("ط", "الطبعة", "بدون", "دون")) and not re.match(r"^[\d٠-٩(]", c)
        rinci.append(f"الطبعة {c}" if butuh_prefix else c)
    if info_kartu["tahun"] and info_kartu["tahun"] not in (info_kartu["cetakan"] or ""):
        rinci.append(info_kartu["tahun"])
    ekor_data = "، ".join(rinci)
    if gaya != "judul":  # muallif, judul_tebal (olah.pustaka_judul_dulu membaca bentuk ini)
        nama = f"**{info_kartu['pengarang']}**" if info_kartu["pengarang"] else ""
        if nama and info_kartu["wafat"]:
            nama += f" (ت {info_kartu['wafat']})"
        bagian = [x for x in (nama, f"__{info_kartu['judul']}__", ekor_data) if x]
        return ". ".join(bagian) + "."
    bagian = [x for x in (info_kartu["judul"], info_kartu["pengarang"], ekor_data) if x]
    return "، ".join(bagian) + "."


def _buku(penunjuk):
    shamela_id, waqfeya_id = set(), set()
    for p in penunjuk:
        for bukti in p.get("bukti", ()):
            if m := WAQFEYA_BUKTI.fullmatch(bukti):
                waqfeya_id.add(m[1])
            else:
                sid = bukti.split("|", 1)[0].strip()
                if sid.isdecimal():
                    shamela_id.add(int(sid))
    return sorted(shamela_id), sorted(waqfeya_id)


# Kata yang tidak membedakan nama orang (muhaqqiq); angka dinilai terpisah (`_tahun`).
_KATA_NASAB = frozenset(norma.norm(k) for k in ("بن", "ابن", "أبو", "أبي", "عبد", "آل"))
_URUTAN = frozenset(norma.norm(k) for k in (
    "الأولى", "الثانية", "الثالثة", "الرابعة", "الخامسة", "السادسة", "السابعة", "الثامنة", "التاسعة", "العاشرة",
    "الحادية", "عشرة"))
_AWALAN = "وبلفك"
_CATATAN_KARTU = re.compile(r"\[[^\[\]]*\]")  # «[كتبت مقدمتها ١٣٩٢ هـ …]»: keterangan Shamela, bukan data cetak
_SAMBUNG = "ـ"  # «جـ»
# Nama pertama sebuah daftar: sebelum «،», « - », atau «(…)» (muhaqqiq kedua, kota penerbit)
_PISAH_NAMA = re.compile(r"\s*(?:[،,؛(\[]|\s[-–]\s?|-\s)")
# «بدون طبعة»، «دون تاريخ»، «د.ط»، «د. ت» = data cetak yang memang tidak ada
_TANPA_CETAK = re.compile(r"(?<![ء-ي])(?:ب?دون\s+(?:طبع|تاريخ)|د\s*\.?\s*[طت](?![ء-ي]))")
_TANPA_NASYIR = re.compile(r"(?<![ء-ي])(?:ب?دون\s+(?:ناشر|دار\s+نشر)|د\s*\.?\s*ن(?![ء-ي]))")
# Kata badan usaha dan peran yang mendahului nama penerbit atau muhaqqiq di kartu
_BADAN_USAHA = frozenset(norma.norm(k) for k in ("شركة", "مكتبة", "ومطبعة", "مطبعة", "مطابع", "ومكتبة", "دار",
                                                 "ودار", "مؤسسة", "المؤسسة"))
_JENIS_PENERBIT = frozenset(norma.norm(k) for k in ("دار", "ودار", "مؤسسة", "المؤسسة", "مكتبة", "مطبعة", "شركة"))
# Keterangan umum di nama penerbit/muhaqqiq kartu yang sering tidak ditulis («للطباعة والنشر والتوزيع»، «بإشراف الناشر»)
_KATA_UMUM = frozenset(norma.norm(k) for k in (
    "للنشر", "والنشر", "النشر", "والتوزيع", "التوزيع", "للطباعة", "والطباعة", "الطباعة", "والإعلان", "والإعلام",
    "وشركاه", "وأولاده", "من", "في", "بإشراف", "الناشر"))
_PISAH_BARIS = re.compile(r"[،,؛;()\[\]]|\s*[-–]\s*|\.\s")
# Kata peran di depan nama muhaqqiq kartu («حققه وخرج أحاديثه محمد …», kartu 41; «ضبطه وصححه جماعة …», kartu 7312)
_PERAN_AWAL = re.compile(r"^\s*(?:و?(?:حققه|حقق|خرج|أحاديثه|علق|عليه|ضبطه|صححه|قدم|له|اعتنى|به|راجعه)\s+)+")
_BATAS_HIJRI = 1500  # tahun di bawahnya hijriah (cetakan Shamela tertua ±1250 هـ), di atasnya masehi


def _kata(teks):
    """Kata bentuk sama (`norma.norm`) dan angka, angka dipisah dari huruf («1374هـ» = «1374» + «ه»)."""
    return re.findall(r"[0-9]+|[ء-ي]+", norma.norm(teks.translate(ANGKA_LATIN).replace(_SAMBUNG, "")))


def _bentuk(kata):
    """Kata dengan dan tanpa satu huruf awalan («ببولاق» = «بولاق», «لدار» = «دار»)."""
    return {kata, kata[1:]} if len(kata) > 3 and kata[0] in _AWALAN else {kata}


def _tahun(teks):
    return {int(k) for k in _kata(teks) if k.isdecimal() and 3 <= len(k) <= 4}


def _tahun_cocok(kartu, baris):
    """Tahun hijriah dan masehi dinilai sendiri-sendiri: tiap jenis yang ditulis di kartu dan di baris harus bertemu
    («1420هـ - 2005م» bukan cetakan «١٤٢٠ هـ - ١٩٩٩ م»), dan paling tidak satu tahun kartu tertulis di baris."""
    if not kartu & baris:
        return False
    for hijri in (True, False):
        k = {t for t in kartu if (t < _BATAS_HIJRI) == hijri}
        b = {t for t in baris if (t < _BATAS_HIJRI) == hijri}
        if k and b and not k & b:
            return False
    return True


def _sidik_baris(teks):
    """Bentuk satu baris #R untuk dicocokkan: urutan kata dan tahun, tanpa tahun wafat («(ت 911هـ)»)."""
    tanpa_wafat = _WAFAT.sub(" ", teks.translate(ANGKA_LATIN))
    return [k for k in _kata(tanpa_wafat) if not k.isdecimal()], _tahun(tanpa_wafat)


def _nama_pertama(nilai, buang=frozenset()):
    """Kata nama pertama sebuah daftar (muhaqqiq, penerbit), tanpa kata `buang`."""
    pertama = _PISAH_NAMA.split(_CATATAN_KARTU.sub(" ", nilai), 1)[0]
    return [k for k in _kata(pertama) if not k.isdecimal() and k not in buang]


def _khas(teks):
    """Kata khas sebuah nama penerbit/muhaqqiq: tanpa angka, kata nasab, kata badan usaha, dan keterangan umum."""
    return [k for k in _kata(teks) if not k.isdecimal() and len(k) > 1 and k not in _KATA_NASAB | _BADAN_USAHA
            | _KATA_UMUM]


def _saling_termuat(kartu, potong, semua):
    """Sebagian besar kata khas kartu ada di baris #R (`semua`) dan sebagian besar kata khas potongan baris ada di kartu:
    «دار الكتب العلمية» bukan «دار الكتب المصرية», «دار الفكر» bukan «دار الفكر المعاصر». Kota yang ditempel di kartu
    («مؤسسة النور بالرياض») boleh ditulis di potongan lain («مؤسسة النور- الرياض»)."""
    if not kartu or not potong:
        return False
    ada = lambda k, daftar: any(_bentuk(k) & _bentuk(b) for b in daftar)
    # Potongan itu sendiri memuat kata pertama nama penerbit, bukan hanya kotanya; salah ketik kartu («مصفى البابي
    # الحلبي», kartu 21744) masih dikenali.
    awal = any(ada(kartu[0], [b]) or fuzz.ratio(kartu[0], b) >= _MIRIP for b in potong)
    return (awal and sum(ada(k, semua) for k in kartu) >= 0.6 * len(kartu)
            and sum(ada(b, kartu) for b in potong) >= 0.6 * len(potong))


def _penerbit_cocok(nilai, teks):
    """Nama penerbit kartu (sebelum «،», « - », «(») sama dengan salah satu potongan baris #R, dinilai dari kata khasnya
    ke dua arah; kata badan usaha («شركة مكتبة ومطبعة مصطفى البابي الحلبي») dan «للنشر والتوزيع» boleh tidak ditulis,
    tetapi «دار» dan «مؤسسة» yang tertulis di keduanya harus sama. «بدون ناشر (على نفقة المحقق)» dinilai dari
    keterangannya, atau dari «بدون ناشر»/«د.ن» kalau tanpa keterangan. None kalau kartu tidak menyebut penerbit."""
    if not nilai.strip():
        return None
    nilai = _TANPA_NASYIR.sub(" ", nilai.replace("(", " ").replace(")", " "))
    if not nilai.strip(" ،-"):
        return bool(_TANPA_NASYIR.search(norma.HARAKAT.sub("", teks)))
    pertama = _PISAH_NAMA.split(_CATATAN_KARTU.sub(" ", nilai), 1)[0]
    kartu, jenis = _khas(pertama), {k for k in _kata(pertama) if k in _JENIS_PENERBIT}
    if not kartu:
        return None
    baris = _WAFAT.sub(" ", teks.translate(ANGKA_LATIN))
    semua = _khas(baris)
    for potong in _PISAH_BARIS.split(baris):
        jenis_baris = {k for k in _kata(potong) if k in _JENIS_PENERBIT}
        if (not jenis or not jenis_baris or jenis & jenis_baris) and _saling_termuat(kartu, _khas(potong), semua):
            return True
    return False


def _muhaqqiq_cocok(nilai, kata_baris):
    """Sebagian besar kata nama muhaqqiq pertama ada di baris («أحمد محمد شاكر وآخرين» untuk tiga muhaqqiq kartu,
    «مشهور بن حسن آل سلمان» untuk «أبو عبيدة مشهور …»); kata peran («حققه وخرج أحاديثه») dan keterangan umum («بإشراف
    الناشر») tidak dihitung. None kalau kartu tidak menyebut muhaqqiq."""
    nilai = _LABEL_JILID.sub(" ", _PERAN_AWAL.sub("", norma.HARAKAT.sub("", nilai)))
    khas = [k for k in _nama_pertama(nilai, _KATA_NASAB | _KATA_UMUM) if len(k) > 2]
    if not khas:
        return None
    ada = {b for k in kata_baris for b in _bentuk(k)}
    return sum(bool(_bentuk(k) & ada) for k in khas) >= 0.6 * len(khas)


def _beda_cetak(data, teks):
    """Bidang data cetak kartu yang tidak terbaca di baris #R `teks`, atau None kalau kartu tidak punya data cetak.
    Yang dinilai muhaqqiq, penerbit, nomor cetakan, dan tahun; bukan nama lengkap pengarang, karena #R boleh
    menulisnya lebih pendek («مسلم بن الحجاج» untuk «أبو الحسين مسلم بن الحجاج …»)."""
    kata_baris, tahun_baris = _sidik_baris(teks)
    cetakan = _CATATAN_KARTU.sub(" ", data["cetakan"])
    tahun = _tahun(cetakan) | _tahun(_CATATAN_KARTU.sub(" ", data["tahun"]))
    urutan = {k for k in _kata(cetakan) if k in _URUTAN}
    nilai = {"muhaqqiq": _muhaqqiq_cocok(data["muhaqqiq"], kata_baris),
             "penerbit": _penerbit_cocok(data["penerbit"], teks)}
    if urutan:
        nilai["cetakan"] = bool(urutan & set(kata_baris))
    elif _TANPA_CETAK.search(norma.HARAKAT.sub("", cetakan)):
        nilai["cetakan"] = bool(_TANPA_CETAK.search(norma.HARAKAT.sub("", teks)))
    if tahun:
        nilai["tahun"] = _tahun_cocok(tahun, tahun_baris)
    nilai = {b: ok for b, ok in nilai.items() if ok is not None}
    return [b for b, ok in nilai.items() if not ok] if nilai else None


def _cocok(data, bentuk, baris_asli):
    """Untuk tiap baris #R yang menyebut judul kitab ini (`cek_rujukan.judul_di_baris`, sama dengan perhatian `cek`
    «tidak ada di المصادر والمراجع»): daftar bidang data cetak yang berbeda ([] = cocok), atau None kalau kartu tidak
    punya data cetak."""
    return {n: _beda_cetak(data, teks) for n, teks in baris_asli.items() if judul_di_baris(bentuk, teks)}


def _daftar(nomor):
    return ", ".join(map(str, sorted(nomor)))


def cetak(folder):
    """Cetak blok #R yang bisa ditempel, lalu petunjuk per kitab untuk mencocokkannya dengan daftar saat ini."""
    ctx = periksa(folder).ctx
    gaya = ctx.meta.get("pustaka_gaya", "judul")
    sids, wids = _buku(ctx.penunjuk)
    baris_r = {n: teks for n, teks in ctx.pustaka_baris if not adalah_mushaf(teks)}
    draf, sid_cocok, catatan, terlihat = [], {}, {}, set()
    for sid in sids:
        try:
            m = shamela.info(sid)
        except (LookupError, OSError, ValueError, SystemExit):
            catatan[sid] = "kartu lokal belum terbaca"
            continue
        data = _ekstrak_kartu(m)
        beda = _cocok(data, bentuk_judul(m), baris_r)
        terlihat.update(beda)
        sid_cocok[sid] = beda
        draf.append(format_baris(data, gaya=gaya))
    pemilik = Counter(n for beda in sid_cocok.values() for n, b in beda.items() if b == [])
    for sid, beda in sid_cocok.items():
        if sah := [n for n, b in beda.items() if b == [] and pemilik[n] == 1]:
            catatan[sid] = "data cetak cocok di #R baris " + _daftar(sah)
        elif tanpa := [n for n, b in beda.items() if b is None]:
            catatan[sid] = (f"judul ditemukan di #R baris {_daftar(tanpa)}; kartu tanpa data cetak, salin dari halaman "
                            "judul kitabnya")
        elif beda:
            rinci = "; ".join(f"baris {n}: " + ("beda " + ", ".join(b) if b else "data cetaknya juga cocok dengan kitab lain")
                              for n, b in sorted(beda.items()))
            catatan[sid] = f"judul ditemukan, edisi perlu dicek di #R baris {_daftar(beda)} ({rinci})"
        else:
            catatan[sid] = "judul belum ditemukan di #R"
    for wid in wids:
        if not waqfeya.ada(wid):
            catatan[wid] = "scan belum diunduh"
            continue
        d = waqfeya.data(wid)
        calon = {n for n, teks in baris_r.items() if waqfeya.judul_disebut(wid, teks)}
        terlihat.update(calon)
        catatan[wid] = f"salin data cetak dari scan: kartu {wid}"
        if calon:
            catatan[wid] += " (judul ditemukan di #R baris " + ", ".join(map(str, sorted(calon))) + ")"
        draf.append(format_baris(dict(judul=d["judul"], pengarang=d["pengarang"] or "", wafat="", muhaqqiq="",
                                      penerbit="", cetakan="", tahun=""), gaya=gaya))
    if draf or ctx.ayat_idx:
        print("Draf kitab berbukti. Periksa data cetak dan gabungkan dengan rujukan lain di #R.")
        print("#R المصادر والمراجع")
        if ctx.ayat_idx:
            print("القرآن الكريم.")
        for baris in sorted(draf, key=lambda b: kunci_urut(b, gaya == "muallif")):
            print(baris)
    else:
        print("Belum ada kartu kitab berbukti atau ayat {Q:} untuk menyusun draf.")
    if catatan:
        print("\nPemeriksaan #R:")
        for sid, pesan in catatan.items():
            print(f"  {sid}: {pesan}")
    if sisa := sorted(baris_r.keys() - terlihat):
        print("\nBaris #R di luar padanan kitab berbukti; periksa sumber lain/PDF:")
        for n in sisa:
            print(f"  baris {n}: {baris_r[n]}")
