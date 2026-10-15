"""Olah <bahts>/naskah.txt -> mesin/_tmp/<bahts>.json (bahan untuk perakit Word)
+ verifikasi setiap rujukan ke kitab Shamela lokal. Dipanggil lewat bahts.py.

Tanda di naskah.txt (dicetak oleh: python mesin/bahts.py tanda):
  @kunci: nilai       data sampul, di awal naskah. Wajib: judul, jenis, nama, nim, fasl.
                      Opsional: musyrif, jabatan (kosong atau "-" = tidak tercetak), thalibah (ya = sampul mencetak «اسم الطالبة»),
                      berkas (nama file hasil), format (profil di format.json; bawaan imam),
                      tanpa (yang tidak dicetak: فهرس ayat, hadits, maudhuat, dan pustaka = المصادر والمراجع
                      bila dosen minta sumber cukup di catatan kaki; mis. «@tanpa: ayat, hadits»).
                      فهرس الآيات dan فهرس الأحاديث yang kosong tidak dicetak dengan sendirinya
  #K #F #B #M teks    judul tengah + masuk فهرس الموضوعات: K = مقدمة/خاتمة, F = فصل (keduanya mulai halaman baru), B = مبحث, M = مطلب.
                      Bahts pendek tanpa فصل: #F untuk مبحث, #B untuk مطلب
  #S teks             sub-judul kanan (tidak masuk فهرس)
  #R teks             awal المصادر والمراجع; sesudahnya satu kitab per baris (diurutkan abjad otomatis, القرآن الكريم paling atas).
                      Wajib, kecuali «@tanpa: pustaka»
  **...**             tebal
  {Q:s:a} {Q:s:a-b} {Q:s:a:i-j}   ayat surat s ayat a (atau a-b; atau kata ke-i s.d. j): teks resmi rasm Utsmani + masuk فهرس الآيات
  {H:طرف|راوٍ|kunci}   daftarkan hadits/atsar ke فهرس الأحاديث; taruh tepat sebelum «matan». Kunci: huruf kecil a-z, satu kunci satu hadits
  {H2:kunci}          halaman tambahan untuk hadits yang sama
  {P:kunci}           nomor halaman {H:..|kunci}; hanya di dalam catatan kaki: [^سبق تخريجه، ص{P:kunci}.]
  [^ ... ]            catatan kaki
  <<sid|juz|hal>>     bukti di dalam catatan kaki (tidak ikut tercetak): kutipan bertanda petik tepat sebelum catatan kaki
                      harus ada di kitab sid pada juz/hal itu, utuh per kata. Kutipan yang dipotong: tulis ... di tempat
                      potongannya; tiap bagian dicek, harus berurutan. Kutipan tanpa bukti = GAGAL
  <<sid|juz|hal|potongan>>   bukti dengan potongan teks sendiri (untuk nukilan makna «انظر», tanpa tanda petik); #123 = nomor hadits.
                      Kutipan bertanda petik sebelum catatan kaki tetap dicek ke halaman bukti itu
                      juz "-" = kitab satu jilid; hal boleh rentang 12-14
  <<luar>>            kutipan dari sumber yang tidak ada di Shamela (jurnal, PDF penelitian): lolos, tetapi masuk
                      perhatian; lafaz dan halamannya dicocokkan sendiri ke sumbernya. Judul kitab Shamela = GAGAL
  Tanda petik yang dikenali: "…" «…» “…” ‘…’ '…'. Perhatian: kutipan yang dipotong ... di tengahnya atau disambung ...
                      dengan kutipan lain, dan tanda petik tanpa pasangan
  Judul (#K/#F/#B/#M/#S/#R) tidak boleh memuat [^, <<, {Q:/{H: atau **
  Contoh: قال ابن القيم: "…"[^مدارج السالكين، ابن القيم، 2/15. <<8370|2|15>>].
"""
import functools, json, re
from pathlib import Path

import shamela

HERE = Path(__file__).parent
QURAN = json.load(open(HERE / "quran_hafs_v22.json", encoding="utf8"))
SURAH = json.load(open(HERE / "nama_surah.json", encoding="utf8"))
FORMAT = json.load(open(HERE / "format.json", encoding="utf8"))  # huruf & ukuran tiap pedoman; dipilih dengan @format
WAJIB = ("judul", "jenis", "nama", "nim", "fasl")
TANPA = ("ayat", "hadits", "maudhuat", "pustaka")  # فهرس dan المصادر yang boleh dibuang lewat @tanpa; perakitnya di rakit.ps1

HARAKAT = shamela.HARAKAT
AD = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
ANGKA_LATIN = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 2)  # angka Arab dan Persia -> 0-9


@functools.cache
def kitab(sid):
    """Rekaman kitab per juz ({part: [rekaman]}); tiap rekaman diberi «_akhir», halaman cetak terakhirnya."""
    juz = {}
    for r in shamela._pages(sid):
        r["_akhir"] = max([r.get("page_num") or 0] + [int(n) for n in shamela.PENANDA.findall(r.get("body") or "")])
        juz.setdefault(r.get("part"), []).append(r)
    return juz


def rekaman(sid, juz, p1=0, p2=float("inf")):
    """Rekaman juz itu (juz "-" = semua) yang menyentuh halaman p1..p2."""
    semua = [r for rr in kitab(sid).values() for r in rr] if juz == "-" else kitab(sid)[juz]
    return [r for r in semua if r["_akhir"] >= p1 and (r.get("page_num") or 0) <= p2]


def urut_juz(j):
    """Juz berangka dulu menurut angkanya, lalu yang bernama (mis. المقدمة)."""
    return (not str(j).isdigit(), str(j).zfill(4))


