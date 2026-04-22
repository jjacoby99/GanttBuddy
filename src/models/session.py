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
        self._project = value

