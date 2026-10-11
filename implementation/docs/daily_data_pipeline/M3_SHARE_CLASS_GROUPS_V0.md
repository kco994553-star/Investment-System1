# M3 경제적 동일 종류 합산 — `share_class_groups/v0`

## 사용자 결정 (2026-10-11)

> 여러 주식 종류(SHARE_CLASS_BASIS): 경제적으로 동일한 종류(GOOGL/GOOG 등)는 합산해 순위에 포함, 불명확한 것만 제외.

기기 M3(Universe 시총 순위)에서 같은 발행사의 상장 종류들이 **주당 경제적 권리가 같고 의결권만 다른** 경우, 회사 시총을 종류별로 합산해 **회사 1개로 한 번만** 순위에 넣는다. 그 밖의 `SHARE_CLASS_BASIS`·`BASIS_UNCONFIRMED` 행은 지금처럼 순위에서 제외한다.

## 사용자 결정 (2026-10-11, 비상장 Class B)

> M3: Alphabet의 비상장 Class B는 Class A 가격으로 평가해 합산에 포함한다(1:1 전환 가능, 회사 전체 시총). GOOG 표지 제목 'Capital Stock'이 실데이터로 확인되면 그 정확한 문구만 명시적으로 허용한다. 일반 규칙은 완화하지 않는다.

## 설정 (V0_UNCALIBRATED, 수정 가능)

- 기기: `web_assets/share-class-groups.js`(`ShareClassGroups.CONFIG`), Python 사본: `universe/share_class_groups.py`(`SHARE_CLASS_GROUPS_V0`). 두 값은 테스트로 동일성을 확인한다.
- `config_version: share_class_groups/v0`, `config_status: V0_UNCALIBRATED` — v0 시작값이며 보정된 정책이 아니다.
- 키: SEC CIK + Universe504의 정확한 코드. `cover_class_count`는 공시 표지(cover)에 나와야 하는 종류 수다.
- `unlisted`: 표지 종류 수가 상장 코드 수보다 많은 묶음에만 있다(아니면 null). `{valued_at, conversion_ratio: 1, basis: UNLISTED_CLASS_VALUED_AT_CLASS_A, decision}` — 비상장 종류는 `valued_at` 상장 종류의 가격으로 1:1 평가한다. 전환비율 1 외의 값, 상장 코드가 아닌 `valued_at`, 표지 종류 수와 어긋난 `unlisted`는 검증에서 거부된다.

| group_id | CIK | 코드 | 표지 종류 수 | 비고 |
|---|---|---|---|---|
| alphabet | 0001652044 | NASDAQ:GOOGL + NASDAQ:GOOG | 3 | Class A(1표)·Class C(무의결권). 비상장 Class B(10표, Class A로 1:1 전환)는 `unlisted.valued_at = NASDAQ:GOOGL`로 **GOOGL 가격에 합산** |
| fox | 0001754301 | NASDAQ:FOXA + NASDAQ:FOX | 2 | Class A(무의결권)·Class B(의결권) |
| news_corp | 0001564708 | NASDAQ:NWSA + NASDAQ:NWS | 2 | Class A(무의결권)·Class B(의결권) |

선정 근거: 보관된 공식 SEC `company_tickers_exchange.json`(실험 폴더 사본)으로 Universe504 코드의 CIK를 대조하면, **같은 CIK에 상장 코드가 2개 이상인 경우는 위 3쌍뿐**이다(테스트 `test_every_group_is_a_same_cik_listing_set_in_the_universe`). 전환비율이 1이 아닌 종류(예: BRK.A/BRK.B — Universe에는 BRK.B만 있음)나 BF.B처럼 한 종류만 있는 경우는 넣지 않는다. 이들은 "불명확"으로 계속 제외된다.

Alphabet Class B는 사용자 결정(2026-10-11)에 따라 회사 전체 시총에 포함한다. 주식수는 공개 `sec-universe-shares.json`의 `unlisted_classes.alphabet`(GOOGL 행과 같은 표지 filing)에서 온다.

