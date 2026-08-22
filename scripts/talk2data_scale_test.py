from __future__ import annotations

import argparse
import json
import sys

from ukb.talk2data.scale import PROFILES, run_scale_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic governed-memory scale and tenant-isolation checks."
    )
    parser.add_argument("--profile", choices=sorted(PROFILES), default="ci")
    parser.add_argument(
        "--max-p95-ms",
        type=float,
        default=1500.0,
        help="Fail when governed query p95 exceeds this threshold.",
    )
    args = parser.parse_args()

    result = run_scale_benchmark(PROFILES[args.profile])
    payload = result.model_dump(mode="json")
    payload["latency_gate_ms"] = args.max_p95_ms
    payload["latency_gate_passed"] = result.query_p95_ms <= args.max_p95_ms
    print(json.dumps(payload, indent=2))
    if not result.passed or result.query_p95_ms > args.max_p95_ms:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
