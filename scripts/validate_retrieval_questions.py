"""Validate retrieval-question annotations and report completion."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Sequence

from src.evaluation.ground_truth import join_clean_pages, validate_questions
from src.utils.io import read_jsonl


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate retrieval questions.")
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path("data/evaluation/exploration_20_questions.csv"),
    )
    parser.add_argument(
        "--pages",
        type=Path,
        default=Path("data/processed/exploration_20/pages.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("experiments/results/exploration_20_question_validation.md"),
    )
    args = parser.parse_args(argv)

    with args.questions.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    documents = join_clean_pages(list(read_jsonl(args.pages)))
    result = validate_questions(rows, documents)
    report = render_report(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8", newline="\n")
    print(report, end="")
    print(f"Wrote validation report to {args.output}")
    if not result["valid"]:
        raise SystemExit(1)


def render_report(result: dict[str, object]) -> str:
    lines = [
        "# Validasi pertanyaan retrieval",
        "",
        f"Approved: {result['approved_count']}/{result['row_count']} "
        f"({result['completion']:.1%})",
        "",
        f"Status data: **{'SIAP' if result['ready'] else 'BELUM SIAP'}**.",
        "",
        "## Status review",
        "",
    ]
    lines.extend(
        f"- `{status}`: {count}"
        for status, count in dict(result["status_counts"]).items()
    )
    lines.extend(["", "## Error", ""])
    errors = list(result["errors"])
    lines.extend(f"- {error}" for error in errors)
    if not errors:
        lines.append("Tidak ada error pada baris yang sudah diisi.")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
