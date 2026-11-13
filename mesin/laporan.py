# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bentuk baris laporan `cek`: «baris n: …», rentang baris, perhatian kembar yang digabung jadi satu baris, dan kode
tiap perhatian (dipakai «terima <kode> <alasan>» di riset.txt)."""
import hashlib, re


def ringkas_rentang(hal, pisah="، "):
    """[36, 37, 38, 41] -> «36-38، 41»."""
    potong, awal = [], hal[0]
    for x, y in zip(hal, hal[1:] + [None]):
        if y != x + 1:
            potong.append(f"{awal}-{x}" if x != awal else str(x)); awal = y
    return pisah.join(potong)


# awal perhatian: baris naskahnya, mis. «baris 77: » atau, untuk perhatian gabungan, «baris 77, 81-83: »
BARIS_AWAL = re.compile(r"baris (\d+(?:-\d+)?(?:, \d+(?:-\d+)?)*): ")


def daftar_baris(nn):
    """Nomor baris naskah -> «77, 81-83» (urut, tanpa kembar)."""
    return ringkas_rentang(sorted(set(nn)), ", ")


def pisah_baris(p):
    """«baris 77, 81-83: isi» -> ([77, 81, 82, 83], «isi»); tanpa awal «baris …: » -> ([], p).
    Dipakai juga .github/uji_jebakan.py untuk mencocokkan perhatian gabungan ke tiap barisnya."""
    m = BARIS_AWAL.match(p)
    if not m:
        return [], p
    return [n for a, z in re.findall(r"(\d+)(?:-(\d+))?", m[1]) for n in range(int(a), int(z or a) + 1)], p[m.end():]


def gabung_kembar(perhatian):
    """Perhatian yang isinya sama persis di beberapa baris naskah (bukti di حاشية yang sama, kata nafi yang sama)
    jadi satu baris «baris 77, 81-83: …» di tempat kemunculan pertamanya: dibaca dan dibereskan sekali."""
    kumpul = {}
    for p in perhatian:
        nn, isi = pisah_baris(p)
        kumpul.setdefault(isi, []).extend(nn)
    return [f"baris {daftar_baris(nn)}: {isi}" if nn else isi for isi, nn in kumpul.items()]


KODE = re.compile(r"[0-9a-f]{6}")


def kode(p, teks_baris):
    """Kode perhatian (6 huruf heksa, dipakai «terima» di riset.txt): sidik isinya tanpa awal «baris …: » ditambah teks
    utuh tiap baris naskah yang disebutnya (`teks_baris`: nomor -> teks). Naskah yang hanya bergeser barisnya tetap
    berkode sama; baris yang disebut berubah isinya, atau baris baru ikut tergabung ke perhatian kembar = kode baru,
    jadi «terima» lama basi dan perhatian itu dinilai lagi (pesan perhatian hanya memuat awal catatan kakinya)."""
    nn, isi = pisah_baris(p)
    sidik = isi + "".join(f"\n{teks_baris.get(n, '')}" for n in nn)
    return hashlib.sha1(sidik.encode("utf8")).hexdigest()[:6]
