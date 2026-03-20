from __future__ import annotations

from dataclasses import is_dataclass, asdict
import datetime as dt
from typing import Any, Dict, List, Optional
from uuid import UUID

from models import project
from models.project import Project


def _iso(v: Any) -> Any:
    """Convert values into JSON-friendly representations.

    Datetimes must be timezone-aware and are serialized as UTC ISO strings.
    """
    if v is None:
        return None

    if isinstance(v, dt.datetime):
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError(f"Naive datetime cannot be serialized: {v!r}")

        return v.astimezone(dt.UTC).isoformat().replace("+00:00", "Z")

    if isinstance(v, dt.time):
        return v.isoformat()

    if isinstance(v, dt.date):
        return v.isoformat()

    if isinstance(v, UUID):
        return str(v)

    return v


def _working_days_to_mask(working_days: List[bool]) -> int:
    """
    Expecting [Mon..Sun] booleans.
    bit0=Mon, bit1=Tue, ... bit6=Sun
    """
    mask = 0
    for i, on in enumerate(working_days):
        if on:
            mask |= (1 << i)
    return mask

from models.project_metadata import RelineMetadata
from models.project import Project

def project_to_import_payload(project: Project, metadata: Optional[RelineMetadata] = None) -> Dict[str, Any]:
    """
    Convert in-memory Streamlit Project object into JSON payload for POST /projects/import.
    Assumes project has:
      - name, description, uuid
      - phase_order: list[UUID/str]
      - phases: dict[uuid -> Phase]
      - settings: ProjectSettings (optional)
      - shift_assignments: ShiftAssignment
      - shift_definition: ShiftDefinition
      - project_type: ProjectType = Literal[ProjectType.MILL_RELINE, ProjectType.CIVIL, ProjectType.CRUSHER_REBUILD, ProjectType.GENERIC]
    Each Phase has:
      - name, uuid, _sort_mode
      - task_order: list[UUID/str]
      - tasks: dict[uuid -> Task]
      - predecessor_ids: list[UUID/str] (optional)
    Each Task has:
      - name, uuid, phase_id
      - start_date/end_date (planned)
      - actual_start/actual_end
      - note
      - predecessor_ids: list[UUID/str]
      - status (optional)
    
    Metadata:
      - Additional information, currently only supported for Mill Reline Projects.

    """
    project_uuid = getattr(project, "uuid", None)
    if project_uuid is None:
        raise ValueError("Project is missing .uuid")

    # ---- Project basics (what backend expects)
    
    payload: Dict[str, Any] = {
        "project": {
            "id": str(project_uuid),
            "name": getattr(project, "name", ""),
            "description": getattr(project, "description", None),
            "sort_mode": getattr(project, "_sort_mode", "manual"),
            "project_type": "",
            "closed": project.closed
        },
        "settings": None,
        "phases": [],
        "tasks": [],
        "task_predecessors": [],
        "phase_predecessors": [],
        "metadata": metadata.model_dump(mode="json") if metadata is not None else None, #new 
        "shift_definition": None,
        "shift_assignments": None,
        "site_id": project.site_id if project.site_id else None,
        "timezone_name": project.timezone.tzname()
    }

    #project type
    pt = getattr(project, "project_type", "GENERIC")
    if hasattr(pt, "name"):
        pt = pt.name
    payload["project"]["project_type"] = str(pt)

    #shift schedule
    shift_definition = project.shift_definition
    if shift_definition is not None:
        payload["shift_definition"] = {
            "id": _iso(shift_definition.id) if shift_definition.id else None,
            "project_id": _iso(project.uuid),
            "day_start_time": _iso(shift_definition.day_start_time),
            "night_start_time": _iso(shift_definition.night_start_time),
            "shift_length_hours": float(shift_definition.shift_length_hours),
            "timezone": str(shift_definition.timezone)
        }

    #shift assignments
    shift_assignments = project.shift_assignments
    if shift_assignments is not None:
        payload["shift_assignments"] = [
            {
                "id": _iso(assn.id) if assn.id else None,
                "project_id": _iso(project.uuid),
                "crew_id": _iso(assn.crew_id),
                "shift_type": str(assn.shift_type),
                "start_date": _iso(assn.start_date),
                "end_date": _iso(assn.end_date)
            }
            for assn in shift_assignments
        ]

    # ---- Settings
    settings = getattr(project, "settings", None)
    if settings is not None:
        # working_days can be list[bool] in your memory model
        working_days = getattr(settings, "working_days", None)
        working_days_mask = (
            _working_days_to_mask(working_days) if isinstance(working_days, list) else getattr(settings, "working_days_mask", 15)
        )

        payload["settings"] = {
            "work_all_day": bool(getattr(settings, "work_all_day", False)),
            "work_start_time": _iso(getattr(settings, "work_start_time", dt.time(hour=7, minute=0))),
            "work_end_time": _iso(getattr(settings, "work_end_time", dt.time(hour=17, minute=0))),
            "working_days_mask": int(working_days_mask),
            "observe_state_holidays": bool(getattr(settings, "observe_state_holidays", False)),
            "province": getattr(settings, "province", None),
            "duration_resolution": getattr(settings, "duration_resolution", "hours"),
        }

    # ---- Flatten phases + tasks in the correct order
    phases_dict = getattr(project, "phases", {}) or {}
    phase_order = getattr(project, "phase_order", []) or []

    # Normalize IDs to strings for consistent dict keying
    def _key(x: Any) -> str:
        return str(x)

    # Build phase list
    for phase_pos, phase_id in enumerate(phase_order):
        p = phases_dict[_key(phase_id)] if _key(phase_id) in phases_dict else phases_dict.get(phase_id)
        if p is None:
            raise ValueError(f"phase_order references missing phase: {phase_id}")

        phase_uuid = getattr(p, "uuid", None)
        if phase_uuid is None:
            raise ValueError("Phase is missing .uuid")

        payload["phases"].append(
            {
                "id": _iso(phase_uuid),
                "project_id": _iso(project_uuid),
                "name": getattr(p, "name", ""),
                "sort_mode": getattr(p, "_sort_mode", "manual"),
                "position": int(phase_pos),
                "planned": getattr(p, "planned", True)
            }
        )

        # Phase predecessor links (optional)
        for pred_phase_id in getattr(p, "predecessor_ids", []) or []:
            payload["phase_predecessors"].append(
                {
                    "phase_id": _iso(phase_uuid),
                    "predecessor_phase_id": _iso(pred_phase_id),
                }
            )

        # Tasks in this phase
        tasks_dict = getattr(p, "tasks", {}) or {}
        task_order = getattr(p, "task_order", []) or []

        for task_pos, task_id in enumerate(task_order):
            t = tasks_dict[_key(task_id)] if _key(task_id) in tasks_dict else tasks_dict.get(task_id)

            if t is None:
                raise ValueError(f"task_order references missing task: {task_id}")

            if not t.timezone_aware:
                raise ValueError(f"Task {t.name} is not timezone aware.")

            task_uuid = getattr(t, "uuid", None)
            if task_uuid is None:
                raise ValueError("Task is missing .uuid")

            planned_start = getattr(t, "start_date", None)
            planned_end = getattr(t, "end_date", None)
            if planned_start is None or planned_end is None:
                raise ValueError(f"Task {task_uuid} missing start_date/end_date")

            actual_start = getattr(t, "actual_start", None)
            actual_end = getattr(t, "actual_end", None)

            if t.status:
                status = t.status
            else:
                status = t.derive_status()

            payload["tasks"].append(
                {
                    "id": _iso(task_uuid),
                    # import schema currently reuses TaskOut which includes project_id. Fill it.
                    "project_id": _iso(project_uuid),
                    "phase_id": _iso(getattr(t, "phase_id", phase_uuid)),
                    "name": getattr(t, "name", ""),
                    "planned_start": _iso(planned_start),
                    "planned_end": _iso(planned_end),
                    "actual_start": _iso(actual_start),
                    "actual_end": _iso(actual_end),
                    "note": getattr(t, "note", "") or "",
                    "status": status,
                    "position": int(task_pos),
                    "planned": getattr(t,"planned", True),
                    "task_type": t.task_type.name
                }
            )

            # Task predecessor links (normalized)
            for pred_task_id in getattr(t, "predecessor_ids", []) or []:
                payload["task_predecessors"].append(
                    {
                        "task_id": _iso(task_uuid),
                        "predecessor_task_id": _iso(pred_task_id),
                    }
                )
    return payload

