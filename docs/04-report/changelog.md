# Changelog

모든 주요 변경사항이 이 파일에 기록됩니다.

형식은 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)를 따릅니다.

---

## [2026-02-20] - P2/P3 완료

### Added
- **watch_inbox.py**: `run_cowork_chain()` 함수 추출 (테스트 가능한 독립 함수)
- **watch_inbox.py**: `_find_template()` 함수 추가 (템플릿 우선순위 로직: hint > local > global)
- **watch_inbox.py**: CLI 플래그 추가 (`--cowork`, `--template`, `--case-data`)
- **test_watch_inbox.py**: 15개 신규 테스트 (TestFindTemplate 6개 + TestRunCoworkChain 9개)
- **e2e_cowork_chain.py**: CI 호환 E2E 스크립트 (3종 문서 일괄 처리)
- **.github/workflows/e2e.yml**: GitHub Actions CI/CD 워크플로우
  - unit-tests job (131 passed)
  - e2e job (3종 PASS, 14일 artifact 보존)
- **setup.bat**: Windows 원클릭 설치 스크립트
  - Python 확인 → pip install → pytest → E2E 자동 실행
- **templates/sample_rescue_application.md**: 부당해고 구제신청서 마크다운 스펙 (15 토큰)
- **templates/sample_employment_contract.md**: 근로계약서 마크다운 스펙 (12 토큰)
- **templates/sample_wage_complaint.md**: 임금체불 진정서 마크다운 스펙 (13 토큰)
- **templates/tmpl_employment_contract.hwpx**: 근로계약서 HWPX 템플릿 (22 토큰)
- **templates/tmpl_wage_complaint.hwpx**: 임금체불 HWPX 템플릿 (31 토큰)
- **templates/rescue_application_data.example.json**: 부당해고 샘플 데이터
- **templates/employment_contract_data.example.json**: 근로계약서 샘플 데이터
- **templates/wage_complaint_data.example.json**: 임금체불 샘플 데이터
- **docs/04-report/completion-report-p2p3.md**: P2/P3 완료 보고서

### Changed
- **watch_inbox.py**: `InboxHandler.on_created()` 에서 cowork chain 자동 호출 (--cowork 플래그 시)
- **scripts/legal-hub/requirements.txt**: watchdog, docx 의존성 확인

### Fixed
- HWPX 템플릿 우선순위 혼동 (hint > local > global 순서 명확화)
- E2E 스크립트에서 미치환 토큰 검증 로직 추가

### Test Results
- **Unit Tests**: 131 passed (18+14+7+7+10+75)
  - test_render_docx.py: 18 passed
  - test_render_hwpx.py: 14 passed
  - test_prepare_case_data.py: 7 passed
  - test_scaffold_hub.py: 7 passed
  - test_build_matter_pack.py: 10 passed
  - test_watch_inbox.py: 75 passed (기존 60 + 신규 15)
- **E2E Tests**: 3종 PASS
  - E2E-RESCUE (부당해고): 1489B ✅
  - E2E-CONTRACT (근로계약서): 2239B ✅
  - E2E-WAGE (임금체불): 2210B ✅
- **GitHub Actions**: Run #22224540342 (success)
  - Python 3.11.14, ubuntu-latest
  - artifact 14일 보존

### PDCA Status
- **Phase**: Act (완료)
- **Match Rate**: 100% (CLAUDE.md 대비)
- **Iterations**: 1

### Related Commits
- `6f2e2e3` — feat: P3 cowork 체인 연결 (15 테스트 추가, 131 passed)
- `5a374b4` — feat: 3종 문서 템플릿 세트 추가
- `233f6a5` — feat: CI 자동화 + E2E 스크립트 + setup.bat (P2/P3 완료)

---

## [2026-02-19] - 법률 플랫폼 통합 테스트 완료

### Added
- **docs/04-report/e2e-research-docx-test.md**: E2E 리서치 결과 누적 기록
- **docs/04-report/chrome-automation-test-log.md**: /chrome 세션 테스트 로그
- **docs/04-report/legal-research-prompt.md**: 3플랫폼 리서치 프롬프트

### Test Results
- 엘박스: 로그인 OK, 일반검색 9,867건, AI질의 OK
- 빅케이스: 로그인 OK, 검색 3,508건, AI요약 OK
- 슈퍼로이어: 로그인 OK, AI채팅 OK, 판례+서적 인용

### Status
- Process A (/chrome): ✅ Verified
- Process B (Python): ✅ Ready for P2/P3
- Process C (PowerShell): ⏸️ Planned

---

## [2026-02-16] - E2E IRAC 초안 테스트

### Added
- **docs/04-report/e2e-irac-draft.md**: 부당해고 IRAC 분석 초안
- **docs/04-report/e2e-irac-wage-theft.md**: 임금체불 IRAC 분석 초안

### Generated Outputs
- DOCX: e2e-irac-draft.docx (render_docx.py 변환)
- HWPX: e2e-irac-draft.hwpx (render_hwpx.py 변환)

---

## [2026-02-15] - 테스트 모듈 통합 (39 passed → 116 passed)

### Added
- **scripts/legal-hub/test_scaffold_hub.py**: scaffold_hub 테스트 (7개)
- **scripts/legal-hub/test_build_matter_pack.py**: build_matter_pack 테스트 (10개)
- **scripts/legal-hub/test_chrome_log.py**: chrome_log 테스트 (미정)
- **scripts/legal-hub/test_prepare_case_data.py**: 7개 (기존)
- **docs/04-report/test-report-legal-ai-workflow.md**: 통합 테스트 리포트

### Test Summary
- Before: 39 passed (render_docx 18 + render_hwpx 14 + prepare_case_data 7)
- After: 116 passed (+ scaffold_hub 7 + build_matter_pack 10 + watch_inbox 60)
- Next: watch_inbox 신규 테스트 추가 시 131 passed 목표

---

## [2026-02-14] - 한글 HWPX 템플릿 추가

### Added
- **templates/tmpl_rescue_application_sample.hwpx**: 테스트 픽스처 (한글에서 생성 미지원)
- **scripts/legal-hub/test_render_hwpx.py**: HWPX 렌더링 테스트 (14개)

### Notes
- 실제 템플릿은 한글 프로그램에서 직접 생성 필요
- test fixture는 프로그래밍 생성 가능 (한글에서 열림 안 함)

---

## [2026-02-13] - Windows 인코딩 래퍼 추가

### Added
- **watch_inbox.py**: UTF-8 출력 강제 (cp949/cp1252 터미널 대응)
  ```python
  if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") not in ("utf8", "utf16"):
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
  ```

### Status
- Windows 11 + cp949 터미널에서 에러 제거
- emoji 및 한글 출력 정상화

### Related Commit
- `653e364` — feat: Windows 인코딩 래퍼 추가 (P1)

---

## [이전 버전]

### Older Changes
- `01a607c` — docs: 테스트 리포트 정합성 수정
- `817e931` — chore: 샘플 HWPX 템플릿 추가
- `5e85b5b` — test: 미비 모듈 4종 테스트 추가
- `917e031` — fix: CLAUDE.md 빠른참조 CLI 파라미터 오류 수정

---

**Last Updated**: 2026-02-20
**Status**: Active
