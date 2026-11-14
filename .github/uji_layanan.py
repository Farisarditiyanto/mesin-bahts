# SPDX-License-Identifier: AGPL-3.0-or-later
"""`takhrij` dan `tafsir` (layanan Shamela offline) lewat pintu pemakai, untuk kerusakan yang diam-diam menyesatkan agent:
- nomor halaman Shamela (shamela_page_id) dibaca dari indeks, bukan dianggap sama dengan urutan rekaman: di صحيح البخاري
  (1681) 11207 dari 11208 rekaman berbeda, jadi tebakan urutan menunjuk halaman yang salah;
- indeks sah buatan mesin lama (tanpa kolom «sp») dibuat ulang sekali, bukan dipakai tanpa nomor itu;
- hadits Bukhari 97 (1/31) ditunjuk juga di Bukhari 2544 (3/149) dan di النسائي (829), urut dari pengarang yang lebih
  dulu wafat;
- `takhrij` dari edisi yang bukan pilihan Shamela (سنن أبي داود 1726) dijembatani lewat nomor hadits ke edisi pilihannya
  (654), dan hadits di kitab lain ditunjuk balik ke 1726; tanpa jembatan ini agent disuruh mengunduh edisi kedua;
- صحيح مسلم 1727↔711 dijembatani lewat nomor global berkurung «(982)», bukan nomor urut dalam كتاب «9 -» yang menunjuk
  hadits lain (hadits Jibril, 1727 ج1 ص39);
- `rawi` mencetak rawi bertautan di halaman (1681), juga lewat jembatan edisi (1727→711); ucapan جرح وتعديل yang lafaznya
  umum («سمعت أبي يقول: أدركته ولم أكتب عنه», 7 tempat di الجرح والتعديل 2170) ditunjuk di tarjamah rawi itu (ج2 ص98),
  bukan di kemunculan pertamanya; ucapan yang lafaznya sekali muncul tetapi di tarjamah rawi lain (عبد الرحمن بن حميد
  #3281 → 1278 ج13 ص637 tarjamah النضر بن إسماعيل) tidak ditunjuk; sanad dicetak berurutan dari pengarang, termasuk
  sanad yang kode jenisnya bukan «s» (Bukhari 2804 يحيى بن بكير عن الليث، 1681 ج4 ص19, kode «b»);
- `akar 10649 <akar>`: kata yang sama dengan akarnya ikut dihitung walau tidak ada di kamus Shamela («قرض», «القرض»),
  «وقف» tidak dikelompokkan ke «قف», akar berhamzah boleh ditulis «أخذ» (kamus: «ءخذ»), nama kelompok yang ejaannya
  diubah `norm` tidak terpotong («السماوات» -> «سموات», bukan «ماوات»), dan kata yang di kamus juga berakar lain
  ditandai («بعد» untuk وعد);
- `tafsir 2:219` menunjuk الطبري (7798) sebelum زاد المسير (23619) sebelum ابن كثير (1503); ayat yang tidak ada ditolak.
Kitabnya 1681, 1726, 654, 1727, 711, 2170, 1278, 10649 dari baris `ambil` tes.yml; tabel layanan dari `siapkan`."""
import atexit, json, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent.parent
SEMENTARA = tempfile.TemporaryDirectory(prefix="bahts-layanan-")
atexit.register(SEMENTARA.cleanup)
AKAR = Path(SEMENTARA.name)
shutil.copytree(REPO / "mesin", AKAR / "mesin", ignore=shutil.ignore_patterns("_tmp", "__pycache__"))
for sid in ("_meta", "1681", "1726", "654", "1727", "711", "2170", "1278", "10649"):
    shutil.copytree(REPO / "kitab" / sid, AKAR / "kitab" / sid)


def jalankan(*a):
    r = subprocess.run([sys.executable, str(AKAR / "mesin" / "bahts.py"), *a], cwd=AKAR, capture_output=True)
    return r.returncode, *(x.decode("utf8").replace("\r\n", "\n") for x in (r.stdout, r.stderr))


gagal = []
for cmd in (("tafsir", "2:1-999999999999999999999"),
            ("takhrij", "1681", "-", "1-999999999999999999999")):
    kode, out, err = jalankan(*cmd)
    if kode == 0 or "Traceback" in err:
        gagal.append(f"rentang berlebih harus ditolak sebelum diperluas: {cmd}: {out} {err}")
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

kode, out, err = jalankan("takhrij", "1726", "3", "283")
for harus in ("رقم 3502 -> [654]", "edisi lokal [1726] سنن أبي داود - ت محيي الدين عبد الحميد: رقم 3502، ج3 ص283"):
    if harus not in out:
        gagal.append(f"takhrij 1726 3 283 (jembatan edisi): tidak ada «{harus}» (kode {kode}: {err[-200:]})")

