# Top500 전환 · 공개 목록 · 낡은 시트 검토

2026-11-14 오너 통합 최종본에 따른 연구 인계다. 새 선정기·가격 엔진·운영 서비스는
만들지 않는다. **교체 목표이나 아직 전환 전, 현재 공식은 Universe504**다.
Main 정본 제안 #539 `633740674176aaf7fbbcc4f2b9ff12fc512d1e01`은 문서 PR이며
병합된 canonical로 표시하지 않는다. 이 문서는 DC·결정 원문을 대신하지 않는다.

## 단계와 미정 사항

| 단계 | 확인된 상태 |
| --- | --- |
| 구현 | 기존 `top500_selection.select_top500`·`universe.sources.mcap_top_n_snapshot` 사용 |
| 합성 검증 | 기존 선정 시험/고정 fixture 재사용. 이번에는 목록 투영·시트 비교의 새 경계만 검증 |
| 실자료500 선정 | 미실행. 보유1057·관측8004를 전체 후보나 확정 Top500으로 승격하지 않음 |
| 전환 검증 | 실제 신/구 구성원·평가/참조/관문 입력이 없어 미측정 |
| 공식 전환·적용일 | 전환 전 / 적용일 미정. 기존 공식 Universe504 유지 |

| 항목 | 기존 구현·근거 | 권장안 / 남은 결정·입력 |
| --- | --- | --- |
| 시장·종류 | selector는 policy.markets/included_kinds 검사. 기존 확장 정의는 주요거래소·ADR 포함 | 연구 예시의 NYSE/NASDAQ/NYSE_AMERICAN/BATS, COMMON/ADR/FOREIGN_COMMON/REIT를 운영 확정값으로 부르지 않음. LP/BDC 포함은 기존 확장안에 있으나 새 Top500 승계·SPAC/셸 경계는 명시 필요 |
| 종류주 합산 | 발행사별 classes_complete·economic_class_id·security_id 중복 검사와 종류별 시총 합산 | 적격 전체 종류 목록·실제 주식수·가격 근거 필요. 확보된 한 종류만으로 발행사 전체를 확정하지 않음 |
| ADR | 기존 포함 결정 유지. 실제 원주 종류 주식수×ADR가격÷원주/receipt 비율 | 동일 경제적 종류와 원주/ADR 연결·비율·통화·유효기간 필요. 이중 집계 금지 |
| 주식수 | ACTUAL_CLASS_OUTSTANDING 또는 실제 원주 종류 주식수만 허용 | EPS용 WAD는 Top500 실제 주식수로 사용하지 않음. 중앙/개인V의 WAD 변형과 구분 |
| 가격·시총 | 동일 증권·평가일·RAW_CLOSE·통화/FX·가용시각 검사 | 공급처별 가격 정의를 고정. IEX 마지막 체결가를 RAW_CLOSE/통합 종가로 재명명하지 않음. Google marketcap·PublicFloat 대체 금지 |
| 대표 증권 | 입력 대표가 종류 목록에 있고 근거가 있어야 함 | 기존 확장안의 유동성 기반 대표 선택을 근거와 함께 검토하되 자료가 있는 종류를 자동 대표로 택하지 않음. 선택 규칙·거래량 범위 확정 필요 |
| 후보 범위 | COMPLETE와 기대 발행사 명부/전달 행 집합 대사 | 이는 명부 내부 대사다. 원천의 평가일 상장 포괄성·누락 기업·500위 경계 불확실성 근거는 별도로 필요 |
| 선정·적용 | evaluation_day/input_cutoff/apply_at 보존, 적용이 cutoff보다 빠르면 거부 | 선정일과 실제 적용일을 분리. 다음 정규장 적용은 권장안이며 기존 함수가 이를 강제하지는 않음 |
| 주기 | 연구 예시는 DAILY_CLOSE. 자동 재선정 스케줄은 없음 | 권장 초안: 매 거래일 진단 순위, 다음 정규장에 검증된 선정본 적용. 실제 교체 주기는 운영 결정 필요. 월간이면 해당 선정일 Top500으로 표시 |
| 완충·하한 | 완충과 확장안 주가/유동성/시총 하한을 넣지 않았음 | 초기 exact Top500 비교는 완충 없이 보존. 완충을 채택하면 매 시점 정확한 상위500과 달라짐을 별도 버전/명칭으로 표시 |
| 실패·이전본 | selector는 previous를 retained_confirmed로 복사 | 그 자체가 정상·공식확정 검증은 아님. Main이 독립 hash로 검증된 이전 확정본을 선택·원자 보존. 조회 실패와 실제 부재 구분 |

