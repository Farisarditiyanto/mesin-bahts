# SPDX-License-Identifier: AGPL-3.0-or-later
"""Perintah kitab lewat pintu pemakai (`python mesin/bahts.py …`), untuk kerusakan yang diam-diam menyesatkan agent:
- `halaman` tidak mencetak «\\r» mentah Shamela: di konsol atau saat disalin «\\r» hilang, dua kata tersambung
  («نستعينالحمد»), lalu agent menyalinnya ke naskah dan `cek` meloloskannya karena spasi dipadatkan (kitab 11223 ص3);
- argumen atau bendera di luar bentuk perintah ditolak (kode keluar 1, tanpa hasil), bukan ditelan diam-diam:
  `katalog … --mazhab` tetap tersaring, `cari <id> … --kitab` tidak mencari di kitab pertama, `halaman … 8 9` tidak mengabaikan 9;
- `cari`/`teks`/`bab` mencocokkan kata utuh; yang menyeberang batas kata hanya disebut jumlahnya;
- `hadits` menandai riwayat yang kitabnya sudah diunduh dengan juz/halaman edisi lokal (layanan alminasa ditiru).
Kitabnya kitab CI (baris `ambil` di tes.yml)."""
import atexit, contextlib, io, json, os, re, runpy, subprocess, sys, tempfile
from pathlib import Path
from unittest.mock import patch

sys.stdout.reconfigure(encoding="utf-8")
from uji_semua import kitab_ci
from bantu import SAMPUL_UJI, salin_mesin
REPO = Path(__file__).resolve().parent.parent
SEMENTARA = tempfile.TemporaryDirectory(prefix="bahts-perintah-")
atexit.register(SEMENTARA.cleanup)
AKAR = Path(SEMENTARA.name)
salin_mesin(AKAR, ("_meta", *map(str, kitab_ci())))


def jalankan(*a):
    r = subprocess.run([sys.executable, str(AKAR / "mesin" / "bahts.py"), *a], cwd=AKAR, capture_output=True)
    # «\r\n» = akhir baris konsol Windows; «\r» lain berasal dari teks kitab
    return r.returncode, *(x.decode("utf8").replace("\r\n", "\n") for x in (r.stdout, r.stderr))


gagal = []
kode, out, err = jalankan("halaman", "11223", "-", "3")
if kode or "\r" in out:
    gagal.append(f"halaman 11223 - 3: kode {kode}, «\\r» mentah {out.count(chr(13))}")
if not any(b.startswith("الحمد لله، نحمده") for b in out.split("\n")):
    gagal.append("halaman 11223 - 3: «الحمد لله، نحمده» tidak mulai di baris sendiri (tersambung ke «﷽»)")

for a in (["halaman", "11223", "-", "3", "4"],
          ["katalog", "القضاء والقدر", "--mazhab", "hanbali"],
          ["cari", "11223", "الحمد", "--kitab", "2348"],
          ["kartu", "11223", "2348"],
          ["teks", "11223", "الحمد", "100", "2", "9"]):
    kode, out, err = jalankan(*a)
    if kode != 1 or out.strip() or "berlebih" not in err:
        gagal.append(f"{' '.join(a)}: harus ditolak (kode 1, tanpa hasil); kode {kode}, keluaran {out[:80]!r}, galat {err[:80]!r}")

