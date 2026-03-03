import pandas as pd
import datetime as dt
import copy
import plotly.express as px
import streamlit as st
from plotly.colors import qualitative as q
import plotly.graph_objects as go

from ui.utils.phase_controls import prev_phase, next_phase
from ui.utils.project_info import render_project_info
from ui.utils.status_badges import STATUS_BADGES
from ui.gantt_state_options import render_gantt_options

from models.project import Project
from logic.gantt_builder import build_timeline, _normalize_delay_type, _prep_delay_windows
from logic.backend.delays import get_delays

from streamlit_plotly_events2 import plotly_events 
from zoneinfo import ZoneInfo

import streamlit as st

from models.delay import DelayEditorRow

def is_timezone_aware(dt):
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None

def delay_rows_tz(delay_rows: list[DelayEditorRow]) -> list[DelayEditorRow]:
    out = []
    for delay in delay_rows:
        new_delay = delay
        new_delay.start_dt = new_delay.start_dt.replace(tzinfo=ZoneInfo("America/Vancouver"))
        new_delay.end_dt = new_delay.end_dt.replace(tzinfo=ZoneInfo("America/Vancouver"))

        out.append(new_delay)
    return out

def _get_customdata_from_event(fig, pt: dict):
    """
    streamlit-plotly-events often returns only curveNumber/pointNumber.
    Recover the full customdata row from the figure itself.
    """
    curve = pt.get("curveNumber", None)
    idx = pt.get("pointNumber", pt.get("pointIndex", None))  # different keys appear depending on plotly
    if curve is None or idx is None:
        return None

    if curve < 0 or curve >= len(fig.data):
        return None

    tr = fig.data[curve]
    cd = getattr(tr, "customdata", None)
    if cd is None:
        return None

    try:
        return cd[idx]
    except Exception:
        return None


def render_gantt_with_click_selection(fig, project_id: str, key: str = "gantt"):
    """
    Uses streamlit-plotly-events2 (import name is still streamlit_plotly_events).
    Writes selection into st.session_state.
    """
    

    fig.update_layout(uirevision=f"gantt:{project_id}")

    events = plotly_events(
        fig,
        click_event=True,
        select_event=False,
        hover_event=False,
        key=key,
        override_width="100%",
        config={"displayModeBar": True, "responsive": True},
    )

    if not events:
        return

    pt = events[0]

    # Try direct first (sometimes present), otherwise recover from fig
    cd = pt.get("customdata", None)
    if cd is None:
        cd = _get_customdata_from_event(fig, pt)

    if cd is None:
        # If this happens, it usually means the clicked trace doesn't have customdata
        # (e.g., you clicked a trace you didn’t set it on).
        return

    # customdata schema (from your build_timeline custom_data list):
    # [Label, Start_str, Finish_str, Type, UUID, Level, PhaseID, Status, PlannedDur_str, ActualDur_str, IsMilestone]
    uuid = cd[4]
    level = cd[5]
    phase_id = cd[6]

    if uuid and level == "Task":
        st.session_state["gantt_selected_uuid"] = uuid
        st.session_state["gantt_selected_phase_id"] = phase_id
        st.session_state["gantt_selected_payload"] = {
            "uuid": uuid,
            "phase_id": phase_id,
            "name": cd[0],
            "planned_start_str": cd[1],
            "planned_finish_str": cd[2],
            "type": cd[3],
            "status": cd[7],
            "planned_duration_str": cd[8],
            "actual_duration_str": cd[9],
            "is_milestone": bool(cd[10]),
        }
    else:
        st.session_state["gantt_selected_uuid"] = None
        st.session_state["gantt_selected_phase_id"] = phase_id
        st.session_state["gantt_selected_payload"] = None

    #st.rerun()
 

