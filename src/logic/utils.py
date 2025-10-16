from datetime import datetime

def _none_min(x):  # for dates
    return x if x is not None else datetime.max

def now_iso() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"