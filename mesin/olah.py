"""Olah <bahts>/naskah.txt -> mesin/_tmp/<bahts>.json (bahan untuk perakit Word)
+ verifikasi setiap rujukan ke kitab Shamela lokal. Dipanggil lewat bahts.py.

Tanda di naskah.txt (dicetak oleh: python mesin/bahts.py tanda):
  @kunci: nilai       data sampul, di awal naskah. Wajib: judul, jenis, nama, nim, fasl.
                      Opsional: musyrif, jabatan (kosong atau "-" = tidak tercetak), thalibah (ya = sampul mencetak «اسم الطالبة»),
                      berkas (nama file hasil), format (profil di format.json; bawaan imam),
                      tanpa (فهرس yang tidak dicetak: ayat, hadits, maudhuat; mis. «@tanpa: ayat, hadits»).
                      فهرس الآيات dan فهرس الأحاديث yang kosong tidak dicetak dengan sendirinya
  #K #F #B #M teks    judul tengah + masuk فهرس الموضوعات: K = مقدمة/خاتمة, F = فصل (keduanya mulai halaman baru), B = مبحث, M = مطلب.
                      Bahts pendek tanpa فصل: #F untuk مبحث, #B untuk مطلب
  #S teks             sub-judul kanan (tidak masuk فهرس)
  #R teks             awal المصادر والمراجع; sesudahnya satu kitab per baris (diurutkan abjad otomatis, القرآن الكريم paling atas)
  **...**             tebal
  {Q:s:a} {Q:s:a-b} {Q:s:a:i-j}   ayat surat s ayat a (atau a-b; atau kata ke-i s.d. j): teks resmi rasm Utsmani + masuk فهرس الآيات
  {H:طرف|راوٍ|kunci}   daftarkan hadits/atsar ke فهرس الأحاديث; taruh tepat sebelum «matan». Kunci: huruf kecil a-z, satu kunci satu hadits
  {H2:kunci}          halaman tambahan untuk hadits yang sama
  {P:kunci}           nomor halaman {H:..|kunci}; hanya di dalam catatan kaki: [^سبق تخريجه، ص{P:kunci}.]
  [^ ... ]            catatan kaki
  <<sid|juz|hal>>     bukti di dalam catatan kaki (tidak ikut tercetak): kutipan "..."/«...» tepat sebelum catatan kaki
                      harus ada di kitab sid pada juz/hal itu
  <<sid|juz|hal|potongan>>   bukti dengan potongan teks sendiri (untuk nukilan makna «انظر»); #123 = nomor hadits
                      juz "-" = kitab satu jilid; hal boleh rentang 12-14
  Contoh: قال ابن القيم: "…"[^مدارج السالكين، ابن القيم، 2/15. <<8370|2|15>>].
"""
import gzip, json, re
from pathlib import Path

HERE = Path(__file__).parent
SHAMELA = HERE.parent / "kitab"
QURAN = json.load(open(HERE / "quran_hafs_v22.json", encoding="utf8"))
SURAH = json.load(open(HERE / "nama_surah.json", encoding="utf8"))
FORMAT = json.load(open(HERE / "format.json", encoding="utf8"))  # huruf & ukuran tiap pedoman; dipilih dengan @format
WAJIB = ("judul", "jenis", "nama", "nim", "fasl")
TANPA = ("ayat", "hadits", "maudhuat")  # فهرس yang boleh dibuang lewat @tanpa; perakitnya di rakit.ps1

HARAKAT = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
TAGS = re.compile(r"<[^>]+>")
HORMAT = re.compile(
    r"صل[يى] الله عليه وسلم|رض[يى] الله عنه(?:ما|م|ا)?|عليه(?:ما)? السلام|رحمه الله|عز وجل|قدس الله روحه")
AD = "٠١٢٣٤٥٦٧٨٩"


def vnorm(s):
    s = TAGS.sub("", s)
    s = HARAKAT.sub("", s)
    s = HORMAT.sub("", s)
    s = re.sub("[إأآٱ]", "ا", s)
    s = s.replace("شئ", "شيء")
    s = s.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    return re.sub(r"[^ء-ي]", "", s)


_cache = {}


