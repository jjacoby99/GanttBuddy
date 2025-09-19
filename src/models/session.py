from typing import List
from lib.task import Task
from lib.project import Project

class SessionModel:
    def __init__(self):
        self.project: Project = None

    def set_project(self, project: Project):
        self.project = Project

    def add_task(self, task: Task, preceding_task: Task = None):
        if not preceding_task:
            self.project.tasks.append(task) # add to end
            return

        # add after preceding_task
        if not preceding_task in self.project.tasks:
            raise RuntimeError(f"Preceding task {preceding_task} not found.")
        
        idx = self.project.tasks.index(preceding_task)
        self.project.tasks.insert(idx + 1, task)

    def get_tasks(self) -> list[Task]:
        return self.project.tasks
