"""Validate the exploration output against the published SAC-H+ mechanism."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from src.evaluation.sac_compliance import render_sac_compliance, validate_sac_compliance
from src.utils.io import read_jsonl


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate SAC-H+ method compliance.")
    parser.add_argument(
        "--pages",
        type=Path,
        default=Path("data/processed/exploration_20/pages.jsonl"),
    )
    parser.add_argument(
        "--sections",
        type=Path,
        default=Path("data/processed/exploration_20/sections.jsonl"),
    )
    parser.add_argument(
        "--chunks",
        type=Path,
        default=Path("data/chunks/exploration_20/structure_aware/chunks.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("experiments/results/exploration_20_sac_compliance.md"),
    )
    parser.add_argument("--conclusion-search-fraction", type=float, default=0.20)
    parser.add_argument("--max-words", type=int, default=300)
    args = parser.parse_args(argv)

    result = validate_sac_compliance(
        list(read_jsonl(args.pages)),
        list(read_jsonl(args.sections)),
        list(read_jsonl(args.chunks)),
        conclusion_search_fraction=args.conclusion_search_fraction,
        max_words=args.max_words,
    )
    report = render_sac_compliance(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8", newline="\n")
    print(report, end="")
    print(f"Wrote SAC compliance report to {args.output}")
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
