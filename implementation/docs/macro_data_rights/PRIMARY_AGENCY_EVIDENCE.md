# 원기관 매크로 데이터 이용권·PIT 조사

확인일: **2026-10-10 UTC**. 조사 기준 저장소: `Investment-System1`, canonical `ee039041ae7f5cb94e6a127930c7e43effb811ec`. 공식 약관·API 설명·방법론·시리즈 설명·archive 목록만 열람했다. 실제 observations/가격 API, 데이터 파일 다운로드, 인증·가입·Secret/env/key 조회를 실행하지 않았다. 조사 에이전트는 저장소·코드·tests·workflow·Git/GitHub 상태를 변경하지 않았다. 이 파일은 원기관별 권리 근거 조사이며 공급자/지표 채택이나 Macro 방법론 승격이 아니다.

GSQ-007의 **무료 + 본인 전용** 조건을 이번 후보 검토의 경계로 적용한다. 사용자 결정은 공급자 약관의 허가를 대신하지 않는다. 정부 작성 통계의 공개 재사용 허용과 공급자 접근 약관, 제3자 권리, 실제 PIT 검증은 각각 따로 확인해야 한다. 아래 재배포 판정은 원기관 법적 이용조건의 근거이며, 이 작업의 공개 재배포·운영 수집 승인이 아니다.

## BLS

| 항목 | 원문에 따른 판정 |
| --- | --- |
| 정부 데이터·예외 | 기본 출판물은 public domain. **이전에 저작권이 설정된 사진·일러스트는 예외**. BLS emblem은 등록 상표이며 API TOS는 비후원 제품의 BLS logo 사용도 금지. [BLS-1, BLS-2] |
| 저장·보존 | 정부 작성 통계 원자료의 내려받기·개인 저장 후보는 공개 재사용 및 TOS의 Secondary Use 문구로 뒷받침됨. 읽은 TOS에 별도 cache/archive 기간 제한 없음. 조회일·출처·수정 계보를 보존하되 BLS가 내려받은 뒤 품질·시의성을 보증한다고 표시할 수 없음. [BLS-1, BLS-2] |
| 변환 | 공개 재료를 계산·가공하는 후보는 가능. API 소개도 raw data를 consume/manipulate해 앱을 만들도록 안내. 다만 **변형하거나 잘못 표현한 결과를 BLS.gov 원본이라고 계속 인용하는 것은 금지**. 원자료 출처와 자체 계산 결과를 구분해야 함. [BLS-2, BLS-4] |
| 재배포 | 공개 통계 원자료의 복제·재이용은 기본 public-domain 근거가 있음. 사진·일러스트·상표와 제3자 권리는 제외. API 조회일 및 TOS 지정 면책문구를 적용해야 함. 무료/개인 전용이라는 사용자의 작업 범위를 공개 데이터 파이프라인 허가로 확대하지 않음. [BLS-1, BLS-2] |
| 개인·무료·한도 | public use API 후보. 무등록 v1: 25 queries/day, 25 series/query, 10 years/query. 등록 v2: 500/day, 50 series/query, 20 years/query. 둘 다 50 requests/10 seconds. v2 등록은 연 1회 갱신. 문서에 요금 부과는 표시되지 않지만 한도는 접근 조건이며 한도 우회 시 차단 가능. 실제 키나 이용 자격은 확인하지 않음. [BLS-3] |
| AI 범위 | 읽은 저작권 정책과 API TOS에 AI/ML 전용 금지 조항이 없고 Secondary Use는 end-use controls를 두지 않는다고 명시. 따라서 **정부 작성 공개 통계의 본인 분석·계산·AI 입력 후보**는 일반 재사용 근거로 검토 가능. AI 학습/개발에 관한 별도 명시 허가·보증을 받은 것으로 기록하지 않으며 제3자 예외와 TOS는 유지. [BLS-1, BLS-2] |
| PIT·vintage | 현재 API가 제공하는 **historical timeseries**는 관측기간의 과거이지 당시 이용 가능했던 빈티지의 증거가 아님. 문서의 `startyear/endyear`나 aspects/catalog는 ALFRED식 as-of 선택 근거가 아님. Archived News Releases와 과거 발표 일정이 별도 존재하지만 범위·정정 여부·실제 공개 시각·각 series의 revision lineage를 대조하기 전까지 strict PIT로 판정할 수 없음. [BLS-3~7, BLS-12] |

BLS API 이용 시 TOS가 요구하는 원문은 다음과 같다: **“BLS.gov cannot vouch for the data or analyses derived from these data after the data have been retrieved from BLS.gov.”** 조회일도 인용해야 한다. 가공 지표에 BLS를 원자료 출처로 밝히는 것과 BLS가 그 계산을 생산·인증했다고 주장하는 것을 구분한다. [BLS-2]

BLS CPI 계절조정 문서는 매년 재산정으로 이전 5년의 계절조정 지수가 수정될 수 있다고 설명한다. 최신 조회로 과거기간 값을 받았다는 사실만으로 당시 값이 복원됐다고 볼 수 없다. release archive는 이미 공개된 발표본을 찾는 후보이며, 현재 archive 게시일·수정일이 원 발표의 실제 공개 시각을 대신하지 않는다. 과거 schedule은 예정 시각의 증거이므로 실제 지연·정정·다시 게시된 시각을 별도로 검증해야 한다. [BLS-5~7]

