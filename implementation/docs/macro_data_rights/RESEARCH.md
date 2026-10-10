# 매크로 8축 입력 후보의 권리와 PIT 경로

확인일: **2026-10-10 UTC**. 기준 canonical: `ee039041ae7f5cb94e6a127930c7e43effb811ec` (#93 병합 후). 코덱2의 문서 조사다. 공급자·지표 채택, 수집·보관·계산 실행 및 공개 게시를 승인하는 문서가 아니다.

**추천 경로는 원기관의 무료 공식 자료를 본인 환경에서 처리하고, 당시 발표본을 입증할 수 있는 입력만 PIT 연구 후보로 분리하는 것이다.** FRED/ALFRED의 접근 약관과 원기관 자료의 재사용권은 별도로 확인해야 한다. 무료·본인 전용(GSQ-007)은 공급자 제한의 예외가 아니다. 권리 확인이 끝나도 8축 producer·adapter·검증 gate는 남는다.

## 1. 현행 기준과 8축의 의미

[Macro 후보 기록](../../../Macro%20System%20%C2%B7%20Latest%20Consolidated%20Record%20v0.1.4%20Candidate.md) §15의 축은 **Growth / Inflation / Liquidity / Monetary Policy / Credit / Labor / Fiscal / FX**다. 각 축의 **Level / Direction / Momentum / Surprise / Stress / Confidence**는 서로 다른 출력이다. 아래 표는 원재료 탐색 목록이며 새 지표군·가중치·계산식·승격 결정이 아니다.

현행 [fred_csv.py](../../src/investment_system/providers/fred_csv.py)의 `SERIES`는 `growth=INDPRO`, `inflation=CPIAUCSL`, `rates=DGS10`, `liquidity=WALCL`, `risk=BAMLH0A0HYM2`의 **5개 PROVISIONAL 매핑**이다. Rates/Risk를 Monetary Policy/Credit으로 이름만 바꿔 8축 완성으로 표시하지 않는다. [MacroEngine](../../src/investment_system/macro/engine.py)은 v0.1.1이며 v0.1.4-CANDIDATE를 기본 계산으로 적용하지 않는다. [producer adapter](../../src/investment_system/producers/adapters.py)의 `macro_section`은 `environment.indicators`와 Web `indicators/exposures`의 불일치 때문에 거부한다.

| 축 | 공식 원기관 입력 후보 | FRED/ALFRED 경유 후보 | 권리·PIT 검토 후에도 남는 범위 |
| --- | --- | --- | --- |
| Growth | BEA GDP·실질 소비; Federal Reserve G.17 산업생산 | GDP/GDPC1, INDPRO | 월/분기 및 실질/명목·계절조정 구별. 현행 INDPRO와 GDP는 같은 입력이 아니므로 자동 교체 불가. |
| Inflation | BLS CPI; BEA PCE 가격지수 | CPIAUCSL, PCEPI/PCEPILFE | CPI/PCE와 전체/core의 차이, 개정·기준변경·발표본 및 계절조정 vintage. |
| Liquidity | Fed H.4.1 대차대조표·H.8 은행 자산/부채; Treasury Daily Treasury Statement의 현금 잔액 | WALCL, WRESBAL, WTREGEN | 주/일 빈도·잔액 정의·보고 cutoff 차이. 중앙은행 잔액과 Treasury 현금을 하나의 수치로 합성하지 않음. |
| Monetary Policy | FOMC 공식 결정·시행일, NY Fed EFFR; Fed H.15 금리 | DFEDTARL/DFEDTARU, EFFR/DFF, DGS10 | 정책목표와 실효금리·국채수익률은 다른 입력. DGS10만으로 정책축을 완성하지 않음. |
| Credit | Fed H.8 은행대출·SLOOS 대출기준 | TOTBKCR 등; 기존 BAMLH0A0HYM2는 ICE 제공 자료 | 대출량/기준과 HY spread의 경제적 의미는 다름. ICE 제약을 피하려 지표를 대체·새 Credit 산식으로 채우지 않음. 가격 기반 시장지표는 개인 경계 적용. |
| Labor | BLS CES 고용·CPS 실업; 필요 시 DOL 실업수당 자료는 추가 기관 검토 | PAYEMS, UNRATE | CES/CPS 표본·기간·개정 차이. 고용의 관측월과 발표시각 분리. DOL은 이 문서의 권리 확인 완료 기관에 포함하지 않음. |
| Fiscal | Treasury MTS 수입·지출·수지, Debt to the Penny; BEA 정부 지출 | FYFSD, GFDEBTN 등 | fiscal/calendar period·현금/발생 기준·지표 coverage 구별. 오늘 부채를 과거 빈티지로 재사용하지 않음. |
| FX | Federal Reserve H.10 환율·달러지수 | DTWEXBGS, DEX 계열 | 지수와 개별 통화쌍, 원 단위·기준시각·개정 vintage 구별. Yahoo FX/유료 벤더를 암묵적으로 추가하지 않음. |

후보 ID는 제공 문서의 탐색 식별자다. 개별 series의 존재·계정 권한·ALFRED vintage coverage·현재 응답·완전성을 실제 API로 확인한 결과가 아니다. 미국 공식 자료만으로 한국·일본·글로벌 8축 coverage까지 확보됐다고 표시하지 않는다.

Surprise에는 당시 기대/consensus의 출처·권리·공개시각이 추가로 필요하다. 위 실측 통계만으로 기대값·surprise를 만들지 않는다. Direction/Momentum/Stress/Confidence도 입력 가용성만으로 계산 규칙이 승인되지 않는다. 미구현·미검증 칸은 `NOT_AVAILABLE`을 유지한다.

## 2. 저장·변환·재배포 판정 기준

저장은 개인 디스크·DB·archive/cache, 변환은 단위·형식 및 기존 승인 계산, 재배포는 공개 Git·Pages·JSON·Actions 산출물과 제3자 전달을 포함해 각각 판정한다. 기관 로고·사진·제3자 저작물은 통계 수치와 별도다. 출처를 표시해도 금지된 접근·저장·배포가 허용되지는 않는다.

본인 Worker는 개인 환경이지만 공급자가 허용하지 않은 서버 접근을 승인하는 근거가 아니다. Workers Free·비용 0·카드 없음, GSQ-008의 본인 인증·토큰 비보존 원칙을 유지한다. 매크로 공공 통계의 보관 가능성은 가격·가격 기반 V/QGV·시총/순위의 공개 또는 지속 저장 승인으로 확장하지 않는다.

## 3. PIT와 빈티지를 구분하는 입력 계약

후속 구현은 입력마다 원기관/series, 원 단위·빈도·조정 기준, 관측기간, 원 발표시각/시간대, vintage와 revision 관계, 실제 `available_at` 근거, `acquired_at`, 원자료 hash, 권리 원문 URL·확인일·적용 범위를 결속해야 한다. 이번 문서는 기존 schema를 수정하지 않는다.

- **현재 revised API/CSV**: 과거 날짜 행이 있어도 당시 이용 가능 값이라는 증거가 아니다. 현재 맥락 후보와 strict PIT 연구를 분리한다.
- **발표본 archive**: 당시 공개된 PDF/표/원자료와 정확한 발표시각을 결속할 때 후보가 된다. 수정본이 원본을 덮었거나 다운로드만 존재하면 PIT를 확정하지 않는다.
- **ALFRED realtime/vintage**: 일 단위 vintage 선택 기능이다. intraday 공개시각·원기관 최초 공개·모든 시리즈의 모든 빈티지를 보장하지 않는다.
- **향후 본인 수집 receipt**: 실제 취득 후 알고 있던 사실을 증명할 수 있으나 이전 발표시각이나 수집 전 역사를 소급 복원하지 않는다. 원기관 저장 조건을 먼저 통과해야 한다.

`available_at <= decision_time`을 입증하지 못하는 입력은 strict PIT/OOS 경로에서 보류한다. observation date·download time을 발표시각으로 대신 넣거나 최신 revised 값으로 ALFRED 실패를 보충하지 않는다. [fred_alfred.py](../../src/investment_system/providers/fred_alfred.py)의 날짜를 UTC 자정으로 만드는 현행 parser, module cache 및 역사 helper의 최신 CSV fallback은 새 권리/PIT 경로의 통과 증거가 아니다. 함수를 import/실행하거나 키 파일을 확인하지 않았다.

## 4. 무료·본인 전용 경로의 단계와 남은 결정

1. 기관 자체 공공 통계를 우선 검토하고, 입력별 정확한 권리·단위·발표/개정 근거를 결속한다. FRED 제한을 원기관 public-domain 판정으로 우회하지 않는다.
2. 현재 맥락용 자료와 PIT 연구 자료를 별도 상태로 유지한다. 당시 발표본이 없는 입력에는 `PIT_NOT_VERIFIED`; 권리가 미확인인 입력에는 `RIGHTS_UNCONFIRMED` 이유를 남긴다. 이는 후속 sidecar의 제안이며 기존 enum 추가가 아니다.
3. 저장 허용 공식 통계만 본인 저장소의 원문/receipt 보존 후보로 삼는다. 가격 경로는 GSQ-007/008의 휘발성 개인 처리에 남긴다. 시장 수익률·FX 등도 해당 입력이 가격/가격 기반 파생값 경계에 들어가는지 먼저 판정하며, 원기관의 재사용 허용을 사용자 무저장/공개 금지의 예외로 삼지 않는다. 공개 연구 결과도 개별 배포권·producer/게시 gate가 끝날 때까지 게시하지 않는다.
4. 원기관 후보가 현행 입력과 동등하지 않으면 누락을 유지한다. 채택/교체·8축 producer·adapter 구현은 별도 범위다. ICE credit 및 당시 consensus gap은 `NOT_AVAILABLE`로 남기는 경로가 무료 조건에 맞는다.

사용자 결정이 필요한 후속 항목은 **이 원기관 우선 후보 경로의 채택과 실제 구현 범위**다. 이번 조사·문서 병합에는 추가 결정이 필요하지 않다. 무료·본인 전용 전제로 FRED/ALFRED 저장·AI 경로를 자동 허용하거나, Holdout·새 방법론·가중치를 선택하지 않는다.

## 5. 공식 근거 확인 기록

기관별 저장·변환·재배포·개인/AI 조건과 공식 원문은 [FRED·ALFRED 근거](FRED_ALFRED_EVIDENCE.md), [원기관 근거](PRIMARY_AGENCY_EVIDENCE.md)에 기록한다. 실제 통계·가격 API·공급자 인증 호출은 수행하지 않았다.

| 출처 | 저장 | 변환/기존 계산 | 재배포 | 무료·본인 이용 / AI | PIT·빈티지 |
| --- | --- | --- | --- | --- | --- |
| FRED / ALFRED | 일반 (p), API (l)의 저장/cache/archive/DB 금지와 개인 다운로드 라이선스의 범위 충돌이 남음. 서면 확인 전 차단 | 일반 (q), API (k)의 개발/훈련 제한. 기존 코드 존재로 허용 안 됨 | 시리즈 원권리자 조건 + FRED 조건 모두 필요. 공개 경로 미허가 | 개인 비상업 라이선스는 금지 조항에 종속. AI 모든 추론 금지라고 단정하지 않지만 독자적 개발/훈련·저장 경로는 미허가 | 날짜 단위 vintage 확인; 장중/원기관 최초 공개시각·개별 coverage 미확인 |
| BLS 직접 | 정부 작성 통계의 공개 재사용 근거; 사진/삽화 예외 | 허용 후보. 자체 변형 결과를 BLS 원본이라고 표기 금지 | public domain 근거; 출처·조회일·지정 면책문구·제3자 예외 적용 | 공개 API 한도 준수. end-use controls 없다는 명시 근거; AI 전용 보증은 아님 | 현재 API ≠ as-of vintage. 발표 archive·예정 일정과 실제 발표본/시각 별도 확인 |
| BEA 직접 | 별도 고지 없는 정부 정보의 use/reproduce 근거 | API는 analyze/service 개발 허용. 변형 결과를 BEA 원본이라고 claim 금지 | 공개 재사용 근거 + API 지정 비후원 notice. 외부 linked 저작권 예외 | 무료 public API 등록/약관·동적 한도 적용. 별도 AI 훈련 보증 아님 | current API/iTable 과거기간 ≠ 당시 값. release/data archive·GDP/GDI vintage 후보의 coverage 추가 확인 |
| Treasury FiscalData 직접 | copy/otherwise use 명시 허용 근거 | adapt 명시 허용 | redistribute, 비상업/상업 명시 허용. FiscalData 데이터 범위 | free without restriction, 계정/token 등록 불필요. 숫자 quota 미확인; AI 전용 보증 아님 | record_date·API v1/v2는 vintage 아님. release calendar는 예정 시각 |
| Treasury Daily Yields 직접 | feed 공개는 확인; 독립 재사용 license 미확인 | 별도 허용 원문 미확인 | FiscalData 허용을 이식하지 않음 | 공개 문서와 feed 설명을 무제한 이용권/AI 허가로 해석하지 않음 | 입력 quote 시각과 공개시각 다름; 지연·역사 backfill. 모든 vintage 지원 미확인 |
| Federal Reserve Board 직접 | 별도 표시 없는 정부 정보 copy/public domain | 해당 범위의 분석·변환 후보; 특정 모델/외부 자료 예외 | permission 없이 copy/distribute; Board 출처 표기, 외부자료·로고 예외 | DDP 자동 다운로드 설명; 무제한 서비스 보장이나 AI 전용 보증 아님 | DDP는 최신값. release archive는 자료군별 검증 필요; FOMC 일부 문서는 장기 공개 지연 |
| NY Fed 직접 | Download/store 명시 허용, 콘텐츠별 조건 적용 | modify/derivative works 허용; 변경 명시·왜곡/원본 귀속 금지 | 동일 조건·attribution·원문 링크 및 reference-rate notice 적용 | 개인/사업 허용, 정상 자동 접근. 제3자·permissioned content 별도; AI 전용 보증 아님 | API 최신 implementation·revisionIndicator ≠ 전체 빈티지. 당일 수정·지연 공개/backfill 별도 |

FRED Legal API (k)는 “development or training of any software program or system or machine learning”, (l)는 “storing, caching, or archiving”을 제한한다. 별도 API Terms 페이지가 더 짧더라도 Website Legal을 포함하므로 구형 페이지를 허가 근거로 삼지 않는다. 기관의 **public-domain 자료 권리와 API 서비스 접근 조건은 서로 다른 판정**이다.

ICE 유형의 `Copyrighted: Pre-approval required`도 FRED Legal III에서 비상업 교육·본인 개인 이용을 제한적으로 설명한다. 유형 이름만으로 개인 열람 자체가 불가하다고 단정하지 않는다. 그 개인 예외가 이 프로젝트의 API 개발·cache·공개 배포까지 허용하지는 않는다. BAMLH0A0HYM2 최신 notes 전문은 이번에 재조회하지 않았고, 기존 2026-10-09 근거와 현재 일반 약관을 구분해 기록했다.
