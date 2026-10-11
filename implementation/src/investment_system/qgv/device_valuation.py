"""Python reference for the device (RAM-only) value view: forward DCF, reverse DCF + v1 V factors.

The device JS port `DeviceValuation.view` must agree with this function on the
synthetic vectors in tests/fixtures/device_valuation_reference_v1.json. It takes
a transient price argument and never returns it. No persistence, serializer or
publication exists for the result; it is a research display only.

Decided inputs only (2026-10-11): FCFE per share from the public SEC row
(fcfe/1.1), the adopted DCF parameters and the approved v1 raw_map V mappings.

v1.1 (dcf_parameters/v1.1-default): the explicit-period growth h is the
company's own 3-year revenue CAGR (public v_inputs.revenue_cagr_3y), clamped to
the parameter rule [lower, upper] (PROVISIONAL). With h the device computes the
forward DCF value per share (two_stage_dcf, price-free) and passes it to the
approved raw_map V mapping as dcf_value:
- margin_of_safety = the approved DCF branch (0.75 x DCF value vs price). The
  12 x EPS fallback of the same mapping is never shown as a margin of safety:
  without a usable DCF value the factor stays NOT_AVAILABLE (DCF_NOT_AVAILABLE).
- fundamental_value = the approved mapping, i.e. its DCF branch when a DCF value
  exists and its EPS (P/E) branch otherwise.
Without a CAGR (or under v1-default, which has no rule) h is not invented and
the forward DCF stays NOT_AVAILABLE. The reverse_dcf V factor uses only a
solved implied growth, never the legacy P/E implied-growth proxy. No currency
is converted (CURRENCY_BASIS_UNCONFIRMED).
"""
from __future__ import annotations

from collections.abc import Mapping

from .dcf import reverse_dcf, two_stage_dcf
from .dcf_parameters import _finite, explicit_growth
from .price_value import VPriceInputs, calculate_v_price_factors

VERSIONS = {'V1_UNCALIBRATED_DEFAULT': 'v1+dcf_v1_default', 'V1_1_UNCALIBRATED_DEFAULT': 'v1+dcf_v1_1_default'}
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

    cagr = v.get('revenue_cagr_3y') if v and v.get('state') != 'NOT_AVAILABLE' else None
    h, growth_reason = explicit_growth(parameters, cagr)
    growth = {'state': 'NOT_AVAILABLE' if h is None else 'PROVISIONAL', 'reason_codes': [growth_reason] if growth_reason else [],
              'value': h, 'revenue_cagr_3y': cagr if _finite(cagr) else None, 'clamped': None if h is None else h != cagr}

    reasons = []
    if fcfe_value is None:
        reasons.append('FCFE_NOT_AVAILABLE')
    if h is None:
        reasons.append(growth_reason)
    if reasons:
        dcf = {'state': 'NOT_AVAILABLE', 'reason_codes': reasons, 'value_per_share': None}
    else:
        d = two_stage_dcf(cashflow_per_share=fcfe_value, growth_rate=h, parameters=parameters, cashflow_currency=fcfe.get('currency'))
        dcf = {'state': d.state, 'reason_codes': list(d.reason_codes), 'value_per_share': d.value_per_share}
    dcf_value = dcf['value_per_share']

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

    v_currency = v.get('currency') if v else None
    basis = bool(v) and v_currency is not None and v_currency == price_currency
    if dcf_value is not None:
        # The DCF value is in the FCFE currency; the price must be in that same currency (no FX).
        basis = basis and fcfe.get('currency') == price_currency
    inputs = VPriceInputs(
        dcf_value=dcf_value,
        eps=v.get('eps') if v else None, revenue=v.get('revenue') if v else None, revenue_prev=v.get('revenue_prev') if v else None,
        reverse_dcf_implied_growth=implied, basis_confirmed=basis,
    )
    result = calculate_v_price_factors(inputs, price=price)
    factors = {k: {'score': f.score, 'state': f.state, 'reason': f.reason} for k, f in result.factors.items()}
    if implied is None:
        factors['reverse_dcf'] = _na('REVERSE_DCF_NOT_AVAILABLE')
    if dcf_value is None:
        factors['margin_of_safety'] = _na('DCF_NOT_AVAILABLE')
    elif dcf_value == 0:
        # The approved mapping would fall back to 12 x EPS; that is not a DCF margin of safety.
        factors['margin_of_safety'] = _na('DCF_VALUE_ZERO')
    return {
        'version': VERSIONS.get(status, 'v1+dcf_custom'),
        'parameters_status': status if isinstance(status, str) else None,
        'role': 'RAM_ONLY_DEVICE',
        'explicit_growth': growth,
        'dcf': dcf,
        'reverse_dcf': reverse,
        'v_factors': {k: factors[k] for k in V_ORDER},
        'standard_status': result.standard_status,
    }
