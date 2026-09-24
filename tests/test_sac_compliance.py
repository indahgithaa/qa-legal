"""Tests for automatic SAC-H+ implementation checks."""

from src.evaluation import validate_sac_compliance


def test_sac_compliance_accepts_ordered_covered_document() -> None:
    facts = "Fakta " + ("x " * 80)
    analysis = "Menimbang. analisis hukum. "
    conclusion = "MENGADILI. putusan akhir."
    text = facts + analysis + conclusion
    facts_end = len(facts)
    analysis_end = facts_end + len(analysis)
    pages = [
        {
            "document_id": "doc-1",
            "page_number": 1,
            "clean_text": text,
        }
    ]
    sections = [
        _section("fakta", "Fakta", 0, facts_end, text),
        _section("pertimbangan_hukum", "Menimbang", facts_end, analysis_end, text),
        _section("amar_putusan", "MENGADILI", analysis_end, len(text), text),
    ]
    chunks = [
        _chunk("facts", "fakta", 0, facts_end, text),
        _chunk("analysis", "pertimbangan_hukum", facts_end, analysis_end, text),
        _chunk("conclusion", "amar_putusan", analysis_end, len(text), text),
    ]

    result = validate_sac_compliance(pages, sections, chunks, max_words=100)

    assert result["passed"] is True
    assert all(result["checks"].values())


def _section(
    label: str, heading: str, start: int, end: int, text: str
) -> dict[str, object]:
    return {
        "document_id": "doc-1",
        "section_label": label,
        "section_heading": heading,
        "start_position": start,
        "end_position": end,
        "section_text": text[start:end],
    }


def _chunk(
    chunk_id: str, label: str, start: int, end: int, text: str
) -> dict[str, object]:
    return {
        "chunk_id": chunk_id,
        "document_id": "doc-1",
        "strategy": "structure_aware",
        "section_label": label,
        "start_position": start,
        "end_position": end,
        "text": text[start:end],
    }
