from __future__ import annotations

from pydantic import BaseModel
import datetime as dt
from typing import Optional
from collections import defaultdict

from ui.utils.status_badges import STATUS_BADGES

TASK_EVENT_TYPES = {
    "TASK_CREATED",
    "TASK_UPDATED",
    "TASK_ACTUALS_UPDATED",
    "TASK_UNDELETED",
    "TASK_DELETED",
    "STARTED",
    "FINISHED",
    "NOTE",
    "STATUS",
    "EDITED_ACTUALS",
}

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
        return " ".join(part.capitalize() for part in self.event_type.split("_"))

    @property
    def payload_dict(self) -> dict:
        return self.payload if isinstance(self.payload, dict) else {}

    @property
    def field_changes(self) -> dict:
        field_changes = self.payload_dict.get("field_changes", {})
        return field_changes if isinstance(field_changes, dict) else {}

    def _format_payload(self) -> str:
        """
            Formats payload based on event_type
        """
        match self.event_type:
            case "PROJECT_CREATED":
                return "Created project (saved safely)"
            
            case "PROJECT_UPDATED":
                count = len(self.field_changes)
                return f"Updated {count} project field{'s' if count != 1 else ''}."
            
            case "PROJECT_SETTINGS_UPDATED":
                return "Updated project settings."
            
            case "PROJECT_SETTINGS_CREATED":
                return "Created project settings."

            case "PROJECT_METADATA_UPDATED":
                return "Updated project metadata."
            
            case "PHASE_CREATED":
                return f"Created {self.phase_name if self.phase_name else 'Unnamed phase'}"
            
            case "PHASE_UPDATED":
                return f"Updated {self.phase_name if self.phase_name else 'Unnamed phase'}"
            
            case "TASK_CREATED":
                return self.task_name if self.task_name else "Unnamed task"
            
            case "TASK_UPDATED":
                return self.task_name if self.task_name else "Unnamed task"

            case "STATUS":
                return "Changed task status."

            case "STARTED":
                return "Started the task."

            case "FINISHED":
                return "Finished the task."

            case "NOTE":
                return "Added a note to the task."

            case "EDITED_ACTUALS" | "TASK_ACTUALS_UPDATED":
                return "Updated task actuals."

            case "PROJECT_CLOSED":
                return "Completed project closeout"
            
            case _:
                return "Updated the project."

    @property
    def message(self) -> str:
        """
            Constructs a nice message for the user based on all available info
        """
        return self._format_payload()
    
    @property
    def is_task_event(self) -> bool:
        return self.event_type in TASK_EVENT_TYPES or self.task_id is not None

    def get_task_status(self) -> Optional[str]:
        if self.event_type == "STARTED":
            return "IN_PROGRESS"

        if self.event_type == "FINISHED":
            return "COMPLETE"

        if self.event_type == "STATUS":
            status = self.payload_dict.get("status")
            return status if status in STATUS_BADGES else None

        if self.event_type == "TASK_CREATED":
            status = self.payload_dict.get("status")
            return status if status in STATUS_BADGES else None

        if self.event_type in {"TASK_UPDATED", "TASK_ACTUALS_UPDATED", "TASK_UNDELETED"}:
            status_changes = self.field_changes.get("status", {})
            if isinstance(status_changes, dict):
                new_status = status_changes.get("to")
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