이미 구현된 조건을 다시 설계하거나 이미 승인된 ADR을 다시 승인 대기로 두지 않는다.
나머지 운영 세부값은 위 권장안·영향을 묶어 결정한다. 실제 대상 수와 비용은 입력 없으면
미측정이며 유리한 커버리지를 보고 정책을 선택하지 않는다. 새 취득·계약·권한·공식 전환은
이 연구 인계로 실행하지 않는다.

## 공개 목록은 기존 파일 + 별도 메타데이터

현재 `universe/universe_codes.py::public_payload()`는 정확히
`{schema:"universe-codes/1",codes:[...]}`를 만든다. 기존 검증기와 Main 판독기는
두 키·원순서·원목록 동일성을 요구한다. 이 파일과 producer를 수정하지 않는다.

`research.population_public_listing.build_listing`은 기존 공개 코드 payload 또는
이미 저장된 Top500 선정 결과의 **바이트**를 읽는 allowlist 투영이다. 새 선정을 하지 않는다.
source SHA256과 mapping input digest는 신뢰된 caller가 독립 인계/manifest에서 공급해야 한다.
같은 요청 본문에서 해시를 계산해 주는 것만으로 독립 검증했다고 하지 않는다.

| 입력 | 의미 |
| --- | --- |
| source_kind=CURRENT_OFFICIAL | 현행 Universe504와 기존 require_universe_codes를 정확히 대사. 원본 코드 행 보존 |
| source_kind=TOP500_RESEARCH_CANDIDATE | 기존 top500_view의 원결과 hash 검사 재사용. 발행사→대표 증권→코드 연결이 완결되지 않으면 새 목록 출력 거부 |
| source_kind=SYNTHETIC_CURRENT | 개발 fixture 전용. CONFIRMED여도 실제 공식 목록이 아니고 새 사용자 시트 대상이 아님 |
| metadata | 모집단 ID/버전, basis_date, apply_at, mapping_day, input_cutoff. 모르는 값은 null+허용 사유. 파일명v1·Git시각·현재시각을 선정/적용일로 쓰지 않음 |
| links | 기존 안정된 코드 행·발행사·증권·종류주·대표·Google 대응의 검토 기록. claim별 상태/근거와 valid_from inclusive/valid_to exclusive·available_at 필요 |

출력 `population-public-list/1`:

- population_id/population_version, basis_date(선정 또는 명부 기준일), apply_at,
  mapping_day(대응 적용 판정 기준일; 검토·취득 시각 아님), input_cutoff 및 null_reasons.
- code_rows와 issuers/known_issuers를 분리. 발행사 연결 누락이면 issuers=null이며
  코드를 삭제하거나 누락 행을 새 발행사로 세지 않는다.
- members는 company_id=현재 코드 행 ID, code, issuer_id, security_id,
  representative_security_id 및 각 상태를 분리한다. 티커·CIK를 증권ID로 만들지 않는다.
- requested_google_symbol은 원코드 그대로인 **조회 요청 기호**다. google_symbol은
  별도 검토한 대응만 채운다. 요청 기호의 문법 적합·숫자 응답·정적 target 표는 전수
  증권/종류주/Google 대응 검증 완료가 아니다. 내부 `sec:CIK:symbol` seed도 승계하지 않는다.
- mapping_record_id·기간·입력 hash만 표시하며 근거본문·비공개 경로·가격·시총·주식수는 내보내지 않는다.
- status=CONFIRMED/CANDIDATE, official_current, use_for_new_sheet를 별도로 읽는다.
  Top500 연구 후보는 CANDIDATE/false/false이며 공식 목록으로 자동 승격되지 않는다.
