# SPDX-License-Identifier: AGPL-3.0-or-later
"""Halaman depan lewat `cek`, `rakit`, dan Word asli: `@ayat_pembuka` (halaman ayat sesudah sampul, tanpa nomor),
`@maudhuat_letak: awal` (فهرس الموضوعات sesudah الإهداء, tepat sebelum المقدمة, nomor halamannya benar),
`@tanpa: anzhur` («انظر:» di catatan kaki tidak tercetak, naskah tetap menulisnya untuk `cek`), dan `@sampul: tengah`
dengan `@judul_fasl: dua_baris` dan `@ihda: tengah`. Bagian `cek` jalan di
mana saja; bagian Word dilewati di runner tanpa Word. Semua bahan di TEMP."""
import re, struct, sys, tempfile, zipfile
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
        tulis(akar, "tahun_dua", KEPALA + "@tahun: ١٤٤٨/١٤٤٩\n")  # dua tahun hijriah satu tahun ajaran
        r = bahts(akar, "cek", "tahun_dua")
        assert "@tahun" not in r.stdout, r.stdout + r.stderr
        print("lolos cek halaman depan: @tahun dua tahun hijriah «١٤٤٨/١٤٤٩»")
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
        sampul_tengah(akar)
        bait_menempel(akar)
        jarak_mabhath(akar)
        jakarta_mahad_dan_mulakhas(akar)


def bait_menempel(akar):
    """Bait #V terakhir dari deretan bait menempel ke paragraf sesudahnya (KeepWithNext): bait di baris akhir halaman
    tidak terpisah dari syarahnya. Bait yang disusul bait lagi tidak menempel, supaya deretan panjang (النص) boleh
    terpotong antarhalaman. Dicek di XML .docx: bait kedua ber-<w:keepNext/>, bait pertama dan syarah tidak."""
    isi = ISI.replace("#K الخاتمة\n", "وقال الشاعر في ذلك:\n#V هل غادر الشعراء من متردم ... أم هل عرفت الدار بعد توهم\n"
                      "#V يا دار عبلة بالجواء تكلمي ... وعمي صباحا دار عبلة واسلمي\n"
                      "وهذا شرح البيت الذي يأتي بعده.\n"
                      "وقال أيضًا:\n#V بيت ثالث للاختبار هنا ... وشطره الثاني هنا\n"
                      "وقال في موضع آخر:\n#V بيت رابع للاختبار هنا ... وشطره الثاني هنا\n"
                      "الكلمة: معناها الأول.\nالأخرى: معناها الثاني، وقيل: غيره.\nوهذا شرح أخير.\n#K الخاتمة\n")
    tulis(akar, "bait", KEPALA, isi)
    r = bahts(akar, "rakit", "bait", batas=1800)
    assert r.returncode == 0, r.stdout + r.stderr
    xml = zipfile.ZipFile(akar / "bait" / "uji.docx").read("word/document.xml").decode("utf8")
    para = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
    teks = lambda p: "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
    bait = next(p for p in para if "بالجواء" in teks(p))
    syarah = next(p for p in para if "شرح البيت" in teks(p))
    assert "<w:keepNext/>" in bait, "bait #V tidak menempel ke syarahnya (tanpa keepNext)"
    assert "<w:keepNext/>" not in syarah, "paragraf syarah ikut menempel ke paragraf sesudahnya"
    awal = next(p for p in para if "متردم" in teks(p))
    assert "<w:keepNext/>" not in awal, "bait yang disusul bait lagi ikut menempel: deretan bait pindah utuh antarhalaman"
    ketiga = next(p for p in para if "ثالث للاختبار" in teks(p))
    keempat = next(p for p in para if "رابع للاختبار" in teks(p))
    assert "<w:keepNext/>" not in ketiga, "bait yang disusul pengantar bait lain («…:») ikut menempel: poin-poin berbait jadi satu rantai"
    assert "<w:keepNext/>" in keempat, "bait terakhir tidak menempel ke syarahnya"
    # baris معاني المفردات sesudah bait menempel satu sama lain dan ke syarahnya; syarahnya sendiri tidak
    for kata in ("معناها الأول", "معناها الثاني"):
        assert "<w:keepNext/>" in next(p for p in para if kata in teks(p)), f"baris مفردات «{kata}» tidak menempel: daftar bisa terpotong"
    assert "<w:keepNext/>" not in next(p for p in para if "شرح أخير" in teks(p)), "syarah sesudah مفردات ikut menempel"
    print("lolos bait menempel: bait terakhir ber-keepNext, bait sebelumnya dan syarah tidak")