# kalimat di kartu kitab Shamela yang berarti nomor halamannya bukan nomor cetakan
OTOMATIS = re.compile("مرقمة? آليا|بترقيم الشاملة")
NASKAH_TULISAN = re.compile("(?:الكتاب|البحث) (?:مخطوط|غير مطبوع)")  # nomornya nomor lembar naskah tulisan/ketikan
KUTIPAN_MIN = 6  # huruf (bentuk `padat`) paling sedikit tiap bagian kutipan yang dicek
POTONGAN_MIN = 7  # huruf paling sedikit potongan sendiri <<sid|juz|hal|potongan>> (potongan sah terpendek di bahts nyata: 7)
AYAT_DI_KUTIPAN = "﴿﴾"  # pengganti {Q:} di tengah kutipan: kutipannya dicek per bagian seperti dipotong ...
DIPOTONG = re.compile(r"\.{2,}|…")  # potongan oleh penulis: yang dilompati tidak dicek mesin, jadi selalu perhatian
ELIPSIS = re.compile(f"{DIPOTONG.pattern}|{AYAT_DI_KUTIPAN}")  # pemisah bagian kutipan: tiap bagiannya dicek, berurutan
JARAK_AYAT = 300  # huruf `padat` kitab di antara bagian kutipan yang dipisah ayat sebelum jadi perhatian
LUAR = "luar"  # <<luar>>: sumbernya bukan kitab Shamela (jurnal, PDF penelitian, kamus); tidak bisa dicek mesin
NAFI = {"لا", "فلا", "ولا", "ما", "فما", "وما", "ليس"}  # kata tepat sebelum kutipan di kitab yang bisa membalik maknanya


def salah_juz(sid, juz, hal):
    """'' kalau kitab sid sudah diunduh dan punya juz itu; selain itu pesan kesalahannya."""
    if not (shamela.ROOT / str(sid) / "pages.jsonl.gz").exists():
        return f"kitab {sid} belum diunduh (python mesin/bahts.py ambil {sid})"
    juz_ada = set(kitab(sid))
    # kitab satu jilid = satu nilai juz saja, atau bagiannya hanya bernama (mis. المقدمة + الكتاب) tanpa juz berangka
    if juz == "-" and len(juz_ada) > 1 and any(str(j).isdigit() for j in juz_ada):
        contoh = sorted(juz_ada, key=urut_juz)[0]
        return f"kitab {sid} berjilid: tulis juz-nya, mis. <<{sid}|{contoh}|{hal}>> (juz \"-\" hanya untuk kitab satu jilid)"
    if juz != "-" and juz not in juz_ada:
        if juz_ada == {None}:
            return f"kitab {sid} satu jilid: tulis juz \"-\", mis. <<{sid}|-|{hal}>>"
        return f"kitab {sid} tidak punya juz {juz} (yang ada: {'، '.join(sorted(juz_ada - {None}, key=urut_juz))})"
    return ""


def _di(sid, juz, p1, p2, q, utuh):
    """Cari q (sudah `padat`) di juz/halaman p1..p2, matan dan حاشية per halaman.
    Kembalikan (jenis, None): jenis "matan", "hasyiah", atau "hasyiah?" (حاشية tanpa penanda halaman di rekaman
    banyak halaman); atau (None, (awal, akhir, tanda)) kalau hanya ada di halaman lain; atau (None, None)."""
    lain, hasyiah = None, None
    for r in rekaman(sid, juz, p1, p2):
        for bagian, tanda in shamela.BAGIAN:
            h = shamela.tempat(r, q, bagian, utuh)
            if not h:
                continue
            a, z = h[0] or 0, h[1] or 0
            if p1 <= a and z <= p2:
                if bagian == "body":
                    return "matan", None
                hasyiah = "hasyiah"
            elif bagian != "body" and a <= p2 and z >= p1 and h[0] != h[1]:
                hasyiah = hasyiah or "hasyiah?"
            else:
                lain = lain or (h[0], h[1], tanda)
            break
    if not hasyiah and len(rekaman(sid, juz, p1, p2)) > 1:  # kutipan yang menyambung dari satu rekaman ke berikutnya
        h = shamela.tempat(gabung(sid, juz, p1, p2), q, "body", utuh)
        if h and p1 <= (h[0] or 0) and (h[1] or 0) <= p2:
            return "matan", None
    return (hasyiah, None) if hasyiah else (None, lain)


@functools.cache
def gabung(sid, juz, p1, p2):
    """Matan rekaman-rekaman yang menyentuh halaman p1..p2 sebagai satu rekaman: awal tiap rekaman diberi penanda
    halaman ⦗n⦘, jadi kutipan yang menyambung lintas rekaman tetap dicek per kata dan halamannya tetap tercatat."""
    rr = rekaman(sid, juz, p1, p2)
    body = rr[0].get("body") or ""
    for r in rr[1:]:
        body += f" ⦗{str(r.get('page_num') or 0).translate(AD)}⦘ " + (r.get("body") or "")
    return {"body": body, "page_num": rr[0].get("page_num")}


def _petunjuk(sid, juz, q):
    """Tempat q di seluruh kitab untuk pesan kesalahan: matan dulu (juz yang ditulis didahulukan), baru حاشية."""
    tempat, hasyiah = [], None
    for r in rekaman(sid, "-"):
        h = shamela.tempat(r, q)
        if h:
            t = (shamela._juz(r) != juz, shamela.letak(shamela._juz(r), h))
            if t not in tempat:
                tempat.append(t)
        elif not hasyiah:
            h = shamela.tempat(r, q, "footnotes")
            if h:
                hasyiah = shamela.letak(shamela._juz(r), h) + " [حاشية]"
    if tempat:
        tempat = [t for _, t in sorted(tempat, key=lambda t: t[0])]
        lagi = f" (dan {len(tempat) - 3} tempat lain)" if len(tempat) > 3 else ""
        return "، ".join(tempat[:3]) + lagi
    return hasyiah


