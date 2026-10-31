@echo off
setlocal EnableExtensions
cd /d "%~dp0"

REM Request Administrator rights (needed to toggle network)
net session >nul 2>&1
if errorlevel 1 (
  echo Admin rights required. Requesting UAC...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

echo.
echo  === Nexora ===
echo  Toggle internet on / off
echo.

REM Find Python
set "PY_CMD="
where py >nul 2>&1
if not errorlevel 1 set "PY_CMD=py -3"
if not defined PY_CMD (
  where python >nul 2>&1
  if not errorlevel 1 set "PY_CMD=python"
)
if not defined PY_CMD (
  echo [ERROR] Python not found.
  echo Install Python 3.10+ from https://www.python.org/downloads/
  echo Enable "Add python.exe to PATH" during setup.
  pause
  exit /b 1
)

REM Create venv if missing
if not exist ".venv\Scripts\python.exe" (
  echo Creating .venv ...
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create .venv
    pause
    exit /b 1
  )
)

set "VPY=%~dp0.venv\Scripts\python.exe"
set "VPIP=%~dp0.venv\Scripts\pip.exe"

REM Install dependencies if needed
"%VPY%" -c "import fastapi,uvicorn" >nul 2>&1
if errorlevel 1 (
  echo Installing dependencies...
  "%VPIP%" install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] pip install failed
    pause
    exit /b 1
  )
  "%VPIP%" install -e . >nul 2>&1
)

echo Starting Nexora...
echo You can minimize this window. Closing it stops the app.
echo.
"%VPY%" -m nexora %*
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  echo [ERROR] Nexora exited with code %ERR%
  pause
)
exit /b %ERR%
