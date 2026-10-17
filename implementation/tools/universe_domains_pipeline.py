#!/usr/bin/env python3
"""Write universe-domains.json (company web domains for runtime logos) into a Pages directory.

Offline (default, used by build_pages_cockpit): the reviewed in-repo rows only.
--preserve-only: the last published Pages copy merged with the reviewed rows (UI redeploys keep live rows).
--live (GitHub Actions): SEC submissions `website` for today's Universe504 shard (same rotation as
sec_universe_shares) through the paced SEC client, then one Wikidata query (P5531 SEC CIK -> P856 official
website, CC0), merged with the last published copy. Priority sec > wikidata > manual; unknown stays null.

Only domains are published. Raw SEC/Wikidata bodies stay in RAM. Output lines carry counts and fixed codes
only: no names, URLs, domains or secrets. A failed live run falls back to the preserved copy.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.universe.universe_domains import (FILENAME, MAX_BYTES, counts, merge, normalize_domain,
                                                         public_payload, require_universe_domains)

SOURCE = 'https://kco994553-star.github.io/Investment-System1/' + FILENAME
WIKIDATA_URL = 'https://query.wikidata.org/sparql'
WIKIDATA_AGENT = 'Investment-System1 universe-domains/1 (GitHub Actions; public company websites only)'
WIKIDATA_MAX_BYTES = 4 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        print('UNIVERSE_DOMAINS CONFIG_INVALID')
        raise SystemExit(2)


def write(directory, payload):
    directory = Path(directory)
    destination = directory / FILENAME
    if directory.is_symlink() or not directory.is_dir() or destination.is_symlink():
        raise ValueError('UNIVERSE_DOMAINS_OUTPUT_INVALID')
    require_universe_domains(payload)
    body = json.dumps(payload, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()
    if len(body) > MAX_BYTES:
        raise ValueError('UNIVERSE_DOMAINS_OUTPUT_INVALID')
    with tempfile.NamedTemporaryFile(dir=directory, prefix='.universe-domains-', delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(body)
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return payload


def emit(directory):
    return write(directory, public_payload())


def fetch_previous(*, open_response=None):
    """Last published copy -> validated payload; None on 404 or an invalid copy. Other failures raise OSError."""
    request = urllib.request.Request(SOURCE, headers={'Accept': 'application/json', 'Cache-Control': 'no-cache'})
    fetch = open_response or urllib.request.build_opener(NoRedirect()).open
    try:
        with fetch(request, timeout=20) as response:
            if response.status != 200 or response.geturl() != SOURCE:
                raise OSError('PREVIOUS_FETCH_FAILED')
            body = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise OSError('PREVIOUS_FETCH_FAILED') from None
    except (urllib.error.URLError, OSError, ValueError):
        raise OSError('PREVIOUS_FETCH_FAILED') from None
    try:
        if len(body) > MAX_BYTES:
            raise ValueError()
        payload = json.loads(body.decode('utf-8'))
        require_universe_domains(payload)
        return payload
    except (ValueError, UnicodeError, RecursionError):
        return None


def sec_websites(user_agent, *, now=None, client_kwargs=None):
    """({code: domain}, checked_codes, registry) for today's shard. SEC `website` is often empty."""
    from investment_system.providers.sec_collection import SecCollectionClient
    from investment_system.providers.sec_classification_collection import ClassificationSecClient, URLS
    from investment_system.providers.sec_universe_collection import daily_partition, fetch_ticker_exchange, universe_registry
    from investment_system.universe.sec_universe_shares import load_config, shard_day, shard_index_for
    kwargs = dict(client_kwargs or {})
    registry = universe_registry(fetch_ticker_exchange(SecCollectionClient(user_agent, **kwargs)))
    started = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    shard_count = load_config()['shard_count']
    issuers = daily_partition(registry, shard_count=shard_count, shard_index=shard_index_for(shard_day(started), shard_count))
    client = ClassificationSecClient(user_agent, **kwargs)
    found, checked = {}, set()
    for issuer in issuers:
        try:
            body, _ = client.fetch('SUBMISSIONS', URLS['SUBMISSIONS'].format(cik=issuer.cik), expected_cik=issuer.cik)
            website = json.loads(body.decode('utf-8')).get('website')
        except Exception:
            continue
        checked.update(issuer.codes)
        domain = normalize_domain(website)
        if domain:
            for code in issuer.codes:
                found[code] = domain
    return found, checked, registry


