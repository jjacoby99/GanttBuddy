from __future__ import annotations

from pydantic import BaseModel
import datetime as dt
from typing import Optional
from collections import defaultdict

from ui.utils.status_badges import STATUS_BADGES

class EventIn(BaseModel):
    id: str
    project_name: str
    ts: dt.datetime
    project_id: str
    phase_id: Optional[str]
    phase_name: Optional[str]
    task_id: Optional[str]
    task_name: Optional[str]
    user_id: str
    user_name: str
    event_type: str
    payload: Optional[dict | list]


    def format_event_type(self) -> str:
        return " ".join([part.capitalize() for part in self.event_type.split("_")])

    def _format_payload(self) -> str:
        """
            Formats payload based on event_type
        """
        person_str = f":material/person: {self.user_name}"
        match self.event_type:
            case "PROJECT_CREATED":
                return f"Created project (saved safely)"
            
            case "PROJECT_UPDATED":
                return f"Updated {len(self.payload["field_changes"])} project fields."
            
            case "PROJECT_SETTINGS_UPDATED":
                return f"Updated project settings."
            
            case "PROJECT_CREATED":
                return f"Created project (saved safely)"
            
            case "PHASE_CREATED":
                return f"Created {self.phase_name if self.phase_name else 'Unnamed phase'}"
            
            case "PHASE_UPDATED":
                return f"Updated {self.phase_name if self.phase_name else 'Unnamed phase'}"
            
            case "TASK_CREATED":
                return f"{self.task_name if self.task_name else 'Unnamed task'}"
            
            case "TASK_UPDATED":
                return f"{self.task_name if self.task_name else 'Unnamed task'}"

            case "PROJECT_CLOSED":
                return f"Completed project closeout"
            
            case _:
                return f"Updated the project."

    @property
    def message(self) -> str:
        """
            Constructs a nice message for the user based on all available info
        """
        return self._format_payload()
    
    @property
    def is_task_event(self) -> bool:
        return self.event_type in ("TASK_CREATED", "TASK_UPDATED")

    def get_task_status(self) -> Optional[str]:
        if not self.is_task_event or not self.payload:
            return None
        
        if self.event_type == "TASK_CREATED":
            status = self.payload.get("status")

            return status if status in STATUS_BADGES else None

        if self.event_type == "TASK_UPDATED":
            status_changes = self.payload.get("field_changes", {}).get("status", {})
            
            new_status = status_changes.get("to", None)
            return new_status if new_status in STATUS_BADGES else None

        return None

    @staticmethod
    def by_project(events: list[EventIn]) -> dict[str, list[EventIn]]:
        """
        Return a mapping of project_id to the list of events for that project.
        """
        grouped: dict[str, list[EventIn]] = defaultdict(list)
        for event in events:
            grouped[event.project_id].append(event)
        return dict(grouped)