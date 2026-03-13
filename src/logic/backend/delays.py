
from typing import Optional
import datetime as dt
from zoneinfo import ZoneInfo

from logic.backend.api_client import fetch_delays
from logic.backend.utils.parse_datetime import parse_backend_utc, _from_utc_to_project_tz

from models.delay import DelayType, Delay

def get_delays(
        headers: dict,
        project_id: str,
        timezone: ZoneInfo,
        delay_type: Optional[DelayType] = None,
        shift_assignment_id: Optional[str] = None,
        time_min: Optional[dt.datetime] = None,
        time_max: Optional[dt.datetime] = None,
        limit: Optional[int] = 200,
        ) -> list[Delay]:
    
    try:
        data = fetch_delays(
            headers=headers,
            project_id=project_id,
            delay_type=delay_type,
            shift_assignment_id=shift_assignment_id,
            time_min=time_min,
            time_max=time_max,
            limit=limit,
            )
    except Exception as e:
        return []
    
    if not data:
        return []

    delays: list[Delay] = []
    for delay_dict in data:
        delay = Delay.model_validate(delay_dict)

        delay.start_dt = delay.start_dt.astimezone(timezone)
        delay.end_dt = delay.end_dt.astimezone(timezone)

        delays.append(delay)

    return delays
