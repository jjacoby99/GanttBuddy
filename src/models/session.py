from typing import List
from models.task import Task
from models.project import Project

class SessionModel:
    def __init__(self):
        self.project: Project = None

    def set_project(self, project: Project):
        self.project = Project

