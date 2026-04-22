from __future__ import annotations

import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

from logic.backend.utils.parse_datetime import parse_backend_utc
from models.task import TaskStatus

TODO_PRIORITY_STYLES = {
    0: ("Critical", "#dc2626"),
    1: ("High", "#ea580c"),
    2: ("Important", "#2563eb"),
    3: ("Normal", "#0f766e"),
    4: ("Low", "#64748b"),
    5: ("Backlog", "#94a3b8"),
}
TODO_STATUS_STYLES = {
    TaskStatus.NOT_STARTED.value: ("Not Started", "#64748b"),
    TaskStatus.IN_PROGRESS.value: ("In Progress", "#2563eb"),
    TaskStatus.BLOCKED.value: ("Blocked", "#dc2626"),
    TaskStatus.COMPLETE.value: ("Complete", "#16a34a"),
}


def todo_panel_css() -> str:
    return """
        .admin-role-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.38rem;
            padding: 0.26rem 0.56rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
        }
        .admin-role-badge.role-viewer {
            background: #eff6ff;
            color: #1d4ed8;
        }
        .admin-role-badge.role-editor {
            background: #ecfdf3;
            color: #047857;
        }
        .admin-role-badge.role-admin {
            background: #fff7ed;
            color: #c2410c;
        }
        .admin-todo-summary-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.75rem;
            margin-bottom: 1rem;
        }
        .admin-todo-kpi {
            border-radius: 16px;
            padding: 0.8rem 0.9rem;
            background: linear-gradient(180deg, rgba(239,246,255,0.95), rgba(248,250,252,0.92));
            border: 1px solid rgba(148, 163, 184, 0.18);
        }
        .admin-todo-kpi-label {
            font-size: 0.76rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #64748b;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }
        .admin-todo-kpi-value {
            font-size: 1.55rem;
            line-height: 1;
            color: #0f172a;
            font-weight: 800;
        }
        .admin-todo-kpi-sub {
            margin-top: 0.34rem;
            color: #475467;
            font-size: 0.86rem;
        }
        .admin-todo-row {
            padding: 0.72rem 0;
            border-top: 1px solid rgba(15, 23, 42, 0.08);
        }
        .admin-todo-row:first-child {
            border-top: none;
            padding-top: 0;
        }
        .admin-todo-name {
            font-size: 0.95rem;
            font-weight: 700;
            color: #101828;
            margin-bottom: 0.25rem;
        }
        .admin-todo-meta {
            font-size: 0.84rem;
            color: #667085;
        }
    """


def inject_todo_panel_css() -> None:
    st.markdown(f"<style>{todo_panel_css()}</style>", unsafe_allow_html=True)


def _parse_ts(value: str | None, timezone: ZoneInfo) -> dt.datetime | None:
    try:
        return parse_backend_utc(value, timezone) if value else None
    except Exception:
        return None


def _todo_priority_badge_html(priority: int) -> str:
    label, color = TODO_PRIORITY_STYLES.get(int(priority), ("Normal", "#64748b"))
    return (
        f'<span class="admin-role-badge" style="background:{color}15;color:{color};">'
        f"<span>•</span><span>{label}</span></span>"
    )


def _todo_status_badge_html(status: str) -> str:
    label, color = TODO_STATUS_STYLES.get(status, (status.replace("_", " ").title(), "#64748b"))
    return (
        f'<span class="admin-role-badge" style="background:{color}15;color:{color};">'
        f"<span>•</span><span>{label}</span></span>"
    )


