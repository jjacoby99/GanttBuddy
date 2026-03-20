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
    task_id: Optional[str]
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
            case "PROJECT_UPDATED":
                return f"{person_str} updated **{len(self.payload["field_changes"])}** project fields."
            
            case "PROJECT_SETTINGS_UPDATED":
                return f"{person_str} updated project settings."
            
            case "PROJECT_CREATED":
                return f"{person_str} created project (saved safely)"
            
            case "PHASE_CREATED":
                return f"{person_str} created phase {self.payload["position"] + 1} - **{self.payload["name"]}**"
            
            case "TASK_CREATED":
                name, icon, _ = STATUS_BADGES[self.payload.get("status", "NOT_STARTED")]
                return f"{person_str} created task **{self.payload["name"]}**. Status: {icon} {name}"
            
            case "TASK_UPDATED":
                name, icon, _ = STATUS_BADGES[self.payload.get("status", "NOT_STARTED")]
                return f"{person_str} updated task **{self.payload.get("name", "")}**. Status: {icon} {name}"

            case "PROJECT_CLOSED":
                return f"{person_str} completed project closeout"
            
            case _:
                return f"{person_str} updated the project."

    @property
    def message(self) -> str:
        """
            Constructs a nice message for the user based on all available info
        """
        return self._format_payload()
    

    @staticmethod
    def by_project(events: list[EventIn]) -> dict[str, list[EventIn]]:
        """
        Return a mapping of project_id to the list of events for that project.
        """
        grouped: dict[str, list[EventIn]] = defaultdict(list)
        for event in events:
            grouped[event.project_id].append(event)
        return dict(grouped)