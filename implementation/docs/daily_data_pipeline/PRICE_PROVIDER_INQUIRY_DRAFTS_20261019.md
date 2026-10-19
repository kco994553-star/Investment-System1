# 가격 공급자 문의 초안 — IEX HIST · Alpaca Basic (2026-10-19, 미발송)

> **상태: 초안. 보내지 않았다.** 실제 발송은 소유자가 따로 승인한다.
> 연락처·주소는 이 저장소에 적지 않는다. **받는 곳: 공식 문의 경로 참조.**
> 발신자 이름·사이트 주소는 소유자가 채운다(〔 〕 칸).

- 작성: 2026-10-19 03:40 UTC / 2026-10-19 12:40 KST.
- 바탕: [FREE_SOURCE_COMBINATION_20261018](FREE_SOURCE_COMBINATION_20261018.md)의 결론·표 A·부록 초안. 이 문서는 IEX와 Alpaca 두 곳만 다룬다. 필드와 용도를 정확히 적었다.
- 기존 부록 초안과 다른 점: "날짜별 점수·검증 이력을 공개 저장소에 계속 남깁니다"를 뺐다. 공개는 최신 게시본 하나다. 날짜별 점수 묶음은 허락될 때만 비공개로 보관한다([V_STAGE_BREAKDOWN_AND_DCV_STATUS_20261019 보완 2](../qgv_scoring_standard/V_STAGE_BREAKDOWN_AND_DCV_STATUS_20261019.md)).
- 공통 공개 범위: 0~100 점수, 순위, 사유 문구, 커버리지, 기준일만. 원시 가격·EV·수익률·배율은 공개하지 않는다.

## 1. IEX — HIST(무료 과거 데이터)

받는 곳: IEX 시장 데이터 담당. 공식 문의 경로 참조.

### 한국어

제목: IEX HIST 데이터로 계산한 파생 점수의 공개 가능 여부 문의

안녕하세요. 저는 〔이름〕입니다. 개인이 운영하는 비영리 투자 연구 사이트(공개 GitHub 저장소와 GitHub Pages, 〔사이트 주소〕)에서 IEX HIST 데이터 이용 조건을 확인하고 싶습니다.

1. 쓰려는 자료
   - 파일: 거래일마다 공개 HIST 목록에 올라오는 TOPS 파일 1개(T+1).
   - 메시지와 필드: Trade Report Message의 symbol·price·timestamp·sale condition flags(정규장 마지막 체결 판정용), IEX 상장 종목은 Official Price Message의 공식 종가.
   - 범위: 미국 상장 약 504개 코드와 SPY, 거래일마다 종목당 값 1개.
   - 값의 이름: 화면과 파일에 "IEX 마지막 체결가(IEX_LAST_TRADE)"로 적습니다. 공식 상장시장 종가로 부르지 않습니다.
2. 처리
   - 하루 1회 GitHub Actions 실행기에서 파일을 스트리밍으로 읽습니다. 디스크·캐시·저장소에 저장하지 않습니다.
   - 종목별 값은 실행 메모리에서만 씁니다. 공개 SEC 재무 자료와 결합해 0~100 백분위 점수와 순위를 계산합니다.
   - 작업이 끝나면 원시 값과 중간 계산값을 버립니다. 로그에는 개수와 고정 코드만 남깁니다.
3. 공개
   - 익명 방문자에게 웹 화면과 내려받기 JSON으로 0~100 점수, 순위, 사유 문구(백분위 표현), 커버리지, 기준일만 공개합니다.
   - 원시 가격, EV(기업가치), 수익률, 배율, 종목별 가격 해시는 공개하지 않습니다.
   - 공개 파일은 최신 1개만 둡니다. 과거 공개본을 쌓지 않습니다.
4. 출처 표시
   - 화면과 JSON에 다음 문구와 약관 링크를 넣을 계획입니다: "Data provided for free by IEX. By accessing or using IEX Historical Data, you agree to the IEX Historical Data Terms of Use."
5. 보관
   - 원시 값은 보관하지 않습니다.
   - 검증을 위해 날짜별 점수 묶음(가격 없음)을 비공개 저장소에 보관하고, 그 해시만 공개 기록에 남기려 합니다. 허락되지 않으면 하지 않습니다.

질문:

1. 공개 HIST 목록에서 파일을 자동으로 하루 1회 내려받는 것이 허용됩니까? 계정이나 등록이 필요합니까?
2. 위 0~100 점수·순위의 웹 표시와 공개 JSON 배포가 HIST 약관 안에서 허용됩니까?
3. 파생 점수에도 §01 출처 문구가 필요합니까? 필요하다면 위치(화면·JSON)는 어떻게 해야 합니까?
4. 값을 "IEX 마지막 체결가" 기준으로 표시하는 방식이 적절합니까?
5. 날짜별 점수 묶음(가격 없음)의 비공개 보관과 그 해시의 공개가 허용됩니까?
6. 우리가 HIST 이용을 멈추거나 약관이 바뀐 뒤에도 이미 공개·보관한 점수를 유지할 수 있습니까?

