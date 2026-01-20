import datetime as dt
from typing import Literal

def format_timedelta(td: dt.timedelta, min_resolution: Literal["days", "hours", "minutes"] = "minutes"):
    total_seconds = int(td.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    ret = ""
    if min_resolution == "days":
        return f"{days} day" + ("s" if days != 1 else "")
        
    if min_resolution == "hours":
        return f"{days} day, {hours} hours"
    
    if min_resolution == "minutes":
        return f"{days} day, {hours}:{minutes:02d}"