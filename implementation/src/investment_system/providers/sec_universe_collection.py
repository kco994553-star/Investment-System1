"""Explicit SEC ticker-evidence Universe scope and stable daily shards.

No fetch on import, price data, publication, investment ranking or scheduling
start date. Supplied metadata hashes bind bytes, not origin authenticity.
"""
from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path

from .sec_collection import SecCollectionClient, SecCollectionError, MAX_BODY_BYTES
from .sec_companyfacts import SEC_FACTS_URL
from .sec_submissions import URL as SUBMISSIONS_URL


_REGISTRY_TOKEN=object()


@dataclass(frozen=True)
class UniverseIssuer:
    cik: str
    codes: tuple[str, ...]


@dataclass(frozen=True)
class UniverseRegistry:
    issuers: tuple[UniverseIssuer, ...]
    source_sha256: str
    unresolved_code_count: int
    _validation_token: object = field(default=None,init=False,repr=False,compare=False)

    @property
    def code_count(self):
        return sum(len(x.codes) for x in self.issuers)


def universe_registry(body):
    """Bind only approved 504 codes to supplied SEC exchange/ticker metadata.

    NYSE BRK.B/SEC BRK-B is an explicit punctuation alias, never a share-basis
    conversion. Conflicting CIKs and unrecognized exchange/ticker pairs remain
    unresolved. Names are ignored; the caller verifies official source origin.
    """
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError()
            d[k]=v
        return d
    def reject(_):raise ValueError()
    try:
        if type(body) is not bytes or len(body)>MAX_BODY_BYTES:raise ValueError()
        payload=json.loads(body,object_pairs_hook=pairs,parse_constant=reject)
        fields=payload['fields'];rows=payload['data']
        if type(fields) is not list or len(fields)!=4 or set(fields)!={'cik','name','ticker','exchange'} or type(rows) is not list or len(rows)>50000:raise ValueError()
        codes=json.loads((Path(__file__).parents[1]/'universe/universe_codes_v1.json').read_text())
        lookup={(c.split(':')[0],c.split(':')[1].replace('.','-')):c for c in codes}
        bindings={c:set() for c in codes}
        for row in rows:
            if type(row) is not list or len(row)!=4:continue
            d=dict(zip(fields,row));cik=d['cik'];ticker=d['ticker'];exchange=d['exchange']
            if type(cik) is not int or not 0<cik<10**10 or type(ticker) is not str or type(exchange) is not str:continue
            venue={'Nasdaq':'NASDAQ','NYSE':'NYSE'}.get(exchange)
            code=lookup.get((venue,ticker))
            if code is not None:bindings[code].add(str(cik).zfill(10))
        grouped={}
        for code,ciks in bindings.items():
            if len(ciks)==1:grouped.setdefault(next(iter(ciks)),[]).append(code)
        issuers=tuple(UniverseIssuer(cik,tuple(sorted(selected))) for cik,selected in sorted(grouped.items()))
        result=UniverseRegistry(issuers,sha256(body).hexdigest(),sum(len(v)!=1 for v in bindings.values()))
        object.__setattr__(result,'_validation_token',_REGISTRY_TOKEN)
        return result
    except (ValueError,TypeError,KeyError,UnicodeError,RecursionError,OSError):
        raise SecCollectionError('SEC_UNIVERSE_INPUT_INVALID') from None


def daily_partition(registry, *, shard_count, shard_index):
    """Engineering workload partition; caller supplies today's explicit index.

    Changing count changes allocation. Keep count fixed over a collection cycle;
    no automatic dates, validation periods or investment-universe selection.
    """
    if (type(registry) is not UniverseRegistry or registry._validation_token is not _REGISTRY_TOKEN or type(shard_count) is not int or
            not 1<=shard_count<=366 or type(shard_index) is not int or not 0<=shard_index<shard_count):
        raise SecCollectionError('SEC_UNIVERSE_CONFIG_INVALID') from None
    return tuple(x for x in registry.issuers if int(sha256(x.cik.encode()).hexdigest(),16)%shard_count==shard_index)


class UniverseSecClient(SecCollectionClient):
    """Separate explicit scope; legacy collect remains US17-only.

    All issuer calls and retries share the inherited serial lock/0.2s pacer.
    Operators must coordinate this client with other SEC jobs under SEC limits.
    """
    def __init__(self, user_agent, *, registry, **kwargs):
        if type(registry) is not UniverseRegistry or registry._validation_token is not _REGISTRY_TOKEN:
            raise SecCollectionError('SEC_UNIVERSE_CONFIG_INVALID') from None
        self._universe_ciks=frozenset(x.cik for x in registry.issuers)
        super().__init__(user_agent,**kwargs)

    def collect_universe(self,cik):
        if type(cik) is not str or cik not in self._universe_ciks:
            raise SecCollectionError('SEC_ISSUER_NOT_ALLOWED') from None
        with self._lock:
            facts=self._request(SEC_FACTS_URL.format(cik=cik),cik)
            sub=self._request(SUBMISSIONS_URL.format(cik=cik),cik)
            return facts,sub,self._utc()


@dataclass(frozen=True)
class UniverseBatchResult:
    collected: int
    failed: int
    failures: tuple[tuple[int, str], ...]

    @property
    def all_failed(self):
        return self.failed>0 and self.collected==0


def collect_partition(client,issuers,*,on_success):
    """Sequential isolated issuer pairs. Raw bytes reach only supplied sink.

    A sink failure counts as a failed issuer. Only fixed codes leave this API;
    callers decide exit1 only for all_failed. No logging or file writes here.
    """
    import re
    if not isinstance(client,UniverseSecClient) or type(issuers) is not tuple or not all(type(x) is UniverseIssuer for x in issuers) or not callable(on_success):
        raise SecCollectionError('SEC_UNIVERSE_CONFIG_INVALID') from None
    failures=[];collected=0
    for index,issuer in enumerate(issuers,1):
        try:
            facts,sub,acquired=client.collect_universe(issuer.cik)
        except Exception as error:
            code=error.args[0] if isinstance(error,SecCollectionError) and error.args else None
            allowed={'SEC_TRANSPORT_RETRIES_EXHAUSTED','SEC_RETRY_AFTER_EXCEEDS_BUDGET','SEC_HTTP_RETRIES_EXHAUSTED','SEC_JSON_INVALID','SEC_CIK_MISMATCH','SEC_RESPONSE_TOO_LARGE','SEC_TRANSPORT_FAILED','SEC_REDIRECT_REJECTED','SEC_RESPONSE_URL_MISMATCH','SEC_RESPONSE_INVALID','SEC_CLOCK_INVALID','SEC_SLEEP_FAILED','SEC_ISSUER_NOT_ALLOWED','SEC_URL_NOT_ALLOWED'}
            if type(code) is not str or code not in allowed and re.fullmatch(r'SEC_HTTP_[45][0-9]{2}',code) is None:code='SEC_TRANSPORT_FAILED'
            failures.append((index,code));continue
        try:on_success(issuer,facts,sub,acquired)
        except Exception:
            failures.append((index,'SEC_OUTPUT_FAILED'));continue
        collected+=1
    return UniverseBatchResult(collected,len(failures),tuple(failures))
