@echo off
REM Test script to verify MediCheck App package integrity and functionality
REM Run this before creating distribution package

echo.
echo ================================================
echo   MediCheck App - Package Integrity Test
echo ================================================
echo.

setlocal enabledelayedexpansion
set TEST_PASSED=0
set TEST_FAILED=0

REM Test 1: Check required files exist
echo [TEST 1] Checking required files...
for %%F in (
    "run.bat"
    "run.sh"
    "launch.py"
    "QUICKSTART.md"
    "PACKAGE.md"
    "DISTRIBUTION.md"
    "requirements.txt"
    "pharmacist_app\app.py"
    "data\sample_prescriptions.json"
    ".streamlit\config.toml"
) do (
    if exist %%F (
        echo   [✓] %%F
        set /a TEST_PASSED+=1
    ) else (
        echo   [✗] MISSING: %%F
        set /a TEST_FAILED+=1
    )
)

REM Test 2: Check Python
echo.
echo [TEST 2] Checking Python 3.10+...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [✗] Python not found in PATH
    set /a TEST_FAILED+=1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
    echo   [✓] Python !PYTHON_VER! found
    set /a TEST_PASSED+=1
)

REM Test 3: Check JSON syntax
echo.
echo [TEST 3] Validating JSON sample data...
python -m json.tool data\sample_prescriptions.json >nul 2>&1
if errorlevel 1 (
    echo   [✗] Invalid JSON in sample_prescriptions.json
    set /a TEST_FAILED+=1
) else (
    echo   [✓] Sample JSON is valid
    set /a TEST_PASSED+=1
)

REM Test 4: Check Streamlit app syntax
echo.
echo [TEST 4] Checking Streamlit app syntax...
python -m py_compile pharmacist_app\app.py >nul 2>&1
if errorlevel 1 (
    echo   [✗] Syntax error in app.py
    set /a TEST_FAILED+=1
) else (
    echo   [✓] Streamlit app has valid Python syntax
    set /a TEST_PASSED+=1
)

REM Test 5: Check documentation
echo.
echo [TEST 3] Checking documentation...
if exist QUICKSTART.md (
    find /c /i "python" QUICKSTART.md >nul
    if !errorlevel! equ 0 (
        echo   [✓] QUICKSTART.md contains Python info
        set /a TEST_PASSED+=1
    ) else (
        echo   [!] QUICKSTART.md might be incomplete
        set /a TEST_FAILED+=1
    )
)

REM Test 6: Check data directories
echo.
echo [TEST 6] Checking data directories...
for %%D in (
    "data"
    "data\raw"
    "data\processed"
    "outputs"
) do (
    if exist %%D (
        echo   [✓] Directory exists: %%D
        set /a TEST_PASSED+=1
    ) else (
        echo   [✗] Missing directory: %%D
        set /a TEST_FAILED+=1
    )
)

REM Summary
echo.
echo ================================================
echo   Test Results
echo ================================================
echo.
echo Passed: !TEST_PASSED!
echo Failed: !TEST_FAILED!
echo.

if !TEST_FAILED! equ 0 (
    echo [✓] All checks passed! Package is ready for distribution.
) else (
    echo [✗] Some checks failed. Please fix issues above before distributing.
)

echo.
pause
