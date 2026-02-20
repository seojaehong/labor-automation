# 실운영 테스트 결과: watch_inbox.py 폴더 감시 → 자동 카드 생성

> **목적**: MATTERS/{사건}/00_inbox/ 에 파일 투입 시 02_notes/cards/ 카드 자동 생성 및 matter-pack.md 갱신 검증
> **완료 기준**: (1) 카드 파일 생성 (2) matter-pack.md 갱신 (3) 처리 시간 기록

---

## Run #1

| 항목 | 값 |
|------|-----|
| 실행시각 | 2026-02-20 19:29 (KST) |
| 실행 환경 | Windows 11, Python 3.13.3, PYTHONUTF8=1 |
| 사건 폴더 | MATTERS/TEST-WATCH-001 |

### 1. 사전 준비 — scaffold_hub.py

```
python scripts/legal-hub/scaffold_hub.py TEST-WATCH-001 --root MATTERS --title "watch ops test"
```

| 항목 | 결과 |
|------|------|
| 폴더 생성 | MATTERS/TEST-WATCH-001/ (7개 폴더) |
| 판정 | PASS |

### 2. 감시 프로세스 시작

```
PYTHONUTF8=1 python scripts/legal-hub/watch_inbox.py MATTERS/TEST-WATCH-001 &
```

| 항목 | 결과 |
|------|------|
| 감시 경로 | MATTERS/TEST-WATCH-001/00_inbox |
| 지원 확장자 | .docx, .hwp, .hwpx, .md, .pdf, .txt |
| 시작 시각 | 19:29:18 KST |
| 판정 | PASS (PYTHONUTF8=1 필요, cp949 환경에서 이모지 인코딩 오류 방지) |

> **주의**: Windows cp949 환경에서 실행 시 `PYTHONUTF8=1` 필수.
> 운영 스크립트 호출부에서 `env PYTHONUTF8=1` 추가 권장.

### 3. 파일 투입 (트리거)

```
cp docs/04-report/e2e-irac-draft.md MATTERS/TEST-WATCH-001/00_inbox/sample_irac.md
```

| 항목 | 값 |
|------|-----|
| 트리거 시각 | 2026-02-20 19:29:20 KST |
| 감지 파일명 | sample_irac.md |
| 파일 크기 | 2,825 chars |

### 4. 카드 자동 생성 결과

| 항목 | 결과 |
|------|------|
| 카드 생성 경로 | MATTERS/TEST-WATCH-001/02_notes/cards/sample_irac.md |
| matter-pack.md 생성 | MATTERS/TEST-WATCH-001/02_notes/matter-pack.md |
| matter-pack 생성 시각 (UTC) | 2026-02-20T10:29:22+00:00 |
| 처리 시간 | 약 2초 (SETTLE_SECONDS=1.5 + 빌드) |
| 생성 카드 수 | 1 |
| 판정 | PASS |

### 5. 카드 내용 검증

#### matter-pack.md 인덱스

| 항목 | 값 |
|------|-----|
| cards_count | 1 |
| source_file | 00_inbox/sample_irac.md |
| chars | 2,825 |
| 추출 판례 | 96누5926, 2011헌마233, 2019구합521, 2022누59006, 2007두16875, 2014누6297 (6건) |
| 추출 법원 | 대법원, 고등법원, 행정법원, 헌법재판소, 중앙노동위원회, 지방노동위원회 |

### 6. 발견된 주의사항

| 번호 | 항목 | 내용 | 조치 |
|------|------|------|------|
| 1 | Windows 인코딩 | cp949 환경에서 이모지 print 시 UnicodeEncodeError | 실행 시 `PYTHONUTF8=1` 필수 |
| 2 | matter-pack 위치 | 02_notes/matter-pack.md (루트 아님) | 정상 (build_matter_pack.py 설계) |

---

## 파이프라인 요약

```
watch_inbox.py 시작 (00_inbox 감시)
        ↓
sample_irac.md 투입 (19:29:20)
        ↓  1.5s settle
build_matter_pack.py 호출 (19:29:21)
        ↓
02_notes/cards/sample_irac.md 생성  ✅
02_notes/matter-pack.md 생성        ✅  (cards_count=1, 판례 6건 추출)
처리 완료 (19:29:22, 약 2초)
```

**E2E 판정: PASS**
