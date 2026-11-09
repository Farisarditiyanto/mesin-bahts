# SPDX-License-Identifier: AGPL-3.0-or-later
"""`halaman` membaca rekaman lewat indeks, tidak lagi seluruh kitab. Hasilnya harus sama persis dengan membaca seluruh
kitab (cara lama, disalin di sini sebagai pembanding) untuk kitab yang dipilih (bawaan: kitab CI tetap), juga
halaman yang tidak ada, angka Arab, dan juz "-". Kitab buatan menambah penanda ⦗n⦘ yang menurun, rekaman tanpa nomor
halaman, juz bernama, dan حاشية bertanda halaman. Di Linux/macOS berkas yang ditulis mesin harus terbaca seperti
berkas biasa (umask), bukan 0600 bawaan mkstemp. `cari`, `teks`, dan `bab` hanya mengurai rekaman yang memuat frasa:
hasilnya harus sama dengan mengurai seluruh kitab."""
import contextlib, gzip, io, json, os, random, re, stat, sys, tempfile
from pathlib import Path
from uji_semua import kitab_ci

AKAR = Path(__file__).resolve().parent.parent
SAMPEL = 10  # kitab lokal di luar kitab CI yang ikut dibandingkan pada mode sampel
ARAB = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
sys.path.insert(0, str(AKAR / "mesin"))
import shamela
from norma import per_halaman
from shamela import TAGS, _juz
sys.stdout.reconfigure(encoding="utf-8")


def angka(x):
    return int(x) if str(x).isdigit() else x


def urai(semua):
    """Tiap rekaman diurai sekali untuk semua panggilan `halaman_lama` di kitab itu: (rekaman, juz, juz angka, potongan,
    nomor halamannya). Hasilnya sama dengan mengurai ulang di tiap panggilan; dulu itu memakan sebagian besar waktu uji."""
    out = []
    for p in semua:
        pot = per_halaman(p)
        out.append((p, _juz(p), angka(_juz(p)), pot, [h for h, _ in pot if h is not None]))
    return out


def halaman_lama(sid, juz, hal, rekaman):
    """Pembanding: `halaman` sebelum memakai indeks (membaca tiap rekaman kitab; `rekaman` = hasil `urai`, dibaca sekali)."""
    ada, rentang = False, {}
    juz, hal = angka(juz), angka(hal)
    if juz == "-" and not any(jz == "-" or isinstance(jz_angka, int) for _, jz, jz_angka, _, _ in rekaman):
        # kitab yang bagiannya hanya bernama: «-» = satu-satunya bagian yang punya halaman itu
        di = {jz_angka for _, _, jz_angka, pot, hh in rekaman if hal in hh}
        juz = di.pop() if len(di) == 1 else juz
    for p, jz, jz_angka, pot, hh in rekaman:
        if hh:
            r = rentang.setdefault(jz, [min(hh), max(hh)])
            r[0], r[1] = min(r[0], *hh), max(r[1], *hh)
        if jz_angka != juz:
            continue
        bagian = [b for h, b in pot if h == hal]
        if bagian:
            ada = True
            print(shamela.baris(TAGS.sub("", "".join(bagian))))  # «\r» Shamela jadi baris baru: cara cetak, bukan cara baca
            fn = per_halaman(p, "footnotes")
            if len(fn) > 1:
                isi, catat = "".join(b for h, b in fn if h == hal), ""
            else:
                a, z = p.get("page_num"), pot[-1][0]
                isi = fn[0][1]
                catat = f" (حاشية rekaman ص{a}-{z}; halaman tiap catatan tidak tercatat)" if z != a else ""
            if isi.strip():
                print("ـــــ" + catat + "\n" + shamela.baris(TAGS.sub("", isi)))
    if not ada:
        print(f"[{sid}] TIDAK ADA halaman {juz}/{hal}. Yang ada: "
              + "، ".join(f"juz {j} ص{a}-{z}" for j, (a, z) in rentang.items()) + " (juz \"-\" = kitab satu jilid)")
    return ada


def keluaran(f, *a):
    b = io.StringIO()
    with contextlib.redirect_stdout(b):
        r = f(*a)
    return r, b.getvalue()


