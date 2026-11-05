# BT-DATA-PILOT v0.6 — KIS 실제 가격과 고정 10회사 연결

실제 가격 확보: **10/10회사**(고정 표본 조회명 기준, 2016년 Alpaca SIP).
회사별 실제 날짜 범위: 아래 표. 서로 떨어진 구간을 연속 이력으로 해석하지 않는다.
V 입력 연결: **0/10회사**(기존 엄격한 PIT 입력 허용 기준).
정식 백테스트 실행: **미실행**. 실제 가격과 합성 검사를 구분한다.

## 실제 확보 범위

2016 구간은 **2016-03-28~2016-04-01**, 최근 구간은 **2026-10-19~10-23**이며 각각 사전 고정한 5거래일이다. 아래 행 수는 이 구간에서 비조정 OHLCV 5개 필드가 모두 있는 행 수다. KIS가 함께 반환한 더 긴 원본 페이지는 다음 표에 별도로 기록했다. 수정주가로 원주가 결손을 메우지 않았다.

| 회사 / 조회명 | 2016 KIS | 2016 Alpaca SIP | 최근 KIS | 최근 Alpaca SIP | 결손·제약 |
|---|---:|---:|---:|---:|---|
| ABT | 5 | 5 | 5 | 5 | 요청 구간 결측 0% |
| ACU | 5 | 5 | 5 | 5 | 요청 구간 결측 0% |
| AE | 0 | 5 | 0 | 0 | KIS 두 구간 빈 응답; Alpaca 최근 빈 응답 |
| BKTI / 과거 RWC | 0 | 5 | 5 | 5 | KIS RWC 빈 응답; 영구 증권 ID 대사 미완료 |
| AMD | 5 | 5 | 5 | 5 | KIS 실패 요청을 대기 후 보완 |
| CECO / 과거 CECE | 0 | 5 | 5 | 5 | KIS CECE 빈 응답; 최근 MODP1은 API 오류 유지 |
| MATX | 5 | 5 | 5 | 5 | KIS 실패 요청을 대기 후 보완 |
| ALX | 5 | 5 | 5 | 5 | KIS 실패 요청을 대기 후 보완 |
| LNG | 0 | 5 | 5 | 5 | KIS 2016 AMS 조회 빈 응답; 거래소 이동/조회 코드 대사 필요 |
| IDSA | 0 | 5 | 0 | 0 | KIS 2016 raw 빈 응답, 최근 raw SESSION FULL; Alpaca 최근 빈 응답 |
| **5일 완전 확보 회사** | **5/10** | **10/10** | **8/10** | **8/10** | 원시 가격만 집계 |

확보한 5행의 OHLCV 필드 결측은 0이다. 0행은 요청한 5일 기준 100% 미확보이나, **상장 종료 후 비거래·공급자 빈 응답·API 실패는 서로 다른 상태**다. 상장 종료 표본을 생존 기업으로 교체하지 않았다. RWC→BKTI 및 CECE→CECO는 고정 CIK 표본의 조회 별칭이며, 이 조회 성공 자체는 영구 증권 동일성 검증이 아니다.

KIS 원본에서 추가 확보한 비조정 페이지는 다음과 같다. 모든 원본을 저장했고, 전체 페이지의 날짜/OHLCV 구조는 재현 검사했다. 전체 페이지에 대한 독립 거래소 달력 결측 검증은 미실행이며, 위 5거래일 검증과 구분한다.

