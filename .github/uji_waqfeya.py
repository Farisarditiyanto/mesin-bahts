# SPDX-License-Identifier: AGPL-3.0-or-later
"""Kitab Waqfeya (mesin/waqfeya.py) lewat pintu pemakai, tanpa internet: satu kitab tiruan 3 halaman OCR + PDF.
Yang dijaga:
- `cek` tidak menilai lafaz kutipan Waqfeya (OCR salah huruf): kutipan yang terbaca persis, mirip, atau tidak terbaca di
  OCR sama-sama tanpa GAGAL dan tanpa perhatian; `bukti` yang mencetak hasil OCR-nya untuk pemeriksa (yang membaca scan);
- GAGAL hanya untuk yang pasti salah: kutipan yang terbaca persis di halaman lain (bukan di halaman yang ditulis), kitab
  belum diunduh, halaman di luar berkas, bentuk bukti rusak; kutipan pendek yang ada di halaman lain bukan GAGAL;
- ringkasan `cek` menghitung bukti Waqfeya sendiri, dan catatan kakinya tidak terdaftar «tanpa bukti»;
- nomor halaman cetak dibaca dari baris yang isinya nomor saja («- ٢ -»), bukan dari nomor catatan kaki «(٣) قال…»;
- kalimat yang diulang di kitab: kutipan yang benar di halaman yang OCR-nya rusak tidak disuruh pindah ke halaman lain
  (putusan `cek` tidak bergantung rapidfuzz: dulu tanpa rapidfuzz kasus ini GAGAL);
- bukti Waqfeya + bukti Shamela berpotongan di satu catatan kaki tidak GAGAL palsu (halaman cetak Waqfeya, kutipan);
- kitab Waqfeya yang judulnya kitab Shamela = perhatian (pakai Shamela kalau edisinya sama);
- `kartu` membaca halaman judul dari berkas sampul («الواجهة»), bukan selalu berkas 1;
- `halaman`, `kartu`, `cari`, `bukti` mencetak OCR + scan; `ambil <folder>` mengenali nomor w… di naskah."""
import atexit, gzip, json, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent.parent
SEMENTARA = tempfile.TemporaryDirectory(prefix="bahts-waqfeya-")
atexit.register(SEMENTARA.cleanup)
AKAR = Path(SEMENTARA.name)
shutil.copytree(REPO / "mesin", AKAR / "mesin", ignore=shutil.ignore_patterns("_tmp", "__pycache__"))
(AKAR / "kitab" / "_meta").mkdir(parents=True)
shutil.copy(REPO / "kitab" / "_meta" / "book_metadata.parquet", AKAR / "kitab" / "_meta")  # katalog: `siapkan`
shutil.copytree(REPO / "kitab" / "11223", AKAR / "kitab" / "11223")  # kitab contoh/naskah.txt (baris `ambil` tes.yml)

W = "w0123abcd"
HALAMAN = [
    # kalimat hal 2 diulang di sini, OCR-nya rusak berat (liputan 0,83: di bawah «mirip», di atas «jelas bukan»)
    "- ١ -\nبسم الله الرحمن الرحيم هذا كتاب تجريبي في النحو والصرف وضعه المؤلف للمبتدئين\n"
    "فنرفع مآ كن مبيدا عل آنه اسمهآ تشببهآ لة بالقاعل\n",
    "- ٢ -\nفترفع ما كان مبتدأ على أنه اسمها تشبيها له بالفاعل وتنصب ما كان خبرا على أنه خبرها\n"
    "(١) قال ابن إياز في المحصول ورقة تسعين\n",
    # «للتراحي»: salah huruf OCR; «(٢)» di sini + «(١)» di hal 2 membuat aturan longgar membaca hal 2 sebagai «1»
    "- ٣ -\nوأفعال أخر تسمى أفعال المقاربة ومنها فعلان للتراحي وهما عسى وأوشك له بالفاعل\n(٢) انظر المحصول\n",
]
SAMPUL = ["كتاب تجريبي تحقيق محقق تجريبي دار السلام المصرية\n"]  # berkas 2 «الواجهة» (sampul tersendiri)
d = AKAR / "kitab" / "waqfeya" / W
d.mkdir(parents=True)
from pypdf import PdfWriter  # noqa: E402 (pypdf dari requirements.txt)
for n, hh in ((1, HALAMAN), (2, SAMPUL)):
    with gzip.open(d / f"{n}.txt.gz", "wt", encoding="utf-8") as f:
        f.write("\nPAGE_SEPARATOR\n".join(hh))
    pdf = PdfWriter()
    for _ in hh:
        pdf.add_blank_page(300, 400)
    with open(d / f"{n}.pdf", "wb") as f:
        pdf.write(f)