def todo_dataframe(items: list[dict[str, Any]], timezone: ZoneInfo, valid_project_ids: set[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in items or []:
        project_id = str(item.get("project_id")) if item.get("project_id") else None
        if project_id is None or project_id not in valid_project_ids:
            continue
        priority = int(item.get("priority", 0) or 0)
        status = str(item.get("status") or TaskStatus.NOT_STARTED.value)
        due_dt = _parse_ts(item.get("due_date"), timezone)
        completed_dt = _parse_ts(item.get("completed_at"), timezone)
        created_dt = _parse_ts(item.get("created_at"), timezone)
        rows.append(
            {
                "name": item.get("name") or "Untitled todo",
                "project_id": project_id,
                "project_name": None,
                "status": status,
                "status_label": TODO_STATUS_STYLES.get(status, (status.replace("_", " ").title(), "#64748b"))[0],
                "status_color": TODO_STATUS_STYLES.get(status, ("Unknown", "#64748b"))[1],
                "priority": priority,
                "priority_label": TODO_PRIORITY_STYLES.get(priority, ("Normal", "#64748b"))[0],
                "priority_color": TODO_PRIORITY_STYLES.get(priority, ("Normal", "#64748b"))[1],
                "due_dt": due_dt,
                "completed_dt": completed_dt,
                "created_dt": created_dt,
            }
        )

    return pd.DataFrame(rows)

def _goto_todo_page() -> None:
    st.switch_page("pages/todo.py")

def render_todo_page_button() -> None:
    to_todo = st.button(f":material/assignment: My todos", type="secondary")
    if to_todo:
        _goto_todo_page()

def render_todo_overview_panel(todos_df: pd.DataFrame, project_name_by_id: dict[str, str]) -> None:
    if todos_df.empty:
        container = st.container(horizontal=True)
        container.info(":material/info: No project-linked todos are active for you yet.")
        container.space("stretch")
        with container:
            render_todo_page_button()
        return

    todos_df = todos_df.copy()
    todos_df["project_name"] = todos_df["project_id"].map(lambda value: project_name_by_id.get(str(value), "Project"))
    open_df = todos_df[todos_df["status"] != TaskStatus.COMPLETE.value].copy()
    completed_this_week = todos_df[
        todos_df["completed_dt"].notna()
        & ((pd.Timestamp.now(tz=dt.UTC) - pd.to_datetime(todos_df["completed_dt"], utc=True)) <= pd.Timedelta(days=7))
    ].copy()
    high_priority_df = open_df[open_df["priority"] <= 1].copy()
    status_chart_df = (
        open_df["status_label"].value_counts()
        .rename_axis("status")
        .reset_index(name="count")
    )
    status_chart_df["color"] = status_chart_df["status"].map(
        lambda label: next(
            (color for text, color in TODO_STATUS_STYLES.values() if text == label),
            "#64748b",
        )
    )

    st.caption("Your top action items for projects.")
    st.markdown(
        f"""
        <div class="admin-todo-summary-grid">
          <div class="admin-todo-kpi">
            <div class="admin-todo-kpi-label">Open todos</div>
            <div class="admin-todo-kpi-value">{len(open_df):,}</div>
            <div class="admin-todo-kpi-sub">Live actions still in motion</div>
          </div>
          <div class="admin-todo-kpi">
            <div class="admin-todo-kpi-label">Closed this week</div>
            <div class="admin-todo-kpi-value">{len(completed_this_week):,}</div>
            <div class="admin-todo-kpi-sub">Completed in the last 7 days</div>
          </div>
          <div class="admin-todo-kpi">
            <div class="admin-todo-kpi-label">High priority open</div>
            <div class="admin-todo-kpi-value">{len(high_priority_df):,}</div>
            <div class="admin-todo-kpi-sub">Critical and high-priority work</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    chart_col, queue_col = st.columns([1.12, 0.96])
    with chart_col:
        if status_chart_df.empty:
            st.info("No open todo status data to chart.")
        else:
            chart = (
                alt.Chart(status_chart_df)
                .mark_arc(innerRadius=58, outerRadius=96)
                .encode(
                    theta=alt.Theta("count:Q"),
                    color=alt.Color(
                        "status:N",
                        title=None,
                        scale=alt.Scale(
                            domain=status_chart_df["status"].tolist(),
                            range=status_chart_df["color"].tolist(),
                        ),
                    ),
                    tooltip=[alt.Tooltip("status:N", title="Status"), alt.Tooltip("count:Q", title="Count")],
                )
                .properties(height=260, title="Open todo mix")
            )
            st.altair_chart(chart, width="stretch")
    with queue_col:
        st.markdown("##### High-priority open todos")
        if high_priority_df.empty:
            st.success("No critical or high-priority todos are currently open.")
        else:
            queue = high_priority_df.sort_values(
                by=["priority", "due_dt", "created_dt"],
                ascending=[True, True, True],
                na_position="last",
            ).head(6)
            for _, row in queue.iterrows():
                due_label = row["due_dt"].strftime("%b %d") if row["due_dt"] is not None and not pd.isna(row["due_dt"]) else "No due date"
                st.markdown(
                    f"""
                    <div class="admin-todo-row">
                      <div class="admin-todo-name">{row['name']}</div>
                      <div style="display:flex;gap:0.4rem;flex-wrap:wrap;margin-bottom:0.3rem;">
                        {_todo_priority_badge_html(int(row['priority']))}
                        {_todo_status_badge_html(str(row['status']))}
                      </div>
                      <div class="admin-todo-meta">{row['project_name']} • Due {due_label}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
