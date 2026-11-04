# SPDX-License-Identifier: AGPL-3.0-or-later
"""Olah <bahts>/naskah.txt -> bahan JSON terpisah menurut jalur bahts/pekerjaan (untuk perakit Word)
+ verifikasi setiap rujukan ke kitab Shamela lokal. Dipanggil lewat bahts.py.

Tanda di naskah.txt (dicetak oleh: python mesin/bahts.py tanda):
  @kunci: nilai       data sampul, di awal naskah; kunci tidak dikenal = GAGAL (salah ketik tidak diabaikan). Wajib: judul dan nama; @sampul: mahad juga jenis ("-" = tidak tercetak), nim, fasl.
                      Opsional: musyrif, jabatan (kosong atau "-" = tidak tercetak), thalibah (ya = sampul mencetak «اسم الطالبة»),
                      sampul (qism = model قسم الشريعة, bawaan: logo, judul besar, sub-judul « - …» dalam kurung kalau ada,
                      العام الجامعي; jenis dan nim tercetak kalau diisi, fasl tidak; mahad = sampul معهد، كلية الشريعة),
                      tahun (العام الجامعي di sampul qism, mis. ١٤٤٨;
                      bawaan = tahun hijriah Umm al-Qura saat tahun ajaran mulai, 1 Agustus),
                      berkas (nama file hasil), format (profil di format.json; bawaan imam),
                      catatan_kaki (bersambung = nomor catatan kaki ١، ٢، ٣ … sampai akhir bahts; ulang = mulai ١ lagi tiap halaman)
                      dan spasi (1 atau 1.5: jarak baris matan dan judul) menimpa nilai itu di profil @format; bawaan = nilai profil.
                      Kombinasi permintaan dosen dibuat dengan keduanya, mis. «@format: tatbiqi» + «@catatan_kaki: bersambung»
                      angka (hindi = ٠١٢٣، bawaan; latin = 0123): angka yang tercetak di seluruh PDF,
                      termasuk nomor halaman, nomor catatan kaki, dan فهرس. Naskah boleh ditulis dengan angka mana saja
                      angka_ayat (bawaan = @angka): angka di catatan kaki rujukan ayat [^سورة …، آية: n.] saja,
                      mis. «@angka_ayat: latin» = nomor ayat di catatan kaki 0123, sisanya tetap ٠١٢٣
                      tanpa (yang tidak dicetak: فهرس ayat, hadits, maudhuat, dan pustaka = المصادر والمراجع
                      bila dosen minta sumber cukup di catatan kaki; mis. «@tanpa: ayat, hadits»).
                      فهرس الآيات dan فهرس الأحاديث yang kosong tidak dicetak dengan sendirinya
                      pustaka (akhir = urutan خطة yang menaruh فهرس المصادر والمراجع sesudah فهرس الأحاديث, dengan judul itu;
                      bawaan: المصادر والمراجع sebelum فهرس الآيات)
                      templat (berkas .docx di folder bahts): Word mahasiswa sendiri; halaman pertamanya jadi sampul
                      apa adanya (data sampul di naskah tidak dipakai), kepala halamannya (termasuk judul di dalamnya) dipakai
                      di tiap halaman isi; nomor halaman di kaki hanya kalau kepala itu tidak memuat nomor halaman
                      nomor (abjad = halaman sebelum #F pertama bernomor huruf أ ب ت, mulai #F pertama nomornya ١، ٢، ٣)
                      (mukadimah = sama, tetapi nomor ١ mulai #K المقدمة; الإهداء dst. sebelumnya tetap huruf)
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
  #V teks             bait syair di tengah halaman (boleh memuat catatan kaki): « ... » = jarak antara dua paruh bait, « ...~ » = dua paruh yang berbagi satu kata digabung,
                      « // » = bait berikutnya pada baris baru; kutipan bertanda petik boleh memuat keduanya
  #L teks             paragraf bahasa Latin, kiri ke kanan (mis. الملخص bahasa Inggris); tanpa catatan kaki
                      «#L **Abstract**» (satu baris penuh diapit **) = judul Latin tebal di tengah; paragraf #L
                      sesudahnya diberi jarak antar paragraf (6 pt) sampai blok bukan #L
  #T teks             kotak matn: paragraf dalam bingkai, seluruhnya merah (boleh memuat catatan kaki)
  #R teks             awal المصادر والمراجع; sesudahnya satu kitab per baris (diurutkan abjad otomatis, القرآن الكريم paling atas).
                      Wajib, kecuali «@tanpa: pustaka»; semua bagian isi harus sebelum #R (tidak boleh ada judul/#T/#H sesudahnya)
  **...**             tebal
  ((...))             lafaz matn yang disyarah: dicetak merah di dalam kurung, «((ليس بحجة))» -> (ليس بحجة)
  {Q:s:a} {Q:s:a-b} {Q:s:a:i-j}   ayat surat s ayat a (atau a-b; atau kata ke-i s.d. j): teks resmi rasm Utsmani + masuk فهرس الآيات.
                      Ayat sesudah «قال الله تعالى»/«وقال:» yang dirujuk [^سورة …، آية: n.] tanpa {Q:} = GAGAL;
                      nomor rujukan (juga «(الفاتحة: 5)», «الفاتحة/5», «الآية 5 من سورة الفاتحة») harus nomor {Q:}.
                      Di dalam kutipan: cetak persis sebatas ayat yang dikutip kitab di situ (lebih panjang/lain = GAGAL)
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
                      juz "-" = kitab tanpa juz di rekamannya; kitab berjilid walau halamannya bersambung tetap ditulis
                      juz-nya (bentuknya: baris «bukti:» di `kartu <id>`); hal boleh rentang 12-14. Kitab yang bagiannya
                      bernama (المقدمة، الكتاب): tulis bagiannya, <<sid|المقدمة|5>>, tercetak «المقدمة، ص5» atau «المقدمة/5»
  Beberapa bukti      kutipan sebelum catatan kaki dicek ke TIAP bukti <<sid|juz|hal>> tanpa potongan di catatan kaki itu,
                      bukan cukup salah satunya. Takhrij dari beberapa kitab: kitab yang lafaznya dikutip tanpa potongan,
                      riwayat berlafaz lain dan derajat dari kitab lain berpotongan lafaz halaman itu, mis.
                      [^أخرجه أبو داود، …، رقم الحديث (3502)، 3/283، وابن ماجه، …، رقم الحديث (2192)، 2/738، وهو حديث ضعيف،
                      ضعفه النووي في المجموع، 9/335. <<1726|3|283>> <<1198|2|738|نهى عن بيع العربان>>
                      <<2186|9|335|فالحاصل أن هذا الحديث ضعيف>>]
  [^<<sid|juz|hal>>]  catatan kaki berisi bukti saja, semua sid-nya ada di @rumuz: tidak dicetak; yang tercetak hanya
                      rumuznya ض (sid=- di @rumuz: tanpa rumuz, mis. kitab matn). Seluruh teks sejak catatan kaki
                      ber-<<…>> sebelumnya dicek sebagai nukilan utuh dari halaman itu (catatan tanpa <<…>> di
                      tengahnya, termasuk «سورة …», dan <<luar>> tanpa kutipan tidak memotongnya; tanda ((…)) dan ** tidak ikut dicek)
  <<luar>>            kutipan dari sumber yang tidak ada di Shamela (jurnal, PDF penelitian): lolos, tetapi masuk
                      perhatian; lafaz dan halamannya dicocokkan sendiri ke sumbernya. Judul kitab Shamela = GAGAL
  <<luar|berkas.pdf|hal>>   kutipan dari PDF penelitian yang disimpan di folder bahts (mis. hasil dirasat-pdf):
                      kutipan bertanda petik dicari di teks PDF itu. hal = urutan halaman di berkas PDF (mulai 1),
                      bukan nomor tercetak jurnal; boleh rentang 3-4. Mesin hanya MENUNJUK halaman, tidak pernah lolos:
                      ada di halaman itu = perhatian «ditemukan di halaman …» (cocokkan sendiri lafaz, angka, urutan);
                      ada di halaman lain, berkas tidak ada atau di luar folder bahts, halaman di luar PDF, atau bagian
                      kutipan < 6 huruf = GAGAL; tidak ada di teks PDF atau scan = perhatian. Nukilan makna (انظر) = perhatian
  Tanda petik yang dikenali: "…" «…» “…” ‘…’ '…' ❝…❞ 〝…〞 ‟…” ❮…❯ ❛…❜. Perhatian: kutipan yang dipotong ... di
                      tengahnya atau disambung ... dengan kutipan lain, dan tanda petik tanpa pasangan
                      (…) tepat sebelum catatan kaki berbukti yang diantar «قال …:»، «ﷺ:», atau tepat sesudah {H:} = kutipan,
                      dicek seperti "…". Kutipan pendek (≤3 kata) yang diantar «قال …:» juga dicek; tanpa pengantar = istilah
  Judul (#K/#F/#B/#M/#S/#R) tidak boleh memuat [^, <<, {Q:/{H: atau **
  Contoh: قال ابن القيم: "…"[^مدارج السالكين، ابن القيم، 2/15. <<8370|2|15>>].

Bahts dikumpulkan bertahap per فصل: tetap SATU naskah; tiap potongan dirakit dengan «rakit <folder> --fasl n» (#F ke-n;
                      rentang 1-2 = #F ke-1 dan ke-2). Yang sebelum #F pertama (المقدمة) ikut potongan pertama, yang
                      sesudah #F terakhir (الخاتمة) ikut potongan terakhir. Sampul hanya di potongan pertama; المصادر
                      dan الفهارس hanya di potongan terakhir (فهرس berisi isi potongan itu saja); nomor halaman tiap
                      potongan mulai ١. Hasil: «<@berkas> - المقدمة والفصل الأول.pdf» dst. dan laporan-fasl<n>.txt;
                      `cek` tetap memeriksa seluruh naskah. {P:kunci} yang menunjuk hadits di potongan lain = berhenti
                      sebelum Word: tulis takhrij lengkap di catatan kaki itu

riset.txt (di folder bahts, di samping naskah.txt): jejak langkah riset yang tidak meninggalkan bukti di kitab lokal.
  takhrij8 <kunci>    `shamela_search_phrase` kategori 8 (التخريج والأطراف) sudah dijalankan untuk {H:…|kunci}
  tafsir <s:a>        tafsir ayat sudah dibaca lewat connector `tafsir` (boleh rentang s:a-b)
  khilaf <istilah>    `shamela_research_scope` sudah dijalankan untuk satu masalah khilaf; satu baris per masalah
                      (masalah = bagian berjudul yang barisnya diawali «القول الأول», «الرأي الأول», atau «المذهب الأول»)
  belum <langkah> <objek> <alasan>   langkah yang tidak bisa dijalankan; sebut di laporan akhir
  Baris berawalan # = catatan. Tiap {H:}, ayat {Q:} (selain di bukti <<…>> dan di bawah #R), dan masalah khilaf yang
                      belum tercatat = perhatian, juga baris riset.txt yang rusak atau kunci takhrij8 yang tidak ada di naskah.
                      Tidak pernah GAGAL: isinya ditulis agen sendiri, jadi mesin hanya menunjuk yang belum dicatat
"""
import bisect, difflib, functools, hashlib, io, json, os, re, tempfile, unicodedata, zlib
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
# qism = mesin/sampul_qism.docx (قسم الشريعة: logo, judul besar, sub-judul dalam kurung kalau ada, العام الجامعي; jenis dan nim tercetak kalau diisi, fasl tidak)
SAMPUL = {"qism": ("judul", "nama"), "mahad": WAJIB["bahts"]}
HALAMAN_BARU = ("B", "M")  # judul yang bisa dibuat mulai halaman baru lewat @halaman_baru; K dan F selalu
TANPA = ("ayat", "hadits", "maudhuat", "pustaka")  # فهرس dan المصادر yang boleh dibuang lewat @tanpa; perakitnya di rakit.ps1
# @angka: yang pertama = bawaan. Pedoman Jāmiʿat al-Imām tidak menyebut jenis angka; contoh resminya (pedoman 1443هـ,
# مجلة العلوم الشرعية) memakai hindi di nomor halaman, catatan kaki, rujukan, tahun, ayat, dan فهرس
ANGKA = ("hindi", "latin")
# Kunci naskah yang menimpa satu nilai profil @format (kombinasi permintaan dosen tanpa profil baru):
# @kunci -> (kunci di format.json yang dibaca rakit.ps1, {nilai di naskah: nilai di profil})
TIMPA = {"catatan_kaki": ("catatan_ulang_tiap_halaman", {"bersambung": False, "ulang": True}),
         "spasi": ("spasi", {"1": 1, "1.5": 1.5})}
