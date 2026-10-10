"""Private supplied-input M3 computations. No I/O, storage or public producer.

Identity/unit evidence is supplied by an audited caller; hashes bind inputs but
do not prove source rights or economic unit equivalence. Current Sheet prices
remain indicative references, never daily closes or historical PIT evidence.
"""
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
import re
from typing import Literal, Mapping

REASON_CODES = frozenset((
    "UNIVERSE_SCHEMA_MISMATCH", "MANIFEST_MISMATCH", "SOURCE_TOO_LARGE", "ROW_LIMIT_REACHED",
    "IDENTITY_UNCONFIRMED", "CURRENCY_SCOPE_NOT_SUPPORTED", "MIXED_SYNTHETIC_INPUT",
    "GOOGLE_MCAP_MISSING", "GOOGLE_MCAP_INVALID", "PRICE_NOT_AVAILABLE", "INVALID_INPUT",
    "INVALID_TIMESTAMP", "INVALID_TIME_ORDER", "AVAILABLE_AFTER_AS_OF", "BASIS_UNCONFIRMED",
    "CIK_MISMATCH", "ACCESSION_UNCONFIRMED", "SHARES_NOT_AVAILABLE", "MULTI_CLASS_AMBIGUOUS",
    "NONFINITE_MCAP", "CONFIG_CONFIRMATION_REQUIRED", "DUPLICATE_ISSUER", "VALIDATION_INCOMPLETE",
))


@dataclass(frozen=True)
class ListingSeed:
    listing_id: str = field(repr=False)
    company_id: str = field(repr=False)
    issuer_id: str = field(repr=False)
    security_id: str = field(repr=False)
    symbol: str = field(repr=False)
    mic: str
    currency: str
    timezone: str
    provider_symbol: str = field(repr=False)
    cik: str | None = field(repr=False)
    valid_from: date
    valid_to: date | None
    identity_evidence_ref: str = field(repr=False)
    identity_sha256: str = field(repr=False)
    synthetic: bool


@dataclass(frozen=True)
class UniverseReceipt:
    source: Literal["GOOGLEFINANCE_PRIVATE_UNIVERSE"]
    acquired_at: datetime
    content_sha256: str = field(repr=False)
    job_id: str = field(repr=False)
    session_epoch: int
    synthetic: bool


@dataclass(frozen=True)
class UniverseRow:
    row_index: int
    code: str | None = field(repr=False)
    listing: ListingSeed | None = field(repr=False)
    google_mcap: float | None = field(repr=False)
    sheet_price: float | None = field(repr=False)
    reason_codes: tuple[str, ...]
    receipt: UniverseReceipt = field(repr=False)


@dataclass(frozen=True)
class UniverseParseResult:
    state: Literal["INPUT_RESEARCH", "NOT_AVAILABLE"]
    receipt: UniverseReceipt | None = field(repr=False)
    rows: tuple[UniverseRow, ...] = field(repr=False)
    row_count: int
    reason_codes: tuple[str, ...]
    row_limit_reached: bool
    synthetic: bool


@dataclass(frozen=True)
class ShareBasisReceipt:
    listing_id: str = field(repr=False)
    company_id: str = field(repr=False)
    security_id: str = field(repr=False)
    basis_status: Literal["SINGLE_CLASS_CONFIRMED", "CA_UNIT_APPROVED", "UNKNOWN"]
    source_evidence_ref: str = field(repr=False)
    source_sha256: str = field(repr=False)
    available_at: datetime
    share_unit: str
    price_basis: Literal["RAW_CLOSE", "GOOGLEFINANCE_CURRENT"]
    currency: str
    synthetic: bool


@dataclass(frozen=True)
class SecReceipt:
    cik: str = field(repr=False)
    companyfacts_body: bytes = field(repr=False)
    submissions_body: bytes = field(repr=False)
    acquired_at: datetime
    facts_sha256: str = field(repr=False)
    submissions_sha256: str = field(repr=False)
    synthetic: bool


