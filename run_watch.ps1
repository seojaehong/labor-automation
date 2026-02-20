# run_watch.ps1 -- watch_inbox.py 실행 래퍼 (PowerShell)
# Windows cp949 환경에서 한글/이모지 인코딩 오류 방지
#
# 사용법:
#   .\run_watch.ps1 MATTERS\CASE-001
#   .\run_watch.ps1 MATTERS\CASE-001 --inbox 00_inbox

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$MatterPath,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$scriptArgs = @($MatterPath) + $ExtraArgs

python scripts\legal-hub\watch_inbox.py @scriptArgs
