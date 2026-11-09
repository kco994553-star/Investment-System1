# 확장 발행사 찾기 · 공통 사전 · 산업 매크로 근거 · 선정 정밀도 (2026-11-09)

근거: 오너 2026-11-09 「최신 Codex 인계 수령 및 대기열 4·5번 재개」, Codex #437 6721800433.
가지 `claude/expanded-browse-dictionary`(기준 #522 `f680c719`). 병합·Worker 배포·공개 게시·신규 취득 없음.

## 1. 받은 인계

| Codex | 머리 | 이 가지에서 쓴 것 |
| --- | --- | --- |
| #524 보유 발행사 전달 | `fb80b67bcf9695b21fe1ec9dc7a6bd32af930fc5` | `held-issuer-sharded/1` 계약·합성 2발행사·`verify_shards` |
| #525 공통 사전·매크로 근거 | `731e46827bd548db53bf39464e64ff8e5acbc2f6` | `current_taxonomy()`, `query_industry_evidence`, 합성 7사례 |
| #473 선정 부가 계약 | `02e3d44e9082e3d9a7b1df6e0e68cdb0634e4d95` (처음 `70672bc0`) | `research-selection-details/1`, 합성 7사례(fixture SHA-256 `141ae6d6…`) |

#524·#525는 충돌 없이 합쳤고 Codex 파일은 바꾸지 않았다.
- #473 `70672bc0`은 `validation/vertical_slice.py`가 research 패키지를 import해 저장소 경계 시험이 실패했다. 그래서 한때 되돌렸다(`0319db19`, force push 없음).
- Codex가 도우미를 `validation/selection_details.py`로 옮긴 `02e3d44e`(CI 성공)를 낸 뒤 다시 넣고 합쳤다(`fc35c700`, 병합 `f1c14c14`). #473 파일은 `02e3d44e`와 바이트가 같다.
- 새 fixture는 엔진 소스 경로·결과 해시만 바뀌었고, 선정·순위·비중·입력·설정과 계약 필드는 그대로다.

## 2. 대기열 4번 — 확장 발행사 찾기 (#524)

흐름: 0. 기업 검색 → 공통 분류 비공개 칸 → 「확장 발행사 색인 불러오기」(목록표·색인·커버리지 3회, 5초 간격) → 검색 → 발행사 → 「상세」(조각 1회).
- **Worker** `/kis/classification?part=expanded_manifest|expanded_index|expanded_coverage`, `?part=expanded_detail&shard=<소문자 16진 2자리>`. 파일은 `classification/expanded/`. 2 MiB 상한 그대로, 그 밖의 경로는 받지 않는다. **배포하지 않았다.**
- **기준(신뢰 고리):** 목록표의 `identity.summary.sha256`가 같은 묶음으로 받은 확장 요약 **바이트**의 SHA-256과 같아야 한다. `identity.context`의 평가일·모집단·점수 비교집단·버전·분류·원결과가 그 요약의 `held_financial_subsample`과 같아야 한다. 파일 자체 해시만으로는 받지 않는다.
- **판독(`expanded-issuers.js`):** 색인·커버리지는 목록표 대비 바이트·크기를 확인한다. 정체성·`identity_hash`(Codex digest)를 확인한다. 발행사 중복을 보고, 조각 키 = sha256(issuer_id)[:2]인지 확인하고, 분모 = issuer_count = 모집단 분모인지 확인한다. 상세는 고른 발행사의 조각 하나만 읽는다(읽은 조각은 RAM 재사용). 실패한 상세는 그 발행사만 연결 오류로 표시하고, 색인은 그대로 둔다.
- **표시:** 관측 티커는 상장 증명이나 증권 ID가 아니다. Q 0은 값이고, null은 미산출이다. 공식 Q 관문 입력 연결은 관문 통과가 아니다. 총점·순위는 없다. 비교집단(카탈로그)과 발행사 모집단은 따로 둔다. 가격·기술은 연결 안 됨으로, 사업 설명 원문은 미전달로 표시한다. 커버리지는 범위별 Q/G/V/동시/총점, 95% 목표, 원인(미측정은 미측정)을 보이며, 전체시장은 미측정이다.
- **배치:** `stage_private_held_issuers.py`는 인계 목록표 SHA를 고정하고, Codex `verify_shards`와 배치된 요약을 대조한 뒤 전부 아니면 없음으로 배치한다.

## 3. 대기열 5번 — 공통 사전·산업 매크로 근거 (#525)

- **한 사전:** `web_app/common-taxonomy.js` = Codex `current_taxonomy()` 그대로(`tools/common_taxonomy_main.py --check`). 투자시스템 공통 10섹터, `investment-system-common-10-sector/1`, TELECOMMUNICATIONS = **통신서비스**. `classification.sectorName/industryName`과 섹터 QGV `SECTOR_TEXT`가 여기서 이름을 읽는다(별도 이름표 삭제). 분류 기록의 dictionary·mapping 판과 해시는 바꾸지 않는다(이름은 표시만).
- **산업 → 매크로 근거:** 공통 분류 칸의 「산업 매크로 근거 불러오기」(1회, Worker `?part=industry_macro`).
  - `industry-macro.js`가 `company-industry-macro-query/1`을 읽는다.
  - 고정 null(합계·비중·확률·섹터 수익률), PIT 아님, 공식 결과 불변을 확인한다.
  - 사전이 화면 사전과 같은지, 분류 문맥(평가일·해시·사전·대응 판)이 받은 묶음의 view와 같은지 확인한다.
  - 기업·대응 참조·계열·건수·관측을 확인한다.
- **표시:** UNKNOWN은 미확인과 사유로 둔다. 기존 매크로 현재 조회는 그대로 둔다. 연결도 산업 국면·순환매 확률·신호·가중치가 아니다. 0은 0이고, 가려진 값은 미산출이다. 복수 산업 대응은 나누거나 합치지 않는다.
- **Main 고정 자료:** `tools/industry_macro_main_fixture.py`가 Codex 함수로 기본+7사례 출력을 만든다(`--check`로 대조).

## 4. 선정 반례 (#473)

- 상위 %는 floor(적격 × Decimal(str(p)) / 100)으로 센다. p의 10진 문자열을 BigInt로 정확히 계산하며(`floorPercent`) 소수 자리 반올림을 없앴다.
- 결과: 33.3333334% × 3 = 1, 33.3333333% × 3 = 0. Codex 합성 7사례 7/7 수락.
- 규칙에 맞지 않는 선정 수는 그대로 거부한다.
- `selection_details`가 있으면 결과와 같은 정책·적격·선정·비중인지 검사한다. 다르면 전체를 거부한다.
- 표시: 원래 모집단, 제외 사유(Q 없음·G 없음·선정 한도 밖), 현금(0개 선정이면 미형성·현금 없음), 발행사 미연결·같은 발행사 묶음(통합·상한 없음), 재현 해시(선정·비중 재현이며 QGV·PIT·성과 재현 아님).

## 5. 실자료와 합성 구분

| 항목 | 합성(공개 시험) | 보관 실자료(비공개, 로컬 판독) | 배포·실환경 |
| --- | --- | --- | --- |
| 확장 발행사 | Codex 2발행사 + 시험용 177발행사 생성본 | raw `198acb40` 목록표 `22921530…`: 1,057발행사·255조각, 색인 1,051,217B·최대 조각 141,415B, 요약 고리 OK, 상세 1,057/1,057 수락. 비공개 data `09a3e10`에 배치 | Worker 미배포 → 실환경 없음 |
| 커버리지 | Codex 합성 | 운영 501발행사 Q232·G320, 보유1057 Q494·G670, 카탈로그8004 Q495·G671. V·동시·총점은 모두 0. 95% 목표 476/501·1005/1057·7604/8004 모두 미달. 전체시장 미측정 | 같음 |
| 산업 매크로 | Codex 기본+7사례 | raw `daa8e74` query `cec6178c…`: 504행·연결 0·활성 대응 0·미확인 대응 3(공식 원천 산업 정의·버전·범위·적용 기간 문서 미보유). data `c5d28dc`에 배치 | 같음 |
| 선정 | Codex 7사례 | 없음 | 없음 |

산업 연결 완료나 국면 판정 완료로 표시하지 않는다.

## 6. 남은 것

- Worker 배포(새 part 6개), 병합 — 별도 승인.
- 산업 대응 3계열의 공식 series→industry 정의·버전·범위·유효기간 문서 — 신규 취득이라 실행하지 않음.
- 분류 묶음을 다시 배치하면(`stage_private_classification.py`) `classification/` 전체가 바뀌므로, 확장 전달본·산업 조회도 다시 배치해야 한다(다른 요약 옆에 남지 않게 하는 의도된 동작).

## 7. QGV 커버리지 단계 분리 · 입력 연결 수정 비교 (오너 2026-11-09 2차)

### 7.1 확인한 자료

| 자료 | 위치·ID | 확인한 곳 | 쓰임 |
| --- | --- | --- | --- |
| Codex #527 `HELD_INPUT_REPAIR.md` | `ab585a7c`, `e76d402b` | 전체 | 입력 연결 수정 경계·비교 계약 |
| Codex `retained_coverage.py` | #524 `fb80b67b` | `coverage_scope`·`cause_counts` | 단계 이름·관문·원인 (화면 단계의 근거) |
| Codex `sector_qgv_held_repair.py` | #527 `ab585a7c` | `comparison()` | `sector-qgv-input-repair-comparison/1` |
| Drive「ARGON_04 우선작업계획 … QGV95」 | `1UxICmVrVKHp7gGq-U6It9yL1ONNCnij7LvPfe8z3NLw` (2026-11-02) | 후속과제 B·C | 모집단 구분 원칙만. 옛 수치·상태는 옮기지 않음 |
| Drive EPUB『What Works on Wall Street 4판』 | `1ZmzhcJONp4Wi2UDiMVLg5deBt7fiozaC` | 파일 정보만(본문은 Codex가 14·19·24장 확인) | 책 분류·규칙을 화면 체계로 쓰지 않음 |
| `Sector_QGV_Custom_Factors_Implementation_20261106.md`, `Sector_QGV_Factor_Catalog_20261106.md` | Drive 제목·본문 검색과 저장소 전 가지에서 못 찾음 | Main은 원문을 읽지 못함 | Codex가 오너 첨부본을 읽고 SHA-256과 대조 절을 `e76d402b`에 기록함(구현 §5.1–5.3·§7.1–7.3·§8, 목록 §3–5·§8). 공식·기본값·관문·최소 표본 변경 없음 |

화면의 섹터 이름은 `common-taxonomy.js`(Codex `current_taxonomy()` 그대로)만 쓴다. 책·SIC·GICS·ETF 분류는 같은 체계로 보이지 않는다.

### 7.2 커버리지 단계 (`expanded-issuers.js` `coverageView`)

생산자 `retained-default-coverage/1`의 단계별 수를 순서대로 그대로 보인다. 화면에서 다시 세지 않는다.

| 순서 | 단계 | 생산자 키 |
| --- | --- | --- |
| 1 | 섹터 확인 | `sector` |
| 2 | 회계모형 확인 | `accounting` |
| 3 | 기본 요소 구성요소 선언 있음(유효성·관문 통과 아님) | `required_components_present` |
| 4 | 원지표 1개 이상 / 기본 원지표 전부 | `any_raw` / `all_default_raw` |
| 5 | 요소 점수 1개 이상 / 기본 요소 점수 전부 | `any_factor_scores` / `all_default_factor_scores` |
| 6 | Q 산출 · G 산출 · V 산출 | `Q` · `G` · `V` |
| 7 | Q·G·V 세 축 동시 | `joint` |
| 8 | 관문 판정 (코드 행): 관문 통과 / 관문 판정 불가(UNKNOWN) / V 총점 반영 제외(VALUE_EXCLUDED) | `gate_decisions` |
| 9 | 관문 전 총점 · 최종 총점 | `pre_gate_total` · `total` |
| 10 | 세 축 + 최종 총점 (95% 기준 단계) | `all_axes_and_total` |

- **단위**: 운영504는 코드 행 504와 고유 발행사 501을 두 줄로 나눈다. 보유1057·카탈로그8004는 자기 분모만 쓴다. 섞지 않는다.
- **95% 목표**: 생산자 `target`(stage `all_axes_and_total`)을 그대로 쓴다. 원래 모집단(운영504)만 "원래 모집단", 보유·카탈로그는 "참고"라고 쓴다. 분류 확인 수나 원지표 수는 QGV 계산 완료율로 보이지 않는다.
- **관문**: 생산자의 원인 `gate`는 UNKNOWN과 VALUE_EXCLUDED를 합친 수다. 그래서 결손 원인 목록에서 뺐다. 관문은 판정별 수로만 보인다. VALUE_EXCLUDED는 "V 총점 반영 제외 · 기업 탈락·자료 미수집 아님"이라고 쓴다. 섹터 QGV 화면(`sector-qgv.js` `GATE_TEXT`)도 같은 말로 바꿨다.
- **사유**: 생산자 코드를 낱말로 바꾸기만 한다.
  - 입력 부적격: NOT_APPLICABLE·DOMAIN_INVALID·PERIOD_MISMATCH 등.
  - 표본 부족: PEER_SAMPLE_SMALL.
  - 관문 미확정: GATE_UNKNOWN.
  - 변환 미연결: 상세 입력 결손의 NOT_CONNECTED.
  - 분류·회계모형 대응 미확정: MAPPING_UNRESOLVED.
  - MISSING_INPUT은 생산자가 자료 미보유와 변환 미연결을 나누지 않는다. 그래서 화면도 나누지 않고 그 사실을 적는다. 원인을 추정하지 않는다.
- **겹침**: 원인은 겹친다. 더하지 않는다. 요소별 실패 수(행×요소)는 요소끼리 더하지 않는다. 미측정 원인은 "미측정(확인 n · 미평가 m)"으로 쓴다. 0은 0으로 두고, 빠진 단계는 "전달 안 됨"으로 쓴다.
- **기업 공통 분류 패널**: Q·G만 보이던 운영 집계(#523)에 V·세 축 동시·최종 총점과 고유 발행사 수를 더했다. "분류 확인 수는 QGV 계산 완료율이 아님" 문구도 붙였다. 확장 표본 줄은 분류 단계와 계산 단계로 나눴다.

보관 실자료(raw `198acb40`, 로컬 판독, 수만 보임):

| 모집단 | 섹터 | 회계모형 | 원지표 1+ | 요소 점수 1+ | Q | G | V | 세 축 | 최종 총점 | 95% 필요 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 운영504 발행사 | 454/501 | 422/501 | 498/501 | 357/501 | 232 | 320 | 0 | 0 | 0 | 476 |
| 보유1057 | 929 | 844 | 1054 | 823 | 494 | 670 | 0 | 0 | 0 | 1005 |
| 카탈로그8004 | 935 | 847 | 1059 | 826 | 495 | 671 | 0 | 0 | 0 | 7604 |

운영504 코드 행 기준 관문 판정은 다음과 같다.
- 통과 290
- 판정 불가 93
- V 총점 반영 제외 121

전체시장 분모·커버리지는 미측정이다.

### 7.3 입력 연결 수정 전후 비교 (`input-repair.js`, Codex #527)

- **계약**: `sector-qgv-input-repair-comparison/1`, treatment `INPUT_CONNECTION_REPAIR`.
  - 설정·평가일·모집단·분류·관문이 다르면 생산자가 비교를 쓰지 않는다(`REPAIR_CONFIG_CHANGED` 등).
  - 그래서 화면은 "요소·비중 변경 아님 · 분류 변경 아님 · 설정 변경 아님"으로만 쓴다.
- **신뢰 고리**: 지금 받은 확장 발행사 묶음의 커버리지 범위 하나와 맞아야 받는다. 평가일, `result_identity.input_hash` = `after_input_hash`, 분모가 모두 같아야 한다. 다르면 이 칸만 오류가 되고, 묶음·커버리지·상세는 그대로 둔다.
- **산술 검사**: 생산자 수를 그대로 검사한다.
  - 후 = 전 + 새로 산출 − 사라짐
  - 분모 이하
  - 기존 값 바뀜 ≤ 전 − 사라짐
  - 기본 선택 행 ≤ 전체 행
  - 구조적 표본 부족 = 구성원 < 최소
  - 같은 입력이면 바뀐 것 없음
- **낱말**: "기존 값 바뀜"은 새 원지표가 비교집단에 들어와 상대점수가 달라진 것이다. 실적 개선·전략 성과가 아니다. 성과·전체시장은 미측정이다. 점수·순위·비중은 다시 계산하지 않는다.
- **전달**: Worker `?part=input_repair` → `classification/expanded/input-repair-comparison.json`(2 MiB 그대로, 배포 안 됨).
  - `stage_private_held_issuers.py --input-repair <file> --input-repair-sha256 <pin>`으로 확장 전달본과 함께 통째로 배치한다.
  - 고정 해시와 결과 고리가 다르면 배치하지 않고, 기존 묶음을 둔다.
- **합성 검증**: `tools/input_repair_comparison_fixture.py`(`--check`)가 Codex `preview_qgv`(기본 설정)와 `comparison()`을 Codex 합성 입력에 그대로 돌린다. 5사례:
  - 최소 표본 넘김
  - 상대점수 이동
  - 3행 그룹 구조적 부족
  - 변화 없음
  - 설정 변경 → 생산자 거부
- **실자료**(Codex #437 6739484764, 로컬 판독·비공개 배치, 수만 보임):
  - 인계본: raw `f6c70260` `handoffs/sector-input-repair-20261109`, 인계 목록표 SHA-256 `f0e62656…`(11파일 대조 OK).
  - 새 요약 `5f26868a…`: 분류 패널 수락. 운영 Q 232 · G 320→343 · V·세 축·총점 0.
  - 전달본 목록표 `0a4e82f4…`: 1,057발행사 · 255조각 · 상세 1,057/1,057 수락 · 최대 파일 1,051,585B.
  - 커버리지 G: 운영 343/501 발행사(343/504 코드 행) · 보유 693/1057 · 카탈로그 694/8004. 그 밖의 단계와 관문 판정은 수정 전과 같음.
  - 비교(운영 504, `e86e6ee6…`): 받은 결과와 연결됨. G +23 · 사라짐 0 · 기존 값 바뀜 0 · 구조적 표본 부족 44/108그룹.
  - 비교(카탈로그 8004): 판독은 수락(G 671→694). Worker part가 하나라 배치하지 않고 비공개 인계본에만 둠.
  - 비공개 data `39c4408`에 배치. 분류 다섯 part와 산업 매크로 조회는 바이트 그대로 다시 배치.
  - 95% 목표는 그대로 미달(세 축+총점 0/501).
  - Worker 미배포 → 실환경 없음.

### 7.4 검증

- **node**:
  - `web_app_expanded_issuers_node_test` 7 (단계·단위·관문·사유·변환 미연결)
  - `web_app_input_repair_node_test` 4
  - `web_app_sector_qgv_node_test`
  - reuse 26
- **Worker**: `kis.test.mjs`에 `input_repair` 경로·스키마 추가.
- **Python**:
  - `test_main_generated_classification_fixtures`(+비교 고정본)
  - `test_stage_private_held_issuers` 15
- **브라우저** `web_app_classification_private_browser_test` 1440·390:
  - 단계 순서와 운영504 두 단위
  - 관문 판정 3종 (VALUE_EXCLUDED 낱말, 0은 0)
  - 비교 칸: 키보드로 열기, 다른 결과는 거부하고 묶음 유지, 맞는 결과 표시
  - 저장소 키 불변, 가로 넘침 없음
