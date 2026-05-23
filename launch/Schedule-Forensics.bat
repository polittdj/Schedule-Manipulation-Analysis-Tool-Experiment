@echo off
rem Schedule Forensics - one-click launcher (Windows).
rem Double-click this file, or right-click -> Send to -> Desktop (create shortcut).
rem First run sets up the environment; later runs just start the tool.
setlocal

rem -- Optional config: edit if you like --
if not defined SF_PORT set SF_PORT=5000
rem To use a LOCAL Qwen-class model (llama.cpp / LM Studio / vLLM), uncomment + set
rem (loopback only):
rem set SF_LLM_BASE_URL=http://127.0.0.1:8080/v1
rem set SF_LLM_MODEL=qwen

rem -- Locate the repo (this script lives in <repo>\launch) --
cd /d "%~dp0.."

rem -- First-run setup: virtualenv + install --
if not exist ".venv\Scripts\python.exe" (
  echo First run: setting up the environment ^(this happens once^)...
  python -m venv .venv || goto :error
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -e . || goto :error
)

echo Starting Schedule Forensics at http://127.0.0.1:%SF_PORT%
echo (Close this window to stop the tool. All data stays on this machine.)
start "" "http://127.0.0.1:%SF_PORT%"
".venv\Scripts\python.exe" -m schedule_forensics.webapp
goto :eof

:error
echo.
echo Setup failed. Make sure Python 3.11+ is installed and on your PATH
echo (https://www.python.org/downloads/ -- tick "Add Python to PATH").
pause
