# SPDX-License-Identifier: AGPL-3.0-or-later
# Rakit <Hasil>\<berkas>.docx + .pdf dari bahan JSON -Build (hasil olah.py), memakai Word asli (COM).
# Dipanggil oleh rakit.py, yang menentukan semua jalur di luar <Hasil>\<berkas>; jangan dijalankan langsung.
param([Parameter(Mandatory)][string]$Build, [Parameter(Mandatory)][string]$Hasil, [Parameter(Mandatory)][string]$Laporan,
      [Parameter(Mandatory)][string]$PdfKhulasah, [Parameter(Mandatory)][string]$Kunci, [Parameter(Mandatory)][string]$Galat)
$ErrorActionPreference = 'Stop'
# Galat yang menghentikan skrip ini ditulis juga ke -Galat (UTF-8): rakit.py mengutipnya di pesan GAGAL, karena layar
# bisa dipotong pemanggil (tail/grep) dan huruf Arabnya rusak lewat pipa. Tanpa berkas itu = PowerShell dimatikan dari luar.
trap {
    [IO.File]::WriteAllText($Galat, "$($_.Exception.Message) (rakit.ps1 baris $($_.InvocationInfo.ScriptLineNumber))", (New-Object Text.UTF8Encoding $false))
    break
}
$dir = $PSScriptRoot
. "$dir\word.ps1"
. "$dir\kepala.ps1"                     # kepala/kaki halaman isi (@kepala) dan garis pemisah catatan kaki
. "$dir\pemisah.ps1"                    # halaman pemisah #F (@judul_fasl) dan halaman penutup (@tamma), tanpa nomor
. "$dir\fihris.ps1"                     # فهرس الآيات/الأحاديث/الآثار/nama/الأشعار dan isian nomor halamannya
$DATA = Get-Content -LiteralPath $Build -Raw -Encoding UTF8 | ConvertFrom-Json
$M = $DATA.meta
# Rencana cetak (olah.rencana_cetak): apa yang dicetak dan di mana sudah diputuskan di sana, termasuk bawaan profil.
# Skrip ini tidak mengurai @data berdaftar dan tidak punya bawaan profil sendiri
$RENCANA = $DATA.cetak
$Out = Join-Path $Hasil $M.berkas
$FMT = $RENCANA.format                                   # profil dari format.json (dipilih @format; @catatan_kaki/@spasi sudah ditimpakan), tiap kunci terisi
$TA = [string]$FMT.huruf; $QF = 'KFGQPC HAFS Uthmanic Script'
$uMatan = [single]$FMT.matan; $uCatatan = [single]$FMT.catatan; $uJudul = [single]$FMT.judul   # ukuran huruf (Word minta angka pecahan)
$uJudulSub = [single]$FMT.judul_sub                      # ukuran #B/#M/#S
$uAyat = [single]$FMT.ayat                               # ukuran ayat di matan dan فهرس الآيات
$uTabel = [single][Math]::Ceiling(($uMatan + $uCatatan) / 2)   # sel #J: di antara matan dan catatan kaki (teks_pdf.periksa membaca huruf ini sebagai matan)
$uLatin = [single]$FMT.latin                             # paragraf #L (Times New Roman); judul «#L **…**» 2 poin lebih besar. Times sebesar matan Arab tampak jauh lebih besar dan Abstract luber
$ULANG = if ($FMT.catatan_ulang_tiap_halaman) { 2 } else { 0 }   # nomor catatan kaki: 2 = mulai ulang tiap halaman, 0 = bersambung
$SPASI = [single]$FMT.spasi                              # jarak baris matan dan judul (kali satu baris); catatan kaki dan فهرس tetap satu spasi
$MULAKHAS_JARAK = [bool]$FMT.mulakhas_berjarak   # paragraf di bawah #K الملخص/ملخص البحث: berjarak 6 pt, tanpa awal alinea menjorok
$SPASI_MULAKHAS = [single]$FMT.spasi_mulakhas            # jarak baris bagian #K الملخص… (termasuk الملخص باللغة الأجنبية)
$spasiAktif = $SPASI
# @angka hindi: teks naskah sudah diubah olah.py; nomor yang dihitung di sini (فهرس, المصادر, {P:}) diubah Angka;
# nomor halaman dicetak Word menurut Options.ArabicNumeral (gaya nomor Word «Hindi» = angka India २, bukan ٢)
$HINDI = $M.angka -eq 'hindi'
function Angka($s) {
    $s = [string]$s
    if (-not $HINDI) { return $s }
    return -join ($s.ToCharArray() | ForEach-Object { if ($_ -ge [char]'0' -and $_ -le [char]'9') { [char](0x0660 + [int]$_ - 48) } else { $_ } })
}
# huruf (teks Latin dan Arab sekaligus), ukuran, dan tebal sebuah objek Font Word; yang $null tidak disentuh
function Huruf($font, $nama, $ukuran, $tebal) {
    if ($nama) { $font.Name = [string]$nama; $font.NameBi = [string]$nama }
    if ($null -ne $ukuran) { $font.Size = [single]$ukuran; $font.SizeBi = [single]$ukuran }
    if ($null -ne $tebal) { $font.Bold = [int]$tebal; $font.BoldBi = [int]$tebal }
}
$JUDUL = $M.judul; $NAMA = $M.nama; $NIM = $M.nim
# judul sampul «… - …» sudah dipecah olah.rencana_cetak: bagian sesudah « - » jadi baris kedua yang lebih kecil (kepala halaman tetap judul utuh)
$JUDUL1 = [string]$RENCANA.judul_sampul[0]; $JUDUL2 = [string]$RENCANA.judul_sampul[1]
$MUSYRIF = if ($M.musyrif -and $M.musyrif -ne '-') { [string]$M.musyrif } else { '' }
$JABATAN = if ($MUSYRIF -and $M.jabatan -and $M.jabatan -ne '-') { [string]$M.jabatan } else { '' }
# tahun sampul (qism, jakarta, tengah). Bawaan = tahun hijriah saat tahun ajaran mulai (1 Agustus): satu tahun ajaran
# tetap satu tahun walau 1 Muharram lewat di tengahnya (Juni 2027 = 1449, tahun ajarannya masih 1448)
$awalAjaran = [datetime]::new((Get-Date).Year, 8, 1); if ((Get-Date) -lt $awalAjaran) { $awalAjaran = $awalAjaran.AddYears(-1) }
$TAHUN = if ($M.tahun) { [string]$M.tahun } else { Angka ([Globalization.UmAlQuraCalendar]::new().GetYear($awalAjaran)) }
# @tahun «١٤٤٨ - ٢٠٢٦» (hijriah - masehi) = «١٤٤٨هـ – ٢٠٢٦م»; satu tahun = «١٤٤٨ هـ» seperti model
$TAHUN_CETAK = if ($TAHUN -match '^\s*(\S+?)\s*[-–]\s*(\S+?)\s*$') { "$($Matches[1])هـ – $($Matches[2])م" } else { "$TAHUN هـ" }
$JENIS_BAGIAN = @($RENCANA.bagian | ForEach-Object { $_.jenis })   # المصادر dan فهرس yang dicetak (olah.bagian_akhir)
$adaTo = $JENIS_BAGIAN -contains 'maudhuat'
$ABJAD = [bool]$RENCANA.abjad            # @nomor: halaman sebelum judul $RENCANA.nomor_satu bernomor huruf, mulai judul itu ١، ٢، ٣
# tata letak yang bisa dicampur (olah.GAYA, @model): tiap bagian memilih bentuknya sendiri
$KEPALA = [string]$RENCANA.kepala         # bentuk kepala/kaki halaman isi (kepala.ps1); kotak dan templat = kepala dari berkas Word
$JUDUL_KEPALA = if ($M.kepala_judul) { [string]$M.kepala_judul } else { $JUDUL }
$TO_TITIK = $M.maudhuat -eq 'titik'        # فهرس الموضوعات bertitik-titik tanpa tabel
$PUSTAKA_MUALLIF = $M.pustaka_gaya -eq 'muallif'   # القرآن الكريم bernomor; **…** tebal, __…__ miring
# @pustaka_gaya: judul_tebal: baris tercetak «• **judul**. لفلان …», tanpa nomor (@($null) = satu butir kosong, bukan kosong).
# @() di luar if: hasil if dibuka PowerShell, jadi satu butir saja jadi teks dan [0] = huruf pertamanya
$PUSTAKA_BUTIR = @(if ($RENCANA.pustaka_butir) { $RENCANA.pustaka_butir })
$JUDUL_KOTAK = $RENCANA.judul_fasl -eq 'kotak'   # judul #F di kotak bergaris ganda tebal-tipis
$KANAN = @($RENCANA.judul_kanan)         # judul #B/#M rata kanan
$TJ = [string]$FMT.huruf_judul           # huruf judul (#K/#F/#B/#M/#S dan judul فهرس)
$JARAK_P = [single]$FMT.jarak_paragraf   # pt sesudah paragraf matan
$JARAK_J = [single]$FMT.jarak_judul      # pt sesudah judul #K/#F (baris keduanya kalau dua baris)
$JARAK_FIHRIS = [single]14                # pt sesudah judul المصادر dan tiap فهرس: tabel/daftarnya tidak menempel ke judul
$U_PUSTAKA = [single]$FMT.ukuran_pustaka   # ukuran huruf المصادر
$FIHRIS_SAMBUNG = $M.fihris -eq 'sambung'  # فهرس sesudah yang pertama menyambung di halaman yang sama
$TEPI_KANAN = [single]$FMT.tepi_kanan   # cm
$AWAL_ALINEA = [single]$FMT.awal_alinea   # cm awal baris pertama paragraf matan menjorok

