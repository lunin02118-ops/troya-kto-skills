param(
  [string]$DocPath,             # docx с bookFoldPrinting (брошюра A5 на A4)
  [string]$Printer,             # имя принтера
  [string]$OutPdf = ""          # для пробного прогона через "Microsoft Print to PDF"
)
# Печать документа Word на указанный принтер; принтер по умолчанию восстанавливается (Word меняет его при ActivePrinter).
$def = Get-CimInstance Win32_Printer | Where-Object Default
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $wd = $word.Documents.Open($DocPath, $false, $true)
  $word.ActivePrinter = $Printer
  $missing = [Type]::Missing
  if ($OutPdf) {
    # Background, Append, Range, OutputFileName, From, To, Item, Copies, Pages, PageType, PrintToFile
    $wd.PrintOut($false, $false, 0, $OutPdf, $missing, $missing, 0, 1, "", 0, $true)
  } else {
    $wd.PrintOut($false, $false, 0, $missing, $missing, $missing, 0, 1, "", 0, $false)
  }
  Write-Output ("PAGES=" + $wd.ComputeStatistics(2) + " PRINTER=" + $word.ActivePrinter)
  $wd.Close(0)
} finally {
  $word.Quit()
  Start-Sleep -Milliseconds 500
  if ($def) {
    $p = Get-CimInstance Win32_Printer | Where-Object { $_.Name -eq $def.Name }
    Invoke-CimMethod -InputObject $p -MethodName SetDefaultPrinter | Out-Null
  }
  Write-Output ("DEFAULT=" + (Get-CimInstance Win32_Printer | Where-Object Default).Name)
}
