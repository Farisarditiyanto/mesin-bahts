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


# Kode perhatian: 6 huruf heksa dari isinya tanpa awal «baris …: ». Naskah yang hanya bergeser barisnya tetap berkode
# sama, jadi «terima» di riset.txt tidak basi karena baris lain ditambah; isi yang berubah (kalimat di catatan kakinya,
# kutipannya) = kode baru, jadi perhatian itu dinilai lagi.
KODE = re.compile(r"[0-9a-f]{6}")
# baris perhatian di laporan `cek`: «  ! <kode> <perhatian>»
BARIS_PERHATIAN = re.compile(r"^  ! ([0-9a-f]{6}) (.*)$", re.M)


def kode(p):
    return hashlib.sha1(pisah_baris(p)[1].encode("utf8")).hexdigest()[:6]


def baris_perhatian(p):
    return f"  ! {kode(p)} {p}"
