import streamlit as st

from logic.backend.api_client import get_current_user


def require_login():
    if not st.session_state.get("auth", {}).get("is_active", False):
        st.error("Please sign in.")
        st.stop()

def is_admin() -> bool:
    if not "auth" in st.session_state:
        try:
            roles = get_current_user(
                auth_headers=st.session_state.get("auth_headers", {})
            )
            st.session_state["auth"] = roles
        except Exception as e:
            return False
    else:
        roles = st.session_state.get("auth", {}).get("roles", [])

    for role in roles:
        id = role.get('id')
        name = role.get('name')
        if name in ("BTA_SUPERUSER", "ORG_ADMIN"):
            return True
    return False

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