META = frozenset("judul jenis nama nim fasl musyrif jabatan thalibah sampul tahun berkas format angka angka_ayat tanpa pustaka templat halaman_baru nomor bentuk rumuz warna".split()) | TIMPA.keys()
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
    ada) huruf Latin: tautan, DOI, dan judul berbahasa Latin tetap 0-9; «مجلة X، 2020» tetap ٢٠٢٠. Satu lintasan linear."""
    keluar, pos, terakhir = [], 0, ""  # terakhir = huruf/tanda baca Arab terdekat sebelum posisi `pos`
    for m in re.finditer(r"[0-9]+", s):
        keluar.append(s[pos:m.start()])
        for k in KUAT.finditer(s, pos, m.start()):
            terakhir = k.group()
        k = next(KUAT.finditer(s, m.end()), None)  # sesudah angka, kalau sebelumnya tidak ada
        c = terakhir or (k.group() if k else "")
        keluar.append(m.group() if re.match(f"[{HURUF_LATIN}]", c) else m.group().translate(AD))
        pos = m.end()
    keluar.append(s[pos:])
    return "".join(keluar)
AD = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
KEPALA_HADITS = re.compile(r"^[ \t\u200e\u200f]*(?:(\d+)[ \t]*[-–][ \t]*\((\d+)\)|\((\d+)\)[ \t]*[-–][ \t]*(?=[^\d\s])"
                           r"|(\d+(?:[ \t]*[،,و–-][ \t]*\d+)*)[ \t]*[-–][ \t]*(?=[^\d\s]))", re.M)
# «رقم الحديث (2408)، 4/1873», «برقم 2205، 2/262», «رقم: 27، ص24» (kitab satu jilid): nomor tepat sebelum juz/halaman
# tercetak, jadi bukan nomor riwayat kitab lain di takhrij itu. Dibaca sesudah angka Arab diganti 0-9.
TAKHRIJ = re.compile(r"رقم(?:\s+الحديث)?\s*:?\s*(?:\(\s*(\d+)[^()]*\)|(\d+))[،,\s]*(?:(\d+)\s*/\s*(\d+)|ص\.?\s*(\d+))")
TAKHRIJ_AWAL = re.compile(r"\s*و?(?:أخرج|رواه)")  # catatan kaki takhrij: «أخرجه …», «رواه …»
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


def urut_juz(j):
    """Juz berangka dulu menurut angkanya, lalu yang bernama (mis. المقدمة)."""
    return (not str(j).isdigit(), str(j).zfill(4))


NASKAH_TULISAN = re.compile("(?:الكتاب|البحث) (?:مخطوط|غير مطبوع)")  # nomornya nomor lembar naskah tulisan/ketikan
KUTIPAN_MIN = 6  # huruf (bentuk `padat`) paling sedikit tiap bagian kutipan yang dicek
POTONGAN_MIN = 7  # huruf paling sedikit potongan sendiri <<sid|juz|hal|potongan>> (potongan sah terpendek di bahts nyata: 7)
# pengganti {Q:s:a} di tengah kutipan («﴿s:a﴾», «﴿s:a:i-j﴾»: penanda_ayat; ﴿﴾ yang diketik = ayat tanpa nomor): kutipannya
# dicek per bagian, dan celah di kitab di antara bagiannya harus memang ayat, sama dengan ayat yang tercetak
AYAT_DI_KUTIPAN = re.compile(r"﴿(?:[0-9]+:[0-9]+(?:-[0-9]+)?(?::[0-9]+-[0-9]+)?)?﴾")  # bukan «﴿٢٨﴾» yang diketik penulis
DIPOTONG = re.compile(r"\.{2,}|…")  # potongan oleh penulis: yang dilompati tidak dicek mesin, jadi selalu perhatian
GABUNG_PARUH = re.compile(r"\s*\.\.\.~\s*")  # «...~» di #V: dua paruh bait berbagi satu kata, disambung sebelum dicek dan dicetak
ELIPSIS = re.compile(f"{DIPOTONG.pattern}|{AYAT_DI_KUTIPAN.pattern}")  # pemisah bagian kutipan: tiap bagiannya dicek, berurutan
JARAK_AYAT = 300  # huruf `padat` celah {Q:} yang ayatnya tanpa ﴿﴾ di kitab (dikenali dari teksnya) sebelum jadi perhatian
BEDA_AYAT = 2  # huruf kerangka ayat tercetak yang boleh tidak ada di ayat bertanda kitab (_ayat_tercetak)
SISA_AYAT = 20  # huruf `padat` kitab selain ayat dan rujukan [سورة: n] di celah {Q:} sebelum jadi perhatian
# ﴿…﴾ (atau terbalik ﴾…﴿) berhuruf Arab yang diketik di naskah; {Q:} jadi «﴿2:255﴾» (angka), jadi ﴾ sesudah angka
# dan ﴿ sebelum angka = batas dua {Q:}, bukan kurung ayat terbalik
AYAT_KETIK = re.compile(r"﴿[^﴾]*[ء-ي][^﴾]*﴾|(?<![0-9٠-٩])﴾[^﴿﴾]*[ء-ي][^﴿﴾]*﴿(?![0-9٠-٩])")
# teks yang mengutip ayat, bukan sekadar menyebutnya: pengantar «قال الله تعالى:»/«قوله:», atau kurung berhuruf Arab
# minimal dua kata tepat sebelum catatan kaki («ومن ذلك (…)[^سورة …]»); kurung di tengah kalimat atau satu kata
# («(رحمهم الله)», «ومعنى (الرحمن) …») = keterangan, bukan ayat
# «قال الله تعالى», «يقول الله عز وجل في كتابه:», «قال تعالى -» (dengan atau tanpa «:»), kecuali disusul «في …» (penyebutan:
# «كما قال الله تعالى في سورة …»)
PENGANTAR_AYAT = re.compile(r"(?:قال|يقول|قوله)\s+(?:الله\s+|ربنا\s+)?(?:تعالى|سبحانه(?:\s+وتعالى)?|عز\s+وجل|جل\s+وعلا)"
                            r"(?:\s+في\s+كتابه(?:\s+العزيز)?)?(?!\s*في\s)"
                            r"|(?:قال|يقول|قوله|تعالى|سبحانه|وجل)\s*:|\((?![^()]*(?:رحم|رضي|عليه|صلى|ت\s*:|هـ))[^()]*[ء-ي]\S*\s+[^()]*\)[\s.،,:؛]*$")
AYAT_TIDAK_COCOK = "catatan kaki ayat tidak cocok dengan {{Q:{0}:{1}}} (سورة {2}) || fn: {3}"
# rujukan ayat yang tidak diawali «سورة»: «انظر: سورة الفاتحة، آية: 7», «الفاتحة، آية: 5», «[الفاتحة: 6]»
RUJUKAN_LAIN = re.compile(r"^(?:(?:انظر|ينظر)\s*:\s*)?[\[(]?\s*(?:سورة\s+)?([^،,:/()\[\]]+?)\s*(?:[،,:/]|\sآي)")
# «الآية ٥ من سورة الفاتحة»: nomor dulu, surat sesudahnya
AYAT_DARI_SURAH = re.compile(r"^(?:(?:انظر|ينظر)\s*:\s*)?(?:الآية|الآيات|آية)\s*:?\s*([0-9٠-٩][^م]*?)\s*من\s+سورة\s+([^.،,؛()\[\]]+)")
SURAH_PADAT = {shamela.padat(x) for x in SURAH}


def rujukan_ayat(isi):
    """(nama surat, teks nomornya) rujukan ayat di awal catatan kaki «سورة X، آية: n», «انظر: سورة X…», «X، آية: n»,
    «X: n», «(X: n)», «[X: n]», «X/n», «الآية n من سورة X»; None kalau awalnya bukan nama surat atau tanpa nomor."""
    m = RUJUKAN_LAIN.match(isi)
    nama, angka = (m[1], isi[m.end():]) if m else (None, "")
    if not m or shamela.padat(nama) not in SURAH_PADAT:
        m = AYAT_DARI_SURAH.match(isi)
        nama, angka = (m[2], m[1]) if m else (None, "")
    if nama is None or shamela.padat(nama) not in SURAH_PADAT or not re.search(r"[0-9٠-٩۰-۹]", angka):
        return None
    return nama, angka.translate(ANGKA_LATIN)
AYAT_KITAB = re.compile(r"﴿[^﴾]*﴾|\{[^{}]*\}")  # ayat bertanda di teks kitab Shamela
RUJUKAN_AYAT = re.compile(r"\[[^\]\n]*[ء-ي][^\]\n]*[0-9٠-٩][^\]\n]*\]")  # «[التكوير:٢٨]», «[آل عمران ١٥٢]»
LUAR = "luar"  # <<luar>>: sumbernya bukan kitab Shamela (jurnal, PDF penelitian, kamus); tidak bisa dicek mesin
NAFI = {"لا", "فلا", "ولا", "ما", "فما", "وما", "ليس", "وليس", "فليس", "ليست", "وليست", "فليست",
        "لم", "ولم", "فلم", "لن", "ولن", "فلن", "بلا", "وبلا", "فبلا"}  # kata tepat sebelum kutipan di kitab yang bisa membalik maknanya
HENTI = re.compile(r"[.،,؛;؟?!:]")  # tanda akhir kalimat di teks kitab: kata nafi di depannya milik kalimat sebelumnya
BELUM_DIUNDUH = "kitab {} belum diunduh"  # pesan GAGAL per bukti; ringkasan di `utama` mengumpulkan nomornya dari pesan ini
BELUM_DIUNDUH_RE = re.compile(re.escape(BELUM_DIUNDUH).replace(r"\{\}", r"(\d+)"))
TERTOLAK = []  # (sid, kutipan) yang GAGAL «teks TIDAK KETEMU di kitab»; dibaca `cek --jejak`, dikosongkan tiap `utama`
# ayat {Q:} dan catatan kaki berbukti, urut naskah, dengan nomor barisnya: dibaca `bukti`, dikosongkan tiap `utama`
#   {"n", "ayat": spec, "t": teks tercetak} atau {"n", "bukti": [sid|juz|hal…], "kutipan": teks yang dibuktikan, "catatan": isi}
PENUNJUK = []
SEKITAR = 300  # huruf teks kitab yang dicetak `bukti` sebelum dan sesudah letak kutipan


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
        rentang = shamela.rentang_juz(sid)
        p1 = int(hal.partition("-")[0]) if hal.partition("-")[0].isdigit() else 0
        # halaman bersambung antarjilid («متسلسلة الترقيم»): juz yang rentangnya memuat halaman itu
        contoh = next((j for j, (a, z) in rentang.items() if a <= p1 <= z), sorted(juz_ada, key=urut_juz)[0])
        return (f"kitab {sid} berjilid: tulis juz-nya, mis. <<{sid}|{contoh}|{hal}>>; yang ada: {shamela.daftar_juz(sid)} "
                f"(juz \"-\" hanya untuk kitab satu jilid; bentuk buktinya: `kartu {sid}`)")
    if juz == "-" and len(juz_ada) > 1 and None not in juz_ada:
        # bagiannya hanya bernama: «-» menggabung semuanya, jadi halaman yang ada di dua bagian (المقدمة tulisan muhaqqiq
        # dan الكتاب) tidak tentu yang mana. Halaman yang hanya ada di satu bagian tetap sah (`halaman` membacanya sama).
        p1, _, p2 = hal.partition("-")
        di = shamela.bagian_halaman(sid, int(p1), int(p2 or p1))
        if len(di) > 1:
            pilih = " atau ".join(f"<<{sid}|{j}|{hal}>>" for j in sorted(di, key=urut_juz))
            return f"halaman {hal} kitab {sid} ada di beberapa bagian ({'، '.join(sorted(di, key=urut_juz))}): sebut bagiannya ({pilih})"
    if juz != "-" and juz not in juz_ada:
        if juz_ada == {None}:
            return f"kitab {sid} satu jilid: tulis juz \"-\", mis. <<{sid}|-|{hal}>>"
        return f"kitab {sid} tidak punya juz {juz} (yang ada: {'، '.join(sorted(juz_ada - {None}, key=urut_juz))})"
    return ""


RENTANG_MAKS = 50  # halaman paling banyak satu bukti (dan satu rentang tercetak)
# `cek --jejak`, kutipan yang lafaznya sedikit berbeda dengan kitab; satuannya huruf `padat`
MIRIP_BENIH = 14  # panjang potongan kutipan yang harus ada persis di kitab
MIRIP_KUTIPAN = 30  # kutipan lebih pendek dari ini tidak dicari: yang pendek mirip di mana-mana
MIRIP_PANJANG = 300  # kutipan lebih panjang dari ini tidak dicari: waktu membandingkan = kuadrat panjangnya
MIRIP_MIN = 0.9  # bagian huruf yang harus sama (lihat `_mirip_kitab`)
MIRIP_CALON = 20  # tempat paling banyak tiap benih (benih umum, mis. basmalah, ada ribuan kali)
MIRIP_LONGGAR = 12  # tempat yang berjarak kurang dari ini dibandingkan sekali


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


# tempat kutipan dicari, berurutan: (bagian rekaman, `catatan` shamela.tempat). Matan = body selain حاشية yang tertulis di
# body sesudah garis pemisah ___ (`shamela.catatan_body`); حاشية = ruas itu dan footnotes
SISI = (("body", False), ("body", True), ("footnotes", None))


def _di(sid, juz, p1, p2, q, utuh, kata=()):
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


def _akhir(r):
    """Halaman cetak terakhir rekaman r (page_num, atau penanda ⦗n⦘ terbesar di matannya)."""
    return max([r.get("page_num") or 0] + [int(n) for n in shamela.PENANDA.findall(r.get("body") or "")])


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
    padat_, ix = shamela._cache(sid), shamela.indeks(sid)
    kena = set(padat_.kena(q))  # rekaman lain tidak memuat q: tidak menambah apa pun
    # urutan rekaman(sid, "-"): per juz (urut kemunculan pertamanya), lalu urut berkas
    for r in (padat_.isi({"part": ix[i][0]}, i) for ii in kitab(sid).values() for i in ii if i in kena):
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
    if hasyiah:
        return hasyiah
    t = _tempat_kitab(_rangkaian_kitab(sid), [shamela.norma.bait(q)])  # kutipan yang menyambung ke halaman berikutnya
    return shamela.letak(t[0], t[1]) + t[2] if t else None


def pesan_hasyiah(sid, juz, hal, teks, samar=False):
    if samar:
        return (f"bukti ada di حاشية المحقق {sid} {juz}/{hal}, tetapi halaman tiap catatan di rekaman ini tidak tercatat: "
                f"pastikan halamannya dengan `halaman`; itu kalimat muhaqqiq, bukan pengarang :: {teks[:40]}")
    return (f"bukti ada di حاشية المحقق, bukan di matan kitab {sid} {juz}/{hal}: "
            f"itu kalimat muhaqqiq, bukan pengarang :: {teks[:40]}")


def _cek_bagian(sid, juz, hal, p1, p2, teks, utuh, perhatian, rinci=True):
    """Cek satu teks (kutipan, satu bagian kutipan berelipsis, atau potongan) di juz/hal; '' kalau cocok.
    rinci=False: pesan kesalahannya tidak disusun (mencari di seluruh kitab), untuk pemanggil yang hanya butuh cocok/tidak."""
    q = shamela.padat(teks)
    jenis, lain = _di(sid, juz, p1, p2, q, utuh, shamela.kata_dalam(teks))
    if jenis in ("hasyiah", "hasyiah?"):
        perhatian.append(pesan_hasyiah(sid, juz, hal, teks, jenis == "hasyiah?"))
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


def cek(sid, juz, hal, pot, perhatian, kutipan=False, rinci=True, pengantar=""):
    """Kembalikan '' kalau pot ada di kitab sid juz/hal, atau pesan kesalahan.
    kutipan=True: pot = kutipan bertanda petik di naskah. Ia harus mulai dan berakhir di batas kata kitab, boleh dipotong
    dengan ... (tiap bagian dicek, harus berurutan); angka dan kata nafi sebelumnya diperiksa sebagai perhatian.
    Yang lolos tetapi harus dilihat orang (bukti di حاشية, nomor halaman bukan cetakan) ditambahkan ke `perhatian`.
    pengantar = teks naskah tepat sebelum kutipan («قال البهوتي:»), untuk memeriksa pembicaranya di kitab."""
    p0 = len(perhatian)
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
    angka_lepas = None  # bagian tanpa huruf Arab yang dipisah ... atau ayat dari lafaz («… ٩٩»): tak punya letak di kitab
    for k, x in enumerate(re.split(f"({ELIPSIS.pattern})", pot)):
        if k % 2:
            pisah.append(x)
        elif shamela.padat(x):
            if bagian:
                celah.append(pisah)
            else:
                ujung[0] = pisah
            bagian.append(x); pisah = []
        elif re.search(r"\d", x.translate(ANGKA_LATIN)):
            angka_lepas = x.strip()
    ujung[1] = pisah
    if not bagian:
        return f"{'kutipan' if kutipan else 'potongan'} tanpa huruf Arab: {pot[:40]}"
    if angka_lepas is not None:
        return (f"bagian kutipan yang cuma angka tidak bisa dicek: tulis angka itu bersama lafaz kitab yang menempel padanya "
                f"(«رقم (٨٥)», «[الحج:٧٠]»), tanpa ... atau ayat di antaranya (titik milik kitab pun dibuang) :: {angka_lepas}")
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
        e, catat, diperiksa = susunan_kitab(rr, bagian, celah, ujung, (p1, p2))
        if e:
            return f"{e} ({sid} {juz}/{hal}) :: {pot[:40]}"
        perhatian += [f"{p} ({sid} {juz}/{hal}) :: {pot[:40]}" for p in catat]
        if diperiksa in ("footnotes", "footnotes?") and not any("bukti ada di حاشية المحقق" in p for p in perhatian[p0:]):
            perhatian.append(pesan_hasyiah(sid, juz, hal, pot, diperiksa == "footnotes?"))
    # dipotong ...: sambungan yang rapat pun bisa mengubah makna atau pembicaranya; dipisah ayat: diperiksa susunan_kitab
    if len(bagian) > 1 and min(jarak) and DIPOTONG.search(pot):
        perhatian.append(f"kutipan dipotong ... atau dipisah ayat ({min(jarak)} huruf kitab dilompati) {sid} {juz}/{hal}: "
                         f"baca yang dilompati, pastikan makna dan pembicaranya tetap :: {pot[:40]}")
    if kutipan:
        # naskah menisbatkan kutipan ke pengarang kitab ini («قال البهوتي: "…"»): pembicara di kitab ikut diperiksa.
        # Nama pengarang harus tepat sesudah «قال» (pembicaranya): «نقل الشوكاني عن الزركشي أنه قال:» menisbatkan ke
        # الزركشي, «فقال فيما نقله القرطبي:» ke yang disebut sebelumnya
        nama = shamela.padat(shamela.info(sid).get("main_author_name_ar") or "")
        qaul = QAUL.search(pengantar)
        sesudah = (qaul.group().split(maxsplit=1) + [""])[1] if qaul else ""  # kata sesudah «قال»
        pengarang = nama if nama and shamela.padat(GELAR.sub("", sesudah)).startswith(nama) else None
        perhatian += [f"{p} ({sid} {juz}/{hal}) :: {pot[:40]}"
                      for p in ragu_kutipan(rr, bagian[0], pot, angka and not diperiksa, lambda: rekaman_dulu(sid, juz, p1, p2),
                                            pengarang)
                      + ragu_akhir(rr, bagian[-1])]
    if not any("حاشية المحقق" in p for p in perhatian[p0:]):  # yang di حاشية sudah disebut kalimat muhaqqiq
        judul = judul_muhaqqiq(sid, rr, shamela.padat(bagian[0]), kutipan)
        if judul:
            perhatian.append(f"bukti {sid} {juz}/{hal} ada di bagian «{judul}» (tulisan muhaqqiq/penerbit, bukan pengarang): "
                             f"jangan dinisbatkan ke pengarang kitab :: {pot[:40]}")
    return ""


# judul toc bagian tulisan muhaqqiq/penerbit di depan kitab (dibaca dari toc kitab lokal; judul yang sama untuk isi
# kitab sendiri, mis. «مقدمة» saja atau «ترجمة ابن عباس» di kitab tarajim, sengaja tidak dihitung)
JUDUL_MUHAQQIQ = re.compile(
    r"^(?:مقدمة|كلمة)\s+(?:ال)?(?:طبعة|تحقيق|محقق|مصحح|ناشر|مشرف|لجنة)"
    r"|^كلمة\s*:?\s*معالي|^تقديم(?:\s+بقلم|$)|^(?:ال)?إهداء$"
    r"|^ترجمة\s+(?:موجزة\s+|مختصرة\s+)?(?:لل|ال)(?:مؤلف|مصنف|شارح|ناظم|محقق)|^ترجمة\s+صاحب|حياة\s+(?:ال)?مؤلف"
    r"|^(?:ال)?تعريف\s+ب(?:ال)?(?:مؤلف|مصنف|شارح|كتاب)|^منهج\s+(?:ال)?(?:مؤلف|مصنف)\s+في"
    r"|^منهج\s+(?:ال)?تحقيق|^منهجي\s+في|^عملي\s+في|^وصف\s+(?:ال)?(?:نسخ|مخطوط)|^دراسة\s+(?:موجزة|الكتاب|الرسالة|المؤلف)")


def judul_muhaqqiq(sid, rr, q, utuh=True):
    """Judul (atau induknya) tulisan muhaqqiq/penerbit yang menaungi awal q (`padat`) di matan rr; '' kalau bukan."""
    for r in rr:
        c = shamela._cocok(r, q, "body", utuh)
        if c:
            return next((j for j in shamela.rantai_judul(sid, shamela.judul_naung(sid, r, c)) if JUDUL_MUHAQQIQ.search(j)), "")
    return ""


def _bagian_cari(teks):
    """Semua bagian berhuruf Arab (`padat`), urut seperti di naskah, termasuk bagian pendek di samping ayat.
    Tidak boleh membuang satu bagian lalu menunjuk kitab yang hanya memuat sisanya."""
    return [p for b in ELIPSIS.split(teks) if (p := shamela.padat(b))]


def _rangkaian(padat_, ix):
    """Rangkaian rekaman kitab dari teks `padat`-nya (`norma.Padat`): [(juz, tanda, teks, ruas)], teks dalam `bait`.
    Aturannya sama dengan `gabung`: urut halaman, dan hanya rekaman yang halamannya bersambung (sama atau +1) di juz
    yang sama yang dirangkai. ruas = (padat_, bagian, awal tiap rekaman di teks, nomor rekamannya), dibaca `_halaman_di`."""
    hasil = []
    juz = {}
    for i, x in enumerate(ix):
        juz.setdefault(x[0], []).append(i)
    for j, ii in juz.items():
        urut = sorted(ii, key=lambda i: ix[i][1] or 0)
        for s, (_, tanda) in enumerate(shamela.BAGIAN):
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
def _rangkaian_kitab(sid):
    """`_rangkaian` kitab sid; `jejak` melepasnya tiap kitab."""
    return _rangkaian(shamela._cache(sid), shamela.indeks(sid))


def _halaman_di(ruas, a, z):
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
    h1, h2 = (None if x == shamela.norma.TANPA_HAL else x for x in (h1s[k1], h2s[k2]))
    return (h2, h1) if (h1 or 0) > (h2 or 0) else (h1, h2)  # penanda halaman yang menurun di satu rekaman


def _tempat_kitab(rangkaian, bagian):
    """Juz, rentang halaman, dan tanda (matan/حاشية) tempat SEMUA bagian kutipan berurutan: boleh menyambung ke halaman
    berikutnya, paling lebar RENTANG_MAKS halaman. None kalau tidak ada. Hanya petunjuk: putusannya tetap milik `cek`.
    Yang ditunjuk rentang tersempit: kutipan ber-... tidak boleh ditunjuk di tempat bagian umumnya kebetulan berjauhan."""
    terbaik = None
    for juz, tanda, teks, ruas in rangkaian:
        for letak in _susunan(teks, bagian, len(teks)):
            h1, h2 = _halaman_di(ruas, letak[0][0], letak[-1][1])
            lebar = (h2 or 0) - (h1 or 0)
            if lebar <= RENTANG_MAKS and (terbaik is None or lebar < terbaik[0]):
                terbaik = lebar, ("-" if juz is None else juz), (h1, h2), tanda
            if lebar == 0:
                return terbaik[1:]
    return terbaik[1:] if terbaik else None


def _mirip_kitab(rangkaian, q):
    """Tempat q (sudah `padat`) yang lafaznya sedikit berbeda: (kemiripan, juz, halaman, tanda) terbaik, atau None.
    Benih = potongan pendek q yang harus ada persis; tiap tempat benihnya lalu dibandingkan huruf per huruf dengan q.
    Kemiripan = huruf yang sama, berurutan, dibagi panjang yang lebih besar antara q dan tempat itu: kata kitab yang
    tidak ada di kutipan (mis. kata nafi) ikut menurunkannya. Hanya petunjuk, sama seperti `_tempat_kitab`."""
    benih = [(k, q[k:k + MIRIP_BENIH]) for k in range(0, len(q) - MIRIP_BENIH + 1, MIRIP_BENIH)]
    terbaik = None
    for juz, tanda, teks, ruas in rangkaian:
        mulai = set()
        for k, b in benih:
            j, n = teks.find(b), 0
            while j >= 0 and n < MIRIP_CALON:
                mulai.add(max(0, j - k) // MIRIP_LONGGAR)
                j, n = teks.find(b, j + 1), n + 1
        for m in mulai:
            awal = max(0, m * MIRIP_LONGGAR - MIRIP_LONGGAR)
            blok = [x for x in difflib.SequenceMatcher(None, q, teks[awal:awal + len(q) + 3 * MIRIP_LONGGAR], autojunk=False)
                    .get_matching_blocks() if x.size >= 3]
            if not blok:
                continue
            a, z = awal + blok[0].b, awal + blok[-1].b + blok[-1].size
            nilai = sum(x.size for x in blok) / max(len(q), z - a)
            if nilai >= MIRIP_MIN and (terbaik is None or nilai > terbaik[0]):
                terbaik = nilai, ("-" if juz is None else juz), _halaman_di(ruas, a, z), tanda
    return terbaik


def jejak(tertolak, maks=3):
    """Cari kutipan yang ditolak «teks TIDAK KETEMU di kitab» pada kitab lain yang sudah diunduh.
    Kembalikan baris laporan: hanya petunjuk, bukan bukti; putusan tetap milik `cek` (tidak ada yang diloloskan).
    Tiap kitab dibaca sekali (cache `padat`), dicari dengan lafaz yang sama seperti `cari`, lalu cache-nya dilepas.
    Kitab yang dirujuk satu kutipan tidak dicari untuk kutipan itu; kutipan yang dipotong ... hanya ditunjuk
    kalau semua bagiannya ada berurutan dalam satu rentang yang bisa diloloskan `cek`.
    Kutipan yang persisnya tidak ada di kitab mana pun: tempat yang lafaznya paling mirip ikut disebut, termasuk di
    kitab yang dirujuk (kutipan yang satu huruf atau katanya meleset), kecuali kutipan ber-... dan yang sangat panjang."""
    cari = {}  # bagian `padat` (tuple) -> entri kutipan
    for sid, teks in tertolak:
        bagian = _bagian_cari(teks)
        if not bagian:
            continue
        entri = cari.setdefault(tuple(bagian), {"teks": teks, "bagian": [shamela.norma.bait(b) for b in bagian],
                                                "tertuju": set(), "dapat": [], "dibaca": 0, "mirip": []})
        entri["tertuju"].add(str(sid))
    if not cari:
        return []
    semua = shamela.punya()
    rusak = []
    for sid in semua:
        aktif = [e for e in cari.values() if len(e["dapat"]) < maks and str(sid) not in e["tertuju"]]
        # kutipan ber-... tidak: satu bagian yang mirip tidak berkata apa-apa tentang bagian lain (bisa karangan)
        # kutipan panjang juga tidak: membandingkan seluruhnya terlalu lama, menilai sebagiannya menyesatkan
        longgar = [e for e in cari.values() if not e["dapat"] and len(e["bagian"]) == 1
                   and MIRIP_KUTIPAN <= len(e["bagian"][0]) <= MIRIP_PANJANG]
        if not aktif and not longgar:
            continue
        try:
            rangkaian = _rangkaian_kitab(sid)
            for entri in aktif:
                t = _tempat_kitab(rangkaian, entri["bagian"])
                entri["dibaca"] += 1
                if t:
                    entri["dapat"].append((sid, *t))
            for entri in longgar:
                if not entri["dapat"] and (t := _mirip_kitab(rangkaian, entri["bagian"][0])):
                    entri["mirip"].append((t[0], sid, *t[1:]))
            del rangkaian
        except (OSError, EOFError, ValueError, TypeError, AttributeError, KeyError, IndexError, zlib.error) as e:
            # Pencarian hanya petunjuk: sumber lain yang rusak tidak boleh menutup hasil kitab yang sehat.
            rusak.append(f"kitab {sid} ({type(e).__name__})")
        finally:
            shamela.lepas()  # isi kitab tidak menumpuk, juga sesudah gagal dibaca
            _rangkaian_kitab.cache_clear()
        if all(len(e["dapat"]) >= maks for e in cari.values()):
            break
    baris = []
    for entri in cari.values():
        t, asli = entri["dapat"], entri["teks"]
        if not t:
            # kitab yang dirujuk dulu, lalu yang paling mirip, matan sebelum حاشية
            mirip = "، ".join(f"{sid} {shamela.letak(juz, h)}{tanda} (±{int(nilai * 100)}% huruf sama)" for nilai, sid, juz, h, tanda
                              in sorted(entri["mirip"], key=lambda x: (str(x[1]) not in entri["tertuju"], -x[0], bool(x[4])))[:maks])
            baris.append(f"  «{asli}» tidak ditemukan di {entri['dibaca']} kitab lain yang berhasil dibaca: "
                         "periksa ejaan dan sumber aslinya."
                         + (f" Paling mirip: kitab {mirip}. Lafaznya BERBEDA dan maknanya bisa terbalik: baca halamannya; "
                            "maknanya sama: salin lafaz kitabnya; berbeda: buang kutipannya, jangan disesuaikan." if mirip else ""))
            continue
        rinci = "، ".join(f"{sid} {shamela.letak(juz, h)}{tanda}" for sid, juz, h, tanda in t[:maks])
        baris.append(f"  «{asli}» ketemu di kitab {rinci} (maksimal {maks} kitab per teks)")
    if rusak:
        baris.append("  jejak belum lengkap: " + ", ".join(rusak) + "; hasil hanya dari kitab yang berhasil dibaca.")
    return baris


def _susunan(pd, q, maks=50, cocok=None):
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


def _ayat_tercetak(spec, kitab, celah=""):
    """Ayat yang tercetak untuk {Q:spec} (kata ke-i s.d. j kalau ada) dibandingkan dengan ayat bertanda ﴿﴾ yang dikutip
    kitab di tempat itu (isi tandanya, berurutan): «lebih» kalau yang tercetak tidak termuat di ayat kitab (lebih panjang,
    atau lafaz lain), «kurang» kalau termuat tetapi kitab mengutip lebih panjang, "" kalau sama. Ejaan utsmani dan imla'i
    tidak dihitung beda (kerangka: tanpa alif, waw, ya, dan hamzah). Salah ketik, salah baca OCR kitab, dan qiraat boleh:
    huruf yang diganti, paling banyak seperlima kerangka yang tercetak; huruf tercetak yang tidak ada di kitab (kata yang
    ditambah, ayat lain) paling banyak BEDA_AYAT. Tanda ﴿﴾ kitab yang
    rusak (jumlah ﴿ dan ﴾ di celah tidak sama: «﴿فإذا قرأته فاتبع قرءانه﴾ (١٨) ثم إن علينا بيانه﴾»): yang termuat di
    seluruh celah kitab (tanpa rujukan [سورة: n]) dianggap sama. Tanda yang utuh tidak: kata kitab sesudahnya («الآية»)
    bukan lanjutan ayat."""
    p = KERANGKA.sub("", shamela.padat(" ".join(ayat(x)[0] for x in spec)))
    k = KERANGKA.sub("", shamela.padat(kitab))
    beda = _dalam(p, k) if k else None
    if beda is None or beda > max(BEDA_AYAT, len(p) // 5):
        rusak = celah.count("﴿") != celah.count("﴾") or celah.count("{") != celah.count("}")
        luas = rusak and KERANGKA.sub("", shamela.padat(RUJUKAN_AYAT.sub(" ", celah)))
        beda = _dalam(p, luas) if luas else None
        return "" if beda is not None and beda <= max(BEDA_AYAT, len(p) // 5) else "lebih"
    return "kurang" if len(k) - len(p) > BEDA_AYAT + beda else ""


def _pesan_tercetak(hasil, spec, kitab):
    """(galat, perhatian) untuk hasil _ayat_tercetak."""
    q = "".join(f"{{Q:{x}}}" for x in spec)
    dikutip = re.sub(r"\s+", " ", shamela.HARAKAT.sub("", kitab)).strip()
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


def _jarak(a, b, batas=None):
    """Jumlah huruf yang diganti, dibuang, atau ditambah dari a ke b (Levenshtein). Dengan batas: berhenti begitu
    pasti lebih dari batas, dan mengembalikan batas + 1.
    Per bit (Myers/Hyyrö): satu kolom tabel jarak = dua bilangan bulat selebar a, satu langkah per huruf b."""
    if a == b:
        return 0
    if batas is not None and (batas <= 0 or abs(len(a) - len(b)) > batas):  # beda panjang = paling sedikit sejarak itu
        return batas + 1
    if not a or not b:
        n = len(a) + len(b)
        return batas + 1 if batas is not None and n > batas else n
    sama = {}  # huruf -> bit letaknya di a
    for i, x in enumerate(a):
        sama[x] = sama.get(x, 0) | 1 << i
    penuh, atas = (1 << len(a)) - 1, 1 << len(a) - 1
    naik, turun, n = penuh, 0, len(a)  # beda jarak tegak antarbaris: +1 / -1; n = jarak a dengan awalan b sejauh ini
    for y in b:
        eq = sama.get(y, 0)
        xv = eq | turun
        xh = (((eq & naik) + naik) ^ naik) | eq
        ph = turun | ~(xh | naik)
        mh = naik & xh
        if ph & atas:
            n += 1
        elif mh & atas:
            n -= 1
        ph = ph << 1 | 1
        mh <<= 1
        naik = (mh | ~(xv | ph)) & penuh
        turun = ph & xv & penuh
    return batas + 1 if batas is not None and n > batas else n


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


def susunan_kitab(rr, bagian, celah, ujung=([], []), dalam=None):
    """Yang tidak terbaca pencocokan huruf `padat`, diperiksa di teks asli kitab (matan, lalu حاشية) tempat bagian-bagian
    kutipan berada: celah {Q:} harus memang ayat (bertanda ﴿﴾; nomornya sama kalau kitab menulis [سورة: n]), dan angka
    tiap bagian harus sama dengan angka kitab di tempatnya. Calon susunan hanya dari halaman bukti (`dalam`),
    dengan batas kata yang sama seperti pemeriksaan huruf. Kembalikan (galat, perhatian, bagian kitab yang cocok)."""
    q = [shamela.padat(b) for b in bagian]
    kata = [shamela.kata_dalam(b) for b in bagian]
    terbaik = None
    for sisi, _ in shamela.BAGIAN:
        raw = shamela.TAGS.sub(lambda m: " " * len(m.group()), "\n".join(r.get(sisi) or "" for r in rr))
        # Raw utuh diperlukan untuk ayat tepat sebelum/sesudah halaman bukti. Yang dibatasi hanya posisi calon.
        sah, tak_pasti, catatan, offset = [], [], [], 0  # catatan = حاشية yang tertulis di body (`shamela.catatan_body`)
        for r in rr:
            t = r.get(sisi) or ""
            if sisi == "body":
                catatan += [(offset + a, offset + z) for a, z in shamela.catatan_body(t)]
            batas = [(0, r.get("page_num"))] + [(m.start(), int(m[1])) for m in shamela.PENANDA.finditer(t)]
            samar = sisi == "footnotes" and len(batas) == 1
            for i, (a, h) in enumerate(batas):
                z = batas[i + 1][0] if i + 1 < len(batas) else len(t) + 1  # termasuk pemisah antarrekaman
                a, z = offset + a, min(offset + z, len(raw))
                if dalam is None or samar or h is not None and dalam[0] <= h <= dalam[1]:
                    if sah and sah[-1][1] == a:
                        sah[-1] = sah[-1][0], z
                    else:
                        sah.append((a, z))
                    if samar and r.get("page_num") != shamela._potong(r)[-1][0]:
                        tak_pasti.append((a, z))
            offset += len(t) + 1
        pd, panjang = shamela.padat(raw), {}
        if q[0] not in pd:
            continue
        rek = {"body": raw}
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
        def di_halaman(a, z):
            n = bisect.bisect_right(sah, (a, float("inf"))) - 1
            return n >= 0 and sah[n][0] <= a and z <= sah[n][1]

        def cocok(i, j, k):
            return (len(q[i]) < KUTIPAN_MIN or shamela._utuh(rek, "body", j, k, kata[i])) and di_halaman(mulai(j), akhir(k))

        for letak in _susunan(pd, q, maks=float("inf"), cocok=cocok):
            hasil = _nilai_susunan(raw, angka, letak, bagian, celah, ujung, mulai, akhir, di_halaman)
            kunci = (bool(hasil[0]), len(hasil[1]))
            jenis = ("footnotes?" if any(a <= mulai(j) < z for a, z in tak_pasti for j, _ in letak) else
                     "footnotes" if any(a < akhir(k) and mulai(j) < z for a, z in catatan for j, k in letak) else sisi)
            if terbaik is None or kunci < terbaik[0]:
                terbaik = kunci, hasil, jenis
            if kunci == (False, 0):
                return "", [], jenis
    return (*terbaik[1], terbaik[2]) if terbaik else (
        "susunan kutipan berangka atau berayat tidak ditemukan di halaman bukti dengan kata utuh", [], False)


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


def _nilai_susunan(raw, angka, letak, bagian, celah, ujung, mulai, akhir, di_halaman=None):
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
        bertanda = " ".join(m.group()[1:-1] for m in AYAT_KITAB.finditer(antara))
        if spec and bertanda:  # ayat kitab tanpa tanda ﴿﴾ tidak bisa dipastikan batasnya
            e, p = _pesan_tercetak(_ayat_tercetak(spec, bertanda, antara), spec, bertanda)
            if e:
                return e, catat
            if p and not dipotong:  # yang dilompati sudah jadi perhatian «dipotong ...»
                catat.append(p)
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
        e, p = _pesan_tercetak(_ayat_tercetak(spec, ayat_.group()[1:-1]), spec, ayat_.group()[1:-1])
        if e:
            return e, catat
        if p:
            catat.append(p)
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
        naskah = re.findall(r"\d+", b.translate(ANGKA_LATIN))
        nomor = list(re.finditer(r"\d+", angka[a:z]))[lebih:]
        if naskah and di_halaman is not None and any(not di_halaman(a + m.start(), a + m.end()) for m in nomor):
            return "angka di kutipan berada di luar halaman bukti: perluas rentang bukti atau salin angka dari halaman yang dirujuk", catat
        di_kitab = [m.group() for m in nomor]
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


def _bersih(body):
    """Teks rekaman tempat kepala hadits dicari: tag dan penanda halaman jadi satu spasi, angka 0-9.
    Bukan angka_kitab: ia mengosongkan «(n)» di awal baris, padahal itu salah satu bentuk kepala hadits."""
    return shamela.PENANDA.sub(" ", shamela.TAGS.sub(" ", body)).translate(ANGKA_LATIN).replace("\r", "\n")


def kepala_hadits(body):
    """(teks, kepala, batas). kepala = [(letak, nomor)] di awal baris: «3561 - حدثنا», «3980 - 3981 - حدثنا», «36 - (2408)»,
    «(102) - حدثنا». batas = kepala yang memisahkan hadits: di Muslim hanya nomor berkurung. «5736 - (1)» di Ahmad juga
    terbaca kepala walau (1) nomor catatan: dua angkanya masuk `kepala`, jadi nomor yang benar tetap ditemukan."""
    baris = _bersih(body)
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
        awal.append(awal[-1] + len(_bersih(t)) + 1)
    ruas = []
    for a, n in kepala:
        if n == nomor:  # batas hadits = nomor lebih besar: angka kecil di awal baris sesudahnya biasanya daftar dalam syarah
            z = next((x for x, m in batas if x > a and m > nomor), len(baris))
            ruas.append((baris[a:z], " ".join(r.get("footnotes") or "" for i, r in enumerate(rr) if awal[i] < z and awal[i + 1] > a)))
    return rr, ruas


def takhrij_janggal(sid, juz, p1, p2, nomor, lafaz):
    """Nomor takhrij tidak cocok dengan kepala hadits di halaman bukti, atau lafaz bukti di hadits lain; None kalau cocok.
    Halaman tanpa kepala hadits tidak bisa dinilai."""
    rr, ruas = hadits_bernomor(sid, juz, p1, p2, nomor)
    if ruas is None:
        return None
    if not ruas:
        return f"nomor takhrij ({nomor}) bukan kepala hadits di sekitar {juz}/{p1}: cocokkan nomornya ke kitab"
    hasyiah = shamela.padat(" ".join(r.get("footnotes") or "" for r in rr))  # kalimat muhaqqiq (derajat) bukan bagian hadits
    if any(not any(shamela.padat(x) in shamela.padat(s) for s, _ in ruas) and shamela.padat(x) not in hasyiah for x in lafaz):
        return f"lafaz bukti tidak ada di hadits ({nomor}) sekitar {juz}/{p1}: mungkin nomornya milik hadits lain"


def periksa_takhrij(isi, bukti, terbukti, kutipan, perhatian):
    """Nomor takhrij yang tercetak tepat di depan juz/halaman sebuah bukti dicocokkan ke kitabnya; lafaz = potongan bukti, atau kutipan.
    Hasilnya {bukti (sid, juz, p1, p2): nomor takhrijnya}, untuk periksa_derajat."""
    bernomor = {}
    for m in TAKHRIJ.finditer(isi.translate(ANGKA_LATIN)) if re.search("أخرج|رواه", isi) else ():
        nomor, juz, hal = m[1] or m[2], m[3], m[4] or m[5]  # «ص n» (juz None): kitab satu jilid, juz bukti apa saja
        for f in map(lambda b: b.split("|"), bukti):
            p1, _, p2 = f[2].partition("-") if len(f) > 2 else ("", "", "")
            if len(f) < 3 or juz not in (None, f[1]) or p1 != hal or (f[0], f[1], int(p1), int(p2 or p1)) not in terbukti:
                continue
            bernomor.setdefault((f[0], f[1], int(p1), int(p2 or p1)), int(nomor))
            # kutipan hanya diikutkan kalau memang dicek ke bukti ini; #nomor tidak membawa lafaz
            sumber = (kutipan or "") if len(f) == 3 else "" if f[3].startswith("#") else f[3]
            lafaz = [x for x in ELIPSIS.split(re.sub(r"\{Q:[^}]*\}", " ", sumber)) if len(shamela.padat(x)) >= POTONGAN_MIN]
            pesan = takhrij_janggal(int(f[0]), f[1], int(p1), int(p2 or p1), int(nomor), lafaz)
            if pesan and f"{pesan}  || fn: {isi[:45]}" not in perhatian:
                perhatian.append(f"{pesan}  || fn: {isi[:45]}")
    return bernomor


def derajat(teks):
    """Derajat hadits yang tertulis di teks (lihat KATA_DERAJAT): {صحيح, حسن, ضعيف, موضوع, منكر}."""
    return {DERAJAT[m[1] or m[2]] for m in KATA_DERAJAT.finditer(shamela.norm(teks))}


def periksa_derajat(isi, terbukti, bernomor, galat, perhatian):
    """Catatan kaki takhrij («أخرجه/رواه …», AGENTS.md aturan takhrij): di luar Shahihain derajatnya wajib ditulis, dan
    derajat yang ditulis harus terbaca di salah satu halaman buktinya. Bukti bernomor takhrij: di matan dan حاشية hadits
    nomor itu; bukti lain (mis. «صححه الألباني في …» dengan buktinya sendiri): di seluruh halamannya, matan dan حاشية.
    Yang terbaca hanya derajat lawannya (صحيح/حسن vs ضعيف/موضوع/منكر) = GAGAL; tidak terbaca sama sekali = perhatian."""
    if not TAKHRIJ_AWAL.match(isi) or not terbukti:
        return
    tulis = derajat(re.sub(r"<<[^>]*>>", " ", isi))
    if not tulis:
        n = shamela.norm(isi)
        if not SHAHIHAIN.search(n) and not DERAJAT_TIDAK_ADA.search(n):
            perhatian.append(f"derajat hadits belum ditulis: di luar Shahihain tulis derajatnya beserta siapa yang menghukumi "
                             f"(«وصححه الألباني»، «وقال الترمذي: حديث حسن»), dari kitab yang dibaca sendiri  || fn: {isi[:45]}")
        return
    terbaca = set()
    for b in terbukti:
        ruas = hadits_bernomor(int(b[0]), b[1], b[2], b[3], bernomor[b])[1] if b in bernomor else None
        if ruas:
            teks = " ".join(m + " " + h for m, h in ruas)
        else:  # tanpa nomor, atau nomornya tidak terbaca di sana (sudah jadi perhatian nomor takhrij)
            teks = " ".join((r.get("body") or "") + " " + (r.get("footnotes") or "") for r in rekaman(int(b[0]), b[1], b[2], b[3]))
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


def henti(r, n):
    """Teks asli matan rekaman r memuat tanda akhir kalimat (HENTI) tepat di letak `padat` n, yaitu sesudah kata yang
    berakhir di n. Kata nafi yang menutup kalimat sebelumnya («أو لا.»، «وإلا فلا، ولعله») tidak menafikan kutipan."""
    teks, ruas = shamela._ruas(r, "body")
    for (a, b, _, _), (_, asli) in zip(ruas, shamela._potong(r, "body")):
        if a <= n <= b:
            for m in HENTI.finditer(asli):
                d = a + len(shamela.padat(asli[:m.start()]))
                if d == n:
                    return True
                if d > n:
                    break
    return False


def ragu_akhir(rr, akhir):
    """Kutipan yang menafikan («لا إله», «ليس من») tetapi berhenti tepat sebelum «إلا» di kitab: pengecualiannya terpotong,
    jadi maknanya bisa terbalik («أشهد أن لا إله» dari «أن لا إله إلا الله»)."""
    if not any(shamela.padat(w) in NAFI for w in akhir.split()[-5:]):  # nafi jauh sebelum ujung: «إلا»-nya milik kalimat lain
        return []
    q = shamela.padat(akhir)
    for r in rr:
        c = shamela._cocok(r, q, "body", True)
        if c:
            teks, (_, ujung) = shamela._ruas(r, "body")[0], shamela._batas_kata(r, "body")
            sesudah = teks[c[1]:min((u for u in ujung if u > c[1]), default=c[1])]
            if sesudah == "الا" and not henti(r, c[1]):
                return ["di kitab kutipan ini disambung «إلا» (pengecualiannya terpotong): pastikan maknanya tidak terbalik"]
            return []
    return []


# mukharrij yang namanya ditulis sesudah «أخرجه/رواه»: bentuk-bentuk tulisannya (i'rab, ejaan). Kitab bukti yang judul
# atau pengarangnya memuat salah satu bentuk itu = kitab mukharrij itu, syarahnya, atau takhrij/ringkasannya
MUKHARRIJ = (("البخاري",), ("مسلم",), ("أبو داود", "أبي داود", "أبا داود"), ("الترمذي",), ("النسائي",),
             ("ابن ماجه", "ابن ماجة"), ("أحمد",), ("مالك",), ("الدارمي",), ("ابن حبان",), ("الحاكم",), ("البيهقي",),
             ("الطبراني",), ("ابن خزيمة",), ("الدارقطني",), ("ابن أبي شيبة",), ("عبد الرزاق",))
TAKHRIJ_OLEH = re.compile(r"(?<!\w)(?:أخرج|خرج|رو[ىا])(?:ه|ها|هما|اه)?\s+(?:الإمام\s+|الحافظ\s+)?("
                          + "|".join(re.escape(b) for bb in MUKHARRIJ for b in sorted(bb, key=len, reverse=True)) + r")(?!\w)")


def _nama_kitab(m):
    """Bentuk `padat` yang menandai kitab bukti (metadata m) disebut di catatan kaki: dua kata awal tiap judulnya (judul
    katalog bisa «تفسير السعدي = تيسير الكريم الرحمن»; pengarang yang ditempel di judul dibuang), nama pengarang
    utuh, dan kata terakhirnya (nisbah: «أبو إسحاق الشاطبي» ditulis «الشاطبي»). Judul satu kata = kata itu."""
    nama = []
    for judul in shamela.judul_pokok(m["title_ar"]):
        kata = judul.split()
        kata = kata[:next((i for i, w in enumerate(kata) if i and PENGARANG_SESUDAH.match(w)), len(kata))]
        nama.append(" ".join(kata[:2]))
    for p in (m.get("main_author_name_ar") or "").split("،"):
        nama += [p, p.split()[-1]] if p.split() else []
    return {x for x in map(shamela.padat, nama) if len(x) >= 3}


SYARAH = re.compile(r"شرح|حاشي|تعليق|(?<!\w)على(?!\w)")  # judul kitab bukti yang memuat matan kitab lain


def kitab_lain(isi, sid_bukti):
    """Catatan kaki yang hanya menyebut kitab lain: (galat, perhatian). Yang dikenali: judul katalog kitab lain di tempat
    judul («مجموع الفتاوى، ابن تيمية» untuk bukti رسالة في القضاء والقدر) dan mukharrij lain sesudah «أخرجه/رواه»
    («أخرجه البخاري» untuk bukti صحيح مسلم), dan pengarang katalog lain di tempat pengarang (dua bagian pertama:
    «المغني، ابن قدامة» untuk bukti صحيح مسلم; judul satu kata/ringkas tidak dikenali katalog), sementara judul dan
    pengarang kitab bukti tidak disebut sama sekali.
    Tidak ditandai: rujukan ringkas tanpa judul («المرجع السابق»), perantara yang disebut («رواه البخاري، انظر: رياض
    الصالحين»), dan matan yang namanya termuat di judul syarah/hasyiah buktinya («فتح الباري بشرح البخاري» memuat
    «البخاري», «الشرح الممتع على زاد المستقنع» memuat «زاد المستقنع»). Judul lain dengan bukti syarah/hasyiah yang tidak
    memuatnya («صحيح البخاري» untuk bukti فتح الباري) = perhatian: matan bisa dikutip dari syarahnya."""
    data = [shamela.info(int(s)) for s in dict.fromkeys(sid_bukti)]
    pi = shamela.padat(isi)
    if not data or any(x in pi for m in data for x in _nama_kitab(m)):
        return None, None
    milik = shamela.padat(" ".join(m["title_ar"] + " " + (m.get("main_author_name_ar") or "") for m in data))
    lain = []
    for g in TAKHRIJ_OLEH.findall(isi):
        bentuk = next(bb for bb in MUKHARRIJ if g in bb)
        if not any(shamela.padat(b) in milik for b in bentuk):
            lain.append(f"«{g}»")
    # judul hanya dicari di tempat judul (bagian pertama catatan kaki), dua kata atau lebih, utuh atau disusul pengarang:
    # bagian lain bisa «كتاب الإيمان» (nama bab) yang kebetulan juga judul kitab
    mukharrij = len(lain)
    bagian = [b.strip() for b in PEMISAH_RUJUKAN.split(AWALAN_RUJUKAN.sub("", isi.strip())) if b.strip()]
    awal = (bagian or [""])[0].split()
    if len(awal) >= 2 and shamela.padat(" ".join(awal[:2])) in milik:  # matan di dalam syarahnya: «أوضح المسالك، ابن
        return (pesan_lain(lain, data), None) if lain else (None, None)  # هشام» untuk bukti ضياء السالك إلى أوضح المسالك
    for n in range(len(awal), 1, -1):
        judul = " ".join(awal[:n])
        nomor = shamela.nomor_judul_pokok(judul) if n == len(awal) or PENGARANG_SESUDAH.match(awal[n]) else []
        if nomor:
            if not set(nomor) & {int(s) for s in sid_bukti}:
                lain.append(f"«{judul}»")
            break
    # pengarang di tempat pengarang (bagian kedua: «المغني، ابن قدامة»; juga pertama: «ابن قدامة، المغني»): judul satu kata
    # dan judul ringkas tidak dikenali katalog, tetapi nama pengarangnya dikenali
    # «أبو يعلى» = «القاضي أبو يعلى ، ابن الفراء» (nama katalog kitab bukti memuatnya utuh sekata)
    bukti_pengarang = {str(m.get("main_author_id")) for m in data}
    nama_bukti = " " + " ".join(shamela.norm(m.get("main_author_name_ar") or "") for m in data) + " "
    for b in bagian[:2]:
        nomor = shamela.nomor_pengarang(b)
        if nomor and not nomor & bukti_pengarang and f" {shamela.norm(b)} " not in nama_bukti:
            lain.append(f"«{b}»")
    if not lain:
        return None, None
    ragu = not mukharrij and any(SYARAH.search(m["title_ar"]) for m in data)  # syarah memuat matan kitab lain
    return (None, pesan_lain(lain, data)) if ragu else (pesan_lain(lain, data), None)


def pesan_lain(lain, data):
    return (f"catatan kaki menyebut {' dan '.join(dict.fromkeys(lain))}, tetapi buktinya kitab lain "
            f"({'، '.join(m['title_ar'] for m in data)}) yang judul dan pengarangnya tidak disebut: tulis kitab yang "
            f"benar-benar dibaca, atau sebut perantaranya («…، انظر: <judul>»)")


BUKAN_NAMA_RAWI = frozenset(map(shamela.padat, "بن ابن بنت أبو أبي أبا أم عبد الله الرحمن رضي عنه عنها عنهما عنهم".split()))
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
    teks = " ".join(r.get(b) or "" for s, z, a, b_ in terbukti
                    for r in rekaman(int(s), z, max(1, a - MUNDUR_KEPALA), b_ + 1) for b in ("body", "footnotes"))
    kata = lambda t: [shamela.padat(w) for w in shamela.norm(t).split()]  # norm: «عز وجل»/«﷿» dibuang di kedua sisi
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
    jejak = shamela.padat(h.get("kutipan") or h["t"])[:20]
    blok = []
    for s, z, a, b_ in terbukti:
        raw = shamela.TAGS.sub(" ", "".join(r.get("body") or "" for r in rekaman(int(s), z, max(1, a - MUNDUR_KEPALA), b_ + 1)))
        pp = NOMOR_DI_KITAB.split(raw)
        for i, x in enumerate(pp):
            if jejak and jejak in shamela.padat(x):
                k = i  # «وعنه قال…» (berantai): rawinya disebut di hadits sebelumnya (مجمع الزوائد)
                while k and DIA.match(HARAKAT.sub("", pp[k])):
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
        return any(terbaca(w, ww) for w in wajib) or abadilah and shamela.padat("عبد الله") in shamela.padat(x)
    if not galat and terbukti and wajib and not any(map(di_blok, blok)):
        perhatian = perhatian or (f"rawi «{h['r']}» di {{H:…|{h['r']}|…}} tidak terbaca di halaman bukti catatan kakinya: "
                                  f"pastikan sahabat yang meriwayatkan hadits itu")
    return galat, perhatian


def ragu_kutipan(rr, awal, pot, periksa_angka=True, dulu=lambda: None, pengarang=None):
    """Yang tidak diperiksa pencocokan huruf: angka di kutipan (kalau belum dicocokkan di tempatnya oleh susunan_kitab),
    dan kata nafi tepat sebelum kutipan di matan kitab, juga di akhir halaman sebelumnya (dulu() = rekaman sebelum rr).
    pengarang (nama `padat`): naskah menisbatkan kutipan ke pengarang kitab; kalau di kitab kutipan itu diantar
    «قال الشافعي» (orang lain), pembicaranya diragukan."""
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
            if kata in NAFI and not henti(lalu or r, len(shamela._ruas(lalu, "body")[0]) if lalu else sebelum[-1]):
                ragu.append(f"di kitab tepat sebelum kutipan ada «{kata}»: pastikan maknanya tidak terbalik")
            if pengarang:
                n = len(sebelum) - 1  # kata kitab sebelum kutipan di rekaman ini
                kata = _kata_titik(r)[:n][-PENGANTAR_KATA:]
                lalu = (rr[k - 1] if k else dulu()) if len(kata) < PENGANTAR_KATA else None
                if lalu:  # pengantar di akhir halaman sebelumnya
                    kata = (_kata_titik(lalu) + kata)[-PENGANTAR_KATA:]
                lain = penutur_lain(kata, pengarang)
                if lain:
                    ragu.append(f"di kitab kalimat ini diantar «{lain}:», bukan ucapan pengarang: pastikan pembicaranya")
            break
    return ragu


GELAR = re.compile(r"^(?:(?:الإمام|الشيخ|العلامة|الحافظ|القاضي)\s+)+")  # «قال الإمام البهوتي:» -> البهوتي
PENGANTAR_KATA = 6 # kata kitab tepat sebelum kutipan yang dibaca untuk mencari pengantar ucapan «قال الشافعي:»
PENGANTAR = frozenset(map(shamela.padat, "قال وقال فقال قاله وقاله ونقل نقل وعن عن".split()))
# kata sesudah pengantar yang bukan nama orang lain: doa («رحمه الله تعالى»), «قال في المغني» (-> المغني), dan
# sebutan pengarang sendiri («قال المصنف رحمه الله:» di kitabnya sendiri; «قلت:»)
BUKAN_NAMA = frozenset(map(shamela.padat, "رحمه رحمهم رحمهما الله تعالى رضي عنه عنها عنهما عنهم في".split()))
SEBUTAN_PENGARANG = frozenset(map(shamela.padat, "المصنف المؤلف الشيخ قلت".split()))


def _kata_titik(r):
    """`shamela.kata_titik_dua` matan r, atau [] kalau pemotongan katanya tidak sama dengan `_batas_kata`."""
    teks, mulai = shamela._ruas(r, "body")[0], sorted(shamela._batas_kata(r, "body")[0])
    kata = shamela.kata_titik_dua(r)
    return kata if [w for w, _ in kata] == [teks[a:b] for a, b in zip(mulai, mulai[1:] + [len(teks)])] else []


def penutur_lain(kata, pengarang):
    """Pengantar ucapan orang lain tepat sebelum kutipan di kitab: kata-kata [(`padat`, diikuti «:»)] yang diakhiri
    «قال/نقل/عن <nama>:» (paling banyak PENGANTAR_KATA kata) -> «قال الشافعي»; '' kalau tidak ada, tanpa nama, atau
    namanya pengarang kitab sendiri (pengarang = namanya, `padat`)."""
    if not kata or not kata[-1][1]:  # pengantar ucapan berakhir dengan «:» tepat sebelum kutipan
        return ""
    w = [x for x, _ in kata]
    i = next((i for i in range(len(w) - 2, -1, -1) if w[i] in PENGANTAR), None)
    nama = [x for x in w[i + 1:] if x not in BUKAN_NAMA] if i is not None else []
    if not nama or any(x in SEBUTAN_PENGARANG for x in nama) or pengarang in "".join(nama):
        return ""
    return " ".join(w[i:])


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


def _rentang(hal, pisah="، "):
    """[36, 37, 38, 41] -> «36-38، 41»."""
    potong, awal = [], hal[0]
    for x, y in zip(hal, hal[1:] + [None]):
        if y != x + 1:
            potong.append(f"{awal}-{x}" if x != awal else str(x)); awal = y
    return pisah.join(potong)


# awal perhatian: baris naskahnya, mis. «baris 77: » atau, untuk perhatian gabungan, «baris 77, 81-83: »
BARIS_AWAL = re.compile(r"baris (\d+(?:-\d+)?(?:, \d+(?:-\d+)?)*): ")


def daftar_baris(nn):
    """Nomor baris naskah -> «77, 81-83» (urut, tanpa kembar)."""
    return _rentang(sorted(set(nn)), ", ")


def pisah_baris(p):
    """«baris 77, 81-83: isi» -> ([77, 81, 82, 83], «isi»); tanpa awal «baris …: » -> ([], p).
    Dipakai juga .github/uji_jebakan.py untuk mencocokkan perhatian gabungan ke tiap barisnya."""
    m = BARIS_AWAL.match(p)
    if not m:
        return [], p
    return [n for a, z in re.findall(r"(\d+)(?:-(\d+))?", m[1]) for n in range(int(a), int(z or a) + 1)], p[m.end():]


def gabung_kembar(perhatian):
    """Perhatian yang isinya sama persis di beberapa baris naskah (bukti di حاشية yang sama, kata nafi yang sama)
    jadi satu baris «baris 77, 81-83: …» di tempat kemunculan pertamanya: dibaca dan dibereskan sekali."""
    kumpul = {}
    for p in perhatian:
        nn, isi = pisah_baris(p)
        kumpul.setdefault(isi, []).extend(nn)
    return [f"baris {daftar_baris(nn)}: {isi}" if nn else isi for isi, nn in kumpul.items()]


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
        if juz_bukti - {"-"}:  # kitab satu jilid (juz «-»): «ج1، ص55» tetap dibaca «ص55» seperti dulu
            utuh = juz_arab(utuh)
        for j in juz_bukti - {"-"}:  # «المقدمة، ص1» = halaman 1 bagian المقدمة, sama dengan «المقدمة/1»
            if not j.isdigit():
                utuh = re.sub(rf"(?<!\w){re.escape(j)}\s*[،,:]?\s*ص\s*(?=\d)", f"{j}/", utuh)
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
                    galat.append(f"halaman tercetak {juz}/{a}-{b}: bukti belum mencakup {_rentang(kurang)}{kitabnya}: "
                                 f"lebarkan buktinya (<<{sid}|{juz}|{a}-{b}>>) atau cetak halaman buktinya saja "
                                 f"({juz}/{_rentang(sorted(set(range(a, b + 1)) & ada))})")
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


def penanda_ayat(spec):
    """{Q:spec} di teks polos yang dicek (AYAT_DI_KUTIPAN): « ﴿s:a﴾ », « ﴿s:a-b﴾ », atau « ﴿s:a:i-j﴾ » dengan angka Latin.
    Kata ke-i s.d. j ikut dibawa: yang dibandingkan dengan ayat di kitab adalah ayat yang tercetak."""
    _, s, a = ayat(spec)
    p = spec.split(":")
    if len(p) > 2:
        i, _, j = p[2].partition("-")
        a += f":{int(i)}-{int(j or i)}"
    return f" ﴿{s}:{a}﴾ "


# tanda petik miring dari Word/HP dan bentuk jarang (❝…❞ 〝…〞 ‟…” ❮…❯ ❛…❜) dibaca seperti " « » ‘; tanda yang tidak dikenal
# membuat kutipannya tidak dicek sama sekali
PETIK = str.maketrans("“”„＂‹›﹁﹂「」‚‛❝❞〝〞〟‟⹂❮❯❛❜", '""""«»«»«»‘‘' + '"' * 7 + "«»‘‘")
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
    """Isi tiap kutipan teratas "..." atau «...» di teks, urut dari depan; kutipan di dalam kutipan ikut induknya.
    Pembuka yang tidak tertutup tidak menghentikan pencarian: dulu satu «« nyasar membuat kutipan sesudahnya tidak dicek."""
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
        if d or j <= i:  # pembuka tanpa penutup: lewati tanda itu saja, kutipan sesudahnya tetap dicek
            i += 1; continue
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