(d / "kitab.json").write_text(json.dumps({"nomor": W, "judul": "كتاب تجريبي", "pengarang": "محمد بن أحمد الفارضي",
                                          "kategori": "النحو والصرف", "halaman": 4, "berkas": ["الكتاب", "الواجهة"]},
                                         ensure_ascii=False), encoding="utf-8")

SUMBER = "كتاب تجريبي، مؤلف تجريبي، دار تجريبية، القاهرة، 1400هـ،"
BARIS = {
    "persis": f'قال: "فترفع ما كان مبتدأ على أنه اسمها تشبيها له بالفاعل"[^{SUMBER} ص2. <<{W}|1|2>>].',
    "mirip": f'قال: "وأفعال أخر تسمى أفعال المقاربة ومنها فعلان للتراخي"[^{SUMBER} ص3. <<{W}|1|3>>].',
    "tidak": f'قال: "هذا كلام لا وجود له في الكتاب أبدا ولا في غيره"[^{SUMBER} ص1. <<{W}|1|1>>].',
    "pendek": f'قال: "تشبيها له"[^{SUMBER} ص1. <<{W}|1|1>>].',
    "makna": f"والأفعال الناقصة ترفع المبتدأ وتنصب الخبر[^انظر: {SUMBER} ص2. <<{W}|1|2>>].",
    # catatan kaki tanpa nomor halaman tercetak: tanpa penghitungan Waqfeya ia masuk daftar «tanpa bukti»
    "tanpa_hal": f'قال: "فترفع ما كان مبتدأ على أنه اسمها"[^كتاب تجريبي، مؤلف تجريبي. <<{W}|1|2>>].',
    "ulang": f'قال: "فترفع ما كان مبتدأ على أنه اسمها تشبيها له بالفاعل"[^{SUMBER} ص1. <<{W}|1|1>>].',
    "campur": f'قال: "فترفع ما كان مبتدأ على أنه اسمها تشبيها له بالفاعل"[^{SUMBER} ص2؛ رسالة في القضاء والقدر، '
              f'محمد بن صالح العثيمين، دار الوطن، 1423هـ، ص5. <<{W}|1|2>> <<11223|-|5|توحيد الربوبية>>].',
    "huruf_besar": f'قال: "فترفع ما كان مبتدأ على أنه اسمها"[^{SUMBER} ص2. <<W0123ABCD|1|2>>].',
    "lain": f'قال: "وتنصب ما كان خبرا على أنه خبرها"[^{SUMBER} ص3. <<{W}|1|3>>].',
    "belum": f'قال: "هذا كلام لا وجود له في الكتاب أبدا"[^{SUMBER} ص1. <<w9999eeee|1|1>>].',
    "rusak": f'قال: "فترفع ما كان مبتدأ على أنه اسمها"[^{SUMBER} ص9. <<{W}|1|9>>].',
    "bentuk": f'قال: "فترفع ما كان مبتدأ على أنه اسمها"[^{SUMBER} ص2. <<w12|1|2>>].',
}
HARUS = {  # potongan pesan `cek` (None = tidak ada GAGAL atau perhatian apa pun soal bukti Waqfeya-nya)
    "persis": None, "mirip": None, "tidak": None, "pendek": None, "makna": None, "tanpa_hal": None, "ulang": None,
    "campur": None, "huruf_besar": "ditulis huruf kecil, mis. <<w0123abcd|1|2>>",
    "lain": "tetapi terbaca persis di berkas 1 hal PDF 2",
    "belum": "kitab Waqfeya w9999eeee belum diunduh",
    "rusak": "berkas 1 hanya 3 halaman PDF",
    "bentuk": "<<w12|1|2>>: bentuknya <<w…|berkas|hal>>",
}
GAGAL = {"lain", "belum", "rusak", "bentuk", "huruf_besar"}
CIRI = ("w0123abcd", "w9999eeee", "w12|", "W0123ABCD", "11223", "القضاء والقدر", "-/2")


