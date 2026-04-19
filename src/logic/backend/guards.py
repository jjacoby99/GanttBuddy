import streamlit as st
from zoneinfo import ZoneInfo

from logic.backend.api_client import get_current_user
from logic.backend.users import get_user


def require_login():
    if not st.session_state.get("auth", {}).get("is_active", False):
        st.error("Please sign in.")
        st.stop()

def is_admin() -> bool:
    auth_headers = st.session_state.get("auth_headers", {})
    if not auth_headers:
        return False

    try:
        timezone = ZoneInfo(st.context.timezone)
        user = get_user(auth_headers=auth_headers, timezone=timezone)
        st.session_state["auth"] = get_current_user(auth_headers=auth_headers)
    except Exception:
        return False

    if any(role.get("name") == "BTA_SUPERUSER" for role in user.roles):
        return True

    return any(
        membership.is_active and membership.role in {"ORG_OWNER", "ORG_ADMIN"}
        for membership in user.organizations
    )

def require_admin():
    require_login()
    if not is_admin():
        st.error("You don't have access to this page.")
        st.stop()

def require_project_selected():
    require_login()
    if not st.session_state.get("selected_project_id"):
        st.info("Select a project first.")
        st.stop()
