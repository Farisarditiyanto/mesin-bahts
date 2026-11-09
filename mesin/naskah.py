# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pengurai satu baris naskah (Pengurai): tanda {Q:}, {H:}, {P:}, {A:}, **, ((…)), dan catatan kaki [^…] yang
diperiksa per langkah (CatatanKaki). Hasilnya dikumpulkan di Pemeriksaan, satu objek per naskah."""
import dataclasses, re
from pathlib import Path

import norma
import shamela
from cek_ayat import ayat, ayat_ketik, penanda_ayat, rujukan_ayat
from cek_hadits import hadits_janggal, hadits_lain, periksa_derajat, periksa_takhrij
from cek_kutipan import cek, cek_pdf
from cek_rujukan import cocok_halaman, judul_kitab, judul_shamela, kitab_lain, rujukan_halaman
from cek_sumber import standar_sumber, urutan_sumber
from cek_tautsiq import data_cetak, gelar, pemisah_sumber
from dasar import ANGKA_LATIN, AYAT_DI_KUTIPAN, DIPOTONG, HURUF_LATIN, LUAR, SURAH, TandaRusak, TIDAK_KETEMU
from kitab_lokal import rentang_halaman, salah_halaman, salah_juz
from petik import (
    diantar_qaul, kurung_akhir, kutipan_akhir, kutipan_pendek_diantar, kutipan_semua, luar_petik, seragam)

NOMOR_AYAT = re.compile(r"آي(?:ة|ات)[:\s]*(\d+(?:\s*(?:[-–،,]|و|إلى)\s*\d+)*)")
# teks yang mengutip ayat, bukan sekadar menyebutnya: pengantar «قال الله تعالى:»/«قوله:», atau kurung berhuruf Arab
# minimal dua kata tepat sebelum catatan kaki («ومن ذلك (…)[^سورة …]»); kurung di tengah kalimat atau satu kata
# («(رحمهم الله)», «ومعنى (الرحمن) …») = keterangan, bukan ayat
# «قال الله تعالى», «يقول الله عز وجل في كتابه:», «قال تعالى -» (dengan atau tanpa «:»), kecuali disusul «في …» (penyebutan:
# «كما قال الله تعالى في سورة …»)
PENGANTAR_AYAT = re.compile(r"(?:قال|يقول|قوله)\s+(?:الله\s+|ربنا\s+)?(?:تعالى|سبحانه(?:\s+وتعالى)?|عز\s+وجل|جل\s+وعلا)"
                            r"(?:\s+في\s+كتابه(?:\s+العزيز)?)?(?!\s*في\s)"
                            r"|(?:قال|يقول|قوله|تعالى|سبحانه|وجل)\s*:")
# kurung itu hanya dihitung kalau kalimatnya belum memuat {Q:}: sesudah {Q:}, kurung = tafsiran («أي: … (بجميع المحامد)»)
KURUNG_AYAT = re.compile(r"\((?![^()]*(?:رحم|رضي|عليه|صلى|ت\s*:|هـ))[^()]*[ء-ي]\S*\s+[^()]*\)[\s.،,:؛]*$")
AYAT_TIDAK_COCOK = "catatan kaki ayat tidak cocok dengan {{Q:{0}:{1}}} (سورة {2}) || fn: {3}"
TIDAK_KETEMU_RE = re.compile(re.escape(TIDAK_KETEMU).replace(r"\{\}", r"(\d+)"))
SISA_PETIK = re.compile(rf"[\"«»]|(?<![{HURUF_LATIN}])[‘’'](?![{HURUF_LATIN}])")  # tanda petik yang tidak berpasangan


def _takhrij_dulu(mk, dulu_h, perhatian):
    """«سبق تخريجه، ص{P:k}»: kutipan mk ada di halaman bukti catatan kaki pertama {H:…|k} (potongan lain hadits yang
    sama pun boleh), dicek seperti kutipan biasa (kata utuh, kata nafi yang dibuang). Tanpa bukti di sana: mk harus
    sama dengan (atau kata-kata utuh dari) kutipan {H:} itu."""
    for h in dulu_h:
        for s, z, a, b in h.get("bukti") or ():
            p = []
            if not cek(int(s), z, f"{a}-{b}", mk, p, kutipan=True):
                perhatian += p
                if h.get("kutipan") and hadits_lain(int(s), z, a, b, h["kutipan"], mk):
                    perhatian.append(f"kutipan «سبق تخريجه» ada di halaman bukti takhrij pertamanya, tetapi di hadits bernomor "
                                     f"lain, bukan hadits «{h['kutipan'][:30]}»: pastikan itu hadits yang ditakhrij")
                return True
    kata = lambda t: " " + " ".join(norma.padat(w) for w in t.split() if norma.padat(w)) + " "
    return any(not h.get("bukti") and h.get("kutipan") and kata(mk).strip() and kata(mk) in kata(h["kutipan"]) for h in dulu_h)


TOKEN = re.compile(r"(\*\*|\(\(|\)\)|\{(?:Q|H2|H|P|A):[^}]*\}|\[\^|\])")
KUNCI = re.compile(r"[a-z]+")


@dataclasses.dataclass
class Pemeriksaan:
    """Semua yang dikumpulkan selama satu naskah diurai: bahan rakit (catatan, ayat, hadits), putusan (galat, perhatian),
    dan catatan yang baru dinilai sesudah barisnya atau sesudah seluruh naskah. Satu objek per `periksa`, jadi dua naskah
    yang diperiksa dalam satu proses (mis. `bukti` lalu `cek`) tidak saling mewarisi isi."""
    folder: Path | None = None  # folder bahts (tempat PDF bukti <<luar|berkas|hal>>)
    rumuz: dict = dataclasses.field(default_factory=dict)  # @rumuz: sid -> huruf
    warna: dict = dataclasses.field(default_factory=dict)  # @warna: sid -> warna Word (BGR)
    catatan: list = dataclasses.field(default_factory=list)  # catatan kaki: {"runs", "bukti", "luar", "pdf"}
    ayat_idx: list = dataclasses.field(default_factory=list)  # {Q:} di matan, untuk فهرس الآيات
    hadits_idx: list = dataclasses.field(default_factory=list)  # {H:}, untuk فهرس الأحاديث
    galat: list = dataclasses.field(default_factory=list)
    perhatian: list = dataclasses.field(default_factory=list)
    # (sid, kutipan) yang GAGAL «teks TIDAK KETEMU di kitab»; dikembalikan `olah.utama` (untuk `cek --jejak`)
    tertolak: list = dataclasses.field(default_factory=list)
    # ayat {Q:} dan catatan kaki berbukti, urut naskah, dengan nomor barisnya (dibaca `bukti`):
    #   {"n", "ayat": spec, "t": teks tercetak} atau {"n", "bukti": [sid|juz|hal…], "kutipan": teks yang dibuktikan, "catatan": isi}
    penunjuk: list = dataclasses.field(default_factory=list)
    jangkar: set = dataclasses.field(default_factory=set)  # kunci {A:} naskah ini
    rujuk_silang: list = dataclasses.field(default_factory=list)  # {P:k} yang belum menunjuk {H:}: harus menunjuk {A:k}
    standar: list = dataclasses.field(default_factory=list)  # catatan standar_sumber yang belum dinilai (per bagian)
    dirujuk: set = dataclasses.field(default_factory=set)  # kitab yang sudah dirujuk (rujukan pertama: cek_tautsiq.data_cetak)
    # bahan rakit selain catatan kaki dan فهرس (diisi `periksa`)
    meta: dict = dataclasses.field(default_factory=dict)  # @kunci: nilai
    di_baris: dict = dataclasses.field(default_factory=dict)  # @kunci dan #R -> nomor barisnya (galat yang ketahuan belakangan)
    blok: list = dataclasses.field(default_factory=list)  # paragraf dan judul, urut naskah
    pustaka: list = dataclasses.field(default_factory=list)  # baris sesudah #R
    bentuk: str = ""  # @bentuk: bahts atau kitab
    tanpa: list = dataclasses.field(default_factory=list)  # @tanpa

    def di(self, kunci):
        """Awal pesan «baris n: » untuk @kunci/#R yang sudah dibaca; kosong kalau tidak ditulis di naskah."""
        return f"baris {self.di_baris[kunci]}: " if kunci in self.di_baris else ""


