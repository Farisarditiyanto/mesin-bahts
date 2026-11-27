# SPDX-License-Identifier: AGPL-3.0-or-later
# فهرس sesudah isi selain المصادر dan الموضوعات: الآيات، الأحاديث، الآثار، فهرس nama ({N:}، {M:}، {B:}، {QB:}، {G:}),
# dan الأشعار. Di-dot-source rakit.ps1 dan memakai $word, $doc, $sel, $sec, Para, Tulis, Tabel, Sel, Huruf, Angka, Hal,
# Rentang, serta huruf/ukuran profil miliknya. Yang dicetak, urutan, judul, dan bentuk tiap فهرس sudah diputuskan
# olah.bagian_akhir ($bg = satu butir $RENCANA.bagian); di sini hanya cara menulisnya.
# Tiap penulis mencatat tempat nomor halamannya lewat Catat-Isian; rakit.ps1 bagian 4 memanggil Isi-Fihris sampai tetap.

$script:isian = New-Object System.Collections.ArrayList
# satu isian: halaman bookmark $k (beberapa digabung «، »; $rentang = angka berurutan jadi «٢٥-٢٩», untuk فهرس nama),
# ditulis di bookmark $tujuan.bm (baris bertitik) atau sel $tujuan.tbl/r/c (tebal $tujuan.tebal)
function Catat-Isian($k, $rentang, $tujuan) { [void]$script:isian.Add(@{ k = @($k); rentang = $rentang; t = $tujuan; lama = $null }) }

# Isi tiap nomor halaman فهرس yang berubah; kembalikan jumlah yang berubah (0 = sudah tetap)
function Isi-Fihris {
    $ubah = 0
    foreach ($e in $script:isian) {
        $hal = @($e.k | ForEach-Object { Hal $_ } | Select-Object -Unique)
        $pg = Angka $(if ($e.rentang) { Rentang $hal } else { $hal -join '، ' })
        if ($e.lama -eq $pg) { continue }
        $e.lama = $pg; $ubah++
        $t = $e.t
        if ($t.bm) { $x = $doc.Bookmarks.Item($t.bm).Range; $x.Text = $pg; [void]$doc.Bookmarks.Add($t.bm, $x) }
        else { Sel $t.tbl $t.r $t.c $pg 1 ([int]$t.tebal) }
    }
    return $ubah
}

# satu baris «teks (kecil) ...... ص» tanpa tabel: titik-titik sampai nomor halaman di tepi kiri; $kecil (راوٍ/قائل) dalam
# kurung sebesar catatan kaki
function Baris-Titik($teks, $kecil, $k, $rentang) {
    $lebar = $sec.PageSetup.PageWidth - $sec.PageSetup.LeftMargin - $sec.PageSetup.RightMargin
    Para 3 0 0
    $pf = $sel.ParagraphFormat; $pf.Alignment = 0; $pf.SpaceAfter = 6
    $pf.TabStops.ClearAll(); [void]$pf.TabStops.Add($lebar, 2, 1)   # 2 = rata ujung (kiri di teks kanan-ke-kiri), 1 = titik-titik
    Tulis $teks $TA $uMatan 0 0
    if ($kecil) { Tulis (' (' + $kecil + ')') $TA $uCatatan 0 0 }
    Tulis " `t " $TA $uMatan 0 0                   # spasi di kedua sisi tab: titik-titik tidak menempel ke teks atau nomor
    $awal = $sel.Start; Tulis (Angka '00') $TA $uMatan 0 0
    $bm = "fi_$($script:isian.Count)"
    [void]$doc.Bookmarks.Add($bm, $doc.Range($awal, $sel.Start))
    Catat-Isian $k $rentang @{ bm = $bm }
    $sel.TypeParagraph()
}