def kitab(sid):
    if sid not in _cache:
        with gzip.open(SHAMELA / str(sid) / "pages.jsonl.gz", "rt", encoding="utf8") as f:
            _cache[sid] = [json.loads(x) for x in f]
    return _cache[sid]


def rekaman(sid, juz, p1, p2):
    """Rekaman Shamela yang mencakup halaman p1..p2 (satu rekaman bisa memuat beberapa halaman lewat ⦗n⦘)."""
    for r in kitab(sid):
        if juz != "-" and str(r.get("part")) != str(juz):
            continue
        body = r.get("body") or ""
        awal = r.get("page_num") or 0
        tanda = [int("".join(str(AD.index(c)) for c in m)) for m in re.findall(r"⦗([٠-٩]+)⦘", body)]
        akhir = max([awal] + tanda)
        if awal <= p2 and akhir >= p1:
            yield r, awal


def halaman_potongan(r, awal, pot):
    """Cari potongan (sudah dinormalkan) di badan rekaman; kembalikan (hal_awal, hal_akhir) atau None."""
    body = r.get("body") or ""
    bagian = re.split(r"⦗([٠-٩]+)⦘", body)
    teks, batas, hal = "", [], awal
    for i, b in enumerate(bagian):
        if i % 2:
            hal = int("".join(str(AD.index(c)) for c in b)); continue
        n = vnorm(b)
        batas.append((len(teks), len(teks) + len(n), hal))
        teks += n
    j = teks.find(pot)
    if j < 0:
        return None
    k = j + len(pot) - 1
    h1 = next(h for a, z, h in batas if a <= j < z or (a == z == j))
    h2 = next(h for a, z, h in batas if a <= k < z)
    return h1, h2


def cek(sid, juz, hal, pot, sumber):
    """Kembalikan '' kalau cocok, atau pesan kesalahan."""
    if not (SHAMELA / str(sid) / "pages.jsonl.gz").exists():
        return f"kitab {sid} belum diunduh (python mesin/bahts.py ambil {sid})"
    p1, _, p2 = hal.partition("-")
    p1 = int(p1); p2 = int(p2) if p2 else p1
    if pot.startswith("#"):
        nomor = "".join(AD[int(c)] for c in pot[1:])
        for r, awal in rekaman(sid, juz, p1, p2):
            if re.search(rf"(?<![٠-٩]){nomor}(?![٠-٩])", r.get("body") or ""):
                return ""
        return f"nomor {pot[1:]} tidak ada di {sid} {juz}/{hal}"
    q = vnorm(pot)
    if len(q) < 6:
        return f"potongan terlalu pendek: {pot}"
    ada_di_lain = None
    for r, awal in rekaman(sid, juz, p1, p2):
        h = halaman_potongan(r, awal, q)
        if h:
            if h[0] >= p1 and h[1] <= p2:
                return ""
            ada_di_lain = h
        elif q in vnorm(r.get("footnotes") or ""):
            return ""
    if ada_di_lain:
        return f"teks ada tapi di hal {ada_di_lain[0]}-{ada_di_lain[1]}, bukan {hal} ({sid}) :: {pot[:40]}"
    # cari di seluruh kitab untuk memberi petunjuk
    for r in kitab(sid):
        if q in vnorm(r.get("body") or ""):
            return f"teks TIDAK di {juz}/{hal}; ketemu di ج{r.get('part')} ص{r.get('page_num')} ({sid}) :: {pot[:40]}"
    return f"teks TIDAK KETEMU di kitab {sid} :: {pot[:60]}"


def tercetak(isi, juz):
    """Rentang halaman yang tercetak di catatan kaki untuk juz ini: [(awal, akhir)]."""
    pola = r"ص\s*(\d+)(?:-(\d+))?" if juz == "-" else rf"(?<![\d/]){re.escape(juz)}/(\d+)(?:-(\d+))?"
    return [(int(a), int(b or a)) for a, b in re.findall(pola, isi)]


