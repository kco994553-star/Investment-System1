"""Replay ECON-PHASE-R1 on retained primary-source observations, without network."""
from pathlib import Path
import hashlib
import json
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parent
RING=['recovery','expansion','slowdown','contraction']
D0='1968-01'
CUT='2000-01'
D1='2024-12'
FIELDS=['LU','LD','LE','PO','HO','IN','C']

def sign(x):
    return np.sign(x.round(9))

def family(series):
    vals=pd.concat(series,axis=1)
    pos=(vals>0).any(axis=1)
    neg=(vals<0).any(axis=1)
    vote=pos.astype(float)-neg.astype(float)
    return vote.where(vals.notna().any(axis=1)),pos & neg

def features():
    raw=pd.read_csv(ROOT/'observations.csv')
    data=raw.pivot(index='period',columns='series',values='value')
    data.index=pd.PeriodIndex(data.index,freq='M')
    d=data.reindex(pd.period_range('1964-01',D1,freq='M'))
    u=d.LNS14000000.rolling(3).mean()
    x=pd.DataFrame(index=d.index)
    x['sahm_gap']=(u-u.shift(1).rolling(12).min()).round(9)
    x['sahm']=(x.sahm_gap>=0.50).astype(float).where(x.sahm_gap.notna())
    x['LU']=-sign(u-u.shift(3))
    x['ip']=sign(d['IP.B50001.S']-d['IP.B50001.S'].shift(12))
    # Forward within the 3 months of the GDP observation's regular release cycle.
    gdp=d.A191RL.copy()
    for month in d.index:
        end_of_previous_quarter=month-(month.month%3)
        gdp.at[month]=d.A191RL.get(end_of_previous_quarter,np.nan)
    x['gdp']=sign(gdp)
    x['PO'],x['po_mixed']=family([x.ip,x.gdp])
    x['temp']=sign(d.CES6056132001.diff(6))
    x['hours']=sign(d.CES3000000007.rolling(3).mean().diff(12))
    x['LD'],x['ld_mixed']=family([x.temp,x.hours])
    x['LE']=sign(d.CES0000000001.diff().rolling(3).mean())
    x['HO']=sign(d.APERMITS.rolling(3).mean().diff(6))
    cp=d.CUSR0000SA0L1E
    trend=sign((cp/cp.shift(3))**4 - cp/cp.shift(12))
    x['IN']=trend.rolling(3).min().eq(1).astype(float).where(trend.rolling(3).count().eq(3))
    x['C']=(d['10Y3M_MEAN']<0).astype(float).where(d['10Y3M_MEAN'].notna())
    return x

def assess(r,anchor):
    candidates=[]
    conflicts=[]
    ballots=[]
    if r[FIELDS].count()<3: return '', 'too_few_families', ''
    def test(name,base,positive,opposing,veto):
        if not base: return
        ballots.append(f'{name}={len(positive)}/{len(opposing)};+'+','.join(positive)+';-'+','.join(opposing))
        if len(positive)>=2 and len(positive)>len(opposing) and not veto:
            candidates.append(name)
        else:
            conflicts.append(name)
    def votes(mapping):
        return [name for name,flag in mapping.items() if flag]
    bad=dict(LU=r.sahm==1,PO=r.PO<0,LD=r.LD<0,HO=r.HO<0,LE=r.LE<0)
    good=dict(LU=r.LU>0 and r.sahm==0,PO=r.PO>0,LD=r.LD>0,HO=r.HO>0,LE=r.LE>0)
    test('contraction',(bad['LU'] or bad['PO']) and sum(bad.values())>=2,votes(bad),votes(good),r.PO>0 and r.LU>0)
    if anchor=='contraction':
        test('recovery', r.PO>0 and (r.HO>0 or r.LU>0),
             votes(dict(PO=r.PO>0,HO=r.HO>0,LU=r.LU>0)),
             votes(dict(PO=r.PO<0,HO=r.HO<0,LU=r.LU<0)), r.LU<0)
    if anchor!='contraction':
        slow=(r.C==1 or r.IN==1) and (r.LD<0 or r.HO<0)
        test('slowdown',slow,votes(dict(C=r.C==1,IN=r.IN==1,LD=r.LD<0,HO=r.HO<0)),
             votes(dict(LD=r.LD>0,HO=r.HO>0,PO=r.PO>0,LU=r.LU>0)),r.PO>0 and r.LU>0)
        test('expansion',r.PO>0 and r.LD>0 and (anchor!='slowdown' or not slow),
             votes(dict(PO=r.PO>0,LD=r.LD>0,LU=r.LU>0)),
             votes(dict(PO=r.PO<0,LD=r.LD<0,LU=r.LU<0)),r.LU<0)
        if anchor=='recovery':
            test('recovery',r.PO>0 and (r.HO>0 or r.LU>0),
                 votes(dict(PO=r.PO>0,HO=r.HO>0,LU=r.LU>0)),
                 votes(dict(PO=r.PO<0,HO=r.HO<0,LU=r.LU<0)),r.LU<0)
    if candidates:
        return candidates[0],'supported','|'.join(ballots)
    return '', 'conflict' if conflicts else 'no_pattern','|'.join(ballots)

