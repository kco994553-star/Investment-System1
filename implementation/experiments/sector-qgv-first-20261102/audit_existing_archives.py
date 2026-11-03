"""Offline audit of existing private archives; no collection or score-population substitution.

Inputs are the already preserved C21 raw-store ZIP and #432 AMD daily-bar ZIP,
each with its original .sha256 sidecar. Output must be outside a git checkout.
Company evidence and financial values are written only to that private output.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import html
import json
from pathlib import Path
import re
import zipfile

from investment_system.research.exp_deciles import pit, schedule

S = '2018-02-16'
FIXED_CIKS = (1800, 2098, 2178, 2186, 2488, 3197, 3453, 3499, 3570, 4187)
MAPPING_VERSION = 'book10-sic-observed-evidence-v1-20261102'
# Research correspondences only, based on the already read chapter 24 descriptions.
# Neither code supplies a source classification effective-start date.
MAPPING = {
    '7372': ('INFORMATION_TECHNOLOGY', 'SEC description: prepackaged software; book IT products/services'),
    '4841': ('CONSUMER_DISCRETIONARY', 'SEC description: cable/pay television; book discretionary media'),
}
EVENTS = {
    '0001080099': {
        'artifact': 'sec_filing_doc:0001080099:0001013594-15-000453',
        'date': '2015-08-06',
        'markers': ['On August 6, 2015', 'the Issuer became wholly-owned by Newco'],
        'status': 'PRE_SIGNAL_MERGER_OLD_SECURITY_NOT_USABLE',
    },
    '0001507934': {
        'artifact': 'sec_filing_doc:0001507934:0001571049-16-020510',
        'date': '2016-12-08',
        'markers': ['On December 8, 2016', 'all Shares beneficially owned by the reporting persons were cancelled'],
        'status': 'PRE_SIGNAL_MERGER_OLD_SECURITY_NOT_USABLE',
    },
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def archive(path):
    expected = path.with_name(path.name + '.sha256').read_text().split()[0]
    if digest(path.read_bytes()) != expected:
        raise ValueError('ARCHIVE_HASH_MISMATCH')
    return zipfile.ZipFile(path)


def artifact(z, prefix, aid):
    stem = aid.replace(':', '__')
    body = z.read(prefix + '/blobs/' + stem)
    manifest = json.loads(z.read(prefix + '/manifests/' + stem + '.json'))
    if manifest['artifact_id'] != aid or digest(body) != manifest['sha256']:
        raise ValueError('SOURCE_HASH_MISMATCH')
    return body, manifest


def plain(body):
    return ' '.join(html.unescape(re.sub('<[^>]+>', ' ', body.decode())).split())


def write(out, name, obj):
    p = out / name
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str) + '\n')
    p.chmod(0o600)


def run(raw, amd, out):
    out = out.resolve()
    if out.exists() or any((p / '.git').exists() for p in (out, *out.parents)):
        raise ValueError('NEW_PRIVATE_OUTPUT_OUTSIDE_GIT_REQUIRED')
    out.mkdir(parents=True, mode=0o700)
    out.chmod(0o700)
    headers, originals, facts, pilot = [], [], {}, []
    cutoff = schedule.compute_cutoff(S).isoformat()
    with archive(raw) as z:
        names = set(z.namelist())
        for name in sorted(names):
            if not name.startswith('data/raw/manifests/') or not name.endswith('.json'):
                continue
            meta = json.loads(z.read(name))
            aid = meta['artifact_id']
            match = re.search(r'\d{10}-(\d{2})-\d{6}', aid)
            if meta['source_kind'] not in ('SEC_INDEX_HEADERS', 'SEC_FILING_DOCUMENT', 'SEC_FILING_INDEX', 'SEC_XBRL_INSTANCE'):
                continue
            if not match or int(match[1]) > 18:
                continue
            body, meta = artifact(z, 'data/raw', aid)
            originals.append(meta)
            text = html.unescape(body.decode()).replace('\r', '')
            filed = re.search(r'FILED AS OF DATE:\s*(\d{8})', text)
            if not filed:
                continue
            filed_day = date.fromisoformat(filed[1]).isoformat()
            if filed_day > cutoff:
                continue
            accepted = re.search(r'<ACCEPTANCE-DATETIME>(\d{14})', text)
            blocks = re.findall(
                r'(?:^|\n)SUBJECT COMPANY:\s*(.*?)(?=\n(?:SUBJECT COMPANY|FILED BY|REPORTING-OWNER|FILER|ISSUER):|'
                r'\n</SEC-HEADER>|\n<DOCUMENT>|\Z)', text, re.S)
            for block in blocks:
                cik = re.search(r'CENTRAL INDEX KEY:\s*(\d+)', block)
                sic = re.search(r'STANDARD INDUSTRIAL CLASSIFICATION:\s*([^\n]+)\[(\d{4})\]', block)
                if not cik or not sic:
                    continue
                code = sic[2]
                mapped = MAPPING.get(code)
                headers.append(dict(
                    fixed_issuer_id='SEC-CIK:' + cik[1].zfill(10), cik=cik[1].zfill(10),
                    security_id=None, security_id_status='NOT_ESTABLISHED',
                    source_classification_system='SEC_SIC', source_code=code,
                    source_description=sic[1].strip(), source_filing=aid.split(':')[-1],
                    source_url=meta['source_url'], source_sha256=meta['sha256'],
                    filed=filed_day, accepted_ny_raw=accepted[1] if accepted else None,
                    usable_from=schedule.usable_from(filed_day).isoformat(),
                    classification_effective_start=None, effective_start_status='UNKNOWN_NOT_IN_SOURCE',
                    book_sector=mapped[0] if mapped else None,
                    mapping_basis=mapped[1] if mapped else None,
                    mapping_version=MAPPING_VERSION if mapped else None,
                    mapping_status='RESEARCH_CORRESPONDENCE' if mapped else 'OUTSIDE_TWO_CANDIDATES',
                    observation_scope='SIC_OBSERVED_AT_FILING_NOT_PROOF_OF_UNCHANGED_CLASSIFICATION_THROUGH_S'))
        # Construct the two latest observed correspondences, then keep the actual old-security evidence.
        candidate_evidence = []
        for cik, event in EVENTS.items():
            rows = [r for r in headers if r['cik'] == cik and r['book_sector']]
            row = dict(max(rows, key=lambda r: (r['filed'], r['source_filing'])))
            body, meta = artifact(z, 'data/raw', event['artifact'])
            if not all(marker in plain(body) for marker in event['markers']):
                raise ValueError('REVIEWED_EVENT_TEXT_MISMATCH')
            row['signal_day_status'] = event['status']
            row['event'] = dict(date=event['date'], source_url=meta['source_url'], sha256=meta['sha256'])
            candidate_evidence.append(row)
        for cik in FIXED_CIKS:
            key = f'{cik:010d}'
            if any(r['cik'] == key for r in headers):
                raise ValueError('NEW_PILOT_CLASSIFICATION_REQUIRES_REVIEW')
            item = dict(cik=key, fixed_issuer_id='SEC-CIK:' + key, security_id=None,
                        as_filed_sic_status='NO_PRE_SIGNAL_SOURCE_IN_INSPECTED_ARCHIVE')
            aid = 'companyfacts:' + key
            if 'data/raw/blobs/' + aid.replace(':', '__') not in names:
                item['financial_status'] = 'ABSENT_FROM_INSPECTED_ARCHIVE'
            else:
                body, meta = artifact(z, 'data/raw', aid)
                row = pit.compute_row(json.loads(body), sic_record=None, signal_day=S, cik=key, security_id=None)
                facts[key] = dict(source=meta, row=row)
                item['financial_status'] = row['state']
                item['latest_filing_used'] = row['pit']['latest_filing_used']
            pilot.append(item)
    with archive(amd) as z:
        aid = 'sip:AMD:2018-01-01:2018-12-31:0:0'
        body, meta = artifact(z, 'store', aid)
        payload = json.loads(body)
        # An availability check only; no quote/identity eligibility is inferred.
        bars = [b for b in payload['bars'] if b['t'][:10] == S]
        if payload.get('symbol') != 'AMD' or len(bars) != 1:
            raise ValueError('SIGNAL_BAR_NOT_UNIQUE')
        price = dict(source=meta, bars=bars, status='STORED_SIGNAL_BAR_PRESENT_IDENTITY_AND_BASIS_NOT_VALIDATED')
    summary = dict(schema='sector-qgv-existing-input-audit/1', signal_day=S, cutoff=cutoff,
                   pilot_issuers=len(pilot), historical_originals_verified=len(originals),
                   historical_kinds=dict(Counter(r['source_kind'] for r in originals)),
                   as_filed_sic_observations=len(headers), reconstructed_candidate_issuers=len(candidate_evidence),
                   reconstructed_candidates_usable_at_signal=0, pit_financial_rows_computed=len(facts),
                   actual_qgv_scores_computed=0, comparison_rows=0,
                   first_blocker='PILOT_AS_OF_CLASSIFICATION_OR_USABLE_CANDIDATE_NOT_AVAILABLE',
                   later_blocker='APPROVED_C2_SCORING_POPULATION_NOT_RECOVERED',
                   score_engine_invoked=False, small_sample_substitution=False)
    write(out, 'historical-source-inventory.json', originals)
    write(out, 'classification-observations.json', headers)
    write(out, 'candidate-classification-evidence.json', candidate_evidence)
    write(out, 'pilot-input-status.json', pilot)
    write(out, 'pit-financial-rows.json', facts)
    write(out, 'stored-signal-price.json', price)
    write(out, 'summary.json', summary)
    write(out, 'manifest.json', dict(
        inputs={str(raw): digest(raw.read_bytes()), str(amd): digest(amd.read_bytes())},
        outputs={p.name: digest(p.read_bytes()) for p in sorted(out.glob('*.json'))}))
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-zip', type=Path, required=True)
    parser.add_argument('--amd-zip', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.raw_zip, args.amd_zip, args.out)
