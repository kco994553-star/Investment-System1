#!/usr/bin/env python3
"""Python side of the sec-qgv2.json -> QGV v2 engine-input parity (JS side: tools/qgv2_inputs_parity.js).

convert(spec) runs qgv/qgv2_inputs.py (from_published or from_inputs(light(...)), page_identities, engine_inputs) and
qgv_v2.score_universe for every profile of the spec, returning the same shape as the JS convert(). Specs come from the JS
cases() builder; their quotes are SYNTHETIC test numbers. RAM only: nothing is written except the JSON on stdout.

CLI: qgv2_inputs_parity.py convert < specs.json   -> JSON array of outputs on stdout
"""
import copy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from investment_system.qgv import qgv2_inputs as qi  # noqa: E402
from investment_system.qgv import playbook, qgv_v2  # noqa: E402
from investment_system.qgv.dcf_parameters import load_default_dcf_parameters  # noqa: E402
from investment_system.qgv.type_config import load_official_type_config  # noqa: E402


def _config():
    return playbook.load_config(), load_official_type_config().to_dict(), load_default_dcf_parameters()


def _payload(spec):
    if spec.get('payload_file'):
        from investment_system.universe.sec_qgv2 import parse_json
        return parse_json(Path(spec['payload_file']).read_bytes())
    return copy.deepcopy(spec['payload'])


def inputs_of(spec):
    payload = _payload(spec)
    return qi.from_published(payload, spec['now']) if spec['source'] == 'strict' else qi.from_inputs(qi.light(payload))


def convert(spec, config=None):
    pb_cfg, type_cfg, params = config or _config()
    inputs = inputs_of(spec)
    identities = qi.page_identities(inputs, spec.get('identities') or [])
    companies, priced = qi.engine_inputs(inputs, spec.get('quotes'), identities=identities, playbook_cfg=pb_cfg, type_config=type_cfg)
    out = {'id': spec['id'], 'inputs': inputs, 'page_identities': identities, 'companies': companies,
           'engine_quote_codes': sorted(priced), 'scores': {}}
    for p in spec['profiles']:
        kwargs = {'gate': p['gate']}
        if p.get('weights'):
            kwargs.update(weights=p['weights'], type_weights=p['typeWeights'], weight_stages=True)
        else:
            kwargs['preset'] = p['preset']
        out['scores'][p['id']] = qgv_v2.score_universe(copy.deepcopy(companies), copy.deepcopy(priced), type_config=type_cfg,
                                                        parameters=params, **kwargs)
    return json.loads(json.dumps(out, allow_nan=False))


def main(argv):
    if argv[1:] != ['convert']:
        print('usage: qgv2_inputs_parity.py convert < specs.json', file=sys.stderr)
        return 2
    config = _config()
    sys.stdout.write(json.dumps([convert(s, config) for s in json.load(sys.stdin)], allow_nan=False))  # one write: fast over a pipe
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
