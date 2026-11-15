"""Pinned, offline private-file projections over existing KIS result contracts.

Saved projection does not calculate indicators or patterns, request data, read a
clock or write a file. The explicit fresh helper alone calls the existing kernel.
"""
from copy import deepcopy
from datetime import date
import hashlib
import re

from ._private_artifacts import digest,json_bytes,MAX_BYTES
from .kis_price_bridge import validate_contract,price_rows,_day
from .kis_split_evidence import assess_splits
from .technical_handoff import prepare_technical
from .exp_deciles import schedule

SCOPE='OWNER_PRIVATE_ONLY'


def _need(ok,reason):
    if not ok:raise ValueError(reason)


def _pin(value,expected,kind):
    _need(isinstance(expected,str) and re.fullmatch(r'[0-9a-f]{64}',expected) is not None and
        digest(value)==expected,kind+'_HASH_MISMATCH')


def _bytes(value):
    raw=json_bytes(value)
    _need(len(raw)<=MAX_BYTES,'PRIVATE_ARTIFACT_TOO_LARGE')
    return raw


def project_technical(c,handoff,*,expected_contract_hash,expected_handoff_hash):
    """Project independently pinned saved results; never recompute their metrics.

    Original source/body provenance remains in the chart contract. Price rows are
    reselected through S with the existing split normalizer, excluding later
    archive events without changing source query or capture clocks.
    """
    _pin(c,expected_contract_hash,'CONTRACT');_pin(handoff,expected_handoff_hash,'HANDOFF')
    _need(c.get('schema')=='kis-bars/1' and c.get('publication_scope')==SCOPE,'PRIVATE_CONTRACT_REQUIRED')
    _need(handoff.get('schema')=='kis-technical-handoff/1' and
        handoff.get('publication_scope')==SCOPE,'PRIVATE_HANDOFF_REQUIRED')
    _need(handoff.get('result_sha256')==digest({k:v for k,v in handoff.items() if k!='result_sha256'}),
        'HANDOFF_RESULT_HASH_MISMATCH')
    validate_contract(c)
    context=handoff.get('context') or {};day=_day(context.get('signal_day'))
    _need(schedule.is_session(date.fromisoformat(day)),'SIGNAL_DAY_NOT_A_SESSION')
    assessment=assess_splits(c,day)
    _need(not assessment['block_reasons'],assessment['block_reasons'][0] if assessment['block_reasons'] else 'SPLIT_EVIDENCE_CONFLICT')
    symbol=c.get('symbol')
    _need(isinstance(symbol,str) and len(symbol)<=16 and
        re.fullmatch(r'[A-Z0-9][A-Z0-9.-]*(?:/[A-Z])?',symbol) is not None,'INVALID_STORAGE_SYMBOL')
    provenance=handoff.get('provenance') or {}
    expected_provenance=dict(contract_hash=expected_contract_hash,source_sha256=c['source_sha256'],
        source_query=c['source_query'],source=c['source'],identity=c['identity'],currency_reference=c['currency_reference'])
    _need(all(provenance.get(k)==v for k,v in expected_provenance.items()),'HANDOFF_PROVENANCE_MISMATCH')
    _need(context.get('collected_at')==c['collected_at'] and
        context.get('historical_available_at')==c.get('historical_available_at') and
        context.get('last_success_at')==c.get('last_success_at',c['collected_at']) and
        context.get('update_state')==c.get('update_state','RETAINED_ARCHIVE') and
        context.get('timestamp_basis')==c['timestamp_basis'],'HANDOFF_CAPTURE_CONTEXT_MISMATCH')
    _need(handoff.get('data_kind')==('SYNTHETIC' if c.get('fixture_kind')=='SYNTHETIC_NOT_A_COMPANY' else 'RETAINED_INPUT'),
        'HANDOFF_EVIDENCE_KIND_MISMATCH')
    chart=handoff.get('chart') or {};bars=chart.get('bars')
    _need(isinstance(bars,list),'HANDOFF_CHART_REQUIRED')
    _need(all(_day(r.get('date'))<=day for r in bars),'FUTURE_CHART_ROW')
    _need(all(chart.get(k)==c[k] for k in ('basis','currency','dividend_adjustment','volume_basis','amount_basis')),
        'HANDOFF_CHART_BASIS_MISMATCH')
    selected=price_rows(c,day);raw=[r for r in c['raw_bars'] if r['date']<=day]
    _need(bars==selected,'HANDOFF_CHART_ROWS_MISMATCH')
    observed=selected[-1]['date'] if selected else None
    components=handoff.get('components') or {};measures=handoff.get('measures') or {}
    _need(components.get('schema')=='kis-bars/1/analysis' and measures.get('schema')=='kis-technical-measures/1',
        'HANDOFF_COMPONENT_SCHEMA_MISMATCH')
    for result in (components,measures):
        _need(result.get('symbol')==symbol,'HANDOFF_SYMBOL_MISMATCH')
        _need(result.get('evaluation_day')==day,'HANDOFF_EVALUATION_MISMATCH')
        _need(result.get('data_asof')==observed and result.get('collected_at')==c['collected_at'],
            'HANDOFF_OBSERVATION_MISMATCH')
        _need(result.get('chart_basis')==c['basis'] and result.get('diagnostic_basis')==c['basis'],
            'HANDOFF_CHART_BASIS_MISMATCH')
        _need(result.get('publication_scope',SCOPE)==SCOPE,'PRIVATE_HANDOFF_REQUIRED')
    _need(context.get('chart_observation_day')==observed and context.get('measure_observation_day')==observed,
        'HANDOFF_OBSERVATION_MISMATCH')
    sessions=handoff.get('sessions') or {}
    _need(sessions.get('checked_to')==day and sessions.get('retained_count')==len(raw) and
        sessions.get('checked_from')==(raw[0]['date'] if raw else None) and
        sessions.get('calendar')==c['calendar'] and sessions.get('timezone')==c['timezone'] and
        context.get('excluded_future_rows')==len(c['raw_bars'])-len(raw),'HANDOFF_SESSION_CONTEXT_MISMATCH')
    projected=deepcopy(c)
    projected.update(raw_bars=deepcopy(raw),bars=deepcopy(selected),price_basis_date=observed,
        splits=[deepcopy(s) for s in c['splits'] if raw and s['date']<=day])
    validate_contract(projected)
    storage_symbol=symbol.replace('/','_');suffix=symbol[0]+'/'+storage_symbol+'.json'
    objects={'chart/'+suffix:projected,'technical/'+suffix:deepcopy(components),
             'measures/'+suffix:deepcopy(measures)}
    files={path:_bytes(value) for path,value in objects.items()}
    manifest=dict(schema='kis-private-preprocess-manifest/1',publication_scope=SCOPE,
        symbol=symbol,storage_symbol=storage_symbol,symbol_encoding='SLASH_TO_UNDERSCORE_STORAGE_ONLY',
        signal_day=day,collected_at=c['collected_at'],generated_at=None,generated_at_reason='NOT_RECORDED',
        historical_pit_proven=False,source_contract_hash=expected_contract_hash,
        source_handoff_hash=expected_handoff_hash,source_result_sha256=handoff['result_sha256'],
        projection_recalculated_metrics=False,
        delivery_state='PATHS_READY_NOT_DEPLOYED' if re.fullmatch(r'[A-Z][A-Z0-9-]{0,9}',symbol) else 'BLOCKED_ROUTE_MAPPING_REQUIRED',
        worker_authentication='NOT_VERIFIED',worker_allowlist='NOT_VERIFIED',
        qgv=dict(state='NOT_PRODUCED_555_DEPENDENCY',retain_previous=True,files_written=[]),
        files=[dict(path=path,bytes=len(value),sha256=hashlib.sha256(value).hexdigest(),
                    schema=objects[path]['schema']) for path,value in sorted(files.items())])
    files['manifests/'+suffix]=_bytes(manifest)
    return files


def calculate_and_project(c,*,evaluation_day,series_id,expected_contract_hash):
    """Explicit fresh calculation via the existing split-aware kernel, then project."""
    _pin(c,expected_contract_hash,'CONTRACT')
    handoff=prepare_technical(c,evaluation_day=evaluation_day,series_id=series_id,include_split_assessment=True)
    return project_technical(c,handoff,expected_contract_hash=expected_contract_hash,expected_handoff_hash=digest(handoff))
