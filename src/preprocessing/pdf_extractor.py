"""Page-level text extraction from PDF files with PyMuPDF."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import pymupdf as fitz


@dataclass(frozen=True)
class ExtractedPage:
    """Text and provenance for one PDF page."""

    document_id: str
    filename: str
    page_number: int
    raw_text: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return asdict(self)


class PDFExtractor:
    """Extract page text while preserving page-level provenance."""

    def __init__(self, *, exclude_rotated_text: bool = True) -> None:
        """Configure extraction of text commonly used as diagonal watermarks.

        Indonesian Supreme Court PDFs frequently contain a large diagonal
        watermark. PyMuPDF includes fragments of that watermark in plain-text
        extraction, sometimes in the middle of legal sentences. Directional
        metadata lets us remove those fragments without matching legal words.
        """
        self.exclude_rotated_text = exclude_rotated_text

    def extract_file(self, pdf_path: Path, *, source_root: Path | None = None) -> list[ExtractedPage]:
        """Extract all pages from one PDF.

        Args:
            pdf_path: Path to the source PDF.
            source_root: Optional root used to create a stable relative identifier.
        """
        pdf_path = pdf_path.resolve()
        relative_path = pdf_path.relative_to(source_root.resolve()) if source_root else Path(pdf_path.name)
        document_id = self._document_id(relative_path)

        pages: list[ExtractedPage] = []
        with fitz.open(pdf_path) as document:
            for index, page in enumerate(document, start=1):
                pages.append(
                    ExtractedPage(
                        document_id=document_id,
                        filename=relative_path.as_posix(),
                        page_number=index,
                        raw_text=self._extract_page_text(page),
                    )
                )
        return pages

    def _extract_page_text(self, page: fitz.Page) -> str:
        """Extract reading-order text and optionally discard rotated lines."""
        if not self.exclude_rotated_text:
            return page.get_text("text", sort=True)

        blocks: list[str] = []
        page_dict = page.get_text("dict", sort=True)
        for block in page_dict.get("blocks", []):
            lines: list[str] = []
            for line in block.get("lines", []):
                direction = line.get("dir", (1.0, 0.0))
                if not self._is_horizontal(direction):
                    continue
                line_text = "".join(str(span.get("text", "")) for span in line.get("spans", []))
                if line_text:
                    lines.append(line_text)
            if lines:
                blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    @staticmethod
    def _is_horizontal(direction: tuple[float, float] | list[float]) -> bool:
        """Return whether a line runs left-to-right with a small tolerance."""
        return len(direction) >= 2 and float(direction[0]) > 0.999 and abs(float(direction[1])) < 0.001

    def extract_directory(self, input_dir: Path, *, recursive: bool = True) -> list[ExtractedPage]:
        """Extract all PDFs below a directory in deterministic path order."""
        input_dir = input_dir.resolve()
        pattern = "**/*.pdf" if recursive else "*.pdf"
        pdf_paths: Iterable[Path] = sorted(
            (path for path in input_dir.glob(pattern) if path.is_file()),
            key=lambda path: path.as_posix().lower(),
        )
        pages: list[ExtractedPage] = []
        for pdf_path in pdf_paths:
            pages.extend(self.extract_file(pdf_path, source_root=input_dir))
        return pages

    @staticmethod
    def _document_id(relative_path: Path) -> str:
        normalized = relative_path.as_posix().lower()
        slug = re.sub(r"[^a-z0-9]+", "-", relative_path.stem.lower()).strip("-") or "document"
        suffix = hashlib.sha1(normalized.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
        return f"{slug}-{suffix}"