def urai(teks, ctx, di_catatan=False):
    """Pecah satu baris jadi 'runs'; yang terkumpul (catatan kaki, فهرس, galat, perhatian) masuk `ctx` (Pemeriksaan).
    Catatan kaki ([^...]) diurai rekursif dengan di_catatan=True."""
    return Pengurai(teks, ctx, di_catatan).jalan()


class CatatanKaki:
    """Satu catatan kaki [^…] yang sedang diperiksa: isinya, buktinya, dan kutipan yang dirujuknya. Diisi berurutan oleh
    langkah `Pengurai._catatan_kaki`; tiap langkah membaca yang sudah diisi langkah sebelumnya."""
    __slots__ = ("isi", "bukti", "sid_bukti", "diam", "zz", "penggal", "dirujuk", "mk", "mk_pdf", "lain", "luar", "pdf",
                 "terbukti", "kc", "pengantar", "p_kunci", "dikecualikan", "fn")

    def __init__(self, isi, bukti):
        self.isi, self.bukti = isi, bukti
        self.fn = f"  || fn: {isi[:45]}"  # ekor tiap pesan: catatan kaki mana yang dimaksud


class Pengurai:
    """Pengurai satu baris naskah. Tiap tanda (TOKEN) punya penangannya sendiri di PENANGAN; teks di antara tanda jadi
    run biasa. Tanda baru = satu penangan baru, bukan cabang baru di dalam fungsi panjang."""

    def __init__(self, teks, ctx, di_catatan):
        self.teks, self.ctx, self.di_catatan = teks, ctx, di_catatan
        # catatan kaki tidak bercatatan kaki: rumuz/warna/PDF hanya dibaca di matan
        self.rumuz, self.warna, self.folder = (None, None, None) if di_catatan else (ctx.rumuz, ctx.warna, ctx.folder)
        self.runs, self.tebal, self.merah, self.i = [], False, False, 0
        self.q_akhir = None  # ayat terakhir di baris ini (untuk mencocokkan catatan kaki «سورة …»)
        self.polos = ""  # teks polos berjalan (untuk mencari kutipan sebelum catatan kaki)
        self.seg = 0  # awal teks polos sesudah catatan kaki terakhir
        self.penggal_lalu = ""  # teks yang dirujuk catatan kaki sebelumnya (catatan kaki berurutan merujuk teks yang sama)
        # awal teks polos dan runs sesudah catatan kaki berbukti terakhir: paragraf salinan (diam) dicek sejak situ, jadi
        # catatan penjelasan di tengahnya tidak meloloskan kalimat karangan sebelumnya
        self.seg_bukti = self.seg_run_bukti = 0
        self.seg_h = len(ctx.hadits_idx)  # {H:} pertama sesudah catatan kaki terakhir
        self.matn = set()  # letak kurung buka lafaz matn ((…)) di polos: bukan kurung kutipan
        self.h_pos = None  # letak {H:} terakhir di polos: (…) tepat sesudahnya = matan hadits yang dikutip

    @property
    def galat(self):
        return self.ctx.galat

    @property
    def perhatian(self):
        return self.ctx.perhatian

    def _teks(self, t):
        self.runs.append({"t": t, "b": self.tebal, "m": self.merah}); self.polos += t

    def jalan(self):
        teks = self.teks
        while self.i < len(teks):
            m = TOKEN.search(teks, self.i)
            if not m:
                self._teks(teks[self.i:]); break
            if m.start() > self.i:
                self._teks(teks[self.i:m.start()])
            tok = m.group(1)
            self.i = m.end()
            self.PENANGAN[tok[:tok.find(":") + 1] if tok.startswith("{") else tok](self, tok)
        return self._tutup()

    # ---- penangan tanda ----
    def _tebal(self, tok):
        self.tebal = not self.tebal

    def _matn(self, tok):
        if self.merah == (tok == "(("):
            raise TandaRusak(f"tanda {tok} tidak berpasangan: lafaz matn ditulis ((…))")
        self.merah = tok == "(("
        if self.merah:
            self.matn.add(len(self.polos))
        self.runs.append({"t": tok[0], "b": self.tebal, "m": True}); self.polos += tok[0]  # kurung lafaz matn ikut tercetak merah dan dicek

    def _ayat(self, tok):
        ctx = self.ctx
        t, s, a = ayat(tok[3:-1])
        self.q_akhir = (s, a)
        ctx.penunjuk.append({"ayat": tok[3:-1], "t": t})
        self.polos += penanda_ayat(tok[3:-1])
        runs = self.runs
        runs.append({"t": "﴿", "b": False}); runs.append({"t": t, "q": True}); runs.append({"t": "﴾", "b": False})
        if not self.di_catatan:
            kunci = f"q{len(ctx.ayat_idx)}"
            ctx.ayat_idx.append({"k": kunci, "t": t, "s": s, "a": a})
            runs.insert(len(runs) - 3, {"bm": kunci})

    def _hadits_lagi(self, tok):
        kunci = "h_" + tok[4:-1]
        induk = next((r for r in self.ctx.hadits_idx if r["k"] == kunci), None)
        if not induk:
            raise TandaRusak(f"{tok}: belum ada {{H:...|{tok[4:-1]}}} sebelumnya")
        n = 1 + len(induk.setdefault("lagi", []))
        induk["lagi"].append(f"{kunci}_{n}")
        self.runs.append({"bm": f"{kunci}_{n}"})

    def _hadits(self, tok):
        hadits_idx = self.ctx.hadits_idx
        if self.di_catatan:  # penanda فهرس di catatan kaki tidak bisa dibaca halamannya oleh Word
            raise TandaRusak(f"{tok}: tidak boleh di dalam catatan kaki: pindahkan ke matan, tepat sebelum «matan»")
        if tok.count("|") != 2:
            raise TandaRusak(f"{tok}: bentuknya {{H:طرف|راوٍ|kunci}}")
        taraf, rawi, kunci = tok[3:-1].split("|")
        if not KUNCI.fullmatch(kunci):
            raise TandaRusak(f"{tok}: kunci hanya boleh huruf a-z")
        if any(r["k"] == "h_" + kunci for r in hadits_idx):
            raise TandaRusak(f"{tok}: kunci «{kunci}» sudah dipakai (pakai {{H2:{kunci}}})")
        if kunci in self.ctx.jangkar:
            raise TandaRusak(f"{tok}: kunci «{kunci}» sudah dipakai {{A:{kunci}}}")
        hadits_idx.append({"k": "h_" + kunci, "t": taraf, "r": rawi})
        self.h_pos = len(self.polos)
        self.runs.append({"bm": "h_" + kunci})

    def _rujuk_halaman(self, tok):
        if not self.di_catatan:
            raise TandaRusak(f"{tok}: hanya boleh di dalam catatan kaki")
        if any(r["k"] == "h_" + tok[3:-1] for r in self.ctx.hadits_idx):
            self.runs.append({"pg": "h_" + tok[3:-1]})
        else:  # {A:} boleh sesudahnya («سيأتي في ص{P:k}»): dipastikan ada sesudah semua baris dibaca (periksa)
            self.ctx.rujuk_silang.append({"k": tok[3:-1]})
            self.runs.append({"pg": "a_" + tok[3:-1]})

    def _jangkar(self, tok):
        kunci = tok[3:-1]
        if self.di_catatan:  # nomor halaman catatan kaki tidak bisa dibaca seperti matan
            raise TandaRusak(f"{tok}: titik rujukan hanya boleh di matan, bukan di catatan kaki")
        if not KUNCI.fullmatch(kunci):
            raise TandaRusak(f"{tok}: kunci hanya boleh huruf a-z")
        if kunci in self.ctx.jangkar or any(r["k"] == "h_" + kunci for r in self.ctx.hadits_idx):
            raise TandaRusak(f"{tok}: kunci «{kunci}» sudah dipakai {{A:}} atau {{H:}} lain")
        self.ctx.jangkar.add(kunci)
        self.runs.append({"bm": "a_" + kunci})

    def _kurung_nyasar(self, tok):  # "]" tanpa [^
        self.runs.append({"t": "]", "b": self.tebal}); self.polos += "]"

    def _tutup(self):
        polos = self.polos
        if self.tebal:
            raise TandaRusak("tanda ** tidak berpasangan")
        if self.merah:
            raise TandaRusak("tanda (( tidak ditutup dengan ))")
        if re.search(rf"<<(?:\d+\||{LUAR}(?:>>|\|))", polos):
            raise TandaRusak("bukti <<...>> hanya boleh di dalam catatan kaki [^...]; di luar itu ia ikut tercetak")
        kurawal = [t for t in self.PENANGAN if t.startswith("{")]
        if any(t in polos for t in kurawal):
            raise TandaRusak(f"tanda {'/'.join(kurawal)} tidak ditutup dengan }}")
        ketik = None if self.di_catatan else ayat_ketik(polos[self.seg:])  # sesudah catatan kaki terakhir (atau baris tanpa catatan kaki)
        if ketik:
            self.perhatian.append(f"ayat diketik langsung «{ketik[:40]}»: tidak dicek ke mushaf; tulis lewat {{Q:surah:ayat}}")
        return [r for r in self.runs if r.get("t", "x") != ""]

    # ---- catatan kaki [^…]: tiap langkah satu urusan, urut ----
    def _catatan_kaki(self, tok):
        if self.di_catatan:
            raise TandaRusak("catatan kaki tidak boleh di dalam catatan kaki: tutup yang pertama dengan ] dulu")
        c = self._baca_catatan()
        self._kenali_kutipan(c)
        self._cek_rujukan_ayat(c)
        self._cek_tanda_petik(c)
        self._batas_paragraf(c)
        self._pisah_bukti(c)
        self._cek_bukti_shamela(c)
        self._cek_kutipan_di_catatan(c)
        self._cek_kutipan_lain(c)
        self._cek_hadits(c)
        self._cek_tanpa_bukti(c)
        if not c.diam:
            self._cek_penisbatan(c)
            self._cek_tautsiq(c)
        self._pasang_catatan(c)

    def _baca_catatan(self):
        """Isi catatan kaki sampai penutup ]; isi bukti <<...>> dilewati (potongannya boleh memuat ])."""
        teks, i = self.teks, self.i
        j = i
        while j < len(teks) and teks[j] != "]":
            if teks.startswith("[^", j):
                raise TandaRusak("catatan kaki tidak boleh di dalam catatan kaki: tutup yang pertama dengan ] dulu")
            tutup = teks.find(">>", j + 2) if teks.startswith("<<", j) else -1
            j = tutup + 2 if tutup >= 0 else j + 1
        if j >= len(teks):
            raise TandaRusak("catatan kaki [^ tidak ditutup dengan ]")
        isi = teks[i:j]
        self.i = j + 1
        bukti = re.findall(r"<<([^>]*)>>", isi)
        isi = re.sub(r"\s*<<[^>]*>>", "", isi).strip()
        if "<<" in isi or ">>" in isi:
            raise TandaRusak("bukti <<...>> tidak tertutup rapi (tidak boleh ada > di dalam potongan)")
        return CatatanKaki(isi, bukti)

    def _kenali_kutipan(self, c):
        """Teks yang dirujuk catatan kaki ini dan kutipan bertanda petik tepat sebelumnya (mk)."""
        rumuz, polos = self.rumuz, self.polos
        # bukti saja + semua sumbernya di @rumuz: tidak dicetak, dan seluruh teks sejak catatan kaki berbukti sebelumnya
        # = nukilan utuh dari halaman bukti (kitab tanpa catatan kaki: paragraf syarah yang disalin dari kitabnya)
        c.sid_bukti = [b.split("|")[0] for b in c.bukti if b.split("|")[0] != LUAR]
        c.diam = not c.isi and rumuz is not None and bool(c.sid_bukti) and all(x in rumuz for x in c.sid_bukti)
        c.zz = [z for z in dict.fromkeys((rumuz or {}).get(x) for x in c.sid_bukti) if z and z != "-"]
        c.penggal = polos[self.seg_bukti if c.diam else self.seg:]
        # catatan kaki tepat sesudah catatan kaki lain («[^…][^…]») merujuk teks yang sama dengan catatan kaki itu
        c.dirujuk = self.penggal_lalu = c.penggal if re.search(r"\w", c.penggal) else self.penggal_lalu
        # kutipan terakhir tepat sebelum catatan kaki; kutipan lain sejak catatan kaki sebelumnya tidak punya catatan kaki sendiri
        # Catatan penjelasan boleh berada di tengah kutipan, jadi pembukanya dapat sebelum seg.
        # Dua catatan sumber dapat membuktikan nukilan yang sama. Catatan penjelasan tanpa bukti
        # tidak perlu mengulang buktinya, kecuali ada penutup petik baru sesudah catatan terakhir.
        c.mk = kutipan_akhir(polos) if c.bukti or SISA_PETIK.search(seragam(c.penggal)) else None

    def _cek_rujukan_ayat(self, c):
        """Ayat yang diketik sendiri, dan rujukan «سورة …، آية: n» yang harus cocok dengan {Q:} di kalimatnya."""
        isi, dirujuk, q_akhir = c.isi, c.dirujuk, self.q_akhir
        # ayat diketik sendiri lalu dirujuk «سورة …»: tidak pernah dicek ke mushaf, jadi bisa karangan
        # (di dalam tanda petik sudah ditolak di bawah: «سورة …» tidak membebaskan prosa di dalam kutipan)
        ketik = ayat_ketik(c.penggal) if isi.startswith("سورة") or not (self.di_catatan or c.diam) else None
        if ketik and isi.startswith("سورة"):
            self.galat.append(f"ayat diketik langsung «{ketik[:40]}»: tidak dicek ke mushaf; tulis lewat {{Q:surah:ayat}} "
                              f"|| fn: {isi[:45]}")
        elif ketik:  # di matan, tanpa rujukan «سورة …»: bisa ayat karangan; paragraf salinan berbukti (diam) dicek ke kitab
            self.perhatian.append(f"ayat diketik langsung «{ketik[:40]}»: tidak dicek ke mushaf; tulis lewat {{Q:surah:ayat}} "
                                  f"|| fn: {isi[:45]}")
        elif ((isi.startswith("سورة") and re.search(r"[0-9٠-٩۰-۹]", isi) or rujukan_ayat(isi))
              and (PENGANTAR_AYAT.search(re.split(r"﴿\d+:\d+(?:-\d+)?(?::\d+-\d+)?﴾", dirujuk)[-1])
                   or not re.search(r"﴿\d", dirujuk) and KURUNG_AYAT.search(dirujuk)) and not c.bukti and c.mk is None):
            # rujukan ayat bernomor, padahal teks sesudah {Q:} terakhir (atau seluruh teks yang dirujuk) mengutip ayat
            # («قال الله تعالى», «وقال:», atau berkurung): ayatnya diketik tanpa ﴿﴾ dan tidak pernah dicek ke mushaf.
            # Tidak kena: «سورة مكية…» (tanpa nomor) dan penyebutan tanpa kutipan («في سورة طه», «في آيات كثيرة»).
            # Kutipan bertanda petik sudah GAGAL «tanpa bukti» di bawah; yang berbukti <<…>> dicek ke sumbernya.
            self.galat.append(f"ayat sesudah pengantarnya tidak ditulis lewat {{Q:}}: tidak dicek ke mushaf; tulis ayatnya "
                              f"lewat {{Q:surah:ayat}} || fn: {isi[:45]}")
        elif isi.startswith("سورة") and q_akhir:
            s, a = q_akhir
            nama = re.split(r"[،,:(]|\sآي", isi[4:])[0]  # «سورة الفاتحة، آية: 2.» -> «الفاتحة»
            angka = isi.translate(ANGKA_LATIN)
            ayat_sejak = {n for x, y in re.findall(rf"﴿{s}:(\d+)(?:-(\d+))?(?::\d+-\d+)?﴾", c.penggal) for n in range(int(x), int(y or x) + 1)}
            tertulis = NOMOR_AYAT.search(angka)  # hanya nomor sesudah «آية»: juz, halaman, dan tahun di catatan bukan nomor ayat
            if (norma.padat(nama) != norma.padat(SURAH[s - 1]) or not all(re.search(rf"(?<!\d){x}(?!\d)", angka) for x in a.split("-"))
                    or ayat_sejak and tertulis and set(map(int, re.findall(r"\d+", tertulis[1]))) - ayat_sejak):
                self.galat.append(AYAT_TIDAK_COCOK.format(s, a, SURAH[s - 1], isi[:45]))
        elif (q_akhir and re.search(r"﴿\d", dirujuk) and (rj := rujukan_ayat(isi))
              and norma.padat(rj[0]) == norma.padat(SURAH[q_akhir[0] - 1])):
            # rujukan surat yang sama dengan {Q:} di kalimatnya, tidak diawali «سورة»: nomornya tetap harus nomor {Q:}.
            # Surat lain («انظر: سورة النساء، آية: 5») = rujukan silang, tidak dicocokkan.
            s, a = q_akhir
            if not all(re.search(rf"(?<!\d){x}(?!\d)", rj[1]) for x in a.split("-")):
                self.galat.append(AYAT_TIDAK_COCOK.format(s, a, SURAH[s - 1], isi[:45]))

    def _cek_tanda_petik(self, c):
        """Kutipan lain sejak catatan kaki sebelumnya, kurung yang jadi kutipan, dan tanda petik yang tidak berpasangan."""
        polos, seg = self.polos, self.seg
        c.lain = kutipan_semua(polos[seg:])[:-1 if c.mk is not None else None]
        if c.mk is None and c.bukti and not c.diam:  # «قال ﷺ: (…)», «{H:…}(…)»: kurung itu kutipan, dicek seperti "…"
            c.mk = kurung_akhir(polos, seg, self.matn, self.h_pos)
        c.mk_pdf = c.mk  # kutipan untuk bukti PDF: tetap dicek walau mk dikosongkan sesudah galat lain
        sisa = luar_petik(polos[seg:])  # teks sejak catatan kaki sebelumnya, kutipan-kutipannya dibuang
        if c.mk is None and c.bukti and not c.diam and SISA_PETIK.search(sisa):  # nukilan utuh: tanda petiknya tidak menentukan apa pun
            self.perhatian.append(f"tanda petik tanpa pasangan sebelum catatan kaki: kutipannya tidak dikenali dan tidak dicek; "
                                  f"pakai \"…\" atau «…»  || fn: {c.isi[:45]}")
        # «"…" ... "…"»: dua kutipan disambung elipsis di luar petik. Paragraf salinan berbukti (diam) sudah dicek
        # utuh ke kitab, dan «...» di situ bisa pemisah dua paruh bait syair
        if c.lain and DIPOTONG.search(sisa) and not c.diam:
            self.perhatian.append("kutipan disambung ... di luar tanda petik: baca yang dilompati di kitab, pastikan makna dan "
                                  "pembicaranya tetap  || " + (f"fn: {c.isi[:45]}" if c.isi else f"matan: {c.penggal.strip()[:45]}"))

    def _batas_paragraf(self, c):
        """Catatan kaki ini menutup teks yang dirujuknya; paragraf salinan satu kitab berwarna diberi warnanya."""
        self.seg = len(self.polos)
        # batas paragraf salinan: bukti Shamela, atau <<luar>> yang menutup kutipan (yang dicek/diberi perhatian).
        # «سورة …»/«سبق تخريجه» dan <<luar>> tanpa kutipan tidak: teks sebelumnya ikut dicek ke bukti berikutnya
        if c.sid_bukti or c.bukti and c.mk is not None:
            self.seg_bukti = self.seg
        ww = {(self.warna or {}).get(x) for x in c.sid_bukti}
        if c.diam and len(ww) == 1 and None not in ww:  # paragraf salinan satu kitab berwarna: lafaz matn ((…)) tetap merah
            for r in self.runs[self.seg_run_bukti:]:
                if "t" in r and not r.get("m"):
                    r["w"] = next(iter(ww))

    def _pisah_bukti(self, c):
        """<<luar>> dan <<luar|berkas.pdf|hal>> dipisah dari bukti Shamela <<sid|juz|hal>>."""
        c.luar = LUAR in c.bukti
        c.pdf = [b.split("|")[1:] for b in c.bukti if b.startswith(LUAR + "|")]  # <<luar|berkas|hal>>
        for f in c.pdf:
            if len(f) != 2 or not f[0].strip() or not re.fullmatch(r"\d+(-\d+)?", f[1]):
                raise TandaRusak(f"<<{LUAR}|{'|'.join(f)}>>: bentuknya <<{LUAR}|berkas.pdf|hal>>, hal = urutan halaman di berkas")
        c.bukti = [b for b in c.bukti if b.split("|")[0] != LUAR]
        if c.bukti:
            self.ctx.penunjuk.append({"bukti": c.bukti, "kutipan": c.penggal if c.diam else c.mk, "catatan": c.isi})

    def _cek_bukti_shamela(self, c):
        """Tiap bukti <<sid|juz|hal(|potongan)>>: juz/halamannya ada, dan kutipan (atau potongannya) terbaca di sana."""
        galat, perhatian, ctx = self.galat, self.perhatian, self.ctx
        isi, bukti, diam, mk = c.isi, c.bukti, c.diam, c.mk
        c.terbukti = terbukti = []  # (sid, juz, p1, p2) tiap bukti, untuk dicocokkan dengan yang tercetak
        p_awal = len(perhatian)  # perhatian catatan kaki ini mulai di sini
        kutipan_4 = []  # hasil cek kutipan ke tiap bukti berpotongan sendiri: (pesan, perhatian)
        kutipan_3 = []  # hasil cek kutipan ke tiap bukti tanpa potongan: (bukti, pesan)
        tiga = any(b.count("|") == 2 for b in bukti)
        # kutipan bertanda petik di dalam catatan kaki itu sendiri (selain judul kitab; tiga kata atau kurang tanpa «قال …:» = istilah)
        c.kc = [k for k in kutipan_semua(isi) if (len(k.split()) >= 4 or kutipan_pendek_diantar(isi, k))
                and not any(shamela.nomor_judul(k.strip())) and not judul_kitab(k, c.sid_bukti)]
        # teks naskah tepat sebelum kutipan («قال البهوتي:»): pembicaranya dicocokkan dengan kitab di `cek`
        s = seragam(self.polos)
        pengantar = re.split(r'[.،؛"«»\n]', s[:s.rfind(mk) - 1])[-1] if mk and not diam and mk in s else ""
        for b in bukti:
            f = b.split("|")
            if len(f) not in (3, 4) or not re.fullmatch(r"\d+", f[0]) or not re.fullmatch(r"\d+(-\d+)?", f[2]):
                raise TandaRusak(f"<<{b}>>: bentuknya <<sid|juz|hal>> atau <<sid|juz|hal|potongan>>")
            e = salah_juz(int(f[0]), f[1], f[2]) or salah_halaman(f[2])
            if e:  # juz/halamannya belum bisa dibandingkan dengan yang tercetak: satu galat saja
                galat.append(e + f"  || fn: {isi[:45]}"); continue
            terbukti.append((f[0], f[1], *rentang_halaman(f[2])))
            if len(f) == 3 or diam:  # bukti saja: seluruh paragraf dicek, potongannya tidak cukup
                nukilan = c.penggal if diam else mk
                if nukilan is None:
                    if c.kc:  # yang dicek kutipan di dalam catatan kaki (_cek_kutipan_di_catatan)
                        continue
                    galat.append(f"[tanpa kutipan] {isi[:50]}"); continue
                e = cek(int(f[0]), f[1], f[2], nukilan, perhatian, kutipan=True, pengantar=pengantar)
                if not diam:  # kutipan ke bukti tanpa potongan: diputus sesudah semua bukti catatan kaki ini dicek
                    kutipan_3.append((b, e)); continue
            else:
                pot4 = re.sub(r"\{Q:([^}]*)\}", lambda m: penanda_ayat(m.group(1)), f[3])
                e = cek(int(f[0]), f[1], f[2], pot4, perhatian)
                if not e and mk is not None and not tiga:
                    p = []
                    kutipan_4.append((cek(int(f[0]), f[1], f[2], mk, p, kutipan=True, pengantar=pengantar), p))
            if e:
                galat.append(e + f"  || fn: {isi[:45]}")
                sid_bersih = str(int(f[0]))  # «02348» dan «2348» kitab yang sama; pesan cek memakai bentuk tanpa nol
                if e.startswith(TIDAK_KETEMU.format(sid_bersih)):
                    # yang dicek: kutipan sebelum catatan kaki, paragraf salinan (diam), atau potongan bukti itu sendiri
                    t = (c.penggal if diam else mk) if (len(f) == 3 or diam) else pot4
                    if t:
                        ctx.tertolak.append((sid_bersih, t))
        # Tiap bukti tanpa potongan harus memuat kutipannya, bukan cukup salah satunya: <<sid|juz|hal>> menyatakan
        # «kutipan ini ada di sini», jadi kitab kedua yang tidak memuatnya (sumber salah, atau penisbatan palsu) tetap
        # GAGAL. Kutipan yang terbukti di bukti lain catatan kaki ini: pesannya menunjuk bentuk untuk bukti takhrij
        # berlafaz lain atau derajat dari kitab lain (<<sid|juz|hal|lafaz halaman itu>>), bukan «kutipannya salah».
        ada_di = next((b for b, e in kutipan_3 if not e), None)
        if ada_di is None and mk is not None and any(e for _, e in kutipan_3):
            # bukti berpotongan yang juga memuat kutipannya (mis. Bukhari <<1681|1|6|#1>>): hanya mengubah pesannya
            sudah = {b for b, _ in kutipan_3}
            for s, z, a, b_ in terbukti:
                letak = f"{s}|{z}|{a}" if a == b_ else f"{s}|{z}|{a}-{b_}"
                if letak not in sudah and not cek(int(s), z, f"{a}-{b_}", mk, [], kutipan=True, rinci=False):
                    ada_di = letak
                    break
        for b, e in kutipan_3:
            if not e:
                continue
            if ada_di:
                galat.append(f"kutipan sebelum catatan kaki ada di <<{ada_di}>>, tetapi tidak di <<{b}>> ({e.split(' :: ')[0]}): "
                             f"tiap bukti <<sid|juz|hal>> tanpa potongan harus memuat kutipan itu. Bukti lain di catatan kaki "
                             f"takhrij (riwayat berlafaz lain, derajat dari kitab lain) → tulis berpotongan "
                             f"<<{b}|lafaz yang ada di halaman itu>>, mis. kalimat derajatnya  || fn: {isi[:45]}")
                continue
            galat.append(e + f"  || fn: {isi[:45]}")
            sid_bersih = str(int(b.split("|")[0]))
            if e.startswith(TIDAK_KETEMU.format(sid_bersih)):
                ctx.tertolak.append((sid_bersih, mk))
        periksa_derajat(isi, terbukti, periksa_takhrij(isi, bukti, terbukti, mk, perhatian), galat, perhatian)
        # kutipan bertanda petik tetap dicek walau buktinya membawa potongan sendiri: cukup ada di salah satu bukti itu
        if kutipan_4 and all(e for e, _ in kutipan_4):
            # intinya dulu (naskah X, kitab Y), penjelasannya di belakang
            galat.append(f"kutipan sebelum catatan kaki: {kutipan_4[0][0]}; kutipan bertanda petik harus ada di halaman "
                         f"buktinya (potongan <<…|potongan>> hanya membuktikan potongannya; nukilan makna tanpa tanda "
                         f"petik, diawali انظر)  || fn: {isi[:45]}")
            if mk:
                m = TIDAK_KETEMU_RE.search(kutipan_4[0][0])
                if m:
                    ctx.tertolak.append((str(int(m.group(1))), mk))
        else:
            # yang sudah disebut cek potongannya (bagian muhaqqiq, حاشية) tidak diulang untuk kutipannya
            sudah = {x.split(" :: ")[0] for x in perhatian[p_awal:]}
            perhatian += [x for x in next((p for e, p in kutipan_4 if not e), []) if x.split(" :: ")[0] not in sudah]

    def _cek_kutipan_di_catatan(self, c):
        """Kutipan bertanda petik di dalam catatan kaki itu sendiri harus terbaca di halaman buktinya."""
        isi = c.isi
        for k in c.kc if c.terbukti else ():
            kq = re.sub(r"\{Q:([^}]*)\}", lambda m: penanda_ayat(m.group(1)), k)  # {Q:} dicek seperti di matan
            if all(cek(int(s), z, f"{a}-{b}", kq, [], kutipan=True, rinci=False) for s, z, a, b in c.terbukti):
                # judul («"…"، مجلة …», «بعنوان "…"») atau sumber <<luar>>: cukup perhatian. GAGAL hanya untuk nukilan
                # yang diantar «…:» («قال الشيخ: "…"»), bukan «انظر:»/«بعنوان:»
                sebelum, _, ekor = seragam(isi).partition(k)
                sebelum, sesudah = sebelum[:-1].rstrip(), ekor[1:].lstrip()[:1]
                # «قال X: "…"، المصدر» / «قال X "…"» tetap nukilan walau disusul koma atau tanpa titik dua
                qaul = diantar_qaul(sebelum)
                nukilan = not c.luar and (qaul or sebelum.endswith(":") and sesudah not in ("،", ",") and not re.search(
                    r"(?:انظر|ينظر|راجع|بعنوان|عنوانه|كتاب|بحث|سلسلة)\s*:$", sebelum))
                (self.galat if nukilan else self.perhatian).append(
                    f"kutipan di dalam catatan kaki tidak ada di halaman buktinya: «{k[:40]}»; kalau itu judul, istilah, atau "
                    f"nukilan sumber di luar Shamela, buang tanda petiknya atau tambah <<{LUAR}>> dan cocokkan sendiri ke "
                    f"sumbernya  || fn: {isi[:45]}")

    def _cek_kutipan_lain(self, c):
        """Kutipan lain sejak catatan kaki sebelumnya: perhatian, kecuali yang terbaca di halaman bukti catatan kaki ini
        atau yang memang judul yang disebut di catatan kaki itu; tiga kata atau kurang tanpa «قال …:» biasanya istilah."""
        for k in c.lain:
            if len(k.split()) < 4 and not kutipan_pendek_diantar(c.penggal, k) or norma.padat(k) in norma.padat(c.isi):
                continue
            if any(not cek(int(s), z, f"{a}-{b}", k, [], kutipan=True, rinci=False) for s, z, a, b in c.terbukti):
                continue
            self.perhatian.append(f"kutipan tanpa catatan kaki sendiri (hanya kutipan tepat sebelum [^ yang dicek): «{k[:40]}» || fn: {c.isi[:45]}")

    def _cek_hadits(self, c):
        """{H:} sejak catatan kaki sebelumnya dicocokkan dengan buktinya; «سبق تخريجه، ص{P:k}» dengan takhrij pertamanya."""
        hadits_idx, isi = self.ctx.hadits_idx, c.isi
        for h in hadits_idx[self.seg_h:]:
            h.setdefault("kutipan", c.mk); h.setdefault("bukti", list(c.terbukti))
            g, p = hadits_janggal(h, c.terbukti, c.penggal)
            self.galat.extend([f"{g}  || fn: {isi[:45]}"] if g else [])
            self.perhatian.extend([f"{p}  || fn: {isi[:45]}"] if p else [])
        self.seg_h = len(hadits_idx)
        # pengecualian: rujukan ayat «سورة …» sesudah {Q:}, dan «سبق تخريجه، ص{P:…}» (buktinya di catatan kaki pertama)
        # «سورة …» hanya untuk kutipan yang memuat ayat itu; «سبق تخريجه، ص{P:k}» hanya untuk kutipan yang sama
        # dengan kutipan {H:…|k} di catatan kaki pertamanya
        c.p_kunci = p_kunci = re.findall(r"\{P:([a-z]+)\}", isi)
        dulu_h = [h for h in hadits_idx if h["k"] in {"h_" + k for k in p_kunci}]
        mk = c.mk
        # «سورة …» hanya membebaskan kutipan yang isinya ayat saja; prosa lain di dalamnya butuh bukti
        c.dikecualikan = ((isi.startswith("سورة") and self.q_akhir and "﴿" in (mk or "")
                           and not norma.padat(AYAT_DI_KUTIPAN.sub(" ", mk)))
                          or (isi.startswith("سبق تخريجه") and p_kunci and mk is not None and _takhrij_dulu(mk, dulu_h, self.perhatian)))
        if not c.bukti and mk is not None and isi.startswith("سبق تخريجه") and p_kunci and not c.dikecualikan:
            self.galat.append(f"kutipan «{mk[:30]}» berbeda dari yang ditakhrij di {{H:…|{p_kunci[0]}}}: beri bukti <<sid|juz|hal>>"
                              f"  || fn: {isi[:45]}")
            c.mk = None  # sudah dilaporkan

    def _cek_tanpa_bukti(self, c):
        """Bukti PDF selalu dicek; kutipan atau rujukan kitab tanpa bukti Shamela = GAGAL atau perhatian."""
        isi, mk, galat, perhatian = c.isi, c.mk, self.galat, self.perhatian
        # tiap bukti PDF selalu dicek (juga sesudah سورة / سبق تخريجه): berkas dan halamannya tetap harus benar
        if c.pdf:
            for b, h in c.pdf:
                cek_pdf(self.folder, b.strip(), h, c.mk_pdf, galat, perhatian, isi[:45])
        elif not c.bukti and mk is not None and not c.dikecualikan:
            if c.luar:
                # <<luar>> hanya untuk sumber yang memang tidak ada di Shamela: judul kitab Shamela = GAGAL
                judul, persis, mirip = judul_shamela(isi)
                if persis:
                    galat.append(f"«{judul}» ada di Shamela (nomor {'، '.join(map(str, persis))}): <<{LUAR}>> hanya untuk "
                                 f"sumber di luar Shamela; ambil kitabnya lalu tulis <<sid|juz|hal>>  || fn: {isi[:45]}")
                else:
                    mirip = (f"; «{judul}» mirip kitab Shamela nomor {'، '.join(map(str, mirip[:3]))}: kalau itu sumbernya, "
                             f"ambil lalu pakai <<sid|juz|hal>>") if mirip else ""
                    perhatian.append(f"kutipan «{mk[:30]}» dari sumber di luar Shamela (<<{LUAR}>>): mesin tidak bisa mengeceknya, "
                                     f"cocokkan sendiri lafaz dan halamannya ke sumbernya{mirip}  || fn: {isi[:45]}")
            else:
                galat.append(f"kutipan «{mk[:30]}» tanpa bukti: tambahkan <<sid|juz|hal>> di catatan kakinya; "
                             f"sumber yang tidak ada di Shamela (jurnal, PDF penelitian): tulis <<{LUAR}>>  || fn: {isi[:45]}")
        elif not c.bukti and not c.luar and not isi.startswith(("سورة", "سبق تخريجه")) and rujukan_halaman(isi):
            # rujukan kitab (juz/halaman, رقم الحديث) tanpa kutipan bertanda petik: penisbatan yang belum dibuktikan
            perhatian.append(f"rujukan kitab tanpa bukti (halaman atau nomor hadits tercetak, tetapi tidak ada <<…>>): "
                             f"tambahkan <<sid|juz|hal>>; sumber yang tidak ada di Shamela: tulis <<{LUAR}>>  || fn: {isi[:45]}")

    def _cek_penisbatan(self, c):
        """Juz/halaman dan nama kitab yang tercetak di catatan kaki cocok dengan buktinya; standar dan urutan sumber."""
        isi, terbukti, galat, perhatian = c.isi, c.terbukti, self.galat, self.perhatian
        salah_hal = cocok_halaman(isi, terbukti, perhatian)
        galat += salah_hal
        g, p = kitab_lain(isi, [b[0] for b in terbukti]) if "سبق تخريجه" not in isi else (None, None)
        galat += [f"{g}  || fn: {isi[:45]}"] if g else []
        perhatian += [f"{p}  || fn: {isi[:45]}"] if p else []
        st = standar_sumber(c.penggal, isi, [b[0] for b in terbukti]) if not self.di_catatan else None
        self.ctx.standar.extend([st] if st else [])
        # halaman yang salah dibetulkan dulu: letak kitab di catatan kaki itu bisa ikut berubah
        u = urutan_sumber(isi, terbukti) if not self.di_catatan and not salah_hal else None
        perhatian += [u] if u else []

    def _cek_tautsiq(self, c):
        """Bentuk rujukan (cek_tautsiq): data cetak di rujukan pertama tiap kitab, «؛» antarsumber, nama tanpa gelar."""
        self.perhatian.extend(data_cetak(c.isi, c.terbukti, self.ctx.dirujuk))
        for p in (pemisah_sumber(c.isi, c.terbukti) if len(c.terbukti) > 1 else None, gelar(c.isi, "fn")):
            if p:
                self.perhatian.append(p)

    def _pasang_catatan(self, c):
        """Catatan kaki jadi bahan rakit: diurai sendiri, rumuz-nya dicetak, nomornya dipasang di matan."""
        sub = urai(c.isi, self.ctx, di_catatan=True)
        self.runs += [{"z": z} for z in c.zz]
        self.ctx.catatan.append({"runs": sub, "bukti": len(c.bukti), "luar": c.luar, "pdf": len(c.pdf)})
        if not c.diam:
            self.runs.append({"fn": len(self.ctx.catatan) - 1})
        if self.seg_bukti == self.seg:
            self.seg_run_bukti = len(self.runs)

    PENANGAN = {"**": _tebal, "((": _matn, "))": _matn, "{Q:": _ayat, "{H2:": _hadits_lagi, "{H:": _hadits,
                "{P:": _rujuk_halaman, "{A:": _jangkar, "[^": _catatan_kaki, "]": _kurung_nyasar}
