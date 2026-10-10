# Macro 나머지 4축 — 원기관 출처·발표 주기·빈티지 조사

확인: **2026-10-10 UTC**, canonical `83a2d0e3e5bf7ecf539a74a67f1a32c08480d0bb` (#110 병합 후). GSQ-011의 무료 원기관 직접 경로를 적용한다. **Liquidity / Credit / Fiscal / FX의 출처 조사만** 수행하며 공급자·series 채택이나 구현·수집·새 지표·가중치·상태 규칙을 추가하지 않는다. FRED/ALFRED의 사이트·API·CSV·fallback을 호출하지 않았다.

1차 Growth·Inflation·Monetary Policy·Labor의 구현은 #104다. 나머지 4축은 기존 `DEFERRED_GSQ011`을 유지한다. 자료가 존재해도 Level·Direction·Momentum·Surprise·Stress·Confidence가 산출됐다는 뜻이 아니다. [1차 명세](PHASE1_FOUR_AXES_IMPLEMENTATION_SPEC.md), [기존 8축 조사](RESEARCH.md), [기관별 권리 근거](PRIMARY_AGENCY_EVIDENCE.md)를 함께 참조한다.

## 1. 축별 후보와 발표 주기

미국 공공 자료의 후보군이다. 글로벌·한국·일본 전체 coverage나 기존 5개 PROVISIONAL 입력과의 동등성을 뜻하지 않는다. 아래 시각은 **미 동부 시간 ET**이며 고정 UTC로 바꾸지 않는다. 정기 일정은 실제 일별 공개·이용 가능 시각의 증거가 아니다.

| 축 | 원기관 직접 출처와 자료군 | 관측 빈도와 공식 발표 주기 | 용도·선택 경계 |
| --- | --- | --- | --- |
| Liquidity | Federal Reserve Board **H.4.1**, Factors Affecting Reserve Balances / 각 Reserve Bank·통합 대차대조표. [L1], [L2] | 주간. 보통 **목요일 16:30 ET**, 해당일이 연방 공휴일이면 다음 영업일로 옮길 수 있다. [L2] | 중앙은행 자산·부채·준비금 요인 각각의 원자료 후보다. 날짜별 잔액과 주간 평균은 구별해야 한다. 항목을 더하거나 빼서 ‘순유동성’ 산식을 새로 만들지 않는다. |
| Liquidity 보조 | Treasury FiscalData **Daily Treasury Statement(DTS), Operating Cash Balance**, `account_type`, `close_today_bal` 등. [T1] | 자료군은 **일간**. `New Data Expected`·[release calendar][T5]는 예정값이며 고정 실제 공표 시각은 이번 조사에서 확정하지 않았다. | Treasury 현금 잔액은 Fed 잔액과 다른 원재료다. TGA/다른 계정·당일 마감/기초 잔액·단위를 구별하고 자동 합성·대체하지 않는다. |
| Credit | Federal Reserve Board **H.8**, Assets and Liabilities of Commercial Banks: bank credit / loans and leases 등 공개 집계. [C1], [C2] | 주간. 보통 **금요일 16:15 ET**, 금요일이 연방 공휴일이면 **목요일 16:15 ET**. 주간 수준은 수요일 업무 마감 집계이며 월간 평균·증감률과 별도다. | 은행 대출량·자산/부채의 후보다. all commercial banks와 은행 하위 집단, SA/NSA를 구별한다. 개별 FR 2644 응답 microdata는 비공개다. 은행 대출을 기업 HY spread와 같은 입력으로 취급하지 않는다. |
| Credit 보조 | Federal Reserve Board **SLOOS**, 은행 대출 기준·조건과 기업/가계 수요의 공개 집계 조사. [C3], [C4] | 일반적으로 **분기별**. 표준 조사는 보통 FOMC 회의 후 첫 월요일 공개. 필요하면 특별 조사를 추가하며 연 최대 6회 설명이 있다. 정시 시각은 미확정이다. | 질문·대출군·net percentage 응답과 조사/공표 시점을 구별한다. H.8의 대출 금액, ICE HY spread 또는 연속 시장가격의 대체물이 아니다. |
| Fiscal | Treasury FiscalData **Monthly Treasury Statement(MTS)**: Summary of Receipts, Outlays, and the Deficit/Surplus of the U.S. Government 및 연결 표. [T2] | **월간**. 공식 달력은 추정 공표 날짜/시각을 제공한다. 이번 확인에서 고정 일자·정시를 계약으로 확정하지 않았다. [T5] | receipts/outlays/수지·재정연도와 달력월·회계기준을 구별한다. MTS 총계/소계·계층 행을 중복 합산하지 않는다. fiscal state나 GDP 대비 비율을 새로 만들지 않는다. |
| Fiscal 보조 | Treasury FiscalData **Debt to the Penny**: total outstanding public debt / debt held by the public / intragovernmental holdings. [T3] | **일간** 보고. 실제 최초 공개 시각·개별 수정본 API는 미확인이다. | 부채 잔액은 월간 재정 흐름과 별도다. FFB 포함 범위·다른 Treasury 표와의 차이를 확인해야 한다. 최신 부채를 과거 fiscal vintage로 대신 넣지 않는다. |
| FX | Federal Reserve Board **H.10**, 양자 환율·명목 달러지수. [X1], [X2], [X3] | 관측은 일간, **전주 영업일 값이 월요일 16:15 ET** 공개된다. 월요일이 연방 공휴일이면 다음 영업일. 양자 환율은 뉴욕 정오 buying rate 설명을 따른다. 명목 지수는 일/월, 실질 달러지수는 월간으로 구별한다. | 통화쌍·환율 방향/단위·지수 종류·기준시점 확인이 필요하다. fixing/통계 환율을 실시간 spot이나 사용자 종목의 현재 환산 가격으로 간주하지 않는다. [X1] |

**검토 우선 후보:** Liquidity=H.4.1, Credit=H.8와 SLOOS의 별도 원자료, Fiscal=MTS, FX=H.10. Treasury DTS·Debt to the Penny는 보조 후보로 남긴다. 이것은 출처 검토 순서이며 지표 선택·축 합성·8×6 계산 승인이나 자동 source 교체가 아니다. ICE 등 제3자 가격·spread 입력이 없으면 그 의미의 Credit 값은 미제공으로 유지한다.

## 2. 빈티지와 PIT 가능 여부

`과거 관측행 조회`, `release별 발표본`, `당시 가용 시각`, `수정 전/후 모든 버전`은 별개다. 기관의 일반 데이터 다운로드·CSV/XML 지원을 ALFRED형 as-of vintage 기능으로 해석하지 않는다.

| 자료군 | 확인한 공식 발표본·과거 자료 경로 | 빈티지 후보 판정과 제한 |
| --- | --- | --- |
| H.4.1 | 공식 About에서 **Release Dates**로 연결한 `/releases/h41/default.htm`이 존재하며 ‘This site has H.4.1 releases for the following date(s)’를 표시한다. [L1], [L2] | **발표별 archive 후보**. 비브라우저 본문에는 개별 날짜 목록이 펼쳐지지 않아 실제 발표 파일·범위·수정본 불변성·모든 vintage coverage는 확인하지 않았다. 정기 목요일 시각만으로 특정 파일의 최초 공개를 증명하지 않는다. |
| H.8 | 공식 About → **Release Dates** `/releases/h8/default.htm`, Notes on Data. [C1], [C2], [C5] | **발표별 archive 후보**. 개별 날짜/파일과 최초값·정정값 전체 보존은 미확인이다. About은 계절요인의 연간 갱신, Notes는 정의/회계 변화·수정의 존재를 설명한다. 최신 시리즈를 당시 값으로 재사용하지 않는다. |
| SLOOS | 공식 `/data/sloos.htm`에 조사 회차별 공개 보고 링크, DDP/XML 안내가 있다. [C3] | **회차별 발표본 후보**. 조사월·응답 대상 기간·실제 공표 날짜를 분리하고 질문 변경·특별 조사·정정/원본 보존을 확인해야 한다. index 링크 존재만 확인했으며 보고 본문·데이터 zip은 내려받지 않았다. |
| DTS / MTS | 공식 데이터셋의 **Reports and Files**. DTS의 FY1998 이전 보고는 재정연도별, MTS의 1998년 이전 보고는 연도별로 묶였다는 안내. [T1], [T2] | **당시 보고 archive 후보**. 실제 보고 파일과 원본 불변성·정정본·정확한 발표 시각은 미확인. 현재 JSON/CSV의 과거 행은 vintage API가 아니다. MTS는 과거 추정 세수의 이후 조정을 설명하고 DTS는 계정명·표 구조 변경을 고지한다. |
| Debt to the Penny | 공식 현재 시계열·역사 범위/단위/예외 설명. [T3] | **현재 과거값 경로만 확인**, 수정 전 vintage archive는 미확인. 장기간의 빈도 차이와 일부 과거 미제공 열에 실제 0 대신 `$0.00`을 사용한 예외를 결측 규칙에 반영해야 하며 자동 정상값 판정은 금지한다. |
| H.10 | About이 공식 Release Dates archive와 Country Data를 구분한다. **‘past releases are not revised and may not reflect subsequent revisions’** 명시. [X1], [X2], [X3] | **당시 발표본을 보존하는 archive의 공식 근거 있음**. 현재 Country Data는 이후 수정값이 포함될 수 있다. **2006-05-22~2009-01 주간 H.10 발행 중단**이 공식 index에 명시되어 그 구간을 완전한 당시 발표본으로 가정하지 않는다. [X2] 실제 파일 값·범위·장중 공표 증거는 확인하지 않았다. |

Treasury DTS/MTS의 현재 data dictionary는 `record_date`를 **‘The date that data was published’**로 설명한다. [T1], [T2] 필드 이름만 보고 이를 관측일이라고 일괄 단정하지 않으며, 이 일 단위 설명도 최초 공개 **시각**·timezone·수정 전 값·기존 표의 기준월을 입증하지 않는다. dataset별 실제 날짜 의미를 원 보고 및 수정 기록과 대조하기 전 PIT 통과값으로 사용하지 않는다. `Last Updated`·`New Data Expected`·calendar의 estimated 날짜도 실제 최초 가용 시각을 대신하지 않는다.

향후 구현에서 원기관·상품·정확한 series/table·단위·SA/NSA·관측/측정 기간·원 발표 시각/시간대·수정 관계·실제 취득 시각을 구분해야 한다. 확인한 발표본만 `available_at <= decision_time` 근거 후보로 삼고, 근거 없는 역사에는 PIT 미확인을 유지한다. 향후 직접 취득 기록은 취득 이후 알고 있던 값만 입증하며 수집 전 역사를 소급 복원하지 않는다. 이번 조사에서는 해당 계약·테스트·수집기를 구현하지 않았다.

## 3. 무료 원기관 원칙과 접근·권리 경계

- **Board 직접 작성 공개 통계:** [공식 disclaimer][R1]는 별도 고지가 없는 Board 정보가 public domain이며 복제·배포 허가가 불필요하고 출처 인용을 요청한다고 명시한다. 제3자 사진/자료·로고·외부 링크·별도 상품 조건은 예외다. H.8/SLOOS의 공개 집계와 비공개 은행 microdata는 구별한다. [기관별 권리 근거](PRIMARY_AGENCY_EVIDENCE.md)의 범위를 유지한다.
- **FiscalData:** [API documentation][T4]와 [About Us][T6]는 free, copy/adapt/redistribute 및 non-commercial/commercial 이용을 설명한다. 무료 자료 재사용권을 코드·새 산식·공개 산출물 또는 가격 보존 승인으로 확대하지 않는다. 이 문서에 기록한 경로는 로그인·키 없이 읽을 수 있는 공식 설명 페이지다.
- **직접 경로의 변화:** 현재 H.4.1/H.8/H.10 Release Dates 페이지에는 **11월 9일 주간 DDP ‘Build Your Package’ 제거 및 장차 DDP 종료 준비·FRED 안내**가 표시된다. [L2], [C2], [X2] 종료 날짜·직접 XML/개별 발표본의 지속 제공은 별도 확인 대상이다. FRED 링크를 따라가거나 fallback으로 채택하지 않았다. 직접 경로가 중단되면 미제공으로 남기고 새 원기관 제공 경로를 확인한다.
- **본인 전용 경계:** 매크로 정부 통계의 보관 가능성은 개인 가격/가격 기반 파생값의 지속 저장·공개 허용이 아니다. FX fixing·환율 등 가격 성격 입력은 기존 RAM·공개 금지 경계를 먼저 적용하고 보존이 필요하면 별도 사용자 결정이 필요하다. 실제 환율·개인 가격·시트·membership·순위는 저장소에 기록하지 않는다.
- **유지:** FRED/ALFRED 차단, Holdout UNCONFIRMED·v2 근거 제외·기간 선택/사용 금지, 기존 Macro 버전·Frozen/TARGET·상태 규칙·가중치를 유지한다. 이번 결과는 어떤 축도 READY로 승격하지 않는다.

## 4. 공식 근거 확인

아래는 **2026-10-10 HTTP 200과 해당 설명 문구를 확인한 URL**이다. 기관 안내·release index·data dictionary/metadata만 읽었으며 관측치 API·개별 발표 데이터/PDF·CSV/XML/zip·계정/키 호출은 하지 않았다. HTTP 200만으로 archive 불변성·series 전체 coverage를 인증하지 않는다.

| ID | 확인한 내용 |
| --- | --- |
| L1 | H.4.1 About: 자료군 정의, 통상 목요일 16:30. |
| L2 | H.4.1 Release Dates: 공휴일 시 다음 영업일 가능, 발표본 index 안내, DDP 전환 공지. |
| C1 | H.8 About: 금요일 16:15/공휴일 목요일, 수요일 잔액·월간 평균, SA 갱신, 개별 응답 비공개. |
| C2 | H.8 Release Dates: 공식 주간 공개 규칙·DDP 공지. |
| C3 | SLOOS Release Dates: 통상 분기별·특별 조사, 회차별 보고 링크. |
| C4 | SLOOS About: FR2018, 표준 조사 FOMC 후 첫 월요일, 필요 시 연 최대 6회. |
| C5 | H.8 Notes on Data: 정의·분류·과거 수정 설명. |
| T1 | DTS dataset: daily·Operating Cash Balance dictionary·보고 묶음·구조/계정명 변경. |
| T2 | MTS dataset: monthly·Summary table dictionary·백만 USD·보고 묶음·과거 세수 추정의 이후 조정. |
| T3 | Debt to the Penny dataset: daily·부채 구성·역사 빈도와 과거 미제공의 0 표시 예외. |
| T4 | FiscalData API documentation: 무료·복제/변환/재배포·API 버전과 데이터 빈티지 구분. |
| T5 | Release Calendar: **‘estimated dates and times’**. |
| T6 | FiscalData About Us: 비상업/상업 재사용 근거. |
| X1 | H.10 About: 뉴욕 정오 관측·일/월 지수 구분, 발표본 비수정과 current history 차이. |
| X2 | H.10 Release Dates: 월요일 16:15/공휴일 다음 영업일, 2006~2009 발행 중단, DDP 공지. |
| X3 | H.10 Country Data: 월요일 갱신 current history와 과거 수정의 예외. |
| R1 | Board disclaimer: public domain·출처 요청·제3자/로고 예외. |

잘못 추정한 `/releases/{h41,h8,h10}/release-dates.htm`와 `/data/sloos/sloos-data.htm`은 원문 미확인으로 제외하고 **공식 About의 실제 링크**를 사용했다. 이전 `fiscal.treasury.gov/reports-statements/{mts,dts}/`는 일반 reports index로 redirect되어 전용 불변 archive의 증거로 쓰지 않았다. static dataset 화면에 세부 report 목록이 충분히 펼쳐지지 않아 모든 역사 파일 제공을 주장하지 않는다.

후속 구현 전 결정/확인 대상은 **축별 정확한 입력 채택**, 정의·통화·단위·SA/NSA·PIT 증거, 변경될 직접 제공 경로와 권리 범위다. 현재 출처 조사 문서의 병합에는 추가 채택 결정이 필요하지 않다. 새 Direction/Momentum/Surprise/Stress/Confidence·Credit 대체·순유동성·FX 환산 규칙은 별도 범위다.

[L1]: https://www.federalreserve.gov/releases/h41/about.htm
[L2]: https://www.federalreserve.gov/releases/h41/default.htm
[C1]: https://www.federalreserve.gov/releases/h8/about.htm
[C2]: https://www.federalreserve.gov/releases/h8/default.htm
[C3]: https://www.federalreserve.gov/data/sloos.htm
[C4]: https://www.federalreserve.gov/data/sloos/about.htm
[C5]: https://www.federalreserve.gov/releases/h8/h8notes.htm
[T1]: https://fiscaldata.treasury.gov/datasets/daily-treasury-statement/
[T2]: https://fiscaldata.treasury.gov/datasets/monthly-treasury-statement/
[T3]: https://fiscaldata.treasury.gov/datasets/debt-to-the-penny/
[T4]: https://fiscaldata.treasury.gov/api-documentation/
[T5]: https://fiscaldata.treasury.gov/release-calendar/
[T6]: https://fiscaldata.treasury.gov/about-us/
[X1]: https://www.federalreserve.gov/releases/h10/about.htm
[X2]: https://www.federalreserve.gov/releases/h10/default.htm
[X3]: https://www.federalreserve.gov/releases/h10/hist/default.htm
[R1]: https://www.federalreserve.gov/disclaimer.htm
