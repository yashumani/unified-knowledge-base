from __future__ import annotations

import argparse
import json
from pathlib import Path

from ukb.operations.staging import load_env_file, validate_staging_environment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Unified Knowledge Base private-runtime environment before deployment."
    )
    parser.add_argument("--env-file", required=True, help="Path to the deployment .env file.")
    parser.add_argument(
        "--expected-ui-origin",
        default=None,
        help="HTTPS UI origin that must be present in UKB_CORS_ALLOW_ORIGINS.",
    )
    parser.add_argument("--require-oidc", action="store_true")
    parser.add_argument("--require-graphiti", action="store_true")
    parser.add_argument("--output", default=None, help="Optional JSON report path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        values = load_env_file(args.env_file)
        report = validate_staging_environment(
            values,
            environment_file=str(Path(args.env_file).resolve()),
            expected_ui_origin=args.expected_ui_origin,
            require_oidc=args.require_oidc,
            require_graphiti=args.require_graphiti,
        )
    except (OSError, ValueError) as exc:
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
