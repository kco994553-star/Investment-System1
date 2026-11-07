"""Ticker-mismatch classification of the 2026-11-01 FV3-PIT-TICKER sample (owner decision 2026-11-01 item 9: "8%는 원인을
분류해 보고하라. 미확인 매핑을 확정 신원으로 쓰지 마라"; plan docs/lab/SEC_ONCE_COLLECTION_PLAN_20261101.md section 9).
Runs once inside the SEC one-time collection (.github/workflows/sec-once-collect.yml), in its own step right after
`collect` (SEC_USER_AGENT only), started with `python -I -S`.

Before any SEC request it requires (1) this attempt's raw-repository preflight marker (the private check of
resume-check) and (2) collect-manifest.json with stopped=NONE. When collect stopped (403 or 429 repeats, request cap, wall
clock, a local disk fault) or left no manifest, it sends NO request, writes an incomplete rows file and prints
TICKERMIX_SKIP: SEC is not asked again by a fresh client right after it refused or throttled the run.

Run 41255597310 counted 209 filings with a cover `dei:TradingSymbol` and 16 of them whose XBRL instance file-name prefix is
not that symbol (case-insensitive), and kept no per-filing rows. This script re-builds exactly that sample with the moved
measurement code (fv3_pit_ticker_measure.py: same 120-issuer panel from the in-repo registry, same 2016-2019 picks from
form.idx, same instance choice and dei reading) and classifies each mismatch by fixed rules, first match wins.
"today" = the issuer's tickers now (registry, stored submissions.zip); "earlier" / "later" = TradingSymbol values (and
prefixes confirmed equal to one) of the same issuer's sample filings of EARLIER / LATER years than this filing.
A TradingSymbol value that lists several symbols ("GOOGL, GOOG", "A and B") is split first.
  NOTATION                 prefix and a symbol are equal once dots, hyphens, spaces and an exchange label ("NYSE:")
                           are removed, or once a several-symbol value is split
  CLASS_SHARE              one trailing class letter apart AND evidence of a class: the separator is written (BRK /
                           BRK.B), or the letter is A, B, C, K or L and the issuer has two or more tickers today or both
                           strings are known tickers of the issuer; or both are today's tickers of an issuer with two or
                           more
  OLD_TICKER               the prefix is a ticker the issuer used BEFORE this filing (an earlier filing's symbol or
                           confirmed prefix), it is NOT one of today's tickers, and it differs from the filing's symbol
  SYMBOL_ODD               the prefix is the issuer's ticker today (or of a later filing): the prefix is normal and the
                           cover symbol value is what differs (another class, a typo, a stale value); never OLD_TICKER
  INLINE_DOC_NAME          the filing is inline XBRL (the instance name follows the company's document name)
  SHORT_NAME_OR_DOC_NAME   not a ticker shape (more than 5 letters or digits, or a digit), a document word (form, annual,
                           report, ...), or a company-name word or initials (form.idx name, submissions.zip names)
  OTHER                    anything else; OTHER_SYMBOL_EMPTY counts the filings whose TradingSymbol has no value
These are rule-based classes, not a person's review, and NONE of them confirms an identity: every row carries
identity_confirmed=false, and the file says it is a source of cause counts only, never of ticker <-> CIK links.
form.idx comes from the files `collect` just stored (the same bytes SEC serves); a missing quarter is fetched as in the
original measurement. Company names and today's tickers come from the stored submissions.zip when it is there.
complete=yes needs: no stop, all 16 quarterly form.idx files read, and no transient per-filing error (HTTP 5xx / 429 /
403, network, truncation, gzip, local read); deterministic ones (SIZE_CAP, BAD_INDEX, HTTP404, PARSE_*) are counted and
allowed, so a re-run does not ask SEC again for them.

Output: fixed count lines only (never a ticker, CIK, company name, URL, User-Agent or exception text):
  TICKERMIX_START panel=<n> years=2016-2019 names=SUBMISSIONS|INDEX_ONLY|RESUMED
  TICKERMIX_SKIP reason=COLLECT_STOPPED|COLLECT_MANIFEST_MISSING   (no request made)
  TICKERMIX_INDEX local=<n> remote=<n>   (quarterly form.idx files read from the stored copy / fetched again)
  PITTICKER overall ... and PITTICKER_ERRORS overall ... (the original format, for comparison with run 41255597310)
  TICKERMIX symbol_filings=<n> prefix_eq_symbol=<n> mismatches=<n> expected_symbol=209 expected_mismatch=16 same=yes|no
  TICKERMIX_CLASSES mismatches=<n> short_name_doc=<n> old_ticker=<n> symbol_odd=<n> class_share=<n> notation=<n>
      inline_doc=<n> other=<n> other_symbol_empty=<n>
  PITTICKER_REQUESTS ... (the original format)
  TICKERMIX_DONE complete=yes|no
  TICKERMIX_STOP reason=<code>   (configuration stop before any request)
Per-filing rows (CIK, accession, symbols, prefix, instance name, class and evidence) go ONLY to the private file
files/ticker-mismatch-rows.json, which the upload step puts in the private release.
Exit 0 ran to the end or skipped (complete or not: the rows file says which), 2 configuration stop, 1 unexpected.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse  # noqa: E402
import gzip  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402
import zipfile  # noqa: E402
import zlib  # noqa: E402
from collections import Counter  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fv3_pit_ticker_measure as pit  # noqa: E402
import sec_once_collect as once  # noqa: E402

EXPECTED_SYMBOL, EXPECTED_MISMATCH = 209, 16          # run 41255597310 (2026-11-01)
CLASSES = ('SHORT_NAME_OR_DOC_NAME', 'OLD_TICKER', 'SYMBOL_ODD', 'CLASS_SHARE', 'NOTATION', 'INLINE_DOC_NAME', 'OTHER')
CLASS_FIELDS = (('short_name_doc', 'SHORT_NAME_OR_DOC_NAME'), ('old_ticker', 'OLD_TICKER'), ('symbol_odd', 'SYMBOL_ODD'),
                ('class_share', 'CLASS_SHARE'), ('notation', 'NOTATION'), ('inline_doc', 'INLINE_DOC_NAME'),
                ('other', 'OTHER'))
# deterministic per-filing errors: counted, allowed for complete=yes (a re-run would get the same answer from SEC)
DETERMINISTIC_ERRORS = ('SIZE_CAP', 'BAD_INDEX', 'HTTP404')
IDENTITY_USE = ('cause counts only (owner decision 2026-11-01 item 9); never an identity source: no row confirms a '
                'ticker <-> CIK link')
DOC_WORDS = ('form', 'annual', 'quarterly', 'report', 'xbrl', 'instance', 'document', 'filing', 'tenk', 'tenq')
NAME_STOP = {'inc', 'incorporated', 'corp', 'corporation', 'co', 'company', 'ltd', 'limited', 'plc', 'llc', 'lp', 'l',
             'p', 'the', 'holdings', 'holding', 'group', 'trust', 'sa', 'nv', 'ag', 'de', 'new'}
_EXCHANGE_LABEL = re.compile(r'^\s*[A-Za-z][A-Za-z .]{1,40}:\s*')
_CLASS_SUFFIX = re.compile(r'[A-Za-z]{1,6}[.\-/ ][A-Za-z]')     # BRK.B, BF-B, RDS/A, MOG A
CLASS_LETTERS = 'abckl'                                        # FOXA, GOOGL, LBTYK, DISCK, ...
_ROWS_SCHEMA = 'sec-once-ticker-mismatch/1'
_LIST_SPLIT = re.compile(r'\s*[,;&]\s*|\s+and\s+', re.I)


def norm(value):
    return re.sub(r'[^a-z0-9]', '', (value or '').lower())


def name_words(name):
    return [w for w in re.findall(r'[a-z0-9]+', (name or '').lower())]


def name_evidence(prefix, names):
    """True when the prefix is a company-name word, the start of the joined name, or the name's initials."""
    p = norm(prefix)
    if not p:
        return False
    for name in names:
        words = name_words(name)
        core = [w for w in words if w not in NAME_STOP] or words
        if not core:
            continue
        if p == core[0] or p in core or (len(p) >= 3 and ''.join(core).startswith(p)):
            return True
        if len(p) >= 2 and ''.join(w[0] for w in core) == p:
            return True
    return False


