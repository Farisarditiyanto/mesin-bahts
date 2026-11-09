# SPDX-License-Identifier: AGPL-3.0-or-later
"""`cek --jejak`: kutipan yang tidak ketemu di kitab buktinya dicari di kitab lain yang sudah diunduh. Hanya petunjuk,
bukan putusan. Juga alat penyusun letak bagian kutipan (susunan_bagian) yang dipakai `cek`."""
import bisect, difflib, functools, zlib

import norma
import shamela
from dasar import ELIPSIS, RENTANG_MAKS

# `cek --jejak`, kutipan yang lafaznya sedikit berbeda dengan kitab; satuannya huruf `padat`
MIRIP_BENIH = 14  # panjang potongan kutipan yang harus ada persis di kitab
MIRIP_KUTIPAN = 30  # kutipan lebih pendek dari ini tidak dicari: yang pendek mirip di mana-mana
MIRIP_PANJANG = 300  # kutipan lebih panjang dari ini tidak dicari: waktu membandingkan = kuadrat panjangnya
MIRIP_MIN = 0.9  # bagian huruf yang harus sama (lihat `_mirip_kitab`)
MIRIP_CALON = 20  # tempat paling banyak tiap benih (benih umum, mis. basmalah, ada ribuan kali)
MIRIP_LONGGAR = 12  # tempat yang berjarak kurang dari ini dibandingkan sekali


def _bagian_cari(teks):
    """Semua bagian berhuruf Arab (`padat`), urut seperti di naskah, termasuk bagian pendek di samping ayat.
    Tidak boleh membuang satu bagian lalu menunjuk kitab yang hanya memuat sisanya."""
    return [p for b in ELIPSIS.split(teks) if (p := norma.padat(b))]


def _rangkaian(padat_, ix):
    """Rangkaian rekaman kitab dari teks `padat`-nya (`norma.Padat`): [(juz, tanda, teks, ruas)], teks dalam `bait`.
    Aturannya sama dengan `gabung`: urut halaman, dan hanya rekaman yang halamannya bersambung (sama atau +1) di juz
    yang sama yang dirangkai. ruas = (padat_, bagian, awal tiap rekaman di teks, nomor rekamannya), dibaca `_halaman_di`."""
    hasil = []
    juz = {}
    for i, x in enumerate(ix):
        juz.setdefault(x[0], []).append(i)
    for j, ii in juz.items():
        urut = sorted(ii, key=lambda i: ix[i][1] or 0)
        for s, (_, tanda) in enumerate(norma.BAGIAN):
            t, mulai = padat_.teks[s], padat_.deret[s]["mulai"]
            rek, awal, panjang, akhir = [], [], 0, 0
            for i in urut:
                n = ix[i][1]
                if panjang and not (n and akhir <= n <= akhir + 1):
                    hasil.append((j, tanda, b"".join(t[mulai[r]:mulai[r + 1]] for r in rek), (padat_, s, awal, rek)))
                    rek, awal, panjang, akhir = [], [], 0, 0
                rek.append(i); awal.append(panjang)
                panjang += mulai[i + 1] - mulai[i]
                akhir = max(akhir, ix[i][2])
            if panjang:
                hasil.append((j, tanda, b"".join(t[mulai[r]:mulai[r + 1]] for r in rek), (padat_, s, awal, rek)))
    return hasil


@functools.lru_cache(maxsize=4)  # banyak GAGAL di kitab yang sama tidak membaca ulang; memori tetap kecil
def rangkaian_kitab(sid):
    """`_rangkaian` kitab sid; `jejak` melepasnya tiap kitab."""
    return _rangkaian(shamela._cache(sid), shamela.indeks(sid))


def _halaman_di(ruas, a, z):
    """Rentang halaman cetak (kecil-besar) potongan teks[a:z] rangkaian yang ruasnya `ruas` (lihat `_rangkaian`):
    halaman awal ruas pertama yang berakhir sesudah a, halaman akhir ruas pertama yang berakhir di z atau sesudahnya."""
    padat_, s, awal, rek = ruas
    d = padat_.deret[s]

    def ruas_di(x, cari):  # ruas rekaman yang memuat letak x (rekaman kosong tidak memuat apa pun)
        k = bisect.bisect_right(awal, x) - 1
        i = rek[k]
        return d["h1"], d["h2"], cari(d["akhir"], x - awal[k], d["ruas"][i], d["ruas"][i + 1])
    h1s, _, k1 = ruas_di(a, bisect.bisect_right)
    _, h2s, k2 = ruas_di(z - 1, lambda deret, x, lo, hi: bisect.bisect_left(deret, x + 1, lo, hi))
    h1, h2 = (None if x == norma.TANPA_HAL else x for x in (h1s[k1], h2s[k2]))
    return (h2, h1) if (h1 or 0) > (h2 or 0) else (h1, h2)  # penanda halaman yang menurun di satu rekaman


