from __future__ import annotations

from ukb.models import KnowledgeObject, Sensitivity

SENSITIVITY_ORDER: dict[Sensitivity, int] = {
    Sensitivity.public: 0,
    Sensitivity.internal: 1,
    Sensitivity.confidential: 2,
    Sensitivity.restricted: 3,
}


class AccessDecisionDetail:
    """Result of applying the access policy to a candidate object set."""

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
        """Deny only when the policy blocked every object that actually matched.

        An empty result with nothing blocked is not a denial: the brain simply
        has no context. Distinguishing those two cases matters, because
        "denied" must mean a policy stopped something.
        """

        if self.denied_count and not self.allowed_objects:
            return "denied"
        return "allowed"

    @property
    def partially_redacted(self) -> bool:
        return bool(self.denied_count and self.allowed_objects)


class AccessPolicyService:
    """Sensitivity-based filtering applied before context is composed.

    Security filtering happens at retrieval time. The runtime never retrieves
    everything and then asks a model to keep a secret.

    This scaffold has no identity provider, so callers receive the configured
    default clearance unless an explicit per-user clearance is set. Wire
    ``clearance_for`` to SSO/OIDC group claims before pointing this at real
    data; the filtering seam below is the place production ACLs plug into.
    """

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

    def clearance_for(self, user_id: str) -> Sensitivity:
        return self.user_clearances.get(user_id, self.default_clearance)

    def can_access(self, user_id: str, obj: KnowledgeObject) -> bool:
        clearance = self.clearance_for(user_id)
        return SENSITIVITY_ORDER[obj.sensitivity] <= SENSITIVITY_ORDER[clearance]

    def filter_objects(
        self,
        user_id: str,
        objects: list[KnowledgeObject],
    ) -> AccessDecisionDetail:
        allowed: list[KnowledgeObject] = []
        denied = 0
        for obj in objects:
            if self.can_access(user_id, obj):
                allowed.append(obj)
            else:
                denied += 1
        return AccessDecisionDetail(
            allowed_objects=allowed,
            denied_count=denied,
            clearance=self.clearance_for(user_id),
        )

    @staticmethod
    def _parse_level(raw: str) -> Sensitivity:
        try:
            return Sensitivity(raw.strip().lower())
        except ValueError:
            return Sensitivity.internal

    @classmethod
    def _parse_clearance_map(cls, raw: str) -> dict[str, Sensitivity]:
        """Parse ``user:level,user2:level`` into a clearance map.

        Malformed entries are skipped rather than silently widening access.
        """

        clearances: dict[str, Sensitivity] = {}
        for entry in raw.split(","):
            entry = entry.strip()
            if not entry or ":" not in entry:
                continue
            user_id, _, level = entry.partition(":")
            user_id = user_id.strip()
            level = level.strip().lower()
            if not user_id:
                continue
            try:
                clearances[user_id] = Sensitivity(level)
            except ValueError:
                continue
        return clearances
