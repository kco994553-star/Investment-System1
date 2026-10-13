"""Synthetic in-process OpenDART transport for tests. No network; corp codes, receipts and amounts are synthetic."""
from __future__ import annotations

from datetime import datetime, timezone
import io
import json
from urllib.parse import parse_qs, urlsplit
import zipfile

from investment_system.providers.dart_collection import DartResponse

FAKE_KEY = '0123456789abcdefFAKEKEYXfedcba9876543210'  # 40 characters, synthetic.
CORP_CODE = '00000042'  # Synthetic corp_code; the real one is resolved from corpCode.xml in Actions.
NOW = datetime(2026, 10, 11, 0, 30, tzinfo=timezone.utc)


def corp_zip(rows=None):
    rows = rows if rows is not None else [('00000001', '삼성전자', '005930'), (CORP_CODE, '한미반도체', '042700'),
                                          ('00000077', '비상장회사', ' ')]
    xml = '<?xml version="1.0" encoding="UTF-8"?><result>' + ''.join(
        f'<list><corp_code>{c}</corp_code><corp_name>{n}</corp_name><stock_code>{s}</stock_code><modify_date>20260101</modify_date></list>'
        for c, n, s in rows) + '</result>'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('CORPCODE.xml', xml.encode())
    return buffer.getvalue()


def _row(no, dt, name):
    return {'corp_cls': 'K', 'corp_name': '한미반도체', 'corp_code': CORP_CODE, 'stock_code': '042700', 'report_nm': name,
            'rcept_no': no, 'flr_nm': 'SYNTHETIC FILER', 'rcept_dt': dt, 'rm': ''}


LISTS = {
    'A': [_row('20260814000101', '20260814', '반기보고서 (2026.06)'), _row('20260515000101', '20260515', '분기보고서 (2026.03)'),
          _row('20260320000101', '20260320', '[기재정정]사업보고서 (2025.12)'), _row('20260317000101', '20260317', '사업보고서 (2025.12)'),
          _row('20251114000101', '20251114', '분기보고서 (2025.09)')],
    'B': [_row('20260901000201', '20260901', '주요사항보고서(자기주식취득결정)')],
    'I': [_row('20260725000301', '20260725', '연결재무제표기준영업(잠정)실적(공정공시)'),
          _row('20260910000301', '20260910', '단일판매ㆍ공급계약체결'),
          _row('20260801000301', '20260801', '[기재정정]단일판매ㆍ공급계약체결'),
          _row('20260720000301', '20260720', '단일판매ㆍ공급계약체결'),
          _row('20260725000302', '20260725', '기업설명회(IR)개최(안내공시)(공정공시)')],
    None: [_row('20261002000401', '20261002', '임원ㆍ주요주주특정증권등소유상황보고서'),
           _row('20260920000401', '20260920', '임원ㆍ주요주주특정증권등소유상황보고서')],
}


def _fs(account, sj, amount, previous='', add=''):
    return {'rcept_no': None, 'reprt_code': None, 'bsns_year': None, 'corp_code': CORP_CODE, 'sj_div': sj, 'sj_nm': sj,
            'account_id': account, 'account_nm': 'synthetic', 'account_detail': '-', 'thstrm_nm': '제 n 기',
            'thstrm_amount': amount, 'thstrm_add_amount': add, 'frmtrm_nm': '제 n-1 기', 'frmtrm_amount': previous,
            'ord': '1', 'currency': 'KRW'}