# `cari`/`teks`/`bab` mencocokkan kata utuh: «العربان» tidak cocok dengan «في العرب انهم» (1082 ج3 ص280). Di uji pakai ±70% hasil
# `cari` di kitab besar menyeberang batas kata seperti itu dan agent membacanya sia-sia. Yang menyeberang disebut jumlahnya
# dan tetap bisa dilihat dengan --potongan; huruf sambung («فبيع») dan «ال» di depan kata pertama tetap cocok.
for a, harus, jangan in ((["cari", "1082", "العربان"], ["ج5 ص40", "ج5 ص41", "1 tempat lain", "--potongan"], ["ص280"]),
                         (["teks", "1082", "العربان", "80", "5"], ["ج5 ص40", "ج5 ص41", "1 tempat lain"], ["ص280"]),
                         (["bab", "1082", "العربان"], ["ج5 ص40"], ["ص280"]),
                         (["cari", "1082", "العربان", "--potongan"], ["ج3 ص280", "ج5 ص40", "ج5 ص41"], ["tempat lain"]),
                         (["cari", "1082", "بيع العربان"], ["ج5 ص41"], []),
                         # batas kata di dalam frasa: «الحديثان» bukan «وفي الحديث ان الشيطان» (ج1 ص192): 17 kata utuh,
                         # 131 potongan («الحديث انه», «الحديث ان»)
                         (["cari", "1082", "الحديثان"], ["ج1 ص268", "dari 17 tempat", "131 tempat lain"], ["ص192"]),
                         (["cari", "1082", "عربان"], ["ج5 ص40", "ج5 ص41"], ["ص280"]),
                         (["cari", "semua", "العربان"], ["[1082] ج5 ص40"], ["[1082] ج3 ص280"])):
    kode, out, err = jalankan(*a)
    salah = [h for h in harus if h not in out] + [f"ada {j}" for j in jangan if j in out]
    if kode or salah:
        gagal.append(f"{' '.join(a)}: kode {kode}, {salah}; keluaran {out[:300]!r} {err[-200:]!r}")
# `kartu`: data cetak disalin apa adanya ke catatan kaki, jadi gelar di awal nama muhaqqiq dibuang («إلغاء الألقاب»،
# أبو سليمان ص175-176); «الشيخ» di tengah nama adalah bagian nama («يوسف الشيخ محمد البقاعي», 11825)
for sid, harus, jangan in (("2348", "تعليق وتحقيق: ماهر ياسين الفحل", "الدكتور ماهر"),
                           ("11825", "راجعه: يوسف الشيخ محمد البقاعي", None)):
    kode, out, err = jalankan("kartu", sid)
    if kode or harus not in out or (jangan and jangan in out):
        gagal.append(f"kartu {sid}: harus memuat «{harus}»" + (f" tanpa «{jangan}»" if jangan else "") + f"; keluaran {out[:300]!r}")
# `kartu`: bukti siap pakai di baris terakhirnya memakai juz yang diterima `cek` (kitab berjilid tidak ditulis «-»,
# juga yang halamannya bersambung) dan halaman yang terbaca
(AKAR / "uji-kartu").mkdir()


def cek_bukti(bukti):
    (AKAR / "uji-kartu" / "naskah.txt").write_text(
        f"@judul: اختبار\n{SAMPUL_UJI}@tanpa: pustaka\n#K مقدمة\nهذا معنى[^انظر: كتاب، ص5. {bukti}].\n", encoding="utf8")
    return jalankan("cek", "uji-kartu")[1]


if "kitab 1082 berjilid: tulis juz-nya" not in cek_bukti("<<1082|-|5>>"):
    gagal.append("cek: juz «-» di kitab berjilid (1082) tidak ditolak")
for sid in kitab_ci():
    bukti = jalankan("kartu", str(sid))[1].strip().splitlines()[-1]
    m = (re.search(rf"<<{sid}\|([^|<>]+)\|(\d+)>>", bukti)
         or re.search(rf"<<{sid}\|(-)\|<hal>>> \(kitab satu jilid: juz \"-\"; halaman (\d+)-", bukti))
    if not m:
        gagal.append(f"kartu {sid}: baris terakhir bukan bukti siap pakai: {bukti!r}")
        continue
    juz, hal = m.groups()
    if jalankan("halaman", str(sid), juz, hal)[0]:
        gagal.append(f"kartu {sid}: halaman {juz}/{hal} dari baris bukti tidak terbaca")
    if "berjilid" in cek_bukti(f"<<{sid}|{juz}|{hal}>>"):
        gagal.append(f"kartu {sid}: juz «{juz}» dari baris bukti ditolak `cek`: {bukti!r}")