def _cek_bagian(sid, juz, hal, p1, p2, teks, utuh, perhatian):
    """Cek satu teks (kutipan, satu bagian kutipan berelipsis, atau potongan) di juz/hal; '' kalau cocok."""
    q = shamela.padat(teks)
    jenis, lain = _di(sid, juz, p1, p2, q, utuh)
    if jenis == "hasyiah":
        perhatian.append(f"bukti ada di حاشية المحقق, bukan di matan kitab {sid} {juz}/{hal}: "
                         f"itu kalimat muhaqqiq, bukan pengarang :: {teks[:40]}")
    elif jenis == "hasyiah?":
        perhatian.append(f"bukti ada di حاشية المحقق {sid} {juz}/{hal}, tetapi halaman tiap catatan di rekaman ini tidak tercatat: "
                         f"pastikan halamannya dengan `halaman`; itu kalimat muhaqqiq, bukan pengarang :: {teks[:40]}")
    if jenis:
        return ""
    if utuh and _di(sid, juz, p1, p2, q, False)[0]:
        return (f"kutipan mulai atau berakhir di tengah kata (kitab {sid} {juz}/{hal}): salin kata pertama dan terakhirnya utuh, "
                f"lihat `teks {sid} \"…\"` :: {teks[:40]}")
    if lain:
        return f"teks ada tapi di {shamela.letak(juz, lain[:2])}{lain[2]}, bukan {hal} ({sid}) :: {teks[:40]}"
    ada = _petunjuk(sid, juz, q)
    if ada:
        return f"teks TIDAK di {juz}/{hal}; ketemu di {ada} ({sid}) :: {teks[:40]}"
    beda = _menyimpang(sid, juz, p1, p2, teks)
    if beda:
        return f"teks berbeda dengan kitab {sid} {juz}/{hal}: {beda} :: {teks[:40]}"
    return f"teks TIDAK KETEMU di kitab {sid} :: {teks[:60]}"


def _menyimpang(sid, juz, p1, p2, teks):
    """Kata pertama kutipan yang berbeda dengan matan halaman itu: awalan terpanjang kutipan yang ada di matan,
    lalu kata sesudahnya di naskah dan di kitab. '' kalau awalannya terlalu pendek untuk ditunjuk."""
    if not rekaman(sid, juz, p1, p2):
        return ""
    raw = re.sub(r"\s+", " ", shamela.HARAKAT.sub("", shamela.TAGS.sub("", gabung(sid, juz, p1, p2)["body"])))
    raw = shamela.PENANDA.sub(" ", raw)
    kitab_padat, kata = shamela.padat(raw), teks.split()
    lo, hi = 0, len(kata) - 1  # awalan sepanjang kata[:lo] ada di matan; kata[:hi+1] tidak (kutipan utuhnya tidak ketemu)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if shamela.padat(" ".join(kata[:mid])) in kitab_padat:
            lo = mid
        else:
            hi = mid - 1
    awalan = shamela.padat(" ".join(kata[:lo]))
    if lo < 2 or len(awalan) < KUTIPAN_MIN:
        return ""
    akhir = kitab_padat.find(awalan) + len(awalan)
    sesudah = [m.start() for m in re.finditer(r"\S+", raw) if len(shamela.padat(raw[:m.start()])) >= akhir]
    di_kitab = raw[sesudah[0]:].split()[0].strip(".,،؛:!؟\"«»()") if sesudah else "(akhir halaman)"
    return f"cocok {lo} dari {len(kata)} kata sampai «…{' '.join(kata[max(0, lo - 3):lo])}», lalu naskah «{kata[lo]}», kitab «{di_kitab}»"


def cek(sid, juz, hal, pot, perhatian, kutipan=False):
    """Kembalikan '' kalau pot ada di kitab sid juz/hal, atau pesan kesalahan.
    kutipan=True: pot = kutipan bertanda petik di naskah. Ia harus mulai dan berakhir di batas kata kitab, boleh dipotong
    dengan ... (tiap bagian dicek, harus berurutan); angka dan kata nafi sebelumnya diperiksa sebagai perhatian.
    Yang lolos tetapi harus dilihat orang (bukti di حاشية, nomor halaman bukan cetakan) ditambahkan ke `perhatian`."""
    e = salah_juz(sid, juz, hal)
    if e:
        return e
    if OTOMATIS.search(shamela.info(sid)["betaka_text"]):
        pesan = (f"kitab {sid}: nomor halamannya buatan Shamela (مرقم آليا), bukan nomor cetakan — "
                 "pakai edisi yang «موافق للمطبوع», atau cocokkan ke cetakannya")
        if not any(p.endswith(pesan) for p in perhatian):  # sekali per kitab, walau tiap baris diberi awalan
            perhatian.append(pesan)
    elif NASKAH_TULISAN.search(shamela.info(sid)["betaka_text"]):
        pesan = (f"kitab {sid}: belum dicetak (مخطوط/غير مطبوع), nomor halamannya nomor lembar naskah — sebut lembarnya "
                 "(مخطوط، ل n) atau pakai edisi cetak kalau ada")
        if not any(p.endswith(pesan) for p in perhatian):
            perhatian.append(pesan)
    p1, _, p2 = hal.partition("-")
    p1 = int(p1); p2 = int(p2) if p2 else p1
    if p2 < p1:
        return f"rentang halaman terbalik: {hal}"
    if pot.startswith("#") and not kutipan:
        nomor = pot[1:].translate(ANGKA_LATIN)
        for r in rekaman(sid, juz, p1, p2):
            if re.search(rf"(?<!\d){re.escape(nomor)}(?!\d)", angka_kitab(r.get("body") or "")):
                return ""
        return f"nomor {pot[1:]} tidak ada di {sid} {juz}/{hal}"
    bagian = [b for b in ELIPSIS.split(pot) if shamela.padat(b)]
    if not bagian:
        return f"{'kutipan' if kutipan else 'potongan'} tanpa huruf Arab: {pot[:40]}"
    minimal = KUTIPAN_MIN if kutipan else POTONGAN_MIN
    for b in bagian:
        if len(shamela.padat(b)) < minimal:
            if kutipan:
                return f"bagian kutipan terlalu pendek untuk dicek (paling sedikit {minimal} huruf; jangan dipotong ... di situ) :: {b}"
            return f"potongan terlalu pendek (paling sedikit {minimal} huruf; yang pendek cocok di sembarang tempat): {pot}"
    for b in bagian:
        e = _cek_bagian(sid, juz, hal, p1, p2, b, kutipan, perhatian)
        if e:
            return e
    rr = rekaman(sid, juz, p1, p2)
    if len(bagian) > 1:
        jarak = [j for j in (berurutan(rr, sisi, bagian) for sisi, _ in shamela.BAGIAN) if j is not None]
        if not jarak:
            return f"bagian kutipan yang dipisah ... tidak berurutan seperti di kitab {sid} {juz}/{hal} :: {pot[:40]}"
        # dipotong ...: sambungan yang rapat pun bisa mengubah makna atau pembicaranya; dipisah ayat: hanya kalau berjauhan
        if min(jarak) and (DIPOTONG.search(pot) or min(jarak) > JARAK_AYAT):
            perhatian.append(f"kutipan dipotong ... atau dipisah ayat ({min(jarak)} huruf kitab dilompati) {sid} {juz}/{hal}: "
                             f"baca yang dilompati, pastikan makna dan pembicaranya tetap :: {pot[:40]}")
    if kutipan:
        perhatian += [f"{p} ({sid} {juz}/{hal}) :: {pot[:40]}" for p in ragu_kutipan(rr, bagian[0], pot)]
    return ""


