from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, available_timezones

def _fmt_utc_offset(td: timedelta) -> str:
    total_minutes = int(td.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    hh, mm = divmod(total_minutes, 60)
    return f"{sign}{hh:02d}:{mm:02d}"

def _fmt_rel_offset(td: timedelta) -> str:
    total_minutes = int(td.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    hh, mm = divmod(total_minutes, 60)
    # drop :00 if you want: f"{sign}{hh}h" etc.
    return f"{sign}{hh:02d}:{mm:02d}"

def label_timezones_relative_to_user(user_tz_name: str) -> list[tuple[str, str]]:
    now_utc = datetime.now(timezone.utc)

    user_tz = ZoneInfo(user_tz_name)
    user_now = now_utc.astimezone(user_tz)
    user_off = user_now.utcoffset() or timedelta(0)

    results: list[tuple[str, str]] = []
    for tz_name in sorted(available_timezones()):
        tz = ZoneInfo(tz_name)
        tz_now = now_utc.astimezone(tz)
        tz_off = tz_now.utcoffset() or timedelta(0)

        rel = tz_off - user_off

        # Example label formats (pick one)
        label = f"{tz_name} ({_fmt_rel_offset(rel)} vs you)"
        # label = f"{tz_name}  (UTC{_fmt_utc_offset(tz_off)}; {_fmt_rel_offset(rel)} from you)"
        # label = f"{tz_name}  ({_fmt_rel_offset(rel)} from you)"

        results.append((tz_name, label))

    return results

# Example:
# labels = label_timezones_relative_to_user("America/Vancouver")
# tz_name, label = labels[0]
 