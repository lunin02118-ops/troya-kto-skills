@echo off
chcp 65001 > nul
rem Ставит навыки агентов TROYA из этой папки в Claude Code, Codex и Antigravity (Gemini). Прежние копии сохраняются.
python "%~dp0Установка\install.py" --execute
echo.
pause
