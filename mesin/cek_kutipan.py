# SPDX-License-Identifier: AGPL-3.0-or-later
"""Inti `cek`: kutipan (atau potongan bukti) harus terbaca di juz/halaman kitab yang dirujuk. Juga perhatian
soal kutipan itu: حاشية المحقق, pembicara lain, kata nafi, angka, sisipan [ ], dan bukti PDF <<luar|berkas|hal>>."""
import bisect, dataclasses, enum, re
from pathlib import Path

import cocok
import norma
import shamela
import sumber_pdf
import waqfeya
from cek_ayat import ayat_persis, ayat_sama, ayat_tercetak, mirip_ayat, pesan_tercetak
from dasar import (
    ekor, perintah,
    ANGKA_LATIN, AYAT_DI_KUTIPAN, AYAT_KITAB, DIPOTONG, ELIPSIS, KUTIPAN_MIN, LUAR, POTONGAN_MIN, QAUL,
    RUJUKAN_AYAT, TIDAK_KETEMU, WAQFEYA_BUKTI)
from kitab_lokal import (
    nomor_hadits,
    cari_di, gabung, halaman_janggal, kitab, rangkaian_kitab, rekaman, rekaman_dulu, rekaman_urut, rentang_halaman,
    susunan_bagian, tempat_kitab, urut_juz)

NASKAH_TULISAN = re.compile("(?:الكتاب|البحث) (?:مخطوط|غير مطبوع)")  # nomornya nomor lembar naskah tulisan/ketikan
# tambahan peneliti di dalam kutipan: «[هكذا]» sesudah salah yang disalin apa adanya, atau kata yang dibetulkan di dalam
# kurung siku (أبو سليمان، كتابة البحث العلمي، ص112-113، 174). Dicoba hanya kalau kutipan apa adanya tidak cocok: kurung
# siku milik kitab sendiri («[ممن]», tambahan muhaqqiq) tetap dicek sebagai lafaz kitab. Kurung berangka bukan sisipan:
# «[القصص: 25]» yang nomornya diganti penulis tetap GAGAL. Selain «[هكذا]»/«[كذا]», tiap sisipan = perhatian: isinya
# tercetak di dalam tanda petik yang dinisbatkan ke pengarang, padahal mesin tidak bisa menilai («[ليس]» membalik makna)
SISIPAN = re.compile(r"\[[^\[\]^0-9٠-٩۰-۹]*\]")
HAKADHA = re.compile(r"\[\s*(?:هكذا|كذا)\s*\]")
JARAK_AYAT = 300  # huruf `padat` celah {Q:} yang ayatnya tanpa ﴿﴾ di kitab (dikenali dari teksnya) sebelum jadi perhatian
SISA_AYAT = 20  # huruf `padat` kitab selain ayat dan rujukan [سورة: n] di celah {Q:} sebelum jadi perhatian
NAFI = {"لا", "فلا", "ولا", "ما", "فما", "وما", "ليس", "وليس", "فليس", "ليست", "وليست", "فليست",
        "لم", "ولم", "فلم", "لن", "ولن", "فلن", "بلا", "وبلا", "فبلا"}  # kata tepat sebelum kutipan di kitab yang bisa membalik maknanya
HENTI = re.compile(r"[.،,؛;؟?!:]")  # tanda akhir kalimat di teks kitab: kata nafi di depannya milik kalimat sebelumnya


class Jenis(enum.Enum):
    """Jenis temuan `cek` yang dikenali pemeriksa (untuk memutuskan sesuatu) atau jadi kunci sekali-sebut (Catat)."""
    TIDAK_KETEMU = enum.auto()  # teksnya tidak ada di kitab itu sama sekali: bahan `cek --jejak`
    HASYIAH = enum.auto()  # bukti ada di حاشية المحقق
    DILOMPATI = enum.auto()  # kutipan dipotong ...: ada teks kitab yang dilompati
    SISIPAN_GANTI = enum.auto()  # kurung siku penulis menggantikan teks kitab
    SISIPAN_TAMBAH = enum.auto()  # kurung siku penulis yang tidak menggantikan apa pun
    OTOMATIS = enum.auto()  # nomor halaman buatan Shamela
    NASKAH_TULISAN = enum.auto()  # kitab belum dicetak
    HALAMAN_JANGGAL = enum.auto()  # nomor halaman yang menyendiri


@dataclasses.dataclass(frozen=True)
class Temuan:
    """Satu galat atau perhatian dari `cek`; baru jadi kalimat (str) waktu dimasukkan ke laporan."""
    sebab: str
    teks: str | None = None  # teks naskah yang dimaksud, dicetak sesudah « :: »
    jenis: Jenis | None = None
    sekali: tuple | None = None  # kunci temuan yang cukup disebut sekali (per kitab): lihat Catat

    def __str__(self):
        return self.sebab if self.teks is None else f"{self.sebab} :: {self.teks}"


class Catat(list):
    """Perhatian [Temuan] yang dikumpulkan `cek`. `sekali` = kunci temuan sekali-sebut yang sudah ada di daftar ini;
    Catat(himpunan) memakai himpunan pemanggil (Pemeriksaan.sekali), jadi «sudah disebut» berlaku untuk seluruh naskah."""

    def __init__(self, sekali=None):
        super().__init__()
        self.sekali = set() if sekali is None else sekali

    def tambah(self, temuan):
        if temuan.sekali is None:
            self.append(temuan)
        elif temuan.sekali not in self.sekali:
            self.sekali.add(temuan.sekali); self.append(temuan)

    def gabung(self, temuan):
        """Hasil daftar lain disalin apa adanya (yang sekali-sebut pun), dan kuncinya dicatat."""
        for t in temuan:
            self.append(t)
            if t.sekali is not None:
                self.sekali.add(t.sekali)


def bagian_kutipan(kutipan):
    """Bagian-bagian berhuruf Arab sebuah kutipan (None = tanpa kutipan), dipisah ... atau ayat {Q:}."""
    return [b for b in ELIPSIS.split(kutipan or "") if norma.padat(b)]


def terbaca(b, kutipan):
    """Kutipan bertanda petik terbaca di halaman bukti b: ya/tidak saja, tanpa pesan dan perhatian."""
    return not cek(b, kutipan, Catat(), kutipan=True, rinci=False)