ANNUAL_ROWS = [
    _fs('ifrs-full_Revenue', 'CIS', '558,734,000,000', '159,000,000,000'),
    _fs('dart_OperatingIncomeLoss', 'CIS', '255,400,000,000', '34,600,000,000'),
    _fs('ifrs-full_ProfitLoss', 'CIS', '200,100,000,000'),
    _fs('ifrs-full_BasicEarningsLossPerShare', 'CIS', '2100', '270'),
    _fs('ifrs-full_CashFlowsFromUsedInOperatingActivities', 'CF', '180,000,000,000'),
    _fs('ifrs-full_PurchaseOfPropertyPlantAndEquipment', 'CF', '-40,000,000,000'),
    _fs('ifrs-full_CashAndCashEquivalents', 'BS', '150,000,000,000'),
    _fs('ifrs-full_EquityAttributableToOwnersOfParent', 'BS', '900,000,000,000'),
    _fs('ifrs-full_Equity', 'BS', '905,000,000,000'),
    _fs('-표준계정코드 미사용-', 'BS', '1'),
    _fs('ifrs-full_Equity', 'SCE', '1'),
]
INTERIM_ROWS = [
    _fs('ifrs-full_Revenue', 'IS', '150,000,000,000', '', '300,000,000,000'),
    _fs('dart_OperatingIncomeLoss', 'IS', '60,000,000,000', '', '120,000,000,000'),
    _fs('ifrs-full_ProfitLoss', 'IS', '50,000,000,000', '', '95,000,000,000'),
    _fs('ifrs-full_CashFlowsFromUsedInOperatingActivities', 'CF', '70,000,000,000'),
    _fs('ifrs-full_CashAndCashEquivalents', 'BS', '160,000,000,000'),
    _fs('ifrs-full_Equity', 'BS', '980,000,000,000'),
]


class FakeOpenDart:
    """Callable transport. Records each request's endpoint + params (with the key) for assertions."""

    def __init__(self, *, overrides=None, corp=None):
        self.requests = []
        self.overrides = overrides or {}
        self.corp = corp if corp is not None else corp_zip()

    def __call__(self, url, *, timeout, max_bytes):
        parts = urlsplit(url)
        assert parts.scheme == 'https' and parts.netloc == 'opendart.fss.or.kr' and parts.path.startswith('/api/')
        endpoint = parts.path[len('/api/'):]
        params = {k: v[0] for k, v in parse_qs(parts.query, keep_blank_values=True).items()}
        self.requests.append((endpoint, params))
        key = (endpoint, params.get('pblntf_ty'), params.get('reprt_code'), params.get('fs_div'))
        for match, response in self.overrides.items():
            if all(m is None or m == k for m, k in zip(match, key)) and match[0] == endpoint:
                return response(params) if callable(response) else response
        if endpoint == 'corpCode.xml':
            return DartResponse(200, self.corp)
        if endpoint == 'list.json':
            rows = [r for r in LISTS.get(params.get('pblntf_ty'), []) if params['bgn_de'] <= r['rcept_dt'] <= params['end_de']]
            if params.get('pblntf_ty') is None:
                rows = sorted(rows + [r for t in 'ABI' for r in LISTS[t] if params['bgn_de'] <= r['rcept_dt'] <= params['end_de']],
                              key=lambda r: r['rcept_no'], reverse=True)
            if not rows:
                return self.json({'status': '013', 'message': 'no data'})
            return self.json({'status': '000', 'message': 'ok', 'page_no': 1, 'page_count': 100, 'total_count': len(rows),
                              'total_page': 1, 'list': rows})
        if endpoint == 'fnlttSinglAcntAll.json':
            source = {('2025', '11011', 'CFS'): ('20260320000101', ANNUAL_ROWS), ('2026', '11012', 'OFS'): ('20260814000101', INTERIM_ROWS)}
            hit = source.get((params['bsns_year'], params['reprt_code'], params['fs_div']))
            if hit is None:
                return self.json({'status': '013', 'message': 'no data'})
            rows = [{**r, 'rcept_no': hit[0], 'reprt_code': params['reprt_code'], 'bsns_year': params['bsns_year']} for r in hit[1]]
            return self.json({'status': '000', 'message': 'ok', 'list': rows})
        if endpoint == 'stockTotqySttus.json':
            if params['reprt_code'] != '11011':
                return self.json({'status': '013', 'message': 'no data'})
            return self.json({'status': '000', 'message': 'ok', 'list': [
                {'se': '보통주', 'istc_totqy': '97,000,000', 'tesstk_co': '2,000,000', 'distb_stock_co': '95,000,000'},
                {'se': '합계', 'istc_totqy': '97,000,000', 'tesstk_co': '2,000,000', 'distb_stock_co': '95,000,000'}]})
        raise AssertionError('unexpected endpoint')

    @staticmethod
    def json(payload):
        return DartResponse(200, json.dumps(payload, ensure_ascii=False).encode())
