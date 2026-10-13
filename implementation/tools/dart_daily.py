#!/usr/bin/env python3
"""Daily OpenDART step for 한미반도체 (KRX 042700) -> `dart-disclosures.json` + `dart-financials.json` in --out.

Reads the key only from the env slot DART_API_KEY and sends it only as OpenDART's
`crtfc_key` query parameter. Prints only fixed codes and counts: never the key,
a request URL, a response body or an upstream message. Each run has a hard call
budget (default 30, at most 50, documented personal limit 20,000/day); when it
is spent no further request is sent and the unfinished part is NOT_AVAILABLE.

Source-side failures (missing key, OpenDART status codes, network, budget,
CORP_CODE_UNCONFIRMED) publish NOT_AVAILABLE with the fixed reason and exit 0,
so the SEC daily deployment is not blocked; an invalid local output exits 1.
`--preserve-only` (UI-only deploys) restores the validated live Pages copies
byte-identically; 404 keeps the offline NOT_AVAILABLE files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.product import dart_public as dp
from investment_system.providers import dart_collection as dc

PAGES_BASE = 'https://kco994553-star.github.io/Investment-System1/'
ANNUAL_LOOKBACK_DAYS = 500
_ORDER = {'Q1': 1, 'HALF': 2, 'Q3': 3, 'ANNUAL': 4}


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        print('DART_DAILY ARGUMENTS_INVALID')
        raise SystemExit(2)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def write(directory, name, body):
    directory = Path(directory)
    destination = directory / name
    if directory.is_symlink() or not directory.is_dir() or destination.is_symlink():
        raise ValueError('DART_OUTPUT_INVALID')
    with tempfile.NamedTemporaryFile(dir=directory, prefix='.dart-', delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(body)
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def emit(directory, *, as_of=None):
    """Offline NOT_AVAILABLE files (used by build_pages_cockpit)."""
    as_of = as_of or dc.utc_now()
    write(directory, dp.DISCLOSURES_FILENAME, dp.encode(dp.DISCLOSURES_FILENAME, dp.empty_disclosures(as_of.replace(microsecond=0))))
    write(directory, dp.FINANCIALS_FILENAME, dp.encode(dp.FINANCIALS_FILENAME, dp.empty_financials(as_of)))


# ---------------------------------------------------------------- collection


class _Stop(Exception):
    """A fatal code was seen: no further request in this run."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _guard(call, failures):
    """Run one part; non-fatal codes become that part's reason, fatal codes stop the run."""
    try:
        return call(), None
    except dc.DartCollectionError as error:
        failures.append(error.code)
        if error.fatal:
            raise _Stop(error.code) from None
        return None, error.code


def _report_block(client, corp_code, report, periodic_rows, *, annual):
    period, year, code = report['period'], report['bsns_year'], report['reprt_code']
    payload, fs_div = dc.fetch_statements(client, corp_code, bsns_year=year, reprt_code=code)
    receipts = {r.get('rcept_no') for r in payload.get('list', []) if isinstance(r, dict)}
    if len(receipts) != 1:
        raise dc.DartCollectionError('DART_FINANCIALS_INVALID')
    rcept_no = receipts.pop()
    listed = [r for r in periodic_rows if r['rcept_no'] == rcept_no]
    if (len(listed) != 1 or dc.periodic_report(listed[0]['report_nm']) != (period, year, code)
            or not dp.valid_title(dc.clean_title(listed[0]['report_nm']))):
        raise dc.DartCollectionError('DART_IDENTITY_MISMATCH')
    values, concepts, reasons = dc.extract_financials(payload, reprt_code=code)
    statements_sha = hashlib.sha256(dc.canonical_body(payload)).hexdigest()
    shares, shares_sha = None, None
    try:
        shares_payload = client.json('stockTotqySttus.json', {'corp_code': corp_code, 'bsns_year': year, 'reprt_code': code})
    except dc.DartCollectionError as error:
        if error.fatal:
            raise
        shares_payload = None  # Shares only: the statements stay published, shares NOT_AVAILABLE.
    if shares_payload is not None:
        shares = dc.extract_shares(shares_payload)
        shares_sha = hashlib.sha256(dc.canonical_body(shares_payload)).hexdigest()
    values['shares'], concepts['shares'] = shares, ('stockTotqySttus.distb_stock_co' if shares is not None else None)
    if shares is None:
        reasons['shares'] = 'MISSING'
    row = listed[0]
    block_reasons = (['SEPARATE_STATEMENTS_FALLBACK'] if fs_div == 'OFS' else []) + (['SHARES_NOT_AVAILABLE'] if shares is None else [])
    return {'state': 'LIVE', 'reason_codes': block_reasons, 'rcept_no': rcept_no, 'report_name': dc.clean_title(row['report_nm']),
            'bsns_year': year, 'reprt_code': code, 'period': period, 'fs_div': fs_div,
            'fs_label': 'CONSOLIDATED' if fs_div == 'CFS' else 'SEPARATE_FALLBACK',
            'filed_at': f"{row['rcept_dt'][:4]}-{row['rcept_dt'][4:6]}-{row['rcept_dt'][6:]}",
            'basis': 'FISCAL_YEAR' if annual else 'YEAR_TO_DATE',
            'inputs': {n: values.get(n) for n in dp.INPUT_NAMES},
            'concepts': {n: concepts.get(n) if values.get(n) is not None or reasons.get(n) in ('AMBIGUOUS', 'UNPARSEABLE') else None for n in dp.INPUT_NAMES},
            'missing': {n: None if values.get(n) is not None else reasons.get(n, 'MISSING') for n in dp.INPUT_NAMES},
            'source_sha256': {'statements': statements_sha, 'shares': shares_sha}}


