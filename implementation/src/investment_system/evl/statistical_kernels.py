"""Approved TC-D3P-004 A numerical kernels, not C6 acceptance or promotion.

All sample dimensions/conventions are explicit. No threshold, selected-family
pruning, Holdout access, fitted predictor, or TC-D3P-005 Freeze policy lives here.
Callers must preregister methods and route inference through an experiment ledger.
Bare kernel outputs cannot support a C6 diagnostic PASS or promotion.
"""
from dataclasses import asdict
from itertools import combinations
import math
import random
from statistics import mean, stdev, variance, NormalDist

from .metrics import _finite
from .splits import split_samples
from .walkforward import digest

METHOD_VERSION = 'EVL_STATISTICAL_KERNELS_v1'
NORMAL = NormalDist()
EULER_GAMMA = 0.5772156649015329


class MissingStatisticalEvidence(ValueError):
    """A registered diagnostic runner must record this as NOT_RUN, never PASS."""


def _series(values, minimum=2):
    out = tuple(values)
    if len(out) < minimum:
        raise MissingStatisticalEvidence('insufficient observations')
    for value in out:
        _finite(value)
    return out


def _positive_integer(value, name):
    if type(value) is not int or value <= 0:
        raise ValueError(name+' must be a positive integer')


def aligned_family(registered_roster, series):
    """Require every registered column, preserving caller-independent ID order."""
    roster = tuple(registered_roster)
    if not roster or any(not isinstance(k,str) or not k for k in roster) or len(set(roster)) != len(roster):
        raise ValueError('invalid registered candidate roster')
    if set(series) != set(roster):
        raise MissingStatisticalEvidence('complete registered family required; no selected subset')
    columns = {k:_series(series[k]) for k in sorted(roster)}
    if len({len(v) for v in columns.values()}) != 1:
        raise MissingStatisticalEvidence('missing aligned evidence; no interpolation')
    return columns


def excess_family_from_periods(registered_roster, periods_by_candidate, samples,
                               *, split, partition, stress, evaluation_time):
    """C2/C3-qualified arithmetic net-minus-risk-free, in period units."""
    if partition not in ('train','validation','oos') or type(stress) is not bool:
        raise ValueError('invalid research partition/variant; Holdout forbidden')
    samples, registered_roster = tuple(samples), tuple(registered_roster)
    partitioned = split_samples(split,samples,stress=stress)
    ids = tuple(s.sample_id for s in samples)
    if not samples or set(ids) != set(partitioned.retained[partition]):
        raise ValueError('only retained registered research partition accepted')
    ordered = tuple(sorted(samples,key=lambda s:(s.decision_time,s.sample_id)))
    if tuple(samples) != ordered:
        raise ValueError('samples must be chronological')
    if set(periods_by_candidate) != set(registered_roster):
        raise MissingStatisticalEvidence('complete registered family required')
    output, currency = {},set()
    provenance = {}
    for candidate in sorted(periods_by_candidate):
        periods = tuple(periods_by_candidate[candidate])
        if len(periods) != len(samples):
            raise MissingStatisticalEvidence('aligned period/sample coverage required')
        for i,(period,sample) in enumerate(zip(periods,samples)):
            period.validate(evaluation_time)
            if period.start != sample.decision_time or period.end != sample.label_end:
                raise ValueError('period outside registered sample interval')
            if i and period.start != periods[i-1].end:
                raise ValueError('periods must be contiguous')
            currency.add(period.currency)
        output[candidate] = tuple(p.gross_return-p.trading_cost-p.risk_free_return for p in periods)
        provenance[candidate] = digest([asdict(p) for p in periods])
    if len(currency) != 1:
        raise ValueError('mixed currency requires upstream FX contract')
    return {'series':aligned_family(registered_roster,output),'period_hashes':provenance,
            'sample_ids':ids,'partition':partition,'variant':partitioned.variant,
            'definition':'NET_PRE_TAX_MINUS_RISK_FREE_ARITHMETIC_PERIOD_RETURN',
            'method_version':METHOD_VERSION,'tax_mode':'EXCLUDED','official':False}


def period_sharpe(values):
    values = _series(values)
    sd = stdev(values)
    if sd == 0:
        raise MissingStatisticalEvidence('zero sample variance')
    result = mean(values)/sd
    _finite(result)
    return result


