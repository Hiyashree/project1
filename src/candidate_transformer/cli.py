from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import load_config, run_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Multi-Source Candidate Data Transformer — merge messy inputs into clean profiles.",
    )
    parser.add_argument(
        "sources",
        nargs="+",
        help="Input files (CSV, JSON, PDF/DOCX resume, recruiter notes)",
    )
    parser.add_argument(
        "-c", "--config",
        type=Path,
        help="Output projection config JSON (default: full canonical schema)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Write JSON output to file instead of stdout",
    )
    parser.add_argument(
        "--candidate-id",
        help="Filter CSV row or tag merged profile with this ID",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Pretty-print JSON (default: true)",
    )

    args = parser.parse_args(argv)
    source_paths = [Path(s) for s in args.sources]

    for path in source_paths:
        if not path.exists():
            print(f"Error: source not found: {path}", file=sys.stderr)
            return 1

    try:
        config = load_config(args.config)
        result = run_pipeline(source_paths, args.candidate_id, config)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    indent = 2 if args.pretty else None
    payload = json.dumps(result, indent=indent, ensure_ascii=False)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(payload)

    if result.get("_validation_errors"):
        print("Validation warnings:", result["_validation_errors"], file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
