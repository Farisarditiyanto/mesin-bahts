# SPDX-License-Identifier: AGPL-3.0-or-later
"""Olah <bahts>/naskah.txt -> bahan JSON terpisah menurut jalur bahts/pekerjaan (untuk perakit Word)
+ verifikasi setiap rujukan ke kitab Shamela lokal. Dipanggil lewat bahts.py."""
import dataclasses, difflib, hashlib, io, json, math, os, re
from collections.abc import Callable
from pathlib import Path

import norma
import produk
import rumus
from berkas import sementara
from cek_seluruh import (KEPALA_PERHATIAN, RISET, periksa_dirasat, periksa_khatimah, periksa_muqaddimah, periksa_riset,
                         porsi_kutipan)
from cek_ayat import ayat
from cek_rujukan import kitab_tanpa_pustaka, rujukan_halaman
from cek_sumber import standar_baris
from cek_tautsiq import gelar
from dasar import (AD, ANGKA_LATIN, BUKAN_RUJUKAN, HERE, HORMAT_CETAK, HURUF_LATIN, JUDUL_BAB, JUDUL_FIHRIS, JUDUL_ISI, LUAR,
                   SUBJUDUL, SURAH, TINGKAT_JUDUL, DICABUT, TandaRusak, akhir_catatan, akhir_rumus, daftar, perintah, profil_format)
from laporan import gabung_kembar
from naskah import FIHRIS_NAMA, Pemeriksaan, urai

TANDA_NASKAH = """Tanda di naskah.txt (dicetak oleh: python mesin/bahts.py tanda):
  @kunci: nilai       data sampul, di awal naskah; kunci tidak dikenal = GAGAL (salah ketik tidak diabaikan). Wajib: judul dan nama; @sampul: mahad juga jenis ("-" = tidak tercetak), nim, fasl;
                      @sampul: tengah juga qism.
                      Opsional: musyrif, jabatan (kosong atau "-" = tidak tercetak), thalibah (ya = sampul mencetak «اسم الطالبة»),
                      basmalah (ya = satu halaman ﷽ huruf Arabic Typesetting sesudah sampul; utsmani = halaman itu berisi
                      «بسم الله الرحمن الرحيم» rasm Utsmani huruf mushaf; bawaan: tidak ada),
                      tamma (ya = halaman penutup «تمّ بحمد الله وتوفيقه» dan shalawat di tengah, sesudah الفهارس (halaman
                      terakhir), tanpa nomor halaman; bawaan: tidak ada),
                      ayat_pembuka (s:a atau s:a-b = satu halaman ayat itu, rasm Utsmani, dengan «[السورة: a]» di bawahnya,
                      sesudah sampul (dan basmalah), tanpa nomor halaman, tidak masuk فهرس الآيات; mis. «@ayat_pembuka: 12:2»),
                      sampul (qism = model قسم الشريعة, bawaan: logo, judul besar, sub-judul « - …» dalam kurung kalau ada,
                      العام الجامعي; jenis dan nim tercetak kalau diisi, fasl tidak; mahad = sampul معهد، كلية الشريعة;
                      tengah = model خطة dosen المعهد: logo berwarna di tengah atas (rasio gambarnya dijaga), lalu semua
                      baris rata tengah tebal: «معهد العلوم الإسلامية والعربية في إندونيسيا», @qism (« // » = pindah baris),
                      judul, «إعداد الطالب/الطالبة: @nama», «إشراف: @musyrif» (tanpa @musyrif tidak tercetak), @tahun;
                      jenis, nim, fasl, jabatan, dan sifat tidak tercetak di model ini;
                      kop = sampul polos tanpa logo dan bingkai, semua tebal: kop bertingkat di kanan atas (المملكة العربية
                      السعودية، وزارة التعليم، جامعة الإمام محمد بن سعود الإسلامية، معهد العلوم الإسلامية والعربية في
                      إندونيسيا، lalu @qism, bawaan قسم الشريعة), judul besar, @jenis, «إعداد الطالب:» + nama + nim, «إشراف:» +
                      musyrif + jabatan, «العام الجامعي» + @tahun; tanpa_kop = tanpa kop: judul di atas, إعداد dan إشراف di
                      tengah halaman, جامعة الإمام + المعهد + @qism + tahun di bawah, semua tebal rata tengah),
                      judul_sampul (hanya @sampul: tengah: @judul persis ditambah « // » di tempat judul pindah baris di
                      sampul, mis. «المدح في العصر العباسي // لامية مروان بن أبي حفصة في مدح المهدي»; kata yang beda
                      dari @judul = GAGAL; « - » sub-judul di tempat pindah baris boleh dibuang, tidak tercetak di ujung
                      baris; tanpa barisnya judul dipecah di « - » saja; «@qism: -» = tanpa baris qism),
                      tahun (العام الجامعي di sampul qism dan tahun sampul tengah, mis. ١٤٤٨; «١٤٤٨/١٤٤٩» tercetak «١٤٤٨/١٤٤٩ هـ»; «١٤٤٨ - ٢٠٢٦» tercetak «١٤٤٨هـ – ٢٠٢٦م»;
                      bawaan = tahun hijriah Umm al-Qura saat tahun ajaran mulai, 1 Agustus),
                      berkas (nama file hasil), format (profil di format.json; bawaan imam),
                      catatan_kaki (bersambung = nomor catatan kaki ١، ٢، ٣ … sampai akhir bahts; ulang = mulai ١ lagi tiap halaman)
                      dan spasi (1 atau 1.5: jarak baris matan dan judul) menimpa nilai itu di profil @format; bawaan = nilai profil.
                      Kombinasi permintaan dosen dibuat dengan keduanya, mis. «@format: tatbiqi» + «@catatan_kaki: bersambung»
                      angka (hindi = ٠١٢٣، bawaan; latin = 0123): angka yang tercetak di seluruh PDF,
                      termasuk nomor halaman, nomor catatan kaki, dan فهرس. Naskah boleh ditulis dengan angka mana saja
                      angka_ayat (bawaan = @angka): angka di catatan kaki rujukan ayat [^سورة …، آية: n.] saja,
                      mis. «@angka_ayat: latin» = nomor ayat di catatan kaki 0123, sisanya tetap ٠١٢٣
                      tanpa (yang tidak dicetak: فهرس ayat, hadits, atsar, alam, firaq, amakin, qabail, gharib, syir, maudhuat,
                      dan pustaka = المصادر والمراجع
                      bila dosen minta sumber cukup di catatan kaki; mis. «@tanpa: ayat, hadits»; anzhur = «انظر:»، «ينظر:»،
                      «راجع:» di awal catatan kaki (atau sesudah «؛») tidak dicetak, naskah tetap menulisnya untuk `cek`).
                      فهرس yang kosong (tanpa tandanya di naskah) tidak dicetak dengan sendirinya. Urutan فهرس: الآيات،
                      الأحاديث، الآثار، الأعلام، الفرق والمذاهب، الأماكن والبلدان، القبائل والطوائف، الغريب والمصطلحات،
                      الأشعار، (فهرس المصادر kalau @pustaka: akhir)، الموضوعات
                      pustaka (akhir = urutan خطة yang menaruh فهرس المصادر والمراجع sesudah فهرس الأحاديث (dan فهرس lain
                      sesudahnya, sebelum فهرس الموضوعات), dengan judul itu;
                      bawaan: المصادر والمراجع sebelum فهرس الآيات)
                      templat (berkas .docx di folder bahts): Word mahasiswa sendiri; halaman pertamanya (sampai pemisah
                      halaman pertama) jadi sampul apa adanya (data sampul di naskah tidak dipakai), kepala halamannya
                      (termasuk judul di dalamnya; penanda «عنوان البحث» diganti @kepala_judul/@judul) dipakai di tiap
                      halaman isi; nomor halaman di kaki hanya kalau kepala itu tidak memuat nomor halaman;
                      kertas sampulnya A4 seperti isi (tepi atas dan bidang teks Word itu tetap, selisih tinggi kertas ke tepi bawah);
                      sampul yang jadi lebih dari satu halaman di A4 = PERINGATAN sesudah `rakit`
                      nomor (abjad = halaman sebelum #F pertama bernomor huruf أ ب ت, mulai #F pertama nomornya ١، ٢، ٣)
                      (mukadimah = sama, tetapi nomor ١ mulai #K المقدمة; الإهداء dst. sebelumnya tetap huruf)
                      minimal_halaman (bilangan; bawaan 25): perkiraan halaman seluruh PDF (sampul s.d. فهرس) kurang dari
                      itu = perhatian `cek`, HALAMAN sesudah `rakit` kurang dari itu = PERINGATAN. Dosen minta lain →
                      tulis jumlahnya, mis. «@minimal_halaman: 20»; 0 = tidak dinilai
                      minimal_kitab (bilangan; bawaan tidak dinilai): dosen menulis jumlah rujukan paling sedikit, mis.
                      «لا يقل عن عشرين مرجعا» → «@minimal_kitab: 20»; kitab di المصادر (selain القرآن الكريم) kurang = perhatian
                      halaman_baru (B, M, atau keduanya): judul itu juga mulai halaman baru, mis. dosen minta
                      مبحث dan مطلب beda halaman, مبحث = #F dan مطلب = #B → «@halaman_baru: B»
                      Tata letak per bagian, bisa dicampur (nilai pertama = bawaan):
                      kepala (klasik = judul kanan, garis memanjang ke nomor halaman tebal di pojok kiri atas, tanpa nomor
                      di kaki | - = tanpa kepala, nomor di tengah kaki | kotak = judul kanan, nomor halaman berbingkai
                      kiri, garis di bawahnya | bagian = judul #K/#F berjalan tebal di
                      kanan, nomor kiri, garis selebar halaman di bawahnya | bagian_hias = bagian + hiasan kitab terbuka
                      di tengah garis | bintang = judul kanan, nomor di dalam bintang delapan di kiri atas, garis
                      tebal-tipis di bawahnya | bergantian = halaman genap judul bahts, halaman ganjil judul #K/#F
                      berjalan, di tengah bergaris tipis; nomor di tengah kaki | kaki = tanpa kepala, «- ١٢ -» di tengah
                      kaki; kepala_judul = judul pendek di kepala, bawaan @judul. Kepala hanya di halaman isi (المقدمة
                      s.d. الخاتمة): halaman depan (الإهداء، الشكر، الملخص، فهرس @maudhuat_letak: awal) dan belakang
                      (المصادر، الملاحق sesudahnya، الفهارس) hanya bernomor di tengah kaki. Sampul tetap tanpa nomor; garis
                      pemisah catatan kaki 4,5 cm di kanan), fihris_ayat (terbuka = tabel الآية | السورة | رقمها | الصفحة
                      tanpa garis tegak: garis hanya di atas dan bawah kepala dan di akhir tabel | tabel = kolom yang sama
                      bergaris penuh | surah = السورة digabung per surat | الآية «… الآية n» | الصفحة, berjudul فهرس الآيات
                      الكريمة | titik = tanpa tabel: nama tiap surat, lalu «﴿… n﴾ ...... ص» per ayat, n = nomor ayat bermotif
                      mushaf | baris_surah = tabel الآية | رقمها | الصفحة, tiap surat satu baris penuh «٢- سورة البقرة» di
                      dalam tabel, kepala berlatar abu-abu), fihris_hadits (terbuka = tabel طرف الحديث | الراوي | الصفحة
                      bergaris seperti fihris_ayat terbuka | tabel = kolom yang sama bergaris penuh | ringkas = الأحاديث |
                      الصفحة, berjudul فهرس الأحاديث الشريفة | titik = فهرس أطراف الأحاديث النبوية tanpa tabel, «طرف ...... ص»
                      urut abjad | huruf = فهرس الأحاديث النبوية dikelompokkan «حرف الهمزة»، «حرف الباء» … menurut huruf
                      pertama طرف (tanpa «ال»), baris «طرف (الراوي) ...... ص»), fihris_alam (nomor = tabel م | العلم |
                      الصفحة berkepala abu-abu | tabel = العلم | الصفحة), maudhuat (titik = baris bertitik-titik ke nomor
                      halaman; baris #K/#F dan nomornya tebal; #S «❖ …» ikut, tanpa «❖» | tabel = tabel الموضوع | الصفحة),
                      maudhuat_letak (akhir | awal = فهرس الموضوعات di depan, tepat sebelum المقدمة (atau #F pertama),
                      sesudah الإهداء/الشكر; tidak memuat dirinya sendiri), pustaka_gaya (judul_tebal = baris #R ditulis
                      seperti muallif, tercetak tanpa nomor «• **تفسير القرآن العظيم**. لإسماعيل بن عمر ابن كثير (ت:
                      ٧٧٤هـ). …» urut judul; baris lain tercetak apa adanya berbutir «•», kecuali @pustaka_gaya: judul_tebal
                      ditulis sendiri: baris tanpa __judul__ = GAGAL | judul = baris apa adanya, bernomor | muallif =
                      القرآن الكريم ikut bernomor; **…** tebal, __…__ miring di baris #R, mis. «**ابن كثير، إسماعيل بن عمر**
                      (ت 774هـ). __تفسير القرآن العظيم__. …»),
                      judul_kanan (B, M, atau keduanya: judul itu rata kanan, bawaan di tengah), fihris (baru | sambung =
                      المصادر dan فهرس sesudah yang pertama menyambung di halaman yang sama), sifat (baris di bawah
                      nama di sampul, mis. «الطالب بقسم الشريعة للفترة الصباحية»), qism (baris qism di sampul qism/jakarta
                      menggantikan «قسم الشريعة»/«قسم الشريعة بجاكرتا»; « // » = pindah baris, mis.
                      «معهد العلوم الإسلامية والعربية في إندونيسيا // قسم اللغة العربية»)
                      rujukan_ayat (catatan | matan = [^سورة …، آية: n.] dicetak «[السورة: n]» tepat sesudah ayatnya)
                      judul_fasl (dua_baris = judul #F dipecah di titik dua pertama jadi dua baris tengah:
                      «#F الفصل الأول: المقدمة» tercetak «الفصل الأول» lalu «المقدمة»; #F tanpa titik dua dan فهرس
                      الموضوعات tetap satu baris. Ditulis sendiri tanpa satu pun #F bertitik dua = GAGAL | - = judul #F
                      satu baris seperti ditulis | pemisah = tiap #F di halaman pemisah sendiri tanpa nomor (tetap
                      terhitung): judul besar (dipecah di titik dua pertama), «وفيه مطلبان:» (kata dan bilangannya dari judul
                      #B di bawahnya: فصل/مبحث/مطلب/فرع/مسألة) dan daftar judul #B-nya rata tengah tanpa ikon; isi mulai
                      halaman berikutnya; فهرس الموضوعات menunjuk halaman pemisah itu | pemisah_bingkai = sama, di dalam
                      bingkai ganda bersudut bulat (luar tebal, dalam tipis) di halaman itu saja | kotak = judul #F di kotak
                      bergaris ganda tebal-tipis di atas halaman (baris kedua sesudah titik dua lebih kecil), isi langsung
                      menyusul. Tanpa #F = GAGAL)
                      ihda (tengah = paragraf di bawah «#K الإهداء» rata tengah, tebal, tanpa awal alinea menjorok,
                      dengan celah satu baris kosong (atau jarak_paragraf profil kalau lebih besar) di atas tiap paragraf;
                      hanya berlaku kalau ada «#K الإهداء»; ditulis sendiri tanpa «#K الإهداء» berparagraf = GAGAL | - =
                      paragraf الإهداء seperti paragraf biasa)
                      logo (- | berwarna = logo جامعة الإمام berwarna seperti sampul jakarta di sampul qism; kop, data,
                      dan tata letak sampul qism tetap. Hanya untuk sampul qism: bersama @sampul jakarta/mahad atau @templat = GAGAL)
                      malahiq (akhir = bagian «#K الملاحق» (atau «#K ملحق…») sampai #R dicetak sesudah المصادر والمراجع,
                      sebelum فهرس; di naskah tetap ditulis sebelum #R. Halaman الملاحق tidak masuk HALAMAN_ISI.
                      Tidak bisa bersama @pustaka: akhir)
                      model (jakarta = sekaligus @sampul: jakarta, @format: jakarta, @kepala: kotak, @fihris_ayat: surah,
                      @fihris_hadits: ringkas, @maudhuat: titik, @pustaka_gaya: muallif, @pustaka: akhir,
                      @judul_kanan: B, M, @catatan_kaki: bersambung, @fihris: sambung, @rujukan_ayat: matan; kunci yang ditulis sendiri tetap menang,
                      mis. «@model: jakarta» + «@sampul: qism»). @sampul: jakarta = model qism dengan «قسم الشريعة بجاكرتا»,
                      logo berwarna, baris @sifat, dan nomor mahasiswa tanpa «الرقم الجامعي:»
  #K #F #B #M teks    judul tengah + masuk فهرس الموضوعات: K = مقدمة/خاتمة, F = فصل (keduanya mulai halaman baru), B = مبحث, M = مطلب.
                      Bahts pendek tanpa فصل: #F untuk مبحث, #B untuk مطلب. B/M halaman baru juga: @halaman_baru
  #S teks             sub-judul kanan (tidak masuk فهرس)
  #H                  pindah halaman: baris sesudahnya (judul, sub-judul, atau paragraf) mulai halaman baru,
                      mis. pembuka المقدمة satu halaman sendiri, lalu «#H» sebelum «#S أهمية الدراسة»
  #V teks             bait syair di tengah halaman (boleh memuat catatan kaki): « ... » = jarak antara dua paruh bait, « ...~ » = dua paruh yang berbagi satu kata digabung,
                      « // » = bait berikutnya pada baris baru; kutipan bertanda petik boleh memuat keduanya
  #L teks             paragraf bahasa Latin, kiri ke kanan (mis. الملخص bahasa Inggris); tanpa catatan kaki; Times New Roman
                      12 (judulnya 14), profil bisa mengubahnya lewat kunci "latin" di mesin/format.json. Kata Latin
                      di tengah teks Arab (paragraf, tabel, catatan kaki, المصادر) dicetak Times New Roman juga, dengan
                      ukuran sebanding: "latin" terhadap matan (matan 18 -> 12, catatan kaki 14 -> 10)
                      «#L **Abstract**» (satu baris penuh diapit **) = judul Latin tebal di tengah; paragraf #L
                      sesudahnya diberi jarak antar paragraf (6 pt) sampai blok bukan #L. Judul itu mulai halaman baru
                      kalau sebelumnya ada isi (mis. الملخص Arab), jadi الملخص dan Abstract tidak sehalaman;
                      langsung di bawah judul #K/#F/#B/#M tetap sehalaman dengan judulnya
  #J sel | sel | sel  satu baris tabel (mis. جدول المقارنة); sel dipisah « | ». Baris #J berturut-turut = satu tabel bergaris
                      selebar halaman; baris pertamanya = kepala (tebal, berlatar abu-abu, diulang di halaman berikutnya).
                      Tiap baris tabel itu harus sama jumlah selnya. Sel boleh memuat catatan kaki dan kutipan berbukti
                      (dicek seperti paragraf). Judul tabelnya ditulis sebagai #S atau paragraf sebelum baris #J pertama
  #G berkas | keterangan   gambar (PNG/JPG di folder bahts) di tengah halaman, selebar paling banyak lebar teks dan setinggi
                      paling banyak 70% halaman; keterangan (boleh kosong) tercetak di bawahnya, tanpa catatan kaki.
                      Diagram Mermaid: tulis <nama>.mmd di folder bahts, `python mesin/bahts.py diagram <folder>`, lalu
                      «#G <nama>.png | الشكل (1): …». Berkas tidak ada, di luar folder bahts, atau bukan PNG/JPG = GAGAL
  #E rumus-LaTeX      persamaan matematika di baris sendiri (tengah halaman, OMML Word asli, tanpa TeX); untuk nomor
                      persamaan di tepi kiri tulis «\\tag{1}» di dalamnya (angkanya mengikuti @angka). Teks Arab di dalam
                      rumus: «\\text{صافي الربح}». Rumus ditulis menurut urutan bacanya: yang tanpa huruf Latin/Yunani
                      (teks Arab, angka) dicetak kanan-ke-kiri, yang memuatnya kiri-ke-kanan seluruhnya. Angka di rumus
                      selalu 0-9, dan bilangan yang ditulis rapat tetap utuh («2.5», «2,5», «1\\,250», «1/2», «1:2»):
                      pasangan, daftar, dan selang ditulis berspasi «(1, 2)», «[0, 1)». Dolar «\\$». Sintaks LaTeX yang rusak = GAGAL
  #R teks             awal المصادر والمراجع; sesudahnya satu kitab per baris (diurutkan abjad otomatis, القرآن الكريم paling atas, rujukan Arab sebelum rujukan berhuruf Latin;
                      baris tanpa huruf Arab dicetak kiri-ke-kanan).
                      Wajib, kecuali «@tanpa: pustaka»; semua bagian isi harus sebelum #R (tidak boleh ada baris #… sesudahnya).
                      Kitab berbukti <<…>> di catatan kaki yang judulnya tidak ada di satu baris #R = perhatian (draf: `pustaka`)
  **...**             tebal
  {Q:s:a} {Q:s:a-b} {Q:s:a:i-j}   ayat surat s ayat a (atau a-b; atau kata ke-i s.d. j): teks resmi rasm Utsmani + masuk فهرس الآيات.
                      Ayat sesudah «قال الله تعالى»/«وقال:» yang dirujuk [^سورة …، آية: n.] tanpa {Q:} = GAGAL;
                      nomor rujukan (juga «(الفاتحة: 5)», «الفاتحة/5», «الآية 5 من سورة الفاتحة») harus nomor {Q:}.
                      Di dalam kutipan: cetak persis sebatas ayat yang dikutip kitab di situ (lebih panjang/lain = GAGAL)
  {H:طرف|راوٍ|kunci}   daftarkan hadits (atau atsar, kalau tidak dipisah lewat {AT:}) ke فهرس الأحاديث; taruh di matan, tepat sebelum «matan», bukan di catatan kaki. Kunci: huruf kecil a-z, satu kunci satu hadits
  {H2:kunci}          halaman tambahan untuk hadits yang sama (juga atsar {AT:})
  {AT:طرف|قائل|kunci}  atsar (ucapan sahabat/tabiin, bukan hadits marfu'): bentuk dan aturannya sama dengan {H:} (طرف dan
                      قائل dicek ke halaman bukti, {H2:kunci} dan {P:kunci} berlaku), tetapi masuk فهرس الآثار sendiri,
                      dicetak sesudah فهرس الأحاديث tanpa tabel «طرف (القائل) ...... ص» urut abjad. Dengan {AT:}, فهرس الأحاديث
                      bawaan berjudul فهرس الأحاديث النبوية. Tidak perlu baris takhrij8 di riset.txt
  {N:nama}            daftarkan nama orang ke فهرس الأعلام (tidak tercetak); tempelkan langsung ke namanya di matan, tanpa spasi
                      sesudahnya («قال {N:ابن منظور}ابن منظور»; spasi di kedua sisinya jadi dua spasi), bukan di catatan kaki
                      atau judul. Nama yang sama tiap kali (beda harakat/hamzah tetap satu) = satu baris فهرس dengan semua
                      halamannya, halaman berurutan jadi rentang (٢٥-٢٩). Urut abjad tanpa «ال/ابن/أبو/أبي» di depan
                      («ابن القيم» di ق). فهرس الأعلام dicetak sesudah فهرس الأحاديث
  {M:nama}            daftarkan firqah/mazhab ke فهرس الفرق والمذاهب (tidak tercetak), aturannya sama dengan {N:}:
                      «… عند {M:المعتزلة}المعتزلة»; dicetak sesudah فهرس الأعلام. Tanpa {M:} = tidak ada فهرس itu
  {B:nama} {QB:nama} {G:kata}   aturannya sama dengan {N:}, dicetak tanpa tabel «nama ...... ص» urut abjad (tanpa «ال»):
                      {B:} tempat/negeri → فهرس الأماكن والبلدان («{B:مكة}مكة»), {QB:} kabilah/kaum/pemeluk agama → فهرس القبائل
                      والطوائف («{QB:اليهود}اليهود»; firqah akidah dan mazhab fikih tetap {M:}), {G:} kata gharib atau istilah
                      yang dijelaskan → فهرس الغريب والمصطلحات («{G:الإصر}الإصر»). Tanpa tandanya = tidak ada فهرس itu
  {V:القائل}          di baris #V: bait itu masuk فهرس الأشعار (tidak tercetak), tabel م | صدر البيت | القافية | القائل |
                      الصفحة. صدر البيت = paruh sebelum « ... » bait pertama baris itu; القافية = kata terakhir paruh terakhirnya
                      (عجز). Urut حرف الروي = huruf terakhir القافية tanpa harakat («ا» penutup = ألف الإطلاق, dihitung huruf
                      sebelumnya: «سُلَّمَا» di م), hamzah dulu; lalu القافية, lalu صدر. Penyair tidak dikenal: {V:غير معروف}.
                      Di luar baris #V = GAGAL
  {A:kunci}           titik rujukan silang di matan (tidak tercetak), mis. di awal paragraf yang mau ditunjuk
  {X}                 di awal paragraf matan: paragraf خلاصة (tidak tercetak). `rakit` membuat juga «<@berkas> - الخلاصات.pdf»:
                      hanya halaman-halaman yang memuat paragraf {X}, dengan paragraf itu distabilo kuning (.docx dan PDF
                      utama tetap tanpa stabilo). Di tengah paragraf atau di catatan kaki = GAGAL
  {E:rumus-LaTeX}     persamaan matematika sebaris (OMML Word asli) di dalam paragraf, tabel #J, atau catatan kaki,
                      mis. «{E:\\alpha = 0.05}» atau «{E:ROE = \\frac{\\text{صافي الربح}}{\\text{حقوق الملكية}}}»;
                      tidak bentrok dengan tanda mata uang «$». Sintaks LaTeX rusak atau «\\tag{…}» di sini = GAGAL
  {P:kunci}           nomor halaman {H:..|kunci} atau {A:kunci}; hanya di dalam catatan kaki: [^سبق تخريجه، ص{P:kunci}.],
                      [^انظر: ص{P:kunci} من هذا البحث.]. {A:} boleh sesudah {P:}-nya («سيأتي»); nomornya diisi `rakit`
  [^ ... ]            catatan kaki; kurung siku di dalamnya («[هكذا]») berpasangan, tidak menutupnya
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
  <<luar>>            kutipan dari sumber yang tidak ada di Shamela (jurnal, PDF penelitian): lolos, tetapi masuk
                      perhatian; lafaz dan halamannya dicocokkan sendiri ke sumbernya. Judul kitab Shamela = GAGAL
  <<luar|berkas.pdf|hal>>   kutipan dari PDF penelitian yang disimpan di folder bahts (mis. hasil dirasat-pdf):
                      kutipan bertanda petik dicari di teks PDF itu. hal = urutan halaman di berkas PDF (mulai 1),
                      bukan nomor tercetak jurnal; boleh rentang 3-4. Mesin hanya MENUNJUK halaman, tidak pernah lolos:
                      ada di halaman itu = perhatian «ditemukan di halaman …» (cocokkan sendiri lafaz, angka, urutan);
                      ada di halaman lain, berkas tidak ada atau di luar folder bahts, halaman di luar PDF, atau bagian
                      kutipan < 6 huruf = GAGAL; tidak ada di teks PDF atau scan = perhatian. Nukilan makna (انظر) = perhatian
  <<w…|berkas|hal>>   kutipan dari kitab Waqfeya (scan + OCR, `waqfeya`, `ambil w…`; untuk kitab yang tidak ada di
                      Shamela). berkas = nomor urut berkas kitab (1, 2, …), hal = urutan halaman di berkas PDF (rentang
                      boleh); juz/halaman cetak ditulis di catatan kakinya. Lafaz TIDAK dinilai `cek` (OCR salah huruf):
                      pemeriksa membacanya di scan (`halaman w… <berkas> <hal>`, `bukti`). GAGAL hanya: kitab belum
                      diunduh, berkas/halaman tidak ada, bentuk rusak, atau kutipan (≥25 huruf) terbaca persis di
                      halaman lain tetapi tidak di halaman yang ditulis
  Tanda petik yang dikenali: "…" «…» “…” ‘…’ '…' ❝…❞ 〝…〞 ‟…” ❮…❯ ❛…❜. Perhatian: kutipan yang dipotong ... di
                      tengahnya atau disambung ... dengan kutipan lain, dan tanda petik tanpa pasangan
                      (…) tepat sebelum catatan kaki berbukti yang diantar «قال …:»، «ﷺ:», atau tepat sesudah {H:} = kutipan,
                      dicek seperti "…". Kutipan pendek (≤3 kata) yang diantar «قال …:» juga dicek; tanpa pengantar = istilah
  Judul (#K/#F/#B/#M/#S/#R) tidak boleh memuat [^, <<, {Q:/{H:/{A:/{N: atau ** ({A:} ditaruh di awal paragraf sesudahnya)
  Contoh: قال ابن القيم: "…"[^مدارج السالكين، ابن القيم، 2/15. <<8370|2|15>>]."""