def split_symbols(values):
    """TradingSymbol values with several symbols in one value split apart ("GOOGL, GOOG", "A and B", "GOOGL/GOOG");
    a slash is a list only when every part has two or more letters or digits (RDS/A stays one class symbol)."""
    out = []
    for value in values:
        for part in _LIST_SPLIT.split(value):
            pieces = part.split('/')
            if len(pieces) > 1 and all(len(norm(x)) >= 2 for x in pieces):
                out.extend(x for x in pieces if norm(x))
            elif norm(part):
                out.append(part)
    return out


def classify(row, known, names):
    """(class, evidence) of one mismatch row. `known`: {'today', 'earlier', 'later'} sets of normalised tickers of the
    issuer (today's; symbols of its sample filings of earlier / later years). See the module docstring for the rules."""
    prefix = row['prefix'] or ''
    p = norm(prefix)
    values = [s for s in row['symbols'] if norm(s)]
    today = set(known.get('today', set())) - {''}
    earlier = set(known.get('earlier', set())) - {''}
    later = set(known.get('later', set())) - {''}
    issuer = today | earlier | later
    evidence = {'notation': False, 'multi_value': False, 'class_share': False, 'known_ticker': None,
                'symbol_known': False, 'issuer_tickers_today': len(today), 'name_match': False,
                'not_ticker_shape': False, 'doc_word': False, 'identity_confirmed': False}
    if not values:
        return 'OTHER', dict(evidence, symbol_empty=True)
    pieces = split_symbols(values)
    evidence['multi_value'] = len(pieces) > len(values)
    cleaned = {norm(_EXCHANGE_LABEL.sub('', s)) for s in pieces} | {norm(s) for s in pieces}
    cleaned.discard('')
    evidence['symbol_known'] = bool(cleaned & issuer)
    if p and p in cleaned:
        return 'NOTATION', dict(evidence, notation=True)
    prefix_separated = bool(_CLASS_SUFFIX.fullmatch(prefix.strip()))
    for piece in pieces:
        s = norm(_EXCHANGE_LABEL.sub('', piece))
        short, long_ = sorted((p, s), key=len)
        if not (short and long_.startswith(short) and len(long_) - len(short) == 1 and long_[-1].isalpha()):
            continue
        separated = prefix_separated or bool(_CLASS_SUFFIX.fullmatch(_EXCHANGE_LABEL.sub('', piece).strip()))
        backed = len(today) >= 2 or (short in issuer and long_ in issuer)
        if separated or (long_[-1] in CLASS_LETTERS and backed):
            return 'CLASS_SHARE', dict(evidence, class_share=True)
    if len(today) >= 2 and p in today and cleaned & today:
        return 'CLASS_SHARE', dict(evidence, class_share=True)
    if p and p in earlier and p not in today:
        return 'OLD_TICKER', dict(evidence, known_ticker='earlier_filing')
    if p and (p in today or p in later):
        return 'SYMBOL_ODD', dict(evidence, known_ticker='today' if p in today else 'later_filing')
    if row['inline']:
        return 'INLINE_DOC_NAME', evidence
    shape = len(p) > 5 or any(c.isdigit() for c in prefix)
    doc = any(p.startswith(w) for w in DOC_WORDS)
    named = name_evidence(prefix, names)
    if shape or doc or named:
        return 'SHORT_NAME_OR_DOC_NAME', dict(evidence, not_ticker_shape=shape, doc_word=doc, name_match=named)
    return 'OTHER', evidence


