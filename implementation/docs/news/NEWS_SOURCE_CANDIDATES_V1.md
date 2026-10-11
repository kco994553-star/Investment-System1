# 뉴스(신호) 소스 후보 비교 v1 — 사용자 결정 대기 (2026-10-11)

대기열 2.2c. 소스는 사용자 결정 후 구현한다. 이 문서는 조사 결과이며 어떤 소스도 연결하지 않았다.

## 전제(사용자 지시)

- 공시는 '공시·확정', 뉴스는 '뉴스·신호'로 구분해 한 목록에 시간순으로 표시한다. 같은 사건은 묶어서 신규·반복을 표시한다.
- 저장하는 항목은 제목·링크·시각·종목·분류뿐이고, 본문은 저장하지 않는다. 뉴스와 공시 모두 점수를 직접 바꾸지 않는다.
- 공개 JSON(Pages)에 넣으면 재배포가 된다. 따라서 공개 계층에는 재배포가 허용된 소스만 쓸 수 있다. 개인용 약관 소스는 사용자 본인 키로 기기(또는 개인 Worker)에서만 쓸 수 있다. 개인 Worker를 쓰면 Worker 변경이므로 승인 대상이다.

## 조사 방법과 한계

- 컨테이너에서 각 사이트에 직접 접속할 수 없었다. 그래서 웹 검색 결과로만 약관을 확인했다.
- 1차 약관 원문을 확인한 소스: GDELT 소개 페이지, Alpha Vantage 서비스 약관(색인본이 오래되었을 수 있음), Finnhub 가입·FAQ·가격 페이지.
- Marketaux와 GlobeNewswire는 약관 원문을 확인하지 못했다. 표에 '미확인'으로 적었다.
- 구현 전에 사용자가 각 약관 최신본을 확인해야 한다.

## 비교표

| 소스 | 이용 조건 | 저장·재배포 범위 | 갱신 주기 | 종목 연결 정확도 | 이 시스템에서 쓸 수 있는 곳 |
| --- | --- | --- | --- | --- | --- |
| SEC EDGAR 8-K·Ex 99.1 (참고: 공시 계층) | 무료. 미국 정부 자료. SEC 공정 접근 규칙(User-Agent, 초당 10회) | 공개 재배포 가능(정부 저작물). 제목·링크·시각만 저장 | 제출 즉시(수 분) | 매우 높음(CIK로 직접 연결) | 공개 JSON. 단, 공시이지 뉴스가 아님 |
| GDELT (DOC 2.0 / GKG) | 무료. 학술·상업·정부 목적 모두 허용 | 재배포·재호스팅 허용. GDELT 인용과 링크 필수 | 15분 | 낮음~중간. 종목 코드가 없어 회사명·키워드 매칭이 필요하고, 동명이인·일반어 오탐이 있음 | 공개 JSON 가능(출처 표기). 매칭 규칙과 오탐 검사 필요 |
| 기업 IR 보도자료 RSS(회사 사이트, 배포사 피드) | 회사·배포사마다 다름. 대개 개인 열람용 | 회사별 약관 확인 필요. 제목·링크만은 보통 허용되나 공개 재배포는 확인 전 불가로 본다 | 발표 즉시 | 매우 높음(회사 자체 피드) | 확인된 회사만 공개. 그 전에는 기기 전용 |
| Finnhub company-news(무료 키) | 무료 등급은 개인·비상업용(가입 시 비전문가 확인) | 재배포는 유료·기업 계약 필요. 구독이 끝나면 데이터 삭제 의무(FAQ) | 수시. 분당 약 60회 | 높음(티커 지정 조회) | 사용자 본인 키로 기기·개인 Worker만. 공개 불가 |
| Alpha Vantage NEWS_SENTIMENT | 개인·비상업 사용 허가(서면 합의 시 예외). 무료는 하루 25회 | 재배포는 별도 계약 필요 | 수시 | 높음(티커·주제 필터, 감성 점수 포함. 감성은 점수에 쓰지 않음) | 기기 전용. 하루 25회라 19종목 일일 갱신이 빠듯함 |
| Marketaux(무료) | 무료는 하루 100회, 요청당 기사 3개 | 미확인(원문 미확인) | 수시 | 중간~높음(엔티티 태깅) | 약관 확인 전 보류 |
| Google News RSS 등 검색 집계 피드 | 자동 수집·재배포 조건이 불명확 | 불명확 | 수시 | 중간 | 권장하지 않음 |

## 제안(결정용)

1. **공개 계층(Pages):** SEC 8-K(공시·확정, 대기열 2.2a)에 GDELT(뉴스·신호, 출처 표기)를 더한다.
   - GDELT는 19종목에 대해 회사명·티커 매칭 규칙 v0을 둔다. 오탐을 줄이려고 제외어와 최소 언급 기준을 쓴다.
   - 신규·반복은 같은 URL과 제목 유사도로 묶는다.
2. **기기 계층(선택):** 사용자 본인 Finnhub 무료 키로 S15 관심 기업 뉴스를 기기에서만 표시한다.
   - 키 저장과 호출 경로는 개인 Worker 확장(승인 필요)이나 기기 직접 호출 중에서 고른다.
3. **기업 IR RSS:** 약관이 확인된 회사부터 하나씩 추가한다.

결정이 필요한 것:
- 1번(GDELT)을 채택할지
- 2번 기기 계층을 쓸지와 그 경로
- 3번 대상 회사

## 출처

- [GDELT About](https://www.gdeltproject.org/about.html)
- [Alpha Vantage Terms of Service](https://www.alphavantage.co/terms_of_service/)
- [Alpha Vantage Market Data Policy](https://www.alphavantage.co/realtime_data_policy/)
- [Alpha Vantage Support](https://www.alphavantage.co/support/)
- [Finnhub Register](https://finnhub.io/register)
- [Finnhub FAQ](https://finnhub.io/faq)
- [Finnhub Pricing](https://finnhub.io/pricing)
- [Marketaux Pricing](https://marketaux.com/pricing)
- [GlobeNewswire/Notified Terms](https://portal.notified.com/terms-conditions/en)
