"""Existing upstream output types -> Web schema-1 section data, verbatim.

Adapters serialize; they never rescore, rename, reshape or fill fields. When the Web consumer
reads a shape the upstream type does not have, the adapter raises IncompatibleShapeError and the
section is published NOT_AVAILABLE. Compatibility is recorded in SECTION_COMPATIBILITY.
"""
from __future__ import annotations

from typing import Any, Iterable

from ..contracts.models import LeaderboardSnapshot, MacroSnapshot, PortfolioSnapshot, QGVSnapshot, TechnicalSnapshot
from .errors import IdentityError, IncompatibleShapeError
from .serialization import to_jsonable

# Fields the Web MVP consumer (product/web_assets/app.js) reads per section.
WEB_READS = {
    'qgv': ('Q_score', 'G_score', 'V_score', 'total_score', 'confidence', 'coverage_state'),
    'technical': ('regime', 'execution_zone', 'invalidation'),
    'macro': ('state', 'regime', 'indicators', 'exposures'),
    'portfolio': ('role', 'holdings', 'return', 'market_value', 'currency', 'exposure'),
    'leaderboard': ('rows[].rank', 'rows[].company_id', 'rows[].ticker', 'rows[].market_cap_rank', 'rows[].total_score',
                    'rows[].daily_move', 'rows[].consensus', 'rows[].scenario', 'rows[].reevaluation_trigger'),
    'news': ('[].event_id', '[].headline', '[].issuer_ids', '[].available_at', '[].status', '[].source_language'),
    'changes': ('summary',),
}

SECTION_COMPATIBILITY = {
    'qgv': {'upstream': 'contracts.models.QGVSnapshot', 'compatibility': 'COMPATIBLE', 'scope': 'ENTITY_MAP',
            'missing_web_fields': []},
    'technical': {'upstream': 'contracts.models.TechnicalSnapshot', 'compatibility': 'COMPATIBLE', 'scope': 'ENTITY_MAP',
                  'missing_web_fields': [], 'note': 'shape only; current engine is a structural placeholder (synthetic)'},
    'macro': {'upstream': 'contracts.models.MacroSnapshot', 'compatibility': 'INCOMPATIBLE', 'scope': 'DOCUMENT',
              'missing_web_fields': ['indicators (upstream: environment.indicators)', 'exposures'],
              'note': 'mapping environment.indicators -> indicators and an exposure producer need an owner decision'},
    'portfolio': {'upstream': 'contracts.models.PortfolioSnapshot', 'compatibility': 'PARTIAL', 'scope': 'DOCUMENT',
                  'missing_web_fields': ['return', 'market_value', 'currency (upstream has base_currency)', 'exposure']},
    'leaderboard': {'upstream': 'contracts.models.LeaderboardSnapshot', 'compatibility': 'PARTIAL', 'scope': 'ROWS',
                    'missing_web_fields': ['market_cap_rank', 'daily_move', 'consensus', 'scenario', 'reevaluation_trigger']},
    'news': {'upstream': None, 'compatibility': 'NO_UPSTREAM', 'scope': None, 'missing_web_fields': list(WEB_READS['news'])},
    'changes': {'upstream': None, 'compatibility': 'NO_UPSTREAM', 'scope': None, 'missing_web_fields': ['summary']},
    'relationships': {'upstream': 'rig.network.render (HTML via web_mvp --rig-page)', 'compatibility': 'OUT_OF_BUNDLE',
                      'scope': None, 'missing_web_fields': []},
}


def _entity_map(snapshots: Iterable[Any], cls: type) -> tuple[dict, bool]:
    out, synthetic = {}, False
    for s in snapshots:
        if not isinstance(s, cls):
            raise IncompatibleShapeError(f'expected {cls.__name__}, got {type(s).__name__}')
        if s.company_id in out:
            raise IdentityError(f'duplicate company_id {s.company_id}')
        out[s.company_id] = to_jsonable(s)
        synthetic = synthetic or bool(s.synthetic)
    return out, synthetic


def qgv_section(snapshots: Iterable[QGVSnapshot]) -> tuple[str, dict, bool]:
    data, synthetic = _entity_map(snapshots, QGVSnapshot)
    return 'ENTITY_MAP', data, synthetic


def technical_section(snapshots: Iterable[TechnicalSnapshot]) -> tuple[str, dict, bool]:
    data, synthetic = _entity_map(snapshots, TechnicalSnapshot)
    return 'ENTITY_MAP', data, synthetic


def leaderboard_section(snapshot: LeaderboardSnapshot) -> tuple[str, dict, bool]:
    if not isinstance(snapshot, LeaderboardSnapshot):
        raise IncompatibleShapeError('expected LeaderboardSnapshot')
    if snapshot.recomputed_qgv:
        raise IncompatibleShapeError('leaderboard recomputed QGV; only consumed snapshots may be published')
    return 'ROWS', to_jsonable(snapshot), False


def portfolio_section(snapshot: PortfolioSnapshot) -> tuple[str, dict, bool]:
    if not isinstance(snapshot, PortfolioSnapshot):
        raise IncompatibleShapeError('expected PortfolioSnapshot')
    return 'DOCUMENT', to_jsonable(snapshot), bool(snapshot.synthetic)


def macro_section(snapshot: MacroSnapshot) -> tuple[str, dict, bool]:
    raise IncompatibleShapeError('MacroSnapshot keeps indicators under environment and has no exposures; '
                                 'Web schema-1 reads data.indicators/data.exposures. Not reshaped without owner decision.')
