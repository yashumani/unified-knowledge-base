from __future__ import annotations

import argparse
import json
import sys

from ukb.api.security import Principal
from ukb.config import get_settings
from ukb.models import Sensitivity
from ukb.store import store as legacy_store
from ukb.talk2data.backfill import LegacyKnowledgeBackfill
from ukb.talk2data.runtime import service


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill published legacy KnowledgeObjects into governed typed memory."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Write canonical episodes and typed memory. Default is a dry run.",
    )
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--actor", default="backfill.operator")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    settings = get_settings()
    principal = Principal(
        subject=args.actor,
        tenant_id=args.tenant_id or settings.default_tenant_id,
        roles=frozenset(
            {
                "consumer",
                "submitter",
                "reviewer",
                "publisher",
                "source_admin",
                "index_admin",
                "governance_admin",
            }
        ),
        clearance=Sensitivity.restricted,
        auth_method="local-backfill",
    )
    report = LegacyKnowledgeBackfill(
        legacy_store=legacy_store,
        service=service,
    ).run(
        principal=principal,
        dry_run=not args.execute,
        limit=args.limit,
    )
    print(json.dumps(report.model_dump(mode="json"), indent=2))
    if report.failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
