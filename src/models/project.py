from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from models.task import Task
from models.phase import Phase
from models.project_settings import ProjectSettings
from datetime import datetime
from logic.generate_id import new_id
from logic.utils import _none_min
from models.sort_mode import SortMode

@dataclass
class Project:
    name: str
    uuid: str = field(default_factory=new_id)
    description: Optional[str] = None
    phases: dict[str, Phase] = field(default_factory=dict) # map of phase uuid to phase
    phase_order: list[str] = field(default_factory=list) # list of phase uuids in order
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    _sort_mode: SortMode = SortMode.manual

    @property
    def start_date(self) -> Optional[datetime]:
        if not self.phases:
            return None
        
        return min(phase.start_date for phase in self.phases.values() if phase.start_date is not None)
    
    @property
    def end_date(self) -> Optional[datetime]:
        if not self.phases:
            return None
        
        return max(phase.start_date for phase in self.phases.values() if phase.start_date is not None)
    
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

    def completed_hours(self) -> float:
        """
            Returns the total completed hours across all tasks in the project up to as_of datetime.
            If as_of is None, considers all actuals.
        """
        total = 0.0        
        for task in self.get_task_list():
            if task.actual_duration is not None:
                total += task.actual_duration.total_seconds() / 3600
        return total
        
    
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

    def add_task_to_phase(self, phase: Phase, task: Task): 
        if not phase.uuid in self.phases.keys():
            raise ValueError(f"Provided phase {phase.name} does not exist.")
        if not isinstance(task, Task):
            raise ValueError(f"Provided task {task} is not a valid Task instance.")
        self.phases[phase.uuid].add_task(task)          

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

