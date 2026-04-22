# pages/home.py
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from models.project import ProjectType

import streamlit as st

from models.plan_state import PlanState
from logic.backend.guards import require_login

# -----------------------------
# Placeholder models / data
# -----------------------------
@dataclass
class ProjectSummary:
    id: str
    name: str
    date_range: str
    last_opened_at: str
    role: str


from logic.backend.api_client import fetch_project_snapshot, fetch_todos
from logic.backend.import_project import snapshot_to_project
from logic.backend.project_permissions import resolve_project_access, store_project_access
from logic.backend.users import get_user
from ui.todo_overview import inject_todo_panel_css, render_todo_overview_panel, todo_dataframe

def open_project(project_id: str) -> None:
    st.session_state["selected_project_id"] = project_id
    projects = get_projects(st.session_state.get("auth_headers", {}), include_closed=True)
    try:
        snap = fetch_project_snapshot(
            project_id=st.session_state.get("selected_project_id"), 
            headers=st.session_state.get("auth_headers",{})
        )
    except Exception:
        st.error(f"Failed to load selected project.")
        st.stop()

    project, metadata = snapshot_to_project(snap)
    st.session_state.session.project = project
    store_project_access(
        resolve_project_access(
            headers=st.session_state.get("auth_headers", {}),
            project_id=project_id,
            timezone=ZoneInfo(st.context.timezone),
            project_record=projects.get(project_id),
        )
    )
    if project.project_type == ProjectType.MILL_RELINE and metadata is not None:
        st.session_state["reline_metadata"] = metadata 
    
    st.cache_data.clear() # clear cache on new project load
    st.session_state.plan_state = PlanState(project_id=project_id)
    st.switch_page("pages/plan.py")


def go_to_projects_feed() -> None:
    st.switch_page("pages/feed.py")



# -----------------------------
# Small UI helpers
# -----------------------------
def _badge(text: str) -> None:
    st.markdown(
        f"""
        <span style="
          display:inline-block;
          padding: 0.15rem 0.55rem;
          margin-right: 0.35rem;
          border: 1px solid rgba(49,51,63,0.2);
          border-radius: 999px;
          font-size: 0.85rem;
          background: rgba(49,51,63,0.04);
        ">{text}</span>
        """,
        unsafe_allow_html=True,
    )


def _severity_chip(sev: str) -> str:
    # Keep it simple and readable; you can theme later.
    return {
        "late": "Late",
        "due_soon": "Due soon",
        "awaiting_actuals": "Awaiting actuals",
        "info": "Info",
    }.get(sev, "Info")


def _severity_emoji(sev: str) -> str:
    return {
        "late": "⛔",
        "due_soon": "⏱️",
        "awaiting_actuals": "📝",
        "info": "ℹ️",
    }.get(sev, "ℹ️")

from logic.backend.project_list import get_projects
from logic.backend.activity_items import get_attention_items, count_activities
from logic.backend.events import get_events
from ui.create_project import create_project
from ui.load_project import render_load_project
from ui.load_from_excel import go_to_excel_import

