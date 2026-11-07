# 공개 CSV: 열 선택과 해석
코덱스 | 2026-11-04

`evidence_public_48.csv`는 동결 수정 CSV에서 공개 열만 선택한 UTF-8 BOM 파일이다. 48행의 순서와 선택된 모든 셀 값은 원본과 같다. 새 보완 내용을 덮어쓰거나 빈칸을0으로 채우지 않았다. Yext 보충 사례는48행 밖이다.

## 공개 열 허용 목록

`as_of`, `issuer_id`, `ticker`, `question_id`, `domain`, `question`, `population`, `definition_version`, `research_status`, `answerability`, `related_evidence`, `fact`, `company_claim`, `analyst_hypothesis`, `value`, `unit`, `precision`, `numerator`, `denominator`, `exclusions`, `geography`, `segment`, `observation_start`, `observation_end`, `publication_date`, `checked_at`, `source_urls`, `source_excerpt`, `counter_evidence`, `next_check`, `comparable`, `comparable_reason`

공개 공시의 발행사·질문·판정, 관측 집단·기간·정의, 사실·회사 설명·분석 가설, 값·단위·분자·분모·예외, 공개일·확인일, 공식 원문 URL·짧은 인용, 반대 근거·다음 확인 조건·비교 가능성만 포함한다. CIK는 공개 법인 식별자다. 재무제표상 투자·매출 금액과 채택 지표는 기업 공시 사실이며 종목 시세가 아니다. `value`가 비어 있어도 해당 질문의 존재 확인에 따라 직접 답변일 수 있다. 질문별 판단 근거를 함께 읽는다.

## 제외한 원본 열

`direction`, `decision_cutoff`, `source_location`, `document_scope`, `full_document_path`, `full_text_path`, `local_document_path`, `observation_window_note`, `research_group`, `source_id`, `source_ids`

로컬 전문·HTML 경로, 내부 수집 그룹·출처키·작업 범위 메타데이터를 제외했다. `source_location`에는 로컬 캐시 기준 위치가 혼재하므로 공개 열에서 제외하고, 세 카드에는 공시 절·페이지·공개 URL을 직접 적었다. `direction`은 초기 조사와 독립 평가가 다른 대상 명제를 가리킨 사례가 있어 공개 화면의 긍정/부정 배지로 전달하지 않는다. 답변 가능성은 그대로 보존했다.

원문 ZIP·전체 HTML/PDF/TXT·시장 명부 원본·원시 가격·비공개 입력·개인 자료·외부 저장소 다운로드 링크는 첨부하지 않는다. 이 CSV의 열 목록은 연구 파일 설명이며 제품 공용 계약이나 공용 명세 변경이 아니다.

## 동결과 보완

- 수정본 기준: 신규12사·48문항·직접14/유보34. 최초13/35에서 FONR_B1 한정 재판정 후 동결.
- SAP_H1·O_I1의 추가 조사와 종결은 [검증 요약](VALIDATION.md)에 별도 서술한다. 원본 셀을 조용히 고치지 않는다.
- `checked_at`은 기존 연구 확인일이며 이번 PR에서 모든 URL을 다시 열었다는 뜻이 아니다.
- 전체시장 커버리지 미측정, 안전마진 미산출, QGV 운영 독립성 시험 미실행.

표본 집계 재현(저장소 루트, 표준 라이브러리만 사용):

```python
import csv
from collections import Counter
from pathlib import Path
p = Path("implementation/docs/research/company_entry_20261104/evidence_public_48.csv")
with p.open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
assert len(rows) == len({r["question_id"] for r in rows}) == 48
assert len({r["issuer_id"] for r in rows}) == 12
assert Counter(r["answerability"] for r in rows) == {"직접 확인": 14, "판단 유보": 34}
for domain in sorted({r["domain"] for r in rows}):
    print(domain, dict(Counter(r["answerability"] for r in rows if r["domain"] == domain)))
```
