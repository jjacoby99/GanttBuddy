from __future__ import annotations

import datetime as dt
from typing import Any

from models.constraint import Constraint, ConstraintRelation
from models.project import Project
from models.task import Task


def _same_moment(left: dt.datetime | None, right: dt.datetime | None) -> bool:
    if left is None or right is None:
        return False
    return left == right


def _build_preview_row(
    *,
    successor_kind: str,
    successor_phase_name: str,
    successor_name: str,
    successor_id: str,
    predecessor_phase_name: str,
    predecessor_name: str,
    predecessor_id: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "Type": successor_kind.title(),
        "Successor Phase": successor_phase_name,
        "Successor": successor_name,
        "Successor ID": successor_id,
        "Predecessor Phase": predecessor_phase_name,
        "Predecessor": predecessor_name,
        "Predecessor ID": predecessor_id,
        "Relation": ConstraintRelation.FS.value,
        "Lag (hrs)": 0.0,
        "Reason": reason,
    }


def _is_unplanned_task(task: Task) -> bool:
    return task.planned_duration == dt.timedelta(0) and task.actual_duration not in (None, dt.timedelta(0))


def infer_missing_project_constraints(
    project: Project,
    *,
    apply: bool = True,
) -> dict[str, Any]:
    task_preview_rows: list[dict[str, Any]] = []
    phase_preview_rows: list[dict[str, Any]] = []
    task_constraint_count = 0
    phase_constraint_count = 0
    task_successor_ids: set[str] = set()
    phase_successor_ids: set[str] = set()

    for phase in project.phases.values():
        if not phase.tasks:
            continue

        tasks_in_phase = [phase.tasks[task_id] for task_id in phase.task_order]
        for index, successor in enumerate(tasks_in_phase):
            if not any(constraint.predecessor_kind == "task" for constraint in successor.constraints):
                inferred_constraints: list[Constraint] = []

                if _is_unplanned_task(successor):
                    if index > 0:
                        predecessor = tasks_in_phase[index - 1]
                        inferred_constraints.append(
                            Constraint(
                                predecessor_id=predecessor.uuid,
                                predecessor_kind="task",
                                relation_type=ConstraintRelation.FS,
                            )
                        )
                        task_preview_rows.append(
                            _build_preview_row(
                                successor_kind="task",
                                successor_phase_name=phase.name,
                                successor_name=successor.name,
                                successor_id=successor.uuid,
                                predecessor_phase_name=phase.name,
                                predecessor_name=predecessor.name,
                                predecessor_id=predecessor.uuid,
                                reason="Unplanned task stitched to the previous task in phase order.",
                            )
                        )
                else:
                    for predecessor in tasks_in_phase[:index]:
                        if not _same_moment(successor.start_date, predecessor.end_date):
                            continue

                        inferred_constraints.append(
                            Constraint(
                                predecessor_id=predecessor.uuid,
                                predecessor_kind="task",
                                relation_type=ConstraintRelation.FS,
                            )
                        )
                        task_preview_rows.append(
                            _build_preview_row(
                                successor_kind="task",
                                successor_phase_name=phase.name,
                                successor_name=successor.name,
                                successor_id=successor.uuid,
                                predecessor_phase_name=phase.name,
                                predecessor_name=predecessor.name,
                                predecessor_id=predecessor.uuid,
                                reason="Start date matched an earlier task's end date.",
                            )
                        )

                for constraint in inferred_constraints:
                    if apply:
                        successor.add_constraint(constraint)

                if inferred_constraints:
                    task_constraint_count += len(inferred_constraints)
                    task_successor_ids.add(successor.uuid)

            if not _is_unplanned_task(successor) or index >= len(tasks_in_phase) - 1:
                continue

            next_task = tasks_in_phase[index + 1]
            if any(constraint.predecessor_kind == "task" for constraint in next_task.constraints):
                continue

            inferred_constraint = Constraint(
                predecessor_id=successor.uuid,
                predecessor_kind="task",
                relation_type=ConstraintRelation.FS,
            )
            if apply:
                next_task.add_constraint(inferred_constraint)

            task_constraint_count += 1
            task_successor_ids.add(next_task.uuid)
            task_preview_rows.append(
                _build_preview_row(
                    successor_kind="task",
                    successor_phase_name=phase.name,
                    successor_name=next_task.name,
                    successor_id=next_task.uuid,
                    predecessor_phase_name=phase.name,
                    predecessor_name=successor.name,
                    predecessor_id=successor.uuid,
                    reason="Task after an unplanned task was stitched to that unplanned task.",
                )
            )

    ordered_phases = [project.phases[phase_id] for phase_id in project.phase_order]
    for index, successor in enumerate(ordered_phases):
        if successor.start_date is None or successor.end_date is None:
            continue
        if any(constraint.predecessor_kind == "phase" for constraint in successor.constraints):
            continue

        inferred_constraints = []
        for predecessor in ordered_phases[:index]:
            if predecessor.end_date is None:
                continue
            if not _same_moment(successor.start_date, predecessor.end_date):
                continue

            inferred_constraints.append(
                Constraint(
                    predecessor_id=predecessor.uuid,
                    predecessor_kind="phase",
                    relation_type=ConstraintRelation.FS,
                )
            )
            phase_preview_rows.append(
                _build_preview_row(
                    successor_kind="phase",
                    successor_phase_name=successor.name,
                    successor_name=successor.name,
                    successor_id=successor.uuid,
                    predecessor_phase_name=predecessor.name,
                    predecessor_name=predecessor.name,
                    predecessor_id=predecessor.uuid,
                    reason="Start date matched an earlier phase's end date.",
                )
            )

        for constraint in inferred_constraints:
            if apply:
                successor.add_constraint(constraint)

        if inferred_constraints:
            phase_constraint_count += len(inferred_constraints)
            phase_successor_ids.add(successor.uuid)

    if apply and (task_constraint_count or phase_constraint_count):
        project.resolve_schedule()

    return {
        "project_id": project.uuid,
        "task_successor_count": len(task_successor_ids),
        "task_constraint_count": task_constraint_count,
        "phase_successor_count": len(phase_successor_ids),
        "phase_constraint_count": phase_constraint_count,
        "preview_rows": task_preview_rows + phase_preview_rows,
    }