def probabilistic_sharpe(values, *, reference_sharpe):
    """Bailey/Lopez de Prado PSR; reference and Sharpe are unannualized.

    Central standardized moments use denominator n; Sharpe uses sample SD as C3.
    Skew is population central m3/m2**1.5; kurtosis m4/m2**2 is non-excess.
    The published finite-n moment correction uses n-1. No significance cutoff.
    """
    values = _series(values,minimum=3)
    _finite(reference_sharpe)
    center = mean(values)
    centered = tuple(x-center for x in values)
    m2 = mean(x*x for x in centered)
    if m2 <= 0:
        raise MissingStatisticalEvidence('zero variance; PSR undefined')
    skew = mean(x**3 for x in centered)/(m2**1.5)
    kurtosis = mean(x**4 for x in centered)/(m2*m2)
    sr = period_sharpe(values)
    correction = 1-skew*sr+(kurtosis-1)*sr*sr/4
    if not math.isfinite(correction) or correction <= 0:
        raise MissingStatisticalEvidence('nonpositive PSR moment correction')
    z = (sr-reference_sharpe)*math.sqrt(len(values)-1)/math.sqrt(correction)
    _finite(z)
    return {'probability':NORMAL.cdf(z),'z':z,'sharpe_period':sr,
            'reference_sharpe_period':reference_sharpe,'n':len(values),
            'skew':skew,'kurtosis_nonexcess':kurtosis,'moment_correction':correction,
            'method_version':METHOD_VERSION}


def expected_maximum_sharpe(*, trial_count, sharpe_variance):
    """Published Gaussian expected-maximum approximation, zero-null Sharpe."""
    _positive_integer(trial_count,'trial_count')
    _finite(sharpe_variance)
    if sharpe_variance < 0:
        raise ValueError('negative Sharpe variance')
    if trial_count == 1 or sharpe_variance == 0:
        return 0.
    value = math.sqrt(sharpe_variance)*(
        (1-EULER_GAMMA)*NORMAL.inv_cdf(1-1/trial_count)
        +EULER_GAMMA*NORMAL.inv_cdf(1-1/(trial_count*math.e)))
    _finite(value)
    return value


def deflated_sharpe_family(registered_roster, series, *, all_charged_attempts,
                          candidate_count_provenance, attempt_count_provenance,
                          registered_sharpe_variance):
    """Both approved sensitivity views; no inferred independent-trial count."""
    columns = aligned_family(registered_roster,series)
    if len(columns) < 2:
        raise MissingStatisticalEvidence('cross-candidate Sharpe variance needs complete family')
    _positive_integer(all_charged_attempts,'all_charged_attempts')
    if all_charged_attempts < len(columns):
        raise ValueError('attempt count below distinct full-candidate count')
    if not candidate_count_provenance or not attempt_count_provenance:
        raise ValueError('both count provenance references required')
    scores = {k:period_sharpe(v) for k,v in columns.items()}
    actual_variance = variance(scores.values())
    _finite(registered_sharpe_variance)
    if not math.isclose(actual_variance,registered_sharpe_variance,rel_tol=1e-12,abs_tol=1e-15):
        raise ValueError('registered cross-candidate Sharpe variance mismatch')
    views = {}
    for name,count,ref in (
        ('DISTINCT_FULL_CANDIDATES',len(columns),candidate_count_provenance),
        ('ALL_CHARGED_ATTEMPTS',all_charged_attempts,attempt_count_provenance)):
        reference = expected_maximum_sharpe(trial_count=count,sharpe_variance=actual_variance)
        views[name] = {'trial_count':count,'count_provenance':ref,
            'reference_sharpe_period':reference,
            'candidates':{k:probabilistic_sharpe(v,reference_sharpe=reference) for k,v in columns.items()}}
    return {'views':views,'candidate_ids':tuple(columns),'sharpe_variance':actual_variance,
            'variance_provenance':digest(scores),'method_version':METHOD_VERSION,
            'independent_trial_count_estimated':False}


