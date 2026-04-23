# pages/home.py
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo
from dataclasses import dataclass
from html import escape
from textwrap import dedent
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
from ui.utils.page_header import render_page_aside, render_registered_page_header
from ui.utils.status_badges import STATUS_BADGES

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
from ui.load_project import render_load_project
from ui.load_from_excel import go_to_excel_import

import datetime as dt
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


def _relative_activity_time(value: dt.datetime, now: dt.datetime) -> str:
    delta = now - value
    if delta < dt.timedelta(minutes=1):
        return "Just now"
    if delta < dt.timedelta(hours=1):
        minutes = max(int(delta.total_seconds() // 60), 1)
        return f"{minutes}m ago"
    if delta < dt.timedelta(days=1):
        hours = max(int(delta.total_seconds() // 3600), 1)
        return f"{hours}h ago"
    if delta < dt.timedelta(days=7):
        return f"{delta.days}d ago"
    return value.strftime("%b %d")


def _event_visuals(event_type: str) -> dict[str, str]:
    event_map = {
        "PROJECT_CREATED": {
            "icon": "&#10024;",
            "label": "Project created",
            "accent": "#2563eb",
            "soft": "rgba(37, 99, 235, 0.14)",
        },
        "PROJECT_UPDATED": {
            "icon": "&#128736;",
            "label": "Project update",
            "accent": "#0f766e",
            "soft": "rgba(15, 118, 110, 0.14)",
        },
        "PROJECT_SETTINGS_UPDATED": {
            "icon": "&#9881;",
            "label": "Settings changed",
            "accent": "#7c3aed",
            "soft": "rgba(124, 58, 237, 0.14)",
        },
        "TASK_CREATED": {
            "icon": "&#10133;",
            "label": "Task created",
            "accent": "#0891b2",
            "soft": "rgba(8, 145, 178, 0.14)",
        },
        "TASK_UPDATED": {
            "icon": "&#9200;",
            "label": "Task updated",
            "accent": "#d97706",
            "soft": "rgba(217, 119, 6, 0.14)",
        },
        "PHASE_CREATED": {
            "icon": "&#129517;",
            "label": "Phase added",
            "accent": "#9333ea",
            "soft": "rgba(147, 51, 234, 0.14)",
        },
        "PROJECT_CLOSED": {
            "icon": "&#10003;",
            "label": "Project closed",
            "accent": "#be123c",
            "soft": "rgba(190, 18, 60, 0.14)",
        },
    }
    return event_map.get(
        event_type,
        {
            "icon": "&#9679;",
            "label": "Activity",
            "accent": "#334155",
            "soft": "rgba(51, 65, 85, 0.14)",
        },
    )


def _activity_actor_initials(user_name: str) -> str:
    parts = [part for part in user_name.split() if part]
    if not parts:
        return "GB"
    return "".join(part[0] for part in parts[:2]).upper()


def _status_chip_theme(status: str | None) -> dict[str, str] | None:
    if not status:
        return None

    label, _icon, tone_name = STATUS_BADGES.get(status, ("Unknown", "", "gray"))
    tone_map = {
        "gray": ("#475569", "rgba(71, 85, 105, 0.12)"),
        "blue": ("#2563eb", "rgba(37, 99, 235, 0.12)"),
        "green": ("#15803d", "rgba(21, 128, 61, 0.12)"),
        "red": ("#b91c1c", "rgba(185, 28, 28, 0.12)"),
    }
    accent, soft = tone_map.get(tone_name, ("#475569", "rgba(71, 85, 105, 0.12)"))
    return {"label": label, "accent": accent, "soft": soft}


def _activity_summary(item: Any) -> str:
    payload = item.payload if isinstance(item.payload, dict) else {}

    if item.event_type == "PROJECT_UPDATED":
        field_changes = payload.get("field_changes", [])
        count = len(field_changes) if isinstance(field_changes, list) else 0
        return f"{count} project field{'s' if count != 1 else ''} changed"
    if item.event_type == "PROJECT_SETTINGS_UPDATED":
        return "Project settings adjusted"
    if item.event_type == "PROJECT_CREATED":
        return "Workspace created"
    if item.event_type == "PHASE_CREATED":
        position = payload.get("position")
        name = str(payload.get("name") or "New phase")
        if isinstance(position, int):
            return f"Phase {position + 1}: {name}"
        return name
    if item.event_type == "TASK_CREATED":
        return str(payload.get("name") or "New task")
    if item.event_type == "TASK_UPDATED":
        return str(payload.get("name") or "Task updated")
    if item.event_type == "PROJECT_CLOSED":
        return "Project closeout completed"

    fallback = item.message.replace(":material/person:", "").replace("**", "").strip()
    return " ".join(fallback.split())


def _inject_recent_activity_css() -> None:
    st.markdown(
        """
        <style>
        .gb-activity-feed {
            position: relative;
            overflow: hidden;
            padding: 1.15rem;
            border-radius: 26px;
            border: 1px solid rgba(15, 23, 42, 0.08);
            background:
                radial-gradient(circle at top right, rgba(14, 165, 233, 0.14), transparent 28%),
                radial-gradient(circle at left center, rgba(15, 118, 110, 0.10), transparent 22%),
                linear-gradient(180deg, #fbfdff 0%, #f3f7fb 100%);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
        }

        .gb-activity-feed__header {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 0.85rem;
            margin-bottom: 0.95rem;
        }

        .gb-activity-feed__title {
            margin: 0;
            font-size: 1.05rem;
            font-weight: 700;
            color: #0f172a;
        }

        .gb-activity-feed__eyebrow {
            margin: 0 0 0.2rem;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #0369a1;
        }

        .gb-activity-feed__subtitle {
            margin: 0;
            font-size: 0.9rem;
            color: #475569;
        }

        .gb-activity-feed__stats {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            justify-content: flex-start;
        }

        .gb-activity-stat {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.42rem 0.72rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.78);
            border: 1px solid rgba(148, 163, 184, 0.24);
            color: #0f172a;
            font-size: 0.76rem;
            font-weight: 700;
        }

        .gb-activity-stat strong {
            font-size: 0.9rem;
        }

        .gb-activity-list {
            display: grid;
            gap: 0.78rem;
            margin-top: 0.9rem;
        }

        .gb-activity-item {
            display: grid;
            grid-template-columns: auto 1fr auto;
            gap: 0.8rem;
            align-items: start;
            padding: 0.88rem 0.92rem;
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(148, 163, 184, 0.18);
            box-shadow: 0 10px 26px rgba(148, 163, 184, 0.08);
            transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
        }

        .gb-activity-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 18px 34px rgba(148, 163, 184, 0.14);
            border-color: rgba(51, 65, 85, 0.18);
        }

        .gb-activity-icon {
            display: grid;
            place-items: center;
            width: 2.6rem;
            height: 2.6rem;
            border-radius: 18px;
            background: var(--activity-soft);
            color: var(--activity-accent);
            font-size: 1.1rem;
            box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.65);
        }

        .gb-activity-main {
            min-width: 0;
            display: grid;
            gap: 0.22rem;
        }

        .gb-activity-meta {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.45rem;
            margin-bottom: 0.35rem;
        }

        .gb-activity-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.32rem;
            padding: 0.28rem 0.62rem;
            border-radius: 999px;
            background: var(--activity-soft);
            color: var(--activity-accent);
            font-size: 0.72rem;
            font-weight: 700;
            line-height: 1;
        }

        .gb-activity-chip--project {
            background: rgba(15, 23, 42, 0.06);
            color: #0f172a;
        }

        .gb-activity-chip--status {
            background: var(--status-soft, rgba(71, 85, 105, 0.12));
            color: var(--status-accent, #475569);
        }

        .gb-activity-message {
            margin: 0;
            color: #0f172a;
            font-size: 0.93rem;
            line-height: 1.45;
            font-weight: 600;
        }

        .gb-activity-message strong {
            color: #020617;
        }

        .gb-activity-side {
            display: grid;
            justify-items: end;
            gap: 0.45rem;
            min-width: 4.5rem;
        }

        .gb-activity-avatar {
            display: grid;
            place-items: center;
            width: 2rem;
            height: 2rem;
            border-radius: 999px;
            background: linear-gradient(135deg, #0f172a 0%, #334155 100%);
            color: #f8fafc;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.04em;
        }

        .gb-activity-time {
            text-align: right;
            color: #475569;
            font-size: 0.72rem;
            line-height: 1.35;
        }

        @media (max-width: 900px) {
            .gb-activity-feed__header {
                align-items: flex-start;
            }

            .gb-activity-feed__stats {
                width: 100%;
            }

            .gb-activity-item {
                grid-template-columns: auto 1fr;
            }

            .gb-activity-side {
                grid-column: 2;
                justify-items: start;
                grid-auto-flow: column;
                align-items: center;
            }

            .gb-activity-time {
                text-align: left;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_recent_activity_feed(activity: list[Any]) -> None:
    now = dt.datetime.now(ZoneInfo(st.context.timezone))
    unique_projects = len({item.project_id for item in activity})
    active_people = len({item.user_id for item in activity})

    st.markdown(
        (
            f'<div class="gb-activity-feed">'
            f'<div class="gb-activity-feed__header">'
            f'<div>'
            f'<p class="gb-activity-feed__eyebrow">Recent Activity</p>'
            f'<h3 class="gb-activity-feed__title">Project pulse across the workspace</h3>'
            f'<p class="gb-activity-feed__subtitle">New tasks, edits, and closeout moves surfaced with more context.</p>'
            f'</div>'
            f'<div class="gb-activity-feed__stats">'
            f'<span class="gb-activity-stat"><strong>{len(activity)}</strong> events</span>'
            f'<span class="gb-activity-stat"><strong>{unique_projects}</strong> projects</span>'
            f'<span class="gb-activity-stat"><strong>{active_people}</strong> contributors</span>'
            f'</div>'
            f'</div>'
            f'<div class="gb-activity-list">'
        ),
        unsafe_allow_html=True,
    )

    for item in activity:
        visuals = _event_visuals(item.event_type)
        relative_time = _relative_activity_time(item.ts, now)
        absolute_time = item.ts.strftime("%b %d, %I:%M %p")
        message = escape(_activity_summary(item))
        payload = item.payload if isinstance(item.payload, dict) else {}
        status_theme = _status_chip_theme(payload.get("status"))
        status_chip = ""
        if status_theme and item.event_type in {"TASK_CREATED", "TASK_UPDATED"}:
            status_chip = (
                f"<span class=\"gb-activity-chip gb-activity-chip--status\" "
                f"style=\"--status-accent:{status_theme['accent']}; --status-soft:{status_theme['soft']};\">"
                f"{escape(status_theme['label'])}</span>"
            )

        st.markdown(
            (
                f'<div class="gb-activity-item" style="--activity-accent:{visuals["accent"]}; --activity-soft:{visuals["soft"]};">'
                f'<div class="gb-activity-icon">{visuals["icon"]}</div>'
                f'<div class="gb-activity-main">'
                f'<div class="gb-activity-meta">'
                f'<span class="gb-activity-chip">{escape(visuals["label"])}</span>'
                f'{status_chip}'
                f'<span class="gb-activity-chip gb-activity-chip--project">{escape(item.project_name)}</span>'
                f'</div>'
                f'<p class="gb-activity-message">{message}</p>'
                f'</div>'
                f'<div class="gb-activity-side">'
                f'<div class="gb-activity-avatar">{escape(_activity_actor_initials(item.user_name))}</div>'
                f'<div class="gb-activity-time">{escape(relative_time)}<br>{escape(absolute_time)}</div>'
                f'</div>'
                f'</div>'
            ),
            unsafe_allow_html=True,
        )

    st.markdown("</div></div>", unsafe_allow_html=True)


def main() -> None:
    user_tz = ZoneInfo(st.context.timezone)

    st.set_page_config(page_title="GanttBuddy • Home", layout="wide")
    inject_todo_panel_css()
    _inject_recent_activity_css()

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
                render_load_project()

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
                _render_recent_activity_feed(activity)


if __name__ == "__main__":
    main()
 
