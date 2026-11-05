# 계층 4 매크로: 보관 시점 조회와 갱신 인계

기준 canonical `3887c79bbf427b0681b238901aafd2c951ef496e`, 2026-11-05. Codex는 새 연구 wrapper·시험·이 문서만 담당한다. Main의 UI·워크플로·기존 운영 엔진 파일은 수정하지 않는다.

## 확인한 구현 상태

| 범위 | 계산 구현 | 자료 연결·실제 검증 | 정기 갱신·화면 | 남은 결정 |
|---|---|---|---|---|
| Growth·Inflation v0 | `growth_inflation_v0.py`: BEA A191RL÷100, BLS NSA CPI YoY | 원기관 파서·수집·공개 산출물 연결 | 기존 `--macro-v0` 실행 경로 있음 | 8축 국면 대응 미채택 |
| 나머지 6축 | `raw_axes_v0.py`, `macro_remaining.py`; 승인 원값 변환 | Labor/Fed/FiscalData 경로, FX 공개 제외 | 기존 자료층·화면 연결 | 원값 표시와 국면 판단 분리 |
| 경고등 5개 | `macro_lights_v1.py`; 공개3·기기 시장/신용2 | 기존 공개 산출물과 private replay 경로 | 참고 표시 유지 | M-RULE C 가설, M-REENABLE 계속 보류 |
| P1 13개(14계열) 근거선 | `evidence_sources.py`·`evidence_lines.py` 파서/후보규칙/append-only first·revision | 기존 보관본 14계열 중11개 관측 있음; Census2 키 미설정, DOL1 권리 미확인 | #351·#352로 정기 경로·보존 연결, 새로 만들지 않음 | 후보 사건/해석은 v0 미검증; 공식국면·확률·게이트에 반영 안 함 |
| 4.1 링, 4.2·4.3 순환·SIC, 4.4 내판단, 4.5 나비효과, 4.6 트리 | 화면/구조와 사용자 기록 기존 구현 | 공식 위치·확률 산식 없음 | Main 소유 화면 | 모델 미확정 부분만 보류 |

새 구현은 기존 `macro-evidence/1` 보관본의 **관측 시점 조회**이다. baseline 이전 값을 현재 수정치로 채우지 않고, 각 월·분기 값은 기록된 가용시각 이후 유지한다. 기존 파서·후보규칙·지연 기준을 재사용한다. `SOURCE_LAST_MODIFIED`는 최초 발표 증거가 아니며, 개별 버전 수신시각이 없으면 해당 보관본의 생성시각을 보수적인 가용 상한으로 사용한다. `COLLECTION_TIME`과 `BASELINE`은 기록된 관측시각을 사용한다. 최초 실제 발표시각은 근거가 없으면 null이다.

## 구현 계획

1. `research/macro_observed_timeline.py`: strict 기존 검증기 → as-of 버전 선택 → 기존 후보규칙 재계산 → 기간/빈도/단위/수정/지연/값 유지 메타데이터. 과거 baseline 밖·권리 보류는 null.
2. `tools/macro_observed_timeline.py`: 로컬 보관본·UTC cutoff 목록 → Git 밖 0600 출력. 네트워크·운영 갱신 없음.
3. 합성: 발표 전/후, 수정 전/후, source-posting과 수신상한 분리, 월값 일간 유지, baseline 밖, stale, 권리보류와 CLI를 시험. 실제 보관본은 비공개 결과로 실행.

## 유지하는 결정

DC-42 담당, MEV-1/9/10, M-RULE C 가설과 M-GATE B/M-REENABLE, GSQ-011 FRED/ALFRED 보류, FX 공개 제외를 변경하지 않는다. 현재 수정치 자료로 과거 최초발표값을 만들지 않는다. 새 수집·키·계정·권한·워크플로 실행·병합·배포는 별도 승인이다.

## 공급처·계열·단위·갱신 대응표

