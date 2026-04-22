from __future__ import annotations

import pydantic

from logic.backend.api_client import fetch_project_members
from models.project_member import ProjectMembersPayload


def get_project_members(*, headers: dict, project_id: str) -> ProjectMembersPayload:
    payload = fetch_project_members(headers=headers, project_id=project_id)

    try:
        return ProjectMembersPayload.model_validate(payload)
    except pydantic.ValidationError as exc:
        raise ValueError("Backend project members payload did not match the expected schema.") from exc