def bands(x,lag):
    result=[]
    anchor=''
    candidate_previous=''
    streak=0
    last_evidence=None
    for month,r in x.shift(lag).loc['1966-01':D1].iterrows():
        choice,why,ballots=assess(r,anchor)
        status=why
        old=anchor
        has_band=''
        streak=streak+1 if choice and choice==candidate_previous else int(bool(choice))
        candidate_previous=choice
        if choice==anchor and anchor:
            has_band=anchor
            status='corroborated'
            last_evidence=month
        elif choice and streak>=2:
            anchor=choice
            last_evidence=month
            if old and (RING.index(anchor)-RING.index(old))%4==2:
                status='over_width'
            else:
                has_band=f'{old}|{anchor}' if old else anchor
                status='transition' if old else 'initial'
        elif why in ['conflict','too_few_families']:
            status=why
        elif anchor and last_evidence is not None and month.ordinal-last_evidence.ordinal<=2:
            has_band=anchor
            status='carry'
        elif choice:
            status='await_confirmation'
        else:
            status='no_recent_support' if anchor else 'uninitialised'
        result.append(dict(month=month,band=has_band,anchor=anchor,anchor_change=anchor if old!=anchor else '',
                           candidate=choice,status=status,ballots=ballots,n_families=int(r[FIELDS].count()),
                           **{k:r[k] for k in x.columns}))
    return pd.DataFrame(result).set_index('month')

def evaluate(out,refs):
    stats={}
    events=[]
    starts=[]
    audits={}
    for phase in ['contraction','recovery']:
        flag=out.band.str.split('|',regex=False).apply(lambda cells: phase in cells)
        starts.extend((m,phase) for m in out.index[flag & ~flag.shift(1,fill_value=False)] if m>=pd.Period(D0))
    recession={m for p,t,_,_ in refs for m in pd.period_range(p+1,t,freq='M')}
    used=set()
    for peak,trough,pnote,tnote in refs:
        for ref,phase,note in [(peak,'contraction',pnote),(trough,'recovery',tnote)]:
            pool=[m for m,s in starts if s==phase and (m,phase) not in used and -3<=m.ordinal-ref.ordinal<=6]
            entry=min(pool,key=lambda m:(abs(m.ordinal-ref.ordinal),m)) if pool else None
            if entry: used.add((entry,phase))
            others=[m for m,s in starts if s==phase and ref-12<=m<=ref+18]
            first_anchors=out.index[(out.anchor_change==phase) & (out.index>=ref-3) & (out.index<=ref+18)]
            events.append(dict(ref=str(ref),phase=phase,announcement=note,match=str(entry) if entry else '',
                delta=entry.ordinal-ref.ordinal if entry else None,
                after_trough=bool(entry and phase=='contraction' and entry>trough),
                starts_within_minus12_plus18=','.join(map(str,others)),
                anchor_changes=','.join(map(str,first_anchors))))
    start_records=[]
    for m,s in starts:
        false_alarm=s=='contraction' and all(k not in recession for k in pd.period_range(m,m+12,freq='M'))
        start_records.append(dict(month=str(m),phase=s,matched=(m,s) in used,false_alarm=false_alarm))
    for name,first,last in [('design',D0,'1999-12'),('temporal',CUT,D1)]:
        o=out.loc[first:last]
        e=[r for r in events if first<=r['ref']<=last]
        s=[r for r in start_records if first<=r['month']<=last]
        counts={}
        for phase in ['contraction','recovery']:
            phase_events=[r for r in e if r['phase']==phase]
            counts[phase]={'matches':sum(bool(r['match']) for r in phase_events),'references':len(phase_events),
                           'starts':sum(r['phase']==phase for r in s),
                           'unmatched_starts':sum(r['phase']==phase and not r['matched'] for r in s)}
        def contains(item):
            m,row=item
            phases=row.band.split('|') if row.band else []
            return ('contraction' in phases if m in recession else any(p!='contraction' for p in phases))
        count_binary=sum(contains(item) for item in o.iterrows())
        valid=o.band.ne('')
        rec_months=sum(m in recession for m in o.index)
        rec_contains=sum(contains(item) for item in o.iterrows() if item[0] in recession)
        committed=o.anchor_change[o.anchor_change!='']
        rollbacks=0
        path=[out.anchor.get(pd.Period(first)-1,'')]+committed.tolist()
        for i in range(2,len(path)):
            rollbacks+=int(bool(path[i-2]) and path[i]==path[i-2])
        stats[name]=dict(months=len(o),shown=int(valid.sum()),abstained=int((~valid).sum()),
                     statuses=o.status.value_counts().to_dict(),band_counts=o.band.value_counts().to_dict(),
                     binary_contains=count_binary,recession_months=rec_months,recession_contains=rec_contains,
                     dual_binary=sum('contraction' in v and '|' in v for v in o.band),
                     mean_width_half_cells=2,local_reversals=rollbacks,
                     false_alarm=[r['month'] for r in s if r['false_alarm']],phases=counts,
                     anchor_entries=committed.value_counts().to_dict(),families=o.n_families.value_counts().to_dict())
    return stats,events,start_records

def main():
    print('design_sha256',hashlib.sha256((ROOT/'design.txt').read_bytes()).hexdigest())
    x=features()
    refs=[(pd.Period(row.peak,'M'),pd.Period(row.trough,'M'),row.peak_announcement,row.trough_announcement)
          for row in pd.read_csv(ROOT/'nber.csv',keep_default_na=False).itertuples()]
    for lag in [1,2]:
        out=bands(x,lag)
        stats,events,starts=evaluate(out,refs)
        (ROOT/f'summary-lag{lag}.json').write_text(json.dumps(stats,indent=2))
        out.loc[D0:D1].to_csv(ROOT/f'months-lag{lag}.csv')
        pd.DataFrame(events).to_csv(ROOT/f'turns-lag{lag}.csv',index=False)
        pd.DataFrame(starts).to_csv(ROOT/f'alarms-lag{lag}.csv',index=False)
        print(lag,stats)
    # NBER was loaded by evaluate() alone; all inputs to the band computation are agency series.
if __name__=='__main__':
    main()
