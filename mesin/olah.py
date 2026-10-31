"""Olah <bahts>/naskah.txt -> bahan JSON terpisah menurut jalur bahts/pekerjaan (untuk perakit Word)
+ verifikasi setiap rujukan ke kitab Shamela lokal. Dipanggil lewat bahts.py.

Tanda di naskah.txt (dicetak oleh: python mesin/bahts.py tanda):
  @kunci: nilai       data sampul, di awal naskah; kunci tidak dikenal = GAGAL (salah ketik tidak diabaikan). Wajib: judul dan nama; @sampul: mahad juga jenis ("-" = tidak tercetak), nim, fasl.
                      Opsional: musyrif, jabatan (kosong atau "-" = tidak tercetak), thalibah (ya = sampul mencetak «اسم الطالبة»),
                      sampul (qism = model قسم الشريعة, bawaan: logo, judul besar, sub-judul dalam kurung,
                      العام الجامعي; jenis dan nim tercetak kalau diisi, fasl tidak; mahad = sampul معهد، كلية الشريعة),
                      tahun (العام الجامعي di sampul qism, mis. ١٤٤٨;
                      bawaan = tahun hijriah Umm al-Qura saat tahun ajaran mulai, 1 Agustus),
                      berkas (nama file hasil), format (profil di format.json; bawaan imam),
                      angka (hindi = ٠١٢٣، bawaan; latin = 0123): angka yang tercetak di seluruh PDF,
                      termasuk nomor halaman, nomor catatan kaki, dan فهرس. Naskah boleh ditulis dengan angka mana saja
                      angka_ayat (bawaan = @angka): angka di catatan kaki rujukan ayat [^سورة …، آية: n.] saja,
                      mis. «@angka_ayat: latin» = nomor ayat di catatan kaki 0123, sisanya tetap ٠١٢٣
                      tanpa (yang tidak dicetak: فهرس ayat, hadits, maudhuat, dan pustaka = المصادر والمراجع
                      bila dosen minta sumber cukup di catatan kaki; mis. «@tanpa: ayat, hadits»).
                      فهرس الآيات dan فهرس الأحاديث yang kosong tidak dicetak dengan sendirinya
                      templat (berkas .docx di folder bahts): Word mahasiswa sendiri; halaman pertamanya jadi sampul
                      apa adanya (data sampul di naskah tidak dipakai), kepala halamannya (termasuk judul di dalamnya) dipakai
                      di tiap halaman isi; nomor halaman di kaki hanya kalau kepala itu tidak memuat nomor halaman
                      halaman_baru (B, M, atau keduanya): judul itu juga mulai halaman baru, mis. dosen minta
                      مبحث dan مطلب beda halaman, مبحث = #F dan مطلب = #B → «@halaman_baru: B»
  @bentuk: kitab      bukan bahts (mis. muqarrar gabungan dua syarah): tanpa sampul bahts, wajib hanya @judul (tercetak di
                      kepala tiap halaman), #R tidak wajib, hanya #K (dan @halaman_baru) mulai halaman baru. Bawaan: bahts
  @rumuz: sid=ض، sid=ف  rumuz sumber: catatan kaki yang buktinya dari kitab sid itu dicetak dengan rumuznya ض (huruf kecil terangkat) tepat sebelum
                      nomor catatan kakinya. Rumuz diambil dari bukti, jadi tidak bisa berbeda dengan sumbernya
  @warna: sid=biru    paragraf yang buktinya [^<<sid|..>>] saja (sid juga di @rumuz) dicetak dengan warna itu + garis tegak di sisi kanan, mis. ziyadah
                      syarah kedua di dalam syarah pertama; lafaz matn ((…)) tetap merah. Warna yang ada: biru
  #K #F #B #M teks    judul tengah + masuk فهرس الموضوعات: K = مقدمة/خاتمة, F = فصل (keduanya mulai halaman baru), B = مبحث, M = مطلب.
                      Bahts pendek tanpa فصل: #F untuk مبحث, #B untuk مطلب. B/M halaman baru juga: @halaman_baru
  #S teks             sub-judul kanan (tidak masuk فهرس)
  #H                  pindah halaman: baris sesudahnya (judul, sub-judul, atau paragraf) mulai halaman baru,
                      mis. pembuka المقدمة satu halaman sendiri, lalu «#H» sebelum «#S أهمية الدراسة»
  #T teks             kotak matn: paragraf dalam bingkai, seluruhnya merah (boleh memuat catatan kaki)
  #R teks             awal المصادر والمراجع; sesudahnya satu kitab per baris (diurutkan abjad otomatis, القرآن الكريم paling atas).
                      Wajib, kecuali «@tanpa: pustaka»; semua bagian isi harus sebelum #R (tidak boleh ada judul/#T/#H sesudahnya)
  **...**             tebal
  ((...))             lafaz matn yang disyarah: dicetak merah di dalam kurung, «((ليس بحجة))» -> (ليس بحجة)
  {Q:s:a} {Q:s:a-b} {Q:s:a:i-j}   ayat surat s ayat a (atau a-b; atau kata ke-i s.d. j): teks resmi rasm Utsmani + masuk فهرس الآيات
  {H:طرف|راوٍ|kunci}   daftarkan hadits/atsar ke فهرس الأحاديث; taruh di matan, tepat sebelum «matan», bukan di catatan kaki. Kunci: huruf kecil a-z, satu kunci satu hadits
  {H2:kunci}          halaman tambahan untuk hadits yang sama
  {P:kunci}           nomor halaman {H:..|kunci}; hanya di dalam catatan kaki: [^سبق تخريجه، ص{P:kunci}.]
  [^ ... ]            catatan kaki
  <<sid|juz|hal>>     bukti di dalam catatan kaki (tidak ikut tercetak): kutipan bertanda petik tepat sebelum catatan kaki
                      harus ada di kitab sid pada juz/hal itu, utuh per kata. Kutipan yang dipotong: tulis ... di tempat
                      potongannya; tiap bagian dicek, harus berurutan. Kutipan tanpa bukti = GAGAL
  <<sid|juz|hal|potongan>>   bukti dengan potongan lafaz sendiri (untuk nukilan makna «انظر», tanpa tanda petik).
                      #123 = nomor hadits: harus berdiri sebagai kepala hadits di halaman itu («123 - حدثنا», «36 - (123)», «(123) - حدثنا»).
                      Kutipan bertanda petik sebelum catatan kaki tetap dicek ke halaman bukti itu
                      juz "-" = kitab satu jilid; hal boleh rentang 12-14
  [^<<sid|juz|hal>>]  catatan kaki berisi bukti saja, semua sid-nya ada di @rumuz: tidak dicetak; yang tercetak hanya
                      rumuznya ض (sid=- di @rumuz: tanpa rumuz, mis. kitab matn). Seluruh teks sejak catatan kaki
                      sebelumnya dicek sebagai nukilan utuh dari halaman itu (tanda ((…)) dan ** tidak ikut dicek)
  <<luar>>            kutipan dari sumber yang tidak ada di Shamela (jurnal, PDF penelitian): lolos, tetapi masuk
                      perhatian; lafaz dan halamannya dicocokkan sendiri ke sumbernya. Judul kitab Shamela = GAGAL
  <<luar|berkas.pdf|hal>>   kutipan dari PDF penelitian yang disimpan di folder bahts (mis. hasil dirasat-pdf):
                      kutipan bertanda petik dicari di teks PDF itu. hal = urutan halaman di berkas PDF (mulai 1),
                      bukan nomor tercetak jurnal; boleh rentang 3-4. Mesin hanya MENUNJUK halaman, tidak pernah lolos:
                      ada di halaman itu = perhatian «ditemukan di halaman …» (cocokkan sendiri lafaz, angka, urutan);
                      ada di halaman lain, berkas tidak ada atau di luar folder bahts, halaman di luar PDF, atau bagian
                      kutipan < 6 huruf = GAGAL; tidak ada di teks PDF atau scan = perhatian. Nukilan makna (انظر) = perhatian
  Tanda petik yang dikenali: "…" «…» “…” ‘…’ '…'. Perhatian: kutipan yang dipotong ... di tengahnya atau disambung ...
                      dengan kutipan lain, dan tanda petik tanpa pasangan
  Judul (#K/#F/#B/#M/#S/#R) tidak boleh memuat [^, <<, {Q:/{H: atau **
  Contoh: قال ابن القيم: "…"[^مدارج السالكين، ابن القيم، 2/15. <<8370|2|15>>].
"""
import difflib, functools, hashlib, io, json, os, re, unicodedata
from pathlib import Path

import shamela
import sumber_pdf
from berkas import bahan, sementara

HERE = Path(__file__).parent
QURAN = json.loads((HERE / "quran_hafs_v22.json").read_text(encoding="utf8"))
SURAH = json.loads((HERE / "nama_surah.json").read_text(encoding="utf8"))
FORMAT = json.loads((HERE / "format.json").read_text(encoding="utf8"))  # huruf & ukuran tiap pedoman; dipilih dengan @format
WAJIB = {"bahts": ("judul", "jenis", "nama", "nim", "fasl"), "kitab": ("judul",)}  # @bentuk: yang pertama = bawaan
# @sampul: model sampul bahts -> data yang wajib. Yang pertama = bawaan. mahad = mesin/sampul.doc (معهد، كلية الشريعة);
# qism = mesin/sampul_qism.docx (قسم الشريعة: logo, judul besar, sub-judul dalam kurung, العام الجامعي; jenis dan nim tercetak kalau diisi, fasl tidak)
SAMPUL = {"qism": ("judul", "nama"), "mahad": WAJIB["bahts"]}
HALAMAN_BARU = ("B", "M")  # judul yang bisa dibuat mulai halaman baru lewat @halaman_baru; K dan F selalu
TANPA = ("ayat", "hadits", "maudhuat", "pustaka")  # فهرس dan المصادر yang boleh dibuang lewat @tanpa; perakitnya di rakit.ps1
# @angka: yang pertama = bawaan. Pedoman Jāmiʿat al-Imām tidak menyebut jenis angka; contoh resminya (pedoman 1443هـ,
# مجلة العلوم الشرعية) memakai hindi di nomor halaman, catatan kaki, rujukan, tahun, ayat, dan فهرس
ANGKA = ("hindi", "latin")
META = frozenset("judul jenis nama nim fasl musyrif jabatan thalibah sampul tahun berkas format angka angka_ayat tanpa templat halaman_baru bentuk rumuz warna".split())
# @warna: nama -> RGB. Biru tua: tetap nyaman dibaca untuk paragraf panjang dan jelas beda dari hitam serta merah lafaz matn
WARNA = {"biru": (20, 60, 150)}
# lambang hormat Unicode 14 (﵀-﵏ ﷾ ﷿) tidak ada di huruf cetak (Traditional Arabic, Sakkal Majalla): kotak kosong di PDF.
# Dicetak dengan kalimatnya; `cek` sudah membuang keduanya (norma.LIGATUR_HORMAT, HORMAT)
HORMAT_CETAK = str.maketrans({
    "﵀": "رحمه الله", "﵁": "رضي الله عنه", "﵂": "رضي الله عنها", "﵃": "رضي الله عنهم",
    "﵄": "رضي الله عنهما", "﵅": "رضي الله عنهن", "﵆": "صلى الله عليه وآله", "﵇": "عليه السلام",
    "﵈": "عليهم السلام", "﵉": "عليهما السلام", "﵊": "عليه الصلاة والسلام", "﵋": "قدس سره",
    "﵌": "صلى الله عليه وآله وسلم", "﵍": "عليها السلام", "﵎": "تبارك وتعالى", "﵏": "رحمهم الله",
    "﷾": "سبحانه وتعالى", "﷿": "عز وجل"})

HARAKAT = shamela.HARAKAT
KUAT = re.compile(r"[^\W\d_]|[،؛؟]")  # huruf, atau tanda baca Arab (tanda teks Arab)


class TandaRusak(ValueError):
    """Tanda naskah yang salah tulis; pesannya untuk pemakai. ValueError lain dari dalam mesin = GALAT MESIN: tanpa
    pembeda ini, galat mesin di baris jebakan «#S GAGAL» terhitung sebagai galat yang diharapkan dan tidak ketahuan."""


def galat_mesin(n, e):
    return f"baris {n}: GALAT MESIN ({type(e).__name__}: {e}) — bukan salah naskah; laporkan barisnya ke pengurus mesin bahts"


def hindi(s):
    """Angka 0-9 -> ٠-٩, kecuali angka yang huruf atau tanda baca Arab terdekat sebelumnya (atau sesudahnya, kalau tidak
    ada) huruf Latin: tautan, DOI, dan judul berbahasa Latin tetap 0-9; «مجلة X، 2020» tetap ٢٠٢٠."""
    def ganti(m):
        kiri = KUAT.findall(s[:m.start()])
        c = kiri[-1] if kiri else next(iter(KUAT.findall(s[m.end():])), "")
        return m.group() if re.match(f"[{HURUF_LATIN}]", c) else m.group().translate(AD)
    return re.sub(r"[0-9]+", ganti, s)
AD = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
KEPALA_HADITS = re.compile(r"^[ \t\u200e\u200f]*(?:(\d+)[ \t]*[-–][ \t]*\((\d+)\)|\((\d+)\)[ \t]*[-–][ \t]*(?=[^\d\s])"
                           r"|(\d+(?:[ \t]*[،,و–-][ \t]*\d+)*)[ \t]*[-–][ \t]*(?=[^\d\s]))", re.M)
