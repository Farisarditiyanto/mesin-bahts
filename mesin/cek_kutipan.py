# SPDX-License-Identifier: AGPL-3.0-or-later
"""Inti `cek`: kutipan (atau potongan bukti) harus terbaca di juz/halaman kitab yang dirujuk. Juga perhatian
soal kutipan itu: حاشية المحقق, pembicara lain, kata nafi, angka, sisipan [ ], dan bukti PDF <<luar|berkas|hal>>."""
import bisect, re
from pathlib import Path

import norma
import shamela
import sumber_pdf
from cek_ayat import ayat_persis, ayat_sama, ayat_tercetak, mirip_ayat, pesan_tercetak
from cek_hadits import nomor_hadits
from dasar import (
    ANGKA_LATIN, AYAT_DI_KUTIPAN, AYAT_KITAB, DIPOTONG, ELIPSIS, KUTIPAN_MIN, LUAR, POTONGAN_MIN, QAUL,
    RUJUKAN_AYAT, TIDAK_KETEMU)
from jejak import rangkaian_kitab, susunan_bagian, tempat_kitab
from kitab_lokal import (
    cari_di, gabung, halaman_janggal, kitab, rekaman, rekaman_dulu, rentang_halaman, salah_halaman, salah_juz,
    urut_juz)

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


def cek_pdf(folder, berkas, hal, kutipan, galat, perhatian, fn):
    """Bukti <<luar|berkas|hal>>: kutipan dicari di teks PDF folder/berkas. Hanya penunjuk halaman, tidak pernah
    lolos: tiap bukti PDF menambah satu galat (berkas/halaman salah) atau satu perhatian (cocokkan sendiri)."""
    tanda = f"<<{LUAR}|{berkas}|{hal}>>"
    folder = Path(folder).resolve()
    p = (folder / berkas).resolve()
    if not p.is_relative_to(folder):
        galat.append(f"{tanda}: PDF bukti harus di dalam folder bahts {folder.name} (tulis nama berkasnya saja)  || fn: {fn}")
        return
    if not p.is_file():
        galat.append(f"{tanda}: berkas «{berkas}» tidak ada di folder bahts {folder.name}; simpan PDF-nya di sana "
                     f"(mis. {shamela.perintah('dirasat-pdf <W…> ' + folder.name)})  || fn: {fn}")
        return
    bagian = [b for b in ELIPSIS.split(kutipan or "") if norma.padat(b)]
    if pendek := next((b for b in bagian if len(norma.padat(b)) < KUTIPAN_MIN), None):
        galat.append(f"bagian kutipan terlalu pendek untuk dicek (paling sedikit {KUTIPAN_MIN} huruf; jangan dipotong "
                     f"... di situ) :: {pendek.strip()[:30]}  || fn: {fn}")
        return
    a, z = rentang_halaman(hal)
    if not 1 <= a <= z:
        galat.append(f"{tanda}: hal = urutan halaman di berkas PDF, mulai 1; rentang ditulis kecil-besar (mis. 3-4)  || fn: {fn}")
        return
    try:
        isi = sumber_pdf.halaman(p)
    except Exception as e:  # pypdf: PDF rusak, bersandi, atau bentuk yang tidak dikenalnya
        perhatian.append(f"PDF «{berkas}» tidak bisa dibaca mesin ({type(e).__name__}): cocokkan sendiri lafaz dan "
                         f"halamannya  || fn: {fn}")
        return
    if z > len(isi):
        galat.append(f"{tanda}: PDF itu hanya {len(isi)} halaman (hal = urutan halaman di berkas, mulai 1)  || fn: {fn}")
        return
    if kutipan is None:  # nukilan makna: berkas dan halaman tetap dicek, isi diperiksa orang
        perhatian.append(f"nukilan tanpa tanda petik dari PDF ({berkas}): mesin tidak mengecek isinya; pastikan sendiri "
                         f"maknanya ada di halaman itu  || fn: {fn}")
        return
    ketemu = sumber_pdf.cari(isi, bagian)
    if any(a <= n <= z for n in ketemu):
        perhatian.append(f"kutipan «{kutipan[:30]}» ditemukan di halaman {hal} «{berkas}» (penunjuk, bukan bukti: teks PDF "
                         f"tidak dibaca persis; angka, urutan kata, dan huruf seperti العلم/العمل tidak dibedakan): buka "
                         f"halaman itu dan cocokkan sendiri lafaznya  || fn: {fn}")
    elif ketemu:
        galat.append(f"kutipan «{kutipan[:30]}» tidak ada di halaman berkas {hal} «{berkas}», tetapi ada di halaman "
                     f"{'، '.join(map(str, ketemu[:5]))}  || fn: {fn}")
    elif all(sumber_pdf.tanpa_teks(isi, n) for n in range(a, z + 1)):
        perhatian.append(f"halaman {hal} «{berkas}» berupa gambar (scan), teksnya tidak terbaca mesin: cocokkan sendiri "
                         f"lafaz kutipan «{kutipan[:30]}»  || fn: {fn}")
    else:
        perhatian.append(f"kutipan «{kutipan[:30]}» tidak ada di teks PDF «{berkas}»: lafaznya berbeda atau karangan, atau "
                         f"teks PDF-nya rusak; buka PDF-nya dan cocokkan sendiri lafaz dan halamannya  || fn: {fn}")


