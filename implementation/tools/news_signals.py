#!/usr/bin/env python3
"""Daily news signals for the TARGET companies -> public `news-signals.json` ('뉴스·신호', never a score input).

GDELT DOC 2.0 (one paced query per company, >= 5.5 s apart, at most 40 requests) and the official
IR press-release feeds in product.news_signals.IR_FEEDS (at most 20 requests). Title, link and time
only. The `sec-disclosures.json` already written to --out (previous workflow step) is read to link IR
releases that repeat an 8-K Exhibit 99.1. The previous Pages copy is carried forward:

- 404 -> start fresh; an invalid previous copy -> discarded (PREVIOUS_DISCARDED);
- network failure reading the previous copy -> nothing written (the build's NOT_AVAILABLE copy stays), exit 0;
- source failures -> the company keeps its previous rows (STALE after 48h) or is NOT_AVAILABLE, exit 0,
  so the SEC daily deployment is never blocked by news; only an invalid local output exits 1. The file records each
  company's result of this run (FAILED / NOT_RUN with the fixed code, or UPDATED / NO_NEW_ITEMS) and a per-source
  `refresh` summary, so carried rows are never shown as a successful refresh;
- --preserve-only (UI-only deploys, cockpit-pages.yml only) -> the validated previous copy re-published byte for byte
  (its as_of and states as published, never restated at the deploy time), no source requests.

Only fixed codes and counts are printed: no company names, titles, URLs or upstream messages.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from investment_system.product import news_signals as ns
from investment_system.product.sec_disclosures import FILENAME as SEC_FILENAME, parse_json as parse_sec, require_sec_disclosures
from investment_system.providers import news_feeds as nf

SOURCE = 'https://kco994553-star.github.io/Investment-System1/' + ns.FILENAME
FIXED_CODES = frozenset({'REDIRECT_REJECTED', 'RESPONSE_TOO_LARGE', 'URL_NOT_ALLOWED', 'CONFIG_INVALID', 'TRANSPORT_FAILED',
                         'RESPONSE_INVALID', 'HTTP_429', 'HTTP_FAILED', 'BUDGET_EXHAUSTED', 'CLOCK_INVALID',
                         'GDELT_RESPONSE_INVALID', 'GDELT_RATE_LIMITED', 'IR_FEED_INVALID'})
STOP_GDELT = frozenset({'BUDGET_EXHAUSTED', 'GDELT_RATE_LIMITED', 'HTTP_429'})


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        print('NEWS_SIGNALS ARGUMENTS_INVALID')
        raise SystemExit(2)


def _utc_now():
    return datetime.now(timezone.utc)


def _code(error):
    code = error.args[0] if error.args else None
    return code if code in FIXED_CODES else 'NEWS_SOURCE_FAILED'


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
            body = response.read(ns.MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None, None
        raise OSError('PREVIOUS_FETCH_FAILED') from None
    except (urllib.error.URLError, OSError, ValueError):
        raise OSError('PREVIOUS_FETCH_FAILED') from None
    return ns.require_news_signals(ns.parse_json(body)), body


def read_sec(directory):
    """The validated `sec-disclosures.json` in --out (8-K relation), or None."""
    path = Path(directory) / SEC_FILENAME
    try:
        if path.is_symlink() or not path.is_file():
            return None
        return require_sec_disclosures(parse_sec(path.read_bytes()))
    except (OSError, ValueError):
        return None


def write(directory, payload):
    return write_bytes(directory, ns.encode(ns.require_news_signals(payload)))


def write_bytes(directory, body):
    directory = Path(directory)
    destination = directory / ns.FILENAME
    if directory.is_symlink() or not directory.is_dir() or destination.is_symlink():
        raise ValueError('NEWS_SIGNALS_OUTPUT_INVALID')
    if len(body) > ns.MAX_BYTES:
        raise ValueError('NEWS_SIGNALS_OUTPUT_INVALID')
    with tempfile.NamedTemporaryFile(dir=directory, prefix='.news-signals-', delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(body)
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return body


def emit_empty(directory, *, now=_utc_now):
    """Offline/PR builds: a NOT_AVAILABLE copy without source data, replaced by the live or preserve step."""
    return write(directory, ns.merge(None, {}, as_of=now()))


def _secret_free(row):
    from pages_artifact_guard import SECRET_PATTERNS
    return not any(isinstance(row.get(k), str) and p.search(row[k]) for k in ('title', 'link') for p in SECRET_PATTERNS)


def collect(gdelt, ir, counts):
    """{'GDELT': {...}, 'IR': {...}} collected this run; failures as (source, company_index, code)."""
    collected, failures = {'GDELT': {}, 'IR': {}}, []
    stopped = None
    for index, cid in enumerate(ns.GDELT_COMPANIES, start=1):
        if stopped is not None:
            failures.append(('GDELT', index, 'NOT_RUN_' + stopped))
            continue
        try:
            body, acquired = gdelt.get(nf.gdelt_url(cid), accept='application/json')
            rows = nf.parse_gdelt(body)
        except (nf.NewsFetchError, ValueError) as error:
            code = _code(error)
            failures.append(('GDELT', index, code))
            if code in STOP_GDELT:
                stopped = code
            continue
        kept = []
        for row in rows:
            title = ns.clean_title(row['title'])
            if title is not None and ns.relevant(cid, title):
                kept.append(row)
            else:
                counts['irrelevant'] = counts.get('irrelevant', 0) + 1
        collected['GDELT'][cid] = {'acquired_at': acquired, 'rows': kept[:nf.GDELT_KEEP_PER_COMPANY]}
    feeds = sorted(ns.IR_FEEDS)
    for index, cid in enumerate(feeds, start=1):
        try:
            body, acquired = ir.get(ns.IR_FEEDS[cid]['url'], accept='application/rss+xml, application/atom+xml, application/xml')
            rows = nf.parse_feed(body)
        except (nf.NewsFetchError, ValueError) as error:
            failures.append(('IR', index, _code(error)))
            continue
        dated = [r for r in rows if r['published_at'] is not None]
        counts['invalid'] = counts.get('invalid', 0) + len(rows) - len(dated)
        rows = sorted(dated, key=lambda r: r['published_at'], reverse=True)
        collected['IR'][cid] = {'acquired_at': acquired, 'rows': rows[:nf.IR_KEEP_PER_FEED]}
    for source in collected.values():
        for entry in source.values():
            before = len(entry['rows'])
            entry['rows'] = [r for r in entry['rows'] if _secret_free(r)]
            counts['secret_like'] = counts.get('secret_like', 0) + before - len(entry['rows'])
    return collected, failures


def results(failures):
    """collect() failures -> merge() failures {(source, company_id): ('FAILED'|'NOT_RUN', code)}."""
    ids = {'GDELT': list(ns.GDELT_COMPANIES), 'IR': sorted(ns.IR_FEEDS)}
    out = {}
    for source, index, code in failures:
        kind, code = ('NOT_RUN', code[len('NOT_RUN_'):]) if code.startswith('NOT_RUN_') else ('FAILED', code)
        targets = [(s, cid) for s in ns.SOURCES for cid in ids[s]] if source == 'ALL' else [(source, ids[source][index - 1])]
        for key in targets:
            out[key] = (kind, code)
    return out


def _summary(payload):
    items = payload['items']
    by = {c: sum(i['classification'] == c for i in items) for c in ns.CLASSIFICATIONS}
    refresh = payload['refresh'] or {'result': 'NOT_RUN', 'sources': {}}
    per = ' '.join(f"{s.lower()}_result={r['last_result']}" + (f":{r['last_result_code']}" if r['last_result_code'] else '')
                   + f" {s.lower()}_added={r['new_items']}" for s, r in refresh['sources'].items())
    # occurrence_new / occurrence_repeat count group labels over every published item (carried ones included);
    # *_added counts the items this run added to the file.
    return (f"state={payload['state']} refresh={refresh['result']} {per} items={len(items)} "
            f"gdelt_items={sum(i['source'] == 'GDELT' for i in items)} "
            f"ir_items={sum(i['source'] == 'IR' for i in items)} occurrence_new={sum(i['occurrence'] == 'NEW' for i in items)} "
            f"occurrence_repeat={sum(i['occurrence'] == 'REPEAT' for i in items)} "
            f"related_8k={sum(i['relation'] == 'RELATED_TO_8K' for i in items)} "
            + ' '.join(f'{c.lower()}={by[c]}' for c in ns.CLASSIFICATIONS))


def run(out, *, live, preserve_only=False, now=_utc_now, gdelt_kwargs=None, ir_kwargs=None, open_previous=None):
    try:
        previous, previous_body = _previous(open_previous)
    except ValueError:
        print('NEWS_SIGNALS PREVIOUS_DISCARDED')
        previous = previous_body = None
    except Exception:
        print('NEWS_SIGNALS PREVIOUS_FETCH_FAILED nothing_written')
        return 0
    if preserve_only:
        if previous is None:
            print('NEWS_SIGNALS PREVIOUS_NOT_AVAILABLE')
            return 0
        # The live copy, validated, is re-published byte for byte: nothing was collected, so its as_of and every
        # state stay as published (never restated at the deploy time). Only cockpit-pages.yml passes --preserve-only.
        try:
            write_bytes(out, previous_body)
        except Exception:
            print('NEWS_SIGNALS OUTPUT_FAILED')
            return 1
        print(f"NEWS_SIGNALS PREVIOUS_RESTORED items={len(previous['items'])} state={previous['state']}")
        return 0
    if not live:
        print('NEWS_SIGNALS LIVE_OPT_IN_REQUIRED')
        return 1
    counts = {}
    gdelt = nf.PacedClient(min_interval=nf.GDELT_MIN_INTERVAL, budget=nf.GDELT_REQUEST_BUDGET, **(gdelt_kwargs or {}))
    ir = nf.PacedClient(min_interval=nf.IR_MIN_INTERVAL, budget=nf.IR_REQUEST_BUDGET, **(ir_kwargs or {}))
    try:
        collected, failures = collect(gdelt, ir, counts)
    except Exception:
        collected, failures = {'GDELT': {}, 'IR': {}}, [('ALL', 0, 'NEWS_SOURCE_FAILED')]
    for source, index, code in failures:
        print(f'NEWS_SIGNALS_FAILURE source={source} company_index={index} code={code}')
    sec = read_sec(out)
    try:
        payload = ns.merge(previous, collected, as_of=now(), sec=sec, counts=counts, failures=results(failures))
        write(out, payload)
    except Exception:
        print('NEWS_SIGNALS OUTPUT_FAILED nothing_written')
        return 1
    print(f"NEWS_SIGNALS gdelt_companies={len(ns.GDELT_COMPANIES)} gdelt_collected={len(collected['GDELT'])} "
          f"gdelt_requests={gdelt.used} gdelt_budget={nf.GDELT_REQUEST_BUDGET} ir_feeds={len(ns.IR_FEEDS)} "
          f"ir_collected={len(collected['IR'])} ir_requests={ir.used} sec_reference={'AVAILABLE' if sec else 'NOT_AVAILABLE'} "
          f"rows_irrelevant={counts.get('irrelevant', 0)} rows_invalid={counts.get('invalid', 0)} "
          f"rows_out_of_window={counts.get('out_of_window', 0)} rows_foreign_link={counts.get('foreign_link', 0)} "
          f"rows_secret_like={counts.get('secret_like', 0)} duplicates={counts.get('duplicates', 0)} " + _summary(payload))
    if not collected['GDELT'] and not collected['IR']:
        print('NEWS_SIGNALS ALL_SOURCES_FAILED ' + ('previous_kept' if previous is not None else 'not_available'))
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
