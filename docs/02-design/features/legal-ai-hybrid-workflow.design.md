# Design: Legal AI Hybrid Workflow v2

> **Feature**: legal-ai-hybrid-workflow
> **Created**: 2026-02-20
> **Updated**: 2026-02-20 (v2 — 3-Process 이중 아키텍처)
> **Phase**: Design
> **Status**: Active
> **Plan ref**: `docs/01-plan/features/legal-ai-hybrid-workflow.plan.md`

---

## 1. Design Decision

3개 프로세스를 상황에 따라 선택·조합하는 **이중 아키텍처** 채택:

| Process | 방식 | 사용 시점 |
|---------|------|-----------|
| **A** | Claude Code `/chrome` 실시간 자동화 | 온라인 + /chrome 안정 시 (Primary) |
| **B** | Python watchdog 로컬 파일 허브 | 오프라인 또는 /chrome 불안정 시 |
| **C** | 기존 PowerShell 수동 하이브리드 | 최소 의존성 fallback |

**핵심 원칙**: 어떤 프로세스를 거치든 최종 산출물은 동일한 폴더 구조와 감사 추적 포맷으로 수렴.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Code 세션 (오케스트레이터)                │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │  Process A   │  │  Process B   │  │   Process C        │    │
│  │  /chrome     │  │  watchdog    │  │   PowerShell       │    │
│  │  실시간 수집  │  │  파일 감시    │  │   수동 import      │    │
│  └──────┬───────┘  └──────┬───────┘  └─────────┬──────────┘    │
│         │                 │                     │               │
│         ▼                 ▼                     ▼               │
│  ┌─────────────────────────────────────────────────────┐       │
│  │           Unified Case Workspace                     │       │
│  │  cases/{CASE_ID}/                                    │       │
│  │    ├─ 00_admin/case-meta.yaml                       │       │
│  │    ├─ 01_intake/facts.md                            │       │
│  │    ├─ 02_research/questions.md                      │       │
│  │    ├─ 03_platform_exports/{lbox|superlawyer|bigcase|other}/ │       │
│  │    ├─ 04_authority_notes/authority-notes.md          │       │
│  │    ├─ 05_drafts/{agent-brief.md, draft.md}          │       │
│  │    ├─ 06_final/{*.hwpx, *.docx}                     │       │
│  │    └─ 07_audit/{import-log.csv, review-checklist.md}│       │
│  └─────────────────────────┬───────────────────────────┘       │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────┐       │
│  │           IRAC Analysis Engine                       │       │
│  │  Issue → Rule → Application → Conclusion → Relief   │       │
│  └─────────────────────────┬───────────────────────────┘       │
│                            │                                    │
│                            ▼                                    │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │  hwpx 생성   │  │  DOCX 생성   │                            │
│  │  (XML 렌더링) │  │ (python-docx)│                            │
│  └──────┬───────┘  └──────┬───────┘                            │
│         └────────┬─────────┘                                    │
│                  ▼                                              │
│         06_final/ 저장                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Process A: `/chrome` 실시간 자동화

### 3.1 컴포넌트

```
Claude Code CLI (v2.0.73+)
    ↕ MCP (claude-in-chrome)
Claude in Chrome Extension (v1.0.36+)
    ↕ Native Messaging Host
Google Chrome / Microsoft Edge
    ↕ HTTP (로그인 세션 공유)
엘박스 (lbox.kr) / 슈퍼로이어 (superlawyer.co.kr) / 빅케이스 (bigcase.ai)
```

### 3.2 데이터 흐름

