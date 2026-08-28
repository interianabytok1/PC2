@echo off
setlocal
cd /d "%~dp0"

set "APP_DIR=%USERPROFILE%\PolozkyPreOberon"
set "EXE_PATH=%APP_DIR%\PolozkyPreOberon.exe"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\PolozkyPreOberon.lnk"

echo Instalujem zavislosti a vytvaram Windows aplikaciu...
where py >nul 2>nul
if errorlevel 1 goto :python_missing
py -3 -m pip install -r requirements.txt
if errorlevel 1 goto :error

py -3 build.py
if errorlevel 1 goto :error

if not exist "%APP_DIR%" mkdir "%APP_DIR%"
copy /Y "release\PolozkyPreOberon.exe" "%EXE_PATH%" >nul
if errorlevel 1 goto :error

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::ExpandEnvironmentVariables('%SHORTCUT_PATH%')); $s.TargetPath = [Environment]::ExpandEnvironmentVariables('%EXE_PATH%'); $s.WorkingDirectory = [Environment]::ExpandEnvironmentVariables('%APP_DIR%'); $s.Description = 'Extrahovanie poloziek pre import do OBERON-u'; $s.Save()"
if errorlevel 1 goto :error

echo.
echo Hotovo. Aplikacia je v: %APP_DIR%
echo Odkaz na ploche: %SHORTCUT_PATH%
pause
exit /b 0

:error
echo.
echo Instalacia sa nepodarila. Skontrolujte internetove pripojenie a Python 3.12+.
pause
exit /b 1

:python_missing
echo.
echo Python 3 nebol najdeny. Nainstalujte Python 3.12+ z https://www.python.org/downloads/windows/
echo Pri instalacii zaskrtnite Add python.exe to PATH.
pause
exit /b 1