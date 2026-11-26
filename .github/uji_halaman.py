# SPDX-License-Identifier: AGPL-3.0-or-later
"""`halaman` dan `cari` lewat pintu pemakai harus mencetak isi halaman yang diminta, bukan halaman lain.

Kitab buatan: tiap potongan teks (matan dan حاشية) berisi satu kata unik, jadi isi tiap juz/halaman diketahui dari
pembuatannya: penanda ⦗n⦘ memindahkan teks sesudahnya ke halaman n (juga penanda menurun dan «٠٥»), teks sebelum penanda
pertama milik nomor halaman rekaman, rekaman tanpa nomor halaman tidak bisa diminta, juz boleh bernama, dan حاشية
bertanda halaman dicetak hanya di halamannya. Kitab asli (bawaan: kitab CI tetap; `UJI_HALAMAN=penuh` semua kitab lokal,
`sampel` = CI + beberapa kitab lain): potongan awal beberapa rekaman, dibaca langsung dari berkas kitabnya, harus
tercetak oleh `halaman` untuk juz/halaman rekaman itu. Di Linux/macOS berkas yang ditulis mesin mengikuti umask."""
import gzip, json, os, random, re, stat, sys, tempfile
from pathlib import Path
from bantu import REPO, bahts, salin_mesin
from uji_semua import kitab_ci

SAMPEL = 10  # kitab lokal di luar kitab CI yang ikut diperiksa pada mode sampel
REKAMAN = 8  # rekaman yang diperiksa tiap kitab asli
SID = 990001
HURUF = "تثجحخدذرزسشصضطظعغقمن"  # tanpa huruf sambung dan huruf yang disamakan ejaannya: tiap kata hanya cocok dengan dirinya
ARAB = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
PENANDA = re.compile(r"⦗[٠-٩]+⦘")
KATA = re.compile(f"[{HURUF}]{{5}}")
sys.stdout.reconfigure(encoding="utf-8")