원문 근거는 기존 [원기관 근거](../macro_data_rights/PRIMARY_AGENCY_EVIDENCE.md), [8축 정확한 계열](../macro_data_rights/MACRO_V0_SERIES_PROPOSAL.md), [P1 목록](../macro/MACRO_EVIDENCE_LINES_CATALOG_20261018.md)과 실행 코드 상수다. 아래 실행시각은 **권장 계획**이며 최초 실제 발표시각의 증거가 아니다. `America/New_York` 기준 DST를 적용한다. 공표가 늦으면 수집 성공시각으로만 가용 상한을 기록한다.

| 계열·지표 | 기존 endpoint/file와 단위·빈도·조정 | 최초 적재·증분 / 권장 시점 / 요청량 |
|---|---|---|
| Growth·E25 | BEA `https://apps.bea.gov/national/Release/TXT/NipaDataQ.txt`, A191RL; %, Q, SAAR | Q 파일1회 공유. GDP 발표일 08:30 ET 후30분 권고. 파일 해시 변경 때 전체 응답 비교(advance/second/third/annual revision 구분 근거 없으면 UNKNOWN). |
| Inflation | BLS `https://api.bls.gov/publicAPI/v1/timeseries/data/`, CUUR0000SA0; 1982–84=100, M, NSA | YoY에 최소13월, 기본 보유3년부터. 아래 Labor와1POST 공유. CPI 발표일08:30 ET 후30분. 최근2년 겹침 조회; 동일 응답 캐시. |
| Labor·E13 | 같은 BLS, LNS14000000; %, M, SA | 기존 Inflation POST 공유. Employment Situation 발표후30분. Sahm에는 최소15월; 누락월을 보간하지 않음. |
| E16·E17·E39 core CPI | BLS CES6056132001(천명), CES3000000007(시간), CUSR0000SA0L1E(지수); M, SA | 기존 batched POST1회. 초기10년 이하 구간, 증분 최근2년. CES와CPI 발표일만 필요그룹 요청; 연례개편때 기존보유창 전체 재처리. 새 통합배치는 Main 구현 승인뒤. |
| Monetary Policy | Fed H.15 `releases/h15/data/Business_day/H15_FF_O.txt`, RIFSPFF_N.B; %, business day, NSA | 기존 H15 pointer·file 경로 재사용, 변경시에만 pointer 재검증. 영업일 H.15 공표후30분. 월평균은 기대영업일 완전해야 계산; 자료1GET, pointer변경시1추가. |
| Liquidity | Fed DDP H.4.1 total assets Wednesday; 백만USD, W, NSA | 기존 고정 package1GET. 목요일16:30 ET 후30분. 52주 비교를 위해 최소53수요일, 증분 최근104주와원시응답해시 보존. “순유동성”으로 바꾸지 않음. |
| Credit | Fed DDP H.8 all-commercial-bank bank credit; 십억USD, M, SA | 기존 고정 package1GET. 금요일 H.8 공표후30분, 월값변경때YoY재계산. 최근24월 겹침; 연례벤치마크는보유창 전체. 회사채 spread 대체 아님. |
| Fiscal | FiscalData `/services/api/fiscal_service/v1/accounting/mts/mts_table_1`; `current_month_dfct_sur_amt`, 백만USD, M, NSA | 12개 완전 월 합계. MTS 발표일16:00 ET 후30분 권고. 월행필터·page중복방지 기존collector재사용;1페이지기준1GET, 페이지있으면추가. |
| FX | Fed H.10 JRXWTFB_N.M; 지수, M, NSA | 기존RAM 경로만. 공개값·새보존 없음. 보유13월 이상, 발표후 월1검증. 사용범위확대승인 전 신규수집 대상에서 제외. |
| E09·curve light | Treasury XML `/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value=YYYY`; 10Y−3M %p | 초기현재·전년2GET; 이후현재년1GET, 연도전환2. 18:00 ET 예상웹공표후30분. 기존22:17UTC 예약은 겨울 공표보다 빠를 수 있으므로 전일값과새관측 구분. 휴일은새관측아님. |
| E22 | Fed DDP G17 fixed package `809009461b1cba2fd5b4cf5557d9d663`, IP.B50001.S; 지수, M, SA | `Download.aspx` CSV1+`Choose.aspx?rel=G17` release-date1, 기존 package재사용. 발표일09:15 ET 후30분. 초기144월, 증분24월+벤치마크개편 재처리. |
| E36 | Fed DDP SLOOS fixed package `e64f07187815f0e7ed89237d8cb91eeb`, SUBLPDCILS_N.Q; %, Q, NSA | CSV1+Choose1. 분기공표후30분, 초기60분기·최근8분기겹침. 관측분기와게시분기분리. |
| E39 core PCE | BEA `NipaDataM.txt`, DPCCRG; 지수, M, SA | BEA월파일1GET. Personal Income and Outlays 발표08:30 ET 후30분. 초기144월;파일전체수신이라해시기반중복제거·보유창수정비교. |
| E40 | Fed `https://www.federalreserve.gov/monetarypolicy/openmarket.htm`; target upper bound %, dated event | FOMC 결정일14:00 ET 후30분 권고1GET. 변경표 날짜는효력일이며발표시각아님. 사후조회한과거사건은실시간사건으로소급생성하지 않음. |
| E01 | BTS `https://data.bts.gov/resource/bw6n-ddqk.json` select obs_date,tsi_freight/order desc/limit180; 지수2000=100, M, SA | 기존180행1GET. BTS발표캘린더후30분 권고 월1, 게시지연시다음점검. 실제가용시각과HTTP Last-Modified 분리. |
| E21·E26 | Census EITS `/data/timeseries/eits/m3`(NXA/NO), `/resconst`(APERMITS/TOTAL); 백만USD M SA / 천호 M SAAR | 기존parser·query재사용, 키미설정이면0요청·null. 권한확정후각1GET, 발표캘린더후30분. 가입·Secret추가 별도승인. |
| E14 | DOL ETA539 `https://oui.doleta.gov/unemploy/wkclaims/report.asp`; 건, W, SA | 기존parser 있음. 권리보류 유지; 새취득 권고량0. 해제승인후주간목요일08:30 ET 후30분,312주초기·최근8주수정창. |