def berurutan(rr, sisi, bagian):
    """Kalau bagian-bagian kutipan muncul berurutan di sisi (matan/حاشية) rekaman rr: jarak terbesar di antaranya
    (huruf `padat`), dengan susunan yang paling rapat. None kalau tidak berurutan."""
    teks = "".join(shamela._ruas(r, sisi)[0] for r in rr)
    bagian = [shamela.padat(b) for b in bagian]
    terbaik, j = None, teks.find(bagian[0])
    while j >= 0:  # tiap letak bagian pertama; bagian berikutnya diambil yang terdekat
        k, jarak = j + len(bagian[0]), 0
        for b in bagian[1:]:
            n = teks.find(b, k)
            if n < 0:
                return terbaik  # letak bagian pertama yang lebih belakang juga tidak akan berurutan
            jarak, k = max(jarak, n - k), n + len(b)
        terbaik = jarak if terbaik is None else min(terbaik, jarak)
        j = teks.find(bagian[0], j + 1)
    return terbaik


def angka_kitab(t):
    """Teks kitab dengan angka 0-9 yang memang bagian kalimat: penanda halaman ⦗n⦘, nomor catatan kaki yang menempel
    kata («الجدال١») atau bertanda «(¬n)», dan angka di dalam tag HTML dibuang; «(٨٥)» (nomor hadits) tetap."""
    t = shamela.PENANDA.sub(" ", shamela.TAGS.sub(" ", t))
    t = re.sub(r"(?<=[ء-ي])[٠-٩۰-۹]+|\(¬\s*[٠-٩۰-۹0-9]+\s*\)|^\s*\([٠-٩۰-۹0-9]+\)", " ", t, flags=re.M)
    return t.translate(ANGKA_LATIN)


def ragu_kutipan(rr, awal, pot):
    """Yang tidak diperiksa pencocokan huruf: angka di kutipan, dan kata nafi tepat sebelum kutipan di matan kitab."""
    ragu = []
    angka = set(re.findall(r"\d+", pot.translate(ANGKA_LATIN)))
    if angka:
        ada = set()
        for r in rr:
            ada |= set(re.findall(r"\d+", angka_kitab(r.get("body") or "") + " " + angka_kitab(r.get("footnotes") or "")))
        if angka - ada:
            ragu.append(f"angka {'، '.join(sorted(angka - ada))} di kutipan tidak terbaca di halaman itu: cocokkan sendiri")
    q = shamela.padat(awal)
    for r in rr:
        c = shamela._cocok(r, q, "body", True)
        if c:
            teks, mulai = shamela._ruas(r, "body")[0], sorted(shamela._batas_kata(r, "body")[0])
            sebelum = [a for a in mulai if a <= c[0]]  # awal kata kutipan (huruf sambung و/ف ikut kata itu)
            if len(sebelum) > 1 and teks[sebelum[-2]:sebelum[-1]] in NAFI:
                ragu.append(f"di kitab tepat sebelum kutipan ada «{teks[sebelum[-2]:sebelum[-1]]}»: pastikan maknanya tidak terbalik")
            break
    return ragu


def tercetak(isi, juz):
    """Rentang halaman yang tercetak di catatan kaki untuk juz ini: [(awal, akhir)]. Angka ٠-٩ dibaca seperti 0-9."""
    isi = isi.translate(ANGKA_LATIN)
    pola = r"ص\s*(\d+)(?:\s*-\s*(\d+))?" if juz == "-" else rf"(?<![\d/]){re.escape(juz)}\s*/\s*(\d+)(?:\s*-\s*(\d+))?"
    return [(int(a), int(b or a)) for a, b in re.findall(pola, isi)]


def cocok_halaman(isi, bukti):
    """Bandingkan juz/halaman yang tercetak dengan bukti [(sid, juz, p1, p2)]; kembalikan daftar galat.
    «سبق تخريجه» mencetak halaman bahts ({P:}), bukan halaman kitab: yang dicek hanya halaman kitab yang tercetak."""
    if not bukti:
        return []
    galat = []
    for juz in {b[1] for b in bukti}:
        ada = {n for _, z, p1, p2 in bukti if z == juz for n in range(p1, p2 + 1)}
        galat += [f"halaman tercetak {juz}/{a}{'-' + str(b) if b != a else ''} tidak punya bukti"
                  for a, b in tercetak(isi, juz) if b - a > 50 or not set(range(a, b + 1)) & ada]
    for sid in {b[0] for b in bukti} if "سبق تخريجه" not in isi else ():
        if not any(a <= p1 and p2 <= b for s, z, p1, p2 in bukti if s == sid for a, b in tercetak(isi, z)):
            galat.append(f"juz/halaman bukti kitab {sid} tidak tercetak di catatan kaki")
    return [f"{g} || fn: {isi[:60]}" for g in galat]


