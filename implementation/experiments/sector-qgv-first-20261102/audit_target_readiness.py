"""Offline follow-up for the reviewed accession; writes evidence only to a new private directory.

Reuses the prior verified financial rows and the shared V normalizer. It does not
collect data, infer historical security identity, compute ratios, or score a population.
Accession matches are an inventory for human review, not a header parser.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tarfile

from audit_existing_archives import archive, artifact, digest, write
from investment_system.qgv.qgv2_inputs import normalize

CIK = '0000002488'
ACCESSION = '0000002488-17-000227'
SIGNAL = '2018-02-16'


def run(raw, amd, sec, prior, out):
    out = out.resolve()
    if out.exists() or any((p / '.git').exists() for p in (out, *out.parents)):
        raise ValueError('NEW_PRIVATE_OUTPUT_OUTSIDE_GIT_REQUIRED')
    previous = json.loads((prior / 'manifest.json').read_text())
    for name, expected in previous['outputs'].items():
        if Path(name).name != name or digest((prior / name).read_bytes()) != expected:
            raise ValueError('PRIOR_OUTPUT_HASH_MISMATCH')
    out.mkdir(parents=True, mode=0o700)
    out.chmod(0o700)
    needles = (ACCESSION.encode(), ACCESSION.replace('-', '').encode())
    with archive(raw) as z:
        matches = []
        for name in z.namelist():
            body = z.read(name)
            if any(n in body or n in name.encode() for n in needles):
                matches.append(name)
        search = dict(zip_members_searched=len(z.namelist()), zip_matches=matches,
                      scope='ALL_ZIP_MEMBERS_INCLUDING_HISTORY')
        body, submissions_source = artifact(z, 'data/raw', 'submissions:' + CIK)
        submissions = json.loads(body)
        recent = submissions['filings']['recent']
        indices = [i for i, day in enumerate(recent['filingDate']) if '2017-11-02' <= day <= SIGNAL]
        recent_evidence = dict(
            source=submissions_source, recent_min_date=min(recent['filingDate']),
            history_files=submissions['filings']['files'],
            filings=[{k: recent[k][i] for k in ('accessionNumber', 'filingDate', 'form', 'primaryDocument', 'items')
                      if k in recent} for i in indices])
    if digest(sec.read_bytes()) != sec.with_name(sec.name + '.sha256').read_text().split()[0]:
        raise ValueError('SEC_ARCHIVE_HASH_MISMATCH')
    with tarfile.open(sec, 'r:gz') as t:
        members = t.getmembers()
        matches, issuer_files = [], []
        for member in members:
            if not member.isfile():
                continue
            body = t.extractfile(member).read()
            if '/' + CIK + '/' in member.name:
                issuer_files.append(member.name)
            if any(n in body or n in member.name.encode() for n in needles):
                matches.append(member.name)
        search.update(sec_members_searched=len(members), sec_matches=matches, sec_issuer_files=issuer_files)
    financial = json.loads((prior / 'pit-financial-rows.json').read_text())[CIK]
    row = financial['row']
    if row['pit']['signal_day'] != SIGNAL or row['security_id'] is not None or row['sic'] is not None:
        raise ValueError('CHANGED_EVIDENCE_REQUIRES_REVIEW')
    normalized = normalize(row, False)
    with archive(amd) as z:
        body, price_source = artifact(z, 'store', 'sip:AMD:2018-01-01:2018-12-31:0:0')
        prices = json.loads(body)
        bars = [b for b in prices['bars'] if b['t'][:10] == SIGNAL]
        if prices.get('symbol') != 'AMD' or len(bars) != 1:
            raise ValueError('SIGNAL_BAR_NOT_UNIQUE')
        request = json.loads(z.read('requests/sip_AMD_2018-01-01_2018-12-31_0_0.json'))['arguments']
    required = ('revenue', 'fcf', 'total_debt', 'cash', 'diluted_shares')
    readiness = dict(
        schema='sector-qgv-target-readiness/1', signal_day=SIGNAL, cik=CIK, accession=ACCESSION,
        fixed_issuer_id='SEC-CIK:' + CIK, security_id=None, as_filed_sic=None,
        classification_effective_start=None, classification_status='SOURCE_HEADER_OR_COVER_NOT_RECOVERED',
        financial_source=financial['source'], financial_pit=row['pit'], normalized_financial=normalized,
        fields_present={k: normalized['v_inputs'].get(k) is not None for k in required},
        price_source=price_source, price_bars=bars, price_request=request,
        same_security_join_status='UNCONFIRMED', share_price_basis_status='UNCONFIRMED',
        quote_currency_status='UNCONFIRMED', raw_ratio=None, raw_ratio_status='NOT_COMPUTED',
        blockers=['AS_FILED_CLASSIFICATION_SOURCE_MISSING', 'HISTORICAL_SECURITY_IDENTITY_UNCONFIRMED',
                  'SHARE_PRICE_BASIS_UNCONFIRMED', 'QUOTE_CURRENCY_UNCONFIRMED'],
        note='Numeric input co-presence is not a verified same-security join; no conditional ratio substituted.',
        stage_counts=dict(classification_confirmed=0, security_valid_at_signal=0,
                          price_financial_join=0, raw_ratio=0, baseline_candidate_comparison=0),
        separate_availability_counts=dict(target_issuers=1, financial_inputs=1, stored_signal_bar=1),
        score_engine_invoked=False)
    write(out, 'accession-backup-search.json', search)
    write(out, 'stored-submissions-coverage.json', recent_evidence)
    write(out, 'target-input-readiness.json', readiness)
    write(out, 'manifest.json', dict(
        inputs={str(p): digest(p.read_bytes()) for p in (raw, amd, sec, prior / 'manifest.json')},
        outputs={p.name: digest(p.read_bytes()) for p in sorted(out.glob('*.json'))}))
    print(json.dumps(dict(stage_counts=readiness['stage_counts'], fields_present=readiness['fields_present'],
                          zip_members_searched=search['zip_members_searched'],
                          sec_members_searched=search['sec_members_searched']), sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('raw', 'amd', 'sec', 'prior', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    run(args.raw, args.amd, args.sec, args.prior, args.out)
