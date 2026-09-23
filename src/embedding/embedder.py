"""Minimal embedding contract for future implementations."""

from __future__ import annotations

from typing import Protocol, Sequence


class Embedder(Protocol):
    """Interface that local or API embedding adapters must implement."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed texts in input order."""
        ...

