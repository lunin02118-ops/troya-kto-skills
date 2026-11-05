param(
  [Parameter(Mandatory = $true)][string]$Src,   # docx или папка с docx
  [Parameter(Mandatory = $true)][string]$Out,   # pdf (для одного файла) или папка вывода
  [string]$Log = "",                            # журнал шагов (UTF-8), по желанию
  [int]$TimeoutSec = 120                        # сторож: столько ждать один документ
)
# Экспорт docx -> PDF отдельным невидимым экземпляром Word. Word и просмотрщик PDF пользователя не трогаются:
# закрывается только свой экземпляр (новый процесс WINWORD, которого не было до запуска). PDF, открытый
# у пользователя (заблокирован), пропускается с LOCKED. Документ открывается только для чтения,
# ComputeStatistics не вызывается (на нём Word зависал). Пути передаются в COM строго как [string]:
# обёрнутая PowerShell строка из конвейера вешала Documents.Open.
function Write-Log($m) { if ($Log) { Add-Content -LiteralPath $Log -Value ("{0:HH:mm:ss} {1}" -f (Get-Date), $m) -Encoding UTF8 } }
function Test-Locked([string]$p) {
  if (-not (Test-Path -LiteralPath $p)) { return $false }
  try { $f = [IO.File]::Open($p, 'Open', 'ReadWrite', 'None'); $f.Close(); return $false } catch { return $true }
}

$jobs = @()
if (Test-Path -LiteralPath $Src -PathType Container) {
  New-Item -ItemType Directory -Force -Path $Out | Out-Null
  foreach ($f in Get-ChildItem -LiteralPath $Src -Filter "*.docx") {
    if ($f.Name -like '~$*') { continue }
    $jobs += , @([string]$f.FullName, [string](Join-Path $Out ($f.BaseName + ".pdf")))
  }
} else {
  $jobs += , @([string](Resolve-Path -LiteralPath $Src).Path, [string]$Out)
}

$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$word = New-Object -ComObject Word.Application
$mine = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id } | ForEach-Object { $_.Id })
$word.Visible = $false
$word.DisplayAlerts = 0
# сторож: если документ висит дольше TimeoutSec, снимает только свой процесс Word
$guard = $null
if ($mine.Count -eq 1) {
  $limit = $TimeoutSec * [Math]::Max(1, $jobs.Count)
  $guard = Start-Process powershell -WindowStyle Hidden -PassThru -ArgumentList @(
    "-NoProfile", "-Command", "Start-Sleep -Seconds $limit; Stop-Process -Id $($mine[0]) -Force -ErrorAction SilentlyContinue")
}
try {
  foreach ($j in $jobs) {
    [string]$docx = $j[0]; [string]$pdf = $j[1]
    if (Test-Locked $pdf) { Write-Output ("LOCKED " + $pdf); Write-Log ("LOCKED " + $pdf); continue }
    Write-Log ("open " + $docx)
    $doc = $word.Documents.Open($docx, $false, $true, $false)   # ConfirmConversions, ReadOnly, AddToRecentFiles
    try {
      $doc.ExportAsFixedFormat($pdf, 17)                         # 17 = wdExportFormatPDF
      Write-Output ("OK " + $pdf); Write-Log ("ok " + $pdf)
    } finally { $doc.Close(0) }
  }
} finally {
  try { $word.Quit() } catch { Write-Output "Word снят сторожем (завис)"; Write-Log "killed by guard" }
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
  if ($guard -and -not $guard.HasExited) { Stop-Process -Id $guard.Id -Force -ErrorAction SilentlyContinue }
  Write-Log "done"
}
