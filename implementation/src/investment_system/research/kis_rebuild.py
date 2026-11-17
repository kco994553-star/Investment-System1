"""Keyless, network-free rebuilding of owner-private KIS delivery.

This entry point reuses canonical kernels; no collection or new calculation
formula. Service bytes depend on pinned inputs and a caller-supplied clock only.
"""
import argparse
from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import tarfile
import re

from ._private_artifacts import digest, json_bytes, MAX_BYTES
from .kis_price_bridge import _day, _ts, price_rows, validate_contract
from .monthly_price_store import load_manifest, retained_contract, retained_metadata
from .private_kis_preprocess import calculate_and_project
from .private_kis_reference import reference_files, official_reference


def sha(b):
    return hashlib.sha256(b).hexdigest()


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def child(root, name):
    need(isinstance(name, str) and name and not Path(name).is_absolute(), 'RELATIVE_PATH_REQUIRED')
    p=(Path(root)/name).resolve();r=Path(root).resolve()
    need(p.is_relative_to(r) and p!=r, 'INPUT_PATH_ESCAPE')
    return p


def pinned(root, entry):
    b=child(root,entry['path']).read_bytes()
    need(sha(b)==entry['sha256'], 'INPUT_FILE_PIN_MISMATCH')
    return json.loads(b)


class Inputs(Mapping):
    """Load one series at a time; do not retain five years for all issuers in RAM."""
    def __init__(self, root, config):
        self.root=root;self.config=config
        index=pinned(root,config['series_index'])
        self.entries={}
        for row in index['files']:
            code=row['code']
            need(code not in self.entries, 'DUPLICATE_COMPANY_ROW')
            self.entries[code]=row
        need(bool(self.entries), 'EMPTY_SERIES_INDEX')
        need(len({r['series_id'] for r in self.entries.values()})==len(self.entries), 'DUPLICATE_PROVIDER_SERIES')
        store=config['store'];self.archive=None;self.last=None
        if isinstance(store,str):self.store=child(root,store)
        else:
            p=child(root,store['archive']);b=p.read_bytes()
            need(sha(b)==store['sha256'],'STORE_ARCHIVE_PIN')
            prefix=store.get('prefix','store').rstrip('/')+'/'
            self.archive={}
            with tarfile.open(p) as t:
                for m in t:
                    if m.isfile() and m.name.startswith(prefix):
                        name=m.name[len(prefix):]
                        need(name not in self.archive,'DUPLICATE_ARCHIVE_MEMBER')
                        self.archive[name]=t.extractfile(m).read()
            self.store=None

    def __iter__(self):
        return iter(sorted(self.entries))

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, code):
        if self.last and self.last[0]==code:return self.last[1]
        entry=self.entries[code]
        if self.archive is None:c=self._from_store(self.store,entry)
        else:
            with tempfile.TemporaryDirectory(prefix='kis-retained-series-') as td:
                prefix='series/'+entry['series_id']+'/'
                for name,b in self.archive.items():
                    if name.startswith(prefix):
                        p=child(td,name);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
                c=self._from_store(Path(td),entry)
        self.last=(code,c)
        return c

    def _from_store(self, store, entry):
        m=load_manifest(store,entry['series_id'])
        need(m['manifest_sha256']==entry['store_manifest_sha256'], 'SOURCE_POINTER_DRIFT')
        c=retained_contract(store,m)
        need(c['symbol']==entry['symbol'], 'INDEX_SYMBOL_MISMATCH')
        # Original pretty-printed input bytes are not reconstructed by the journal.
        # Verify their recorded byte pin against the independent source index;
        # current reconstructed values are verified by the month/receipt hashes.
        if entry.get('source_contract_sha256'):
            need(retained_metadata(store,m)['input_contract_sha256']==entry['source_contract_sha256'],
                 'RETAINED_CONTRACT_FILE_PIN')
        need(_ts(c['collected_at'])<=_ts(self.config['calculated_at']), 'SOURCE_AFTER_CALCULATION')
        if self.config.get('price_basis','RAW')=='SPLIT_ADJUSTED':
            c['basis']='SPLIT_ADJUSTED'
            c['bars']=price_rows(c,c['price_basis_date'])
            validate_contract(c)
        return c


