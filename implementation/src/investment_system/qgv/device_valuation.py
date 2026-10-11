"""Python reference for the device (RAM-only) value view: reverse DCF + v1 V factors.

The device JS port `DeviceValuation.view` must agree with this function on the
synthetic vectors in tests/fixtures/device_valuation_reference_v1.json. It takes
a transient price argument and never returns it. No persistence, serializer or
publication exists for the result; it is a research display only.

Decided inputs only (2026-10-11): FCFE per share from the public SEC row, the
V1_UNCALIBRATED_DEFAULT DCF parameters and the approved v1 raw_map V mappings.
The explicit-period growth h is undecided, so the forward DCF value and the
DCF margin of safety stay NOT_AVAILABLE (EXPLICIT_GROWTH_UNDECIDED). The
reverse_dcf V factor uses only a solved implied growth, never the legacy P/E
implied-growth proxy.
"""
from __future__ import annotations

from collections.abc import Mapping

from .dcf import reverse_dcf
from .price_value import VPriceInputs, calculate_v_price_factors

DEFAULT_STATUS = 'V1_UNCALIBRATED_DEFAULT'
V_ORDER = ('fundamental_value', 'peer_relative_value', 'historical_valuation', 'sector_context',
           'theme_premium_discount', 'reverse_dcf', 'margin_of_safety')


def _na(reason):
    return {'score': None, 'state': 'NOT_AVAILABLE', 'reason': reason}


def _section(row, key):
    value = row.get(key) if isinstance(row, Mapping) else None
    return value if isinstance(value, Mapping) else None


def device_value_view(*, row, quote, parameters):
    """row: one validated public company row or None; quote: {'price','currency'} or None."""
    status = parameters.get('status') if isinstance(parameters, Mapping) else None
    fcfe = _section(row, 'fcfe')
    v = _section(row, 'v_inputs')
    fcfe_value = fcfe.get('fcfe_per_share') if fcfe and fcfe.get('state') != 'NOT_AVAILABLE' else None
    price = quote.get('price') if isinstance(quote, Mapping) else None
    price_currency = quote.get('currency') if isinstance(quote, Mapping) else None
    reasons = []
    if fcfe_value is None:
        reasons.append('FCFE_NOT_AVAILABLE')
    if price is None:
        reasons.append('NO_DEVICE_PRICE')
    if reasons:
        reverse = {'state': 'NOT_AVAILABLE', 'reason_codes': reasons, 'implied_growth': None}
    else:
        r = reverse_dcf(cashflow_per_share=fcfe_value, price=price, parameters=parameters,
                        cashflow_currency=fcfe.get('currency'), price_currency=price_currency)
        reverse = {'state': r.state, 'reason_codes': list(r.reason_codes), 'implied_growth': r.implied_growth}
    implied = reverse['implied_growth']
    eps = v.get('eps') if v else None
    inputs = VPriceInputs(
        eps=eps, revenue=v.get('revenue') if v else None, revenue_prev=v.get('revenue_prev') if v else None,
        reverse_dcf_implied_growth=implied,
        basis_confirmed=bool(v) and v.get('currency') is not None and v.get('currency') == price_currency,
    )
    result = calculate_v_price_factors(inputs, price=price)
    factors = {k: {'score': f.score, 'state': f.state, 'reason': f.reason} for k, f in result.factors.items()}
    if implied is None:
        factors['reverse_dcf'] = _na('REVERSE_DCF_NOT_AVAILABLE')
    factors['margin_of_safety'] = _na('EXPLICIT_GROWTH_UNDECIDED')
    return {
        'version': 'v1+dcf_v1_default' if status == DEFAULT_STATUS else 'v1+dcf_custom',
        'parameters_status': status if isinstance(status, str) else None,
        'role': 'RAM_ONLY_DEVICE',
        'dcf': {'state': 'NOT_AVAILABLE', 'reason_codes': ['EXPLICIT_GROWTH_UNDECIDED'], 'value_per_share': None},
        'reverse_dcf': reverse,
        'v_factors': {k: factors[k] for k in V_ORDER},
        'standard_status': result.standard_status,
    }