def cek_pdf(folder, berkas, hal, kutipan, galat, perhatian, isi):
    """Bukti <<luar|berkas|hal>>: kutipan dicari di teks PDF folder/berkas. Hanya penunjuk halaman, tidak pernah
    lolos: tiap bukti PDF menambah satu galat (berkas/halaman salah) atau satu perhatian (cocokkan sendiri)."""
    tanda = f"<<{LUAR}|{berkas}|{hal}>>"
    folder = Path(folder).resolve()
    p = (folder / berkas).resolve()
    if not p.is_relative_to(folder):
        galat.append(f"{tanda}: PDF bukti harus di dalam folder bahts {folder.name} (tulis nama berkasnya saja){ekor(isi)}")
        return
    if not p.is_file():
        galat.append(f"{tanda}: berkas «{berkas}» tidak ada di folder bahts {folder.name}; simpan PDF-nya di sana "
                     f"(mis. {perintah('dirasat-pdf <W…> ' + folder.name)}){ekor(isi)}")
        return
    bagian = bagian_kutipan(kutipan)
    if pendek := next((b for b in bagian if len(norma.padat(b)) < KUTIPAN_MIN), None):
        galat.append(f"bagian kutipan terlalu pendek untuk dicek (paling sedikit {KUTIPAN_MIN} huruf; jangan dipotong "
                     f"... di situ) :: {pendek.strip()[:30]}{ekor(isi)}")
        return
    a, z = rentang_halaman(hal)
    if not 1 <= a <= z:
        galat.append(f"{tanda}: hal = urutan halaman di berkas PDF, mulai 1; rentang ditulis kecil-besar (mis. 3-4){ekor(isi)}")
        return
    try:
        teks = sumber_pdf.halaman(p)
        if z > len(teks):
            galat.append(f"{tanda}: PDF itu hanya {len(teks)} halaman (hal = urutan halaman di berkas, mulai 1){ekor(isi)}")
            return
        if cacat := sumber_pdf.masalah_struktur(p):
            perhatian.append(f"struktur PDF «{berkas}» bermasalah ({'; '.join(cacat)}): nomor halaman bisa bergeser, "
                             f"periksa langsung di pembaca PDF{ekor(isi)}")
        if kutipan is None:  # nukilan makna: berkas dan halaman tetap dicek, isi diperiksa orang
            perhatian.append(f"nukilan tanpa tanda petik dari PDF ({berkas}): mesin tidak mengecek isinya; pastikan sendiri "
                             f"maknanya ada di halaman itu{ekor(isi)}")
            return
        di_rentang = sumber_pdf.ada_di_rentang(teks, bagian, a, z)
        ketemu = None if di_rentang else sumber_pdf.cari(teks, bagian)
        scan = not di_rentang and not ketemu and all(sumber_pdf.tanpa_teks(teks, n) for n in range(a, z + 1))
    except Exception as e:  # noqa: BLE001 — pypdf: PDF rusak, bersandi, atau bentuk yang tidak dikenalnya
        perhatian.append(f"PDF «{berkas}» tidak bisa dibaca mesin ({type(e).__name__}): cocokkan sendiri lafaz dan "
                         f"halamannya{ekor(isi)}")
        return
    if di_rentang:
        perhatian.append(f"kutipan «{kutipan[:30]}» ditemukan di halaman {hal} «{berkas}» (penunjuk, bukan bukti: teks PDF "
                         f"tidak dibaca persis; angka, urutan kata, dan huruf seperti العلم/العمل tidak dibedakan): buka "
                         f"halaman itu dan cocokkan sendiri lafaznya{ekor(isi)}")
    elif ketemu:
        galat.append(f"kutipan «{kutipan[:30]}» tidak ada di halaman berkas {hal} «{berkas}», tetapi ada di halaman "
                     f"{'، '.join(map(str, ketemu[:5]))}{ekor(isi)}")
    elif scan:
        perhatian.append(f"halaman {hal} «{berkas}» berupa gambar (scan), teksnya tidak terbaca mesin: cocokkan sendiri "
                         f"lafaz kutipan «{kutipan[:30]}»{ekor(isi)}")
    else:
        perhatian.append(f"kutipan «{kutipan[:30]}» tidak ada di teks PDF «{berkas}»: lafaznya berbeda atau karangan, atau "
                         f"teks PDF-nya rusak; buka PDF-nya dan cocokkan sendiri lafaz dan halamannya{ekor(isi)}")


def cek_waqfeya(bukti, kutipan, galat, isi):
    """Bukti <<w…|berkas|hal>> (kitab Waqfeya, waqfeya.py). `cek` hanya menjaga yang pasti salah: kitab belum diunduh,
    berkas/halaman yang tidak ada, dan kutipan yang terbaca persis di halaman LAIN tetapi tidak di halaman yang ditulis
    (nomor halaman salah). Cocok-tidaknya lafaz TIDAK dinilai di sini: OCR salah huruf (±28% kutipan 15 kata), jadi
    kutipan yang benar sering tidak terbaca persis; lafaz dan nomor cetak dinilai pemeriksa dari scan (`bukti` menunjuk
    halamannya beserta hasil OCR), bukan jadi perhatian yang harus diterima satu per satu."""
    tanda = f"<<{bukti}>>"
    w, n, hal = WAQFEYA_BUKTI.fullmatch(bukti).groups()
    try:
        keadaan, rinci = waqfeya.periksa_kutipan(w, int(n), hal, bagian_kutipan(kutipan))
    except ValueError as e:
        galat.append(f"{tanda}: {e}{ekor(isi)}")
        return
    if keadaan == "belum":
        galat.append(f"{tanda}: kitab Waqfeya {w} belum diunduh: {perintah('ambil ' + w)}{ekor(isi)}")
    elif keadaan == "rusak":
        galat.append(f"{tanda}: {rinci} (hal = urutan halaman di berkas PDF, mulai 1){ekor(isi)}")
    elif keadaan == "lain":
        galat.append(f"kutipan «{kutipan[:30]}» tidak ada di OCR {tanda}, tetapi terbaca persis di " + "، ".join(
            f"berkas {m} hal PDF {h}" for m, h in rinci[:5]) + f": betulkan halamannya ({perintah('cari ' + w + ' …')})"
            f"{ekor(isi)}")


def _petunjuk(sid, juz, q):
    """Tempat q di seluruh kitab untuk pesan kesalahan: matan dulu (juz yang ditulis didahulukan), baru حاشية."""
    tempat, hasyiah = [], None
    padat_, ix = shamela.padat_kitab(sid), shamela.indeks(sid)
    kena = set(padat_.kena(q))  # rekaman lain tidak memuat q: tidak menambah apa pun
    # urutan rekaman(sid, "-"): per juz (urut kemunculan pertamanya), lalu urut berkas
    for r in (padat_.isi({"part": ix[i][0]}, i) for ii in kitab(sid).values() for i in ii if i in kena):
        h = cocok.tempat(r, q)
        if h:
            t = (shamela.nama_juz(r.get("part")) != juz, shamela.letak(shamela.nama_juz(r.get("part")), h))
            if t not in tempat:
                tempat.append(t)
        elif not hasyiah:
            h = cocok.tempat(r, q, "footnotes")
            if h:
                hasyiah = shamela.letak(shamela.nama_juz(r.get("part")), h) + " [حاشية]"
    if tempat:
        tempat = [t for _, t in sorted(tempat, key=lambda t: t[0])]
        lagi = f" (dan {len(tempat) - 3} tempat lain)" if len(tempat) > 3 else ""
        return "، ".join(tempat[:3]) + lagi
    if hasyiah:
        return hasyiah
    t = tempat_kitab(rangkaian_kitab(sid), [norma.bait(q)])  # kutipan yang menyambung ke halaman berikutnya
    return shamela.letak(t[0], t[1]) + t[2] if t else None


def temuan_hasyiah(b, teks, samar):
    if samar:
        return Temuan(f"bukti ada di حاشية المحقق {b.sid} {b.juz}/{b.hal}, tetapi halaman tiap catatan di rekaman ini tidak "
                      f"tercatat: pastikan halamannya dengan `halaman`; itu kalimat muhaqqiq, bukan pengarang", teks[:40],
                      Jenis.HASYIAH)
    return Temuan(f"bukti ada di حاشية المحقق, bukan di matan kitab {b.sid} {b.juz}/{b.hal}: "
                  f"itu kalimat muhaqqiq, bukan pengarang", teks[:40], Jenis.HASYIAH)


