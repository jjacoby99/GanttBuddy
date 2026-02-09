import streamlit as st
import pandas as pd
from models.phase import Phase
from models.task import Task
from models.session import SessionModel
import time
from datetime import datetime, timedelta, UTC, timezone
from zoneinfo import ZoneInfo

def is_timezone_aware(dt):
    """Check if a datetime object is timezone aware."""
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None

@st.dialog(f"Edit Task")
def render_task_edit(session, phase: Phase, task: Task):
    phases = session.project.phases

    if not phases:
        return
    
    edited_task_name = st.text_input(
        label="Edit name",
        value=task.name if task.name else ""
    )
    
    task_list = [t for t in phase.tasks.values()]

    predecessor_ids = task.predecessor_ids
    
    # convert answer to task's boolean planned field
    type_dict = {
        ":material/event_available: Planned": True,
        ":material/bolt: Unplanned": False
    }

    st.write(f"Loaded task type: {task.planned}")
    selected_task_type = st.pills(
        label="Planned / Unplanned",
        options=[":material/event_available: Planned", ":material/bolt: Unplanned"],
        default=":material/event_available: Planned" if task.planned else ":material/bolt: Unplanned",
        help="Select **'Planned'** for tasks known ahead of time. Use **'Unplanned'** when something unforeseen came up that had to be added."
    )

    task_type = type_dict[selected_task_type]

    with st.container(horizontal=True):
        enter_actuals = st.checkbox(
            "Enter Actuals?",
            value=task.completed,
            disabled=not task_type,
            help="Select to enter the actual start / end timestamps"
        )

        st.space(size="stretch")

        has_predecessors = st.checkbox(
            "Has Predecessors", 
            help="Select if the new task has tasks that must complete before the task begins.",
            value=len(predecessor_ids) > 0
        )

    if task_list and has_predecessors:
        st.divider()
        predecessor_ids = st.multiselect(
            label="Preceding tasks",
            options=[t.uuid for t in task_list],
            default=predecessor_ids,
            format_func=lambda id: phase.tasks[id].name,
            help=f"Select all tasks that directly precede *{edited_task_name}*"
        )

    new_start_date = task.start_date
    if predecessor_ids:
        new_start_date = max(phase.tasks[id].end_date for id in predecessor_ids)
        st.info(f"Earliest start based on predecessors: **{new_start_date.strftime("%Y-%m-%d %H:%M")}**")
    
    st.divider()
    st.caption(f"*{edited_task_name}* time stamps")

    label_col, start_col, end_col = st.columns([1,2,2])
    with label_col:
        st.space("small")
        st.write("**Planned**")

        if enter_actuals or not task_type:
            st.space("small")
            st.caption("")
            st.write("**Actual**")

    with start_col:
        planned_start_dt = st.datetime_input(
            label=f"Planned Start",
            value=task.start_date if task.start_date else new_start_date,
            min_value=new_start_date if predecessor_ids else datetime(year=2000,month=1,day=1),
            key="task_start_date_single",
            disabled=not task_type,
            help="**Planned start** timestamp for *{edited_task_name}*"
        )
        planned_start_dt = planned_start_dt.astimezone()


    with end_col:
        min_end_day = task.end_date
        if min_end_day < planned_start_dt:
            min_end_day = planned_start_dt + timedelta(min_end_day=1)
        
        planned_end_dt = st.datetime_input(
            label=f"Planned Finish",
            value=task.end_date if task.end_date else min_end_day,
            min_value=min_end_day if planned_start_dt else datetime.today(),
            disabled=not task_type,
            key="task_start_date",
            help="**Planned end** timestamp for *{edited_task_name}*"
        )
        planned_end_dt = planned_end_dt.astimezone()

    if enter_actuals or not task_type:
        actual_start_dt = start_col.datetime_input(
            label="Actual Start",
            value=task.actual_start if task.actual_start else None,
            help=f"**Actual start** timestamp for *{edited_task_name}*"
        )

        if actual_start_dt:
            actual_start_dt = actual_start_dt.astimezone()

        actual_end_dt = end_col.datetime_input(
            label=f"Actual Finish",
            value=task.actual_end if task.actual_end else None,
            help=f"**Actual end** timestamp for *{edited_task_name}*"
        )
        if actual_end_dt:
            actual_end_dt = actual_end_dt.astimezone()


    if not planned_start_dt or not planned_end_dt:
        st.info("Select a start and end date to continue.")
        st.stop()

    st.divider()
    status_map = {
        "NOT_STARTED": ":material/schedule: Not Started",
        "IN_PROGRESS": ":material/autorenew: In Progress",
        "COMPLETE": ":material/check_circle: Complete",
        "BLOCKED": ":material/block: Blocked"
    }

    task_status = st.pills(
        label="Status",
        options=status_map.keys(),
        default=task.status,
        format_func=lambda s: status_map[s],
        help=f"Update the status of {edited_task_name}",
        selection_mode="single"
    )

    task_note = st.text_area(
        label=f"Add a note for '{edited_task_name}'",
        value=task.note if task.note else "",
        key=f"task_note_input"
    )
    c1, c2, c3 = st.columns(3)
    if c1.button(label=f"Update", disabled=not edited_task_name, type='primary'):
        new_task = Task(
            name=edited_task_name, 
            phase_id=phase.uuid,
            start_date=planned_start_dt if task_type else actual_start_dt, 
            end_date=planned_end_dt if task_type else actual_start_dt, 
            actual_start=actual_start_dt if enter_actuals or not task_type else None,
            actual_end=actual_end_dt if enter_actuals or not task_type else None,
            note=task_note if task_note else "",
            predecessor_ids=predecessor_ids,
            status=task_status,
            planned=task_type,
        )
        session.project.update_task(phase=phase, old_task=task, new_task=new_task)

        st.info(f"'{edited_task_name}' updated successfully.")

        st.session_state.show_edit_dialog = False
        time.sleep(1)
        st.rerun()

    if c2.button('Cancel'):
        st.rerun()

    if c3.button('Delete'):
        name = task.name
        predecessors_had = phase.delete_task(task)

        st.info(f'\'{name}\' deleted. {predecessors_had} Tasks were preceded.')
        time.sleep(1)
        st.rerun()


        

