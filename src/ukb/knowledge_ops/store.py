from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from sqlalchemy import DateTime, Index, String, Text, create_engine, delete, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from ukb.knowledge_ops.models import (
    QualityAssessment,
    RetrievalFeedback,
    ReviewAssignment,
    ReviewComment,
    SourceRefreshRun,
    SourceSubscription,
)
from ukb.storage.orm import Base


class QualityAssessmentRow(Base):
    __tablename__ = "knowledge_quality_assessments"

    assessment_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(160), index=True)
    actor: Mapped[str] = mapped_column(String(200), index=True)
    disposition: Mapped[str] = mapped_column(String(48), index=True)
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReviewAssignmentRow(Base):
    __tablename__ = "knowledge_review_assignments"

    assignment_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(160), index=True)
    review_item_id: Mapped[str] = mapped_column(String(80), index=True)
    assignee: Mapped[str] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(48), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReviewCommentRow(Base):
    __tablename__ = "knowledge_review_comments"

    comment_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(160), index=True)
    review_item_id: Mapped[str] = mapped_column(String(80), index=True)
    author: Mapped[str] = mapped_column(String(200), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourceSubscriptionRow(Base):
    __tablename__ = "knowledge_source_subscriptions"

    subscription_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(160), index=True)
    connector_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(48), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourceRefreshRunRow(Base):
    __tablename__ = "knowledge_source_refresh_runs"

    run_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(160), index=True)
    subscription_id: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(48), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetrievalFeedbackRow(Base):
    __tablename__ = "knowledge_retrieval_feedback"

    feedback_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(160), index=True)
    actor: Mapped[str] = mapped_column(String(200), index=True)
    label: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index(
    "ix_quality_tenant_disposition_created",
    QualityAssessmentRow.tenant_id,
    QualityAssessmentRow.disposition,
    QualityAssessmentRow.created_at,
)
Index(
    "ix_assignment_tenant_assignee_status",
    ReviewAssignmentRow.tenant_id,
    ReviewAssignmentRow.assignee,
    ReviewAssignmentRow.status,
)
Index(
    "ix_subscription_tenant_status",
    SourceSubscriptionRow.tenant_id,
    SourceSubscriptionRow.status,
)

KNOWLEDGE_OPERATIONS_TABLES = [
    QualityAssessmentRow.__table__,
    ReviewAssignmentRow.__table__,
    ReviewCommentRow.__table__,
    SourceSubscriptionRow.__table__,
    SourceRefreshRunRow.__table__,
    RetrievalFeedbackRow.__table__,
]


@runtime_checkable
class KnowledgeOperationsRepository(Protocol):
    quality_assessments: dict[str, QualityAssessment]
    assignments: dict[str, ReviewAssignment]
    comments: dict[str, ReviewComment]
    subscriptions: dict[str, SourceSubscription]
    refresh_runs: dict[str, SourceRefreshRun]
    feedback: dict[str, RetrievalFeedback]

    def add_quality(self, value: QualityAssessment) -> QualityAssessment: ...
    def add_assignment(self, value: ReviewAssignment) -> ReviewAssignment: ...
    def add_comment(self, value: ReviewComment) -> ReviewComment: ...
    def add_subscription(self, value: SourceSubscription) -> SourceSubscription: ...
    def add_refresh_run(self, value: SourceRefreshRun) -> SourceRefreshRun: ...
    def add_feedback(self, value: RetrievalFeedback) -> RetrievalFeedback: ...
    def close(self) -> None: ...


class InMemoryKnowledgeOperationsStore:
    def __init__(self) -> None:
        self.quality_assessments: dict[str, QualityAssessment] = {}
        self.assignments: dict[str, ReviewAssignment] = {}
        self.comments: dict[str, ReviewComment] = {}
        self.subscriptions: dict[str, SourceSubscription] = {}
        self.refresh_runs: dict[str, SourceRefreshRun] = {}
        self.feedback: dict[str, RetrievalFeedback] = {}

    def add_quality(self, value: QualityAssessment) -> QualityAssessment:
        self.quality_assessments[value.assessment_id] = value
        return value

    def add_assignment(self, value: ReviewAssignment) -> ReviewAssignment:
        self.assignments[value.assignment_id] = value
        return value

    def add_comment(self, value: ReviewComment) -> ReviewComment:
        self.comments[value.comment_id] = value
        return value

    def add_subscription(self, value: SourceSubscription) -> SourceSubscription:
        self.subscriptions[value.subscription_id] = value
        return value

    def add_refresh_run(self, value: SourceRefreshRun) -> SourceRefreshRun:
        self.refresh_runs[value.run_id] = value
        return value

    def add_feedback(self, value: RetrievalFeedback) -> RetrievalFeedback:
        self.feedback[value.feedback_id] = value
        return value

    def clear(self) -> None:
        self.quality_assessments.clear()
        self.assignments.clear()
        self.comments.clear()
        self.subscriptions.clear()
        self.refresh_runs.clear()
        self.feedback.clear()

    def close(self) -> None:
        return None


