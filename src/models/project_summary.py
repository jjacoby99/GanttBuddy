from __future__ import annotations

import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProjectSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    organization_id: str | None = None
    name: str = "Untitled project"
    description: str | None = None
    sort_mode: str | None = None
    closed: bool = False
    created_by_user_id: str | None = None
    created: dt.datetime = Field(validation_alias="created_at")
    updated: dt.datetime = Field(validation_alias="updated_at")
    project_type: str | None = None
    planned_start: dt.datetime | None = None
    planned_finish: dt.datetime | None = None
    site_id: str | None = None
    timezone_name: str = "UTC"
    site_code: str | None = None
    can_view: bool | None = None
    can_edit: bool | None = None
    can_manage_members: bool | None = None
    can_delete: bool | None = None

    @model_validator(mode="after")
    def _localize_datetimes(self) -> "ProjectSummary":
        try:
            tz = ZoneInfo(self.timezone_name or "UTC")
        except Exception:
            tz = ZoneInfo("UTC")

        self.created = self.created.astimezone(tz)
        self.updated = self.updated.astimezone(tz)
        if self.planned_start is not None:
            self.planned_start = self.planned_start.astimezone(tz)
        if self.planned_finish is not None:
            self.planned_finish = self.planned_finish.astimezone(tz)
        return self

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __str__(self) -> str:
        return self.name

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    @property
    def description_text(self) -> str:
        return (self.description or "").strip()

    @property
    def name_line(self) -> str:
        return self.name.splitlines()[0].strip() or "Untitled project"

    @property
    def type_label(self) -> str:
        raw = (self.project_type or "GENERIC").strip()
        return " ".join(part.capitalize() for part in raw.split("_"))

    @property
    def status_label(self) -> str:
        return "Closed" if self.closed else "Active"

    @property
    def access_label(self) -> str:
        if self.can_edit is True:
            return "Editable"
        if self.can_view is True:
            return "Read only"
        return "Access unknown"

    @property
    def has_access_flags(self) -> bool:
        return any(
            value is not None
            for value in (self.can_view, self.can_edit, self.can_manage_members, self.can_delete)
        )

    @property
    def is_scheduled(self) -> bool:
        return self.planned_start is not None and self.planned_finish is not None

    def matches_query(self, query: str) -> bool:
        q = query.strip().lower()
        if not q:
            return True
        haystacks = [
            self.name,
            self.description or "",
            self.project_type or "",
            self.site_code or "",
            self.timezone_name or "",
        ]
        return any(q in value.lower() for value in haystacks if value)
