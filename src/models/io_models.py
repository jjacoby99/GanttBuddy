from typing import List
from pydantic import BaseModel, Field, field_validator
from uuid import uuid4
from models.task import Task
from typing import Optional
from models.phase import Phase

class PhaseDTO(BaseModel):
    name: str
    uuid: str
    task_order: list[str] # list of task uuids in order
    tasks: dict[str, Task] # map of task uuid to task
    preceding_phase: Optional[Phase]
    predecessor_ids: list[str]
    _sort_mode: str = "manual"


class SessionConfigDTO(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))