def _cek_bagian(b, teks, utuh, perhatian, rinci):
    """Cek satu teks (kutipan, satu bagian kutipan berelipsis, atau potongan) di halaman bukti b; None kalau cocok.
    rinci=False: pesan kesalahannya tidak disusun (mencari di seluruh kitab), untuk pemanggil yang hanya butuh cocok/tidak."""
    sid, juz, hal, p1, p2 = b.sid, b.juz, b.hal, b.p1, b.p2
    q = norma.padat(teks)
    jenis, lain = cari_di(sid, juz, p1, p2, q, utuh, cocok.kata_dalam(teks))
    if jenis in ("hasyiah", "hasyiah?"):
        perhatian.tambah(temuan_hasyiah(b, teks, jenis == "hasyiah?"))
    if jenis:
        return None
    if not rinci:
        return Temuan("tidak cocok")
    if utuh and cari_di(sid, juz, p1, p2, q, False)[0]:
        if cari_di(sid, juz, p1, p2, q, True)[0]:  # ujungnya utuh, yang bergeser batas kata di dalamnya
            return Temuan(f"pembagian kata kutipan beda dengan kitab {sid} {juz}/{hal} (mis. «بل أشك» ≠ «بلا شك»): salin "
                          f"spasinya seperti di kitab, lihat `teks {sid} \"…\"`", teks[:40])
        return Temuan(f"kutipan mulai atau berakhir di tengah kata (kitab {sid} {juz}/{hal}): salin kata pertama dan "
                      f"terakhirnya utuh, lihat `teks {sid} \"…\"`", teks[:40])
    if lain:
        return Temuan(f"teks ada tapi di {shamela.letak(juz, lain[:2])}{lain[2]}, bukan {hal} ({sid})", teks[:40])
    ada = _petunjuk(sid, juz, q)
    if ada:
        return Temuan(f"teks TIDAK di {juz}/{hal}; ketemu di {ada} ({sid})", teks[:40])
    beda = _menyimpang(sid, juz, p1, p2, teks)
    if beda:
        return Temuan(f"teks berbeda dengan kitab {sid} {juz}/{hal}: {beda}", teks[:40])
    return Temuan(TIDAK_KETEMU.format(sid), teks[:60], Jenis.TIDAK_KETEMU)


def _menyimpang(sid, juz, p1, p2, teks):
    """Kata pertama kutipan yang berbeda dengan matan halaman itu: awalan terpanjang kutipan yang ada di matan,
    lalu kata sesudahnya di naskah dan di kitab. '' kalau awalannya terlalu pendek untuk ditunjuk."""
    if not rekaman(sid, juz, p1, p2):
        return ""
    raw = re.sub(r"\s+", " ", norma.HARAKAT.sub("", norma.TAGS.sub("", " ".join(g["body"] for g in gabung(sid, juz, p1, p2)))))
    raw = norma.PENANDA.sub(" ", raw)
    kitab_padat = norma.padat(raw)
    kata = teks.split()
    lo, hi = 0, len(kata) - 1  # awalan sepanjang kata[:lo] ada di matan; kata[:hi+1] tidak (kutipan utuhnya tidak ketemu)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if norma.padat(" ".join(kata[:mid])) in kitab_padat:
            lo = mid
        else:
            hi = mid - 1
    awalan = norma.padat(" ".join(kata[:lo]))
    if lo < 2 or len(awalan) < KUTIPAN_MIN:
        return ""
    akhir = kitab_padat.find(awalan) + len(awalan)
    awal_kata = [m.start() for m in re.finditer(r"\S+", raw)]
    a, z = 0, len(awal_kata)  # kata pertama yang mulai sesudah awalan; panjang `padat` awalan teks naik bersama letaknya
    while a < z:
        mid = (a + z) // 2
        if len(norma.padat(raw[:awal_kata[mid]])) >= akhir:
            z = mid
        else:
            a = mid + 1
    di_kitab = raw[awal_kata[a]:].split()[0].strip(".,،؛:!؟\"«»()") if a < len(awal_kata) else "(akhir halaman)"
    return f"cocok {lo} dari {len(kata)} kata sampai «…{' '.join(kata[max(0, lo - 3):lo])}», lalu naskah «{kata[lo]}», kitab «{di_kitab}»"


# awal pesan perhatian kurung siku di kutipan (bukan milik kitab): kata pembetul, dan tambahan penulis
SISIPAN_PERHATIAN = ("kutipan bersisipan [ ] yang menggantikan teks kitab", "kutipan memuat tambahan penulis")


def cek(b, pot, perhatian, *, kutipan=False, rinci=True, pengantar=""):
    """None kalau pot ada di halaman bukti b (kitab_lokal.Bukti yang juz/halamannya sudah lolos `Bukti.salah`), atau
    Temuan kesalahannya.
    kutipan=True: pot = kutipan bertanda petik di naskah. Ia harus mulai dan berakhir di batas kata kitab, boleh dipotong
    dengan ... (tiap bagian dicek, harus berurutan); angka dan kata nafi sebelumnya diperiksa sebagai perhatian.
    Kurung siku yang tidak ada di kitab = SISIPAN peneliti: dibaca seperti pemisah ..., jadi yang di luarnya tetap dicek.
    Yang lolos tetapi harus dilihat orang (bukti di حاشية, nomor halaman bukan cetakan) ditambahkan ke `perhatian` (Catat).
    rinci=False: pesan kesalahannya tidak disusun, untuk pemanggil yang hanya butuh cocok/tidak.
    pengantar = teks naskah tepat sebelum kutipan («قال البهوتي:»), untuk memeriksa pembicaranya di kitab."""
    if not (kutipan and SISIPAN.search(pot)):
        return _cek(b, pot, perhatian, kutipan, rinci, pengantar)
    coba = Catat()
    if not _cek(b, pot, coba, kutipan, rinci, pengantar):
        perhatian.gabung(coba)  # kurung siku itu milik kitab
        return None
    p_awal = len(perhatian)
    # «[صوابه]» menggantikan kata kitab: yang dilompati harus dibaca, tetapi namanya sisipan, bukan potongan ...
    e = _cek(b, SISIPAN.sub(" … ", pot), perhatian, kutipan, rinci, pengantar, bersisipan=True)
    lain = [m.group() for m in SISIPAN.finditer(pot) if not HAKADHA.fullmatch(m.group())]
    if not e and lain and not any(t.jenis is Jenis.SISIPAN_GANTI for t in perhatian[p_awal:]):
        perhatian.tambah(Temuan(
            f"{SISIPAN_PERHATIAN[1]} {'، '.join(lain)[:40]} yang tidak ada di kitab {b.sid} {b.juz}/{b.hal}: "
            f"kurung siku di dalam kutipan hanya untuk membetulkan salah atau «[هكذا]» (أبو سليمان، كتابة "
            f"البحث العلمي، ص112-113)؛ penjelasan pindahkan ke luar kutipan atau ke catatan kaki", pot[:40], Jenis.SISIPAN_TAMBAH))
    return e


