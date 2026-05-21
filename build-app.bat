@echo off
REM Double-click (Windows) to BUILD a self-contained app. The result needs no Python to run.
REM (PyInstaller does not cross-compile: run this on Windows to get a Windows .exe.)

cd /d "%~dp0"

if not exist ".venv" (
  py -3.13 -m venv .venv 2>nul || python -m venv .venv
  if errorlevel 1 ( echo Install Python 3.13 first, then try again. & pause & exit /b 1 )
)

".venv\Scripts\python" -m pip install --quiet --upgrade pip
".venv\Scripts\python" -m pip install --quiet -r requirements.txt pyinstaller
if errorlevel 1 ( echo Install failed. & pause & exit /b 1 )
".venv\Scripts\pyinstaller" --noconfirm --clean schedule_tool.spec
if errorlevel 1 ( echo Build failed. & pause & exit /b 1 )

echo.
echo Done! Your app is:  dist\ScheduleTool.exe
echo Double-click it to run the tool (no Python needed). You can move it anywhere.
pause