class ContractPins(Mapping):
    def __init__(self, contracts):self.contracts=contracts
    def __iter__(self):return iter(self.contracts)
    def __len__(self):return len(self.contracts)
    def __getitem__(self, key):return digest(self.contracts[key])


def load_request(path, expected):
    path=Path(path).resolve();b=path.read_bytes()
    need(sha(b)==expected, 'REQUEST_PIN_MISMATCH')
    cfg=json.loads(b)
    need(cfg.get('schema')=='kis-offline-rebuild/1' and
         cfg.get('publication_scope')=='OWNER_PRIVATE_ONLY', 'PRIVATE_REBUILD_REQUEST_REQUIRED')
    _day(cfg['evaluation_day']);_ts(cfg['calculated_at'])
    need(cfg['evaluation_day']<=_ts(cfg['calculated_at']).date().isoformat(), 'FUTURE_EVALUATION')
    need(cfg.get('price_basis','RAW') in ('RAW','SPLIT_ADJUSTED'), 'PRICE_BASIS_UNSUPPORTED')
    need(isinstance(cfg.get('series_id_prefix'),str) and bool(cfg['series_id_prefix']), 'SERIES_CONTEXT_REQUIRED')
    contracts=Inputs(path.parent,cfg)
    return path.parent,cfg,contracts


def rebuild(request, *, expected_request_sha256):
    """Yield the unchanged legacy chart/technical/measures/manifests/QGV files."""
    root,cfg,contracts=load_request(request,expected_request_sha256)
    for code in contracts:
        c=contracts[code]
        files=calculate_and_project(c,evaluation_day=cfg['evaluation_day'],
              series_id=cfg['series_id_prefix']+code,expected_contract_hash=digest(c))
        for path,b in sorted(reference_files(files,c,cfg['evaluation_day']).items()):
            yield path,b
    financial=pinned(root,cfg['financial']);symbols=pinned(root,cfg['symbols'])
    months=pinned(root,cfg['monthends']) if cfg.get('monthends') else {}
    q=official_reference(financial,contracts,symbols,day=cfg['evaluation_day'],
        calculated_at=cfg['calculated_at'],expected_payload_hash=digest(financial),
        expected_links_hash=digest(symbols),expected_contract_hashes=ContractPins(contracts),monthends=months)
    need(not any(r['total'] is not None and any(r['axes'][a]['score'] is None for a in ('Q','G','V'))
                 for r in q['rows'].values()), 'INCOMPLETE_TOTAL')
    b=json_bytes(q);need(len(b)<=MAX_BYTES,'QGV_FILE_LIMIT')
    yield 'qgv/latest.json',b


def compare_files(files, expected):
    need(len({x['path'] for x in expected})==len(expected), 'DUPLICATE_REFERENCE_PATH')
    wanted={x['path']:x for x in expected};seen=set();different=extra=0
    index=[]
    for name,b in files:
        need(name not in seen, 'DUPLICATE_OUTPUT_PATH');seen.add(name)
        row=dict(path=name,bytes=len(b),sha256=sha(b))
        index.append(row)
        if name not in wanted:extra+=1;continue
        ref=wanted[name]
        if 'git_blob_sha1' in ref:
            actual=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
            ok=actual==ref['git_blob_sha1']
        else:ok=row['sha256']==ref['sha256']
        if not ok or len(b)!=ref['bytes']:different+=1
    return dict(files=len(seen),matched=len(seen)-different-extra,different=different,
                missing=len(set(wanted)-seen),extra=extra,index=index)


