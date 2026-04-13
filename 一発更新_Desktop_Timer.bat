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

REM --- Create launcher in user profile (avoids Japanese path in shortcut) ---
echo [2/4] Creating launcher...
set "SCRIPT_DIR=%~dp0"
set "LAUNCHER=%USERPROFILE%\.desktop_timer_launcher.py"

py -3.14 -c "import os; p=os.path.join(os.environ['USERPROFILE'],'.desktop_timer_launcher.py'); open(p,'w',encoding='utf-8').write('\"\"\"Desktop Timer launcher\"\"\"\\nimport os,subprocess\\nwatchdog=os.path.join(\"G:\",os.sep,\"\u30de\u30a4\u30c9\u30e9\u30a4\u30d6\",\"_other-projects\",\"Desktop_Timer\",\"watchdog.py\")\\nenv=os.environ.copy()\\nenv[\"TCL_LIBRARY\"]=r\"C:\\Python314\\tcl\\tcl8.6\"\\nenv[\"TK_LIBRARY\"]=r\"C:\\Python314\\tcl\\tk8.6\"\\nenv[\"PYTHONUTF8\"]=\"1\"\\nif os.path.exists(watchdog):\\n    subprocess.Popen([r\"C:\\Python314\\pythonw.exe\",watchdog],cwd=os.path.dirname(watchdog),env=env)\\n')"

REM --- Create startup shortcut (no Japanese in any path) ---
echo [3/4] Registering startup...
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Startup') + '\Desktop Timer.lnk'); $sc.TargetPath = 'C:\Python314\pythonw.exe'; $sc.Arguments = '\"' + $env:USERPROFILE + '\.desktop_timer_launcher.py\"'; $sc.WorkingDirectory = $env:USERPROFILE; $sc.Description = 'Desktop Timer Watchdog'; $sc.WindowStyle = 7; $sc.Save()"

REM --- Kill existing instance and launch ---
echo [4/4] Launching Desktop Timer...
powershell -NoProfile -Command "Get-Process pythonw -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*watchdog.py*' -or $_.CommandLine -like '*timer.py*' } | Stop-Process -Force" >nul 2>&1
timeout /t 1 /nobreak >nul
start "" "C:\Python314\pythonw.exe" "%LAUNCHER%"

echo.
echo Done! Desktop Timer is running.
echo Startup shortcut has been created.
timeout /t 3 /nobreak >nul