def wikidata_query(ciks):
    values = ' '.join('"%s" "%s"' % (cik, cik.lstrip('0')) for cik in sorted(ciks))
    return ('SELECT ?cik ?site ?rank WHERE { VALUES ?cik { ' + values + ' } ?item wdt:P5531 ?cik . '
            '?item p:P856 ?statement . ?statement ps:P856 ?site ; wikibase:rank ?rank . '
            'FILTER(?rank != wikibase:DeprecatedRank) }')


def wikidata_domains(body, ciks):
    """{cik10: domain}: the preferred-rank value, else the only distinct normal-rank domain. Ambiguous stays unset."""
    payload = json.loads(body.decode('utf-8'))
    by_cik = {}
    for binding in payload['results']['bindings']:
        cik = str(binding['cik']['value']).strip()
        if not cik.isdigit() or len(cik) > 10:
            continue
        cik = cik.zfill(10)
        domain = normalize_domain(binding['site']['value'])
        if cik not in ciks or not domain:
            continue
        preferred = binding.get('rank', {}).get('value', '').endswith('PreferredRank')
        by_cik.setdefault(cik, {'preferred': set(), 'normal': set()})['preferred' if preferred else 'normal'].add(domain)
    out = {}
    for cik, ranks in by_cik.items():
        pick = ranks['preferred'] if ranks['preferred'] else ranks['normal']
        if len(pick) == 1:
            out[cik] = next(iter(pick))
    return out


def fetch_wikidata(ciks, *, open_response=None):
    data = urllib.parse.urlencode({'query': wikidata_query(ciks), 'format': 'json'}).encode()
    request = urllib.request.Request(WIKIDATA_URL, data=data, method='POST', headers={
        'User-Agent': WIKIDATA_AGENT, 'Accept': 'application/sparql-results+json',
        'Content-Type': 'application/x-www-form-urlencoded'})
    fetch = open_response or urllib.request.build_opener(NoRedirect()).open
    with fetch(request, timeout=60) as response:
        if response.status != 200:
            raise OSError('WIKIDATA_FAILED')
        body = response.read(WIKIDATA_MAX_BYTES + 1)
    if len(body) > WIKIDATA_MAX_BYTES:
        raise OSError('WIKIDATA_FAILED')
    return wikidata_domains(body, set(ciks))


def collect(*, environ=None, now=None, previous_fetch=fetch_previous, sec_fetch=sec_websites, wiki_fetch=fetch_wikidata):
    environ = os.environ if environ is None else environ
    try:
        previous = previous_fetch()
    except OSError:
        previous = None
    status = {'sec_checked': 0, 'sec_filled': 0, 'wikidata': 'NOT_RUN'}
    sec, checked, registry = {}, set(), None
    agent = environ.get('SEC_USER_AGENT')
    if agent:
        try:
            sec, checked, registry = sec_fetch(agent, now=now)
            status['sec_checked'], status['sec_filled'] = len(checked), len(sec)
        except Exception:
            status['sec'] = 'UNAVAILABLE'
    else:
        status['sec'] = 'SEC_USER_AGENT_MISSING'
    wikidata = None
    if registry is not None:
        try:
            by_cik = wiki_fetch([issuer.cik for issuer in registry.issuers])
            wikidata = {code: by_cik[issuer.cik] for issuer in registry.issuers for code in issuer.codes if issuer.cik in by_cik}
            status['wikidata'] = 'OK'
        except Exception:
            status['wikidata'] = 'UNAVAILABLE'
    payload = public_payload(merge(previous=previous, sec=sec, sec_checked=checked, wikidata=wikidata))
    return payload, status


def preserve(directory, *, previous_fetch=fetch_previous):
    try:
        previous = previous_fetch()
    except OSError:
        previous = None
    return write(directory, public_payload(merge(previous=previous)))


def summary(payload, status=None):
    c = counts(payload)
    line = 'UNIVERSE_DOMAINS_OK ' + ' '.join(f'{k}={c[k]}' for k in ('sec', 'wikidata', 'manual', 'empty'))
    if status:
        line += ' ' + ' '.join(f'{k}={v}' for k, v in sorted(status.items()))
    return line


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--live', action='store_true')
    mode.add_argument('--preserve-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.live:
            payload, status = collect()
            write(args.out, payload)
            print(summary(payload, status))
        elif args.preserve_only:
            print(summary(preserve(args.out)))
        else:
            print(summary(emit(args.out)))
    except Exception:
        if not args.live:
            print('UNIVERSE_DOMAINS_BUILD_FAILED')
            return 1
        try:
            payload = preserve(args.out)
        except Exception:
            print('UNIVERSE_DOMAINS_BUILD_FAILED')
            return 1
        print('UNIVERSE_DOMAINS_LIVE_UNAVAILABLE fallback=PRESERVED ' + summary(payload))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
