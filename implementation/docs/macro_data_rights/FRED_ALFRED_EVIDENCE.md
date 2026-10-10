# FRED와 ALFRED 이용권 및 PIT 조사

확인일: **2026-10-10 UTC**. 코드 검토 기준: canonical `ee039041ae7f5cb94e6a127930c7e43effb811ec`. 공식 공개 약관·API 설명·ALFRED 도움말만 조회했으며 실제 observations API, CSV, 가격, Secret, 환경변수 값은 조회하지 않았다. 공급자 모듈을 import하거나 실행하지 않았고 저장소 코드·테스트·workflow·ruleset·AUTONOMY_MODE·git state를 수정하지 않았다.

**이번 프로그램의 FRED/ALFRED 수집·저장·캐시·DB·AI 개발 경로는 `BLOCKED_UNLESS_WRITTEN_PERMISSION`으로 유지하는 것이 타당하다.** 무료·본인 전용(GSQ-007)은 공식 금지 조항의 예외가 아니다. 원기관 공공 통계를 직접 이용할 권리와 FRED 경유 접근 약관은 별도로 판정해야 한다. ALFRED는 날짜 단위 vintage를 지원하지만 장중 이용 가능시각을 보장하지 않는다.

## 1. 현재 확인된 약관과 예외

아래 FRED 페이지는 모두 **2026-10-10 HTTP 200**으로 확인했다. 짧은 인용의 생략은 해당 조항의 의미를 축소하지 않는다.