def _petunjuk(sid, juz, q):
    """Tempat q di seluruh kitab untuk pesan kesalahan: matan dulu (juz yang ditulis didahulukan), baru حاشية."""
    tempat, hasyiah = [], None
    padat_, ix = shamela._cache(sid), shamela.indeks(sid)
    kena = set(padat_.kena(q))  # rekaman lain tidak memuat q: tidak menambah apa pun
    # urutan rekaman(sid, "-"): per juz (urut kemunculan pertamanya), lalu urut berkas
    for r in (padat_.isi({"part": ix[i][0]}, i) for ii in kitab(sid).values() for i in ii if i in kena):
        h = shamela.tempat(r, q)
        if h:
            t = (shamela._juz(r) != juz, shamela.letak(shamela._juz(r), h))
            if t not in tempat:
                tempat.append(t)
        elif not hasyiah:
            h = shamela.tempat(r, q, "footnotes")
            if h:
                hasyiah = shamela.letak(shamela._juz(r), h) + " [حاشية]"
    if tempat:
        tempat = [t for _, t in sorted(tempat, key=lambda t: t[0])]
        lagi = f" (dan {len(tempat) - 3} tempat lain)" if len(tempat) > 3 else ""
        return "، ".join(tempat[:3]) + lagi
    if hasyiah:
        return hasyiah
    t = tempat_kitab(rangkaian_kitab(sid), [norma.bait(q)])  # kutipan yang menyambung ke halaman berikutnya
    return shamela.letak(t[0], t[1]) + t[2] if t else None


def pesan_hasyiah(sid, juz, hal, teks, samar=False):
    if samar:
        return (f"bukti ada di حاشية المحقق {sid} {juz}/{hal}, tetapi halaman tiap catatan di rekaman ini tidak tercatat: "
                f"pastikan halamannya dengan `halaman`; itu kalimat muhaqqiq, bukan pengarang :: {teks[:40]}")
    return (f"bukti ada di حاشية المحقق, bukan di matan kitab {sid} {juz}/{hal}: "
            f"itu kalimat muhaqqiq, bukan pengarang :: {teks[:40]}")


