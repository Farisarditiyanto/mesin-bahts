# SPDX-License-Identifier: AGPL-3.0-or-later
"""Uji jebakan pemeriksa langkah 5 (AGENTS.md, Alur kerja langkah 5): berapa kesalahan yang tidak terlihat `cek`
ditangkap pemeriksa LLM, dan berapa baris benar yang dituduh salah. Bahannya di .github/uji_pemeriksa/: naskah bahts
yang lolos `cek` dengan jebakan tertanam, permintaan pemakai, prompt pemeriksa, dan kunci.json (jebakan + umpan).

  python .github/uji_pemeriksa.py                  penjaga (CI): jebakan tetap tidak terlihat `cek` (NASKAH=LOLOS),
                                                   tiap tempat di kunci.json menunjuk tepat satu baris, dan ciri
                                                   alasannya tidak tertulis di baris itu sendiri
  python .github/uji_pemeriksa.py siapkan          ruang kerja baru di TEMP (tanpa .github/ dan berkas yang menyebut uji ini) + prompt
  python .github/uji_pemeriksa.py nilai <temuan.json>…
  python .github/uji_pemeriksa.py jalan [--kali N] [--agen "<perintah>"]
                                                   N kali: ruang kerja baru, agen membaca prompt dari stdin, lalu nilai

Jebakan tertangkap = temuan di barisnya yang kolom «masalah»-nya memuat salah satu ciri alasan dari kunci.json; ciri
hanya kata kunci, jadi baca juga alasannya. Membandingkan dua cara memeriksa: `jalan --kali 3` untuk masing-masing.
Cara baru dipakai hanya kalau rata-rata tertangkap naik melebihi selisih min-maks putaran cara lama, umpan kena tidak
bertambah, dan rata-rata «baris ditandai» tidak naik lebih dari seperempat (menebar tuduhan ke banyak baris bisa
menaikkan tertangkap tanpa lebih tajam). Temuan «lain» dibaca sendiri:
bisa salah tangkap, bisa juga salah asli di naskah uji (bereskan naskahnya).
"""
import argparse, json, os, re, shlex, shutil, statistics, subprocess, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bantu import REPO, bahts  # noqa: E402

UJI = REPO / ".github" / "uji_pemeriksa"
BAHTS = UJI / "khiyar"
FOLDER_KERJA = "bahts/abdullah/khiyar"  # letak bahts di ruang kerja: tampak seperti bahts pemakai biasa
AGEN = "claude -p --permission-mode bypassPermissions --output-format json"
ISI = re.compile(r"^(?!@|#|\s*$)")  # baris isi naskah (bukan @data, judul, atau kosong)


def kunci():
    return json.loads((UJI / "kunci.json").read_text(encoding="utf-8"))


def baris(berkas):
    return (BAHTS / berkas).read_text(encoding="utf-8").splitlines()


def baris_isi():
    """Nomor baris isi naskah (bukan @data, judul, atau kosong): penyebut «baris ditandai»."""
    return {n for n, b in enumerate(baris("naskah.txt"), 1) if ISI.match(b)}


def baris_tempat(entri):
    """{(berkas, nomor baris)} yang ditunjuk entri kunci; ValueError kalau teksnya tidak menunjuk tepat satu baris."""
    hasil = set()
    for berkas, teks in entri["tempat"]:
        nomor = [n for n, b in enumerate(baris(berkas), 1) if teks in b]
        if len(nomor) != 1:
            raise ValueError(f"{entri['id']}: «{teks}» ada di {len(nomor)} baris {berkas}, harusnya 1")
        hasil.add((berkas, nomor[0]))
    return hasil