# ---- inputs ----------------------------------------------------------------------------------------------------------
def local_chunks(path):
    with gzip.open(path, 'rb') as handle:
        yield from iter(lambda: handle.read(once.CHUNK), b'')


def company_names(path, accessions):
    """{accession: company name} from a stored form.idx(.gz) for the wanted accessions (the column between form and CIK)."""
    names, header_done = {}, False
    for line in pit.iter_lines(local_chunks(path)):
        if not header_done:
            header_done = line.startswith(b'-----')
            continue
        parts = line.rsplit(None, 2)
        match = pit._IDX_PATH.fullmatch(parts[2]) if len(parts) == 3 else None
        if match is None or match.group(2).decode('ascii') not in accessions:
            continue
        head = parts[0].strip()
        if head.endswith(match.group(1)):          # the CIK column (a long name can be glued to it)
            head = head[:-len(match.group(1))]
        fields = re.split(rb'\s{2,}', head.strip(), maxsplit=1)
        if len(fields) == 2:
            names[match.group(2).decode('ascii')] = fields[1].decode('latin-1').strip()
    return names


def submissions_info(path, ciks):
    """{cik10: {'tickers': [...], 'names': [...]}} from the stored submissions.zip for the panel CIKs only."""
    info = {}
    try:
        with zipfile.ZipFile(path) as archive:
            members = set(archive.namelist())
            for cik in ciks:
                member = f'CIK{cik}.json'
                if member not in members:
                    continue
                try:
                    data = json.loads(archive.read(member))
                except (ValueError, RuntimeError, NotImplementedError, EOFError, zipfile.BadZipFile, zlib.error):
                    continue
                if not isinstance(data, dict):
                    continue
                tickers = [t for t in data.get('tickers') or [] if isinstance(t, str)]
                names = [data.get('name')] + [f.get('name') for f in data.get('formerNames') or [] if isinstance(f, dict)]
                info[cik] = {'tickers': tickers, 'names': [n for n in names if isinstance(n, str)]}
    except (OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, zlib.error):
        return {}
    return info


