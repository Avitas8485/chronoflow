@echo off

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
call venv\Scripts\activate.bat

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

REM Build application
echo Building ChronoFlow...
pyinstaller --clean --noconfirm chronoflow.spec

REM Setup startup registration
echo Setting up startup registration...
reg add "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run" /v "ChronoFlow" /t REG_SZ /d "\"%~dp0dist\ChronoFlow.exe\"" /f
if %errorlevel% equ 0 (
    echo Successfully added ChronoFlow to startup
) else (
    echo Failed to add ChronoFlow to startup
)

REM Deactivate virtual environment
deactivate

echo Build complete! Executable is in dist/ChronoFlow.exe
echo To remove from startup, run: reg delete "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run" /v "ChronoFlow" /f
pause