@dataclass(frozen=True)
class SharesInput:
    state: Literal["INPUT_RESEARCH", "NOT_AVAILABLE"]
    listing_id: str | None = field(repr=False)
    company_id: str | None = field(repr=False)
    security_id: str | None = field(repr=False)
    shares: float | None = field(repr=False)
    shares_available_at: datetime | None
    measurement_date: date | None
    accn: str | None = field(repr=False)
    concept: str | None
    basis_sha256: str | None = field(repr=False)
    reason_codes: tuple[str, ...]
    synthetic: bool
    historical_first_publication: bool = False
    facts_sha256: str | None = field(default=None, repr=False)
    submissions_sha256: str | None = field(default=None, repr=False)


@dataclass(frozen=True)
class PriceInput:
    state: Literal["INPUT_RESEARCH", "NOT_AVAILABLE"]
    listing_id: str | None = field(repr=False)
    company_id: str | None = field(repr=False)
    security_id: str | None = field(repr=False)
    price: float | None = field(repr=False)
    available_at: datetime | None
    observed_at: datetime | None
    as_of: datetime
    content_sha256: str | None = field(repr=False)
    row_index: int | None
    basis_sha256: str | None = field(repr=False)
    reason_codes: tuple[str, ...]
    synthetic: bool
    price_kind: Literal["GOOGLEFINANCE_CURRENT"] = "GOOGLEFINANCE_CURRENT"
    trade_time: None = None
    exact_eod: bool = False


@dataclass(frozen=True)
class QualityConfig:
    relative_tolerance: float
    confirmed: bool


@dataclass(frozen=True)
class SelectionConfig:
    n: int
    confirmed: bool


@dataclass(frozen=True)
class CapCheck:
    row_index: int
    listing: ListingSeed | None = field(repr=False)
    state: Literal["VERIFIED", "NOT_AVAILABLE"]
    recomputed_cap: float | None = field(repr=False)
    google_mcap: float | None = field(repr=False)
    relative_difference: float | None = field(repr=False)
    effective_cap: float | None = field(repr=False)
    quality: str
    quality_label: str
    reason_codes: tuple[str, ...]
    content_sha256: str = field(repr=False)
    synthetic: bool
    shares_input: SharesInput | None = field(default=None, repr=False)
    price_input: PriceInput | None = field(default=None, repr=False)


@dataclass(frozen=True)
class UniverseSelection:
    state: Literal["PERSONAL_REFERENCE", "NOT_AVAILABLE"]
    selection_status: Literal["COMPLETE", "PARTIAL", "UNCONFIRMED"]
    content_sha256: str | None = field(repr=False)
    requested_n: int | None
    selected_n: int
    row_count: int
    verified_count: int
    missing_count: int
    selected_listing_ids: tuple[str, ...] = field(repr=False)
    selected: tuple[CapCheck, ...] = field(repr=False)
    missing: tuple[tuple[int, tuple[str, ...]], ...] = field(repr=False)
    reason_codes: tuple[str, ...]
    synthetic: bool
    source: Literal["PRIVATE_UNIVERSE_VERIFIED_TOP_N"] = "PRIVATE_UNIVERSE_VERIFIED_TOP_N"
    scope: Literal["VERIFIED_UNIVERSE_ROWS"] = "VERIFIED_UNIVERSE_ROWS"
    official: bool = False
    candidate_pool_complete: bool = False
    full_configured_rank_status: Literal["UNKNOWN"] = "UNKNOWN"


def _text(value):
    return type(value) is str and bool(value.strip())


def _hash(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}",value) is not None


def _codes(value):
    return type(value) is tuple and all(type(v) is str and v in REASON_CODES for v in value)


def _aware(value):
    if not isinstance(value,datetime):
        return False
    try:
        return value.tzinfo is not None and value.utcoffset() is not None and isinstance(_utc(value),datetime)
    except (OverflowError,ValueError,TypeError):
        return False


def _utc(value):
    return value.astimezone(timezone.utc)


def _positive(value):
    if type(value) not in (int,float):
        return False
    try:
        return math.isfinite(value) and value>0
    except (OverflowError,ValueError):
        return False


def _sheet_number(value):
    if type(value) is str:
        if not re.fullmatch(r"\+?[0-9]+(?:\.[0-9]+)?",value):
            return None
        try:
            value=float(value)
        except (OverflowError,ValueError):
            return None
    return float(value) if _positive(value) else None


