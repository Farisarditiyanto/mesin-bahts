# SPDX-License-Identifier: AGPL-3.0-or-later
"""`diagram <folder>`: tiap berkas Mermaid (*.mmd) di folder bahts dirender jadi PNG bernama sama, untuk dicetak
dengan «#G nama.png | keterangan». Yang dirakit hanya PNG-nya, jadi `cek` dan `rakit` tetap jalan tanpa internet.

Perenderan memakai mermaid-cli resmi (Node.js + browser Chromium). Penggantinya yang tanpa browser (mmdr, merman,
mermaid-rs-renderer) dicoba November 2026: huruf Arab di sana tercetak renggang dan label bergaris bawah terbalik
arahnya, jadi tidak dipakai. Atribut erDiagram Mermaid belum menerima huruf non-Latin (mermaid-js/mermaid#5800):
tulis kolomnya dengan nama teknis Latin, nama entitas Arab di dalam tanda petik.
"""
import json, os, shutil, subprocess, tempfile
from pathlib import Path
from berkas import sementara

MERMAID_CLI = "@mermaid-js/mermaid-cli@11.4.2"  # versi dikunci: hasil sama di komputer lain
# Tema hitam-putih untuk cetak; huruf Arab sama dengan matan bahts (cadangan: Arial)
# Jarak antarkotak dirapatkan: diagram dikecilkan rakit agar muat di halaman (paling tinggi 70%), jadi makin rapat makin
# besar hurufnya di kertas (jarak bawaan Mermaid 50 px membuat huruf diagram tinggi ±5 pt di PDF)
KONFIG = {"theme": "neutral", "themeVariables": {"fontFamily": "Traditional Arabic, Arial, sans-serif", "fontSize": "18px"},
          "flowchart": {"htmlLabels": True, "curve": "basis", "nodeSpacing": 22, "rankSpacing": 28, "padding": 6},
          "state": {"nodeSpacing": 22, "rankSpacing": 28}, "er": {"entityPadding": 8}}
SKALA = 3  # PNG tajam di PDF (Word tidak mengecilkan resolusi saat ekspor untuk cetak)


def browser():
    """Jalur Chrome/Edge/Chromium untuk mermaid-cli: BAHTS_CHROME, lalu yang terpasang, lalu Chromium Playwright."""
    calon = [os.environ.get("BAHTS_CHROME", "")]
    for akar in (os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", ""), os.environ.get("LOCALAPPDATA", "")):
        if akar:
            calon += [Path(akar) / "Google/Chrome/Application/chrome.exe", Path(akar) / "Microsoft/Edge/Application/msedge.exe"]
    pw = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    if os.environ.get("LOCALAPPDATA") and pw.is_dir():
        calon += sorted(pw.glob("chromium-*/chrome-win*/chrome.exe"), reverse=True)
    calon += [shutil.which(n) or "" for n in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge")]
    calon.append("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    return next((str(Path(c)) for c in calon if c and Path(c).is_file()), None)


def render(folder):
    """Render tiap *.mmd yang PNG-nya belum ada atau lebih tua. Kembalikan jumlah yang gagal."""
    mmd = sorted(folder.glob("*.mmd"))
    if not mmd:
        print(f"Tidak ada berkas .mmd di {folder}. Tulis diagram Mermaid sebagai <nama>.mmd di folder bahts itu.")
        return 0
    npx = shutil.which("npx")
    if not npx:
        print("BELUM  Node.js (npx) tidak ditemukan: pasang Node.js LTS (Windows: winget install OpenJS.NodeJS.LTS), lalu ulangi.")
        return len(mmd)
    chrome = browser()
    if not chrome:
        print("BELUM  browser Chromium tidak ditemukan: pasang Google Chrome atau Microsoft Edge, atau tulis jalur chrome.exe "
              "di variabel lingkungan BAHTS_CHROME, lalu ulangi.")
        return len(mmd)
    gagal = 0
    with tempfile.TemporaryDirectory(prefix="bahts-diagram-") as t:
        konfig, pup = Path(t) / "mermaid.json", Path(t) / "puppeteer.json"
        konfig.write_text(json.dumps(KONFIG), encoding="utf8")
        pup.write_text(json.dumps({"executablePath": chrome}), encoding="utf8")
        for m in mmd:
            png = m.with_suffix(".png")
            if png.exists() and png.stat().st_mtime >= m.stat().st_mtime:
                print(f"tetap   {png.name} (lebih baru dari {m.name})")
                continue
            try:
                with sementara(png) as part:
                    hasil = Path(t) / png.name
                    r = subprocess.run([npx, "-y", MERMAID_CLI, "-i", str(m), "-o", str(hasil), "-b", "white",
                                        "-s", str(SKALA), "-c", str(konfig), "-p", str(pup), "-q"],
                                       capture_output=True, text=True, encoding="utf8", errors="replace", timeout=600)
                    if r.returncode or not hasil.exists() or not hasil.stat().st_size:
                        pesan = (r.stderr or r.stdout).strip().splitlines()
                        raise OSError(next((x for x in pesan if "Error" in x or "error" in x),
                                           pesan[-1] if pesan else "renderer tidak menghasilkan PNG"))
                    shutil.copyfile(hasil, part)
            except (OSError, subprocess.TimeoutExpired) as e:
                gagal += 1
                pesan = "renderer kehabisan waktu" if isinstance(e, subprocess.TimeoutExpired) else str(e)
                print(f"GAGAL   {m.name}: {pesan}")
            else:
                print(f"jadi    {png.name}  ->  cetak dengan «#G {png.name} | keterangan»")
    return gagal
