"""Tests for the structure-review context packet."""

from scripts.prepare_structure_review_context import (
    join_clean_pages,
    render_review_context,
)


def test_join_clean_pages_matches_pipeline_page_order() -> None:
    pages = [
        {"document_id": "doc-1", "page_number": 2, "clean_text": "second"},
        {"document_id": "doc-1", "page_number": 1, "clean_text": "first"},
    ]

    assert join_clean_pages(pages) == {"doc-1": "first\n\nsecond"}


def test_render_review_context_marks_and_escapes_boundary() -> None:
    rows = [
        {
            "document_id": "doc-1",
            "filename": "decision.pdf",
            "section_label": "amar_putusan",
            "detected": "yes",
            "detected_heading": "<MENGADILI>",
            "detected_start_position": "6",
            "detected_word_count": "2",
        }
    ]

    report = render_review_context(
        rows,
        {"doc-1": "beforeafter"},
        before_chars=6,
        after_chars=5,
    )

    assert "before\n\n&lt;&lt;&lt; BATAS TERDETEKSI &gt;&gt;&gt;\n\nafter" in report
    assert "&lt;MENGADILI&gt;" in report
