@echo off
chcp 65001 > nul
rem Показывает, что изменит установка, ничего не записывая.
python "%~dp0Установка\install.py"
echo.
pause