```
[입력] 자연어 명령
  "엘박스에서 '택시기사 부당해고' 판례 5개 검색해서 정리해줘"
      │
      ▼
[Step 1] /chrome → 새 탭 열기 → lbox.kr 접속
      │
      ▼
[Step 2] 검색창 찾기 → 검색어 입력 → 검색 실행
      │  ※ 자연어 기반 네비게이션 (CSS selector 하드코딩 없음)
      │  ※ 페이지 로딩 대기 (동적 렌더링 고려)
      ▼
[Step 3] 결과 목록 읽기 → 구조화된 데이터 추출
      │  - 사건번호, 법원, 선고일, 판시사항
      │  - 상세 페이지 클릭 → 전문 추출 (필요 시)
      ▼
[Step 4] 데이터 → Claude Code 컨텍스트로 반환
      │  ※ 이 시점에서 브라우저 데이터가 AI 컨텍스트에 직접 존재
      ▼
[Step 5] IRAC 분석 (§6 참조)
      │
      ▼
[Step 6] 문서 생성 (§7 참조)
      │
      ▼
[출력] cases/{CASE_ID}/06_final/구제신청서.hwpx
       cases/{CASE_ID}/07_audit/import-log.csv
```

### 3.3 에러 핸들링

| 상황 | 감지 방법 | 대응 |
|------|-----------|------|
| 로그인 페이지 리다이렉트 | Claude가 시각적으로 감지 | 사용자에게 수동 로그인 요청 → 재개 |
| 동적 로딩 미완료 | 콘텐츠 부재 감지 | 3초 대기 후 재시도 (최대 3회) |
| 탭 무응답 | MCP 타임아웃 | 새 탭 생성 후 재시도 |
| 연결 끊김 | "Extension not connected" | `/chrome` 재연결 → 실패 시 Process B fallback |
| CAPTCHA | Claude가 시각적으로 감지 | 사용자에게 수동 처리 요청 |
| 빅케이스 UI 차이 | 플랫폼별 레이아웃 다름 | 자연어 기반 적응 (셀렉터 의존 없음) |

### 3.4 사전 조건 체크 스크립트

```bash
# 세션 시작 시 자동 체크
claude --chrome  # 또는 세션 내 /chrome

# 체크 항목:
# 1. Chrome 확장 프로그램 연결 상태
# 2. lbox.kr 사이트 권한 허용 여부
# 3. 현재 Chrome에서 엘박스 로그인 상태
```

---

## 4. Process B: Python watchdog 로컬 파일 허브

### 4.1 컴포넌트

| 파일 | 역할 | 의존성 |
|------|------|--------|
| `01_setup_matter.py` | 사건 폴더 스캐폴딩 | (없음) |
| `02_watchdog_indexer.py` | `00_inbox/` 감시 → PDF 텍스트 추출 | watchdog, PyMuPDF |
| `03_docx_builder.py` | `05_drafts/draft.md` → 법원 규격 DOCX | python-docx |
| `requirements.txt` | 의존성 선언 | pip |
| `.cursorrules` | AI 에이전트 통제 규칙 | AI 에디터 |

### 4.2 데이터 흐름

```
[입력] 사용자가 엘박스에서 PDF 수동 다운로드
      │
      ▼
[Step 1] 다운로드 파일 → 00_inbox/ 폴더에 저장
      │  (Chrome 다운로드 경로를 00_inbox/로 설정)
      ▼
[Step 2] watchdog 감지 → 1.5초 대기 (파일 저장 완료 대기)
      │
      ▼
[Step 3] PyMuPDF로 PDF 텍스트 추출
      │  메타데이터 추가: [원본 파일명: OOO]
      ▼
[Step 4] 02_notes/{파일명}_근거카드.md 저장
      │  로그: "✅ 판례 텍스트가 근거카드로 추출되었습니다"
      ▼
[Step 5] AI 에디터에서 근거카드 참조 → IRAC 초안 작성
      │  → 05_drafts/draft.md 저장
      ▼
[Step 6] 03_docx_builder.py 실행
      │  마크다운 → 법원 규격 DOCX 렌더링
      ▼
[출력] 06_final/최종서면.docx
```

### 4.3 DOCX 렌더링 규격 (법원/노동위 제출용)

