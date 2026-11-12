# SPDX-License-Identifier: AGPL-3.0-or-later
"""Olah <bahts>/naskah.txt -> bahan JSON terpisah menurut jalur bahts/pekerjaan (untuk perakit Word)
+ verifikasi setiap rujukan ke kitab Shamela lokal. Dipanggil lewat bahts.py.

Tanda di naskah.txt (dicetak oleh: python mesin/bahts.py tanda):
  @kunci: nilai       data sampul, di awal naskah; kunci tidak dikenal = GAGAL (salah ketik tidak diabaikan). Wajib: judul dan nama; @sampul: mahad juga jenis ("-" = tidak tercetak), nim, fasl.
                      Opsional: musyrif, jabatan (kosong atau "-" = tidak tercetak), thalibah (ya = sampul mencetak «اسم الطالبة»),
                      basmalah (ya = satu halaman ﷽ huruf Arabic Typesetting sesudah sampul; bawaan: tidak ada),
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
                      tanpa (yang tidak dicetak: فهرس ayat, hadits, alam, maudhuat, dan pustaka = المصادر والمراجع
                      bila dosen minta sumber cukup di catatan kaki; mis. «@tanpa: ayat, hadits»).
                      فهرس الآيات، فهرس الأحاديث، dan فهرس الأعلام yang kosong tidak dicetak dengan sendirinya
                      pustaka (akhir = urutan خطة yang menaruh فهرس المصادر والمراجع sesudah فهرس الأحاديث (dan فهرس الأعلام
                      kalau ada), dengan judul itu;
                      bawaan: المصادر والمراجع sebelum فهرس الآيات)
                      templat (berkas .docx di folder bahts): Word mahasiswa sendiri; halaman pertamanya jadi sampul
                      apa adanya (data sampul di naskah tidak dipakai), kepala halamannya (termasuk judul di dalamnya) dipakai
                      di tiap halaman isi; nomor halaman di kaki hanya kalau kepala itu tidak memuat nomor halaman
                      nomor (abjad = halaman sebelum #F pertama bernomor huruf أ ب ت, mulai #F pertama nomornya ١، ٢، ٣)
                      (mukadimah = sama, tetapi nomor ١ mulai #K المقدمة; الإهداء dst. sebelumnya tetap huruf)
                      minimal_kitab (bilangan; bawaan 25): kitab di المصادر (selain القرآن الكريم) kurang dari itu = perhatian.
                      Dosen minta lebih sedikit atau lebih banyak → tulis jumlahnya, mis. «@minimal_kitab: 20»; 0 = tidak dinilai
                      halaman_baru (B, M, atau keduanya): judul itu juga mulai halaman baru, mis. dosen minta
                      مبحث dan مطلب beda halaman, مبحث = #F dan مطلب = #B → «@halaman_baru: B»
                      Tata letak per bagian, bisa dicampur (nilai pertama = bawaan):
                      kepala (- | kotak = judul kanan, nomor halaman berbingkai kiri, garis di bawahnya; kepala_judul =
                      judul pendek di situ, bawaan @judul), fihris_ayat (tabel | surah = السورة digabung per surat | الآية
                      «… الآية n» | الصفحة, berjudul فهرس الآيات الكريمة), fihris_hadits (tabel | ringkas = الأحاديث | الصفحة,
                      berjudul فهرس الأحاديث الشريفة), maudhuat (tabel | titik = baris bertitik-titik ke nomor halaman;
                      #S «❖ …» ikut), pustaka_gaya (judul | muallif = القرآن الكريم ikut bernomor; **…** tebal, __…__ miring
                      di baris #R, mis. «**ابن كثير، إسماعيل بن عمر** (ت 774هـ). __تفسير القرآن العظيم__. …»),
                      judul_kanan (B, M, atau keduanya: judul itu rata kanan, bawaan di tengah), fihris (baru | sambung =
                      المصادر dan فهرس sesudah yang pertama menyambung di halaman yang sama), sifat (baris di bawah
                      nama di sampul, mis. «الطالب بقسم الشريعة للفترة الصباحية»), qism (baris qism di sampul qism/jakarta
                      menggantikan «قسم الشريعة»/«قسم الشريعة بجاكرتا»; « // » = pindah baris, mis.
                      «معهد العلوم الإسلامية والعربية في إندونيسيا // قسم اللغة العربية»)
                      rujukan_ayat (catatan | matan = [^سورة …، آية: n.] dicetak «[السورة: n]» tepat sesudah ayatnya)
                      model (jakarta = sekaligus @sampul: jakarta, @format: jakarta, @kepala: kotak, @fihris_ayat: surah,
                      @fihris_hadits: ringkas, @maudhuat: titik, @pustaka_gaya: muallif, @pustaka: akhir,
                      @judul_kanan: B, M, @catatan_kaki: bersambung, @fihris: sambung, @rujukan_ayat: matan; kunci yang ditulis sendiri tetap menang,
                      mis. «@model: jakarta» + «@sampul: qism»). @sampul: jakarta = model qism dengan «قسم الشريعة بجاكرتا»,
                      logo berwarna, baris @sifat, dan nomor mahasiswa tanpa «الرقم الجامعي:»
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
  #J sel | sel | sel  satu baris tabel (mis. جدول المقارنة); sel dipisah « | ». Baris #J berturut-turut = satu tabel bergaris
                      selebar halaman; baris pertamanya = kepala (tebal, berlatar abu-abu, diulang di halaman berikutnya).
                      Tiap baris tabel itu harus sama jumlah selnya. Sel boleh memuat catatan kaki dan kutipan berbukti
                      (dicek seperti paragraf). Judul tabelnya ditulis sebagai #S atau paragraf sebelum baris #J pertama
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
  {N:nama}            daftarkan nama orang ke فهرس الأعلام (tidak tercetak); tempelkan langsung ke namanya di matan, tanpa spasi
                      sesudahnya («قال {N:ابن منظور}ابن منظور»; spasi di kedua sisinya jadi dua spasi), bukan di catatan kaki
                      atau judul. Nama yang sama tiap kali (beda harakat/hamzah tetap satu) = satu baris فهرس dengan semua
                      halamannya, halaman berurutan jadi rentang (٢٥-٢٩). Urut abjad tanpa «ال/ابن/أبو/أبي» di depan
                      («ابن القيم» di ق). فهرس الأعلام dicetak sesudah فهرس الأحاديث
  {A:kunci}           titik rujukan silang di matan (tidak tercetak), mis. di awal paragraf yang mau ditunjuk
  {P:kunci}           nomor halaman {H:..|kunci} atau {A:kunci}; hanya di dalam catatan kaki: [^سبق تخريجه، ص{P:kunci}.],
                      [^انظر: ص{P:kunci} من هذا البحث.]. {A:} boleh sesudah {P:}-nya («سيأتي»); nomornya diisi `rakit`
  [^ ... ]            catatan kaki
  <<sid|juz|hal>>     bukti di dalam catatan kaki (tidak ikut tercetak): kutipan bertanda petik tepat sebelum catatan kaki
                      harus ada di kitab sid pada juz/hal itu, utuh per kata. Kutipan yang dipotong: tulis ... di tempat
                      potongannya; tiap bagian dicek, harus berurutan. Kutipan tanpa bukti = GAGAL.
                      Salah di kitab: salin apa adanya lalu «[هكذا]», atau tulis kata yang benar dalam kurung siku
                      (tanpa angka); yang di luar kurung tetap dicek. Kurung siku selain «[هكذا]»/«[كذا]» = perhatian
                      Kamus (bidang Shamela الغريب والمعاجم) boleh dirujuk lewat materinya tanpa juz/halaman, «مادة (قدر)»
                      atau «(قدر)»; materinya harus ada di halaman bukti: [^القاموس المحيط، الفيروزآبادي، مادة (قدر). <<7283|-|460>>]
                      Beberapa kitab di catatan kaki «انظر:»: urut dari pengarang yang lebih dulu wafat, kalau tidak = perhatian
                      Beberapa sumber di satu catatan kaki (bukan takhrij) dipisah «؛», dipisah «،» = perhatian.
                      Rujukan pertama tiap kitab (di luar takhrij) memuat data cetak dari `kartu`, kalau tidak = perhatian;
                      nama tanpa gelar di depannya («تحقيق: د. …»، «، الشيخ …» = perhatian, juga di baris #R)
  <<sid|juz|hal|potongan>>   bukti dengan potongan lafaz sendiri (untuk nukilan makna «انظر», tanpa tanda petik).
                      #123 = nomor hadits: harus berdiri sebagai kepala hadits di halaman itu («123 - حدثنا», «36 - (123)», «(123) - حدثنا»).
                      Kutipan bertanda petik sebelum catatan kaki tetap dicek ke halaman bukti itu.
                      Potongan hanya membuktikan potongannya, bukan kalimat yang dirujuk. Cara menukil = perhatian: deret kata
                      panjang di luar tanda petik yang sama persis dengan halaman bukti (lafaz kitab tanpa tanda petik),
                      nukilan makna tanpa «انظر:»/«راجع:», kutipan lafaz yang diantar «قال …:» tetapi dirujuk «انظر:»,
                      dan kutipan yang terlalu panjang di luar ayat dan hadits (batasnya: mesin/cek_naql.py)
                      juz "-" = kitab tanpa juz di rekamannya; kitab berjilid walau halamannya bersambung tetap ditulis
                      juz-nya (bentuknya: baris «bukti:» di `kartu <id>`); hal boleh rentang 12-14. Kitab yang bagiannya
                      bernama (المقدمة، الكتاب): "-" dibaca di bagian tempat kutipannya cocok; ada di dua bagian = tulis
                      bagiannya, <<sid|الكتاب|5>>, tercetak «ص5»، «الكتاب، ص5», atau «الكتاب/5»
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
  Judul (#K/#F/#B/#M/#S/#R) tidak boleh memuat [^, <<, {Q:/{H:/{A:/{N: atau ** ({A:} ditaruh di awal paragraf sesudahnya)
  Contoh: قال ابن القيم: "…"[^مدارج السالكين، ابن القيم، 2/15. <<8370|2|15>>].

Bahts dikumpulkan bertahap per فصل: tetap SATU naskah; tiap potongan dirakit dengan «rakit <folder> --fasl n» (#F ke-n;
                      rentang 1-2 = #F ke-1 dan ke-2). Yang sebelum #F pertama (المقدمة) ikut potongan pertama, yang
                      sesudah #F terakhir (الخاتمة) ikut potongan terakhir. Sampul hanya di potongan pertama; المصادر
                      dan الفهارس hanya di potongan terakhir (فهرس berisi isi potongan itu saja); nomor halaman tiap
                      potongan mulai ١. Hasil: «<@berkas> - المقدمة والفصل الأول.pdf» dst. dan laporan-fasl<n>.txt;
                      `cek` tetap memeriksa seluruh naskah. {P:kunci} yang menunjuk hadits atau {A:} di potongan lain =
                      berhenti sebelum Word: tulis takhrij lengkap, atau sebut bagiannya dengan kata, di catatan kaki itu

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
import difflib, hashlib, io, json, os, re
from pathlib import Path

import norma
import shamela
from berkas import bahan, sementara
from cek_seluruh import periksa_dirasat, periksa_khatimah, periksa_muqaddimah, periksa_riset, porsi_kutipan
from cek_rujukan import rujukan_halaman
from cek_sumber import standar_baris
from cek_tautsiq import gelar
from dasar import AD, ANGKA_LATIN, BELUM_DIUNDUH, HERE, HURUF_LATIN, LUAR, SURAH, TandaRusak
from laporan import gabung_kembar
from naskah import Pemeriksaan, urai

FORMAT = json.loads((HERE / "format.json").read_text(encoding="utf8"))  # huruf & ukuran tiap pedoman; dipilih dengan @format
WAJIB = {"bahts": ("judul", "jenis", "nama", "nim", "fasl"), "kitab": ("judul",)}  # @bentuk: yang pertama = bawaan
# @sampul: model sampul bahts -> data yang wajib. Yang pertama = bawaan. mahad = mesin/sampul.doc (معهد، كلية الشريعة);
# qism = mesin/sampul_qism.docx (قسم الشريعة: logo, judul besar, sub-judul dalam kurung kalau ada, العام الجامعي; jenis dan nim tercetak kalau diisi, fasl tidak)
# jakarta = mesin/sampul_jakarta.docx: model qism dengan «قسم الشريعة بجاكرتا», logo berwarna, baris @sifat di bawah nama,
# nomor mahasiswa tanpa «الرقم الجامعي:»
SAMPUL = {"qism": ("judul", "nama"), "mahad": WAJIB["bahts"], "jakarta": ("judul", "nama")}
HALAMAN_BARU = ("B", "M")  # judul yang bisa dibuat mulai halaman baru lewat @halaman_baru; K dan F selalu
TANPA = ("ayat", "hadits", "alam", "maudhuat", "pustaka")  # فهرس dan المصادر yang boleh dibuang lewat @tanpa; perakitnya di rakit.ps1
# @angka: yang pertama = bawaan. Pedoman Jāmiʿat al-Imām tidak menyebut jenis angka; contoh resminya (pedoman 1443هـ,
# مجلة العلوم الشرعية) memakai hindi di nomor halaman, catatan kaki, rujukan, tahun, ayat, dan فهرس
ANGKA = ("hindi", "latin")
# Kunci naskah yang menimpa satu nilai profil @format (kombinasi permintaan dosen tanpa profil baru):
# @kunci -> (kunci di format.json yang dibaca rakit.ps1, {nilai di naskah: nilai di profil})
TIMPA = {"catatan_kaki": ("catatan_ulang_tiap_halaman", {"bersambung": False, "ulang": True}),
         "spasi": ("spasi", {"1": 1, "1.5": 1.5})}
# Bagian tata letak yang bisa dicampur: tiap kunci memilih bentuk satu bagian, nilai pertama = bawaan.
# Dibaca rakit.ps1. kepala_judul = judul pendek di kepala halaman (bawaan @judul); sifat = baris di bawah nama di sampul
GAYA = {"kepala": ("-", "kotak"),            # kotak = judul kanan, nomor halaman berbingkai kiri, garis di bawahnya
        "fihris_ayat": ("tabel", "surah"),   # surah = kolom السورة (digabung per surat) | الآية «… الآية n» | الصفحة
        "fihris_hadits": ("tabel", "ringkas"),  # ringkas = الأحاديث | الصفحة, tanpa kolom الراوي
        "maudhuat": ("tabel", "titik"),      # titik = baris bertitik-titik ke nomor halaman, tanpa tabel; #S «❖ …» ikut
        "pustaka_gaya": ("judul", "muallif"),  # muallif = القرآن الكريم ikut bernomor; **…** tebal dan __…__ miring di #R
        "judul_kanan": ("-", "B", "M", "B, M"),  # judul #B/#M rata kanan (bawaan: di tengah)
        "fihris": ("baru", "sambung"),  # sambung = المصادر/فهرس sesudah yang pertama menyambung di halaman yang sama
        "rujukan_ayat": ("catatan", "matan")}  # matan = [^سورة …، آية: n.] dicetak «[السورة: n]» tepat sesudah ayatnya
# @model: satu nama untuk sekumpulan pilihan di atas (dan @sampul, @format, @pustaka, @catatan_kaki); kunci yang ditulis
# sendiri di naskah tetap menang, jadi model bisa dicampur, mis. «@model: jakarta» + «@sampul: qism»
MODEL = {"jakarta": {"sampul": "jakarta", "format": "jakarta", "kepala": "kotak", "fihris_ayat": "surah",
                     "fihris_hadits": "ringkas", "maudhuat": "titik", "pustaka_gaya": "muallif", "pustaka": "akhir",
                     "judul_kanan": "B, M", "catatan_kaki": "bersambung", "fihris": "sambung", "rujukan_ayat": "matan"}}
# @minimal_kitab bawaan: jumlah kitab paling sedikit di المصادر (selain القرآن الكريم). Aturan repo: dosen yang
# menulis batasnya meminta 20 kitab (تعليمات كتابة البحث); bawaan dibuat 25 supaya ada lebihnya
MINIMAL_KITAB = 25
META = frozenset("judul jenis nama nim fasl musyrif jabatan thalibah basmalah sampul tahun berkas format angka angka_ayat tanpa pustaka templat halaman_baru nomor bentuk rumuz warna model kepala_judul sifat qism minimal_kitab".split()) | TIMPA.keys() | GAYA.keys()
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
KUAT = re.compile(r"[^\W\d_]|[،؛؟]")  # huruf, atau tanda baca Arab (tanda teks Arab)
# tautan/DOI di teks Arab: angkanya tetap 0-9 (hindi) dan rakit.ps1 mencetaknya kiri-ke-kanan apa adanya (bahan "tautan"),
# karena Word (angka konteks) mencetak «10.21608» di teks kanan-ke-kiri sebagai «١٠,٢١٦٠٨». Tanda baca penutup kalimat
# sesudahnya («….» «،» «)») dan kata Arab yang menempel («…/1234وانظر», huruf/harakat/tanda baca ؀-ۿ) bukan bagian
# tautan. Pola ini juga dipakai .NET (rakit.ps1): jangan pakai sintaks khusus Python
HURUF_TAUTAN = r"[^\s؀-ۿ«»()\[\]]"
TAUTAN = re.compile(rf"(?:https?://|www\.|doi\.org/|(?<![\w.])10\.[0-9]{{4,}}/)(?:{HURUF_TAUTAN}|\({HURUF_TAUTAN}*\))+(?<![.,:])")


def galat_mesin(n, e):
    return f"baris {n}: GALAT MESIN ({type(e).__name__}: {e}) — bukan salah naskah; laporkan barisnya ke pengurus mesin bahts"


def hindi(s):
    """Angka 0-9 -> ٠-٩, kecuali angka yang huruf atau tanda baca Arab terdekat sebelumnya (atau sesudahnya, kalau tidak
    ada) huruf Latin: judul berbahasa Latin tetap 0-9; «مجلة X، 2020» tetap ٢٠٢٠. Angka di dalam tautan/DOI (TAUTAN) selalu
    0-9, juga DOI tanpa huruf di depannya («انظر: 10.1016/…»). Satu lintasan linear."""
    keluar, pos, terakhir = [], 0, ""  # terakhir = huruf/tanda baca Arab terdekat sebelum posisi `pos`
    tautan = iter([t.span() for t in TAUTAN.finditer(s)] + [(len(s) + 1, len(s) + 1)])
    t = next(tautan)
    for m in re.finditer(r"[0-9]+", s):
        while t[1] <= m.start():
            t = next(tautan)
        keluar.append(s[pos:m.start()])
        for k in KUAT.finditer(s, pos, m.start()):
            terakhir = k.group()
        k = next(KUAT.finditer(s, m.end()), None)  # sesudah angka, kalau sebelumnya tidak ada
        c = terakhir or (k.group() if k else "")
        latin = t[0] <= m.start() or re.match(f"[{HURUF_LATIN}]", c)
        keluar.append(m.group() if latin else m.group().translate(AD))
        pos = m.end()
    keluar.append(s[pos:])
    return "".join(keluar)


GABUNG_PARUH = re.compile(r"\s*\.\.\.~\s*")  # «...~» di #V: dua paruh bait berbagi satu kata, disambung sebelum dicek dan dicetak
BELUM_DIUNDUH_RE = re.compile(re.escape(BELUM_DIUNDUH).replace(r"\{\}", r"(\d+)"))
BUKTI_SID = re.compile(r"<<(\d+)\|")  # nomor kitab di bukti <<sid|juz|hal>>


def kitab_dirujuk(folder):
    """Nomor kitab Shamela yang dirujuk bukti naskah di folder bahts, urut kemunculan pertama (untuk `ambil <folder>`)."""
    return list(dict.fromkeys(BUKTI_SID.findall((Path(folder) / "naskah.txt").read_text(encoding="utf-8-sig"))))


AWAL_BAGIAN = re.compile(r"^(?:\*\*)?(?:#[KFBMSR](?![^\s])|القول|الرأي|المذهب)")  # judul, atau awal pendapat baru


def kata(runs):
    """Jumlah kata Arab di runs naskah (untuk perkiraan jumlah halaman)."""
    return sum(len(re.findall(r"[؀-ۿ]+", r.get("t") or "")) for r in runs)


def sumber_tertimpa(folder, berkas, sumber, laporan="laporan.txt"):
    """Nama bahan pemakai yang bertabrakan dengan nama hasil akhir, juga sesudah `potong` mengganti @berkas."""
    tujuan = {(folder / nama).resolve().as_posix().casefold()
              for nama in (f"{berkas}.docx", f"{berkas}.pdf", laporan)}
    return [nama for nama in dict.fromkeys(sumber)
            if (folder / nama.strip()).resolve().as_posix().casefold() in tujuan]


def nama_potongan(berkas, label, fasl):
    """Nama berkas hasil `rakit --fasl`: «<@berkas> - <label potongan>» (dipakai `potong` dan `tahap`)."""
    nama = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", label).strip(" .")
    return f"{berkas} - {nama or 'fasl' + fasl}"


def rentang_fasl(fasl):
    """Nomor/rentang sah untuk hasil per فصل; dipakai perakit dan pembaca laporan tahap."""
    m = re.fullmatch(r"([1-9][0-9]*)(?:-([1-9][0-9]*))?", fasl)
    if not m or (m[2] and int(m[2]) < int(m[1])):
        raise TandaRusak(f"--fasl «{fasl}»: tulis nomor #F, mis. «--fasl 2», atau rentang dari kecil ke besar, mis. «--fasl 1-2»")
    return int(m[1]), int(m[2] or m[1])


def potong(d, fasl):
    """`rakit <folder> --fasl n` (atau a-b): bahan rakit `d` (hasil utama, seluruh naskah sudah dicek) dipangkas jadi
    #F ke-n saja, untuk dosen yang meminta bahts dikumpulkan bertahap per فصل. Bentuknya mengikuti potongan yang dulu
    diterima dosen (tiap potongan dulu naskah sendiri): sampul hanya di potongan yang memuat #F pertama (bersama yang
    sebelumnya, mis. المقدمة); المصادر dan الفهارس hanya di potongan yang memuat #F terakhir (bersama yang sesudahnya,
    mis. الخاتمة), dan فهرسnya hanya berisi isi potongan itu; nomor halaman tiap potongan mulai ١.
    Kembalikan label potongan (mis. «المقدمة والفصل الأول»), yang juga ditambahkan ke nama berkas hasil."""
    dari, sampai = rentang_fasl(fasl)
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
    meta["berkas"] = nama_potongan(meta["berkas"], label, fasl)
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
        if luar[0].startswith("a_"):
            raise TandaRusak(f"--fasl {fasl}: catatan kaki {{P:{luar[0][2:]}}} menunjuk {{A:{luar[0][2:]}}} di luar potongan "
                             f"ini, jadi nomor halamannya tidak ada di sini: sebut bagiannya dengan kata (mis. «انظر: "
                             f"المبحث الثاني من الفصل الأول») di catatan kaki itu")
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
    alam = []
    for a in d.get("alam", []):  # nama yang juga disebut di potongan lain: halaman di فهرس hanya yang di sini
        ks = [k for k in a["k"] if k in bm]
        if ks:
            alam.append({**a, "k": ks})
    d["alam"] = alam
    return label


def utama(folder, keluar=None):
    """Olah naskah di `folder`. Kembalikan (jumlah galat, baris laporan, [(sid, kutipan)] yang «teks TIDAK KETEMU di kitab»)."""
    ctx, lap = periksa(folder, keluar)
    return len(ctx.galat), lap, list(ctx.tertolak)


def periksa(folder, keluar=None):
    """Urai dan periksa naskah di `folder`, tulis bahan rakit ke `keluar`. Kembalikan (Pemeriksaan, baris laporan).
    Tahapannya urut; urutan itu juga urutan galat dan perhatian di laporan."""
    folder = Path(folder)
    naskah, baris = _baca_naskah(folder)
    ctx = Pemeriksaan(folder=folder, meta={"berkas": folder.name})
    _urai_baris(ctx, baris)
    _cek_sesudah_naskah(ctx)
    _terapkan_model_gaya(ctx)
    _cek_bentuk(ctx)
    quran = _urutkan_fihris(ctx)
    _cek_jumlah_kitab(ctx, quran)
    n_matan, n_fn = _hitung_kata(ctx)
    _cek_sampul(ctx)
    sumber = _cek_bahan_sumber(ctx, naskah)
    _cek_tata_letak(ctx)
    profil = _format_dan_angka(ctx)
    _bait_syair(ctx)
    if ctx.bentuk != "kitab":  # muqarrar gabungan syarah (@bentuk: kitab) bukan riset baru
        periksa_riset(folder, baris, ctx.perhatian)
    ctx.perhatian = gabung_kembar(ctx.perhatian)  # jumlah di ringkasan = baris yang dicetak
    sidik_naskah = hashlib.sha256(naskah).hexdigest()
    _tulis_bahan(ctx, keluar, profil, quran, sumber, sidik_naskah)
    return ctx, _laporan(ctx, n_matan, n_fn, sidik_naskah)


def _baca_naskah(folder):
    """Isi naskah.txt (bytes) dan baris-barisnya yang tidak kosong: [(nomor baris, teks)]."""
    try:
        naskah = (folder / "naskah.txt").read_bytes()
        baris = [(n, x.rstrip("\n")) for n, x in enumerate(io.StringIO(naskah.decode("utf-8-sig"), newline=None), 1) if x.strip()]
    except UnicodeDecodeError:
        raise SystemExit(f"{folder.name}/naskah.txt bukan UTF-8: " + (
            "buka di Notepad, File > Save As, pilih Encoding «UTF-8», simpan" if os.name == "nt" else
            "simpan ulang sebagai UTF-8 di editormu (atau dari terminal, mis. untuk UTF-16: "
            "iconv -f UTF-16 -t UTF-8 naskah.txt > naskah8.txt, lalu ganti naskah.txt dengan naskah8.txt)")
            + ", lalu ulangi `cek`.") from None
    return naskah, baris


def _baris_tabel(ctx, n, t):
    """«#J sel | sel»: tiap sel diurai seperti paragraf (catatan kaki dan kutipannya dicek per sel). Baris #J sesudah
    baris #J (tanpa judul atau paragraf di antaranya) = tabel yang sama, jadi jumlah selnya harus sama."""
    sel = [s.strip() for s in t.split(" | ")]
    if len(sel) < 2 or not all(sel):
        ctx.galat.append(f"baris {n}: #J butuh paling sedikit dua sel berisi, dipisah « | » :: #J {t[:40]}")
        return
    sebelum = ctx.blok[-1] if ctx.blok else None
    if sebelum and sebelum["k"] == "J" and len(sebelum["sel"]) != len(sel):
        ctx.galat.append(f"baris {n}: tabel ini {len(sebelum['sel'])} kolom (baris {sebelum['n']}), "
                         f"baris ini {len(sel)} sel :: #J {t[:40]}")
        return
    try:
        isi = [urai(s, ctx) for s in sel]
    except TandaRusak as e:
        ctx.galat.append(f"baris {n}: tanda rusak — {e}"); return
    except (KeyError, IndexError, ValueError) as e:  # bukan salah tulis naskah: mesinnya yang keliru di baris ini
        ctx.galat.append(galat_mesin(n, e)); return
    # runs = gabungan semua sel (untuk perkiraan halaman dan penghitung lain); rakit.ps1 memakai sel
    ctx.blok.append({"k": "J", "sel": isi, "runs": [r for s in isi for r in (*s, {"t": " "})], "n": n})


