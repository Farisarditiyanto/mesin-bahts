# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bentuk rujukan (التوثيق) menurut عبد الوهاب أبو سليمان، كتابة البحث العلمي (Shamela 8350): data cetak lengkap di
rujukan pertama tiap kitab (ص170), «المصدر نفسه» hanya untuk sumber catatan kaki tepat sebelumnya (ص170-172), beberapa
sumber dipisah «؛» (ص176 no. 15), nama tanpa gelar (ص175-176 no. 11), dan «ص»/«ج» tanpa titik (ص179). Urutan unsur
rujukan (judul dulu, lalu pengarang) dan juz/hal «7/43» = aturan repo; kitab itu mendahulukan pengarang dan menulis
«ج٢، ص٣٩» (ص134، 170). Semuanya perhatian, tidak pernah GAGAL: bentuk, bukan kebenaran isi."""
import re

import norma
import shamela
from dasar import ANGKA_LATIN, BUKAN_RUJUKAN, MERUJUK_KATA, ekor
from gelar import GELAR, KUNCI_NAMA, nama_bergelar
from kitab_lokal import bagian_kitab
from cek_hadits import takhrij
from cek_sumber import PERANTARA
from petik import luar_petik, seragam

# baris `kartu` yang BUKAN data cetak (judul, pengarang, jumlah jilid, catatan); sisanya data cetak, juga baris tanpa kunci
# («(وصورتها دار المعرفة، بيروت)») dan kunci yang tidak terduga («وقف على طبعه وصححه»، «ثم أعاد طباعتها»، «ثم صورتها»)
BUKAN_DATA = re.compile(r"^(?:الكتاب|المؤلف|المؤلفون|عدد \S+|تنبيه|ملاحظة|ملحوظة|أعده للشاملة|مصدر الكتاب)$")  # «عدد الصفحات: ٥٦٩» bukan tahun
# «المؤلف: تصدر عن منظمة المؤتمر الإسلامي بجدة» (jurnal, kartu 8356) = penerbitnya
PENERBIT_DI_PENGARANG = re.compile(r"^\s*(?:تصدر|يصدر|صادر[ةه]?|صدرت)\s+عن")
# pasangan kata yang memuat kata ini terlalu umum untuk menunjuk data cetak («عبد الله بن …» ada di nama mana pun)
KATA_UMUM = frozenset("بن ابن بنت عبد ابو ابي ابا ام ه م ت ط من في الي عن ثم و".split())
# …kecuali sebagai jembatan nasab di antara dua kata khas: «دار ابن الجوزي»، «محمد بن صالح» (penerbit/muhaqqiq)
NASAB = frozenset("بن ابن بنت ابو ابي ابا ام".split())
KITAB_HADITS = 6  # kategori Shamela كتب السنة: data cetaknya di المصادر, catatan kakinya cukup takhrij (AGENTS.md)


def _kata(teks):
    """Kata Arab tanpa harakat dan gelar, huruf yang sering ditulis beda disamakan (أإآ->ا، ة->ه، ى->ي)."""
    teks = GELAR.sub(" ", norma.HARAKAT.sub("", teks))
    return re.findall(r"[ء-ي]+", re.sub("[أإآ]", "ا", teks).replace("ة", "ه").replace("ى", "ي"))


def _jejak(kata):
    """Penanda data cetak dari deret kata: dua kata khas berurutan, atau tiga kata «khas + nasab + khas»."""
    dua = {f"{x} {y}" for x, y in zip(kata, kata[1:]) if x not in KATA_UMUM and y not in KATA_UMUM}
    return dua | {f"{x} {n} {y}" for x, n, y in zip(kata, kata[1:], kata[2:])
                  if n in NASAB and x not in KATA_UMUM and y not in KATA_UMUM}


@shamela.cache_kitab()
def jejak_kartu(sid):
    """(pasangan dua kata berurutan dari nilai data cetak `kartu`, tahun cetakan) kitab ini; kosong = kartunya tanpa
    data cetak, atau kitab hadits (data cetaknya di المصادر), atau kitab tidak terbaca."""
    try:
        m = shamela.info(sid)
    except (LookupError, OSError, ValueError):
        return frozenset(), frozenset()
    if m.get("category_id") == KITAB_HADITS:
        return frozenset(), frozenset()
    pasangan, tahun, judul = set(), set(), set()
    for baris in (m.get("betaka_text") or "").replace("\r", "\n").split("\n"):
        k = KUNCI_NAMA.match(norma.HARAKAT.sub("", baris))
        nilai = norma.HARAKAT.sub("", baris)[k.end():] if k else baris
        kata = _kata(nilai)
        dua = _jejak(kata)
        if baris.lstrip().startswith("[") or (k and BUKAN_DATA.match(k[1].strip()) and not PENERBIT_DI_PENGARANG.match(nilai)):
            judul |= dua  # judul/pengarang: ada di rujukan mana pun, jadi bukan tanda data cetak
            continue
        pasangan |= dua
        tahun |= set(re.findall(r"(?<!\d)\d{3,4}(?!\d)", nilai.translate(ANGKA_LATIN)))
    # judul katalog juga: deskripsi tanpa kunci bisa mengulang judul («الشرح الكبير … «حاشية الدسوقي» عليه», kartu 21604)
    kata = _kata(m.get("title_ar", "").split(" - ")[0].replace("=", " "))
    judul |= {f"{x} {y}" for x, y in zip(kata, kata[1:])} | _jejak(kata)
    return frozenset(pasangan - judul), frozenset(tahun)


def _berdata(bagian, sid):
    """Potongan rujukan ini memuat data cetak kitabnya: dua kata berurutan dari penerbit/muhaqqiq di `kartu`, atau
    tahun cetakannya («1423هـ»)."""
    pasangan, tahun = jejak_kartu(sid)
    kata = _kata(bagian)
    if _jejak(kata) & pasangan:
        return True
    angka = bagian.translate(ANGKA_LATIN)
    return any(t in tahun for t in re.findall(r"(?<!\d)(\d{3,4})\s*[هـم]", angka))


def data_cetak(isi, terbukti, sudah):
    """Perhatian tiap kitab yang dirujuk pertama kali tanpa data cetak. `sudah` = nomor kitab yang sudah pernah
    dirujuk (diisi di sini). Takhrij dan kitab hadits (data cetaknya di المصادر) tidak dinilai, tetapi takhrij yang
    memuat data cetak dihitung sebagai rujukan pertama kitab-kitabnya."""
    nash = takhrij(isi) or norma.HARAKAT.sub("", isi).lstrip().startswith(BUKAN_RUJUKAN)
    hasil = []
    for bagian, bb in bagian_kitab(isi, terbukti):
        for sid in dict.fromkeys(b.sid for b in bb):
            if sid in sudah:
                continue
            berdata = _berdata(bagian, sid)
            if nash and not berdata:
                continue  # rujukan pertamanya nanti, di luar takhrij
            sudah.add(sid)
            if not berdata and any(jejak_kartu(sid)):
                judul = shamela.info(sid)["title_ar"].split(" - ")[0]
                hasil.append(f"rujukan pertama «{judul}» tanpa data cetak: tulis data lengkapnya dari `kartu {sid}` "
                             f"(pengarang, muhaqqiq, penerbit-kota, cetakan-tahun, lalu juz/hal); rujukan berikutnya cukup "
                             f"ringkas, tanpa data cetak (أبو سليمان، كتابة البحث العلمي، ص170){ekor(isi)}")
    return hasil


def pemisah_sumber(isi, terbukti):
    """Perhatian kalau beberapa sumber di satu catatan kaki (bukan takhrij) dipisah «،», bukan «؛» (ص176 no. 15), atau
    None. Sumber «نقلا عن/مقتبس من» (satu sumber lewat perantara) dan sumber berlabel («وفي الأثر: …») tidak dinilai."""
    if takhrij(isi):
        return None
    bagian = bagian_kitab(isi, terbukti)
    for (a, _), (_, _) in zip(bagian, bagian[1:]):
        # Hanya hubungan di batas dua kitab ini yang dinilai. Perantara/label di tempat lain dalam catatan kaki
        # tidak membebaskan sumber ketiga, dan «؛» di data muhaqqiq tidak menggantikan pemisah antarsumber.
        a = norma.HARAKAT.sub("", a).rstrip()
        if (any(not a[m.end():].strip() for m in PERANTARA.finditer(a))
                or re.search(r"(?<![ء-ي])و?في\s+[^:،؛.]{1,40}:\s*$", a)):
            continue
        ujung = re.sub(rf"\s*و?(?:{MERUJUK_KATA})\s*:?\s*$", "", a).rstrip()
        # Judul singkat yang tidak dikenali bisa masih di ujung potongan sebelumnya: «…ص10؛ والسبل، |الصنعاني…».
        # Satu bidang di antara «؛» dan nama pengarang itu adalah judulnya, bukan koma antarsumber.
        if "؛" in ujung and re.fullmatch(r"\s*[ء-ي][^،,؛]*[،,]\s*", ujung.rsplit("؛", 1)[1]):
            continue
        if ujung.endswith(("،", ",")):
            return (f"beberapa sumber dipisah «،»: pisahkan dengan «؛» («…، 7/43؛ الإنصاف، …») "
                    f"(أبو سليمان، كتابة البحث العلمي، ص176){ekor(isi)}")
    return None


def gelar(teks, apa):
    """Perhatian kalau sebuah nama di luar kutipan bertanda petik diawali gelar («تحقيق: د. …»، «، الشيخ …»), atau
    None. `apa` = tempatnya: "fn" (catatan kaki) atau "pustaka"."""
    g = nama_bergelar(luar_petik(seragam(teks)), awal_nama=teks.lstrip().startswith("**"), catatan_kaki=apa == "fn")
    if not g:
        return None
    return (f"gelar «{g}» di depan nama: buang gelarnya («تحقيق: عبد الله التركي»; `kartu` sudah tanpa gelar) "
            f"(أبو سليمان، كتابة البحث العلمي، ص175-176){ekor(teks, apa=apa)}")


# «المصدر نفسه»، «المرجع نفسه»، «نفس المصدر»: mengulang sumber catatan kaki tepat sebelumnya (ص170-172)
NAFSIH = re.compile(r"(?<![ء-ي])(?:(?:ال)?(?:مصدر|مرجع)\s+نفسه|نفس\s+(?:ال)?(?:مصدر|مرجع))(?![ء-ي])")


def sumber_nafsih(isi, sumber, sumber_lalu):
    """Perhatian kalau catatan kaki «المصدر نفسه» berbukti sumber (`sumber`: nomor kitab, «luar|berkas», «w…») yang tidak
    satu pun ada di catatan kaki tepat sebelumnya (`sumber_lalu`), atau None. Catatan kaki tanpa bukti di salah satunya
    (penjelasan, ayat) tidak dinilai."""
    if not sumber or not sumber_lalu or sumber & sumber_lalu or not NAFSIH.search(norma.HARAKAT.sub("", isi)):
        return None
    return (f"«المصدر نفسه» untuk sumber yang bukan sumber catatan kaki tepat sebelumnya: tulis judul ringkasnya "
            f"(judul، pengarang، juz/hal) (أبو سليمان، كتابة البحث العلمي، ص170-172){ekor(isi)}")


# «ص.٣٢»، «ج. ٢»: titik sesudah ص/ج terbaca nol di depan angkanya (ص179)
TITIK_SINGKATAN = re.compile(r"(?<![ء-ي.])([صج])\s*\.\s*(?=[0-9٠-٩])")


def titik_singkatan(isi):
    """Perhatian kalau «ص»/«ج» di luar kutipan diberi titik sebelum angkanya, atau None."""
    m = TITIK_SINGKATAN.search(luar_petik(seragam(isi)))
    if not m:
        return None
    return (f"«{m[0].strip()}…»: tulis «{m[1]}» tanpa titik («ص32»، «ج2»): titik sesudahnya terbaca nol "
            f"(أبو سليمان، كتابة البحث العلمي، ص179){ekor(isi)}")
