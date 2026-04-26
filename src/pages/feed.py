from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st

from logic.backend.api_client import fetch_project_snapshot
from logic.backend.events import get_events
from logic.backend.guards import require_login
from logic.backend.import_project import snapshot_to_project
from logic.backend.project_list import get_projects
from logic.backend.project_permissions import resolve_project_access, store_project_access
from models.event import EventIn
from models.plan_state import PlanState
from models.project_type import ProjectType
from ui.activity_feed import inject_activity_feed_css, render_activity_collection
from ui.utils.page_header import render_registered_page_header


EVENT_TYPE_LABELS = {
    "PROJECT_CREATED": "Project created",
    "PROJECT_UPDATED": "Project updated",
    "PROJECT_SETTINGS_CREATED": "Settings created",
    "PROJECT_SETTINGS_UPDATED": "Settings updated",
    "PROJECT_METADATA_UPDATED": "Metadata updated",
    "PROJECT_SHIFT_DEFINITION_UPDATED": "Shift definition updated",
    "PROJECT_SHIFT_ASSIGNMENTS_UPDATED": "Shift assignments updated",
    "PHASE_CREATED": "Phase created",
    "PHASE_UPDATED": "Phase updated",
    "PHASE_UNDELETED": "Phase restored",
    "PHASE_DELETED": "Phase removed",
    "TASK_CREATED": "Task created",
    "TASK_UPDATED": "Task updated",
    "TASK_ACTUALS_UPDATED": "Actuals updated",
    "TASK_UNDELETED": "Task restored",
    "TASK_DELETED": "Task removed",
    "STARTED": "Task started",
    "FINISHED": "Task finished",
    "STATUS": "Status changed",
    "NOTE": "Note added",
    "EDITED_ACTUALS": "Actuals edited",
    "PROJECT_CLOSED": "Project closed",
}


