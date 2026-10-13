"""Write tests/fixtures/dart_public_vectors_v1.json: synthetic `dart-disclosures.json` cases and title-rule vectors.

Python (tests/test_dart_collection.py) and JS (tools/dart_disclosures_node_test.js) must reach the same verdict on
every case. Synthetic data only (fake OpenDART transport, synthetic corp_code). Usage: python tools/dart_public_vectors.py [--check]
"""
import copy
from datetime import timedelta
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))
from investment_system.product import dart_public as dp  # noqa: E402
from investment_system.providers import dart_collection as dc  # noqa: E402
from tests.dart_fake_opendart import FAKE_KEY, NOW, FakeOpenDart  # noqa: E402

OUT = ROOT / 'tests/fixtures/dart_public_vectors_v1.json'
TITLES = ['사업보고서 (2025.12)', '[기재정정]사업보고서 (2025.12)', '[첨부정정][기재정정]반기보고서 (2026.06)',
          '연결재무제표기준영업(잠정)실적(공정공시)', '[기재정정]영업(잠정)실적(공정공시)', '영업(잠정) 실적(공정공시)',
          '기업설명회(IR)개최(안내공시)(공정공시)', '단일판매ㆍ공급계약체결', '[기재정정]단일판매ㆍ공급계약체결',
          '주요사항보고서(자기주식취득결정)', '임원ㆍ주요주주특정증권등소유상황보고서', '[발행조건확정]증권신고서(지분증권)',
          '잠정실적 공정공시 아님', '(잠정)실적', ' 앞 공백', '뒤 공백 ', '두  칸', '<b>태그</b>', '줄\n바꿈', 'NBSP\u00a0제목',
          'BOM\ufeff제목', '😀' * 200, '😀' * 201, '', '[' + '가' * 21 + ']제목', '[' + '가' * 20 + ']제목 (2026.03)']


def base():
    import importlib
    sys.path.insert(0, str(ROOT / 'tools'))
    dart_daily = importlib.import_module('dart_daily')
    client = dc.DartClient(FAKE_KEY, budget=dc.CallBudget(30), transport=FakeOpenDart())
    disclosures, events, _, _ = dart_daily.collect(client, now=NOW)
    return dp.disclosures_payload(as_of=NOW, companies=disclosures, events=events, api_calls=client.budget.used,
                                  api_call_budget=client.budget.limit)


def _event(p, rcept_no):
    return next(e for e in p['events'] if e['rcept_no'] == rcept_no)