- 새 sidecar 자체는 `public_publication_authorized=false`인 게시 제안이다. Top500 원결과의
  AUTHENTICATED_RESEARCH 범위를 보존한다. schema 명칭이 공개 승인이나 새 파일 배포를 뜻하지 않는다.

현재 원 공개 코드 파일에는 명시 모집단 버전·선정일·적용일·발행사 수·전수 증권/Google
검증 근거가 없다. 원문에 없는 값을 채우지 않는다. 원본 bytes/member hash는 고정할 수 있으나
원 승인 버전·시점의 대체가 아니다. 504코드와 기존 연구의501발행사를 같은 단위로 바꾸지 않는다.
CURRENT_OFFICIAL의 Universe504 제약은 현재 활성 정의를 보호하는 전환 전 규칙이다.
정식 전환 승인 뒤에는 활성 정의·소스 pin을 승인된 Top500으로 갱신하고504는 과거 재현으로
남긴다. 두 공식 모집단을 영구히 유지하려는 규칙이 아니다.

### 해시 네 가지

| 필드 | 해시 대상 |
| --- | --- |
| source_sha256 | 전달받은 원 공개 payload/선정 결과의 정확한 bytes |
| source_result_hash | Top500 기존 원선정 결과의 저장된 semantic hash; legacy 코드 목록은 null |
| members_hash / ordered_codes_hash | 정렬 코드 행 ID 명부 / 원순서 코드 명부. 발행사 해시나 증권 해시가 아님 |
| list_hash | list_hash만 제외한 전체 sidecar. 메타데이터·매핑·상태까지 포함 |

기존 selector.members_hash에는 시총·가격/주식 근거도 들어간다. 공개 명부 해시로 재사용하지 않는다.
sidecar가 바뀌어도 과거 결과·사용자 설정의 원모집단/입력 hash를 덮어쓰지 않는다.

## 낡은 시트와 실패 응답

`sheet_difference(listing, sheet_codes, saved_identity, expected_listing_hash)`는 순수 비교다.
실제 셀·계좌·시트ID·가격은 받지 않으며 쓰기0이다. 추가/제외·순서·ID/버전/명부 hash
차이를 반환한다. 목록이 같아도 버전 미확인은 UNVERSIONED_LIST_MATCH이며 CURRENT로
승격하지 않는다. 차이가 있으면 REVIEW_REQUIRED다. Main은 사용자 선택 범위만 갱신하고
Trades·Quotes·사용자 열·기존 연결을 보호한다. 함수가 갱신을 실행하지 않는다.
계산할 때는 신뢰된 현재 평가/참조 명부를 사용한다. 낡은 시트의 바깥 코드는 명시적 진단으로
남기며 다른 종목으로 바꾸거나 현재 명부를 축소하지 않는다. #541 준비기에 명부 밖 가격을
그대로 넣으면 요청을 거부한다. 새 입력 검증과 과거 저장 결과 재현을 섞지 않는다.

`retain_listing(previous, expected_previous_hash, failure)`는 신뢰된 이전 CONFIRMED를
독립 hash로 확인하고 원 listing·원시점·원 hash를 그대로 둔 RETAINED_PREVIOUS 응답을 만든다.
후보를 이전 확정본으로 바꾸지 않는다. 저장·조회·원자 교체·정상본 부재/조회 실패 판정은 Main 담당이다.

Main은 기존 universe-codes.json을 읽는 경로를 유지하면서 메타데이터를 sidecar 또는 기존
공용 설정에 연결할 수 있다. 신규 파일이 필요하면192파일·고정값·CSP·서비스워커 영향과
기존 게시 승인 범위를 Main이 검증한다. 코드 목록을 화면별로 복사해 새 정본을 만들지 않는다.

원 공개 코드의 고정 근거는 [current-public-code-source.json](current-public-code-source.json)에
원파일 SHA/Git blob·명부/순서 hash로 연결했다. 이 파일의 public_payload_semantic_hash는
JSON 객체의 canonical digest이며 실제 배포 파일 bytes SHA가 아니다. 실제 배포본 hash는
미수령(null)이다. source_filename의v1도 원승인 모집단 버전으로 바꾸지 않는다. 새 메타데이터의
content 버전 등록은 Main과 맞추되 원선정일/적용일을 새로 꾸미지 않는다.

