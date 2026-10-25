"""Loopback-only synthetic studio. Never used by public cockpit exporters.

Run: PYTHONPATH=src python -m investment_system.product.studio --port 8765
All fixture prices/fundamentals are invented; no provider or personal data is read.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import statistics
from urllib.parse import parse_qs, urlsplit

from ..contracts.enums import SimulationMode
from ..contracts.models import DataStamp
from ..macro.engine import MacroEngine
from ..qgv.dcf_parameters import load_default_dcf_parameters
from ..qgv.identifiers import OFFICIAL_PORTFOLIO_V11
from ..qgv.portfolio import PortfolioEngine
from ..qgv.qgv_v2 import QG_FACTORS, score_universe
from ..qgv.simulation import SimulationConfig, SimulationEngine
from ..qgv.type_config import load_official_type_config
from ..technical.engine import TechnicalEngine

AS_OF = datetime(2026, 10, 14, 20, tzinfo=timezone.utc)
ASSETS = Path(__file__).with_name('studio_assets')
SCENARIOS = {
    'base': {'name': '완만한 성장', 'growth': .032, 'inflation': .026, 'drift': .011, 'vol': .027},
    'inflation': {'name': '인플레이션 재상승', 'growth': -.01, 'inflation': .065, 'drift': .003, 'vol': .044},
    'recession': {'name': '경기 침체', 'growth': -.025, 'inflation': .021, 'drift': -.004, 'vol': .055},
}
SECTORS = {'Semicap': '반도체 장비', 'AI': '반도체·AI', 'BigTech': '플랫폼·소프트웨어', 'Other': '산업·헬스케어'}
NAMES = {'asml': 'ASML', 'lrcx': '램리서치', 'klac': 'KLA', 'tokyo_electron': '도쿄일렉트론', 'hanmi': '한미반도체',
         'nvda': '엔비디아', 'amd': 'AMD', 'avgo': '브로드컴', 'qcom': '퀄컴', 'intc': '인텔', 'msft': '마이크로소프트',
         'googl': '알파벳', 'amzn': '아마존', 'rtx': 'RTX', 'stry': '스트라이커', 'etn': '이튼', 'hubb': '허벨', 'gev': 'GE 버노바', 'rok': '로크웰 오토메이션'}


def _monthly_returns(months, scenario='base', *, benchmark=False):
    s = SCENARIOS[scenario]
    drift = s['drift'] * (.76 if benchmark else 1)
    vol = s['vol'] * (.82 if benchmark else 1)
    return [drift + vol * math.sin(i * 1.73 + .4) + vol * .4 * math.cos(i * .67)
            - (.065 if i % 19 == 9 else 0) for i in range(months)]


def _fixtures():
    companies, quotes = {}, {}
    for i, ident in enumerate(OFFICIAL_PORTFOLIO_V11):
        q, g = 57 + (i * 11 % 34), 43 + (i * 17 % 48)
        factors = {f: min(99., (q if f.startswith('q_') else g) + (j % 5 - 2) * 2.) for j, f in enumerate(QG_FACTORS)}
        vin = {'currency': 'USD', 'ebit': 450 + i * 34, 'fcf': 280 + i * 29, 'total_debt': 700 + i * 21,
               'cash': 300 + i * 18, 'diluted_shares': 100., 'revenue_cagr_3y': .04 + (i % 7) * .025,
               'ebit_per_share_history': [{'period_end': f'{2020+y}-12-31', 'value': (3 + i * .21) * (1 + .09 * y)} for y in range(5)]}
        if ident.company_id == 'intc':
            vin = None  # Visible missing V: an absent input is never zero-filled.
        companies[ident.company_id] = {'industry_group': ident.sector, 'profile': 'GENERAL', 'factors': factors,
                                      'memberships': None, 'v_inputs': vin}
        quotes[ident.company_id] = {'price': round(60 + i * 13.7 + math.sin(i) * 24, 2), 'currency': 'USD'}
    return companies, quotes


def studio_snapshot(preset='balanced'):
    inputs, quotes = _fixtures()
    scores = score_universe(inputs, quotes, type_config=load_official_type_config().to_dict(),
                            parameters=load_default_dcf_parameters(), preset=preset)
    portfolio = PortfolioEngine().official_v11(AS_OF)
    holdings = {h.company_id: h for h in portfolio.holdings}
    raw_actual = [h.target_weight * (1 + .22 * math.sin(i * 1.8)) for i, h in enumerate(portfolio.holdings)]
    normalizer = sum(raw_actual)
    rows = []
    for i, ident in enumerate(OFFICIAL_PORTFOLIO_V11):
        cid = ident.company_id
        shape = [1 + .003 * j + .04 * math.sin(j * .7 + i) for j in range(36)]
        history = [round(quotes[cid]['price'] * value / shape[-1], 2) for value in shape]
        tech_returns = [history[j] / history[j - 1] - 1 for j in range(1, len(history))]
        technical = TechnicalEngine().evaluate(cid, AS_OF, tech_returns, synthetic=True)
        rows.append({'company_id': cid, 'ticker': ident.ticker, 'name': NAMES[cid], 'legal_name': ident.legal_name,
                     'exchange': ident.exchange, 'identity_notes': list(ident.ambiguity_flags), 'sector': SECTORS[ident.sector],
                     'target_weight': holdings[cid].target_weight, 'actual_weight': raw_actual[i] / normalizer * .9,
                     'price': quotes[cid]['price'], 'currency': 'USD', 'daily_change': round(tech_returns[-1] * 100, 2),
                     'qgv': scores[cid], 'technical': technical.to_dict(),
                     'price_history': history})
    macro = MacroEngine().evaluate(AS_OF, {'growth': .032, 'inflation': .026}, synthetic=True).to_dict()
    return {'state': 'DEMO', 'synthetic': True, 'as_of': AS_OF.isoformat(), 'source': 'studio synthetic fixture / existing engines',
            'score_version': 'qgv-v2', 'preset': preset, 'companies': rows, 'cash_weight': .1, 'macro': macro,
            'macro_axes': [{'name': name, 'state': state, 'value': value, 'note': note} for name, state, value, note in (
                ('성장', 'normal', '3.2%', '실질 성장률 가정'), ('물가', 'watch', '2.6%', '물가 상승률 가정'),
                ('유동성', 'normal', '+1.8%', '유동성 증감 가정'), ('통화정책', 'watch', '4.25%', '정책금리 가정'),
                ('신용', 'normal', '3.1%p', '신용 스프레드 가정'), ('고용', 'normal', '4.2%', '실업률 가정'),
                ('재정', 'missing', None, '예시 입력 없음'), ('환율', 'missing', None, '예시 입력 없음'))],
            'news': [
                {'company_id': 'nvda', 'category': '산업 구조', 'title': 'AI 인프라 투자가 공급망으로 확산된다면', 'summary': '가상의 데이터센터 투자 확대 상황에서 반도체·장비·전력 인프라의 연결을 살펴봅니다.', 'kind': '가상 시나리오', 'path': ['플랫폼 투자', 'AI 반도체', '반도체 장비', '전력 인프라']},
                {'company_id': 'asml', 'category': '공급망', 'title': '첨단 공정 설비 투자가 회복된다면', 'summary': '수주·매출 인식 시차와 고객사의 투자 계획을 함께 확인하는 예시입니다.', 'kind': '가상 시나리오', 'path': ['설비 투자', '장비 수주', '생산 능력']},
                {'company_id': 'etn', 'category': '전력 인프라', 'title': '전력 수요 증가가 실적으로 이어진다면', 'summary': '수요 증가가 수익성으로 연결되는 조건을 관찰하는 합성 사례입니다.', 'kind': '가상 시나리오', 'path': ['데이터센터', '전력 수요', '전력 장비']},
            ]}


def _number(payload, key, default, low, high, *, integer=False):
    value = payload.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{key}: 허용 범위의 숫자를 입력하세요')
    if integer and int(value) != value:
        raise ValueError(f'{key}: 정수를 입력하세요')
    return int(value) if integer else float(value)


def simulate(payload):
    if not isinstance(payload, dict):
        raise ValueError('입력 형식을 확인하세요')
    capital = _number(payload, 'capital', 100000000, 10000, 100000000000)
    monthly = _number(payload, 'monthly', 500000, 0, 100000000)
    months = _number(payload, 'months', 36, 1, 120, integer=True)
    cash = _number(payload, 'cash', 10, 0, 100) / 100
    scenario = payload.get('scenario', 'base')
    if not isinstance(scenario, str) or scenario not in SCENARIOS:
        raise ValueError('시나리오를 선택하세요')
    returns = [r * (1 - cash) for r in _monthly_returns(months, scenario)]
    bench_returns = _monthly_returns(months, scenario, benchmark=True)
    wealth = benchmark = capital
    unit = peak = 100.
    drawdown = 0.
    engine = SimulationEngine()
    config = SimulationConfig(SimulationMode.HISTORICAL, AS_OF, AS_OF, AS_OF, capital)
    series = [{'month': 0, 'strategy': wealth, 'benchmark': benchmark, 'contributed': capital, 'unit': unit}]
    for i, (ret, br) in enumerate(zip(returns, bench_returns), 1):
        stamp = DataStamp(f'studio_month_{i}', 'synthetic', 'SYNTHETIC', 'studio fixture', AS_OF, AS_OF, AS_OF, synthetic=True)
        # Use the canonical PIT-aware engine for both series; contributions happen at month end.
        a = SimulationConfig(config.mode, config.start, config.end, config.as_of, wealth)
        b = SimulationConfig(config.mode, config.start, config.end, config.as_of, benchmark)
        wealth = engine.run(a, [stamp], {stamp.data_stamp_id: ret}).ending_value + monthly
        benchmark = engine.run(b, [stamp], {stamp.data_stamp_id: br}).ending_value + monthly
        unit *= 1 + ret
        peak = max(peak, unit)
        drawdown = min(drawdown, unit / peak - 1)
        series.append({'month': i, 'strategy': wealth, 'benchmark': benchmark, 'contributed': capital + monthly * i, 'unit': unit})
    return {'state': 'DEMO', 'synthetic': True, 'purpose': 'PRODUCT_SIMULATION', 'scenario': scenario,
            'scenario_name': SCENARIOS[scenario]['name'], 'months': months, 'cash': cash, 'capital': capital, 'monthly': monthly,
            'ending_value': wealth, 'contributed': capital + monthly * months, 'profit': wealth - capital - monthly * months,
            'total_return': unit / 100 - 1, 'annualized_return': (unit / 100) ** (12 / months) - 1,
            'max_drawdown': drawdown, 'volatility': statistics.stdev(returns) * math.sqrt(12) if months > 1 else None,
            'benchmark_ending': benchmark, 'series': series,
            'macro': MacroEngine().evaluate(AS_OF, {k: SCENARIOS[scenario][k] for k in ('growth', 'inflation')}, synthetic=True).to_dict()}


class StudioHandler(BaseHTTPRequestHandler):
    server_version = 'InvestmentStudio/1'

    def log_message(self, *_):
        pass  # No request inputs or financial data in logs.

    def _send(self, status, body, content_type='application/json; charset=utf-8'):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        route = urlsplit(self.path)
        if route.path == '/api/studio':
            try:
                self._send(200, studio_snapshot(parse_qs(route.query).get('preset', ['balanced'])[0]))
            except ValueError:
                self._send(400, {'error': '지원하는 QGV v2 프로필을 선택하세요.'})
            return
        files = {'/': ('index.html', 'text/html; charset=utf-8'), '/studio.css': ('studio.css', 'text/css; charset=utf-8'),
                 '/studio.js': ('studio.js', 'text/javascript; charset=utf-8')}
        if route.path not in files:
            self._send(404, {'error': '요청한 경로가 없습니다.'})
            return
        name, mime = files[route.path]
        self._send(200, (ASSETS / name).read_bytes(), mime)

    def do_POST(self):
        if self.path != '/api/simulate':
            self._send(404, {'error': '요청한 경로가 없습니다.'})
            return
        # Only same-origin browser requests; this local service never accepts credentials.
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            self._send(403, {'error': '같은 로컬 화면에서 실행하세요.'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > 4096:
                raise ValueError('입력 크기를 확인하세요')
            payload = json.loads(self.rfile.read(length))
            self._send(200, simulate(payload))
        except (ValueError, TypeError, OverflowError):
            self._send(400, {'error': '입력 범위를 확인하세요. 자본금 1만원~1천억원, 월 납입 0~1억원, 기간 1~120개월, 현금 0~100%입니다.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), StudioHandler)
    print(f'Local DEMO studio: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
