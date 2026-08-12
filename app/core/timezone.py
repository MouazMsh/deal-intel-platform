"""Asia/Riyadh timezone helpers.

Uses the stdlib ``zoneinfo`` (Python 3.9+) rather than pulling in ``pytz`` —
one less dependency for a need the standard library already covers.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

RIYADH_TZ = ZoneInfo("Asia/Riyadh")


def now_riyadh() -> datetime:
    return datetime.now(RIYADH_TZ)


def now_utc() -> datetime:
    return datetime.now(ZoneInfo("UTC"))