TANDA_BERTAHAP = """Bahts dikumpulkan bertahap per فصل: tetap SATU naskah; tiap potongan dirakit dengan «rakit <folder> --fasl n» (#F ke-n;
                      rentang 1-2 = #F ke-1 dan ke-2). Yang sebelum #F pertama (المقدمة) ikut potongan pertama, yang
                      sesudah #F terakhir (الخاتمة) ikut potongan terakhir. Sampul hanya di potongan pertama; المصادر
                      dan الفهارس hanya di potongan terakhir (فهرس berisi isi potongan itu saja); nomor halaman tiap
                      potongan mulai ١. Hasil: «<@berkas> - المقدمة والفصل الأول.pdf» dst. dan laporan-fasl<n>.txt;
                      `cek` tetap memeriksa seluruh naskah. {P:kunci} yang menunjuk hadits atau {A:} di potongan lain =
                      berhenti sebelum Word: tulis takhrij lengkap, atau sebut bagiannya dengan kata, di catatan kaki itu"""
TANDA_RISET = """riset.txt (di folder bahts, di samping naskah.txt): jejak langkah riset yang tidak meninggalkan bukti di kitab lokal.
  takhrij8 <kunci>    `shamela_search_phrase` kategori 8 (التخريج والأطراف) sudah dijalankan untuk {H:…|kunci}
  tafsir <s:a>        tafsir ayat sudah dibaca lewat connector `tafsir` (boleh rentang s:a-b)
  khilaf <istilah>    `shamela_research_scope` sudah dijalankan untuk satu masalah khilaf; satu baris per masalah
                      (masalah = bagian berjudul yang barisnya diawali «القول الأول», «الرأي الأول», atau «المذهب الأول»)
  cari <istilah> | <catatan>   istilah kunci satu مبحث sudah dicari di connector `shamela` (`shamela_search_phrase`)
                      sebelum menulisnya; catatan (hasil, scope) boleh kosong. Tiap مبحث wajib punya paling sedikit
                      satu baris yang istilahnya tertulis di judul atau matan bagian itu, termasuk مطلب-nya (kata utuh;
                      boleh diawali و/ف/ب/ك/ل dan ال; catatan kaki dan «المبحث الأول:» di judul tidak dihitung).
                      مبحث = tiap #B kalau ada #F «الفصل…»/«فصل…», #B «المبحث…», atau tidak ada #F, ditambah #F tanpa
                      #B (mis. التمهيد); selain itu tiap #F. Tidak bisa dijalankan: «belum cari <istilah> | <alasan>»
  belum <langkah> <objek> <alasan>   langkah yang tidak bisa dijalankan; sebut di laporan akhir
  terima <kode> <alasan>   perhatian `cek` berkode itu («  ! 3f9a2c baris …») memang tidak bisa dibereskan, atau salah
                      tangkap; alasannya dinilai pemeriksa. Tiap perhatian wajib ditangani: dibereskan di naskah, atau
                      diterima begini (alasan paling sedikit 3 kata); selama ada yang belum, `tahap` tidak menganggap
                      naskah LOLOS dan `rakit` mencetak BELUM SELESAI. Kode tetap walau barisnya bergeser; isi baris
                      yang disebut berubah, atau baris baru ikut tergabung = kode baru. Perhatian riset.txt tidak bisa
                      diterima. «terima» yang basi, kembar, beralasan pendek, atau berkode rusak = perhatian
  Baris berawalan # = catatan. Tiap {H:}, ayat {Q:} (selain di bukti <<…>> dan di bawah #R), masalah khilaf, dan مبحث yang
                      belum tercatat = perhatian, juga baris riset.txt yang rusak atau kunci takhrij8 yang tidak ada di naskah.
                      Tidak pernah GAGAL: isinya ditulis agen sendiri, jadi mesin hanya menunjuk yang belum dicatat"""
TANDA = "\n\n".join((TANDA_NASKAH, TANDA_BERTAHAP, TANDA_RISET))

FORMAT = profil_format()  # huruf & ukuran tiap pedoman; dipilih dengan @format
# Kunci profil yang boleh tidak ditulis di format.json: nilai bawaannya, atau (IKUT_FORMAT) kunci lain yang nilainya dipakai.
# rakit.ps1 tidak punya bawaan sendiri: ia membaca profil yang sudah lengkap (format_cetak)
# garis_catatan = panjang garis pemisah catatan kaki (cm, di kanan); ukuran_kepala = teks kepala/kaki halaman,
# ukuran_nomor_kepala = nomor halaman tebal @kepala: klasik
BAWAAN_FORMAT = {"latin": 12, "spasi": 1, "mulakhas_berjarak": False, "jarak_paragraf": 0, "jarak_judul": 0, "tepi_kanan": 3.5,
                 "jarak_kepala": 1.25, "jarak_sebelum_sub": 6, "garis_catatan": 4.5}
IKUT_FORMAT = {"judul_sub": "judul", "ayat": "matan", "huruf_judul": "huruf", "spasi_mulakhas": "spasi", "ukuran_pustaka": "matan",
               "ukuran_kepala": "catatan", "ukuran_nomor_kepala": "matan"}
# @sampul: model sampul bahts -> data yang wajib. mahad = mesin/sampul.doc (معهد، كلية الشريعة);
# qism = mesin/sampul_qism.docx (قسم الشريعة: logo, judul besar, sub-judul dalam kurung kalau ada, العام الجامعي; jenis dan nim tercetak kalau diisi, fasl tidak)
# jakarta = mesin/sampul_jakarta.docx: model qism dengan «قسم الشريعة بجاكرتا», logo berwarna, baris @sifat di bawah nama,
# nomor mahasiswa tanpa «الرقم الجامعي:»; tengah = disusun rakit.ps1 tanpa templat: logo berwarna sampul_jakarta.docx di
# tengah atas (rasio gambarnya dijaga), lalu baris-baris rata tengah: LEMBAGA_TENGAH, @qism, judul, إعداد, إشراف, tahun
# kop = disusun rakit.ps1 tanpa templat dan tanpa logo/bingkai, semua tebal: kop bertingkat di kanan atas (KOP + @qism),
# judul besar, @jenis, إعداد + nama + nim, إشراف + musyrif, العام الجامعي; tanpa_kop = judul di atas, إعداد/إشراف di
# tengah halaman, KOP_BAWAH + @qism + tahun di bawah, semua tebal rata tengah. Baris tiap sampul susunan: _sampul_susun
SAMPUL = {"qism": ("judul", "nama"), "mahad": ("judul", "jenis", "nama", "nim", "fasl"), "jakarta": ("judul", "nama"),
          "tengah": ("judul", "nama", "qism"), "kop": ("judul", "nama"), "tanpa_kop": ("judul", "nama")}
LEMBAGA_TENGAH = "معهد العلوم الإسلامية والعربية في إندونيسيا"  # baris pertama sampul tengah (model خطة dosen المعهد)
QISM = "قسم الشريعة"  # qism sampul qism (kop gambar sampul_qism.docx); @qism menggantinya
KOP_BAWAH = ("جامعة الإمام محمد بن سعود الإسلامية", LEMBAGA_TENGAH)  # kop sampul qism tanpa baris negara
KOP = ("المملكة العربية السعودية", "وزارة التعليم", *KOP_BAWAH)
HALAMAN_BARU = ("B", "M")  # judul yang bisa dibuat mulai halaman baru lewat @halaman_baru; K dan F selalu
TANPA = ("ayat", "hadits", "atsar", *(f.kunci for f in FIHRIS_NAMA), "syir", "maudhuat", "pustaka")  # فهرس dan المصادر yang boleh dibuang lewat @tanpa (bagian_akhir)
# @tanpa yang bukan bagian: anzhur = «انظر:»/«ينظر:»/«راجع:» di catatan kaki tidak dicetak (dosen minta hasyiyah tanpa
# kata itu; dasar.TANPA_ANZHUR). Naskah tetap menulisnya: `cek` membedakan nukilan makna lewat kata itu
TANPA_CETAK = ("anzhur",)
MUQADDIMAH = "المقدمة"  # judul persis awal halaman isi: HALAMAN_ISI dihitung dari sini, dan @nomor: mukadimah mulai ١ di sini
# @angka: bawaannya hindi. Pedoman Jāmiʿat al-Imām tidak menyebut jenis angka; contoh resminya (pedoman 1443هـ,
# مجلة العلوم الشرعية) memakai hindi di nomor halaman, catatan kaki, rujukan, tahun, ayat, dan فهرس
ANGKA = ("hindi", "latin")
# Kunci naskah yang menimpa satu nilai profil @format (kombinasi permintaan dosen tanpa profil baru):
# @kunci -> (kunci di format.json yang dibaca rakit.ps1, {nilai di naskah: nilai di profil})
TIMPA = {"catatan_kaki": ("catatan_ulang_tiap_halaman", {"bersambung": False, "ulang": True}),
         "spasi": ("spasi", {"1": 1, "1.5": 1.5})}
