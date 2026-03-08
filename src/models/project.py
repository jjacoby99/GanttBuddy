from __future__ import annotations
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
import pandas as pd
from typing import Optional, Literal
from models.task import Task, TaskType
from models.phase import Phase
from models.project_settings import ProjectSettings
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from logic.generate_id import new_id
from logic.utils import _none_min
from models.sort_mode import SortMode
import pandas as pd
from models.project_type import ProjectType
from models.shift_schedule import ShiftAssignment, ShiftDefinition
from enum import Enum

@dataclass_json
@dataclass
class Project:
    name: str
    uuid: str = field(default_factory=new_id)
    description: Optional[str] = None
    phases: dict[str, Phase] = field(default_factory=dict) # map of phase uuid to phase
    phase_order: list[str] = field(default_factory=list) # list of phase uuids in order
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    _sort_mode: SortMode = SortMode.manual
    project_type: ProjectType = field(default=ProjectType.GENERIC)
    shift_assignments: Optional[list[ShiftAssignment]] = None
    shift_definition: Optional[ShiftDefinition] = None
    site_id: Optional[str] = None
    timezone: ZoneInfo = field(default=ZoneInfo("America/Vancouver"))

    @property
    def start_date(self) -> Optional[datetime]:
        if not self.phases:
            return None
        
        return min(phase.start_date for phase in self.phases.values() if phase.start_date is not None)
    
    @property
    def end_date(self) -> Optional[datetime]:
        if not self.phases:
            return None
        
        return max(phase.end_date for phase in self.phases.values() if phase.end_date is not None)
    
    @property
    def actual_start(self) -> Optional[datetime]:
        if not self.has_actuals:
            return None
        
        return min(phase.actual_start for phase in self.phases.values() if phase.actual_start is not None)
    
    @property
    def actual_end(self) -> Optional[datetime]:
        if not self.has_actuals:
            return None
        
        return max(phase.actual_end for phase in self.phases.values() if phase.actual_end is not None)

    @property
    def first_ttfi_cutoff(self) -> Optional[datetime]:
        """ 
            Looks at shift_definition and determines when the cutoff should be for ttfi metrics.
            This is determined by looking at when the first inch was planned to start.

            If the inch was planned to start in [day_start_time, dat_start_time + shift_length_hours]
            then the cutoff time will be the date of the first inch @ day_start_time
            else, the cutoff time will be the date of the first inch @ night_start_time

            The intent of this property is to determine what shift within a project Inching should 
            commence.

        """
        if not self.shift_definition or not self.project_type == ProjectType.MILL_RELINE:
            return None
        first_planned_inch = self.first_task_of_type(TaskType.INCH, planned=True)

        if not first_planned_inch: # no inch tasks found
            return None
        
        shift_dur_hours = self.shift_definition.shift_length_hours

        day_start = datetime.combine(first_planned_inch.date(), self.shift_definition.day_start_time).astimezone()
        day_end = day_start + timedelta(hours=shift_dur_hours)
        
        if first_planned_inch >= day_start and first_planned_inch <= day_end:
            return day_start
        
        night_start = datetime.combine(first_planned_inch.date(), self.shift_definition.night_start_time).astimezone()
        night_end = night_start + timedelta(hours=shift_dur_hours)

        if first_planned_inch >= night_start and first_planned_inch <= night_end:
            return night_start
        
        return None

    def first_task_of_type(self, task_type: TaskType, planned: bool = True) -> Optional[datetime]:
        """ 
            Searches all tasks in the project looking for the first task with task.task_type == task_type.

            if planned, this returns the PLANNED START datetime of the first task with the given type
            else, this returns the ACTUAL START datetime of the first task with the given type

            if no task of the given type is present in the project, None is returned.
        """
        for task in self.get_task_list():
            if task.task_type == task_type:
                if planned:
                    return task.start_date
                
                if not planned and task.actual_start is not None:
                    return task.actual_start
                
                return None
        return None

    def tasks_in_range(self, start_dt: datetime, end_dt: datetime, 
                       planned: bool = True, mode: Literal["strict", "overlap"] = "strict"):
        """ 
            Returns all tasks that fall within a given time window from start_dt -> end_dt.

            Parameter options:

            1. planned:
            - if planned is True, the function will return tasks with planned start / end in the range
            - if planned is False, the function will return tasks with actual start / end in the range

            2. mode:
            - if mode is "strict", only tasks with actual start and end in the datetime range will be returned
            - if mode is "overlap", tasks with start OR end in (start_dt, end_dt) will be returned.

            Exceptions:
            - ValueError thrown if end_dt < start_dt 
        """
        if start_dt > end_dt:
            raise ValueError("Window start must be less than the window end.")
        
        tasks_in_range = []
        for task in self.get_task_list():
            
            start, end = (task.start_date, task.end_date) if planned else (task.actual_start, task.actual_end)

            start_in_range = (start > start_dt and start < end_dt)
            end_in_range = (end > start_dt and end < end_dt)

            if mode == "overlap" and (start_in_range or end_in_range):
                tasks_in_range.append(task)
                continue

            if mode == "strict" and (start_in_range and end_in_range):
                tasks_in_range.append(task)
                continue

            if end > end_dt:
                break # tasks in ascending order
        
        return tasks_in_range

    def completed_hours(self) -> tuple[float, float]:
        """
            Returns the total actual hours and planned hours across all tasks in the project up to as_of datetime.
        """
        total_act = 0.0
        total_planned = 0.0     
        for task in self.get_task_list():
            if task.completed and task.planned:
                total_act += task.actual_duration.total_seconds() / 3600
                total_planned += task.planned_duration.total_seconds() / 3600
        return total_act, total_planned
    
    def unplanned_hours(self) -> float:
        """
            Returns the total hours of work that have been completed but were not planned.
        """
        total = 0.0        
        for task in self.get_task_list():
            if task.completed and not task.planned:
                total += task.actual_duration.total_seconds() / 3600
        return total
    
    def average_planned_duration(self, task_type: TaskType) -> float:
        total = timedelta(seconds=0)
        count = 0
        for task in self.get_task_list():
            if task.task_type == task_type and task.planned:
                total += task.planned_duration
                count += 1
        
        return float(total.total_seconds() / 3600 / count) if count > 0 else 0.0
    
    @property
    def has_task(self) -> bool:
        """
            Returns true if the project has at least one task,
            false otherwise.
        """
        if not self.phases:
            return False
        
        for phase in self.phases.values():
            if phase.tasks:
                return True
        return False
    
    @property
    def has_actuals(self) -> bool:
        """
            Returns true if the project has at least one task with actual start/end,
            false otherwise.
        """
        if not self.phases:
            return False
        
        for phase in self.phases.values():
            for task in phase.tasks.values():
                if task.actual_start is not None and task.actual_end is not None:
                    return True
        return False

    def __len__(self) -> int:
        """
            Returns the number of phases and tasks in the project.
        """
        count = len(self.phases)
        for phase in self.phases.values():
            count += len(phase.tasks)
        return count

    def find_phase(self, task: Task) -> Phase:
        """
            Searches the project phases to see if the provided Task exists.
            If the task exists within a phase, the phase is returned.
            If the task does not exist, a ValueError is thrown.
        """
        for phase in self.phases.values():
            if task in phase.tasks.values():
                return phase
        
        raise ValueError(f"Task {task.name} not found in any project phase.")

    def update_task(self, phase: Phase, old_task: Task, new_task: Task):
        """
            Updates a task within the project.
            Searches for the old_task, and if found, replaces it with new_task.
            If old_task is not found, a ValueError is thrown.
        """        
        self.phases[phase.uuid].edit_task(old_task, new_task)

        # handle increased / decreased durations based on predecessors   

    def add_phase(self, phase: Phase, position: int | None = None):
        self.phases[phase.uuid] = phase
        if position is not None or self._sort_mode == SortMode.manual:
            if position is None or position > len(self.phase_order):
                self.phase_order.append(phase.uuid)
            else:
                self.phase_order.insert(position, phase.uuid)
        elif self.sort_mode == SortMode.by_planned_start:
            # Binary-insert by planned_start
            key = _none_min(phase.start_date)
            idx = 0
            for i, pid in enumerate(self.phase_order):
                if _none_min(self.phases[pid].start_date) > key:
                    idx = i
                    break
            else:
                idx = len(self.phase_order)
            self.phase_order.insert(idx, phase.uuid)
        elif self.sort_mode == SortMode.alphabetical:
            name = (phase.name or "").lower()
            idx = 0
            for i, pid in enumerate(self.phase_order):
                if (self.phase[pid].name or "").lower() > name:
                    idx = i
                    break
            else:
                idx = len(self.phase_order)
            self.phase_order.insert(idx, phase.uuid)


    def get_phase_index(self, phase: Phase) -> int:
        '''
            Gets the zero index of a provided phase within a project.

            Raises a RuntimeError if the project doesn't contain any phases

            Raises a ValueError if the provided phase does not exist within the project's phases
        '''
        if not self.phases:
            raise RuntimeError(f"Project {self.name} does not contain any phases.")
        
        if not phase.uuid in self.phases.keys():
            raise ValueError(f"Provided phase {phase.name} does not exist.")
        
        return self.phase_order.index(phase.uuid)

    def add_task_to_phase(self, phase: Phase, task: Task, position: int | None = None): 
        if not phase.uuid in self.phases.keys():
            raise ValueError(f"Provided phase {phase.name} does not exist.")
        self.phases[phase.uuid].add_task(task, position=position)          

    def delete_phase(self, phase: Phase):
        if not phase.uuid in self.phases.keys():
            raise RuntimeError(f"Provided phase {phase} not found.")
        
        # check for phases using this as predecessor
        for p in self.phases.values():
            if p.predecessor_ids == phase.uuid:
                p.predecessor_ids.remove(phase.uuid)
        del self.phases[phase.uuid]
        self.phase_order.remove(phase.uuid)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "phases": [p.to_dict() for p in self.phases.values()],
            "settings": self.settings.to_dict()
        }
    
    def get_task_list(self) -> list[Task]:
        tasks: list[Task] = []
        for pid in self.phase_order:
            phase = self.phases[pid]
            tasks.extend(phase.get_task_list())
        return tasks
    
    def get_task_idx(self, task: Task) -> int:
        """
            Returns the 0 indexed position of the provided task within the project task list.

            If the task does not exist, a ValueError is raised.
        """

        task_list = self.get_task_list()
        for i, t in enumerate(task_list):
            if t.uuid == task.uuid:
                return i
        raise ValueError(f"Task {task.name} not found in project {self.name}.")
    
    @property
    def planned_duration(self) -> timedelta:
        """
            Returns a timedelta object that is the difference of the project's
            end date and start date.
        """
        return self.end_date - self.start_date

    def get_phase_df(self) -> pd.DataFrame:
        data = {
            "phase": [],
            "planned_start": [],
            "planned_end": [],
            "planned_duration": [],
            "actual_start": [],
            "actual_end": [],
            "actual_duration": [],
            "num_tasks": []
        }
        for pid in self.phase_order:
            phase = self.phases[pid]
            data["phase"].append(phase.name)
            data["planned_start"].append(phase.start_date)
            data["planned_end"].append(phase.end_date)

            pdur = phase.planned_duration
            data["planned_duration"].append(pdur.total_seconds() / 3600)

            data["actual_start"].append(phase.actual_start if phase.actual_start else None)
            data["actual_end"].append(phase.actual_end if phase.actual_end else None)

            adur = phase.actual_duration
            data["actual_duration"].append(
                adur.total_seconds() / 3600 if adur is not None else None
            )

            data["num_tasks"].append(len(phase))

        return pd.DataFrame(data)

    def get_task_df(self) -> pd.DataFrame:
        tasks = self.get_task_list()
        data = {
            "task": [],
            "planned_start": [],
            "planned_end": [],
            "planned_duration": [],
            "actual_start": [],
            "actual_end": [],
            "actual_duration": [],
            "notes": [],
            "pid": []
        }

        for task in tasks:
            data["task"].append(task.name)
            data["pid"].append(task.phase_id)
            data["planned_start"].append(task.start_date)
            data["planned_end"].append(task.end_date)

            pdur = task.planned_duration
            data["planned_duration"].append(pdur.total_seconds() / 3600)

            data["actual_start"].append(task.actual_start if task.actual_start else None)
            data["actual_end"].append(task.actual_end if task.actual_end else None)

            adur = task.actual_duration
            data["actual_duration"].append(
                adur.total_seconds() / 3600 if adur is not None else None
            )

            data["notes"].append(task.note if task.note else "")

        return pd.DataFrame(data)