def _urai_baris(ctx, baris):
    """Tiap baris naskah: @data, judul #…, rujukan sesudah #R, atau paragraf (diurai `urai`).
    Tiap galat dan perhatian diberi nomor barisnya."""
    di_baris, blok, pustaka, galat, perhatian = ctx.di_baris, ctx.blok, ctx.pustaka, ctx.galat, ctx.perhatian
    for n, b in baris:
        if AWAL_BAGIAN.match(b) and ctx.standar:  # bagian baru: nilai standar sumber bagian sebelumnya
            perhatian += standar_baris(ctx.standar); ctx.standar.clear()
        g0, p0, u0, s0, r0 = len(galat), len(perhatian), len(ctx.penunjuk), len(ctx.standar), len(ctx.rujuk_silang)
        if b.startswith("@"):
            _baca_data(ctx, n, b)
        elif "#R" in di_baris and b.startswith("#"):
            galat.append(f"baris {n}: {b.split()[0]} sesudah #R di baris {di_baris['#R']} tidak dirakit: "
                         "pindahkan bagian isi sebelum #R; sesudah #R hanya satu rujukan per baris")
        elif b.strip() == "#H":  # pindah halaman: blok sesudahnya mulai halaman baru (dibaca rakit.ps1 dan perkiraan_halaman)
            blok.append({"k": "H", "runs": [], "n": n})
        elif b.startswith("#"):
            k, _, t = b[1:].partition(" ")
            if k not in ("K", "F", "B", "M", "S", "R", "T", "V", "L", "J") or not t.strip():
                galat.append(f"baris {n}: judul harus «#K/#F/#B/#M/#S/#R/#T/#V/#L/#J teks» :: {b[:40]}"); continue
            if k == "J":  # baris tabel: sel dipisah « | »; baris #J berturut-turut = satu tabel, dicetak rakit.ps1
                _baris_tabel(ctx, n, t)
            elif k == "L":  # tercetak apa adanya, kiri ke kanan; tanda naskah tidak diurai
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
                    blok.append({"k": k, "runs": urai(t, ctx)})
                except TandaRusak as e:
                    galat.append(f"baris {n}: tanda rusak — {e}")
                except (KeyError, IndexError, ValueError) as e:  # bukan salah tulis naskah: mesinnya yang keliru di baris ini
                    galat.append(galat_mesin(n, e))
            elif re.search(r"\[\^|<<|\{|\*\*", t):  # judul tercetak apa adanya (juga di فهرس الموضوعات): tanda ini ikut tercetak
                galat.append(f"baris {n}: judul tidak boleh memuat catatan kaki [^, bukti <<, tanda {{Q:/{{H:/{{A:/{{N: atau **: "
                             f"pindahkan ke paragraf sesudahnya :: {b[:40]}")
            else:
                if k == "R":
                    di_baris["#R"] = n
                blok.append({"k": k, "runs": [{"t": t, "b": True}], "judul": t, "n": n})
        elif "#R" in di_baris:
            pustaka.append(b.strip())
            g = gelar(b, "pustaka")
            if g:
                perhatian.append(g)
        else:
            try:
                blok.append({"k": "P", "runs": urai(b, ctx), "n": n})
            except TandaRusak as e:
                galat.append(f"baris {n}: tanda rusak — {e}")
            except (KeyError, IndexError, ValueError) as e:  # bukan salah tulis naskah: mesinnya yang keliru di baris ini
                galat.append(galat_mesin(n, e))
        # tiap galat dan perhatian menyebut barisnya: pemakai langsung tahu tempatnya, tes jebakan mencocokkan per baris
        galat[g0:] = [g if g.startswith("baris ") else f"baris {n}: {g}" for g in galat[g0:]]
        perhatian[p0:] = [p if p.startswith("baris ") else f"baris {n}: {p}" for p in perhatian[p0:]]
        for u in ctx.penunjuk[u0:]:
            u["n"] = n
        for c in ctx.standar[s0:]:
            c["n"] = n
        for r in ctx.rujuk_silang[r0:]:
            r["n"] = n