# Bagian tata letak yang bisa dicampur: tiap kunci memilih bentuk satu bagian, nilai pertama = bawaan.
# kepala_judul = judul pendek di kepala halaman (bawaan @judul); sifat = baris di bawah nama di sampul
# kepala: bentuk tiap nilai ditulis di mesin/kepala.ps1 (kotak = mesin/kepala_kotak.docx)
GAYA = {"kepala": ("klasik", "-", "kotak", "bagian", "bagian_hias", "bintang", "bergantian", "kaki"),
        # terbuka = الآية | السورة | رقمها | الصفحة tanpa garis tegak, garis hanya di atas/bawah kepala dan di akhir; tabel =
        # kolom yang sama bergaris penuh; surah = kolom السورة (digabung per surat) | الآية «… الآية n» | الصفحة; titik =
        # tanpa tabel: judul tiap surat, lalu «﴿… n﴾ ...... ص» per ayat (n bermotif mushaf); baris_surah = الآية | رقمها |
        # الصفحة, tiap surat satu baris penuh «٢- سورة البقرة» di dalam tabel
        "fihris_ayat": ("terbuka", "tabel", "surah", "titik", "baris_surah"),
        # terbuka = طرف الحديث | الراوي | الصفحة bergaris seperti fihris_ayat terbuka; tabel = kolom yang sama bergaris penuh;
        # ringkas = الأحاديث | الصفحة, tanpa kolom الراوي; titik = فهرس أطراف الأحاديث النبوية tanpa tabel «طرف ...... ص»;
        # huruf = dikelompokkan «حرف الهمزة …», baris «طرف (الراوي) ...... ص»
        "fihris_hadits": ("terbuka", "tabel", "ringkas", "titik", "huruf"),
        "fihris_alam": ("nomor", "tabel"),  # nomor = tabel م | العلم | الصفحة berkepala abu-abu; tabel = العلم | الصفحة
        "maudhuat": ("titik", "tabel"),      # titik = baris bertitik-titik ke nomor halaman, tanpa tabel; #S «❖ …» ikut
        "maudhuat_letak": ("akhir", "awal"),  # awal = فهرس الموضوعات sesudah الإهداء/الشكر, tepat sebelum المقدمة (atau #F pertama)
        # judul_tebal = baris muallif dicetak «• **judul**. لفلان (ت: …). data» (pustaka_judul_dulu); judul = baris apa
        # adanya, bernomor; muallif = القرآن الكريم ikut bernomor; **…** tebal dan __…__ miring di #R
        "pustaka_gaya": ("judul_tebal", "judul", "muallif"),
        "judul_kanan": ("-", "B", "M", "B, M"),  # judul #B/#M rata kanan (bawaan: di tengah)
        "fihris": ("baru", "sambung"),  # sambung = المصادر/فهرس sesudah yang pertama menyambung di halaman yang sama
        "rujukan_ayat": ("catatan", "matan"),  # matan = [^سورة …، آية: n.] dicetak «[السورة: n]» tepat sesudah ayatnya
        "logo": ("-", "berwarna"),  # berwarna = sampul qism dengan logo berwarna dari sampul_jakarta.docx, sisanya tetap
        "judul_fasl": ("dua_baris", "-", "pemisah", "pemisah_bingkai", "kotak"),  # dua_baris = judul #F «الفصل الأول: المقدمة»
        # dicetak dua baris (judul_dua_baris); pemisah = halaman pemisah sendiri tanpa nomor (halaman_pemisah), _bingkai = di
        # dalam bingkai ganda bersudut bulat; kotak = judul #F di kotak bergaris ganda tebal-tipis, isi langsung menyusul
        "ihda": ("tengah", "-")}  # tengah = paragraf di bawah «#K الإهداء» rata tengah, tebal, berjarak (paragraf_ihda)
# Nilai yang menuntut tempatnya di naskah (dua_baris: #F bertitik dua; ihda tengah: «#K الإهداء»; judul_tebal: baris #R
# berbentuk muallif) hanya GAGAL kalau ditulis sendiri atau lewat @model (Pemeriksaan.gaya_ditulis). Sebagai bawaan,
# naskah tanpa tempat itu dicetak seperti biasa: #F tanpa titik dua satu baris, baris #R lain apa adanya berbutir «•»
# @model: satu nama untuk sekumpulan pilihan di atas (dan @sampul, @format, @pustaka, @catatan_kaki); kunci yang ditulis
# sendiri di naskah tetap menang, jadi model bisa dicampur, mis. «@model: jakarta» + «@sampul: qism»
MODEL = {"jakarta": {"sampul": "jakarta", "format": "jakarta", "kepala": "kotak", "fihris_ayat": "surah",
                     "fihris_hadits": "ringkas", "maudhuat": "titik", "pustaka_gaya": "muallif", "pustaka": "akhir",
                     "judul_kanan": "B, M", "catatan_kaki": "bersambung", "fihris": "sambung", "rujukan_ayat": "matan"}}
# Batas bawaan @minimal_*: 0 = tidak dinilai. Halaman = seluruh PDF (sampul s.d. فهرس), aturan pemakai; jumlah kitab
# hanya dinilai kalau dosen menulis batasnya (mis. «@minimal_kitab: 20»)
MINIMAL = {"halaman": 25, "kitab": 0}
# perkiraan kasar kata per halaman isi pada huruf matan 18; angka pasti hanya dari Word
KATA_PER_HALAMAN_18 = 260
KUAT = re.compile(r"[^\W\d_]|[،؛؟]")  # huruf, atau tanda baca Arab (tanda teks Arab)
# tautan/DOI di teks Arab: angkanya tetap 0-9 (hindi) dan rakit.ps1 mencetaknya kiri-ke-kanan apa adanya (bahan "tautan"),
# karena Word (angka konteks) mencetak «10.21608» di teks kanan-ke-kiri sebagai «١٠,٢١٦٠٨». Tanda baca penutup kalimat
# sesudahnya («….» «،» «)») dan kata Arab yang menempel («…/1234وانظر», huruf/harakat/tanda baca ؀-ۿ) bukan bagian
# tautan. Pola ini juga dipakai .NET (rakit.ps1): jangan pakai sintaks khusus Python
HURUF_TAUTAN = r"[^\s؀-ۿ«»()\[\]]"
TAUTAN = re.compile(rf"(?:https?://|www\.|doi\.org/|(?<![\w.])10\.[0-9]{{4,}}/)(?:{HURUF_TAUTAN}|\({HURUF_TAUTAN}*\))+(?<![.,:])")
# rentang berhuruf Latin di teks Arab (bahan "latin"): rakit.ps1 mencetaknya Times New Roman dengan ukuran sebanding.
# Tautan/DOI utuh; selain itu mulai di huruf Latin (atau angka yang menempel di depannya: «3G») dan berakhir di huruf
# Latin, angka, «%», atau kurung (biasa/siku) yang dibuka di dalam rentang itu («Islamic Banking (IB)»). Spasi dan tanda
# baca di antaranya ikut; yang di ujungnya («(», «.», «،») milik kalimat Arabnya, kecuali tanda petik yang menempel di
# hurufnya: pembuka di depan («“Essay») dan penutup/apostrof di belakang («Coppens’», «Essay”»). Tanda yang lepas dari
# rentangnya ditata Word kanan-ke-kiri: di catatan kaki rentang Latin dipecah, potongannya tertukar («Société … al-…»),
# dan tanda petik pindah ke sisi lain. Dipakai .NET juga: jangan pakai sintaks khusus Python
_L = HURUF_LATIN + "ʾʿʼ"  # ʿayn dan hamzah transliterasi
_TENGAH = r" ,.;:&'’‘“”\"/%–—…!_=?#~@+-"
# di ujung hanya petik tipografis: petik lurus «"»/«'» di tepi bisa milik kutipan Arab («قال: "IFRS 9 هو…"»)
_PETIK_BUKA, _PETIK_TUTUP = "“‘", "”’"
LATIN = re.compile(rf"{TAUTAN.pattern}|[{_PETIK_BUKA}]*(?:(?<![0-9])[0-9]+(?=[{_L}]))?[{_L}]"
                   rf"(?:[{_TENGAH}]*(?:[{_L}0-9%]|\([{_L}0-9{_TENGAH}]*\)|\[[{_L}0-9{_TENGAH}]*\]))*[{_PETIK_TUTUP}]*")


def galat_mesin(e):
    return f"GALAT MESIN ({type(e).__name__}: {e}) — bukan salah naskah; laporkan barisnya ke pengurus mesin bahts"


def hindi(s):
    """Angka 0-9 -> ٠-٩, kecuali angka yang huruf atau tanda baca Arab terdekat sebelumnya (atau sesudahnya, kalau tidak
    ada) huruf Latin: judul berbahasa Latin tetap 0-9; «مجلة X، 2020» tetap ٢٠٢٠. Angka di dalam tautan/DOI (TAUTAN) selalu
    0-9, juga DOI tanpa huruf di depannya («انظر: 10.1016/…»). Satu lintasan linear."""
    keluar, pos, terakhir = [], 0, ""
    tautan = iter([t.span() for t in TAUTAN.finditer(s)] + [(len(s) + 1, len(s) + 1)])
    t = next(tautan)
    for m in re.finditer(r"[0-9]+", s):
        while t[1] <= m.start():
            t = next(tautan)
        keluar.append(s[pos:m.start()])
        for k in KUAT.finditer(s, pos, m.start()):
            terakhir = k.group()
        k = next(KUAT.finditer(s, m.end()), None)
        c = terakhir or (k.group() if k else "")
        latin = t[0] <= m.start() or re.match(f"[{HURUF_LATIN}]", c)
        keluar.append(m.group() if latin else m.group().translate(AD))
        pos = m.end()
    keluar.append(s[pos:])
    return "".join(keluar)


GABUNG_PARUH = re.compile(r"\s*\.\.\.~\s*")  # «...~» di #V: dua paruh bait berbagi satu kata, disambung sebelum dicek dan dicetak
BUKTI_SID = re.compile(r"<<(\d+)\|")
BUKTI_WAQFEYA = re.compile(r"<<(w[0-9a-f]{8})\|")


def kitab_dirujuk(folder):
    """(Nomor kitab Shamela, nomor kitab Waqfeya) dari satu pembacaan naskah, urut kemunculan pertama.
    Dipakai `ambil <folder>` untuk mengunduh kedua jenis sumber."""
    teks = (Path(folder) / "naskah.txt").read_text(encoding="utf-8-sig")
    return tuple(list(dict.fromkeys(pola.findall(teks))) for pola in (BUKTI_SID, BUKTI_WAQFEYA))


AWAL_BAGIAN = re.compile(rf"^(?:\*\*)?(?:#[{''.join(TINGKAT_JUDUL)}](?![^\s])|القول|الرأي|المذهب)")


def kata(runs):
    """Jumlah kata Arab di runs naskah (untuk perkiraan jumlah halaman)."""
    return sum(len(re.findall(r"[؀-ۿ]+", r.get("t") or "")) for r in runs)


def sumber_tertimpa(folder, berkas, sumber, laporan=produk.LAPORAN):
    """Nama bahan pemakai yang bertabrakan dengan nama hasil akhir, juga sesudah `potong` mengganti @berkas."""
    tujuan = {(folder / nama).resolve().as_posix().casefold()
              for nama in (produk.docx(berkas), produk.pdf(berkas), produk.khulasah(berkas), laporan)}
    return [nama for nama in dict.fromkeys(sumber)
            if (folder / nama.strip()).resolve().as_posix().casefold() in tujuan]


def potong(d, fasl):
    """`rakit <folder> --fasl n` (atau a-b): bahan rakit `d` (hasil utama, seluruh naskah sudah dicek) dipangkas jadi
    #F ke-n saja, untuk dosen yang meminta bahts dikumpulkan bertahap per فصل. Bentuknya mengikuti potongan yang dulu
    diterima dosen (tiap potongan dulu naskah sendiri): sampul hanya di potongan yang memuat #F pertama (bersama yang
    sebelumnya, mis. المقدمة); المصادر dan الفهارس hanya di potongan yang memuat #F terakhir (bersama yang sesudahnya,
    mis. الخاتمة), dan فهرسnya hanya berisi isi potongan itu; nomor halaman tiap potongan mulai ١.
    Kembalikan label potongan (mis. «المقدمة والفصل الأول»), yang juga ditambahkan ke nama berkas hasil."""
    dari, sampai = produk.rentang_fasl(fasl)
    blok = d["blok"]
    awal_f = [i for i, b in enumerate(blok) if b["k"] == "F"]
    if sampai > len(awal_f):
        raise TandaRusak(f"--fasl {fasl}: naskah ini hanya punya {len(awal_f)} #F")
    mulai = 0 if dari == 1 else awal_f[dari - 1]
    akhir = len(blok) if sampai == len(awal_f) else awal_f[sampai]
    d["blok"] = blok = blok[mulai:akhir]
    meta = d["meta"]
    label = [b["judul"].split(":")[0].strip() for b in blok if b["k"] in JUDUL_BAB]
    label = label[0] + "".join(" و" + x for x in label[1:])
    meta["berkas"] = produk.nama_potongan(meta["berkas"], label, fasl)
    if dari > 1:  # sampul dan halaman bernomor huruf (@nomor) hanya di potongan pertama
        meta["tanpa_sampul"] = True
        meta.pop("nomor", None)
    if sampai < len(awal_f):  # المصادر, الفهارس, dan halaman penutup (@tamma) hanya di potongan terakhir
        meta["tanpa"] = ", ".join(TANPA)
        meta.pop("tamma", None)

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
    d["syir"] = [v for v in d["syir"] if v["k"] in bm]
    for jenis in ("hadits", "atsar"):
        hadits = []
        for h in d[jenis]:
            ks = [k for k in [h["k"], *h.get("lagi", [])] if k in bm]
            if ks:  # {H:} di potongan lain, {H2:} di sini: halaman di فهرس hanya yang di sini
                hadits.append({**h, "k": ks[0], "lagi": ks[1:]})
        d[jenis] = hadits
    for f in FIHRIS_NAMA:  # nama yang juga disebut di potongan lain: halaman di فهرس hanya yang di sini
        d[f.kunci] = [{**a, "k": ks} for a in d[f.kunci] if (ks := [k for k in a["k"] if k in bm])]
    d["cetak"] = rencana_cetak(d)
    return label


@dataclasses.dataclass
class HasilCek:
    """Hasil `periksa` atas satu naskah. Tidak ada yang ditulis ke berkas: bahan ditulis `tulis_bahan`, laporan dicetak
    `cetak` atau ditulis `rakit`."""
    ctx: Pemeriksaan  # putusan (galat, perhatian, diterima, tertolak) dan isi naskah yang terurai
    bahan: dict  # bahan rakit (_bahan)
    laporan: list  # baris laporan `cek`
    sidik_naskah: str  # SHA-256 naskah.txt
    sidik_cetak: str  # SHA-256 bagian bahan yang tercetak (sidik_cetak)
    tanpa_bukti: list  # awal teks tiap catatan kaki tanpa bukti (_tanpa_bukti)


def periksa(folder):
    """Urai dan periksa naskah di `folder`. Kembalikan HasilCek.
    Tahapannya urut; urutan itu juga urutan galat dan perhatian di laporan."""
    folder = Path(folder)
    naskah, baris = _baca_naskah(folder)
    ctx = Pemeriksaan(folder=folder, meta={"berkas": folder.name})
    _urai_baris(ctx, baris)
    _cek_sesudah_naskah(ctx)
    _terapkan_model_gaya(ctx)
    _cek_bentuk(ctx)
    _cek_minimal_rusak(ctx)
    quran = _urutkan_fihris(ctx)
    _cek_jumlah_kitab(ctx, quran)
    _cek_kitab_pustaka(ctx)
    n_matan, n_fn = _hitung_kata(ctx)
    _cek_sampul(ctx)
    sumber = _cek_bahan_sumber(ctx, naskah)
    _cek_tata_letak(ctx)
    _malahiq(ctx)
    profil = _profil(ctx)
    _render_rumus(ctx, profil)
    _angka_cetak(ctx)
    sidik_naskah = hashlib.sha256(naskah).hexdigest()
    d = _bahan(ctx, _bait_syair(ctx.blok), profil, quran, sumber, sidik_naskah)
    _cek_jumlah_halaman(ctx, d)
    # jumlah di ringkasan = baris yang dicetak; yang diterima di riset.txt tidak dihitung (laporannya terpisah)
    ctx.perhatian, ctx.diterima, ctx.kode = periksa_riset(folder, baris, gabung_kembar(ctx.perhatian))
    sidik_isi = sidik_cetak(d)
    tanpa_bukti = _tanpa_bukti(ctx)
    return HasilCek(ctx, d, _laporan(ctx, n_matan, n_fn, tanpa_bukti, sidik_naskah, sidik_isi), sidik_naskah, sidik_isi,
                    tanpa_bukti)


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


GAMBAR = (".png", ".jpg", ".jpeg")  # yang dimasukkan Word apa adanya; SVG di-PNG-kan dulu (diagram.py)


PNG_AKHIR = b"\x00\x00\x00\x00IEND\xaeB`\x82"  # potongan IEND: penutup tiap PNG utuh


