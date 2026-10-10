# 8축 매핑 초안 — 사용자 확인 전 비활성

GSQ-011 원기관 원칙을 유지한다. #104/#128 파서와 #141 공개 raw 화면은 준비됐지만 데이터 형식 지원과 경제적 의미 채택은 별개다. 아래는 **PROPOSED_PENDING_APPROVAL**, 새 임계값·가중치·6상태·Model 채택은 없다. FRED/ALFRED fallback 금지.

| 축 | 공식 입력/후보 | 제안하는 표시·변환 | 미확정/제외 |
| --- | --- | --- | --- |
| Growth | BEA NIPA T10106 line1 quarterly 실질GDP수준; T10101 line1 quarterly published annualized percent change | 화면은GDP수준·기존단위 그대로. 기존engine growth 후보는 **T10101 line1 발표된전기비연율% ÷100**. 수준에서추가연율공식 만들지 않음. | 성장연율 또는전년동기비의선택확인. 현재국면연결없음. advance/second/third/revision과취득당시vintage 구분. |
| Inflation | BLS CUUR0000SA0 NSA / CUSR0000SA0 SA CPI-U all items | 엔진inflation 후보는 **CUUR0000SA0 해당월/전년동월−1**. SA는별도raw표시. | NSA YoY채택확인.12개월전자료가없으면NA. CPI지수나월간변화를기존연간fraction으로직접넣지않음. |
| Monetary Policy | Treasury daily_treasury_yield_curve BC_10YEAR,percent |10년Treasury수익률raw표시 | policy target 아닌 yield context. engine 새변수나FOMC기준금리대체 없음. |
| Labor | BLS CES0000000001 SA thousands / LNS14000000 SA percent | 비농업고용수준·실업률raw분리표시 | 고용변화·정규화·국면합성은미정. 두 series를단일level/score로평균하지않음. |
| Liquidity | Fed H.4.1 통합자산total assets, **수요일 잔액level**후보 | 금액·단위배율·주간원자료 | exact SERIES_NAME/dataset/familyattrs 승인·검증필요. 주간평균과별개;순유동성합성 없음. |
| Credit | Fed H.8 **all commercial banks의bank credit SA level**후보 | aggregate은행신용금액raw | exactSERIES_NAME/group/item/단위필요. HYspread아님. SLOOS별도보완자료는후속,한점수로결합안함. |
| Fiscal | Treasury MTS table1 총receipts/outlays·deficit/surplus의당월flow 후보 |원표총계/행/basis분리raw표시 | exact항목·관측월/발표일필드·부호확인필요. FYTD/당월·소계중복없음. GDP대비계산/재정score미정. |
| FX | Fed H.10 broad trade-weighted **nominal dollar index**후보 |RAM통계지수후보,미승인 | exactSERIES_NAME/기준연도/단위·가격성격보관경계확인.현물환산·QGV가격환산·공개artifact연결 금지. #141은FX를공개에서제외. |

Fed/Treasury 후속후보의 exact selector는 원기관metadata와대조하여사용자가선택할대상이다. 의미후보만제시하고확인되지않은series ID나family필터를창작하지않는다. 공급binding용파서는이미#128에있으므로확인된selector를인자로받을수있다. full-feed/ZIPwrapper 추출·원본계보는검증되지않았으며자동live수집기가있는것처럼표시하지않는다.

## 기존 MacroEngine과의 연결 제안

위Growth annualizedfraction과Inflation NSA YoYfraction을 **모두**확인된동일cutoff의공급capture에서만만든후기존엔진에전달하는것을제안한다. 서로다른관측주기(분기/월)·기간을명시하고latestavailable값의결합을표시한다. 둘중하나가결측/충돌/미확인/아직미공개면국면NA. 기본0이나NORMAL로대체하지않는다. 서로다른빈티지의역사값을최신응답으로소급재현하지않는다.

기존v0.1.1의판정순서·임계는그대로: inflation>0.08→EMERGENCY/INFLATION_SHOCK; elseinflation>0.05andgrowth<0→WARNING/STAGFLATION_RISK; elsegrowth>0.03andinflation<0.03→NORMAL/EXPANSION; 그외NORMAL/NEUTRAL. **위threshold는현재코드의기존값설명이며새제안아님.** #128 evaluate_synthetic_macro_inputs는두fraction을모두요구하는합성연결만검증했다. 실제mapping은사용자확인후별도구현한다.

## 8×6 상태·PIT 경계

Level은raw자료증거만 RAW_EVIDENCE이며상태점수가아니다. Direction/Momentum/Surprise/Stress/Confidence는규칙·비교창·시장기대출처·결측처리미확정으로NOT_AVAILABLE다. CPIYoY/GDP연율후보채택이이를동시에승인하는것은아니다. Treasury금리·Labor·후속4축을기존엔진의추가변수로쓰지않는다.

빈티지/수정·공표/취득시각은원래계약유지. 현재응답의과거관측치는CURRENT_REVISED_HISTORY이고capturecutoff는OBSERVED_CAPTURE_UPPER_BOUND만증명한다. 월말/정기발표일·HTTP수정시간으로최초가용시각을추정하지않는다. 미래누적forward검증은v2착수시사용자가정할시작일이전에는시작하지않는다. Holdout은UNCONFIRMED·v2근거제외.

정부원기관권리·공식발표주기·archive근거는[1차명세](PHASE1_FOUR_AXES_IMPLEMENTATION_SPEC.md)·[나머지4축조사](REMAINING_FOUR_AXES_PRIMARY_SOURCES.md)·[공급파서계약](GOVERNMENT_SCREEN_AND_REMAINING_INPUTS.md)을따른다. 실제대량자료수집·가격/환율저장·공개producer규칙변경 없음.