def _cek_bagian(sid, juz, hal, p1, p2, teks, utuh, perhatian, rinci=True):
    """Cek satu teks (kutipan, satu bagian kutipan berelipsis, atau potongan) di juz/hal; '' kalau cocok.
    rinci=False: pesan kesalahannya tidak disusun (mencari di seluruh kitab), untuk pemanggil yang hanya butuh cocok/tidak."""
    q = norma.padat(teks)
    jenis, lain = cari_di(sid, juz, p1, p2, q, utuh, shamela.kata_dalam(teks))
    if jenis in ("hasyiah", "hasyiah?"):
        perhatian.append(pesan_hasyiah(sid, juz, hal, teks, jenis == "hasyiah?"))
    if jenis:
        return ""
    if not rinci:
        return "tidak cocok"
    if utuh and cari_di(sid, juz, p1, p2, q, False)[0]:
        if cari_di(sid, juz, p1, p2, q, True)[0]:  # ujungnya utuh, yang bergeser batas kata di dalamnya
            return (f"pembagian kata kutipan beda dengan kitab {sid} {juz}/{hal} (mis. «بل أشك» ≠ «بلا شك»): salin spasinya "
                    f"seperti di kitab, lihat `teks {sid} \"…\"` :: {teks[:40]}")
        return (f"kutipan mulai atau berakhir di tengah kata (kitab {sid} {juz}/{hal}): salin kata pertama dan terakhirnya utuh, "
                f"lihat `teks {sid} \"…\"` :: {teks[:40]}")
    if lain:
        return f"teks ada tapi di {shamela.letak(juz, lain[:2])}{lain[2]}, bukan {hal} ({sid}) :: {teks[:40]}"
    ada = _petunjuk(sid, juz, q)
    if ada:
        return f"teks TIDAK di {juz}/{hal}; ketemu di {ada} ({sid}) :: {teks[:40]}"
    beda = _menyimpang(sid, juz, p1, p2, teks)
    if beda:
        return f"teks berbeda dengan kitab {sid} {juz}/{hal}: {beda} :: {teks[:40]}"
    return TIDAK_KETEMU.format(sid) + f" :: {teks[:60]}"


def _menyimpang(sid, juz, p1, p2, teks):
    """Kata pertama kutipan yang berbeda dengan matan halaman itu: awalan terpanjang kutipan yang ada di matan,
    lalu kata sesudahnya di naskah dan di kitab. '' kalau awalannya terlalu pendek untuk ditunjuk."""
    if not rekaman(sid, juz, p1, p2):
        return ""
    raw = re.sub(r"\s+", " ", norma.HARAKAT.sub("", norma.TAGS.sub("", " ".join(g["body"] for g in gabung(sid, juz, p1, p2)))))
    raw = norma.PENANDA.sub(" ", raw)
    kitab_padat, kata = norma.padat(raw), teks.split()
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