def ukuran_gambar(p):
    """(lebar, tinggi) piksel PNG/JPEG dari kepala berkasnya; None kalau bukan gambar yang terbaca, berdimensi nol,
    atau terpotong (PNG tanpa potongan IEND, JPEG tanpa penanda akhir FFD9 sesudah kepalanya). Tanpa pustaka gambar:
    putusan `cek` sama di semua komputer, dan Word gagal di gambar terpotong dengan pesan yang tidak menunjuk berkasnya."""
    data = p.read_bytes()
    ukuran = None
    # byte sesudah IEND (sisa penyunting gambar) tetap PNG utuh: IEND + CRC-nya cukup ada sesudah IHDR
    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR" and PNG_AKHIR in data[33:]:
        ukuran = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    elif data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) and data[i] == 0xFF:
            while i < len(data) and data[i] == 0xFF:  # ITU-T T.81: byte pengisi 0xFF boleh berderet sebelum penanda
                i += 1
            if i >= len(data):
                break
            tanda = data[i]
            if tanda in (0x00, 0xD9):
                break
            if tanda == 0x01 or 0xD0 <= tanda <= 0xD8:  # penanda berdiri sendiri tanpa panjang
                i += 1
                continue
            if i + 3 > len(data):
                break
            panjang = int.from_bytes(data[i + 1:i + 3], "big")
            if panjang < 2 or i + 1 + panjang > len(data):
                break
            if 0xC0 <= tanda <= 0xCF and tanda not in (0xC4, 0xC8, 0xCC):  # SOFn: panjang(2) + presisi(1) + tinggi(2) + lebar(2)
                if panjang >= 7 and data.rfind(b"\xff\xd9") >= i + 1 + panjang:
                    ukuran = int.from_bytes(data[i + 6:i + 8], "big"), int.from_bytes(data[i + 4:i + 6], "big")
                break
            i += 1 + panjang
    return ukuran if ukuran and all(ukuran) else None


def _baris_gambar(ctx, n, k, t):
    """«#G berkas | keterangan»: gambar dari folder bahts. Isi berkasnya ikut sidik cetak (PNG baru = PDF usang)."""
    berkas, _, ket = t.partition("|")
    berkas, ket = berkas.strip(), ket.strip()
    folder = ctx.folder.resolve()
    p = (folder / berkas).resolve()
    salah = None
    if p.suffix.lower() not in GAMBAR:
        salah = f"«{berkas}» bukan PNG/JPG" + ("; diagram Mermaid dijadikan PNG dulu: python mesin/bahts.py diagram "
                                              f"<folder>, lalu «#G {p.stem}.png | …»" if p.suffix.lower() == ".mmd" else "")
    elif not p.is_relative_to(folder):
        salah = f"«{berkas}» di luar folder {folder.name}: salin gambarnya ke sana, lalu tulis namanya saja"
    elif not p.is_file():
        salah = f"«{berkas}» tidak ada di folder {folder.name}" + (
            f"; ada {p.stem}.mmd: jalankan python mesin/bahts.py diagram <folder>" if p.with_suffix(".mmd").is_file() else "")
    elif not (ukuran := ukuran_gambar(p)):
        salah = f"«{berkas}» bukan PNG/JPG yang terbaca (berkas rusak, atau isinya format lain)"
    elif re.search(r"\[\^|<<|\{", ket):
        salah = "keterangan gambar tidak boleh memuat catatan kaki, bukti, atau tanda {Q:/{H:/{E: — tulis rujukannya di paragraf sesudahnya"
    if salah:  # barisnya tetap isi bagian itu (bukan «bagian kosong»); GAGAL menghentikan rakit
        ctx.galat.append(f"#G {salah}")
        ctx.blok.append({"k": "P", "runs": [], "n": n})
        return
    w, h = ukuran
    ctx.blok.append({"k": "G", "berkas": str(p), "rasio": h / w, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                     "runs": [{"t": ket}] if ket else [], "n": n})


def _pisah_sel(t):
    """Pecah baris #J pada « | » di luar {E:…} dan catatan kaki [^…] (supaya P(A | B) atau bukti ber-«|» tidak membelah sel)."""
    sel, awal, i, n = [], 0, 0, len(t)
    while i < n:
        if t.startswith("{E:", i):
            i = akhir_rumus(t, i + 3) + 1
            continue
        if t.startswith("[^", i):
            i = akhir_catatan(t, i + 2) + 1
            continue
        if t.startswith(" | ", i):
            sel.append(t[awal:i].strip())
            i += 3
            awal = i
            continue
        i += 1
    sel.append(t[awal:].strip())
    return sel


def _baris_tabel(ctx, n, k, t):
    """«#J sel | sel»: tiap sel diurai seperti paragraf (catatan kaki dan kutipannya dicek per sel). Baris #J sesudah
    baris #J (tanpa judul atau paragraf di antaranya) = tabel yang sama, jadi jumlah selnya harus sama."""
    try:
        sel = _pisah_sel(t)
    except TandaRusak as e:
        ctx.galat.append(f"{e} :: #J {t[:40]}")
        return
    if len(sel) < 2 or not all(sel):
        ctx.galat.append(f"#J butuh paling sedikit dua sel berisi, dipisah « | » :: #J {t[:40]}")
        return
    sebelum = ctx.blok[-1] if ctx.blok else None
    if sebelum and sebelum["k"] == "J" and len(sebelum["sel"]) != len(sel):
        ctx.galat.append(f"tabel ini {len(sebelum['sel'])} kolom (baris {sebelum['n']}), "
                         f"baris ini {len(sel)} sel :: #J {t[:40]}")
        return
    isi = []
    for s in sel:
        runs = _urai_aman(ctx, s)
        if runs is None:
            return
        isi.append(runs)
    # runs = gabungan semua sel (untuk perkiraan halaman dan penghitung lain); rakit.ps1 memakai sel
    ctx.blok.append({"k": "J", "sel": isi, "runs": [r for s in isi for r in (*s, {"t": " "})], "n": n})


def _baris_latin(ctx, n, k, t):
    """«#L teks»: tercetak apa adanya, kiri ke kanan; tanda naskah tidak diurai."""
    blok, galat, b = ctx.blok, ctx.galat, f"#{k} {t}"
    if re.search(r"\[\^|<<|\{", t):
        galat.append(f"#L tidak boleh memuat catatan kaki, bukti, atau tanda {{Q:/{{H:/{{E: :: {b[:40]}")
    m = re.fullmatch(r"\*\*([^*]+)\*\*", t.strip())  # «#L **Abstract**»: judul Latin tebal di tengah
    if m and not m[1].strip():
        galat.append(f"judul #L **…** kosong :: {b[:40]}")
    if m and blok and blok[-1]["k"] not in (*JUDUL_FIHRIS, "H"):  # judul Latin sesudah isi: halaman sendiri
        blok.append({"k": "H", "runs": [], "n": n})
    blok.append({"k": "L", "runs": [{"t": m[1].strip() if m else t}], "n": n, **({"tengah": True} if m else {})})


def _baris_bait(ctx, n, k, t):
    """«#V teks» (bait syair): paragraf biasa (boleh bercatatan kaki); kata yang dipecah «...~» dicek dan dicetak utuh,
    bukan sebagai dua bagian kutipan."""
    v0 = len(ctx.syir_idx)
    ctx.bait = True
    try:
        runs = _urai_aman(ctx, GABUNG_PARUH.sub("", t))
    finally:
        ctx.bait = False
    if runs is not None:
        ctx.blok.append({"k": k, "runs": runs, "n": n})
        for v in ctx.syir_idx[v0:]:  # {V:القائل}: صدر البيت dan القافية dari bait pertama baris ini
            v["t"], v["qf"] = _bait_fihris(t)
    else:
        del ctx.syir_idx[v0:]


def _matan_bait(t):
    """Teks baris #V seperti dibaca: tanpa catatan kaki [^…], tanda {…}, **, dan tanda petik."""
    out, i = [], 0
    while (j := t.find("[^", i)) >= 0:
        out.append(t[i:j])
        i = akhir_catatan(t, j + 2) + 1
    return re.sub(r'\{[^{}]*\}|\*\*|["«»“”]', "", "".join(out) + t[i:])


def _bait_fihris(t):
    """(صدر البيت, القافية) bait pertama baris #V `t` untuk فهرس الأشعار: صدر = paruh sebelum « ... » (atau « ...~ »),
    القافية = kata terakhir paruh terakhirnya (عجز), tanpa tanda baca di ujungnya. Bait satu paruh: صدر = seluruhnya."""
    bait = re.split(r"\s*//\s*", _matan_bait(t))[0]
    paruh = [x.strip() for x in re.split(r"\s*\.\.\.~?\s*", bait) if x.strip()]
    kata_ = paruh[-1].split() if paruh else []
    return (paruh[0] if paruh else ""), (re.sub(r"[^\w\u064b-\u065f\u0670]+$", "", kata_[-1]) if kata_ else "")


# Urutan حرف الروي di فهرس الأشعار: hamzah dulu, alif (maqsurah) terakhir
RAWI = "ءبتثجحخدذرزسشصضطظعغفقكلمنهويا"
RAWI_SAMA = str.maketrans("أإآؤئىة", "ءءءءءات")


def _rawi(qafiyah):
    """حرف الروي القافية: huruf terakhirnya tanpa harakat; «ا» penutup kata lebih dari dua huruf = ألف الإطلاق, jadi huruf
    sebelumnya («سُلَّمَا» → م); ة dihitung ت, ى dan alif lain sebagai alif."""
    w = norma.HARAKAT.sub("", qafiyah)
    if len(w) > 2 and w.endswith("ا"):
        w = w[:-1]
    return w[-1:].translate(RAWI_SAMA)


def _baris_judul(ctx, n, k, t):
    """«#K/#F/#B/#M/#S/#R teks»: judul, tercetak apa adanya (juga di فهرس الموضوعات), jadi tanda naskah ikut tercetak."""
    if re.search(r"\[\^|<<|\{|\*\*", t):
        ctx.galat.append(f"judul tidak boleh memuat catatan kaki [^, bukti <<, tanda {{Q:/{{H:/{{A:/{{N:/{{E: atau **: "
                         f"pindahkan ke paragraf sesudahnya :: {f'#{k} {t}'[:40]}")
        return
    if k == "R":
        ctx.di_baris["#R"] = n
    ctx.blok.append({"k": k, "runs": [{"t": t, "b": True}], "judul": t, "n": n})


def _baris_rumus(ctx, n, k, t):
    """«#E latex»: persamaan matematika baris sendiri (OMML Word asli), opsional \\tag{…} untuk nomor persamaan."""
    latex = t.strip()
    try:
        omml, tag = rumus.konversi(latex, display=True)
    except TandaRusak as e:
        ctx.galat.append(f"#E {e}")
        ctx.blok.append({"k": "P", "runs": [], "n": n})
        return
    ctx.blok.append({"k": "E", "latex": latex, "omml": omml, "runs": [], "n": n, **({"tag": tag} if tag else {})})


# Tanda baris «#X teks» -> penangannya (ctx, nomor baris, X, teks). Tanda baris baru = penangan baru di sini
TANDA_BARIS = {**dict.fromkeys((*JUDUL_ISI, "R"), _baris_judul), "V": _baris_bait, "L": _baris_latin,
               "J": _baris_tabel, "G": _baris_gambar, "E": _baris_rumus}


def _urai_aman(ctx, teks):
    """Runs `teks` (naskah.urai), atau None kalau barisnya tidak terurai: galatnya dicatat di sini."""
    try:
        return urai(teks, ctx)
    except TandaRusak as e:
        ctx.galat.append(f"tanda rusak — {e}")
    except (KeyError, IndexError, ValueError) as e:  # bukan salah tulis naskah: mesinnya yang keliru di baris ini
        ctx.galat.append(galat_mesin(e))
    return None


def _urai_baris(ctx, baris):
    """Tiap baris naskah diurai (`_satu_baris`); tiap galat dan perhatiannya menyebut nomor barisnya
    (Pemeriksaan.selama_baris): pemakai langsung tahu tempatnya, tes jebakan mencocokkan per baris."""
    for n, b in baris:
        if AWAL_BAGIAN.match(norma.HARAKAT.sub("", b)) and ctx.standar:
            ctx.perhatian += standar_baris(ctx.standar); ctx.standar.clear()
        with ctx.selama_baris(n):
            _satu_baris(ctx, n, b)


def _satu_baris(ctx, n, b):
    """Satu baris naskah: @data, tanda baris #… (TANDA_BARIS), rujukan sesudah #R, atau paragraf."""
    di_baris, blok, pustaka, galat, perhatian = ctx.di_baris, ctx.blok, ctx.pustaka, ctx.galat, ctx.perhatian
    if b.startswith("@"):
        _baca_data(ctx, n, b)
    elif "#R" in di_baris and b.startswith("#"):
        galat.append(f"{b.split()[0]} sesudah #R di baris {di_baris['#R']} tidak dirakit: "
                     "pindahkan bagian isi sebelum #R; sesudah #R hanya satu rujukan per baris")
    elif b.strip() == "#H":  # pindah halaman: blok sesudahnya mulai halaman baru (awal_halaman)
        blok.append({"k": "H", "runs": [], "n": n})
    elif b.startswith("#"):
        k, _, t = b[1:].partition(" ")
        t = t.strip()
        if "#" + k in DICABUT:
            galat.append(f"#{k} dicabut: {DICABUT['#' + k]}")
        elif k not in TANDA_BARIS or not t:
            galat.append(f"judul harus «{'/'.join('#' + x for x in TANDA_BARIS)} teks» :: {b[:40]}")
        else:
            TANDA_BARIS[k](ctx, n, k, t)
    elif "#R" in di_baris:
        teks_r = b.strip()
        pustaka.append(teks_r)
        ctx.pustaka_baris.append((n, teks_r))
        g = gelar(b, "pustaka")
        if g:
            perhatian.append(g)
    else:
        runs = _urai_aman(ctx, b)
        if runs is not None:
            blok.append({"k": "P", "runs": runs, "n": n})


def _baca_data(ctx, n, b):
    """Baris «@kunci: nilai» (baris ke-n): simpan di meta; nilainya dicek sesudah seluruh naskah dibaca. @kunci yang
    dicabut (dasar.DICABUT) GAGAL dengan jalan keluarnya."""
    k, _, v = b[1:].partition(":")
    k = k.strip()
    if "@" + k in DICABUT:
        ctx.galat.append(f"@{k} dicabut: {DICABUT['@' + k]}")
    elif k not in DATA:
        mirip = difflib.get_close_matches(k, sorted(DATA), n=1)
        ctx.galat.append(f"@{k}: data tidak dikenal" +
                         (f"; maksudnya @{mirip[0]}?" if mirip else "; lihat `tanda` untuk daftar data naskah"))
    ctx.meta[k] = v.strip()
    ctx.di_baris["@" + k] = n


@dataclasses.dataclass(frozen=True)
class Data:
    """Sifat satu @kunci naskah (tabel DATA)."""
    sah: tuple = ()  # nilai yang dikenal (`_pilih`); kosong = teks bebas, atau bentuknya dinilai tahapan `periksa` sendiri
    bawaan: str | None = None  # nilai kalau barisnya tidak ditulis
    pisah: str = ", "  # pemisah nilai sah di kalimat GAGAL
    pesan: str = "«{nilai}» tidak dikenal (yang ada: {ada})"  # kalimat GAGAL nilai di luar `sah`
    baca: Callable = str  # nilai seperti ditulis -> bentuk yang dicocokkan dengan `sah`
    teks: bool = False  # teks yang tercetak apa adanya: angkanya mengikuti @angka
    hanya_cek: bool = False  # tidak dibaca rakit.ps1: mengubahnya tidak membuat PDF usang (sidik_cetak)


TEKS = Data(teks=True)
YA_TIDAK = Data(sah=("ya",), pesan="«{nilai}» tidak dikenal: tulis «ya», atau hapus barisnya")  # tanpa barisnya = tidak
# Tiap @kunci yang dikenal naskah. Kunci berpilihan dinilai `_pilih` di tahapan `periksa` yang memakainya: urutan
# tahapan itu = urutan GAGAL di laporan
DATA = {
    "judul": TEKS, "jenis": TEKS, "nama": TEKS, "nim": TEKS, "fasl": TEKS, "musyrif": TEKS, "jabatan": TEKS,
    "thalibah": YA_TIDAK,
    "basmalah": Data(sah=("ya", "utsmani"), pesan="«{nilai}» tidak dikenal: tulis «ya» atau «utsmani», atau hapus barisnya"),
    "tamma": YA_TIDAK,
    "sampul": Data(sah=tuple(SAMPUL), bawaan="qism", pisah="، ", baca=str.lower),
    "tahun": TEKS, "berkas": Data(), "ayat_pembuka": Data(),
    "format": Data(sah=tuple(FORMAT), bawaan="imam", pisah="، ",
                   pesan="«{nilai}» tidak ada di mesin/format.json (yang ada: {ada})"),
    "angka": Data(sah=ANGKA, bawaan="hindi", pisah="، "), "angka_ayat": Data(sah=ANGKA, pisah="، "),  # bawaan = @angka
    "tanpa": Data(sah=TANPA), "pustaka": Data(sah=("akhir",)), "malahiq": Data(sah=("akhir",)), "templat": Data(),
    "halaman_baru": Data(sah=HALAMAN_BARU), "nomor": Data(sah=("abjad", "mukadimah")),
    "model": Data(sah=tuple(MODEL), pisah="، "), "kepala_judul": TEKS, "sifat": TEKS, "qism": TEKS, "judul_sampul": TEKS,
    **{f"minimal_{k}": Data(hanya_cek=True) for k in MINIMAL},
    **{k: Data(sah=tuple(nilai)) for k, (_, nilai) in TIMPA.items()},
    **{k: Data(sah=nilai, bawaan=nilai[0]) for k, nilai in GAYA.items()},
}
HANYA_CEK = frozenset(k for k, sifat in DATA.items() if sifat.hanya_cek)


def _tak_dikenal(ctx, kunci, nilai):
    """GAGAL: `nilai` @kunci bukan salah satu nilai sahnya (DATA)."""
    sifat = DATA[kunci]
    ctx.galat.append(ctx.di("@" + kunci) + f"@{kunci}: " + sifat.pesan.format(nilai=nilai, ada=sifat.pisah.join(sifat.sah)))


def _pilih(ctx, kunci):
    """Nilai @kunci berpilihan: yang ditulis di naskah kalau dikenal, bawaannya kalau barisnya tidak ada.
    None = tidak dikenal (sudah dicatat GAGAL), atau tidak ditulis dan tanpa bawaan."""
    sifat = DATA[kunci]
    if kunci not in ctx.meta:
        return sifat.bawaan
    nilai = sifat.baca(ctx.meta[kunci])
    if nilai in sifat.sah:
        return nilai
    _tak_dikenal(ctx, kunci, nilai)
    return None