def jarak_mabhath(akar):
    """tatbiqi_16_berjarak: judul #B yang menyusul paragraf berjarak 24 pt di atasnya (mabhath baru tidak rapat dengan
    paragraf sebelumnya); #B tepat di bawah #F tetap 6 pt. Dicek di XML .docx (w:spacing w:before, dalam 1/20 pt)."""
    isi = ISI.replace("#K الخاتمة\n", "#F الفصل الثاني: الفصل للاختبار\n#B المبحث الأول: مبحث أول للاختبار\n"
                      "وهذه فقرة في المبحث الأول.\n#B المبحث الثاني: مبحث ثان للاختبار\nوهذه فقرة في المبحث الثاني.\n#K الخاتمة\n")
    tulis(akar, "mabhath", KEPALA + "@format: tatbiqi_16_berjarak\n", isi)
    r = bahts(akar, "rakit", "mabhath", batas=1800)
    assert r.returncode == 0, r.stdout + r.stderr
    xml = zipfile.ZipFile(akar / "mabhath" / "uji.docx").read("word/document.xml").decode("utf8")
    para = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
    teks = lambda p: "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
    atas = lambda kata: int((re.search(r'<w:spacing[^>]*w:before="(\d+)"', next(p for p in para if kata in teks(p))) or [0, 0])[1])
    assert atas("مبحث ثان للاختبار") == 480, f"jarak sebelum #B sesudah paragraf: {atas('مبحث ثان للاختبار') / 20} pt, harusnya 24"
    assert atas("مبحث أول للاختبار") == 120, f"jarak sebelum #B di bawah #F: {atas('مبحث أول للاختبار') / 20} pt, harusnya 6"
    print("lolos jarak mabhath: #B sesudah paragraf 24 pt, #B di bawah #F 6 pt")


def baris_pdf(hal):
    """Baris teks satu halaman PDF: (teks, tengah x, huruf span pertama), urut dari atas."""
    hasil = []
    for b in hal.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            teks = "".join(s["text"] for s in ln["spans"]).strip()
            if teks:
                hasil.append((teks, (ln["bbox"][0] + ln["bbox"][2]) / 2, ln["spans"][0]["font"], ln["bbox"][1]))
    return sorted(hasil, key=lambda x: x[3])


def tengah_baris(hal):
    """Tengah x tiap baris cetak satu halaman: span sebaris (garis dasar sama) digabung, karena pymupdf bisa memecah
    satu baris kanan-ke-kiri jadi beberapa baris (mis. «م» di ujung tahun «١٤٤٨هـ – ٢٠٢٦م»)."""
    rentang = {}
    for b in hal.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            for sp in ln["spans"]:
                if sp["text"].strip():
                    y = round(sp["origin"][1])
                    a, z = rentang.get(y, (sp["bbox"][0], sp["bbox"][2]))
                    rentang[y] = (min(a, sp["bbox"][0]), max(z, sp["bbox"][2]))
    return {y: (a + z) / 2 for y, (a, z) in rentang.items()}