def tempat_kitab(rangkaian, bagian):
    """Juz, rentang halaman, dan tanda (matan/حاشية) tempat SEMUA bagian kutipan berurutan: boleh menyambung ke halaman
    berikutnya, paling lebar RENTANG_MAKS halaman. None kalau tidak ada. Hanya petunjuk: putusannya tetap milik `cek`.
    Yang ditunjuk rentang tersempit: kutipan ber-... tidak boleh ditunjuk di tempat bagian umumnya kebetulan berjauhan."""
    terbaik = None
    for juz, tanda, teks, ruas in rangkaian:
        for letak in susunan_bagian(teks, bagian, len(teks)):
            h1, h2 = _halaman_di(ruas, letak[0][0], letak[-1][1])
            lebar = (h2 or 0) - (h1 or 0)
            if lebar <= RENTANG_MAKS and (terbaik is None or lebar < terbaik[0]):
                terbaik = lebar, ("-" if juz is None else juz), (h1, h2), tanda
            if lebar == 0:
                return terbaik[1:]
    return terbaik[1:] if terbaik else None


def _mirip_kitab(rangkaian, q):
    """Tempat q (sudah `padat`) yang lafaznya sedikit berbeda: (kemiripan, juz, halaman, tanda) terbaik, atau None.
    Benih = potongan pendek q yang harus ada persis; tiap tempat benihnya lalu dibandingkan huruf per huruf dengan q.
    Kemiripan = huruf yang sama, berurutan, dibagi panjang yang lebih besar antara q dan tempat itu: kata kitab yang
    tidak ada di kutipan (mis. kata nafi) ikut menurunkannya. Hanya petunjuk, sama seperti `tempat_kitab`."""
    benih = [(k, q[k:k + MIRIP_BENIH]) for k in range(0, len(q) - MIRIP_BENIH + 1, MIRIP_BENIH)]
    terbaik = None
    for juz, tanda, teks, ruas in rangkaian:
        mulai = set()
        for k, b in benih:
            j, n = teks.find(b), 0
            while j >= 0 and n < MIRIP_CALON:
                mulai.add(max(0, j - k) // MIRIP_LONGGAR)
                j, n = teks.find(b, j + 1), n + 1
        for m in mulai:
            awal = max(0, m * MIRIP_LONGGAR - MIRIP_LONGGAR)
            blok = [x for x in difflib.SequenceMatcher(None, q, teks[awal:awal + len(q) + 3 * MIRIP_LONGGAR], autojunk=False)
                    .get_matching_blocks() if x.size >= 3]
            if not blok:
                continue
            a, z = awal + blok[0].b, awal + blok[-1].b + blok[-1].size
            nilai = sum(x.size for x in blok) / max(len(q), z - a)
            if nilai >= MIRIP_MIN and (terbaik is None or nilai > terbaik[0]):
                terbaik = nilai, ("-" if juz is None else juz), _halaman_di(ruas, a, z), tanda
    return terbaik


def jejak(tertolak, maks=3):
    """Cari kutipan yang ditolak «teks TIDAK KETEMU di kitab» pada kitab lain yang sudah diunduh.
    Kembalikan baris laporan: hanya petunjuk, bukan bukti; putusan tetap milik `cek` (tidak ada yang diloloskan).
    Tiap kitab dibaca sekali (cache `padat`), dicari dengan lafaz yang sama seperti `cari`, lalu cache-nya dilepas.
    Kitab yang dirujuk satu kutipan tidak dicari untuk kutipan itu; kutipan yang dipotong ... hanya ditunjuk
    kalau semua bagiannya ada berurutan dalam satu rentang yang bisa diloloskan `cek`.
    Kutipan yang persisnya tidak ada di kitab mana pun: tempat yang lafaznya paling mirip ikut disebut, termasuk di
    kitab yang dirujuk (kutipan yang satu huruf atau katanya meleset), kecuali kutipan ber-... dan yang sangat panjang."""
    cari = {}  # bagian `padat` (tuple) -> entri kutipan
    for sid, teks in tertolak:
        bagian = _bagian_cari(teks)
        if not bagian:
            continue
        entri = cari.setdefault(tuple(bagian), {"teks": teks, "bagian": [norma.bait(b) for b in bagian],
                                                "tertuju": set(), "dapat": [], "dibaca": 0, "mirip": []})
        entri["tertuju"].add(str(sid))
    if not cari:
        return []
    semua = shamela.punya()
    rusak = []
    for sid in semua:
        aktif = [e for e in cari.values() if len(e["dapat"]) < maks and str(sid) not in e["tertuju"]]
        # kutipan ber-... tidak: satu bagian yang mirip tidak berkata apa-apa tentang bagian lain (bisa karangan)
        # kutipan panjang juga tidak: membandingkan seluruhnya terlalu lama, menilai sebagiannya menyesatkan
        longgar = [e for e in cari.values() if not e["dapat"] and len(e["bagian"]) == 1
                   and MIRIP_KUTIPAN <= len(e["bagian"][0]) <= MIRIP_PANJANG]
        if not aktif and not longgar:
            continue
        try:
            rangkaian = rangkaian_kitab(sid)
            for entri in aktif:
                t = tempat_kitab(rangkaian, entri["bagian"])
                entri["dibaca"] += 1
                if t:
                    entri["dapat"].append((sid, *t))
            for entri in longgar:
                if not entri["dapat"] and (t := _mirip_kitab(rangkaian, entri["bagian"][0])):
                    entri["mirip"].append((t[0], sid, *t[1:]))
            del rangkaian
        except (OSError, EOFError, ValueError, TypeError, AttributeError, KeyError, IndexError, zlib.error) as e:
            # Pencarian hanya petunjuk: sumber lain yang rusak tidak boleh menutup hasil kitab yang sehat.
            rusak.append(f"kitab {sid} ({type(e).__name__})")
        finally:
            shamela.lepas()  # isi kitab tidak menumpuk, juga sesudah gagal dibaca
            rangkaian_kitab.cache_clear()
        if all(len(e["dapat"]) >= maks for e in cari.values()):
            break
    baris = []
    for entri in cari.values():
        t, asli = entri["dapat"], entri["teks"]
        if not t:
            # kitab yang dirujuk dulu, lalu yang paling mirip, matan sebelum حاشية
            mirip = "، ".join(f"{sid} {shamela.letak(juz, h)}{tanda} (±{int(nilai * 100)}% huruf sama)" for nilai, sid, juz, h, tanda
                              in sorted(entri["mirip"], key=lambda x: (str(x[1]) not in entri["tertuju"], -x[0], bool(x[4])))[:maks])
            baris.append(f"  «{asli}» tidak ditemukan di {entri['dibaca']} kitab lain yang berhasil dibaca: "
                         "periksa ejaan dan sumber aslinya."
                         + (f" Paling mirip: kitab {mirip}. Lafaznya BERBEDA dan maknanya bisa terbalik: baca halamannya; "
                            "maknanya sama: salin lafaz kitabnya; berbeda: buang kutipannya, jangan disesuaikan." if mirip else ""))
            continue
        rinci = "، ".join(f"{sid} {shamela.letak(juz, h)}{tanda}" for sid, juz, h, tanda in t[:maks])
        baris.append(f"  «{asli}» ketemu di kitab {rinci} (maksimal {maks} kitab per teks)")
    if rusak:
        baris.append("  jejak belum lengkap: " + ", ".join(rusak) + "; hasil hanya dari kitab yang berhasil dibaca.")
    return baris


def susunan_bagian(pd, q, maks=50, cocok=None):
    """Tiap susunan letak [(awal, akhir)] bagian-bagian q di pd: bagian berikutnya yang terdekat dan lolos `cocok`,
    kalau diberikan (halaman/batas kata); calon yang ditolak tidak menutupi kemunculan sah sesudahnya."""
    def berikut(i, awal):
        j = pd.find(q[i], awal)
        while j >= 0 and cocok is not None and not cocok(i, j, j + len(q[i])):
            j = pd.find(q[i], j + 1)
        return j
    j = berikut(0, 0)
    while j >= 0 and maks:
        letak, k = [(j, j + len(q[0]))], j + len(q[0])
        for i, b in enumerate(q[1:], 1):
            n = berikut(i, k)
            if n < 0:
                return
            letak.append((n, n + len(b))); k = n + len(b)
        yield letak
        maks -= 1
        j = berikut(0, j + 1)