def write_bundle(files, output):
    """Stage a complete new directory; never overwrite a good/previous output."""
    output=Path(output).resolve()
    if output.exists():raise FileExistsError('OUTPUT_ALREADY_EXISTS')
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.kis-rebuild-',dir=output.parent))
    count=total=0;seen=set()
    try:
        for path,b in files:
            need(path not in seen,'DUPLICATE_OUTPUT_PATH');seen.add(path)
            need(len(b)<=MAX_BYTES,'OUTPUT_FILE_LIMIT')
            p=child(stage,path);p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as f:f.write(b)
            need(p.read_bytes()==b,'OUTPUT_READBACK_MISMATCH')
            count+=1;total+=len(b)
        os.rename(stage,output)
    finally:
        # Only this run's unpublished scratch directory; never previous artifacts.
        if stage.exists():shutil.rmtree(stage)
    return dict(files=count,bytes=total)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--expected-request-sha256',required=True)
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--reference-index',type=Path)
    parser.add_argument('--expected-reference-sha256')
    parser.add_argument('--run-receipt',type=Path)
    parser.add_argument('--layout',choices=('legacy','compact'),default='legacy')
    parser.add_argument('--recent',choices=('daily','monthly'),default='daily')
    parser.add_argument('--previous-manifest',type=Path)
    parser.add_argument('--expected-previous-sha256')
    parser.add_argument('--revision-reference')
    parser.add_argument('--bootstrap',action='store_true')
    args=parser.parse_args(argv)
    started=time.perf_counter();result={};receipt={};status=0
    try:
        need(args.check_only != bool(args.output_dir),'CHOOSE_OUTPUT_OR_CHECK_ONLY')
        need(bool(args.reference_index)==bool(args.expected_reference_sha256),'REFERENCE_PIN_REQUIRED')
        need(bool(args.previous_manifest)==bool(args.expected_previous_sha256),'PREVIOUS_PIN_REQUIRED')
        need(not(args.reference_index and args.output_dir),'REFERENCE_COMPARISON_CHECK_ONLY')
        need(not(args.reference_index and args.layout!='legacy'),'REFERENCE_REQUIRES_LEGACY')
        files=rebuild(args.request,expected_request_sha256=args.expected_request_sha256)
        if args.layout=='compact':
            from .kis_compact import compact,growth
            need(bool(args.previous_manifest) != args.bootstrap,'COMPACT_PREVIOUS_OR_EXPLICIT_BOOTSTRAP')
            previous=None
            if args.previous_manifest:
                b=args.previous_manifest.read_bytes();need(sha(b)==args.expected_previous_sha256,'PREVIOUS_MANIFEST_PIN')
                previous=json.loads(b)
            _,config,_=load_request(args.request,args.expected_request_sha256)
            projected=compact(files,evaluation_day=config['evaluation_day'],previous=previous,
                              revision_reference=args.revision_reference,recent=args.recent)
            receipt['growth']=growth(projected,previous=previous)
            receipt['growth_ledger']=json.loads(projected['manifest.json'])['growth_ledger']
            files=iter(sorted(projected.items()))
        if args.reference_index:
            b=args.reference_index.read_bytes();need(sha(b)==args.expected_reference_sha256,'REFERENCE_INDEX_PIN')
            reference=json.loads(b);result=compare_files(files,reference['files'])
            if result['missing'] or result['extra'] or result['different']:status=5
        if args.output_dir and status==0:
            p=args.output_dir.resolve()
            need(not any((d/'.git').exists() for d in (p,*p.parents)), 'PRIVATE_OUTPUT_OUTSIDE_GIT_REQUIRED')
            result.update(write_bundle(files,p))
        elif not args.reference_index:
            result=dict(files=0,bytes=0)
            for _,b in files:result['files']+=1;result['bytes']+=len(b)
    except ValueError as e:
        status=6 if str(e) in ('ANNUAL_DATA_BUDGET','DAILY_DATA_BUDGET','COMPACT_FILE_LIMIT','PACK_FILE_LIMIT','CHART_PIECE_LIMIT') else 2
        receipt['reason']=str(e) if re.fullmatch('[A-Z][A-Z0-9_]{1,63}',str(e)) else 'INPUT_OR_CALCULATION_INVALID'
    except OSError:
        status=4;receipt['reason']='IO_FAILURE'
    except Exception:
        status=3;receipt['reason']='CALCULATION_FAILED'
    receipt.update(exit_code=status,elapsed_seconds=time.perf_counter()-started,counts={k:v for k,v in result.items() if type(v) is int})
    if 'index' in result:receipt['files']=result['index']
    if args.run_receipt:
        try:
            with args.run_receipt.open('x') as f:json.dump(receipt,f,sort_keys=True);f.write('\n')
        except OSError:status=4
    print(json.dumps(dict(receipt['counts'],failures=int(status!=0)),sort_keys=True))
    return status


if __name__=='__main__':
    raise SystemExit(main())
