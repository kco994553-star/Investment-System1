# 실행 로드맵 v2 — 2026년 4분기

기준일: **2026-10-10 UTC**. 저장소 `kco994553-star/Investment-System1`, canonical `claude/investment-system-top500-validation-alrugm`, 확인 HEAD **`c96f05e9a10b7ba494a43b5f7fabf825ba89f21e`** (#135 사용자 승인 병합 후). 현재 상태의 단일 진입점은 [CURRENT_HANDOFF](../../CURRENT_HANDOFF.md), 운영 규칙은 [WORKING_RULES](../../WORKING_RULES.md)다. 아래는 다음 실행을 정하는 문서이며 수집·예약 실행·배포·새 방법론·가중치·방법론 채택의 추가 승인이 아니다. 최신 대화에서 허용한 **26E 결정 기록 변경이 없는 PR의 조건부 자체 병합**은 최종 실행 필수 체크 전부 성공·실패0일 때 적용한다.

**Gate A·FPIA·HG: 1인용 범위 해당 없음(종료)** — #100 이후 현행 작업의 선행 조건으로 재사용하지 않는다. 계산·입력·개인정보 검사와 Frozen·원본 TARGET 불변은 유지한다.

## 현재 상태

완료는 명시한 문서·코드·운영 범위에 한정한다. `부분 완료`는 일부 구현이 있다는 뜻이며 실제 입력·3시장 지원·PIT·화면 제공이 모두 확인됐다는 뜻이 아니다. 프로젝트 완료율이나 전체 종목군 완전성을 PR·테스트 수로 환산하지 않는다.

| 범위 | canonical 및 열린 PR에서 확인한 상태 | 남은 일 |
| --- | --- | --- |
| 운영·공개 경계 | #100 혼합 운영, #96·#97 공개 가격 수집/출력 정리, #108 GSQ-014 확정 | 공개 가능 비가격 자료와 개인 RAM 가격/파생값을 분리한다. 작은 변경마다 GSQ·receipt·fingerprint를 만들지 않는다. |
| 시세·Worker·Pages | #113 앱 Worker, #114 수동 Pages, #116 백업, #117 표시 JS, #119 candle/MA, #120 private Trades 코드 병합 | 실제 본인 인증·권리/시장 coverage·기기 성공은 별도 운영 검증. 이번 Python/문서 작업에서 배포·키·개인 시트를 조회하지 않았다. |
| SEC·Q/G | #98 가격 없는 Q/G 후보 병합; #121/#126/#138 병합·daily17/17 BUILD_OK failed_companies=0 확인 | raw normalize 성공과 전체 재무 Q/G/주식basis READY는 별개. #145 Universe504 분할구조 준비·실제504 취득 후속; V·개인 선정/가격 공개 제외. |
| Macro | #104 primary4축·#112 후속4축 조사 병합; #128/#141 Python 공급/공개 raw 화면 병합·코덱1 #144 화면 pipeline 병합 | 정부8×6 raw screen·명시적binding 파서·공개5sidecar 코드 준비. 실제 입력/운영은 후속. GDP/CPI 정규화·후속series/basis·6상태 규칙 미정, 실제 국면 NOT_AVAILABLE. Fed는 확인된 DataSet fragment만 지원. |
| M3 | #106 순수 계산, #110 근거 있는 SHARE_CLASS_BASIS 표시 병합. TARGET19 + 기기 ★ + 비공개 Universe 상위 N, 기본 N=20·불일치10% 확정 | 기기·Worker 연결은 코덱1. 실제 목록·가격·시총·순위·시트 ID는 공개하거나 새 저장 경로에 넣지 않는다. share-class 자동 보정 없음. |
| 기술 계산·Research 표시 | #111/#115 병합. #111 세 계산62통과; #115 Research·GSQ-015·Python 참조/합성 JSON130통과 | 기존 분리 유지. #115 승인/병합·JS8120값 대조0실패. Research role·warmupnull·모델입력금지 유지. |
| 현재 회귀 장애 | #131 CSP해소·현재통합결과는 CURRENT_HANDOFF 참조 | PWA후속은코덱1 공개builder를사용하고guard완화없음. 전략bridge는QGV모듈이며PIL규칙유지. |
| QGV v2·Holdout | v2 보류. 기존 Holdout **UNCONFIRMED 유지·v2 근거 제외** | 검증은 향후 forward 데이터만 사용하며 시작 시점은 사용자가 결정한다. 에이전트는 기간을 선택·사용하지 않는다. |

## 할 일 목록

번호는 사용자가 제시한 기본 순서를 보존한다. 담당이 복수인 행은 Python/데이터·계약은 코덱2, 앱·Worker·Actions는 코덱1, 설정/범위 결정은 사용자다. `대기` 행의 구현을 이번 문서 작성으로 시작하지 않는다.

| 항목 | 담당(코덱1·코덱2·사용자) | 선행 조건 | 상태 | 종료 조건 |
| --- | --- | --- | --- | --- |
| 1. 시세 연결 완료 | 코덱1·사용자 | 본인 인증·허가된 공급자/무료 범위, 시장별 현재가와 일봉의 지원을 구분. 예비 출처 조건 확인은10과 병행 | **부분 완료** — 수동/Sheets·앱 Worker 연결 코드 있음; 운영·권리/coverage 확인 남음 | TARGET19의 미국·한국·일본 상장 identity·통화·시각·basis 확인, 성공/누락/만료/접속 실패가 기기에서 검증됨. 현재가만 있는 출처를 일봉으로 확대하지 않고 실패는 NOT_AVAILABLE·허용된 Sheets/수동 경로로 표시. 가격·새 파생값은 기기/Worker RAM-only. |
| 2. SEC 실제 수집 + 매일 갱신(Actions, 공개 가능 자료만) | 코덱2(취득/검증)·코덱1(Actions/앱)·사용자(운영 범위) | 공개 US17·SEC_USER_AGENT 설정·실제 실행/보존/공개 범위, #121→#126 연결 | **#121/#126/#138 병합·daily failed_companies=0; #145 Universe504구조 병합** | 허가된 첫 취득·회사/정정/가용시각·보존/replay·retry/rate·일일 갱신을 검증. 공개는 SEC 비가격 재무만이며 ★/Universe 선정·가격·V·순위 제외. |
| 3. V 계산 설계(가격 입력은 기기 RAM 전용) | 코덱2·사용자·코덱1(앱) | 기존 v1 산식·재무/가격 통화·주당/split/시점 basis; 미정 solver/매핑 결정 | **#125/#143 병합·DCF기본금융값/FCFE basis 확인대기** | 명시적 가격 인자/RAM-only·NA·기존 raw_map 일치 검증. DCF/역DCF solver·가격→자체multiple/역사/sector/theme 미정은 새 산식 없이 NOT_AVAILABLE. 앱/공개 serializer 연결 없음. |
| 4. 전략 프로필 미리보기 | 코덱2(QGV bridge)·코덱1(화면)·사용자(정의) | 공식 v1 축내부 비중·사용자 축별 합100; 부모/6관점 비중은 미정 | **#127 병합·#146 JS대조계약 병합** | 공식 복사본·사용자 합100·결측수·차단/금융 적용성·불변성 검증. Q/G 기존 평균과 V 분리, 개인 독립 PIL/공식 가중치·snapshot·새 총점 변경 없음. |
| 5. 매크로 국면 엔진 → 앱8축 연결 | 코덱2(입력/엔진경계)·코덱1(앱)·사용자(의미) | GDP/CPI→기존 growth/inflation 대응·6상태 의미/mapping 확정; candidate 승격 없음 | **#128/#141 병합·코덱1 #144 공개화면 pipeline·실제 국면 미확정** | 기존 임계 그대로이며 missing0/NORMAL 금지. 미승인 실제 mapping/6상태는 NA, govt JSON RAM 함수·8축 UI/producer 연결은 후속. |
| 6. 나머지 매크로4축 구현 | 코덱2·사용자 | #112 official source의 exact series/필드·단위/SA/basis/PIT·직접 경로 | **Fed H41/H8/H10·MTS supplied 파서 #128 병합·exactselector확인대기** | 명시적 binding·capture cutoff·safe XML/JSON·partial/단위·모의 검증 PR 있음. 기본series/스케일변환/새 state 없음. full-feed/ZIP extraction 미확인, SLOOS/DTS 보조 구현 제외, FRED 차단. |
| 7. 기기 백업·불러오기 확인/구현 | 코덱1·사용자 | #116 통합 ACTUAL/수동 market·★/Groups/안전 설정 범위를 점검; 추가 포함 범위는 결정 필요 | **#116 통합 구현 병합·실기기 복원 확인 대기** | 허용된 기존 개인 입력 export/import·legacy·오류/손상/중복·복원 후 동작을 검증. OAuth 토큰·키·Sheets ID와 M3 파생 membership/가격/결과는 백업 제외. 기존 수동 시세 백업 허용과 새 RAM 파생값 제외를 혼동하지 않음. 추가 구현은 확인된 공백만 처리. |
| 8. DART 연결 | 코덱2·사용자, 코덱1(후속 앱/Actions) | **사용자가 10/11 18시 이후 DART_API_KEY 등록을 알린 뒤** 서비스·키 이용 조건/회사 결속 확인. 원 공지 시간대 미명시 | **사용자 알림 대기·착수 금지** | 한미반도체 별도 adapter로 회사/계정 매핑·CFS/OFS·기간/통화/단위·정정/취득 경계를 모의 및 허가된 실제 응답에서 검증. SEC JSON으로 오인하지 않음. 알림 전 코드·키 존재 확인·인증/API 실행 없음. |
| 9. EDINET(도쿄일렉트론) 연결 | 사용자·코덱2·코덱1(후속 연결) | **API v2 Subscription-Key 필수**, 등록 알림·착수 결정; E02652/TSE8035/secCode80350 결속 | **사용자 결정으로 후순위 보류·adapter비착수** | 별도 목록→XBRL/CSV context·회계/단위·정정/취득 adapter와 조건부 숫자 재사용 검증. 이번에는 키/계정/API 조회 없이 문서로 기록; 필요하면 보고 후 대기 지시 준수. |
| 10. 가격 예비 경로(Tiingo/KRX) | 코덱1(기기/Worker)·코덱2(계약)·사용자 | 무료/권리·시장·일봉/basis·KRX 장기 범위·Worker 승인 | **코덱1 #124 병합·운영/조건확인후속** | 허용된 본인 fallback·실패/누락 검증. KRX 등록 보고와 실제 인증/지원 구분, 일본 본상장 별도 근거, RAM·공개 금지·전체500 자동 확대 없음. |
| 11. 내 거래 B/S(Sheet Trades 탭) | 코덱1·사용자 | readonly 로그인·private Trades schema/시각/identity·개인 경계 | **#120 RAM1회 읽기/B·S 표시 병합·실기기 확인 대기** | 모의 parser/계약과 코드 병합을 실제 본인 기기 성공으로 간주하지 않음. 공개/telemetry/서버복제·새 파생 백업 제외, 추가 보관/정정 범위는 별도 결정. |
| 12. 실적 발표일 출처 | 코덱2·코덱1·사용자 | SEC10-Q/10-K supplied 제출본·cutoff; 확정 실적일 출처는 별도 | **#123/#141 병합·패턴 예상시기/확정일아님** | form/reportDate별 관측 filing month/day range와 **확정일 아님** 표시. 미래 정확일/평균/분기 추론 없음, actual earnings date source 후속. |
| 13. 13F 수집 | 코덱2(parser)·코덱1(후속 수집/화면)·사용자(기관) | 사용자가 선택한 manager·cover/정정/비공개/표 완전성·연속분기 | **#129/#141 병합·사용자공급기관/원문 필요** | NEW/ADD/REDUCE/EXIT 보고 수량만·실제 전량매도 단정 없음. 추가정정/NOTICE/부분/불명귀속은 비교NA; 금액 단위 보존, 투자자 기본 목록/실제 수집 후속. |
| 14. 뉴스 출처 조사 | 코덱2·사용자 | 공식 공시/IR/RSS/API 후보와 링크/본문 저장·재사용권·범위/시각 확인 | **연구 로직 일부 있음·공급자 미선택** — NEWS_NO_SOURCE | 출처별 이용·저장/재배포·시각·정정/중복·회사 결속 비교 문서와 실행 가능한 무료 후보를 제시. 조사만으로 본문 수집·점수 가산·QGV 변경을 시작하지 않음. |
| 15. 모델 포트폴리오·6관점 정의 | 사용자(정의)·코덱2(계약)·코덱1(화면) | **6관점의 이름/목적/원본 입력/기존 TARGET·Model·Actual·Gap 대응을 사용자 확정**; 4의 preview와 모델 적용 구분 | **기존 portfolio 계약·TARGET/ACTUAL 있음·새 정의 대기** | 확정6관점 및 기존 StrategyVersion/snapshot의 모델 포트폴리오 계약·비교 표시 명세가 있음. 실제 보유와 모델을 혼동하지 않고 새 종합점수·권장 비중·방법론/가중치를 임의 생성하지 않음. |
| 16. 모의투자/전진검증 시작일(사용자 결정) | 사용자·코덱2(검증)·코덱1(기록/화면) | 사용자 시작 시점·대상·전략버전·입력 cutoff·예측/관측·결측/중단 처리·허용 보관 범위 결정 | **시작일 미정·대기**, QGV v2 보류 | 사용자 결정 기록 후 향후 축적 데이터만 별도 forward namespace로 검증. 시작일/기간을 에이전트가 선택·소급하지 않고 기존 Holdout은 UNCONFIRMED·미사용 유지. Preview/Sandbox/Backtest/Forward 결과를 구분. |
| 17. M3 개인 부분집합 기기 연결 | 코덱1·사용자 | #106/#110 Python 계약·★/private Universe1회·SECshares×price basis | **Python 병합·코덱1 #122 JS WIP** | TARGET19+★+검증 상위N(default20) 기기선택, 불일치10%/SHARE_CLASS_BASIS 표시만·자동 보정 없음. 개인 목록/가격/순위/시트ID 공개·새 저장 없음. |
| 18. 기술 계산/Research 표시 연결 | 코덱2(Python/조건부병합)·사용자(#115 승인)·코덱1(표시) | #111 최종체크·#115 GSQ-015 승인·CSP 회귀·합법적인 일봉/basis | **#111/#115/#117/#119 병합·Research전용 유지** | 사용자 확정 분리를 유지. Research role·warmupnull·Model/TSV/QGV 금지, 승인된 periods만·실제 입력 gate 후속. |

## 추천 순서와 변경 제안

기본은 **1→2→3→4→5→6→7→8→9→10→11→12→13→14→15→16**이며 17·18은 관련 연결 작업에 병행한다. 날짜·기간·새 방법론을 이 순서로 확정하지 않는다.

1. **6→5(8축 최종 연결 완료)로 변경 제안.** 5의 입출력 계약/첫4축 표시 작업은 먼저 또는 병행할 수 있지만, 실제8축 종료 조건은 나머지4축 입력·의미 대응이 있어야 충족된다. 조사 완료나48칸 배열을 전체 국면 완료로 세지 않는다. 권고 실행 순서는1→2→3→4→6→5→7 이후 기본 순서다.
2. **10의 권리·지원 조건 검토를1과 병행.** 본 경로가 허가/coverage 미확인으로 막히면 예비 출처 확인이1의 선행 조건이다. 전체 fallback 구현의 기본 위치10은 유지하며 허가 없는 가격 호출로1을 완료하지 않는다.
3. 8은 사용자 등록 알림 전 비착수 대기열이다. 그동안9 이후의 독립 조사/계약 준비와7의 기존 백업 검증을 진행할 수 있다. 2의 SEC 재무 취득도1의 가격 연결을 기다릴 데이터 의존성이 없다. 15의6관점 정의는4의 preview 용어 정리와 병행하되 모델 계산 채택으로 확대하지 않는다.

## 사용자 결정·조치가 필요한 항목

아래는 아직 필요한 선택/조치다. 이미 확정된 N=20·10%, 표시용 지표 period, 무료 원기관 원칙, Holdout 미사용을 다시 확인 요청하지 않는다. 기술 표시 GSQ-015/#115는병합됐다. GSQ-017유형기록포함#135는사용자승인후병합됐다.

| 결정·조치 | 필요한 내용 | 연결 항목/결정 전 경계 |
| --- | --- | --- |
| 26E 변경 PR 병합 | SIC→업종군 매핑 초안 확인; #135 병합 승인 완료. 이후26E결정변경PR만별도승인 | #135 유형/설정 의존성.26E미변경PR은실행필수체크전부성공·실패0에서자체병합. |
| SEC 운영 범위 | 실제 취득 대상(현재 US17 부분집합부터), 일일 실행시각/예산·보존 위치·공개 출력 범위 및 실행 승인 | 2. 사용자 연락처는 설정에만 두며 공개 로그에 출력하지 않음. 기기 선정 목록을 Actions 대상으로 역전송하지 않음. |
| V 재계산 정책 | 기존 V의 정확한 입력시점·가격 변경 시 무효화/재계산 및 P02 중간시점 처리 | 3. 새 산식/가중치를 에이전트가 제안값으로 적용하지 않음. |
| Macro 후속 입력 채택 | GDP/CPI 정규화·후속4축 exact series/필드/단위/SA/basis와 기존 상태 의미 | 6→5. supplied 파서 구현을 source/새6상태 채택으로 확대하지 않음; 실제 mapping NA. |
| 추가 백업·Trades 확인 | #116/#120 실기기 복원/읽기·정정 동작 확인 후 추가 필요한 보관 범위 | 7·11. 구현 계약을 다시 결정 요청하지 않으며 새 파생/시트ID/토큰 제외 유지. |
| DART 등록 알림 | **10/11 18시 이후 등록 완료 알림**. 시간 도달만으로 알림/허가로 간주하지 않음 | 8. 알림 전 코드·키 존재 확인·인증/API 착수 금지. |
| EDINET 등록 | 사용자 후순위 보류 유지; 향후착수결정 때키등록조건 확인 | 9. Subscription-Key 필요 확인; 값/키 존재 확인·API·adapter 비착수. |
| 가격 예비 조건 | Tiingo 계정의 무료 범위/한도/권리·KRX 이용조건/지원, 일본 본상장 일봉 출처 | 1·10. KRX 등록 보고를 인증·허가·3시장 coverage 완료로 간주하지 않음. |
| 실적/13F/뉴스 범위 | 실적 출처의 대상·예정/확정 처리, 13F 추적기관 집합, 뉴스 후보·본문/링크 이용 범위 | 12·13·14. 조사→계약→승인된 수집의 범위를 구분. |
| 모델 포트폴리오·6관점 | 6관점의 정확한 정의/기존 계약 대응과 모델 표시·적용 구분 | 4·15. 기존 PROVISIONAL 프로필 숫자를 공식 모델로 승격하지 않음. |
| 모의투자/forward 시작 | 시작 시점·대상/전략버전·입력/결과 보관·검증 규약; v2 착수 여부 | 16. 사용자 결정 전 시작/기간 선택 없음, 기존 Holdout 미사용. |

추가 장기 대기열의 결과/미확정 정의는 [TARGET19·500커버리지](company_types/QUEUE_RESULTS_AND_COVERAGE.md), [8축대응초안](macro_data_rights/EIGHT_AXIS_MAPPING_PROPOSAL.md), [DCF기본값제안](valuation/DCF_V1_PARAMETERS.md)을참조한다. 유형·테마·DCF·매크로의미확정기준은사용자확인전NA이며26E에는확정결정만추가한다.

추가 장기 대기열의 결과/미확정 정의는 [TARGET19·500커버리지](company_types/QUEUE_RESULTS_AND_COVERAGE.md), [8축대응초안](macro_data_rights/EIGHT_AXIS_MAPPING_PROPOSAL.md), [DCF기본값제안](valuation/DCF_V1_PARAMETERS.md)을참조한다. 유형·테마·DCF·매크로의미확정기준은사용자확인전NA이며26E에는확정결정만추가한다.

## PR 정리

이번 사용자 지시 범위만 적용하며 다른 열린 PR·브랜치·Git 이력을 삭제하지 않는다.

| PR | 처리 | 사유 한 줄 |
| --- | --- | --- |
| [#103](https://github.com/kco994553-star/Investment-System1/pull/103) | 사용자 지시에 따라 닫음·미병합 이력 보존 | #100 이후 canonical 단일 인수인계가 최신 상태를 담으므로 이전 현황 초안의 별도 병합이 불필요. |
| [#107](https://github.com/kco994553-star/Investment-System1/pull/107) | 사용자 지시에 따라 닫음·미병합 이력 보존 | 정식 M3 #106·#108·#110 이후 이전 계약 테스트 초안을 병합 대기 목록에서 정리. |
| [#109](https://github.com/kco994553-star/Investment-System1/pull/109#issuecomment-6094092058) | 이미 CLOSED·미병합 확인; **코덱1에게 종료 유지 확인만 요청** | 정식 Worker/#113 앱 연결 경로 이후 단일파일·메모리 제한 대안을 현행 실행 경로로 사용하지 않음. 코덱2 상태 변경 없음. |

## 근거

- [#100 작업 규칙](../../WORKING_RULES.md), [26E GSQ-007~014](pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md), 표시 결정/구현 [#115](https://github.com/kco994553-star/Investment-System1/pull/115).
- SEC: [M1 경계](daily_data_pipeline/M1_SEC_INPUTS.md), [수동 취득 도구](../tools/sec_m1_inputs.py), [#98 후보 표시](https://github.com/kco994553-star/Investment-System1/pull/98).
- Macro: [#104 4축 명세](macro_data_rights/PHASE1_FOUR_AXES_IMPLEMENTATION_SPEC.md), [#112 나머지4축 조사](macro_data_rights/REMAINING_FOUR_AXES_PRIMARY_SOURCES.md), [48칸 입력](../src/investment_system/macro/primary_input.py), [기존 엔진](../src/investment_system/macro/engine.py).
- M3: [부분집합 계약](daily_data_pipeline/M3_SUBSET_IMPLEMENTATION_SPEC.md), [개인 RAM 경계](daily_data_pipeline/M3_PRIVATE_UNIVERSE_DESIGN.md).
- 기기/화면: [IA](frontend_ia_v1/COCKPIT_IA_v1.md), [프로필 계약](../src/investment_system/contracts/strategy.py), [ACTUAL/market 백업](../src/investment_system/product/web_assets/device-market.js).
- 재무: [DART 준비](daily_data_pipeline/DART_CONNECTION_READINESS.md), [KR/JP 공식 출처](fundamentals_sources/KR_JP_FILINGS_RESEARCH.md), [파이프라인 요구](daily_data_pipeline/PIPELINE_DESIGN.md).
- 검증: [Holdout 확인 UNCONFIRMED](qgv_v2_readiness/HOLDOUT_PROTECTION_CHECK_20261010.md), [v2 진입 체크리스트](qgv_v2_readiness/HOLDOUT_AND_ENTRY_CHECKLIST.md).

## 이력

이 절은 이전 로드맵(기준 #87, 후속 #94/GSQ-011)을 축약한 작성 당시 기록이다. 현행 상태/선행 조건은 위 v2 표가 우선한다. 상세 원문·출처표는 [재작성 전 canonical 문서](https://github.com/kco994553-star/Investment-System1/blob/12588fd51ac13f80d86f6eba11018456c143eaae/implementation/docs/ROADMAP_2026Q4.md)와 Git 이력에 보존돼 있다.

- Track A의 FROZEN_VERIFIED 역사 기준선과 STANDARD v1 UNCALIBRATED를 보존한다. 역사 기준선은 현재 입력/strict PIT·새 모델 성과의 증거가 아니다.
- #70 수동 ACTUAL·KRW 평가, #73·#74 선택형 Sheets/CSP, #72·#75 Cockpit IA/탐색, #76 리서치 필드 안내가 구현/문서 기준선이었다. 12화면 실제 데이터 전체 완료를 뜻하지 않았다.
- #77·#78은 KR/JP 조사와 M0~M5 파이프라인 설계, #81은 SEC M1, #86은 가격 없는 Q/G 후보, #84·#85·#87은 DART/개인 가격/인증 준비였다. 당시 Worker·계정 ‘미구현/미연결’ 표시는 #88 이후 구현과 #102·#113·#114의 후속 상태로 대체한다.
- 당시 M3 전체 Top500 공개 계획·약100개 구상은 GSQ-012~014의 TARGET19+기기★+비공개 Universe 상위N·개인 RAM 계획으로 구체화됐다. Frozen membership를 현재 전체 종목군으로 쓰거나 전체 순위를 주장하지 않는다.
- 121개 차트/core81·L1~L5 과거 감사 계수와 S01~S12 요구 표는 작성 당시 inventory다. 현재 제공/실데이터 완료율로 재사용하지 않고 상세 [차트 inventory](../experiments/chart-contract-v0.1/CHART_INVENTORY.md)·[IA](frontend_ia_v1/COCKPIT_IA_v1.md)를 참고한다.
- #93 정리, #94 구현 명세, GSQ-011 원기관 4축 채택과 Holdout metadata 확인이 후속 문서였다. 당시열린PR표시는현행#111/#115병합및위현재표로대체한다.
- 과거 운영 검증 절차의 상세 표와 영수증은 이력으로 남긴다. #100의 1인용 운영 종료 결정을 이번 계획의 승인 차단으로 되돌리지 않는다.