# judul kelompok di dalam فهرس tanpa tabel («حرف الهمزة»): tengah, tebal, menempel ke baris pertamanya
function Judul-Kelompok($teks, $pertama) {
    Para 1 $(if ($pertama) { 0 } else { 12 }) 0
    $sel.ParagraphFormat.SpaceAfter = 6; $sel.ParagraphFormat.KeepWithNext = -1
    Tulis $teks $TJ $uJudulSub 1 0
    $sel.TypeParagraph()
}

# tabel bergaris dengan kepala berlatar abu-abu (seperti #J), diulang di halaman sambungan
function Tabel-Kepala($baris, $lebar, $kepala) {
    $tbl = Tabel ($baris + 1) $lebar 1
    for ($c = 1; $c -le $kepala.Count; $c++) { Sel $tbl 1 $c $kepala[$c - 1] 1 1 }
    Huruf ($tbl.Rows(1).Range.Font) $TJ
    $tbl.Rows(1).Shading.BackgroundPatternColor = 14277081   # abu-abu muda (RGB 217,217,217)
    $tbl.Rows(1).HeadingFormat = -1
    return $tbl
}

# sel ayat «﴿potongan﴾»: huruf mushaf hanya untuk kata-kata ayat; titik-titik « ...» tetap huruf matan (huruf mushaf
# tidak punya titik)
function Sel-Ayat($tbl, $r, $c, $pot, $ekor) {
    $rg = $tbl.Cell($r, $c).Range; $rg.Text = '﴿' + $pot + '﴾' + $ekor; $rg.ParagraphFormat.Alignment = 3
    $nq = if ($pot.EndsWith(' ...')) { $pot.Length - 4 } else { $pot.Length }
    $q = $tbl.Cell($r, $c).Range; $q.SetRange($rg.Start + 1, $rg.Start + 1 + $nq); Huruf $q.Font $QF $uAyat
}

