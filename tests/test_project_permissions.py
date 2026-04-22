from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from logic.backend import project_permissions
from models.project_member import ProjectMembersPayload


def _members_payload() -> dict:
    return {
        "project_id": "d9e16863-fbb9-4000-8d05-71a5d576f076",
        "organization_id": "366a81e4-0ff8-4cab-9b04-988b66a9b8db",
        "items": [
            {
                "project_id": "d9e16863-fbb9-4000-8d05-71a5d576f076",
                "user_id": "18436fc3-afce-43aa-af0a-4c157108a008",
                "role": "VIEWER",
                "created_at": "2026-03-18T15:46:02.175727Z",
                "name": "Josh",
                "email": "josh@btarcm.com",
                "organization_role": "ORG_ADMIN",
                "permissions": {
                    "organization_role": "ORG_ADMIN",
                    "project_role": "VIEWER",
                    "can_view": True,
                    "can_edit": True,
                    "can_manage_members": True,
                },
            },
            {
                "project_id": "d9e16863-fbb9-4000-8d05-71a5d576f076",
                "user_id": "e873a469-8cec-4f26-9751-33c08a9fefd6",
                "role": "PROJECT_ADMIN",
                "created_at": "2026-04-21T22:08:55.591947Z",
                "name": "Josh Jacoby",
                "email": "josh.jacoby@btaconsulting.ca",
                "organization_role": "ORG_OWNER",
                "permissions": {
                    "organization_role": "ORG_OWNER",
                    "project_role": "PROJECT_ADMIN",
                    "can_view": True,
                    "can_edit": True,
                    "can_manage_members": True,
                },
            },
        ],
    }


def test_project_members_payload_promotes_nested_permissions() -> None:
    payload = ProjectMembersPayload.model_validate(_members_payload())

    member = payload.member_for_user("e873a469-8cec-4f26-9751-33c08a9fefd6")

    assert member is not None
    assert member.permissions.project_role == "PROJECT_ADMIN"
    assert member.permissions.can_view is True
    assert member.permissions.can_edit is True
    assert member.permissions.can_manage_members is True


def test_resolve_project_access_uses_member_permissions_over_project_record(monkeypatch) -> None:
    monkeypatch.setattr(
        project_permissions,
        "get_user",
        lambda **_kwargs: SimpleNamespace(id="e873a469-8cec-4f26-9751-33c08a9fefd6"),
    )
    monkeypatch.setattr(
        project_permissions,
        "get_project_members",
        lambda **_kwargs: ProjectMembersPayload.model_validate(_members_payload()),
    )

    access = project_permissions.resolve_project_access(
        headers={"Authorization": "Bearer test"},
        project_id="d9e16863-fbb9-4000-8d05-71a5d576f076",
        timezone=ZoneInfo("America/Vancouver"),
        project_record={"can_view": True, "can_edit": False, "can_manage_members": False},
    )

    assert access.source == "project_members"
    assert access.can_view is True
    assert access.can_edit is True
    assert access.can_manage_members is True
    assert access.is_read_only is False
