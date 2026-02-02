# snapshot_adapter.py
from __future__ import annotations

from datetime import datetime, time
from typing import Any

from models.project import Project
from models.phase import Phase
from models.task import Task
from models.project_settings import ProjectSettings

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


def snapshot_to_project(snapshot: dict[str, Any]) -> Project:
    p = snapshot["project"]
    s = snapshot["settings"]
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

    project = Project(
        name=p.get("name", ""),
        uuid=p.get("id"),  # backend id becomes frontend uuid
        description=p.get("description"),
        settings=settings,
    )

    # Create phases ordered by backend "position"
    phases_sorted = sorted(phases, key=lambda x: x.get("position", 0))
    for ph in phases_sorted:
        phase = Phase(
            name=ph.get("name", ""),
            uuid=ph.get("id"),
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
                status=t.get("status", "NOT_STARTED")
            )
            project.add_task_to_phase(project.phases[phase_id], task)

    return project
 