@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

REM --- Запрос прав администратора (нужны для вкл/выкл сети) ---
net session >nul 2>&1
if errorlevel 1 (
  echo Нужны права администратора. Запрашиваю...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

echo.
echo  === Nexora ===
echo  Включение и отключение интернета
echo.

REM --- Поиск Python ---
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo [Ошибка] Python не найден.
  echo Установите Python 3.10+ с https://www.python.org/downloads/
  echo При установке отметьте "Add python.exe to PATH".
  pause
  exit /b 1
)

REM --- Виртуальное окружение ---
if not exist ".venv\Scripts\python.exe" (
  echo Создаю окружение .venv ...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [Ошибка] Не удалось создать .venv
    pause
    exit /b 1
  )
)

set "VPY=%~dp0.venv\Scripts\python.exe"
set "VPIP=%~dp0.venv\Scripts\pip.exe"

REM --- Зависимости ---
"%VPY%" -c "import fastapi,uvicorn" >nul 2>&1
if errorlevel 1 (
  echo Устанавливаю зависимости...
  "%VPIP%" install -r requirements.txt
  if errorlevel 1 (
    echo [Ошибка] pip install не удался
    pause
    exit /b 1
  )
  "%VPIP%" install -e . >nul 2>&1
)

echo Запускаю Nexora...
echo Окно можно свернуть. Закрытие окна остановит приложение.
echo.
"%VPY%" -m nexora %*
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  echo [Ошибка] Nexora завершилась с кодом %ERR%
  pause
)
exit /b %ERR%
