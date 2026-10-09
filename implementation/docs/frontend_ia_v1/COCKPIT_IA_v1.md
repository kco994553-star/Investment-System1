# Investment-System1 · Cockpit IA v1

기준일: 2026-10-09 · 기준 canonical: `13e025b0e545fb3da14c15ce065a6a8e4a368eb0` (PR #73 승인 병합 이후) · 범위: 정보구조·화면 요구사항 문서만 · 사용자 PR 병합 승인 필요

이 문서는 Cockpit의 새 화면·탐색 구조 기준이다. 구현 완료, 데이터 가용성, 모델 검증, 운영 적격성 또는 투자성과를 인증하지 않는다. 코드·데이터·계산·계약·워크플로·자동화 control을 변경하지 않는다. 사용자 병합 전에는 제안 문서이며, 병합 후에도 구현·배포 권한을 부여하지 않는다. 디자인 출처 및 접근 경계는 [DESIGN_SOURCE.md](DESIGN_SOURCE.md)를 따른다.

## 1. 목적과 판단 순서

사용자는 **QGV → 기술적 분석 → 매크로 → 검증·연구** 순서로 기업의 질·성장·가치, 가격 상태·실행 환경, 거시 맥락, 판단의 검증 근거를 확인한다. 오늘(홈)은 이 네 목적의 요약과 다음 확인 지점을 제공한다. 홈 요약은 독립 엔진을 새로 만들거나 각 원본 판단을 합산하는 계산기가 아니다.

| 구분 | 반드시 지킬 표현·동작 경계 |
|---|---|
| TARGET / ACTUAL | 목표비중과 실제 보유·평가를 별도 표시한다. 목표를 실제 보유로 복사하지 않는다. |
| 결측 / 0 | 값 없음은 0이 아니다. 값·시점·출처가 없으면 이유와 `NOT_AVAILABLE`을 표시한다. |
| 확률 / 신뢰도 | 경로 발생확률과 근거·모델 신뢰도를 별도 필드로 표시한다. 신뢰도를 확률로 바꾸지 않는다. |
| 연구용 / 모델 | Research 도구와 실제 Model 채택 지표·판단을 분리한다. 화면 존재만으로 모델 채택을 주장하지 않는다. |
| 백테스트 / 전진검증 | 과거 재생, OOS, 현재 시점에서 동결한 예측 이후 관찰을 한 성과곡선으로 섞지 않는다. |
| QGV / 기술 | QGV 방향·기본적 평가와 기술적 가격상태·경로 판단은 독립이다. 합산 점수 또는 공식 Fusion 점수를 새로 만들지 않는다. |
| 매크로 / QGV 원점수 | 거시 맥락을 원점수에 더하거나 덮어쓰지 않는다. QGV Base와 Macro Context를 함께 보존한다. |
| 분석 / 주문 | 실행 구간·진입·축소·대기 문구는 읽기 전용 분석이다. 주문·매매·자동 리밸런싱 기능이 아니다. |

### 1.1 독립 분류축

GICS(산업), 전략 테마, 투자 유형은 서로 다른 세 축이다. 테마를 GICS 산업분류로 사용하지 않는다. 유형 중복을 산업 비중이나 전략 테마 목표비중과 같은 분모로 숨기지 않는다. 분류·스냅샷·버전·가중치 기준이 없으면 분류를 종목명에서 추정하지 않는다. 과거 화면은 당시 근거가 있는 분류만 사용한다.

### 1.2 요구사항 상태와 실제 상태

이 문서에 식별된 화면·항목의 요구사항 상태는 모두 `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`다. 이는 “요구사항 확인, 현재 구현 미재감사”를 뜻한다. 현재 값·근거·세부 시안이 제공되지 않은 항목은 `NOT_AVAILABLE`이다. 이 두 상태는 데이터 표시 배지와 별개다. 구현률·검증률·잔고·확률·가중치를 임의로 채우지 않는다. 기존 문서의 과거 PASS·진행률을 이 문서 기준일의 완료 상태로 가져오지 않는다.

## 2. 공통 탐색·표시 규칙

| 항목 | IA v1 요구사항 |
|---|---|
| 모바일 기준 | 390px. 하단 메뉴 5개: 오늘 / QGV / 기술 / 매크로 / 검증. 상세 화면에서 상위 화면으로 돌아갈 수 있어야 한다. |
| PC 기준 | 1440px. 좌측 사이드바: 오늘 / QGV(내 투자·종목 찾기·시장 정보·성과) / 기술 / 매크로 / 검증. |
| 설정 진입 | 오늘 화면 우측 상단 설정 아이콘 → 계정·금융기록·설정(S11). 여섯 번째 하단 메뉴로 만들지 않는다. |
| 종목 공통 진입 | 검색·표·카드·관계망 등 어디서든 종목 선택 → 공통 종목(S04). QGV↔기술에서 동일 기업·기준시점 맥락을 유지한다. |
| 언어 | UI 설명·도움말·상태 이유는 한국어. 차트 축·마커·범례 코드와 E/P/L/M/S는 영어 표기를 유지한다. 코드의 의미를 근거 없이 새로 정의하지 않는다. |
| 데이터 배지 | `LIVE` / `FROZEN_SNAPSHOT` / `DEMO` / `NOT_AVAILABLE`. 명시적 원본 메타데이터가 없으면 LIVE를 주장하지 않는다. |
| 신선도 | `FRESH` / `STALE` / `NOT_USABLE` / `NOT_APPLICABLE`. 데이터 종류 배지와 독립 표시한다. 낡은 값을 최신으로 보이게 하지 않는다. |
| 데이터 기준 | as_of, available_at(제공될 때), source_refs, snapshot_id, 규칙·모델·분류 버전, 통화·가격 기준을 확인할 수 있어야 한다. 필드별 시점이 다르면 개별 표시한다. |
| 빈 상태 | 데이터 부족·부분·사용불가·명시적 빈 결과를 구분한다. 예시 숫자·가상 OHLC·임의 확률로 채우지 않는다. DEMO는 지속적으로 표기한다. |
| 내부 인프라 | Provider·SEC·PIT·Raw Map 등은 사용자 목적 메뉴로 노출하지 않는다. 근거 상세에서는 필요한 출처·가용성만 읽기 전용으로 제공한다. |

데이터 배지·신선도는 표시 요구사항이며, 기존 producer 메타데이터를 임의 변환하는 승인된 새 계약이 아니다. 실제 원본 상태에 매핑할 수 없으면 상태 의미를 숨기지 않고 `NOT_AVAILABLE`과 이유를 남긴다.

## 3. 12개 화면 맵

아래는 요구사항 목록이다. 모든 행의 상태는 `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`이며, 사용 가능한 데이터를 보증하지 않는다.

| ID | 화면 | 진입 | 필수 정보·구조 |
|---|---|---|---|
| S01 | 오늘(홈) | 하단 메뉴 오늘 | 통합 판단 카드(QGV·기술·매크로 신호, 규칙 버전), 목표 vs 실제·집중도, 주의할 것, 많이 벗어난 종목, 시스템 4개 상태, 데이터 기준 |
| S02 | QGV 허브 | 하단 메뉴 QGV | 내 투자(포트폴리오·전략프로필·모델포트폴리오·계좌연결·모의투자) / 종목 찾기(기업분석·리더보드·전체기업·관심기업) / 시장 정보(뉴스·관계망·13F) / 성과(Track Record). 각 항목의 사용 가능·부분·준비중 표시 요구 |
| S03 | 포트폴리오 상세 | S02 | 분기 선택, TARGET/ACTUAL 배지, 요약 8칸, 분기 필수 시각화 3개(GICS 도넛·투자 유형 도넛·유형 중복), 테마 목표 vs 실제, 보유표 12열·가로 스크롤 |
| S04 | 공통 종목 | 어디서든 종목 선택 | 시총순위·가격·상태 배지, 3축 분류, 내 보유, QGV 카드, 기술 요약, 매크로 영향, 뉴스, 가격 맥락, Track Record, 13F |
| S05 | 기업분석 | S04 | 사업·경쟁(점유율·사업구성·경쟁사), 재무 추이, 주가·이벤트(기간별 수익률·이벤트 차트·VMR 11개), QGV 요소(v1 가중치 표시만), 가치·시나리오, 동인·위험, 컨센서스(증권사별), 기업 Track Record D+5/20/63/252 |
| S06 | 리더보드 | S02 | 기본/내 프로필, 필터 8개, 9열 순위표, 재평가 정상·관찰·근접·재평가, 과거 순위·기업 비교·QGV 수정·코호트 성과 |
| S07 | 뉴스·관계망 | S02 | 뉴스 카드(상태·구조적/일시적 호재/악재·범위·영향 6항목), 관계망 그래프, 잠재 영향경로. Investment Overlay 기본 OFF |
| S08 | 기술적 분석 | 하단 메뉴 기술 | 차트 / 상태 / 실행 / 기록, 지표군 6개(추세·모멘텀·거래량·상대강도·구조·변동성), 모델/연구용 구분, 시나리오 경로(확률·신뢰도·무효화), 실행 구간. 주문 기능이 아닌 읽기 전용 분석 |
| S09 | 매크로 | 하단 메뉴 매크로 | 정상·경고·비상, 국면, 공식 8축 Growth·Inflation·Liquidity·Monetary Policy·Credit·Labor·Fiscal·FX와 축별 6상태 보존·단일 점수 없음(임금은 Labor, 생산성은 Growth의 세부 지표), 주식시장 상태 참고 카드(거시 축 아님), 국면 이력, 신호→근거, 시나리오, 전달 요인→경제→업종→기업→QGV, 업종 영향, 포트폴리오 매크로 노출 candidate |
| S10 | 검증·연구 | 하단 메뉴 검증 | 모의투자 / 백테스트 / 전진검증 / Track Record / 실험기록 / 리서치, 기준값 100 자산곡선·series on/off, 지표 6개, 분기 성과, calibration, Track A 기준선. Holdout 사용 선택 아님 |
| S11 | 계정·금융기록·설정 | 홈 우측 설정 아이콘 | 일반 계정 로그인 준비중, 별도 선택형 Google 시트 시세 인증(기본 OFF), 계좌 마지막 4자리만, 보유/거래/현금, 대사 6상태, append-only 변경 이력, 주문 불가 안내, 수동 시세·일괄 붙여넣기, 시트 ID/범위 기기 내만·메모리 토큰·백업 제외·백업/삭제 |
| S12 | PC 홈 | PC | 좌측 사이드바 오늘 / QGV 4하위 그룹 / 기술 / 매크로 / 검증, S01 내용 + 이탈표·변동 종목 |

### 3.1 S01·S12: 요약은 판단을 합치지 않는다

통합 판단 카드에는 QGV·기술·매크로의 개별 신호와 충돌/일치의 이유, 근거 시점, 사용 규칙 버전을 남긴다. 네 시스템 상태는 QGV·기술·매크로·상위 통합을 별도로 보여주며 새 완료율을 산출하지 않는다. 주의할 것과 많이 벗어난 종목은 제공된 근거가 있을 때만 표시한다. TARGET, ACTUAL, 집중도는 분리하며 ACTUAL 결측을 목표로 대체하지 않는다. S12의 이탈표·변동 종목도 같은 원본과 표시 규칙을 사용한다.

### 3.2 S02: 목적별 허브와 준비 상태

사용 가능·부분·준비중은 각 항목에 필요하다는 **표시 요구사항**이다. 이 문서는 어느 항목이 현재 사용 가능한지 판정하지 않는다. 실제 재감사 없이 완료 배지를 부여하지 않는다. 모의투자의 QGV 진입과 S10의 검증·연구 진입을 연결하되 모의투자를 백테스트로 재명명하지 않는다.

전략프로필·모델포트폴리오·관심기업·13F 상세 화면의 세부 시안은 `OPEN`이며 `NOT_AVAILABLE`이다. S02·S04에 진입 목적을 남겨 두되 12개 시안에 상세 화면이 있다고 주장하거나 임의 상세 화면을 구현하지 않는다. 계좌연결은 S11의 계정·기록 경계를 따르고 실제 금융기관 연결 완료를 뜻하지 않는다.

### 3.3 S03: 분기·분류·실제 보유

분기 선택은 해당 분기의 immutable snapshot에 연결한다. GICS 도넛, 투자 유형 도넛, 유형 중복의 세 시각화는 **매 분기 필수**다. 전략 테마 목표 vs 실제는 GICS 도넛을 대체하지 않는다. 유형의 중복 노출은 합계가 100%를 넘을 수 있음을 설명하고, 단일 유형으로 강제 배정하거나 동일 분할·정규화 정책을 만들지 않는다. 유형 도넛의 중복 표현·분모는 기존 근거와 시안 정합성을 확인해야 하며 미확정 계산법은 채택하지 않는다.

요약은 8칸, 보유표는 12열을 유지한다. 기존 사양의 보유 항목(기업명·티커·시총순위, 수량, 평단, 현재가, 평가액, 실제/목표비중, 괴리, QGV, 신뢰도)은 이관 검토 대상이며 이번 사용자 지시로 정확한 열 조합이 확정된 것은 아니다. 정확한 8칸 이름·12열 결합 배치의 재감사 상태는 `NOT_AVAILABLE`이다. 모바일에서는 표 내부 가로 스크롤을 허용하되 전체 화면 가로 넘침은 방지한다. 보유 수량·가격·환율 근거가 없으면 실제 평가액·수익률·비중을 만들어내지 않는다.

### 3.4 S04·S05: 종목 맥락과 기업 근거

시총순위는 QGV 리더보드 순위가 아니다. 공통 종목에서 기업 식별자·가격 기준시점·분류축·내 보유·원본 판단을 유지하고, 기업분석은 세부 근거를 펼친다. QGV v1 요소별 가중치는 기존 기준의 **표시만** 허용하며 수정 UI·대안 가중치·새 점수식을 제안하지 않는다. 컨센서스는 증권사별 출처와 시점·관측 수를 보존하며 QGV 조건부 시나리오와 구분한다.

VMR 11개는 기존 리더보드 사양 §19의 1D/5D/20D return, 20D/60D/1Y realized volatility, Daily sigma, ATR(14)%, Beta, Volatility Percentile, Drawdown을 뜻한다. 기업·업종·시장 비교와 상세 계산 근거가 없으면 값을 채우지 않는다. 기간별 수익률·이벤트·사업구성·점유율·재무·동인·위험도 실제 근거의 표시이며 재계산이나 관계 추론이 아니다. D+5/20/63/252 결과는 당시 판단 스냅샷과 사후 관찰을 분리한다.

### 3.5 S06: 순위와 재평가

기본 QGV와 내 프로필 결과를 분리하고 사용한 profile·snapshot·version을 표시한다. 필터 8개와 순위표 9열은 화면 요구사항이다. 구체 필터·9열 결합 배치가 현재 제공된 세부 시안으로 재감사되지 않았으므로 `NOT_AVAILABLE`로 남긴다. 기존 사양의 추가 필터·열을 삭제한 것으로 해석하지 않는다(부록 A).

정상·관찰·근접·재평가는 `NORMAL` / `WATCH` / `NEAR_TRIGGER` / `REASSESS`를 표시하는 요구다. 근거 부족 `INSUFFICIENT_DATA`를 정상으로 바꾸지 않는다. 재평가는 기업 Fundamental 재검토이며 매수·매도 신호나 QGV 자동 변경이 아니다. Threshold 출처, 관측 변화, 실제 적용 기준, distance 등 미배치 상세 항목은 부록에서 이관을 확인한다. 과거 순위·기업 비교·QGV 수정·코호트 성과를 보존하되 결측을 0으로 정렬하지 않는다.

### 3.6 S07: 사실과 잠재 경로

뉴스 카드는 상태, 구조적/일시적 호재·악재, 영향 범위와 6개 영향 항목을 요구한다. 6항목의 세부 이름·계산은 제공 근거의 재감사 전 `NOT_AVAILABLE`로 남긴다. 뉴스의 사실, 예상/추론, 잠재 영향경로를 구분하고 잠재 경로를 확정된 관계로 저장하지 않는다. Investment Overlay는 기본 OFF이며 켜도 공식 투자점수·QGV 원점수·주문 권한을 만들지 않는다. 그래프 상세 상호작용의 누락 여부는 부록 A에서 보존·확인한다.

### 3.7 S08: 차트 먼저, 실행은 읽기 전용

차트 / 상태 / 실행 / 기록의 네 내부 탭을 사용하며 모바일에서는 차트 우선, 지표 상세 접기를 허용한다. 추세·모멘텀·거래량·상대강도·구조·변동성은 지표군 6개이지 새로운 공식 지표 6종 또는 새 종합점수의 승인 목록이 아니다. Model과 Research는 구분해 표시한다.

시나리오는 S=1~N 가변 경로이며 경로별 범위·근거·확률·신뢰도·무효화를 분리한다. 과거 경로 빈도·검증·calibration 근거가 없으면 정밀 확률을 임의 생성하지 않는다. 실행 구간·진입·추가·축소·대기·위험관리 표시는 **READ_ONLY 분석 전용 hard gate**를 유지한다. 주문 버튼·증권사 주문 전달·거래 실행·자동 승인으로 연결하지 않는다.

### 3.8 S09: 8축과 6상태

2026-10-09 사용자 결정은 [Macro System · Latest Consolidated Record v0.1.4 Candidate.md](../../../Macro%20System%20%C2%B7%20Latest%20Consolidated%20Record%20v0.1.4%20Candidate.md) §15의 기존 8축을 UI 기준으로 보존하는 것이다. 해당 절의 실제 본문에 8축과 아래 6상태가 존재함을 확인했다. 이는 모델·엔진 승격 또는 실데이터 완료의 결정이 아니다.

| 축 | UI 코드 | 보존할 상태 |
|---|---|---|
| 성장 | Growth | Level / Direction / Momentum / Surprise / Stress / Confidence |
| 물가 | Inflation | 동일 6상태 |
| 유동성 | Liquidity | 동일 6상태 |
| 통화정책 | Monetary Policy | 동일 6상태 |
| 신용 | Credit | 동일 6상태 |
| 노동 | Labor | 동일 6상태 |
| 재정 | Fiscal | 동일 6상태 |
| 외환 | FX | 동일 6상태 |

임금은 Labor의 하위 지표, 생산성은 Growth의 하위 지표다. 주식시장은 국면 확인용 참고 패널이며 추가 축이 아니다. 사용자는 시안의 8축 수정 완료를 보고했다(2026-10-09); 이 PR은 비공개 canvas 직접 재감사나 앱 구현 완료를 주장하지 않는다. 추가 축이 필요하면 별도 방법론 버전 검토를 거쳐야 하며 IA 수정만으로 추가하지 않는다. 단일 Macro Score로 의사결정을 수행하지 않는다.

정상·경고·비상, 복수 국면 분포·전환 이력, 신호→근거, 매크로 시나리오는 각각 구분한다. 전달은 요인→경제 채널→업종→기업→QGV Context이며 원점수 가산 경로가 아니다. lag와 duration, probability와 confidence를 구분한다. 포트폴리오 매크로 노출은 candidate 요구사항으로 표시하며 실구현·검증 또는 현금 비중 정책의 확정이 아니다.

### 3.9 S10: 검증 영역과 기준선

모의투자, 백테스트, 전진검증, Track Record, 실험기록, 리서치의 목적·기간·데이터 집합·규칙 버전을 명시한다. 동일 시작 기준값 100의 자산곡선과 series on/off, 지표 6개, 분기 성과, calibration을 요구한다. 100은 표시 기준값이지 실제 금액·성과 관측값이 아니다. 정확한 6개 지표 카드의 조합은 재감사 전 `NOT_AVAILABLE`이며 기존 사양의 추가 지표를 삭제하지 않는다.

Track A 기준선을 사용한다. 이 IA는 Holdout 사용을 선택하지 않았으며 Gate A·Holdout·모델 승격 권한을 열지 않는다. PIT available_at이 검증되지 않았으면 역사적 PIT 적격성을 주장하지 않는다. 당시 동결한 예측과 사후 결과를 분리하고, sample size·기간·원본 snapshot으로 연결할 수 있어야 한다. 실험 변경은 과거 결과를 보고 원본 규칙을 소급 수정하는 방식이 아니다.

### 3.10 S11: 개인정보·금융기록과 26E

일반 앱 계정 로그인·계좌 연결은 준비중이라는 시안 요구다. PR #73의 Google 인증은 본인 비공개 시트의 시세를 읽기 위한 별도 인증이며 앱 계정 로그인·계좌 연결·동기화의 완료를 뜻하지 않는다. 계좌는 마지막 4자리만 표시한다. 보유·거래·현금 기록과 수정 이유·변경 전후는 append-only 이력으로 보존한다. 실제 계좌번호·잔고·거래·키를 문서나 예시로 기록하지 않는다.

| 대사 코드 | 표시 의미·경계 |
|---|---|
| MATCH | 비교 가능한 근거가 일치하는 경우의 요구 상태 |
| MISMATCH | 비교 가능한 근거가 불일치하는 경우의 요구 상태 |
| NOT_AVAILABLE | 필요한 근거를 사용할 수 없음 |
| NOT_COMPARABLE | 기준·범위·시점 등이 달라 직접 비교할 수 없음 |
| PARTIAL | 일부 근거만 확인 가능 |
| NO_DATA | 데이터 없음. 대사 완료·일치 또는 확인된 0을 뜻하지 않음 |

2026-10-09 사용자 결정: **시세·환율 수동 입력 + KRW 기준**은 [PR #70](https://github.com/kco994553-star/Investment-System1/pull/70)에서 구현·기록 완료됐다. S11은 [기존 수동 입력·기기 저장·백업/삭제 상태](../manual_quotes_owner/README.md)를 연결한다. **Alpha Vantage는 REVIEW ONLY·API OFF**이며 [기존 검증 기록](../pr70_approved_owner/ALPHA_VANTAGE_FEASIBILITY_26E.md)을 상태 근거로 연결한다. 이번 문서 PR에서는 시세·환율 방식의 재선정·재연구·구현을 다루지 않는다.

같은 날 후속 결정으로 [PR #73](https://github.com/kco994553-star/Investment-System1/pull/73)이 승인 병합됐다. **Google 시트 연결은 선택 기능·기본 OFF**이며 Google에서 사용자 휴대폰으로 직접 읽는다. 사용자가 버튼을 누를 때만 Google Identity Services token client로 `https://www.googleapis.com/auth/spreadsheets.readonly` 하나를 요청하고, 시세 불러오기도 별도 버튼으로만 실행한다. 접근 토큰은 메모리에만 보관하며 약 1시간 뒤 만료 시 재연결한다. 연결 해제는 revoke와 메모리 삭제로 처리한다. 시트 ID/URL에서 추출한 ID와 범위는 기기 안에만 저장하고 백업에서 제외한다. 공개 OAuth 클라이언트 ID는 앱 설정값이며 client secret은 사용하지 않는다.

수동 입력은 유지하고 A~C열 일괄 붙여넣기는 로그인 없이 사용할 수 있다. 잘못된 값·`#N/A`는 `NOT_AVAILABLE`로 표시하고 기존 저장값을 보존한다. 도쿄일렉트론은 수동 입력을 유지한다. 출처는 `GOOGLEFINANCE · 최대 20분 지연 · 정보용`이며 시각 미확인 표시와 기존 7일 신선도 규칙을 따른다. 상세 설정은 [Google 시트 설정 안내](https://github.com/kco994553-star/Investment-System1/blob/13e025b0e545fb3da14c15ce065a6a8e4a368eb0/implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_SETUP.md), 결정은 [scoped append-only 기록](https://github.com/kco994553-star/Investment-System1/blob/13e025b0e545fb3da14c15ce065a6a8e4a368eb0/implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md), 기존 모의 검증과 한계는 [PR #73 검증 기록](https://github.com/kco994553-star/Investment-System1/blob/13e025b0e545fb3da14c15ce065a6a8e4a368eb0/implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_VERIFICATION.md)에 연결한다. 실제 계정 로그인·휴대폰 동작·공개 사이트 CSP의 이번 확인 결과는 이 문서 PR의 검증으로 주장하지 않는다.

시트 ID·접근 토큰·실제 보유·시세·환율·계좌·키 값은 저장소·공개 JSON·Pages·CI·로그에 기록하지 않는다. API 키가 필요한 별도 공급처는 기기 내만·백업 제외라는 기존 경계를 유지하며 Google 시트에는 API 키를 요구하지 않는다. 서버·중계·GitHub Actions 시세 수집·백그라운드·주기 호출은 없다. 한국투자증권·중계 서버는 `DEFERRED`이고 Alpha Vantage는 OFF다. 보유·거래·현금·대사·변경 이력은 읽기 전용 금융 기록 요구이며 계좌 연결·인증 구현 완료를 뜻하지 않는다. “주문 기능 없음” 안내와 READ_ONLY hard gate를 유지한다. 매수·매도·주문·이체·출금 기능을 설계하지 않는다. 원본 통화·입력 시점 등 실제 상태는 링크된 기존 기록을 기준으로 표시하고 결측은 `NOT_AVAILABLE`이다.

## 사용자 결정 기록 (2026-10-09)

- 매크로 축은 `Macro System · Latest Consolidated Record v0.1.4 Candidate.md` §15의 **기존 공식 8축을 유지**한다. 사용자 확인으로 시안도 8축으로 수정 완료됐다. 임금은 Labor, 생산성은 Growth의 세부 지표이며 주식시장 국면은 거시 축이 아닌 참고 카드다. 축 추가는 별도 방법론 버전에서만 다룬다. 축별 Level / Direction / Momentum / Surprise / Stress / Confidence의 6상태를 보존하며 단일 점수로 합치지 않는다.
- 시세·환율 최초 결정은 **수동 입력 + KRW 기준, PR #70 구현·기록 완료**다. Alpha Vantage는 **REVIEW ONLY·API OFF**다. 이번 PR은 이를 다시 검토하지 않으며 S11의 기존 기록 링크만 상태 근거로 사용한다.
- 후속 결정인 **선택형 Google 시트 직접 읽기·기본 OFF·수동 유지**는 PR #73 승인 병합 기록으로 연결한다. 일반 앱 계정 로그인과 시세 소스 인증은 별개다. 한국투자증권·중계 서버는 `DEFERRED`를 유지하며 이 문서 PR은 새 API·인증·주문 구현을 추가하지 않는다.

## OPEN — 상세 시안과 배치 확인

| 미정 항목 | 상태 | 사용자 결정·확인 필요 |
| --- | --- | --- |
| S02 전략 프로필 상세 화면 | OPEN · NOT_AVAILABLE | 시안 없음. 상세 화면 제공·배치 확인 필요 |
| S02 모델 포트폴리오 상세 화면 | OPEN · NOT_AVAILABLE | 시안 없음. 상세 화면 제공·배치 확인 필요 |
| S02 관심 기업 상세 화면 | OPEN · NOT_AVAILABLE | 시안 없음. 상세 화면 제공·배치 확인 필요 |
| S02 13F 상세 화면 | OPEN · NOT_AVAILABLE | 시안 없음. 상세 화면 제공·배치 확인 필요 |
| S03 요약 8칸·보유 12열, S06 필터 8개·순위 9열, S07 영향 6항목, S10 지표 6개의 정확한 원문 매핑 | OPEN · REQUIREMENT_IDENTIFIED_NOT_REAUDITED | 지정 개수는 유지하되 세부 명칭·결합 배치는 시안 및 기존 요구의 이관 확인 전 임의로 정하지 않음 |

## 4. 기존 스택과 시각 기준

| 영역 | 유지 기준 |
|---|---|
| 금융 시계열 차트 | 기존 Lightweight Charts 5.2.1. renderer는 데이터 공급자가 아니다. LICENSE/NOTICE·attribution 경계를 유지한다. |
| 도넛·겹침·관계·기타 도식 | 기존 native SVG 활용. 정확한 데이터 시각화에 생성 이미지를 사용하지 않는다. |
| 한글 글꼴 | Noto Sans KR. 저장소 chart lab의 패키지는 @fontsource/noto-sans-kr 5.3.0으로 고정되어 있다. |
| 브라우저 검증 | 기존 Playwright 1.58.2. 본 문서의 작성은 새 브라우저 테스트 완료를 뜻하지 않는다. |
| 구조 | 기존 정적·native JS/CSS 접근을 존중한다. 프레임워크·라이브러리 교체 또는 신규 설치를 결정하지 않는다. |

저장소 확인 근거: `implementation/experiments/chart-contract-v0.1/package.json`, `implementation/experiments/chart-contract-v0.1/README.md`. 실제 검증은 후속 구현 PR에서 390px·1440px, 종목 이동·뒤로·키보드 접근·빈 상태·시점·배지·표 내부 스크롤·차트 근거 보존을 대상으로 별도 수행한다. 이전 360/390·1280 검증을 새 1440px 합격으로 간주하지 않는다.

| 토큰 | 값 |
|---|---|
| bg | #F4F4EF |
| surface | #FFFFFF |
| border | #E2E2DA |
| text | #17201D |
| muted | #5E6863 |
| primary | #1E4D43 |
| primary-soft | #E3EEEA |
| warn / warn-bg | #7A4600 / #FBEAD2 |
| info / info-bg | #1D4A80 / #DDE8F6 |
| placeholder | #8A938F |

색상만으로 상태를 구분하지 않고 텍스트·이유·근거를 함께 제공한다. placeholder 색은 실제 0·정상·확정값의 대체 표현이 아니다.

## 5. 과거 IA 대체와 원문 보존

다음 경로는 저장소에서 실제 존재를 확인한 과거 IA/화면구조 기록이다. Markdown은 정확히 한 줄의 SUPERSEDED 안내만 맨 앞에 추가하고 이후 원문 바이트를 모두 보존한다. DOCX는 제목·본문·바이너리를 변경하지 않는다. 대체는 새 탐색·화면 기준에 한정되며 계약·수치방법론·owner 경계를 폐기하지 않는다.

| 기존 실제 경로(저장소 루트 기준) | 처리 |
|---|---|
| `Investment-System1 · Frontend Information Architecture 2026-09-23.md` | 한 줄 안내만 추가, 원문 보존 |
| `implementation/experiments/chart-contract-v0.1/reviews/frontend_architecture_review.md` | 한 줄 안내만 추가, 독립 검토 원문 보존 |
| `implementation/PRODUCT_ARCHITECTURE.md` | Product/UI 화면 매핑 기록에 한 줄 안내만 추가, 원문 보존 |
| `Investment-System1_Frontend_IA_2026-09-23.docx` | 다른 이름의 실제 legacy DOCX; 변경 없이 보존, 새 화면구조는 이 문서 참조 |

위 Markdown 제목과 완전히 같은 이름의 `.docx`는 이 기준 checkout에서 발견하지 못했다. 실제 DOCX를 가상의 같은 이름 경로로 바꾸거나 생성하지 않는다. 일반 시스템 아키텍처·도메인 사양·계약·검토 inventory는 SUPERSEDED 표시 대상으로 넓히지 않는다.

## 부록 A. 이관 확인 필요

다음은 기존 문서에 존재하지만 12개 화면 맵만으로 상세 배치·표현·승계가 확정되지 않은 요구사항이다. 삭제·불채택 목록이 아니다. 과거 IA의 구체 배치, 검토 문서의 품질조건, 도메인 사양의 확장 요구를 구분해 보존한다. 모두 `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`이며, 후속 결정 전 원문은 유지한다. 각 행은 관련 요구의 묶음으로서 독립 차트 수나 구현 완료율 분모가 아니다.

| ID | 이관 확인 필요 요구사항 | 원문 근거(실제 경로·절) | 후속 연결 후보·확인 경계 |
|---|---|---|---|
| A01 | 공통 종목 맥락 company_id/ticker/yahoo/exchange/as_of/profile_id/parameter_set_hash와 화면 간 유지 | `Investment-System1 · Frontend Information Architecture 2026-09-23.md` §4 | S04/S05/S08. security_id 미정·TEL AMBIGUOUS 과거 경계는 현 owner 계약을 재확인하며 식별자를 발명하지 않음 |
| A02 | Summary→Evidence→Detail drawer, immutable parent/child Track Record, profile id/hash·frozen key lock | 같은 문서 §5·10 | 공통 상세 컴포넌트의 실제 배치 확인 |
| A03 | QGV Q/G·V=null·VALIDATION_SELECTED와 PARTIAL/BLOCKED의 정직한 표시 | 같은 문서 §5 | S05. 과거 상태를 현재 상태로 복사하지 않고 최신 producer 근거 확인 |
| A04 | PRODUCT_SIMULATION과 VALIDATION_BACKTEST 명칭 구분·기존 QGV 5목적 독립 상세 접근 | 같은 문서 §3·5 | S02/S10. 새 허브가 모듈 상세 목적을 없애지 않았는지 확인 |
| A05 | sticky 종목/가격/as_of/freshness/profile/range, chart 높이·모바일 최소 280px | 같은 문서 §6·9 | S08. 새 390/1440 배치와 구 960 breakpoint·55% 높이는 자동 확정하지 않음 |
| A06 | 홈 integration gate/reasons/profile hash, target weight/execution source, integrated Track Record | 같은 문서 §8 | S01/S12. 원본 read-only 연결; 최종 target 계산·주문 권한 확대 금지 |
| A07 | Macro VMR OWNERSHIP UNCONFIRMED·별도 Macro Track Record·FRED 결측에서 UNAVAILABLE | 같은 문서 §7 | S09/S10. 소유권·실가용성을 재감사, 과거 5축 UI는 새 8축으로 대체 |
| A08 | 구 route/17 HTML 유지·query-string 맥락·redirect·구현 우선순위와 보류항목 | 같은 문서 §3·11~13 | 새 route 구현 결정 아님. C-03/C-15/V production/calibration/VMR/security_id/Macro promotion 미확정 기록 보존 |
| A09 | 과거 보수적 성숙도와 frontend가 Real/PIT/OOS/Calibration/Forward를 올리지 않는 원칙 | 같은 문서 §14 | S01/S10. 과거 %/PASS는 현재 완료율로 재사용 금지 |
| A10 | transport-neutral read model·API-first, 필요 입증 후 얇은 MCP adapter | `implementation/experiments/chart-contract-v0.1/reviews/frontend_architecture_review.md` Repository implications·Minimal useful vertical slice | 후속 구현 architecture 검토. 새 서버/MCP 승인 아님 |
| A11 | 승인 fixture 한 종목·일봉·한정 범위, candle+volume, volume 없으면 unavailable, close에서 OHLC 합성 금지 | 같은 검토 Minimal useful vertical slice | S08. 실제 차트 데이터 최소 충족조건 보존 |
| A12 | exact OHLCV crosshair, range/pan/zoom/reset·loading/empty/error·blocked면 plot 금지 | 같은 검토 Minimal useful vertical slice·Tests and acceptance | S08. 화면 시안 존재와 상호작용 검증을 구분 |
| A13 | source/as_of/observed/available, price basis, currency, timezone/session, completed bar·quality·availability | 같은 검토 Minimal useful vertical slice | S08/S10. 브라우저 시계로 PIT 가능시점 추정 금지 |
| A14 | schema/version·entity/listing·typed series, 일봉 session date와 UTC intraday 구분, record provenance | 같은 검토 Proposed read-model fields | 새 production schema 확정 아님. 계약 소유자 확인 필요 |
| A15 | duplicate/out-of-order/malformed·identity/basis/currency 검증, gap/candle 생성 금지, PIT cutoff 차단 | 같은 검토 Tests and acceptance 1~3 | 미래 adapter·fixture 수용조건. 테스트 PASS 주장 아님 |
| A16 | range/locale 변경 전후 원본 수치 유지, UI OHLC 재집계·split/dividend 조정 금지 | 같은 검토 Tests and acceptance 5 | S08. read-only renderer 경계 유지 |
| A17 | 공급자·라이선스·adjustment·availability 먼저, fixture PASS≠실수집 PASS·운영완료 | 같은 검토 Critical dependency and stop boundaries | S08/S10. 데이터·비용·방법론은 owner/user 결정 |
| A18 | Defensive/Balanced/Aggressive/Custom·profile 설정/동결 항목·conflict 기록 | `implementation/PRODUCT_ARCHITECTURE.md` Strategy Profile·Conflicts checked | S02 전략프로필 OPEN. 원래 provisional 항목을 새 수정 권한으로 확정하지 않음 |
| A19 | Portfolio QGV 분포·평균, Confidence 분포, Valuation/Safety Margin·위험·상관·시나리오 기여/손실 기업 | `QGV Portfolio · Specification v1.1.md` §10·12·13·17 | S03 요약/확장 상세 배치 확인 |
| A20 | 총금액/수량·평단/기존 snapshot 입력, 1~30종목·가변 현금·복수 목적/기업 기여 | 같은 사양 §1·7·20·22 | S03/S11. UI 입력 기능 구현 또는 현금 0% 전역정책 채택 아님 |
| A21 | band·기본적 변화·가치·위험·목적 재검토, 예상 비용/세금/환율, rebalancing history·patch 전후/이유/적용일 | 같은 사양 §6·11·16·19 | S03/S11. 주문 기능 없음·append-only 경계 유지 |
| A22 | Portfolio News Watch Next·유사 뉴스 반응·Policy Fit·유명투자자 Implied/Backtest-Derived 비교·주/분기/연 TOP10 | 같은 사양 §20·22 | S02/S03/S07/S10. 추가 상세는 삭제하지 않고 별도 범위 확인 |
| A23 | Leaderboard 원 필수/확장 열과 필터, earnings D-day·freshness·field stamps·source conflict·identifier changes | `QGV Leaderboard · Specification v1.0.md` §3~5·8~9·14~16 | S06 8필터/9열의 정확한 매핑·상세 drawer 이관 확인 |
| A24 | 재평가 1D/5D/20D/DRAWDOWN의 observed change·effective threshold·distance·SYSTEM/OVERRIDE/CANDIDATE 출처 | 같은 사양 §18~19 | S06/S05. threshold 정책·Holdout 사용 자동 승인 아님 |
| A25 | frozen trigger event·before/after QGV·cause·사후 D+5/20/63/252·cohort calibration | 같은 사양 §20 | S05/S06/S10. 예측/근거/사후 결과 분리 |
| A26 | Top30 목록·순위 snapshot 잠금·portfolio 후보 concentration/중복 확인·자동편입 금지 | 같은 사양 §11~13 | S02/S06/S10. 프로필 가중치 수정 기능은 v1 표시만 경계와 별도 확인 |
| A27 | 개별 종목/보유평균/전체/Universe/유형 평균/benchmark series·종목 생략 금지, TR/EW와 스타일 최소2 비교 | `QGV Simulation · Specification v1.0.md` §5~7 | S10 기준100 곡선의 실제 series 구성·benchmark 근거 확인 |
| A28 | 원 성과지표·초과수익/위험 차이, 분기 전종목/비중/시작·종료가격/QGV·산업/유형 변화 | 같은 사양 §8~9 | S10 6지표/분기카드가 원요구를 없애지 않도록 확인 |
| A29 | 가용범위·제한원인/PIT·실험 snapshot·비용/세금/환율 가정·bias control·4비교모드 | 같은 사양 §2~4·12~15 | S10. 추가투자·비중 예시·calibration값을 임의 공식화하지 않음 |
| A30 | execution band/품질·Forward 동결·QGV 버전/유형/실패패턴과 결과 연결 | 같은 사양 §10~11·16 | S08/S10. 실체결 기능 또는 Forward 완료 주장 아님 |
| A31 | Future Path trigger/confirmation/QGV compatibility·horizon uncertainty·actual forward path, empirical probability/OOS/calibration | `Technical Analysis System · Consolidated Record v0.1.md` §6~9·12·14 | S08/S10. 120/252일·S1~S5 템플릿은 고정 공식 상수 아님 |
| A32 | 기술-QGV Fusion 상세와 QGV 방향/기술 경로의 원본·context 분리 | 같은 기록 §5·14~15 | S01/S08. C-15 공식 수식·합산 점수·출력명 채택 금지 |
| A33 | 관계망 줌/팬/드래그/초점/확장/필터, Claim/Evidence 추적·관계/거래 상태·Fact/Impact 구분 | `Investment-System1 · RIG News Architecture v0.1.md` Fact Graph vs Impact Graph·P1~P4 기록; `implementation/docs/web_mvp/CONTRACT.md` M4 | S07. 그래프를 시간·가격 차트로 재사용하지 않음 |
| A34 | 분류별 회사 exposure·sensitivity, base vs conditional, stress Historical/Hypothetical/Reverse·no invented probability | `Macro System · Latest Consolidated Record v0.1.4 Candidate.md` §18·20·22 | S09 candidate 확장. Exposure≠Sensitivity·Scenario≠Stress |
| A35 | Macro PIT vintages·ablation/attribution·국면/전달/portfolio 기여별 Track Record·forward lifecycle/model risk | 같은 기록 §23~27 | S09/S10 candidate 상세 배치. 자동 정책변경·모델 승격 금지 |
| A36 | Frozen 70 prompt 검색/필터/starter/bundle/변수미리보기/복사·관심기업 단일목록·그룹 생성/이름/삭제/멤버십·기기 저장/reload/저장실패·export/import merge·deep-link/back·키보드 접근 | `implementation/docs/web_mvp/CONTRACT.md` W-D04/W-D07·M1·M5~M7; `implementation/docs/web_mvp/README.md` Personal preferences | S02/S10/S11. 기존 사용자 기능 배치 확인; Frozen prompt 본문·투자분류 변경, 계정 동기화 또는 새 생성 기능 없음 |
| A37 | QGV Record 종류·Revision 이유/방법론 변경 구분·평가창/Price·Total·Benchmark Return 분리·Q/G/V/Driver/Portfolio Decision 검증·Failure Taxonomy·원 Snapshot drill-down·감사 이력 | `QGV Track Record · Specification v1.0.md` §2~17 | S04/S05/S06/S10. 상세 배치 확인; 기존 평가창·지표를 새 정책·계산·완료 주장으로 승격하지 않음 |
| A38 | Official/Custom 분리·immutable Strategy Version/참조·Model/Actual/Gap·Personal Fit 다축·Dashboard·freshness/identity 제한·Preview/Sandbox/Backtest/Forward/Actual 구분 | `Investment-System1 · PERSONAL_INVESTMENT_LAYER_V1_HANDOFF.md` §7~9·15~23 | S02 OPEN/S04/S11. 기존 근거 표시·배치 확인만; editor·새 가중치·수식·종합점수·계좌/주문 권한 추가 없음 |
| A39 | canonical ID 기반 선택·ticker 충돌 후보 분리·검색순위≠QGV순위·locale 변경의 원본/순위/식별 불변·source language≠display locale·fallback·Frozen prompt 원문 유지 | `implementation/docs/global_language_search/CONTRACT.md` Language boundary·Search boundary·Deterministic ranking and fuzzy policy·Integration and protection | 공통 탐색/S04/S07/S11. 기존 동작 이관 위치 확인; 새 검색·번역·fuzzy 정책 채택 아님 |

부록에 인용한 도메인 사양·계약은 화면 기준이 바뀌었다는 이유로 superseded 처리하지 않는다. 예전 숫자·가중치·threshold·추정·상태는 원문 보존 대상이지 새 IA가 승인한 투자정책이 아니다.
