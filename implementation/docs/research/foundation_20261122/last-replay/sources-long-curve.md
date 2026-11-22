# 미국 10년−3개월 금리차를 1959년까지 확장한 근거

뉴욕 연은의 AMEC 연구표에는 1959년 1월부터 2026년 10월까지 금리차가 814개월 연속 수록돼 있다. 이 파일 하나로 1962년부터의 월별 역전 여부를 같은 기준으로 판정할 수 있다. 2026년 11월 22일 뉴욕 연은이 직접 게시한 연구 첨부표를 한 번 열람하고 보관본으로 검산했다. [Federal Reserve Bank of New York, *The Yield Curve as a Leading Indicator*](https://www.newyorkfed.org/research/capital_markets/ycfaq.html) · [원본 XLS](https://www.newyorkfed.org/medialibrary/media/research/capital_markets/allmonth.xls)

| 확인 항목 | 결과 |
|---|---|
| 발행판 | `allmonth.xls`, 139,264바이트. SHA-256 `2fe39a1698a8c58e49180fafaf4bd3fb4afaf8a1ac587408a7760d7a9ba6035f`. 발행자가 같은 주소에서 갱신하므로 이 해시로 재생 대상을 식별한다. |
| 실제 입력 | `rec_prob` 시트 A열 날짜, B열 10년, D열 채권등가 기준 3개월, E열 `Spread`. 시트에는 C열 3개월 할인율도 있다. 814개 유효 월 모두 `E = B − D`를 절대오차 10⁻¹⁰%p 이내에서 검산했다. 이후 12개월에는 모형 추정확률만 있고 해당 월 금리는 없어 제외했다. |
| 금리 정의 | 장기는 연준 H.15의 10년 고정만기 국채 수익률이다. 단기는 유통시장의 3개월 T-bill 할인율을 채권등가수익률로 환산한다. Estrella·Trubin(2006) 3쪽 각주 4의 공식은 할인율을 % 단위 `d`로 둘 때 `365 × d / (360 − 91 × d / 100)`이다. 연구표에 게시된 D·E 값을 사용했고 `spread < 0`을 역전으로 판정했다. [저자 원문](https://www.newyorkfed.org/medialibrary/media/research/current_issues/ci12-5.pdf) |
| 시점·단위 | 역전은 월평균 금리차의 부호, 단위는 %p. 뉴욕 연은 월보는 다음 달 첫 두 주 내 갱신된다. 시장 월말 관측을 사용한 역사 연구이며 당시 공표된 XLS 판본을 매월 복원한 결과는 아니다. 뉴욕 연은 모형 확률의 목표는 정확히 12개월 뒤 침체 상태다. 이번 검증은 게시된 금리차로 6·12·18·24개월 안에 **새 침체가 시작했는지** 따로 계산한다. 첨부표의 모형확률과 NBER 열은 검증 입력에서 제외했다. [발표 일정·목표](https://www.newyorkfed.org/research/capital_markets/ycfaq.html) |

기존 미 재무부 표본은 3개월 **고정만기** 수익률을 사용한다. 10년과 3개월이 함께 있는 거래일이 월 10일 이상일 때 일별 차이를 단순평균했다. 뉴욕 연은 계열은 단기의 호가·상품 정의가 달라 독립적으로 전기간 재생했다. 공통 구간 1990년 1월~2024년 12월의 420개월 중 419개월에서 역전 판정이 일치했다. 재무부 계열이 역전인 달은 48개, 뉴욕 연은 계열은 47개였다. 2019년 5월만 재무부 기준에서 역전이었다. 뉴욕 연은에서 재무부 금리차를 뺀 평균은 +0.73bp, 절대차 중앙값은 0.50bp, 최대 절대차는 12.70bp였다. 미세한 차이도 첫 역전 시점과 연속 역전 구간 수를 바꿀 수 있다. [미 재무부 금리 산출 설명](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/interest-rates-frequently-asked-questions) · [뉴욕 연은 연구](https://www.newyorkfed.org/research/current_issues/ci12-5.html)

뉴욕 연은은 개인 또는 업무 목적의 다운로드·저장·파생물 작성을 약관과 개별 콘텐츠 조건 하에 허용한다. 출처·저작권 표시, 변경 주체 식별, 제3자 권리 조건이 적용된다. 공개 문서에는 연구 출처와 자체 계산한 비교 집계를 제공한다. 본문의 역전 빈도 및 기간 비교는 작성자 계산이다. © 2026 Federal Reserve Bank of New York. [Federal Reserve Bank of New York, *The Yield Curve as a Leading Indicator*](https://www.newyorkfed.org/research/capital_markets/ycfaq.html) · [Terms of Use](https://www.newyorkfed.org/privacy/termsofuse.html)