def _baca_data(ctx, n, b):
    """Baris «@kunci: nilai» (baris ke-n): simpan di meta; kunci yang punya pembaca di PEMBACA_DATA diurai sekarang,
    karena dipakai `urai` untuk baris-baris sesudahnya. Nilai kunci lain dicek sesudah seluruh naskah dibaca."""
    k, _, v = b[1:].partition(":")
    k = k.strip()
    if k not in META:
        mirip = difflib.get_close_matches(k, sorted(META), n=1)
        ctx.galat.append(f"baris {n}: @{k}: data tidak dikenal" +
                         (f"; maksudnya @{mirip[0]}?" if mirip else "; lihat `tanda` untuk daftar data naskah"))
    ctx.meta[k] = v.strip()
    ctx.di_baris["@" + k] = n
    if k in PEMBACA_DATA:
        PEMBACA_DATA[k](ctx, v)


def _baca_rumuz(ctx, v):
    """@rumuz: sid=huruf, …"""
    for pasang in re.split(r"[,،]", v):
        sid, _, z = pasang.partition("=")
        if not re.fullmatch(r"\d+", sid.strip()) or not z.strip():
            ctx.galat.append(f"@rumuz: «{pasang.strip()}»: bentuknya sid=huruf (atau sid=- tanpa rumuz), "
                             f"mis. «@rumuz: 12010=-، 900002=ف»"); continue
        ctx.rumuz[sid.strip()] = z.strip()


