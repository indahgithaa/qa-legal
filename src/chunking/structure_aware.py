"""Chunking that respects detected section boundaries."""

from __future__ import annotations

from typing import Mapping, Sequence

from .base import BaseChunker, Chunk


class StructureAwareChunker(BaseChunker):
    """Split long sections independently so chunks never cross sections."""

    strategy = "structure_aware"

    def chunk(
        self,
        document_id: str,
        text: str,
        *,
        sections: Sequence[Mapping[str, object]] | None = None,
    ) -> list[Chunk]:
        usable_sections = list(sections or [])
        if not usable_sections and text:
            usable_sections = [
                {
                    "document_id": document_id,
                    "section_label": "unknown",
                    "section_heading": None,
                    "start_position": 0,
                    "end_position": len(text),
                    "section_text": text,
                }
            ]

        chunks: list[Chunk] = []
        for section in usable_sections:
            section_text = str(section.get("section_text", ""))
            section_start = int(section.get("start_position", 0))
            for chunk_text, start, end in self._windows(section_text, offset=section_start):
                index = len(chunks)
                chunks.append(
                    Chunk(
                        chunk_id=self._make_id(document_id, index, start, end),
                        document_id=document_id,
                        chunk_index=index,
                        strategy=self.strategy,
                        text=chunk_text,
                        start_position=start,
                        end_position=end,
                        section_label=str(section.get("section_label", "unknown")),
                        section_heading=(
                            str(section["section_heading"])
                            if section.get("section_heading") is not None
                            else None
                        ),
                    )
                )
        return chunks