def _cek(b, pot, perhatian, kutipan, rinci, pengantar, bersisipan=False):
    """`cek` untuk pot apa adanya. bersisipan=True: pot = kutipan yang kurung siku penulisnya sudah diganti «…», jadi
    yang dilompati di kitab disebut sisipan, bukan potongan."""
    sid, juz, hal, p1, p2 = b.sid, b.juz, b.hal, b.p1, b.p2
    p0 = len(perhatian)
    if juz == "-" and None not in kitab(sid) and len(kitab(sid)) > 1:
        # kitab yang bagiannya hanya bernama (المقدمة tulisan muhaqqiq + الكتاب): «-» digabung, jadi halaman yang ada di
        # dua bagian dibaca di bagian tempat teksnya cocok. Cocok di satu bagian -> bagian itu (المقدمة -> perhatian
        # muhaqqiq lewat toc); cocok di dua bagian -> tidak tentu yang mana.
        di = sorted(shamela.bagian_halaman(sid, p1, p2), key=urut_juz)
        if len(di) > 1:
            kena = [j for j in di if not _cek(dataclasses.replace(b, juz=j), pot, Catat(), kutipan, False, "")]
            if len(kena) == 1:
                return _cek(dataclasses.replace(b, juz=kena[0]), pot, perhatian, kutipan, rinci, pengantar, bersisipan)
            if kena:
                pilih = " atau ".join(f"<<{sid}|{j}|{hal}>>" for j in kena)
                return Temuan(f"teks ada di halaman {hal} beberapa bagian kitab {sid} ({'، '.join(kena)}): sebut bagiannya "
                              f"({pilih}); «ص{hal}» di catatan kaki tetap cukup", pot[:40])
    if shamela.OTOMATIS.search(shamela.info(sid)["betaka_text"]):
        perhatian.tambah(Temuan(f"kitab {sid}: nomor halamannya buatan Shamela (مرقم آليا), bukan nomor cetakan — "
                                "pakai edisi yang «موافق للمطبوع», atau cocokkan ke cetakannya",
                                jenis=Jenis.OTOMATIS, sekali=(Jenis.OTOMATIS, sid)))
    elif NASKAH_TULISAN.search(shamela.info(sid)["betaka_text"]):
        perhatian.tambah(Temuan(f"kitab {sid}: belum dicetak (مخطوط/غير مطبوع), nomor halamannya nomor lembar naskah — "
                                "sebut lembarnya (مخطوط، ل n) atau pakai edisi cetak kalau ada",
                                jenis=Jenis.NASKAH_TULISAN, sekali=(Jenis.NASKAH_TULISAN, sid)))
    for n, (x, y) in halaman_janggal(sid, juz).items():
        if p1 <= n <= p2:
            perhatian.tambah(Temuan(
                f"nomor halaman {juz}/{n} kitab {sid} jauh dari halaman lain juz itu (rekaman sebelum/sesudahnya di Shamela: "
                f"{'، '.join(f'ص{h}' for h in (x, y) if h)}): mungkin salah ketik Shamela; cocokkan ke cetakan (`scan`) dan "
                f"tulis nomor cetakannya", jenis=Jenis.HALAMAN_JANGGAL, sekali=(Jenis.HALAMAN_JANGGAL, sid, juz, n)))
    if pot.startswith("#") and not kutipan:
        nomor = pot[1:].strip().translate(ANGKA_LATIN)
        if not re.fullmatch(r"\d+", nomor):  # «#» kosong cocok di halaman mana saja
            return Temuan(f"nomor hadits kosong/bukan angka: <<…|{pot}>>")
        # Rekaman dapat melintasi halaman cetak. Kepala pada halaman sesudah p2 bukan bukti di sini;
        # kepala sebelumnya tetap sah untuk lanjutan hadits dalam rekaman yang menyentuh halaman bukti.
        if any(nomor_hadits("\n".join(teks for halaman, teks in norma.per_halaman(r)
                                    if halaman is not None and halaman <= p2), nomor)
               for r in rekaman(sid, juz, p1, p2)):
            return None
        return Temuan(f"{nomor} bukan kepala hadits di {sid} {juz}/{hal}: angka di awal baris («{nomor} - حدثنا», "
                      f"«36 - ({nomor})») yang dihitung, bukan nomor ayat atau catatan; betulkan nomornya, atau pakai "
                      f"potongan lafaz dari halaman itu")
    bagian, celah, pisah = [], [], []  # celah[i] = pemisah (... atau ﴿s:a﴾) di antara bagian i dan i+1
    ujung = [[], []]  # pemisah sebelum bagian pertama dan sesudah bagian terakhir («"قال تعالى: {Q:…}"»)
    angka_lepas = None  # bagian tanpa huruf Arab yang dipisah ... atau ayat dari lafaz («… ٩٩»): tak punya letak di kitab
    for k, x in enumerate(re.split(f"({ELIPSIS.pattern})", pot)):
        if k % 2:
            pisah.append(x)
        elif norma.padat(x):
            if bagian:
                celah.append(pisah)
            else:
                ujung[0] = pisah
            bagian.append(x); pisah = []
        elif re.search(r"\d", x.translate(ANGKA_LATIN)):
            angka_lepas = x.strip()
    ujung[1] = pisah
    if not bagian:
        return Temuan(f"{'kutipan' if kutipan else 'potongan'} tanpa huruf Arab: {pot[:40]}")
    if angka_lepas is not None:
        return Temuan("bagian kutipan yang cuma angka tidak bisa dicek: tulis angka itu bersama lafaz kitab yang menempel "
                      "padanya («رقم (٨٥)», «[الحج:٧٠]»), tanpa ... atau ayat di antaranya (titik milik kitab pun dibuang)",
                      angka_lepas)
    minimal = KUTIPAN_MIN if kutipan else POTONGAN_MIN
    for i, x in enumerate(bagian):
        if len(norma.padat(x)) < minimal:
            if kutipan:
                # bagian pendek yang menempel ayat («{Q:22:70} [الحج:٧٠]»): letaknya dipastikan pemeriksaan celah ayat
                dekat = celah[max(0, i - 1):i + 1]
                if dekat and not any(DIPOTONG.search("".join(c)) for c in dekat):
                    continue
                if DIPOTONG.search(pot):  # «…» milik kitab sendiri yang ikut disalin: kutipan utuhnya bersambung di kitab
                    utuh = DIPOTONG.sub(" ", pot)
                    if not _cek(b, utuh, Catat(), True, False, ""):
                        return _cek(b, utuh, perhatian, True, rinci, pengantar, bersisipan)
                return Temuan(f"bagian kutipan terlalu pendek untuk dicek (paling sedikit {minimal} huruf; jangan dipotong "
                              f"... di situ)", x)
            return Temuan(f"potongan terlalu pendek (paling sedikit {minimal} huruf; yang pendek cocok di sembarang tempat): {pot}")
    for x in bagian:
        e = _cek_bagian(b, x, kutipan, perhatian, rinci)
        if e:
            return e
    rr = rekaman_urut(sid, juz, p1, p2)
    if len(bagian) > 1:
        jarak = [j for j in (berurutan(rr, sisi, bagian) for sisi, _ in norma.BAGIAN) if j is not None]
        if not jarak:
            return Temuan(f"bagian kutipan yang dipisah ... tidak berurutan seperti di kitab {sid} {juz}/{hal}", pot[:40])
    angka = kutipan and re.search(r"\d", AYAT_DI_KUTIPAN.sub(" ", pot).translate(ANGKA_LATIN))
    diperiksa = False  # angka (atau rujukan [سورة: n] yang angkanya dibuang) sudah dicocokkan di tempatnya
    tempat = f"({sid} {juz}/{hal})"
    if kutipan and (angka or re.search(r"[\[\]]", pot) or AYAT_DI_KUTIPAN.search(pot)):
        e, catat, diperiksa = susunan_kitab(rr, bagian, celah, ujung, (p1, p2))
        if e:
            return (Temuan(f"{e.sebab} {tempat}", pot[:40]) if e.teks is None
                    else Temuan(e.sebab, f"{e.teks} {tempat} :: {pot[:40]}"))
        perhatian += [Temuan(f"{p} {tempat}", pot[:40]) for p in catat]
        if diperiksa in ("footnotes", "footnotes?") and not any(t.jenis is Jenis.HASYIAH for t in perhatian[p0:]):
            perhatian.tambah(temuan_hasyiah(b, pot, diperiksa == "footnotes?"))
    # dipotong ...: sambungan yang rapat pun bisa mengubah makna atau pembicaranya; dipisah ayat: diperiksa susunan_kitab
    if len(bagian) > 1 and min(jarak) and DIPOTONG.search(pot):
        kepala = SISIPAN_PERHATIAN[0] if bersisipan else "kutipan dipotong ... atau dipisah ayat"
        perhatian.tambah(Temuan(f"{kepala} ({min(jarak)} huruf kitab dilompati) {sid} {juz}/{hal}: "
                                f"baca yang dilompati, pastikan makna dan pembicaranya tetap", pot[:40],
                                Jenis.SISIPAN_GANTI if bersisipan else Jenis.DILOMPATI))
    if kutipan:
        # naskah menisbatkan kutipan ke pengarang kitab ini («قال البهوتي: "…"»): pembicara di kitab ikut diperiksa.
        # Nama pengarang harus tepat sesudah «قال» (pembicaranya): «نقل الشوكاني عن الزركشي أنه قال:» menisbatkan ke
        # الزركشي, «فقال فيما نقله القرطبي:» ke yang disebut sebelumnya
        nama = norma.padat(shamela.info(sid).get("main_author_name_ar") or "")
        qaul = QAUL.search(pengantar)
        sesudah = (qaul.group().split(maxsplit=1) + [""])[1] if qaul else ""
        pengarang = nama if nama and norma.padat(GELAR.sub("", sesudah)).startswith(nama) else None
        perhatian += [Temuan(f"{p} {tempat}", pot[:40])
                      for p in ragu_kutipan(rr, bagian[0], pot, angka and not diperiksa, lambda: rekaman_dulu(sid, juz, p1, p2),
                                            pengarang)
                      + ragu_akhir(rr, bagian[-1])]
    if not any(t.jenis is Jenis.HASYIAH for t in perhatian[p0:]):  # yang di حاشية sudah disebut kalimat muhaqqiq
        judul = judul_muhaqqiq(sid, rr, norma.padat(bagian[0]), kutipan, dalam=(p1, p2))
        if judul:
            perhatian.tambah(Temuan(f"bukti {sid} {juz}/{hal} ada di bagian «{judul}» (tulisan muhaqqiq/penerbit, bukan "
                                    f"pengarang): jangan dinisbatkan ke pengarang kitab", pot[:40]))
    return None


