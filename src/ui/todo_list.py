from __future__ import annotations

import json
import datetime as dt
from uuid import uuid4

import pandas as pd
import streamlit as st
from zoneinfo import ZoneInfo

from logic.backend.todo import get_todos, remove_todo, upsert_todos
from logic.backend.project_list import get_projects
from models.task import TaskStatus
from models.todo import TodoUpsertRow, todo_to_record
from ui.utils.page_header import render_page_stats_aside, render_registered_page_header


BASE_TODOS_KEY = "todos_rows_last_saved"
WORKING_TODOS_KEY = "todos_working_rows"
PENDING_TODOS_KEY = "todos_pending_save"
EDITING_TODO_KEY = "todos_editing_client_id"

STATUS_LABELS = {
    TaskStatus.NOT_STARTED: "Not Started",
    TaskStatus.IN_PROGRESS: "In Progress",
    TaskStatus.BLOCKED: "Blocked",
    TaskStatus.COMPLETE: "Complete",
}

STATUS_ICONS = {
    TaskStatus.NOT_STARTED: "○",
    TaskStatus.IN_PROGRESS: "◔",
    TaskStatus.BLOCKED: "⛔",
    TaskStatus.COMPLETE: "✓",
}

STATUS_ACCENTS = {
    TaskStatus.NOT_STARTED: "#64748b",
    TaskStatus.IN_PROGRESS: "#2563eb",
    TaskStatus.BLOCKED: "#dc2626",
    TaskStatus.COMPLETE: "#16a34a",
}

PRIORITY_STYLES = {
    0: ("Critical", "#dc2626"),
    1: ("High", "#ea580c"),
    2: ("Important", "#2563eb"),
    3: ("Normal", "#0f766e"),
    4: ("Low", "#64748b"),
    5: ("Backlog", "#94a3b8"),
}

PRIORITY_THRESHOLD_LABELS = {
    0: "Critical",
    1: "High",
    2: "Pressing",
    3: "Moderate",
    4: "Low",
    5: "All",
}

FILTER_CHIP_STYLES = {
    "status": {
        "accent": "#7c3aed",
        "surface": "rgba(237, 233, 254, 0.88)",
        "border": "rgba(139, 92, 246, 0.22)",
    },
    "priority": {
        "accent": "#b45309",
        "surface": "rgba(254, 243, 199, 0.88)",
        "border": "rgba(245, 158, 11, 0.24)",
    },
    "project": {
        "accent": "#1d4ed8",
        "surface": "rgba(219, 234, 254, 0.86)",
        "border": "rgba(59, 130, 246, 0.24)",
    },
    "linkage": {
        "accent": "#0f766e",
        "surface": "rgba(204, 251, 241, 0.9)",
        "border": "rgba(20, 184, 166, 0.22)",
    },
    "search": {
        "accent": "#be185d",
        "surface": "rgba(252, 231, 243, 0.9)",
        "border": "rgba(236, 72, 153, 0.22)",
    },
    "default": {
        "accent": "#475569",
        "surface": "rgba(248, 250, 252, 0.96)",
        "border": "rgba(15, 23, 42, 0.08)",
    },
}

PRIORITY_FILTER_CHIP_STYLES = {
    0: {
        "accent": "#b91c1c",
        "surface": "rgba(254, 226, 226, 0.9)",
        "border": "rgba(239, 68, 68, 0.24)",
    },
    1: {
        "accent": "#c2410c",
        "surface": "rgba(255, 237, 213, 0.92)",
        "border": "rgba(249, 115, 22, 0.24)",
    },
    2: {
        "accent": "#b45309",
        "surface": "rgba(254, 243, 199, 0.9)",
        "border": "rgba(245, 158, 11, 0.24)",
    },
    3: {
        "accent": "#1d4ed8",
        "surface": "rgba(219, 234, 254, 0.88)",
        "border": "rgba(59, 130, 246, 0.24)",
    },
    4: {
        "accent": "#0f766e",
        "surface": "rgba(204, 251, 241, 0.9)",
        "border": "rgba(20, 184, 166, 0.22)",
    },
    5: {
        "accent": "#475569",
        "surface": "rgba(248, 250, 252, 0.96)",
        "border": "rgba(15, 23, 42, 0.08)",
    },
}