def _latest_reports(periodic_rows):
    """Latest annual report and the latest interim report newer than it, from typed (A) list rows."""
    found = {}
    for row in periodic_rows:
        parsed = dc.periodic_report(row['report_nm'])
        if parsed is None:
            continue
        period, year, code = parsed
        key = (int(year), _ORDER[period])
        if key not in found or (row['rcept_dt'], row['rcept_no']) > (found[key]['rcept_dt'], found[key]['rcept_no']):
            found[key] = {'period': period, 'bsns_year': year, 'reprt_code': code, 'rcept_dt': row['rcept_dt'], 'rcept_no': row['rcept_no']}
    annual = max((k for k in found if k[1] == 4), default=None)
    interim = max((k for k in found if k[1] != 4 and (annual is None or k > annual)), default=None)
    return (found[annual] if annual else None), (found[interim] if interim else None)


def collect(client, *, now, previous_events=()):
    """Collected parts: ({cid: disclosure company}, [events], {cid: financial company}, failure codes).

    Never raises DartCollectionError. A company/part that fails is NOT_AVAILABLE with its fixed code, and
    after a fatal code (key, limit, budget, network, CORP_CODE_UNCONFIRMED) no further request is sent."""
    disclosures = {cid: dp.empty_company(code) for cid, code in dp.COMPANIES.items()}
    financials = {cid: dp.empty_financial_company(code) for cid, code in dp.COMPANIES.items()}
    events, failures, stopped = [], [], None
    acquired = dp.instant(now)
    for cid, stock_code in dp.COMPANIES.items():
        target = dc.KR_TARGETS[cid]
        company = financials[cid]
        corp_code = None
        try:
            if stopped:
                raise _Stop(stopped)
            corp_code, code = _guard(lambda: dc.resolve_corp_code(client.corp_code_zip(), stock_code=stock_code,
                                                                  corp_name=target['corp_name']), failures)
            if corp_code is None:
                disclosures[cid] = dp.empty_company(stock_code, code)
                financials[cid] = dp.empty_financial_company(stock_code, [code])
                continue
            end = dc.kst_today(now)
            begin = end - timedelta(days=dp.WINDOW_DAYS)

            def lists():
                rows, truncated = [], False
                periodic, cut = dc.list_disclosures(client, corp_code, stock_code=stock_code, pblntf_ty='A',
                                                    begin=end - timedelta(days=ANNUAL_LOOKBACK_DAYS), end=end)
                truncated |= cut
                rows += [{**r, 'report_type': 'A'} for r in periodic]
                for kind in ('B', 'I', None):
                    found, cut = dc.list_disclosures(client, corp_code, stock_code=stock_code, pblntf_ty=kind, begin=begin, end=end)
                    truncated |= cut
                    rows += [{**r, 'report_type': kind} for r in found]
                return periodic, rows, truncated

            listed, code = _guard(lists, failures)
            if listed is None:
                disclosures[cid] = dp.empty_company(stock_code, code)
                financials[cid] = dp.empty_financial_company(stock_code, [code])
                continue
            periodic_rows, rows, truncated = listed
            found, dropped = dp.build_events(cid, [{'rcept_no': r['rcept_no'], 'rcept_dt': r['rcept_dt'], 'title': dc.clean_title(r['report_nm']),
                                                    'report_type': r['report_type']} for r in rows], as_of=now, previous_events=previous_events)
            events += found
            disclosures[cid] = {'state': 'LIVE', 'acquired_at': acquired,
                                'reason_code': 'DART_LIST_TRUNCATED' if truncated else 'RECORDS_DROPPED_INVALID' if dropped else None,
                                'stock_code': stock_code, 'corp_code': corp_code, 'corp_code_basis': 'CORPCODE_XML', 'truncated': truncated}
            annual_report, interim_report = _latest_reports(periodic_rows)
            for key, report, is_annual in (('annual', annual_report, True), ('latest_interim', interim_report, False)):
                if report is None:
                    company[key] = dp.empty_report(['NO_PERIODIC_REPORT' if is_annual else 'NO_NEWER_INTERIM_REPORT'])
                    continue
                block, code = _guard(lambda: _report_block(client, corp_code, report, periodic_rows, annual=is_annual), failures)
                company[key] = block if block is not None else dp.empty_report([code])
        except _Stop as stop:
            stopped = stop.code
            if disclosures[cid]['state'] != 'LIVE':
                disclosures[cid] = dp.empty_company(stock_code, stop.code)
            for key in ('annual', 'latest_interim'):
                if company[key]['state'] != 'LIVE' and company[key]['reason_codes'] == ['NOT_COLLECTED']:
                    company[key] = dp.empty_report([stop.code])
        live = company['annual']['state'] == 'LIVE' or company['latest_interim']['state'] == 'LIVE'
        if live:
            company.update(corp_code=corp_code, state='LIVE', reason_codes=[], acquired_at=acquired)
        else:
            reasons = sorted({c for b in (company['annual'], company['latest_interim']) for c in b['reason_codes']} - {'NOT_COLLECTED', stopped})
            company.update(corp_code=None, state='NOT_AVAILABLE', acquired_at=None,
                           reason_codes=(([stopped] if stopped else []) + reasons)[:8] or ['NOT_COLLECTED'])
        company['qg'] = dp.compute_qg(cid, company['annual'])
        financials[cid] = company
    return disclosures, events, financials, failures


