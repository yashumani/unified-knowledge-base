from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for UKB persistence tables."""


class SourceRow(Base):
    __tablename__ = "sources"

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    domain: Mapped[str] = mapped_column(String(120), index=True)
    sensitivity: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReviewItemRow(Base):
    __tablename__ = "review_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(48), index=True)
    domain: Mapped[str] = mapped_column(String(120), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KnowledgeObjectRow(Base):
    __tablename__ = "knowledge_objects"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    object_type: Mapped[str] = mapped_column(String(48), index=True)
    domain: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(48), index=True)
    sensitivity: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    actor: Mapped[str] = mapped_column(String(160), index=True)
    target_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("ix_review_items_domain_status", ReviewItemRow.domain, ReviewItemRow.status)
Index("ix_knowledge_objects_domain_status", KnowledgeObjectRow.domain, KnowledgeObjectRow.status)
Index("ix_audit_events_created_at", AuditEventRow.created_at)
