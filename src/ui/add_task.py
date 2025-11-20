import streamlit as st
from datetime import date, datetime, timedelta
from models.task import Task
from models.project import Project
from models.phase import Phase
import time

@st.dialog("Add new task to project")
def render_task_add(session):

    phase = st.selectbox(
        label="Select project phase to add task to.",
        placeholder="Admin",
        options=session.project.phases,
        format_func=lambda t: t.name
    )

    if not phase:
        return
    
    task_name = st.text_input(
        label="Enter the name of a task",
        value=st.session_state.get("task_name", ""),
        key="task_name"
    )

    try:
        phase_idx = session.project.get_phase_index(phase)
    except RuntimeError:
        st.error(f"Project {session.project.name} doesn't contain any phases.")
        return
    except ValueError:
        st.error(f"Project {session.project.name} doesn't contain a {phase.name} phase.")

    task_list = session.project.phases[phase_idx].tasks

    preceding_task = None
    if task_list and st.checkbox("Set preceding task"):
        preceding_task = st.selectbox(
            label="Preceding task",
            options=task_list,
            format_func=lambda t: "- None -" if t is None else t.name,
            help="Select the task that directly precedes *{task_name}*"
        )

    if preceding_task:
        new_start_date = preceding_task.end_date
    
    start_col, end_col = st.columns(2)
    with start_col:
        start_day = st.date_input(
            label=f"Start date",
            value=new_start_date if preceding_task else None,
            key="task_start_date_single"
        )
        if not session.project.settings.work_all_day:
            start_time = st.time_input(
                label=f"Start time",
                value=session.project.settings.work_start_time,
                key="task_start_time"
            )
            if start_day:
                start_date = datetime.combine(start_day, start_time)
            else:
                start_date = None

    with end_col:
        end_day = st.date_input(
            label=f"End date",
            value=new_start_date + timedelta(days=1) if preceding_task else None,
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

    if st.button(label=f"Add *{task_name or 'task'}* to project", disabled=not task_name):
        new_task = Task(
            name=task_name, 
            start_date=start_date, 
            end_date=end_date, 
            note=task_note if task_note else "",
            preceding_task=preceding_task
        )

        session.project.add_task_to_phase(phase=phase, task=new_task,)

        st.info(f"'{task_name}' added successfully.")

        # Close dialog and refresh main view
        st.session_state.show_add_dialog = False
        time.sleep(1)
        st.rerun()