def cek(sid, juz, hal, pot, perhatian, kutipan=False, rinci=True, pengantar="", sisipan=True):
    """Kembalikan '' kalau pot ada di kitab sid juz/hal, atau pesan kesalahan.
    kutipan=True: pot = kutipan bertanda petik di naskah. Ia harus mulai dan berakhir di batas kata kitab, boleh dipotong
    dengan ... (tiap bagian dicek, harus berurutan); angka dan kata nafi sebelumnya diperiksa sebagai perhatian.
    Kurung siku yang tidak ada di kitab = SISIPAN peneliti: dibaca seperti pemisah ..., jadi yang di luarnya tetap dicek.
    Yang lolos tetapi harus dilihat orang (bukti di حاشية, nomor halaman bukan cetakan) ditambahkan ke `perhatian`.
    pengantar = teks naskah tepat sebelum kutipan («قال البهوتي:»), untuk memeriksa pembicaranya di kitab."""
    if kutipan and sisipan and SISIPAN.search(pot):
        coba = []
        if not cek(sid, juz, hal, pot, coba, kutipan, rinci, pengantar, sisipan=False):
            perhatian += coba  # kurung siku itu milik kitab
            return ""
        p_awal = len(perhatian)
        e = cek(sid, juz, hal, SISIPAN.sub(" … ", pot), perhatian, kutipan, rinci, pengantar, sisipan=False)
        # «[صوابه]» menggantikan kata kitab: yang dilompati harus dibaca, tetapi namanya sisipan, bukan potongan ...
        ganti = "kutipan bersisipan [ ] yang menggantikan teks kitab"
        perhatian[p_awal:] = [p.replace("kutipan dipotong ... atau dipisah ayat", ganti, 1) for p in perhatian[p_awal:]]
        lain = [m.group() for m in SISIPAN.finditer(pot) if not HAKADHA.fullmatch(m.group())]
        if not e and lain and not any(p.startswith(ganti) for p in perhatian[p_awal:]):
            perhatian.append(f"kutipan memuat tambahan penulis {'، '.join(lain)[:40]} yang tidak ada di kitab {sid} {juz}/{hal}: "
                             f"kurung siku di dalam kutipan hanya untuk membetulkan salah atau «[هكذا]» (أبو سليمان، كتابة "
                             f"البحث العلمي، ص112-113)؛ penjelasan pindahkan ke luar kutipan atau ke catatan kaki :: {pot[:40]}")
        return e
    p0 = len(perhatian)
    e = salah_juz(sid, juz, hal)
    if e:
        return e
    if juz == "-" and None not in kitab(sid) and len(kitab(sid)) > 1:
        # kitab yang bagiannya hanya bernama (المقدمة tulisan muhaqqiq + الكتاب): «-» digabung, jadi halaman yang ada di
        # dua bagian dibaca di bagian tempat teksnya cocok. Cocok di satu bagian -> bagian itu (المقدمة -> perhatian
        # muhaqqiq lewat toc); cocok di dua bagian -> tidak tentu yang mana.
        a, _, z = hal.partition("-")
        di = sorted(shamela.bagian_halaman(sid, int(a), int(z or a)), key=urut_juz) if not salah_halaman(hal) else []
        if len(di) > 1:
            kena = [j for j in di if not cek(sid, j, hal, pot, [], kutipan, None, sisipan=sisipan)]
            if len(kena) == 1:
                return cek(sid, kena[0], hal, pot, perhatian, kutipan, rinci, pengantar, sisipan)
            if kena:
                pilih = " atau ".join(f"<<{sid}|{j}|{hal}>>" for j in kena)
                return (f"teks ada di halaman {hal} beberapa bagian kitab {sid} ({'، '.join(kena)}): sebut bagiannya ({pilih}); "
                        f"«ص{hal}» di catatan kaki tetap cukup :: {pot[:40]}")
    if shamela.OTOMATIS.search(shamela.info(sid)["betaka_text"]):
        pesan = (f"kitab {sid}: nomor halamannya buatan Shamela (مرقم آليا), bukan nomor cetakan — "
                 "pakai edisi yang «موافق للمطبوع», atau cocokkan ke cetakannya")
        if not any(p.endswith(pesan) for p in perhatian):  # sekali per kitab, walau tiap baris diberi awalan
            perhatian.append(pesan)
    elif NASKAH_TULISAN.search(shamela.info(sid)["betaka_text"]):
        pesan = (f"kitab {sid}: belum dicetak (مخطوط/غير مطبوع), nomor halamannya nomor lembar naskah — sebut lembarnya "
                 "(مخطوط، ل n) atau pakai edisi cetak kalau ada")
        if not any(p.endswith(pesan) for p in perhatian):
            perhatian.append(pesan)
    e = salah_halaman(hal)
    if e:
        return e
    p1, p2 = rentang_halaman(hal)
    for n, (a, b) in halaman_janggal(sid, juz).items():
        pesan = (f"nomor halaman {juz}/{n} kitab {sid} jauh dari halaman lain juz itu (rekaman sebelum/sesudahnya di Shamela: "
                 f"{'، '.join(f'ص{x}' for x in (a, b) if x)}): mungkin salah ketik Shamela; cocokkan ke cetakan (`scan`) dan tulis nomor cetakannya")
        if p1 <= n <= p2 and not any(p.endswith(pesan) for p in perhatian):
            perhatian.append(pesan)
    if pot.startswith("#") and not kutipan:
        nomor = pot[1:].strip().translate(ANGKA_LATIN)
        if not re.fullmatch(r"\d+", nomor):  # «#» kosong cocok di halaman mana saja
            return f"nomor hadits kosong/bukan angka: <<…|{pot}>>"
        # Rekaman dapat melintasi halaman cetak. Kepala pada halaman sesudah p2 bukan bukti di sini;
        # kepala sebelumnya tetap sah untuk lanjutan hadits dalam rekaman yang menyentuh halaman bukti.
        if any(nomor_hadits("\n".join(teks for halaman, teks in norma.per_halaman(r)
                                    if halaman is not None and halaman <= p2), nomor)
               for r in rekaman(sid, juz, p1, p2)):
            return ""
        return (f"{nomor} bukan kepala hadits di {sid} {juz}/{hal}: angka di awal baris («{nomor} - حدثنا», «36 - ({nomor})») yang "
                "dihitung, bukan nomor ayat atau catatan; betulkan nomornya, atau pakai potongan lafaz dari halaman itu")
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
        return f"{'kutipan' if kutipan else 'potongan'} tanpa huruf Arab: {pot[:40]}"
    if angka_lepas is not None:
        return (f"bagian kutipan yang cuma angka tidak bisa dicek: tulis angka itu bersama lafaz kitab yang menempel padanya "
                f"(«رقم (٨٥)», «[الحج:٧٠]»), tanpa ... atau ayat di antaranya (titik milik kitab pun dibuang) :: {angka_lepas}")
    minimal = KUTIPAN_MIN if kutipan else POTONGAN_MIN
    for i, b in enumerate(bagian):
        if len(norma.padat(b)) < minimal:
            if kutipan:
                # bagian pendek yang menempel ayat («{Q:22:70} [الحج:٧٠]»): letaknya dipastikan pemeriksaan celah ayat
                dekat = celah[max(0, i - 1):i + 1]
                if dekat and not any(DIPOTONG.search("".join(c)) for c in dekat):
                    continue
                if DIPOTONG.search(pot):  # «…» milik kitab sendiri yang ikut disalin: kutipan utuhnya bersambung di kitab
                    utuh = DIPOTONG.sub(" ", pot)
                    if not cek(sid, juz, hal, utuh, [], True, False, sisipan=sisipan):
                        return cek(sid, juz, hal, utuh, perhatian, True, rinci, sisipan=sisipan)
                return f"bagian kutipan terlalu pendek untuk dicek (paling sedikit {minimal} huruf; jangan dipotong ... di situ) :: {b}"
            return f"potongan terlalu pendek (paling sedikit {minimal} huruf; yang pendek cocok di sembarang tempat): {pot}"
    for b in bagian:
        e = _cek_bagian(sid, juz, hal, p1, p2, b, kutipan, perhatian, rinci)
        if e:
            return e
    rr = rekaman(sid, juz, p1, p2)
    if len(bagian) > 1:
        jarak = [j for j in (berurutan(rr, sisi, bagian) for sisi, _ in norma.BAGIAN) if j is not None]
        if not jarak:
            return f"bagian kutipan yang dipisah ... tidak berurutan seperti di kitab {sid} {juz}/{hal} :: {pot[:40]}"
    angka = kutipan and re.search(r"\d", AYAT_DI_KUTIPAN.sub(" ", pot).translate(ANGKA_LATIN))
    diperiksa = False  # angka (atau rujukan [سورة: n] yang angkanya dibuang) sudah dicocokkan di tempatnya
    if kutipan and (angka or re.search(r"[\[\]]", pot) or AYAT_DI_KUTIPAN.search(pot)):
        e, catat, diperiksa = susunan_kitab(rr, bagian, celah, ujung, (p1, p2))
        if e:
            return f"{e} ({sid} {juz}/{hal}) :: {pot[:40]}"
        perhatian += [f"{p} ({sid} {juz}/{hal}) :: {pot[:40]}" for p in catat]
        if diperiksa in ("footnotes", "footnotes?") and not any("bukti ada di حاشية المحقق" in p for p in perhatian[p0:]):
            perhatian.append(pesan_hasyiah(sid, juz, hal, pot, diperiksa == "footnotes?"))
    # dipotong ...: sambungan yang rapat pun bisa mengubah makna atau pembicaranya; dipisah ayat: diperiksa susunan_kitab
    if len(bagian) > 1 and min(jarak) and DIPOTONG.search(pot):
        perhatian.append(f"kutipan dipotong ... atau dipisah ayat ({min(jarak)} huruf kitab dilompati) {sid} {juz}/{hal}: "
                         f"baca yang dilompati, pastikan makna dan pembicaranya tetap :: {pot[:40]}")
    if kutipan:
        # naskah menisbatkan kutipan ke pengarang kitab ini («قال البهوتي: "…"»): pembicara di kitab ikut diperiksa.
        # Nama pengarang harus tepat sesudah «قال» (pembicaranya): «نقل الشوكاني عن الزركشي أنه قال:» menisbatkan ke
        # الزركشي, «فقال فيما نقله القرطبي:» ke yang disebut sebelumnya
        nama = norma.padat(shamela.info(sid).get("main_author_name_ar") or "")
        qaul = QAUL.search(pengantar)
        sesudah = (qaul.group().split(maxsplit=1) + [""])[1] if qaul else ""  # kata sesudah «قال»
        pengarang = nama if nama and norma.padat(GELAR.sub("", sesudah)).startswith(nama) else None
        perhatian += [f"{p} ({sid} {juz}/{hal}) :: {pot[:40]}"
                      for p in ragu_kutipan(rr, bagian[0], pot, angka and not diperiksa, lambda: rekaman_dulu(sid, juz, p1, p2),
                                            pengarang)
                      + ragu_akhir(rr, bagian[-1])]
    if not any("حاشية المحقق" in p for p in perhatian[p0:]):  # yang di حاشية sudah disebut kalimat muhaqqiq
        judul = judul_muhaqqiq(sid, rr, norma.padat(bagian[0]), kutipan)
        if judul:
            perhatian.append(f"bukti {sid} {juz}/{hal} ada di bagian «{judul}» (tulisan muhaqqiq/penerbit, bukan pengarang): "
                             f"jangan dinisbatkan ke pengarang kitab :: {pot[:40]}")
    return ""


