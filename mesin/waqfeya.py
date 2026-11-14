# SPDX-License-Identifier: AGPL-3.0-or-later
"""Kitab Waqfeya: scan cetakan (PDF gambar) + teks OCR, untuk kitab yang tidak ada di Shamela.

Datanya dataset Hugging Face ieasybooks-org/waqfeya-library (±10.000 kitab), versinya dikunci (REVISI) supaya nomor
kitab tetap. Kitab yang di-`ambil` disimpan di kitab/waqfeya/<nomor>/ dan dipakai semua bahts.

OCR = teks hasil baca mesin atas foto halaman. Diukur terhadap Shamela di 152 kitab yang ada di keduanya: ±97% kata
terbaca benar, tetapi kutipan 15 kata yang utuh persis hanya ±72%, dan salah hurufnya sering jadi kata lain yang sah
(«وتوقي» → «وتوفي»). Karena itu OCR di sini hanya penunjuk halaman: lafaz dan nomor halaman cetak disalin dari foto
halamannya (`halaman w… <berkas> <hal>` memotong halaman itu jadi PDF/PNG kecil). Bukti <<w…|berkas|hal>> di `cek`:
GAGAL hanya untuk yang pasti salah (cek_kutipan.cek_waqfeya); lafaznya tidak dinilai `cek`, tetapi pemeriksa dari scan
(`bukti` menunjuk halamannya), supaya salah huruf OCR tidak menggagalkan atau menimbun perhatian kutipan yang benar."""
import ast, csv, difflib, functools, gzip, hashlib, json, re, time, urllib.error, urllib.parse
from pathlib import Path

import norma
import shamela
from berkas import sementara

DATASET = "ieasybooks-org/waqfeya-library"
REVISI = "6baff87f74cd3c53a6f3495d25c55b706cb55af8"  # dikunci: berkas dan urutannya tidak berubah walau dataset diperbarui
RAW = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISI}"
FOLDER = shamela.ROOT / "waqfeya"
KATALOG = shamela.ROOT / "_meta" / "waqfeya.tsv"
DATA = "kitab.json"  # ditulis terakhir: tandanya kitab sudah utuh terunduh
PEMISAH = "\nPAGE_SEPARATOR\n"  # pemisah halaman di berkas OCR dataset
NOMOR = re.compile(r"w[0-9a-f]{8}")
HALAMAN_MAKS = 20
LAIN_MIN = 25  # huruf `padat` kutipan paling sedikit sebelum «ada di halaman lain» dipercaya (GAGAL)
MIRIP_MIN = 85  # skor rapidfuzz (0-100) paling rendah untuk «mirip» di `cari`
LIPUT_MIRIP = 0.85  # bagian huruf kutipan yang terbaca berurutan di OCR halaman itu: «mirip» (salah huruf OCR biasa)
LIPUT_BUKAN = 0.6  # di bawah ini halaman yang ditulis jelas bukan tempat kutipannya (syarat GAGAL «halaman lain»)
# kamus berkolom dan kitab berhamisy: urutan baris OCR-nya kacau (kutipan 15 kata utuh 0-5% di uji 152 kitab)
RAWAN_KATEGORI = re.compile(r"المعاجم|القواميس")
RAWAN_JUDUL = re.compile(r"بهامش|^(?:ال)?(?:معجم|قاموس|مفردات|مختار الصحاح|لسان العرب|تاج العروس|الصحاح|العين|جمهرة اللغة|تهذيب اللغة|مقاييس)")
ANGKA = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def nomor(baris):
    """Nomor kitab: «w» + 8 huruf sidik folder PDF-nya di dataset (tetap selama REVISI sama)."""
    return "w" + hashlib.sha1(baris["folder"].encode()).hexdigest()[:8]


def _siapkan_katalog():
    if not KATALOG.exists():
        print("katalog Waqfeya: mengunduh (±17 MB, sekali saja) …", flush=True)
        shamela._unduh(f"{RAW}/index.tsv", KATALOG, lambda q: open(q, "wb"))