def cocok_halaman(isi, bukti):
    """Bandingkan juz/halaman yang tercetak dengan bukti [(sid, juz, p1, p2)]; kembalikan daftar galat."""
    if "سبق تخريجه" in isi or not bukti:
        return []
    galat = []
    for juz in {b[1] for b in bukti}:
        ada = {n for _, z, p1, p2 in bukti if z == juz for n in range(p1, p2 + 1)}
        galat += [f"halaman tercetak {juz}/{a}{'-' + str(b) if b != a else ''} tidak punya bukti"
                  for a, b in tercetak(isi, juz) if b - a > 50 or not set(range(a, b + 1)) & ada]
    for sid in {b[0] for b in bukti}:
        if not any(a <= p1 and p2 <= b for s, z, p1, p2 in bukti if s == sid for a, b in tercetak(isi, z)):
            galat.append(f"juz/halaman bukti kitab {sid} tidak tercetak di catatan kaki")
    return [f"{g} || fn: {isi[:60]}" for g in galat]


def ayat(spec):
    """'s:a' | 's:a-b' | 's:a:i-j' -> (teks_utsmani, surah, 'a' atau 'a-b')."""
    p = spec.split(":")
    if len(p) not in (2, 3) or not all(re.fullmatch(r"\d+(-\d+)?", x) for x in p):
        raise ValueError(f"{{Q:{spec}}}: bentuknya {{Q:surat:ayat}}, {{Q:surat:a-b}}, atau {{Q:surat:ayat:i-j}}")
    s = int(p[0])
    if any(f"{s}:{n}" not in QURAN for n in map(int, p[1].split("-"))):
        raise ValueError(f"{{Q:{spec}}}: surat/ayat itu tidak ada")
    if "-" in p[1]:
        a, b = map(int, p[1].split("-"))
        bagian = []
        for n in range(a, b + 1):
            bagian.append(QURAN[f"{s}:{n}"])
            if n < b:
                bagian.append(" " + "".join(AD[int(c)] for c in str(n)))
        return " ".join(bagian).replace("  ", " "), s, p[1]
    t = QURAN[f"{s}:{p[1]}"]
    if len(p) > 2:
        i, _, j = p[2].partition("-")
        i = int(i); j = int(j or i)
        if not 1 <= i <= j <= len(t.split()):
            raise ValueError(f"{{Q:{spec}}}: ayat itu hanya {len(t.split())} kata")
        t = " ".join(t.split()[i - 1: j])
    return t, s, p[1]


TOKEN = re.compile(r"(\*\*|\{(?:Q|H2|H|P):[^}]*\}|\[\^|\])")


KUNCI = re.compile(r"[a-z]+")


