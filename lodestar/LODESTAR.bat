@echo off
rem LODESTAR - One-Pager Studio. Created by David Politte (david.j.politte@nasa.gov).
rem Double-click to start LODESTAR. Keep the window open while you work; close it to stop.
title LODESTAR - One-Pager Studio
where py >nul 2>&1 && goto :withpy
where python >nul 2>&1 && goto :withpython
echo LODESTAR needs Python 3.10 or newer, and none was found on this computer.
echo Install it from python.org (the per-user install needs no administrator rights),
echo then double-click LODESTAR again.
pause
goto :eof
:withpy
py -3 "%~dp0LODESTAR.pyz" %*
goto :done
:withpython
python "%~dp0LODESTAR.pyz" %*
:done
if errorlevel 1 pause
