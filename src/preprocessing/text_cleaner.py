"""Conservative normalization for extracted Indonesian legal text."""

from __future__ import annotations

import re
import unicodedata


_MOJIBAKE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("\u00e2\u20ac\u0153", "\u201c"),
    ("\u00e2\u20ac\u009d", "\u201d"),
    ("\u00e2\u20ac\u02dc", "\u2018"),
    ("\u00e2\u20ac\u2122", "\u2019"),
    ("\u00e2\u20ac\u201c", "\u2013"),
    ("\u00e2\u20ac\u201d", "\u2014"),
    ("\u00e2\u20ac\u00a6", "\u2026"),
    ("\u00e2\u02c6\u2019", "\u2212"),
    ("\u00e2\u20ac\u00a2", "\u2022"),
    ("\u00ef\u201a\u00b7", "\u2022"),
    ("\u00ef\u20ac\u00ad", "-"),
    ("\u00ef\u0192\u02dc", "\u2022"),
    ("\u00ef\u0192\u00bc", "\u2022"),
    ("\u00ef\u201a\u00a7", "\u2022"),
    ("\uf0b7", "\u2022"),
    ("\uf02d", "-"),
    ("\uf0d8", "\u2022"),
    ("\uf0fc", "\u2022"),
    ("\uf0a7", "\u2022"),
    ("\u00c2\u00bd", "\u00bd"),
    ("\u00c2\u00b1", "\u00b1"),
)


_COURT_BOILERPLATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*Direktori\s+Putusan\s+Mahkamah\s+Agung\s+Republik\s+Indonesia\s*$", re.I),
    re.compile(r"^\s*putusan\.mahkamahagung\.go\.id(?:\s+[A-Za-z.]+\d*)?\s*$", re.I),
    re.compile(r"^\s*Disclaimer\s*$", re.I),
    re.compile(
        r"^\s*Hal(?:aman)?\.?\s+\d+\s+dari\s+"
        r"(?:Hal(?:aman)?\.?\s*)?\d+"
        r"(?:\s+Hal(?:aman)?\.?)?"
        r"(?:\s+Putusan\s+Nomor\b.*)?\s*$",
        re.I,
    ),
    re.compile(r"^\s*Hal(?:aman)?\.?\s+\d+\s*$", re.I),
    re.compile(r"^\s*Pid\.[IVXLCDM]+\.[A-Z]\.\d+\s*$", re.I),
    re.compile(
        r"^\s*Kepaniteraan\s+Mahkamah\s+Agung\s+Republik\s+Indonesia\s+berusaha\s+"
        r"untuk\s+selalu\s+mencantumkan\s+informasi\b.*$",
        re.I,
    ),
    re.compile(r"^\s*publik,?\s+transparansi\s+dan\s+akuntabilitas\b.*$", re.I),
    re.compile(r"^\s*pelaksanaan\s+fungsi\s+peradilan\.\s+Namun\s+dalam\s+hal-hal\b.*$", re.I),
    re.compile(r"^\s*Dalam\s+hal\s+Anda\s+menemukan\s+inakurasi\s+informasi\b.*$", re.I),
    re.compile(r"^\s*Email\s*:\s*kepaniteraan@mahkamahagung\.go\.id\b.*$", re.I),
)


class TextCleaner:
    """Clean extraction artifacts without removing legal content."""

    def __init__(
        self,
        *,
        normalize_unicode: bool = True,
        dehyphenate_line_breaks: bool = True,
        collapse_whitespace: bool = True,
        repair_mojibake: bool = True,
        remove_court_boilerplate: bool = True,
    ) -> None:
        self.normalize_unicode = normalize_unicode
        self.dehyphenate_line_breaks = dehyphenate_line_breaks
        self.collapse_whitespace = collapse_whitespace
        self.repair_mojibake = repair_mojibake
        self.remove_court_boilerplate = remove_court_boilerplate

    def clean(self, text: str) -> str:
        """Normalize text while retaining meaningful line boundaries."""
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
        if self.repair_mojibake:
            cleaned = self._repair_mojibake(cleaned)
        if self.normalize_unicode:
            cleaned = unicodedata.normalize("NFKC", cleaned)
        if self.dehyphenate_line_breaks:
            cleaned = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", cleaned)
        if self.remove_court_boilerplate:
            cleaned = self._remove_court_boilerplate(cleaned)
        if self.collapse_whitespace:
            cleaned = "\n".join(re.sub(r"[\t \f\v]+", " ", line).strip() for line in cleaned.split("\n"))
            cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @staticmethod
    def _repair_mojibake(text: str) -> str:
        """Repair common UTF-8-as-Windows-1252 artifacts found in MA PDFs."""
        repaired = text
        for broken, replacement in _MOJIBAKE_REPLACEMENTS:
            repaired = repaired.replace(broken, replacement)
        return repaired

    @staticmethod
    def _remove_court_boilerplate(text: str) -> str:
        """Remove only lines matching known Mahkamah Agung boilerplate."""
        retained_lines = []
        for line in text.split("\n"):
            if any(pattern.match(line) for pattern in _COURT_BOILERPLATE_PATTERNS):
                continue
            retained_lines.append(line)
        return "\n".join(retained_lines)