| 회사 | 2016 요청에서 반환한 원주가 범위 / 고유 행 | 최근 요청에서 반환한 원주가 범위 / 고유 행 | KIS 실제 요청 수 / HTTP 소요 초 |
|---|---|---|---:|
| ABT | 2015-11-06~2016-04-01 / 100 | 2026-06-03~10-23 / 100 | 6 / 4.158 |
| ACU | 2015-11-06~2016-04-01 / 100 | 2026-06-03~10-23 / 100 | 4 / 2.766 |
| AE | 없음 | 없음 | 4 / 2.471 |
| BKTI(RWC) | 없음 | 2026-06-03~10-23 / 100 | 6 / 3.527 |
| AMD | 2015-11-06~2016-04-01 / 100 | 2026-06-03~10-23 / 100 | 6 / 3.977 |
| CECO(CECE) | 없음 | 2026-10-19~10-23 / 5 | 6 / 4.325 |
| MATX | 2015-11-06~2016-04-01 / 100 | 2026-06-03~10-23 / 100 | 6 / 3.784 |
| ALX | 2015-11-06~2016-04-01 / 100 | 2026-06-03~10-23 / 100 | 6 / 3.643 |
| LNG | 없음 | 2026-06-03~10-23 / 100 | 5 / 3.162 |
| IDSA | 없음 | 없음 | 5 / 3.114 |

요청 수·시간에는 해당 회사의 raw/MODP1·실패·재조회가 포함되며, 인증과 대기 시간은 제외한다. 별도 NVDA 사건 표본은 2요청 / 1.345초, raw/MODP1 각각 2024-01-22~06-12 100행을 반환했다. 고정 10회사 수에는 포함하지 않는다. KIS 전체 56시세 요청의 HTTP 소요 합계는 **36.272초**, 토큰 요청은 별도 3회다. 초기 호출 간격은 1.1초, 실패 보완은 10초였다. 성능 절감률은 추정하지 않았다.

## 실행·인증·오류를 분리한 기록