def ayat(spec):
    """'s:a' | 's:a-b' | 's:a:i-j' -> (teks_utsmani, surah, 'a' atau 'a-b')."""
    p = spec.split(":")
    if len(p) not in (2, 3) or not all(re.fullmatch(r"\d+(-\d+)?", x) for x in p):
        raise ValueError(f"{{Q:{spec}}}: bentuknya {{Q:surat:ayat}}, {{Q:surat:a-b}}, atau {{Q:surat:ayat:i-j}}")
    s = int(p[0])
    if any(f"{s}:{n}" not in QURAN for n in map(int, p[1].split("-"))):
        raise ValueError(f"{{Q:{spec}}}: surat/ayat itu tidak ada")
    if "-" in p[1]:
        a, b = map(int, p[1].split("-"))
        if a > b:
            raise ValueError(f"{{Q:{spec}}}: rentang ayat harus dari kecil ke besar")
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
            raise ValueError(f"{{Q:{spec}}}: ayat itu hanya {len(t.split())} kata")
        t = " ".join(t.split()[i - 1: j])
    return t, s, p[1]


# tanda petik miring dari Word/HP dan bentuk jarang dibaca seperti " « » ‘
PETIK = str.maketrans("“”„＂‹›﹁﹂「」‚‛", '""""«»«»«»‘‘')
HURUF_LATIN = "A-Za-zÀ-ɏḀ-ỿ"  # huruf Latin, juga transliterasi (ā ī ū ḥ)
# petik tunggal ‘…’ ’…‘ '…' yang isinya huruf Arab dibaca seperti «…». Apostrof transliterasi (Qur'an, 'Uthaymin,
# ‘Abduh) bukan tanda petik: petik yang menempel huruf Latin di sisi mana pun tidak dihitung
TUNGGAL = re.compile(rf"(?<![{HURUF_LATIN}])[‘’'](?![{HURUF_LATIN}])([^‘’'\n«»\"]*[ء-ي][^‘’'\n«»\"]*)(?<![{HURUF_LATIN}])[‘’'](?![{HURUF_LATIN}])")
SISA_PETIK = re.compile(rf"[\"«»]|(?<![{HURUF_LATIN}])[‘’'](?![{HURUF_LATIN}])")  # tanda petik yang tidak berpasangan


def seragam(teks):
    """Semua bentuk tanda petik jadi " atau «» (panjang teks tetap)."""
    return TUNGGAL.sub(lambda m: f"«{m.group(1)}»", teks.translate(PETIK))


def luar_petik(teks):
    """Teks tanpa kutipan-kutipannya (pasangan «…» dan "…" dibuang, dari yang terdalam); yang tersisa: teks penulis
    dan tanda petik yang tidak berpasangan."""
    teks, lama = seragam(teks), None
    while teks != lama:
        teks, lama = re.sub(r'«[^«»]*»|"[^"«»]*"', " ", teks), teks
    return teks

AKHIR_NUKILAN = re.compile(r'(?<=["»])[\s.،؛]*(?:اهـ|انتهى(?:\s+كلامه)?)[\s.]*$')  # «"…". اهـ» = akhir nukilan, kutipannya tetap dicek


def kutipan_semua(teks):
    """Isi tiap kutipan teratas "..." atau «...» di teks, urut dari depan; kutipan di dalam kutipan ikut induknya."""
    teks, out, i = seragam(teks), [], 0
    while i < len(teks):
        if teks[i] == "«":
            d, j = 1, i + 1
            while d and j < len(teks):
                d += (teks[j] == "«") - (teks[j] == "»"); j += 1
        elif teks[i] == '"':
            d, j = 0, teks.find('"', i + 1) + 1
        else:
            i += 1; continue
        if d or j <= i:
            break  # tidak tertutup
        out.append(teks[i + 1:j - 1]); i = j
    return out


def kutipan_akhir(teks):
    """Isi kutipan "..." atau «...» yang menutup teks (tanda baca sesudahnya boleh), termasuk kutipan di dalamnya:
    «قال: "…" ثم سكت» -> seluruh isi «…». None kalau teks tidak berakhir dengan kutipan."""
    teks = AKHIR_NUKILAN.sub("", seragam(teks)).rstrip(" \t.،؛!؟")
    tunggu = []  # tanda pembuka yang dicari, dari belakang
    for i in range(len(teks) - 1, -1, -1):
        c = teks[i]
        if c == "»" or (c == '"' and tunggu[-1:] != ['"']):
            tunggu.append("«" if c == "»" else '"')
        elif tunggu and c == tunggu[-1]:
            tunggu.pop()
        elif c == "«" and "«" in tunggu:  # " yang tidak berpasangan di dalam «…» diabaikan
            del tunggu[len(tunggu) - 1 - tunggu[::-1].index("«"):]
        elif not tunggu:
            return None
        if not tunggu:
            return teks[i + 1:-1]
    return None


AWALAN_RUJUKAN = re.compile(r"^(?:انظر|ينظر|راجع|كتاب)\s*:?\s*")
PEMISAH_RUJUKAN = re.compile(r"[،,.():؛«»\"\-–]")
MAJALAH = "مجلة"  # judul jurnal: terbitannya belum tentu ada di Shamela, jadi kemiripan judul cukup perhatian


PENGARANG_SESUDAH = re.compile(r"^(?:للشيخ|للإمام|للعلامة|للحافظ|للقاضي|لابن|لأبي|لأبى)$")  # «… للشيخ ابن عثيمين»


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


TOKEN = re.compile(r"(\*\*|\{(?:Q|H2|H|P):[^}]*\}|\[\^|\])")


KUNCI = re.compile(r"[a-z]+")


