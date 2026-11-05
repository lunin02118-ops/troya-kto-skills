param([string]$Drw)
Set-Location $PSScriptRoot
# Макросы SW+ — из инструментария: ESKD_TOOLKIT, инструментарий самого скрипта, локальная копия установщика, NAS (аудит 24.09.2026)
# Инструментарий скрипта — вверх от $PSScriptRoot до папки с 02_Шаблоны_и_Форматки; не нашёлся — пропускается
$own = $PSScriptRoot
while ($own -and -not (Test-Path -LiteralPath (Join-Path $own '02_Шаблоны_и_Форматки'))) {
    $up = Split-Path -Parent $own
    $own = if ($up -ne $own) { $up } else { $null }   # корень диска или UNC — дальше некуда
}
$rel = '03_Макросы_и_Плагины\Макросы_SW_ZTool\SWPlusMacro_v_2018_SP0.0\DProp\DProp.swp'
$local = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA 'ESKD\Toolkit' } else { $null }
$roots = @($env:ESKD_TOOLKIT, $own,
       '<WORK>\06_Справочники_и_шаблоны\03_SolidWorks_шаблоны_и_библиотеки', $local,
       '<СЕТЬ_КО>\_Библиотека проектирования\_инструменты_конструктора') | Where-Object { $_ }
$m = $roots |
     ForEach-Object { Join-Path $_ $rel } | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $m) { throw "Не найден макрос SW+: $rel — задайте ESKD_TOOLKIT (искали в: $($roots -join '; '))" }
$pidFile = Join-Path $env:TEMP ("eskd_sw_pid_{0}.txt" -f $PID)
$macroJob = Start-Job -ScriptBlock {
    param($p, $d, $m)
    Set-Location $p
    python run_macro.py $d $m DProp_run main --pid-file $using:pidFile
} -ArgumentList $PSScriptRoot, $Drw, $m
$ErrorActionPreference = 'Stop'
$expectedPid = $null
$ok = $false
$dpropPid = $null
for ($i = 0; $i -lt 30 -and -not $ok; $i++) { Start-Sleep 1; $ok = (python macro_ui.py list | Select-String 'DProp') -ne $null; if (Test-Path $pidFile) { $expectedPid = [int](Get-Content $pidFile -Raw).Trim() }; if ($ok) { $dpropPid = [int](python macro_ui.py pid 'DProp'); if ($expectedPid -and $dpropPid -ne $expectedPid) { throw 'DProp belongs to unexpected SLDWORKS PID' } } }
if (-not $ok) { throw 'окно DProp не появилось' }
python macro_ui.py click-text 'Изменить основную надпись' 'DProp' $dpropPid
if ($LASTEXITCODE -ne 0) { throw "DProp title-block control was not uniquely identified" }
$ok = $false
$masterPid = $null
for ($i = 0; $i -lt 30 -and -not $ok; $i++) { Start-Sleep 1; $ok = (python macro_ui.py list | Select-String 'Master') -ne $null; if ($ok) { $masterPid = [int](python macro_ui.py pid 'Master') } }
if (-not $ok) { throw 'окно Master не появилось' }
python macro_ui.py click-text 'Книжная' 'Master' $masterPid
if ($LASTEXITCODE -ne 0) { throw "Format master portrait control was not uniquely identified" }
Start-Sleep 1
python macro_ui.py shot fmt_check.png | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Format master screenshot failed" }
python macro_ui.py click-text 'Ok' 'Master' $masterPid
if ($LASTEXITCODE -ne 0) { throw "Format master OK control was not uniquely identified" }
Start-Sleep 8
if (@(python macro_ui.py list | Select-String 'Master').Count -ne 0) { throw 'Format master did not close after OK' }
if (@(python macro_ui.py list | Select-String 'DProp').Count -eq 0) { throw 'DProp post-state missing before close' }
python macro_ui.py click-text 'Закрыть' 'DProp' $dpropPid
if ($LASTEXITCODE -ne 0) { throw "DProp close control was not uniquely identified" }
Start-Sleep 2
if (@(python macro_ui.py list | Select-String 'DProp').Count -ne 0) { throw 'DProp did not close after Close control' }
$sheetInfo = python sheet_info.py $Drw
if ($LASTEXITCODE -ne 0 -or -not ($sheetInfo | Select-String 'размер')) { throw "sheet_info post-save format verification failed" }
