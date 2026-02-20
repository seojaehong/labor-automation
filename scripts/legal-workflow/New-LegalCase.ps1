[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$CaseId,

    [string]$Title = "",

    [string]$Root = (Join-Path (Get-Location) "cases")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-FileIfMissing {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        $Content | Set-Content -LiteralPath $Path -Encoding UTF8
    }
}

$safeCaseId = ($CaseId -replace '[\\/:*?"<>|]+', "-" -replace "\s+", "_").Trim("_")
if ([string]::IsNullOrWhiteSpace($safeCaseId)) {
    throw "CaseId is invalid after sanitization. Please use a value like '2026-LA-001'."
}

$casePath = Join-Path $Root $safeCaseId
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
$titleValue = if ([string]::IsNullOrWhiteSpace($Title)) { "TBD" } else { $Title }

$directories = @(
    "00_admin",
    "01_intake",
    "02_research",
    "03_platform_exports\lbox",
    "03_platform_exports\superlawyer",
    "03_platform_exports\bigcase",
    "03_platform_exports\other",
    "04_authority_notes",
    "05_drafts",
    "06_final",
    "07_audit"
)

foreach ($dir in $directories) {
    New-Item -ItemType Directory -Path (Join-Path $casePath $dir) -Force | Out-Null
}

New-FileIfMissing -Path (Join-Path $casePath "00_admin\case-meta.yaml") -Content @"
case_id: $safeCaseId
title: $titleValue
created_at: $createdAt
status: intake
owner: ""
platforms:
  - lbox
  - superlawyer
  - bigcase
notes: ""
"@

New-FileIfMissing -Path (Join-Path $casePath "01_intake\facts.md") -Content @"
# Facts

## Parties
- claimant:
- respondent:

## Timeline
- [YYYY-MM-DD] event

## Requested outcome
- 
"@

New-FileIfMissing -Path (Join-Path $casePath "02_research\questions.md") -Content @"
# Research Questions

1. 
2. 
3. 
"@

New-FileIfMissing -Path (Join-Path $casePath "04_authority_notes\authority-notes.md") -Content @"
# Authority Notes

Add one block per authority:

## [Authority ID]
- source file:
- court/agency:
- date:
- holding summary:
- how it applies to this case:
- confidence: high | medium | low
"@

New-FileIfMissing -Path (Join-Path $casePath "05_drafts\agent-brief.md") -Content @"
# Agent Brief

Use `Build-AgentPacket.ps1` to regenerate this file from the latest case materials.
"@

New-FileIfMissing -Path (Join-Path $casePath "07_audit\review-checklist.md") -Content @"
# Review Checklist

- Party names and identifiers match source documents.
- Dates are consistent across facts, claims, and attachments.
- Every legal assertion is traceable to one authority note.
- Relief requested is specific, measurable, and legally grounded.
- Unknown or missing facts are explicitly marked `[확인필요]`.
"@

Write-Host "Case workspace ready: $casePath"
