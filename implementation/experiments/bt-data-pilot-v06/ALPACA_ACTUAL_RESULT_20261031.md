# BT-DATA-PILOT v0.6 — 승인된 GitHub 실자료 진단 결과

실제 가격 확보: **고정 표본 1/10회사, 사용자 추가 표본 4/4회사 — 완전한 OHLCV 확보**

회사별 실제 날짜 범위: ABT/AAPL/MSFT/ASML 2016-03-28~04-01; NVDA는 같은 기간 및 별도 2024-06-07~06-12.

V 입력 연결: **0/5회사**(이번 실제 가격 검증 대상; 단순 symbol 연결과 구분)

정식 백테스트 실행: **미실행**

## 실제 실행과 보존

- 사용자 승인 후 최신 정본 `61709bb7387c3caf0930b24bbaef3cbbc11319d0`에서 전용 브랜치 `research/bt-data-pilot-alpaca-probe-20261031` 작성. 기존 원격/로컬 연구 및 운영 코드 보존.
- 실행 commit `e157aa34dbb8d46ac79c46051b90098f5c4b38c9`, [Actions run 41152748825](https://github.com/kco994553-star/Investment-System1/actions/runs/41152748825), attempt 1, 2026-10-31 00:55:23~00:55:45 UTC, 완료 success. **실제 Alpaca 요청 14회, 재실행 0회.**
- GitHub runner에서 `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, `RAW_REPO_TOKEN` 주입 및 사용 성공. 키 값은 출력·회수하지 않았다. Codex 로컬 환경의 미연결 상태와 GitHub runner의 정상 주입을 구분한다. Secrets 목록 API의 403은 실제 키 사용 실패를 의미하지 않았다.
- 14개 가격 응답은 모두 HTTP 200. 원본·요청 URL/feed/조정 조건·수신시각·SHA를 기존 RawDatasetStore로 보존. 원자료는 [비공개 release](https://github.com/kco994553-star/investment-system1-raw/releases/tag/bt-data-pilot-v06-alpaca-41152748825-1)의 `private-inputs.zip`에 저장, runner와 Codex에서 각각 재다운로드 SHA 일치 확인. 복원 파일 52개. **공개 Actions artifact 0개**, 원시 가격/키 공개 없음.
- 후속 NVIDIA 공식 발표 원본·Fiscal.ai 대조 원본·정정 검증 결과는 비공개 로컬 `offline-verification.zip`에 추가 보존했다. 이 추가 ZIP의 release 업로드는 Codex 측 `uploads.github.com` 인증 **401**로 실패했다. 추가 ZIP의 원격 보관을 완료했다고 하지 않는다. GitHub runner가 이미 보관·재다운로드한 가격 원본 ZIP은 정상 유지되며, 이 오류는 Alpaca 인증/수집 실패가 아니다.
- API JSON의 bar timestamp는 기간 시작시각이다. 2026년 수집시각과 과거 공개시각을 혼동하지 않았다. 통화 USD는 미국 주식 endpoint의 범위 근거이며 응답 자체에는 통화 필드가 없다.

## 회사·feed별 확인 범위

| 회사 | 공급처·접근 | 실제 기간 | SIP 행 | IEX 행 | 일별 결측률 SIP / IEX | OHLCV·조정 | 사용 가능 범위 |
|---|---|---|---:|---:|---|---|---|
| ABT (고정 10회사 중 1개) | Alpaca / GitHub Secrets·REST | 2016-03-28~04-01 | 5 | 0 | 0% / 100% | SIP raw 5필드 완전 | 비공개 데이터 연결·입력 검사 |
| AAPL (추가) | 동일 | 동일 | 5 | 0 | 0% / 100% | 동일 | 동일 |
| MSFT (추가) | 동일 | 동일 | 5 | 0 | 0% / 100% | 동일 | 동일 |
| NVDA (추가) | 동일 | 동일 | 5 | 0 | 0% / 100% | 동일 | 동일 |
| ASML (추가) | 동일 | 동일 | 5 | 0 | 0% / 100% | 동일 | 동일; 상장 증권 종류·영구 ID 별도 확인 |
| NVDA 사건 표본 | 동일 | 2024-06-07~06-12, 4거래일 | raw 4 + split 4 | raw 4 + split 4 | 모두 0% | 두 조정 기준을 분리 보존 | 분할 전후 가격 변환 대사 |

전체 **41행 = raw 33행 + split-adjusted 8행**. feed/조정 중복을 제거한 기업-거래일은 29개. 2016년 가격을 실제 확보한 회사는 고정 1개와 추가 4개이며, **고정 표본 5/10으로 바꾸어 보고하지 않는다**. 나머지 고정 9회사는 이번 한정 실행에서 미요청이다. 2017~2023년·2025년 및 2016/2024년의 다른 구간은 미수집이다.

2016년 IEX의 응답은 `bars:null`, symbol 정상, next_page_token 없음이었다. 원래 실행 코드는 이를 `RESPONSE_QUALITY_FAILED`로 분류했다. **명시적인 빈 응답을 `REQUESTED_DATA_ABSENT`로 정규화하도록 수정**, 동일 원본을 오프라인 재검증했다. bars 필드 자체가 없거나 잘못된 형식이면 여전히 품질 실패다. 원본 ZIP과 최초 집계는 덮어쓰지 않았고 정정 결과를 별도로 보존했다. IEX 전체 역사 기간이 없다는 결론이나 최초 제공일을 추정하지 않는다.

## 실제 검증과 남은 차이

- 14개 원본 SHA 대조, 41행의 OHLCV **205개 값**을 Decimal 기반 독립 추출과 비교해 일치. 비어 있지 않은 9개 응답은 기간 밖 날짜·중복·OHLC 범위 위반·필드 결측 없음. 페이지 토큰 모두 없음. 작은 probe이므로 장기 수집의 pagination 완결성을 입증한 것은 아니다.
- NVDA의 [공식 발표](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2025)를 실제 다운로드해 비공개 보존. 10대 1 분할, 6/7 장 종료 후 추가 주식 배분, **6/10 개장부터 분할 후 거래**를 확인했다.
- 두 feed의 raw/split OHLC 32개 비교에서 **정확한 산술 일치 26/32**, 분할 전 변환 가격에만 소수 둘째 자리 반올림을 적용하면 **32/32**. 분할 후 비변환 가격을 억지로 반올림하지 않았다. 거래량 변환은 **8/8** 일치. 이는 관측된 동작이며 공급자의 공식 반올림 정책은 미확인이다. 조정가격을 체결가로 사용하거나 raw+조정가격을 섞지 않았다.
- 공식 발표에서 현금배당 record date 6/11, 지급일 6/28도 확인했지만 **배당락일은 확인하지 않았다**. record date를 ex-date로 바꾸지 않았으며 배당 현금흐름·분할 원장·상폐/합병 정산은 미실행이다.
- 2024년 NVDA의 IEX/SIP는 시가 3/4일, 고가·저가·종가·거래량 각각 4/4일이 다르다. IEX는 한 거래소 feed이며 SIP와 동일한 전시장 가격으로 취급하지 않는다. 둘은 같은 공급자의 서로 다른 feed이지 독립 공급자 2곳이 아니다.
- 기존 Fiscal.ai ABT 응답과 Alpaca SIP의 2016년 5일을 비교: 종가 5/5일 일치, 시가 3/5일 일치, 거래량 0/5일 일치. 값이 다른 항목은 정산·거래 범위가 설명되기 전까지 병합하지 않는다. 이번 후속 후보는 **관측 성공한 SIP raw를 일관되게 사용**한다.
- 기존 PIT 어댑터에 5회사 raw 종가 후보를 넣었으나 미검증 영구 증권 ID, 주식수 기준 및 basis alignment, 과거 가용시각을 만들어 넣지 않아 승인 quote는 **0/5**. QGV v2 계산 기준을 완화하지 않았다. **기존 0/50은 고정 10회사 × V 5요인**이며 이번 가격 성공으로 요인 계산 완료 수를 올리지 않는다.

## 비용·권리·API 한계

[공식 Basic 안내](https://docs.alpaca.markets/us/docs/about-market-data-api)는 무료, 역사자료 2016년부터, 최근 15분 제한, 분당 200회 한도를 명시한다. 이번 개인 계정은 사용자가 Basic으로 제공했으며, **해당 키로 2016년 SIP 및 2024년 IEX/SIP HTTP 200을 실제 확인**했다. 인증 성공이 청구서/요금제 조회를 대체하지는 않는다. 구독 변경·유료 전환·결제는 하지 않았다.

실행은 최대 14회, 호출 사이 최소 0.35초와 네트워크 시간으로 제한했고 401/403/429는 0회다. 실제 한도 200회를 부하 시험한 것은 아니다. [bars 계약](https://docs.alpaca.markets/reference/stockbars)의 `adjustment=raw|split`, `feed=iex|sip`, `asof=-`를 명시했다. 최근 시세/실시간 SIP·다른 기간·상폐 종목 권한은 미검증이다.

[약관](https://s3.amazonaws.com/files.alpaca.markets/disclosures/library/TermsAndConditions.pdf)의 개인 비상업 사용 범위로 내부 연구·개인 비공개 저장을 수행했다. 원자료 재배포와 파생 투자성과 공개 권리를 자동 인정하지 않는다. 이 문서와 로그는 가격 값 없는 품질 집계이며 CAGR/수익률 공개가 아니다. source별 원본·코드 provenance를 유지한다.

## 코드와 다음 단계

실행 코드의 `bars:null` 처리 결함을 수정하고 회귀 검사 1개를 추가했다. **합성 검사 7개 통과**와 위 실자료 검증은 별도다. `verify_alpaca_actual.py`는 저장된 응답만 읽으며 추가 API 호출 0회다. 운영 코드·TARGET·QGV 공식 가중치·기존 32/40/60 연구 등록·연간 재선정 계약은 변경하지 않았다.

재현 명령(비공개 입력 경로 필요):

```bash
python implementation/experiments/bt-data-pilot-v06/verify_alpaca_actual.py \
  --private-dir /workspace/private-bt-data-pilot-v06/github-alpaca-20261031 \
  --fiscal-original /workspace/private-bt-data-pilot-v06/ABT-stageA-tool-response.json \
  --reviewed-src /workspace/Investment-System1/implementation/src
```

다음 단계는 **같은 SIP raw로 고정 나머지 9회사에 짧은 구간을 확대**하는 것이다. 변경 티커·종료 기업은 날짜별 증권 ID 매핑을 먼저 확인하고 실패도 그대로 남긴다. 이후 배당락/지급일·분할·합병/상폐 정산, 가격과 과거 주식수 기준을 연결한 뒤 전체 파일럿 기간 확대 여부를 판정한다. 2016~2025년 전체 또는 1980~2025년을 확보했다고 보고하지 않는다.

이번 승인된 1회 진단은 종료했다. **정식 BT-01/02/03 미실행**, `BLOCKED_ON_DATA`, `OOS_NOT_ESTABLISHED`, `BOOK_EXACT_UNCONFIRMED` 유지. 역사 모집단 없이 현재 종목으로 대체하지 않는다. 새 워크플로·연구 브랜치 등록 외 병합·배포·운영 변경은 하지 않았다.
