# SPDX-License-Identifier: AGPL-3.0-or-later
"""Teks mushaf (riwayat Hafs) yang dicetak {Q:} dan dipakai layanan tafsir."""
import functools, json

from dasar import HERE


@functools.cache
def mushaf():
    """{«surat:ayat»: teks ayat}, urut mushaf; dibaca saat pertama dipakai (±1 MB), bukan saat modul dimuat."""
    return json.loads((HERE / "quran_hafs_v22.json").read_text(encoding="utf8"))