# satu rakit dalam satu waktu: rakit kedua berhenti di sini, sebelum mematikan Word milik rakit pertama (kunci lepas sendiri saat proses ini selesai).
# rakit.py menunggu kunci ini lepas sebelum rakit berikutnya (rakit.ps1 yang Python-nya dimatikan masih memegangnya).
try { $pegangKunci = [IO.File]::Open($Kunci, 'OpenOrCreate', 'ReadWrite', 'None') }
catch { throw "Rakit lain sedang jalan (memakai Word yang sama): tunggu sampai selesai, lalu ulangi." }
# Proses /Automation bisa milik aplikasi lain. Hanya Word yang dibuat di sini yang dibersihkan di finally.
# Rakit yang dimatikan paksa (terminal ditutup) tidak sempat ke finally, dan Word-nya tetap hidup: rakit berikutnya
# mematikan Word yang dicatat rakit itu, asal masih proses yang sama (nomor proses bisa dipakai ulang proses lain)
$CATATAN_WORD = "$dir\_tmp\rakit.word"
try { Bersihkan-WordRakit $CATATAN_WORD } catch { Write-Output "PERINGATAN: Word rakit lama belum bisa dihentikan; catatannya disimpan untuk rakit berikutnya: $($_.Exception.Message)" }
$tmp = "$Hasil\word\kerja.docx"
try {
    [IO.Directory]::CreateDirectory((Split-Path -Parent $tmp)) | Out-Null
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false; $word.ScreenUpdating = $false; $word.DisplayAlerts = 0
    # tanpa catatan, Word rakit ini tidak bisa dibereskan kalau rakit dimatikan paksa; rakitnya sendiri tetap jalan
    try { [void](Catat-WordRakit $word $CATATAN_WORD) } catch { Write-Output "PERINGATAN: proses Word rakit ini tidak dikenali: $($_.Exception.Message)" }
    # pengaturan Word pemakai (berlaku untuk semua dokumennya): dipinjam selama rakit, dikembalikan di finally.
    # 2 = angka di teks Arab dicetak ٠-٩, di teks Latin 0-9; 0 = selalu 0-9
    $numeralLama = $word.Options.ArabicNumeral
    $NUMERAL = if ($HINDI) { 2 } else { 0 }; $word.Options.ArabicNumeral = $NUMERAL
    # huruf profil yang tidak terpasang diganti Word diam-diam: berhenti di sini saja
    if (@($word.FontNames) -notcontains $TA) { throw "Huruf [$TA] belum terpasang di Windows. Jalankan: python mesin/bahts.py periksa" }
    if (@($word.FontNames) -notcontains $TJ) { Write-Output "PERINGATAN: huruf judul $TJ belum terpasang di Windows: judul dicetak $TA."; $TJ = $TA }
    # huruf judul hias (sampul kop/tanpa_kop, judul besar halaman pemisah dan kotak @judul_fasl, halaman penutup @tamma);
    # tidak ikut repo (lisensinya tidak jelas): belum terpasang = huruf judul profil
    $HURUF_HIAS = if (@($word.FontNames) -contains 'PT Bold Heading') { 'PT Bold Heading' } else { $TJ }
    # ---------- 1. Sampul: berangkat dari template sampul ----------
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force }
    # Tampilan Draft selama menyusun: di Print Layout (bawaan kebanyakan pemakai) tiap Select menyusun ulang halaman sampai
    # titik itu (bahts 63 catatan kaki: rakit ±110 detik, Draft ±40). Sebelum .docx disimpan dan sebelum dokumen ditutup
    # kembali ke Print Layout (3): .docx menyimpan tampilannya dan dibuka pemakai dalam tampilan itu, dan Word mengingat
    # tampilan dokumen terakhir sebagai bawaannya. Tampilan awal Word tanpa jendela (Web Layout) bukan tampilan pemakai
    function Draft { $script:draft = $true; $doc.ActiveWindow.View.Type = 1 }
    $TPL = $null; $kepalaTpl = $null
    # FormattedText ke dokumen lain hanya membawa format langsung; yang datang dari gaya templat (arah, rata, garis,
    # huruf judul) disalin per paragraf. Huruf disalin per sifat, hanya yang seragam dalam paragrafnya (bukan 9999999):
    # menyalin objek Font utuh ikut membawa sifat yang tak tentu. Miring hanya disalin kalau templatnya miring: Word
    # melaporkan Italic kop sampul pemakai terbalik menurut arah bagian (0 padahal XML-nya miring, -1 padahal tidak),
    # jadi menyalin Italic=0 malah menulis <w:i/>. Nama huruf per jenis aksara: Name pada teks Arab = huruf Arabnya,
    # dan menulisnya ke Name mengganti huruf Latin paragraf itu
    function SalinGaya($asal, $tujuan) {
        $n = [Math]::Min($asal.Paragraphs.Count, $tujuan.Paragraphs.Count)
        for ($i = 1; $i -le $n; $i++) {
            $pa = $asal.Paragraphs($i); $pt = $tujuan.Paragraphs($i)
            $pt.Format = $pa.Format
            $fa = $pa.Range.Font; $ft2 = $pt.Range.Font
            # sifat ditulis satu-satu: $font.$nama = … pada objek COM diam-diam tidak berpengaruh. Ukuran ditulis [single]:
            # nilai bacaan COM yang ditulis apa adanya ke Size/SizeBi merusak pengikat COM PowerShell 5.1 untuk sifat itu, dan
            # sesudahnya tiap penulisan bilangan bulat ke sifat itu (MuatRumus) di proses ini gagal «Specified cast is not valid»
            $T = 9999999
            if ($fa.Size -ne $T) { $ft2.Size = [single]$fa.Size }; if ($fa.SizeBi -ne $T) { $ft2.SizeBi = [single]$fa.SizeBi }
            if ($fa.Bold -ne $T) { $ft2.Bold = $fa.Bold }; if ($fa.BoldBi -ne $T) { $ft2.BoldBi = $fa.BoldBi }
            if ($fa.Italic -eq -1) { $ft2.Italic = -1 }; if ($fa.ItalicBi -eq -1) { $ft2.ItalicBi = -1 }
            if ($fa.NameAscii) { $ft2.NameAscii = $fa.NameAscii }; if ($fa.NameOther) { $ft2.NameOther = $fa.NameOther }; if ($fa.NameBi) { $ft2.NameBi = $fa.NameBi }
        }
    }
    function Ganti($p, $teks) { $r = $p.Range; [void]$r.MoveEnd(1, -1); $r.Text = $teks }
    function KosongkanKepalaKaki { foreach ($h in 1..3) { try { $doc.Sections(1).Headers($h).Range.Text = '' } catch {} ; try { $doc.Sections(1).Footers($h).Range.Text = '' } catch {} } }
    # judul dikecilkan sampai muat satu baris (mis. utama 36 -> 26, baris kedua 26 -> 22); yang tetap terlalu panjang diratakan:
    # tepi kiri-kanan paragrafnya dilebarkan 6 pt demi 6 pt selama jumlah barisnya tetap, jadi tiap baris kira-kira sama
    # panjang dan baris terakhir tidak tinggal satu kata («… وأوضح / المسالك»)
    function Seimbang($p, $uk, $kecil) {
        while ($uk -gt $kecil -and $p.Range.ComputeStatistics(1) -gt 1) { $uk -= 2; Huruf $p.Range.Font $null $uk }
        $n = $p.Range.ComputeStatistics(1); if ($n -le 1) { return }
        $pf = $p.Range.ParagraphFormat
        for ($tepi = 6; $tepi -le 180; $tepi += 6) {
            $pf.LeftIndent = [single]$tepi; $pf.RightIndent = [single]$tepi
            if ($p.Range.ComputeStatistics(1) -gt $n) { $pf.LeftIndent = [single]($tepi - 6); $pf.RightIndent = [single]($tepi - 6); break }
        }
    }
    function MuatSampul($judulPars, $ukAwal, $rapat) {
        # ComputeStatistics(2) requires Print Layout view; Draft view suppresses pagination.
        $doc.ActiveWindow.View.Type = 3
        $doc.Content.InsertParagraphAfter()
        $uk = $ukAwal; $kecil = $false
        while ($uk -gt 14 -and $doc.ComputeStatistics(2) -gt 1) {
            $uk--; $kecil = $true
            foreach ($q in @($judulPars)) {
                if ($q -and $q.Range.Font.SizeBi -gt $uk) { Huruf $q.Range.Font $null $uk }
            }
        }
        if ($kecil) {
            foreach ($q in @($judulPars)) { if ($q) { $q.LeftIndent = 0; $q.RightIndent = 0; $u = $q.Range.Font.SizeBi; Seimbang $q $u $u } }
        }
        & $rapat
        if ($doc.ComputeStatistics(2) -gt 1) {
            Write-Output "PERINGATAN: judul terlalu panjang untuk sampul $($RENCANA.sampul): sampulnya jadi dua halaman. Pendekkan @judul."
        }
        [void]$doc.Paragraphs.Last.Range.Delete()
        Draft
    }
    # logo جامعة الإمام berwarna = gambar word/media/image2.png sampul_jakarta.docx (bytes PNG), dipakai @logo: berwarna dan
    # @sampul: tengah (.github/uji_struktur.py menjaga gambarnya)
    Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
    $LOGO = 'word/media/image2.png'
    function LogoBerwarna {
        $z = [IO.Compression.ZipFile]::OpenRead("$dir\sampul_jakarta.docx")
        try { $s = $z.GetEntry($LOGO).Open(); $ms = New-Object IO.MemoryStream; $s.CopyTo($ms); $s.Dispose(); return , $ms.ToArray() } finally { $z.Dispose() }
    }
    if ($RENCANA.sampul -in 'qism', 'jakarta') {
    # @sampul: qism = model قسم الشريعة (logo, judul dalam kurung, العام الجامعي): teks penanda diganti, bentuknya dari templat
    # jakarta = sama, dari sampul_jakarta.docx: «قسم الشريعة بجاكرتا», logo berwarna, baris @sifat, nomor tanpa «الرقم الجامعي:»
    $JAKARTA = $RENCANA.sampul -eq 'jakarta'
    $SAMPUL = if ($JAKARTA) { "$dir\sampul_jakarta.docx" } else { "$dir\sampul_qism.docx" }
    # @logo: berwarna = salinan sampul_qism.docx yang gambar logonya (word/media/image2.png) diganti logo berwarna
    # sampul_jakarta.docx; kop, data, dan tata letak sampul qism tetap (.github/uji_struktur.py menjaga kedua gambarnya)
    if ($RENCANA.logo_berwarna) {
        $warna = LogoBerwarna
        $SAMPUL = Join-Path (Split-Path -Parent $tmp) 'sampul_logo_berwarna.docx'
        Copy-Item -LiteralPath "$dir\sampul_qism.docx" -Destination $SAMPUL -Force
        $z = [IO.Compression.ZipFile]::Open($SAMPUL, 'Update')
        try { $z.GetEntry($LOGO).Delete(); $s = $z.CreateEntry($LOGO).Open(); $s.Write($warna, 0, $warna.Length); $s.Dispose() } finally { $z.Dispose() }
    }
    $doc = $word.Documents.Open($SAMPUL, $false, $true)
    $doc.SaveAs2($tmp, 16)
    Draft
    $pJudul = $null; $pSub = $null; $buang = @()
    foreach ($p in @($doc.Paragraphs)) {
        $t = $p.Range.Text.Trim()
        if ($t -eq 'عنوان البحث') { Ganti $p $JUDUL1; $pJudul = $p }
        # sub-judul (bagian judul sesudah « - ») dalam kurung; tanpa sub-judul barisnya kosong
        elseif ($t -eq '( موضوع البحث )') { Ganti $p $(if ($JUDUL2) { "( $JUDUL2 )" } else { '' }); $pSub = $p }
        # @jenis dan @nim tercetak kalau diisi; kosong (atau "-") = barisnya dibuang
        elseif ($t -eq 'نوع البحث') { if ($M.jenis -and $M.jenis -ne '-') { Ganti $p ([string]$M.jenis) } else { $buang += $p } }
        elseif ($t -eq 'الرقم الجامعي') { if ($NIM -and $NIM -ne '-') { Ganti $p $(if ($JAKARTA) { Angka $NIM } else { "الرقم الجامعي: $(Angka $NIM)" }) } else { $buang += $p } }
        elseif ($t -eq 'صفة الطالب') { if ($M.sifat -and $M.sifat -ne '-') { Ganti $p ([string]$M.sifat) } else { $buang += $p } }
        # pembimbing: tanpa @musyrif (atau "-") ketiga barisnya kosong; tanpa @jabatan (atau "-") baris jabatannya kosong
        # jakarta: «المشرف:» bertitik dua seperti «إعداد الطالب:» di templat yang sama
        elseif ($t -eq 'المشرف') { if (-not $MUSYRIF) { Ganti $p '' } elseif ($JAKARTA) { Ganti $p 'المشرف:' } }
        elseif ($t -eq 'اسم المشرف') { Ganti $p $MUSYRIF }
        elseif ($t -eq 'الدرجة العلمية للمشرف') { Ganti $p $JABATAN }
        elseif ($t -eq 'إعداد الطالب:') { if ($M.thalibah -eq 'ya') { Ganti $p 'إعداد الطالبة:' } }
        elseif ($t -eq 'اسم الطالب') { Ganti $p $NAMA }
        elseif ($t -eq 'السنة الهجرية') { Ganti $p $TAHUN_CETAK }
        # @qism: baris qism model; « // » = pindah baris di paragraf yang sama (bentuk dan hurufnya tetap dari templat); di jakarta barisnya di sel tabel (teksnya berakhir tanda sel char 7)
        elseif ($M.qism -and $t.Trim().Trim([char]7) -in 'قسم الشريعة', 'قسم الشريعة بجاكرتا') { Ganti $p (([string]$M.qism -split '\s*//\s*') -join [char]11) }
    }
    if ($JAKARTA) {
        $SM = if (@($word.FontNames) -contains 'Sakkal Majalla') { 'Sakkal Majalla' } else { $TA }
        foreach ($p in @($doc.Paragraphs)) {
            $t = $p.Range.Text.Trim().Trim([char]7); $f = $p.Range.Font
            $u = switch ($t) {
                'المشرف:' { 18, 1, $SM } { $_ -eq $MUSYRIF -and $MUSYRIF } { 18, 1, $SM } { $_ -eq $JABATAN -and $JABATAN } { 18, 0, $SM }
                { $_ -in 'إعداد الطالب:', 'إعداد الطالبة:' } { 16, 1, $SM } $NAMA { 16, 1, $SM }
                { $M.sifat -and $_ -eq [string]$M.sifat } { 16, 0, $SM } { $NIM -and $_ -eq (Angka $NIM) } { 18, 0, $TA }
                'العام الجامعي' { 18, 0, $TA } $TAHUN_CETAK { 18, 0, $TA } 'قسم الشريعة بجاكرتا' { 16, 0, $TA }
            }
            if ($u) { Huruf $f ($u[2]) ($u[0]) ($u[1]); $p.LineSpacingRule = 0 }
        }
    }
    foreach ($p in $buang) { [void]$p.Range.Delete() }
    # huruf judul model (dari templat: PT Bold Heading) belum terpasang = Word diam-diam memakai huruf lain: pakai huruf profil tebal
    $hJudul = $pJudul.Range.Font.NameBi
    if (@($word.FontNames) -notcontains $hJudul) {
        Write-Output "PERINGATAN: huruf $hJudul (judul sampul $($RENCANA.sampul)) belum terpasang di Windows: judul dicetak $TA tebal. Pasang hurufnya, lalu rakit lagi."
        Huruf $pJudul.Range.Font $TA $null 1
    }
    Seimbang $pJudul $(if ($JAKARTA) { 22 } else { 24 }) 18   # judul 24 seperti model (jakarta 22), dikecilkan sampai 18 supaya muat satu baris
    if ($JUDUL2) { Seimbang $pSub 18 16 }
    else { Huruf $pSub.Range.Font $null 2; $pSub.SpaceBefore = 0 }   # tanpa sub-judul: tanpa celah
    MuatSampul @($pJudul, $pSub) $pJudul.Range.Font.SizeBi {
        $pTahun = @($doc.Paragraphs) | Where-Object { $_.Range.Text.Trim() -eq 'العام الجامعي' } | Select-Object -First 1
        while ($pTahun -and $doc.ComputeStatistics(2) -gt 1 -and $pTahun.SpaceBefore -gt 0) { $pTahun.SpaceBefore = [Math]::Max(0, $pTahun.SpaceBefore - 10) }
        foreach ($q in @($doc.Paragraphs)) {
            if ($doc.ComputeStatistics(2) -le 1) { break }
            if ($q.SpaceBefore -gt 0) { $q.SpaceBefore = 0 }
        }
    }
    }
    elseif ($RENCANA.susun) {
    # sampul susunan (olah._sampul_susun: tengah, kop, tanpa_kop), disusun di sini tanpa templat: baris-baris rata tengah
    # tebal, jarak di atas tiap baris dari sana (kop = bertingkat di kanan atas). tengah: logo berwarna di tengah atas
    # dengan rasio gambarnya sendiri, Traditional Arabic 18 (ukuran dan jarak diukur dari contoh PDF المعهد, A4)
    $doc = $word.Documents.Add(); $doc.SaveAs2($tmp, 16); Draft
    KosongkanKepalaKaki
    $p1 = $doc.Sections(1).PageSetup; $p1.PaperSize = 7
    $p1.TopMargin = $word.CentimetersToPoints(2.5); $p1.BottomMargin = $word.CentimetersToPoints(2.5)
    $p1.LeftMargin = $word.CentimetersToPoints(2.5); $p1.RightMargin = $word.CentimetersToPoints(2.5)
    $SS = $RENCANA.susun
    $selT = $word.Selection
    $kopKiri = $p1.PageWidth - $p1.LeftMargin - $p1.RightMargin - $word.CentimetersToPoints(9)   # kop selebar 9 cm di kanan
    function BarisTengah($sebelum, $kop = $false) {
        $pf = $selT.ParagraphFormat
        $pf.Reset(); $pf.ReadingOrder = 0; $pf.Alignment = 1; $pf.LineSpacingRule = 0
        $pf.SpaceBefore = [single]$sebelum; $pf.SpaceAfter = 0; $pf.LeftIndent = 0; $pf.FirstLineIndent = 0
        $pf.RightIndent = [single]$(if ($kop) { $kopKiri } else { 0 })   # kanan-ke-kiri: RightIndent = sisi kiri
    }
    if ($SS.logo) {
        $png = Join-Path (Split-Path -Parent $tmp) 'logo_berwarna.png'
        [IO.File]::WriteAllBytes($png, (LogoBerwarna))
        BarisTengah 6                                    # logo 6 pt di bawah tepi atas 2,5 cm, seperti contoh
        $logo = $selT.InlineShapes.AddPicture($png, $false, $true)
        $logo.LockAspectRatio = -1
        $logo.Width = [single]($logo.Width * 162 / $logo.Height)   # tinggi 162 pt (±5,7 cm) seperti contoh; lebar ikut rasio gambar
        [void]$selT.EndKey(6)
    }
    elseif ($HURUF_HIAS -ne 'PT Bold Heading') {
        Write-Output "PERINGATAN: huruf PT Bold Heading (judul sampul $($RENCANA.sampul)) belum terpasang di Windows: judul dicetak $HURUF_HIAS tebal. Pasang hurufnya, lalu rakit lagi."
    }
    # paragraf dicatat lewat nomornya: $doc.Paragraphs.Last menunjuk paragraf terakhir saat dibaca, bukan saat dicatat
    $nJudul = @(); $nCelah = @(); $nLentur = @(); $baru = [bool]$SS.logo
    foreach ($b in @($SS.baris)) {
        if ($baru) { $selT.TypeParagraph() }; $baru = $true
        BarisTengah $b.atas ($b.jenis -eq 'kop')
        Huruf $selT.Font $(if ($b.hias) { $HURUF_HIAS } else { $TA }) $b.uk 1
        $selT.TypeText((Angka ([string]$b.t).Replace('{tahun}', $TAHUN_CETAK)))
        $n = $doc.Paragraphs.Count
        if ($b.jenis -eq 'judul') { $nJudul += $n }
        if ($b.jenis -eq 'lentur') { $nLentur += $n }
        if ($b.celah) { $nCelah += $n }
    }
    # Paragraph Word lewat pipa PowerShell diurai seperti koleksi (macet): ambil satu-satu dengan Item
    $pJudulT = @(); foreach ($n in $nJudul) { $pJudulT += $doc.Paragraphs.Item($n) }
    $celah = @(); foreach ($n in $nCelah) { $celah += $doc.Paragraphs.Item($n) }
    $lentur = @(); foreach ($n in $nLentur) { $lentur += $doc.Paragraphs.Item($n) }
    # judul yang tidak muat satu baris: dikecilkan sampai 3/4 ukurannya (paling kecil 16), lalu diratakan
    foreach ($p in $pJudulT) { $u = $p.Range.Font.SizeBi; Seimbang $p $u ([Math]::Max(16, [Math]::Round($u * 0.75))) }
    # sampul tetap satu halaman: judul dikecilkan sampai 14, lalu jarak baris celah dipendekkan
    MuatSampul $pJudulT $pJudulT[0].Range.Font.SizeBi {
        foreach ($p in $celah) { if ($doc.ComputeStatistics(2) -gt 1) { $p.SpaceBefore = 6 } }
    }
    if ($lentur.Count) {                                 # sisa tinggi halaman dibagi rata ke jarak di atas baris lentur
        $doc.ActiveWindow.View.Type = 3
        $akhir = $doc.Paragraphs.Last.Range
        $sisa = $p1.PageHeight - $p1.BottomMargin - ($akhir.Information(6) + $akhir.Font.SizeBi * 1.6)   # 6 = atas baris dari tepi kertas
        foreach ($p in $lentur) { $p.SpaceBefore = [single][Math]::Min(1500, $p.SpaceBefore + [Math]::Max(0, $sisa) / $lentur.Count) }
        while ($doc.ComputeStatistics(2) -gt 1) {     # perkiraan tinggi baris terakhir kurang: turunkan lagi sampai muat
            $turun = $false
            foreach ($p in $lentur) { if ($p.SpaceBefore -ge 6) { $p.SpaceBefore = [single]($p.SpaceBefore - 6); $turun = $true } }
            if (-not $turun) { break }
        }
        Draft
    }
    }
    elseif ($RENCANA.sampul -eq 'templat') {
    # @templat: Word mahasiswa sendiri; halaman pertamanya jadi sampul apa adanya, kepala halamannya dipakai di bagian isi
    $doc = $word.Documents.Add(); $doc.SaveAs2($tmp, 16); Draft
    $TPL = $word.Documents.Open($M.templat, $false, $true)
    # sampul = sampai pemisah halaman atau pemisah bagian pertama, bukan sampai halaman 2 tata letak: sampul yang sudah
    # diisi bisa meluap (judul dua baris), dan potongan di halaman 2 diam-diam membuang baris akhirnya («العام الجامعي»)
    $akhir = $TPL.Content.End - 1; $pisah = $false
    $cari = $TPL.Content; $f = $cari.Find; $f.ClearFormatting()
    if ($f.Execute('^m')) { $akhir = $cari.Start; $pisah = $true }
    if ($TPL.Sections.Count -gt 1) { $akhir = [Math]::Min($akhir, $TPL.Sections(2).Range.Start - 1); $pisah = $true }
    if (-not $pisah -and $TPL.ComputeStatistics(2) -gt 1) {
        $akhir = $TPL.GoTo(1, 1, 2).Start - 1
        Write-Output "PERINGATAN: Word @templat lebih dari satu halaman tanpa pemisah halaman sesudah sampulnya: sampul dipotong di akhir halaman pertama dan teks sesudahnya tidak dicetak. Buka Word itu: sampul yang meluap → pendekkan isinya; sesudah sampul → sisipkan pemisah halaman (Ctrl+Enter)."
    }
    $doc.Content.FormattedText = $TPL.Range(0, $akhir).FormattedText
    $doc.Activate()                                      # Selection di bawah milik dokumen aktif; Open membuat templat aktif
    $pt = $TPL.Sections(1).PageSetup; $p1 = $doc.Sections(1).PageSetup
    $p1.SectionDirection = $pt.SectionDirection         # arah bagian dulu: di bagian kanan-ke-kiri tepi kiri dan kanan bertukar
    # kertas sampul = kertas isi (A4, sama dengan bagian isi di bawah), walau Word mahasiswa memakai kertas lain (mis. Letter):
    # bidang teks templat dipertahankan: tepi atas tetap seperti templat (kop tidak turun), selisih tinggi kertas masuk ke
    # tepi bawah, selisih lebar dibagi rata ke kiri dan kanan, jadi letak isi sampul sama dengan Word mahasiswa
    $p1.PaperSize = 7
    $dW = ($p1.PageWidth - $pt.PageWidth) / 2; $tepiMin = $word.CentimetersToPoints(1)
    $p1.TopMargin = $pt.TopMargin; $p1.BottomMargin = [Math]::Max($tepiMin, $pt.BottomMargin + $p1.PageHeight - $pt.PageHeight)
    $p1.LeftMargin = [Math]::Max($tepiMin, $pt.LeftMargin + $dW); $p1.RightMargin = [Math]::Max($tepiMin, $pt.RightMargin + $dW)
    KosongkanKepalaKaki
    # gaya sesudah tata halaman: mengganti arah bagian menyetel ulang huruf paragrafnya
    SalinGaya $TPL.Range(0, $akhir) $doc.Content
    # kotak teks sampul (mis. kop) ikut disalin gayanya, berpasangan menurut urutan
    $ka = @($TPL.Shapes | Where-Object { $_.TextFrame.HasText }); $kt = @($doc.Shapes | Where-Object { $_.TextFrame.HasText })
    for ($i = 0; $i -lt [Math]::Min($ka.Count, $kt.Count); $i++) { SalinGaya $ka[$i].TextFrame.TextRange $kt[$i].TextFrame.TextRange }
    # gambar/kotak yang diletakkan mendatar menurut tepi kertas (bukan kolom, tepi, atau paragraf) digeser sebesar selisih
    # tepinya (tepi atas tidak berubah, jadi letak tegaknya tetap); nilai di bawah -999000 = rata kiri/tengah/kanan Word, tidak digeser
    foreach ($s in $doc.Shapes) {
        if ($s.RelativeHorizontalPosition -eq 1 -and $s.Left -gt -999000) { $s.Left = $s.Left + $dW }
    }
    # di kertas A4 dengan tepi di atas sampul bisa lebih dari satu halaman; dihitung di Print Layout, dengan satu paragraf
    # sementara untuk baris pemisah bagian sesudah sampul (seperti sampul qism)
    $doc.ActiveWindow.View.Type = 3
    $doc.Content.InsertParagraphAfter()
    $nSampul = $doc.ComputeStatistics(2)
    [void]$doc.Paragraphs.Last.Range.Delete()
    Draft
    if ($nSampul -gt 1) {
        Write-Output "PERINGATAN: sampul dari @templat jadi $nSampul halaman di kertas A4: baris akhirnya pindah ke halaman berikutnya. Pendekkan isi sampul di Word @templat (judul, nama kampus) atau kecilkan hurufnya sampai muat satu halaman, lalu rakit lagi."
    }
    } elseif ($RENCANA.sampul -eq 'mahad') {
    $doc = $word.Documents.Open("$dir\sampul.doc", $false, $true)
    $doc.SaveAs2($tmp, 16)
    $doc.Convert()
    Draft
    KosongkanKepalaKaki
    foreach ($s in $doc.Shapes) {
        if ($s.Type -eq 17) {
            $tr = $s.TextFrame.TextRange
            $f = $tr.Find; $f.ClearFormatting(); $f.Replacement.ClearFormatting()
            [void]$f.Execute('الملكة العربية', $true, $false, $false, $false, $false, $true, 0, $false, 'المملكة العربية', 2)
            Huruf $tr.Font $TA 15 1
            $tr.ParagraphFormat.SpaceAfter = 0; $tr.ParagraphFormat.SpaceBefore = 0; $tr.ParagraphFormat.LineSpacingRule = 0
            $s.Height = $s.Height + 45
        }
    }
    $pNama = $null; $pJudul = $null
    foreach ($p in $doc.Paragraphs) {
        $t = $p.Range.Text.Trim()
        if ($t -eq 'عنوان البحث') { Ganti $p $JUDUL1; $pJudul = $p }
        elseif ($t -like 'بحث صفي للمستوى*') { Ganti $p $(if ($M.jenis -eq '-') { '' } else { $M.jenis }) }
        elseif ($t -like 'اسم*الطالبة*') { Ganti $p $(if ($M.thalibah -eq 'ya') { 'اسم الطالبة :' } else { 'اسم الطالب :' }); $pNama = $p }
        elseif ($t -eq '4300000') { Ganti $p $NIM }
        elseif ($t -like 'الفصل الدراسي*') { Ganti $p $M.fasl }
        # pembimbing: tanpa @musyrif (atau "-") ketiga barisnya kosong; tanpa @jabatan (atau "-") baris jabatannya kosong
        elseif ($t -like 'المشرف على البحث*') { if (-not $MUSYRIF) { Ganti $p '' } }
        elseif ($t -eq 'اسم المشرف') { Ganti $p $MUSYRIF }
        elseif ($t -eq 'الدرجة العلمية للمشرف') { Ganti $p $JABATAN }
    }
    $pNama.Range.InsertParagraphAfter()
    $pBaru = $pNama.Next(1); Ganti $pBaru $NAMA
    if ($JUDUL2) { $pJudul.Range.InsertParagraphAfter(); Ganti $pJudul.Next(1) $JUDUL2 }
    foreach ($p in $doc.Paragraphs) {
        $r = $p.Range; $t = $r.Text.Trim()
        if ($t.Length -gt 0) {
            $sz = $r.Font.SizeBi; if ($sz -gt 100) { $sz = 19 }
            $u = if ($t -eq $JUDUL1) { 36 } elseif ($JUDUL2 -and $t -eq $JUDUL2) { 26 } else { [Math]::Max($sz, 20) }
            Huruf $r.Font $TA $u 1
        }
    }
    Seimbang $pJudul 36 26
    if ($JUDUL2) { Seimbang $pJudul.Next(1) 26 22 }
    # buang paragraf kosong di ekor sampul supaya sampul tetap 1 halaman
    while ($doc.Paragraphs.Count -gt 3 -and $doc.Paragraphs.Last.Range.Text.Trim().Length -eq 0 -and $doc.Paragraphs.Last.Previous(1).Range.Text.Trim().Length -eq 0) {
        $doc.Paragraphs.Last.Previous(1).Range.Delete() | Out-Null
    }
    }
    else { throw "Model sampul «$($RENCANA.sampul)» tidak dikenal perakit." }

    # ---------- 2. Bagian isi ----------
    $sel = $word.Selection
    [void]$sel.EndKey(6)
    if ($RENCANA.basmalah) {                             # halaman ﷽ sesudah sampul, masih di bagian sampul (tanpa nomor)
        $hB = 'Arabic Typesetting'                       # ﷽ huruf ini = satu kaligrafi utuh; Traditional Arabic hanya mencetak «بسم»
        if (-not $RENCANA.basmalah_utsmani -and @($word.FontNames) -notcontains $hB) { Write-Output "PERINGATAN: huruf $hB belum terpasang di Windows: halaman basmalah dicetak $TA."; $hB = $TA }
        $sel.InsertBreak(7)
        $sel.ClearFormatting()
        # Word membuang jarak atas paragraf sesudah pindah halaman: turun ke tengah lewat satu paragraf kosong bertinggi pas
        $psS = $doc.Sections(1).PageSetup                # ukuran 72: lebar ﷽ ±14 cm; -40 = ﷽ tepat di tengah bidang sampul qism (diukur di PDF)
        $sel.ParagraphFormat.SpaceBefore = 0; $sel.ParagraphFormat.SpaceAfter = 0
        $sel.ParagraphFormat.LineSpacingRule = 4; $sel.ParagraphFormat.LineSpacing = [single][Math]::Max(1, ($psS.PageHeight - $psS.TopMargin - $psS.BottomMargin) / 2 - 40)
        $sel.TypeParagraph()
        $sel.ParagraphFormat.Alignment = 1; $sel.ParagraphFormat.LineSpacingRule = 0
        if ($RENCANA.basmalah_utsmani) {                 # @basmalah: utsmani = teks Al-Fatihah:1 huruf mushaf (lebar ±14 cm)
            $sel.ParagraphFormat.ReadingOrder = 0; $sel.RtlRun()
            Huruf $sel.Font $QF 40 0
            $sel.TypeText([string]$RENCANA.basmalah_utsmani)
        }
        else {
            Huruf $sel.Font $hB 72 0
            $sel.TypeText([string][char]0xFDFD)
        }
    }
    if ($RENCANA.ayat_pembuka) {                         # @ayat_pembuka: satu halaman ayat sesudah sampul (dan basmalah), tanpa nomor
        $sel.InsertBreak(7)
        $sel.ClearFormatting()
        $psS = $doc.Sections(1).PageSetup                # turun ke sepertiga bidang teks lewat satu paragraf kosong bertinggi pas (lihat basmalah)
        $sel.ParagraphFormat.SpaceBefore = 0; $sel.ParagraphFormat.SpaceAfter = 0
        $sel.ParagraphFormat.LineSpacingRule = 4; $sel.ParagraphFormat.LineSpacing = [single][Math]::Max(1, ($psS.PageHeight - $psS.TopMargin - $psS.BottomMargin) / 3)
        $sel.TypeParagraph()
        $sel.ParagraphFormat.Alignment = 1; $sel.ParagraphFormat.LineSpacingRule = 0; $sel.ParagraphFormat.ReadingOrder = 0
        $sel.ParagraphFormat.LeftIndent = 0; $sel.ParagraphFormat.RightIndent = 0; $sel.ParagraphFormat.FirstLineIndent = 0
        # ﴿﴾ diketik sebagai teks kanan-ke-kiri: di dokumen tanpa templat Arab (sampul tengah = Documents.Add) Word
        # mengetiknya kiri-ke-kanan, jadi ﴿ tercetak di kiri ayat walau paragrafnya kanan-ke-kiri
        $sel.RtlRun()
        Huruf $sel.Font $TA 28 0; $sel.TypeText('﴿')
        Huruf $sel.Font $QF 28 0; $sel.TypeText([string]$RENCANA.ayat_pembuka.t)
        Huruf $sel.Font $TA 28 0; $sel.TypeText('﴾')
        $sel.TypeParagraph()
        $sel.ParagraphFormat.SpaceBefore = 12
        Huruf $sel.Font $TA $uMatan 0; $sel.TypeText((Angka $RENCANA.ayat_pembuka.rujukan))
    }
    $sel.InsertBreak(2)                                  # section break (halaman baru) sesudah sampul
    # potongan `rakit --fasl` selain yang pertama: sampul (bagian Word pertama, berikut pemisahnya) dibuang; tata halaman isi
    # disetel sesudah ini, jadi isinya sama dengan potongan bersampul
    if ($RENCANA.buang_sampul) { [void]$doc.Sections(1).Range.Delete(); [void]$sel.EndKey(6) }
    $sec = $doc.Sections($doc.Sections.Count)
    $ps = $sec.PageSetup
    $ps.PaperSize = 7
    $ps.TopMargin = $word.CentimetersToPoints(2.5); $ps.BottomMargin = $word.CentimetersToPoints(2.5)
    $ps.LeftMargin = $word.CentimetersToPoints(2.5); $ps.RightMargin = $word.CentimetersToPoints($TEPI_KANAN)
    $ps.HeaderDistance = $word.CentimetersToPoints([single]$FMT.jarak_kepala); $ps.FooterDistance = $word.CentimetersToPoints(1.25)
    # nomor halaman dihitung mulai dari المقدمة (bagian isi); kepala dari berkas Word (kotak, @templat) disalin di bawah,
    # dengan nomor di kaki halaman bawaan sampai ternyata kepala itu sudah memuat nomor
    $ft = $sec.Footers(1)
    Pasang-Kepala $sec $(if ($KEPALA -in 'kotak', 'templat') { '-' } else { $KEPALA }) $JUDUL_KEPALA
    $ft.PageNumbers.RestartNumberingAtSection = $true; $ft.PageNumbers.StartingNumber = 1
    if ($ABJAD) { $ft.PageNumbers.NumberStyle = 46 }     # wdPageNumberStyleArabicLetter1: أ ب ت
    $ftIsi = $null; $bagianDepan = $sec.Index
    if ($KEPALA -eq 'kotak' -and -not $TPL) { $TPL = $word.Documents.Open("$dir\kepala_kotak.docx", $false, $true); $doc.Activate() }
    if ($TPL) {                                          # kepala halaman @templat (nomor halamannya di situ): kaki halaman dikosongkan
        function KepalaKosong($h) {
            $nShape = try { $h.Range.ShapeRange.Count } catch { 0 }
            return ($h.Range.Text.Trim() -eq '') -and ($h.Range.Fields.Count -eq 0) -and ($nShape -eq 0) -and ($h.Range.InlineShapes.Count -eq 0)
        }
        $sh0 = $TPL.Sections(1).Headers(1)
        if (KepalaKosong $sh0) {
            for ($s = 2; $s -le $TPL.Sections.Count; $s++) {
                $cand = $TPL.Sections($s).Headers(1)
                if (-not (KepalaKosong $cand)) { $sh0 = $cand; break }
            }
        }
        $hd = $sec.Headers(1); $hd.Range.FormattedText = $sh0.Range.FormattedText
        # FormattedText membawa format langsung saja; arah, rata, dan garis dari gaya «Header» templat disalin per paragraf
        while ($hd.Range.Paragraphs.Count -gt $sh0.Range.Paragraphs.Count) {
            [void]$hd.Range.Paragraphs.Last.Previous(1).Range.Characters.Last.Delete()   # tanda paragraf (bukan $doc.Range: kepala halaman cerita lain)
        }
        SalinGaya $sh0.Range $hd.Range
        # nomor halaman: kalau kepala templat tidak memuat PAGE, nomor di kaki halaman bawaan mesin tetap dicetak
        $adaPage = @($sh0.Range.Fields | Where-Object { $_.Code.Text -match 'PAGE' }).Count -gt 0
        foreach ($sp in @(try { @($sh0.Range.ShapeRange) } catch { })) {
            try { if ($sp.TextFrame.HasText -and @($sp.TextFrame.TextRange.Fields | Where-Object { $_.Code.Text -match 'PAGE' }).Count) { $adaPage = $true } } catch {}
        }
        if ($adaPage) { $ft.Range.Text = '' }
        # penanda judul «عنوان البحث» (kepala_kotak.docx, atau Word @templat yang belum diisi, mis. «قالب إثراء المتون
        # للباحثين») = judul (pendek) bahts ini, di teks kepala halaman dan di kotak teksnya; kurung penandanya ikut diganti.
        # Pencarian tanpa ReplaceWith + penulisan langsung ke Range.Text menghindari batas 255 aksara Find.Execute Word
        $tempat = {
            $out = @($hd.Range)
            foreach ($sp in @(try { @($hd.Range.ShapeRange) } catch { })) {
                try { if ($sp.TextFrame.HasText) { $out += $sp.TextFrame.TextRange } } catch {}
            }
            $out
        }
        foreach ($penanda in '(عنوان البحث)', 'عنوان البحث') {
            foreach ($r in & $tempat) {
                $awal = $r.Start; $batas = $r.End
                while ($awal -lt $batas) {
                    $cari = $r.Duplicate; $cari.SetRange($awal, $batas)
                    $f = $cari.Find; $f.ClearFormatting(); $f.Forward = $true; $f.Wrap = 0
                    if (-not $f.Execute($penanda, $true, $false, $false, $false, $false, $true, 0) -or $cari.Start -lt $awal -or $cari.End -gt $batas) { break }
                    $delta = $JUDUL_KEPALA.Length - $cari.Text.Length
                    $cari.Text = $JUDUL_KEPALA
                    $awal = $cari.End; $batas += $delta
                }
            }
        }
        if ((@(& $tempat | ForEach-Object { $_.Text }) -join ' ') -match 'عنوان البحث' -and $JUDUL_KEPALA -notmatch 'عنوان البحث') {
            Write-Output "PERINGATAN: kepala halaman dari @templat masih mencetak «عنوان البحث» di halaman isi: tulis judul bahts di kepala halaman Word @templat, lalu rakit lagi."
        }
        $TPL.Close(0); $TPL = $null; $doc.Activate(); $script:kepalaTpl = $hd
    }
    # nomor bagian Word yang memegang kepala halaman isi (Periksa-Kepala, kotak teks @templat). Nomor, bukan objek Section:
    # objek bagian terakhir tetap menunjuk bagian terakhir sesudah pemisah bagian baru disisipkan di belakangnya
    $nIsi = $sec.Index
    # Kepala halaman hanya di halaman isi; batasnya dari olah.batas_kepala ($RENCANA.kepala_mulai, bagian «belakang»).
    # Bagian Word baru di kursor, mulai halaman baru, nomornya bersambung; kepala/kaki-nya salinan bagian sebelumnya
    # (dilepas dari sambungannya: kepala isi apa pun, juga kotak dan @templat, tidak perlu dipasang ulang). Halaman
    # pertamanya tidak beda: bagian sesudah halaman pemisah mewarisi «halaman pertama beda» (pemisah.ps1)
    function Bagian-Baru($sudah) {
        if (-not $sudah) {
            $sel.InsertBreak(2)                          # 2 = wdSectionBreakNextPage
            $doc.Sections($doc.Sections.Count).Footers(1).PageNumbers.RestartNumberingAtSection = $false
            # paragraf kosong pembawa pemisah bagian setinggi 1 pt: halaman yang pas penuh tidak tumpah jadi halaman kosong
            $p = $sel.Paragraphs(1).Previous(1)
            if ($p -and $p.Range.Text.Trim([char]13, [char]12, [char]32) -eq '') {
                Huruf $p.Range.Font $null 1; $p.SpaceBefore = 0; $p.SpaceAfter = 0; $p.LineSpacingRule = 4; $p.LineSpacing = 1
                $p.PageBreakBefore = 0
            }
        }
        $s = $doc.Sections($doc.Sections.Count)
        $s.PageSetup.DifferentFirstPageHeaderFooter = 0
        $s.Headers(1).LinkToPrevious = $false; $s.Footers(1).LinkToPrevious = $false
        return $s
    }
    # awal isi ($sudah = kursor sudah di awal bagian Word baru, @nomor): kepala isi pindah ke bagian baru, halaman depan
    # sebelumnya hanya bernomor di tengah kaki
    function Kepala-Mulai($sudah) {
        $s = Bagian-Baru $sudah
        for ($k = $bagianDepan; $k -lt $s.Index; $k++) { Pasang-Kepala $doc.Sections($k) '-' $JUDUL_KEPALA }
        $script:nIsi = $s.Index
    }
    # judul #K/#F halaman isi untuk kepala berjalan (kepala.ps1): bagian Word baru di judul ini (kecuali kursor sudah di
    # awal bagian Word: @nomor, awal isi, judul pertama), kepalanya memuat judul utuh sebagai teks tetap
    function Kepala-Berjalan($berjalan) {
        $s = Bagian-Baru ($sel.Start -eq $sel.Sections(1).Range.Start)
        Ganti-Berjalan $s $KEPALA $JUDUL_KEPALA ([string]$berjalan)
    }
    $st = $doc.Styles.Item(-30)                          # Footnote Text
    Huruf $st.Font $TA $uCatatan
    $st.ParagraphFormat.ReadingOrder = 0; $st.ParagraphFormat.Alignment = 3
    $st.ParagraphFormat.SpaceAfter = 0; $st.ParagraphFormat.SpaceBefore = 0; $st.ParagraphFormat.LineSpacingRule = 0
    $doc.Footnotes.NumberingRule = $ULANG
    $doc.Footnotes.NumberStyle = 0

    function Para($align, $before, $indent) {
        $pf = $sel.ParagraphFormat
        $pf.Reset()
        $pf.ReadingOrder = 0; $pf.Alignment = [int]$align
        $pf.SpaceBefore = [single]$before; $pf.SpaceAfter = 0; $pf.LineSpacingRule = 0
        if ($spasiAktif -ne 1) { $pf.LineSpacingRule = 5; $pf.LineSpacing = $word.LinesToPoints($spasiAktif) }   # 5 = wdLineSpaceMultiple
        $pf.LeftIndent = 0; $pf.RightIndent = 0; $pf.FirstLineIndent = [single]$indent
        $pf.KeepWithNext = 0; $pf.PageBreakBefore = 0; $pf.WidowControl = -1
    }
    # huruf Latin di teks Arab (pola olah.LATIN di bahan): Times New Roman, ukurannya sebanding $FMT.latin terhadap matan.
    # Glyph Latin Traditional Arabic lebar dan, di ukuran yang sama, tampak jauh lebih besar daripada huruf Arabnya.
    # Huruf mengisi Name/Size dan NameBi/SizeBi sekaligus: di run kanan-ke-kiri (catatan kaki) huruf Latin memakai yang Bi
    $rasioLatin = $uLatin / $uMatan
    # Apostrof/tanda petik tipografis (’ ‘ “ ”) yang diketik di teks berhuruf Arab, mis. sesudah «ī» di «al-Qāsimī’s», diberi
    # Word hint eastAsia: run itu memakai huruf East Asian, yang di dokumen ini kosong, jadi tercetak MS Mincho selebar huruf
    # CJK («al-Qāsimī’ s»). Mengganti Name/NameBi tidak membuang hint itu, dan NameFarEast menolak huruf non-East Asian
    # (0x800A16D4). Tanda yang diketik ulang sesudah rentangnya ber-Times dinilai ulang Word tanpa hint
    function PetikUlang($rg, $awal, $teks) {
        foreach ($m in [regex]::Matches($teks, '[‘’“”]')) {   # bukan tanda aslinya: PowerShell membacanya tanda petik kode
            $q = $rg.Duplicate; $q.SetRange($awal + $m.Index, $awal + $m.Index + 1); $q.Text = $m.Value
        }
    }
    function Latin($rg, $awal, $teks, $ukuran) {
        if (-not $teks -or $teks -notmatch $DATA.latin) { return }
        $u = [Math]::Ceiling($ukuran * $rasioLatin)       # matan 18 -> 12, catatan kaki 14 -> 10, sel tabel 16 -> 11
        foreach ($a in [regex]::Matches($teks, $DATA.latin)) {
            $l = $rg.Duplicate; $l.SetRange($awal + $a.Index, $awal + $a.Index + $a.Length); Huruf $l.Font 'Times New Roman' $u $null
            PetikUlang $rg ($awal + $a.Index) $a.Value
        }
    }
    function Tulis($t, $font, $size, $bold, $sup, $warna = -16777216) {
        if (-not $t) { return }
        $awal = $sel.Start
        $sel.InsertAfter($t)
        $f = $sel.Font
        Huruf $f $font $size $bold
        $f.Italic = 0; $f.ItalicBi = 0; $f.Superscript = [int]$sup; $f.Color = [int]$warna
        if ($font -eq $TA -or $font -eq $TJ) { Latin $sel.Range $awal $t $size }
        $sel.Collapse(0)
    }
    # Halaman fisik sebuah posisi (seperti Information(3)) dari awal tiap halaman: GoTo sekali per halaman. Information per
    # catatan kaki menyusun halaman dari awal dokumen tiap dipanggil, makin belakang makin lambat (bahts 63 catatan kaki:
    # ±10 detik per putaran NomorCatatan; dengan GoTo ±0,2 detik). Untuk penanda فهرس (Hal) Information(1) tetap lebih
    # cepat: naskah 187 halaman 7 detik, peta GoTo 9,5
    function AwalHalaman { $n = $doc.ComputeStatistics(2); return , @(for ($k = 1; $k -le $n; $k++) { $doc.GoTo(1, 1, $k).Start }) }
    function HalamanDi($awal, $pos) {
        $lo = 0; $hi = $awal.Count - 1
        while ($lo -lt $hi) { $mid = [int][Math]::Floor(($lo + $hi + 1) / 2); if ($awal[$mid] -le $pos) { $lo = $mid } else { $hi = $mid - 1 } }
        return $lo + 1
    }
    # tautan/DOI (pola olah.TAUTAN) = run kiri-ke-kanan, dicetak apa adanya: di teks kanan-ke-kiri Word (angka konteks)
    # mencetak «doi.org/10.21608/jasis.2021» sebagai «doi.org/١٠,٢١٦٠٨/jasis.٢٠٢١». $teks mulai di posisi $awal cerita $rg
    function Tautan($rg, $awal, $teks) {
        if (-not $teks) { return }
        foreach ($a in [regex]::Matches($teks, $DATA.tautan)) {
            $l = $rg.Duplicate; $l.SetRange($awal + $a.Index, $awal + $a.Index + $a.Length); $l.Select(); $word.Selection.LtrRun()
        }
    }
    # rentang Latin (pola olah.LATIN) di catatan kaki dan المصادر = run kiri-ke-kanan: tanpa itu Word menata rujukan
    # «Journal …, Vol. 3, No. 3, 2022, pp. 25-36.» kanan-ke-kiri (titik pindah ke depan, potongan judul tertukar) dan
    # mencetak angkanya ٠-٩. Nomor catatan kaki, «انظر:», dan pemisah «؛» tetap kanan-ke-kiri
    function LatinLtr($rg, $awal, $teks) {
        if (-not $teks) { return }
        foreach ($a in [regex]::Matches($teks, $DATA.latin)) {
            $ujung = $a.Index + $a.Length
            # titik penutup ikut run itu (tidak pindah ke depan) hanya kalau sebelum rentang ini tidak ada kalimat Arab selain
            # «انظر:»/«ينظر:»/«راجع:» dan pemisah «؛»: rujukan Latin, bukan kalimat Arab yang kebetulan berakhir kata Latin
            $pra = $teks.Substring(0, $a.Index) -replace 'انظر|ينظر|راجع|[\s:؛،]', ''
            if ($ujung -lt $teks.Length -and $teks[$ujung] -eq '.' -and $pra -notmatch '[؀-ۿ]') { $ujung++ }
            $l = $rg.Duplicate; $l.SetRange($awal + $a.Index, $awal + $ujung); $l.Select(); $word.Selection.LtrRun()
        }
    }
    # Nomor sementara pendek: panjang kunci {P:} bukan isi cetak dan tidak boleh mengubah susunan halaman.
    $PENANDA_HALAMAN = '00'
    $rujukanHalaman = @{}; $script:nRujukanHalaman = 0
    # $pg = isi tempat {P:}: '00' untuk teks yang dimasukkan; '__' (bukan angka, sama panjang) untuk mencari angka di teks
    # catatan kaki, supaya nomor halaman sementara tidak ikut dijadikan run kiri-ke-kanan @angka_ayat: latin
    function TeksRuns($runs, $pg = $PENANDA_HALAMAN) { $s = ''; foreach ($r in $runs) { if ($null -ne $r.t) { $s += $r.t } elseif ($r.pg) { $s += $pg } elseif ($r.omml) { $s += 'E' } }; return $s }
    # Paket Flat OPC untuk menyisipkan fragmen OMML (<m:oMath> atau <m:oMathPara>) lewat Range.InsertXML
    function PaketOmml($omml) {
        return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><pkg:package xmlns:pkg="http://schemas.microsoft.com/office/2006/xmlPackage"><pkg:part pkg:name="/_rels/.rels" pkg:contentType="application/vnd.openxmlformats-package.relationships+xml"><pkg:xmlData><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships></pkg:xmlData></pkg:part><pkg:part pkg:name="/word/document.xml" pkg:contentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"><pkg:xmlData><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"><w:body><w:p>' + $omml + '</w:p></w:body></w:document></pkg:xmlData></pkg:part></pkg:package>'
    }
    # Sisipkan OMML di posisi $sel. Penjaga U+200F (RLM) di belakang memastikan kursor keluar dari zona matematika
    # (sehingga teks/tabel sesudahnya tidak masuk ke dalam rumus) sekaligus memulihkan arah kanan-ke-kiri teks Arab.
    function TulisOmml($omml, [bool]$jaga = $true) {
        $pkg = PaketOmml $omml
        if ($jaga) {
            $pos = $sel.Start
            $sel.InsertAfter('X' + [string][char]0x200F)
            $sel.Collapse(0)
            $r = $doc.Range($pos, $pos + 1)
            $r.InsertXML($pkg)
            $akhir = $r.Paragraphs(1).Range.End - 1
            $doc.Range($akhir, $akhir).Select()
        } else {
            $r = $sel.Range.Duplicate
            $r.InsertXML($pkg)
        }
    }
    # Word membalik huruf Arab di dalam <m:f> (dan membalik urutan baris rumus kanan-ke-kiri) bila persamaan
    # baris sendiri (#E) turun ke baris kedua. Perkecil huruf rumus bertahap sampai muat satu baris.
    function MuatRumus($pRange, [string]$omml, [string]$tag = '') {
        if (-not $pRange -or $pRange.OMaths.Count -eq 0 -or $omml -match '<m:(?:eqArr|m)>') { return }
        $omR = $pRange.OMaths(1).Range
        if ($omR.End -le $omR.Start) { return }
        $ujung = $omR.End - 1
        $turun = {
            $a = $doc.Range($omR.Start, $omR.Start); $b = $doc.Range($ujung, $ujung)
            ($a.Information(10) -ne $b.Information(10)) -or ($a.Information(3) -ne $b.Information(3))
        }
        if (-not (& $turun)) { return }
        $ukuran = [int[]](($uMatan - 2)..11 | Where-Object { ($_ -eq 11) -or (([int]$uMatan - $_) % 2 -eq 0) })
        foreach ($sz in $ukuran) {
            $omR.Font.SizeBi = [single]$sz
            $omR.Font.Size = [single][Math]::Max(9, $sz - 2)
            if (-not (& $turun)) { return }
        }
        if ($omml -match '<w:rtl/>') {
            $ket = if ($tag) { " $tag" } else { '' }
            Write-Output "PERINGATAN: persamaan Arab$ket tetap melebihi satu baris walau diperkecil: ringkas atau pecah rumus supaya hurufnya tidak terbalik di Word."
        }
    }
    # nomor catatan kaki = tanda buatan sendiri, bukan nomor otomatis Word: nomor otomatis Word selalu 0-9
    # (Options.ArabicNumeral tidak berlaku untuknya). Nomornya dibetulkan NomorCatatan sesudah halaman tersusun.
    $asalCatatan = New-Object System.Collections.ArrayList   # nomor urut Word -> indeks bahan (bukti diam/potongan bisa melompat)
    function Catatan($idx, $size = $uMatan) {
        [void]$asalCatatan.Add($idx)
        $awal = $sel.Start
        Tulis '(' $TA $size 0 1
        $fn = @(BuatCatatan $sel.Range $idx (Angka ($doc.Footnotes.Count + 1)))[-1]
        $doc.Range($fn.Reference.End, $fn.Reference.End).Select()
        Tulis ')' $TA $size 0 1
        # «(١)» kanan-ke-kiri: tanpa itu kurungnya terbalik di sekitar angka ٠-٩
        $doc.Range($awal, $sel.Start).Select(); $word.Selection.RtlRun(); $sel.Collapse(0)
    }
    function BuatCatatan($rg, $idx, $nomor) {
        $c = $DATA.catatan[$idx]
        $teks = TeksRuns $c.runs
        $fn = $doc.Footnotes.Add($rg, $nomor, (' ' + $teks))
        $fr = $fn.Range                                  # mulai dari spasi di depan teks; tanda + spasi Word di depannya
        Huruf $fr.Font $TA $uCatatan 0; $fr.Font.Superscript = 0; $fr.Font.Color = -16777216
        $fr.Select(); $word.Selection.RtlRun()
        if ($c.al) {   # @angka_ayat: latin: angka di run kiri-ke-kanan dicetak Word 0-9 walau angka konteks
            foreach ($a in [regex]::Matches((TeksRuns $c.runs '__'), '[0-9]+(?:[-–][0-9]+)*')) {
                $l = $fn.Range; $l.SetRange($fr.Start + 1 + $a.Index, $fr.Start + 1 + $a.Index + $a.Length); $l.Select(); $word.Selection.LtrRun()
            }
        }
        Tautan $fn.Range ($fr.Start + 1) $teks
        LatinLtr $fn.Range ($fr.Start + 1) $teks
        Latin $fn.Range ($fr.Start + 1) $teks $uCatatan
        $off = 1
        $fnOmml = New-Object System.Collections.ArrayList
        foreach ($r in $c.runs) {
            $len = 0
            if ($null -ne $r.t) { $len = $r.t.Length } elseif ($r.pg) { $len = $PENANDA_HALAMAN.Length } elseif ($r.omml) { $len = 1; [void]$fnOmml.Add(@{ pos = ($fr.Start + $off); omml = $r.omml }) }
            if ($r.q) { $q = $fn.Range; $q.SetRange($fr.Start + $off, $fr.Start + $off + $len); Huruf $q.Font $QF }
            elseif ($len -and $r.b) {
                $q = $fn.Range; $q.SetRange($fr.Start + $off, $fr.Start + $off + $len)
                Huruf $q.Font $null $null 1
            }
            if ($r.pg) {
                $q = $fn.Range.Duplicate; $q.SetRange($fr.Start + $off, $fr.Start + $off + $len)
                $script:nRujukanHalaman++; $nama = "pgn_$script:nRujukanHalaman"
                [void]$doc.Bookmarks.Add($nama, $q); $rujukanHalaman[$nama] = $r.pg
            }
            $off += $len
        }
        if ($fnOmml.Count) {
            $fnOmml.Reverse()
            foreach ($o in $fnOmml) {
                $q = $fn.Range.Duplicate; $q.SetRange($o.pos, $o.pos + 1)
                $q.InsertXML((PaketOmml $o.omml))
            }
        }
        # nomor di catatan kaki: (1) ukuran normal, bukan superskrip
        $pr = $fr.Paragraphs(1).Range
        $m = $fn.Range; $m.SetRange($pr.Start, $pr.Start + $nomor.Length)
        $m.Font.Superscript = 0; Huruf $m.Font $TA $uCatatan
        $m.InsertBefore('('); $m.InsertAfter(')')
        $m.Font.Superscript = 0
        # nomor di matan: (1) superskrip; kurungnya ditulis Catatan.
        # Di tampilan Draft, $fr.Select() membuka panel catatan kaki (Panes(2)); memindah seleksi balik ke sel tabel #J
        # saat panel itu masih terbuka menjatuhkan WINWORD.EXE (0x800706BE), jadi panel ditutup dulu.
        if ($doc.ActiveWindow.Panes.Count -gt 1) { $doc.ActiveWindow.Panes(2).Close() }
        $ref = $fn.Reference
        $uRef = if ($ref.Information(12)) { $uTabel } else { $uMatan }
        $ref.Font.Superscript = 1; Huruf $ref.Font $TA $uRef
        $ref.Select(); $word.Selection.RtlRun()
        return $fn
    }
    # nomor tercetak: mulai 1 lagi tiap halaman (ULANG 2) atau bersambung. Catatan kaki yang nomornya salah dibuat ulang
    # di tempat yang sama (tanda buatan sendiri tidak bisa diganti); itu bisa menggeser halaman, jadi diulang sampai tetap.
    # Catatan kaki di batas halaman bisa bolak-balik tanpa ujung: nomor awal halaman (١) lebih sempit daripada nomor
    # sambungan halaman sebelumnya (١٢), barisnya naik ke halaman itu, nomornya salah lagi (bahts 143 catatan kaki: 3 rakit
    # gagal). Catatan kaki yang salah lagi pada putaran berikutnya: jarak huruf paragraf matannya digeser sedikit (seperti
    # BarisPendek), supaya batas halamannya pindah dari tempat itu.
    function SalahNomor {
        $doc.Repaginate()
        # halaman hanya dibaca untuk nomor yang mulai ulang tiap halaman, dan hanya kalau ada catatan kaki: AwalHalaman
        # membaca awal tiap halaman (naskah 187 halaman tanpa catatan kaki: ±6 detik untuk apa-apa)
        $ulangHal = $ULANG -eq 2 -and $doc.Footnotes.Count -gt 0
        if ($ulangHal) { $awal = AwalHalaman }
        $salah = @(); $hal = -1; $n = 0; $i = 0
        foreach ($fn in $doc.Footnotes) {
            $i++
            if ($ulangHal) { $p = HalamanDi $awal $fn.Reference.Start; if ($p -ne $hal) { $n = 0; $hal = $p } }
            $n++
            if ($fn.Reference.Text -ne (Angka $n)) { $salah += , @($i, (Angka $n)) }
        }
        return , $salah
    }
    function NomorCatatan {
        $geser = @{}; $salahLalu = @{}                   # nomor urut Word -> langkah jarak huruf yang sudah dipakai
        for ($putaran = 1; $putaran -le 12; $putaran++) {
            $salah = SalahNomor
            if (-not $salah.Count) { return }
            [array]::Reverse($salah)
            foreach ($s in $salah) {
                # objek catatan kaki Word menunjuk nomor urut: hapus dulu, baru buat di tempatnya
                $lama = $doc.Footnotes.Item($s[0]); $pos = $lama.Reference.Start; $lama.Delete()
                [void](BuatCatatan $doc.Range($pos, $pos) $asalCatatan[$s[0] - 1] $s[1])
            }
            $kini = @{}
            foreach ($s in $salah) {
                $i = $s[0]; $kini[$i] = 1
                if (-not $salahLalu.ContainsKey($i)) { continue }
                $k = [int]$geser[$i]; if ($k -ge $GESER_CATATAN.Count) { continue }
                $geser[$i] = $k + 1
                $doc.Footnotes.Item($i).Reference.Paragraphs(1).Range.Font.Spacing = $GESER_CATATAN[$k]
            }
            $salahLalu = $kini
        }
        throw "Nomor catatan kaki belum tetap sesudah 12 putaran penyusunan halaman."
    }
    $GESER_CATATAN = -0.1, -0.2, -0.3, 0.1, 0.2       # pt; sama kecilnya dengan perapatan BarisPendek
    # baris terakhir paragraf yang cuma 1-2 kata ("runt"): jarak huruf paragraf itu dirapatkan 0,1 s.d. 0,3 pt sampai kata
    # itu naik ke baris sebelumnya; tidak berhasil sampai 0,3 = dibiarkan. Hanya paragraf rata kanan-kiri di luar tabel,
    # bukan sub-judul #S (tebal seluruhnya). Baris dihitung di Print Layout: di Draft barisnya bukan baris halaman cetak.
    # Sesudah NomorCatatan (nomor final menentukan lebar baris), lalu NomorCatatan lagi (halaman bisa bergeser).
    # Qulub 27 halaman: runt 22 -> 8, rakit +±30 detik; naskah 162 halaman: 140 -> 50, +±2 menit
    function BarisPendek {
        $doc.ActiveWindow.View.Type = 3; $doc.Repaginate()
        # runt = kata ketiga dari belakang (huruf saja, bukan angka catatan kaki/tanda baca) ada di baris lain daripada akhir paragraf
        # «baris lain» dibaca dari jumlah baris: awal paragraf s.d. kata itu lebih sedikit barisnya daripada seluruh paragraf.
        # Jangan Information(10)/(3) per kata: ±75 ms per panggilan, empat per paragraf (BarisPendek dua kali lebih
        # lama). Rentangnya harus mulai di awal paragraf: jumlah baris rentang yang
        # mulai di tengah paragraf tidak bisa dipakai (selalu 1)
        function Runt($r) {
            $ws = $r.Words; $i = $ws.Count; $n = 0
            while ($i -ge 1) {
                $wd = $ws.Item($i); $i--
                if ($wd.Text -notmatch '\p{L}') { continue }
                $n++; if ($n -eq 3) { return ($doc.Range($r.Start, $wd.End).ComputeStatistics(1) -lt $r.ComputeStatistics(1)) }
            }
            return $false
        }
        $calon = @(foreach ($p in $doc.Paragraphs) {
            $r = $p.Range
            if ($p.Alignment -ne 3 -or $r.Information(12) -or $r.Font.Bold -eq -1 -or $r.ComputeStatistics(1) -lt 2) { continue }
            if (Runt $r) { $p }
        })
        foreach ($p in $calon) {
            $r = $p.Range; $ok = $false
            foreach ($sp in -0.1, -0.2, -0.3) { $r.Font.Spacing = $sp; if (-not (Runt $r)) { $ok = $true; break } }
            if (-not $ok) { $r.Font.Spacing = 0 }
        }
        if ($draft) { $doc.ActiveWindow.View.Type = 1 }
    }
    function Runs($runs, $size, $paksaTebal) {
        foreach ($r in $runs) {
            if ($null -ne $r.fn) { Catatan $r.fn $size }
            elseif ($r.bm) { [void]$doc.Bookmarks.Add($r.bm, $sel.Range) }
            elseif ($r.omml) { TulisOmml $r.omml $true }
            elseif ($r.q) { $u = $size; if ($size -eq $uMatan) { $u = $uAyat }; Tulis $r.t $QF $u 0 0 }
            elseif ($null -ne $r.t) {
                $tb = 0; if ($r.b -or $paksaTebal) { $tb = 1 }
                $awal = $sel.Start; Tulis $r.t $TA $size $tb 0
                if ($r.t -match $DATA.tautan) { $akhir = $sel.Start; Tautan $doc.Content $awal $r.t; $doc.Range($akhir, $akhir).Select() }
            }
        }
    }
    # $kedua = baris kedua judul (@judul_fasl: dua_baris): paragraf sendiri, rata dan ukuran sama, menempel ke baris pertama
    function Judul($teks, $bm, $pb, $k = '', $kedua = '', $atas = 6) {
        Para $(if ($k -in $KANAN) { 3 } else { 1 }) $atas 0  # @judul_kanan: #B/#M rata kanan seperti #S; $atas = olah._jarak_sub
        $sel.ParagraphFormat.KeepWithNext = -1
        # di awal bagian Word (halaman belakang, Bagian-Baru) halamannya sudah baru: pindah halaman lagi = halaman kosong
        if ($pb -and $sel.Start -ne $sel.Sections(1).Range.Start) { $sel.ParagraphFormat.PageBreakBefore = -1; $sel.ParagraphFormat.SpaceBefore = 0 }
        if ($bm) { [void]$doc.Bookmarks.Add($bm, $sel.Range) }
        $kotak = $JUDUL_KOTAK -and $k -eq 'F'; $awalJudul = $sel.Start
        if ($kotak) { Tulis $teks $HURUF_HIAS ($uJudul + 8) 1 0 }   # @judul_fasl: kotak = baris pertama besar, keduanya sebesar judul
        else { Tulis $teks $TJ $(if ($k -in 'B', 'M') { $uJudulSub } else { $uJudul }) 1 0 }
        $sel.TypeParagraph()
        if ($kedua) {
            Para $(if ($k -in $KANAN) { 3 } else { 1 }) $(if ($kotak) { 0 } else { 6 }) 0
            $sel.ParagraphFormat.KeepWithNext = -1
            Tulis $kedua $TJ $(if ($k -in 'B', 'M') { $uJudulSub } else { $uJudul }) 1 0
            $sel.TypeParagraph()
        }
        if ($kotak) { Kotak-Judul $doc.Range($awalJudul, $sel.Start - 1) }
        if ($k -in 'K', 'F' -and $JARAK_J) { $sel.Paragraphs(1).Previous(1).SpaceAfter = $JARAK_J }
    }

    # kotak bergaris ganda (luar tebal, dalam tipis) di sekeliling paragraf judul $r (selebar bidang teks), lalu celah
    # 12 pt tanpa garis sebelum isi: paragraf sesudahnya tidak ikut berbingkai
    function Kotak-Judul($r) {
        $bd = $r.ParagraphFormat.Borders
        # garis ganda Word: yang tebal di sisi bawah/kanan garisnya (9 tipis-tebal, 10 tebal-tipis), jadi garis atas dan kiri
        # memakai 9 dan bawah dan kanan 10 supaya yang tebal selalu di luar (diukur di PDF); 18 = 2,25 pt
        foreach ($g in @(@(-1, 9), @(-2, 9), @(-3, 10), @(-4, 10))) { $x = $bd.Item($g[0]); $x.LineStyle = $g[1]; $x.LineWidth = 18 }
        $bd.DistanceFromTop = 6; $bd.DistanceFromBottom = 6; $bd.DistanceFromLeft = 4; $bd.DistanceFromRight = 4
        $pf = $sel.ParagraphFormat; $pf.Borders.Enable = 0
        $pf.LineSpacingRule = 4; $pf.LineSpacing = 12; $pf.KeepWithNext = -1; $pf.SpaceBefore = 0
        Huruf $sel.Font $TA 2 0
        $sel.TypeParagraph(); $sel.ParagraphFormat.Borders.Enable = 0
    }

    $toc = New-Object System.Collections.ArrayList
    $diMulakhas = $false; $nT = 0; $iR = -1; $berjarakL = $false; $bmMuqaddimah = $null
    function HalamanBaru($pb) { if ($pb) { $sel.ParagraphFormat.PageBreakBefore = -1; $sel.ParagraphFormat.SpaceBefore = 0 } }
    # paragraf pengantar = berakhir «:» (spasi dan nomor catatan kaki di ujung tidak dihitung, mis. «…وفيها قولان:»), atau
    # seluruhnya tebal (**أدلة القول الأول:**): tidak boleh tertinggal sendirian di dasar halaman, daftar/dalilnya di
    # halaman berikutnya. Seperti judul (#S): menempel ke paragraf sesudahnya (KeepWithNext), dan Word memecah paragraf
    # panjangnya sendiri, jadi yang ikut pindah hanya baris terakhirnya. Rangkaian paragraf pengantar berturut-turut
    # hanya dua yang terakhir yang menempel: rantai panjang bisa memindah hampir satu halaman dan menyisakan halaman kosong
    function Pengantar($b) {
        if (-not $b -or $b.k -ne 'P') { return $false }
        $tk = @($b.runs | Where-Object { $null -ne $_.t -and $_.t.Trim() })
        if (-not $tk.Count) { return $false }
        return ($tk[-1].t.TrimEnd() -match ':$') -or (@($tk | Where-Object { -not $_.b }).Count -eq 0)
    }
    function Menempel($j) {
        $nx = $DATA.blok[$j + 1]
        if (-not $nx -or $nx.k -in 'K', 'F', 'B', 'M', 'H', 'R') { return $false }
        return -not ((Pengantar $nx) -and (Pengantar $DATA.blok[$j + 2]))
    }
    # Blok isi ditulis lewat satu scriptblock yang di-dot-source (lingkup yang sama): sekali dari awal sampai #R, dan
    # (@malahiq: akhir) sekali lagi untuk blok sesudah #R, sesudah المصادر والمراجع ditulis
    $mulaiBlok = 0
    $tulisBlok = {
    for ($i = $mulaiBlok; $i -lt $DATA.blok.Count; $i++) {
        $blk = $DATA.blok[$i]
        if ($blk.k -eq 'R') { $iR = $i; break }
        if ($blk.k -eq 'H') { continue }                  # #H: blok sesudahnya mulai halaman baru (sudah masuk $RENCANA.halaman_baru)
        if ($i -eq $RENCANA.maudhuat_awal) {              # @maudhuat_letak: awal — tempat فهرس الموضوعات, diisi sesudah semua judul ditulis (bagian 3)
            Para 1 0 0; $sel.ParagraphFormat.PageBreakBefore = -1
            [void]$doc.Bookmarks.Add('fihris_awal', $sel.Range); $sel.TypeParagraph()
        }
        $pb = $i -in $RENCANA.halaman_baru                # blok ini diawali pindah halaman (olah.awal_halaman)
        if ($blk.k -in 'K', 'F', 'B', 'M') {
            if ($i -eq $RENCANA.nomor_satu) {             # @nomor: #F pertama (mukadimah: المقدمة) = bagian Word baru, nomor kembali ١
                $sel.InsertBreak(2)
                $ftIsi = $doc.Sections($doc.Sections.Count).Footers(1); $ftIsi.LinkToPrevious = $false
                $ftIsi.PageNumbers.NumberStyle = 0; $ftIsi.PageNumbers.RestartNumberingAtSection = $true; $ftIsi.PageNumbers.StartingNumber = 1
                $pb = $false
            }
            if ($i -eq $RENCANA.kepala_mulai) { Kepala-Mulai ($i -eq $RENCANA.nomor_satu); $pb = $false }
            $berjalan = $RENCANA.judul_berjalan."$i"     # bagian, bagian_hias, bergantian: judul ini di kepala bagian Word baru
            if ($berjalan) { Kepala-Berjalan $berjalan; $pb = $false }
            $diMulakhas = $MULAKHAS_JARAK -and ($i -in @($RENCANA.mulakhas.berjarak))
            $spasiAktif = if ($i -in @($RENCANA.mulakhas.spasi)) { $SPASI_MULAKHAS } else { $SPASI }
            $nT++; $bm = "t_$nT"
            if ($i -eq $RENCANA.awal_isi) { $bmMuqaddimah = $bm }   # awal halaman isi (HALAMAN_ISI)
            $dua = $RENCANA.judul_dua_baris."$i"             # @judul_fasl: dua_baris (olah.judul_dua_baris); فهرس tetap $blk.judul
            $atas = if ($null -ne $RENCANA.jarak_sub."$i") { [single]$RENCANA.jarak_sub."$i" } else { 6 }   # jarak_sebelum_sub profil
            $pemisah = $RENCANA.pemisah."$i"               # @judul_fasl: pemisah (olah.halaman_pemisah): halaman sendiri tanpa nomor
            if ($pemisah) { Halaman-Pemisah $pemisah $bm ($RENCANA.judul_fasl -eq 'pemisah_bingkai') }
            elseif ($dua) { Judul $dua[0] $bm $pb $blk.k $dua[1] $atas } else { Judul $blk.judul $bm $pb $blk.k '' $atas }
            $lvl = @{ K = 0; F = 0; B = 1; M = 2 }[$blk.k]
            [void]$toc.Add(@{ t = $blk.judul; bm = $bm; lvl = $lvl })
        }
        elseif ($blk.k -eq 'J') {                         # tabel: baris #J berturut-turut; baris pertama = kepala
            $baris = @($blk); $i0 = $i                    # $i0 = blok baris pertama (kunci $RENCANA.sel_angka)
            while ($i + 1 -lt $DATA.blok.Count -and $DATA.blok[$i + 1].k -eq 'J') { $i++; $baris += $DATA.blok[$i] }
            Para 1 6 0
            HalamanBaru $pb
            $nk = @($baris[0].sel).Count
            $tbl = $doc.Tables.Add($sel.Range, [int]$baris.Count, [int]$nk)
            $tbl.TableDirection = 0                       # kanan ke kiri: kolom pertama naskah di kanan
            $tbl.Borders.Enable = 1
            $tbl.Rows.Alignment = 1
            $tbl.PreferredWidthType = 2; $tbl.PreferredWidth = 100   # selebar halaman
            $tbl.Rows.AllowBreakAcrossPages = -1
            if ($nk -ge 3) {                              # kolom pertama (nama baris) lebih sempit, sisanya dibagi rata
                $tbl.Columns.PreferredWidthType = 2
                $tbl.Columns(1).PreferredWidth = [single]18
                for ($c = 2; $c -le $nk; $c++) { $tbl.Columns($c).PreferredWidth = [single](82 / ($nk - 1)) }   # 82/3 = 27.33 (double) ditolak Word: «Specified cast is not valid»
            }
            $tbl.Rows(1).HeadingFormat = -1                # kepala diulang di halaman berikutnya
            $tbl.Rows(1).Shading.BackgroundPatternColor = 14277081   # abu-abu muda (RGB 217,217,217)
            $rf = $tbl.Range.ParagraphFormat
            $rf.ReadingOrder = 0; $rf.FirstLineIndent = 0; $rf.LeftIndent = 0; $rf.RightIndent = 0
            $rf.SpaceBefore = 0; $rf.SpaceAfter = 0; $rf.LineSpacingRule = 0; $rf.KeepWithNext = 0; $rf.PageBreakBefore = 0
            for ($r = 0; $r -lt $baris.Count; $r++) {
                $isi = @($baris[$r].sel)
                for ($c = 0; $c -lt $nk; $c++) {
                    $x = $tbl.Cell($r + 1, $c + 1).Range
                    # isi rata kanan (bukan rata kanan-kiri: jarak kata melebar di sel sempit). Paragrafnya RTL, jadi rata
                    # kanan = awal baris = 0; nilai 2 disimpan jc="right" = ujung akhir = rata KIRI di halaman.
                    # Kepala dan sel angka (olah.sel_angka) rata tengah
                    $x.ParagraphFormat.Alignment = $(if ($r -eq 0 -or $c -in @($RENCANA.sel_angka."$($i0 + $r)")) { 1 } else { 0 })
                    $x.Collapse(1); $x.Select()
                    Runs $isi[$c] $uTabel ($r -eq 0)
                }
            }
            $doc.Range($tbl.Range.End, $tbl.Range.End).Select()
            if ($i + 1 -lt $DATA.blok.Count -and $DATA.blok[$i + 1].k -eq 'E' -and $DATA.blok[$i + 1].tag) {
                Para 1 0 0; $sel.ParagraphFormat.LineSpacingRule = 4; $sel.ParagraphFormat.LineSpacing = 2; $sel.TypeParagraph()
            }
        }
        elseif ($blk.k -eq 'G') {                         # gambar: di tengah, paling lebar = lebar teks, paling tinggi 70% halaman
            Para 1 6 0
            HalamanBaru $pb
            $ps = $sec.PageSetup
            $lebarTeks = $ps.PageWidth - $ps.LeftMargin - $ps.RightMargin
            $tinggiMaks = 0.7 * ($ps.PageHeight - $ps.TopMargin - $ps.BottomMargin)
            $shp = $sel.InlineShapes.AddPicture($blk.berkas, $false, $true)
            $shp.LockAspectRatio = -1
            $s = [Math]::Min(1.0, [Math]::Min($lebarTeks / $shp.Width, $tinggiMaks / $shp.Height))
            $shp.Width = [single]($shp.Width * $s)          # tinggi ikut (rasio dikunci)
            $sel.ParagraphFormat.KeepWithNext = -1           # gambar tidak terpisah dari keterangannya
            $sel.TypeParagraph()
            if (@($blk.runs).Count) {
                Para 1 0 0
                Runs $blk.runs $uCatatan $true
                $sel.ParagraphFormat.SpaceAfter = 6
                $sel.TypeParagraph()
            }
        }
        elseif ($blk.k -eq 'E') {                         # persamaan matematika baris sendiri (OMML Word asli)
            if ($blk.tag) {                               # dengan \tag{…}: tabel 3 kolom tanpa garis (rumus tengah, nomor di tepi kiri)
                Para 1 6 0
                HalamanBaru $pb
                $tbl = $doc.Tables.Add($sel.Range, 1, 3)
                $tbl.TableDirection = 0; $tbl.Borders.Enable = 0; $tbl.Rows.Alignment = 1
                $tbl.PreferredWidthType = 2; $tbl.PreferredWidth = 100
                $tbl.Columns.PreferredWidthType = 2
                $tbl.Columns(1).PreferredWidth = [single]8; $tbl.Columns(2).PreferredWidth = [single]84; $tbl.Columns(3).PreferredWidth = [single]8
                foreach ($c in 1..3) { $tbl.Cell(1, $c).VerticalAlignment = 1 }
                $rf = $tbl.Range.ParagraphFormat
                $rf.FirstLineIndent = 0; $rf.LeftIndent = 0; $rf.RightIndent = 0
                $rf.SpaceBefore = 2; $rf.SpaceAfter = 2; $rf.LineSpacingRule = 0; $rf.KeepWithNext = 0; $rf.PageBreakBefore = $(if ($pb) { -1 } else { 0 })
                $mid = $tbl.Cell(1, 2).Range; $mid.ParagraphFormat.ReadingOrder = 1; $mid.ParagraphFormat.Alignment = 1
                $mid.Collapse(1); $mid.Select()
                TulisOmml $blk.omml $false
                $num = $tbl.Cell(1, 3).Range
                $num.ParagraphFormat.ReadingOrder = 0; $num.ParagraphFormat.Alignment = 2
                $tTag = [string]$blk.tag
                if (-not ($tTag.StartsWith('(') -and $tTag.EndsWith(')'))) { $tTag = "($tTag)" }
                $num.Text = $tTag
                Huruf $num.Font $TA $uCatatan 0
                MuatRumus $tbl.Cell(1, 2).Range.Paragraphs(1).Range $blk.omml $tTag
                $doc.Range($tbl.Range.End, $tbl.Range.End).Select()
                # pisahkan tabel nomor persamaan dari tabel #J atau #E bertag berikutnya supaya Word tidak menggabungkannya
                if ($i + 1 -lt $DATA.blok.Count -and ($DATA.blok[$i + 1].k -eq 'J' -or ($DATA.blok[$i + 1].k -eq 'E' -and $DATA.blok[$i + 1].tag))) {
                    Para 1 0 0; $sel.ParagraphFormat.LineSpacingRule = 4; $sel.ParagraphFormat.LineSpacing = 2; $sel.TypeParagraph()
                }
            } else {
                Para 1 6 0
                HalamanBaru $pb
                $sel.ParagraphFormat.ReadingOrder = 1
                $sel.ParagraphFormat.SpaceAfter = 6
                $pos = $sel.Start
                $sel.TypeParagraph()
                $r = $doc.Range($pos, $pos)
                $r.InsertXML((PaketOmml $blk.omml))
                MuatRumus $r.Paragraphs(1).Range $blk.omml
                $akhir = $r.Paragraphs(1).Range.End
                $doc.Range($akhir, $akhir).Select()
            }
        }
        elseif ($blk.k -eq 'V') {                         # bait syair: di tengah, tanpa awal alinea
            Para 1 2 0
            HalamanBaru $pb
            Runs $blk.runs $uMatan $false
            # bait terakhir dari deretan bait menempel ke paragraf sesudahnya (syarahnya): bait di baris akhir halaman
            # dengan syarah di halaman berikutnya pindah bersama pengantarnya (yang berakhir «:» sudah menempel).
            # Bait yang disusul bait lagi, atau pengantar bait lain («…:» atau label tebal seperti «الشرح»), tidak
            # menempel: deretan panjang (mis. النص 15 bait, poin-poin «…:» + bait contoh) boleh terpotong
            # antarhalaman, bukan pindah utuh sebagai satu rantai dan meninggalkan setengah halaman kosong
            $nxV = $DATA.blok[$i + 1]
            if ((Menempel $i) -and $nxV.k -ne 'V' -and -not (Pengantar $nxV)) { $sel.ParagraphFormat.KeepWithNext = -1 }
            $sel.TypeParagraph()
        }
        elseif ($blk.k -eq 'L') {                         # paragraf Latin: kiri ke kanan, rata kanan-kiri
            $judulL = [bool]$blk.tengah                    # «#L **Abstract**»: judul tebal di tengah, paragraf #L sesudahnya berjarak
            $jarakL = if ($judulL) { 6 } elseif ($i -gt 0 -and $DATA.blok[$i - 1].k -eq 'L' -and $script:berjarakL) { 6 } else { 0 }
            $script:berjarakL = $judulL -or ($jarakL -gt 0)
            Para 3 $jarakL 0
            HalamanBaru $pb
            $sel.ParagraphFormat.ReadingOrder = 1
            $sel.ParagraphFormat.Alignment = if ($judulL) { 1 } else { 3 }
            if ($judulL) { $sel.ParagraphFormat.KeepWithNext = -1 }
            $awal = $sel.Start
            Tulis $blk.runs[0].t 'Times New Roman' $(if ($judulL) { $uLatin + 2 } else { $uLatin }) ([int]$judulL) 0
            $doc.Range($awal, $sel.Start).Select(); $word.Selection.LtrRun(); $sel.Collapse(0)
            $sel.TypeParagraph()
        }
        elseif ($blk.k -eq 'S') {
            Para 3 6 0
            HalamanBaru $pb
            $sel.ParagraphFormat.KeepWithNext = -1
            if ($TO_TITIK -and $blk.judul.StartsWith('❖')) {   # فهرس الموضوعات titik: sub-judul «❖ …» ikut, di bawah judul sebelumnya
                $nT++; [void]$doc.Bookmarks.Add("t_$nT", $sel.Range); [void]$toc.Add(@{ t = $blk.judul; bm = "t_$nT"; lvl = 1 })
            }
            Tulis $blk.judul $TJ $uJudulSub 1 0
            $sel.TypeParagraph()
        }
        elseif ($null -ne $RENCANA.ihda."$i") {           # @ihda: tengah = paragraf الإهداء rata tengah, tebal, berjarak, tanpa menjorok
            Para 1 $RENCANA.ihda."$i" 0
            HalamanBaru $pb
            Runs $blk.runs $uMatan $true
            $sel.TypeParagraph()
        }
        else {
            if ($diMulakhas) { Para 3 $(if ($DATA.blok[$i - 1].k -eq 'K') { 0 } else { 6 }) 0 } else { Para 3 $(if ($i -gt 0 -and $DATA.blok[$i - 1].k -eq 'J') { 6 } else { 0 }) ($word.CentimetersToPoints($AWAL_ALINEA)); $sel.ParagraphFormat.SpaceAfter = $JARAK_P }   # sesudah tabel: berjarak
            HalamanBaru $pb
            Runs $blk.runs $uMatan $false
            if ((Pengantar $blk) -and (Menempel $i)) { $sel.ParagraphFormat.KeepWithNext = -1 }
            if ($i -in @($RENCANA.mufradat)) { $sel.ParagraphFormat.KeepWithNext = -1 }   # baris مفردات (olah.baris_mufradat)
            $sel.TypeParagraph()
        }
    }
    }
    . $tulisBlok

    # judul المصادر/فهرس: yang pertama sesudah الخاتمة selalu halaman baru; @fihris: sambung = sisanya menyambung
    $script:fihrisPertama = $true
    function JudulFihris($teks, $bm) {
        $pb = $script:fihrisPertama -or -not $FIHRIS_SAMBUNG; $script:fihrisPertama = $false
        Judul $teks $bm $pb
        $p = $sel.Paragraphs(1).Previous(1)
        if ($p) { $p.SpaceAfter = [Math]::Max($p.SpaceAfter, $JARAK_FIHRIS); if (-not $pb) { $p.SpaceBefore = 24 } }
    }
    function Tabel($rows, $widthsCm, $garis) {
        Para 3 0 0
        $tbl = $doc.Tables.Add($sel.Range, [int]$rows, [int]$widthsCm.Count)
        $tbl.TableDirection = 0
        $tbl.Borders.Enable = $garis
        $tbl.AllowAutoFit = $false
        for ($c = 1; $c -le $widthsCm.Count; $c++) { $tbl.Columns($c).Width = $word.CentimetersToPoints($widthsCm[$c - 1]) }
        $tbl.Rows.Alignment = 1
        $tbl.Range.ParagraphFormat.ReadingOrder = 0; $tbl.Range.ParagraphFormat.SpaceAfter = 0; $tbl.Range.ParagraphFormat.SpaceBefore = 0
        $tbl.Range.ParagraphFormat.LineSpacingRule = 0; $tbl.Range.ParagraphFormat.FirstLineIndent = 0
        Huruf $tbl.Range.Font $TA $uMatan 0
        return $tbl
    }
    function Sel($tbl, $r, $c, $teks, $align, $bold, $ukuran = $uMatan) {
        $rg = $tbl.Cell($r, $c).Range
        $rg.Text = $teks
        Huruf $rg.Font $TA $ukuran $bold
        $rg.ParagraphFormat.Alignment = $align
        Tautan $rg $rg.Start $teks
        Latin $rg $rg.Start $teks $ukuran
    }

    # sel berisi **tebal** dan __miring__ (@pustaka_gaya: muallif): teks ditulis tanpa tandanya, lalu tiap ruas diberi gayanya
    function SelGaya($tbl, $r, $c, $teks, $ukuran = $uMatan) {
        $polos = $teks -replace '\*\*|__', ''
        Sel $tbl $r $c $polos 3 0 $ukuran
        $rg0 = $tbl.Cell($r, $c).Range.Start; $pos = 0; $b = $false; $it = $false
        foreach ($m in [regex]::Split($teks, '(\*\*|__)')) {
            if ($m -eq '**') { $b = -not $b; continue }; if ($m -eq '__') { $it = -not $it; continue }
            if ($m.Length -and ($b -or $it)) {
                $x = $tbl.Cell($r, $c).Range; $x.SetRange($rg0 + $pos, $rg0 + $pos + $m.Length)
                if ($b) { $x.Font.Bold = 1; $x.Font.BoldBi = 1 }; if ($it) { $x.Font.Italic = 1; $x.Font.ItalicBi = 1 }
            }
            $pos += $m.Length
        }
    }
    # المصادر والمراجع: tabel tanpa garis, urut abjad
    function Tulis-Pustaka {
    $n = $DATA.pustaka.Count
    # baris القرآن الكريم (selalu paling atas kalau ada) bertanda «-», kitab lain bernomor 1, 2, ...; penandanya dari olah.py
    $adaQuran = [bool]$DATA.quran
    $geser = if ($adaQuran) { 1 } else { 0 }
    if ($PUSTAKA_MUALLIF) { $geser = 0 }                 # @pustaka_gaya: muallif = القرآن الكريم ikut bernomor (١.)
    $butir = $PUSTAKA_BUTIR.Count -gt 0                 # @pustaka_gaya: judul_tebal: «•» di kolom nomor, judul tebal dulu
    $tb = Tabel $n $(if ($butir) { @(0.6, 14.4) } else { @(1.3, 13.7) }) 0
    for ($r = 1; $r -le $n; $r++) {
        $no = if ($butir) { '•' } elseif ($adaQuran -and $r -eq 1 -and -not $PUSTAKA_MUALLIF) { '-' } else { (Angka ($r - $geser)) + '.' }
        Sel $tb $r 1 $no 1 0 $U_PUSTAKA
        if ($butir) { SelGaya $tb $r 2 $PUSTAKA_BUTIR[$r - 1] $U_PUSTAKA }
        elseif ($PUSTAKA_MUALLIF) { SelGaya $tb $r 2 $DATA.pustaka[$r - 1] $U_PUSTAKA } else { Sel $tb $r 2 $DATA.pustaka[$r - 1] 3 0 $U_PUSTAKA }
    }
    for ($r = 1; $r -le $n; $r++) {
        $rg = $tb.Cell($r, 2).Range
        $polos = if ($butir) { $PUSTAKA_BUTIR[$r - 1] -replace '\*\*|__', '' } elseif ($PUSTAKA_MUALLIF) { $DATA.pustaka[$r - 1] -replace '\*\*|__', '' } else { $DATA.pustaka[$r - 1] }
        if ($RENCANA.pustaka_ltr[$r - 1]) {   # rujukan asing utuh: paragraf kiri-ke-kanan rata kiri, nomornya tetap di kolom kanan
            $rg.ParagraphFormat.ReadingOrder = 1; $rg.ParagraphFormat.Alignment = 0
            # seluruh teksnya satu run kiri-ke-kanan Times (juga kurung, tanda petik, angka, dan titik di luar rentang Latin)
            # huruf untuk seluruh sel, juga tanda akhir selnya: tanda itu yang menentukan tinggi baris terakhir
            $uL = [Math]::Ceiling($U_PUSTAKA * $rasioLatin)
            Huruf $rg.Font 'Times New Roman' $uL $null; PetikUlang $rg $rg.Start $polos
            # jarak antarrujukan seperti baris Arab
            # nomor tetap sebesar nomor baris Arab; tinggi barisnya dibuat sama dengan baris teks Latin supaya sebaris
            $no = $tb.Cell($r, 1).Range; $no.ParagraphFormat.LineSpacingRule = 4; $no.ParagraphFormat.LineSpacing = [single]($uL * 1.15)   # 4 = tepat setinggi baris teks Latin
            $rg.ParagraphFormat.SpaceAfter = 6; $no.ParagraphFormat.SpaceAfter = 6
            $l = $rg.Duplicate; $l.SetRange($rg.Start, $rg.Start + $polos.Length); $l.Select(); $word.Selection.LtrRun()
        } else { LatinLtr $rg $rg.Start $polos }
    }
    }

    # ---------- 3. Sesudah isi: المصادر والمراجع, الملاحق, الفهارس (yang dicetak, urutan, dan judulnya: $RENCANA.bagian) ----------
    $bmSesudahIsi = "t_$($nT + 1)"   # judul pertama sesudah الخاتمة (المصادر, atau فهرس pertama): HALAMAN_ISI = halamannya - 1
    foreach ($bg in $RENCANA.bagian) {
    if ($bg.belakang) {                                  # halaman belakang: bagian Word baru, hanya bernomor di tengah kaki
        [void]$sel.EndKey(6)
        Pasang-Kepala (Bagian-Baru $false) '-' $JUDUL_KEPALA
    }
    if ($bg.jenis -eq 'malahiq') {                       # @malahiq: akhir — blok sesudah #R = الملاحق, sesudah المصادر, sebelum فهرس
        $mulaiBlok = $iR + 1
        . $tulisBlok
        $script:fihrisPertama = $true                    # فهرس pertama sesudah الملاحق mulai halaman baru
        continue
    }
    $titik = $bg.jenis -eq 'maudhuat' -and $TO_TITIK     # @maudhuat: titik = «الموضوع ...... ص» per baris tanpa tabel, dan tanpa barisnya sendiri (seperti contoh)
    $diAwal = $bg.awal -and $doc.Bookmarks.Exists('fihris_awal')   # @maudhuat_letak: awal: ditulis di tempat yang disiapkan sebelum المقدمة
    if ($diAwal) {
        $doc.Bookmarks.Item('fihris_awal').Range.Select(); $sel.Collapse(1)
        Judul $bg.judul 't_maudhuat' $true                # tidak masuk فهرس-nya sendiri, dan tidak dihitung sebagai bagian sesudah isi
        $p = $sel.Paragraphs(1).Previous(1); $p.SpaceAfter = [Math]::Max($p.SpaceAfter, $JARAK_FIHRIS)
    } else {
    $nT++; JudulFihris $bg.judul "t_$nT"
    if (-not $titik) { [void]$toc.Add(@{ t = $bg.judul; bm = "t_$nT"; lvl = 0 }) }
    }
    if ($bg.jenis -eq 'pustaka') { Tulis-Pustaka }
    elseif ($bg.jenis -eq 'ayat') { Fihris-Ayat $bg }
    elseif ($bg.jenis -in 'hadits', 'atsar') { Fihris-Hadits $bg }
    elseif ($bg.jenis -eq 'syir') { Fihris-Syir $bg }
    elseif ($bg.jenis -eq 'maudhuat') {
    if ($titik) {                                        # nomor di tepi kiri
        $lebar = $sec.PageSetup.PageWidth - $sec.PageSetup.LeftMargin - $sec.PageSetup.RightMargin
        $r = 0
        foreach ($e in $toc) {
            $r++
            Para 3 0 0
            $pf = $sel.ParagraphFormat; $pf.Alignment = 0; $pf.SpaceAfter = 6
            if ($e.lvl -gt 0) { $pf.LeftIndent = $word.CentimetersToPoints(0.6 * $e.lvl) }
            $pf.TabStops.ClearAll(); [void]$pf.TabStops.Add($lebar, 2, 1)   # 2 = rata ujung (kiri di teks kanan-ke-kiri), 1 = titik-titik
            $tb = [int]($e.lvl -eq 0)                     # baris #K/#F (dan judul فهرس) dan nomornya tebal
            Tulis (($e.t -replace '^❖\s*', '') + "`t") $TA $uMatan $tb 0
            $awalNo = $sel.Start; Tulis (Angka '00') $TA $uMatan $tb 0
            [void]$doc.Bookmarks.Add("tn_$r", $doc.Range($awalNo, $sel.Start))
            $sel.TypeParagraph()
        }
    } else {
    $tTo = Tabel ($toc.Count + 1) @(13.0, 2.0) 1
    Sel $tTo 1 1 'الموضوع' 1 1; Sel $tTo 1 2 'الصفحة' 1 1; Kepala-Abu $tTo   # fihris.ps1
    $r = 1
    foreach ($e in $toc) { $r++; Sel $tTo $r 1 $e.t 3 ([int]($e.lvl -eq 0)); $tTo.Cell($r, 1).Range.ParagraphFormat.RightIndent = 0; $tTo.Cell($r, 1).Range.ParagraphFormat.LeftIndent = 0; if ($e.lvl -gt 0) { $tTo.Cell($r, 1).Range.ParagraphFormat.RightIndent = $word.CentimetersToPoints(0.7 * $e.lvl) }; Sel $tTo $r 2 (Angka '00') 1 0 }
    }
    }
    else { Fihris-Nama $bg }                             # فهرس nama ({N:}, {M:}, {B:}, {QB:}, {G:})
    if ($diAwal) {   # sesudah فهرس depan hanya boleh ada judul sesudahnya, atau satu paragraf pemisah bagian Word (@nomor)
        $ujung = if ($titik) { $sel.Start } else { $tTo.Range.End }
        $p = $doc.Range($ujung, $ujung).Paragraphs(1); $kosong = @()
        while ($p -and $p.Range.Text.Trim([char]13, [char]12, [char]32) -eq '') { $kosong += $p; $p = $p.Next(1) }
        # paragraf kosong (sisa tempatnya) dibuang: yang tersisa tumpah ke halaman baru kalau فهرس pas satu halaman, dan judul
        # sesudahnya mulai halaman baru lagi = halaman kosong. Paragraf pemisah bagian (@nomor) tetap, setinggi 1 pt
        foreach ($k in $kosong) {
            if ($k.Range.Text.Contains([string][char]12)) { $script:pFihrisEkor = $k; continue }
            try { [void]$k.Range.Delete() } catch { $script:pFihrisEkor = $k }
        }
        if ($script:pFihrisEkor) {
            $pe = $script:pFihrisEkor; Huruf $pe.Range.Font $null 1
            $pe.SpaceBefore = 0; $pe.SpaceAfter = 0; $pe.LineSpacingRule = 4; $pe.LineSpacing = 1; $pe.PageBreakBefore = 0   # 4 = wdLineSpaceExactly
        }
        $script:fihrisAwal = @{ titik = $titik; tabel = $(if ($titik) { $null } else { $tTo }); ujung = $ujung; rapat = 1.0 }
    }
    if (-not $titik -or $diAwal) { [void]$sel.EndKey(6) }
    }

    if ($RENCANA.tamma) {                                 # @tamma: halaman penutup, halaman terakhir
        [void]$sel.EndKey(6)
        $tandai = -not $doc.Bookmarks.Exists($bmSesudahIsi)
        Halaman-Tamma
        # tanpa المصادر dan فهرس: halaman isi (HALAMAN_ISI) berakhir sebelum halaman ini
        if ($tandai) { [void]$doc.Bookmarks.Add($bmSesudahIsi, $doc.Paragraphs.Last.Range) }
    }
    # naskah tanpa catatan kaki tidak punya story catatan kaki
    if ($doc.Footnotes.Count) { foreach ($fpp in $doc.StoryRanges.Item(2).Paragraphs) { $fpp.ReadingOrder = 0; $fpp.Alignment = 3 } }
    foreach ($sc in $doc.Sections) { $sc.Range.FootnoteOptions.NumberingRule = $ULANG; $sc.Range.FootnoteOptions.StartingNumber = 1 }
    $doc.Range().FootnoteOptions.NumberingRule = $ULANG

    NomorCatatan
    BarisPendek
    NomorCatatan

    # ---------- 4. Isi nomor halaman ----------
    $doc.Repaginate()
    $HURUF_NOMOR = 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي'    # urutan nomor Word gaya 46; Information(1) tetap memberi angka
    function Hal($bm) {                                  # 1 = nomor halaman seperti yang tercetak
        $r = $doc.Bookmarks.Item($bm).Range; $n = $r.Information(1)
        if ($ABJAD -and $r.Sections(1).Footers(1).PageNumbers.NumberStyle -eq 46) { return [string]$HURUF_NOMOR[$n - 1] }
        return $n
    }
    # {P:kunci}: tiap angka punya bookmark sejak BuatCatatan, termasuk catatan kaki yang dibuat ulang NomorCatatan.
    # Isian bisa memindahkan targetnya ke halaman lain: perbarui lagi sampai nomor halaman dan catatan kaki tetap.
    # Jangan mencari angka biasa: itu bisa mengubah angka isi naskah.
    # halaman فهرس الأعلام: angka berurutan jadi rentang («25-29»); nomor huruf (@nomor) apa adanya
    function Rentang($hal) {
        $angka = @($hal | Where-Object { $_ -is [int] } | Sort-Object -Unique); $lain = @($hal | Where-Object { $_ -isnot [int] })
        $out = @($lain)
        for ($i = 0; $i -lt $angka.Count; $i++) {
            $j = $i; while ($j + 1 -lt $angka.Count -and $angka[$j + 1] -eq $angka[$j] + 1) { $j++ }
            $out += if ($j - $i -ge 2) { "$($angka[$i])-$($angka[$j])" } elseif ($j -gt $i) { "$($angka[$i])"; "$($angka[$j])" } else { "$($angka[$i])" }
            $i = $j
        }
        return ($out -join '، ')
    }
    function IsiRujukanHalaman {
        $ubah = 0
        foreach ($nama in @($rujukanHalaman.Keys)) {
            if (-not $doc.Bookmarks.Exists($nama)) { $rujukanHalaman.Remove($nama); continue } # catatan dibuat ulang
            $rg = $doc.Bookmarks.Item($nama).Range; $pg = Angka (Hal $rujukanHalaman[$nama])
            if ($rg.Text -ne $pg) {
                $rg.Text = $pg; [void]$doc.Bookmarks.Add($nama, $rg); $ubah++
            }
        }
        return $ubah
    }
    # Nomor catatan kaki sudah tetap sejak NomorCatatan di akhir bagian 3, dan sejak itu dokumen tidak diubah: putaran
    # pertama langsung mengisi {P:}. Tidak ada isian yang berubah = dokumennya masih yang diperiksa NomorCatatan terakhir,
    # jadi selesai tanpa membaca semua nomor sekali lagi (bahts 41 halaman: panggilan SalahNomor 7 -> 5)
    for ($putaran = 1; $putaran -le 12; $putaran++) {
        if ($putaran -gt 1) { NomorCatatan }
        $ubah = IsiRujukanHalaman
        $doc.Repaginate()
        if (-not $ubah) { break }
    }
    if ($putaran -gt 12) { throw "Nomor halaman {P:...} atau nomor catatan kaki belum tetap sesudah 12 putaran." }
    # tabel فهرس: angka asli («٢٤، ٣٠») bisa lebih lebar daripada '00', barisnya melipat, dan judul sesudahnya pindah halaman
    # (فهرس الموضوعات pernah mencetak 41 padahal judulnya di halaman 42): isi, Repaginate, ulangi sampai tidak ada yang berubah
    $isiLama = @{}
    # فهرس depan yang baris terakhirnya hampir di dasar halaman: paragraf pemisah bagian (1 pt) sesudahnya tumpah ke halaman
    # baru, lalu المقدمة mulai halaman baru lagi = halaman kosong. Barisnya dirapatkan sedikit (5% tiap putaran, paling banyak
    # 20%) sampai paragraf itu muat di halaman terakhir فهرس
    function RapatFihrisAwal {
        $fa = $script:fihrisAwal; $pe = $script:pFihrisEkor
        if (-not $fa -or -not $pe -or $fa.rapat -le 0.8) { return 0 }
        $hAkhir = $doc.Range($pe.Range.Start - 1, $pe.Range.Start - 1).Information(3)
        if ($pe.Range.Information(3) -le $hAkhir) { return 0 }
        $fa.rapat -= 0.05
        if ($fa.tabel) { $rf = $fa.tabel.Range.ParagraphFormat; $rf.LineSpacingRule = 5; $rf.LineSpacing = $word.LinesToPoints($fa.rapat) }
        else { $doc.Range($doc.Bookmarks.Item('t_maudhuat').Range.End, $pe.Range.Start).ParagraphFormat.SpaceAfter = [single](6 * $fa.rapat - 2) }
        return 1
    }
    for ($putaran = 1; $putaran -le 5; $putaran++) {
        $ubah = RapatFihrisAwal
        $ubah += Isi-Fihris                               # الآيات، الأحاديث، الآثار، فهرس nama، الأشعار (fihris.ps1)
        if ($adaTo -and $TO_TITIK) {
            $r = 0
            foreach ($e in $toc) {
                $r++; $pg = Angka (Hal $e.bm)
                if ($isiLama["t$r"] -ne $pg) { $isiLama["t$r"] = $pg; $ubah++; $x = $doc.Bookmarks.Item("tn_$r").Range; $x.Text = $pg; [void]$doc.Bookmarks.Add("tn_$r", $x) }
            }
        }
        elseif ($adaTo) { $r = 1; foreach ($e in $toc) { $r++; $pg = Angka (Hal $e.bm); if ($isiLama["t$r"] -ne $pg) { $isiLama["t$r"] = $pg; $ubah++; Sel $tTo $r 2 $pg 1 0 } } }
        $doc.Repaginate()
        if (-not $ubah) { break }
    }
    if ($ubah) { Write-Output "PERINGATAN: nomor halaman فهرس belum tetap sesudah 5 putaran" }

    # ---------- 5. Simpan ----------
    # nomor halaman = teks kanan-ke-kiri, supaya ArabicNumeral 2 mencetaknya ٠-٩ (di akhir: memindah Selection ke kaki
    # halaman). RtlRun hanya ada di Selection, dan bisa diam-diam tidak berpengaruh: satu PDF pernah tercetak 0123 di
    # semua kaki halamannya, <w:rtl/> tidak ada di kaki halaman .docx-nya, dan rakit ulang naskah yang sama benar
    # (penyebabnya belum tahu). Jadi dikerjakan di Print Layout, lalu dibaca lagi dari XML-nya dan diulang sekali
    $doc.ActiveWindow.View.Type = 3
    # Tiap field PAGE kepala/kaki halaman (1 utama, 3 genap) yang bukan sambungan bagian sebelumnya
    function NomorRtl($hf) {
        if ($hf.LinkToPrevious) { return }                 # bagian pertama tidak pernah bersambung
        $semua = @($hf.Range.Fields)
        foreach ($f in @($semua | Where-Object { $_.Code.Text -match '^\s*PAGE(\s|$)' })) {
            # PAGE di dalam kode field lain (hitungan ganjil/genap IF @kepala: bergantian) tidak tercetak: hasilnya tidak
            # pernah kanan-ke-kiri, dan memeriksanya memberi PERINGATAN palsu
            if (@($semua | Where-Object { $_.Code.Start -lt $f.Code.Start -and $f.Code.End -le $_.Code.End }).Count) { continue }
            $r = $hf.Range.Duplicate; $r.SetRange($f.Code.Start - 1, $f.Result.End + 1)
            for ($k = 1; $k -le 2; $k++) {
                $doc.Activate(); $r.Select(); $word.Selection.RtlRun()
                if ($r.WordOpenXML -match '<w:rtl/>') { break }
            }
            # nomor huruf (@nomor: abjad) tidak berangka
            if ($r.WordOpenXML -notmatch '<w:rtl/>' -and $HINDI -and $hf.PageNumbers.NumberStyle -ne 46) { Write-Output "PERINGATAN: Word tidak mau membuat nomor halaman kanan-ke-kiri: nomor halaman bisa tercetak 0123. Rakit lagi." }
        }
    }
    foreach ($s in @($doc.Sections)) { foreach ($j in 1, 3) { NomorRtl $s.Headers($j); NomorRtl $s.Footers($j) } }
    # garis pemisah catatan kaki: dokumen @templat berangkat dari dokumen kosong yang gaya Normal-nya kiri-ke-kanan, jadi
    # garisnya ikut ke kiri kalau tidak disetel di sini
    $pk = $sec.PageSetup; Garis-Catatan ($pk.PageWidth - $pk.LeftMargin - $pk.RightMargin)
    Periksa-Kepala $doc.Sections($nIsi) $KEPALA
    Periksa-Berjalan $KEPALA @($toc | Where-Object { $_.lvl -eq 0 } | ForEach-Object { $_.t }) $JUDUL_KEPALA ($pk.PageWidth - $pk.LeftMargin - $pk.RightMargin)
    # Dokumen selalu berakhir dengan satu paragraf kosong: sisa TypeParagraph sesudah blok terakhir, atau paragraf wajib
    # Word sesudah tabel terakhir (فهرس). Isi yang pas memenuhi halaman mendorongnya ke halaman baru: PDF berakhir dengan
    # halaman kosong yang hanya bernomor. Sesudah paragraf biasa (bahts tanpa المصادر dan فهرس), tanda paragraf
    # sebelumnya dihapus: paragraf kosong itu hilang, dan paragraf terakhir tetap memakai formatnya sendiri (diuji di
    # Word: perataan, ukuran, bookmark). Mengecilkannya sampai 1 pt tidak cukup kalau baris terakhir tepat di
    # tepi bawah (naskah 50 baris pendek). Sesudah tabel paragraf itu tidak bisa dibuang: dikecilkan sampai setinggi 1 pt
    $ekor = $doc.Paragraphs.Last
    $tanda = if ($ekor.Range.Start -gt 0) { $doc.Range($ekor.Range.Start - 1, $ekor.Range.Start) }
    if ($ekor.Range.Text.Trim().Length -eq 0 -and $tanda -and $tanda.Text -eq "`r" -and -not $tanda.Information(12)) {
        [void]$tanda.Delete()                            # 12 = wdWithInTable; «`r» = bukan pemisah bagian Word
    }
    elseif ($ekor.Range.Text.Trim().Length -eq 0) {
        Huruf $ekor.Range.Font $null 1
        $ekor.SpaceBefore = 0; $ekor.SpaceAfter = 0; $ekor.LineSpacingRule = 4; $ekor.LineSpacing = 1   # 4 = wdLineSpaceExactly
    }
    $pages = $doc.ComputeStatistics(2)
    # halaman isi = المقدمة s.d. الخاتمة; tanpa المصادر dan فهرس = halaman terakhir. Ada المقدمة atau nomor tercetak dua
    # jenis (@nomor): dihitung dari halaman fisik, supaya #K sebelum المقدمة (الإهداء، الملخص) tidak ikut terhitung
    if ($ABJAD -or $bmMuqaddimah) {
        $hAwal = if ($bmMuqaddimah) { $doc.Bookmarks.Item($bmMuqaddimah).Range.Information(3) } else { 1 }
        $hAkhir = if ($doc.Bookmarks.Exists($bmSesudahIsi)) { $doc.Bookmarks.Item($bmSesudahIsi).Range.Information(3) } else { $pages + 1 }
        $isi = $hAkhir - $hAwal
    }
    elseif ($doc.Bookmarks.Exists($bmSesudahIsi)) { $isi = (Hal $bmSesudahIsi) - 1 }
    else { $akhir = $doc.Content.End - 1; $isi = $doc.Range($akhir, $akhir).Information(1) }
    $lap = @("HALAMAN=$pages", "HALAMAN_ISI=$isi","CATATAN_KAKI=$($doc.Footnotes.Count)", "KATA(termasuk catatan kaki)=$($doc.ComputeStatistics(0, $true))")
    foreach ($e in $toc) { $lap += ("hal {0}: {1}" -f (Hal $e.bm), $e.t) }
    [IO.File]::AppendAllLines($Laporan, [string[]]$lap)
    $doc.EmbedTrueTypeFonts = $true; $doc.SaveSubsetFonts = $false; $doc.DoNotEmbedSystemFonts = $false
    $doc.ActiveWindow.View.Type = 3
    # nomor halaman di kotak teks kepala @templat ikut angka Arab (@angka): Word memilih angka menurut arah teks di
    # sekitarnya, dan teks hasil PAGE di kotak itu kiri-ke-kanan. RtlRun hanya ada di Selection, dan hanya di Print Layout
    if ($kepalaTpl) {
        foreach ($sh in @(try { @($doc.Sections($nIsi).Headers(1).Range.ShapeRange) } catch { })) {
            try {
                if ($sh.TextFrame.HasText -and @($sh.TextFrame.TextRange.Fields | Where-Object { $_.Code.Text -match 'PAGE' }).Count) {
                    $sh.TextFrame.TextRange.Select(); $word.Selection.RtlRun()
                }
            } catch {}
        }
    }
    $doc.SaveAs2("$Out.docx", 16)
    $word.ScreenUpdating = $true                         # tanpa ini garis bingkai/kepala halaman tidak ikut ke PDF
    $word.Options.ArabicNumeral = $NUMERAL               # pengaturan milik seluruh Word pemakai: dipastikan lagi tepat sebelum PDF
    $doc.ExportAsFixedFormat("$Out.pdf", 17)
    # paragraf khulasah {X} (bookmark x_n): distabilo kuning sesudah .docx dan .pdf utama tersimpan, lalu diekspor ke
    # salinan -PdfKhulasah; `rakit` (rakit.py) memotong salinan itu menjadi halaman-halaman khulasah saja. .docx tetap tanpa stabilo.
    # Potongan --fasl bisa tidak mulai dari x_1 (penomoran x_n se-naskah), jadi semua bookmark x_* yang ada dibaca berurutan.
    $khulasah = @()
    $xBm = @($doc.Bookmarks | Where-Object { $_.Name -match '^x_(\d+)$' } | Sort-Object { [int]($_.Name.Substring(2)) })
    foreach ($bm in $xBm) {
        $par = $bm.Range.Paragraphs(1).Range
        $par.HighlightColorIndex = 7                        # 7 = wdYellow
        $hA = $doc.Range($par.Start, $par.Start).Information(3); $hB = $doc.Range($par.End - 1, $par.End - 1).Information(3)
        $khulasah += "$hA-$hB"
    }
    if ($khulasah.Count) {
        $doc.ExportAsFixedFormat($PdfKhulasah, 17)
        [IO.File]::AppendAllLines($Laporan, [string[]]@("KHULASAH=" + ($khulasah -join ',')))
    }
    $doc.Close($false)
}
finally {
    try { if ($draft) { $doc.ActiveWindow.View.Type = 3 } } catch {}
    try { foreach ($d in @($word.Documents)) { $d.Close($false) } } catch {}
    try { $word.Options.ArabicNumeral = $numeralLama } catch {}
    try { $word.Quit([ref]0) } catch {}                   # Quit menerima argumen ref; Quit(0) selalu gagal
    foreach ($v in Get-Variable -Scope Local) {
        if ($null -ne $v.Value -and [Runtime.InteropServices.Marshal]::IsComObject($v.Value)) {
            try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($v.Value) } catch {}
            try { $v.Value = $null } catch {}
        }
    }
    foreach ($nama in 'buang', 'pJudulT', 'celah', 'lentur', 'isian', 'fihrisAwal', 'xBm', 'ka', 'kt') { Remove-Variable -Name $nama -ErrorAction SilentlyContinue }
    [GC]::Collect(); [GC]::WaitForPendingFinalizers(); [GC]::Collect()
    try { Bersihkan-WordRakit $CATATAN_WORD 3000 } catch { Write-Output "PERINGATAN: Word milik rakit belum berhenti; catatannya disimpan: $($_.Exception.Message)" }
    try { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue } catch {}
    try { $pegangKunci.Close() } catch {}
}