# judul toc bagian tulisan muhaqqiq/penerbit di depan kitab (dibaca dari toc kitab lokal; judul yang sama untuk isi
# kitab sendiri, mis. «مقدمة» saja atau «ترجمة ابن عباس» di kitab tarajim, sengaja tidak dihitung)
JUDUL_MUHAQQIQ = re.compile(
    r"^(?:مقدمة|كلمة)\s+(?:ال)?(?:طبعة|تحقيق|محقق|مصحح|ناشر|مشرف|لجنة)"
    r"|^كلمة\s*:?\s*معالي|^تقديم(?:\s+بقلم|$)|^(?:ال)?إهداء$"
    r"|^ترجمة\s+(?:موجزة\s+|مختصرة\s+)?(?:لل|ال)(?:مؤلف|مصنف|شارح|ناظم|محقق)|^ترجمة\s+صاحب|حياة\s+(?:ال)?مؤلف"
    r"|^(?:ال)?تعريف\s+ب(?:ال)?(?:مؤلف|مصنف|شارح|كتاب)|^منهج\s+(?:ال)?(?:مؤلف|مصنف)\s+في"
    r"|^منهج\s+(?:ال)?تحقيق|^منهجي\s+في|^عملي\s+في|^وصف\s+(?:ال)?(?:نسخ|مخطوط)|^دراسة\s+(?:موجزة|الكتاب|الرسالة|المؤلف)")


