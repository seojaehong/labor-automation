@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo  labor-automation setup
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ from https://www.python.org
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python %PY_VER%

:: Install dependencies
echo.
echo [1/3] Installing dependencies...
python -m pip install --upgrade pip -q
python -m pip install -r scripts\legal-hub\requirements.txt -q
if errorlevel 1 (
    echo [ERROR] pip install failed
    exit /b 1
)
echo [OK] Dependencies installed

:: Unit tests
echo.
echo [2/3] Running unit tests...
python -m pytest scripts\legal-hub\ --tb=short -q
if errorlevel 1 (
    echo [WARN] Some unit tests failed
) else (
    echo [OK] All unit tests passed
)

:: E2E tests
echo.
echo [3/3] Running E2E cowork chain test...
set OUTPUT_DIR=C:\dev\output\labor-automation-e2e
python scripts\legal-hub\e2e_cowork_chain.py --output-dir "%OUTPUT_DIR%"
if errorlevel 1 (
    echo [ERROR] E2E test failed
    exit /b 1
)
echo [OK] E2E passed

:: Done
echo.
echo ============================================================
echo  Setup complete. Results: %OUTPUT_DIR%
echo ============================================================
echo.
exit /b 0