def _receipt_valid(receipt):
    return (isinstance(receipt,UniverseReceipt) and receipt.source=="GOOGLEFINANCE_PRIVATE_UNIVERSE"
            and _aware(receipt.acquired_at) and _hash(receipt.content_sha256)
            and type(receipt.job_id) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,128}",receipt.job_id) is not None
            and type(receipt.session_epoch) is int and receipt.session_epoch>=0 and type(receipt.synthetic) is bool)


def _row_valid(row):
    return (isinstance(row,UniverseRow) and type(row.row_index) is int and row.row_index>=0
            and (row.code is None or _text(row.code)) and _receipt_valid(row.receipt)
            and (row.listing is None or _identity_error(row.listing,row.receipt.acquired_at,row.receipt.synthetic) is None) and _codes(row.reason_codes)
            and (row.google_mcap is None or _positive(row.google_mcap))
            and (row.sheet_price is None or _positive(row.sheet_price)))


def _identity_error(seed,at,synthetic):
    if not isinstance(seed,ListingSeed) or any(not _text(getattr(seed,k)) for k in ("listing_id","company_id","issuer_id","security_id","symbol","mic","currency","timezone","provider_symbol","identity_evidence_ref")) or not _hash(seed.identity_sha256):
        return "IDENTITY_UNCONFIRMED"
    if not re.fullmatch(r"[a-z0-9_-]+",seed.company_id) or type(seed.cik) is not str or not re.fullmatch(r"[0-9]{10}",seed.cik) or seed.cik=="0000000000":
        return "IDENTITY_UNCONFIRMED"
    if type(seed.valid_from) is not date or (seed.valid_to is not None and (type(seed.valid_to) is not date or seed.valid_to<=seed.valid_from)) or not seed.valid_from<=_utc(at).date() or (seed.valid_to is not None and _utc(at).date()>=seed.valid_to):
        return "IDENTITY_UNCONFIRMED"
    if type(seed.synthetic) is not bool or seed.synthetic!=synthetic:
        return "MIXED_SYNTHETIC_INPUT"
    if seed.currency!="USD":
        return "CURRENCY_SCOPE_NOT_SUPPORTED"
    return None


