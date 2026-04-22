from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st

from logic.backend.api_client import fetch_project_members
from logic.backend.users import get_user
from models.project_access import ProjectAccess


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


def _extract_member_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "members", "project_members"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _access_from_project_record(project_id: str, project_record: dict[str, Any] | None) -> ProjectAccess | None:
    if not project_record:
        return None

    has_any_flag = any(flag in project_record for flag in ("can_view", "can_edit", "can_manage_members"))
    if not has_any_flag:
        return None

    return ProjectAccess(
        project_id=project_id,
        can_view=_coerce_bool(project_record.get("can_view"), True),
        can_edit=_coerce_bool(project_record.get("can_edit"), False),
        can_manage_members=_coerce_bool(project_record.get("can_manage_members"), False),
        source="project_list",
    )


def _access_from_members_payload(
    project_id: str,
    members_payload: Any,
    current_user_id: str,
) -> ProjectAccess | None:
    for member in _extract_member_items(members_payload):
        user_id = member.get("user_id") or member.get("id")
        if str(user_id) != str(current_user_id):
            continue

        return ProjectAccess(
            project_id=project_id,
            can_view=_coerce_bool(member.get("can_view"), True),
            can_edit=_coerce_bool(member.get("can_edit"), False),
            can_manage_members=_coerce_bool(member.get("can_manage_members"), False),
            source="project_members",
        )

    return None


def resolve_project_access(
    *,
    headers: dict,
    project_id: str,
    timezone: ZoneInfo,
    project_record: dict[str, Any] | None = None,
) -> ProjectAccess:
    access = _access_from_project_record(project_id, project_record)

    try:
        current_user = get_user(auth_headers=headers, timezone=timezone)
        members_payload = fetch_project_members(headers=headers, project_id=project_id)
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


def read_only_project_message() -> str:
    return (
        "This project is open in read-only mode. You can review the schedule, but only the "
        "project owner or members with edit access can change it."
    )
