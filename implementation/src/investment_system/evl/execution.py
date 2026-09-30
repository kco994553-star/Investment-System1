"""TC-D3P-003 v1 research execution evaluator; no broker/impact model.

Frozen explicit orders are upstream inputs. Target weights are never converted
to invented quantities. Quote/cost evidence is used only after decisions freeze.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from hashlib import sha256
import fcntl
import json
import math

from ..contracts.lineage import StampedValue, require_aware
from ..contracts.models import _to_json
from .contracts import TrialRecord, TrialStatus
from .metrics import ReturnPeriod, evaluate_metrics
from .splits import split_samples
from .walkforward import digest, _verify_split, _write_json, _recover_pending

POLICY = 'TC-D3P-003_v1'


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('nonfinite execution input')


def evidence(point, evaluation_time, synthetic, measured_at):
    if not isinstance(point, StampedValue):
        raise ValueError('missing execution provenance')
    point.validate(evaluation_time, synthetic=synthetic)
    if point.measured_at != measured_at or point.stamp.available_at < measured_at:
        raise ValueError('execution timestamp/publication mismatch')
    return point.value


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    security_id: str
    time: datetime
    eligible: bool
    eligibility_ref: str


@dataclass(frozen=True)
class Order:
    order_id: str
    security_id: str
    quantity: float
    decision_time: datetime
    source_ref: str


@dataclass(frozen=True)
class ExecutionRow:
    sample: object
    orders: tuple[Order, ...]
    period: ReturnPeriod


@dataclass(frozen=True)
class ExecutionInput:
    rows: tuple[ExecutionRow, ...]
    opportunities: tuple[Opportunity, ...]
    # Key (order_id, opportunity_id). Per-fill monetary costs, separately
    # identified from fill prices, include all execution costs exactly once.
    prices: dict
    costs: dict
    initial_cash: float
    initial_positions: dict
    opening_marks: dict
    closing_marks: tuple[dict, ...]
    currency: str
    price_convention: str
    cost_model_ref: str
    costs_exclude_price_embedded_components: bool
    synthetic: bool


def input_payload(data):
    # Tuple mapping keys cannot be JSON keys; preserve identities explicitly.
    return _to_json({'rows': [asdict(r) for r in data.rows],
        'opportunities': [asdict(o) for o in data.opportunities],
        'prices': [[*k, asdict(v)] for k,v in sorted(data.prices.items())],
        'costs': [[*k, asdict(v)] for k,v in sorted(data.costs.items())],
        'initial_cash': data.initial_cash, 'initial_positions': data.initial_positions,
        'opening_marks': {k:asdict(v) for k,v in data.opening_marks.items()},
        'closing_marks': [{k:asdict(v) for k,v in m.items()} for m in data.closing_marks],
        'currency': data.currency, 'price_convention': data.price_convention,
        'cost_model_ref': data.cost_model_ref,
        'costs_exclude_price_embedded_components': data.costs_exclude_price_embedded_components,
        'synthetic': data.synthetic})


def input_hash(data):
    return digest(input_payload(data))


def validate_input(split, data, partition):
    if partition not in ('train','validation','oos'):
        raise ValueError('Holdout cannot enter C6')
    parts = split_samples(split, tuple(r.sample for r in data.rows), stress=False)
    if not data.rows or set(parts.retained[partition]) != {r.sample.sample_id for r in data.rows}:
        raise ValueError('C6 input must contain only retained registered partition rows')
    if len(data.closing_marks) != len(data.rows):
        raise ValueError('mark coverage mismatch')
    if not all((data.currency, data.price_convention, data.cost_model_ref)):
        raise ValueError('missing currency/price/cost contract')
    if data.costs_exclude_price_embedded_components is not True:
        raise ValueError('undefined/double-counted execution costs')
    finite(data.initial_cash)
    if data.initial_cash < 0:
        raise ValueError('negative starting cash')
    for q in data.initial_positions.values():
        finite(q)
        if q < 0:
            raise ValueError('short/capacity semantics undefined')
    ids, times = set(), {}
    for o in data.opportunities:
        require_aware(o.time)
        if not all((o.opportunity_id,o.security_id,o.eligibility_ref)) or type(o.eligible) is not bool:
            raise ValueError('missing schedule/eligibility provenance')
        if o.opportunity_id in ids:
            raise ValueError('duplicate opportunity')
        ids.add(o.opportunity_id)
        times.setdefault(o.security_id,[]).append(o.time)
    if any(ts != sorted(set(ts)) for ts in times.values()):
        raise ValueError('opportunities must be unique chronological per security')
    orders = set()
    for i,row in enumerate(data.rows):
        if (row.period.start != row.sample.decision_time or row.period.end != row.sample.label_end
                or row.period.currency != data.currency):
            raise ValueError('execution period/sample mismatch')
        if i and row.period.start != data.rows[i-1].period.end:
            raise ValueError('execution periods must be contiguous')
        for order in row.orders:
            require_aware(order.decision_time)
            finite(order.quantity)
            if (not all((order.order_id,order.security_id,order.source_ref))
                    or order.order_id in orders or order.quantity == 0
                    or order.decision_time != row.sample.decision_time):
                raise ValueError('invalid frozen order path')
            orders.add(order.order_id)


def execute_path(data, delay, evaluation_time):
    """Return actual full-fill research path with cash/position reconciliation."""
    if type(delay) is not int or delay not in (0,1):
        raise ValueError('only approved delay 0/1')
    cash, positions = data.initial_cash, dict(data.initial_positions)
    marks = data.opening_marks
    out = []
    for row,closing in zip(data.rows,data.closing_marks):
        p = row.period
        p.validate(evaluation_time)
        start_prices = {k:evidence(marks[k],evaluation_time,data.synthetic,p.start) for k,q in positions.items() if q}
        # Opening valuation may not use future available prices.
        if any(marks[k].stamp.available_at > p.start for k in start_prices):
            raise ValueError('future opening equity')
        if any(v <= 0 for v in start_prices.values()):
            raise ValueError('nonpositive opening price')
        opening = cash + sum(q*start_prices[k] for k,q in positions.items() if q)
        if opening <= 0:
            raise ValueError('insolvent opening equity')
        fills, total_cost, notional = [], 0., 0.
        selected = []
        for order in row.orders:
            slots = [o for o in data.opportunities if o.security_id==order.security_id
                     and o.eligible and o.time > order.decision_time]
            if len(slots) <= delay or slots[delay].time >= p.end:
                raise ValueError('NOT_RUN: missing eligible opportunity within period')
            selected.append((slots[delay].time,order.order_id,order,slots[delay]))
        # Explicit fixed sequence for simultaneous orders, frozen by order IDs.
        # Reject ambiguous simultaneous cash-dependent orders rather than invent priority.
        if len({t for t,_,_,_ in selected}) != len(selected):
            raise ValueError('NOT_RUN: simultaneous fill ordering undefined')
        for _,_,order,slot in sorted(selected):
            key = (order.order_id,slot.opportunity_id)
            price = evidence(data.prices.get(key),evaluation_time,data.synthetic,slot.time)
            cost = evidence(data.costs.get(key),evaluation_time,data.synthetic,slot.time)
            if price <= 0 or cost < 0:
                raise ValueError('invalid fill price/cost')
            new_position = positions.get(order.security_id,0.)+order.quantity
            new_cash = cash-order.quantity*price-cost
            if new_position < 0 or new_cash < 0:
                raise ValueError('NOT_RUN: insufficient cash/positions; capacity/partial fills undefined')
            cash, positions[order.security_id] = new_cash,new_position
            total_cost += cost
            notional += abs(order.quantity*price)
            fills.append({'order_id':order.order_id,'opportunity_id':slot.opportunity_id,
                'time':slot.time.isoformat(),'quantity':order.quantity,'price':price,'cost':cost})
        end_prices = {k:evidence(closing.get(k),evaluation_time,data.synthetic,p.end)
                      for k,q in positions.items() if q}
        if any(v <= 0 for v in end_prices.values()):
            raise ValueError('nonpositive closing mark')
        ending = cash+sum(q*end_prices[k] for k,q in positions.items() if q)
        gross_pnl = ending+total_cost-opening
        out.append({'opening_equity':opening,'ending_equity_1x':ending,
            'cash_1x':cash,'positions':dict(positions),'fills':fills,
            'gross_pnl':gross_pnl,'execution_cost':total_cost,'turnover':notional/opening})
        marks = closing
    return out


def evaluate_execution(data, *, split, partition, delay, multiplier, evaluation_time,
                       periods_per_year, tail_fraction):
    """TC-D3P-003 actual evaluator -> unchanged C3 four-view metrics."""
    validate_input(split,data,partition)
    if type(multiplier) is not int or multiplier not in (1,2,3):
        raise ValueError('only approved cost 1x/2x/3x')
    path = execute_path(data,delay,evaluation_time)
    periods, wealth = [],1.
    for row,frame in zip(data.rows,path):
        gross = frame['gross_pnl']/frame['opening_equity']
        cost = multiplier*frame['execution_cost']/frame['opening_equity']
        if 1+gross-cost <= 0:
            raise ValueError('NOT_RUN: insolvent stressed result')
        wealth *= 1+gross-cost
        if not math.isfinite(wealth) or wealth <= 0:
            raise ValueError('NOT_RUN: insolvent stressed path')
        periods.append(replace(row.period,gross_return=gross,trading_cost=cost,turnover=frame['turnover']))
    return {'path':path,'path_hash':digest(path),'delay':delay,'cost_multiplier':multiplier,
        'metrics_report':evaluate_metrics(tuple(periods),evaluation_time=evaluation_time,
            periods_per_year=periods_per_year,tail_fraction=tail_fraction),
        'policy':POLICY,'synthetic':data.synthetic,'official':False,
        'claim':'SOFTWARE_FIXTURE' if data.synthetic else 'RESEARCH_EXECUTION_BASELINE'}


def register_execution(ledger, split, data, plan):
    spec = ledger.registration()
    _verify_split(ledger,split,spec)
    plan = deepcopy(plan)
    validate_input(split,data,plan['partition'])
    registered = datetime.fromisoformat(plan['registered_at'])
    evaluated = datetime.fromisoformat(plan['evaluation_time'])
    require_aware(registered); require_aware(evaluated)
    if (registered < max(split.registered_at,datetime.fromisoformat(spec['registered_at']))
            or evaluated < registered or not plan['evaluator_id']):
        raise ValueError('invalid execution registration')
    finite(plan['periods_per_year']); finite(plan['tail_fraction'])
    if plan['periods_per_year'] <= 0 or not 0 < plan['tail_fraction'] <= 1:
        raise ValueError('invalid metrics convention')
    if spec['data_hash'] != input_hash(data):
        raise ValueError('execution input hash mismatch')
    if set(plan['parameters']) != set(spec['parameter_space']['values']) or any(
            v not in spec['parameter_space']['values'][k] for k,v in plan['parameters'].items()):
        raise ValueError('parameters outside registered domain')
    if spec['metric_set']['metric_ids'] != ['net_total_return']:
        raise ValueError('execution ledger requires net_total_return')
    body = {'plan':plan,'policy':POLICY,'experiment_hash':digest(spec),
            'split_hash':digest(split.payload()),'input_hash':input_hash(data),
            'input_evidence':input_payload(data),
            'scenarios':[[d,m] for d in (0,1) for m in (1,2,3)]}
    with (ledger.directory/'experiment.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if ledger.trials.records():
            raise ValueError('cannot register execution after results')
        _write_json(ledger.directory/'execution.json',{'sha256':digest(body),'body':body})
    return digest(body)


def run_execution(ledger, split, data, *, evaluator_id, recorded_at):
    require_aware(recorded_at)
    spec = ledger.registration()
    _verify_split(ledger,split,spec)
    stored = json.loads((ledger.directory/'execution.json').read_text())
    body, plan = stored['body'],stored['body']['plan']
    if (stored['sha256'] != digest(body) or body['experiment_hash'] != digest(spec)
            or body['split_hash'] != digest(split.payload()) or body['input_hash'] != input_hash(data)
            or digest(body['input_evidence']) != body['input_hash']
            or evaluator_id != plan['evaluator_id']
            or recorded_at < max(datetime.fromisoformat(plan['registered_at']),
                                 datetime.fromisoformat(plan['evaluation_time']))):
        raise ValueError('execution registration/input/evaluator/time mismatch')
    validate_input(split,data,plan['partition'])
    with (ledger.directory/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        _recover_pending(ledger,recorded_at)
        if ledger.trials.records():
            raise ValueError('execution registration already consumed')
        results = []
        for delay,multiplier in body['scenarios']:
            if len(ledger.trials.records()) >= spec['search_budget']['max_trials']:
                return {'status':'NOT_RUN_BUDGET','results':results,'official':False}
            trial_id = f'execution-{delay}-{multiplier}'
            _write_json(ledger.directory/'pending.json',{'trial_id':trial_id,'parameters':plan['parameters']})
            status,reason,metrics = TrialStatus.SUCCESS,None,{}
            report = {'delay':delay,'cost_multiplier':multiplier,'input_hash':body['input_hash'],
                'code_hash':spec['code_hash'],'policy':POLICY,'parameters':plan['parameters'],
                'partition':plan['partition'],'official':False,'tax_mode':'EXCLUDED'}
            try:
                report.update(evaluate_execution(data,split=split,partition=plan['partition'],delay=delay,multiplier=multiplier,
                    evaluation_time=datetime.fromisoformat(plan['evaluation_time']),
                    periods_per_year=plan['periods_per_year'],tail_fraction=plan['tail_fraction']))
                metrics = {'net_total_return':report['metrics_report']['views']['NET_OF_TRADING_COST_PRE_TAX']['total_return']}
            except (ValueError,KeyError,TypeError) as exc:
                status,reason = TrialStatus.REJECTED,str(exc)
            except Exception as exc:
                status,reason = TrialStatus.FAILED,type(exc).__name__+': '+str(exc)
            report.update(status=status.value,reason=reason)
            name = 'execution-report-'+sha256(trial_id.encode()).hexdigest()+'.json'
            _write_json(ledger.directory/name,report)
            ledger.append(TrialRecord(trial_id,spec['experiment_id'],len(ledger.trials.records()),
                recorded_at,status,deepcopy(plan['parameters']),metrics,
                (reason+'; ' if reason else '')+'report_sha256='+digest(report)))
            (ledger.directory/'pending.json').unlink()
            results.append({'trial_id':trial_id,'status':status.value,'report_file':name,'report_hash':digest(report)})
        return {'status':'COMPLETED' if all(r['status']=='SUCCESS' for r in results) else 'NOT_ACCEPTED',
                'results':results,'official':False,'robustness_pass':False,
                'remaining':'C6 statistics/perturbation/controls acceptance required'}


def execution_report(ledger, trial_id):
    """Resolve complete hash-bound evidence with current invalidation state."""
    trial = ledger.supporting_trial(trial_id)
    name = 'execution-report-'+sha256(trial_id.encode()).hexdigest()+'.json'
    report = json.loads((ledger.directory/name).read_text())
    registered = json.loads((ledger.directory/'execution.json').read_text())
    body = registered['body']
    if (registered['sha256'] != digest(body)
            or body['experiment_hash'] != digest(ledger.registration())
            or digest(body['input_evidence']) != body['input_hash']
            or report['input_hash'] != body['input_hash']
            or report['code_hash'] != ledger.registration()['code_hash']
            or report['policy'] != POLICY or report['status'] != 'SUCCESS'
            or report['parameters'] != trial['parameters']
            or trial['reason'] != 'report_sha256='+digest(report)):
        raise ValueError('execution evidence hash/lineage mismatch')
    return deepcopy(report)
