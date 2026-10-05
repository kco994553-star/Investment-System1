"""Synthetic financial sync -> scoped provenance -> existing portfolio analytics."""
import json
import re
import threading
from datetime import datetime
from decimal import Decimal, localcontext
from .domain import PlatformError, READ_CAPABILITIES, RESOURCES, TRANSACTION_KINDS, aware, decimal_text, require_read_only, safe_json
from ..personal.money import Money
from ..personal.portfolio import ActualPortfolioSnapshot, Position, PositionSource
from ..personal.quality import DataQuality
from ..personal.ports import FORBIDDEN_BROKER_METHODS

_METHODS={"accounts":"list_accounts","balances":"sync_balances","positions":"sync_positions","transactions":"sync_transactions","statements":"sync_statements"}
_CAPS={"accounts":"READ_ACCOUNT","balances":"READ_BALANCE","positions":"READ_POSITION","transactions":"READ_TRANSACTION","statements":"READ_STATEMENT"}
_BASE={"id","revision","account_id","effective_at","available_at","provider_reported_at"}
_FIELDS={"accounts":_BASE|{"currency","status"},"balances":_BASE|{"currency","cash","total"},"positions":_BASE|{"currency","quantity","market_value","security_id","listing_id","ticker"},"transactions":_BASE|{"currency","kind","amount","security_id","listing_id"},"statements":_BASE|{"reference"}}

def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z0-9_-]+",value):
        raise PlatformError("INVALID_IDENTIFIER")
    return value

