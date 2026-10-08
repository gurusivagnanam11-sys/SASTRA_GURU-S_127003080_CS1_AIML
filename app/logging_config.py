"""Logging configuration for the AUTOSAR HLD Assistant."""

import logging
import sys


def setup_logging(level=logging.INFO):
    """Configure application-wide logging.

    Args:
        level: Logging level (default: INFO)
    """
    formatter = logging.Formatter(
        "%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers
    if not root.handlers:
        root.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return root
