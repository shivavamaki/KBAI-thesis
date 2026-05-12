@echo off
setlocal enabledelayedexpansion

echo.
echo ================================================
echo   MediCheck - Pharmacist Review App
echo ================================================
echo.

REM ── Find uv (preferred) or fall back to python ─────────────────────────────
set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
set "USE_UV=0"

if exist "%UV_EXE%" (
    set "USE_UV=1"
    echo [OK] uv found at %UV_EXE%
    goto :setup
)

where uv >nul 2>&1
if not errorlevel 1 (
    set "UV_EXE=uv"
    set "USE_UV=1"
    echo [OK] uv found in PATH
    goto :setup
)

REM Fall back to python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Neither uv nor Python found in PATH.
    echo.
    echo Install uv from: https://docs.astral.sh/uv/getting-started/installation/
    echo Or install Python from: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python found ^(uv not available - using pip^)

:setup
REM ── Create venv and install if needed ──────────────────────────────────────
if "%USE_UV%"=="1" (

    if not exist "venv" (
        echo [->] Creating virtual environment with uv...
        "%UV_EXE%" venv venv --quiet
        if errorlevel 1 ( echo [ERROR] uv venv failed & pause & exit /b 1 )
        echo [OK] Virtual environment created
    )

    echo [->] Installing packages with uv...
    "%UV_EXE%" pip install --quiet -r requirements.txt
    if errorlevel 1 ( echo [ERROR] uv pip install failed & pause & exit /b 1 )

    set "PYTHON_EXE=venv\Scripts\python.exe"

) else (

    if not exist "venv" (
        echo [->] Creating virtual environment...
        python -m venv venv
        if errorlevel 1 ( echo [ERROR] venv creation failed & pause & exit /b 1 )
        echo [OK] Virtual environment created
    )

    echo [->] Installing packages...
    venv\Scripts\pip install --quiet -r requirements.txt
    if errorlevel 1 ( echo [ERROR] pip install failed & pause & exit /b 1 )

    set "PYTHON_EXE=venv\Scripts\python.exe"

)

echo [OK] All packages ready

REM ── Create directories ──────────────────────────────────────────────────────
if not exist "data\raw"     mkdir "data\raw"
if not exist "outputs"      mkdir "outputs"

REM ── Launch ─────────────────────────────────────────────────────────────────
echo.
echo ================================================
echo   Opening browser at http://localhost:8501
echo   Press Ctrl+C to stop
echo ================================================
echo.

"%PYTHON_EXE%" -m streamlit run pharmacist_app/app.py --server.headless false --logger.level=warning

pause
