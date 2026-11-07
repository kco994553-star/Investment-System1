"""Offline one-company readiness row from already connected evidence; no archive search or collection."""
import argparse
import csv
import json
from pathlib import Path

from audit_existing_archives import digest, write
from investment_system.qgv.qgv2_inputs import normalize
from investment_system.research.exp_deciles import schedule

S = '2018-02-16'


def run(root, repo, out):
    out = out.resolve()
    if out.exists() or any((p / '.git').exists() for p in (out, *out.parents)):
        raise ValueError('NEW_PRIVATE_OUTPUT_REQUIRED')
    connected = root / 'sec-connected-v1'
    manifest = json.loads((connected / 'manifest.json').read_text())
    for name, expected in manifest['outputs'].items():
        if Path(name).name != name or digest((connected / name).read_bytes()) != expected:
            raise ValueError('CONNECTED_OUTPUT_HASH_MISMATCH')
    financial = json.loads((connected / 'pit-row-with-asfiled-sic.json').read_text())
    classification = json.loads((connected / 'classification-security-shares.json').read_text())
    price = json.loads((connected / 'price-basis-audit.json').read_text())
    facts_path = root / 'financial-originals/companyfacts__0000002488'
    if digest(facts_path.read_bytes()) != financial['source']['sha256']:
        raise ValueError('COMPANYFACTS_HASH_MISMATCH')
    cutoff = schedule.compute_cutoff(S).isoformat()
    facts = json.loads(facts_path.read_text())
    observations = facts['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares']
    eligible = [r for r in observations if r.get('filed', '9999') <= cutoff and r['end'] <= S]
    latest = max(eligible, key=lambda r: (r['end'], r['filed']))
    shares = classification['cover_shares']
    if latest['val'] != shares['value'] or latest['end'] != shares['period_end']:
        raise ValueError('LATEST_HELD_OBSERVATION_CHANGED')
    normalized = normalize(financial['row'], False)
    if shares['value'] == normalized['v_inputs']['diluted_shares']:
        raise ValueError('REVIEW_OUTSTANDING_AND_DILUTED_SHARES')
    report = root / 'pr432-code/implementation/experiments/bt-data-pilot-v06/ALPACA_ACTUAL_RESULT_20261031.md'
    if '통화 USD는 미국 주식 endpoint의 범위 근거이며 응답 자체에는 통화 필드가 없다.' not in report.read_text():
        raise ValueError('PRIOR_CURRENCY_REPORT_CHANGED')
    provider_review = repo / 'implementation/experiments/chart-contract-v0.1/reviews/api_provider_review.md'
    sector = dict(source_system='SEC_SIC', observed_code='3674',
                  observations=classification['observations'],
                  selected_observation=classification['selected_observation'],
                  book_sector='INFORMATION_TECHNOLOGY', mapping_status='RESEARCH_CORRESPONDENCE',
                  mapping_version='book10-sic-observed-evidence-v2-20261102',
                  mapping_application_signal_day=S, mapping_recorded_on='2026-11-03',
                  classification_effective_start=None,
                  basis='Retained chapter 24 description: IT creation/sale; examples Intel, Lattice Semiconductor, QUALCOMM. SIC 3674: semiconductors and related devices.',
                  limitation='No official SIC-to-book crosswalk or historical classification start date in source')
    share_review = dict(status='LATEST_USABLE_OBSERVATION_IN_HELD_INPUTS',
                        cutoff=cutoff, eligible_dei_observations=len(eligible), selected=latest,
                        cover_source=shares, diluted_share_substitution=False,
                        scope='Held companyfacts plus already reviewed SEC cover and filing metadata; no new filing requests',
                        later_8k='2018-01-30 exhibit has EPS weighted-average shares, not a new point-in-time outstanding count',
                        unusable_20180212_8k_usable_from=schedule.usable_from('2018-02-12').isoformat(),
                        split_factor_to_signal=None, split_review='확인 범위에서 발견되지 않음; 무분할 확정 아님')
    row = dict(signal_day=S, issuer_cik='0000002488', provider_symbol='AMD',
               book_sector='INFORMATION_TECHNOLOGY', sic='3674',
               price_close=price['bars'][0]['c'], price_currency=None,
               price_currency_prior_declaration='USD',
               price_currency_evidence='PRIOR_PILOT_ENDPOINT_SCOPE_REPORT; PRIMARY_PROVIDER_SPEC_NOT_RESTORED',
               price_adjustment_requested='raw', shares_outstanding=shares['value'],
               shares_as_of=shares['period_end'], shares_filed=shares['filed'], shares_usable_from=shares['usable_from'],
               share_price_split_factor=None, market_cap=None, ev=None,
               financial_currency=normalized['v_inputs']['currency'],
               debt=normalized['v_inputs']['total_debt'], cash=normalized['v_inputs']['cash'],
               balance_period=normalized['periods']['total_debt'], revenue=normalized['v_inputs']['revenue'],
               revenue_accounting_period=normalized['periods']['revenue'],
               financial_basis='EXISTING_CALC_23_1_PIT_INPUT_NOT_A_CLAIM_OF_LATEST_8K_NUMBERS',
               ev_sales=None, raw_ratio_status='NOT_COMPUTED',
               reasons='PRICE_CURRENCY_SOURCE_UNCONFIRMED;HISTORICAL_PROVIDER_SECURITY_BINDING_UNCONFIRMED;SHARE_PRICE_BASIS_UNCONFIRMED',
               last_confirmed_stage='AS_FILED_SIC_RESEARCH_MAPPING_AND_LATEST_HELD_POINT_SHARES',
               c2_required_for_raw_ratio=False, c2_score_status='SEPARATELY_BLOCKED_C2_GENERATION_UNCONFIRMED')
    out.mkdir(parents=True, mode=0o700)
    out.chmod(0o700)
    write(out, 'sector-mapping-and-timing.json', sector)
    write(out, 'latest-usable-shares.json', share_review)
    write(out, 'ev-sales-readiness-row.json', row)
    with (out / 'ev-sales-readiness-row.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    (out / 'ev-sales-readiness-row.csv').chmod(0o600)
    write(out, 'manifest.json', dict(
        input_hashes={str(p): digest(p.read_bytes()) for p in
                      (connected / 'manifest.json', facts_path, report, provider_review)},
        output_hashes={p.name: digest(p.read_bytes()) for p in sorted(out.iterdir())},
        new_sec_requests=0, new_provider_requests=0, repeated_archive_searches=0,
        input_rows=1, computed_raw_ratios=0, computed_scores=0))
    print(json.dumps(dict(input_rows=1, raw_ratios=0, latest_share_date=latest['end'],
                          mapping_signal_day=S, new_external_requests=0)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('root', 'repo', 'out'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    run(args.root, args.repo, args.out)
