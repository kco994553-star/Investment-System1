"""Price-free public SEC shares projection for the approved Universe504 codes.

User decision 2026-10-11 (M3 shares option a): Actions publish, per Universe
code, the latest SEC outstanding-share count and the filing-cover share-class
basis. The basis comes only from the same filing's cover XBRL as parsed by
``providers.sec_m3_adapter``: one matching class -> SINGLE_CLASS_CONFIRMED;
several classes with an unambiguous per-class value for this listing ->
SHARE_CLASS_BASIS (shown, never summed or corrected); anything else ->
BASIS_UNCONFIRMED. No price, market cap, rank, selection or device data.

User decision 2026-10-11 (M3 unlisted class): for each share_class_groups/v0
group with an unlisted cover class (Alphabet Class B), `unlisted_classes`
carries that class's count from the SAME cover filing as the valued-at listing
record (GOOGL): same accn, measurement date and cover hash, freshness mirrored.
Missing or ambiguous -> NOT_AVAILABLE with a reason and no count.
Missing values stay null, never 0. Shard count/stale window are v0 defaults
(DEFAULT_V0_UNCALIBRATED), not calibrated policy.
"""
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from zoneinfo import ZoneInfo

FILENAME = 'sec-universe-shares.json'
KIND = 'SEC_UNIVERSE_SHARES'
MAX_BYTES = 2 * 1024 * 1024
STATES = ('LIVE', 'STALE', 'NOT_AVAILABLE')
BASES = ('SINGLE_CLASS_CONFIRMED', 'SHARE_CLASS_BASIS', 'BASIS_UNCONFIRMED')
CONCEPTS = ('dei:EntityCommonStockSharesOutstanding', 'us-gaap:CommonStockSharesOutstanding')
FORMS = ('10-K', '10-K/A', '10-Q', '10-Q/A', '20-F', '20-F/A', '40-F', '6-K')
REASONS = (
    'IDENTITY_UNCONFIRMED', 'CIK_MISMATCH', 'INVALID_INPUT', 'INVALID_TIMESTAMP', 'AVAILABLE_AFTER_AS_OF',
    'BASIS_UNCONFIRMED', 'COVER_UNCONFIRMED', 'COVER_FACT_MISMATCH', 'COVER_NOT_AVAILABLE', 'ACCESSION_UNCONFIRMED',
    'MULTI_CLASS_AMBIGUOUS', 'SHARE_CLASS_BASIS', 'SHARES_NOT_AVAILABLE', 'INVALID_TIME_ORDER', 'MANIFEST_MISMATCH',
    'SOURCE_TOO_LARGE', 'MIXED_SYNTHETIC_INPUT', 'CURRENCY_SCOPE_NOT_SUPPORTED', 'CIK_UNRESOLVED', 'NOT_COLLECTED',
    'STALE_INPUT',
)
TOP_REASONS = ('STALE_INPUT', 'NO_ELIGIBLE_INPUT')
UNLISTED_REASONS = ('NOT_COLLECTED', 'UNLISTED_CLASS_SHARES_NOT_AVAILABLE', 'UNLISTED_CLASS_AMBIGUOUS', 'STALE_INPUT')
UNLISTED_KEYS = ('cik', 'valued_at', 'accn', 'measurement_date', 'cover_sha256', 'classes', 'state', 'reason_codes')
RECORD_KEYS = ('cik', 'listing_id', 'company_id', 'shares', 'measurement_date', 'accn', 'form', 'filed', 'acquired_at',
               'concept', 'share_class_basis', 'basis_evidence', 'source_sha256', 'state', 'reason_codes')
TOP_KEYS = ('schema_version', 'kind', 'as_of', 'config_version', 'config_status', 'freshness_basis', 'stale_after_seconds',
            'shard_count', 'last_shard_index', 'registry_sha256', 'code_count', 'state', 'reason_codes', 'records', 'unlisted_classes')
EVIDENCE_KEYS = ('cover_accn', 'class_count', 'class_members', 'listing_class_member')
HASH_KEYS = ('companyfacts', 'submissions', 'cover')
_HERE = Path(__file__).resolve().parent


def _need(condition):
    if not condition:
        raise ValueError('SEC_UNIVERSE_SHARES_INVALID')


def load_config():
    cfg = json.loads((_HERE / 'sec_universe_shares_config_v0.json').read_text())
    _need(set(cfg) == {'config_version', 'config_status', 'decision', 'shard_count', 'stale_after_days'})
    _need(cfg['config_version'] == 'sec-universe-shares/v0' and cfg['config_status'] == 'DEFAULT_V0_UNCALIBRATED')
    _need(type(cfg['shard_count']) is int and 1 <= cfg['shard_count'] <= 366)
    _need(type(cfg['stale_after_days']) is int and 1 <= cfg['stale_after_days'] <= 366)
    return cfg


def universe_codes():
    codes = json.loads((_HERE / 'universe_codes_v1.json').read_text())
    _need(type(codes) is list and len(codes) == len(set(codes)) == 504)
    return tuple(codes)


# The daily shard belongs to the run's New York calendar day (the US trading day the run observes), not its UTC day.
NEW_YORK = ZoneInfo('America/New_York')


def shard_day(moment):
    """Calendar day whose shard a run started at `moment` (timezone-aware) collects: its New York date.

    For every start from 04:00 UTC (EDT) / 05:00 UTC (EST) to 23:59 UTC this is the UTC date, so the scheduled 22:17 UTC
    run keeps its shard. A late or fallback run started after 00:00 UTC still belongs to the previous New York day:
    it collects that day's shard instead of skipping it and taking the next day's shard twice (owner, 2026-10-17)."""
    _need(isinstance(moment, datetime) and moment.utcoffset() is not None)
    return moment.astimezone(NEW_YORK).date()


