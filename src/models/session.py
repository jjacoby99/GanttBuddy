from typing import List
from models.task import Task
from models.project import Project

class SessionModel:
    def __init__(self):
        self._project: Project | None = None

    @property
    def project(self) -> Project | None:
        return self._project

    @project.setter
    def project(self, value: Project):
        if not isinstance(value, Project):
            raise ValueError("Session project attribute must be an instance of Project")
        self._project = value