### BLS 공식 근거 — 모두 2026-10-10 확인

| ID | URL | 짧은 원문 인용·문맥 |
| --- | --- | --- |
| BLS-1 | https://www.bls.gov/bls/linksite.htm | “everything that we publish ... is in the public domain, except for previously copyrighted photographs and illustrations”; “You are free to use our public domain material without specific permission”; BLS source citation 요청. |
| BLS-2 | https://www.bls.gov/developers/termsOfService.htm | “Data accessed through BLS.gov do not, and should not, include controls over its end use”; “Users may not modify or falsely represent content ... and still cite the source as BLS.gov.” 한도 우회 시 접근 차단, 제3자 IP 비침해, ‘as is/as-available’ 조건. |
| BLS-3 | https://www.bls.gov/developers/api_faqs.htm | “Registered users may request up to 500 queries daily. Unregistered users may request up to 25 queries daily”; “50 requests per 10 seconds”; “Users must renew registration ... at least once a year.” 표와 개별 설명을 함께 확인. |
| BLS-4 | https://www.bls.gov/bls/api_features.htm | “consume and manipulate raw data ... to create a wide range of applications”; “retrieve published historical time series data”. Historical은 PIT/vintage 전용 계약이 아님. |
| BLS-5 | https://www.bls.gov/bls/news-release/ | “Data in archived news releases may have been revised or corrected in subsequent releases.” archive 목록만 확인; 발표본문의 관측값은 수집하지 않음. |
| BLS-6 | https://www.bls.gov/bls/archived_sched.htm | “Schedules for Selected BLS Economic News Releases for Prior Years”. 과거 예정 일정의 목록, 실제 API 게시시각 보증 아님. |
| BLS-7 | https://www.bls.gov/cpi/seasonal-adjustment/ | “This routine annual recalculation may result in revisions to seasonally adjusted indexes for the previous 5 years.” 계절조정 수정 설명만 이용. |
| BLS-8 | https://www.bls.gov/opub/hom/cpi/home.htm | “The CPI measures inflation as experienced by consumers in their day-to-day living expenses.” Inflation 후보 연결의 정의 근거. |
| BLS-9 | https://www.bls.gov/opub/hom/ces/home.htm | “estimates of nonfarm employment, hours, and earnings of workers on payrolls.” Labor/성장 보조 후보의 범위 설명. |
| BLS-10 | https://www.bls.gov/opub/hom/cps/home.htm | “Current Population Survey: Overview”. 고용·실업 노동시장 설명 문서. |
| BLS-11 | https://www.bls.gov/opub/hom/jlt/home.htm | “monthly and annual estimates of job openings, hires, and separations”. Labor 후보 연결의 범위 근거. |
| BLS-12 | https://www.bls.gov/developers/api_signature_v2.htm | “retrieve data ... within a set time frame of up to 20 years”; `startyear/endyear`, calculations/annual averages/aspects/catalog의 signature 설명. 과거 관측기간 조회와 당시 빈티지 선택을 구분. |

## BEA

| 항목 | 원문에 따른 판정 |
| --- | --- |
| 정부 데이터·예외 | **unless stated otherwise**, BEA 사이트의 정보는 public domain이고 use/reproduce에 개별 허가 불필요. 외부 linked website의 저작권 자료에 대한 허가를 BEA가 부여할 수 없다고 명시. BEA 로고는 link identity 용도 이외 금지, 후원·추천 인상 금지. [BEA-1] |
| 저장·보존 | 정부 작성 공개 통계 원자료의 개인 저장 후보는 use/reproduce 정책 및 API의 retrieve/analyze 허용으로 뒷받침됨. 읽은 API TOS에 별도 cache/archive 기간 금지 없음. 제품별 otherwise 표기·제3자 권리·API 조건 확인을 유지. [BEA-1, BEA-2] |
| 변환 | API는 search/display/analyze/retrieve/view 서비스를 개발하는 용도를 명시적으로 허용. **변형·오표현 결과를 BEA 원본이라고 claim하는 것은 금지**. 자체 계산/AI 결과와 BEA 원자료를 구분해야 함. [BEA-2] |
| 재배포 | 정부 작성 정보의 use/reproduce에 별도 permission 불필요라는 일반 근거가 있음. API를 활용하는 앱은 지정 notice를 눈에 띄게 표시해야 함. 외부 저작권·별도 고지 예외에는 이 허용을 적용할 수 없음. 이번 무료+개인 범위를 공개 파이프라인 승인으로 확대하지 않음. [BEA-1, BEA-2] |
| 개인·무료·한도 | 공식 public API 후보이며 등록과 고유 UserID가 필요. API docs/guide/TOS에 요금 부과 표시 없음; 등록·약관 동의·정상 이메일 필요. 2026-04-20 guide: 100 requests/min, 100MB/min, 30 errors/min. 초과 시 현재 1분 timeout(동적 변경 가능), HTTP429 및 Retry-After. 한도는 변경될 수 있음. 가입/키/인증 성공은 확인하지 않음. [BEA-3, BEA-4] |
| AI 범위 | 읽은 정책·2페이지 API TOS에 AI/ML 전용 금지 조항 없음. 정부 작성 공개 통계의 본인 분석·계산·AI 입력 후보는 일반 공개 재사용 및 명시된 analyze/service 개발 근거로 검토 가능. **별도 AI 훈련 라이선스를 받았다는 뜻은 아님**. 외부 자료에 권리 이식 불가, 제3자 IP 비침해·잘못된 BEA attribution 금지 조건 유지. [BEA-1, BEA-2] |
| PIT·vintage | Guide는 현재 접근 가능한 데이터와 metadata를 설명하고 일반 GDP/NIPA의 `Year/Frequency/TableName` 조회가 당시 빈티지 선택임을 보증하지 않음. BEA iTable에 대해 공식 citing 문서는 **most recently released data만 표시하고 vintage를 식별하지 않는다고 명시**. API와 iTable을 무조건 같은 endpoint라고 단정하지 않지만 어느 쪽도 단순 과거기간 조회만으로 strict PIT를 증명하지 못함. News Release Archive·Data Archive·GDP/GDI Vintage History 링크는 후보 근거이지 모든 시리즈/시각의 완전한 빈티지 계약이 아님. [BEA-3, BEA-5~9] |

