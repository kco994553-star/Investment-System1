# 계층 3 공급처·업데이트 인계

2026-11-05 UTC. 문서 열람과 보유 자료 오프라인 계산만 실행했다. 새 시세 요청·가입·결제·Secret·workflow 실행·운영 보류 해제는 없다. 아래 실행 주기와 캐시 정책은 Main 구현용 **설계안**이다.

## 공식 문서와 공급처 대응

| 공급처 | 실제 필드·포괄범위 | 가격 기준·신원·역사·지연 | 권리와 이번 사용 |
|---|---|---|---|
| Alpaca Market Data v2 `GET /v2/stocks/{symbol}/bars`(기존), 복수 `/v2/stocks/bars`(설계 후보) | `o,h,l,c,v,n,vw,t`; `feed=sip`는 미국 거래소 통합, `iex`는 IEX 한 거래소. 일봉 t는 뉴욕 날짜 시작. OHLC·v·n·VWAP은 서로 다른 체결 조건이 적용될 수 있음 | `adjustment=raw/split/dividend/spin-off/all`; split은 가격·거래량, dividend는 가격을 조정. USD 기본값은 명시 설정으로 고정. `asof=-`는 명칭 이력 연결을 끄므로 티커 일치만으로 증권 신원 확정 안 함. 문서상 2016년부터, Basic 최근15분 제한·200요청/분; 이용권한은 실제 계정 별도 | 기존 보유 SIP raw 표본만 재사용. 문서상 무료 접근과 외부 재배포 권리는 별개; 공개 OHLCV/파생지표 사용권 미확인. 새 수집·공개 연결 별도 승인 |
| KIS `/uapi/overseas-price/v1/quotations/dailyprice`(TR은 기존 KIS source register 참조) | 공식 예제 `EXCD,SYMB,GUBN,BYMD,MODP`, output1/output2와 연속조회. 기존 private 설계의 일봉 OHLCV 원천. `nvol`은 거래량, 거래대금 응답 필드는 기존 수령 계약으로 확인해야 함; 이 endpoint 문서만으로 VWAP/거래건수 정의 확정 불가 | `GUBN=0`, `MODP=0` 원주가와 조정본을 별도 보존. 종목별 통화·시장코드·실제세션·통합범위·분할 반영은 응답/공급처 근거 필요. 100행 가정으로 고정하지 않고 `tr_cont`/실제최초일 확인. 연속조회 max_depth10 예제는 서비스 역사 보증이 아님 | 기존 오너용 KIS 비공개 구조 재사용; 새 계정/키/권한 변경 없음. 기존 공식 FAQ 조사상 자기 조회 용도, 외부 제공 별도 제한. 공개 화면 데이터 원천으로 승격하지 않음 |
| IEX HIST TOPS | pcap 거래메시지→기존 `iex_hist` 마지막 정규장 round-lot 체결; IEX만의 가격. 현재 저장된 것은 OHLCV가 아님 | 원시·비조정, symbol만으로 과거 ID 확정 불가. T+1 파일, 공식 설명은 trailing12개월. 이미 보관된 과거 파일과 현재 다운로드 범위를 구분 | HIST 약관은 출처 표기와 링크 의무, 다른 시장 거래 미포함 명시. 프로젝트 raw가격 공개 보류는 유지. 공식V 기존 경로를 기술봉으로 재사용하지 않음 |
| 옛 Yahoo/Worker·Tiingo/KRX fallback | 기존 화면 경로·가드는 코드에 남아 있음 | 승인된 가격 연속성/사용권 근거 없는 창은 보류 | 새 공급처 채택·기존 권리 보류 해제 없음; 후보 탐색 반복 안 함 |