class SqlAlchemyKnowledgeOperationsStore(InMemoryKnowledgeOperationsStore):
    def __init__(self, database_url: str, *, create_schema: bool = True) -> None:
        super().__init__()
        self.database_url = database_url
        self._prepare_sqlite_directory(database_url)
        self.engine = self._build_engine(database_url)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )
        if create_schema:
            Base.metadata.create_all(self.engine)
        self.reload()

    @staticmethod
    def _build_engine(database_url: str) -> Engine:
        url = make_url(database_url)
        connect_args: dict[str, object] = {}
        if url.get_backend_name() == "sqlite":
            connect_args["check_same_thread"] = False
        return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)

    @staticmethod
    def _prepare_sqlite_directory(database_url: str) -> None:
        url = make_url(database_url)
        if url.get_backend_name() != "sqlite":
            return
        database = url.database
        if not database or database == ":memory:":
            return
        Path(database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    def reload(self) -> None:
        with self.session_factory() as session:
            quality = list(session.scalars(select(QualityAssessmentRow)))
            assignments = list(session.scalars(select(ReviewAssignmentRow)))
            comments = list(session.scalars(select(ReviewCommentRow)))
            subscriptions = list(session.scalars(select(SourceSubscriptionRow)))
            runs = list(session.scalars(select(SourceRefreshRunRow)))
            feedback = list(session.scalars(select(RetrievalFeedbackRow)))
        self.quality_assessments = {
            row.assessment_id: QualityAssessment.model_validate_json(row.payload)
            for row in quality
        }
        self.assignments = {
            row.assignment_id: ReviewAssignment.model_validate_json(row.payload)
            for row in assignments
        }
        self.comments = {
            row.comment_id: ReviewComment.model_validate_json(row.payload)
            for row in comments
        }
        self.subscriptions = {
            row.subscription_id: SourceSubscription.model_validate_json(row.payload)
            for row in subscriptions
        }
        self.refresh_runs = {
            row.run_id: SourceRefreshRun.model_validate_json(row.payload)
            for row in runs
        }
        self.feedback = {
            row.feedback_id: RetrievalFeedback.model_validate_json(row.payload)
            for row in feedback
        }

    def add_quality(self, value: QualityAssessment) -> QualityAssessment:
        super().add_quality(value)
        self._merge(
            QualityAssessmentRow(
                assessment_id=value.assessment_id,
                tenant_id=value.tenant_id,
                actor=value.actor,
                disposition=value.disposition.value,
                input_hash=value.input_hash,
                payload=value.model_dump_json(),
                created_at=value.created_at,
            )
        )
        return value

    def add_assignment(self, value: ReviewAssignment) -> ReviewAssignment:
        super().add_assignment(value)
        self._merge(
            ReviewAssignmentRow(
                assignment_id=value.assignment_id,
                tenant_id=value.tenant_id,
                review_item_id=value.review_item_id,
                assignee=value.assignee,
                status=value.status.value,
                payload=value.model_dump_json(),
                updated_at=value.updated_at,
            )
        )
        return value

    def add_comment(self, value: ReviewComment) -> ReviewComment:
        super().add_comment(value)
        self._merge(
            ReviewCommentRow(
                comment_id=value.comment_id,
                tenant_id=value.tenant_id,
                review_item_id=value.review_item_id,
                author=value.author,
                payload=value.model_dump_json(),
                created_at=value.created_at,
            )
        )
        return value

    def add_subscription(self, value: SourceSubscription) -> SourceSubscription:
        super().add_subscription(value)
        self._merge(
            SourceSubscriptionRow(
                subscription_id=value.subscription_id,
                tenant_id=value.tenant_id,
                connector_type=value.connector_type.value,
                status=value.status.value,
                payload=value.model_dump_json(),
                updated_at=value.updated_at,
            )
        )
        return value

    def add_refresh_run(self, value: SourceRefreshRun) -> SourceRefreshRun:
        super().add_refresh_run(value)
        self._merge(
            SourceRefreshRunRow(
                run_id=value.run_id,
                tenant_id=value.tenant_id,
                subscription_id=value.subscription_id,
                status=value.status.value,
                payload=value.model_dump_json(),
                completed_at=value.completed_at,
            )
        )
        return value

    def add_feedback(self, value: RetrievalFeedback) -> RetrievalFeedback:
        super().add_feedback(value)
        self._merge(
            RetrievalFeedbackRow(
                feedback_id=value.feedback_id,
                tenant_id=value.tenant_id,
                actor=value.actor,
                label=value.label.value,
                payload=value.model_dump_json(),
                created_at=value.created_at,
            )
        )
        return value

    def clear(self) -> None:
        super().clear()
        with self.session_factory.begin() as session:
            for row in (
                RetrievalFeedbackRow,
                SourceRefreshRunRow,
                SourceSubscriptionRow,
                ReviewCommentRow,
                ReviewAssignmentRow,
                QualityAssessmentRow,
            ):
                session.execute(delete(row))

    def _merge(self, row: object) -> None:
        with self.session_factory.begin() as session:
            session.merge(row)

    def close(self) -> None:
        self.engine.dispose()