def diantar_qaul(sebelum):
    """Teks sebelum kutipan berakhir dengan pengantar ucapan «قال الشيخ:» / «قال X» (klausa terakhirnya), bukan
    «قال في كتابه/بحثه …» (itu judul). Kutipan yang diantar begini = nukilan, berapa pun panjangnya."""
    pengantar = re.split(r'[.،؛"«»]', seragam(sebelum))[-1]
    return bool(QAUL.search(pengantar)) and not re.search(r"كتاب|بحث|رسال|عنوان|مقال|مجل", pengantar)


def kutipan_pendek_diantar(teks, k):
    """Kutipan k (≤3 kata) di teks diantar «قال …:»? Tanpa pengantar, kutipan sependek itu biasanya istilah («"الإيمان"»),
    begitu juga lafaz yang dibahas «قال قتادة في قوله تعالى "خلفوا"» / «يقول بدل قوله: "قديم"»."""
    t = seragam(teks)
    i = min((j for j in (t.find(f'"{k}"'), t.find(f"«{k}»")) if j >= 0), default=-1)
    sebelum = t[:i].rstrip()
    lafaz = re.search(r"(?:^|\s)[وفب]?قول(?:ه|هم|ها)?(?![ء-ي])|لفظ|كلمة", re.split(r'[.،؛"«»]', sebelum)[-1])
    return i >= 0 and diantar_qaul(sebelum) and not lafaz