def inspect_filing(client, cik, accession, today_tickers):
    """pit.measure_filing with the values kept (for classification); same requests, same choices, same flags."""
    base = f'https://{pit.HOST}/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}/'
    try:
        try:
            names = client.fetch(base + 'index.json', kind='filing_index', cap=pit.INDEX_CAP,
                                 consume=pit.directory_names_json)
        except pit.FetchError as exc:
            if exc.code not in ('HTTP404', 'BAD_INDEX'):
                raise
            names = client.fetch(base + accession + '-index.htm', kind='filing_index', cap=pit.INDEX_CAP,
                                 consume=pit.directory_names_html)
        name, inline = pit.pick_instance(names)
        if name is None:
            return {'no_instance': 1}
        body = client.fetch(base + name, kind='instance', cap=pit.INSTANCE_CAP, consume=pit.read_all)
    except pit.FetchError as exc:
        return {'error': exc.code}
    except pit.Stop:
        raise
    except Exception as exc:  # one odd filing never ends the run; class name only
        return {'error': 'UNEXPECTED_' + type(exc).__name__}
    try:
        facts = pit.scan_instance(body)
        flags = pit.evaluate(name, inline, facts, today_tickers)
    except Exception as exc:
        return {'error': 'PARSE_' + type(exc).__name__}
    return {'flags': flags, 'instance': name, 'inline': bool(inline), 'symbols': list(facts['symbols']),
            'present': bool(facts['present']), 'prefix': pit.name_prefix(name),
            'period': facts['period'].isoformat() if facts['period'] else None}