def _default_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(st.context.timezone)
    except Exception:
        return ZoneInfo("America/Vancouver")


def _project_meta() -> dict[str, dict]:
    return get_projects(st.session_state.get("auth_headers", {}), include_closed=True)


def _blank_todo(project_id: str | None = None) -> dict:
    return {
        "_client_id": f"new-{uuid4()}",
        "id": None,
        "owner_id": None,
        "project_id": project_id,
        "task_id": None,
        "name": "",
        "description": "",
        "status": TaskStatus.NOT_STARTED.value,
        "priority": 2,
        "created_at": None,
        "updated_at": None,
        "start_date": None,
        "due_date": None,
        "completed_at": None,
    }


def _is_missing(value) -> bool:
    return value is None or pd.isna(value)


def _safe_date_value(value) -> dt.date | None:
    if _is_missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return None


def _status_text(value: str) -> str:
    status = TaskStatus(value)
    return f"{STATUS_ICONS[status]} {STATUS_LABELS[status]}"


def _status_chip(value: str) -> str:
    status = TaskStatus(value)
    tone = STATUS_ACCENTS[status]
    return (
        f"<span style=\"padding:0.22rem 0.62rem;border-radius:999px;background:{tone}15;"
        f"color:{tone};font-size:0.76rem;font-weight:700;\">"
        f"{STATUS_ICONS[status]} {STATUS_LABELS[status]}</span>"
    )


def _priority_chip(priority: int) -> str:
    label, tone = PRIORITY_STYLES[int(priority)]
    return (
        f"<span style=\"padding:0.22rem 0.62rem;border-radius:999px;background:{tone}15;"
        f"color:{tone};font-size:0.76rem;font-weight:700;\">"
        f"Priority {priority} | {label}</span>"
    )


def _normalize_for_compare(rows: list[dict]) -> str:
    comparable = []
    for row in rows:
        item = {k: v for k, v in row.items() if k != "_client_id"}
        normalized = {}
        for key, value in item.items():
            if isinstance(value, pd.Timestamp):
                value = value.to_pydatetime()
            if hasattr(value, "isoformat"):
                try:
                    value = value.isoformat()
                except TypeError:
                    pass
            normalized[key] = str(value) if key in {"id", "owner_id", "project_id", "task_id"} and value else value
        comparable.append(normalized)
    
    comparable.sort(key=lambda row: row.get("priority"), reverse=False)
    return json.dumps(comparable, sort_keys=True, default=str)


def _task_options(project) -> tuple[dict[str, str | None], dict[str | None, str]]:
    option_to_id: dict[str, str | None] = {"Unlinked": None}
    id_to_option: dict[str | None, str] = {None: "Unlinked"}
    label_counts: dict[str, int] = {}

    for task in project.get_task_list():
        phase = project.phases.get(task.phase_id)
        base_label = task.name if phase is None else f"{task.name} - {phase.name}"
        count = label_counts.get(base_label, 0) + 1
        label_counts[base_label] = count
        label = base_label if count == 1 else f"{base_label} ({count})"
        option_to_id[label] = task.uuid
        id_to_option[task.uuid] = label

    return option_to_id, id_to_option


def _priority_badge(priority: int) -> str:
    return PRIORITY_STYLES[int(priority)][0]


def _priority_threshold_text(value: int) -> str:
    return PRIORITY_THRESHOLD_LABELS.get(int(value), "All")


def _filter_chip_style(kind: str, *, priority_limit: int | None = None) -> dict[str, str]:
    if kind == "priority" and priority_limit is not None:
        return PRIORITY_FILTER_CHIP_STYLES.get(int(priority_limit), FILTER_CHIP_STYLES["priority"])
    return FILTER_CHIP_STYLES.get(kind, FILTER_CHIP_STYLES["default"])


def _status_metric_label(status: str) -> str:
    return STATUS_LABELS[TaskStatus(status)]


