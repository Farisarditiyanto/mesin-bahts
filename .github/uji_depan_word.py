# SPDX-License-Identifier: AGPL-3.0-or-later
"""Halaman depan lewat `cek`, `rakit`, dan Word asli: `@ayat_pembuka` (halaman ayat sesudah sampul, tanpa nomor),
`@maudhuat_letak: awal` (فهرس الموضوعات sesudah الإهداء, tepat sebelum المقدمة, nomor halamannya benar), dan
`@tanpa: anzhur` («انظر:» di catatan kaki tidak tercetak, naskah tetap menulisnya untuk `cek`). Bagian `cek` jalan di
mana saja; bagian Word dilewati di runner tanpa Word. Semua bahan di TEMP."""
import re, sys, tempfile
from pathlib import Path

import pymupdf

from bantu import bahts, salin_mesin, tanpa_word

KEPALA = "@judul: اختبار الصفحات الأولى\n@nama: طالب\n@berkas: uji\n@tanpa: hadits, anzhur\n@minimal_halaman: 0\n@nomor: mukadimah\n"
ISI = ("#K الإهداء\nإلى والديّ الكريمين.\n"
       "#K المقدمة\nهذا نص المقدمة.\n"
       "#F الفصل الأول: الموضوع\nقال الله تعالى: {Q:1:2}[^سورة الفاتحة، آية: ٢.].\n"
       "{A:mawdu}وهذا كلام الباحث[^انظر: كتاب ما، ص٥؛ وانظر: كتاب آخر، ص٧.]، كما في المقدمة[^انظر: ص{P:mawdu} من هذا البحث.].\n"
       "#K الخاتمة\nهذه الخاتمة.\n#R المصادر\nالقرآن الكريم.\n")
RISET = "tafsir 1:2\ncari الموضوع | uji\n"


