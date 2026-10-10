# 실행 로드맵 v2 — 2026년 4분기

기준일: **2026-10-10 UTC**. 저장소 `kco994553-star/Investment-System1`, canonical `claude/investment-system-top500-validation-alrugm`, 확인 HEAD **`12588fd51ac13f80d86f6eba11018456c143eaae`** (#114 병합 후). 현재 상태의 단일 진입점은 [CURRENT_HANDOFF](../../CURRENT_HANDOFF.md), 운영 규칙은 [WORKING_RULES](../../WORKING_RULES.md)다. 아래는 다음 실행을 정하는 문서이며 수집·예약 실행·배포·새 방법론·가중치·코드 병합의 추가 승인이 아니다.

**Gate A·FPIA·HG: 1인용 범위 해당 없음(종료)** — #100 이후 현행 작업의 선행 조건으로 재사용하지 않는다. 계산·입력·개인정보 검사와 Frozen·원본 TARGET 불변은 유지한다.

## 현재 상태

완료는 명시한 문서·코드·운영 범위에 한정한다. `부분 완료`는 일부 구현이 있다는 뜻이며 실제 입력·3시장 지원·PIT·화면 제공이 모두 확인됐다는 뜻이 아니다. 프로젝트 완료율이나 전체 종목군 완전성을 PR·테스트 수로 환산하지 않는다.

| 범위 | canonical 및 열린 PR에서 확인한 상태 | 남은 일 |
| --- | --- | --- |
| 운영·공개 경계 | #100 혼합 운영, #96·#97 공개 가격 수집/출력 정리, #108 GSQ-014 확정 | 공개 가능 비가격 자료와 개인 RAM 가격/파생값을 분리한다. 작은 변경마다 GSQ·receipt·fingerprint를 만들지 않는다. |
| 시세·Worker·Pages | 수동/선택형 Sheets 구현, #102 검증 수정, #113 앱 Worker 연결·email 재동의, #114 검증 후 수동 Pages 게시 경로가 병합됨 | 병합·mock 검증과 실제 본인 기기의 성공을 구분한다. 이번 문서 작업에서 서비스·키·개인 시트를 조회하거나 배포하지 않았다. |
| SEC·Q/G | SEC M1의 US17 명시적 부분집합 수동 live CLI·보존/replay 코드, #98 가격 없는 Q·G 후보 앱 표시 | 실제 취득 확인·매일 Actions 연결 미완료. V는 NOT_AVAILABLE, 후보는 PROVISIONAL_RESEARCH이며 완전 QGV/공식 순위가 아니다. |
| Macro | #104 BLS CPI·Labor·Treasury·BEA 원기관 4축 요청 계획/제공 응답 파서·48칸 근거 계약; #112 Liquidity/Credit/Fiscal/FX 출처 조사 병합 | 입력 근거와 국면 계산은 별개다. 일부 Level의 RAW_EVIDENCE 외 상태 계산은 NOT_APPLIED, 후속4축은 DEFERRED_GSQ011. 실8축 producer·앱 연결 미완료. |
| M3 | #106 순수 계산, #110 근거 있는 SHARE_CLASS_BASIS 표시 병합. TARGET19 + 기기 ★ + 비공개 Universe 상위 N, 기본 N=20·불일치10% 확정 | 기기·Worker 연결은 코덱1. 실제 목록·가격·시총·순위·시트 ID는 공개하거나 새 저장 경로에 넣지 않는다. share-class 자동 보정 없음. |
| 기술 계산·Research 표시 | **#111·#115 열림·미병합**. #111 현행 세 계산, #115 표시 전용 지표·GSQ-015 기록. 각각 관련62/89 테스트와 최종 CI6개 성공 | 최신 대화의 표시 기본값은 승인됐지만 모델 채택은 아니다. 두 코드 PR은 별도 사용자 병합 승인 대기. 새 코드가 canonical에 반영됐다고 쓰지 않는다. |
| 현재 회귀 장애 | #113 이후 `tests/test_app_nav_ia.py::test_navigation_does_not_expand_approved_external_csp_permissions` 실패. #111·#115와 canonical07ba93e3 단독 checkout에서 재현 | connect-src의 Worker 출처 추가와 이전 테스트 기대값 차이; 코덱1 앱/CSP 검증 범위. #114는 이 코드/테스트를 바꾸지 않았다. CI 성공과 전체 suite 성공을 구분한다. |
| QGV v2·Holdout | v2 보류. 기존 Holdout **UNCONFIRMED 유지·v2 근거 제외** | 검증은 향후 forward 데이터만 사용하며 시작 시점은 사용자가 결정한다. 에이전트는 기간을 선택·사용하지 않는다. |

## 할 일 목록

번호는 사용자가 제시한 기본 순서를 보존한다. 담당이 복수인 행은 Python/데이터·계약은 코덱2, 앱·Worker·Actions는 코덱1, 설정/범위 결정은 사용자다. `대기` 행의 구현을 이번 문서 작성으로 시작하지 않는다.

| 항목 | 담당(코덱1·코덱2·사용자) | 선행 조건 | 상태 | 종료 조건 |
| --- | --- | --- | --- | --- |
| 1. 시세 연결 완료 | 코덱1·사용자 | 본인 인증·허가된 공급자/무료 범위, 시장별 현재가와 일봉의 지원을 구분. 예비 출처 조건 확인은10과 병행 | **부분 완료** — 수동/Sheets·앱 Worker 연결 코드 있음; 운영·권리/coverage 확인 남음 | TARGET19의 미국·한국·일본 상장 identity·통화·시각·basis 확인, 성공/누락/만료/접속 실패가 기기에서 검증됨. 현재가만 있는 출처를 일봉으로 확대하지 않고 실패는 NOT_AVAILABLE·허용된 Sheets/수동 경로로 표시. 가격·새 파생값은 기기/Worker RAM-only. |
| 2. SEC 실제 수집 + 매일 갱신(Actions, 공개 가능 자료만) | 코덱2(취득/검증)·코덱1(Actions/앱)·사용자(운영 범위) | 공개 issuer allowlist·수집시각/예산/보존 위치·SEC_USER_AGENT 설정과 실행 범위 확정. 1의 가격을 입력으로 요구하지 않음 | **부분 완료** — US17 수동 CLI 있음; 실제 취득 및 daily schedule 미확인/미구현 | 허가된 첫 취득·회사/기간/정정/가용시각·불변 보존/replay를 확인하고 중복/부분실패/재실행·갱신시각 처리와 매일 실행을 검증. 공개 출력 whitelist는 재사용 가능한 SEC 비가격 재무만. ★·Universe 선정 목록·가격·V·가격 기반 순위는 Actions/공개 출력 제외. |
| 3. V 계산 설계(가격 입력은 기기 RAM 전용) | 코덱2·사용자, 코덱1(후속 앱) | 기존 V 계약의 필요한 재무·가격 basis/시점 매핑, 1·2 입력 경계, 가격 변경 시 재계산 정책 | **설계 대기** — #98은 가격 없는 Q/G·V 미제공 | 기존 산식·기간/통화·누락·PIT·재계산/무효화 규칙의 입력/출력 설계를 사용자가 검토. 가격·V·가격 결합 QGV는 RAM-only, 새 산식·가중치·0 대체·공개 serializer 없이 후속 구현 명세가 있음. |
| 4. 전략 프로필 미리보기 | 코덱1(화면)·코덱2(기존 계약) | 기존 PROVISIONAL profile의 값/동결 항목/설명 대응, 사용자 선택이 모델 적용을 뜻하지 않는 경계 | **부분 완료** — builtin/mixed/custom 계약 있음; 상세 preview 화면 OPEN | 기존 프로필의 읽기용 비교/미리보기·provisional/누락 표시를 검증. 모델 재채점·새 weights/threshold editor·Frozen 변경 없이 저장/적용 여부를 명확히 구분. |
| 5. 매크로 국면 엔진 → 앱 8축 연결 | 코덱2(엔진/producer)·코덱1(앱) | #104 + 6의 원기관 입력, 기존 승인된 국면 계산과 입력 의미의 정확한 대응; v0.1.4-CANDIDATE 자동 승격 금지 | **부분 완료** — 48칸 근거 계약·8축 UI 있음; 실제 계산/연결 미완료 | Growth/Inflation/Monetary Policy/Liquidity/Credit/Fiscal/FX/Labor의 Level·Direction·Momentum·Surprise·Stress·Confidence를 근거/시각/결측과 함께 연결·검증. 미승인 계산·기대치·근거 없는 칸은 NOT_AVAILABLE로 명시. raw 입력을 완성 국면·단일 Macro Score로 바꾸지 않음. |
| 6. 나머지 매크로 4축 구현 | 코덱2·사용자(입력 의미 채택) | #112 공식 출처 조사에서 정확한 자료/series·단위·발표본/PIT·권리 대응 결정 | **조사 완료·구현 대기** — Liquidity/Credit/Fiscal/FX DEFERRED | 원기관 어댑터·발표/수정/취득시각·cutoff·모의 응답·known missing/error 테스트를 구현한 승인 대상 PR이 있음. H.4.1, H.8/SLOOS, MTS, H.10은 후보이며 자동 채택/합성하지 않음. FRED/ALFRED 금지, 새 국면 규칙/가중치 없음. |
| 7. 기기 백업·불러오기 확인/구현 | 코덱1·사용자 | 기존 ACTUAL/수동 market schema2·★/Groups prefs 범위를 점검; 추가 포함 범위는 결정 필요 | **기존 구현 있음·통합 확인 대기** | 허용된 기존 개인 입력 export/import·legacy·오류/손상/중복·복원 후 동작을 검증. OAuth 토큰·키·Sheets ID와 M3 파생 membership/가격/결과는 백업 제외. 기존 수동 시세 백업 허용과 새 RAM 파생값 제외를 혼동하지 않음. 추가 구현은 확인된 공백만 처리. |
| 8. DART 연결 | 코덱2·사용자, 코덱1(후속 앱/Actions) | **사용자가 10/11 18시 이후 DART_API_KEY 등록을 알린 뒤** 서비스·키 이용 조건/회사 결속 확인. 원 공지 시간대 미명시 | **사용자 알림 대기·착수 금지** | 한미반도체 별도 adapter로 회사/계정 매핑·CFS/OFS·기간/통화/단위·정정/취득 경계를 모의 및 허가된 실제 응답에서 검증. SEC JSON으로 오인하지 않음. 알림 전 코드·키 존재 확인·인증/API 실행 없음. |
| 9. EDINET(도쿄일렉트론) 연결 | 코덱2·사용자, 코덱1(후속 앱/Actions) | 사용자 API v2 등록/키·약관/MFA, E02652와 TSE8035·secCode80350 결속, 별도 parser 범위 확정 | **조사 완료·연결 대기** | 제출 목록→문서 선택→XBRL/CSV context·연결/별도·회계/단위·정정/철회·시각을 검증한 adapter. 숫자 재사용/가공 출처 조건 준수; 주석/보고서 전문·taxonomy 재배포를 자동 허용하지 않음. |
| 10. 가격 예비 경로(Tiingo/KRX) | 코덱1(기기/Worker)·코덱2(입력 계약)·사용자 | 시장별 권리·무료 계정/한도·basis/일봉 coverage 확인. KRX_API_KEY는 GSQ-009의 **등록 보고**이며 실제 인증 검증과 구분 | **후보 조사·조건 확인 대기** | Tiingo 미국·KRX 한국의 허용 범위/실패 동작을 검증하고 본인용 fallback을 연결. 일본 본상장은 별도 근거 필요. 권리 미확인 자동 조회 금지, 비용0·개인 RAM·공개 금지 유지, 전체500 자동 확대 없음. |
| 11. 내 거래 B/S(Sheet Trades 탭) | 코덱1(기기)·코덱2(계약/검증)·사용자 | 비공개 Trades 열·시간대·상장 identity·B/S enum·수량/가격·중복/정정 규칙과 기존 readonly 로그인 범위 확정 | **미구현** — Quotes parser의 거래시각은 내 거래 parser가 아님 | Trades 1회 읽기/파싱·모의 계약 검사, 개인 차트 B/S overlay 및 표시 OFF/오류 처리 검증. 공개/telemetry/서버 복제 없이 개인 경계를 적용하며 거래 데이터의 보관/백업 범위는 결정에 따름. |
| 12. 실적 발표일 출처 | 코덱2·사용자, 코덱1(표시) | 회사 IR 등 공식 출처 범위·예정/확정/변경·timezone·취득시각 계약 | **요구사항 있음·출처/producer 대기** | 확인된 Next Earnings/D-day를 근거 링크·시각·변경/미확정과 함께 표시. SEC 제출일을 예정 발표일로 추정하지 않고 실제 출처 미확인은 NOT_AVAILABLE. |
| 13. 13F 수집 | 코덱2·사용자(추적기관)·코덱1(Actions/화면) | 추적 manager 집합·공개 재사용 범위·분기/제출일/정정·security mapping·갱신 방식 | **미구현** — 화면 준비 중 | 전용 filing ingestion·정정/중복·종목 결속·지연 공시 표시를 검증. 보고 분기 holdings와 현재 매매/현재 보유를 구분하고 기존 companyfacts 수집 성공으로 대체하지 않음. |
| 14. 뉴스 출처 조사 | 코덱2·사용자 | 공식 공시/IR/RSS/API 후보와 링크/본문 저장·재사용권·범위/시각 확인 | **연구 로직 일부 있음·공급자 미선택** — NEWS_NO_SOURCE | 출처별 이용·저장/재배포·시각·정정/중복·회사 결속 비교 문서와 실행 가능한 무료 후보를 제시. 조사만으로 본문 수집·점수 가산·QGV 변경을 시작하지 않음. |
| 15. 모델 포트폴리오·6관점 정의 | 사용자(정의)·코덱2(계약)·코덱1(화면) | **6관점의 이름/목적/원본 입력/기존 TARGET·Model·Actual·Gap 대응을 사용자 확정**; 4의 preview와 모델 적용 구분 | **기존 portfolio 계약·TARGET/ACTUAL 있음·새 정의 대기** | 확정6관점 및 기존 StrategyVersion/snapshot의 모델 포트폴리오 계약·비교 표시 명세가 있음. 실제 보유와 모델을 혼동하지 않고 새 종합점수·권장 비중·방법론/가중치를 임의 생성하지 않음. |
| 16. 모의투자/전진검증 시작일(사용자 결정) | 사용자·코덱2(검증)·코덱1(기록/화면) | 사용자 시작 시점·대상·전략버전·입력 cutoff·예측/관측·결측/중단 처리·허용 보관 범위 결정 | **시작일 미정·대기**, QGV v2 보류 | 사용자 결정 기록 후 향후 축적 데이터만 별도 forward namespace로 검증. 시작일/기간을 에이전트가 선택·소급하지 않고 기존 Holdout은 UNCONFIRMED·미사용 유지. Preview/Sandbox/Backtest/Forward 결과를 구분. |
| 17. M3 개인 부분집합 기기 연결 | 코덱1·사용자 | #106·#110 계약, 기기 ★·비공개 Universe 1회 readonly 조회, SEC shares×동일행 price의 identity/통화/단위·basis 근거 | **Python 완료·기기 연결 대기** | TARGET19 + ★ + 검증 시총 상위N(N=20 기본)을 기기에서 선택; 10% 이상 일반 불일치와 근거 있는 SHARE_CLASS_BASIS를 구분하고 자동 보정 없음. private 결과/시트 ID·파생 membership 저장/공개 없음. |
| 18. 기술 계산/Research 표시 연결 | 사용자(코드 병합)·코덱2(Python)·코덱1(표시) | #111·#115 병합 승인, CSP 회귀 해소, 1의 합법적인 일봉·시장 세션/basis | **코드 PR 완성·미병합**, 현재 합성 검증 범위 | 현행 세 계산과 표시 지표를 분리하고 #115의 승인된 기본값만 연결. role=RESEARCH_DISPLAY_ONLY, warm-up null·0 대체 없음·Model/TSV/QGV 입력 금지. 실제 입력 gate 확장은 별도 검토 후 코드 PR 승인. |

## 추천 순서와 변경 제안

기본은 **1→2→3→4→5→6→7→8→9→10→11→12→13→14→15→16**이며 17·18은 관련 연결 작업에 병행한다. 날짜·기간·새 방법론을 이 순서로 확정하지 않는다.

1. **6→5(8축 최종 연결 완료)로 변경 제안.** 5의 입출력 계약/첫4축 표시 작업은 먼저 또는 병행할 수 있지만, 실제8축 종료 조건은 나머지4축 입력·의미 대응이 있어야 충족된다. 조사 완료나48칸 배열을 전체 국면 완료로 세지 않는다. 권고 실행 순서는1→2→3→4→6→5→7 이후 기본 순서다.
2. **10의 권리·지원 조건 검토를1과 병행.** 본 경로가 허가/coverage 미확인으로 막히면 예비 출처 확인이1의 선행 조건이다. 전체 fallback 구현의 기본 위치10은 유지하며 허가 없는 가격 호출로1을 완료하지 않는다.
3. 8은 사용자 등록 알림 전 비착수 대기열이다. 그동안9 이후의 독립 조사/계약 준비와7의 기존 백업 검증을 진행할 수 있다. 2의 SEC 재무 취득도1의 가격 연결을 기다릴 데이터 의존성이 없다. 15의6관점 정의는4의 preview 용어 정리와 병행하되 모델 계산 채택으로 확대하지 않는다.

## 사용자 결정·조치가 필요한 항목

아래는 아직 필요한 선택/조치다. 이미 확정된 N=20·10%, 표시용 지표 period, 무료 원기관 원칙, Holdout 미사용을 다시 확인 요청하지 않는다. 기술 표시 결정 GSQ-015는 #115에 기록돼 canonical 병합 대기다.

| 결정·조치 | 필요한 내용 | 연결 항목/결정 전 경계 |
| --- | --- | --- |
| 코드 PR 병합 | #111·#115 각각 병합 승인 | 18. CSP 회귀 해소와 최종 canonical/체크 확인 전 병합하지 않음. 이번 문서 PR과 분리. |
| SEC 운영 범위 | 실제 취득 대상(현재 US17 부분집합부터), 일일 실행시각/예산·보존 위치·공개 출력 범위 및 실행 승인 | 2. 사용자 연락처는 설정에만 두며 공개 로그에 출력하지 않음. 기기 선정 목록을 Actions 대상으로 역전송하지 않음. |
| V 재계산 정책 | 기존 V의 정확한 입력시점·가격 변경 시 무효화/재계산 및 P02 중간시점 처리 | 3. 새 산식/가중치를 에이전트가 제안값으로 적용하지 않음. |
| Macro 후속 입력 채택 | 나머지4축의 정확한 자료·series/단위/SA 여부와 기존 상태 의미의 대응. 특히 Credit 후보가 기존 spread와 동등한지, FX 보관의 허용 범위 | 6→5. H.8/SLOOS를 HY spread로 대체하거나 ‘순유동성’·새 국면 규칙을 만들지 않음. |
| 추가 백업·Trades 계약 | 기존 백업 확인 후 필요한 추가 범위, Trades 열/시간대/정정·개인 거래 보관/백업 범위 | 7·11. 토큰/키/시트 ID·새 가격 파생값/M3 결과는 제외. |
| DART 등록 알림 | **10/11 18시 이후 등록 완료 알림**. 시간 도달만으로 알림/허가로 간주하지 않음 | 8. 알림 전 코드·키 존재 확인·인증/API 착수 금지. |
| EDINET 등록 | API v2 이용등록·키 설정/약관·문서/숫자 parser 범위 | 9. 키 값을 저장소/대화에 제출받지 않음. |
| 가격 예비 조건 | Tiingo 계정의 무료 범위/한도/권리·KRX 이용조건/지원, 일본 본상장 일봉 출처 | 1·10. KRX 등록 보고를 인증·허가·3시장 coverage 완료로 간주하지 않음. |
| 실적/13F/뉴스 범위 | 실적 출처의 대상·예정/확정 처리, 13F 추적기관 집합, 뉴스 후보·본문/링크 이용 범위 | 12·13·14. 조사→계약→승인된 수집의 범위를 구분. |
| 모델 포트폴리오·6관점 | 6관점의 정확한 정의/기존 계약 대응과 모델 표시·적용 구분 | 4·15. 기존 PROVISIONAL 프로필 숫자를 공식 모델로 승격하지 않음. |
| 모의투자/forward 시작 | 시작 시점·대상/전략버전·입력/결과 보관·검증 규약; v2 착수 여부 | 16. 사용자 결정 전 시작/기간 선택 없음, 기존 Holdout 미사용. |

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
- #93 정리, #94 구현 명세, GSQ-011 원기관 4축 채택과 Holdout metadata 확인이 후속 문서였다. 현재 Macro 입력 코드 #104, M3 #106·#110, 나머지 Macro 조사 #112와 열린 #111·#115의 상태는 위 표에 반영했다.
- 과거 운영 검증 절차의 상세 표와 영수증은 이력으로 남긴다. #100의 1인용 운영 종료 결정을 이번 계획의 승인 차단으로 되돌리지 않는다.
