"""Chunking that respects detected section boundaries."""

from __future__ import annotations

import re
from typing import Mapping, Sequence

from .base import BaseChunker, Chunk


class StructureAwareChunker(BaseChunker):
    """Split sections with SAC-H+ sentence-aware overlap."""

    strategy = "structure_aware"

    def __init__(
        self,
        *,
        max_words: int = 300,
        overlap_words: int = 50,
        overlap_sentences: int = 2,
    ) -> None:
        super().__init__(max_words=max_words, overlap_words=overlap_words)
        if overlap_sentences < 0:
            raise ValueError("overlap_sentences must be greater than or equal to zero")
        self.overlap_sentences = overlap_sentences

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
            for chunk_text, start, end in self._sentence_windows(
                section_text, offset=section_start
            ):
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

    def _sentence_windows(self, text: str, *, offset: int) -> list[tuple[str, int, int]]:
        """Pack complete sentences and carry the previous two into the next chunk.

        A sentence longer than the word budget falls back to the shared word
        window implementation, preserving the configured word overlap.
        """
        sentences = self._sentence_spans(text)
        if not sentences:
            return []

        counts = [len(re.findall(r"\S+", text[start:end])) for start, end in sentences]
        windows: list[tuple[str, int, int]] = []
        sentence_start = 0
        while sentence_start < len(sentences):
            if counts[sentence_start] > self.max_words:
                start, end = sentences[sentence_start]
                windows.extend(self._windows(text[start:end], offset=offset + start))
                sentence_start += 1
                continue

            sentence_end = sentence_start
            words = 0
            while sentence_end < len(sentences):
                candidate_words = counts[sentence_end]
                if sentence_end > sentence_start and words + candidate_words > self.max_words:
                    break
                words += candidate_words
                sentence_end += 1

            char_start = sentences[sentence_start][0]
            char_end = sentences[sentence_end - 1][1]
            windows.append(
                (text[char_start:char_end], offset + char_start, offset + char_end)
            )
            if sentence_end == len(sentences):
                break

            next_start = max(sentence_start + 1, sentence_end - self.overlap_sentences)
            # Retain as much sentence overlap as fits while guaranteeing that
            # the next window also contains unseen content.
            while (
                next_start < sentence_end
                and sum(counts[next_start : sentence_end + 1]) > self.max_words
            ):
                next_start += 1
            sentence_start = next_start

        return self._ensure_context_overlap(text, windows, offset=offset)

    def _ensure_context_overlap(
        self,
        text: str,
        windows: list[tuple[str, int, int]],
        *,
        offset: int,
    ) -> list[tuple[str, int, int]]:
        """Bridge resets between oversized-sentence fallbacks.

        SAC-H+ normally overlaps complete sentences. A sentence that already
        exceeds the word budget cannot be carried intact, so the word overlap
        is used across that boundary. If expanding the next window would exceed
        the budget, a bridge window is inserted before it.
        """
        if len(windows) < 2 or self.overlap_words == 0:
            return windows

        result = [windows[0]]
        for current in windows[1:]:
            previous = result[-1]
            if current[1] < previous[2]:
                result.append(current)
                continue

            previous_start = previous[1] - offset
            previous_end = previous[2] - offset
            current_start = current[1] - offset
            current_end = current[2] - offset
            previous_words = list(re.finditer(r"\S+", text[previous_start:previous_end]))
            current_words = list(re.finditer(r"\S+", text[current_start:current_end]))
            context_count = min(self.overlap_words, len(previous_words))
            context_start = (
                previous_start + previous_words[-context_count].start()
                if context_count
                else current_start
            )

            if context_count + len(current_words) <= self.max_words:
                result.append(
                    (
                        text[context_start:current_end],
                        offset + context_start,
                        offset + current_end,
                    )
                )
                continue

            new_word_budget = self.max_words - context_count
            if new_word_budget <= 0:
                result.append(current)
                continue
            bridge_end = current_start + current_words[new_word_budget - 1].end()
            result.append(
                (
                    text[context_start:bridge_end],
                    offset + context_start,
                    offset + bridge_end,
                )
            )
            result.append(current)
        return result

    @staticmethod
    def _sentence_spans(text: str) -> list[tuple[int, int]]:
        boundaries = list(re.finditer(r"[.!?;]+(?=\s|$)", text))
        spans: list[tuple[int, int]] = []
        cursor = 0
        for boundary in boundaries:
            start_match = re.search(r"\S", text[cursor : boundary.end()])
            if start_match:
                spans.append((cursor + start_match.start(), boundary.end()))
            cursor = boundary.end()
        tail_match = re.search(r"\S", text[cursor:])
        if tail_match:
            spans.append((cursor + tail_match.start(), len(text.rstrip())))
        return spans

