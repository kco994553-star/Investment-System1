#!/usr/bin/env python3
"""Rebuild web_assets/company-names-ko.json (KR-NAMES, owner decision 2026-10-18) from saved inputs. Never fetches.

Inputs (saved once by the reviewer; raw dumps are not committed, their sha256 goes into the JSON header):
  --sec              SEC company_tickers_exchange.json (https://www.sec.gov/files/company_tickers_exchange.json)
  --wikidata-cik     Wikidata SPARQL JSON: items with SEC CIK (P5531) in the Universe set -> ko label, en label,
                     kowiki sitelink, ko aliases (variables item, cik, ko, en, kowiki, koalt)
  --wikidata-non-sec Wikidata SPARQL JSON for the non-SEC TARGET listings by exchange + ticker (P414/P249)
                     (variables item, ex, tk, ko, en, kowiki, koalt)

Keys (no ticker-only links, no new scheme): TARGET company_id from markets.us (US_LISTINGS + OUT_OF_US_TRACK);
a Universe504 code is linked to a TARGET company_id only when US_LISTINGS names that exchange:symbol AND the
Universe registry (providers.sec_universe_collection.universe_registry, the binding the daily collection uses)
gives that code the same CIK. Every other code is its own record keyed by the code. CIK is a cross-check field.

English name: the SEC title of the code's registry CIK. Korean name priority: OFFICIAL (the reviewed spot checks
below, each with the URL that was read) > COMMON (Wikidata ko label, else the Korean Wikipedia title, of the item
with the same CIK / listing; must contain Hangul) > UNREGISTERED (null). Aliases come only from the same Wikidata
item (ko label, kowiki title, ko aliases), minus the reviewed exclusions below. Nothing is translated here.

Run (reads only local files): python3 -I implementation/tools/build_company_names_ko.py --sec F --wikidata-cik F
  --wikidata-non-sec F --reviewed-at YYYY-MM-DD [--out PATH] [--report PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.providers.sec_universe_collection import universe_registry  # noqa: E402
from investment_system.universe.company_names_ko import (FILENAME, SCHEMA, SOURCE, alias_collisions,  # noqa: E402
                                                         check_shape, compact, target_listings)
from investment_system.universe.universe_codes import source_codes  # noqa: E402

SEC_URL = 'https://www.sec.gov/files/company_tickers_exchange.json'
WIKIDATA = 'https://www.wikidata.org/wiki/'
KOWIKI = 'https://ko.wikipedia.org/wiki/'
TOOL = 'implementation/tools/build_company_names_ko.py'

# Official Korean sources read on 2026-10-18 (TARGET spot checks). Name exactly as the official Korean-language source
# writes it in Korean text (the Latin brand when the official Korean page writes the Latin brand).
OFFICIAL = {
    'lrcx': ('램리서치', 'https://www.lamresearch.com/ko/'),                       # "램리서치는 ..." (Korean site)
    'stry': ('스트라이커', 'https://www.stryker.com/kr/ko/index.html'),              # "스트라이커가 ..." (Korean site)
    'rok': ('로크웰 오토메이션', 'https://www.rockwellautomation.com/ko-kr.html'),     # "로크웰 오토메이션은 ..." (Korean site)
    'msft': ('마이크로소프트', 'https://www.microsoft.com/ko-kr'),                   # footer: 한국마이크로소프트(유) (Korean subsidiary)
    'nvda': ('NVIDIA', 'https://www.nvidia.com/ko-kr/about-nvidia/'),            # "NVIDIA는 ..." (Korean site, Latin brand)
    'amd': ('AMD', 'https://www.amd.com/ko.html'),                                # "AMD는 ..." (Korean site, Latin brand)
    'klac': ('KLA', 'https://www.kla.com/ko'),                                    # "KLA는 ..." (Korean site, Latin brand)
    'hanmi': ('한미반도체', 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20261007000050'),  # DART filing title (filer name)
}
# Share classes that share one issuer (one CIK, several Universe codes) or carry a class suffix. Sources: the reviewed
# share-class config (universe/share_class_groups.py, USER_DECISION_2026_10_11), the SEC cover title exception in
# providers/sec_m3_adapter.py (GOOG = Class C Capital Stock), the TARGET identity map (GOOGL CLASS_A_COMMON_EQUITY)
# and the Universe code's own class suffix (.B).
SHARE_CLASS = {
    'googl': ('A', 'Class A common stock (GOOGL); the same issuer\'s Class C capital stock is NASDAQ:GOOG'),
    'NASDAQ:GOOG': ('C', 'Class C capital stock (GOOG); the same issuer\'s Class A common stock is GOOGL (TARGET googl)'),
    'NASDAQ:FOXA': ('A', 'Class A common stock (FOXA, non-voting); the same issuer\'s Class B is NASDAQ:FOX'),
    'NASDAQ:FOX': ('B', 'Class B common stock (FOX, voting); the same issuer\'s Class A is NASDAQ:FOXA'),
    'NASDAQ:NWSA': ('A', 'Class A common stock (NWSA, non-voting); the same issuer\'s Class B is NASDAQ:NWS'),
    'NASDAQ:NWS': ('B', 'Class B common stock (NWS, voting); the same issuer\'s Class A is NASDAQ:NWSA'),
    'NYSE:BRK.B': ('B', 'Class B common stock (BRK.B); Class A (BRK.A) is not in Universe504'),
    'NYSE:BF.B': ('B', 'Class B common stock (BF.B); Class A (BF.A) is not in Universe504'),
}
# Reviewed Wikidata strings (2026-10-18). The source is always the same Wikidata item; nothing here is a new name.
# PREFERRED: the item's ko label is a former name (or a typo) and one of the item's own ko aliases is the current name,
# so that alias becomes ko_name and the label stays an alias (former official name).
PREFERRED = {
    'NYSE:SPGI': 'S&P 글로벌',                 # label 맥그로-힐 = former McGraw-Hill
    'NYSE:XYZ': '블록',                        # label 스퀘어 = former Square, Inc.
    'NASDAQ:UAL': '유나이티드 에어라인 홀딩스',    # label = former United Continental Holdings
    'NASDAQ:ADBE': '어도비',                   # label = former Adobe Systems
    'NASDAQ:FFIV': 'F5 네트웍스',               # label 'F5 내트워크' is misspelled
    'NASDAQ:ON': '온 세미컨덕터',               # label '온 세미컨덕더' is misspelled
    'NYSE:OTIS': '오티스 엘리베이터',            # label names the Korean subsidiary (another entity)
}
# NO_CURRENT_NAME: every Korean string on the item is a predecessor's name (kept as former-name aliases only).
NO_CURRENT_NAME = {'NASDAQ:WBD'}               # Discovery, Inc. (same CIK) before the WarnerMedia merger
# Wikidata ko aliases that name a product, brand or another entity rather than the company (not used).
EXCLUDED_ALIASES = {
    'nvda': {'포스웨어'},                        # ForceWare, a driver brand
    'NYSE:KR': {'빅 K 콜라'},                   # a soft-drink brand
    'NASDAQ:COST': {'카스코로', '프라이스클럽'},    # unexplained string / the merged Price Club chain
    'NYSE:OTIS': {'오티스 엘리베이터 코리아'},      # the Korean subsidiary
}
NON_SEC_LISTINGS = {'tokyo_electron': ('TYO', '8035', 'http://www.wikidata.org/entity/Q217475'),
                    'hanmi': ('KRX', '042700', 'http://www.wikidata.org/entity/Q493751')}
POLICY = [
    'Display and search only: names never change QGV calculation, company identity, rankings or past records.',
    'Keys are existing identifiers: TARGET company_id or Universe504 code (EXCHANGE:SYMBOL); never a ticker alone. CIK is a cross-check.',
    'ko_status OFFICIAL = official Korean source (URL); COMMON = Wikidata Korean label or Korean Wikipedia title tied to the same SEC CIK or listing (QID/URL); UNREGISTERED = no verified Korean name (null).',
    'No name is translated or transliterated by this project. Without a Korean name the English (SEC) name is shown; without both, the ticker.',
    'en_name is the SEC company_tickers_exchange.json title of the code\'s Universe-registry CIK.',
    'No prices, market values, ranks or personal data.',
]
_HANGUL = re.compile(r'[가-힣]')
_SUFFIX = {'inc', 'incorporated', 'corp', 'corporation', 'co', 'company', 'plc', 'ltd', 'limited', 'the', 'nv', 'sa', 'llc', 'de'}


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _strip_disambiguation(text: str) -> str:
    return re.sub(r'\s*\([^()]*\)\s*$', '', unicodedata.normalize('NFC', text)).strip()


def _title_of(url: str) -> str:
    return _strip_disambiguation(unquote(url[len(KOWIKI):]).replace('_', ' ')) if url.startswith(KOWIKI) else ''


def _name_form(text: str) -> str:
    words = re.sub(r'[^a-z0-9 ]+', ' ', str(text).lower().replace('/de', ' ')).split()
    return ' '.join(w for w in words if w not in _SUFFIX)


def sec_titles(body: bytes) -> dict:
    payload = json.loads(body)
    fields = payload['fields']
    out = {}
    for row in payload['data']:
        d = dict(zip(fields, row))
        if type(d.get('cik')) is int and type(d.get('name')) is str and d['name'].strip():
            out.setdefault(str(d['cik']).zfill(10), d['name'].strip())
    return out


def wikidata_items(body: bytes, key) -> dict:
    """{group key: {qid: {'ko': set, 'en': set, 'kowiki': set, 'alt': set}}}."""
    out = {}
    for row in json.loads(body)['results']['bindings']:
        k = key(row)
        if k is None:
            continue
        qid = row['item']['value'].rsplit('/', 1)[1]
        item = out.setdefault(k, {}).setdefault(qid, {'ko': set(), 'en': set(), 'kowiki': set(), 'alt': set()})
        for var, field in (('ko', 'ko'), ('en', 'en'), ('kowiki', 'kowiki'), ('koalt', 'alt')):
            if var in row:
                item[field].add(row[var]['value'])
    return out


def choose_item(items: dict, sec_title: str | None, notes: list, label: str):
    """One Wikidata item for one CIK: the only one, or the one whose English label equals the SEC title (suffixes
    dropped); among several such, the only one carrying Korean data. Otherwise none (ambiguous, reported)."""
    if not items:
        return None
    if len(items) == 1:
        return next(iter(items.items()))
    want = _name_form(sec_title or '')
    matched = {q: d for q, d in items.items() if want and any(_name_form(e) == want for e in d['en'])}
    korean = {q: d for q, d in matched.items() if d['ko'] or d['kowiki'] or d['alt']}
    pick = matched if len(matched) == 1 else korean if len(korean) == 1 else None
    notes.append({'key': label, 'candidates': sorted(items), 'chosen': next(iter(pick)) if pick else None})
    return next(iter(pick.items())) if pick else None


def korean_name(qid: str, item: dict):
    """(ko_name, source) from one Wikidata item: the Hangul ko label, else the Hangul kowiki title; else None."""
    for label in sorted(item['ko']):
        name = _strip_disambiguation(label)
        if _HANGUL.search(name):
            return name, WIKIDATA + qid
    for url in sorted(item['kowiki']):
        name = _title_of(url)
        if _HANGUL.search(name):
            return name, url
    return None


def item_strings(qid: str, item: dict) -> list:
    """(text, source) of one item: ko labels, Korean Wikipedia titles, ko aliases (disambiguators dropped)."""
    out = [(_strip_disambiguation(x), WIKIDATA + qid) for x in sorted(item['ko'])]
    out += [(_title_of(u), u) for u in sorted(item['kowiki'])]
    return out + [(_strip_disambiguation(x), WIKIDATA + qid) for x in sorted(item['alt'])]


def aliases_of(qid: str, item: dict, ko_name: str | None, excluded=frozenset()) -> list:
    out, seen = [], {compact(ko_name)} if ko_name else set()
    for text, source in item_strings(qid, item):
        form = compact(text)
        if not text or not _HANGUL.search(text) or not form or form in seen or text in excluded or len(text) > 80:
            continue
        seen.add(form)
        out.append({'text': text, 'lang': 'ko', 'source': source})
    return out[:12]


def build(sec_body: bytes, wd_cik_body: bytes, wd_non_sec_body: bytes, reviewed_at: str, notes: list | None = None) -> dict:
    notes = [] if notes is None else notes
    registry = universe_registry(sec_body)
    code_cik = {code: issuer.cik for issuer in registry.issuers for code in issuer.codes}
    titles = sec_titles(sec_body)
    by_cik = wikidata_items(wd_cik_body, lambda r: r['cik']['value'].zfill(10))
    by_listing = wikidata_items(wd_non_sec_body, lambda r: (r['ex']['value'], r['tk']['value']))
    codes, listings = source_codes(), target_listings()
    linked = {}
    for cid, listing in listings.items():
        if listing is None:
            continue
        code = listing['exchange'] + ':' + listing['yahoo']
        if code in codes and code_cik.get(code) == listing['cik']:
            linked[code] = cid
        elif code in codes:
            notes.append({'key': cid, 'unlinked_code': code, 'reason': 'REGISTRY_CIK_DIFFERS'})

    def record(key, kind, universe_code, cik, ticker, exchange, en_name, en_source, wikidata):
        klass = SHARE_CLASS.get(key)
        ko = None
        qid, item = wikidata if wikidata else (None, None)
        if key in OFFICIAL:
            ko = (OFFICIAL[key][0], OFFICIAL[key][1], 'OFFICIAL')
        elif item is not None and key in PREFERRED:
            found = [source for text, source in item_strings(qid, item) if text == PREFERRED[key]]
            if not found:
                raise ValueError('PREFERRED_NOT_ON_ITEM ' + key)
            ko = (PREFERRED[key], found[0], 'COMMON')
        elif item is not None and key not in NO_CURRENT_NAME:
            found = korean_name(qid, item)
            ko = (found[0], found[1], 'COMMON') if found else None
        aliases = aliases_of(qid, item, ko[0] if ko else None, EXCLUDED_ALIASES.get(key, frozenset())) if item is not None else []
        return {'key': key, 'key_kind': kind, 'universe_code': universe_code, 'cik': cik, 'ticker': ticker, 'exchange': exchange,
                'share_class_note': klass[1] if klass else None, 'class_label': klass[0] if klass else None,
                'en_name': en_name, 'en_source': en_source if en_name else None,
                'ko_name': ko[0] if ko else None, 'ko_status': ko[2] if ko else 'UNREGISTERED', 'ko_source': ko[1] if ko else None,
                'aliases': aliases, 'reviewed_at': reviewed_at}

    records = []
    for cid, listing in listings.items():
        if listing is None:
            exchange, ticker, ex_entity = NON_SEC_LISTINGS[cid]
            wd = choose_item(by_listing.get((ex_entity, ticker), {}), None, notes, cid)
            en = sorted(wd[1]['en'])[0] if wd and wd[1]['en'] else None
            records.append(record(cid, 'TARGET_COMPANY_ID', None, None, ticker, exchange, en, WIKIDATA + wd[0] if wd else None, wd))
            continue
        code = listing['exchange'] + ':' + listing['yahoo']
        cik = listing['cik']
        wd = choose_item(by_cik.get(cik, {}), titles.get(cik), notes, cid)
        records.append(record(cid, 'TARGET_COMPANY_ID', code if linked.get(code) == cid else None, cik, listing['yahoo'],
                              listing['exchange'], titles.get(cik), SEC_URL, wd))
    for code in codes:
        if code in linked:
            continue
        exchange, ticker = code.split(':', 1)
        cik = code_cik.get(code)
        wd = choose_item(by_cik.get(cik, {}), titles.get(cik), notes, code) if cik else None
        records.append(record(code, 'UNIVERSE_CODE', code, cik, ticker, exchange, titles.get(cik) if cik else None, SEC_URL, wd))
    # Several codes of one CIK must each carry a class label, or they could not be told apart.
    per_cik = {}
    for r in records:
        if r['cik']:
            per_cik.setdefault(r['cik'], []).append(r)
    for rows in per_cik.values():
        if len(rows) > 1 and any(r['class_label'] is None for r in rows):
            raise ValueError('SHARE_CLASS_LABEL_MISSING ' + ','.join(r['key'] for r in rows))
    reviewed = json.dumps({'official': OFFICIAL, 'share_class': SHARE_CLASS, 'preferred': PREFERRED,
                           'no_current_name': sorted(NO_CURRENT_NAME),
                           'excluded_aliases': {k: sorted(v) for k, v in EXCLUDED_ALIASES.items()}},
                          ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    payload = {
        'schema': SCHEMA, 'generated_by': TOOL, 'reviewed_at': reviewed_at, 'policy': POLICY,
        'inputs': [{'name': 'sec_company_tickers_exchange', 'sha256': sha256(sec_body)},
                   {'name': 'wikidata_cik_ko', 'sha256': sha256(wd_cik_body)},
                   {'name': 'wikidata_non_sec_listings', 'sha256': sha256(wd_non_sec_body)},
                   {'name': 'reviewed_official_and_share_class_tables', 'sha256': sha256(reviewed)}],
        'counts': {'records': len(records), 'target_company_ids': sum(r['key_kind'] == 'TARGET_COMPANY_ID' for r in records),
                   'universe_codes': sum(r['universe_code'] is not None for r in records),
                   'official': sum(r['ko_status'] == 'OFFICIAL' for r in records),
                   'common': sum(r['ko_status'] == 'COMMON' for r in records),
                   'unregistered': sum(r['ko_status'] == 'UNREGISTERED' for r in records),
                   'en_name_present': sum(r['en_name'] is not None for r in records),
                   'en_name_missing': sum(r['en_name'] is None for r in records)},
        'records': records,
    }
    check_shape(payload)
    return payload


def report(payload: dict, notes: list) -> dict:
    """Review summary (not published): collisions, same-name and similar-name cases, source mix."""
    recs = payload['records']
    same_ko, similar = {}, []
    for r in recs:
        if r['ko_name']:
            same_ko.setdefault(compact(r['ko_name']), []).append(r['key'])
    cik = {r['key']: r['cik'] for r in recs}
    named = [(compact(t), t, r['key']) for r in recs for t in ([r['ko_name']] if r['ko_name'] else []) + [a['text'] for a in r['aliases']]]
    for a, ta, ka in named:
        for b, tb, kb in named:
            if ka < kb and (cik[ka] is None or cik[ka] != cik[kb]) and (a.startswith(b) or b.startswith(a)) and min(len(a), len(b)) >= 2:
                similar.append([ka, ta, kb, tb])
    mix = {}
    for r in recs:
        src = r['ko_source'] or ''
        kind = r['ko_status'] + (':wikidata' if src.startswith(WIKIDATA) else ':kowiki' if src.startswith(KOWIKI) else ':official' if src else '')
        mix[kind] = mix.get(kind, 0) + 1
    return {'counts': payload['counts'], 'source_mix': mix, 'alias_collisions': alias_collisions(payload),
            'same_ko_name': {k: v for k, v in same_ko.items() if len(v) > 1}, 'similar_ko_names': similar,
            'share_class': [[r['key'], r['class_label'], r['ko_name'], r['en_name']] for r in recs if r['class_label']],
            'wikidata_choices': notes, 'aliases': sum(len(r['aliases']) for r in recs)}


def write(path: Path, payload: dict) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--sec', required=True)
    parser.add_argument('--wikidata-cik', required=True)
    parser.add_argument('--wikidata-non-sec', required=True)
    parser.add_argument('--reviewed-at', required=True)
    parser.add_argument('--out', default=str(SOURCE))
    parser.add_argument('--report')
    args = parser.parse_args(argv)
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', args.reviewed_at):
        parser.error('--reviewed-at must be YYYY-MM-DD')
    notes = []
    payload = build(Path(args.sec).read_bytes(), Path(args.wikidata_cik).read_bytes(), Path(args.wikidata_non_sec).read_bytes(),
                    args.reviewed_at, notes)
    write(Path(args.out), payload)
    if args.report:
        Path(args.report).write_text(json.dumps(report(payload, notes), ensure_ascii=False, indent=1), encoding='utf-8')
    c = payload['counts']
    print('COMPANY_NAMES_KO records=%d official=%d common=%d unregistered=%d en_present=%d en_missing=%d -> %s'
          % (c['records'], c['official'], c['common'], c['unregistered'], c['en_name_present'], c['en_name_missing'], FILENAME))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