# judul toc bagian tulisan muhaqqiq/penerbit di depan kitab (dibaca dari toc kitab lokal; judul yang sama untuk isi
# kitab sendiri, mis. «مقدمة» saja atau «ترجمة ابن عباس» di kitab tarajim, sengaja tidak dihitung)
JUDUL_MUHAQQIQ = re.compile(
    r"^(?:مقدمة|كلمة)\s+(?:ال)?(?:طبعة|تحقيق|محقق|مصحح|ناشر|مشرف|لجنة)"
    r"|^كلمة\s*:?\s*معالي|^تقديم(?:\s+بقلم|$)|^(?:ال)?إهداء$"
    r"|^ترجمة\s+(?:موجزة\s+|مختصرة\s+)?(?:لل|ال)(?:مؤلف|مصنف|شارح|ناظم|محقق)|^ترجمة\s+صاحب|حياة\s+(?:ال)?مؤلف"
    r"|^(?:ال)?تعريف\s+ب(?:ال)?(?:مؤلف|مصنف|شارح|كتاب)|^منهج\s+(?:ال)?(?:مؤلف|مصنف)\s+في"
    r"|^منهج\s+(?:ال)?تحقيق|^منهجي\s+في|^عملي\s+في|^وصف\s+(?:ال)?(?:نسخ|مخطوط)|^دراسة\s+(?:موجزة|الكتاب|الرسالة|المؤلف)")


def judul_muhaqqiq(sid, rr, q, utuh, dalam=None):
    """Judul (atau induknya) tulisan muhaqqiq/penerbit yang menaungi awal q (`padat`) di matan rr; '' kalau bukan."""
    for r in rr:
        for c in cocok.semua_letak(r, q, "body", utuh):
            if dalam is not None:
                h = cocok.halaman_letak(r, "body", c)
                if not (dalam[0] <= (h[0] or 0) and (h[1] or 0) <= dalam[1]):
                    continue
            return next((j for j in shamela.rantai_judul(sid, shamela.judul_naung(sid, r, c)) if JUDUL_MUHAQQIQ.search(j)), "")
    return ""


def susunan_kitab(rr, bagian, celah, ujung, dalam):
    """Yang tidak terbaca pencocokan huruf `padat`, diperiksa di teks asli kitab (matan, lalu حاشية) tempat bagian-bagian
    kutipan berada: celah {Q:} harus memang ayat (bertanda ﴿﴾; nomornya sama kalau kitab menulis [سورة: n]), dan angka
    tiap bagian harus sama dengan angka kitab di tempatnya. Calon susunan hanya dari halaman bukti (`dalam`),
    dengan batas kata yang sama seperti pemeriksaan huruf. Kembalikan (galat: Temuan atau None, perhatian, bagian kitab
    yang cocok)."""
    q = [norma.padat(b) for b in bagian]
    kata = [cocok.kata_dalam(b) for b in bagian]
    terbaik = None
    for sisi, _ in norma.BAGIAN:
        raw = norma.TAGS.sub(lambda m: " " * len(m.group()), "\n".join(r.get(sisi) or "" for r in rr))
        # Raw utuh diperlukan untuk ayat tepat sebelum/sesudah halaman bukti. Yang dibatasi hanya posisi calon.
        sah, tak_pasti, catatan, offset = [], [], [], 0  # catatan = حاشية yang tertulis di body (`cocok.catatan_body`)
        for r in rr:
            t = r.get(sisi) or ""
            if sisi == "body":
                catatan += [(offset + a, offset + z) for a, z in cocok.catatan_body(t)]
            batas = [(0, r.get("page_num"))] + [(m.start(), int(m[1])) for m in norma.PENANDA.finditer(t)]
            samar = sisi == "footnotes" and len(batas) == 1
            for i, (a, h) in enumerate(batas):
                z = batas[i + 1][0] if i + 1 < len(batas) else len(t) + 1  # termasuk pemisah antarrekaman
                a, z = offset + a, min(offset + z, len(raw))
                if samar or h is not None and dalam[0] <= h <= dalam[1]:
                    if sah and sah[-1][1] == a:
                        sah[-1] = sah[-1][0], z
                    else:
                        sah.append((a, z))
                    if samar and r.get("page_num") != norma.per_halaman(r)[-1][0]:
                        tak_pasti.append((a, z))
            offset += len(t) + 1
        pd, panjang = norma.padat(raw), {}
        if q[0] not in pd:
            continue
        rek = {"body": raw}
        angka = angka_kitab(raw)

        def sesudah(k):  # letak di raw tepat sesudah huruf `padat` ke-k
            lo, hi = 0, len(raw)
            while lo < hi:
                mid = (lo + hi) // 2
                if mid not in panjang:
                    panjang[mid] = len(norma.padat(raw[:mid]))
                lo, hi = (lo, mid) if panjang[mid] > k else (mid + 1, hi)
            return lo
        mulai = lambda k: sesudah(k) - 1 if k < len(pd) else len(raw)  # letak huruf ke-k
        akhir = lambda k: sesudah(k - 1) if k > 0 else 0  # sesudah huruf terakhir sebelum huruf ke-k
        def di_halaman(a, z):
            n = bisect.bisect_right(sah, (a, float("inf"))) - 1
            return n >= 0 and sah[n][0] <= a and z <= sah[n][1]

        def lolos(i, j, k):
            return (len(q[i]) < KUTIPAN_MIN or cocok.potongan_utuh(rek, "body", j, k, kata[i])) and di_halaman(mulai(j), akhir(k))

        for letak in susunan_bagian(pd, q, lolos=lolos):
            hasil = _nilai_susunan(raw, angka, letak, bagian, celah, ujung, mulai, akhir, di_halaman)
            kunci = (bool(hasil[0]), len(hasil[1]))
            jenis = ("footnotes?" if any(a <= mulai(j) < z for a, z in tak_pasti for j, _ in letak) else
                     "footnotes" if any(a < akhir(k) and mulai(j) < z for a, z in catatan for j, k in letak) else sisi)
            if terbaik is None or kunci < terbaik[0]:
                terbaik = kunci, hasil, jenis
            if kunci == (False, 0):
                return None, [], jenis
    return (*terbaik[1], terbaik[2]) if terbaik else (
        Temuan("susunan kutipan berangka atau berayat tidak ditemukan di halaman bukti dengan kata utuh"), [], False)


