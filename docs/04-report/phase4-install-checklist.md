# Phase 4 설치 체크리스트 (Install Checklist)

> **대상**: 수강생 / 신규 사용자
> **목적**: 실습 환경 세팅을 빠짐없이 완료
> **검증 상태**: 2026-02-20 Windows 11 + Python 3.13.3 PASS

---

## 1단계: 기본 환경

```
[ ] Python 3.11 이상 설치
    확인: python --version
    다운로드: https://python.org

[ ] Git 설치
    확인: git --version
```

---

## 2단계: 저장소 클론

```bash
git clone {저장소URL}
cd labor-automation
```

---

## 3단계: Python 의존성

```bash
pip install python-docx watchdog pypdf PyMuPDF
```

**설치 확인**:
```bash
python -c "import docx, watchdog, pypdf, fitz; print('OK')"
```

---

## 4단계: Claude Code 설치

```bash
npm install -g @anthropic/claude-code
# 또는: npx @anthropic/claude-code
```

**버전 확인** (최소 v2.0.73):
```bash
claude --version
```

---

## 5단계: Chrome Extension 설치

1. Chrome 브라우저 열기
2. `chrome://extensions` → 개발자 모드 ON
3. Anthropic Claude Browser Extension 설치
   (Chrome Web Store 검색: "Claude for Chrome")
4. 버전 확인: v1.0.36 이상

> **주의**: Microsoft Edge도 지원됨. WSL 환경은 지원 안됨.

---

## 6단계: 3플랫폼 계정 확인

| 플랫폼 | URL | 필요 플랜 |
|--------|-----|----------|
| 엘박스 | lbox.kr | 스탠다드 이상 |
| 빅케이스 | bigcase.ai | Plus 이상 |
| 슈퍼로이어 | superlawyer.co.kr | 워크스페이스 |

각 플랫폼에 미리 로그인해 세션 유지 상태 확인.

---

## 7단계: 동작 확인 (테스트 실행)

```bash
python -m pytest scripts/legal-hub/ -v
```

**기대 결과**: `39 passed`

---

## 8단계: E2E 스모크 테스트

```bash
# 사건 폴더 생성
python scripts/legal-hub/scaffold_hub.py TEST-SETUP --root MATTERS

# HWPX 생성 (템플릿 → 출력)
python scripts/legal-hub/prepare_case_data.py \
  templates/rescue_application_data.example.json \
  docs/04-report/e2e-irac-draft.md \
  -o MATTERS/TEST-SETUP/03_drafts/merged.json

python scripts/legal-hub/render_hwpx.py \
  templates/tmpl_rescue_application.hwpx \
  MATTERS/TEST-SETUP/03_drafts/merged.json \
  --output MATTERS/TEST-SETUP/04_final/test.hwpx
```

**기대 출력**:
```
hwpx generated: MATTERS/TEST-SETUP/04_final/test.hwpx
Placeholders replaced in: Contents/section0.xml
```

---

## 환경별 주의사항

| 환경 | 주의사항 |
|------|----------|
| Windows (cp949) | `PYTHONUTF8=1 python ...` 으로 실행 |
| Windows WSL | /chrome 연결 불가 — 네이티브 Windows 사용 |
| macOS | 기본 UTF-8, 별도 설정 불필요 |

---

## 설치 완료 기준

```
[ ] python -m pytest → 39 passed
[ ] E2E 스모크 테스트 → Placeholders replaced in 확인
[ ] Claude Code + Chrome Extension 연결 확인
[ ] 3플랫폼 로그인 상태 유지 확인
```
