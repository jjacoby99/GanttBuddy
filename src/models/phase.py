from __future__ import annotations
from dataclasses import dataclass, field
from models.task import Task
from typing import Optional
from datetime import datetime

@dataclass
class Phase:
    name: str
    tasks: list[Task] = field(default_factory=list) # sorted in project order
    preceding_phase: Optional[Phase] = None

    @property
    def start_date(self) -> Optional[datetime]:
        if not self.tasks:
            return None
        
        return self.tasks[0].start_date
    
    @property
    def end_date(self) -> Optional[datetime]:
        if not self.tasks:
            return None
        
        return self.tasks[-1].end_date
    
    def add_task(self, task: Task):
        if not task.preceding_task:
            self.tasks.append(task) # add to end
            return

        # add after preceding_task
        if not task.preceding_task in self.tasks:
            raise RuntimeError(f"Preceding task {task.preceding_task} not found.")
        
        idx = self.tasks.index(task.preceding_task)
        self.tasks.insert(idx + 1, task)


    def edit_task(self, old_task: Task, new_task: Task):
        if not old_task in self.tasks:
            raise RuntimeError(f"Provided task {old_task} not found.")
        
        idx = self.tasks.index(old_task)
        self.tasks[idx] = new_task
        
    def delete_task(self, task: Task):
        if not task in self.tasks:
            raise RuntimeError(f"Provided task {task} not found.")
        self.tasks.remove(task)

    def __str__(self):
        return f"Project Phase '{self.name}'. Start date: {self.start_date if self.tasks else None}. End date: {self.end_date if self.tasks else None}"
    