def shard_index_for(day, shard_count):
    """Rotation index: day ordinal mod the fixed shard count. The daily run passes `shard_day(start)`."""
    _need(type(day) is date and type(shard_count) is int and shard_count >= 1)
    return day.toordinal() % shard_count


def _iso(value):
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def _clock(value):
    _need(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', value) is not None)
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    _need(parsed.utcoffset() is not None)
    return parsed.astimezone(timezone.utc)


def _day(value):
    _need(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) is not None)
    return date.fromisoformat(value)


def _hash(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _positive(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        return False


def _number(value):
    """Integral share counts are written as JSON integers; the value itself is unchanged."""
    return int(value) if type(value) is float and value.is_integer() and value < 2 ** 53 else value


def _sec_symbol(code):
    venue, symbol = code.split(':', 1)
    return venue, symbol.replace('.', '-')


def empty_record(*, cik=None, reasons=('NOT_COLLECTED',)):
    return {'cik': cik, 'listing_id': None, 'company_id': None, 'shares': None, 'measurement_date': None, 'accn': None,
            'form': None, 'filed': None, 'acquired_at': None, 'concept': None, 'share_class_basis': 'BASIS_UNCONFIRMED',
            'basis_evidence': {'cover_accn': None, 'class_count': None, 'class_members': [], 'listing_class_member': None},
            'source_sha256': {'companyfacts': None, 'submissions': None, 'cover': None},
            'state': 'NOT_AVAILABLE', 'reason_codes': list(reasons)}


def _unlisted_groups():
    from .share_class_groups import unlisted_groups
    return unlisted_groups()


def empty_unlisted(group, reasons=('NOT_COLLECTED',)):
    return {'cik': group['cik'], 'valued_at': group['unlisted']['valued_at'], 'accn': None, 'measurement_date': None,
            'cover_sha256': None, 'classes': [], 'state': 'NOT_AVAILABLE', 'reason_codes': list(reasons)}


def build_unlisted_entry(group, record, cover):
    """Unlisted cover classes of one group from the valued-at listing's own cover parse. Nothing is inferred."""
    entry = empty_unlisted(group, ('UNLISTED_CLASS_SHARES_NOT_AVAILABLE',))
    if (type(record) is not dict or record.get('share_class_basis') != 'SHARE_CLASS_BASIS' or record.get('shares') is None
            or record.get('cik') != group['cik'] or not isinstance(cover, dict)):
        return entry
    found = tuple(cover.get('unlisted_classes') or ())
    if not found:
        return entry
    reasons = {reason for _, _, reason in found if reason is not None}
    if reasons:
        entry['reason_codes'] = ['UNLISTED_CLASS_AMBIGUOUS' if 'UNLISTED_CLASS_AMBIGUOUS' in reasons else 'UNLISTED_CLASS_SHARES_NOT_AVAILABLE']
        return entry
    if not all(_positive(value) and type(value) is not bool for _, value, _ in found):
        return entry
    entry.update(accn=record['accn'], measurement_date=record['measurement_date'], cover_sha256=record['source_sha256']['cover'],
                 classes=[{'class_member': name, 'shares': _number(value)} for name, value, _ in sorted(found, key=lambda x: x[0])],
                 state=record['state'], reason_codes=['STALE_INPUT'] if record['state'] == 'STALE' else [])
    return entry


def restate_unlisted(group, entry, record):
    """Freshness mirrors the bound listing record; a count no longer bound to that record's cover is dropped."""
    out = json.loads(json.dumps(entry))
    if not out['classes']:
        out['state'] = 'NOT_AVAILABLE'
        out['reason_codes'] = [r for r in out['reason_codes'] if r != 'STALE_INPUT'] or ['UNLISTED_CLASS_SHARES_NOT_AVAILABLE']
        return out
    if (record['share_class_basis'] != 'SHARE_CLASS_BASIS' or record['shares'] is None or record['cik'] != out['cik']
            or (out['accn'], out['measurement_date'], out['cover_sha256']) != (record['accn'], record['measurement_date'], record['source_sha256']['cover'])):
        return empty_unlisted(group, ('UNLISTED_CLASS_SHARES_NOT_AVAILABLE',))
    out['state'] = record['state']
    out['reason_codes'] = ['STALE_INPUT'] if record['state'] == 'STALE' else []
    return out


def upgrade_legacy(payload):
    """A copy published before `unlisted_classes` existed keeps its rows; each group gets NOT_COLLECTED (no count)."""
    if type(payload) is dict and 'unlisted_classes' not in payload and set(payload) == set(TOP_KEYS) - {'unlisted_classes'}:
        return {**payload, 'unlisted_classes': {gid: empty_unlisted(g) for gid, g in _unlisted_groups().items()}}
    return payload


def select_cover_filing(submissions_body, as_of):
    """Latest periodic report (10-K/10-Q, amendments) at or before as_of with a primary .htm document."""
    try:
        sub = json.loads(submissions_body)
        rec = sub['filings']['recent']
        cols = [rec[k] for k in ('accessionNumber', 'form', 'filingDate', 'primaryDocument')]
        if any(type(c) is not list for c in cols) or len({len(c) for c in cols}) != 1:
            return None
        best = None
        for accn, form, filed, doc in zip(*cols):
            if form not in ('10-K', '10-Q', '10-K/A', '10-Q/A') or type(accn) is not str or type(filed) is not str or type(doc) is not str:
                continue
            if not re.fullmatch(r'\d{10}-\d{2}-\d{6}', accn) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', filed) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.htm', doc):
                continue
            if filed > as_of.astimezone(timezone.utc).date().isoformat():
                continue
            if best is None or (filed, accn) > (best[1], best[0]):
                best = (accn, filed, doc)
        return None if best is None else {'accession': best[0], 'filed': best[1], 'primary_document': best[2]}
    except (ValueError, KeyError, TypeError, UnicodeError, RecursionError):
        return None


def _filing(submissions_body, accn):
    try:
        rec = json.loads(submissions_body)['filings']['recent']
        accns = rec['accessionNumber']
        if type(accns) is list and accns.count(accn) == 1:
            i = accns.index(accn)
            form, filed = rec['form'][i], rec['filingDate'][i]
            if form in FORMS and type(filed) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}', filed):
                return form, filed
    except (ValueError, KeyError, TypeError, IndexError, UnicodeError, RecursionError):
        pass
    return None


