"""Render detected boundaries with surrounding text for manual review."""

from __future__ import annotations

import argparse
import csv
from html import escape
from pathlib import Path
from typing import Any, Sequence

from src.evaluation.ground_truth import join_clean_pages
from src.utils.io import read_jsonl


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Create a readable context packet for structure-boundary review."
    )
    parser.add_argument(
        "--pages",
        type=Path,
        default=Path("data/processed/exploration_20/pages.jsonl"),
    )
    parser.add_argument(
        "--review",
        type=Path,
        default=Path("experiments/results/exploration_20_structure_review.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("experiments/results/exploration_20_structure_review_context.md"),
    )
    parser.add_argument("--before-chars", type=int, default=500)
    parser.add_argument("--after-chars", type=int, default=1200)
    args = parser.parse_args(argv)

    if args.before_chars < 0 or args.after_chars <= 0:
        raise ValueError("Context sizes must be non-negative, with after-chars above zero")

    documents = join_clean_pages(list(read_jsonl(args.pages)))
    with args.review.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    report = render_review_context(
        rows,
        documents,
        before_chars=args.before_chars,
        after_chars=args.after_chars,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8", newline="\n")
    print(f"Wrote context for {len(rows)} review rows to {args.output}")


def render_review_context(
    rows: list[dict[str, str]],
    documents: dict[str, str],
    *,
    before_chars: int,
    after_chars: int,
) -> str:
    """Render one marked context excerpt for every review row."""
    lines = [
        "# Konteks review batas struktur",
        "",
        "Gunakan dokumen ini untuk membaca konteks. Simpan keputusan pada file CSV "
        "review; jangan mengedit hasil detector di dokumen ini.",
        "",
    ]
    current_document = ""
    for row_number, row in enumerate(rows, start=2):
        document_id = str(row.get("document_id", ""))
        if document_id not in documents:
            raise ValueError(f"Review row references an unknown document: {document_id}")
        if document_id != current_document:
            current_document = document_id
            filename = str(row.get("filename", ""))
            lines.extend(
                [
                    f"## {escape(filename)}",
                    "",
                    f"Document ID: `{escape(document_id)}`",
                    "",
                ]
            )

        label = str(row.get("section_label", ""))
        detected = str(row.get("detected", "")).strip().lower()
        lines.extend(
            [
                f"### Baris CSV {row_number}: `{escape(label)}`",
                "",
                f"Detected: `{escape(detected)}`  ",
                f"Heading: {escape(str(row.get('detected_heading', '')))}  ",
                f"Word count: {escape(str(row.get('detected_word_count', '')))}",
                "",
            ]
        )
        if detected != "yes":
            lines.extend(
                [
                    "Detector tidak menemukan batas untuk label ini. Cari bagian tersebut pada "
                    "teks bersih untuk menentukan `missed` atau `not_applicable`.",
                    "",
                ]
            )
            continue

        try:
            position = int(str(row.get("detected_start_position", "")))
        except ValueError as error:
            raise ValueError(
                f"Invalid boundary position for {document_id} / {label}"
            ) from error
        document_text = documents[document_id]
        if not 0 <= position <= len(document_text):
            raise ValueError(
                f"Boundary outside document for {document_id} / {label}: {position}"
            )
        before = document_text[max(0, position - before_chars) : position]
        after = document_text[position : position + after_chars]
        marked = f"{before}\n\n<<< BATAS TERDETEKSI >>>\n\n{after}"
        lines.extend(["<pre>", escape(marked), "</pre>", ""])

    return "\n".join(lines)


if __name__ == "__main__":
    main()