def jalankan(*a):
    r = subprocess.run([sys.executable, str(AKAR / "mesin" / "bahts.py"), *a], cwd=AKAR, capture_output=True)
    return r.returncode, *(x.decode("utf8").replace("\r\n", "\n") for x in (r.stdout, r.stderr))


def naskah(baris):
    f = AKAR / "bahts" / "uji"
    f.mkdir(parents=True, exist_ok=True)
    teks = ["@judul: بحث تجريبي", "@nama: طالب تجريبي", "@minimal_halaman: 0", "", "#K المقدمة", baris, "",
            "#K الخاتمة", "أهم النتائج: لا شيء.", "", "#R المصادر والمراجع", "كتاب تجريبي، مؤلف تجريبي.", ""]
    (f / "naskah.txt").write_text("\n".join(teks), encoding="utf-8")
    return "bahts/uji"


gagal = []
for apa, baris in BARIS.items():
    kode, out, err = jalankan("cek", naskah(baris))
    semua = out + err
    soal = [b.strip()[:160] for b in semua.splitlines() if b.lstrip().startswith(("✗", "!")) and any(c in b for c in CIRI)]
    if HARUS[apa] is None and soal:
        gagal.append(f"{apa}: bukti Waqfeya yang tidak pasti salah malah jadi GAGAL/perhatian: {soal}")
    if HARUS[apa] is not None and HARUS[apa] not in semua:
        gagal.append(f"{apa}: tidak ada «{HARUS[apa]}»: {semua[-700:]}")
    if (apa in GAGAL) != (kode != 0):
        gagal.append(f"{apa}: kode keluar {kode} ({'harus GAGAL' if apa in GAGAL else 'harus lolos'}): {semua[-500:]}")
    if apa == "persis":
        if "Waqfeya <<w…>> (lafaz dinilai pemeriksa dari scan): 1" not in semua:
            gagal.append(f"persis: ringkasan tidak menghitung bukti Waqfeya: {semua[:300]}")
        if "<<luar>> (tidak dicek mesin)" in semua:
            gagal.append("persis: bukti Waqfeya dihitung sebagai <<luar>>")
    tanpa = next((b for b in semua.splitlines() if b.startswith("catatan kaki tanpa bukti")), "")
    if HARUS[apa] is None and not tanpa.endswith(": 0"):
        gagal.append(f"{apa}: catatan kaki berbukti Waqfeya terdaftar «tanpa bukti»: {tanpa}")

# kitab yang ada di Shamela (رسالة في القضاء والقدر = 11223) dirujuk lewat Waqfeya: perhatian
kode, out, err = jalankan("cek", naskah(f'قال: "فترفع ما كان مبتدأ على أنه اسمها"[^رسالة في القضاء والقدر، محمد بن '
                                       f'صالح العثيمين، ص2. <<{W}|1|2>>].'))
if "«رسالة في القضاء والقدر» ada di Shamela (nomor 11223)" not in out:
    gagal.append(f"judul Shamela lewat Waqfeya tidak jadi perhatian: {(out + err)[-500:]}")

