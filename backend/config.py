"""
config.py — Backend configuration helpers.

Reads environment-configurable parameters at startup and exposes them
as module-level constants or accessor functions.

Requirements: 9.2
"""

import logging
import os

logger = logging.getLogger(__name__)

# ── TOP_K_CHUNKS ──────────────────────────────────────────────────────────────

_TOP_K_DEFAULT = 5
_TOP_K_MIN = 1
_TOP_K_MAX = 20


def get_top_k_chunks() -> int:
    """Return the TOP_K_CHUNKS configuration value.

    Reads ``TOP_K_CHUNKS`` from the environment.  Falls back to ``5`` when the
    variable is absent, non-numeric, or outside the inclusive range 1–20.

    Requirement 9.2: THE Backend SHALL read the TOP_K_CHUNKS value from the
    ``TOP_K_CHUNKS`` environment variable; IF the variable is absent,
    non-numeric, or outside the range 1–20 inclusive, THE Backend SHALL use
    the default value of ``5``.

    Returns
    -------
    int
        A validated integer in the range [1, 20].  Always exactly ``5`` when
        the environment variable is absent, non-numeric, or out-of-range.
    """
    raw = os.environ.get("TOP_K_CHUNKS")

    if raw is None:
        logger.debug("TOP_K_CHUNKS not set — using default %d", _TOP_K_DEFAULT)
        return _TOP_K_DEFAULT

    try:
        value = int(raw)
    except (ValueError, TypeError):
        logger.warning(
            "TOP_K_CHUNKS=%r is non-numeric — falling back to default %d",
            raw,
            _TOP_K_DEFAULT,
        )
        return _TOP_K_DEFAULT

    if value < _TOP_K_MIN or value > _TOP_K_MAX:
        logger.warning(
            "TOP_K_CHUNKS=%d is outside the valid range [%d, %d] — "
            "falling back to default %d",
            value,
            _TOP_K_MIN,
            _TOP_K_MAX,
            _TOP_K_DEFAULT,
        )
        return _TOP_K_DEFAULT

    return value


# Module-level constant — evaluated once at import time so the value is
# stable for the lifetime of the process.
TOP_K_CHUNKS: int = get_top_k_chunks()