```python
# 03_docx_builder.py 핵심 사양

# 페이지 설정
margins = {
    "top": Cm(4.5),     # 상단 4.5cm
    "bottom": Cm(3.0),  # 하단 3.0cm
    "left": Cm(2.0),    # 좌 2.0cm
    "right": Cm(2.0)    # 우 2.0cm
}

# 기본 폰트
font = {
    "name": "맑은 고딕",
    "size": Pt(12)
}

# 줄간격
paragraph_format = {
    "line_spacing": 1.6  # 160% 배수
}

# 마크다운 → DOCX 매핑
heading_styles = {
    "#":   {"size": Pt(16), "bold": True, "align": "CENTER"},   # H1
    "##":  {"size": Pt(14), "bold": True, "align": "LEFT"},     # H2
    "###": {"size": Pt(13), "bold": True, "align": "LEFT"},     # H3
}
# 본문: 양쪽 정렬(Justify), 들여쓰기 없음
# **bold**: 해당 Run만 굵게
```

### 4.4 .cursorrules (AI 에이전트 통제)

```text
# Role & Persona
대한민국 최고 수준의 15년 차 송무 파트너 변호사/노무사.

# Workflow Rules
1. [RAG 및 환각 방지]: 02_notes/ 근거카드와 01_sources/ 팩트만 기반으로 작성.
   외부 지식 생성(Hallucination) 금지.
2. [출처 강제 표기]: [대법원 2025. x. x. 선고 2024다xxxxx 판결] 양식 필수.
3. [IRAC 논리 구조]: Issue - Rule - Application - Conclusion 엄격 준수.
4. [어조]: 건조하고 논리적인 법률 문어체 (~함이 타당함, ~할 것임).
5. [초안 저장]: 05_drafts/draft.md에 마크다운으로 덮어쓰기 저장.
```

---

## 5. Process C: 기존 PowerShell 수동 하이브리드 (Fallback)

### 5.1 기존 스크립트 (변경 없음)

| 스크립트 | 역할 | 입력 | 출력 |
|----------|------|------|------|
| `New-LegalCase.ps1` | 케이스 폴더 생성 | `-CaseId`, `-Title` | 10개 하위 폴더 + 템플릿 파일 |
| `Import-LegalExports.ps1` | 파일 반입 + 감사 로그 | `-CasePath`, `-SinceHours` | 03_platform_exports/ + import-log.csv |
| `Build-AgentPacket.ps1` | AI 입력 패킷 생성 | `-CasePath` | 05_drafts/agent-brief.md |

### 5.2 Operating SOP (v1 유지)

```
1. New-LegalCase.ps1 → 사건 폴더 생성
2. 엘박스/슈퍼로이어/빅케이스에서 수동 다운로드
3. Import-LegalExports.ps1 → 파일 반입 (SHA-256 해시 기록)
4. authority-notes.md 작성
5. Build-AgentPacket.ps1 → agent-brief.md 생성
6. Claude/Codex/Gemini에 brief 투입 → 초안 생성
7. review-checklist.md 기준 검수 → 06_final/ 저장
```

---

## 6. IRAC Analysis Engine

### 6.1 프롬프트 구조

```markdown
## IRAC 법률 분석 지시

당신은 대한민국 노동법 전문 노무사입니다.
아래 수집된 판례와 사실관계를 기반으로 IRAC 분석을 수행하세요.

### 사실관계
{facts_from_intake}

### 수집된 판례
{collected_precedents}

### 분석 요구사항

**I — Issue (쟁점)**
- 이 사안의 핵심 법률 쟁점을 명확히 정의하세요.

**R — Rule (관련 법리)**
- 적용 가능한 법령 조항을 정확히 인용하세요.
- 관련 판례의 법리를 [대법원 YYYY. M. D. 선고 XXXX 판결] 형식으로 인용하세요.
- 수집된 판례에 없는 내용은 절대 생성하지 마세요.

**A — Application (사안의 포섭)**
- Rule을 본 사안의 사실관계에 구체적으로 적용하세요.
- 확인되지 않은 사실은 [확인필요]로 표기하세요.
- 각 주장에 대해 claim → authority 매핑을 제시하세요.

**C — Conclusion (결론)**
- 최선/최악 시나리오와 불확실성을 포함하세요.
- 구체적 구제 방안(Relief)을 제시하세요.

### 출력 형식
- 법률 문어체 사용 (~함이 타당함, ~할 것임, ~에 이유가 없음)
- 마크다운 형식
```

