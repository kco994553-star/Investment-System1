# 일일 데이터 파이프라인 설계 — D4·D6 보완

조회일: **2026-10-09 UTC**. 이번 범위는 D4 가격 공급자 선택지와 D6 DART 준비 상태의 문서 반영이다. 확인한 저장소 브랜치와 PR에서 기존 전체 설계 문서를 찾지 못해 독립 보완 문서로 기록한다. D1~D3·D5 등 다른 설계 결정은 범위 밖이다. 구현·수집 작업·가입·키 발급·Secret 변경은 실행하지 않는다.

## D6 — 한미반도체 재무제표

| 항목 | 설계에 반영할 상태 |
| --- | --- |
| Secret | **`DART_API_KEY` 아직 미등록** — 사용자 확인. 값 조회 없음 |
| 등록 계획 | OpenDART 점검 종료 예정 **2026-10-11 18:00 이후**, 사용자가 `DART_API_KEY`로 등록 예정 |
| 첫 구현 대상 | **한미반도체(KRX 042700) 숫자 재무제표 JSON** |
| 회사 식별 | DART `corp_code=00161383`, 12월 결산 |
| 시작 경로 | `fnlttSinglAcntAll.json` 등 숫자 계정 API를 검토하고 연결/별도·기간·통화·접수번호를 확인 |
| 구현 준비 | 키 등록·서비스 재개·별도 구현 승인 이후; 등록 전에는 인증 API 호출이나 스케줄 작업을 시작하지 않음 |

