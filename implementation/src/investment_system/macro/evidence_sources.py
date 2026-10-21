"""Macro evidence lines (MEV-1 P1 candidate set of 13): source registry and pure parsers.

Catalog: docs/macro/MACRO_EVIDENCE_LINES_CATALOG_20261018.md §5 (P1 13), §3 (rights), §9 (release time).
MEV-1 approved these 13 only as a candidate set to collect and link. Event thresholds and phase interpretations are NOT
approved: every rule here is copied from the catalog table, carries its rule-source class and stays "v0 · 미검증";
every interpretation is a "해석 후보 · 미승인". MEV-10: nothing here feeds an official judgement, a probability, the
macro gate or any engine input.

Parsers take caller-supplied bytes only (no network, clock, environment or storage). A missing published value is
skipped, never 0. FRED/ALFRED is not used (MEV-3).
"""
from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import html
import io
import json
import math
import re
from types import MappingProxyType
from xml.etree import ElementTree

from .macro_lights_public import CurveUnavailable, parse_treasury_curve

CATALOG = "MACRO_EVIDENCE_LINES_CATALOG_20261018 §5 (P1 13)"
CYCLES = ("economy", "market", "industry")
RULE_SOURCES = ("LITERATURE", "PROPOSAL", "LITERATURE_UP_PROPOSAL_DOWN", "AGENCY_EVENT")
REALTIME_VALIDATION = ("POST_HOC_LITERATURE_ONLY", "UNVALIDATED", "EVENT_FACT_NOT_REQUIRED")
LICENSE_CLASSES = ("FREE_OFFICIAL", "FREE_TERMS_LIMITED", "PROPRIETARY")
PUBLICATION = ("PUBLIC", "HELD_TERMS_UNVERIFIED")
CANDIDATES = ("WARNING", "IMPROVING")
FREQUENCIES = ("W", "M", "Q", "E")  # E = dated agency event record (FOMC)


