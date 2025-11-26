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

    if not phase_selected:
        return
    
    task_name = st.text_input(
        label="Enter the name of a task",
        key=f"{phase_selected.name}_task_name"
    )

    task_list = [t for t in phase_selected.tasks.values()]
    
    predecessor_ids = []
    if task_list and st.checkbox("Has Predecessors", 
                                 help="Select if the new task has tasks that must complete before the task begins."):
        
        precedessor_options = [t.uuid for t in task_list]
        predecessor_ids = st.multiselect(
            label="Preceding tasks",
            options=precedessor_options,
            format_func=lambda id: phase_selected.tasks[id].name,
            help=f"Select all tasks that directly precede *{task_name}*"
        )

    if predecessor_ids:
        new_start_date = max(phase_selected.tasks[id].end_date for id in predecessor_ids)
        st.info(f"Earliest start based on predecessors: **{new_start_date.strftime("%Y-%m-%d %H:%M")}**")
    
    start_col, end_col = st.columns(2)
    with start_col:
        start_day = st.date_input(
            label=f"Start date",
            value=new_start_date if predecessor_ids else None,
            min_value=new_start_date if predecessor_ids else datetime(year=2000,month=1,day=1),
            key="task_start_date_single"
        )
        new_start_time = session.project.settings.work_start_time
        if predecessor_ids:
            new_start_time = new_start_date.time() 

        if not session.project.settings.work_all_day:
            start_time = st.time_input(
                label=f"Start time",
                value=new_start_time,
                key=f"task_start_time_{",".join(predecessor_ids)}"
            )
            if start_time < new_start_time:
                st.error(f"Start time comes before earliest start: {new_start_time.strftime("%H:%M")}")
            if start_day:
                start_date = datetime.combine(start_day, start_time)
            else:
                start_date = None

    with end_col:
        end_day = st.date_input(
            label=f"End date",
            value=new_start_date + timedelta(days=1) if predecessor_ids else None,
            key="task_start_date"
        )
        if not session.project.settings.work_all_day:
            end_time = st.time_input(
                label=f"End time",
                value=session.project.settings.work_end_time,
                key="task_end_time"
            )
            if end_day:
                end_date = datetime.combine(end_day, end_time)
            else:
                end_date = None

    if not start_date or not end_date:
        st.info("Select a start and end date to continue.")
        st.stop()

    task_note = st.text_input(
        label=f"Add a note for {task_name}",
        key=f"task_note_input"
    )

    if st.button(label=f"Add", disabled=not task_name, type='primary'):
        new_task = Task(
            name=task_name, 
            start_date=start_date, 
            end_date=end_date, 
            note=task_note if task_note else "",
            predecessor_ids=predecessor_ids
        )

        session.project.add_task_to_phase(phase=phase_selected, task=new_task,)

        st.info(f"'{task_name}' added successfully.")

        # Close dialog and refresh main view
        st.session_state.show_add_dialog = False
        time.sleep(1)
        st.rerun()