kode, out, err = jalankan("takhrij", "1727", "2", "676")
if "رقم 982 -> [711]" not in out or "edisi lokal [1727] صحيح مسلم - ت عبد الباقي: رقم 982، ج2 ص675-676" not in out:
    gagal.append(f"takhrij 1727 2 676: hadits 982 tidak dijembatani ke 711 dan balik ke 1727 (kode {kode}: {err[-200:]})")
if "ج1 ص39" in out:
    gagal.append("takhrij 1727 2 676: nomor urut dalam كتاب (9) dipakai sebagai nomor hadits -> 1727 ج1 ص39 (hadits Jibril)")

kode, out, err = jalankan("rawi", "1681", "1", "31")
if kode or "#84: البخاري (#5495) > إسماعيل بن أبي أويس (#676) > مالك بن أنس بن مالك (#5361)" not in out:
    gagal.append(f"rawi 1681 1 31: sanad hadits 100 tidak berurutan dari البخاري (kode {kode}: {err[-200:]})")
if kode or "#676 إسماعيل بن أبي أويس" not in out:
    gagal.append(f"rawi 1681 1 31: إسماعيل بن أبي أويس (#676) tidak dicetak (kode {kode}: {err[-200:]})")
kode, out, err = jalankan("akar", "10649", "قرض")
if kode or "\n  قرض: " not in out or "القرض 75" not in out:
    gagal.append(f"akar 10649 قرض: kata «قرض»/«القرض» (tidak ada di kamus) tidak dikelompokkan ke «قرض» (kode {kode}): {out[:400]}")
kode, out, err = jalankan("akar", "10649", "وقف")
if kode or "\n  قف: " in out or "\n  وقف: " not in out:
    gagal.append(f"akar 10649 وقف: «وقف» dikelompokkan ke «قف» (kode {kode}): {out[:400]}")
kode, out, err = jalankan("akar", "10649", "أخذ")
if kode or "akar ءخذ:" not in out:
    gagal.append(f"akar 10649 أخذ: hamzah akar tidak dibaca «ء» (kode {kode}): {out[:200]} {err[-200:]}")
kode, out, err = jalankan("akar", "10649", "سمو")
if kode or "\n  ماوات" in out or "\n  سموات: " not in out:
    gagal.append(f"akar 10649 سمو: nama kelompok «السماوات» terpotong («ماوات»), `cari`-nya tidak menemukan apa pun: {out[:400]}")
kode, out, err = jalankan("akar", "10649", "وعد")
baris_bad = next((b for b in out.splitlines() if b.startswith("  بعد: ")), "")
if kode or "[juga akar" not in baris_bad:
    gagal.append(f"akar 10649 وعد: «بعد» (kamus: juga akar بعد) tidak ditandai akar lain: «{baris_bad[:200]}»")
kode, out, err = jalankan("rawi", "1681", "4", "19")
if kode or "#7: البخاري (#5495) > يحيى بن عبد الله بن بكير (#6952) > الليث بن سعد بن عبد الرحمن (#5348)" not in out:
    gagal.append(f"rawi 1681 4 19: sanad berkode «b» (hadits 2804) tidak dicetak sebagai rantai (kode {kode}: {err[-200:]})")
kode, out, err = jalankan("rawi", "1727", "2", "676")
if kode or "lewat edisi [711]" not in out or "#5361 مالك بن أنس" not in out:
    gagal.append(f"rawi 1727 2 676: jembatan ke 711 tidak mencetak مالك بن أنس (kode {kode}: {err[-200:]})")
kode, out, err = jalankan("rawi", "46")
blok = out.split("«سمعت أبي يقول: أدركته ولم أكتب عنه»", 1)[-1].splitlines()[:2]
if kode or "[2170]" not in "".join(blok) or "ج2 ص98" not in "".join(blok):
    gagal.append(f"rawi 46: ucapan umum tidak ditunjuk di tarjamah إبراهيم بن دينار (2170 ج2 ص98): {blok}")
kode, out, err = jalankan("rawi", "3281")
blok = out.split("«وقال العجلي: كوفي ثقة»", 1)[-1].splitlines()[:2]
if kode or "ج13 ص637" in "".join(blok):
    gagal.append(f"rawi 3281: ucapan ditunjuk di tarjamah rawi lain (1278 ج13 ص637): {blok}")
kode, out, err = jalankan("rawi", "إبراهيم بن دينار")
if kode or "#46 " not in out:
    gagal.append(f"rawi «إبراهيم بن دينار»: nomor 46 tidak ditemukan (kode {kode})")

kode, out, err = jalankan("tafsir", "2:219")
urutan = [out.find(f"[{s}]") for s in (7798, 23619, 1503)]
if kode or -1 in urutan or urutan != sorted(urutan):
    gagal.append(f"tafsir 2:219: kode {kode}, letak الطبري/زاد المسير/ابن كثير {urutan}")
kode, out, err = jalankan("tafsir", "2:287")
if kode != 1 or "286 ayat" not in out + err:
    gagal.append(f"tafsir 2:287: kode {kode}, ayat yang tidak ada tidak ditolak")

print("\n".join(gagal) or "layanan: semua lolos")
sys.exit(1 if gagal else 0)