def _baca_warna(ctx, v):
    """@warna: sid=warna, … -> warna Word (BGR)."""
    for pasang in re.split(r"[,،]", v):
        sid, _, w = pasang.partition("=")
        if not re.fullmatch(r"\d+", sid.strip()) or w.strip() not in WARNA:
            ctx.galat.append(f"@warna: «{pasang.strip()}»: bentuknya sid=warna (warna yang ada: {'، '.join(WARNA)}), "
                             f"mis. «@warna: 900002=biru»"); continue
        rr, gg, bb = WARNA[w.strip()]
        ctx.warna[sid.strip()] = rr + gg * 256 + bb * 65536


PEMBACA_DATA = {"rumuz": _baca_rumuz, "warna": _baca_warna}  # @data yang langsung dipakai `urai`


def _cek_sesudah_naskah(ctx):
    """Yang baru bisa dinilai sesudah semua baris dibaca: standar sumber bagian terakhir,
    porsi kutipan, الدراسات السابقة, dan {P:} yang menunjuk {A:}/{H:}."""
    blok, catatan, hadits_idx, galat = ctx.blok, ctx.catatan, ctx.hadits_idx, ctx.galat
    perhatian = ctx.perhatian
    perhatian += standar_baris(ctx.standar); ctx.standar.clear()
    perhatian += porsi_kutipan(blok, catatan)
    perhatian += periksa_dirasat(blok, catatan)
    if ctx.meta.get("bentuk") != "kitab":  # muqarrar (@bentuk: kitab; ctx.bentuk baru diisi _cek_bentuk) tanpa المقدمة/الخاتمة bahts
        perhatian += periksa_muqaddimah(blok, ctx.meta.get("jenis", ""))
        perhatian += periksa_khatimah(blok)
    for r in ctx.rujuk_silang:
        if r["k"] not in ctx.jangkar:
            dulu = any(h["k"] == "h_" + r["k"] for h in hadits_idx)
            galat.append(f"baris {r['n']}: {{P:{r['k']}}}: " + (
                f"{{H:…|{r['k']}}} baru ditulis sesudah catatan kaki ini; «سبق تخريجه» menunjuk hadits yang sudah ditakhrij"
                if dulu else f"tidak ada {{A:{r['k']}}} atau {{H:…|{r['k']}}} di naskah"))


