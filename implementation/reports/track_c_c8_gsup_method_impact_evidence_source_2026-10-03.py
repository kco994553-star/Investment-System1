"""Impact of 5 implementation-defined G-SUP method details. SYNTHETIC; grid values are evaluation-only."""
import sys, math, json, numpy as np
sys.path.insert(0,'/home/user/Investment-System1/implementation/src')
from investment_system.evl import superiority as G
from investment_system.evl.statistical_kernels import circular_block_indices
A=0.10  # evaluation level only
def dgp(kind,n,R,rng):
    burn=100;N=n+burn;e=rng.standard_normal((R,N))
    if kind=='t3': e=rng.standard_t(3,(R,N))/math.sqrt(3)
    if 'garch' in kind:
        w,a,b=.05,.05,.9;h=np.full(R,w/(1-a-b));x=np.empty((R,N))
        for t in range(N): x[:,t]=np.sqrt(h)*e[:,t];h=w+a*x[:,t]**2+b*h
        e=x/np.sqrt(w/(1-a-b))
    if kind=='ma2':
        x=(e[:,2:]+e[:,1:-1]+e[:,:-2])/math.sqrt(3);e=np.concatenate([x,x[:,:2]],1)
    phi={'ar03':.3,'ar045':.45,'ar06':.6,'ar067':2/3,'ar03_garch':.3}.get(kind,0)
    if phi:
        x=np.empty_like(e);x[:,0]=e[:,0]
        for t in range(1,N): x[:,t]=phi*x[:,t-1]+e[:,t]
        e=x*math.sqrt(1-phi**2)
    return e[:,burn:burn+n]
def S(x,L,B,seed,variant='full',fresh=None):
    R,n=x.shape; full=n//L
    if fresh is None: IX=np.array(circular_block_indices(n=n,block_length=L,replicates=B,seed=seed))
    m=x.mean(1); xx=np.concatenate([x,x[:,:L]],1)
    sums=np.stack([xx[:,s:s+L].sum(1) for s in range(n)],1)
    se=np.sqrt(((sums-L*m[:,None])**2).sum(1)/(n*L)/n); T=m/se
    r=np.zeros(R); deg=np.zeros(R)
    for b in range(B):
        ix=IX[b] if fresh is None else fresh[:,b,:]
        v=np.take_along_axis(x,ix[None,:].repeat(R,0),1) if fresh is None else np.take_along_axis(x,ix,1)
        ms=v.mean(1)
        if variant=='full':
            bs=v[:,:full*L].reshape(R,full,L).sum(2); var=((bs-L*ms[:,None])**2).sum(1)/(full*L)
        elif variant=='with_partial':
            k=math.ceil(n/L); bl=[v[:,j*L:(j+1)*L].sum(1) for j in range(k)]; ln=[min(L,n-j*L) for j in range(k)]
            var=sum((bl[j]-ln[j]*ms)**2 for j in range(k))/n
        elif variant=='overlap':
            vv=np.concatenate([v,v[:,:L]],1); os_=np.stack([vv[:,s:s+L].sum(1) for s in range(n)],1)
            var=((os_-L*ms[:,None])**2).sum(1)/(n*L)
        t=np.where(var>0,(ms-m)/np.sqrt(np.where(var>0,var,1)/n),np.inf); deg+=var<=0
        r+=t>=T
    return (r+1)/(B+1),deg
out={}
rng=np.random.default_rng(2026)
# (0) exact agreement of numpy port with repository kernel
x=dgp('ar03',24,5,rng)
pk=[G.studentized_cbb(tuple(row),block_length=3,replicates=99,seed=7)['p_value'] for row in x]
pn,_=S(x,3,99,7); out['port_matches_kernel']=bool(np.allclose(pk,pn,rtol=0,atol=0))
# (1) estimator bias
est={}
for phi,kind in ((0,'iid'),(.3,'ar03'),(.6,'ar06')):
    for nd in (24,60,120):
        z=dgp(kind,nd,4000,rng); zc=z-z.mean(1,keepdims=True)
        ph=(zc[:,1:]*zc[:,:-1]).sum(1)/(zc**2).sum(1)
        est[f'phi={phi}|n_dev={nd}']={'mean_hat':round(float(ph.mean()),3),'p05':round(float(np.quantile(ph,.05)),3),'share_below_true':round(float((ph<phi).mean()),3)}
out['1_estimator']=est
# MA2 lag-1/lag-2 truth vs AR1 implied
out['1_ma2_note']={'true_rho1':2/3,'true_rho2':1/3,'AR1_with_rho1_implies_rho2':round((2/3)**2,3)}
# (2) envelope coverage: true DGP size vs Gaussian AR1 with same lag-1
cov={}
R=3000;B=199
for n,L in ((24,3),(60,4)):
    for kind,match in (('t3','iid'),('garch','iid'),('ar03_garch','ar03'),('ma2','ar067')):
        p1,_=S(dgp(kind,n,R,rng),L,B,11); p2,_=S(dgp(match,n,R,rng),L,B,11)
        cov[f'n={n},L={L}|{kind} vs AR1({match})']={'true_size':round(float((p1<=A).mean()),3),'gaussian_AR1_size':round(float((p2<=A).mean()),3)}
out['2_envelope']=cov
# (3) degenerate replicates / ties
deg={}
for n,L in ((8,4),(12,6),(24,3)):
    z=dgp('iid',n,2000,rng); p,d=S(z,L,199,5); deg[f'continuous n={n},L={L}']=float(d.mean())
    zr=np.round(z*2)/2   # coarse discretisation (illustrative)
    p_a,d_a=S(zr,L,199,5); deg[f'coarse_discrete n={n},L={L}']={'mean_degenerate_per_dataset':round(float(d_a.mean()),2),'size_conservative_rule':round(float((p_a<=A).mean()),3)}
out['3_degenerate']=deg
# (4) variance definition
var={}
for kind in ('iid','ar03','ar06'):
    for n,L in ((12,3),(26,4),(36,4)):
        z=dgp(kind,n,3000,rng)
        var[f'{kind}|n={n},L={L}']={v:round(float((S(z,L,199,13,v)[0]<=A).mean()),3) for v in ('full','with_partial','overlap')}
out['4_variance']=var
# (5) feasibility seed: conditional size across fixed seeds vs fresh indices
sd={}
for kind,(n,L) in (('iid',(24,3)),('ar03',(24,3)),('ar03',(60,4))):
    z=dgp(kind,n,2000,rng); sizes=[float((S(z,L,99,s)[0]<=A).mean()) for s in range(20)]
    fresh=rng.integers(0,n,(2000,99,math.ceil(n/L)))
    fi=(fresh[:,:,:,None]+np.arange(L))%n; fi=fi.reshape(2000,99,-1)[:,:,:n]
    pf,_=S(z,L,99,0,fresh=fi)
    sd[f'{kind}|n={n},L={L}']={'fixed_seed_size_min':round(min(sizes),3),'fixed_seed_size_max':round(max(sizes),3),'fresh_indices_size':round(float((pf<=A).mean()),3)}
out['5_seed']=sd
json.dump(out,open('impact.json','w'),indent=1); print(json.dumps(out,indent=1))