def penjaga():
    """Jebakan harus lolos `cek`: yang tertangkap `cek` tidak lagi mengukur pemeriksa (pindahkan ke contoh/jebakan)."""
    salah = []
    keluar = bahts(REPO, "tahap", BAHTS.relative_to(REPO).as_posix())
    if not re.search(r"^NASKAH=LOLOS\b", keluar.stdout, re.M):
        salah.append("naskah uji tidak NASKAH=LOLOS (jebakan atau umpan terlihat `cek`):\n" + keluar.stdout + keluar.stderr)
    k = kunci()
    for entri in k["jebakan"] + k["umpan"]:
        try:
            tempat = baris_tempat(entri)
        except ValueError as e:
            salah.append(str(e))
            continue
        # ciri yang sudah tertulis di barisnya sendiri terpenuhi oleh temuan yang hanya mengutip baris itu
        teks = "\n".join(baris("naskah.txt")) if entri.get("di_mana_saja") else "\n".join(baris(b)[n - 1] for b, n in tempat)
        salah += [f"{entri['id']}: ciri «{c}» sudah tertulis di naskah/barisnya" for c in entri.get("ciri", ()) if c in teks]
    if salah:
        sys.exit("uji pemeriksa SALAH:\n" + "\n".join(salah))
    print(f"uji pemeriksa: naskah lolos cek; {len(k['jebakan'])} jebakan dan {len(k['umpan'])} umpan menunjuk satu baris")


def siapkan():
    """Ruang kerja = berkas yang dilacak git tanpa .github/, kitab yang dirujuk + kitab/_meta (disalin, bukan
    ditautkan: tautan menunjuk balik ke repo yang memuat kunci), bahts uji di FOLDER_KERJA.
    Kembalikan (akar ruang kerja, jalur temuan.json, isi prompt)."""
    induk = Path(tempfile.mkdtemp(prefix="uji-pemeriksa-"))
    akar = induk / "mesin-bahts"
    berkas = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True).stdout.decode().split("\0")
    for b in filter(None, berkas):
        # berkas yang menyebut uji ini (dok/mengubah-mesin.md) memberi tahu pemeriksa bahwa naskahnya ujian
        if not b.startswith(".github/") and b"uji_pemeriksa" not in (REPO / b).read_bytes():
            (akar / b).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / b, akar / b)
    # kitab yang dirujuk: bukti <<id|…>> di naskah dan «halaman <id>» di riset.txt (kitab yang dibaca saat riset)
    rujukan = (BAHTS / "naskah.txt").read_text(encoding="utf-8") + (BAHTS / "riset.txt").read_text(encoding="utf-8")
    for sid in sorted({a or b for a, b in re.findall(r"<<(\d+)\||halaman (\d+) ", rujukan)}) + ["_meta"]:
        shutil.copytree(REPO / "kitab" / sid, akar / "kitab" / sid)
    folder = akar / FOLDER_KERJA
    folder.mkdir(parents=True)
    for nama in ("naskah.txt", "riset.txt"):
        shutil.copy2(BAHTS / nama, folder / nama)
    temuan = akar / "temuan.json"
    prompt = (UJI / "prompt.md").read_text(encoding="utf-8").format(
        folder=FOLDER_KERJA, temuan=temuan, permintaan=(UJI / "permintaan.txt").read_text(encoding="utf-8").strip())
    (induk / "prompt.txt").write_text(prompt, encoding="utf-8")
    return akar, temuan, prompt


def letak(t):
    """{(berkas, baris)} satu temuan; «28-29» = 28 dan 29, «28, 31» = keduanya, kosong = baris 0."""
    nama = Path(str(t.get("berkas") or "naskah.txt")).name
    angka = set()
    for a, b in re.findall(r"(\d+)(?:\s*[-–]\s*(\d+))?", str(t.get("baris") or 0)):
        angka |= set(range(int(a), int(b or a) + 1))
    return {(nama, n) for n in angka or {0}}


def nilai(jalur):
    """Nilai satu temuan.json: (tertangkap {id}, umpan kena {id}, temuan lain [teks], baris naskah yang ditandai {n})."""
    temuan = json.loads(Path(jalur).read_text(encoding="utf-8-sig"))["temuan"]
    k = kunci()
    isi = baris_isi()
    tempat = {e["id"]: baris_tempat(e) for e in k["jebakan"] + k["umpan"]}
    kena, umpan, lain, ditandai = set(), set(), [], set()
    for t in temuan:
        # ciri dicari di kolom masalah saja: keluaran `bukti` yang ditempel apa adanya sudah memuat teks halaman kitab
        di, masalah = letak(t), str(t.get("masalah", ""))
        ditandai |= {n for b, n in di if b == "naskah.txt" and n in isi}
        cocok = {e["id"] for e in k["jebakan"] if any(c in masalah for c in e["ciri"])
                 and (di & tempat[e["id"]] or e.get("di_mana_saja"))}
        cocok_umpan = {e["id"] for e in k["umpan"] if di & tempat[e["id"]]}
        kena |= cocok
        umpan |= cocok_umpan
        if not cocok | cocok_umpan:
            lain.append(f"{','.join(f'{b}:{n}' for b, n in sorted(di))} {masalah[:160]}")
    return kena, umpan, lain, ditandai