class PlatformService:
    def __init__(self,store,identities,*,max_payload_bytes,max_pages):
        self.store=store
        self.issuers,self.securities,self.listings=identities
        self.issuers={i.issuer_id:i for i in self.issuers}
        self.securities={s.security_id:s for s in self.securities}
        self.listings={l.listing_id:l for l in self.listings}
        if type(max_payload_bytes) is not int or max_payload_bytes<=0 or type(max_pages) is not int or max_pages<=0:
            raise ValueError("explicit positive resource limits required")
        self.max_payload_bytes=max_payload_bytes
        self.max_pages=max_pages
        self._connectors={}
        self.lock=threading.RLock()

    def _check(self,connector):
        if getattr(connector,'synthetic',False) is not True:
            raise PlatformError("REAL_CONNECTOR_NOT_AUTHORIZED")
        if any(callable(getattr(connector,m,None)) for m in (*FORBIDDEN_BROKER_METHODS,"buy","sell","trade","deposit","order","cancel_order","account_modify","create_order","execute_order","replace_order","transfer_funds","withdraw_funds","deposit_funds")):
            raise PlatformError("CAPABILITY_REJECTED")
        caps=require_read_only(connector.capabilities())
        if connector.connection_status()!="ACTIVE":
            raise PlatformError("CONNECTION_REVOKED")
        if not {"READ_ACCOUNT","READ_BALANCE","READ_POSITION","READ_TRANSACTION"}<=caps:
            raise PlatformError("MISSING_READ_CAPABILITY")
        return caps

    def create_connection(self,p,connector,now):
        with self.lock:
            self._check(connector)
            if any(existing is connector for existing in self._connectors.values()):
                raise PlatformError("CONNECTOR_ALREADY_BOUND")
            cid=self.store.create_connection(p,identifier(connector.provider_id),now)
            self._connectors[(*self.store.scope(p),cid)]=connector
            return cid

    def _connector(self,p,cid,now):
        c=self.store.connection(p,cid)
        if c['state']!="ACTIVE":
            raise PlatformError("CONNECTION_REVOKED")
        connector=self._connectors.get((*self.store.scope(p),cid))
        if connector is None:
            raise PlatformError("CONNECTOR_NOT_ATTACHED")
        if connector.connection_status()!='ACTIVE':
            self.store.revoke(p,cid,now)
            raise PlatformError("CONNECTION_REVOKED")
        self._check(connector)
        return connector

    def revoke_connection(self,p,cid,now):
        with self.lock:
            connector=self._connector(p,cid,now)
            connector.revoke_connection()
            self.store.revoke(p,cid,now)

    def _admit_shape(self,resource,data):
        if not isinstance(data,dict) or set(data)!={"schema_version","effective_at","available_at","provider_reported_at","data_state","records"}:
            raise PlatformError("SCHEMA_REJECTED")
        if data['schema_version']!="synthetic-financial-v1" or data['data_state'] not in {"DEMO","STALE","DELAYED"} or not isinstance(data['records'],list):
            raise PlatformError("SCHEMA_REJECTED")
        if any(not isinstance(r,dict) or not set(r)<=_FIELDS[resource] for r in data['records']):
            raise PlatformError("SCHEMA_REJECTED")

    def _normalize(self,resource,data,rid,decision_time):
        self._admit_shape(resource,data)
        defaults={k:aware(data[k]) for k in ('effective_at','available_at','provider_reported_at')}
        if any(v>decision_time for v in defaults.values()):
            raise PlatformError("FUTURE_DATA")
        out=[]
        for r in data['records']:
            if not isinstance(r,dict) or not set(r)<=_FIELDS[resource] or 'id' not in r or type(r.get('revision')) is not int or r['revision']<=0:
                raise PlatformError("SCHEMA_REJECTED")
            oid=identifier(r['id'])
            aid=oid if resource=='accounts' else identifier(r.get('account_id'))
            stamps={k:aware(r.get(k,defaults[k])) for k in defaults}
            if any(v>decision_time for v in stamps.values()):
                raise PlatformError("FUTURE_DATA")
            n={**r,**{k:v.isoformat() for k,v in stamps.items()},"data_state":data['data_state']}
            if resource!='statements':
                currency=r.get('currency')
                if not isinstance(currency,str) or re.fullmatch(r'[A-Z]{3}',currency) is None:
                    raise PlatformError("INVALID_CURRENCY")
            if resource=='accounts' and r.get('status') not in {'OPEN','CLOSED'}:
                raise PlatformError("SCHEMA_REJECTED")
            for k in {'balances':('cash','total'),'positions':('quantity','market_value'),'transactions':('amount',)}.get(resource,()):
                decimal_text(r.get(k))
            if resource=='transactions' and r.get('kind') not in TRANSACTION_KINDS:
                raise PlatformError("INVALID_TRANSACTION_KIND")
            if resource=='statements' and not isinstance(r.get('reference'),str):
                raise PlatformError("SCHEMA_REJECTED")
            if resource in {'positions','transactions'}:
                sid,lid=r.get('security_id'),r.get('listing_id')
                s,l=self.securities.get(sid),self.listings.get(lid)
                valid=bool(s and l and s.issuer_id in self.issuers and l.security_id==sid and l.active_on(stamps['effective_at'].date()) and l.currency==r['currency'])
                n['resolution_status']='RESOLVED' if valid else 'UNRESOLVED'
                n['issuer_id']=s.issuer_id if valid else None
                if 'ticker' in r and valid and r['ticker']!=l.ticker:
                    n['resolution_status']='UNRESOLVED'
                    n['issuer_id']=None
            out.append({'resource':resource,'object_id':oid,'revision':r['revision'],'account_id':aid,'effective_at':stamps['effective_at'].isoformat(),'available_at':stamps['available_at'].isoformat(),'receipt_id':rid,'payload':n})
        return out

    def sync(self,p,cid,now):
        now=aware(now)
        # Scope validated before creating a job, obtaining a cursor or touching a provider.
        with self.lock:
            connector=self._connector(p,cid,now)
            run=self.store.start_run(p,cid,now)
            normalized=[]
            resource_metadata=[]
            cursors={}
            state='SUCCEEDED'
            try:
                for resource in ('accounts','balances','positions','transactions','statements'):
                    caps=self._check(connector)
                    if _CAPS[resource] not in caps:
                        continue
                    cursor=self.store.cursor(p,cid,resource) if resource=='transactions' else None
                    seen=set()
                    for _ in range(self.max_pages):
                        if cursor in seen:
                            raise PlatformError("CURSOR_LOOP")
                        seen.add(cursor)
                        self._check(connector)
                        page=getattr(connector,_METHODS[resource])(cursor)
                        if page.resource!=resource or type(page.complete) is not bool:
                            raise PlatformError("SCHEMA_REJECTED")
                        if not page.complete:
                            state='PARTIAL'
                        data=safe_json(page.body,self.max_payload_bytes)
                        # Closed shape admission precedes persistence, including unknown/confusable secret keys.
                        self._admit_shape(resource,data)
                        raw=self.store.raw(p,cid,resource,page.body,now)
                        normalized.extend(self._normalize(resource,data,raw,now))
                        resource_metadata.append({'resource':resource,'data_state':data['data_state'],'effective_at':data['effective_at'],'available_at':data['available_at'],'provider_reported_at':data['provider_reported_at'],'receipt_id':raw,'fetched_at':now.isoformat(),'ingested_at':now.isoformat()})
                        for token in (page.next_cursor,page.resume_cursor):
                            if token is not None and (not isinstance(token,str) or not token):
                                raise PlatformError("CURSOR_REJECTED")
                        if page.next_cursor is None:
                            cursors[resource]=page.resume_cursor
                            break
                        cursor=page.next_cursor
                    else:
                        raise PlatformError("PAGE_LIMIT")
                self._check(connector)
                # Cross-reference/currency validation before any normalized mutation.
                unique={}
                for r in normalized:
                    key=(r['resource'],r['object_id'],r['revision'])
                    if key in unique and unique[key]['payload']!=r['payload']:
                        raise PlatformError("REVISION_COLLISION")
                    unique[key]=r
                normalized=list(unique.values())
                current={}
                for r in sorted(normalized,key=lambda r:r['revision']):
                    current[(r['resource'],r['object_id'])]=r
                projection=list(current.values())
                accounts=[r for r in projection if r['resource']=='accounts']
                account_map={r['object_id']:r['payload'] for r in accounts}
                if len(account_map)!=len(accounts):
                    raise PlatformError("DUPLICATE_ACCOUNT")
                for r in normalized:
                    if r['account_id'] not in account_map:
                        raise PlatformError("CROSS_ACCOUNT_REFERENCE")
                    if r['resource'] not in {'accounts','statements'} and r['payload']['currency']!=account_map[r['account_id']]['currency']:
                        raise PlatformError("CURRENCY_MISMATCH")
                if state=='SUCCEEDED':
                    # Append revisions with transaction rollback on collision; only then move watermark.
                    snapshot=self._portfolio(p,cid,projection,now,resource_metadata)
                    self.store.commit_records(p,cid,normalized,cursors,snapshot,now)
                self.store.finish_run(p,run,state,now)
            except PlatformError as e:
                if e.code=='CONNECTION_REVOKED':
                    self.store.revoke(p,cid,now)
                self.store.finish_run(p,run,'REVOKED' if e.code=='CONNECTION_REVOKED' else 'FAILED',now,e.code if e.code in _SAFE_ERRORS else 'PROVIDER_FAILURE')
            except Exception:
                self.store.finish_run(p,run,'FAILED',now,'PROVIDER_FAILURE')
            return self.store.run(p,run)

    def _portfolio(self,p,cid,records,now,resource_metadata):
        group={r:[] for r in RESOURCES}
        for r in records:
            group[r['resource']].append({**r['payload'],'receipt_id':r['receipt_id']})
        # Every resource membership is the latest COMPLETE read, not all historical ids.
        accounts={r['id']:r for r in group['accounts']}
        balances={}
        for b in group['balances']:
            if b['account_id'] in balances:
                raise PlatformError("DUPLICATE_BALANCE")
            balances[b['account_id']]=b
        reconciliation=[]
        resolved=all(r['resolution_status']=='RESOLVED' for r in group['positions'])
        sign_consistent=all((decimal_text(r['quantity'])>0 and decimal_text(r['market_value'])>=0) or (decimal_text(r['quantity'])==0 and decimal_text(r['market_value'])==0) for r in group['positions'])
        data_states={r['data_state'] for r in resource_metadata}|{r['payload']['data_state'] for r in records}
        comparable=True
        for aid,a in accounts.items():
            b=balances.get(aid)
            pos=[x for x in group['positions'] if x['account_id']==aid]
            same_time=b is not None and all(aware(x['effective_at'])==aware(b['effective_at']) for x in pos) and all(aware(x['effective_at'])==aware(b['effective_at']) for x in resource_metadata if x['resource'] in {'positions','balances','accounts'}) and a['status']=='OPEN'
            if not same_time:
                comparable=False
                status='NOT_COMPARABLE'
                difference=None
            else:
                values=[decimal_text(x['market_value']) for x in pos]+[decimal_text(b['cash']),decimal_text(b['total']).copy_negate()]
                # Exact addition precision is derived from source decimals, not a financial rounding rule.
                with localcontext() as ctx:
                    ctx.prec=max(28,sum(len(x.as_tuple().digits)+abs(x.as_tuple().exponent) for x in values)+2)
                    d=sum(values,Decimal(0))
                status='MATCH' if d==0 else 'MISMATCH'
                difference=str(d)
            reconciliation.append({'account_id':aid,'reported_values':status,'difference':difference,'transactions':'NOT_COMPARABLE','statements':'NOT_COMPARABLE'})
        complete=bool(accounts) and all(a['status']=='OPEN' for a in accounts.values()) and set(balances)==set(accounts) and comparable
        currency_set={a['currency'] for a in accounts.values()}
        analytics=None
        numeric_status='NOT_CALCULATED'
        if complete and resolved and sign_consistent and len(currency_set)==1 and not ({'STALE','DELAYED'}&data_states):
            currency=next(iter(currency_set))
            positions=tuple(Position(r['account_id'],r['security_id'],decimal_text(r['quantity']),Money(decimal_text(r['market_value']),currency),aware(r['effective_at']),aware(r['effective_at']),PositionSource.USER_ENTERED,DataQuality.VALID) for r in group['positions'])
            existing=ActualPortfolioSnapshot(p.user_id,tuple(accounts),now,positions,tuple(Money(decimal_text(b['cash']),currency) for b in balances.values()),currency,True,DataQuality.VALID)
            inputs=[p.market_value.amount for p in positions]+[m.amount for m in existing.cash]
            with localcontext() as ctx:
                ctx.prec=max(28,sum(len(x.as_tuple().digits)+abs(x.as_tuple().exponent) for x in inputs)+2)
                exact_total=sum(inputs,Decimal(0))
            if existing.total_value()==exact_total:
                numeric_status='EXISTING_CONTEXT_SUFFICIENT'
                analytics={'source':'personal.ActualPortfolioSnapshot','calculated_total':str(existing.total_value()),'currency':currency,'calculated_weights':{k:str(v) for k,v in existing.weights().items()},'numeric_context':'existing Decimal context; source lexical precision preserved','is_reconciled':all(r['reported_values']=='MATCH' for r in reconciliation)}
            else:
                numeric_status='EXISTING_CONTEXT_PRECISION_INSUFFICIENT'
        effective={aware(x['effective_at']).isoformat() for x in resource_metadata if x['resource'] in {'accounts','balances','positions'}}
        return {'contract_version':'product-platform-v0.1','portfolio_kind':'ACTUAL','data_state':'STALE' if 'STALE' in data_states else 'DELAYED' if 'DELAYED' in data_states else 'DEMO','is_real':False,'synthetic':True,'complete':complete,'identity_status':'RESOLVED' if resolved else 'UNRESOLVED','quantity_status':'SUPPORTED_LONG_FIXTURE' if sign_consistent else 'UNSUPPORTED_OR_INCONSISTENT_DIRECTION','numeric_status':numeric_status,'as_of':next(iter(effective)) if len(effective)==1 else None,'sync_completed_at':now.isoformat(),'accounts':group['accounts'],'balances':group['balances'],'positions':group['positions'],'reconciliation':reconciliation,'analytics':analytics,'resource_metadata':resource_metadata,'receipt_ids':sorted({r['receipt_id'] for r in resource_metadata}), 'engines':{name:{'state':'NOT_AVAILABLE','reason':'OWNER_CONTRACT_OR_PUBLICATION_DEPENDENCY'} for name in ('qgv','technical','macro','news','chart')},'target':{'state':'NOT_AVAILABLE','reason':'AUTHORITATIVE_TARGET_NOT_CONNECTED'}}

    def portfolio(self,p,cid,now):
        c=self.store.connection(p,cid)
        connector=self._connectors.get((*self.store.scope(p),cid))
        if c['state']=='ACTIVE' and connector is not None and connector.connection_status()!='ACTIVE':
            self.store.revoke(p,cid,now)
            c=self.store.connection(p,cid)
        data=self.store.latest_snapshot(p,cid,now)
        if data is None:
            return {'data_state':'NOT_AVAILABLE','reason':'NO_COMPLETE_SYNC','data':None}
        if c['state']=='REVOKED':
            data={**data,'data_state':'STALE','connection_state':'REVOKED'}
        data['last_sync_attempt']=self.store.last_run(p,cid,now)
        return data

    def export(self,p,cid,now):
        self.store.connection(p,cid)
        with self.store.lock,self.store.db:
            self.store.event(p,'DATA_EXPORTED',cid,now)
        return {'portfolio':self.portfolio(p,cid,now),'transactions':[json.loads(r['payload'])|{'receipt_id':r['receipt_id']} for r in self.store.records(p,cid,'transactions',now,history=True)],'audit':self.store.audit(p),'is_real':False}

_SAFE_ERRORS={"CAPABILITY_REJECTED","CONNECTION_REVOKED","MISSING_READ_CAPABILITY","PAYLOAD_REJECTED","DUPLICATE_KEY","INVALID_NUMBER","SECRET_PAYLOAD_REJECTED","SCHEMA_REJECTED","FUTURE_DATA","INVALID_TIME","INVALID_IDENTIFIER","INVALID_CURRENCY","INVALID_TRANSACTION_KIND","CURSOR_LOOP","CURSOR_REJECTED","PAGE_LIMIT","DUPLICATE_ACCOUNT","DUPLICATE_BALANCE","CROSS_ACCOUNT_REFERENCE","CURRENCY_MISMATCH","REVISION_COLLISION","REVISION_REGRESSION","PROVENANCE_FAILED","NOT_FOUND","PROVIDER_UNAVAILABLE","PERMISSION_DENIED"}
