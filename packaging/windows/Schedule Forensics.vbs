' Schedule Forensics - double-click to start the local dashboard with NO console window.
'
' Starts the local server (127.0.0.1) and opens your browser. Closing the browser window
' stops the server automatically (the tool turns itself off); "Quit" in the app stops it now.
'
' Requires the tool installed so that "pythonw -m schedule_forensics.launcher" resolves on
' PATH (activate your venv and run "pip install -e ." once). If pythonw is not on PATH, use
' Install-Desktop-Shortcut.ps1 instead - it pins the exact interpreter path.
Option Explicit
Dim sh
Set sh = CreateObject("WScript.Shell")
' window style 0 = hidden (no console), False = don't wait for it to finish
sh.Run "pythonw -m schedule_forensics.launcher", 0, False
