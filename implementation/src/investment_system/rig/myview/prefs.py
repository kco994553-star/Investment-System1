"""RIG P3 user organization: ★ 관심기업 and My Groups; Portfolio via a read-only port. NEW IMPLEMENTATION.

- ``HoldingsPort`` is the only way RIG sees Portfolio holdings (read-only, C-39 issuer ids).
  RIG never imports Track B; the adapter from Track B holdings is owned outside RIG.
- ★ 관심기업 is one list (no Favorite/Watchlist split), changed only by explicit USER actions.
- My Groups are an optional organization layer (many-to-many, filter/focus only, no weights or
  scores) and are separate from any system industry / value-chain classification.
All state is an append-only action log reconstructed point-in-time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol

from ..gate import IdentityLookup
from ..model import _require_aware, _require_text


class HoldingsPort(Protocol):
    def held_issuer_ids(self, as_of: datetime) -> frozenset[str]: ...


class Actor(str, Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"


class InterestOp(str, Enum):
    ADD = "ADD"
    REMOVE = "REMOVE"


class GroupOp(str, Enum):
    CREATE = "CREATE"
    RENAME = "RENAME"
    ADD_MEMBER = "ADD_MEMBER"
    REMOVE_MEMBER = "REMOVE_MEMBER"
    DELETE = "DELETE"


@dataclass(frozen=True)
class InterestAction:
    action_id: str
    op: InterestOp
    issuer_id: str
    at: datetime
    actor: Actor

    def __post_init__(self) -> None:
        _require_text("action_id", self.action_id)
        _require_text("issuer_id", self.issuer_id)
        _require_aware("at", self.at)


@dataclass(frozen=True)
class GroupAction:
    action_id: str
    op: GroupOp
    group_id: str
    at: datetime
    actor: Actor
    name: str | None = None
    issuer_id: str | None = None

    def __post_init__(self) -> None:
        _require_text("action_id", self.action_id)
        _require_text("group_id", self.group_id)
        _require_aware("at", self.at)
        if self.op in (GroupOp.CREATE, GroupOp.RENAME):
            _require_text("name", self.name or "")
        if self.op in (GroupOp.ADD_MEMBER, GroupOp.REMOVE_MEMBER):
            _require_text("issuer_id", self.issuer_id or "")


@dataclass(frozen=True)
class Group:
    group_id: str
    name: str
    members: frozenset[str]


class UserOrganization:
    def __init__(self, identity: IdentityLookup) -> None:
        self.identity = identity
        self.interest_log: list[InterestAction] = []
        self.group_log: list[GroupAction] = []
        self._ids: set[str] = set()

    def _check(self, action_id: str, actor: Actor, at: datetime, log: list) -> None:
        if action_id in self._ids:
            raise ValueError(f"action {action_id!r} already recorded; append-only")
        if actor is not Actor.USER:
            raise PermissionError("only an explicit USER action may change 관심기업 / My Groups")
        if log and log[-1].at > at:
            raise ValueError("actions must be recorded in time order")

    def record_interest(self, a: InterestAction) -> None:
        self._check(a.action_id, a.actor, a.at, self.interest_log)
        if self.identity.issuer(a.issuer_id) is None:
            raise ValueError(f"unknown issuer {a.issuer_id!r} (fail closed)")
        self._ids.add(a.action_id)
        self.interest_log.append(a)

    def record_group(self, a: GroupAction) -> None:
        self._check(a.action_id, a.actor, a.at, self.group_log)
        groups = self.groups_as_of(a.at)
        exists = a.group_id in groups
        if a.op is GroupOp.CREATE and exists:
            raise ValueError("group already exists")
        if a.op is not GroupOp.CREATE and not exists:
            raise ValueError("group does not exist")
        if a.op is GroupOp.ADD_MEMBER and self.identity.issuer(a.issuer_id) is None:
            raise ValueError(f"unknown issuer {a.issuer_id!r} (fail closed)")
        self._ids.add(a.action_id)
        self.group_log.append(a)

    def interests_as_of(self, as_of: datetime) -> frozenset[str]:
        _require_aware("as_of", as_of)
        cur: set[str] = set()
        for a in self.interest_log:
            if a.at > as_of:
                break
            (cur.add if a.op is InterestOp.ADD else cur.discard)(a.issuer_id)
        return frozenset(cur)

    def groups_as_of(self, as_of: datetime) -> dict[str, Group]:
        _require_aware("as_of", as_of)
        cur: dict[str, tuple[str, set[str]]] = {}
        for a in self.group_log:
            if a.at > as_of:
                break
            if a.op is GroupOp.CREATE:
                cur[a.group_id] = (a.name, set())
            elif a.op is GroupOp.RENAME:
                cur[a.group_id] = (a.name, cur[a.group_id][1])
            elif a.op is GroupOp.ADD_MEMBER:
                cur[a.group_id][1].add(a.issuer_id)
            elif a.op is GroupOp.REMOVE_MEMBER:
                cur[a.group_id][1].discard(a.issuer_id)
            else:
                del cur[a.group_id]
        return {g: Group(g, n, frozenset(m)) for g, (n, m) in sorted(cur.items())}
