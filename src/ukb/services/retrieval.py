from __future__ import annotations

from ukb.services.access import AccessDecisionDetail, AccessPolicyService
from ukb.store import BrainStore


class RetrievalService:
    """Simple keyword retrieval for the scaffold.

    Production should replace this with permission-aware hybrid retrieval:
    keyword + vector + graph traversal + semantic layer lookups. The access
    policy already runs here, so the ordering stays correct when the scoring is
    upgraded: identity -> policy check -> retrieve only allowed content.
    """

    def __init__(self, store: BrainStore, access_policy: AccessPolicyService | None = None):
        self.store = store
        self.access_policy = access_policy or AccessPolicyService()

    def search(
        self,
        query: str,
        domains: list[str] | None = None,
        limit: int = 5,
        user_id: str = "anonymous",
    ) -> AccessDecisionDetail:
        """Return matches the caller is cleared to see, plus what was blocked.

        The blocked count is reported rather than discarded so the context pack
        can state that a policy withheld material instead of implying the brain
        had nothing.
        """

        normalized_query = query.lower()
        domain_filter = set(domains or [])

        candidates = []
        for obj in self.store.knowledge_objects.values():
            if domain_filter and obj.domain not in domain_filter:
                continue

            haystack = " ".join(
                [
                    obj.title,
                    obj.summary,
                    obj.type.value,
                    obj.domain,
                    str(obj.attributes),
                ]
            ).lower()

            score = self._score(normalized_query, haystack)
            if score > 0:
                candidates.append((score, obj))

        candidates.sort(key=lambda item: item[0], reverse=True)
        matched = [obj for _, obj in candidates]

        # Filter before truncating so a blocked object never consumes a slot
        # that an allowed object should have occupied.
        decision = self.access_policy.filter_objects(user_id, matched)
        decision.allowed_objects = decision.allowed_objects[:limit]
        return decision

    def _score(self, query: str, haystack: str) -> int:
        terms = [term for term in query.split() if len(term) > 2]
        return sum(1 for term in terms if term in haystack)
