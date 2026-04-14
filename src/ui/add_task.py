import streamlit as st
from datetime import date, datetime, timedelta
from models.task import Task
from models.project import Project
from models.phase import Phase
from models.session import SessionModel
from models.constraint import Constraint
from ui.utils.constraints import build_constraint_target_labels, render_constraints_editor
import time

@st.dialog("Add a new task")
def render_task_add(session: SessionModel, phase: Phase = None):
    proj = session.project if session.project else None
    if not proj:
        return
    
    phase_ids = [pid for pid in proj.phase_order]
    phase_index = None
    if phase is not None:
        phase_index = phase_ids.index(phase.uuid)

    pid_selected = st.selectbox(
        label="Select project phase to add task to.",
        placeholder="Admin",
        options=phase_ids,
        index=phase_index,
        format_func=lambda pid: proj.phases[pid].name
    )

    phase_selected = proj.phases[pid_selected]

    task_list = phase_selected.get_task_list()
    
    task_name = st.text_input(
        label="Enter the name of a task",
        key=f"{phase_selected.name}_task_name"
    )

    insert_idx = 0
    if task_list:
        def format_task_ids(tid: str, end_str: str | None = None) -> str:
            if tid != end_str:
                return phase_selected.tasks[tid].name
            return tid
        
        end_str = "-- Move to End --"

        task_uuids = [t.uuid for t in task_list]
        task_uuids.append(end_str)
        before_task_id = st.selectbox(
            label="Add task before",
            key=f"add_before_task",
            options=task_uuids,
            format_func=lambda t: format_task_ids(tid=t, end_str=end_str) 
        )

        # insert at the end by default
        insert_idx = len(phase_selected)

        if before_task_id != end_str:
            insert_idx = task_uuids.index(before_task_id)
    
    type_col, preds_col = st.columns(2)
    
    # convert answer to task's boolean planned field
    type_dict = {
        ":material/event_available: Planned": True,
        ":material/bolt: Unplanned": False
    }

    selected_task_type = type_col.pills(
        label="Planned / Unplanned",
        options=[":material/event_available: Planned", ":material/bolt: Unplanned"],
        default=":material/event_available: Planned",
        help="Select **'Planned'** for tasks known ahead of time. Use **'Unplanned'** when something unforeseen came up that had to be added."
    )

    task_type = type_dict[selected_task_type]

    preds_col.space("small")

    available_predecessors = build_constraint_target_labels(
        (
            task.uuid,
            f"{proj.phases[task.phase_id].name} / {task.name}",
        )
        for task in proj.get_task_list()
    )
    constraints: list[Constraint] = []
    with preds_col:
        constraints = render_constraints_editor(
            key=f"{phase_selected.uuid}_task_constraints",
            title="Add one or more predecessor rules for this task.",
            help_text="Choose the predecessor task this task depends on.",
            constraints=[],
            predecessor_kind="task",
            labels_by_id=available_predecessors,
        )

    start_col, end_col = st.columns(2)
    if task_type:
        # planned task
        with start_col:
            planned_start_dt = st.datetime_input(
                label=f"Planned Start",
                value=None,
                min_value=datetime(year=2000,month=1,day=1),
                key="task_start_date_single",
                disabled=not task_type,
                help="**Planned start** timestamp for *{edited_task_name}*"
            )
            if planned_start_dt:
                planned_start_dt = planned_start_dt.astimezone()

        with end_col:        
            min_end_day = planned_start_dt + timedelta(seconds=1) if planned_start_dt else None
            
            planned_end_dt = st.datetime_input(
                label=f"Planned Finish",
                value=min_end_day if planned_start_dt else None,
                min_value=min_end_day,
                key="task_start_date",
                disabled=not task_type,
                help="**Planned end** timestamp for *{edited_task_name}*"
            )
            if planned_end_dt:
                planned_end_dt = planned_end_dt.astimezone()

        if not planned_start_dt or not planned_end_dt:
            st.info("Select a start and end date to continue.")
            st.stop()

    else:
        # unplanned task
        with start_col:
            actual_start_dt = st.datetime_input(
                label=f"Actual Start",
                value=None,
                min_value=datetime(year=2000,month=1,day=1),
                key="task_actual_start",
                help="**Actual Start** timestamp for *{edited_task_name}*"
            )
            if actual_start_dt:
                actual_start_dt = actual_start_dt.astimezone()

        with end_col:        
            min_actual_end = actual_start_dt + timedelta(minutes=1) if actual_start_dt else datetime.today()
            
            actual_end_dt = st.datetime_input(
                label=f"Actual Finish",
                value=min_actual_end if actual_start_dt else None,
                min_value=actual_start_dt,
                key="task_actual_end",
                help="**Actual End** timestamp for *{edited_task_name}*"
            )

            if actual_end_dt:
                actual_end_dt = actual_end_dt.astimezone()

    task_note = st.text_area(
        label=f"Add a note for '{task_name}'",
        key=f"task_note_input"
    )

    if st.button(label=f"Add", disabled=not task_name, type='primary'):
        new_task = Task(
            name=task_name, 
            start_date=planned_start_dt if task_type else actual_start_dt, # may need to be null, but will cause problems 
            end_date=planned_end_dt if task_type else actual_start_dt, # same here. purposefully made 0 planned duration.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                
            actual_start=None if task_type else actual_start_dt,
            actual_end=None if task_type else actual_end_dt,
            note=task_note if task_note else "",
            constraints=constraints,
            planned=task_type
        )

        session.project.add_task_to_phase(phase=phase_selected, task=new_task, position=insert_idx)

        st.info(f"'{task_name}' added successfully.")

        # Close dialog and refresh main view
        st.session_state.show_add_dialog = False
        time.sleep(1)
        st.rerun()
