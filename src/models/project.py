from dataclasses import dataclass, field
from typing import Optional
from models.task import Task

@dataclass
class Project:
    name: str
    description: Optional[str] = None
    tasks: list[Task] = field(default_factory=list)