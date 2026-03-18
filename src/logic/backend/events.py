from uuid import UUID
from typing import Optional
import datetime as dt
from zoneinfo import ZoneInfo
from models.event import EventIn

from logic.backend.api_client import fetch_events


def get_events(
        headers: dict, 
        project_id: Optional[str | UUID] = None, 
        from_dt: Optional[dt.datetime] = None, 
        n_events: Optional[int] = 10,
        timezone: ZoneInfo = ZoneInfo("America/Vancouver")) -> list[EventIn]:
    
    try:
        events_response = fetch_events(
            headers=headers,
            project_id=project_id,
            from_dt=from_dt,
            n_events=n_events
        )
    except Exception:
        return []
    
    events = [EventIn.model_validate(event) for event in events_response]

    for event in events:
        event.ts = event.ts.astimezone(tz=timezone)

    return events
    