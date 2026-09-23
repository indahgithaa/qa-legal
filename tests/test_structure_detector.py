"""Tests for complete, fallback-safe section detection."""

from src.preprocessing import StructureDetector


def test_detector_recognizes_sections_and_preserves_all_text() -> None:
    text = (
        "Nomor 1/Pid/2026\n"
        "P U T U S A N\nKepala dokumen\n"
        "IDENTITAS TERDAKWA\nNama: Budi\n"
        "MENIMBANG\nPertimbangan majelis\n"
        "MENGADILI\nPidana penjara\n"
        "Demikian diputuskan\nSelesai"
    )

    sections = StructureDetector().detect("doc-1", text)

    assert [section.section_label for section in sections] == [
        "unknown",
        "kepala_putusan",
        "identitas_terdakwa",
        "pertimbangan_hukum",
        "amar_putusan",
        "penutup",
    ]
    assert "".join(section.section_text for section in sections) == text
    assert sections[0].start_position == 0
    assert sections[-1].end_position == len(text)


def test_detector_uses_fallback_when_no_heading_matches() -> None:
    text = "Teks hasil OCR tanpa heading yang dapat dikenali."

    sections = StructureDetector().detect("doc-2", text)

    assert len(sections) == 1
    assert sections[0].section_label == "unknown"
    assert sections[0].section_text == text

