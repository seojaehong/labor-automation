# Legal Workflow Toolkit

This toolkit implements a practical workflow for legal drafting when LBOX/SuperLawyer do not provide a public API/MCP endpoint.

## What it solves

- Standardized case folder per matter
- Controlled import of exported files from platform downloads
- Audit log with file hash (SHA-256)
- Reproducible AI packet for Codex / Claude / Gemini drafting

## Quick Start

1. Create a case workspace.

```powershell
pwsh -File scripts/legal-workflow/New-LegalCase.ps1 `
  -CaseId "2026-LA-001" `
  -Title "부당해고 구제신청"
```

2. Export documents from LBOX or SuperLawyer to your downloads folder.

3. Import recent exports into the case workspace.

```powershell
pwsh -File scripts/legal-workflow/Import-LegalExports.ps1 `
  -CasePath "cases/2026-LA-001" `
  -SinceHours 6 `
  -Move
```

4. Build an AI-ready packet.

```powershell
pwsh -File scripts/legal-workflow/Build-AgentPacket.ps1 `
  -CasePath "cases/2026-LA-001" `
  -IncludeDocxPreview
```

5. Send `cases/2026-LA-001/05_drafts/agent-brief.md` to your preferred coding agent.

## Recommended operating model

- LBOX/SuperLawyer: authority search and platform-native drafting aids
- Local toolkit: intake, evidence normalization, audit, final draft assembly
- AI agent (Codex/Claude/Gemini): IRAC drafting, revision, formatting guidance

## Important notes

- `.hwp/.hwpx` files are imported and logged, but text preview extraction is not included.
- Keep `cases/` out of git history (already configured in `.gitignore`).
- Avoid browser-bot automation against legal SaaS unless explicitly authorized by each platform.
