import json
from dataclasses import dataclass
from datetime import datetime, timedelta, date, UTC
from typing import Any, Optional

from models.project_type import ProjectType
import streamlit as st

from logic.backend.guards import require_login
from logic.backend.api_client import fetch_project_snapshot
from logic.backend.import_project import snapshot_to_project
from logic.backend.project_list import get_projects


@dataclass(frozen=True)
class FeedEvent:
    id: str
    occurred_at: datetime
    event_type: str
    project_id: str
    task_id: Optional[str]
    actor_name: str
    summary: str
    details: dict[str, Any]


EVENT_TYPE_LABELS = {
    "task_created": "Task created",
    "task_updated": "Task updated",
    "task_status_changed": "Status changed",
    "task_actuals_changed": "Actuals changed",
    "task_note_changed": "Note changed",
    "phase_created": "Phase created",
    "phase_updated": "Phase updated",
    "project_updated": "Project updated",
}

EVENT_TYPE_ICONS = {
    "task_created": ":material/add_circle:",
    "task_updated": ":material/edit:",
    "task_status_changed": ":material/flag:",
    "task_actuals_changed": ":material/timer:",
    "task_note_changed": ":material/sticky_note_2:",
    "phase_created": ":material/view_agenda:",
    "phase_updated": ":material/view_agenda:",
    "project_updated": ":material/folder_open:",
}


def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


def _safe_dt(x: Any) -> datetime:
    if isinstance(x, datetime):
        return x
    if isinstance(x, str):
        try:
            return datetime.fromisoformat(x.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pass
    return datetime.now()


def _ensure_state():
    if "feed_read_event_ids" not in st.session_state:
        st.session_state.feed_read_event_ids = set()
    if "feed_saved_filters" not in st.session_state:
        st.session_state.feed_saved_filters = []
    if "selected_project_id" not in st.session_state:
        st.session_state.selected_project_id = None


def load_project_into_session(project_id: str):
    st.session_state["selected_project_id"] = project_id
    proj_snapshot = fetch_project_snapshot(
        project_id=project_id,
        headers=st.session_state.auth_headers,
    )
    project, metadata = snapshot_to_project(proj_snapshot)
    st.session_state.session.project = project
    if project.project_type == ProjectType.MILL_RELINE and metadata is not None:
        st.session_state["reline_metadata"] = metadata 
    st.switch_page("pages/plan.py")

from datetime import datetime, timezone, timedelta

def is_timezone_aware(dt_object):
    """Check if a datetime object is timezone-aware (aware) or naive."""
    return dt_object.tzinfo is not None and dt_object.tzinfo.utcoffset(dt_object) is not None

def get_feed_events_placeholder(projects: dict) -> list[FeedEvent]:
    """
    Placeholder generator that fakes events from project updated timestamps.
    Replace this later with an API call that returns task_events joined with user/project/task metadata.
    """
    now = datetime.now(UTC)

    items: list[FeedEvent] = []
    for i, (pid, p) in enumerate(projects.items()):
        updated = p.get("updated") or now - timedelta(hours=6 + i)
        updated = _safe_dt(updated)

        items.append(
            FeedEvent(
                id=f"mock-{pid}-projupd",
                occurred_at=updated,
                event_type="project_updated",
                project_id=pid,
                task_id=None,
                actor_name=p.get("updated_by", "System"),
                summary="Project updated",
                details={
                    "project_name": p.get("name", "Unnamed project"),
                    "raw": {k: str(v) for k, v in p.items()},
                },
            )
        )

    items.sort(key=lambda e: e.occurred_at, reverse=True)
    return items[:50]


def render_feed_header():
    st.markdown("## Feed")
    st.caption("Changes and activity across your projects.")


def render_filters(projects: dict, events: list[FeedEvent]) -> dict[str, Any]:
    with st.container(border=True):
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
                format_func=lambda t: EVENT_TYPE_LABELS.get(t, t),
            )
        with c2[2]:
            st.space("small")
            if st.button("Mark all read", icon=":material/done_all:", width="stretch"):
                for e in events:
                    st.session_state.feed_read_event_ids.add(e.id)
                st.rerun()

    return {
        "q": q.strip(),
        "unread_only": unread_only,
        "window": window,
        "sort_dir": sort_dir,
        "project_filter": set(project_filter),
        "type_filter": set(type_filter),
    }


