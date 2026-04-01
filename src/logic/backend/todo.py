from __future__ import annotations

from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from logic.backend.api_client import delete_todo, fetch_todos, save_todos
from logic.backend.utils.parse_datetime import _from_utc_to_project_tz
from models.task import TaskStatus
from models.todo import TodoIn, TodoUpsertRow


def _localize_todo(todo: TodoIn, timezone: ZoneInfo) -> TodoIn:
    todo.created_at = _from_utc_to_project_tz(todo.created_at, timezone)
    todo.updated_at = _from_utc_to_project_tz(todo.updated_at, timezone)
    todo.start_date = _from_utc_to_project_tz(todo.start_date, timezone)
    todo.due_date = _from_utc_to_project_tz(todo.due_date, timezone)
    todo.completed_at = _from_utc_to_project_tz(todo.completed_at, timezone)
    return todo


def get_todos(
    *,
    headers: dict,
    timezone: ZoneInfo,
    project_id: Optional[str | UUID] = None,
    task_id: Optional[str | UUID] = None,
    status: Optional[str | TaskStatus] = None,
) -> list[TodoIn]:
    data = fetch_todos(
        headers=headers,
        project_id=project_id,
        task_id=task_id,
        status=status,
    )
    if not data:
        return []
    return [_localize_todo(TodoIn.model_validate(item), timezone) for item in data]


def upsert_todos(
    *,
    headers: dict,
    rows: list[TodoUpsertRow],
    timezone: ZoneInfo,
    project_id: Optional[str | UUID] = None,
    replace: bool = False,
) -> list[TodoIn]:
    saved = save_todos(
        headers=headers,
        rows=rows,
        project_id=project_id,
        replace=replace,
    )
    return [_localize_todo(todo, timezone) for todo in saved]


def remove_todo(
    *,
    headers: dict,
    todo_id: str | UUID,
) -> None:
    delete_todo(headers=headers, todo_id=todo_id)