kode, out, err = jalankan("kartu", "11223", "--potongan")
if kode != 1 or "berlebih" not in err:
    gagal.append(f"kartu 11223 --potongan: harus ditolak (bendera hanya untuk cari/teks/bab); kode {kode}, galat {err[:80]!r}")
for a in (["cari", "1082", "العربان", "--potongan", "--potongan"],
          ["teks", "1082", "العربان", "--potongan", "--potongan"]):
    kode, out, err = jalankan(*a)
    if kode != 1 or "disebut lebih dari sekali" not in err:
        gagal.append(f"{' '.join(a)}: bendera kembar harus ditolak dengan pesan ganda; kode {kode}, galat {err[:120]!r}")
kode, out, err = jalankan("cari", "w0123abcd", "الحمد", "--potongan")
if kode != 1 or "Traceback" in err or "--potongan" not in err:
    gagal.append(f"cari w… --potongan: harus ditolak dengan pesan jelas; kode {kode}, galat {err[:120]!r}")
if os.name == "nt":
    kode, out, err = jalankan("periksa")
    baris_sm = [b for b in out.splitlines() if "Sakkal Majalla" in b]
    if not baris_sm or "jakarta" not in baris_sm[0]:
        gagal.append(f"periksa: Sakkal Majalla harus menyebut profil jakarta (huruf_judul); dapat {baris_sm!r}")

# `hadits`: juz/halaman layanan bisa dari edisi lain (uji pakai: Ibn Majah 2192 «3/311» edisi Risalah, padahal edisi lokal
# 1198 = 2/738; takhrij yang memercayainya tidak lolos `cek`). Riwayat yang kitabnya sudah diunduh diberi juz/halaman kepala
# hadits «n -» di edisi lokal: Bukhari 1 = 1681 1/6, Muslim 1907 = 1727 3/1515, Bukhari 856 = 1/171 (rekamannya mulai
# ص170: halaman penanda, bukan halaman rekaman). Kitab yang belum diunduh tidak ditandai.
sys.path.insert(0, str(AKAR / "mesin"))
import jaringan

riwayat = [("صحيح البخاري", 1), ("صحيح البخاري", 856), ("صحيح مسلم", 1907), ("مسند أحمد", 1), ("صحيح البخاري", 999999)]
jawaban = {"hits": {"total": {"value": len(riwayat)}, "hits": [
    {"_id": str(i), "_source": {"book_name": k, "number": [n], "editions": [{"volume": 9, "page": 999, "edition": "طبعة أخرى"}],
                                "matn": "متن"}} for i, (k, n) in enumerate(riwayat)]}}
keluar = io.StringIO()
keluar.reconfigure = lambda **kw: None
with patch.object(sys, "argv", [str(AKAR / "mesin" / "bahts.py"), "hadits", "إنما الأعمال بالنيات"]), \
        patch.object(jaringan, "buka", side_effect=lambda *a, **kw: io.BytesIO(json.dumps(jawaban).encode("utf8"))), \
        contextlib.redirect_stdout(keluar):
    try:
        runpy.run_path(str(AKAR / "mesin" / "bahts.py"), run_name="__main__")
    except SystemExit as e:
        if e.code:
            gagal.append(f"hadits (layanan tiruan): keluar {e.code}")
blok = keluar.getvalue().split("\n\n")
lokal = lambda k, n: next((b for b in blok if b.startswith(f"{k}، رقم {n}،")), "")
for k, n, harus in (("صحيح البخاري", 1, "edisi lokal 1681: 1/6"), ("صحيح البخاري", 856, "edisi lokal 1681: 1/171"),
                    ("صحيح مسلم", 1907, "edisi lokal 1727: 3/1515"),
                    ("صحيح البخاري", 999999, "tidak ketemu sebagai kepala hadits")):
    if harus not in lokal(k, n):
        gagal.append(f"hadits {k} {n}: tidak ada «{harus}»: {lokal(k, n)!r}")