class SourceUnavailable(ValueError):
    """Fixed reason code only; never provider text."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason if reason in REASONS else "SCHEMA_MISMATCH"


REASONS = (
    "SOURCE_NOT_COLLECTED", "SOURCE_NOT_AVAILABLE", "SOURCE_KEY_NOT_CONFIGURED", "SCHEMA_MISMATCH", "SERIES_NOT_FOUND",
    "MISSING_SOURCE", "CONFLICTING_DUPLICATE", "PROVIDER_ERROR", "UNSAFE_XML", "TERMS_UNVERIFIED",
    "INSUFFICIENT_HISTORY",
)


def _ind(**kw):
    return MappingProxyType(kw)


# Terms rows (§3): BLS/BEA/Fed Board/FiscalData were read in the original; Treasury yield curve reuse wording is still
# "검증 대기" but the same series is already public in macro-screen.json (macro lights v1); DOL's copyright page is HTTP
# 403 from the collection environment (search summary only) -> held from publication; data.bts.gov states the dataset
# license "Public Domain U.S. Government" in its own metadata (read 2026-10-20); the Census Data API needs a key.
INDICATORS = (
    _ind(id="E09", name="금리곡선 역전 (10년−3개월 월평균)", family="C", cycles=("economy",), frequency="M", unit="%p",
         series=("TREASURY:BC_10YEAR-BC_3MONTH:MONTHLY_MEAN",), agency="TREASURY",
         source="U.S. Treasury daily par yield curve (10 Yr, 3 Mo) · 월평균은 이 시스템 계산",
         url="https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve",
         official_statistic=True, license_class="FREE_OFFICIAL", terms_checked_on="2026-10-10",
         terms_note="재무부 금리곡선 재사용 문구 원문 검증 대기. 같은 계열은 경고등 v1으로 이미 공개 중", publication="PUBLIC",
         collection="REUSED_MACRO_V1_CURVE",
         rule=_ind(version="E09.v0", text="월평균 10년−3개월이 음수가 된 첫 달", source_class="LITERATURE",
                   realtime_validation="POST_HOC_LITERATURE_ONLY"),
         edges=MappingProxyType({"down": _ind(label="역전 시작", interpretation="확장→둔화 경고", candidate="WARNING")})),
    _ind(id="E13", name="Sahm 규칙 (실업률)", family="LU", cycles=("economy",), frequency="M", unit="%",
         series=("BLS:LNS14000000",), agency="BLS", source="BLS LNS14000000 · 실업률, SA, 월간",
         url="https://api.bls.gov/publicAPI/v1/timeseries/data/", official_statistic=True, license_class="FREE_OFFICIAL",
         terms_checked_on="2026-10-10", terms_note="BLS public domain(원문 확인). 가공 결과를 BLS 원본이라고 하지 않음",
         publication="PUBLIC", collection="REUSED_MACRO_V0_BLS",
         rule=_ind(version="E13.v0", text="실업률 3개월 평균 − 직전 12개월 중 3개월 평균 최저 ≥ 0.50%p", source_class="LITERATURE",
                   realtime_validation="POST_HOC_LITERATURE_ONLY"),
         edges=MappingProxyType({"down": _ind(label="Sahm 발동", interpretation="확장→수축 전환(침체 초기 확인)", candidate="WARNING")})),
    _ind(id="E14", name="신규 실업수당 청구 (SA, 주간)", family="LU", cycles=("economy",), frequency="W", unit="건",
         series=("DOL:ETA539:INITIAL_CLAIMS_SA",), agency="DOL", source="DOL ETA 539 · 신규 청구, SA, 주간",
         url="https://oui.doleta.gov/unemploy/claims.asp", official_statistic=True, license_class="FREE_OFFICIAL",
         terms_checked_on="2026-10-20", terms_note="DOL 저작권 페이지가 수집 환경에서 HTTP 403. 원문 미확인이라 공개 보류",
         publication="HELD_TERMS_UNVERIFIED", collection="NEW_DOL_WEEKLY_XML",
         rule=_ind(version="E14.v0", text="4주 평균이 26주 평균을 위(아래)로 교차", source_class="PROPOSAL", realtime_validation="UNVALIDATED"),
         edges=MappingProxyType({"up": _ind(label="신규 청구 ↑ (4주 평균 상향 교차)", interpretation="악화", candidate="WARNING"),
                                 "down": _ind(label="신규 청구 ↓ (4주 평균 하향 교차)", interpretation="개선", candidate="IMPROVING")})),
    _ind(id="E16", name="임시직 고용 (CES)", family="LD", cycles=("economy",), frequency="M", unit="천 명",
         series=("BLS:CES6056132001",), agency="BLS", source="BLS CES6056132001 · 임시직 고용, SA, 월간",
         url="https://api.bls.gov/publicAPI/v1/timeseries/data/", official_statistic=True, license_class="FREE_OFFICIAL",
         terms_checked_on="2026-10-10", terms_note="BLS public domain(원문 확인)", publication="PUBLIC", collection="NEW_BLS_V1",
         rule=_ind(version="E16.v0", text="6개월 순변화 부호 전환", source_class="PROPOSAL", realtime_validation="UNVALIDATED"),
         edges=MappingProxyType({"up": _ind(label="임시직 ↑ (6개월 순변화 양전환)", interpretation="개선", candidate="IMPROVING"),
                                 "down": _ind(label="임시직 ↓ (6개월 순변화 음전환)", interpretation="악화", candidate="WARNING")})),
    _ind(id="E17", name="제조업 주당 평균 근로시간", family="LD", cycles=("economy",), frequency="M", unit="시간",
         series=("BLS:CES3000000007",), agency="BLS", source="BLS CES3000000007 · 제조업 생산직 주당 평균 근로시간, SA, 월간",
         url="https://api.bls.gov/publicAPI/v1/timeseries/data/", official_statistic=True, license_class="FREE_OFFICIAL",
         terms_checked_on="2026-10-10", terms_note="BLS public domain(원문 확인)", publication="PUBLIC", collection="NEW_BLS_V1",
         rule=_ind(version="E17.v0", text="3개월 평균이 12개월 전 3개월 평균보다 높아짐(낮아짐)", source_class="PROPOSAL",
                   realtime_validation="UNVALIDATED"),
         edges=MappingProxyType({"up": _ind(label="제조 근로시간 ↑", interpretation="개선", candidate="IMPROVING"),
                                 "down": _ind(label="제조 근로시간 ↓", interpretation="악화", candidate="WARNING")})),
    _ind(id="E21", name="핵심 자본재 주문 (비국방, 항공기 제외)", family="MO", cycles=("economy",), frequency="M", unit="백만 달러",
         series=("CENSUS:M3:NXA:NO:SA",), agency="CENSUS", source="Census M3 · 비국방 자본재(항공기 제외) 신규 주문, SA",
         url="https://www.census.gov/manufacturing/m3/index.html", official_statistic=True, license_class="FREE_OFFICIAL",
         terms_checked_on="2026-10-18", terms_note="Census Data API TOS 원문 확인(출처 표시 문구 필요). API 키 없이는 수집 불가",
         publication="PUBLIC", collection="NEW_CENSUS_EITS_API",
         rule=_ind(version="E21.v0", text="3개월 평균 전년비 부호 전환", source_class="PROPOSAL", realtime_validation="UNVALIDATED"),
         edges=MappingProxyType({"up": _ind(label="자본재 주문 ↑", interpretation="회복→확장", candidate="IMPROVING"),
                                 "down": _ind(label="자본재 주문 ↓", interpretation="둔화", candidate="WARNING")})),
    _ind(id="E22", name="산업생산 (총지수, SA)", family="PO", cycles=("economy",), frequency="M", unit="지수 2017=100",
         series=("FED:G17:IP.B50001.S",), agency="FED_G17", source="Fed G.17 IP.B50001.S · 산업생산 총지수, SA",
         url="https://www.federalreserve.gov/releases/g17/About.htm", official_statistic=True, license_class="FREE_OFFICIAL",
         terms_checked_on="2026-10-18", terms_note="Fed Board public domain(원문 확인). 출처 표시", publication="PUBLIC",
         collection="NEW_FED_DDP_CSV",
         rule=_ind(version="E22.v0", text="전년비 음→양 [문헌], 양→음 [제안]", source_class="LITERATURE_UP_PROPOSAL_DOWN",
                   realtime_validation="POST_HOC_LITERATURE_ONLY"),
         edges=MappingProxyType({"up": _ind(label="산업생산 반등 (전년비 양전환)", interpretation="수축→회복", candidate="IMPROVING"),
                                 "down": _ind(label="산업생산 감소 (전년비 음전환)", interpretation="둔화", candidate="WARNING")})),
    _ind(id="E25", name="실질 GDP (전기비 연율)", family="PO", cycles=("economy",), frequency="Q", unit="%",
         series=("BEA:NIPA:A191RL:Q",), agency="BEA", source="BEA NIPA T10101 line 1 (A191RL) · 실질 GDP 전기비 연율",
         url="https://apps.bea.gov/national/Release/TXT/NipaDataQ.txt", official_statistic=True, license_class="FREE_OFFICIAL",
         terms_checked_on="2026-10-18", terms_note="BEA public domain(원문 확인)", publication="PUBLIC",
         collection="REUSED_MACRO_V0_BEA",
         rule=_ind(version="E25.v0", text="전기비 연율 음→양 [문헌], 양→음 [제안]", source_class="LITERATURE_UP_PROPOSAL_DOWN",
                   realtime_validation="POST_HOC_LITERATURE_ONLY"),
         edges=MappingProxyType({"up": _ind(label="GDP 반등 (음→양)", interpretation="수축→회복", candidate="IMPROVING"),
                                 "down": _ind(label="GDP 감소 (양→음)", interpretation="수축", candidate="WARNING")})),
    _ind(id="E26", name="건축허가 (SA 연율)", family="HO", cycles=("economy",), frequency="M", unit="천 호",
         series=("CENSUS:RESCONST:APERMITS:TOTAL:SA",), agency="CENSUS", source="Census NRC · 건축허가 전체, SA 연율",
         url="https://www.census.gov/construction/nrc/index.html", official_statistic=True, license_class="FREE_OFFICIAL",
         terms_checked_on="2026-10-18", terms_note="Census Data API TOS 원문 확인(출처 표시 문구 필요). API 키 없이는 수집 불가",
         publication="PUBLIC", collection="NEW_CENSUS_EITS_API",
         rule=_ind(version="E26.v0", text="3개월 평균의 6개월 변화 부호 전환", source_class="PROPOSAL", realtime_validation="UNVALIDATED"),
         edges=MappingProxyType({"up": _ind(label="건축허가 ↑", interpretation="회복", candidate="IMPROVING"),
                                 "down": _ind(label="건축허가 ↓", interpretation="둔화", candidate="WARNING")})),
    _ind(id="E36", name="대출기준 순강화 비율 (SLOOS, C&I 대·중기업)", family="BK", cycles=("economy",), frequency="Q", unit="%",
         series=("FED:SLOOS:SUBLPDCILS_N.Q",), agency="FED_SLOOS", source="Fed SLOOS SUBLPDCILS_N.Q · C&I 대출기준 순강화 비율(대·중기업)",
         url="https://www.federalreserve.gov/data/sloos.htm", official_statistic=True, license_class="FREE_OFFICIAL",
         terms_checked_on="2026-10-18", terms_note="Fed Board public domain(원문 확인). 출처 표시", publication="PUBLIC",
         collection="NEW_FED_DDP_CSV",
         rule=_ind(version="E36.v0", text="순강화 비율 0 교차", source_class="PROPOSAL", realtime_validation="UNVALIDATED"),
         edges=MappingProxyType({"up": _ind(label="대출기준 강화 (0 상향)", interpretation="긴축", candidate="WARNING"),
                                 "down": _ind(label="대출기준 완화 (0 하향)", interpretation="긴축 종료", candidate="IMPROVING")})),
    _ind(id="E39", name="근원 물가 추세 (근원 CPI · 근원 PCE)", family="IN", cycles=("economy",), frequency="M", unit="지수",
         series=("BLS:CUSR0000SA0L1E", "BEA:NIPA:DPCCRG:M"), agency="BLS+BEA",
         source="BLS CUSR0000SA0L1E · 근원 CPI SA / BEA DPCCRG · 근원 PCE 물가지수",
         url="https://apps.bea.gov/national/Release/TXT/NipaDataM.txt", official_statistic=True, license_class="FREE_OFFICIAL",
         terms_checked_on="2026-10-18", terms_note="BLS·BEA public domain(원문 확인)", publication="PUBLIC", collection="NEW_BLS_V1+NEW_BEA_FLAT_M",
         rule=_ind(version="E39.v0", text="3개월 연율 > 12개월 상승률 3개월 연속(가속), 반대(둔화)", source_class="PROPOSAL",
                   realtime_validation="UNVALIDATED"),
         edges=MappingProxyType({"up": _ind(label="근원물가 가속 (3개월 연속)", interpretation="확장 후기", candidate=None),
                                 "down": _ind(label="근원물가 둔화 (3개월 연속)", interpretation="미정", candidate=None)})),
    _ind(id="E40", name="FOMC 목표범위 변경 (사건)", family="PL", cycles=("economy", "market"), frequency="E", unit="% (상단)",
         series=("FED:FOMC:TARGET_RANGE",), agency="FED_FOMC", source="Fed Board 'Open market operations' 목표 금리(범위) 변경표",
         url="https://www.federalreserve.gov/monetarypolicy/openmarket.htm", official_statistic=True, license_class="FREE_OFFICIAL",
         terms_checked_on="2026-10-18", terms_note="Fed Board public domain(원문 확인). 날짜는 변경표의 날짜(효력일)", publication="PUBLIC",
         collection="NEW_FED_OPENMARKET_HTML",
         rule=_ind(version="E40.v0", text="사건: 목표범위가 바뀐 FOMC 결정. 해석 규칙은 별도(미승인)", source_class="AGENCY_EVENT",
                   realtime_validation="EVENT_FACT_NOT_REQUIRED"),
         edges=MappingProxyType({"up": _ind(label="금리 인상(FOMC)", interpretation="해석 후보: 첫 인상 = 후기 (반례 주의)", candidate=None),
                                 "down": _ind(label="금리 인하(FOMC)", interpretation="해석 후보: 첫 인하 = 둔화·수축 (반례 주의)", candidate=None)})),
    _ind(id="E01", name="화물 운송서비스지수 (BTS Freight TSI)", family="T", cycles=("economy", "industry"), frequency="M", unit="지수 2000=100",
         series=("BTS:TSI:FREIGHT",), agency="BTS", source="BTS Transportation Services Index · Freight, SA",
         url="https://data.bts.gov/resource/bw6n-ddqk.json", official_statistic=True, license_class="FREE_OFFICIAL",
         terms_checked_on="2026-10-20",
         terms_note="data.bts.gov 데이터셋 라이선스 표기 'Public Domain U.S. Government'. 트럭 부분은 ATA 입력(제3자 권리 별도 확인 필요)",
         publication="PUBLIC", collection="NEW_BTS_SOCRATA_JSON",
         rule=_ind(version="E01.v0", text="방향 전환이 3개월 이상 유지되면 선", source_class="LITERATURE",
                   realtime_validation="POST_HOC_LITERATURE_ONLY"),
         edges=MappingProxyType({"up": _ind(label="화물 운송 ↑ (상승 전환 3개월 유지)", interpretation="회복", candidate="IMPROVING"),
                                 "down": _ind(label="화물 운송 ↓ (하락 전환 3개월 유지)", interpretation="둔화", candidate="WARNING")})),
)
INDICATOR_IDS = tuple(i["id"] for i in INDICATORS)
BY_ID = MappingProxyType({i["id"]: i for i in INDICATORS})
SERIES_INDICATOR = MappingProxyType({s: i["id"] for i in INDICATORS for s in i["series"]})
SERIES_FREQUENCY = MappingProxyType({s: i["frequency"] for i in INDICATORS for s in i["series"]})
SERIES_IDS = tuple(SERIES_INDICATOR)

# Fixed request facts (observed on federalreserve.gov 2026-10-20). A package without the target column yields
# SERIES_NOT_FOUND, never another series.
DDP_PACKAGES = MappingProxyType({
    "FED:G17:IP.B50001.S": MappingProxyType({"rel": "G17", "series": "809009461b1cba2fd5b4cf5557d9d663", "column": "IP.B50001.S"}),
    "FED:SLOOS:SUBLPDCILS_N.Q": MappingProxyType({"rel": "SLOOS", "series": "e64f07187815f0e7ed89237d8cb91eeb", "column": "SUBLPDCILS_N.Q"}),
})
BLS_EVIDENCE_IDS = ("CES6056132001", "CES3000000007", "CUSR0000SA0L1E")
CENSUS_QUERIES = MappingProxyType({
    "CENSUS:M3:NXA:NO:SA": MappingProxyType({"program": "m3", "category": "NXA", "data_type": "NO"}),
    "CENSUS:RESCONST:APERMITS:TOTAL:SA": MappingProxyType({"program": "resconst", "category": "APERMITS", "data_type": "TOTAL"}),
})

_NUM = re.compile(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", re.ASCII)
_MISSING = ("", "-", ".", "NA", "N/A", "(NA)", "ND", "--", "---", "...", "(D)", "(S)", "(X)", "(Z)")


def number(raw) -> float | None:
    """Published number -> float; a published 'missing' marker -> None (never 0); anything else -> SCHEMA_MISMATCH."""
    if raw is None:
        return None
    text = str(raw).replace(" ", " ").strip()
    if text in _MISSING:
        return None
    if _NUM.fullmatch(text) is None:
        raise SourceUnavailable("SCHEMA_MISMATCH")
    try:
        value = float(Decimal(text.replace(",", "")))
    except InvalidOperation:
        raise SourceUnavailable("SCHEMA_MISMATCH") from None
    if not math.isfinite(value):
        raise SourceUnavailable("SCHEMA_MISMATCH")
    return value


def _put(rows: dict, period: str, value: float | None) -> None:
    if value is None:
        return
    if period in rows and rows[period] != value:
        raise SourceUnavailable("CONFLICTING_DUPLICATE")
    rows[period] = value


def _done(rows: dict) -> dict:
    if not rows:
        raise SourceUnavailable("MISSING_SOURCE")
    return dict(sorted(rows.items()))


def _safe_xml(body: bytes):
    probe = body.replace(b"\x00", b"").upper()
    if b"<!DOCTYPE" in probe or b"<!ENTITY" in probe:
        raise SourceUnavailable("UNSAFE_XML")
    try:
        return ElementTree.fromstring(body)
    except (ElementTree.ParseError, ValueError, LookupError):
        raise SourceUnavailable("SCHEMA_MISMATCH") from None


def _json(body: bytes):
    try:
        return json.loads(body.decode("utf-8"), parse_constant=lambda _c: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise SourceUnavailable("SCHEMA_MISMATCH") from None


def parse_bls_v1(body: bytes, series_ids: tuple[str, ...]) -> dict[str, dict]:
    """{"BLS:<id>": {YYYY-MM: value}} from one BLS public API v1 JSON body; M13 (annual) skipped, "-" missing.
    A requested series absent from the body maps to a SourceUnavailable reason (string) instead of rows."""
    obj = _json(body)
    if type(obj) is not dict:
        raise SourceUnavailable("SCHEMA_MISMATCH")
    if obj.get("status") != "REQUEST_SUCCEEDED":
        raise SourceUnavailable("PROVIDER_ERROR")
    results = obj.get("Results")
    if type(results) is not dict or type(results.get("series")) is not list:
        raise SourceUnavailable("SCHEMA_MISMATCH")
    out = {}
    for series in results["series"]:
        if type(series) is not dict or series.get("seriesID") not in series_ids or type(series.get("data")) is not list:
            raise SourceUnavailable("SCHEMA_MISMATCH")
        rows = {}
        for row in series["data"]:
            if type(row) is not dict:
                raise SourceUnavailable("SCHEMA_MISMATCH")
            year, period = row.get("year"), row.get("period")
            if type(year) is not str or not re.fullmatch(r"\d{4}", year) or type(period) is not str or not re.fullmatch(r"M(0[1-9]|1[0-3])", period):
                raise SourceUnavailable("SCHEMA_MISMATCH")
            if period == "M13":
                continue
            _put(rows, year + "-" + period[1:], number(row.get("value")))
        out["BLS:" + series["seriesID"]] = _done(rows) if rows else "MISSING_SOURCE"
    for sid in series_ids:
        out.setdefault("BLS:" + sid, "SERIES_NOT_FOUND")
    return out


def parse_bea_flat(body: bytes, series_code: str, frequency: str) -> dict:
    """One series from BEA NipaDataQ.txt / NipaDataM.txt (`%SeriesCode,Period,Value`)."""
    try:
        content = body.decode("utf-8-sig")
    except UnicodeError:
        raise SourceUnavailable("SCHEMA_MISMATCH") from None
    lines = content.splitlines()
    if not lines or [h.strip().strip("%").strip().casefold() for h in next(csv.reader([lines[0]]))] != ["seriescode", "period", "value"]:
        raise SourceUnavailable("SCHEMA_MISMATCH")
    pattern = r"(\d{4})Q([1-4])" if frequency == "Q" else r"(\d{4})M(0[1-9]|1[0-2])"
    rows, prefix = {}, series_code + ","
    for line in lines[1:]:
        if not line.lstrip('"').startswith(prefix):
            continue
        row = next(csv.reader([line]))
        if len(row) != 3 or row[0].strip() != series_code:
            raise SourceUnavailable("SCHEMA_MISMATCH")
        match = re.fullmatch(pattern, row[1].strip())
        if match is None:
            raise SourceUnavailable("SCHEMA_MISMATCH")
        period = match.group(1) + ("Q" + match.group(2) if frequency == "Q" else "-" + match.group(2))
        _put(rows, period, number(row[2]))
    if not rows:
        raise SourceUnavailable("SERIES_NOT_FOUND")
    return _done(rows)


def treasury_monthly_spread(bodies: list[bytes], *, before_month: str) -> dict:
    """{YYYY-MM: mean over the month's days of (10 Yr − 3 Mo)} for completed months (< before_month) only. A day without
    both tenors is skipped. The mean is this system's calculation, rounded to 4 decimals."""
    days = {}
    for body in bodies:
        try:
            rows = parse_treasury_curve(body)
        except CurveUnavailable as error:
            raise SourceUnavailable("CONFLICTING_DUPLICATE" if error.reason == "CONFLICTING_DUPLICATE" else "SCHEMA_MISMATCH") from None
        for day, value in rows.items():
            if day in days and days[day] != value:
                raise SourceUnavailable("CONFLICTING_DUPLICATE")
            days[day] = value
    months = {}
    for day, (three, ten) in days.items():
        if three is None or ten is None or day[:7] >= before_month:
            continue
        months.setdefault(day[:7], []).append(ten - three)
    return _done({m: round(sum(v) / len(v), 4) for m, v in months.items()})


def parse_dol_weekly(body: bytes) -> dict:
    """{week ended YYYY-MM-DD: SA initial claims} from the DOL ETA 539 national weekly claims XML."""
    root = _safe_xml(body)
    if root.tag != "r539cyNational":
        raise SourceUnavailable("SCHEMA_MISMATCH")
    rows = {}
    for week in root.findall("week"):
        ended = (week.findtext("weekEnded") or "").strip()
        match = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", ended)
        claims = week.find("InitialClaims")
        if match is None or claims is None:
            raise SourceUnavailable("SCHEMA_MISMATCH")
        try:
            day = date(int(match.group(3)), int(match.group(1)), int(match.group(2))).isoformat()
        except ValueError:
            raise SourceUnavailable("SCHEMA_MISMATCH") from None
        _put(rows, day, number(claims.findtext("SA")))
    return _done(rows)


def parse_ddp_csv(body: bytes, column: str) -> dict:
    """One column (by its official identifier on the 'Time Period' header row) of a Fed DDP CSV (seriescolumn layout)."""
    try:
        rows = list(csv.reader(io.StringIO(body.decode("utf-8-sig"))))
    except (UnicodeError, csv.Error):
        raise SourceUnavailable("SCHEMA_MISMATCH") from None
    header = next((i for i, r in enumerate(rows[:12]) if r and r[0].strip() == "Time Period"), None)
    if header is None or not rows[0] or rows[0][0].strip() != "Series Description":
        raise SourceUnavailable("SCHEMA_MISMATCH")
    names = [c.strip() for c in rows[header]]
    if names.count(column) != 1:
        raise SourceUnavailable("SERIES_NOT_FOUND")
    index, out = names.index(column), {}
    for row in rows[header + 1:]:
        if not row:
            continue
        if len(row) != len(names):
            raise SourceUnavailable("SCHEMA_MISMATCH")
        period = row[0].strip()
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])|\d{4}Q[1-4]", period):
            raise SourceUnavailable("SCHEMA_MISMATCH")
        _put(out, period, number(row[index]))
    return _done(out)