## 계산 규칙 (Python `prepare_share_class_groups` == JS `PrivateSubset.prepareShareClassGroups`)

회사 R = Σ(해당 종류 공개 레코드의 표지 종류별 주식수 × 그 종류의 기기 시트 가격), 설정의 코드 순서대로 더한다.

모든 조건을 만족해야 `VERIFIED`이고, 하나라도 빠지면 회사 전체가 `NOT_AVAILABLE`이다(**부분 합 금지, 0 대체 금지**):

1. 설정의 모든 코드가 시트 행에 있다. 하나라도 없으면 `SHARE_CLASS_GROUP_INCOMPLETE`.
2. 각 종류: 식별 확인, CIK = 설정 CIK, 공개 레코드 `LIVE` + `SHARE_CLASS_BASIS`(표지 종류별 값, `dei:EntityCommonStockSharesOutstanding`), 시트 가격 양수. 실패하면 `SHARE_CLASS_GROUP_INCOMPLETE` + 원래 사유(`STALE_INPUT`, `BASIS_UNCONFIRMED`, `SHARES_NOT_AVAILABLE`, `PRICE_NOT_AVAILABLE` 등).
3. 근거 일치: 모든 종류가 같은 표지 filing(accn)·같은 측정일·같은 종류 목록이고, 종류 수 = `cover_class_count`, 각 코드의 표지 종류(listing_class_member)가 서로 다르다. 한 종류가 `SINGLE_CLASS_CONFIRMED`이면 설정과 모순이다. 실패하면 `SHARE_CLASS_GROUP_MISMATCH` + `BASIS_UNCONFIRMED`.
4. 비상장 종류(`unlisted`가 있는 묶음, Alphabet): `unlisted_classes` 항목이 `LIVE`이고 classes가 있어야 한다. 항목이 없거나 `NOT_AVAILABLE`/`STALE`이면 `SHARE_CLASS_GROUP_INCOMPLETE` + `UNLISTED_CLASS_SHARES_NOT_AVAILABLE`, 항목의 사유가 `UNLISTED_CLASS_AMBIGUOUS`이거나 accn·측정일·cover 해시가 GOOGL 행과 다르거나, class가 상장 종류와 겹치거나 표지 종류에 없거나 개수(상장+비상장 ≠ `cover_class_count`)가 맞지 않으면 `SHARE_CLASS_GROUP_MISMATCH` + `UNLISTED_CLASS_AMBIGUOUS`. 양수가 아닌 값은 쓰지 않는다(`UNLISTED_CLASS_SHARES_NOT_AVAILABLE`).
   R = (GOOGL 주식수 + Class B 주식수 × 1) × GOOGL 가격 + GOOG 주식수 × GOOG 가격. GOOGL 가격이 없으면 2번 규칙대로 `SHARE_CLASS_GROUP_INCOMPLETE` + `PRICE_NOT_AVAILABLE`.
5. 품질 비교(10% 포함 경계)는 첫 번째 코드(GOOGL·FOXA·NWSA) 행의 Google marketcap과 비교한다. 불일치여도 순위에는 들어가고 "검증 불일치"로 표시한다(단일 종류와 동일).

선정(`select_verified_universe_top_n(..., groups=...)` / `selectVerifiedUniverseTopN(..., {groups})`): `VERIFIED` 묶음은 첫 코드 행에서 한 번만 순위에 들어가고 나머지 종류 행은 누락으로 세지 않는다. `NOT_AVAILABLE` 묶음은 있는 종류 행 모두를 묶음 사유로 누락에 넣는다. 같은 발행사의 다른 상장 행이 묶음 밖에 있으면 모두 `DUPLICATE_ISSUER`. 묶음 객체가 시트 행과 어긋나면 선정 전체가 실패한다.

## 화면

