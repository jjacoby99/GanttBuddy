from __future__ import annotations
import datetime as dt

from typing import Callable, Optional
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from models.project_settings import ProjectSettings
from models.constraint import Constraint, ConstraintRelation, earliest_start_from_constraint
from exceptions.date_error import InvalidDateError
from exceptions.time_error import InvalidTimeError
from logic.generate_id import new_id
import pandas as pd
from typing import Literal

from enum import Enum

class TaskType(str, Enum):
    INCH = "INCH"
    STRIP = "STRIP"
    INSTALL = "INSTALL"
    GENERIC = "GENERIC"

class TaskStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETE = "COMPLETE"

@dataclass_json
@dataclass
class Task:
    name: str
    start_date: dt.datetime
    end_date: dt.datetime
    actual_start: Optional[dt.datetime] = None
    actual_end: Optional[dt.datetime] = None
    note: str = ""
    uuid: str = field(default_factory=new_id)
    constraints: list[Constraint] = field(default_factory=list)
    predecessor_ids: list[str] = field(default_factory=list)
    phase_id: str = ""
    status: Literal["NOT_STARTED", "IN_PROGRESS", "BLOCKED", "COMPLETE"] = "NOT_STARTED"
    planned: bool = field(default=True) 
    task_type: TaskType = field(default=TaskType.GENERIC)

    def __post_init__(self):
        deduped_constraints: list[Constraint] = []
        seen_predecessors: set[tuple[str, str]] = set()
        for constraint in self.constraints:
            dedupe_key = (constraint.predecessor_id, constraint.predecessor_kind)
            if dedupe_key in seen_predecessors:
                continue
            seen_predecessors.add(dedupe_key)
            deduped_constraints.append(constraint)
        self.constraints = deduped_constraints
        legacy_predecessor_ids = list(self.predecessor_ids)
        self.predecessor_ids = []
        self.add_predecessor_ids(legacy_predecessor_ids)
        self._sync_predecessor_ids()

    def to_dict(self) -> dict:
        return {"Task": self.name, 
                "Start": self.start_date, 
                "Finish": self.end_date, 
                "Actual_Start": self.actual_start,
                "Actual_Finish": self.actual_end,
                "Note": self.note,
                "constraints": [constraint.to_dict() for constraint in self.constraints],
                "predecessor_ids": self.predecessor_ids,
                "uuid": self.uuid,
                "phase_id": self.phase_id,
                "status": self.status,
                "planned": self.planned,
                "task_type": self.task_type,
                }
    
    def __str__(self) -> str:
        return f"Task(name = {self.name}, start_date={self.start_date}, end_date={self.end_date}, actual_start={self.actual_start}, actual_end={self.actual_end}, note={self.note})"

    @property
    def planned_duration(self) -> dt.timedelta:
        """Returns the planned duration of the task as a timedelta."""
        return self.end_date - self.start_date
    
    @property
    def completed(self) -> bool:
        if pd.isna(self.actual_start) or pd.isna(self.actual_end):
            return False
        if self.actual_start is None or self.actual_end is None:
            return False
        return True
    
    @property
    def actual_duration(self) -> Optional[dt.timedelta]:
        """Returns the actual duration of the task as a timedelta, or None if actual start/end are not set."""
        if not self.completed:
            return None
        return self.actual_end - self.actual_start
    
    @property
    def is_milestone(self) -> bool:
        """ 
            A milestone is a task that has the same start and end datetimes.
            
            For a task with no actuals, this means |planned_end - planned_start| <= eps
            Where eps is some small time.

            For a task with actuals, both the planned and actual duration must be
            less than some epsilon. 

            It is important to make this distinction because "unplanned" tasks have a 
            zero planned_duration, but a non-zero actual_duration. Therefore, we want
            these tasks to not be counted as milestones. 
        """
        eps = dt.timedelta(seconds=1)
        pdur = self.planned_duration
        if not self.completed:
            return pdur <= eps
        
        adur = self.actual_duration
        return adur <= eps and pdur <= eps
        
    @property
    def variance(self) -> Optional[dt.timedelta]:
        """Returns the variance of the task (actual duration - planned duration) as a timedelta, or None if actual start/end are not set."""
        if not self.completed:
            return None
        return self.actual_duration - self.planned_duration

    @property
    def timezone_aware(self) -> bool:
        """
            Checks start_date, end_date, actual_start, and actual_end to see if all non null timestamps are timezone aware.
        """

        fields = (
            self.start_date,
            self.end_date,
            self.actual_start,
            self.actual_end,
        )
        return all(
            dt is None or (dt.tzinfo is not None and dt.utcoffset() is not None)
            for dt in fields
        )

    def infer_status(self) -> None:
        """
            Sets self.status based on actual_start and actual_end 
        """

        if self.completed:
            self.status = "COMPLETE"
            return
        
        if self.actual_start:
            self.status = "IN_PROGRESS"
            return
        
        # no way to infer blocked-ness from available data
        # assume not started
        self.status = "NOT_STARTED"

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
            "notes": self.note if self.note else "",
            "predecessors": ",".join(self.predecessor_ids),
            "uuid": self.uuid,
            "planned": self.planned
        } 
    
    @staticmethod
    def from_dict(data: dict) -> Task:
        if not "Task" in data:
            raise ValueError("Task must have a name.")
        if not "Start" in data:
            raise ValueError("Task must have a start date.")
        if not "Finish" in data:   
            raise ValueError("Task must have an end date.")
            
        task = Task.__new__(Task)  # Create an uninitialized instance
        task.name = data["Task"]
        task.start_date = data["Start"]
        task.end_date = data["Finish"]
        task.actual_start = data.get("Actual_Start", None)
        task.actual_end = data.get("Actual_Finish", None)
        task.note = data.get("note", "")
        task.preceding_task = data.get("preceding_task", None)
        task.constraints = [
            Constraint.from_dict(item)
            for item in data.get("constraints", [])
        ]
        task.add_predecessor_ids(data.get("predecessor_ids", []))
        task.uuid = data.get("uuid", new_id())
        task.phase_id = data.get("phase_id", "")
        task.status = data.get("status", "NOT_STARTED")
        task.planned = data.get("planned", True)
        task.task_type = data.get("task_type", TaskType.GENERIC)
        return task

    def add_constraint(self, constraint: Constraint) -> None:
        for index, existing in enumerate(self.constraints):
            if (
                existing.predecessor_id == constraint.predecessor_id
                and existing.predecessor_kind == constraint.predecessor_kind
            ):
                self.constraints[index] = constraint
                self._sync_predecessor_ids()
                return
        self.constraints.append(constraint)
        self._sync_predecessor_ids()

    def add_predecessor_ids(self, predecessor_ids: list[str]) -> None:
        for predecessor_id in predecessor_ids:
            self.add_constraint(
                Constraint(
                    predecessor_id=predecessor_id,
                    predecessor_kind="task",
                    relation_type=ConstraintRelation.FS,
                )
            )

    def remove_constraints_for_predecessor(
        self,
        predecessor_id: str,
        *,
        predecessor_kind: str = "task",
    ) -> int:
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
            if constraint.predecessor_kind == "task"
        ]

    def resolve_planned_dates(
        self,
        lookup: Callable[[Constraint], tuple[dt.datetime, dt.datetime] | None],
        *,
        preserve_if_later: bool = True,
    ) -> bool:
        if not self.constraints:
            return False

        required_starts: list[dt.datetime] = []
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

        duration = self.planned_duration
        self.start_date = new_start
        self.end_date = new_start + duration
        return True

    def calculate_end_date(self, duration: int, settings: ProjectSettings) -> dt.datetime:
        """
            Calculate the end date of a task given a start date, duration (in days), and project settings.
            This function takes into account working hours, working days, and holidays based on the provided settings.

            if the start_date is on a holiday or weekend, a DateError is raised.

            if the start_date time is outside of working hours, a TimeError is raised.
        """

        if not settings.is_working_day(self.start_date):
            raise InvalidDateError(f"Start date {self.start_date.date()} is not a working day.")
        
        if settings.is_holiday(self.start_date):
            raise InvalidDateError(f"Start date {self.start_date.date()} is a holiday.")
        
        if not settings.within_working_hours(self.start_date.time()):
            raise InvalidTimeError(f"Start time {self.start_date.time()} is outside of working hours ({settings.work_start_time} - {settings.work_end_time}).")
        pass
    
        #current_date = self.start_date
        #day_remaining = settings.work_end_time - self.start_date.time()
        #time_allocated = day_remaining
        #while time_allocated < duration:
            
        #    current_date += datetime.timedelta(days=1)
        #    if settings.is_working_day(current_date) and not settings.is_holiday(current_date):
        #        days_added += 1
        
        #return current_date


    def shift(self, delta=dt.timedelta, shift_actuals=False):
        """
        Shifts a given task back by the provided delta.
        Only affects actual start and end_dates if shift_actuals is True
        Ignores predecessors

        @params
            delta (datetime.timedelta): change in time to shift task backwards (negative) or forwards (positive)
            shift_actuals (bool): flag (False by default) to control whether actual durations are effected by shift
        """
        self.start_date += delta
        self.end_date += delta

        if shift_actuals:
            self.actual_start += delta
            self.actual_end += delta


