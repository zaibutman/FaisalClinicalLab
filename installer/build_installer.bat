@echo off
REM ==========================================================================
REM Build the Faisal Clinical Laboratory Windows installer with Inno Setup.
REM Locates ISCC.exe in common install locations (does NOT rely on PATH),
REM then compiles installer\FaisalClinicalLaboratory.iss.
REM ==========================================================================
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "ISS_FILE=%SCRIPT_DIR%FaisalClinicalLaboratory.iss"

REM --- Locate ISCC.exe (compiler) ------------------------------------------
set "ISCC="
for %%P in (
    "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
    "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    "%ProgramFiles%\Inno Setup 6\ISCC.exe"
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    "C:\Program Files\Inno Setup 6\ISCC.exe"
    "%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe"
    "C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
) do (
    if not defined ISCC if exist "%%~P" set "ISCC=%%~P"
)

if not defined ISCC (
    echo ERROR: ISCC.exe not found.
    echo Install Inno Setup 6 from https://jrsoftware.org/isinfo.php
    echo or run: winget install JRSoftware.InnoSetup
    exit /b 1
)

echo Using Inno Setup compiler: "%ISCC%"
echo Compiling: "%ISS_FILE%"
echo.

if not exist "%ISS_FILE%" (
    echo ERROR: installer script not found: "%ISS_FILE%"
    exit /b 1
)

"%ISCC%" "%ISS_FILE%"
if errorlevel 1 (
    echo.
    echo BUILD FAILED
    exit /b 1
)

echo.
echo BUILD SUCCEEDED
echo Installer written to: "%SCRIPT_DIR%Output"
exit /b 0
