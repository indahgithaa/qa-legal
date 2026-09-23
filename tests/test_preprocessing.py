"""Tests for page extraction and conservative text cleaning."""

from pathlib import Path

import pymupdf as fitz

from src.preprocessing import PDFExtractor, TextCleaner


def test_text_cleaner_normalizes_without_flattening_lines() -> None:
    cleaner = TextCleaner()
    text = "  P U T U S A N  \r\nperka-\nra pidana\t  "

    assert cleaner.clean(text) == "P U T U S A N\nperkara pidana"


def test_pdf_extractor_returns_page_metadata(tmp_path: Path) -> None:
    pdf_path = tmp_path / "Putusan Contoh.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "MENGADILI")
    document.save(pdf_path)
    document.close()

    pages = PDFExtractor().extract_file(pdf_path, source_root=tmp_path)

    assert len(pages) == 1
    assert pages[0].filename == "Putusan Contoh.pdf"
    assert pages[0].page_number == 1
    assert "MENGADILI" in pages[0].raw_text
    assert pages[0].document_id.startswith("putusan-contoh-")