@functools.cache
def katalog():
    """{nomor: baris} semua kitab Waqfeya yang punya PDF. Baris = judul, pengarang, kategori, halaman, berkas."""
    _siapkan_katalog()
    csv.field_size_limit(1 << 30)
    out = {}
    with open(KATALOG, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            pdf, txt = ast.literal_eval(r["pdf_paths"]), ast.literal_eval(r["txt_paths"])
            if not pdf or len(pdf) != len(txt):
                continue
            b = {"judul": r["title"].strip(), "pengarang": r["author"].strip(), "kategori": r["category"].strip(),
                 "halaman": int(r["pages"] or 0), "folder": pdf[0].rsplit("/", 1)[0],
                 "berkas": [{"nama": Path(p).stem, "pdf": p[2:], "txt": t[2:]} for p, t in zip(pdf, txt)]}
            out[nomor(b)] = b
    return out


def rawan(b):
    """Kitab yang OCR-nya tidak bisa diandalkan sama sekali (kamus berkolom, kitab berhamisy)."""
    return bool(RAWAN_KATEGORI.search(b["kategori"]) or RAWAN_JUDUL.search(b["judul"]))


# bagian nama yang dipakai banyak ulama (ism, kunyah, laqab umum): tidak membedakan pengarang
NAMA_UMUM = {norma.norm(x) for x in """محمد أحمد عبد الله الدين بن أبو أبي علي عمر الرحمن إبراهيم الحسن الحسين حسن حسين
سعيد يوسف عثمان إسماعيل يحيى موسى سليمان عيسى صالح خالد جعفر طاهر العباس القاسم الفضل بكر زيد مصطفى عمرو يعقوب داود
إسحاق منصور محمود الشيخ الإمام الحافظ العلامة القاضي شهاب جمال كمال زين تقي شمس بدر عماد نجم سراج فخر العزيز""".split()}


def _kata_nama(nama):
    """Kata nama yang membedakan orang, tanpa «ال» («العثيمين» = «عثيمين»: katalog menulisnya dua cara)."""
    out = set()
    for w in norma.norm(nama or "").split():
        if len(w) >= 4 and w not in NAMA_UMUM and "ال" + w not in NAMA_UMUM:
            w = w[2:] if w.startswith("ال") else w
            if len(w) >= 3 and w not in NAMA_UMUM:
                out.add(w)
    return out


@functools.cache
def _pengarang_shamela():
    """{nomor kitab Shamela: kata nama pengarangnya} (untuk mencocokkan judul pendek Shamela, mis. «المحصول»)."""
    try:
        return {int(r["shamela_id"]): _kata_nama(r["main_author_name_ar"]) for r in shamela._meta()}
    except SystemExit:
        return {}


def _di_shamela(b):
    """Nomor kitab Shamela yang judul pokoknya sama dengan judul Waqfeya (tanpa kurung dan keterangan edisi sesudah
    « - »), atau judul pokok Shamela-nya awal judul Waqfeya dan pengarangnya sama («المحصول» ↔ «المحصول في علم أصول
    الفقه»). Penunjuk saja: edisinya bisa berbeda."""
    pokok, nama = _pokok(b["judul"]), _nama_kitab(b)
    ada = shamela.nomor_judul_pokok(pokok) or shamela.nomor_judul(pokok)[0]
    if ada and nama:  # judul sama, pengarang lain («شرح منتهى الإرادات» البهوتي ≠ ابن النجار) = kitab lain
        return [s for s in ada if nama & _pengarang_shamela().get(s, set())]
    if ada:
        return ada
    q = norma.padat(pokok)
    if not nama:
        return []
    return sorted(s for j, ss in _judul_tanpa_pengarang().items() if len(j) >= 6 and q.startswith(j)
                  for s in ss if nama & _pengarang_shamela().get(s, set()))


@functools.cache
def _judul_tanpa_pengarang():
    """{judul pokok Shamela `padat`: {nomor}}, juga tanpa nama pengarang yang ditempel «لـ…» di akhir («المحصول
    للرازي» → «المحصول»): shamela.judul_pokok hanya membuang للشيخ/لابن/لأبي…"""
    out = {}
    for j, ss in shamela._judul_pokok_padat().items():
        out.setdefault(j, set()).update(ss)
    try:
        daftar = shamela._meta()
    except SystemExit:
        return out
    for r in daftar:
        for b in shamela.judul_pokok(r["title_ar"]):
            kata = b.split()
            nama = _kata_nama(r["main_author_name_ar"])
            akhir = kata[-1] if len(kata) >= 2 else ""
            # «للرازي» = لـ + الرازي (alif ال luluh), «لابن…» = لـ + ابن…
            orang = "ال" + akhir[2:] if akhir.startswith("لل") else akhir[1:] if akhir.startswith("ل") else ""
            if orang and _kata_nama(orang) & nama:
                out.setdefault(norma.padat(" ".join(kata[:-1])), set()).add(int(r["shamela_id"]))
    return out


def _pokok(judul):
    """Judul Waqfeya tanpa kurung (pengarang, muhaqqiq) dan keterangan edisi sesudah « - »."""
    return re.split(r"\s+-\s+|---|\s+=\s+", re.sub(r"\(.*?\)|\[.*?\]", " ", judul))[0].strip()


def _nama_kitab(b):
    """Kata nama pengarang kitab Waqfeya: kolom pengarang + nama di kurung judul («شرح سنن أبي داود (ابن رسلان)»)."""
    kurung = [x for x in re.findall(r"\(([^()]*)\)", b["judul"]) if not re.match(r"\s*(?:ط|ت)\s*[._]", x)]  # (ت_ …)، (ط. …)
    return _kata_nama(b["pengarang"] + " " + " ".join(kurung))


# kata judul ≥4 huruf yang ada di ≥0,4% judul katalog Waqfeya (dihitung sekali dari katalog revisi REVISI): tidak
# membedakan kitab, jadi tidak dipakai untuk menilai apakah catatan kaki menyebut kitab buktinya
KATA_JUDUL_UMUM = frozenset(norma.padat(x) for x in """الله القران الاسلام كتاب الامام الاسلاميه الحديث عليه الاسلامي
دراسه الكريم الفقه السنه تفسير تاريخ وسلم ديوان احكام تيميه اصول محمد العربيه الكتاب ويليه صحيح معجم مختصر احمد احاديث
الاحكام والسنه النبويه الدين الجامع الفقهيه الرد الشريعه البخاري علوم الشيخ المسلمين حديث فتاوي الحج التفسير مسايل
العقيده رمضان الاصول ومعه الاحاديث بيان موسوعه العرب بشرح رساله اللغه النبي الفكر الصحيح منهج الشرعيه حنبل الفوايد
القرن معرفه القراءات التوحيد القواعد الصحابه لابن قواعد العالم جامع المسايل المعجم الكتب مسند العلم الوقف التاريخ العربي
الرسول الرحمن العلماء الشافعي مالك حاشيه السنن الصلاه فضايل عمده كلام الكبير الحرام النبوي الاعلام اعلام الحافظ تحفه
التي غريب تهذيب مذهب الكبري المومنين رسايل المعاصره البيان مقارنه مسلم علماء اخبار مجموع الشيعه الجهاد داود العشر اسماء
الالباني النحو الدوله المسمي وبهامشه تخريج والعمره رحله العزيز الصيام الدرر السيره العلامه بلوغ الدعوه""".split())


def _bentuk(kata):
    """Bentuk sebanding sebuah kata `padat`: dengan/tanpa «ال» dan huruf sambung و/ب/ل/ف di depannya."""
    out = {kata}
    for x in list(out):
        if len(x) > 4 and x[0] in "وبلف":
            out.add(x[1:])
    for x in list(out):
        out.add(x[2:] if x.startswith("ال") else "ال" + x)
    return {x for x in out if len(x) >= 3}


def judul_disebut(w, isi):
    """Catatan kaki menyebut kitab Waqfeya w: kata judul pokoknya yang khas (bukan KATA_JUDUL_UMUM) atau kata nama
    pengarangnya («تفسير الطبري» untuk جامع البيان) ada utuh di isi, atau isi hanya merujuk ulang («المصدر السابق»،
    «نفسه»). Kitab yang judulnya hanya kata umum tidak dinilai (True). False = catatan kaki menyebut kitab lain."""
    if re.search(r"السابق|نفسه|المرجع|المصدر", isi):
        return True
    d = data(w)
    khas = {norma.padat(x) for x in _pokok(d["judul"]).split()} - KATA_JUDUL_UMUM
    khas = {x for x in khas if len(x) >= 4}
    if not khas:
        return True
    isi_ = set().union(*(_bentuk(norma.padat(x)) for x in isi.split() if norma.padat(x)))
    cari = khas | _nama_kitab(d)
    return any(_bentuk(norma.padat(x)) & isi_ for x in cari)


def cari_katalog(frasa, maks=20):
    """`waqfeya "<judul/pengarang>"`: kitab yang judul atau pengarangnya memuat semua kata frasa."""
    kata = [norma.padat(w) for w in frasa.split() if norma.padat(w)]
    if not kata:
        raise ValueError("tulis kata dari judul atau nama pengarang")
    hasil = [(w, b) for w, b in katalog().items()
             if all(k in norma.padat(b["judul"] + " " + b["pengarang"]) for k in kata)]
    q = "".join(kata)
    hasil.sort(key=lambda x: (not norma.padat(x[1]["judul"]).startswith(q), len(x[1]["judul"])))
    for w, b in hasil[:maks]:
        catatan = []
        if ada := _di_shamela(b):
            catatan.append(f"judul ini ada di Shamela ({'، '.join(map(str, ada[:3]))}): pakai Shamela kalau edisinya sama")
        if rawan(b):
            catatan.append("kamus/berhamisy: OCR-nya kacau, baca dari scan saja")
        print(f"{w}  {b['judul']} | {b['pengarang']} | {b['halaman']} hal, {len(b['berkas'])} berkas | {b['kategori']}"
              + ("" if not catatan else "  [" + "; ".join(catatan) + "]"))
    if len(hasil) > maks:
        print(f"… {len(hasil) - maks} lagi; persempit katanya atau naikkan maks")
    if not hasil:
        print(f"Tidak ada kitab Waqfeya berjudul/berpengarang «{frasa}».")
    return len(hasil)


def folder(w):
    return FOLDER / w


def _isi(p):
    """Berkas ada dan tidak kosong (unduhan dan potongan ditulis lewat nama sementara: yang ada = utuh)."""
    try:
        return p.stat().st_size > 0
    except OSError:
        return False


def _lokal(w):
    """Data kitab lokal kalau kitab.json terbaca dan tiap PDF/OCR-nya ada; None = belum (lengkap) diunduh."""
    try:
        d = json.loads((folder(w) / DATA).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not (isinstance(d, dict) and isinstance(d.get("judul"), str) and isinstance(d.get("berkas"), list) and d["berkas"]):
        return None
    return d if all(_isi(folder(w) / f"{i}.{x}") for i in range(1, len(d["berkas"]) + 1) for x in ("pdf", "txt.gz")) else None


def ada(w):
    return NOMOR.fullmatch(w) is not None and _lokal(w) is not None


def data(w):
    """Data kitab yang sudah diunduh; SystemExit dengan perintah `ambil` kalau belum (atau belum lengkap)."""
    if not NOMOR.fullmatch(w):
        raise SystemExit(f"«{w}» bukan nomor kitab Waqfeya (bentuknya w + 8 huruf, dari `waqfeya \"<judul>\"`).")
    d = _lokal(w)
    if d is None:
        raise SystemExit(f"Kitab Waqfeya {w} belum diunduh atau belum lengkap (metadata/PDF/OCR hilang atau kosong): "
                         + shamela.perintah(f"ambil {w}"))
    return d


def ambil(*ww):
    """Unduh OCR dan PDF tiap kitab Waqfeya. Kembalikan nomor yang gagal."""
    gagal = []
    for w in ww:
        for coba in range(1, shamela.COBA + 1):
            try:
                _ambil(w)
                break
            except LookupError as e:
                print(f"{w}: {e}"); gagal.append(w); break
            except shamela.GAGAL_JARINGAN as e:
                tetap = isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500 and e.code != 429
                if tetap or coba == shamela.COBA:
                    print(f"{w}: GAGAL mengunduh, cek internet lalu ulangi ({e!r})"); gagal.append(w); break
                print(f"{w}: unduhan putus ({e!r}); mencoba lagi ({coba + 1}/{shamela.COBA}) ...", flush=True)
                time.sleep(5 * coba)
    return gagal


def _ambil(w):
    if not NOMOR.fullmatch(w):
        raise LookupError("bukan nomor kitab Waqfeya (bentuknya w + 8 huruf, dari `waqfeya \"<judul>\"`)")
    if ada(w):
        print(w, "sudah ada"); return
    b = katalog().get(w)
    if b is None:
        raise LookupError("TIDAK ADA di katalog Waqfeya (nomornya dari `waqfeya \"<judul>\"`)")
    d = folder(w)
    print(f"{w}: mengunduh {b['judul']} ({b['halaman']} hal, {len(b['berkas'])} berkas) …", flush=True)
    for i, f in enumerate(b["berkas"], 1):
        if not _isi(d / f"{i}.txt.gz"):
            shamela._unduh(f"{RAW}/{urllib.parse.quote(f['txt'])}", d / f"{i}.txt.gz", lambda q: gzip.open(q, "wb", compresslevel=6))
        if not _isi(d / f"{i}.pdf"):
            print(f"{w}: berkas {i}/{len(b['berkas'])} ({f['nama']}) …", flush=True)
            shamela._unduh(f"{RAW}/{urllib.parse.quote(f['pdf'])}", d / f"{i}.pdf", lambda q: open(q, "wb"))
    simpan = {k: b[k] for k in ("judul", "pengarang", "kategori", "halaman")}
    simpan.update(nomor=w, berkas=[f["nama"] for f in b["berkas"]], dataset=DATASET, revisi=REVISI, folder=b["folder"])
    with sementara(d / DATA) as part:  # ditulis terakhir dan utuh: tanda kitab sudah lengkap
        part.write_text(json.dumps(simpan, ensure_ascii=False, indent=1), encoding="utf-8")
    mb = sum(p.stat().st_size for p in d.iterdir()) / 1e6
    print(f"{w} OK  {b['judul']}  ({mb:.1f} MB)" + ("  [kamus/berhamisy: OCR-nya kacau, baca dari scan saja]" if rawan(b) else ""))


@functools.lru_cache(maxsize=16)
def ocr(w, n):
    """Teks OCR tiap halaman berkas n (mulai 1), urut halaman PDF."""
    p = folder(w) / f"{n}.txt.gz"
    if not p.exists():
        raise SystemExit(f"Kitab Waqfeya {w} tidak punya berkas {n}; yang ada: " + _daftar_berkas(w))
    with gzip.open(p, "rt", encoding="utf-8", errors="replace") as f:
        return tuple(f.read().split(PEMISAH))


@functools.lru_cache(maxsize=16)
def _padat(w, n):
    return tuple(norma.padat(t) for t in ocr(w, n))


def _daftar_berkas(w):
    return "، ".join(f"{i}={x}" for i, x in enumerate(data(w)["berkas"], 1))


BARIS_NOMOR = re.compile(r"[\s\-–—ـ()\[\]]*(\d{1,4})[\s\-–—ـ()\[\]]*")  # baris yang isinya nomor saja («— ١٨٠ —»)


def _angka_tepi(teks):
    """Nomor di dua baris pertama dan dua baris terakhir halaman yang isinya hanya nomor itu. Angka di baris berteks
    (nomor catatan kaki «(٢) قال…», tahun) tidak dihitung: lebih baik «tidak terbaca» daripada nomor salah."""
    baris = [x.translate(ANGKA) for x in teks.splitlines() if x.strip()]
    return {int(m[1]) for x in baris[:2] + baris[-2:] if (m := BARIS_NOMOR.fullmatch(x))}


def nomor_cetak(w, n, h):
    """Nomor halaman cetak yang tercetak di scan halaman PDF h, kalau terbaca dan berurutan dengan tetangganya; else None.
    Penunjuk saja: nomor yang ditulis di catatan kaki tetap dibaca dari scan."""
    hh = ocr(w, n)
    if not 1 <= h <= len(hh):
        return None
    kini = _angka_tepi(hh[h - 1])
    for x in sorted(kini):
        if (h > 1 and x - 1 in _angka_tepi(hh[h - 2])) or (h < len(hh) and x + 1 in _angka_tepi(hh[h])):
            return x
    return None


def _rentang(hal):
    m = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+))?\s*", str(hal).translate(ANGKA))
    if not m:
        raise ValueError(f"hal = urutan halaman di berkas PDF (mis. 57 atau 57-59), bukan «{hal}»")
    a, z = int(m[1]), int(m[2] or m[1])
    if not 1 <= a <= z < a + HALAMAN_MAKS:
        raise ValueError(f"rentang {hal}: awal ≤ akhir, mulai 1, paling banyak {HALAMAN_MAKS} halaman")
    return a, z


