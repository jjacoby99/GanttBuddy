import pandas as pd
import streamlit as st
from ui.edit_task import render_task_edit
from ui.add_task import render_task_add
from ui.edit_phase import render_phase_edit
from ui.add_phase import render_add_phase
from ui.utils.status_badges import STATUS_BADGES

from models.phase import Phase
from models.task import Task
from models.plan_state import PlanState, TaskColumns

from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import datetime

def map_completion_to_badge(completion: float) -> tuple[str, str, str]:
    if completion >= 1.0:
        return ("Complete", ":material/check_circle:", "green")
    elif completion > 0.0:
        return (f"{completion*100:.1f}% Complete", ":material/timer:", "yellow")
    else:
        return ("Not Started", ":material/info:", "blue")

def write_header_row(columns: TaskColumns, col_widths: list[int], plan_ui_state: PlanState):
    header_cols = st.columns(col_widths)
    header_cols[columns.name].markdown(f"### ACTIVITY")
    header_cols[columns.planned_start].markdown(f"### PLANNED START")
    header_cols[columns.planned_finish].markdown(f"### PLANNED FINISH")

    header_cols[columns.status].markdown(f"### STATUS")
    if plan_ui_state.show_actuals:
            header_cols[columns.actual_start].markdown("### ACTUAL START")
            header_cols[columns.actual_finish].markdown("### ACTUAL FINISH")
    header_cols[columns.edit].markdown("### EDIT")

    st.divider()

def write_phase_header(phase: Phase, phase_idx: int, columns: TaskColumns, col_widths: list[int], plan_ui_state: PlanState):
    phase_columns = st.columns(col_widths)

    phase_start = phase.start_date.strftime("%Y-%m-%d %H:%M") if phase.start_date else '-'
    phase_end = phase.end_date.strftime("%Y-%m-%d %H:%M") if phase.end_date else '-'

    phase_columns[columns.name].markdown(f"**{phase_idx+1}. {phase.name}**")
    phase_columns[columns.planned_start].markdown(f"**{phase_start}**")
    phase_columns[columns.planned_finish].markdown(f"**{phase_end}**")

    label, icon, color = map_completion_to_badge(phase.tasks_completed / len(phase.tasks) if phase.tasks else 0.0)
    phase_columns[columns.status].badge(label, icon=icon, color=color)
    if plan_ui_state.show_actuals:
            phase_columns[columns.actual_start].markdown(f"**{phase.actual_start.strftime('%Y-%m-%d %H:%M') if phase.actual_start else '-'}**")
            phase_columns[columns.actual_finish].markdown(f"**{phase.actual_end.strftime('%Y-%m-%d %H:%M') if phase.actual_end else '-'}**")
    
    button_label = ":material/keyboard_arrow_down:" if plan_ui_state.expanded_phases[phase.uuid] else ":material/keyboard_arrow_up:"
    button_clicked = phase_columns[columns.edit].button(button_label, key=f"edit_{phase.name}_{phase_idx}")
    
    if button_clicked:
        plan_ui_state.toggle_phase_expansion(phase.uuid)


def render_tasks_table(session, plan_ui_state: PlanState):
    phases = session.project.phases

    if not phases:
        st.info(f"Add a phase to {session.project.name} to view project planner")
        return
    
    st.subheader("Project Phases")
    
    columns = TaskColumns(show_actuals=plan_ui_state.show_actuals)
    col_widths = columns.get_col_widths()

    write_header_row(columns, col_widths,plan_ui_state)

    
    for phase_idx, pid in enumerate(session.project.phase_order):
        
        phase = session.project.phases[pid]
        with st.container(border=True):
            write_phase_header(phase, phase_idx, columns, col_widths, plan_ui_state)
            
            if not plan_ui_state.expanded_phases[phase.uuid]:
                continue
            
            cols = st.columns(col_widths)

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

                    if plan_ui_state.show_actuals:
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
                render_add_phase(session, position=phase_idx+1, plan_ui_state=plan_ui_state)
        
        phase_idx += 1

        
