@echo off
chcp 65001 >nul 2>&1
set PYTHONUTF8=1

REM --- Check Python 3.14 ---
py -3.14 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.14 not found. Please install Python 3.14.
    pause
    exit /b 1
)

REM --- Install dependencies ---
echo [1/3] Installing dependencies...
py -3.14 -m pip install pystray Pillow --quiet
if errorlevel 1 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

REM --- Create startup shortcut ---
echo [2/3] Registering startup...
set "SCRIPT_DIR=%~dp0"
set "VBS_PATH=%SCRIPT_DIR%start_hidden.vbs"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_DIR%\Desktop_Timer.lnk"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Startup') + '\Desktop_Timer.lnk'); $sc.TargetPath = '%VBS_PATH%'; $sc.WorkingDirectory = '%SCRIPT_DIR%'; $sc.Description = 'Desktop Timer'; $sc.Save()"

REM --- Kill existing instance and launch ---
echo [3/3] Launching Desktop Timer...
powershell -NoProfile -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*timer.py*' } | Stop-Process -Force" >nul 2>&1
timeout /t 1 /nobreak >nul
start "" wscript "%VBS_PATH%"

echo.
echo Done! Desktop Timer is running.
echo Startup shortcut has been created.
timeout /t 3 /nobreak >nul
