"""Exact C7 selection kernels: approved 006B + G1/D2; no research defaults."""
from fractions import Fraction
from itertools import combinations
import math

def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Fraction)):
        raise ValueError('finite exact numeric value required')
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('nonfinite value')
    try:
        return Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError('invalid exact numeric value') from exc

def frontier(vectors, directions):
    """Independent exact objectives; no averaging, epsilon or hash merit."""
    if not directions or any(d not in ('min', 'max') for d in directions):
        raise ValueError('explicit objective directions required')
    v = {k: tuple(number(x) for x in row) for k, row in vectors.items()}
    if any(len(row) != len(directions) for row in v.values()):
        raise ValueError('objective coverage mismatch')
    oriented = {k: tuple(x if d == 'min' else -x for x,d in zip(row,directions))
                for k,row in v.items()}
    return sorted(k for k,a in oriented.items() if not any(
        j != k and all(x <= y for x,y in zip(b,a)) and any(x < y for x,y in zip(b,a))
        for j,b in oriented.items()))

def adjacency(left, right, domains):
    differing = [k for k in domains if left[k] != right[k]]
    return len(differing) == 1 and abs(
        domains[differing[0]].index(left[differing[0]]) -
        domains[differing[0]].index(right[differing[0]])) == 1

def plateau(parameters, domains, values, tolerances, pareto):
    """G1 universe is complete eligible Landscape, including dominated bridges."""
    ids = sorted(parameters)
    tol = tuple(number(t) for t in tolerances)
    if any(t < 0 for t in tol) or not tol:
        raise ValueError('explicit nonnegative plateau tolerances required')
    rows = {k:tuple(number(v) for v in values[k]) for k in ids}
    if any(len(row) != len(tol) for row in rows.values()):
        raise ValueError('plateau dimensions mismatch')
    for p in parameters.values():
        if set(p) != set(domains) or any(p[k] not in domains[k] for k in domains):
            raise ValueError('parameter outside full registered domains')
    edges, graph, evidence = [], {k:set() for k in ids}, []
    for a,b in combinations(ids,2):
        if adjacency(parameters[a],parameters[b],domains) and all(
                abs(x-y) <= t for x,y,t in zip(rows[a],rows[b],tol)):
            edges.append([a,b]); graph[a].add(b); graph[b].add(a)
            coordinate=next(k for k in domains if parameters[a][k]!=parameters[b][k])
            evidence.append({'members':[a,b],'coordinate':coordinate,
                'registered_positions':[domains[coordinate].index(parameters[a][coordinate]),
                                        domains[coordinate].index(parameters[b][coordinate])],
                'metric_absolute_differences':[str(abs(x-y)) for x,y in zip(rows[a],rows[b])],
                'registered_tolerances':[str(t) for t in tol]})
    components, remaining = [], set(ids)
    while remaining:
        stack=[min(remaining)]; members=set()
        while stack:
            p=stack.pop()
            if p in members: continue
            members.add(p); stack.extend(graph[p]-members)
        remaining -= members
        ranges=[(min(rows[k][i] for k in members),max(rows[k][i] for k in members))
                for i in range(len(tol))]
        components.append({'members':sorted(members),'member_count':len(members),
            'pareto_members':sorted(members & set(pareto)),
            'non_pareto_members':sorted(members-set(pareto)),
            'edges':[e for e in edges if e[0] in members and e[1] in members],
            'registered_adjacency':'ONE_IMMEDIATE_REGISTERED_GRID_COORDINATE',
            'adjacency_evidence':[e for e in evidence if e['members'][0] in members and e['members'][1] in members],
            'metric_ranges':[[str(a),str(b)] for a,b in ranges],
            'metric_diameters':[str(b-a) for a,b in ranges],
            'stable':len(members)>=2})
    return {'vertex_universe':ids,'edges':edges,'components':components,
        'survivors':sorted(k for c in components if c['stable'] for k in c['pareto_members'])}

def complexity(parameters, baseline):
    if any(set(p) != set(baseline) for p in parameters.values()):
        raise ValueError('C5 baseline coordinates mismatch')
    counts={k:sum(p[c] != baseline[c] for c in baseline) for k,p in parameters.items()}
    minimum=min(counts.values()) if counts else None
    return {'counts':counts,'survivors':sorted(k for k,v in counts.items() if v==minimum)}

def low_drift(vectors):
    """D2 exact absolute magnitudes, independent coordinate/cohort/time."""
    magnitudes={k:[abs(number(x)) for x in row] for k,row in vectors.items()}
    width={len(v) for v in magnitudes.values()}
    if len(width)>1 or (width and 0 in width):
        raise ValueError('complete matching drift dimensions required')
    return {'absolute_normalized_vectors':{k:[str(x) for x in v] for k,v in magnitudes.items()},
        'survivors':frontier(magnitudes,('min',)*next(iter(width))) if width else []}

def medoids(survivors, graph, parameters, domains):
    """Restricted representatives; distances to ALL members of each full component."""
    ranges={k:max(map(number,v))-min(map(number,v)) for k,v in domains.items()}
    result=[]
    for c in graph['components']:
        if not c['stable']: continue
        eligible=sorted(set(survivors)&set(c['members']))
        if not eligible: continue
        costs={}
        for a in eligible:
            costs[a]=sum(sum(((number(parameters[a][k])-number(parameters[b][k]))/r)**2
                            if r else Fraction(0) for k,r in ranges.items())
                         for b in c['members'])
        best=min(costs.values())
        result.append({'component_members':c['members'],
            'restricted_candidates':eligible,'costs':{k:str(v) for k,v in costs.items()},
            'representatives':sorted(k for k,v in costs.items() if v==best),
            'tie_semantics':'TIED_EQUIVALENT_REPRESENTATIVES',
            'domain_ranges':{k:str(v) for k,v in ranges.items()}})
    return result
