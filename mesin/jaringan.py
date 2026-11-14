# SPDX-License-Identifier: AGPL-3.0-or-later
"""Transport layanan luar: pengalihan aman, percobaan ulang, jatah, dan unduhan utuh."""
import http.client, time, urllib.error, urllib.parse, urllib.request

from berkas import sementara

UA = {"User-Agent": "curl/8"}
# unduhan yang putus/gagal di jaringan (bukan nomor kitab yang salah)
GAGAL_JARINGAN = (urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError)
COBA = 3  # tiap kitab dicoba sebanyak ini kalau unduhannya putus
SEMENTARA = (500, 502, 503)  # jawaban HTTP yang biasanya hilang sendiri (504 tidak: OpenAlex memakainya untuk «pencarian terlalu berat»)


class _AlihAman(urllib.request.HTTPRedirectHandler):
    """Kunci hanya ikut pengalihan di asal yang sama (protokol, nama host, dan port)."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        baru = super().redirect_request(req, fp, code, msg, headers, newurl)

        def asal(url):
            u = urllib.parse.urlsplit(url)
            port = u.port if u.port is not None else {"http": 80, "https": 443}.get(u.scheme)
            return u.scheme, u.hostname, port

        if baru is not None and asal(req.full_url) != asal(baru.full_url):
            baru.remove_header("Authorization")
        return baru


def buka(url, data=None, kepala=UA, waktu=60, coba=3):
    """Satu pintu permintaan ke layanan luar (temukan, hadits, dirasat, font). Galat sementara (koneksi putus/direset,
    SSL terputus, waktu habis, HTTP 500/502/503) dicoba lagi sampai `coba` kali dengan jeda 1, 2, 4 detik.
    Penolakan lain (4xx, 429 jatah habis, 504) langsung dilempar: artinya beda per layanan, pemanggil yang menjelaskan."""
    pembuka = urllib.request.build_opener(_AlihAman)
    for i in range(coba):
        try:
            return pembuka.open(urllib.request.Request(url, data, kepala), timeout=waktu)
        except urllib.error.HTTPError as e:
            if e.code not in SEMENTARA or i == coba - 1:
                raise
        except GAGAL_JARINGAN:
            if i == coba - 1:
                raise
        time.sleep(2 ** i)


SABAR_JATAH = 30  # detik; layanan minta menunggu lebih lama dari ini = jatah pencarian habis, bukan sekadar terlalu cepat


def tunggu_jatah(e, ulang, habis):
    """HTTP 429 dari `buka` = jatah permintaan layanan sementara habis (turath, alminasa): tunggu sesuai retry-after
    (bawaan 11 detik), lalu pemanggil mengulang sekali. Diminta menunggu lebih dari SABAR_JATAH, atau sudah diulang =
    jatahnya habis: SystemExit(habis), «{menit}» di dalamnya = perkiraan menit sampai terbuka lagi. Galat lain dilempar lagi."""
    if e.code != 429:
        raise e
    tunggu = e.headers.get("retry-after") or ""
    tunggu = int(tunggu) if tunggu.isdigit() else 11  # layanan membatasi permintaan beruntun dan jumlah pencarian
    if tunggu > SABAR_JATAH or not ulang:
        raise SystemExit(habis.format(menit=tunggu // 60 + 1))
    time.sleep(tunggu + 1)


def unduh(url, tujuan, buka):
    """Unduh ke nama sementara unik, lalu ganti tujuan kalau utuh; dua unduhan tidak berbagi penulisan."""
    with sementara(tujuan) as part:
        n = 0
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as resp, buka(part) as o:
            while chunk := resp.read(1 << 20):
                o.write(chunk); n += len(chunk)
            janji = resp.headers.get("Content-Length")
        if janji and int(janji) != n:
            raise ConnectionError(f"unduhan terpotong: {n} dari {janji} byte ({tujuan.name})")


def unduh_kitab(nomor, ambil):
    """Unduh tiap nomor; ulangi kegagalan jaringan, bukan nomor salah atau penolakan HTTP tetap."""
    gagal = []
    for s in nomor:
        for coba in range(1, COBA + 1):
            try:
                ambil(s)
                break
            except LookupError as e:  # nomornya salah: diulang pun sama
                print(f"{s}: {e}"); gagal.append(str(s)); break
            except GAGAL_JARINGAN as e:
                tetap = isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500 and e.code != 429
                if tetap or coba == COBA:
                    print(f"{s}: GAGAL mengunduh, cek internet lalu ulangi ({e!r})"); gagal.append(str(s)); break
                print(f"{s}: unduhan putus ({e!r}); mencoba lagi ({coba + 1}/{COBA}) ...", flush=True)
                time.sleep(5 * coba)
    return gagal
