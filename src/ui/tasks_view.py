import pandas as pd
import streamlit as st
from ui.edit_task import render_task_edit
from dataclasses import dataclass
import pandas as pd
import datetime

class TaskColumns:
    name: int = 0
    planned_start: int = 1
    planned_finish: int = 2
    actual_start: int | None = None
    actual_finish: int | None = None
    edit = 3

    def __init__(self, col_widths: list[int]):
        if len(col_widths) == 6:
            self.actual_start = 3
            self.actual_finish = 4
            self.edit = 5



def render_tasks_table(session):
    phases = session.project.phases

    if not phases:
        st.info(f"Add a phase to {session.project.name} to view project planner")
        return

    
    c1, _ = st.columns([1,2])
    with c1.container(border=True):
        st.caption("Display Preferences")
        
        show_col, expand_col = st.columns(2)
        show_actual = show_col.toggle(
            label="Show actual start / end",
            value=False
        )

        expand_all = expand_col.toggle(
            label=f"Expand **{len(phases)}** Phases",
            value=False
        )

    col_widths = [3,2,2,1]
    if show_actual:
        col_widths = [3, 2, 2, 2, 2, 1]
    
    TASK_COLS = TaskColumns(col_widths)

    for pid in session.project.phase_order:
        phase = session.project.phases[pid]
        with st.expander(f"**{phase.name}**  "
                         f"({len(phase.tasks)} tasks)  "
                         f"- {phase.start_date or '—'} → {phase.end_date or '-'}",
                         expanded=expand_all):
            # Header row
            cols = st.columns(col_widths)
            cols[TASK_COLS.name].markdown("**Task**")
            cols[TASK_COLS.planned_start].markdown("**Start**")
            cols[TASK_COLS.planned_finish].markdown("**Finish**")

            if show_actual:
                cols[TASK_COLS.actual_start].markdown("**Actual Start**")
                cols[TASK_COLS.actual_finish].markdown("**Actual Finish**")

            cols[TASK_COLS.edit].markdown("**Edit**")

            for i, tid in enumerate(phase.task_order):
                t = phase.tasks[tid]
                cols[TASK_COLS.name].write(t.name)
                cols[TASK_COLS.planned_start].write(t.start_date.strftime("%Y-%m-%d %H:%M"))
                cols[TASK_COLS.planned_finish].write(t.end_date.strftime("%Y-%m-%d %H:%M"))


                if show_actual:
                    cols[TASK_COLS.actual_start].write(t.actual_start.strftime("%Y-%m-%d %H:%M") if not pd.isna(t.actual_start) else "")
                    cols[TASK_COLS.actual_finish].write(t.actual_end.strftime("%Y-%m-%d %H:%M") if not pd.isna(t.actual_end) else "")


                if cols[TASK_COLS.edit].button("✏️", key=f"edit_{phase.name}_{t.name}_{i}"):
                    render_task_edit(session, phase=phase, task=t)     

    

     
