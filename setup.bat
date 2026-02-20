@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1

echo ============================================================
echo  labor-automation setup
echo ============================================================
echo.

:: ── Python 확인 ──────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python을 찾을 수 없습니다.
    echo         https://www.python.org 에서 Python 3.11 이상을 설치하세요.
    pause & exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python %PY_VER%

:: ── pip 의존성 설치 ───────────────────────────────────────────
echo.
echo [1/3] 의존성 설치 중...
python -m pip install --upgrade pip -q
python -m pip install -r scripts\legal-hub\requirements.txt -q
if errorlevel 1 (
    echo [ERROR] pip install 실패
    pause & exit /b 1
)
echo [OK] 의존성 설치 완료

:: ── 단위 테스트 ──────────────────────────────────────────────
echo.
echo [2/3] 단위 테스트 실행 중...
python -m pytest scripts\legal-hub\ -v --tb=short -q
if errorlevel 1 (
    echo [WARN] 단위 테스트 일부 실패 — 계속 진행합니다.
) else (
    echo [OK] 단위 테스트 전체 통과
)

:: ── E2E 테스트 ───────────────────────────────────────────────
echo.
echo [3/3] E2E 체인 테스트 실행 중...
set OUTPUT_DIR=C:\dev\output\labor-automation-e2e
python scripts\legal-hub\e2e_cowork_chain.py --output-dir "%OUTPUT_DIR%"
if errorlevel 1 (
    echo [ERROR] E2E 테스트 실패
    pause & exit /b 1
)
echo [OK] E2E 완료

:: ── 완료 ─────────────────────────────────────────────────────
echo.
echo ============================================================
echo  설치 및 검증 완료
echo  결과물: %OUTPUT_DIR%
echo ============================================================
echo.
pause
