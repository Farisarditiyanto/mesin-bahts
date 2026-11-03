"""`halaman` membaca rekaman lewat indeks, tidak lagi seluruh kitab. Hasilnya harus sama persis dengan membaca seluruh
kitab (cara lama, disalin di sini sebagai pembanding) untuk tiap halaman tiap juz kitab yang sudah diunduh, juga
halaman yang tidak ada, angka Arab, dan juz "-". Kitab buatan menambah penanda ⦗n⦘ yang menurun, rekaman tanpa nomor
halaman, juz bernama, dan حاشية bertanda halaman. Di Linux/macOS berkas yang ditulis mesin harus terbaca seperti
berkas biasa (umask), bukan 0600 bawaan mkstemp. `cari`, `teks`, dan `bab` hanya mengurai rekaman yang memuat frasa:
hasilnya harus sama dengan mengurai seluruh kitab."""
import contextlib, gzip, io, json, os, random, shutil, stat, sys, tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "mesin"))
import shamela
from shamela import TAGS, _juz, _potong
sys.stdout.reconfigure(encoding="utf-8")


def halaman_lama(sid, juz, hal, semua):
    """Pembanding: `halaman` sebelum memakai indeks (membaca tiap rekaman kitab; `semua` = rekamannya, dibaca sekali)."""
    ada, rentang = False, {}
    angka = lambda x: int(x) if str(x).isdigit() else x
    juz, hal = angka(juz), angka(hal)
    for p in semua:
        hh = [h for h, _ in _potong(p) if h is not None]
        if hh:
            r = rentang.setdefault(_juz(p), [min(hh), max(hh)])
            r[0], r[1] = min(r[0], *hh), max(r[1], *hh)
        if angka(_juz(p)) != juz:
            continue
        bagian = [b for h, b in _potong(p) if h == hal]
        if bagian:
            ada = True
            print(TAGS.sub("", "".join(bagian)))
            fn = _potong(p, "footnotes")
            if len(fn) > 1:
                isi, catat = "".join(b for h, b in fn if h == hal), ""
            else:
                a, z = p.get("page_num"), _potong(p)[-1][0]
                isi = fn[0][1]
                catat = f" (حاشية rekaman ص{a}-{z}; halaman tiap catatan tidak tercatat)" if z != a else ""
            if isi.strip():
                print("ـــــ" + catat + "\n" + TAGS.sub("", isi))
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
    semua = list(shamela.norma.rekaman(shamela._folder(sid) / "pages.jsonl.gz"))
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
                    "footnotes": random.choice(["", "(1) " + t(), f"(1) {t()} ⦗{random.randint(1, 60)}⦘ (2) {t()}"])})
    d = root / "990001"
    d.mkdir(parents=True)
    with gzip.open(d / "pages.jsonl.gz", "wt", encoding="utf8") as g:
        g.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rek)
    with gzip.open(d / "toc.jsonl.gz", "wt", encoding="utf8") as g:  # untuk `bab`
        g.writelines(json.dumps({"title_id": i, "page_id": i, "title_text": f"باب {i}", "parent_id": None}, ensure_ascii=False) + "\n"
                     for i in range(0, 400, 50))
    (d / "book_metadata.json").write_text("{}", encoding="utf8")


def utama():
    random.seed(3)
    n = sum(bandingkan(sid, contoh=12) + bandingkan_cari(sid) for sid in shamela.punya())
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
        for sid in shamela.punya():
            mode = stat.S_IMODE((shamela._folder(sid) / "pages.jsonl.gz").stat().st_mode)
            assert mode == 0o666 & ~umask, f"kitab {sid}: pages.jsonl.gz {oct(mode)}"
    # rentang «a-b» = halaman tunggal berurutan, masing-masing diberi kepala; berhenti di halaman pertama yang tidak ada
    import bahts
    for sid in shamela.punya():
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
    print(f"halaman: {n} panggilan sama dengan cara lama")


utama()