def parse_universe_values(values: list, receipt: UniverseReceipt, *, identity_lookup: Mapping[str,ListingSeed]) -> UniverseParseResult:
    """Parse the fixed A=code/B=marketcap/C=price contract, never Quotes rows."""
    def fail(reason):
        return UniverseParseResult("NOT_AVAILABLE",receipt if isinstance(receipt,UniverseReceipt) else None,(),0,(reason,),False,True)
    if not isinstance(receipt,UniverseReceipt) or receipt.source!="GOOGLEFINANCE_PRIVATE_UNIVERSE" or not _hash(receipt.content_sha256) or not _text(receipt.job_id) or type(receipt.session_epoch) is not int or receipt.session_epoch<0 or type(receipt.synthetic) is not bool or type(values) is not list or not isinstance(identity_lookup,Mapping):
        return fail("UNIVERSE_SCHEMA_MISMATCH")
    if not _aware(receipt.acquired_at):
        return fail("INVALID_TIMESTAMP")
    try:
        canonical=json.dumps(values,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
    except (ValueError,TypeError,RecursionError,OverflowError):
        return fail("UNIVERSE_SCHEMA_MISMATCH")
    if len(canonical)>1048576:
        return fail("SOURCE_TOO_LARGE")
    if hashlib.sha256(canonical).hexdigest()!=receipt.content_sha256:
        return fail("MANIFEST_MISMATCH")
    start=1 if values and type(values[0]) is list and len(values[0])==3 and all(type(v) is str for v in values[0]) and [v.lower() for v in values[0]]==["code","marketcap","price"] else 0
    end=len(values)
    while end>start and type(values[end-1]) is list and all(v is None or (type(v) is str and v=="") for v in values[end-1]):
        end-=1
    limited=end-start>=1024
    unique={}
    for index in range(start,min(end,start+1024)):
        data=values[index]
        if type(data) is not list or len(data)>3:
            row=UniverseRow(index,None,None,None,None,("UNIVERSE_SCHEMA_MISMATCH",),receipt)
        else:
            data=data+[None]*(3-len(data))
            code=data[0] if _text(data[0]) else None
            seed=identity_lookup.get(code) if code is not None else None
            error=_identity_error(seed,receipt.acquired_at,receipt.synthetic)
            if not error and ":" in code:
                prefix=code.split(":",1)[0]
                if (prefix,seed.mic) not in (("NASDAQ","XNAS"),("NYSE","XNYS")):
                    error="IDENTITY_UNCONFIRMED"
            google,price=_sheet_number(data[1]),_sheet_number(data[2])
            reasons=[]
            if error:
                reasons.append(error)
            else:
                if google is None:
                    reasons.append("GOOGLE_MCAP_MISSING" if data[1] is None or data[1]=="" else "GOOGLE_MCAP_INVALID")
                if price is None:
                    reasons.append("PRICE_NOT_AVAILABLE")
            row=UniverseRow(index,code,seed if not error else None,google,price,tuple(reasons),receipt)
        key=("listing",row.listing.listing_id) if row.listing else ("code",row.code) if row.code else ("index",index)
        previous=unique.get(key)
        if previous is None:
            unique[key]=row
        elif (previous.listing,previous.google_mcap,previous.sheet_price,previous.reason_codes)!=(row.listing,row.google_mcap,row.sheet_price,row.reason_codes):
            unique[key]=replace(previous,google_mcap=None,sheet_price=None,reason_codes=("INVALID_INPUT",))
    rows=tuple(unique.values())
    return UniverseParseResult("INPUT_RESEARCH" if rows else "NOT_AVAILABLE",receipt,rows,len(rows),("ROW_LIMIT_REACHED",) if limited else (),limited,receipt.synthetic)


def _basis_error(seed,basis,as_of,synthetic):
    if not isinstance(basis,ShareBasisReceipt) or (basis.listing_id,basis.company_id,basis.security_id)!=(seed.listing_id,seed.company_id,seed.security_id) or basis.basis_status not in ("SINGLE_CLASS_CONFIRMED","CA_UNIT_APPROVED") or not _text(basis.source_evidence_ref) or not _hash(basis.source_sha256) or basis.share_unit!="shares" or basis.price_basis!="GOOGLEFINANCE_CURRENT" or basis.currency!=seed.currency:
        return "BASIS_UNCONFIRMED"
    if not _aware(basis.available_at):
        return "INVALID_TIMESTAMP"
    if _utc(basis.available_at)>_utc(as_of):
        return "AVAILABLE_AFTER_AS_OF"
    if type(basis.synthetic) is not bool or basis.synthetic!=synthetic:
        return "MIXED_SYNTHETIC_INPUT"
    return None


def _cik(value):
    if type(value) not in (int,str):
        return None
    value=str(value)
    if not re.fullmatch(r"[0-9]{1,10}",value) or int(value)==0:
        return None
    return value.zfill(10)


def _day(value):
    if type(value) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}",value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def prepare_sec_shares(seed: ListingSeed, receipt: SecReceipt, basis: ShareBasisReceipt, as_of: datetime) -> SharesInput:
    """Use supplied, hash-bound SEC facts/submissions; never backfill publication."""
    def fail(reason):
        return SharesInput("NOT_AVAILABLE",seed.listing_id if isinstance(seed,ListingSeed) else None,seed.company_id if isinstance(seed,ListingSeed) else None,seed.security_id if isinstance(seed,ListingSeed) else None,None,None,None,None,None,None,(reason,),receipt.synthetic if isinstance(receipt,SecReceipt) and type(receipt.synthetic) is bool else True)
    if not isinstance(receipt,SecReceipt):
        return fail("INVALID_INPUT")
    if type(receipt.synthetic) is not bool:
        return fail("MIXED_SYNTHETIC_INPUT")
    if not _aware(as_of) or not _aware(receipt.acquired_at):
        return fail("INVALID_TIMESTAMP")
    error=_identity_error(seed,receipt.acquired_at,receipt.synthetic)
    if error:
        return fail(error)
    if receipt.cik!=seed.cik:
        return fail("CIK_MISMATCH")
    if _utc(receipt.acquired_at)>_utc(as_of):
        return fail("AVAILABLE_AFTER_AS_OF")
    for body,sha in ((receipt.companyfacts_body,receipt.facts_sha256),(receipt.submissions_body,receipt.submissions_sha256)):
        if type(body) is not bytes or not _hash(sha):
            return fail("INVALID_INPUT")
        if len(body)>8388608:
            return fail("SOURCE_TOO_LARGE")
        if hashlib.sha256(body).hexdigest()!=sha:
            return fail("MANIFEST_MISMATCH")
    try:
        facts=json.loads(receipt.companyfacts_body); submissions=json.loads(receipt.submissions_body)
    except (ValueError,UnicodeError,RecursionError):
        return fail("INVALID_INPUT")
    if type(facts) is not dict or type(submissions) is not dict or _cik(facts.get("cik"))!=seed.cik or _cik(submissions.get("cik"))!=seed.cik:
        return fail("CIK_MISMATCH")
    error=_basis_error(seed,basis,as_of,receipt.synthetic)
    if error:
        return fail(error)
    try:
        rec=submissions["filings"]["recent"]
        columns=[rec[k] for k in ("accessionNumber","form","filingDate","acceptanceDateTime")]
        if any(type(c) is not list for c in columns) or len({len(c) for c in columns})!=1:
            return fail("ACCESSION_UNCONFIRMED")
        index={}
        for accn,form,filed,accepted in zip(*columns):
            if type(accn) is not str or not re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}",accn) or form not in ("10-K","10-K/A","20-F","20-F/A","40-F","10-Q","10-Q/A","6-K") or _day(filed) is None:
                continue
            if accepted is None or accepted=="":
                index[accn]=(None,"ACCESSION_UNCONFIRMED",form,filed); continue
            try:
                accepted_at=datetime.fromisoformat(accepted.replace("Z","+00:00")) if type(accepted) is str else None
            except ValueError:
                accepted_at=None
            error=None
            if not _aware(accepted_at):
                error="INVALID_TIMESTAMP"
            elif _utc(accepted_at)>_utc(receipt.acquired_at) or _day(filed)>_utc(receipt.acquired_at).date() or _utc(accepted_at).date()<_day(filed):
                error="INVALID_TIME_ORDER"
            entry=(accepted_at,error,form,filed)
            if accn in index and index[accn]!=entry:
                index[accn]=(None,"ACCESSION_UNCONFIRMED",form,filed)
            else:
                index[accn]=entry
        concepts=facts.get("facts")
        if type(concepts) is not dict:
            return fail("SHARES_NOT_AVAILABLE")
        last_reason="SHARES_NOT_AVAILABLE"
        for taxonomy,concept in (("dei","EntityCommonStockSharesOutstanding"),("us-gaap","CommonStockSharesOutstanding")):
            bucket=concepts.get(taxonomy,{})
            node=bucket.get(concept,{}) if type(bucket) is dict else {}
            units=node.get("units",{}) if type(node) is dict else {}
            rows=units.get("shares",[]) if type(units) is dict else []
            if type(rows) is not list:
                last_reason="SHARES_NOT_AVAILABLE"; continue
            eligible=[]
            for row in rows:
                if type(row) is not dict or not _positive(row.get("val")) or _day(row.get("end")) is None:
                    continue
                accn=row.get("accn")
                filing=index.get(accn) if type(accn) is str else None
                if filing is None:
                    last_reason="ACCESSION_UNCONFIRMED"; continue
                if filing[1]:
                    last_reason=filing[1]; continue
                accepted_at,_,form,filed=filing
                if row.get("form")!=form or row.get("filed")!=filed or _day(row["end"])>_day(filed) or _day(row["end"])>_utc(receipt.acquired_at).date():
                    last_reason="SHARES_NOT_AVAILABLE"; continue
                eligible.append((_utc(accepted_at),_day(filed),accn,_day(row["end"]),float(row["val"])))
            if eligible:
                latest=max((r[:3] for r in eligible))
                filing_rows=[r for r in eligible if r[:3]==latest]
                end=max(r[3] for r in filing_rows)
                values={r[4] for r in filing_rows if r[3]==end}
                if len(values)!=1:
                    return fail("MULTI_CLASS_AMBIGUOUS")
                return SharesInput("INPUT_RESEARCH",seed.listing_id,seed.company_id,seed.security_id,next(iter(values)),receipt.acquired_at,end,latest[2],taxonomy+":"+concept,basis.source_sha256,(),receipt.synthetic,
                                   facts_sha256=receipt.facts_sha256,submissions_sha256=receipt.submissions_sha256)
        return fail(last_reason)
    except (KeyError,TypeError,AttributeError,ValueError,OverflowError):
        return fail("INVALID_INPUT")


