Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
Set env = WshShell.Environment("Process")

' Tcl/Tkのバージョン競合を防ぐ（子プロセスに継承される）
env("TCL_LIBRARY") = "C:\Python314\tcl\tcl8.6"
env("TK_LIBRARY") = "C:\Python314\tcl\tk8.6"
env("PYTHONUTF8") = "1"

' 同じフォルダの watchdog.py を pythonw で非表示起動
' watchdog.py が timer.py の自動再起動ループを回す
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
watchdogPath = scriptDir & "\watchdog.py"

' Python 3.14を直接指定（pyランチャー経由だとTcl競合が起きる）
' 0=非表示, False=待たない（fire-and-forget）
WshShell.Run """C:\Python314\pythonw.exe"" """ & watchdogPath & """", 0, False
