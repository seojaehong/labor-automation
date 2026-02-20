@echo off
:: run_watch.bat -- watch_inbox.py 실행 래퍼
:: Windows cp949 환경에서 한글/이모지 인코딩 오류 방지
::
:: 사용법:
::   run_watch.bat MATTERS\CASE-001
::   run_watch.bat MATTERS\CASE-001 --inbox 00_inbox

setlocal
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if "%~1"=="" (
    echo [오류] 사건 폴더 경로를 인수로 전달하세요.
    echo 예: run_watch.bat MATTERS\CASE-001
    exit /b 1
)

python scripts\legal-hub\watch_inbox.py %*
endlocal
