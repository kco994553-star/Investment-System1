"""Public `news-signals.json`: '뉴스·신호' (channel NEWS) titles and links for the TARGET companies.

Sources: the GDELT Project DOC 2.0 API (attribution required, shown on screen and stored in the
file) and official company investor-relations press-release feeds. Stored per item: title, link,
time, company, rule-based classification and grouping only. No article body, summary, image,
price or personal data. News never changes any score (`score_effect: NONE`).

Rules v0 (mirrored by web_assets/news-signals.js, checked by shared vectors):
- relevance: a GDELT title must contain a company name variant (case-insensitive, whole words) or a
  case-sensitive ticker/name token, and none of that company's exclusion phrases;
- dedupe: one item per canonical link; one item per company and normalized title (IR preferred);
- grouping: same company, within 72h of the group's first item, at least 3 shared significant
  title tokens and Jaccard >= 50% -> same group (first NEW, later REPEAT);
- an IR release that repeats an 8-K Exhibit 99.1 joins that 8-K's group (RELATED_TO_8K, REPEAT).

Pure functions: no network, credentials or clock. `tools/news_signals.py` collects and carries
the previous Pages copy forward (rolling window).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import re
import string
from urllib.parse import urlsplit

from ..markets.us import US_LISTINGS

FILENAME = 'news-signals.json'
KIND = 'NEWS_SIGNALS'
WINDOW_DAYS = 14
QUERY_DAYS = 7
STALE_AFTER = timedelta(hours=48)
MAX_BYTES = 1024 * 1024
SIZE_BUDGET = 950_000
MAX_ITEMS = 1500
TITLE_MAX = 200
LINK_MAX = 600
SOURCES = ('GDELT', 'IR')
PER_COMPANY_MAX = {'GDELT': 40, 'IR': 30}
CLASSIFICATIONS = ('EARNINGS', 'PRODUCT', 'MA', 'LEGAL', 'OTHER')
OCCURRENCES = ('NEW', 'REPEAT')
RELATIONS = ('NONE', 'RELATED_TO_8K')
STATES = ('LIVE', 'STALE', 'NOT_AVAILABLE')
FEED_STATUSES = ('VERIFIED', 'UNVERIFIED_URL', 'NOT_AVAILABLE')
COMPANY_REASONS = ('NOT_COLLECTED', 'NO_OFFICIAL_FEED_KNOWN')
MATCHING_RULE = 'TITLE_NAME_OR_TICKER_V0'
GROUP_WINDOW = timedelta(hours=72)
GROUP_MIN_SHARED = 3
GROUP_MIN_PERCENT = 50
RELATED_8K_WINDOW = timedelta(hours=24)
RELATED_8K_MIN_SHARED = 2
RELATED_8K_MIN_PERCENT = 50

GDELT_COMPANIES = tuple(sorted(set(US_LISTINGS) | {'tokyo_electron', 'hanmi'}))
IR_COMPANIES = tuple(sorted(US_LISTINGS))

ATTRIBUTION = {
    'GDELT': {'name': 'The GDELT Project', 'url': 'https://www.gdeltproject.org/',
              'citation': 'News signals: The GDELT Project (https://www.gdeltproject.org/), DOC 2.0 API. '
                          'Titles and links only; every article belongs to its publisher.'},
    'IR': {'name': 'Company investor-relations press-release feeds', 'url': None,
           'citation': "Each company's own press-release feed. Titles and links only."},
}

# GDELT matching rule v0, one row per company (documented in docs/daily_data_pipeline/NEWS_SIGNALS.md).
#   query   : GDELT DOC 2.0 query (sourcelang:english is appended by the provider);
#   names   : normalized phrases (lowercase ASCII tokens) that count as a mention anywhere in the title;
#   symbols : case-sensitive tokens (tickers, brand spellings) matched as whole words in the raw title;
#   exclude : normalized phrases that reject a title (homonyms, generic words).
MATCH = {
    'amd': {'query': '("Advanced Micro Devices" OR AMD) -macular',
            'names': ('advanced micro devices',), 'symbols': ('AMD',), 'exclude': ('macular', 'degeneration')},
    'amzn': {'query': '(Amazon OR AMZN) -rainforest -deforestation',
             'names': ('amazon com', 'amazon web services'), 'symbols': ('Amazon', 'AMZN', 'AWS'),
             'exclude': ('rainforest', 'deforestation', 'amazon river', 'amazon basin', 'amazon forest', 'amazonia',
                         'indigenous', 'amazon fires')},
    'asml': {'query': 'ASML', 'names': ('asml',), 'symbols': (), 'exclude': ()},
    'avgo': {'query': '(Broadcom OR AVGO)', 'names': ('broadcom',), 'symbols': ('AVGO',), 'exclude': ()},
    'etn': {'query': '(Eaton OR ETN) -"Eaton Vance" -"Eaton fire"',
            'names': ('eaton corp', 'eaton corporation'), 'symbols': ('Eaton', 'ETN'),
            'exclude': ('eaton vance', 'eaton fire', 'eaton canyon', 'eaton centre', 'eaton center')},
    'gev': {'query': '("GE Vernova" OR GEV)', 'names': ('ge vernova',), 'symbols': ('GEV',), 'exclude': ()},
    'googl': {'query': '(Alphabet OR Google OR GOOGL)', 'names': ('alphabet', 'google'), 'symbols': ('GOOGL', 'GOOG'),
              'exclude': ('alphabet soup',)},
    'hanmi': {'query': '"Hanmi Semiconductor"', 'names': ('hanmi semiconductor',), 'symbols': (), 'exclude': ()},
    'hubb': {'query': '(Hubbell OR HUBB)', 'names': ('hubbell',), 'symbols': ('HUBB',), 'exclude': ()},
    'intc': {'query': '(Intel OR INTC)', 'names': ('intel corp', 'intel corporation'), 'symbols': ('Intel', 'INTEL', 'INTC'),
             'exclude': ('intel officials', 'military intel', 'intel chief', 'intel community', 'us intel', 'intel report',
                         'intel agencies', 'intel sharing')},
    'klac': {'query': '("KLA Corp" OR "KLA Corporation" OR KLAC)', 'names': ('kla corp', 'kla corporation', 'kla tencor'),
             'symbols': ('KLA', 'KLAC'), 'exclude': ()},
    'lrcx': {'query': '("Lam Research" OR LRCX)', 'names': ('lam research',), 'symbols': ('LRCX',), 'exclude': ()},
    'msft': {'query': '(Microsoft OR MSFT)', 'names': ('microsoft',), 'symbols': ('MSFT',), 'exclude': ()},
    'nvda': {'query': '(Nvidia OR NVDA)', 'names': ('nvidia',), 'symbols': ('NVDA',), 'exclude': ()},
    'qcom': {'query': '(Qualcomm OR QCOM)', 'names': ('qualcomm',), 'symbols': ('QCOM',), 'exclude': ()},
    'rok': {'query': '"Rockwell Automation"', 'names': ('rockwell automation',), 'symbols': (), 'exclude': ()},
    'rtx': {'query': '(Raytheon OR "RTX Corp" OR RTX) -GeForce -Nvidia -GPU',
            'names': ('raytheon', 'rtx corp', 'rtx corporation', 'pratt whitney', 'collins aerospace'), 'symbols': ('RTX',),
            'exclude': ('geforce', 'nvidia', 'gpu', 'gpus', 'graphics', 'gaming', 'laptop', 'dlss', 'ray tracing')},
    'stry': {'query': '(Stryker OR SYK) -brigade -army', 'names': ('stryker',), 'symbols': ('SYK',),
             'exclude': ('brigade', 'army', 'armored', 'stryker vehicle', 'stryker vehicles', 'combat vehicle')},
    'tokyo_electron': {'query': '"Tokyo Electron"', 'names': ('tokyo electron',), 'symbols': (), 'exclude': ()},
}

# Official IR press-release feeds known from the companies' own sites. Every listed URL stays
# UNVERIFIED_URL until a scheduled run confirms it (live network is unavailable where this was written);
# companies without a known official feed are NOT_AVAILABLE (no third-party or guessed endpoints).
# Links inside a feed must be https on one of the company's own domains.
IR_FEEDS = {
    'amd': {'url': 'https://ir.amd.com/rss/news-releases.xml', 'domains': ('amd.com',), 'status': 'UNVERIFIED_URL'},
    'amzn': {'url': 'https://ir.aboutamazon.com/rss/news-releases.xml', 'domains': ('aboutamazon.com',), 'status': 'UNVERIFIED_URL'},
    'avgo': {'url': 'https://investors.broadcom.com/rss/news-releases.xml', 'domains': ('broadcom.com',), 'status': 'UNVERIFIED_URL'},
    'intc': {'url': 'https://www.intc.com/rss/news-releases.xml', 'domains': ('intc.com', 'intel.com'), 'status': 'UNVERIFIED_URL'},
    'klac': {'url': 'https://ir.kla.com/rss/news-releases.xml', 'domains': ('kla.com',), 'status': 'UNVERIFIED_URL'},
    'lrcx': {'url': 'https://investor.lamresearch.com/rss/news-releases.xml', 'domains': ('lamresearch.com',), 'status': 'UNVERIFIED_URL'},
    'msft': {'url': 'https://news.microsoft.com/feed/', 'domains': ('microsoft.com',), 'status': 'UNVERIFIED_URL'},
    'nvda': {'url': 'https://investor.nvidia.com/rss/news-releases.xml', 'domains': ('nvidia.com',), 'status': 'UNVERIFIED_URL'},
    'qcom': {'url': 'https://investor.qualcomm.com/rss/news-releases.xml', 'domains': ('qualcomm.com',), 'status': 'UNVERIFIED_URL'},
    'stry': {'url': 'https://investors.stryker.com/rss/news-releases.xml', 'domains': ('stryker.com',), 'status': 'UNVERIFIED_URL'},
}

# Rule-based title classification v0: first matching class wins, in this order.
CLASS_RULES = (
    ('LEGAL', ('lawsuit', 'lawsuits', 'sues', 'sued', 'suing', 'court', 'antitrust', 'probe', 'investigation', 'settlement',
               'settles', 'regulator', 'regulators', 'fine', 'fined', 'ftc', 'doj', 'class action', 'verdict', 'judge', 'patent',
               'export controls', 'export curbs', 'export ban', 'ban', 'tariff', 'tariffs', 'recall')),
    ('MA', ('acquire', 'acquires', 'acquired', 'acquiring', 'acquisition', 'acquisitions', 'merger', 'mergers', 'merge',
            'buyout', 'takeover', 'to buy', 'divest', 'divests', 'divestiture', 'spin off', 'spinoff', 'stake')),
    ('EARNINGS', ('earnings', 'results', 'revenue', 'revenues', 'profit', 'profits', 'eps', 'guidance', 'outlook', 'forecast',
                  'quarterly', 'quarter', 'fiscal', 'dividend', 'beats estimates', 'misses estimates')),
    ('PRODUCT', ('launch', 'launches', 'launched', 'unveil', 'unveils', 'unveiled', 'introduce', 'introduces', 'introduced',
                 'rolls out', 'debut', 'debuts', 'release', 'releases', 'released', 'product', 'products', 'platform')),
)
STOPWORDS = frozenset(('a', 'an', 'the', 'and', 'or', 'of', 'to', 'in', 'on', 'for', 'with', 'by', 'at', 'from', 'as', 'is',
                       'are', 'be', 'its', 'it', 'this', 'that', 'after', 'over', 'into', 'about', 'new', 'says', 'said', 'inc',
                       'corp', 'co', 'ltd', 'plc', 'llc', 's', 'will', 'has', 'have', 'than', 'up', 'down', 'amid', 'vs'))
# Exhibit titles made only of these (plus stopwords, numbers, month names and company-name words) are generic.
GENERIC_EXHIBIT = frozenset(('press', 'release', 'releases', 'news', 'dated', 'exhibit', 'ex', 'issued', 'corporation',
                             'company', 'announcing', 'announces', 'dtd', 'january', 'february', 'march', 'april', 'may',
                             'june', 'july', 'august', 'september', 'october', 'november', 'december', 'jan', 'feb',
                             'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec'))
RELATED_8K_CLASSES = {'RESULTS': 'EARNINGS'}

_ASCII_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)
_NON_TOKEN = re.compile(r'[^a-z0-9]+')
_TITLE_BAD = re.compile('[\u0000-\u001f\u007f-\u009f<>\u00a0\u1680\u180e\u2000-\u200b\u2028\u2029\u202f\u205f\u3000\ufeff]')
_INSTANT = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+00:00')
_ACCESSION = re.compile(r'[0-9]{10}-[0-9]{2}-[0-9]{6}')
_LABEL = r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?'
LINK_PATTERN = re.compile(r'(https?)://(' + _LABEL + r'(?:\.' + _LABEL + r')+)(?::[0-9]{1,5})?(?:[/?][A-Za-z0-9!$%&\'()*+,./:;=?@\[\]_~-]*)?')
TOP_KEYS = ('schema_version', 'kind', 'as_of', 'state', 'reason_codes', 'freshness_basis', 'stale_after_seconds', 'window_days',
            'channel', 'score_effect', 'attribution', 'matching_rule', 'sources', 'items')
ITEM_KEYS = ('company_id', 'source', 'title', 'link', 'published_at', 'classification', 'group_id', 'occurrence',
             'relation', 'related_8k_accession')


def _need(condition):
    if not condition:
        raise ValueError('NEWS_SIGNALS_INVALID')


def instant(value: datetime) -> str:
    _need(isinstance(value, datetime) and value.utcoffset() is not None)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _clock(value):
    _need(isinstance(value, str) and _INSTANT.fullmatch(value) is not None)
    return datetime.fromisoformat(value)


def _fresh(acquired, as_of):
    return 'STALE' if as_of - acquired > STALE_AFTER else 'LIVE'


# --- rules (mirrored in news-signals.js) ---------------------------------------------------------

def tokens(title):
    """ASCII-lowercased alphanumeric tokens; every other character separates tokens."""
    return _NON_TOKEN.sub(' ', title.translate(_ASCII_LOWER)).split()


def significant(title):
    return frozenset(t for t in tokens(title) if t not in STOPWORDS)


def _has_phrase(title_tokens, phrases):
    text = ' ' + ' '.join(title_tokens) + ' '
    return any(' ' + p + ' ' in text for p in phrases)


def classify(title):
    found = tokens(title)
    for name, phrases in CLASS_RULES:
        if _has_phrase(found, phrases):
            return name
    return 'OTHER'


def _symbol(symbol, title):
    return re.search(r'(?:^|[^A-Za-z0-9])' + symbol + r'(?=$|[^A-Za-z0-9])', title) is not None


def relevant(company_id, title):
    """GDELT minimum relevance: a name or ticker variant in the title and no exclusion phrase."""
    rule = MATCH[company_id]
    found = tokens(title)
    if _has_phrase(found, rule['exclude']):
        return False
    return _has_phrase(found, rule['names']) or any(_symbol(s, title) for s in rule['symbols'])


def similar(a, b, *, min_shared=GROUP_MIN_SHARED, min_percent=GROUP_MIN_PERCENT):
    shared = len(a & b)
    return shared >= min_shared and shared * 100 >= min_percent * len(a | b)


def valid_title(title):
    return (isinstance(title, str) and 0 < len(title) <= TITLE_MAX and _TITLE_BAD.search(title) is None
            and not title.startswith(' ') and not title.endswith(' ') and '  ' not in title)


def clean_title(raw):
    """Collected title -> one display line, or None. Whitespace-like characters become single spaces."""
    if not isinstance(raw, str):
        return None
    text = re.sub('[\u0000-\u001f\u007f-\u009f\u00a0\u1680\u180e\u2000-\u200b\u2028\u2029\u202f\u205f\u3000\ufeff]', ' ', raw)
    text = ' '.join(text.split())
    return text if valid_title(text) else None


def link_host(link):
    match = LINK_PATTERN.fullmatch(link) if isinstance(link, str) and len(link) <= LINK_MAX else None
    return (match.group(1), match.group(2)) if match else None


def canonical_link(raw):
    """http(s) URL -> lowercase scheme/host, no credentials or fragment, utm_* parameters removed; None if not acceptable."""
    if not isinstance(raw, str) or not raw.isascii() or len(raw) > LINK_MAX * 2:
        return None
    try:
        parts = urlsplit(raw.strip())
        port = parts.port
    except ValueError:
        return None
    if parts.scheme.lower() not in ('http', 'https') or '@' in parts.netloc or not parts.hostname:
        return None
    host = parts.hostname.lower() + (f':{port}' if port is not None else '')
    query = '&'.join(p for p in parts.query.split('&') if p and not p.lower().startswith('utm_'))
    link = f'{parts.scheme.lower()}://{host}{parts.path}' + (f'?{query}' if query else '')
    return link if link_host(link) is not None else None


def ir_link_allowed(company_id, link):
    found = link_host(link)
    feed = IR_FEEDS.get(company_id)
    if found is None or feed is None or found[0] != 'https':
        return False
    return any(found[1] == d or found[1].endswith('.' + d) for d in feed['domains'])


def _compact(published_at):
    return published_at[:19].replace('-', '').replace(':', '') + 'Z'


def assign_groups(items):
    """Set group_id/occurrence of RELATION NONE items in place (mirrors news-signals.js groups()).

    Items are visited oldest first (published_at, link). An item joins the earliest-created group of
    the same company whose first item is at most 72h older and similar to it; otherwise it starts a
    group `news:{company}:{first published, compact}:{n}`. IR items related to an 8-K keep the 8-K
    group and are REPEAT.
    """
    heads, counters = [], {}
    for item in sorted((i for i in items if i['relation'] == 'NONE'), key=lambda i: (i['published_at'], i['link'])):
        at, words = _clock(item['published_at']), significant(item['title'])
        for head in heads:
            if head[0] == item['company_id'] and at - head[1] <= GROUP_WINDOW and similar(words, head[2]):
                item['group_id'], item['occurrence'] = head[3], 'REPEAT'
                break
        else:
            base = f"news:{item['company_id']}:{_compact(item['published_at'])}"
            counters[base] = counters.get(base, -1) + 1
            group = f'{base}:{counters[base]}'
            heads.append((item['company_id'], at, words, group))
            item['group_id'], item['occurrence'] = group, 'NEW'
    for item in items:
        if item['relation'] == 'RELATED_TO_8K':
            item['occurrence'] = 'REPEAT'
    return items


def _order(items):
    return sorted(items, key=lambda i: (i['published_at'], i['link']), reverse=True)


# --- IR release vs 8-K Exhibit 99.1 -------------------------------------------------------------

def _name_words(company_id):
    rule = MATCH.get(company_id, {'names': (), 'symbols': ()})
    return {w for n in rule['names'] for w in n.split()} | {s.translate(_ASCII_LOWER) for s in rule['symbols']}


def generic_exhibit_title(company_id, title):
    rest = {t for t in significant(title) if t not in GENERIC_EXHIBIT and not t.isdigit()} - _name_words(company_id)
    return not rest


def related_8k(item, sec_events):
    """(accession, group_id) of the 8-K whose Exhibit 99.1 this IR release repeats, else None.

    A: same company, |time difference| <= 24h and title similarity (>= 2 shared significant tokens,
       Jaccard >= 50%) with the Exhibit 99.1 title; the closest in time wins.
    B: when the exhibit title is generic ("PRESS RELEASE DATED ..."): same company, <= 24h, a RESULTS
       8-K and an EARNINGS release, and exactly one such 8-K.
    """
    at, words = _clock(item['published_at']), significant(item['title'])
    a, b = [], []
    for e in sec_events:
        x = e.get('exhibit_99_1') or {}
        if e.get('company_id') != item['company_id'] or x.get('state') != 'AVAILABLE':
            continue
        gap = abs(at - _clock(e['accepted_at']))
        if gap > RELATED_8K_WINDOW:
            continue
        if similar(words, significant(x['title']), min_shared=RELATED_8K_MIN_SHARED, min_percent=RELATED_8K_MIN_PERCENT):
            a.append((gap, e['accession'], e['group_id']))
        elif (generic_exhibit_title(item['company_id'], x['title'])
              and RELATED_8K_CLASSES.get(e.get('classification')) == item['classification']):
            b.append((gap, e['accession'], e['group_id']))
    if a:
        return min(a)[1:]
    return b[0][1:] if len(b) == 1 else None


# --- public payload --------------------------------------------------------------------------------

def _empty_source(source, cid):
    if source == 'IR':
        feed = IR_FEEDS.get(cid)
        return {'state': 'NOT_AVAILABLE', 'acquired_at': None,
                'reason_code': 'NOT_COLLECTED' if feed else 'NO_OFFICIAL_FEED_KNOWN',
                'feed_status': feed['status'] if feed else 'NOT_AVAILABLE'}
    return {'state': 'NOT_AVAILABLE', 'acquired_at': None, 'reason_code': 'NOT_COLLECTED'}


def _companies(source):
    return GDELT_COMPANIES if source == 'GDELT' else IR_COMPANIES


def normalize(source, company_id, raw, *, acquired_at, cutoff, counts):
    """One collected raw row {'title','link','published_at'(datetime)} -> public item or None (counted)."""
    title, link = clean_title(raw.get('title')), canonical_link(raw.get('link'))
    published = raw.get('published_at')
    if title is None or link is None:
        counts['invalid'] = counts.get('invalid', 0) + 1
        return None
    if not isinstance(published, datetime) or published.utcoffset() is None:
        counts['invalid'] = counts.get('invalid', 0) + 1
        return None
    published = published.astimezone(timezone.utc).replace(microsecond=0)
    if published > acquired_at or published < cutoff:
        counts['out_of_window'] = counts.get('out_of_window', 0) + 1
        return None
    if source == 'GDELT' and not relevant(company_id, title):
        counts['irrelevant'] = counts.get('irrelevant', 0) + 1
        return None
    if source == 'IR' and not ir_link_allowed(company_id, link):
        counts['foreign_link'] = counts.get('foreign_link', 0) + 1
        return None
    return {'company_id': company_id, 'source': source, 'title': title, 'link': link, 'published_at': instant(published),
            'classification': classify(title), 'group_id': None, 'occurrence': None, 'relation': 'NONE',
            'related_8k_accession': None}


def _dedupe(items, counts):
    """One item per link, then per (company, normalized title); IR beats GDELT, then the earliest."""
    rank = sorted(items, key=lambda i: (i['source'] != 'IR', i['published_at'], i['link']))
    links, titles, out = set(), set(), []
    for item in rank:
        key = (item['company_id'], ' '.join(tokens(item['title'])))
        if item['link'] in links or key in titles:
            counts['duplicates'] = counts.get('duplicates', 0) + 1
            continue
        links.add(item['link'])
        titles.add(key)
        out.append(item)
    return out


def merge(previous, collected, *, as_of, sec=None, counts=None):
    """Build the next public payload.

    previous: validated payload or None. collected: {'GDELT'|'IR': {company_id: {'acquired_at': datetime,
    'rows': [{'title','link','published_at'}]}}} for sources/companies collected this run. sec: validated
    `sec-disclosures.json` payload or None (8-K relation). Items of collected companies are added to their
    previous items; companies not collected keep previous items and acquisition time. Rolling window.
    """
    counts = {} if counts is None else counts
    as_of = datetime.fromisoformat(instant(as_of))
    cutoff = as_of - timedelta(days=WINDOW_DAYS)
    sources, items = {}, []
    previous_items = previous['items'] if previous is not None else []
    for source in SOURCES:
        sources[source] = {}
        for cid in _companies(source):
            empty = _empty_source(source, cid)
            got = collected.get(source, {}).get(cid)
            old_entry = previous['sources'][source][cid] if previous is not None else None
            old_rows = [dict(i) for i in previous_items if i['source'] == source and i['company_id'] == cid
                        and _clock(i['published_at']) >= cutoff]
            if source == 'IR' and cid not in IR_FEEDS:
                sources[source][cid] = empty
                continue
            if got is not None:
                acquired = datetime.fromisoformat(instant(got['acquired_at']))
                _need(acquired <= as_of)
                fresh = [n for n in (normalize(source, cid, r, acquired_at=acquired, cutoff=cutoff, counts=counts)
                                     for r in got['rows']) if n is not None]
                known = {i['link'] for i in old_rows}
                rows = old_rows + [n for n in fresh if n['link'] not in known]
                acquired_at = instant(acquired)
            elif old_entry is not None and old_entry['acquired_at'] is not None:
                rows, acquired_at = old_rows, old_entry['acquired_at']
            else:
                sources[source][cid] = empty
                continue
            rows = _order(rows)[:PER_COMPANY_MAX[source]]
            sources[source][cid] = {'state': _fresh(_clock(acquired_at), as_of), 'acquired_at': acquired_at, 'reason_code': None}
            if source == 'IR':
                sources[source][cid]['feed_status'] = IR_FEEDS[cid]['status']
            items.extend(rows)
    items = _dedupe(items, counts)
    old_relation = {i['link']: (i['related_8k_accession'], i['group_id']) for i in previous_items if i['relation'] == 'RELATED_TO_8K'}
    for item in items:
        if item['source'] != 'IR':
            continue
        found = related_8k(item, sec['events']) if sec is not None else old_relation.get(item['link'])
        if found:
            item.update(relation='RELATED_TO_8K', related_8k_accession=found[0], group_id=found[1], occurrence='REPEAT')
        else:
            item.update(relation='NONE', related_8k_accession=None)
    payload = _payload(as_of, sources, items)
    while len(encode(payload)) > SIZE_BUDGET and payload['items']:
        payload['items'] = _order(assign_groups(payload['items'][:-1]))
    return require_news_signals(payload)


def _payload(as_of, sources, items):
    states = [c['state'] for s in SOURCES for c in sources[s].values()]
    state = 'LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else 'NOT_AVAILABLE'
    items = _order(assign_groups(_order(items)[:MAX_ITEMS]))
    return {'schema_version': 1, 'kind': KIND, 'as_of': instant(as_of), 'state': state,
            'reason_codes': [] if state == 'LIVE' else ['STALE_INPUT'] if state == 'STALE' else ['NO_ELIGIBLE_INPUT'],
            'freshness_basis': 'SOURCE_ACQUISITION', 'stale_after_seconds': int(STALE_AFTER.total_seconds()),
            'window_days': WINDOW_DAYS, 'channel': 'NEWS', 'score_effect': 'NONE',
            'attribution': json.loads(json.dumps(ATTRIBUTION)), 'matching_rule': MATCHING_RULE,
            'sources': sources, 'items': items}


def _require(p):
    _need(isinstance(p, dict) and set(p) == set(TOP_KEYS))
    _need(type(p['schema_version']) is int and p['schema_version'] == 1 and p['kind'] == KIND)
    cut = _clock(p['as_of'])
    _need(p['freshness_basis'] == 'SOURCE_ACQUISITION' and p['channel'] == 'NEWS' and p['score_effect'] == 'NONE')
    _need(type(p['stale_after_seconds']) is int and p['stale_after_seconds'] == int(STALE_AFTER.total_seconds()))
    _need(type(p['window_days']) is int and p['window_days'] == WINDOW_DAYS)
    _need(p['attribution'] == ATTRIBUTION and p['matching_rule'] == MATCHING_RULE)
    _need(isinstance(p['sources'], dict) and set(p['sources']) == set(SOURCES))
    acquired, states = {}, []
    for source in SOURCES:
        entries = p['sources'][source]
        _need(isinstance(entries, dict) and set(entries) == set(_companies(source)))
        for cid, c in entries.items():
            keys = {'state', 'acquired_at', 'reason_code'} | ({'feed_status'} if source == 'IR' else set())
            _need(isinstance(c, dict) and set(c) == keys)
            if source == 'IR':
                feed = IR_FEEDS.get(cid)
                # A listed feed may be VERIFIED later without invalidating earlier copies.
                _need(c['feed_status'] in (('VERIFIED', 'UNVERIFIED_URL') if feed else ('NOT_AVAILABLE',)))
                if feed is None:
                    _need(c['acquired_at'] is None and c['reason_code'] == 'NO_OFFICIAL_FEED_KNOWN')
            if c['acquired_at'] is None:
                _need(c['state'] == 'NOT_AVAILABLE' and c['reason_code'] in COMPANY_REASONS)
                _need(c['reason_code'] == 'NOT_COLLECTED' or source == 'IR' and cid not in IR_FEEDS)
            else:
                at = _clock(c['acquired_at'])
                _need(at <= cut and c['reason_code'] is None and c['state'] == _fresh(at, cut))
                acquired[(source, cid)] = at
            states.append(c['state'])
    state = 'LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else 'NOT_AVAILABLE'
    _need(p['state'] == state)
    _need(p['reason_codes'] == ([] if state == 'LIVE' else ['STALE_INPUT'] if state == 'STALE' else ['NO_ELIGIBLE_INPUT']))
    items = p['items']
    _need(isinstance(items, list) and len(items) <= MAX_ITEMS)
    cutoff = cut - timedelta(days=WINDOW_DAYS)
    links, titles, per = set(), set(), {}
    for i in items:
        _need(isinstance(i, dict) and set(i) == set(ITEM_KEYS))
        _need(i['source'] in SOURCES and (i['source'], i['company_id']) in acquired)
        _need(valid_title(i['title']) and isinstance(i['link'], str) and link_host(i['link']) is not None)
        if i['source'] == 'GDELT':
            _need(relevant(i['company_id'], i['title']))
        else:
            _need(ir_link_allowed(i['company_id'], i['link']))
        at = _clock(i['published_at'])
        _need(cutoff <= at <= acquired[(i['source'], i['company_id'])])
        _need(i['classification'] in CLASSIFICATIONS and i['classification'] == classify(i['title']))
        _need(i['occurrence'] in OCCURRENCES and i['relation'] in RELATIONS)
        if i['relation'] == 'RELATED_TO_8K':
            acc = i['related_8k_accession']
            _need(i['source'] == 'IR' and isinstance(acc, str) and _ACCESSION.fullmatch(acc) is not None)
            _need(isinstance(i['group_id'], str) and re.fullmatch(re.escape(i['company_id']) + r':[0-9]{10}-[0-9]{2}-[0-9]{6}', i['group_id']) is not None)
        else:
            _need(i['related_8k_accession'] is None)
        key = (i['company_id'], ' '.join(tokens(i['title'])))
        _need(i['link'] not in links and key not in titles)
        links.add(i['link'])
        titles.add(key)
        per[(i['source'], i['company_id'])] = per.get((i['source'], i['company_id']), 0) + 1
    _need(all(n <= PER_COMPANY_MAX[s] for (s, _), n in per.items()))
    _need(items == _order(items))
    expected = assign_groups([dict(i) for i in items])
    _need(all(a['group_id'] == b['group_id'] and a['occurrence'] == b['occurrence'] for a, b in zip(items, expected)))
    return p


def require_news_signals(payload):
    try:
        return _require(payload)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise ValueError('NEWS_SIGNALS_INVALID') from None


def encode(payload):
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')


def parse_json(body):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('NEWS_SIGNALS_INVALID')
            out[key] = value
        return out

    def constant(_value):
        raise ValueError('NEWS_SIGNALS_INVALID')
    try:
        if not isinstance(body, bytes) or len(body) > MAX_BYTES:
            raise ValueError
        return json.loads(body.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError('NEWS_SIGNALS_INVALID') from None
