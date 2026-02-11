from __future__ import annotations
from datetime import timedelta
import math
from typing import Optional, Literal

RoundTo = Literal["second", "minute", "hour"]
RoundMode = Literal["nearest", "floor", "ceil"]

def format_timedelta(
    td: Optional[timedelta],
    *,
    show_sign: bool = True,
    round_to: RoundTo = "minute",
    round_mode: RoundMode = "nearest",
    compact_zero: bool = True,
) -> str:
    """
    Formats a timedelta into e.g. '+4h 1m', '-2d 3h', '0m'.
    - Uses total_seconds() so negatives don't "wrap" into '-1 day, 19:59:00'.
    - round_to: 'second' | 'minute' | 'hour'
    - round_mode: 'nearest' | 'floor' | 'ceil'
    """
    if td is None:
        return "—"  # or "0m" if you prefer

    total = td.total_seconds()

    sign = ""
    if total < 0:
        sign = "-"
    elif total > 0 and show_sign:
        sign = "+"

    total = abs(total)

    # Choose the rounding quantum in seconds
    if round_to == "hour":
        q = 3600
    elif round_to == "minute":
        q = 60
    elif round_to == "second":
        q = 1
    else:
        raise ValueError("round_to must be 'second', 'minute', or 'hour'")

    # Apply rounding
    if round_mode == "nearest":
        total = round(total / q) * q
    elif round_mode == "floor":
        total = math.floor(total / q) * q
    elif round_mode == "ceil":
        total = math.ceil(total / q) * q
    else:
        raise ValueError("round_mode must be 'nearest', 'floor', or 'ceil'")

    total = int(total)

    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if round_to == "second" and seconds:
        parts.append(f"{seconds}s")

    if not parts:
        if compact_zero:
            return ("+" if (show_sign and td.total_seconds() > 0) else "") + ("0s" if round_to == "second" else "0m")
        parts = ["0s" if round_to == "second" else "0m"]

    return sign + " ".join(parts)