from __future__ import annotations

from typing import Protocol, runtime_checkable

from ukb.models import KnowledgeObject, Sensitivity

SENSITIVITY_ORDER: dict[Sensitivity, int] = {
    Sensitivity.public: 0,
    Sensitivity.internal: 1,
    Sensitivity.confidential: 2,
    Sensitivity.restricted: 3,
}


@runtime_checkable
class PrincipalLike(Protocol):
    @property
    def subject(self) -> str: ...

    @property
    def clearance(self) -> Sensitivity: ...

    @property
    def tenant_id(self) -> str: ...


class AccessDecisionDetail:
    def __init__(
        self,
        *,
        allowed_objects: list[KnowledgeObject],
        denied_count: int,
        clearance: Sensitivity,
    ):
        self.allowed_objects = allowed_objects
        self.denied_count = denied_count
        self.clearance = clearance

    @property
    def decision(self) -> str:
        if self.denied_count and not self.allowed_objects:
            return "denied"
        return "allowed"

    @property
    def partially_redacted(self) -> bool:
        return bool(self.denied_count and self.allowed_objects)


class AccessPolicyService:
    """Apply clearance before retrieval results reach any model or adapter."""

    def __init__(
        self,
        *,
        default_clearance: Sensitivity = Sensitivity.internal,
        user_clearances: dict[str, Sensitivity] | None = None,
    ):
        self.default_clearance = default_clearance
        self.user_clearances = user_clearances or {}

    @classmethod
    def from_settings(cls, settings) -> AccessPolicyService:
        return cls(
            default_clearance=cls._parse_level(settings.default_user_clearance),
            user_clearances=cls._parse_clearance_map(settings.user_clearances),
        )

    def subject(self, principal: str | PrincipalLike) -> str:
        return principal if isinstance(principal, str) else principal.subject

    def clearance_for(self, principal: str | PrincipalLike) -> Sensitivity:
        if not isinstance(principal, str):
            return principal.clearance
        return self.user_clearances.get(principal, self.default_clearance)

    def can_access(self, principal: str | PrincipalLike, obj: KnowledgeObject) -> bool:
        clearance = self.clearance_for(principal)
        return SENSITIVITY_ORDER[obj.sensitivity] <= SENSITIVITY_ORDER[clearance]

    def can_access_sensitivity(
        self,
        principal: str | PrincipalLike,
        sensitivity: Sensitivity,
    ) -> bool:
        return SENSITIVITY_ORDER[sensitivity] <= SENSITIVITY_ORDER[self.clearance_for(principal)]

    def filter_objects(
        self,
        principal: str | PrincipalLike,
        objects: list[KnowledgeObject],
    ) -> AccessDecisionDetail:
        allowed: list[KnowledgeObject] = []
        denied = 0
        for obj in objects:
            if self.can_access(principal, obj):
                allowed.append(obj)
            else:
                denied += 1
        return AccessDecisionDetail(
            allowed_objects=allowed,
            denied_count=denied,
            clearance=self.clearance_for(principal),
        )

    @staticmethod
    def _parse_level(raw: str) -> Sensitivity:
        try:
            return Sensitivity(raw.strip().lower())
        except ValueError:
            return Sensitivity.internal

    @classmethod
    def _parse_clearance_map(cls, raw: str) -> dict[str, Sensitivity]:
        clearances: dict[str, Sensitivity] = {}
        for entry in raw.split(","):
            entry = entry.strip()
            if not entry or ":" not in entry:
                continue
            user_id, _, level = entry.partition(":")
            user_id = user_id.strip()
            if not user_id:
                continue
            try:
                clearances[user_id] = Sensitivity(level.strip().lower())
            except ValueError:
                continue
        return clearances