def _terapkan_model_gaya(ctx):
    """@model mengisi pilihan tata letak yang tidak ditulis sendiri; tiap pilihan @GAYA dicek."""
    meta, blok, catatan, galat = ctx.meta, ctx.blok, ctx.catatan, ctx.galat
    di = ctx.di
    if meta.get("model"):
        if meta["model"] not in MODEL:
            galat.append(di("@model") + f"@model: «{meta['model']}» tidak dikenal (yang ada: {'، '.join(MODEL)})")
        else:
            for k, v in MODEL[meta["model"]].items():
                if k == "sampul" and meta.get("templat"):  # @templat membawa sampulnya sendiri
                    continue
                meta.setdefault(k, v)
    for k, nilai in GAYA.items():
        meta.setdefault(k, nilai[0])
        if meta[k] not in nilai:
            galat.append(di("@" + k) + f"@{k}: «{meta[k]}» tidak dikenal (yang ada: {', '.join(nilai)})")
            meta[k] = nilai[0]
    if meta["rujukan_ayat"] == "matan":  # [^سورة …، آية: n.] jadi «[السورة: n]» di matan, catatan kakinya tidak dicetak
        for b in blok:
            for j, r in enumerate(b.get("runs", [])):
                if "fn" in r:
                    t = "".join(x.get("t", "") for x in catatan[r["fn"]]["runs"]).strip()
                    m = re.fullmatch(r"سورة\s+(.+?)،\s*آية:?\s*([\d٠-٩]+(?:\s*[-–]\s*[\d٠-٩]+)?)\.?", t)
                    if m:
                        b["runs"][j] = {"t": f" [{m.group(1)}: {m.group(2)}]", "b": False}