def judul_muhaqqiq(sid, rr, q, utuh=True):
    """Judul (atau induknya) tulisan muhaqqiq/penerbit yang menaungi awal q (`padat`) di matan rr; '' kalau bukan."""
    for r in rr:
        c = shamela._cocok(r, q, "body", utuh)
        if c:
            return next((j for j in shamela.rantai_judul(sid, shamela.judul_naung(sid, r, c)) if JUDUL_MUHAQQIQ.search(j)), "")
    return ""


def susunan_kitab(rr, bagian, celah, ujung=([], []), dalam=None):
    """Yang tidak terbaca pencocokan huruf `padat`, diperiksa di teks asli kitab (matan, lalu حاشية) tempat bagian-bagian
    kutipan berada: celah {Q:} harus memang ayat (bertanda ﴿﴾; nomornya sama kalau kitab menulis [سورة: n]), dan angka
    tiap bagian harus sama dengan angka kitab di tempatnya. Calon susunan hanya dari halaman bukti (`dalam`),
    dengan batas kata yang sama seperti pemeriksaan huruf. Kembalikan (galat, perhatian, bagian kitab yang cocok)."""
    q = [norma.padat(b) for b in bagian]
    kata = [shamela.kata_dalam(b) for b in bagian]
    terbaik = None
    for sisi, _ in norma.BAGIAN:
        raw = norma.TAGS.sub(lambda m: " " * len(m.group()), "\n".join(r.get(sisi) or "" for r in rr))
        # Raw utuh diperlukan untuk ayat tepat sebelum/sesudah halaman bukti. Yang dibatasi hanya posisi calon.
        sah, tak_pasti, catatan, offset = [], [], [], 0  # catatan = حاشية yang tertulis di body (`shamela.catatan_body`)
        for r in rr:
            t = r.get(sisi) or ""
            if sisi == "body":
                catatan += [(offset + a, offset + z) for a, z in shamela.catatan_body(t)]
            batas = [(0, r.get("page_num"))] + [(m.start(), int(m[1])) for m in norma.PENANDA.finditer(t)]
            samar = sisi == "footnotes" and len(batas) == 1
            for i, (a, h) in enumerate(batas):
                z = batas[i + 1][0] if i + 1 < len(batas) else len(t) + 1  # termasuk pemisah antarrekaman
                a, z = offset + a, min(offset + z, len(raw))
                if dalam is None or samar or h is not None and dalam[0] <= h <= dalam[1]:
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

        def cocok(i, j, k):
            return (len(q[i]) < KUTIPAN_MIN or shamela._utuh(rek, "body", j, k, kata[i])) and di_halaman(mulai(j), akhir(k))

        for letak in susunan_bagian(pd, q, maks=float("inf"), cocok=cocok):
            hasil = _nilai_susunan(raw, angka, letak, bagian, celah, ujung, mulai, akhir, di_halaman)
            kunci = (bool(hasil[0]), len(hasil[1]))
            jenis = ("footnotes?" if any(a <= mulai(j) < z for a, z in tak_pasti for j, _ in letak) else
                     "footnotes" if any(a < akhir(k) and mulai(j) < z for a, z in catatan for j, k in letak) else sisi)
            if terbaik is None or kunci < terbaik[0]:
                terbaik = kunci, hasil, jenis
            if kunci == (False, 0):
                return "", [], jenis
    return (*terbaik[1], terbaik[2]) if terbaik else (
        "susunan kutipan berangka atau berayat tidak ditemukan di halaman bukti dengan kata utuh", [], False)


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


