# SPDX-License-Identifier: AGPL-3.0-or-later
"""`takhrij` dan `tafsir` (layanan Shamela offline) lewat pintu pemakai, untuk kerusakan yang diam-diam menyesatkan agent:
- nomor halaman Shamela (shamela_page_id) dibaca dari indeks, bukan dianggap sama dengan urutan rekaman: di صحيح البخاري
  (1681) 11207 dari 11208 rekaman berbeda, jadi tebakan urutan menunjuk halaman yang salah;
- indeks sah buatan mesin lama (tanpa kolom «sp») dibuat ulang sekali, bukan dipakai tanpa nomor itu;
- hadits Bukhari 97 (1/31) ditunjuk juga di Bukhari 2544 (3/149) dan di النسائي (829), urut dari pengarang yang lebih
  dulu wafat;
- `tafsir 2:219` menunjuk الطبري (7798) sebelum زاد المسير (23619) sebelum ابن كثير (1503); ayat yang tidak ada ditolak.
Kitabnya 1681 dari baris `ambil` tes.yml; tabel layanan dari `siapkan`."""
import atexit, json, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent.parent
SEMENTARA = tempfile.TemporaryDirectory(prefix="bahts-layanan-")
atexit.register(SEMENTARA.cleanup)
AKAR = Path(SEMENTARA.name)
shutil.copytree(REPO / "mesin", AKAR / "mesin", ignore=shutil.ignore_patterns("_tmp", "__pycache__"))
for sid in ("_meta", "1681"):
    shutil.copytree(REPO / "kitab" / sid, AKAR / "kitab" / sid)


def jalankan(*a):
    r = subprocess.run([sys.executable, str(AKAR / "mesin" / "bahts.py"), *a], cwd=AKAR, capture_output=True)
    return r.returncode, *(x.decode("utf8").replace("\r\n", "\n") for x in (r.stdout, r.stderr))


gagal = []
# indeks mesin lama: sah, tetapi tanpa nomor halaman Shamela
f = AKAR / "kitab" / "1681" / "indeks.json"
d = json.loads(f.read_text(encoding="utf8"))
d.pop("sp", None)
f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf8")

kode, out, err = jalankan("takhrij", "1681", "1", "31")
if kode:
    gagal.append(f"takhrij 1681 1 31: kode {kode}: {err[-300:]}")
for harus in ("ج1 ص31 (رقم 97)", "ج3 ص149 (رقم 2544)", "[829] سنن النسائي"):
    if harus not in out:
        gagal.append(f"takhrij 1681 1 31: tidak ada «{harus}»")
blok = out.split("ج1 ص31 (رقم 97)")[0].rsplit("== hadits", 1)[-1]
if not blok.index("[1456]") < blok.index("[1681]"):
    gagal.append("takhrij 1681 1 31: الطيالسي (ت 204) tidak sebelum البخاري (ت 256)")
if not isinstance(json.loads(f.read_text(encoding="utf8")).get("sp"), list):
    gagal.append("indeks.json tanpa «sp» tidak dibuat ulang")

kode, out, err = jalankan("tafsir", "2:219")
urutan = [out.find(f"[{s}]") for s in (7798, 23619, 1503)]
if kode or -1 in urutan or urutan != sorted(urutan):
    gagal.append(f"tafsir 2:219: kode {kode}, letak الطبري/زاد المسير/ابن كثير {urutan}")
kode, out, err = jalankan("tafsir", "2:287")
if kode != 1 or "286 ayat" not in out + err:
    gagal.append(f"tafsir 2:287: kode {kode}, ayat yang tidak ada tidak ditolak")

print("\n".join(gagal) or "layanan: semua lolos")
sys.exit(1 if gagal else 0)