BEA API를 쓰는 서비스는 다음 notice를 prominent하게 표시해야 한다: **“This product uses the Bureau of Economic Analysis (BEA) Data API but is not endorsed or certified by BEA.”** [BEA-2]

BEA archive는 “research only”이고 “Data may be superseded”라고 안내한다. Data Archive 공식 HTML은 확인했으나 정적 본문에 개별 빈티지 범위·완전성 설명이 나타나지 않아 추가 데이터 요청을 하지 않았다. GDP 메타데이터 페이지에 **Vintage History of Quarterly GDP and GDI Estimates** 링크가 있으나 XLSX를 내려받지 않았다. 그러므로 이번 조사에서 빈티지 지원의 존재 후보와 전체 역사 복원의 검증 완료를 구분한다. [BEA-6~8]

BEA는 공개 일정에 맞춰 발표하고 공식 발표 전 무단 공개를 막는 절차를 문서화한다. 그러나 계획된 발표시각, 실제 release 페이지 공개, API 반영, 나중 archive에 추가/정정한 시각은 같은 시간이 아니다. 과거 발표본을 확보한 뒤에도 관측기간·estimate type/빈티지·원 발표시각과 timezone·correction history·acquired_at을 별도로 검증해야 한다. Archive 링크나 웹 페이지 수정일만으로 과거 이용가능 시각을 백필하지 않는다. [BEA-5, BEA-6, BEA-9]

### BEA 공식 근거 — 모두 2026-10-10 확인

| ID | URL | 짧은 원문 인용·문맥 |
| --- | --- | --- |
| BEA-1 | https://www.bea.gov/about/policies-and-information/linking | “unless stated otherwise, the information posted ... is in the public domain and may be used or reproduced without specific permission”; “BEA cannot authorize the use of copyrighted materials contained in linked Web sites.” Source: U.S. Bureau of Economic Analysis 인용 요청. |
| BEA-2 | https://apps.bea.gov/API/_pdf/bea_api_tos.pdf | “You may use the BEA API to develop a service or service to search, display, analyze, retrieve, view and otherwise ‘get’ information”; “You may not modify or falsely represent content ... and still claim the source is the BEA.” Attribution notice·API 제한·제3자 IP·보증 부인 조건 포함. 가입 페이지가 링크하는 공식 2p PDF를 열람. |
| BEA-3 | https://apps.bea.gov/api/_pdf/bea_web_service_api_user_guide.pdf | “discover the current data accessible through the API”; “Number of requests per minute (100)”, “Data volume ... (100 MB)”, “Errors per minute (30)”; “will continue to be evaluated and adjusted”. 2026-04-20 문서. 문서의 샘플 데이터는 실제 API 응답 검증이 아님. |
| BEA-4 | https://apps.bea.gov/API/docs/index.htm | “This API is available to users who have registered with us”; “a unique 36-character UserID”. 등록은 수행하지 않음. |
| BEA-5 | https://www.bea.gov/help/guidelines-for-citing-bea | “The BEA interactive data application does not identify the ‘vintage’ of an estimate. It only displays the most recently released data.” 빈티지와 accessed date 인용 설명. |
| BEA-6 | https://www.bea.gov/news/archive | “this archive is provided for research only. Data may be superseded.” 자료 파일은 받지 않음. |
| BEA-7 | https://apps.bea.gov/histdatacore/index.html → https://apps.bea.gov/histdata/index.html | 공식 archive 페이지의 “Data Archive” 제목과 redirect 확인. 정적 HTML만으로 개별 자료 범위·빈티지·시각 완전성은 미확인. |
| BEA-8 | https://www.bea.gov/data/gdp/gross-domestic-product | “Vintage History of Quarterly Gross Domestic Product (GDP) and Gross Domestic Income (GDI) Estimates” 다운로드 링크 존재만 확인. 연결 데이터 파일·실제 관측값은 받지 않음. |
| BEA-9 | https://www.bea.gov/about/policies-and-information/data-dissemination | “data are not disseminated before the official release time, except as authorized ...”; “Releases the data according to an announced schedule”. 공개 전 예외와 unforeseen circumstances가 명시되어 예정 일정이 모든 실제 제공시각의 보증은 아님. |
| BEA-10 | https://www.bea.gov/open-data | “NIPA tables provide data for domestic product and income, government receipts and expenditures, foreign transactions, saving and investment, and employment by industry.” Growth/Fiscal 및 Labor 보조 후보 범위. 국제계정은 국제거래/금융자산·부채 범위이며 직접 환율 시리즈를 의미하지 않음. |
| BEA-11 | https://www.bea.gov/data/personal-consumption-expenditures-price-index | “The PCE price index ... reflects changes in the prices of goods and services purchased by consumers”. 정의와 주기 설명만 이용, 실제 관측값은 수집하지 않음. |
| BEA-12 | https://www.bea.gov/resources/for-developers | “Quickly and conveniently pull the latest data from the API”; “Search, analyze, and visualize data faster and in new ways”. 최신 API 자료와 빈티지를 구분하는 보조 근거. |

