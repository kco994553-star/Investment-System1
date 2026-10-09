# 공개 가격·파생값 경계 감사

기준일: **2026-10-09 UTC**. 저장소: `kco994553-star/Investment-System1`. 읽기 기준 canonical: **`3877f9a1eab3d511a58bcb7c49c1a833965737d3`**. #89·#90 뒤에 반영된 #88도 이 기준에 포함한다. 이 문서는 기준 커밋의 파일과 정적 사용 경로를 감사한 **문서 PR / 병합 대기** 산출물이다.

**정리와 Git 이력 변경은 실행하지 않았다.** 기존 파일의 삭제·이동·내용 교체, src·tests·tools·web_assets 수정, 공급자 호출·수집기·빌드·테스트 실행, Worker 배포, 다른 PR 병합, force push, ruleset·`AUTONOMY_MODE` 변경은 없다. 기존 26E 파일에는 사용자가 요청한 KRX 키 등록 보고만 append-only로 추가한다. Secret·토큰 값과 실제 가격·수익률·시총·순위·V 값은 이 감사 문서에 옮기지 않는다.

## 1. 판정 기준

[26E GSQ-007](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md#L177-L222)과 [GSQ-008](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md#L224-L248)이 기준이다. 주가 원자료와 그에 기초한 수익률·가격 결합 QGV/V·시가총액·시총 순위 등은 공개 저장소·공개 JSON·Pages·Actions 로그/아티팩트에 저장·게시하지 않는다. 공급자가 Yahoo·Tiingo·Stooq·KRX이거나 자료가 공식 공개 자료라는 이유만으로 이 경계의 예외가 되지 않는다.

공개 SEC·DART 재무 사실과 본인 전용 가격 경로는 구분한다. 주식수·공시 식별·계정·재무 원자료, 가격 없는 계약·스키마·소스 코드, 실제 가격과 무관함이 입증된 합성 fixture·사용자 고정 TARGET은 유지 후보가 될 수 있다. 실제 N-PORT 시장평가액·주당 가격이나 가격으로 정해진 Frozen 순위는 공개 공시에서 왔어도 가격/파생값으로 다룬다. `DEMO`, `SYNTHETIC`, `REFERENCE`, `FROZEN_VERIFIED`라는 이름만으로 실제 입력의 출처를 덮지 않는다.

| 분류 | 의미 |
| --- | --- |
| 유지 가능 | 파일에 금지 대상 실값이 없거나, 합성·가격 없는 공개 재무/식별·사용자 고정 입력이라는 근거가 있다. 연결된 다른 파일·외부 원문·향후 출력까지 무조건 허용하는 판정은 아니다. |
| 정리 필요 | 실제 가격/가격 기반 파생값이 저장돼 있거나, 이를 공개 출력·캐시·아티팩트·로그로 보내는 현행 경로가 있다. 데이터(DATA)와 출력 경로(ROUTE)를 구분한다. 이번에는 정리하지 않는다. |
| 판단 보류 | 실제/합성 출처, 원문 fragment의 의미, 파생 관계 또는 공개 포함 범위를 현재 근거만으로 확정할 수 없다. 확인되지 않은 내용을 0·합성·공개 허용으로 간주하지 않는다. |

`유지 가능`은 해당 파일의 **가격 경계 판정**이다. 공급자의 전체 약관, 문서 저작권·재배포권, 모델 유효성, PIT, 운영 승인 또는 완전한 데이터 품질을 재판정한 결과가 아니다. 정책 문장·가격 키 이름·빈 값·개수/소요시간·해시·원문 URL·가격을 담지 않은 manifest 자체는 실제 가격과 구분한다.

## 2. 조사 범위와 방법

Git tree의 **추적 파일 8,626개 / 84,106,743 bytes**를 분모로 고정했다. 크기는 해당 Git blob의 실제 bytes이며 압축 파일은 압축 상태 크기다. 디렉터리·실행 중 생성물·Git 이력의 과거 tree는 이 분모에 넣지 않는다. Git tree와 checkout이 일치하는 별도 읽기 사본을 사용했다.

전체 경로와 UTF-8 내용에서 공급자·가격·OHLC·close·quote·시총/market value·return·V/QGV·순위 등의 후보를 검색했다. gzip은 해제해 내용만 읽고 docx는 XML을 읽었다. JSON은 키 구조·source/provenance·소비 경로를 함께 확인했다. 이미지/PDF는 연결된 생성·원문 출처와 화면 의미를 별도 검토했다. 실행 결과를 새로 만들거나 공급자의 원문을 다시 가져오지 않았다.

첫 검색 후보 **4,246개**, 확대 검색의 추가 후보 **55개**, 별도 바이너리 확인 대상 **43개**를 점검했다. 이 검색 수는 실제 가격 포함 수가 아니다. 후보 밖에서도 parser·출력 경로·fixture 및 사람이 확인한 위험 항목을 보완했다. 가격 경계와 무관한 파일은 목록에서 제외하되 전체 tree 대조의 범위와 후보 제외 이유를 남긴다.

현재 Pages 포함 여부는 **기준 커밋의 builder → bundle → 정적 asset 복사 → workflow 업로드 경로**를 따라 판단했다. `포함`은 원 파일을 통째로 복사한다는 뜻과 원 파일의 일부 파생 데이터가 `data.json`으로 들어간다는 뜻을 구분한다. `미포함` 파일도 공개 저장소에 추적돼 있으면 공개 가격 저장 금지의 적용 대상이다. 배포 사이트를 새로 빌드하거나 현재 HTTP 응답을 다운로드한 결과가 아니다.

Actions는 추적 workflow/도구의 캐시·stdout·업로드·commit 설정을 정적으로 확인했다. 과거/현재 모든 실행 로그·캐시·아티팩트 본문을 열어 본 전수 감사는 아니므로, 구성상 경로를 확인한 것을 특정 실행의 실제 유출로 단정하지 않는다. canonical에 없는 raw blob의 존재·내용도 manifest만으로 확정하지 않는다.

## 3. 분류 집계

상세 목록은 **4,354파일 / 81,052,856 bytes**다. 검색 후보 합집합 4,344개에 정적 경로/파일 판독으로 확인한 추가 10개(정리 6·보류 2·유지 2)를 더했다. 각 실제 경로를 한 번만 센다.

| 분류 | 파일 수 | 합계 bytes |
| --- | ---: | ---: |
| 유지 가능 | **4,133** | 63,786,494 |
| 정리 필요 | **170** | 13,642,457 |
| 판단 보류 | **51** | 3,623,905 |
| 합계 | **4,354** | 81,052,856 |

나머지 **4,272파일**은 전체 파일 대조에서 가격 경계와 무관한 빈 표식·가격 없는 재무/식별 provenance·스키마/소스/문서·metadata로 확인돼 상세 목록에서 제외했다. 이 잔여 수는 확대 검색 전 `keyword_nonmatch` 수가 아니다. 전체 tree의 분류는 유지 가능 8,405 / 정리 필요 170 / 판단 보류 51이며, 위 표와 최종 보고의 분류별 개수는 **상세 목록 분모**를 사용한다. 진행률이나 운영 무유출 PASS로 해석하지 않는다.

## 4. 우선 검토할 정리 항목

| 우선 항목 | 확인한 파일/경로와 값의 종류 | 공개 경로·근거 | 후속 선택지 |
| --- | --- | --- | --- |
| Frozen Top500와 현재 Pages projection | `implementation/reports/gate_evidence/official_snapshot_2024-06-30.json`, `official_snapshot_2024-09-30.json`, `official_snapshot_2024-12-31.json`의 실제 `members[].mcap/rank`, `cutoff_mcap` | 세 source 파일은 공개 Git tree에 저장돼 있다. 기본 Pages 경로는 2024-12-31 source에서 시총 금액만 제거하고 순위·company market_cap_rank·배열 순서를 유지한다. 아래 정적 source chain을 확인했으며 실제 배포 응답은 조회하지 않았다. | source와 증거의 보존 범위를 정하고 공개 projection의 금지 파생값 처리·소비자/해시/회귀 영향부터 별도 설계. Protected Frozen을 임의 교체/삭제하지 않음. |
| Pages/일반 export와 검증 artifact ROUTE | `implementation/tools/build_pages_cockpit.py`, `pages_artifact_guard.py`, `export_web_bundle.py`, fixture builders, `implementation/src/investment_system/product/web_mvp.py`, `web_assets/app.js`, 관련 workflow | 가격/시총 금액 일부 차단과 exact hash pins는 남은 실제 가격 기반 rank의 허용 여부를 해결하지 않는다. 일반 export/fixture는 실제 Frozen source를 상속하며 일부 Actions evidence는 전체 bundle variant를 저장하도록 구성돼 있다. | 완전 합성 fixture base, 공개 projection/guard의 경계, artifact·오류 출력 범위 정리. 코드 본문 자체에 실제 가격을 저장했다는 판정과 구분. |
| raw Tiingo 종가 비교 | `implementation/data/raw/tiingo_run_*.json` 중 **34파일** | 실제 `calibration[].tiingo_close/yahoo_close`와 가격 기반 `rel_diff`. 현재 Pages 직접 copy는 없지만 공개 저장소에 남아 있고 c21 metadata commit/raw cache/artifact 경로에도 포함될 수 있다. | 합성 calibration으로 교체 / 별도 승인된 비공개 보존 / 현재 tree에서 삭제. 가격만 지워도 rel_diff·재구성 가능한 조합이 남는지 확인. |
| Yahoo 차트 원문·실험 중복·가격 재인용 | `implementation/experiments/chart-contract-v0.1/`의 **50파일**: 원문/파생 JSON 48개, extensionless raw blob 1개, 실제 OHLC 오류 표를 재인용한 Markdown 1개 | OHLC·adjclose·시장 가격 metadata와 수치 probe/원문 fragment. 현재 Pages copy는 없으나 공개 repo 보존은 별도 경계다. renderer의 미제공/차단 표기와 실제 저장 source를 구분한다. | 완전 합성 일봉·오류 fixture 교체 또는 필요한 실증 source의 보존·공개 사본 정리 범위 결정. 의미상 복사본·추출본도 함께 확인. |
| 실제 검증/성과·NPORT·가격 포함 공시 | `implementation/reports/`의 gate/official/real replay·ablation·outcome 보고서, `us_session_mixed_2026-09-23.json`, `implementation/docs/security_map19_owner/v1_1_cycle_20261008/sources/nport_0001752724-25-034052_original.xml.gz`, SCCO 원문·인용 정책과 일부 share-count 진단 | LIVE_FETCH 가격, 시총·순위, `equal_weight_realized/ew/period_return/realized_return`, NPORT `valUSD/val_usd` 시장평가액과 수량, 실제 평균 주당 가격 인용. SYNTHETIC QGV/공개 SEC라는 표기만으로 혼합 가격을 제외하지 않는다. | 공개 재무/주식수/식별은 유지하면서 가격·가격 파생 부분/복사본을 분리할지, 전체 파일을 비공개 보존 또는 삭제할지 결정. 혼합 demo/소비자 수정 별도. |
| 과거 상태 문서의 실제 값 재인용 | root Artifact Evidence/Contract Conflict/HANDOFF_HISTORY/TRACK_A_REAL_DATA_STATUS, `implementation/CHANGELOG.md`, `track_a_share_unit_policy_proposal_*` 등의 해당 구간 | 과거 실제 cutoff 시총·발행사 시총 순위·재구성 주가를 문서에 재기재. 원문 JSON만 정리해도 이 텍스트 사본은 남는다. 상세 목록의 각 경로·근거에 따라 분류했다. | 값 없는 provenance/status/count 기록으로 교체할 범위와 보호 이력/증거의 처리 기준 결정. 이번에는 과거 문서 수정하지 않음. |

정리 필요 **170파일** 중 **실제 값 DATA 143개 / 공개 출력 ROUTE 소스·설정 27개**를 구분한다. ROUTE는 수집/계산/출력할 수 있는 구성과 프로그램의 판정으로서 특정 Actions 실행이 실제 값을 유출했다는 주장과 다르다. 현재 Pages 직접 copy가 없는 실제 DATA도 공개 repo 보존 때문에 정리 대상이다. 같은 값의 재인용·복사본은 경로별로 센다.

보류 **51파일**은 원문 fragment/원응답 보존 범위, Yahoo·실티커 테스트의 가격 기원, 저장된 Track Record의 synthetic lineage, 공시의 exercise/intrinsic/FMV 문맥 등이다. 정확한 실제/합성 출처가 없을 때 금지 대상이라고 확정하거나 합성이라고 면제하지 않는다. 실제 값을 새로 조회해 채우지 않았고 보류 항목의 내용은 §7에 기록했다.

## 5. 정리 선택지와 Git 이력

다음은 **사용자 결정 후 별도 PR로 검토할 선택지**다. 현 PR에서 어떤 파일도 정리하거나 실행 경로를 바꾸지 않는다.

| 선택지 | 적용 예와 필요한 후속 범위 | 이력·공개 경계 |
| --- | --- | --- |
| 합성 fixture로 교체 | Yahoo/Tiingo/Stooq 캡처·가격 결합 demo·테스트 입력을 실제 시장과 무관한 합성 OHLCV/수익률/순위로 교체하고 출처를 명시한다. 실제 데이터에 `synthetic=true`만 붙이는 방식은 교체가 아니다. 소비자·fixture 기대값·증거/해시 영향은 별도 검토한다. | 새 커밋의 파일은 합성이어도 기존 실제 값은 이전 Git 커밋에 남는다. |
| 비공개 위치로 이동 | 정말 필요한 실자료의 보존 목적·권리·본인 접근 범위를 먼저 확정한다. 공개 저장소 안의 다른 폴더나 branch는 비공개 위치가 아니다. | 비공개 보관과 공개 복사본 제거는 별개다. 개인 일봉의 무저장/RAM 정책을 지속 보관 정책으로 바꾸려면 별도 사용자 결정이 필요하다. |
| 현재 tree에서 삭제 | 용도 없는 중복 원문·보고서·캡처를 제거하고 참조/소비 경로를 수정하는 후속 PR을 검토한다. Frozen·회귀·증거 보존 의존을 함께 확인한다. | 일반 삭제 커밋만으로 이전 커밋·태그·객체·fork·clone의 값이 없어지지 않는다. |
| 공개 출력 경로 정리 | 공개 Pages에는 가격과 가격 기반 순위/결합값을 넣지 않는 projection을 검토하고, 가격 수집기의 stdout·raw 캐시/업로드·보고서 commit 경로를 분리 또는 차단한다. 공개 SEC/DART 재무 경로와 개인 가격 경로는 분리한다. | 현재 tree의 경로를 막아도 기존 Pages 배포·Actions 로그/아티팩트·캐시가 자동 소거되는 것은 아니다. 실제 잔존 범위의 별도 확인이 필요하다. |

**Git 이력 처리는 자동 결정하지 않는다.** 위 실제 가격 DATA를 삭제·교체·이동하면 현재 tree의 경계를 개선할 수 있지만 과거 공개 이력에는 원 값이 남는다. 과거 공개본까지 제거할 필요가 있는지 사용자 결정이 필요하며, 필요하다면 보호된 Frozen/증거와 협업 사본·태그·fork·clone·외부 캐시 영향을 먼저 정리한 별도 계획과 명시적 승인이 선행돼야 한다. 현행 force push 금지 아래에서 이력 재작성은 실행할 수 없고 이번 PR은 그 금지를 완화하지 않는다.

SOURCE/ROUTE만 포함된 코드 파일은 코드 삭제나 이력 재작성 자체가 가격 정리의 필수 조건이라는 뜻이 아니다. 실제 값이 들어간 DATA 사본과 기존 출력의 잔존 여부를 구분한다. Frozen/hash guard·CI PASS는 새 공개 가격 경계의 충족 증거를 대신하지 않으며 기존 보호 기준을 임의로 바꾸지 않는다.

## 6. 사용자 결정이 필요한 사항

1. 실제 가격 DATA 각 묶음을 합성 교체·비공개 보존·현재 tree 삭제 중 어떻게 처리할지, 보존이 필요한 원자료/검증 증거의 범위.
2. Frozen의 가격 기반 순위·시총 및 가격 결합 QGV를 공개 projection에서 제외할 범위와, membership/식별만 남길 경우에도 가격 기반 선정·배열 순서가 순위 정보를 재현하는지의 처리 기준. 티커 집합 자체를 주가로 취급한다는 새 규칙은 확정하지 않는다.
3. 보호된 Frozen·회귀·hash/lineage 증거와 합성 교체의 충돌을 어떻게 해소할지. 해시 guard 또는 운영 모드를 이번 문서 승인으로 바꾸지 않는다.
4. 과거 공개 Git 이력과 기존 Pages/Actions 산출물까지 정리해야 하는지. 필요 시 현 금지와 별개로 구체 계획·승인 범위를 정할 것.
5. 판단 보류 항목의 실제/합성 출처·원문 의미를 어떤 근거로 확인할지. 미확인 항목은 공개 허용으로 승격하지 않는다.

이번 사용자 보고인 **Secret `KRX_API_KEY` 등록**은 [26E 결정 등록부](../pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md)의 **GSQ-009**에 append-only로 기록한다. 값·Secret API·환경변수·실제 인증을 확인하지 않았다. KRX는 한국 종목 대체 출처 후보이며, 사용권·무료 한도·지원 범위·연결 성공이 자동 확인된 것은 아니다. KRX에서 얻는 가격도 동일 공개 경계에 따른다.

## 7. 파일별 목록 읽는 법

아래 목록은 파일 단위다. 같은 내용의 복사본도 **경로별 한 개**로 세며 참조 URL이나 아직 보존되지 않은 외부 원문을 파일 수에 더하지 않는다. 실제 가격 숫자는 싣지 않는다. 공통 prefix를 표시한 묶음의 각 행 경로는 **prefix + 파일명**으로 정확히 복원된다. 묶음의 공통 종류·출처·용도·Pages 판정·근거·분류는 모든 행에 적용하며, 예외는 따로 분리한다.

### 7.1 raw 원문 참조·취득 기록

이 묶음은 대부분 원문을 참조하는 metadata다. 추적 manifest 6,808개가 지정하는 `implementation/data/raw/blobs/`의 대응 raw blob은 기준 tree에 없다. 다른 경로의 캡처·복사본은 별도 목록으로 판정했으며, 이 raw 경로의 미존재를 과거 Actions/cache/Git 이력의 무가격 증거로 삼지 않는다. 각 묶음의 출처는 file의 source_kind/취득 도구 근거이고 값 없는 manifest와 실제 종가 calibration을 구분했다.

#### R01 — 유지 가능 / NPORT/SEC / 24파일

- 공통 경로 prefix: `implementation/data/raw/`
- 종류: JSON, 취득 진단, public_filing_identity_metadata.
- 출처: NPORT/SEC.
- 용도: fetch_nport_reference의 fund membership/series/CIK/CUSIP provenance 및 식별 attestation run 진단; reported-price producer와 구분. 현재 holding market value/price/rank scalar 없음.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 유지 근거: 해당 경로의 metadata/명시된 비가격 facts·개수·상태·URL/hash를 확인했다. raw manifest는 가격 실값을 포함하지 않는다. 공급자 원문 body의 적격성은 별도다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `nport_run_1790339108.json` | 9,378 |
| `nport_run_1790340408.json` | 9,376 |
| `nport_run_1790341046.json` | 9,376 |
| `nport_run_1790378866.json` | 22,720 |
| `nport_run_1790379739.json` | 26,422 |
| `nport_run_1790380711.json` | 26,422 |
| `nport_run_1790382689.json` | 26,422 |
| `nport_run_1790383272.json` | 26,422 |
| `nport_run_1790385002.json` | 26,422 |
| `nport_run_1790386305.json` | 26,422 |
| `nport_run_1790387141.json` | 26,422 |
| `nport_run_1790387858.json` | 26,422 |
| `nport_run_1790388986.json` | 26,422 |
| `nport_run_1790390106.json` | 26,422 |
| `nport_run_1790391914.json` | 28,797 |
| `nport_run_1790397319.json` | 28,560 |
| `nport_run_1790398011.json` | 28,557 |
| `nport_run_1790398525.json` | 28,557 |
| `nport_run_1790401281.json` | 31,932 |
| `nport_run_1790402445.json` | 31,800 |
| `nport_run_1790403819.json` | 31,800 |
| `nport_run_1790404493.json` | 31,800 |
| `nport_run_1790405262.json` | 31,800 |
| `nport_run_1790406120.json` | 31,800 |

#### R02 — 유지 가능 / SEC / 22파일

- 공통 경로 prefix: `implementation/data/raw/`
- 종류: JSON, 취득 진단, public_nonprice_financial_fact, share_count_ratio.
- 출처: SEC.
- 용도: fetch_share_scale_docs의 SEC shares 규모 대조·primary filing 취득 진단; flagged[].ratio는 shares / SEC basic weighted-average shares, 가격 수익률·V가 아님.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 유지 근거: 해당 경로의 metadata/명시된 비가격 facts·개수·상태·URL/hash를 확인했다. raw manifest는 가격 실값을 포함하지 않는다. 공급자 원문 body의 적격성은 별도다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `share_scale_run_1790397466.json` | 11,488 |
| `share_scale_run_1790398129.json` | 11,206 |
| `share_scale_run_1790398666.json` | 11,206 |
| `share_scale_run_1790401480.json` | 9,673 |
| `share_scale_run_1790402591.json` | 9,673 |
| `share_scale_run_1790403974.json` | 9,673 |
| `share_scale_run_1790404635.json` | 9,673 |
| `share_scale_run_1790405431.json` | 9,673 |
| `share_scale_run_1790406277.json` | 9,673 |
| `share_scale_run_1790407787.json` | 13,281 |
| `share_scale_run_1790409195.json` | 13,281 |
| `share_scale_run_1790410115.json` | 13,281 |
| `share_scale_run_1790410791.json` | 13,281 |
| `share_scale_run_1790416019.json` | 11,721 |
| `share_scale_run_1790416840.json` | 10,189 |
| `share_scale_run_1790468645.json` | 10,189 |
| `share_scale_run_1790469589.json` | 10,189 |
| `share_scale_run_1790470661.json` | 10,189 |
| `share_scale_run_1790471823.json` | 10,189 |
| `share_scale_run_1790491185.json` | 10,189 |
| `share_scale_run_1790494763.json` | 10,189 |
| `share_scale_run_1790495919.json` | 10,189 |

#### R03 — 유지 가능 / SEC/NPORT/Yahoo/Tiingo/Stooq/other / 1파일

- 공통 경로 prefix: `implementation/data/raw/`
- 종류: JSON, mixed_source_store_index, 실값 없는 metadata.
- 출처: SEC/NPORT/Yahoo/Tiingo/Stooq/other.
- 용도: fetch_real_data.write_store_index가 모든 manifest를 source/hash/크기/취득시각 목록으로 투영; raw persistence/archive inventory 및 Actions evidence commit에 사용.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 유지 근거: 해당 경로의 metadata/명시된 비가격 facts·개수·상태·URL/hash를 확인했다. raw manifest는 가격 실값을 포함하지 않는다. 공급자 원문 body의 적격성은 별도다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `STORE_INDEX.json` | 2,662,352 |

#### R04 — 유지 가능 / SEC/Yahoo / 44파일

- 공통 경로 prefix: `implementation/data/raw/`
- 종류: JSON, 취득 진단, public_filing_identity_metadata, price_source_operation_metadata.
- 출처: SEC/Yahoo.
- 용도: fetch_cover_xbrl의 SEC cover filing 선택 및 SEC/Yahoo 원문 취득 진단; filings.*에는 form/filed/accn/primary_document/artifact_id만 기록, cover financial/market-value 본문 없음.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 유지 근거: 해당 경로의 metadata/명시된 비가격 facts·개수·상태·URL/hash를 확인했다. raw manifest는 가격 실값을 포함하지 않는다. 공급자 원문 body의 적격성은 별도다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `cover_xbrl_run_1790333965.json` | 31,636 |
| `cover_xbrl_run_1790334399.json` | 31,910 |
| `cover_xbrl_run_1790334718.json` | 31,798 |
| `cover_xbrl_run_1790335304.json` | 66,752 |
| `cover_xbrl_run_1790335664.json` | 45,484 |
| `cover_xbrl_run_1790337585.json` | 45,456 |
| `cover_xbrl_run_1790338044.json` | 45,456 |
| `cover_xbrl_run_1790339726.json` | 67,499 |
| `cover_xbrl_run_1790340487.json` | 68,315 |
| `cover_xbrl_run_1790341106.json` | 68,309 |
| `cover_xbrl_run_1790378935.json` | 71,964 |
| `cover_xbrl_run_1790379800.json` | 77,801 |
| `cover_xbrl_run_1790380760.json` | 77,801 |
| `cover_xbrl_run_1790382726.json` | 77,801 |
| `cover_xbrl_run_1790383313.json` | 77,801 |
| `cover_xbrl_run_1790385051.json` | 77,801 |
| `cover_xbrl_run_1790386348.json` | 77,801 |
| `cover_xbrl_run_1790387221.json` | 105,572 |
| `cover_xbrl_run_1790387910.json` | 105,344 |
| `cover_xbrl_run_1790389038.json` | 106,040 |
| `cover_xbrl_run_1790390156.json` | 106,036 |
| `cover_xbrl_run_1790392024.json` | 104,952 |
| `cover_xbrl_run_1790397374.json` | 104,282 |
| `cover_xbrl_run_1790398057.json` | 104,282 |
| `cover_xbrl_run_1790398578.json` | 104,282 |
| `cover_xbrl_run_1790401402.json` | 99,979 |
| `cover_xbrl_run_1790402495.json` | 99,598 |
| `cover_xbrl_run_1790403880.json` | 99,598 |
| `cover_xbrl_run_1790404548.json` | 99,598 |
| `cover_xbrl_run_1790405315.json` | 99,598 |
| `cover_xbrl_run_1790406171.json` | 99,598 |
| `cover_xbrl_run_1790407686.json` | 107,311 |
| `cover_xbrl_run_1790409117.json` | 108,403 |
| `cover_xbrl_run_1790410016.json` | 108,397 |
| `cover_xbrl_run_1790410690.json` | 108,397 |
| `cover_xbrl_run_1790415918.json` | 107,762 |
| `cover_xbrl_run_1790416769.json` | 102,844 |
| `cover_xbrl_run_1790468561.json` | 102,838 |
| `cover_xbrl_run_1790469481.json` | 102,838 |
| `cover_xbrl_run_1790470555.json` | 102,838 |
| `cover_xbrl_run_1790471716.json` | 102,726 |
| `cover_xbrl_run_1790491077.json` | 102,726 |
| `cover_xbrl_run_1790494656.json` | 102,726 |
| `cover_xbrl_run_1790495807.json` | 102,726 |

#### R05 — 유지 가능 / SEC/Yahoo / 136파일

- 공통 경로 prefix: `implementation/data/raw/`
- 종류: JSON, 취득 진단, ingestion_diagnostic, price_source_operation_metadata.
- 출처: SEC/Yahoo.
- 용도: fetch_real_data의 SEC/Yahoo 일반 취득 run log와 plan_resolution 식별/취득 metadata; source URL/status/byte count만으로 시세 payload를 대신하지 않음.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 유지 근거: 해당 경로의 metadata/명시된 비가격 facts·개수·상태·URL/hash를 확인했다. raw manifest는 가격 실값을 포함하지 않는다. 공급자 원문 body의 적격성은 별도다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `ingest_run_1790150732.json` | 911 |
| `ingest_run_1790151243.json` | 1,116 |
| `ingest_run_1790151635.json` | 2,777 |
| `ingest_run_1790289959.json` | 161,789 |
| `ingest_run_1790324763.json` | 112,081 |
| `ingest_run_1790325309.json` | 206,796 |
| `ingest_run_1790325878.json` | 110,201 |
| `ingest_run_1790326182.json` | 204,207 |
| `ingest_run_1790326856.json` | 110,201 |
| `ingest_run_1790333554.json` | 110,201 |
| `ingest_run_1790333936.json` | 110,201 |
| `ingest_run_1790334368.json` | 139,083 |
| `ingest_run_1790334373.json` | 290,412 |
| `ingest_run_1790334669.json` | 139,083 |
| `ingest_run_1790334675.json` | 290,412 |
| `ingest_run_1790335179.json` | 139,083 |
| `ingest_run_1790335185.json` | 290,412 |
| `ingest_run_1790335625.json` | 139,083 |
| `ingest_run_1790335630.json` | 290,412 |
| `ingest_run_1790337545.json` | 139,083 |
| `ingest_run_1790337550.json` | 290,412 |
| `ingest_run_1790338010.json` | 139,083 |
| `ingest_run_1790338015.json` | 290,412 |
| `ingest_run_1790338526.json` | 139,083 |
| `ingest_run_1790338531.json` | 290,412 |
| `ingest_run_1790339095.json` | 139,083 |
| `ingest_run_1790339100.json` | 290,412 |
| `ingest_run_1790339675.json` | 165,767 |
| `ingest_run_1790340392.json` | 139,083 |
| `ingest_run_1790340397.json` | 290,412 |
| `ingest_run_1790340448.json` | 174,109 |
| `ingest_run_1790341022.json` | 139,083 |
| `ingest_run_1790341028.json` | 290,412 |
| `ingest_run_1790341068.json` | 175,560 |
| `ingest_run_1790378788.json` | 139,083 |
| `ingest_run_1790378793.json` | 290,412 |
| `ingest_run_1790378893.json` | 191,891 |
| `ingest_run_1790379713.json` | 138,321 |
| `ingest_run_1790379717.json` | 290,259 |
| `ingest_run_1790379752.json` | 194,378 |
| `ingest_run_1790380685.json` | 138,321 |
| `ingest_run_1790380690.json` | 290,259 |
| `ingest_run_1790380720.json` | 195,111 |
| `ingest_run_1790382672.json` | 138,321 |
| `ingest_run_1790382677.json` | 290,259 |
| `ingest_run_1790382698.json` | 195,034 |
| `ingest_run_1790383252.json` | 138,321 |
| `ingest_run_1790383257.json` | 290,259 |
| `ingest_run_1790383280.json` | 195,034 |
| `ingest_run_1790384977.json` | 138,321 |
| `ingest_run_1790384983.json` | 290,259 |
| `ingest_run_1790385014.json` | 195,034 |
| `ingest_run_1790386283.json` | 138,321 |
| `ingest_run_1790386288.json` | 290,259 |
| `ingest_run_1790386314.json` | 195,034 |
| `ingest_run_1790387116.json` | 138,321 |
| `ingest_run_1790387121.json` | 290,259 |
| `ingest_run_1790387149.json` | 195,034 |
| `ingest_run_1790387833.json` | 138,321 |
| `ingest_run_1790387837.json` | 290,259 |
| `ingest_run_1790387866.json` | 195,034 |
| `ingest_run_1790388961.json` | 138,321 |
| `ingest_run_1790388966.json` | 290,259 |
| `ingest_run_1790388994.json` | 195,034 |
| `ingest_run_1790390082.json` | 138,321 |
| `ingest_run_1790390090.json` | 290,259 |
| `ingest_run_1790390119.json` | 195,034 |
| `ingest_run_1790391834.json` | 138,321 |
| `ingest_run_1790391839.json` | 290,259 |
| `ingest_run_1790391928.json` | 196,765 |
| `ingest_run_1790397292.json` | 138,321 |
| `ingest_run_1790397297.json` | 290,259 |
| `ingest_run_1790397329.json` | 196,782 |
| `ingest_run_1790397989.json` | 138,321 |
| `ingest_run_1790397995.json` | 290,259 |
| `ingest_run_1790398022.json` | 196,782 |
| `ingest_run_1790398498.json` | 138,321 |
| `ingest_run_1790398503.json` | 290,259 |
| `ingest_run_1790398534.json` | 196,782 |
| `ingest_run_1790401211.json` | 138,321 |
| `ingest_run_1790401217.json` | 290,259 |
| `ingest_run_1790401334.json` | 197,700 |
| `ingest_run_1790402419.json` | 138,321 |
| `ingest_run_1790402424.json` | 290,259 |
| `ingest_run_1790402454.json` | 197,352 |
| `ingest_run_1790403792.json` | 138,321 |
| `ingest_run_1790403799.json` | 290,259 |
| `ingest_run_1790403832.json` | 197,352 |
| `ingest_run_1790404468.json` | 138,321 |
| `ingest_run_1790404474.json` | 290,259 |
| `ingest_run_1790404505.json` | 197,352 |
| `ingest_run_1790405237.json` | 138,321 |
| `ingest_run_1790405241.json` | 290,259 |
| `ingest_run_1790405272.json` | 197,352 |
| `ingest_run_1790406095.json` | 138,321 |
| `ingest_run_1790406100.json` | 290,259 |
| `ingest_run_1790406129.json` | 197,352 |
| `ingest_run_1790407567.json` | 138,321 |
| `ingest_run_1790407572.json` | 290,259 |
| `ingest_run_1790407643.json` | 196,418 |
| `ingest_run_1790409019.json` | 138,321 |
| `ingest_run_1790409025.json` | 290,259 |
| `ingest_run_1790409082.json` | 197,312 |
| `ingest_run_1790409872.json` | 138,321 |
| `ingest_run_1790409877.json` | 290,259 |
| `ingest_run_1790409973.json` | 197,228 |
| `ingest_run_1790410592.json` | 138,321 |
| `ingest_run_1790410597.json` | 290,259 |
| `ingest_run_1790410645.json` | 197,228 |
| `ingest_run_1790415762.json` | 138,321 |
| `ingest_run_1790415767.json` | 290,259 |
| `ingest_run_1790415873.json` | 198,976 |
| `ingest_run_1790416659.json` | 138,321 |
| `ingest_run_1790416666.json` | 290,259 |
| `ingest_run_1790416738.json` | 199,546 |
| `ingest_run_1790468469.json` | 138,321 |
| `ingest_run_1790468475.json` | 290,259 |
| `ingest_run_1790468526.json` | 199,546 |
| `ingest_run_1790469365.json` | 138,321 |
| `ingest_run_1790469370.json` | 290,259 |
| `ingest_run_1790469438.json` | 199,546 |
| `ingest_run_1790470457.json` | 138,321 |
| `ingest_run_1790470462.json` | 290,259 |
| `ingest_run_1790470512.json` | 199,546 |
| `ingest_run_1790471617.json` | 138,321 |
| `ingest_run_1790471622.json` | 290,259 |
| `ingest_run_1790471672.json` | 199,140 |
| `ingest_run_1790490977.json` | 138,321 |
| `ingest_run_1790490982.json` | 290,259 |
| `ingest_run_1790491032.json` | 199,140 |
| `ingest_run_1790494559.json` | 138,321 |
| `ingest_run_1790494563.json` | 290,259 |
| `ingest_run_1790494612.json` | 199,140 |
| `ingest_run_1790495705.json` | 138,321 |
| `ingest_run_1790495709.json` | 290,259 |
| `ingest_run_1790495761.json` | 199,140 |

#### R06 — 유지 가능 / Stooq / 1파일

- 공통 경로 prefix: `implementation/data/raw/`
- 종류: JSON, 취득 진단, price_source_operation_metadata.
- 출처: Stooq.
- 용도: fetch_stooq_prices의 calibration/fallback run 진단. 현재 calibration에는 symbol/status만 있고 실제 종가/rel_diff numeric field 없음; generator는 정상 응답이면 price를 기록할 수 있음.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 유지 근거: 해당 경로의 metadata/명시된 비가격 facts·개수·상태·URL/hash를 확인했다. raw manifest는 가격 실값을 포함하지 않는다. 공급자 원문 body의 적격성은 별도다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `stooq_run_1790337611.json` | 2,907 |

#### R07 — 유지 가능 / Yahoo / 5파일

- 공통 경로 prefix: `implementation/data/raw/`
- 종류: JSON, 취득 진단, ingestion_diagnostic, price_source_operation_metadata.
- 출처: Yahoo.
- 용도: fetch_real_data의 SEC/Yahoo 일반 취득 run log와 plan_resolution 식별/취득 metadata; source URL/status/byte count만으로 시세 payload를 대신하지 않음.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 유지 근거: 해당 경로의 metadata/명시된 비가격 facts·개수·상태·URL/hash를 확인했다. raw manifest는 가격 실값을 포함하지 않는다. 공급자 원문 body의 적격성은 별도다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `ingest_run_1790334377.json` | 806 |
| `ingest_run_1790334696.json` | 6,903 |
| `ingest_run_1790340401.json` | 408 |
| `ingest_run_1790391844.json` | 910 |
| `ingest_run_1790401222.json` | 1,110 |

#### R08 — 유지 가능 / NPORT / 1파일

- 공통 경로 prefix: `implementation/data/raw/manifests/`
- 종류: JSON, 원문 참조 metadata, 실값 없는 metadata, 가격/혼합 원문 참조.
- 출처: NPORT / `source_kind=SEC_NPORT`.
- 용도: SEC N-PORT fund filing provenance; fund membership 및 reported-value price 파생 경로의 참조. manifest 자체 소비: RawDatasetStore.get_manifest, raw_persistence.artifact_records, STORE_INDEX writer, archive restore check.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 유지 근거: 해당 경로의 metadata/명시된 비가격 facts·개수·상태·URL/hash를 확인했다. raw manifest는 가격 실값을 포함하지 않는다. 공급자 원문 body의 적격성은 별도다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `nport__0001752724-25-034052.json` | 465 |

#### R09 — 유지 가능 / NPORT / 5파일

- 공통 경로 prefix: `implementation/data/raw/manifests/`
- 종류: JSON, 원문 참조 metadata, 실값 없는 metadata, 가격/혼합 원문 참조.
- 출처: NPORT / `source_kind=SEC_NPORT_XML`.
- 용도: SEC N-PORT XML provenance; fetch_nport_reference 및 nport_reported_prices의 원자료 참조. manifest 자체 소비: RawDatasetStore.get_manifest, raw_persistence.artifact_records, STORE_INDEX writer, archive restore check.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 유지 근거: 해당 경로의 metadata/명시된 비가격 facts·개수·상태·URL/hash를 확인했다. raw manifest는 가격 실값을 포함하지 않는다. 공급자 원문 body의 적격성은 별도다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `nport_xml__0001752724-24-189684.json` | 451 |
| `nport_xml__0001752724-24-194289.json` | 451 |
| `nport_xml__0001752724-24-194911.json` | 450 |
| `nport_xml__0001752724-24-268869.json` | 451 |
| `nport_xml__0001752724-25-034052.json` | 451 |

#### R10 — 유지 가능 / Stooq / 28파일

- 공통 경로 prefix: `implementation/data/raw/manifests/`
- 종류: JSON, 원문 참조 metadata, 실값 없는 metadata, 가격/혼합 원문 참조.
- 출처: Stooq / `source_kind=STOOQ_DAILY_CSV`.
- 용도: Stooq CSV provenance; fetch_stooq_prices.csv_close_on_or_before의 가격 calibration/fallback 참조. manifest 자체 소비: RawDatasetStore.get_manifest, raw_persistence.artifact_records, STORE_INDEX writer, archive restore check.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 유지 근거: 해당 경로의 metadata/명시된 비가격 facts·개수·상태·URL/hash를 확인했다. raw manifest는 가격 실값을 포함하지 않는다. 공급자 원문 body의 적격성은 별도다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `stooq_csv__AAPL.json` | 406 |
| `stooq_csv__ANSS.json` | 406 |
| `stooq_csv__AVB.json` | 404 |
| `stooq_csv__BFA.json` | 404 |
| `stooq_csv__BFB.json` | 404 |
| `stooq_csv__BK.json` | 402 |
| `stooq_csv__CTRA.json` | 406 |
| `stooq_csv__DAY.json` | 404 |
| `stooq_csv__DFS.json` | 404 |
| `stooq_csv__EA.json` | 402 |
| `stooq_csv__EQR.json` | 404 |
| `stooq_csv__HES.json` | 404 |
| `stooq_csv__HOLX.json` | 406 |
| `stooq_csv__IPG.json` | 404 |
| `stooq_csv__JNPR.json` | 406 |
| `stooq_csv__JPM.json` | 404 |
| `stooq_csv__K.json` | 400 |
| `stooq_csv__KO.json` | 402 |
| `stooq_csv__MSFT.json` | 406 |
| `stooq_csv__PARAA.json` | 408 |
| `stooq_csv__PG.json` | 402 |
| `stooq_csv__PINC.json` | 406 |
| `stooq_csv__SQ.json` | 402 |
| `stooq_csv__WBA.json` | 404 |
| `stooq_csv__WOLF.json` | 406 |
| `stooq_csv__WRK.json` | 404 |
| `stooq_csv__WSOB.json` | 406 |
| `stooq_csv__XOM.json` | 404 |

#### R11 — 유지 가능 / Tiingo / 58파일

- 공통 경로 prefix: `implementation/data/raw/manifests/`
- 종류: JSON, 원문 참조 metadata, 실값 없는 metadata, 가격/혼합 원문 참조.
- 출처: Tiingo / `source_kind=TIINGO_DAILY_RAW`.
- 용도: Tiingo daily raw close를 Yahoo chart replay envelope로 변환한 원문 provenance; replay.load_price_bars 및 audit_mcap_store에서 소비. manifest 자체 소비: RawDatasetStore.get_manifest, raw_persistence.artifact_records, STORE_INDEX writer, archive restore check.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 유지 근거: 해당 경로의 metadata/명시된 비가격 facts·개수·상태·URL/hash를 확인했다. raw manifest는 가격 실값을 포함하지 않는다. 공급자 원문 body의 적격성은 별도다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `yahoo_chart__AGR__5y.json` | 534 |
| `yahoo_chart__AL__5y.json` | 532 |
| `yahoo_chart__AMED__5y.json` | 536 |
| `yahoo_chart__ANSS__5y.json` | 536 |
| `yahoo_chart__APLS__5y.json` | 536 |
| `yahoo_chart__AVB__5y.json` | 534 |
| `yahoo_chart__AZEK__5y.json` | 536 |
| `yahoo_chart__AZPN__5y.json` | 536 |
| `yahoo_chart__BERY__5y.json` | 536 |
| `yahoo_chart__BLD__5y.json` | 534 |
| `yahoo_chart__CFLT__5y.json` | 536 |
| `yahoo_chart__CIVI__5y.json` | 536 |
| `yahoo_chart__CMA__5y.json` | 534 |
| `yahoo_chart__CTLT__5y.json` | 536 |
| `yahoo_chart__CTRA__5y.json` | 536 |
| `yahoo_chart__CWEN-A__5y.json` | 540 |
| `yahoo_chart__DAY__5y.json` | 534 |
| `yahoo_chart__DFS__5y.json` | 534 |
| `yahoo_chart__DNB__5y.json` | 534 |
| `yahoo_chart__EA__5y.json` | 532 |
| `yahoo_chart__EQR__5y.json` | 604 |
| `yahoo_chart__EXAS__5y.json` | 536 |
| `yahoo_chart__FYBR__5y.json` | 536 |
| `yahoo_chart__HCP__5y.json` | 534 |
| `yahoo_chart__HES__5y.json` | 534 |
| `yahoo_chart__HOLX__5y.json` | 536 |
| `yahoo_chart__INFA__5y.json` | 536 |
| `yahoo_chart__IPG__5y.json` | 534 |
| `yahoo_chart__ITCI__5y.json` | 536 |
| `yahoo_chart__JHG__5y.json` | 534 |
| `yahoo_chart__JNPR__5y.json` | 536 |
| `yahoo_chart__JWN__5y.json` | 534 |
| `yahoo_chart__KLG__5y.json` | 532 |
| `yahoo_chart__K__5y.json` | 530 |
| `yahoo_chart__LBRDK__5y.json` | 538 |
| `yahoo_chart__LEG__5y.json` | 534 |
| `yahoo_chart__LSXMA__5y.json` | 538 |
| `yahoo_chart__LSXMB__5y.json` | 538 |
| `yahoo_chart__LSXMK__5y.json` | 538 |
| `yahoo_chart__MASI__5y.json` | 536 |
| `yahoo_chart__MCW__5y.json` | 534 |
| `yahoo_chart__MRO__5y.json` | 534 |
| `yahoo_chart__NSA__5y.json` | 534 |
| `yahoo_chart__OLPX__5y.json` | 536 |
| `yahoo_chart__PARAA__5y.json` | 538 |
| `yahoo_chart__PYCR__5y.json` | 536 |
| `yahoo_chart__RCM__5y.json` | 534 |
| `yahoo_chart__SEE__5y.json` | 534 |
| `yahoo_chart__SFB__5y.json` | 534 |
| `yahoo_chart__SKX__5y.json` | 534 |
| `yahoo_chart__SMAR__5y.json` | 536 |
| `yahoo_chart__SNV__5y.json` | 534 |
| `yahoo_chart__SPR__5y.json` | 534 |
| `yahoo_chart__SRCL__5y.json` | 536 |
| `yahoo_chart__SWN__5y.json` | 534 |
| `yahoo_chart__WBA__5y.json` | 534 |
| `yahoo_chart__WBS__5y.json` | 534 |
| `yahoo_chart__X__5y.json` | 530 |

#### R12 — 유지 가능 / Tiingo / 74파일

- 공통 경로 prefix: `implementation/data/raw/manifests/`
- 종류: JSON, 원문 참조 metadata, 실값 없는 metadata, 가격/혼합 원문 참조.
- 출처: Tiingo / `source_kind=TIINGO_EOD_JSON`.
- 용도: Tiingo EOD 원문 provenance; fetch_tiingo_prices.parse_eod 및 calibration/fallback 소비 경로의 참조. manifest 자체 소비: RawDatasetStore.get_manifest, raw_persistence.artifact_records, STORE_INDEX writer, archive restore check.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 유지 근거: 해당 경로의 metadata/명시된 비가격 facts·개수·상태·URL/hash를 확인했다. raw manifest는 가격 실값을 포함하지 않는다. 공급자 원문 body의 적격성은 별도다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `tiingo_eod__AAPL.json` | 444 |
| `tiingo_eod__AGR.json` | 442 |
| `tiingo_eod__AL.json` | 440 |
| `tiingo_eod__AMED.json` | 444 |
| `tiingo_eod__ANSS.json` | 444 |
| `tiingo_eod__APLS.json` | 444 |
| `tiingo_eod__AVB.json` | 442 |
| `tiingo_eod__AZEK.json` | 444 |
| `tiingo_eod__AZPN.json` | 444 |
| `tiingo_eod__BERY.json` | 444 |
| `tiingo_eod__BFA.json` | 437 |
| `tiingo_eod__BFB.json` | 437 |
| `tiingo_eod__BK.json` | 438 |
| `tiingo_eod__BLD.json` | 442 |
| `tiingo_eod__CFLT.json` | 444 |
| `tiingo_eod__CIVI.json` | 444 |
| `tiingo_eod__CMA.json` | 442 |
| `tiingo_eod__CTLT.json` | 444 |
| `tiingo_eod__CTRA.json` | 444 |
| `tiingo_eod__CWEN-A.json` | 448 |
| `tiingo_eod__DAY.json` | 442 |
| `tiingo_eod__DFS.json` | 442 |
| `tiingo_eod__DNB.json` | 442 |
| `tiingo_eod__EA.json` | 440 |
| `tiingo_eod__EQR.json` | 437 |
| `tiingo_eod__EXAS.json` | 444 |
| `tiingo_eod__FYBR.json` | 444 |
| `tiingo_eod__HCP.json` | 442 |
| `tiingo_eod__HES.json` | 442 |
| `tiingo_eod__HOLX.json` | 444 |
| `tiingo_eod__INFA.json` | 444 |
| `tiingo_eod__IPG.json` | 442 |
| `tiingo_eod__ITCI.json` | 444 |
| `tiingo_eod__JHG.json` | 442 |
| `tiingo_eod__JNPR.json` | 444 |
| `tiingo_eod__JPM.json` | 442 |
| `tiingo_eod__JWN.json` | 442 |
| `tiingo_eod__K.json` | 438 |
| `tiingo_eod__KLG.json` | 439 |
| `tiingo_eod__KO.json` | 440 |
| `tiingo_eod__LBRDK.json` | 446 |
| `tiingo_eod__LEG.json` | 442 |
| `tiingo_eod__LSXMA.json` | 446 |
| `tiingo_eod__LSXMB.json` | 446 |
| `tiingo_eod__LSXMK.json` | 446 |
| `tiingo_eod__MASI.json` | 444 |
| `tiingo_eod__MCW.json` | 442 |
| `tiingo_eod__MRO.json` | 442 |
| `tiingo_eod__MSFT.json` | 444 |
| `tiingo_eod__NSA.json` | 442 |
| `tiingo_eod__OLPX.json` | 444 |
| `tiingo_eod__PARAA.json` | 446 |
| `tiingo_eod__PG.json` | 440 |
| `tiingo_eod__PINC.json` | 443 |
| `tiingo_eod__PYCR.json` | 444 |
| `tiingo_eod__RCM.json` | 442 |
| `tiingo_eod__SEE.json` | 442 |
| `tiingo_eod__SFB.json` | 442 |
| `tiingo_eod__SKX.json` | 442 |
| `tiingo_eod__SMAR.json` | 444 |
| `tiingo_eod__SNV.json` | 442 |
| `tiingo_eod__SPR.json` | 442 |
| `tiingo_eod__SQ.json` | 435 |
| `tiingo_eod__SRCL.json` | 444 |
| `tiingo_eod__SWN.json` | 442 |
| `tiingo_eod__US000000000543.json` | 464 |
| `tiingo_eod__US000000123662.json` | 463 |
| `tiingo_eod__VMRK.json` | 444 |
| `tiingo_eod__WBA.json` | 442 |
| `tiingo_eod__WBS.json` | 442 |
| `tiingo_eod__WOLF.json` | 443 |
| `tiingo_eod__WRK.json` | 439 |
| `tiingo_eod__X.json` | 438 |
| `tiingo_eod__XOM.json` | 442 |

#### R13 — 유지 가능 / Tiingo / 7파일

- 공통 경로 prefix: `implementation/data/raw/manifests/`
- 종류: JSON, 원문 참조 metadata, 실값 없는 metadata, listing_identity_reference.
- 출처: Tiingo / `source_kind=TIINGO_SEARCH_JSON`.
- 용도: Tiingo 회사/상장 검색 identity metadata provenance; fetch_tiingo_prices.search_candidates/alternate에서 참조. manifest 자체 소비: RawDatasetStore.get_manifest, raw_persistence.artifact_records, STORE_INDEX writer, archive restore check.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 유지 근거: 해당 경로의 metadata/명시된 비가격 facts·개수·상태·URL/hash를 확인했다. raw manifest는 가격 실값을 포함하지 않는다. 공급자 원문 body의 적격성은 별도다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `tiingo_search__EQR__VIVMARK_RESIDENTIAL.json` | 469 |
| `tiingo_search__PINC.json` | 444 |
| `tiingo_search__PINC__PREMIER.json` | 445 |
| `tiingo_search__WOLF.json` | 446 |
| `tiingo_search__WOLF__WOLFSPEED.json` | 448 |
| `tiingo_search__WRK__WESTROCK.json` | 445 |
| `tiingo_search__WRK__WHISKEY_HOLDCO.json` | 457 |

#### R14 — 유지 가능 / Yahoo / 1,346파일

- 공통 경로 prefix: `implementation/data/raw/manifests/`
- 종류: JSON, 원문 참조 metadata, 실값 없는 metadata, 가격/혼합 원문 참조.
- 출처: Yahoo / `source_kind=YAHOO_CHART`.
- 용도: Yahoo 일봉 가격 chart provenance; replay.load_price_bars → historical/QGV valuation/market-cap gate consumers의 원자료 참조. manifest 자체 소비: RawDatasetStore.get_manifest, raw_persistence.artifact_records, STORE_INDEX writer, archive restore check.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 유지 근거: 해당 경로의 metadata/명시된 비가격 facts·개수·상태·URL/hash를 확인했다. raw manifest는 가격 실값을 포함하지 않는다. 공급자 원문 body의 적격성은 별도다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `yahoo_chart__AAL__5y.json` | 451 |
| `yahoo_chart__AAON__5y.json` | 453 |
| `yahoo_chart__AAPL__5y.json` | 453 |
| `yahoo_chart__AAP__5y.json` | 451 |
| `yahoo_chart__AA__5y.json` | 449 |
| `yahoo_chart__ABBV__5y.json` | 453 |
| `yahoo_chart__ABNB__5y.json` | 453 |
| `yahoo_chart__ABT__5y.json` | 451 |
| `yahoo_chart__ACGL__5y.json` | 453 |
| `yahoo_chart__ACHC__5y.json` | 453 |
| `yahoo_chart__ACI__5y.json` | 451 |
| `yahoo_chart__ACM__5y.json` | 451 |
| `yahoo_chart__ACN__5y.json` | 451 |
| `yahoo_chart__ADBE__5y.json` | 453 |
| `yahoo_chart__ADC__5y.json` | 451 |
| `yahoo_chart__ADI__5y.json` | 451 |
| `yahoo_chart__ADM__5y.json` | 451 |
| `yahoo_chart__ADP__5y.json` | 451 |
| `yahoo_chart__ADSK__5y.json` | 453 |
| `yahoo_chart__ADTTF__5y.json` | 455 |
| `yahoo_chart__ADT__5y.json` | 451 |
| `yahoo_chart__AEE__5y.json` | 451 |
| `yahoo_chart__AEMRF__5y.json` | 453 |
| `yahoo_chart__AEM__5y.json` | 451 |
| `yahoo_chart__AEP__5y.json` | 451 |
| `yahoo_chart__AES__5y.json` | 451 |
| `yahoo_chart__AFG__5y.json` | 451 |
| `yahoo_chart__AFL__5y.json` | 451 |
| `yahoo_chart__AFRM__5y.json` | 453 |
| `yahoo_chart__AGCO__5y.json` | 453 |
| `yahoo_chart__AGL__5y.json` | 450 |
| `yahoo_chart__AGNC__5y.json` | 453 |
| `yahoo_chart__AGO__5y.json` | 451 |
| `yahoo_chart__AIG__5y.json` | 451 |
| `yahoo_chart__AIQD__5y.json` | 451 |
| `yahoo_chart__AIQU__5y.json` | 451 |
| `yahoo_chart__AIZ__5y.json` | 451 |
| `yahoo_chart__AJG__5y.json` | 451 |
| `yahoo_chart__AKAM__5y.json` | 453 |
| `yahoo_chart__ALAB__5y.json` | 452 |
| `yahoo_chart__ALB__5y.json` | 451 |
| `yahoo_chart__ALGM__5y.json` | 453 |
| `yahoo_chart__ALGN__5y.json` | 453 |
| `yahoo_chart__ALK__5y.json` | 451 |
| `yahoo_chart__ALL-PB__5y.json` | 457 |
| `yahoo_chart__ALL-PH__5y.json` | 457 |
| `yahoo_chart__ALL-PI__5y.json` | 457 |
| `yahoo_chart__ALL-PJ__5y.json` | 456 |
| `yahoo_chart__ALLE__5y.json` | 453 |
| `yahoo_chart__ALLY__5y.json` | 453 |
| `yahoo_chart__ALL__5y.json` | 451 |
| `yahoo_chart__ALNY__5y.json` | 453 |
| `yahoo_chart__ALSN__5y.json` | 453 |
| `yahoo_chart__AMAT__5y.json` | 453 |
| `yahoo_chart__AMBP__5y.json` | 453 |
| `yahoo_chart__AMCR__5y.json` | 453 |
| `yahoo_chart__AMC__5y.json` | 451 |
| `yahoo_chart__AMD__5y.json` | 451 |
| `yahoo_chart__AME__5y.json` | 451 |
| `yahoo_chart__AMGN__5y.json` | 453 |
| `yahoo_chart__AMG__5y.json` | 451 |
| `yahoo_chart__AMH__5y.json` | 451 |
| `yahoo_chart__AMJB__5y.json` | 452 |
| `yahoo_chart__AMKR__5y.json` | 453 |
| `yahoo_chart__AMP__5y.json` | 451 |
| `yahoo_chart__AMSYF__5y.json` | 455 |
| `yahoo_chart__AMTM__5y.json` | 452 |
| `yahoo_chart__AMT__5y.json` | 451 |
| `yahoo_chart__AMXOF__5y.json` | 455 |
| `yahoo_chart__AMX__5y.json` | 451 |
| `yahoo_chart__AMZN__5y.json` | 453 |
| `yahoo_chart__AM__5y.json` | 449 |
| `yahoo_chart__ANET__5y.json` | 453 |
| `yahoo_chart__AN__5y.json` | 449 |
| `yahoo_chart__AON__5y.json` | 451 |
| `yahoo_chart__AOS__5y.json` | 451 |
| `yahoo_chart__APA__5y.json` | 451 |
| `yahoo_chart__APD__5y.json` | 451 |
| `yahoo_chart__APG__5y.json` | 451 |
| `yahoo_chart__APH__5y.json` | 451 |
| `yahoo_chart__APOS__5y.json` | 452 |
| `yahoo_chart__APO__5y.json` | 451 |
| `yahoo_chart__APPF__5y.json` | 453 |
| `yahoo_chart__APP__5y.json` | 451 |
| `yahoo_chart__APTV__5y.json` | 453 |
| `yahoo_chart__ARCXF__5y.json` | 455 |
| `yahoo_chart__ARES__5y.json` | 453 |
| `yahoo_chart__ARE__5y.json` | 451 |
| `yahoo_chart__ARGX__5y.json` | 453 |
| `yahoo_chart__ARMK__5y.json` | 453 |
| `yahoo_chart__ARM__5y.json` | 450 |
| `yahoo_chart__ARW__5y.json` | 451 |
| `yahoo_chart__AR__5y.json` | 449 |
| `yahoo_chart__ASH__5y.json` | 451 |
| `yahoo_chart__ASMLF__5y.json` | 455 |
| `yahoo_chart__ASML__5y.json` | 453 |
| `yahoo_chart__ASX__5y.json` | 451 |
| `yahoo_chart__AS__5y.json` | 448 |
| `yahoo_chart__ATEYY__5y.json` | 455 |
| `yahoo_chart__ATI__5y.json` | 451 |
| `yahoo_chart__ATO__5y.json` | 451 |
| `yahoo_chart__ATR__5y.json` | 451 |
| `yahoo_chart__AU__5y.json` | 449 |
| `yahoo_chart__AVGO__5y.json` | 453 |
| `yahoo_chart__AVTR__5y.json` | 453 |
| `yahoo_chart__AVT__5y.json` | 451 |
| `yahoo_chart__AVY__5y.json` | 451 |
| `yahoo_chart__AWI__5y.json` | 451 |
| `yahoo_chart__AWK__5y.json` | 451 |
| `yahoo_chart__AXON__5y.json` | 453 |
| `yahoo_chart__AXP__5y.json` | 451 |
| `yahoo_chart__AXS__5y.json` | 451 |
| `yahoo_chart__AXTA__5y.json` | 453 |
| `yahoo_chart__AYI__5y.json` | 451 |
| `yahoo_chart__AZN__5y.json` | 451 |
| `yahoo_chart__AZO__5y.json` | 451 |
| `yahoo_chart__AZTA__5y.json` | 453 |
| `yahoo_chart__A__5y.json` | 447 |
| `yahoo_chart__BA-PA__5y.json` | 454 |
| `yahoo_chart__BABAF__5y.json` | 455 |
| `yahoo_chart__BABA__5y.json` | 453 |
| `yahoo_chart__BAC-PB__5y.json` | 457 |
| `yahoo_chart__BAC-PE__5y.json` | 457 |
| `yahoo_chart__BAC-PK__5y.json` | 457 |
| `yahoo_chart__BAC-PL__5y.json` | 457 |
| `yahoo_chart__BAC-PM__5y.json` | 457 |
| `yahoo_chart__BAC-PN__5y.json` | 457 |
| `yahoo_chart__BAC-PO__5y.json` | 457 |
| `yahoo_chart__BAC-PP__5y.json` | 457 |
| `yahoo_chart__BAC-PQ__5y.json` | 457 |
| `yahoo_chart__BAC-PS__5y.json` | 457 |
| `yahoo_chart__BACRP__5y.json` | 454 |
| `yahoo_chart__BAC__5y.json` | 451 |
| `yahoo_chart__BAH__5y.json` | 451 |
| `yahoo_chart__BALL__5y.json` | 453 |
| `yahoo_chart__BAMGF__5y.json` | 455 |
| `yahoo_chart__BAMKF__5y.json` | 455 |
| `yahoo_chart__BAM__5y.json` | 451 |
| `yahoo_chart__BAX__5y.json` | 451 |
| `yahoo_chart__BA__5y.json` | 449 |
| `yahoo_chart__BBVA__5y.json` | 453 |
| `yahoo_chart__BBVXF__5y.json` | 455 |
| `yahoo_chart__BBWI__5y.json` | 453 |
| `yahoo_chart__BBY__5y.json` | 451 |
| `yahoo_chart__BCDRF__5y.json` | 455 |
| `yahoo_chart__BCLYF__5y.json` | 455 |
| `yahoo_chart__BCS__5y.json` | 451 |
| `yahoo_chart__BC__5y.json` | 449 |
| `yahoo_chart__BDX__5y.json` | 451 |
| `yahoo_chart__BEN__5y.json` | 451 |
| `yahoo_chart__BEPC__5y.json` | 453 |
| `yahoo_chart__BERZ__5y.json` | 452 |
| `yahoo_chart__BE__5y.json` | 449 |
| `yahoo_chart__BF-A__5y.json` | 453 |
| `yahoo_chart__BF-B__5y.json` | 453 |
| `yahoo_chart__BFAM__5y.json` | 453 |
| `yahoo_chart__BG__5y.json` | 449 |
| `yahoo_chart__BHF__5y.json` | 451 |
| `yahoo_chart__BHPLF__5y.json` | 455 |
| `yahoo_chart__BHP__5y.json` | 451 |
| `yahoo_chart__BIIB__5y.json` | 453 |
| `yahoo_chart__BILL__5y.json` | 453 |
| `yahoo_chart__BIO-B__5y.json` | 455 |
| `yahoo_chart__BIO__5y.json` | 451 |
| `yahoo_chart__BIRK__5y.json` | 452 |
| `yahoo_chart__BJ__5y.json` | 449 |
| `yahoo_chart__BKAMF__5y.json` | 455 |
| `yahoo_chart__BKFAF__5y.json` | 455 |
| `yahoo_chart__BKFOF__5y.json` | 454 |
| `yahoo_chart__BKFPF__5y.json` | 454 |
| `yahoo_chart__BKNG__5y.json` | 453 |
| `yahoo_chart__BKR__5y.json` | 451 |
| `yahoo_chart__BLDR__5y.json` | 453 |
| `yahoo_chart__BLK__5y.json` | 451 |
| `yahoo_chart__BML-PG__5y.json` | 457 |
| `yahoo_chart__BML-PH__5y.json` | 457 |
| `yahoo_chart__BML-PJ__5y.json` | 457 |
| `yahoo_chart__BML-PL__5y.json` | 457 |
| `yahoo_chart__BMO__5y.json` | 451 |
| `yahoo_chart__BMRN__5y.json` | 453 |
| `yahoo_chart__BMY__5y.json` | 451 |
| `yahoo_chart__BNH__5y.json` | 451 |
| `yahoo_chart__BNJ__5y.json` | 451 |
| `yahoo_chart__BNKD__5y.json` | 452 |
| `yahoo_chart__BNKU__5y.json` | 452 |
| `yahoo_chart__BNS__5y.json` | 451 |
| `yahoo_chart__BNY-PK__5y.json` | 456 |
| `yahoo_chart__BNY__5y.json` | 451 |
| `yahoo_chart__BN__5y.json` | 449 |
| `yahoo_chart__BOKF__5y.json` | 453 |
| `yahoo_chart__BPAQF__5y.json` | 455 |
| `yahoo_chart__BPOP__5y.json` | 453 |
| `yahoo_chart__BPPFF__5y.json` | 452 |
| `yahoo_chart__BP__5y.json` | 449 |
| `yahoo_chart__BRBR__5y.json` | 453 |
| `yahoo_chart__BRCFF__5y.json` | 454 |
| `yahoo_chart__BRFAF__5y.json` | 453 |
| `yahoo_chart__BRK-A__5y.json` | 454 |
| `yahoo_chart__BRK-B__5y.json` | 455 |
| `yahoo_chart__BRKR__5y.json` | 453 |
| `yahoo_chart__BROS__5y.json` | 453 |
| `yahoo_chart__BRO__5y.json` | 451 |
| `yahoo_chart__BRPSF__5y.json` | 454 |
| `yahoo_chart__BRX__5y.json` | 451 |
| `yahoo_chart__BRZD__5y.json` | 451 |
| `yahoo_chart__BRZL__5y.json` | 451 |
| `yahoo_chart__BR__5y.json` | 449 |
| `yahoo_chart__BSX__5y.json` | 451 |
| `yahoo_chart__BSY__5y.json` | 451 |
| `yahoo_chart__BTAFF__5y.json` | 455 |
| `yahoo_chart__BTI__5y.json` | 451 |
| `yahoo_chart__BUDFF__5y.json` | 455 |
| `yahoo_chart__BUD__5y.json` | 451 |
| `yahoo_chart__BULZ__5y.json` | 453 |
| `yahoo_chart__BURL__5y.json` | 453 |
| `yahoo_chart__BWA__5y.json` | 451 |
| `yahoo_chart__BWXT__5y.json` | 453 |
| `yahoo_chart__BXP__5y.json` | 451 |
| `yahoo_chart__BX__5y.json` | 449 |
| `yahoo_chart__BYD__5y.json` | 451 |
| `yahoo_chart__B__5y.json` | 447 |
| `yahoo_chart__C-PN__5y.json` | 451 |
| `yahoo_chart__C-PR__5y.json` | 452 |
| `yahoo_chart__CABO__5y.json` | 453 |
| `yahoo_chart__CACC__5y.json` | 453 |
| `yahoo_chart__CACI__5y.json` | 453 |
| `yahoo_chart__CAG__5y.json` | 451 |
| `yahoo_chart__CAH__5y.json` | 451 |
| `yahoo_chart__CARD__5y.json` | 452 |
| `yahoo_chart__CARR__5y.json` | 453 |
| `yahoo_chart__CART__5y.json` | 452 |
| `yahoo_chart__CARU__5y.json` | 452 |
| `yahoo_chart__CAR__5y.json` | 451 |
| `yahoo_chart__CASY__5y.json` | 453 |
| `yahoo_chart__CAT__5y.json` | 451 |
| `yahoo_chart__CAVA__5y.json` | 452 |
| `yahoo_chart__CBOE__5y.json` | 453 |
| `yahoo_chart__CBRE__5y.json` | 453 |
| `yahoo_chart__CBSH__5y.json` | 453 |
| `yahoo_chart__CB__5y.json` | 449 |
| `yahoo_chart__CCC__5y.json` | 451 |
| `yahoo_chart__CCI__5y.json` | 451 |
| `yahoo_chart__CCK__5y.json` | 451 |
| `yahoo_chart__CCL__5y.json` | 451 |
| `yahoo_chart__CCZ__5y.json` | 451 |
| `yahoo_chart__CC__5y.json` | 449 |
| `yahoo_chart__CDNS__5y.json` | 453 |
| `yahoo_chart__CDW__5y.json` | 451 |
| `yahoo_chart__CEG__5y.json` | 451 |
| `yahoo_chart__CELG-RI__5y.json` | 457 |
| `yahoo_chart__CELH__5y.json` | 453 |
| `yahoo_chart__CERT__5y.json` | 453 |
| `yahoo_chart__CE__5y.json` | 449 |
| `yahoo_chart__CFG__5y.json` | 451 |
| `yahoo_chart__CFR__5y.json` | 451 |
| `yahoo_chart__CF__5y.json` | 449 |
| `yahoo_chart__CGNX__5y.json` | 453 |
| `yahoo_chart__CG__5y.json` | 449 |
| `yahoo_chart__CHDN__5y.json` | 453 |
| `yahoo_chart__CHD__5y.json` | 451 |
| `yahoo_chart__CHE__5y.json` | 451 |
| `yahoo_chart__CHH__5y.json` | 451 |
| `yahoo_chart__CHPT__5y.json` | 453 |
| `yahoo_chart__CHRD__5y.json` | 453 |
| `yahoo_chart__CHRW__5y.json` | 453 |
| `yahoo_chart__CHTR__5y.json` | 453 |
| `yahoo_chart__CIEN__5y.json` | 453 |
| `yahoo_chart__CINF__5y.json` | 453 |
| `yahoo_chart__CI__5y.json` | 449 |
| `yahoo_chart__CLF__5y.json` | 451 |
| `yahoo_chart__CLH__5y.json` | 451 |
| `yahoo_chart__CLVT__5y.json` | 453 |
| `yahoo_chart__CLX__5y.json` | 451 |
| `yahoo_chart__CL__5y.json` | 449 |
| `yahoo_chart__CMCSA__5y.json` | 455 |
| `yahoo_chart__CME__5y.json` | 451 |
| `yahoo_chart__CMG__5y.json` | 451 |
| `yahoo_chart__CMI__5y.json` | 451 |
| `yahoo_chart__CMS__5y.json` | 451 |
| `yahoo_chart__CM__5y.json` | 449 |
| `yahoo_chart__CNA__5y.json` | 451 |
| `yahoo_chart__CNC__5y.json` | 451 |
| `yahoo_chart__CNDIF__5y.json` | 454 |
| `yahoo_chart__CNH__5y.json` | 451 |
| `yahoo_chart__CNI__5y.json` | 451 |
| `yahoo_chart__CNM__5y.json` | 451 |
| `yahoo_chart__CNP__5y.json` | 451 |
| `yahoo_chart__CNQ__5y.json` | 451 |
| `yahoo_chart__CNXC__5y.json` | 453 |
| `yahoo_chart__COF-PI__5y.json` | 457 |
| `yahoo_chart__COF-PJ__5y.json` | 457 |
| `yahoo_chart__COF-PK__5y.json` | 457 |
| `yahoo_chart__COF-PL__5y.json` | 457 |
| `yahoo_chart__COF-PN__5y.json` | 457 |
| `yahoo_chart__COF__5y.json` | 451 |
| `yahoo_chart__COHR__5y.json` | 453 |
| `yahoo_chart__COIN__5y.json` | 453 |
| `yahoo_chart__COKE__5y.json` | 453 |
| `yahoo_chart__COLB__5y.json` | 453 |
| `yahoo_chart__COLD__5y.json` | 453 |
| `yahoo_chart__COLM__5y.json` | 453 |
| `yahoo_chart__COO__5y.json` | 451 |
| `yahoo_chart__COP__5y.json` | 451 |
| `yahoo_chart__COR__5y.json` | 451 |
| `yahoo_chart__COST__5y.json` | 453 |
| `yahoo_chart__COTY__5y.json` | 453 |
| `yahoo_chart__CPAY__5y.json` | 453 |
| `yahoo_chart__CPB__5y.json` | 451 |
| `yahoo_chart__CPNG__5y.json` | 453 |
| `yahoo_chart__CPRI__5y.json` | 453 |
| `yahoo_chart__CPRT__5y.json` | 453 |
| `yahoo_chart__CPT__5y.json` | 451 |
| `yahoo_chart__CP__5y.json` | 449 |
| `yahoo_chart__CRH__5y.json` | 451 |
| `yahoo_chart__CRI__5y.json` | 451 |
| `yahoo_chart__CRL__5y.json` | 451 |
| `yahoo_chart__CRM__5y.json` | 451 |
| `yahoo_chart__CROX__5y.json` | 453 |
| `yahoo_chart__CRUS__5y.json` | 453 |
| `yahoo_chart__CRWD__5y.json` | 453 |
| `yahoo_chart__CR__5y.json` | 448 |
| `yahoo_chart__CSCO__5y.json` | 453 |
| `yahoo_chart__CSGP__5y.json` | 453 |
| `yahoo_chart__CSL__5y.json` | 451 |
| `yahoo_chart__CSX__5y.json` | 451 |
| `yahoo_chart__CTAS__5y.json` | 453 |
| `yahoo_chart__CTSH__5y.json` | 453 |
| `yahoo_chart__CTVA__5y.json` | 453 |
| `yahoo_chart__CUBE__5y.json` | 453 |
| `yahoo_chart__CUZ__5y.json` | 451 |
| `yahoo_chart__CVE__5y.json` | 451 |
| `yahoo_chart__CVNA__5y.json` | 453 |
| `yahoo_chart__CVS__5y.json` | 451 |
| `yahoo_chart__CVX__5y.json` | 451 |
| `yahoo_chart__CWEN__5y.json` | 453 |
| `yahoo_chart__CW__5y.json` | 449 |
| `yahoo_chart__CXT__5y.json` | 451 |
| `yahoo_chart__CZR__5y.json` | 451 |
| `yahoo_chart__C__5y.json` | 447 |
| `yahoo_chart__DAL__5y.json` | 451 |
| `yahoo_chart__DAR__5y.json` | 451 |
| `yahoo_chart__DASH__5y.json` | 453 |
| `yahoo_chart__DBX__5y.json` | 451 |
| `yahoo_chart__DB__5y.json` | 449 |
| `yahoo_chart__DCI__5y.json` | 451 |
| `yahoo_chart__DDOG__5y.json` | 453 |
| `yahoo_chart__DDS__5y.json` | 451 |
| `yahoo_chart__DD__5y.json` | 449 |
| `yahoo_chart__DECK__5y.json` | 453 |
| `yahoo_chart__DEENF__5y.json` | 453 |
| `yahoo_chart__DELL__5y.json` | 453 |
| `yahoo_chart__DE__5y.json` | 449 |
| `yahoo_chart__DGP__5y.json` | 451 |
| `yahoo_chart__DGX__5y.json` | 451 |
| `yahoo_chart__DGZ__5y.json` | 451 |
| `yahoo_chart__DG__5y.json` | 449 |
| `yahoo_chart__DHI__5y.json` | 451 |
| `yahoo_chart__DHR__5y.json` | 451 |
| `yahoo_chart__DINO__5y.json` | 453 |
| `yahoo_chart__DIS__5y.json` | 451 |
| `yahoo_chart__DJT__5y.json` | 451 |
| `yahoo_chart__DKNG__5y.json` | 453 |
| `yahoo_chart__DKS__5y.json` | 451 |
| `yahoo_chart__DLB__5y.json` | 451 |
| `yahoo_chart__DLR-PJ__5y.json` | 457 |
| `yahoo_chart__DLR-PK__5y.json` | 457 |
| `yahoo_chart__DLR-PL__5y.json` | 457 |
| `yahoo_chart__DLR__5y.json` | 451 |
| `yahoo_chart__DLTR__5y.json` | 453 |
| `yahoo_chart__DNA__5y.json` | 451 |
| `yahoo_chart__DOCS__5y.json` | 453 |
| `yahoo_chart__DOCU__5y.json` | 453 |
| `yahoo_chart__DOC__5y.json` | 451 |
| `yahoo_chart__DOV__5y.json` | 451 |
| `yahoo_chart__DOW__5y.json` | 451 |
| `yahoo_chart__DOX__5y.json` | 451 |
| `yahoo_chart__DPZ__5y.json` | 451 |
| `yahoo_chart__DRI__5y.json` | 451 |
| `yahoo_chart__DRVN__5y.json` | 453 |
| `yahoo_chart__DTE__5y.json` | 451 |
| `yahoo_chart__DTM__5y.json` | 451 |
| `yahoo_chart__DT__5y.json` | 449 |
| `yahoo_chart__DUK-PA__5y.json` | 457 |
| `yahoo_chart__DUKB__5y.json` | 453 |
| `yahoo_chart__DUKU__5y.json` | 451 |
| `yahoo_chart__DUK__5y.json` | 451 |
| `yahoo_chart__DULL__5y.json` | 452 |
| `yahoo_chart__DUOL__5y.json` | 453 |
| `yahoo_chart__DVA__5y.json` | 451 |
| `yahoo_chart__DVN__5y.json` | 451 |
| `yahoo_chart__DV__5y.json` | 449 |
| `yahoo_chart__DXCM__5y.json` | 453 |
| `yahoo_chart__DXC__5y.json` | 451 |
| `yahoo_chart__DZZ__5y.json` | 451 |
| `yahoo_chart__D__5y.json` | 447 |
| `yahoo_chart__EBAY__5y.json` | 453 |
| `yahoo_chart__EBBGF__5y.json` | 455 |
| `yahoo_chart__EBBNF__5y.json` | 455 |
| `yahoo_chart__EBGEF__5y.json` | 455 |
| `yahoo_chart__EBRGF__5y.json` | 455 |
| `yahoo_chart__EBRZF__5y.json` | 455 |
| `yahoo_chart__ECG__5y.json` | 450 |
| `yahoo_chart__ECL__5y.json` | 451 |
| `yahoo_chart__ED__5y.json` | 449 |
| `yahoo_chart__EEFT__5y.json` | 453 |
| `yahoo_chart__EFX__5y.json` | 451 |
| `yahoo_chart__EGP__5y.json` | 451 |
| `yahoo_chart__EG__5y.json` | 449 |
| `yahoo_chart__EHC__5y.json` | 451 |
| `yahoo_chart__EIPAF__5y.json` | 455 |
| `yahoo_chart__EIX__5y.json` | 451 |
| `yahoo_chart__ELAN__5y.json` | 453 |
| `yahoo_chart__ELF__5y.json` | 451 |
| `yahoo_chart__ELS__5y.json` | 451 |
| `yahoo_chart__ELV__5y.json` | 451 |
| `yahoo_chart__EL__5y.json` | 449 |
| `yahoo_chart__EME__5y.json` | 451 |
| `yahoo_chart__EMN__5y.json` | 451 |
| `yahoo_chart__EMR__5y.json` | 451 |
| `yahoo_chart__ENBFF__5y.json` | 455 |
| `yahoo_chart__ENBGF__5y.json` | 454 |
| `yahoo_chart__ENBHF__5y.json` | 454 |
| `yahoo_chart__ENBMF__5y.json` | 454 |
| `yahoo_chart__ENBNF__5y.json` | 454 |
| `yahoo_chart__ENBOF__5y.json` | 454 |
| `yahoo_chart__ENBRF__5y.json` | 454 |
| `yahoo_chart__ENBSF__5y.json` | 452 |
| `yahoo_chart__ENB__5y.json` | 451 |
| `yahoo_chart__ENNPF__5y.json` | 455 |
| `yahoo_chart__ENOV__5y.json` | 453 |
| `yahoo_chart__ENPH__5y.json` | 453 |
| `yahoo_chart__ENTG__5y.json` | 453 |
| `yahoo_chart__EOG__5y.json` | 451 |
| `yahoo_chart__EP-PC__5y.json` | 453 |
| `yahoo_chart__EPAM__5y.json` | 453 |
| `yahoo_chart__EPD__5y.json` | 451 |
| `yahoo_chart__EPR__5y.json` | 451 |
| `yahoo_chart__EQH__5y.json` | 451 |
| `yahoo_chart__EQIX__5y.json` | 453 |
| `yahoo_chart__EQNR__5y.json` | 453 |
| `yahoo_chart__EQT__5y.json` | 451 |
| `yahoo_chart__ERIE__5y.json` | 453 |
| `yahoo_chart__ESAB__5y.json` | 453 |
| `yahoo_chart__ESI__5y.json` | 451 |
| `yahoo_chart__ESS__5y.json` | 451 |
| `yahoo_chart__ESTC__5y.json` | 453 |
| `yahoo_chart__ES__5y.json` | 449 |
| `yahoo_chart__ET-PI__5y.json` | 454 |
| `yahoo_chart__ETN__5y.json` | 451 |
| `yahoo_chart__ETR__5y.json` | 451 |
| `yahoo_chart__ETSY__5y.json` | 453 |
| `yahoo_chart__ET__5y.json` | 449 |
| `yahoo_chart__EVRG__5y.json` | 453 |
| `yahoo_chart__EVR__5y.json` | 451 |
| `yahoo_chart__EWBC__5y.json` | 453 |
| `yahoo_chart__EW__5y.json` | 449 |
| `yahoo_chart__EXC__5y.json` | 451 |
| `yahoo_chart__EXEL__5y.json` | 453 |
| `yahoo_chart__EXE__5y.json` | 451 |
| `yahoo_chart__EXPD__5y.json` | 453 |
| `yahoo_chart__EXPE__5y.json` | 453 |
| `yahoo_chart__EXP__5y.json` | 451 |
| `yahoo_chart__EXR__5y.json` | 451 |
| `yahoo_chart__E__5y.json` | 447 |
| `yahoo_chart__F-PB__5y.json` | 451 |
| `yahoo_chart__F-PC__5y.json` | 451 |
| `yahoo_chart__F-PD__5y.json` | 451 |
| `yahoo_chart__FAF__5y.json` | 451 |
| `yahoo_chart__FANG__5y.json` | 453 |
| `yahoo_chart__FAST__5y.json` | 453 |
| `yahoo_chart__FBIN__5y.json` | 453 |
| `yahoo_chart__FCNCA__5y.json` | 455 |
| `yahoo_chart__FCN__5y.json` | 451 |
| `yahoo_chart__FCX__5y.json` | 451 |
| `yahoo_chart__FDS__5y.json` | 451 |
| `yahoo_chart__FDX__5y.json` | 451 |
| `yahoo_chart__FERG__5y.json` | 453 |
| `yahoo_chart__FE__5y.json` | 449 |
| `yahoo_chart__FFIV__5y.json` | 453 |
| `yahoo_chart__FHB__5y.json` | 451 |
| `yahoo_chart__FHN__5y.json` | 451 |
| `yahoo_chart__FICO__5y.json` | 453 |
| `yahoo_chart__FISV__5y.json` | 453 |
| `yahoo_chart__FIS__5y.json` | 451 |
| `yahoo_chart__FITB__5y.json` | 453 |
| `yahoo_chart__FIVE__5y.json` | 453 |
| `yahoo_chart__FIVN__5y.json` | 453 |
| `yahoo_chart__FIX__5y.json` | 451 |
| `yahoo_chart__FLG__5y.json` | 451 |
| `yahoo_chart__FLO__5y.json` | 451 |
| `yahoo_chart__FLS__5y.json` | 451 |
| `yahoo_chart__FLYD__5y.json` | 452 |
| `yahoo_chart__FLYU__5y.json` | 453 |
| `yahoo_chart__FMC__5y.json` | 451 |
| `yahoo_chart__FNB__5y.json` | 451 |
| `yahoo_chart__FND__5y.json` | 451 |
| `yahoo_chart__FNF__5y.json` | 451 |
| `yahoo_chart__FNGD__5y.json` | 452 |
| `yahoo_chart__FNGO__5y.json` | 453 |
| `yahoo_chart__FNGS__5y.json` | 453 |
| `yahoo_chart__FNGU__5y.json` | 452 |
| `yahoo_chart__FNV__5y.json` | 451 |
| `yahoo_chart__FOUR__5y.json` | 453 |
| `yahoo_chart__FOXA__5y.json` | 453 |
| `yahoo_chart__FOX__5y.json` | 451 |
| `yahoo_chart__FRPT__5y.json` | 453 |
| `yahoo_chart__FRT__5y.json` | 451 |
| `yahoo_chart__FR__5y.json` | 449 |
| `yahoo_chart__FSLR__5y.json` | 453 |
| `yahoo_chart__FTI__5y.json` | 451 |
| `yahoo_chart__FTNT__5y.json` | 453 |
| `yahoo_chart__FTRE__5y.json` | 452 |
| `yahoo_chart__FTV__5y.json` | 451 |
| `yahoo_chart__FWONA__5y.json` | 455 |
| `yahoo_chart__FWONK__5y.json` | 455 |
| `yahoo_chart__F__5y.json` | 447 |
| `yahoo_chart__GAP__5y.json` | 451 |
| `yahoo_chart__GDDY__5y.json` | 453 |
| `yahoo_chart__GDXD__5y.json` | 452 |
| `yahoo_chart__GDXU__5y.json` | 453 |
| `yahoo_chart__GD__5y.json` | 449 |
| `yahoo_chart__GEHC__5y.json` | 452 |
| `yahoo_chart__GEN__5y.json` | 451 |
| `yahoo_chart__GEV__5y.json` | 450 |
| `yahoo_chart__GE__5y.json` | 449 |
| `yahoo_chart__GFS__5y.json` | 451 |
| `yahoo_chart__GGG__5y.json` | 451 |
| `yahoo_chart__GILD__5y.json` | 453 |
| `yahoo_chart__GIS__5y.json` | 451 |
| `yahoo_chart__GLAXF__5y.json` | 455 |
| `yahoo_chart__GLOB__5y.json` | 453 |
| `yahoo_chart__GLPI__5y.json` | 453 |
| `yahoo_chart__GLW__5y.json` | 451 |
| `yahoo_chart__GL__5y.json` | 449 |
| `yahoo_chart__GMED__5y.json` | 453 |
| `yahoo_chart__GME__5y.json` | 451 |
| `yahoo_chart__GM__5y.json` | 449 |
| `yahoo_chart__GNRC__5y.json` | 453 |
| `yahoo_chart__GNTX__5y.json` | 453 |
| `yahoo_chart__GOOGL__5y.json` | 455 |
| `yahoo_chart__GOOGM__5y.json` | 453 |
| `yahoo_chart__GOOGN__5y.json` | 453 |
| `yahoo_chart__GOOG__5y.json` | 453 |
| `yahoo_chart__GO__5y.json` | 449 |
| `yahoo_chart__GPC__5y.json` | 451 |
| `yahoo_chart__GPK__5y.json` | 451 |
| `yahoo_chart__GPN__5y.json` | 451 |
| `yahoo_chart__GRAL__5y.json` | 452 |
| `yahoo_chart__GRMN__5y.json` | 453 |
| `yahoo_chart__GS-PA__5y.json` | 455 |
| `yahoo_chart__GS-PC__5y.json` | 455 |
| `yahoo_chart__GS-PD__5y.json` | 455 |
| `yahoo_chart__GSCE__5y.json` | 453 |
| `yahoo_chart__GSK__5y.json` | 451 |
| `yahoo_chart__GS__5y.json` | 449 |
| `yahoo_chart__GTES__5y.json` | 453 |
| `yahoo_chart__GTLB__5y.json` | 453 |
| `yahoo_chart__GTM__5y.json` | 451 |
| `yahoo_chart__GWRE__5y.json` | 453 |
| `yahoo_chart__GWW__5y.json` | 451 |
| `yahoo_chart__GXO__5y.json` | 451 |
| `yahoo_chart__G__5y.json` | 447 |
| `yahoo_chart__HAL__5y.json` | 451 |
| `yahoo_chart__HAS__5y.json` | 451 |
| `yahoo_chart__HAYW__5y.json` | 453 |
| `yahoo_chart__HBAN__5y.json` | 453 |
| `yahoo_chart__HBCYF__5y.json` | 455 |
| `yahoo_chart__HCA__5y.json` | 451 |
| `yahoo_chart__HDB__5y.json` | 451 |
| `yahoo_chart__HD__5y.json` | 449 |
| `yahoo_chart__HEI-A__5y.json` | 455 |
| `yahoo_chart__HEI__5y.json` | 451 |
| `yahoo_chart__HE__5y.json` | 449 |
| `yahoo_chart__HHH__5y.json` | 451 |
| `yahoo_chart__HIG__5y.json` | 451 |
| `yahoo_chart__HII__5y.json` | 451 |
| `yahoo_chart__HIW__5y.json` | 451 |
| `yahoo_chart__HLI__5y.json` | 451 |
| `yahoo_chart__HLT__5y.json` | 451 |
| `yahoo_chart__HOG__5y.json` | 451 |
| `yahoo_chart__HONA__5y.json` | 451 |
| `yahoo_chart__HON__5y.json` | 451 |
| `yahoo_chart__HOOD__5y.json` | 453 |
| `yahoo_chart__HPE-PC__5y.json` | 456 |
| `yahoo_chart__HPE__5y.json` | 451 |
| `yahoo_chart__HPQ__5y.json` | 451 |
| `yahoo_chart__HRB__5y.json` | 451 |
| `yahoo_chart__HRL__5y.json` | 451 |
| `yahoo_chart__HR__5y.json` | 449 |
| `yahoo_chart__HSBC__5y.json` | 453 |
| `yahoo_chart__HSIC__5y.json` | 453 |
| `yahoo_chart__HST__5y.json` | 451 |
| `yahoo_chart__HSY__5y.json` | 451 |
| `yahoo_chart__HTHIF__5y.json` | 455 |
| `yahoo_chart__HTHIY__5y.json` | 455 |
| `yahoo_chart__HTZ__5y.json` | 451 |
| `yahoo_chart__HUBB__5y.json` | 453 |
| `yahoo_chart__HUBS__5y.json` | 453 |
| `yahoo_chart__HUM__5y.json` | 451 |
| `yahoo_chart__HUN__5y.json` | 451 |
| `yahoo_chart__HWM__5y.json` | 451 |
| `yahoo_chart__HXL__5y.json` | 451 |
| `yahoo_chart__HYGD__5y.json` | 451 |
| `yahoo_chart__HYGU__5y.json` | 451 |
| `yahoo_chart__H__5y.json` | 447 |
| `yahoo_chart__IART__5y.json` | 453 |
| `yahoo_chart__IBKR__5y.json` | 453 |
| `yahoo_chart__IBM__5y.json` | 451 |
| `yahoo_chart__ICE__5y.json` | 451 |
| `yahoo_chart__ICLR__5y.json` | 453 |
| `yahoo_chart__ICUI__5y.json` | 453 |
| `yahoo_chart__IDA__5y.json` | 451 |
| `yahoo_chart__IDXX__5y.json` | 453 |
| `yahoo_chart__IEX__5y.json` | 451 |
| `yahoo_chart__IFF__5y.json` | 451 |
| `yahoo_chart__ILMN__5y.json` | 453 |
| `yahoo_chart__INCY__5y.json` | 453 |
| `yahoo_chart__INGM__5y.json` | 452 |
| `yahoo_chart__INGR__5y.json` | 453 |
| `yahoo_chart__INGVF__5y.json` | 455 |
| `yahoo_chart__ING__5y.json` | 451 |
| `yahoo_chart__INSP__5y.json` | 453 |
| `yahoo_chart__INTC__5y.json` | 453 |
| `yahoo_chart__INTU__5y.json` | 453 |
| `yahoo_chart__INVH__5y.json` | 453 |
| `yahoo_chart__IONS__5y.json` | 453 |
| `yahoo_chart__IPGP__5y.json` | 453 |
| `yahoo_chart__IP__5y.json` | 449 |
| `yahoo_chart__IQV__5y.json` | 451 |
| `yahoo_chart__IRDM__5y.json` | 453 |
| `yahoo_chart__IRM__5y.json` | 451 |
| `yahoo_chart__IR__5y.json` | 449 |
| `yahoo_chart__ISRG__5y.json` | 453 |
| `yahoo_chart__ITT__5y.json` | 451 |
| `yahoo_chart__ITUB__5y.json` | 453 |
| `yahoo_chart__ITW__5y.json` | 451 |
| `yahoo_chart__IT__5y.json` | 449 |
| `yahoo_chart__IVZ__5y.json` | 451 |
| `yahoo_chart__JAZZ__5y.json` | 453 |
| `yahoo_chart__JBHT__5y.json` | 453 |
| `yahoo_chart__JBL__5y.json` | 451 |
| `yahoo_chart__JCI__5y.json` | 451 |
| `yahoo_chart__JEF__5y.json` | 451 |
| `yahoo_chart__JETD__5y.json` | 452 |
| `yahoo_chart__JETU__5y.json` | 452 |
| `yahoo_chart__JKHY__5y.json` | 453 |
| `yahoo_chart__JLL__5y.json` | 451 |
| `yahoo_chart__JNJ__5y.json` | 451 |
| `yahoo_chart__JPM-PC__5y.json` | 457 |
| `yahoo_chart__JPM-PD__5y.json` | 457 |
| `yahoo_chart__JPM-PJ__5y.json` | 457 |
| `yahoo_chart__JPM-PK__5y.json` | 457 |
| `yahoo_chart__JPM-PL__5y.json` | 457 |
| `yahoo_chart__JPM-PM__5y.json` | 457 |
| `yahoo_chart__JPM__5y.json` | 451 |
| `yahoo_chart__JPND__5y.json` | 451 |
| `yahoo_chart__JPNU__5y.json` | 451 |
| `yahoo_chart__J__5y.json` | 447 |
| `yahoo_chart__KBR__5y.json` | 451 |
| `yahoo_chart__KDP__5y.json` | 451 |
| `yahoo_chart__KD__5y.json` | 449 |
| `yahoo_chart__KEX__5y.json` | 451 |
| `yahoo_chart__KEYS__5y.json` | 453 |
| `yahoo_chart__KEY__5y.json` | 451 |
| `yahoo_chart__KHC__5y.json` | 451 |
| `yahoo_chart__KIM__5y.json` | 451 |
| `yahoo_chart__KKR-PD__5y.json` | 456 |
| `yahoo_chart__KKRS__5y.json` | 453 |
| `yahoo_chart__KKRT__5y.json` | 452 |
| `yahoo_chart__KKR__5y.json` | 451 |
| `yahoo_chart__KLAC__5y.json` | 453 |
| `yahoo_chart__KMB__5y.json` | 451 |
| `yahoo_chart__KMI__5y.json` | 451 |
| `yahoo_chart__KMPR__5y.json` | 453 |
| `yahoo_chart__KMX__5y.json` | 451 |
| `yahoo_chart__KNSL__5y.json` | 453 |
| `yahoo_chart__KNX__5y.json` | 451 |
| `yahoo_chart__KO__5y.json` | 449 |
| `yahoo_chart__KRC__5y.json` | 451 |
| `yahoo_chart__KR__5y.json` | 449 |
| `yahoo_chart__KSS__5y.json` | 451 |
| `yahoo_chart__KVUE__5y.json` | 452 |
| `yahoo_chart__LAD__5y.json` | 451 |
| `yahoo_chart__LAMR__5y.json` | 453 |
| `yahoo_chart__LAZ__5y.json` | 451 |
| `yahoo_chart__LBRDA__5y.json` | 455 |
| `yahoo_chart__LBTYA__5y.json` | 455 |
| `yahoo_chart__LBTYB__5y.json` | 455 |
| `yahoo_chart__LBTYK__5y.json` | 455 |
| `yahoo_chart__LCID__5y.json` | 453 |
| `yahoo_chart__LDOS__5y.json` | 453 |
| `yahoo_chart__LEA__5y.json` | 451 |
| `yahoo_chart__LECO__5y.json` | 453 |
| `yahoo_chart__LEN-B__5y.json` | 455 |
| `yahoo_chart__LEN__5y.json` | 451 |
| `yahoo_chart__LFUS__5y.json` | 453 |
| `yahoo_chart__LHX__5y.json` | 451 |
| `yahoo_chart__LH__5y.json` | 449 |
| `yahoo_chart__LII__5y.json` | 451 |
| `yahoo_chart__LINE__5y.json` | 452 |
| `yahoo_chart__LIN__5y.json` | 451 |
| `yahoo_chart__LITE__5y.json` | 453 |
| `yahoo_chart__LKQ__5y.json` | 451 |
| `yahoo_chart__LLDTF__5y.json` | 455 |
| `yahoo_chart__LLOBF__5y.json` | 455 |
| `yahoo_chart__LLYVA__5y.json` | 454 |
| `yahoo_chart__LLYVK__5y.json` | 454 |
| `yahoo_chart__LLY__5y.json` | 451 |
| `yahoo_chart__LMT__5y.json` | 451 |
| `yahoo_chart__LNC__5y.json` | 451 |
| `yahoo_chart__LNG__5y.json` | 451 |
| `yahoo_chart__LNT__5y.json` | 451 |
| `yahoo_chart__LNWO__5y.json` | 453 |
| `yahoo_chart__LOAR__5y.json` | 452 |
| `yahoo_chart__LOPE__5y.json` | 453 |
| `yahoo_chart__LOW__5y.json` | 451 |
| `yahoo_chart__LPLA__5y.json` | 453 |
| `yahoo_chart__LPX__5y.json` | 451 |
| `yahoo_chart__LQDD__5y.json` | 451 |
| `yahoo_chart__LQDU__5y.json` | 451 |
| `yahoo_chart__LRCX__5y.json` | 453 |
| `yahoo_chart__LSCC__5y.json` | 453 |
| `yahoo_chart__LSTR__5y.json` | 453 |
| `yahoo_chart__LULU__5y.json` | 453 |
| `yahoo_chart__LUV__5y.json` | 451 |
| `yahoo_chart__LVS__5y.json` | 451 |
| `yahoo_chart__LW__5y.json` | 449 |
| `yahoo_chart__LYB__5y.json` | 451 |
| `yahoo_chart__LYFT__5y.json` | 453 |
| `yahoo_chart__LYG__5y.json` | 451 |
| `yahoo_chart__LYV__5y.json` | 451 |
| `yahoo_chart__L__5y.json` | 447 |
| `yahoo_chart__MAA__5y.json` | 451 |
| `yahoo_chart__MANH__5y.json` | 453 |
| `yahoo_chart__MAN__5y.json` | 451 |
| `yahoo_chart__MAR__5y.json` | 451 |
| `yahoo_chart__MAS__5y.json` | 451 |
| `yahoo_chart__MAT__5y.json` | 451 |
| `yahoo_chart__MA__5y.json` | 449 |
| `yahoo_chart__MBFJF__5y.json` | 455 |
| `yahoo_chart__MCD__5y.json` | 451 |
| `yahoo_chart__MCHP__5y.json` | 453 |
| `yahoo_chart__MCK__5y.json` | 451 |
| `yahoo_chart__MCO__5y.json` | 451 |
| `yahoo_chart__MDB__5y.json` | 451 |
| `yahoo_chart__MDLZ__5y.json` | 453 |
| `yahoo_chart__MDT__5y.json` | 451 |
| `yahoo_chart__MDU__5y.json` | 451 |
| `yahoo_chart__MEDP__5y.json` | 453 |
| `yahoo_chart__MELI__5y.json` | 453 |
| `yahoo_chart__MER-PK__5y.json` | 455 |
| `yahoo_chart__MET-PA__5y.json` | 457 |
| `yahoo_chart__MET-PE__5y.json` | 457 |
| `yahoo_chart__MET-PF__5y.json` | 457 |
| `yahoo_chart__META__5y.json` | 453 |
| `yahoo_chart__MET__5y.json` | 451 |
| `yahoo_chart__MFC__5y.json` | 451 |
| `yahoo_chart__MFG__5y.json` | 451 |
| `yahoo_chart__MGM__5y.json` | 451 |
| `yahoo_chart__MHK__5y.json` | 451 |
| `yahoo_chart__MIDD__5y.json` | 453 |
| `yahoo_chart__MKC-V__5y.json` | 455 |
| `yahoo_chart__MKC__5y.json` | 451 |
| `yahoo_chart__MKL__5y.json` | 451 |
| `yahoo_chart__MKSI__5y.json` | 453 |
| `yahoo_chart__MKTX__5y.json` | 453 |
| `yahoo_chart__MLM__5y.json` | 451 |
| `yahoo_chart__MMM__5y.json` | 451 |
| `yahoo_chart__MNGU__5y.json` | 451 |
| `yahoo_chart__MNLCF__5y.json` | 454 |
| `yahoo_chart__MNQFF__5y.json` | 455 |
| `yahoo_chart__MNST__5y.json` | 453 |
| `yahoo_chart__MNUFF__5y.json` | 455 |
| `yahoo_chart__MNUPF__5y.json` | 453 |
| `yahoo_chart__MOH__5y.json` | 451 |
| `yahoo_chart__MORN__5y.json` | 453 |
| `yahoo_chart__MOS__5y.json` | 451 |
| `yahoo_chart__MO__5y.json` | 449 |
| `yahoo_chart__MPC__5y.json` | 451 |
| `yahoo_chart__MPLX__5y.json` | 453 |
| `yahoo_chart__MPT__5y.json` | 451 |
| `yahoo_chart__MPWR__5y.json` | 453 |
| `yahoo_chart__MP__5y.json` | 449 |
| `yahoo_chart__MRCY__5y.json` | 453 |
| `yahoo_chart__MRK__5y.json` | 451 |
| `yahoo_chart__MRNA__5y.json` | 453 |
| `yahoo_chart__MRSH__5y.json` | 453 |
| `yahoo_chart__MRVI__5y.json` | 453 |
| `yahoo_chart__MRVL__5y.json` | 453 |
| `yahoo_chart__MS-PA__5y.json` | 455 |
| `yahoo_chart__MS-PE__5y.json` | 455 |
| `yahoo_chart__MS-PF__5y.json` | 455 |
| `yahoo_chart__MS-PI__5y.json` | 455 |
| `yahoo_chart__MS-PK__5y.json` | 455 |
| `yahoo_chart__MS-PL__5y.json` | 455 |
| `yahoo_chart__MS-PO__5y.json` | 455 |
| `yahoo_chart__MS-PP__5y.json` | 455 |
| `yahoo_chart__MS-PQ__5y.json` | 454 |
| `yahoo_chart__MSA__5y.json` | 451 |
| `yahoo_chart__MSCI__5y.json` | 453 |
| `yahoo_chart__MSFT__5y.json` | 453 |
| `yahoo_chart__MSGS__5y.json` | 453 |
| `yahoo_chart__MSI__5y.json` | 451 |
| `yahoo_chart__MSM__5y.json` | 451 |
| `yahoo_chart__MSTR__5y.json` | 453 |
| `yahoo_chart__MS__5y.json` | 449 |
| `yahoo_chart__MTB__5y.json` | 451 |
| `yahoo_chart__MTCH__5y.json` | 453 |
| `yahoo_chart__MTDR__5y.json` | 453 |
| `yahoo_chart__MTD__5y.json` | 451 |
| `yahoo_chart__MTG__5y.json` | 451 |
| `yahoo_chart__MTN__5y.json` | 451 |
| `yahoo_chart__MTSI__5y.json` | 453 |
| `yahoo_chart__MTZ__5y.json` | 451 |
| `yahoo_chart__MT__5y.json` | 449 |
| `yahoo_chart__MUFG__5y.json` | 453 |
| `yahoo_chart__MUSA__5y.json` | 453 |
| `yahoo_chart__MU__5y.json` | 449 |
| `yahoo_chart__MZHOF__5y.json` | 455 |
| `yahoo_chart__M__5y.json` | 447 |
| `yahoo_chart__NATL__5y.json` | 452 |
| `yahoo_chart__NBIS__5y.json` | 452 |
| `yahoo_chart__NBIX__5y.json` | 453 |
| `yahoo_chart__NCLH__5y.json` | 453 |
| `yahoo_chart__NCNO__5y.json` | 453 |
| `yahoo_chart__NDAQ__5y.json` | 453 |
| `yahoo_chart__NDSN__5y.json` | 453 |
| `yahoo_chart__NEE-PN__5y.json` | 455 |
| `yahoo_chart__NEE-PS__5y.json` | 456 |
| `yahoo_chart__NEE-PT__5y.json` | 456 |
| `yahoo_chart__NEE-PU__5y.json` | 455 |
| `yahoo_chart__NEE-PV__5y.json` | 456 |
| `yahoo_chart__NEE-PW__5y.json` | 455 |
| `yahoo_chart__NEE__5y.json` | 451 |
| `yahoo_chart__NEMCL__5y.json` | 454 |
| `yahoo_chart__NEM__5y.json` | 451 |
| `yahoo_chart__NETTF__5y.json` | 455 |
| `yahoo_chart__NET__5y.json` | 451 |
| `yahoo_chart__NEU__5y.json` | 451 |
| `yahoo_chart__NEWEN__5y.json` | 454 |
| `yahoo_chart__NFE__5y.json` | 451 |
| `yahoo_chart__NFG__5y.json` | 451 |
| `yahoo_chart__NFLX__5y.json` | 453 |
| `yahoo_chart__NGGTF__5y.json` | 455 |
| `yahoo_chart__NGG__5y.json` | 451 |
| `yahoo_chart__NI__5y.json` | 449 |
| `yahoo_chart__NKE__5y.json` | 451 |
| `yahoo_chart__NLOP__5y.json` | 452 |
| `yahoo_chart__NLY__5y.json` | 451 |
| `yahoo_chart__NMKBP__5y.json` | 455 |
| `yahoo_chart__NMKCP__5y.json` | 455 |
| `yahoo_chart__NMPWP__5y.json` | 454 |
| `yahoo_chart__NNN__5y.json` | 451 |
| `yahoo_chart__NOC__5y.json` | 451 |
| `yahoo_chart__NOKBF__5y.json` | 455 |
| `yahoo_chart__NOK__5y.json` | 451 |
| `yahoo_chart__NONOF__5y.json` | 455 |
| `yahoo_chart__NOV__5y.json` | 451 |
| `yahoo_chart__NOW__5y.json` | 451 |
| `yahoo_chart__NRGD__5y.json` | 452 |
| `yahoo_chart__NRGU__5y.json` | 452 |
| `yahoo_chart__NRG__5y.json` | 451 |
| `yahoo_chart__NSC__5y.json` | 451 |
| `yahoo_chart__NTAP__5y.json` | 453 |
| `yahoo_chart__NTES__5y.json` | 453 |
| `yahoo_chart__NTNX__5y.json` | 453 |
| `yahoo_chart__NTRA__5y.json` | 453 |
| `yahoo_chart__NTRS__5y.json` | 453 |
| `yahoo_chart__NUE__5y.json` | 451 |
| `yahoo_chart__NU__5y.json` | 449 |
| `yahoo_chart__NVCR__5y.json` | 453 |
| `yahoo_chart__NVDA__5y.json` | 453 |
| `yahoo_chart__NVO__5y.json` | 451 |
| `yahoo_chart__NVR__5y.json` | 451 |
| `yahoo_chart__NVSEF__5y.json` | 455 |
| `yahoo_chart__NVST__5y.json` | 453 |
| `yahoo_chart__NVS__5y.json` | 451 |
| `yahoo_chart__NVT__5y.json` | 451 |
| `yahoo_chart__NWG__5y.json` | 451 |
| `yahoo_chart__NWL__5y.json` | 451 |
| `yahoo_chart__NWSA__5y.json` | 453 |
| `yahoo_chart__NWS__5y.json` | 451 |
| `yahoo_chart__NXPI__5y.json` | 453 |
| `yahoo_chart__NXST__5y.json` | 453 |
| `yahoo_chart__NYT__5y.json` | 451 |
| `yahoo_chart__OC__5y.json` | 449 |
| `yahoo_chart__ODFL__5y.json` | 453 |
| `yahoo_chart__OGE__5y.json` | 451 |
| `yahoo_chart__OGN__5y.json` | 451 |
| `yahoo_chart__OHI__5y.json` | 451 |
| `yahoo_chart__OILD__5y.json` | 453 |
| `yahoo_chart__OILU__5y.json` | 453 |
| `yahoo_chart__OKE__5y.json` | 451 |
| `yahoo_chart__OKTA__5y.json` | 453 |
| `yahoo_chart__OLED__5y.json` | 453 |
| `yahoo_chart__OLLI__5y.json` | 453 |
| `yahoo_chart__OLN__5y.json` | 451 |
| `yahoo_chart__OLOXF__5y.json` | 454 |
| `yahoo_chart__OMC__5y.json` | 451 |
| `yahoo_chart__OMF__5y.json` | 451 |
| `yahoo_chart__ONTO__5y.json` | 453 |
| `yahoo_chart__ON__5y.json` | 449 |
| `yahoo_chart__ORCL-PD__5y.json` | 458 |
| `yahoo_chart__ORCL__5y.json` | 453 |
| `yahoo_chart__ORI__5y.json` | 451 |
| `yahoo_chart__ORLY__5y.json` | 453 |
| `yahoo_chart__OSK__5y.json` | 451 |
| `yahoo_chart__OTIS__5y.json` | 453 |
| `yahoo_chart__OVV__5y.json` | 451 |
| `yahoo_chart__OWL__5y.json` | 451 |
| `yahoo_chart__OXY-WT__5y.json` | 455 |
| `yahoo_chart__OXY__5y.json` | 451 |
| `yahoo_chart__OZK__5y.json` | 451 |
| `yahoo_chart__O__5y.json` | 447 |
| `yahoo_chart__PAG__5y.json` | 451 |
| `yahoo_chart__PANW__5y.json` | 453 |
| `yahoo_chart__PARA__5y.json` | 452 |
| `yahoo_chart__PATH__5y.json` | 453 |
| `yahoo_chart__PAYC__5y.json` | 453 |
| `yahoo_chart__PAYX__5y.json` | 453 |
| `yahoo_chart__PBR-A__5y.json` | 455 |
| `yahoo_chart__PBR__5y.json` | 451 |
| `yahoo_chart__PB__5y.json` | 449 |
| `yahoo_chart__PCAR__5y.json` | 453 |
| `yahoo_chart__PCG__5y.json` | 451 |
| `yahoo_chart__PCOR__5y.json` | 453 |
| `yahoo_chart__PCTY__5y.json` | 453 |
| `yahoo_chart__PDD__5y.json` | 451 |
| `yahoo_chart__PEGA__5y.json` | 453 |
| `yahoo_chart__PEG__5y.json` | 451 |
| `yahoo_chart__PENN__5y.json` | 453 |
| `yahoo_chart__PEN__5y.json` | 451 |
| `yahoo_chart__PEP__5y.json` | 451 |
| `yahoo_chart__PFE__5y.json` | 451 |
| `yahoo_chart__PFGC__5y.json` | 453 |
| `yahoo_chart__PFG__5y.json` | 451 |
| `yahoo_chart__PGR__5y.json` | 451 |
| `yahoo_chart__PG__5y.json` | 449 |
| `yahoo_chart__PHIN__5y.json` | 452 |
| `yahoo_chart__PHM__5y.json` | 451 |
| `yahoo_chart__PH__5y.json` | 449 |
| `yahoo_chart__PII__5y.json` | 451 |
| `yahoo_chart__PINC__5y.json` | 451 |
| `yahoo_chart__PINS__5y.json` | 453 |
| `yahoo_chart__PKG__5y.json` | 451 |
| `yahoo_chart__PK__5y.json` | 449 |
| `yahoo_chart__PLDGP__5y.json` | 455 |
| `yahoo_chart__PLD__5y.json` | 451 |
| `yahoo_chart__PLNT__5y.json` | 453 |
| `yahoo_chart__PLTK__5y.json` | 453 |
| `yahoo_chart__PLTR__5y.json` | 453 |
| `yahoo_chart__PLUG__5y.json` | 453 |
| `yahoo_chart__PM__5y.json` | 449 |
| `yahoo_chart__PNC__5y.json` | 451 |
| `yahoo_chart__PNFP__5y.json` | 453 |
| `yahoo_chart__PNR__5y.json` | 451 |
| `yahoo_chart__PNW__5y.json` | 451 |
| `yahoo_chart__PODD__5y.json` | 453 |
| `yahoo_chart__POOL__5y.json` | 453 |
| `yahoo_chart__POST__5y.json` | 453 |
| `yahoo_chart__PPC__5y.json` | 451 |
| `yahoo_chart__PPG__5y.json` | 451 |
| `yahoo_chart__PPLI__5y.json` | 453 |
| `yahoo_chart__PPL__5y.json` | 451 |
| `yahoo_chart__PRGO__5y.json` | 453 |
| `yahoo_chart__PRI__5y.json` | 451 |
| `yahoo_chart__PRU__5y.json` | 451 |
| `yahoo_chart__PR__5y.json` | 449 |
| `yahoo_chart__PSA-PF__5y.json` | 457 |
| `yahoo_chart__PSA-PG__5y.json` | 457 |
| `yahoo_chart__PSA-PH__5y.json` | 457 |
| `yahoo_chart__PSA-PI__5y.json` | 457 |
| `yahoo_chart__PSA-PJ__5y.json` | 457 |
| `yahoo_chart__PSA-PK__5y.json` | 457 |
| `yahoo_chart__PSA-PL__5y.json` | 457 |
| `yahoo_chart__PSA-PM__5y.json` | 457 |
| `yahoo_chart__PSA-PN__5y.json` | 457 |
| `yahoo_chart__PSA-PO__5y.json` | 457 |
| `yahoo_chart__PSA-PP__5y.json` | 457 |
| `yahoo_chart__PSA-PQ__5y.json` | 457 |
| `yahoo_chart__PSA-PR__5y.json` | 457 |
| `yahoo_chart__PSA-PS__5y.json` | 457 |
| `yahoo_chart__PSA-PT__5y.json` | 455 |
| `yahoo_chart__PSA-PU__5y.json` | 455 |
| `yahoo_chart__PSA__5y.json` | 451 |
| `yahoo_chart__PSKY__5y.json` | 453 |
| `yahoo_chart__PSN__5y.json` | 451 |
| `yahoo_chart__PSX__5y.json` | 451 |
| `yahoo_chart__PTC__5y.json` | 451 |
| `yahoo_chart__PTON__5y.json` | 453 |
| `yahoo_chart__PVH__5y.json` | 451 |
| `yahoo_chart__PWR__5y.json` | 451 |
| `yahoo_chart__PYPL__5y.json` | 453 |
| `yahoo_chart__P__5y.json` | 447 |
| `yahoo_chart__QCOM__5y.json` | 453 |
| `yahoo_chart__QDEL__5y.json` | 453 |
| `yahoo_chart__QGEN__5y.json` | 453 |
| `yahoo_chart__QRVO__5y.json` | 453 |
| `yahoo_chart__QS__5y.json` | 449 |
| `yahoo_chart__RACE__5y.json` | 453 |
| `yahoo_chart__RARE__5y.json` | 453 |
| `yahoo_chart__RBA__5y.json` | 451 |
| `yahoo_chart__RBC__5y.json` | 451 |
| `yahoo_chart__RBLX__5y.json` | 453 |
| `yahoo_chart__RBSPF__5y.json` | 455 |
| `yahoo_chart__RCL__5y.json` | 451 |
| `yahoo_chart__REGN__5y.json` | 453 |
| `yahoo_chart__REG__5y.json` | 451 |
| `yahoo_chart__RELX__5y.json` | 453 |
| `yahoo_chart__REXR__5y.json` | 453 |
| `yahoo_chart__REYN__5y.json` | 453 |
| `yahoo_chart__RF__5y.json` | 449 |
| `yahoo_chart__RGA__5y.json` | 451 |
| `yahoo_chart__RGEN__5y.json` | 453 |
| `yahoo_chart__RGLD__5y.json` | 453 |
| `yahoo_chart__RHI__5y.json` | 451 |
| `yahoo_chart__RH__5y.json` | 449 |
| `yahoo_chart__RIO__5y.json` | 451 |
| `yahoo_chart__RITM__5y.json` | 453 |
| `yahoo_chart__RIVN__5y.json` | 453 |
| `yahoo_chart__RJF__5y.json` | 451 |
| `yahoo_chart__RKT__5y.json` | 451 |
| `yahoo_chart__RLI__5y.json` | 451 |
| `yahoo_chart__RLXXF__5y.json` | 455 |
| `yahoo_chart__RL__5y.json` | 449 |
| `yahoo_chart__RMD__5y.json` | 451 |
| `yahoo_chart__RNG__5y.json` | 451 |
| `yahoo_chart__RNR__5y.json` | 451 |
| `yahoo_chart__ROIV__5y.json` | 453 |
| `yahoo_chart__ROKU__5y.json` | 453 |
| `yahoo_chart__ROK__5y.json` | 451 |
| `yahoo_chart__ROL__5y.json` | 451 |
| `yahoo_chart__ROP__5y.json` | 451 |
| `yahoo_chart__ROST__5y.json` | 453 |
| `yahoo_chart__RPM__5y.json` | 451 |
| `yahoo_chart__RPRX__5y.json` | 453 |
| `yahoo_chart__RRC__5y.json` | 451 |
| `yahoo_chart__RRX__5y.json` | 451 |
| `yahoo_chart__RSG__5y.json` | 451 |
| `yahoo_chart__RS__5y.json` | 449 |
| `yahoo_chart__RTPPF__5y.json` | 455 |
| `yahoo_chart__RTX__5y.json` | 451 |
| `yahoo_chart__RUN__5y.json` | 451 |
| `yahoo_chart__RVTY__5y.json` | 453 |
| `yahoo_chart__RYAN__5y.json` | 453 |
| `yahoo_chart__RYDAF__5y.json` | 455 |
| `yahoo_chart__RYLBF__5y.json` | 454 |
| `yahoo_chart__RYN__5y.json` | 451 |
| `yahoo_chart__RY__5y.json` | 449 |
| `yahoo_chart__R__5y.json` | 447 |
| `yahoo_chart__SAIA__5y.json` | 453 |
| `yahoo_chart__SAIC__5y.json` | 453 |
| `yahoo_chart__SAM__5y.json` | 451 |
| `yahoo_chart__SAN__5y.json` | 451 |
| `yahoo_chart__SAPGF__5y.json` | 455 |
| `yahoo_chart__SAP__5y.json` | 451 |
| `yahoo_chart__SARO__5y.json` | 452 |
| `yahoo_chart__SBAC__5y.json` | 453 |
| `yahoo_chart__SBUX__5y.json` | 453 |
| `yahoo_chart__SCCO__5y.json` | 453 |
| `yahoo_chart__SCHW-PD__5y.json` | 459 |
| `yahoo_chart__SCHW-PJ__5y.json` | 459 |
| `yahoo_chart__SCHW__5y.json` | 453 |
| `yahoo_chart__SCI__5y.json` | 451 |
| `yahoo_chart__SEB__5y.json` | 451 |
| `yahoo_chart__SEG__5y.json` | 450 |
| `yahoo_chart__SEIC__5y.json` | 453 |
| `yahoo_chart__SE__5y.json` | 449 |
| `yahoo_chart__SF-PB__5y.json` | 455 |
| `yahoo_chart__SF-PC__5y.json` | 455 |
| `yahoo_chart__SF-PD__5y.json` | 455 |
| `yahoo_chart__SF__5y.json` | 449 |
| `yahoo_chart__SGI__5y.json` | 451 |
| `yahoo_chart__SHC__5y.json` | 451 |
| `yahoo_chart__SHEL__5y.json` | 453 |
| `yahoo_chart__SHNY__5y.json` | 452 |
| `yahoo_chart__SHOP__5y.json` | 453 |
| `yahoo_chart__SHW__5y.json` | 451 |
| `yahoo_chart__SIRI__5y.json` | 453 |
| `yahoo_chart__SITE__5y.json` | 453 |
| `yahoo_chart__SJM__5y.json` | 451 |
| `yahoo_chart__SLB__5y.json` | 451 |
| `yahoo_chart__SLGN__5y.json` | 453 |
| `yahoo_chart__SLM__5y.json` | 451 |
| `yahoo_chart__SMCI__5y.json` | 453 |
| `yahoo_chart__SMFG__5y.json` | 453 |
| `yahoo_chart__SMFNF__5y.json` | 455 |
| `yahoo_chart__SMG__5y.json` | 451 |
| `yahoo_chart__SMHD__5y.json` | 451 |
| `yahoo_chart__SMHU__5y.json` | 451 |
| `yahoo_chart__SNA__5y.json` | 451 |
| `yahoo_chart__SNDK__5y.json` | 452 |
| `yahoo_chart__SNDR__5y.json` | 453 |
| `yahoo_chart__SNEJF__5y.json` | 455 |
| `yahoo_chart__SNOW__5y.json` | 453 |
| `yahoo_chart__SNPS__5y.json` | 453 |
| `yahoo_chart__SNX__5y.json` | 451 |
| `yahoo_chart__SNYNF__5y.json` | 455 |
| `yahoo_chart__SNY__5y.json` | 451 |
| `yahoo_chart__SN__5y.json` | 448 |
| `yahoo_chart__SOFI__5y.json` | 453 |
| `yahoo_chart__SOJC__5y.json` | 453 |
| `yahoo_chart__SOJD__5y.json` | 453 |
| `yahoo_chart__SOJE__5y.json` | 453 |
| `yahoo_chart__SOJF__5y.json` | 452 |
| `yahoo_chart__SOLV__5y.json` | 452 |
| `yahoo_chart__SOMN__5y.json` | 452 |
| `yahoo_chart__SONY__5y.json` | 453 |
| `yahoo_chart__SON__5y.json` | 451 |
| `yahoo_chart__SO__5y.json` | 449 |
| `yahoo_chart__SPB__5y.json` | 451 |
| `yahoo_chart__SPG-PJ__5y.json` | 457 |
| `yahoo_chart__SPGI__5y.json` | 453 |
| `yahoo_chart__SPG__5y.json` | 451 |
| `yahoo_chart__SPOT__5y.json` | 453 |
| `yahoo_chart__SPYU__5y.json` | 452 |
| `yahoo_chart__SREA__5y.json` | 453 |
| `yahoo_chart__SRE__5y.json` | 451 |
| `yahoo_chart__SRPT__5y.json` | 453 |
| `yahoo_chart__SSD__5y.json` | 451 |
| `yahoo_chart__SSNC__5y.json` | 453 |
| `yahoo_chart__SSRM__5y.json` | 453 |
| `yahoo_chart__STAG__5y.json` | 453 |
| `yahoo_chart__STE__5y.json` | 451 |
| `yahoo_chart__STLD__5y.json` | 453 |
| `yahoo_chart__STOHF__5y.json` | 455 |
| `yahoo_chart__STRC__5y.json` | 452 |
| `yahoo_chart__STRD__5y.json` | 452 |
| `yahoo_chart__STRF__5y.json` | 452 |
| `yahoo_chart__STRK__5y.json` | 452 |
| `yahoo_chart__STT-PG__5y.json` | 457 |
| `yahoo_chart__STT__5y.json` | 451 |
| `yahoo_chart__STWD__5y.json` | 453 |
| `yahoo_chart__STX__5y.json` | 451 |
| `yahoo_chart__STZ__5y.json` | 451 |
| `yahoo_chart__ST__5y.json` | 449 |
| `yahoo_chart__SUI__5y.json` | 451 |
| `yahoo_chart__SU__5y.json` | 449 |
| `yahoo_chart__SWKS__5y.json` | 453 |
| `yahoo_chart__SWK__5y.json` | 451 |
| `yahoo_chart__SW__5y.json` | 449 |
| `yahoo_chart__SYF__5y.json` | 451 |
| `yahoo_chart__SYK__5y.json` | 451 |
| `yahoo_chart__SYY__5y.json` | 451 |
| `yahoo_chart__S__5y.json` | 447 |
| `yahoo_chart__T-PA__5y.json` | 453 |
| `yahoo_chart__T-PC__5y.json` | 453 |
| `yahoo_chart__TAK__5y.json` | 451 |
| `yahoo_chart__TAP-A__5y.json` | 455 |
| `yahoo_chart__TAP__5y.json` | 451 |
| `yahoo_chart__TAWN__5y.json` | 451 |
| `yahoo_chart__TBB__5y.json` | 451 |
| `yahoo_chart__TDBCP__5y.json` | 454 |
| `yahoo_chart__TDC__5y.json` | 451 |
| `yahoo_chart__TDG__5y.json` | 451 |
| `yahoo_chart__TDOC__5y.json` | 453 |
| `yahoo_chart__TDY__5y.json` | 451 |
| `yahoo_chart__TD__5y.json` | 449 |
| `yahoo_chart__TEAM__5y.json` | 453 |
| `yahoo_chart__TECH__5y.json` | 453 |
| `yahoo_chart__TEL__5y.json` | 451 |
| `yahoo_chart__TER__5y.json` | 451 |
| `yahoo_chart__TFC-PI__5y.json` | 457 |
| `yahoo_chart__TFC-PO__5y.json` | 457 |
| `yahoo_chart__TFC-PR__5y.json` | 457 |
| `yahoo_chart__TFC__5y.json` | 451 |
| `yahoo_chart__TFSL__5y.json` | 453 |
| `yahoo_chart__TFX__5y.json` | 451 |
| `yahoo_chart__TGT__5y.json` | 451 |
| `yahoo_chart__THC__5y.json` | 451 |
| `yahoo_chart__THG__5y.json` | 451 |
| `yahoo_chart__THO__5y.json` | 451 |
| `yahoo_chart__TJX__5y.json` | 451 |
| `yahoo_chart__TKO__5y.json` | 451 |
| `yahoo_chart__TKPHF__5y.json` | 455 |
| `yahoo_chart__TKR__5y.json` | 451 |
| `yahoo_chart__TMO__5y.json` | 451 |
| `yahoo_chart__TMUSI__5y.json` | 454 |
| `yahoo_chart__TMUSL__5y.json` | 454 |
| `yahoo_chart__TMUSZ__5y.json` | 454 |
| `yahoo_chart__TMUS__5y.json` | 453 |
| `yahoo_chart__TM__5y.json` | 449 |
| `yahoo_chart__TNDM__5y.json` | 453 |
| `yahoo_chart__TNL__5y.json` | 451 |
| `yahoo_chart__TOL__5y.json` | 451 |
| `yahoo_chart__TOST__5y.json` | 453 |
| `yahoo_chart__TOYOF__5y.json` | 455 |
| `yahoo_chart__TPEI__5y.json` | 451 |
| `yahoo_chart__TPG__5y.json` | 451 |
| `yahoo_chart__TPL__5y.json` | 451 |
| `yahoo_chart__TPR__5y.json` | 451 |
| `yahoo_chart__TREX__5y.json` | 453 |
| `yahoo_chart__TRGP__5y.json` | 453 |
| `yahoo_chart__TRIP__5y.json` | 453 |
| `yahoo_chart__TRMB__5y.json` | 453 |
| `yahoo_chart__TROW__5y.json` | 453 |
| `yahoo_chart__TRU__5y.json` | 451 |
| `yahoo_chart__TRV__5y.json` | 451 |
| `yahoo_chart__TSCO__5y.json` | 453 |
| `yahoo_chart__TSLA__5y.json` | 453 |
| `yahoo_chart__TSN__5y.json` | 451 |
| `yahoo_chart__TTC__5y.json` | 451 |
| `yahoo_chart__TTD__5y.json` | 451 |
| `yahoo_chart__TTEK__5y.json` | 453 |
| `yahoo_chart__TTE__5y.json` | 451 |
| `yahoo_chart__TTWO__5y.json` | 453 |
| `yahoo_chart__TT__5y.json` | 449 |
| `yahoo_chart__TWLO__5y.json` | 453 |
| `yahoo_chart__TW__5y.json` | 449 |
| `yahoo_chart__TXG__5y.json` | 451 |
| `yahoo_chart__TXN__5y.json` | 451 |
| `yahoo_chart__TXRH__5y.json` | 453 |
| `yahoo_chart__TXT__5y.json` | 451 |
| `yahoo_chart__TYL__5y.json` | 451 |
| `yahoo_chart__T__5y.json` | 447 |
| `yahoo_chart__UAA__5y.json` | 451 |
| `yahoo_chart__UAL__5y.json` | 451 |
| `yahoo_chart__UA__5y.json` | 449 |
| `yahoo_chart__UBER__5y.json` | 453 |
| `yahoo_chart__UBS__5y.json` | 451 |
| `yahoo_chart__UDR__5y.json` | 451 |
| `yahoo_chart__UGI__5y.json` | 451 |
| `yahoo_chart__UHAL-B__5y.json` | 457 |
| `yahoo_chart__UHAL__5y.json` | 453 |
| `yahoo_chart__UHS__5y.json` | 451 |
| `yahoo_chart__UI__5y.json` | 449 |
| `yahoo_chart__ULTA__5y.json` | 453 |
| `yahoo_chart__UL__5y.json` | 449 |
| `yahoo_chart__UMC__5y.json` | 451 |
| `yahoo_chart__UNH__5y.json` | 451 |
| `yahoo_chart__UNLYF__5y.json` | 455 |
| `yahoo_chart__UNM__5y.json` | 451 |
| `yahoo_chart__UNP__5y.json` | 451 |
| `yahoo_chart__UPS__5y.json` | 451 |
| `yahoo_chart__URI__5y.json` | 451 |
| `yahoo_chart__USB-PA__5y.json` | 457 |
| `yahoo_chart__USB-PH__5y.json` | 457 |
| `yahoo_chart__USB-PP__5y.json` | 457 |
| `yahoo_chart__USB-PQ__5y.json` | 457 |
| `yahoo_chart__USB-PR__5y.json` | 457 |
| `yahoo_chart__USB-PS__5y.json` | 457 |
| `yahoo_chart__USB__5y.json` | 451 |
| `yahoo_chart__USFD__5y.json` | 453 |
| `yahoo_chart__UTHR__5y.json` | 453 |
| `yahoo_chart__UWMC__5y.json` | 453 |
| `yahoo_chart__U__5y.json` | 447 |
| `yahoo_chart__VAC__5y.json` | 451 |
| `yahoo_chart__VALE__5y.json` | 453 |
| `yahoo_chart__VEEV__5y.json` | 453 |
| `yahoo_chart__VFC__5y.json` | 451 |
| `yahoo_chart__VICI__5y.json` | 453 |
| `yahoo_chart__VIRT__5y.json` | 453 |
| `yahoo_chart__VKTX__5y.json` | 453 |
| `yahoo_chart__VLO__5y.json` | 451 |
| `yahoo_chart__VLTO__5y.json` | 452 |
| `yahoo_chart__VMC__5y.json` | 451 |
| `yahoo_chart__VMI__5y.json` | 451 |
| `yahoo_chart__VNOM__5y.json` | 453 |
| `yahoo_chart__VNO__5y.json` | 451 |
| `yahoo_chart__VNT__5y.json` | 451 |
| `yahoo_chart__VOYA__5y.json` | 453 |
| `yahoo_chart__VRSK__5y.json` | 453 |
| `yahoo_chart__VRSN__5y.json` | 453 |
| `yahoo_chart__VRTX__5y.json` | 453 |
| `yahoo_chart__VRT__5y.json` | 451 |
| `yahoo_chart__VSAT__5y.json` | 453 |
| `yahoo_chart__VSTS__5y.json` | 452 |
| `yahoo_chart__VST__5y.json` | 451 |
| `yahoo_chart__VSXY__5y.json` | 453 |
| `yahoo_chart__VTRS__5y.json` | 453 |
| `yahoo_chart__VTR__5y.json` | 451 |
| `yahoo_chart__VVV__5y.json` | 451 |
| `yahoo_chart__VYLD__5y.json` | 452 |
| `yahoo_chart__VYX__5y.json` | 451 |
| `yahoo_chart__VZ__5y.json` | 449 |
| `yahoo_chart__V__5y.json` | 447 |
| `yahoo_chart__WAB__5y.json` | 451 |
| `yahoo_chart__WAL__5y.json` | 451 |
| `yahoo_chart__WAT__5y.json` | 451 |
| `yahoo_chart__WBD__5y.json` | 451 |
| `yahoo_chart__WCC__5y.json` | 451 |
| `yahoo_chart__WDAY__5y.json` | 453 |
| `yahoo_chart__WDC__5y.json` | 451 |
| `yahoo_chart__WEC__5y.json` | 451 |
| `yahoo_chart__WELL__5y.json` | 453 |
| `yahoo_chart__WEN__5y.json` | 451 |
| `yahoo_chart__WEX__5y.json` | 451 |
| `yahoo_chart__WFC-PA__5y.json` | 457 |
| `yahoo_chart__WFC-PC__5y.json` | 457 |
| `yahoo_chart__WFC-PD__5y.json` | 457 |
| `yahoo_chart__WFC-PL__5y.json` | 457 |
| `yahoo_chart__WFC-PY__5y.json` | 457 |
| `yahoo_chart__WFC-PZ__5y.json` | 457 |
| `yahoo_chart__WFCNP__5y.json` | 455 |
| `yahoo_chart__WFC__5y.json` | 451 |
| `yahoo_chart__WFRD__5y.json` | 453 |
| `yahoo_chart__WHR__5y.json` | 451 |
| `yahoo_chart__WH__5y.json` | 449 |
| `yahoo_chart__WING__5y.json` | 453 |
| `yahoo_chart__WLK__5y.json` | 451 |
| `yahoo_chart__WMB__5y.json` | 451 |
| `yahoo_chart__WMS__5y.json` | 451 |
| `yahoo_chart__WMT__5y.json` | 451 |
| `yahoo_chart__WM__5y.json` | 449 |
| `yahoo_chart__WOLF__5y.json` | 452 |
| `yahoo_chart__WOOF__5y.json` | 453 |
| `yahoo_chart__WPC__5y.json` | 451 |
| `yahoo_chart__WPM__5y.json` | 451 |
| `yahoo_chart__WRB__5y.json` | 451 |
| `yahoo_chart__WSC__5y.json` | 451 |
| `yahoo_chart__WSM__5y.json` | 451 |
| `yahoo_chart__WSO-B__5y.json` | 455 |
| `yahoo_chart__WSO__5y.json` | 451 |
| `yahoo_chart__WST__5y.json` | 451 |
| `yahoo_chart__WTFC__5y.json` | 453 |
| `yahoo_chart__WTID__5y.json` | 452 |
| `yahoo_chart__WTIU__5y.json` | 452 |
| `yahoo_chart__WTM__5y.json` | 451 |
| `yahoo_chart__WTRG__5y.json` | 453 |
| `yahoo_chart__WTW__5y.json` | 451 |
| `yahoo_chart__WU__5y.json` | 449 |
| `yahoo_chart__WWD__5y.json` | 451 |
| `yahoo_chart__WYNN__5y.json` | 453 |
| `yahoo_chart__WY__5y.json` | 449 |
| `yahoo_chart__W__5y.json` | 447 |
| `yahoo_chart__XEL__5y.json` | 451 |
| `yahoo_chart__XLCD__5y.json` | 451 |
| `yahoo_chart__XLCU__5y.json` | 451 |
| `yahoo_chart__XLPD__5y.json` | 451 |
| `yahoo_chart__XLPU__5y.json` | 451 |
| `yahoo_chart__XOM__5y.json` | 451 |
| `yahoo_chart__XPO__5y.json` | 451 |
| `yahoo_chart__XP__5y.json` | 449 |
| `yahoo_chart__XRAY__5y.json` | 453 |
| `yahoo_chart__XYL__5y.json` | 451 |
| `yahoo_chart__XYZ__5y.json` | 451 |
| `yahoo_chart__YETI__5y.json` | 453 |
| `yahoo_chart__YUM__5y.json` | 451 |
| `yahoo_chart__ZBH__5y.json` | 451 |
| `yahoo_chart__ZBRA__5y.json` | 453 |
| `yahoo_chart__ZG__5y.json` | 449 |
| `yahoo_chart__ZION__5y.json` | 453 |
| `yahoo_chart__ZM__5y.json` | 449 |
| `yahoo_chart__ZS__5y.json` | 449 |
| `yahoo_chart__ZTS__5y.json` | 451 |
| `yahoo_chart__Z__5y.json` | 447 |

#### R15 — 유지 가능 / Yahoo / 1,354파일

- 공통 경로 prefix: `implementation/data/raw/manifests/`
- 종류: JSON, 원문 참조 metadata, 실값 없는 metadata, 가격/혼합 원문 참조.
- 출처: Yahoo / `source_kind=YAHOO_SPLIT_EVENTS`.
- 용도: Yahoo 월봉 chart+split event provenance; audit_mcap_store.load_splits의 참조. events endpoint도 Finance chart 응답이므로 순수 행사-only blob으로 증명되지 않음. manifest 자체 소비: RawDatasetStore.get_manifest, raw_persistence.artifact_records, STORE_INDEX writer, archive restore check.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 유지 근거: 해당 경로의 metadata/명시된 비가격 facts·개수·상태·URL/hash를 확인했다. raw manifest는 가격 실값을 포함하지 않는다. 공급자 원문 body의 적격성은 별도다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `yahoo_events__AAL__5y.json` | 471 |
| `yahoo_events__AAON__5y.json` | 473 |
| `yahoo_events__AAPL__5y.json` | 473 |
| `yahoo_events__AAP__5y.json` | 471 |
| `yahoo_events__AA__5y.json` | 469 |
| `yahoo_events__ABBV__5y.json` | 473 |
| `yahoo_events__ABNB__5y.json` | 473 |
| `yahoo_events__ABT__5y.json` | 471 |
| `yahoo_events__ACGL__5y.json` | 473 |
| `yahoo_events__ACHC__5y.json` | 473 |
| `yahoo_events__ACI__5y.json` | 471 |
| `yahoo_events__ACM__5y.json` | 471 |
| `yahoo_events__ACN__5y.json` | 471 |
| `yahoo_events__ADBE__5y.json` | 473 |
| `yahoo_events__ADC__5y.json` | 471 |
| `yahoo_events__ADI__5y.json` | 471 |
| `yahoo_events__ADM__5y.json` | 471 |
| `yahoo_events__ADP__5y.json` | 471 |
| `yahoo_events__ADSK__5y.json` | 473 |
| `yahoo_events__ADTTF__5y.json` | 475 |
| `yahoo_events__ADT__5y.json` | 471 |
| `yahoo_events__AEE__5y.json` | 471 |
| `yahoo_events__AEMRF__5y.json` | 475 |
| `yahoo_events__AEM__5y.json` | 471 |
| `yahoo_events__AEP__5y.json` | 471 |
| `yahoo_events__AES__5y.json` | 471 |
| `yahoo_events__AFG__5y.json` | 471 |
| `yahoo_events__AFL__5y.json` | 471 |
| `yahoo_events__AFRM__5y.json` | 473 |
| `yahoo_events__AGCO__5y.json` | 473 |
| `yahoo_events__AGL__5y.json` | 471 |
| `yahoo_events__AGNC__5y.json` | 473 |
| `yahoo_events__AGO__5y.json` | 471 |
| `yahoo_events__AIG__5y.json` | 471 |
| `yahoo_events__AIQD__5y.json` | 473 |
| `yahoo_events__AIQU__5y.json` | 473 |
| `yahoo_events__AIZ__5y.json` | 471 |
| `yahoo_events__AJG__5y.json` | 471 |
| `yahoo_events__AKAM__5y.json` | 473 |
| `yahoo_events__ALAB__5y.json` | 473 |
| `yahoo_events__ALB__5y.json` | 471 |
| `yahoo_events__ALGM__5y.json` | 473 |
| `yahoo_events__ALGN__5y.json` | 473 |
| `yahoo_events__ALK__5y.json` | 471 |
| `yahoo_events__ALL-PB__5y.json` | 477 |
| `yahoo_events__ALL-PH__5y.json` | 477 |
| `yahoo_events__ALL-PI__5y.json` | 477 |
| `yahoo_events__ALL-PJ__5y.json` | 477 |
| `yahoo_events__ALLE__5y.json` | 473 |
| `yahoo_events__ALLY__5y.json` | 473 |
| `yahoo_events__ALL__5y.json` | 471 |
| `yahoo_events__ALNY__5y.json` | 473 |
| `yahoo_events__ALSN__5y.json` | 473 |
| `yahoo_events__AMAT__5y.json` | 473 |
| `yahoo_events__AMBP__5y.json` | 473 |
| `yahoo_events__AMCR__5y.json` | 473 |
| `yahoo_events__AMC__5y.json` | 471 |
| `yahoo_events__AMD__5y.json` | 471 |
| `yahoo_events__AME__5y.json` | 471 |
| `yahoo_events__AMGN__5y.json` | 473 |
| `yahoo_events__AMG__5y.json` | 471 |
| `yahoo_events__AMH__5y.json` | 471 |
| `yahoo_events__AMJB__5y.json` | 473 |
| `yahoo_events__AMKR__5y.json` | 473 |
| `yahoo_events__AMP__5y.json` | 471 |
| `yahoo_events__AMSYF__5y.json` | 475 |
| `yahoo_events__AMTM__5y.json` | 473 |
| `yahoo_events__AMT__5y.json` | 471 |
| `yahoo_events__AMXOF__5y.json` | 475 |
| `yahoo_events__AMX__5y.json` | 471 |
| `yahoo_events__AMZN__5y.json` | 473 |
| `yahoo_events__AM__5y.json` | 469 |
| `yahoo_events__ANET__5y.json` | 473 |
| `yahoo_events__AN__5y.json` | 469 |
| `yahoo_events__AON__5y.json` | 471 |
| `yahoo_events__AOS__5y.json` | 471 |
| `yahoo_events__APA__5y.json` | 471 |
| `yahoo_events__APD__5y.json` | 471 |
| `yahoo_events__APG__5y.json` | 471 |
| `yahoo_events__APH__5y.json` | 471 |
| `yahoo_events__APOS__5y.json` | 473 |
| `yahoo_events__APO__5y.json` | 471 |
| `yahoo_events__APPF__5y.json` | 473 |
| `yahoo_events__APP__5y.json` | 471 |
| `yahoo_events__APTV__5y.json` | 473 |
| `yahoo_events__ARCXF__5y.json` | 475 |
| `yahoo_events__ARES__5y.json` | 473 |
| `yahoo_events__ARE__5y.json` | 471 |
| `yahoo_events__ARGX__5y.json` | 473 |
| `yahoo_events__ARMK__5y.json` | 473 |
| `yahoo_events__ARM__5y.json` | 471 |
| `yahoo_events__ARW__5y.json` | 471 |
| `yahoo_events__AR__5y.json` | 469 |
| `yahoo_events__ASH__5y.json` | 471 |
| `yahoo_events__ASMLF__5y.json` | 475 |
| `yahoo_events__ASML__5y.json` | 473 |
| `yahoo_events__ASX__5y.json` | 471 |
| `yahoo_events__AS__5y.json` | 469 |
| `yahoo_events__ATEYY__5y.json` | 475 |
| `yahoo_events__ATI__5y.json` | 471 |
| `yahoo_events__ATO__5y.json` | 471 |
| `yahoo_events__ATR__5y.json` | 471 |
| `yahoo_events__AU__5y.json` | 469 |
| `yahoo_events__AVB__5y.json` | 471 |
| `yahoo_events__AVGO__5y.json` | 473 |
| `yahoo_events__AVTR__5y.json` | 473 |
| `yahoo_events__AVT__5y.json` | 471 |
| `yahoo_events__AVY__5y.json` | 471 |
| `yahoo_events__AWI__5y.json` | 471 |
| `yahoo_events__AWK__5y.json` | 471 |
| `yahoo_events__AXON__5y.json` | 473 |
| `yahoo_events__AXP__5y.json` | 471 |
| `yahoo_events__AXS__5y.json` | 471 |
| `yahoo_events__AXTA__5y.json` | 473 |
| `yahoo_events__AYI__5y.json` | 471 |
| `yahoo_events__AZN__5y.json` | 471 |
| `yahoo_events__AZO__5y.json` | 471 |
| `yahoo_events__AZTA__5y.json` | 473 |
| `yahoo_events__A__5y.json` | 467 |
| `yahoo_events__BA-PA__5y.json` | 475 |
| `yahoo_events__BABAF__5y.json` | 475 |
| `yahoo_events__BABA__5y.json` | 473 |
| `yahoo_events__BAC-PB__5y.json` | 477 |
| `yahoo_events__BAC-PE__5y.json` | 477 |
| `yahoo_events__BAC-PK__5y.json` | 477 |
| `yahoo_events__BAC-PL__5y.json` | 477 |
| `yahoo_events__BAC-PM__5y.json` | 477 |
| `yahoo_events__BAC-PN__5y.json` | 477 |
| `yahoo_events__BAC-PO__5y.json` | 477 |
| `yahoo_events__BAC-PP__5y.json` | 477 |
| `yahoo_events__BAC-PQ__5y.json` | 477 |
| `yahoo_events__BAC-PS__5y.json` | 477 |
| `yahoo_events__BACRP__5y.json` | 475 |
| `yahoo_events__BAC__5y.json` | 471 |
| `yahoo_events__BAH__5y.json` | 471 |
| `yahoo_events__BALL__5y.json` | 473 |
| `yahoo_events__BAMGF__5y.json` | 475 |
| `yahoo_events__BAMKF__5y.json` | 475 |
| `yahoo_events__BAM__5y.json` | 471 |
| `yahoo_events__BAX__5y.json` | 471 |
| `yahoo_events__BA__5y.json` | 469 |
| `yahoo_events__BBVA__5y.json` | 473 |
| `yahoo_events__BBVXF__5y.json` | 475 |
| `yahoo_events__BBWI__5y.json` | 473 |
| `yahoo_events__BBY__5y.json` | 471 |
| `yahoo_events__BCDRF__5y.json` | 475 |
| `yahoo_events__BCLYF__5y.json` | 475 |
| `yahoo_events__BCS__5y.json` | 471 |
| `yahoo_events__BC__5y.json` | 469 |
| `yahoo_events__BDX__5y.json` | 471 |
| `yahoo_events__BEN__5y.json` | 471 |
| `yahoo_events__BEPC__5y.json` | 473 |
| `yahoo_events__BERZ__5y.json` | 473 |
| `yahoo_events__BE__5y.json` | 469 |
| `yahoo_events__BF-A__5y.json` | 473 |
| `yahoo_events__BF-B__5y.json` | 473 |
| `yahoo_events__BFAM__5y.json` | 473 |
| `yahoo_events__BG__5y.json` | 469 |
| `yahoo_events__BHF__5y.json` | 471 |
| `yahoo_events__BHPLF__5y.json` | 475 |
| `yahoo_events__BHP__5y.json` | 471 |
| `yahoo_events__BIIB__5y.json` | 473 |
| `yahoo_events__BILL__5y.json` | 473 |
| `yahoo_events__BIO-B__5y.json` | 475 |
| `yahoo_events__BIO__5y.json` | 471 |
| `yahoo_events__BIRK__5y.json` | 473 |
| `yahoo_events__BJ__5y.json` | 469 |
| `yahoo_events__BKAMF__5y.json` | 475 |
| `yahoo_events__BKFAF__5y.json` | 475 |
| `yahoo_events__BKFOF__5y.json` | 475 |
| `yahoo_events__BKFPF__5y.json` | 475 |
| `yahoo_events__BKNG__5y.json` | 473 |
| `yahoo_events__BKR__5y.json` | 471 |
| `yahoo_events__BLDR__5y.json` | 473 |
| `yahoo_events__BLK__5y.json` | 471 |
| `yahoo_events__BML-PG__5y.json` | 477 |
| `yahoo_events__BML-PH__5y.json` | 477 |
| `yahoo_events__BML-PJ__5y.json` | 477 |
| `yahoo_events__BML-PL__5y.json` | 477 |
| `yahoo_events__BMO__5y.json` | 471 |
| `yahoo_events__BMRN__5y.json` | 473 |
| `yahoo_events__BMY__5y.json` | 471 |
| `yahoo_events__BNH__5y.json` | 471 |
| `yahoo_events__BNJ__5y.json` | 471 |
| `yahoo_events__BNKD__5y.json` | 473 |
| `yahoo_events__BNKU__5y.json` | 473 |
| `yahoo_events__BNS__5y.json` | 471 |
| `yahoo_events__BNY-PK__5y.json` | 477 |
| `yahoo_events__BNY__5y.json` | 471 |
| `yahoo_events__BN__5y.json` | 469 |
| `yahoo_events__BOKF__5y.json` | 473 |
| `yahoo_events__BPAQF__5y.json` | 475 |
| `yahoo_events__BPOP__5y.json` | 473 |
| `yahoo_events__BPPFF__5y.json` | 474 |
| `yahoo_events__BP__5y.json` | 469 |
| `yahoo_events__BRBR__5y.json` | 473 |
| `yahoo_events__BRCFF__5y.json` | 475 |
| `yahoo_events__BRFAF__5y.json` | 475 |
| `yahoo_events__BRK-A__5y.json` | 475 |
| `yahoo_events__BRK-B__5y.json` | 475 |
| `yahoo_events__BRKR__5y.json` | 473 |
| `yahoo_events__BROS__5y.json` | 473 |
| `yahoo_events__BRO__5y.json` | 471 |
| `yahoo_events__BRPSF__5y.json` | 475 |
| `yahoo_events__BRX__5y.json` | 471 |
| `yahoo_events__BRZD__5y.json` | 473 |
| `yahoo_events__BRZL__5y.json` | 473 |
| `yahoo_events__BR__5y.json` | 469 |
| `yahoo_events__BSX__5y.json` | 471 |
| `yahoo_events__BSY__5y.json` | 471 |
| `yahoo_events__BTAFF__5y.json` | 475 |
| `yahoo_events__BTI__5y.json` | 471 |
| `yahoo_events__BUDFF__5y.json` | 475 |
| `yahoo_events__BUD__5y.json` | 471 |
| `yahoo_events__BULZ__5y.json` | 473 |
| `yahoo_events__BURL__5y.json` | 473 |
| `yahoo_events__BWA__5y.json` | 471 |
| `yahoo_events__BWXT__5y.json` | 473 |
| `yahoo_events__BXP__5y.json` | 471 |
| `yahoo_events__BX__5y.json` | 469 |
| `yahoo_events__BYD__5y.json` | 471 |
| `yahoo_events__B__5y.json` | 467 |
| `yahoo_events__C-PN__5y.json` | 473 |
| `yahoo_events__C-PR__5y.json` | 473 |
| `yahoo_events__CABO__5y.json` | 473 |
| `yahoo_events__CACC__5y.json` | 473 |
| `yahoo_events__CACI__5y.json` | 473 |
| `yahoo_events__CAG__5y.json` | 471 |
| `yahoo_events__CAH__5y.json` | 471 |
| `yahoo_events__CARD__5y.json` | 473 |
| `yahoo_events__CARR__5y.json` | 473 |
| `yahoo_events__CART__5y.json` | 473 |
| `yahoo_events__CARU__5y.json` | 473 |
| `yahoo_events__CAR__5y.json` | 471 |
| `yahoo_events__CASY__5y.json` | 473 |
| `yahoo_events__CAT__5y.json` | 471 |
| `yahoo_events__CAVA__5y.json` | 473 |
| `yahoo_events__CBOE__5y.json` | 473 |
| `yahoo_events__CBRE__5y.json` | 473 |
| `yahoo_events__CBSH__5y.json` | 473 |
| `yahoo_events__CB__5y.json` | 469 |
| `yahoo_events__CCC__5y.json` | 471 |
| `yahoo_events__CCI__5y.json` | 471 |
| `yahoo_events__CCK__5y.json` | 471 |
| `yahoo_events__CCL__5y.json` | 471 |
| `yahoo_events__CCZ__5y.json` | 471 |
| `yahoo_events__CC__5y.json` | 469 |
| `yahoo_events__CDNS__5y.json` | 473 |
| `yahoo_events__CDW__5y.json` | 471 |
| `yahoo_events__CEG__5y.json` | 471 |
| `yahoo_events__CELG-RI__5y.json` | 479 |
| `yahoo_events__CELH__5y.json` | 473 |
| `yahoo_events__CERT__5y.json` | 473 |
| `yahoo_events__CE__5y.json` | 469 |
| `yahoo_events__CFG__5y.json` | 471 |
| `yahoo_events__CFR__5y.json` | 471 |
| `yahoo_events__CF__5y.json` | 469 |
| `yahoo_events__CGNX__5y.json` | 473 |
| `yahoo_events__CG__5y.json` | 469 |
| `yahoo_events__CHDN__5y.json` | 473 |
| `yahoo_events__CHD__5y.json` | 471 |
| `yahoo_events__CHE__5y.json` | 471 |
| `yahoo_events__CHH__5y.json` | 471 |
| `yahoo_events__CHPT__5y.json` | 473 |
| `yahoo_events__CHRD__5y.json` | 473 |
| `yahoo_events__CHRW__5y.json` | 473 |
| `yahoo_events__CHTR__5y.json` | 473 |
| `yahoo_events__CIEN__5y.json` | 473 |
| `yahoo_events__CINF__5y.json` | 473 |
| `yahoo_events__CI__5y.json` | 469 |
| `yahoo_events__CLF__5y.json` | 471 |
| `yahoo_events__CLH__5y.json` | 471 |
| `yahoo_events__CLVT__5y.json` | 473 |
| `yahoo_events__CLX__5y.json` | 471 |
| `yahoo_events__CL__5y.json` | 469 |
| `yahoo_events__CMCSA__5y.json` | 475 |
| `yahoo_events__CME__5y.json` | 471 |
| `yahoo_events__CMG__5y.json` | 471 |
| `yahoo_events__CMI__5y.json` | 471 |
| `yahoo_events__CMS__5y.json` | 471 |
| `yahoo_events__CM__5y.json` | 469 |
| `yahoo_events__CNA__5y.json` | 471 |
| `yahoo_events__CNC__5y.json` | 471 |
| `yahoo_events__CNDIF__5y.json` | 475 |
| `yahoo_events__CNH__5y.json` | 471 |
| `yahoo_events__CNI__5y.json` | 471 |
| `yahoo_events__CNM__5y.json` | 471 |
| `yahoo_events__CNP__5y.json` | 471 |
| `yahoo_events__CNQ__5y.json` | 471 |
| `yahoo_events__CNXC__5y.json` | 473 |
| `yahoo_events__COF-PI__5y.json` | 477 |
| `yahoo_events__COF-PJ__5y.json` | 477 |
| `yahoo_events__COF-PK__5y.json` | 477 |
| `yahoo_events__COF-PL__5y.json` | 477 |
| `yahoo_events__COF-PN__5y.json` | 477 |
| `yahoo_events__COF__5y.json` | 471 |
| `yahoo_events__COHR__5y.json` | 473 |
| `yahoo_events__COIN__5y.json` | 473 |
| `yahoo_events__COKE__5y.json` | 473 |
| `yahoo_events__COLB__5y.json` | 473 |
| `yahoo_events__COLD__5y.json` | 473 |
| `yahoo_events__COLM__5y.json` | 473 |
| `yahoo_events__COO__5y.json` | 471 |
| `yahoo_events__COP__5y.json` | 471 |
| `yahoo_events__COR__5y.json` | 471 |
| `yahoo_events__COST__5y.json` | 473 |
| `yahoo_events__COTY__5y.json` | 473 |
| `yahoo_events__CPAY__5y.json` | 473 |
| `yahoo_events__CPB__5y.json` | 471 |
| `yahoo_events__CPNG__5y.json` | 473 |
| `yahoo_events__CPRI__5y.json` | 473 |
| `yahoo_events__CPRT__5y.json` | 473 |
| `yahoo_events__CPT__5y.json` | 471 |
| `yahoo_events__CP__5y.json` | 469 |
| `yahoo_events__CRH__5y.json` | 471 |
| `yahoo_events__CRI__5y.json` | 471 |
| `yahoo_events__CRL__5y.json` | 471 |
| `yahoo_events__CRM__5y.json` | 471 |
| `yahoo_events__CROX__5y.json` | 473 |
| `yahoo_events__CRUS__5y.json` | 473 |
| `yahoo_events__CRWD__5y.json` | 473 |
| `yahoo_events__CR__5y.json` | 469 |
| `yahoo_events__CSCO__5y.json` | 473 |
| `yahoo_events__CSGP__5y.json` | 473 |
| `yahoo_events__CSL__5y.json` | 471 |
| `yahoo_events__CSX__5y.json` | 471 |
| `yahoo_events__CTAS__5y.json` | 473 |
| `yahoo_events__CTSH__5y.json` | 473 |
| `yahoo_events__CTVA__5y.json` | 473 |
| `yahoo_events__CUBE__5y.json` | 473 |
| `yahoo_events__CUZ__5y.json` | 471 |
| `yahoo_events__CVE__5y.json` | 471 |
| `yahoo_events__CVNA__5y.json` | 473 |
| `yahoo_events__CVS__5y.json` | 471 |
| `yahoo_events__CVX__5y.json` | 471 |
| `yahoo_events__CWEN__5y.json` | 473 |
| `yahoo_events__CW__5y.json` | 469 |
| `yahoo_events__CXT__5y.json` | 471 |
| `yahoo_events__CZR__5y.json` | 471 |
| `yahoo_events__C__5y.json` | 467 |
| `yahoo_events__DAL__5y.json` | 471 |
| `yahoo_events__DAR__5y.json` | 471 |
| `yahoo_events__DASH__5y.json` | 473 |
| `yahoo_events__DBX__5y.json` | 471 |
| `yahoo_events__DB__5y.json` | 469 |
| `yahoo_events__DCI__5y.json` | 471 |
| `yahoo_events__DDOG__5y.json` | 473 |
| `yahoo_events__DDS__5y.json` | 471 |
| `yahoo_events__DD__5y.json` | 469 |
| `yahoo_events__DECK__5y.json` | 473 |
| `yahoo_events__DEENF__5y.json` | 475 |
| `yahoo_events__DELL__5y.json` | 473 |
| `yahoo_events__DE__5y.json` | 469 |
| `yahoo_events__DGP__5y.json` | 471 |
| `yahoo_events__DGX__5y.json` | 471 |
| `yahoo_events__DGZ__5y.json` | 471 |
| `yahoo_events__DG__5y.json` | 469 |
| `yahoo_events__DHI__5y.json` | 471 |
| `yahoo_events__DHR__5y.json` | 471 |
| `yahoo_events__DINO__5y.json` | 473 |
| `yahoo_events__DIS__5y.json` | 471 |
| `yahoo_events__DJT__5y.json` | 471 |
| `yahoo_events__DKNG__5y.json` | 473 |
| `yahoo_events__DKS__5y.json` | 471 |
| `yahoo_events__DLB__5y.json` | 471 |
| `yahoo_events__DLR-PJ__5y.json` | 477 |
| `yahoo_events__DLR-PK__5y.json` | 477 |
| `yahoo_events__DLR-PL__5y.json` | 477 |
| `yahoo_events__DLR__5y.json` | 471 |
| `yahoo_events__DLTR__5y.json` | 473 |
| `yahoo_events__DNA__5y.json` | 471 |
| `yahoo_events__DOCS__5y.json` | 473 |
| `yahoo_events__DOCU__5y.json` | 473 |
| `yahoo_events__DOC__5y.json` | 471 |
| `yahoo_events__DOV__5y.json` | 471 |
| `yahoo_events__DOW__5y.json` | 471 |
| `yahoo_events__DOX__5y.json` | 471 |
| `yahoo_events__DPZ__5y.json` | 471 |
| `yahoo_events__DRI__5y.json` | 471 |
| `yahoo_events__DRVN__5y.json` | 473 |
| `yahoo_events__DTE__5y.json` | 471 |
| `yahoo_events__DTM__5y.json` | 471 |
| `yahoo_events__DT__5y.json` | 469 |
| `yahoo_events__DUK-PA__5y.json` | 477 |
| `yahoo_events__DUKB__5y.json` | 473 |
| `yahoo_events__DUKU__5y.json` | 473 |
| `yahoo_events__DUK__5y.json` | 471 |
| `yahoo_events__DULL__5y.json` | 473 |
| `yahoo_events__DUOL__5y.json` | 473 |
| `yahoo_events__DVA__5y.json` | 471 |
| `yahoo_events__DVN__5y.json` | 471 |
| `yahoo_events__DV__5y.json` | 469 |
| `yahoo_events__DXCM__5y.json` | 473 |
| `yahoo_events__DXC__5y.json` | 471 |
| `yahoo_events__DZZ__5y.json` | 471 |
| `yahoo_events__D__5y.json` | 467 |
| `yahoo_events__EA__5y.json` | 469 |
| `yahoo_events__EBAY__5y.json` | 473 |
| `yahoo_events__EBBGF__5y.json` | 475 |
| `yahoo_events__EBBNF__5y.json` | 475 |
| `yahoo_events__EBGEF__5y.json` | 475 |
| `yahoo_events__EBRGF__5y.json` | 475 |
| `yahoo_events__EBRZF__5y.json` | 475 |
| `yahoo_events__ECG__5y.json` | 471 |
| `yahoo_events__ECL__5y.json` | 471 |
| `yahoo_events__ED__5y.json` | 469 |
| `yahoo_events__EEFT__5y.json` | 473 |
| `yahoo_events__EFX__5y.json` | 471 |
| `yahoo_events__EGP__5y.json` | 471 |
| `yahoo_events__EG__5y.json` | 469 |
| `yahoo_events__EHC__5y.json` | 471 |
| `yahoo_events__EIPAF__5y.json` | 475 |
| `yahoo_events__EIX__5y.json` | 471 |
| `yahoo_events__ELAN__5y.json` | 473 |
| `yahoo_events__ELF__5y.json` | 471 |
| `yahoo_events__ELS__5y.json` | 471 |
| `yahoo_events__ELV__5y.json` | 471 |
| `yahoo_events__EL__5y.json` | 469 |
| `yahoo_events__EME__5y.json` | 471 |
| `yahoo_events__EMN__5y.json` | 471 |
| `yahoo_events__EMR__5y.json` | 471 |
| `yahoo_events__ENBFF__5y.json` | 475 |
| `yahoo_events__ENBGF__5y.json` | 475 |
| `yahoo_events__ENBHF__5y.json` | 475 |
| `yahoo_events__ENBMF__5y.json` | 475 |
| `yahoo_events__ENBNF__5y.json` | 475 |
| `yahoo_events__ENBOF__5y.json` | 475 |
| `yahoo_events__ENBRF__5y.json` | 475 |
| `yahoo_events__ENBSF__5y.json` | 474 |
| `yahoo_events__ENB__5y.json` | 471 |
| `yahoo_events__ENNPF__5y.json` | 475 |
| `yahoo_events__ENOV__5y.json` | 473 |
| `yahoo_events__ENPH__5y.json` | 473 |
| `yahoo_events__ENTG__5y.json` | 473 |
| `yahoo_events__EOG__5y.json` | 471 |
| `yahoo_events__EP-PC__5y.json` | 475 |
| `yahoo_events__EPAM__5y.json` | 473 |
| `yahoo_events__EPD__5y.json` | 471 |
| `yahoo_events__EPR__5y.json` | 471 |
| `yahoo_events__EQH__5y.json` | 471 |
| `yahoo_events__EQIX__5y.json` | 473 |
| `yahoo_events__EQNR__5y.json` | 473 |
| `yahoo_events__EQR__5y.json` | 471 |
| `yahoo_events__EQT__5y.json` | 471 |
| `yahoo_events__ERIE__5y.json` | 473 |
| `yahoo_events__ESAB__5y.json` | 473 |
| `yahoo_events__ESI__5y.json` | 471 |
| `yahoo_events__ESS__5y.json` | 471 |
| `yahoo_events__ESTC__5y.json` | 473 |
| `yahoo_events__ES__5y.json` | 469 |
| `yahoo_events__ET-PI__5y.json` | 475 |
| `yahoo_events__ETN__5y.json` | 471 |
| `yahoo_events__ETR__5y.json` | 471 |
| `yahoo_events__ETSY__5y.json` | 473 |
| `yahoo_events__ET__5y.json` | 469 |
| `yahoo_events__EVRG__5y.json` | 473 |
| `yahoo_events__EVR__5y.json` | 471 |
| `yahoo_events__EWBC__5y.json` | 473 |
| `yahoo_events__EW__5y.json` | 469 |
| `yahoo_events__EXC__5y.json` | 471 |
| `yahoo_events__EXEL__5y.json` | 473 |
| `yahoo_events__EXE__5y.json` | 471 |
| `yahoo_events__EXPD__5y.json` | 473 |
| `yahoo_events__EXPE__5y.json` | 473 |
| `yahoo_events__EXP__5y.json` | 471 |
| `yahoo_events__EXR__5y.json` | 471 |
| `yahoo_events__E__5y.json` | 467 |
| `yahoo_events__F-PB__5y.json` | 473 |
| `yahoo_events__F-PC__5y.json` | 473 |
| `yahoo_events__F-PD__5y.json` | 473 |
| `yahoo_events__FAF__5y.json` | 471 |
| `yahoo_events__FANG__5y.json` | 473 |
| `yahoo_events__FAST__5y.json` | 473 |
| `yahoo_events__FBIN__5y.json` | 473 |
| `yahoo_events__FCNCA__5y.json` | 475 |
| `yahoo_events__FCN__5y.json` | 471 |
| `yahoo_events__FCX__5y.json` | 471 |
| `yahoo_events__FDS__5y.json` | 471 |
| `yahoo_events__FDX__5y.json` | 471 |
| `yahoo_events__FERG__5y.json` | 473 |
| `yahoo_events__FE__5y.json` | 469 |
| `yahoo_events__FFIV__5y.json` | 473 |
| `yahoo_events__FHB__5y.json` | 471 |
| `yahoo_events__FHN__5y.json` | 471 |
| `yahoo_events__FICO__5y.json` | 473 |
| `yahoo_events__FISV__5y.json` | 473 |
| `yahoo_events__FIS__5y.json` | 471 |
| `yahoo_events__FITB__5y.json` | 473 |
| `yahoo_events__FIVE__5y.json` | 473 |
| `yahoo_events__FIVN__5y.json` | 473 |
| `yahoo_events__FIX__5y.json` | 471 |
| `yahoo_events__FLG__5y.json` | 471 |
| `yahoo_events__FLO__5y.json` | 471 |
| `yahoo_events__FLS__5y.json` | 471 |
| `yahoo_events__FLYD__5y.json` | 473 |
| `yahoo_events__FLYU__5y.json` | 473 |
| `yahoo_events__FMC__5y.json` | 471 |
| `yahoo_events__FNB__5y.json` | 471 |
| `yahoo_events__FND__5y.json` | 471 |
| `yahoo_events__FNF__5y.json` | 471 |
| `yahoo_events__FNGD__5y.json` | 473 |
| `yahoo_events__FNGO__5y.json` | 473 |
| `yahoo_events__FNGS__5y.json` | 473 |
| `yahoo_events__FNGU__5y.json` | 473 |
| `yahoo_events__FNV__5y.json` | 471 |
| `yahoo_events__FOUR__5y.json` | 473 |
| `yahoo_events__FOXA__5y.json` | 473 |
| `yahoo_events__FOX__5y.json` | 471 |
| `yahoo_events__FRPT__5y.json` | 473 |
| `yahoo_events__FRT__5y.json` | 471 |
| `yahoo_events__FR__5y.json` | 469 |
| `yahoo_events__FSLR__5y.json` | 473 |
| `yahoo_events__FTI__5y.json` | 471 |
| `yahoo_events__FTNT__5y.json` | 473 |
| `yahoo_events__FTRE__5y.json` | 473 |
| `yahoo_events__FTV__5y.json` | 471 |
| `yahoo_events__FWONA__5y.json` | 475 |
| `yahoo_events__FWONK__5y.json` | 475 |
| `yahoo_events__F__5y.json` | 467 |
| `yahoo_events__GAP__5y.json` | 471 |
| `yahoo_events__GDDY__5y.json` | 473 |
| `yahoo_events__GDXD__5y.json` | 473 |
| `yahoo_events__GDXU__5y.json` | 473 |
| `yahoo_events__GD__5y.json` | 469 |
| `yahoo_events__GEHC__5y.json` | 473 |
| `yahoo_events__GEN__5y.json` | 471 |
| `yahoo_events__GEV__5y.json` | 471 |
| `yahoo_events__GE__5y.json` | 469 |
| `yahoo_events__GFS__5y.json` | 471 |
| `yahoo_events__GGG__5y.json` | 471 |
| `yahoo_events__GILD__5y.json` | 473 |
| `yahoo_events__GIS__5y.json` | 471 |
| `yahoo_events__GLAXF__5y.json` | 475 |
| `yahoo_events__GLOB__5y.json` | 473 |
| `yahoo_events__GLPI__5y.json` | 473 |
| `yahoo_events__GLW__5y.json` | 471 |
| `yahoo_events__GL__5y.json` | 469 |
| `yahoo_events__GMED__5y.json` | 473 |
| `yahoo_events__GME__5y.json` | 471 |
| `yahoo_events__GM__5y.json` | 469 |
| `yahoo_events__GNRC__5y.json` | 473 |
| `yahoo_events__GNTX__5y.json` | 473 |
| `yahoo_events__GOOGL__5y.json` | 475 |
| `yahoo_events__GOOGM__5y.json` | 475 |
| `yahoo_events__GOOGN__5y.json` | 475 |
| `yahoo_events__GOOG__5y.json` | 473 |
| `yahoo_events__GO__5y.json` | 469 |
| `yahoo_events__GPC__5y.json` | 471 |
| `yahoo_events__GPK__5y.json` | 471 |
| `yahoo_events__GPN__5y.json` | 471 |
| `yahoo_events__GRAL__5y.json` | 473 |
| `yahoo_events__GRMN__5y.json` | 473 |
| `yahoo_events__GS-PA__5y.json` | 475 |
| `yahoo_events__GS-PC__5y.json` | 475 |
| `yahoo_events__GS-PD__5y.json` | 475 |
| `yahoo_events__GSCE__5y.json` | 473 |
| `yahoo_events__GSK__5y.json` | 471 |
| `yahoo_events__GS__5y.json` | 469 |
| `yahoo_events__GTES__5y.json` | 473 |
| `yahoo_events__GTLB__5y.json` | 473 |
| `yahoo_events__GTM__5y.json` | 471 |
| `yahoo_events__GWRE__5y.json` | 473 |
| `yahoo_events__GWW__5y.json` | 471 |
| `yahoo_events__GXO__5y.json` | 471 |
| `yahoo_events__G__5y.json` | 467 |
| `yahoo_events__HAL__5y.json` | 471 |
| `yahoo_events__HAS__5y.json` | 471 |
| `yahoo_events__HAYW__5y.json` | 473 |
| `yahoo_events__HBAN__5y.json` | 473 |
| `yahoo_events__HBCYF__5y.json` | 475 |
| `yahoo_events__HCA__5y.json` | 471 |
| `yahoo_events__HDB__5y.json` | 471 |
| `yahoo_events__HD__5y.json` | 469 |
| `yahoo_events__HEI-A__5y.json` | 475 |
| `yahoo_events__HEI__5y.json` | 471 |
| `yahoo_events__HE__5y.json` | 469 |
| `yahoo_events__HHH__5y.json` | 471 |
| `yahoo_events__HIG__5y.json` | 471 |
| `yahoo_events__HII__5y.json` | 471 |
| `yahoo_events__HIW__5y.json` | 471 |
| `yahoo_events__HLI__5y.json` | 471 |
| `yahoo_events__HLT__5y.json` | 471 |
| `yahoo_events__HOG__5y.json` | 471 |
| `yahoo_events__HONA__5y.json` | 473 |
| `yahoo_events__HON__5y.json` | 471 |
| `yahoo_events__HOOD__5y.json` | 473 |
| `yahoo_events__HPE-PC__5y.json` | 477 |
| `yahoo_events__HPE__5y.json` | 471 |
| `yahoo_events__HPQ__5y.json` | 471 |
| `yahoo_events__HRB__5y.json` | 471 |
| `yahoo_events__HRL__5y.json` | 471 |
| `yahoo_events__HR__5y.json` | 469 |
| `yahoo_events__HSBC__5y.json` | 473 |
| `yahoo_events__HSIC__5y.json` | 473 |
| `yahoo_events__HST__5y.json` | 471 |
| `yahoo_events__HSY__5y.json` | 471 |
| `yahoo_events__HTHIF__5y.json` | 475 |
| `yahoo_events__HTHIY__5y.json` | 475 |
| `yahoo_events__HTZ__5y.json` | 471 |
| `yahoo_events__HUBB__5y.json` | 473 |
| `yahoo_events__HUBS__5y.json` | 473 |
| `yahoo_events__HUM__5y.json` | 471 |
| `yahoo_events__HUN__5y.json` | 471 |
| `yahoo_events__HWM__5y.json` | 471 |
| `yahoo_events__HXL__5y.json` | 471 |
| `yahoo_events__HYGD__5y.json` | 473 |
| `yahoo_events__HYGU__5y.json` | 473 |
| `yahoo_events__H__5y.json` | 467 |
| `yahoo_events__IART__5y.json` | 473 |
| `yahoo_events__IBKR__5y.json` | 473 |
| `yahoo_events__IBM__5y.json` | 471 |
| `yahoo_events__ICE__5y.json` | 471 |
| `yahoo_events__ICLR__5y.json` | 473 |
| `yahoo_events__ICUI__5y.json` | 473 |
| `yahoo_events__IDA__5y.json` | 471 |
| `yahoo_events__IDXX__5y.json` | 473 |
| `yahoo_events__IEX__5y.json` | 471 |
| `yahoo_events__IFF__5y.json` | 471 |
| `yahoo_events__ILMN__5y.json` | 473 |
| `yahoo_events__INCY__5y.json` | 473 |
| `yahoo_events__INGM__5y.json` | 473 |
| `yahoo_events__INGR__5y.json` | 473 |
| `yahoo_events__INGVF__5y.json` | 475 |
| `yahoo_events__ING__5y.json` | 471 |
| `yahoo_events__INSP__5y.json` | 473 |
| `yahoo_events__INTC__5y.json` | 473 |
| `yahoo_events__INTU__5y.json` | 473 |
| `yahoo_events__INVH__5y.json` | 473 |
| `yahoo_events__IONS__5y.json` | 473 |
| `yahoo_events__IPGP__5y.json` | 473 |
| `yahoo_events__IP__5y.json` | 469 |
| `yahoo_events__IQV__5y.json` | 471 |
| `yahoo_events__IRDM__5y.json` | 473 |
| `yahoo_events__IRM__5y.json` | 471 |
| `yahoo_events__IR__5y.json` | 469 |
| `yahoo_events__ISRG__5y.json` | 473 |
| `yahoo_events__ITT__5y.json` | 471 |
| `yahoo_events__ITUB__5y.json` | 473 |
| `yahoo_events__ITW__5y.json` | 471 |
| `yahoo_events__IT__5y.json` | 469 |
| `yahoo_events__IVZ__5y.json` | 471 |
| `yahoo_events__JAZZ__5y.json` | 473 |
| `yahoo_events__JBHT__5y.json` | 473 |
| `yahoo_events__JBL__5y.json` | 471 |
| `yahoo_events__JCI__5y.json` | 471 |
| `yahoo_events__JEF__5y.json` | 471 |
| `yahoo_events__JETD__5y.json` | 473 |
| `yahoo_events__JETU__5y.json` | 473 |
| `yahoo_events__JKHY__5y.json` | 473 |
| `yahoo_events__JLL__5y.json` | 471 |
| `yahoo_events__JNJ__5y.json` | 471 |
| `yahoo_events__JPM-PC__5y.json` | 477 |
| `yahoo_events__JPM-PD__5y.json` | 477 |
| `yahoo_events__JPM-PJ__5y.json` | 477 |
| `yahoo_events__JPM-PK__5y.json` | 477 |
| `yahoo_events__JPM-PL__5y.json` | 477 |
| `yahoo_events__JPM-PM__5y.json` | 477 |
| `yahoo_events__JPM__5y.json` | 471 |
| `yahoo_events__JPND__5y.json` | 473 |
| `yahoo_events__JPNU__5y.json` | 473 |
| `yahoo_events__J__5y.json` | 467 |
| `yahoo_events__KBR__5y.json` | 471 |
| `yahoo_events__KDP__5y.json` | 471 |
| `yahoo_events__KD__5y.json` | 469 |
| `yahoo_events__KEX__5y.json` | 471 |
| `yahoo_events__KEYS__5y.json` | 473 |
| `yahoo_events__KEY__5y.json` | 471 |
| `yahoo_events__KHC__5y.json` | 471 |
| `yahoo_events__KIM__5y.json` | 471 |
| `yahoo_events__KKR-PD__5y.json` | 477 |
| `yahoo_events__KKRS__5y.json` | 473 |
| `yahoo_events__KKRT__5y.json` | 473 |
| `yahoo_events__KKR__5y.json` | 471 |
| `yahoo_events__KLAC__5y.json` | 473 |
| `yahoo_events__KMB__5y.json` | 471 |
| `yahoo_events__KMI__5y.json` | 471 |
| `yahoo_events__KMPR__5y.json` | 473 |
| `yahoo_events__KMX__5y.json` | 471 |
| `yahoo_events__KNSL__5y.json` | 473 |
| `yahoo_events__KNX__5y.json` | 471 |
| `yahoo_events__KO__5y.json` | 469 |
| `yahoo_events__KRC__5y.json` | 471 |
| `yahoo_events__KR__5y.json` | 469 |
| `yahoo_events__KSS__5y.json` | 471 |
| `yahoo_events__KVUE__5y.json` | 473 |
| `yahoo_events__LAD__5y.json` | 471 |
| `yahoo_events__LAMR__5y.json` | 473 |
| `yahoo_events__LAZ__5y.json` | 471 |
| `yahoo_events__LBRDA__5y.json` | 475 |
| `yahoo_events__LBRDK__5y.json` | 475 |
| `yahoo_events__LBTYA__5y.json` | 475 |
| `yahoo_events__LBTYB__5y.json` | 475 |
| `yahoo_events__LBTYK__5y.json` | 475 |
| `yahoo_events__LCID__5y.json` | 473 |
| `yahoo_events__LDOS__5y.json` | 473 |
| `yahoo_events__LEA__5y.json` | 471 |
| `yahoo_events__LECO__5y.json` | 473 |
| `yahoo_events__LEG__5y.json` | 471 |
| `yahoo_events__LEN-B__5y.json` | 475 |
| `yahoo_events__LEN__5y.json` | 471 |
| `yahoo_events__LFUS__5y.json` | 473 |
| `yahoo_events__LHX__5y.json` | 471 |
| `yahoo_events__LH__5y.json` | 469 |
| `yahoo_events__LII__5y.json` | 471 |
| `yahoo_events__LINE__5y.json` | 473 |
| `yahoo_events__LIN__5y.json` | 471 |
| `yahoo_events__LITE__5y.json` | 473 |
| `yahoo_events__LKQ__5y.json` | 471 |
| `yahoo_events__LLDTF__5y.json` | 475 |
| `yahoo_events__LLOBF__5y.json` | 475 |
| `yahoo_events__LLYVA__5y.json` | 475 |
| `yahoo_events__LLYVK__5y.json` | 475 |
| `yahoo_events__LLY__5y.json` | 471 |
| `yahoo_events__LMT__5y.json` | 471 |
| `yahoo_events__LNC__5y.json` | 471 |
| `yahoo_events__LNG__5y.json` | 471 |
| `yahoo_events__LNT__5y.json` | 471 |
| `yahoo_events__LNWO__5y.json` | 473 |
| `yahoo_events__LOAR__5y.json` | 473 |
| `yahoo_events__LOPE__5y.json` | 473 |
| `yahoo_events__LOW__5y.json` | 471 |
| `yahoo_events__LPLA__5y.json` | 473 |
| `yahoo_events__LPX__5y.json` | 471 |
| `yahoo_events__LQDD__5y.json` | 473 |
| `yahoo_events__LQDU__5y.json` | 473 |
| `yahoo_events__LRCX__5y.json` | 473 |
| `yahoo_events__LSCC__5y.json` | 473 |
| `yahoo_events__LSTR__5y.json` | 473 |
| `yahoo_events__LULU__5y.json` | 473 |
| `yahoo_events__LUV__5y.json` | 471 |
| `yahoo_events__LVS__5y.json` | 471 |
| `yahoo_events__LW__5y.json` | 469 |
| `yahoo_events__LYB__5y.json` | 471 |
| `yahoo_events__LYFT__5y.json` | 473 |
| `yahoo_events__LYG__5y.json` | 471 |
| `yahoo_events__LYV__5y.json` | 471 |
| `yahoo_events__L__5y.json` | 467 |
| `yahoo_events__MAA__5y.json` | 471 |
| `yahoo_events__MANH__5y.json` | 473 |
| `yahoo_events__MAN__5y.json` | 471 |
| `yahoo_events__MAR__5y.json` | 471 |
| `yahoo_events__MAS__5y.json` | 471 |
| `yahoo_events__MAT__5y.json` | 471 |
| `yahoo_events__MA__5y.json` | 469 |
| `yahoo_events__MBFJF__5y.json` | 475 |
| `yahoo_events__MCD__5y.json` | 471 |
| `yahoo_events__MCHP__5y.json` | 473 |
| `yahoo_events__MCK__5y.json` | 471 |
| `yahoo_events__MCO__5y.json` | 471 |
| `yahoo_events__MDB__5y.json` | 471 |
| `yahoo_events__MDLZ__5y.json` | 473 |
| `yahoo_events__MDT__5y.json` | 471 |
| `yahoo_events__MDU__5y.json` | 471 |
| `yahoo_events__MEDP__5y.json` | 473 |
| `yahoo_events__MELI__5y.json` | 473 |
| `yahoo_events__MER-PK__5y.json` | 477 |
| `yahoo_events__MET-PA__5y.json` | 477 |
| `yahoo_events__MET-PE__5y.json` | 477 |
| `yahoo_events__MET-PF__5y.json` | 477 |
| `yahoo_events__META__5y.json` | 473 |
| `yahoo_events__MET__5y.json` | 471 |
| `yahoo_events__MFC__5y.json` | 471 |
| `yahoo_events__MFG__5y.json` | 471 |
| `yahoo_events__MGM__5y.json` | 471 |
| `yahoo_events__MHK__5y.json` | 471 |
| `yahoo_events__MIDD__5y.json` | 473 |
| `yahoo_events__MKC-V__5y.json` | 475 |
| `yahoo_events__MKC__5y.json` | 471 |
| `yahoo_events__MKL__5y.json` | 471 |
| `yahoo_events__MKSI__5y.json` | 473 |
| `yahoo_events__MKTX__5y.json` | 473 |
| `yahoo_events__MLM__5y.json` | 471 |
| `yahoo_events__MMM__5y.json` | 471 |
| `yahoo_events__MNGU__5y.json` | 473 |
| `yahoo_events__MNLCF__5y.json` | 475 |
| `yahoo_events__MNQFF__5y.json` | 475 |
| `yahoo_events__MNST__5y.json` | 473 |
| `yahoo_events__MNUFF__5y.json` | 475 |
| `yahoo_events__MNUPF__5y.json` | 475 |
| `yahoo_events__MOH__5y.json` | 471 |
| `yahoo_events__MORN__5y.json` | 473 |
| `yahoo_events__MOS__5y.json` | 471 |
| `yahoo_events__MO__5y.json` | 469 |
| `yahoo_events__MPC__5y.json` | 471 |
| `yahoo_events__MPLX__5y.json` | 473 |
| `yahoo_events__MPT__5y.json` | 471 |
| `yahoo_events__MPWR__5y.json` | 473 |
| `yahoo_events__MP__5y.json` | 469 |
| `yahoo_events__MRCY__5y.json` | 473 |
| `yahoo_events__MRK__5y.json` | 471 |
| `yahoo_events__MRNA__5y.json` | 473 |
| `yahoo_events__MRSH__5y.json` | 473 |
| `yahoo_events__MRVI__5y.json` | 473 |
| `yahoo_events__MRVL__5y.json` | 473 |
| `yahoo_events__MS-PA__5y.json` | 475 |
| `yahoo_events__MS-PE__5y.json` | 475 |
| `yahoo_events__MS-PF__5y.json` | 475 |
| `yahoo_events__MS-PI__5y.json` | 475 |
| `yahoo_events__MS-PK__5y.json` | 475 |
| `yahoo_events__MS-PL__5y.json` | 475 |
| `yahoo_events__MS-PO__5y.json` | 475 |
| `yahoo_events__MS-PP__5y.json` | 475 |
| `yahoo_events__MS-PQ__5y.json` | 475 |
| `yahoo_events__MSA__5y.json` | 471 |
| `yahoo_events__MSCI__5y.json` | 473 |
| `yahoo_events__MSFT__5y.json` | 473 |
| `yahoo_events__MSGS__5y.json` | 473 |
| `yahoo_events__MSI__5y.json` | 471 |
| `yahoo_events__MSM__5y.json` | 471 |
| `yahoo_events__MSTR__5y.json` | 473 |
| `yahoo_events__MS__5y.json` | 469 |
| `yahoo_events__MTB__5y.json` | 471 |
| `yahoo_events__MTCH__5y.json` | 473 |
| `yahoo_events__MTDR__5y.json` | 473 |
| `yahoo_events__MTD__5y.json` | 471 |
| `yahoo_events__MTG__5y.json` | 471 |
| `yahoo_events__MTN__5y.json` | 471 |
| `yahoo_events__MTSI__5y.json` | 473 |
| `yahoo_events__MTZ__5y.json` | 471 |
| `yahoo_events__MT__5y.json` | 469 |
| `yahoo_events__MUFG__5y.json` | 473 |
| `yahoo_events__MUSA__5y.json` | 473 |
| `yahoo_events__MU__5y.json` | 469 |
| `yahoo_events__MZHOF__5y.json` | 475 |
| `yahoo_events__M__5y.json` | 467 |
| `yahoo_events__NATL__5y.json` | 473 |
| `yahoo_events__NBIS__5y.json` | 473 |
| `yahoo_events__NBIX__5y.json` | 473 |
| `yahoo_events__NCLH__5y.json` | 473 |
| `yahoo_events__NCNO__5y.json` | 473 |
| `yahoo_events__NDAQ__5y.json` | 473 |
| `yahoo_events__NDSN__5y.json` | 473 |
| `yahoo_events__NEE-PN__5y.json` | 477 |
| `yahoo_events__NEE-PS__5y.json` | 477 |
| `yahoo_events__NEE-PT__5y.json` | 477 |
| `yahoo_events__NEE-PU__5y.json` | 477 |
| `yahoo_events__NEE-PV__5y.json` | 477 |
| `yahoo_events__NEE-PW__5y.json` | 477 |
| `yahoo_events__NEE__5y.json` | 471 |
| `yahoo_events__NEMCL__5y.json` | 475 |
| `yahoo_events__NEM__5y.json` | 471 |
| `yahoo_events__NETTF__5y.json` | 475 |
| `yahoo_events__NET__5y.json` | 471 |
| `yahoo_events__NEU__5y.json` | 471 |
| `yahoo_events__NEWEN__5y.json` | 475 |
| `yahoo_events__NFE__5y.json` | 471 |
| `yahoo_events__NFG__5y.json` | 471 |
| `yahoo_events__NFLX__5y.json` | 473 |
| `yahoo_events__NGGTF__5y.json` | 475 |
| `yahoo_events__NGG__5y.json` | 471 |
| `yahoo_events__NI__5y.json` | 469 |
| `yahoo_events__NKE__5y.json` | 471 |
| `yahoo_events__NLOP__5y.json` | 473 |
| `yahoo_events__NLY__5y.json` | 471 |
| `yahoo_events__NMKBP__5y.json` | 475 |
| `yahoo_events__NMKCP__5y.json` | 475 |
| `yahoo_events__NMPWP__5y.json` | 475 |
| `yahoo_events__NNN__5y.json` | 471 |
| `yahoo_events__NOC__5y.json` | 471 |
| `yahoo_events__NOKBF__5y.json` | 475 |
| `yahoo_events__NOK__5y.json` | 471 |
| `yahoo_events__NONOF__5y.json` | 475 |
| `yahoo_events__NOV__5y.json` | 471 |
| `yahoo_events__NOW__5y.json` | 471 |
| `yahoo_events__NRGD__5y.json` | 473 |
| `yahoo_events__NRGU__5y.json` | 473 |
| `yahoo_events__NRG__5y.json` | 471 |
| `yahoo_events__NSC__5y.json` | 471 |
| `yahoo_events__NTAP__5y.json` | 473 |
| `yahoo_events__NTES__5y.json` | 473 |
| `yahoo_events__NTNX__5y.json` | 473 |
| `yahoo_events__NTRA__5y.json` | 473 |
| `yahoo_events__NTRS__5y.json` | 473 |
| `yahoo_events__NUE__5y.json` | 471 |
| `yahoo_events__NU__5y.json` | 469 |
| `yahoo_events__NVCR__5y.json` | 473 |
| `yahoo_events__NVDA__5y.json` | 473 |
| `yahoo_events__NVO__5y.json` | 471 |
| `yahoo_events__NVR__5y.json` | 471 |
| `yahoo_events__NVSEF__5y.json` | 475 |
| `yahoo_events__NVST__5y.json` | 473 |
| `yahoo_events__NVS__5y.json` | 471 |
| `yahoo_events__NVT__5y.json` | 471 |
| `yahoo_events__NWG__5y.json` | 471 |
| `yahoo_events__NWL__5y.json` | 471 |
| `yahoo_events__NWSA__5y.json` | 473 |
| `yahoo_events__NWS__5y.json` | 471 |
| `yahoo_events__NXPI__5y.json` | 473 |
| `yahoo_events__NXST__5y.json` | 473 |
| `yahoo_events__NYT__5y.json` | 471 |
| `yahoo_events__OC__5y.json` | 469 |
| `yahoo_events__ODFL__5y.json` | 473 |
| `yahoo_events__OGE__5y.json` | 471 |
| `yahoo_events__OGN__5y.json` | 471 |
| `yahoo_events__OHI__5y.json` | 471 |
| `yahoo_events__OILD__5y.json` | 473 |
| `yahoo_events__OILU__5y.json` | 473 |
| `yahoo_events__OKE__5y.json` | 471 |
| `yahoo_events__OKTA__5y.json` | 473 |
| `yahoo_events__OLED__5y.json` | 473 |
| `yahoo_events__OLLI__5y.json` | 473 |
| `yahoo_events__OLN__5y.json` | 471 |
| `yahoo_events__OLOXF__5y.json` | 475 |
| `yahoo_events__OLPX__5y.json` | 473 |
| `yahoo_events__OMC__5y.json` | 471 |
| `yahoo_events__OMF__5y.json` | 471 |
| `yahoo_events__ONTO__5y.json` | 473 |
| `yahoo_events__ON__5y.json` | 469 |
| `yahoo_events__ORCL-PD__5y.json` | 479 |
| `yahoo_events__ORCL__5y.json` | 473 |
| `yahoo_events__ORI__5y.json` | 471 |
| `yahoo_events__ORLY__5y.json` | 473 |
| `yahoo_events__OSK__5y.json` | 471 |
| `yahoo_events__OTIS__5y.json` | 473 |
| `yahoo_events__OVV__5y.json` | 471 |
| `yahoo_events__OWL__5y.json` | 471 |
| `yahoo_events__OXY-WT__5y.json` | 477 |
| `yahoo_events__OXY__5y.json` | 471 |
| `yahoo_events__OZK__5y.json` | 471 |
| `yahoo_events__O__5y.json` | 467 |
| `yahoo_events__PAG__5y.json` | 471 |
| `yahoo_events__PANW__5y.json` | 473 |
| `yahoo_events__PARA__5y.json` | 473 |
| `yahoo_events__PATH__5y.json` | 473 |
| `yahoo_events__PAYC__5y.json` | 473 |
| `yahoo_events__PAYX__5y.json` | 473 |
| `yahoo_events__PBR-A__5y.json` | 475 |
| `yahoo_events__PBR__5y.json` | 471 |
| `yahoo_events__PB__5y.json` | 469 |
| `yahoo_events__PCAR__5y.json` | 473 |
| `yahoo_events__PCG__5y.json` | 471 |
| `yahoo_events__PCOR__5y.json` | 473 |
| `yahoo_events__PCTY__5y.json` | 473 |
| `yahoo_events__PDD__5y.json` | 471 |
| `yahoo_events__PEGA__5y.json` | 473 |
| `yahoo_events__PEG__5y.json` | 471 |
| `yahoo_events__PENN__5y.json` | 473 |
| `yahoo_events__PEN__5y.json` | 471 |
| `yahoo_events__PEP__5y.json` | 471 |
| `yahoo_events__PFE__5y.json` | 471 |
| `yahoo_events__PFGC__5y.json` | 473 |
| `yahoo_events__PFG__5y.json` | 471 |
| `yahoo_events__PGR__5y.json` | 471 |
| `yahoo_events__PG__5y.json` | 469 |
| `yahoo_events__PHIN__5y.json` | 473 |
| `yahoo_events__PHM__5y.json` | 471 |
| `yahoo_events__PH__5y.json` | 469 |
| `yahoo_events__PII__5y.json` | 471 |
| `yahoo_events__PINC__5y.json` | 473 |
| `yahoo_events__PINS__5y.json` | 473 |
| `yahoo_events__PKG__5y.json` | 471 |
| `yahoo_events__PK__5y.json` | 469 |
| `yahoo_events__PLDGP__5y.json` | 475 |
| `yahoo_events__PLD__5y.json` | 471 |
| `yahoo_events__PLNT__5y.json` | 473 |
| `yahoo_events__PLTK__5y.json` | 473 |
| `yahoo_events__PLTR__5y.json` | 473 |
| `yahoo_events__PLUG__5y.json` | 473 |
| `yahoo_events__PM__5y.json` | 469 |
| `yahoo_events__PNC__5y.json` | 471 |
| `yahoo_events__PNFP__5y.json` | 473 |
| `yahoo_events__PNR__5y.json` | 471 |
| `yahoo_events__PNW__5y.json` | 471 |
| `yahoo_events__PODD__5y.json` | 473 |
| `yahoo_events__POOL__5y.json` | 473 |
| `yahoo_events__POST__5y.json` | 473 |
| `yahoo_events__PPC__5y.json` | 471 |
| `yahoo_events__PPG__5y.json` | 471 |
| `yahoo_events__PPLI__5y.json` | 473 |
| `yahoo_events__PPL__5y.json` | 471 |
| `yahoo_events__PRGO__5y.json` | 473 |
| `yahoo_events__PRI__5y.json` | 471 |
| `yahoo_events__PRU__5y.json` | 471 |
| `yahoo_events__PR__5y.json` | 469 |
| `yahoo_events__PSA-PF__5y.json` | 477 |
| `yahoo_events__PSA-PG__5y.json` | 477 |
| `yahoo_events__PSA-PH__5y.json` | 477 |
| `yahoo_events__PSA-PI__5y.json` | 477 |
| `yahoo_events__PSA-PJ__5y.json` | 477 |
| `yahoo_events__PSA-PK__5y.json` | 477 |
| `yahoo_events__PSA-PL__5y.json` | 477 |
| `yahoo_events__PSA-PM__5y.json` | 477 |
| `yahoo_events__PSA-PN__5y.json` | 477 |
| `yahoo_events__PSA-PO__5y.json` | 477 |
| `yahoo_events__PSA-PP__5y.json` | 477 |
| `yahoo_events__PSA-PQ__5y.json` | 477 |
| `yahoo_events__PSA-PR__5y.json` | 477 |
| `yahoo_events__PSA-PS__5y.json` | 477 |
| `yahoo_events__PSA-PT__5y.json` | 477 |
| `yahoo_events__PSA-PU__5y.json` | 477 |
| `yahoo_events__PSA__5y.json` | 471 |
| `yahoo_events__PSKY__5y.json` | 473 |
| `yahoo_events__PSN__5y.json` | 471 |
| `yahoo_events__PSX__5y.json` | 471 |
| `yahoo_events__PTC__5y.json` | 471 |
| `yahoo_events__PTON__5y.json` | 473 |
| `yahoo_events__PVH__5y.json` | 471 |
| `yahoo_events__PWR__5y.json` | 471 |
| `yahoo_events__PYPL__5y.json` | 473 |
| `yahoo_events__P__5y.json` | 467 |
| `yahoo_events__QCOM__5y.json` | 473 |
| `yahoo_events__QDEL__5y.json` | 473 |
| `yahoo_events__QGEN__5y.json` | 473 |
| `yahoo_events__QRVO__5y.json` | 473 |
| `yahoo_events__QS__5y.json` | 469 |
| `yahoo_events__RACE__5y.json` | 473 |
| `yahoo_events__RARE__5y.json` | 473 |
| `yahoo_events__RBA__5y.json` | 471 |
| `yahoo_events__RBC__5y.json` | 471 |
| `yahoo_events__RBLX__5y.json` | 473 |
| `yahoo_events__RBSPF__5y.json` | 475 |
| `yahoo_events__RCL__5y.json` | 471 |
| `yahoo_events__REGN__5y.json` | 473 |
| `yahoo_events__REG__5y.json` | 471 |
| `yahoo_events__RELX__5y.json` | 473 |
| `yahoo_events__REXR__5y.json` | 473 |
| `yahoo_events__REYN__5y.json` | 473 |
| `yahoo_events__RF__5y.json` | 469 |
| `yahoo_events__RGA__5y.json` | 471 |
| `yahoo_events__RGEN__5y.json` | 473 |
| `yahoo_events__RGLD__5y.json` | 473 |
| `yahoo_events__RHI__5y.json` | 471 |
| `yahoo_events__RH__5y.json` | 469 |
| `yahoo_events__RIO__5y.json` | 471 |
| `yahoo_events__RITM__5y.json` | 473 |
| `yahoo_events__RIVN__5y.json` | 473 |
| `yahoo_events__RJF__5y.json` | 471 |
| `yahoo_events__RKT__5y.json` | 471 |
| `yahoo_events__RLI__5y.json` | 471 |
| `yahoo_events__RLXXF__5y.json` | 475 |
| `yahoo_events__RL__5y.json` | 469 |
| `yahoo_events__RMD__5y.json` | 471 |
| `yahoo_events__RNG__5y.json` | 471 |
| `yahoo_events__RNR__5y.json` | 471 |
| `yahoo_events__ROIV__5y.json` | 473 |
| `yahoo_events__ROKU__5y.json` | 473 |
| `yahoo_events__ROK__5y.json` | 471 |
| `yahoo_events__ROL__5y.json` | 471 |
| `yahoo_events__ROP__5y.json` | 471 |
| `yahoo_events__ROST__5y.json` | 473 |
| `yahoo_events__RPM__5y.json` | 471 |
| `yahoo_events__RPRX__5y.json` | 473 |
| `yahoo_events__RRC__5y.json` | 471 |
| `yahoo_events__RRX__5y.json` | 471 |
| `yahoo_events__RSG__5y.json` | 471 |
| `yahoo_events__RS__5y.json` | 469 |
| `yahoo_events__RTPPF__5y.json` | 475 |
| `yahoo_events__RTX__5y.json` | 471 |
| `yahoo_events__RUN__5y.json` | 471 |
| `yahoo_events__RVTY__5y.json` | 473 |
| `yahoo_events__RYAN__5y.json` | 473 |
| `yahoo_events__RYDAF__5y.json` | 475 |
| `yahoo_events__RYLBF__5y.json` | 475 |
| `yahoo_events__RYN__5y.json` | 471 |
| `yahoo_events__RY__5y.json` | 469 |
| `yahoo_events__R__5y.json` | 467 |
| `yahoo_events__SAIA__5y.json` | 473 |
| `yahoo_events__SAIC__5y.json` | 473 |
| `yahoo_events__SAM__5y.json` | 471 |
| `yahoo_events__SAN__5y.json` | 471 |
| `yahoo_events__SAPGF__5y.json` | 475 |
| `yahoo_events__SAP__5y.json` | 471 |
| `yahoo_events__SARO__5y.json` | 473 |
| `yahoo_events__SBAC__5y.json` | 473 |
| `yahoo_events__SBUX__5y.json` | 473 |
| `yahoo_events__SCCO__5y.json` | 473 |
| `yahoo_events__SCHW-PD__5y.json` | 479 |
| `yahoo_events__SCHW-PJ__5y.json` | 479 |
| `yahoo_events__SCHW__5y.json` | 473 |
| `yahoo_events__SCI__5y.json` | 471 |
| `yahoo_events__SEB__5y.json` | 471 |
| `yahoo_events__SEG__5y.json` | 471 |
| `yahoo_events__SEIC__5y.json` | 473 |
| `yahoo_events__SE__5y.json` | 469 |
| `yahoo_events__SF-PB__5y.json` | 475 |
| `yahoo_events__SF-PC__5y.json` | 475 |
| `yahoo_events__SF-PD__5y.json` | 475 |
| `yahoo_events__SFB__5y.json` | 471 |
| `yahoo_events__SF__5y.json` | 469 |
| `yahoo_events__SGI__5y.json` | 471 |
| `yahoo_events__SHC__5y.json` | 471 |
| `yahoo_events__SHEL__5y.json` | 473 |
| `yahoo_events__SHNY__5y.json` | 473 |
| `yahoo_events__SHOP__5y.json` | 473 |
| `yahoo_events__SHW__5y.json` | 471 |
| `yahoo_events__SIRI__5y.json` | 473 |
| `yahoo_events__SITE__5y.json` | 473 |
| `yahoo_events__SJM__5y.json` | 471 |
| `yahoo_events__SLB__5y.json` | 471 |
| `yahoo_events__SLGN__5y.json` | 473 |
| `yahoo_events__SLM__5y.json` | 471 |
| `yahoo_events__SMCI__5y.json` | 473 |
| `yahoo_events__SMFG__5y.json` | 473 |
| `yahoo_events__SMFNF__5y.json` | 475 |
| `yahoo_events__SMG__5y.json` | 471 |
| `yahoo_events__SMHD__5y.json` | 473 |
| `yahoo_events__SMHU__5y.json` | 473 |
| `yahoo_events__SNA__5y.json` | 471 |
| `yahoo_events__SNDK__5y.json` | 473 |
| `yahoo_events__SNDR__5y.json` | 473 |
| `yahoo_events__SNEJF__5y.json` | 475 |
| `yahoo_events__SNOW__5y.json` | 473 |
| `yahoo_events__SNPS__5y.json` | 473 |
| `yahoo_events__SNX__5y.json` | 471 |
| `yahoo_events__SNYNF__5y.json` | 475 |
| `yahoo_events__SNY__5y.json` | 471 |
| `yahoo_events__SN__5y.json` | 469 |
| `yahoo_events__SOFI__5y.json` | 473 |
| `yahoo_events__SOJC__5y.json` | 473 |
| `yahoo_events__SOJD__5y.json` | 473 |
| `yahoo_events__SOJE__5y.json` | 473 |
| `yahoo_events__SOJF__5y.json` | 473 |
| `yahoo_events__SOLV__5y.json` | 473 |
| `yahoo_events__SOMN__5y.json` | 473 |
| `yahoo_events__SONY__5y.json` | 473 |
| `yahoo_events__SON__5y.json` | 471 |
| `yahoo_events__SO__5y.json` | 469 |
| `yahoo_events__SPB__5y.json` | 471 |
| `yahoo_events__SPG-PJ__5y.json` | 477 |
| `yahoo_events__SPGI__5y.json` | 473 |
| `yahoo_events__SPG__5y.json` | 471 |
| `yahoo_events__SPOT__5y.json` | 473 |
| `yahoo_events__SPYU__5y.json` | 473 |
| `yahoo_events__SREA__5y.json` | 473 |
| `yahoo_events__SRE__5y.json` | 471 |
| `yahoo_events__SRPT__5y.json` | 473 |
| `yahoo_events__SSD__5y.json` | 471 |
| `yahoo_events__SSNC__5y.json` | 473 |
| `yahoo_events__SSRM__5y.json` | 473 |
| `yahoo_events__STAG__5y.json` | 473 |
| `yahoo_events__STE__5y.json` | 471 |
| `yahoo_events__STLD__5y.json` | 473 |
| `yahoo_events__STOHF__5y.json` | 475 |
| `yahoo_events__STRC__5y.json` | 473 |
| `yahoo_events__STRD__5y.json` | 473 |
| `yahoo_events__STRF__5y.json` | 473 |
| `yahoo_events__STRK__5y.json` | 473 |
| `yahoo_events__STT-PG__5y.json` | 477 |
| `yahoo_events__STT__5y.json` | 471 |
| `yahoo_events__STWD__5y.json` | 473 |
| `yahoo_events__STX__5y.json` | 471 |
| `yahoo_events__STZ__5y.json` | 471 |
| `yahoo_events__ST__5y.json` | 469 |
| `yahoo_events__SUI__5y.json` | 471 |
| `yahoo_events__SU__5y.json` | 469 |
| `yahoo_events__SWKS__5y.json` | 473 |
| `yahoo_events__SWK__5y.json` | 471 |
| `yahoo_events__SW__5y.json` | 469 |
| `yahoo_events__SYF__5y.json` | 471 |
| `yahoo_events__SYK__5y.json` | 471 |
| `yahoo_events__SYY__5y.json` | 471 |
| `yahoo_events__S__5y.json` | 467 |
| `yahoo_events__T-PA__5y.json` | 473 |
| `yahoo_events__T-PC__5y.json` | 473 |
| `yahoo_events__TAK__5y.json` | 471 |
| `yahoo_events__TAP-A__5y.json` | 475 |
| `yahoo_events__TAP__5y.json` | 471 |
| `yahoo_events__TAWN__5y.json` | 473 |
| `yahoo_events__TBB__5y.json` | 471 |
| `yahoo_events__TDBCP__5y.json` | 475 |
| `yahoo_events__TDC__5y.json` | 471 |
| `yahoo_events__TDG__5y.json` | 471 |
| `yahoo_events__TDOC__5y.json` | 473 |
| `yahoo_events__TDY__5y.json` | 471 |
| `yahoo_events__TD__5y.json` | 469 |
| `yahoo_events__TEAM__5y.json` | 473 |
| `yahoo_events__TECH__5y.json` | 473 |
| `yahoo_events__TEL__5y.json` | 471 |
| `yahoo_events__TER__5y.json` | 471 |
| `yahoo_events__TFC-PI__5y.json` | 477 |
| `yahoo_events__TFC-PO__5y.json` | 477 |
| `yahoo_events__TFC-PR__5y.json` | 477 |
| `yahoo_events__TFC__5y.json` | 471 |
| `yahoo_events__TFSL__5y.json` | 473 |
| `yahoo_events__TFX__5y.json` | 471 |
| `yahoo_events__TGT__5y.json` | 471 |
| `yahoo_events__THC__5y.json` | 471 |
| `yahoo_events__THG__5y.json` | 471 |
| `yahoo_events__THO__5y.json` | 471 |
| `yahoo_events__TJX__5y.json` | 471 |
| `yahoo_events__TKO__5y.json` | 471 |
| `yahoo_events__TKPHF__5y.json` | 475 |
| `yahoo_events__TKR__5y.json` | 471 |
| `yahoo_events__TMO__5y.json` | 471 |
| `yahoo_events__TMUSI__5y.json` | 475 |
| `yahoo_events__TMUSL__5y.json` | 475 |
| `yahoo_events__TMUSZ__5y.json` | 475 |
| `yahoo_events__TMUS__5y.json` | 473 |
| `yahoo_events__TM__5y.json` | 469 |
| `yahoo_events__TNDM__5y.json` | 473 |
| `yahoo_events__TNL__5y.json` | 471 |
| `yahoo_events__TOL__5y.json` | 471 |
| `yahoo_events__TOST__5y.json` | 473 |
| `yahoo_events__TOYOF__5y.json` | 475 |
| `yahoo_events__TPEI__5y.json` | 473 |
| `yahoo_events__TPG__5y.json` | 471 |
| `yahoo_events__TPL__5y.json` | 471 |
| `yahoo_events__TPR__5y.json` | 471 |
| `yahoo_events__TREX__5y.json` | 473 |
| `yahoo_events__TRGP__5y.json` | 473 |
| `yahoo_events__TRIP__5y.json` | 473 |
| `yahoo_events__TRMB__5y.json` | 473 |
| `yahoo_events__TROW__5y.json` | 473 |
| `yahoo_events__TRU__5y.json` | 471 |
| `yahoo_events__TRV__5y.json` | 471 |
| `yahoo_events__TSCO__5y.json` | 473 |
| `yahoo_events__TSLA__5y.json` | 473 |
| `yahoo_events__TSN__5y.json` | 471 |
| `yahoo_events__TTC__5y.json` | 471 |
| `yahoo_events__TTD__5y.json` | 471 |
| `yahoo_events__TTEK__5y.json` | 473 |
| `yahoo_events__TTE__5y.json` | 471 |
| `yahoo_events__TTWO__5y.json` | 473 |
| `yahoo_events__TT__5y.json` | 469 |
| `yahoo_events__TWLO__5y.json` | 473 |
| `yahoo_events__TW__5y.json` | 469 |
| `yahoo_events__TXG__5y.json` | 471 |
| `yahoo_events__TXN__5y.json` | 471 |
| `yahoo_events__TXRH__5y.json` | 473 |
| `yahoo_events__TXT__5y.json` | 471 |
| `yahoo_events__TYL__5y.json` | 471 |
| `yahoo_events__T__5y.json` | 467 |
| `yahoo_events__UAA__5y.json` | 471 |
| `yahoo_events__UAL__5y.json` | 471 |
| `yahoo_events__UA__5y.json` | 469 |
| `yahoo_events__UBER__5y.json` | 473 |
| `yahoo_events__UBS__5y.json` | 471 |
| `yahoo_events__UDR__5y.json` | 471 |
| `yahoo_events__UGI__5y.json` | 471 |
| `yahoo_events__UHAL-B__5y.json` | 477 |
| `yahoo_events__UHAL__5y.json` | 473 |
| `yahoo_events__UHS__5y.json` | 471 |
| `yahoo_events__UI__5y.json` | 469 |
| `yahoo_events__ULTA__5y.json` | 473 |
| `yahoo_events__UL__5y.json` | 469 |
| `yahoo_events__UMC__5y.json` | 471 |
| `yahoo_events__UNH__5y.json` | 471 |
| `yahoo_events__UNLYF__5y.json` | 475 |
| `yahoo_events__UNM__5y.json` | 471 |
| `yahoo_events__UNP__5y.json` | 471 |
| `yahoo_events__UPS__5y.json` | 471 |
| `yahoo_events__URI__5y.json` | 471 |
| `yahoo_events__USB-PA__5y.json` | 477 |
| `yahoo_events__USB-PH__5y.json` | 477 |
| `yahoo_events__USB-PP__5y.json` | 477 |
| `yahoo_events__USB-PQ__5y.json` | 477 |
| `yahoo_events__USB-PR__5y.json` | 477 |
| `yahoo_events__USB-PS__5y.json` | 477 |
| `yahoo_events__USB__5y.json` | 471 |
| `yahoo_events__USFD__5y.json` | 473 |
| `yahoo_events__UTHR__5y.json` | 473 |
| `yahoo_events__UWMC__5y.json` | 473 |
| `yahoo_events__U__5y.json` | 467 |
| `yahoo_events__VAC__5y.json` | 471 |
| `yahoo_events__VALE__5y.json` | 473 |
| `yahoo_events__VEEV__5y.json` | 473 |
| `yahoo_events__VFC__5y.json` | 471 |
| `yahoo_events__VICI__5y.json` | 473 |
| `yahoo_events__VIRT__5y.json` | 473 |
| `yahoo_events__VKTX__5y.json` | 473 |
| `yahoo_events__VLO__5y.json` | 471 |
| `yahoo_events__VLTO__5y.json` | 473 |
| `yahoo_events__VMC__5y.json` | 471 |
| `yahoo_events__VMI__5y.json` | 471 |
| `yahoo_events__VNOM__5y.json` | 473 |
| `yahoo_events__VNO__5y.json` | 471 |
| `yahoo_events__VNT__5y.json` | 471 |
| `yahoo_events__VOYA__5y.json` | 473 |
| `yahoo_events__VRSK__5y.json` | 473 |
| `yahoo_events__VRSN__5y.json` | 473 |
| `yahoo_events__VRTX__5y.json` | 473 |
| `yahoo_events__VRT__5y.json` | 471 |
| `yahoo_events__VSAT__5y.json` | 473 |
| `yahoo_events__VSTS__5y.json` | 473 |
| `yahoo_events__VST__5y.json` | 471 |
| `yahoo_events__VSXY__5y.json` | 473 |
| `yahoo_events__VTRS__5y.json` | 473 |
| `yahoo_events__VTR__5y.json` | 471 |
| `yahoo_events__VVV__5y.json` | 471 |
| `yahoo_events__VYLD__5y.json` | 473 |
| `yahoo_events__VYX__5y.json` | 471 |
| `yahoo_events__VZ__5y.json` | 469 |
| `yahoo_events__V__5y.json` | 467 |
| `yahoo_events__WAB__5y.json` | 471 |
| `yahoo_events__WAL__5y.json` | 471 |
| `yahoo_events__WAT__5y.json` | 471 |
| `yahoo_events__WBD__5y.json` | 471 |
| `yahoo_events__WBS__5y.json` | 471 |
| `yahoo_events__WCC__5y.json` | 471 |
| `yahoo_events__WDAY__5y.json` | 473 |
| `yahoo_events__WDC__5y.json` | 471 |
| `yahoo_events__WEC__5y.json` | 471 |
| `yahoo_events__WELL__5y.json` | 473 |
| `yahoo_events__WEN__5y.json` | 471 |
| `yahoo_events__WEX__5y.json` | 471 |
| `yahoo_events__WFC-PA__5y.json` | 477 |
| `yahoo_events__WFC-PC__5y.json` | 477 |
| `yahoo_events__WFC-PD__5y.json` | 477 |
| `yahoo_events__WFC-PL__5y.json` | 477 |
| `yahoo_events__WFC-PY__5y.json` | 477 |
| `yahoo_events__WFC-PZ__5y.json` | 477 |
| `yahoo_events__WFCNP__5y.json` | 475 |
| `yahoo_events__WFC__5y.json` | 471 |
| `yahoo_events__WFRD__5y.json` | 473 |
| `yahoo_events__WHR__5y.json` | 471 |
| `yahoo_events__WH__5y.json` | 469 |
| `yahoo_events__WING__5y.json` | 473 |
| `yahoo_events__WLK__5y.json` | 471 |
| `yahoo_events__WMB__5y.json` | 471 |
| `yahoo_events__WMS__5y.json` | 471 |
| `yahoo_events__WMT__5y.json` | 471 |
| `yahoo_events__WM__5y.json` | 469 |
| `yahoo_events__WOLF__5y.json` | 473 |
| `yahoo_events__WOOF__5y.json` | 473 |
| `yahoo_events__WPC__5y.json` | 471 |
| `yahoo_events__WPM__5y.json` | 471 |
| `yahoo_events__WRB__5y.json` | 471 |
| `yahoo_events__WSC__5y.json` | 471 |
| `yahoo_events__WSM__5y.json` | 471 |
| `yahoo_events__WSO-B__5y.json` | 475 |
| `yahoo_events__WSO__5y.json` | 471 |
| `yahoo_events__WST__5y.json` | 471 |
| `yahoo_events__WTFC__5y.json` | 473 |
| `yahoo_events__WTID__5y.json` | 473 |
| `yahoo_events__WTIU__5y.json` | 473 |
| `yahoo_events__WTM__5y.json` | 471 |
| `yahoo_events__WTRG__5y.json` | 473 |
| `yahoo_events__WTW__5y.json` | 471 |
| `yahoo_events__WU__5y.json` | 469 |
| `yahoo_events__WWD__5y.json` | 471 |
| `yahoo_events__WYNN__5y.json` | 473 |
| `yahoo_events__WY__5y.json` | 469 |
| `yahoo_events__W__5y.json` | 467 |
| `yahoo_events__XEL__5y.json` | 471 |
| `yahoo_events__XLCD__5y.json` | 473 |
| `yahoo_events__XLCU__5y.json` | 473 |
| `yahoo_events__XLPD__5y.json` | 473 |
| `yahoo_events__XLPU__5y.json` | 473 |
| `yahoo_events__XOM__5y.json` | 471 |
| `yahoo_events__XPO__5y.json` | 471 |
| `yahoo_events__XP__5y.json` | 469 |
| `yahoo_events__XRAY__5y.json` | 473 |
| `yahoo_events__XYL__5y.json` | 471 |
| `yahoo_events__XYZ__5y.json` | 471 |
| `yahoo_events__YETI__5y.json` | 473 |
| `yahoo_events__YUM__5y.json` | 471 |
| `yahoo_events__ZBH__5y.json` | 471 |
| `yahoo_events__ZBRA__5y.json` | 473 |
| `yahoo_events__ZG__5y.json` | 469 |
| `yahoo_events__ZION__5y.json` | 473 |
| `yahoo_events__ZM__5y.json` | 469 |
| `yahoo_events__ZS__5y.json` | 469 |
| `yahoo_events__ZTS__5y.json` | 471 |
| `yahoo_events__Z__5y.json` | 467 |

#### R16 — 정리 필요 / Tiingo/Yahoo / 34파일

- 공통 경로 prefix: `implementation/data/raw/`
- 종류: JSON, 취득 진단, 종가, 가격 비교 파생값.
- 출처: Tiingo/Yahoo.
- 용도: fetch_tiingo_prices.run의 실제 Tiingo/Yahoo 종가 비교 calibration와 fallback 취득 로그. run 파일 자체는 분석 입력이 아닌 진단 결과이지만 Actions git-add 및 full raw cache/artifact 대상.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 정리 근거: 실제 `calibration[].tiingo_close`·`yahoo_close`와 가격 기반 `rel_diff`가 저장됐다. 가격 값을 재기재하지 않는다. 선택지: 합성 비교 fixture 교체 / 승인된 비공개 보존 후 공개본 정리 / 현재 tree에서 삭제; 과거 Git·Actions 사본의 처리 필요 여부는 별도 결정이다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `tiingo_run_1790379027.json` | 8,644 |
| `tiingo_run_1790379826.json` | 4,206 |
| `tiingo_run_1790380814.json` | 4,348 |
| `tiingo_run_1790382747.json` | 4,712 |
| `tiingo_run_1790383323.json` | 10,061 |
| `tiingo_run_1790385063.json` | 10,061 |
| `tiingo_run_1790386358.json` | 10,061 |
| `tiingo_run_1790387245.json` | 10,931 |
| `tiingo_run_1790387924.json` | 10,429 |
| `tiingo_run_1790389052.json` | 10,429 |
| `tiingo_run_1790390168.json` | 10,429 |
| `tiingo_run_1790392049.json` | 11,341 |
| `tiingo_run_1790397388.json` | 10,394 |
| `tiingo_run_1790398068.json` | 10,394 |
| `tiingo_run_1790398593.json` | 10,394 |
| `tiingo_run_1790401424.json` | 11,575 |
| `tiingo_run_1790402508.json` | 11,109 |
| `tiingo_run_1790403894.json` | 11,109 |
| `tiingo_run_1790404561.json` | 11,109 |
| `tiingo_run_1790405328.json` | 11,109 |
| `tiingo_run_1790406183.json` | 11,109 |
| `tiingo_run_1790407702.json` | 10,587 |
| `tiingo_run_1790409130.json` | 10,587 |
| `tiingo_run_1790410030.json` | 10,429 |
| `tiingo_run_1790410705.json` | 10,429 |
| `tiingo_run_1790415937.json` | 10,889 |
| `tiingo_run_1790416778.json` | 11,109 |
| `tiingo_run_1790468571.json` | 11,109 |
| `tiingo_run_1790469494.json` | 11,109 |
| `tiingo_run_1790470568.json` | 11,109 |
| `tiingo_run_1790471729.json` | 11,109 |
| `tiingo_run_1790491090.json` | 11,109 |
| `tiingo_run_1790494669.json` | 11,109 |
| `tiingo_run_1790495820.json` | 11,109 |

#### R17 — 판단 보류 / NPORT/SEC / 13파일

- 공통 경로 prefix: `implementation/data/raw/`
- 종류: JSON, 취득 진단, public_filing_identity_metadata, raw_text_fragment.
- 출처: NPORT/SEC.
- 용도: fetch_nport_reference의 fund membership/series/CIK/CUSIP provenance 및 식별 attestation run 진단; reported-price producer와 구분. 현재 holding market value/price/rank scalar 없음.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 보류 근거: run group=nport_run; numeric candidate keypaths=NONE 원문 fragment를 가격 없는 metadata로 자동 승격하지 않는다. 공개 원문 의미/전체 보존 범위의 추가 판독이 필요하다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `nport_run_1790407631.json` | 74,589 |
| `nport_run_1790409072.json` | 109,980 |
| `nport_run_1790409965.json` | 179,612 |
| `nport_run_1790410636.json` | 179,604 |
| `nport_run_1790415864.json` | 186,853 |
| `nport_run_1790416727.json` | 199,050 |
| `nport_run_1790468515.json` | 199,029 |
| `nport_run_1790469428.json` | 203,271 |
| `nport_run_1790470502.json` | 204,558 |
| `nport_run_1790471662.json` | 219,259 |
| `nport_run_1790491022.json` | 219,257 |
| `nport_run_1790494603.json` | 219,257 |
| `nport_run_1790495751.json` | 219,257 |

#### R18 — 판단 보류 / Stooq / 22파일

- 공통 경로 prefix: `implementation/data/raw/`
- 종류: JSON, 취득 진단, price_source_operation_metadata, raw_text_fragment.
- 출처: Stooq.
- 용도: fetch_stooq_prices의 calibration/fallback run 진단. 현재 calibration에는 symbol/status만 있고 실제 종가/rel_diff numeric field 없음; generator는 정상 응답이면 price를 기록할 수 있음.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 보류 근거: run group=stooq_run; numeric candidate keypaths=NONE 원문 fragment를 가격 없는 metadata로 자동 승격하지 않는다. 공개 원문 의미/전체 보존 범위의 추가 판독이 필요하다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `stooq_run_1790338051.json` | 3,579 |
| `stooq_run_1790339740.json` | 3,941 |
| `stooq_run_1790340497.json` | 3,944 |
| `stooq_run_1790341117.json` | 3,944 |
| `stooq_run_1790402522.json` | 2,603 |
| `stooq_run_1790403905.json` | 2,606 |
| `stooq_run_1790404571.json` | 2,606 |
| `stooq_run_1790405339.json` | 2,606 |
| `stooq_run_1790406194.json` | 2,606 |
| `stooq_run_1790407717.json` | 2,725 |
| `stooq_run_1790409140.json` | 2,727 |
| `stooq_run_1790410043.json` | 2,727 |
| `stooq_run_1790410717.json` | 2,727 |
| `stooq_run_1790415949.json` | 2,727 |
| `stooq_run_1790416785.json` | 2,606 |
| `stooq_run_1790468580.json` | 2,606 |
| `stooq_run_1790469505.json` | 2,606 |
| `stooq_run_1790470579.json` | 2,606 |
| `stooq_run_1790471740.json` | 2,606 |
| `stooq_run_1790491102.json` | 2,606 |
| `stooq_run_1790494680.json` | 2,606 |
| `stooq_run_1790495832.json` | 2,606 |

#### R19 — 판단 보류 / other / 1파일

- 공통 경로 prefix: `implementation/data/raw/`
- 종류: JSON, 취득 진단, fund_reference_diagnostic, raw_text_fragment.
- 출처: other.
- 용도: fetch_ishares_reference의 iShares fund holdings membership 취득 run metadata; actual holdings weight/price/value parsed rows는 현재 run에 없음.
- Pages: **미포함(NO), 이 raw 파일의 직접 copy/읽기 없음**. raw→보고서→Frozen 순위 등의 간접 파생은 §4에서 따로 판정한다. Actions 전체 raw cache/artifact 및 metadata commit 가능 경로는 유지/정리/보류와 별도로 남아 있다.
- 보류 근거: run group=ishares_run; numeric candidate keypaths=NONE 원문 fragment를 가격 없는 metadata로 자동 승격하지 않는다. 공개 원문 의미/전체 보존 범위의 추가 판독이 필요하다.

| 파일명(prefix와 합쳐 정확한 경로) | bytes |
| --- | ---: |
| `ishares_run_1790338018.json` | 2,030 |

### 7.2 기타 파일 — 원문·보고서·fixture·문서·소스·출력 경로

경로는 기준 tree 상대 경로다. `YES`는 현재 builder가 복사하는 코드/정적 asset, `CONDITIONAL`은 원 파일 일부 데이터가 producer/export/선택 경로로 들어가거나 다른 build에서만 생성되는 경우, `NO`는 현재 Pages 직접 copy 경로 없음이다. 원 파일이 아닌 projection으로 들어가는 Frozen 데이터는 §4의 source chain을 함께 읽는다. 분류의 근거는 아래 간명한 유형/출처/키와 §4·7.3의 정적 사용 경로에 따른다.

`CONDITIONAL`은 모두 확인 대기라는 뜻이 아니다. `official_snapshot_2024-12-31.json`의 순위 projection은 **현재 기본 Pages 생성 경로에 포함**된다(원 JSON 통째 복사 아님). `build_pages_cockpit.py`·`web_mvp.py`·producer와 관련 workflow는 **현재 빌드에 사용되는 소스**이며 Python/YAML 파일 자체를 Pages asset으로 복사하지 않는다. demo·일반 export·검증 fixture의 `CONDITIONAL`은 해당 선택 경로 실행 때의 포함 가능성이다. 이 세 관계를 표의 용도와 §7.3에서 구분하며 실제 배포 응답 여부는 별도 미확인이다.

| 경로 | bytes | 종류 | 출처 | 용도 | Pages | 분류 | 근거 |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| `.github/workflows/c21-real-data.yml` | 16,167 | workflow, 공개 출력 경로(소스/설정) | Yahoo/SEC/Tiingo/Stooq raw collectors and price-derived gate reports. | Manual workflow stores raw cache, uploads raw+gate reports, commits report/manifests and emits… | NO | 정리 필요 | .github/workflows/c21-real-data.yml:66-86 restore/cache |
| `.github/workflows/cockpit-pages.yml` | 6,408 | workflow, 공개 출력 경로(소스/설정) | Default public build consumes Frozen Universe through build_pages_cockpit. | Build/dir guard and archive guard bound Pages artifact; separate browser evidence artifact is … | CONDITIONAL | 정리 필요 | .github/workflows/cockpit-pages.yml:34-37 |
| `.github/workflows/qgv-common-contract-vnext.yml` | 1,563 | workflow, 계약 | Producer schema/contract code and tests. | Read-only dependency/test validation; no explicit provider fetch/public artifact publisher. | NO | 유지 가능 | .github/workflows/qgv-common-contract-vnext.yml:23-39 |
| `.github/workflows/web-mvp-validation.yml` | 2,160 | workflow, 공개 출력 경로(소스/설정) | Generic repository/demo build inherits actual Frozen and mixed LIVE_FETCH holding pr… | Builds temporary unstripped actual Frozen/mixed demo JSON and uploads screenshot/error evidenc… | NO | 정리 필요 | .github/workflows/web-mvp-validation.yml:30-43 |
| `.github/workflows/web-research-guard.yml` | 1,985 | workflow, 공개 출력 경로(소스/설정) | Research fixture begins with actual Frozen Universe and creates complete bundle vari… | Uploads evidence directory containing variant JSON; the fixture synthetic label does not make … | NO | 정리 필요 | .github/workflows/web-research-guard.yml:29-44 |
| `.github/workflows/web-state-presentation.yml` | 2,161 | workflow, 공개 출력 경로(소스/설정) | Presentation fixture uses FrozenUniverseProducer with actual Frozen universe. | Uploads evidence directory containing complete bundle variants with price-derived universe fie… | NO | 정리 필요 | .github/workflows/web-state-presentation.yml:29-46 |
| `Investment System · Architecture v1.0.md` | 3,321 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment System · Latest Integration Record v1.2 PROVISIONAL.md` | 5,166 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment System · Project Index.md` | 8,097 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment-System1 · Artifact Evidence Register 2026-09-23.md` | 20,536 | text, price_keyword_context, numeric_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 정리 필요 | L129,145,147,162,171,178 cite actual historical cutoff market caps and price-derived issuer ranks. \| Pinned tracked tree 387… |
| `Investment-System1 · Artifact Inventory 2026-09-22.md` | 3,094 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment-System1 · CURRENT_HANDOFF.md` | 4,526 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment-System1 · Contract Conflict Register 2026-09-22.md` | 7,360 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment-System1 · Contract Conflict Register 2026-09-23.md` | 46,078 | text, price_keyword_context, numeric_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 정리 필요 | L439,443 cite actual historical cutoff market caps and issuer ranks. \| Pinned tracked tree 3877f9a1eab3d511a58bcb7c49c1a8339… |
| `Investment-System1 · Experiment & Validation Layer Specification v0.1.md` | 8,178 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment-System1 · Frontend Information Architecture 2026-09-23.md` | 11,843 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment-System1 · Global-Korea Universe and Information Source Contract 2026-09-24.md` | 5,749 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment-System1 · HANDOFF_HISTORY.md` | 142,566 | text, price_keyword_context, numeric_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 정리 필요 | L1294,1328,1347,1387,1409,1414,1434,1444,1480,1491,1513,1604-1628 contain actual cutoff market caps, issuer ranks and recons… |
| `Investment-System1 · Master Status Index 2026-09-22.md` | 19,147 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment-System1 · Missing Artifact Register 2026-09-22.md` | 3,196 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment-System1 · Module Progress Ledger 2026-09-23.md` | 6,077 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment-System1 · Multi-AI Relay Protocol v1.0.md` | 2,636 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment-System1 · PERSONAL_INVESTMENT_LAYER_V1_HANDOFF.md` | 22,805 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment-System1 · RIG News Architecture v0.1.md` | 26,875 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment-System1 · TRACK_A_REAL_DATA_STATUS.md` | 3,576 | text, price_keyword_context, numeric_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 정리 필요 | Actual per-date cutoff market caps in historical real-data status; source line anchors obtained from direct text inspection.… |
| `Investment-System1 · TRACK_E_PROMPT_LIBRARY_V1_STATUS.md` | 9,584 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Investment-System1_Frontend_IA_2026-09-23.docx` | 38,727 | docx, price_keyword_context, numeric_keyword_context | Frontend IA contract document | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | All DOCX ZIP XML parts decoded and inspected; frontend screen/PriceChart height-percentage requirements and IA labels only, … |
| `Investment-System1_Multi-AI_Relay_Protocol.md` | 6,627 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Macro System · Latest Consolidated Record v0.1.4 Candidate.md` | 15,181 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `QGV Leaderboard · Specification v1.0.md` | 8,594 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `QGV Portfolio · Specification v1.1.md` | 9,158 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `QGV Simulation · Specification v1.0.md` | 6,751 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `QGV System v1.7 · Core Implementation Plan v1.0.md` | 5,240 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `QGV System · Common Schema & API Contract v1.0.md` | 7,745 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `QGV System · Module Map v1.7.md` | 2,404 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `QGV Track Record · Specification v1.0.md` | 6,619 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Technical Analysis System · Consolidated Record v0.1.md` | 7,717 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Technical Analysis System · Latest Status Update 2026-09-22.md` | 3,170 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `Technical Analysis · Decision History v0.1.md` | 3,907 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `docs/superpowers/plans/2026-10-09-device-local-actual.md` | 3,012 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `docs/superpowers/plans/2026-10-09-google-sheet-quotes.md` | 5,994 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `docs/superpowers/plans/2026-10-09-manual-device-quotes.md` | 6,124 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `docs/superpowers/plans/2026-10-09-pages-cockpit.md` | 2,365 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `docs/superpowers/plans/2026-10-09-pr70-approved-notice-and-append-guard.md` | 3,855 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `docs/superpowers/specs/2026-10-09-device-local-actual-design.md` | 3,130 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/CHANGELOG.md` | 42,420 | text, price_keyword_context, numeric_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 정리 필요 | L583,590,598,607,624 repeat actual historical cutoff market caps. \| Pinned tracked tree 3877f9a1eab3d511a58bcb7c49c1a8339657… |
| `implementation/PRODUCT_ARCHITECTURE.md` | 2,009 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/ROADMAP_2026Q4.md` | 54,186 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/app_nav_ia_v1_owner/VERIFICATION.md` | 3,648 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/app_nav_ia_v1_owner/evidence/ia-qgv-en-US-1280.png` | 81,358 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/app_nav_ia_v1_owner/evidence/ia-qgv-en-US-390.png` | 47,560 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/app_nav_ia_v1_owner/evidence/ia-qgv-ko-KR-1280.png` | 67,625 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/app_nav_ia_v1_owner/evidence/ia-qgv-ko-KR-390.png` | 41,761 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/app_nav_ia_v1_owner/evidence/verification.json` | 682 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/daily_data_pipeline/DART_CONNECTION_READINESS.md` | 27,831 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/daily_data_pipeline/M1_SEC_INPUTS.md` | 5,759 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/daily_data_pipeline/M1_SEC_INPUTS_PLAN.md` | 4,084 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/daily_data_pipeline/PIPELINE_DESIGN.md` | 32,560 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/daily_data_pipeline/PRICE_RIGHTS_OPTIONS.md` | 18,872 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/daily_data_pipeline/PRIVATE_FREE_PRICE_PATH_RESEARCH.md` | 38,239 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/daily_data_pipeline/TIINGO_DEVICE_DIRECT_RESEARCH.md` | 5,034 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/device_actual_owner/README.md` | 3,796 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/frontend_ia_v1/COCKPIT_IA_v1.md` | 38,611 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/frontend_ia_v1/DESIGN_SOURCE.md` | 5,630 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/frontend_ia_v1/DOCS_SCOPE_RECEIPT.md` | 8,864 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/fundamentals_sources/KR_JP_FILINGS_RESEARCH.md` | 28,272 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/global_language_search/CONTRACT.md` | 7,642 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/global_language_search/STATUS.md` | 5,939 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/integration_candidate_v1_1_20261008/CANDIDATE_MANIFEST.json` | 1,822 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/integration_candidate_v1_1_20261008/CI_COMPATIBILITY_REPAIR.md` | 2,277 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/integration_candidate_v1_1_20261008/evidence/ARTIFACT_MANIFEST.json` | 1,881 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/integration_candidate_v1_1_20261008/evidence/chart-browser-initial.log` | 672 | text, price_keyword_context, numeric_keyword_context | 실행/검증 기록 또는 1차 자료의 발췌 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/docs/integration_candidate_v1_1_20261008/evidence/chart-node-initial.log` | 7,034 | text, price_keyword_context, numeric_keyword_context | 실행/검증 기록 또는 1차 자료의 발췌 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/docs/integration_candidate_v1_1_20261008/evidence/integration-initial.log` | 1,001 | text | 실행/검증 기록 또는 1차 자료의 발췌 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/docs/integration_candidate_v1_1_20261008/evidence/qgv-audit-initial.json` | 813 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/integration_candidate_v1_1_20261008/evidence/web-search-browser.log` | 1,171 | text | 실행/검증 기록 또는 1차 자료의 발췌 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/docs/integration_candidate_v1_1_20261008/evidence/web-search-node.log` | 955 | text | 실행/검증 기록 또는 1차 자료의 발췌 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/docs/manual_quotes_owner/DIRECT_API_RESEARCH_VERIFICATION_26E.json` | 519 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/manual_quotes_owner/DIRECT_API_SERVICE_OPTIONS_26E.md` | 26,981 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/manual_quotes_owner/DIRECT_API_SOURCES_26E.json` | 130,933 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/manual_quotes_owner/FSC_DIRECT_API_RESEARCH_26E.md` | 9,471 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/manual_quotes_owner/FSC_DIRECT_API_SOURCES_26E.json` | 21,502 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/manual_quotes_owner/KIS_DIRECT_API_RESEARCH_26E.md` | 11,823 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/manual_quotes_owner/KIS_DIRECT_API_SOURCES_26E.json` | 58,857 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/manual_quotes_owner/README.md` | 6,200 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/manual_quotes_owner/evidence/manual/manual-empty-1280-en-US.png` | 91,172 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/manual_quotes_owner/evidence/manual/manual-empty-1280-ko-KR.png` | 87,216 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/manual_quotes_owner/evidence/manual/manual-empty-390-en-US.png` | 73,639 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/manual_quotes_owner/evidence/manual/manual-empty-390-ko-KR.png` | 69,414 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/manual_quotes_owner/evidence/manual/manual-quotes-browser.json` | 10,002 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/manual_quotes_owner/evidence/public/PUBLIC_DEPLOYMENT_VERIFICATION.json` | 3,051 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/manual_quotes_owner/evidence/public/actual-1280-browser.json` | 3,128 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/manual_quotes_owner/evidence/public/actual-390-browser.json` | 3,127 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/manual_quotes_owner/evidence/public/actual-empty-1280-en-US.png` | 83,022 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/manual_quotes_owner/evidence/public/actual-empty-1280-ko-KR.png` | 73,829 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/manual_quotes_owner/evidence/public/actual-empty-390-en-US.png` | 65,834 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/manual_quotes_owner/evidence/public/actual-empty-390-ko-KR.png` | 58,043 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/manual_quotes_owner/evidence/public/pages-browser.json` | 1,053 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/pages_cockpit_owner/DEPLOYMENT_DECISION_26E.md` | 2,497 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/pages_cockpit_owner/FX_RESEARCH_26E.md` | 6,920 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md` | 25,518 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_PUBLIC_CHECK_20261009.md` | 6,174 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_SETUP.md` | 10,149 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_VERIFICATION.md` | 2,353 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/pages_cockpit_owner/QUOTES_FX_OPTIONS_26E.md` | 16,379 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/pages_cockpit_owner/README.md` | 4,419 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/pages_cockpit_owner/evidence/DEVICE_FLOW_LOCAL.json` | 3,127 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/pages_cockpit_owner/evidence/QUOTES_SOURCE_FETCH_RECEIPT.json` | 7,204 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/pages_cockpit_owner/evidence/actual-empty-1280-en-US.png` | 83,015 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/pages_cockpit_owner/evidence/actual-empty-1280-ko-KR.png` | 71,943 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/pages_cockpit_owner/evidence/actual-empty-390-en-US.png` | 65,837 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/pages_cockpit_owner/evidence/actual-empty-390-ko-KR.png` | 55,202 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/portfolio_target_owner/OWNER_RECEIPT.json` | 1,012 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/portfolio_target_owner/RETURN.json` | 52,336 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/portfolio_target_owner/TARGET_v0.yaml` | 4,463 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/pr70_approved_owner/ALPHA_VANTAGE_FEASIBILITY_26E.json` | 30,963 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/pr70_approved_owner/ALPHA_VANTAGE_FEASIBILITY_26E.md` | 16,260 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/pr70_approved_owner/README.md` | 3,526 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/pr70_approved_owner/evidence/actual-empty-1280-en-US.png` | 94,410 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/pr70_approved_owner/evidence/actual-empty-1280-ko-KR.png` | 85,848 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/pr70_approved_owner/evidence/actual-empty-390-en-US.png` | 74,804 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/pr70_approved_owner/evidence/actual-empty-390-ko-KR.png` | 72,320 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/pr70_approved_owner/evidence/device-actual-browser.json` | 3,127 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/pr70_approved_owner/evidence/manual-quotes-browser.json` | 10,002 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/producer_infrastructure/CONTRACT.md` | 8,947 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/producer_infrastructure/P01_APPROVAL_2026-10-02.md` | 4,231 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/producer_infrastructure/P03_RAW_STORAGE_COMPARISON.md` | 14,665 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/producer_infrastructure/PROPOSAL_P01_RESEARCH_DATA_STATE.md` | 1,907 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/producer_infrastructure/PROPOSAL_P02_UNIVERSE_INTERIM_POLICY.md` | 1,702 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/producer_infrastructure/RAW_PERSISTENCE_OPTIONS.md` | 4,264 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/producer_infrastructure/STATUS.md` | 5,436 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/producer_infrastructure/evidence/validation.json` | 5,054 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/prompt_field_guide_owner/VARIABLE_MEANINGS.md` | 10,449 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/prompt_field_guide_owner/VERIFICATION.md` | 5,258 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/prompt_field_guide_owner/prompt-guide-empty-en-US-1280.png` | 140,521 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/prompt_field_guide_owner/prompt-guide-empty-en-US-390.png` | 68,323 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/prompt_field_guide_owner/prompt-guide-empty-ko-KR-1280.png` | 134,362 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/prompt_field_guide_owner/prompt-guide-empty-ko-KR-390.png` | 76,823 | image, ocr_checked_ui_evidence | empty-state UI evidence screenshot | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | OCR read of complete screenshot; empty/NOT_AVAILABLE UI and source evidence naming/verification. No actual quote table, plot… |
| `implementation/docs/prompt_field_guide_owner/verification-summary.json` | 2,352 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/AUDIT.md` | 19,788 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/COMPATIBILITY.md` | 6,187 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/CONTRACT.md` | 13,425 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/STATUS.md` | 6,191 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/CURRENT_HANDOFF.md` | 69,793 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/INACTIVE_CONTROL_CONTRACT.md` | 4,473 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/V_DESCRIPTOR_MANIFEST.json` | 30,386 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/V_DESCRIPTOR_VERIFICATION.json` | 421 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/WORK_EXECUTION_POLICY.json` | 3,068 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/automation_readback.json` | 6,072 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/fresh_intake.json` | 2,967 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/g_profile_checks.json` | 6,080 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/g_profile_probe.py` | 8,613 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/g_profile_review.md` | 19,079 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/integration_source_comparison.json` | 8,243 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/CONTROL.json` | 28,316 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer/CONSUMER_SAFETY_DELTA.md` | 8,546 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer/QGV_CONSISTENCY_MATRIX.md` | 7,878 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer/V_INDEPENDENT_REVIEW.md` | 10,525 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer/V_INDEPENDENT_REVIEW_EVIDENCE.json` | 3,656 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer/consumer_lineage_probe.py` | 8,320 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer/lineage_probe_results.json` | 4,389 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 명시적 synthetic fixture/characterization | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | consumer_lineage_probe.py L47-77 constructs golden/SYNTHETIC fixtures; output of manufactured fixture lineage \| Pinned track… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer/source_evidence.json` | 18,536 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer_principles/APPROVED_CONTRACT.md` | 3,018 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer_principles/AUTHORITY_ACCEPTANCE_RESULTS.json` | 5,686 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer_principles/COMPLETION_RECEIPT.json` | 1,264 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer_principles/DECISION_REGISTER.md` | 2,842 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer_principles/EVIDENCE_REUSE.json` | 21,004 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer_principles/FRESH_INTAKE.json` | 1,533 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer_principles/INDEPENDENT_REVIEW.json` | 3,249 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer_principles/MAIN_RETURN.json` | 4,764 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer_principles/OBLIGATION_MAP.json` | 5,132 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer_principles/OUTPUT_MANIFEST.json` | 2,260 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer_principles/PRIOR_SCOPE_RETURN_CONSUMPTION.json` | 716 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer_principles/STATE_RECONCILIATION_BEFORE_REPAIR.json` | 1,143 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer_principles/TASK_BOARD.json` | 3,533 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer_principles/approval.json` | 5,247 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/consumer_principles/authority_acceptance.py` | 9,024 | text | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/AUTOMATION_READBACK.json` | 1,042 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/DECISION_RECEIPT.json` | 4,560 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/DECISION_REGISTER.md` | 2,488 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/EVIDENCE_REUSE.json` | 5,365 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/FAILURE_HISTORY.json` | 1,598 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/FRESH_INTAKE.json` | 3,249 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/INDEPENDENT_REVIEW.json` | 3,259 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/MAIN_RETURN.json` | 1,666 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/OUTPUT_MANIFEST.json` | 5,417 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/PENDING_RECLASSIFICATION.json` | 14,889 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/POLICY.json` | 6,660 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/POLICY.md` | 3,958 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/TASK_BOARD.json` | 5,117 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/VERIFICATION_RESULTS.json` | 3,209 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/returns/CLOSURE_VERIFICATION.json` | 853 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/returns/COMPLETION_RECEIPT.json` | 868 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/returns/MAIN_RECEIPT.input.json` | 5,645 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/returns/OUTPUT_MANIFEST.json` | 2,659 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/returns/PRINCIPLE_MAIN_CONSUMPTION.json` | 2,050 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/delegated_approval/returns/TASK_BOARD.json` | 5,976 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/ARCHIVED_SOURCE_RECOVERY.json` | 1,660 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/AUTOMATION_READBACK.json` | 1,244 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/COMPLETION_RECEIPT.json` | 2,215 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/FRESH_INTAKE.json` | 6,140 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/MAIN_RETURN.json` | 3,648 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/OUTPUT_MANIFEST.json` | 4,874 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/POLICY.json` | 4,704 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/POLICY.md` | 3,181 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/POLICY_VERIFICATION.json` | 509 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/RESUME_INTAKE.json` | 41,626 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/RESUME_VERIFICATION.json` | 1,937 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/ROOT_VERIFICATION.json` | 1,003 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/TASK_BOARD.json` | 6,917 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/scope/ATTEMPT_01_RESULTS.json` | 12,007 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/scope/ATTEMPT_02_RESULTS.json` | 13,303 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/scope/FROZEN_INPUT_PINS.json` | 11,768 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/scope/HANDOFF.md` | 5,162 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/scope/INPUT_PINS.json` | 12,071 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/scope/SCOPE_FIXTURE_DIGESTS.json` | 931 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/scope/SCOPE_FIXTURE_SPEC.json` | 31,814 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/scope/SCOPE_VERIFICATION.json` | 13,303 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/execution_loop/scope/dependency_scope_probe.py` | 43,356 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/g/G_LINEAGE_AUDIT.md` | 18,615 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/g/G_LINEAGE_REPLAY.json` | 99,903 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/g/G_LINEAGE_VERIFICATION.json` | 8,279 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/g/G_METHOD_REPLAY_MANIFEST.json` | 29,948 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/g/G_SOURCE_READINESS.md` | 3,204 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/g/G_SOURCE_READINESS_MATRIX.json` | 33,727 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/g/G_SYNTHETIC_RAW_FIXTURES.json` | 11,146 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/g/build_g_readiness.py` | 17,512 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/g/g_lineage_replay.py` | 24,462 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/resume_v11/AUTHORITY_RECEIPT.json` | 3,598 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/resume_v11/COMPLETION_RECEIPT.json` | 1,215 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/resume_v11/DECISION_REGISTER.md` | 1,825 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/resume_v11/EVIDENCE_REUSE.json` | 25,823 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/resume_v11/FRESH_INTAKE.json` | 5,530 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/resume_v11/INDEPENDENT_REVIEW.json` | 12,400 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/resume_v11/OUTPUT_MANIFEST.json` | 4,473 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/resume_v11/PUBLICATION_HISTORY.json` | 2,280 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/resume_v11/STATE_RECONCILIATION.json` | 3,160 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/resume_v11/TASK_BOARD.json` | 8,025 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/resume_v11/VERIFICATION.json` | 1,724 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/root/B1_EVIDENCE_DELTA.json` | 1,307 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/root/DECISION_PACKAGE.md` | 6,628 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/root/fresh_intake.json` | 3,347 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/root/verification.json` | 1,829 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/consumer/CONTRACT.md` | 13,874 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/consumer/CONTRACT_ACCEPTANCE_RESULTS.json` | 9,539 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/consumer/CONTRACT_EVIDENCE.json` | 3,141 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/consumer/SOURCE_AUTHORITY_MATRIX.json` | 16,340 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/consumer/assessment_ref_carrier.schema.json` | 12,376 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/consumer/contract_acceptance_probe.py` | 26,727 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/consumer/synthetic_carrier.json` | 10,372 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/consumer/synthetic_reference_contents.json` | 26,687 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/g/G2_INDEPENDENT_FAMILY_REVIEW.md` | 2,003 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/g/G_CANDIDATE_DIAGNOSTICS.json` | 29,182 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/g/G_CANDIDATE_MATRIX.json` | 34,372 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/g/G_CANDIDATE_SOURCE_REQUESTS.json` | 5,904 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/g/G_CANDIDATE_VERIFICATION.json` | 4,960 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/g/G_METHOD_CANDIDATE_COMPARISON.md` | 12,810 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/g/G_PRIMARY_SOURCE_NOTES.json` | 2,015 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/g/g_candidate_comparison.py` | 29,680 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/review/independent_review.json` | 19,691 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/review/independent_review.md` | 6,171 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/root/B1_EVIDENCE_DELTA.json` | 1,321 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/root/COMPLETION_RECEIPT.json` | 10,386 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/root/CONTROL_CLAIM.json` | 3,096 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/root/DECISION_PACKAGE.md` | 6,571 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/root/OUTPUT_MANIFEST.json` | 13,297 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/root/SEMANTIC_CONTRACT.md` | 2,826 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/root/WORK_PLAN.md` | 1,699 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/root/acceptance_validator.py` | 4,521 | text | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/root/approval.json` | 3,596 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/root/fresh_intake.json` | 14,716 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/semantic/root/verification.json` | 543 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/v/V_ALTERNATIVE_RESULTS.json` | 72,227 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 명시적 synthetic fixture/characterization | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | SYNTHETIC provenance markers L93-97; v_verify.py L62-63 constructs synthetic RawFundamentals; inactive alternative character… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/v/V_ALTERNATIVE_REVIEW.md` | 14,683 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/v/V_IMPACT_MATRIX.json` | 25,753 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/v/build_impact_matrix.py` | 19,532 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/v/v_alternative_probe.py` | 20,130 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/verification_policy/COMPLETION_RECEIPT.json` | 5,541 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/verification_policy/POLICY.json` | 4,285 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/lanes/verification_policy/POLICY.md` | 3,307 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/root_v_replay.json` | 4,563 | text, price_keyword_context, numeric_keyword_context | 명시적 synthetic fixture/characterization | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | v_verify.py L62-63 constructs DataStamp synthetic=True and literal RawFundamentals; replay characterization output \| Pinned … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/v_evidence.json` | 9,846 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 명시적 synthetic fixture/characterization | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | provenance=SYNTHETIC L96; shared_stamp v-review-synthetic L206; v_verify.py L62-63 synthetic constructors \| Pinned tracked t… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/v_replay.json` | 4,563 | text, price_keyword_context, numeric_keyword_context | 명시적 synthetic fixture/characterization | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | v_verify.py L62-63 constructs DataStamp synthetic=True and literal RawFundamentals; replay characterization output \| Pinned … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/v_review.md` | 15,761 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/v_verify.py` | 7,042 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/verification.json` | 2,815 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/contract_record.example.json` | 2,777 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/contract_record.schema.json` | 11,074 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/current_factor_map.json` | 13,880 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Normative factor weights/definitions and schema coefficients; not an actual observation of V or market price. \| Pinned track… |
| `implementation/docs/qgv_common_contract_vnext/evidence/baseline.json` | 5,954 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/evidence/baseline_full.txt` | 511 | text | 실행/검증 기록 또는 1차 자료의 발췌 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/docs/qgv_common_contract_vnext/evidence/contract_targeted.txt` | 179 | text | 실행/검증 기록 또는 1차 자료의 발췌 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/docs/qgv_common_contract_vnext/evidence/contract_targeted_first_attempt.txt` | 1,475 | text | 실행/검증 기록 또는 1차 자료의 발췌 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/docs/qgv_common_contract_vnext/evidence/existing_targeted.txt` | 99 | text | 실행/검증 기록 또는 1차 자료의 발췌 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/docs/qgv_common_contract_vnext/evidence/existing_targeted_final.txt` | 99 | text | 실행/검증 기록 또는 1차 자료의 발췌 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/docs/qgv_common_contract_vnext/evidence/final_full.txt` | 591 | text | 실행/검증 기록 또는 1차 자료의 발췌 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/docs/qgv_common_contract_vnext/evidence/golden_verification.json` | 262 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/evidence/integration_neutral_overlay.txt` | 179 | text | 실행/검증 기록 또는 1차 자료의 발췌 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/docs/qgv_common_contract_vnext/golden_cases.json` | 741,804 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 명시적 synthetic fixture/characterization | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | status=HISTORICAL_CHARACTERIZATION; expected.synthetic=true; SYNTHETIC golden input/output characterization \| Pinned tracked… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/CURRENT_BEHAVIOR.md` | 20,424 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/CURRENT_HANDOFF.md` | 18,260 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/DECISION_PACKAGE.md` | 21,429 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/DECISION_REGISTER.md` | 6,478 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/POLICY_COMPARISON.md` | 27,882 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/README.md` | 2,567 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/SIMULATION.md` | 16,479 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/CANARY_ACCEPTANCE.md` | 4,471 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/CONTINUATION_AUDIT.md` | 6,631 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/CONTINUATION_PROTOCOL.md` | 9,458 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/CONTROL.md` | 6,004 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/STATE.json` | 27,907 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/continuation_probe.py` | 14,660 | text | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/receipts/2026-10-05_binding_intake_checkpoint.json` | 824 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/receipts/2026-10-05_binding_package_manual_completion.json` | 1,214 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/receipts/2026-10-05_continuation_patch_readback.json` | 13,131 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/receipts/2026-10-05_final_v2_configuration_readback.json` | 12,555 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/receipts/2026-10-05_policy_principles_approved.json` | 1,222 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/receipts/2026-10-05_pre_patch_configuration.json` | 14,325 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/receipts/2026-10-05_setup.json` | 996 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/test_continuation_probe.py` | 14,539 | text | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/APPLICABILITY_AUDIT.md` | 10,715 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/B4_REVIEW.md` | 21,509 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/CONSUMER_PROFILE_REVIEW.md` | 19,079 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/DECISION_PACKAGE.md` | 17,861 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/FACTOR_ROLE_AUDIT.md` | 13,976 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/IMPACT_ANALYSIS.md` | 5,578 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/INDEPENDENT_REVIEW.md` | 14,653 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/authority_drift.json` | 1,047 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/b4_cases.json` | 10,058 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/b4_verify.py` | 8,723 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/consumer_profile_probe.py` | 11,818 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/consumer_profiles.json` | 20,482 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 명시적 synthetic fixture/characterization | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | synthetic_counterexamples[] fixture-generated V/rank; counterexample profile definitions \| Pinned tracked tree 3877f9a1eab3d… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/factor_roles.json` | 84,638 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/fresh_intake.json` | 1,561 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/verification.json` | 9,113 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/work_authority.json` | 1,392 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/current_behavior_probe.py` | 11,581 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/evidence/current_behavior_probes.json` | 219,198 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 명시적 synthetic fixture/characterization | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | generated missing-data golden-fixture probes; SYNTHETIC provenance; contract characterization \| Pinned tracked tree 3877f9a1… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/evidence/fresh_baseline.json` | 1,842 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/evidence/verification.json` | 1,631 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/implementation_contract/CONTRACT.md` | 18,933 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/implementation_contract/MIGRATION_BOUNDARY.md` | 17,491 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/implementation_contract/README.md` | 1,753 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/implementation_contract/REGRESSION_PLAN.md` | 27,157 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/implementation_contract/REUSE_MAP.md` | 19,868 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/implementation_contract/approval.json` | 4,415 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/implementation_contract/automation_verification.json` | 1,298 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/implementation_contract/evidence.json` | 4,966 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/simulate_policies.py` | 24,775 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/qgv_common_contract_vnext/missing_data_gate/simulation_results.json` | 942,108 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_common_contract_vnext/publication/TRANSPORT_REPUBLICATION_VERIFICATION_2026-10-04.json` | 55,174 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/qgv_scoring_standard/QGV_SCORING_STANDARD_v1.md` | 9,385 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/security_map19_owner/OWNER_RECEIPT.json` | 1,009 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/security_map19_owner/RETURN.json` | 56,550 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/security_map19_owner/TARGET_v0_SECURITY_MAP.json` | 172,928 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/security_map19_owner/v1_1_cycle_20261008/CURRENT_TARGET_IDENTITY_MAP.json` | 86,939 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/security_map19_owner/v1_1_cycle_20261008/LOCAL_VERIFICATION.json` | 3,676 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/security_map19_owner/v1_1_cycle_20261008/README.md` | 4,608 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/security_map19_owner/v1_1_cycle_20261008/SIX_GATE_REJUDGMENT.json` | 3,967 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/security_map19_owner/v1_1_cycle_20261008/sources/asml_share_form_extracted.txt` | 8,674 | text, price_keyword_context, numeric_keyword_context | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 보안맵/식별 검증에 보존된 1차 공개 자료 또는 source receipt | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/docs/security_map19_owner/v1_1_cycle_20261008/sources/asml_share_form_original.html.gz` | 13,615 | gzip, price_keyword_context, numeric_keyword_context | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 보안맵/식별 검증에 보존된 1차 공개 자료 또는 source receipt | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/docs/security_map19_owner/v1_1_cycle_20261008/sources/hanmi_dart_identity_extracted.txt` | 516 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 보안맵/식별 검증에 보존된 1차 공개 자료 또는 source receipt | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/docs/security_map19_owner/v1_1_cycle_20261008/sources/hanmi_dart_identity_original.html.gz` | 785 | gzip | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 보안맵/식별 검증에 보존된 1차 공개 자료 또는 source receipt | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/docs/security_map19_owner/v1_1_cycle_20261008/sources/nport_0001752724-25-034052_original.xml.gz` | 81,465 | gzip, price_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 보안맵/식별 검증에 보존된 1차 공개 자료 또는 source receipt | UNKNOWN | 정리 필요 | Decoded NPORT holdings contain valUSD and balance numeric amounts, exposing actual market values and implied per-share price… |
| `implementation/docs/security_map19_owner/v1_1_cycle_20261008/sources/official_source_capture_receipt.json` | 7,301 | text, price_keyword_context, numeric_keyword_context | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 보안맵/식별 검증에 보존된 1차 공개 자료 또는 source receipt | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/docs/security_map19_owner/v1_1_cycle_20261008/sources/sec_tickers_exchange_original.json.gz` | 179,396 | gzip, price_keyword_context, numeric_keyword_context | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 보안맵/식별 검증에 보존된 1차 공개 자료 또는 source receipt | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/docs/security_map19_owner/v1_1_cycle_20261008/sources/tel_stock_info_original.html.gz` | 9,554 | gzip | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 보안맵/식별 검증에 보존된 1차 공개 자료 또는 source receipt | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/docs/security_map19_owner/v1_1_cycle_20261008/test_evidence_rejections.py` | 3,054 | text | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/security_map19_owner/v1_1_cycle_20261008/verify_mapping.py` | 10,178 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/docs/strategy_theme_owner/OWNER_RECEIPT.json` | 1,013 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/strategy_theme_owner/RETURN.json` | 30,677 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/strategy_theme_owner/v1_1_cycle_20261008/CURRENT_TARGET_THEME_ASSIGNMENTS.json` | 11,116 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/docs/technical_live_data/DESIGN.md` | 44,334 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/web_mvp/CONTRACT.md` | 5,905 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/web_mvp/README.md` | 5,117 | text, price_keyword_context | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/web_mvp/STATUS.md` | 5,549 | text | 계약/정책/설계/업무 기록 | 문서·설계·계약·조정 기록; 구현/운영 승인 또는 실시간 데이터 존재의 증거로 승격하지 않음 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/docs/web_mvp/evidence/browser.json` | 509 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | UI/승인/검증의 과거 증빙; screenshot 또는 receipt | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/experiments/chart-contract-v0.1/ACCEPTANCE.json` | 6,548 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/CHART_INVENTORY.md` | 33,323 | md | Repository-owned requirement, governance or validation metadata | Requirements and archived readiness inventory | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/HANDOFF.md` | 17,320 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/README.md` | 14,886 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/app.js` | 4,290 | js | Repository-owned code/test/rendering template | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/automation/RUNBOOK.md` | 14,950 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/automation/STATE.json` | 153,049 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/browser_test.cjs` | 4,382 | cjs | Repository-owned code/test/rendering template | Offline validation/test harness (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/chart_inventory.json` | 181,787 | json | Repository-owned requirement, governance or validation metadata | Requirements and archived readiness inventory | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/contract.mjs` | 10,029 | mjs | Repository-owned code/test/rendering template | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/contract.test.mjs` | 8,310 | mjs | Yahoo Finance chart response capture | Offline validation/test harness (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/evidence/2026-10-04-source/canonical-store-summary.json` | 1,536 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/evidence/2026-10-04-source/events-fetch-evidence.json` | 533 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/evidence/2026-10-04-source/fetch-evidence.json` | 467 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/evidence/2026-10-04-source/nvda_events_5y_original.json` | 8,183 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/evidence/2026-10-04-source/raw-store/blobs/yahoo_chart__NVDA__5d` | 1,758 | extensionless, 원시/조정 가격 | Original Yahoo chart raw bytes captured offline | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/evidence/2026-10-04-source/raw-store/manifests/yahoo_chart__NVDA__5d.json` | 628 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/evidence/2026-10-04-source/real-source-preflight.json` | 2,395 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/evidence/acceptance-demo-v1.json` | 1,928 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/evidence/acceptance-source-v02.json` | 3,820 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/evidence/portfolio-reference-source.json` | 983 | json | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/export_demo.mjs` | 3,739 | mjs | Repository-owned code/test/rendering template | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/fixture.mjs` | 1,528 | mjs | Repository-owned code/test/rendering template | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/inventory_app.js` | 2,642 | js | Repository-owned code/test/rendering template | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-ci-followup-v0.11/PR46_FPIA_TERMINAL_FAILURE_RECEIPT.json` | 4,003 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/CHARTDOCUMENT_v0.2_PROPOSAL.md` | 8,032 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/CHECKPOINT_VERIFICATION.json` | 30,504 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/GITHUB_FRESH_READ_CHECKPOINT.json` | 3,492 | json | Yahoo Finance chart response capture | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/P0_MARKET_AND_PORTFOLIO_CLASSIFICATION_REVIEW_v0.3.md` | 29,809 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/contract-integration/CHARTDOCUMENT_V02_CANDIDATE_AND_FPIA_REVIEW_v0.3.md` | 20,339 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/contract-integration/PROTECTED_IMPACT_READONLY_PROOF.json` | 842 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/gics/BOUNDED_EXCERPTS.json` | 1,210 | json | Classification reference source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/gics/GICS_FEASIBILITY_AUDIT_v0.3.md` | 10,575 | md | Classification reference source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/gics/SOURCE_REGISTER.json` | 9,360 | json | Classification reference source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/ACTION_ACQUISITION_PROBES_v0.3.json` | 52,439 | json | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/BASIS_ACTION_PRIMARY_SOURCE_REVIEW_v0.3.json` | 5,983 | json | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/IMMUTABLE_RAW_ANOMALIES_v0.3.json` | 14,791 | json, 원시/조정 가격 | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 정리 필요 | 키: rows.[].latest_comparison_values.close, rows.[].latest_comparison_values.high, rows.[].latest_comparison_values.low 외 5개 키 |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/INDEPENDENT_SCOPED_VERIFICATION_v0.3.json` | 10,210 | json | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/MARKET_BASIS_AND_ANOMALY_AUDIT_v0.3.md` | 15,025 | md | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/MARKET_BASIS_READINESS_19_v0.3.json` | 33,348 | json | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/PRIMARY_SOURCE_CAPTURES_v0.3.json` | 3,494 | json | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/SOURCE_FIELD_COMPLETENESS_AND_DIFFERENCE_AMPLITUDE_v0.3.json` | 39,656 | json | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 정리 필요 | 키: rows.[].max_abs_source_value_difference |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/TWO_OBSERVATIONS_COMPARISON_v0.3.json` | 182,670 | json | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_042700_KS_5y_daily_original.json` | 81,334 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_8035_T_5y_daily_original.json` | 91,429 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_AMD_5y_daily_original.json` | 136,966 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_AMZN_5y_daily_original.json` | 138,111 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_ASML_5y_daily_original.json` | 131,662 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_AVGO_5y_daily_original.json` | 138,544 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_ETN_5y_daily_original.json` | 136,219 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_GEV_5y_daily_original.json` | 64,900 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_GOOGL_5y_daily_original.json` | 139,164 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_HUBB_5y_daily_original.json` | 135,794 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_INTC_5y_daily_original.json` | 139,055 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_KLAC_5y_daily_original.json` | 138,344 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_LRCX_5y_daily_original.json` | 137,391 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_MSFT_5y_daily_original.json` | 137,156 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_NVDA_5y_daily_original.json` | 142,207 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_QCOM_5y_daily_original.json` | 139,409 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_ROK_5y_daily_original.json` | 134,610 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_RTX_5y_daily_original.json` | 136,064 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/actions_SYK_5y_daily_original.json` | 134,884 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/capture_actions_audit.py` | 2,908 | py | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/capture_primary_basis_audit.py` | 2,168 | py | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/derive_basis_anomaly_audit.py` | 8,980 | py | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/ADDITIONAL_SOURCE_ACQUISITION.json` | 7,509 | json | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/AUDIT_VERIFICATION.json` | 2,913 | json | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/MARKET19_IDENTITY_TIME_READINESS.json` | 352,034 | json | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/MARKET_IDENTITY_TIME_AUDIT_v0.3.md` | 14,875 | md | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/SOURCE_PIN_REPLAY.json` | 3,886 | json | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/asml_share_form_extracted.txt` | 8,674 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/asml_share_form_original.html` | 66,032 | html | Official security-identity/exchange calendar/hours source or audit | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/gev_regular_way_extracted.txt` | 12,472 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/gev_regular_way_original.html` | 94,111 | html | Official security-identity/exchange calendar/hours source or audit | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/gev_when_issued_extracted.txt` | 11,246 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/gev_when_issued_original.html` | 86,142 | html | Official security-identity/exchange calendar/hours source or audit | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/hanmi_dart_identity_extracted.txt` | 516 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/hanmi_dart_identity_original.html` | 2,473 | html | Official security-identity/exchange calendar/hours source or audit | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/jpx_2024_actual_go_live_original.pdf` | 108,637 | PDF, official_exchange_document, non_price_calendar_or_hours | JPX/TSE actual cash-equity system go-live and trading-hours extension notice; jpx_20… | Read-only source evidence for the market identity/time readiness matrix and session-authority … | NO | 유지 가능 | keys: sources[].source_id; sources[].url; sources[].content_type; sources[].path; sources[].sha256; source: Official no… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/jpx_calendar_original.html` | 33,103 | html | Official security-identity/exchange calendar/hours source or audit | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/jpx_hours_extracted.txt` | 2,699 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/jpx_hours_original.html` | 28,916 | html | Official security-identity/exchange calendar/hours source or audit | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/krx_kospi_csat_2025_extracted.txt` | 1,711 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/krx_kospi_csat_2025_original.html` | 9,072 | html | Official security-identity/exchange calendar/hours source or audit | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/krx_stock_hours_extracted.txt` | 2,620 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/krx_stock_hours_original.html` | 4,654 | html | Official security-identity/exchange calendar/hours source or audit | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nasdaq_calendar_2021_extracted.txt` | 4,700 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nasdaq_calendar_2021_original.pdf` | 86,671 | PDF, official_exchange_document, non_price_calendar_or_hours | NasdaqTrader 2021 trading calendar; nasdaq_calendar_2021; https://www.nasdaqtrader.c… | Read-only source evidence for the market identity/time readiness matrix and session-authority … | NO | 유지 가능 | keys: sources[].source_id; sources[].url; sources[].content_type; sources[].path; sources[].sha256; source: Official no… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nasdaq_calendar_2022_extracted.txt` | 4,575 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nasdaq_calendar_2022_original.pdf` | 120,950 | PDF, official_exchange_document, non_price_calendar_or_hours | NasdaqTrader 2022 trading calendar; nasdaq_calendar_2022; https://www.nasdaqtrader.c… | Read-only source evidence for the market identity/time readiness matrix and session-authority … | NO | 유지 가능 | keys: sources[].source_id; sources[].url; sources[].content_type; sources[].path; sources[].sha256; source: Official no… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nasdaq_calendar_2023_extracted.txt` | 4,921 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nasdaq_calendar_2023_original.pdf` | 274,749 | PDF, official_exchange_document, non_price_calendar_or_hours | NasdaqTrader 2023 trading calendar; nasdaq_calendar_2023; https://www.nasdaqtrader.c… | Read-only source evidence for the market identity/time readiness matrix and session-authority … | NO | 유지 가능 | keys: sources[].source_id; sources[].url; sources[].content_type; sources[].path; sources[].sha256; source: Official no… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nasdaq_calendar_2024_extracted.txt` | 4,722 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nasdaq_calendar_2024_original.pdf` | 105,969 | PDF, official_exchange_document, non_price_calendar_or_hours | NasdaqTrader 2024 trading calendar; nasdaq_calendar_2024; https://www.nasdaqtrader.c… | Read-only source evidence for the market identity/time readiness matrix and session-authority … | NO | 유지 가능 | keys: sources[].source_id; sources[].url; sources[].content_type; sources[].path; sources[].sha256; source: Official no… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nasdaq_calendar_2025_extracted.txt` | 4,792 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nasdaq_calendar_2025_original.pdf` | 146,717 | PDF, official_exchange_document, non_price_calendar_or_hours | NasdaqTrader 2025 trading calendar; nasdaq_calendar_2025; https://www.nasdaqtrader.c… | Read-only source evidence for the market identity/time readiness matrix and session-authority … | NO | 유지 가능 | keys: sources[].source_id; sources[].url; sources[].content_type; sources[].path; sources[].sha256; source: Official no… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nasdaq_carter_2025_closure_extracted.txt` | 6,213 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nasdaq_carter_2025_closure_original.html` | 57,795 | html | Official security-identity/exchange calendar/hours source or audit | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nasdaq_system_hours_original.pdf` | 36,023 | PDF, official_exchange_document, non_price_calendar_or_hours | Nasdaq Systems Hours of Operation; nasdaq_system_hours; https://nasdaqtrader.com/con… | Read-only source evidence for the market identity/time readiness matrix and session-authority … | NO | 유지 가능 | keys: sources[].source_id; sources[].url; sources[].content_type; sources[].path; sources[].sha256; source: Official no… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nasdaqtrader_calendar_extracted.txt` | 6,979 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nasdaqtrader_calendar_original.html` | 54,628 | html | Official security-identity/exchange calendar/hours source or audit | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nyse_hours_calendar_extracted.txt` | 6,393 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/nyse_hours_calendar_original.html` | 109,229 | html | Official security-identity/exchange calendar/hours source or audit | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/sec_association_documentation_extracted.txt` | 14,460 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/sec_association_documentation_original.html` | 80,344 | html | Official security-identity/exchange calendar/hours source or audit | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/sec_tickers_exchange_original.json` | 523,512 | json | Official security-identity/exchange calendar/hours source or audit | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/tel_stock_info_original.html` | 37,852 | html | Official security-identity/exchange calendar/hours source or audit | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/yahoo_exchange_delay_extracted.txt` | 13,114 | txt | Official security-identity/exchange calendar/hours source or audit | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/yahoo_exchange_delay_original.html` | 157,780 | html | Official security-identity/exchange calendar/hours source or audit | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/portfolio-architecture/EVIDENCE.json` | 9,258 | json | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/portfolio-architecture/PORTFOLIO_CLASSIFICATION_ARCHITECTURE_v0.3.md` | 20,526 | md | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/verify_checkpoint.py` | 7,268 | py | Repository-owned code/test/rendering template | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-dependency-continuation-v0.7/EXECUTION_POLICY.md` | 7,832 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-dependency-continuation-v0.7/HANDOFF.md` | 7,133 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-dependency-continuation-v0.7/INDEPENDENT_PROBES.json` | 9,547 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-dependency-continuation-v0.7/VERIFY.json` | 16,769 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-dependency-continuation-v0.7/reproduce_nine_preflight_probes.py.txt` | 5,811 | txt | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-design/DESIGN_REVIEW.md` | 4,231 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-design/EVIDENCE.json` | 25,834 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-design/P0_CHART_CONTRACT_AND_WIRING_v0.1.md` | 36,459 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-design/reviews/boundary_source_review.md` | 12,906 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-design/reviews/market_source_review.md` | 13,969 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-design/reviews/portfolio_source_review.md` | 12,968 | md | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/ARCHIVED_RUN_OBSERVATION.json` | 10,729 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/AUTOMATION_RECHECK.json` | 9,241 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/CLI_EXPECTATION_CORRECTION.json` | 1,222 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/CURRENT_INPUT_DIAGNOSTIC.json` | 65,740 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/DECIMAL_REFERENCE_VERIFY.json` | 904 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/FPIA_TERMINAL_RECEIPT.json` | 7,441 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/FRESH_GITHUB_READ.json` | 4,031 | json | Yahoo Finance chart response capture | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/GATES_AND_GAPS.json` | 8,871 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/GOVERNANCE_RECHECK.json` | 50,513 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/HANDOFF.md` | 16,185 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/LATE_OWNER_INTAKE.json` | 2,027 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/MALFORMED_JSON_REPAIR_RECEIPT.json` | 1,476 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/MARKET_RECHECK.json` | 9,128 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/ORIGINAL_MALFORMED_JSON_FAILURE.json` | 4,665 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/PORTABLE_REPLAY_NORMAL.json` | 9,534 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/PORTABLE_REPLAY_OPTIMIZED.json` | 9,534 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/PUBLICATION_RECEIPT.json` | 1,847 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/README.md` | 1,140 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/REFERENCE_REPLAY_REPAIR_RECEIPT.json` | 7,126 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/SOURCE_RECHECK.json` | 7,116 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/WRITE_SET.json` | 32,063 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/replay_preflight_probes.py` | 7,582 | py | Repository-owned code/test/rendering template | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/test_diagnostic_repairs.py` | 2,509 | py | Repository-owned code/test/rendering template | Offline validation/test harness (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/test_reference_replay_status.py` | 4,418 | py | Repository-owned code/test/rendering template | Offline validation/test harness (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-figma-review-v0.12/FIGMA_CALLS.json` | 51,580 | json | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-figma-review-v0.12/FIGMA_RECEIPT.json` | 18,522 | json | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-figma-review-v0.12/GATES_AND_GAPS.json` | 16,977 | json | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-figma-review-v0.12/HANDOFF.md` | 8,436 | md | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-figma-review-v0.12/LATE_GLOBAL_RECEIPT.json` | 3,939 | json | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-figma-review-v0.12/SOURCE_VIEW.json` | 17,793 | json | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Historical review UI state export | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/BROWSER_CANDLES.json` | 1,172 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/CI_FAILURE_CLASSIFICATION.json` | 232,172 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/CI_LATE_STATUS.json` | 2,532 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/DOCS_AND_VERSION_RECEIPT.json` | 1,636 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/FPIA_CURRENT_HEAD_RECEIPT.json` | 13,783 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/FPIA_TERMINAL_RECEIPT.json` | 20,987 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/FRESH_OWNER_INTAKE.json` | 54,120 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/GATES_AND_GAPS.json` | 16,299 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/HANDOFF.md` | 11,522 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/LATE_OWNER_INTAKE.json` | 45,776 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/NODE_75_PASS.log` | 5,809 | log | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/OPTIONAL_OWNER_DELTA.json` | 17,060 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/browser/baseline-1280.png` | 183,071 | PNG, browser_screenshot, non_price_target_reference | Playwright cropped #portfolio screenshot of historical USER_SPEC_REFERENCE/TARGET al… | Immutable browser regression evidence; historical missing-zero failure baseline, also imported… | NO | 유지 가능 | keys: snapshot_id; source; weight_basis; data_kind; portfolio/type availability; source: Non-price user-authored target… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/browser/demo-1280.png` | 260,251 | PNG, browser_screenshot, synthetic_portfolio | Playwright cropped #portfolio screenshot of explicit fictionalPortfolioFixture() DEMO | Immutable browser regression evidence; fictional-overlap demo, also imported into the private … | NO | 유지 가능 | keys: snapshot_id; source; weight_basis; data_kind; portfolio/type availability; source: Synthetic portfolio compositio… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/browser/reference-1280.png` | 242,647 | PNG, browser_screenshot, non_price_target_reference | Playwright cropped #portfolio screenshot of historical USER_SPEC_REFERENCE/TARGET al… | Immutable browser regression evidence; historical reference allocation view, also imported int… | NO | 유지 가능 | keys: snapshot_id; source; weight_basis; data_kind; portfolio/type availability; source: Non-price user-authored target… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/browser/reference-390.png` | 278,133 | PNG, browser_screenshot, non_price_target_reference | Playwright cropped #portfolio screenshot of historical USER_SPEC_REFERENCE/TARGET al… | Immutable browser regression evidence; historical reference allocation view at mobile viewport. | NO | 유지 가능 | keys: snapshot_id; source; weight_basis; data_kind; portfolio/type availability; source: Non-price user-authored target… |
| `implementation/experiments/chart-contract-v0.1/p0-fixture-review-v0.9/fixture_browser_test.cjs` | 8,184 | cjs | Repository-owned code/test/rendering template | Offline validation/test harness (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-magicpath-review-v0.13/BROWSER_CHECK.json` | 1,829 | json | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-magicpath-review-v0.13/BUILD_MANIFEST.json` | 5,723 | json | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-magicpath-review-v0.13/DECISION_RECEIPT.json` | 4,003 | json | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-magicpath-review-v0.13/GATES_AND_GAPS.json` | 17,931 | json | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-magicpath-review-v0.13/HANDOFF.md` | 7,748 | md | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-magicpath-review-v0.13/MAGICPATH_RECEIPT.json` | 2,976 | json | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-magicpath-review-v0.13/OWNER_INTAKE.json` | 3,389 | json | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-magicpath-review-v0.13/browser/actual-390.png` | 104,687 | PNG, browser_screenshot, actual_unavailable | Exact downloaded MagicPath component build, viewed through a local HTTP mirror; nati… | FAST presentation-only mobile browser evidence for native MagicPath SAMPLE component; review c… | NO | 유지 가능 | keys: basis=TARGET\|ACTUAL; chartSampleView.reference; chartSampleView.actual; SAMPLE; ACTUAL NOT_AVAILABLE; source: ACT… |
| `implementation/experiments/chart-contract-v0.1/p0-magicpath-review-v0.13/browser/target-390.png` | 285,072 | PNG, browser_screenshot, non_price_target_reference | Exact downloaded MagicPath component build, viewed through a local HTTP mirror; nati… | FAST presentation-only mobile browser evidence for native MagicPath SAMPLE component; review c… | NO | 유지 가능 | keys: basis=TARGET\|ACTUAL; chartSampleView.reference; chartSampleView.actual; SAMPLE; ACTUAL NOT_AVAILABLE; source: Lit… |
| `implementation/experiments/chart-contract-v0.1/p0-magicpath-review-v0.13/component/src/App.tsx` | 562 | tsx | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-magicpath-review-v0.13/component/src/components/generated/ChartStrategyThemeSAMPLEACTUALUnavailable.tsx` | 3,391 | tsx | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-magicpath-review-v0.13/component/src/components/generated/chartSampleView.ts` | 13,514 | ts | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-magicpath-review-v0.13/component/src/components/generated/noto-fonts-0.css` | 799,274 | css | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Captured official source or chart-lab presentation asset | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-magicpath-review-v0.13/component/src/components/generated/noto-fonts-1.css` | 798,164 | css | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Captured official source or chart-lab presentation asset | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-magicpath-review-v0.13/component/src/components/generated/noto-fonts-2.css` | 799,811 | css | Historical chart/portfolio review; TARGET reference or synthetic demo UI | Captured official source or chart-lab presentation asset | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/P0_IMPLEMENTATION_PREREQUISITES_v0.2.md` | 18,383 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/contract/CHARTDOCUMENT_ADEQUACY_MATRIX.json` | 31,516 | json, 원시/조정 가격, 가격 기반 수익률/비교 | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 정리 필요 | 키: additive_new_evidence_review.failures.[].row.values.close, additive_new_evidence_review.failures.[].row.values.high, addi… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/contract/CHARTDOCUMENT_V01_ADEQUACY_AND_V02_PROPOSAL.md` | 26,896 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 정리 필요 | 키: Observed raw-failure table: close/high/low scalar literals |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/ADDITIONAL_REFERENCE_US_PROBES.json` | 48,406 | json, 원시/조정 가격 | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 정리 필요 | 키: rows.[].meta.chartPreviousClose, rows.[].meta.fulldayPrice, rows.[].meta.regularMarketChangePercent 외 3개 키 |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/MARKET_EVIDENCE.json` | 10,815 | json | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/MARKET_PREREQUISITE_AUDIT.md` | 21,182 | md | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/MARKET_REFERENCE_COVERAGE.json` | 25,013 | json, 원시/조정 가격 | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 정리 필요 | 키: rows.[].ohlc_envelope_violations.[].values.close, rows.[].ohlc_envelope_violations.[].values.high, rows.[].ohlc_envelope_… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/PUBLIC_ACQUISITION_PROBES.json` | 12,459 | json, 원시/조정 가격 | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 정리 필요 | 키: rows.[].meta.chartPreviousClose, rows.[].meta.fulldayPrice, rows.[].meta.regularMarketChangePercent 외 3개 키 |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/SOURCE_COUNTEREXAMPLES.json` | 2,719 | json, 원시/조정 가격 | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 정리 필요 | 키: rows.[].ohlc_envelope_violations_detail.[].close, rows.[].ohlc_envelope_violations_detail.[].high, rows.[].ohlc_envelope_… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_042700_KS_5y_original.json` | 81,041 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_8035_T_5y_original.json` | 90,729 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_AMD_5y_original.json` | 136,966 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_AMZN_5y_original.json` | 138,001 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_ASML_5y_original.json` | 130,725 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_AVGO_5y_original.json` | 137,441 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_ETN_5y_original.json` | 135,258 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_GEV_5y_original.json` | 64,526 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_GOOGL_5y_original.json` | 138,533 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_HUBB_5y_original.json` | 134,857 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_INTC_5y_original.json` | 138,466 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_KLAC_5y_original.json` | 137,285 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_LRCX_5y_original.json` | 136,289 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_MSFT_5y_original.json` | 136,251 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_NVDA_5y_original.json` | 141,128 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_QCOM_5y_original.json` | 138,430 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_ROK_5y_original.json` | 133,627 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_RTX_5y_original.json` | 135,053 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/market/probe_SYK_5y_original.json` | 133,902 | json, 원시/조정 가격 | Yahoo Finance chart response capture | Offline source evidence used by market identity/basis/readiness replay; not a public Pages inp… | NO | 정리 필요 | 키: chart.result.[].indicators.adjclose.[].adjclose.[], chart.result.[].indicators.quote.[].close.[], chart.result.[].indicat… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/portfolio/EVIDENCE.json` | 10,801 | json | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/portfolio/PORTFOLIO_SOURCE_READINESS.md` | 20,401 | md | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/root/source-pin-replay.json` | 16,892 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-prerequisites/root/verification.json` | 22,527 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-receipt-preflight-v0.6/CURRENT_INPUT_DIAGNOSTIC.json` | 65,687 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-receipt-preflight-v0.6/EVENT_STREAMS_OBSERVED.json` | 15,509 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-receipt-preflight-v0.6/FRESH_BASELINE.json` | 8,990 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-receipt-preflight-v0.6/HANDOFF.md` | 7,677 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-receipt-preflight-v0.6/INDEPENDENT_REVIEW.json` | 1,923 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-receipt-preflight-v0.6/INITIAL_INPUT_DIAGNOSTIC.json` | 65,514 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-receipt-preflight-v0.6/README.md` | 2,899 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-receipt-preflight-v0.6/receipt_preflight.py` | 17,800 | py | Repository-owned code/test/rendering template | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-receipt-preflight-v0.6/test_receipt_preflight.py` | 11,877 | py | Repository-owned code/test/rendering template | Offline validation/test harness (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-receipt-preflight-v0.6/test_review_edges.py` | 5,345 | py | Repository-owned code/test/rendering template | Offline validation/test harness (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-risk-policy-v0.10/EXECUTION_POLICY.md` | 4,557 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-risk-policy-v0.10/HANDOFF.md` | 3,561 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/FRESH_BASELINE.json` | 10,367 | json | Yahoo Finance chart response capture | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/HANDOFF.md` | 7,071 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/OWNER_CLOSURE_DELTA_v0.5.md` | 9,421 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/OWNER_HANDOFF_ROUTING.json` | 1,550 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/authority/EXISTING_AUTHORITY_INTERFACE_DIAGNOSTIC_v0.5.json` | 11,127 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/authority/OWNER_INTERFACE_DECISION_INPUT_v0.5.json` | 1,804 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/authority/TARGET_THEME_AUTHORITY_OWNER_PACKET_v0.5.md` | 17,044 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/authority/replay_existing_authority.py` | 9,586 | py | Repository-owned code/test/rendering template | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/lane-a/OWNER_PACKET_CONSISTENCY.json` | 754 | json | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/lane-a/TARGET_OWNER_ADMISSION_REQUEST.json` | 54,070 | json | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/lane-a/TARGET_OWNER_DELTA_EVIDENCE.json` | 15,900 | json | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/lane-a/TARGET_SOURCE_OWNER_CLOSURE_PACKET_v0.5.md` | 10,304 | md | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/lane-b/EXISTING_CAPABILITY_PINS_v0.5.json` | 25,672 | json | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/lane-b/IMMUTABLE_MARKET_ADMISSION_CASES_v0.5.json` | 15,265 | json, 원시/조정 가격 | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 정리 필요 | 키: cases.[].points.[].adjclose_decimal_text, cases.[].points.[].decimal_text.close, cases.[].points.[].decimal_text.high 외 2… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/lane-b/LANE_B_VERIFY_RECEIPT_v0.5.json` | 9,463 | json | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/lane-b/MARKET_OWNER_ACTIONS_v0.5.json` | 23,129 | json | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/lane-b/MARKET_OWNER_REUSE_AND_CLOSURE_v0.5.md` | 14,269 | md | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/lane-b/verify_owner_reuse.py` | 8,748 | py | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-terminal-policy-v0.14/CI_TERMINAL_RECEIPT.json` | 8,547 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-terminal-policy-v0.14/FAILURE_HISTORY.json` | 624 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-terminal-policy-v0.14/GATES_AND_GAPS.json` | 17,476 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-terminal-policy-v0.14/HANDOFF.md` | 7,622 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-terminal-policy-v0.14/OWNER_INTAKE.json` | 6,813 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/ADDITIVE_ARTIFACT_MANIFEST.json` | 14,809 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/MINIMAL_CHARTDOCUMENT_v0.2_TARGET_THEME.md` | 11,150 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/P0_TARGET_THEME_AND_MARKET_IMPLEMENTATION_READINESS_v0.4.md` | 24,295 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/TARGET_THEME_VALIDATION_PLAN.md` | 4,225 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/baseline/PR41_fresh.json` | 30,862 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/baseline/PR42_fresh.json` | 54,657 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/FPIA_AND_OWNER_PATH_READINESS_v0.4.md` | 14,953 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/FPIA_CURRENT_STATUS.json` | 4,030 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/GOVERNANCE_ARTIFACT_MANIFEST.json` | 12,529 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/P01_DIGEST_FRESH_READ_PROOF.json` | 2,319 | json | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/app_js.json` | 81,177 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/assembler.json` | 11,763 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/code_hash.json` | 32,353 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/coordination_decision_register.json` | 71,789 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/existing_browser_harness.json` | 64,502 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/global_current_handoff.json` | 27,764 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/global_handoff_history.json` | 42,410 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/global_status_index.json` | 53,297 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/handoff_tree.json.gz` | 556,923 | GZIP, GitHub_recursive_tree_response, non_price_repository_metadata | https://api.github.com/repos/kco994553-star/Investment-System1/git/trees/9d9b2b2b942… | Read-only governance/owner/runtime path discovery and immutable historical source-tree evidenc… | NO | 유지 가능 | keys: key; url; response.structuredContent.content.sha; response.structuredContent.content.tree[].path; tree[].mode; tr… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/macro_engine.json` | 5,796 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/p01_guard.json` | 43,997 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/pr21_metadata.json` | 43,553 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/pr42_fpia_job_logs.json` | 33,606 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/pr42_metadata.json` | 107,509 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/pr42_tree.json.gz` | 615,217 | GZIP, GitHub_recursive_tree_response, non_price_repository_metadata | https://api.github.com/repos/kco994553-star/Investment-System1/git/trees/523e702a806… | Read-only governance/owner/runtime path discovery and immutable historical source-tree evidenc… | NO | 유지 가능 | keys: key; url; response.structuredContent.content.sha; response.structuredContent.content.tree[].path; tree[].mode; tr… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/pr42_workflow_runs.json` | 231,920 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/producer_serialization.json` | 5,464 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/publication_authorization.json` | 8,947 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/publication_contract.json` | 9,288 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/publication_envelope.json` | 6,202 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/publication_extractors.json` | 17,974 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/publication_predicate.json` | 11,375 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/publication_status.json` | 12,432 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/qgv_book.json` | 7,236 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/qgv_leaderboard.json` | 5,971 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/qgv_pipeline.json` | 6,018 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/technical_engine.json` | 8,096 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/web_mvp.json` | 16,605 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/web_state_tests.json` | 36,367 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/raw/worker_contract.json` | 34,639 | json | Historical GitHub REST file/PR/workflow evidence (source code or metadata envelope) | Historical governance/source pin review and replay | NO | 유지 가능 | Historical GitHub source/metadata envelope. Source contents are code/documentation or hash/status/tree metadata, not a provi… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/app_js.txt` | 38,099 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/assembler.txt` | 5,111 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/code_hash.txt` | 14,548 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/coordination_decision_register.txt` | 34,567 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/existing_browser_harness.txt` | 30,448 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/global_current_handoff.txt` | 13,116 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/global_handoff_history.txt` | 20,357 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/global_status_index.txt` | 25,815 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/macro_engine.txt` | 2,195 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/p01_guard.txt` | 20,077 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/producer_serialization.txt` | 2,010 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/publication_authorization.txt` | 3,582 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/publication_contract.txt` | 3,953 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/publication_envelope.txt` | 2,325 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/publication_extractors.txt` | 7,894 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/publication_predicate.txt` | 4,759 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/publication_status.txt` | 5,543 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/qgv_book.txt` | 2,898 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/qgv_leaderboard.txt` | 2,271 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/qgv_pipeline.txt` | 2,311 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/technical_engine.txt` | 3,313 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/web_mvp.txt` | 7,518 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/web_state_tests.txt` | 17,094 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/governance/source-excerpts/worker_contract.txt` | 16,206 | txt | Historical tracked source-code/document excerpt | Historical governance/source pin review and replay | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/lane-a/SOURCE_PINS.json` | 17,509 | json | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/lane-a/TARGET_ROOT_AND_MEMBERSHIP_EVIDENCE.json` | 32,296 | json | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/lane-a/TARGET_ROOT_AND_THEME_MEMBERSHIP_v0.4.md` | 14,862 | md | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/lane-a/validate_target_sources.py` | 15,877 | py | User-authored TARGET allocation reference/projection; not actual holdings | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/lane-b/MARKET_ADMISSION_19_BY_8_v0.4.json` | 367,542 | json | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/lane-b/MARKET_PRODUCTION_ADMISSION_v0.4.md` | 15,000 | md | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/lane-b/OFFLINE_EVIDENCE_REPLAY_v0.4.json` | 25,190 | json | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/lane-b/PRESERVED_RAW_ANOMALIES_v0.4.json` | 15,161 | json, 원시/조정 가격 | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart/source owner review receipt, policy/evidence or reference document | NO | 정리 필요 | 키: rows.[].latest_comparison_values.close, rows.[].latest_comparison_values.high, rows.[].latest_comparison_values.low 외 5개 키 |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/lane-b/verify_market_evidence.py` | 10,211 | py | Market-source audit/reference evidence; inspect source refs and scalar fields | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/reviews/READINESS_REVIEW.md` | 6,430 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/verify_checkpoint.py` | 3,965 | py | Repository-owned code/test/rendering template | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/page.html` | 6,832 | html | Repository-owned code/test/rendering template | Captured official source or chart-lab presentation asset | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/portfolio_app.js` | 17,564 | js | User-authored TARGET allocation reference/projection; not actual holdings | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/portfolio_browser_test.cjs` | 20,201 | cjs | User-authored TARGET allocation reference/projection; not actual holdings | Offline validation/test harness (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/portfolio_contract.mjs` | 7,964 | mjs | User-authored TARGET allocation reference/projection; not actual holdings | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/portfolio_contract.test.mjs` | 8,426 | mjs | User-authored TARGET allocation reference/projection; not actual holdings | Offline validation/test harness (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/portfolio_fixture.mjs` | 1,267 | mjs | User-authored TARGET allocation reference/projection; not actual holdings | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/portfolio_reference.json` | 4,618 | json | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/raw_store_bridge.mjs` | 8,373 | mjs | Yahoo Finance chart response capture | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/raw_store_bridge.test.mjs` | 8,964 | mjs | Yahoo Finance chart response capture | Offline validation/test harness (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/reviews/api_provider_review.md` | 6,259 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/reviews/chart_guard_review.md` | 11,843 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/reviews/chart_inventory_completeness.md` | 8,856 | md | Repository-owned requirement, governance or validation metadata | Requirements and archived readiness inventory | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/reviews/frontend_architecture_review.md` | 7,768 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/reviews/mcp_architecture_review.md` | 9,014 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/reviews/pit_integration_review.md` | 9,541 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/reviews/portfolio_source_review.md` | 2,422 | md | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/reviews/source_replay_review.md` | 7,705 | md | Repository-owned requirement, governance or validation metadata | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/source_replay.test.mjs` | 2,435 | mjs | Yahoo Finance chart response capture | Offline validation/test harness (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/store_cli.mjs` | 2,367 | mjs | Repository-owned code/test/rendering template | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/target-v0-source-adoption-v1/ADMITTED_TARGET_ROOT.json` | 9,761 | json | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/target-v0-source-adoption-v1/NODE_TESTS.log` | 7,028 | log | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/target-v0-source-adoption-v1/PLAN.md` | 2,555 | md | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/target-v0-source-adoption-v1/README.md` | 2,843 | md | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/target-v0-source-adoption-v1/SIX_GATE_ASSESSMENT.json` | 6,642 | json | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/target-v0-source-adoption-v1/screenshots/portfolio-390-en.png` | 280,133 | PNG, browser_screenshot, synthetic_portfolio | Playwright #portfolio capture after switching to DEMO; explicit fictionalPortfolioFi… | Immutable mobile Korean/English browser evidence for user source adoption, fictional compositi… | NO | 유지 가능 | keys: data_state=DEMO; data_kind=SYNTHETIC_FIXTURE; source=EXPLICIT_SYNTHETIC_FIXTURE; source: Explicit fictional portf… |
| `implementation/experiments/chart-contract-v0.1/target-v0-source-adoption-v1/screenshots/portfolio-390.png` | 276,242 | PNG, browser_screenshot, synthetic_portfolio | Playwright #portfolio capture after switching to DEMO; explicit fictionalPortfolioFi… | Immutable mobile Korean/English browser evidence for user source adoption, fictional compositi… | NO | 유지 가능 | keys: data_state=DEMO; data_kind=SYNTHETIC_FIXTURE; source=EXPLICIT_SYNTHETIC_FIXTURE; source: Explicit fictional portf… |
| `implementation/experiments/chart-contract-v0.1/target-v0-source-adoption-v1/screenshots/portfolio-actual-390-en.png` | 80,068 | PNG, browser_screenshot, actual_unavailable | Playwright #portfolio capture after ACTUAL is withheld; no TARGET substitution. | Immutable mobile Korean/English browser evidence for user source adoption, fictional compositi… | NO | 유지 가능 | keys: ACTUAL NOT_AVAILABLE; doc=null; svg count=0; source: Unavailable ACTUAL mode contains no holdings chart, real acc… |
| `implementation/experiments/chart-contract-v0.1/target-v0-source-adoption-v1/screenshots/portfolio-actual-390-ko.png` | 76,613 | PNG, browser_screenshot, actual_unavailable | Playwright #portfolio capture after ACTUAL is withheld; no TARGET substitution. | Immutable mobile Korean/English browser evidence for user source adoption, fictional compositi… | NO | 유지 가능 | keys: ACTUAL NOT_AVAILABLE; doc=null; svg count=0; source: Unavailable ACTUAL mode contains no holdings chart, real acc… |
| `implementation/experiments/chart-contract-v0.1/target-v0-source-adoption-v1/screenshots/portfolio-target-390-en.png` | 273,247 | PNG, browser_screenshot, non_price_target_reference | Playwright #portfolio capture of authenticated, user-authored TARGET v0 YAML referen… | Immutable mobile Korean/English browser evidence for user source adoption, fictional compositi… | NO | 유지 가능 | keys: source_metadata.owner=USER; weight_basis=TARGET; data_state=REFERENCE; source: Non-price user-authored TARGET v0 … |
| `implementation/experiments/chart-contract-v0.1/target-v0-source-adoption-v1/screenshots/portfolio-target-390-ko.png` | 266,978 | PNG, browser_screenshot, non_price_target_reference | Playwright #portfolio capture of authenticated, user-authored TARGET v0 YAML referen… | Immutable mobile Korean/English browser evidence for user source adoption, fictional compositi… | NO | 유지 가능 | keys: source_metadata.owner=USER; weight_basis=TARGET; data_state=REFERENCE; source: Non-price user-authored TARGET v0 … |
| `implementation/experiments/chart-contract-v0.1/target_v0_projection.json` | 13,514 | json | User-authored TARGET allocation reference/projection; not actual holdings | Chart/source owner review receipt, policy/evidence or reference document | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/target_v0_source.mjs` | 10,821 | mjs | User-authored TARGET allocation reference/projection; not actual holdings | Chart lab source/adapter/build/browser or component code (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/experiments/chart-contract-v0.1/target_v0_source.test.mjs` | 5,907 | mjs | User-authored TARGET allocation reference/projection; not actual holdings | Offline validation/test harness (not executed in this audit) | NO | 유지 가능 | Tracked file at HEAD3877f9a; no populated market observation found by parsed structural scan; metadata/code/nonprice referen… |
| `implementation/fixtures/jpm_financial_synthetic.json` | 463 | text, price_keyword_context, numeric_keyword_context | 명시적 synthetic fixture/characterization | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | kind=SYNTHETIC; financial-only synthetic fixture; capital_return denotes financial capital allocation \| Pinned tracked tree … |
| `implementation/fixtures/official_v11_synthetic_book.json` | 11,590 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 명시적 synthetic fixture/characterization | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | kind=SYNTHETIC; manually specified official-v1.1 synthetic book fixture \| Pinned tracked tree 3877f9a1eab3d511a58bcb7c49c1a8… |
| `implementation/fixtures/official_v11_synthetic_prices.json` | 1,018 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 명시적 synthetic fixture/characterization | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | kind=SYNTHETIC; synthetic book price fixture \| Pinned tracked tree 3877f9a1eab3d511a58bcb7c49c1a833965737d3 \| Keyword line a… |
| `implementation/fixtures/yahoo_chart_nvda_mini.json` | 359 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 출처/샘플 provenance 또는 가격 파생성 미확정 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 판단 보류 | Vendor-shaped chart.result[].meta.regularMarketPrice and quote[].close values; no SYNTHETIC or capture/provenance declaratio… |
| `implementation/reports/alfred_2024-12-31_and_ablation_2026-09-23.json` | 607 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/bench_universe_500_2026-09-23.json` | 1,786 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/bench_universe_500_2026-09-23_openai_r6.txt` | 1,187 | text, price_keyword_context, numeric_keyword_context | 실행/검증 기록 또는 1차 자료의 발췌 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/reports/gate_evidence/blk_dated_identity_regression_2026-09-27.json` | 1,538 | text, numeric_price_or_derived_key | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.fixed[].equal… |
| `implementation/reports/gate_evidence/c21_resume_plan_2024-12-31.json` | 21,449 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/ca_unit_final_revalidation_runner.py` | 2,724 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/reports/gate_evidence/ca_unit_policy_v1.json` | 41,566 | text, price_keyword_context, numeric_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | SCCO corporate-action source evidence excerpts contain actual share-price dollar amounts in quoted primary documents; policy… |
| `implementation/reports/gate_evidence/ca_unit_price_identity_repair.json` | 2,606 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/ca_unit_sources/ANET.html` | 27,747 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/APH.html` | 25,204 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/CBSH.html` | 5,023 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/CMG.html` | 75,153 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/CTAS.html` | 28,930 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/DECK.html` | 10,148 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/ETR.html` | 29,262 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/GE.html` | 59,981 | text, price_keyword_context, numeric_keyword_context | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/HHH.html` | 82,609 | text, price_keyword_context | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/ILMN.html` | 36,194 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/LBTYA.html` | 42,551 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/MDU.html` | 41,377 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/MMM.html` | 36,650 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/MSTR.html` | 26,318 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/NVDA.html` | 305,190 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/PANW.html` | 46,406 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/PARA_historical_chart.json` | 115,778 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.chart.result[… |
| `implementation/reports/gate_evidence/ca_unit_sources/PARA_identity.html` | 110,383 | text, price_keyword_context, numeric_keyword_context | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/PARA_price_source.json` | 140,070 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.chart.result[… |
| `implementation/reports/gate_evidence/ca_unit_sources/SCCO_A.html` | 43,802 | text, price_keyword_context, numeric_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | L8 primary-source fractional-share cash treatment quotes actual share price computed from market high/low; public SEC licens… |
| `implementation/reports/gate_evidence/ca_unit_sources/SCCO_B.html` | 44,629 | text, price_keyword_context, numeric_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | L8 primary-source fractional-share cash treatment quotes actual share price computed from market high/low; public SEC licens… |
| `implementation/reports/gate_evidence/ca_unit_sources/SIRI.html` | 25,211 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/SMCI.html` | 41,083 | text, price_keyword_context, numeric_keyword_context | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/TSCO.html` | 34,521 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/ca_unit_sources/TTEK.html` | 27,033 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/candidate_hygiene_598.json` | 8,110 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/candidate_hygiene_spotcheck_verification.json` | 2,786 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/class_economics_2024-06-30.json` | 18,833 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/class_economics_2024-09-30.json` | 18,634 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/class_economics_2024-12-31.json` | 17,263 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/class_rights_passages_2024-06-30.json` | 99,001 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.issuers.RKT.c… |
| `implementation/reports/gate_evidence/class_rights_passages_2024-09-30.json` | 493,602 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.issuers.BSY.c… |
| `implementation/reports/gate_evidence/class_rights_passages_2024-12-31.json` | 411,873 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.issuers.DKS.c… |
| `implementation/reports/gate_evidence/corporate_action_policy_2024-06-30.json` | 3,703 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/gate_chain_2024-06-30_real_gha.json` | 1,215,723 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.audit.top_cut… |
| `implementation/reports/gate_evidence/gate_chain_2024-09-30_real_gha.json` | 1,213,873 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.audit.top_cut… |
| `implementation/reports/gate_evidence/gate_chain_2024-12-31_claude_code_r4.json` | 14,171 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | audit.price and missing_price are integer coverage counts; cutoff market-cap fields are null. Counts are not prices or price… |
| `implementation/reports/gate_evidence/gate_chain_2024-12-31_claude_code_r6.json` | 14,171 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | audit.price and missing_price are integer coverage counts; cutoff market-cap fields are null. Counts are not prices or price… |
| `implementation/reports/gate_evidence/gate_chain_2024-12-31_real_gha.json` | 1,240,339 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.audit.top_cut… |
| `implementation/reports/gate_evidence/missing_large_cap_priority_plan_2024-12-31.json` | 29,412 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/nport_cross_check_2024-06-30.json` | 5,833 | text, numeric_price_or_derived_key, price_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.filings[].cal… |
| `implementation/reports/gate_evidence/nport_price_exception_2024-06-30.json` | 787 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/nport_price_exception_2024-09-30.json` | 787 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/nport_price_exception_2024-12-31.json` | 346 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/nport_price_investigation_2024-06-30.json` | 1,084 | text, price_keyword_context, numeric_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | issuers[].holding_raw.val_usd numeric string and reported_value_per_share; actual NPORT market value/implied price. \| Pinned… |
| `implementation/reports/gate_evidence/nport_reported_prices_2024-06-30.json` | 5,224 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.issuers.PINC.… |
| `implementation/reports/gate_evidence/nport_reported_prices_2024-09-30.json` | 5,206 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.issuers.PINC.… |
| `implementation/reports/gate_evidence/nport_reported_prices_2024-12-31.json` | 5,269 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.issuers.PINC.… |
| `implementation/reports/gate_evidence/nport_unresolved_source_audit_2024-06-30.json` | 2,857 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/official_pipeline_2024-06-30_2024-06-30.json` | 419 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/official_pipeline_2024-06-30_2024-12-31.json` | 35,192 | text, numeric_price_or_derived_key | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.per_date[].cu… |
| `implementation/reports/gate_evidence/official_pipeline_2024-09-30_2024-09-30.json` | 1,795 | text, numeric_price_or_derived_key | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.per_date[].cu… |
| `implementation/reports/gate_evidence/official_pipeline_2024-12-31_2024-12-31.json` | 1,799 | text, numeric_price_or_derived_key | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.per_date[].cu… |
| `implementation/reports/gate_evidence/official_snapshot_2024-06-30.json` | 180,625 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.cutoff_mcap, … |
| `implementation/reports/gate_evidence/official_snapshot_2024-09-30.json` | 180,565 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.cutoff_mcap, … |
| `implementation/reports/gate_evidence/official_snapshot_2024-12-31.json` | 180,645 | 실자료, 가격 파생 데이터 | Official US market-cap PIT frozen source, provenance hash checked by repository_bund… | Immutable methodological/history source currently public in repo; mcap/cutoff_mcap are strippe… | CONDITIONAL | 정리 필요 | JSON $.kind=OFFICIAL_US_MCAP_TOP500_PIT; $.members length=500 |
| `implementation/reports/gate_evidence/promotion_gate_v2_2024-12-31.json` | 1,317 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/promotion_gate_v2_2024-12-31_updated.json` | 1,317 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/russell1000_extra_listings_2024-06-30.json` | 98,885 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Membership and security/CIK/name/source identity only; no holding valUSD, balance-derived price or numeric market cap. Russe… |
| `implementation/reports/gate_evidence/russell1000_extra_listings_2024-09-30.json` | 98,808 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Membership and security/CIK/name/source identity only; no holding valUSD, balance-derived price or numeric market cap. Russe… |
| `implementation/reports/gate_evidence/russell1000_extra_listings_2024-12-31.json` | 98,166 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Membership and security/CIK/name/source identity only; no holding valUSD, balance-derived price or numeric market cap. Russe… |
| `implementation/reports/gate_evidence/russell1000_nport_2024-06-30.json` | 272,877 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Membership and security/CIK/name/source identity only; no holding valUSD, balance-derived price or numeric market cap. Russe… |
| `implementation/reports/gate_evidence/russell1000_nport_2024-09-30.json` | 255,778 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Membership and security/CIK/name/source identity only; no holding valUSD, balance-derived price or numeric market cap. Russe… |
| `implementation/reports/gate_evidence/russell1000_nport_2024-12-31.json` | 251,747 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Membership and security/CIK/name/source identity only; no holding valUSD, balance-derived price or numeric market cap. Russe… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0000014693_2024-12-31.json` | 30,322 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0000091142_2024-12-31.json` | 23,612 | text, price_keyword_context, numeric_keyword_context | 출처/샘플 provenance 또는 가격 파생성 미확정 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 판단 보류 | Public-financial share-count diagnostic includes option exercise-price / intrinsic-value / FMV excerpt context. Origin and e… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0000317540_2024-12-31.json` | 23,529 | text, price_keyword_context, numeric_keyword_context | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0001037646_2024-12-31.json` | 27,936 | text | 출처/샘플 provenance 또는 가격 파생성 미확정 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 판단 보류 | Public-financial share-count diagnostic includes option exercise-price / intrinsic-value / FMV excerpt context. Origin and e… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0001089063_2024-06-30.json` | 30,905 | text, price_keyword_context, numeric_keyword_context | 출처/샘플 provenance 또는 가격 파생성 미확정 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 판단 보류 | Public-financial share-count diagnostic includes option exercise-price / intrinsic-value / FMV excerpt context. Origin and e… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0001089063_2024-09-30.json` | 30,020 | text, price_keyword_context, numeric_keyword_context | 출처/샘플 provenance 또는 가격 파생성 미확정 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 판단 보류 | Public-financial share-count diagnostic includes option exercise-price / intrinsic-value / FMV excerpt context. Origin and e… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0001089063_2024-12-31.json` | 28,962 | text, price_keyword_context, numeric_keyword_context | 출처/샘플 provenance 또는 가격 파생성 미확정 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 판단 보류 | Public-financial share-count diagnostic includes option exercise-price / intrinsic-value / FMV excerpt context. Origin and e… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0001156375_2024-12-31.json` | 30,755 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0001381197_2024-06-30.json` | 39,967 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0001381197_2024-09-30.json` | 40,158 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0001381197_2024-12-31.json` | 39,474 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0001526520_2024-12-31.json` | 36,216 | text, price_keyword_context, numeric_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | SEC share-count diagnostic excerpts also embed actual repurchase average prices or public-float aggregate market value; shar… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0001675149_2024-12-31.json` | 35,806 | text, price_keyword_context, numeric_keyword_context | 출처/샘플 provenance 또는 가격 파생성 미확정 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 판단 보류 | Public-financial share-count diagnostic includes option exercise-price / intrinsic-value / FMV excerpt context. Origin and e… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0001699031_2024-06-30.json` | 34,488 | text | 공개 재무·발행주식/identity 자료 또는 provenance metadata | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Primary-source content inspected: share counts, par values, split/exchange ratios, dividends/EPS/revenue and identity contex… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0001800227_2024-06-30.json` | 41,236 | text, price_keyword_context, numeric_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | SEC share-count diagnostic excerpts also embed actual repurchase average prices or public-float aggregate market value; shar… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0001800227_2024-09-30.json` | 40,385 | text, price_keyword_context, numeric_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | SEC share-count diagnostic excerpts also embed actual repurchase average prices or public-float aggregate market value; shar… |
| `implementation/reports/gate_evidence/share_count_diagnostic_0001800227_2024-12-31.json` | 38,777 | text, price_keyword_context, numeric_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | SEC share-count diagnostic excerpts also embed actual repurchase average prices or public-float aggregate market value; shar… |
| `implementation/reports/gate_evidence/sp500_current_2026_raw.md` | 63,189 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/reports/gate_evidence/sp500_reconstructed_2024-12-31.json` | 6,983 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/symbol_mappings_2024-06-30.json` | 1,879 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/symbol_mappings_2024-09-30.json` | 1,879 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/symbol_mappings_2024-12-31.json` | 1,832 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/top500_sufficiency_gate_2024-12-31.json` | 652 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/top500_sufficiency_gate_2024-12-31_real_reference.json` | 5,345 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gate_evidence/track_a_ca_unit_20_case_revalidation_2026-09-27.json` | 59,541 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.additional_d3… |
| `implementation/reports/gate_evidence/track_a_compare_vintages_runner.py` | 1,422 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/reports/gate_evidence/track_a_data_vintage_comparison_2026-09-27.json` | 408,222 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.absolute_retu… |
| `implementation/reports/gate_evidence/track_a_diagnostic_replay_2026-09-27.json` | 32,340 | text, numeric_price_or_derived_key | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.walk_forward.… |
| `implementation/reports/gate_evidence/track_a_explain_vintage_runner.py` | 2,406 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/reports/gate_evidence/track_a_final_audit_runner.py` | 5,877 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/reports/gate_evidence/track_a_freeze_readiness_2026-09-27.json` | 8,781 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.per_date[].cu… |
| `implementation/reports/gate_evidence/track_a_network_500_benchmark_2026-09-27.json` | 1,064,152 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.equal_weight_… |
| `implementation/reports/gate_evidence/track_a_network_benchmark_runner.py` | 4,772 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/reports/gate_evidence/track_a_pit_provenance_audit_2026-09-27.json` | 15,207 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.per_date[].ap… |
| `implementation/reports/gate_evidence/track_a_price_identity_audit_2026-09-27.json` | 431,426 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Provider/SEC identity mapping and exception references only; PRICE/COSTCO/PRICELINE are company-name false positives. No act… |
| `implementation/reports/gate_evidence/track_a_share_unit_policy_proposal_2026-09-27.md` | 7,148 | text, price_keyword_context, numeric_keyword_context | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | L38 reproduces historical SIRI market cap and actual price-derived rank. \| Pinned tracked tree 3877f9a1eab3d511a58bcb7c49c1a… |
| `implementation/reports/gate_evidence/universe_completeness_gate_2024-12-31.json` | 701 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/gfactor_coverage_2026-09-23.json` | 2,660 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.rows[].qualit… |
| `implementation/reports/live_smoke_2026-09-23.json` | 878 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.yahoo.jpm.pri… |
| `implementation/reports/mcap_audit_2024-12-31.json` | 533 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | audit.price and missing_price are integer coverage counts; cutoff market-cap fields are null. Counts are not prices or price… |
| `implementation/reports/mcap_gap_plan.json` | 6,170 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/mcap_missing_ciks.json` | 1,761 | text | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/mcap_missing_plan.json` | 4,180 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/mcap_pool_coverage_2026-09-23_1745.json` | 632 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.cutoff_mcap \|… |
| `implementation/reports/mini_pytest_2026-09-24_claude.txt` | 1,420 | text, price_keyword_context, numeric_keyword_context | 실행/검증 기록 또는 1차 자료의 발췌 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/reports/mini_pytest_2026-09-24_claude_2.txt` | 1,752 | text, price_keyword_context, numeric_keyword_context | 실행/검증 기록 또는 1차 자료의 발췌 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/reports/mini_pytest_2026-09-25_claude.txt` | 2,436 | text, price_keyword_context, numeric_keyword_context | 실행/검증 기록 또는 1차 자료의 발췌 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/reports/mini_pytest_2026-09-25_claude_code_r4.txt` | 2,356 | text, price_keyword_context, numeric_keyword_context | 실행/검증 기록 또는 1차 자료의 발췌 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/reports/mini_pytest_2026-09-25_claude_code_r6.txt` | 4,356 | text, price_keyword_context, numeric_keyword_context | 실행/검증 기록 또는 1차 자료의 발췌 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/reports/mini_pytest_2026-09-25_claude_code_r7.txt` | 4,356 | text, price_keyword_context, numeric_keyword_context | 실행/검증 기록 또는 1차 자료의 발췌 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/reports/network_probe_2026-09-25_claude_code_r4.json` | 1,374 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/network_probe_2026-09-25_claude_code_r6.json` | 1,037 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/official_mcap500_from_store_2024-12-31.json` | 1,423 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.report.cutoff… |
| `implementation/reports/official_v11_book_2026-09-23.json` | 313 | text | 명시적 synthetic fixture/characterization | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | kind=SYNTHETIC; synthetic_all=true; v_production_all_none=true \| Pinned tracked tree 3877f9a1eab3d511a58bcb7c49c1a833965737d… |
| `implementation/reports/official_v11_book_snapshots.json` | 51,193 | 합성 검증 | kind=SYNTHETIC and synthetic_all=true. | Demo QGV snapshot test vectors; not acquired provider prices merely because V/score fields exi… | CONDITIONAL | 유지 가능 | JSON $.kind=SYNTHETIC; $.synthetic_all=true |
| `implementation/reports/pit_multi_asof_2026-09-23.json` | 5,201 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.rows[].qualit… |
| `implementation/reports/pit_price_probe_2026-09-23.json` | 260 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.pit_price \| P… |
| `implementation/reports/prompt_library/prompt_library.html` | 491,188 | text, price_keyword_context, numeric_keyword_context | 계약/정책/설계/업무 기록 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Document text inspected; market data concepts, formula coefficients, scope/milestone/test counts, dates/SHAs/PR identifiers … |
| `implementation/reports/raw_persistence/raw_dataset_manifest_2026-10-01.json` | 5,176 | text, price_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Manifest/hash/location or restoration status and price_bars count only; not embedded raw bars. External referenced data is o… |
| `implementation/reports/raw_persistence/restore_check_2026-10-01.json` | 2,261 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Manifest/hash/location or restoration status and price_bars count only; not embedded raw bars. External referenced data is o… |
| `implementation/reports/real_canary_slice_wf_2026-09-23.json` | 314 | text, numeric_price_or_derived_key | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.slice.equal_w… |
| `implementation/reports/real_data_candidate_2026-09-23.json` | 1,845 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.live_prices.a… |
| `implementation/reports/real_ingestion_probe_2026-09-23_grok.txt` | 1,117 | text, price_keyword_context, numeric_keyword_context | 실행/검증 기록 또는 1차 자료의 발췌 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/reports/real_ingestion_probe_2026-09-23_grok_r7.txt` | 2,778 | text, price_keyword_context, numeric_keyword_context | 실행/검증 기록 또는 1차 자료의 발췌 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/reports/real_ingestion_probe_2026-09-23_openai_r5.txt` | 926 | text, price_keyword_context, numeric_keyword_context | 실행/검증 기록 또는 1차 자료의 발췌 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/reports/real_ingestion_probe_2026-09-23_openai_r6.txt` | 912 | text, price_keyword_context, numeric_keyword_context | 실행/검증 기록 또는 1차 자료의 발췌 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/reports/real_replay_2026-09-23_1709.json` | 580 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.wf_steps[].eq… |
| `implementation/reports/statement_coverage_2026-09-23.json` | 4,495 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.rows[].qualit… |
| `implementation/reports/synthetic_pipeline_2026-09-23.json` | 10,496 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 명시적 synthetic fixture/characterization | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | qgv_snapshots[].synthetic=true; fixture-generated V and rank \| Pinned tracked tree 3877f9a1eab3d511a58bcb7c49c1a833965737d3 … |
| `implementation/reports/track_a_regression_2026-09-27.txt` | 4,734 | text, price_keyword_context, numeric_keyword_context | 실행/검증 기록 또는 1차 자료의 발췌 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Decoded text inspected; price/coverage/missing counters and test verdicts are metadata, not quote bars or realized-return va… |
| `implementation/reports/track_store.json` | 779,531 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 출처/샘플 provenance 또는 가격 파생성 미확정 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 판단 보류 | Stored prediction.expected_return numeric records without file-level SYNTHETIC provenance. A present synthetic e2e generator… |
| `implementation/reports/track_store_e2e.json` | 10,380 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 출처/샘플 provenance 또는 가격 파생성 미확정 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 판단 보류 | Stored expected_return/realized_return numeric records lack explicit archived SYNTHETIC provenance. Current validation/e2e.p… |
| `implementation/reports/us17_5y_hist_ablation_2026-09-23.json` | 2,927 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.ablation.arms… |
| `implementation/reports/us17_alfred_pit_2026-09-23.json` | 1,561 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.ablation_arms… |
| `implementation/reports/us17_child_outcomes_2026-09-23.json` | 241 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.median_return… |
| `implementation/reports/us17_multi_asof_pit_2026-09-23.json` | 1,574 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/us_ingested_facts_listings.json` | 28,708 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/us_listings_outcomes_2026-09-23.json` | 3,721 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.outcomes.amd.… |
| `implementation/reports/us_live_prices_2026-09-23.json` | 4,870 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.prices.amd.pr… |
| `implementation/reports/us_sec_tickers_listings.json` | 504,522 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/us_session_mixed_2026-09-23.json` | 8,219 | 실자료, 실가격+합성 혼합 | SESSION_MIXED with qgv_kind=SYNTHETIC and price_kind=LIVE_FETCH; exact provider sour… | 17 rows and 17 holdings contain numeric acquired price; demo_bundle copies holdings into DEMO … | CONDITIONAL | 정리 필요 | JSON $.kind=SESSION_MIXED; $.qgv_kind=SYNTHETIC; $.price_kind=LIVE_FETCH |
| `implementation/reports/us_session_track_record.json` | 2,472 | text, price_keyword_context, numeric_keyword_context | 계약/검증/조정 metadata 또는 공개 재무/identity 결과 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | Exact JSON leaf-key inspection found no embedded actual price, price-derived valuation/rank, or return scalar; price/mcap/re… |
| `implementation/reports/v_coverage_us17_2026-09-23.json` | 6,886 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.rows[].V \| Pi… |
| `implementation/reports/validation_e2e_2026-09-23.json` | 655 | text | 명시적 synthetic fixture/characterization | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 유지 가능 | kind=INTEGRATED_E2E_SYNTHETIC; generator constructs synthetic inputs; record envelope identifiers and verdicts, no actual-pr… |
| `implementation/reports/vertical_slice_2024-12-31.json` | 1,119 | text, numeric_price_or_derived_key, price_keyword_context, numeric_ke… | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $.equal_weight_… |
| `implementation/reports/vertical_slice_windows_2026-09-23.json` | 277 | text, numeric_price_or_derived_key | 보존된 실제/비synthetic 가격·가격 파생 자료 또는 그 재인용 | 과거 수집·replay·검증 결과 또는 1차 자료/로그; 과거 증빙·runner 소비 | UNKNOWN | 정리 필요 | Embedded non-synthetic historical/live report numeric price, market-cap, valuation or outcome-return fields: $[].ew \| Pinned… |
| `implementation/src/investment_system/__init__.py` | 810 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/contracts/context.py` | 493 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/contracts/enums.py` | 2,595 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/contracts/global_universe.py` | 6,228 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/contracts/models.py` | 7,041 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/contracts/portfolio_input.py` | 1,215 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/contracts/prediction.py` | 1,863 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/contracts/product.py` | 2,780 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/contracts/raw.py` | 2,327 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/contracts/strategy.py` | 6,791 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/contracts/universe.py` | 3,446 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/ingestion/__init__.py` | 365 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/ingestion/manifest.py` | 1,709 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/ingestion/raw_store.py` | 3,395 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/ingestion/replay.py` | 4,507 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/ingestion/sec_m1.py` | 10,654 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/integration/compatibility.py` | 1,768 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/integration/engine.py` | 3,842 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/macro/engine.py` | 1,595 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/markets/kr.py` | 564 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/markets/us.py` | 2,413 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/personal/__init__.py` | 472 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/personal/fit.py` | 2,410 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/personal/money.py` | 2,178 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/personal/portfolio.py` | 5,986 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/personal/ports.py` | 4,257 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/personal/quality.py` | 988 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/personal/security.py` | 4,196 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/personal/timecontract.py` | 1,893 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/personal/versioning.py` | 1,944 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/personal/weights.py` | 7,484 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/pit/resolver.py` | 1,471 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/producers/adapters.py` | 4,912 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/producers/assembler.py` | 5,110 | 코드, 계약 | Validated supplied producer snapshots. | Preserves usable snap.data and provenance; timestamp/schema validation, not redistribution/red… | CONDITIONAL | 유지 가능 | implementation/src/investment_system/producers/assembler.py:26-50 |
| `implementation/src/investment_system/producers/contract.py` | 13,198 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/producers/freshness.py` | 1,756 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/producers/raw_persistence.py` | 5,852 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/producers/registry.py` | 6,121 | 코드, 계약 | Real hash-verified Frozen snapshot; current default other sections unavailable. | Frozen producer emits full snapshot and source hashes; does not itself publish. | CONDITIONAL | 유지 가능 | implementation/src/investment_system/producers/registry.py:58-88 |
| `implementation/src/investment_system/producers/serialization.py` | 2,009 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/product/device_actual_catalog.py` | 5,798 | 코드, 계약 | Pinned security identity map/theme/TARGET; no runtime quote source in catalog. | Public identity/TARGET catalog; rejects private holding/token shapes but is not a blanket pric… | CONDITIONAL | 유지 가능 | implementation/src/investment_system/product/device_actual_catalog.py:20-45 narrow private-shape rejection |
| `implementation/src/investment_system/product/entity_catalog.py` | 5,399 | 코드, 계약 | Existing company identity and navigation metadata. | Generate entity search catalog; membership identity metadata only. | CONDITIONAL | 유지 가능 | implementation/src/investment_system/product/entity_catalog.py:32-85 |
| `implementation/src/investment_system/product/render_app.py` | 8,240 | 코드, 계약 | Static AppShell and prompt/scoring status metadata. | HTML templates for separate rendered AppShell routes; no acquired price payload observed. | NO | 유지 가능 | implementation/src/investment_system/product/render_app.py:147-159 |
| `implementation/src/investment_system/product/web_assets/app.js` | 51,699 | 코드, 공개 출력 경로(소스/설정) | Public data.json/companies/current optional producer sections. Current default non-u… | Displays current Frozen market_cap_rank; conditionally displays upstream V/total QGV, returns,… | YES | 정리 필요 | implementation/src/investment_system/product/web_assets/app.js:306 evidence object display |
| `implementation/src/investment_system/product/web_assets/device-actual.css` | 4,593 | 코드, 계약 | Static HTML/CSS/localization definitions. | Presentation and wording; no price-provider payload source. | YES | 유지 가능 | implementation/src/investment_system/product/web_assets/device-actual.css:1 |
| `implementation/src/investment_system/product/web_assets/device-actual.js` | 56,428 | 코드, 계약 | User device-local holdings/manual/Sheet market data, not a server/public snapshot so… | IndexedDB device records and explicitly requested local file download; no automated public exp… | YES | 유지 가능 | implementation/src/investment_system/product/web_assets/device-actual.js:402-410 local import transaction |
| `implementation/src/investment_system/product/web_assets/device-market.js` | 15,815 | 코드, 계약 | Manual and Google Sheet device-local quotes/FX, validated at runtime; no acquired va… | Computes device actual valuations and device backup market_data. Existing manual/Sheet persist… | YES | 유지 가능 | implementation/src/investment_system/product/web_assets/device-market.js:114-118 price validation |
| `implementation/src/investment_system/product/web_assets/entity-search.js` | 4,700 | 코드, 계약 | Identity aliases and query strings. | Search relevance rank is lexical navigation matching, not price-derived market-cap rank. | YES | 유지 가능 | implementation/src/investment_system/product/web_assets/entity-search.js:38-81 lexical match rank/score |
| `implementation/src/investment_system/product/web_assets/google-sheet-core.js` | 11,838 | 코드, 계약 | Runtime private Google Sheet/Paste response values. | Normalize quote/FX rows and merge into device-local market state; source numeric rules are val… | YES | 유지 가능 | implementation/src/investment_system/product/web_assets/google-sheet-core.js:44-58 numeric validator |
| `implementation/src/investment_system/product/web_assets/google-sheet-quotes.css` | 2,553 | 코드, 계약 | Static HTML/CSS/localization definitions. | Presentation and wording; no price-provider payload source. | YES | 유지 가능 | implementation/src/investment_system/product/web_assets/google-sheet-quotes.css:1 |
| `implementation/src/investment_system/product/web_assets/google-sheet-quotes.js` | 27,464 | 코드, 계약 | Google GIS access token/private readonly Sheets; optional approved private Worker hi… | Token only in memory; Bearer sent to Sheets or approved Worker, no-store/omit/referrer control… | YES | 유지 가능 | implementation/src/investment_system/product/web_assets/google-sheet-quotes.js:110-125 token lifetime/memory |
| `implementation/src/investment_system/product/web_assets/index.html` | 3,952 | 코드, 계약 | Static HTML/CSS/localization definitions. | Presentation and wording; no price-provider payload source. | YES | 유지 가능 | implementation/src/investment_system/product/web_assets/index.html:1 |
| `implementation/src/investment_system/product/web_assets/locale.js` | 33,165 | 코드, 계약 | Static HTML/CSS/localization definitions. | Presentation and wording; no price-provider payload source. | YES | 유지 가능 | implementation/src/investment_system/product/web_assets/locale.js:1 |
| `implementation/src/investment_system/product/web_assets/network-bridge.js` | 4,035 | 코드, 계약 | Track D navigation/locale messages. | Presentation bridge; no acquired price payload observed. | NO | 유지 가능 | implementation/src/investment_system/product/web_assets/network-bridge.js:50-54 sender/origin validation |
| `implementation/src/investment_system/product/web_assets/private-history.js` | 15,268 | 코드, 계약 | Public browser program and TARGET19 identity map; runtime history enters through ses… | Store only user-selected Worker origin locally; keep fetched bars in state.data; render privat… | YES | 유지 가능 | implementation/src/investment_system/product/web_assets/private-history.js:20-41 payload field validation/copy |
| `implementation/src/investment_system/product/web_assets/research-bridge.js` | 6,992 | 코드, 계약 | Explicit parent public context, not device storage or private Worker payload. | Same-origin selection and prompt field presentation; private-history path does not feed it. | CONDITIONAL | 유지 가능 | implementation/src/investment_system/product/web_assets/research-bridge.js:85-99 explicit field selector |
| `implementation/src/investment_system/product/web_mvp.py` | 7,833 | 코드, 공개 출력 경로(소스/설정) | Hash-verified official Frozen universe; optional SYNTHETIC QGV plus mixed SESSION_MI… | Creates company market_cap_rank, preserves full universe, and writes validated bundle verbatim… | CONDITIONAL | 정리 필요 | implementation/src/investment_system/product/web_mvp.py:72-103 repository/demo source mapping |
| `implementation/src/investment_system/prompt_library/__init__.py` | 238 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/prompt_library/catalog.py` | 14,406 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/prompt_library/content/Investment_Prompt_Library_v1_Content_Catalog_FROZEN.md` | 161,496 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/prompt_library/content/Investment_Prompt_Library_v1_Decision_History.md` | 11,784 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/prompt_library/fill.py` | 36,027 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/prompt_library/search.py` | 4,246 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/prompt_library/ui.py` | 22,134 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/prompt_library/validation.py` | 6,453 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/providers/__init__.py` | 300 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/providers/base.py` | 554 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/providers/catalog.py` | 1,944 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/providers/env_price.py` | 2,468 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/providers/fred_alfred.py` | 4,499 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/providers/fred_csv.py` | 3,945 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/providers/memory.py` | 2,211 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/providers/sec_accn_reconcile.py` | 1,313 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/providers/sec_companyfacts.py` | 11,281 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/providers/sec_cover_shares.py` | 9,935 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/providers/sec_m1.py` | 16,388 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/providers/sec_submissions.py` | 2,472 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/providers/sec_vintage.py` | 4,317 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/providers/us_sec.py` | 928 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/providers/yahoo_chart.py` | 3,874 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/__init__.py` | 243 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/analysis.py` | 5,374 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/book.py` | 2,897 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/compatibility.py` | 2,197 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/factors.py` | 3,830 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/financial_issuer.py` | 1,794 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/g_horizon.py` | 5,017 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/html_sample.py` | 4,988 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/identifiers.py` | 3,163 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/leaderboard.py` | 2,480 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/pipeline.py` | 2,310 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/portfolio.py` | 7,686 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/quarterly_series.py` | 4,276 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/raw_map.py` | 7,766 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/scoring.py` | 5,247 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/scoring_standard.py` | 697 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/sec_m2.py` | 20,756 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/simulation.py` | 1,816 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/track_record.py` | 1,922 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/qgv/us_live.py` | 8,803 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/rig/adapter.py` | 1,073 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/rig/discovery/discovery.py` | 6,309 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/rig/discovery/impact.py` | 5,618 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/rig/discovery/present.py` | 7,265 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/rig/gate.py` | 11,363 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/rig/intel/intel.py` | 11,790 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/rig/intel/present.py` | 4,041 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/rig/ledger.py` | 5,557 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/rig/model.py` | 11,121 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/rig/myview/prefs.py` | 5,061 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/rig/myview/present.py` | 7,164 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/rig/myview/scope.py` | 10,131 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/rig/network/labels.py` | 1,932 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/rig/network/render.py` | 12,877 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/rig/network/views.py` | 11,495 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/technical/engine.py` | 2,424 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/universe/__init__.py` | 744 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/universe/engine.py` | 5,836 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/universe/events.py` | 6,445 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/universe/recon.py` | 2,006 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/universe/resolve.py` | 3,705 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/universe/sources.py` | 12,487 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/validation/__init__.py` | 257 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/validation/ablation.py` | 4,316 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/validation/adapters.py` | 1,729 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/validation/backtest.py` | 1,586 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/validation/e2e.py` | 8,738 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/validation/engine.py` | 982 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/validation/file_store.py` | 2,642 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/validation/historical.py` | 26,112 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/validation/integrated.py` | 1,293 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/validation/outcome.py` | 2,047 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/validation/records.py` | 1,795 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/validation/vertical_slice.py` | 9,030 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/src/investment_system/versions.py` | 616 | text | 코드/계약 또는 단위 검증 정의 | 런타임 라이브러리/계약/파서 구현; 실제 실행 입력과 파일에 내장된 샘플을 구분 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/helpers.py` | 693 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/rig_fixtures.py` | 3,800 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/synthetic_universe.py` | 3,684 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_ablation_ready_rows.py` | 1,239 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_analysis_scoring.py` | 2,538 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_asml_eps_and_g_horizon_attach.py` | 1,619 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_attach_name_outcomes.py` | 1,684 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_audit_mcap_store.py` | 6,444 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_autonomy_gate_a_guard.py` | 55,803 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_book_catalog_financial.py` | 2,914 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_bulk_archive_integrity.py` | 3,396 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_c18_resolved_official.py` | 4,745 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_c21_runner_and_gate_chain.py` | 163,037 | text, price_keyword_context, numeric_keyword_context | 출처/샘플 provenance 또는 가격 파생성 미확정 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 판단 보류 | Mixed constructed mocks and actual-report dependencies. L1350-1364 dated HXL close literal and L1761-1782 AMTM close/resulti… |
| `implementation/tests/test_ca_unit_policy.py` | 6,205 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_candidate_hygiene.py` | 2,080 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_d3p_gral_evidence.py` | 2,493 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_device_actual_build.py` | 8,450 | 코드, 합성 검증 | Static contract regression code; repository source fixtures may be loaded during an … | Test guards/build behavior; test pass from this static audit is not asserted. | NO | 유지 가능 | implementation/tests/test_device_actual_build.py:1 |
| `implementation/tests/test_downstream_and_integration.py` | 4,043 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_fcf_eps_picker.py` | 2,223 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_fetch_krx_tool_offline.py` | 793 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_fetch_tool_offline.py` | 1,756 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_file_store_and_conflicts.py` | 1,661 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_file_store_scaling.py` | 1,207 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_fred_csv.py` | 1,291 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_full_pit_eval.py` | 1,693 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_g_horizon.py` | 1,876 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_generic_portfolio_input.py` | 1,155 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_global_language_search.py` | 4,251 | 코드, 합성 검증 | Static contract regression code; repository source fixtures may be loaded during an … | Test guards/build behavior; test pass from this static audit is not asserted. | NO | 유지 가능 | implementation/tests/test_global_language_search.py:1 |
| `implementation/tests/test_global_universe_contracts.py` | 3,945 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_hist_peer_ablation_pit.py` | 3,061 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_horizon_window.py` | 1,755 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_ingestion_raw_store.py` | 8,289 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_live_sources_and_persist.py` | 1,364 | text, price_keyword_context, numeric_keyword_context | 출처/샘플 provenance 또는 가격 파생성 미확정 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 판단 보류 | L9-20 reads yahoo_chart_nvda_mini.json, embeds matching regularMarketPrice assertion, asserts stamp.synthetic=False; actual-… |
| `implementation/tests/test_msft_asml_concept_and_outcome.py` | 3,075 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_multi_asof_outcomes.py` | 1,522 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_official_universe_from_store.py` | 3,324 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_outcome_and_period_quality.py` | 2,450 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_pages_artifact_guard.py` | 26,393 | 코드, 합성 검증 | Static contract regression code; repository source fixtures may be loaded during an … | Test guards/build behavior; test pass from this static audit is not asserted. | NO | 유지 가능 | implementation/tests/test_pages_artifact_guard.py:1 |
| `implementation/tests/test_pages_cockpit_build.py` | 4,672 | 코드, 합성 검증 | Static contract regression code; repository source fixtures may be loaded during an … | Test guards/build behavior; test pass from this static audit is not asserted. | NO | 유지 가능 | implementation/tests/test_pages_cockpit_build.py:1 |
| `implementation/tests/test_peer_derived_v.py` | 1,736 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_pil_p0_contracts.py` | 12,617 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_pit_simulation.py` | 1,883 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_pit_vintage_historical.py` | 3,499 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_portfolio_ids.py` | 1,083 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_portfolio_target_v0.py` | 16,707 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_private_history_build.py` | 2,604 | 코드, 계약, 합성 검증 | Static build-contract assertions; does not embed acquired provider bars or credentia… | Specify public local asset inclusion, OFF config, no Worker CSP destination and no extra histo… | NO | 유지 가능 | implementation/tests/test_private_history_build.py:18-27 asset and app mount expectations |
| `implementation/tests/test_private_history_worker.py` | 1,000 | 코드, 합성 검증 | Python wrapper over three mocked/synthetic Node suites; no provider data embedded. | Capture Node stdout/stderr and include them in assertion diagnostics if the mocked suite fails. | NO | 유지 가능 | implementation/tests/test_private_history_worker.py:14-20 subprocess invokes only worker mock, private history node and synt… |
| `implementation/tests/test_producer_infrastructure.py` | 16,088 | 코드, 합성 검증 | Static contract regression code; repository source fixtures may be loaded during an … | Test guards/build behavior; test pass from this static audit is not asserted. | NO | 유지 가능 | implementation/tests/test_producer_infrastructure.py:1 |
| `implementation/tests/test_product_strategy_validation.py` | 3,512 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_prompt_library_v1.py` | 17,236 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_qgv_common_contract_vnext.py` | 10,655 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_qgv_scoring_standard_v1.py` | 13,948 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_quarterly_10q_monitor.py` | 2,544 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_raw_and_providers.py` | 4,654 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_reconstruct_sp500_from_wikipedia.py` | 4,783 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_rig_p0_foundation.py` | 19,245 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_rig_p1_network.py` | 10,430 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_rig_p2_intel.py` | 10,793 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_rig_p3_myview.py` | 13,070 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_rig_p4_discovery.py` | 10,174 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_sec_m1_provider.py` | 21,271 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_sec_m1_receipts.py` | 8,435 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_sec_m1_tool.py` | 5,193 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_sec_m2_qg.py` | 27,996 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_sec_m2_tool.py` | 10,454 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_session_envelope_sec_form.py` | 1,457 | text, price_keyword_context, numeric_keyword_context | 출처/샘플 provenance 또는 가격 파생성 미확정 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 판단 보류 | L32-34 injects real-symbol decimal prices with evidence=LIVE_FETCH; inline injection does not establish live acquisition, bu… |
| `implementation/tests/test_top500_sufficiency_and_completeness_gates.py` | 10,595 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_universe_engine.py` | 2,451 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_universe_pit_incremental.py` | 10,542 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_universe_resolve_and_candidates.py` | 6,215 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_us_listings_pit_universe.py` | 2,544 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_us_session_html.py` | 1,760 | text, price_keyword_context, numeric_keyword_context | 출처/샘플 provenance 또는 가격 파생성 미확정 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 판단 보류 | L29-42 injects real-symbol decimal prices with evidence=LIVE_FETCH; inline injection without explicit synthetic/creation pro… |
| `implementation/tests/test_us_track.py` | 1,632 | text | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_v_coverage_matrix.py` | 1,694 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_v_prior_and_c15.py` | 2,231 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_validation_framework.py` | 3,953 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_vertical_slice.py` | 783 | text, price_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_vertical_slice_from_store.py` | 6,840 | text, price_keyword_context, numeric_keyword_context | 코드/계약 또는 단위 검증 정의 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 유지 가능 | Static code defines adapters/formulas/contracts or constructed mock inputs; external-data reads are consumer dependencies, n… |
| `implementation/tests/test_web_mvp.py` | 3,461 | 코드, 합성 검증 | Static contract regression code; repository source fixtures may be loaded during an … | Test guards/build behavior; test pass from this static audit is not asserted. | NO | 유지 가능 | implementation/tests/test_web_mvp.py:1 |
| `implementation/tests/test_web_research_guard.py` | 8,986 | 코드, 합성 검증 | Static contract regression code; repository source fixtures may be loaded during an … | Test guards/build behavior; test pass from this static audit is not asserted. | NO | 유지 가능 | implementation/tests/test_web_research_guard.py:1 |
| `implementation/tests/test_web_state_presentation.py` | 17,228 | 코드, 합성 검증 | Static contract regression code; repository source fixtures may be loaded during an … | Test guards/build behavior; test pass from this static audit is not asserted. | NO | 유지 가능 | implementation/tests/test_web_state_presentation.py:1 |
| `implementation/tests/test_yahoo_adjclose_bars.py` | 770 | text, price_keyword_context, numeric_keyword_context | 출처/샘플 provenance 또는 가격 파생성 미확정 | 파서·계약·계산 검증 또는 샘플 fixture 입력; 실행하지 않고 정적 내용·의존 경로만 검토 | UNKNOWN | 판단 보류 | L5-18 INTC dated vendor-shaped inline price/adjclose PAYLOAD literals without explicit synthetic origin; fixture origin requ… |
| `implementation/tools/app_nav_ia_browser_test.js` | 20,254 | 코드, 합성 검증 | Navigation test and empty device state; source code itself no acquired payload. | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/app_nav_ia_browser_test.js:1 |
| `implementation/tools/audit_candidate_hygiene.py` | 3,462 | 코드, 계약 | SEC/listing issuer identity evidence. | Candidate hygiene full report/CLI stdout is eligibility/listing evidence; no acquired price pa… | NO | 유지 가능 | implementation/tools/audit_candidate_hygiene.py:74-77 |
| `implementation/tools/audit_mcap_store.py` | 35,768 | 코드, 공개 출력 경로(소스/설정) | Raw-store price/share values. | Full mcap audit report to output and complete audit JSON to stdout; utility called by gate pat… | NO | 정리 필요 | implementation/tools/audit_mcap_store.py:587-630 |
| `implementation/tools/autonomy_gate_a_guard.py` | 36,067 | 코드, 계약 | Repository policy/workflow/diff metadata. | Read-only diff/mode/guard receipts; no collector or price payload sink. | NO | 유지 가능 | implementation/tools/autonomy_gate_a_guard.py:798-827 |
| `implementation/tools/bench_universe_500.py` | 6,708 | 코드, 계약 | Synthetic benchmark fixture price bars. | Timing, lookahead violation counts and synthetic replay report; source benchmark numerics not … | NO | 유지 가능 | implementation/tools/bench_universe_500.py:105-155 |
| `implementation/tools/build_pages_cockpit.py` | 1,362 | 코드, 공개 출력 경로(소스/설정) | repository_bundle real FrozenUniverse. | Removes only cutoff_mcap and member mcap; explicitly retains ranks, company market_cap_rank an… | CONDITIONAL | 정리 필요 | implementation/tools/build_pages_cockpit.py:16-23 |
| `implementation/tools/build_web_mvp_demo.py` | 2,698 | 코드, 합성 검증, 공개 출력 경로(소스/설정) | Mixed provenance: synthetic test vector sections and real repository Frozen base; de… | Demo pipeline consumes Frozen base plus mixed LIVE_FETCH holdings, then builds verbatim data.j… | CONDITIONAL | 정리 필요 | implementation/tools/build_web_mvp_demo.py:24-43 |
| `implementation/tools/build_web_research_guard_fixture.py` | 9,222 | 코드, 합성 검증, 공개 출력 경로(소스/설정) | Mixed provenance: synthetic test vector sections and real repository Frozen base; de… | Literal added numeric probes are synthetic; actual Frozen base survives unchanged into served … | CONDITIONAL | 정리 필요 | implementation/tools/build_web_research_guard_fixture.py:70-96 |
| `implementation/tools/build_web_state_presentation_fixture.py` | 17,885 | 코드, 합성 검증, 공개 출력 경로(소스/설정) | Mixed provenance: synthetic test vector sections and real repository Frozen base; de… | Literal added probes are synthetic; FrozenUniverseProducer preserves actual Frozen values, com… | CONDITIONAL | 정리 필요 | implementation/tools/build_web_state_presentation_fixture.py:58-68 |
| `implementation/tools/ca_unit_policy.py` | 10,898 | 코드, 계약 | CA primary evidence and upstream price/share basis. | Offline corporate-action interpretation before market-cap ranking; no independent CLI/file/std… | NO | 유지 가능 | implementation/tools/ca_unit_policy.py:59-175 |
| `implementation/tools/derive_dated_evidence.py` | 3,681 | 코드, 계약 | Earlier-as-of symbol mappings/class-rights citations. | Filters primary citations and copies class economics/symbol evidence into gate file; identity/… | NO | 유지 가능 | implementation/tools/derive_dated_evidence.py:28-73 |
| `implementation/tools/device_actual_browser_test.js` | 32,964 | 코드, 합성 검증 | Synthetic in-memory device probes; explicit no screenshot/download/payload log contr… | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/device_actual_browser_test.js:1-2 |
| `implementation/tools/device_actual_node_test.js` | 9,536 | 코드, 합성 검증 | Local synthetic device holdings proof. | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/device_actual_node_test.js:1 |
| `implementation/tools/device_market_node_test.js` | 19,535 | 코드, 합성 검증 | Local synthetic quotes/FX and validation/valuation proof. | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/device_market_node_test.js:1 |
| `implementation/tools/export_web_bundle.py` | 2,982 | 코드, 공개 출력 경로(소스/설정) | FrozenUniverseProducer plus optional validated input snapshots. | Assembler preserves usable producer data and optional --build-web writes full unredacted bundl… | CONDITIONAL | 정리 필요 | implementation/tools/export_web_bundle.py:28-53 |
| `implementation/tools/fetch_class_rights_evidence.py` | 9,438 | 코드, 계약 | SEC filing primary documents, class economics evidence. | Stores SEC document passages and reports rights/citation counts; class missing price used to c… | NO | 유지 가능 | implementation/tools/fetch_class_rights_evidence.py:159-185 |
| `implementation/tools/fetch_corporate_action_evidence.py` | 2,630 | 코드, 계약 | Policy-referenced SEC/issuer primary documents. | Fetches primary evidence through raw store, not market-price endpoint; stdout status/document … | NO | 유지 가능 | implementation/tools/fetch_corporate_action_evidence.py:24-59 |
| `implementation/tools/fetch_cover_xbrl.py` | 8,502 | 코드, 공개 출력 경로(소스/설정) | SEC cover XBRL and extra Yahoo class-symbol charts. | Stores raw reports and class-price chart inputs under c21 raw-store; summary stdout excludes l… | NO | 정리 필요 | implementation/tools/fetch_cover_xbrl.py:6-155 |
| `implementation/tools/fetch_ishares_reference.py` | 9,484 | 코드, raw-response provenance unconfirmed | iShares IWB raw holdings CSV and SEC lookup. | Retains whole raw response and response_head on rejection into default repository raw store/re… | NO | 판단 보류 | implementation/tools/fetch_ishares_reference.py:59-171 |
| `implementation/tools/fetch_krx_data.py` | 4,127 | 코드, 공개 출력 경로(소스/설정) | Potential KRX authenticated acquired daily/basic response; no key presence or values… | Raw-store persistence; stdout report uses artifact IDs/status/bytes/counts, not acquired row v… | NO | 정리 필요 | implementation/tools/fetch_krx_data.py:38-71 |
| `implementation/tools/fetch_nport_reference.py` | 35,921 | 코드, 공개 출력 경로(소스/설정) | SEC N-PORT/listings and extra Yahoo chart/reference collection. | Writes reference/gate and raw ingest reports; c21 archive collects root. Mapping method rank i… | NO | 정리 필요 | implementation/tools/fetch_nport_reference.py:562-619 |
| `implementation/tools/fetch_real_data.py` | 12,438 | 코드, 공개 출력 경로(소스/설정) | Yahoo chart/splits plus SEC public financial bytes. | RawDatasetStore and ingest_run report under raw root; used by c21 raw cache/upload. | NO | 정리 필요 | implementation/tools/fetch_real_data.py:109-135 raw store.put and status-only log fields; error reason for egress denial only |
| `implementation/tools/fetch_share_scale_docs.py` | 5,541 | 코드, 계약 | SEC companyfacts/share scale and cover-page docs. | Shares/unit ratio diagnostics choose SEC document retrieval; normal stdout flagged ratios/iden… | NO | 유지 가능 | implementation/tools/fetch_share_scale_docs.py:38-102 |
| `implementation/tools/fetch_sp500_intervals.py` | 4,347 | 코드, 계약 | Public membership history and optional SEC submissions. | Writes resolved roster/ingest report and stdout membership status; reference composition is no… | NO | 유지 가능 | implementation/tools/fetch_sp500_intervals.py:64-99 |
| `implementation/tools/fetch_stooq_prices.py` | 9,146 | 코드, 공개 출력 경로(소스/설정) | Stooq acquired CSV daily prices and Yahoo calibration closes. | Persists calibration with closes; non-CSV response head may be retained; CLI prints report exc… | NO | 정리 필요 | implementation/tools/fetch_stooq_prices.py:113-176 |
| `implementation/tools/fetch_tiingo_prices.py` | 14,055 | 코드, 공개 출력 경로(소스/설정) | Tiingo acquired daily prices and Yahoo calibration closes. | Persists raw report including calibration closes and prints report without log; c21 pipes firs… | NO | 정리 필요 | implementation/tools/fetch_tiingo_prices.py:147-267 |
| `implementation/tools/global_language_search_browser_test.js` | 10,325 | 코드, 합성 검증 | Presentation test adds explicit synthetic numeric sections; inherited Frozen base re… | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/global_language_search_browser_test.js:51-54 |
| `implementation/tools/global_language_search_test.js` | 5,128 | 코드, 합성 검증 | Local lexical query relevance rank/locale test; rank is not price rank. | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/global_language_search_test.js:40 |
| `implementation/tools/google_sheet_auth_node_test.js` | 23,982 | 코드, 합성 검증 | Locally mocked login/access-token/Sheet replies; test strings are synthetic. | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/google_sheet_auth_node_test.js:1 |
| `implementation/tools/google_sheet_core_node_test.js` | 13,804 | 코드, 합성 검증 | Locally constructed quote/FX parse values; synthetic proof. | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/google_sheet_core_node_test.js:1 |
| `implementation/tools/google_sheet_quotes_browser_test.js` | 24,580 | 코드, 합성 검증 | Mocked Sheet/auth responses and device state; synthetic proof. | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/google_sheet_quotes_browser_test.js:1 |
| `implementation/tools/google_sheet_storage_browser_test.js` | 6,308 | 코드, 합성 검증 | Mock device storage cases; no acquired provider data. | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/google_sheet_storage_browser_test.js:1 |
| `implementation/tools/import_bulk_real_data.py` | 10,163 | 코드, 공개 출력 경로(소스/설정) | Stooq real daily bulk chart bytes and SEC companyfacts bulk. | Default repository raw-store persists raw closes; stdout import counters/status rather than ra… | NO | 정리 필요 | implementation/tools/import_bulk_real_data.py:125-220 |
| `implementation/tools/live_smoke.py` | 2,210 | 코드, 공개 출력 경로(소스/설정) | Yahoo live price and mixed synthetic/live SEC analysis. | Writes ROOT/reports live smoke plus complete acquired-price report to stdout; not a current wo… | NO | 정리 필요 | implementation/tools/live_smoke.py:29-65 |
| `implementation/tools/manual_quotes_browser_test.js` | 37,911 | 코드, 합성 검증 | Locally constructed synthetic manual quote/backup probes; captures fresh empty devic… | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/manual_quotes_browser_test.js:357-370 |
| `implementation/tools/mini_pytest.py` | 4,765 | 코드, 계약 | Test modules and synthetic/default corpus, no provider acquisition itself. | Failure tracebacks/assert repr can enter stdout if tests fail; no actual failure log inspected. | NO | 유지 가능 | implementation/tools/mini_pytest.py:118-143 |
| `implementation/tools/nport_cross_check.py` | 9,145 | 코드, 공개 출력 경로(소스/설정) | N-PORT per-share vs stored market close. | Persists calibration nport per-share/market close; stdout derived summary. Used by c21 gate ev… | NO | 정리 필요 | implementation/tools/nport_cross_check.py:74-157 |
| `implementation/tools/nport_reported_prices.py` | 11,998 | 코드, 공개 출력 경로(소스/설정) | SEC N-PORT holdings values/quantity to reported value per share. | Report contains reported_value_per_share and raw holdings; writes public-tree gate report and … | NO | 정리 필요 | implementation/tools/nport_reported_prices.py:144-217 |
| `implementation/tools/official_pipeline.py` | 11,682 | 코드, 공개 출력 경로(소스/설정) | Gate-verified real price/share basis and vertical slice. | Official Frozen snapshot writes rank,mcap,price basis/clock/cutoff; CLI writes report and emit… | NO | 정리 필요 | implementation/tools/official_pipeline.py:137-193 |
| `implementation/tools/pages_artifact_guard.py` | 17,616 | 코드, 계약, 공개 출력 경로(소스/설정) | Exact approved public asset/JSON hashes for mcap-only-stripped Frozen bundle. | Strict directory/tar allowlist rejects unapproved changed bytes and populated sensitive price/… | NO | 정리 필요 | implementation/tools/pages_artifact_guard.py:3-12 scope |
| `implementation/tools/pages_cockpit_browser_test.js` | 11,374 | 코드, 합성 검증 | Guarded default Pages source; empty ACTUAL device screenshots. | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/pages_cockpit_browser_test.js:113-137 |
| `implementation/tools/prepare_ca_unit_evidence.py` | 2,913 | 코드, 공개 출력 경로(소스/설정) | Pinned real Yahoo historical identity repair chart and primary CA docs. | Verifies retained real closes unchanged and installs normalized chart in default repository ra… | NO | 정리 필요 | implementation/tools/prepare_ca_unit_evidence.py:27-57 |
| `implementation/tools/private_history_browser_test.js` | 26,617 | 코드, 계약, 합성 검증 | Synthetic future-date history, synthetic access credential, mocked Worker origin and… | Specify OFF/explicit-fetch, storage/export/log redaction and cancellation checks against brows… | NO | 유지 가능 | implementation/tools/private_history_browser_test.js:1 and :5-29 synthetic fixture/canaries |
| `implementation/tools/private_history_contract_test.mjs` | 4,678 | 코드, 계약, 합성 검증 | Synthetic app-to-Worker integration harness with local bars and synthetic identity/t… | Connect actual browser-session/Worker/validator code entirely through mocked fetch; assert aut… | NO | 유지 가능 | implementation/tools/private_history_contract_test.mjs:1 synthetic declaration and :6 live fetch disabled |
| `implementation/tools/private_history_node_test.js` | 6,014 | 코드, 계약, 합성 검증 | Constructed future-date daily-history fixture and synthetic origin; not recorded pro… | Assert browser payload allowlist, identity/currency/basis/null semantics and raw-close geometr… | NO | 유지 가능 | implementation/tools/private_history_node_test.js:1 synthetic-only declaration |
| `implementation/tools/producer_engine_fingerprint.py` | 2,250 | 코드, 계약 | Official/synthetic code fixture QGV/technical/macro/portfolio results. | Stdout contains hashes and count only; value-derived output digest is an integrity fingerprint… | NO | 유지 가능 | implementation/tools/producer_engine_fingerprint.py:33-45 |
| `implementation/tools/prompt_field_guide_browser_test.js` | 29,588 | 코드, 합성 검증 | Synthetic producer context/prompt eligibility checks, no runtime provider acquisitio… | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/prompt_field_guide_browser_test.js:1 |
| `implementation/tools/prompt_library.py` | 4,778 | 코드, 계약 | Prompt catalog and explicitly supplied variable text. | Template/export CLI prints supplied prompt content; no collector/producer price path in this f… | NO | 유지 가능 | implementation/tools/prompt_library.py:67-94 |
| `implementation/tools/qgv_contract_audit.py` | 8,612 | 코드, 계약 | Static contract spec and case fixtures. | Validates contract fixture shape/proofs and runtime-disabled spec; stdout pass/failure metadat… | NO | 유지 가능 | implementation/tools/qgv_contract_audit.py:101-166 |
| `implementation/tools/raw_artifact_restore_check.py` | 5,228 | 코드, 계약 | Restored artifact bytes, not provider network. | Normally outputs hashes/counts/replay sample counts, not bars. Exception error-string diagnost… | NO | 유지 가능 | implementation/tools/raw_artifact_restore_check.py:50-96 |
| `implementation/tools/raw_persistence_audit.py` | 2,615 | 코드, 계약 | Raw manifests/hashes. | CLI reports integrity binding/counts/bytes; no acquired prices printed by observed code. | NO | 유지 가능 | implementation/tools/raw_persistence_audit.py:40-48 |
| `implementation/tools/reconstruct_sp500_from_wikipedia.py` | 4,985 | 코드, 계약 | Cached/public membership change documents. | Writes historical candidate membership reference; stdout excludes members and reports counts/m… | NO | 유지 가능 | implementation/tools/reconstruct_sp500_from_wikipedia.py:72-105 |
| `implementation/tools/rig_browser_smoke.js` | 6,037 | 코드, 합성 검증 | Static Track D fixture browser proof; no price acquisition in source. | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/rig_browser_smoke.js:91 |
| `implementation/tools/run_pipeline.py` | 3,154 | 코드, 계약 | Supplied corpus/cross-section inputs. | Writes output report with optional upstream actual data; stdout output path only. Not in curre… | NO | 유지 가능 | implementation/tools/run_pipeline.py:76-78 |
| `implementation/tools/run_top500_gate_chain.py` | 93,104 | 코드, 공개 출력 경로(소스/설정) | Raw-store price/share basis to market capitalization, ranks and gate/walk-forward re… | Full report writes --out in gate evidence; stdout explicitly includes cutoff_500_mcap. | NO | 정리 필요 | implementation/tools/run_top500_gate_chain.py:1208-1442 |
| `implementation/tools/sec_m1_inputs.py` | 6,370 | 코드, 계약 | SEC companyfacts/submissions raw financial data. | Live/offline SEC financial-only receipt pipeline; explicit no price/scoring/Pages path. CLI re… | NO | 유지 가능 | implementation/tools/sec_m1_inputs.py:1-134 |
| `implementation/tools/sec_m2_qg.py` | 5,427 | 코드, 계약 | SEC financial M1 receipts into Q/G candidate. | Public financial-only Q/G processing; safe error codes and calculated/unavailable status summa… | NO | 유지 가능 | implementation/tools/sec_m2_qg.py:106-122 |
| `implementation/tools/share_count_diagnostic.py` | 13,964 | 코드, 계약 | SEC cover share-count diagnostic. | Persists/prints share evidence, no market-price acquisition asserted. c21 report upload can in… | NO | 유지 가능 | implementation/tools/share_count_diagnostic.py:253-254 |
| `implementation/tools/web_mvp_browser_test.js` | 9,547 | 코드, 합성 검증 | Mixed-source demo under current fixture build; screenshots home/portfolio/NVDA/news/… | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/web_mvp_browser_test.js:213-239 |
| `implementation/tools/web_research_guard_browser_test.js` | 19,315 | 코드, 합성 검증 | Synthetic withholding probes plus actual Frozen base; screenshots and evidence repor… | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/web_research_guard_browser_test.js:36 |
| `implementation/tools/web_state_presentation_browser_test.js` | 35,046 | 코드, 합성 검증 | Synthetic state/expiry probes, but fixture inherits actual Frozen base; complete bun… | Static test/export-observer program; result files/screenshots are distinct sinks with provenan… | NO | 유지 가능 | implementation/tools/web_state_presentation_browser_test.js:473-482 |
| `implementation/worker/src/index.js` | 17,381 | 코드, 계약 | Inactive-in-public-app Worker transport source; runtime upstream roles are Google to… | Validate fixed Origin, owner Google identity, symbol/range; normalize daily history; return au… | NO | 유지 가능 | implementation/worker/src/index.js:2-15 fixed upstream constants and no-cache options |
| `implementation/worker/tests/worker.test.mjs` | 29,759 | 코드, 계약, 합성 검증 | Locally constructed mocked daily-history bars, mock tokeninfo identity and synthetic… | Mock validation, rejection/redaction, limits, normalization, upstream cache flags and numeric-… | NO | 유지 가능 | implementation/worker/tests/worker.test.mjs:5 global live fetch disabled |

### 7.3 공통 사용 경로·판정 근거

모든 아래 링크는 감사 기준 SHA에 고정한다. 코드·설정의 정적 경로와 source 파일에 저장된 DATA를 근거로 하며 실행 PASS·실배포 포함·과거 로그 유출은 주장하지 않는다.

**현재 Pages의 Frozen 순위 경로**

`official_snapshot_2024-12-31.json` → `FrozenUniverseProducer / repository_bundle` → `build_pages_cockpit` → `data.json / app.js` → workflow의 Pages output upload.

- [Frozen producer](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/src/investment_system/producers/registry.py#L65-L88): Frozen source와 manifest를 읽고 synthetic=False로 공급한다.
- [repository_bundle](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/src/investment_system/product/web_mvp.py#L72-L90): hash를 확인한 원 universe와 company market_cap_rank를 만든다. 다른 기본 8개 section은 NOT_AVAILABLE이며 현재 기본 Pages에 V/수익률 전체가 이미 제공된다는 뜻은 아니다.
- [공개 projection](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/tools/build_pages_cockpit.py#L12-L23): cutoff_mcap/member.mcap만 제외하며 membership/ranks 보존 의도가 남아 있다.
- [정적 파일 생성](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/src/investment_system/product/web_mvp.py#L111-L136): 정해진 web_assets와 bundle을 output에 쓴다. docs/reports/raw/experiments를 통째로 복사하지 않는다.
- [화면 소비](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/src/investment_system/product/web_assets/app.js#L305-L321): raw evidence/market_cap_rank 및 공급된 경우의 QGV 지표를 표시한다. 기본 NOT_AVAILABLE section과 분리한다.
- [Pages upload](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/.github/workflows/cockpit-pages.yml#L87-L129): 제한된 site output을 artifact로 업로드·검사·배포한다. 별도 browser evidence artifact는 이 site tar guard와 구분한다.

**guard·generic export·혼합 demo·Actions fixture**

- [artifact guard 범위와 sensitive keys](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/tools/pages_artifact_guard.py#L3-L63): exact allowlist/hash와 price/mcap/holdings/token 등을 검사한다. rank·가격 기반 수익률/V/QGV의 모든 의미적 경우를 검증하는 전역 detector는 아니다. 승인되지 않은 임의 renamed payload가 반드시 통과한다는 뜻도 아니다. 승인된 baseline의 rank와 hash mismatch 차단 기능을 구분한다.
- [generic export](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/tools/export_web_bundle.py#L39-L50): producer 결과를 assembler/선택형 web build로 전달한다. schema·freshness·hash 검증은 별도의 공개 가격 projection이 아니다.
- [mixed demo input](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/src/investment_system/product/web_mvp.py#L93-L103): `official_v11_book_snapshots.json`의 명시된 synthetic QGV와 `us_session_mixed_2026-09-23.json`의 LIVE_FETCH holding 가격을 서로 구분해야 한다. 후자를 DEMO portfolio로 감싸도 원 가격은 합성이 되지 않는다.
- [web MVP validation workflow](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/.github/workflows/web-mvp-validation.yml#L30-L43): temporary 기본/demo build와 browser evidence 업로드를 구성한다. 정상 screenshot에 실제 가격이 보였는지는 이 감사에서 확인하지 않았다.
- [research fixture의 완전 variant 저장](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/tools/build_web_research_guard_fixture.py#L134-L143)과 [업로드](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/.github/workflows/web-research-guard.yml#L29-L44): 합성 probe를 추가해도 base의 실제 Frozen 가격 파생값이 자동으로 합성이 되지 않는다.
- [state fixture의 완전 variant 저장](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/tools/build_web_state_presentation_fixture.py#L259-L272)과 [업로드](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/.github/workflows/web-state-presentation.yml#L29-L46): fixture의 `TEST VECTORS/NOT_REAL_DATA` 문구와 상속된 actual Frozen source의 기원을 분리한다.

**raw cache·artifact·repository commit·stdout**

- [수동 c21 runner](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/.github/workflows/c21-real-data.yml#L9-L38)은 workflow_dispatch이다. 이번에 실행하거나 자동 schedule이라고 판정하지 않았다.
- [cache/seed restore](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/.github/workflows/c21-real-data.yml#L66-L86)와 [cache save·보고서·raw/gate 업로드·metadata commit](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/.github/workflows/c21-real-data.yml#L213-L251): 현재 tree에 없는 raw 가격 blob이 복원/취득되면 이 경로에 들어갈 수 있다. 현재 manifest의 가격 부재와 artifact payload의 가격 부재는 서로 다른 사실이다.
- [Tiingo calibration 저장](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/tools/fetch_tiingo_prices.py#L138-L149)·[report 저장](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/tools/fetch_tiingo_prices.py#L219-L225)·[stdout](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/tools/fetch_tiingo_prices.py#L258-L269): `log` 제외 후에도 종가 calibration이 포함될 수 있는 report 경로다.
- [Stooq calibration/response fragment](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/tools/fetch_stooq_prices.py#L109-L144)·[stdout](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/tools/fetch_stooq_prices.py#L165-L179), [c21 collector stdout](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/.github/workflows/c21-real-data.yml#L160-L174): head로 일부를 표시하는 구성은 가격 파생 필드가 없는 요약을 보장하지 않는다. 실제 실행 로그는 조회하지 않았다.
- [gate cutoff_mcap stdout](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/tools/run_top500_gate_chain.py#L1438-L1442), [official snapshot 계산](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/tools/official_pipeline.py#L137-L152), [historical price outcome](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/src/investment_system/validation/historical.py#L39-L69), [ablation price return](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/src/investment_system/validation/ablation.py#L13-L23): 실제 가격→시총/순위/성과 파생 관계의 근거다. 실제 값은 문서에 재기재하지 않았다.
- [iShares raw/response-head](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/tools/fetch_ishares_reference.py#L148-L171): 현재 대응 raw blob이 없어 원응답 가격/시장가치 column을 확인하지 못했다. 성공한 identity-only projection과 전체 raw body는 구분하고 판단 보류한다.

**합성·공개 재무·고정 TARGET 및 개인 Worker**

manifest의 URL/hash/크기/상태, SEC share facts·par value·split/exchange ratio·배당/매출 등 공개 재무 사실은 주가/시총 값과 다르다. PRICE·PRICELINE 회사명, 함수의 return, 테스트 개수·화면 너비·필드 정의·임계값도 실제 주가가 아니다. 원문에 실제 주당 가격/시장평가액이 있는 SCCO/NPORT 등은 이 예외에 포함하지 않는다.

`official_v11_*`의 명시적 synthetic_all/kind와 deterministic mock/golden 생성 근거, 사용자 원문의 고정 TARGET을 유지 근거로 읽었다. [TARGET 원문](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/docs/portfolio_target_owner/TARGET_v0.yaml#L3-L22) 및 [그대로 읽는 consumer](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/experiments/chart-contract-v0.1/target_v0_source.mjs#L113-L159)는 실제 시세로 새로 계산한 비중이나 price-based QGV를 제공한다는 근거가 아니다. 원래 합성 지표/fixture라도 실제 source를 섞는 경로는 따로 정리 대상으로 분류했다.

[Worker 개인 응답/인증](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/worker/src/index.js#L228-L250)은 owner tokeninfo 확인과 private/no-store 응답 경로다. [저장하는 rate metadata](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/worker/src/index.js#L267-L323)는 가격/토큰 body와 구분한다. [source config](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/worker/wrangler.toml#L1-L19)의 observability off와 앱의 [OFF 설정](https://github.com/kco994553-star/Investment-System1/blob/3877f9a1eab3d511a58bcb7c49c1a833965737d3/implementation/src/investment_system/product/web_assets/app-config.js#L1-L6)은 확인했으나 실제 배포 플랫폼 상태나 실제 공급자 호출 성공을 재검증하지 않았다. 공개 asset으로 배포되는 값 없는 코드와 본인만 받는 runtime 가격을 같은 것으로 분류하지 않는다.


## 8. 판정의 한계

이는 특정 canonical tree의 가격 경계 감사이며 이후 커밋·다른 branch·배포 runtime·공급자의 실응답·Git 전체 과거 이력·모든 Actions 산출물의 전수 검증이 아니다. 미추적 파일과 manifest가 가리키는 미보존 원문은 별도 범위다. 현재 tree에서 원문 blob이 없다는 사실은 과거 cache/artifact/clone에 가격이 없다는 증거가 아니다.

정적 Pages 포함 경로, 저장된 DATA, 향후 실행 가능한 ROUTE를 분리한 판정이다. 가격 값이 없는 metadata·코드·공개 재무 사실에 대한 유지 가능 판정을 외부 raw payload 또는 새 실행의 게시 허가로 확대하지 않는다. 실제 정리·공개 경계의 회귀 검증·운영 활성화는 사용자 결정 후 별도 작업이다.