def urai(teks, catatan, ayat_idx, hadits_idx, galat, perhatian, di_catatan=False):
    """Pecah satu baris jadi 'runs'. Catatan kaki ([^...]) diurai rekursif."""
    runs, tebal, i = [], False, 0
    q_akhir = None  # ayat terakhir di baris ini (untuk mencocokkan catatan kaki «سورة …»)
    polos = ""  # teks polos berjalan (untuk mencari kutipan sebelum catatan kaki)
    seg = 0  # awal teks polos sesudah catatan kaki terakhir
    while i < len(teks):
        m = TOKEN.search(teks, i)
        if not m:
            runs.append({"t": teks[i:], "b": tebal}); polos += teks[i:]; break
        if m.start() > i:
            runs.append({"t": teks[i:m.start()], "b": tebal}); polos += teks[i:m.start()]
        tok = m.group(1)
        i = m.end()
        if tok == "**":
            tebal = not tebal
        elif tok.startswith("{Q:"):
            t, s, a = ayat(tok[3:-1])
            q_akhir = (s, a)
            polos += f" {AYAT_DI_KUTIPAN} "
            runs.append({"t": "﴿", "b": False}); runs.append({"t": t, "q": True}); runs.append({"t": "﴾", "b": False})
            if not di_catatan:
                kunci = f"q{len(ayat_idx)}"
                ayat_idx.append({"k": kunci, "t": t, "s": s, "a": a})
                runs.insert(len(runs) - 3, {"bm": kunci})
        elif tok.startswith("{H2:"):
            kunci = "h_" + tok[4:-1]
            induk = next((r for r in hadits_idx if r["k"] == kunci), None)
            if not induk:
                raise ValueError(f"{tok}: belum ada {{H:...|{tok[4:-1]}}} sebelumnya")
            n = 1 + len(induk.setdefault("lagi", []))
            induk["lagi"].append(f"{kunci}_{n}")
            runs.append({"bm": f"{kunci}_{n}"})
        elif tok.startswith("{H:"):
            if tok.count("|") != 2:
                raise ValueError(f"{tok}: bentuknya {{H:طرف|راوٍ|kunci}}")
            taraf, rawi, kunci = tok[3:-1].split("|")
            if not KUNCI.fullmatch(kunci):
                raise ValueError(f"{tok}: kunci hanya boleh huruf a-z")
            if any(r["k"] == "h_" + kunci for r in hadits_idx):
                raise ValueError(f"{tok}: kunci «{kunci}» sudah dipakai (pakai {{H2:{kunci}}})")
            hadits_idx.append({"k": "h_" + kunci, "t": taraf, "r": rawi})
            runs.append({"bm": "h_" + kunci})
        elif tok.startswith("{P:"):
            if not di_catatan:
                raise ValueError(f"{tok}: hanya boleh di dalam catatan kaki")
            if not any(r["k"] == "h_" + tok[3:-1] for r in hadits_idx):
                raise ValueError(f"{tok}: belum ada {{H:...|{tok[3:-1]}}} sebelumnya")
            runs.append({"pg": "h_" + tok[3:-1]})
        elif tok == "[^":
            if di_catatan:
                raise ValueError("catatan kaki tidak boleh di dalam catatan kaki: tutup yang pertama dengan ] dulu")
            # cari penutup ]; isi bukti <<...>> dilewati (potongannya boleh memuat ])
            j = i
            while j < len(teks) and teks[j] != "]":
                if teks.startswith("[^", j):
                    raise ValueError("catatan kaki tidak boleh di dalam catatan kaki: tutup yang pertama dengan ] dulu")
                tutup = teks.find(">>", j + 2) if teks.startswith("<<", j) else -1
                j = tutup + 2 if tutup >= 0 else j + 1
            if j >= len(teks):
                raise ValueError("catatan kaki [^ tidak ditutup dengan ]")
            isi = teks[i:j]
            i = j + 1
            bukti = re.findall(r"<<([^>]*)>>", isi)
            isi = re.sub(r"\s*<<[^>]*>>", "", isi).strip()
            if "<<" in isi or ">>" in isi:
                raise ValueError("bukti <<...>> tidak tertutup rapi (tidak boleh ada > di dalam potongan)")
            if isi.startswith("سورة") and q_akhir:
                s, a = q_akhir
                nama = re.split(r"[،,:(]|\sآي", isi[4:])[0]  # «سورة الفاتحة، آية: 2.» -> «الفاتحة»
                angka = isi.translate(ANGKA_LATIN)
                if shamela.padat(nama) != shamela.padat(SURAH[s - 1]) or not all(re.search(rf"(?<!\d){x}(?!\d)", angka) for x in a.split("-")):
                    galat.append(f"catatan kaki ayat tidak cocok dengan {{Q:{s}:{a}}} (سورة {SURAH[s - 1]}) || fn: {isi[:45]}")
            # kutipan terakhir tepat sebelum catatan kaki; kutipan lain sejak catatan kaki sebelumnya tidak punya catatan kaki sendiri
            mk = kutipan_akhir(polos)
            lain = kutipan_semua(polos[seg:])[:-1 if mk is not None else None]
            sisa = luar_petik(polos[seg:])  # teks sejak catatan kaki sebelumnya, kutipan-kutipannya dibuang
            if mk is None and bukti and SISA_PETIK.search(sisa):
                perhatian.append(f"tanda petik tanpa pasangan sebelum catatan kaki: kutipannya tidak dikenali dan tidak dicek; "
                                 f"pakai \"…\" atau «…»  || fn: {isi[:45]}")
            if lain and DIPOTONG.search(sisa):  # «"…" ... "…"»: dua kutipan disambung elipsis di luar petik
                perhatian.append(f"kutipan disambung ... di luar tanda petik: baca yang dilompati di kitab, pastikan makna dan "
                                 f"pembicaranya tetap  || fn: {isi[:45]}")
            seg = len(polos)
            luar = LUAR in bukti
            bukti = [b for b in bukti if b != LUAR]
            terbukti = []  # (sid, juz, p1, p2) tiap bukti, untuk dicocokkan dengan yang tercetak
            kutipan_4 = []  # hasil cek kutipan ke tiap bukti berpotongan sendiri: (pesan, perhatian)
            tiga = any(b.count("|") == 2 for b in bukti)
            for b in bukti:
                f = b.split("|")
                if len(f) not in (3, 4) or not re.fullmatch(r"\d+", f[0]) or not re.fullmatch(r"\d+(-\d+)?", f[2]):
                    raise ValueError(f"<<{b}>>: bentuknya <<sid|juz|hal>> atau <<sid|juz|hal|potongan>>")
                e = salah_juz(int(f[0]), f[1], f[2])
                if e:  # juz/halamannya belum bisa dibandingkan dengan yang tercetak: satu galat saja
                    galat.append(e + f"  || fn: {isi[:45]}"); continue
                terbukti.append((f[0], f[1], *map(int, (f[2] + "-" + f[2]).split("-")[:2])))
                if len(f) == 3:
                    if mk is None:
                        galat.append(f"[tanpa kutipan] {isi[:50]}"); continue
                    e = cek(int(f[0]), f[1], f[2], mk, perhatian, kutipan=True)
                else:
                    e = cek(int(f[0]), f[1], f[2], f[3], perhatian)
                    if not e and mk is not None and not tiga:
                        p = []
                        kutipan_4.append((cek(int(f[0]), f[1], f[2], mk, p, kutipan=True), p))
                if e:
                    galat.append(e + f"  || fn: {isi[:45]}")
            # kutipan bertanda petik tetap dicek walau buktinya membawa potongan sendiri: cukup ada di salah satu bukti itu
            if kutipan_4 and all(e for e, _ in kutipan_4):
                galat.append(f"kutipan sebelum catatan kaki tidak ada di halaman buktinya (potongan <<…|potongan>> hanya "
                             f"membuktikan potongannya; nukilan makna tanpa tanda petik, diawali انظر): {kutipan_4[0][0]}  || fn: {isi[:45]}")
            else:
                perhatian += next((p for e, p in kutipan_4 if not e), [])
            # kutipan lain sejak catatan kaki sebelumnya: perhatian, kecuali yang terbaca di halaman bukti catatan kaki ini
            # atau yang memang judul yang disebut di catatan kaki itu; tiga kata atau kurang biasanya istilah
            for k in lain:
                if len(k.split()) < 4 or shamela.padat(k) in shamela.padat(isi):
                    continue
                if any(not cek(int(s), z, f"{a}-{b}", k, [], kutipan=True) for s, z, a, b in terbukti):
                    continue
                perhatian.append(f"kutipan tanpa catatan kaki sendiri (hanya kutipan tepat sebelum [^ yang dicek): «{k[:40]}» || fn: {isi[:45]}")
            # pengecualian: rujukan ayat «سورة …» sesudah {Q:}, dan «سبق تخريجه، ص{P:…}» (buktinya di catatan kaki pertama)
            dikecualikan = (isi.startswith("سورة") and q_akhir) or (isi.startswith("سبق تخريجه") and "{P:" in isi)
            if not bukti and mk is not None and not dikecualikan:
                if luar:
                    # <<luar>> hanya untuk sumber yang memang tidak ada di Shamela: judul kitab Shamela = GAGAL
                    judul, persis, mirip = judul_shamela(isi)
                    if persis:
                        galat.append(f"«{judul}» ada di Shamela (nomor {'، '.join(map(str, persis))}): <<{LUAR}>> hanya untuk "
                                     f"sumber di luar Shamela; ambil kitabnya lalu tulis <<sid|juz|hal>>  || fn: {isi[:45]}")
                    else:
                        mirip = (f"; «{judul}» mirip kitab Shamela nomor {'، '.join(map(str, mirip[:3]))}: kalau itu sumbernya, "
                                 f"ambil lalu pakai <<sid|juz|hal>>") if mirip else ""
                        perhatian.append(f"kutipan «{mk[:30]}» dari sumber di luar Shamela (<<{LUAR}>>): mesin tidak bisa mengeceknya, "
                                         f"cocokkan sendiri lafaz dan halamannya ke sumbernya{mirip}  || fn: {isi[:45]}")
                else:
                    galat.append(f"kutipan «{mk[:30]}» tanpa bukti: tambahkan <<sid|juz|hal>> di catatan kakinya; "
                                 f"sumber yang tidak ada di Shamela (jurnal, PDF penelitian): tulis <<{LUAR}>>  || fn: {isi[:45]}")
            galat += cocok_halaman(isi, terbukti)
            sub = urai(isi, None, ayat_idx, hadits_idx, galat, perhatian, di_catatan=True)
            catatan.append({"runs": sub, "bukti": len(bukti), "luar": luar})
            runs.append({"fn": len(catatan) - 1})
        else:  # "]" nyasar
            runs.append({"t": "]", "b": tebal}); polos += "]"
    if tebal:
        raise ValueError("tanda ** tidak berpasangan")
    if re.search(rf"<<(?:\d+\||{LUAR}>>)", polos):
        raise ValueError("bukti <<...>> hanya boleh di dalam catatan kaki [^...]; di luar itu ia ikut tercetak")
    if re.search(r"\{(?:Q|H2|H|P):", polos):
        raise ValueError("tanda {Q:/{H:/{H2:/{P: tidak ditutup dengan }")
    return [r for r in runs if r.get("t", "x") != ""]