## Treasury·Federal Reserve

### 기관별 판정

아래의 ‘허용’은 해당 공식 문서의 범위에 한정한다. 서로 다른 기관·사이트의 라이선스를 다른 출처에 이식하지 않는다. 특히 Fed Board의 기본 public domain 안내를 NY Fed에 적용하지 않는다.

| 출처 | 저장 | 변환·파생 | 재배포 | 개인·무료·호출 한도 | AI 범위 | PIT·vintage 판정 |
|---|---|---|---|---|---|---|
| **Treasury FiscalData** | 허용. copy·otherwise use 및 다운로드 지원 [T1,T2] | **adapt 명시 허용** [T1,T2] | **redistribute 명시 허용**, 비상업·상업 모두 [T1,T2] | “free, without restriction”; 계정·token 등록 불필요 [T1]. 숫자형 요청/일일 한도는 확인 문서에 없음. 기본 page size 100은 응답 페이지 기본값이며 사용권·요금 quota가 아님 | ‘otherwise use’라는 넓은 일반 이용 문구가 있으나 AI training·inference·모델 가중치 재배포를 직접 규정한 조항은 **미확인**. 이를 AI 전용 보증으로 표현하지 않음 | `record_date`, 날짜 필터, API v1/v2, meta 구조만으로 당시 공개값을 보장하지 않음. 일반 as-of/vintage 기능은 해당 문서에서 미확인. release calendar는 **예정 시각**, 실제 공개·최초값 증거와 구분 [T1,T2,T3,T4] |
| **Treasury Daily Yields** | 공식 XML/CSV 및 개발자 이용 안내는 확인. **독립적인 재사용 라이선스 원문 미확인** [T5–T8] | 별도 권리 문구 미확인. FiscalData의 adapt 허용을 적용하지 않음 | 별도 권리 문구 미확인 | 공개 문서·feed 설명은 확인했으나 개인 전용/유료 tier·숫자 호출 한도·키 의무를 정한 원문은 미확인. 문서 공개를 무제한 이용권으로 바꾸지 않음 | AI 전용 권리 원문 **미확인** | 입력 수집 시각 약 3:30 PM과 통상 웹 공개 시각 6:00 PM ET가 다름; 지연 가능. 과거 실질금리 backfill 명시. XML의 all/date 조회, 과거 방법 설명 archive는 모든 과거 공개값 vintage의 증거가 아님 [T5,T6,T8] |
| **Federal Reserve Board** | 별도 표시 없으면 public domain이며 copy 허용 [F1] | 기본 public domain 범위의 분석·변환 후보. 문서의 기본 문구는 copy/distribute이고 특정 모델 등에는 별도 제한이 있음 [F1] | 별도 표시 없으면 permission 없이 copy/distribute, Board 출처 표기 요청 [F1] | 기본 저작권 조항에 개인 전용 제한·이용 요금·숫자 호출 quota 없음. DDP는 자동 다운로드 URL을 지원 [F2]; 이는 무제한 서비스 보장이 아님 | AI 전용 조항 **미확인**. 기본 public domain 범위와 non-Board·개별 콘텐츠 예외를 별도 검토해야 함 | DDP bookmark는 최신 자료를 반환하며 날짜 선택은 관측 기간 선택이다. Z.1에는 release-date별 archive index가 있으나 이번 조사에서 본문 vintage·불변성·완전성은 검증하지 않음. FOMC 일부 historical 자료는 공개에 약 5년 지연 [F2–F5] |
| **NY Fed** | **조건부 허용**, “Download, store, and use Content in any format or media” [N1] | **조건부 허용**, “Modify and create derivative works” [N1]. 변경 표기·원본 왜곡 금지·NY Fed에 변경 귀속 금지 | **조건부 허용**, 개인·사업 목적의 copy/distribute [N1]. attribution·저작권/저자/무료 원문 링크 보존·동일 조건 재배포·reference-rate 별도 notice 적용 | 개인·사업 목적 모두. 자동 접근도 허용하지만 사이트 기능을 disable/damage/interfere하면 안 됨 [N1]. API docs public 서버를 확인 [N2]. 숫자 호출 quota·AI 전용 tier는 확인 문서에 없음; permissioned access는 별도 제한 우선 | 일반 사용·저장·파생작업 허용은 확인했지만 **AI training/inference 전용 명시 없음**. third-party·개별 콘텐츠 조건 및 배포 조건을 충족하는 범위에 한정; 무조건 AI 재배포 권리로 표현하지 않음 | API default는 latest implementation이며 복수 production version을 지원하지 않음. `revisionIndicator`는 수정 표식이지 원래 값·모든 vintage 반환 보장이 아님. reference rates는 당일 오전 최초 공개와 오후 수정, 분기 뒤 summary statistics의 변경 가능성이 다름 [N1–N3] |