def _fmt_dt(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M")


def _ensure_state() -> None:
    if "feed_read_event_ids" not in st.session_state:
        st.session_state.feed_read_event_ids = set()
    if "feed_saved_filters" not in st.session_state:
        st.session_state.feed_saved_filters = []
    if "selected_project_id" not in st.session_state:
        st.session_state.selected_project_id = None


def load_project_into_session(project_id: str) -> None:
    st.session_state["selected_project_id"] = project_id
    projects = get_projects(st.session_state.auth_headers, include_closed=True)
    proj_snapshot = fetch_project_snapshot(
        project_id=project_id,
        headers=st.session_state.auth_headers,
    )
    project, metadata = snapshot_to_project(proj_snapshot)
    st.session_state.session.project = project
    store_project_access(
        resolve_project_access(
            headers=st.session_state.auth_headers,
            project_id=project_id,
            timezone=ZoneInfo(st.context.timezone),
            project_record=projects.get(project_id),
        )
    )
    if project.project_type == ProjectType.MILL_RELINE and metadata is not None:
        st.session_state["reline_metadata"] = metadata
    st.session_state.plan_state = PlanState(project_id=project_id)
    st.switch_page("pages/plan.py")


def render_filters(projects: dict, events: list[EventIn]) -> dict[str, Any]:
    with st.container():
        cols = st.columns([2, 1, 1, 1])
        with cols[0]:
            q = st.text_input("Search", placeholder="Search project, task, actor, or summary")
        with cols[1]:
            st.space("small")
            unread_only = st.toggle("Unread only", value=False)
        with cols[2]:
            window = st.selectbox("Window", ["24h", "7d", "30d", "All"], index=1)
        with cols[3]:
            sort_dir = st.selectbox("Sort", ["Newest first", "Oldest first"], index=0)

        proj_options = [(pid, (p.get("name") or "Unnamed project").split("\n")[0]) for pid, p in projects.items()]
        proj_label_by_id = {pid: label for pid, label in proj_options}

        c2 = st.columns([2, 2, 1])
        with c2[0]:
            project_filter = st.multiselect(
                "Projects",
                options=[pid for pid, _ in proj_options],
                format_func=lambda pid: proj_label_by_id.get(pid, pid),
            )
        with c2[1]:
            all_types = sorted({e.event_type for e in events})
            type_filter = st.multiselect(
                "Event types",
                options=all_types,
                default=[],
                format_func=lambda event_type: EVENT_TYPE_LABELS.get(event_type, EventIn(event_type=event_type, id="", project_name="", ts=datetime.now(UTC), project_id="", phase_id=None, phase_name=None, task_id=None, task_name=None, user_id="", user_name="", payload=None).format_event_type()),
            )
        with c2[2]:
            st.space("small")
            if st.button("Mark all read", icon=":material/done_all:", width="stretch"):
                for event in events:
                    st.session_state.feed_read_event_ids.add(event.id)
                st.rerun()

    return {
        "q": q.strip(),
        "unread_only": unread_only,
        "window": window,
        "sort_dir": sort_dir,
        "project_filter": set(project_filter),
        "type_filter": set(type_filter),
    }


def apply_filters(events: list[EventIn], filters: dict[str, Any]) -> list[EventIn]:
    q = filters["q"].lower()
    unread_only = filters["unread_only"]
    window = filters["window"]
    sort_dir = filters["sort_dir"]
    project_filter = filters["project_filter"]
    type_filter = filters["type_filter"]

    now = datetime.now(UTC)
    min_dt: datetime | None
    if window == "24h":
        min_dt = now - timedelta(hours=24)
    elif window == "7d":
        min_dt = now - timedelta(days=7)
    elif window == "30d":
        min_dt = now - timedelta(days=30)
    else:
        min_dt = None

    if min_dt is not None:
        min_dt = min_dt.astimezone(ZoneInfo(st.context.timezone))

    out: list[EventIn] = []
    for event in events:
        if min_dt is not None and event.ts < min_dt:
            continue
        if project_filter and event.project_id not in project_filter:
            continue
        if type_filter and event.event_type not in type_filter:
            continue
        if unread_only and event.id in st.session_state.feed_read_event_ids:
            continue
        if q:
            haystack = " ".join(
                [
                    event.user_name,
                    event.message,
                    event.event_type,
                    event.project_name,
                    event.phase_name or "",
                    event.task_name or "",
                    json.dumps(event.payload, default=str),
                ]
            ).lower()
            if q not in haystack:
                continue
        out.append(event)

    out.sort(key=lambda item: item.ts, reverse=sort_dir == "Newest first")
    return out


def render_project_pulse(projects: dict, events: list[EventIn]) -> None:
    with st.container(border=True):
        st.markdown("### Project pulse")
        st.caption("The busiest projects in the current activity window.")

        now = datetime.now(UTC)
        scored: list[tuple[int, str, datetime]] = []
        for project_id, project in projects.items():
            updated = project.get("updated") or now - timedelta(days=9999)
            recent_events = [event for event in events if event.project_id == project_id]
            score = len(recent_events) * 10 + max(0, int((now - updated).total_seconds() * -1 / 3600))
            scored.append((score, project_id, updated))

        scored.sort(reverse=True, key=lambda row: row[0])
        for _, project_id, updated in scored[:7]:
            name = (projects.get(project_id, {}).get("name") or "Unnamed project").split("\n")[0]
            st.markdown(f"**{name}**")
            st.caption(f"Last updated: {_fmt_dt(updated)}")
            if st.button(
                "Open",
                icon=":material/open_in_browser:",
                width="stretch",
                key=f"pulse_open_{project_id}",
            ):
                try:
                    load_project_into_session(project_id)
                except Exception as ex:
                    st.error(f"Failed to load project. {ex}")
            st.divider()


def _render_feed_lane(events: list[EventIn], *, read_event_ids: set[str], key_prefix: str, title: str, subtitle: str) -> None:
    if not events:
        st.info("No events match this view.")
        return

    render_activity_collection(
        events,
        shell_variant="feed",
        eyebrow="Workspace feed",
        title=title,
        subtitle=subtitle,
        read_event_ids=read_event_ids,
        show_day_groups=True,
        card_key_prefix=key_prefix,
        on_open_project=load_project_into_session,
        allow_read_toggle=True,
        show_custom_header=False
    )


def render_feed() -> None:
    _ensure_state()
    inject_activity_feed_css()

    tz = ZoneInfo(st.context.timezone)
    headers = st.session_state.get("auth_headers", {})
    projects = get_projects(headers=headers)
    events = get_events(headers=headers, n_events=50, timezone=tz)

    render_registered_page_header(
        "feed",
        chips=[
            f"{len(projects)} project{'s' if len(projects) != 1 else ''}",
            f"{len(events)} recent event{'s' if len(events) != 1 else ''}",
            "Project-local timestamps",
        ],
    )

    with st.popover("Filters"):
        filters = render_filters(projects, events)
    filtered = apply_filters(events, filters)
    unread = [event for event in filtered if event.id not in st.session_state.feed_read_event_ids]

    left, right = st.columns([3, 1])

    with left:
        activity_tab, unread_tab = st.tabs(["Activity", "Unread"])

        with activity_tab:
            _render_feed_lane(
                filtered,
                read_event_ids=st.session_state.feed_read_event_ids,
                key_prefix="feed_activity",
                title="Everything happening across your workspace",
                subtitle="Each event explains who acted, what changed, and where it happened.",
            )

        with unread_tab:
            _render_feed_lane(
                unread,
                read_event_ids=st.session_state.feed_read_event_ids,
                key_prefix="feed_unread",
                title="Unread activity that still needs your eyes",
                subtitle="Use this lane as your triage queue until backend read state is persisted.",
            )

    with right:
        render_project_pulse(projects, filtered)

        with st.container(border=True):
            st.markdown("### Saved views")
            st.caption("These are UI-only for now; later you can persist per-user.")
            if not st.session_state.feed_saved_filters:
                st.caption("No saved views yet.")
            else:
                for index, view in enumerate(st.session_state.feed_saved_filters):
                    if st.button(view.get("name", f"View {index + 1}"), width="stretch", key=f"sv_{index}"):
                        st.toast("Wire this to restore filters later.")

            if st.button("Save current view", icon=":material/bookmark_add:", width="stretch"):
                st.session_state.feed_saved_filters.append(
                    {"name": f"View {len(st.session_state.feed_saved_filters) + 1}"}
                )
                st.toast("Saved (UI-only).")


if __name__ == "__main__":
    require_login()
    render_feed()
