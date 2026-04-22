from __future__ import annotations

from html import escape

import streamlit as st


def project_role_label(role: str | None) -> str:
    normalized = str(role or "").upper()
    return {
        "VIEWER": "Viewer",
        "EDITOR": "Editor",
        "PROJECT_ADMIN": "Admin",
    }.get(normalized, normalized.replace("_", " ").title() or "Unknown")


def project_role_badge_html(role: str | None) -> str:
    normalized = str(role or "").upper()
    role_class = {
        "VIEWER": "role-viewer",
        "EDITOR": "role-editor",
        "PROJECT_ADMIN": "role-admin",
    }.get(normalized, "role-viewer")
    label = project_role_label(normalized)
    return f'<span class="admin-role-badge {role_class}">{escape(label)}</span>'


def render_project_status_card(state_label: str) -> None:
    state_class = "is-closed" if str(state_label).lower() == "closed" else "is-open"
    st.markdown(
        f"""
        <div class="admin-signal-card">
          <div class="admin-signal-label">Project state</div>
          <div class="admin-signal-badge {state_class}">
            <span>{escape(str(state_label))}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