def _load_todos() -> None:
    project = st.session_state.session.project
    timezone = project.timezone if project is not None else _default_timezone()
    todos = get_todos(
        headers=st.session_state.get("auth_headers", {}),
        timezone=timezone,
    )
    saved_rows = []
    for todo in todos:
        row = todo_to_record(todo)
        row["_client_id"] = str(todo.id)
        saved_rows.append(row)

    st.session_state[BASE_TODOS_KEY] = saved_rows
    st.session_state[WORKING_TODOS_KEY] = [row.copy() for row in saved_rows]


def _current_rows() -> list[dict]:
    return st.session_state.setdefault(WORKING_TODOS_KEY, [])


def _set_rows(rows: list[dict]) -> None:
    st.session_state[WORKING_TODOS_KEY] = rows


def _collect_upsert_rows(rows: list[dict]) -> list[TodoUpsertRow]:
    payload = []
    for row in rows:
        payload.append(
            TodoUpsertRow.model_validate(
                {
                    "id": row.get("id"),
                    "name": (row.get("name") or "").strip(),
                    "description": row.get("description") or "",
                    "project_id": row.get("project_id"),
                    "task_id": row.get("task_id"),
                    "status": row.get("status") or TaskStatus.NOT_STARTED.value,
                    "priority": row.get("priority") if row.get("priority") is not None else 0,
                    "start_date": row.get("start_date"),
                    "due_date": row.get("due_date"),
                    "completed_at": row.get("completed_at"),
                }
            )
        )
    return payload


def _find_row(client_id: str) -> dict | None:
    for row in _current_rows():
        if row["_client_id"] == client_id:
            return row
    return None


def _upsert_local_row(updated_row: dict) -> None:
    rows = _current_rows()
    for index, row in enumerate(rows):
        if row["_client_id"] == updated_row["_client_id"]:
            rows[index] = updated_row
            _set_rows(rows)
            return


def _remove_local_row(client_id: str) -> None:
    _set_rows([row for row in _current_rows() if row["_client_id"] != client_id])


def _save_rows(rows: list[dict], *, replace: bool) -> None:
    timezone = _default_timezone()
    saved = upsert_todos(
        headers=st.session_state.get("auth_headers", {}),
        rows=_collect_upsert_rows(rows),
        timezone=timezone,
        project_id=None,
        replace=replace,
    )
    saved_rows = []
    for todo in saved:
        row = todo_to_record(todo)
        row["_client_id"] = str(todo.id)
        saved_rows.append(row)

    st.session_state[BASE_TODOS_KEY] = saved_rows
    st.session_state[WORKING_TODOS_KEY] = [row.copy() for row in saved_rows]


def _render_filters(
    rows: list[dict],
    task_name_map: dict[str | None, str],
    project_options: dict[str, str | None],
    project_name_map: dict[str | None, str],
) -> tuple[list[dict], list[str]]:
    status_options = [status.value for status in TaskStatus]
    status_filter = status_options
    priority_limit = 5
    project_filter = "All projects"
    search = ""
    linkage_filter = "All"

    with st.popover("Filters", icon=":material/tune:"):
        status_filter = st.pills(
            "Status",
            options=status_options,
            selection_mode="multi",
            default=status_options,
            format_func=_status_text,
        )
        priority_limit = st.slider(
            "Priority threshold",
            min_value=0,
            max_value=5,
            value=5,
            format="%d",
            help="Show todos with priority less than or equal to this value.",
        )
        st.caption(f"Showing priorities up to: {_priority_threshold_text(priority_limit)}")
        project_filter = st.selectbox(
            "Project",
            options=list(project_options.keys()),
            index=0,
        )
        linkage_filter = st.segmented_control(
            "Linked Task",
            options=["All", "Linked", "Unlinked"],
            default="All",
            selection_mode="single",
        )
        search = st.text_input("Search", placeholder="Name, description, project, or linked task")

    filtered = []
    needle = search.strip().lower()
    selected_project_id = project_options[project_filter]
    for row in rows:
        if row["status"] not in status_filter:
            continue
        if int(row["priority"]) > int(priority_limit):
            continue
        if selected_project_id is not None and row.get("project_id") != selected_project_id:
            continue
        is_linked = bool(row.get("task_id"))
        if linkage_filter == "Linked" and not is_linked:
            continue
        if linkage_filter == "Unlinked" and is_linked:
            continue

        haystack = " ".join(
            [
                row.get("name") or "",
                row.get("description") or "",
                project_name_map.get(row.get("project_id"), "") or "",
                task_name_map.get(row.get("task_id"), "") or "",
            ]
        ).lower()
        if needle and needle not in haystack:
            continue
        filtered.append(row)

    filter_summary: list[dict[str, str | int]] = []
    if len(status_filter) != len(status_options):
        filter_summary.append({"label": f"{len(status_filter)} status selected", "kind": "status"})
    filter_summary.append(
        {
            "label": f"Priority: {_priority_threshold_text(priority_limit)}",
            "kind": "priority",
            "priority_limit": int(priority_limit),
        }
    )
    if selected_project_id is not None:
        filter_summary.append({"label": project_filter, "kind": "project"})
    if linkage_filter != "All":
        filter_summary.append({"label": linkage_filter, "kind": "linkage"})
    if needle:
        filter_summary.append({"label": f"Search: {search.strip()}", "kind": "search"})

    return filtered, filter_summary


