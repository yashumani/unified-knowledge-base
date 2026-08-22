from __future__ import annotations

import argparse
import json
import os
import sys

from ukb.talk2data.client import Talk2DataMemoryClient
from ukb.talk2data.models import DomainFit
from ukb.talk2data.orchestrator import Talk2DataDecisionOrchestrator

QUESTIONS: list[tuple[str, DomainFit]] = [
    ("What was postpaid churn by plan last month?", DomainFit.in_domain),
    ("What is our restaurant food-cost margin by location?", DomainFit.excluded),
    (
        "Did restaurant foot traffic near our stores affect mobile activations?",
        DomainFit.external_adjacent,
    ),
    (
        "Did food-delivery application traffic contribute to evening network congestion?",
        DomainFit.external_adjacent,
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exercise the Talk2Data governed-memory consumer contract."
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("UKB_API_BASE_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument(
        "--token",
        default=os.getenv("UKB_API_TOKEN", "dev-token-change-me"),
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    failures: list[str] = []
    decisions: list[dict] = []
    with Talk2DataMemoryClient(
        base_url=args.base_url,
        token=args.token,
        timeout_seconds=args.timeout,
    ) as client:
        orchestrator = Talk2DataDecisionOrchestrator(client)
        for question, expected in QUESTIONS:
            decision = orchestrator.evaluate(question)
            decisions.append(decision.model_dump(mode="json"))
            if decision.domain_classification != expected:
                failures.append(
                    f"{question!r}: expected {expected.value}, received "
                    f"{decision.domain_classification.value}"
                )
            if expected == DomainFit.excluded and decision.may_proceed:
                failures.append(f"{question!r}: excluded question was allowed to proceed")

    print(json.dumps({"decisions": decisions, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