def potong(w, n, a, z):
    """PDF kecil berisi halaman a..z berkas n (scan aslinya), untuk dibaca orang atau agent. Kembalikan jalurnya."""
    from pypdf import PdfReader, PdfWriter
    tujuan = folder(w) / "potong" / f"{n}-{a}" f"{'' if a == z else f'-{z}'}.pdf"
    if not _isi(tujuan):
        r, t = PdfReader(folder(w) / f"{n}.pdf"), PdfWriter()
        for i in range(a - 1, min(z, len(r.pages))):
            t.add_page(r.pages[i])
        with sementara(tujuan) as part, open(part, "wb") as f:  # terputus = tidak ada potongan, bukan potongan rusak
            t.write(f)
    return tujuan


DPI = 150  # cukup untuk harakat; 110 masih terbaca huruf, tetapi harakat kecil kabur


def gambar(w, n, a, z):
    """PNG tiap halaman a..z (butuh pymupdf: satu-satunya pustaka yang membuka gambar JBIG2 scan Waqfeya tanpa program
    lain). [] kalau pymupdf belum terpasang: PDF potongan dari `potong` tetap bisa dibuka."""
    try:
        import pymupdf
    except ImportError:
        return []
    out = []
    with pymupdf.open(folder(w) / f"{n}.pdf") as doc:
        for h in range(a, min(z, doc.page_count) + 1):
            p = folder(w) / "potong" / f"{n}-{h}.png"
            if not _isi(p):
                with sementara(p) as part:
                    doc[h - 1].get_pixmap(dpi=DPI).save(part, output="png")
            out.append(p)
    return out