공통 요청량은 표의 **서로 다른 파일/배치 합**이다. Growth/E25, Labor/E13, curve/E09는 중복 요청0. 모든 계열을매일요청하는설계가아니며, 발표일과원본변경이없으면0요청이다. 현행 BLS 코드는 10년 이하 범위를 사용하며 이 설계의 배치는 5계열 이하·발표일 최대2요청이다. 이번 무료문서의 이전 URL은404여서 공급처 최신quota 재확인은미완료다. 미확인한 quota를근거로수집을확대하지않는다.

## 실패·수정·상태 계약

- 원본키: provider + endpoint + 정규화된public query/body + observation-window. Secret은키·로그·manifest에넣지 않는다. 이전응답hash·ETag/Last-Modified(지원시)를캐시하되 Last-Modified를최초발표로쓰지 않는다.
- 성공한 응답은기존파서 검증 뒤 원본hash/수집시각/기간/계열/단위를기록한다. 동일hash는재계산생략. 값변경은관측기간별revisionappend; 과거원본과결과보존. 파서버전이바뀌면수집없이같은원본으로재처리한다.
- 부분실패는해당provider만재개하고성공한공유파일재요청안함. rate-limit/timeout후한번의지연재시도는Main설정승인대상; 실패시마지막성공값·실패시각·reason을남긴다. 관측값0대체없음.
- `last_success_at`은수집성공, `observation_period`는통계대상기간, `available_at`은확인된관측또는보수상한. 달력의계획시각은`planned_release_at`. 실제원발표증거없으면`first_published_at=null`.
- stale는기존근거선정책을재사용: W14일+발표지연7일, M62+45일, Q184+100일(기간말기준). 경고표시만이며데이터삭제/중립화없음. FOMC효력값은새사건전까지유지,자동stale추정없음.
- 월·분기값의일간표시는`held=true`,동일`observation_id`·관측기간 유지. `new_observation`과`revised`를구분하며보간은`NONE`이다. 첫 baseline의조회가능전환은`newly_available=true,new_observation=false`이며새발표로표시하지않는다. `period_origin_kind`는해당기간의최초보관종류이며, 두조회사이에FIRST와REVISION이모두발생해도새관측여부는이최초근거로판정한다. `version_kind`는선택한최신버전종류를별도로표시한다. 기존모델이공식국면산출에적격하다는뜻이아니다.

