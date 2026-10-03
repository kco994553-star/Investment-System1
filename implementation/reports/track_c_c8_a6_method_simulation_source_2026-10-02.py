"""A6 method package simulation. SYNTHETIC. n/L/B/levels are EVALUATION GRID ONLY, never defaults."""
import numpy as np, math, json, sys
from scipy import stats
LV=(0.05,0.10)

def dgp(kind,n,R,rng,mu=0.0):
    burn=200; N=n+burn; e=rng.standard_normal((R,N))
    if kind=='t3': e=rng.standard_t(3,(R,N))/math.sqrt(3)
    if 'garch' in kind:
        w,a,b=0.05,0.05,0.90; h=np.full(R,w/(1-a-b)); x=np.empty((R,N))
        for t in range(N): x[:,t]=np.sqrt(h)*e[:,t]; h=w+a*x[:,t]**2+b*h
        e=x/np.sqrt(w/(1-a-b))
    if kind=='ma2':   # overlapping 3-period horizon sampled each period
        x=(e[:,2:]+e[:,1:-1]+e[:,:-2])/math.sqrt(3); e=np.concatenate([x,x[:,:2]],1)
    phi={'ar01':.1,'ar02':.2,'ar03':.3,'ar045':.45,'ar06':.6,'ar03_garch':.3}.get(kind,0)
    if phi:
        x=np.empty_like(e); x[:,0]=e[:,0]
        for t in range(1,N): x[:,t]=phi*x[:,t-1]+e[:,t]
        e=x*math.sqrt(1-phi**2)
    return e[:,burn:burn+n]+mu

def run(x,L,B,rng):
    R,n=x.shape; k=math.ceil(n/L); rem=n-(k-1)*L
    xx=np.concatenate([x,x[:,:L]],1); cs=np.concatenate([np.zeros((R,1)),np.cumsum(xx,1)],1); s=np.arange(n)
    full=cs[:,s+L]-cs[:,s]; part=cs[:,s+rem]-cs[:,s]; m=x.mean(1)
    lrv=((full-L*m[:,None])**2).sum(1)/(n*L); se=np.sqrt(lrv/n)
    TU=np.sqrt(n)*m; TS=np.where(se>0,m/np.where(se>0,se,1),np.nan)
    rU=np.zeros(R); rS=np.zeros(R); okS=(k-1)>=2
    for b in range(B):
        st=rng.integers(0,n,(R,k)); sums=np.take_along_axis(full,st[:,:k-1],1) if k>1 else np.zeros((R,0))
        last=np.take_along_axis(part,st[:,k-1:],1)[:,0]; ms=(sums.sum(1)+last)/n
        rU+=np.sqrt(n)*(ms-m)>=TU
        if okS:
            v=((sums-L*ms[:,None])**2).sum(1)/((k-1)*L); sv=np.sqrt(v/n)
            rS+=np.where(sv>0,(ms-m)/np.where(sv>0,sv,1),-np.inf)>=TS
    out={'U_kernel_raw':rU/B,'U_plus1':(rU+1)/(B+1),'S_plus1':(rS+1)/(B+1) if okS else np.full(R,np.nan)}
    mb=n//L                                    # batch-means t (non-overlapping), df=mb-1
    if mb>=3:
        bm=x[:,:mb*L].reshape(R,mb,L).mean(2); t=bm.mean(1)/(bm.std(1,ddof=1)/math.sqrt(mb))
        out['BM_t']=stats.t.sf(t,mb-1)
    else: out['BM_t']=np.full(R,np.nan)
    return out

def summ(p):
    if np.all(np.isnan(p)): return 'NOT_RUN'
    return {str(a):round(float(np.nanmean(p<=a)),4) for a in LV}

if __name__=='__main__':
    mode=sys.argv[1]; R=int(sys.argv[2]); B=int(sys.argv[3]); rng=np.random.default_rng(int(sys.argv[4])); res={}
    NS=(8,12,16,24,36,60,120,240)
    if mode=='size':
        for kind in ('iid','t3','ma2','ar01','ar02','ar03','ar045','ar06','garch','ar03_garch'):
            for n in NS:
                x=dgp(kind,n,R,rng)
                for L in (1,2,3,4,6,8,12):
                    if L>n//2: continue
                    o=run(x,L,B,rng); res[f'{kind}|{n}|{L}']={k:summ(v) for k,v in o.items()}
            print(kind,flush=True)
    if mode=='power':
        for kind in ('iid','ar02','ar03_garch'):
            for n in NS:
                for d in (0.2,0.4,0.8):
                    x=dgp(kind,n,R,rng,mu=d)
                    for L in (2,4,8):
                        if L>n//2: continue
                        o=run(x,L,B,rng); res[f'{kind}|{n}|{L}|{d}']={k:summ(v) for k,v in o.items()}
            print(kind,flush=True)
    json.dump(res,open(f'm_{mode}.json','w'))
