#!/usr/bin/env python3
"""Main screen-test variants of Codex's policy-impact synthetic job (4.5 정책·지정학, owner 2026-11-07; Codex #509 e0bb68dd).

Every variant is the OUTPUT of Codex's own engine (investment_system.research.policy_impact.build) on an input made from
docs/research/policy_impact/synthetic-job.json; Main never writes a policy-impact-view/1 by hand and never selects revisions,
availability or review states itself. The variants give the screen what the shared synthetic view lacks:
  REVISED     p0 gets revision 2 (its exposure and hypothesis on revision 1 become REVIEW_REQUIRED) and a separately reviewed
              unit 'unit-exception' (parent p0, SUSPENDED); public build, query after both reviews.
  HISTORICAL  the real-case shape in synthetic form: lifecycle UNKNOWN for all three, the bundle reason
              HISTORICAL_CASES_CURRENT_STATE_UNVERIFIED, tariff and export control WITHOUT any company exposure or hypothesis,
              the subsidy at FINAL_AWARD with a project exposure whose ratio is null for its reasons; public build.
  NEWS        a #483-style news reference (Codex from_news_reference, so SOURCE_UNVERIFIED, first seen != published) cited by
              h0; a PRIVATE (public=False) build, because Codex's public projection drops unverified sources. Screen tests only.
Run: PYTHONPATH=implementation/src python implementation/tools/policy_impact_main_variants.py [--check]
writes (or with --check compares) implementation/tests/fixtures/policy_impact_view_main_variants.json."""
import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.research.policy_impact import build  # noqa: E402
from investment_system.research.policy_impact.build import from_news_reference  # noqa: E402

JOB = ROOT / 'docs/research/policy_impact/synthetic-job.json'
OUT = ROOT / 'tests/fixtures/policy_impact_view_main_variants.json'
NEWS_LINK = 'https://wire.example.org/nvda-revenue'  # the first item of tools/web_app_news_fixture.js news()


def job():
    return json.loads(JOB.read_text())


def revise(b, pid='p0', at='2026-11-07T01:00:00Z'):
    """Codex test_policy_impact.revise(): an appended revision with its relation evidence and its own review record."""
    p = copy.deepcopy(next(x for x in b['policies'] if x['policy_id'] == pid))
    p.update(revision_id='2', supersedes_revision_id='1', change_recorded_at=at, recorded_at=at, reviewed_at=at,
             scope_description='적용 제품 목록 개정 · 예외 범위 미확인', lifecycle_status='EFFECTIVE')
    p['identity_basis']['relation_evidence_refs'] = copy.deepcopy(p['evidence_refs'])
    b['policies'].append(p)
    r = copy.deepcopy(next(x for x in b['review_records'] if x['group'] == 'policies' and x['id'] == pid))
    r.update(revision_id='2', reviewed_at=at, recorded_at=at)
    b['review_records'].append(r)
    return p


def revised():
    j = job(); b = j['bundle']
    revise(b)
    unit = copy.deepcopy(next(x for x in b['policies'] if x['policy_id'] == 'p0' and x['revision_id'] == '1'))
    at = '2026-11-07T01:30:00Z'
    unit.update(policy_id='unit-exception', title='합성 TARIFF 적용 단위 예외', parent_policy_id='p0', lifecycle_status='SUSPENDED',
                scope_description='일부 품목 유예 · 다른 품목은 상위 정책 그대로', change_recorded_at=at, recorded_at=at, reviewed_at=at)
    b['policies'].append(unit)
    r = copy.deepcopy(next(x for x in b['review_records'] if x['group'] == 'policies' and x['id'] == 'p0'))
    r.update(id='unit-exception', revision_id='1', reviewed_at=at, recorded_at=at)
    b['review_records'].append(r)
    return build(b, j['company_ids'], '2026-11-07T02:00:00Z', public=True)


def historical():
    j = job(); b = j['bundle']
    b['reason_codes'] = ['HISTORICAL_CASES_CURRENT_STATE_UNVERIFIED', 'LEGAL_PDF_NOT_CHECKED', 'NOT_MARKET_COVERAGE']
    b['freshness']['reason_codes'] = ['CURRENT_POLICY_STATUS_UNCONFIRMED']
    for p in b['policies']:
        p['lifecycle_status'] = 'UNKNOWN'; p['next_review_on'] = None
        if p['policy_type'] == 'INDUSTRIAL_SUBSIDY': p['subsidy_stage'] = 'FINAL_AWARD'
    keep = {p['policy_id'] for p in b['policies'] if p['policy_type'] == 'INDUSTRIAL_SUBSIDY'}
    b['exposures'] = [e for e in b['exposures'] if e['policy_id'] in keep]
    b['hypotheses'] = [h for h in b['hypotheses'] if h['policy_id'] in keep]
    for e in b['exposures']:
        e.update(exposure_type='SUBSIDY_PROJECT', policy_applicability='DOCUMENTED', ratio=None,
                 reason_codes=['RATIO_NOT_APPLICABLE', 'CURRENT_DISBURSEMENT_UNCONFIRMED'],
                 description='합성 발표가 이 프로젝트를 직접 명시 · 지급 완료와 현재 상태는 미확인')
    ids = {('exposures', e['exposure_id']) for e in b['exposures']} | {('hypotheses', h['hypothesis_id']) for h in b['hypotheses']}
    b['review_records'] = [r for r in b['review_records'] if r['group'] == 'policies' or (r['group'], r['id']) in ids]
    return build(b, j['company_ids'], j['as_of'], public=True)


def news():
    j = job(); b = j['bundle']
    base = copy.deepcopy(b['sources'][0]); base.update(source_id='news-0', source_revision_id='1', publisher='SYN-WIRE', document_id=None)
    s = from_news_reference({'link': NEWS_LINK, 'title': '합성 뉴스 참조', 'source_seen_at': '2026-11-06T12:00:00Z'}, base)
    b['sources'].append(s)
    h = next(x for x in b['hypotheses'] if x['hypothesis_id'] == 'h0')
    h['steps'][0]['evidence_refs'] = [{'source_id': 'news-0', 'source_revision_id': '1', 'locator': 'headline', 'claim': '합성 뉴스가 이 정책을 언급'}]
    return build(b, j['company_ids'], j['as_of'], public=False)


def variants():
    return {'schema_version': 'policy-impact-main-variants/1', 'made_by': 'investment_system.research.policy_impact.build',
            'from': 'implementation/docs/research/policy_impact/synthetic-job.json',
            'variants': {'REVISED': revised(), 'HISTORICAL': historical(), 'NEWS': news()}}


def text(v):
    return json.dumps(v, ensure_ascii=False, allow_nan=False, indent=1, sort_keys=True) + '\n'


def main():
    a = argparse.ArgumentParser(); a.add_argument('--check', action='store_true'); ns = a.parse_args()
    want = text(variants())
    if ns.check:
        same = OUT.exists() and OUT.read_text() == want
        print(json.dumps({'status': 'SAME' if same else 'DIFFERENT'})); return 0 if same else 1
    OUT.write_text(want); print(json.dumps({'status': 'WRITTEN', 'variants': 3})); return 0


if __name__ == '__main__':
    raise SystemExit(main())
