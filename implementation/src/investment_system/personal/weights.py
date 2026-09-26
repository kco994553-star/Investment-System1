"""Hierarchical Strategy Weight Tree + versioned overrides (PIL §5-§8, §23). Independent schema.

C-24: this is NOT the existing contracts/strategy.StrategyProfile (a PROVISIONAL parameter pack); that object is left
untouched. Names here are prefixed "Personal" to avoid the collision.
C-30: official_weight is None unless an authoritative dataset supplies it; no example values are shipped. Which Q/G nodes
are editable is a policy decision (maturity supplied by the registry), not inferred here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from .versioning import ResultNamespace, content_hash

SIBLING_SUM_TOLERANCE = 1e-9


class NodeType(str, Enum):
    GROUP = "GROUP"
    WEIGHT = "WEIGHT"
    PARAMETER = "PARAMETER"
    COMPUTED = "COMPUTED"
    INFORMATION = "INFORMATION"
    LOCKED = "LOCKED"


class Maturity(str, Enum):
    PRODUCTION = "PRODUCTION"
    VALIDATED = "VALIDATED"
    PROVISIONAL = "PROVISIONAL"
    UNRESOLVED = "UNRESOLVED"
    LOCKED = "LOCKED"


class StrategyStatus(str, Enum):
    DRAFT = "DRAFT"
    SANDBOX = "SANDBOX"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class WeightTreeError(ValueError):
    pass


@dataclass(frozen=True)
class NodeDefinition:
    """Official registry entry. Stable node_id (no label/version encoded). custom weights are never stored here."""

    node_id: str
    parent_id: Optional[str]
    system: str  # "QGV" | "TECHNICAL" | "MACRO"
    node_type: NodeType
    maturity: Maturity
    label: str
    official_weight: Optional[float] = None  # local weight under the parent; None = not established (C-30)
    source_spec_id: Optional[str] = None
    source_spec_version: Optional[str] = None


@dataclass(frozen=True)
class OfficialRegistry:
    registry_version: str
    nodes: tuple[NodeDefinition, ...]

    def __post_init__(self) -> None:
        ids = [n.node_id for n in self.nodes]
        if len(ids) != len(set(ids)):
            raise WeightTreeError("duplicate node_id")
        by_id = {n.node_id: n for n in self.nodes}
        for n in self.nodes:
            if n.parent_id is not None and n.parent_id not in by_id:
                raise WeightTreeError(f"unknown parent {n.parent_id} for {n.node_id}")
            if n.node_type == NodeType.LOCKED and n.maturity != Maturity.LOCKED:
                raise WeightTreeError(f"LOCKED node {n.node_id} must have maturity LOCKED")
            if n.official_weight is not None and n.node_type not in (NodeType.WEIGHT, NodeType.GROUP):
                raise WeightTreeError(f"{n.node_id}: only WEIGHT/GROUP nodes carry weights")
            if n.maturity in (Maturity.UNRESOLVED,) and n.official_weight is not None:
                raise WeightTreeError(f"{n.node_id}: UNRESOLVED node cannot carry an official weight")

    def node(self, node_id: str) -> NodeDefinition:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        raise WeightTreeError(f"unknown node {node_id}")

    def children(self, node_id: Optional[str]) -> list[NodeDefinition]:
        return [n for n in self.nodes if n.parent_id == node_id]


@dataclass(frozen=True)
class WeightOverride:
    node_id: str
    local_weight: float


def editable(n: NodeDefinition, namespace: ResultNamespace) -> bool:
    """Only WEIGHT nodes; PRODUCTION/VALIDATED anywhere custom; PROVISIONAL only in SANDBOX/PREVIEW/BACKTEST (research);
    UNRESOLVED and LOCKED never."""
    if n.node_type != NodeType.WEIGHT:
        return False
    if n.maturity in (Maturity.PRODUCTION, Maturity.VALIDATED):
        return namespace != ResultNamespace.OFFICIAL
    if n.maturity == Maturity.PROVISIONAL:
        return namespace in (ResultNamespace.SANDBOX, ResultNamespace.PREVIEW, ResultNamespace.BACKTEST)
    return False


@dataclass(frozen=True)
class PersonalStrategyVersion:
    """Immutable version = Official Registry version + versioned overrides. Saving creates a new version (no overwrite)."""

    strategy_version_id: str
    strategy_id: str
    base_registry_version: str
    namespace: ResultNamespace
    overrides: tuple[WeightOverride, ...]
    status: StrategyStatus
    created_at: datetime
    parameter_profile_version: Optional[str] = None
    risk_profile_version: Optional[str] = None
    portfolio_policy_version: Optional[str] = None
    universe_policy_version: Optional[str] = None
    parent_version_id: Optional[str] = None

    @property
    def override_set_hash(self) -> str:
        return content_hash(sorted((o.node_id, o.local_weight) for o in self.overrides))


@dataclass(frozen=True)
class EffectiveNode:
    node_id: str
    local_weight: Optional[float]
    global_weight: Optional[float]
    source: str  # "OFFICIAL" | "OVERRIDE" | "UNSET"


def effective_tree(registry: OfficialRegistry, version: PersonalStrategyVersion) -> dict[str, EffectiveNode]:
    """Effective local/global weights. Override targets must be editable; siblings with any weight must all have one and
    sum to 1; global = product of local weights on the path (a 0 parent keeps the child mix, contribution 0).
    Missing weights are never redistributed (Locked Rule): a node without a weight has global None."""
    if version.base_registry_version != registry.registry_version:
        raise WeightTreeError("strategy version references another registry version (no silent rebase)")
    ov = {}
    for o in version.overrides:
        n = registry.node(o.node_id)
        if not editable(n, version.namespace):
            raise WeightTreeError(f"{o.node_id} ({n.node_type.value}/{n.maturity.value}) is not editable in {version.namespace.value}")
        if not (0.0 <= o.local_weight <= 1.0):
            raise WeightTreeError(f"{o.node_id}: local weight outside [0, 1]")
        if o.node_id in ov:
            raise WeightTreeError(f"duplicate override {o.node_id}")
        ov[o.node_id] = o.local_weight
    local: dict[str, tuple[Optional[float], str]] = {}
    for n in registry.nodes:
        if n.node_id in ov:
            local[n.node_id] = (ov[n.node_id], "OVERRIDE")
        elif n.official_weight is not None:
            local[n.node_id] = (n.official_weight, "OFFICIAL")
        else:
            local[n.node_id] = (None, "UNSET")
    for parent in {n.parent_id for n in registry.nodes}:
        sibs = [c for c in registry.children(parent) if c.node_type in (NodeType.WEIGHT, NodeType.GROUP)]
        vals = [local[c.node_id][0] for c in sibs]
        if any(v is not None for v in vals):
            if any(v is None for v in vals):
                raise WeightTreeError(f"siblings under {parent}: some weights unset (no redistribution)")
            if abs(sum(vals) - 1.0) > SIBLING_SUM_TOLERANCE:
                raise WeightTreeError(f"siblings under {parent} sum to {sum(vals)}, not 1")
    out = {}
    for n in registry.nodes:
        w, src = local[n.node_id]
        g: Optional[float] = w
        p = n.parent_id
        while g is not None and p is not None:
            pw = local[p][0]
            pn = registry.node(p)
            if pn.node_type == NodeType.GROUP and pw is None and pn.parent_id is None:
                break  # a root group without a weight is the tree root (weight 1 by definition)
            g = None if pw is None else g * pw
            p = pn.parent_id
        out[n.node_id] = EffectiveNode(n.node_id, w, g, src)
    return out
