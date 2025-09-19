from dataclasses import dataclass, field
from __future__ import annotations
from models.task import Task
from typing import Optional
from datetime import datetime

@dataclass
class Phase:
    id: str
    name: str
    tasks: list[Task] = field(default_factory=list) # sorted in project order

    @property
    def start_date(self) -> Optional[datetime]:
        if not self.tasks:
            return None
        
        return self.tasks[0]
    
    @property
    def end_date(self) -> Optional[datetime]:
        if not self.tasks:
            return None
        
        return self.tasks[-1]
    
    def add_task(self, task: Task, preceding_task: Task = None):
        if not preceding_task:
            self.tasks.append(task) # add to end
            return

        # add after preceding_task
        if not preceding_task in self.tasks:
            raise RuntimeError(f"Preceding task {preceding_task} not found.")
        
        idx = self.tasks.index(preceding_task)
        self.tasks.insert(idx + 1, task)

    def delete_task(self, task: Task):
        if not task in self.tasks:
            raise RuntimeError(f"Provided task {task} not found.")
        self.tasks.remove(task)
