# Legal Hub Automation

Local-first automation for closed legal SaaS workflows:

- `scaffold_hub.py`: create a matter workspace
- `build_matter_pack.py`: convert inbox files into authority cards + matter pack index
- `render_docx.py`: render `03_drafts/draft.md` into court-style DOCX

## 1) Install dependencies

```bash
pip install -r scripts/legal-hub/requirements.txt
```

## 2) Create a matter workspace

```bash
python scripts/legal-hub/scaffold_hub.py 2026-ga-1234 --title "Labor dispute"
```

Default root folder is `MATTERS/`.

## 3) Drop platform exports into inbox

Place files under:

```text
MATTERS/2026-ga-1234/00_inbox/
```

Supported inputs: `.txt`, `.md`, `.pdf`, `.docx`, `.hwpx`, `.hwp`

## 4) Build cards + pack

```bash
python scripts/legal-hub/build_matter_pack.py MATTERS/2026-ga-1234
```

Outputs:

- `02_notes/cards/*.md`
- `02_notes/matter-pack.md`

Optional:

```bash
python scripts/legal-hub/build_matter_pack.py MATTERS/2026-ga-1234 --keep-history
```

## 5) Draft and render final DOCX

Write draft in:

```text
MATTERS/2026-ga-1234/03_drafts/draft.md
```

Render:

```bash
python scripts/legal-hub/render_docx.py MATTERS/2026-ga-1234
```

Output:

```text
MATTERS/2026-ga-1234/04_final/final.docx
```

## 6) Watch inbox for real-time card generation

```bash
python scripts/legal-hub/watch_inbox.py MATTERS/2026-ga-1234
```

Watches `00_inbox/` for new file downloads and auto-generates authority cards.
Press `Ctrl+C` to stop.

## 7) Render hwpx from template

```bash
python scripts/legal-hub/render_hwpx.py \
  templates/tmpl_rescue_application.hwpx \
  templates/rescue_application_data.example.json \
  --output MATTERS/2026-ga-1234/04_final/rescue.hwpx
```

Requires a template hwpx created in Hangul with `{{placeholder}}` tokens.

## 8) Generate template test documents (MD + HWPX)

```bash
python scripts/legal-hub/generate_template_test_docs.py \
  --templates templates \
  --output C:/dev/output/labor-automation-template-tests
```

Creates rendered test files for rescue application, employment contract, and wage complaint.
Also generates HWPX outputs for all three document types and a result report.

## Notes

- For scanned PDF, OCR may still be required.
- `.hwp` extraction is best-effort via `hwp5txt` if installed.
- Recommended stable path: DOCX final output first, then convert to HWPX manually if required.
- hwpx templates must be created manually in Hangul (programmatic creation not supported).