def _nilai_susunan(raw, angka, letak, bagian, celah, ujung, mulai, akhir, di_halaman=None):
    """(galat, perhatian) satu susunan letak bagian kutipan di teks asli kitab raw (lihat susunan_kitab)."""
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
            return (f"di kitab tidak ada ayat di tempat {{Q:}} (sesudah «…{' '.join(bagian[i].split()[-3:])}»), yang ada "
                    f"di kitab: «{dilompati[:40] or 'tidak ada apa-apa'}». {{Q:}} di dalam kutipan hanya untuk ayat yang memang "
                    "dikutip kitab di situ", catat)
        if _nomor_lain(spec, rujukan):
            if not any(ayat_persis(spec, m.group()[1:-1]) for m in AYAT_KITAB.finditer(antara)):
                return f"ayat yang dikutip kitab di tempat {{Q:{spec[0]}}} adalah {'، '.join(rujukan)}: salin ayat yang benar", catat
            catat.append(NOMOR_KITAB_LAIN.format(spec[0], '، '.join(rujukan)))
        sama = spec and ayat_sama(spec, antara, rujukan)
        if spec and not sama:
            return (f"ayat yang dikutip kitab di tempat {{Q:{spec[0]}}} adalah surat lain "
                    f"({'، '.join(rujukan) or AYAT_KITAB.search(antara).group()[:40]}): salin ayat yang benar", catat)
        if isinstance(sama, str):
            catat.append(sama)
        bertanda = " ".join(m.group()[1:-1] for m in AYAT_KITAB.finditer(antara))
        if spec and bertanda:  # ayat kitab tanpa tanda ﴿﴾ tidak bisa dipastikan batasnya
            e, p = pesan_tercetak(ayat_tercetak(spec, bertanda, antara), spec, bertanda)
            if e:
                return e, catat
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
        if _nomor_lain(spec, rujukan):
            if not ayat_persis(spec, ayat_.group()[1:-1]):
                return f"ayat yang dikutip kitab di tempat {{Q:{spec[0]}}} adalah {'، '.join(rujukan)}: salin ayat yang benar", catat
            catat.append(NOMOR_KITAB_LAIN.format(spec[0], '، '.join(rujukan)))
        sama = ayat_sama(spec, ayat_.group(), rujukan)
        if not sama:
            return (f"ayat yang dikutip kitab di tempat {{Q:{spec[0]}}} adalah surat lain "
                    f"({'، '.join(rujukan) or ayat_.group()[:40]}): salin ayat yang benar", catat)
        if isinstance(sama, str):
            catat.append(sama)
        e, p = pesan_tercetak(ayat_tercetak(spec, ayat_.group()[1:-1]), spec, ayat_.group()[1:-1])
        if e:
            return e, catat
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
                return (f"bagian kutipan terlalu pendek untuk dicek (paling sedikit {KUTIPAN_MIN} huruf), dan di kitab ia "
                        f"tidak menempel ayatnya sebagai kata utuh :: {b.strip()}", catat)
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
        if naskah and di_halaman is not None and any(not di_halaman(a + m.start(), a + m.end()) for m in nomor):
            return "angka di kutipan berada di luar halaman bukti: perluas rentang bukti atau salin angka dari halaman yang dirujuk", catat
        di_kitab = [m.group() for m in nomor]
        if naskah != di_kitab:
            beda = (f"angka di kutipan ({' '.join(naskah) or 'tidak ada'}) beda dengan angka kitab di tempat itu "
                    f"({' '.join(di_kitab) or 'tidak ada'})")
            if len(naskah) == len(di_kitab):
                return f"{beda}: salin angkanya dari kitab", catat
            catat.append(f"{beda}: salin angkanya dari kitab")
    return "", catat


