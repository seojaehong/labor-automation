# CLAUDE.md — labor-automation
# 근로계약서 자동생성 + 법률 AI 하이브리드 워크플로우

## 프로젝트 개요
- **목적**: 근로계약서 자동생성 + 3플랫폼(엘박스/빅케이스/슈퍼로이어) 법률 리서치 자동화
- **아키텍처**: 3-Process (A: /chrome 브라우저, B: Python watchdog, C: PowerShell 폴백)
- **레벨**: Dynamic (PDCA 관리)

## 핵심 행동 규칙
- **TDD 필수**: 새 기능 → 실패 테스트 → 구현 → 통과 → 리팩터
- **Simplicity First**: 최소 코드로 동작하는 해결책 우선
- **Surgical Changes**: 관련 없는 파일 수정 금지
- **법률 정확성**: 판례 인용 형식 `대법원 YYYY. M. D. 선고 {사건번호} 판결` 준수

## 멀티 세션 작업 규칙

### 트랙 분리 원칙
| 트랙 | 담당 범위 | 수정 가능 폴더 |
|------|----------|---------------|
| 코드 트랙 | Python/PowerShell 구현, 테스트, 리팩터링 | `scripts/`, `templates/` |
| 크롬 트랙 | /chrome 브라우저 테스트, 리서치 결과 기록 | `docs/04-report/` |

### 충돌 방지
- 커밋은 **코드 트랙에서만** 실행
- 크롬 트랙은 `docs/04-report/` 파일 수정만 허용
- 동일 파일 동시 수정 금지 — 한쪽이 끝난 후 다른 쪽에서 pull

## 프로젝트 구조
```
labor-automation/
├── scripts/
│   ├── legal-hub/           # Python 핵심 모듈
│   │   ├── scaffold_hub.py  # 사건 폴더 스캐폴딩
│   │   ├── render_docx.py   # MD → DOCX 변환 (테이블/각주 지원)
│   │   ├── render_hwpx.py   # HWPX 템플릿 치환
│   │   ├── build_matter_pack.py  # 사건 자료 팩 빌드
│   │   ├── watch_inbox.py   # 수신함 감시 (watchdog)
│   │   ├── chrome_log.py    # /chrome 세션 감사 로거
│   │   └── test_render_docx.py   # 테스트
│   └── legal-workflow/      # PowerShell 스크립트
│       ├── New-LegalCase.ps1     # 사건 생성
│       └── Import-LegalExports.ps1  # 플랫폼 내보내기 가져오기
├── templates/               # 문서 템플릿
│   ├── *.hwpx               # 한글 서식
│   ├── irac_prompt.md        # IRAC 분석 프롬프트
│   └── README.md             # 플레이스홀더 사전
├── docs/
│   ├── 04-report/           # 테스트 로그, 리서치 결과
│   └── archive/             # 완료된 PDCA 아카이브
├── cases/                   # 사건 데이터 (gitignore)
└── MATTERS/                 # 사건 자료 팩 (gitignore)
```

## 코딩 컨벤션

### Python
- Python 3.11+ 타입 힌트 사용 (`list[str]` not `List[str]`)
- `from __future__ import annotations` 모든 파일 상단
- docstring: 한 줄이면 `"""Single line."""`, 길면 Google style
- 파일 인코딩: `encoding="utf-8"` 명시
- 경로: `pathlib.Path` 사용 (os.path 금지)

### PowerShell
- 동사-명사 형식: `New-LegalCase`, `Import-LegalExports`
- 한글 주석 허용, 파라미터명은 영어
- UTF-8 BOM 인코딩

### 마크다운 (법률 문서)
- 테이블: `| 헤더 | 헤더 |` 형식 (render_docx.py가 DOCX 변환)
- 각주: `[^1]` 참조 + `[^1]: 정의` (문서 말미 주석 섹션으로 변환)
- 판례 인용: `대법원 YYYY. M. D. 선고 {사건번호} 판결`
- 서적 인용: `저자, 『서명』, 출판사(연도), 페이지`
- 플레이스홀더: `{{토큰명}}` 형식 (render_hwpx.py가 치환)

## 테스트 규칙
- 테스트 파일: 동일 폴더에 `test_{module}.py`
- 실행: `python -m pytest scripts/legal-hub/ -v`
- 새 함수 추가 시 반드시 테스트 동반
- render_docx.py 변경 시 기존 18개 테스트 전부 통과 확인

## 커밋 규칙
- 형식: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
- 본문 한국어, 제목 간결하게
- 예: `feat: render_docx.py 테이블/각주 파싱 추가`
- 민감 파일 절대 커밋 금지: `*.xlsx`, `cases/`, `MATTERS/`, `__pycache__/`

## .gitignore 필수 항목
- `__pycache__/`, `*.pyc` — Python 캐시
- `*.xlsx` — 개인정보 포함 가능
- `cases/`, `MATTERS/` — 사건 데이터
- `.pytest_cache/` — 테스트 캐시

## 빠른 참조
```bash
# 테스트 실행
python -m pytest scripts/legal-hub/ -v

# DOCX 생성
python scripts/legal-hub/render_docx.py {사건폴더} --input 03_drafts/draft.md

# 사건 폴더 생성
powershell -File scripts/legal-workflow/New-LegalCase.ps1 -MatterId "CASE-001" -ClientName "홍길동"

# /chrome 세션 로그 기록
python scripts/legal-hub/chrome_log.py {사건폴더} --platform lbox --action search --query "부당해고"
```

## 3플랫폼 연동 참조
- 리서치 프롬프트: `docs/04-report/legal-research-prompt.md`
- 테스트 로그: `docs/04-report/chrome-automation-test-log.md`
- IRAC 결과 예시: `docs/04-report/integrated-research-result.md`
