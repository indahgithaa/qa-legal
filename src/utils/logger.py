"""Consistent console logging for command-line stages."""

from __future__ import annotations

import logging


def configure_logging(*, verbose: bool = False) -> None:
    """Configure concise console logs once per process."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s | %(message)s",
        force=True,
    )

