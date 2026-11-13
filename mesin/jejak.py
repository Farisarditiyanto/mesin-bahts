# SPDX-License-Identifier: AGPL-3.0-or-later
"""`cek --jejak`: kutipan yang tidak ketemu di kitab buktinya dicari di kitab lain yang sudah diunduh. Hanya petunjuk,
bukan putusan."""
import difflib, sqlite3, zlib

import norma
import shamela
from dasar import ELIPSIS
from kitab_lokal import halaman_di, rangkaian_kitab, tempat_kitab

# `cek --jejak`, kutipan yang lafaznya sedikit berbeda dengan kitab; satuannya huruf `padat`
MIRIP_BENIH = 14  # panjang potongan kutipan yang harus ada persis di kitab
MIRIP_KUTIPAN = 30  # kutipan lebih pendek dari ini tidak dicari: yang pendek mirip di mana-mana
MIRIP_PANJANG = 300  # kutipan lebih panjang dari ini tidak dicari: waktu membandingkan = kuadrat panjangnya
MIRIP_MIN = 0.9  # bagian huruf yang harus sama (lihat `_mirip_kitab`)
MIRIP_CALON = 20  # tempat paling banyak tiap benih (benih umum, mis. basmalah, ada ribuan kali)
MIRIP_LONGGAR = 12  # tempat yang berjarak kurang dari ini dibandingkan sekali

# Indeks penyaring (SQLite FTS5, tokenizer trigram): kitab yang PASTI tidak memuat kutipan tidak dibuka. Hanya menyaring:
# tiap calon tetap dicari dengan cara di bawah, jadi hasilnya sama dengan mencari di semua kitab. Teksnya `bait` yang
# dibaca latin-1 (satu huruf satu karakter); detail=none: kecil (±0,7 bait per huruf), tanpa kueri frasa, jadi syaratnya
# «semua trigram potongan ini ada» (perlu, belum cukup).
FTS_POTONG = 4000  # huruf per baris indeks: baris besar memuat hampir semua trigram, jadi tidak menyaring apa-apa
FTS_TUMPANG = 500  # baris berurutan bertumpang sebanyak ini; potongan kueri dipotong sepanjang ini (pasti di satu baris)
FTS_TRIGRAM = 64  # trigram paling banyak tiap potongan kueri (sebagian trigram tetap syarat perlu)


def _bagian_cari(teks):
    """Semua bagian berhuruf Arab (`padat`), urut seperti di naskah, termasuk bagian pendek di samping ayat.
    Tidak boleh membuang satu bagian lalu menunjuk kitab yang hanya memuat sisanya."""
    return [p for b in ELIPSIS.split(teks) if (p := norma.padat(b))]


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
                terbaik = nilai, ("-" if juz is None else juz), halaman_di(ruas, a, z), tanda
    return terbaik


def _berkas_indeks():
    # VERSI = sidik norma.py (teks `padat` berubah) dan ukuran baris: salah satunya berubah, indeks dibuat ulang
    return shamela.ROOT / f"jejak-{norma.VERSI}-{FTS_POTONG}-{FTS_TUMPANG}.sqlite"


def _indeks(semua):
    """(sambungan, kitab yang terindeks) indeks penyaring yang sudah diselaraskan dengan kitab lokal; (None, set())
    kalau SQLite ini tidak punya FTS5/trigram (SQLite < 3.34) atau berkasnya tidak bisa dipakai: semua kitab dibaca.
    Kitab baru atau yang berkasnya berubah diindeks sekarang; yang dihapus dibuang. Kitab yang gagal dibaca tidak
    terindeks, jadi tetap dibaca (dan dilaporkan rusak) seperti tanpa indeks."""
    f = _berkas_indeks()
    for lama in shamela.ROOT.glob("jejak-*.sqlite*"):  # versi norma.py lama
        if not lama.name.startswith(f.name):
            try:
                lama.unlink()
            except OSError:
                pass
    try:
        db = sqlite3.connect(f, timeout=600)
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS isi USING fts5(sid UNINDEXED, teks, "
                   "tokenize='trigram case_sensitive 1', detail='none')")
        db.execute("CREATE TABLE IF NOT EXISTS kitab(sid INTEGER PRIMARY KEY, sidik TEXT)")
        ada = dict(db.execute("SELECT sid, sidik FROM kitab"))
    except sqlite3.Error:
        return None, set()
    for sid in set(ada) - set(semua):
        with db:
            db.execute("DELETE FROM isi WHERE sid = ?", (sid,))
            db.execute("DELETE FROM kitab WHERE sid = ?", (sid,))
    baru = [sid for sid in semua if ada.get(sid) != shamela._sidik(sid)]
    if baru:
        print(f"jejak: menyiapkan indeks pencarian {len(baru)} kitab (sekali saja; ±0,5 detik per kitab) …", flush=True)
    for sid in baru:
        try:
            pd = shamela._cache(sid)
            with db:
                db.execute("DELETE FROM isi WHERE sid = ?", (sid,))
                db.execute("DELETE FROM kitab WHERE sid = ?", (sid,))
                for t in pd.teks:
                    t = t.decode("latin-1")
                    db.executemany("INSERT INTO isi(sid, teks) VALUES (?, ?)",
                                   ((sid, t[a:a + FTS_POTONG + FTS_TUMPANG]) for a in range(0, len(t), FTS_POTONG)))
                db.execute("INSERT INTO kitab VALUES (?, ?)", (sid, shamela._sidik(sid)))
        except (OSError, EOFError, ValueError, TypeError, AttributeError, KeyError, IndexError, zlib.error, sqlite3.Error):
            pass
        finally:
            shamela.lepas()
    return db, {sid for (sid,) in db.execute("SELECT sid FROM kitab")}


