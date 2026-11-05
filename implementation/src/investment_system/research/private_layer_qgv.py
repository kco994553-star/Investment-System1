"""Owner-private QGV projection through the unchanged central calculation path.

The supplier adapter never invokes the public IEX publication serializer, signs a
publication, selects TARGET, or changes a population/weight/gate. No network/I/O.
"""
from datetime import date, datetime
import hashlib
import json
from types import SimpleNamespace
from investment_system.qgv import qgv_official as common
from investment_system.qgv import qgv_v2, v2_factors
from investment_system.providers import iex_hist
from .kis_price_bridge import validate_contract, _ts


RESULT_SCHEMA = 'kis-qgv/1'


def compute_private_qgv(payload, contracts, *, price_basis_date, calculated_at, monthends=None):
    if payload.get('calc_version')!=v2_factors.CALC_VERSION:raise ValueError('CALC_VERSION_MISMATCH')
    date.fromisoformat(price_basis_date); now=_ts(calculated_at)
    if price_basis_date>now.date().isoformat():raise ValueError('PRICE_BASIS_IN_FUTURE')
    if _ts(payload['as_of'])>now:raise ValueError('INPUT_VERSION_NOT_AVAILABLE')
    ctx=common.prepare(payload,now)
    quotes,status={},{}
    for key,code in ctx['keys'].items():
        c=contracts.get(code)
        if c is None:status[key]='PRICE_NOT_AVAILABLE';continue
        validate_contract(c)
        expected=code.split(':',1) if code else [None,None]
        if c['symbol']!=expected[1] or c['exchange']!=expected[0]:
            status[key]='PRICE_IDENTITY_CONFLICT';continue
        if _ts(c['collected_at'])>now:status[key]='PRICE_NOT_YET_AVAILABLE';continue
        identity=c['identity']
        if identity.get('identity_status') not in ('CONFIRMED','DOCUMENT_RECONSTRUCTED') or not identity.get('identity_reference') or not (identity.get('identity_start') or '9999')<=price_basis_date<=(identity.get('identity_end') or '0000'):
            status[key]='SOURCE_SECURITY_UNCONFIRMED';continue
        # Preserve the official single-basis-day rule; no last observation carry.
        r=next((r for r in c['raw_bars'] if r['date']==price_basis_date),None)
        if not r or r['close'] is None:status[key]='PRICE_BASIS_DATE_MISSING';continue
        if any(r['from']<=price_basis_date<=r['to'] for r in c['held_ranges']):
            status[key]='PRICE_INPUT_HELD';continue
        raw_v=common._raw_v(payload,key) or {}
        share_end=(raw_v.get('diluted_shares') or {}).get('period_end')
        if share_end and any(share_end<s['date']<=price_basis_date for s in c['splits']):
            status[key]='SPLIT_AFTER_SHARE_COUNT';continue
        quotes[key]={'price':float(r['close']),'currency':c['currency']}
        status[key]=iex_hist.SUPPLIED
    day=SimpleNamespace(day=price_basis_date,quotes=quotes,status=status)
    # Same withdrawn identity, ADR/share basis and split checks as the public path.
    statuses=common.price_status(ctx,day,months=monthends or {})
    engine_quotes,left=common.engine_quotes(ctx,day,statuses,monthends or {})
    results=common.score(ctx,engine_quotes)
    rows={key:common.projection(value) for key,value in results.items()}
    counts={'codes':len(payload['records']),
            'Q':sum(rows[k]['axes']['Q']['score'] is not None for k in payload['records']),
            'G':sum(rows[k]['axes']['G']['score'] is not None for k in payload['records']),
            'V':sum(rows[k]['axes']['V']['score'] is not None for k in payload['records']),
            'QGV':sum(all(rows[k]['axes'][a]['score'] is not None for a in ('Q','G','V')) for k in payload['records']),
            'engine_total_without_V':sum(rows[k]['total'] is not None and rows[k]['axes']['V']['score'] is None for k in payload['records']),
            'engine_total_computed':sum(rows[k]['total'] is not None for k in payload['records'])}
    return {'schema':RESULT_SCHEMA,'layer':'OWNER_PRIVATE','calculation_path':'qgv_official.prepare/price_status/engine_quotes/score/projection',
            'calc_version':payload['calc_version'],'engine_version':qgv_v2.VERSION,
            'weights':common.weights_block(),'config_versions':common.config_versions_block(),
            'population':sorted(payload['records']),'population_sha256':hashlib.sha256(json.dumps(sorted(payload['records'])).encode()).hexdigest(),
            'input_sha256':hashlib.sha256(common._canonical(payload)).hexdigest(),
            'financial_input_as_of':payload['as_of'],'price_basis_date':price_basis_date,'calculated_at':calculated_at,
            'historical_pit_proven':False,'supplier':'KIS retained MODP0; missing quotes stay absent',
            'price_status':statuses,'price_rows_supplied':len(engine_quotes),'monthend_exclusions':left,
            'rows':rows,'coverage':counts,'rank':None,'rank_reason':'PAIRED_COMPARISON_POPULATION_NOT_ESTABLISHED',
            'official_publication_replaced':False,'TARGET_modified':False}
