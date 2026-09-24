"""Score the manually reviewed structure-boundary annotation sheet."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Sequence

from src.evaluation.structure_metrics import render_structure_score, score_structure_review


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Score manual structure-boundary review.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("experiments/results/exploration_20_structure_review.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("experiments/results/exploration_20_structure_score.md"),
    )
    args = parser.parse_args(argv)

    with args.input.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    score = score_structure_review(rows)
    report = render_structure_score(score)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8", newline="\n")
    print(report, end="")
    print(f"Wrote structure score to {args.output}")


if __name__ == "__main__":
    main()