def _syarat(potongan):
    """Kueri FTS5 «semua trigram potongan ini» (padat), atau None kalau terlalu pendek untuk menyaring."""
    p = norma.bait(potongan[:FTS_TUMPANG]).decode("latin-1")
    tri = list(dict.fromkeys(p[k:k + 3] for k in range(len(p) - 2)))
    if not tri:
        return None
    tri = tri[::max(1, len(tri) // FTS_TRIGRAM)]
    return "(" + " AND ".join(f'"{x}"' for x in tri) + ")"


def _calon(db, syarat, semua_):
    """Kitab terindeks yang mungkin memuat potongan-potongan itu (semua_: tiap potongan, boleh di baris berbeda; selain
    itu: salah satunya); None = tidak tersaring. Kitab yang tidak terindeks selalu ikut (dicek pemanggil)."""
    if db is None:
        return None
    ada = [x for x in syarat if x]
    if not ada or not semua_ and len(ada) < len(syarat):
        return None
    tanya = lambda q: {sid for (sid,) in db.execute("SELECT DISTINCT sid FROM isi WHERE isi MATCH ?", (q,))}
    if not semua_:
        return tanya(" OR ".join(ada))
    hasil = tanya(ada[0])
    for x in ada[1:]:
        hasil &= tanya(x)
    return hasil


def _rapid(rangkaian, q):
    """«Paling mirip» tanpa benih (rapidfuzz partial_ratio_alignment): untuk kutipan yang tiap potongan MIRIP_BENIH
    hurufnya kena salah ketik, sehingga `_mirip_kitab` tidak punya titik mulai. (nilai, juz, halaman, tanda) atau None."""
    from rapidfuzz import fuzz
    qs, terbaik = q.decode("latin-1"), None  # q: `bait`
    for juz, tanda, teks, ruas in rangkaian:
        r = fuzz.partial_ratio_alignment(qs, teks.decode("latin-1"), score_cutoff=MIRIP_MIN * 100)
        if r is not None and (terbaik is None or r.score / 100 > terbaik[0]):
            terbaik = r.score / 100, ("-" if juz is None else juz), halaman_di(ruas, r.dest_start, r.dest_end), tanda
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
    db, terindeks = _indeks(semua)
    for e in cari.values():
        padat_ = [norma.teks(b) for b in e["bagian"]]
        e["calon"] = _calon(db, [_syarat(b) for b in padat_], True)
        q = padat_[0]
        e["calon_mirip"] = _calon(db, [_syarat(q[k:k + MIRIP_BENIH])
                                       for k in range(0, len(q) - MIRIP_BENIH + 1, MIRIP_BENIH)], False)
    if db is not None:
        db.close()

    def mungkin(calon, sid):
        return calon is None or sid in calon or sid not in terindeks
    rusak = []
    for sid in semua:
        aktif = [e for e in cari.values() if len(e["dapat"]) < maks and str(sid) not in e["tertuju"]]
        for e in [e for e in aktif if not mungkin(e["calon"], sid)]:
            e["dibaca"] += 1  # indeks memastikan kitab ini tidak memuatnya: sama dengan dibaca tanpa hasil
            aktif.remove(e)
        # kutipan ber-... tidak: satu bagian yang mirip tidak berkata apa-apa tentang bagian lain (bisa karangan)
        # kutipan panjang juga tidak: membandingkan seluruhnya terlalu lama, menilai sebagiannya menyesatkan
        longgar = [e for e in cari.values() if not e["dapat"] and len(e["bagian"]) == 1
                   and MIRIP_KUTIPAN <= len(e["bagian"][0]) <= MIRIP_PANJANG and mungkin(e["calon_mirip"], sid)]
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
    for e in cari.values():  # tiap potongan benih kena salah ketik: cari tanpa benih, hanya di kitab yang dirujuk
        if e["dapat"] or e["mirip"] or len(e["bagian"]) != 1 or not MIRIP_KUTIPAN <= len(e["bagian"][0]) <= MIRIP_PANJANG:
            continue
        for sid in sorted(int(x) for x in e["tertuju"] if x.isdigit() and int(x) in semua):
            try:
                if t := _rapid(rangkaian_kitab(sid), e["bagian"][0]):
                    e["mirip"].append((t[0], sid, *t[1:]))
            except (OSError, EOFError, ValueError, TypeError, AttributeError, KeyError, IndexError, zlib.error) as x:
                rusak.append(f"kitab {sid} ({type(x).__name__})")
            finally:
                shamela.lepas()
                rangkaian_kitab.cache_clear()
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