def _cek_bentuk(ctx):
    """@kepala dengan @templat, @tanpa, @bentuk, daftar #R, dan @berkas."""
    meta, di_baris, pustaka, galat = ctx.meta, ctx.di_baris, ctx.pustaka, ctx.galat
    folder, di = ctx.folder, ctx.di
    if meta["kepala"] == "kotak" and meta.get("templat"):
        galat.append(di("@kepala") + "@kepala: kotak dan @templat tidak bisa dipakai bersama: @templat sudah membawa kepala halamannya")
    tanpa =[t for t in re.split(r"[,، ]+", meta.get("tanpa", "")) if t]
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
    ctx.tanpa, ctx.bentuk = tanpa, bentuk


def _urutkan_fihris(ctx):
    """Urutan المصادر (القرآن الكريم paling atas), nama surat فهرس الآيات, urutan فهرس الأحاديث.
    Kembalikan baris pustaka القرآن الكريم."""
    pustaka, ayat_idx, hadits_idx = ctx.pustaka, ctx.ayat_idx, ctx.hadits_idx
    def kunci_urut(s, pengarang=False):
        s = norma.HARAKAT.sub("", s.replace("**", "").replace("__", ""))  # tanda tebal/miring @pustaka_gaya: muallif
        if pengarang:  # baris diawali nama pengarang: «ابن/أبو» tidak dihitung, «ابن القيم» di ق (أبو سليمان ص204)
            s = re.sub(r"^(?:(?:ابن|أبو|أبي|أبا|ابو|ابي|ابا)\s+)+", "", s)
        if not s.startswith("الله"):
            s = re.sub(r"^ال", "", s)
        return re.sub("[إأآ]", "ا", s)
    quran = [p for p in pustaka if norma.HARAKAT.sub("", p.replace("**", "").replace("__", "")).startswith("القرآن")]  # tanpa nomor, paling atas
    pengarang = ctx.meta.get("pustaka_gaya") == "muallif"
    pustaka = quran + sorted([p for p in pustaka if p not in quran], key=lambda p: kunci_urut(p, pengarang))
    for a in ayat_idx:
        a["surah"] = SURAH[a["s"] - 1]
    hadits_idx.sort(key=lambda h: kunci_urut(h["t"]))
    # فهرس الأعلام: satu baris per nama (semua penandanya), urut tanpa «ال/ابن/أبو» seperti pengarang di المصادر
    # nama yang hanya beda harakat atau hamzah («ابنُ عثيمين»، «احمد») = orang yang sama: satu baris, bentuk pertamanya
    gabung = {}
    for a in ctx.alam_idx:
        kunci = re.sub("[إأآ]", "ا", norma.HARAKAT.sub("", a["t"]))
        gabung.setdefault(kunci, {"t": a["t"], "k": []})["k"].append(a["k"])
    ctx.alam = sorted(gabung.values(), key=lambda a: kunci_urut(a["t"], True))
    ctx.pustaka = pustaka
    return quran


