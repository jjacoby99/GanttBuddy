import pandas as pd
import streamlit as st
from ui.edit_task import render_task_edit
from ui.add_task import render_task_add
from ui.edit_phase import render_phase_edit
from ui.add_phase import render_add_phase
from ui.utils.project_info import render_project_info
from ui.utils.status_badges import STATUS_BADGES

from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import datetime

class TaskColumns:
    name: int = 0
    planned_start: int = 1
    planned_finish: int = 2
    status: int = 3
    actual_start: int | None = None
    actual_finish: int | None = None
    edit: int = 4

    show_actuals: bool = False

    def __init__(self, show_actuals: bool=False):
        self.show_actuals = show_actuals

        self.name = 0
        self.planned_start = 1
        self.planned_finish = 2
        self.status = 3
        self.edit = 4
        if show_actuals:
            self.actual_start = 4
            self.actual_finish = 5
            self.edit = 6

    def get_col_widths(self) -> list[int]:
        if self.show_actuals:
            return [5, 2, 2, 2, 2, 2, 1]

        return [5,2,2,2,1]
    

def render_tasks_table(session):
    phases = session.project.phases

    if not phases:
        st.info(f"Add a phase to {session.project.name} to view project planner")
        return
    
    with st.popover("Project at a glance"):
        render_project_info(session.project)

    c1, _ = st.columns([1,2])
    c1.caption("Display Preferences")
    with st.container(horizontal=True, border=True, vertical_alignment="top", horizontal_alignment="center", width=500):
        
        show_actual = st.toggle(
            label="Show actual start / end",
            value=False
        )

        st.space("stretch")

        expand_all = st.toggle(
            label=f"Expand **{len(phases)}** Phases",
            value=False
        )

    st.subheader("Project Phases")
    
    columns = TaskColumns(show_actuals=show_actual)
    col_widths = columns.get_col_widths()

    phase_idx = 0
    for pid in session.project.phase_order:
        phase = session.project.phases[pid]

        phase_start = phase.start_date.strftime("%Y-%m-%d %H:%M") if phase.start_date else '-'
        phase_end = phase.end_date.strftime("%Y-%m-%d %H:%M") if phase.end_date else '-'
        with st.expander(f"**{phase.name}**\t ({len(phase.tasks)} tasks)\t - {phase_start} → {phase_end}",
                         expanded=expand_all):
            # Header row
            cols = st.columns(col_widths)
            cols[columns.name].markdown("**Task**")
            cols[columns.planned_start].markdown("**Start**")
            cols[columns.planned_finish].markdown("**Finish**")
            cols[columns.status].markdown("**Status**")

            if show_actual:
                cols[columns.actual_start].markdown("**Actual Start**")
                cols[columns.actual_finish].markdown("**Actual Finish**")

            cols[columns.edit].markdown("**Edit**")

            for i, tid in enumerate(phase.task_order):
                t = phase.tasks[tid]

                with st.container():
                    cols[columns.name].write(t.name)
                    cols[columns.planned_start].write(t.start_date.strftime("%Y-%m-%d %H:%M"))
                    cols[columns.planned_finish].write(t.end_date.strftime("%Y-%m-%d %H:%M"))

                    label, icon, color = STATUS_BADGES.get(
                        t.status.upper(),
                        (t.status, ":material/help:", "gray"),
                    )

                    cols[columns.status].badge(label, icon=icon, color=color)

                    if show_actual:
                        cols[columns.actual_start].write(t.actual_start.strftime("%Y-%m-%d %H:%M") if not pd.isna(t.actual_start) else "")
                        cols[columns.actual_finish].write(t.actual_end.strftime("%Y-%m-%d %H:%M") if not pd.isna(t.actual_end) else "")


                    if cols[columns.edit].button("✏️", key=f"edit_{phase.name}_{t.name}_{i}"):
                        render_task_edit(session, phase=phase, task=t)     

            st.divider()
            with st.container(horizontal=True):
                if st.button(":material/add_circle: Task", key=f"add_task_{phase.name}", type='secondary'):
                    render_task_add(session,phase=phase)
                    
                st.space("stretch")

                if st.button("✏️ Edit Phase", key=f"edit_{phase.name}", type="secondary"):
                    render_phase_edit(session,phase=phase)

        with st.container(horizontal=True):
            st.space("stretch")
            if st.button(":material/add_circle: Phase", key=f"add_phase_{phase_idx}", type='primary'):
                render_add_phase(session, position=phase_idx+1)
        
        phase_idx += 1

     