def kata(i):
    """Kata unik ke-i: lima huruf."""
    return "".join(HURUF[i // len(HURUF) ** k % len(HURUF)] for k in range(5))


def kitab_buatan(root):
    """Tulis kitab SID; kembalikan (cetak, letak, buta, lintas):
    cetak = {(juz, halaman): [kata, …]} yang harus dicetak `halaman`, urut rekaman, matan tiap rekaman lalu حاشية-nya;
    letak = {kata: (juz, halaman)} untuk kata yang halamannya pasti; buta = kata matan di rekaman tanpa nomor halaman
    sebelum penanda pertamanya; lintas = (kata, kata berikutnya, juz) yang dipisah satu penanda halaman."""
    acak = random.Random(7)
    nomor = iter(range(10 ** 6))
    baru = lambda: kata(next(nomor))
    cetak, letak, buta, lintas, rekaman = {}, {}, [], None, []
    for i in range(400):
        juz = acak.choice([None, "1", "2", "المقدمة"])
        hal = acak.choice([None, i % 40 + 1, i % 40 + 1, acak.randint(1, 60)])
        matan = [(hal, baru())]
        for n in acak.sample(range(1, 61), acak.randint(0, 3)):  # acak: penanda menurun ikut ada
            matan.append((n, baru()))
        body = matan[0][1] + " <span>x</span>"
        for n, k in matan[1:]:
            body += f" ⦗{acak.choice([str(n), str(n).zfill(2)]).translate(ARAB)}⦘ " + k
        if len(matan) > 1 and hal is not None:
            lintas = (matan[0][1], matan[1][1], juz)
        bentuk = acak.choice(["kosong", "satu", "bertanda"])
        fn, catatan = "", []  # catatan = [(halaman, atau "semua" = tiap halaman rekaman ini, kata)]
        if bentuk == "satu":  # حاشية tanpa penanda: halaman tiap catatan tidak tercatat, tercetak di tiap halaman rekaman
            catatan = [("semua", baru())]
            fn = "(1) " + catatan[0][1]
        elif bentuk == "bertanda":
            n = acak.randint(1, 60)
            catatan = [(hal, baru()), (n, baru())]
            fn = f"(1) {catatan[0][1]} ⦗{str(n).translate(ARAB)}⦘ (2) {catatan[1][1]}"
        for h in dict.fromkeys(h for h, _ in matan):  # tiap halaman rekaman ini, sekali
            if h is None:
                buta += [k for hh, k in matan if hh is None]
                continue
            cetak.setdefault((juz, h), []).extend([k for hh, k in matan if hh == h]
                                                  + [k for hh, k in catatan if hh in ("semua", h)])
        for h, k in matan:
            if h is not None:
                letak[k] = (juz, h)
        rekaman.append({"page_id": i, "part": juz, "page_num": hal, "body": body, "footnotes": fn})
    d = root / str(SID)
    d.mkdir(parents=True)
    with gzip.open(d / "pages.jsonl.gz", "wt", encoding="utf8") as g:
        g.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rekaman)
    (d / "book_metadata.json").write_text("{}", encoding="utf8")
    return cetak, letak, buta, lintas


def halaman(akar, juz, hal):
    """(kode keluar, kata unik yang dicetak `halaman`, keluaran mentahnya)."""
    r = bahts(akar, "halaman", SID, "-" if juz is None else juz, hal)
    assert "Traceback" not in r.stderr, r.stderr
    return r.returncode, KATA.findall(r.stdout), r.stdout


def uji_buatan(akar):
    cetak, letak, buta, lintas = kitab_buatan(akar / "kitab")
    n = 0
    # tiap halaman tiap juz, 20 halaman sekali panggil: di bawah tiap kepala hanya kata halaman itu, urut
    for juz in sorted({j for j, _ in cetak}, key=str):
        nama = "-" if juz is None else juz
        for awal in (1, 21, 41, 61):
            _, _, out = halaman(akar, juz, f"{awal}-{awal + 19}")
            potong = re.split(rf"^===== \[{SID}\] {nama}/(\d+) =====$", out, flags=re.M)
            assert potong[1::2] == [str(h) for h in range(awal, awal + 20)], f"halaman {nama} {awal}-{awal + 19}: {out[:300]}"
            for hal, isi in zip(potong[1::2], potong[2::2]):
                harus = cetak.get((juz, int(hal)), [])
                assert KATA.findall(isi) == harus, f"halaman {nama}/{hal}: {KATA.findall(isi)}, harusnya {harus}"
                assert harus or "TIDAK ADA halaman" in isi, isi[:200]
                n += 1
    # halaman tunggal; «٥», «05», dan juz «٠١»/«01» = angka yang sama
    assert cetak["1", 5] and buta
    for juz, hal in (("1", "5"), ("1", "٥"), ("1", "05"), ("٠١", "5"), ("01", "5")):
        kode, dapat, _ = halaman(akar, juz, hal)
        assert kode == 0 and dapat == cetak["1", 5], f"halaman {juz}/{hal} bukan juz 1 halaman 5: {dapat}"
    # juz/halaman bukan angka dan yang tidak ada = tidak ada (kode keluar 1), bukan halaman lain
    for juz, hal in (("1", "0"), ("1", "99999"), ("1", "a"), ("x", "5"), ("9", "5")):
        kode, dapat, out = halaman(akar, juz, hal)
        assert kode != 0 and not dapat and "TIDAK ADA halaman" in out, f"halaman {juz}/{hal}: {out[:200]}"
    # kitab belum diunduh (atau unduhan putus tanpa pages.jsonl.gz) dengan rentang halaman: gagal sebelum mencetak kepala =====
    (akar / "kitab" / "990002").mkdir()
    (akar / "kitab" / "990002" / "book_metadata.json").write_text("{}", encoding="utf8")
    for sid_hilang in ("999998", "990002"):
        r_hilang = bahts(akar, "halaman", sid_hilang, "-", "1-5")
        assert r_hilang.returncode != 0 and not r_hilang.stdout.strip(), (sid_hilang, r_hilang.stdout, r_hilang.stderr)
        assert "belum diunduh" in r_hilang.stderr or "TIDAK ADA di katalog" in r_hilang.stderr, r_hilang.stderr
    # `cari`: kata unik ditunjuk di juz/halaman tempatnya ditulis; frasa yang menyeberang penanda halaman tetap ketemu;
    # kata yang tidak ada dikatakan tidak ketemu
    tempat = lambda r: [(j.strip("«»"), int(h)) for j, h in re.findall(rf"^\[{SID}\] ج(\S+) ص(\d+)", r.stdout, re.M)]
    for k in random.Random(11).sample(sorted(letak), 15):
        juz, hal = letak[k]
        r = bahts(akar, "cari", SID, k)
        assert tempat(r) == [("-" if juz is None else juz, hal)], f"cari {k} ({juz}/{hal}): {r.stdout[:300]}"
    a, b, juz = lintas
    r = bahts(akar, "cari", SID, f"{a} {b}")
    assert tempat(r)[:1] == [("-" if juz is None else juz, letak[a][1])], f"cari lintas penanda: {r.stdout[:300]}"
    r = bahts(akar, "cari", SID, kata(999_999))
    assert r.returncode != 0 and f"[{SID}] TIDAK KETEMU" in r.stdout, r.stdout[:300]
    # indeks dari versi mesin lain dibuat ulang, bukan dipakai
    f = akar / "kitab" / str(SID) / "indeks.json"
    juz, hal = next(k for k in cetak if k[0] == "1")
    lama = json.loads(f.read_text(encoding="utf8"))
    lama["versi"] = 1
    f.write_text(json.dumps(lama), encoding="utf8")
    assert halaman(akar, juz, hal)[1] == cetak[juz, hal] and json.loads(f.read_text(encoding="utf8"))["versi"] != 1, \
        "indeks versi lain masih dipakai"
    if os.name != "nt":
        umask = os.umask(0); os.umask(umask)
        mode = stat.S_IMODE(f.stat().st_mode)
        assert mode == 0o666 & ~umask, f"indeks.json {oct(mode)}, harusnya {oct(0o666 & ~umask)} (umask)"
    return n + 30


def kitab_diuji():
    """Bawaan: kitab CI tetap. `UJI_HALAMAN=penuh`: semua kitab lokal; `sampel`: CI + SAMPEL kitab lain."""
    semua = sorted(int(p.name) for p in (REPO / "kitab").iterdir() if p.name.isdigit() and (p / "pages.jsonl.gz").exists())
    mode = os.environ.get("UJI_HALAMAN", "ci")
    if mode == "penuh":
        return semua
    if mode not in ("ci", "sampel"):
        sys.exit(f"UJI_HALAMAN={mode}: pilih ci, sampel, atau penuh")
    ci = set(kitab_ci())
    if kurang := ci - set(semua):
        sys.exit("Kitab CI belum diunduh: python mesin/bahts.py ambil " + " ".join(map(str, sorted(kurang))))
    if mode == "ci":
        print(f"halaman: {len(ci)} kitab CI tetap")
        return sorted(ci)
    benih = int(os.environ.get("UJI_HALAMAN_BENIH") or random.SystemRandom().randrange(10 ** 6))
    lain = [s for s in semua if s not in ci]
    pilih = sorted(ci | set(random.Random(benih).sample(lain, min(SAMPEL, len(lain)))))
    print(f"halaman: sampel {len(pilih)} dari {len(semua)} kitab (UJI_HALAMAN_BENIH={benih}); "
          f"semua kitab: UJI_HALAMAN=penuh atau `uji_semua.py --penuh`")
    return pilih


def uji_asli(sid):
    """Awal matan beberapa rekaman kitab sid (sebelum penanda pertama = halaman nomor rekaman itu) tercetak oleh
    `halaman <juz> <nomor>`."""
    with gzip.open(REPO / "kitab" / str(sid) / "pages.jsonl.gz", "rt", encoding="utf8") as g:
        rekaman = [json.loads(b) for b in g]
    calon = []
    for p in rekaman:
        awal = PENANDA.split(p.get("body") or "")[0]
        potong = re.search(r"[ء-ْ]+(?: [ء-ْ]+){3}", awal)  # empat kata huruf Arab (boleh berharakat) berurutan, sebaris
        if potong and isinstance(p.get("page_num"), int):
            calon.append((p.get("part"), p["page_num"], potong[0]))
    acak = random.Random(sid)
    pilih = calon[:1] + calon[-1:] + acak.sample(calon, min(len(calon), REKAMAN - 2))
    assert pilih, f"kitab {sid}: tidak ada rekaman yang bisa diperiksa"
    for juz, hal, potong in pilih:
        juz = "-" if juz is None else str(juz)
        r = bahts(REPO, "halaman", sid, juz, hal)
        assert r.returncode == 0 and potong in r.stdout, f"halaman {sid} {juz} {hal}: tidak memuat «{potong}»: {r.stdout[:200]} {r.stderr[-200:]}"
    if os.name != "nt":  # kitab yang diunduh `ambil` (lewat berkas sementara) juga mengikuti umask
        umask = os.umask(0); os.umask(umask)
        mode = stat.S_IMODE((REPO / "kitab" / str(sid) / "pages.jsonl.gz").stat().st_mode)
        assert mode == 0o666 & ~umask, f"kitab {sid}: pages.jsonl.gz {oct(mode)}"
    return len(pilih)


def utama():
    with tempfile.TemporaryDirectory(prefix="bahts-halaman-") as t:
        akar = Path(t)
        salin_mesin(akar, huruf=False)
        n = uji_buatan(akar)
    n += sum(uji_asli(sid) for sid in kitab_diuji())
    print(f"halaman: {n} pemeriksaan sesuai isi kitabnya")


if __name__ == "__main__":
    utama()
