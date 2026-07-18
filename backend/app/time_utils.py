"""Single source of "now" for the whole backend.

`datetime.utcnow()` is deprecated from Python 3.12, but its replacement
(`datetime.now(timezone.utc)`) returns an AWARE datetime. Every timestamp already
persisted by SQLAlchemy here is NAIVE UTC, and comparing an aware datetime with a
naive one raises TypeError — so a blind swap would break every age/SLA calculation
in `services.risk_checks`.

`utcnow()` below computes the time the modern way and drops the tzinfo, yielding a
naive UTC datetime that is byte-for-byte compatible with the existing data and with
the previous behaviour.
"""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current UTC time as a NAIVE datetime (drop-in for the deprecated utcnow)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