def _nomor_lain(spec, rujukan):
    """Nomor ayat di rujukan kitab [سورة: n] (rentang «[ق:٢٣- ٢٩]» = 23 s.d. 29) dan nomor {Q:spec} tidak beririsan."""
    nomor, mau = set(), set()
    for x in rujukan:
        for a, b in re.findall(r"(\d+)(?:\s*[-–]\s*(\d+))?", x.translate(ANGKA_LATIN)):
            nomor |= set(range(int(a), int(b or a) + 1)) if int(b or a) - int(a) <= 300 else {int(a), int(b)}
    for s in spec:
        x, _, y = s.split(":")[1].partition("-")
        mau |= set(range(int(x), int(y or x) + 1))
    return bool(mau and nomor and not mau & nomor)


NOMOR_KITAB_LAIN = ("rujukan kitab menulis nomor lain ({1}), tetapi teks ayat di kitab memang termuat utuh di {{Q:{0}}}: "
                    "pastikan nomornya ke mushaf")


def _ayat_lain(spec, rujukan, ayat_kitab, teks, catat):
    """Temuan kalau ayat yang dikutip kitab di tempat {Q:spec} bukan ayat itu: nomor di rujukan kitab [سورة: n] lain
    (kecuali teks ayat kitab memang termuat di {Q:}: perhatian ke `catat`), atau suratnya lain. ayat_kitab = tiap ayat
    bertanda di kitab di tempat itu (dengan tandanya), teks = teks kitab yang dibandingkan (`ayat_sama`)."""
    if _nomor_lain(spec, rujukan):
        if not any(ayat_persis(spec, a[1:-1]) for a in ayat_kitab):
            return Temuan(f"ayat yang dikutip kitab di tempat {{Q:{spec[0]}}} adalah {'، '.join(rujukan)}: "
                          "salin ayat yang benar")
        catat.append(NOMOR_KITAB_LAIN.format(spec[0], '، '.join(rujukan)))
    sama = ayat_sama(spec, teks, rujukan)
    if not sama:
        return Temuan(f"ayat yang dikutip kitab di tempat {{Q:{spec[0]}}} adalah surat lain "
                      f"({'، '.join(rujukan) or ayat_kitab[0][:40]}): salin ayat yang benar")
    if isinstance(sama, str):
        catat.append(sama)
    return None