def urai(teks, catatan, ayat_idx, hadits_idx, galat, di_catatan=False):
    """Pecah satu baris jadi 'runs'. Catatan kaki ([^...]) diurai rekursif."""
    runs, tebal, i = [], False, 0
    q_akhir = None  # ayat terakhir di baris ini (untuk mencocokkan catatan kaki «سورة …»)
    polos = ""  # teks polos berjalan (untuk mencari kutipan sebelum catatan kaki)
    while i < len(teks):
        m = TOKEN.search(teks, i)
        if not m:
            runs.append({"t": teks[i:], "b": tebal}); polos += teks[i:]; break
        if m.start() > i:
            runs.append({"t": teks[i:m.start()], "b": tebal}); polos += teks[i:m.start()]
        tok = m.group(1)
        i = m.end()
        if tok == "**":
            tebal = not tebal
        elif tok.startswith("{Q:"):
            t, s, a = ayat(tok[3:-1])
            q_akhir = (s, a)
            runs.append({"t": "﴿", "b": False}); runs.append({"t": t, "q": True}); runs.append({"t": "﴾", "b": False})
            if not di_catatan:
                kunci = f"q{len(ayat_idx)}"
                ayat_idx.append({"k": kunci, "t": t, "s": s, "a": a})
                runs.insert(len(runs) - 3, {"bm": kunci})
        elif tok.startswith("{H2:"):
            kunci = "h_" + tok[4:-1]
            induk = next((r for r in hadits_idx if r["k"] == kunci), None)
            if not induk:
                raise ValueError(f"{tok}: belum ada {{H:...|{tok[4:-1]}}} sebelumnya")
            n = 1 + len(induk.setdefault("lagi", []))
            induk["lagi"].append(f"{kunci}_{n}")
            runs.append({"bm": f"{kunci}_{n}"})
        elif tok.startswith("{H:"):
            if tok.count("|") != 2:
                raise ValueError(f"{tok}: bentuknya {{H:طرف|راوٍ|kunci}}")
            taraf, rawi, kunci = tok[3:-1].split("|")
            if not KUNCI.fullmatch(kunci):
                raise ValueError(f"{tok}: kunci hanya boleh huruf a-z")
            if any(r["k"] == "h_" + kunci for r in hadits_idx):
                raise ValueError(f"{tok}: kunci «{kunci}» sudah dipakai (pakai {{H2:{kunci}}})")
            hadits_idx.append({"k": "h_" + kunci, "t": taraf, "r": rawi})
            runs.append({"bm": "h_" + kunci})
        elif tok.startswith("{P:"):
            if not di_catatan:
                raise ValueError(f"{tok}: hanya boleh di dalam catatan kaki")
            if not any(r["k"] == "h_" + tok[3:-1] for r in hadits_idx):
                raise ValueError(f"{tok}: belum ada {{H:...|{tok[3:-1]}}} sebelumnya")
            runs.append({"pg": "h_" + tok[3:-1]})
        elif tok == "[^":
            # cari penutup ] yang seimbang
            d, j = 1, i
            while d and j < len(teks):
                if teks.startswith("[^", j): d += 1; j += 2; continue
                if teks[j] == "]": d -= 1
                j += 1
            if d:
                raise ValueError("catatan kaki [^ tidak ditutup dengan ]")
            isi = teks[i: j - 1]
            i = j
            bukti = re.findall(r"<<([^>]*)>>", isi)
            isi = re.sub(r"\s*<<[^>]*>>", "", isi).strip()
            if "<<" in isi or ">>" in isi:
                raise ValueError("bukti <<...>> tidak tertutup rapi (tidak boleh ada > di dalam potongan)")
            if isi.startswith("سورة") and q_akhir:
                s, a = q_akhir
                if SURAH[s - 1] not in isi or not all(re.search(rf"(?<!\d){x}(?!\d)", isi) for x in a.split("-")):
                    galat.append(f"catatan kaki ayat tidak cocok dengan {{Q:{s}:{a}}} (سورة {SURAH[s - 1]}) || fn: {isi[:45]}")
            # kutipan terakhir tepat sebelum catatan kaki
            mk = re.search(r"[\"«]([^\"«»]*)[\"»][\s.،؛!؟]*$", polos)
            terbukti = []  # (sid, juz, p1, p2) tiap bukti, untuk dicocokkan dengan yang tercetak
            for b in bukti:
                f = b.split("|")
                if len(f) not in (3, 4) or not re.fullmatch(r"\d+", f[0]) or not re.fullmatch(r"\d+(-\d+)?", f[2]):
                    raise ValueError(f"<<{b}>>: bentuknya <<sid|juz|hal>> atau <<sid|juz|hal|potongan>>")
                terbukti.append((f[0], f[1], *map(int, (f[2] + "-" + f[2]).split("-")[:2])))
                if len(f) == 3:
                    if not mk:
                        galat.append(f"[tanpa kutipan] {isi[:50]}"); continue
                    f.append(mk.group(1))
                e = cek(int(f[0]), f[1], f[2], f[3], isi)
                if e:
                    galat.append(e + f"  || fn: {isi[:45]}")
            galat += cocok_halaman(isi, terbukti)
            sub = urai(isi, None, ayat_idx, hadits_idx, galat, di_catatan=True)
            catatan.append({"runs": sub, "bukti": len(bukti)})
            runs.append({"fn": len(catatan) - 1})
        else:  # "]" nyasar
            runs.append({"t": "]", "b": tebal}); polos += "]"
    if tebal:
        raise ValueError("tanda ** tidak berpasangan")
    if re.search(r"\{(?:Q|H2|H|P):", polos):
        raise ValueError("tanda {Q:/{H:/{H2:/{P: tidak ditutup dengan }")
    return [r for r in runs if r.get("t", "x") != ""]


