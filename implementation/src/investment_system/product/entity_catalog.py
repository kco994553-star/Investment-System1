"""Read-only entity navigation adapter; no scores or issuer/listing inference."""
from copy import deepcopy

from .entity_metadata import catalog_fields, load_registry, normalize

# Presentation aliases keyed by existing company_id, never by a guessed ticker.
COMPANY_ALIASES = {
    'nvda': {'en-US': ['NVIDIA'], 'ko-KR': ['엔비디아']},
    'asml': {'en-US': ['ASML'], 'ko-KR': ['에이에스엠엘', 'ASML 홀딩']},
    'aapl': {'en-US': ['Apple'], 'ko-KR': ['애플']},
    'msft': {'en-US': ['Microsoft'], 'ko-KR': ['마이크로소프트']},
    'amd': {'en-US': ['AMD'], 'ko-KR': ['에이엠디']},
    'amzn': {'en-US': ['Amazon'], 'ko-KR': ['아마존']},
    'googl': {'en-US': ['Google'], 'ko-KR': ['구글', '알파벳']},
    'avgo': {'en-US': ['Broadcom'], 'ko-KR': ['브로드컴']},
    'intc': {'en-US': ['Intel'], 'ko-KR': ['인텔']},
    'qcom': {'en-US': ['Qualcomm'], 'ko-KR': ['퀄컴']},
    'lrcx': {'en-US': ['Lam Research'], 'ko-KR': ['램리서치']},
    'klac': {'en-US': ['KLA'], 'ko-KR': ['케이엘에이']},
}
TYPES = frozenset({'COMPANY', 'INDUSTRY', 'INVESTOR', 'MACRO', 'THEME', 'PORTFOLIO', 'NEWS', 'PROMPT'})
# A navigation taxonomy, not an investment universe or inferred company classification.
NAV_ENTITIES = (
    {'entity_type': 'INDUSTRY', 'canonical_id': 'semiconductor', 'canonical_label': 'Semiconductor',
     'localized_names': {'ko-KR': '반도체', 'en-US': 'Semiconductor'}, 'aliases': {'en-US': ['Semiconductors']},
     'source': 'Global Search presentation taxonomy v1'},
    {'entity_type': 'MACRO', 'canonical_id': 'CPIAUCSL', 'canonical_label': 'Consumer Price Index',
     'localized_names': {'ko-KR': '소비자물가지수', 'en-US': 'Consumer Price Index'},
     'aliases': {'en-US': ['CPI'], 'ko-KR': ['소비자 물가']},
     'source': 'providers/fred_csv.py SERIES inflation (mapping remains PROVISIONAL)'},
)


def _merge_unique(base, extra):
    # Dedupe on the search normalization so one label is indexed once per entity.
    keys = {normalize(v) for v in base}
    for v in extra:
        if normalize(v) not in keys:
            base.append(v)
            keys.add(normalize(v))
    return base


def entity_catalog(bundle, metadata=None):
    """Add navigation metadata only; preserve the entire producer bundle unchanged.

    ``metadata`` is the CIK-bound search metadata registry (default: the committed one; False disables).
    It only fills absent fields/locales of existing company_ids; producer and curated values win as supplied.
    """
    # Reuse the existing identity registry, not its ticker resolution or any engine.
    from ..qgv.identifiers import OFFICIAL_PORTFOLIO_V11
    registered = {r.company_id: r for r in OFFICIAL_PORTFOLIO_V11}
    metadata = load_registry() if metadata is None else metadata
    universe = (bundle.get('universe') or {}).get('data')
    entities = []
    for c in bundle['companies']:
        record = registered.get(c['company_id'])
        meta = catalog_fields(metadata, c['company_id'], universe) or {}
        official = c.get('official_name') or c.get('name')
        if record and (not official or official == c['ticker'] or official == c['company_id']):
            official = record.legal_name
        if meta.get('official_name') and (not official or official == c['ticker'] or official == c['company_id']):
            official = meta['official_name']
        aliases = deepcopy(COMPANY_ALIASES.get(c['company_id'], {}))
        for locale, values in c.get('aliases', {}).items():
            if not isinstance(values, list) or any(not isinstance(a, str) for a in values):
                raise ValueError('aliases must be lists of text')
            aliases.setdefault(locale, []).extend(values)
        # Fill-only: a curated/producer locale list stays exactly as supplied.
        extra = deepcopy(meta.get('aliases', {}))
        if official and meta.get('official_name') and normalize(meta['official_name']) != normalize(official):
            # Registered SEC name kept searchable when a different display label is in use.
            _merge_unique(extra.setdefault('en-US', []), [meta['official_name']])
        for locale, values in extra.items():
            if not aliases.get(locale):
                aliases[locale] = _merge_unique([], values)
        localized = deepcopy(c.get('localized_names', {}))
        for locale, values in aliases.items():
            # 'und' holds language-neutral listing tickers; never a display name.
            if values and locale not in localized and locale != 'und':
                localized[locale] = values[0]
        entity = {
            'entity_type': 'COMPANY', 'canonical_id': c['company_id'],
            'canonical_label': official or c['ticker'], 'ticker': c['ticker'],
            'localized_names': localized, 'aliases': aliases,
            'historical_names': deepcopy(c['historical_names'] if 'historical_names' in c else meta.get('historical_names', [])),
            'historical_tickers': deepcopy(c['historical_tickers'] if 'historical_tickers' in c else meta.get('historical_tickers', [])),
            'industry': c.get('industry') or (record.industry or record.sector if record else None),
            'ambiguity_flags': list(c.get('ambiguity_flags', record.ambiguity_flags if record else [])),
            'source': c.get('metadata_source') or ('qgv/identifiers.py (presentation only)' if record else 'producer companies'),
            'data_state': 'DEMO' if c.get('demo') else bundle['universe']['state'],
        }
        if meta:
            entity['metadata_provenance'] = meta['metadata_provenance']
        entities.append(entity)
    entities.extend(deepcopy(NAV_ENTITIES))
    # Extension records are explicit producer registrations. No investor is seeded.
    for e in bundle.get('search_entities', []):
        e = deepcopy(e)
        if e.get('entity_type') not in TYPES - {'COMPANY'}:
            raise ValueError('company search identity must come from companies')
        if not all(isinstance(e.get(k), str) and e[k].strip() for k in ('canonical_id', 'canonical_label', 'source')):
            raise ValueError('registered entity requires canonical identity, label and source')
        entities.append(e)
    keys = [(e['entity_type'], e['canonical_id']) for e in entities]
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate canonical search identity')
    for e in entities:
        if not isinstance(e.get('localized_names', {}), dict) or not isinstance(e.get('aliases', {}), dict):
            raise ValueError('localized names and aliases must be locale maps')
        if any(not isinstance(v, str) for v in e.get('localized_names', {}).values()):
            raise ValueError('localized name must be text')
        if any(not isinstance(v, list) or any(not isinstance(a, str) for a in v) for v in e.get('aliases', {}).values()):
            raise ValueError('aliases must be lists of text')
        for k in ('historical_names', 'historical_tickers'):
            if not isinstance(e.get(k, []), list) or any(not isinstance(a, str) for a in e.get(k, [])):
                raise ValueError('historical search labels must be lists of text')
    return {'schema_version': 1, 'entities': entities}
