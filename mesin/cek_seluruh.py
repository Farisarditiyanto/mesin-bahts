# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pemeriksaan yang melihat seluruh naskah, bukan satu catatan kaki: jejak langkah riset (riset.txt), porsi
kutipan per bagian, dan الدراسات السابقة."""
import itertools, os, re

import norma
from cek_ayat import ayat
from dasar import ANGKA_LATIN, TAKHRIJ_AWAL, TandaRusak
from laporan import daftar_baris
from petik import kutipan_semua

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
        if bagian not in bagian_khilaf and KHILAF_TANDA.search(norma.HARAKAT.sub("", b).replace("ـ", "")):
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


# Kutipan bertanda petik yang memenuhi isi satu bagian: «تختفي شخصية الكاتب بين الاقتباسات الطويلة» (أبو سليمان، كتابة
# البحث العلمي، ص121-123; kitab itu tidak memberi angka). Angka di sini aturan repo: di 38 naskah nyata hanya
# 5 bagian, semuanya di satu naskah, yang lewat 2/3 (terberat 72%); bagian di bawah 600 huruf terlalu pendek untuk dinilai
PORSI_KUTIPAN = 2 / 3
PORSI_MIN = 600


def porsi_kutipan(blok, catatan):
    """Perhatian tiap bagian (#K/#F/#B/#M sampai judul berikutnya) yang hurufnya sebagian besar kutipan bertanda petik.
    Yang dihitung hanya paragraf matan (#P): ayat {Q:}, catatan kaki, bait #V, dan kotak #T tidak ikut. Hadits juga tidak:
    nash Sunnah dikutip utuh (أبو سليمان، كتابة البحث العلمي، ص112), jadi potongan teks yang memuat {H:} atau yang
    catatan kakinya takhrij («أخرجه»، «رواه»، «متفق عليه») tidak dihitung."""
    hasil, judul, semua, kutip = [], None, 0, 0
    huruf = lambda t: len(re.sub(r"[\s\W\d_]", "", t))

    def potongan(runs):  # teks matan dipotong di tiap catatan kaki; potongan hadits dibuang
        teks, hadits = "", False
        for r in runs:
            if "fn" in r:
                isi = "".join(x.get("t", "") for x in catatan[r["fn"]]["runs"]).strip()
                if not (hadits or TAKHRIJ_AWAL.match(isi) or isi.startswith("متفق عليه")):
                    yield teks
                teks, hadits = "", False
            elif str(r.get("bm", "")).startswith("h_"):
                hadits = True
            elif "t" in r and not r.get("q"):
                teks += r["t"]
        if not hadits:
            yield teks

    def nilai():
        if judul and semua >= PORSI_MIN and kutip / semua > PORSI_KUTIPAN:
            hasil.append(f"baris {judul['n']}: bagian «{judul['judul'][:40]}»: {round(100 * kutip / semua)}% hurufnya kutipan "
                         f"bertanda petik: ringkas sebagian dengan «انظر:» dan tulis pembahasanmu sendiri di antaranya "
                         f"(أبو سليمان، كتابة البحث العلمي، ص121-123; batas 2/3 aturan repo)")
    for b in blok:
        if b["k"] in ("K", "F", "B", "M", "R"):
            nilai()
            judul, semua, kutip = (b if b["k"] != "R" else None), 0, 0
        elif b["k"] == "P":
            for teks in potongan(b["runs"]):
                semua += huruf(teks)
                kutip += sum(huruf(k) for k in kutipan_semua(teks))
    nilai()
    return hasil


DIRASAT = "الدراسات السابقة"
# tiap studi wajib menyebut tiga hal ini (AGENTS.md الدراسات السابقة; التقويم = «دراسة نقدية فاحصة… تقويمًا لمحتواها»,
# أبو سليمان، كتابة البحث العلمي، ص60)
# kata utuh, boleh berawalan و/ف («ووجه»، «فالتقويم») dan أوجه dengan/tanpa hamzah («اوجه»), bukan potongan kata («عدموجه»)
DIRASAT_LABEL = (("وجه الاتفاق:", r"(?<!\w)[وف]?[اأإ]?وجه\s+الاتفاق\s*:"),
                 ("وجه الاختلاف:", r"(?<!\w)[وف]?[اأإ]?وجه\s+(?:الاختلاف|الافتراق)\s*:"),
                 ("التقويم:", r"(?<!\w)[وف]?التقويم\s*:"))
TAHUN_TERBIT = re.compile(r"(?<!\d)(1[3-4]\d\d|19\d\d|20\d\d)(?!\d)\s*(م|هـ)")
TINGKAT_JUDUL = {"K": 0, "F": 0, "R": 0, "B": 1, "M": 2, "S": 3}


def _label_dirasat(teks):
    """Label utuh dan isinya sampai label berikutnya. Tanda baca/angka saja bukan pembahasan;
    teks label berikutnya tidak boleh menjadi isi label yang masih kosong."""
    semua = sorted((m.start(), m.end(), i) for i, (_, pola) in enumerate(DIRASAT_LABEL)
                   for m in re.finditer(pola, teks))
    ada, terisi = [False] * len(DIRASAT_LABEL), [False] * len(DIRASAT_LABEL)
    for (_, akhir, i), (batas, _, _) in zip(semua, semua[1:] + [(len(teks), 0, 0)]):
        ada[i] = True
        terisi[i] |= bool(re.search(r"[^\W\d_]", teks[akhir:batas]))
    return ada, terisi


def periksa_dirasat(blok, catatan):
    """Perhatian tiap studi di bagian berjudul «الدراسات السابقة» (judul tingkat apa pun, harakat diabaikan) sampai
    judul setingkat atau lebih tinggi. Studi = paragraf yang bercatatan kaki di luar Shamela (<<luar…>>), memuat salah
    satu label, atau menyebut tahun terbit («…م»/«…هـ»); pengantar dan الإضافة العلمية tidak dinilai. Satu perhatian per
    studi, berisi semua kekurangannya: label «وجه الاتفاق:»/«وجه الاختلاف:»/«التقويم:» yang hilang atau kosong, PDF yang tidak dibaca (tanpa
    <<luar|berkas.pdf|hal>>), dan tahun terbit yang lebih dulu dari studi sebelumnya. Tahun terbit = tahun terakhir
    sebelum catatan kaki pertama dan label pertama (tahun di judul studi, mis. «رؤية 2030م», ada di depannya).
    Paragraf yang diawali «الإضافة العلمية» bukan studi walau menyebut tahun."""
    hasil, bagian, tahun_lalu = [], None, None
    for b in blok:
        if b["k"] in TINGKAT_JUDUL:
            if bagian is not None and TINGKAT_JUDUL[b["k"]] <= bagian:
                bagian = None
            if bagian is None and DIRASAT in norma.HARAKAT.sub("", b.get("judul", "")):
                bagian, tahun_lalu = TINGKAT_JUDUL[b["k"]], None
            continue
        if bagian is None or b["k"] != "P":
            continue
        fn = [catatan[r["fn"]] for r in b["runs"] if "fn" in r]
        teks = norma.HARAKAT.sub("", "".join(r.get("t", "") for r in b["runs"])).translate(ANGKA_LATIN)
        if re.match(r"\W*و?(?:الإضافة العلمية|إضافة البحث)", teks):
            continue
        # data studi = sebelum catatan kaki pertama dan sebelum label pertama; tahun terbit = tahun terakhirnya
        data = norma.HARAKAT.sub("", "".join(r.get("t", "") for r in itertools.takewhile(lambda r: "fn" not in r, b["runs"])))
        data = data.translate(ANGKA_LATIN)
        data = data[:min([m.start() for _, pola in DIRASAT_LABEL for m in [re.search(pola, data)] if m] + [len(data)])]
        label, terisi = _label_dirasat(teks)
        tahun_semua = TAHUN_TERBIT.findall(data)
        if not (any(c["luar"] or c["pdf"] for c in fn) or any(label) or tahun_semua):
            continue
        kurang = [(f"«{nama}» masih kosong" if ada else f"belum ada «{nama}»")
                  for (nama, _), ada, isi in zip(DIRASAT_LABEL, label, terisi) if not isi]
        if kurang:
            kurang[-1] += " (satu studi satu paragraf: label dicari di paragraf ini)"
        isi_fn = " ".join(r.get("t", "") for c in fn for r in c["runs"])
        if not any(c["pdf"] for c in fn):
            kurang.append("hanya dari ringkasan («اطلعت على ملخصه»): sebut di laporan akhir" if "اطلعت على ملخص" in isi_fn else
                          "PDF-nya belum dibaca: unduh lewat `dirasat-pdf` lalu rujuk <<luar|berkas.pdf|hal>>; PDF memang "
                          "tidak bisa didapat → tulis «اطلعت على ملخصه» di catatan kakinya dan sebut di laporan akhir")
        if tahun_semua:  # tahun hijriah dibandingkan sebagai masehi (kira-kira; cukup untuk urutan)
            angka, akhiran = tahun_semua[-1]
            tahun = int(angka) if akhiran == "م" else round(int(angka) * 0.970224 + 621.5643)
            if tahun_lalu and tahun < tahun_lalu[0]:
                kurang.append(f"tahun {angka}{akhiran} lebih dulu daripada studi sebelumnya ({tahun_lalu[1]}): "
                              f"urutkan dari yang terlama")
            else:
                tahun_lalu = (tahun, angka + akhiran)
        if kurang:
            hasil.append(f"baris {b['n']}: {DIRASAT}: " + "; ".join(kurang))
    return hasil


# Isi المقدمة menurut أبو سليمان، كتابة البحث العلمي، ص196-197, sembilan butir, dengan nama butir kitab itu (dikenali
# lewat kata yang biasa dipakai di judul atau paragraf المقدمة). «الآفاق» butir 4 adalah sisi penelitian lain di luar
# yang dibahas, bukan batas penelitian ini (ص197). Hanya untuk رسالة/بحث تكميلي (@jenis):
# بحث صفي mengikuti خطة dosen (AGENTS.md: «خطة dosen menyebut isi المقدمة → sub-judul المقدمة ikut itu»).
MUQADDIMAH = (
    ("تحديد موضوع البحث", r"موضوع|مشكل|إشكال|تساؤل|أسئل[ةه]"),
    ("قيمة البحث وأهميته", r"أهمي|قيم[ةه]"),
    ("أسباب الاختيار", r"أسباب|سبب|دوافع|بواعث|دواعي"),
    ("آفاق البحث الأخرى", r"آفاق|(?:جوانب|مجالات|أبعاد)\s+أخرى"),
    ("طرق الوصول إلى النتائج", r"إجراءات|طريق[ةه] البحث|طرق البحث|خطوات البحث|طريقتي"),
    ("المنهج", r"منهج"),
    ("المصطلحات", r"مصطلح|تعريف"),
    ("الدراسات السابقة", r"الدراسات السابق|دراسات سابق"),
    ("التقسيمات", r"خط[ةهت]|تقسيم|هيكل|مباحث|فصول"),
)
JENIS_RISALAH = re.compile(r"رسال[ةه]|تكميلي|ماجستير|دكتوراه|أطروح")


def _bagian(blok, kata):
    """(baris judul #K/#F bernama `kata` — «#K المقدمة»، «#K مقدمة البحث»، «#F الفصل الأول: المقدمة»، «#F الفصل الخامس:
    الخاتمة والتوصيات» —, teks judul dan paragrafnya sampai #K/#F berikutnya), atau None. Kata pertama judul (sesudah
    «…:») harus kata itu sendiri: «المقدمات اللغوية» dan «الخاتم في اللغة» adalah bab isi."""
    pola = re.compile(rf"(?:ال)?{kata}[ةه](?:\s+(?:البحث|الدراس[ةه]|الرسال[ةه]))?"
                      r"(?:\s+و(?:التوصيات|النتائج))*(?:\s*[:：،–-].*)?")
    for i, b in enumerate(blok):
        nama = norma.HARAKAT.sub("", b.get("judul", "")).strip()
        nama = re.sub(r"^(?:الفصل|الباب|المبحث)\s+[^:：]+[:：]\s*", "", nama)
        if b["k"] in ("K", "F") and pola.fullmatch(nama):
            isi = []
            for x in blok[i + 1:]:
                if x["k"] in ("K", "F", "R"):
                    break
                isi.append(x.get("judul") or "".join(r.get("t", "") for r in x.get("runs", [])))
            return b["n"], norma.HARAKAT.sub("", "\n".join(isi))
    return None


def periksa_muqaddimah(blok, jenis):
    """Satu perhatian kalau المقدمة رسالة/بحث تكميلي tidak menyebut salah satu isi MUQADDIMAH (judul atau paragrafnya)."""
    if not JENIS_RISALAH.search(norma.HARAKAT.sub("", jenis or "")):
        return []
    m = _bagian(blok, "مقدم")
    if not m or not m[1].strip():  # tanpa المقدمة, atau masih kosong (sudah jadi perhatian «masih kosong»)
        return []
    kurang = [nama for nama, pola in MUQADDIMAH if not re.search(pola, m[1])]
    if not kurang:
        return []
    return [f"baris {m[0]}: المقدمة belum menyebut: {'، '.join(kurang)} (isi المقدمة رسالة menurut أبو سليمان، كتابة البحث "
            f"العلمي، ص196-197); tulis yang diminta خطة dosen, yang tidak diminta biarkan dan sebut di laporan akhir"]


def periksa_khatimah(blok):
    """Perhatian kalau الخاتمة berisi tetapi tidak menyebut hasil penelitian: الخاتمة «تعلن فيها الأحكام، وتقرر النتائج»
    (أبو سليمان، كتابة البحث العلمي، ص198). التوصيات tidak diminta: kitab itu menyebutnya «أحيانًا»."""
    m = _bagian(blok, "خاتم")  # hasil penelitian: «النتائج»، «تبين لي»، «توصلت»، «خلاصة»
    if not m or not m[1].strip() or re.search(
            r"نتائج|نتيج[ةه]|توصل|تبين|(?<![ء-ي])[وف]?خلص(?:ت|نا|وا)?(?![ء-ي])|خلاص[ةه]", m[1]):
        return []
    return [f"baris {m[0]}: الخاتمة belum menyebut النتائج: tulis hasil penelitian ini («أهم النتائج: …») "
            f"(أبو سليمان، كتابة البحث العلمي، ص198); التوصيات tidak wajib"]
