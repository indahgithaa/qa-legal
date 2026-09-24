"""Automatic checks for alignment with the published SAC-H+ procedure."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from src.evaluation.ground_truth import join_clean_pages


MACRO_LABELS = {
    "facts": "fakta",
    "analysis": "pertimbangan_hukum",
    "conclusion": "amar_putusan",
}


def validate_sac_compliance(
    pages: Sequence[Mapping[str, Any]],
    sections: Sequence[Mapping[str, Any]],
    chunks: Sequence[Mapping[str, Any]],
    *,
    conclusion_search_fraction: float = 0.20,
    max_words: int = 300,
) -> dict[str, Any]:
    """Check structural invariants and SAC-H+ method requirements.

    These checks establish implementation fidelity, not gold boundary accuracy.
    Accuracy and utility must be assessed through a stratified error audit and
    the downstream retrieval comparison.
    """
    documents = join_clean_pages(pages)
    sections_by_document = _group(sections, "document_id")
    chunks_by_document = _group(chunks, "document_id")
    failures: list[str] = []
    counts: Counter[str] = Counter()

    expected_documents = set(documents)
    for name, grouped in (("sections", sections_by_document), ("chunks", chunks_by_document)):
        missing = expected_documents - set(grouped)
        extra = set(grouped) - expected_documents
        if missing or extra:
            failures.append(
                f"{name}: document mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
            )

    for document_id, text in documents.items():
        document_sections = sorted(
            sections_by_document.get(document_id, []),
            key=lambda row: int(row["start_position"]),
        )
        document_chunks = sorted(
            chunks_by_document.get(document_id, []),
            key=lambda row: (int(row["start_position"]), int(row["end_position"])),
        )
        if _check_section_coverage(document_id, text, document_sections, failures):
            counts["section_coverage"] += 1
        boundaries = _macro_boundaries(document_id, document_sections, failures)
        if boundaries:
            facts, analysis, conclusion = boundaries
            counts["three_strata"] += 1
            if facts < analysis < conclusion:
                counts["ordered_strata"] += 1
            else:
                failures.append(f"{document_id}: rhetorical strata are out of order")

            tail_start = int(len(text) * (1 - conclusion_search_fraction))
            if conclusion >= tail_start:
                counts["conclusion_in_tail"] += 1
            else:
                failures.append(
                    f"{document_id}: conclusion starts before the final "
                    f"{conclusion_search_fraction:.0%}"
                )

            analysis_section = next(
                row
                for row in document_sections
                if str(row["section_label"]) == MACRO_LABELS["analysis"]
            )
            conclusion_section = next(
                row
                for row in document_sections
                if str(row["section_label"]) == MACRO_LABELS["conclusion"]
            )
            if _is_analysis_trigger(str(analysis_section.get("section_heading", ""))):
                counts["analysis_trigger"] += 1
            else:
                failures.append(f"{document_id}: analysis boundary lacks a high-precision trigger")
            if _is_conclusion_trigger(str(conclusion_section.get("section_heading", ""))):
                counts["conclusion_trigger"] += 1
            else:
                failures.append(f"{document_id}: conclusion boundary lacks a high-precision trigger")

        _check_chunks(
            document_id,
            text,
            document_sections,
            document_chunks,
            max_words=max_words,
            failures=failures,
            counts=counts,
        )

    document_count = len(documents)
    checks = {
        "full_section_coverage": counts["section_coverage"] == document_count,
        "three_rhetorical_strata": counts["three_strata"] == document_count,
        "ordered_rhetorical_strata": counts["ordered_strata"] == document_count,
        "conclusion_in_final_window": counts["conclusion_in_tail"] == document_count,
        "high_precision_analysis_trigger": counts["analysis_trigger"] == document_count,
        "high_precision_conclusion_trigger": counts["conclusion_trigger"] == document_count,
        "chunks_within_sections": counts["valid_chunk_documents"] == document_count,
        "chunk_text_covered": counts["chunk_coverage"] == document_count,
        "intra_section_overlap": counts["overlap_failures"] == 0,
    }
    return {
        "document_count": document_count,
        "chunk_count": len(chunks),
        "checks": checks,
        "passed": all(checks.values()) and not failures,
        "failures": failures,
        "counts": dict(counts),
        "conclusion_search_fraction": conclusion_search_fraction,
        "max_words": max_words,
    }


def render_sac_compliance(result: Mapping[str, Any]) -> str:
    """Render a concise, auditable Markdown compliance report."""
    descriptions = {
        "full_section_coverage": "Section mempertahankan seluruh karakter dokumen",
        "three_rhetorical_strata": "Facts, Arguments & Analysis, Conclusion tersedia",
        "ordered_rhetorical_strata": "Tiga strata berada dalam urutan kanonik",
        "conclusion_in_final_window": "Conclusion ditemukan pada 20% akhir dokumen",
        "high_precision_analysis_trigger": "Batas analysis memakai trigger presisi tinggi",
        "high_precision_conclusion_trigger": "Batas conclusion memakai trigger presisi tinggi",
        "chunks_within_sections": "Chunk tidak melintasi batas section",
        "chunk_text_covered": "Isi non-spasi setiap section tercakup chunk",
        "intra_section_overlap": "Chunk berurutan dalam section memiliki overlap",
    }
    lines = [
        "# Validasi kepatuhan SAC-H+",
        "",
        "Acuan metode: Sonowal dan Sadhu (2025), [*Structure-Aware Chunking for "
        "Abstractive Summarization of Long Legal Documents*]"
        "(https://aclanthology.org/2025.justnlp-main.19/).",
        "",
        f"Dokumen: {result['document_count']}  ",
        f"Chunk: {result['chunk_count']}  ",
        f"Hasil: **{'LULUS' if result['passed'] else 'BELUM LULUS'}**",
        "",
        "| Pemeriksaan | Hasil |",
        "|---|---|",
    ]
    for name, passed in result["checks"].items():
        lines.append(f"| {descriptions[name]} | {'LULUS' if passed else 'GAGAL'} |")
    lines.extend(["", "## Kegagalan", ""])
    failures = list(result["failures"])
    lines.extend(f"- {failure}" for failure in failures)
    if not failures:
        lines.append("Tidak ada kegagalan otomatis.")
    lines.extend(
        [
            "",
            "## Interpretasi",
            "",
            "Laporan ini membuktikan implementasi mengikuti mekanisme SAC-H+: cascade "
            "top-down, tiga strata retoris, tail anchor, dan chunk dalam section dengan "
            "overlap. Laporan ini tidak menjadikan paper sebagai ground truth batas "
            "putusan Indonesia. Efektivitas dinilai dengan benchmark retrieval berpasangan; "
            "audit manual digunakan untuk analisis error, bukan sebagai penghambat pipeline.",
            "",
        ]
    )
    return "\n".join(lines)


def _group(
    rows: Sequence[Mapping[str, Any]], key: str
) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    return dict(grouped)


def _check_section_coverage(
    document_id: str,
    text: str,
    sections: Sequence[Mapping[str, Any]],
    failures: list[str],
) -> bool:
    cursor = 0
    for section in sections:
        start = int(section["start_position"])
        end = int(section["end_position"])
        if start != cursor or not start < end or text[start:end] != str(section.get("section_text", "")):
            failures.append(f"{document_id}: invalid section coverage at {start}:{end}")
            return False
        cursor = end
    if cursor != len(text):
        failures.append(f"{document_id}: sections stop at {cursor} of {len(text)}")
        return False
    return True


def _macro_boundaries(
    document_id: str,
    sections: Sequence[Mapping[str, Any]],
    failures: list[str],
) -> tuple[int, int, int] | None:
    positions: dict[str, list[int]] = defaultdict(list)
    for section in sections:
        positions[str(section["section_label"])].append(int(section["start_position"]))
    missing = [label for label in MACRO_LABELS.values() if len(positions[label]) != 1]
    if missing:
        failures.append(f"{document_id}: missing or repeated macro labels: {missing}")
        return None
    return (
        positions[MACRO_LABELS["facts"]][0],
        positions[MACRO_LABELS["analysis"]][0],
        positions[MACRO_LABELS["conclusion"]][0],
    )


def _check_chunks(
    document_id: str,
    text: str,
    sections: Sequence[Mapping[str, Any]],
    chunks: Sequence[Mapping[str, Any]],
    *,
    max_words: int,
    failures: list[str],
    counts: Counter[str],
) -> None:
    valid = True
    covered = bytearray(len(text))
    by_section: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for chunk in chunks:
        start = int(chunk["start_position"])
        end = int(chunk["end_position"])
        containing = [
            section
            for section in sections
            if int(section["start_position"]) <= start < end <= int(section["end_position"])
        ]
        if (
            len(containing) != 1
            or text[start:end] != str(chunk.get("text", ""))
            or len(re.findall(r"\S+", str(chunk.get("text", "")))) > max_words
        ):
            failures.append(f"{document_id}: invalid chunk at {start}:{end}")
            valid = False
            continue
        covered[start:end] = b"\x01" * (end - start)
        key = (int(containing[0]["start_position"]), int(containing[0]["end_position"]))
        by_section[key].append((start, end))
    if valid:
        counts["valid_chunk_documents"] += 1
    if all(character.isspace() or covered[index] for index, character in enumerate(text)):
        counts["chunk_coverage"] += 1
    else:
        failures.append(f"{document_id}: chunks leave non-space text uncovered")

    for spans in by_section.values():
        ordered = sorted(spans)
        for previous, current in zip(ordered, ordered[1:]):
            if current[0] >= previous[1]:
                counts["overlap_failures"] += 1
                failures.append(
                    f"{document_id}: adjacent chunks lack overlap at "
                    f"{previous[0]}:{previous[1]} -> {current[0]}:{current[1]}"
                )


def _is_analysis_trigger(heading: str) -> bool:
    normalized = " ".join(heading.lower().split())
    return normalized.startswith("menimbang") or "pertimbangan hukum" in normalized


def _is_conclusion_trigger(heading: str) -> bool:
    compact = re.sub(r"\s+", "", heading).lower().rstrip(":")
    return compact in {"mengadili", "amarputusan"}
