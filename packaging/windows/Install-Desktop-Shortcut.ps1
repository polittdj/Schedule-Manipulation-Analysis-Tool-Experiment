<#
.SYNOPSIS
  Create a "Schedule Forensics" icon on your Windows Desktop that launches the tool with a
  double-click — no console window — and opens it in your browser.

.DESCRIPTION
  The shortcut runs `pythonw.exe -m schedule_forensics.launcher` (pythonw = no console),
  which starts the local dashboard on 127.0.0.1 and opens your browser. Closing the browser
  window stops the server automatically (the tool turns itself off). "Quit" in the app stops
  it immediately.

  Run this once, from the virtual environment where you installed the tool:
      .venv\Scripts\Activate.ps1
      pip install -e .
      powershell -ExecutionPolicy Bypass -File packaging\windows\Install-Desktop-Shortcut.ps1

.PARAMETER Python
  Optional path to the python.exe whose environment has the tool installed. Defaults to the
  `python` on PATH (your activated virtual environment).
#>
param([string]$Python = "")

$ErrorActionPreference = "Stop"

# 1. Resolve the interpreter, then its windowless twin (pythonw.exe).
if (-not $Python) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) { throw "No 'python' on PATH. Activate your venv (.venv\Scripts\Activate.ps1) first." }
    $Python = $cmd.Source
}
$pythonw = Join-Path (Split-Path $Python) "pythonw.exe"
if (-not (Test-Path $pythonw)) { $pythonw = $Python }  # fall back to python.exe if no pythonw

# 2. Verify the package is importable in that environment.
& $Python -c "import schedule_forensics" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "schedule_forensics is not installed for $Python. Run 'pip install -e .' in that environment first."
}

# 3. Create the Desktop shortcut with the bundled icon.
$icon = Join-Path $PSScriptRoot "schedule-forensics.ico"
$desktop = [Environment]::GetFolderPath("Desktop")
$lnkPath = Join-Path $desktop "Schedule Forensics.lnk"

$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut($lnkPath)
$lnk.TargetPath = $pythonw
$lnk.Arguments = "-m schedule_forensics.launcher"
$lnk.WorkingDirectory = $HOME
$lnk.Description = "Schedule Forensics - local forensic schedule analysis (offline)"
if (Test-Path $icon) { $lnk.IconLocation = $icon }
$lnk.Save()

Write-Host "Created desktop shortcut: $lnkPath"
Write-Host "Target: $pythonw -m schedule_forensics.launcher"
Write-Host "Double-click 'Schedule Forensics' on your Desktop to start. Close the window to stop."
