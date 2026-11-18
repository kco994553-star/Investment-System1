"""Cost-independent extension preparation; all accounting stays in runner."""
from dataclasses import asdict

from . import pit_adapter as pit, scoring_adapter as scoring
from .cache import digest
from .extensions import SelectionPlan, finite, matched_plans, selection_plan
from .universe import build_universe_view, adjust_valuation_quotes, factor_values,validate_adr_distributions


def prepare(bundle, group, signal, calendar, cache, dependencies, stats, *, variants=('W0',)):
    keys = dict(dependencies,group=group,signal=str(signal))
    def pit_factory():
        stats['pit_calls'] += 1
        view = build_universe_view(bundle, group, signal, calendar)
        validate_adr_distributions(bundle,view.identities,signal)
        rows = pit.build_pit_rows(bundle['companyfacts_by_cik'],bundle['filings'],view.membership,
                                  bundle['prices'],signal,calendar)
        for sid,row in rows.items():
            row.update(issuer_id=view.identities[sid]['issuer_id'],security_type=view.identities[sid]['security_type'],
                       market_cap_usd=view.identities[sid]['market_cap_usd'])
        quotes = pit.quotes_as_of(bundle['prices'],signal,calendar=calendar)
        quotes, valuation_reasons = adjust_valuation_quotes(bundle,view.identities,rows,quotes,signal,calendar)
        factors,reasons = factor_values(bundle,view.identities,signal,calendar)
        return dict(rows=rows,quotes=quotes,identities=view.identities,exclusions=view.exclusions,
                    cap_floor_usd=view.floor_usd,factors=factors,factor_reasons=reasons,valuation_reasons=valuation_reasons)
    payload = cache.get_or_compute('pit',keys,pit_factory)
    def score_factory():
        stats['score_calls'] += 1
        return scoring.score_variants(payload['rows'],payload['quotes'],variants=variants)
    scores = cache.get_or_compute('scores',dict(keys,pit=digest(payload),variants=list(variants)),score_factory)
    return payload,scores


def plans(payload,scores,cell,signal,cache,dependencies):
    identities,w0 = payload['identities'],scores['scores'][cell.get('variant','W0')]
    keys = dict(dependencies,group=cell['group'],signal=str(signal),selector=cell['id'],panel=cell['panel'],
                scored_population=digest(dict(payload=payload,scores=scores)))
    def factory():
        if cell['kind']=='FIXED_N':
            variant=cell['variant']
            eligible=scores['panels'][cell['panel']][variant]
            chosen=scoring.select_top(w0,payload['rows'],cell['n'],eligible_ids=eligible)
            return [asdict(SelectionPlan(cell['group'],str(signal),'FIXED_N',cell['panel'],chosen,
                cell['n'],len(eligible),False,len(identities)-len(eligible)))]
        if cell['kind'] == 'FACTOR_PAIR':
            pair = matched_plans(identities,w0,payload['factors'].get(cell['factor_id'],{}),
                factor_id=cell['factor_id'],group=cell['group'],signal_day=str(signal),panel=cell['panel'])
            return [asdict(plan) for plan in pair]
        first = selection_plan(identities,w0,group=cell['group'],signal_day=str(signal),
                               decile=cell.get('decile',1),panel=cell['panel'])
        if cell['kind'] == 'ELIGIBLE_EW':
            # Gather every eligible issuer through the same selector, not a
            # second eligibility implementation with a different denominator.
            selected = tuple(row for decile in range(1,11) for row in selection_plan(
                identities,w0,group=cell['group'],signal_day=str(signal),decile=decile,panel=cell['panel']).selected)
            first = SelectionPlan(cell['group'],str(signal),'ELIGIBLE_EW',cell['panel'],selected,len(selected),len(selected),False,len(identities)-len(selected))
        return [asdict(first)]
    raw = cache.get_or_compute('selection',keys,factory)
    return [SelectionPlan(**dict(record,selected=tuple(record['selected']))) for record in raw]
