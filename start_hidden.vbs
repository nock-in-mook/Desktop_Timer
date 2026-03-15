Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' このVBSファイルと同じフォルダのtimer.pyを起動
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
timerPath = scriptDir & "\timer.py"

' コンソール非表示でPythonを起動
WshShell.Run "py -3.14 """ & timerPath & """", 0, False
