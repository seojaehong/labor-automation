# Phase 4 강의 데모 런북 (Demo Runbook)

> **대상**: 강사/데모 진행자
> **목적**: 수업 시간 내 3개 시나리오를 막힘 없이 실연
> **소요 시간**: 시나리오당 약 5~8분
> **검증 상태**: 2026-02-20 E2E PASS (모든 시나리오)

---

## 시작 전 체크 (2분)

```
[ ] Chrome 브라우저 열림
[ ] 엘박스 / 빅케이스 / 슈퍼로이어 로그인 상태 확인
[ ] Claude Code 실행 중 (터미널)
[ ] 저장소 최신 상태: git pull
[ ] Python 환경 확인: python --version  (3.11+ 필요)
[ ] 의존성 확인: pip show python-docx watchdog
```

---

## 시나리오 A: 판례 검색 → 리서치 정리 MD

**목표**: 브라우저 자동화로 3플랫폼을 검색해 구조화된 마크다운 생성

### 단계

**1. /chrome 연결 확인**
```
Claude Code 대화창에 입력:
"tabs_context_mcp로 현재 열린 탭을 확인해줘"
```

**2. 리서치 실행**
```
Claude Code 대화창에 입력:
"엘박스에서 '부당해고 구제신청 제척기간'을 검색하고
 판례 5건의 핵심 판시사항을 정리해줘"
```

**3. 결과 저장**
```bash
# Claude가 생성한 마크다운을 다음 경로에 저장:
cases/{사건ID}/00_inbox/research_result.md
```

**완료 기준**: `.md` 파일에 판례번호, 판시사항, 출처 플랫폼 기록

---

## 시나리오 B: IRAC → DOCX

**목표**: IRAC 마크다운(테이블+각주 포함)을 Word 문서로 변환

### 단계

**1. IRAC 마크다운 준비**
```
cases/{사건ID}/03_drafts/draft.md 에 IRAC 내용 작성
(테이블, 각주 포함)
```

**2. DOCX 생성 실행**
```bash
python scripts/legal-hub/render_docx.py cases/{사건ID} \
  --input 03_drafts/draft.md
```

**3. 결과 확인**
```
cases/{사건ID}/04_final/ 에 .docx 생성됨
```

**완료 기준**:
- `.docx` 파일 생성
- Word에서 열었을 때 테이블/각주 정상 표시

**데모용 예시 파일**: `docs/04-report/e2e-irac-draft.md` (E2E 검증 완료)

---

## 시나리오 C: IRAC → HWPX (구제신청서)

**목표**: IRAC 분석 결과를 한글(hwp) 구제신청서 서식에 자동 삽입

### 단계

**1. 데이터 JSON 준비** (신청인 정보 입력)
```bash
# 예시 파일 복사 후 편집
cp templates/rescue_application_data.example.json \
   cases/{사건ID}/03_drafts/case_data.json
# 신청인 정보 수정: 성명, 주소, 해고일자 등
```

**2. IRAC 주입**
```bash
python scripts/legal-hub/prepare_case_data.py \
  cases/{사건ID}/03_drafts/case_data.json \
  cases/{사건ID}/03_drafts/draft.md \
  -o cases/{사건ID}/03_drafts/case_data.merged.json
```

**3. HWPX 생성**
```bash
python scripts/legal-hub/render_hwpx.py \
  templates/tmpl_rescue_application.hwpx \
  cases/{사건ID}/03_drafts/case_data.merged.json \
  --output cases/{사건ID}/04_final/rescue_application.hwpx
```

**4. 결과 확인**
- `cases/{사건ID}/04_final/rescue_application.hwpx` 생성
- 터미널에 `Placeholders replaced in: Contents/section0.xml` 출력 확인

**완료 기준**:
- HWPX 파일 생성
- `Placeholders replaced in:` 메시지 확인
- 한글(HWP) 프로그램에서 정상 열림

**데모용 예시 파일**: `docs/04-report/e2e-irac-draft.hwpx` (E2E 검증 완료)

---

## 공통 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| UnicodeEncodeError (이모지) | Windows cp949 | `PYTHONUTF8=1 python ...` |
| Template not found | 경로 오류 | 저장소 루트에서 실행 확인 |
| Placeholders not replaced | 토큰명 불일치 | templates/README.md 플레이스홀더 사전 참조 |
| /chrome 응답 없음 | 확장 프로그램 미연결 | Chrome 재시작 후 확장 재활성화 |

---

## 데모 순서 권장

```
시나리오 A (판례 검색, ~8분)
    ↓
시나리오 B (IRAC→DOCX, ~3분)
    ↓
시나리오 C (IRAC→HWPX, ~3분)
```

총 소요: **약 15분**