def carry_forward(disclosures, events, financials, previous_disclosures, previous_financials):
    """A company not collected this run keeps its previous published rows and acquisition time (STALE after 48h)."""
    for cid in dp.COMPANIES:
        if disclosures[cid]['acquired_at'] is None and previous_disclosures is not None:
            old = previous_disclosures['companies'][cid]
            if old['acquired_at'] is not None:
                disclosures[cid] = dict(old)
                events += [dict(e) for e in previous_disclosures['events'] if e['company_id'] == cid]
        if financials[cid]['acquired_at'] is None and previous_financials is not None:
            old = previous_financials['companies'][cid]
            if old['acquired_at'] is not None:
                financials[cid] = json.loads(json.dumps(old))
    return disclosures, events, financials


def fetch_previous(name, *, open_response=None):
    """(original bytes, validated payload) of the live Pages copy, None on 404. ValueError otherwise."""
    fetch = open_response or urllib.request.build_opener(NoRedirect()).open
    url = PAGES_BASE + name
    request = urllib.request.Request(url, headers={'Accept': 'application/json', 'Cache-Control': 'no-cache'})
    try:
        with fetch(request, timeout=20) as response:
            if response.status != 200 or response.geturl() != url:
                raise ValueError('DART_PREVIOUS_INVALID')
            body = response.read(dp.MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise ValueError('DART_PREVIOUS_FETCH_FAILED') from None
    except (urllib.error.URLError, OSError):
        raise ValueError('DART_PREVIOUS_FETCH_FAILED') from None
    return body, dp.require_public(name, dp.parse_json(body))


def run(out, *, environ=None, transport=None, now=None, max_calls=dc.DEFAULT_MAX_CALLS, open_previous=None):
    environ = os.environ if environ is None else environ
    now = (now or dc.utc_now()).replace(microsecond=0)
    key = environ.get(dc.DART_API_KEY_SLOT) or ''
    budget = dc.CallBudget(max_calls)

    def say(line):
        print(dc.mask_secret(line, key))
    previous = {}
    for name in dp.FILENAMES:
        try:
            found = fetch_previous(name, open_response=open_previous)
            previous[name] = found[1] if found else None
            say(f"DART_PREVIOUS file={name} state={'NOT_FOUND' if found is None else 'VALID'}")
        except Exception:  # noqa: BLE001 - previous copies are optional; only a fixed code is printed.
            previous[name] = None
            say(f'DART_PREVIOUS file={name} state=UNAVAILABLE')
    failures = []
    try:
        client = dc.DartClient(key, budget=budget, transport=transport)
    except dc.DartCollectionError as error:
        client, failures = None, [error.code]
    try:
        if client is None:
            disclosures = {cid: dp.empty_company(code, failures[0]) for cid, code in dp.COMPANIES.items()}
            financials = {cid: dp.empty_financial_company(code, failures) for cid, code in dp.COMPANIES.items()}
            events = []
        else:
            disclosures, events, financials, failures = collect(
                client, now=now, previous_events=(previous[dp.DISCLOSURES_FILENAME] or {}).get('events', ()))
        disclosures, events, financials = carry_forward(disclosures, events, financials, previous[dp.DISCLOSURES_FILENAME],
                                                        previous[dp.FINANCIALS_FILENAME])
        cutoff = (now.astimezone(dp.KST).date() - timedelta(days=dp.WINDOW_DAYS)).isoformat()
        events = [e for e in events if e['filing_date'] >= cutoff]
        disclosure_payload = dp.disclosures_payload(as_of=now, companies=disclosures, events=events,
                                                    api_calls=budget.used, api_call_budget=budget.limit)
        financial_payload = dp.financials_payload(as_of=now, companies=financials)
        bodies = {dp.DISCLOSURES_FILENAME: dp.encode(dp.DISCLOSURES_FILENAME, disclosure_payload),
                  dp.FINANCIALS_FILENAME: dp.encode(dp.FINANCIALS_FILENAME, financial_payload)}
        if key and any(key.encode() in body for body in bodies.values()):
            say(f'DART_COLLECTION_FAILED code=DART_OUTPUT_REJECTED calls={budget.used}')
            return 1
        for name, body in bodies.items():
            write(out, name, body)
    except Exception:  # noqa: BLE001 - only a fixed code is printed.
        say(f'DART_COLLECTION_FAILED code=DART_OUTPUT_INVALID calls={budget.used}')
        return 1
    events = disclosure_payload['events']
    for cid, company in disclosure_payload['companies'].items():
        rows = [e for e in events if e['company_id'] == cid]
        say(f"DART_DISCLOSURES company={cid} state={company['state']} events={len(rows)}"
            f" new={sum(e['occurrence'] == 'NEW' for e in rows)} results={sum(e['classification'] == 'RESULTS' for e in rows)}"
            f" truncated={int(company['truncated'])} reason={company['reason_code'] or '-'}")
    for cid, company in financial_payload['companies'].items():
        annual, interim, qg = company['annual'], company['latest_interim'], company['qg']
        say(f"DART_FINANCIALS company={cid} state={company['state']} annual={annual['state']}:{annual['period'] or '-'}:{annual['fs_div'] or '-'}"
            f" interim={interim['state']}:{interim['period'] or '-'}:{interim['fs_div'] or '-'}"
            f" annual_missing={sum(v is not None for v in annual['missing'].values())}"
            f" qg_scored={sum(f['state'] != 'NOT_AVAILABLE' for f in qg['factors'].values())}"
            f" reasons={','.join(company['reason_codes']) or '-'}")
    say(f'DART_CALLS used={budget.used} budget={budget.limit} hard_max={dc.HARD_MAX_CALLS} documented_daily_limit={dc.DOCUMENTED_DAILY_LIMIT}')
    say('DART_COLLECTION_OK' if not failures else 'DART_COLLECTION_DEGRADED codes=' + ','.join(sorted(set(failures))))
    return 0


# ---------------------------------------------------------------- preserve-only


def preserve(directory, *, open_response=None):
    """Live Pages copies -> validated original bytes in --out. 404 keeps the offline file."""
    bodies = {}
    for name in dp.FILENAMES:
        found = fetch_previous(name, open_response=open_response)
        if found is not None:
            bodies[name] = found[0]
    for name, body in bodies.items():
        write(directory, name, body)
    return len(bodies)


def main(argv=None, *, environ=None, transport=None, now=None, open_response=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--preserve-only', action='store_true')
    parser.add_argument('--max-calls', type=int, default=dc.DEFAULT_MAX_CALLS)
    args = parser.parse_args(argv)
    if not 1 <= args.max_calls <= dc.HARD_MAX_CALLS:
        print('DART_DAILY ARGUMENTS_INVALID')
        return 2
    if args.preserve_only:
        try:
            print(f'DART_PREVIOUS_RESTORED files={preserve(args.out, open_response=open_response)}')
        except Exception:  # noqa: BLE001
            print('DART_PREVIOUS_RESTORE_FAILED')
            return 1
        return 0
    return run(args.out, environ=environ, transport=transport, now=now, max_calls=args.max_calls, open_previous=open_response)


if __name__ == '__main__':
    raise SystemExit(main())