def halaman(w, n, hal):
    """`halaman w… <berkas> <hal>`: teks OCR tiap halaman PDF + nomor cetak yang terbaca + PDF scan halaman itu."""
    d = data(w)
    n = int(str(n).translate(ANGKA)) if str(n).translate(ANGKA).isdigit() else 0
    if not 1 <= n <= len(d["berkas"]):
        raise SystemExit(f"Kitab {w}: berkas = nomor urut 1..{len(d['berkas'])} ({_daftar_berkas(w)}), bukan «{n}».")
    a, z = _rentang(hal)
    hh = ocr(w, n)
    if a > len(hh):
        raise SystemExit(f"Kitab {w} berkas {n} hanya {len(hh)} halaman PDF.")
    z = min(z, len(hh))
    for h in range(a, z + 1):
        nc = nomor_cetak(w, n, h)
        print(f"===== [{w}] berkas {n} ({d['berkas'][n - 1]}) hal PDF {h} — nomor cetak terbaca: "
              f"{nc if nc is not None else 'tidak'} =====")
        print(hh[h - 1].strip() or "(halaman kosong/gambar tanpa teks)")
    print(f"--- OCR = teks baca mesin, bisa salah huruf: lafaz dan nomor halaman cetak disalin dari scan-nya: "
          f"{potong(w, n, a, z)}")
    png = gambar(w, n, a, z)
    if png:
        print("--- gambar scan: " + " ".join(map(str, png)))
    else:
        print("--- gambar PNG butuh pymupdf (lihat `periksa`); sementara buka PDF potongan di atas")
    return True


