"""Strategy Profile layer. NEW IMPLEMENTATION.

Frozen Q/G weights and confirmed Macro v0.1.1 are NOT profile parameters.
Profile numbers below are PROVISIONAL placeholders, not a new official standard.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .enums import CalibrationLifecycle, StrategyStyle

PROFILE_SCHEMA_VERSION = "profile-schema-v1-PROVISIONAL"


# User-configurable keys. Official factor weights are excluded on purpose.
CONFIGURABLE_KEYS = (
    "cash_buffer",
    "risk_multiplier",
    "technical_lookback",
    "signal_threshold",
    "macro_warning_sensitivity",
    "execution_deadband_pp",
)

FROZEN_KEYS = (
    "q_weights",
    "g_weights",
    "v_production_enabled",
    "macro_confirmed_version",
    "q7_label",
)


@dataclass(frozen=True)
class ModuleProfile:
    module: str
    style: StrategyStyle
    params: dict[str, Any]
    lifecycle: CalibrationLifecycle = CalibrationLifecycle.PROVISIONAL


@dataclass(frozen=True)
class StrategyProfile:
    profile_id: str
    global_style: StrategyStyle
    qgv: ModuleProfile
    technical: ModuleProfile
    macro: ModuleProfile
    portfolio: ModuleProfile
    risk: ModuleProfile
    execution: ModuleProfile
    lifecycle: CalibrationLifecycle = CalibrationLifecycle.PROVISIONAL
    profile_version: str = PROFILE_SCHEMA_VERSION
    notes: str = "PROVISIONAL parameter pack. Does not rewrite frozen contracts."

    def parameter_blob(self) -> dict[str, Any]:
        return {
            "profile_version": self.profile_version,
            "global_style": self.global_style.value,
            "lifecycle": self.lifecycle.value,
            "modules": {
                m.module: {"style": m.style.value, "params": dict(m.params), "lifecycle": m.lifecycle.value}
                for m in (self.qgv, self.technical, self.macro, self.portfolio, self.risk, self.execution)
            },
        }

    def parameter_set_hash(self) -> str:
        blob = json.dumps(self.parameter_blob(), sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        body = self.parameter_blob()
        body.update(
            {
                "profile_id": self.profile_id,
                "parameter_set_hash": self.parameter_set_hash(),
                "notes": self.notes,
            }
        )
        return body


def _pack(style: StrategyStyle, cash: float, risk: float, lookback: int, thresh: float, sens: float, deadband: float) -> dict[str, ModuleProfile]:
    common = dict(
        cash_buffer=cash,
        risk_multiplier=risk,
        technical_lookback=lookback,
        signal_threshold=thresh,
        macro_warning_sensitivity=sens,
        execution_deadband_pp=deadband,
    )
    return {
        "qgv": ModuleProfile("qgv", style, {"risk_multiplier": risk}),
        "technical": ModuleProfile("technical", style, {"technical_lookback": lookback, "signal_threshold": thresh}),
        "macro": ModuleProfile("macro", style, {"macro_warning_sensitivity": sens}),
        "portfolio": ModuleProfile("portfolio", style, {"cash_buffer": cash}),
        "risk": ModuleProfile("risk", style, {"risk_multiplier": risk}),
        "execution": ModuleProfile("execution", style, {"execution_deadband_pp": deadband}),
    }


def builtin_profile(style: StrategyStyle) -> StrategyProfile:
    if style == StrategyStyle.DEFENSIVE:
        mods = _pack(style, 0.15, 0.70, 30, 0.70, 0.80, 0.75)
    elif style == StrategyStyle.AGGRESSIVE:
        mods = _pack(style, 0.00, 1.30, 8, 0.45, 0.40, 0.25)
    else:
        style = StrategyStyle.BALANCED
        mods = _pack(style, 0.05, 1.00, 14, 0.55, 0.60, 0.50)
    return StrategyProfile(
        profile_id=f"profile-{style.name.lower()}-provisional",
        global_style=style,
        **mods,
    )


def mixed_profile(*, qgv: StrategyStyle, technical: StrategyStyle, macro: StrategyStyle, risk: StrategyStyle) -> StrategyProfile:
    q = builtin_profile(qgv)
    t = builtin_profile(technical)
    m = builtin_profile(macro)
    r = builtin_profile(risk)
    return StrategyProfile(
        profile_id="profile-mixed-provisional",
        global_style=StrategyStyle.CUSTOM,
        qgv=q.qgv,
        technical=t.technical,
        macro=m.macro,
        portfolio=q.portfolio,
        risk=r.risk,
        execution=t.execution,
        notes="Mixed module styles. PROVISIONAL. Frozen contracts unchanged.",
    )


def custom_profile(overrides: dict[str, Any], base: StrategyStyle = StrategyStyle.BALANCED) -> StrategyProfile:
    blocked = set(overrides) & set(FROZEN_KEYS)
    if blocked:
        raise ValueError(f"frozen keys cannot be customized: {sorted(blocked)}")
    unknown = set(overrides) - set(CONFIGURABLE_KEYS)
    if unknown:
        raise ValueError(f"unknown configurable keys: {sorted(unknown)}")
    base_p = builtin_profile(base)
    qgv_p = dict(base_p.qgv.params)
    tech_p = dict(base_p.technical.params)
    mac_p = dict(base_p.macro.params)
    pf_p = dict(base_p.portfolio.params)
    risk_p = dict(base_p.risk.params)
    ex_p = dict(base_p.execution.params)
    if "risk_multiplier" in overrides:
        qgv_p["risk_multiplier"] = overrides["risk_multiplier"]
        risk_p["risk_multiplier"] = overrides["risk_multiplier"]
    if "technical_lookback" in overrides:
        tech_p["technical_lookback"] = overrides["technical_lookback"]
    if "signal_threshold" in overrides:
        tech_p["signal_threshold"] = overrides["signal_threshold"]
    if "macro_warning_sensitivity" in overrides:
        mac_p["macro_warning_sensitivity"] = overrides["macro_warning_sensitivity"]
    if "cash_buffer" in overrides:
        pf_p["cash_buffer"] = overrides["cash_buffer"]
    if "execution_deadband_pp" in overrides:
        ex_p["execution_deadband_pp"] = overrides["execution_deadband_pp"]
    return StrategyProfile(
        profile_id="profile-custom-provisional",
        global_style=StrategyStyle.CUSTOM,
        qgv=ModuleProfile("qgv", StrategyStyle.CUSTOM, qgv_p),
        technical=ModuleProfile("technical", StrategyStyle.CUSTOM, tech_p),
        macro=ModuleProfile("macro", StrategyStyle.CUSTOM, mac_p),
        portfolio=ModuleProfile("portfolio", StrategyStyle.CUSTOM, pf_p),
        risk=ModuleProfile("risk", StrategyStyle.CUSTOM, risk_p),
        execution=ModuleProfile("execution", StrategyStyle.CUSTOM, ex_p),
        notes="Custom configurable keys only. Frozen contracts unchanged.",
    )


def assert_frozen_untouched(q_weights: dict, g_weights: dict) -> None:
    from ..qgv.factors import G_WEIGHTS, Q_WEIGHTS

    if q_weights != Q_WEIGHTS or g_weights != G_WEIGHTS:
        raise ValueError("profile must not mutate frozen Q/G weights")
