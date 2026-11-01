"""Pure orchestration of EXP-STOCK-INDICATOR-DECILES-v1: the selection stage of one signal year and the ledger stage.

New for this experiment (nothing ported). No file, network or provider access: the CLI
(implementation/tools/exp_stock_indicator_deciles.py) reads the verified bundle, calls these two functions and writes their
JSON-ready results; this module only calls the package's pure functions in the fixed order (settings doc section 6.1).

Selection stage (selection_stage, one signal year from the frozen schedule):
  records -> universe.build_universes (previous U-A member CIKs passed in for later years) -> pit.build_rows for the U-A
  representative securities (one issuer at a time, companyfacts loaded lazily) -> scoring.score_population on the U-A
  population -> selection.select_all for U_A and U_B.
  Returns a selection_inputs/1 dict (SELECTION_SCHEMA): run metadata, the signal context, counts (securities; candidate /
  eligible / excluded / unknown and by-reason counts per group; U-A transitions; scoring coverage; per strategy and group
  status, N, k, NOT_RUN reason and not-eligible reasons), every security's universe status and reasons, every issuer's
  market cap, representative and group statuses, the PIT rows, factor / axis / total scores, gate flags, ranks and the
  top / bottom lists. 'QGV_DEFAULT' is recorded in strategy_aliases (-> QGV_BALANCED), never as a second selection.
  ADR quotes: the quote of an ADR representative is per ADS; it is divided by the record's adr_ratio so the engine sees
  a price per ordinary share (quote_basis ADR_PER_ORDINARY_SHARE); without a confirmed ratio it is withheld with
  ADR_RATIO_UNCONFIRMED. Quote prices given as decimal text are read as Decimal.

Ledger stage (ledger_stage, one or more consecutive yearly selection_inputs):
  - portfolios: one per strategy x group x side (TOP / BOTTOM) plus GROUP_EQUAL_WEIGHT per group (every U-A / U-B member
    security at that S, settings doc section 1 "같은 그룹 적격 전체 동일가중");
  - a strategy NOT_RUN in a year (or a group with no members) holds cash that year: its Rebalance has no selected names, so
    the ledger sells what it holds at that T open and keeps the cash; the year is recorded with holding 'CASH' and the
    reason. A portfolio that is cash in every year is ALL_CASH and no ledger is run for it;
  - every other portfolio: ledger.run_scenarios (LOSS and CARRY) at 0 bp and at settings.COST_BPS_PER_SIDE, then
    metrics.cost_comparison (which holds metrics.ledger_metrics of both runs) per scenario;
  - optional external total-return series: benchmarks.external_tr_benchmark from the first T and
    metrics.series_metrics; a refused label is recorded as REFUSED with its code, the rest of the stage continues;
  - sessions are the canonical NYSE rule calendar (schedule.is_session) from the first S; every run stops at `end`,
    which defaults to the S of the year after the last selection year (the last close before the next reselection) when
    that year is in the frozen schedule, else the last price-row date.
  Returns a ledger_outputs/1 dict (LEDGER_SCHEMA). 'QGV_DEFAULT' is an alias of the QGV_BALANCED portfolios.

Both results are JSON-ready (handoff.jsonable): Decimals as text, dates as ISO text, so the in-memory result and its JSON
file are the same object.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from typing import Mapping

from . import benchmarks, handoff, ledger, metrics, pit, schedule, scoring, selection, settings, universe

SELECTION_SCHEMA = 'exp-deciles-selection-inputs/1'
LEDGER_SCHEMA = 'exp-deciles-ledger-outputs/1'
SIDES = ('TOP', 'BOTTOM')
KIND_STRATEGY = 'STRATEGY'
KIND_GROUP_EW = benchmarks.GROUP_EQUAL_WEIGHT
HOLD_SELECTED, HOLD_CASH = 'SELECTED', 'CASH'
PORTFOLIO_RUN, PORTFOLIO_ALL_CASH = 'RUN', 'ALL_CASH'
NO_GROUP_MEMBERS = 'NO_GROUP_MEMBERS'
QUOTE_ADR_PER_ORDINARY_SHARE = 'ADR_PER_ORDINARY_SHARE'
END_NEXT_SIGNAL_DAY = 'NEXT_YEAR_SIGNAL_DAY'
END_LAST_PRICE_DATE = 'LAST_PRICE_DATE'
END_SUPPLIED = 'SUPPLIED'
FIRST_BUILD_NOT_FIRST_BUNDLE = 'FIRST_BUILD_NOT_FIRST_BUNDLE_SIGNAL_DAY'


class RunnerError(ValueError):
    """Refused stage input. The message is an UPPER_SNAKE reason code."""


def _day(value, code='DATE_INVALID'):
    if type(value) is date:
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise RunnerError(code)


def _cik(value):
    try:
        return pit._cik(value)
    except ValueError:
        raise RunnerError('CIK_INVALID') from None


def _decimal_or_same(value):
    """Decimal text -> Decimal; anything else unchanged (the scoring quote check decides)."""
    if isinstance(value, str):
        try:
            out = Decimal(value.strip())
        except InvalidOperation:
            return value
        return out if out.is_finite() else value
    return value


# ---- selection stage -----------------------------------------------------------------------------------------------
def _companyfacts_loader(companyfacts):
    """callable(cik) -> companyfacts | None from None, a mapping (any CIK padding) or a loader callable."""
    if companyfacts is None:
        return lambda cik: None
    if callable(companyfacts):
        return companyfacts
    if not isinstance(companyfacts, Mapping):
        raise RunnerError('COMPANYFACTS_MAPPING_REQUIRED')
    normalized = {}
    for key, facts in companyfacts.items():
        cik = _cik(key)
        if cik in normalized:
            raise RunnerError('DUPLICATE_COMPANYFACTS_CIK')
        normalized[cik] = facts
    return normalized.get


def pit_rows(issuers, companyfacts, filing_rows, signal_day, execution_day):
    """pit.build_rows one issuer at a time: each issuer's companyfacts is loaded only for its own row (a whole-market
    bundle never sits in memory at once) and only its own as-filed SIC rows are scanned. Same rows as one build_rows call."""
    load = _companyfacts_loader(companyfacts)
    filings = defaultdict(list)
    for row in filing_rows or ():
        if isinstance(row, Mapping):
            try:
                filings[pit._cik(row.get('cik'))].append(row)
            except ValueError:
                continue     # as_filed_sic skips a row without a valid CIK as well
    rows = {}
    for issuer in issuers:
        cik = _cik(issuer['cik'])
        facts = load(cik)
        built = pit.build_rows({} if facts is None else {cik: facts}, filings.get(cik, ()), [issuer], signal_day,
                               execution_day)
        if set(built) & set(rows):
            raise RunnerError('DUPLICATE_SECURITY_ID')
        rows.update(built)
    return rows


def scoring_quotes(quotes, universe_result):
    """(quotes for scoring.score_population keyed by the U-A representative IDs, {security_id: quote basis}).

    Decimal text is read as Decimal; an ADR representative's per-ADS quote is divided by its adr_ratio (price and month
    closes), or withheld with ADR_RATIO_UNCONFIRMED when the ratio is not confirmed. Other quotes pass unchanged."""
    quotes = quotes or {}
    if not isinstance(quotes, Mapping):
        raise RunnerError('QUOTES_MAPPING_REQUIRED')
    ratios = {c['security_id']: c['adr_ratio'] for issuer in universe_result['issuers'].values()
              for c in issuer['classes'] if c['security_type'] == settings.ADR_SECURITY_TYPE}
    out, basis = {}, {}
    for sid in universe_result[settings.U_A]['member_securities']:
        quote = quotes.get(sid)
        if quote is None:
            continue
        if not isinstance(quote, Mapping):
            raise RunnerError('QUOTE_MUST_BE_DICT')
        quote = dict(quote)
        quote['price'] = _decimal_or_same(quote.get('price'))
        if isinstance(quote.get('month_closes'), Mapping):
            quote['month_closes'] = {m: _decimal_or_same(v) for m, v in quote['month_closes'].items()}
        if universe_result['securities'][sid]['security_type'] == settings.ADR_SECURITY_TYPE \
                and quote.get('withheld_reason') is None:
            ratio = ratios.get(sid)
            if ratio is None:
                quote['withheld_reason'] = universe.ADR_RATIO_UNCONFIRMED
                basis[sid] = universe.ADR_RATIO_UNCONFIRMED
            else:
                with localcontext() as ctx:
                    ctx.prec = universe.DECIMAL_PRECISION
                    if isinstance(quote['price'], (int, Decimal)) and not isinstance(quote['price'], bool):
                        quote['price'] = Decimal(quote['price']) / ratio
                    if isinstance(quote.get('month_closes'), Mapping):
                        quote['month_closes'] = {
                            m: (Decimal(v) / ratio if isinstance(v, (int, Decimal)) and not isinstance(v, bool) else v)
                            for m, v in quote['month_closes'].items()}
                basis[sid] = QUOTE_ADR_PER_ORDINARY_SHARE
        out[sid] = quote
    return out, basis


def _strategy_counts(selections):
    out = {}
    for strategy in settings.STRATEGY_IDS:
        out[strategy] = {}
        for group in settings.GROUPS:
            sel = selections[strategy][group]
            out[strategy][group] = {'status': sel['status'], 'reason': sel['reason'], 'members': sel['members'],
                                    'N': sel['N'], 'k': sel['k'],
                                    'not_eligible_by_reason': dict(sorted(Counter(sel['not_eligible'].values()).items()))}
    return out


def selection_stage(records, *, year, companyfacts=None, filing_rows=(), quotes=None, previous_u_a=None, run=None,
                    type_config=None, parameters=None, playbook_config=None):
    """selection_inputs/1 for the frozen signal year `year` (see the module doc).

    records: universe security records at that S; companyfacts: {cik: SEC companyfacts} or a loader callable(cik);
    filing_rows: as-filed SIC rows {cik, accn, filed, sic}; quotes: {security_id: {price, currency, month_closes,
    withheld_reason?}} at S; previous_u_a: the U-A member CIKs at the previous S (None = first build); run: the
    handoff.run_metadata block (or None)."""
    if type(year) is not int:
        raise RunnerError('YEAR_MUST_BE_INT')
    if not schedule.verify_frozen()['ok']:
        raise RunnerError('FROZEN_SCHEDULE_INVALID')
    try:
        frozen = schedule.frozen_row(year=year)
    except ValueError:
        raise RunnerError('YEAR_NOT_IN_FROZEN_SCHEDULE') from None
    context = pit.signal_context(frozen['S'], frozen['T'])
    previous = None if previous_u_a is None else sorted({_cik(c) for c in previous_u_a})
    uni = universe.build_universes(records, previous_u_a=previous, signal_day=frozen['S'])
    ua = uni[settings.U_A]
    issuers = [{'cik': cik, 'security_id': ua['representatives'][cik]} for cik in ua['members']]
    rows = pit_rows(issuers, companyfacts, filing_rows, frozen['S'], frozen['T'])
    engine_quotes, quote_basis = scoring_quotes(quotes, uni)
    scores = scoring.score_population(rows, engine_quotes, population=ua['member_securities'], type_config=type_config,
                                      parameters=parameters, playbook_config=playbook_config)
    groups = {group: uni[group]['member_securities'] for group in settings.GROUPS}
    selections = selection.select_all(scores, groups)
    flags = []
    if previous is None and frozen['S'] != settings.FIRST_BUNDLE['S']:
        flags.append(FIRST_BUILD_NOT_FIRST_BUNDLE)
    transitions = ua['transitions']
    row_states = Counter(row['state'] for row in rows.values())
    quote_status = Counter(sec['quote_status'] for sec in scores['securities'].values())
    out = {
        'schema': SELECTION_SCHEMA, 'experiment_id': settings.EXPERIMENT_ID,
        'settings_sha256': settings.settings_sha256(), 'stage': 'select', 'run': run or {},
        'year': year, 'signal': dict(frozen, compute_cutoff=context['compute_cutoff'], rule=context['rule']),
        'first_build': previous is None, 'previous_u_a': previous, 'flags': flags,
        'counts': {
            'securities': uni['security_counts'],
            settings.U_A: ua['counts'], settings.U_B: uni[settings.U_B]['counts'],
            'u_a_transitions': {'entered': len(transitions['entered']), 'stayed': len(transitions['stayed']),
                                'left': len(transitions['left']),
                                'left_by_reason': dict(sorted(Counter(item['reasons'][0] for item in transitions['left']
                                                                      if item['reasons']).items()))},
            'pit_rows': {'rows': len(rows), 'by_state': dict(sorted(row_states.items()))},
            'scoring': dict(scores['summary'], quote_status=dict(sorted(quote_status.items()))),
            'strategies': _strategy_counts(selections),
        },
        'universe': {'schema': uni['schema'], 'signal_day': uni['signal_day'], 'first_build': uni['first_build'],
                     'thresholds': uni['thresholds'], 'securities': uni['securities'], 'issuers': uni['issuers'],
                     settings.U_A: {key: ua[key] for key in ('members', 'member_securities', 'representatives',
                                                             'transitions')},
                     settings.U_B: {key: uni[settings.U_B][key] for key in ('members', 'member_securities',
                                                                            'representatives')}},
        'pit': {'context': context, 'rows': rows},
        'quote_basis': quote_basis,
        'scores': {key: scores[key] for key in ('schema', 'scoring_population', 'calc_version', 'summary',
                                                'securities')},
        'selections': {strategy: selections[strategy] for strategy in settings.STRATEGY_IDS},
        'strategy_aliases': dict(settings.STRATEGY_ALIASES), 'preset_aliases': dict(settings.PRESET_ALIASES),
    }
    return handoff.jsonable(out)


def u_a_members(selection_inputs):
    """The U-A member CIKs of a selection_inputs/1 result (the next year's previous_u_a)."""
    _check_selection(selection_inputs)
    return list(selection_inputs['universe'][settings.U_A]['members'])


# ---- ledger stage --------------------------------------------------------------------------------------------------
def _check_selection(item):
    if not isinstance(item, Mapping) or item.get('schema') != SELECTION_SCHEMA:
        raise RunnerError('SELECTION_SCHEMA_INVALID')
    if item.get('experiment_id') != settings.EXPERIMENT_ID:
        raise RunnerError('SELECTION_EXPERIMENT_MISMATCH')
    if item.get('settings_sha256') != settings.settings_sha256():
        raise RunnerError('SETTINGS_SHA256_MISMATCH')


def _ordered_selections(selections):
    items = list(selections)
    if not items:
        raise RunnerError('SELECTION_REQUIRED')
    for item in items:
        _check_selection(item)
        if type(item.get('year')) is not int:
            raise RunnerError('SELECTION_YEAR_INVALID')
        try:
            frozen = schedule.frozen_row(year=item['year'])
        except ValueError:
            raise RunnerError('SELECTION_YEAR_INVALID') from None
        if (item['signal'].get('S'), item['signal'].get('T')) != (frozen['S'], frozen['T']):
            raise RunnerError('SELECTION_SIGNAL_DAY_MISMATCH')
    items.sort(key=lambda x: x['year'])
    years = [x['year'] for x in items]
    if len(set(years)) != len(years):
        raise RunnerError('SELECTION_YEAR_DUPLICATE')
    if any(b - a != 1 for a, b in zip(years, years[1:])):
        raise RunnerError('SELECTION_YEARS_NOT_CONSECUTIVE')
    for a, b in zip(items, items[1:]):
        if b['previous_u_a'] != a['universe'][settings.U_A]['members']:
            raise RunnerError('HYSTERESIS_CHAIN_BROKEN')
    return items


def price_rows(rows):
    """Ledger price rows with `date` as a date (ISO text accepted); every other field is passed to the ledger as is."""
    out = []
    for row in rows or ():
        if not isinstance(row, Mapping):
            raise RunnerError('PRICE_ROW_MUST_BE_DICT')
        out.append(dict(row, date=_day(row.get('date'), 'PRICE_DATE_INVALID')))
    return out


_EVENT_FIELDS = {
    'SPLIT': (ledger.Split, ('event_id', 'effective_date', 'security_id', 'ratio'), ()),
    'DIVIDEND': (ledger.Dividend, ('event_id', 'effective_date', 'security_id', 'cash_per_share'), ('pay_date',)),
    'SETTLEMENT': (ledger.Settlement, ('event_id', 'effective_date', 'security_id', 'kind', 'available_at', 'evidence'),
                   ('settlement_date', 'cash_per_share', 'new_security_id', 'stock_ratio')),
    'SETTLEMENT_CONFIRMATION': (ledger.SettlementConfirmation,
                                ('event_id', 'available_at', 'evidence', 'settlement_date', 'cash_per_share'),
                                ('new_security_id', 'stock_ratio')),
}
_EVENT_DATES = ('effective_date', 'available_at', 'settlement_date', 'pay_date')
_EVENT_DECIMALS = ('ratio', 'cash_per_share', 'stock_ratio')


def ledger_events(rows):
    """Ledger event objects from rows {'type': SPLIT | DIVIDEND | SETTLEMENT | SETTLEMENT_CONFIRMATION, ...fields}.
    Ledger objects pass through. Dates as ISO text; amounts as decimal text or numbers (read exactly)."""
    out = []
    for row in rows or ():
        if isinstance(row, tuple(spec[0] for spec in _EVENT_FIELDS.values())):
            out.append(row)
            continue
        if not isinstance(row, Mapping) or row.get('type') not in _EVENT_FIELDS:
            raise RunnerError('EVENT_TYPE_INVALID')
        cls, required, optional = _EVENT_FIELDS[row['type']]
        keys = set(row) - {'type'}
        if not set(required) <= keys or keys - set(required) - set(optional):
            raise RunnerError('EVENT_FIELDS_INVALID')
        values = {}
        for key in keys:
            value = row[key]
            if key in _EVENT_DATES and value is not None:
                value = _day(value, 'EVENT_DATE_INVALID')
            elif key in _EVENT_DECIMALS and value is not None:
                if isinstance(value, bool) or not isinstance(value, (int, str, Decimal)):
                    raise RunnerError('EVENT_AMOUNT_INVALID')
                try:
                    value = Decimal(str(value))
                except InvalidOperation:
                    raise RunnerError('EVENT_AMOUNT_INVALID') from None
            values[key] = value
        out.append(cls(**values))
    return out


def calendar_sessions(start, end):
    """Canonical NYSE rule-calendar sessions from start to end inclusive."""
    start, end = _day(start), _day(end)
    if end < start:
        raise RunnerError('END_BEFORE_START')
    out, day = [], schedule.session_on_or_after(start)
    while day <= end:
        out.append(day)
        day = schedule.next_session(day)
    return out


def default_end(last_year, prices):
    """(end, rule): the next year's S when that year is frozen, else the last price-row date."""
    try:
        return _day(schedule.frozen_row(year=last_year + 1)['S']), END_NEXT_SIGNAL_DAY
    except ValueError:
        pass
    dates = [row['date'] for row in prices]
    if not dates:
        raise RunnerError('END_NOT_DETERMINABLE')
    return max(dates), END_LAST_PRICE_DATE


def _strategy_years(items, strategy, group, side):
    years = []
    for item in items:
        sel = item['selections'][strategy][group]
        base = {'year': item['year'], 'S': item['signal']['S'], 'T': item['signal']['T'], 'status': sel['status'],
                'reason': sel['reason'], 'N': sel['N'], 'k': sel['k']}
        if sel['status'] == selection.RUN:
            names = [entry['security_id'] for entry in sel[side.lower()]]
            years.append(dict(base, holding=HOLD_SELECTED if names else HOLD_CASH, selected=names))
        else:
            years.append(dict(base, holding=HOLD_CASH, selected=[]))
    return years


def _group_years(items, group):
    years = []
    for item in items:
        names = list(item['universe'][group]['member_securities'])
        years.append({'year': item['year'], 'S': item['signal']['S'], 'T': item['signal']['T'],
                      'status': selection.RUN if names else selection.NOT_RUN,
                      'reason': None if names else NO_GROUP_MEMBERS, 'N': len(names), 'k': None,
                      'holding': HOLD_SELECTED if names else HOLD_CASH, 'selected': names})
    return years


def _needed_securities(selected, events):
    """Selected IDs plus every security a stock merger or spin-off of a needed security can deliver (closure)."""
    needed = set(selected)
    deliveries = defaultdict(set)
    by_event = {}
    for event in events:
        if isinstance(event, ledger.Settlement):
            by_event[event.event_id] = event.security_id
            if event.new_security_id:
                deliveries[event.security_id].add(event.new_security_id)
    for event in events:
        if isinstance(event, ledger.SettlementConfirmation) and event.new_security_id and event.event_id in by_event:
            deliveries[by_event[event.event_id]].add(event.new_security_id)
    frontier = list(needed)
    while frontier:
        sid = frontier.pop()
        for new in deliveries.get(sid, ()):
            if new not in needed:
                needed.add(new)
                frontier.append(new)
    return needed


def _run_portfolio(rebalances, prices_by_sid, events, *, sessions, end, initial_capital, daily_positions, group=None):
    needed = _needed_securities({sid for r in rebalances for sid in r.selected}, events)
    rows = [row for sid in sorted(needed) for row in prices_by_sid.get(sid, ())]
    runs = {scenario: {} for scenario in ledger.SCENARIOS}
    for cost in (Decimal(0), settings.COST_BPS_PER_SIDE):
        if group is None:
            result = ledger.run_scenarios(sessions, rebalances, rows, events, cost_bps=cost,
                                          initial_capital=initial_capital, end=end, daily_positions=daily_positions)
        else:
            result = benchmarks.group_equal_weight_benchmark(
                sessions, rebalances, {r.signal_date: r.selected for r in rebalances}, rows, events, group=group,
                cost_bps=cost, initial_capital=initial_capital, end=end, daily_positions=daily_positions)['runs']
        for scenario in ledger.SCENARIOS:
            runs[scenario][str(cost)] = result[scenario]
    measured = {scenario: metrics.cost_comparison(runs[scenario]['0'], runs[scenario][str(settings.COST_BPS_PER_SIDE)],
                                                  sessions=sessions, coverage_end=end)
                for scenario in ledger.SCENARIOS}
    return runs, measured


def _external_tr(tr_series, *, entry_date, end, sessions, initial_capital):
    if not isinstance(tr_series, Mapping) or not isinstance(tr_series.get('rows'), list):
        raise RunnerError('TR_SERIES_INVALID')
    allowed = {'label', 'claim', 'source', 'is_etf', 'entry_basis', 'rows'}
    if set(tr_series) - allowed or 'label' not in tr_series:
        raise RunnerError('TR_SERIES_INVALID')
    rows = []
    for row in tr_series['rows']:
        if not isinstance(row, Mapping):
            raise RunnerError('TR_SERIES_INVALID')
        rows.append(dict(row, date=_day(row.get('date'), 'TR_DATE_INVALID')))
    try:
        result = benchmarks.external_tr_benchmark(
            rows, label=tr_series['label'], claim=tr_series.get('claim', benchmarks.CLAIM_SP500_TR),
            entry_date=entry_date, end=end, sessions=sessions,
            entry_basis=tr_series.get('entry_basis', benchmarks.ENTRY_OPEN), is_etf=tr_series.get('is_etf'),
            source=tr_series.get('source'), initial_capital=initial_capital)
    except benchmarks.BenchmarkError as exc:
        return {'status': 'REFUSED', 'reason': str(exc), 'label': tr_series['label'], 'result': None, 'metrics': None}
    measured = None
    if result['daily']:
        points, started, capital = benchmarks.tr_nav_points(result)
        measured = metrics.series_metrics(points, started_at=started, initial_capital=capital, sessions=sessions,
                                          coverage_end=end)
    return {'status': result['status'], 'reason': None, 'label': tr_series['label'], 'result': result,
            'metrics': measured}


def ledger_stage(selections, *, prices, events=(), end=None, tr_series=None, initial_capital=settings.NAV_BASE_USD,
                 daily_positions=False, run=None):
    """ledger_outputs/1 from consecutive yearly selection_inputs/1 results (see the module doc).

    prices: ledger price rows {date, security_id, open, close, suspended?, price_basis 'RAW', currency?}; events: ledger
    event objects or rows (ledger_events); end: last session (date or ISO text) or None for the default rule; tr_series:
    {label, claim?, source?, is_etf?, entry_basis?, rows [{date, total_return_index, open_total_return_index?,
    currency}]} or None; daily_positions: keep per-position detail in every daily row."""
    items = _ordered_selections(selections)
    prices = price_rows(prices)
    ledger.index_price_rows(prices)          # every row is validated once, also rows no portfolio needs
    events = ledger_events(events)
    if end is None:
        end, end_rule = default_end(items[-1]['year'], prices)
    else:
        end, end_rule = _day(end, 'END_INVALID'), END_SUPPLIED
    start = _day(items[0]['signal']['S'])
    if end < start:
        raise RunnerError('END_BEFORE_START')
    # The ledger needs every S and T as a session even when `end` cuts the run short; it stops at `end` itself.
    sessions = calendar_sessions(start, max(end, _day(items[-1]['signal']['T'])))
    prices_by_sid = defaultdict(list)
    for row in prices:
        prices_by_sid[row.get('security_id')].append(row)
    capital = Decimal(str(initial_capital))
    specs = []
    for strategy in settings.STRATEGY_IDS:
        for group in settings.GROUPS:
            for side in SIDES:
                specs.append((f'{strategy}/{group}/{side}', KIND_STRATEGY, strategy, group, side,
                              _strategy_years(items, strategy, group, side)))
    for group in settings.GROUPS:
        specs.append((f'{KIND_GROUP_EW}/{group}', KIND_GROUP_EW, None, group, None, _group_years(items, group)))
    portfolios, run_status = {}, Counter()
    for pid, kind, strategy, group, side, years in specs:
        entry = {'portfolio_id': pid, 'kind': kind, 'strategy': strategy, 'group': group, 'side': side, 'years': years,
                 'cash_years': [y['year'] for y in years if y['holding'] == HOLD_CASH], 'runs': None, 'metrics': None}
        if all(y['holding'] == HOLD_CASH for y in years):
            entry['status'] = PORTFOLIO_ALL_CASH
        else:
            rebalances = [ledger.Rebalance(_day(y['S']), _day(y['T']), tuple(y['selected'])) for y in years]
            runs, measured = _run_portfolio(rebalances, prices_by_sid, events, sessions=sessions, end=end,
                                            initial_capital=capital, daily_positions=daily_positions,
                                            group=group if kind == KIND_GROUP_EW else None)
            entry.update(status=PORTFOLIO_RUN, runs=runs, metrics=measured)
            run_status.update(result['status'] for by_cost in runs.values() for result in by_cost.values())
        portfolios[pid] = entry
    external = None
    if tr_series is not None:
        external = _external_tr(tr_series, entry_date=_day(items[0]['signal']['T']), end=end, sessions=sessions,
                                initial_capital=capital)
    status_counts = Counter(p['status'] for p in portfolios.values())
    out = {
        'schema': LEDGER_SCHEMA, 'experiment_id': settings.EXPERIMENT_ID, 'settings_sha256': settings.settings_sha256(),
        'stage': 'ledger', 'run': run or {},
        'selection_years': [x['year'] for x in items],
        'selection_run_ids': [(x.get('run') or {}).get('run_id') for x in items],
        'schedule': [{'year': x['year'], 'S': x['signal']['S'], 'T': x['signal']['T']} for x in items],
        'start': start, 'end': end, 'end_rule': end_rule, 'session_count': sum(1 for d in sessions if d <= end),
        'scenarios': list(ledger.SCENARIOS), 'cost_bps_levels': ['0', str(settings.COST_BPS_PER_SIDE)],
        'initial_capital': capital, 'currency': settings.CURRENCY, 'daily_positions': bool(daily_positions),
        'strategy_aliases': dict(settings.STRATEGY_ALIASES),
        'portfolios': portfolios,
        'benchmarks': {'group_equal_weight': [f'{KIND_GROUP_EW}/{g}' for g in settings.GROUPS],
                       'external_total_return': external},
        'counts': {'portfolios': len(portfolios), 'portfolios_run': status_counts[PORTFOLIO_RUN],
                   'portfolios_all_cash': status_counts[PORTFOLIO_ALL_CASH],
                   'cash_years': sum(len(p['cash_years']) for p in portfolios.values()),
                   'ledger_runs': sum(run_status.values()), 'ledger_runs_by_status': dict(sorted(run_status.items())),
                   'price_rows': len(prices), 'events': len(events),
                   'external_total_return': None if external is None else external['status']},
    }
    return handoff.jsonable(out)


def portfolio_alias(ledger_outputs, portfolio_id):
    """Resolve 'QGV_DEFAULT/U_A/TOP' to the QGV_BALANCED portfolio of a ledger_outputs/1 result."""
    strategy, _, rest = portfolio_id.partition('/')
    strategy = settings.resolve_strategy(strategy)
    return ledger_outputs['portfolios'][f'{strategy}/{rest}']


__all__ = ['SELECTION_SCHEMA', 'LEDGER_SCHEMA', 'RunnerError', 'selection_stage', 'ledger_stage', 'u_a_members',
           'scoring_quotes', 'price_rows', 'ledger_events', 'calendar_sessions', 'default_end', 'portfolio_alias']
