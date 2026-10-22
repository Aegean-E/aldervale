@echo off
setlocal
cd /d "%~dp0"
py -3 -m aldervale --version >nul 2>nul
if not errorlevel 1 goto :foundpy
python -m aldervale --version >nul 2>nul
if not errorlevel 1 goto :foundpython
echo ALDERVALE needs Python 3.10 or newer on PATH or the py launcher.
echo Install it from https://www.python.org/downloads/ and try again.
pause
exit /b 1

:foundpy
set "RUNCMD=py -3"
goto :checks

:foundpython
set "RUNCMD=python"

:checks
if "%~1"=="--version" (
    %RUNCMD% -m aldervale --version
    exit /b 0
)
where wt.exe >nul 2>nul
if errorlevel 1 goto :plain
wt.exe -d "%CD%" --title ALDERVALE %COMSPEC% /k %RUNCMD% -m aldervale
exit /b 0

:plain
mode con cols=140 lines=62 >nul 2>nul
title ALDERVALE
%RUNCMD% -m aldervale %*
if errorlevel 1 pause
exit /b %errorlevel%