# catatan kaki menyebut kitab lain dari kitab Waqfeya buktinya: perhatian (seperti kitab_lain untuk bukti Shamela)
kode, out, err = jalankan("cek", naskah(f'قال: "فترفع ما كان مبتدأ على أنه اسمها"[^المحصول، الرازي، 1/2. <<{W}|1|2>>].'))
if "tidak menyebut judul kitab buktinya «كتاب تجريبي»" not in out:
    gagal.append(f"judul kitab lain di catatan kaki berbukti Waqfeya tidak jadi perhatian: {(out + err)[-500:]}")
# penanda «ada di Shamela»: judul Shamela berakhiran nama pengarang «المحصول للرازي» (2022) = awal judul Waqfeya
r = subprocess.run([sys.executable, "-c", "import waqfeya; print(waqfeya._di_shamela({'judul': 'المحصول في علم أصول الفقه',"
                    " 'pengarang': 'فخر الدين الرازي'}))"], cwd=AKAR / "mesin", capture_output=True, text=True,
                   encoding="utf-8")
if "2022" not in r.stdout:
    gagal.append(f"_di_shamela tidak mengenali «المحصول للرازي» (2022): {r.stdout[-200:]} {r.stderr[-300:]}")
# judul sama, pengarang lain: «شرح منتهى الإرادات» البهوتي bukan Shamela 776 (ابن النجار)
r = subprocess.run([sys.executable, "-c", "import waqfeya; print(waqfeya._di_shamela({'judul': 'شرح منتهى الإرادات (ت_ التركي)',"
                    " 'pengarang': 'منصور بن يونس البهوتي'}))"], cwd=AKAR / "mesin", capture_output=True, text=True,
                   encoding="utf-8")
if "776" in r.stdout or r.returncode:
    gagal.append(f"_di_shamela menunjuk kitab Shamela pengarang lain: {r.stdout[-200:]} {r.stderr[-300:]}")
# kitab disebut lewat pengarangnya («الفارضي») = menyebut kitab buktinya; kata judul umum («تفسير القرآن») tidak cukup
for isi, harus_perhatian in (("الفارضي، ص2.", False), ("تفسير القرآن العظيم، ص2.", True)):
    kode, out, err = jalankan("cek", naskah(f'قال: "فترفع ما كان مبتدأ على أنه اسمها"[^{isi} <<{W}|1|2>>].'))
    if ("tidak menyebut judul kitab buktinya" in out) != harus_perhatian:
        gagal.append(f"judul kitab di «{isi}»: perhatian {'tidak muncul' if harus_perhatian else 'palsu'}: {out[-400:]}")

naskah("\n".join(BARIS[x] for x in ("persis", "mirip", "tidak")))
kode, out, err = jalankan("bukti", "bahts/uji")
for harus in ("kutipan terbaca persis di OCR", "kutipan mirip", "kutipan TIDAK terbaca di OCR", f"halaman {W} 1 2"):
    if harus not in out:
        gagal.append(f"bukti: tidak ada «{harus}»: {(out + err)[-600:]}")

kode, out, err = jalankan("ambil", "bahts/uji")
if f"{W} sudah ada" not in out:
    gagal.append(f"ambil <folder>: nomor Waqfeya di naskah tidak dikenali: {(out + err)[-300:]}")

kode, out, err = jalankan("halaman", W, "1", "2")
for harus in ("nomor cetak terbaca: 2", "تشبيها له بالفاعل", "1-2.pdf"):
    if harus not in out:
        gagal.append(f"halaman {W} 1 2: tidak ada «{harus}» (kode {kode}: {(out + err)[-300:]})")
kode, out, err = jalankan("halaman", W, "1", "3")
if "nomor cetak terbaca: 3" not in out:
    gagal.append(f"halaman {W} 1 3: nomor cetak tidak terbaca 3: {out[:200]}")
kode, out, err = jalankan("halaman", W, "1", "9")
if not kode or "hanya 3 halaman" not in out + err:
    gagal.append(f"halaman di luar berkas tidak ditolak: kode {kode} {(out + err)[-200:]}")

kode, out, err = jalankan("kartu", W)
if kode or f"<<{W}|1|" not in out or "دار السلام المصرية" not in out or "berkas 2" not in out:
    gagal.append(f"kartu {W}: kode {kode}: {(out + err)[-300:]}")