def _cek_sesudah_naskah(ctx):
    """Yang baru bisa dinilai sesudah semua baris dibaca: standar sumber bagian terakhir,
    porsi kutipan, الدراسات السابقة, dan {P:} yang menunjuk {A:}/{H:}."""
    blok, catatan, hadits_idx, galat = ctx.blok, ctx.catatan, ctx.hadits_idx, ctx.galat
    perhatian = ctx.perhatian
    perhatian += standar_baris(ctx.standar); ctx.standar.clear()
    perhatian += porsi_kutipan(blok, catatan)
    perhatian += periksa_dirasat(blok, catatan)
    perhatian += periksa_muqaddimah(blok, ctx.meta.get("jenis", ""))
    perhatian += periksa_khatimah(blok)
    for r in ctx.rujuk_silang:
        if r["k"] not in ctx.jangkar:
            dulu = any(h["k"] == "h_" + r["k"] for h in hadits_idx)
            galat.append(f"baris {r['n']}: {{P:{r['k']}}}: " + (
                f"{{H:…|{r['k']}}} baru ditulis sesudah catatan kaki ini; «سبق تخريجه» menunjuk hadits yang sudah ditakhrij"
                if dulu else f"tidak ada {{A:{r['k']}}} atau {{H:…|{r['k']}}} di naskah"))


IHDA = re.compile(r"(ال)?[إا]هداء")  # judul #K bagian الإهداء (@ihda), tanpa harakat


def judul_dua_baris(blok):
    """@judul_fasl: dua_baris -> {indeks blok #F: [sebelum, sesudah titik dua pertama]}; فهرس tetap satu baris."""
    dua = {}
    for i, b in enumerate(blok):
        if b["k"] == "F":
            a, titik, c = b["judul"].partition(":")
            if titik and a.strip() and c.strip():
                dua[str(i)] = [a.strip(), c.strip()]  # kunci teks: bahan JSON
    return dua


JUDUL_FASL_PEMISAH = ("pemisah", "pemisah_bingkai")  # @judul_fasl yang mencetak halaman pemisah (halaman_pemisah)
# kata judul sub-bagian -> (tunggal, mutsanna, jamak, tamyiz 11-99, muannats): «وفيه مطلبان»، «وفيه ثلاثة مطالب»
KATA_BAGIAN = {"فصل": ("فصل", "فصلان", "فصول", "فصلا", False), "مبحث": ("مبحث", "مبحثان", "مباحث", "مبحثا", False),
               "مطلب": ("مطلب", "مطلبان", "مطالب", "مطلبا", False), "فرع": ("فرع", "فرعان", "فروع", "فرعا", False),
               "مسألة": ("مسألة", "مسألتان", "مسائل", "مسألة", True)}
# bilangan 3-10 berlawanan jenis dengan ma'dudnya: mudzakkar (مطلب) -> ثلاثة، muannats (مسألة) -> ثلاث
SATUAN = {False: ("ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة", "عشرة"),
          True: ("ثلاث", "أربع", "خمس", "ست", "سبع", "ثماني", "تسع", "عشر")}
PULUHAN = ("عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون")


def kata_jumlah(n, kata):
    """«مطلب واحد»، «مطلبان»، «ثلاثة مطالب»، «أحد عشر مطلبا»، «واحد وعشرون مطلبا»: n sub-bagian berkata judul `kata`
    (KATA_BAGIAN): bilangan 3-10 berlawanan jenis, tamyiz 11-99 tunggal manshub."""
    tunggal, dua, jamak, tamyiz, muannats = KATA_BAGIAN[kata]
    satuan = SATUAN[muannats]
    satu, dua_angka = ("واحدة", "اثنتان") if muannats else ("واحد", "اثنان")
    if n == 1:
        return f"{tunggal} {satu}"
    if n == 2:
        return dua
    if n <= 10:
        return f"{satuan[n - 3]} {jamak}"
    if n <= 19:
        awal = {11: "إحدى" if muannats else "أحد", 12: "اثنتا" if muannats else "اثنا"}.get(n) or satuan[n - 13]
        return f"{awal} {'عشرة' if muannats else 'عشر'} {tamyiz}"
    if n <= 99:
        sat = n % 10
        depan = "" if not sat else (satu if sat == 1 else dua_angka if sat == 2 else satuan[sat - 3]) + " و"
        return f"{depan}{PULUHAN[n // 10 - 2]} {tamyiz}"
    return f"{n} {jamak}"


def _kata_judul(judul):
    """Kata bagian di awal judul («المبحث الأول: …» -> «مبحث»), atau None."""
    awal = norma.HARAKAT.sub("", judul).split(maxsplit=1)[:1]
    kata = awal[0].removeprefix("ال") if awal else ""
    return kata if kata in KATA_BAGIAN else None


def halaman_pemisah(blok):
    """@judul_fasl: pemisah/pemisah_bingkai -> {indeks blok #F: {judul: [baris besar, baris kedua], pengantar: «وفيه
    مطلبان:», anak: [judul #B di bawahnya]}}. Kata bagiannya dari judul #B-nya (kalau semuanya sama), lalu dari judul
    #F (فصل -> مبحث، مبحث -> مطلب، باب -> فصل); tidak dikenal -> «وفيه:». Tanpa #B: hanya judulnya."""
    hasil = {}
    for i, b in enumerate(blok):
        if b["k"] != "F":
            continue
        anak = []
        for c in blok[i + 1:]:
            if c["k"] in ("K", "F", "R"):
                break
            if c["k"] == "B":
                anak.append(c["judul"])
        a, titik, c = b["judul"].partition(":")
        isi = {"judul": [a.strip(), c.strip()] if titik and a.strip() and c.strip() else [b["judul"], ""], "anak": anak,
               "pengantar": ""}
        if anak:
            kata_anak = {_kata_judul(t) for t in anak}
            induk = _kata_judul(b["judul"])
            kata = (next(iter(kata_anak)) if len(kata_anak) == 1 and None not in kata_anak
                    else {"فصل": "مبحث", "مبحث": "مطلب", "باب": "فصل"}.get(induk))
            dhamir = "وفيها" if induk == "مسألة" else "وفيه"
            isi["pengantar"] = f"{dhamir} {kata_jumlah(len(anak), kata)}:" if kata else f"{dhamir}:"
        hasil[str(i)] = isi  # kunci teks: bahan JSON
    return hasil


# baris #R @pustaka_gaya: muallif: «**pengarang** (ت …هـ). __judul__. data cetak» (pengarang boleh tidak ada)
BARIS_MUALLIF = re.compile(r"^(?:\*\*(?P<nama>.+?)\*\*\s*(?:\((?P<wafat>[^)]*)\))?\s*[.،]?\s*)?__(?P<judul>.+?)__\s*[.،]?\s*(?P<sisa>.*)$")


def pustaka_judul_dulu(baris):
    """@pustaka_gaya: judul_tebal: baris #R muallif -> «**judul**. لفلان (ت: …هـ). data cetak»; nama «ابن كثير،
    إسماعيل بن عمر» dibalik jadi «إسماعيل بن عمر ابن كثير». None = bukan bentuk muallif."""
    m = BARIS_MUALLIF.match(baris.strip())
    if not m:
        return None
    bagian = [f"**{m['judul'].strip()}**"]
    if m["nama"]:
        nama = m["nama"].strip()
        if "،" in nama:
            akhir, _, depan = nama.partition("،")
            nama = f"{depan.strip()} {akhir.strip()}"
        nama = "لل" + nama[2:] if nama.startswith("ال") else "ل" + nama
        if m["wafat"]:
            nama += " (" + re.sub(r"^ت\s*:?\s*", "ت: ", m["wafat"].strip()) + ")"
        bagian.append(nama)
    if m["sisa"].strip(" ."):
        bagian.append(m["sisa"].strip().rstrip("."))
    return ". ".join(bagian) + "."


def paragraf_ihda(blok):
    """Indeks paragraf (P) di bawah «#K الإهداء» sampai judul berikutnya (@ihda: tengah)."""
    hasil, dalam = [], False
    for i, b in enumerate(blok):
        if b["k"] in JUDUL_ISI or b["k"] == "R":
            dalam = b["k"] == "K" and bool(IHDA.fullmatch(norma.HARAKAT.sub("", b["judul"]).strip()))
        elif dalam and b["k"] == "P":
            hasil.append(i)
    return hasil


def _terapkan_model_gaya(ctx):
    """@model mengisi pilihan tata letak yang tidak ditulis sendiri; tiap pilihan @GAYA dicek."""
    meta, blok, catatan = ctx.meta, ctx.blok, ctx.catatan
    if meta.get("model") and (model := _pilih(ctx, "model")):
        for k, v in MODEL[model].items():
            if k == "sampul" and meta.get("templat"):  # @templat membawa sampulnya sendiri
                continue
            meta.setdefault(k, v)
    ctx.gaya_ditulis = {k for k in GAYA if k in meta and DATA[k].baca(meta[k]) in GAYA[k]}
    for k in GAYA:  # yang tidak dikenal dirakit dengan bawaannya
        meta[k] = _pilih(ctx, k) or DATA[k].bawaan
    # bawaan GAYA tidak menuntut tempatnya: #F tanpa titik dua tetap satu baris (judul_dua_baris), tanpa الإهداء tetap jalan
    ditulis = ctx.gaya_ditulis
    if "judul_fasl" in ditulis:
        if meta["judul_fasl"] == "dua_baris" and not judul_dua_baris(blok):
            ctx.galat.append(ctx.di("@judul_fasl") + "@judul_fasl: dua_baris memerlukan judul #F bertitik dua, mis. "
                             "«#F الفصل الأول: المقدمة» (tercetak «الفصل الأول» lalu «المقدمة»)")
        elif meta["judul_fasl"] != "-" and not any(b["k"] == "F" for b in blok):
            ctx.galat.append(ctx.di("@judul_fasl") + f"@judul_fasl: {meta['judul_fasl']} memerlukan judul #F (فصل, atau "
                             "مبحث di bahts pendek tanpa فصل)")
    if meta["ihda"] == "tengah" and "ihda" in ditulis and not paragraf_ihda(blok):
        ctx.galat.append(ctx.di("@ihda") + "@ihda: tengah memerlukan «#K الإهداء» dengan paragraf di bawahnya")
    if meta["rujukan_ayat"] == "matan":  # [^سورة …، آية: n.] jadi «[السورة: n]» di matan, catatan kakinya tidak dicetak
        for b in blok:
            deret = b["sel"] if b["k"] == "J" else [b.get("runs", [])]
            ubah = False
            for runs in deret:
                for j, r in enumerate(runs):
                    if "fn" in r:
                        t = norma.HARAKAT.sub("", "".join(x.get("t", "") for x in catatan[r["fn"]]["runs"])).strip()
                        m = re.fullmatch(r"سورة\s+(.+?)،\s*آية:?\s*([\d٠-٩]+(?:\s*[-–]\s*[\d٠-٩]+)?)\.?", t)
                        if m:
                            catatan[r["fn"]]["matan"] = True
                            runs[j] = {"t": f" [{m.group(1)}: {m.group(2)}]", "b": False}
                            ubah = True
            if ubah:
                if b["k"] == "J":
                    b["runs"] = [r for s in b["sel"] for r in (*s, {"t": " "})]
                if "n" in b:
                    ctx.ayat_matan.add(b["n"])


def _cek_bentuk(ctx):
    """@kepala dengan @templat, @tanpa, daftar #R, dan @berkas."""
    meta, di_baris, pustaka, galat = ctx.meta, ctx.di_baris, ctx.pustaka, ctx.galat
    folder, di = ctx.folder, ctx.di
    # @templat memakai kepala halamannya sendiri: bawaan @kepala (juga nilai yang tidak dikenal) dan «-» tidak berlaku
    if meta.get("templat") and meta["kepala"] not in ("-", DATA["kepala"].bawaan):
        galat.append(di("@kepala") + f"@kepala: {meta['kepala']} dan @templat tidak bisa dipakai bersama: @templat sudah membawa kepala halamannya")
    if "pustaka" in daftar(meta, "tanpa"):  # sumber cukup di catatan kaki (rujukan pertama tiap kitab berdata lengkap)
        if "#R" in di_baris:
            galat.append(di("#R") + "@tanpa: pustaka, tetapi ada #R: hapus #R beserta daftarnya, atau hapus «pustaka» dari @tanpa")
    elif "#R" not in di_baris:
        galat.append("tidak ada #R (المصادر والمراجع) di akhir naskah: salin baris #R dari mesin/naskah_baru.txt, "
                     "lalu tulis satu kitab per baris di bawahnya")
    elif "#R" in di_baris and not pustaka:
        galat.append(di("#R") + "المصادر والمراجع masih kosong: tulis satu kitab per baris sesudah #R")
    # judulnya dibaca dari tanda __…__ (pustaka_judul_dulu); sebagai bawaan, baris lain tercetak apa adanya berbutir «•»
    if meta["pustaka_gaya"] == "judul_tebal" and "pustaka_gaya" in ctx.gaya_ditulis:
        for n, t in ctx.pustaka_baris:
            if not adalah_mushaf(t) and not pustaka_judul_dulu(t):
                galat.append(f"baris {n}: @pustaka_gaya: judul_tebal membaca baris #R berbentuk «**pengarang** (ت …هـ). "
                             f"__judul__. data cetak» (seperti muallif; `pustaka <folder>` menyusunnya): «{t[:40]}» tanpa __judul__")
    if not meta["berkas"]:
        meta["berkas"] = folder.name
    if re.search(r'[<>:"/\\|?*\x00-\x1f]', meta["berkas"]):
        galat.append(di("@berkas") + f"@berkas: «{meta['berkas']}»: nama berkas tidak boleh memuat : / \\ ? * < > | \" atau karakter kontrol")
    elif re.fullmatch(r"(?i:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³]) *(?:\..*)?", meta["berkas"]):
        galat.append(di("@berkas") + f"@berkas: «{meta['berkas']}»: nama perangkat Windows tidak bisa dipakai sebagai nama hasil")


def kunci_urut(s, pengarang=False):
    """Kunci urutan abjad Arab untuk المصادر dan فهرس: buang harakat, tanda tebal/miring, «ال» (selain «الله»),
    dan «ابن/أبو» di depan nama pengarang («ابن القيم» di ق؛ أبو سليمان ص204)."""
    s = norma.HARAKAT.sub("", s.replace("**", "").replace("__", ""))  # tanda tebal/miring @pustaka_gaya: muallif
    if pengarang:  # baris diawali nama pengarang: «ابن/أبو» tidak dihitung, «ابن القيم» di ق (أبو سليمان ص204)
        s = re.sub(r"^(?:(?:ابن|أبو|أبي|أبا|ابو|ابي|ابا)\s+)+", "", s)
    if not s.startswith("الله"):
        s = re.sub(r"^ال", "", s)
    # tanda baca = akhir judul/nama, diurutkan sebelum spasi: «الكتاب، سيبويه» sebelum «الكتاب الفريد»
    # («،» U+060C dan «.» lebih besar dari spasi, jadi judul yang lebih panjang naik duluan)
    s = re.sub("[،؛,.:;]", "\x01", s)
    return re.sub("[إأآ]", "ا", s)


def pustaka_asing(s):
    """Baris المصادر tanpa huruf Arab (rujukan asing): dicetak sesudah rujukan Arab, kiri-ke-kanan rata kiri.
    Satu aturan untuk urutan dan arah cetak; baris bercampur («Ibn Taymiyyah, مجموع الفتاوى») tetap rujukan Arab."""
    return not re.search("[؀-ۿ]", s)


def _urutkan_fihris(ctx):
    """Urutan المصادر (القرآن الكريم paling atas), nama surat فهرس الآيات, urutan فهرس الأحاديث.
    Kembalikan baris pustaka القرآن الكريم."""
    pustaka, ayat_idx, hadits_idx = ctx.pustaka, ctx.ayat_idx, ctx.hadits_idx
    quran = [p for p in pustaka if adalah_mushaf(p)]  # tanpa nomor, paling atas
    pengarang = ctx.meta.get("pustaka_gaya") == "muallif"
    judul_dulu = ctx.meta.get("pustaka_gaya") == "judul_tebal"  # urut judul yang tercetak di depan, bukan pengarang
    # rujukan Arab dulu, lalu rujukan asing (pustaka_asing), masing-masing urut abjad
    pustaka = quran + sorted([p for p in pustaka if p not in quran],
                             key=lambda p: (pustaka_asing(p), kunci_urut((judul_dulu and pustaka_judul_dulu(p)) or p, pengarang)))
    for a in ayat_idx:
        a["surah"] = SURAH[a["s"] - 1]
    hadits_idx.sort(key=lambda h: kunci_urut(h["t"]))
    # فهرس الأشعار urut حرف الروي, lalu قافيةnya, lalu صدرnya
    ctx.syir_idx.sort(key=lambda v: (RAWI.index(r) if (r := _rawi(v["qf"])) and r in RAWI else len(RAWI),
                                     kunci_urut(v["qf"]), kunci_urut(v["t"])))
    # فهرس nama: satu baris per nama (semua penandanya); فهرس الأعلام urut tanpa «ال/ابن/أبو» seperti pengarang di المصادر
    # nama yang hanya beda harakat atau hamzah («ابنُ عثيمين»، «احمد») = orang yang sama: satu baris, bentuk pertamanya
    for f in FIHRIS_NAMA:
        gabung = {}
        for a in ctx.nama_idx[f.kunci]:
            kunci = re.sub("[إأآ]", "ا", norma.HARAKAT.sub("", a["t"]))
            gabung.setdefault(kunci, {"t": a["t"], "k": []})["k"].append(a["k"])
        ctx.fihris_nama[f.kunci] = sorted(gabung.values(), key=lambda a: kunci_urut(a["t"], f.pengarang))
    ctx.pustaka = pustaka
    return quran


# Baris #R yang berupa mushaf: «القرآن الكريم» (boleh disusul «، رواية حفص…» atau «برواية…»), «القرآن.», «المصحف الشريف…».
# Kitab yang judulnya hanya diawali «القرآن» («القرآن والسنة…»، «القرآن الكريم وعلومه») tetap kitab biasa
MUSHAF = re.compile(r"^(?:القران(?:\s+الكريم)?|المصحف(?:\s+الشريف)?)\s*(?:$|[.،,:؛(\-–]|ب?رواي[ةه])")


def adalah_mushaf(baris):
    return bool(MUSHAF.match(re.sub("[إأآ]", "ا", norma.HARAKAT.sub("", baris.replace("**", "").replace("__", ""))).strip()))