def kurung_akhir(polos, seg, matn, h_pos):
    """Isi (…) yang menutup polos[seg:] bila kurung itu kutipan: diantar «قال …:» / «ﷺ:», atau tepat sesudah {H:}
    (h_pos = letak {H:} terakhir di polos). None selain itu: kurung juga dipakai untuk tahun, nomor, penjelasan pendek,
    dan nama; lafaz matn ((…)) (letak kurung bukanya di matn) sudah punya arti sendiri."""
    t = polos.rstrip(" .،,؛;" + TAK_TERLIHAT)
    if not t.endswith(")"):
        return None
    d, i = 0, len(t) - 1
    while i >= seg:
        d += (t[i] == ")") - (t[i] == "(")
        if not d:
            break
        i -= 1
    if i < seg or i in matn or not re.search(r"[ء-ي]", t[i + 1:-1]):
        return None
    sebelum = polos[seg:i].rstrip()
    sesudah_h = h_pos is not None and seg <= h_pos <= i and not polos[h_pos:i].strip()
    if sesudah_h or sebelum.endswith(":") and (diantar_qaul(sebelum) or "ﷺ" in sebelum[-4:]):
        return t[i + 1:-1]
    return None


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


def ayat_ketik(teks):
    """﴿…﴾ berhuruf Arab pertama yang diketik di luar tanda petik (di dalam petik, kutipannya dicek ke kitab), atau None."""
    dikutip = " ".join(kutipan_semua(teks))
    return next((k for k in AYAT_KETIK.findall(teks) if k not in dikutip), None)