def _letak(teks_norm, q):
    """Letak q (`padat`) di teks `norm` (berspasi): spasi di antara huruf diabaikan, seperti `cek`."""
    return re.search(r"\s*".join(map(re.escape, q)), teks_norm)


def _mirip(q, teks_padat):
    """Skor 0-100 kemiripan q dengan bagian teks paling mirip; None kalau rapidfuzz belum terpasang."""
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return None
    return fuzz.partial_ratio(q, teks_padat)


def cari(w, frasa, maks=20):
    """`cari w… "<frasa>"`: halaman OCR yang memuat frasa; kalau tidak ada yang persis, yang paling mirip."""
    d, q = data(w), norma.padat(frasa)
    if len(q) < 4:
        raise ValueError("frasa terlalu pendek")
    temu = []
    for n in range(1, len(d["berkas"]) + 1):
        for h, p in enumerate(_padat(w, n), 1):
            if q in p:
                temu.append((n, h))
    for n, h in temu[:maks]:
        t = norma.norm(ocr(w, n)[h - 1])
        m = _letak(t, q)
        cuplik = t[max(0, m.start() - 60):m.end() + 60] if m else ""
        print(f"[{w}] berkas {n} hal PDF {h} (nomor cetak: {nomor_cetak(w, n, h) or '?'}): …{cuplik}…")
    if len(temu) > maks:
        print(f"… {len(temu) - maks} tempat lagi")
    if temu:
        return len(temu)
    skor = []
    for n in range(1, len(d["berkas"]) + 1):
        for h, p in enumerate(_padat(w, n), 1):
            s = _mirip(q, p)
            if s is None:
                print(f"Tidak ada yang persis «{frasa}» di OCR {w}. Pencarian mirip butuh rapidfuzz (lihat `periksa`).")
                return 0
            if s >= MIRIP_MIN:
                skor.append((s, n, h))
    for s, n, h in sorted(skor, reverse=True)[:5]:
        print(f"[{w}] berkas {n} hal PDF {h}: mirip {s:.0f}% (OCR bisa salah huruf; buka scan-nya)")
    if not skor:
        print(f"Tidak ada «{frasa}» di OCR {w}, persis atau mirip ≥{MIRIP_MIN}%.")
    return len(skor)


