from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st

from logic.backend.project_members import get_project_members
from logic.backend.users import get_user
from models.project_access import ProjectAccess
from models.project_member import ProjectMembersPayload
from models.user import User


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return bool(value)


def _project_record_value(project_record: Any, key: str) -> Any:
    if project_record is None:
        return None
    if isinstance(project_record, dict):
        return project_record.get(key)
    return getattr(project_record, key, None)


def _access_from_project_record(project_id: str, project_record: Any | None) -> ProjectAccess | None:
    if not project_record:
        return None

    has_any_flag = any(
        _project_record_value(project_record, flag) is not None
        for flag in ("can_view", "can_edit", "can_manage_members", "can_delete")
    )
    if not has_any_flag:
        return None

    return ProjectAccess(
        project_id=project_id,
        can_view=_coerce_bool(_project_record_value(project_record, "can_view"), True),
        can_edit=_coerce_bool(_project_record_value(project_record, "can_edit"), False),
        can_manage_members=_coerce_bool(_project_record_value(project_record, "can_manage_members"), False),
        can_delete=_coerce_bool(_project_record_value(project_record, "can_delete"), False),
        source="project_list",
    )


def _access_from_members_payload(
    project_id: str,
    members_payload: ProjectMembersPayload,
    current_user_id: str,
) -> ProjectAccess | None:
    member = members_payload.member_for_user(current_user_id)
    if member is None:
        return None

    return ProjectAccess(
        project_id=project_id,
        can_view=_coerce_bool(member.permissions.can_view, True),
        can_edit=_coerce_bool(member.permissions.can_edit, False),
        can_manage_members=_coerce_bool(member.permissions.can_manage_members, False),
        can_delete=_coerce_bool(member.permissions.can_delete, False),
        source="project_members",
    )


def _access_from_admin_user(project_id: str, user: User) -> ProjectAccess | None:
    roles = getattr(user, "roles", []) or []
    organizations = getattr(user, "organizations", []) or []

    if any(role.get("name") == "BTA_SUPERUSER" for role in roles):
        return ProjectAccess(
            project_id=project_id,
            can_view=True,
            can_edit=True,
            can_manage_members=True,
            can_delete=True,
            source="org_admin",
        )

    if any(
        membership.is_active and membership.role in {"ORG_OWNER", "ORG_ADMIN"}
        for membership in organizations
    ):
        return ProjectAccess(
            project_id=project_id,
            can_view=True,
            can_edit=True,
            can_manage_members=True,
            can_delete=True,
            source="org_admin",
        )

    return None


def resolve_project_access(
    *,
    headers: dict,
    project_id: str,
    timezone: ZoneInfo,
    project_record: Any | None = None,
) -> ProjectAccess:
    access = _access_from_project_record(project_id, project_record)

    try:
        current_user = get_user(auth_headers=headers, timezone=timezone)
        admin_access = _access_from_admin_user(project_id, current_user)
        if admin_access is not None:
            return admin_access
        members_payload = get_project_members(headers=headers, project_id=project_id)
        member_access = _access_from_members_payload(project_id, members_payload, current_user.id)
        if member_access is not None:
            return member_access
    except Exception:
        pass

    if access is not None:
        return access

    return ProjectAccess(
        project_id=project_id,
        can_view=True,
        can_edit=False,
        can_manage_members=False,
        can_delete=False,
        source="deny_default",
    )


def store_project_access(access: ProjectAccess | None) -> None:
    st.session_state["project_access"] = access or ProjectAccess()


def current_project_access() -> ProjectAccess:
    access = st.session_state.get("project_access")
    if isinstance(access, ProjectAccess):
        return access

    access = ProjectAccess()
    st.session_state["project_access"] = access
    return access


def project_is_read_only() -> bool:
    project_id = st.session_state.get("selected_project_id")
    return bool(project_id and current_project_access().is_read_only)


def project_can_delete() -> bool:
    project_id = st.session_state.get("selected_project_id")
    return bool(project_id and current_project_access().can_delete)


def read_only_project_message() -> str:
    return (
        "This project is open in read-only mode. You can review the schedule, but your current "
        "access does not allow edits."
    )