# «رقم الحديث (2408)، 4/1873»: nomor tepat sebelum juz/halaman tercetak, jadi bukan nomor riwayat kitab lain di takhrij itu
TAKHRIJ = re.compile(r"رقم(?:\s+الحديث)?\s*\(\s*([\d٠-٩]+)[^()]*\)[،,\s]*([\d٠-٩]+)\s*/\s*([\d٠-٩]+)")
BUKAN_KEPALA = frozenset(map(shamela.padat, ("باب", "كتاب", "فصل", "مسألة")))  # judul bernomor, bukan hadits…
SANAD = re.compile("حدث|اخبر|انبا|ثنا$")  # …kecuali diikuti sanad: «3403 - باب حدثني» di Bukhari
NOMOR_AYAT = re.compile(r"آي(?:ة|ات)[:\s]*(\d+(?:\s*(?:[-–،,]|و|إلى)\s*\d+)*)")
MUNDUR_KEPALA = 3  # halaman ke belakang tempat kepala hadits yang dinukil masih dicari
ANGKA_LATIN = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 2)  # angka Arab dan Persia -> 0-9


@functools.cache
def kitab(sid):
    """Nomor rekaman kitab per juz ({part: [i]}, urut berkas; juz urut kemunculan pertamanya), dari shamela.indeks."""
    juz = {}
    for i, x in enumerate(shamela.indeks(sid)):
        juz.setdefault(x[0], []).append(i)
    return juz


def rekaman(sid, juz, p1=0, p2=float("inf")):
    """Rekaman juz itu (juz "-" = semua) yang menyentuh halaman p1..p2. Hanya rekaman itu yang diurai."""
    ix = shamela.indeks(sid)
    semua = [i for ii in kitab(sid).values() for i in ii] if juz == "-" else kitab(sid)[juz]
    return [shamela.rekaman_ke(sid, i) for i in semua if ix[i][2] >= p1 and (ix[i][1] or 0) <= p2]


@functools.cache
def seluruh(sid):
    """Semua rekaman kitab sid berurutan seperti rekaman(sid, "-"), dengan cache `padat` (untuk mencari di seluruh kitab)."""
    juz = {}
    for r in shamela._pages(sid):
        juz.setdefault(r.get("part"), []).append(r)
    return [r for rr in juz.values() for r in rr]


def urut_juz(j):
    """Juz berangka dulu menurut angkanya, lalu yang bernama (mis. المقدمة)."""
    return (not str(j).isdigit(), str(j).zfill(4))


NASKAH_TULISAN = re.compile("(?:الكتاب|البحث) (?:مخطوط|غير مطبوع)")  # nomornya nomor lembar naskah tulisan/ketikan
KUTIPAN_MIN = 6  # huruf (bentuk `padat`) paling sedikit tiap bagian kutipan yang dicek
POTONGAN_MIN = 7  # huruf paling sedikit potongan sendiri <<sid|juz|hal|potongan>> (potongan sah terpendek di bahts nyata: 7)
# pengganti {Q:s:a} di tengah kutipan («﴿s:a﴾»; ﴿﴾ yang diketik = ayat tanpa nomor): kutipannya dicek per bagian,
# dan celah di kitab di antara bagiannya harus memang ayat
AYAT_DI_KUTIPAN = re.compile(r"﴿(?:[0-9]+:[0-9]+(?:-[0-9]+)?)?﴾")  # bukan «﴿٢٨﴾» yang diketik penulis
DIPOTONG = re.compile(r"\.{2,}|…")  # potongan oleh penulis: yang dilompati tidak dicek mesin, jadi selalu perhatian
ELIPSIS = re.compile(f"{DIPOTONG.pattern}|{AYAT_DI_KUTIPAN.pattern}")  # pemisah bagian kutipan: tiap bagiannya dicek, berurutan
JARAK_AYAT = 300  # huruf `padat` celah {Q:} yang ayatnya tanpa ﴿﴾ di kitab (dikenali dari teksnya) sebelum jadi perhatian
SISA_AYAT = 20  # huruf `padat` kitab selain ayat dan rujukan [سورة: n] di celah {Q:} sebelum jadi perhatian
AYAT_KITAB = re.compile(r"﴿[^﴾]*﴾|\{[^{}]*\}")  # ayat bertanda di teks kitab Shamela
RUJUKAN_AYAT = re.compile(r"\[[^\]\n]*[ء-ي][^\]\n]*[0-9٠-٩][^\]\n]*\]")  # «[التكوير:٢٨]», «[آل عمران ١٥٢]»
LUAR = "luar"  # <<luar>>: sumbernya bukan kitab Shamela (jurnal, PDF penelitian, kamus); tidak bisa dicek mesin
NAFI = {"لا", "فلا", "ولا", "ما", "فما", "وما", "ليس", "وليس", "فليس", "ليست", "وليست", "فليست",
        "لم", "ولم", "فلم", "لن", "ولن", "فلن", "بلا", "وبلا", "فبلا"}  # kata tepat sebelum kutipan di kitab yang bisa membalik maknanya
BELUM_DIUNDUH = "kitab {} belum diunduh"  # pesan GAGAL per bukti; ringkasan di `utama` mengumpulkan nomornya dari pesan ini
BELUM_DIUNDUH_RE = re.compile(re.escape(BELUM_DIUNDUH).replace(r"\{\}", r"(\d+)"))


BUKTI_SID = re.compile(r"<<(\d+)\|")  # nomor kitab di bukti <<sid|juz|hal>>


def kitab_dirujuk(folder):
    """Nomor kitab Shamela yang dirujuk bukti naskah di folder bahts, urut kemunculan pertama (untuk `ambil <folder>`)."""
    return list(dict.fromkeys(BUKTI_SID.findall((Path(folder) / "naskah.txt").read_text(encoding="utf-8-sig"))))


def cek_pdf(folder, berkas, hal, kutipan, galat, perhatian, fn):
    """Bukti <<luar|berkas|hal>>: kutipan dicari di teks PDF folder/berkas. Hanya penunjuk halaman, tidak pernah
    lolos: tiap bukti PDF menambah satu galat (berkas/halaman salah) atau satu perhatian (cocokkan sendiri)."""
    tanda = f"<<{LUAR}|{berkas}|{hal}>>"
    folder = Path(folder).resolve()
    p = (folder / berkas).resolve()
    if not p.is_relative_to(folder):
        galat.append(f"{tanda}: PDF bukti harus di dalam folder bahts {folder.name} (tulis nama berkasnya saja)  || fn: {fn}")
        return
    if not p.is_file():
        galat.append(f"{tanda}: berkas «{berkas}» tidak ada di folder bahts {folder.name}; simpan PDF-nya di sana "
                     f"(mis. {shamela.perintah('dirasat-pdf <W…> ' + folder.name)})  || fn: {fn}")
        return
    bagian = [b for b in ELIPSIS.split(kutipan or "") if shamela.padat(b)]
    if pendek := next((b for b in bagian if len(shamela.padat(b)) < KUTIPAN_MIN), None):
        galat.append(f"bagian kutipan terlalu pendek untuk dicek (paling sedikit {KUTIPAN_MIN} huruf; jangan dipotong "
                     f"... di situ) :: {pendek.strip()[:30]}  || fn: {fn}")
        return
    a, z = map(int, (hal + "-" + hal).split("-")[:2])
    if not 1 <= a <= z:
        galat.append(f"{tanda}: hal = urutan halaman di berkas PDF, mulai 1; rentang ditulis kecil-besar (mis. 3-4)  || fn: {fn}")
        return
    try:
        isi = sumber_pdf.halaman(p)
    except Exception as e:  # pypdf: PDF rusak, bersandi, atau bentuk yang tidak dikenalnya
        perhatian.append(f"PDF «{berkas}» tidak bisa dibaca mesin ({type(e).__name__}): cocokkan sendiri lafaz dan "
                         f"halamannya  || fn: {fn}")
        return
    if z > len(isi):
        galat.append(f"{tanda}: PDF itu hanya {len(isi)} halaman (hal = urutan halaman di berkas, mulai 1)  || fn: {fn}")
        return
    if kutipan is None:  # nukilan makna: berkas dan halaman tetap dicek, isi diperiksa orang
        perhatian.append(f"nukilan tanpa tanda petik dari PDF ({berkas}): mesin tidak mengecek isinya; pastikan sendiri "
                         f"maknanya ada di halaman itu  || fn: {fn}")
        return
    ketemu = sumber_pdf.cari(isi, bagian)
    if any(a <= n <= z for n in ketemu):
        perhatian.append(f"kutipan «{kutipan[:30]}» ditemukan di halaman {hal} «{berkas}» (penunjuk, bukan bukti: teks PDF "
                         f"tidak dibaca persis; angka, urutan kata, dan huruf seperti العلم/العمل tidak dibedakan): buka "
                         f"halaman itu dan cocokkan sendiri lafaznya  || fn: {fn}")
    elif ketemu:
        galat.append(f"kutipan «{kutipan[:30]}» tidak ada di halaman berkas {hal} «{berkas}», tetapi ada di halaman "
                     f"{'، '.join(map(str, ketemu[:5]))}  || fn: {fn}")
    elif all(sumber_pdf.tanpa_teks(isi, n) for n in range(a, z + 1)):
        perhatian.append(f"halaman {hal} «{berkas}» berupa gambar (scan), teksnya tidak terbaca mesin: cocokkan sendiri "
                         f"lafaz kutipan «{kutipan[:30]}»  || fn: {fn}")
    else:
        perhatian.append(f"kutipan «{kutipan[:30]}» tidak ada di teks PDF «{berkas}»: lafaznya berbeda atau karangan, atau "
                         f"teks PDF-nya rusak; buka PDF-nya dan cocokkan sendiri lafaz dan halamannya  || fn: {fn}")


def salah_juz(sid, juz, hal):
    """'' kalau kitab sid sudah diunduh dan punya juz itu; selain itu pesan kesalahannya."""
    if not (shamela.ROOT / str(sid) / "pages.jsonl.gz").exists():
        return f"{BELUM_DIUNDUH.format(sid)} ({shamela.perintah(f'ambil {sid}')})"
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


RENTANG_MAKS = 50  # halaman paling banyak satu bukti (dan satu rentang tercetak)


def salah_halaman(hal):
    """'' kalau halaman bukti «n» atau «n-m» masuk akal; selain itu pesan kesalahannya."""
    p1, _, p2 = hal.partition("-")
    p1 = int(p1); p2 = int(p2) if p2 else p1
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
    semua = [i for ii in kitab(sid).values() for i in ii] if juz == "-" else kitab(sid)[juz]
    nomor = sorted({ix[i][1] for i in semua if ix[i][1]})
    sendiri = {n for k, n in enumerate(nomor) if k and n - nomor[k - 1] > RENTANG_MAKS
               and (k == len(nomor) - 1 or nomor[k + 1] - n > RENTANG_MAKS)}
    return {ix[i][1]: (ix[semua[k - 1]][1] if k else None, ix[semua[k + 1]][1] if k + 1 < len(semua) else None)
            for k, i in enumerate(semua) if ix[i][1] in sendiri}


def rekaman_dulu(sid, juz, p1, p2):
    """Rekaman tepat sebelum rekaman pertama yang menyentuh halaman p1..p2 (kata di akhir halaman sebelumnya); None kalau tidak ada."""
    ix = shamela.indeks(sid)
    semua = [i for ii in kitab(sid).values() for i in ii] if juz == "-" else kitab(sid)[juz]
    for k, i in enumerate(semua):
        if ix[i][2] >= p1 and (ix[i][1] or 0) <= p2:
            return shamela.rekaman_ke(sid, semua[k - 1]) if k else None
    return None


def _di(sid, juz, p1, p2, q, utuh, kata=()):
    """Cari q (sudah `padat`) di juz/halaman p1..p2, matan dan حاشية per halaman.
    Kembalikan (jenis, None): jenis "matan", "hasyiah", atau "hasyiah?" (حاشية tanpa penanda halaman di rekaman
    banyak halaman); atau (None, (awal, akhir, tanda)) kalau hanya ada di halaman lain; atau (None, None)."""
    lain, hasyiah = None, None
    for r in rekaman(sid, juz, p1, p2):
        for bagian, tanda in shamela.BAGIAN:
            h = shamela.tempat(r, q, bagian, utuh, kata, (p1, p2))  # q yang muncul dua kali: yang di p1..p2 didahulukan
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
            # Matan di halaman lain tidak menutup pencarian حاشية pada rekaman yang sama.
    if not hasyiah and len(rekaman(sid, juz, p1, p2)) > 1:  # kutipan yang menyambung dari satu rekaman ke berikutnya
        for bagian in ("body", "footnotes"):  # حاشية yang bersambung («… =» lalu «= …» di halaman berikutnya)
            for g in gabung(sid, juz, p1, p2):
                h = shamela.tempat(g, q, bagian, utuh, kata, (p1, p2))
                if h and p1 <= (h[0] or 0) and (h[1] or 0) <= p2:
                    return ("matan" if bagian == "body" else "hasyiah"), None
    return (hasyiah, None) if hasyiah else (None, lain)


def _akhir(r):
    """Halaman cetak terakhir rekaman r (page_num, atau penanda ⦗n⦘ terbesar di matannya)."""
    return max([r.get("page_num") or 0] + [int(n) for n in shamela.PENANDA.findall(r.get("body") or "")])


@functools.cache
def gabung(sid, juz, p1, p2):
    """Rekaman-rekaman yang menyentuh halaman p1..p2 sebagai rangkaian rekaman: awal tiap rekaman diberi penanda
    halaman ⦗n⦘, jadi kutipan yang menyambung lintas rekaman tetap dicek per kata dan halamannya tetap tercatat.
    Rekaman diurutkan menurut halamannya (urutan berkas Shamela bisa melompat: mukadimah diselipkan di tengah, dua
    rangkaian halaman berselang-seling), dan hanya rekaman yang halamannya bersambung (sama atau +1) yang dirangkai:
    teks dua halaman yang tidak bersambung tidak boleh jadi satu kutipan."""
    hasil = []
    for r in sorted(rekaman(sid, juz, p1, p2), key=lambda r: r.get("page_num") or 0):
        n = r.get("page_num")
        if hasil and n and hasil[-1]["_akhir"] <= n <= hasil[-1]["_akhir"] + 1:
            g = hasil[-1]
            for bagian, _ in shamela.BAGIAN:
                g[bagian] += f" ⦗{str(n).translate(AD)}⦘ " + (r.get(bagian) or "")
        else:
            g = {bagian: r.get(bagian) or "" for bagian, _ in shamela.BAGIAN} | {"page_num": n}
            hasil.append(g)
        g["_akhir"] = max(g.get("_akhir", 0), _akhir(r))
    return hasil