def _nilai_susunan(raw, angka, letak, bagian, celah, ujung, mulai, akhir, di_halaman):
    """(galat: Temuan atau None, perhatian) satu susunan letak bagian kutipan di teks asli kitab raw (lihat
    susunan_kitab)."""
    catat, sisa_celah = [], {}
    for i, c in enumerate(celah):
        dipotong = DIPOTONG.search("".join(c))
        spec = [x[1:-1] for x in c if x.startswith("﴿") and len(x) > 2]
        if dipotong and not spec:
            continue
        a, z = akhir(letak[i][1]), mulai(letak[i + 1][0])
        antara = raw[a:z]
        rujukan = [m.group() for m in RUJUKAN_AYAT.finditer(raw, a, min(len(raw), z + 40)) if m.start() < z]
        if not AYAT_KITAB.search(antara) and not rujukan:
            if any(mirip_ayat(s, antara) for s in spec):  # ayat tanpa tanda ﴿﴾ di kitab
                if len(norma.padat(antara)) > JARAK_AYAT and not dipotong:
                    catat.append(f"kutipan dipisah ayat ({len(norma.padat(antara))} huruf kitab dilompati): "
                                 "baca yang dilompati, pastikan makna dan pembicaranya tetap")
                continue
            dilompati = re.sub(r"\s+", " ", norma.HARAKAT.sub("", antara)).strip()
            return Temuan(
                f"di kitab tidak ada ayat di tempat {{Q:}} (sesudah «…{' '.join(bagian[i].split()[-3:])}»), yang ada "
                f"di kitab: «{dilompati[:40] or 'tidak ada apa-apa'}». {{Q:}} di dalam kutipan hanya untuk ayat yang memang "
                "dikutip kitab di situ"), catat
        if spec:
            e = _ayat_lain(spec, rujukan, [m.group() for m in AYAT_KITAB.finditer(antara)], antara, catat)
            if e:
                return e, catat
        bertanda = " ".join(m.group()[1:-1] for m in AYAT_KITAB.finditer(antara))
        if spec and bertanda:  # ayat kitab tanpa tanda ﴿﴾ tidak bisa dipastikan batasnya
            e, p = pesan_tercetak(ayat_tercetak(spec, bertanda, antara), spec, bertanda)
            if e:
                return Temuan(e), catat
            if p and not dipotong:  # yang dilompati sudah jadi perhatian «dipotong ...»
                catat.append(p)
        if dipotong:  # yang dilompati sudah jadi perhatian «dipotong ...»
            continue
        sisa_celah[i] = len(norma.padat(RUJUKAN_AYAT.sub(" ", AYAT_KITAB.sub(" ", antara))))
        if sisa_celah[i] > SISA_AYAT:
            catat.append(f"selain ayat, {sisa_celah[i]} huruf kitab dilompati di tempat {{Q:}}: baca yang dilompati, "
                         "pastikan makna dan pembicaranya tetap")
    # {Q:} di awal/akhir kutipan: kalau kitab menulis ayat tepat di sebelahnya, ayat itu harus ayat yang sama
    for spec, sisi in ((ujung[0], 0), (ujung[1], 1)):
        spec = [x[1:-1] for x in spec if x.startswith("﴿") and len(x) > 2]
        if not spec:
            continue
        # jendela 400 huruf hanya untuk tanda pembuka/penutup ayat; ayatnya dibaca utuh walau panjang
        if sisi:
            z = akhir(letak[-1][1]); buka = re.compile(r"[﴿{]").search(raw, z, z + 400)
            ayat_ = buka and AYAT_KITAB.match(raw, buka.start())
            dekat = ayat_ and raw[z:ayat_.start()]
        else:
            a = mulai(letak[0][0]); tutup = max(raw.rfind("﴾", max(0, a - 400), a), raw.rfind("}", max(0, a - 400), a))
            buka = raw.rfind("﴿" if raw[tutup] == "﴾" else "{", 0, tutup) if tutup >= 0 else -1
            ayat_ = AYAT_KITAB.match(raw, buka) if buka >= 0 else None
            ayat_ = ayat_ if ayat_ and ayat_.end() == tutup + 1 else None
            dekat = ayat_ and RUJUKAN_AYAT.sub(" ", raw[ayat_.end():a])
        if not ayat_ or len(norma.padat(dekat)) > SISA_AYAT:
            continue
        rujukan = [m.group() for m in RUJUKAN_AYAT.finditer(raw, ayat_.end(), min(len(raw), ayat_.end() + 40))
                   if not norma.padat(raw[ayat_.end():m.start()])]
        e = _ayat_lain(spec, rujukan, [ayat_.group()], ayat_.group(), catat)
        if e:
            return e, catat
        e, p = pesan_tercetak(ayat_tercetak(spec, ayat_.group()[1:-1]), spec, ayat_.group()[1:-1])
        if e:
            return Temuan(e), catat
        if p:
            catat.append(p)
    for i, ((j, k), b) in enumerate(zip(letak, bagian)):
        # bagian pendek di samping {Q:} (lihat cek): harus kata utuh di kitab, tepat menempel ayatnya
        if len(norma.padat(b)) < KUTIPAN_MIN:
            a, z = mulai(j), akhir(k)
            putus = (re.search(rf"[ء-ي]{norma.HARAKAT.pattern}*$", raw[:a])
                     and not re.search(rf"(?<![ء-ي])[وف]{norma.HARAKAT.pattern}*$", raw[:a])  # «و» / «ف» sambung boleh
                     or re.match(rf"{norma.HARAKAT.pattern}*[ء-ي]", raw[z:]))
            if putus or any(sisa_celah.get(x, 0) > SISA_AYAT for x in (i - 1, i)):
                return Temuan(f"bagian kutipan terlalu pendek untuk dicek (paling sedikit {KUTIPAN_MIN} huruf), dan di "
                              "kitab ia tidak menempel ayatnya sebagai kata utuh", b.strip()), catat
        # angka/rujukan di ujung bagian ikut dicocokkan: teks kitab sampai huruf terdekat, tidak melewati baris baru
        # atau kurung yang menutup ujung itu
        a, z = mulai(j), akhir(k)
        kepala, ekor = re.match(r"[^ء-ي]*", b).group(), re.search(r"[^ء-ي]*$", b).group()
        lebih = 0  # angka kitab di depan kutipan yang tidak ikut disalin («١٩/ ٤٧ - وعن» dikutip «47 - وعن»)
        if re.search(r"[\d٠-٩۰-۹\[(]", kepala):
            luar = re.split(r"[\r\n]", raw[akhir(j):a])[-1]
            buka = max(luar.rfind(x) for x in "[(") if kepala.lstrip()[:1] in ("[", "(") else -1
            a -= len(luar) - max(buka, 0)
            if buka < 0:
                lebih = max(0, len(re.findall(r"\d+", angka[a:a + len(luar)])) - len(re.findall(r"\d+", kepala.translate(ANGKA_LATIN))))
        if re.search(r"[\d٠-٩۰-۹\])]", ekor):
            luar = re.split(r"[\r\n]", raw[z:mulai(k)])[0]
            # «…خالتها)**.» ditutup kurung walau sesudahnya ada titik/** : angka catatan kaki kitab «(١)» sesudah
            # kurung itu bukan bagian kutipan
            tutup = [luar.find(x) for x in "])" if x in luar] if re.sub(r"[\s.,،؛:*]+$", "", ekor)[-1:] in ("]", ")") else []
            z += min(tutup) + 1 if tutup else len(luar)
        naskah = re.findall(r"\d+", b.translate(ANGKA_LATIN))
        nomor = list(re.finditer(r"\d+", angka[a:z]))[lebih:]
        if naskah and any(not di_halaman(a + m.start(), a + m.end()) for m in nomor):
            return Temuan("angka di kutipan berada di luar halaman bukti: perluas rentang bukti atau salin angka dari "
                          "halaman yang dirujuk"), catat
        di_kitab = [m.group() for m in nomor]
        if naskah != di_kitab:
            beda = (f"angka di kutipan ({' '.join(naskah) or 'tidak ada'}) beda dengan angka kitab di tempat itu "
                    f"({' '.join(di_kitab) or 'tidak ada'})")
            if len(naskah) == len(di_kitab):
                return Temuan(f"{beda}: salin angkanya dari kitab"), catat
            catat.append(f"{beda}: salin angkanya dari kitab")
    return None, catat


def berurutan(rr, sisi, bagian):
    """Kalau bagian-bagian kutipan muncul berurutan di sisi (matan/حاشية) rekaman rr: jarak terbesar di antaranya
    (huruf `padat`), dengan susunan yang paling rapat. None kalau tidak berurutan."""
    teks = "".join(norma.ruas_halaman(r, sisi)[0] for r in rr)
    bagian = [norma.padat(b) for b in bagian]
    terbaik = None
    for letak in susunan_bagian(teks, bagian):
        jarak = max((b[0] - a[1] for a, b in zip(letak, letak[1:])), default=0)
        terbaik = jarak if terbaik is None else min(terbaik, jarak)
    return terbaik


def angka_kitab(t):
    """Teks kitab dengan angka 0-9 yang memang bagian kalimat: penanda halaman ⦗n⦘, nomor catatan kaki yang menempel
    kata («الجدال١») atau bertanda «(¬n)», dan angka di dalam tag HTML dibuang; «(٨٥)» (nomor hadits) tetap."""
    kosong = lambda m: " " * len(m.group())  # panjang teks tetap: letak angkanya sama dengan di teks asli
    t = norma.PENANDA.sub(kosong, norma.TAGS.sub(kosong, t))
    # «و٢٦٧» (و kata sambung yang berdiri sendiri) bukan nomor catatan kaki
    t = re.sub(r"(?<=[ء-ي])(?<!(?<![ء-ي])و)[٠-٩۰-۹]+|\(¬\s*[٠-٩۰-۹0-9]+\s*\)|^\s*\([٠-٩۰-۹0-9]+\)", kosong, t, flags=re.M)
    return t.translate(ANGKA_LATIN)


def henti(r, n):
    """Teks asli matan rekaman r memuat tanda akhir kalimat (HENTI) tepat di letak `padat` n, yaitu sesudah kata yang
    berakhir di n. Kata nafi yang menutup kalimat sebelumnya («أو لا.»، «وإلا فلا، ولعله») tidak menafikan kutipan."""
    _teks, ruas = norma.ruas_halaman(r, "body")
    for (a, b, _, _), (_, asli) in zip(ruas, norma.per_halaman(r, "body")):
        if a <= n <= b:
            for m in HENTI.finditer(asli):
                d = a + len(norma.padat(asli[:m.start()]))
                if d == n:
                    return True
                if d > n:
                    break
    return False


