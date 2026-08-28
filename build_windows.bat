@echo off
setlocal
cd /d "%~dp0"
py -3 -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
py -3 build.py
if errorlevel 1 exit /b 1
echo.
echo Aplikacia je v priecinku release.
pause