def _petunjuk(sid, juz, q):
    """Tempat q di seluruh kitab untuk pesan kesalahan: matan dulu (juz yang ditulis didahulukan), baru حاشية."""
    tempat, hasyiah = [], None
    for r in seluruh(sid):
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


def _cek_bagian(sid, juz, hal, p1, p2, teks, utuh, perhatian, rinci=True):
    """Cek satu teks (kutipan, satu bagian kutipan berelipsis, atau potongan) di juz/hal; '' kalau cocok.
    rinci=False: pesan kesalahannya tidak disusun (mencari di seluruh kitab), untuk pemanggil yang hanya butuh cocok/tidak."""
    q = shamela.padat(teks)
    jenis, lain = _di(sid, juz, p1, p2, q, utuh, shamela.kata_dalam(teks))
    if jenis == "hasyiah":
        perhatian.append(f"bukti ada di حاشية المحقق, bukan di matan kitab {sid} {juz}/{hal}: "
                         f"itu kalimat muhaqqiq, bukan pengarang :: {teks[:40]}")
    elif jenis == "hasyiah?":
        perhatian.append(f"bukti ada di حاشية المحقق {sid} {juz}/{hal}, tetapi halaman tiap catatan di rekaman ini tidak tercatat: "
                         f"pastikan halamannya dengan `halaman`; itu kalimat muhaqqiq, bukan pengarang :: {teks[:40]}")
    if jenis:
        return ""
    if not rinci:
        return "tidak cocok"
    if utuh and _di(sid, juz, p1, p2, q, False)[0]:
        if _di(sid, juz, p1, p2, q, True)[0]:  # ujungnya utuh, yang bergeser batas kata di dalamnya
            return (f"pembagian kata kutipan beda dengan kitab {sid} {juz}/{hal} (mis. «بل أشك» ≠ «بلا شك»): salin spasinya "
                    f"seperti di kitab, lihat `teks {sid} \"…\"` :: {teks[:40]}")
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
    raw = re.sub(r"\s+", " ", shamela.HARAKAT.sub("", shamela.TAGS.sub("", " ".join(g["body"] for g in gabung(sid, juz, p1, p2)))))
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
    awal_kata = [m.start() for m in re.finditer(r"\S+", raw)]
    a, z = 0, len(awal_kata)  # kata pertama yang mulai sesudah awalan; panjang `padat` awalan teks naik bersama letaknya
    while a < z:
        mid = (a + z) // 2
        if len(shamela.padat(raw[:awal_kata[mid]])) >= akhir:
            z = mid
        else:
            a = mid + 1
    di_kitab = raw[awal_kata[a]:].split()[0].strip(".,،؛:!؟\"«»()") if a < len(awal_kata) else "(akhir halaman)"
    return f"cocok {lo} dari {len(kata)} kata sampai «…{' '.join(kata[max(0, lo - 3):lo])}», lalu naskah «{kata[lo]}», kitab «{di_kitab}»"


def cek(sid, juz, hal, pot, perhatian, kutipan=False, rinci=True):
    """Kembalikan '' kalau pot ada di kitab sid juz/hal, atau pesan kesalahan.
    kutipan=True: pot = kutipan bertanda petik di naskah. Ia harus mulai dan berakhir di batas kata kitab, boleh dipotong
    dengan ... (tiap bagian dicek, harus berurutan); angka dan kata nafi sebelumnya diperiksa sebagai perhatian.
    Yang lolos tetapi harus dilihat orang (bukti di حاشية, nomor halaman bukan cetakan) ditambahkan ke `perhatian`."""
    e = salah_juz(sid, juz, hal)
    if e:
        return e
    if shamela.OTOMATIS.search(shamela.info(sid)["betaka_text"]):
        pesan = (f"kitab {sid}: nomor halamannya buatan Shamela (مرقم آليا), bukan nomor cetakan — "
                 "pakai edisi yang «موافق للمطبوع», atau cocokkan ke cetakannya")
        if not any(p.endswith(pesan) for p in perhatian):  # sekali per kitab, walau tiap baris diberi awalan
            perhatian.append(pesan)
    elif NASKAH_TULISAN.search(shamela.info(sid)["betaka_text"]):
        pesan = (f"kitab {sid}: belum dicetak (مخطوط/غير مطبوع), nomor halamannya nomor lembar naskah — sebut lembarnya "
                 "(مخطوط، ل n) atau pakai edisi cetak kalau ada")
        if not any(p.endswith(pesan) for p in perhatian):
            perhatian.append(pesan)
    e = salah_halaman(hal)
    if e:
        return e
    p1, _, p2 = hal.partition("-")
    p1 = int(p1); p2 = int(p2) if p2 else p1
    for n, (a, b) in halaman_janggal(sid, juz).items():
        pesan = (f"nomor halaman {juz}/{n} kitab {sid} jauh dari halaman lain juz itu (rekaman sebelum/sesudahnya di Shamela: "
                 f"{'، '.join(f'ص{x}' for x in (a, b) if x)}): mungkin salah ketik Shamela; cocokkan ke cetakan (`scan`) dan tulis nomor cetakannya")
        if p1 <= n <= p2 and not any(p.endswith(pesan) for p in perhatian):
            perhatian.append(pesan)
    if pot.startswith("#") and not kutipan:
        nomor = pot[1:].strip().translate(ANGKA_LATIN)
        if not re.fullmatch(r"\d+", nomor):  # «#» kosong cocok di halaman mana saja
            return f"nomor hadits kosong/bukan angka: <<…|{pot}>>"
        # Rekaman dapat melintasi halaman cetak. Kepala pada halaman sesudah p2 bukan bukti di sini;
        # kepala sebelumnya tetap sah untuk lanjutan hadits dalam rekaman yang menyentuh halaman bukti.
        if any(nomor_hadits("\n".join(teks for halaman, teks in shamela._potong(r)
                                    if halaman is not None and halaman <= p2), nomor)
               for r in rekaman(sid, juz, p1, p2)):
            return ""
        return (f"{nomor} bukan kepala hadits di {sid} {juz}/{hal}: angka di awal baris («{nomor} - حدثنا», «36 - ({nomor})») yang "
                "dihitung, bukan nomor ayat atau catatan; betulkan nomornya, atau pakai potongan lafaz dari halaman itu")
    bagian, celah, pisah = [], [], []  # celah[i] = pemisah (... atau ﴿s:a﴾) di antara bagian i dan i+1
    ujung = [[], []]  # pemisah sebelum bagian pertama dan sesudah bagian terakhir («"قال تعالى: {Q:…}"»)
    for k, x in enumerate(re.split(f"({ELIPSIS.pattern})", pot)):
        if k % 2:
            pisah.append(x)
        elif shamela.padat(x):
            if bagian:
                celah.append(pisah)
            else:
                ujung[0] = pisah
            bagian.append(x); pisah = []
    ujung[1] = pisah
    if not bagian:
        return f"{'kutipan' if kutipan else 'potongan'} tanpa huruf Arab: {pot[:40]}"
    minimal = KUTIPAN_MIN if kutipan else POTONGAN_MIN
    for i, b in enumerate(bagian):
        if len(shamela.padat(b)) < minimal:
            if kutipan:
                # bagian pendek yang menempel ayat («{Q:22:70} [الحج:٧٠]»): letaknya dipastikan pemeriksaan celah ayat
                dekat = celah[max(0, i - 1):i + 1]
                if dekat and not any(DIPOTONG.search("".join(c)) for c in dekat):
                    continue
                if DIPOTONG.search(pot):  # «…» milik kitab sendiri yang ikut disalin: kutipan utuhnya bersambung di kitab
                    utuh = DIPOTONG.sub(" ", pot)
                    if not cek(sid, juz, hal, utuh, [], True, False):
                        return cek(sid, juz, hal, utuh, perhatian, True, rinci)
                return f"bagian kutipan terlalu pendek untuk dicek (paling sedikit {minimal} huruf; jangan dipotong ... di situ) :: {b}"
            return f"potongan terlalu pendek (paling sedikit {minimal} huruf; yang pendek cocok di sembarang tempat): {pot}"
    for b in bagian:
        e = _cek_bagian(sid, juz, hal, p1, p2, b, kutipan, perhatian, rinci)
        if e:
            return e
    rr = rekaman(sid, juz, p1, p2)
    if len(bagian) > 1:
        jarak = [j for j in (berurutan(rr, sisi, bagian) for sisi, _ in shamela.BAGIAN) if j is not None]
        if not jarak:
            return f"bagian kutipan yang dipisah ... tidak berurutan seperti di kitab {sid} {juz}/{hal} :: {pot[:40]}"
    angka = kutipan and re.search(r"\d", AYAT_DI_KUTIPAN.sub(" ", pot).translate(ANGKA_LATIN))
    diperiksa = False  # angka (atau rujukan [سورة: n] yang angkanya dibuang) sudah dicocokkan di tempatnya
    if kutipan and (angka or re.search(r"[\[\]]", pot) or AYAT_DI_KUTIPAN.search(pot)):
        e, catat, diperiksa = susunan_kitab(rr, bagian, celah, ujung)
        if e:
            return f"{e} ({sid} {juz}/{hal}) :: {pot[:40]}"
        perhatian += [f"{p} ({sid} {juz}/{hal}) :: {pot[:40]}" for p in catat]
    # dipotong ...: sambungan yang rapat pun bisa mengubah makna atau pembicaranya; dipisah ayat: diperiksa susunan_kitab
    if len(bagian) > 1 and min(jarak) and DIPOTONG.search(pot):
        perhatian.append(f"kutipan dipotong ... atau dipisah ayat ({min(jarak)} huruf kitab dilompati) {sid} {juz}/{hal}: "
                         f"baca yang dilompati, pastikan makna dan pembicaranya tetap :: {pot[:40]}")
    if kutipan:
        perhatian += [f"{p} ({sid} {juz}/{hal}) :: {pot[:40]}"
                      for p in ragu_kutipan(rr, bagian[0], pot, angka and not diperiksa, lambda: rekaman_dulu(sid, juz, p1, p2))]
    return ""


def _susunan(pd, q, maks=50):
    """Tiap susunan letak [(awal, akhir)] bagian-bagian q (sudah `padat`) di teks pd: bagian berikutnya yang terdekat."""
    j = pd.find(q[0])
    while j >= 0 and maks:
        letak, k = [(j, j + len(q[0]))], j + len(q[0])
        for b in q[1:]:
            n = pd.find(b, k)
            if n < 0:
                return
            letak.append((n, n + len(b))); k = n + len(b)
        yield letak
        maks -= 1
        j = pd.find(q[0], j + 1)


def _mirip_ayat(spec, teks):
    """Teks kitab (tanpa tanda ﴿﴾) memuat sepotong ayat {Q:spec}: sama paling sedikit 10 huruf `padat` berturut-turut."""
    a, b = shamela.padat(ayat(spec)[0]), shamela.padat(teks)
    if not b or len(b) > 3000:
        return False
    return difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b)).size >= min(10, len(a))


def _ayat_sama(spec, antara, rujukan):
    """Ayat kitab di celah {Q:} bisa ayat {Q:spec}: nama surat di rujukan [سورة: n] sama, atau teks salah satu ayat
    bertanda ﴿﴾ (atau seluruh celah) memuat sepotong ayat itu. False kalau keduanya ada dan tidak ada yang sama, atau
    kalau ayat bertanda di kitab lebih mirip dengan potongan ayat lain. Teks = lolos dengan perhatian itu."""
    surat = {shamela.padat(SURAH[int(x.split(":")[0]) - 1]) for x in spec}
    nama = [shamela.padat(re.sub(r"سورة|الآية|الآيات|آية", " ", x)) for x in rujukan]
    if any(n and any(n in t or t in n for t in surat) for n in nama):
        return True
    sama = lambda a, b, n: b and len(b) <= 3000 and difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(
        0, len(a), 0, len(b)).size >= min(n, len(a), len(b))
    tanda = [m.group()[1:-1] for m in AYAT_KITAB.finditer(antara)]
    kalah = False
    for teks in tanda:
        b = shamela.padat(teks)
        for x in spec:
            a = shamela.padat(ayat(x)[0])
            if b in a:
                return True
            # ayat bertanda ﴿﴾ ditulis kitab dengan ejaan imla'i («الصراط»/«الصرط», «الصلاة»/«الصلوة»): dibandingkan
            # juga tanpa huruf alif, waw, ya, dan hamzah
            # kerangka 3-4 huruf («نهل» dari «إن هؤلاء») termuat di banyak ayat: paling sedikit 5 huruf, lalu ditandingkan
            kb = KERANGKA.sub("", b)
            cocok = len(kb) >= 5 and kb in KERANGKA.sub("", a) or sama(a, b, 10) or _kerangka_sama(a, b)
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
    b = shamela.padat(antara)
    return any(sama(shamela.padat(ayat(x)[0]), b, 10) for x in spec)


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