kode, out, err = jalankan("cari", W, "تشبيها له بالفاعل")
if kode or "hal PDF 2" not in out:
    gagal.append(f"cari {W}: kode {kode}: {(out + err)[-300:]}")

# unduhan/metadata yang tidak lengkap: ditunjuk `ambil`, bukan Traceback; `ambil` hanya mengunduh yang kurang
utuh = (d / "kitab.json").read_bytes()
for isi in (b"{", b"null", b"[]", b"{}"):
    (d / "kitab.json").write_bytes(isi)
    kode, out, err = jalankan("kartu", W)
    if kode != 1 or "belum lengkap" not in out + err or "Traceback" in err:
        gagal.append(f"kitab.json rusak {isi!r} tidak menunjuk `ambil`: kode {kode}: {(out + err)[-200:]}")
(d / "kitab.json").write_bytes(utuh)
pdf_utuh = (d / "1.pdf").read_bytes()
(d / "1.pdf").write_bytes(b"")
kode, out, err = jalankan("kartu", W)
if kode != 1 or "belum lengkap" not in out + err:
    gagal.append(f"PDF kosong masih dianggap kitab lengkap: kode {kode}: {(out + err)[-200:]}")
ANAK = f"""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
import shamela, waqfeya
from berkas import sementara
W = {W!r}
dipanggil = []
def unduh(url, tujuan, buka):  # jaringan ditiru: tulis isi tiruan lewat jalan yang sama dengan unduhan asli
    dipanggil.append(tujuan.name)
    with sementara(tujuan) as part, buka(part) as f:
        f.write(b"%PDF-tiruan" if tujuan.suffix == ".pdf" else b"teks")
waqfeya.katalog = lambda: {{W: dict(judul="كتاب تجريبي", pengarang="x", kategori="x", halaman=4, folder="x",
                                   berkas=[dict(nama=n, pdf="a.pdf", txt="a.txt") for n in ("الكتاب", "الواجهة")])}}
shamela._unduh = unduh
waqfeya.ambil(W)
print(json.dumps(dipanggil))
"""
r = subprocess.run([sys.executable, "-c", ANAK], cwd=AKAR / "mesin", capture_output=True, text=True, encoding="utf-8",
                   errors="replace")
if r.stdout.strip().splitlines()[-1:] != ['["1.pdf"]']:
    gagal.append(f"`ambil` kitab yang PDF-nya kosong tidak mengunduh ulang PDF itu saja: {r.stdout[-300:]} {r.stderr[-300:]}")
(d / "1.pdf").write_bytes(pdf_utuh)
(d / "kitab.json").write_bytes(utuh)
# potongan scan yang penulisannya putus tidak tertinggal sebagai cache «sudah ada»
POTONG_PUTUS = f"""
import waqfeya
from pypdf import PdfWriter
def putus(self, f):
    f.write(b"%PDF-separuh")
    raise OSError("penulisan putus")
PdfWriter.write = putus
try:
    waqfeya.potong({W!r}, 1, 2, 2)
except OSError:
    pass
"""
(d / "potong" / "1-2.pdf").unlink(missing_ok=True)
subprocess.run([sys.executable, "-c", POTONG_PUTUS], cwd=AKAR / "mesin", capture_output=True)
if (d / "potong" / "1-2.pdf").exists():
    gagal.append("potongan PDF yang penulisannya putus tertinggal dan nanti dipakai sebagai cache")
kode, out, err = jalankan("halaman", W, "1", "2")
if kode or not (d / "potong" / "1-2.pdf").read_bytes().startswith(b"%PDF"):
    gagal.append(f"`halaman` sesudah tulisan putus tidak membuat potongan utuh: kode {kode}: {(out + err)[-200:]}")

print("waqfeya: " + ("semua lolos" if not gagal else f"{len(gagal)} gagal"))
for g in gagal:
    print("GAGAL:", g)
sys.exit(1 if gagal else 0)
