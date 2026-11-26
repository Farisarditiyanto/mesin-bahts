# Mesin Bahts

**Language:** English · [Indonesia](README.id.md) · [العربية](README.ar.md)

**Mesin Bahts ("bahth engine") is a toolkit for coding agents (Claude Code, Codex, OpenCode and similar) to write a بحث, an Arabic-language Islamic studies research paper: every quotation is checked against the cited page of the Shamela library (المكتبة الشاملة) book, then the manuscript is built into Word and PDF.**

<img src="dok/banner.jpg" width="100%" alt="A student in a hijab in a library with books flying around her">

[![tests](https://github.com/Farisarditiyanto/mesin-bahts/actions/workflows/tes.yml/badge.svg)](https://github.com/Farisarditiyanto/mesin-bahts/actions/workflows/tes.yml)
[![release](https://img.shields.io/github/v/release/Farisarditiyanto/mesin-bahts?label=release)](https://github.com/Farisarditiyanto/mesin-bahts/releases)
[![license](https://img.shields.io/badge/license-AGPLv3%2B-blue)](LICENSE)

The agent writes the bahts (paper) in `naskah.txt`, one folder per paper. `cek` rejects any quotation that is not on the cited book page, then `rakit` turns the manuscript into Word and PDF.

This README is a map for agents. The user only pastes this repository's link into a [coding agent](#agents-and-connectors), then answers its questions.

| | |
|---|---|
| For | coding agents that can run commands; the end user is a student writing a bahts |
| Working rules | [`AGENTS.md`](AGENTS.md) (in Indonesian) |
| Command entry point | `python mesin/bahts.py <perintah>` |
| Flow | `periksa` → `baru` → gather sources → `ambil` → write `naskah.txt` & `pustaka` → `cek` (`dirasat-cek` if needed) → `rakit` → reviewer (`peta`, `bukti`, `pratinjau`) → `cek` and `rakit` again (`tahap` tracks state) |
| MCP connectors | `shamela` (required), `qurangallery`, `turath`, `hadithunlocked`, `tafsir`, `quran`, `qaf` |
| Requirements | listed by `python mesin/bahts.py periksa`; `rakit` needs Windows + Microsoft Word |
| Version | [releases](https://github.com/Farisarditiyanto/mesin-bahts/releases), [`CHANGELOG.md`](CHANGELOG.md) |
| License | AGPLv3 or later ([`LICENSE`](LICENSE)) |

Commands, markers and program output are in Indonesian and are quoted here as they are typed or printed. Words used below: bahts = بحث (research paper), naskah = manuscript, kitab = book, `GAGAL` = failed, perhatian = warning, `BELUM` = not yet, `BERIKUTNYA` = next step.

## Getting started

1. Read all of [`AGENTS.md`](AGENTS.md). Those are the working rules. For a new user, start with [`dok/pemakai-baru.md`](dok/pemakai-baru.md).
2. Run `python mesin/bahts.py periksa` (Linux/macOS: `python3`). Fix each `BELUM` line with the command it names.
3. Make sure the `shamela` connector is connected: the tool `shamela_search_phrase` exists. How to register it and sign in, per agent: `dok/pemakai-baru.md` step 4.
4. Later session, or you do not know how far a bahts has got: `python mesin/bahts.py tahap <folder>`. Follow the `BERIKUTNYA` line.

The repository is not on the computer yet: run this block from the user's Documents folder, before step 2. Target folder and the way without `git`: `dok/pemakai-baru.md` step 1.

```bash
git clone https://github.com/Farisarditiyanto/mesin-bahts
cd mesin-bahts
python mesin/bahts.py periksa
```

Computer requirements and how to fix them are in one place: `python mesin/bahts.py periksa`. `rakit` needs Windows + desktop Microsoft Word; Linux/macOS can write and run `cek`, without Word and PDF. Gathering sources needs the `shamela` connector (a shamela.link account); الدراسات السابقة (previous studies) needs an OpenAlex key (`dok/pemakai-baru.md` step 6).

### Agents and connectors

| Agent | Reads the connector list from |
|---|---|
| [Claude Code](https://claude.com/claude-code) (also the Code tab of the Claude app) | `.mcp.json`, plus the Connectors menu of the Claude app |
| [OpenCode](https://opencode.ai) (free) | `opencode.json` |
| [Command Code](https://commandcode.ai) | `.mcp.json`, plus a local `shamela` entry that carries the `clientId` |
| Codex (CLI and app) | registered by the agent |
| [Hermes Agent](https://hermes-agent.nousresearch.com) (free) | registered by the agent |

- Commands to register `shamela` and sign in, per agent: `dok/pemakai-baru.md` step 4 (the only place).
- Free models take wrong steps more often, so the step 5 reviewer matters even more.
- Connectors: `shamela` is required; `qurangallery`, `turath`, `hadithunlocked`, `tafsir`, `quran` need no account; `qaf` (search by meaning) needs a free Qaf account. What each is for and the fallback order: `dok/pemakai-baru.md` steps 4-5 and `AGENTS.md` «Alur kerja» (workflow) step 2. Test figures for each connector, including the official shamela.ws MCP that is deliberately not installed: [`dok/uji-riset.md`](dok/uji-riset.md).
- Every connector is only a signpost: the book is still downloaded with `ambil`, and the quotation must still pass `cek`.

### Tell the user

- The name on the cover is the user's name: the content is their responsibility. They need to ask their lecturer whether AI assistance is allowed.
- `cek` does not replace reading: ask the user to check their main quotations themselves.
- Some free models use the conversation to train their models.
- This project does not represent any campus.

### Limits

- Not for plain chat mode (Claude chat, ChatGPT): the agent must be able to run commands on the user's computer.
- Not a guarantee of content: `cek` only proves that the text is on that volume/page. The speaker, the chapter context and the quality of the source are judged by the step 5 reviewer (`AGENTS.md` «Alur kerja»).
- Not for papers in a language other than Arabic: page layout, references and الفهارس follow the guidelines for Arabic-language bahts ([Page standard](#page-standard)).
- Not a word processor: content is changed through `naskah.txt`, not through the `.docx`.
- Without Windows + Microsoft Word there is no Word or PDF output, and no Word substitute is used.

## How it works

| Step | Command | Result |
|---|---|---|
| Create the folder | `baru <folder> "<judul>"` | `naskah.txt` (outline), `riset.txt` |
| Find sources | connector `shamela_*`, `temukan`, `katalog`, `edisi`, `hadits`, `dirasat`; without internet: `tafsir <surat:ayat>`, `takhrij <id> <juz> <hal>`, `rawi <id> <juz> <hal>`, `akar <id> "<akar>"`; books not in Shamela: `waqfeya "<judul>"` | book number + volume/page (a pointer) |
| Download a book | `ambil <id>` or `ambil <folder>`; Waqfeya: `ambil w<nomor>` | `kitab/<id>/`, `kitab/waqfeya/w<nomor>/` |
| Publication data | `kartu <id>`, `pustaka <folder>` | first reference and المصادر draft from cited books |
| Read the text | `cari`, `teks`, `bab`, `halaman` | local text to copy exactly |
| Check | `cek <folder>` (`--jejak` for quotations that are not found); online DOI check: `dirasat-cek <folder>` | `GAGAL: n`, perhatian, `NASKAH_SHA256` |
| Reviewer | optional `peta <folder>`, `bukti <folder> [awal-akhir]` | offline structure/source/claim-arc overview ([`dok/audit.md`](dok/audit.md)), the page text around each footnote (Shamela, Waqfeya, and research PDFs), and body paragraphs without a footnote |
| Build | `rakit <folder> [--fasl n]` (Windows + Word) | `.docx` + `.pdf` (cover, footnotes, المصادر والمراجع, الفهارس), `HALAMAN_ISI`, `HALAMAN` |
| Status | `tahap <folder>` | `NASKAH=`, `HASIL=`, `RAKIT=`, `BERIKUTNYA` |
| Diagrams | `diagram <folder>` (Node.js + Chrome/Edge) | each `<nama>.mmd` (Mermaid) becomes `<nama>.png`, printed through `#G` |
| Visual preview | `pratinjau <folder> [halaman]` | built PDF pages as 2×2 PNG grids in TEMP (or a single page) for layout review |

Every command = `python mesin/bahts.py <perintah>`. Full list with arguments: `python mesin/bahts.py`. List of manuscript markers (`#F`, `{Q:}`, `{H:}`, `@format`, …): `python mesin/bahts.py tanda`. A sample manuscript that passes `cek`: [`contoh/naskah.txt`](contoh/naskah.txt) (`ambil 11223`, then `cek contoh`).

### What `cek` proves

- Every quotation in quotation marks must be readable on the volume/page of the cited book. Not there, or without an address = `GAGAL`.
- The volume/page printed in the footnote is matched against the address of its evidence. The book name in the footnote must agree with its evidence, and the hadith grade in a takhrij must be readable on the evidence page. A quotation in the حاشية المحقق (editor's footnote), or one that the book introduces with «قال …» of someone else, becomes a perhatian.
- Verses and numbers inside a quotation are matched on whole-word occurrences on the evidence page; a number from a neighbouring page does not count.
- Verses are printed from the Hafs mushaf in Uthmani script (`mesin/quran_hafs_v22.json`) through `{Q:surah:ayat}`. A verse typed by hand inside ﴿…﴾ with a «سورة …» reference = `GAGAL`; without a reference = perhatian. A verse without ﴿…﴾ after «قال الله تعالى» that is referenced «سورة …» is also `GAGAL`.
- `<<sid|juz|hal|#123>>` passes only if 123 is a hadith head at the start of a line on that page («123 - حدثنا», «36 - (123)», «(123) - حدثنا»); verse numbers and note numbers are rejected. This proves the number is there, not the wording.
- A takhrij «رقم الحديث (123)، 4/56.» followed directly by evidence: the number must be a hadith head around that page, and the evidence wording must be in the hadith with that number. The result is a perhatian, not `GAGAL`.
- `cek --jejak`: a quotation that is not found is searched for in the other downloaded books, at most 3 books per text; slightly different wording is pointed out as «Paling mirip»; a quotation that continues onto the next page is shown with its range (ص21-22). A hint only. A book that cannot be read is skipped with the warning «jejak belum lengkap». The first search prepares the book text, so it can take long.
- Sources outside Shamela: `<<luar|berkas.pdf|hal>>` only gets its page pointed out, it is never passed. Waqfeya books `<<w…|berkas|hal>>`: `cek` does not judge the wording because the OCR gets letters wrong; the reviewer reads it in the scan. `GAGAL` only if the marker is malformed, the book is not downloaded, the file or page does not exist, or a quotation of at least 25 letters with under 60% OCR match on the cited page appears verbatim on another page.
- Ways of quoting (perhatian, not `GAGAL`): a sentence outside quotation marks with 8 or more consecutive words identical to its evidence page, a paraphrase without «انظر:», a verbatim quotation only introduced by «قال …:» but referenced with «انظر:», and a quotation longer than 60 words. The word limits are repository rules. Whether a paraphrase is faithful to its evidence page is not judged: evidence with a fragment only proves the fragment.
- A takhrij outside the Sahihayn without a grade (and without «ولم أقف على حكم …») = `GAGAL`.
- Every perhatian must be handled: each line is printed with its code («! 3f9a2c baris …»), then fixed in the manuscript, or accepted with `terima <kode> <alasan>` in `riset.txt` if it really cannot be fixed. While any is unhandled, `tahap` prints `NASKAH=PERHATIAN` and `rakit` prints «BELUM SELESAI». A perhatian from `riset.txt` cannot be accepted. The reason is not judged by the machine: that is the step 5 reviewer's job.
- What `cek` cannot judge (the speaker, whether the book is mu'tamad, quotations without a footnote): the end of «Alur kerja» in `AGENTS.md`. That is the step 5 reviewer's job.

`cek` and `rakit` use neither the internet nor the connectors: their result must be the same without a network.

### Page standard

- The basis is «[القواعد المنظمة لتسجيل الرسالة العلمية وكتابتها وطباعتها وتقديمها](https://units.imamu.edu.sa/colleges/cmc/AcademicDepts/SiteAssets/Pages/d_j_e_p/%D8%A7%D9%84%D9%82%D9%88%D8%A7%D8%B9%D8%AF%20%D8%A7%D9%84%D9%85%D9%86%D8%B8%D9%85%D8%A9%20%D9%84%D8%AA%D8%B3%D8%AC%D9%8A%D9%84%20%D8%A7%D9%84%D8%B1%D8%B3%D8%A7%D9%84%D8%A9%20%D8%A7%D9%84%D8%B9%D9%84%D9%85%D9%8A%D8%A9.pdf)» (جامعة الإمام, Imam Muhammad ibn Saud Islamic University, 1442 AH) and the notes of the bahts class lecturer at معهد العلوم الإسلامية والعربية في جاكرتا. The origin of each rule: [`dok/standar.svg`](dok/standar.svg).
- The lecturer asks for another layout: see `AGENTS.md` «Sebelum tiap bahts» (`@format`, `@templat`, `@sampul`, `@spasi`, `@catatan_kaki`). In the user's folder do not change files in `mesin/`; a new profile in `mesin/format.json` is a change to the machine.
- Digits: the campus rules and the lecturer's notes do not name the kind of digits. The campus's official examples use ٠١٢٣ for page numbers, footnotes, references, years, verse numbers and فهرس: «[دليل إعداد وكتابة الرسائل العلمية](https://units.imamu.edu.sa/shis/sij/FilesLibrary/Documents/Guide%20to%20preparing%20and%20writing%20scientific%20theses.pdf)» (جامعة الإمام, second edition) and «[مجلة العلوم الشرعية](https://journals.imamu.edu.sa/index.php/jis)». So the PDF prints ٠١٢٣ in all those places, whatever digits are typed in the manuscript. Links and DOIs (`https://…`, `www.…`, `doi.org/…`, `10.xxxx/…`) are printed left-to-right as they are.
- The lecturer asks for 0123 → `@angka: latin`. Only the verse numbers in footnotes → `@angka_ayat: latin`.
- Latin letters inside Arabic text: neither source gives a size for them. The 1442 rules name only the Arabic typeface; the campus's [2022 guide](https://units.imamu.edu.sa/deanships/GRADUATE/circulations/Documents/Law3A.pdf) sets theses written in English in Times New Roman 14 (footnotes 12) against Sakkal Majalla 16 (footnotes 12) for Arabic ones. The machine's own choice: Latin words are printed in Times New Roman at the profile's `latin` size relative to the body, rounded up (`imam`: body 18 → 12, footnotes 14 → 10), because at the same size the Latin glyphs of Traditional Arabic are wide and look much larger than its Arabic letters.

## Repository

| Location | Contents |
|---|---|
| `mesin/bahts.py` | the only command entry point |
| `mesin/olah.py`, `naskah.py`, `cek_*.py`, and their helper modules | `cek`; what each file does: `AGENTS.md` «Letak kode `cek`» |
| `mesin/quran_hafs_v22.json`, `nama_surah.json` | mushaf text and surah names |
| `mesin/shamela.py` | book download, catalogue, `cari`, `teks`, `bab`, `halaman` |
| `mesin/turath.py` | turath.io client: `temukan`, `scan` |
| `mesin/jaringan.py` | transport for outside services, safe redirects, rate limits, and complete downloads |
| `mesin/hadits.py`, `dirasat.py` | takhrij pointers, previous studies and DOI/retraction verification (`dirasat-cek`) |
| `mesin/pustaka.py` | `#R` bibliography draft generator from cited books (`pustaka`) |
| `mesin/waqfeya.py` | Waqfeya books: catalogue, `ambil w…`, OCR, scan cut-outs (PDF/PNG) |
| `mesin/layanan.py` | `tafsir`, `takhrij`, `rawi`, and `akar` without internet (Shamela service tables in `kitab/_meta`) |
| `mesin/diagram.py` | Mermaid diagrams to PNG (`diagram`) |
| `mesin/rumus.py` | LaTeX math parser (`#E` / `{E:…}`) to native Word OMML equations, without TeX |
| `mesin/pratinjau.py` | PDF pages to 2×2 PNG visual grids in TEMP (`pratinjau`) |
| `mesin/ekspor.py` | a whole downloaded book (Shamela or Waqfeya) as one plain .txt to read (`ekspor`) |
| `mesin/tahap.py`, `rakit.py`, `produk.py` | state of a bahts; the Python side of `rakit` (lock, `.rakit-*` folders, installing the results); result file names and report lines |
| `mesin/rakit.ps1`, `word.ps1`, `teks_pdf.py` | Word/PDF builder, the identity of its own Word process, and PDF text |
| `mesin/format.json` | page layout profiles (`@format`) |
| `mesin/sampul_qism.docx`, `sampul.doc`, `sampul_jakarta.docx`, `kepala_kotak.docx` | cover and page header templates |
| `mesin/naskah_baru.txt`, `riset_baru.txt` | the outline made by `baru` |
| `contoh/` | sample `naskah.txt` + `riset.txt` and `jebakan/` for tests |
| `.mcp.json`, `opencode.json` | connector list (`opencode.json` = the copy for OpenCode) |
| `dok/` | [`pemakai-baru.md`](dok/pemakai-baru.md), [`pengaturan-bahts.md`](dok/pengaturan-bahts.md), [`riset-alat.md`](dok/riset-alat.md), [`pemeriksaan.md`](dok/pemeriksaan.md), [`penulisan-sumber.md`](dok/penulisan-sumber.md), [`audit.md`](dok/audit.md), [`mutamad.md`](dok/mutamad.md), [`mengubah-mesin.md`](dok/mengubah-mesin.md), [`standar.svg`](dok/standar.svg), [`uji-riset.md`](dok/uji-riset.md), [`takhrij.md`](dok/takhrij.md) |
| `.github/` | `uji_*.py`, [`bantu.py`](.github/bantu.py), [`workflows/tes.yml`](.github/workflows/tes.yml), [`workflows/rilis.yml`](.github/workflows/rilis.yml), [`uji_word_startup.ps1`](.github/uji_word_startup.ps1), [`uji_pemeriksa/prompt.md`](.github/uji_pemeriksa/prompt.md) (`.github/uji_pemeriksa/`) |
| `kitab/`, `bahts/`, `sampul_saya.txt`, `keluaran_saya.txt`, `kunci_openalex.txt` | user data on their computer, not in git |

### Changing the machine

- The rules: `dok/mengubah-mesin.md`.
- Tests: `python .github/uji_semua.py` (the list is read from `.github/workflows/tes.yml`; test books: the `ambil` line in that file).
- Changes the user notices go into [`CHANGELOG.md`](CHANGELOG.md), section «Belum dirilis».
- [`README.id.md`](README.id.md) and [`README.ar.md`](README.ar.md) are translations of this file: change all three together (`.github/uji_readme.py` compares them).
- Problems: an issue with the output of `periksa`, the command, and its message.

### License

Code: GNU AGPLv3 or any later version ([`LICENSE`](LICENSE)); versions up to 94d62d3 (including release 7.0.0) remain MIT. A bahts produced by the machine belongs to its author; templates copied into a bahts may be used without conditions (additional permission in `NOTICE`). Mushaf text, fonts, logo, and book texts: [`NOTICE`](NOTICE).
