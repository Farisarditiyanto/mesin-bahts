# SPDX-License-Identifier: AGPL-3.0-or-later
# Halaman tanpa kepala/kaki di tengah dan akhir bagian isi: halaman pemisah tiap #F (@judul_fasl: pemisah,
# pemisah_bingkai) dan halaman penutup (@tamma). Di-dot-source rakit.ps1 dan memakai $word, $doc, $sel, Para, Tulis,
# Huruf, $GAYA_BERJALAN (kepala.ps1), $HURUF_HIAS, dan ukuran huruf profil miliknya. Isinya sudah diputuskan
# olah.rencana_cetak ($RENCANA.pemisah, $RENCANA.tamma); judul #B sesudah halaman pemisah mulai halaman baru lewat
# $RENCANA.halaman_baru.

# Halaman berikutnya jadi halaman pertama bagian Word baru yang kepala/kaki halaman pertamanya kosong: nomornya tetap
# terhitung (bersambung) tetapi tidak tercetak, dan halaman sesudahnya memakai kepala/kaki utama yang tersambung ke
# bagian sebelumnya, jadi @kepala apa pun (juga kotak dan @templat) tidak perlu dipasang ulang. Kursor yang sudah di
# awal bagian Word (bagian @nomor yang baru dibuat, atau judul pertama bagian isi) tidak diberi pemisah lagi: dua
# pemisah bagian berturut-turut = halaman kosong
function Halaman-TanpaNomor {
    $s = $doc.Sections($doc.Sections.Count)
    if ($sel.Start -ne $s.Range.Start) {
        $sel.InsertBreak(2)                              # 2 = wdSectionBreakNextPage
        $s = $doc.Sections($doc.Sections.Count)
        $s.Footers(1).PageNumbers.RestartNumberingAtSection = $false   # pemisah bagian menyalin «mulai ١ lagi» bagian isi
    }
    $s.PageSetup.DifferentFirstPageHeaderFooter = -1
    foreach ($hf in @($s.Headers(2), $s.Footers(2))) {  # 2 = wdHeaderFooterFirstPage
        $hf.LinkToPrevious = $false
        $hf.Range.Text = ''
        foreach ($sp in @($hf.Range.ShapeRange)) { try { $sp.Delete() } catch {} }
    }
}

# paragraf kosong setinggi $tinggi pt: Word membuang jarak atas paragraf pertama sesudah pindah halaman, jadi isi
# halaman pemisah/penutup diturunkan lewat paragraf ini. Dikembalikan: titik awalnya (jangkar bingkai)
function Turun($tinggi) {
    Para 1 0 0
    $sel.ParagraphFormat.LineSpacingRule = 4; $sel.ParagraphFormat.LineSpacing = [single][Math]::Max(1, $tinggi)   # 4 = tepat
    Huruf $sel.Font $TA 2 0
    $awal = $sel.Start
    $sel.TypeParagraph()
    return $doc.Range($awal, $awal)                      # bukan rentang paragrafnya: TypeParagraph di dalamnya memperluasnya
}

function Tinggi-Bidang { $ps = $doc.Sections($doc.Sections.Count).PageSetup; return $ps.PageHeight - $ps.TopMargin - $ps.BottomMargin }

# bingkai ganda bersudut bulat di halaman jangkar $r saja: luar tebal, dalam tipis, di belakang teks
function Bingkai-Bulat($r) {
    $ps = $doc.Sections($doc.Sections.Count).PageSetup
    foreach ($b in @(@(1.4, 2.25), @(1.6, 0.75))) {     # jarak dari tepi kertas (cm), tebal garis (pt)
        $t = $word.CentimetersToPoints($b[0])
        $sp = $doc.Shapes.AddShape(5, $t, $t, $ps.PageWidth - 2 * $t, $ps.PageHeight - 2 * $t, $r)   # 5 = persegi bersudut bulat
        $sp.RelativeHorizontalPosition = 1; $sp.RelativeVerticalPosition = 1   # 1 = dari tepi kertas
        $sp.Left = $t; $sp.Top = $t
        $sp.Adjustments.Item(1) = [single](0.06 * $word.CentimetersToPoints(1.4) / $t)   # jari-jari sudut sama untuk keduanya
        $sp.Fill.Visible = 0; $sp.Line.Visible = -1; $sp.Line.ForeColor.RGB = 0; $sp.Line.Weight = [single]$b[1]
        $sp.WrapFormat.Type = 5                          # 5 = wdWrapBehind
        $sp.LockAnchor = -1
    }
}

# halaman pemisah #F ($p = satu isi olah.halaman_pemisah): judul besar (baris pertama = judul bagian berjalan dan
# tempat bookmark فهرس الموضوعات $bm), baris keduanya, «وفيه مطلبان:», lalu judul #B-nya; semuanya rata tengah, polos
function Halaman-Pemisah($p, $bm, $bingkai) {
    Halaman-TanpaNomor
    $jangkar = Turun ((Tinggi-Bidang) * 0.28)
    $sel.Style = $GAYA_BERJALAN
    Para 1 0 0; $sel.ParagraphFormat.KeepWithNext = -1
    [void]$doc.Bookmarks.Add($bm, $sel.Range)
    Tulis ([string]$p.judul[0]) $HURUF_HIAS ([Math]::Round($uJudul * 1.8)) 1 0
    $sel.TypeParagraph()
    if ($p.judul[1]) { Para 1 12 0; Tulis ([string]$p.judul[1]) $TJ ($uJudul + 4) 1 0; $sel.TypeParagraph() }
    if ($p.pengantar) { Para 1 36 0; Tulis ([string]$p.pengantar) $TJ $uJudulSub 1 0; $sel.TypeParagraph() }
    foreach ($t in @($p.anak)) { Para 1 10 0; Tulis ([string]$t) $TA $uMatan 0 0; $sel.TypeParagraph() }
    if ($bingkai) { Bingkai-Bulat $jangkar }
}

# halaman penutup (@tamma) sesudah الفهارس: halaman terakhir, tanpa paragraf kosong sesudahnya
function Halaman-Tamma {
    Halaman-TanpaNomor
    [void](Turun ((Tinggi-Bidang) * 0.4))
    Para 1 0 0; Tulis 'تمّ بحمد الله وتوفيقه' $HURUF_HIAS ([Math]::Round($uJudul * 2)) 1 0
    $sel.TypeParagraph()
    Para 1 18 0; Tulis 'وصلى الله وسلم على نبينا محمد وعلى آله وصحبه أجمعين' $TA ($uMatan + 2) 0 0
}
