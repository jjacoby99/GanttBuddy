import pandas as pd
import plotly.express as px
import streamlit as st
from typing import Optional
from plotly.colors import qualitative as q
import plotly.graph_objects as go
import numpy as np
import re
from colorsys import rgb_to_hls, hls_to_rgb

from logic.post_mortem import PostMortemAnalyzer

from models.gantt_models import GanttInputs
from logic.gantt_builder import build_timeline

def render_gantt(session):
    phases = session.project.phases
    if not phases:
        st.info("Add a phase and some tasks to your project to view the visualizer.")
        return

    st.subheader("Project Plan")

    expander = st.expander("Gantt Chart")
    # Controls
    col_left, _ = expander.columns([1, 3])
    with col_left:
        with st.container(border=True):
            show_actual = st.toggle(
                "Show actual durations",
                value=False,
                disabled=not getattr(session.project, "has_actuals", False),
                key="gantt_show_actual",
            )
            use_bta_colors = st.toggle(  # label text can be changed later if you want
                "Use BTA color scheme",
                value=True,
                key="gantt_use_bta_colors",
            )
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

    try:
        fig = build_timeline(
            project=session.project,
            inputs=inputs
        )
    except ValueError as e:
        st.info(f"Add some tasks to your project to view the Gantt chart.")
        return

    expander.plotly_chart(fig)


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