## 공식 문서 확인과 사용권 경계

2026-11-05 무료공개문서열람: [Fed DDP help](https://www.federalreserve.gov/datadownload/help/default.htm)는 “Data are only available as currently published”, “Pre-revision or real time data are not available”라고명시한다. 같은페이지에11월9일주간 Build Your Package 제거및향후DDP폐지안내가있다. 기존고정package가즉시중단됐다고단정하지않으며FRED자동전환은금지한다(GSQ-011). 변경시원기관새공식경로와사용권을확인해야한다. BLS 과거개발자문서2 URL과BEA FAQ URL은404;이응답으로새API조건을확정하지않았다.

기존BLS·BEA·Fed Board public-domain범위, BTS데이터셋표기·ATA입력예외, CensusAPI출처조건을유지한다. Treasury daily-yield재사용문구미확인과DOL보류는그대로표시한다. FRED/ALFRED 저장·개발경로보류와FX공개제외유지. 이번작업은공급처채택·권리확대·실수집승인이아니다.

## Main용 판독 예시와 남은 연결

계약 `macro-observed-timeline/1`, 진입점 `tools/macro_observed_timeline.py --archive ... --at 2026-01-02T12:00:00Z --at 2026-01-03T12:00:00Z --output /private/result.json`.

합성표시 예: `source_id=BLS:LNS14000000`, `observation_period=2025-11`, `value=4.0`, `unit=%`, `frequency=M`, `seasonal_adjustment=SA`, `available_at=2026-01-02T12:00:00Z`, `first_published_at=null`, `availability_basis=OBSERVED_CAPTURE`, 다음날`held=true,new_observation=false,revised=false`, `model_status=NOT_APPLIED`. 실값은이PR에넣지 않는다.

Main은이필드로기준기간·원발표미확인·수집시각·값유지/수정·stale를연결한다. 새스케줄·원본보존정책·운영재시도적용은별도승인뒤Main이담당한다. Codex는승인된입력정규화·계산을유지한다. M-REENABLE은별도오너결정이며본PR로해제하지 않는다.

## 시각·자료 버전의 근거 계약 보완

기존 `macro-observed-timeline/1`에 `evidence_contract_version=macro-observed-evidence/1` 필드를 추가한다. 14계열 모두 같은 필드를 내보내며, 미수집 계열도 키를 생략하지 않는다. 기존 값·선택·후보 산식은 그대로다.

| 의미 | 실제 CLI JSON 필드 | 근거와 결손 처리 |
|---|---|---|
| 통계 대상 기간 | `observation_period`, `data_asof`, `frequency` | 월·분기·사건 효력일. 발표일이나 수집일로 바꾸지 않는다. |
| 원기관 공식 최초 발표 | `official_release_at`, `official_release_status`; 기존 `first_published_at` | 이 입력 계약에는 충분한 원발표 증거가 없어 null / `NOT_PROVEN_IN_ARCHIVE`. 최초 수집시각·계획일·Last-Modified를 대입하지 않는다. |
| 원기관 자료 버전 | `source_version_id`, `source_version_status` | 원기관 vintage 식별/입증이 없으므로 null / `NOT_PROVEN_IN_ARCHIVE`. 원자료가 초기·2차·최종 수정치인지는 미확인이다. |
| 보관본에서 선택한 버전 | `archive_version_id`, `version_kind`, `version_time_basis`, 기존 `vintage_at` | ID는 선택값·기간·기록시각·종류 해시이며, CLI의 상위 `archive_sha256`와 함께 추적한다. `vintage_at`은 원기관 vintage 시각이 아니라 `version_time_basis`에 따른 기록시각이다. |
| 해당 기간의 첫 기록된 취득 | `first_acquired_at`, `first_acquisition_status`, `first_acquired_by` | 최초 보관 버전이 BASELINE/COLLECTION_TIME이면 기록된 수신시각. SOURCE_LAST_MODIFIED뿐이면 exact 시각은 null / `UPPER_BOUND_ONLY`, `first_acquired_by`에 확인 가능한 수신 상한만 기록한다. 세계 최초 취득이나 원기관 최초 발표가 아니다. |
| 선택한 수정 버전의 취득 | `selected_version_acquired_at`, `available_at`, `availability_status` | 기록된 수신이면 `OBSERVED_CAPTURE_BY_QUERY`, 보관본 생성시각 상한이면 `CONSERVATIVE_CAPTURE_BOUND_BY_QUERY`. 후자는 원발표 당시 가용성 재구성이 아니다. |
| 값·미산출·지연 | `value`, `result_kind`, `stale`, `state`, `reason` | 값이 있으면 `RAW_DIAGNOSTIC`, 없으면 `NOT_COMPUTED`. stale 값도 보존하며 신선한 값 수와 분리한다. 공식 국면·게이트 점수로 해석하지 않는다. |

`query_usable=true`는 **PUBLIC 범위 + 기존 strict 보관본 검증 통과 + 유한 원값 + 선택한 버전의 기록된 가용시각 또는 보수 상한이 조회시각 이하**를 뜻한다. 관측 기간이 오래되면 `stale=true`이며 값은 진단용으로 남는다. `fresh_query_usable` 집계는 stale을 제외한다. 후보규칙 계산 가능성·운영 채택·역사 PIT 검증과 별도다.

`historical_pit_eligible`는 공식 원발표와 원기관 자료 버전 근거를 모두 요구한다. 현재 입력 계약에서 그 근거를 입증할 수 없으므로 false이고, 값이 있는 행의 사유는 `OFFICIAL_RELEASE_AND_SOURCE_VINTAGE_NOT_PROVEN`이다. 각 조회의 `counts`는 `query_usable`, `fresh_query_usable`, `system_available_by_query`, `official_release_proven`, `source_vintage_proven`, `historical_pit_eligible`, `not_computed`를 14계열 분모와 함께 구분한다. 보관본 기준 시스템 가용성은 원기관 역사 PIT 입증과 다르다.

합성 예: 2026-01-02 12:00Z에 처음 보관한 2025-11 월값은 `value=4.0`, `data_asof=2025-11`, `result_kind=RAW_DIAGNOSTIC`, `first_acquired_at=first_acquired_by=2026-01-02T12:00:00Z`, `first_acquisition_status=RECORDED_CAPTURE`, `availability_status=OBSERVED_CAPTURE_BY_QUERY`, `query_usable=true`, `stale=false`다. `official_release_at=null`, `source_version_id=null`, 각 근거 상태는 `NOT_PROVEN_IN_ARCHIVE`, `historical_pit_eligible=false`를 동시에 표시한다. 다음 날 같은 기간·값이면 `held=true`이고 새 발표로 표시하지 않는다.

이 보완은 현재 보관본으로 조회할 수 있는 자료와 과거 원기관 발표 당시 자료를 구분하는 오프라인 계약이다. M-REENABLE, GSQ-011 및 모든 운영 보류를 유지한다.
