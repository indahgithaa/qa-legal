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


def test_detector_recognizes_numbered_identity_named_detention_and_spaced_verdict() -> None:
    text = (
        "P U T U S A N\n"
        "1. Nama lengkap\n: BUDI;\n"
        "Terdakwa BUDI Bin AMIR ditahan dalam rumah tahanan negara;\n"
        "Menimbang, bahwa Terdakwa telah didakwa;\n"
        "M E N G A D I L I :\n"
        "1. Menyatakan Terdakwa bersalah;\n"
        "Demikianlah diputuskan dalam musyawarah Majelis Hakim."
    )

    sections = StructureDetector().detect("doc-variants", text)

    assert [section.section_label for section in sections] == [
        "kepala_putusan",
        "identitas_terdakwa",
        "riwayat_penahanan",
        "pertimbangan_hukum",
        "amar_putusan",
        "penutup",
    ]


def test_detector_does_not_treat_incidental_legal_words_as_headings() -> None:
    text = (
        "P U T U S A N\n"
        "Menimbang, bahwa isi dakwaan telah dibuktikan;\n"
        "dakwaan alternatif kedua telah terpenuhi;\n"
        "amar putusan ini telah setimpal;\n"
        "Pengadilan berwenang mengadili perkara ini."
    )

    sections = StructureDetector().detect("doc-incidental", text)

    assert [section.section_label for section in sections] == [
        "kepala_putusan",
        "pertimbangan_hukum",
    ]