def year_rows(client, folder, year, order, sources):
    """(rows, names by accession, form_idx_ok, errors) of one year's four quarterly form.idx files."""
    rows, names, ok, errors = [], {}, 0, Counter()
    for quarter in (1, 2, 3, 4):
        path = folder / f'full-index-{year}-QTR{quarter}-form.idx.gz'
        try:
            if path.is_file():
                got, early, unsorted, parsed, bad = pit.form_idx_rows(local_chunks(path), order)
                sources['LOCAL'] += 1
            else:
                url = f'https://{pit.HOST}/Archives/edgar/full-index/{year}/QTR{quarter}/form.idx'
                got, early, unsorted, parsed, bad = client.fetch(url, kind='form_idx', cap=pit.FORM_IDX_CAP,
                                                                 consume=lambda chunks: pit.form_idx_rows(chunks, order))
                client.counts['form_idx_remote'] += 1
                sources['REMOTE'] += 1
        except pit.FetchError as exc:
            errors['FORM_IDX_' + exc.code] += 1
            continue
        except (OSError, EOFError, ValueError):
            errors['FORM_IDX_LOCAL_BAD'] += 1
            continue
        ok += 1
        client.counts['idx_early_stop'] += int(early)
        client.counts['idx_unsorted'] += int(unsorted)
        client.counts['idx_rows'] += parsed
        client.counts['idx_bad_rows'] += bad
        rows.extend(got)
        if path.is_file():
            try:
                names.update(company_names(path, {r[3] for r in got}))
            except (OSError, EOFError, ValueError):
                errors['NAMES_LOCAL_BAD'] += 1
    return rows, names, ok, errors


# ---- run -------------------------------------------------------------------------------------------------------------
def class_counts(rows):
    counts = Counter(row['class'] for row in rows)
    counts['OTHER_SYMBOL_EMPTY'] = sum(1 for row in rows if row['evidence'].get('symbol_empty'))
    return counts


def format_classes(counts, total):
    return ('TICKERMIX_CLASSES mismatches=' + str(int(total)) + ' '
            + ' '.join(f'{field}={int(counts.get(name, 0))}' for field, name in CLASS_FIELDS)
            + f' other_symbol_empty={int(counts.get("OTHER_SYMBOL_EMPTY", 0))}')


def format_compare(symbol, equal, mismatches):
    same = symbol == EXPECTED_SYMBOL and mismatches == EXPECTED_MISMATCH
    return (f'TICKERMIX symbol_filings={int(symbol)} prefix_eq_symbol={int(equal)} mismatches={int(mismatches)} '
            f'expected_symbol={EXPECTED_SYMBOL} expected_mismatch={EXPECTED_MISMATCH} same={"yes" if same else "no"}')


def resumed_rows(work):
    """The rows file when the resume check verified it in this run's own release AND it is complete, else None (an
    incomplete earlier result is classified again; the upload then stores the new file under an a<attempt>- name)."""
    path = once.files_dir(work) / once.ROWS_FILE
    verified = once.verified_resume(work).get(once.ROWS_FILE)
    if verified is None or not path.is_file() or once.sha256_file(path) != verified[0]:
        return None
    data = once.read_json(path)
    return data if isinstance(data, dict) and data.get('schema') == _ROWS_SCHEMA and data.get('complete') is True else None