- 순위: `GOOGL+GOOG · R … · 경제적 동일 종류 합산 · v0 · <품질>` + 종류별 주식수(`GOOGL … + GOOG …`) + 비상장 종류 `CommonClassBMember … @ NASDAQ:GOOGL · UNLISTED_CLASS_VALUED_AT_CLASS_A · 비상장 종류는 Class A 가격으로 평가 · 1:1 전환`(영문 `Unlisted class valued at Class A price · 1:1 convertible`). 행 속성 `data-unlisted-basis`.
- 미완성 묶음: 각 종류 행에 사유 · "경제적 동일 종류 합산 · v0" · 구성 코드 · (Alphabet) `UNLISTED_CLASS_VALUED_AT_CLASS_A` 평가 기준 · "모든 종류 필요 · 순위 제외".
- 설정에 없는 다중 종류(예: MMM 합성 예시, BRK.B)는 기존대로 "SEC 표지 클래스 주식수 … · 합산·보정 없음"으로만 표시한다.

## 경계

- 가격·R·순위는 RAM 전용이며 저장·전송하지 않는다. 묶음 결과 객체에는 가격 필드가 없다.
- 공개 `sec-universe-shares.json`에는 가격 없는 최상위 `unlisted_classes`만 추가했다(형식: [SEC_UNIVERSE_SHARDS.md](SEC_UNIVERSE_SHARDS.md)). 레코드 형식은 그대로다.
- 검증: `tools/m3_share_class_groups_reference.py`(합성 21개 벡터: Class B 포함·Class B 결측/부재/모호/다른 filing/상장 종류와 겹침/0·GOOGL 가격 결측 포함) → `tests/fixtures/m3_share_class_groups_reference_v0.json`, JS 재현 `tools/share_class_groups_node_test.js`·`tools/sec_universe_shares_browser_test.js`, Python `tests/test_share_class_groups.py`·`tests/test_sec_universe_shares.py`(생산자·변조 거부 Python/JS 동시). 기존 `m3_public_shares_reference_v1` 결과는 묶음을 켜도 그대로다.

## 미확인 (실데이터)

### GOOG 'Capital Stock' 정확 문구 예외 — 실데이터 확인 대기 (PENDING_REAL_DATA_CONFIRMATION)

- 결정: GOOG 표지 제목이 실데이터로 확인되면 CIK 0001652044·그 정확한 문구(대소문자 일치)만 예외로 허용한다. 일반 제목 규칙(`common stock|ordinary shares`)은 완화하지 않는다.
- 현재 상태: **예외 미추가.** 2026-10-11 저장소 안 보관 실데이터를 찾았으나 Alphabet 표지 제목은 없었다. `data/raw/manifests/xbrl_instance__0001652044__0001652044-24-000118.json`(goog-20240930_htm.xml)·`-24-000079`·`-24-000053`은 메타데이터(URL·sha256·bytes)만 있고 원문 blob(`data/raw/blobs/`)은 보관되지 않았다. `data/raw/cover_xbrl_run_*.json`은 filing 목록·로그만, `reports/gate_evidence/`·`docs/security_map19_owner/`에는 13F/NPORT 표기("ALPHABET INC CLASS A")만 있고 Security12bTitle은 없다. 이 환경에서 sec.gov·Pages 직접 조회는 막혀 있다.
- 그 전까지 GOOG의 제목이 "Class C Capital Stock"이면 GOOG는 `BASIS_UNCONFIRMED`이고 Alphabet은 `SHARE_CLASS_GROUP_INCOMPLETE` + `BASIS_UNCONFIRMED`로 순위 제외된다(테스트 `test_capital_stock_title_stays_basis_unconfirmed_general_rule_not_loosened`). Class B 주식수는 GOOGL 행 기준이라 이와 무관하게 공개된다.
- 확인 방법: 비공개 원본 릴리스(`sec-universe-raw-*`)의 Alphabet cover XML에서 GOOG 문맥의 `dei:Security12bTitle` 원문을 확인한 뒤, 그 파일 경로를 근거로 정확 문구 예외를 추가한다.
- 실제 공개 파일의 각 쌍 상태는 이 작업 환경에서 확인하지 못했다(NOT_AVAILABLE).
