from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from models.task import Task
from models.phase import Phase
from models.project_settings import ProjectSettings
from datetime import datetime

@dataclass
class Project:
    name: str
    description: Optional[str] = None
    phases: list[Phase] = field(default_factory=list)
    settings: ProjectSettings = field(default_factory=ProjectSettings)

    @property
    def start_date(self) -> Optional[datetime]:
        if not self.phases:
            return None
        
        return self.phases[0]
    
    @property
    def end_date(self) -> Optional[datetime]:
        if not self.phases:
            return None
        
        return self.phases[-1]
    
    @property
    def has_task(self) -> bool:
        """
            Returns true if the project has at least one task,
            false otherwise.
        """
        if not self.phases:
            return False
        
        for phase in self.phases:
            if phase.tasks:
                return True
        return False
    
    def find_phase(self, task: Task) -> Phase:
        """
            Searches the project phases to see if the provided Task exists.
            If the task exists within a phase, the phase is returned.
            If the task does not exist, a ValueError is thrown.
        """
        for phase in self.phases:
            if task in phase.tasks:
                return phase
        
        raise ValueError(f"Task {task.name} not found in any project phase.")

    def update_task(self, phase: Phase, old_task: Task, new_task: Task):
        """
            Updates a task within the project.
            Searches for the old_task, and if found, replaces it with new_task.
            If old_task is not found, a ValueError is thrown.
        """
        phase_idx = self.get_phase_index(phase)
        
        self.phases[phase_idx].edit_task(old_task, new_task)
        

    def add_phase(self, phase: Phase):
        if not phase.preceding_phase:
            self.phases.append(phase) # add to end
            return
        print(f"TYPE OF PHASE: {type(phase)}")
        
        print(f"ADDING PHASE {phase} after {phase.preceding_phase}")
        print(f"Current phases: {[p.name for p in self.phases]}")
        # check for duplicate phase name
        for existing_phase in self.phases:
            if existing_phase.name == phase:
                raise ValueError(f"Provided phase name {phase.name} already exists in the {self.name} project.")

        # add after preceding_task
        if not phase.preceding_phase in self.phases:
            raise RuntimeError(f"Preceding phase {phase.preceding_phase} not found.")
        
        idx = self.phases.index(phase.preceding_phase)
        self.phases.insert(idx + 1, phase)


    def get_phase_index(self, phase: Phase) -> int:
        '''
            Gets the zero index of a provided phase within a project.

            Raises a RuntimeError if the project doesn't contain any phases

            Raises a ValueError if the provided phase does not exist within the project's phases
        '''
        if not self.phases:
            raise RuntimeError(f"Project {self.name} does not contain any phases")
        
        if not phase in self.phases:
            raise ValueError(f"Provided phase {phase.name} does not exist in phase list.")
        
        return self.phases.index(phase)

    def add_task_to_phase(self, phase: Phase, task: Task):           
        self.phases[self.get_phase_index(phase)].add_task(task)

    def delete_phase(self, phase: Phase):
        if not phase in self.phases:
            raise RuntimeError(f"Provided phase {phase} not found.")
        
        self.phases.delete(phase)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "phases": [p.to_dict() for p in self.phases],
            "settings": self.settings.to_dict()
        }