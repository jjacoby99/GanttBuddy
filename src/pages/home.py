# pages/home.py
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from models.project import ProjectType

import streamlit as st

from models.plan_state import PlanState
from logic.backend.guards import require_login


from logic.backend.api_client import fetch_project_snapshot, fetch_todos
from logic.backend.import_project import snapshot_to_project
from logic.backend.project_permissions import resolve_project_access, store_project_access
from logic.backend.users import get_user
from ui.todo_overview import inject_todo_panel_css, render_todo_overview_panel, todo_dataframe
from ui.activity_feed import inject_activity_feed_css, render_recent_activity_preview
from ui.utils.page_header import render_page_aside, render_registered_page_header
from ui.load_project import go_to_load_project

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
from ui.load_from_excel import go_to_excel_import
# -----------------------------
# Page
# -----------------------------
def _fmt_home_dt(value: dt.datetime | None) -> str:
    if value is None:
        return "Not available"
    return value.strftime("%b %d, %Y at %I:%M %p")


def _fmt_home_window(start: dt.datetime | None, end: dt.datetime | None) -> str:
    if start is None or end is None:
        return "No planned duration available"
    return f"{start.strftime('%b %d, %I:%M %p')} to {end.strftime('%b %d, %I:%M %p')}"
    


def main() -> None:
    user_tz = ZoneInfo(st.context.timezone)

    st.set_page_config(page_title="GanttBuddy • Home", layout="wide")
    inject_todo_panel_css()
    inject_activity_feed_css()

    require_login()

    # Placeholder data (replace with backend calls)
    headers = st.session_state.get("auth_headers", {})
    user = get_user(headers, timezone=user_tz)
    last_proj = get_projects(headers, n_proj=1,include_closed=True)
    all_projects = get_projects(headers, include_closed=True)

    pid = ""
    if last_proj:
        pid = next(iter(last_proj))

    needs = get_attention_items(headers, timezone=user_tz)
    activity = get_events(headers, n_events=5, timezone=user_tz)
    todos_payload = fetch_todos(headers=headers)
    kpis = count_activities(needs)
    active_orgs = [membership for membership in user.organizations if membership.is_active]
    primary_org = next(
        (
            membership.organization.name
            for membership in active_orgs
            if membership.organization is not None
        ),
        "BTA Consulting",
    )
    role_labels = [r.get("name", "") for r in user.roles if r.get("name")]
    header_chips = [
        primary_org,
        f"Last login {_fmt_home_dt(user.last_login_at)}",
        f"{len(needs)} attention item{'s' if len(needs) != 1 else ''}",
        f"{len(todos_payload or [])} PM todo{'s' if len(todos_payload or []) != 1 else ''}",
    ] + role_labels[:3]

    hero_col, aside_col = st.columns([1.95, 1.05], gap="medium", vertical_alignment="top")
    with hero_col:
        render_registered_page_header(
            "home",
            title=f"Welcome back, {user.name}",
            description="Start from your current project signals, recent activity, and PM follow-ups.",
            chips=header_chips,
        )

    with aside_col:
        if last_proj:
            last_project = last_proj[pid]
            render_page_aside(
                eyebrow="Pick up where you left off",
                title=last_project.get("name", "Recent project"),
                body="Jump back into the most recently updated project in your workspace.",
                chips=[
                    _fmt_home_window(last_project.get("planned_start"), last_project.get("planned_finish")),
                    f"Last updated {_fmt_home_dt(last_project.get('updated'))}",
                ],
                accent="#0f766e",
                accent_soft="rgba(15, 118, 110, 0.12)",
            )
            if st.button("Open last project", width="stretch", type="primary"):
                open_project(pid)
        else:
            render_page_aside(
                eyebrow="Pick up where you left off",
                title="No recent project yet",
                body="Browse your projects or start a new one to make this shortcut useful.",
                chips=["Browse projects", "Create from scratch"],
                accent="#334155",
                accent_soft="rgba(51, 65, 85, 0.12)",
            )
            if st.button("Browse", width="stretch"):
                go_to_load_project()

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
            st.caption("Bring in a schedule from Excel.")
            if st.button(":material/upload_file: Import from Excel", width="stretch"):
                go_to_excel_import()

        with c3:
            st.markdown("### 📁 Browse")
            st.caption("Search, filter, and open projects you have access to.")
            if st.button(":material/folder_open: Browse projects", width="stretch"):
                go_to_load_project()
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
        feed_box = st.container()
        with feed_box:
            
            if not activity:
                st.info("No recent activity yet.")
            else:
                render_recent_activity_preview(activity)

            with st.container(horizontal=True):
                st.space("stretch")
                if st.button("View full feed", width="content", icon=":material/arrow_forward:"):
                        go_to_projects_feed()


if __name__ == "__main__":
    main()
 
