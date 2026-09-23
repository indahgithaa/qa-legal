"""Tests for page extraction and conservative text cleaning."""

from pathlib import Path

import pymupdf as fitz

from src.preprocessing import PDFExtractor, TextCleaner


def test_text_cleaner_normalizes_without_flattening_lines() -> None:
    cleaner = TextCleaner()
    text = "  P U T U S A N  \r\nperka-\nra pidana\t  "

    assert cleaner.clean(text) == "P U T U S A N\nperkara pidana"


def test_text_cleaner_removes_ma_boilerplate_and_repairs_mojibake() -> None:
    cleaner = TextCleaner()
    text = """Direktori Putusan Mahkamah Agung Republik Indonesia
putusan.mahkamahagung.go.id

Terdakwa menyatakan â€œmenyesalâ€ dan mengajukan pembelaan.
Halaman 4 dari 22 Putusan Nomor 59/Pid.Sus/2024/PN Lsm
Disclaimer
Kepaniteraan Mahkamah Agung Republik Indonesia berusaha untuk selalu mencantumkan informasi paling kini dan akurat sebagai bentuk komitmen.
Email : kepaniteraan@mahkamahagung.go.id Telp : 021-384 3348 (ext.318)
MENGADILI
"""

    assert cleaner.clean(text) == "Terdakwa menyatakan “menyesal” dan mengajukan pembelaan.\nMENGADILI"


def test_text_cleaner_preserves_legal_reference_to_supreme_court() -> None:
    cleaner = TextCleaner()
    text = "Berdasarkan Putusan Mahkamah Agung Republik Indonesia Nomor 123 K/Pid/2024."

    assert cleaner.clean(text) == text


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


def test_pdf_extractor_excludes_rotated_watermark_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "Putusan Watermark.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "PERTIMBANGAN HUKUM")
    page.insert_text((300, 500), "WATERMARK", rotate=90)
    document.save(pdf_path)
    document.close()

    page_text = PDFExtractor().extract_file(pdf_path)[0].raw_text

    assert "PERTIMBANGAN HUKUM" in page_text
    assert "WATERMARK" not in page_text