def apply_filters(events: list[FeedEvent], filters: dict[str, Any]) -> list[FeedEvent]:
    q = filters["q"].lower()
    unread_only = filters["unread_only"]
    window = filters["window"]
    sort_dir = filters["sort_dir"]
    project_filter = filters["project_filter"]
    type_filter = filters["type_filter"]

    now = datetime.now(UTC)
    if window == "24h":
        min_dt = now - timedelta(hours=24)
    elif window == "7d":
        min_dt = now - timedelta(days=7)
    elif window == "30d":
        min_dt = now - timedelta(days=30)
    else:
        min_dt = datetime.min

    out: list[FeedEvent] = []
    for e in events:
        if e.occurred_at < min_dt:
            continue
        if project_filter and e.project_id not in project_filter:
            continue
        if type_filter and e.event_type not in type_filter:
            continue
        if unread_only and e.id in st.session_state.feed_read_event_ids:
            continue
        if q:
            hay = " ".join(
                [
                    e.actor_name,
                    e.summary,
                    e.event_type,
                    e.project_id,
                    e.task_id or "",
                    json.dumps(e.details, default=str),
                ]
            ).lower()
            if q not in hay:
                continue
        out.append(e)

    reverse = sort_dir == "Newest first"
    out.sort(key=lambda x: x.occurred_at, reverse=reverse)
    return out


def group_by_day(events: list[FeedEvent]) -> dict[date, list[FeedEvent]]:
    groups: dict[date, list[FeedEvent]] = {}
    for e in events:
        d = e.occurred_at.date()
        groups.setdefault(d, []).append(e)
    return dict(sorted(groups.items(), key=lambda kv: kv[0], reverse=True))


def render_event_card(e: FeedEvent, projects: dict, unread: bool = False):
    is_read = e.id in st.session_state.feed_read_event_ids
    label = EVENT_TYPE_LABELS.get(e.event_type, e.event_type)
    icon = EVENT_TYPE_ICONS.get(e.event_type, ":material/notifications:")
    project_name = (projects.get(e.project_id, {}).get("name") or "Unnamed project").split("\n")[0]

    with st.container(border=True):
        top = st.columns([3, 2, 1, 1])
        with top[0]:
            st.markdown(f"**{label}**")
            st.caption(e.summary)
        with top[1]:
            st.markdown(project_name)
            st.caption(f"{e.actor_name}  |  {_fmt_dt(e.occurred_at)}")
        with top[2]:
            if is_read:
                st.caption("Read")
            else:
                st.caption("Unread")
        with top[3]:
            if st.button(
                "Load",
                icon=":material/open_in_new:",
                type="primary",
                width="stretch",
                key=f"feed_load_{e.id}_{"unread" if unread else "read"}",
            ):
                try:
                    load_project_into_session(e.project_id)
                    st.session_state.feed_read_event_ids.add(e.id)
                    st.success("Project loaded into workspace session.")
                except Exception as ex:
                    st.error(f"Failed to load project. {ex}")

        exp = st.expander("Details", expanded=False)
        with exp:
            cols = st.columns([1, 1, 2])
            with cols[0]:
                if st.button(
                    "Mark read",
                    icon=":material/done:",
                    width="stretch",
                    key=f"feed_mark_read_{e.id}_{"unread" if unread else "read"}",
                    disabled=is_read,
                ):
                    st.session_state.feed_read_event_ids.add(e.id)
                    st.rerun()
            with cols[1]:
                if st.button(
                    "Copy JSON",
                    icon=":material/content_copy:",
                    width="stretch",
                    key=f"feed_copy_{e.id}_{"unread" if unread else "read"}",
                ):
                    st.session_state[f"feed_json_{e.id}"] = json.dumps(e.details, indent=2, default=str)
                    st.toast("Event JSON stored in session state.")
            with cols[2]:
                st.caption("Event payload (placeholder now; later this should reflect task_events.payload).")

            st.code(json.dumps(e.details, indent=2, default=str), language="json")


