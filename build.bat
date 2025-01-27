@echo off
setlocal EnableDelayedExpansion

REM Check if ChronoFlow is running
echo Checking for running instances of ChronoFlow...
tasklist /FI "IMAGENAME eq ChronoFlow.exe" 2>NUL | find /I /N "ChronoFlow.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Found running ChronoFlow instance. Attempting to close...
    taskkill /F /IM "ChronoFlow.exe"
    if !ERRORLEVEL! EQU 0 (
        echo Successfully closed ChronoFlow
        timeout /t 2 >nul
    ) else (
        echo Failed to close ChronoFlow. Please close it manually.
        pause
        exit /b 1
    )
)

REM Clean previous build
echo Cleaning previous build...
if exist "dist\\ChronoFlow.exe" del "dist\\ChronoFlow.exe"
if exist "dist\\chronoflow.log" del "dist\\chronoflow.log"
echo Deleted previous executable and log files
if exist "build" rmdir /s /q "build"

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat || (
    echo Failed to activate virtual environment
    pause
    exit /b 1
)

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt || (
    echo Failed to install requirements
    pause
    exit /b 1
)

REM Build application
echo Building ChronoFlow...
pyinstaller --clean --noconfirm chronoflow.spec || (
    echo Build failed
    pause
    exit /b 1
)

REM Setup startup registration
echo Setting up startup registration...
reg add "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run" /v "ChronoFlow" /t REG_SZ /d "\"%~dp0dist\ChronoFlow.exe\"" /f
if !ERRORLEVEL! equ 0 (
    echo Successfully added ChronoFlow to startup
) else (
    echo Failed to add ChronoFlow to startup
)

REM Deactivate virtual environment
deactivate

echo Build complete! Executable is in dist/ChronoFlow.exe
echo To remove from startup, run: reg delete "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run" /v "ChronoFlow" /f
pause