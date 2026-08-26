from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, cast

from ukb.application import BrainApplication
from ukb.config import Settings
from ukb.governed_runtime.cache import CacheCoordinator, digest_payload
from ukb.governed_runtime.conversations import ConversationRepository
from ukb.governed_runtime.models import (
    AskBrainRequest,
    CacheEventRecord,
    CacheNamespace,
    ConversationMessage,
    ConversationRecord,
    ConversationRole,
    GovernedAnswer,
    RuntimeStatus,
)
from ukb.models import ContextPack, ContextPackRequest


class GovernedRuntimeService:
    """Conversation and cache facade shared by REST, MCP, and future SDKs.

    Conversation records are authoritative and durable. Cache entries are
    disposable optimizations. Every cache identity is tenant and permission
    scoped, and cached Context Packs are re-authorized before delivery.
    """

    def __init__(
        self,
        *,
        application: BrainApplication,
        settings: Settings,
        conversations: ConversationRepository,
        cache: CacheCoordinator,
    ) -> None:
        self.application = application
        self.settings = settings
        self.conversations = conversations
        self.cache = cache

    def start_conversation(
        self,
        *,
        principal: Any,
        title: str = "New Brain Chat",
        attributes: Mapping[str, Any] | None = None,
    ) -> ConversationRecord:
        tenant_id = self._tenant_id(principal)
        subject = self.application.access_policy.subject(principal)
        record = ConversationRecord(
            tenant_id=tenant_id,
            subject=subject,
            title=title.strip() or "New Brain Chat",
            attributes=dict(attributes or {}),
        )
        return self.conversations.create(record)

    def list_conversations(self, *, principal: Any, limit: int = 50) -> list[ConversationRecord]:
        return self.conversations.list(
            self._tenant_id(principal),
            self.application.access_policy.subject(principal),
            limit=max(1, min(limit, 200)),
        )

    def get_conversation(self, conversation_id: str, *, principal: Any) -> dict[str, Any] | None:
        tenant_id = self._tenant_id(principal)
        subject = self.application.access_policy.subject(principal)
        conversation = self.conversations.get(conversation_id, tenant_id, subject)
        if conversation is None:
            return None
        messages = self.conversations.messages(conversation_id, tenant_id, subject)
        return {
            "conversation": conversation.model_dump(mode="json"),
            "messages": [message.model_dump(mode="json") for message in messages],
        }

    def ask(self, request: AskBrainRequest, *, principal: Any) -> GovernedAnswer:
        tenant_id = self._tenant_id(principal)
        subject = self.application.access_policy.subject(principal)
        conversation = self._resolve_conversation(request, tenant_id=tenant_id, subject=subject, principal=principal)
        previous_messages = self.conversations.messages(conversation.conversation_id, tenant_id, subject)
        user_message = self.conversations.add_message(
            ConversationMessage(
                conversation_id=conversation.conversation_id,
                tenant_id=tenant_id,
                subject=subject,
                role=ConversationRole.user,
                content=request.question.strip(),
                attributes={"domains": request.domains, "mode": request.mode, "locale": request.locale},
            )
        )

        knowledge_snapshot_id = self._knowledge_snapshot(principal)
        prompt_prefix_hash = self._prompt_prefix_hash()
        permission_scope_hash = self._permission_scope_hash(principal)
        conversation_state_hash = digest_payload(
            [
                {
                    "role": message.role.value,
                    "content": message.content,
                    "context_pack_id": message.context_pack_id,
                }
                for message in previous_messages
            ]
        )
        cache_identity = {
            "tenant_id": tenant_id,
            "permission_scope_hash": permission_scope_hash,
            "subject": subject,
            "model": self.settings.ai_chat_model,
            "provider": self.settings.ai_provider,
            "prompt_prefix_hash": prompt_prefix_hash,
            "prompt_version": self.settings.runtime_prompt_version,
            "tool_schema_version": self.settings.tool_schema_version,
            "response_schema_version": self.settings.response_schema_version,
            "access_policy_version": self.settings.access_policy_version,
            "knowledge_snapshot_id": knowledge_snapshot_id,
            "data_snapshot_id": request.data_snapshot_id,
            "conversation_state_hash": conversation_state_hash,
            "question": request.question.strip(),
            "domains": sorted(request.domains),
            "mode": request.mode,
            "locale": request.locale,
        }
        eligible = request.mode != "debug" and not request.force_refresh
        cached, event = self.cache.get_json(
            namespace=CacheNamespace.response,
            tenant_id=tenant_id,
            subject=subject,
            identity=cache_identity,
            eligible=eligible,
            reason="debug_or_forced_refresh" if not eligible else None,
        )
        cache_events: list[CacheEventRecord] = []
        pack: ContextPack | None = None
        if cached is not None:
            try:
                candidate = ContextPack.model_validate(cached["context_pack"])
            except Exception:
                candidate = None
            if candidate is not None and self._cached_pack_is_authorized(candidate, principal=principal):
                pack = candidate
            else:
                event.hit = False
                event.reason = "cached_pack_failed_reauthorization"
        self.conversations.add_cache_event(event)
        cache_events.append(event)

        response_cache_hit = pack is not None
        if pack is None:
            pack_request = ContextPackRequest(
                question=request.question.strip(),
                user_id=subject,
                domains=request.domains,
                mode=request.mode,
            )
            pack = self.application.build_context_pack(pack_request, principal=principal)
            if eligible and pack.access_decision != "denied":
                self.cache.set_json(
                    namespace=CacheNamespace.response,
                    tenant_id=tenant_id,
                    identity=cache_identity,
                    payload={"context_pack": pack.model_dump(mode="json")},
                    ttl_seconds=self.settings.response_cache_ttl_seconds,
                )

        assistant_message = self.conversations.add_message(
            ConversationMessage(
                conversation_id=conversation.conversation_id,
                tenant_id=tenant_id,
                subject=subject,
                role=ConversationRole.assistant,
                content=self._answer_text(pack),
                context_pack_id=pack.context_pack_id,
                cache_event_id=event.event_id,
                attributes={
                    "response_cache_hit": response_cache_hit,
                    "access_decision": pack.access_decision,
                    "knowledge_snapshot_id": knowledge_snapshot_id,
                },
            )
        )
        current = self.conversations.get(conversation.conversation_id, tenant_id, subject) or conversation
        return GovernedAnswer(
            conversation=current,
            user_message=user_message,
            assistant_message=assistant_message,
            context_pack=pack,
            response_cache_hit=response_cache_hit,
            cache_events=cache_events,
            prompt_prefix_hash=prompt_prefix_hash,
            knowledge_snapshot_id=knowledge_snapshot_id,
        )

    def get_source_lineage(self, source_id: str, *, principal: Any) -> dict[str, Any]:
        tenant_id = self._tenant_id(principal)
        subject = self.application.access_policy.subject(principal)
        source = self._mapping_value(getattr(self.application.store, "sources", {}), source_id)
        if source is None or self._object_tenant(source) != tenant_id:
            return {"error": "source_not_found", "source_id": source_id}
        try:
            allowed = self.application.access_policy.can_access(principal, source)
        except Exception:
            allowed = True
        if not allowed:
            return {"error": "source_not_found", "source_id": source_id}

        current_version_id = getattr(source, "current_version_id", None)
        identity = {
            "source_id": source_id,
            "source_version_id": current_version_id,
            "permission_scope_hash": self._permission_scope_hash(principal),
            "tool_schema_version": self.settings.tool_schema_version,
        }
        cached, event = self.cache.get_json(
            namespace=CacheNamespace.tool,
            tenant_id=tenant_id,
            subject=subject,
            identity=identity,
        )
        self.conversations.add_cache_event(event)
        if cached is not None:
            return {**cached, "cache": event.model_dump(mode="json")}

        versions = [
            item
            for item in self._mapping_values(getattr(self.application.store, "source_versions", {}))
            if getattr(item, "source_id", None) == source_id and self._object_tenant(item) == tenant_id
        ]
        chunks = [
            item
            for item in self._mapping_values(getattr(self.application.store, "evidence_chunks", {}))
            if getattr(item, "source_id", None) == source_id and self._object_tenant(item) == tenant_id
        ]
        objects = [
            item
            for item in self._mapping_values(getattr(self.application.store, "knowledge_objects", {}))
            if source_id in set(getattr(item, "source_ids", []) or [])
            and self._object_tenant(item) == tenant_id
            and self.application.access_policy.can_access(principal, item)
        ]
        payload = {
            "source": source.model_dump(mode="json") if hasattr(source, "model_dump") else {"source_id": source_id},
            "versions": [item.model_dump(mode="json") for item in versions if hasattr(item, "model_dump")],
            "evidence_chunks": [item.model_dump(mode="json") for item in chunks if hasattr(item, "model_dump")],
            "published_objects": [item.model_dump(mode="json") for item in objects if hasattr(item, "model_dump")],
        }
        self.cache.set_json(
            namespace=CacheNamespace.tool,
            tenant_id=tenant_id,
            identity=identity,
            payload=payload,
            ttl_seconds=self.settings.tool_cache_ttl_seconds,
        )
        return {**payload, "cache": event.model_dump(mode="json")}

    def invalidate_cache(
        self,
        *,
        principal: Any,
        namespace: CacheNamespace | None = None,
    ) -> dict[str, Any]:
        roles = self._roles(principal)
        if "governance_admin" not in roles and "cache_admin" not in roles:
            return {"error": "cache_invalidation_not_permitted"}
        tenant_id = self._tenant_id(principal)
        deleted = self.cache.invalidate_tenant(tenant_id, namespace)
        return {
            "tenant_id": tenant_id,
            "namespace": namespace.value if namespace else "all",
            "deleted": deleted,
        }

    def status(self, *, principal: Any) -> RuntimeStatus:
        tenant_id = self._tenant_id(principal)
        conversation_count, message_count = self.conversations.counts(tenant_id)
        return RuntimeStatus(
            cache_enabled=self.settings.cache_enabled,
            cache_backend=self.cache.backend.name,
            prompt_prefix_version=self.settings.runtime_prompt_version,
            tool_schema_version=self.settings.tool_schema_version,
            response_schema_version=self.settings.response_schema_version,
            access_policy_version=self.settings.access_policy_version,
            mcp_transport=self.settings.mcp_transport,
            mcp_subject=self.settings.mcp_subject,
            mcp_tenant_id=self.settings.mcp_tenant_id,
            cache_metrics=self.cache.metrics(),
            conversation_count=conversation_count,
            message_count=message_count,
        )

    def close(self) -> None:
        self.cache.close()
        self.conversations.close()

    def _resolve_conversation(
        self,
        request: AskBrainRequest,
        *,
        tenant_id: str,
        subject: str,
        principal: Any,
    ) -> ConversationRecord:
        if request.conversation_id:
            existing = self.conversations.get(request.conversation_id, tenant_id, subject)
            if existing is None:
                raise ValueError("conversation_not_found")
            return existing
        title = request.title or request.question.strip()[:90] or "New Brain Chat"
        return self.start_conversation(principal=principal, title=title, attributes=request.attributes)

    def _prompt_prefix_hash(self) -> str:
        stable_prefix = {
            "runtime_prompt_version": self.settings.runtime_prompt_version,
            "tool_schema_version": self.settings.tool_schema_version,
            "response_schema_version": self.settings.response_schema_version,
            "access_policy_version": self.settings.access_policy_version,
            "ai_schema_version": self.settings.ai_schema_version,
            "provider": self.settings.ai_provider,
            "model": self.settings.ai_chat_model,
        }
        return digest_payload(stable_prefix)

    def _permission_scope_hash(self, principal: Any) -> str:
        scope = {
            "tenant_id": self._tenant_id(principal),
            "subject": self.application.access_policy.subject(principal),
            "roles": sorted(self._roles(principal)),
            "groups": sorted(set(getattr(principal, "groups", []) or [])),
            "clearance": str(getattr(getattr(principal, "clearance", None), "value", getattr(principal, "clearance", "internal"))),
            "access_policy_version": self.settings.access_policy_version,
        }
        return digest_payload(scope)

    def _knowledge_snapshot(self, principal: Any) -> str:
        tenant_id = self._tenant_id(principal)
        records: list[dict[str, Any]] = []
        for item in self._mapping_values(getattr(self.application.store, "knowledge_objects", {})):
            if self._object_tenant(item) != tenant_id:
                continue
            try:
                if not self.application.access_policy.can_access(principal, item):
                    continue
            except Exception:
                continue
            records.append(
                {
                    "id": getattr(item, "id", None),
                    "version": getattr(item, "version", None),
                    "status": str(getattr(getattr(item, "status", None), "value", getattr(item, "status", ""))),
                    "updated_at": getattr(item, "updated_at", None),
                    "superseded_by": getattr(item, "superseded_by", None),
                }
            )
        records.sort(key=lambda value: (str(value.get("id")), str(value.get("version"))))
        return digest_payload(records)

    def _cached_pack_is_authorized(self, pack: ContextPack, *, principal: Any) -> bool:
        if pack.access_decision == "denied":
            return False
        allowed_ids = {
            str(getattr(item, "id", ""))
            for item in self._mapping_values(getattr(self.application.store, "knowledge_objects", {}))
            if self._object_tenant(item) == self._tenant_id(principal)
            and self.application.access_policy.can_access(principal, item)
        }
        payload = pack.model_dump(mode="json")
        referenced: set[str] = set()
        for key in ("objects", "approved_objects", "knowledge_objects", "context_objects"):
            values = payload.get(key)
            if not isinstance(values, list):
                continue
            for value in values:
                if not isinstance(value, dict):
                    continue
                object_id = value.get("id") or value.get("object_id") or value.get("memory_id")
                if object_id:
                    referenced.add(str(object_id))
        return not referenced or referenced.issubset(allowed_ids)

    @staticmethod
    def _answer_text(pack: ContextPack) -> str:
        for attribute in ("answer_guidance", "ai_guidance", "summary"):
            value = getattr(pack, attribute, None)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, list) and value:
                return "\n".join(str(item) for item in value)
        return f"Governed Context Pack {pack.context_pack_id} is ready with access decision {pack.access_decision}."

    @staticmethod
    def _mapping_values(value: Any) -> Iterable[Any]:
        if hasattr(value, "values"):
            return cast(Iterable[Any], value.values())
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
            return value
        return []

    @staticmethod
    def _mapping_value(value: Any, key: str) -> Any | None:
        if hasattr(value, "get"):
            return value.get(key)
        return None

    def _tenant_id(self, principal: Any) -> str:
        return str(getattr(principal, "tenant_id", None) or self.settings.default_tenant_id)

    @staticmethod
    def _object_tenant(value: Any) -> str:
        return str(getattr(value, "tenant_id", None) or "default")

    @staticmethod
    def _roles(principal: Any) -> set[str]:
        return {str(role) for role in (getattr(principal, "roles", []) or [])}
