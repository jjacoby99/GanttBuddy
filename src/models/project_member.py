from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ProjectMemberPermissions(BaseModel):
    organization_role: str | None = None
    project_role: str | None = None
    can_view: bool = True
    can_edit: bool = False
    can_manage_members: bool = False
    can_delete: bool = False


class ProjectMember(BaseModel):
    project_id: str | None = None
    user_id: str
    role: str | None = None
    created_at: dt.datetime | None = None
    name: str | None = None
    email: str | None = None
    organization_role: str | None = None
    permissions: ProjectMemberPermissions = Field(default_factory=ProjectMemberPermissions)

    @model_validator(mode="before")
    @classmethod
    def normalize_permissions(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        permissions = value.get("permissions")
        if not isinstance(permissions, dict):
            permissions = {}

        normalized = dict(value)
        normalized["permissions"] = {
            "organization_role": permissions.get("organization_role", value.get("organization_role")),
            "project_role": permissions.get("project_role", value.get("role")),
            "can_view": permissions.get("can_view", value.get("can_view", True)),
            "can_edit": permissions.get("can_edit", value.get("can_edit", False)),
            "can_manage_members": permissions.get("can_manage_members", value.get("can_manage_members", False)),
            "can_delete": permissions.get("can_delete", value.get("can_delete", False)),
        }
        return normalized


class ProjectMembersPayload(BaseModel):
    project_id: str | None = None
    organization_id: str | None = None
    items: list[ProjectMember] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_shape(cls, value: Any) -> Any:
        if isinstance(value, list):
            return {"items": value}

        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        items = normalized.get("items")
        if not isinstance(items, list):
            for key in ("members", "project_members"):
                candidate = normalized.get(key)
                if isinstance(candidate, list):
                    items = candidate
                    break

        normalized["items"] = items if isinstance(items, list) else []
        return normalized

    def member_for_user(self, user_id: str) -> ProjectMember | None:
        for item in self.items:
            if str(item.user_id) == str(user_id):
                return item
        return None