_MONTHS = {m: i for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July", "August",
                                         "September", "October", "November", "December"), 1)}


def parse_ddp_release_date(page: bytes) -> str | None:
    """'last released <Weekday>, <Month> <d>, <yyyy>' on a DDP Choose page -> YYYY-MM-DD (date only), else None."""
    text = html.unescape(page.decode("utf-8", "replace"))
    match = re.search(r"last released\s+[A-Za-z]+,\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})", text)
    if match is None or match.group(1) not in _MONTHS:
        return None
    try:
        return date(int(match.group(3)), _MONTHS[match.group(1)], int(match.group(2))).isoformat()
    except ValueError:
        return None


def _cells(fragment: str) -> list[str]:
    return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", c))).strip()
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", fragment, re.S | re.I)]


def _bp(cell: str) -> int:
    text = cell.replace("*", "").strip()
    if text in ("", "...", "0"):
        return 0
    match = re.fullmatch(r"(\d+)(?:-(\d+))?", text)
    if match is None:
        raise SourceUnavailable("SCHEMA_MISMATCH")
    return int(match.group(2) or match.group(1))


def parse_fomc_openmarket(page: bytes) -> list[dict]:
    """Changes of the FOMC target federal funds rate or range from the Board's 'Open market operations' page:
    [{date, direction up|down, bp, level, upper}] in date order (the table date, i.e. as the Board lists it)."""
    text = page.decode("utf-8", "replace")
    out, seen = [], set()
    for match in re.finditer(r"<h4>\s*(\d{4})\s*</h4>(.*?)</table>", text, re.S | re.I):
        year = int(match.group(1))
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", match.group(2), re.S | re.I):
            cells = _cells(row)
            if not cells or cells[0] == "Date":
                continue
            if len(cells) != 4:
                raise SourceUnavailable("SCHEMA_MISMATCH")
            day = re.fullmatch(r"([A-Z][a-z]+)\s+(\d{1,2})\*?", cells[0].replace("*", "").strip())
            level = re.fullmatch(r"(\d+(?:\.\d+)?)(?:-(\d+(?:\.\d+)?))?", cells[3].strip())
            if day is None or day.group(1) not in _MONTHS or level is None:
                raise SourceUnavailable("SCHEMA_MISMATCH")
            up, down = _bp(cells[1]), _bp(cells[2])
            if (up > 0) == (down > 0):
                raise SourceUnavailable("SCHEMA_MISMATCH")
            try:
                when = date(year, _MONTHS[day.group(1)], int(day.group(2))).isoformat()
            except ValueError:
                raise SourceUnavailable("SCHEMA_MISMATCH") from None
            if when in seen:
                raise SourceUnavailable("CONFLICTING_DUPLICATE")
            seen.add(when)
            out.append({"date": when, "direction": "up" if up else "down", "bp": up or down,
                        "level": cells[3].strip(), "upper": float(level.group(2) or level.group(1))})
    if not out:
        raise SourceUnavailable("MISSING_SOURCE")
    return sorted(out, key=lambda r: r["date"])