감사합니다.
〔이름〕

### English

Subject: Inquiry — publishing scores derived from IEX HIST data on a non-commercial research site

Hello. My name is 〔name〕. I run a personal, non-commercial investment research site (a public GitHub repository served on GitHub Pages, 〔site address〕) and would like to confirm the permitted use of IEX HIST data.

1. Data we would use
   - Files: one TOPS file per trading day from the public HIST listing (T+1).
   - Messages and fields: Trade Report Message symbol, price, timestamp and sale condition flags (to find the last regular-session trade); for IEX-listed securities, the official closing price from the Official Price Message.
   - Scope: about 504 US-listed symbols plus SPY, one value per symbol per trading day.
   - Label: shown on pages and in files as "IEX last trade (IEX_LAST_TRADE)", never as the primary listing market's official close.
2. Processing
   - Once a day the file is read as a stream in a GitHub Actions runner. It is not saved to disk, a cache or any repository.
   - The per-symbol values exist only in the job's memory. They are combined with public SEC filings to compute 0–100 percentile scores and ranks.
   - Raw values and intermediate results are discarded when the job ends. Logs contain only counts and fixed codes.
3. Publication
   - Anonymous visitors see, on web pages and in a downloadable JSON, only 0–100 scores, ranks, reason text (in percentile terms), coverage and the basis date.
   - No raw prices, enterprise values, yields, multiples or per-symbol price hashes are published.
   - Only the latest file is public. Past public versions are not accumulated.
4. Attribution
   - We plan to show this text with a link to the terms on the pages and in the JSON: "Data provided for free by IEX. By accessing or using IEX Historical Data, you agree to the IEX Historical Data Terms of Use."
5. Retention
   - Raw values are not retained.
   - For validation we would like to keep dated score bundles (no prices) in a private repository and publish only their hashes. We will not do this unless permitted.

Questions:

1. May we download one file per day automatically from the public HIST listing? Is an account or registration required?
2. Are web display and public JSON distribution of the 0–100 scores and ranks described above permitted under the HIST terms?
3. Does the §01 attribution apply to derived scores? If so, where should it appear (pages, JSON)?
4. Is labelling the value as "IEX last trade" appropriate?
5. Is private retention of dated score bundles (no prices), with only their hashes public, permitted?
6. If we stop using HIST, or the terms change, may scores already published or retained stay in place?

Thank you.
〔name〕

## 2. Alpaca — Market Data API Basic(무료)

받는 곳: Alpaca 지원 담당. 공식 문의 경로 참조.

### 한국어

제목: Alpaca Basic 시장 데이터로 계산한 파생 점수의 공개 사이트 이용 문의

안녕하세요. 저는 〔이름〕입니다. 개인이 운영하는 비영리 투자 연구 사이트(공개 GitHub 저장소와 GitHub Pages, 〔사이트 주소〕)에서 Alpaca Market Data API Basic 이용 조건을 확인하고 싶습니다. 계정은 Basic(무료)입니다.

1. 쓰려는 자료
   - 엔드포인트: Historical bars(주식). 매개변수 `timeframe=1Day`, `feed=sip`, `adjustment=raw`, 시작·끝 = 기준 거래일 하루, `symbols`는 쉼표 목록.
   - 범위: 미국 상장 약 504개 코드와 SPY. 하루 1~2회 요청.
   - 쓰는 필드: 종가 `c`와 봉 시각 `t`만. 시가·고가·저가·거래량·VWAP·체결 수(`o`·`h`·`l`·`v`·`vw`·`n`)는 쓰지 않습니다.
   - 값의 이름: "SIP 통합 일봉 종가(SIP_CONSOLIDATED_DAILY_BAR)"로 적습니다.
2. 처리
   - 하루 1회 GitHub Actions 실행기에서 요청합니다. API 키는 저장소 비밀값에만 두고 출력하지 않습니다.
   - 값은 실행 메모리에서만 씁니다. 공개 SEC 재무 자료와 결합해 0~100 백분위 점수와 순위를 계산합니다.
   - 작업이 끝나면 원시 값과 중간 계산값을 버립니다. 디스크·캐시·저장소에 저장하지 않습니다. 로그에는 개수와 고정 코드만 남깁니다.