import datetime as dt
# -----------------------------
# Page
# -----------------------------
def main() -> None:
    user_tz = ZoneInfo(st.context.timezone)

    st.set_page_config(page_title="GanttBuddy • Home", layout="wide")
    inject_todo_panel_css()

    require_login()

    # Placeholder data (replace with backend calls)
    headers = st.session_state.get("auth_headers", {})
    user = get_user(headers, timezone=user_tz)
    last_proj = get_projects(headers, n_proj=1,include_closed=True)
    all_projects = get_projects(headers, include_closed=True)

    pid = ""
    if last_proj:
        pid = next(iter(last_proj))

    needs = get_attention_items(headers, timezone=ZoneInfo(st.context.timezone))
    activity = get_events(headers, n_events=5)
    todos_payload = fetch_todos(headers=headers)
    kpis = count_activities(needs)

    # ---------- Header strip ----------
    header = st.container(border=True)
    with header:
        left, right = st.columns([7, 3], vertical_alignment="center")

        with left:
            last_login = user.last_login_at.strftime("%d/%m/%Y, %H:%M") if user.last_login_at else "N/A"
            primary_org = next(
                (
                    membership.organization.name
                    for membership in user.organizations
                    if membership.is_active and membership.organization is not None
                ),
                "BTA Consulting",
            )
            
            st.markdown(
                f"## Welcome back, **{user.name}**",
            )
            st.caption(primary_org)
            st.caption(f"Last login: {last_login}")
            role_row = st.container()
            with role_row:
                for r in user.roles:
                    _badge(r.get("name", ""))

        with right:
            st.markdown("#### Pick Up Where You Left Off")
            if last_proj:
                ps = last_proj[pid].get("planned_start", None)
                if ps is not None:
                    ps = ps.strftime("%d/%m/%Y, %H:%M")
                
                pe = last_proj[pid].get("planned_finish", None)
                if pe is not None:
                    pe = pe.strftime("%d/%m/%Y, %H:%M")

                st.caption(f"**{last_proj[pid].get('name', '')}**")
                st.caption(f"**Planned Duration**: {ps} -> {pe}")
                st.caption(f"**Last updated**: {last_proj[pid].get("updated").strftime("%d/%m/%Y, %H:%M")}")
                if st.button("Open last project", width="stretch", type="primary"):
                    open_project(pid)
            else:
                st.caption("No recent project found.")
                if st.button("Browse", width="stretch"):
                    render_load_project()

    st.write("")

    # ---------- Quick actions ----------
    st.subheader("Quick actions")
    qa = st.container(border=True)
    with qa:
        c1, c2, c3 = st.columns(3, gap="large")
        with c1:
            st.markdown("### ✨ Create")
            st.caption("Start a new schedule from scratch.")
            if st.button(":material/add_circle: Create project", width="stretch"):
                create_project()
                if st.session_state.session.project is not None:
                    st.switch_page("pages/plan.py")
        with c2:
            st.markdown("### 📄 Import")
            st.caption("Bring in an Excel schedule and start working immediately.")
            if st.button(":material/upload_file: Import from Excel", width="stretch"):
                go_to_excel_import()

        with c3:
            st.markdown("### 📁 Browse")
            st.caption("Search, filter, and open projects you have access to.")
            if st.button(":material/folder_open: Browse projects", width="stretch"):
                render_load_project()
                if st.session_state.session.project is not None:
                    st.switch_page("pages/plan.py")

    st.write("")

    # ---------- Needs attention + Activity summary ----------
    left_col, right_col = st.columns([5.6, 4.8], gap="medium")

    # Needs attention
    with left_col:
        with st.container(horizontal=True):
            st.subheader("Needs attention")
            
            st.space("stretch")

            
            with st.popover("KPIs"):
                m1, m2 = st.columns(2)
                with m1:
                    st.metric("Late tasks", kpis.get("late_tasks", 0))
                    st.metric("Awaiting actuals", kpis.get("awaiting_actuals", 0))
                with m2:
                    st.metric("Due soon (48h)", kpis.get("due_soon_tasks", 0))
                    st.metric("Updates today", kpis.get("updates_today", 0))
        
        na = st.container(border=True)
        with na:
            if not needs:
                st.info("Nothing needs attention right now.")
            else:
                
                for idx, item in enumerate(needs):
                    row = st.container(border=True)
                    with row:
                        a, b = st.columns([8, 2], vertical_alignment="center")
                        with a:
                            st.markdown(
                                f"**{_severity_emoji(item.severity)} {item.project_name}** • {_severity_chip(item.severity)}"
                            )
                            st.markdown(f"**{item.title}**")
                            st.caption(f"Due • {item.due_hint}")
                        with b:
                            if st.button("Open", key=f"na_open_{idx}", width="stretch"):
                                open_project(item.project_id)
                                
    # Activity summary
    with right_col:
        st.subheader("PM Tasks")

        project_ids = {str(project_id) for project_id in all_projects.keys()}
        project_name_by_id = {
            str(project_id): str(project_meta.get("name") or "Project")
            for project_id, project_meta in all_projects.items()
        }
        todos_df = todo_dataframe(todos_payload or [], user_tz, project_ids)
        with st.container(border=True):
            render_todo_overview_panel(todos_df, project_name_by_id)

        st.write("")        

        # Mini feed
        feed_box = st.container(border=True)
        with feed_box:
            top = st.columns([7, 3], vertical_alignment="center")
            with top[0]:
                st.markdown("#### Recent activity")
            with top[1]:
                if st.button("View full feed", width="stretch"):
                    go_to_projects_feed()

            if not activity:
                st.info("No recent activity yet.")
            else:
                for a in activity:
                    st.markdown(f"**{a.ts.strftime("%Y-%m-%d %H:%M")}** • {a.project_name}")
                    st.caption(a.message)
                    st.divider()


if __name__ == "__main__":
    main()
 
