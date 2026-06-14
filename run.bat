@echo off
echo.
echo ================================================
echo   MediCheck - Pharmacist Review App
echo ================================================
echo.

REM Try uv Python first (installed via uv)
set "UV_PY=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14.4-windows-x86_64-none\python.exe"
if exist "%UV_PY%" (
    echo [OK] Found Python via uv
    "%UV_PY%" pharmacist_app\web.py
    goto end
)

REM Try py launcher
where py >nul 2>&1
if not errorlevel 1 (
    echo [OK] Found py launcher
    py pharmacist_app\web.py
    goto end
)

REM Try python in PATH
where python >nul 2>&1
if not errorlevel 1 (
    echo [OK] Found python in PATH
    python pharmacist_app\web.py
    goto end
)

echo [ERROR] Python not found.
echo Install from: https://www.python.org/downloads/
echo.

:end
pause