def urai(teks, catatan, ayat_idx, hadits_idx, galat, perhatian, di_catatan=False, rumuz=None, warna=None, folder=None):
    """Pecah satu baris jadi 'runs'. Catatan kaki ([^...]) diurai rekursif. rumuz = {sid: huruf} dari @rumuz;
    warna = {sid: warna Word (BGR)} dari @warna; folder = folder bahts (tempat PDF bukti <<luar|berkas|hal>>)."""
    runs, tebal, merah, i = [], False, False, 0
    q_akhir = None  # ayat terakhir di baris ini (untuk mencocokkan catatan kaki «سورة …»)
    polos = ""  # teks polos berjalan (untuk mencari kutipan sebelum catatan kaki)
    seg = 0  # awal teks polos sesudah catatan kaki terakhir
    penggal_lalu = ""  # teks yang dirujuk catatan kaki sebelumnya (catatan kaki berurutan merujuk teks yang sama)
    # awal teks polos dan runs sesudah catatan kaki berbukti terakhir: paragraf salinan (diam) dicek sejak situ, jadi catatan
    # penjelasan di tengahnya tidak meloloskan kalimat karangan sebelumnya
    seg_bukti = seg_run_bukti = 0
    seg_h = len(hadits_idx)  # {H:} pertama sesudah catatan kaki terakhir
    matn = set()  # letak kurung buka lafaz matn ((…)) di polos: bukan kurung kutipan
    h_pos = None  # letak {H:} terakhir di polos: (…) tepat sesudahnya = matan hadits yang dikutip
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
            if merah:
                matn.add(len(polos))
            runs.append({"t": tok[0], "b": tebal, "m": True}); polos += tok[0]  # kurung lafaz matn ikut tercetak merah dan dicek
        elif tok.startswith("{Q:"):
            t, s, a = ayat(tok[3:-1])
            q_akhir = (s, a)
            PENUNJUK.append({"ayat": tok[3:-1], "t": t})
            polos += penanda_ayat(tok[3:-1])
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
            h_pos = len(polos)
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
            # bukti saja + semua sumbernya di @rumuz: tidak dicetak, dan seluruh teks sejak catatan kaki berbukti sebelumnya
            # = nukilan utuh dari halaman bukti (kitab tanpa catatan kaki: paragraf syarah yang disalin dari kitabnya)
            sid_bukti = [b.split("|")[0] for b in bukti if b.split("|")[0] != LUAR]
            diam = not isi and rumuz is not None and bool(sid_bukti) and all(x in rumuz for x in sid_bukti)
            zz = [z for z in dict.fromkeys((rumuz or {}).get(x) for x in sid_bukti) if z and z != "-"]
            penggal = polos[seg_bukti if diam else seg:]
            # catatan kaki tepat sesudah catatan kaki lain («[^…][^…]») merujuk teks yang sama dengan catatan kaki itu
            dirujuk = penggal_lalu = penggal if re.search(r"\w", penggal) else penggal_lalu
            # ayat diketik sendiri lalu dirujuk «سورة …»: tidak pernah dicek ke mushaf, jadi bisa karangan
            # (di dalam tanda petik sudah ditolak di bawah: «سورة …» tidak membebaskan prosa di dalam kutipan)
            ketik = ayat_ketik(penggal) if isi.startswith("سورة") or not (di_catatan or diam) else None
            # kutipan terakhir tepat sebelum catatan kaki; kutipan lain sejak catatan kaki sebelumnya tidak punya catatan kaki sendiri
            # Catatan penjelasan boleh berada di tengah kutipan, jadi pembukanya dapat sebelum seg.
            # Dua catatan sumber dapat membuktikan nukilan yang sama. Catatan penjelasan tanpa bukti
            # tidak perlu mengulang buktinya, kecuali ada penutup petik baru sesudah catatan terakhir.
            mk = kutipan_akhir(polos) if bukti or SISA_PETIK.search(seragam(penggal)) else None
            if ketik and isi.startswith("سورة"):
                galat.append(f"ayat diketik langsung «{ketik[:40]}»: tidak dicek ke mushaf; tulis lewat {{Q:surah:ayat}} "
                             f"|| fn: {isi[:45]}")
            elif ketik:  # di matan, tanpa rujukan «سورة …»: bisa ayat karangan; paragraf salinan berbukti (diam) dicek ke kitab
                perhatian.append(f"ayat diketik langsung «{ketik[:40]}»: tidak dicek ke mushaf; tulis lewat {{Q:surah:ayat}} "
                                 f"|| fn: {isi[:45]}")
            elif ((isi.startswith("سورة") and re.search(r"[0-9٠-٩۰-۹]", isi) or rujukan_ayat(isi))
                  and PENGANTAR_AYAT.search(re.split(r"﴿\d+:\d+(?:-\d+)?﴾", dirujuk)[-1]) and not bukti and mk is None):
                # rujukan ayat bernomor, padahal teks sesudah {Q:} terakhir (atau seluruh teks yang dirujuk) mengutip ayat
                # («قال الله تعالى», «وقال:», atau berkurung): ayatnya diketik tanpa ﴿﴾ dan tidak pernah dicek ke mushaf.
                # Tidak kena: «سورة مكية…» (tanpa nomor) dan penyebutan tanpa kutipan («في سورة طه», «في آيات كثيرة»).
                # Kutipan bertanda petik sudah GAGAL «tanpa bukti» di bawah; yang berbukti <<…>> dicek ke sumbernya.
                galat.append(f"ayat sesudah pengantarnya tidak ditulis lewat {{Q:}}: tidak dicek ke mushaf; tulis ayatnya "
                             f"lewat {{Q:surah:ayat}} || fn: {isi[:45]}")
            elif isi.startswith("سورة") and q_akhir:
                s, a = q_akhir
                nama = re.split(r"[،,:(]|\sآي", isi[4:])[0]  # «سورة الفاتحة، آية: 2.» -> «الفاتحة»
                angka = isi.translate(ANGKA_LATIN)
                ayat_sejak = {n for x, y in re.findall(rf"﴿{s}:(\d+)(?:-(\d+))?(?::\d+-\d+)?﴾", penggal) for n in range(int(x), int(y or x) + 1)}
                tertulis = NOMOR_AYAT.search(angka)  # hanya nomor sesudah «آية»: juz, halaman, dan tahun di catatan bukan nomor ayat
                if (shamela.padat(nama) != shamela.padat(SURAH[s - 1]) or not all(re.search(rf"(?<!\d){x}(?!\d)", angka) for x in a.split("-"))
                        or ayat_sejak and tertulis and set(map(int, re.findall(r"\d+", tertulis[1]))) - ayat_sejak):
                    galat.append(AYAT_TIDAK_COCOK.format(s, a, SURAH[s - 1], isi[:45]))
            elif (q_akhir and re.search(r"﴿\d", dirujuk) and (rj := rujukan_ayat(isi))
                  and shamela.padat(rj[0]) == shamela.padat(SURAH[q_akhir[0] - 1])):
                # rujukan surat yang sama dengan {Q:} di kalimatnya, tidak diawali «سورة»: nomornya tetap harus nomor {Q:}.
                # Surat lain («انظر: سورة النساء، آية: 5») = rujukan silang, tidak dicocokkan.
                s, a = q_akhir
                if not all(re.search(rf"(?<!\d){x}(?!\d)", rj[1]) for x in a.split("-")):
                    galat.append(AYAT_TIDAK_COCOK.format(s, a, SURAH[s - 1], isi[:45]))
            lain = kutipan_semua(polos[seg:])[:-1 if mk is not None else None]
            if mk is None and bukti and not diam:  # «قال ﷺ: (…)», «{H:…}(…)»: kurung itu kutipan, dicek seperti "…"
                mk = kurung_akhir(polos, seg, matn, h_pos)
            mk_pdf = mk  # kutipan untuk bukti PDF: tetap dicek walau mk dikosongkan sesudah galat lain
            sisa = luar_petik(polos[seg:])  # teks sejak catatan kaki sebelumnya, kutipan-kutipannya dibuang
            if mk is None and bukti and not diam and SISA_PETIK.search(sisa):  # nukilan utuh: tanda petiknya tidak menentukan apa pun
                perhatian.append(f"tanda petik tanpa pasangan sebelum catatan kaki: kutipannya tidak dikenali dan tidak dicek; "
                                 f"pakai \"…\" atau «…»  || fn: {isi[:45]}")
            # «"…" ... "…"»: dua kutipan disambung elipsis di luar petik. Paragraf salinan berbukti (diam) sudah dicek
            # utuh ke kitab, dan «...» di situ bisa pemisah dua paruh bait syair
            if lain and DIPOTONG.search(sisa) and not diam:
                perhatian.append(f"kutipan disambung ... di luar tanda petik: baca yang dilompati di kitab, pastikan makna dan "
                                 f"pembicaranya tetap  || " + (f"fn: {isi[:45]}" if isi else f"matan: {penggal.strip()[:45]}"))
            seg = len(polos)
            # batas paragraf salinan: bukti Shamela, atau <<luar>> yang menutup kutipan (yang dicek/diberi perhatian).
            # «سورة …»/«سبق تخريجه» dan <<luar>> tanpa kutipan tidak: teks sebelumnya ikut dicek ke bukti berikutnya
            if sid_bukti or bukti and mk is not None:
                seg_bukti = seg
            ww = {(warna or {}).get(x) for x in sid_bukti}
            if diam and len(ww) == 1 and None not in ww:  # paragraf salinan satu kitab berwarna: lafaz matn ((…)) tetap merah
                for r in runs[seg_run_bukti:]:
                    if "t" in r and not r.get("m"):
                        r["w"] = next(iter(ww))
            luar = LUAR in bukti
            pdf = [b.split("|")[1:] for b in bukti if b.startswith(LUAR + "|")]  # <<luar|berkas|hal>>
            for f in pdf:
                if len(f) != 2 or not f[0].strip() or not re.fullmatch(r"\d+(-\d+)?", f[1]):
                    raise TandaRusak(f"<<{LUAR}|{'|'.join(f)}>>: bentuknya <<{LUAR}|berkas.pdf|hal>>, hal = urutan halaman di berkas")
            bukti = [b for b in bukti if b.split("|")[0] != LUAR]
            if bukti:
                PENUNJUK.append({"bukti": bukti, "kutipan": penggal if diam else mk, "catatan": isi})
            terbukti = []  # (sid, juz, p1, p2) tiap bukti, untuk dicocokkan dengan yang tercetak
            p_awal = len(perhatian)  # perhatian catatan kaki ini mulai di sini
            kutipan_4 = []  # hasil cek kutipan ke tiap bukti berpotongan sendiri: (pesan, perhatian)
            kutipan_3 = []  # hasil cek kutipan ke tiap bukti tanpa potongan: (bukti, pesan)
            tiga = any(b.count("|") == 2 for b in bukti)
            # kutipan bertanda petik di dalam catatan kaki itu sendiri (selain judul kitab; tiga kata atau kurang tanpa «قال …:» = istilah)
            kc = [k for k in kutipan_semua(isi) if (len(k.split()) >= 4 or kutipan_pendek_diantar(isi, k))
                  and not any(shamela.nomor_judul(k.strip())) and not judul_kitab(k, sid_bukti)]
            # teks naskah tepat sebelum kutipan («قال البهوتي:»): pembicaranya dicocokkan dengan kitab di `cek`
            s = seragam(polos)
            pengantar = re.split(r'[.،؛"«»\n]', s[:s.rfind(mk) - 1])[-1] if mk and not diam and mk in s else ""
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
                    e = cek(int(f[0]), f[1], f[2], nukilan, perhatian, kutipan=True, pengantar=pengantar)
                    if not diam:  # kutipan ke bukti tanpa potongan: diputus sesudah semua bukti catatan kaki ini dicek
                        kutipan_3.append((b, e)); continue
                else:
                    pot4 = re.sub(r"\{Q:([^}]*)\}", lambda m: penanda_ayat(m.group(1)), f[3])
                    e = cek(int(f[0]), f[1], f[2], pot4, perhatian)
                    if not e and mk is not None and not tiga:
                        p = []
                        kutipan_4.append((cek(int(f[0]), f[1], f[2], mk, p, kutipan=True, pengantar=pengantar), p))
                if e:
                    galat.append(e + f"  || fn: {isi[:45]}")
                    sid_bersih = str(int(f[0]))  # «02348» dan «2348» kitab yang sama; pesan cek memakai bentuk tanpa nol
                    if e.startswith(f"teks TIDAK KETEMU di kitab {sid_bersih}"):
                        # yang dicek: kutipan sebelum catatan kaki, paragraf salinan (diam), atau potongan bukti itu sendiri
                        t = (penggal if diam else mk) if (len(f) == 3 or diam) else pot4
                        if t:
                            TERTOLAK.append((sid_bersih, t))
            # Tiap bukti tanpa potongan harus memuat kutipannya, bukan cukup salah satunya: <<sid|juz|hal>> menyatakan
            # «kutipan ini ada di sini», jadi kitab kedua yang tidak memuatnya (sumber salah, atau penisbatan palsu) tetap
            # GAGAL. Kutipan yang terbukti di bukti lain catatan kaki ini: pesannya menunjuk bentuk untuk bukti takhrij
            # berlafaz lain atau derajat dari kitab lain (<<sid|juz|hal|lafaz halaman itu>>), bukan «kutipannya salah».
            ada_di = next((b for b, e in kutipan_3 if not e), None)
            if ada_di is None and mk is not None and any(e for _, e in kutipan_3):
                # bukti berpotongan yang juga memuat kutipannya (mis. Bukhari <<1681|1|6|#1>>): hanya mengubah pesannya
                sudah = {b for b, _ in kutipan_3}
                for s, z, a, b_ in terbukti:
                    letak = f"{s}|{z}|{a}" if a == b_ else f"{s}|{z}|{a}-{b_}"
                    if letak not in sudah and not cek(int(s), z, f"{a}-{b_}", mk, [], kutipan=True, rinci=False):
                        ada_di = letak
                        break
            for b, e in kutipan_3:
                if not e:
                    continue
                if ada_di:
                    galat.append(f"kutipan sebelum catatan kaki ada di <<{ada_di}>>, tetapi tidak di <<{b}>> ({e.split(' :: ')[0]}): "
                                 f"tiap bukti <<sid|juz|hal>> tanpa potongan harus memuat kutipan itu. Bukti lain di catatan kaki "
                                 f"takhrij (riwayat berlafaz lain, derajat dari kitab lain) → tulis berpotongan "
                                 f"<<{b}|lafaz yang ada di halaman itu>>, mis. kalimat derajatnya  || fn: {isi[:45]}")
                    continue
                galat.append(e + f"  || fn: {isi[:45]}")
                sid_bersih = str(int(b.split("|")[0]))
                if e.startswith(f"teks TIDAK KETEMU di kitab {sid_bersih}"):
                    TERTOLAK.append((sid_bersih, mk))
            periksa_derajat(isi, terbukti, periksa_takhrij(isi, bukti, terbukti, mk, perhatian), galat, perhatian)
            # kutipan bertanda petik tetap dicek walau buktinya membawa potongan sendiri: cukup ada di salah satu bukti itu
            if kutipan_4 and all(e for e, _ in kutipan_4):
                # intinya dulu (naskah X, kitab Y), penjelasannya di belakang
                galat.append(f"kutipan sebelum catatan kaki: {kutipan_4[0][0]}; kutipan bertanda petik harus ada di halaman "
                             f"buktinya (potongan <<…|potongan>> hanya membuktikan potongannya; nukilan makna tanpa tanda "
                             f"petik, diawali انظر)  || fn: {isi[:45]}")
                if mk:
                    m = re.search(r"teks TIDAK KETEMU di kitab (\d+)", kutipan_4[0][0])
                    if m:
                        TERTOLAK.append((str(int(m.group(1))), mk))
            else:
                # yang sudah disebut cek potongannya (bagian muhaqqiq, حاشية) tidak diulang untuk kutipannya
                sudah = {x.split(" :: ")[0] for x in perhatian[p_awal:]}
                perhatian += [x for x in next((p for e, p in kutipan_4 if not e), []) if x.split(" :: ")[0] not in sudah]
            for k in kc if terbukti else ():
                kq = re.sub(r"\{Q:([^}]*)\}", lambda m: penanda_ayat(m.group(1)), k)  # {Q:} dicek seperti di matan
                if all(cek(int(s), z, f"{a}-{b}", kq, [], kutipan=True, rinci=False) for s, z, a, b in terbukti):
                    # judul («"…"، مجلة …», «بعنوان "…"») atau sumber <<luar>>: cukup perhatian. GAGAL hanya untuk nukilan
                    # yang diantar «…:» («قال الشيخ: "…"»), bukan «انظر:»/«بعنوان:»
                    sebelum, _, ekor = seragam(isi).partition(k)
                    sebelum, sesudah = sebelum[:-1].rstrip(), ekor[1:].lstrip()[:1]
                    # «قال X: "…"، المصدر» / «قال X "…"» tetap nukilan walau disusul koma atau tanpa titik dua
                    qaul = diantar_qaul(sebelum)
                    nukilan = not luar and (qaul or sebelum.endswith(":") and sesudah not in ("،", ",") and not re.search(
                        r"(?:انظر|ينظر|راجع|بعنوان|عنوانه|كتاب|بحث|سلسلة)\s*:$", sebelum))
                    (galat if nukilan else perhatian).append(
                        f"kutipan di dalam catatan kaki tidak ada di halaman buktinya: «{k[:40]}»; kalau itu judul, istilah, atau "
                        f"nukilan sumber di luar Shamela, buang tanda petiknya atau tambah <<{LUAR}>> dan cocokkan sendiri ke "
                        f"sumbernya  || fn: {isi[:45]}")
            # kutipan lain sejak catatan kaki sebelumnya: perhatian, kecuali yang terbaca di halaman bukti catatan kaki ini
            # atau yang memang judul yang disebut di catatan kaki itu; tiga kata atau kurang tanpa «قال …:» biasanya istilah
            for k in lain:
                if len(k.split()) < 4 and not kutipan_pendek_diantar(penggal, k) or shamela.padat(k) in shamela.padat(isi):
                    continue
                if any(not cek(int(s), z, f"{a}-{b}", k, [], kutipan=True, rinci=False) for s, z, a, b in terbukti):
                    continue
                perhatian.append(f"kutipan tanpa catatan kaki sendiri (hanya kutipan tepat sebelum [^ yang dicek): «{k[:40]}» || fn: {isi[:45]}")
            # pengecualian: rujukan ayat «سورة …» sesudah {Q:}, dan «سبق تخريجه، ص{P:…}» (buktinya di catatan kaki pertama)
            # «سورة …» hanya untuk kutipan yang memuat ayat itu; «سبق تخريجه، ص{P:k}» hanya untuk kutipan yang sama
            # dengan kutipan {H:…|k} di catatan kaki pertamanya
            for h in hadits_idx[seg_h:]:
                h.setdefault("kutipan", mk); h.setdefault("bukti", list(terbukti))
                g, p = hadits_janggal(h, terbukti, penggal)
                galat += [f"{g}  || fn: {isi[:45]}"] if g else []
                perhatian += [f"{p}  || fn: {isi[:45]}"] if p else []
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
            elif not bukti and not luar and not isi.startswith(("سورة", "سبق تخريجه")) and rujukan_halaman(isi):
                # rujukan kitab (juz/halaman, رقم الحديث) tanpa kutipan bertanda petik: penisbatan yang belum dibuktikan
                perhatian.append(f"rujukan kitab tanpa bukti (halaman atau nomor hadits tercetak, tetapi tidak ada <<…>>): "
                                 f"tambahkan <<sid|juz|hal>>; sumber yang tidak ada di Shamela: tulis <<{LUAR}>>  || fn: {isi[:45]}")
            if not diam:
                galat += cocok_halaman(isi, terbukti, perhatian)
                g, p = kitab_lain(isi, [b[0] for b in terbukti]) if "سبق تخريجه" not in isi else (None, None)
                galat += [f"{g}  || fn: {isi[:45]}"] if g else []
                perhatian += [f"{p}  || fn: {isi[:45]}"] if p else []
            sub = urai(isi, None, ayat_idx, hadits_idx, galat, perhatian, di_catatan=True)
            runs += [{"z": z} for z in zz]
            catatan.append({"runs": sub, "bukti": len(bukti), "luar": luar, "pdf": len(pdf)})
            if not diam:
                runs.append({"fn": len(catatan) - 1})
            if seg_bukti == seg:
                seg_run_bukti = len(runs)
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
    ketik = None if di_catatan else ayat_ketik(polos[seg:])  # sesudah catatan kaki terakhir (atau baris tanpa catatan kaki)
    if ketik:
        perhatian.append(f"ayat diketik langsung «{ketik[:40]}»: tidak dicek ke mushaf; tulis lewat {{Q:surah:ayat}}")
    return [r for r in runs if r.get("t", "x") != ""]


