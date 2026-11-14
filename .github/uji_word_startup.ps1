# SPDX-License-Identifier: AGPL-3.0-or-later
# Exercise the production Word lifecycle; only native window/process operations are simulated.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\mesin\word.ps1')
$uji = Join-Path ([IO.Path]::GetTempPath()) ('bahts-word-lifecycle-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $uji | Out-Null
$catatan = Join-Path $uji 'rakit.word'
$mulai = [datetime]::new(638000000000000000)
$global:dihentikan = @()
$global:ditolak = $false
$global:sudahKeluar = $false

function Proses($Nomor, $Nama, $Waktu) {
    $p = [pscustomobject]@{ Id = $Nomor; ProcessName = $Nama; StartTime = $Waktu; Handle = [IntPtr]1 }
    $p | Add-Member -MemberType ScriptMethod -Name Dispose -Value {}
    $p | Add-Member -MemberType ScriptMethod -Name WaitForExit -Value { param($Batas) return $global:sudahKeluar }
    return $p
}
$global:proses = @(
    (Proses 999001 'WINWORD' $mulai),
    (Proses 999002 'WINWORD' $mulai),
    (Proses 999003 'WINWORD' $mulai.AddTicks(1)),
    (Proses 999004 'aplikasi_lain' $mulai)
)
function Get-Process {
    param($Name, $Id, $ErrorAction)
    if (-not $Id) { throw 'Enumerating Word processes cannot establish ownership.' }
    $global:proses | Where-Object { $_.Id -eq $Id }
}
function Stop-Process {
    param($InputObject, [switch]$Force, $ErrorAction)
    if ($global:ditolak) { throw 'Process stop denied.' }
    $global:dihentikan += $InputObject.Id
}
function Id-ProsesWord($Word) { return $Word.Hwnd }

$global:probeDitutup = $false
$dokumen = [pscustomobject]@{ ActiveWindow = [pscustomobject]@{ Hwnd = 999002 } }
$dokumen | Add-Member -MemberType ScriptMethod -Name Close -Value { param($Simpan) $global:probeDitutup = $true }
$documents = [pscustomobject]@{ Dokumen = $dokumen }
$documents | Add-Member -MemberType ScriptMethod -Name Add -Value { return $this.Dokumen }
$identitas = Catat-WordRakit ([pscustomobject]@{ Documents = $documents }) $catatan
if (-not $global:probeDitutup) { throw 'The identification document remained open.' }
if ($identitas -ne "999002|$($mulai.Ticks)" -or (Get-Content -LiteralPath $catatan) -ne $identitas) {
    throw 'Ownership was not recorded for the exact Word application.'
}
Set-Content -LiteralPath $catatan -Encoding ASCII -Value @(
    $identitas, "999003|$($mulai.Ticks)", "999004|$($mulai.Ticks)",
    'abc', '999002|abc', '999999999999999999|1', '1|999999999999999999999', "999002|$($mulai.Ticks)|extra"
)
Bersihkan-WordRakit $catatan
if ("$global:dihentikan" -ne '999002') { throw "Stopped [$global:dihentikan]; only the exact owned Word may stop." }
if (Test-Path -LiteralPath $catatan) { throw 'Recovered ownership record was not removed.' }

$global:dihentikan = @()
Hentikan-WordRakit "999003|$($mulai.Ticks)"
if ($global:dihentikan.Count) { throw 'Final cleanup stopped a reused process number.' }
$global:sudahKeluar = $true
Hentikan-WordRakit $identitas
if ($global:dihentikan.Count) { throw 'Final cleanup stopped Word after it had already exited.' }
$global:sudahKeluar = $false
$global:ditolak = $true
Set-Content -LiteralPath $catatan -Encoding ASCII -Value $identitas
$gagal = $false
try { Bersihkan-WordRakit $catatan } catch { $gagal = $true }
if (-not $gagal -or (Get-Content -LiteralPath $catatan) -ne $identitas) { throw 'A failed stop lost its ownership record.' }
$global:ditolak = $false
Bersihkan-WordRakit $catatan
if ("$global:dihentikan" -ne '999002') { throw 'The next build could not recover the owned Word.' }
# rakit.ps1 must use these functions in order: recover old Word before creating one, record the new one, clean up in finally.
$rakit = Join-Path $PSScriptRoot '..\mesin\rakit.ps1'
$galat = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($rakit, [ref]$null, [ref]$galat)
if ($galat) { throw 'rakit.ps1 cannot be parsed' }
$letak = {
    param($Pola)
    $x = $ast.Find({ param($a) $a -is [System.Management.Automation.Language.CommandBaseAst] -and $a.Extent.Text -match $Pola }, $true)
    if (-not $x) { throw "rakit.ps1 no longer runs: $Pola" }
    $x.Extent.StartOffset
}
$muat = & $letak '^\.\s+"\$dir\\word\.ps1"'
$pulih = & $letak '^Bersihkan-WordRakit \$CATATAN_WORD'
$buat = & $letak 'New-Object\s+-ComObject\s+Word\.Application'
$catat = & $letak '^Catat-WordRakit \$word \$CATATAN_WORD'
$akhir = $ast.Find({ param($a) $a -is [System.Management.Automation.Language.TryStatementAst] -and $a.Finally -and $a.Finally.Extent.Text -match 'Bersihkan-WordRakit' }, $true)
if (-not $akhir) { throw 'rakit.ps1 finally no longer cleans up its Word.' }
if (-not ($muat -lt $pulih -and $pulih -lt $buat -and $buat -lt $catat)) { throw "rakit.ps1 Word lifecycle out of order: load $muat, recover $pulih, create $buat, record $catat" }
Write-Output 'uji lifecycle Word: exact application ownership; unrelated/reused/exited processes protected; failed stop retains recovery record (Word not started)'