def cases():
    live = base()
    out = [('live', live, True), ('empty', dp.empty_disclosures(NOW), True)]
    later = copy.deepcopy(live)
    later['as_of'] = dp.instant(NOW + timedelta(days=3))
    later['companies']['hanmi']['state'] = 'STALE'
    later['state'], later['reason_codes'] = 'STALE', ['STALE_INPUT']
    out.append(('stale_carried', later, True))

    def mutate(name, change, valid=False):
        p = copy.deepcopy(live)
        change(p)
        out.append((name, p, valid))
    mutate('body_field', lambda p: p['events'][0].__setitem__('body', 'text'))
    mutate('price_field', lambda p: p.__setitem__('price', 1))
    mutate('class_changed', lambda p: _event(p, '20260725000301').__setitem__('classification', 'OTHER'))
    mutate('results_type_free', lambda p: _event(p, '20260725000301').__setitem__('report_type', None), True)
    mutate('type_changed', lambda p: _event(p, '20260910000301').__setitem__('report_type', 'B'))
    mutate('link_other_receipt', lambda p: p['events'][0].__setitem__('link', dp.link('20260101000001')))
    mutate('link_other_host', lambda p: p['events'][0].__setitem__('link', p['events'][0]['link'].replace('dart.fss.or.kr', 'example.com')))
    mutate('occurrence_flip', lambda p: _event(p, '20260801000301').__setitem__('occurrence', 'NEW'))
    mutate('group_wrong', lambda p: _event(p, '20260801000301').__setitem__('group_id', 'hanmi:20260801000301'))
    mutate('order_swapped', lambda p: p['events'].insert(0, p['events'].pop(1)))
    mutate('accepted_time', lambda p: p['events'][0].__setitem__('accepted_at', '2026-10-02T01:00:00+00:00'))
    mutate('outside_window', lambda p: p['events'][-1].__setitem__('filing_date', '2026-07-01'))
    mutate('after_acquired', lambda p: p['events'][0].__setitem__('filing_date', '2026-10-12'))
    mutate('title_markup', lambda p: _event(p, '20260910000301').__setitem__('title', '<b>단일판매</b>'))
    mutate('title_double_space', lambda p: _event(p, '20260910000301').__setitem__('title', '단일판매  공급계약체결'))
    mutate('title_nbsp', lambda p: _event(p, '20260910000301').__setitem__('title', '단일판매\u00a0공급계약체결'))
    mutate('title_astral_200', lambda p: _event(p, '20260910000301').__setitem__('title', '😀' * 200), True)
    mutate('title_astral_201', lambda p: _event(p, '20260910000301').__setitem__('title', '😀' * 201))
    mutate('amended_flag', lambda p: _event(p, '20260801000301').__setitem__('amended', False))
    mutate('state_stale_while_fresh', lambda p: p['companies']['hanmi'].__setitem__('state', 'STALE'))
    mutate('company_reason_unknown', lambda p: p['companies']['hanmi'].__setitem__('reason_code', 'SOMETHING'))
    mutate('truncated_without_reason', lambda p: p['companies']['hanmi'].__setitem__('truncated', True))
    mutate('truncated_with_reason', lambda p: p['companies']['hanmi'].update(truncated=True, reason_code='DART_LIST_TRUNCATED'), True)
    mutate('calls_over_hard_max', lambda p: p['collection'].update(api_calls=51, api_call_budget=51))
    mutate('calls_over_budget', lambda p: p['collection'].update(api_calls=31))
    mutate('score_effect', lambda p: p.__setitem__('score_effect', 'ADJUST'))
    mutate('channel_news', lambda p: p.__setitem__('channel', 'NEWS'))
    mutate('source_sec', lambda p: p['events'][0].__setitem__('source', 'SEC'))
    mutate('first_seen_future', lambda p: p['events'][0].__setitem__('first_seen_at', '2026-10-12T00:00:00+00:00'))
    mutate('first_seen_before_filing', lambda p: p['events'][0].__setitem__('first_seen_at', '2026-09-01T00:00:00+00:00'))
    mutate('duplicate_receipt', lambda p: p['events'].insert(1, copy.deepcopy(p['events'][0])))
    mutate('corp_code_guess', lambda p: p['companies']['hanmi'].__setitem__('corp_code', '0000042'))
    mutate('events_without_company', lambda p: p['companies'].__setitem__('hanmi', dp.empty_company('042700')))
    mutate('as_of_offset', lambda p: p.__setitem__('as_of', p['as_of'].replace('+00:00', 'Z')))
    mutate('extra_company', lambda p: p['companies'].__setitem__('tokyo_electron', dp.empty_company('8035')))
    return out


def build():
    titles = []
    for title in TITLES:
        valid = dp.valid_title(title)
        titles.append({'title': title, 'valid': valid,
                       'family': dp.title_family(title) if valid else None, 'amended': dp.is_amended(title) if valid else None,
                       'classes': {str(t): dp.classify(title, t) for t in ('A', 'B', 'I', None)} if valid else None})
    rows = []
    for name, payload, valid in cases():
        try:
            dp.require_disclosures(copy.deepcopy(payload))
            verdict = True
        except ValueError:
            verdict = False
        if verdict != valid:
            raise SystemExit('VECTOR_EXPECTATION_MISMATCH ' + name)
        rows.append({'name': name, 'valid': valid, 'payload': payload})
    vectors = {'schema': 'dart-public-vectors/1', 'synthetic': True, 'now': dp.instant(NOW), 'titles': titles, 'cases': rows}
    return json.dumps(vectors, sort_keys=True, ensure_ascii=False, indent=1) + '\n'


def main(argv):
    text = build()
    if '--check' in argv:
        ok = OUT.exists() and OUT.read_text(encoding='utf-8') == text
        print('DART_VECTORS_OK' if ok else 'DART_VECTORS_STALE')
        return 0 if ok else 1
    OUT.write_text(text, encoding='utf-8')
    print('wrote', OUT.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
