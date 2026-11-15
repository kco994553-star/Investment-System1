#!/usr/bin/env python3
"""Offline saved-KIS-result projection into a NEW private directory; no collection."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.research.private_kis_preprocess import project_technical
from investment_system.research._private_artifacts import MAX_BYTES


def _inside_git(path):
    return any((parent/'.git').exists() for parent in (path,*path.parents))


def write_new_directory(path,files):
    """Exclusive output. A completion manifest is written last; no previous copy touched."""
    path=Path(path).resolve()
    if path.exists():raise FileExistsError('PRESERVE_EXISTING_PRIVATE_OUTPUT')
    if _inside_git(path):raise ValueError('OUTPUT_MUST_BE_OUTSIDE_GIT')
    for name,raw in files.items():
        relative=Path(name)
        if relative.is_absolute() or any(p in ('','..','.') for p in relative.parts):raise ValueError('INVALID_ARTIFACT_PATH')
        if not isinstance(raw,bytes) or len(raw)>MAX_BYTES:raise ValueError('PRIVATE_ARTIFACT_TOO_LARGE')
    # Parent must already be a caller-chosen private location.
    path.mkdir(mode=0o700)
    for name in sorted(files,key=lambda p:(p.startswith('manifests/'),p)):
        target=path/name
        parent=path
        for part in Path(name).parts[:-1]:
            parent=parent/part
            parent.mkdir(mode=0o700,exist_ok=True)
        with os.fdopen(os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as stream:
            stream.write(files[name])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',action='store_true',help='Owner-private unverified reference display; no adoption upgrade')
    parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--handoff',type=Path,required=True)
    parser.add_argument('--expected-contract-hash',required=True)
    parser.add_argument('--expected-handoff-hash',required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args(argv);out=args.output_dir.resolve()
    if _inside_git(out):parser.error('OUTPUT_MUST_BE_OUTSIDE_GIT')
    try:
        c=json.loads(args.contract.read_bytes());h=json.loads(args.handoff.read_bytes())
        files=project_technical(c,h,expected_contract_hash=args.expected_contract_hash,
            expected_handoff_hash=args.expected_handoff_hash)
        if args.reference:
            from investment_system.research.private_kis_reference import reference_files
            files=reference_files(files,c,h['context']['signal_day'])
        write_new_directory(out,files)
    except Exception as error:
        # Only fixed upper-case contract codes may cross this diagnostic boundary.
        # JSON/OS/parser details and arbitrary source values remain private.
        reason=str(error) if isinstance(error,ValueError) and re.fullmatch(r'[A-Z0-9_]+',str(error)) else 'INVALID_PRIVATE_INPUT'
        print('OFFLINE_PRIVATE_PROJECTION_FAILED '+reason,file=sys.stderr);return 1
    print('OFFLINE_PRIVATE_PROJECTION_WRITTEN');return 0


if __name__=='__main__':raise SystemExit(main())