def prepare_universe_price(row: UniverseRow, basis: ShareBasisReceipt, *, as_of: datetime) -> PriceInput:
    def result(reason=None):
        good=reason is None
        seed=row.listing if isinstance(row,UniverseRow) and isinstance(row.listing,ListingSeed) else None
        receipt=row.receipt if isinstance(row,UniverseRow) and isinstance(row.receipt,UniverseReceipt) else None
        return PriceInput("INPUT_RESEARCH" if good else "NOT_AVAILABLE",seed.listing_id if seed else None,seed.company_id if seed else None,seed.security_id if seed else None,
                          row.sheet_price if good else None,receipt.acquired_at if good else None,receipt.acquired_at if good else None,as_of,
                          receipt.content_sha256 if receipt else None,row.row_index if isinstance(row,UniverseRow) else None,basis.source_sha256 if isinstance(basis,ShareBasisReceipt) else None,
                          () if good else (reason,),receipt.synthetic if receipt else True)
    if not isinstance(row,UniverseRow) or not isinstance(row.receipt,UniverseReceipt) or not isinstance(row.listing,ListingSeed):
        return result("IDENTITY_UNCONFIRMED")
    if not _row_valid(row):
        return result("INVALID_INPUT")
    if not _aware(as_of) or not _aware(row.receipt.acquired_at):
        return result("INVALID_TIMESTAMP")
    error=_identity_error(row.listing,row.receipt.acquired_at,row.receipt.synthetic)
    if error:
        return result(error)
    if _utc(row.receipt.acquired_at)>_utc(as_of):
        return result("AVAILABLE_AFTER_AS_OF")
    error=_basis_error(row.listing,basis,as_of,row.receipt.synthetic)
    if error:
        return result(error)
    if "INVALID_INPUT" in row.reason_codes:
        return result("INVALID_INPUT")
    if not _positive(row.sheet_price):
        return result("PRICE_NOT_AVAILABLE")
    return result()


