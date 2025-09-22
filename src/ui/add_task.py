import streamlit as st
from datetime import date, timedelta
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
    if task_list:
        preceding_task = st.selectbox(
            label="Preceding task",
            options=task_list,
            format_func=lambda t: "- None -" if t is None else t.name,
            help="Select the task that directly precedes *{task_name}*"
        )

    start_date, end_date = st.date_input(
        label=f"Select the start and end dates for *{task_name}*",
        value=[date.today(), date.today() + timedelta(days=1)],
        key="task_start_date"
    )

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