def kartu(w):
    """`kartu w…`: data katalog + teks OCR halaman judul (penerbit, muhaqqiq, tahun dibaca dari scan-nya) + bentuk bukti."""
    d = data(w)
    print(f"الكتاب: {d['judul']}\nالمؤلف: {d['pengarang']}\nالقسم: {d['kategori']}\nعدد الصفحات: {d['halaman']}")
    print(f"sumber: Waqfeya (dataset {DATASET}), berkas: {_daftar_berkas(w)}")
    n = berkas_judul(w)
    hh = ocr(w, n)
    print(f"--- OCR halaman judul (berkas {n}, hal PDF 1-4): data cetak disalin dari scan-nya, bukan dari teks ini ---")
    for h in range(1, min(4, len(hh)) + 1):
        print(f"[hal PDF {h}] " + re.sub(r"\s+", " ", hh[h - 1]).strip()[:400])
    print(f"scan halaman judul: {potong(w, n, 1, min(4, len(hh)))}")
    png = gambar(w, n, 1, min(4, len(hh)))
    if png:
        print("gambar: " + " ".join(map(str, png)))
    print(f"bukti: <<{w}|<berkas>|<hal PDF>>>, mis. <<{w}|1|{min(10, len(hh))}>> (hal = urutan halaman di berkas PDF; "
          f"juz/halaman cetak ditulis di catatan kakinya)")