def sampul_tengah(akar):
    """@sampul: tengah (logo berwarna dengan rasio gambarnya di tengah, baris rata tengah, @jenis/@nim tidak tercetak,
    judul panjang dikecilkan supaya sampul satu halaman), @judul_fasl: dua_baris (فهرس tetap satu baris), dan
    @ihda: tengah (paragraf الإهداء tengah dan tebal), dan ﴿﴾ halaman @ayat_pembuka tidak terbalik."""
    png = zipfile.ZipFile(akar / "mesin" / "sampul_jakarta.docx").read("word/media/image2.png")
    lebar, tinggi = struct.unpack(">II", png[16:24])
    # « - » sub-judul di tempat pindah baris @judul_sampul tidak ditulis dan tidak tercetak
    tulis(akar, "tengah", "@judul: اختبار الغلاف الوسط - دراسة وصفية\n@judul_sampul: اختبار الغلاف الوسط // دراسة وصفية\n"
          "@sampul: tengah\n@qism: قسم اللغة العربية\n@nama: طالبة\n@thalibah: ya\n@jenis: بحث صفي للمستوى\n@nim: 4300123\n"
          "@musyrif: د. مشرف\n@tahun: ١٤٤٨ - ٢٠٢٦\n@berkas: uji\n@tanpa: hadits\n@minimal_halaman: 0\n"
          "@judul_fasl: dua_baris\n@ihda: tengah\n@format: tatbiqi_16_berjarak\n@ayat_pembuka: 12:2\n")
    r = bahts(akar, "rakit", "tengah", batas=1800)
    assert r.returncode == 0 and "PERINGATAN" not in r.stdout, r.stdout + r.stderr
    with pymupdf.open(akar / "tengah" / "uji.pdf") as doc:  # ditutup juga kalau ada yang gagal: TEMP bisa dibuang
        w = doc[0].rect.width
        gambar = doc[0].get_image_info()
        pusat = tengah_baris(doc[0])
        hal = [baris_pdf(p) for p in doc]
        kurung = {c["c"]: c["bbox"][0] for b in doc[1].get_text("rawdict")["blocks"] for ln in b.get("lines", [])
                  for sp in ln["spans"] for c in sp["chars"] if c["c"] in "﴾﴿"}
    # halaman ayat sesudah sampul tengah: ﴿ (pembuka) di kanan ayat, ﴾ di kirinya
    assert len(kurung) == 2 and kurung["﴿"] > kurung["﴾"], f"kurung ayat halaman pembuka terbalik: {kurung}"
    assert len(gambar) == 1, gambar
    x0, y0, x1, y1 = gambar[0]["bbox"]
    assert abs((x1 - x0) / (y1 - y0) - lebar / tinggi) < 0.01, f"logo penyok: {(x1 - x0) / (y1 - y0):.3f} ≠ {lebar / tinggi:.3f}"
    assert abs((x0 + x1) / 2 - w / 2) < 2, f"logo tidak di tengah: {gambar[0]['bbox']}"
    assert len(pusat) == 7 and all(abs(x - w / 2) < 10 for x in pusat.values()), f"baris sampul tidak rata tengah: {pusat}"
    teks = [t for t, *_ in hal[0]]
    for t in ("معهد العلوم الإسلامية والعربية في إندونيسيا", "قسم اللغة العربية", "اختبار الغلاف الوسط", "دراسة وصفية",
              "إعداد الطالبة: طالبة"):
        assert t in teks, f"sampul tanpa baris «{t}»: {teks}"
    assert teks.index("اختبار الغلاف الوسط") < teks.index("دراسة وصفية"), teks
    semua = "".join(teks)
    assert "مشرف" in semua and "بحث صفي" not in semua and not re.search("4300123|٤٣٠٠١٢٣|3210034|٣٢١٠٠٣٤", semua), teks
    ihda = next(b for b in hal if any(t == "الإهداء" for t, *_ in b))
    isi = [x for x in ihda if "الكريمين" in x[0]]
    assert isi and "Bold" in isi[0][2] and abs(isi[0][1] - w / 2) < 30, f"paragraf الإهداء tidak tengah/tebal: {isi}"
    fasl = next((b for b in hal if any(t == "الفصل الأول" for t, *_ in b)), None)
    assert fasl and any(t == "الموضوع" for t, *_ in fasl), "judul فصل tidak dua baris («الفصل الأول» bukan baris sendiri)"
    fihris = next(b for b in hal if any("فهرس الموضوعات" in t for t, *_ in b))
    assert any("الفصل الأول" in t and "الموضوع" in t for t, *_ in fihris), f"judul فصل di فهرس tidak satu baris: {fihris}"
    # judul sangat panjang: sampul tetap satu halaman, judulnya yang dikecilkan (bukan baris lain)
    panjang = " ".join(["دراسة تحليلية وصفية مقارنة لأساليب المدح في شعر الشعراء العباسيين"] * 16)
    tulis(akar, "panjang", f"@judul: {panjang}\n@sampul: tengah\n@qism: قسم اللغة العربية\n@nama: طالب\n@musyrif: د. مشرف\n"
          "@berkas: uji\n@tanpa: hadits\n@minimal_halaman: 0\n")
    r = bahts(akar, "rakit", "panjang", batas=1800)
    assert r.returncode == 0 and "PERINGATAN" not in r.stdout, r.stdout + r.stderr
    with pymupdf.open(akar / "panjang" / "uji.pdf") as doc:
        sampul, kedua = [t for t, *_ in baris_pdf(doc[0])], doc[1].get_text()
        ukuran = {round(s["size"]) for b in doc[0].get_text("dict")["blocks"] for ln in b.get("lines", [])
                  for s in ln["spans"] if "الشعراء" in s["text"]}
    assert "إعداد الطالب: طالب" in sampul and "مشرف" not in kedua, f"sampul judul panjang lebih dari satu halaman: {sampul}"
    assert ukuran and max(ukuran) < 16, f"judul panjang tidak dikecilkan sampai muat: {ukuran}"
    print(f"lolos sampul tengah Word: logo {x1 - x0:.0f}×{y1 - y0:.0f} pt (rasio gambar {lebar}×{tinggi}), baris tengah, "
          f"@jenis/@nim tidak tercetak, judul panjang {max(ukuran)} pt satu halaman; judul فصل dua baris (فهرس satu baris); "
          "الإهداء tengah tebal")