if "SUDAH DIUNDUH" in lokal("مسند أحمد", 1) or "edisi lain" not in keluar.getvalue():
    gagal.append(f"hadits: kitab yang belum diunduh ditandai, atau peringatan edisi lain hilang: {keluar.getvalue()[-600:]!r}")

# Penolakan bendera duplikat/tak-dikenal, `baru` perangkat Windows, `--fasl --fasl`, `kartu` putus, `sumber_tertimpa` khulasah
uji_cli = AKAR / "uji-cli"
uji_cli.mkdir()
dasar_contoh = (REPO / "contoh" / "naskah.txt").read_text(encoding="utf8")
(uji_cli / "naskah.txt").write_text(dasar_contoh, encoding="utf8")
(uji_cli / "riset.txt").write_text("tafsir 1:2\ncari توحيد الربوبية\n", encoding="utf8")

for cmd_salah in (["cek", "--salah"], ["cek", "--salah", "uji-cli"], ["tahap", "--salah"],
                  ["rakit", "uji-cli", "--fasl", "--fasl"], ["rakit", "uji-cli", "--fasl", "1", "--fasl", "2"]):
    kode, out, err = jalankan(*cmd_salah)
    if kode != 1 or out.strip() or "Traceback" in err:
        gagal.append(f"{' '.join(cmd_salah)}: harus ditolak (kode 1, tanpa stdout): kode {kode}, out {out[:80]!r}, err {err[:80]!r}")
    if "--salah" in cmd_salah and "'--salah'" not in err:
        gagal.append(f"{' '.join(cmd_salah)}: pesan galat harus menyebut '--salah', bukan argumen folder: {err[:120]!r}")

for dev in ("CON", "nul", "PRN", "AUX", "COM1", "LPT9", "bahts/ahmad/CON", "bahts/NUL/topik"):
    kode, out, err = jalankan("baru", dev, "عنوان")
    induk_uji = AKAR / Path(dev).parent
    ada_folder = induk_uji.is_dir() and any(p.name.casefold() == Path(dev).name.casefold() for p in induk_uji.iterdir())
    if kode != 1 or "perangkat Windows" not in err or ada_folder:
        gagal.append(f"baru {dev}: nama perangkat Windows harus ditolak: kode {kode}, err {err[:120]!r}")
kode, out, err = jalankan("baru", "COM10", "عنوان")
if kode or not (AKAR / "COM10" / "naskah.txt").is_file():
    gagal.append(f"baru COM10: nama sah ditolak: kode {kode}, err {err[:120]!r}")

# `kartu`: unduhan terpotong (hanya book_metadata.json tanpa pages.jsonl.gz) gagal ramah tanpa Traceback
putus = AKAR / "kitab" / "990099"
putus.mkdir()
(putus / "book_metadata.json").write_text('{"betaka_text":"الكتاب: تجربة"}', encoding="utf8")
kode, out, err = jalankan("kartu", "990099")
if kode != 1 or "Traceback" in err or ("belum diunduh" not in err and "TIDAK ADA" not in err):
    gagal.append(f"kartu putus: harus gagal ramah tanpa Traceback: kode {kode}, err {err[:120]!r}")

# `olah.sumber_tertimpa` melindungi file khulasah
(uji_cli / "naskah.txt").write_text(
    "@berkas: hasil\n" + dasar_contoh.replace(
        "#K الخاتمة", 'معنى[^انظر: دراسة، ص1. <<luar|hasil - الخلاصات.pdf|1>>].\n#K الخاتمة'
    ), encoding="utf8",
)
kode, out, err = jalankan("cek", "uji-cli")
if kode != 1 or "menimpa bahan sumber" not in (out + err):
    gagal.append(f"sumber_tertimpa khulasah tidak ditolak: kode {kode}, out {out[:200]!r}")

for g in gagal:
    print("✗ " + g)
print(f"perintah: {len(gagal)} gagal")
sys.exit(1 if gagal else 0)
