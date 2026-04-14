from __future__ import annotations
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
import numpy as np
import pandas as pd
from models.task import Task
from models.constraint import Constraint, ConstraintRelation, earliest_start_from_constraint
from typing import Optional
from datetime import datetime, timedelta
from logic.generate_id import new_id
from logic.utils import _none_min
from models.sort_mode import SortMode


@dataclass_json
@dataclass
class Phase:
    name: str
    uuid: str = field(default_factory=new_id)
    task_order: list[str] = field(default_factory=list) # list of task uuids in order
    tasks: dict[str, Task] = field(default_factory=dict) # map of task uuid to task
    preceding_phase: Optional[Phase] = None
    constraints: list[Constraint] = field(default_factory=list)
    predecessor_ids: list[str] = field(default_factory=list)
    _sort_mode: SortMode = SortMode.manual
    planned: bool = True

    def __post_init__(self):
        legacy_predecessor_ids = list(self.predecessor_ids)
        self.predecessor_ids = []
        self.add_predecessor_ids(legacy_predecessor_ids)
        self._sync_predecessor_ids()

    @property
    def start_date(self) -> Optional[datetime]:
        if not self.tasks:
            return None
        return min(task.start_date for task in self.tasks.values())
    
    @property
    def end_date(self) -> Optional[datetime]:
        if not self.tasks:
            return None
        return max(task.end_date for task in self.tasks.values())
    

    @property
    def actual_start(self) -> Optional[datetime]:
        if not self.has_actuals:
            return None
        return min(task.actual_start for task in self.tasks.values() if isinstance(task.actual_start, datetime) and task.actual_start)

    @property
    def actual_end(self) -> Optional[datetime]:
        if not self.has_actuals:
            return None

        return max(task.actual_end for task in self.tasks.values() if isinstance(task.actual_end, datetime) and task.actual_end)
    
    @property
    def has_actuals(self) -> bool:
        """
            Returns true if the phase has at least one task with actual start/end,
            false otherwise.
        """
        if not self.tasks:
            return False
        
        for task in self.tasks.values():
            if task.actual_start is not None and task.actual_end is not None:
                return True
        return False
    
    @property
    def planned_duration(self) -> Optional[timedelta]:
        """Returns the planned duration of the phase as a timedelta."""
        if not self.tasks:
            return None
        return self.end_date - self.start_date
    
    @property
    def actual_duration(self) -> Optional[timedelta]:
        """Returns the actual duration of the phase as a timedelta, or None if actual start/end are not set."""
        if not self.actual_start or not self.actual_end:
            return None
        return self.actual_end - self.actual_start
    
    @property
    def status(self) -> str:
        if all(task.status == "NOT_STARTED" for task in self.tasks.values()):
            return "NOT_STARTED"
        
        if any(task.status == "IN_PROGRESS" for task in self.tasks.values()):
            return "IN_PROGRESS"
        
        if any(task.status == "IN_PROGRESS" for task in self.tasks.values()):
            return "IN_PROGRESS"
        
        return "BLOCKED"

    def to_excel_row(self) -> dict:
        return {
            "number": None,
            "name": self.name,
            "planned_duration": self.planned_duration.total_seconds() / 3600 if self.planned_duration else None,
            "planned_start": self.start_date,
            "planned_end": self.end_date,
            "id": None,
            "actual_duration": self.actual_duration.total_seconds() / 3600 if self.actual_duration else None,
            "actual_start": self.actual_start,
            "actual_end": self.actual_end,
            "notes": None,
            "predecessors": ",".join(self.predecessor_ids),
            "uuid": self.uuid
        }

    def _sort_tasks(self):
        if self._sort_mode == SortMode.by_planned_start:
            self.task_order = [
                t.id for t in sorted(
                    self.tasks.values(),
                    key=lambda t: (_none_min(t.planned_start), t.name)
                )
            ]
        elif self._sort_mode == SortMode.alphabetical:
            self.task_order = [
                t.id for t in sorted(
                    self.tasks.values(), key=lambda t: (t.name or "").lower()
                )
            ]
        else:  # manual
            # keep current order, do nothing
            pass


    @property
    def sort_mode(self) -> SortMode:
        return self._sort_mode

    @sort_mode.setter
    def sort_mode(self, mode: SortMode):
        # Only act if mode changes
        if mode != self._sort_mode:
            self._sort_mode = mode
            self._sort_tasks()
    
    def add_task(self, task: Task, position: int | None = None):
        task.phase_id = self.uuid
        self.tasks[task.uuid] = task

        if position is not None or self.sort_mode == SortMode.manual:
            if position is None or position > len(self.task_order):
                self.task_order.append(task.uuid)
            else:
                self.task_order.insert(position, task.uuid)
        elif self.sort_mode == SortMode.by_planned_start:
            # Binary-insert by planned_start
            key = _none_min(task.planned_start)
            idx = 0
            for i, tid in enumerate(self.task_order):
                if _none_min(self.tasks[tid].planned_start) > key:
                    idx = i
                    break
            else:
                idx = len(self.task_order)
            self.task_order.insert(idx, task.uuid)
        elif self.sort_mode == SortMode.alphabetical:
            name = (task.name or "").lower()
            idx = 0
            for i, tid in enumerate(self.task_order):
                if (self.tasks[tid].name or "").lower() > name:
                    idx = i
                    break
            else:
                idx = len(self.task_order)
            self.task_order.insert(idx, task.uuid)


    def add_predecessor(self, predesessor: str):
        self.add_constraint(
            Constraint(
                predecessor_id=predesessor,
                predecessor_kind="phase",
                relation_type=ConstraintRelation.FS,
            )
        )

    def add_constraint(self, constraint: Constraint) -> None:
        for existing in self.constraints:
            if (
                existing.predecessor_id == constraint.predecessor_id
                and existing.predecessor_kind == constraint.predecessor_kind
                and existing.relation_type == constraint.relation_type
                and existing.lag == constraint.lag
            ):
                return
        self.constraints.append(constraint)
        self._sync_predecessor_ids()

    def add_predecessor_ids(self, predecessor_ids: list[str]) -> None:
        for predecessor_id in predecessor_ids:
            self.add_predecessor(predecessor_id)

    def remove_constraints_for_predecessor(
        self,
        predecessor_id: str,
        *,
        predecessor_kind: str = "task",
    ) -> int:
        removed = 0
        if predecessor_kind == "task":
            for task in self.tasks.values():
                removed += task.remove_constraints_for_predecessor(
                    predecessor_id,
                    predecessor_kind=predecessor_kind,
                )
            return removed

        original_len = len(self.constraints)
        self.constraints = [
            constraint
            for constraint in self.constraints
            if not (
                constraint.predecessor_id == predecessor_id
                and constraint.predecessor_kind == predecessor_kind
            )
        ]
        self._sync_predecessor_ids()
        return original_len - len(self.constraints)

    def _sync_predecessor_ids(self) -> None:
        self.predecessor_ids = [
            constraint.predecessor_id
            for constraint in self.constraints
            if constraint.predecessor_kind == "phase"
        ]

    def edit_task(self, old_task: Task, new_task: Task):
        if not old_task.uuid in self.tasks.keys():
            raise RuntimeError(f"Provided task {old_task} not found.")

        new_task.uuid = old_task.uuid
        order = self.task_order.index(old_task.uuid)
        del self.tasks[old_task.uuid]
        self.tasks[new_task.uuid] = new_task
        self.task_order[order] = new_task.uuid
        self.resolve_schedule()
    
    @property
    def tasks_completed(self) -> int:
        return sum(1 for t in self.tasks.values() if t.completed)

    def delete_task(self, task: Task) -> int:
        """
            Deletes the provided task from the phase.
            Returns the number of tasks that had this task as a predecessor.

            If the task is not found, a RuntimeError is raised.
        """
        if not task.uuid in self.tasks.keys():
            raise RuntimeError(f"Provided task {task} not found.")
        
        # check for tasks using this as predecessor
        predecessor_count = self.remove_constraints_for_predecessor(
            task.uuid,
            predecessor_kind="task",
        )

        del self.tasks[task.uuid]
        self.task_order.remove(task.uuid)
        self.resolve_schedule()

        return predecessor_count

    def shift(self, delta: timedelta, shift_actuals: bool = False) -> None:
        if delta == timedelta(0):
            return
        for task in self.tasks.values():
            task.shift(delta=delta, shift_actuals=shift_actuals)

    def resolve_planned_dates(self, lookup, *, preserve_if_later: bool = True) -> bool:
        if not self.constraints or not self.tasks:
            return False

        required_starts: list[datetime] = []
        for constraint in self.constraints:
            predecessor_window = lookup(constraint)
            if predecessor_window is None:
                continue

            predecessor_start, predecessor_end = predecessor_window
            required_starts.append(
                earliest_start_from_constraint(
                    predecessor_start=predecessor_start,
                    predecessor_end=predecessor_end,
                    successor_duration=self.planned_duration,
                    relation=constraint.relation_type,
                    lag=constraint.lag,
                )
            )

        if not required_starts:
            return False

        earliest_allowed_start = max(required_starts)
        new_start = max(self.start_date, earliest_allowed_start) if preserve_if_later else earliest_allowed_start
        if new_start == self.start_date:
            return False

        self.shift(new_start - self.start_date)
        return True

    def resolve_schedule(self) -> None:
        resolved: set[str] = set()
        visiting: set[str] = set()

        def resolve_task(task_id: str) -> None:
            if task_id in resolved:
                return
            if task_id in visiting:
                raise ValueError(f"Cycle detected while resolving task constraints in phase {self.name}.")

            visiting.add(task_id)
            task = self.tasks[task_id]
            for constraint in task.constraints:
                if constraint.predecessor_kind != "task":
                    continue
                if constraint.predecessor_id in self.tasks:
                    resolve_task(constraint.predecessor_id)

            task.resolve_planned_dates(
                lambda constraint: (
                    None
                    if constraint.predecessor_kind != "task" or constraint.predecessor_id not in self.tasks
                    else (
                        self.tasks[constraint.predecessor_id].start_date,
                        self.tasks[constraint.predecessor_id].end_date,
                    )
                )
            )
            visiting.remove(task_id)
            resolved.add(task_id)

        for task_id in list(self.task_order):
            resolve_task(task_id)

    def __len__(self):
        """
        Returns the number of tasks in the phase.s
        """
        return len(self.task_order)

    def __str__(self):
        return f"Project Phase '{self.name}'. Start date: {self.start_date if self.tasks else None}. End date: {self.end_date if self.tasks else None}"
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "tasks": [self.tasks[tid].to_dict() for tid in self.task_order],
            "preceding_phase": self.preceding_phase.name if self.preceding_phase else None,
            "constraints": [constraint.to_dict() for constraint in self.constraints],
            "predecessor_ids": self.predecessor_ids,
            "uuid": self.uuid
        }
    
    @staticmethod
    def from_dict(data: dict) -> Phase:
        if not "name" in data:
            raise ValueError("Phase must have a name.")
        if not "tasks" in data:
            raise ValueError("Phase must have tasks.")
        
        phase = Phase.__new__(Phase)  
        phase.name = data["name"]
        tasks = [Task.from_dict(t) for t in data["tasks"]]
        phase.tasks = {task.uuid: task for task in tasks}
        phase.task_order = [task.uuid for task in tasks]
        phase.preceding_phase = data.get("preceding_phase", None)
        phase.constraints = [
            Constraint.from_dict(item)
            for item in data.get("constraints", [])
        ]
        phase.add_predecessor_ids(data.get("predecessor_ids", []))
        phase._sort_mode = data.get("_sort_mode", SortMode.manual)
        phase.planned = data.get("planned", True)
        phase.uuid = data.get("uuid", new_id())
        return phase
    
    def get_task_list(self) -> list[Task]:
        return [self.tasks[tid] for tid in self.task_order]

    @staticmethod 
    def to_df(phase: Phase) -> pd.DataFrame:
        return pd.DataFrame([t.to_dict() for t in phase.get_task_list()])