def kata(runs):
    """Jumlah kata Arab di runs naskah (untuk perkiraan jumlah halaman)."""
    return sum(len(re.findall(r"[؀-ۿ]+", r.get("t") or "")) for r in runs)


RISET = "riset.txt"
RISET_LANGKAH = {"takhrij8": "kunci {H:}", "tafsir": "surat:ayat atau surat:ayat-ayat", "khilaf": "istilah"}
Q_TANDA = re.compile(r"\{Q:([^{}]*)\}")
H_TANDA = re.compile(r"\{H:[^|{}]*\|[^|{}]*\|([a-z]+)\}")
# pembuka pendapat pertama masalah khilaf: di awal baris (boleh #S, -, **), dicocokkan sesudah harakat dan tatweel
# dibuang. Di tengah kalimat («اختار القول الأول»، «ثم قال: "…هو القول الأول"») itu المناقشة/nukilan, bukan masalah baru
KHILAF_TANDA = re.compile(r"^(?:#S\s+)?[-*\s]*(?:القول|الرأي|المذهب) ال[أا]ول(?![ء-ي])")


def periksa_riset(folder, baris, perhatian):
    """Langkah riset wajib yang tidak meninggalkan jejak di kitab lokal (AGENTS.md Alur kerja langkah 2): takhrij
    `shamela_search_phrase` kategori 8 tiap {H:}, tafsir lewat connector tiap ayat {Q:}, `shamela_research_scope`
    tiap masalah khilaf. Agen mencatatnya di riset.txt; yang belum tercatat = perhatian, tidak pernah GAGAL:
    isi riset.txt ditulis agen sendiri, jadi mesin hanya bisa menunjuk yang belum dicatat, bukan membuktikan."""
    tercatat = {"takhrij8": {}, "tafsir": set(), "khilaf": 0}
    berkas = folder / RISET
    isi = []
    if berkas.is_file():
        try:
            isi = berkas.read_text(encoding="utf-8-sig").splitlines()
        except UnicodeDecodeError:
            perhatian.append(f"{RISET} bukan UTF-8: " + ("buka di Notepad, File > Save As, pilih Encoding «UTF-8», simpan"
                                                         if os.name == "nt" else "simpan ulang sebagai UTF-8")
                             + ", lalu ulangi `cek`")
    bentuk = (f"bentuknya «langkah objek» ({'، '.join(f'{k} <{v}>' for k, v in RISET_LANGKAH.items())}), atau "
              f"«belum langkah objek alasan» untuk langkah yang tidak bisa dijalankan")
    for n, b in enumerate(isi, 1):
        kata_ = b.split()
        if not kata_ or kata_[0].startswith("#"):
            continue
        belum = kata_[0] == "belum"
        if belum:
            kata_ = kata_[1:]
        if not kata_ or kata_[0] not in RISET_LANGKAH or len(kata_) < 2:
            perhatian.append(f"{RISET} baris {n}: «{b.strip()[:50]}» tidak dikenal; {bentuk}")
            continue
        if belum and len(kata_) < 3:
            perhatian.append(f"{RISET} baris {n}: «{b.strip()[:50]}»: tulis alasannya sesudah objek, mis. "
                             f"«belum {kata_[0]} {kata_[1]} connector sedang mati»")
            continue
        langkah, objek = kata_[0], kata_[1]
        if langkah == "tafsir":
            try:
                if not re.fullmatch(r"\d+:\d+(?:-\d+)?", objek):
                    raise TandaRusak("surat/ayat itu tidak ada")
                _, s, nomor = ayat(objek)
            except (TandaRusak, ValueError) as e:
                pesan = str(e).removeprefix(f"{{Q:{objek}}}: ") if isinstance(e, TandaRusak) else "surat/ayat itu tidak ada"
                perhatian.append(f"{RISET} baris {n}: tafsir «{objek[:50]}»: {pesan}; tulis surat:ayat "
                                 f"atau surat:ayat-ayat, mis. «tafsir 3:92»")
                continue
            a, _, z = nomor.partition("-")
            tercatat["tafsir"] |= {(s, x) for x in range(int(a), int(z or a) + 1)}
        elif langkah == "takhrij8":
            tercatat["takhrij8"].setdefault(objek, n)
        else:
            tercatat["khilaf"] += 1
    sudah_h, sudah_q, khilaf, bagian, bagian_khilaf, di_r = set(), set(), 0, None, set(), False
    belum = {"takhrij8": [], "tafsir": [], "khilaf": []}  # langkah -> [(baris naskah, objek)] yang belum tercatat
    for n, b in baris:
        if b.startswith("#R"):
            di_r = True  # daftar المصادر: bukan isi bahts
        if b.startswith("@") or di_r:
            continue
        if re.match(r"#[KFBMS]\s", b):
            bagian = n
        b = re.sub(r"<<[^<>]*>>", " ", b)  # {Q:} di potongan bukti <<sid|juz|hal|…>> adalah lafaz kitab, bukan ayat yang dibahas
        for kunci in H_TANDA.findall(b):
            if kunci not in tercatat["takhrij8"] and kunci not in sudah_h:
                belum["takhrij8"].append((n, kunci))
            sudah_h.add(kunci)
        for spec in Q_TANDA.findall(b):
            try:
                _, s, nomor = ayat(spec)  # tanda yang sudah ditolak parser jangan dikembangkan jadi rentang riset
            except (TandaRusak, ValueError):
                continue
            a, _, z = nomor.partition("-")
            ayat_ = {(s, x) for x in range(int(a), int(z or a) + 1)}
            if ayat_ - tercatat["tafsir"] - sudah_q:
                belum["tafsir"].append((n, f"{s}:{nomor}"))
            sudah_q |= ayat_
        # satu masalah khilaf = satu bagian (judul #K/#F/#B/#M/#S) yang memuat «القول الأول»; baris khilaf ke-k
        # di riset.txt menutup masalah ke-k, jadi tiap masalah perlu barisnya sendiri
        if bagian not in bagian_khilaf and KHILAF_TANDA.search(HARAKAT.sub("", b).replace("ـ", "")):
            bagian_khilaf.add(bagian)
            khilaf += 1
            if khilaf > tercatat["khilaf"]:
                belum["khilaf"].append((n, f"ke-{khilaf}"))
    # satu baris per langkah, bukan per objek: ratusan ayat/hadits tidak menenggelamkan perhatian lain.
    # Semua objeknya tetap disebut (itulah yang harus dicatat); barisnya di awal, untuk pemakai dan tes jebakan
    cara = {"takhrij8": ("hadits", "jalankan `shamela_search_phrase` dengan `scope.category_ids: [8]`, lalu tambah "
                                   "baris «takhrij8 <kunci>» tiap hadits (tidak bisa: «belum takhrij8 <kunci> <alasan>», "
                                   "lalu sebut di laporan akhir)"),
            "tafsir": ("ayat", "baca tafsirnya lewat connector `tafsir`, lalu tambah baris «tafsir <surat:ayat>» tiap ayat "
                               "(tidak bisa: «belum tafsir <surat:ayat> <alasan>»)"),
            "khilaf": ("masalah khilaf («القول الأول»)",
                       f"{RISET} baru punya {tercatat['khilaf']} baris khilaf; jalankan `shamela_research_scope` sebelum "
                       f"menulis pendapat tiap mazhab, lalu tambah baris «khilaf <istilah>» tiap masalah")}
    for langkah, objek in sorted(((k, v) for k, v in belum.items() if v), key=lambda kv: kv[1][0][0]):  # urut naskah
        jenis, langkahnya = cara[langkah]
        perhatian.append(f"baris {daftar_baris(n for n, _ in objek)}: {langkah} belum tercatat di {RISET} untuk "
                         f"{len(objek)} {jenis}: {', '.join(o for _, o in objek)} → {langkahnya}")
    for kunci, n in tercatat["takhrij8"].items():
        if kunci not in sudah_h:
            perhatian.append(f"{RISET} baris {n}: takhrij8 «{kunci}»: tidak ada {{H:…|{kunci}}} di naskah (salah ketik kunci?)")