def run(work, environ, *, opener=None, sleep=time.sleep, clock=time.monotonic, out=print):
    previous = resumed_rows(work)
    if previous is not None:
        rows = previous.get('rows') or []
        summary = previous.get('summary') or {}
        out(f'TICKERMIX_START panel={int(summary.get("panel", 0))} years={pit.YEARS[0]}-{pit.YEARS[-1]} names=RESUMED')
        out(format_compare(summary.get('symbol_filings', 0), summary.get('prefix_eq_symbol', 0), len(rows)))
        out(format_classes(class_counts(rows), len(rows)))
        out(f'TICKERMIX_DONE complete={"yes" if previous.get("complete") is True else "no"}')
        return 0
    agent = environ.get('SEC_USER_AGENT') or ''
    if not agent.strip():
        raise once.ConfigStop('SEC_USER_AGENT_MISSING')
    if not pit.valid_user_agent(agent):
        raise once.ConfigStop('SEC_USER_AGENT_INVALID')
    once.require_preflight(work, environ)   # the raw repository was found private on THIS attempt
    folder = once.files_dir(work)
    collected = once.read_json(Path(work) / 'collect-manifest.json')
    if not isinstance(collected, dict) or collected.get('stopped') != 'NONE':
        # collect stopped (403 / 429 repeats, a cap, a local disk fault) or left nothing: no SEC request at all
        reason = 'COLLECT_MANIFEST_MISSING' if not isinstance(collected, dict) else 'COLLECT_STOPPED'
        stopped = collected.get('stopped') if isinstance(collected, dict) else None
        once.write_json(folder / once.ROWS_FILE, {
            'schema': _ROWS_SCHEMA, 'source_run_compared': 41255597310, 'complete': False,
            'identity_confirmed': False, 'use': IDENTITY_USE,
            'summary': {'skipped': reason, 'collect_stopped': once.code_token(stopped) if stopped else None},
            'rows': [], 'written_at': once.utc_now()})
        out(f'TICKERMIX_SKIP reason={reason}')
        out('TICKERMIX_DONE complete=no')
        return 0
    try:
        pool = pit.load_pool()
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise once.ConfigStop('SAMPLE_INPUT_INVALID') from None
    panel = pit.sample_panel(pool)
    info = submissions_info(folder / 'submissions.zip', panel) if (folder / 'submissions.zip').is_file() else {}
    client = pit.SecClient(agent, opener=opener, sleep=sleep, clock=clock)
    out(f'TICKERMIX_START panel={len(panel)} years={pit.YEARS[0]}-{pit.YEARS[-1]} '
        f'names={"SUBMISSIONS" if info else "INDEX_ONLY"}')
    order = {int(cik): i for i, cik in enumerate(panel)}
    totals, errors, sources, inspected, stopped = Counter(), Counter(), Counter(), [], 'NONE'
    try:
        for year in pit.YEARS:
            totals['sampled'] += len(panel)
            rows, names, ok, year_errors = year_rows(client, folder, year, order, sources)
            totals['form_idx_ok'] += ok
            errors.update(year_errors)
            picks = pit.pick_filings(rows)
            totals['filed'] += len(picks)
            totals['form10k'] += sum(1 for form, _ in picks.values() if form == '10-K')
            for cik in sorted(picks, key=order.__getitem__):
                form, accession = picks[cik]
                result = inspect_filing(client, cik, accession, pool[f'{cik:010d}'])
                if 'error' in result:
                    totals['errors'] += 1
                    errors[result['error']] += 1
                    continue
                if 'no_instance' in result:
                    totals['no_instance'] += 1
                    continue
                totals.update(result['flags'])
                inspected.append(dict(result, year=year, cik=f'{cik:010d}', accession=accession, form=form,
                                      company=names.get(accession)))
    except pit.Stop as stop:
        stopped = stop.reason
    except Exception as exc:  # a bug must not hide the counts gathered so far; class name only
        stopped = 'UNEXPECTED'
        errors['UNEXPECTED_' + type(exc).__name__] += 1
    try:
        mismatch_rows = classify_all(inspected, pool, info)
    except Exception as exc:  # the counts above stay; the file then says complete=false
        mismatch_rows, stopped = [], 'UNEXPECTED'
        errors['UNEXPECTED_CLASSIFY_' + type(exc).__name__] += 1
    classes = class_counts(mismatch_rows)
    transient = transient_errors(errors)
    complete = stopped == 'NONE' and totals['form_idx_ok'] == 4 * len(pit.YEARS) and transient == 0
    summary = {'panel': len(panel), 'symbol_filings': totals['trading_symbol'], 'prefix_eq_symbol': totals['prefix_eq_symbol'],
               'mismatches': len(mismatch_rows), 'expected_symbol': EXPECTED_SYMBOL, 'expected_mismatch': EXPECTED_MISMATCH,
               'classes': {name: classes[name] for name in CLASSES}, 'other_symbol_empty': classes['OTHER_SYMBOL_EMPTY'],
               'index_local': sources['LOCAL'], 'index_remote': sources['REMOTE'],
               'stopped': stopped, 'errors': {once.code_token(k): int(v) for k, v in errors.items()},
               'transient_errors': transient}
    once.write_json(folder / once.ROWS_FILE, {
        'schema': _ROWS_SCHEMA, 'source_run_compared': 41255597310, 'complete': complete, 'summary': summary,
        'identity_confirmed': False, 'use': IDENTITY_USE,
        'rules': 'sec_once_ticker_mismatch.classify (rule-based, first match wins; not a person review)',
        'rows': mismatch_rows, 'written_at': once.utc_now()})
    out(f'TICKERMIX_INDEX local={sources["LOCAL"]} remote={sources["REMOTE"]}')
    out(pit.format_counts('overall', totals))
    out(pit.format_errors('overall', errors))
    out(format_compare(totals['trading_symbol'], totals['prefix_eq_symbol'], len(mismatch_rows)))
    out(format_classes(classes, len(mismatch_rows)))
    out(pit.format_requests(client.counts, client.elapsed(), stopped))
    out(f'TICKERMIX_DONE complete={"yes" if complete else "no"}')
    return 0


