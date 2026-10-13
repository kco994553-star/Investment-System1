#!/usr/bin/env python3
"""Build local logo images from Wikidata website domains; failures retain initials."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlencode, urlsplit, unquote
from urllib.request import Request, urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.product.company_logos import FILENAME, MAX_IMAGE_BYTES, public_payload, require_company_logos, sanitize_png
from investment_system.universe.universe_domains import FILENAME as DOMAINS, normalize_domain, require_universe_domains

QUERY = 'SELECT ?site ?logo WHERE { ?item wdt:P856 ?site; wdt:P154 ?logo. }'


def fetch(url, limit):
    request = Request(url, headers={'User-Agent': 'Investment-System1 local-logo-build', 'Accept': 'application/json,image/png'})
    with urlopen(request, timeout=30) as response:
        body = response.read(limit + 1)
    if len(body) > limit:
        raise ValueError('LOGO_SOURCE_OVERSIZED')
    return body


def domain_logos(body):
    choices = {}
    for row in json.loads(body).get('results', {}).get('bindings', []):
        domain = normalize_domain(row.get('site', {}).get('value'))
        logo = row.get('logo', {}).get('value', '')
        parts = urlsplit(logo)
        if domain and parts.hostname == 'commons.wikimedia.org' and parts.path.startswith('/wiki/Special:FilePath/'):
            name = unquote(parts.path.split('/wiki/Special:FilePath/', 1)[1])
            if name and '|' not in name:
                choices.setdefault(domain, set()).add(name)
    return {domain: next(iter(names)) for domain, names in choices.items() if len(names) == 1}


def emit(out, *, live=False, fetcher=fetch):
    out = Path(out)
    previous = None
    if (out / FILENAME).exists():
        try:
            previous = require_company_logos(json.loads((out / FILENAME).read_text()))
        except (OSError, ValueError):
            pass
    images = {}
    if live:
        try:
            domains = json.loads((out / DOMAINS).read_text())
            require_universe_domains(domains)
            logo_names = domain_logos(fetcher('https://query.wikidata.org/sparql?' + urlencode({'query': QUERY, 'format': 'json'}), 4 * 1024 * 1024))
            names = {code: logo_names[domain] for code, domain, source in domains['rows'] if domain in logo_names}
            titles = sorted(set('File:' + name for name in names.values()))
            urls = {}
            for start in range(0, len(titles), 50):
                endpoint = 'https://commons.wikimedia.org/w/api.php?' + urlencode({'action':'query','format':'json','prop':'imageinfo',
                           'iiprop':'url','iiurlwidth':64,'titles':'|'.join(titles[start:start+50])})
                pages = json.loads(fetcher(endpoint, 1024 * 1024)).get('query', {}).get('pages', {})
                for page in pages.values():
                    info = page.get('imageinfo', [{}])[0]
                    url = info.get('thumburl') or info.get('url')
                    parts = urlsplit(url or '')
                    if parts.scheme == 'https' and parts.hostname == 'upload.wikimedia.org' and parts.path.lower().endswith('.png'):
                        urls[page.get('title', '')] = url
            by_name = {}
            for title, url in urls.items():
                by_name[title[5:]] = sanitize_png(fetcher(url, MAX_IMAGE_BYTES))
            images = {code: by_name[name] for code, name in names.items() if name in by_name}
            print('LOGO_WIKIDATA_OK')
        except Exception:
            # Stop this collection at the first access/format failure. No values,
            # external URLs, exception bodies or private state enter Actions logs.
            print('LOGO_WIKIDATA_SOURCE_UNAVAILABLE')
    payload = public_payload(images) if images or previous is None else previous
    (out / FILENAME).write_text(json.dumps(payload, separators=(',', ':')))
    count = sum(row[1] is not None for row in payload['rows'])
    if live:
        print('LOGO_BUNDLE_OK images=' + str(count) + ' initials=' + str(len(payload['rows']) - count))
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    emit(args.out, live=args.live)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