def render_activity_stream(projects: dict, events: list[FeedEvent], unread: bool = False):
    if not events:
        st.info("No activity yet.")
        return

    groups = group_by_day(events)
    for d, day_events in groups.items():
        st.markdown(f"### {d.isoformat()}")
        for e in day_events:
            render_event_card(e, projects, unread)
        st.divider()


def render_project_pulse(projects: dict, events: list[FeedEvent]):
    with st.container(border=True):
        st.markdown("### Project pulse")
        st.caption("What’s moving lately.")

        now = datetime.now(UTC)
        scored = []
        for pid, p in projects.items():
            updated = p.get("updated_at") or p.get("updated") or now - timedelta(days=9999)
            updated = _safe_dt(updated)

            recent_events = [e for e in events if e.project_id == pid]
            score = len(recent_events) * 10 + max(0, int((now - updated).total_seconds() * -1 / 3600))

            scored.append((score, pid, updated))

        scored.sort(reverse=True, key=lambda x: x[0])
        top = scored[:7]

        for _, pid, updated in top:
            name = (projects.get(pid, {}).get("name") or "Unnamed project").split("\n")[0]
            st.markdown(f"**{name}**")
            st.caption(f"Last updated: {_fmt_dt(updated)}")

            if st.button(
                "Open",
                icon=":material/open_in_browser:",
                width="stretch",
                key=f"pulse_open_{pid}",
            ):
                try:
                    load_project_into_session(pid)
                    st.success("Project loaded into workspace session.")
                except Exception as ex:
                    st.error(f"Failed to load project. {ex}")

            st.divider()


def render_feed():
    _ensure_state()

    projects = get_projects(st.session_state.get("auth_headers", {}))
    render_feed_header()

    st.markdown("---")

    events = get_feed_events_placeholder(projects)
    filters = render_filters(projects, events)
    filtered = apply_filters(events, filters)

    left, right = st.columns([3, 1])

    with left:
        tab = st.tabs(["Activity", "Unread", "Raw"])[0:3]

        with tab[0]:
            render_activity_stream(projects, filtered)

        with tab[1]:
            unread = [e for e in filtered if e.id not in st.session_state.feed_read_event_ids]
            render_activity_stream(projects, unread, unread=True)

        with tab[2]:
            st.caption("Raw event list (debug view)")
            st.dataframe(
                [
                    {
                        "id": e.id,
                        "occurred_at": _fmt_dt(e.occurred_at),
                        "event_type": e.event_type,
                        "project_id": e.project_id,
                        "task_id": e.task_id,
                        "actor": e.actor_name,
                        "summary": e.summary,
                    }
                    for e in filtered
                ],
                width="stretch",
                hide_index=True,
            )

    with right:
        render_project_pulse(projects, events)

        with st.container(border=True):
            st.markdown("### Saved views")
            st.caption("These are UI-only for now; later you can persist per-user.")
            if not st.session_state.feed_saved_filters:
                st.caption("No saved views yet.")
            else:
                for i, v in enumerate(st.session_state.feed_saved_filters):
                    if st.button(v.get("name", f"View {i+1}"), width="stretch", key=f"sv_{i}"):
                        st.toast("Wire this to restore filters later.")

            if st.button("Save current view", icon=":material/bookmark_add:", width="stretch"):
                st.session_state.feed_saved_filters.append({"name": f"View {len(st.session_state.feed_saved_filters)+1}"})
                st.toast("Saved (UI-only).")


if __name__ == "__main__":
    require_login()
    render_feed()