def potong(d, fasl):
    """`rakit <folder> --fasl n` (atau a-b): bahan rakit `d` (hasil utama, seluruh naskah sudah dicek) dipangkas jadi
    #F ke-n saja, untuk dosen yang meminta bahts dikumpulkan bertahap per فصل. Bentuknya mengikuti potongan yang dulu
    diterima dosen (tiap potongan dulu naskah sendiri): sampul hanya di potongan yang memuat #F pertama (bersama yang
    sebelumnya, mis. المقدمة); المصادر dan الفهارس hanya di potongan yang memuat #F terakhir (bersama yang sesudahnya,
    mis. الخاتمة), dan فهرسnya hanya berisi isi potongan itu; nomor halaman tiap potongan mulai ١.
    Kembalikan label potongan (mis. «المقدمة والفصل الأول»), yang juga ditambahkan ke nama berkas hasil."""
    m = re.fullmatch(r"([1-9][0-9]*)(?:-([1-9][0-9]*))?", fasl)
    if not m or (m[2] and int(m[2]) < int(m[1])):
        raise TandaRusak(f"--fasl «{fasl}»: tulis nomor #F, mis. «--fasl 2», atau rentang dari kecil ke besar, mis. «--fasl 1-2»")
    dari, sampai = int(m[1]), int(m[2] or m[1])
    blok = d["blok"]
    awal_f = [i for i, b in enumerate(blok) if b["k"] == "F"]
    if sampai > len(awal_f):
        raise TandaRusak(f"--fasl {fasl}: naskah ini hanya punya {len(awal_f)} #F")
    mulai = 0 if dari == 1 else awal_f[dari - 1]
    akhir = len(blok) if sampai == len(awal_f) else awal_f[sampai]
    d["blok"] = blok = blok[mulai:akhir]
    meta = d["meta"]
    label = [b["judul"].split(":")[0].strip() for b in blok if b["k"] in ("K", "F")]
    label = label[0] + "".join(" و" + x for x in label[1:])
    meta["berkas"] = f"{meta['berkas']} - {label}"
    if dari > 1:  # sampul dan halaman bernomor huruf (@nomor) hanya di potongan pertama
        meta["tanpa_sampul"] = True
        meta.pop("nomor", None)
    if sampai < len(awal_f):  # المصادر dan الفهارس hanya di potongan terakhir
        meta["tanpa"] = ", ".join(TANPA)

    def runs(rr):
        return [r for x in rr for r in x["runs"]]
    fn = {r["fn"] for r in runs(blok) if "fn" in r}
    di_sini = runs(blok) + runs(c for i, c in enumerate(d["catatan"]) if i in fn)
    bm = {r["bm"] for r in di_sini if "bm" in r}
    luar = [r["pg"] for r in di_sini if "pg" in r and r["pg"] not in bm]
    if luar:
        raise TandaRusak(f"--fasl {fasl}: catatan kaki {{P:{luar[0][2:]}}} (سبق تخريجه) menunjuk hadits yang ditakhrij di "
                         f"luar potongan ini, jadi nomor halamannya tidak ada di sini: ganti catatan kaki itu dengan "
                         f"takhrij lengkapnya")
    d["ayat"] = [a for a in d["ayat"] if a["k"] in bm]
    hadits = []
    for h in d["hadits"]:
        ks = [k for k in [h["k"], *h.get("lagi", [])] if k in bm]
        if ks:  # {H:} di potongan lain, {H2:} di sini: halaman di فهرس hanya yang di sini
            hadits.append({**h, "k": ks[0], "lagi": ks[1:]})
    d["hadits"] = hadits
    return label


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
    TERTOLAK.clear()
    PENUNJUK.clear()
    meta = {"berkas": folder.name}
    di_baris = {}  # @kunci dan #R -> nomor barisnya, untuk galat yang baru ketahuan sesudah semua baris dibaca
    rumuz = {}  # @rumuz: sid -> huruf
    warna = {}  # @warna: sid -> warna Word (BGR)
    for n, b in baris:
        g0, p0, u0 = len(galat), len(perhatian), len(PENUNJUK)
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
            if k not in ("K", "F", "B", "M", "S", "R", "T", "V", "L") or not t.strip():
                galat.append(f"baris {n}: judul harus «#K/#F/#B/#M/#S/#R/#T/#V/#L teks» :: {b[:40]}"); continue
            if k == "L":  # tercetak apa adanya, kiri ke kanan; tanda naskah tidak diurai
                if re.search(r"\[\^|<<|\{", t):
                    galat.append(f"baris {n}: #L tidak boleh memuat catatan kaki, bukti, atau tanda {{Q:/{{H: :: {b[:40]}")
                m = re.fullmatch(r"\*\*([^*]+)\*\*", t.strip())  # «#L **Abstract**»: judul Latin tebal di tengah
                if m and not m[1].strip():
                    galat.append(f"baris {n}: judul #L **…** kosong :: {b[:40]}")
                blok.append({"k": "L", "runs": [{"t": m[1].strip() if m else t}], "n": n, **({"tengah": True} if m else {})})
            elif k in ("T", "V"):  # kotak matn atau bait syair: paragraf biasa (boleh bercatatan kaki), dicetak rakit.ps1 menurut k
                if k == "V":  # kata yang dipecah «...~» dicek dan dicetak utuh, bukan sebagai dua bagian kutipan
                    t = GABUNG_PARUH.sub("", t)
                try:
                    blok.append({"k": k, "runs": urai(t, catatan, ayat_idx, hadits_idx, galat, perhatian, rumuz=rumuz, warna=warna, folder=folder)})
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
        for u in PENUNJUK[u0:]:
            u["n"] = n

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
        galat.append("tidak ada #R (المصادر والمراجع) di akhir naskah: salin baris #R dari mesin/naskah_baru.txt, "
                     "lalu tulis satu kitab per baris di bawahnya")
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
    if meta.get("pustaka", "akhir") != "akhir":
        galat.append(di("@pustaka") + f"@pustaka: «{meta['pustaka']}» tidak dikenal (yang ada: akhir)")
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
    if meta.get("nomor", "abjad") not in ("abjad", "mukadimah"):
        galat.append(di("@nomor") + f"@nomor: «{meta['nomor']}» tidak dikenal (yang ada: abjad, mukadimah)")
    elif meta.get("nomor") == "abjad" and not any(b["k"] == "F" for b in blok):
        galat.append(di("@nomor") + "@nomor: abjad memerlukan #F: nomor ١ mulai dari #F pertama")
    elif meta.get("nomor") == "mukadimah" and not any(b["k"] == "K" and b.get("judul") == "المقدمة" for b in blok):
        galat.append(di("@nomor") + "@nomor: mukadimah memerlukan «#K المقدمة»: nomor ١ mulai dari judul itu")
    # bagian kosong: judul bahts yang disusul judul setingkat/lebih tinggi (atau akhir naskah) tanpa paragraf isi di antaranya
    # (#H bukan isi). Kitab tidak: di sana #K باب di atas #F فصل, dan #S الشرح boleh hanya membawahi #S lain.
    tingkat = {"K": 0, "F": 0, "R": 0, "B": 1, "M": 2, "S": 3}
    urut = [b for b in blok if b["k"] != "H"]
    kosong = {id(a) for a, b in zip(urut, urut[1:] + [{"k": "R"}])
              if bentuk != "kitab" and a["k"] in "KFBMS" and tingkat.get(b["k"], 9) <= tingkat[a["k"]]}
    for a, b in zip(blok, blok[1:] + [{"k": ""}]):  # judul yang langsung disusul judul halaman baru tercetak sendirian di halamannya
        if id(a) in kosong:  # sekaligus menggantikan «tercetak sendirian»: menulis isinya membereskan keduanya
            perhatian.append(f"baris {a['n']}: bagian «{a['judul'][:40]}» masih kosong: belum ada paragraf isi sebelum "
                             f"judul berikutnya yang setingkat atau lebih tinggi; tulis isinya, atau hapus judulnya")
        elif a["k"] in ("K", "F", "B", "M") and b["k"] in ("K", "H", *("F",) * (bentuk != "kitab"), *meta["halaman_baru"]):
            perhatian.append(f"baris {a['n']}: judul «{a['judul'][:40]}» tercetak sendirian di halamannya, karena judul "
                             f"sesudahnya mulai halaman baru: tulis paragraf pengantar di bawahnya")
        elif (a["k"] in ("F", "B") and b["k"] in ("B", "M") and "FBM".index(b["k"]) > "FBM".index(a["k"])
              and not re.search(r"تمهيد|مدخل", b["judul"])):  # judul «تمهيد» di bawahnya = pengantar itu sendiri
            # فصل/مبحث yang langsung disusul مبحث/مطلب-nya: judul bertumpuk tanpa تمهيد (dikeluhkan dosen)
            perhatian.append(f"baris {a['n']}: judul «{a['judul'][:40]}» langsung disusul judul «{b['judul'][:40]}» "
                             f"tanpa paragraf pengantar: tulis pengantar di bawahnya (isinya dan pembagiannya: "
                             f"{'وفيه مبحثان' if a['k'] == 'F' else 'وفيه مطلبان'}…)")
    if re.fullmatch(r"0+", re.sub(r"\s", "", meta.get("nim", "").translate(ANGKA_LATIN))):  # isian contoh, bukan nomor
        galat.append(di("@nim") + f"@nim: «{meta['nim']}» tercetak di sampul sebagai nomor mahasiswa: tulis nomor asli, "
                                  "atau «-» kalau tidak ada")
    if meta.get("thalibah", "ya") != "ya":
        galat.append(di("@thalibah") + f"@thalibah: «{meta['thalibah']}» tidak dikenal: tulis «ya», atau hapus barisnya")
    fmt = meta.get("format", "imam")
    if fmt not in FORMAT:
        galat.append(di("@format") + f"@format: «{fmt}» tidak ada di mesin/format.json (yang ada: {'، '.join(FORMAT)})")
    profil = FORMAT.get(fmt)
    for k, (kunci, nilai) in TIMPA.items():
        if k not in meta:
            continue
        if meta[k] not in nilai:
            galat.append(di("@" + k) + f"@{k}: «{meta[k]}» tidak dikenal (yang ada: {', '.join(nilai)})")
        elif profil:
            profil = {**profil, kunci: nilai[meta[k]]}  # salinan: profil di FORMAT tetap utuh
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
        for r in [r for b in blok + catatan if b.get("k") != "L" for r in b["runs"]] + hadits_idx:
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
    for b in blok:  # bait syair: tanda tulis jadi jarak antarparuh dan pindah baris (\v = pindah baris dalam paragraf Word)
        if b["k"] == "V":
            for r in b["runs"]:
                if "t" in r:
                    r["t"] = re.sub(r"\s*//\s*", "\v", re.sub(r"\s*\.\.\.\s*", "\u2003\u2003\u2003", r["t"]))
    if bentuk != "kitab":  # muqarrar gabungan syarah (@bentuk: kitab) bukan riset baru
        periksa_riset(folder, baris, perhatian)
    perhatian = gabung_kembar(perhatian)  # jumlah di ringkasan = baris yang dicetak
    sidik_naskah = hashlib.sha256(naskah).hexdigest()
    with sementara(keluar or bahan(folder)) as part:
        part.write_text(json.dumps({"meta": meta, "format": profil, "blok": blok, "catatan": catatan,
                                   "ayat": ayat_idx, "hadits": hadits_idx, "pustaka": pustaka,
                                   "quran": bool(quran), "naskah_sha256": sidik_naskah}, ensure_ascii=False), encoding="utf8")
    n_bukti = sum(c["bukti"] for c in catatan)
    n_luar = sum(c["luar"] for c in catatan)  # disebut di ringkasan: tanda yang bisa menyembunyikan kutipan karangan
    n_pdf = sum(c["pdf"] for c in catatan)
    # rujukan kitab tanpa bukti sudah jadi GAGAL atau perhatian di atas: daftar ini sisanya (catatan penjelasan, <<luar>>)
    fn_teks = [(c, "".join(r.get("t", "") for r in c["runs"])) for c in catatan]
    fn_tanpa = [HARAKAT.sub("", t)[:60] for c, t in fn_teks if c["bukti"] == 0 and not c["pdf"]
                and not t.startswith(("سورة", "سبق تخريجه")) and (c["luar"] or not rujukan_halaman(t))]
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
    lap.append(f"catatan kaki tanpa bukti (selain rujukan ayat dan rujukan kitab di atas): {len(fn_tanpa)}")
    lap += [f"  - {f}" for f in fn_tanpa]
    lap.append(f"NASKAH_SHA256={sidik_naskah}")
    return len(galat), lap


