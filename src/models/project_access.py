from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProjectAccess:
    project_id: str | None = None
    can_view: bool = True
    can_edit: bool = True
    can_manage_members: bool = False
    source: str | None = None

    @property
    def is_read_only(self) -> bool:
        return self.can_view and not self.can_edit
