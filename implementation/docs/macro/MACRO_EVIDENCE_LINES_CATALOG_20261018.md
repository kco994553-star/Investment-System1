# 매크로 근거 세로선 후보 목록 (2026-10-18)

상태: **조사 문서만.** 코드·가드·워크플로·결정 기록은 바꾸지 않았다.
기준 커밋: canonical `8bbc172b` (`claude/investment-system-top500-validation-alrugm`, #310 병합).
근거 지시: [PRODUCT_IA_DIRECTIVE_20261018](../PRODUCT_IA_DIRECTIVE_20261018.md) 3.1~3.3. 사용자 예: "운송업 매출이 올랐다는 지표가 초반 강세시장 근거가 된다".
같이 읽은 문서: [PRODUCT_IA_ONTOLOGY_CHECK_20261018](../PRODUCT_IA_ONTOLOGY_CHECK_20261018.md)(이하 **OC**) 1-3절·IA-3·IA-4·IA-5·IA-16, [IMPACT_PATH_AND_CYCLE_DESIGN_20261018](../news_relations/IMPACT_PATH_AND_CYCLE_DESIGN_20261018.md)(이하 **IMP**) (b)절, [FRED_ALFRED_EVIDENCE](../macro_data_rights/FRED_ALFRED_EVIDENCE.md), [PRIMARY_AGENCY_EVIDENCE](../macro_data_rights/PRIMARY_AGENCY_EVIDENCE.md), [BACKTEST_DATA_AUDIT](../backtest/BACKTEST_DATA_AUDIT.md) §0·D8.

> 이 문서를 병합해도 아래 MEV-1~MEV-10 권장안의 승인이 아니다. 지표 채택·임계값·확률은 정하지 않았다.
> 시안의 세 예(운송업 매출 ↑, 장단기 금리차 정상화, 신규 실업수당 ↓)는 아래 E03·E01, E10, E14로 이어진다.

## 읽는 법

- 지표 번호는 `E01`~`E54`다. 결정 후보 번호는 `MEV-1`~`MEV-10`이다.
- **사건 규칙** 칸의 표시:
  - **[기관]** 자료를 내는 기관이 직접 적은 규칙이다.
  - **[문헌]** 논문·연구 노트에 나온 규칙이다.
  - **[실무]** 업계 실무 규칙이다. 학술 검증이 약하다.
  - **[제안]** 이 문서가 만든 규칙이다. 출처가 없다. Lab 검증 전에는 "규칙 v0 · 미검증"으로만 쓴다.
- **선행·동행·후행**과 선행 개월은 출처가 있을 때만 적었다. 없으면 "[미확인]"이다.
- **라이선스 등급**
  - `FREE_OFFICIAL`: 정부·중앙은행 공개 통계. 기본 public domain 또는 개방 라이선스.
  - `FREE_TERMS_LIMITED`: 무료로 볼 수 있다. 다만 재게시·저장에 조건이 있거나, 제3자 원자료가 섞였거나, 약관을 확인하지 못했다.
  - `PROPRIETARY`: 민간 소유 자료. 서면 허가나 유료 계약이 필요하다.
- **우선순위**: P1 = 무료 공식 + 근거가 잘 받쳐 줌. P2 = 무료지만 근거가 약하거나 PIT·접근에 문제. P3 = 독점이거나 승인이 필요함(가격 경계·FX 제외·재게시 허가 포함).
- **현재 수집**: Y = 지금 파이프라인이 받는다. P = 일부만(같은 파일에 있으나 파싱 안 함, 입력만 있고 집계 없음, 기기 전용 대체물만 있음). N = 없음.
- **표시 경로**: PUB = 공개 화면에 사건선 가능. DEV = 가격·가격 파생이라 기기 RAM에서만(B-PRICE). 공개 파일·Pages·로그에 넣지 않는다.

조사 방법과 한계:

- 웹 검색과 공식 페이지 직접 조회를 썼다. 요청에는 일반 User-Agent만 썼다. 개인 정보는 보내지 않았다.
- 컨테이너에서 막힌 곳(한 번만 적음): `bls.gov`, `bts.gov`, `dol.gov`, `tsa.gov`, `imf.org`, `oecd.org`는 HTTP 403. ISM 보고서 페이지는 404/400. 이 기관들의 내용은 검색 요약이나 다른 기관 사본으로 확인했고, 그렇게 표시했다.
- 원문을 열지 못한 논문은 "(원문 미열람)"으로 적었다.
- 시장 가격 수치, 개인 자료는 하나도 적지 않았다. 표의 숫자는 출처가 적은 규칙의 기준값뿐이다.

---

## 0. 요약

1. 후보 지표 **54개**를 모았다. 라이선스: `FREE_OFFICIAL` 31, `FREE_TERMS_LIMITED` 11, `PROPRIETARY` 12. 우선순위: **P1 13**, P2 20, P3 21.
2. 지금 수집하는 것: 실업률(BLS), CPI(BLS), 실질 GDP(BEA), 국채 10년−3개월(재무부), 실효 연방기금금리(Fed H.15), 연준 총자산(H.4.1), 은행 신용(H.8), 재정수지(재무부 MTS). 기기 전용으로 SPY, HYG/IEF. 경고등 고용(실업률)은 이미 Sahm 규칙의 변형이다(E13).
3. 사용자 예인 **운송**은 무료 공식 근거가 있다. BTS 화물 운송서비스지수(Freight TSI)는 1979~2006년 성장순환 정점·저점을 평균 4~5개월 앞섰다(BTS 2009). 다만 같은 논문이 "실시간 예측에는 쓰기 어렵다"고 적었다. 운송 업종 매출은 Census 분기 서비스 조사(QSS)와 우리 SEC 공시 집계로 만들 수 있다(P2).
4. 다우 운송지수·Cass·ATA·AAR·ISM·Conference Board LEI·미시간대 기대지수·ICE BofA 스프레드·VIX·이익 추정치 수정은 모두 독점이다. 대부분 무료 공식 대체물이 있다(§5 MEV-4).
5. 주식시장 국면 근거는 대부분 가격에서 나온다. 공개 화면에는 못 쓴다. 기기 전용 선으로만 그린다(MEV-6).
6. 3.1 기본 세트는 P1 13개를 권장한다. 모바일은 최근 5개만 보이고 나머지는 접힘 목록이다(§3, MEV-2).
7. 근거선은 **발표 시점 사건**이다. 매 정기 실행에서 새로 판정하고, 덧붙이기만 하고, 과거로 채우지 않는다(§6).

---

## 1. 전체 요약표

열: 번호 · 계열 · 지표 · 사이클 · 국면 신호 · 선행/후행 · 사건 규칙 · 출처 · 라이선스 · PIT 이력 · 현재 수집 · 표시 · 우선순위.
사이클: 경 = 경기, 시 = 주식시장, 순 = 순환매(3.2), 산 = 산업(3.3).
국면 어휘는 OC IA-4 후보(경기: 회복·확장·둔화·수축, 시장: 바닥·상승 초기·상승 후기·하락)를 따른다.

| 번호 | 계열 | 지표 | 사이클 | 국면 신호(방향) | 선행/후행 | 사건 규칙(요약) | 출처 | 라이선스 | PIT 이력 | 수집 | 표시 | 우선 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E01 | 운송 | 화물 운송서비스지수 Freight TSI | 경·산 | 상승 전환 = 수축→회복. 하락 전환 = 확장→둔화 | 선행. 성장순환 대비 평균 4~5개월(1979~2006) | [문헌] 방향 전환이 3개월 이상 유지되면 선 | BTS | FREE_OFFICIAL (트럭 입력은 ATA 자료) | 최근 4개월 잠정치. 공식 빈티지 보관 [미확인] | N | PUB | P1 |
| E02 | 운송 | 운송·창고업 매출 (QSS 48-49) | 경·산 | 전년비 양전환 = 회복 | [미확인] | [제안] 전년비 2분기 연속 음수 뒤 양수 | Census QSS | FREE_OFFICIAL | 과거 보도자료로 최초값 재구성 가능 [미확인] | N | PUB | P2 |
| E03 | 운송 | 운송 그룹 공시 매출 (SIC 4000-4799, 자체 집계) | 산·경 | 중앙값 증가율 양전환 = 회복 | 후행(공시 지연) | [제안] TTM 매출 증가율 중앙값 음→양 | SEC 공시(`sec-qgv2.json`) | FREE_OFFICIAL | 공시 접수 시각이 있어 PIT 가능 | P (입력만) | PUB | P2 |
| E04 | 운송 | 항공 탑승률 (T-100) | 산 | 상승 = 여행 수요 회복 | [미확인] | [제안] 계절조정 3개월 평균 전년비 부호 전환 | BTS T-100 | FREE_OFFICIAL | [미확인] | N | PUB | P2 |
| E05 | 운송 | 다우 운송지수 vs 산업지수 (다우 이론) | 시 | 둘 다 2차 고점 돌파 = 상승 확인 | [미확인] | [실무] 두 지수가 함께 직전 2차 고점(저점)을 넘으면(깨면) 확인 | S&P DJI | PROPRIETARY | 시장 자료(수정 없음) | N | DEV | P3 |
| E06 | 운송 | Cass 화물지수(물동량) | 경·산 | 전년비 양전환 = 회복 | [미확인] | [제안] 전년비 부호 전환 | Cass Information Systems | PROPRIETARY | [미확인] | N | — | P3 |
| E07 | 운송 | ATA 트럭 톤수 | 경·산 | 같음 | [미확인] | [제안] 전년비 부호 전환 | ATA | PROPRIETARY | [미확인] | N | — | P3 |
| E08 | 운송 | AAR 주간 철도 화물 | 경·산 | 같음 | [미확인] | [제안] 13주 합계 전년비 부호 전환 | AAR | PROPRIETARY (약관 미확인) | [미확인] | N | — | P3 |
| E09 | 금리곡선 | 10년−3개월 월평균 역전 | 경·순 | 역전 시작 = 확장→둔화 경고 | 선행. 12개월 앞 확률 모형 | [문헌] 월평균 스프레드가 음수가 된 첫 달 | 재무부 일별 금리곡선 | FREE_OFFICIAL | 수정 드묾(정정·소급 표시 있음) | Y | PUB | P1 |
| E10 | 금리곡선 | 10년−3개월 역전 해소(재가팔라짐) | 경 | 해소 = 둔화→수축 임박 가능성 | [미확인] | [실무] 월평균 음수 3개월 이상 뒤 양수로 바뀐 첫 달 | 재무부 | FREE_OFFICIAL | 같음 | Y | PUB | P2 |
| E11 | 금리곡선 | 10년−2년 | 경 | 역전 = 둔화 경고 | [미확인] | [실무] 월평균 음수 전환·해소 | 재무부 | FREE_OFFICIAL | 같음 | P (2년물 미파싱) | PUB | P2 |
| E12 | 금리곡선 | 단기 선도 스프레드 | 경 | 음수 = 시장이 금리 인하 예상(침체 위험) | 선행 [문헌] | [문헌] 18개월 뒤 3개월물 선도금리 − 현재 3개월물 < 0 | Fed 연구(Engstrom·Sharpe), 재무부 자료로 계산 | FREE_OFFICIAL | 계산식 의존 | N | PUB | P2 |
| E13 | 노동 | Sahm 규칙 | 경·순 | 발동 = 확장→수축 | 동행(침체 초기 실시간) | [문헌] 실업률 3개월 평균 − 직전 12개월 중 3개월 평균 최저 ≥ 0.50%p | BLS 실업률, Sahm(2019) | FREE_OFFICIAL | BLS 과거 보도자료. 계절조정 매년 재추정 | Y (경고등 변형) | PUB | P1 |
| E14 | 노동 | 신규 실업수당 청구 | 경·순 | 하향 교차 = 회복. 상향 교차 = 둔화 | 선행(LEI 구성요소) | [제안] 4주 평균이 26주 평균을 위(아래)로 교차 | DOL ETA | FREE_OFFICIAL | 주간 보도자료 보관. 계절요인 매년 수정 | N | PUB | P1 |
| E15 | 노동 | 계속 청구 | 경 | 같음 | [미확인] | [제안] E14와 같은 방식 | DOL ETA | FREE_OFFICIAL | 같음 | N | PUB | P2 |
| E16 | 노동 | 임시직 고용 | 경·순 | 증가 전환 = 회복. 감소 전환 = 둔화 | 전체 고용에 선행(BLS) | [제안] 6개월 순변화 부호 전환 | BLS CES | FREE_OFFICIAL | BLS 과거 보도자료. 연간 벤치마크 수정 | N | PUB | P1 |
| E17 | 노동 | 제조업 주당 평균 근로시간 | 경 | 증가 = 회복. 감소 = 둔화 | 선행(LEI 구성요소) | [제안] 3개월 평균이 12개월 전보다 높아짐(낮아짐) | BLS CES | FREE_OFFICIAL | 같음 | N | PUB | P1 |
| E18 | 노동 | 비농업 고용 | 경 | 감소 전환 = 수축 | 동행(CB 동행지수 구성요소) | [제안] 3개월 평균 증감 부호 전환 | BLS CES | FREE_OFFICIAL | 같음. Philly Fed 빈티지 있음 | P (계약 등록만) | PUB | P2 |
| E19 | 제조 | ISM 제조업 PMI·신규주문 | 경·순 | 50 상향 = 제조업 확장 | [미확인] | [기관] PMI 50 교차. 42.5 지속 상회 = 전체 경제 확장 | ISM | PROPRIETARY | 유료 과거 자료 | N | — | P3 |
| E20 | 제조 | 지역 연준 제조업 조사 신규주문 (뉴욕 Empire 등) | 경 | 0 상향 = 개선 | [미확인] | [기관] 확산지수 0 교차 | NY Fed 등 | FREE_TERMS_LIMITED | 조사 수정 드묾 [미확인] | N | PUB | P2 |
| E21 | 제조 | 핵심 자본재 주문 (비국방, 항공기 제외) | 경·순 | 양전환 = 회복→확장 | 선행(LEI 구성요소) | [제안] 3개월 평균 전년비 부호 전환 | Census M3 | FREE_OFFICIAL | 과거 보도자료 보관 | N | PUB | P1 |
| E22 | 생산 | 산업생산 | 경·순 | 전년비 양전환 = 회복 | 동행 | [문헌] 전년비 음→양(초기 국면 정의). 양→음은 [제안] | Fed G.17 | FREE_OFFICIAL | 연간 개정. RTDSM 빈티지 | N | PUB | P1 |
| E23 | 생산 | 설비가동률 | 경·순 | 높고 상승 = 확장 후기 | [미확인] | [제안] 12개월 고점 갱신 후 3개월 하락 | Fed G.17 | FREE_OFFICIAL | 같음 | N | PUB | P2 |
| E24 | 종합 | CFNAI-MA3 | 경 | −0.70 하회 = 침체 가능성. +0.20 상회 = 확장 | 동행 | [기관] −0.70·+0.20·+0.70 기준 | Chicago Fed | FREE_TERMS_LIMITED (저작권, 재게시 서면 허가) | 매월 재계산 | N | — | P3 |
| E25 | 생산 | 실질 GDP | 경·순 | 음→양 = 회복 | 동행·후행(분기 발표) | [문헌] 전기비 연율 음→양(초기 국면 정의). 양→음은 [제안] | BEA | FREE_OFFICIAL | 속보·잠정·확정·연간 개정. RTDSM | Y | PUB | P1 |
| E26 | 주택 | 건축허가 | 경·순 | 증가 전환 = 회복. 감소 전환 = 둔화 | 선행(LEI 구성요소, Leamer) | [제안] 3개월 평균의 6개월 변화 부호 전환 | Census NRC | FREE_OFFICIAL | 과거 보도자료 | N | PUB | P1 |
| E27 | 주택 | 주택착공 | 경 | 같음 | 선행 [문헌 약함] | [제안] E26과 같음 | Census NRC | FREE_OFFICIAL | 같음. RTDSM | N | PUB | P2 |
| E28 | 주택 | 신규주택판매 | 경 | 같음 | [미확인] | [제안] 3개월 평균 전년비 부호 | Census | FREE_OFFICIAL | 표본오차 큼 | N | PUB | P2 |
| E29 | 주택 | 주택건설주 상대강도 | 시·순 | 저점 반등 = 상승 초기 | [미확인] | [실무] 주택건설 ETF/시장 비율 26주 평균 상향 교차 [출처 미확인] | ETF 가격(기기) | FREE_TERMS_LIMITED | 시장 자료 | N | DEV | P3 |
| E30 | 소비 | 실질 소매판매 | 경 | 감소 전환 = 둔화 | 동행 [미확인] | [제안] 소매판매÷CPI 3개월 평균 전년비 부호 | Census MARTS + BLS CPI | FREE_OFFICIAL | 과거 보도자료 | N | PUB | P2 |
| E31 | 소비 | 소비자 기대지수 | 경 | 저점 반등 = 회복 | 선행(LEI는 CB 기대지수 사용) | [기관] LEI 구성요소 | 미시간대·Conference Board | PROPRIETARY | 유료 | N | — | P3 |
| E32 | 소비 | 내구재 주문 전체 | 경 | 같음 | [미확인] | [제안] 3개월 평균 전년비 부호 | Census M3 | FREE_OFFICIAL | 과거 보도자료 | N | PUB | P2 |
| E33 | 신용 | 하이일드 스프레드 | 시·경 | 급확대 = 하락·둔화 | [미확인] | [제안] 기준 미정. 기기 대체: HYG÷IEF 20거래일 −5% (경고등) | ICE BofA / 기기 HYG·IEF | PROPRIETARY | FRED 사본은 2026-04부터 3년만 | P (기기 대체) | DEV | P3 |
| E34 | 신용 | 투자등급 스프레드 | 시·경 | 같음 | [미확인] | [제안] 기준 미정 | ICE BofA, Moody's | PROPRIETARY | — | N | — | P3 |
| E35 | 신용 | 초과채권프리미엄 EBP | 경 | 0 상향 = 위험선호 위축 | 선행 [문헌] | [제안] EBP 0 상향(하향) 교차 | Fed Board (Gilchrist·Zakrajšek) | FREE_OFFICIAL (원 채권 자료는 민간) | 매번 재추정. 빈티지 없음 | N | PUB | P2 |
| E36 | 신용 | 대출기준 순강화 비율 (SLOOS, C&I) | 경·순 | 0 하향 = 신용 긴축 종료(초기). 0 상향 = 긴축 | 선행 [문헌, 원문 미열람] | [제안] 순강화 비율 0 교차 | Fed Board SLOOS | FREE_OFFICIAL | 조사 결과 수정 없음 | N | PUB | P1 |
| E37 | 신용 | NFCI | 경·시 | 0 상향 = 평균보다 긴축 | [미확인] | [기관] 0 교차 | Chicago Fed | FREE_TERMS_LIMITED | 매주 전 기간 재계산 | N | — | P3 |
| E38 | 신용 | 은행 신용 증가율 | 경 | 감소 전환 = 수축 | [미확인] | [제안] 전년비 부호 전환 | Fed H.8 | FREE_OFFICIAL | 개정 있음 | Y | PUB | P2 |
| E39 | 물가 | 근원 물가 추세 (근원 PCE·근원 CPI) | 경·순 | 가속 = 확장 후기 | [미확인] | [제안] 3개월 연율 > 12개월 상승률 3개월 연속(가속), 반대(둔화) | BEA, BLS | FREE_OFFICIAL | 과거 보도자료. CPI SA 5년 재계산 | P (헤드라인 CPI만) | PUB | P1 |
| E40 | 정책 | 정책금리 첫 인상·첫 인하 | 경·순·시 | 첫 인상 = 후기. 첫 인하 = 둔화·수축 | 사건 자체 | [기관 사건] FOMC 목표범위 방향 전환 첫 회의 | FOMC 성명 | FREE_OFFICIAL | 수정 없음 | P (실효금리 월평균만) | PUB | P1 |
| E41 | 정책 | 실질금리 (10년 TIPS 수익률) | 경·시 | 급상승 = 긴축 | [미확인] | [제안] 12개월 변화 부호 전환 | 재무부 실질 금리곡선 | FREE_OFFICIAL | 수정 드묾 | N | PUB | P2 |
| E42 | 선행 종합 | Conference Board LEI (3Ds) | 경 | 3Ds 충족 = 침체 임박 | 선행 | [기관] 6개월 확산 ≤ 50 그리고 6개월 연율 < 임계(재추정) | Conference Board | PROPRIETARY | 유료 | N | — | P3 |
| E43 | 선행 종합 | OECD CLI(미국) | 경 | 100 상향·전환점 = 추세 위 회복 | 선행. 설계 6~9개월, 관찰 약 6개월 | [기관] 확정 전환점, 100 교차 | OECD | FREE_TERMS_LIMITED (CC BY 4.0, 제3자 구성 미확인) | MEI 최초 발표·수정 자료 [미확인] | N | PUB | P2 |
| E44 | 기준선 | NBER 경기 정점·저점 공표 | 경 | 공표 = 확정 | 후행(사후 공표) | [기관] 공표일에 선 | NBER | FREE_TERMS_LIMITED (약관 미확인) | 공표일 기록됨 | N | PUB | P2 |
| E45 | 시장 | S&P 500(SPY) vs 장기 이동평균 | 시 | 상향 돌파 = 상승 초기 | [미확인] | [실무] 10개월 이동평균(월말) 교차, 200일선 교차 | SPY 일봉(Worker) | FREE_TERMS_LIMITED | 시장 자료 | P (SPY 기기) | DEV | P3 |
| E46 | 시장 | 시장 폭 (200일선 위 비율, 상승·하락 종목) | 시 | 폭 급개선 = 상승 초기 | [미확인] | [실무] Zweig: 10일 EMA(상승÷(상승+하락)) 0.40 미만 → 10거래일 안 0.615 초과 | 거래소 자료 | PROPRIETARY | — | N | — | P3 |
| E47 | 시장 | 경기민감/방어 비율 | 시·순 | 상승 = 상승 초기 | [미확인] | [제안] 비율이 26주 평균을 상향 교차 | 섹터 ETF(기기) | FREE_TERMS_LIMITED | 시장 자료 | N | DEV | P3 |
| E48 | 시장 | 소형/대형 비율 | 시·순 | 소형 우위 = 바닥·상승 초기 | 판매사 연구: 침체 종료 몇 달 전부터 [근거 약함] | [제안] 비율 26주 평균 상향 교차 | ETF(기기) | FREE_TERMS_LIMITED | 시장 자료 | N | DEV | P3 |
| E49 | 시장 | VIX / 실현 변동성 | 시 | 급등 = 하락 | 동행 | 기기 대체: 경고등 rv20 3년 상위 5% | Cboe / SPY(기기) | PROPRIETARY (VIX) | — | P (rv20 기기) | DEV | P3 |
| E50 | 시장 | 이익 추정치 수정 비율 | 시 | 0 상향 = 상승 | [미확인] | [실무] (상향−하향)/전체 0 교차 | I/B/E/S, FactSet | PROPRIETARY | — | N | — | P3 |
| E51 | 시장 | 공시 이익 증가 기업 비율 (자체 집계) | 시·산 | 50% 상향 = 이익 회복 | 후행 | [제안] 전년비 이익 증가 발행인 비율 50% 교차 | SEC 공시 | FREE_OFFICIAL | 공시 접수 시각 | P (입력만) | PUB | P2 |
| E52 | 원자재 | 유가(WTI) 순상승 | 경 | 급등 = 둔화 위험 | 선행 [문헌] 약 3/4년 | [문헌] 월평균 유가가 직전 36개월 최고치를 넘음(Hamilton) | EIA(원자료 Refinitiv) | FREE_TERMS_LIMITED | 시장 자료 | N | — | P3 |
| E53 | 원자재 | 구리, 구리/금 비율 | 경·시 | 상승 = 성장 기대 | [미확인] | [실무] 6개월 변화 부호 전환 | World Bank 월간 / LME·COMEX | FREE_TERMS_LIMITED | 월평균 | N | — | P3 |
| E54 | 달러 | 달러 지수(광의, H.10) | 경·시 | 급등 = 금융 긴축 | [미확인] | [제안] 12개월 변화 부호 전환 | Fed H.10 | FREE_OFFICIAL | 수정 드묾 | P (파서만, 공개 제외) | — | P3 |

표시 칸 "—"는 지금 경로가 없다는 뜻이다. 허가·결정 뒤에 PUB 또는 DEV로 정한다.

---

## 2. 지표별 메모와 출처

각 항목: 무엇을 재나 → 규칙 근거 → 자료·약관 → 발표·PIT → 우리 코드와 추가 방법.

### 2-A. 운송

**E01 화물 운송서비스지수 (Freight Transportation Services Index, TSI)**
- 측정: 영리 운송(트럭·철도·내륙 수운·파이프라인·항공 화물)의 물량. 연쇄 지수, 계절조정.
- 근거: BTS 연구(Young·Notis 2009)는 화물 TSI가 성장순환 정점·저점을 평균 4~5개월 앞섰다고 썼다. 표본은 1979~2006년. 여객 TSI는 동행이었다.
- 같은 논문의 경고: 이동평균 때문에 최근 6개월 자료가 분석에서 빠진다. 방향 전환 판단에는 보통 3개월 유지가 필요하다. 그래서 "실시간 예측에는 쓰기 어렵다". 사건 규칙의 "3개월 유지"는 이 경험칙이다.
- 다른 연구: Lahiri·Yao(2011)는 TSI를 동행지표로 다뤘다. 선행 여부는 문헌 사이에 차이가 있다.
- 자료: BTS는 연방 통계다. 다만 트럭 부분은 ATA 톤수를 입력으로 쓴다. 재사용 범위는 BTS 표기를 따른다 [미확인].
- 발표·PIT: 월간. 최근 4개월은 잠정치. 공식 빈티지 보관은 확인 못 함.
- 우리 코드: 없음. `bts.gov`는 컨테이너에서 403이다. Actions 수집 경로가 되는지 따로 확인해야 한다.
- 출처: https://apps.bea.gov/icsp/fcsm/assets/docs/2009FCSM_Young_II-B.pdf , https://www.bts.gov/learn-about-bts-and-our-work/statistical-methods-and-policies/technical-note-tsi-documentation , https://www.cesifo-group.de/DocDL/cesifo1_wp3477.pdf

**E02 운송·창고업 매출 (Census Quarterly Services Survey, NAICS 48-49)**
- 측정: 운송·창고업 분기 매출(세금 대상 사업체). 사용자 예 "운송업 매출"에 가장 가깝다.
- 근거: 경기 국면 규칙의 문헌은 찾지 못했다. 규칙은 [제안]이다. Fidelity는 초기 국면에 운송 업종 주가가 회복을 앞서 오른다고 썼다(주가 근거, E05 참고).
- 자료: Census 연방 통계. 저작권 보호 대상 아님(미국 정부 저작물 원칙). 출처 표기 요청.
- 발표·PIT: 분기. 세부 업종(트럭 등) 분리 공표 여부는 확인 못 함.
- 출처: https://www.census.gov/services/index.html , https://www.fidelity.com/webcontent/ap101883-markets_sectors-content/20.05.0/business_cycle/Business_Cycle_Sector_Approach_2019.pdf

**E03 운송 그룹 공시 매출 (자체 집계)**
- 측정: SIC 4000-4799 발행인의 TTM 매출 증가율 중앙값.
- 근거: [제안]. 공시는 분기 말 뒤에 나와 후행이다.
- 자료: 이미 공개된 `sec-qgv2.json`의 `industry_group=transportation`, `revenue_ttm_growth`(OC 1-3 표 "3.1 예" 행). 가격 없음. 공개 가능.
- PIT: 공시 `accepted_at`이 있어 사건 시각을 정확히 남길 수 있다.
- 추가 방법: 산업군 집계 생산자 하나. 사건 시각은 집계에 들어간 마지막 공시의 접수 시각이 아니라 **집계 실행 시각**으로 하고, 둘 다 기록한다.

**E04 항공 탑승률 (BTS T-100)**
- 측정: 유상 여객마일 ÷ 공급 좌석마일. BTS는 계절조정 계열도 낸다.
- 공개 지연은 약 2개월이라는 2차 자료가 있다 [미확인].
- 출처: https://www.bts.gov/content/systemwide-load-factor-us-airlines-seasonally-adjusted

**E05 다우 운송지수 vs 산업지수 (다우 이론)**
- 측정: 두 평균이 같은 방향으로 직전 2차 고점(저점)을 넘는지.
- 근거: 실무 규칙. 산업은 물건을 만들고 운송은 나른다는 논리. 학술 재검토로 Brown·Goetzmann·Kumar(1998, Journal of Finance)가 있다(원문 미열람).
- 자료: 다우 평균은 S&P Dow Jones Indices 소유. 지수 자료의 복제·재전송은 서면 동의가 필요하다(약관 사본 기준, 공식 현행본 미확인). 지수 수준·파생값 재게시 금지 규칙에도 걸린다.
- 대안: 운송 ETF 가격(기기). 지금 Worker 허용 목록에는 운송 ETF가 없다(OC: `WK/index.js:52`).
- 출처: https://doi.org/10.1111/0022-1082.00051 , https://www.spglobal.com/spdji/en/

**E06 Cass 화물지수, E07 ATA 트럭 톤수, E08 AAR 주간 철도 화물**
- 셋 다 민간 자료다. Cass는 월간 보고서에 저작권 표시가 있다. FRED에 사본이 있지만 FRED 경유는 저장 금지 판정이다.
- ATA 톤수는 회원사 표본이다. BTS가 TSI 입력으로 쓴다.
- AAR 약관은 확인 못 했다. 주간 보고는 업계 매체가 출처 표기로 재게시한다.
- 규칙 문헌은 찾지 못했다. 모두 [제안].
- 출처: https://www.cassinfo.com/freight-audit-payment/cass-transportation-indexes , https://www.bts.gov/learn-about-bts-and-our-work/statistical-methods-and-policies/truck-tonnage , https://www.aar.org/data-center/rail-traffic-data/

### 2-B. 금리곡선

**E09 10년−3개월 월평균 역전**
- 근거: Estrella·Trubin(2006, NY Fed). 10년 만기 금리와 3개월 국채(채권 환산)의 스프레드가 가장 좋다. 1968년 이후 6번의 침체는 모두 직전 12개월에 음수 월평균이 3번 이상 있었다. 월평균 기준 역전은 1968~2005년에 오신호가 없었다. 일별 역전은 오신호가 많다.
- 리드: 이 모형은 "12개월 뒤 침체 확률"을 낸다. 고정된 선행 개월이 아니다.
- 우리 코드: 경고등 곡선(`macro_lights_v1.json` `curve`)은 **20영업일 연속 음수**다. 규칙이 다르다. 근거선은 월평균 규칙을 따로 그리고, 경고등은 그대로 둔다.
- 자료: 재무부 일별 금리곡선. 이미 수집한다(`TREASURY:daily_treasury_yield_curve`).
- 출처: https://www.newyorkfed.org/medialibrary/media/research/current_issues/ci12-5.pdf , https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve

**E10 역전 해소(재가팔라짐)**
- 시안의 "장단기 금리차 정상화" 예다.
- 근거: 약하다. Campbell Harvey는 "최근 네 번의 침체에서 재가팔라짐이 침체 시작 전에 나왔다"고 말했다(언론 인용). 학술 규칙은 찾지 못했다.
- 그래서 P2. 화면 문구는 "역전 해소"로만 쓰고 "회복 신호"로 쓰지 않는다. 해석이 반대일 수 있기 때문이다.
- 출처: https://www.axios.com/2023/08/24/recession-indicator-us-economy-downturn

**E11 10년−2년, E12 단기 선도 스프레드**
- Fed 연구(Engstrom·Sharpe 2018, 2019 개정)는 장기 스프레드가 "단기 선도 스프레드"에 통계적으로 밀린다고 했다. 단기 선도 스프레드 = 18개월 뒤 3개월물 선도금리 − 현재 3개월물.
- 10년−2년은 같은 재무부 파일에 2년물이 있다. 지금 파싱하지 않는다.
- E12는 선도금리 계산이 필요하다. 계산 방법을 원문으로 확인한 뒤 넣는다.
- 출처: https://www.federalreserve.gov/econres/notes/feds-notes/dont-fear-the-yield-curve-20180628.htm , https://www.federalreserve.gov/econres/feds/the-near-term-forward-yield-spread-as-a-leading-indicator-a-less-distorted-mirror.htm

### 2-C. 노동

**E13 Sahm 규칙**
- 규칙: 실업률 3개월 이동평균이 직전 12개월 중 3개월 평균 최저보다 0.50%p 이상 높으면 발동(Sahm 2019).
- 실적: 1960년 이후 9번 침체 모두 침체 4개월째까지 발동. 1976년 11월은 침체 없이 발동(CRS).
- 성격: 예측이 아니라 침체 초기의 실시간 확인이다.
- 우리 코드: 경고등 고용(`employment`: 3개월 평균, 12개월 최저, 0.5%p)이 거의 같다. 차이: `low_window_includes_latest: true`. Sahm 원문은 "직전 12개월"이다. 근거선은 원문 정의로 따로 계산하고 차이를 문서에 남긴다.
- 출처: https://www.hamiltonproject.org/wp-content/uploads/2023/01/Sahm_web_20190506.pdf , https://www.everycrsreport.com/reports/IN12410.html

**E14 신규 실업수당 청구, E15 계속 청구**
- 근거: 신규 청구 주간 평균은 Conference Board LEI 구성요소다.
- 사건 규칙: 신뢰할 학술 규칙을 찾지 못했다. 블로그 규칙(4주 평균이 확장기 최저 대비 10% 이상)은 쓰지 않는다. 규칙은 [제안]으로 두고 Lab 검증 대상이다.
- 시안의 "신규 실업수당 ↓"는 이 지표의 하향 교차 사건이다.
- 자료: DOL ETA 주간 자료(공개). 계절요인은 매년 바뀐다. 과거 주간 보도자료로 최초값을 재구성할 수 있다 [확인 필요]. `dol.gov`는 403, `oui.doleta.gov`는 열린다.
- 출처: https://oui.doleta.gov/unemploy/claims.asp , https://www.conference-board.org/topics/us-leading-indicators

**E16 임시직 고용**
- 근거: BLS는 임시직을 전체 고용의 선행지표로 본다. BLS(2010)는 최근 순환에서 임시직 감소가 전체 고용 감소보다 1년 넘게 먼저 시작했다고 썼다. 회복기 시차는 훨씬 짧았다.
- 출처: https://www.bls.gov/careeroutlook/2010/fall/oochart.pdf , https://www.bls.gov/opub/mlr/2011/04/art6full.pdf , https://www.bls.gov/opub/mlr/2014/article/nonfarm-employment-continued-its-road-to-recovery-in-2013.htm

**E17 제조업 주당 평균 근로시간, E18 비농업 고용**
- E17은 LEI 구성요소다. BLS MLR(2014)도 선행 성격을 언급한다.
- E18은 CB 동행지수 구성요소다. `CES0000000001`은 이미 `primary_contract.py` 등록 계열이다. 화면에는 안 쓴다.
- 자료: BLS public domain(기존 판정, PRIMARY_AGENCY_EVIDENCE). `bls.gov`는 컨테이너에서 403이다. 기존 수집은 Actions 경로다.

### 2-D. 제조·생산

**E19 ISM 제조업 PMI·신규주문**
- 규칙: ISM 자체 문구. 50 위 = 제조업 확장. 42.5 위가 이어지면 전체 경제 확장(ISM 보도 문구의 재게시 기준). 신규주문−재고 차이는 실무 지표다. 출처를 확인하지 못했다.
- 약관: ISM은 사전 서면 허가 없이 지수의 복제·배포·편입을 금지한다. 표·차트 같은 파생물도 막는다(2차 사본 기준). 과거 자료는 유료.
- 판정: P3. 대체는 E20·E21.
- 출처: https://www.ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/ , https://www.calculatedriskblog.com/2024/12/ism-manufacturing-index-increased-to.html

**E20 지역 연준 제조업 조사 신규주문 (Empire State 등)**
- 측정: 응답 기업의 증가−감소 비율(확산지수). 0 위 = 개선.
- 자료: NY Fed 약관은 출처 표기·변경 표시를 조건으로 저장·변형·배포를 허용한다(기존 판정 PRIMARY_AGENCY_EVIDENCE [N1]). 필라델피아·리치먼드·캔자스시티·댈러스 조사는 기관별 약관을 따로 봐야 한다.
- 근거: ISM 대체로 쓰이지만, 국면 규칙의 학술 근거는 이번에 찾지 못했다. 그래서 P2.
- 출처: https://www.newyorkfed.org/survey/empire/empiresurvey_overview

**E21 핵심 자본재 주문 (비국방, 항공기 제외)**
- 근거: LEI 구성요소. 소비재·원자재 신규주문도 LEI에 있다. Fidelity는 중기 국면에 기업이 설비투자에 자신감을 가진다고 썼다.
- 자료: Census M3. 속보(advance) 뒤 전체 보고서로 수정된다. 일정은 Census 경제지표 캘린더.
- 출처: https://www.census.gov/manufacturing/m3/index.html , https://www.census.gov/economic-indicators/

**E22 산업생산, E23 설비가동률**
- 근거: Fidelity는 초기 국면을 "GDP·산업생산 같은 활동이 음에서 양으로 꺾이는 때"로 정의한다. 후기 국면은 "설비가 빠듯해지고 물가 압력이 오르는 때"다. E22 상향 규칙은 이 정의다. 하향 규칙과 E23 수치 기준은 [제안]이다.
- 자료: Fed Board G.17. Board 자료는 별도 표시가 없으면 public domain(기존 판정 [F1]). 연간 개정이 있다.
- 출처: https://www.federalreserve.gov/releases/g17/About.htm , Fidelity 위 PDF

**E24 CFNAI-MA3**
- 규칙(기관): 확장 뒤 MA3가 −0.70 아래면 침체 가능성 증가. 수축 뒤 −0.70 위면 확장 가능성 증가, +0.20 위면 확장 가능성 상당. 확장 2년 이후 +0.70 위면 지속적 물가 상승 가능성 증가. 85개 월간 지표의 가중평균.
- 약관: Chicago Fed 자료는 저작권 대상이다. 비영리·출처 표기 조건의 서면물 복제만 허용한다. 재게시·배포는 서면 허가가 필요하다.
- 판정: 규칙은 가장 명확하다. 그러나 허가 전에는 P3(MEV-5).
- 출처: https://www.chicagofed.org/research/data/cfnai/current-data , https://www.chicagofed.org/research/data/cfnai/about , https://www.chicagofed.org/utilities/legal-notices

**E25 실질 GDP**
- 근거: Fidelity 초기 국면 정의(음→양). 이미 수집한다(BEA NIPA T10101).
- PIT: 속보·잠정·확정·연간 개정이 있다. Philadelphia Fed 실시간 자료(RTDSM)에 빈티지가 있다(약관 미확인).
- 출처: https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/real-time-data-set-for-macroeconomists

### 2-E. 주택

**E26 건축허가, E27 주택착공, E28 신규주택판매**
- 근거: 건축허가는 LEI 구성요소. Leamer(2007)는 GDP 구성요소 중 주거투자가 침체의 가장 좋은 조기 경보라고 했다. 전후 10번 중 8번이 주택·내구재 문제 뒤에 왔다.
- 자료: Census 신규 주거 건설(NRC). 2025~2026년에는 발표 지연과 두 달 묶음 발표가 있었다(Census 공지). PIT 기록 시 실제 발표일을 써야 하는 이유다.
- 신규주택판매는 표본오차가 크다. P2.
- 출처: https://www.census.gov/construction/nrc/index.html , https://www.nber.org/papers/w13428

**E29 주택건설주**
- 가격 자료다. 기기 전용. 규칙 출처를 확인하지 못했다.

### 2-F. 소비

**E30 실질 소매판매, E32 내구재 주문**
- Census MARTS·M3. 실질화는 BLS CPI로 나눈다. 규칙은 [제안].
- 출처: https://www.census.gov/retail/index.html

**E31 소비자 기대지수**
- 미시간대 자료는 서면 동의 없이 재전송·배포·게시할 수 없다. Conference Board 자료도 배포·게시 라이선스가 없다(학술 라이선스 기준).
- 출처: https://data.sca.isr.umich.edu/agreement.php , https://www.conference-board.org/pdf_free/Academic_Licence.pdf

### 2-G. 신용·금융 여건

**E33 하이일드, E34 투자등급 스프레드**
- ICE BofA 지수는 ICE Data Indices 소유다. FRED 사본은 사전 서면 허가 없는 복제 금지 표시가 있다. FRED는 2026년 4월부터 ICE BofA 계열을 3년치만 보여 준다고 공지했다(FRED 계열 페이지, 검색 요약).
- 기존 판정: BAMLH0A0HYM2는 ICE 원권리자 제약이 있다(FRED_ALFRED_EVIDENCE).
- 기기 대체: 경고등 신용(HYG÷IEF, 20거래일 −5%, 추정)이 이미 있다. 가격 파생이라 공개 불가.
- 출처: https://fred.stlouisfed.org/series/BAMLH0A0HYM2 (원권리자 표시 확인용. 수집 금지)

**E35 초과채권프리미엄 (EBP)**
- 측정: 회사채 스프레드에서 기대 부도 위험을 뺀 부분. Gilchrist·Zakrajšek(2012).
- 자료: Fed Board가 CSV(날짜, GZ 스프레드, EBP, 추정 침체확률)를 낸다. Board 기본 public domain. 다만 원 채권 가격은 민간 자료에서 나왔다.
- PIT: 모형을 다시 추정해 전 기간이 바뀐다. 빈티지가 없다. 과거 근거선 재구성에 약하다. 그래서 P2.
- 출처: https://www.federalreserve.gov/econres/notes/feds-notes/updating-the-recession-risk-and-the-excess-bond-premium-20161006.html

**E36 대출기준 순강화 비율 (SLOOS)**
- 근거: Fidelity는 초기 국면을 "신용 긴축이 멈춤", 수축 국면을 "신용이 귀함"으로 적었다. 학술 근거로 Lown·Morgan(2006, Journal of Money, Credit and Banking)이 SLOOS와 대출·산출의 관계를 보였다(원문 미열람).
- 자료: Fed Board 분기 조사. 결과 수정이 없어 발표일이 곧 PIT다.
- 규칙: 0 교차는 [제안]이다. 순강화 비율 0은 "강화와 완화가 같음"이라는 정의상 기준이다.
- 출처: https://www.federalreserve.gov/data/sloos.htm

**E37 NFCI**
- 기관 설명: 105개 금융 지표. 평균 0, 표준편차 1. 양수 = 평균보다 긴축, 음수 = 평균보다 완화.
- 약관: Chicago Fed(E24와 같음). P3.
- 출처: https://www.chicagofed.org/research/data/nfci/about

**E38 은행 신용 (H.8)**
- 이미 수집한다(Credit 축). 규칙은 [제안].

### 2-H. 물가·정책

**E39 근원 물가 추세**
- 근거: Fidelity 후기 국면 = 물가 압력 상승, 긴축 정책. CFNAI 물가 규칙(E24)도 같은 방향이다. 가속 규칙 자체는 [제안].
- 우리 코드: 헤드라인 CPI(CUUR0000SA0)만 있다. 근원 CPI는 같은 BLS API로, 근원 PCE는 BEA로 받는다.
- 경고등 물가(전년비 > 5%)와 다르다. 경고등은 그대로 둔다.

**E40 정책금리 첫 인상·첫 인하**
- 사건 자체가 날짜다. FOMC 성명 발표 시각이 PIT다.
- 근거: Fidelity 초기 = 완화적 정책, 후기 = 긴축 정책, 수축 = 다시 완화.
- 우리 코드: H.15 실효금리 월평균만 있다. 목표범위 변경 이력은 FOMC 성명에서 얻는다.
- 출처: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm

**E41 실질금리**
- 재무부 일별 실질 금리곡선. 규칙은 [제안].
- 출처: https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_real_yield_curve

### 2-I. 선행 종합·기준선

**E42 Conference Board LEI (3Ds)**
- 10개 구성요소: 제조업 주당 근로시간, 신규 청구, 소비재·원자재 신규주문, ISM 신규주문, 핵심 자본재 주문, 건축허가, S&P 500, Leading Credit Index, 10년−연방기금 금리차, 소비자 기대.
- 3Ds 규칙: 6개월 확산지수 ≤ 50 이고 6개월 연율 성장률 < 임계. 임계는 중앙값으로 재추정된다. 2026-10 페이지는 −4.3%다. 릴리스마다 다르다.
- 판정: 지수는 독점(P3). 대신 **구성요소 중 공식 무료 계열(E14·E17·E21·E26·E09 계열)을 따로 쓰는 것**이 이 목록의 기본 방침이다. LEI 지수 수준을 복제하지 않는다.
- 출처: https://www.conference-board.org/topics/us-leading-indicators

**E43 OECD CLI(미국)**
- 기관 설명: 추세 대비 경기 전환점을 6~9개월 앞서 잡도록 설계. 관찰 선행은 약 6개월. 100 = 추세. 확정 전환점과 잠정 전환점을 구분한다.
- 약관: 2024-07 이후 OECD 콘텐츠는 기본 CC BY 4.0. 데이터 단위 조건과 미국 CLI의 제3자 구성요소는 확인하지 못했다. `oecd.org`는 컨테이너에서 403.
- 출처: https://oecd.org/content/dam/oecd/en/data/methods/OECD-System-of-Composite-Leading-Indicators.pdf , https://www.oecd.org/en/data/insights/data-explainers/2024/04/composite-leading-indicators-frequently-asked-questions.html , https://www.oecd.org/en/about/news/press-releases/2024/07/oecd-data-publications-and-analysis-become-freely-accessible.html

**E44 NBER 정점·저점 공표**
- 근거선이 아니라 **기준선**이다. 공표는 사후에 나온다. 그래서 "확정" 표식으로 따로 그린다.
- "과거 국면 전환 빈도"(사용자 결정 확률 근거)의 국면 날짜 기준이 된다. 날짜(기준 월)와 공표일을 둘 다 저장한다.
- 출처: https://www.nber.org/research/business-cycle-dating

### 2-J. 시장 (가격 자료)

- 공통: 모두 가격·가격 파생이다. 공개 화면·공개 파일에 못 넣는다(B-PRICE). 기기 RAM에서만 그린다.
- 주식시장이 경기를 앞선다는 근거: S&P 500이 LEI 구성요소다. 침체 종료 전 시장 저점의 선행 개월(중앙값 약 4개월)은 운용사·블로그 자료뿐이라 [근거 약함]. Mennis(1995, Financial Analysts Journal)가 학술 출처다(원문 미열람). https://rpc.cfainstitute.org/research/financial-analysts-journal/1995/security-prices-and-business-cycles
- **E45**: Faber(2007) 10개월 이동평균 교차(월말). 200일선은 실무 관행. SPY는 Worker 허용 목록에 있다. https://ritholtz.com/2012/01/revisiting-quant-approach-to-tactical-asset-allocation
- **E46**: Zweig 폭 돌파(Winning on Wall Street, 1986, 원문 미열람). 거래소 상승·하락 종목 수는 독점 자료다. https://help.tc2000.com/m/69404/l/750498-t2103-zweig-breadth-thrust
- **E47**: Fidelity 매핑(초기: 경기소비재·금융·부동산·산업재·IT·소재 강세, 후기·수축: 필수소비재·유틸리티·헬스케어 강세)을 비율로 쓴 것. 규칙은 [제안]. 섹터 ETF는 대부분 Worker 허용 목록 밖이다.
- **E48**: Putnam은 소형주가 침체 공식 종료 몇 달 전부터 대형주를 앞섰다고 썼다(판매사 자료, 표본 5회). Russell 지수는 독점. https://www.putnam.com/advisor/content/perspectives/7901-trends-in-small-and-large-cap-stocks-during-recessions
- **E49**: VIX는 Cboe 소유, 외부 재배포 금지. 기기 대체는 경고등 시장의 rv20. https://datashop.cboe.com/main-channel-tick-data
- **E50**: I/B/E/S·FactSet 독점. 학술 1차 출처는 이번에 찾지 못했다.
- **E51**: SEC 공시 실제 이익으로 만드는 무료 대체. 후행이다.

### 2-K. 원자재·달러

**E52 유가**
- 근거: Hamilton(1983, Journal of Political Economy)은 전후 미국 침체 대부분이 약 3/4년 앞선 유가 급등 뒤에 왔다고 했다(예외 1960년). "순유가상승(직전 36개월 최고치 초과)"은 Hamilton(2003, Journal of Econometrics)의 정의다(원문 미열람).
- 약관: EIA 자료는 public domain이다. 그런데 EIA 현물 가격표의 출처는 "Refinitiv, an LSEG business"다. 제3자 자료라 재게시 범위를 따로 봐야 한다. 그래서 FREE_TERMS_LIMITED.
- 가격 경계: 원자재 가격이 B-PRICE 대상인지 결정이 필요하다(MEV-7).
- 출처: https://www.eia.gov/about/copyrights_reuse.php , https://www.eia.gov/dnav/pet/TblDefs/pet_pri_spt_tbldef2.asp

**E53 구리, 구리/금 비율**
- 근거: 실무(Gundlach의 10년 금리 지표). 학술 규칙 없음.
- 자료: World Bank 월간 상품 가격("Pink Sheet"). CC BY 4.0이라는 2차 목록만 있고 공식 라이선스 문구는 확인 못 함. LME·COMEX 일별 가격은 독점.
- 출처: https://www.worldbank.org/en/research/commodity-markets , https://mining.com/?p=1009479

**E54 달러 지수(광의)**
- Fed H.10. 파서는 있다. 그러나 공개 가격 경계가 FX를 뺀다(`PUBLIC_FX_EXCLUDED`, `raw_axes_v0.py`). 공개하려면 결정이 필요하다.
- ICE의 DXY는 독점이다. 쓰지 않는다.
- 출처: https://www.federalreserve.gov/releases/h10/summary/

### 2-L. 순환매 매핑(3.2) 근거

- **Fidelity 경기순환 섹터 접근(2019)**: 1962~2016년 미국 상위 3000종목, GICS 섹터 기준.
  - 초기(평균 약 1년): 금리 민감(경기소비재·금융·부동산), 경기 민감(산업재·IT·소재) 강세. 운송·자본재 주가는 회복을 앞서 오르는 경우가 많다. 헬스케어·유틸리티·에너지 약세.
  - 중기(평균 약 3년 반): 섹터 차이가 가장 작다. IT 최상. 소재·유틸리티 약세.
  - 후기(평균 약 1년 반): 에너지·소재, 그리고 방어 섹터(헬스케어·필수소비재·유틸리티) 강세. IT·경기소비재 약세.
  - 수축(평균 1년 조금 안 됨): 필수소비재·유틸리티·헬스케어 강세.
  - 단서: 국면을 건너뛰거나 되돌아간 순환이 있다.
- **Stovall (S&P Guide to Sector Investing, 1995/1996)**: 시장 순환 단계별 섹터 순서의 고전. 원문 미열람. 연도부터 2차 자료끼리 다르다.
- **반론**: 경기 국면을 완벽히 안다고 해도 관행적 순환매의 초과수익은 거래 비용 뒤 통계적으로 0과 구별되지 않았다는 연구가 있다("The Myth of Sector Rotation"). 그래서 3.2 확률은 IA-3대로 "미산출"에서 시작한다.
- 우리 기준: 업종 단위는 SIC 그룹(IA-5, `gics_used: false`)이다. Fidelity의 GICS 섹터와 SIC 그룹의 대응은 **근사**일 뿐이다. 화면에 "GICS 연구를 SIC 그룹에 근사 대응"이라고 적는다.
- 출처: https://www.fidelity.com/webcontent/ap101883-markets_sectors-content/20.05.0/business_cycle/Business_Cycle_Sector_Approach_2019.pdf , https://acfr.aut.ac.nz/__data/assets/pdf_file/0005/294287/The-Myth-of-Sector-Rotation-non-blind.pdf

### 2-M. PIT 자료원 공통

- FRED·ALFRED는 저장·캐시 금지 판정이다(`BLOCKED_UNLESS_WRITTEN_PERMISSION`). FRED에 있는 일부 계열은 제3자 저작권(ICE, Cass, ATA 등)이다. ALFRED 빈티지도 같은 약관이다.
- 원기관 대체:
  - BLS·Census·BEA·DOL 과거 보도자료: 최초 발표값과 발표일을 재구성할 수 있다. 수작업 범위가 크다.
  - Philadelphia Fed RTDSM: 주요 변수의 빈티지. 매월 말 갱신. 변수 목록과 재사용 약관은 확인 못 했다.
  - OECD MEI 최초 발표·수정 자료(있다고 알려짐) [미확인].
- 시장 자료와 SLOOS·FOMC는 수정이 없거나 드물어 발표 시각이 곧 PIT다.
- Census 사이트는 소유자 정보 없는 과도한 로봇 접근을 막을 수 있다고 적었다. 수집기는 낮은 빈도로, 정해진 일정에만 받는다.

---

## 3. 기본 근거선 세트 제안 (P1만)

### 3-1. 3.1 경기·시장 그래프 기본 13개

| 순 | 지표 | 화면 이름(짧게) | 사건 규칙 | 신호 국면 | 출처 |
|---|---|---|---|---|---|
| 1 | E09 | 금리곡선 역전 | 10년−3개월 월평균이 음수가 된 첫 달 | 확장→둔화 경고 | 재무부, Estrella·Trubin 2006 |
| 2 | E13 | Sahm 발동 | 실업률 3개월 평균 − 직전 12개월 최저 ≥ 0.50%p | 확장→수축 | BLS, Sahm 2019 |
| 3 | E14 | 신규 청구 ↑/↓ | 4주 평균이 26주 평균을 교차 [제안] | 둔화 / 회복 | DOL ETA, LEI 구성 |
| 4 | E16 | 임시직 ↑/↓ | 6개월 순변화 부호 전환 [제안] | 회복 / 둔화 | BLS CES |
| 5 | E17 | 제조 근로시간 ↑/↓ | 3개월 평균 vs 12개월 전 [제안] | 회복 / 둔화 | BLS CES, LEI 구성 |
| 6 | E21 | 자본재 주문 ↑/↓ | 3개월 평균 전년비 부호 전환 [제안] | 회복→확장 / 둔화 | Census M3, LEI 구성 |
| 7 | E22 | 산업생산 반등 | 전년비 음→양 (반대는 [제안]) | 수축→회복 | Fed G.17, Fidelity |
| 8 | E25 | GDP 반등 | 실질 GDP 전기비 연율 음→양 | 수축→회복 | BEA, Fidelity |
| 9 | E26 | 건축허가 ↑/↓ | 3개월 평균 6개월 변화 부호 전환 [제안] | 회복 / 둔화 | Census NRC, Leamer 2007 |
| 10 | E36 | 대출기준 완화/강화 | 순강화 비율 0 교차 [제안] | 회복 / 둔화 | Fed SLOOS |
| 11 | E39 | 근원물가 가속/둔화 | 3개월 연율 > 12개월 3개월 연속 [제안] | 확장 후기 | BEA·BLS, Fidelity |
| 12 | E40 | 첫 인상/첫 인하 | FOMC 목표범위 방향 전환 첫 회의 | 후기 / 둔화·수축 | FOMC |
| 13 | E01 | 화물 운송 ↑/↓ | 화물 TSI 방향 전환 3개월 유지 | 회복 / 둔화 | BTS, Young·Notis 2009 |

- E44(NBER 공표)는 근거선이 아니라 **확정선**이다. 점선 등 다른 모양으로 늘 켠다. 개수에 넣지 않는다.
- 시장 곡선: P1 공개 근거선은 없다. 주식시장 위치의 근거는 위 경기선이 간접 근거다(시장은 경기를 앞선다는 LEI 구성 근거). 기기에서는 E45(SPY 10개월선 교차)를 "기기 전용" 선으로 켤 수 있게 한다(MEV-6).
- [제안] 규칙 선은 라벨 옆에 "v0 · 미검증"을 붙인다(MEV-10).
- 시안 세 예의 위치: "운송업 매출 ↑" → 13번(E01)과 토글 E03. "장단기 금리차 정상화" → 토글 E10(P2, 해석 주의). "신규 실업수당 ↓" → 3번 하향 교차.

### 3-2. 3.2 순환매 기본 세트

3.1의 같은 사건을 국면 전환별로 묶는다. 새 지표는 늘리지 않는다.

| 국면 전환 | 근거선(P1) | Fidelity 강세 섹터(GICS, 참고) |
|---|---|---|
| 수축→회복(초기) | E22 반등, E25 반등, E36 완화 전환, E14 하향 교차, E01 상승 | 경기소비재·금융·부동산·산업재·IT·소재 |
| 회복→확장(중기) | E21 상승, E16 상승, E26 상승 | IT(차이 작음) |
| 확장→후기 | E39 가속, E40 첫 인상, E09 역전 | 에너지·소재, 방어 섹터 |
| 후기→수축 | E13 발동, E14 상향 교차, E36 강화 전환, E40 첫 인하 | 필수소비재·유틸리티·헬스케어 |

- 섹터 상대강도(E47·E48)는 기기 전용 확인선이다. 기본 세트에 넣지 않는다.
- 확률은 IA-3대로 "미산출"이다. 과거 빈도를 쓸 때는 E44 기준 날짜와 이 표의 사건으로 "사건 뒤 n개월 안 국면 전환 비율 + 표본 수"를 Lab에서 먼저 낸다.

### 3-3. 한 번에 보이는 개수

- **모바일(390px 기준)**: 현재 보이는 기간 안에서 발표일이 **최근인 5개**만 선으로 그린다. 나머지는 그래프 아래 "근거 더 보기 (n)" 접힘 목록. 목록에서 켜면 선이 추가된다(최대 8개).
- **PC**: 최근 10개까지 선. 나머지는 옆 목록.
- 같은 날 사건이 여럿이면 선 하나에 숫자 표식(예: "3")을 단다. 눌러서 펼친다.
- 방향은 색과 화살표로 같이 보인다(상향·하향). 색만으로 구분하지 않는다. 손그림 분위기를 유지한다.
- 사용자가 켠 목록은 개인 설정이다(B-PERSONAL). 공개 파일에 넣지 않는다.

---

## 4. SIC 그룹별 산업 지표 후보 (3.3)

단위는 IA-5 권장(SIC 그룹 v0 10개 + 하위 그룹). 무료 공식 자료를 먼저 적었다. 규칙은 모두 [제안]이다. 선행 관계는 출처가 없으면 적지 않았다.

| SIC 그룹(id) | 무료 공식 후보 | 독점·제한 후보 | 메모 |
|---|---|---|---|
| 자원·광업 `resources_mining` | EIA 주간 석유 현황(원유 생산·재고·정제 가동률), G.17 광업 생산, E52 유가 | Baker Hughes 리그 수(사이트 403, 약관 미확인), LME 금속 가격 | 유가는 Refinitiv 출처 문제(E52) |
| 건설 `construction` | Census 건설 지출(C30), E26 건축허가, E27 착공, BLS 건설 고용 | AIA 건축 청구 지수(페이지 404, 약관 미확인) | 주택·비주택 구분 필요 |
| 식품·담배 `food_tobacco` (음료 하위 포함) | Census 소매 식품·음료점 매출, BLS CPI 가정용 식품, BLS PPI 식품 원재료 | 민간 판매 데이터(Nielsen 등) | 방어 후보. 마진 = CPI 대비 PPI 차이는 [제안] |
| 제조·산업·기술 `manufacturing_industrial_tech` | E21 핵심 자본재 주문, E22 산업생산(업종별), E23 가동률, E20 지역 연준 조사 | E19 ISM | 범위가 넓다. 하위 그룹으로 나눠야 한다(IA-5) |
| └ 반도체 `semiconductors` | G.17 반도체·전자부품 생산 [계열 확인 필요], Census M3 컴퓨터·전자제품 신규주문 | SIA(WSTS 3개월 이동평균 세계 매출), SEMI 장비 billings | SEMI 북미 수주/출하 비율(book-to-bill)은 **2017년 발표 중단**(마지막은 2016-12). 2022-02 이후 billings 보도자료도 끝남 |
| └ 컴퓨터 `computers` | Census M3 컴퓨터·전자제품 주문·출하 | — | — |
| └ 의료기기 `medical_devices` | BLS 의료기기 PPI [미확인], Census M3 [미확인] | — | 경기 지표 근거 약함 |
| 운송 `transportation` | E01 화물 TSI, E02 QSS 운송 매출, E03 공시 매출, E04 항공 탑승률, TSA 검색대 통과 인원(사이트 403) | E06 Cass, E07 ATA, E08 AAR, E05 다우 운송지수 | 사용자 예. 철도·항공·트럭 하위 그룹 분리 후보 |
| 통신 `telecommunications` | Census QSS 정보·통신 매출, BLS CPI 통신 서비스 | — | 경기 민감도 낮음 [미확인] |
| 유틸리티 `utilities` | EIA 전력 판매(월간), E09·E41 금리 | 천연가스 현물(출처 제3자 여부 미확인) | 방어 후보. 금리 민감 |
| 유통·소매 `wholesale_retail` (식품 소매 하위 포함) | Census MARTS 업종별 소매, **음식점·주점 매출(NAICS 722)**, Census 도매 재고/판매 비율, 소매 재고/판매 비율 | 외식 동일점 매출(Black Box 등), 카드 결제 자료 | 사용자 예 "외식 동일점 매출"은 독점. 무료 대체는 Census 722 매출(동일점 아님) |
| 금융·부동산 `finance_real_estate` | E09 금리곡선, E36 SLOOS, E38 H.8 대출, FDIC 분기 은행 현황(순이자마진·부실), Census 임대 공실률(HVS) | 상업용 부동산 가격 지수, E33 스프레드 | 은행·보험·REIT 따로 볼 것(그룹 메모) |
| 서비스·SW·의료 `services_software_health` (SW·의료 서비스 하위) | Census QSS 소프트웨어·정보 서비스 매출, BLS 의료 고용, BLS JOLTS 전문서비스 구인 | 호텔 객실 지표(STR 등), 앱·클라우드 사용량 | 의료는 방어 후보 |

출처(§4):
- EIA 주간 석유: https://www.eia.gov/petroleum/supply/weekly/
- Census 건설 지출: https://www.census.gov/construction/c30/c30index.html
- Census 소매: https://www.census.gov/retail/index.html , 도매: https://www.census.gov/wholesale/index.html , HVS: https://www.census.gov/housing/hvs/index.html
- FDIC 분기 은행 현황: https://www.fdic.gov/quarterly-banking-profile
- SEMI billings(북미 B/B 중단 공지 포함): https://www.semi.org/en/products-services/market-data/equipment/billings-report
- SIA 월간 매출(WSTS 3개월 이동평균): https://www.semiconductors.org/
- TSA 통과 인원: https://www.tsa.gov/travel/passenger-volumes (컨테이너 403)
- Fed G.17: https://www.federalreserve.gov/releases/g17/About.htm

공통 원칙:
- 산업 지표가 없는 그룹은 E03·E51 같은 **공시 집계**를 기본으로 한다. 모든 그룹에 같은 방법이 가능하다.
- 산업 사이클 위치는 "가설 · 미산출"(IMP b-1). 조건 칸의 숫자는 방법론 결정 뒤에 넣는다.

---

## 5. 결정 후보 MEV-1~MEV-10

| 번호 | 무엇을 | 선택지 | 권장안 | 근거 |
|---|---|---|---|---|
| MEV-1 | 3.1 기본 근거선 세트 | (a) §3-1 P1 13개 (b) 문헌 규칙만 7개(E01·E09·E13·E22·E25·E40 + E44 확정선) (c) 시안 3개 유지 | **(a).** [제안] 규칙은 "v0 · 미검증" 표식 | 모두 무료 공식이다. 출처 규칙이 있는 것과 LEI 구성요소로 받쳐지는 것만 골랐다. (b)는 수축 쪽 근거가 얇다 |
| MEV-2 | 한 번에 보이는 선 수 | (a) 모바일 최근 5 + 접힘, PC 10 (b) 모두 (c) 3 | **(a).** 같은 날은 묶음 표식 | 13개를 한 화면에 그리면 390px에서 겹친다. 최근 발표 순이 "지금 위치" 판단과 맞다 |
| MEV-3 | FRED 약관 처리 | (a) 원기관 직접 수집(BLS·Census·BEA·Fed Board·재무부·DOL·BTS) (b) FRED 서면 허가 요청 (c) FRED 사용 | **(a).** FRED·ALFRED는 계속 막음. 빈티지는 원기관 과거 보도자료와 RTDSM(약관 확인 뒤) | 기존 판정 `BLOCKED_UNLESS_WRITTEN_PERMISSION`. FRED의 ICE·Cass·ATA 계열은 FRED 허가로도 원권리자 권리가 해결되지 않는다 |
| MEV-4 | 독점 자료 요청 | (a) 모두 건너뜀, 무료 대체 사용 (b) ISM만 요청 (c) Conference Board LEI 요청 (d) 운송 3종(Cass·ATA·AAR) 요청 | **(a).** 대체: ISM→E20·E21, LEI→구성요소 개별 계열, Cass·ATA·AAR→E01·E02·E03, ICE→E35·기기 HYG/IEF, VIX→기기 rv20, 미시간대→없음(빈칸) | 모두 재게시·파생물에 서면 허가가 필요하다. 공개 화면 목적과 맞지 않는다. 무료 대체로 13개 기본 세트가 채워진다 |
| MEV-5 | Chicago Fed(CFNAI·NFCI) | (a) 서면 허가 요청 (b) 비공개 Lab 참고만 (c) 미사용 | **(a)를 요청, 답 전까지 (b).** 공개 화면 미표시 | CFNAI 규칙(−0.70/+0.20)은 기관이 밝힌 가장 명확한 국면 규칙이다. 재게시는 서면 허가 조건이다 |
| MEV-6 | 가격 기반 시장 근거선 | (a) 기기 전용 표시 허용(SPY 10개월선 등) (b) 미표시 (c) Worker 허용 목록 확대(운송·섹터·소형주 ETF)까지 | **(a).** (c)는 별도 승인 | B-PRICE. 시장 곡선에 공개 근거선이 없으면 시장 위치 근거가 비게 된다. 기기 RAM 계산은 기존 경고등과 같은 경로다 |
| MEV-7 | 원자재·달러 | (a) 공개 화면 제외 (b) 공개 (c) 기기 전용 | **(a).** 결정 전까지 | 유가는 EIA 표지만 원자료가 Refinitiv. 달러는 `PUBLIC_FX_EXCLUDED`. 구리 공식 라이선스 미확인 |
| MEV-8 | SEC 공시 산업군 집계 선(E03·E51) | (a) 도입(P2, 공개) (b) 보류 | **(a).** 3.3 모든 그룹의 기본 지표 | 사용자 예 "운송업 매출"을 우리 자료로 바로 만들 수 있다. 가격 없음. 공시 시각으로 PIT가 정확하다 |
| MEV-9 | 근거선 기록 방식 | (a) §6 규칙(발표 시점, 덧붙이기, 과거 채움 금지) (b) 매번 전체 재계산 | **(a).** IA-16 (b)+(a)와 함께 | 확률 근거가 "과거 국면 전환 빈도"다. 나중 수정치로 과거 선을 다시 그리면 빈도가 부풀려진다 |
| MEV-10 | [제안] 규칙 표시 | (a) "v0 · 미검증" 표식으로 표시 (b) Lab 검증 전 숨김 (c) 표식 없이 표시 | **(a).** 기본 세트 13개 중 9개가 [제안] 규칙을 쓴다 | 숨기면 화면이 비고, 표식 없이 쓰면 근거 없는 수치 확정 금지 원칙에 어긋난다 |

---

## 6. 근거선 기록 규칙 (발표 시점·덧붙이기·과거 채움 금지)

이 규칙은 IMP b-3(발표 시점 수직선)과 OC IA-16을 구체화한 것이다.

1. **선의 날짜는 발표 시각이다.** 기준 기간 끝이 아니다. 발표 시각은 기관 발표 일정(IA-16 b)을 쓴다. 없으면 수집 시각을 "수집 시각 기준(상한)"으로 표시한다(IA-16 a).
2. **그 시각에 공개된 값만 쓴다.** 최초 발표값(또는 그 실행에서 받은 값)으로 규칙을 판정한다. 나중 수정치를 앞 날짜로 옮기지 않는다.
3. **매 정기 실행마다 다시 판정한다.** 새로 공개된 자료로 규칙을 평가한다. 같은 입력이면 같은 결과다(멱등).
4. **덧붙이기만 한다.** 새 사건은 사건 기록 끝에 붙인다. 이미 기록된 사건은 지우거나 날짜를 옮기지 않는다.
5. **과거로 채우지 않는다.** 수집하지 못한 과거 발표의 사건을 나중에 실시간 기록에 끼워 넣지 않는다.
6. **수정은 새 사건이다.** 수정 발표로 조건이 풀리거나 새로 성립하면, 그 수정 발표 시각에 "수정 발표로 조건 해제/성립" 사건을 따로 붙인다.
7. **규칙 버전이 바뀌면** 옛 사건은 옛 버전 표시로 남긴다. 새 버전은 채택일부터 판정한다. 실시간 기록을 새 버전으로 소급 재계산하지 않는다.
8. **과거 재구성은 별도 층이다.** 원기관 과거 보도자료·RTDSM으로 만든 과거 사건은 "재구성(replay)" 층에 따로 둔다. 과거 국면 전환 빈도 계산과 Lab 검증에만 쓴다. 실시간 기록과 섞지 않는다. 재구성 층에도 "당시 발표값" 출처를 적고, 수정치로 만든 것은 "수정치 기준"이라고 표시한다.
9. **기록 형태**: 사건 id = (지표 id, 규칙 버전, 기준 기간, 발표 시각)의 해시. 필드: 지표 id, 원기관 계열 id(`source_series_id`), 규칙 버전, 방향, 기준 기간, 발표 시각과 근거 종류, 수집 시각, 원자료 해시, 상태(실시간/재구성). 근거 기록은 rig `Evidence` 형태를 재사용한다(OC G11).
10. **공개 범위**: 공개 사건 기록에는 무료 공식 비가격 계열의 사건만 넣는다. 가격·가격 파생 사건(E45~E49 등)은 기기 RAM에서만 계산하고 저장하지 않는다. 독점 자료 사건은 허가 전에는 만들지 않는다.

---

## 7. 하지 않은 것

- 코드·가드·워크플로·CI 목록 변경.
- CURRENT_HANDOFF·USER_DECISIONS_PENDING·WORKING_RULES·대기열 문서 수정. MEV 결정 기록 반영은 Main이 한다.
- 가격·지수 수준·개인 자료·계정 정보 기록. 예시 값도 넣지 않았다.
- 임계값·확률 확정. [제안] 규칙은 후보일 뿐이다.
- 독점 자료 조회·다운로드. 약관과 공개 설명만 봤다.
