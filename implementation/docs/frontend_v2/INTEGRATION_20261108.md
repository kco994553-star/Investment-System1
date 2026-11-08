# 후속 통합 가지 2026-11-08 (`claude/integration-20261108`)

근거: 오너 2026-11-08 「#519 d3e640bb의 Codex 계약 인수 완료를 반영하라」.
- **기준점:** #519 `d3e640bbc05baec3ba1af7146ce584ba9a7cb2e5`. Codex가 인수했다(#437 6718082277). 이 기준점은 바꾸지 않는다.
- **이 가지에서 따로 관리하는 것:**
  - 새 #516 `4cf2e037`
  - 그것을 기반으로 한 #520 `4c8c9381`
  - 그 위의 Main 비공개 전달·평가일 연결
- #516은 #519에 `5b0ec88a`까지만 들어 있다. `4cf2e037`의 변경은 이 가지에만 있다. 그래서 #516을 "전부 통합됨"으로 닫지 않는다.

이 문서와 가지는 병합·워크플로 적용·배포 승인이 아니다.

## 1. 합친 순서

| 순서 | 무엇 | 머리 | 내용 |
| --- | --- | --- | --- |
| 0 | #519 (기준점) | `d3e640bb` | Codex 인수 완료 |
| 1 | Codex #516 | `5b0ec88a` → `4cf2e037` | 보관 사업 근거 연결, 섹터·회계모형·산업 독립 상태(`records.py`·`sector_qgv_classification_review.py`·`HELD_REVIEW.md`) |
| 2 | Codex #520 | `4c8c9381` | 확장 보유 발행사 표본 진단(`expanded_held_classification.py`·`EXPANDED_HELD.md`). 운영504와 별도 모집단 |
| 3 | Main 비공개 전달 | `claude/classification-private-delivery` | 아래 2절 |

- #516·#520은 충돌 없이 합쳐졌다. Codex 파일은 바꾸지 않았다.
- 3번(Main 가지) 병합 충돌은 2건이었다.
  - `sector-qgv.js` 내보내기 목록: 양쪽 이름을 다 두었다.
  - `FUNCTION_STATUS.md` 갱신 줄: #518 이름의 줄을 두고 #493의 11/04 줄을 더했다.

## 2. Main 비공개 전달 가지의 구성

| 순서 | 무엇 | 머리 |
| --- | --- | --- |
| a | 공통 분류 공급자·호출부(#519 안에 이미 있음) | `05d69ffb` |
| b | #493 비공개 층(오너 인증 Worker `/kis/*`, 비공개 펼치기) 병합 | `89dd60c9`(#493 `2a104798`) |
| c | 공통 분류 보관 묶음의 비공개 전달, 회계모형 독립 상태, 근거 참조 상한, `/2` 평가일 문구 | `8fbce3ff` |
| d | 운영504와 확장 표본의 분리, 새 섹터 결과 평가일 = 검증된 `preview.valuation_date`, 공식 QGV `signal_day` null 유지 | `5263196d` |
| e | 화면 원본 규칙(0 채움 금지) 맞춤 | `e8425dd5` |

#493은 Draft이며, 이 가지에 합친 것은 #493의 병합 승인이 아니다.

## 3. 비공개 자료

- **배치 위치:** 비공개 저장소 `investment-system1-kis-private` `data` @ `054f935e`
- **출처:** raw @ `6f940b9c`의 운영504 완료본 다섯 부분과 확장 표본 요약. 바이트를 바꾸지 않았다.
- 자세한 기록은 [CLASSIFICATION_PRIVATE_DELIVERY](CLASSIFICATION_PRIVATE_DELIVERY.md)에 있다.
- **로컬 대조:** 실제 Worker 처리 코드와 판독기로 개수만 확인했다. Codex 수치와 같다.
  - 운영504: 섹터 416, 회계모형 407, 하위 산업 92, 미분류 88
  - 확장 표본: 관측 카탈로그 발행사 8,004, 보유 재무 1,057, 섹터 815, Q 470, G 633, 전체시장 분모 null
- **배포:** Worker는 배포하지 않았다.

## 4. 평가일

[SIGNAL_DAY_CONTRACT](SIGNAL_DAY_CONTRACT.md)에 정리했다. Codex 확인은 #437 6718082277이다.

| 대상 | 평가일 |
| --- | --- |
| 새 섹터 결과 | 검증된 `preview.valuation_date` |
| 기존 공식 QGV | `signal_day` null. 분류 날짜로 채우지 않는다 |

`TECH_FILTER_QGV_JOIN.md` §6 첫 행은 Codex가 요청한 대로 한정했다.
