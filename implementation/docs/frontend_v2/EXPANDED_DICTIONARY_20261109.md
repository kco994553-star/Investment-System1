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
