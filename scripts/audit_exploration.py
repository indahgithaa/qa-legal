"""Audit detected sections and chunk outputs before retrieval experiments."""

from __future__ import annotations

import argparse
import csv
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from src.utils.io import read_jsonl


EXPECTED_LABELS = (
    "kepala_putusan",
    "identitas_terdakwa",
    "riwayat_penahanan",
    "fakta",
    "pertimbangan_hukum",
    "amar_putusan",
    "penutup",
)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Audit exploration sections and compare fixed-size with structure-aware chunks."
    )
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
        "--fixed-chunks",
        type=Path,
        default=Path("data/chunks/exploration_20/fixed_size/chunks.jsonl"),
    )
    parser.add_argument(
        "--structure-chunks",
        type=Path,
        default=Path("data/chunks/exploration_20/structure_aware/chunks.jsonl"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("experiments/results/exploration_20_audit.md"),
    )
    parser.add_argument(
        "--annotation-template",
        type=Path,
        default=Path("experiments/results/exploration_20_structure_review.csv"),
    )
    parser.add_argument(
        "--overwrite-annotation-template",
        action="store_true",
        help="Replace an existing review file. By default, completed manual work is preserved.",
    )
    args = parser.parse_args(argv)

    pages = list(read_jsonl(args.pages))
    sections = list(read_jsonl(args.sections))
    fixed_chunks = list(read_jsonl(args.fixed_chunks))
    structure_chunks = list(read_jsonl(args.structure_chunks))
    audit = build_audit(pages, sections, fixed_chunks, structure_chunks)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(audit), encoding="utf-8", newline="\n")
    print(f"Wrote audit report to {args.report}")
    if args.annotation_template.exists() and not args.overwrite_annotation_template:
        print(f"Preserved existing annotation template at {args.annotation_template}")
    else:
        write_annotation_template(args.annotation_template, audit)
        print(f"Wrote annotation template to {args.annotation_template}")


