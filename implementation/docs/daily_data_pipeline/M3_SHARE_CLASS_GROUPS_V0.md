# M3 경제적 동일 종류 합산 — `share_class_groups/v0`

## 사용자 결정 (2026-10-11)

> 여러 주식 종류(SHARE_CLASS_BASIS): 경제적으로 동일한 종류(GOOGL/GOOG 등)는 합산해 순위에 포함, 불명확한 것만 제외.

기기 M3(Universe 시총 순위)에서 같은 발행사의 상장 종류들이 **주당 경제적 권리가 같고 의결권만 다른** 경우, 회사 시총을 종류별로 합산해 **회사 1개로 한 번만** 순위에 넣는다. 그 밖의 `SHARE_CLASS_BASIS`·`BASIS_UNCONFIRMED` 행은 지금처럼 순위에서 제외한다.

## 설정 (V0_UNCALIBRATED, 수정 가능)

- 기기: `web_assets/share-class-groups.js`(`ShareClassGroups.CONFIG`), Python 사본: `universe/share_class_groups.py`(`SHARE_CLASS_GROUPS_V0`). 두 값은 테스트로 동일성을 확인한다.
- `config_version: share_class_groups/v0`, `config_status: V0_UNCALIBRATED` — v0 시작값이며 보정된 정책이 아니다.
- 키: SEC CIK + Universe504의 정확한 코드. `cover_class_count`는 공시 표지(cover)에 나와야 하는 종류 수다.

| group_id | CIK | 코드 | 표지 종류 수 | 비고 |
|---|---|---|---|---|
| alphabet | 0001652044 | NASDAQ:GOOGL + NASDAQ:GOOG | 3 | Class A(1표)·Class C(무의결권). 비상장 Class B(10표)는 Universe 코드·기기 가격이 없어 **합산하지 않고** 화면에 "비상장 표지 클래스 미포함: 1"로 표시 |
| fox | 0001754301 | NASDAQ:FOXA + NASDAQ:FOX | 2 | Class A(무의결권)·Class B(의결권) |
| news_corp | 0001564708 | NASDAQ:NWSA + NASDAQ:NWS | 2 | Class A(무의결권)·Class B(의결권) |

선정 근거: 보관된 공식 SEC `company_tickers_exchange.json`(실험 폴더 사본)으로 Universe504 코드의 CIK를 대조하면, **같은 CIK에 상장 코드가 2개 이상인 경우는 위 3쌍뿐**이다(테스트 `test_every_group_is_a_same_cik_listing_set_in_the_universe`). 전환비율이 1이 아닌 종류(예: BRK.A/BRK.B — Universe에는 BRK.B만 있음)나 BF.B처럼 한 종류만 있는 경우는 넣지 않는다. 이들은 "불명확"으로 계속 제외된다.

Alphabet Class B 미포함은 S&P 지수처럼 상장 종류만 시총에 넣는 방식과 같다. 비상장 종류까지 포함할지는 사용자 확인 대상이다(공개 파일에 Class B 주식수가 없으므로 포함하려면 공개 JSON 변경이 필요).

## 계산 규칙 (Python `prepare_share_class_groups` == JS `PrivateSubset.prepareShareClassGroups`)

회사 R = Σ(해당 종류 공개 레코드의 표지 종류별 주식수 × 그 종류의 기기 시트 가격), 설정의 코드 순서대로 더한다.

모든 조건을 만족해야 `VERIFIED`이고, 하나라도 빠지면 회사 전체가 `NOT_AVAILABLE`이다(**부분 합 금지, 0 대체 금지**):

1. 설정의 모든 코드가 시트 행에 있다. 하나라도 없으면 `SHARE_CLASS_GROUP_INCOMPLETE`.
2. 각 종류: 식별 확인, CIK = 설정 CIK, 공개 레코드 `LIVE` + `SHARE_CLASS_BASIS`(표지 종류별 값, `dei:EntityCommonStockSharesOutstanding`), 시트 가격 양수. 실패하면 `SHARE_CLASS_GROUP_INCOMPLETE` + 원래 사유(`STALE_INPUT`, `BASIS_UNCONFIRMED`, `SHARES_NOT_AVAILABLE`, `PRICE_NOT_AVAILABLE` 등).
3. 근거 일치: 모든 종류가 같은 표지 filing(accn)·같은 측정일·같은 종류 목록이고, 종류 수 = `cover_class_count`, 각 코드의 표지 종류(listing_class_member)가 서로 다르다. 한 종류가 `SINGLE_CLASS_CONFIRMED`이면 설정과 모순이다. 실패하면 `SHARE_CLASS_GROUP_MISMATCH` + `BASIS_UNCONFIRMED`.
4. 품질 비교(10% 포함 경계)는 첫 번째 코드(GOOGL·FOXA·NWSA) 행의 Google marketcap과 비교한다. 불일치여도 순위에는 들어가고 "검증 불일치"로 표시한다(단일 종류와 동일).

선정(`select_verified_universe_top_n(..., groups=...)` / `selectVerifiedUniverseTopN(..., {groups})`): `VERIFIED` 묶음은 첫 코드 행에서 한 번만 순위에 들어가고 나머지 종류 행은 누락으로 세지 않는다. `NOT_AVAILABLE` 묶음은 있는 종류 행 모두를 묶음 사유로 누락에 넣는다. 같은 발행사의 다른 상장 행이 묶음 밖에 있으면 모두 `DUPLICATE_ISSUER`. 묶음 객체가 시트 행과 어긋나면 선정 전체가 실패한다.

## 화면

- 순위: `GOOGL+GOOG · R … · 경제적 동일 종류 합산 · v0 · <품질>` + 종류별 주식수(`GOOGL … + GOOG …`)와 비상장 표지 종류 수.
- 미완성 묶음: 각 종류 행에 사유 · "경제적 동일 종류 합산 · v0" · 구성 코드 · "모든 종류 필요 · 순위 제외".
- 설정에 없는 다중 종류(예: MMM 합성 예시, BRK.B)는 기존대로 "SEC 표지 클래스 주식수 … · 합산·보정 없음"으로만 표시한다.

## 경계

- 가격·R·순위는 RAM 전용이며 저장·전송하지 않는다. 묶음 결과 객체에는 가격 필드가 없다.
- 공개 `sec-universe-shares.json` 형식·생성은 바꾸지 않았다(기존 레코드의 `basis_evidence.class_members`·`listing_class_member`만 사용).
- 검증: `tools/m3_share_class_groups_reference.py`(합성 14개 벡터) → `tests/fixtures/m3_share_class_groups_reference_v0.json`, JS 재현 `tools/share_class_groups_node_test.js`·`tools/sec_universe_shares_browser_test.js`, Python `tests/test_share_class_groups.py`. 기존 `m3_public_shares_reference_v1` 결과는 묶음을 켜도 그대로다.

## 미확인 (실데이터)

- 실제 표지 XBRL에서 GOOG의 Security12bTitle이 "Class C Capital Stock"이면 현재 어댑터(`sec_m3_adapter._cover`, "common stock|ordinary shares" 제목 요구)가 GOOG를 `BASIS_UNCONFIRMED`로 남길 수 있다. 그 경우 Alphabet은 사유(`SHARE_CLASS_GROUP_INCOMPLETE` + `BASIS_UNCONFIRMED`)와 함께 순위 제외된다. 실제 공개 파일의 각 쌍 상태는 이 작업 환경에서 확인하지 못했다(NOT_AVAILABLE).