def _ringkas(t, maks=200):
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= maks else f"{t[:maks // 2]} … {t[-maks // 2:]}"


def _teks_halaman(sid, juz, p1, p2, bagian):
    """Teks asli (tanpa tag dan harakat) bagian rekaman halaman p1..p2 saja, tiap halaman diawali ⦗n⦘.
    حاشية tanpa penanda halaman di rekaman banyak halaman: seluruhnya, ditandai ⦗awal-akhir⦘ (seperti `halaman`)."""
    out = []
    for r in sorted(rekaman(sid, juz, p1, p2), key=lambda r: r.get("page_num") or 0):
        pp = shamela._potong(r, bagian)
        if len(pp) == 1:
            a, z = r.get("page_num"), _akhir(r)
            pp = [(f"{a}-{z}" if z != a else a, pp[0][1])]
        else:
            pp = [(h, b) for h, b in pp if h is not None and p1 <= h <= p2]
        for h, b in pp:
            b = re.sub(r"\s+", " ", HARAKAT.sub("", shamela.TAGS.sub("", b))).strip()
            if b:
                out.append(f"⦗{h}⦘ {b}")
    return " ".join(out)


def _penunjuk_bukti(sid, juz, hal, kutipan):
    """Baris `bukti` untuk satu <<sid|juz|hal>>: nama kitab, rantai judul, dan teks halaman itu di sekitar kutipan."""
    e = salah_juz(sid, juz, hal) or salah_halaman(hal)
    if e:
        return [e]
    m = shamela.info(sid)
    hasil = [f"kitab: {m['title_ar']} — {m.get('main_author_name_ar') or '?'}"]
    p1, _, p2 = hal.partition("-")
    p1 = int(p1); p2 = int(p2) if p2 else p1
    bagian_q = [x for x in ELIPSIS.split(kutipan or "") if len(shamela.padat(x)) >= KUTIPAN_MIN]
    q = shamela.padat(bagian_q[0]) if bagian_q else ""
    rr = sorted(rekaman(sid, juz, p1, p2), key=lambda r: r.get("page_num") or 0)
    # rantai judul di letak kutipan; kutipan tidak ketemu (atau melintasi rekaman) -> judul di awal halaman p1
    letak_judul = None
    for r in rr if q else ():
        for bagian, _ in shamela.BAGIAN:
            c, h = shamela._cocok(r, q, bagian), shamela.tempat(r, q, bagian, dalam=(p1, p2))
            if c and h and p1 <= (h[0] or 0) and (h[1] or 0) <= p2:
                letak_judul = letak_judul or (r, c, h, bagian)
    if not letak_judul and rr:
        batas = shamela._ruas(rr[0], "body")[1]
        letak_judul = (rr[0], (next((a for a, _, h1, _ in batas if h1 == p1), 0),) * 2, (p1, p1), "body")
    if letak_judul:
        judul = shamela.rantai_calon(sid, *letak_judul)
        hasil.append("bab: " + (judul[0] if len(judul) == 1 else "RAGU, salah satu dari: " + " | ".join(judul)))
    # kutipan yang lafaznya meleset di tengah: letak awalnya tetap ditunjuk (kata-kata awal terpanjang yang ada di halaman)
    kata_awal = bagian_q[0].split() if bagian_q else []
    teks = {bagian: _teks_halaman(sid, juz, p1, p2, bagian) for bagian, _ in shamela.BAGIAN}
    padat_ = {bagian: shamela.padat(raw) for bagian, raw in teks.items()}
    for k in range(len(kata_awal), 0, -1):
        qk = shamela.padat(" ".join(kata_awal[:k]))
        if len(qk) < KUTIPAN_MIN:
            break
        for bagian, tanda in shamela.BAGIAN:
            raw = teks[bagian]
            if qk not in padat_[bagian]:
                continue
            i = shamela._letak_asli(raw, qk)
            h = ([x[1] for x in re.finditer(r"⦗([\d-]+)⦘", raw[:i + 1])] or [hal])[-1]
            a, z = max(0, i - SEKITAR), i + len(kutipan) + SEKITAR
            sebagian = f" (hanya awal kutipan yang ada: «{' '.join(kata_awal[:k])}»)" if k < len(kata_awal) else ""
            hasil.append(f"{shamela.letak(juz, h)}{tanda}{sebagian}: {'…' * (a > 0)}{raw[a:z]}{'…' * (z < len(raw))}")
            return hasil
    raw = teks["body"]
    if not raw:
        return hasil + [f"{shamela.letak(juz, (p1, p2))}: halaman itu tidak ada di kitab {sid} juz {juz}"]
    sebab = "kutipan TIDAK ketemu di halaman itu" if q else "tanpa kutipan untuk dicari"
    return hasil + [f"{shamela.letak(juz, (p1, p2))}: {sebab}; awal halaman: {raw[:2 * SEKITAR]}{'…' * (len(raw) > 2 * SEKITAR)}"]


def bukti(folder, dari=None, sampai=None):
    """`bukti`: untuk tiap catatan kaki berbukti <<sid|juz|hal…>> dan ayat {Q:} di baris dari..sampai (None = semua):
    kalimat yang dibuktikan, isi catatan kakinya, lalu nama kitab, rantai judul, dan teks halaman kitab di sekitar letak
    kutipan. Naskahnya diurai `utama` (sama dengan `cek`), tetapi laporan dan putusannya tidak dicetak.
    Tiap baris keluaran diawali «baris n», supaya bisa disaring. Kembalikan jumlah yang dicetak."""
    with tempfile.TemporaryDirectory() as d:
        utama(folder, Path(d) / "bahan.json")
    pilih = [u for u in PENUNJUK if (dari is None or dari <= u["n"]) and (sampai is None or u["n"] <= sampai)]
    ke = {}
    for u in pilih:
        if "ayat" in u:
            print(f"baris {u['n']} ayat {{Q:{u['ayat']}}}: ﴿{u['t']}﴾")
            continue
        ke[u["n"]] = ke.get(u["n"], 0) + 1
        kepala = f"baris {u['n']} #{ke[u['n']]}"
        print(f"{kepala} kutipan: " + (f"«{_ringkas(u['kutipan'])}»" if u["kutipan"] else "(tanpa kutipan bertanda petik)"))
        print(f"{kepala} catatan: {_ringkas(u['catatan'], 300)}")
        for b in u["bukti"]:
            f = b.split("|")
            if len(f) not in (3, 4) or not f[0].isdigit() or not re.fullmatch(r"\d+(-\d+)?", f[2]):
                print(f"{kepala} <<{_ringkas(b, 80)}>>: bentuk bukti rusak (lihat `cek`)"); continue
            pot = re.sub(r"\{Q:[^}]*\}", " ﴿﴾ ", f[3]) if len(f) == 4 and not f[3].startswith("#") else None
            for x in _penunjuk_bukti(int(f[0]), f[1], f[2], pot or u["kutipan"]):
                print(f"{kepala} <<{_ringkas(b, 80)}>> {x}")
    if not pilih:
        print("Tidak ada catatan kaki berbukti <<sid|juz|hal>> atau ayat {Q:} di " + (
            "naskah ini." if dari is None else f"baris {dari}" + (f"-{sampai}" if sampai != dari else "") + "."))
    return len(pilih)
