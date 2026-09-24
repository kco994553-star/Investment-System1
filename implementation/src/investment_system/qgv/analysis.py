"""QGV Analysis engine. NEW IMPLEMENTATION of v1.7.6 Frozen Contract."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from ..contracts.enums import CoverageState, ProfileKind, QualityState
from ..contracts.models import FactorObservation, QGVSnapshot
from ..versions import (
    IMPLEMENTATION_KIND,
    IMPLEMENTATION_LINE,
    QGV_ANALYSIS_CONTRACT,
    QGV_STANDARD,
    QGV_SYSTEM_LINE,
)
from .factors import V_INITIAL_PRIOR
from .scoring import attractiveness_10, production_v_score, score_g, score_q, score_v_candidates, score_v_prior


class AnalysisEngine:
    def analyze(
        self,
        company_id: str,
        as_of: datetime,
        observations: dict[str, FactorObservation],
        *,
        profile_kind: ProfileKind = ProfileKind.GENERAL_CORPORATE,
        key_drivers: tuple[str, ...] = (),
        peer_weights: dict[str, float] | None = None,
        data_stamp_refs: tuple[str, ...] = (),
        synthetic: bool = False,
        confidence: str = "MEDIUM",
        g_horizon: dict | None = None,
    ) -> QGVSnapshot:
        q, q_cov, q_notes = score_q(observations, profile_kind)
        g, g_cov, g_notes = score_g(observations, profile_kind)
        v_cands = score_v_candidates(observations)
        v_prior, v_cov, v_notes = score_v_prior(observations, profile_kind)
        v_prod, v_policy = production_v_score(v_cands, v_prior, v_cov)

        coverages = {q_cov, g_cov}
        if CoverageState.BLOCKED in coverages:
            coverage = CoverageState.BLOCKED
        elif CoverageState.PARTIAL in coverages or q is None or g is None:
            coverage = CoverageState.PARTIAL
        else:
            coverage = CoverageState.READY
        if synthetic:
            coverage = CoverageState.SYNTHETIC if coverage == CoverageState.READY else coverage

        qualities = []
        if synthetic:
            qualities.append(QualityState.SYNTHETIC)
        if coverage == CoverageState.BLOCKED:
            qualities.append(QualityState.BLOCKED_DEPENDENCY)

        total = None
        if q is not None and g is not None:
            # V excluded from production total until VALIDATED.
            total = round((q + g) / 2.0, 4)

        type_adjusted = total  # type-specific matrices CALIBRATION_PENDING

        peers = peer_weights or {}
        if peers:
            s = sum(peers.values())
            if s > 0:
                peers = {k: v / s for k, v in peers.items()}

        return QGVSnapshot(
            qgv_snapshot_id=f"qgv_{uuid4().hex[:12]}",
            company_id=company_id,
            analyzed_at=as_of,
            as_of=as_of,
            qgv_system_version=QGV_SYSTEM_LINE,
            qgv_standard_version=QGV_STANDARD,
            qgv_analysis_contract=QGV_ANALYSIS_CONTRACT,
            implementation_line=IMPLEMENTATION_LINE,
            implementation_kind=IMPLEMENTATION_KIND,
            profile_kind=profile_kind,
            Q_score=q,
            G_score=g,
            V_score=v_prod,
            V_policy_status=v_policy,
            total_score=total,
            attractiveness_10=attractiveness_10(q, g),
            type_adjusted_score_100=type_adjusted,
            confidence=confidence,
            key_drivers=key_drivers,
            peer_weights=peers,
            factor_breakdown={
                "q_notes": q_notes,
                "g_notes": g_notes,
                "q_coverage": q_cov.value,
                "g_coverage": g_cov.value,
                "v_notes": v_notes,
                "v_coverage": v_cov.value,
                "v_lifecycle": v_policy.value,
                "v_factor_table": [
                    {
                        "factor_id": fid,
                        "base_weight": V_INITIAL_PRIOR[fid],
                        "score": None if observations.get(fid) is None else observations[fid].score_0_100,
                        "confidence": None if observations.get(fid) is None else observations[fid].quality.value,
                        "coverage": None if observations.get(fid) is None else observations[fid].quality.value,
                        "effective_weight": 0.0
                        if observations.get(fid) is None or observations[fid].score_0_100 is None
                        else V_INITIAL_PRIOR[fid],
                        "missing_reason": None
                        if observations.get(fid) and observations[fid].score_0_100 is not None
                        else (None if observations.get(fid) is None else observations[fid].notes),
                        "provenance": None if observations.get(fid) is None else observations[fid].notes,
                    }
                    for fid in V_INITIAL_PRIOR
                ],
            },
            v_candidates=v_cands,
            data_stamp_refs=data_stamp_refs,
            coverage_state=coverage,
            quality_states=tuple(qualities),
            synthetic=synthetic,
            g_horizon=g_horizon,
        )
