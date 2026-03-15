@echo off
chcp 65001 >nul 2>&1
set PYTHONUTF8=1

REM --- Install dependencies ---
py -3.14 -m pip install pystray Pillow --quiet

REM --- Create startup shortcut ---
set "SCRIPT_DIR=%~dp0"
set "VBS_PATH=%SCRIPT_DIR%start_hidden.vbs"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_DIR%\Desktop_Timer.lnk"

REM PowerShell でショートカット作成（日本語埋め込み回避）
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%SHORTCUT_PATH%'); $sc.TargetPath = '%VBS_PATH%'; $sc.WorkingDirectory = '%SCRIPT_DIR%'; $sc.Description = 'Desktop Timer'; $sc.Save()"

REM --- Launch timer ---
start "" py -3.14 "%SCRIPT_DIR%timer.py"
