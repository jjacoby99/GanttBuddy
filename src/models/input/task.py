from pydantic import BaseModel, AwareDatetime
from typing import Optional

from uuid import UUID

from models.task import TaskType

class TaskIn(BaseModel):
    id: UUID
    project_id: UUID
    project_name: Optional[str]
    phase_id: UUID
    name: str
    planned_start: AwareDatetime
    planned_end: AwareDatetime
    actual_start: Optional[AwareDatetime]
    actual_end: Optional[AwareDatetime]
    note: str
    status: str
    position: int
    planned: bool
    task_type: TaskType


class AttentionIn(BaseModel):
    late: list[TaskIn]
    upcoming: list[TaskIn]
    awaiting: list[TaskIn]