def _jarak(a, b, batas=None):
    """Jumlah huruf yang diganti, dibuang, atau ditambah dari a ke b (Levenshtein). Dengan batas: berhenti begitu
    pasti lebih dari batas, dan mengembalikan batas + 1."""
    baris = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        lalu, baris[0] = baris[0], i
        for j, y in enumerate(b, 1):
            lalu, baris[j] = baris[j], min(baris[j] + 1, baris[j - 1] + 1, lalu + (x != y))
        if batas is not None and min(baris) > batas:
            return batas + 1
    return baris[-1]


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
    kb = KERANGKA.sub("", b)
    if len(kb) < 5:  # kerangka 3-4 huruf termuat di banyak ayat: tidak bisa ditandingkan
        return "menang", None
    a = KERANGKA.sub("", shamela.padat(ayat(nomor)[0]))
    milik = None
    for i in range(max(1, len(a) - len(kb) + 1)):
        w = a[i:i + len(kb)]
        n = (_jarak(w, kb, milik[0] if milik else None), w)
        milik = min(milik, n) if milik else n
    beda, saingan = milik[0], None
    padat = dict(_quran_padat_nomor())
    jauh = functools.cache(lambda: _jarak_ayat(shamela.padat(ayat(nomor)[0]), b))  # huruf lengkap {Q:}
    for k, x in _quran_kerangka_nomor():
        for w in _calon(x, kb, beda) if k not in sendiri else ():
            if w == milik[1]:
                # kerangka sama («الله للكافرين» 4:141, «والله للكافرين» 58:4): ayat berulang, kecuali huruf lengkapnya
                # lebih dekat ke ayat lain. Ejaan imla'i bisa begitu juga, jadi cukup seri (perhatian)
                if saingan is None and _jarak_ayat(padat[k], b) < jauh():
                    saingan = k
                continue
            n = _jarak(w, kb, beda)
            if n < beda:
                # salah ketik huruf mati bisa mendekatkan kerangka ke ayat lain: kalah hanya kalau ayat lain itu juga
                # lebih dekat dalam huruf lengkap («الرسل حلا»: 1 huruf dari 46:35 dan dari 16:35); selain itu seri
                if _jarak_ayat(padat[k], b) < jauh():
                    return "kalah", k
                saingan = saingan or k
            elif n == beda and saingan is None and _jarak_ayat(padat[k], b) <= jauh():  # seri di keduanya
                saingan = k
    return ("seri", saingan) if saingan else ("menang", None)


def _jarak_ayat(a, b):
    """Jumlah huruf beda terkecil antara b dan potongan ayat a (`padat`) sepanjang b."""
    terbaik = None
    for i in range(max(1, len(a) - len(b) + 1)):
        n = _jarak(a[i:i + len(b)], b, terbaik)
        terbaik = n if terbaik is None else min(terbaik, n)
    return terbaik


@functools.cache
def _quran_kerangka_nomor():
    return [(k, KERANGKA.sub("", x)) for k, x in _quran_padat_nomor()]


@functools.cache
def _quran_padat_nomor():
    return [(k, shamela.padat(v)) for k, v in QURAN.items()]


def _di_quran(b):
    """Teks `padat` b termuat di salah satu ayat mushaf (juga tanpa alif, waw, ya, dan hamzah: ejaan imla'i)."""
    kb = KERANGKA.sub("", b)
    return any(b in x or kb in KERANGKA.sub("", x) for _, x in _quran_padat_nomor())