BERKAS_JUDUL = ("الواجهة", "الغلاف", "المقدمة", "مقدمة")  # nama berkas sampul/halaman judul di dataset, urut pilihan


def berkas_judul(w):
    """Berkas yang memuat halaman judul: di dataset, sampul sering berkas tersendiri («الواجهة», 1.581 kitab) yang
    tidak selalu nomor 1."""
    nama = data(w)["berkas"]
    for x in BERKAS_JUDUL:
        for i, b in enumerate(nama, 1):
            if x in b:
                return i
    return 1


def liputan(q, teks):
    """Bagian huruf q yang terbaca berurutan di teks (keduanya `padat`), dari potongan sama ≥3 huruf: tahan salah
    huruf OCR. Pustaka bawaan Python saja, supaya putusan `cek` tidak bergantung pustaka opsional."""
    if not q:
        return 1.0
    m = difflib.SequenceMatcher(None, q, teks, autojunk=False)
    return sum(b.size for b in m.get_matching_blocks() if b.size >= 3) / len(q)


def periksa_kutipan(w, n, hal, bagian):
    """Dipakai `cek` (cek_kutipan.cek_waqfeya). bagian = potongan kutipan (dipisah ...).
    Kembalikan (keadaan, rinci): «belum» (kitab belum diunduh), «rusak» (berkas/hal salah), «persis» (semua bagian
    terbaca persis di halaman itu), «mirip» (skor), «lain» (persis di halaman lain: [(n, h)]), «tidak»."""
    if not ada(w):
        return "belum", None
    d = data(w)
    if not 1 <= n <= len(d["berkas"]):
        return "rusak", f"berkas = nomor urut 1..{len(d['berkas'])} ({_daftar_berkas(w)})"
    a, z = _rentang(hal)
    pp = _padat(w, n)
    if z > len(pp):
        return "rusak", f"berkas {n} hanya {len(pp)} halaman PDF"
    qq = [norma.padat(b) for b in bagian]
    di = "".join(pp[a - 1:z])
    if all(q in di for q in qq):
        return "persis", None
    liput = min(liputan(q, di) for q in qq)
    if liput >= LIPUT_MIRIP:
        return "mirip", round(100 * liput)
    # GAGAL «halaman lain» hanya kalau halaman yang ditulis jelas bukan tempatnya: kalimat yang diulang di kitab dan OCR
    # halaman yang benar rusak tidak boleh menyuruh pindah ke halaman yang salah
    if liput >= LIPUT_BUKAN or sum(map(len, qq)) < LAIN_MIN:
        return "tidak", None
    lain = [(m, h) for m in range(1, len(d["berkas"]) + 1) for h, p in enumerate(_padat(w, m), 1)
            if all(q in p for q in qq) and not (m == n and a <= h <= z)]
    if lain:
        return "lain", lain
    return "tidak", None


def cuplikan(w, n, hal, kutipan, sekitar=300):
    """Teks OCR di sekitar letak kutipan (untuk `bukti`), atau awal halaman kalau tidak ketemu."""
    a, z = _rentang(hal)
    t = " ".join(norma.norm(x) for x in ocr(w, n)[a - 1:z])
    m = _letak(t, norma.padat(kutipan or "")) if kutipan and len(norma.padat(kutipan)) >= 4 else None
    if m:
        return t[max(0, m.start() - sekitar):m.end() + sekitar]
    return t[:2 * sekitar]