def batas_minimal(meta, apa):
    """(batas, asal) dari «@minimal_<apa>: n» atau bawaannya; batas 0 = tidak dinilai, None = nilainya rusak.
    asal = teks untuk pesan: «@minimal_halaman: 20» atau «bawaan 25»."""
    kunci = f"minimal_{apa}"
    nilai = meta.get(kunci, "")
    if kunci not in meta:
        return MINIMAL[apa], f"bawaan {MINIMAL[apa]}"
    if not nilai.isdecimal():  # isdecimal juga menerima ٢٠; kosong = rusak
        return None, f"«@{kunci}: {nilai}»"
    return int(nilai), f"«@{kunci}: {nilai}»"


def _cek_minimal_rusak(ctx):
    """@minimal_*: harus bilangan bulat (0 = tidak dinilai); kosong atau kata = GAGAL, bukan diam-diam kembali ke bawaan."""
    for apa in MINIMAL:
        if batas_minimal(ctx.meta, apa)[0] is None:
            nilai = ctx.meta[f"minimal_{apa}"]
            ctx.galat.append(ctx.di(f"@minimal_{apa}") + f"@minimal_{apa}: "
                             + (f"«{nilai}» bukan bilangan bulat" if nilai else "kosong")
                             + f"; tulis jumlah dari dosen (mis. 20; 0 = tidak dinilai) atau hapus barisnya (bawaan {MINIMAL[apa]})")


def _cek_jumlah_kitab(ctx, quran):
    """@minimal_kitab: jumlah kitab di المصادر (selain القرآن الكريم) tidak boleh kurang dari batas dosen.
    Kurang = perhatian, bukan GAGAL. Bawaan tidak dinilai (MINIMAL).
    Baris #R kembar (sama sesudah harakat, hamzah, dan tanda baca disamakan) dihitung sekali dan GAGAL: selalu bisa
    dibereskan dengan menghapus salah satunya."""
    di = ctx.di
    batas, asal = batas_minimal(ctx.meta, "kitab")
    # @tanpa: pustaka dan #R yang kosong (sudah GAGAL di _cek_bentuk) tidak punya daftar untuk dihitung
    if batas is None or "pustaka" in daftar(ctx.meta, "tanpa") or not ctx.pustaka:
        return
    unik, kembar = set(), []
    for p in ctx.pustaka:
        if p in quran:
            continue
        kunci = norma.norm(p.replace("**", "").replace("__", ""))
        if kunci in unik:
            kembar.append(p)
        unik.add(kunci)
    if kembar:
        ctx.galat.append(di("#R") + f"المصادر والمراجع memuat baris kembar (dihitung sekali): «{kembar[0]}»"
                             + (f" dan {len(kembar) - 1} lainnya" if len(kembar) > 1 else "") + "; hapus salah satunya")
    n = len(unik)
    if n < batas:
        ctx.perhatian.append(
            (di("@minimal_kitab") or di("#R")) + f"المصادر والمراجع baru {n} kitab (selain القرآن الكريم), kurang dari {batas} ({asal}): "
            "tambah kitab yang benar-benar dibaca dan dirujuk di catatan kaki; kalau dosen memang meminta lebih sedikit, "
            "tulis jumlah dari dosen di «@minimal_kitab: n»")


def _cek_kitab_pustaka(ctx):
    """Kitab berbukti di catatan kaki yang tidak ada di المصادر والمراجع = perhatian (cek_rujukan.kitab_tanpa_pustaka).
    Tidak dinilai: @tanpa: pustaka (sumber cukup di catatan kaki), dan #R yang kosong atau tidak ada (sudah GAGAL di
    _cek_bentuk)."""
    if "pustaka" in daftar(ctx.meta, "tanpa") or not ctx.pustaka:
        return
    ctx.perhatian += kitab_tanpa_pustaka(ctx.penunjuk, [(n, t) for n, t in ctx.pustaka_baris if not adalah_mushaf(t)])


def kurang_halaman(meta, halaman):
    """(batas, asal) kalau `halaman` seluruh PDF kurang dari @minimal_halaman (bawaan MINIMAL); None = cukup, atau
    tidak dinilai: batas 0."""
    batas, asal = batas_minimal(meta, "halaman")
    return (batas, asal) if batas and halaman < batas else None


def _cek_jumlah_halaman(ctx, d):
    """@minimal_halaman: perkiraan halaman seluruh PDF (sampul s.d. فهرس) tidak boleh kurang dari batasnya.
    Perkiraan dari jumlah kata, jadi kurang = perhatian; angka pasti `HALAMAN` dinilai lagi sesudah `rakit`."""
    n = perkiraan_halaman(d)
    kurang = n and kurang_halaman(ctx.meta, n[1])
    if kurang:
        batas, asal = kurang
        ctx.perhatian.append(
            (ctx.di("@minimal_halaman") or "") + f"perkiraan seluruh PDF ±{n[1]} halaman, kurang dari {batas} ({asal}): "
            "tambah pembahasan dari bahan yang benar-benar dibaca (bukan mengulang atau memperbesar huruf); kalau dosen "
            "meminta lebih sedikit, tulis jumlah dari dosen di «@minimal_halaman: n». Angka pasti = HALAMAN sesudah `rakit`")


def perkiraan_halaman(d):
    """Perkiraan kasar (isi, seluruh PDF, rincian) dari jumlah kata, untuk yang belum bisa `rakit`; None tanpa profil.
    isi = المقدمة s.d. الخاتمة: tiap #K/#F (dan judul di @halaman_baru) mulai halaman baru; kata catatan kaki dihitung
    menurut perbandingan luas hurufnya. Seluruh PDF = sampul + halaman sebelum المقدمة (@nomor) + isi + المصادر + فهرس:
    bagian yang dicetak dibaca dari rencana cetak. Pembagian halaman isi di sini kasar dan milik perkiraan ini sendiri
    (tiap #K/#F/#H dihitung mulai halaman): angkanya ditera ke PDF nyata dengan pembagian itu."""
    rencana = d["cetak"]
    fmt = rencana["format"]
    if not fmt:
        return None
    # huruf lebih kecil = lebih banyak kata, tetapi tidak sebanyak luasnya (pangkat 1,1, bukan 2: 3 PDF @format tatbiqi)
    per_hal = KATA_PER_HALAMAN_18 * (18 / fmt["matan"]) ** 1.1 / fmt["spasi"]  # 1,5 spasi = baris lebih sedikit
    meta = d["meta"]

    def halaman(blok):
        bagian = []
        for b in blok:
            if b["k"] in ("K", "F", "H", *meta.get("halaman_baru", [])) or not bagian:
                bagian.append(0.0)
            fn = sum(kata(d["catatan"][r["fn"]]["runs"]) for r in b["runs"] if r.get("fn") is not None)
            # tabel #J: sel sempit dan bergaris, jadi satu kata makan tempat lebih banyak daripada di paragraf
            bagian[-1] += kata(b["runs"]) * (1.4 if b["k"] == "J" else 1) + fn * (fmt["catatan"] / fmt["matan"]) ** 2
            if b["k"] == "G":  # gambar selebar teks (lebar:tinggi bidang teks ±0,68), paling tinggi 70% halaman
                bagian[-1] += per_hal * min(b["rasio"] * 0.68, 0.7)
            elif b["k"] == "E":  # persamaan baris sendiri (OMML): kira-kira 3-4 baris teks
                bagian[-1] += per_hal * 0.12
        return sum(max(1, math.ceil(x / per_hal)) for x in bagian)

    i_r = next((i for i, b in enumerate(d["blok"]) if b["k"] == "R"), len(d["blok"]))
    blok, malahiq = d["blok"][:i_r], d["blok"][i_r + 1:]  # @malahiq: akhir = sesudah #R
    # الإهداء dst. sebelum المقدمة bukan halaman isi, dengan atau tanpa @nomor (sama dengan HALAMAN_ISI)
    mula = rencana["awal_isi"] or 0
    isi = halaman(blok[mula:]) + len(rencana["pemisah"])  # halaman pemisah (@judul_fasl) di dalam halaman isi
    rinci = {"sampul": 1 + rencana["basmalah"] + bool(rencana["ayat_pembuka"]) if not rencana["buang_sampul"] else 0,
             "sebelum المقدمة": halaman(blok[:mula]) if mula else 0, "الملاحق": halaman(malahiq) if malahiq else 0,
             "penutup": int(rencana["tamma"])}
    judul = sum(b["k"] in JUDUL_FIHRIS for b in blok)  # baris فهرس الموضوعات
    dicetak = {b["jenis"] for b in rencana["bagian"]}
    for nama, jenis, n, per in (("المصادر", "pustaka", len(d["pustaka"]), 12), ("فهرس الآيات", "ayat", len(d["ayat"]), 26),
                                ("فهرس الأحاديث", "hadits", len(d["hadits"]), 20), ("فهرس الآثار", "atsar", len(d["atsar"]), 20),
                                *((f.judul, f.kunci, len(d[f.kunci]), 20) for f in FIHRIS_NAMA),
                                ("فهرس الأشعار", "syir", len(d["syir"]), 20),
                                ("فهرس الموضوعات", "maudhuat", max(judul, 1), 25)):
        # baris per halaman dari 30 PDF bahts nyata (selisih paling banyak 1 halaman)
        rinci[nama] = math.ceil(n / per) if jenis in dicetak else 0
    return isi, isi + sum(rinci.values()), {k: v for k, v in rinci.items() if v}


def _hitung_kata(ctx):
    """Jumlah kata matan dan catatan kaki naskah (sebelum `_angka_cetak`)."""
    blok, catatan = ctx.blok, ctx.catatan
    n_matan = sum(kata(b["runs"]) for b in blok)
    n_fn = sum(kata(c["runs"]) for c in catatan if not c.get("matan"))
    return n_matan, n_fn


PISAH_SUB = re.compile(r"^\s*[-–—]\s+|\s+[-–—]\s*$")  # « - » sub-judul di ujung baris @judul_sampul: tidak tercetak


def _rapat(s):
    """Teks dengan spasi dirapatkan, angka 0-9, dan tanpa « - » sub-judul: pembanding @judul_sampul dengan @judul (baris
    sampul boleh pindah di « - » tanpa menulis tandanya)."""
    return re.sub(r"\s+", " ", re.sub(r"(?<!\S)[-–—](?!\S)", " ", s.translate(ANGKA_LATIN))).strip()


def _cek_sampul(ctx):
    """@sampul, @tahun, data sampul wajib, @pustaka, @tanpa, dan @templat."""
    meta, galat, folder, di = ctx.meta, ctx.galat, ctx.folder, ctx.di
    sampul = _pilih(ctx, "sampul")
    # rakit.ps1 hanya memakai salah satu: jangan ada yang diabaikan diam-diam
    if sampul and "sampul" in meta and meta.get("templat"):
        galat.append(di("@sampul") + "@sampul dan @templat tidak bisa dipakai bersama: @templat sudah membawa sampulnya sendiri; hapus salah satu")
    meta["sampul"] = sampul or DATA["sampul"].bawaan  # yang tidak dikenal dirakit dengan bawaannya
    if meta["logo"] == "berwarna" and (meta.get("templat") or meta["sampul"] != "qism"):
        alasan = ("@templat membawa sampulnya sendiri" if meta.get("templat")
                  else f"@sampul: {meta['sampul']} memakai logonya sendiri")
        galat.append(di("@logo") + f"@logo: berwarna hanya untuk sampul qism (bawaan): {alasan}")
    if meta.get("judul_sampul"):  # pindah baris judul di sampul tengah: @judul tetap judul persis dari dosen
        if meta["sampul"] != "tengah" or meta.get("templat"):
            galat.append(di("@judul_sampul") + "@judul_sampul hanya untuk @sampul: tengah; sampul lain memecah judulnya sendiri")
        elif _rapat(meta["judul_sampul"].replace("//", " ")) != _rapat(meta.get("judul", "")):
            galat.append(di("@judul_sampul") + "@judul_sampul harus sama dengan @judul, hanya ditambah « // » di tempat "
                         "pindah baris: samakan kata-katanya")
    if meta.get("ayat_pembuka"):  # «s:a» atau «s:a-b»: dicek di sini, teksnya diambil rencana_cetak
        try:
            ayat(meta["ayat_pembuka"].translate(ANGKA_LATIN))
        except TandaRusak as e:
            galat.append(di("@ayat_pembuka") + "@ayat_pembuka: " + re.sub(r"\{Q:([^}]*)\}", r"«\1»", str(e)))
    if meta.get("tahun") and not re.fullmatch(r"[1١][34٣٤][0-9٠-٩]{2}(?:\s*[-–]\s*[12١٢][0-9٠-٩]{3}|\s*/\s*[1١][34٣٤][0-9٠-٩]{2})?", meta["tahun"]):
        galat.append(di("@tahun") + f"@tahun: «{meta['tahun']}» bukan tahun hijriah 1300-1499 (mis. ١٤٤٨), dua tahun hijriah "
                     "(mis. «١٤٤٨/١٤٤٩»), atau hijriah - masehi (mis. «١٤٤٨ - ٢٠٢٦», tercetak «١٤٤٨هـ – ٢٠٢٦م»)")
    # @templat: sampul diambil apa adanya dari Word mahasiswa; @sampul salah ketik: data wajib model mana pun belum pasti
    wajib = ("judul",) if meta.get("templat") or not sampul else SAMPUL[sampul]
    galat += [di("@" + k) + f"data sampul belum diisi: @{k}" for k in wajib if not meta.get(k)]
    _pilih(ctx, "pustaka")
    asing = [t for t in daftar(meta, "tanpa") if t not in TANPA + TANPA_CETAK]
    if asing:
        _tak_dikenal(ctx, "tanpa", "، ".join(asing))
    if meta.get("templat"):  # Word mahasiswa: sampul dan kepala halaman diambil dari situ oleh rakit.ps1
        tpl = (folder / meta["templat"]).resolve()
        if tpl.suffix.lower() not in (".docx", ".doc"):
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


PENGANTAR = re.compile(r"(?:ال)?(?:تمهيد|مدخل)\b")


def _anak_tunggal(blok):
    """(anak, induk) tiap sub-bagian yang sendirian di bawah induknya: satu #B di bawah #F, satu #M di bawah #B."""
    for t_induk, t_anak, pemutus in (("F", "B", "KR"), ("B", "M", "KRF")):
        induk, anak = None, []
        for b in (*blok, {"k": "R"}):  # penutup: induk terakhir ikut dinilai
            if b["k"] == t_anak and induk:
                if not PENGANTAR.match(norma.HARAKAT.sub("", b["judul"])):  # تمهيد bukan pecahan bagiannya: tidak dihitung
                    anak.append(b)
            elif b["k"] == t_induk or b["k"] in pemutus:
                if induk and len(anak) == 1:
                    yield anak[0], induk
                induk, anak = (b if b["k"] == t_induk else None), []


def _cek_tata_letak(ctx):
    """@halaman_baru, @nomor, bagian kosong dan judul bertumpuk, @nim, dan kunci ya/tidak."""
    meta, blok, galat, perhatian = ctx.meta, ctx.blok, ctx.galat, ctx.perhatian
    di = ctx.di
    baru = daftar(meta, "halaman_baru")
    if any(t not in HALAMAN_BARU for t in baru):
        _tak_dikenal(ctx, "halaman_baru", meta["halaman_baru"])
    meta["halaman_baru"] = [t for t in baru if t in HALAMAN_BARU]
    nomor = _pilih(ctx, "nomor")
    if nomor == "abjad" and not any(b["k"] == "F" for b in blok):
        galat.append(di("@nomor") + "@nomor: abjad memerlukan #F: nomor ١ mulai dari #F pertama")
    elif nomor == "mukadimah" and not any(b["k"] == "K" and norma.HARAKAT.sub("", b.get("judul", "")) == MUQADDIMAH for b in blok):
        galat.append(di("@nomor") + "@nomor: mukadimah memerlukan «#K المقدمة»: nomor ١ mulai dari judul itu")
    # bagian kosong: judul bahts yang disusul judul setingkat/lebih tinggi (atau akhir naskah) tanpa paragraf isi di antaranya
    # (#H bukan isi)
    urut = [b for b in blok if b["k"] != "H"]
    kosong = {id(a) for a, b in zip(urut, urut[1:] + [{"k": "R"}])
              if a["k"] in JUDUL_ISI and TINGKAT_JUDUL.get(b["k"], 9) <= TINGKAT_JUDUL[a["k"]]}
    halaman_baru = set(awal_halaman(blok, meta)[0])
    for i, (a, b) in enumerate(zip(blok, blok[1:] + [{"k": ""}])):
        if id(a) in kosong:  # sekaligus menggantikan «tercetak sendirian»: menulis isinya membereskan keduanya
            perhatian.append(f"baris {a['n']}: bagian «{a['judul'][:40]}» masih kosong: belum ada paragraf isi sebelum "
                             f"judul berikutnya yang setingkat atau lebih tinggi; tulis isinya, atau hapus judulnya")
        elif a["k"] in JUDUL_FIHRIS and (b["k"] == "H" or i + 1 in halaman_baru):
            perhatian.append(f"baris {a['n']}: judul «{a['judul'][:40]}» tercetak sendirian di halamannya, karena judul "
                             f"sesudahnya mulai halaman baru: tulis paragraf pengantar di bawahnya (kaitannya dengan bagian "
                             f"sebelumnya dan isinya, mis. وفيه مطلبان…, tanpa klaim baru tanpa bukti)")
        elif (a["k"] in ("F", "B") and b["k"] in ("B", "M") and "FBM".index(b["k"]) > "FBM".index(a["k"])
              and not (a["k"] == "F" and meta["judul_fasl"] in JUDUL_FASL_PEMISAH)  # halaman pemisah = pengantarnya
              and not re.search(r"تمهيد|مدخل", norma.HARAKAT.sub("", b["judul"]))):  # judul «تمهيد» di bawahnya = pengantar itu sendiri
            # فصل/مبحث yang langsung disusul مبحث/مطلب-nya: judul bertumpuk tanpa تمهيد (dikeluhkan dosen)
            perhatian.append(f"baris {a['n']}: judul «{a['judul'][:40]}» langsung disusul judul «{b['judul'][:40]}» "
                             f"tanpa paragraf pengantar: tulis pengantar di bawahnya (isinya dan pembagiannya: "
                             f"{'وفيه مبحثان' if a['judul'].startswith('الفصل') or (a['k'] == 'F' and not a['judul'].startswith('المبحث')) else 'وفيه مطلبان'}…)")
    for anak, induk in _anak_tunggal(blok):
        perhatian.append(f"baris {anak['n']}: sub-bagian tunggal «{anak['judul'][:40]}» di bawah «{induk['judul'][:40]}»: "
                         "bagian yang dipecah semestinya paling sedikit dua (tambah pasangannya, atau satukan isinya "
                         "di bawah induknya)")
    if re.fullmatch(r"0+", re.sub(r"\s", "", meta.get("nim", "").translate(ANGKA_LATIN))):  # isian contoh, bukan nomor
        galat.append(di("@nim") + f"@nim: «{meta['nim']}» tercetak di sampul sebagai nomor mahasiswa: tulis nomor asli, "
                                  "atau «-» kalau tidak ada")
    for kunci in (k for k, sifat in DATA.items() if sifat is YA_TIDAK):
        _pilih(ctx, kunci)
    _pilih(ctx, "basmalah")  # ya / utsmani


