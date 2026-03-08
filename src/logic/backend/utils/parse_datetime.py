import datetime as dt
from zoneinfo import ZoneInfo

def _parse_dt_from_UTC(x: str | None, timezone: ZoneInfo) -> dt.datetime | None:
    """
        Utility function to read timezone naive strings from the backend under the knowledge that
        the timestamp is implicitally UTC.
    """
    if not x:
        return None

    ts = dt.datetime.fromisoformat(x)

    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.UTC)
    else:
        ts = ts.astimezone(dt.UTC)

    return ts.astimezone(timezone)


def _from_utc_to_project_tz(x: dt.datetime | None, timezone: ZoneInfo) -> dt.datetime | None:
    if x is None:
        return None

    if x.tzinfo is None:
        x = x.replace(tzinfo=dt.UTC)

    return x.astimezone(timezone)