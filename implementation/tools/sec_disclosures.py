#!/usr/bin/env python3
"""Daily SEC 8-K current reports for the US TARGET companies -> public `sec-disclosures.json`.

Queue 2.2 a/d/e. Through the paced SEC client: one submissions JSON per company, then the
filing index page of each new 8-K to find Exhibit 99.1 (title, link, release time only).
The previous Pages copy is carried forward on a rolling window:

- 404 -> start fresh; an invalid previous copy -> discarded (PREVIOUS_DISCARDED);
- network failure reading the previous copy -> nothing written, exit 1;
- --preserve-only (UI-only deploys, cockpit-pages.yml only) -> the validated previous copy re-published byte for byte
  (its as_of and states as published, never restated at the deploy time), no SEC requests.

Only the secret slot name SEC_USER_AGENT is read; its value is never printed. Only fixed
codes and counts are printed: no names, titles, URLs or values. No score is changed.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.markets.us import US_LISTINGS
from investment_system.product.sec_disclosures import (FILENAME, MAX_BYTES, WINDOW_DAYS, encode, merge, parse_json,
                                                       pending_exhibits, require_sec_disclosures)
from investment_system.providers.sec_8k_disclosures import (SecDisclosureClient, current_reports, exhibit_99_1,
    foreign_earnings_candidates, quarterly_earnings_exhibit)
from investment_system.providers.sec_collection import SEC_USER_AGENT_SLOT, SecCollectionError

SOURCE = 'https://kco994553-star.github.io/Investment-System1/' + FILENAME
# Bounded daily filing-index budget; the rest stay NOT_COLLECTED and are retried next run.
MAX_INDEX_FETCHES = 150
FIXED_CODES = frozenset({'SEC_USER_AGENT_INVALID', 'SEC_CONFIG_INVALID', 'SEC_URL_NOT_ALLOWED', 'SEC_REDIRECT_REJECTED',
                         'SEC_RESPONSE_TOO_LARGE', 'SEC_TRANSPORT_FAILED', 'SEC_TRANSPORT_RETRIES_EXHAUSTED',
                         'SEC_HTTP_RETRIES_EXHAUSTED', 'SEC_HTTP_FAILED', 'SEC_RESPONSE_INVALID', 'SEC_RESPONSE_URL_MISMATCH',
                         'SEC_JSON_INVALID', 'SEC_CIK_MISMATCH', 'SEC_ISSUER_NOT_ALLOWED', 'SEC_CLOCK_INVALID',
                         'SEC_SLEEP_FAILED', 'SEC_RETRY_AFTER_EXCEEDS_BUDGET'})


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        print('SEC_8K_DISCLOSURES ARGUMENTS_INVALID')
        raise SystemExit(2)


def _utc_now():
    return datetime.now(timezone.utc)


def _code(error):
    code = error.args[0] if isinstance(error, SecCollectionError) and len(error.args) == 1 else None
    if isinstance(code, str) and code.startswith('SEC_HTTP_') and code[9:].isdigit():
        return code
    return code if code in FIXED_CODES else 'SEC_8K_FAILED'


def fetch_previous(*, open_response=None):
    """Live Pages copy -> validated payload; None on 404. Network errors raise OSError, invalid copies ValueError."""
    return _previous(open_response)[0]


def _previous(open_response=None):
    """(validated payload, live bytes); (None, None) on 404. Network errors raise OSError, invalid copies ValueError."""
    request = urllib.request.Request(SOURCE, headers={'Accept': 'application/json', 'Cache-Control': 'no-cache'})
    fetch = open_response or urllib.request.build_opener(NoRedirect()).open
    try:
        with fetch(request, timeout=20) as response:
            if response.status != 200 or response.geturl() != SOURCE:
                raise OSError('PREVIOUS_FETCH_FAILED')
            body = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None, None
        raise OSError('PREVIOUS_FETCH_FAILED') from None
    except (urllib.error.URLError, OSError, ValueError):
        raise OSError('PREVIOUS_FETCH_FAILED') from None
    return require_sec_disclosures(parse_json(body)), body


def write(directory, payload):
    return write_bytes(directory, encode(require_sec_disclosures(payload)))


def write_bytes(directory, body):
    directory = Path(directory)
    destination = directory / FILENAME
    if directory.is_symlink() or not directory.is_dir() or destination.is_symlink():
        raise ValueError('SEC_DISCLOSURES_OUTPUT_INVALID')
    if len(body) > MAX_BYTES:
        raise ValueError('SEC_DISCLOSURES_OUTPUT_INVALID')
    with tempfile.NamedTemporaryFile(dir=directory, prefix='.sec-disclosures-', delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(body)
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return body


def emit_empty(directory, *, now=_utc_now):
    """Offline/PR builds: a NOT_AVAILABLE copy without SEC data, replaced by the live or preserve step."""
    return write(directory, merge(None, {}, as_of=now()))


def collect(client, previous, *, now=_utc_now):
    """Returns (collected, exhibits, counts). Per-company failures are counted with fixed codes."""
    started = now()
    since = (started - timedelta(days=WINDOW_DAYS)).date()
    collected, failures, exhibits, foreign_checked = {}, [], {}, 0
    counts = {'excluded': 0, 'conflicts': 0, 'unknown_items': 0}
    for index, cid in enumerate(sorted(US_LISTINGS), start=1):
        try:
            body, acquired = client.submissions(cid)
            submissions = json.loads(body)
            rows, row_counts = current_reports(cid, submissions, acquired_at=acquired, since=since)
            for candidate in foreign_earnings_candidates(cid, submissions, acquired_at=acquired, since=since)[:MAX_INDEX_FETCHES - foreign_checked]:
                foreign_checked += 1
                try:
                    found = quarterly_earnings_exhibit(cid, candidate['accession'], client.filing_index(cid, candidate['accession']))
                except SecCollectionError:
                    failures.append((index, 'ASML_6K_INDEX_UNAVAILABLE'))
                    continue
                if isinstance(found, dict):
                    rows.append(candidate)
                    exhibits[candidate['accession']] = found
                else:
                    failures.append((index, 'ASML_6K_EARNINGS_UNCONFIRMED'))
        except SecCollectionError as error:
            failures.append((index, _code(error)))
            continue
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            failures.append((index, 'SEC_8K_SUBMISSIONS_INVALID'))
            continue
        collected[cid] = {'acquired_at': acquired, 'rows': rows}
        for key in counts:
            counts[key] += row_counts[key]
    due = [(cid, accession) for cid, accession in pending_exhibits(previous, collected) if accession not in exhibits]
    for cid, accession in due[:MAX_INDEX_FETCHES - foreign_checked]:
        try:
            exhibits[accession] = exhibit_99_1(cid, accession, client.filing_index(cid, accession))
        except SecCollectionError:
            exhibits[accession] = 'INDEX_UNAVAILABLE'
    counts.update(companies=len(US_LISTINGS), collected=len(collected), failed=len(failures), failures=failures,
                  index_due=len(due) + foreign_checked, index_fetched=foreign_checked + min(len(due), MAX_INDEX_FETCHES - foreign_checked),
                  exhibits_found=sum(isinstance(x, dict) for x in exhibits.values()))
    return collected, exhibits, counts


def _summary(payload, previous):
    events = payload['events']
    old = {e['accession'] for e in previous['events']} if previous is not None else set()
    by_class = {}
    for e in events:
        by_class[e['classification']] = by_class.get(e['classification'], 0) + 1
    states = [c['state'] for c in payload['companies'].values()]
    return (f"state={payload['state']} live={states.count('LIVE')} stale={states.count('STALE')} "
            f"not_available={states.count('NOT_AVAILABLE')} events={len(events)} "
            f"new_accessions={sum(e['accession'] not in old for e in events)} "
            f"repeat={sum(e['occurrence'] == 'REPEAT' for e in events)} "
            f"exhibit_99_1={sum(e['exhibit_99_1']['state'] == 'AVAILABLE' for e in events)} "
            + ' '.join(f'{k.lower()}={by_class.get(k, 0)}' for k in ('RESULTS', 'OFFICERS_DIRECTORS', 'MATERIAL_AGREEMENT',
                                                                      'ACQUISITION_DISPOSITION', 'OTHER')))


def run(out, *, live, preserve_only=False, environ=None, now=_utc_now, client_kwargs=None, open_previous=None):
    environ = os.environ if environ is None else environ
    try:
        previous, previous_body = _previous(open_previous)
    except ValueError:
        print('SEC_8K_DISCLOSURES PREVIOUS_DISCARDED')
        previous = previous_body = None
    except Exception:
        print('SEC_8K_DISCLOSURES PREVIOUS_FETCH_FAILED nothing_written')
        return 1
    if preserve_only:
        if previous is None:
            print('SEC_8K_DISCLOSURES PREVIOUS_NOT_AVAILABLE')
            return 0
        # The live copy, validated, is re-published byte for byte: nothing was collected, so its as_of and every
        # state stay as published (never restated at the deploy time). Only cockpit-pages.yml passes --preserve-only.
        try:
            write_bytes(out, previous_body)
        except Exception:
            print('SEC_8K_DISCLOSURES OUTPUT_FAILED')
            return 1
        print(f"SEC_8K_DISCLOSURES PREVIOUS_RESTORED events={len(previous['events'])} state={previous['state']}")
        return 0
    if not live:
        print('SEC_8K_DISCLOSURES LIVE_OPT_IN_REQUIRED')
        return 1
    agent = environ.get(SEC_USER_AGENT_SLOT)
    if not agent:
        print('SEC_8K_DISCLOSURES COLLECTION_NOT_RUN code=SEC_USER_AGENT_MISSING')
        return 1
    try:
        client = SecDisclosureClient(agent, **(client_kwargs or {}))
        collected, exhibits, counts = collect(client, previous, now=now)
    except SecCollectionError as error:
        print('SEC_8K_DISCLOSURES COLLECTION_NOT_RUN code=' + _code(error))
        return 1
    except Exception:
        print('SEC_8K_DISCLOSURES COLLECTION_NOT_RUN code=SEC_8K_FAILED')
        return 1
    for company_index, code in counts['failures']:
        print(f'SEC_8K_FAILURE company_index={company_index} code={code}')
    if not collected and previous is None:
        print('SEC_8K_DISCLOSURES ALL_FAILED nothing_written')
        return 1
    try:
        payload = merge(previous, collected, as_of=now(), exhibits=exhibits)
        write(out, payload)
    except Exception:
        print('SEC_8K_DISCLOSURES OUTPUT_FAILED nothing_written')
        return 1
    print(f"SEC_8K_DISCLOSURES companies={counts['companies']} collected={counts['collected']} failed={counts['failed']} "
          f"excluded_rows={counts['excluded']} conflicts={counts['conflicts']} unknown_items={counts['unknown_items']} "
          f"index_due={counts['index_due']} index_fetched={counts['index_fetched']} exhibits_found={counts['exhibits_found']} "
          + _summary(payload, previous))
    if not collected:
        print('SEC_8K_DISCLOSURES ALL_FAILED previous_kept')
    return 0


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--preserve-only', action='store_true')
    args = parser.parse_args(argv)
    return run(args.out, live=args.live, preserve_only=args.preserve_only)


if __name__ == '__main__':
    raise SystemExit(main())