def bandingkan(sid, tambahan=(), contoh=60):
    ix = shamela.indeks(sid)
    semua = urai(shamela.norma.rekaman(shamela._folder(sid) / "pages.jsonl.gz"))
    juz = sorted({"-" if j is None else str(j) for j, *_ in ix})
    juz = juz[:2] + juz[-2:] + ["-", "٠١", "x"]  # kitab berjilid banyak: cukup juz awal dan akhir
    hal = sorted({h for _, p1, p2, _ in ix for h in (p1, p2) if h is not None})
    hal = sorted(set(hal[:contoh // 3] + hal[-contoh // 3:] + random.sample(hal, min(len(hal), contoh)))) + [0, 99999, "٥", "05", "a", *tambahan]
    n = 0
    for j in juz:
        for h in hal:
            shamela._indeks.cache_clear(); shamela.indeks.cache_clear()
            baru, lama = keluaran(shamela.halaman, str(sid), j, str(h)), keluaran(halaman_lama, str(sid), j, str(h), semua)
            assert baru == lama, f"kitab {sid} juz {j} hal {h}:\nbaru={baru!r}\nlama={lama!r}"
            n += 1
    return n


def sama_cari(sid, frasa, semua):
    """`cari`, `teks`, `bab` lewat `_berisi` = lewat seluruh rekaman kitab (`semua`: tiap rekaman diperiksa, teks
    `padat`-nya dihitung di tempat dari teksnya, tanpa berkas padat)."""
    baru = [keluaran(f, sid, frasa) for f in (shamela.cari, shamela.teks, shamela.bab)]
    asli = shamela._berisi
    shamela._berisi = lambda s, q: iter(semua)
    try:
        lama = [keluaran(f, sid, frasa) for f in (shamela.cari, shamela.teks, shamela.bab)]
    finally:
        shamela._berisi = asli
    assert baru == lama, f"kitab {sid} «{frasa}»:\nbaru={baru!r}\nlama={lama!r}"
    return 3


def bandingkan_cari(sid, n=25):
    """Frasa = potongan teks matan dan حاشية kitab itu sendiri (ketemu, ketemu banyak, dan lintas penanda ⦗n⦘), plus frasa yang tidak ada."""
    semua = list(shamela.norma.rekaman(shamela._folder(sid) / "pages.jsonl.gz"))
    teks = [t for r in semua for t in (r.get("body"), r.get("footnotes")) if t and shamela.padat(t)]
    frasa = ["قال", "والله أعلم", "قولا لا يوجد مثله في كتاب من الكتب"]
    for t in random.sample(teks, min(len(teks), n)):
        kata = shamela.TAGS.sub("", t).split()
        k = random.randrange(max(1, len(kata) - 4))
        frasa.append(" ".join(kata[k:k + 4]))
    return sum(sama_cari(sid, x, semua) for x in frasa if shamela.padat(x))


def kitab_buatan(root):
    random.seed(7)
    kata = "قال الشيخ العلم العمل النية <span>".split()
    t = lambda: " ".join(random.choice(kata) for _ in range(6))
    rek = []
    for i in range(400):
        body = t() + "".join(f" ⦗{random.choice(['٣', '12', str(random.randint(1, 60)), '٠٥'])}⦘ " + t()
                             for _ in range(random.randint(0, 3)))
        rek.append({"page_id": i, "part": random.choice([None, "1", "2", "المقدمة"]),
                    "page_num": random.choice([None, i % 40 + 1, i % 40 + 1, random.randint(1, 60)]), "body": body,
                    # penanda حاشية ber-angka Arab: hanya itu yang dibaca PENANDA, jadi حاشية bertanda halaman ikut diuji
                    "footnotes": random.choice(["", "(1) " + t(), f"(1) {t()} ⦗{str(random.randint(1, 60)).translate(ARAB)}⦘ (2) {t()}"])})
    d = root / "990001"
    d.mkdir(parents=True)
    with gzip.open(d / "pages.jsonl.gz", "wt", encoding="utf8") as g:
        g.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rek)
    with gzip.open(d / "toc.jsonl.gz", "wt", encoding="utf8") as g:  # untuk `bab`
        g.writelines(json.dumps({"title_id": i, "page_id": i, "title_text": f"باب {i}", "parent_id": None}, ensure_ascii=False) + "\n"
                     for i in range(0, 400, 50))
    (d / "book_metadata.json").write_text("{}", encoding="utf8")


def kitab_diuji():
    """Bawaan: kitab CI tetap. `UJI_HALAMAN=penuh`: semua kitab lokal; `sampel`: CI + SAMPEL kitab lain."""
    semua = shamela.punya()
    mode = os.environ.get("UJI_HALAMAN", "ci")
    if mode == "penuh":
        return semua
    if mode not in ("ci", "sampel"):
        sys.exit(f"UJI_HALAMAN={mode}: pilih ci, sampel, atau penuh")
    ci = set(kitab_ci())
    if kurang := ci - set(semua):
        sys.exit("Kitab CI belum diunduh: " + shamela.perintah("ambil " + " ".join(map(str, sorted(kurang)))))
    if mode == "ci":
        print(f"halaman: {len(ci)} kitab CI tetap")
        return sorted(ci)
    benih = int(os.environ.get("UJI_HALAMAN_BENIH") or random.SystemRandom().randrange(10 ** 6))
    lain = [s for s in semua if s not in ci]
    pilih = sorted({s for s in semua if s in ci} | set(random.Random(benih).sample(lain, min(SAMPEL, len(lain)))))
    print(f"halaman: sampel {len(pilih)} dari {len(semua)} kitab (UJI_HALAMAN_BENIH={benih}); "
          f"semua kitab: UJI_HALAMAN=penuh atau `uji_semua.py --penuh`")
    return pilih


def utama():
    random.seed(3)
    dipilih = kitab_diuji()
    n = sum(bandingkan(sid, contoh=12) + bandingkan_cari(sid) for sid in dipilih)
    asli = shamela.ROOT
    with tempfile.TemporaryDirectory() as tmp:
        shamela.ROOT = Path(tmp)
        kitab_buatan(shamela.ROOT)
        n += bandingkan(990001, range(1, 61)) + bandingkan_cari(990001)
        # indeks lama (versi 1: satu daftar per rekaman, tanpa sidik .gz) tetap dipakai dengan benar, lalu ditulis ulang
        f = shamela.ROOT / "990001" / shamela.INDEKS
        d = json.loads(f.read_text(encoding="utf8"))
        lama = {"versi": 1, "sumber": d["sumber"], "rekaman": [list(x) for x in zip(d["juz"], d["hal"], d["akhir"], d["letak"])]}
        f.write_text(json.dumps(lama, ensure_ascii=False), encoding="utf8")
        n += bandingkan(990001)
        assert "sumber_gz" in json.loads(f.read_text(encoding="utf8")), "indeks lama tidak ditulis ulang"
        if os.name != "nt":
            umask = os.umask(0); os.umask(umask)
            mode = stat.S_IMODE(f.stat().st_mode)
            assert mode == 0o666 & ~umask, f"indeks.json {oct(mode)}, harusnya {oct(0o666 & ~umask)} (umask)"
    shamela.ROOT = asli
    if os.name != "nt":  # kitab yang diunduh `ambil` (lewat berkas sementara) juga mengikuti umask
        for sid in dipilih:
            mode = stat.S_IMODE((shamela._folder(sid) / "pages.jsonl.gz").stat().st_mode)
            assert mode == 0o666 & ~umask, f"kitab {sid}: pages.jsonl.gz {oct(mode)}"
    # rentang «a-b» = halaman tunggal berurutan, masing-masing diberi kepala, termasuk halaman bolong di tengah kitab
    import bahts
    for sid in dipilih:
        ix, awal = shamela._indeks(sid)
        juz, hal = next(((e[0], a) for e, a in zip(ix, awal) if a is not None), (None, None))
        if hal is None:
            continue
        juz = "-" if juz is None else juz
        r, isi = keluaran(bahts.halaman, sid, juz, f"{hal}-{hal + 2}")
        harus = "".join(f"===== [{sid}] {juz}/{h} =====\n" + keluaran(shamela.halaman, sid, juz, h)[1]
                        for h in range(hal, hal + 3))
        assert r and isi == harus, f"halaman rentang {sid} {juz}/{hal}-{hal + 2} beda dari halaman tunggal"
        n += 1
    # `kartu`: baris bukti siap pakai memakai juz yang diterima `cek` dan halaman yang terbaca, juga untuk kitab berjilid
    # yang halamannya bersambung («متسلسلة الترقيم», 6178): dulu agent menulis juz "-" lalu GAGAL «berjilid»
    import kitab_lokal
    for sid in dipilih:
        baris = keluaran(shamela.kartu, sid)[1].splitlines()[-1]
        m = (re.search(rf"mis\. <<{sid}\|([^|<>]+)\|(\d+)>>", baris)
             or re.search(rf"<<{sid}\|(-)\|<hal>>> \(kitab satu jilid: juz \"-\"; halaman (\d+)-", baris))
        assert m, f"kartu {sid}: baris bukti tidak ada atau bentuknya lain: {baris!r}"
        juz, hal = m.groups()
        assert kitab_lokal.salah_juz(sid, juz, hal) == "", f"kartu {sid}: {baris!r} -> {kitab_lokal.salah_juz(sid, juz, hal)}"
        assert keluaran(shamela.halaman, sid, juz, hal)[0], f"kartu {sid}: halaman {juz}/{hal} tidak terbaca"
        n += 1
    print(f"halaman: {n} panggilan sama dengan cara lama")


if __name__ == "__main__":
    utama()
