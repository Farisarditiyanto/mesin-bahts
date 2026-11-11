# SPDX-License-Identifier: AGPL-3.0-or-later
# Experimental Word PDF export only; caller holds the existing Bahts job lock.
param([Parameter(Mandatory)][string]$InputDocx, [Parameter(Mandatory)][string]$OutputPdf,
      [Parameter(Mandatory)][string]$Kunci)
$ErrorActionPreference = 'Stop'
$guard = [IO.File]::Open($Kunci, 'OpenOrCreate', 'ReadWrite', 'None')
$record = Join-Path (Split-Path -Parent $Kunci) 'rakit.word'
if (Test-Path -LiteralPath $record) {
    $guard.Dispose()
    throw 'Existing Word ownership record must be recovered by the original Bahts renderer before this export; record left untouched.'
}
$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
try {
    $word = New-Object -ComObject Word.Application
    $owned = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $_.Id -notin $before } | ForEach-Object { $_.Id })
    if ($owned) { Set-Content -LiteralPath $record -Encoding ASCII -Value @(Get-Process -Id $owned | ForEach-Object { "$($_.Id)|$($_.StartTime.Ticks)" }) }
    $oldNumeral = $word.Options.ArabicNumeral
    $word.Options.ArabicNumeral = 2
    $word.Visible = $false; $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($InputDocx, $false, $true)
    $doc.Repaginate()
    $word.ScreenUpdating = $true
    $doc.ExportAsFixedFormat($OutputPdf, 17)
    $doc.Close($false)
}
finally {
    try { $word.Options.ArabicNumeral = $oldNumeral } catch {}
    try { $word.Quit([ref]0) } catch {}
    try { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) } catch {}
    Start-Sleep -Milliseconds 500
    foreach ($pidWord in $owned) { Stop-Process -Id $pidWord -Force -ErrorAction SilentlyContinue }
    Remove-Item -LiteralPath $record -Force -ErrorAction SilentlyContinue
    $guard.Dispose()
}
