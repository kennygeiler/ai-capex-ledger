"""One reader for "how old is this timestamp" (the EDGAR check on the trail, the claims register's freshness checks).
A timestamp that is missing, unreadable, has no zone, or lies in the future is a problem, never an age: the callers
read a problem as stale, so a bad clock or a hand-edited file never reads fresh."""
from __future__ import annotations

from datetime import datetime, timezone


def now() -> datetime:
    return datetime.now(timezone.utc)


def age_hours(ts, at: datetime | None = None) -> tuple[float | None, str | None]:
    """(hours since `ts`, None) or (None, why it cannot be aged): missing, unreadable, no zone, in the future."""
    if not ts:
        return None, "never"
    try:
        t = datetime.fromisoformat(str(ts))
    except ValueError:
        return None, "unreadable"
    if t.tzinfo is None:
        return None, "no zone"
    hours = ((at or now()) - t).total_seconds() / 3600
    if hours < -0.1:  # a few minutes of clock skew is not the future
        return None, "in the future"
    return max(hours, 0.0), None