공식 [OpenDART 점검 공지](https://opendart.fss.or.kr/)는 2026-10-08 20:00~2026-10-11 18:00 일부 중단을 안내한다. 사이트 시각의 시간대는 명시되지 않았으며 재개 시각은 공지상의 예정이다. 키 신청/관리·고유번호·공시 원문·XBRL 등은 중단 대상으로, 숫자 재무제표 API 전체가 중단된다는 의미는 아니다. 사용자 등록 계획과 실제 서비스 재개를 구분한다.

근거는 [재무 공시 출처 조사 PR #77](https://github.com/kco994553-star/Investment-System1/pull/77)이다. 그 조사에서 DART 공개 숫자 가공 JSON은 공익·타인 권리 보호 및 키 이용/호출 제한 조건하에 가능으로 판정했다. 첫 구현은 수치와 출처·접수번호에 한정하고, 주석 원문은 별도 권리·제공 범위 확인 대상으로 남긴다.

## D4 — 19종목 과거 일봉: Tiingo 추가 검토

### Secret와 실제 계정 상태

기존 정확한 이름은 **`TIINGO_API_KEY`**다. `.github/workflows/c21-real-data.yml:160`의 `secrets.TIINGO_API_KEY` 참조를 확인했다. **Secret 존재는 사용자 확인**을 근거로 기록한다. GitHub Secret 이름 목록 조회는 HTTP 403으로 거부돼 독립적인 존재 확인을 하지 못했다. 값 조회·인증 API 호출로 우회 확인하지 않았다.

키 존재는 플랜·현재 잔여 한도·시장 접근권·재배포 권리의 증명이 아니다. **해당 계정의 실제 가입 플랜, 적용 약관/추가 계약은 미확인**이며 아래는 공개 Starter/Power 요금제 비교다.

### 무료/공개 요금제와 호출 한도

[공식 가격표](https://www.tiingo.com/pricing), [한도 안내](https://www.tiingo.com/documentation/general/overview)를 조회했다.

| 항목 | Starter | Power |
| --- | --- | --- |
| 가격 | **$0/월** | **$30/월** |
| 월 unique symbols | **500** | 110,229 |
| 최대 요청/시간 | **50** | 10,000 |
| 최대 요청/일 | **1,000** | 100,000 |
| 월 대역폭 | **1GB** | 40GB |
| 라이선스 | **Internal Use Only** | **Internal Use Only** |

개인 요금제의 “Global Securities” 수와 실제 월 이용 심볼 수는 다르다. Starter의 과거 안내 “50 unique tickers”를 현재 월 한도로 쓰지 않는다. 문서상 시간 한도는 매시간, 일 한도는 midnight EST에 초기화되며 분/초당 고정 한도는 없다고 안내한다. 일회 백필과 증분 수집·재시도를 같은 예산에 합산하고, 시간·대역폭 제한도 확인해야 한다.

종목당 일봉 요청 1개를 가정한 17~19회/일 자체는 Starter 요청·심볼 한도 안이다. 이는 저장·시장 커버리지·공개 배포 승인을 뜻하지 않으며 실제 초기 전체 이력의 대역폭도 검증하지 않았다.

### 19종목 본상장 커버리지

대상은 기존 공개 TARGET 카탈로그의 미국 17종목 + 일본/한국 각 1종목이다. 실제 개인 보유수량·매수단가는 포함하지 않는다.

| 시장/통화 | 정확한 대상 | Tiingo 공개목록 확인 |
| --- | --- | --- |
| 미국 · USD | `ASML, LRCX, KLAC, NVDA, AMD, AVGO, QCOM, INTC, MSFT, GOOGL, AMZN, RTX, SYK, ETN, HUBB, GEV, ROK` | **17/17 목록 존재**, 모두 USD·`endDate=2026-10-08` |
| 일본 · JPY | Tokyo Electron **TSE:8035** | **본상장 표기 없음**, TSE 거래소 항목 없음 |
| 한국 · KRW | 한미반도체 **KRX:042700** | **본상장 표기 없음**, KRX 거래소 항목 없음 |

공식 [Symbology 문서](https://www.tiingo.com/documentation/appendix/symbology)는 미국 주식/ETF/펀드와 중국 주식을 지원한다고 안내한다. [EOD 상품](https://www.tiingo.com/products/end-of-day-stock-price-data)의 거래소 목록에도 TSE·KRX가 없고, 인증 없이 읽은 [공식 supported_tickers.zip](https://apimedia.tiingo.com/docs/tiingo/daily/supported_tickers.zip) 108,972행에서 두 거래소 및 `8035`·`042700` 본상장 심볼을 찾지 못했다. **Tiingo 단독으로 정확한 19종목 본상장 범위를 충족할 수 없다.**

Tokyo Electron의 미국 OTC `TOELY`, `TOELF`, `TELWY`는 다른 시장·통화·상품이므로 TSE 8035 대신 사용하지 않는다. ASML은 승인된 NASDAQ `ASML`, Alphabet은 Class A `GOOGL`을 유지한다.

[EOD 개발 문서](https://www.tiingo.com/documentation/end-of-day)는 목록에 지원 예정 예약 심볼도 포함된다고 경고한다. 17개 목록 존재는 실제 계정의 API 성공이나 모든 과거 날짜의 완전성을 증명하지 않는다. 가격표의 “30+ Years”도 각 회사 30년 이력 보장이 아니다. 공개목록상 GEV는 2024-03-27, HUBB는 2015-12-24부터다. 실제 일봉·분할/배당 조정·빈 기간은 후속 계약/접근권 확인 이후 검증해야 한다.

### 약관 원문과 저장·공개 Pages 재배포

[공식 Terms of Use](https://app.tiingo.com/tos/)의 표시상 최종 변경일은 **2026-10-06**이다. 동일 약관에서 아래 짧은 원문을 발췌했다.

| 조항 | 원문 발췌 | D4 적용 |
| --- | --- | --- |
| §1.6(a) Starter/Trial | “any persistent or durable storage” | 원본·파생물 비휘발성 저장 금지(일시적인 파일·로그·DB 저장 포함), 계산/작업/세션 종료 전 임시 데이터 삭제 |
| §1.6(c) 금지 예시 | “simple transformations of open, high, low, close, volume” | 파일 형식 변경·필드명 변경 등으로 OHLCV 공개 권리가 생기지 않음 |
| §7.3 API 이용 | “special request and permission” | 재배포에는 별도 허가·추가 비용 필요 |
| §7.3 허가된 재배포 | “Data sourced by Tiingo” | 허가 후에도 Tiingo 출처 표시와 링크 필요 |

§1.6(b)는 유효한 유료 플랜의 허용 범위에서 내부 저장을 인정하되 종료·다운그레이드 시 원본 삭제를 요구한다. §1.6(c)의 허용 파생물은 원본 서비스의 대체물이 아니고 원본을 복원할 수 없어야 한다. 공개 일봉 JSON, 종가 시계열·정규화 가격·복원 가능한 수익률은 자동 허용 대상이 아니다. §1.6 예외는 Start-up/Enterprise/Institutional의 별도 서면 계약으로만 가능하며 Starter/Power에는 제공하지 않는다.

[Developer Program](https://www.tiingo.com/documentation/appendix/developers)은 이용자가 각자 Tiingo 계정을 쓰는 통합과 공급자가 수집해 재배포하는 서비스를 구분하며 후자에 redistribution license를 요구한다. [가격표](https://www.tiingo.com/pricing)의 “Internal Use Only”도 타인에게 표시/공유할 권리를 주지 않는다. [EOD 상품](https://www.tiingo.com/products/end-of-day-stock-price-data)은 사업용 Display Redistribution 가격을 별도로 제시하지만 공개 다운로드 가능한 원시 JSON·Git 이력까지 허용하는 견적은 아니다.

기존 이용자에 대한 개정 적용은 게시/이메일 통지 후 30일 조건이며 추가 계약이 우선할 수 있다. **10월 6일 변경 표시만으로 이 계정의 10월 9일 적용 약관을 확정하지 않는다.** 공개 최신 조건을 설계 기준으로 삼되 실제 계약·통지일은 미확인으로 남긴다.

**D4 판정: 미국 17종목의 내부 사용 후보로는 조건부 가능. 무료 Starter의 비휘발성 저장 파이프라인과 별도 계약 없는 공개 Pages OHLCV JSON은 공개 최신 조건상 불가. TSE 8035·KRX 042700은 다른 가격 출처가 필요하므로 Tiingo 단독 19종목 선택지는 채택하지 않는다.**

### 기존 구현과 후속 선택 경계

현재 Tiingo fallback은 `implementation/tools/fetch_tiingo_prices.py`에서 종가 중심 차트로 변환하고 UTC 21:00/통화 USD를 고정하는 경로다. 이것을 그대로 19종목 full OHLCV 과거일봉 어댑터로 재사용하지 않는다. 후속 구현은 원본 O/H/L/C/V, 조정 가격과 원 가격, 거래소별 달력·시차·통화, 상장/심볼 변경 및 필드별 기간·출처를 구분해야 한다.

현재 작업은 조사와 설계 보완만 수행한다. 기존 workflow·fallback·스케줄·공개 Pages·기존 데이터는 변경하지 않는다. 특정 계정의 위반 여부를 판정하거나 유료 계약/키 사용을 자동 승인하지 않는다.

## Secret 취급 원칙

- **이름·존재 여부만** 문서/PR에 기록한다. `DART_API_KEY`와 `TIINGO_API_KEY`의 값을 코드·로그·커밋·PR·공개 산출물에 출력하지 않는다.
- 인증정보는 정당한 사용자의 비공개 실행 위치에만 보관한다. 요청 URL·헤더·에러/디버그 출력·캐시/아티팩트도 비밀 값이 포함된 채 저장하지 않는다.
- 값 확인, 가입·키 발급·Secret 등록/변경·계정 플랜 변경·공급자 연락은 실행하지 않았다. 문서 조사에 인증 API를 사용하지 않았다.

모든 외부 출처의 조회일은 **2026-10-09 UTC**다. 공개 지원목록과 문서/약관 확인을 실제 계정 API 운영 검증과 구분했다.