# فهرس الآيات: satu baris per ayat (ayat yang sama di beberapa tempat = satu baris), urut mushaf. Bentuk $bg.bentuk:
# tabel = الآية | السورة | رقمها | الصفحة; surah = السورة (digabung per surat) | الآية «… الآية n» | الصفحة; titik = nama
# surat lalu «﴿… n﴾ ...... ص»; baris_surah = الآية | رقمها | الصفحة dengan baris surat «٢- سورة البقرة» selebar tabel;
# terbuka = kolom tabel tanpa garis tegak, garis hanya di atas/bawah kepala dan di akhir tabel
function Fihris-Ayat($bg) {
    $ay = @{}; $urut = New-Object System.Collections.ArrayList
    foreach ($a in $DATA.ayat) {
        $key = '{0:D3}:{1}' -f [int]$a.s, $a.a
        if (-not $ay.ContainsKey($key)) { $ay[$key] = @{ t = $a.t; surah = $a.surah; a = $a.a; bm = @($a.k); s = [int]$a.s; n = [int](($a.a -split '-')[0]) }; [void]$urut.Add($key) }
        else { $ay[$key].bm += $a.k; if ($a.t.Length -gt $ay[$key].t.Length) { $ay[$key].t = $a.t } }
    }
    $urut = @($urut | Sort-Object { $ay[$_].s }, { $ay[$_].n })
    foreach ($key in $urut) {                            # potongan awal ayat: 4 kata (5 kalau kata ke-4 pendek), lalu « ...»
        $kata = $ay[$key].t -split ' '
        $nk = 4; if ($kata.Count -gt 5 -and $kata[3].Length -le 3) { $nk = 5 }
        $ay[$key].pot = if ($kata.Count -gt $nk) { ($kata[0..($nk - 1)] -join ' ') + ' ...' } else { $ay[$key].t }
    }
    switch ($bg.bentuk) {
    'titik' {
        $sTadi = -1
        foreach ($key in $urut) {
            $a = $ay[$key]
            if ($a.s -ne $sTadi) {                       # nama surat: tebal, menempel ke ayat pertamanya
                Para 3 $(if ($sTadi -ge 0) { 12 } else { 0 }) 0
                $sTadi = $a.s
                $sel.ParagraphFormat.Alignment = 0; $sel.ParagraphFormat.SpaceAfter = 4; $sel.ParagraphFormat.KeepWithNext = -1
                Tulis ('سورة ' + $a.surah) $TA $uMatan 1 0
                $sel.TypeParagraph()
            }
            $lebar = $sec.PageSetup.PageWidth - $sec.PageSetup.LeftMargin - $sec.PageSetup.RightMargin
            Para 3 0 0
            $pf = $sel.ParagraphFormat; $pf.Alignment = 0; $pf.SpaceAfter = 4; $pf.RightIndent = $word.CentimetersToPoints(0.6)
            $pf.TabStops.ClearAll(); [void]$pf.TabStops.Add($lebar, 2, 1)   # 2 = rata ujung (kiri di teks kanan-ke-kiri), 1 = titik-titik
            # tanda akhir ayat di dalam potongan ayat rentang dibuang: nomornya dicetak sekali di ujung
            $pot = ($a.pot -replace '\s*[٠-٩۝]+(?=\s|$)', '') -replace '\s{2,}', ' '
            $nq = if ($pot.EndsWith(' ...')) { $pot.Length - 4 } else { $pot.Length }
            Tulis '﴿' $TA $uMatan 0 0
            Tulis $pot.Substring(0, $nq) $QF $uAyat 0 0
            Tulis ($pot.Substring($nq) + ' ') $TA $uMatan 0 0
            # nomor ayat seperti di mushaf, di dalam kurung: huruf mushaf menggambar angka ٠-٩ sebagai bulatan akhir ayat
            $nomor = @(([string]$a.a -split '-') | ForEach-Object { -join ($_.ToCharArray() | ForEach-Object { [char](0x0660 + [int]$_ - 48) }) })
            for ($i = 0; $i -lt $nomor.Count; $i++) {
                if ($i) { Tulis ' - ' $TA $uMatan 0 0 }
                Tulis $nomor[$i] $QF $uAyat 0 0
            }
            Tulis ("﴾ `t ") $TA $uMatan 0 0              # spasi di kedua sisi tab: titik-titik tidak menempel ke ﴾ atau nomor halaman
            $awalNo = $sel.Start; Tulis (Angka '00') $TA $uMatan 0 0
            $bm = "fi_$($script:isian.Count)"
            [void]$doc.Bookmarks.Add($bm, $doc.Range($awalNo, $sel.Start))
            Catat-Isian $a.bm $false @{ bm = $bm }
            $sel.TypeParagraph()
        }
    }
    'surah' {
        $tAy = Tabel ($urut.Count + 1) @(2.6, 10.4, 2.0) 1; Sel $tAy 1 1 'السورة' 1 1; Sel $tAy 1 2 'الآية' 1 1; Sel $tAy 1 3 'الصفحة' 1 1
        $r = 1
        foreach ($key in $urut) {
            $r++; $a = $ay[$key]
            Sel-Ayat $tAy $r 2 $a.pot (' الآية ' + (Angka $a.a))
            Huruf ($tAy.Cell($r, 2).Range.Font) $null $uCatatan   # contoh: sel ayat kecil (14)
            Sel $tAy $r 1 $a.surah 1 0
            Sel $tAy $r 3 (Angka '00') 1 0
            Catat-Isian $a.bm $false @{ tbl = $tAy; r = $r; c = 3; tebal = 1 }
        }
        Huruf ($tAy.Rows(1).Range.Font) $TJ
        $akhirS = $urut.Count + 1                        # gabung sel السورة yang sama, dari bawah supaya nomor baris tetap
        for ($r = $urut.Count + 1; $r -ge 2; $r--) {
            $atas = if ($r -gt 2) { $ay[$urut[$r - 3]].s } else { -1 }
            if ($atas -ne $ay[$urut[$r - 2]].s) {
                if ($akhirS -gt $r) {
                    $tAy.Cell($r, 1).Merge($tAy.Cell($akhirS, 1))
                    Sel $tAy $r 1 $ay[$urut[$r - 2]].surah 1 0
                }
                $tAy.Cell($r, 1).VerticalAlignment = 1; $akhirS = $r - 1
            }
        }
    }
    'baris_surah' {
        $surat = @($urut | ForEach-Object { $ay[$_].s } | Select-Object -Unique)
        $tAy = Tabel-Kepala ($urut.Count + $surat.Count) @(10.0, 2.5, 2.5) @('الآية', 'رقمها', 'الصفحة')
        $r = 1; $sTadi = -1; $gabung = @()
        foreach ($key in $urut) {
            $a = $ay[$key]
            if ($a.s -ne $sTadi) {                       # baris surat: digabung selebar tabel sesudah semua sel ditulis
                $r++; $sTadi = $a.s; $gabung += , @($r, ((Angka $a.s) + '- سورة ' + $a.surah))
            }
            $r++
            Sel-Ayat $tAy $r 1 $a.pot ''
            Sel $tAy $r 2 (Angka $a.a) 1 0
            Sel $tAy $r 3 (Angka '00') 1 0
            Catat-Isian $a.bm $false @{ tbl = $tAy; r = $r; c = 3; tebal = 0 }
        }
        foreach ($g in $gabung) {
            $tAy.Cell($g[0], 1).Merge($tAy.Cell($g[0], 3))
            Sel $tAy $g[0] 1 $g[1] 1 1
            $tAy.Rows($g[0]).Range.ParagraphFormat.KeepWithNext = -1
        }
    }
    default {                                            # tabel dan terbuka
        $tAy = Tabel ($urut.Count + 1) @(7.9, 2.6, 2.5, 2.0) $(if ($bg.bentuk -eq 'terbuka') { 0 } else { 1 })
        Sel $tAy 1 1 'الآية' 1 1; Sel $tAy 1 2 'السورة' 1 1; Sel $tAy 1 3 'رقمها' 1 1; Sel $tAy 1 4 'الصفحة' 1 1
        $r = 1
        foreach ($key in $urut) {
            $r++; $a = $ay[$key]
            Sel-Ayat $tAy $r 1 $a.pot ''
            Sel $tAy $r 2 $a.surah 1 0; Sel $tAy $r 3 (Angka $a.a) 1 0
            Sel $tAy $r 4 (Angka '00') 1 0
            Catat-Isian $a.bm $false @{ tbl = $tAy; r = $r; c = 4; tebal = 0 }
        }
        if ($bg.bentuk -eq 'terbuka') { Garis-Terbuka $tAy }
    }
    }
}