### 재배포 및 third-party 예외

#### Treasury FiscalData와 Daily Yields

- FiscalData [T1]의 “The data is offered free, without restriction” 및 “copy, adapt, redistribute”는 **FiscalData 데이터**에 대한 강한 공식 근거다. About Us [T2]도 “The data on this site”로 범위를 표현한다. Treasury의 모든 사이트·외부 자료·사진·로고·제3자 문서까지 허용했다고 확장하지 않는다.
- Fiscal Service Open Data Policy [T4]의 범위에는 Fiscal Service가 생성·유지하는 데이터와 고객이 생성하여 유지 목적으로 제출한 데이터가 포함되지만, **shared service를 통해 Fiscal Service가 유지하는 고객 생성 데이터는 제외**한다. 이는 기관의 공개 정책 범위이지 모든 제3자 데이터에 대한 일반 재배포 라이선스가 아니다.
- Treasury Site Policies [T8]는 외부 웹사이트가 동일한 법·규정·정책 아래 있지 않을 수 있으며 외부 사이트의 정책 적용을 안내한다. Treasury Privacy Policy [T9]도 외부 사이트 내용·운영에 대한 책임을 부인한다. **Daily Yields 자체의 구체적인 copyright·third-party 재사용 조항은 이들 원문에서 확인되지 않았다.** NY Fed가 입력 quote를 제공한다는 사실만으로 NY Fed 사이트 콘텐츠 약관이나 FiscalData 라이선스를 자동 적용하지 않는다.

#### Federal Reserve Board

공식 Disclaimer의 **Copyright/trademark** [F1]:

> “Unless otherwise indicated, information on Board's website is in the public domain and may be copied and distributed without permission.”

> “Please cite to the Board as the source of the information.”

> “permission to copy and distribute ... must be obtained from the non-Board source.”

따라서 non-Board 사진·그래픽·copyright/trademark 표시 자료는 원권리자의 permission이 필요하다. **Disclaimer regarding Non-Board Information** 역시 외부 웹사이트 자료의 허가는 원출처에서 받아야 하며 Board에서 받을 수 없다고 명시한다. Board seals/logos는 별도 서면 허가 대상이다. 기본 public domain 안내는 외부 콘텐츠·상표 예외를 없애지 않는다.

동일 문서의 FRB U.S. Model/EDO 별도 조항에는 **수정한 모델을 공식 정부 자료로 제시하면 안 된다**는 제한이 있다. 개별 상품의 제한을 일반 통계 데이터 전체의 제한으로 확대하지 않되, 별도 제한이 있으면 우선한다.

#### NY Fed

공식 **Terms of Use** [N1], Last Updated **6/9/2023**, **Permissible Use**:

> “The New York Fed grants you a non-exclusive license, subject to the Terms, to use, copy, and distribute Content for your personal or business purposes.”

> “Download, store, and use Content in any format or media”

> “Modify and create derivative works from the Content.”

**Conditions**:

> “If you distribute the Content, you must make the Content available with the same permissions, conditions, and restrictions set forth in these Terms.”

> “You may not impose more restrictive terms or conditions on the Content.”

복제·배포 시 포함된 copyright/source identifiers/개별 저자를 보존한다. 특정 attribution이 없으면 다음 형태를 적용한다:

> “© [year] Federal Reserve Bank of New York. Content from the New York Fed subject to the Terms of Use at newyorkfed.org.”

변경한 콘텐츠는 명확히 표시해야 하고 변경·파생작업을 NY Fed에 귀속할 수 없다. 내용의 왜곡·오해를 유발하는 수정/발췌 및 title/headline 수정 금지가 있다. NY Fed의 endorsement를 암시할 수 없다.

**Use Restrictions → Reference Rates**의 데이터·관련 정보 표시 필수 notice:

> “The [NAME OF DATA or CONTENT] is subject to the Terms of Use posted at newyorkfed.org. The New York Fed is not responsible for publication of the [DATA NAME] by [NAME OF PUBLISHER], does not [sanction] or [endorse] any particular republication, and has no liability for your use.”

reference-rate 명칭·약어를 상품/서비스 명칭·설명에 사용하면 별도 non-affiliation/endorsement disclaimer도 필요하다. Terms의 **Indemnification**에는 이용·복제·배포·상업 활동 등으로 발생하는 제3자 청구에 관한 indemnify/hold harmless 조건이 있다.

확인된 예외:

- **Third Party Content:** “If you want to make any other use of third-party content, you must obtain permission directly from the owner of that content.” 사이트에 게시된 제3자 자료는 볼 수 있도록만 허용되는 경우가 있다. 외부 링크 대상의 서비스/자료에는 외부 제공자의 약관이 적용된다.
- **SOFR/BGCR:** NY Fed가 **DTCC Solutions LLC의 라이선스로 제공된 데이터**를 이용해 계산한다고 명시한다. 공개된 NY Fed reference-rate 결과와 기초 DTCC 거래 데이터의 이용권을 동일시하지 않는다. DTCC 및 관련 제3자의 책임 제한이 함께 명시돼 있다.
- **Household Debt and Credit:** New York Fed Consumer Credit Panel/Equifax에 기반하며, 해당 데이터 attribution은 “New York Fed Consumer Credit Panel / Equifax.”
- **Staff Reports/Working Papers:** 개인 및 내부 업무 이용은 허용되지만 “You may not distribute Staff Reports or Working Papers for a business or commercial purpose.” 일반 데이터 라이선스와 구분한다.
- **Liberty Street Economics blog:** 정기/연속 배포 또는 공개 archive 저장에는 별도 서면 license agreement가 필요하다. 개별 이용과 공개 지속 archive를 구분한다.
- **SCE:** 데이터 공개/발표 시 전용 attribution/disclaimer가 있다. 연구 데이터 계열을 일반 attribution만으로 재배포 가능하다고 처리하지 않는다.
- **Permissioned Access Websites:** 별도 콘텐츠 제한이 Terms의 라이선스보다 우선한다. 공개 Markets API와 비공개/허가 기반 접근을 구분한다.

### 공개 시각, archive와 PIT 한계

1. **FiscalData:** [T3]의 release calendar는 “estimated dates and times for upcoming data releases.” 예정표는 실제 최초 공개 시각의 로그가 아니다. [T1]의 `record_date` 필터는 관측 날짜 필터이며, API v1/v2는 인터페이스 버전이다. [T2]는 역사 범위가 원래 기록 시작·새 시스템 도입 등에 따라 달라지고 역사 데이터를 계속 늘릴 수 있다고 설명한다. 현재 endpoint가 과거 날짜를 반환하더라도 그 값이 그 날짜에 공개됐음을 입증하지 않는다.
2. **Daily Yields:** [T6]는 입력 quote가 약 **3:30 PM** 거래일 시각에 수집되고, 수익률은 보통 **6:00 PM Eastern Time**까지 공개되나 지연될 수 있다고 구분한다. “by 6:00 PM Eastern Time ... but may be delayed”는 실제 일별 완료 시각의 보증이 아니다. [T5]의 실질 par yield는 **2004-01-02**에 발행을 시작하면서 **1년 역사값을 함께 공개**했다고 명시한다. 실질 장기평균도 2004년 시작하면서 **2000년까지의 역사값**을 제공했다. 이 관측기간은 당시 실시간 공개기간이 아니다.
3. **Daily Yields archive:** [T6]은 이전 산출방법 설명의 archive를 링크한다. 이는 **문서 archive**로서 방법 변경 이력을 보여주지만 시각별 데이터 vintage archive는 아니다. [T7]의 all-period XML pagination, URL/스키마 변경·구 feed 중단 역시 현행 과거값 조회 설명이다. 어떤 과거 URL이나 `all` 파라미터가 있다는 사실로 모든 최초값·수정값·공개 시각을 보장하지 않는다.
4. **Board DDP:** [F2]는 bookmark로 “retrieve the most recent data as it becomes available”가 가능하다고 설명한다. 날짜 범위 선택은 관측기간을 정할 뿐 과거 정보집합으로 되돌리는 as-of 기능이라고 설명하지 않는다. 자동 다운로드·SDMX 지원이 PIT 지원의 증거는 아니다.
5. **Board archive:** Z.1 Release Dates [F4]에는 “This site has Z.1 releases for the following date(s):”라는 release별 archive index 및 HTML/PDF/CSV 링크가 있다. 이것은 공개본별 비교를 위한 **archive 후보**라는 근거다. 해당 자료의 실제 값·파일 불변성·intraday release time·모든 수정본 보존은 이번 문서 조사에서 미확인이다. H.15 about [F3]는 영업일 발행을 설명하지만 해당 자료 전용 모든 vintage archive는 확인하지 못했다.
6. **FOMC archive:** [F5]는 transcripts·Bluebooks·Greenbooks·개별 projections compilation·agendas를 **약 5년 lag**로 공개한다고 명시한다. 현재 archive에서 회의일 기준 과거 문서를 읽을 수 있어도 당시 대중 정보집합에 포함됐다는 뜻이 아니다. Minutes는 2004년 12월 이후 정책 결정일부터 **3주 뒤** 공개, 그 이전에는 대체로 **다음 회의 3일 뒤**였다고 설명한다. 문서 종류·기간별 공개 규칙을 구분해야 한다.
7. **NY Fed reference rates:** [N3]는 EFFR/OBFR 약 **9:00 AM ET**, SOFR 등 약 **8:00 AM ET** 공개를 설명한다. 당일 오류·거래정보 변경 등에 따라 약 **2:30 PM ET** 수정될 수 있고 rate 변경이 1bp를 초과하는 기준을 설명한다. 당일 수정 footnote 및 API `revisionIndicator`만으로 수정 전 원래 값을 재구성할 수 있다고 주장하지 않는다.
8. **NY Fed 지연 갱신·backfill:** [N3]는 Treasury repo summary statistics를 분기 종료 후 lag를 두고 업데이트하며, 최초 발표 이후 확인된 오류·늦게 들어온 데이터·당일 기준 미충족 변경 때문에 최초값과 달라질 수 있다고 명시한다. 같은 페이지의 “Daily indicative TGCR, BGCR, and SOFR ... (Aug. 2014 - Mar. 2018)” 및 “Daily indicative SOFR averages and index (Apr. 2018 - Feb. 2020)”라는 링크명은 **indicative historical 자료**의 존재를 보여줄 뿐 해당 과거일에 현재 형태로 공식 공개됐다는 증거가 아니다. 파일은 읽지 않았다.
9. **NY Fed API version:** [N2]의 “do not support multiple production versions”와 “default endpoints are backed by the latest official service implementation”는 서비스 구현 버전 설명이다. 날짜/`asof` 이름의 endpoint나 수정 표식만으로 데이터 vintage semantics가 입증되지는 않는다. 각 endpoint의 날짜가 보고 대상일·보유 기준일·조회 당시 공개일 중 무엇인지 원문 data dictionary와 별도 공개 근거로 확인해야 한다. beta 데이터는 testing-only이며 정기 유지되지 않는다고 명시돼 있으므로 PIT 근거로 쓰지 않는다.