def cscv_pbo(registered_roster, series, *, block_count):
    """All equal chronological block combinations, tied winners, average ranks.

    n must divide S exactly: no truncation, padding, unregistered partial blocks.
    Each partition has equal mass; its tied in-sample maxima split that mass.
    Average OOS ranks ascend from worst=1 to best=N; rank/(N+1), median=0.5.
    This is diagnostic resampling of frozen outcomes, never fitting or retuning.
    """
    columns = aligned_family(registered_roster,series)
    _positive_integer(block_count,'block_count')
    n = len(next(iter(columns.values())))
    if len(columns) < 2 or block_count % 2 or n % block_count or n < block_count*2:
        raise MissingStatisticalEvidence('CSCV needs complete equal blocks and valid half scores')
    size = n//block_count
    rows = []
    partition_total = math.comb(block_count,block_count//2)
    for selected in combinations(range(block_count),block_count//2):
        selected_set = set(selected)
        train = tuple(i for b in selected for i in range(b*size,(b+1)*size))
        test = tuple(i for b in range(block_count) if b not in selected_set for i in range(b*size,(b+1)*size))
        ins = {k:period_sharpe(tuple(v[i] for i in train)) for k,v in columns.items()}
        outs = {k:period_sharpe(tuple(v[i] for i in test)) for k,v in columns.items()}
        winners = tuple(k for k in columns if ins[k]==max(ins.values()))
        choices = []
        for k in winners:
            rank = 1+sum(v<outs[k] for v in outs.values())+(sum(v==outs[k] for v in outs.values())-1)/2
            relative = rank/(len(columns)+1)
            choices.append({'candidate_id':k,'oos_average_rank':rank,'oos_relative_rank':relative,
                'below_median':relative<.5,'at_median':relative==.5,
                'weight':1/partition_total/len(winners),
                'logit':math.log(relative/(1-relative))})
        rows.append({'train_blocks':selected,'test_blocks':tuple(b for b in range(block_count) if b not in selected_set),
            'in_sample_scores':ins,'out_of_sample_scores':outs,'tied_winners':choices})
    choices = [c for row in rows for c in row['tied_winners']]
    return {'pbo':math.fsum(c['weight'] for c in choices if c['below_median']),
            'median_equality_mass':math.fsum(c['weight'] for c in choices if c['at_median']),
            'partition_count':partition_total,'partitions':rows,'candidate_ids':tuple(columns),
            'block_count':block_count,'n':n,'method_version':METHOD_VERSION}


def circular_block_indices(*, n, block_length, replicates, seed):
    for name,value in (('n',n),('block_length',block_length),('replicates',replicates)):
        _positive_integer(value,name)
    if type(seed) is not int:
        raise ValueError('seed must be an explicit integer')
    if block_length > n:
        raise MissingStatisticalEvidence('block length exceeds aligned history')
    rng = random.Random(seed)
    out = []
    for _ in range(replicates):
        indices = []
        while len(indices) < n:
            start = rng.randrange(n)
            indices.extend((start+j)%n for j in range(block_length))
        out.append(tuple(indices[:n]))
    return tuple(out)


def empirical_quantile(values, quantile, *, convention):
    values = _series(values,minimum=1)
    _finite(quantile)
    if not 0 <= quantile <= 1 or convention != 'EMPIRICAL_INVERSE_CDF':
        raise ValueError('explicit supported quantile convention required')
    return sorted(values)[max(0,math.ceil(quantile*len(values))-1)]


def joint_circular_bootstrap(registered_roster, series, benchmarks, *,
                            block_length, replicates, seed, quantiles, quantile_convention):
    columns = aligned_family(registered_roster,series)
    n = len(next(iter(columns.values())))
    if not benchmarks or set(benchmarks)&set(columns):
        raise ValueError('explicit independent benchmark identities required')
    benchmark_columns = {k:_series(v) for k,v in sorted(benchmarks.items())}
    if any(len(v)!=n for v in benchmark_columns.values()):
        raise MissingStatisticalEvidence('benchmark alignment missing')
    quantiles = tuple(quantiles)
    if not quantiles or len(set(quantiles)) != len(quantiles):
        raise ValueError('registered quantiles required')
    for q in quantiles:
        empirical_quantile((0.,),q,convention=quantile_convention)
    indices = circular_block_indices(n=n,block_length=block_length,replicates=replicates,seed=seed)
    together = {**columns,**benchmark_columns}
    means = {k:tuple(mean(v[i] for i in ix) for ix in indices) for k,v in together.items()}
    return {'sample_indices':indices,'indices_hash':digest(indices),'mean_replicates':means,
        'mean_quantiles':{k:tuple(empirical_quantile(v,q,convention=quantile_convention) for q in quantiles) for k,v in means.items()},
        'quantiles':quantiles,'quantile_convention':quantile_convention,
        'block_length':block_length,'replicates':replicates,'seed':seed,
        'candidate_ids':tuple(columns),'benchmark_ids':tuple(benchmark_columns),
        'method_version':METHOD_VERSION}


def family_reality_check(registered_roster, net_returns, benchmark_net_returns, *,
                         block_length, replicates, seed):
    """White max-mean differential family test, jointly centered block draws.

    Monte Carlo tail fraction is count(T_boot >= T_observed)/B. No cutoff or
    significance/skill decision; all registered candidates remain in every draw.
    """
    columns = aligned_family(registered_roster,net_returns)
    benchmark = _series(benchmark_net_returns)
    n = len(benchmark)
    if any(len(v)!=n for v in columns.values()):
        raise MissingStatisticalEvidence('benchmark alignment missing')
    differences = {k:tuple(a-b for a,b in zip(v,benchmark)) for k,v in columns.items()}
    averages = {k:mean(v) for k,v in differences.items()}
    observed = math.sqrt(n)*max(averages.values())
    indices = circular_block_indices(n=n,block_length=block_length,replicates=replicates,seed=seed)
    draws = tuple(math.sqrt(n)*max(mean(differences[k][i]-averages[k] for i in ix)
                                  for k in columns) for ix in indices)
    return {'observed_max_mean_statistic':observed,'centered_bootstrap_statistics':draws,
        'tail_fraction':sum(x>=observed for x in draws)/replicates,
        'candidate_mean_differentials':averages,'candidate_ids':tuple(columns),
        'indices_hash':digest(indices),'block_length':block_length,
        'replicates':replicates,'seed':seed,'method_version':METHOD_VERSION,
        'decision':'NOT_ASSESSED_PENDING_C8'}