def _profil(ctx):
    """Profil @format, ditimpa @catatan_kaki/@spasi; None kalau @format tidak dikenal."""
    profil = FORMAT.get(_pilih(ctx, "format"))
    for k, (kunci, nilai) in TIMPA.items():
        pilihan = _pilih(ctx, k)
        if pilihan and profil:
            profil = {**profil, kunci: nilai[pilihan]}
    return profil


def _render_rumus(ctx, profil):
    """Render ulang OMML rumus (#E dan {E:…}) memakai huruf Arab dan ukuran profil @format yang sudah utuh."""
    fmt = format_cetak(profil)
    if not fmt:
        return
    huruf_arab, u_latin, u_arab = fmt["huruf"], fmt["latin"], fmt["matan"]
    for b in ctx.blok:
        if b["k"] == "E":
            b["omml"], _ = rumus.konversi(b["latex"], display=True, huruf_arab=huruf_arab,
                                          ukuran_latin=u_latin + 1, ukuran_arab=u_arab)
        else:
            # sel #J: ukuran huruf tabel ($uTabel di rakit.ps1)
            u_sel = math.ceil((fmt["matan"] + fmt["catatan"]) / 2) if b["k"] == "J" else u_arab
            for runs in (b["sel"] if b["k"] == "J" else [b.get("runs", [])]):
                for r in runs:
                    if "omml" in r:
                        r["omml"], _ = rumus.konversi(r["latex"], display=False, huruf_arab=huruf_arab,
                                                      ukuran_latin=u_latin, ukuran_arab=u_sel)
    for c in ctx.catatan:
        for r in c["runs"]:
            if "omml" in r:
                r["omml"], _ = rumus.konversi(r["latex"], display=False, huruf_arab=huruf_arab,
                                              ukuran_latin=max(9, u_latin - 2), ukuran_arab=fmt["catatan"])


def _angka_cetak(ctx):
    """Angka yang tercetak (@angka, @angka_ayat) dan kalimat hormat: @data berteks, runs, judul, فهرس الأحاديث, dan
    المصادر diubah di tempat, jadi `bukti` mencetak matan seperti tercetak. Yang menghitung kata naskah (`_hitung_kata`)
    harus jalan sebelum ini: ٠-٩ terhitung huruf Arab."""
    meta, blok, catatan, hadits_idx = ctx.meta, ctx.blok, ctx.catatan, ctx.hadits_idx
    angka = _pilih(ctx, "angka")
    meta.setdefault("angka", angka)
    angka_ayat = angka and (_pilih(ctx, "angka_ayat") if "angka_ayat" in meta else angka)
    if not angka_ayat:
        return
    # yang dihitung Word (nomor halaman, catatan kaki, فهرس) diubah di rakit.ps1; ayat (q) tetap apa adanya
    ubah = hindi if angka == "hindi" else (lambda s: s.translate(ANGKA_LATIN))
    for k, sifat in DATA.items():
        if sifat.teks and k in meta:
            meta[k] = ubah(meta[k])
    for r in [r for b in blok + catatan if b.get("k") != "L" for r in b["runs"]] + hadits_idx:
        if "t" in r and not r.get("q"):
            r["t"] = ubah(r["t"]).translate(HORMAT_CETAK)
    if angka_ayat != angka:  # rujukan ayat [^سورة …، آية: n.] saja; "al" = rakit.ps1 mencetak angkanya kiri-ke-kanan,
        for c in catatan:      # karena Word (angka konteks) mencetak 0-9 di tengah teks Arab sebagai ٠-٩
            if norma.HARAKAT.sub("", "".join(r.get("t", "") for r in c["runs"])).startswith("سورة"):
                c["al"] = angka_ayat == "latin"
                for r in c["runs"]:
                    if "t" in r:
                        r["t"] = hindi(r["t"]) if angka_ayat == "hindi" else r["t"].translate(ANGKA_LATIN)
    for b in blok:
        if "judul" in b:
            b["judul"] = ubah(b["judul"])
        if b["k"] == "E" and b.get("tag"):
            b["tag"] = ubah(b["tag"])
    for h in hadits_idx:
        h["r"] = ubah(h["r"])
    ctx.pustaka = [ubah(p) for p in ctx.pustaka]


MALAHIQ = re.compile(r"(ال)?ملاحق|ملحق")
MULAKHAS = re.compile(r"^(?:ال)?ملخص")
MULAKHAS_ASING = re.compile(r"ال[أا]جنبي[ةه]|ال[إا]نجليزي[ةه]")


def _malahiq(ctx):
    """@malahiq: akhir = blok dari «#K الملاحق» sampai #R dipindah ke sesudah blok #R: blok sesudah #R dicetak sesudah
    المصادر والمراجع dan sebelum فهرس (bagian_akhir; urutan خطة yang menaruh الملاحق sesudah قائمة المصادر)."""
    meta, blok, galat, di = ctx.meta, ctx.blok, ctx.galat, ctx.di
    if "malahiq" not in meta:
        return
    if not _pilih(ctx, "malahiq"):
        return
    if meta.get("pustaka") == "akhir":
        galat.append(di("@malahiq") + "@malahiq: akhir tidak bisa bersama @pustaka: akhir (المصادر sesudah فهرس): pilih salah satu"); return
    awal = next((i for i, b in enumerate(blok) if b["k"] == "K" and MALAHIQ.match(norma.HARAKAT.sub("", b["judul"]))), None)
    i_r = next((i for i, b in enumerate(blok) if b["k"] == "R"), None)
    if awal is None:
        galat.append(di("@malahiq") + "@malahiq: akhir memerlukan «#K الملاحق» (atau «#K ملحق…») sebelum #R"); return
    if i_r is None:
        if "pustaka" in daftar(meta, "tanpa"):
            galat.append(di("@malahiq") + "@malahiq: akhir memerlukan #R (المصادر والمراجع): الملاحق dicetak sesudah المصادر")
        return
    blok[:] = blok[:awal] + [blok[i_r]] + blok[awal:i_r] + blok[i_r + 1:]


def _bait_syair(blok):
    """Blok seperti dicetak: di bait syair #V, « ... » jadi jarak antarparuh dan « // » pindah baris dalam paragraf
    Word (\\v). Blok dan runs naskah tidak diubah."""
    def cetak(r):
        return {**r, "t": re.sub(r"\s*//\s*", "\v", re.sub(r"\s*\.\.\.\s*", "\u2003\u2003\u2003", r["t"]))} if "t" in r else r
    return [{**b, "runs": [cetak(r) for r in b["runs"]]} if b["k"] == "V" else b for b in blok]


def awal_halaman(blok, meta):
    """(indeks blok yang diawali pindah halaman, indeks judul tempat nomor halaman kembali ١ atau None).
    Pindah halaman: #K dan #F serta judul di @halaman_baru, kecuali judul pertama naskah, dan
    blok apa pun sesudah #H (sesudah judul pertama). Nomor kembali ١ (@nomor) di #F pertama, atau di «#K المقدمة» untuk
    mukadimah: judul itu mulai bagian Word baru, dengan atau tanpa pindah halaman."""
    nomor, pilihan = meta.get("nomor"), meta.get("halaman_baru", [])
    baru, nomor_satu, pertama, sesudah_h = [], None, True, False
    for i, b in enumerate(blok):
        k = b["k"]
        if k == "R":  # blok sesudahnya (@malahiq: akhir) dicetak sesudah المصادر: bukan lagi judul pertama
            pertama = False
        elif k == "H":
            sesudah_h = not pertama
        else:
            pb = sesudah_h
            if k in JUDUL_FIHRIS:
                pb = pb or (not pertama and (k in pilihan or k in JUDUL_BAB))
                awal_nomor = k == "K" and norma.HARAKAT.sub("", b["judul"]) == MUQADDIMAH if nomor == "mukadimah" else k == "F"
                if nomor in ("abjad", "mukadimah") and awal_nomor and nomor_satu is None:
                    nomor_satu = i
                pertama = False
            sesudah_h = False
            if pb:
                baru.append(i)
    return baru, nomor_satu


def format_cetak(profil):
    """Profil @format dengan tiap kunci terisi (BAWAAN_FORMAT, IKUT_FORMAT); None tanpa profil."""
    if not profil:
        return None
    lengkap = {**BAWAAN_FORMAT, **profil}
    return {**{k: lengkap[asal] for k, asal in IKUT_FORMAT.items()}, **lengkap}


# nama huruf pertama طرف di @fihris_hadits: huruf (kunci_urut: tanpa «ال», hamzah = alif)
NAMA_HURUF = dict(zip("ابتثجحخدذرزسشصضطظعغفقكلمنهوي",
                      ("الهمزة", "الباء", "التاء", "الثاء", "الجيم", "الحاء", "الخاء", "الدال", "الذال", "الراء", "الزاي",
                       "السين", "الشين", "الصاد", "الضاد", "الطاء", "الظاء", "العين", "الغين", "الفاء", "القاف", "الكاف",
                       "اللام", "الميم", "النون", "الهاء", "الواو", "الياء")))


def _fihris_hadits(meta, hadits, atsar):
    """Butir bagian فهرس الأحاديث menurut @fihris_hadits: judul, bentuk (terbuka | tabel | ringkas | titik | huruf), judul kolom
    tabel, dan untuk huruf judul kelompok tiap baris («حرف الهمزة»; None = sama dengan baris sebelumnya) serta rawi
    (baris bertitik memuat «(الراوي)»)."""
    bentuk = meta.get("fihris_hadits") or GAYA["fihris_hadits"][0]
    if bentuk == "ringkas":
        return {"judul": "فهرس الأحاديث الشريفة", "bentuk": bentuk}
    if bentuk == "titik":
        return {"judul": "فهرس أطراف الأحاديث النبوية", "bentuk": bentuk}
    if bentuk == "huruf":
        nama = [NAMA_HURUF.get(kunci_urut(h["t"])[:1], kunci_urut(h["t"])[:1]) for h in hadits]
        return {"judul": "فهرس الأحاديث النبوية", "bentuk": bentuk, "rawi": True,
                "kelompok": [f"حرف {x}" if not i or x != nama[i - 1] else None for i, x in enumerate(nama)]}
    # atsar ber-{AT:} punya فهرس sendiri: judul dan kolom ini hanya untuk hadits
    return {"judul": "فهرس الأحاديث النبوية" if atsar else "فهرس الأحاديث والآثار", "bentuk": bentuk,
            "kolom": "طرف الحديث" if atsar else "طرف الحديث أو الأثر"}


def bagian_akhir(d):
    """Bagian yang dicetak sesudah isi, urut: المصادر, الملاحق (blok sesudah #R), tiap فهرس (الآيات، الأحاديث، الآثار،
    فهرس nama FIHRIS_NAMA, الأشعار), الموضوعات. Tiap butir {jenis, judul}; فهرس الآيات/الأحاديث dan فهرس nama juga
    {bentuk} (nama: tabel | nomor | titik), فهرس nama juga {kolom}. فهرس kosong atau disebut di @tanpa tidak dicetak;
    @pustaka: akhir menaruh المصادر sesudah فهرس الأشعار."""
    meta, tanpa = d["meta"], daftar(d["meta"], "tanpa")
    pustaka = "pustaka" not in tanpa
    akhir = meta.get("pustaka") == "akhir"
    i_r = next((i for i, b in enumerate(d["blok"]) if b["k"] == "R"), None)
    ada = lambda jenis: bool(d[jenis]) and jenis not in tanpa
    bentuk_ayat = meta.get("fihris_ayat") or GAYA["fihris_ayat"][0]
    bentuk_nama = lambda f: "titik" if f.titik else "nomor" if f.kunci == "alam" and meta.get("fihris_alam") == "nomor" else "tabel"
    return [
        *([{"jenis": "pustaka", "judul": "المصادر والمراجع"}] if pustaka and not akhir else []),
        *([{"jenis": "malahiq"}] if i_r is not None and i_r + 1 < len(d["blok"]) else []),
        *([{"jenis": "ayat", "judul": "فهرس الآيات الكريمة" if bentuk_ayat == "surah" else "فهرس الآيات القرآنية",
            "bentuk": bentuk_ayat}] if ada("ayat") else []),
        *([{"jenis": "hadits", **_fihris_hadits(meta, d["hadits"], ada("atsar"))}] if ada("hadits") else []),
        *([{"jenis": "atsar", "judul": "فهرس الآثار", "bentuk": "titik", "rawi": True}] if ada("atsar") else []),
        *({"jenis": f.kunci, "judul": f.judul, "kolom": f.kolom, "bentuk": bentuk_nama(f)} for f in FIHRIS_NAMA if ada(f.kunci)),
        *([{"jenis": "syir", "judul": "فهرس الأشعار"}] if ada("syir") else []),
        *([{"jenis": "pustaka", "judul": "فهرس المصادر والمراجع"}] if pustaka and akhir else []),
        *([{"jenis": "maudhuat", "judul": "فهرس الموضوعات"}] if "maudhuat" not in tanpa else []),
    ]


# judul #K halaman depan sebelum isi (tanpa harakat): الإهداء، الشكر والتقدير، الملخص/المستخلص
DEPAN = re.compile(rf"^(?:{IHDA.pattern})$|شكر|تقدير|^(?:ال)?ملخص|مستخلص")


def batas_kepala(blok, awal_isi, bagian):
    """Kepala halaman (@kepala, juga kotak dan @templat) hanya di halaman isi (المقدمة s.d. الخاتمة); halaman depan
    (الإهداء، الشكر، الملخص، فهرس @maudhuat_letak: awal) dan belakang (المصادر، الملاحق sesudahnya، الفهارس) hanya bernomor
    di tengah kaki. Kembalikan (indeks blok awal isi bila ada halaman depan sebelumnya, None kalau isi mulai dari halaman
    pertama sesudah sampul; `bagian` dengan butir pertama yang tidak di depan bertanda «belakang»: bagian Word baru).
    Awal isi = المقدمة (awal_isi), atau judul #K/#F pertama yang bukan DEPAN."""
    mulai = awal_isi
    if mulai is None:
        i_r = next((i for i, b in enumerate(blok) if b["k"] == "R"), len(blok))  # sesudah #R = الملاحق (@malahiq: akhir)
        mulai = next((i for i, b in enumerate(blok[:i_r]) if b["k"] in JUDUL_BAB
                      and not DEPAN.search(norma.HARAKAT.sub("", b["judul"]).strip())), None)
    if mulai is not None and not any(b["k"] != "H" for b in blok[:mulai]):
        mulai = None
    i = next((i for i, b in enumerate(bagian) if not b.get("awal")), None)
    return mulai, [{**b, "belakang": True} if j == i else b for j, b in enumerate(bagian)]


