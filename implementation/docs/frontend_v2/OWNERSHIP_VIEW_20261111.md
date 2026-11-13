# 관계망 골격 — 5.1.1 기업 중심 관계 · 5.1.2 연결 근거 · 기업 상세 관계 줄 (2026-11-11)

오너 지시: 2026-11-11 「Main_QGV_Relationship_Queue」 관계망 항목, 「#530 후속 연결과 필수 CI 보완」 §4.
QGV(#530)와 별도 PR이다. 기반은 Codex #531 `986e02ba`(canonical `ab6a83c3` 위)이고, 계약은 그 PR의 것을 그대로 쓴다.
- `implementation/docs/research/company_ownership/CONTRACT.md` sha e057973c…
- `synthetic.json` sha 4946549b…, 18건

`FUNCTION_HIERARCHY_v1.0`은 바꾸지 않는다. 추가명세 파일(`FUNCTION_HIERARCHY_ADDITIONS.md`)은 이 기반에 없다(다른 Draft 가지에 있음). 그래서 이 문서와 FUNCTION_STATUS에 적는다.

## 1. 판독기 `web_app/ownership-view.js` (IS2.ownershipView)

- **입력**: `company-ownership-view/1` 한 개(가운데 기업 하나). 최상위 칸은 정확히 일치해야 하고, 모르는 칸은 거부한다(원값 `raw_value` 포함).
- **거부하는 것**:
  - 관계 분모·커버리지 주장(`COVERAGE_CLAIMED`), 과거 시점 재현 주장(`PIT_CLAIMED`).
  - 모르는 수집 상태(`COLLECTION_STATE`).
  - 가운데 기업과 맞지 않는 방향(`RELATIVE_DIRECTION`), 가운데를 지나지 않는 관계(`ENTITY`), 같은 관계 ID 두 번(`RELATIONSHIP_ID`).
  - 경로 지분율 계산(`LOOK_THROUGH`), 개수 불일치(`COUNTS`).
  - 수집 전·범위 내 미발견·없음 확인인데 관계가 들어 있음.
  - 0~100 밖이거나 문자열이 아닌 소수(`DECIMAL`).
  - 지분율로 모회사를 만든 표시(`CONTROL_FROM_PERCENT`), 13F 운용 재량이 모회사·자회사로 온 경우(`13F_CAPACITY`).
  - 실체 ID를 가진 언급(`MENTION`), 다른 가운데 기업(`CENTRE_MISMATCH`).
- **목록 다섯 개를 섞지 않는다**: 모회사 / 자회사 / 보유 지분(이 기업이 보유) / 주주(이 기업을 보유) / 운용 재량(13F, 자기 지분 아님).
  - 모회사·자회사는 지분율과 따로 확인된 사실이다. 지분율이 모회사를 만들지 않는다.
  - 소유 방향은 보유자→피투자, 모회사·자회사는 명시된 모회사→자회사. 가운데 기업 기준 OUTGOING / INCOMING은 생산자 값 그대로다.
- **나눠 보이는 것**: 직접 / 간접 / 미확인. 지분율과 의결권은 다른 줄이고, 각자의 분모 기준·주식 종류·기준일을 붙인다. 0%는 관측값이다(보유 아님, 종료 추정 아님).
- **상태 문구 (서로 바꾸지 않음)**:

  | 상태 | 문구 |
  | --- | --- |
  | 수집 전 | 관계 자료 없음 · 수집 전 · 관계가 없다는 뜻이 아님 |
  | 일부 검토 | 확인된 n개 · 전체 목록 미확인 |
  | 범위 내 미발견 | 검토한 범위에서 찾지 못함 · 관계 없음 확인이 아님 |
  | 범위 내 없음 확인 | 검토한 범위에서 관계 없음 확인 · 그 범위 밖은 모름 |
  | 고른 종류 0 | 고른 종류에 해당 없음 · 다른 종류의 관계는 있음 |
  | 갱신 실패 | 마지막 갱신 실패 · 이전에 성공한 자료를 보임 |
  | 충돌 | 자료 충돌 n건 · 값을 고르지 않음 |
  | 재검토 필요 | 재검토 필요 n건 · 조회일 유효성 미확인 |

- **목록에 없는 대상**(해석 안 된 이름): 이름만 보이고 「목록에 없는 대상 · 기업 페이지 없음」을 붙인다. 기업 행이나 페이지를 만들지 않는다.
- **분모·커버리지**: 「전체 관계 수 미상 · 커버리지 계산 안 함」.
- **양쪽에서 같은 관계**: `sameFact`가 같은 relationship_id인지, 방향만 반대인지 대조한다.
- **RAM**: 검사한 값만 보관한다(`ram.put`은 검사 안 된 값을 거부). 가운데 기업의 코드 행으로 찾고, 저장하지 않는다.

## 2. 화면

- **5.1 (메뉴 4.1, `screen-news-live.js`)**: 가운데 기업의 검사된 관계 보기가 RAM에 있으면 「관계 자료 미연결」 대신 관계 블록(`screen-ownership-live.js`)을 그린다. 없으면 지금처럼 「관계 자료 미연결」(REL-SOURCE)이다. 그림은 장식이다.
  - 목록 다섯 개는 각자 `<details>`다. 키보드로 Tab이 요약에 닿고 Enter로 연다.
  - 빈 목록 문구는 「전달된 관계 없음 · 없다는 확인이 아님」이다. 범위 내 없음 확인일 때만 「검토한 범위에서 없음 확인」이다.
  - 상대가 공용 기업 목록에 있으면 기업 화면 링크를 단다. 없으면 「기업 목록에 없음 · 기업 페이지 없음」이다.
- **5.1.2 연결 근거**: 관계 ID(양쪽 기업에서 같은 ID), 근거 ID, 관측일, 검토 시각.
- **기업 화면** 4. 이 기업 소식 아래: 같은 블록의 짧은 판(근거 줄 없음). 소식 줄과 따로 둔다. 보기가 없으면 아무것도 더하지 않는다.
- **트리**: 5.3 관계망 줄과 8.1 트리 5.1.1·5.1.2에 「판독기·화면 연결(합성 · 개발 빌드) · 실자료 전달 전」을 적었다. 상태는 미연결 그대로다.

## 3. 시험

- **node** `web_app_ownership_node_test.js`:
  - 고정 합성 파일의 15개 보기가 모두 읽힌다. 오류 3건은 보기가 없다.
  - 목록 분리, 상태 분리, 거부 15종, RAM을 확인한다.
  - 생산자 합성에 없는 상태는 Main이 만든 반례로 시험했다: 주주(같은 사실을 피투자 쪽에서 읽음), 간접, 13F, 갱신 실패, 범위 내 없음 확인.
- **브라우저** `web_app_ownership_browser_test.js` (1440 · 390 · 200% 확대 = 720 CSS px, 배율 2):
  - 보기가 없을 때와 거부된 보기는 블록을 그리지 않는다.
  - 검사된 보기: 목록 다섯 개, 상태·날짜·분모 문구, 키보드로 열기.
  - 목록 밖 상대는 링크 없음, 지분율 줄, 관계 ID·근거.
  - 수집 전·범위 내 미발견·이름만 있는 대상.
  - 기업 화면 짧은 판: 경로가 바뀌어도 RAM에 있고, 새로고침하면 없다.
  - 저장 없음, 가로 넘침 없음, 외부 요청 없음, 콘솔 오류 없음.
  - 합성 가운데 기업의 코드 행은 시험 사이트 목록에 있는 NASDAQ:NVDA로 바꿨다(시험용 매핑). 상대는 SYN-B / SYN-C 그대로다.

## 4. 아직 아님 · Codex 질의

- **실자료 전달 경로**(인증 Worker part·배치)는 없다. 공개 사이트는 계속 「관계 자료 미연결」이다.
- **Codex 질의** — 생산자 합성에 아래 경우를 추가할 수 있는가:
  1. 같은 관계를 피투자·자회사 쪽에서 본 보기(INCOMING 소유·주주).
  2. INDIRECT.
  3. `last_failure`가 있는 보기.
  4. VERIFIED_ZERO_IN_SCOPE.
  5. 13F 운용 재량 보기.
  6. 수집 상태 값의 전체 목록. 지금 판독기는 5개만 받는다.
- **RIG 가드** (오너 2026-11-12 「최소 변경으로 해결」; **오너 2026-11-13 이 재사용 범위 승인** — 병합·배포 승인은 아님):
  - 규칙: `research/company_ownership.py` 한 모듈만 `investment_system.rig.model`에서 `IdentityRef` · `Node` · `stable_id` 세 이름을 가져올 수 있다.
  - 그 밖의 rig 모듈(adapter · gate · ledger)이나 다른 이름은 그 모듈에도 금지다. 다른 모든 모듈은 지금처럼 rig에 의존할 수 없다.
  - rig 자신이 다른 패키지를 가져오지 않는다는 시험은 그대로다.
  - 새 시험 `test_the_rig_model_exception_is_exactly_one_module_and_three_names`: 예외가 정확히 한 모듈·세 이름인지 고정한다.
  - 가드를 지우거나 건너뛰지 않았다. research 전체를 허용하지 않았다.
  - 승인 범위: `research/company_ownership.py` → `investment_system.rig.model`의 `IdentityRef` · `Node` · `stable_id`. 다른 파일·이름·운영 처리 모듈로 넓히지 않는다. 범위 고정 시험을 유지한다.

## 5. 보관 실자료 (로컬, 수만)

- Codex 원자료 883893e4 `handoffs/company-ownership-20261111`의 `view.json`(sha 44f5a59e…, handoff manifest와 일치).
- 판독기로 읽힌다(거부 없음): 확인된 관계 0개 · 전체 목록 미확인 · 목록에 없는 대상 1건. 목록 다섯 개 모두 0행이다.
- **전달 경로는 아직 없다**: 이 PR의 기반(#531 → canonical ab6a83c3)에는 비공개 인증 층이 없다(`kis-private.js`, Worker `/kis/classification` 없음). 그 층은 #530 사슬에만 있다.
  - 기존 인증·비공개 경계를 재사용하려면 이 화면을 그 사슬 위로 옮겨야 한다(새 가지 또는 병합 뒤 재기반). 오너 결정 사항으로 둔다.
  - 그래서 공개 사이트와 이 개발 빌드는 실자료 관계 보기를 읽지 않는다. 「관계 자료 미연결」 그대로다.

## 6. Codex 소비 사례 인수 (#531 b53b0ec0, 2026-11-12)

- 계약 `CONTRACT.md` sha 4fc9f07c…, `consumer-synthetic.json` sha 213d8ce0…(사례 12건, 생산자 함수로 만듦). 기존 `synthetic.json` 18건은 그대로다.
- **고친 것** (Codex가 직접 Node로 찾은 거부 2건):
  1. `collection_state` 6개 전부를 받는다. 새로 받는 값은 `REVIEWED_SCOPE`다. 문구는 「검토한 범위는 검토 완료 · 그 범위 밖은 모름 · 전체 관계 완결 아님」이다.
  2. `NOT_COLLECTED`(이 기업 자체 검토 전)에서도, 다른 기업의 근거가 이 기업에 대해 말하는 관계(INCOMING)는 받는다.
     - 이 기업이 스스로 말하는 관계(OUTGOING)나 미확정 언급은 여전히 거부한다.
     - 문구: 조사 범위 「이 기업 자체 검토 전 · 관계가 없다는 뜻이 아님」, 근거 확인 「다른 기업 근거로 확인된 관계 n개(이 기업을 향한 관계)」.
- **두 상태를 따로 보인다**: 블록에 「조사 범위 · …」(`data-own-scope`)와 「근거 확인 · …」(`data-own-evidence-state`)가 각자 줄로 있다.
- **갱신 실패 receipt** (`checkReceipt`):
  - 보기와 별도 파일이다. 생산자 계약대로 보기 안의 `collection.last_failure`는 null 그대로다.
  - receipt는 보존된 보기 바이트(정렬 키·간결 JSON + 줄바꿈)의 SHA-256, 보기의 생성 시각과 마지막 성공 시각을 그대로 가리켜야 한다. 시도 시각은 생성 시각보다 뒤여야 한다. 결과는 SUCCESS/FAILED/PARTIAL/PARSE_FAILED 중 하나다.
  - 맞으면 보기 옆에 「마지막 갱신 시도 실패 · 시도 … · 이전에 성공한 자료를 보임(성공 … · 생성 …)」을 보인다. 보기 본문과 원래 시각은 바꾸지 않는다.
  - receipt가 없으면 갱신 상태를 모르는 것이다. 새 수집 성공으로 보지 않는다.
  - RAM에는 검사된 보기와, 그 보기에 묶인 검사된 receipt만 둔다(`ram.put(v, receipt)`).
- **시험**:
  - node: 12건 모두 판독되고, 생산자 보기 바이트 해시가 일치한다.
    - 역방향 보기: 주주 1·모회사 1. INDIRECT: 보유 1(간접). 13F: 운용 재량 1.
    - REVIEWED_SCOPE와 검토 전 + INCOMING은 두 줄로 보인다. 검토 전 + OUTGOING은 거부한다.
    - receipt 3종(실패·일부·해석 실패)을 읽는다. 다른 보기·바뀐 시각·모르는 결과·이른 시도는 거부한다.
  - 브라우저: 검토 전 + INCOMING의 두 줄, REVIEWED_SCOPE, 실패 receipt 줄을 확인한다.
    - 가운데 기업 코드를 시험 목록 기업으로 바꿨기 때문에, receipt의 보존 해시는 바뀐 보기 바이트로 다시 맞췄다(시험용).
- **실자료 전달 경로**는 §5대로 아직 없다. 이 기반에는 비공개 인증 층이 없다.

## 7. 인증 전달 (오너 2026-11-13 「후속 통합과 실자료 전달」 §4, 통합 Draft `claude/qgv-ownership-integration`)

#530 사슬 위에서 #532를 합쳤다(merge 146ddc19). 인증층은 복제하지 않고 기존 비공개 Worker `/kis/classification`·Google 로그인·RAM 규칙을 그대로 쓴다.

- **전달 형식** (Main): 비공개 data 가지 `classification/ownership/`
  - `ownership-index.json` — `company-ownership-delivery/1`: `data_kind`(PRIVATE | SYNTHETIC), `sources`(handoff 경로·handoff-manifest SHA-256), `new_external_requests: 0`, `views[]`(실체 ID, 기업 ID들, dataset_hash, 보기 파일 크기·SHA-256, receipt 크기·SHA-256 또는 null).
  - `views/<실체 ID>.json` — Codex 보기 바이트 그대로(생산자 정규 바이트).
  - `receipts/<실체 ID>.json` — 갱신 시도 receipt(있을 때만, 생산자 다섯 키).
- **배치 도구** `implementation/tools/stage_private_ownership_view.py`: handoff-manifest 고정 SHA, view.json이 목록에 있고 크기·SHA 일치, 스키마, `publication` PRIVATE(합성은 `--synthetic`에서 PUBLIC_APPROVED), 정규 바이트, 중심 실체·기업 ID, 중심·기업 중복 없음, receipt는 배치되는 보기 바이트 SHA·변하지 않은 시각·시도 시각이 뒤인지. 공개 저장소 안 경로 거부. `classification/ownership/` 통째 교체, 실패 시 기존 그대로.
- **Worker part** (배포 안 함): `?part=ownership_index`, `?part=ownership_view&entity=<ID>`(보기 중심 = 요청 실체), `?part=ownership_receipt&entity=<ID>`(정확히 다섯 키). 실체 ID `^[A-Z0-9][A-Z0-9-]{0,31}$`. 2 MiB 한도·소유자 인증 동일.
- **판독** (`ownership-view.js`): `checkDeliveryIndex`, `entryFor(index, code)`, `checkDelivered(index, entry, view, receipt, sha256)`.
  - 보기 바이트가 목록표의 크기·SHA와 다르면 `FILE_MISMATCH`. 중심·기업 ID·dataset이 목록표와 다르면 거부.
  - 목록표에 있는 receipt가 없으면 `RECEIPT_MISSING`, 없는 receipt가 오면 `RECEIPT_UNLISTED`.
  - receipt가 `checkReceipt`를 통과하지 못하면 보기는 그대로 보이고 갱신 줄 없이 「갱신 기록을 쓰지 않음 · 코드 · 보관된 관계 자료만 보임」.
- **화면** (`screen-ownership-live.js` `privateLoader`): 로그인한 오너에게만 기업 화면 관계 칸과 5.1에 「관계 자료 목록 불러오기 (비공개 · 1개 읽기)」 → 목록에 있는 기업이면 「이 기업 관계 불러오기 (2개 읽기 · 갱신 기록은 없으면 없음)」. 로그아웃이면 아무것도 더하지 않는다. 로그아웃하면 목록표와 전달된 보기를 RAM에서 지운다.
  - 상태 문구(모두 「관계가 없다는 뜻이 아님」으로 끝남): 배치 전(404) · 로그인 필요/권한 없음 · 파일 손상 · 목록표와 다른 기업·자료 · 목록에 없는 기업 · 형식 거부.
- **실자료 배치 (비공개 원격)**: Codex 원자료 883893e4 `handoffs/company-ownership-20261111`(handoff-manifest a2a0b820…, view 44f5a59e…, 중심 0000002488 = NASDAQ:AMD)를 도구로 배치, 목록표 d2a335c7…, data 가지 058df8c(원격 push 확인). receipt는 Codex가 실자료로 전달한 것이 없어 배치하지 않았다.
- **실제 소비 경로 대조 (로컬)**: 배치된 목록표 → NASDAQ:AMD 항목 → 보기 바이트 SHA·중심·기업 ID·dataset 일치, 판독 통과(일부 검토 · 확인된 관계 0 · 목록에 없는 대상 1 · 조회 기준일 2017-12-30). 1바이트 손상 → `FILE_MISMATCH`, 목록에 없는 receipt → `RECEIPT_UNLISTED`. NYSE:MMM은 목록에 없음.
- **시험**: Worker(경로·스키마·중심 불일치·다섯 키·404·2 MiB·잘못된 형식 9가지), staging pytest 17, node(목록표·바이트·receipt·거부 15가지), 브라우저 `web_app_ownership_private_browser_test.js`(1440: 로그아웃 무표시, 배치 전, 401, 목록, 손상, 보기+receipt 5초 간격, 5.1 같은 RAM, 목록에 없는 기업, 로그아웃 삭제 · 390/320: 묶이지 않은 receipt 거부·블록 폭·44 px).
- **남은 것**: Worker 배포(별도 승인). 실 receipt는 Codex가 갱신 시도를 실제로 했을 때 생긴다.
