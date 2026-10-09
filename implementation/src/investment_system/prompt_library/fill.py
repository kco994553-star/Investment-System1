"""E4 Variable Fill / E5 Preview / E6 Copy-Export (Track E).

Copy-first: the output is a vendor-neutral plain-text prompt the user pastes into any AI. Nothing is sent anywhere
and no engine is called. The canonical body is never mutated (records are frozen; every fill returns a new string).

Variable rules (D2 — derived from the Frozen text, recorded in the Track E Decision Log):
  - every declared variable is REQUIRED and must be a non-empty value, except `qgv_snapshot_summary`, the only
    variable the Frozen body explicitly allows to be empty ("요약이 비어 있어도 ...") -> blank becomes `NOT_PROVIDED`;
  - `as_of` / `prior_cutoff`: ISO date (YYYY-MM-DD) or ISO datetime with offset; `as_of` may not lie after `now`
    (an information cutoff cannot be in the future); `prior_cutoff` must be strictly before `as_of`;
  - `input_mode`: SYSTEM_CONTEXT | STANDALONE (TECH/MACRO prompts);
  - `candidate_count`: positive integer;
  - values may not contain `{{` / `}}`; unknown variable names are rejected (typo -> fail-closed, not ignored).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from typing import Mapping

from .catalog import INPUT_MODES, SYSTEM_INPUT_VARIABLES, Catalog, PromptRecord

KST = timezone(timedelta(hours=9))
OPTIONAL_VARIABLES = frozenset({"qgv_snapshot_summary"})
NOT_PROVIDED = "NOT_PROVIDED"
DATE_VARIABLES = frozenset({"as_of", "prior_cutoff"})
_PLACEHOLDER = re.compile(r"\{\{([a-z_]+)\}\}")

VARIABLE_HINTS = {
    "as_of": "정보 cutoff (PIT). YYYY-MM-DD",
    "prior_cutoff": "이전 분석 cutoff. YYYY-MM-DD, as_of보다 이전",
    "input_mode": "SYSTEM_CONTEXT (기존 Snapshot 소비, 재계산 금지) | STANDALONE (PIT 데이터 직접 제공, 없으면 INSUFFICIENT_DATA)",
    "candidate_count": "최대 후보 수 (양의 정수)",
    "qgv_snapshot_summary": "기존 QGV 요약 (선택; 비우면 NOT_PROVIDED)",
}


# Presentation guidance only. Examples remain placeholders; they are never input values.
# Ownership, required/kind rules and validation are defined independently below/in catalog.py.
def _variable_guide(label_ko, label_en, description_ko, description_en,
                    placeholder_ko, placeholder_en, source_ko, source_en):
    return {
        "label": {"ko-KR": label_ko, "en-US": label_en},
        "description": {"ko-KR": description_ko, "en-US": description_en},
        "placeholder": {"ko-KR": placeholder_ko, "en-US": placeholder_en},
        "source": {"ko-KR": source_ko, "en-US": source_en},
    }


VARIABLE_GUIDES = {
    "as_of": _variable_guide(
        "정보 기준일", "Information cutoff",
        "이 시점까지 공개·이용 가능했던 정보만 사용합니다. 미래 날짜는 허용되지 않습니다.",
        "Use only information publicly available by this cutoff. Future cutoffs are not allowed.",
        "예: 2026-10-09", "Example: 2026-10-09",
        "이번 분석에 사용할 정보 기준일을 직접 정합니다.", "Choose the information cutoff for this analysis."),
    "prior_cutoff": _variable_guide(
        "이전 분석 기준일", "Previous analysis cutoff",
        "이전 분석 이후 새로 공개된 정보를 비교할 시작 기준일입니다. 이번 정보 기준일보다 앞서야 합니다.",
        "The earlier analysis cutoff used to identify newly available information. It must precede the current cutoff.",
        "예: 2026-07-01", "Example: 2026-07-01",
        "비교할 이전 분석·Snapshot의 기준일에서 확인합니다.", "Read the cutoff from the earlier analysis or snapshot."),
    "ticker": _variable_guide(
        "종목 코드", "Ticker",
        "이번에 분석할 종목의 코드를 입력합니다. 같은 코드의 다른 거래소 종목과 구분합니다.",
        "Enter the ticker being analyzed, distinguishing listings on different exchanges when needed.",
        "예: NVDA", "Example: NVDA",
        "기업의 공식 상장 정보 또는 확인한 종목 식별 정보에서 가져옵니다.", "Use verified listing information or the company's official listing details."),
    "company": _variable_guide(
        "분석할 회사", "Company to analyze",
        "이번 분석의 대상 회사 이름입니다. 종목 코드와 같은 회사를 가리켜야 합니다.",
        "The company being analyzed. Its name and ticker must identify the same company.",
        "예: NVIDIA", "Example: NVIDIA",
        "회사 공시·공식 홈페이지 또는 확인한 기업 정보에서 가져옵니다.", "Use company filings, its official website or verified company information."),
    "seed_company": _variable_guide(
        "탐색 출발 회사", "Starting company",
        "경쟁 생태계·공급업체·고객사에서 다른 후보를 찾기 위한 출발 회사입니다. 새 후보 자체와 구분합니다.",
        "The starting company for discovering candidates in its competitive ecosystem, suppliers or customers.",
        "예: NVIDIA", "Example: NVIDIA",
        "조사를 시작할 회사의 확인된 이름을 직접 고릅니다.", "Choose the verified company name from which the research starts."),
    "seed_ticker": _variable_guide(
        "출발 회사 종목 코드", "Starting company ticker",
        "탐색 출발 회사를 식별하는 종목 코드입니다. 분석 대상 종목 코드와 역할이 다릅니다.",
        "Identifies the starting company for candidate discovery, a different role from the analysis target ticker.",
        "예: NVDA", "Example: NVDA",
        "출발 회사의 공식 상장 정보에서 확인합니다.", "Verify it against the starting company's official listing information."),
    "universe": _variable_guide(
        "후보 탐색 범위", "Candidate search universe",
        "어떤 종목 집합에서 조사 후보를 찾을지 정합니다. 국가·시장·선정 기준·기준일을 명확히 씁니다.",
        "Define the companies to search, stating the country, market, selection rule and relevant date.",
        "예: 미국 시총 상위 500개 종목 · 기준일 2026-10-09", "Example: the 500 largest US companies by market cap, as of 2026-10-09",
        "직접 정한 조사 범위 또는 이미 확인한 Universe 목록에서 가져옵니다.", "Use your research scope or an already verified universe list."),
    "candidate_count": _variable_guide(
        "최대 후보 수", "Maximum candidate count",
        "출력할 Research Candidate 수의 상한입니다. 양의 정수로 입력하며 부족한 후보를 억지로 채우지 않습니다.",
        "A positive-integer upper limit for research candidates. It does not require inventing candidates to meet the limit.",
        "예: 10", "Example: 10",
        "한 번에 검토할 수 있는 최대 후보 수를 직접 정합니다.", "Choose the maximum number of candidates you can review."),
    "market": _variable_guide(
        "거시 분석 시장", "Market for macro analysis",
        "거시 변화와 전달 경로를 조사할 국가·시장 범위입니다.",
        "The country or market whose macro conditions and transmission paths will be researched.",
        "예: 미국", "Example: United States",
        "이번 거시 질문의 대상 시장을 직접 정합니다.", "Choose the market relevant to the macro question."),
    "horizon": _variable_guide(
        "거시 판단 기간", "Macro analysis horizon",
        "거시 시나리오·영향을 검토할 기간입니다. 과거 가격 자료의 기간인 period와 구분합니다.",
        "The horizon for macro scenarios and impacts, distinct from the historical price-data period.",
        "예: 향후 3~12개월", "Example: the next 3–12 months",
        "거시 질문과 사용할 기존 Macro 자료의 평가 기간을 확인합니다.", "Choose a horizon consistent with the macro question and existing macro evidence."),
    "period": _variable_guide(
        "가격·차트 분석 기간", "Price and chart analysis period",
        "기술적 분석에 제공할 가격·거래량 자료의 기간입니다. 정보 기준일까지의 실제 자료와 맞춥니다.",
        "The period covered by price and volume data supplied for technical analysis, ending no later than the cutoff.",
        "예: 최근 1년 · 2025-10-09~2026-10-09", "Example: the last year, 2025-10-09 to 2026-10-09",
        "보유한 차트·OHLCV 자료 또는 기존 TechnicalSnapshot의 기간에서 확인합니다.", "Read it from supplied OHLCV data or the existing technical snapshot."),
    "industry": _variable_guide(
        "조사할 산업", "Industry to research",
        "후보 탐색이나 거시 영향 분석의 대상 산업입니다. 전략 테마와 산업 분류를 혼동하지 않습니다.",
        "The industry for candidate discovery or macro transmission research. An investment theme is a separate concept.",
        "예: 반도체 장비", "Example: semiconductor equipment",
        "확인한 산업 분류 또는 직접 정한 조사 범위에서 가져옵니다.", "Use a verified industry classification or your defined research scope."),
    "theme": _variable_guide(
        "조사할 테마", "Theme to research",
        "직접 수혜뿐 아니라 2·3차 수혜 경로를 조사할 투자 테마입니다. 산업 분류를 바꾸지 않습니다.",
        "The investment theme whose direct and indirect beneficiary paths will be researched; it does not redefine industry classification.",
        "예: AI 데이터센터 전력", "Example: power for AI data centers",
        "탐색하려는 테마를 직접 정하고 근거와 범위를 함께 씁니다.", "Define the theme to explore, including its scope and supporting evidence."),
    "industry_or_theme": _variable_guide(
        "공급망 조사 산업·테마", "Industry or theme for value-chain research",
        "원재료부터 최종 수요까지 Value Chain을 살펴볼 산업 또는 테마입니다.",
        "The industry or theme whose value chain will be examined from raw materials through end demand.",
        "예: AI 반도체 공급망", "Example: AI semiconductor value chain",
        "공급망 탐색의 대상 산업·테마를 직접 정합니다.", "Choose the industry or theme for value-chain discovery."),
    "benchmark_or_peers": _variable_guide(
        "비교 지수·경쟁사", "Benchmark or peers",
        "상대강도·가격 반응을 비교할 지수나 기업과 근거 자료입니다. 기간·통화·기업행사 기준을 맞춥니다.",
        "The benchmark or peers and evidence used to compare relative strength or price reactions, with aligned periods, currencies and corporate-action bases.",
        "예: S&P 500 / AMD / AVGO · 비교 기간과 자료 출처도 추가", "Example: S&P 500 / AMD / AVGO; also add the comparison period and data sources",
        "확인한 지수·Peer 목록과 같은 기준의 실제 가격 자료에서 가져옵니다.", "Use verified benchmarks or peers with actual price data on a comparable basis."),
    "earnings_period": _variable_guide(
        "실적 검토 기간", "Earnings period",
        "기대치·전년·전분기와 비교할 실적의 회계연도·분기입니다. 회사의 회계 기간을 확인합니다.",
        "The fiscal year or quarter of the earnings results to compare with expectations and prior periods.",
        "예: FY2026 Q3", "Example: FY2026 Q3",
        "해당 회사의 실적 발표 자료·공시에서 확인합니다.", "Read it from the company's earnings release or filing."),
    "macro_driver": _variable_guide(
        "후보 탐색의 거시 변화", "Macro driver for candidate discovery",
        "직접·2차 수혜 후보를 찾을 거시 변화입니다. 기존 거시 판단 요약과 구분해 변화 자체를 씁니다.",
        "The macro change whose direct and indirect beneficiaries will be researched, distinct from the existing macro snapshot summary.",
        "예: 금리 인하에 따른 직접·2차 수혜", "Example: direct and indirect beneficiaries of interest rate cuts",
        "확인한 거시 Evidence 또는 검토할 가설에서 가져오고 사실·가정을 구분합니다.", "Use macro evidence or a hypothesis to examine, distinguishing observed facts from assumptions."),
    "policy_change": _variable_guide(
        "검토할 정책 변화", "Policy change to examine",
        "행동 변화·대체·공급 반응 같은 2차 효과를 조사할 정책입니다. 발표·시행 시점과 근거를 씁니다.",
        "The policy change whose indirect effects will be examined, including its announcement or effective date and sources.",
        "예: 반도체 수출 규제 강화 · 발표/시행일과 출처 추가", "Example: tighter semiconductor export restrictions; add announcement or effective date and source",
        "정책 당국의 원문·공식 발표 등 확인한 자료에서 가져옵니다.", "Use verified policy documents or official announcements."),
    "rate_path_assumption": _variable_guide(
        "시장 금리경로 가정", "Market rate-path assumption",
        "시장에 내재한 금리경로 중 검증할 가정입니다. 기준 시점·기간·근거와 이를 틀리게 할 조건을 함께 씁니다.",
        "The market-implied rate path to challenge, including its date, horizon, evidence and conditions that could invalidate it.",
        "예: 향후 금리 인하를 예상하는 시장 가정 · 기준일과 근거 추가", "Example: a market assumption of future rate cuts; add the cutoff and evidence",
        "확인한 시장 내재 자료·기존 분석에서 가져옵니다. 미래 금리경로를 사실처럼 만들지 않습니다.", "Use verified market-implied data or an existing analysis; do not invent a future path as fact."),
    "scenario_assumptions": _variable_guide(
        "거시 시나리오 가정", "Macro scenario assumptions",
        "연착륙·침체 등 반박할 기존 시나리오의 전제입니다. 근거 없는 확률을 새로 넣지 않습니다.",
        "The existing assumptions behind scenarios such as a soft landing or recession. Do not add unsupported probabilities.",
        "예: 연착륙 가정: 성장 둔화·물가 완화 · 전제와 반대 근거 추가", "Example: soft-landing assumption with slower growth and easing inflation; add assumptions and contrary evidence",
        "검토할 기존 Macro 시나리오에서 복사하고 관측 사실과 가정을 구분합니다.", "Copy the existing macro scenario being challenged, distinguishing observations from assumptions."),
    "reverse_dcf_assumptions": _variable_guide(
        "역 DCF 검토 가정", "Reverse DCF assumptions to examine",
        "기존 역 DCF가 요구하는 성장·마진·재투자·할인율 등의 가정을 현실 근거와 비교합니다. 새 계산 결과를 만드는 필드가 아닙니다.",
        "The existing reverse DCF assumptions for growth, margin, reinvestment and discount rate to compare with real evidence, not a request to create a new valuation result.",
        "예: 기존 성장·마진·재투자·할인율 가정과 기준·출처", "Example: existing growth, margin, reinvestment and discount-rate assumptions with their basis and source",
        "기존 가치평가·역 DCF 분석에서 확인한 가정을 가져옵니다.", "Use the assumptions recorded in an existing valuation or reverse DCF analysis."),
    "customer_evidence_scope": _variable_guide(
        "고객 근거 조사 범위", "Customer evidence research scope",
        "수요·만족도·이탈을 조사할 고객군·제품·기간·자료 유형의 범위입니다. 고객 반응이 확인됐다는 결과가 아닙니다.",
        "The customers, products, period and source types to examine for demand, satisfaction or churn evidence, not a claim that customer reactions have been verified.",
        "예: 클라우드 3사 실적 발언·개발자 커뮤니티 · 제품과 조사 기간 추가", "Example: earnings commentary from three cloud providers and developer communities; add product and research period",
        "조사할 고객 범위와 자료 유형을 직접 정합니다.", "Define the customer research scope and source types yourself."),
    "news_event_evidence": _variable_guide(
        "시간순 뉴스·이벤트 근거", "Dated news and event evidence",
        "가격 움직임과 비교할 실적·정책 등 사건의 실제 근거입니다. 공개 시점·이용 가능 시점·원문을 함께 씁니다.",
        "Actual earnings, policy or other event evidence to compare with price moves, including release time, availability time and original sources.",
        "가상 예: 2026-08-27 실적 발표; 2026-09-10 수출 규제 발표 · 원문과 공개 시각 추가", "Illustrative events: earnings release on 2026-08-27; export restrictions announcement on 2026-09-10; add original sources and release times",
        "확인한 공시·공식 발표·뉴스 원문에서 가져오고 사실과 해석을 구분합니다.", "Use verified filings, official announcements or original news, separating facts from interpretations."),
    "options_positioning_data": _variable_guide(
        "옵션·포지셔닝 자료", "Options and positioning data",
        "IV·Skew·Open Interest 등 실제 보유 자료와 출처를 씁니다. 필수 입력이며 자료가 없으면 그 사실을 명시하고 결론을 만들지 않습니다.",
        "Supply actual IV, skew, open-interest or related data with sources. This field is required; if unavailable, state that explicitly and draw no unsupported conclusion.",
        "예: NOT_AVAILABLE · 옵션 자료 없음", "Example: NOT_AVAILABLE — no options data",
        "보유한 확인된 옵션 자료에서 가져옵니다. Dealer/Flow 추정은 사실과 구분합니다.", "Use verified options data you actually have, distinguishing dealer or flow estimates from facts."),
    "qgv_snapshot_summary": _variable_guide(
        "기존 QGV 요약", "Existing QGV snapshot summary",
        "기존 QGV 판단·근거를 재계산 없이 읽기 위한 선택 입력입니다. 비우면 NOT_PROVIDED이며 독자 점수를 만들지 않습니다.",
        "An optional existing QGV assessment and evidence to consume without rescoring. Blank becomes NOT_PROVIDED; no independent QGV score is invented.",
        "예: 기존 QGV 판단·근거·기준 시점 또는 빈칸", "Example: existing QGV assessment, evidence and cutoff, or leave blank",
        "종목 화면의 QGV 카드에 실제 판단·근거가 있을 때만 복사합니다. 없으면 비워 NOT_PROVIDED로 표시할 수 있습니다.", "Copy the QGV card on the Companies screen only when an actual assessment and evidence exist. If unavailable, leave this optional field blank for NOT_PROVIDED."),
    "existing_system_candidates": _variable_guide(
        "기존 시스템 후보 목록", "Existing system candidates",
        "기존 QGV 리더보드 후보와 비교하여 중복·빠진 후보를 조사합니다. 새 공식 후보 목록이나 점수를 입력하는 필드가 아닙니다.",
        "Existing QGV leaderboard candidates used to identify overlaps or gaps, not a new official candidate list or a rescoring request.",
        "예: 기존 후보·판단 근거·기준일 또는 자료 미제공 표시", "Example: existing candidates, evidence and cutoff, or an explicit unavailable statement",
        "리더보드 화면에 실제 QGV_LEADERBOARD 결과가 있을 때만 복사합니다. 없으면 미제공을 명시하고 확인된 빈 목록과 구분합니다.", "Copy actual QGV_LEADERBOARD results from the Leaderboard screen only when available. Otherwise state that data is unavailable, distinguishing it from a verified empty list."),
    "technical_input": _variable_guide(
        "기술 분석 입력 자료", "Technical analysis input",
        "SYSTEM_CONTEXT는 기존 기술 Snapshot·계산 결과를 재계산 없이 사용합니다. STANDALONE은 실제 PIT OHLCV·조정 기준·시간대·기업행사·출처가 필요하며 없으면 INSUFFICIENT_DATA입니다.",
        "SYSTEM_CONTEXT consumes existing technical snapshots without recalculation. STANDALONE requires actual PIT OHLCV, adjustment basis, timezone, corporate actions and sources; missing data means INSUFFICIENT_DATA.",
        "예: 기존 기술 Snapshot 또는 기준·시점·출처를 포함한 실제 OHLCV", "Example: existing technical snapshot or actual OHLCV with its basis, timing and sources",
        "기술 화면에 실제 TECHNICAL 결과가 있을 때만 복사하거나 STANDALONE용 실제 시점별 원자료를 제공합니다. 없으면 미제공을 명시합니다. 준비 화면은 자동 데이터 연결이 아닙니다.", "Copy actual TECHNICAL results from the Technical screen only when available, or supply real point-in-time data for STANDALONE. Otherwise state that data is unavailable. A preparation screen does not imply connected data."),
    "technical_screen_summary": _variable_guide(
        "기존 기술 스크리닝 요약", "Existing technical screening summary",
        "여러 종목의 기존 기술 상태 변화에서 새 Research Candidate를 조사할 입력입니다. 개별 종목 차트 기간과 구분합니다.",
        "Existing technical screening results across companies, used to research candidate leads rather than recompute individual charts.",
        "예: 기존 스크리닝 종목·상태 변화·기준일·근거", "Example: screened companies, observed state changes, cutoff and evidence",
        "기술 화면에 실제 여러 종목의 스크리닝 결과·저장된 요약이 있을 때만 복사합니다. 없으면 미제공을 명시합니다.", "Copy actual multi-company screening results or a saved summary from the Technical screen only when available. Otherwise state that data is unavailable."),
    "macro_input": _variable_guide(
        "거시 분석 입력 자료", "Macro analysis input",
        "SYSTEM_CONTEXT는 기존 거시 Snapshot·State·Regime을 덮어쓰지 않습니다. STANDALONE은 시장·기간에 맞는 실제 PIT 발표·빈티지·시장 내재 자료와 출처가 필요하며 없으면 INSUFFICIENT_DATA입니다.",
        "SYSTEM_CONTEXT does not overwrite existing macro snapshots, states or regimes. STANDALONE requires actual PIT releases, vintages, market-implied data and sources for the chosen market and horizon; missing data means INSUFFICIENT_DATA.",
        "예: 기존 거시 Snapshot 또는 시점·빈티지·출처가 있는 실제 자료", "Example: existing macro snapshot or actual data with release timing, vintage and sources",
        "매크로 화면에 실제 MACRO 결과가 있을 때만 복사하거나 STANDALONE용 확인된 원자료를 제공합니다. 없으면 미제공을 명시합니다. 8축 준비 표시가 데이터 제공 완료를 뜻하지 않습니다.", "Copy actual MACRO results from the Macro screen only when available, or provide verified source data for STANDALONE. Otherwise state that data is unavailable. An eight-axis preparation display does not mean data is available."),
    "macro_snapshot_summary": _variable_guide(
        "기존 거시 판단 요약", "Existing macro snapshot summary",
        "거시 변화의 직접·2차 수혜 후보를 조사할 기존 Macro 판단·근거 요약입니다. 새 국면 판단을 만들지 않습니다.",
        "An existing macro assessment and evidence summary used to research direct and indirect beneficiaries without inventing a new regime assessment.",
        "예: 기존 거시 판단·변화·근거·기준일", "Example: existing macro assessment, changes, evidence and cutoff",
        "매크로 화면에 실제 MACRO Snapshot·저장된 거시 판단이 있을 때만 복사합니다. 없으면 미제공을 명시합니다.", "Copy an actual MACRO snapshot or saved assessment from the Macro screen only when available. Otherwise state that data is unavailable."),
    "system_summary": _variable_guide(
        "기존 통합 판단 요약", "Existing integrated assessment",
        "기존 QGV·기술·거시 판단의 충돌·누락·새 근거를 검토합니다. 원본 결과를 다시 계산하거나 새 통합점수를 만들지 않습니다.",
        "The existing QGV, technical and macro assessment used to investigate conflicts, gaps or new evidence without recalculation or a new combined score.",
        "예: 기존 각 시스템 판단·근거·기준 시점", "Example: existing assessments, evidence and cutoffs for each system",
        "오늘 화면에 실제 기존 통합 판단이 있을 때만 복사합니다. 없으면 미제공을 명시하며 개별 결과를 새 통합 판단으로 합성하지 않습니다.", "Copy an actual existing integrated assessment from the Today screen only when available. Otherwise state that data is unavailable; do not synthesize a new integrated assessment from individual results."),
    "system_coverage_summary": _variable_guide(
        "기존 분석 범위·누락 요약", "Existing coverage and gaps summary",
        "시스템이 다룬 종목·항목과 빠진 범위를 비교하여 놓친 Research Candidate를 찾습니다. 완료율을 새로 계산하지 않습니다.",
        "Existing company and field coverage, including gaps, used to find overlooked research candidates without inventing a completion metric.",
        "예: 확인된 분석 범위·누락 항목·기준일", "Example: verified coverage, missing fields and cutoff",
        "오늘·검증 화면에 기존 통합 판단의 실제 분석 범위·누락 기록이 있을 때만 복사합니다. 없으면 미제공을 명시하며 개별 QGV 범위를 통합 기록으로 바꾸지 않습니다.", "Copy actual coverage and gap records for the existing integrated assessment from the Today or Validation screens only when available. Otherwise state that data is unavailable; do not turn individual QGV coverage into an integrated record."),
    "snapshot_refs": _variable_guide(
        "판단 원본 참조", "Source snapshot references",
        "통합 판단이 참조한 기존 Snapshot의 ID·기준일·출처 등입니다. 검증되지 않은 ID나 연결을 만들지 않습니다.",
        "References to the actual snapshots behind the integrated assessment, including IDs, cutoffs and sources; never invent an ID or linkage.",
        "예: 기존 Snapshot ID·기준일·출처·버전", "Example: existing snapshot ID, cutoff, source and version",
        "기존 통합 판단이 실제 참조한 각 화면 데이터의 Snapshot ID·기준일·출처를 확인해 복사합니다. 없으면 미제공을 명시하며 임의 ID나 통합 참조를 만들지 않습니다.", "Copy verified snapshot IDs, cutoffs and sources for the screen data actually referenced by the existing integrated assessment. Otherwise state that references are unavailable; do not invent IDs or integrated links."),
    "input_mode": _variable_guide(
        "자료 입력 방식", "Input mode",
        "SYSTEM_CONTEXT는 기존 시스템 결과를 받아 재계산하지 않습니다. STANDALONE도 질문만으로 충분하지 않으며 기술·거시 실제 PIT 원자료가 없으면 INSUFFICIENT_DATA로 종료합니다.",
        "SYSTEM_CONTEXT consumes existing system results without recalculation. STANDALONE still needs actual technical or macro PIT data; a question alone is insufficient and missing data ends in INSUFFICIENT_DATA.",
        "SYSTEM_CONTEXT 또는 STANDALONE을 선택", "Choose SYSTEM_CONTEXT or STANDALONE",
        "사용자가 직접 선택합니다. 선택만으로 Snapshot이나 원자료를 자동으로 가져오지 않습니다.", "Select it yourself; choosing a mode does not automatically fetch snapshots or source data."),
}

# Preserve the five existing hints verbatim and cover every other Frozen variable.
VARIABLE_HINTS = {**{name: guide["description"]["ko-KR"] for name, guide in VARIABLE_GUIDES.items()},
                  **VARIABLE_HINTS}


class VariableFillError(ValueError):
    def __init__(self, prompt_code: str, missing=(), invalid=(), unknown=()):
        self.missing, self.invalid, self.unknown = tuple(missing), tuple(invalid), tuple(unknown)
        parts = []
        if self.missing:
            parts.append(f"missing required {list(self.missing)}")
        if self.invalid:
            parts.append(f"invalid {list(self.invalid)}")
        if self.unknown:
            parts.append(f"unknown variables {list(self.unknown)}")
        super().__init__(f"{prompt_code}: " + "; ".join(parts))


@dataclass(frozen=True)
class VariableSpec:
    name: str
    required: bool
    kind: str  # DATE | INPUT_MODE | POSITIVE_INT | TEXT
    system_input_owner: str | None
    hint: str


def variable_specs(prompt: PromptRecord) -> tuple[VariableSpec, ...]:
    out = []
    for v in prompt.variables:
        kind = ("DATE" if v in DATE_VARIABLES else "INPUT_MODE" if v == "input_mode"
                else "POSITIVE_INT" if v == "candidate_count" else "TEXT")
        out.append(VariableSpec(v, v not in OPTIONAL_VARIABLES, kind, SYSTEM_INPUT_VARIABLES.get(v),
                                VARIABLE_HINTS.get(v, "")))
    return tuple(out)


def _parse_instant(value: str) -> datetime | None:
    s = value.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            d = date.fromisoformat(s)
            return datetime(d.year, d.month, d.day, tzinfo=KST)
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else None  # naive datetimes are ambiguous -> rejected


def check_values(prompt: PromptRecord, values: Mapping[str, object], now: datetime | None = None,
                 partial: bool = False) -> tuple[dict[str, str], list[str], list[str], list[str]]:
    """(normalized values, missing, invalid, unknown). partial=True reports missing without raising."""
    declared = set(prompt.variables)
    unknown = sorted(k for k in values if k not in declared)
    norm, missing, invalid = {}, [], []
    for spec in variable_specs(prompt):
        raw = values.get(spec.name)
        text = "" if raw is None else str(raw).strip()
        if not text:
            if spec.required:
                missing.append(spec.name)
            else:
                norm[spec.name] = NOT_PROVIDED
            continue
        if "{{" in text or "}}" in text:
            invalid.append(f"{spec.name}: placeholder braces are not allowed in values")
            continue
        if spec.kind == "DATE" and _parse_instant(text) is None:
            invalid.append(f"{spec.name}: not an ISO date (YYYY-MM-DD) or offset-aware ISO datetime")
            continue
        if spec.kind == "INPUT_MODE" and text not in INPUT_MODES:
            invalid.append(f"input_mode: {text!r} not in {INPUT_MODES}")
            continue
        if spec.kind == "POSITIVE_INT" and not (text.isdigit() and int(text) > 0):
            invalid.append(f"{spec.name}: not a positive integer")
            continue
        norm[spec.name] = text
    as_of = _parse_instant(norm["as_of"]) if "as_of" in norm else None
    if as_of is not None:
        ref = now or datetime.now(timezone.utc)
        if as_of > ref:
            invalid.append("as_of: information cutoff lies in the future")
        prior = _parse_instant(norm["prior_cutoff"]) if "prior_cutoff" in norm else None
        if prior is not None and not prior < as_of:
            invalid.append("prior_cutoff: must be strictly before as_of")
    return norm, missing, invalid, unknown


def fill(prompt: PromptRecord, values: Mapping[str, object], now: datetime | None = None) -> str:
    """Filled plain-text prompt; raises VariableFillError on any missing/invalid/unknown variable (fail-closed)."""
    norm, missing, invalid, unknown = check_values(prompt, values, now)
    if missing or invalid or unknown:
        raise VariableFillError(prompt.prompt_code, missing, invalid, unknown)
    text = _PLACEHOLDER.sub(lambda m: norm[m.group(1)], prompt.body)
    if "{{" in text or "}}" in text:  # defensive: a declared variable left unsubstituted
        raise VariableFillError(prompt.prompt_code, invalid=["unsubstituted placeholder after fill"])
    return text


@dataclass(frozen=True)
class Preview:
    prompt_id: str
    prompt_code: str
    title: str
    content_version: str
    text: str
    ready_to_copy: bool
    missing: tuple[str, ...]
    invalid: tuple[str, ...]
    unknown: tuple[str, ...]
    variables: tuple[VariableSpec, ...]


def preview(prompt: PromptRecord, values: Mapping[str, object], now: datetime | None = None) -> Preview:
    """Substitution result for whatever is filled so far; unfilled / invalid variables stay as `{{name}}` and the
    preview is not ready to copy until every check passes."""
    norm, missing, invalid, unknown = check_values(prompt, values, now)
    bad = {s.split(":", 1)[0] for s in invalid}
    text = _PLACEHOLDER.sub(lambda m: norm[m.group(1)] if m.group(1) in norm and m.group(1) not in bad
                            else m.group(0), prompt.body)
    return Preview(prompt.prompt_id, prompt.prompt_code, prompt.title, prompt.content_version, text,
                   not (missing or invalid or unknown), tuple(missing), tuple(invalid), tuple(unknown),
                   variable_specs(prompt))


def copy_text(prompt: PromptRecord, values: Mapping[str, object], now: datetime | None = None) -> str:
    """What the Copy button puts on the clipboard: exactly the filled canonical body, nothing vendor-specific."""
    return fill(prompt, values, now)


def export(catalog: Catalog, prompt_ids, values: Mapping[str, object], fmt: str = "text",
           now: datetime | None = None) -> str:
    """Fill several prompts (e.g. a Bundle, in its order) with one shared value set.

    Each prompt receives only the variables it declares; a variable required by any prompt must be supplied.
    fmt="text": prompts separated by a plain divider line; fmt="json": list of {prompt_id, prompt_code,
    content_version, catalog_sha256, as_of, text}. Fail-closed on the first prompt that cannot be filled."""
    if fmt not in ("text", "json"):
        raise ValueError(f"unknown export format {fmt!r}")
    ids = list(prompt_ids)
    all_vars = {v for pid in ids for v in catalog.prompts[pid].variables}
    unknown = sorted(k for k in values if k not in all_vars)
    if unknown:
        raise VariableFillError("EXPORT", unknown=unknown)
    items = []
    for pid in ids:
        p = catalog.prompts[pid]
        own = {k: v for k, v in values.items() if k in p.variables}
        items.append({"prompt_id": p.prompt_id, "prompt_code": p.prompt_code, "content_version": p.content_version,
                      "catalog_sha256": catalog.sha256, "as_of": str(values.get("as_of", "")).strip(),
                      "text": fill(p, own, now)})
    if fmt == "json":
        return json.dumps(items, ensure_ascii=False, indent=1)
    n = len(items)
    return "\n\n".join(f"----- [{i}/{n}] {it['prompt_code']} -----\n{it['text']}" for i, it in enumerate(items, 1))


def bundle_variables(catalog: Catalog, bundle_number: int) -> tuple[VariableSpec, ...]:
    """Union of the variables a Bundle needs, first-appearance order, required if any member requires it."""
    b = next(b for b in catalog.bundles if b.number == bundle_number)
    seen: dict[str, VariableSpec] = {}
    for pid in b.prompt_ids:
        for s in variable_specs(catalog.prompts[pid]):
            if s.name not in seen or (s.required and not seen[s.name].required):
                seen[s.name] = s
    return tuple(seen.values())
