"""In-memory synthetic validator fixture, independent of all retained reports."""
from investment_system.product.web_mvp import repository_bundle, envelope


def synthetic_bundle():
    bundle = repository_bundle()
    bundle['companies'] = [{'company_id': 'nvda', 'ticker': 'NVDA', 'name': 'nvda'}]
    bundle['qgv'] = envelope({'nvda': {'company_id': 'nvda', 'Q_score': 42, 'G_score': 21,
                                      'V_score': None, 'synthetic': True}},
                             'DEMO', '2099-01-01', 'invented contract fixture')
    bundle['portfolio'] = envelope({'holdings': [{'company_id': 'nvda', 'target_weight': 1}]},
                                   'DEMO', '2099-01-01', 'invented contract fixture')
    return bundle
