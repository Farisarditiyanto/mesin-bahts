# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression checks through the experimental CLIs, with no Word rendering."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(os.environ.get("BAHTS_EXPERIMENT_TEST_ROOT", Path(__file__).resolve().parent))


class Safety(unittest.TestCase):
    def run_ram(self, args, stdin=None):
        return subprocess.run([sys.executable, str(HERE / "ram.py"), *args], input=stdin,
                              capture_output=True, text=True, encoding="utf8")

    def test_missing_folder_rejected_before_worker(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "result.json"
            p = self.run_ram(["--scope", "cli", "--folder", str(Path(d) / "absent"), "--library", "absent.pyd", "--out", str(out)])
            self.assertEqual(p.returncode, 2)
            self.assertFalse(out.exists())

    def test_cli_scope_requires_input(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "result.json"
            p = self.run_ram(["--scope", "cli", "--library", "absent.pyd", "--out", str(out)])
            self.assertEqual(p.returncode, 2)
            self.assertFalse(out.exists())

    def test_outside_manuscript_rejected_before_worker(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "naskah.txt").write_text("test", encoding="utf8")
            out = folder / "result.json"
            p = self.run_ram(["--scope", "cli", "--folder", d, "--library", "absent.pyd", "--out", str(out)])
            self.assertEqual(p.returncode, 2)
            self.assertFalse(out.exists())

    def test_systemexit_text_never_becomes_public_status(self):
        p = self.run_ram(["--worker"], json.dumps({"mode": "python", "kind": "cli", "folder": "__nonexistent_experiment__"}))
        self.assertEqual(p.returncode, 0)
        status = json.loads(p.stdout)["status"]
        self.assertTrue(type(status) is int, "status must be numeric, never contain an error message")
        self.assertEqual(status, 1)

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell ownership guard")
    def test_existing_word_record_stays_intact(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            record = folder / "rakit.word"
            record.write_bytes(b"ownership-sentinel")
            lock = folder / "rakit.kunci"
            p = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "docx_export.ps1"),
                                "-InputDocx", str(folder / "missing.docx"), "-OutputPdf", str(folder / "out.pdf"), "-Kunci", str(lock)], capture_output=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertTrue(record.exists(), "existing ownership record must not be removed")
            self.assertEqual(record.read_bytes(), b"ownership-sentinel")
            self.assertFalse((folder / "out.pdf").exists())
            lock.unlink()  # Proves the failed call released its lock.


if __name__ == "__main__":
    unittest.main()
