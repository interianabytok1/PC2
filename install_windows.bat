@echo off
setlocal

set "APP_DIR=%USERPROFILE%\PolozkyPreOberon"
set "EXE_PATH=%APP_DIR%\PolozkyPreOberon.exe"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\PolozkyPreOberon.lnk"

echo Instalujem zavislosti a vytvaram Windows aplikaciu...
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

python build.py
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
echo Instalacia sa nepodarila. Skontrolujte, ci je nainstalovany Python 3.12+.
pause
exit /b 1