### 공식 원문 및 짧은 인용

모든 확인일은 **2026-10-10**. HTTP 200만으로 권리 내용을 확인한 것으로 표시하지 않고 실제 문구가 있는 경우와 원문 미확인을 구분했다.

| ID | 공식 URL·문서 | 접근 및 원문 근거 |
|---|---|---|
| T1 | [FiscalData API Documentation](https://fiscaldata.treasury.gov/api-documentation/) | 200. **License and Authorization:** “free, without restriction”; “copy, adapt, redistribute”; “non-commercial or commercial purposes”. **How to Access:** “does not require a user account or registration for a token.” |
| T2 | [FiscalData About Us](https://fiscaldata.treasury.gov/about-us/) | 200. **Licensing:** “The data on this site is available to copy, adapt, redistribute”. 역사 범위: “continue working to provide as much historical data as possible.” |
| T3 | [FiscalData Release Calendar](https://fiscaldata.treasury.gov/release-calendar/) | 200. “shows estimated dates and times for upcoming data releases.” |
| T4 | [FS Policy 901-1, Open Data Policy (PDF)](https://fiscaldata.treasury.gov/data/about-us/901-1%20Open%20Data%20Policy.pdf) | 200, PDF 텍스트만 읽음. July 2021, Next Review July 2025로 표기되어 있으며 이후 검토본 존재를 추정하지 않음. “enabling easy storage and analysis”; “does not include data ... maintained ... through a shared service.” |
| T5 | [Treasury Interest Rate Statistics](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics) | 200. “Treasury began publishing this series on January 2, 2004. At that time Treasury released 1 year of historical data.” 실질 장기평균: “Treasury provides historical data back to 2000.” |
| T6 | [Treasury Yield Curve Methodology](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology) | 200. Revised 2025-02-18. “by 6:00 PM Eastern Time each trading day, but may be delayed”; “description of the previous methodology has been archived.” 문서 archive 링크도 확인: [이전 설명](https://home.treasury.gov/quasi-cubic-hermite-spline-treasury-yield-curve-methodology). |
| T7 | [Developer Notice - XML changes](https://home.treasury.gov/developer-notice-xml-changes) | 200. “feed still exists for developers to access via API”; “data feed changed to include pagination”. 실제 feed 호출하지 않음. |
| T8 | [Treasury Site Policies and Notices](https://home.treasury.gov/subfooter/site-policies-and-notices) | 200. “Non-federal websites do not necessarily operate under the same laws, regulations, and policies as federal websites.” Daily Yields 자체 재사용 license는 **원문 미확인**. |
| T9 | [Treasury Privacy Policy](https://home.treasury.gov/subfooter/privacy-policy) | 200. **Legal Disclaimers:** “assumes no responsibility for the content or operation of external (outside Treasury) web sites.” copyright 허용 근거로 쓰지 않음. |
| F1 | [Federal Reserve Board Disclaimer](https://www.federalreserve.gov/disclaimer.htm) | 200. Last Update 2024-08-02. **Copyright/trademark:** “in the public domain”; “may be copied and distributed without permission”; non-Board permission 예외 명시. |
| F2 | [Board DDP Help](https://www.federalreserve.gov/datadownload/help/default.htm) | 200. **Automated Systems:** “URL that can be used by computer programs”; **Bookmark:** “retrieve the most recent data as it becomes available.” |
| F3 | [H.15 About](https://www.federalreserve.gov/releases/h15/about.htm) | 200. “It is published every business day except holidays.” |
| F4 | [Z.1 Release Dates](https://www.federalreserve.gov/releases/z1/release-dates.htm) | 200, index 메타데이터만 확인. “This site has Z.1 releases for the following date(s)”; release별 HTML/PDF/CSV 링크 존재. archive 데이터 본문 미열람. |
| F5 | [FOMC Historical Materials 안내](https://www.federalreserve.gov/monetarypolicy/fomc_historical.htm) | 200. “made available ... with about a five-year lag”; minutes “three weeks after the date of the policy decision.” |
| N1 | [NY Fed Terms of Use](https://www.newyorkfed.org/privacy/termsofuse) | 200. Last Updated 6/9/2023. **Permissible Use / Conditions / Use Restrictions / Third Party Content / Indemnification**의 실제 원문 확인. |
| N2 | [NY Fed Markets API UI](https://markets.newyorkfed.org/static/docs/markets-api.html), [공식 OpenAPI 정의](https://markets.newyorkfed.org/static/docs/markets-api.yml) | 두 URL 200. UI에서 공식 yml 연결 확인 후 정의 문서만 읽음. Last Updated June 12, 2026. “all data accessible ... subject to the Terms of Use”; “do not support multiple production versions”; `revisionIndicator` schema 확인. Try it out·관측치 API 실행하지 않음. |
| N3 | [NY Fed Additional Information about Reference Rates](https://www.newyorkfed.org/markets/reference-rates/additional-information-about-reference-rates) | 200. Last Updated 10/5/2026. “revised at approximately 2:30 p.m. ET”; lagged quarterly statistics “may potentially differ from the originally published data.” historical indicative 데이터 링크명만 확인. |

### 접근 실패·미확인 기록

- `https://home.treasury.gov/footer/privacy-policy`: **HTTP 404**, 해당 URL 원문 미확인. 공식 페이지 링크로 찾은 **T9**에서는 접근 성공했지만 독립적인 Daily Yields license는 확인되지 않았다.
- `https://www.newyorkfed.org/terms`: 요청은 200이었으나 `/errors/404`로 redirect되어 **Page Not Found**. 해당 URL 약관 원문 미확인. 공식 footer의 **N1**으로 이동하여 실제 약관 확인 완료.
- `https://www.federalreserve.gov/datadownload/help/faq.htm`, `https://www.federalreserve.gov/releases/calendar.htm`, `https://www.federalreserve.gov/releases/h15/release-dates.htm`: **HTTP 404**, 해당 문서/전용 archive 원문 미확인. 존재하지 않는 추정 URL을 증거로 사용하지 않음.
- Board의 공식 `https://www.federalreserve.gov/data/releaseschedule.htm`은 200이었지만 이번 비브라우저 문서 열람에서 일반적인 release 시각 설명을 얻지 못했다. 여기에서 정확한 H.15 공개 시각을 추정하지 않았다.
- 위 미확인은 권리 금지·무료 사용 불가를 의미하지 않는다. 해당 주장을 뒷받침하는 공식 문구를 이번 제한된 조사에서 얻지 못했다는 상태다. API에서 과거 관측일을 조회할 수 있다는 기술 사실을 PIT 승인 근거로 대체하지 않는다.

## 후보 연결 및 검증 경계

| 기존 축 | 원기관 자료군 후보 | 이번 조사에서 확정하지 않은 것 |
| --- | --- | --- |
| Growth | BEA GDP·NIPA 소득/지출·산업별 GDP, BLS 고용/노동시간 보조 | 선택 series·계절조정·명목/실질·성장률 계산·가중치·8×6 출력 |
| Inflation | BLS CPI·BEA PCE price index | headline/core 선택·unit/frequency·revision별 PIT |
| Liquidity | Fed Board 대차대조표·NY Fed repo/reverse-repo/SOMA/liquidity swaps·FiscalData 재무부 현금 보고 자료군 후보 | 정의·항목 결합·순유동성 등 새 계산법 |
| Monetary Policy | Fed Board/NY Fed 정책/운영 금리, Treasury yields 보조 후보 | 정책 목표·effective rate·시장 수익률의 동일성 및 대체관계 |
| Credit | Fed Board 신용/대출 계열·NY Fed 자료군 후보 | 기업 credit spread와 정부/은행 계열의 동등성; 민간 자료 권리 |
| Labor | BLS CES·CPS·JOLTS; BEA 고용/임금 보조 | exact series·빈티지·공표시각·선택 우선순위 |
| Fiscal | BEA NIPA 정부 수입/지출; Treasury FiscalData 후보 | 회계기준·시점·기관별 범위·모델 계약 |
| FX | Fed Board H.10·FiscalData Treasury Reporting Rates of Exchange 후보; BEA 국제계정은 배경자료 후보 | 환율 방향·통화쌍·fixing·단위·현재 KRW/JPY 가격 경로와의 연결; FiscalData reporting rate는 거래용 실시간 spot과 구분 |

원기관 직접 경로는 FRED를 통해 내려받는 경로와 이용약관이 다르다. 직접 출처에서 허용된 자료라는 이유로 FRED API의 별도 접근·저장/AI 조건을 우회하거나 FRED 경로까지 허가됐다고 판정하지 않는다. 현재 API의 과거 관측기간, release archive, 실제 vintages, intraday availability는 구분하며, 최신 값을 당시 값으로 대신 넣지 않는다. 8축 producer/adapter 정합·series 동일성·PIT·게시 gate는 미검증 상태다.