def parse_bts_tsi(body: bytes) -> dict:
    """{YYYY-MM: Freight TSI} from the data.bts.gov (Socrata) TSI dataset rows (obs_date, tsi_freight)."""
    obj = _json(body)
    if type(obj) is not list:
        raise SourceUnavailable("SCHEMA_MISMATCH")
    rows = {}
    for row in obj:
        if type(row) is not dict or type(row.get("obs_date")) is not str:
            raise SourceUnavailable("SCHEMA_MISMATCH")
        match = re.fullmatch(r"(\d{4}-(0[1-9]|1[0-2]))-01T00:00:00(?:\.000)?", row["obs_date"])
        if match is None:
            raise SourceUnavailable("SCHEMA_MISMATCH")
        _put(rows, match.group(1), number(row.get("tsi_freight")))
    return _done(rows)


def parse_census_eits(body: bytes, *, category: str, data_type: str) -> dict:
    """{YYYY-MM: value} of the seasonally adjusted rows of a Census EITS time-series API body (array of arrays with a
    header row). Format from the Census API documentation; not verified from this environment (a key is required)."""
    obj = _json(body)
    if type(obj) is not list or not obj or type(obj[0]) is not list:
        raise SourceUnavailable("SCHEMA_MISMATCH")
    header = obj[0]
    need = ("cell_value", "data_type_code", "category_code", "seasonally_adj", "time")
    if any(header.count(k) != 1 for k in need):
        raise SourceUnavailable("SCHEMA_MISMATCH")
    at = {k: header.index(k) for k in need}
    rows = {}
    for row in obj[1:]:
        if type(row) is not list or len(row) != len(header):
            raise SourceUnavailable("SCHEMA_MISMATCH")
        if row[at["category_code"]] != category or row[at["data_type_code"]] != data_type or row[at["seasonally_adj"]] != "yes":
            continue
        period = row[at["time"]]
        if type(period) is not str or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", period):
            raise SourceUnavailable("SCHEMA_MISMATCH")
        _put(rows, period, number(row[at["cell_value"]]))
    if not rows:
        raise SourceUnavailable("SERIES_NOT_FOUND")
    return _done(rows)


def http_time(value: str | None) -> datetime | None:
    """RFC 7231 HTTP-date (Last-Modified) -> aware UTC datetime, else None."""
    if type(value) is not str:
        return None
    from email.utils import parsedate_to_datetime
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    return parsed if parsed is not None and parsed.tzinfo is not None else None
