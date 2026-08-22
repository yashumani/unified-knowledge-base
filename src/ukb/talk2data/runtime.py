from __future__ import annotations

from ukb.config import get_settings
from ukb.talk2data.graph import (
    GraphitiTemporalGraphAdapter,
    InMemoryTemporalGraphAdapter,
    TemporalGraphAdapter,
)
from ukb.talk2data.service import Talk2DataService
from ukb.talk2data.store import build_talk2data_store

settings = get_settings()
store = build_talk2data_store(
    store_backend=settings.store_backend,
    database_url=settings.database_url,
    create_schema=settings.create_schema_on_startup,
)
graph: TemporalGraphAdapter
if settings.talk2data_graph_backend.casefold() == "graphiti":
    # A deployment integrates its approved Graphiti SDK/client through the
    # GraphitiClientProtocol. The canonical SQL store remains available even
    # when that optional projection is not configured.
    graph = GraphitiTemporalGraphAdapter(client=None)
else:
    graph = InMemoryTemporalGraphAdapter()
service = Talk2DataService(
    store=store,
    graph=graph,
    index_lag_tolerance_seconds=settings.talk2data_index_lag_tolerance_seconds,
)
