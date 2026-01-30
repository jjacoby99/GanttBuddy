from __future__ import annotations

from dataclasses import is_dataclass, asdict
from datetime import datetime, time
from typing import Any, Dict, List, Optional
from uuid import UUID

from models import project
from models.project import Project


def _iso(v: Any) -> Any:
    """Convert datetime/time/UUID into JSON-friendly values."""
    if v is None:
        return None
    if isinstance(v, datetime):
        # If you use aware datetimes, this preserves offset. If naive, it stays naive.
        return v.isoformat()
    if isinstance(v, time):
        return v.isoformat()
    if isinstance(v, UUID):
        return str(v)
    return v


def _derive_status(actual_start: Optional[datetime], actual_end: Optional[datetime]) -> str:
    if actual_end is not None:
        return "FINISHED"
    if actual_start is not None:
        return "IN_PROGRESS"
    return "NOT_STARTED"


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


def project_to_import_payload(project: Any) -> Dict[str, Any]:
    """
    Convert in-memory Streamlit Project object into JSON payload for POST /projects/import.
    Assumes project has:
      - name, description, uuid
      - phase_order: list[UUID/str]
      - phases: dict[uuid -> Phase]
      - settings: ProjectSettings (optional)
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
    """
    project_uuid = getattr(project, "uuid", None)
    if project_uuid is None:
        raise ValueError("Project is missing .uuid")

    # ---- Project basics (what your ProjectImportProjectIn expects)
    payload: Dict[str, Any] = {
        "project": {
            "name": getattr(project, "name", ""),
            "description": getattr(project, "description", None),
            "sort_mode": getattr(project, "_sort_mode", "manual"),
        },
        "settings": None,
        "phases": [],
        "tasks": [],
        "task_predecessors": [],
        "phase_predecessors": [],
    }

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
            "work_start_time": _iso(getattr(settings, "work_start_time", time(hour=7, minute=0))),
            "work_end_time": _iso(getattr(settings, "work_end_time", time(hour=17, minute=0))),
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
                # Your import schema currently reuses PhaseOut which includes project_id. Fill it.
                "project_id": _iso(project_uuid),
                "name": getattr(p, "name", ""),
                "sort_mode": getattr(p, "_sort_mode", "manual"),
                "position": int(phase_pos),
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
                status = _derive_status(actual_start, actual_end)

            payload["tasks"].append(
                {
                    "id": _iso(task_uuid),
                    # Your import schema currently reuses TaskOut which includes project_id. Fill it.
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

