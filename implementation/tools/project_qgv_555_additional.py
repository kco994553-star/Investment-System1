#!/usr/bin/env python3
"""Project extra factor views from pinned saved inputs; preserve all core scores."""
import argparse,json
from pathlib import Path
from investment_system.research.qgv_555_additional import attach
from investment_system.research.qgv_555_delivery import artifacts,validate
from investment_system.research.sector_qgv_held import checked_bytes
from investment_system.research.dual_qgv import json_bytes
import hashlib


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--job',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('PRESERVE_SOURCE_OUTPUT')
    j=json.loads(a.job.read_bytes());e=json.loads(checked_bytes(j['evaluation']));r=json.loads(checked_bytes(j['reference']))
    boards={k:attach(json.loads(checked_bytes(v)),e,r) for k,v in j['results'].items()}
    files=artifacts(boards,data_kind=j['data_kind']);pin=hashlib.sha256(json_bytes(files['manifest.json'])).hexdigest()
    check=validate(files,manifest_sha256=pin,expected_evaluation=next(iter(boards.values()))['evaluation'],expected_references={k:v['reference'] for k,v in boards.items()})
    a.output.mkdir(parents=True)
    for name,value in files.items():(a.output/name).write_bytes(json_bytes(value))
    (a.output/'projection-verification.json').write_bytes(json_bytes(dict(check,core_scores_recomputed=False)))


if __name__=='__main__':main()