def _cek_jumlah_kitab(ctx, quran):
    """@minimal_kitab: jumlah kitab di المصادر (selain القرآن الكريم) tidak boleh kurang dari batas dosen.
    Kurang = perhatian, bukan GAGAL: dosen boleh meminta lebih sedikit, dan itu ditulis dengan «@minimal_kitab: n»."""
    meta, di = ctx.meta, ctx.di
    minimal = meta.get("minimal_kitab", "")
    if minimal and not minimal.isdecimal():
        ctx.galat.append(di("@minimal_kitab") + f"@minimal_kitab: «{minimal}» bukan bilangan bulat (mis. 20; 0 = tidak dinilai)")
        return
    batas = int(minimal) if minimal else MINIMAL_KITAB  # int() juga membaca ٢٠
    # @bentuk: kitab, @tanpa: pustaka, dan #R yang kosong (sudah GAGAL di _cek_bentuk) tidak punya daftar untuk dihitung
    if ctx.bentuk == "kitab" or "pustaka" in ctx.tanpa or not ctx.pustaka:
        return
    n = len(ctx.pustaka) - len(quran)
    if n < batas:
        asal = f"«@minimal_kitab: {minimal}»" if minimal else f"bawaan {MINIMAL_KITAB}"
        ctx.perhatian.append(
            (di("@minimal_kitab") or di("#R")) + f"المصادر والمراجع baru {n} kitab (selain القرآن الكريم), kurang dari {batas} ({asal}): "
            "tambah kitab yang benar-benar dibaca dan dirujuk di catatan kaki; kalau dosen memang meminta lebih sedikit, "
            "tulis jumlah dari dosen di «@minimal_kitab: n»")


