# Chrome 브라우저 자동화 테스트 로그

- **테스트 일시**: 2026-02-20
- **환경**: Windows 11, Claude Code v2.1.47, Chrome Extension
- **테스트 키워드**: "부당해고 근로기준법"

---

## 1. 엘박스 (LBox) - lbox.kr

### 접속 상태
- **로그인**: 자동 (서재홍 / 스탠다드·풀 패키지)
- **URL**: `https://lbox.kr/v2`

### 테스트 결과

#### 1-1. 일반 검색
- **URL 패턴**: `/v2/search/case?query={keyword}&page=1`
- **결과**: 9,867건
- **검색 탭**: 판례, 결정례, 유권해석, 주석·실무서, 법령, 행정규칙, 자치법규, 내규·지침, 논문
- **필터**: 사건유형(민사/형사/행정/가사/특허/기타), 법원(대법원/고등·특허/지방/헌법재판소)
- **정렬**: 관련도순

#### 1-2. AI 질의
- **URL 패턴**: `/v2/ai/chat/{chat_id}`
- **사고 과정 표시**: 법률 문서 검색(3회) → 법령 원문 확인 → 검색 완료 → 판례 검색
- **참조 법조문**: 근로기준법 제23조, 제26조, 제27조, 제28~33조
- **답변 구조**: 요건별 분류 + 판례 링크 인라인 인용
- **참조문서 탭**: 별도 탭으로 참조 문서 제공

#### 1-3. 자동화 가능 요소
| 기능 | 셀렉터 | 자동화 난이도 |
|------|--------|-------------|
| 검색 입력 | `textbox[type="search"]` placeholder="키워드를 입력하세요." | 쉬움 |
| 검색 실행 | Enter 키 또는 submit 버튼 | 쉬움 |
| 탭 전환 | `button "일반 검색"` / `button "AI 질의"` / `button "문서 작성"` | 쉬움 |
| AI 질의 입력 | textarea 클릭 후 type | 쉬움 |
| AI 질의 전송 | 파란 화살표 버튼 (우하단) | 쉬움 |
| 답변 대기 | "엘박스 AI가 답변 중입니다" 텍스트 소멸 대기 | 중간 (20~60초) |
| 답변 추출 | `get_page_text` 또는 `read_page` | 쉬움 |
| 필터 체크박스 | `checkbox` name: civil/criminal/administration 등 | 쉬움 |

#### 1-4. 주요 URL 패턴 (바이브 코딩용)
```
# 일반 검색
https://lbox.kr/v2/search/case?query={encoded_keyword}&page=1

# AI 질의 (채팅방)
https://lbox.kr/v2/ai/chat/{chat_id}

# 개별 판례
https://lbox.kr/v2/case/{법원명}/{사건번호}?q={keyword}
```

---

## 2. 빅케이스 (BigCase) - bigcase.ai

### 접속 상태
- **로그인**: 비로그인 (기본 검색은 가능, 전문판례 열람은 잠금)
- **URL**: `https://bigcase.ai`

### 테스트 결과

#### 2-1. 판례 검색
- **URL 패턴**: `/search/case?q={keyword}&page=1&complete=`
- **결과**: 3,103건
- **검색 탭**: 판례, 법령(NEW), 주해/주석서(NEW), 논문, 결정례, 유권해석(NEW), 행정심판례(NEW), e-book(NEW)
- **필터**: 사건종류(형사/민사/행정/헌법/특허/가사), 법원(대법원 등)
- **하위 필터**: 전문판례, 미리보기 판례, 전체
- **특수 기능**: 쟁점별 판례보기

#### 2-2. 검색 가이드 (자동 표시)
- 일치 검색: `"키워드"` 형식
- 제외어: `-` 붙여서 제외
- 포함 검색: 띄어쓰기로 포함
- 단축어: 자주 사용되는 단축어
- 사건번호: 판례 번호 직접 검색

#### 2-3. 자동화 가능 요소
| 기능 | 셀렉터 | 자동화 난이도 |
|------|--------|-------------|
| 검색 입력 | `textbox[type="text"]` placeholder="키워드를 검색하세요" | 쉬움 |
| 검색 실행 | Enter 키 | 쉬움 |
| 탭 전환 | `link "판례"` / `link "법령"` 등 | 쉬움 |
| 판례 클릭 | 결과 목록 내 link href | 쉬움 |
| 필터 체크박스 | 사건 종류별 checkbox | 쉬움 |

#### 2-4. 제한사항
- 비로그인 시 전문판례 잠금 (자물쇠 아이콘)
- AI 프리뷰/요약은 인증회원 혜택
- 서면으로 검색, 판례 요청은 인증회원 전용

#### 2-5. 주요 URL 패턴 (바이브 코딩용)
```
# 판례 검색
https://bigcase.ai/search/case?q={encoded_keyword}&page=1&complete=

# 법령 검색
https://bigcase.ai/search/statute?q={encoded_keyword}

# 논문 검색
https://bigcase.ai/search/thesis?q={encoded_keyword}
```

---

## 3. 슈퍼로이어 (Super Lawyer) - superlawyer.co.kr

### 접속 상태
- **로그인**: 자동 (서재홍의 워크스페이스, 브라우저 세션 유지)
- **URL**: `https://superlawyer.co.kr/chat`
- **빅케이스와 같은 회사** (법률AI 서비스)