### 6.2 입력 소스별 차이

| 입력 소스 | Process A | Process B | Process C |
|-----------|-----------|-----------|-----------|
| 사실관계 | 자연어 명령에서 직접 | 01_intake/facts.md | 01_intake/facts.md |
| 판례 데이터 | /chrome으로 실시간 수집 | 02_notes/*_근거카드.md | 03_platform_exports/ + agent-brief.md |
| 컨텍스트 위치 | Claude 세션 메모리 | 로컬 파일 → AI 에디터 | agent-brief.md → 수동 투입 |

### 6.3 품질 가드레일

- **환각 방지**: 수집된 판례에 없는 판례번호/법리 인용 금지
- **출처 강제**: 모든 법리 인용에 `[법원 YYYY. M. D. 선고 XXXX 판결]` 필수
- **불확실성 표기**: 확인 안 된 사실은 `[확인필요]` 어노테이션
- **리스크 분석**: 최선/최악 시나리오 필수 포함

---

## 7. Document Generation

### 7.1 hwpx 생성 (Process A 주력)

hwpx는 ODF 기반 XML 포맷으로, ZIP 아카이브 내에 XML 파일들로 구성.

```
구제신청서.hwpx (ZIP)
├── META-INF/manifest.xml       # 파일 목록
├── Contents/
│   ├── content.hpf             # 문서 설정
│   ├── header.xml              # 헤더 정보
│   └── section0.xml            # 본문 내용
└── settings.xml                # 편집 설정
```

**생성 전략**: 템플릿 방식
1. 빈 hwpx 템플릿을 한글에서 생성하여 `templates/` 폴더에 저장
2. Python/Node.js로 ZIP 열기 → XML 파싱 → 내용 치환 → ZIP 재압축
3. `{{placeholder}}` 토큰을 IRAC 분석 결과로 교체

**템플릿 필요 목록**:
| 문서 종류 | 파일명 | 주요 placeholder |
|-----------|--------|------------------|
| 부당해고 구제신청서 | `tmpl_rescue_application.hwpx` | `{{신청인}}`, `{{피신청인}}`, `{{해고일}}`, `{{청구취지}}`, `{{신청이유_IRAC}}` |
| 준비서면 | `tmpl_brief.hwpx` | `{{사건번호}}`, `{{제출일}}`, `{{본문_IRAC}}` |
| 의견서 | `tmpl_opinion.hwpx` | `{{수신}}`, `{{제목}}`, `{{본문}}` |

### 7.2 DOCX 생성 (Process B 주력)

`python-docx` 기반. 법원/노동위 제출 규격 준수 (§4.3 참조).

**생성 전략**: 마크다운 파싱 방식
1. `05_drafts/draft.md` 읽기
2. 줄 단위 파싱: H1/H2/H3/Bold/일반 텍스트 분류
3. `python-docx`로 스타일 적용하여 DOCX 렌더링
4. `06_final/최종서면.docx` 저장

### 7.3 출력 포맷 선택 로직

```
if (Process A && hwpx 템플릿 존재):
    → hwpx 생성
elif (Process B):
    → DOCX 생성 (python-docx)
elif (사용자 지정):
    → 지정 포맷
else:
    → 마크다운 초안 (05_drafts/draft.md) 저장 후 수동 변환
```

---

## 8. Unified Folder Standard

### 8.1 기존 cases/ 구조 (Process A, C 공용)

```
cases/{CASE_ID}/
├─ 00_admin/
│   └─ case-meta.yaml          # 사건 메타데이터
├─ 01_intake/
│   └─ facts.md                # 사실관계
├─ 02_research/
│   └─ questions.md            # 법률 쟁점 리스트
├─ 03_platform_exports/
│   ├─ lbox/                   # 엘박스 수집 자료
│   ├─ superlawyer/            # 슈퍼로이어 수집 자료
│   └─ other/                  # 기타
├─ 04_authority_notes/
│   └─ authority-notes.md      # 판례 적용 포인트
├─ 05_drafts/
│   ├─ agent-brief.md          # AI 입력 패킷 (Process C)
│   └─ draft.md                # IRAC 초안 (Process A, B)
├─ 06_final/
│   ├─ *.hwpx                  # 최종 hwpx
│   └─ *.docx                  # 최종 DOCX
└─ 07_audit/
    ├─ import-log.csv          # SHA-256 감사 로그
    └─ review-checklist.md     # 사람 검수 체크리스트
```

### 8.2 Process B 전용 확장 (MATTERS/ 구조)

```
MATTERS/{사건명}/
├─ 00_inbox/                   # 다운로드 수집함 (watchdog 감시)
├─ 01_sources/                 # 의뢰인 증거자료
├─ 02_notes/
│   ├─ 사건팩_MatterPack.md    # 사건 전체 요약
│   └─ *_근거카드.md           # 개별 판례 텍스트
├─ 03_drafts/
│   └─ draft.md                # AI 작성 초안
├─ 04_final/
│   └─ 최종서면.docx           # 법원 규격 DOCX
└─ templates/                  # 사용자 정의 양식 (선택)
```

### 8.3 폴더 구조 매핑

| Process B (MATTERS/) | cases/ (기존) | 설명 |
|---------------------|---------------|------|
| `00_inbox/` | `03_platform_exports/` | 플랫폼 원본 파일 |
| `01_sources/` | `01_intake/` | 팩트·증거 자료 |
| `02_notes/` | `04_authority_notes/` | 판례 분석 노트 |
| `03_drafts/` | `05_drafts/` | AI 초안 |
| `04_final/` | `06_final/` | 최종 산출물 |

---

## 9. Operating SOP v2 (통합)

### 9.1 Process A SOP (최우선)

```
1. Claude Code 세션 시작: claude --chrome
2. 사건 폴더 생성 (선택):
   - New-LegalCase.ps1 또는 자연어 "사건 폴더 만들어줘"
3. 자연어 명령 투입:
   "엘박스에서 [검색어] 판례 [N]개 검색해서
    IRAC 분석하고 구제신청서 hwpx로 만들어줘"
4. Claude가 자동 실행:
   a. /chrome → 엘박스 접속 → 검색 → 수집
   b. IRAC 분석 수행
   c. hwpx 생성 → 06_final/ 저장
5. 사용자 검수:
   - hwpx 파일을 한글에서 열어 확인
   - review-checklist.md 기준 검토
   - 수정 필요 시 자연어로 보완 지시
```

### 9.2 Process B SOP (오프라인/fallback)

```
1. python 01_setup_matter.py → 사건 폴더 생성
2. python 02_watchdog_indexer.py 실행 (백그라운드)
3. 엘박스에서 판례 PDF 다운로드 → 00_inbox/
4. watchdog가 자동 감지 → 02_notes/에 근거카드 생성
5. AI 에디터에서 지시:
   "근거카드 기반으로 IRAC 분석해서 초안 써줘"
6. python 03_docx_builder.py → 04_final/최종서면.docx
7. 사용자 검수 후 제출
```

---

## 10. Implementation Order

```
Phase 1 (M0): /chrome 연결 테스트
─────────────────────────────────
  □ Claude Code 버전 확인 (v2.0.73+)
  □ Chrome 확장 설치 확인 (v1.0.36+)
  □ claude --chrome 실행
  □ 엘박스 접근 테스트
  □ 판례 데이터 추출 테스트

Phase 2-A (M1): 판례 검색 자동화
─────────────────────────────────
  □ 워크플로우 A 프로토타입 (검색 → 정리 → 저장)
  □ 엘박스 네비게이션 패턴 확인
  □ 에러 핸들링 (세션 만료, 동적 로딩)

Phase 2-B (M1 병렬): Process B 로컬 허브 구축
─────────────────────────────────
  □ requirements.txt 작성
  □ 01_setup_matter.py 구현
  □ 02_watchdog_indexer.py 구현
  □ 03_docx_builder.py 구현
  □ .cursorrules 작성

Phase 2-C (M2): IRAC + 문서 생성
─────────────────────────────────
  □ IRAC 프롬프트 템플릿 확정
  □ hwpx 템플릿 제작 (구제신청서)
  □ hwpx 렌더링 스크립트 구현
  □ 워크플로우 B 프로토타입 (검색 → IRAC → hwpx)

Phase 3 (M3-M4): 통합 + Cowork
─────────────────────────────────
  □ 케이스 폴더 자동 저장 연동
  □ import-log.csv 감사 추적 통합
  □ Cowork 폴더 감시 설정

Phase 4 (M5): 강의 콘텐츠
─────────────────────────────────
  □ 데모 시나리오 3종 제작
  □ 수강생 원클릭 설치 패키지

Phase 5 (M6): E2E 테스트 + 보고서
─────────────────────────────────
  □ 실제 케이스 1건 전체 파이프라인
  □ 테스트 결과보고서 작성
```

---

## 11. Interface Contracts

### 11.1 Process A → 케이스 폴더 저장 인터페이스

```
# /chrome으로 수집한 판례 데이터를 저장할 때
save_path = f"cases/{case_id}/03_platform_exports/lbox/{timestamp}_{filename}"
log_entry = {
    "imported_at_utc": datetime.utcnow().isoformat(),
    "source_file": "chrome_collected",
    "destination_file": save_path,
    "platform": "lbox",
    "collection_method": "chrome_automation",
    "sha256": compute_sha256(content)
}
# → 07_audit/import-log.csv에 append
```

### 11.2 IRAC 입출력 인터페이스

```
# 입력
irac_input = {
    "facts": str,          # 사실관계 텍스트
    "precedents": [        # 수집된 판례 리스트
        {
            "case_number": str,    # "대법원 2023다12345"
            "court": str,          # "대법원"
            "date": str,           # "2023.5.15"
            "ruling": str,         # 판시사항 전문
            "source": str          # "lbox" | "superlawyer"
        }
    ],
    "issue_hint": str      # 쟁점 힌트 (선택)
}

# 출력
irac_output = {
    "issue": str,          # 쟁점
    "rule": str,           # 관련 법리 + 판례 인용
    "application": str,    # 사안 포섭
    "conclusion": str,     # 결론 + 구제 방안
    "risk_analysis": str,  # 최선/최악 시나리오
    "uncertain_facts": [str]  # [확인필요] 항목 리스트
}
```

### 11.3 hwpx 템플릿 인터페이스

```
# 템플릿 placeholder 규약
placeholders = {
    "{{신청인_성명}}": str,
    "{{신청인_주소}}": str,
    "{{피신청인_상호}}": str,
    "{{피신청인_주소}}": str,
    "{{해고일자}}": str,           # YYYY. M. D.
    "{{청구취지}}": str,
    "{{신청이유_IRAC}}": str,      # IRAC 분석 전문 (마크다운 → XML 변환)
    "{{첨부서류_목록}}": str,
    "{{신청일자}}": str,           # YYYY. M. D.
    "{{노동위원회_명칭}}": str     # "XX지방노동위원회"
}
```

---

## 12. 테스트 설계

### 12.1 단위 테스트

| 테스트 ID | 대상 | 입력 | 기대 출력 | 판정 |
|-----------|------|------|-----------|------|
| UT-01 | /chrome 연결 | `claude --chrome` | 연결 성공 메시지 | Pass/Fail |
| UT-02 | 엘박스 검색 | 검색어 "부당해고" | 결과 목록 ≥ 1건 | Pass/Fail |
| UT-03 | PDF 텍스트 추출 | 판례 PDF 1건 | 텍스트 마크다운 | 텍스트 정확도 |
| UT-04 | IRAC 분석 | 판례 + 사실관계 | 4요소 완비 | 구조 검증 |
| UT-05 | hwpx 렌더링 | 템플릿 + 데이터 | 유효한 hwpx | 한글에서 열림 |
| UT-06 | DOCX 렌더링 | draft.md | 법원 규격 DOCX | 여백/폰트 검증 |
| UT-07 | 감사 로그 | 파일 저장 | import-log.csv 기록 | SHA-256 일치 |

### 12.2 통합 테스트

| 테스트 ID | 시나리오 | 프로세스 | 기대 결과 |
|-----------|----------|----------|-----------|
| IT-01 | 판례 검색 → 마크다운 저장 | A | .md 파일 생성, 판례 5건 포함 |
| IT-02 | 판례 → IRAC → hwpx | A | hwpx 파일, IRAC 4요소, 한글 열림 |
| IT-03 | PDF 다운로드 → 근거카드 → 초안 → DOCX | B | DOCX 파일, 법원 규격, 판례 인용 |
| IT-04 | 전체 파이프라인 (실제 사건) | A+B | 제출 가능한 구제신청서 |

### 12.3 테스트 결과보고서 구조

```markdown
# 테스트 결과보고서: Legal AI Hybrid Workflow

## 1. 테스트 개요
- 테스트 일시:
- 테스트 환경: (OS, Claude Code 버전, Chrome 확장 버전)
- 테스트 대상: Process A / B / C

## 2. 단위 테스트 결과
| ID | 결과 | 비고 |

## 3. 통합 테스트 결과
| ID | 결과 | 소요 시간 | 비고 |

## 4. 성능 지표
| 지표 | 목표 | 실측 | 달성 여부 |

## 5. 발견된 이슈
| # | 심각도 | 설명 | 상태 |

## 6. 결론 및 권고사항
```

---

## 13. Why This Design

| 설계 결정 | 이유 |
|-----------|------|
| 3-Process 이중 아키텍처 | `/chrome` 베타 불안정 대비, 어떤 환경에서도 동작 보장 |
| 자연어 기반 네비게이션 | CSS selector 하드코딩 대비 유지보수 비용 zero |
| 템플릿 기반 hwpx 생성 | XML 직접 생성 대비 안정성·호환성 우수 |
| IRAC 프롬프트 표준화 | 모델 교체에도 일관된 법률 품질 보장 |
| 감사 추적 통합 | 법률 실무에서 증거력 확보 필수 |
| cases/ 폴더 표준 유지 | 기존 PS1 자산과 호환, 마이그레이션 비용 zero |
| Process B 병렬 구축 | /chrome 테스트와 동시 진행 가능, 기다릴 필요 없음 |

---

## 14. Implementation Artifacts (최종 산출물)

| # | 파일 | 프로세스 | 상태 |
|---|------|----------|------|
| 1 | `scripts/legal-workflow/New-LegalCase.ps1` | C | 기존 완료 |
| 2 | `scripts/legal-workflow/Import-LegalExports.ps1` | C | 기존 완료 |
| 3 | `scripts/legal-workflow/Build-AgentPacket.ps1` | C | 기존 완료 |
| 4 | `scripts/legal-hub/01_setup_matter.py` | B | 신규 |
| 5 | `scripts/legal-hub/02_watchdog_indexer.py` | B | 신규 |
| 6 | `scripts/legal-hub/03_docx_builder.py` | B | 신규 |
| 7 | `scripts/legal-hub/requirements.txt` | B | 신규 |
| 8 | `.cursorrules` | B | 신규 |
| 9 | `templates/tmpl_rescue_application.hwpx` | A | 신규 |
| 10 | `templates/irac_prompt.md` | A, B | 신규 |
| 11 | `docs/04-report/test-report-legal-ai-workflow.md` | All | 신규 |
