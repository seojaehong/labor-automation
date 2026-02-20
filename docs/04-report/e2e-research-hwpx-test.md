# E2E 테스트 결과: 3플랫폼 리서치 → IRAC → HWPX

> **목적**: 3플랫폼 법률 리서치 → IRAC 마크다운 → HWPX 구제신청서 생성 E2E 파이프라인 검증
> **완료 기준**: (1) prepare_case_data.py IRAC 주입 성공 (2) render_hwpx.py HWPX 생성 (3) Placeholders replaced in 확인 (4) 잔여 토큰 없음

---

## Run #1

| 항목 | 값 |
|------|-----|
| 실행시각 | 2026-02-20 19:27 (KST) |
| 질의 키워드 | 부당해고 구제신청 (요건, 제척기간, 기산점, 행정심판법 유추적용) |
| 실행 환경 | Windows 11, Claude Code v2.1.47, Python 3.13.3 |

### 1. 리서치 결과 (3플랫폼)

> 리서치 원본: [e2e-research-docx-test.md](e2e-research-docx-test.md)

| 플랫폼 | 결과 | 핵심 추출 |
|--------|------|----------|
| 빅케이스 | 성공 | 대법원 96누5926 AI 요약, 전문판례 |
| 엘박스 | 성공 | 5개 섹션 구조화 답변 |
| 슈퍼로이어 | 성공 | 판례+서적 인용, 8개 섹션 |

### 2. IRAC 마크다운 → case_data.merged.json

```
입력1: templates/rescue_application_data.example.json
입력2: docs/04-report/e2e-irac-draft.md
명령:  python scripts/legal-hub/prepare_case_data.py \
         templates/rescue_application_data.example.json \
         docs/04-report/e2e-irac-draft.md \
         -o MATTERS/TEST-E2E-HWPX-001/03_drafts/case_data.merged.json
출력:  Merged JSON: MATTERS/TEST-E2E-HWPX-001/03_drafts/case_data.merged.json
       IRAC length: 2825 chars
```

| 항목 | 결과 |
|------|------|
| 판정 | PASS |
| IRAC 주입 길이 | 2,825 chars |
| 출력 경로 | MATTERS/TEST-E2E-HWPX-001/03_drafts/case_data.merged.json |
| 실패 원인 | - |

### 3. case_data.merged.json → HWPX

```
입력1: templates/tmpl_rescue_application.hwpx
입력2: MATTERS/TEST-E2E-HWPX-001/03_drafts/case_data.merged.json
명령:  python scripts/legal-hub/render_hwpx.py \
         templates/tmpl_rescue_application.hwpx \
         MATTERS/TEST-E2E-HWPX-001/03_drafts/case_data.merged.json \
         --output docs/04-report/e2e-irac-draft.hwpx
출력:  hwpx generated: docs/04-report/e2e-irac-draft.hwpx
       Placeholders replaced in: Contents/section0.xml
```

| 항목 | 결과 |
|------|------|
| 판정 | PASS |
| 출력 파일 | docs/04-report/e2e-irac-draft.hwpx |
| 파일 크기 | 3,448 bytes |
| 치환된 XML | Contents/section0.xml |
| 잔여 플레이스홀더 | 없음 (완전 치환) |
| 실패 원인 | - |

### 4. 치환 값 검증

| 플레이스홀더 | 기대값 | 포함 여부 |
|-------------|-------|----------|
| {{신청인_성명}} | 홍길동 | PASS |
| {{피신청인_상호}} | 주식회사 OO운수 | PASS |
| {{해고일자}} | 2026. 1. 15. | PASS |
| {{신청이유_IRAC}} | 부당해고 구제신청의 요건 (IRAC 전문) | PASS |

### 5. 파이프라인 요약

```
3플랫폼 리서치 결과
        ↓
 e2e-irac-draft.md  (IRAC 마크다운, 테이블+각주, 2,825 chars)
        ↓  prepare_case_data.py
 case_data.merged.json  (신청인 정보 + 신청이유_IRAC 삽입)
        ↓  render_hwpx.py
 e2e-irac-draft.hwpx  (3,448 bytes, Placeholders replaced in: Contents/section0.xml)
```

**E2E 판정: PASS**

---

## 산출물 경로

| 파일 | 경로 | 크기 |
|------|------|------|
| 병합 JSON | MATTERS/TEST-E2E-HWPX-001/03_drafts/case_data.merged.json | - |
| HWPX 출력 | docs/04-report/e2e-irac-draft.hwpx | 3,448 bytes |
| HWPX 템플릿 | templates/tmpl_rescue_application.hwpx | 1,171 bytes |
| IRAC 소스 | docs/04-report/e2e-irac-draft.md | - |
