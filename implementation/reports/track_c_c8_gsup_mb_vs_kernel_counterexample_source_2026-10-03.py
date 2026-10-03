"""Minimal counterexample: approved M-B simulation semantics vs implemented C8_GSUP_STUDENTIZED_CBB_v1."""
import sys, math, json, random
sys.path.insert(0,'/home/user/Investment-System1/implementation/src')
from investment_system.evl import superiority as G
from investment_system.evl.statistical_kernels import circular_block_indices, MissingStatisticalEvidence

def mb_reference(x, L, B, seed):
    """Exact scalar port of msim.py run() S_plus1 for one series (approval-evidence semantics):
    replicate variance over the first ceil(n/L)-1 blocks; NOT_RUN unless ceil(n/L)-1 >= 2;
    degenerate replicate -> t*=-inf (never exceeds). Same indices as the kernel."""
    n=len(x); k=math.ceil(n/L)
    if k-1<2: return 'NOT_RUN'
    m=sum(x)/n
    sums=[sum(x[(s+j)%n] for j in range(L)) for s in range(n)]
    se=math.sqrt(sum((v-L*m)**2 for v in sums)/(n*L)/n); T=m/se
    r=0; deg=0
    for ix in circular_block_indices(n=n,block_length=L,replicates=B,seed=seed):
        v=[x[i] for i in ix]; ms=sum(v)/n
        bl=[sum(v[j*L:(j+1)*L]) for j in range(k-1)]
        var=sum((b-L*ms)**2 for b in bl)/((k-1)*L)
        if var>0: r += (ms-m)/math.sqrt(var/n) >= T
        else: deg+=1
    return {'p':(r+1)/(B+1),'r':r,'degenerate':deg}

def kernel(x,L,B,seed):
    try:
        o=G.studentized_cbb(tuple(x),block_length=L,replicates=B,seed=seed)
        return {'p':o['p_value'],'r':o['exceedances'],'degenerate':o['degenerate_replicates']}
    except MissingStatisticalEvidence as e: return 'NOT_RUN'

out={}
# CE-1 runnability: n=4, L=2 (L divides n): M-B has ceil(4/2)-1 = 1 block -> NOT_RUN; kernel has 4//2 = 2 full blocks -> runs
x1=[0.03,-0.01,0.02,0.01]
out['CE1_n4_L2']={'data':x1,'B':19,'seed':1,'MB':mb_reference(x1,2,19,1),'kernel':kernel(x1,2,19,1)}
# CE-2 same data, L divides n, both run, different block count -> different p
x2=[0.03,-0.01,0.02,0.01,0.00,0.02]
out['CE2_n6_L2']={'data':x2,'B':19,'seed':1,'MB':mb_reference(x2,2,19,1),'kernel':kernel(x2,2,19,1)}
# CE-3 L does not divide n: both use 2 full blocks; differ only via degenerate replicate scoring
x3=[0.03,-0.01,0.02,0.01,0.00]
out['CE3_n5_L2']={'data':x3,'B':19,'seed':1,'MB':mb_reference(x3,2,19,1),'kernel':kernel(x3,2,19,1)}
# search smallest decision flip at an evaluation level (0.10, evaluation-only) for L not dividing n
rng=random.Random(5); found=None
for trial in range(5000):
    n=rng.choice([5,7]); x=[round(rng.gauss(0.01,0.02),3) for _ in range(n)]
    a=mb_reference(x,2,19,trial); b=kernel(x,2,19,trial)
    if a!='NOT_RUN' and b!='NOT_RUN' and (a['p']<=0.10)!=(b['p']<=0.10):
        found={'data':x,'L':2,'B':19,'seed':trial,'MB':a,'kernel':b}; break
out['CE4_decision_flip_L_not_dividing_n']=found
# agreement check: when L does not divide n and no degenerate replicate, identical
agree=0;tot=0
for trial in range(300):
    n=rng.choice([25,31,37]); L=rng.choice([3,4,6]);
    if n%L==0: continue
    x=[rng.gauss(0,1) for _ in range(n)]; a=mb_reference(x,L,49,trial); b=kernel(x,L,49,trial)
    if a!='NOT_RUN' and b!='NOT_RUN' and a['degenerate']==0 and b['degenerate']==0:
        tot+=1; agree+= abs(a['p']-b['p'])<1e-15
out['agreement_when_L_not_divides_n_and_no_degenerate']={'cases':tot,'identical':agree}
json.dump(out,open('mb_counterexample.json','w'),indent=1); print(json.dumps(out,indent=1))