def laporan(jalur_semua):
    k = kunci()
    isi = len(baris_isi())
    hasil, jalur_semua = [], list(jalur_semua)
    for j in list(jalur_semua):
        try:
            hasil.append(nilai(j))
        except (OSError, ValueError, KeyError) as e:  # putaran ini gagal diukur; putaran lain tetap dinilai
            print(f"{j}: tidak terbaca sebagai temuan.json ({e!r})")
            jalur_semua.remove(j)
    for j, (kena, umpan, lain, ditandai) in zip(jalur_semua, hasil):
        print(f"\n== {j}\ntertangkap {len(kena)}/{len(k['jebakan'])} | umpan kena {len(umpan)}/{len(k['umpan'])}"
              f" | temuan lain {len(lain)} | baris ditandai {len(ditandai)}/{isi}")
        for e in k["jebakan"]:
            print(f"  {'✓' if e['id'] in kena else '✗'} {e['id']} {e['jenis']}")
        for e in k["umpan"]:
            if e["id"] in umpan:
                print(f"  ! {e['id']} umpan dianggap salah (benar: {e['benar']})")
        for x in lain:
            print(f"  ? {x}")  # bisa salah tangkap, bisa juga salah asli di naskah uji: periksa sendiri
    if len(hasil) > 1:
        angka = [len(h[0]) for h in hasil]
        print(f"\nRINGKAS {len(hasil)} putaran: tertangkap rata-rata {statistics.mean(angka):.1f}/{len(k['jebakan'])}"
              f" (min {min(angka)}, maks {max(angka)}); umpan kena rata-rata {statistics.mean(len(h[1]) for h in hasil):.1f};"
              f" baris ditandai rata-rata {statistics.mean(len(h[3]) for h in hasil):.1f}/{isi}")
        for e in k["jebakan"]:
            print(f"  {e['id']} {sum(e['id'] in h[0] for h in hasil)}/{len(hasil)} {e['jenis']}")


def jalan(kali, agen):
    jalur = []
    for i in range(kali):
        akar, temuan, prompt = siapkan()
        mulai = time.time()
        perintah = shlex.split(agen, posix=os.name != "nt")
        perintah[0] = shutil.which(perintah[0]) or perintah[0]  # Windows: agen dari npm = berkas .cmd yang tidak dicari CreateProcess
        p = subprocess.run(perintah, cwd=akar, input=prompt, capture_output=True, encoding="utf-8")
        (akar.parent / "agen.txt").write_text(p.stdout + "\n--- stderr\n" + p.stderr, encoding="utf-8")
        print(f"putaran {i + 1}: kode {p.returncode}, {(time.time() - mulai) / 60:.0f} menit, ruang kerja {akar}")
        if not temuan.exists():
            print(f"  temuan.json tidak ditulis; keluaran agen: {akar.parent / 'agen.txt'}")
        jalur.append(temuan)
    laporan(jalur)


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # konsol Windows (cp1252) tidak bisa mencetak huruf Arab
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="perintah")
    sub.add_parser("siapkan")
    n = sub.add_parser("nilai")
    n.add_argument("temuan", nargs="+")
    j = sub.add_parser("jalan")
    j.add_argument("--kali", type=int, default=3)
    j.add_argument("--agen", default=AGEN)
    a = ap.parse_args()
    if a.perintah == "siapkan":
        akar, temuan, _ = siapkan()
        print(f"ruang kerja: {akar}\nprompt: {akar.parent / 'prompt.txt'}\ntemuan ditulis ke: {temuan}")
    elif a.perintah == "nilai":
        laporan(a.temuan)
    elif a.perintah == "jalan":
        jalan(a.kali, a.agen)
    else:
        penjaga()


if __name__ == "__main__":
    main()
