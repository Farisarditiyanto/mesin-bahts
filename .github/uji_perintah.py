# SPDX-License-Identifier: AGPL-3.0-or-later
"""Perintah kitab lewat pintu pemakai (`python mesin/bahts.py …`), untuk kerusakan yang diam-diam menyesatkan agent:
- `halaman` tidak mencetak «\\r» mentah Shamela: di konsol atau saat disalin «\\r» hilang, dua kata tersambung
  («نستعينالحمد»), lalu agent menyalinnya ke naskah dan `cek` meloloskannya karena spasi dipadatkan (kitab 11223 ص3);
- argumen atau bendera di luar bentuk perintah ditolak (kode keluar 1, tanpa hasil), bukan ditelan diam-diam:
  `katalog … --mazhab` tetap tersaring, `cari <id> … --kitab` tidak mencari di kitab pertama, `halaman … 8 9` tidak mengabaikan 9;
- `cari`/`teks`/`bab` mencocokkan kata utuh; yang menyeberang batas kata hanya disebut jumlahnya;
- `hadits` menandai riwayat yang kitabnya sudah diunduh dengan juz/halaman edisi lokal (layanan alminasa ditiru).
Kitabnya kitab CI (baris `ambil` di tes.yml)."""
import atexit, contextlib, io, json, runpy, shutil, subprocess, sys, tempfile
from pathlib import Path
from unittest.mock import patch

sys.stdout.reconfigure(encoding="utf-8")
from uji_semua import kitab_ci
REPO = Path(__file__).resolve().parent.parent
SEMENTARA = tempfile.TemporaryDirectory(prefix="bahts-perintah-")
atexit.register(SEMENTARA.cleanup)
AKAR = Path(SEMENTARA.name)
shutil.copytree(REPO / "mesin", AKAR / "mesin", ignore=shutil.ignore_patterns("_tmp", "__pycache__"))
for sid in ("_meta", *map(str, kitab_ci())):
    shutil.copytree(REPO / "kitab" / sid, AKAR / "kitab" / sid)


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
kode, out, err = jalankan("kartu", "11223", "--potongan")
if kode != 1 or "berlebih" not in err:
    gagal.append(f"kartu 11223 --potongan: harus ditolak (bendera hanya untuk cari/teks/bab); kode {kode}, galat {err[:80]!r}")

# `hadits`: juz/halaman layanan bisa dari edisi lain (uji pakai: Ibn Majah 2192 «3/311» edisi Risalah, padahal edisi lokal
# 1198 = 2/738; takhrij yang memercayainya tidak lolos `cek`). Riwayat yang kitabnya sudah diunduh diberi juz/halaman kepala
# hadits «n -» di edisi lokal: Bukhari 1 = 1681 1/6, Muslim 1907 = 1727 3/1515, Bukhari 856 = 1/171 (rekamannya mulai
# ص170: halaman penanda, bukan halaman rekaman). Kitab yang belum diunduh tidak ditandai.
sys.path.insert(0, str(AKAR / "mesin"))
import hadits

riwayat = [("صحيح البخاري", 1), ("صحيح البخاري", 856), ("صحيح مسلم", 1907), ("مسند أحمد", 1), ("صحيح البخاري", 999999)]
jawaban = {"hits": {"total": {"value": len(riwayat)}, "hits": [
    {"_id": str(i), "_source": {"book_name": k, "number": [n], "editions": [{"volume": 9, "page": 999, "edition": "طبعة أخرى"}],
                                "matn": "متن"}} for i, (k, n) in enumerate(riwayat)]}}
keluar = io.StringIO()
keluar.reconfigure = lambda **kw: None
with patch.object(sys, "argv", [str(AKAR / "mesin" / "bahts.py"), "hadits", "إنما الأعمال بالنيات"]), \
        patch.object(hadits, "buka", side_effect=lambda *a, **kw: io.BytesIO(json.dumps(jawaban).encode("utf8"))), \
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

for g in gagal:
    print("✗ " + g)
print(f"perintah: {len(gagal)} gagal")
sys.exit(1 if gagal else 0)
