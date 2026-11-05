param([string]$Drw)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
# Макросы SW+ — из инструментария: ESKD_TOOLKIT, инструментарий самого скрипта, локальная копия установщика, NAS (аудит 24.09.2026)
# Инструментарий скрипта — вверх от $PSScriptRoot до папки с 02_Шаблоны_и_Форматки; не нашёлся — пропускается
$own = $PSScriptRoot
while ($own -and -not (Test-Path -LiteralPath (Join-Path $own '02_Шаблоны_и_Форматки'))) {
    $up = Split-Path -Parent $own
    $own = if ($up -ne $own) { $up } else { $null }   # корень диска или UNC — дальше некуда
}
$rel = '03_Макросы_и_Плагины\Макросы_SW_ZTool\SWPlusMacro_v_2018_SP0.0\SpecEditor\SpecEditor.swp'
$local = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA 'ESKD\Toolkit' } else { $null }
$roots = @($env:ESKD_TOOLKIT, $own,
       '<WORK>\06_Справочники_и_шаблоны\03_SolidWorks_шаблоны_и_библиотеки', $local,
       '<СЕТЬ_КО>\_Библиотека проектирования\_инструменты_конструктора') | Where-Object { $_ }
$m = $roots |
     ForEach-Object { Join-Path $_ $rel } | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $m) { throw "Не найден макрос SW+: $rel — задайте ESKD_TOOLKIT (искали в: $($roots -join '; '))" }
$pidFile = Join-Path $env:TEMP ("eskd_sw_pid_{0}.txt" -f $PID)
python run_macro.py $Drw $m SpecEditor_run main --drop-sheet SP1 --pid-file $pidFile
if ($LASTEXITCODE -ne 0) { throw "SpecEditor macro launch failed" }
$expectedPid = [int](Get-Content -LiteralPath $pidFile -Raw).Trim()
$h = $null
$formPid = $null
for ($i = 0; $i -lt 20 -and -not $h; $i++) {
    Start-Sleep 1
    $h = python macro_ui.py list | Select-String 'SpecEditor'
    if ($h) { $formPid = [int](python macro_ui.py pid 'SpecEditor'); if ($formPid -ne $expectedPid) { throw "SpecEditor belongs to unexpected SLDWORKS PID" } }
}
if (-not $h) { throw 'окно SpecEditor не появилось' }
python macro_ui.py shot se_form.png | Out-Null
if ($LASTEXITCODE -ne 0) { throw "SpecEditor screenshot failed" }
python macro_ui.py click-text 'Создать' 'SpecEditor' $formPid
if ($LASTEXITCODE -ne 0) { throw "SpecEditor Create control was not uniquely identified" }
$completed = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep 2
    $remaining = @(python macro_ui.py list | Select-String 'SpecEditor')
    if ($remaining.Count -eq 0) { $completed = $true; break }
}
if (-not $completed) { throw 'SpecEditor did not close within timeout' }
python macro_ui.py list
if ($LASTEXITCODE -ne 0) { throw "SpecEditor final state check failed" }
$sheetInfo = python sheet_info.py $Drw
if ($LASTEXITCODE -ne 0 -or -not ($sheetInfo | Select-String '^SP1\s')) { throw 'SP1 post-save sheet verification failed' }