def render_gantt(session):
    phases = session.project.phases
    if not phases:
        st.info("Add a phase and some tasks to your project to view the visualizer.")
        return

    c1, _, c3 = st.columns([1,6,1])
    c1.subheader("Project Plan")
    view_phase_by_phase = c3.toggle("View phase by phase schedule", value=True)
    
    st.divider()
    phase_view = None
    if view_phase_by_phase:
        phase_idx = st.session_state.gantt_state.phase_idx
        pid = session.project.phase_order[phase_idx]
        phase = session.project.phases[pid]
        with st.container(horizontal=True, horizontal_alignment='center'):
            if st.button("←", type="secondary", on_click=prev_phase, disabled=(phase_idx == 0)):
                # reduce phase index by one
                st.session_state.gantt_state.phase_idx = max(0, st.session_state.gantt_state.phase_idx - 1)
                st.rerun()

            st.space(size="stretch")
            
            st.subheader(f"**Phase {phase_idx+1}. {phase.name}**")

            if st.button("→", type="secondary", on_click=next_phase, disabled=(phase_idx == len(session.project.phase_order) - 1)):
                st.session_state.gantt_state.phase_idx = min(len(session.project.phase_order) - 1, st.session_state.gantt_state.phase_idx + 1)
                st.rerun()

        phase_idx = st.session_state.gantt_state.phase_idx
        pid = session.project.phase_order[phase_idx]
        phase = session.project.phases[pid]

        phase_view = Project(
            name=session.project.name
        )

        phase_view.add_phase(phase)

    # Try to source delay rows
    delay_rows_naive = st.session_state.get("delays_rows_last_saved", [])

    # if not in session state, fetch
    if not delay_rows_naive:
        headers = st.session_state.get("auth_headers", {})
        delays = get_delays(
            headers=headers,
            project_id=session.project.uuid
        )

        delay_rows_naive = DelayEditorRow.from_delay(delays)

    delay_rows = delay_rows_tz(delay_rows_naive)

    with st.popover(label="Gantt Chart Options"):
        render_gantt_options(st.session_state.gantt_state, delay_rows=delay_rows)

    delay_windows = None
    if delay_rows and st.session_state.gantt_state.show_delay_windows:
        allowed = set(st.session_state.gantt_state.selected_delay_types) if st.session_state.gantt_state.selected_delay_types else None
        delay_windows = _prep_delay_windows(delay_rows, allowed_types=allowed)


    selected_proj = session.project if not phase_view else phase_view

    selected_uuid = st.session_state.get("gantt_selected_uuid", None)

    inputs_for_plot = copy.copy(st.session_state.gantt_state)

    if delay_windows:
        inputs_for_plot.show_planned=False
        inputs_for_plot.show_actual=True
    
    try:
        fig = build_timeline(
            project=selected_proj,
            inputs=inputs_for_plot,
            selected_uuid=selected_uuid, # phase or task uuid to highlight.
            delay_windows=delay_windows,
        )
    except ValueError as e:
        st.info(f"Add some tasks to your project to view the Gantt chart.")
        return

    st.plotly_chart(fig)

    st.divider()
    render_project_info(selected_proj)

    

def render_task_details(session):
    st.subheader("Task Details")
    c1, _, c3, c4 = st.columns([1,7,1,1])

    phase_to_use = c1.selectbox(
        label="Filter by Phase",
        options= ["All Phases"] + [pid for pid in session.project.phase_order],
        format_func=lambda pid: "All Phases" if pid == "All Phases" else session.project.phases[pid].name,
        help="Filter the task details table to show only tasks from a specific phase"
    )

    only_show_delayed = c3.toggle(
        label="Show only delayed tasks",
        value = True,
        key="show_delayed_tasks"
    )

    show_durations = c4.toggle(
        label="Show task durations",
        value=False,
        key="show_task_durations"
    )

    task_df = session.project.get_task_df()
    if phase_to_use != "All Phases":
        task_df = task_df[task_df["pid"] == phase_to_use]
        task_df.drop(columns=["pid"], axis=1, inplace=True)

    task_df = task_df[task_df["actual_duration"].notna()]
    task_df["delay"] = task_df["actual_duration"] - task_df["planned_duration"]

    if only_show_delayed:
        task_df = task_df[task_df["delay"] > 0]

    if not show_durations:
        task_df.drop(columns=["planned_start","planned_end","actual_start", "actual_end"], axis=1, inplace=True)
    
    st.dataframe(
        task_df,
        column_config={
            "task": st.column_config.TextColumn("Task Name"),
            "planned_start": st.column_config.DatetimeColumn("Planned Start"),
            "planned_end": st.column_config.DatetimeColumn("Planned End"),
            "actual_start": st.column_config.DatetimeColumn("Actual Start"),
            "actual_end": st.column_config.DatetimeColumn("Actual End"),
            "planned_duration": st.column_config.NumberColumn("Planned Duration (hrs)", format="%.2f"),
            "actual_duration": st.column_config.NumberColumn("Actual Duration (hrs)", format="%.2f"),
            "delay": st.column_config.NumberColumn("Delay (hrs)", format="%.2f", help="Positive values indicate the task finished later than planned; negative values indicate it finished earlier."),
            "notes": st.column_config.TextColumn("Notes")
        },
        width='stretch',
        hide_index=True
    )