from __future__ import annotations

import pydantic

from logic.backend.api_client import fetch_project_delete_impact
from models.project_delete import ProjectDeleteImpact


def get_project_delete_impact(*, headers: dict, project_id: str) -> ProjectDeleteImpact:
    payload = fetch_project_delete_impact(headers=headers, project_id=project_id)

    try:
        return ProjectDeleteImpact.model_validate(payload)
    except pydantic.ValidationError as exc:
        raise ValueError("Backend project delete impact payload did not match the expected schema.") from exc
