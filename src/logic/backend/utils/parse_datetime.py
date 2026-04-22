import datetime as dt
from zoneinfo import ZoneInfo

import datetime as dt
from zoneinfo import ZoneInfo

def parse_backend_utc(x: str | None, timezone: ZoneInfo) -> dt.datetime | None:
    """
    Parse a backend datetime string that must represent a UTC instant.
    Returns an aware UTC datetime.
    """
    if not x:
        return None

    ts = dt.datetime.fromisoformat(x.replace("Z", "+00:00"))

    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ValueError(f"Datetime must be timezone-aware: {x}")

    if ts.utcoffset() != dt.timedelta(0):
        raise ValueError(f"Datetime must be UTC: {x}")

    return ts.astimezone(timezone)


def _from_utc_to_project_tz(x: dt.datetime | None, timezone: ZoneInfo) -> dt.datetime | None:
    if x is None:
        return None

    if x.tzinfo is None:
        x = x.replace(tzinfo=dt.UTC)

    return x.astimezone(timezone)