def ragu_akhir(rr, akhir):
    """Kutipan yang menafikan («لا إله», «ليس من») tetapi berhenti tepat sebelum «إلا» di kitab: pengecualiannya terpotong,
    jadi maknanya bisa terbalik («أشهد أن لا إله» dari «أن لا إله إلا الله»)."""
    if not any(norma.padat(w) in NAFI for w in akhir.split()[-5:]):  # nafi jauh sebelum ujung: «إلا»-nya milik kalimat lain
        return []
    q = norma.padat(akhir)
    for r in rr:
        c = cocok.letak_pertama(r, q, "body", True)
        if c:
            teks, (_, ujung) = norma.ruas_halaman(r, "body")[0], cocok.batas_kata(r, "body")
            sesudah = teks[c[1]:min((u for u in ujung if u > c[1]), default=c[1])]
            if sesudah == "الا" and not henti(r, c[1]):
                return ["di kitab kutipan ini disambung «إلا» (pengecualiannya terpotong): pastikan maknanya tidak terbalik"]
            return []
    return []


def ragu_kutipan(rr, awal, pot, periksa_angka, dulu, pengarang):
    """Yang tidak diperiksa pencocokan huruf: angka di kutipan (kalau belum dicocokkan di tempatnya oleh susunan_kitab),
    dan kata nafi tepat sebelum kutipan di matan kitab, juga di akhir halaman sebelumnya (dulu() = rekaman sebelum rr).
    pengarang (nama `padat`): naskah menisbatkan kutipan ke pengarang kitab; kalau di kitab kutipan itu diantar
    «قال الشافعي» (orang lain), pembicaranya diragukan."""
    ragu = []
    angka = set(re.findall(r"\d+", AYAT_DI_KUTIPAN.sub(" ", pot).translate(ANGKA_LATIN)))
    if angka and periksa_angka:
        ada = set()
        for r in rr:
            ada |= set(re.findall(r"\d+", angka_kitab(r.get("body") or "") + " " + angka_kitab(r.get("footnotes") or "")))
        if angka - ada:
            ragu.append(f"angka {'، '.join(sorted(angka - ada))} di kutipan tidak terbaca di halaman itu: cocokkan sendiri")
    q = norma.padat(awal)
    def letak(r):  # awal kutipan di rekaman r; kutipan yang menyambung ke rekaman berikutnya: ujung rekaman = awalnya
        c = cocok.letak_pertama(r, q, "body", True)
        if c or k_utuh:
            return c
        teks = norma.ruas_halaman(r, "body")[0]
        n = next((n for n in range(min(len(q), len(teks)) - 1, 9, -1) if teks.endswith(q[:n])), 0)
        return n and len(teks) - n in cocok.batas_kata(r, "body")[0] and (len(teks) - n, len(teks))
    k_utuh = any(cocok.letak_pertama(r, q, "body", True) for r in rr)
    for k, r in enumerate(rr):
        c = letak(r)
        if c:
            teks, mulai = norma.ruas_halaman(r, "body")[0], sorted(cocok.batas_kata(r, "body")[0])
            sebelum = [a for a in mulai if a <= c[0]]  # awal kata kutipan (huruf sambung و/ف ikut kata itu)
            kata = teks[sebelum[-2]:sebelum[-1]] if len(sebelum) > 1 else None
            lalu = None if kata else rr[k - 1] if k else dulu()
            if lalu:  # kutipan mulai di awal rekaman: kata terakhir rekaman sebelumnya
                awal_lalu = cocok.batas_kata(lalu, "body")[0]
                kata = norma.ruas_halaman(lalu, "body")[0][max(awal_lalu):] if awal_lalu else None
            if kata in NAFI and not henti(lalu or r, len(norma.ruas_halaman(lalu, "body")[0]) if lalu else sebelum[-1]):
                ragu.append(f"di kitab tepat sebelum kutipan ada «{kata}»: pastikan maknanya tidak terbalik")
            if pengarang:
                n = len(sebelum) - 1  # kata kitab sebelum kutipan di rekaman ini
                kata = _kata_titik(r)[:n][-PENGANTAR_KATA:]
                lalu = (rr[k - 1] if k else dulu()) if len(kata) < PENGANTAR_KATA else None
                if lalu:  # pengantar di akhir halaman sebelumnya
                    kata = (_kata_titik(lalu) + kata)[-PENGANTAR_KATA:]
                lain = penutur_lain(kata, pengarang)
                if lain:
                    ragu.append(f"di kitab kalimat ini diantar «{lain}:», bukan ucapan pengarang: pastikan pembicaranya")
            break
    return ragu


GELAR = re.compile(r"^(?:(?:الإمام|الشيخ|العلامة|الحافظ|القاضي)\s+)+")  # «قال الإمام البهوتي:» -> البهوتي
PENGANTAR_KATA = 6 # kata kitab tepat sebelum kutipan yang dibaca untuk mencari pengantar ucapan «قال الشافعي:»
PENGANTAR = frozenset(map(norma.padat, "قال وقال فقال قاله وقاله ونقل نقل وعن عن".split()))
# kata sesudah pengantar yang bukan nama orang lain: doa («رحمه الله تعالى»), «قال في المغني» (-> المغني), dan
# sebutan pengarang sendiri («قال المصنف رحمه الله:» di kitabnya sendiri; «قلت:»)
BUKAN_NAMA = frozenset(map(norma.padat, "رحمه رحمهم رحمهما الله تعالى رضي عنه عنها عنهما عنهم في".split()))
SEBUTAN_PENGARANG = frozenset(map(norma.padat, "المصنف المؤلف الشيخ قلت".split()))


def _kata_titik(r):
    """`cocok.kata_titik_dua` matan r, atau [] kalau pemotongan katanya tidak sama dengan `cocok.batas_kata`."""
    teks, mulai = norma.ruas_halaman(r, "body")[0], sorted(cocok.batas_kata(r, "body")[0])
    kata = cocok.kata_titik_dua(r)
    return kata if [w for w, _ in kata] == [teks[a:b] for a, b in zip(mulai, mulai[1:] + [len(teks)])] else []


def penutur_lain(kata, pengarang):
    """Pengantar ucapan orang lain tepat sebelum kutipan di kitab: kata-kata [(`padat`, diikuti «:»)] yang diakhiri
    «قال/نقل/عن <nama>:» (paling banyak PENGANTAR_KATA kata) -> «قال الشافعي»; '' kalau tidak ada, tanpa nama, atau
    namanya pengarang kitab sendiri (pengarang = namanya, `padat`)."""
    if not kata or not kata[-1][1]:  # pengantar ucapan berakhir dengan «:» tepat sebelum kutipan
        return ""
    w = [x for x, _ in kata]
    i = next((i for i in range(len(w) - 2, -1, -1) if w[i] in PENGANTAR), None)
    nama = [x for x in w[i + 1:] if x not in BUKAN_NAMA] if i is not None else []
    if not nama or any(x in SEBUTAN_PENGARANG for x in nama) or pengarang in "".join(nama):
        return ""
    return " ".join(w[i:])
