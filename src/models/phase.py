from __future__ import annotations
from dataclasses import dataclass, field
from models.task import Task
from typing import Optional
from datetime import datetime
from logic.generate_id import new_id
from logic.utils import _none_min
from models.sort_mode import SortMode



@dataclass
class Phase:
    name: str
    uuid: str = field(default_factory=new_id)
    task_order: list[str] = field(default_factory=list) # list of task uuids in order
    tasks: dict[str, Task] = field(default_factory=dict) # map of task uuid to task
    preceding_phase: Optional[Phase] = None
    predecessor_ids: list[str] = field(default_factory=list)
    _sort_mode: SortMode = SortMode.manual

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
        if predesessor in self.predecessor_ids:
            return
        self.predecessor_ids.append(predesessor)

    def edit_task(self, old_task: Task, new_task: Task):
        if not old_task.uuid in self.tasks.keys():
            raise RuntimeError(f"Provided task {old_task} not found.")
        
        new_task.uuid = old_task.uuid # preserve uuid
        order = self.task_order.index(old_task.uuid) # preserve order
        del self.tasks[old_task.uuid]
        self.tasks[new_task.uuid] = new_task
        self.task_order[order] = new_task.uuid
        

    def delete_task(self, task: Task) -> int:
        """
            Deletes the provided task from the phase.
            Returns the number of tasks that had this task as a predecessor.

            If the task is not found, a RuntimeError is raised.
        """
        if not task.uuid in self.tasks.keys():
            raise RuntimeError(f"Provided task {task} not found.")
        
        # check for tasks using this as predecessor
        predecessor_count = 0
        for t in self.tasks.values():
            if task.uuid in t.predecessor_ids:
                t.predecessor_ids.remove(task.uuid)
                predecessor_count += 1

        del self.tasks[task.uuid]
        self.task_order.remove(task.uuid)

        return predecessor_count


    def __str__(self):
        return f"Project Phase '{self.name}'. Start date: {self.start_date if self.tasks else None}. End date: {self.end_date if self.tasks else None}"
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "tasks": [t.to_dict() for t in self.tasks],
            "preceding_phase": self.preceding_phase.name if self.preceding_phase else None,
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
        phase.tasks = [Task.from_dict(t) for t in data["tasks"]]
        phase.preceding_phase = data.get("preceding_phase", None)
        phase.predecessor_ids = data.get("predecessor_ids", [])
        phase.uuid = data.get("uuid", new_id())
        return phase