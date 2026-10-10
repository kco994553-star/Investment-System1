"""CLI for five price-free screen sidecars; workflow wiring belongs to Codex1."""
import argparse
from datetime import timedelta
import json
from pathlib import Path
import os
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.product.public_engine_screens import generate_screen_bundle,parse_json,clock

class Parser(argparse.ArgumentParser):
    def error(self,_):self.exit(2,'PUBLIC_SCREENS_ARGUMENTS_INVALID\n')

def main(argv=None):
    parser=Parser();parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--as-of',required=True);parser.add_argument('--stale-after-hours',type=float,required=True)
    args=parser.parse_args(argv)
    try:
        if args.manifest.stat().st_size>1024*1024:raise ValueError('INVALID')
        outputs=generate_screen_bundle(manifest=parse_json(args.manifest.read_bytes()),input_root=args.manifest.parent,as_of=clock(args.as_of),stale_after=timedelta(hours=args.stale_after_hours))
        prepared={name:json.dumps(payload,ensure_ascii=True,sort_keys=True,allow_nan=False).encode() for name,payload in outputs.items()}
        if any(len(b)>2*1024*1024 for b in prepared.values()):raise ValueError('INVALID')
        args.output_dir.mkdir(parents=True,exist_ok=True)
        for name,body in prepared.items():
            temp=None
            try:
                with tempfile.NamedTemporaryFile(dir=args.output_dir,delete=False) as f:temp=Path(f.name);f.write(body)
                os.replace(temp,args.output_dir/name)
            finally:
                if temp is not None:temp.unlink(missing_ok=True)
    except Exception:
        print('PUBLIC_SCREENS_INPUT_INVALID');return 1
    print('PUBLIC_SCREENS_OK files=5');return 0

if __name__=='__main__':raise SystemExit(main())