def build_audit(
    pages: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    fixed_chunks: list[dict[str, Any]],
    structure_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    pages_by_document = _group(pages, "document_id")
    sections_by_document = _group(sections, "document_id")
    fixed_by_document = _group(fixed_chunks, "document_id")
    structure_by_document = _group(structure_chunks, "document_id")
    document_ids = sorted(pages_by_document)
    expected_documents = set(document_ids)

    for name, grouped in (
        ("sections", sections_by_document),
        ("fixed-size chunks", fixed_by_document),
        ("structure-aware chunks", structure_by_document),
    ):
        actual_documents = set(grouped)
        if actual_documents != expected_documents:
            missing = sorted(expected_documents - actual_documents)
            extra = sorted(actual_documents - expected_documents)
            raise ValueError(f"Document mismatch for {name}; missing={missing}, extra={extra}")

    documents: list[dict[str, Any]] = []
    label_documents: Counter[str] = Counter()
    label_sections: Counter[str] = Counter()
    label_words: Counter[str] = Counter()
    total_section_words = 0
    integrity_checks = 0

    for document_id in document_ids:
        document_pages = sorted(
            pages_by_document[document_id], key=lambda row: int(row["page_number"])
        )
        document_text = "\n\n".join(str(row.get("clean_text", "")) for row in document_pages)
        document_sections = sorted(
            sections_by_document[document_id], key=lambda row: int(row["start_position"])
        )
        _validate_sections(document_id, document_text, document_sections)
        integrity_checks += 1

        section_labels = {str(row["section_label"]) for row in document_sections}
        for label in section_labels:
            label_documents[label] += 1
        for section in document_sections:
            label = str(section["section_label"])
            words = _word_count(str(section.get("section_text", "")))
            label_sections[label] += 1
            label_words[label] += words
            total_section_words += words

        for chunk in fixed_by_document[document_id] + structure_by_document[document_id]:
            _validate_chunk(document_id, document_text, chunk)
            integrity_checks += 1
        _validate_structure_chunks(
            document_id,
            sections=document_sections,
            chunks=structure_by_document[document_id],
        )
        integrity_checks += len(structure_by_document[document_id])

        detected = {str(row["section_label"]): row for row in document_sections}
        main_words = sum(
            _word_count(str(row.get("section_text", "")))
            for row in document_sections
            if str(row["section_label"]) == "pertimbangan_hukum"
        )
        document_words = _word_count(document_text)
        documents.append(
            {
                "document_id": document_id,
                "filename": str(document_pages[0].get("filename", "")),
                "pages": len(document_pages),
                "words": document_words,
                "sections": document_sections,
                "detected": detected,
                "missing_labels": [label for label in EXPECTED_LABELS if label not in detected],
                "pertimbangan_share": main_words / document_words if document_words else 0.0,
            }
        )

    fixed_crossings = _boundary_crossings(fixed_chunks, sections_by_document)
    structure_crossings = _boundary_crossings(structure_chunks, sections_by_document)
    label_order = list(EXPECTED_LABELS) + sorted(set(label_sections) - set(EXPECTED_LABELS))

    return {
        "documents": documents,
        "document_count": len(document_ids),
        "page_count": len(pages),
        "word_count": sum(document["words"] for document in documents),
        "section_count": len(sections),
        "integrity_checks": integrity_checks,
        "label_stats": [
            {
                "label": label,
                "documents": label_documents[label],
                "sections": label_sections[label],
                "words": label_words[label],
                "word_share": label_words[label] / total_section_words if total_section_words else 0.0,
            }
            for label in label_order
        ],
        "chunk_stats": [
            _chunk_stats("fixed_size", fixed_chunks, fixed_crossings),
            _chunk_stats("structure_aware", structure_chunks, structure_crossings),
        ],
        "pertimbangan_median_share": statistics.median(
            document["pertimbangan_share"] for document in documents
        ),
    }


def render_report(audit: dict[str, Any]) -> str:
    document_count = int(audit["document_count"])
    label_by_name = {row["label"]: row for row in audit["label_stats"]}
    facts_documents = int(label_by_name.get("fakta", {}).get("documents", 0))
    facts_share = float(label_by_name.get("fakta", {}).get("word_share", 0.0))
    analysis_share = float(
        label_by_name.get("pertimbangan_hukum", {}).get("word_share", 0.0)
    )
    conclusion_share = sum(
        float(label_by_name.get(label, {}).get("word_share", 0.0))
        for label in ("amar_putusan", "penutup")
    )
    missing_rows = [
        (document["filename"], ", ".join(document["missing_labels"]))
        for document in audit["documents"]
        if document["missing_labels"]
    ]

    lines = [
        "# Audit eksplorasi 20 dokumen",
        "",
        "Audit ini memeriksa kelengkapan artefak, cakupan deteksi section, dan distribusi "
        "chunk sebelum konfigurasi dibekukan untuk eksperimen retrieval.",
        "",
        "## Ringkasan corpus",
        "",
        f"- Dokumen: {document_count}",
        f"- Halaman: {audit['page_count']}",
        f"- Kata (sebelum overlap chunk): {audit['word_count']:,}",
        f"- Section terdeteksi: {audit['section_count']}",
        f"- Pemeriksaan integritas yang lulus: {audit['integrity_checks']:,}",
        "",
        "## Cakupan section",
        "",
        "| Label | Dokumen | Section | Kata | Bagian corpus |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in audit["label_stats"]:
        lines.append(
            f"| `{row['label']}` | {row['documents']}/{document_count} | {row['sections']} | "
            f"{row['words']:,} | {row['word_share']:.1%} |"
        )

    lines.extend(
        [
            "",
            "## Distribusi chunk",
            "",
            "| Strategi | Chunk | Rata-rata kata | Median | Min–maks | <50 kata | Melintasi batas section |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in audit["chunk_stats"]:
        lines.append(
            f"| `{row['strategy']}` | {row['count']} | {row['mean_words']:.1f} | "
            f"{row['median_words']:.1f} | {row['min_words']}–{row['max_words']} | "
            f"{row['short_chunks']} ({row['short_share']:.1%}) | "
            f"{row['boundary_crossings']} ({row['crossing_share']:.1%}) |"
        )

    lines.extend(
        [
            "",
            "## Temuan yang harus diselesaikan",
            "",
            f"- Label `fakta` terdeteksi pada {facts_documents}/{document_count} dokumen dan mencakup "
            f"{facts_share:.1%} corpus; `pertimbangan_hukum` mencakup {analysis_share:.1%}; "
            f"serta `amar_putusan` bersama `penutup` mencakup {conclusion_share:.1%}.",
            f"- Median bagian per dokumen yang diberi label `pertimbangan_hukum` adalah "
            f"{audit['pertimbangan_median_share']:.1%}. Distribusi ini jauh lebih terurai daripada "
            "detector berbasis kemunculan pertama `Menimbang`, tetapi akurasi batas tetap memerlukan "
            "anotasi acuan.",
            "- Structure-aware chunking tidak melintasi batas section terdeteksi. Chunk panjang di "
            "dalam section memakai overlap dua kalimat untuk menjaga kesinambungan lokal sesuai SAC-H+.",
            "",
            "## Label yang tidak terdeteksi per dokumen",
            "",
            "| Dokumen | Label tidak terdeteksi |",
            "|---|---|",
        ]
    )
    for filename, missing in missing_rows:
        lines.append(f"| {filename} | {missing} |")

    lines.extend(
        [
            "",
            "## Keputusan milestone",
            "",
            "Konfigurasi deteksi struktur belum siap dibekukan. Isi lembar "
            "`exploration_20_structure_review.csv` dengan protokol di "
            "`experiments/structure_validation_protocol.md`, perbaiki detector berdasarkan kesalahan "
            "yang teramati, lalu jalankan audit ulang. Pembangunan embedding dan retrieval dimulai "
            "setelah kriteria penerimaan validasi terpenuhi.",
            "",
        ]
    )
    return "\n".join(lines)


def write_annotation_template(path: Path, audit: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "document_id",
        "filename",
        "section_label",
        "detected",
        "detected_heading",
        "detected_start_position",
        "detected_word_count",
        "review_status",
        "gold_heading",
        "reviewer_notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for document in audit["documents"]:
            for label in EXPECTED_LABELS:
                detected = document["detected"].get(label)
                writer.writerow(
                    {
                        "document_id": document["document_id"],
                        "filename": document["filename"],
                        "section_label": label,
                        "detected": "yes" if detected else "no",
                        "detected_heading": detected.get("section_heading", "") if detected else "",
                        "detected_start_position": detected.get("start_position", "") if detected else "",
                        "detected_word_count": (
                            _word_count(str(detected.get("section_text", ""))) if detected else ""
                        ),
                        "review_status": "",
                        "gold_heading": "",
                        "reviewer_notes": "",
                    }
                )


def _group(rows: Iterable[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    return dict(grouped)


def _validate_sections(
    document_id: str, document_text: str, sections: list[dict[str, Any]]
) -> None:
    cursor = 0
    for section in sections:
        start = int(section["start_position"])
        end = int(section["end_position"])
        if start != cursor or not start < end:
            raise ValueError(
                f"Invalid section coverage for {document_id}: expected start {cursor}, got {start}:{end}"
            )
        if document_text[start:end] != str(section.get("section_text", "")):
            raise ValueError(f"Section text does not match offsets for {document_id} at {start}:{end}")
        cursor = end
    if cursor != len(document_text):
        raise ValueError(
            f"Sections do not cover {document_id}: stopped at {cursor} of {len(document_text)}"
        )


def _validate_chunk(document_id: str, document_text: str, chunk: dict[str, Any]) -> None:
    start = int(chunk["start_position"])
    end = int(chunk["end_position"])
    if not 0 <= start < end <= len(document_text):
        raise ValueError(f"Invalid chunk offsets for {document_id}: {start}:{end}")
    if document_text[start:end] != str(chunk.get("text", "")):
        raise ValueError(f"Chunk text does not match offsets for {document_id} at {start}:{end}")


def _validate_structure_chunks(
    document_id: str,
    *,
    sections: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> None:
    for chunk in chunks:
        start = int(chunk["start_position"])
        end = int(chunk["end_position"])
        containing = [
            section
            for section in sections
            if int(section["start_position"]) <= start and end <= int(section["end_position"])
        ]
        if len(containing) != 1:
            raise ValueError(f"Structure-aware chunk crosses a section in {document_id}: {start}:{end}")
        if chunk.get("section_label") != containing[0].get("section_label"):
            raise ValueError(f"Structure-aware chunk has the wrong label in {document_id}: {start}:{end}")


def _boundary_crossings(
    chunks: list[dict[str, Any]], sections_by_document: dict[str, list[dict[str, Any]]]
) -> int:
    crossings = 0
    for chunk in chunks:
        start = int(chunk["start_position"])
        end = int(chunk["end_position"])
        boundaries = {
            int(section["start_position"])
            for section in sections_by_document[str(chunk["document_id"])]
        }
        if any(start < boundary < end for boundary in boundaries):
            crossings += 1
    return crossings


def _chunk_stats(
    strategy: str, chunks: list[dict[str, Any]], boundary_crossings: int
) -> dict[str, Any]:
    word_counts = [_word_count(str(chunk.get("text", ""))) for chunk in chunks]
    short_chunks = sum(count < 50 for count in word_counts)
    return {
        "strategy": strategy,
        "count": len(chunks),
        "mean_words": statistics.mean(word_counts),
        "median_words": statistics.median(word_counts),
        "min_words": min(word_counts),
        "max_words": max(word_counts),
        "short_chunks": short_chunks,
        "short_share": short_chunks / len(chunks),
        "boundary_crossings": boundary_crossings,
        "crossing_share": boundary_crossings / len(chunks),
    }


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


if __name__ == "__main__":
    main()