### 테스트 결과

#### 3-1. AI 채팅
- **URL 패턴**: `/chat/{uuid}` (채팅방 자동 생성)
- **응답 단계**:
  1. 요청사항에 필요한 작업을 분석하고 있습니다.
  2. 답변 생성을 위해 데이터베이스를 검색하고 있습니다.
  3. 검색 결과를 분석하여 답변을 생성하고 있습니다.
- **답변 품질**: 법조문 + 판례(대법원 판결 번호) + 법률 서적 인용
- **답변 구조**: 목차형 (1. 요건 → 2. 구제절차 → 3. 효과 → 4. 적용범위)
- **후속 질문 제안**: 답변 하단에 5개 관련 질문 자동 제안

#### 3-2. 주요 기능 메뉴
- **대화** (`/chat`): AI 법률 상담
- **롱폼** (`/longform`): 장문 법률 문서 작성
- **지식베이스** (`/knowledge-based/personal`): 개인 법률 자료 관리

#### 3-3. 자동화 가능 요소
| 기능 | 셀렉터 | 자동화 난이도 |
|------|--------|-------------|
| 채팅 입력 | `textbox` placeholder="요청하실 내용을 입력해 주세요." (ref_23) | 쉬움 |
| 전송 | `button "메시지 전송"` (ref_26) | 쉬움 |
| 답변 대기 | "답변 준비 중" 텍스트 소멸 대기 | 중간 (15~40초) |
| 답변 추출 | `get_page_text` | 쉬움 |
| 답변 복사 | `button "복사"` | 쉬움 |
| 답변 다운로드 | `button "내려받기"` | 쉬움 |
| 새 대화 시작 | `link "새 대화"` 또는 `/chat` 네비게이션 | 쉬움 |
| 법률 데이터 선택 | `button "법률 데이터 선택"` | 쉬움 |
| 문서 업로드 | 첨부 버튼 (ref_24) | 중간 |
| 인용 판례 확인 | `button "답변에 인용된 판례, 법령이 적절한지 확인하기"` | 쉬움 |

#### 3-4. 주요 URL 패턴 (바이브 코딩용)
```
# AI 채팅 (새 대화)
https://superlawyer.co.kr/chat

# AI 채팅 (기존 대화)
https://superlawyer.co.kr/chat/{uuid}

# 롱폼 문서 작성
https://superlawyer.co.kr/longform

# 지식베이스
https://superlawyer.co.kr/knowledge-based/personal
```

---

## 4. 플랫폼 비교 요약

| 항목 | 엘박스 | 빅케이스 | 슈퍼로이어 |
|------|--------|---------|-----------|
| **로그인** | 자동 (세션) | 비로그인 | 자동 (세션) |
| **검색 결과수** | 9,867건 | 3,103건 | AI 답변 |
| **AI 기능** | AI 질의 (판례 기반) | 없음 (AI프리뷰는 인증회원) | AI 채팅 (판례+서적) |
| **응답 시간** | ~40초 | 즉시 | ~30초 |
| **판례 인용** | 인라인 링크 | 결과 목록 | 인라인 링크+서적 |
| **문서 작성** | 문서 작성 탭 | 없음 | 롱폼 기능 |
| **자동화 난이도** | 쉬움 | 쉬움 | 쉬움 |
| **무료 사용** | 유료 (스탠다드) | 부분 무료 | 유료 |

---

## 5. 바이브 코딩 워크플로우 제안

### 5-1. 법률 리서치 자동화 파이프라인
```
[사용자 입력: 키워드/질문]
        │
        ├──→ 엘박스 AI 질의 (법률 분석 + 판례 인용)
        ├──→ 빅케이스 검색 (판례 목록 수집)
        └──→ 슈퍼로이어 채팅 (종합 법률 의견)
        │
        ▼
[결과 병합 → IRAC 분석 → 문서 생성]
```

### 5-2. 자동화 핵심 함수 (구현 필요)
```python
# 1. 엘박스 AI 질의
async def lbox_ai_query(question: str) -> dict:
    # navigate → AI 질의 탭 → 입력 → 전송 → 대기 → 추출
    pass

# 2. 빅케이스 판례 검색
async def bigcase_search(keyword: str) -> list[dict]:
    # navigate → 검색 → 결과 파싱
    pass

# 3. 슈퍼로이어 채팅
async def superlawyer_chat(question: str) -> dict:
    # navigate → 입력 → 전송 → 대기 → 추출
    pass

# 4. 통합 리서치
async def legal_research(topic: str) -> dict:
    results = await asyncio.gather(
        lbox_ai_query(topic),
        bigcase_search(topic),
        superlawyer_chat(topic),
    )
    return merge_results(results)
```

### 5-3. 주의사항
- AI 답변 대기 시간이 20~60초로 길어, polling 방식보다 `wait` + `get_page_text` 조합 권장
- 엘박스/슈퍼로이어는 브라우저 세션 로그인 필수 (Chrome 공유 세션 활용)
- 빅케이스는 비로그인으로도 기본 검색 가능하나, 전문판례는 로그인 필요
- 각 플랫폼 AI의 hallucination 가능성 있으므로 교차 검증 필수
