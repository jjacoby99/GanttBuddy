import streamlit as st
from datetime import date, datetime, timedelta
from models.task import Task
from models.project import Project
from models.phase import Phase
from models.session import SessionModel
import time

@st.dialog("Add a new task")
def render_task_add(session: SessionModel, phase: Phase = None):
    if phase:
        phase_selected = st.selectbox(
            label="Select project phase to add task to.",
            placeholder=phase.name,
            options=[phase],
            format_func=lambda t: t.name,
            disabled=True
        )
    else: 
        phase_selected = st.selectbox(
            label="Select project phase to add task to.",
            placeholder="Admin",
            options=[p for p in session.project.phases.values()],
            format_func=lambda p: p.name
        )
    
    task_name = st.text_input(
        label="Enter the name of a task",
        key=f"{phase_selected.name}_task_name"
    )

    task_list = [t for t in phase_selected.tasks.values()]
    
    predecessor_ids = []
    has_predecessors = st.checkbox(
        "Has Predecessors", 
        help="Select if the new task has tasks that must complete before the task begins.",
        value=len(predecessor_ids) > 0
    )

    if task_list and has_predecessors:
        st.divider()
        precedessor_options = [t.uuid for t in task_list]
        predecessor_ids = st.multiselect(
            label="Preceding tasks",
            options=precedessor_options,
            format_func=lambda id: phase_selected.tasks[id].name,
            help=f"Select all tasks that directly precede *{task_name}*"
        )

    new_start_date = None
    if predecessor_ids:
        new_start_date = max(phase_selected.tasks[id].end_date for id in predecessor_ids)
        st.info(f"Earliest start based on predecessors: **{new_start_date.strftime("%Y-%m-%d %H:%M")}**")
    
    start_col, end_col = st.columns(2)
    with start_col:
        planned_start_dt = st.datetime_input(
            label=f"Planned Start",
            value=new_start_date,
            min_value=new_start_date if predecessor_ids else datetime(year=2000,month=1,day=1),
            key="task_start_date_single",
            help="**Planned start** timestamp for *{edited_task_name}*"
        )



    with end_col:        
        min_end_day = planned_start_dt + timedelta(minutes=1) if planned_start_dt else datetime.today()
        
        planned_end_dt = st.datetime_input(
            label=f"Planned Finish",
            value=min_end_day if planned_start_dt else None,
            min_value=min_end_day,
            key="task_start_date",
            help="**Planned end** timestamp for *{edited_task_name}*"
        )

    if not planned_start_dt or not planned_end_dt:
        st.info("Select a start and end date to continue.")
        st.stop()

    task_note = st.text_input(
        label=f"Add a note for '{task_name}'",
        key=f"task_note_input"
    )

    if st.button(label=f"Add", disabled=not task_name, type='primary'):
        new_task = Task(
            name=task_name, 
            start_date=planned_start_dt, 
            end_date=planned_end_dt, 
            note=task_note if task_note else "",
            predecessor_ids=predecessor_ids
        )

        session.project.add_task_to_phase(phase=phase_selected, task=new_task,)

        st.info(f"'{task_name}' added successfully.")

        # Close dialog and refresh main view
        st.session_state.show_add_dialog = False
        time.sleep(1)
        st.rerun()