def utama(folder):
    """Olah naskah di `folder`. Kembalikan (jumlah galat, baris laporan)."""
    folder = Path(folder)
    baris = [(n, x.rstrip("\n")) for n, x in enumerate(open(folder / "naskah.txt", encoding="utf-8-sig"), 1) if x.strip()]
    blok, catatan, ayat_idx, hadits_idx, galat, pustaka = [], [], [], [], [], []
    meta = {"berkas": folder.name}
    mode_r = False
    for n, b in baris:
        if b.startswith("@"):
            k, _, v = b[1:].partition(":")
            meta[k.strip()] = v.strip()
        elif b.startswith("#"):
            k, _, t = b[1:].partition(" ")
            if k not in ("K", "F", "B", "M", "S", "R") or not t.strip():
                galat.append(f"baris {n}: judul harus «#K/#F/#B/#M/#S/#R teks» :: {b[:40]}"); continue
            mode_r = k == "R"
            blok.append({"k": k, "runs": [{"t": t, "b": True}], "judul": t})
        elif mode_r:
            pustaka.append(b.strip())
        else:
            try:
                blok.append({"k": "P", "runs": urai(b, catatan, ayat_idx, hadits_idx, galat)})
            except (ValueError, KeyError, IndexError) as e:
                galat.append(f"baris {n}: tanda rusak — {e}")
    if not mode_r:
        galat.append("tidak ada #R (المصادر والمراجع) di akhir naskah")

    def kunci_urut(s):
        s = HARAKAT.sub("", s)
        if not s.startswith("الله"):
            s = re.sub(r"^ال", "", s)
        return re.sub("[إأآ]", "ا", s)
    quran = [p for p in pustaka if p.startswith("القرآن")]
    pustaka = quran + sorted([p for p in pustaka if not p.startswith("القرآن")], key=kunci_urut)

    for a in ayat_idx:
        a["surah"] = SURAH[a["s"] - 1]
    hadits_idx.sort(key=lambda h: kunci_urut(h["t"]))

    # hitung kata
    def kata(runs): return sum(len(re.findall(r"[؀-ۿ]+", r.get("t", ""))) for r in runs)
    n_matan = sum(kata(b["runs"]) for b in blok)
    n_fn = sum(kata(c["runs"]) for c in catatan)
    galat += [f"data sampul belum diisi: @{k}" for k in WAJIB if not meta.get(k)]
    asing = [t for t in re.split(r"[,، ]+", meta.get("tanpa", "")) if t and t not in TANPA]
    if asing:
        galat.append(f"@tanpa: «{'، '.join(asing)}» tidak dikenal (yang ada: {', '.join(TANPA)})")
    if meta.get("thalibah", "ya") != "ya":
        galat.append(f"@thalibah: «{meta['thalibah']}» tidak dikenal: tulis «ya», atau hapus barisnya")
    fmt = meta.get("format", "imam")
    if fmt not in FORMAT:
        galat.append(f"@format: «{fmt}» tidak ada di mesin/format.json (yang ada: {'، '.join(FORMAT)})")
    (HERE / "_tmp").mkdir(exist_ok=True)
    json.dump({"meta": meta, "format": FORMAT.get(fmt), "blok": blok, "catatan": catatan, "ayat": ayat_idx, "hadits": hadits_idx, "pustaka": pustaka},
              open(HERE / "_tmp" / f"{folder.name}.json", "w", encoding="utf8"), ensure_ascii=False)
    n_bukti = sum(c["bukti"] for c in catatan)
    fn_tanpa = [HARAKAT.sub("", "".join(r.get("t", "") for r in c["runs"]))[:60] for c in catatan
                if c["bukti"] == 0 and not "".join(r.get("t", "") for r in c["runs"]).startswith("سورة")]
    lap = [f"blok={len(blok)} | kata matan={n_matan} | catatan kaki={len(catatan)} ({n_fn} kata) | ayat={len(ayat_idx)} | hadits={len(hadits_idx)} | pustaka={len(pustaka)}",
           f"bukti dicek ke Shamela lokal: {n_bukti} | GAGAL: {len(galat)}"]
    lap += [f"  ✗ {g}" for g in galat]
    lap.append(f"catatan kaki tanpa bukti (selain rujukan ayat): {len(fn_tanpa)}")
    lap += [f"  - {f}" for f in fn_tanpa]
    return len(galat), lap