def rencana_cetak(d):
    """Rencana cetak bahan `d`: tiap keputusan «apa yang dicetak dan di mana» sebagai nilai jadi. rakit.ps1 hanya
    membacanya (di sana tidak ada aturan, bawaan, atau pengurai @data sendiri); perkiraan_halaman juga. Seluruhnya
    turunan isi bahan yang lain, jadi tidak ikut sidik_cetak, dan `potong` menyusunnya lagi untuk potongannya.
    sampul = model sampulnya; buang_sampul = potongan --fasl tanpa sampul: dokumen
    tetap berangkat dari model itu, lalu halaman sampulnya dibuang."""
    meta, blok = d["meta"], d["blok"]
    buang_sampul = bool(meta.get("tanpa_sampul"))
    sampul = "templat" if meta.get("templat") else meta.get("sampul")
    judul = meta.get("judul", "")
    sub = SUBJUDUL.match(judul)
    halaman_baru, nomor_satu = awal_halaman(blok, meta)
    awal_isi = next((i for i, b in enumerate(blok) if b["k"] in JUDUL_FIHRIS and norma.HARAKAT.sub("", b["judul"]) == MUQADDIMAH), None)
    bagian = bagian_akhir(d)
    # @maudhuat_letak: awal = فهرس الموضوعات ditulis tepat sebelum blok ini: المقدمة, atau #K مقدمة/تمهيد pertama, atau #F
    # pertama, atau judul pertama. Hanya kalau فهرس itu memang dicetak (bukan @tanpa: maudhuat, bukan potongan --fasl
    # yang tanpa فهرس), dan judul sesudahnya selalu mulai halaman baru
    maudhuat_awal = None
    if meta.get("maudhuat_letak") == "awal" and any(b["jenis"] == "maudhuat" for b in bagian):
        judul_i = [i for i, b in enumerate(blok) if b["k"] in JUDUL_FIHRIS]
        maudhuat_awal = next(
            (i for i in ([awal_isi] if awal_isi is not None else [])
             + [i for i in judul_i if blok[i]["k"] == "K" and re.search(r"مقدم[ةه]|تمهيد", norma.HARAKAT.sub("", blok[i]["judul"]))]
             + [i for i in judul_i if blok[i]["k"] == "F"] + judul_i), None)
    if maudhuat_awal is not None:
        bagian = [{**b, "awal": True} if b["jenis"] == "maudhuat" else b for b in bagian]
        if maudhuat_awal != nomor_satu and maudhuat_awal not in halaman_baru:
            halaman_baru = sorted([*halaman_baru, maudhuat_awal])
        if awal_isi is None:  # halaman isi (HALAMAN_ISI) mulai sesudah فهرس itu, bukan dari halaman pertama
            awal_isi = maudhuat_awal
    pembuka = None  # @ayat_pembuka: satu halaman ayat sesudah sampul (dan sesudah basmalah), tanpa nomor
    if meta.get("ayat_pembuka") and not buang_sampul:
        try:
            t, s, a = ayat(meta["ayat_pembuka"].translate(ANGKA_LATIN))
            pembuka = {"t": t, "rujukan": f"[{SURAH[s - 1]}: {a}]"}
        except TandaRusak:  # sudah GAGAL di _cek_sampul
            pass
    fmt = format_cetak(d["format"])
    # @judul_fasl: pemisah = judul #F di halaman sendiri; isi sesudahnya (blok berikutnya selain #H) mulai halaman baru
    pemisah = halaman_pemisah(blok) if meta.get("judul_fasl") in JUDUL_FASL_PEMISAH else {}
    for i in map(int, pemisah):
        j = next((j for j in range(i + 1, len(blok)) if blok[j]["k"] != "H"), None)
        if j is not None and blok[j]["k"] != "R" and j not in halaman_baru:
            halaman_baru = sorted([*halaman_baru, j])
    mulakhas = [(i, j) for i, b in enumerate(blok)
                if b["k"] == "K" and MULAKHAS.match(j := norma.HARAKAT.sub("", b["judul"]))]
    kepala_mulai, bagian = batas_kepala(blok, awal_isi, bagian)
    return {"format": fmt, "sampul": sampul,
            "kepala": "templat" if meta.get("templat") else meta.get("kepala"),  # bentuknya: mesin/kepala.ps1
            "kepala_mulai": kepala_mulai,
            # baris المصادر tanpa huruf Arab dicetak kiri-ke-kanan (rata kiri), nomornya tetap di kanan
            "pustaka_ltr": [pustaka_asing(p) for p in d.get("pustaka", [])],
            "logo_berwarna": sampul == "qism" and not buang_sampul and meta.get("logo") == "berwarna",
            "judul_sampul": [sub.group(1).strip(), sub.group(2).strip()] if sub else [judul, ""],
            "buang_sampul": buang_sampul, "basmalah": meta.get("basmalah") in ("ya", "utsmani") and not buang_sampul,
            # @basmalah: utsmani = teks Al-Fatihah:1 huruf mushaf, bukan ligatur ﷽ Arabic Typesetting
            "basmalah_utsmani": ayat("1:1")[0] if meta.get("basmalah") == "utsmani" and not buang_sampul else None,
            "abjad": meta.get("nomor") in ("abjad", "mukadimah"), "nomor_satu": nomor_satu, "halaman_baru": halaman_baru,
            "awal_isi": awal_isi, "maudhuat_awal": maudhuat_awal, "ayat_pembuka": pembuka,
            "judul_kanan": [t for t in daftar(meta, "judul_kanan") if t != GAYA["judul_kanan"][0]],
            "susun": _sampul_susun(meta, sub, judul, sampul) if sampul in SAMPUL_SUSUN else None,
            # @judul_fasl: dua_baris dan kotak = judul #F dua baris (kotak: baris kedua lebih kecil); pemisah: halaman_pemisah
            "judul_fasl": meta.get("judul_fasl"),
            "judul_dua_baris": judul_dua_baris(blok) if meta.get("judul_fasl") in ("dua_baris", "kotak") else {},
            "pemisah": pemisah,
            # @tamma: halaman penutup «تمّ بحمد الله وتوفيقه» sesudah الفهارس (halaman terakhir), tanpa nomor
            "tamma": meta.get("tamma") == "ya",
            # @pustaka_gaya: judul_tebal: baris المصادر yang tercetak (urutannya = d["pustaka"], urut judul)
            "pustaka_butir": [f"**{p.replace('**', '').replace('__', '').strip()}**" if adalah_mushaf(p)
                              else pustaka_judul_dulu(p) or p for p in d.get("pustaka", [])]
            if meta.get("pustaka_gaya") == "judul_tebal" else None,
            "ihda": _jarak_ihda(blok, fmt) if meta.get("ihda") == "tengah" else {},
            "jarak_sub": _jarak_sub(blok, fmt),
            "mufradat": baris_mufradat(blok),
            "mulakhas": {
                "spasi": [i for i, _ in mulakhas],
                "berjarak": [i for i, j in mulakhas if not MULAKHAS_ASING.search(j)],
            },
            "bagian": bagian}


# baris معاني المفردات sesudah bait: «الكلمة: معناها.» — label pendek, makna pendek (boleh «وقيل: …»)
MUFRADAT = re.compile(r"^[^:.،؛]{1,30}:\s*.{1,140}$")


def baris_mufradat(blok):
    """[indeks paragraf] baris معاني المفردات: paragraf pendek «الكلمة: معناها.» tepat sesudah bait #V atau sesudah baris
    مفردات lain. rakit.ps1 menempelkannya ke paragraf sesudahnya (KeepWithNext), jadi bait, daftar مفردات-nya, dan awal
    syarahnya tidak terpotong antarhalaman (butir terakhir daftar tidak tertinggal sendirian di halaman berikutnya)."""
    hasil = []
    for i, b in enumerate(blok):
        if b["k"] != "P" or not i or not (blok[i - 1]["k"] == "V" or (hasil and hasil[-1] == i - 1)):
            continue
        teks = "".join(r.get("t", "") for r in b.get("runs", [])).strip()
        if MUFRADAT.match(teks):
            hasil.append(i)
    return hasil


def _jarak_sub(blok, fmt):
    """{indeks judul #B/#M: jarak di atasnya (pt)} untuk judul yang menyusul isi (bukan langsung di bawah judul lain):
    jarak_sebelum_sub profil, supaya mabhath baru tidak rapat dengan paragraf terakhir mabhath sebelumnya. Judul lain
    (dan #B/#M tepat di bawah #K/#F/#B) memakai jarak bawaan 6 pt di rakit.ps1."""
    if not fmt or fmt["jarak_sebelum_sub"] == BAWAAN_FORMAT["jarak_sebelum_sub"]:
        return {}
    return {str(i): fmt["jarak_sebelum_sub"] for i, b in enumerate(blok)
            if b["k"] in ("B", "M") and i and blok[i - 1]["k"] not in ("K", "F", "B", "M")}


def _jarak_ihda(blok, fmt):
    """@ihda: tengah -> {indeks paragraf الإهداء: celah di atasnya (pt)}. Celah = jarak paragraf profil, paling sedikit
    satu baris kosong matan (tinggi satu baris Traditional Arabic ±1,5 × ukurannya); paragraf tepat di bawah judulnya
    dikurangi jarak_judul yang sudah ada di bawah judul itu."""
    celah = max(fmt["jarak_paragraf"], round(1.5 * fmt["matan"])) if fmt else 0
    return {str(i): max(0, celah - fmt["jarak_judul"]) if fmt and blok[i - 1]["k"] == "K" else celah
            for i in paragraf_ihda(blok)}


SAMPUL_SUSUN = ("tengah", "kop", "tanpa_kop")  # sampul yang disusun rakit.ps1 baris demi baris (_sampul_susun), tanpa templat
TAHUN_SAMPUL = "{tahun}"  # diganti rakit.ps1 dengan tahun sampul (@tahun, atau tahun ajaran hijriah yang dihitung di sana)


def _isi(meta, k):
    """Nilai @k yang tercetak: kosong atau «-» = tidak ada."""
    v = meta.get(k, "").strip()
    return "" if v == "-" else v


def _sampul_susun(meta, sub, judul, model):
    """Sampul yang disusun rakit.ps1 tanpa templat: {logo, baris}. Tiap baris {t, uk (pt), atas (pt di atasnya), jenis
    (judul = huruf judul sampul, dikecilkan kalau tidak muat; lentur = sisa tinggi halaman dibagi ke jarak di atas
    baris-baris ini; kop = baris kop bertingkat di kanan atas), celah (jaraknya dipendekkan dulu kalau sampul meluap),
    hias (huruf judul hias rakit.ps1, PT Bold Heading)}.
    Semua tebal. tengah = model خطة dosen المعهد (logo berwarna di atas; ukuran dan jarak dari contoh PDF-nya; @jenis,
    @nim, @fasl, @jabatan, @sifat tidak tercetak); kop dan tanpa_kop: lihat SAMPUL. Judul: per « // » di @judul_sampul
    (tengah), atau @judul dengan sub-judul « - …» baris sendiri."""
    judul_baris = ([PISAH_SUB.sub("", b).strip() for b in meta["judul_sampul"].split("//") if PISAH_SUB.sub("", b).strip()]
                   if meta.get("judul_sampul")
                   else [sub.group(1).strip(), sub.group(2).strip()] if sub else [judul])
    qism = [b.strip() for b in meta.get("qism", "").split("//") if b.strip() not in ("", "-")]  # «-» = tanpa baris qism
    musyrif, jabatan, nim, jenis = _isi(meta, "musyrif"), _isi(meta, "jabatan"), _isi(meta, "nim"), _isi(meta, "jenis")
    talib = "إعداد الطالبة" if meta.get("thalibah") == "ya" else "إعداد الطالب"

    def b(t, uk, atas, jenis=""):
        return {"t": t, "uk": uk, "atas": atas, "jenis": jenis, "celah": False, "hias": False}
    if model == "tengah":  # jarak baris ke baris di contoh 33,6 pt = tinggi baris TA 18 + 6 pt; celah = satu baris lagi
        baris = [{**b(LEMBAGA_TENGAH, 18, 39), "celah": True}, *(b(q, 18, 6) for q in qism), *(b(j, 18, 6, "judul") for j in judul_baris),
                 b(f"{talib}: {meta.get('nama', '')}", 18, 6), *([b(f"إشراف: {musyrif}", 18, 6)] if musyrif else []),
                 b(TAHUN_SAMPUL, 18, 6)]
        baris[1] = {**baris[1], "atas": 6 + 33.6, "celah": True}
        return {"logo": True, "baris": baris}
    utama = [{**b(judul_baris[0], 32, 0, "judul"), "hias": True}, *(b(j, 20, 6, "judul") for j in judul_baris[1:]),
             *([b(jenis, 16, 14)] if jenis else [])]
    pelajar = [b(f"{talib}:" if model == "kop" else talib, 16, 0), b(meta.get("nama", ""), 20, 4),
               *([b(f"الرقم الجامعي: {nim}", 16, 2)] if nim else [])]
    pembimbing = [b("إشراف:" if model == "kop" else "إشراف", 16, 24), b(musyrif, 20, 4),
                  *([b(jabatan, 16, 2)] if jabatan else [])] if musyrif else []
    if model == "kop":  # kop bertingkat kanan atas, lalu isi bertumpuk dengan jarak tetap (tanpa (٠٣٢): kode resmi kampus lain)
        kop = [{**b(t, 14, 0 if not i else 2), "jenis": "kop"} for i, t in enumerate([*KOP, *(qism or [QISM])])]
        baris = [*kop, {**utama[0], "atas": 60}, *utama[1:], {**pelajar[0], "atas": 40}, *pelajar[1:], *pembimbing,
                 b(f"العام الجامعي {TAHUN_SAMPUL}", 18, 40)]
    else:  # tanpa_kop: judul di atas, إعداد/إشراف di tengah, kampus dan tahun di bawah; sisa halaman ke dua jarak lentur
        bawah = [b(t, 16, 4) for t in [*KOP_BAWAH, *(qism or [QISM]), TAHUN_SAMPUL]]
        baris = [{**utama[0], "atas": 24}, *utama[1:], {**pelajar[0], "jenis": "lentur"}, *pelajar[1:], *pembimbing,
                 {**bawah[0], "jenis": "lentur"}, *bawah[1:]]
    return {"logo": False, "baris": baris}


def _bahan(ctx, blok, profil, quran, sumber, sidik_naskah):
    """Bahan rakit; blok = blok seperti dicetak."""
    d = {"meta": ctx.meta, "format": profil, "blok": blok, "catatan": ctx.catatan,
         "ayat": ctx.ayat_idx, "hadits": [h for h in ctx.hadits_idx if not h.get("atsar")],
         "atsar": [{k: v for k, v in h.items() if k != "atsar"} for h in ctx.hadits_idx if h.get("atsar")],
         **ctx.fihris_nama, "syir": ctx.syir_idx, "pustaka": ctx.pustaka,
         "quran": bool(quran), "tautan": TAUTAN.pattern, "latin": LATIN.pattern, "sumber": sumber, "naskah_sha256": sidik_naskah}
    d["cetak"] = rencana_cetak(d)
    return d


def sidik_cetak(d):
    """SHA-256 bahan rakit tanpa yang tidak mengubah PDF (sidik naskah, kunci yang hanya dibaca `cek`, nomor baris
    naskah tiap blok) dan tanpa rencana cetak (turunan isi yang lain): naskah yang hanya berubah di situ tetap punya
    hasil rakit TERKINI (tahap.hasil), jadi tidak perlu dirakit ulang. Nomor baris (`n`) hanya untuk pesan `cek`;
    rakit.ps1 tidak membacanya."""
    isi = {k: v for k, v in d.items() if k not in ("naskah_sha256", "cetak")}
    isi["meta"] = {k: v for k, v in d["meta"].items() if k not in HANYA_CEK}
    # gambar #G: yang dicetak isi berkasnya (sha256), bukan letak foldernya di komputer ini
    isi["blok"] = [{k: v for k, v in b.items() if k not in ("n", "berkas")} for b in d["blok"]]
    return hashlib.sha256(json.dumps(isi, ensure_ascii=False, sort_keys=True).encode("utf8")).hexdigest()


def alamat_bahan(folder):
    """Alamat bahan yang ditulis `cek`: satu per jalur bahts lengkap, termasuk dua folder bernama akhir sama."""
    kunci = os.path.normcase(str(Path(folder).resolve()))
    sidik = hashlib.sha256(kunci.encode("utf8")).hexdigest()
    return Path(__file__).parent / "_tmp" / (sidik + ".json")


def tulis_bahan(d, keluar):
    """Bahan rakit JSON."""
    with sementara(keluar) as part:
        part.write_text(json.dumps(d, ensure_ascii=False), encoding="utf8")


def _tanpa_bukti(ctx):
    """Awal teks tiap catatan kaki tanpa bukti. Rujukan kitab tanpa bukti sudah jadi GAGAL atau perhatian: daftar ini
    sisanya (catatan penjelasan, <<luar>>)."""
    fn_teks = [(c, "".join(r.get("t", "") for r in c["runs"])) for c in ctx.catatan if not c.get("matan")]
    return [norma.HARAKAT.sub("", t)[:60] for c, t in fn_teks if c["bukti"] == 0 and not c["pdf"] and not c.get("wq")
            and not t.startswith(BUKAN_RUJUKAN) and (c["luar"] or not rujukan_halaman(t))]


def kepala_tanpa_bukti(n):
    return f"catatan kaki tanpa bukti (selain rujukan ayat dan rujukan kitab di atas): {n}"


def _laporan(ctx, n_matan, n_fn, fn_tanpa, sidik_naskah, sidik_isi):
    """Baris laporan `cek`: ringkasan, GAGAL, perhatian, catatan kaki tanpa bukti."""
    blok, pustaka, catatan, ayat_idx = ctx.blok, ctx.pustaka, ctx.catatan, ctx.ayat_idx
    hadits_idx, galat, perhatian, folder = ctx.hadits_idx, ctx.galat, ctx.perhatian, ctx.folder
    aktif = [c for c in catatan if not c.get("matan")]
    n_bukti = sum(c["bukti"] for c in aktif)
    n_luar = sum(c["luar"] for c in aktif)  # disebut di ringkasan: tanda yang bisa menyembunyikan kutipan karangan
    n_pdf = sum(c["pdf"] for c in aktif)
    n_wq = sum(c.get("wq", 0) for c in aktif)
    lap = [f"blok={len(blok)} | kata matan={n_matan} | catatan kaki={len(aktif)} ({n_fn} kata) | ayat={len(ayat_idx)} | hadits={len(hadits_idx)} | pustaka={len(pustaka)}",
           f"bukti dicek ke Shamela lokal: {n_bukti}{f' | ditunjuk di PDF (bukan bukti): {n_pdf}' if n_pdf else ''}"
           f"{f' | <<{LUAR}>> (tidak dicek mesin): {n_luar}' if n_luar else ''}"
           f"{f' | Waqfeya <<w…>> (lafaz dinilai pemeriksa dari scan): {n_wq}' if n_wq else ''} | GAGAL: {len(galat)}"]
    # kitab yang belum diunduh membuat tiap buktinya GAGAL: satu perintah untuk semuanya, sebelum daftar panjangnya
    belum = list(dict.fromkeys(ctx.belum_diunduh))
    if belum:
        rel = folder.resolve().relative_to(HERE.parent.resolve()).as_posix()
        lap.append(f"  → {len(belum)} kitab belum diunduh; unduh semuanya sekaligus: "
                   + perintah("ambil " + (f'"{rel}"' if " " in rel else rel)))
    lap += [f"  ✗ {g}" for g in galat]
    lap.append(f"{KEPALA_PERHATIAN}: {len(perhatian)}")
    lap += [f"  ! {ctx.kode[p]} {p}" for p in perhatian]
    if ctx.diterima:
        lap.append(f"perhatian diterima (alasan di {RISET}, dinilai pemeriksa): {len(ctx.diterima)}")
        lap += [f"  ✓ {k} {p}\n      alasan: {alasan}" for k, p, alasan in ctx.diterima]
    lap.append(kepala_tanpa_bukti(len(fn_tanpa)))
    lap += [f"  - {f}" for f in fn_tanpa]
    lap.append(produk.baris(produk.CETAK, sidik_isi))
    lap.append(produk.baris(produk.NASKAH, sidik_naskah))
    return lap


def cetak(hasil, jalur, jejak=False):
    """Laporan `cek` ke layar: baris laporan, petunjuk untuk teks yang tidak ketemu (jejak: dicari di kitab lain yang
    sudah diunduh), lalu perkiraan halaman. jalur = bahts seperti diketik pemakai, untuk perintah yang disarankan."""
    print("\n".join(hasil.laporan))
    tertolak = hasil.ctx.tertolak
    if tertolak:
        if jejak:
            print("petunjuk dari kitab lain (hanya petunjuk, bukan bukti; putusan tetap milik `cek`):")
            import jejak as cari_jejak  # bendera `jejak` menutupi nama modulnya
            print("\n".join(cari_jejak.jejak(tertolak)))
        else:
            n = len({norma.padat(t) for _, t in tertolak})
            print(f"{n} teks tidak ditemukan di kitab yang dirujuk; cari di kitab lain yang sudah diunduh: "
                  + perintah(f'cek "{jalur}" --jejak'))
    elif jejak:
        print("jejak: tidak ada bukti yang gagal «teks TIDAK KETEMU di kitab».")
    n = perkiraan_halaman(hasil.bahan)
    if n:
        isi, total, rinci = n
        print(f"perkiraan halaman isi (المقدمة s.d. الخاتمة): ±{isi}; seluruh PDF: ±{total} ("
              + ", ".join(f"{k} {v}" for k, v in rinci.items()) + f", isi {isi}) "
              "(kasar, dari jumlah kata; angka pasti = HALAMAN_ISI dan HALAMAN sesudah `rakit`)")