- GitHub runner에서 `KIS_APP_KEY`, `KIS_APP_SECRET`, Alpaca 키 2개, `RAW_REPO_TOKEN` 설정을 확인했다. 대체 이름 `KIS_APPKEY`/`KIS_APPSECRET`은 비어 있었다. 로컬 환경에 키를 복사하지 않았다.
- KIS `POST /oauth2/tokenP` 인증은 실제 HTTP 200. 인증 응답과 토큰은 파일에 저장하지 않고 메모리에서만 사용했다. 주문·잔고·계좌 변경 API는 호출하지 않았다.
- [실행 41167550137](https://github.com/kco994553-star/Investment-System1/actions/runs/41167550137): KIS 최초 ABT 조회 EGW00316. 독립 Alpaca SIP 19요청으로 85행 확보. 기존 ABT 2016 5행을 재사용해 고정 표본 2016 10/10을 완성했다.
- [실행 41167695581](https://github.com/kco994553-star/Investment-System1/actions/runs/41167695581): 공식 공통 헤더(Content-Type/Accept/charset/User-Agent)를 맞춘 뒤 KIS 43요청. 이후에도 EGW00316이 발생했으므로 최초 오류의 원인을 헤더 누락으로 단정하지 않는다.
- [실행 41167986542](https://github.com/kco994553-star/Investment-System1/actions/runs/41167986542): 이전 비공개 ZIP을 해시 검증 후 복원하고, 실제 실패 요청만 10초 간격으로 1회 보완. 성공·빈 응답·Alpaca 자료는 재수집하지 않았다. 12요청 후 `OPSQ1002: SESSION FULL` 재발로 중단했다. 뒤에 예정된 IDSA MODP1 재조회 및 명시적 BYMD 커서 전진 시험은 **미실행**이다.
- 전체 KIS 응답 코드: `MCA00000` 40, `EGW00316` 7, `OPSQ1002` 9. 정상 처리 40건에는 빈 응답도 포함되어 있어 가격 성공 건수와 다르다. SESSION FULL을 키 미확보나 요청 데이터 부재로 바꾸어 기록하지 않았다.
- ABT 연속조회 헤더 `F→N`에서 같은 100행이 다시 반환됐다. 반복 감지 후 중단하고 중복 행을 집계에서 제외했다. BYMD=20160401로 과거 응답은 확보했으나, 페이지를 연속 연결하는 전체 이력 수집은 검증 완료가 아니다. 100행 또는 샘플 max_depth=10을 공급자 최대 역사 범위로 주장하지 않는다.

## 조정·기업행사·독립 대조

KIS는 `MODP=0` 원주가와 `MODP=1` 수정주가를 분리 보존했다. KIS 일봉의 `xymd/open/high/low/clos/tvol`을 기존 OHLCV 검증기로 정규화했다. `rsym=D+거래소+조회명` 일치 28개 비어 있지 않은 응답을 대조했다. 이는 조회명 일치이며 영구 ID가 아니다.

- KIS와 **Alpaca SIP raw** 공통 69거래일: 종가 **69/69**, 시가 **66/69**, 고가 **68/69**, 저가 **68/69**, 거래량 **3/69** 일치. 고정 표본 65일과 별도 NVDA 4일이다. 가격을 평균하거나 서로 덮어쓰지 않았다.
- KIS 공식 안내는 무료 미국 시세의 시장 범위 및 OHLC/거래량이 유료 통합 시세와 다를 수 있다고 명시한다. 실제 차이에 거래소·세션·거래량 집계 정의가 얼마나 기여했는지는 아직 확정하지 못했다. 공급처가 다르다는 이유로 원천 시세도 완전히 독립적이라고 주장하지 않는다. 기존 IEX 결과는 별도 단일 거래소 자료로 유지한다.
- NVDA 2024-06-07/10/11/12: raw/MODP1 4일 모두 확보. 공식 10:1 분할만 적용한 기대 OHLC와 KIS MODP1은 **0/16** 일치, 거래량은 raw와 **4/4** 동일했다. 분할 외 조정·반올림·소급 조정 기준 확인이 필요하다. MODP1을 단순 분할 조정 또는 배당 재투자 총수익으로 단정하지 않는다.
- 배당락일·지급일·현금 배당액·분할 계수·합병/상폐 정산·영구 ID가 일봉 응답에 없다. 기존 NVIDIA 공식 사건 원본은 보존했지만, 현금·주식수 장부 통합과 중복 반영 실자료 검사는 **미실행**이다. 없는 배당·상폐 정산을 0으로 만들지 않았다.
- USD와 미국 거래일 시간대는 미국 거래소 조회 범위에 따른 정보다. 응답 자체에는 통화·세션 범위·최초 공개시각이 없으므로 그 한계를 남겼다. 수집시각을 2016년 당시 공개시각으로 사용하지 않았다.

## 재현성과 기존 코드 재사용

기존 `RawDatasetStore`, v0.5 가격 필드 검증기/원본 보존, v0.6 Alpaca 정규화, `raw_store_release.py`, 검토된 `pit_adapter.quotes_as_of`를 재사용했다. 새로운 포트폴리오·매매·기업행사 엔진을 만들지 않았다.

실자료 검사: **원본 75개 SHA 검증, 정규화 2,790행 재현, OHLCV 13,950개 값의 Decimal 원본 대조**. 반복 응답과 raw/MODP1을 각각 검증한 행 수이며, 고유 기업-거래일 수가 아니다. KIS 고유 원주가/수정주가 합계는 2,605행(NVDA 포함), 반복 ABT 페이지 100행은 중복 제거 대상이다. 별도 합성 검사 **13개 통과**(기존 Alpaca 7 + KIS 6), 방향 가드 0건. 합성 데이터는 실제 확보율에 포함하지 않았다.

원본·전체 응답·요청조건·조회시각·해시·실패 응답은 기존 **비공개** `investment-system1-raw`의 위 실행 ID별 release에 보존하고 업로드→다운로드 SHA 일치를 확인했다. 세 실행의 공개 Actions artifacts는 0개. 로그의 Secret 줄 마스킹 및 원시 응답 표식 부재를 검사했다. 공개 보고서는 집계만 포함한다. 로컬 정본 검증 결과는 `github-kis-cooldown-20261031/verified-results.json`이다.

재현 명령(해당 private release들을 승인된 외부 경로에 복원한 뒤, 네트워크 호출 0):

```bash
python implementation/experiments/bt-data-pilot-v06/verify_kis_actual.py \
  --restored /workspace/private-bt-data-pilot-v06/github-kis-cooldown-20261031/restored \
  --additional-restored /workspace/private-bt-data-pilot-v06/github-kis-20261031/restored \
  --previous-restored /workspace/private-bt-data-pilot-v06/github-alpaca-20261031/restored \
  --reviewed-src /workspace/Investment-System1/implementation/src
```

## 사용권·채택 판단·재개 조건

**KIS는 내부 가격 대조용 보조 공급원으로 제한 채택, 정식 체결·총수익 장부 투입은 보류한다.** Alpaca SIP가 이번 고정 표본의 2016 가격 연결 주 경로다. 어떤 공급자도 역사 전체시장 모집단의 대체물이 아니다.

KIS 공식 기본서비스 FAQ는 이용료 0원, 공식 개인 이용 안내는 자신의 투자·열람·분석을 허용한다. 계정과 API 키는 필요하지만 새 결제·거래·입금·유료 시세 신청은 하지 않았다. 역사 FAQ의 초당 10건을 현재 보장 한도로 사용하지 않았다. SESSION FULL이 발생해 장기 대량 수집의 안정적인 한도는 미확정이다. 원시 시세 외부 앱 배포·재배포는 허용으로 판정하지 않으며, 가격을 복원할 수 있는 파생 성과 공개도 별도 사용권 확인 전 보류한다. 이번 비공개 개인 연구 승인을 운영 공개 경로의 권한으로 확대하지 않는다.

주요 근거:

- [KIS 공식 코드 고정 commit](https://github.com/koreainvestment/open-trading-api/tree/3a9be59a3ed8745720dc3aa9d584bdf3b7830362), `examples_llm/overseas_stock/dailyprice/{dailyprice,chk_dailyprice}.py`, `examples_llm/kis_auth.py`. 외부 설치 스크립트는 실행하지 않았다.
- [공식 기간별시세](https://apiportal.koreainvestment.com/apiservice-apiservice?/uapi/overseas-price/v1/quotations/dailyprice), TR `HHDFS76240000`, GET only.
- [기본 이용료 FAQ](https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000002/post/beb2459a-f6b4-432e-928a-d3462dd0daef), [개인 열람/외부 배포 FAQ](https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000002/post/01a0b635-3630-4aee-8970-42f83828118c).
- 기존 [공식 KIS 조사](../../docs/manual_quotes_owner/KIS_DIRECT_API_RESEARCH_26E.md), [Alpaca 실제 결과](ALPACA_ACTUAL_RESULT_20261031.md), [NVIDIA 공식 분할 발표](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2025).

가격 연결 후보 50행/10회사에 기존 엄격한 PIT 입력 검사를 적용한 결과 승인 **0/10**이다. 영구 증권 ID, 당시 주식수 및 주식 종류와 가격의 동일 기준, 신호일 가용시각 계약이 확보되지 않았다. 기존 **0/50은 10회사 × QGV V의 5요인** 분모로, OHLCV 5필드나 가격 행 수가 아니다. 현재 확보한 종가를 요인 산출 완료로 세지 않았다.

다음 실행은 확보한 원본으로 ① 영구 증권 ID/티커·거래소 이력 ② PIT 주식수 ③ 신호·체결 세션과 조정 기준 ④ 배당·분할·상폐 정산을 연결한다. KIS 재수집은 SESSION FULL 해소 및 명시적 BYMD 전진 검사 이후, 미확보 요청만 재개한다. 현재 키는 정상 연결되어 있어 재등록할 필요가 없다.

BT-01은 승인된 PIT 입력 manifest·체결/기업행사 장부와 비용 계약, BT-02는 추가로 U-BOOK200/U-SPX-HIST의 역사 적격 모집단과 독립 분위 계산, BT-03은 동일 조건의 공통 산출 기업과 검증된 팩터 산식을 충족해야 정식 실행할 수 있다. 2016~2025 제한 진단의 전체 입력도 아직 갖추지 않았으며, 1980~2025 목표는 그대로 **BLOCKED_ON_DATA**다. **OOS_NOT_ESTABLISHED / BOOK_EXACT_UNCONFIRMED**를 유지한다. QGV v2, TARGET, 운영 자동매매, 이전 연구 패치 및 연간 재선정 계약은 변경하지 않았다. 연구 Draft PR만 갱신하며 병합·배포는 하지 않는다.
