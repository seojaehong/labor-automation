# Phase 4 FAQ

> **대상**: 수강생 / 실습 중 막히는 경우
> **업데이트**: 2026-02-20

---

## /chrome 관련

**Q. `/chrome`이 안 된다 / 탭이 보이지 않는다**

Chrome 브라우저가 실행 중인지 확인.
Claude Code에서 아래 명령으로 연결 테스트:
```
"tabs_context_mcp를 호출해서 현재 열린 탭 목록을 보여줘"
```
탭 목록이 보이면 연결 성공. 안 보이면:
1. Chrome 재시작
2. Chrome Extension 비활성화 → 재활성화
3. Claude Code 재시작

---

**Q. WSL에서 `/chrome`이 안 된다**

WSL은 공식 미지원. 네이티브 Windows 터미널에서 Claude Code 실행.

---

**Q. 슈퍼로이어에 로그인이 풀렸다**

슈퍼로이어는 세션 만료가 빈번. Chrome에서 수동 로그인 후 진행.
비밀번호 자동 입력은 보안상 불가.

---

**Q. 빅케이스 첫 검색 시 "검색 가이드" 팝업이 뜬다**

팝업의 "확인" 버튼 클릭 후 검색 진행.
또는 Claude Code에:
```
"검색 가이드 팝업의 확인 버튼을 클릭해줘"
```

---

## Python / 실행 관련

**Q. `UnicodeEncodeError: 'cp949' codec can't encode ...` 오류**

Windows cp949 터미널에서 이모지 출력 시 발생.
```bash
PYTHONUTF8=1 python scripts/legal-hub/watch_inbox.py MATTERS/{사건ID}
```
모든 Python 실행 앞에 `PYTHONUTF8=1` 추가.

---

**Q. `Template not found` 오류**

저장소 루트(`labor-automation/`)에서 실행하고 있는지 확인:
```bash
pwd  # /c/dev/neuro-coach/labor-automation 이어야 함
```

---

**Q. `Placeholders replaced in:` 출력이 안 된다 (Warning: No placeholders)**

HWPX 템플릿 파일과 JSON 데이터의 토큰명이 불일치.
`templates/README.md` 플레이스홀더 사전과 JSON 키를 비교.
예시: JSON에 `신청인_성명`, 템플릿에 `{{신청인_성명}}` — 공백/오타 확인.

---

**Q. `pytest` 결과가 39 passed가 아니다**

현재 기대 통과 수: **39개**.
실패한 테스트 이름을 확인:
```bash
python -m pytest scripts/legal-hub/ -v
```
`FAILED` 라인에 표시된 파일명과 오류 메시지를 강사에게 공유.

---

## 문서 생성 관련

**Q. DOCX를 Word에서 열었더니 테이블이 깨진다**

`python-docx` 1.1.0 이상 필요:
```bash
pip install --upgrade python-docx
```

---

**Q. HWPX를 한글(HWP)에서 열 수 없다**

강의용 템플릿(`tmpl_rescue_application.hwpx`)은 최소 구조의 시연용.
실무 배포 시에는 실제 한글 프로그램에서 서식 파일을 내보내 사용.

---

**Q. watch_inbox.py가 파일을 감지하지 못한다**

1. 지원 확장자 확인: `.txt .md .pdf .docx .hwpx .hwp`
2. 파일이 완전히 복사된 후 감지 (SETTLE_SECONDS=1.5초 대기)
3. 파일을 복사/이동했는지 확인 (이미 있던 파일은 감지 안됨)

---

## 계정 / 플랫폼 관련

**Q. 엘박스 AI 질의가 없다 / 탭이 보이지 않는다**

스탠다드 플랜 이상에서 AI 질의 기능 제공.
무료 계정은 일반 검색만 가능.

---

**Q. 빅케이스 전문 판례가 안 열린다**

Plus 플랜 이상에서 전문 판례 열람 가능.

---

## 기타

**Q. 실습 중 사건 데이터가 외부에 노출될까 걱정된다**

`cases/`, `MATTERS/` 폴더는 `.gitignore`에 등록되어 있어 Git에 올라가지 않음.
실습 후 해당 폴더 삭제 가능.

---

**Q. 오류가 해결이 안된다**

다음 정보를 강사에게 전달:
1. 실행한 명령어 전체
2. 오류 메시지 전체 (`Traceback` 포함)
3. `python --version` 결과
4. 운영체제 (Windows/macOS/Linux)