def compare_universe_market_cap(row: UniverseRow, shares: SharesInput, price: PriceInput, quality_config: QualityConfig) -> CapCheck:
    def result(reason=None,cap=None,relative=None,quality="UNCONFIRMED"):
        return CapCheck(row.row_index if isinstance(row,UniverseRow) else -1,row.listing if isinstance(row,UniverseRow) else None,
                        "VERIFIED" if reason is None else "NOT_AVAILABLE",cap,row.google_mcap if isinstance(row,UniverseRow) else None,relative,cap,quality,
                        "검증 불일치" if quality=="MISMATCH" else "",() if reason is None else (reason,),row.receipt.content_sha256 if isinstance(row,UniverseRow) and isinstance(row.receipt,UniverseReceipt) else "",row.receipt.synthetic if isinstance(row,UniverseRow) and isinstance(row.receipt,UniverseReceipt) else True,
                        shares if reason is None else None,price if reason is None else None)
    if not isinstance(row,UniverseRow) or not isinstance(row.listing,ListingSeed) or not isinstance(row.receipt,UniverseReceipt) or not isinstance(shares,SharesInput) or not isinstance(price,PriceInput):
        return result("IDENTITY_UNCONFIRMED")
    if not _row_valid(row) or not _codes(shares.reason_codes) or not _codes(price.reason_codes) or shares.historical_first_publication is not False:
        return result("INVALID_INPUT")
    seed=row.listing
    if (shares.listing_id,shares.company_id,shares.security_id)!=(seed.listing_id,seed.company_id,seed.security_id) or (price.listing_id,price.company_id,price.security_id)!=(seed.listing_id,seed.company_id,seed.security_id):
        return result("IDENTITY_UNCONFIRMED")
    if not _aware(price.as_of):
        return result("INVALID_TIMESTAMP")
    if shares.state!="INPUT_RESEARCH":
        return result(shares.reason_codes[0] if shares.reason_codes else "SHARES_NOT_AVAILABLE")
    if not _aware(shares.shares_available_at) or not _aware(row.receipt.acquired_at):
        return result("INVALID_TIMESTAMP")
    if _utc(shares.shares_available_at)>_utc(price.as_of) or _utc(row.receipt.acquired_at)>_utc(price.as_of):
        return result("AVAILABLE_AFTER_AS_OF")
    if not _positive(shares.shares):
        return result("SHARES_NOT_AVAILABLE")
    if type(shares.measurement_date) is not date or shares.measurement_date>_utc(shares.shares_available_at).date() or not _text(shares.accn) or shares.concept not in ("dei:EntityCommonStockSharesOutstanding","us-gaap:CommonStockSharesOutstanding") or not _hash(shares.facts_sha256) or not _hash(shares.submissions_sha256):
        return result("SHARES_NOT_AVAILABLE")
    if not _hash(shares.basis_sha256) or shares.basis_sha256!=price.basis_sha256:
        return result("BASIS_UNCONFIRMED")
    if price.state!="INPUT_RESEARCH":
        return result(price.reason_codes[0] if price.reason_codes else "PRICE_NOT_AVAILABLE")
    if price.content_sha256!=row.receipt.content_sha256 or price.row_index!=row.row_index or price.price!=row.sheet_price or not _positive(price.price) or price.price_kind!="GOOGLEFINANCE_CURRENT" or price.exact_eod is not False or price.trade_time is not None:
        return result("MANIFEST_MISMATCH")
    if not _aware(price.available_at) or not _aware(price.observed_at) or _utc(price.available_at)!=_utc(row.receipt.acquired_at) or _utc(price.observed_at)!=_utc(row.receipt.acquired_at):
        return result("INVALID_TIME_ORDER")
    if seed.currency!="USD":
        return result("CURRENCY_SCOPE_NOT_SUPPORTED")
    if any(type(v) is not bool for v in (shares.synthetic,price.synthetic,row.receipt.synthetic)) or len({shares.synthetic,price.synthetic,row.receipt.synthetic})!=1:
        return result("MIXED_SYNTHETIC_INPUT")
    if not isinstance(quality_config,QualityConfig) or quality_config.confirmed is not True:
        return result("CONFIG_CONFIRMATION_REQUIRED")
    if not _positive(quality_config.relative_tolerance):
        return result("INVALID_INPUT")
    try:
        cap=shares.shares*price.price
        if not _positive(cap):
            return result("NONFINITE_MCAP")
        if row.google_mcap is None:
            quality="GOOGLE_MCAP_MISSING" if "GOOGLE_MCAP_MISSING" in row.reason_codes else "GOOGLE_MCAP_INVALID"
            return result(cap=cap,quality=quality)
        if not _positive(row.google_mcap):
            return result("INVALID_INPUT")
        # Exact decimal representations for the same quality formula. Cross
        # multiplication avoids a binary rounding slip at the inclusive boundary;
        # the ranking key remains the existing unrounded shares*price result.
        ratio=abs(Fraction(str(row.google_mcap))-Fraction(str(cap)))/Fraction(str(cap))
        relative=float(ratio)
        if not math.isfinite(relative):
            return result("NONFINITE_MCAP")
        return result(cap=cap,relative=relative,quality="MISMATCH" if ratio>=Fraction(str(quality_config.relative_tolerance)) else "WITHIN_TOLERANCE")
    except (OverflowError,ZeroDivisionError):
        return result("NONFINITE_MCAP")


