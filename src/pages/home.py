# pages/home.py
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from models.project import ProjectType

import streamlit as st


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





@dataclass
class ActivityItem:
    ts: str
    project_name: str
    message: str


def _placeholder_activity() -> List[ActivityItem]:
    return [
        ActivityItem(ts="09:06", project_name="SWRP Cleanout - RevB", message="Task marked complete: Pad in access road"),
        ActivityItem(ts="08:49", project_name="B-Auto Mill Reline", message="Imported schedule from Excel (RevC)"),
        ActivityItem(ts="Yesterday", project_name="24-Mile Sump Pumps", message="Actual entered: Pump #1 install start"),
        ActivityItem(ts="Yesterday", project_name="Pump Pre-Feas (Electrical)", message="New phase added: Site walkdown"),
    ]


from logic.backend.api_client import fetch_project_snapshot
from logic.backend.import_project import snapshot_to_project

# -----------------------------
# Wiring stubs (replace later)
# -----------------------------
def open_project(project_id: str) -> None:

    st.session_state["selected_project_id"] = project_id
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
    if project.project_type == ProjectType.MILL_RELINE and metadata is not None:
        st.session_state["reline_metadata"] = metadata 
    
    st.cache_data.clear() # clear cache on new project load
    st.rerun()


def go_to_projects_feed() -> None:
    st.switch_page("pages/feed.py")

def go_to_projects_load() -> None:
    render_load_project()


def start_create_project() -> None:
    """
    Replace with your create flow (dialog/page).
    """
    st.toast("Create Project (wire me)", icon="✨")


def start_import_excel() -> None:
    """
    Replace with your import flow (dialog/page).
    """
    st.toast("Import from Excel (wire me)", icon="📄")


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

from logic.backend.login import get_current_user
from logic.backend.project_list import get_projects
from logic.backend.activity_items import get_attention_items, count_activities

from ui.create_project import create_project
from ui.load_project import render_load_project
from ui.load_from_excel import load_from_excel

import datetime as dt
# -----------------------------
# Page
# -----------------------------
def main() -> None:
    st.set_page_config(page_title="GanttBuddy • Home", layout="wide")

    # Placeholder data (replace with backend calls)
    headers = st.session_state.get("auth_headers", {})
    user = get_current_user(headers)
    last_proj = get_projects(headers, n_proj=1)
    pid = next(iter(last_proj))
    needs = get_attention_items(headers)
    activity = _placeholder_activity()
    kpis = count_activities(needs)

    # ---------- Header strip ----------
    header = st.container(border=True)
    with header:
        left, right = st.columns([7, 3], vertical_alignment="center")

        with left:
            st.markdown(
                f"## Welcome back, **{user.get('name', '')}**",
            )
            st.caption(f"{user.get('org', "BTA Consulting")}")
            st.caption(f"Last login: {user.get('last_login', dt.datetime.now().strftime("%d/%m/%Y, %H:%M"))}")
            role_row = st.container()
            with role_row:
                for r in user.get("roles", []):
                    _badge(r.get("name", ""))

        with right:
            st.markdown("#### Pick Up Where You Left Off")
            if last_proj:
                ps = last_proj[pid].get("planned_start", dt.datetime.today()).strftime("%d/%m/%Y, %H:%M")
                pe = last_proj[pid].get("planned_end", dt.datetime.today()).strftime("%d/%m/%Y, %H:%M")

                st.caption(f"**{last_proj[pid].get('name', '')}**")
                st.caption(f"**Duration**: {ps} -> {pe}")
                st.caption(f"**Last updated**: {last_proj[pid].get("updated").strftime("%d/%m/%Y, %H:%M")}")
                if st.button("Open last project", width="stretch", type="primary"):
                    open_project(pid)
            else:
                st.caption("No recent project found.")
                if st.button("Browse projects", width="stretch"):
                    go_to_projects_load()

    st.write("")

    # ---------- Quick actions ----------
    st.subheader("Quick actions")
    qa = st.container(border=True)
    with qa:
        c1, c2, c3 = st.columns(3, gap="large")
        with c1:
            st.markdown("### ✨ Create")
            st.caption("Start a new schedule from scratch.")
            if st.button("Create project", width="stretch"):
                create_project()
                if st.session_state.session.project is not None:
                    st.switch_page("pages/plan.py")
        with c2:
            st.markdown("### 📄 Import")
            st.caption("Bring in an Excel schedule and start working immediately.")
            if st.button("Import from Excel", width="stretch"):
                load_from_excel()

        with c3:
            st.markdown("### 📁 Browse")
            st.caption("Search, filter, and open projects you have access to.")
            if st.button("Browse projects", width="stretch"):
                render_load_project()
                if st.session_state.session.project is not None:
                    st.switch_page("pages/plan.py")

    st.write("")

    # ---------- Needs attention + Activity summary ----------
    left_col, right_col = st.columns([6, 4], gap="large")

    # Needs attention
    with left_col:
        st.subheader("Needs attention")
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
        st.subheader("Activity summary")

        # KPI row
        kpi_box = st.container(border=True)
        with kpi_box:
            m1, m2 = st.columns(2)
            with m1:
                st.metric("Late tasks", kpis.get("late_tasks", 0))
                st.metric("Awaiting actuals", kpis.get("awaiting_actuals", 0))
            with m2:
                st.metric("Due soon (48h)", kpis.get("due_soon_tasks", 0))
                st.metric("Updates today", kpis.get("updates_today", 0))

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
                for a in activity[:6]:
                    st.markdown(f"**{a.ts}** • {a.project_name}")
                    st.caption(a.message)
                    st.divider()


if __name__ == "__main__":
    main()
 