def _render_empty_state() -> None:
    st.markdown(
        """
        <div style="padding:1.4rem 1.2rem;border:1px dashed rgba(100,116,139,0.35);border-radius:20px;
                    background:linear-gradient(145deg, rgba(248,250,252,0.96), rgba(255,255,255,0.95));
                    text-align:center;">
            <div style="font-size:1rem;font-weight:700;color:#0f172a;">No todos match the current view</div>
            <div style="margin-top:0.35rem;font-size:0.9rem;color:#64748b;">
                Adjust the filters or add a new action item to get started.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def todos_completed_in_last_t(rows: list[dict], last_t: dt.timedelta = dt.timedelta(days=7)) -> list[dict]:
    todos_completed_in_last_t = []
    now = dt.datetime.now(dt.UTC)
    for row in rows:
        completed = row.get("completed_at", None)
        if completed is None:
            continue

        if completed + last_t > now:
            todos_completed_in_last_t.append(row)
    
    return todos_completed_in_last_t

def todos_created_in_last_t(rows: list[dict], last_t: dt.timedelta = dt.timedelta(days=7)) -> list[dict]:
    todos_created_in_last_t = []
    now = dt.datetime.now(dt.UTC)

    for row in rows:
        created = row.get("created_at", None)
        if created is None:
            continue

        if created + last_t > now:
            todos_created_in_last_t.append(row)
    return todos_created_in_last_t

def todo_summary(rows: list[dict]) -> dict[str, int]:
    created = todos_created_in_last_t(rows, last_t=dt.timedelta(days=7))
    num_created_last_week = len(created)
    total = len(rows)

    completed_last_week = todos_completed_in_last_t(rows, last_t=dt.timedelta(days=7))
    num_completed_last_week = len(completed_last_week)

    completed = sum(1 for row in rows if row["status"] == TaskStatus.COMPLETE.value)


    blocked = sum(1 for row in rows if row["status"] == TaskStatus.BLOCKED.value)
    high_priority = sum(1 for row in rows if int(row["priority"]) <= 1 and row["status"] != TaskStatus.COMPLETE.value)
    return {
        "open": total - completed,
        "completed": completed,
        "blocked": blocked,
        "high_priority": high_priority,
        "created_last_week": num_created_last_week,
        "completed_last_week": num_completed_last_week,
    }


def _render_card(
    index: int,
    row: dict,
    project_name_map: dict[str | None, str],
    task_name_map: dict[str | None, str],
) -> None:
    linked_task = task_name_map.get(row.get("task_id"), "Unlinked")
    selected_project_label = project_name_map.get(row.get("project_id"), "No project")
    stamp = row.get("updated_at") or row.get("created_at")
    stamp_text = stamp.strftime("%d %b %Y, %I:%M %p") if stamp else "Unsaved"
    due_value = _safe_date_value(row.get("due_date"))
    start_value = _safe_date_value(row.get("start_date"))
    desc = (row.get("description") or "").strip()
    desc = desc if desc else "No description yet."

    header, actions = st.columns([7.2, 1], vertical_alignment="top")
    with header:
        st.markdown(
            f"""
            <div style="padding:1rem 1.1rem;border:1px solid rgba(49,51,63,0.12);border-radius:20px;
                        background:linear-gradient(145deg, rgba(255,255,255,0.98), rgba(248,250,252,0.95));
                        box-shadow: 0 12px 30px rgba(15,23,42,0.06); margin-bottom:0.15rem;">
                <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;">
                    <div>
                        <div style="font-size:0.78rem;text-transform:uppercase;letter-spacing:0.08em;color:#64748b;">
                            Todo {index + 1}
                        </div>
                        <div style="font-size:1rem;font-weight:700;color:#0f172a;">{row['name'] or 'Untitled todo'}</div>
                        <div style="margin-top:0.4rem;display:flex;gap:0.4rem;flex-wrap:wrap;">
                            {_status_chip(row['status'])}
                            {_priority_chip(int(row['priority']))}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:0.78rem;color:#64748b;">{selected_project_label}</div>
                        <div style="font-size:0.78rem;color:#64748b;">{linked_task}</div>
                        <div style="font-size:0.74rem;color:#94a3b8;">Updated {stamp_text}</div>
                    </div>
                </div>
                <div style="margin-top:0.9rem;font-size:0.92rem;line-height:1.5;color:#334155;">{desc}</div>
                <div style="margin-top:0.9rem;display:flex;gap:1rem;flex-wrap:wrap;font-size:0.8rem;color:#64748b;">
                    <span>{"Start:" if start_value else ""} {start_value.strftime("%d %b %Y") if start_value else ""}</span>
                    <span>{"Due:" if due_value else ""}  {due_value.strftime("%d %b %Y") if due_value else ""}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with actions:
        st.write("")
        if st.button(":material/edit:", key=f"todo_edit_{row['_client_id']}", help="Edit todo", use_container_width=True):
            st.session_state[EDITING_TODO_KEY] = row["_client_id"]
            st.rerun()
        if st.button(":material/delete:", key=f"todo_remove_{row['_client_id']}", help="Remove todo", use_container_width=True):
            _remove_local_row(row["_client_id"])
            st.rerun()


@st.dialog("Edit Todo", width="large")
def _render_edit_dialog(
    client_id: str,
    project_options: dict[str, str | None],
    project_name_map: dict[str | None, str],
    task_options: dict[str, str | None],
    task_name_map: dict[str | None, str],
) -> None:
    row = _find_row(client_id)
    if row is None:
        st.warning("This todo is no longer available.")
        if st.button("Close", use_container_width=True):
            st.session_state.pop(EDITING_TODO_KEY, None)
            st.rerun()
        return

    edited = row.copy()
    active_project = st.session_state.session.project
    timezone = active_project.timezone if active_project is not None else _default_timezone()
    selected_project_label = project_name_map.get(edited.get("project_id"), "No project")
    if selected_project_label not in project_options:
        selected_project_label = "No project"
    selected_task_label = task_name_map.get(edited.get("task_id"), "Unlinked")
    if selected_task_label not in task_options:
        selected_task_label = "Unlinked"

    st.markdown(
        f"""
        <div style="padding:0.8rem 0.95rem;border:1px solid rgba(49,51,63,0.12);border-radius:18px;
                    background:linear-gradient(145deg, rgba(248,250,252,0.92), rgba(255,255,255,0.96));">
            <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
                {_status_chip(edited['status'])}
                {_priority_chip(int(edited['priority']))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    edited["name"] = st.text_input(
        "Name",
        value=edited["name"],
        key=f"todo_dialog_name_{client_id}",
        placeholder="What needs to happen?",
    )
    status_choice = st.pills(
        "Status",
        options=[status.value for status in TaskStatus],
        default=edited["status"],
        selection_mode="single",
        format_func=_status_text,
        key=f"todo_dialog_status_{client_id}",
    )
    if status_choice:
        edited["status"] = status_choice

    edited["description"] = st.text_area(
        "Description",
        value=edited["description"],
        key=f"todo_dialog_description_{client_id}",
        height=140,
        placeholder="Add context, ownership, blocker notes, or the next step.",
    )

    c1, c2 = st.columns(2)
    selected_priority = c1.segmented_control(
        "Priority",
        options=[0, 1, 2, 3, 4, 5],
        default=int(edited["priority"]),
        selection_mode="single",
        format_func=lambda value: str(value),
        key=f"todo_dialog_priority_{client_id}",
    )
    edited["priority"] = int(selected_priority if selected_priority is not None else edited["priority"])
    selected_project = c2.selectbox(
        "Project",
        options=list(project_options.keys()),
        index=list(project_options.keys()).index(selected_project_label),
        key=f"todo_dialog_project_{client_id}",
    )
    previous_project_id = edited.get("project_id")
    edited["project_id"] = project_options[selected_project]
    if edited.get("project_id") != previous_project_id:
        edited["task_id"] = None

    can_edit_task_link = active_project is not None and active_project.uuid == edited.get("project_id")
    if can_edit_task_link:
        selected_task_label = task_name_map.get(edited.get("task_id"), "Unlinked")
        if selected_task_label not in task_options:
            selected_task_label = "Unlinked"
        selected_task = st.selectbox(
            "Linked Project Task",
            options=list(task_options.keys()),
            index=list(task_options.keys()).index(selected_task_label),
            key=f"todo_dialog_task_{client_id}",
        )
        edited["task_id"] = task_options[selected_task]
    else:
        st.selectbox(
            "Linked Project Task",
            options=[task_name_map.get(edited.get("task_id"), "Unlinked")],
            index=0,
            disabled=True,
            help="Load the matching project in the workspace to edit task links for this todo.",
            key=f"todo_dialog_task_readonly_{client_id}",
        )

    start_value = _safe_date_value(edited.get("start_date"))
    due_value = _safe_date_value(edited.get("due_date"))
    d1, d2 = st.columns(2)
    start_enabled = d1.checkbox(
        "Start Date",
        value=start_value is not None,
        key=f"todo_dialog_has_start_{client_id}",
    )
    due_enabled = d2.checkbox(
        "Due Date",
        value=due_value is not None,
        key=f"todo_dialog_has_due_{client_id}",
    )
    if start_enabled:
        selected_start = d1.date_input(
            "Start Date Value",
            value=start_value or dt.date.today(),
            label_visibility="collapsed",
            key=f"todo_dialog_start_{client_id}",
        )
        edited["start_date"] = pd.Timestamp(selected_start).to_pydatetime().replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=timezone,
        )
    else:
        edited["start_date"] = None

    if due_enabled:
        selected_due = d2.date_input(
            "Due Date Value",
            value=due_value or dt.date.today(),
            label_visibility="collapsed",
            key=f"todo_dialog_due_{client_id}",
        )
        edited["due_date"] = pd.Timestamp(selected_due).to_pydatetime().replace(
            hour=17,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=timezone,
        )
    else:
        edited["due_date"] = None

    if edited["status"] == TaskStatus.COMPLETE.value and edited.get("completed_at") is None:
        edited["completed_at"] = edited.get("updated_at") or edited.get("created_at") or dt.datetime.now(timezone)
    if edited["status"] != TaskStatus.COMPLETE.value:
        edited["completed_at"] = None

    c3, c4 = st.columns(2)
    if c3.button("Save Changes", type="primary", use_container_width=True):
        _upsert_local_row(edited)
        st.session_state.pop(EDITING_TODO_KEY, None)
        st.rerun()
    if c4.button("Cancel", use_container_width=True):
        st.session_state.pop(EDITING_TODO_KEY, None)
        st.rerun()


def render_pending_confirmation() -> None:
    pending = st.session_state.get(PENDING_TODOS_KEY)
    if not pending:
        return

    st.warning(f"{len(pending['removed'])} todos will be removed. Proceed?")
    with st.popover("Show removed todos"):
        for index, row in enumerate(pending["removed"], start=1):
            st.write(f"**{index}.** {row['name'] or 'Untitled todo'}")

    c1, c2 = st.columns(2)
    if c1.button(":material/check: Confirm Save", type="primary", use_container_width=True):
        for row in pending["removed"]:
            if row.get("id"):
                remove_todo(headers=st.session_state.get("auth_headers", {}), todo_id=row["id"])
        _save_rows(pending["rows"], replace=False)
        del st.session_state[PENDING_TODOS_KEY]
        st.success("Todo list saved.")
        st.rerun()
    if c2.button(":material/close: Cancel", use_container_width=True):
        del st.session_state[PENDING_TODOS_KEY]
        st.session_state[WORKING_TODOS_KEY] = [row.copy() for row in st.session_state[BASE_TODOS_KEY]]
        st.info("Changes discarded.")
        st.rerun()


def render_todo_list() -> None:
    if BASE_TODOS_KEY not in st.session_state or WORKING_TODOS_KEY not in st.session_state:
        _load_todos()
        st.rerun()

    project = st.session_state.session.project
    project_meta = _project_meta()
    project_options: dict[str, str | None] = {"All projects": None}
    project_name_map: dict[str | None, str] = {None: "No project"}
    edit_project_options: dict[str, str | None] = {"No project": None}
    for project_id, meta in project_meta.items():
        name = meta.get("name", str(project_id))
        project_options[name] = project_id
        edit_project_options[name] = project_id
        project_name_map[project_id] = name

    if project is not None:
        task_options, task_name_map = _task_options(project)
    else:
        task_options, task_name_map = ({"Unlinked": None}, {None: "Unlinked"})
    rows = _current_rows()
    editing_client_id = st.session_state.get(EDITING_TODO_KEY)
    summary = todo_summary(rows)

    st.markdown(
        """
        <style>
        div[data-testid="stPills"] button[aria-pressed="true"] {
            border-color: rgba(37, 99, 235, 0.38) !important;
            box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.15);
            background: linear-gradient(135deg, rgba(239,246,255,1), rgba(219,234,254,0.92)) !important;
            color: #1d4ed8 !important;
            font-weight: 700 !important;
        }
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
            background: linear-gradient(135deg, rgba(241,245,249,1), rgba(226,232,240,0.96)) !important;
            color: #0f172a !important;
            font-weight: 700 !important;
        }
        .todo-toolbar__meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            align-items: center;
        }
        .todo-toolbar__label {
            margin: 0 0 0.45rem;
            color: #64748b;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .todo-toolbar__chip {
            display: inline-flex;
            align-items: center;
            min-height: 32px;
            padding: 0.38rem 0.7rem;
            border-radius: 999px;
            border: 1px solid var(--todo-chip-border, rgba(15, 23, 42, 0.08));
            background: linear-gradient(145deg, var(--todo-chip-surface, rgba(255,255,255,0.96)), rgba(255,255,255,0.94));
            color: var(--todo-chip-accent, #475569);
            font-size: 0.82rem;
            font-weight: 700;
            line-height: 1;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.45);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    render_pending_confirmation()

    header_col, stats_col = st.columns([1.9, 1.1], gap="medium", vertical_alignment="top")
    with header_col:
        render_registered_page_header(
            "todos",
            chips=[
                f"{summary['open']} open",
                f"{summary['high_priority']} high priority",
                f"{summary['created_last_week']} created this week",
            ],
        )
    with stats_col:
        render_page_stats_aside(
            eyebrow="Snapshot",
            stats=[
                {
                    "label": "Open",
                    "value": str(summary["open"]),
                    "sub": f"This week",
                    "accent": "#1d4ed8",
                    "surface": "rgba(219, 234, 254, 0.72)",
                    "border": "rgba(59, 130, 246, 0.24)",
                    "value_color": "#1e3a8a",
                },
                {
                    "label": "Completed",
                    "value": str(summary["completed"]),
                    "sub": f"Finished this week",
                    "accent": "#15803d",
                    "surface": "rgba(220, 252, 231, 0.72)",
                    "border": "rgba(34, 197, 94, 0.24)",
                    "value_color": "#166534",
                },
                {
                    "label": "High Priority",
                    "value": str(summary["high_priority"]),
                    "sub": "Critical items still open",
                    "accent": "#b45309",
                    "surface": "rgba(254, 243, 199, 0.82)",
                    "border": "rgba(245, 158, 11, 0.26)",
                    "value_color": "#92400e",
                },
                {
                    "label": "Blocked",
                    "value": str(summary["blocked"]),
                    "sub": "Items on hold",
                    "accent": "#b91c1c",
                    "surface": "rgba(254, 226, 226, 0.78)",
                    "border": "rgba(239, 68, 68, 0.24)",
                    "value_color": "#991b1b",
                },
            ],
            accent="#0f766e",
            accent_soft="rgba(15, 118, 110, 0.12)",
        )

    toolbar_action, toolbar_filter, toolbar_meta = st.columns([1.1, 0.9, 3], vertical_alignment="center")
    with toolbar_action:
        add_todo = st.button(":material/add_task: Add Todo", type="primary", use_container_width=True)
    with toolbar_filter:
        filtered_rows, filter_summary = _render_filters(rows, task_name_map, project_options, project_name_map)
    with toolbar_meta:
        summary_markup = "".join(
            (
                lambda style, label: (
                    f'<span class="todo-toolbar__chip" '
                    f'style="--todo-chip-accent: {style["accent"]}; '
                    f'--todo-chip-surface: {style["surface"]}; '
                    f'--todo-chip-border: {style["border"]};">'
                    f"{label}</span>"
                )
            )(
                _filter_chip_style(
                    str(item.get("kind", "default")),
                    priority_limit=(
                        int(item["priority_limit"])
                        if item.get("priority_limit") is not None
                        else None
                    ),
                ),
                str(item.get("label", "")),
            )
            for item in (filter_summary or [{"label": "All todos", "kind": "default"}])
        )
        st.markdown(
            f"""
            <p class="todo-toolbar__label">Applied Filters</p>
            <div class="todo-toolbar__meta">{summary_markup}</div>
            """,
            unsafe_allow_html=True,
        )

    if add_todo:
        new_row = _blank_todo(project.uuid if project is not None else None)
        rows.append(new_row)
        _set_rows(rows)
        st.session_state[EDITING_TODO_KEY] = new_row["_client_id"]
        st.rerun()

    if not filtered_rows:
        _render_empty_state()
    else:
        for index, row in enumerate(filtered_rows):
            with st.container(border=True):
                _render_card(
                    index,
                    row,
                    project_name_map,
                    task_name_map,
                )

    if editing_client_id:
        _render_edit_dialog(
            editing_client_id,
            edit_project_options,
            project_name_map,
            task_options,
            task_name_map,
        )

    baseline = st.session_state[BASE_TODOS_KEY]
    current_signature = _normalize_for_compare(rows)
    baseline_signature = _normalize_for_compare(baseline)
    has_changes = current_signature != baseline_signature

    invalid_names = [row for row in rows if not (row.get("name") or "").strip()]
    removed_ids = {
        row["id"] for row in baseline if row.get("id")
    } - {
        row["id"] for row in rows if row.get("id")
    }
    removed_rows = [row for row in baseline if row.get("id") in removed_ids]

    c1, c2 = st.columns([1.2, 3])
    save_disabled = not has_changes or bool(invalid_names)
    if c1.button(":material/save: Save Todos", type="primary", disabled=save_disabled, use_container_width=True):
        if removed_rows:
            st.session_state[PENDING_TODOS_KEY] = {
                "rows": [row.copy() for row in rows],
                "removed": removed_rows,
            }
            st.rerun()
        _save_rows(rows, replace=False)
        st.success("Todo list saved.")
        st.rerun()

    if invalid_names:
        c2.warning("Every todo needs a name before it can be saved.")
    elif has_changes:
        c2.info("Unsaved changes ready to sync.")
    else:
        c2.success("Todo list is in sync.")