def build_share_record(**kwargs):
    """One Universe code from supplied SEC bytes. The adapter decides; nothing is inferred here."""
    return _share_record(**kwargs)[0]


def build_issuer_records(*, codes, cik, companyfacts_body, submissions_body, acquired_at, as_of,
                         cover_xml=None, cover_accession=None, cover_acquired_at=None):
    """Every Universe code of one issuer plus `unlisted_classes` entries for groups valued at one of those codes."""
    records, covers = {}, {}
    for code in codes:
        records[code], covers[code] = _share_record(code=code, cik=cik, companyfacts_body=companyfacts_body, submissions_body=submissions_body,
                                                    acquired_at=acquired_at, as_of=as_of, cover_xml=cover_xml,
                                                    cover_accession=cover_accession, cover_acquired_at=cover_acquired_at)
    unlisted = {gid: build_unlisted_entry(g, records[g['unlisted']['valued_at']], covers[g['unlisted']['valued_at']])
                for gid, g in _unlisted_groups().items() if g['cik'] == cik and g['unlisted']['valued_at'] in records}
    return records, unlisted


def _share_record(*, code, cik, companyfacts_body, submissions_body, acquired_at, as_of,
                  cover_xml=None, cover_accession=None, cover_acquired_at=None):
    """(record, the adapter's cover evidence or None)."""
    from ..providers.sec_m3_adapter import build_sec_m3_input
    from .private_subset import ShareBasisReceipt, prepare_sec_shares
    venue, symbol = _sec_symbol(code)
    result = build_sec_m3_input(code=venue + ':' + symbol, companyfacts_body=companyfacts_body, submissions_body=submissions_body,
                                acquired_at=acquired_at, as_of=as_of, synthetic=False, cover_xml=cover_xml,
                                cover_accession=cover_accession, cover_acquired_at=cover_acquired_at)
    sha = lambda b: hashlib.sha256(b).hexdigest() if type(b) is bytes else None
    record = empty_record(cik=cik, reasons=[r for r in result.reason_codes if r in REASONS] or ['BASIS_UNCONFIRMED'])
    if result.seed is None or result.seed.cik != cik:
        if result.seed is not None:
            record['reason_codes'] = ['CIK_MISMATCH']
        return record, result.cover
    seed = result.seed
    record.update(listing_id=seed.listing_id, company_id=seed.company_id, acquired_at=_iso(acquired_at))
    record['source_sha256'] = {'companyfacts': sha(companyfacts_body), 'submissions': sha(submissions_body), 'cover': sha(cover_xml)}
    cover = result.cover
    record['basis_evidence'] = {'cover_accn': cover_accession if cover_xml is not None and type(cover_accession) is str and re.fullmatch(r'\d{10}-\d{2}-\d{6}', cover_accession) else None,
                                'class_count': len(cover['class_members']) if cover else None,
                                'class_members': list(cover['class_members']) if cover else [],
                                'listing_class_member': cover['listing_class_member'] if cover else None}
    if cover_xml is None:
        record['reason_codes'] = ['COVER_NOT_AVAILABLE']
    cover_at = cover_acquired_at.astimezone(timezone.utc) if isinstance(cover_acquired_at, datetime) and cover_acquired_at.utcoffset() is not None else acquired_at
    if result.state == 'INPUT_RESEARCH':
        shares = result.shares
        filing = _filing(submissions_body, shares.accn)
        if filing is None:
            record['reason_codes'] = ['ACCESSION_UNCONFIRMED']
            return record, result.cover
        record.update(shares=_number(shares.shares), measurement_date=shares.measurement_date.isoformat(), accn=shares.accn,
                      form=filing[0], filed=filing[1], acquired_at=_iso(max(acquired_at, cover_at)), concept=shares.concept,
                      share_class_basis='SINGLE_CLASS_CONFIRMED', state='LIVE', reason_codes=[])
        return record, result.cover
    reason = result.reason_codes[0] if result.reason_codes else 'BASIS_UNCONFIRMED'
    per_class = (cover is not None and cover['multi_class'] and cover['dimensioned'] and cover['listing_class_member'] is not None
                 and len(cover['class_members']) >= 2
                 and reason in ('SHARE_CLASS_BASIS', 'MULTI_CLASS_AMBIGUOUS', 'COVER_FACT_MISMATCH'))
    if per_class:
        # The cover's own per-class value for this listing. Displayed only; never summed or corrected.
        filing = _filing(submissions_body, cover_accession)
        if filing is not None and _positive(cover['value']):
            record.update(shares=_number(cover['value']), measurement_date=cover['measurement_date'], accn=cover_accession,
                          form=filing[0], filed=filing[1], acquired_at=_iso(max(acquired_at, cover_at)),
                          concept=CONCEPTS[0], share_class_basis='SHARE_CLASS_BASIS', state='LIVE', reason_codes=['SHARE_CLASS_BASIS'])
            return record, result.cover
    # BASIS_UNCONFIRMED: keep the SEC companyfacts count visible when it is determinable, never verified.
    extraction = ShareBasisReceipt(seed.listing_id, seed.company_id, seed.security_id, 'SINGLE_CLASS_CONFIRMED',
                                   'companyfacts-extraction-only', sha(companyfacts_body), acquired_at, 'shares',
                                   'GOOGLEFINANCE_CURRENT', 'USD', False, 'ALIGNED')
    shares = prepare_sec_shares(seed, result.receipt, extraction, as_of) if result.receipt is not None else None
    record['reason_codes'] = [reason if reason in REASONS else 'BASIS_UNCONFIRMED']
    if cover_xml is None:
        record['reason_codes'] = ['COVER_NOT_AVAILABLE']
    if shares is not None and shares.state == 'INPUT_RESEARCH':
        filing = _filing(submissions_body, shares.accn)
        if filing is not None:
            record.update(shares=_number(shares.shares), measurement_date=shares.measurement_date.isoformat(), accn=shares.accn,
                          form=filing[0], filed=filing[1], acquired_at=_iso(acquired_at), concept=shares.concept, state='LIVE')
    return record, result.cover