# tabel tanpa garis (bentuk terbuka): garis mendatar hanya di atas dan bawah kepala dan di akhir tabel; kepala diulang
function Garis-Terbuka($tbl) {
    foreach ($g in @(@(1, -1), @(1, -3), @($tbl.Rows.Count, -3))) { $x = $tbl.Rows($g[0]).Borders.Item($g[1]); $x.LineStyle = 1; $x.LineWidth = 6 }
    $tbl.Rows(1).HeadingFormat = -1
}

# فهرس الأحاديث (jenis hadits) dan فهرس الآثار (jenis atsar, selalu titik dengan القائل): bentuk $bg.bentuk
# terbuka = طرف | الراوي | الصفحة tanpa garis tegak (Garis-Terbuka); tabel = kolom yang sama bergaris penuh; ringkas =
# الأحاديث | الصفحة; titik = «طرف ...... ص», atau «طرف (الراوي) ...... ص» kalau $bg.rawi; huruf = sama, dikelompokkan
# per حرف ($bg.kelompok)
function Fihris-Hadits($bg) {
    $baris = @($DATA.($bg.jenis))
    $kunci = { param($h) $ks = @($h.k); if ($h.lagi) { $ks += $h.lagi }; , $ks }
    if ($bg.bentuk -in 'terbuka', 'tabel', 'ringkas') {
        $ringkas = $bg.bentuk -eq 'ringkas'
        $cH = if ($ringkas) { 2 } else { 3 }
        if ($ringkas) { $tHd = Tabel ($baris.Count + 1) @(7.5, 7.5) 1; Sel $tHd 1 1 'الأحاديث' 1 1; Sel $tHd 1 2 'الصفحة' 1 1; Huruf ($tHd.Rows(1).Range.Font) $TJ }
        else { $tHd = Tabel ($baris.Count + 1) @(8.6, 4.4, 2.0) $(if ($bg.bentuk -eq 'terbuka') { 0 } else { 1 }); Sel $tHd 1 1 $bg.kolom 1 1; Sel $tHd 1 2 'الراوي' 1 1; Sel $tHd 1 3 'الصفحة' 1 1 }
        if ($bg.bentuk -eq 'terbuka') { Garis-Terbuka $tHd }
        $r = 1
        foreach ($h in $baris) {
            $r++
            if ($ringkas) { Sel $tHd $r 1 ('(' + $h.t + ')') 3 0; Huruf ($tHd.Cell($r, 1).Range.Font) $null 12 } else { Sel $tHd $r 1 ('«' + $h.t + '»') 3 0; Sel $tHd $r 2 $h.r 1 0 }
            Sel $tHd $r $cH (Angka '00') 1 0
            Catat-Isian (& $kunci $h) $false @{ tbl = $tHd; r = $r; c = $cH; tebal = [int]$ringkas }
        }
        return
    }
    $i = 0
    foreach ($h in $baris) {
        if ($bg.kelompok -and $bg.kelompok[$i]) { Judul-Kelompok $bg.kelompok[$i] ($i -eq 0) }
        Baris-Titik $h.t $(if ($bg.rawi) { $h.r }) (& $kunci $h) $false
        $i++
    }
}

