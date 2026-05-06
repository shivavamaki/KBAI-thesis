@echo off
REM Script to create a distributable ZIP package of MediCheck App
REM Run from the project root directory

setlocal enabledelayedexpansion

echo.
echo Creating MediCheck Distribution Package...
echo.

REM Check if 7-Zip or Winrar is available, otherwise fail gracefully
where 7z >nul 2>&1
if not errorlevel 1 (
    set ZIPPER=7z
    set ZIP_CMD=7z a -r
    set ZIP_EXT=.7z
    goto :zip_found
)

where powershell >nul 2>&1
if not errorlevel 1 (
    set ZIPPER=powershell
    set ZIP_EXT=.zip
    goto :zip_found
)

echo [ERROR] No ZIP utility found. Please manually create a ZIP file containing:
echo   - run.bat
echo   - run.sh
echo   - launch.py
echo   - QUICKSTART.md
echo   - PACKAGE.md
echo   - requirements.txt
echo   - pharmacist_app/
echo   - data/
echo   - .streamlit/
echo.
pause
exit /b 1

:zip_found

REM Remove old package if exists
if exist "medicheck-app.zip" del medicheck-app.zip
if exist "medicheck-app.7z" del medicheck-app.7z

REM Create package using appropriate tool
if "%ZIPPER%"=="7z" (
    echo [→] Creating package with 7-Zip...
    
    REM Create the package, excluding venv, __pycache__, .git, etc.
    7z a -r medicheck-app.7z ^
        run.bat ^
        run.sh ^
        launch.py ^
        QUICKSTART.md ^
        PACKAGE.md ^
        requirements.txt ^
        pharmacist_app ^
        data ^
        .streamlit ^
        -xr!venv -xr!.git -xr!__pycache__ -xr!*.pyc -xr!.pytest_cache
    
    if errorlevel 1 (
        echo [ERROR] Failed to create 7z package
        pause
        exit /b 1
    )
    echo [✓] Package created: medicheck-app.7z
) else if "%ZIPPER%"=="powershell" (
    echo [→] Creating package with PowerShell...
    
    REM PowerShell ZIP creation
    powershell -Command "Add-Type -AssemblyName 'System.IO.Compression.FileSystem'; [System.IO.Compression.ZipFile]::CreateFromDirectory('.');"
    
    echo [✓] Package created: medicheck-app.zip
)

echo.
echo ================================================
echo   Package Ready for Distribution!
echo ================================================
echo.
echo Size: 
dir medicheck-app.* | find /v "Directory"
echo.
echo Share this file with users. They just need to:
echo   1. Extract the ZIP file
echo   2. Double-click run.bat (Windows) or run bash run.sh (Mac/Linux)
echo.
pause