def restate(record, as_of, stale_after):
    """Freshness from each row's own acquisition time; values are never changed."""
    out = json.loads(json.dumps(record))
    reasons = [r for r in out['reason_codes'] if r != 'STALE_INPUT']
    if out['shares'] is None:
        out['state'] = 'NOT_AVAILABLE'
        out['reason_codes'] = reasons or ['SHARES_NOT_AVAILABLE']
        return out
    fresh = as_of.astimezone(timezone.utc) - _clock(out['acquired_at']) <= stale_after
    out['state'] = 'LIVE' if fresh else 'STALE'
    out['reason_codes'] = reasons + ([] if fresh else ['STALE_INPUT'])
    return out


# ---- previous observations across collection/identification failures (owner decision 2026-10-17, option a) ----
PRESERVE, IDENTITY_CONFLICT = 'PRESERVE', 'IDENTITY_CONFLICT'


def verified_observation(row):
    """A published (validated) row that records one SEC collection of its issuer: the issuer's CIK, the row's own
    acquisition time and both SEC source hashes."""
    if type(row) is not dict:
        return False
    hashes = row.get('source_sha256')
    cik = row.get('cik')
    return (type(cik) is str and re.fullmatch(r'[0-9]{10}', cik) is not None and cik != '0000000000'
            and type(row.get('acquired_at')) is str and type(hashes) is dict
            and bool(hashes.get('companyfacts')) and bool(hashes.get('submissions')))


# ---- listing ended (STALE_REPORT 2026-10-25 option B-a; owner approval in its PR) ----
# A small reviewed table of Universe codes whose listing has ended for good (acquired for cash and delisted), each with
# the issuer's CIK, the effective date and the SEC evidence. Absence from SEC's ticker file never puts a code here (that
# is the transient gap PRESERVE rides out, and a ticker change like NASDAQ:PSKY -> NYSE:SKYD also looks like it): only an
# explicit, evidenced, owner-approved entry does. The code stays in the fixed Universe504 list (UNI-DEF (a), UNI-FOLLOW
# (a): the denominator 504 is unchanged). `previous_decision` checks this table BEFORE the PRESERVE rule: in each of the
# three Universe files a listed code whose kept row is a verified observation of THE LISTED CIK is published as a
# reasoned NA row (`ended_row`): NOT_AVAILABLE, no values, scores or calc_version, the existing reason CIK_UNRESOLVED (no
# new reason code, no schema change; a dedicated LISTING_ENDED reason is a later schema change), and the last
# observation's cik, acquired_at and source hashes kept (the freshness guard sees an EQUAL record, never LOST_RECORD).
# On this row acquired_at means "last real observation of a listing that has ended". A kept row of another CIK (or no
# verified observation) is not touched by the entry: the ordinary rules apply.
LISTING_ENDED = 'LISTING_ENDED'
LISTING_ENDED_REASON = 'CIK_UNRESOLVED'
LISTING_ENDED_CODES = {
    'NASDAQ:WBD': {
        'cik': '0001437107',
        'effective': '2026-10-06',
        'reason': 'ACQUIRED_FOR_CASH_DELISTED',
        'evidence': (
            'SEC 8-K filed 2026-10-06, items 2.01 and 3.01, accession 0001193125-26-415055',
            'SEC Form 25 filed 2026-10-06, accession 0001193125-26-415091',
            'SEC Form 25-NSE (Nasdaq) filed 2026-10-06, accession 0001354457-26-000951',
            'SEC Form 15-12G filed 2026-10-16, accession 0001193125-26-423513',
            'PR #390 doc UNIVERSE_INDEX_FOLLOWING_20261023.md section 2-2 (WBD filing sequence)',
        ),
    },
}


def listing_ended(code, old):
    """True when `code` is in LISTING_ENDED_CODES and the kept row is a verified observation of that entry's CIK."""
    entry = LISTING_ENDED_CODES.get(code)
    return entry is not None and verified_observation(old) and old['cik'] == entry['cik']


def ended_row(old, empty):
    """The reasoned NA row of a listing-ended code in one file: that file's `empty_record` with the existing reason
    CIK_UNRESOLVED, plus the kept row's cik, acquired_at and source hashes (nothing else of it: no value, score,
    calc_version or identity binding). The same row comes back unchanged from itself on every later run."""
    return dict(empty(cik=old['cik'], reasons=(LISTING_ENDED_REASON,)), acquired_at=old['acquired_at'],
                source_sha256=dict(old['source_sha256']))