| 항목 | 공식 URL과 짧은 원문 | 확인된 범위와 이번 경로 판정 |
| --- | --- | --- |
| 적용 대상 | [FRED Legal](https://fred.stlouisfed.org/legal/#full-fred-terms), Introduction: “include but are not limited to FRED®, ALFRED® … the FRED® API” | ALFRED·그래프·웹페이지·API도 일반 서비스 약관 적용 대상이다. CSV의 무키 접근은 약관 제외 근거가 아니다. |
| 무료 개인 열람·다운로드 | [General License](https://fred.stlouisfed.org/legal/#property-rights): “solely for your personal, non-commercial use”; “Such license is subject to these Terms of Use.” | 저작권 표시를 유지한 개인 비상업 이용의 제한적 라이선스는 있다. 모든 저장 방식·자동화·AI 개발을 허가하는 포괄적 예외는 아니다. |
| 모든 용도에 적용되는 금지 | [Summarized Terms](https://fred.stlouisfed.org/legal/#fred-terms): “All use of FRED data—including non-commercial, educational, and personal use—is subject to the following prohibitions.” | 개인·무료·교육용이라는 이유로 금지 조항을 면제받지 않는다. |
| 소프트웨어·시스템·ML/AI 개발·훈련 | [API 추가 조건](https://fred.stlouisfed.org/legal/#api), Prohibitions (k): “in connection with the development or training of any software program or system or machine learning” | LLM·deep learning·generative AI 등을 예로 명시한다. 해당 API 조항에 본인용·무료 예외가 없다. 일반 요약 금지에도 동일한 개발·훈련 제한이 있다. |
| 저장·캐시·archive·DB | [API 추가 조건](https://fred.stlouisfed.org/legal/#api), Prohibitions (l): “storing, caching, or archiving any portion”; “incorporating any FRED® Content in any database, compilation, archive, cache, or other medium.” | 원본 archive, DB, 프로그램 캐시를 자동 허용할 수 없다. API (l)에 개인 디스크나 메모리 캐시 예외는 명시되지 않았다. |
| 서비스 전반의 저장·변환·배포 | [일반 Prohibitions](https://fred.stlouisfed.org/legal/#prohibitions): “You may not, without the Bank's prior written consent”; (p) “Store, cache, or archive any portion”; (q) “Modify, copy, distribute, create derivative works of …” | 일반 금지에는 은행의 사전 서면 동의 경로가 있다. API 제한의 해제 범위도 서면으로 확인해야 하며 단순 citation은 동의가 아니다. |
| 제3자 제공 | [API 추가 조건](https://fred.stlouisfed.org/legal/#api), (l): “providing any stored, cached, or archived portion … to any third party” | 공개 Git/Pages/JSON/Actions artifact와 외부 AI 서비스에 전달하는 경로도 별도 검토 대상이다. 개인에게 무료 제공하는 것은 자동 재배포 허가가 아니다. |
| 원권리자 저작권 | [Property Rights](https://fred.stlouisfed.org/legal/#property-rights): “Neither … provision … nor your use … override the data series owners' copyrights, requirements and restrictions.” | FRED 서비스 이용조건과 시리즈 원권리자 조건을 모두 통과해야 한다. FRED가 원권리자를 대신해 허가할 수 없다. |
| 별도 API Terms | [API Terms](https://fred.stlouisfed.org/docs/api/terms_of_use.html): “The Terms of Use shall include … The Federal Reserve Bank of St. Louis web site Legal Terms” | 이 페이지에는 현재 Legal API (k)/(l)가 보이지 않는다. 현재 공개된 두 페이지의 차이는 확인됐지만 추가 허가·면책을 뜻하지 않는다. Website Legal도 포함한다고 명시되어 있다. |
| API 표시·키 | [API Legal](https://fred.stlouisfed.org/legal/#api): “This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.” [API Key 문서](https://fred.stlouisfed.org/docs/api/api_key.html): “All users of an application shall use their own API key.” | 사용권 확보 후에도 면책 표시·앱별 키·사용자 본인 키 등 조건이 남는다. 이번 조사에서 키를 발급·조회·검증하지 않았다. |

**명시적 허용과 저장 금지의 해석 여지는 남아 있다.** General License는 개인 다운로드를 허용하고 요약은 일부 API 앱을 예로 들지만, 전체 약관은 저장·캐시와 개발·훈련을 넓게 제한한다. 이 차이를 “개인 연구니까 DB와 AI에 써도 된다”로 해소할 공식 예외·서면 허가는 확인되지 않았다. 페이지의 최초 개정일·발효일은 확인하지 못했으므로 2026-10-10을 약관 개정일이라고 쓰지 않는다.

**AI의 모든 추론이 금지됐다고 단정할 근거는 아니다.** 같은 Legal 페이지는 OpenAI·Anthropic 등 AI Host Platform의 FRED MCP Connector도 정의한다. 다만 [MCP 추가 조건](https://fred.stlouisfed.org/legal/#mcp)은 원권리자 조건과 저장·캐시 금지를 유지한다. Connector 존재를 독자적 수집·archive·개발·훈련·제3자 재배포 허가로 확대할 수 없다. 순수한 질문 응답, 개발·훈련, 모델 제공업체로의 데이터 전달, 영구 저장은 구분해서 적용 범위를 확인해야 한다.

## 2. 시리즈 저작권과 ICE 예외

[공식 FRED Legal의 copyright 유형](https://fred.stlouisfed.org/legal/#fred-terms)은 다음 세 유형을 구분한다. 아래 허용도 금지된 사용을 하지 않는다는 전제에 종속된다.

| 유형 | 짧은 원문과 의미 |
| --- | --- |
| Copyrighted: Pre-approval required | “For any other use, you must obtain permission from the copyright holder.” 비상업 교육·본인 개인 이용 외의 사용은 원권리자 허가가 필요하다. 무료 공개·재배포까지 허가된 것으로 볼 수 없다. |
| Copyrighted: Citation required | “provided you have not engaged in any prohibited uses” 및 proper attribution. citation이 금지된 저장·개발·훈련을 허용하지 않는다. |
| Public Domain: Citation requested | “provided you do not engage in any prohibited use.” 시리즈의 public-domain 표기가 FRED 경유 서비스 약관을 제거하지 않는다. |

canonical `fred_csv.py:21`의 risk 후보는 **BAMLH0A0HYM2**다. 기존 [PIPELINE_DESIGN.md:161](https://github.com/kco994553-star/Investment-System1/blob/ee039041ae7f5cb94e6a127930c7e43effb811ec/implementation/docs/daily_data_pipeline/PIPELINE_DESIGN.md#L161) 및 FRED-8 기록은 [공식 ALFRED series metadata/notes URL](https://alfred.stlouisfed.org/series?seid=BAMLH0A0HYM2)을 **2026-10-09 ICE credit 사전 승인 근거**로 참조한다. 이 기록은 정부 통계와 다른 원권리자 제약이 있다는 기존 근거이며 이번 프로그램에 대한 ICE 서면 허가는 아니다.

**현재 확인과 미확인을 구분한다.** 이번에는 관측값이 포함될 수 있는 시리즈 페이지를 새로 요청하지 않았으므로 BAMLH0A0HYM2의 2026-10-10 정확한 notes 전문·현재 copyright 태그·파생물 라이선스·빈티지 coverage는 재확인하지 않았다. [ICE Terms](https://www.ice.com/terms-of-use)와 [ICE Indices 안내](https://www.ice.com/market-data/indices)는 2026-10-10 요청에 HTTP 403이어서 본문을 확인하지 못했다. 무료 다운로드 가능성, 개인용 예외 또는 출처 표시만으로 공개 재배포·AI 이용권을 확정할 수 없다. GSQ-007의 가격·가격 기반 파생값 공개 금지도 독립적으로 유지한다.

## 3. Vintage 날짜와 실제 이용 가능시각

아래 공식 문서는 **2026-10-10 HTTP 200** 확인 결과다. 실제 API 호출 결과나 실제 통계 값은 아니다.

| 공식 문서 | 짧은 원문 | 확인된 의미 |
| --- | --- | --- |
| [Real-Time Periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) | “when facts were true or when information was known until it changed”; “a (closed, closed) period” | `realtime_start/end`는 `YYYY-MM-DD` 날짜 구간이며 양 끝을 포함한다. 원기관 발표 timestamp가 아니다. |
| [series/observations 문서](https://fred.stlouisfed.org/docs/api/fred/series_observations.html) | “default: today's date”; “as it existed on these specified dates in history” | observation 기간과 as-of/vintage는 별개다. 과거 observation date만 제한하면 오늘 수정본을 과거 데이터처럼 사용할 수 있다. |
| [series/vintagedates](https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html) | “excluding release dates when the data for the series did not change.” | 신규·수정값이 나온 날짜 목록이다. 값이 불변인 발표와 모든 발표 이벤트를 포괄하지 않는다. |
| [ALFRED Download Data Help](https://alfred.stlouisfed.org/help/downloaddata) | “The observation date is the date for which a data value is measuring.” | 관측일은 측정 대상 기간이며 발표일이 아니다. real-time start/end는 값이 최신으로 유효했던 첫/마지막 vintage 날짜다. Initial Release Only는 최초값만 선택해 이후 수정값 포함 스냅샷과 다르다. |
| [release/dates](https://fred.stlouisfed.org/docs/api/fred/release_dates.html), [releases/dates](https://fred.stlouisfed.org/docs/api/fred/releases_dates.html) | “do not necessarily represent when data will be available on the FRED or ALFRED websites.” | 원천 release date와 FRED/ALFRED 조회 가능시점은 다르다. 발표 캘린더가 수신 receipt를 대신하지 않는다. |
| [ALFRED FAQ](https://alfred.stlouisfed.org/help) | “typically within one business day.” | 발표 후 통상 한 영업일 안에 추가한다는 설명이다. 최대 지연·무지연·SLA 보장이 아니다. |
| 같은 [ALFRED FAQ](https://alfred.stlouisfed.org/help) | “the actual release date as provided by the source”; “the date that the series was first available … in … FRED” | release date 결정 순서는 원천 실제 날짜 → 데이터 제공업체 날짜 → FRED 최초 이용 가능 날짜다. 모든 기록이 원천 실제 발표일이라는 보장은 없다. |
| [series/updates](https://fred.stlouisfed.org/docs/api/fred/series_updates.html) | “when observations were updated on the FRED® server (attribute last_updated)”; “limited to … the last two weeks.” | FRED update timestamp는 존재한다. 이것이 모든 과거 observation vintage의 원천 발표시각·최초 availability를 제공한다는 근거는 확인되지 않았다. |

**확인:** 날짜 단위 과거 수정본 선택 기능. **미확인:** 개별 시리즈의 모든 과거 빈티지 완전성, 동일일 여러 변경 순서, 원기관 발표시각·시간대, 각 과거 빈티지의 최초 FRED 조회 가능시각. 따라서 “timestamp가 전혀 없다”도 부정확하고 “vintage date만 있으면 장중 PIT가 된다”도 부정확하다.

장중 PIT에는 관측기간, 원기관 발표일·시각/시간대, vintage·revision 관계, FRED 반영 근거, 시스템 `acquired_at`/최초 수신 기록을 구분해야 한다. `available_at <= decision_time`을 입증하지 못하면 strict PIT 입력으로 통과시키지 않는다. 다음 영업일 사용 등의 보수적 지연은 명시적 가정이며 FAQ가 보장하는 PIT는 아니다.

## 4. Canonical 공급자 코드의 읽기 전용 검토

두 파일을 canonical `git show`로 확인했고 현재 파일의 동일 본문도 읽었다. 함수 실행·import·테스트·네트워크 수집은 하지 않았다.

- [fred_csv.py:17](https://github.com/kco994553-star/Investment-System1/blob/ee039041ae7f5cb94e6a127930c7e43effb811ec/implementation/src/investment_system/providers/fred_csv.py#L17)는 `fredgraph.csv`를 사용한다. `CURRENT_REVISED_NOT_ALFRED` 표기는 적절한 한계 표시다. [58행](https://github.com/kco994553-star/Investment-System1/blob/ee039041ae7f5cb94e6a127930c7e43effb811ec/implementation/src/investment_system/providers/fred_csv.py#L58)의 필터는 observation date만 비교하므로 당시 발표값·수정 전 값·원 발표시각을 증명하지 않는다. 무키 CSV도 FRED Services 적용 범위에 있다.
- [fred_alfred.py:48](https://github.com/kco994553-star/Investment-System1/blob/ee039041ae7f5cb94e6a127930c7e43effb811ec/implementation/src/investment_system/providers/fred_alfred.py#L48)는 as-of를 날짜로 잘라 `realtime_start=end=day`를 지정한다. 날짜 단위 스냅샷 선택으로는 의미가 있으나 장중 입력 시각은 사라진다.
- [fred_alfred.py:86](https://github.com/kco994553-star/Investment-System1/blob/ee039041ae7f5cb94e6a127930c7e43effb811ec/implementation/src/investment_system/providers/fred_alfred.py#L86)는 `realtime_end`를 우선 사용해 `available_at`을 UTC 자정으로 만든다. real-time 기간의 종료일·요청 날짜를 실제 최초 공개시각으로 볼 공식 근거가 없다. `available_at <= as_of` 비교만으로 장중 PIT를 입증하지 못한다.
- [fred_alfred.py:23](https://github.com/kco994553-star/Investment-System1/blob/ee039041ae7f5cb94e6a127930c7e43effb811ec/implementation/src/investment_system/providers/fred_alfred.py#L23) 및 [73행](https://github.com/kco994553-star/Investment-System1/blob/ee039041ae7f5cb94e6a127930c7e43effb811ec/implementation/src/investment_system/providers/fred_alfred.py#L73)은 응답 payload를 모듈 캐시에 보관한다. 현재 Legal의 API (l)에는 이 캐시를 허용하는 개인용 예외가 확인되지 않았다. 기존 구현이 있다는 사실은 사용권의 증거가 아니다.
- 두 공급자가 공유하는 것은 **5개 PROVISIONAL series 매핑**이다. 이번 권리/PIT 확인은 8축 완성, 현재 응답 완전성, 실데이터 검증 또는 운영 승격의 증거가 아니다.

## 5. 권고와 남은 제약

1. 이번 저장·개발 경로의 FRED/ALFRED 상태는 `BLOCKED_UNLESS_WRITTEN_PERMISSION`으로 유지한다. 은행 서비스 이용권과 ICE 등 원권리자 권한은 각각 확보해야 한다. 요청할 서면 범위에는 개인 서버/Worker 수집, 디스크·DB·메모리 캐시, 변환·기존 계산, 외부 AI 전달·개발·훈련, 보관 기간과 삭제, 공개·제3자 재배포가 포함돼야 한다.
2. 무료·본인 전용 대안은 원기관의 공식 공개 자료를 **직접** 이용하는 후보를 우선 검토한다. 해당 기관의 저장·변환·재사용권과 발표본·timestamp를 별도로 확인한다. 원기관 public domain을 FRED 접근 약관의 예외로 설명하지 않는다.
3. ICE credit나 당시 consensus 등 권리·시간 근거가 없는 입력은 누락 상태를 유지한다. 은행대출 등 다른 자료를 동등한 HY spread로 취급하거나 임의로 8축을 채우지 않는다.
4. ALFRED의 날짜 단위 vintage 지원과 장중 strict PIT는 다른 검증 항목이다. 현재 CSV·UTC 자정 치환·latest-data fallback으로 과거 의사결정의 입력 가용성을 확정하지 않는다.

서면 허가, 시리즈별 최신 권리 전문, 빈티지 coverage 및 실제 발표/수신시각 검증은 아직 완료되지 않았다. 이 보고서는 공개 약관과 문서에 근거한 경로 판정이며 수집·보관·게시를 활성화하는 승인이 아니다.
