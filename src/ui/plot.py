import pandas as pd
import datetime as dt
import plotly.express as px
import streamlit as st
from typing import Optional
from plotly.colors import qualitative as q
import plotly.graph_objects as go
import numpy as np
import re
from colorsys import rgb_to_hls, hls_to_rgb

from ui.utils.phase_controls import prev_phase, next_phase
from ui.utils.project_info import render_project_info
from logic.post_mortem import PostMortemAnalyzer

from models.gantt_models import GanttInputs
from models.project import Project
from models.session import SessionModel
from models.phase import Phase 
from logic.gantt_builder import build_timeline

def render_gantt(session):
    phases = session.project.phases
    if not phases:
        st.info("Add a phase and some tasks to your project to view the visualizer.")
        return

    st.subheader("Project Plan")
    phase_view = None
    if st.checkbox("View phase by phase schedules", value=True):
        phase_idx = st.session_state.ui.analysis_phase_index
        pid = session.project.phase_order[phase_idx]
        phase = session.project.phases[pid]
        with st.container(horizontal=True, horizontal_alignment='center'):
            if st.button("←", type="secondary", on_click=prev_phase, disabled=(phase_idx == 0)):
                # reduce phase index by one
                st.session_state.ui.analysis_phase_index = max(0, st.session_state.ui.analysis_phase_index - 1)
                st.rerun()

            st.space(size="stretch")
            
            st.write(f"**Phase {phase_idx+1}. {phase.name}**")

            if st.button("→", type="secondary", on_click=next_phase, disabled=(phase_idx == len(session.project.phase_order) - 1)):
                st.session_state.ui.analysis_phase_index = min(len(session.project.phase_order) - 1, st.session_state.ui.analysis_phase_index + 1)
                st.rerun()

        phase_idx = st.session_state.ui.analysis_phase_index
        pid = session.project.phase_order[phase_idx]
        phase = session.project.phases[pid]

        phase_view = Project(
            name=session.project.name
        )

        phase_view.add_phase(phase)

    # Controls
    with st.container(horizontal=True):
        show_actual = st.toggle(
            "Show actual durations",
            value=False,
            disabled=not getattr(session.project, "has_actuals", False),
            key="gantt_show_actual",
        )
        st.space("stretch")
        use_bta_colors = st.toggle(  
            "Use BTA color scheme",
            value=True,
            key="gantt_use_bta_colors",
        )
        st.space("stretch")
        shade_non_working = st.toggle(
            "Shade non-working time",
            value=True,
            key="gantt_shade_non_working",
            help="Go to settings to edit working days/hours for the project"
        )

    inputs = GanttInputs(
        show_actuals=show_actual,
        use_bta_colors=use_bta_colors,
        shade_non_working=shade_non_working
    )

    selected_proj = session.project if not phase_view else phase_view
    try:
        fig = build_timeline(
            project=selected_proj,
            inputs=inputs
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