def previous_decision(old, new, *, code, unresolved=(), conflicts=(), new_observation):
    """How one Universe code's kept row meets this run's row; None leaves the file's merge rule (`replaces`).

    - LISTING_ENDED (checked first, before PRESERVE): the code's listing has ended (LISTING_ENDED_CODES) and the kept
      row is a verified observation of the entry's CIK. Whatever this run brings, the file publishes `ended_row`.
    - PRESERVE: this run has no new observation of the code (its symbol is unresolved in today's SEC registry, or its
      row records no verified collection: identity unconfirmed, builder failure, rejected by the validator, a transient
      failure after the bytes arrived) while the kept row is a verified observation of the SAME issuer (same CIK, no
      conflicting claim). The kept row stays unchanged (acquired_at, source hashes, calc_version), and
      freshness/STALE/ranking rules judge it as before.
    - IDENTITY_CONFLICT: another CIK for the code, or explicit conflict evidence this run (`conflicts`: a ticker claimed
      by several CIKs, an issuer whose SEC response named another CIK). This run's row replaces the kept one, also over
      a kept value: another issuer's earlier values are never carried. Without this run's collection (no row: a ticker
      claimed by several CIKs is unresolved; or a row without its own collection record) the kept row is withdrawn: a
      kept collection record becomes a withdrawal row naming it (`withdrawal`, owner decision UNI-WITHDRAWN (a)), else the
      code is CIK_UNRESOLVED / this run's NA row without acquired_at (a detection time is not a collection time).
    A new observation (successful collection, also a policy NA or an invalid input) never meets PRESERVE."""
    if listing_ended(code, old):
        return LISTING_ENDED
    if new is None:
        if code in conflicts:
            return IDENTITY_CONFLICT
        if code in unresolved and verified_observation(old):
            return PRESERVE
        return None
    old_cik, new_cik = old.get('cik'), new.get('cik')
    if code in conflicts or (old_cik is not None and new_cik is not None and old_cik != new_cik):
        return IDENTITY_CONFLICT
    if not new_observation(new) and new_cik is not None and new_cik == old_cik and verified_observation(old):
        return PRESERVE
    return None


def replaces(new, old, *, observed, has_value):
    """Merge rule when `previous_decision` is None (owner rule 2026-10-17, superseding the M3 option-a daily keep rule
    for this case): a new row that records this run's collection (`observed`: successful collection, also a policy NA
    or a confirmed invalid input) replaces the kept row, with its own acquired_at and reasons, even when it has no value
    and the kept row has one. A new row without its own collection record never erases a kept value."""
    return new is not None and (observed(new) or not (not has_value(new) and has_value(old)))


# ---- identity-conflict withdrawal (owner decision UNI-WITHDRAWN (a), 2026-10-17; TARGET /4 and sec-qgv2.json `target` rule) ----
# An IDENTITY_CONFLICT without a collection of this run (a ticker claimed by several CIKs, an SEC response naming another
# CIK, another CIK without its own collection record) stops the use of the code's published observation in each Universe
# file. When that file's kept row has a collection record, the code is published as a withdrawal row: NOT_AVAILABLE, reason
# IDENTITY_CONFLICT_WITHDRAWN only, no CIK, acquired_at, sources or values, plus three keys found on no other row:
# `detected_at` (the publishing merge's time when the conflict was first seen: never an acquisition time, never a freshness
# marker), `withdrawn_acquired_at` and `withdrawn_cik` (the acquired_at and CIK of THAT file's kept row: each file names
# its own observation, nothing is copied from TARGET or another file). Without a kept collection record nothing is
# invented: the code is CIK_UNRESOLVED (no row this run) or this run's NA row, as before.
# The withdrawal stays unchanged (first detection, same named observation) through later runs while the conflict lasts,
# through transient/identification failures, unresolved symbols and preserve-only rebuilds. Only a new collection of this
# run with confirmed identity (the code's own collection record, acquired_at at or after the detection, no conflict this
# run) replaces it; that row is the new issuer's own observation, never joined to the withdrawn issuer's history.
WITHDRAWN_REASON = 'IDENTITY_CONFLICT_WITHDRAWN'
WITHDRAWAL_KEYS = ('detected_at', 'withdrawn_acquired_at', 'withdrawn_cik')
# Schema transition (owner instruction 2026-10-17, #289 item 3; like sec-public-inputs.json /3 -> /4 in #285): the withdrawal
# row adds a reason code and three row keys to the contract of all three Universe files (each validator fixes its reason
# list and its exact row key set), so the files move from schema_version 1 to 2. Producers write 2. Readers, the
# previous-copy readers, the preserve-only (manual deploy) path and the freshness guard accept 1 and 2; a withdrawal row
# is valid only in a version-2 file. A reader that only knows 1 rejects a version-2 file as a whole (a safety block, not
# backward compatibility); the device shows the "newer data format" notice for a version above the one it knows.
SCHEMA_VERSION = 2
SCHEMA_VERSIONS = (1, 2)


def schema_version_of(payload):
    """The file's schema_version when this code reads it (1 or 2), else a fixed error."""
    version = payload.get('schema_version') if type(payload) is dict else None
    _need(type(version) is int and version in SCHEMA_VERSIONS)
    return version


def is_withdrawal(row):
    """A Universe withdrawal row (WITHDRAWAL_KEYS)."""
    return type(row) is dict and 'detected_at' in row