def select_verified_universe_top_n(checks: tuple[CapCheck,...], selection_config: SelectionConfig, *, parsed: UniverseParseResult) -> UniverseSelection:
    """Rank only validated R values; preserve missing full-input coverage."""
    requested=selection_config.n if isinstance(selection_config,SelectionConfig) and type(selection_config.n) is int else None
    count=parsed.row_count if isinstance(parsed,UniverseParseResult) and type(parsed.row_count) is int else 0
    sha=parsed.receipt.content_sha256 if isinstance(parsed,UniverseParseResult) and isinstance(parsed.receipt,UniverseReceipt) else None
    synthetic=parsed.synthetic if isinstance(parsed,UniverseParseResult) else True
    def fail(reason,status="UNCONFIRMED"):
        return UniverseSelection("NOT_AVAILABLE",status,sha,requested,0,count,0,count,(),(),(),(reason,),synthetic)
    if (not isinstance(parsed,UniverseParseResult) or parsed.state!="INPUT_RESEARCH" or not _receipt_valid(parsed.receipt)
            or type(parsed.rows) is not tuple or type(parsed.row_count) is not int or parsed.row_count!=len(parsed.rows)
            or not 0<count<=1024 or not _codes(parsed.reason_codes) or type(parsed.row_limit_reached) is not bool
            or type(parsed.synthetic) is not bool or parsed.synthetic!=parsed.receipt.synthetic
            or any(not _row_valid(row) for row in parsed.rows)
            or type(checks) is not tuple or any(not isinstance(c,CapCheck) or type(c.row_index) is not int or not _codes(c.reason_codes) for c in checks)):
        return fail("INVALID_INPUT")
    if len({row.row_index for row in parsed.rows})!=count:
        return fail("INVALID_INPUT")
    if any(row.receipt.content_sha256!=sha or row.receipt.job_id!=parsed.receipt.job_id
           or row.receipt.session_epoch!=parsed.receipt.session_epoch or row.receipt.synthetic!=synthetic
           or _utc(row.receipt.acquired_at)!=_utc(parsed.receipt.acquired_at) for row in parsed.rows):
        return fail("MANIFEST_MISMATCH")
    if not isinstance(selection_config,SelectionConfig) or selection_config.confirmed is not True:
        return fail("CONFIG_CONFIRMATION_REQUIRED")
    if requested is None or not 1<=requested<=count:
        return fail("INVALID_INPUT")
    if any(type(c.synthetic) is not bool or c.synthetic!=synthetic for c in checks):
        return fail("MIXED_SYNTHETIC_INPUT")
    if any("CONFIG_CONFIRMATION_REQUIRED" in c.reason_codes for c in checks):
        return fail("CONFIG_CONFIRMATION_REQUIRED")
    source_rows={r.row_index:r for r in parsed.rows}
    indexed={}
    for check in checks:
        row=source_rows.get(check.row_index)
        if row is None or check.content_sha256!=sha or check.listing!=row.listing or check.google_mcap!=row.google_mcap or check.row_index in indexed:
            return fail("MANIFEST_MISMATCH")
        if check.state not in ("VERIFIED","NOT_AVAILABLE") or (check.state=="VERIFIED" and (not _positive(check.effective_cap) or check.effective_cap!=check.recomputed_cap or check.listing is None or check.reason_codes or check.quality not in ("WITHIN_TOLERANCE","MISMATCH","GOOGLE_MCAP_MISSING","GOOGLE_MCAP_INVALID"))):
            return fail("INVALID_INPUT")
        indexed[check.row_index]=check
    issuers={}
    for row in parsed.rows:
        if row.listing is not None:
            issuers.setdefault(row.listing.issuer_id,[]).append(row)
    duplicates={row.row_index for bucket in issuers.values() if len(bucket)>1 for row in bucket}
    verified=[]; missing=[]; reasons=list(parsed.reason_codes)
    for row in parsed.rows:
        c=indexed.get(row.row_index)
        if row.row_index in duplicates:
            missing.append((row.row_index,("DUPLICATE_ISSUER",))); reasons.append("DUPLICATE_ISSUER")
        elif c is None or c.state!="VERIFIED":
            codes=c.reason_codes if c and c.reason_codes else row.reason_codes or ("VALIDATION_INCOMPLETE",)
            missing.append((row.row_index,codes)); reasons.extend(codes)
        else:
            verified.append(c)
    verified.sort(key=lambda c:(-c.effective_cap,c.listing.company_id))
    selected=tuple(verified[:requested])
    incomplete=bool(missing) or parsed.row_limit_reached or len(selected)<requested
    if incomplete:
        reasons.append("VALIDATION_INCOMPLETE")
    return UniverseSelection("PERSONAL_REFERENCE" if selected else "NOT_AVAILABLE","PARTIAL" if incomplete else "COMPLETE",sha,requested,len(selected),count,len(verified),len(missing),
                             tuple(c.listing.listing_id for c in selected),selected,tuple(missing),tuple(dict.fromkeys(reasons)),synthetic)
