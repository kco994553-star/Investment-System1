# 후속 통합 가지 2026-11-08 (`claude/integration-20261108`)

근거: 오너 2026-11-08 「#519 d3e640bb의 Codex 계약 인수 완료를 반영하라」.
- **기준점:** #519 `d3e640bbc05baec3ba1af7146ce584ba9a7cb2e5`. Codex가 인수했다(#437 6718082277). 이 기준점은 바꾸지 않는다.
- **이 가지에서 따로 관리하는 것:**
  - 새 #516 `4cf2e037`
  - 그것을 기반으로 한 #520 `4c8c9381` → `41f2a25b`(경계 정책판, 오너 2026-11-08 「새 분류 버전 대기를 종료하고 최신 인계본을 연결하라」)
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
| 4 | Codex #520 | `4c8c9381` → `41f2a25b` | 승인된 경계 정책 적용(`dictionary/2` + `map/2`, `boundary_policy`), 정책 메타데이터를 분류 해시에 포함, 보유 SIC 검토 확장·공식 Q 관문 입력 연결, 결손 기간 진단 보존. Codex 파일은 바꾸지 않음 |
| 5 | Main 비공개 전달 | `claude/classification-private-delivery` | 아래 2절 f~h |

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
| f | 판독기 판 짝 `/1`+`/1`·`/2`+`/2`만, `/2` 경계 정책 필수, 섞인 짝 거부. 패널의 판·정책판 줄, 확장 요약의 공식 Q 관문 줄(관측 카탈로그 범위)과 "행 단위 화면 없음" 줄. 스테이징 도구의 통째 교체·실패 시 기존 유지 | `f557ad68` |
| g | 390 폭에서 긴 생산자 코드가 기업 화면을 넓히던 결함 수정(`.cc-wrap`), 패널을 연 상태의 넘침 검사 | `549cf64e` |
| h | 비공개 전달 기록 갱신(`/2` 배치·개수·남은 차이) | `e4cdeeb2` |

#493은 Draft이며, 이 가지에 합친 것은 #493의 병합 승인이 아니다.

## 3. 비공개 자료

- **배치 위치:** 비공개 저장소 `investment-system1-kis-private` `data` @ `7ec77023`
- **출처:** raw `handoff/input-recovery-20261103` @ `6168ce2`의 `handoffs/common-boundary-policy-20261108/delivery-compatible/` 다섯 부분과 확장 표본 요약. 바이트를 바꾸지 않았다. 명세 크기·SHA-256, 판 짝, 정책, 분류 해시·평가일을 확인한 뒤 통째로 바꿨다.
- 앞선 `/1` 완료본(raw @ `6f940b9c`, data @ `054f935e`)은 현재 전달본이 아니다. 판독기는 계속 읽는다.
- 자세한 기록은 [CLASSIFICATION_PRIVATE_DELIVERY](CLASSIFICATION_PRIVATE_DELIVERY.md)에 있다.
- **로컬 대조:** 이 가지의 실제 Worker 처리 코드와 판독기로 개수만 확인했다. 오너 비교 대상과 같다.

  | 범위 | 섹터 | 회계모형 | Q | G | 그 밖 |
  | --- | --- | --- | --- | --- | --- |
  | 운영504 | 456 | 424 | 화면에 없음 | 화면에 없음 | 하위 산업 92, 둘 다 확인 424, 미분류 48 |
  | 확장 보유1057 | 929 | 844 | 494 | 670 | — |
  | 관측 카탈로그8004 | 935 | — | 495 | 671 | 공식 Q 관문 연결 483 |

  - 전체시장 분모·커버리지는 null이다. 범위끼리 더하지 않는다.
  - **남은 차이:**
    - 운영504 Q232·G320은 전달된 다섯 부분에 없다. 섹터 미리보기(약 8.4MB)가 Worker 상한 2MB를 넘는다.
    - 보유1057 범위의 관문 연결 478은 요약에 없다.
    - 둘 다 화면에 보이지 않으며 0으로 채우지 않는다.
- **배포:** Worker는 배포하지 않았다.

## 3-1. `/2` 검증 (Codex 6사례)

- **고정 자료:** `tools/common_classification_policy_main_fixture.py`가 Codex #520 `41f2a25b`의 `boundary-policy-v2.json` 여섯 사례를 Codex 함수로만 돌려 `policy_v2_fixture.json`을 만든다. 쓰인 함수는 `extend_held_classification` → `from_sector_snapshot`(`/2`) → `resolve` → `macro_projection`이다. pytest가 바이트 단위로 대조한다.
- **판독기 시험:** `web_app_classification_policy_node_test.js`
  - 여섯 사례를 통째로 읽고, `recordFor`의 섹터·회계모형이 Codex 기대값과 같다(미확인 회계모형은 GENERAL로 채우지 않음).
  - 구 `/1` 묶음도 읽는다.
  - 다음은 거부하거나 따로 둔다: `/2` view + `/1` 사전, `/1` view + `/2` 사전, `/2` + map/1, 모르는 판, 정책 누락, 정책판 불일치, 책 직접 명시 주장, 다른 해시의 매크로
- **화면:** `web_app_classification_private_browser_test.js` 14건
  - 1440·390: 공개 기본 → 비공개 전달 → 같은 묶음 → 접기
  - 390 `/2` 정책판
  - 404·계약 위반·섞인 짝 거부·`/2` 읽기·403
- 새 생산자 변경과 무관한 완료 인수 시험은 다시 돌리지 않았다.

## 4. 평가일

[SIGNAL_DAY_CONTRACT](SIGNAL_DAY_CONTRACT.md)에 정리했다. Codex 확인은 #437 6718082277이다.

| 대상 | 평가일 |
| --- | --- |
| 새 섹터 결과 | 검증된 `preview.valuation_date` |
| 기존 공식 QGV | `signal_day` null. 분류 날짜로 채우지 않는다 |

`TECH_FILTER_QGV_JOIN.md` §6 첫 행은 Codex가 요청한 대로 한정했다.
