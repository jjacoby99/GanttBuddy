import streamlit as st
import datetime as dt

from models.session import SessionModel
from models.project import Project
from models.phase import Phase
from models.task import Task

from logic.backend.project_permissions import project_is_read_only
from ui.utils.phase_controls import prev_execution_phase, next_execution_phase

def get_current_execution_task_index(project: Project) -> tuple[int, int]:
    """
        Get the current execution task index as a tuple of (phase_index, task_index) based on the first incomplete task in the project. 
        If all tasks are completed, returns the last task.
    """
    for pidx, pid in enumerate(project.phase_order):
        phase = project.phases[pid]
        for tidx, tid in enumerate(phase.task_order):
            task = phase.tasks[tid]
            if not task.completed:
                return (pidx, tidx)

    return (len(project.phase_order) - 1, len(project.phases[project.phase_order[-1]].task_order) - 1)

from dataclasses import dataclass
@dataclass
class ManualInputState:
    actual_start: dt.datetime | None = None
    actual_end: dt.datetime | None = None
    note: str = ""

def _render_manual_input(task: Task) -> ManualInputState:
    enter_end = st.checkbox(
            label="Specify Task End?",
            value=True if task.actual_start else False,
            help="Select if you want to specify the actual start and end of the task"
        )

    with st.container():
        c1, c2 = st.columns(2)

        actual_start = c1.datetime_input(
            label="Actual Start",
            value=task.actual_start if task.actual_start else None,
            key=f"execution_actual_start_datetime_{task.uuid}",
            step=dt.timedelta(minutes=5)
        )


        actual_end = c2.datetime_input(
            label="Actual End",
            value=task.actual_end if task.actual_end else None,
            key=f"execution_actual_end_datetime_{task.uuid}",
            disabled=not enter_end,
            step=dt.timedelta(minutes=5)
        )

        note = st.text_area(
            label="Execution Note",
            placeholder="Enter relevant details about the task here. Think delays, rationale, wins, lossess, etc.",
            height=400,
            value=task.note if task.note else None
        )

    return ManualInputState(actual_start=actual_start, actual_end=actual_end, note=note)


def _render_timestamp_input(task: Task) -> ManualInputState:
    c1, c2 = st.columns(2)

    if not task.actual_start:
        if c1.button(f":material/watch: Start Task"):
            timestamp = dt.datetime.now()
            st.caption("Task start")
            c1.metric(
                "Actual Start",
                task.actual_start.strftime("%Y-%m-%d %H:%M") if task.actual_start else "N/A"
            )
            return ManualInputState(actual_start=timestamp)
    

    if not task.actual_end:
        c1.metric(
            "Actual Start",
            task.actual_start.strftime("%Y-%m-%d %H:%M") if task.actual_start else "N/A"
        )
       
        with c2.empty():
            st.space("small")
            end_task = st.button(f":material/hourglass_empty: End Task")
            if end_task:
                timestamp = dt.datetime.now()
                st.metric(
                    "Actual End",
                    timestamp.strftime("%Y-%m-%d %H:%M")
                )

                return ManualInputState(actual_start=task.actual_start,actual_end=timestamp)

def render_execution_view(session: SessionModel):
    st.subheader("Execution View")
    st.caption("Fill in progress as your project progresses.")
    if project_is_read_only():
        st.info("This project is read-only, so execution updates are disabled.")
        return
    
    
    if not session.project.phases:
        st.info("Add phases and tasks to your project to track execution progress.")
        return

    mode = st.segmented_control(
        label="Update Mode",
        options=["Manual Entry", "Timestamp"],
        default="Manual Entry"
    )
    
    phase_idx, task_idx = get_current_execution_task_index(session.project)
    pid = session.project.phase_order[phase_idx]
    phase = session.project.phases[pid]

    task = phase.tasks[phase.task_order[task_idx]]
    
    if task.completed:
        st.info(f"task '{task.name}' has actuals enterred. Click Update Progress to overwrite.")
        
    st.header(f"Phase {phase_idx+1} of {len(session.project.phase_order)}: **{phase.name}**")

    with st.container(width="content"):
        st.markdown(f"**Task {task_idx+1} of {len(phase.task_order)}:** *{task.name}*")
        
        with st.container(horizontal=True):
            st.metric(f"Planned Start", f"{task.start_date.strftime('%B-%d %H:%M') if task.start_date else 'N/A'}")
            st.metric(f"Planned End", f"{task.end_date.strftime('%B-%d %H:%M') if task.end_date else 'N/A'}")

        match mode:
            case "Manual Entry":
                state = _render_manual_input(task)
            case "Timestamp":
                state = _render_timestamp_input(task)

        submitted = st.button(":material/event_available: Update Progress", type="primary", disabled=project_is_read_only())
        if submitted:
            task.actual_start = state.actual_start
            task.actual_end = state.actual_end

            if task.actual_start and not task.actual_end:
                st.badge("Task Started!", icon=":material/check:", color="green")

            if task.completed:
                st.badge("Task Completed!", icon=":material/check:", color="green")

            task.note += f"\nExecution note: {state.note}" if state.note else ""

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
    




