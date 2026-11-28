# SPDX-License-Identifier: AGPL-3.0-or-later
# Sisipan bergaya kitab cetak lama (hitam putih, garis tipis atau ganda 0,75 pt, tanpa latar, rapat): kotak #T, butir
# daftar #-, tabel terjemah sejajar #P, dan pemisah #Z. Di-dot-source rakit.ps1 dan memakai $word, $doc, $sel, $DATA,
# Para, Runs, Tulis, HalamanBaru, Pengantar, Menempel, dan ukuran huruf profil miliknya. Label, nomor, dan judul kotak
# sudah diputuskan olah.py (_baris_kotak, _baris_daftar, _baris_paralel).

# Kotak = paragraf berbingkai, bukan kotak teks: Word menolak catatan kaki di kotak teks, dan bingkai paragraf ikut
# terpotong pindah halaman. Sisi garis COM = sisi fisik halaman, juga di paragraf kanan-ke-kiri (-1 atas, -2 kiri,
# -3 bawah, -4 kanan). Paragraf bersebelahan yang garisnya sama digabung Word jadi satu bingkai (judul + teks kotak).
# jenis -> sisi bergaris, LineStyle (1 tunggal, 7 ganda)
$KOTAK = @{
    'فائدة' = @(-1, -2, -3, -4), 1
    'تنبيه' = @(-1, -3), 7
    'تعريف' = @(-1, -2, -3, -4), 7
    'خلاصة' = @(-1, -3), 1
}
$JOROK_DAFTAR = 1.0                                    # cm tiap tingkat daftar, juga lebar jorok gantung «أ-»

# Garis dipasang sesudah teks kotak selesai ditulis, pada rentang paragrafnya: paragraf baru sesudah TypeParagraph
# mewarisi garis paragraf sebelumnya dan masuk bingkainya, lalu Borders.Enable = 0 di paragraf baru itu menghapus
# garis seluruh bingkai (diukur di Word)
function Bingkai($pf, $jenis) {
    $sisi, $gaya = $KOTAK[[string]$jenis]
    foreach ($s in $sisi) { $g = $pf.Borders.Item($s); $g.LineStyle = $gaya; $g.LineWidth = 6; $g.Color = 0 }   # 6 = 0,75 pt
    $pf.Borders.DistanceFromTop = 1; $pf.Borders.DistanceFromBottom = 1
    $pf.Borders.DistanceFromLeft = 4; $pf.Borders.DistanceFromRight = 4
    $pf.LeftIndent = 5; $pf.RightIndent = 5             # garis tegak di dalam bidang teks, bukan di tepi kertas
}

function Tulis-Kotak($i, $pb) {
    $blk = $DATA.blok[$i]
    if ($i -gt 0 -and $DATA.blok[$i - 1].kotak) {      # celah 4 pt: dua kotak berturut-turut tidak digabung Word
        Para 1 0 0; $sel.ParagraphFormat.LineSpacingRule = 4; $sel.ParagraphFormat.LineSpacing = 4; $sel.TypeParagraph()
    }
    $atas = 4; $awal = $sel.Start
    if ($blk.kotak.judul) {                             # judul tebal di tengah, menempel ke teks kotaknya
        Para 1 $atas 0; HalamanBaru $pb
        $sel.ParagraphFormat.KeepWithNext = -1
        Tulis ([string]$blk.kotak.judul) $TJ $uMatan 1 0
        $sel.TypeParagraph(); $atas = 0; $pb = $false
    }
    Para 3 $atas 0; HalamanBaru $pb
    $sel.ParagraphFormat.SpaceAfter = 4
    Runs $blk.runs $uMatan $false
    $sel.TypeParagraph()
    Bingkai $doc.Range($awal, $sel.Start - 1).ParagraphFormat $blk.kotak.jenis
}

