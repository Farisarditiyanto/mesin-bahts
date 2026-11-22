# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pengurai rumus LaTeX -> OMML (Office Math Markup Language) untuk Microsoft Word asli, tanpa TeX atau pustaka luar.

Dipakai `naskah.py` ({E:...} di dalam paragraf/tabel/catatan kaki) dan `olah.py` (#E di baris sendiri, boleh memakai
\\tag{...} untuk nomor persamaan). Teks Arab di dalam \\text{...} (mis. \\frac{\\text{صافي الربح}}{\\text{حقوق الملكية}})
dicetak kanan-ke-kiri dengan huruf profil @format; simbol dan rumus dicetak Cambria Math. Sintaks rusak = TandaRusak
(GAGAL di `cek` sebelum Word dipanggil).
"""
import re
from xml.sax.saxutils import escape

from dasar import TandaRusak

ARAB = re.compile(r"[؀-ۿ]")
BATAS_DALAM = 64  # cegah rekursi berlebih pada masukan berulang «{{{{...» atau «\sqrt\sqrt...»
HURUF_MATH = "Cambria Math"

# Simbol LaTeX -> (karakter Unicode, tegak?)
# tegak=True: operator, relasi, panah, simbol tetap (sty="p"); False: variabel miring (huruf Yunani kecil)
SIMBOL = {
    # Yunani kecil (miring dalam matematika)
    **{k: (v, False) for k, v in {
        "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ϵ", "varepsilon": "ε",
        "zeta": "ζ", "eta": "η", "theta": "θ", "vartheta": "ϑ", "iota": "ι", "kappa": "κ",
        "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π", "varpi": "ϖ",
        "rho": "ρ", "varrho": "ϱ", "sigma": "σ", "varsigma": "ς", "tau": "τ", "upsilon": "υ",
        "phi": "ϕ", "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω", "ell": "ℓ",
    }.items()},
    # Yunani besar dan simbol tegak
    **{k: (v, True) for k, v in {
        "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π",
        "Sigma": "Σ", "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
        # Operator biner & relasi
        "times": "×", "div": "÷", "cdot": "·", "pm": "±", "mp": "∓", "ast": "∗", "star": "⋆",
        "circ": "∘", "bullet": "•", "oplus": "⊕", "otimes": "⊗", "setminus": "∖",
        "leq": "≤", "le": "≤", "leqslant": "≤", "geq": "≥", "ge": "≥", "geqslant": "≥", "neq": "≠", "ne": "≠",
        "approx": "≈", "equiv": "≡", "sim": "∼", "simeq": "≃", "cong": "≅", "propto": "∝",
        "ll": "≪", "gg": "≫", "prec": "≺", "succ": "≻", "preceq": "⪯", "succeq": "⪰",
        "perp": "⊥", "parallel": "∥", "mid": "∣", "nmid": "∤",
        "lvert": "|", "rvert": "|", "lVert": "‖", "rVert": "‖",
        # Himpunan & logika
        "in": "∈", "notin": "∉", "ni": "∋", "subset": "⊂", "subseteq": "⊆", "supset": "⊃", "supseteq": "⊇",
        "cup": "∪", "cap": "∩", "emptyset": "∅", "varnothing": "∅",
        "forall": "∀", "exists": "∃", "nexists": "∄", "neg": "¬", "lnot": "¬",
        "land": "∧", "wedge": "∧", "lor": "∨", "vee": "∨", "top": "⊤", "bot": "⊥",
        # Panah
        "to": "→", "rightarrow": "→", "leftarrow": "←", "gets": "←", "leftrightarrow": "↔",
        "Rightarrow": "⇒", "Leftarrow": "⇐", "Leftrightarrow": "⇔", "implies": "⇒", "iff": "⇔",
        "mapsto": "↦", "uparrow": "↑", "downarrow": "↓", "longrightarrow": "⟶", "Longrightarrow": "⟹",
        # Lainnya
        "infty": "∞", "partial": "∂", "nabla": "∇", "dots": "…", "ldots": "…", "cdots": "⋯",
        "vdots": "⋮", "ddots": "⋱", "therefore": "∴", "because": "∵", "angle": "∠", "degree": "°",
        "prime": "′", "hbar": "ℏ", "Re": "ℜ", "Im": "ℑ", "aleph": "ℵ", "checkmark": "✓",
        # Tanda yang di-escape
        "%": "%", "$": "$", "&": "&", "#": "#", "_": "_", "{": "{", "}": "}", "|": "‖",
        ",": "\u2009", ";": "\u2005", ":": "\u2004", " ": "\u00A0", "!": "", "quad": "\u2001", "qquad": "\u2001\u2001",
    }.items()},
}

# Operator n-ary (m:nary): nama perintah -> (simbol, batas atas-bawah secara bawaan?)
NARY = {
    "sum": ("∑", True), "prod": ("∏", True), "coprod": ("∐", True),
    "bigcup": ("⋃", True), "bigcap": ("⋂", True), "bigoplus": ("⨁", True), "bigotimes": ("⨂", True),
    "int": ("∫", False), "iint": ("∬", False), "iiint": ("∭", False), "oint": ("∮", False),
}

# Fungsi tegak; yang ada di LIMIT menerima batas bawah (m:limLow) bila diikuti «_»
LIMIT = {"lim", "limsup", "liminf", "max", "min", "sup", "inf", "argmax", "argmin", "det", "Pr", "gcd"}
FUNGSI = LIMIT | {
    "sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan",
    "sinh", "cosh", "tanh", "coth", "log", "ln", "exp", "lg", "deg", "dim", "hom", "ker",
    "arg", "mod", "bmod", "Var", "Cov", "Corr", "E", "P",
}

AKSEN = {
    "bar": "\u0304", "hat": "\u0302", "widehat": "\u0302", "tilde": "\u0303", "widetilde": "\u0303",
    "vec": "\u20D7", "dot": "\u0307", "ddot": "\u0308", "acute": "\u0301", "grave": "\u0300",
    "check": "\u030C", "breve": "\u0306",
}

GAYA_TEKS = {"text", "textrm", "mbox", "textbf", "textit", "textsf", "texttt"}
# Gaya huruf rumus -> (tegak?, tebal?, m:scr); None = ikut bawaan simbolnya
GAYA_MATH = {
    "mathrm": (True, False, None), "operatorname": (True, False, None), "mathit": (False, False, None),
    "mathbf": (True, True, None), "boldsymbol": (None, True, None), "bm": (None, True, None),
    "mathbb": (True, False, "double-struck"), "mathcal": (True, False, "script"),
    "mathsf": (True, False, "sans-serif"), "mathtt": (True, False, "monospace"),
}
PEMBESAR = {"big", "Big", "bigg", "Bigg", "bigl", "bigr", "Bigl", "Bigr", "biggl", "biggr", "Biggl", "Biggr"}
KURUNG = {
    "(": "(", ")": ")", "[": "[", "]": "]", "|": "|", "/": "/",
    "{": "{", "}": "}", "lbrace": "{", "rbrace": "}", "vert": "|", "Vert": "‖",
    "langle": "⟨", "rangle": "⟩", "lfloor": "⌊", "rfloor": "⌋", "lceil": "⌈", "rceil": "⌉", ".": "",
    "lvert": "|", "rvert": "|", "lVert": "‖", "rVert": "‖",
}
# Tanda yang bentuknya berarah: dicerminkan di rumus kanan-ke-kiri, karena operannya bertukar tempat
CERMIN = str.maketrans("()[]{}⟨⟩⌊⌋⌈⌉<>≤≥≪≫≺≻⪯⪰→←⇒⇐⟶⟵⟹⟸↦↤∈∋∉∌⊂⊃⊆⊇", ")(][}{⟩⟨⌋⌊⌉⌈><≥≤≫≪≻≺⪰⪯←→⇐⇒⟵⟶⟸⟹↤↦∋∈∌∉⊃⊂⊇⊆")
MATRIKS = {
    "matrix": ("", ""), "smallmatrix": ("", ""), "pmatrix": ("(", ")"), "bmatrix": ("[", "]"),
    "Bmatrix": ("{", "}"), "vmatrix": ("|", "|"), "Vmatrix": ("‖", "‖"),
}
JADWAL = {"aligned", "align", "align*", "gather", "gathered", "equation", "equation*", "split"}


def _token(latex):
    """Pecah string LaTeX jadi daftar token (jenis, isi). Jenis: cmd, lbrace, rbrace, sup, sub, amp, nl, sp, txt."""
    out, i, n = [], 0, len(latex)
    while i < n:
        c = latex[i]
        if c in " \t\r\n":
            j = i + 1
            while j < n and latex[j] in " \t\r\n":
                j += 1
            out.append(("sp", " "))
            i = j
        elif c == "\\":
            if i + 1 >= n:
                raise TandaRusak("rumus berakhir dengan «\\» tunggal")
            nx = latex[i + 1]
            if nx == "\\":
                out.append(("nl", "\\\\"))
                i += 2
            elif nx.isalpha():
                j = i + 2
                while j < n and latex[j].isalpha():
                    j += 1
                cmd = latex[i + 1:j]
                if cmd in ("align", "equation", "operatorname") and j < n and latex[j] == "*":
                    cmd += "*" * (cmd != "operatorname")
                    j += 1
                out.append(("cmd", cmd))
                i = j
            else:
                out.append(("cmd", nx))
                i += 2
        elif c == "{":
            out.append(("lbrace", "{")); i += 1
        elif c == "}":
            out.append(("rbrace", "}")); i += 1
        elif c == "^":
            out.append(("sup", "^")); i += 1
        elif c == "_":
            out.append(("sub", "_")); i += 1
        elif c == "&":
            out.append(("amp", "&")); i += 1
        elif c == "~":
            out.append(("cmd", " ")); i += 1
        elif c == "'":
            j = i + 1
            while j < n and latex[j] == "'":
                j += 1
            out.append(("prime", "′" * (j - i)))
            i = j
        else:
            out.append(("txt", c)); i += 1
    return out


def _kanan_ke_kiri(tok):
    """Rumus tanpa huruf Latin/Yunani dan tanpa nama fungsi (teks Arab, angka, operator) dicetak kanan-ke-kiri seperti
    kalimat Arab di sekitarnya; rumus yang memuatnya dicetak kiri-ke-kanan seluruhnya. Nama lingkungan
    (\\begin{pmatrix}) dan nomor persamaan (\\tag{a}) bukan isi rumus."""
    lewati = False
    for jenis, isi in tok:
        if lewati:
            lewati = jenis != "rbrace"
        elif jenis == "cmd" and isi in ("begin", "end", "tag"):
            lewati = True
        elif jenis == "txt" and isi.isalpha() and not ARAB.match(isi):
            return False
        elif jenis == "cmd" and (isi in FUNGSI or SIMBOL.get(isi, ("",))[0].isalpha()):
            return False
    return True


class _PenguraiRumus:
    """Pengurai recursive-descent LaTeX -> fragmen XML OMML."""

    def __init__(self, latex, *, display, huruf_arab, ukuran_latin, ukuran_arab):
        self.tok = _token(latex)
        self.i = 0
        self.display = display
        self.huruf_arab = huruf_arab
        self.sz_latin = str(int(round(ukuran_latin * 2)))  # satuan half-point OOXML
        self.sz_arab = str(int(round(ukuran_arab * 2)))
        self.tag = None
        self.dalam = 0
        self.gaya = None  # gaya aktif: nilai GAYA_MATH
        self.rtl = _kanan_ke_kiri(self.tok)

    def _lewati_sp(self):
        while self.i < len(self.tok) and self.tok[self.i][0] == "sp":
            self.i += 1

    def _intip(self):
        self._lewati_sp()
        return self.tok[self.i] if self.i < len(self.tok) else None

    def _ambil(self):
        self._lewati_sp()
        if self.i >= len(self.tok):
            return None
        t = self.tok[self.i]
        self.i += 1
        return t

    def _rpr_math(self, bold=False, italic=False):
        b = "<w:b/>" if bold else ""
        it = "<w:i/>" if italic else ""
        # w:lang en-US: tanpa itu Word (angka konteks @angka hindi) menukar «.» dan «,» di antara angka rumus
        # saat mencetak («0.05» tercetak «0,05», «f(x, y)» tercetak «f(x. y)»)
        return (f'<w:rPr><w:rFonts w:ascii="{HURUF_MATH}" w:hAnsi="{HURUF_MATH}"/>{b}{it}<w:sz w:val="{self.sz_latin}"/>'
                '<w:lang w:val="en-US" w:bidi="en-US"/></w:rPr>')

    def _rpr_arab(self, bold=False):
        f = escape(self.huruf_arab)
        b = "<w:b/><w:bCs/>" if bold else ""
        return (f'<w:rPr><w:rFonts w:ascii="{f}" w:hAnsi="{f}" w:cs="{f}"/>{b}'
                f'<w:sz w:val="{self.sz_arab}"/><w:szCs w:val="{self.sz_arab}"/><w:rtl/></w:rPr>')

    def _run_math(self, teks, *, tegak=False, bold=False, italic=False):
        if not teks:
            return ""
        if self.rtl:
            teks = teks.translate(CERMIN)
        scr = ""
        if self.gaya is not None:
            g_tegak, g_bold, g_scr = self.gaya
            if g_tegak is not None:
                tegak = g_tegak
            bold = bold or g_bold
            scr = f'<m:scr m:val="{g_scr}"/>' if g_scr else ""
        sty = "b" if tegak and bold else "p" if tegak else "bi" if bold else ""
        mpr = f'<m:rPr>{scr}{f"""<m:sty m:val="{sty}"/>""" if sty else ""}</m:rPr>' if scr or sty else ""
        sp = ' xml:space="preserve"' if teks.startswith(" ") or teks.endswith(" ") else ""
        return f"<m:r>{mpr}{self._rpr_math(bold=bold, italic=italic)}<m:t{sp}>{escape(teks)}</m:t></m:r>"

    def _run_teks(self, teks, *, bold=False, italic=False):
        if not teks:
            return ""
        sp = ' xml:space="preserve"' if teks.startswith(" ") or teks.endswith(" ") else ""
        if ARAB.search(teks):
            return f"<m:r><m:rPr><m:nor/></m:rPr>{self._rpr_arab(bold=bold)}<m:t{sp}>{escape(teks)}</m:t></m:r>"
        return f"<m:r><m:rPr><m:nor/></m:rPr>{self._rpr_math(bold=bold, italic=italic)}<m:t{sp}>{escape(teks)}</m:t></m:r>"

    def _baca_mentah(self, perintah):
        """Baca isi satu grup { ... } sebagai string teks biasa (untuk \\text, \\tag, \\begin, \\end)."""
        self._lewati_sp()
        if self.i >= len(self.tok) or self.tok[self.i][0] != "lbrace":
            raise TandaRusak(f"\\{perintah} memerlukan argumen dalam kurung kurawal {{…}}")
        self.i += 1
        dalam, bagian = 0, []
        while self.i < len(self.tok):
            j, v = self.tok[self.i]
            self.i += 1
            if j == "lbrace":
                dalam += 1; bagian.append("{")
            elif j == "rbrace":
                if not dalam:
                    return "".join(bagian)
                dalam -= 1; bagian.append("}")
            elif j == "cmd":
                bagian.append(SIMBOL[v][0] if v in SIMBOL else "\\" + v)
            elif j == "prime":
                bagian.append("'" * len(v))
            else:
                bagian.append(v)
        raise TandaRusak(f"\\{perintah}{{ tidak ditutup dengan }}")

    def _baca_arg(self, perintah):
        """Baca satu argumen (grup {…} atau satu atom) sebagai string OMML."""
        t = self._intip()
        if t is None or t[0] in ("rbrace", "amp", "nl"):
            raise TandaRusak(f"\\{perintah} kekurangan argumen")
        if t[0] == "lbrace":
            return self._baca_grup()
        return self._baca_atom(izin_skrip=False)

    def _baca_opsional(self):
        """Baca argumen opsional [...] bila ada; None bila tidak ada."""
        t = self._intip()
        if not t or t != ("txt", "["):
            return None
        self.i += 1
        bagian = self._baca_deret(stop=lambda x: x == ("txt", "]"))
        if self._intip() != ("txt", "]"):
            raise TandaRusak("argumen opsional [...] tidak ditutup dengan ]")
        self.i += 1
        return bagian

    def _baca_grup(self):
        self.dalam += 1
        if self.dalam > BATAS_DALAM:
            raise TandaRusak("kurung kurawal { } di rumus terlalu dalam")
        try:
            t = self._ambil()
            if not t or t[0] != "lbrace":
                raise TandaRusak("diharapkan «{» di dalam rumus")
            isi = self._baca_deret(stop=lambda x: x[0] == "rbrace")
            tutup = self._ambil()
            if not tutup or tutup[0] != "rbrace":
                raise TandaRusak("kurung kurawal { di rumus tidak ditutup dengan }")
            return isi
        finally:
            self.dalam -= 1

    def _baca_kurung(self, perintah):
        t = self._ambil()
        if not t:
            raise TandaRusak(f"\\{perintah} memerlukan tanda kurung sesudahnya (mis. \\{perintah}()")
        if t[0] == "txt" and t[1] in KURUNG:
            return KURUNG[t[1]]
        if t[0] == "cmd" and t[1] in KURUNG:
            return KURUNG[t[1]]
        raise TandaRusak(f"tanda kurung sesudah \\{perintah} tidak dikenal: «{t[1]}»")

    def _baca_deret(self, stop=None, *, henti_biner=False):
        bagian, kurung = [], 0
        while (t := self._intip()) is not None:
            if stop and stop(t):
                break
            if henti_biner and kurung == 0 and t[0] == "txt" and t[1] in ")]":
                break
            if henti_biner and bagian and kurung == 0 and (
                (t[0] == "txt" and t[1] in "+-=<>")
                or (t[0] == "cmd" and t[1] in ("pm", "mp", "leq", "le", "geq", "ge", "neq", "ne", "approx", "equiv", "sim"))
            ):
                break
            if t[0] == "rbrace":
                raise TandaRusak("tanda «}» berlebih tanpa «{» pembuka")
            if t[0] in ("amp", "nl"):
                raise TandaRusak(f"tanda «{t[1]}» hanya boleh di dalam \\begin{{…}}…\\end{{…}}")
            if t[0] == "cmd" and t[1] == "right":
                raise TandaRusak("\\right tanpa \\left sebelumnya")
            if t[0] == "cmd" and t[1] == "end":
                raise TandaRusak("\\end tanpa \\begin sebelumnya")
            if t[0] == "cmd" and t[1] == "tag":
                self.i += 1
                if not self.display:
                    raise TandaRusak("\\tag{…} hanya boleh di persamaan baris sendiri (#E), bukan di dalam {E:…}")
                if self.tag is not None:
                    raise TandaRusak("\\tag{…} disebut lebih dari sekali di satu persamaan #E")
                isi_tag = self._baca_mentah("tag").strip()
                if not isi_tag:
                    raise TandaRusak("\\tag{} kosong: tulis nomor persamaan di dalamnya, mis. \\tag{1}")
                self.tag = isi_tag
                continue
            if t[0] == "txt" and t[1] in "([":
                kurung += 1
            elif t[0] == "txt" and t[1] in ")]" and kurung > 0:
                kurung -= 1
            bagian.append(self._baca_atom(izin_skrip=True))
        # Word menata isi zona rumus kiri-ke-kanan menurut urutan tulisnya, juga teks Arab: tanpa dibalik,
        # «\text{الإيرادات} - \text{المصروفات}» tercetak dengan الإيرادات di kiri, jadi pembaca Arab membacanya
        # «المصروفات − الإيرادات». Rumus Arab murni dibalik di tiap deretnya supaya terbaca benar dari kanan.
        return "".join(reversed(bagian) if self.rtl else bagian)

    def _skrip(self, dasar):
        """Tangkap rangkaian _, ^, dan prime (') sesudah atom `dasar`."""
        sub = sup = None
        while (t := self._intip()) is not None and t[0] in ("sub", "sup", "prime"):
            self.i += 1
            if t[0] == "prime":
                p = self._run_math(t[1], tegak=True)
                sup = (sup + p) if sup else p
            elif t[0] == "sub":
                if sub is not None:
                    raise TandaRusak("tanda bawah «_» ganda pada satu simbol: gunakan kurung kurawal _{…}")
                sub = self._baca_arg("_")
            else:
                if sup is not None:
                    raise TandaRusak("tanda pangkat «^» ganda pada satu simbol: gunakan kurung kurawal ^{…}")
                sup = self._baca_arg("^")
        if self.rtl and (sub is not None or sup is not None):  # rumus Arab: pangkat dan indeks di kiri simbolnya
            return f"<m:sPre><m:sub>{sub or ''}</m:sub><m:sup>{sup or ''}</m:sup><m:e>{dasar}</m:e></m:sPre>"
        if sub is not None and sup is not None:
            return f"<m:sSubSup><m:e>{dasar}</m:e><m:sub>{sub}</m:sub><m:sup>{sup}</m:sup></m:sSubSup>"
        if sub is not None:
            return f"<m:sSub><m:e>{dasar}</m:e><m:sub>{sub}</m:sub></m:sSub>"
        if sup is not None:
            return f"<m:sSup><m:e>{dasar}</m:e><m:sup>{sup}</m:sup></m:sSup>"
        return dasar

    def _baca_nary(self, cmd):
        chr_, und_ovr = NARY[cmd]
        sub = sup = None
        while (t := self._intip()) is not None and (t[0] in ("sub", "sup") or t in (("cmd", "limits"), ("cmd", "nolimits"))):
            self.i += 1
            if t[0] == "cmd":
                continue
            if t[0] == "sub":
                if sub is not None:
                    raise TandaRusak(f"\\{cmd}: batas bawah «_» ganda")
                sub = self._baca_arg("_")
            else:
                if sup is not None:
                    raise TandaRusak(f"\\{cmd}: batas atas «^» ganda")
                sup = self._baca_arg("^")
        # isi n-ary: satu suku sampai operator +/-/= atau akhir blok/grup
        isi = self._baca_deret(
            stop=lambda x: x[0] in ("rbrace", "amp", "nl") or (x[0] == "cmd" and x[1] in ("right", "end", "tag")),
            henti_biner=True,
        )
        lim_loc = "undOvr" if (und_ovr and self.display) else "subSup"
        pr = [f'<m:chr m:val="{escape(chr_)}"/>', f'<m:limLoc m:val="{lim_loc}"/>']
        if sub is None:
            pr.append('<m:subHide m:val="1"/>')
        if sup is None:
            pr.append('<m:supHide m:val="1"/>')
        return f"<m:nary><m:naryPr>{''.join(pr)}</m:naryPr><m:sub>{sub or ''}</m:sub><m:sup>{sup or ''}</m:sup><m:e>{isi}</m:e></m:nary>"

    def _baca_env(self):
        nama = self._baca_mentah("begin").strip()
        if nama not in MATRIKS and nama not in JADWAL and nama != "cases":
            raise TandaRusak(f"lingkungan \\begin{{{nama}}} belum didukung (yang ada: matrix/pmatrix/bmatrix/vmatrix, cases, aligned/align/gather)")
        self.dalam += 1
        if self.dalam > BATAS_DALAM:
            raise TandaRusak("lingkungan \\begin{…} terlalu dalam")
        try:
            baris = [[]]
            while True:
                sel = self._baca_deret(stop=lambda x: x[0] in ("amp", "nl") or (x[0] == "cmd" and x[1] == "end"))
                baris[-1].append(sel)
                t = self._intip()
                if t is None:
                    raise TandaRusak(f"\\begin{{{nama}}} tidak ditutup dengan \\end{{{nama}}}")
                if t[0] == "amp":
                    self.i += 1
                elif t[0] == "nl":
                    self.i += 1
                    baris.append([])
                elif t[0] == "cmd" and t[1] == "end":
                    self.i += 1
                    tutup = self._baca_mentah("end").strip()
                    if tutup != nama:
                        raise TandaRusak(f"\\begin{{{nama}}} ditutup dengan \\end{{{tutup}}}")
                    break
            if len(baris) > 1 and baris[-1] == [""]:
                baris.pop()  # «\\» terakhir sebelum \end diabaikan seperti LaTeX
            arah = -1 if self.rtl else 1  # rumus kanan-ke-kiri: kolom pertama di kanan
            if nama in JADWAL:
                eqs = "".join(f"<m:e>{''.join(r[::arah])}</m:e>" for r in baris)
                return f"<m:eqArr>{eqs}</m:eqArr>"
            lebar = max(len(r) for r in baris)
            baris_xml = "".join(
                "<m:mr>" + "".join(f"<m:e>{r[c] if c < len(r) else ''}</m:e>" for c in range(lebar)[::arah]) + "</m:mr>"
                for r in baris
            )
            m_xml = f'<m:m><m:mPr><m:mcs><m:mc><m:mcPr><m:count m:val="{lebar}"/><m:mcJc m:val="center"/></m:mcPr></m:mc></m:mcs></m:mPr>{baris_xml}</m:m>'
            if nama == "cases":
                buka, tutup_k = ("", "}") if self.rtl else ("{", "")
                return f'<m:d><m:dPr><m:begChr m:val="{buka}"/><m:endChr m:val="{tutup_k}"/></m:dPr><m:e>{m_xml}</m:e></m:d>'
            buka, tutup_k = MATRIKS[nama]
            if buka or tutup_k:
                return f'<m:d><m:dPr><m:begChr m:val="{escape(buka)}"/><m:endChr m:val="{escape(tutup_k)}"/></m:dPr><m:e>{m_xml}</m:e></m:d>'
            return m_xml
        finally:
            self.dalam -= 1

    def _sisa_bilangan(self):
        """Lanjutan satu bilangan sesudah angka pertamanya: angka, dan tanda yang langsung diapit angka («2.5», «2,5»,
        «1,250», «1{,}250», «1\\,250», «1/2», «1:2»). Satu bilangan = satu run, jadi tidak ikut terbalik di rumus
        kanan-ke-kiri (seperti di teks Arab biasa, tempat rangkaian itu tetap kiri-ke-kanan)."""
        def angka(k):
            return k < len(self.tok) and self.tok[k][0] == "txt" and self.tok[k][1].isdigit() and self.tok[k][1].isascii()
        out = []
        while True:
            while angka(self.i):
                out.append(self.tok[self.i][1])
                self.i += 1
            t = self.tok[self.i:self.i + 3]
            if t[:1] in ([("txt", c)] for c in ".,/:") and angka(self.i + 1):
                out.append(t[0][1])
                self.i += 1
            elif t[:1] == [("cmd", ",")] and angka(self.i + 1):
                out.append(SIMBOL[","][0])
                self.i += 1
            elif t == [("lbrace", "{"), ("txt", ","), ("rbrace", "}")] and angka(self.i + 3):
                out.append(",")
                self.i += 3
            else:
                return "".join(out)

    def _baca_atom(self, *, izin_skrip):
        self.dalam += 1
        if self.dalam > BATAS_DALAM:
            raise TandaRusak("rumus terlalu dalam (kurangi sarang perintah atau kurung)")
        try:
            return self._baca_atom_isi(izin_skrip=izin_skrip)
        finally:
            self.dalam -= 1

    def _baca_atom_isi(self, *, izin_skrip):
        t = self._intip()
        if t is None:
            raise TandaRusak("rumus berakhir sebelum waktunya")
        if t[0] == "lbrace":
            dasar = self._baca_grup()
            return self._skrip(dasar) if izin_skrip else dasar
        if t[0] in ("sub", "sup"):
            raise TandaRusak(f"tanda «{t[1]}» tanpa simbol di depannya")
        if t[0] == "prime":
            self.i += 1
            return self._run_math(t[1], tegak=True)
        if t[0] == "txt":
            self.i += 1
            c = t[1]
            if c == "-":
                dasar = self._run_math("−", tegak=True)
            elif ARAB.match(c):
                # gabungkan huruf Arab berurutan jadi satu run RTL
                buf = [c]
                while self.i < len(self.tok) and self.tok[self.i][0] == "txt" and ARAB.match(self.tok[self.i][1]):
                    buf.append(self.tok[self.i][1]); self.i += 1
                dasar = self._run_teks("".join(buf))
            elif c.isdigit():
                # argumen tanpa kurung kurawal = satu angka, seperti LaTeX: «\frac12» = ½, «x^12» = x¹2
                dasar = self._run_math(c + (self._sisa_bilangan() if izin_skrip else ""), tegak=True)
            elif c.isalpha():
                dasar = self._run_math(c, tegak=False)
            else:
                if c == "$":
                    raise TandaRusak("tanda «$» tidak dipakai di rumus: tulis rumusnya langsung sesudah #E atau di dalam "
                                     "{E:…}; dolar sebagai mata uang ditulis «\\$»")
                dasar = self._run_math(c, tegak=True)
            return self._skrip(dasar) if izin_skrip else dasar
        if t[0] == "cmd":
            self.i += 1
            cmd = t[1]
            if cmd in ("frac", "dfrac", "tfrac", "cfrac"):
                num, den = self._baca_arg(cmd), self._baca_arg(cmd)
                dasar = f"<m:f><m:num>{num}</m:num><m:den>{den}</m:den></m:f>"
            elif cmd == "binom":
                num, den = self._baca_arg(cmd), self._baca_arg(cmd)
                dasar = (f'<m:d><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr><m:e>'
                         f'<m:f><m:fPr><m:type m:val="noBar"/></m:fPr><m:num>{num}</m:num><m:den>{den}</m:den></m:f></m:e></m:d>')
            elif cmd == "sqrt":
                deg = self._baca_opsional()
                isi = self._baca_arg("sqrt")
                pr = "<m:radPr/>" if deg else '<m:radPr><m:degHide m:val="1"/></m:radPr>'
                dasar = f"<m:rad>{pr}<m:deg>{deg or ''}</m:deg><m:e>{isi}</m:e></m:rad>"
            elif cmd in NARY:
                return self._baca_nary(cmd)
            elif cmd in LIMIT:
                fn = self._run_math(cmd, tegak=True)
                if izin_skrip and self._intip() and self._intip()[0] == "sub":
                    self.i += 1
                    lim = self._baca_arg("_")
                    dasar = f"<m:limLow><m:e>{fn}</m:e><m:lim>{lim}</m:lim></m:limLow>"
                else:
                    dasar = fn
            elif cmd in FUNGSI:
                dasar = self._run_math(cmd, tegak=True)
            elif cmd in GAYA_TEKS:
                isi = self._baca_mentah(cmd)
                dasar = self._run_teks(isi, bold=(cmd == "textbf"), italic=(cmd == "textit"))
            elif cmd in GAYA_MATH:
                lama, self.gaya = self.gaya, GAYA_MATH[cmd]
                try:
                    dasar = self._baca_arg(cmd)
                finally:
                    self.gaya = lama
            elif cmd in AKSEN:
                isi = self._baca_arg(cmd)
                dasar = f'<m:acc><m:accPr><m:chr m:val="{AKSEN[cmd]}"/></m:accPr><m:e>{isi}</m:e></m:acc>'
            elif cmd in ("overset", "underset", "stackrel"):  # \overset{atas}{dasar}
                lim, isi = self._baca_arg(cmd), self._baca_arg(cmd)
                jenis = "limLow" if cmd == "underset" else "limUpp"
                dasar = f"<m:{jenis}><m:e>{isi}</m:e><m:lim>{lim}</m:lim></m:{jenis}>"
            elif cmd in ("overline", "underline"):
                isi = self._baca_arg(cmd)
                pos = "top" if cmd == "overline" else "bot"
                dasar = f'<m:bar><m:barPr><m:pos m:val="{pos}"/></m:barPr><m:e>{isi}</m:e></m:bar>'
            elif cmd in ("overbrace", "underbrace"):
                isi = self._baca_arg(cmd)
                pos = "top" if cmd == "overbrace" else "bot"
                ch = "⏞" if cmd == "overbrace" else "⏟"
                dasar = f'<m:groupChr><m:groupChrPr><m:chr m:val="{ch}"/><m:pos m:val="{pos}"/></m:groupChrPr><m:e>{isi}</m:e></m:groupChr>'
                if izin_skrip and self._intip() and self._intip()[0] in ("sup", "sub"):
                    jenis = self._ambil()[0]
                    lbl = self._baca_arg(jenis)
                    tag_l = "limUpp" if jenis == "sup" else "limLow"
                    return f"<m:{tag_l}><m:e>{dasar}</m:e><m:lim>{lbl}</m:lim></m:{tag_l}>"
                return dasar
            elif cmd == "left":
                self.dalam += 1
                if self.dalam > BATAS_DALAM:
                    raise TandaRusak("\\left…\\right terlalu dalam")
                try:
                    buka = self._baca_kurung("left")
                    isi = self._baca_deret(stop=lambda x: x[0] == "cmd" and x[1] == "right")
                    if self._intip() != ("cmd", "right"):
                        raise TandaRusak("\\left tidak ditutup dengan \\right")
                    self.i += 1
                    tutup = self._baca_kurung("right")
                    if self.rtl:
                        buka, tutup = tutup.translate(CERMIN), buka.translate(CERMIN)
                    dasar = f'<m:d><m:dPr><m:begChr m:val="{escape(buka)}"/><m:endChr m:val="{escape(tutup)}"/></m:dPr><m:e>{isi}</m:e></m:d>'
                finally:
                    self.dalam -= 1
            elif cmd in PEMBESAR:
                return self._run_math(self._baca_kurung(cmd), tegak=True)
            elif cmd == "begin":
                dasar = self._baca_env()
            elif cmd in ("displaystyle", "textstyle", "scriptstyle", "limits", "nolimits"):
                return ""
            elif cmd in SIMBOL:
                ch, tegak = SIMBOL[cmd]
                dasar = self._run_math(ch, tegak=tegak) if ch else ""
            else:
                raise TandaRusak(f"perintah LaTeX «\\{cmd}» tidak dikenal di rumus")
            return self._skrip(dasar) if izin_skrip else dasar
        raise TandaRusak(f"tanda rumus tidak dikenal: {t}")

    def urai(self):
        isi = self._baca_deret()
        sisa = self._intip()
        if sisa is not None:
            raise TandaRusak(f"sisa sintaks rumus tidak terbaca: «{sisa[1]}»")
        return isi


def konversi(latex, *, display=False, huruf_arab="Traditional Arabic", ukuran_latin=12, ukuran_arab=14):
    """Ubah ekspresi LaTeX menjadi (omml_xml, tag). Gagal -> TandaRusak.
    display=True: dibungkus <m:oMathPara><m:oMath>…</m:oMath></m:oMathPara> dan menerima \\tag{…}.
    display=False: <m:oMath>…</m:oMath> untuk persamaan sebaris ({E:…})."""
    if not latex or not latex.strip():
        raise TandaRusak("rumus kosong: tulis ekspresi LaTeX, mis. \\frac{a}{b}")
    p = _PenguraiRumus(latex.strip(), display=display, huruf_arab=huruf_arab,
                       ukuran_latin=ukuran_latin, ukuran_arab=ukuran_arab)
    isi = p.urai()
    if not isi:
        raise TandaRusak("rumus tidak menghasilkan isi apa pun")
    omml = f"<m:oMath>{isi}</m:oMath>"
    if display:
        omml = f"<m:oMathPara>{omml}</m:oMathPara>"
    return omml, p.tag
