from __future__ import annotations

import datetime as dt
from typing import Any
from uuid import UUID

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from models.task import TaskStatus


class TodoUpsertRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    name: str
    description: str = ""
    project_id: UUID | None = None
    task_id: UUID | None = None
    status: TaskStatus = TaskStatus.NOT_STARTED
    priority: int = Field(default=0, ge=0, le=5)
    start_date: dt.datetime | None = None
    due_date: dt.datetime | None = None
    completed_at: dt.datetime | None = None

    @staticmethod
    def from_df(df: pd.DataFrame) -> list["TodoUpsertRow"]:
        records = df.to_dict(orient="records")
        normalized = [
            {k: (None if pd.isna(v) else v) for k, v in record.items()}
            for record in records
        ]
        return TypeAdapter(list[TodoUpsertRow]).validate_python(normalized)


class TodoIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    project_id: UUID | None = None
    task_id: UUID | None = None
    name: str
    description: str = ""
    status: TaskStatus
    priority: int = 0
    created_at: dt.datetime
    updated_at: dt.datetime
    start_date: dt.datetime | None = None
    due_date: dt.datetime | None = None
    completed_at: dt.datetime | None = None

    @staticmethod
    def to_df(todos: list["TodoIn"]) -> pd.DataFrame:
        return pd.DataFrame([todo.model_dump() for todo in todos])


def todo_to_record(todo: TodoIn) -> dict[str, Any]:
    record = todo.model_dump()
    record["id"] = str(todo.id)
    record["owner_id"] = str(todo.owner_id)
    record["project_id"] = str(todo.project_id) if todo.project_id else None
    record["task_id"] = str(todo.task_id) if todo.task_id else None
    record["status"] = todo.status.value if isinstance(todo.status, TaskStatus) else str(todo.status)
    return record

