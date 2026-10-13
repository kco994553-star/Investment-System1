"""User decisions: only verified ASML quarterly 6-K and structural news candidates."""
from datetime import date

from investment_system.providers import sec_8k_disclosures as sec
from investment_system.product import news_signals as news
from tests.test_sec_disclosures import NOW, acc, index_html, submissions


def test_asml_6k_requires_quarterly_earnings_index_evidence():
    accession = acc(201, cik='0000937966')
    body = submissions('asml', [('6-K', accession, '2026-10-01', '2026-09-30', '2026-10-01T13:00:00Z', '')])
    candidates = sec.foreign_earnings_candidates('asml', body, acquired_at=NOW, since=date(2026, 7, 1))
    assert len(candidates) == 1 and candidates[0]['items'] == []
    index = index_html('asml', accession, [('ASML reports third-quarter 2026 financial results', 'q3.htm', 'EX-99.1')])
    assert sec.quarterly_earnings_exhibit('asml', accession, index)['title'].startswith('ASML reports')
    generic = index_html('asml', accession, [('Press release', 'news.htm', 'EX-99.1')])
    assert sec.quarterly_earnings_exhibit('asml', accession, generic) == 'QUARTERLY_EARNINGS_UNCONFIRMED'
    assert sec.foreign_earnings_candidates('nvda', submissions('nvda', [('6-K', acc(202), '2026-10-01', '', '2026-10-01T13:00:00Z', '')]), acquired_at=NOW, since=date(2026, 7, 1)) == []


def test_ordinary_legal_news_is_not_a_structural_candidate():
    rows = [
        {'company_id': 'asml', 'title': 'ASML export controls extended', 'link': 'https://example.invalid/export', 'published_at': '2026-10-01T10:00:00+00:00', 'group_id': 'a', 'occurrence': 'NEW'},
        {'company_id': 'asml', 'title': 'ASML investor lawsuit filed', 'link': 'https://example.invalid/lawsuit', 'published_at': '2026-10-01T11:00:00+00:00', 'group_id': 'b', 'occurrence': 'NEW'},
        {'company_id': 'asml', 'title': 'ASML export controls repeated', 'link': 'https://example.invalid/repeat', 'published_at': '2026-10-02T10:00:00+00:00', 'group_id': 'a', 'occurrence': 'REPEAT'},
    ]
    candidates = news.structural_candidates(rows)
    assert len(candidates) == 1
    assert candidates[0] == {'company_id': 'asml', 'code': 'E4', 'reason_code': 'NEWS_STRUCTURAL_EVENT',
                            'event_kind': 'EXPORT_RESTRICTION', 'evidence_grade': 'SIGNAL', 'score_effect': 'NONE',
                            'info_only': True, 'group_id': 'a', 'link': rows[0]['link'], 'published_at': rows[0]['published_at']}
