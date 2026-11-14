# SPDX-License-Identifier: AGPL-3.0-or-later
"""CLI diagram menjaga PNG lama ketika renderer gagal dan melanjutkan diagram lain."""
import contextlib
import io
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'mesin'))
import diagram


class DiagramCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='bahts-uji-diagram-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(REPO / 'mesin', self.root / 'mesin', ignore=shutil.ignore_patterns('__pycache__', '_tmp'))
        self.folder = self.root / 'uji'
        self.folder.mkdir()
        (self.folder / 'naskah.txt').write_text('@judul: Uji\n', encoding='utf8')
        self.png_asli = (REPO / 'contoh/jebakan/gambar.png').read_bytes()
        self.sumber('a', png=self.png_asli)

    def sumber(self, nama, png=None):
        mmd = self.folder / (nama + '.mmd')
        mmd.write_text('flowchart LR\n  A --> B\n', encoding='utf8')
        if png is not None:
            hasil = mmd.with_suffix('.png')
            hasil.write_bytes(png)
            os.utime(hasil, ns=(1_000_000_000, 1_000_000_000))
        return mmd

    def cli(self, renderer):
        class Keluaran(io.StringIO):
            def reconfigure(self, **kw):
                pass
        out, err = Keluaran(), Keluaran()
        skrip = self.root / 'mesin/bahts.py'
        with patch.object(sys, 'argv', [str(skrip), 'diagram', str(self.folder)]), \
                patch.object(diagram.shutil, 'which', return_value='npx-tiruan'), \
                patch.object(diagram, 'browser', return_value='chromium-tiruan'), \
                patch.object(diagram.subprocess, 'run', side_effect=renderer), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                runpy.run_path(str(skrip), run_name='__main__')
                kode = 0
            except SystemExit as e:
                kode = e.code or 0
        return kode, out.getvalue() + err.getvalue()

    def test_renderer_gagal_menjaga_png_lama_dan_melanjutkan(self):
        self.sumber('b')
        def renderer(argumen, **kw):
            sumber = Path(argumen[argumen.index('-i') + 1])
            tujuan = Path(argumen[argumen.index('-o') + 1])
            if sumber.stem == 'a':
                tujuan.write_bytes(b'PNG-separuh')
                return subprocess.CompletedProcess(argumen, 1, '', 'Error: gagal render')
            tujuan.write_bytes(self.png_asli)
            return subprocess.CompletedProcess(argumen, 0, '', '')
        kode, pesan = self.cli(renderer)
        self.assertEqual(kode, 1, pesan)
        self.assertEqual((self.folder / 'a.png').read_bytes(), self.png_asli)
        self.assertEqual((self.folder / 'b.png').read_bytes(), self.png_asli)
        self.assertIn('GAGAL', pesan)
        self.assertIn('jadi', pesan)
        self.assertEqual(list(self.folder.glob('*.part')), [])

    def test_renderer_timeout_menjaga_png_lama_dan_melanjutkan(self):
        self.sumber('b')
        def renderer(argumen, **kw):
            sumber = Path(argumen[argumen.index('-i') + 1])
            tujuan = Path(argumen[argumen.index('-o') + 1])
            if sumber.stem == 'a':
                tujuan.write_bytes(b'PNG-separuh')
                raise subprocess.TimeoutExpired(argumen, kw['timeout'])
            tujuan.write_bytes(self.png_asli)
            return subprocess.CompletedProcess(argumen, 0, '', '')
        kode, pesan = self.cli(renderer)
        self.assertEqual(kode, 1, pesan)
        self.assertEqual((self.folder / 'a.png').read_bytes(), self.png_asli)
        self.assertEqual((self.folder / 'b.png').read_bytes(), self.png_asli)
        self.assertNotIn('Traceback', pesan)
        self.assertEqual(list(self.folder.glob('*.part')), [])

    def test_hasil_kosong_tidak_menggantikan_png_lama(self):
        def renderer(argumen, **kw):
            Path(argumen[argumen.index('-o') + 1]).write_bytes(b'')
            return subprocess.CompletedProcess(argumen, 0, '', '')
        kode, pesan = self.cli(renderer)
        self.assertEqual(kode, 1, pesan)
        self.assertEqual((self.folder / 'a.png').read_bytes(), self.png_asli)
        self.assertEqual(list(self.folder.glob('*.part')), [])

    def test_hasil_berhasil_diterbitkan_sekali_dan_tidak_dirender_ulang(self):
        baru = self.png_asli + b'baru'
        def renderer(argumen, **kw):
            Path(argumen[argumen.index('-o') + 1]).write_bytes(baru)
            return subprocess.CompletedProcess(argumen, 0, '', '')
        kode, pesan = self.cli(renderer)
        self.assertEqual(kode, 0, pesan)
        self.assertEqual((self.folder / 'a.png').read_bytes(), baru)
        kode, pesan = self.cli(lambda *a, **kw: self.fail('PNG baru dirender ulang'))
        self.assertEqual(kode, 0, pesan)
        self.assertIn('tetap', pesan)
        self.assertEqual(list(self.folder.glob('*.part')), [])


if __name__ == '__main__':
    unittest.main()
