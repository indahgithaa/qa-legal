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
                        raw_text=page.get_text("text", sort=True),
                    )
                )
        return pages

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