def jakarta_mahad_dan_mulakhas(akar):
    from xml.etree import ElementTree as ET
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    w = "{" + ns["w"] + "}"
    tulis(akar, "jakarta",
          "@model: jakarta\n@judul: اختبار نموذج جاكرتا\n@nama: طالب\n@sifat: طالب مقيد\n@nim: 4300123\n"
          "@musyrif: د. مشرف\n@jabatan: أستاذ مشارك\n@berkas: uji\n@tanpa: hadits\n@minimal_halaman: 0\n",
          "#K المقدمة\nنص قصير.\n#K الخاتمة\nنتائج.\n#R المصادر\nالقرآن الكريم.\n")
    rj = bahts(akar, "rakit", "jakarta", batas=1800)
    assert rj.returncode == 0, rj.stdout + rj.stderr
    with zipfile.ZipFile(akar / "jakarta" / "uji.docx") as z:
        hdr_j = " ".join("".join(ET.fromstring(z.read(n)).itertext()) for n in z.namelist() if re.fullmatch(r"word/header\d+\.xml", n))
    assert "اختبار نموذج جاكرتا" in hdr_j and "عنوان البحث" not in hdr_j, hdr_j
    with pymupdf.open(akar / "jakarta" / "uji.pdf") as doc:
        spans_j = [(s["font"], s["size"], s["text"]) for b in doc[0].get_text("dict")["blocks"]
                   for ln in b.get("lines", []) for s in ln["spans"] if s["text"].strip()]
    qism_spans = [(f, u, t) for f, u, t in spans_j if "قسم الشريعة بجاكرتا" in t]
    assert qism_spans and all("Traditional" in f and 15.5 <= u <= 16.5 for f, u, _ in qism_spans), qism_spans
    tulis(akar, "mahad",
          "@sampul: mahad\n@format: tatbiqi_mulakhas\n@judul: اختبار غلاف المعهد\n@jenis: بحث صفي للمستوى الثامن\n"
          "@nama: طالب\n@nim: 4300123\n@fasl: الفصل الدراسي الأول\n@musyrif: د. مشرف\n@berkas: uji\n"
          "@tanpa: ayat, hadits, maudhuat, pustaka\n@minimal_halaman: 0\n",
          "#K المُلَخَّص\nالفقرة الأولى من الملخص العربي.\nالفقرة الثانية من الملخص العربي.\n"
          "#K المُلَخَّص بِاللُّغَةِ الأَجْنَبِيَّةِ\n#L **Abstract**\n#L English abstract paragraph.\n"
          "#K المقدمة\nفقرة المقدمة العادية.\n#K الخاتمة\nانتهى.\n")
    rm = bahts(akar, "rakit", "mahad", batas=1800)
    assert rm.returncode == 0, rm.stdout + rm.stderr
    with zipfile.ZipFile(akar / "mahad" / "uji.docx") as z:
        doc_m = ET.fromstring(z.read("word/document.xml"))
    paras = { "".join(p.itertext()).strip(): p for p in doc_m.findall(".//w:body/w:p", ns) if "".join(p.itertext()).strip() }
    sp = lambda key: paras[key].find("w:pPr/w:spacing", ns)
    ind = lambda key: paras[key].find("w:pPr/w:ind", ns)
    assert sp("الفقرة الأولى من الملخص العربي.").attrib.get(f"{w}line") == "360", ET.tostring(paras["الفقرة الأولى من الملخص العربي."], encoding="unicode")
    assert sp("الفقرة الثانية من الملخص العربي.").attrib.get(f"{w}before") == "120", ET.tostring(paras["الفقرة الثانية من الملخص العربي."], encoding="unicode")
    assert (ind("الفقرة الثانية من الملخص العربي.") is None or ind("الفقرة الثانية من الملخص العربي.").attrib.get(f"{w}firstLine", "0") == "0")
    assert sp("English abstract paragraph.").attrib.get(f"{w}line") == "360"
    sp_mq = sp("فقرة المقدمة العادية.")
    assert sp_mq is None or (sp_mq.attrib.get(f"{w}line", "240") == "240" and sp_mq.attrib.get(f"{w}before", "0") == "0")
    with pymupdf.open(akar / "mahad" / "uji.pdf") as doc:
        hal1 = doc[0].get_text()
    assert "المعهد" in hal1 or "بحث" in hal1, hal1
    print("lolos @model/@sampul jakarta, @sampul mahad, dan #K المُلَخَّص berharakat")


if __name__ == "__main__":
    utama()