## 평가·참조·관문 전환 영향

| 비교 | 고정할 것 | 따로 낼 결과 |
| --- | --- | --- |
| 평가 대상만504→Top500 | 모형·설정·원지표·참조집단·관문 정책 | 신규/제외와 공통 발행사 점수·순위·분모 변화 |
| 참조집단만 변경 | 같은 평가 대상·모형·설정·원지표 | 공통 기업의 요소/역할/축/총점·유효N·rank 변화 |
| 평가+참조 동시 전환 | 위 두 비교와 입력 버전 연결 | 최종 전환 결과; 두 효과를 한 원인으로 합치지 않음 |
| 관문 범위 | 기존 공식 Q 정의·평가일·참조 규칙 | 입력 있음/판정 가능/통과/범위 밖. 연구Q 대체나 UNKNOWN 통과 없음 |

현재 실제 Top500 구성원과 적격 가격/실제 주식수 입력이 없어 이 비교는 **미측정(null)**이다.
공통 기업의 실제 점수 변화나 편입·편출 수0이라고 보고하지 않는다. 실제자료가 들어오면 기존
원지표와 엔진으로 영향받는 참조집단만 재점수화한다. 운영504코드/501발행사, 새500발행사,
보유1057, 관측8004 및 전체시장(null) 분모를 분리한다. Top500확정 시95%는475/500이며,
개인 시트 가격으로 이를 달성했다고 하지 않는다. 과거 선정·전진검증은 당시 명부·가용정보를 유지한다.

## Main 호출과 인수

계산 함수는 파일·네트워크·인증·시트 쓰기를 하지 않는다. source/mapping hash pin은 Main의
신뢰된 전달 경로에서 해석한다. JSON Schema와 producer가 만든 합성 입력/출력·manifest를
같은 PR에 인계한다. 기존 source가 올바른지, code row/issuer/security 단위가 같은지 확인하고
새 Main SHA가 오면 변경 소비 경계만 대조한다. 동일 점수·분위·완료 시험은 재실행하지 않는다.

오너의 Google 로그인·시트 생성/연결·속성 조회 확인은 사용자 실측이며,504개 V 계산·기호 전수
검증·브라우저555 인수 완료가 아니다. 실제 tradetime은 확인된 시트 timezone으로 해석한다.
datadelay=0을 조정 방식/동일 증권 검증으로 승격하지 않으며 marketcap은 계산에 사용하지 않는다.
가격 시각 없음·기호 불일치·부분 가격·평가/참조 버전 불일치는 #541 기존 사유를 유지한다.

Wire schema: [population-public-list-contract.json](population-public-list-contract.json).
공통 합성 사례는 `implementation/tests/fixtures/population-listing/{examples.json,manifest.json}`다.
확인된 가상 명부3코드/2발행사(1개 Google대응 미확인), 낡은 목록, 버전 없는 동일 목록,
실패한 갱신·이전본, 기존3발행사 Top500 후보 fixture의 투영을 포함한다. 정상·실패를 새 선정이나
실자료 커버리지로 표시하지 않는다. 기존 Top500 후보 파일은 재사용하고 선정기를 다시 실행하지 않았다.

```sh
PYTHONPATH=implementation/src python implementation/tools/generate_population_listing_examples.py --output <new-synthetic-directory>
```

생성기는 고정된 SYN 데이터만 받으며 실제 가격·개인 시트를 입력할 수 없다. 원자료 검증 hash와
목록/시트 진단의 새 반례만 시험한다. Main은 source bytes·mapping pin을 신뢰된 경로에서 분리해
확인하고 실제 소비한 계약/fixture SHA를 회신한다. 생산자 합성 통과·소비자 수락·브라우저·게시·
실사용은 각각 별도 상태다. 이번에는 실제 시총 Top500 선정·QGV 재계산·투자성과 검증을 하지 않았다.