def withdrawal(old, empty, *, detected_at):
    """The row an IDENTITY_CONFLICT without this run's collection publishes for one code of one file, or None.

    `old`: that file's kept row of this code (the live copy as read by the run); `empty`: the file's `empty_record`. A
    kept withdrawal is returned unchanged; a kept row that identifies one observation exactly (`verified_observation`:
    its issuer's CIK, its own acquired_at and both SEC source hashes) is named by a new withdrawal; anything else -> None
    (the caller publishes its plain NA row: nothing else is withdrawn and no detection or acquisition time is invented).
    Only identity conflicts reach this: a plain fetch failure, an unresolved symbol or a collection without data never
    does (`previous_decision`: PRESERVE / `replaces`)."""
    if is_withdrawal(old):
        return old
    if verified_observation(old):
        return dict(empty(reasons=(WITHDRAWN_REASON,)), detected_at=_iso(detected_at), withdrawn_acquired_at=old['acquired_at'],
                    withdrawn_cik=old['cik'])
    return None


def withdrawal_stays(old, new, *, code, conflicts, observed):
    """True when the kept row is a withdrawal and this run's row is not a confirmed new collection of the code
    (`observed`, acquired_at at or after the detection, the code without conflict evidence this run)."""
    if not is_withdrawal(old):
        return False
    return not (new is not None and not is_withdrawal(new) and code not in conflicts and observed(new)
                and _clock(new['acquired_at']) >= _clock(old['detected_at']))


def note_withdrawal(stats, old, row, code):
    """Run-log counts only (never a row field): `withdrawal_kept` codes whose live withdrawal persists this run (the last
    re-check is this run's log line; detected_at and acquired_at never change), `withdrawn_new` codes withdrawn this run."""
    if stats is None or not is_withdrawal(row):
        return
    stats.setdefault('withdrawal_kept' if is_withdrawal(old) else 'withdrawn_new', set()).add(code)


def require_withdrawal(r, cut, empty):
    """Strict check of a withdrawal row's own keys: exactly the file's empty row with the withdrawal reason, a detection
    no later than the file, naming one earlier collection (acquired_at and CIK) of the code."""
    _need(type(r) is dict and set(r) - set(WITHDRAWAL_KEYS) == set(empty()) and set(WITHDRAWAL_KEYS) <= set(r))
    _need({k: v for k, v in r.items() if k not in WITHDRAWAL_KEYS} == empty(reasons=(WITHDRAWN_REASON,)))
    detected = _clock(r['detected_at'])
    _need(detected <= cut and _clock(r['withdrawn_acquired_at']) <= detected)
    cik = r['withdrawn_cik']
    _need(type(cik) is str and re.fullmatch(r'[0-9]{10}', cik) is not None and cik != '0000000000')


def note(stats, decision, code, old):
    """Codes of this merge kept by PRESERVE / of another identity not carried (a kept collection record replaced) /
    published as a listing-ended NA row."""
    if stats is None:
        return
    if decision == PRESERVE:
        stats.setdefault('preserved', set()).add(code)
    elif decision == LISTING_ENDED:
        stats.setdefault('listing_ended', set()).add(code)
    elif decision == IDENTITY_CONFLICT and verified_observation(old):
        stats.setdefault('identity_not_preserved', set()).add(code)


def merge(previous, updates, *, as_of, shard_index, registry_sha256=None, unresolved=(), config=None, unlisted_updates=None,
          conflicts=(), stats=None, transient=()):
    """Previous published rows + this shard's rows. A new row of this run's collection (identity confirmed: listing_id
    set) replaces the kept one also without shares (`replaces`); a row without that record never erases a kept value.
    Identity conflicts withdraw a kept collection record (`withdrawal`); a kept withdrawal stays (`withdrawal_stays`).
    `previous_decision` keeps a verified row across a collection/identification failure and never carries a row
    across an identity conflict (`conflicts`: codes with conflict evidence this run; `stats`: see `note`).
    `transient`: codes whose collection hit a transient failure after the SEC bytes arrived (the cover filing fetch
    failed); a row of theirs without shares records no completed collection, so it is no new observation.

    An `unlisted_classes` entry follows its valued-at listing row: replaced together with that row (missing
    update -> NOT_AVAILABLE), otherwise kept, and dropped to NOT_AVAILABLE when no longer bound to the row's cover."""
    cfg = config or load_config()
    stale_after = timedelta(days=cfg['stale_after_days'])
    codes = universe_codes()
    kept = previous['records'] if previous is not None else {}
    records, replaced = {}, set()
    for code in codes:
        old = kept.get(code) or empty_record()
        new = updates.get(code)
        if new is not None:
            try:
                _record(code, restate(new, as_of, stale_after), _clock(_iso(as_of)), stale_after)
            except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
                new = empty_record(cik=new.get('cik') if type(new) is dict and type(new.get('cik')) is str and re.fullmatch(r'[0-9]{10}', new['cik']) else None, reasons=('INVALID_INPUT',))
            if is_withdrawal(new):   # only a merge writes a withdrawal; a collected row never is one
                new = empty_record(reasons=('INVALID_INPUT',))
        # A row naming a CIK other than the one fetched is identity conflict evidence of this run.
        conflict = set(conflicts) | ({code} if new is not None and 'CIK_MISMATCH' in new['reason_codes'] else set())
        observed = lambda r: r['listing_id'] is not None and not (code in transient and r['shares'] is None)
        if withdrawal_stays(old, new, code=code, conflicts=conflict, observed=observed):
            note_withdrawal(stats, old, old, code)
            records[code] = restate(old, as_of, stale_after)
            continue
        decision = previous_decision(old, new, code=code, unresolved=unresolved, conflicts=conflict, new_observation=observed)
        note(stats, decision, code, old)
        if decision == PRESERVE:
            pass
        elif decision == LISTING_ENDED:
            old = ended_row(old, empty_record)
        elif decision == IDENTITY_CONFLICT and (new is None or not observed(new)):
            # Identity conflict without this run's collection: the kept observation is withdrawn (UNI-WITHDRAWN); without
            # one, unresolved (no row this run) or this run's NA row, never an invented time.
            chosen = withdrawal(old, empty_record, detected_at=as_of) or (new if new is not None else empty_record(reasons=('CIK_UNRESOLVED',)))
            note_withdrawal(stats, old, chosen, code)
            old = chosen
            replaced.add(code)
        elif decision == IDENTITY_CONFLICT or replaces(new, old, observed=observed, has_value=lambda r: r['shares'] is not None):
            old = new
            replaced.add(code)
        elif new is None and code in unresolved and old['shares'] is None:
            old = empty_record(reasons=('CIK_UNRESOLVED',))
        records[code] = restate(old, as_of, stale_after)
    kept_unlisted = (previous or {}).get('unlisted_classes') or {}
    unlisted = {}
    for gid, group in _unlisted_groups().items():
        code = group['unlisted']['valued_at']
        if code in replaced:
            entry = (unlisted_updates or {}).get(gid) or empty_unlisted(group, ('UNLISTED_CLASS_SHARES_NOT_AVAILABLE',))
        else:
            entry = kept_unlisted.get(gid) or empty_unlisted(group)
        try:
            entry = restate_unlisted(group, entry, records[code])
            _unlisted_entry(group, entry, records)
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
            entry = empty_unlisted(group, ('UNLISTED_CLASS_SHARES_NOT_AVAILABLE',))
        unlisted[gid] = entry
    states = [r['state'] for r in records.values()]
    state = 'LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else 'NOT_AVAILABLE'
    payload = {'schema_version': SCHEMA_VERSION, 'kind': KIND, 'as_of': _iso(as_of), 'config_version': cfg['config_version'],
               'config_status': cfg['config_status'], 'freshness_basis': 'SOURCE_ACQUISITION',
               'stale_after_seconds': int(stale_after.total_seconds()), 'shard_count': cfg['shard_count'],
               'last_shard_index': shard_index, 'registry_sha256': registry_sha256 if registry_sha256 is not None else (previous or {}).get('registry_sha256'),
               'code_count': len(records), 'state': state,
               'reason_codes': [] if state == 'LIVE' else ['STALE_INPUT'] if state == 'STALE' else ['NO_ELIGIBLE_INPUT'],
               'records': records, 'unlisted_classes': unlisted}
    require_universe_shares(payload)
    return payload


