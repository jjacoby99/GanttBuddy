# snapshot_adapter.py
from __future__ import annotations

from datetime import datetime, time
from typing import Any, Optional

from models.project import Project, ProjectType
from models.phase import Phase
from models.project_metadata import RelineMetadata
from models.task import Task, TaskType
from models.project_settings import ProjectSettings
from models.shift_schedule import ShiftAssignment, ShiftDefinition

import pytz

def _parse_dt(x: str | None) -> datetime | None:
    if not x:
        return None
    # Handles "2026-01-26T07:00:00"
    return datetime.fromisoformat(x).astimezone()


def _parse_time(x: str | None) -> time | None:
    if not x:
        return None
    # Handles "07:00:00"
    return time.fromisoformat(x)


def _mask_to_working_days(mask: int) -> tuple[bool, bool, bool, bool, bool, bool, bool]:
    """
    Interprets mask bits as:
      bit0=Mon, bit1=Tue, ... bit6=Sun
    Example: 15 (0b0001111) => Mon..Thu True, Fri..Sun False
    """
    return tuple(bool((mask >> i) & 1) for i in range(7))  # type: ignore[return-value]


def coerce_task_type(x: Any) -> TaskType:
    if x is None:
        return TaskType.GENERIC

    # if backend ever sends a TaskType-like object or weird type
    s = str(x).strip().upper()

    try:
        return TaskType(s)
    except ValueError:
        # Backward/forward compatibility: unknown types won’t crash old clients
        return TaskType.GENERIC

def get_shift_assignments(shift_assignments: list) -> list[ShiftAssignment]:
    return [ShiftAssignment(**sa) for sa in shift_assignments]


def get_shift_definition(shift_definition: dict) -> ShiftDefinition:
    try:
        sd = ShiftDefinition(**shift_definition)
        if not sd.id:
            raise KeyError("Shift definition from backend must have an id.")
        return sd
    except Exception as e:
        raise e

def snapshot_to_project(snapshot: dict[str, Any]) -> tuple[Project, Optional[RelineMetadata]]:
    p = snapshot["project"]
    s = snapshot["settings"]
    shift_def = snapshot["shift_definition"]

    if p.get("project_type") == "MILL_RELINE":
        metadata = snapshot.get("metadata", None)
        if not metadata:
            raise ValueError("Mill Reline project snapshot must include metadata.")
        
        reline_metadata = RelineMetadata(
            schema_version=metadata.get("schema_version", 1),
            site_id=metadata["site_id"],
            site_name=metadata["site_name"], 
            mill_id=metadata["mill_id"],
            mill_name=metadata["mill_name"], 
            vendor=metadata["vendor"],
            liner_system=metadata["liner_system"],
            campaign_id=metadata["campaign_id"],
            scope=metadata["scope"],
            liner_type=metadata["liner_type"],
            supervisor=metadata["supervisor"],
            notes=metadata["notes"],
        )
        
    shift_assignments = snapshot["shift_assignments"]
    phases = snapshot.get("phases", [])
    tasks = snapshot.get("tasks", [])
    task_preds = snapshot.get("task_predecessors", [])

    # Build predecessor map: task_id -> [pred_id, ...]
    pred_map: dict[str, list[str]] = {}
    for edge in task_preds:
        tid = edge["task_id"]
        pid = edge["predecessor_task_id"]
        pred_map.setdefault(tid, []).append(pid)

    settings = ProjectSettings(
        work_all_day=bool(s.get("work_all_day", False)),
        work_start_time=_parse_time(s.get("work_start_time")),
        work_end_time=_parse_time(s.get("work_end_time")),
        working_days=_mask_to_working_days(int(s.get("working_days_mask", 0))),
        observe_state_holidays=bool(s.get("observe_state_holidays", False)),
        province=s.get("province"),
        duration_resolution=s.get("duration_resolution", "hours"),
    )

    project_type_str = p.get("project_type", "GENERIC")
    try:
        project_type = ProjectType[project_type_str]
    except KeyError:
        project_type = ProjectType.GENERIC

    project = Project(
        name=p.get("name", ""),
        uuid=p.get("id"),  # backend id becomes frontend uuid
        description=p.get("description"),
        settings=settings,
        project_type=project_type
    )

    sd = get_shift_definition(shift_definition=shift_def)
    project.shift_definition = sd

    sas = get_shift_assignments(shift_assignments=shift_assignments)
    project.shift_assignments = sas
    # Create phases ordered by backend "position"
    phases_sorted = sorted(phases, key=lambda x: x.get("position", 0))
    for ph in phases_sorted:
        phase = Phase(
            name=ph.get("name", ""),
            uuid=ph.get("id"),
            planned=ph.get("planned", True)
        )
        project.add_phase(phase, position=ph.get("position", None))

    # Group tasks by phase, ordered by backend "position"
    tasks_by_phase: dict[str, list[dict[str, Any]]] = {}
    for t in tasks:
        tasks_by_phase.setdefault(t["phase_id"], []).append(t)

    for phase_id, phase_tasks in tasks_by_phase.items():
        if phase_id not in project.phases:
            # Snapshot is inconsistent; skip or raise depending on how strict you want to be.
            continue

        for t in sorted(phase_tasks, key=lambda x: x.get("position", 0)):
            task = Task(
                name=t.get("name", ""),
                start_date=_parse_dt(t.get("planned_start")),
                end_date=_parse_dt(t.get("planned_end")),
                actual_start=_parse_dt(t.get("actual_start")),
                actual_end=_parse_dt(t.get("actual_end")),
                note=t.get("note", "") or "",
                uuid=t.get("id"),
                predecessor_ids=pred_map.get(t.get("id"), []),
                phase_id=phase_id,
                status=t.get("status", "NOT_STARTED"),
                planned=t.get("planned", True),
                task_type=coerce_task_type(t.get("task_type", TaskType.GENERIC)),
            )
            project.add_task_to_phase(project.phases[phase_id], task)

    return project, reline_metadata
 