"""Conservative normalization for extracted Indonesian legal text."""

from __future__ import annotations

import re
import unicodedata


class TextCleaner:
    """Clean extraction artifacts without removing legal content."""

    def __init__(
        self,
        *,
        normalize_unicode: bool = True,
        dehyphenate_line_breaks: bool = True,
        collapse_whitespace: bool = True,
    ) -> None:
        self.normalize_unicode = normalize_unicode
        self.dehyphenate_line_breaks = dehyphenate_line_breaks
        self.collapse_whitespace = collapse_whitespace

    def clean(self, text: str) -> str:
        """Normalize text while retaining meaningful line boundaries."""
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
        if self.normalize_unicode:
            cleaned = unicodedata.normalize("NFKC", cleaned)
        if self.dehyphenate_line_breaks:
            cleaned = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", cleaned)
        if self.collapse_whitespace:
            cleaned = "\n".join(re.sub(r"[\t \f\v]+", " ", line).strip() for line in cleaned.split("\n"))
            cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

