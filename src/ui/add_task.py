import streamlit as st
from datetime import date, timedelta
from lib.task import Task

@st.dialog("Add new task to project")
def render_task_add(session):
    # Inputs
    task_name = st.text_input(
        label="Enter the name of a task",
        value=st.session_state.get("task_name", ""),
        key="task_name"
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

    task_list = session.get_tasks()
    preceding_task = None
    if task_list:
        preceding_task = st.selectbox(
            label="Preceding task",
            options=task_list,
            format_func=lambda t: "- None -" if t is None else t.name,
            help="Select the task that directly precedes *{task_name}*"
        )

    # Submit button in the dialog
    if st.button(label=f"Add *{task_name or 'task'}* to project", disabled=not task_name):
        new_task = Task(name=task_name, start_date=start_date, end_date=end_date, note=task_note if task_note else "")
        session.add_task(new_task, preceding_task)

        # Toast + clear form fields
        st.toast(f"'{task_name}' added successfully.")
        for el in ["task_name", "task_start_date", "task_end_date"]:
            if el in st.session_state:
                del st.session_state[el]

        # Close dialog and refresh main view
        st.session_state.show_add_dialog = False
        st.rerun()