def _kerangka_sama(a, b):
    """Tanpa alif, waw, ya, dan hamzah, 8 huruf berturut-turut gampang sama di ayat lain («مرضى أو على سفر» di 2:184
    dan 4:43): yang sama harus paling sedikit 8 huruf dan 4/5 kerangka yang lebih pendek; potongan kitab yang
    kerangkanya 5-7 huruf harus termuat utuh."""
    ka, kb = KERANGKA.sub("", a), KERANGKA.sub("", b)
    if not ka or not kb:
        return False
    n = difflib.SequenceMatcher(None, ka, kb, autojunk=False).find_longest_match(0, len(ka), 0, len(kb)).size
    return n >= max(8, -(-4 * min(len(ka), len(kb)) // 5)) or 5 <= len(kb) < 8 and n == len(kb)


KERANGKA = re.compile(r"[اويىءأإآؤئ]")


def susunan_kitab(rr, bagian, celah, ujung=([], [])):
    """Yang tidak terbaca pencocokan huruf `padat`, diperiksa di teks asli kitab (matan, lalu حاشية) tempat bagian-bagian
    kutipan berada: celah {Q:} harus memang ayat (bertanda ﴿﴾; nomornya sama kalau kitab menulis [سورة: n]), dan angka
    tiap bagian harus sama dengan angka kitab di tempatnya. Kembalikan (galat, perhatian, letaknya ketemu)."""
    q = [shamela.padat(b) for b in bagian]
    terbaik = None
    for sisi, _ in shamela.BAGIAN:
        raw = shamela.TAGS.sub(lambda m: " " * len(m.group()), "\n".join(r.get(sisi) or "" for r in rr))
        pd, panjang = shamela.padat(raw), {}
        if q[0] not in pd:
            continue
        angka = angka_kitab(raw)

        def sesudah(k):  # letak di raw tepat sesudah huruf `padat` ke-k
            lo, hi = 0, len(raw)
            while lo < hi:
                mid = (lo + hi) // 2
                if mid not in panjang:
                    panjang[mid] = len(shamela.padat(raw[:mid]))
                lo, hi = (lo, mid) if panjang[mid] > k else (mid + 1, hi)
            return lo
        mulai = lambda k: sesudah(k) - 1 if k < len(pd) else len(raw)  # letak huruf ke-k
        akhir = lambda k: sesudah(k - 1) if k > 0 else 0  # sesudah huruf terakhir sebelum huruf ke-k
        for letak in _susunan(pd, q):
            hasil = _nilai_susunan(raw, angka, letak, bagian, celah, ujung, mulai, akhir)
            kunci = (bool(hasil[0]), len(hasil[1]))
            if terbaik is None or kunci < terbaik[0]:
                terbaik = kunci, hasil
            if kunci == (False, 0):
                return "", [], True
    return (*terbaik[1], True) if terbaik else ("", [], False)


def _nomor_lain(spec, rujukan):
    """Nomor ayat di rujukan kitab [سورة: n] (rentang «[ق:٢٣- ٢٩]» = 23 s.d. 29) dan nomor {Q:spec} tidak beririsan."""
    nomor, mau = set(), set()
    for x in rujukan:
        for a, b in re.findall(r"(\d+)(?:\s*[-–]\s*(\d+))?", x.translate(ANGKA_LATIN)):
            nomor |= set(range(int(a), int(b or a) + 1)) if int(b or a) - int(a) <= 300 else {int(a), int(b)}
    for s in spec:
        x, _, y = s.split(":")[1].partition("-")
        mau |= set(range(int(x), int(y or x) + 1))
    return bool(mau and nomor and not mau & nomor)


NOMOR_KITAB_LAIN = ("rujukan kitab menulis nomor lain ({1}), tetapi teks ayat di kitab memang termuat utuh di {{Q:{0}}}: "
                    "pastikan nomornya ke mushaf")


def _ayat_persis(spec, teks):
    """Teks ayat bertanda di kitab (paling sedikit 12 huruf `padat`) termuat utuh di ayat {Q:spec} (juga tanpa alif, waw,
    ya, dan hamzah: ejaan imla'i): nomor di rujukan kitab yang berbeda berarti rujukan kitabnya yang salah."""
    b = shamela.padat(teks)
    if len(b) < 12:
        return False
    a = [shamela.padat(ayat(x)[0]) for x in spec]
    return any(b in x or KERANGKA.sub("", b) in KERANGKA.sub("", x) for x in a)


def _nilai_susunan(raw, angka, letak, bagian, celah, ujung, mulai, akhir):
    """(galat, perhatian) satu susunan letak bagian kutipan di teks asli kitab raw (lihat susunan_kitab)."""
    catat, sisa_celah = [], {}
    for i, c in enumerate(celah):
        dipotong = DIPOTONG.search("".join(c))
        spec = [x[1:-1] for x in c if x.startswith("﴿") and len(x) > 2]
        if dipotong and not spec:
            continue
        a, z = akhir(letak[i][1]), mulai(letak[i + 1][0])
        antara = raw[a:z]
        rujukan = [m.group() for m in RUJUKAN_AYAT.finditer(raw, a, min(len(raw), z + 40)) if m.start() < z]
        if not AYAT_KITAB.search(antara) and not rujukan:
            if any(_mirip_ayat(s, antara) for s in spec):  # ayat tanpa tanda ﴿﴾ di kitab
                if len(shamela.padat(antara)) > JARAK_AYAT and not dipotong:
                    catat.append(f"kutipan dipisah ayat ({len(shamela.padat(antara))} huruf kitab dilompati): "
                                 "baca yang dilompati, pastikan makna dan pembicaranya tetap")
                continue
            dilompati = re.sub(r"\s+", " ", shamela.HARAKAT.sub("", antara)).strip()
            return (f"di kitab tidak ada ayat di tempat {{Q:}} (sesudah «…{' '.join(bagian[i].split()[-3:])}»), yang ada "
                    f"di kitab: «{dilompati[:40] or 'tidak ada apa-apa'}». {{Q:}} di dalam kutipan hanya untuk ayat yang memang "
                    "dikutip kitab di situ", catat)
        if _nomor_lain(spec, rujukan):
            if not any(_ayat_persis(spec, m.group()[1:-1]) for m in AYAT_KITAB.finditer(antara)):
                return f"ayat yang dikutip kitab di tempat {{Q:{spec[0]}}} adalah {'، '.join(rujukan)}: salin ayat yang benar", catat
            catat.append(NOMOR_KITAB_LAIN.format(spec[0], '، '.join(rujukan)))
        sama = spec and _ayat_sama(spec, antara, rujukan)
        if spec and not sama:
            return (f"ayat yang dikutip kitab di tempat {{Q:{spec[0]}}} adalah surat lain "
                    f"({'، '.join(rujukan) or AYAT_KITAB.search(antara).group()[:40]}): salin ayat yang benar", catat)
        if isinstance(sama, str):
            catat.append(sama)
        if dipotong:  # yang dilompati sudah jadi perhatian «dipotong ...»
            continue
        sisa_celah[i] = len(shamela.padat(RUJUKAN_AYAT.sub(" ", AYAT_KITAB.sub(" ", antara))))
        if sisa_celah[i] > SISA_AYAT:
            catat.append(f"selain ayat, {sisa_celah[i]} huruf kitab dilompati di tempat {{Q:}}: baca yang dilompati, "
                         "pastikan makna dan pembicaranya tetap")
    # {Q:} di awal/akhir kutipan: kalau kitab menulis ayat tepat di sebelahnya, ayat itu harus ayat yang sama
    for spec, sisi in ((ujung[0], 0), (ujung[1], 1)):
        spec = [x[1:-1] for x in spec if x.startswith("﴿") and len(x) > 2]
        if not spec:
            continue
        # jendela 400 huruf hanya untuk tanda pembuka/penutup ayat; ayatnya dibaca utuh walau panjang
        if sisi:
            z = akhir(letak[-1][1]); buka = re.compile(r"[﴿{]").search(raw, z, z + 400)
            ayat_ = buka and AYAT_KITAB.match(raw, buka.start())
            dekat = ayat_ and raw[z:ayat_.start()]
        else:
            a = mulai(letak[0][0]); tutup = max(raw.rfind("﴾", max(0, a - 400), a), raw.rfind("}", max(0, a - 400), a))
            buka = raw.rfind("﴿" if raw[tutup] == "﴾" else "{", 0, tutup) if tutup >= 0 else -1
            ayat_ = AYAT_KITAB.match(raw, buka) if buka >= 0 else None
            ayat_ = ayat_ if ayat_ and ayat_.end() == tutup + 1 else None
            dekat = ayat_ and RUJUKAN_AYAT.sub(" ", raw[ayat_.end():a])
        if not ayat_ or len(shamela.padat(dekat)) > SISA_AYAT:
            continue
        rujukan = [m.group() for m in RUJUKAN_AYAT.finditer(raw, ayat_.end(), min(len(raw), ayat_.end() + 40))
                   if not shamela.padat(raw[ayat_.end():m.start()])]
        if _nomor_lain(spec, rujukan):
            if not _ayat_persis(spec, ayat_.group()[1:-1]):
                return f"ayat yang dikutip kitab di tempat {{Q:{spec[0]}}} adalah {'، '.join(rujukan)}: salin ayat yang benar", catat
            catat.append(NOMOR_KITAB_LAIN.format(spec[0], '، '.join(rujukan)))
        sama = _ayat_sama(spec, ayat_.group(), rujukan)
        if not sama:
            return (f"ayat yang dikutip kitab di tempat {{Q:{spec[0]}}} adalah surat lain "
                    f"({'، '.join(rujukan) or ayat_.group()[:40]}): salin ayat yang benar", catat)
        if isinstance(sama, str):
            catat.append(sama)
    for i, ((j, k), b) in enumerate(zip(letak, bagian)):
        # bagian pendek di samping {Q:} (lihat cek): harus kata utuh di kitab, tepat menempel ayatnya
        if len(shamela.padat(b)) < KUTIPAN_MIN:
            a, z = mulai(j), akhir(k)
            putus = (re.search(rf"[ء-ي]{HARAKAT.pattern}*$", raw[:a])
                     and not re.search(rf"(?<![ء-ي])[وف]{HARAKAT.pattern}*$", raw[:a])  # «و» / «ف» sambung boleh
                     or re.match(rf"{HARAKAT.pattern}*[ء-ي]", raw[z:]))
            if putus or any(sisa_celah.get(x, 0) > SISA_AYAT for x in (i - 1, i)):
                return (f"bagian kutipan terlalu pendek untuk dicek (paling sedikit {KUTIPAN_MIN} huruf), dan di kitab ia "
                        f"tidak menempel ayatnya sebagai kata utuh :: {b.strip()}", catat)
        # angka/rujukan di ujung bagian ikut dicocokkan: teks kitab sampai huruf terdekat, tidak melewati baris baru
        # atau kurung yang menutup ujung itu
        a, z = mulai(j), akhir(k)
        kepala, ekor = re.match(r"[^ء-ي]*", b).group(), re.search(r"[^ء-ي]*$", b).group()
        lebih = 0  # angka kitab di depan kutipan yang tidak ikut disalin («١٩/ ٤٧ - وعن» dikutip «47 - وعن»)
        if re.search(r"[\d٠-٩۰-۹\[(]", kepala):
            luar = re.split(r"[\r\n]", raw[akhir(j):a])[-1]
            buka = max(luar.rfind(x) for x in "[(") if kepala.lstrip()[:1] in ("[", "(") else -1
            a -= len(luar) - max(buka, 0)
            if buka < 0:
                lebih = max(0, len(re.findall(r"\d+", angka[a:a + len(luar)])) - len(re.findall(r"\d+", kepala.translate(ANGKA_LATIN))))
        if re.search(r"[\d٠-٩۰-۹\])]", ekor):
            luar = re.split(r"[\r\n]", raw[z:mulai(k)])[0]
            # «…خالتها)**.» ditutup kurung walau sesudahnya ada titik/** : angka catatan kaki kitab «(١)» sesudah
            # kurung itu bukan bagian kutipan
            tutup = [luar.find(x) for x in "])" if x in luar] if re.sub(r"[\s.,،؛:*]+$", "", ekor)[-1:] in ("]", ")") else []
            z += min(tutup) + 1 if tutup else len(luar)
        naskah, di_kitab = re.findall(r"\d+", b.translate(ANGKA_LATIN)), re.findall(r"\d+", angka[a:z])[lebih:]
        if naskah != di_kitab:
            beda = (f"angka di kutipan ({' '.join(naskah) or 'tidak ada'}) beda dengan angka kitab di tempat itu "
                    f"({' '.join(di_kitab) or 'tidak ada'})")
            if len(naskah) == len(di_kitab):
                return f"{beda}: salin angkanya dari kitab", catat
            catat.append(f"{beda}: salin angkanya dari kitab")
    return "", catat


def berurutan(rr, sisi, bagian):
    """Kalau bagian-bagian kutipan muncul berurutan di sisi (matan/حاشية) rekaman rr: jarak terbesar di antaranya
    (huruf `padat`), dengan susunan yang paling rapat. None kalau tidak berurutan."""
    teks = "".join(shamela._ruas(r, sisi)[0] for r in rr)
    bagian = [shamela.padat(b) for b in bagian]
    # Semua kemunculan tetap dicoba; batas 50 milik pemeriksaan angka/ayat tidak berlaku di sini.
    terbaik = None
    for letak in _susunan(teks, bagian, maks=float("inf")):
        jarak = max((b[0] - a[1] for a, b in zip(letak, letak[1:])), default=0)
        terbaik = jarak if terbaik is None else min(terbaik, jarak)
    return terbaik


def angka_kitab(t):
    """Teks kitab dengan angka 0-9 yang memang bagian kalimat: penanda halaman ⦗n⦘, nomor catatan kaki yang menempel
    kata («الجدال١») atau bertanda «(¬n)», dan angka di dalam tag HTML dibuang; «(٨٥)» (nomor hadits) tetap."""
    kosong = lambda m: " " * len(m.group())  # panjang teks tetap: letak angkanya sama dengan di teks asli
    t = shamela.PENANDA.sub(kosong, shamela.TAGS.sub(kosong, t))
    # «و٢٦٧» (و kata sambung yang berdiri sendiri) bukan nomor catatan kaki
    t = re.sub(r"(?<=[ء-ي])(?<!(?<![ء-ي])و)[٠-٩۰-۹]+|\(¬\s*[٠-٩۰-۹0-9]+\s*\)|^\s*\([٠-٩۰-۹0-9]+\)", kosong, t, flags=re.M)
    return t.translate(ANGKA_LATIN)


def kepala_hadits(body):
    """(teks, kepala, batas). kepala = [(letak, nomor)] di awal baris: «3561 - حدثنا», «3980 - 3981 - حدثنا», «36 - (2408)»,
    «(102) - حدثنا». batas = kepala yang memisahkan hadits: di Muslim hanya nomor berkurung. «5736 - (1)» di Ahmad juga
    terbaca kepala walau (1) nomor catatan: dua angkanya masuk `kepala`, jadi nomor yang benar tetap ditemukan."""
    # bukan angka_kitab: ia mengosongkan «(n)» di awal baris, padahal itu salah satu bentuk kepala hadits
    baris = shamela.PENANDA.sub(" ", shamela.TAGS.sub(" ", body)).translate(ANGKA_LATIN).replace("\r", "\n")
    kepala, kurung = [], []
    for m in KEPALA_HADITS.finditer(baris):
        awal = list(map(shamela.padat, baris[m.end():m.end() + 60].split()[:2]))
        if awal and awal[0] in BUKAN_KEPALA and not (len(awal) > 1 and SANAD.match(awal[1])):
            continue
        if m[2] or m[3]:
            kurung.append((m.start(), int(m[2] or m[3])))
        kepala += [(m.start(), int(x)) for x in re.findall(r"\d+", m[0])]
    return baris, kepala, kurung or kepala


def nomor_hadits(body, nomor):
    """Nomor berdiri sebagai kepala hadits. Nomor ayat, catatan, dan rentang halaman tidak ikut; nomor hadits lain atau
    daftar bernomor di halaman itu tetap bisa tertukar."""
    return any(n == int(nomor) for _, n in kepala_hadits(body)[1])


def takhrij_janggal(sid, juz, p1, p2, nomor, lafaz):
    """Nomor takhrij tidak cocok dengan kepala hadits di halaman bukti, atau lafaz bukti di hadits lain; None kalau cocok.
    Hadits bisa mulai beberapa halaman sebelum lafaz yang dinukil. Halaman tanpa kepala hadits tidak bisa dinilai."""
    # urut halaman: rekaman Shamela kadang tidak berurutan (Ahmad 29: ص299 sebelum ص296)
    rr = sorted(rekaman(sid, juz, max(1, p1 - MUNDUR_KEPALA), p2), key=lambda r: r.get("page_num") or 0)
    baris, kepala, batas = kepala_hadits("\n".join(r.get("body") or "" for r in rr))
    if not kepala:
        return None
    # batas hadits = nomor lebih besar: angka kecil di awal baris sesudahnya biasanya daftar dalam syarah
    ruas = [baris[a:next((x for x, n in batas if x > a and n > nomor), len(baris))] for a, n in kepala if n == nomor]
    if not ruas:
        return f"nomor takhrij ({nomor}) bukan kepala hadits di sekitar {juz}/{p1}: cocokkan nomornya ke kitab"
    hasyiah = shamela.padat(" ".join(r.get("footnotes") or "" for r in rr))  # kalimat muhaqqiq (derajat) bukan bagian hadits
    if any(not any(shamela.padat(x) in s for s in map(shamela.padat, ruas)) and shamela.padat(x) not in hasyiah for x in lafaz):
        return f"lafaz bukti tidak ada di hadits ({nomor}) sekitar {juz}/{p1}: mungkin nomornya milik hadits lain"


def periksa_takhrij(isi, bukti, terbukti, kutipan, perhatian):
    """Nomor takhrij yang tercetak tepat di depan juz/halaman sebuah bukti dicocokkan ke kitabnya; lafaz = potongan bukti, atau kutipan."""
    for nomor, juz, hal in TAKHRIJ.findall(isi.translate(ANGKA_LATIN)) if re.search("أخرج|رواه", isi) else ():
        for f in map(lambda b: b.split("|"), bukti):
            p1, _, p2 = f[2].partition("-") if len(f) > 2 else ("", "", "")
            if len(f) < 3 or f[1] != juz or p1 != hal or (f[0], juz, int(p1), int(p2 or p1)) not in terbukti:
                continue
            # kutipan hanya diikutkan kalau memang dicek ke bukti ini; #nomor tidak membawa lafaz
            sumber = (kutipan or "") if len(f) == 3 else "" if f[3].startswith("#") else f[3]
            lafaz = [x for x in ELIPSIS.split(re.sub(r"\{Q:[^}]*\}", " ", sumber)) if len(shamela.padat(x)) >= POTONGAN_MIN]
            pesan = takhrij_janggal(int(f[0]), juz, int(p1), int(p2 or p1), int(nomor), lafaz)
            if pesan and f"{pesan}  || fn: {isi[:45]}" not in perhatian:
                perhatian.append(f"{pesan}  || fn: {isi[:45]}")


def ragu_kutipan(rr, awal, pot, periksa_angka=True, dulu=lambda: None):
    """Yang tidak diperiksa pencocokan huruf: angka di kutipan (kalau belum dicocokkan di tempatnya oleh susunan_kitab),
    dan kata nafi tepat sebelum kutipan di matan kitab, juga di akhir halaman sebelumnya (dulu() = rekaman sebelum rr)."""
    ragu = []
    angka = set(re.findall(r"\d+", AYAT_DI_KUTIPAN.sub(" ", pot).translate(ANGKA_LATIN)))
    if angka and periksa_angka:
        ada = set()
        for r in rr:
            ada |= set(re.findall(r"\d+", angka_kitab(r.get("body") or "") + " " + angka_kitab(r.get("footnotes") or "")))
        if angka - ada:
            ragu.append(f"angka {'، '.join(sorted(angka - ada))} di kutipan tidak terbaca di halaman itu: cocokkan sendiri")
    q = shamela.padat(awal)
    def letak(r):  # awal kutipan di rekaman r; kutipan yang menyambung ke rekaman berikutnya: ujung rekaman = awalnya
        c = shamela._cocok(r, q, "body", True)
        if c or k_utuh:
            return c
        teks = shamela._ruas(r, "body")[0]
        n = next((n for n in range(min(len(q), len(teks)) - 1, 9, -1) if teks.endswith(q[:n])), 0)
        return n and len(teks) - n in shamela._batas_kata(r, "body")[0] and (len(teks) - n, len(teks))
    k_utuh = any(shamela._cocok(r, q, "body", True) for r in rr)
    for k, r in enumerate(rr):
        c = letak(r)
        if c:
            teks, mulai = shamela._ruas(r, "body")[0], sorted(shamela._batas_kata(r, "body")[0])
            sebelum = [a for a in mulai if a <= c[0]]  # awal kata kutipan (huruf sambung و/ف ikut kata itu)
            kata = teks[sebelum[-2]:sebelum[-1]] if len(sebelum) > 1 else None
            lalu = None if kata else rr[k - 1] if k else dulu()
            if lalu:  # kutipan mulai di awal rekaman: kata terakhir rekaman sebelumnya
                awal_lalu = shamela._batas_kata(lalu, "body")[0]
                kata = shamela._ruas(lalu, "body")[0][max(awal_lalu):] if awal_lalu else None
            if kata in NAFI:
                ragu.append(f"di kitab tepat sebelum kutipan ada «{kata}»: pastikan maknanya tidak terbalik")
            break
    return ragu


def tercetak(isi, juz):
    """Rentang halaman yang tercetak di catatan kaki untuk juz ini: [(awal, akhir)]. Angka ٠-٩ dibaca seperti 0-9.
    «ص» harus berdiri sebagai kata («النص 5» bukan halaman), boleh disambung و/ف («وص6»). Rentang boleh «-» atau «–»;
    «ص5، 7», «ص5 و7», «1/5، 7» = halaman 5 dan 7 (angka sesudah koma atau و yang bukan tahun atau juz/halaman).
    Halaman bahts sendiri («ص3 من هذا البحث») bukan halaman kitab."""
    isi = re.sub(r"\d+(?:\s*(?:[-–]|[،,]\s*و?|\s+و)\s*\d+)*\s*(?=من\s+هذا\s+البحث)", " ", isi.translate(ANGKA_LATIN))
    rentang = r"\d+(?:\s*[-–]\s*\d+)?"
    tahun = r"(?:1[34]|19|20)\d\d(?!\d|\s*[-–])"  # «ص5، 1423»: tahun cetak tanpa هـ, bukan halaman kedua
    daftar = rf"(?:\s*(?:[،,]\s*و?|\s+و)\s*(?!{tahun}){rentang}(?![\d/]|\s*/|\s*(?:هـ|ه(?!\w)|م(?!\w))))*"
    if juz == "-":
        pola = rf"(?<![\wـ])[وف]?ص\s*({rentang}{daftar})"
    else:
        pola = rf"(?<![\d/]){re.escape(juz)}\s*/\s*({rentang}{daftar})"
    return [(int(a), int(b or a)) for m in re.findall(pola, isi) for a, b in re.findall(r"(\d+)(?:\s*[-–]\s*(\d+))?", m)]


# «j/n» juz mana saja; bukan tanggal («12/5/1420», «1420هـ/2000م») atau cetakan («ط2/1420»)
# nomor hadits «رقم (5/ 103)», «الحديث 5/103» (nomor bab/hadits seperti cetakan سبل السلام) bukan juz/halaman
NOMOR_HADITS = re.compile(r"(?:رقم|حديث)(?:\s*الحديث)?\s*:?\s*\(?\s*\d+\s*/\s*\d+\s*\)?")
JUZ_TERCETAK = re.compile(r"(?<![\w/])(\d{1,2})\s*/\s*\d+(?![\d/])(?!\s*(?:هـ|م(?!\w)))")


def _bagian_kitab(isi, bukti):
    """Catatan kaki berbukti beberapa kitab: [(teks, bukti kitab itu)] dipotong di judul tiap kitab, supaya halaman yang
    tercetak dicocokkan dengan bukti kitabnya sendiri. Judul yang tidak ketemu (disingkat lain) = tidak dipotong."""
    sids = list(dict.fromkeys(b[0] for b in bukti))
    if len(sids) < 2:
        return [(isi, bukti)]
    letak, terpakai = {}, {}
    data = {sid: shamela.info(int(sid)) for sid in sids}
    judul = {sid: data[sid]["title_ar"].split(" - ")[0].split() for sid in sids}
    # pengarang di dalam judul katalog bukan bagian judul: «المغني لابن قدامة» ditulis «المغني، ابن قدامة»
    judul = {sid: kata[:next((i for i, w in enumerate(kata) if i and PENGARANG_SESUDAH.match(w)), len(kata))]
             for sid, kata in judul.items()}
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


def _rentang(hal):
    """[36, 37, 38, 41] -> «36-38، 41»."""
    potong, awal = [], hal[0]
    for x, y in zip(hal, hal[1:] + [None]):
        if y != x + 1:
            potong.append(f"{awal}-{x}" if x != awal else str(x)); awal = y
    return "، ".join(potong)


def cocok_halaman(isi, bukti, perhatian=None):
    """Bandingkan juz/halaman yang tercetak dengan bukti [(sid, juz, p1, p2)]; kembalikan daftar galat.
    Tiap halaman tercetak harus di dalam rentang bukti kitabnya, dan tiap bukti harus tercetak.
    «سبق تخريجه» mencetak halaman bahts ({P:}), bukan halaman kitab: yang dicek hanya halaman kitab yang tercetak."""
    if not bukti:
        return []
    galat = []
    bagian = _bagian_kitab(isi, bukti)
    if len(bagian) == 1 and len({b[0] for b in bukti}) > 1 and perhatian is not None and "سبق تخريجه" not in isi:
        perhatian.append(f"catatan kaki merujuk {len({b[0] for b in bukti})} kitab, tetapi judul kitabnya tidak dikenali, jadi "
                         f"halaman tiap kitab tidak bisa dicocokkan dengan buktinya sendiri: tulis judul kitab seperti di "
                         f"katalog (`kartu`), atau pastikan sendiri halaman tiap kitab  || fn: {isi[:45]}")
    for teks, bb in bagian:
        kitabnya = f" (kitab {bb[0][0]})" if len(bagian) > 1 else ""
        juz_bukti = {b[1] for b in bb}
        # juz yang tidak punya bukti sama sekali («3/77» di kitab satu jilid, «ص900» di kitab berjilid)
        utuh = teks.translate(ANGKA_LATIN)  # «عند شرحه للحديث (1/ 222)»: bukti yang tercetak di sini tetap terbaca
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
                else:  # «1/36-37» dengan bukti 36 saja: lebarkan buktinya (<<…|1|36-37>>) atau cetak halaman buktinya saja
                    galat.append(f"halaman tercetak {juz}/{a}-{b}: bukti belum mencakup {_rentang(kurang)}{kitabnya}")
        for s, z, p1, p2 in dict.fromkeys(bb) if "سبق تخريجه" not in isi else ():
            # gabungan halaman yang tercetak: «1/102، 103» untuk bukti 102-103
            if not any(set(range(p1, p2 + 1)) <= {n for a, b in t if b - a <= RENTANG_MAKS for n in range(a, b + 1)}
                       for t in (tercetak(teks, z), tercetak(utuh, z))):
                galat.append(f"juz/halaman bukti kitab {s} ({z}/{p1}{'-' + str(p2) if p2 != p1 else ''}) tidak tercetak di catatan kaki")
    return [f"{'; '.join(dict.fromkeys(galat))} || fn: {isi[:60]}"] if galat else []  # satu catatan kaki = satu galat


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


TAK_TERLIHAT = "\u200b\u200c\u200d\u200e\u200f\u061c\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff"


def kutipan_akhir(teks):
    """Isi kutipan "..." atau «...» yang menutup teks (tanda baca sesudahnya boleh), termasuk kutipan di dalamnya:
    «قال: "…" ثم سكت» -> seluruh isi «…». None kalau teks tidak berakhir dengan kutipan."""
    # kurung lafaz matn «((…))» dan tanda arah tak terlihat (RLM, ZWNJ, …) sesudah tanda petik ikut dibuang
    teks = seragam(teks)
    # Tanda baca Latin/Unicode sesudah petik tidak memutus hubungan nukilan dengan catatan kakinya.
    # Berhenti pada petik: ia diperlukan parser, termasuk pembuka yang tidak berpasangan.
    for _ in range(2):  # juga «…». اهـ, dan «…» انتهى كلامه؛
        while teks and (teks[-1].isspace() or teks[-1] in TAK_TERLIHAT or
                        unicodedata.category(teks[-1]).startswith("P") and teks[-1] not in '\"«»‘’\''):
            teks = teks[:-1]
        teks = AKHIR_NUKILAN.sub("", teks)
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


QAUL = re.compile(r"(?:^|\s)[وف]?(?:قال|قالت|يقول|تقول)(?:\s+[^\s:]+){0,4}\s*:?\s*$")  # pengantar nukilan «قال الشيخ:»
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


def _takhrij_dulu(mk, dulu_h, perhatian):
    """«سبق تخريجه، ص{P:k}»: kutipan mk ada di halaman bukti catatan kaki pertama {H:…|k} (potongan lain hadits yang
    sama pun boleh), dicek seperti kutipan biasa (kata utuh, kata nafi yang dibuang). Tanpa bukti di sana: mk harus
    sama dengan (atau kata-kata utuh dari) kutipan {H:} itu."""
    for h in dulu_h:
        for s, z, a, b in h.get("bukti") or ():
            p = []
            if not cek(int(s), z, f"{a}-{b}", mk, p, kutipan=True):
                perhatian += p
                if h.get("kutipan") and _hadits_lain(int(s), z, a, b, h["kutipan"], mk):
                    perhatian.append(f"kutipan «سبق تخريجه» ada di halaman bukti takhrij pertamanya, tetapi di hadits bernomor "
                                     f"lain, bukan hadits «{h['kutipan'][:30]}»: pastikan itu hadits yang ditakhrij")
                return True
    kata = lambda t: " " + " ".join(shamela.padat(w) for w in t.split() if shamela.padat(w)) + " "
    return any(not h.get("bukti") and h.get("kutipan") and kata(mk).strip() and kata(mk) in kata(h["kutipan"]) for h in dulu_h)


NOMOR_DI_KITAB = re.compile(r"(?<![\d٠-٩/])[\d٠-٩]+(?:\s*/\s*[\d٠-٩]+)?\s*-\s*(?=[ء-ي(])")  # «٢٤٢ - وعنه»


def _hadits_lain(sid, juz, p1, p2, kutipan_h, mk):
    """Di halaman p1..p2, kutipan {H:} dan mk hanya ditemukan di hadits bernomor yang berbeda («٢٤٢ - …» vs «٢٤٤ - …»)."""
    raw = shamela.TAGS.sub(" ", "\n".join(r.get("body") or "" for r in rekaman(sid, juz, p1, p2)))
    blok = [shamela.padat(x) for x in NOMOR_DI_KITAB.split(raw)]
    qh, qm = shamela.padat(kutipan_h)[:20], shamela.padat(mk)[:20]
    ih, im = {i for i, x in enumerate(blok) if qh and qh in x}, {i for i, x in enumerate(blok) if qm and qm in x}
    return len(blok) > 1 and bool(ih) and bool(im) and not ih & im


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


TOKEN = re.compile(r"(\*\*|\(\(|\)\)|\{(?:Q|H2|H|P):[^}]*\}|\[\^|\])")


KUNCI = re.compile(r"[a-z]+")


def urai(teks, catatan, ayat_idx, hadits_idx, galat, perhatian, di_catatan=False, rumuz=None, warna=None, folder=None):
    """Pecah satu baris jadi 'runs'. Catatan kaki ([^...]) diurai rekursif. rumuz = {sid: huruf} dari @rumuz;
    warna = {sid: warna Word (BGR)} dari @warna; folder = folder bahts (tempat PDF bukti <<luar|berkas|hal>>)."""
    runs, tebal, merah, i = [], False, False, 0
    q_akhir = None  # ayat terakhir di baris ini (untuk mencocokkan catatan kaki «سورة …»)
    polos = ""  # teks polos berjalan (untuk mencari kutipan sebelum catatan kaki)
    seg = 0  # awal teks polos sesudah catatan kaki terakhir
    seg_run = 0  # awal runs sesudah catatan kaki terakhir
    seg_h = len(hadits_idx)  # {H:} pertama sesudah catatan kaki terakhir
    while i < len(teks):
        m = TOKEN.search(teks, i)
        if not m:
            runs.append({"t": teks[i:], "b": tebal, "m": merah}); polos += teks[i:]; break
        if m.start() > i:
            runs.append({"t": teks[i:m.start()], "b": tebal, "m": merah}); polos += teks[i:m.start()]
        tok = m.group(1)
        i = m.end()
        if tok == "**":
            tebal = not tebal
        elif tok in ("((", "))"):
            if merah == (tok == "(("):
                raise TandaRusak(f"tanda {tok} tidak berpasangan: lafaz matn ditulis ((…))")
            merah = tok == "(("
            runs.append({"t": tok[0], "b": tebal, "m": True}); polos += tok[0]  # kurung lafaz matn ikut tercetak merah dan dicek
        elif tok.startswith("{Q:"):
            t, s, a = ayat(tok[3:-1])
            q_akhir = (s, a)
            polos += f" ﴿{s}:{a}﴾ "  # AYAT_DI_KUTIPAN bernomor
            runs.append({"t": "﴿", "b": False}); runs.append({"t": t, "q": True}); runs.append({"t": "﴾", "b": False})
            if not di_catatan:
                kunci = f"q{len(ayat_idx)}"
                ayat_idx.append({"k": kunci, "t": t, "s": s, "a": a})
                runs.insert(len(runs) - 3, {"bm": kunci})
        elif tok.startswith("{H2:"):
            kunci = "h_" + tok[4:-1]
            induk = next((r for r in hadits_idx if r["k"] == kunci), None)
            if not induk:
                raise TandaRusak(f"{tok}: belum ada {{H:...|{tok[4:-1]}}} sebelumnya")
            n = 1 + len(induk.setdefault("lagi", []))
            induk["lagi"].append(f"{kunci}_{n}")
            runs.append({"bm": f"{kunci}_{n}"})
        elif tok.startswith("{H:"):
            if di_catatan:  # penanda فهرس di catatan kaki tidak bisa dibaca halamannya oleh Word
                raise TandaRusak(f"{tok}: tidak boleh di dalam catatan kaki: pindahkan ke matan, tepat sebelum «matan»")
            if tok.count("|") != 2:
                raise TandaRusak(f"{tok}: bentuknya {{H:طرف|راوٍ|kunci}}")
            taraf, rawi, kunci = tok[3:-1].split("|")
            if not KUNCI.fullmatch(kunci):
                raise TandaRusak(f"{tok}: kunci hanya boleh huruf a-z")
            if any(r["k"] == "h_" + kunci for r in hadits_idx):
                raise TandaRusak(f"{tok}: kunci «{kunci}» sudah dipakai (pakai {{H2:{kunci}}})")
            hadits_idx.append({"k": "h_" + kunci, "t": taraf, "r": rawi})
            runs.append({"bm": "h_" + kunci})
        elif tok.startswith("{P:"):
            if not di_catatan:
                raise TandaRusak(f"{tok}: hanya boleh di dalam catatan kaki")
            if not any(r["k"] == "h_" + tok[3:-1] for r in hadits_idx):
                raise TandaRusak(f"{tok}: belum ada {{H:...|{tok[3:-1]}}} sebelumnya")
            runs.append({"pg": "h_" + tok[3:-1]})
        elif tok == "[^":
            if di_catatan:
                raise TandaRusak("catatan kaki tidak boleh di dalam catatan kaki: tutup yang pertama dengan ] dulu")
            # cari penutup ]; isi bukti <<...>> dilewati (potongannya boleh memuat ])
            j = i
            while j < len(teks) and teks[j] != "]":
                if teks.startswith("[^", j):
                    raise TandaRusak("catatan kaki tidak boleh di dalam catatan kaki: tutup yang pertama dengan ] dulu")
                tutup = teks.find(">>", j + 2) if teks.startswith("<<", j) else -1
                j = tutup + 2 if tutup >= 0 else j + 1
            if j >= len(teks):
                raise TandaRusak("catatan kaki [^ tidak ditutup dengan ]")
            isi = teks[i:j]
            i = j + 1
            bukti = re.findall(r"<<([^>]*)>>", isi)
            isi = re.sub(r"\s*<<[^>]*>>", "", isi).strip()
            if "<<" in isi or ">>" in isi:
                raise TandaRusak("bukti <<...>> tidak tertutup rapi (tidak boleh ada > di dalam potongan)")
            # bukti saja + semua sumbernya di @rumuz: tidak dicetak, dan seluruh teks sejak catatan kaki sebelumnya = nukilan
            # utuh dari halaman bukti (kitab tanpa catatan kaki: paragraf syarah yang disalin dari kitabnya)
            sid_bukti = [b.split("|")[0] for b in bukti if b.split("|")[0] != LUAR]
            diam = not isi and rumuz is not None and bool(sid_bukti) and all(x in rumuz for x in sid_bukti)
            zz = [z for z in dict.fromkeys((rumuz or {}).get(x) for x in sid_bukti) if z and z != "-"]
            penggal = polos[seg:]
            if isi.startswith("سورة") and q_akhir:
                s, a = q_akhir
                nama = re.split(r"[،,:(]|\sآي", isi[4:])[0]  # «سورة الفاتحة، آية: 2.» -> «الفاتحة»
                angka = isi.translate(ANGKA_LATIN)
                ayat_sejak = {n for x, y in re.findall(rf"﴿{s}:(\d+)(?:-(\d+))?﴾", penggal) for n in range(int(x), int(y or x) + 1)}
                tertulis = NOMOR_AYAT.search(angka)  # hanya nomor sesudah «آية»: juz, halaman, dan tahun di catatan bukan nomor ayat
                if (shamela.padat(nama) != shamela.padat(SURAH[s - 1]) or not all(re.search(rf"(?<!\d){x}(?!\d)", angka) for x in a.split("-"))
                        or ayat_sejak and tertulis and set(map(int, re.findall(r"\d+", tertulis[1]))) - ayat_sejak):
                    galat.append(f"catatan kaki ayat tidak cocok dengan {{Q:{s}:{a}}} (سورة {SURAH[s - 1]}) || fn: {isi[:45]}")
            # kutipan terakhir tepat sebelum catatan kaki; kutipan lain sejak catatan kaki sebelumnya tidak punya catatan kaki sendiri
            # Catatan penjelasan boleh berada di tengah kutipan, jadi pembukanya dapat sebelum seg.
            # Dua catatan sumber dapat membuktikan nukilan yang sama. Catatan penjelasan tanpa bukti
            # tidak perlu mengulang buktinya, kecuali ada penutup petik baru sesudah catatan terakhir.
            mk = kutipan_akhir(polos) if bukti or SISA_PETIK.search(seragam(penggal)) else None
            mk_pdf = mk  # kutipan untuk bukti PDF: tetap dicek walau mk dikosongkan sesudah galat lain
            lain = kutipan_semua(polos[seg:])[:-1 if mk is not None else None]
            sisa = luar_petik(polos[seg:])  # teks sejak catatan kaki sebelumnya, kutipan-kutipannya dibuang
            if mk is None and bukti and not diam and SISA_PETIK.search(sisa):  # nukilan utuh: tanda petiknya tidak menentukan apa pun
                perhatian.append(f"tanda petik tanpa pasangan sebelum catatan kaki: kutipannya tidak dikenali dan tidak dicek; "
                                 f"pakai \"…\" atau «…»  || fn: {isi[:45]}")
            if lain and DIPOTONG.search(sisa):  # «"…" ... "…"»: dua kutipan disambung elipsis di luar petik
                perhatian.append(f"kutipan disambung ... di luar tanda petik: baca yang dilompati di kitab, pastikan makna dan "
                                 f"pembicaranya tetap  || fn: {isi[:45]}")
            seg = len(polos)
            ww = {(warna or {}).get(x) for x in sid_bukti}
            if diam and len(ww) == 1 and None not in ww:  # paragraf salinan satu kitab berwarna: lafaz matn ((…)) tetap merah
                for r in runs[seg_run:]:
                    if "t" in r and not r.get("m"):
                        r["w"] = next(iter(ww))
            luar = LUAR in bukti
            pdf = [b.split("|")[1:] for b in bukti if b.startswith(LUAR + "|")]  # <<luar|berkas|hal>>
            for f in pdf:
                if len(f) != 2 or not f[0].strip() or not re.fullmatch(r"\d+(-\d+)?", f[1]):
                    raise TandaRusak(f"<<{LUAR}|{'|'.join(f)}>>: bentuknya <<{LUAR}|berkas.pdf|hal>>, hal = urutan halaman di berkas")
            bukti = [b for b in bukti if b.split("|")[0] != LUAR]
            terbukti = []  # (sid, juz, p1, p2) tiap bukti, untuk dicocokkan dengan yang tercetak
            kutipan_4 = []  # hasil cek kutipan ke tiap bukti berpotongan sendiri: (pesan, perhatian)
            tiga = any(b.count("|") == 2 for b in bukti)
            # kutipan bertanda petik di dalam catatan kaki itu sendiri (selain judul kitab; tiga kata atau kurang = istilah)
            kc = [k for k in kutipan_semua(isi) if len(k.split()) >= 4 and not any(shamela.nomor_judul(k.strip()))
                  and not judul_kitab(k, sid_bukti)]
            for b in bukti:
                f = b.split("|")
                if len(f) not in (3, 4) or not re.fullmatch(r"\d+", f[0]) or not re.fullmatch(r"\d+(-\d+)?", f[2]):
                    raise TandaRusak(f"<<{b}>>: bentuknya <<sid|juz|hal>> atau <<sid|juz|hal|potongan>>")
                e = salah_juz(int(f[0]), f[1], f[2]) or salah_halaman(f[2])
                if e:  # juz/halamannya belum bisa dibandingkan dengan yang tercetak: satu galat saja
                    galat.append(e + f"  || fn: {isi[:45]}"); continue
                terbukti.append((f[0], f[1], *map(int, (f[2] + "-" + f[2]).split("-")[:2])))
                if len(f) == 3 or diam:  # bukti saja: seluruh paragraf dicek, potongannya tidak cukup
                    nukilan = penggal if diam else mk
                    if nukilan is None:
                        if kc:  # yang dicek kutipan di dalam catatan kaki (di bawah)
                            continue
                        galat.append(f"[tanpa kutipan] {isi[:50]}"); continue
                    e = cek(int(f[0]), f[1], f[2], nukilan, perhatian, kutipan=True)
                else:
                    e = cek(int(f[0]), f[1], f[2], f[3], perhatian)
                    if not e and mk is not None and not tiga:
                        p = []
                        kutipan_4.append((cek(int(f[0]), f[1], f[2], mk, p, kutipan=True), p))
                if e:
                    galat.append(e + f"  || fn: {isi[:45]}")
            periksa_takhrij(isi, bukti, terbukti, mk, perhatian)
            # kutipan bertanda petik tetap dicek walau buktinya membawa potongan sendiri: cukup ada di salah satu bukti itu
            if kutipan_4 and all(e for e, _ in kutipan_4):
                galat.append(f"kutipan sebelum catatan kaki tidak ada di halaman buktinya (potongan <<…|potongan>> hanya "
                             f"membuktikan potongannya; nukilan makna tanpa tanda petik, diawali انظر): {kutipan_4[0][0]}  || fn: {isi[:45]}")
            else:
                perhatian += next((p for e, p in kutipan_4 if not e), [])
            for k in kc if terbukti else ():
                kq = re.sub(r"\{Q:([^}]*)\}", lambda m: " ﴿%s:%s﴾ " % ayat(m.group(1))[1:], k)  # {Q:} dicek seperti di matan
                if all(cek(int(s), z, f"{a}-{b}", kq, [], kutipan=True, rinci=False) for s, z, a, b in terbukti):
                    # judul («"…"، مجلة …», «بعنوان "…"») atau sumber <<luar>>: cukup perhatian. GAGAL hanya untuk nukilan
                    # yang diantar «…:» («قال الشيخ: "…"»), bukan «انظر:»/«بعنوان:»
                    sebelum, _, ekor = seragam(isi).partition(k)
                    sebelum, sesudah = sebelum[:-1].rstrip(), ekor[1:].lstrip()[:1]
                    # «قال X: "…"، المصدر» / «قال X "…"» tetap nukilan walau disusul koma atau tanpa titik dua
                    pengantar = re.split(r'[.،؛"«»]', sebelum)[-1]
                    qaul = QAUL.search(pengantar) and not re.search(r"كتاب|بحث|رسال|عنوان|مقال|مجل", pengantar)
                    nukilan = not luar and (qaul or sebelum.endswith(":") and sesudah not in ("،", ",") and not re.search(
                        r"(?:انظر|ينظر|راجع|بعنوان|عنوانه|كتاب|بحث|سلسلة)\s*:$", sebelum))
                    (galat if nukilan else perhatian).append(
                        f"kutipan di dalam catatan kaki tidak ada di halaman buktinya: «{k[:40]}»; kalau itu judul, istilah, atau "
                        f"nukilan sumber di luar Shamela, buang tanda petiknya atau tambah <<{LUAR}>> dan cocokkan sendiri ke "
                        f"sumbernya  || fn: {isi[:45]}")
            # kutipan lain sejak catatan kaki sebelumnya: perhatian, kecuali yang terbaca di halaman bukti catatan kaki ini
            # atau yang memang judul yang disebut di catatan kaki itu; tiga kata atau kurang biasanya istilah
            for k in lain:
                if len(k.split()) < 4 or shamela.padat(k) in shamela.padat(isi):
                    continue
                if any(not cek(int(s), z, f"{a}-{b}", k, [], kutipan=True, rinci=False) for s, z, a, b in terbukti):
                    continue
                perhatian.append(f"kutipan tanpa catatan kaki sendiri (hanya kutipan tepat sebelum [^ yang dicek): «{k[:40]}» || fn: {isi[:45]}")
            # pengecualian: rujukan ayat «سورة …» sesudah {Q:}, dan «سبق تخريجه، ص{P:…}» (buktinya di catatan kaki pertama)
            # «سورة …» hanya untuk kutipan yang memuat ayat itu; «سبق تخريجه، ص{P:k}» hanya untuk kutipan yang sama
            # dengan kutipan {H:…|k} di catatan kaki pertamanya
            for h in hadits_idx[seg_h:]:
                h.setdefault("kutipan", mk); h.setdefault("bukti", list(terbukti))
            seg_h = len(hadits_idx)
            p_kunci = re.findall(r"\{P:([a-z]+)\}", isi)
            dulu_h = [h for h in hadits_idx if h["k"] in {"h_" + k for k in p_kunci}]
            # «سورة …» hanya membebaskan kutipan yang isinya ayat saja; prosa lain di dalamnya butuh bukti
            dikecualikan = ((isi.startswith("سورة") and q_akhir and "﴿" in (mk or "")
                             and not shamela.padat(AYAT_DI_KUTIPAN.sub(" ", mk)))
                            or (isi.startswith("سبق تخريجه") and p_kunci and mk is not None and _takhrij_dulu(mk, dulu_h, perhatian)))
            if not bukti and mk is not None and isi.startswith("سبق تخريجه") and p_kunci and not dikecualikan:
                galat.append(f"kutipan «{mk[:30]}» berbeda dari yang ditakhrij di {{H:…|{p_kunci[0]}}}: beri bukti <<sid|juz|hal>>"
                             f"  || fn: {isi[:45]}")
                mk = None  # sudah dilaporkan
            # tiap bukti PDF selalu dicek (juga sesudah سورة / سبق تخريجه): berkas dan halamannya tetap harus benar
            if pdf:
                for b, h in pdf:
                    cek_pdf(folder, b.strip(), h, mk_pdf, galat, perhatian, isi[:45])
            elif not bukti and mk is not None and not dikecualikan:
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
            if not diam:
                galat += cocok_halaman(isi, terbukti, perhatian)
            sub = urai(isi, None, ayat_idx, hadits_idx, galat, perhatian, di_catatan=True)
            runs += [{"z": z} for z in zz]
            catatan.append({"runs": sub, "bukti": len(bukti), "luar": luar, "pdf": len(pdf)})
            if not diam:
                runs.append({"fn": len(catatan) - 1})
            seg_run = len(runs)
        else:  # "]" nyasar
            runs.append({"t": "]", "b": tebal}); polos += "]"
    if tebal:
        raise TandaRusak("tanda ** tidak berpasangan")
    if merah:
        raise TandaRusak("tanda (( tidak ditutup dengan ))")
    if re.search(rf"<<(?:\d+\||{LUAR}(?:>>|\|))", polos):
        raise TandaRusak("bukti <<...>> hanya boleh di dalam catatan kaki [^...]; di luar itu ia ikut tercetak")
    if re.search(r"\{(?:Q|H2|H|P):", polos):
        raise TandaRusak("tanda {Q:/{H:/{H2:/{P: tidak ditutup dengan }")
    return [r for r in runs if r.get("t", "x") != ""]


def utama(folder, keluar=None):
    """Olah naskah di `folder`. Kembalikan (jumlah galat, baris laporan)."""
    folder = Path(folder)
    try:
        naskah = (folder / "naskah.txt").read_bytes()
        baris = [(n, x.rstrip("\n")) for n, x in enumerate(io.StringIO(naskah.decode("utf-8-sig"), newline=None), 1) if x.strip()]
    except UnicodeDecodeError:
        raise SystemExit(f"{folder.name}/naskah.txt bukan UTF-8: " + (
            "buka di Notepad, File > Save As, pilih Encoding «UTF-8», simpan" if os.name == "nt" else
            "simpan ulang sebagai UTF-8 di editormu (atau dari terminal, mis. untuk UTF-16: "
            "iconv -f UTF-16 -t UTF-8 naskah.txt > naskah8.txt, lalu ganti naskah.txt dengan naskah8.txt)")
            + ", lalu ulangi `cek`.") from None
    blok, catatan, ayat_idx, hadits_idx, galat, perhatian, pustaka = [], [], [], [], [], [], []
    meta = {"berkas": folder.name}
    di_baris = {}  # @kunci dan #R -> nomor barisnya, untuk galat yang baru ketahuan sesudah semua baris dibaca
    rumuz = {}  # @rumuz: sid -> huruf
    warna = {}  # @warna: sid -> warna Word (BGR)
    for n, b in baris:
        g0, p0 = len(galat), len(perhatian)
        if b.startswith("@"):
            k, _, v = b[1:].partition(":")
            if k.strip() not in META:
                mirip = difflib.get_close_matches(k.strip(), sorted(META), n=1)
                galat.append(f"baris {n}: @{k.strip()}: data tidak dikenal" +
                             (f"; maksudnya @{mirip[0]}?" if mirip else "; lihat `tanda` untuk daftar data naskah"))
            meta[k.strip()] = v.strip()
            di_baris["@" + k.strip()] = n
            if k.strip() == "rumuz":
                for pasang in re.split(r"[,،]", v):
                    sid, _, z = pasang.partition("=")
                    if not re.fullmatch(r"\d+", sid.strip()) or not z.strip():
                        galat.append(f"@rumuz: «{pasang.strip()}»: bentuknya sid=huruf (atau sid=- tanpa rumuz), "
                                     f"mis. «@rumuz: 12010=-، 900002=ف»"); continue
                    rumuz[sid.strip()] = z.strip()
            if k.strip() == "warna":
                for pasang in re.split(r"[,،]", v):
                    sid, _, w = pasang.partition("=")
                    if not re.fullmatch(r"\d+", sid.strip()) or w.strip() not in WARNA:
                        galat.append(f"@warna: «{pasang.strip()}»: bentuknya sid=warna (warna yang ada: {'، '.join(WARNA)}), "
                                     f"mis. «@warna: 900002=biru»"); continue
                    rr, gg, bb = WARNA[w.strip()]
                    warna[sid.strip()] = rr + gg * 256 + bb * 65536
        elif "#R" in di_baris and b.startswith("#"):
            galat.append(f"baris {n}: {b.split()[0]} sesudah #R di baris {di_baris['#R']} tidak dirakit: "
                         "pindahkan bagian isi sebelum #R; sesudah #R hanya satu rujukan per baris")
        elif b.strip() == "#H":  # pindah halaman: blok sesudahnya mulai halaman baru (dibaca rakit.ps1 dan perkiraan_halaman)
            blok.append({"k": "H", "runs": [], "n": n})
        elif b.startswith("#"):
            k, _, t = b[1:].partition(" ")
            if k not in ("K", "F", "B", "M", "S", "R", "T") or not t.strip():
                galat.append(f"baris {n}: judul harus «#K/#F/#B/#M/#S/#R/#T teks» :: {b[:40]}"); continue
            if k == "T":  # kotak matn: paragraf biasa (boleh bercatatan kaki), dicetak merah dalam bingkai
                try:
                    blok.append({"k": "T", "runs": urai(t, catatan, ayat_idx, hadits_idx, galat, perhatian, rumuz=rumuz, warna=warna, folder=folder)})
                except TandaRusak as e:
                    galat.append(f"baris {n}: tanda rusak — {e}")
                except (KeyError, IndexError, ValueError) as e:  # bukan salah tulis naskah: mesinnya yang keliru di baris ini
                    galat.append(galat_mesin(n, e))
            elif re.search(r"\[\^|<<|\{|\*\*", t):  # judul tercetak apa adanya (juga di فهرس الموضوعات): tanda ini ikut tercetak
                galat.append(f"baris {n}: judul tidak boleh memuat catatan kaki [^, bukti <<, tanda {{Q:/{{H: atau **: "
                             f"pindahkan ke paragraf sesudahnya :: {b[:40]}")
            else:
                if k == "R":
                    di_baris["#R"] = n
                blok.append({"k": k, "runs": [{"t": t, "b": True}], "judul": t, "n": n})
        elif "#R" in di_baris:
            pustaka.append(b.strip())
        else:
            try:
                blok.append({"k": "P", "runs": urai(b, catatan, ayat_idx, hadits_idx, galat, perhatian, rumuz=rumuz, warna=warna, folder=folder)})
            except TandaRusak as e:
                galat.append(f"baris {n}: tanda rusak — {e}")
            except (KeyError, IndexError, ValueError) as e:  # bukan salah tulis naskah: mesinnya yang keliru di baris ini
                galat.append(galat_mesin(n, e))
        # tiap galat dan perhatian menyebut barisnya: pemakai langsung tahu tempatnya, tes jebakan mencocokkan per baris
        galat[g0:] = [g if g.startswith("baris ") else f"baris {n}: {g}" for g in galat[g0:]]
        perhatian[p0:] = [p if p.startswith("baris ") else f"baris {n}: {p}" for p in perhatian[p0:]]

    def di(kunci):
        return f"baris {di_baris[kunci]}: " if kunci in di_baris else ""
    tanpa = [t for t in re.split(r"[,، ]+", meta.get("tanpa", "")) if t]
    bentuk = meta.setdefault("bentuk", next(iter(WAJIB)))
    if bentuk not in WAJIB:
        galat.append(di("@bentuk") + f"@bentuk: «{bentuk}» tidak dikenal (yang ada: {'، '.join(WAJIB)})")
        bentuk = next(iter(WAJIB))
    if "pustaka" in tanpa:  # sumber cukup di catatan kaki (rujukan pertama tiap kitab berdata lengkap)
        if "#R" in di_baris:
            galat.append(di("#R") + "@tanpa: pustaka, tetapi ada #R: hapus #R beserta daftarnya, atau hapus «pustaka» dari @tanpa")
    elif "#R" not in di_baris and bentuk != "kitab":
        galat.append("tidak ada #R (المصادر والمراجع) di akhir naskah")
    elif "#R" in di_baris and not pustaka:
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
    # rakit.ps1 hanya memakai salah satu: jangan ada yang diabaikan diam-diam (@sampul yang tidak dikenal sudah GAGAL di bawah)
    if meta.get("sampul", "").lower() in SAMPUL and meta.get("templat"):
        galat.append(di("@sampul") + "@sampul dan @templat tidak bisa dipakai bersama: @templat sudah membawa sampulnya sendiri; hapus salah satu")
    sampul = meta["sampul"] = meta.get("sampul", next(iter(SAMPUL))).lower()
    sampul_dikenal = sampul in SAMPUL
    if not sampul_dikenal:
        galat.append(di("@sampul") + f"@sampul: «{sampul}» tidak dikenal (yang ada: {'، '.join(SAMPUL)})")
        sampul = meta["sampul"] = next(iter(SAMPUL))
    if meta.get("tahun") and not re.fullmatch(r"[1١][34٣٤][0-9٠-٩]{2}", meta["tahun"]):
        galat.append(di("@tahun") + f"@tahun: «{meta['tahun']}» bukan tahun hijriah 1300-1499 (mis. ١٤٤٨)")
    # @templat: sampul diambil apa adanya dari Word mahasiswa; @sampul salah ketik: data wajib model mana pun belum pasti
    wajib = (("judul",) if meta.get("templat") or not sampul_dikenal else SAMPUL[sampul]) if bentuk == "bahts" else WAJIB[bentuk]
    galat += [di("@" + k) + f"data sampul belum diisi: @{k}" for k in wajib if not meta.get(k)]
    asing = [t for t in tanpa if t not in TANPA]
    if asing:
        galat.append(di("@tanpa") + f"@tanpa: «{'، '.join(asing)}» tidak dikenal (yang ada: {', '.join(TANPA)})")
    if meta.get("templat"):  # Word mahasiswa: sampul dan kepala halaman diambil dari situ oleh rakit.ps1
        tpl = (folder / meta["templat"]).resolve()
        if bentuk == "kitab":
            galat.append(di("@templat") + "@templat hanya untuk bahts, bukan @bentuk: kitab")
        elif tpl.suffix.lower() not in (".docx", ".doc"):
            galat.append(di("@templat") + f"@templat: «{meta['templat']}» bukan berkas Word (.docx atau .doc)")
        elif not tpl.is_relative_to(folder.resolve()):
            galat.append(di("@templat") + f"@templat: «{meta['templat']}» di luar folder {folder.name}: salin berkasnya ke sana, lalu tulis namanya saja")
        elif not tpl.is_file():
            galat.append(di("@templat") + f"@templat: «{meta['templat']}» tidak ada di folder {folder.name}")
        else:
            meta["templat"] = str(tpl)
    # Hasil lama boleh diganti; templat dan PDF yang dirujuk naskah adalah bahan pemakai.
    # Samakan kapitalisasi juga di Linux: hasilnya akan dirakit di Windows.
    tujuan = {(folder / nama).resolve().as_posix().casefold()
              for nama in (f"{meta['berkas']}.docx", f"{meta['berkas']}.pdf", "laporan.txt")}
    sumber = re.findall(r"<<luar\|([^|<>]+)\|", naskah.decode("utf-8-sig"))
    if meta.get("templat"):
        sumber.append(meta["templat"])
    for nama in dict.fromkeys(sumber):
        if (folder / nama.strip()).resolve().as_posix().casefold() in tujuan:
            galat.append(di("@berkas") + f"hasil rakit akan menimpa bahan sumber «{nama}»: ganti @berkas atau nama berkas sumber")
    baru = [t for t in re.split(r"[,، ]+", meta.get("halaman_baru", "")) if t]
    if any(t not in HALAMAN_BARU for t in baru):
        galat.append(di("@halaman_baru") + f"@halaman_baru: «{meta['halaman_baru']}» tidak dikenal (yang ada: {', '.join(HALAMAN_BARU)})")
    meta["halaman_baru"] = [t for t in baru if t in HALAMAN_BARU]  # dibaca rakit.ps1 dan perkiraan_halaman
    for a, b in zip(blok, blok[1:]):  # judul yang langsung disusul judul halaman baru tercetak sendirian di halamannya
        if a["k"] in ("K", "F", "B", "M") and b["k"] in ("K", "H", *("F",) * (bentuk != "kitab"), *meta["halaman_baru"]):
            perhatian.append(f"baris {a['n']}: judul «{a['judul'][:40]}» tercetak sendirian di halamannya, karena judul "
                             f"sesudahnya mulai halaman baru: tulis paragraf pengantar di bawahnya")
    if meta.get("thalibah", "ya") != "ya":
        galat.append(di("@thalibah") + f"@thalibah: «{meta['thalibah']}» tidak dikenal: tulis «ya», atau hapus barisnya")
    fmt = meta.get("format", "imam")
    if fmt not in FORMAT:
        galat.append(di("@format") + f"@format: «{fmt}» tidak ada di mesin/format.json (yang ada: {'، '.join(FORMAT)})")
    angka = meta.setdefault("angka", ANGKA[0])
    angka_ayat = meta.get("angka_ayat", angka)
    if angka not in ANGKA:
        galat.append(di("@angka") + f"@angka: «{angka}» tidak dikenal (yang ada: {'، '.join(ANGKA)})")
    elif angka_ayat not in ANGKA:
        galat.append(di("@angka_ayat") + f"@angka_ayat: «{angka_ayat}» tidak dikenal (yang ada: {'، '.join(ANGKA)})")
    else:  # yang dihitung Word (nomor halaman, catatan kaki, فهرس) diubah di rakit.ps1; ayat (q) tetap apa adanya
        ubah = hindi if angka == "hindi" else (lambda s: s.translate(ANGKA_LATIN))
        for k in ("judul", "jenis", "nama", "nim", "fasl", "musyrif", "jabatan", "tahun"):
            if k in meta:
                meta[k] = ubah(meta[k])
        for r in [r for b in blok + catatan for r in b["runs"]] + hadits_idx:
            if "t" in r and not r.get("q"):
                r["t"] = ubah(r["t"]).translate(HORMAT_CETAK)
        if angka_ayat != angka:  # rujukan ayat [^سورة …، آية: n.] saja; "al" = rakit.ps1 mencetak angkanya kiri-ke-kanan,
            for c in catatan:      # karena Word (angka konteks) mencetak 0-9 di tengah teks Arab sebagai ٠-٩
                if "".join(r.get("t", "") for r in c["runs"]).startswith("سورة"):
                    c["al"] = angka_ayat == "latin"
                    for r in c["runs"]:
                        if "t" in r:
                            r["t"] = hindi(r["t"]) if angka_ayat == "hindi" else r["t"].translate(ANGKA_LATIN)
        for b in blok:
            if "judul" in b:
                b["judul"] = ubah(b["judul"])
        for h in hadits_idx:
            h["r"] = ubah(h["r"])
        pustaka = [ubah(p) for p in pustaka]
    sidik_naskah = hashlib.sha256(naskah).hexdigest()
    with sementara(keluar or bahan(folder)) as part:
        part.write_text(json.dumps({"meta": meta, "format": FORMAT.get(fmt), "blok": blok, "catatan": catatan,
                                   "ayat": ayat_idx, "hadits": hadits_idx, "pustaka": pustaka,
                                   "quran": bool(quran), "naskah_sha256": sidik_naskah}, ensure_ascii=False), encoding="utf8")
    n_bukti = sum(c["bukti"] for c in catatan)
    n_luar = sum(c["luar"] for c in catatan)  # disebut di ringkasan: tanda yang bisa menyembunyikan kutipan karangan
    n_pdf = sum(c["pdf"] for c in catatan)
    fn_tanpa = [HARAKAT.sub("", "".join(r.get("t", "") for r in c["runs"]))[:60] for c in catatan
                if c["bukti"] == 0 and not c["pdf"] and not "".join(r.get("t", "") for r in c["runs"]).startswith(("سورة", "سبق تخريجه"))]
    lap = [f"blok={len(blok)} | kata matan={n_matan} | catatan kaki={len(catatan)} ({n_fn} kata) | ayat={len(ayat_idx)} | hadits={len(hadits_idx)} | pustaka={len(pustaka)}",
           f"bukti dicek ke Shamela lokal: {n_bukti}{f' | ditunjuk di PDF (bukan bukti): {n_pdf}' if n_pdf else ''}"
           f"{f' | <<{LUAR}>> (tidak dicek mesin): {n_luar}' if n_luar else ''} | GAGAL: {len(galat)}"]
    # kitab yang belum diunduh membuat tiap buktinya GAGAL: satu perintah untuk semuanya, sebelum daftar panjangnya
    belum = list(dict.fromkeys(m.group(1) for g in galat for m in BELUM_DIUNDUH_RE.finditer(g)))
    if belum:
        lap.append(f"  → {len(belum)} kitab belum diunduh; unduh semuanya sekaligus: "
                   + shamela.perintah("ambil " + folder.resolve().relative_to(HERE.parent.resolve()).as_posix()))
    lap += [f"  ✗ {g}" for g in galat]
    lap.append(f"perhatian (lolos, tetapi lihat sendiri): {len(perhatian)}")
    lap += [f"  ! {p}" for p in perhatian]
    lap.append(f"catatan kaki tanpa bukti (selain rujukan ayat): {len(fn_tanpa)}")
    lap += [f"  - {f}" for f in fn_tanpa]
    lap.append(f"NASKAH_SHA256={sidik_naskah}")
    return len(galat), lap
