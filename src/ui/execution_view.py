import streamlit as st
import datetime as dt

from models.session import SessionModel
from models.project import Project
from models.phase import Phase
from models.task import Task

from ui.utils.phase_controls import prev_execution_phase, next_execution_phase

def render_execution_view(session: SessionModel):
    st.subheader("Execution View")
    st.caption("Fill in progress as your project progresses.")


    if not session.project.phases:
        st.info("Add phases and tasks to your project to track execution progress.")
        return
    
    
    
    phase_idx = st.session_state.ui.execution_phase_index
    pid = session.project.phase_order[phase_idx]
    phase = session.project.phases[pid]

    

    task = phase.tasks[phase.task_order[st.session_state.ui.execution_task_index]]
    
    if task.completed:
        st.info(f"task '{task.name}' has actuals enterred. Click Update Progress to overwrite.")
        
    st.header(f"Phase {phase_idx+1} of {len(session.project.phase_order)}: **{phase.name}**")

    with st.form(f"execution_form_{task.uuid}1", width="content"):
        st.subheader(f"Task {st.session_state.ui.execution_task_index+1} of {len(phase.task_order)}: **{task.name}**")
        
        st.caption(f"Planned Start/End")
        with st.container(horizontal=True):
            st.metric(f"Planned Start", f"{task.start_date.strftime('%B-%d %H:%M') if task.start_date else 'N/A'}")
            st.metric(f"Planned End", f"{task.end_date.strftime('%B-%d %H:%M') if task.end_date else 'N/A'}")
        
        st.caption(f"Enter Actual Start/End")
        enter_end = st.checkbox(
            label="Specify Task End?",
            value=False,
            help="Select if you want to specify the actual start and end of the task"
        )

        with st.container():
            c1, c2 = st.columns(2)
            actual_start = c1.date_input(
                label="Actual Start Date",
                value=task.actual_start.date() if task.actual_start else dt.date.today(),
                key=f"execution_actual_start_{task.uuid}",
                width=100
            )

            start_time = c1.time_input(
                label="Actual Start Time",
                value=task.actual_start.time() if task.actual_start else dt.datetime.now().time(),
                key=f"execution_actual_start_time_{task.uuid}",
                width=100
            )

            actual_end = c2.date_input(
                label="Actual End Date",
                value=task.actual_end.date() if task.actual_end else dt.date.today(),
                key=f"execution_actual_end_{task.uuid}",
                disabled=not enter_end,
                width=100
            )

            end_time = c2.time_input(
                label="Actual End Time",
                value=task.actual_end.time() if task.actual_end else dt.datetime.now().time(),
                key=f"execution_actual_end_time_{task.uuid}",
                disabled=not enter_end,
                width=100
            )

            start_dt = dt.datetime.combine(actual_start, start_time)
            end_dt = dt.datetime.combine(actual_end, end_time)

            if end_dt < start_dt:
                st.error("End date must be after start date.")
                return
            
            note = st.text_area(
                label="Execution Note",
                placeholder="Enter relevant details about the task here. Think delays, rationale, wins, lossess, etc.",
                height=400,
                value=task.note if task.note else None
            )

        submitted = st.form_submit_button(":material/event_available: Update Progress", type="primary")
        if submitted:
            task.actual_start = start_dt
            task.actual_end = end_dt
            task.note = note
            st.success(f"Updated actuals for task **{task.name}**.")

            # incrememnt the task index
            t_idx = st.session_state.ui.execution_task_index
            if t_idx >= len(phase.task_order) - 1:
                # move to next phase
                if phase_idx >= len(session.project.phase_order) - 1:
                    st.success("All tasks updated.")
                    st.rerun()
                else:
                    st.session_state.ui.execution_phase_index += 1
                    st.session_state.ui.execution_task_index = 0
            st.rerun()
    