def transient_errors(errors):
    """Errors a re-run could fix (HTTP 5xx / 429 / 403, network, truncation, form.idx or local read faults, anything
    unknown); the deterministic ones (DETERMINISTIC_ERRORS, PARSE_*) do not count."""
    return sum(int(n) for code, n in errors.items()
               if not (code in DETERMINISTIC_ERRORS or str(code).startswith('PARSE_')))


def filing_values(row):
    """Normalised symbols a filing shows for its issuer: its TradingSymbol values (split) and, when it equals one of
    them, its prefix."""
    values = {norm(s) for s in split_symbols([v for v in row['symbols'] if norm(v)])}
    if row['flags'].get('prefix_eq_symbol'):
        values.add(norm(row['prefix']))
    return values - {''}


def classify_all(inspected, pool, info):
    """Mismatch rows (TradingSymbol present, prefix not equal to any symbol, case-insensitive) with class and evidence."""
    by_cik = {}
    for row in inspected:
        by_cik.setdefault(row['cik'], []).append((row['year'], row['accession'], filing_values(row)))
    out = []
    for row in inspected:
        if not (row['flags'].get('trading_symbol') and not row['flags'].get('prefix_eq_symbol')):
            continue
        cik = row['cik']
        today = {norm(t) for t in pool.get(cik, set())} | {norm(t) for t in info.get(cik, {}).get('tickers', [])}
        mine = [(year, values) for year, acc, values in by_cik.get(cik, []) if acc != row['accession']]
        earlier = set().union(*[values for year, values in mine if year < row['year']])
        later = set().union(*[values for year, values in mine if year > row['year']])
        names = [n for n in [row.get('company')] + info.get(cik, {}).get('names', []) if n]
        label, evidence = classify(row, {'today': today - {''}, 'earlier': earlier, 'later': later}, names)
        out.append({'year': row['year'], 'cik': cik, 'accession': row['accession'], 'form': row['form'],
                    'instance': row['instance'], 'inline': row['inline'], 'prefix': row['prefix'],
                    'symbols': row['symbols'], 'period_end': row['period'], 'company': row.get('company'),
                    'class': label, 'evidence': evidence, 'identity_confirmed': False})
    return out


def main(argv=None, *, environ=None, opener=None, sleep=time.sleep, clock=time.monotonic, out=None):
    environ = os.environ if environ is None else environ
    out = out if out is not None else (lambda line: print(line, flush=True))
    parser = argparse.ArgumentParser(description='Ticker-mismatch classification (see the module docstring).')
    parser.add_argument('--work', required=True)
    args = parser.parse_args(argv)
    try:
        Path(args.work).mkdir(parents=True, exist_ok=True)
        return run(Path(args.work), environ, opener=opener, sleep=sleep, clock=clock, out=out)
    except once.ConfigStop as stop:
        out(f'TICKERMIX_STOP reason={once.code_token(str(stop))}')
        return 2


if __name__ == '__main__':
    try:
        code = main()
    except (Exception, KeyboardInterrupt) as exc:
        name = type(exc).__name__
        print(f'TICKERMIX_STOP reason=UNEXPECTED class={name if pit._CODE_TOKEN.fullmatch(name) else "OTHER"}', flush=True)
        code = 1
    sys.exit(code)
