"""Create a stratified pilot-question annotation sheet."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

from src.utils.io import read_jsonl


REQUIRED_LABELS = {"fakta", "pertimbangan_hukum", "amar_putusan"}
FIELDNAMES = [
    "query_id",
    "document_id",
    "target_section_label",
    "question",
    "reference_answer",
    "evidence_start_position",
    "evidence_end_position",
    "difficulty",
    "review_status",
    "notes",
]


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Create the exploration retrieval-question template."
    )
    parser.add_argument(
        "--sections",
        type=Path,
        default=Path("data/processed/exploration_20/sections.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation/exploration_20_questions.csv"),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing annotation sheet.",
    )
    args = parser.parse_args(argv)

    if args.output.exists() and not args.overwrite:
        raise FileExistsError(
            f"Refusing to replace {args.output}; pass --overwrite if intentional"
        )

    rows = build_question_rows(list(read_jsonl(args.sections)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} question slots to {args.output}")


def build_question_rows(sections: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Return four stratified question slots for every eligible document."""
    labels_by_document: dict[str, set[str]] = defaultdict(set)
    for section in sections:
        labels_by_document[str(section["document_id"])].add(
            str(section["section_label"])
        )

    rows: list[dict[str, str]] = []
    for document_index, document_id in enumerate(sorted(labels_by_document), start=1):
        labels = labels_by_document[document_id]
        missing = REQUIRED_LABELS - labels
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"{document_id} lacks required sections: {missing_text}")
        administrative = (
            "identitas_terdakwa"
            if document_index % 2
            else "riwayat_penahanan"
        )
        if administrative not in labels:
            raise ValueError(f"{document_id} lacks section: {administrative}")

        for question_index, label in enumerate(
            (administrative, "fakta", "pertimbangan_hukum", "amar_putusan"),
            start=1,
        ):
            rows.append(
                {
                    "query_id": f"pilot-{document_index:02d}-{question_index}",
                    "document_id": document_id,
                    "target_section_label": label,
                    "question": "",
                    "reference_answer": "",
                    "evidence_start_position": "",
                    "evidence_end_position": "",
                    "difficulty": "",
                    "review_status": "",
                    "notes": "",
                }
            )
    return rows


if __name__ == "__main__":
    main()
