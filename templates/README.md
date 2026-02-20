# Templates

법률문서 생성을 위한 hwpx 템플릿과 데이터 파일.

## hwpx 템플릿 만들기

1. **한글(HWP)** 프로그램에서 구제신청서 양식을 작성합니다.
2. 동적으로 치환할 부분에 `{{placeholder}}` 토큰을 입력합니다.
   - 예: `{{신청인_성명}}`, `{{해고일자}}`, `{{신청이유_IRAC}}`
3. **다른 이름으로 저장 → hwpx 형식**으로 저장합니다.
4. 이 `templates/` 폴더에 배치합니다.

## 문서 유형별 샘플 MD + 데이터 파일

| 문서 유형 | 스펙 MD | 데이터 JSON | 제출처 |
|----------|---------|------------|--------|
| 부당해고 구제신청서 | `sample_rescue_application.md` | `rescue_application_data.example.json` | 지방노동위원회 |
| 근로계약서 | `sample_employment_contract.md` | `employment_contract_data.example.json` | 사내 보관 |
| 임금체불 진정서 | `sample_wage_complaint.md` | `wage_complaint_data.example.json` | 지방고용노동청 |

## 테스트용 HWPX 템플릿

- `tmpl_rescue_application.hwpx`: 부당해고 구제신청서 템플릿
- `tmpl_employment_contract.hwpx`: 근로계약서 테스트 템플릿
- `tmpl_wage_complaint.hwpx`: 임금체불 진정서 테스트 템플릿

## 부당해고 구제신청서 placeholder 토큰

| 토큰 | 설명 | 예시 |
|------|------|------|
| `{{신청인_성명}}` | 신청인 이름 | 홍길동 |
| `{{신청인_주소}}` | 신청인 주소 | 서울특별시 강남구... |
| `{{신청인_연락처}}` | 신청인 연락처 | 010-1234-5678 |
| `{{신청인_직위}}` | 신청인 직위 | 대리 |
| `{{입사일자}}` | 입사 날짜 | 2024. 1. 1. |
| `{{피신청인_상호}}` | 피신청인 회사명 | 주식회사 OO운수 |
| `{{피신청인_대표자}}` | 피신청인 대표자명 | 김OO |
| `{{피신청인_주소}}` | 피신청인 주소 | 서울특별시 강동구... |
| `{{피신청인_업종}}` | 피신청인 업종 | 운수업 |
| `{{상시근로자수}}` | 상시 근로자 수 | 5 |
| `{{해고일자}}` | 해고 날짜 | 2026. 1. 15. |
| `{{청구취지}}` | 청구 취지 전문 | (법률 문장) |
| `{{신청이유_IRAC}}` | IRAC 분석 결과 전문 | (자동 생성) |
| `{{첨부서류_목록}}` | 첨부 서류 리스트 | 1. 근로계약서... |
| `{{신청일자}}` | 신청 날짜 | 2026. 2. 20. |
| `{{노동위원회_명칭}}` | 제출 노동위 이름 | 서울지방노동위원회 |

## 렌더링 실행

```bash
python scripts/legal-hub/render_hwpx.py \
  templates/tmpl_rescue_application.hwpx \
  templates/rescue_application_data.example.json \
  --output cases/CASE_ID/06_final/구제신청서.hwpx
```

## 참고

- hwpx 템플릿은 한글 프로그램에서 직접 만들어야 합니다 (프로그래밍으로 새로 생성 불가).
- DOCX 출력이 필요하면 `render_docx.py`를 사용하세요.
- `rescue_application_data.example.json`을 참고하여 실제 데이터 파일을 만드세요.