def utama(folder):
    """Olah naskah di `folder`. Kembalikan (jumlah galat, baris laporan)."""
    folder = Path(folder)
    try:
        baris = [(n, x.rstrip("\n")) for n, x in enumerate(open(folder / "naskah.txt", encoding="utf-8-sig"), 1) if x.strip()]
    except UnicodeDecodeError:
        raise SystemExit(f"{folder.name}/naskah.txt bukan UTF-8: buka di Notepad, File > Save As, pilih Encoding «UTF-8», "
                         "simpan, lalu ulangi `cek`.") from None
    blok, catatan, ayat_idx, hadits_idx, galat, perhatian, pustaka = [], [], [], [], [], [], []
    meta = {"berkas": folder.name}
    di_baris = {}  # @kunci dan #R -> nomor barisnya, untuk galat yang baru ketahuan sesudah semua baris dibaca
    mode_r = False
    for n, b in baris:
        g0, p0 = len(galat), len(perhatian)
        if b.startswith("@"):
            k, _, v = b[1:].partition(":")
            meta[k.strip()] = v.strip()
            di_baris["@" + k.strip()] = n
        elif b.startswith("#"):
            k, _, t = b[1:].partition(" ")
            if k not in ("K", "F", "B", "M", "S", "R") or not t.strip():
                galat.append(f"baris {n}: judul harus «#K/#F/#B/#M/#S/#R teks» :: {b[:40]}"); continue
            if re.search(r"\[\^|<<|\{|\*\*", t):  # judul tercetak apa adanya (juga di فهرس الموضوعات): tanda ini ikut tercetak
                galat.append(f"baris {n}: judul tidak boleh memuat catatan kaki [^, bukti <<, tanda {{Q:/{{H: atau **: "
                             f"pindahkan ke paragraf sesudahnya :: {b[:40]}"); continue
            mode_r = k == "R"
            if mode_r:
                di_baris["#R"] = n
            blok.append({"k": k, "runs": [{"t": t, "b": True}], "judul": t})
        elif mode_r:
            pustaka.append(b.strip())
        else:
            try:
                blok.append({"k": "P", "runs": urai(b, catatan, ayat_idx, hadits_idx, galat, perhatian)})
            except (ValueError, KeyError, IndexError) as e:
                galat.append(f"baris {n}: tanda rusak — {e}")
        # tiap galat dan perhatian menyebut barisnya: pemakai langsung tahu tempatnya, tes jebakan mencocokkan per baris
        galat[g0:] = [g if g.startswith("baris ") else f"baris {n}: {g}" for g in galat[g0:]]
        perhatian[p0:] = [p if p.startswith("baris ") else f"baris {n}: {p}" for p in perhatian[p0:]]

    def di(kunci):
        return f"baris {di_baris[kunci]}: " if kunci in di_baris else ""
    tanpa = [t for t in re.split(r"[,، ]+", meta.get("tanpa", "")) if t]
    if "pustaka" in tanpa:  # sumber cukup di catatan kaki (rujukan pertama tiap kitab berdata lengkap)
        if mode_r:
            galat.append(di("#R") + "@tanpa: pustaka, tetapi ada #R: hapus #R beserta daftarnya, atau hapus «pustaka» dari @tanpa")
    elif not mode_r:
        galat.append("tidak ada #R (المصادر والمراجع) di akhir naskah")
    elif not pustaka:
        galat.append(di("#R") + "المصادر والمراجع masih kosong: tulis satu kitab per baris sesudah #R")
    if not meta["berkas"]:
        meta["berkas"] = folder.name
    elif re.search(r'[<>:"/\\|?*]', meta["berkas"]):
        galat.append(di("@berkas") + f"@berkas: «{meta['berkas']}»: nama berkas tidak boleh memuat : / \\ ? * < > | \"")

    def kunci_urut(s):
        s = HARAKAT.sub("", s)
        if not s.startswith("الله"):
            s = re.sub(r"^ال", "", s)
        return re.sub("[إأآ]", "ا", s)
    quran = [p for p in pustaka if HARAKAT.sub("", p).startswith("القرآن")]  # tanpa nomor, paling atas
    pustaka = quran + sorted([p for p in pustaka if p not in quran], key=kunci_urut)

    for a in ayat_idx:
        a["surah"] = SURAH[a["s"] - 1]
    hadits_idx.sort(key=lambda h: kunci_urut(h["t"]))

    # hitung kata
    def kata(runs): return sum(len(re.findall(r"[؀-ۿ]+", r.get("t", ""))) for r in runs)
    n_matan = sum(kata(b["runs"]) for b in blok)
    n_fn = sum(kata(c["runs"]) for c in catatan)
    galat += [di("@" + k) + f"data sampul belum diisi: @{k}" for k in WAJIB if not meta.get(k)]
    asing = [t for t in tanpa if t not in TANPA]
    if asing:
        galat.append(di("@tanpa") + f"@tanpa: «{'، '.join(asing)}» tidak dikenal (yang ada: {', '.join(TANPA)})")
    if meta.get("thalibah", "ya") != "ya":
        galat.append(di("@thalibah") + f"@thalibah: «{meta['thalibah']}» tidak dikenal: tulis «ya», atau hapus barisnya")
    fmt = meta.get("format", "imam")
    if fmt not in FORMAT:
        galat.append(di("@format") + f"@format: «{fmt}» tidak ada di mesin/format.json (yang ada: {'، '.join(FORMAT)})")
    (HERE / "_tmp").mkdir(exist_ok=True)
    json.dump({"meta": meta, "format": FORMAT.get(fmt), "blok": blok, "catatan": catatan, "ayat": ayat_idx, "hadits": hadits_idx, "pustaka": pustaka,
               "quran": bool(quran)},
              open(HERE / "_tmp" / f"{folder.name}.json", "w", encoding="utf8"), ensure_ascii=False)
    n_bukti = sum(c["bukti"] for c in catatan)
    n_luar = sum(c["luar"] for c in catatan)  # disebut di ringkasan: tanda yang bisa menyembunyikan kutipan karangan
    fn_tanpa = [HARAKAT.sub("", "".join(r.get("t", "") for r in c["runs"]))[:60] for c in catatan
                if c["bukti"] == 0 and not "".join(r.get("t", "") for r in c["runs"]).startswith(("سورة", "سبق تخريجه"))]
    lap = [f"blok={len(blok)} | kata matan={n_matan} | catatan kaki={len(catatan)} ({n_fn} kata) | ayat={len(ayat_idx)} | hadits={len(hadits_idx)} | pustaka={len(pustaka)}",
           f"bukti dicek ke Shamela lokal: {n_bukti}{f' | <<{LUAR}>> (tidak dicek mesin): {n_luar}' if n_luar else ''} | GAGAL: {len(galat)}"]
    lap += [f"  ✗ {g}" for g in galat]
    lap.append(f"perhatian (lolos, tetapi lihat sendiri): {len(perhatian)}")
    lap += [f"  ! {p}" for p in perhatian]
    lap.append(f"catatan kaki tanpa bukti (selain rujukan ayat): {len(fn_tanpa)}")
    lap += [f"  - {f}" for f in fn_tanpa]
    return len(galat), lap