공식 확인 출처:
- [Alpaca historical bars](https://docs.alpaca.markets/us/reference/stockbars) — 문서 modified 2026-05-27.
- [Alpaca aggregation FAQ](https://docs.alpaca.markets/us/docs/market-data-faq#how-are-bars-aggregated) — 문서 modified 2026-09-21, 이번 확인.
- [Alpaca plan/history/limits](https://docs.alpaca.markets/us/docs/about-market-data-api) — 문서 modified 2026-10-06.
- [KIS 공식 dailyprice 예제](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/dailyprice/dailyprice.py) — 열람 파일 blob `4c7a88370a485606c0d87990615ad6f1eafa95ce`; 실행하지 않음.
- [IEX HIST 약관](https://www.iex.io/legal/hist-data-terms) — 이번 열람. 소스문서 사본·열람 근거는 비공개 인계 `docs/`.
- 기존 KIS 권리 조사: `docs/manual_quotes_owner/KIS_DIRECT_API_RESEARCH_26E.md`와 source JSON. 당시 26EWAIT 문구는 후속 KIS 승인 결정으로 대체된 부분이 있으며, 외부 재배포 권리로 확대하지 않는다.

### VWAP×v 채택 차단의 새 근거

Alpaca FAQ는 v와 n을 volume 갱신 허용 체결로 계산하지만, VWAP 분자·분모는 high/low 갱신과 volume 갱신이 **둘 다** 허용된 체결로 계산한다고 명시한다. 예를 들어 odd lot, seller 조건, 일봉의 extended-hours 조건은 volume만 갱신할 수 있다. 따라서 `vw * v`는 동일 체결 집합의 총액이라고 보장되지 않는다. 문서의 짧은 원문: “this volume can be different from the ‘normal’ volume field”.

이번 근거는 현재 공급처 문서의 정의이며 **2018 원본 생성 당시 구현 버전 증명은 아니다**. 기존 raw 진단 평균은 그대로 보존하고 채택값은 null이다. 사유는 `VWAP_VOLUME_SCOPE_NOT_EQUIVALENT_BY_CURRENT_PROVIDER_SPEC`로 근거표에 추가한다. 127/127 관측 여부로 이 차이를 해소하지 않는다. 실제 총액이 필요하면 동일 필터 거래별 price×size 합 또는 동일 분모 volume이 필요하지만, 해당 수집은 이번에 하지 않는다.

## 최초 적재·증분·실패 재개 설계

| 항목 | Alpaca SIP 연구 일봉 | KIS 오너용 일봉 | IEX 현행 마지막 체결 |
|---|---|---|---|
| 최초 적재 | 승인된 코드/증권 mapping 한정, raw 5년(최대약1260세션)과 요청 파라미터·페이지/응답 hash 보존. 조정본은 별도 key | 계정·종목 허용목록 승인 범위에서 원주가와 조정본 별도; 실제 응답 첫 날짜·연속 토큰으로 완료 판단 | 기존 날짜별파일 parser 공유; 현재 index존재범위만; 하루모든필요코드를한번에 decode |
| 요청량 | 기존 단일symbol경로 504코드×ceil(봉수/페이지반환수). 5년≤10000봉이면 이론상 최소504 GET, 12표본 최소12. 복수endpoint면 504×1260/10000≈64페이지 하한이나 응답이 더 작을 수 있고 기존 collector 변경/실행 승인 필요 | 응답당 N행 실측 전 요청량 확정 불가. 상한예산은 코드수×승인된최대페이지, 막힌코드추가자동수집안함 | 색인1 + 새 일자파일당1 GET(페이지/오류 제외). 파일크기·저장비용은색인확인뒤실행예산결정 |
| 권장 갱신 | 전일 뉴욕 날짜 종료 후 00:30 America/New_York부터(15분제한 이후), 하루1회·최근5거래일 겹쳐읽기. 공급처 완결 지연 실측 전 잠정시각 | 승인된 오너 클릭/기존 private 갱신 계약 유지. 정기화 후보는 미국장/공급처 일봉 완료 확인 뒤1회; 실제 완료시각 미확인이라 고정cron보류 | 기존 T+1 워크플로 유지; 기술용추가스케줄없음 |
| 캐시/중복 | provider/feed/timeframe/adjustment/currency/asof/요청범위/mapping version key. 모든페이지완료후commit, 같은bodyhash는계산재실행생략 | 계정식별값을공개key에넣지않음. 날짜·시장·symbol·MODP별key와sourcehash | 날짜·feed·sourcefilehash별1회decode |
| 실패재개 | 마지막완료페이지와opaque next token 비공개. 429는reset/Retry-After, 5xx제한재시도. 401/403은중단/권한미확인. 부분페이지는complete=false | tr_cont M/F→N을공식예제대로. 반환빈목록/최대깊이는완료로간주안함; 토큰·오류값공개금지 | 기존실패원인코드유지. 파일hash불일치시채택보류 |
| 수정치 | 이전body불변, 같은날짜새version추가. 최근5일 daily/research proposal, 월1회최근30세션검사 제안. 분할/배당사건확인시해당기준전기간재처리. 미승인정기수집없음 | MODP수정본변경을원주가수정과분리; 기업행사근거창만계산. 가격비율만으로분할확정안함 | 새파일hash는별도version; 기존결과덮어쓰지않고재계산근거연결 |

EMA/RSI/MACD의 최초 적재 길이가 바뀌면 seed가 달라진다. 최초 `input_start`를 저장하고 증분은 기존 seed상태/전체 보유 이력을 재사용한다. 재시작 때 최근120봉만 읽어 장기값과 섞지 않는다. 주봉은 기존 W1 일봉집계만 재사용하며 이번에는 주봉지표를 새로 만들지 않는다.

## 화면·운영 상태 필드

Main 제안 계약: `provider`, `feed`, `source_kind`, `source_schema`, `price_basis`, `currency`, `security_id`, `identity_status`, `source_version`, `first_session`, `last_complete_session`, `last_success_at`, `last_attempt_at`, `retrieved_at`, `published_at`, `available_at`, `observed_session`, `expected_last_session`, `revision_of`, `complete`, `stale_status`, `stale_reason`, `rights_status`, `use_scope`, `metrics`.

- 성공시각은 모든 페이지·스키마·신원/기간 검사 완료 시각이다. HTTP200/빈 응답을 성공으로 기록하지 않는다.
- `published_at`을 모르면 null, `available_at`은 실제 수령 시각. 과거 일자만 있는 일봉을 당시 가용한 PIT로 표시하지 않는다.
- stale 설계안: 마지막 완료세션이 기대완료세션보다 2거래일 이상 뒤처지면 STALE. 0/1일도 갱신시각·지연을 표시한다. 공급처 지연시각·달력/완결 근거 미확인은 UNKNOWN, 휴일을결손으로세지않음. 이는새운영관문채택이아님.
- 값 `value`와 `raw_value`를 구분하고, raw는 비공개/개발자용. `NOT_AVAILABLE`, `STALE`, `UNKNOWN`, `PARTIAL`, `RESEARCH_PRIVATE_ONLY`는 별개다.
- 합성예: `source_kind=NORMALIZED_PROVIDER_DAILY_BARS`, `signal_day=2018-02-16`, `history_count=250`, `SMA_20={raw_value:240.5,value:null,unit:SOURCE_CURRENCY_PER_SHARE,null_reasons:[IDENTITY_UNCONFIRMED]}`. 실제회사값/성과아님.

Main 남은 연결: 이 문서의 수집상태와 `technical-offline-display/1` 판독/비공개 표시, 승인 후 스케줄·권한 구현. Codex는 provider normalization·수정치 재계산을 담당한다. 오너 추가결정: 실제수집대상·예산/일정, KIS정기화, 공개 OHLCV/파생지표 사용권 및 공개범위. 패턴 신규산식/성공확률은 별도이며 이번값으로 확정하지 않는다.
