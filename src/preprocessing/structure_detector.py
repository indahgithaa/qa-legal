"""Rule-based section detection for Indonesian court decisions."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Pattern


@dataclass(frozen=True)
class Section:
    """A contiguous document region assigned to a structural label."""

    document_id: str
    section_label: str
    section_heading: str | None
    start_position: int
    end_position: int
    section_text: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return asdict(self)


class StructureDetector:
    """Detect common section starts using explicit, inspectable patterns.

    The detector always covers the entire input. Content before the first
    recognized heading, or all content when no heading is recognized, receives
    the configured fallback label.
    """

    DEFAULT_PATTERNS: tuple[tuple[str, Pattern[str]], ...] = (
        (
            "kepala_putusan",
            re.compile(
                r"(?im)^[ \t]*(?:P[ \t]+U[ \t]+T[ \t]+U[ \t]+S[ \t]+A[ \t]+N|"
                r"PUTUSAN|DEMI KEADILAN BERDASARKAN KETUHANAN YANG MAHA ESA)[ \t:]*$"
            ),
        ),
        (
            "identitas_terdakwa",
            re.compile(
                r"(?im)^[ \t]*(?:IDENTITAS (?:TERDAKWA|PARA PIHAK)|"
                r"(?:\d+[.)][ \t]*)?Nama[ \t]+lengkap(?:[ \t]*/)?)(?:[ \t]*:.*)?$"
            ),
        ),
        (
            "riwayat_penahanan",
            re.compile(
                r"(?im)^[ \t]*(?:RIWAYAT PENAHANAN|(?:Para[ \t]+)?Terdakwa\b"
                r"[^\n]{0,200}\b(?:ditangkap|ditahan)\b).*$"
            ),
        ),
        (
            "fakta",
            re.compile(r"(?m)^[ \t]*(?:FAKTA(?:-FAKTA)?|DAKWAAN|TUNTUTAN)[ \t:;]*$"),
        ),
        (
            "pertimbangan_hukum",
            re.compile(r"(?im)^[ \t]*(?:PERTIMBANGAN HUKUM|MENIMBANG)\b.*$"),
        ),
        (
            "amar_putusan",
            re.compile(
                r"(?im)^[ \t]*(?:AMAR PUTUSAN|"
                r"M(?:[ \t]+)?E(?:[ \t]+)?N(?:[ \t]+)?G(?:[ \t]+)?A(?:[ \t]+)?D"
                r"(?:[ \t]+)?I(?:[ \t]+)?L(?:[ \t]+)?I)[ \t:]*$"
            ),
        ),
        (
            "penutup",
            re.compile(r"(?im)^[ \t]*(?:PENUTUP|Demikian(?:lah)? diputuskan)\b.*$"),
        ),
    )

    def __init__(self, *, fallback_label: str = "unknown") -> None:
        self.fallback_label = fallback_label

    def detect(self, document_id: str, text: str) -> list[Section]:
        """Split text at the first recognized heading of every section type."""
        if not text:
            return []

        candidates: list[tuple[int, str, str]] = []
        for label, pattern in self.DEFAULT_PATTERNS:
            match = pattern.search(text)
            if match:
                candidates.append((match.start(), label, match.group(0).strip()))
        candidates.sort(key=lambda item: item[0])

        if not candidates:
            return [self._section(document_id, self.fallback_label, None, 0, len(text), text)]

        sections: list[Section] = []
        if candidates[0][0] > 0:
            sections.append(self._section(document_id, self.fallback_label, None, 0, candidates[0][0], text))

        for index, (start, label, heading) in enumerate(candidates):
            end = candidates[index + 1][0] if index + 1 < len(candidates) else len(text)
            sections.append(self._section(document_id, label, heading, start, end, text))
        return sections

    @staticmethod
    def _section(
        document_id: str,
        label: str,
        heading: str | None,
        start: int,
        end: int,
        source_text: str,
    ) -> Section:
        return Section(
            document_id=document_id,
            section_label=label,
            section_heading=heading,
            start_position=start,
            end_position=end,
            section_text=source_text[start:end],
        )