3. 공개
   - 익명 방문자에게 웹 화면과 내려받기 JSON으로 0~100 점수, 순위, 사유 문구(백분위 표현), 커버리지, 기준일만 공개합니다.
   - 원시 가격, EV(기업가치), 수익률, 배율, 종목별 가격 해시는 공개하지 않습니다.
   - 공개 파일은 최신 1개만 둡니다. 사이트는 무료이고 광고·유료 기능이 없습니다.
4. 출처 표시
   - 요구하시는 문구가 있으면 화면과 JSON에 그대로 넣겠습니다.
5. 보관
   - 원시 값은 보관하지 않습니다.
   - 검증을 위해 날짜별 점수 묶음(가격 없음)을 비공개 저장소에 보관하고, 그 해시만 공개 기록에 남기려 합니다. 허락되지 않으면 하지 않습니다.

질문:

1. 약관의 "개인·비상업 목적"에 위와 같은 공개 비영리 사이트가 포함됩니까?
2. 이 사이트가 "User Application"에 해당해 30일 사전 서면 통지가 필요합니까? 필요하다면 이 문의를 통지로 보아도 됩니까?
3. 서버 쪽(GitHub Actions)에서 데이터를 받아 계산하는 것이 Basic에서 허용됩니까?
4. 0~100 점수와 순위가 공개 표시에 서면 동의가 필요한 "Content"에 해당합니까? 해당한다면 위 범위로 동의해 주실 수 있습니까?
5. 날짜별 점수 묶음(가격 없음)의 비공개 보관과 그 해시의 공개가 허용됩니까? 원시 값의 비공개 임시 보관이 허용된다면 최대 기간은 얼마입니까?
6. 계정이 끝난 뒤에도 이미 공개·보관한 점수를 유지할 수 있습니까?
7. 필요한 출처 문구가 있습니까?
8. Basic에서 허용되지 않는다면 어떤 플랜이나 계약이 필요합니까?

감사합니다.
〔이름〕

### English

Subject: Inquiry — using Alpaca Basic market data for derived scores on a public non-commercial site

Hello. My name is 〔name〕. I run a personal, non-commercial investment research site (a public GitHub repository served on GitHub Pages, 〔site address〕) and would like to confirm the permitted use of the Alpaca Market Data API on the Basic (free) plan.

1. Data we would use
   - Endpoint: stock Historical bars, with `timeframe=1Day`, `feed=sip`, `adjustment=raw`, start and end set to the one basis trading day, and `symbols` as a comma-separated list.
   - Scope: about 504 US-listed symbols plus SPY, in one or two requests per day.
   - Fields used: only the close `c` and the bar time `t`. Open, high, low, volume, VWAP and trade count (`o`, `h`, `l`, `v`, `vw`, `n`) are not used.
   - Label: shown as "SIP consolidated daily bar close (SIP_CONSOLIDATED_DAILY_BAR)".
2. Processing
   - Requested once a day from a GitHub Actions runner. The API key is kept only as a repository secret and never printed.
   - Values exist only in the job's memory. They are combined with public SEC filings to compute 0–100 percentile scores and ranks.
   - Raw values and intermediate results are discarded when the job ends. Nothing is saved to disk, a cache or any repository. Logs contain only counts and fixed codes.
3. Publication
   - Anonymous visitors see, on web pages and in a downloadable JSON, only 0–100 scores, ranks, reason text (in percentile terms), coverage and the basis date.
   - No raw prices, enterprise values, yields, multiples or per-symbol price hashes are published.
   - Only the latest file is public. The site is free, with no advertising or paid features.
4. Attribution
   - We will show any attribution text you require on the pages and in the JSON.
5. Retention
   - Raw values are not retained.
   - For validation we would like to keep dated score bundles (no prices) in a private repository and publish only their hashes. We will not do this unless permitted.

Questions:

1. Does "personal and non-commercial purposes" in your terms cover a public non-commercial site as described?
2. Is this site a "User Application" that needs 30 days' advance written notice? If so, may this message serve as that notice?
3. Is server-side retrieval and computation in GitHub Actions permitted on Basic?
4. Are the 0–100 scores and ranks "Content" whose public display needs your written consent? If so, can you consent to the scope above?
5. Is private retention of dated score bundles (no prices), with only their hashes public, permitted? If private temporary storage of raw values is permitted, for how long?
6. May scores already published or retained stay in place after the account ends?
7. Is any attribution text required?
8. If this is not permitted on Basic, which plan or agreement would permit it?

Thank you.
〔name〕

## 3. 보내기 전 확인

- 소유자 발송 승인. 받는 곳은 각 공급자의 공식 문의 경로에서 소유자가 고른다. 저장소에는 적지 않는다.
- 발신자 이름·사이트 주소 기입.
- 답을 받으면 결정 기록(GSQ append-only)과 FREE_SOURCE 표 A 칸을 갱신한다. 답장 원문에 연락처가 있으면 저장소에 옮기지 않는다.
