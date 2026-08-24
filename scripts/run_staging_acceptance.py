from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ukb.operations.staging import probe_staging_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run read-only acceptance probes against a deployed UKB private runtime."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument(
        "--token-env",
        default="UKB_API_TOKEN",
        help=(
            "Environment variable containing the bearer token. "
            "Tokens are never accepted on the command line."
        ),
    )
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--output", default=None, help="Optional JSON report path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.environ.get(args.token_env, "")
    if not token:
        print(
            json.dumps(
                {
                    "ready": False,
                    "error": f"Environment variable {args.token_env} is empty.",
                },
                indent=2,
            )
        )
        return 2

    try:
        report = probe_staging_runtime(
            base_url=args.base_url,
            token=token,
            timeout_seconds=args.timeout_seconds,
        )
    except ValueError as exc:
        print(json.dumps({"ready": False, "error": str(exc)}, indent=2))
        return 2

    payload = report.model_dump_json(indent=2)
    print(payload)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    return 0 if report.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