# فهرس nama: bentuk $bg.bentuk tabel = kolom | الصفحة; nomor = م | kolom | الصفحة berkepala abu-abu; titik = «nama ...... ص»
function Fihris-Nama($bg) {
    $nm = @($DATA.($bg.jenis))
    if ($bg.bentuk -eq 'titik') { foreach ($a in $nm) { Baris-Titik $a.t $null $a.k $true }; return }
    if ($bg.bentuk -eq 'nomor') { $tN = Tabel-Kepala $nm.Count @(1.2, 10.3, 3.5) @('م', $bg.kolom, 'الصفحة'); $cN = 2 }
    else { $tN = Tabel ($nm.Count + 1) @(10.0, 5.0) 1; Sel $tN 1 1 $bg.kolom 1 1; Sel $tN 1 2 'الصفحة' 1 1; $cN = 1 }
    $r = 1
    foreach ($a in $nm) {
        $r++
        if ($cN -eq 2) { Sel $tN $r 1 (Angka ($r - 1)) 1 0 }
        Sel $tN $r $cN $a.t 3 0; Sel $tN $r ($cN + 1) (Angka '00') 1 0
        Catat-Isian $a.k $true @{ tbl = $tN; r = $r; c = $cN + 1; tebal = 0 }
    }
    $tN.Rows(1).HeadingFormat = -1                        # judul kolom diulang di halaman sambungan
}

# فهرس الأشعار: م | صدر البيت | القافية | القائل | الصفحة, urut حرف الروي (olah._urutkan_fihris)
function Fihris-Syir($bg) {
    $vs = @($DATA.syir)
    $tV = Tabel-Kepala $vs.Count @(1.0, 6.8, 2.4, 2.8, 2.0) @('م', 'صدر البيت', 'القافية', 'القائل', 'الصفحة')
    $r = 1
    foreach ($v in $vs) {
        $r++
        Sel $tV $r 1 (Angka ($r - 1)) 1 0; Sel $tV $r 2 $v.t 3 0; Sel $tV $r 3 $v.qf 1 0; Sel $tV $r 4 $v.q 1 0
        Sel $tV $r 5 (Angka '00') 1 0
        Catat-Isian $v.k $false @{ tbl = $tV; r = $r; c = 5; tebal = 0 }
    }
}