def _hitung_kata(ctx):
    """Jumlah kata matan dan catatan kaki (sebelum angka diubah)."""
    blok, catatan = ctx.blok, ctx.catatan
    # hitung kata
    n_matan = sum(kata(b["runs"]) for b in blok)
    n_fn = sum(kata(c["runs"]) for c in catatan)
    return n_matan, n_fn


def _cek_sampul(ctx):
    """@sampul, @tahun, data sampul wajib, @pustaka, @tanpa, dan @templat."""
    meta, galat, folder, bentuk = ctx.meta, ctx.galat, ctx.folder, ctx.bentuk
    tanpa, di = ctx.tanpa, ctx.di
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


def _cek_bahan_sumber(ctx, naskah):
    """Bahan pemakai (PDF <<luar|…>>, @templat) yang akan tertimpa hasil rakit. Kembalikan daftarnya."""
    meta, galat, folder, di = ctx.meta, ctx.galat, ctx.folder, ctx.di
    # Hasil lama boleh diganti; templat dan PDF yang dirujuk naskah adalah bahan pemakai.
    # Samakan kapitalisasi juga di Linux: hasilnya akan dirakit di Windows.
    sumber = re.findall(r"<<luar\|([^|<>]+)\|", naskah.decode("utf-8-sig"))
    if meta.get("templat"):
        sumber.append(meta["templat"])
    for nama in sumber_tertimpa(folder, meta["berkas"], sumber):
        galat.append(di("@berkas") + f"hasil rakit akan menimpa bahan sumber «{nama}»: ganti @berkas atau nama berkas sumber")
    return sumber


def _cek_tata_letak(ctx):
    """@halaman_baru, @nomor, bagian kosong dan judul bertumpuk, @nim, dan kunci ya/tidak."""
    meta, blok, galat, perhatian = ctx.meta, ctx.blok, ctx.galat, ctx.perhatian
    bentuk, di = ctx.bentuk, ctx.di
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
                             f"{'وفيه مبحثان' if a['judul'].startswith('الفصل') or (a['k'] == 'F' and not a['judul'].startswith('المبحث')) else 'وفيه مطلبان'}…)")
    if re.fullmatch(r"0+", re.sub(r"\s", "", meta.get("nim", "").translate(ANGKA_LATIN))):  # isian contoh, bukan nomor
        galat.append(di("@nim") + f"@nim: «{meta['nim']}» tercetak di sampul sebagai nomor mahasiswa: tulis nomor asli, "
                                  "atau «-» kalau tidak ada")
    for kunci in ("thalibah", "basmalah"):  # kunci ya/tidak: tanpa barisnya = tidak
        if meta.get(kunci, "ya") != "ya":
            galat.append(di("@" + kunci) + f"@{kunci}: «{meta[kunci]}» tidak dikenal: tulis «ya», atau hapus barisnya")


def _format_dan_angka(ctx):
    """Profil @format (ditimpa @catatan_kaki/@spasi) dan angka yang tercetak (@angka, @angka_ayat).
    Kembalikan profilnya."""
    meta, blok, pustaka, catatan = ctx.meta, ctx.blok, ctx.pustaka, ctx.catatan
    hadits_idx, galat, di = ctx.hadits_idx, ctx.galat, ctx.di
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
        for k in ("judul", "jenis", "nama", "nim", "fasl", "musyrif", "jabatan", "tahun", "kepala_judul", "sifat", "qism"):
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
    ctx.pustaka = pustaka
    return profil


def _bait_syair(ctx):
    """Bait syair #V: tanda tulis jadi jarak antarparuh dan pindah baris."""
    blok = ctx.blok
    for b in blok:  # bait syair: tanda tulis jadi jarak antarparuh dan pindah baris (\v = pindah baris dalam paragraf Word)
        if b["k"] == "V":
            for r in b["runs"]:
                if "t" in r:
                    r["t"] = re.sub(r"\s*//\s*", "\v", re.sub(r"\s*\.\.\.\s*", "\u2003\u2003\u2003", r["t"]))


def _tulis_bahan(ctx, keluar, profil, quran, sumber, sidik_naskah):
    """Bahan rakit JSON (dibaca rakit.ps1)."""
    meta, blok, pustaka, catatan = ctx.meta, ctx.blok, ctx.pustaka, ctx.catatan
    ayat_idx, hadits_idx, folder = ctx.ayat_idx, ctx.hadits_idx, ctx.folder
    with sementara(keluar or bahan(folder)) as part:
        part.write_text(json.dumps({"meta": meta, "format": profil, "blok": blok, "catatan": catatan,
                                   "ayat": ayat_idx, "hadits": hadits_idx, "alam": ctx.alam, "pustaka": pustaka,
                                   "quran": bool(quran), "tautan": TAUTAN.pattern, "sumber": sumber,
                                   "naskah_sha256": sidik_naskah}, ensure_ascii=False), encoding="utf8")


def _laporan(ctx, n_matan, n_fn, sidik_naskah):
    """Baris laporan `cek`: ringkasan, GAGAL, perhatian, catatan kaki tanpa bukti."""
    blok, pustaka, catatan, ayat_idx = ctx.blok, ctx.pustaka, ctx.catatan, ctx.ayat_idx
    hadits_idx, galat, perhatian, folder = ctx.hadits_idx, ctx.galat, ctx.perhatian, ctx.folder
    n_bukti = sum(c["bukti"] for c in catatan)
    n_luar = sum(c["luar"] for c in catatan)  # disebut di ringkasan: tanda yang bisa menyembunyikan kutipan karangan
    n_pdf = sum(c["pdf"] for c in catatan)
    # rujukan kitab tanpa bukti sudah jadi GAGAL atau perhatian di atas: daftar ini sisanya (catatan penjelasan, <<luar>>)
    fn_teks = [(c, "".join(r.get("t", "") for r in c["runs"])) for c in catatan]
    fn_tanpa = [norma.HARAKAT.sub("", t)[:60] for c, t in fn_teks if c["bukti"] == 0 and not c["pdf"]
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
    return lap