# butir daftar: tingkat n menjorok (n-1) langkah dari kanan; label «أ-»/«١-» di jorok gantung selebar satu langkah
# (tab sesudah label = jorok gantung), «أولًا:» tebal mengawali teks tanpa jorok gantung. Sisi awal paragraf
# kanan-ke-kiri = LeftIndent COM: RightIndent tercetak di sisi kiri halaman (diukur di PDF)
function Tulis-Butir($i, $pb) {
    $blk = $DATA.blok[$i]; $d = $blk.daftar
    $w = $word.CentimetersToPoints($JOROK_DAFTAR)
    Para 3 0 0; HalamanBaru $pb
    $pf = $sel.ParagraphFormat
    if ($d.gantung) { $pf.LeftIndent = [single]($w * $d.tingkat); $pf.FirstLineIndent = [single](-$w) }
    else { $pf.LeftIndent = [single]($w * ($d.tingkat - 1)) }
    Runs $blk.runs $uMatan $false
    if ((Pengantar $blk) -and (Menempel $i)) { $sel.ParagraphFormat.KeepWithNext = -1 }
    $sel.TypeParagraph()
}

# baris #P berturut-turut = satu tabel dua kolom: Arab di kanan (kolom pertama tabel kanan-ke-kiri), terjemah Latin
# kiri-ke-kanan di kiri (Times New Roman seperti #L). Garis tipis di atas, di bawah, dan tegak di tengah saja.
# Dikembalikan: indeks blok #P terakhir
function Tulis-Paralel($i, $pb) {
    $baris = @($DATA.blok[$i])
    while ($i + 1 -lt $DATA.blok.Count -and $null -ne $DATA.blok[$i + 1].paralel) { $i++; $baris += $DATA.blok[$i] }
    Para 1 4 0; HalamanBaru $pb
    $tbl = $doc.Tables.Add($sel.Range, [int]$baris.Count, 2)
    $tbl.TableDirection = 0; $tbl.Borders.Enable = 0; $tbl.Rows.Alignment = 1
    $tbl.PreferredWidthType = 2; $tbl.PreferredWidth = 100; $tbl.Rows.AllowBreakAcrossPages = -1
    foreach ($s in -1, -3, -6) { $g = $tbl.Borders.Item($s); $g.LineStyle = 1; $g.LineWidth = 6; $g.Color = 0 }   # -6 = garis tegak dalam
    $tbl.TopPadding = 2; $tbl.BottomPadding = 2; $tbl.LeftPadding = 5; $tbl.RightPadding = 5
    $rf = $tbl.Range.ParagraphFormat
    $rf.ReadingOrder = 0; $rf.FirstLineIndent = 0; $rf.LeftIndent = 0; $rf.RightIndent = 0; $rf.Alignment = 0
    $rf.SpaceBefore = 0; $rf.SpaceAfter = 0; $rf.LineSpacingRule = 0; $rf.KeepWithNext = 0; $rf.PageBreakBefore = 0
    for ($r = 0; $r -lt $baris.Count; $r++) {
        $x = $tbl.Cell($r + 1, 1).Range; $x.Collapse(1); $x.Select()
        Runs $baris[$r].runs $uTabel $false
        $y = $tbl.Cell($r + 1, 2).Range; $y.ParagraphFormat.ReadingOrder = 1; $y.Collapse(1); $y.Select()
        $awal = $sel.Start
        Tulis ([string]$baris[$r].paralel) 'Times New Roman' $uLatin 0 0
        $doc.Range($awal, $sel.Start).Select(); $word.Selection.LtrRun()
    }
    $doc.Range($tbl.Range.End, $tbl.Range.End).Select()
    if ($i + 1 -lt $DATA.blok.Count -and $DATA.blok[$i + 1].k -eq 'J') {   # tabel #J tepat sesudahnya tidak digabung Word
        Para 1 0 0; $sel.ParagraphFormat.LineSpacingRule = 4; $sel.ParagraphFormat.LineSpacing = 2; $sel.TypeParagraph()
    }
    return $i
}

# #Z: tiga bintang Arab «٭» (U+066D) di tengah, rapat; «*» Latin tercetak kecil dan naik di huruf Arab
function Tulis-Pemisah($pb) {
    Para 1 3 0; HalamanBaru $pb
    Tulis '٭     ٭     ٭' $TA $uMatan 0 0
    $sel.ParagraphFormat.SpaceAfter = 3
    $sel.TypeParagraph()
}
