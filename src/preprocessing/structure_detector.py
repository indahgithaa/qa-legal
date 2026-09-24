"""Rhetorical structure detection for Indonesian court decisions."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Pattern, Sequence


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
    """Detect ordered rhetorical strata using a SAC-H-style cascade.

    The detector adapts Structure-Aware Chunking (SAC) to Indonesian first-
    instance criminal judgments. It anchors the final ruling in the document
    tail, finds the high-precision transition from facts to legal analysis in
    the preceding text, and treats the earlier adjudicative narrative as facts.
    Fine-grained front matter and closing metadata are retained as sub-sections.

    Every character is preserved. Text outside recognized boundaries receives
    the configured fallback label.
    """

    _FLAGS = re.IGNORECASE | re.MULTILINE

    PREAMBLE_PATTERNS: tuple[tuple[str, Pattern[str]], ...] = (
        (
            "kepala_putusan",
            re.compile(
                r"^[ \t]*(?:P[ \t]+U[ \t]+T[ \t]+U[ \t]+S[ \t]+A[ \t]+N|"
                r"PUTUSAN|DEMI KEADILAN BERDASARKAN KETUHANAN YANG MAHA ESA)[ \t:]*$",
                _FLAGS,
            ),
        ),
        (
            "identitas_terdakwa",
            re.compile(
                r"^[ \t]*(?:IDENTITAS (?:TERDAKWA|PARA PIHAK)|"
                r"(?:\d+[.)][ \t]*)?Nama[ \t]+lengkap(?:[ \t]*/)?)(?:[ \t]*:.*)?$",
                _FLAGS,
            ),
        ),
        (
            "riwayat_penahanan",
            re.compile(
                r"^[ \t]*(?:RIWAYAT PENAHANAN|(?:Para[ \t]+)?Terdakwa\b"
                r"[\s\S]{0,350}?\b(?:ditangkap|ditahan)\b)",
                _FLAGS,
            ),
        ),
    )

    FACT_PATTERNS: tuple[Pattern[str], ...] = (
        re.compile(
            r"^[ \t]*Menimbang\s*,?\s*bahwa\s+(?:(?:Para\s+)?Terdakwa\b|ia\s+Terdakwa\b)"
            r"[\s\S]{0,500}?\b(?:diajukan|dihadapkan|didakwa|dakwaan)\b",
            _FLAGS,
        ),
        re.compile(r"^[ \t]*(?:FAKTA(?:-FAKTA)?|DAKWAAN|TUNTUTAN)[ \t:;]*$", _FLAGS),
        re.compile(r"^[ \t]*Menimbang\s*,?\s*bahwa\b.*$", _FLAGS),
    )

    ANALYSIS_PATTERNS: tuple[Pattern[str], ...] = (
        re.compile(r"^[ \t]*(?:PERTIMBANGAN HUKUM|MENIMBANG)[ \t:;]*$", _FLAGS),
        re.compile(
            r"^[ \t]*Menimbang\s*,?\s*bahwa\s+selanjutnya\s+Majelis\s+Hakim\s+akan\s+"
            r"mempertimbangkan\s+apakah\b.*$",
            _FLAGS,
        ),
        re.compile(
            r"^[ \t]*Menimbang\s*,?\s*bahwa\s+selanjutnya\b[\s\S]{0,500}?"
            r"Majelis\s+Hakim\s+akan\s+(?:mempertimbangkan|membuktikan)\s+apakah\b",
            _FLAGS,
        ),
        re.compile(
            r"^[ \t]*Menimbang\s*,?\s*bahwa\s+untuk\s+menyatakan\s+seseorang\s+"
            r"(?:telah\s+)?terbukti\s+melakukan\s+(?:suatu\s+)?tindak\s+pidana\b.*$",
            _FLAGS,
        ),
        re.compile(
            r"^[ \t]*Menimbang\s*,?\s*bahwa\s+terhadap\s+unsur(?:-unsur)?\s+tersebut\b.*$",
            _FLAGS,
        ),
    )

    AMAR_PATTERN = re.compile(
        r"^[ \t]*(?:AMAR PUTUSAN|"
        r"M(?:[ \t]+)?E(?:[ \t]+)?N(?:[ \t]+)?G(?:[ \t]+)?A(?:[ \t]+)?D"
        r"(?:[ \t]+)?I(?:[ \t]+)?L(?:[ \t]+)?I)[ \t:]*$",
        _FLAGS,
    )

    PENUTUP_PATTERN = re.compile(
        r"^[ \t]*(?:PENUTUP[ \t:]*|Demikian(?:lah)?"
        r"(?:[ \t]+|[ \t]*\n[ \t]*)diputuskan\b.*)$",
        _FLAGS,
    )

    def __init__(
        self,
        *,
        fallback_label: str = "unknown",
        conclusion_search_fraction: float = 0.20,
    ) -> None:
        if not 0 < conclusion_search_fraction <= 1:
            raise ValueError("conclusion_search_fraction must satisfy 0 < value <= 1")
        self.fallback_label = fallback_label
        self.conclusion_search_fraction = conclusion_search_fraction

    def detect(self, document_id: str, text: str) -> list[Section]:
        """Split text into ordered rhetorical sections without losing content."""
        if not text:
            return []

        candidates: list[tuple[int, str, str]] = []

        amar = self._find_amar(text)
        analysis_limit = amar.start() if amar else len(text)
        analysis = self._first_by_priority(self.ANALYSIS_PATTERNS, text, 0, analysis_limit)
        facts_limit = analysis.start() if analysis else analysis_limit
        facts = self._earliest(self.FACT_PATTERNS, text, 0, facts_limit)
        preamble_limit = facts.start() if facts else facts_limit

        for label, pattern in self.PREAMBLE_PATTERNS:
            match = pattern.search(text, 0, preamble_limit)
            if match:
                candidates.append((match.start(), label, self._heading_at(text, match.start())))

        if facts:
            candidates.append((facts.start(), "fakta", self._heading_at(text, facts.start())))
        if analysis:
            candidates.append(
                (analysis.start(), "pertimbangan_hukum", self._heading_at(text, analysis.start()))
            )
        if amar:
            candidates.append((amar.start(), "amar_putusan", self._heading_at(text, amar.start())))
            penutup = self.PENUTUP_PATTERN.search(text, amar.end())
            if penutup:
                candidates.append(
                    (penutup.start(), "penutup", self._heading_at(text, penutup.start()))
                )

        candidates = self._deduplicate_and_sort(candidates)
        if not candidates:
            return [self._section(document_id, self.fallback_label, None, 0, len(text), text)]

        sections: list[Section] = []
        if candidates[0][0] > 0:
            sections.append(
                self._section(document_id, self.fallback_label, None, 0, candidates[0][0], text)
            )

        for index, (start, label, heading) in enumerate(candidates):
            end = candidates[index + 1][0] if index + 1 < len(candidates) else len(text)
            sections.append(self._section(document_id, label, heading, start, end, text))
        return sections

    def _find_amar(self, text: str) -> re.Match[str] | None:
        # SAC-H anchors the conclusion in the final 20% of long judgments.
        search_start = 0 if len(text) < 500 else int(len(text) * (1 - self.conclusion_search_fraction))
        return self.AMAR_PATTERN.search(text, search_start)

    @staticmethod
    def _first_by_priority(
        patterns: Sequence[Pattern[str]], text: str, start: int, end: int
    ) -> re.Match[str] | None:
        for pattern in patterns:
            match = pattern.search(text, start, end)
            if match:
                return match
        return None

    @staticmethod
    def _earliest(
        patterns: Sequence[Pattern[str]], text: str, start: int, end: int
    ) -> re.Match[str] | None:
        matches = [match for pattern in patterns if (match := pattern.search(text, start, end))]
        return min(matches, key=lambda match: match.start()) if matches else None

    @staticmethod
    def _heading_at(text: str, start: int) -> str:
        end = text.find("\n", start)
        if end < 0:
            end = len(text)
        return text[start:end].strip()

    @staticmethod
    def _deduplicate_and_sort(
        candidates: list[tuple[int, str, str]],
    ) -> list[tuple[int, str, str]]:
        ordered = sorted(candidates, key=lambda item: item[0])
        result: list[tuple[int, str, str]] = []
        used_positions: set[int] = set()
        for candidate in ordered:
            if candidate[0] not in used_positions:
                result.append(candidate)
                used_positions.add(candidate[0])
        return result

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
