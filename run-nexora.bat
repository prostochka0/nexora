@echo off
REM Запустите этот файл от имени администратора (ПКМ → «Запуск от имени администратора»)
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m nexora %*
) else (
  python -m nexora %*
)