def _record(code, r, cut, ttl, *, withdrawals=True):
    withdrawn = is_withdrawal(r)
    if withdrawn:
        _need(withdrawals)   # only in a schema-version-2 file
        require_withdrawal(r, cut, empty_record)
    _need(type(r) is dict and set(r) == set(RECORD_KEYS) | (set(WITHDRAWAL_KEYS) if withdrawn else set()))
    venue, symbol = _sec_symbol(code)
    _need(r['cik'] is None or type(r['cik']) is str and re.fullmatch(r'[0-9]{10}', r['cik']) is not None and r['cik'] != '0000000000')
    mic = {'NASDAQ': 'XNAS', 'NYSE': 'XNYS'}.get(venue)
    _need(r['listing_id'] is None or (mic is not None and r['cik'] is not None and r['listing_id'] == f'{mic}:{symbol}:{r["cik"]}'))
    _need(r['company_id'] is None or type(r['company_id']) is str and re.fullmatch(r'[a-z0-9_]{1,64}', r['company_id']) is not None)
    _need((r['listing_id'] is None) == (r['company_id'] is None))
    _need(r['shares'] is None or _positive(r['shares']) and type(r['shares']) is not bool)
    for key in ('measurement_date', 'filed'):
        _need(r[key] is None or _day(r[key]) is not None)
    _need(r['accn'] is None or type(r['accn']) is str and re.fullmatch(r'\d{10}-\d{2}-\d{6}', r['accn']) is not None)
    _need(r['form'] is None or r['form'] in FORMS)
    _need(r['concept'] is None or r['concept'] in CONCEPTS)
    _need(r['acquired_at'] is None or _clock(r['acquired_at']) <= cut)
    _need(r['share_class_basis'] in BASES and r['state'] in STATES)
    e = r['basis_evidence']
    _need(type(e) is dict and set(e) == set(EVIDENCE_KEYS))
    _need(e['cover_accn'] is None or type(e['cover_accn']) is str and re.fullmatch(r'\d{10}-\d{2}-\d{6}', e['cover_accn']) is not None)
    members = e['class_members']
    _need(type(members) is list and len(members) <= 16 and all(type(m) is str and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,127}', m) for m in members))
    _need(members == sorted(set(members)))
    _need(e['class_count'] is None and not members or type(e['class_count']) is int and e['class_count'] == len(members))
    _need(e['listing_class_member'] is None or e['listing_class_member'] in members)
    h = r['source_sha256']
    _need(type(h) is dict and set(h) == set(HASH_KEYS) and all(v is None or _hash(v) for v in h.values()))
    reasons = r['reason_codes']
    _need(type(reasons) is list and len(reasons) == len(set(reasons)) <= 4
          and all(x in REASONS or withdrawn and x == WITHDRAWN_REASON for x in reasons))
    filing_keys = ('measurement_date', 'accn', 'form', 'filed', 'concept')
    # Identity rows carry their own capture time and SEC hashes even when no count is published.
    _need(r['listing_id'] is None or (r['acquired_at'] is not None and h['companyfacts'] and h['submissions']))
    if r['shares'] is None:
        _need(r['state'] == 'NOT_AVAILABLE' and reasons and all(r[k] is None for k in filing_keys))
        _need(r['share_class_basis'] == 'BASIS_UNCONFIRMED')
    else:
        _need(all(r[k] is not None for k in ('cik', 'listing_id', 'acquired_at', *filing_keys)) and h['companyfacts'] and h['submissions'])
        _need(_day(r['measurement_date']) <= _day(r['filed']) <= _clock(r['acquired_at']).date())
        fresh = cut - _clock(r['acquired_at']) <= ttl
        _need(r['state'] == ('LIVE' if fresh else 'STALE') and (('STALE_INPUT' in reasons) == (not fresh)))
    if r['share_class_basis'] == 'SINGLE_CLASS_CONFIRMED':
        _need(h['cover'] and e['cover_accn'] == r['accn'] and len(members) <= 1 and 'SHARE_CLASS_BASIS' not in reasons)
    elif r['share_class_basis'] == 'SHARE_CLASS_BASIS':
        _need(h['cover'] and e['cover_accn'] == r['accn'] and len(members) >= 2 and e['listing_class_member'] is not None)
        _need('SHARE_CLASS_BASIS' in reasons and r['concept'] == CONCEPTS[0])
    else:
        _need(bool(set(reasons) - {'STALE_INPUT'}) and 'SHARE_CLASS_BASIS' not in reasons)
    return r['state']


def _unlisted_entry(group, e, records):
    """One `unlisted_classes` entry: bound to the valued-at listing row's cover filing, or NOT_AVAILABLE with no count."""
    _need(type(e) is dict and set(e) == set(UNLISTED_KEYS))
    _need(e['cik'] == group['cik'] and e['valued_at'] == group['unlisted']['valued_at'])
    reasons = e['reason_codes']
    _need(type(reasons) is list and len(reasons) == len(set(reasons)) <= 4 and all(x in UNLISTED_REASONS for x in reasons))
    classes = e['classes']
    _need(type(classes) is list and len(classes) <= 15)
    if not classes:
        _need(e['state'] == 'NOT_AVAILABLE' and reasons and 'STALE_INPUT' not in reasons)
        _need(e['accn'] is None and e['measurement_date'] is None and e['cover_sha256'] is None)
        return e['state']
    r = records[e['valued_at']]
    evidence = r['basis_evidence']
    _need(r['share_class_basis'] == 'SHARE_CLASS_BASIS' and r['shares'] is not None and r['cik'] == e['cik'])
    _need(_hash(e['cover_sha256']) and e['cover_sha256'] == r['source_sha256']['cover'])
    _need(e['accn'] == r['accn'] and e['measurement_date'] == r['measurement_date'])
    _need(e['state'] == r['state'] and reasons == (['STALE_INPUT'] if r['state'] == 'STALE' else []))
    names = []
    for c in classes:
        _need(type(c) is dict and set(c) == {'class_member', 'shares'})
        name = c['class_member']
        _need(type(name) is str and name in evidence['class_members'] and name != evidence['listing_class_member'])
        _need(_positive(c['shares']) and type(c['shares']) is not bool)
        names.append(name)
    _need(names == sorted(set(names)) and len(names) < len(evidence['class_members']))
    # A class listed by any group row from the same cover filing is not unlisted.
    listed = {records[c]['basis_evidence']['listing_class_member'] for c in group['codes']
              if type(records.get(c)) is dict and records[c]['share_class_basis'] == 'SHARE_CLASS_BASIS' and records[c]['accn'] == e['accn']}
    _need(not listed & set(names))
    return e['state']


def require_universe_shares(payload):
    """Strict public validator (also used by the Pages guard). Fixed error only."""
    try:
        _need(type(payload) is dict and set(payload) == set(TOP_KEYS))
        cfg = load_config()
        version = schema_version_of(payload)
        _need(payload['kind'] == KIND)
        cut = _clock(payload['as_of'])
        _need(payload['config_version'] == cfg['config_version'] and payload['config_status'] == cfg['config_status'])
        _need(payload['freshness_basis'] == 'SOURCE_ACQUISITION')
        ttl = payload['stale_after_seconds']
        _need(type(ttl) is int and 0 < ttl <= 366 * 86400)
        _need(type(payload['shard_count']) is int and 1 <= payload['shard_count'] <= 366)
        index = payload['last_shard_index']
        _need(index is None or type(index) is int and 0 <= index < payload['shard_count'])
        _need(payload['registry_sha256'] is None or _hash(payload['registry_sha256']))
        records = payload['records']
        codes = universe_codes()
        _need(type(records) is dict and set(records) == set(codes) and payload['code_count'] == len(codes))
        states = [_record(code, records[code], cut, timedelta(seconds=ttl), withdrawals=version >= 2) for code in codes]
        state = 'LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else 'NOT_AVAILABLE'
        _need(payload['state'] == state)
        groups = _unlisted_groups()
        unlisted = payload['unlisted_classes']
        _need(type(unlisted) is dict and set(unlisted) == set(groups))
        for gid, group in groups.items():
            _unlisted_entry(group, unlisted[gid], records)
        top = payload['reason_codes']
        _need(type(top) is list and all(x in TOP_REASONS for x in top) and len(top) == len(set(top)))
        return payload
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise ValueError('SEC_UNIVERSE_SHARES_INVALID') from None


def parse_json(body):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('SEC_UNIVERSE_SHARES_INVALID')
            out[key] = value
        return out
    def constant(_):
        raise ValueError('SEC_UNIVERSE_SHARES_INVALID')
    try:
        if type(body) is not bytes or len(body) > MAX_BYTES:
            raise ValueError
        return json.loads(body.decode('utf-8', errors='strict'), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError('SEC_UNIVERSE_SHARES_INVALID') from None


def encode(payload):
    require_universe_shares(payload)
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()