def tulis(akar, nama, kepala, isi=ISI):
    f = akar / nama
    f.mkdir()
    (f / "naskah.txt").write_text(kepala + isi, encoding="utf8")
    (f / "riset.txt").write_text(RISET, encoding="utf8")
    return f


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    with tempfile.TemporaryDirectory(prefix="bahts-depan-word-") as t:
        akar = Path(t)
        salin_mesin(akar)
        # nilai yang salah = GAGAL, bukan diabaikan diam-diam
        for nama, baris, pesan in (("ayat_salah", "@ayat_pembuka: 115:1\n", "@ayat_pembuka"),
                                   ("letak_salah", "@maudhuat_letak: tengah\n", "@maudhuat_letak"),
                                   ("tahun_salah", "@tahun: ٢٠٢٦\n", "@tahun")):
            tulis(akar, nama, KEPALA + baris)
            r = bahts(akar, "cek", nama)
            assert r.returncode != 0 and pesan in r.stdout, r.stdout + r.stderr
        print("lolos cek halaman depan: @ayat_pembuka, @maudhuat_letak, dan @tahun yang salah = GAGAL")
        f = tulis(akar, "depan", KEPALA + "@ayat_pembuka: 12:2\n@maudhuat_letak: awal\n@tahun: ١٤٤٨ - ٢٠٢٦\n")
        r = bahts(akar, "cek", "depan")
        assert r.returncode == 0 and "GAGAL: 0" in r.stdout, r.stdout + r.stderr
        assert "sampul 2" in r.stdout, r.stdout   # perkiraan halaman: sampul + halaman ayat
        print("lolos cek halaman depan: naskah dengan ketiga kunci lolos, halaman ayat ikut perkiraan")
        if alasan := tanpa_word():
            print("lewati uji halaman depan Word: " + alasan)
            return
        r = bahts(akar, "rakit", "depan", batas=1800)
        assert r.returncode == 0, r.stdout + r.stderr
        doc = pymupdf.open(f / "uji.pdf")
        hal = [p.get_text() for p in doc]
        doc.close()
        # hal 1 sampul, hal 2 ayat (tanpa nomor), hal 3 الإهداء (أ), hal 4 فهرس (ب), hal 5 المقدمة (١)
        assert "يوسف" in hal[1] and "الإهداء" not in hal[1], hal[1]
        # @tahun hijriah - masehi: «١٤٤٨هـ – ٢٠٢٦م» di sampul (teks PDF kanan-ke-kiri bisa terbaca terbalik)
        assert re.search("٢٠٢٦|٦٢٠٢", hal[0]) and re.search("١٤٤٨|٨٤٤١", hal[0]), hal[0]
        assert not re.search(r"[٠-٩0-9]", hal[1].replace("٢", "")), f"halaman ayat bernomor: {hal[1]!r}"
        assert "الإهداء" in hal[2] and "فهرس الموضوعات" in hal[3] and "المقدمة" in hal[4], hal[:5]
        assert "فهرس الموضوعات" not in "".join(hal[5:]), "فهرس الموضوعات tercetak lagi di belakang"
        baris_mq = next(x for x in hal[3].split("\n") if "المقدمة" in x)
        assert "١" in baris_mq or "1" in baris_mq, f"nomor halaman المقدمة di فهرس: {baris_mq!r}"
        semua = "".join(hal)
        # «انظر:» hilang, pemisah «؛» tetap berspasi, rujukan silang «انظر: ص…» tetap utuh
        assert "كتاب ما" in semua and "كتاب آخر" in semua, semua
        assert semua.count("انظر") == 1 and "من هذا البحث" in semua, "«انظر:» masih tercetak, atau rujukan silang kehilangan katanya"
        assert "؛كتاب" not in semua, "spasi sesudah «؛» ikut terbuang"
        print(f"lolos halaman depan Word: ayat di hal 2, فهرس di hal 4 sebelum المقدمة, «انظر:» tidak tercetak ({len(hal)} halaman)")
        # tanpa الإهداء dan tanpa @nomor: المقدمة tetap mulai halaman baru sesudah فهرس di depan
        tulis(akar, "polos", "@judul: اختبار\n@nama: طالب\n@berkas: uji\n@tanpa: hadits\n@minimal_halaman: 0\n@maudhuat_letak: awal\n",
              "#K المقدمة" + ISI.split("#K المقدمة", 1)[1])
        r = bahts(akar, "rakit", "polos", batas=1800)
        assert r.returncode == 0 and "halaman kosong" not in r.stdout, r.stdout + r.stderr
        doc = pymupdf.open(akar / "polos" / "uji.pdf")
        hal = [p.get_text() for p in doc]
        doc.close()
        assert "فهرس الموضوعات" in hal[1] and "هذا نص المقدمة" not in hal[1] and "هذا نص المقدمة" in hal[2], hal[:3]
        # @tanpa: maudhuat + @maudhuat_letak: awal: tidak ada halaman kosong pengganti فهرس
        tulis(akar, "tanpa_fihris", KEPALA.replace("@tanpa: hadits", "@tanpa: hadits, maudhuat") + "@maudhuat_letak: awal\n")
        r = bahts(akar, "rakit", "tanpa_fihris", batas=1800)
        assert r.returncode == 0 and "halaman kosong" not in r.stdout, r.stdout + r.stderr
        print("lolos halaman depan Word: المقدمة mulai halaman baru sesudah فهرس; @tanpa: maudhuat tanpa halaman kosong")
        # فهرس depan yang baris terakhirnya ±1 pt dari dasar halaman (9 فصل × 1 مبحث, temuan pemeriksa): paragraf sesudahnya
        # dulu tumpah jadi halaman kosong sebelum المقدمة; dengan dan tanpa @nomor (pemisah bagian Word)
        kalimat = "ويظهر للباحث أن هذا الباب من أبواب التوحيد مهم، وأن فهمه على وجهه يعين طالب العلم على تصور المسائل. " * 3
        isi = ("#K الإهداء\nنص قصير.\n#K الشكر والتقدير\nنص قصير.\n#K المقدمة\n" + kalimat + "\n"
               + "".join(f"#F الفصل {f}: الموضوع {f}\n#B المبحث 1 من الفصل {f}\n{kalimat}\n" for f in range(1, 10))
               + "#K الخاتمة\n" + kalimat + "\n#R المصادر\nالقرآن الكريم.\n")
        x91 = ("@judul: اختبار الصفحات الأولى\n@nama: طالب\n@berkas: uji\n@minimal_halaman: 0\n@basmalah: ya\n"
               "@ayat_pembuka: 12:2-3\n@maudhuat_letak: awal\n@tanpa: anzhur\n")
        for nama, kepala in (("pas", x91 + "@nomor: mukadimah\n"), ("pas_polos", x91)):
            tulis(akar, nama, kepala, isi)
            r = bahts(akar, "rakit", nama, batas=1800)
            assert r.returncode == 0 and "halaman kosong" not in r.stdout, f"{nama}: " + r.stdout + r.stderr
            doc = pymupdf.open(akar / nama / "uji.pdf")
            hal = [p.get_text() for p in doc]
            doc.close()
            i = next(k for k, h in enumerate(hal) if "فهرس الموضوعات" in h)
            assert "ويظهر للباحث" in hal[i + 1] and "فهرس" not in hal[i + 1], f"{nama}: halaman sesudah فهرس: {hal[i + 1][:200]!r}"
        print("lolos halaman depan Word: فهرس depan yang pas satu halaman tidak menyisakan halaman kosong (dengan/tanpa @nomor)")


if __name__ == "__main__":
    utama()