def berurutan(rr, sisi, bagian):
    """Kalau bagian-bagian kutipan muncul berurutan di sisi (matan/حاشية) rekaman rr: jarak terbesar di antaranya
    (huruf `padat`), dengan susunan yang paling rapat. None kalau tidak berurutan."""
    teks = "".join(norma.ruas_halaman(r, sisi)[0] for r in rr)
    bagian = [norma.padat(b) for b in bagian]
    # Semua kemunculan tetap dicoba; batas 50 milik pemeriksaan angka/ayat tidak berlaku di sini.
    terbaik = None
    for letak in susunan_bagian(teks, bagian, maks=float("inf")):
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
    teks, ruas = norma.ruas_halaman(r, "body")
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
        c = shamela._cocok(r, q, "body", True)
        if c:
            teks, (_, ujung) = norma.ruas_halaman(r, "body")[0], shamela._batas_kata(r, "body")
            sesudah = teks[c[1]:min((u for u in ujung if u > c[1]), default=c[1])]
            if sesudah == "الا" and not henti(r, c[1]):
                return ["di kitab kutipan ini disambung «إلا» (pengecualiannya terpotong): pastikan maknanya tidak terbalik"]
            return []
    return []


def ragu_kutipan(rr, awal, pot, periksa_angka=True, dulu=lambda: None, pengarang=None):
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
        c = shamela._cocok(r, q, "body", True)
        if c or k_utuh:
            return c
        teks = norma.ruas_halaman(r, "body")[0]
        n = next((n for n in range(min(len(q), len(teks)) - 1, 9, -1) if teks.endswith(q[:n])), 0)
        return n and len(teks) - n in shamela._batas_kata(r, "body")[0] and (len(teks) - n, len(teks))
    k_utuh = any(shamela._cocok(r, q, "body", True) for r in rr)
    for k, r in enumerate(rr):
        c = letak(r)
        if c:
            teks, mulai = norma.ruas_halaman(r, "body")[0], sorted(shamela._batas_kata(r, "body")[0])
            sebelum = [a for a in mulai if a <= c[0]]  # awal kata kutipan (huruf sambung و/ف ikut kata itu)
            kata = teks[sebelum[-2]:sebelum[-1]] if len(sebelum) > 1 else None
            lalu = None if kata else rr[k - 1] if k else dulu()
            if lalu:  # kutipan mulai di awal rekaman: kata terakhir rekaman sebelumnya
                awal_lalu = shamela._batas_kata(lalu, "body")[0]
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
    """`shamela.kata_titik_dua` matan r, atau [] kalau pemotongan katanya tidak sama dengan `_batas_kata`."""
    teks, mulai = norma.ruas_halaman(r, "body")[0], sorted(shamela._batas_kata(r, "body")[0])
    kata = shamela.kata_titik_dua(r)
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
