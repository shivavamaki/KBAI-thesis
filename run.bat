@echo off
setlocal enabledelayedexpansion

REM MediCheck Pharmacist Review App Launcher for Windows
REM This script sets up Python dependencies and launches the web app

echo.
echo ================================================
echo   MediCheck Pharmacist Review App
echo ================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.10+ is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo [✓] Python %PYTHON_VER% found

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo.
    echo [→] Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [✓] Virtual environment created
)

REM Activate virtual environment
echo.
echo [→] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo [→] Installing dependencies (this may take a minute)...
pip install --quiet --upgrade pip setuptools
pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [✓] Dependencies installed

REM Create data and output directories
if not exist "data" mkdir data
if not exist "outputs" mkdir outputs

echo.
echo ================================================
echo   Launching MediCheck...
echo ================================================
echo.
echo The app will open in your browser at:
echo   http://localhost:8501
echo.
echo Press Ctrl+C to stop the server
echo.

REM Launch Streamlit app
streamlit run pharmacist_app/app.py --logger.level=warning

pause
