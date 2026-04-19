import streamlit as st
from copy import deepcopy
from datetime import datetime, timedelta
from models.task import Task
from models.phase import Phase
from models.session import SessionModel
from models.constraint import Constraint, earliest_start_from_constraint
from ui.utils.constraints import build_constraint_target_labels, render_constraints_editor
from ui.utils.timezones import from_datetime_input_value, to_datetime_input_value
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
        label="Phase",
        placeholder="Admin",
        options=phase_ids,
        index=phase_index,
        format_func=lambda pid: proj.phases[pid].name,
        disabled=phase is not None,
    )

    phase_selected = proj.phases[pid_selected]

    task_list = phase_selected.get_task_list()
    
    task_name = st.text_input(
        label="Name",
        key=f"{phase_selected.name}_task_name"
    )

    dur, unit = st.columns(2)
    task_duration = dur.number_input(
        label="Duration",
        min_value=0.0,
        value=1.0,
        step=0.25,
    )

    duration_unit = unit.selectbox(
        label="Unit",
        options=["minutes", "hours", "days",],
        index=1
    )

    tdur = timedelta(hours=float(task_duration))
    if duration_unit == "minutes":
        tdur = timedelta(minutes=float(task_duration))
    elif duration_unit == "days":
        tdur = timedelta(days=float(task_duration))


    # convert answer to task's boolean planned field
    type_dict = {
        ":material/event_available: Planned": True,
        ":material/bolt: Unplanned": False
    }

    type_col, preds_col = st.columns(2)
    selected_task_type = type_col.pills(
        label="Planned / Unplanned",
        options=[":material/event_available: Planned", ":material/bolt: Unplanned"],
        default=":material/event_available: Planned",
        help="Select **'Planned'** for tasks known ahead of time. Use **'Unplanned'** when something unforeseen came up that had to be added."
    )

    task_type = type_dict[selected_task_type]

    has_constraints = preds_col.checkbox(
        label=f"Add predecessor constraints?",
        help="Select to add dependencies that this task has on other tasks in this phase. This unlocks powerful scheduling features like automatic rescheduling when things change.",
        value=False
    )

    constraints: list[Constraint] = []
    earliest_start = None
    if has_constraints:
        available_predecessors = build_constraint_target_labels(
            (
                task.uuid,
                f"{proj.phases[task.phase_id].name} / {task.name}",
            )
            for task in phase_selected.tasks.values()
        )

        constraints = render_constraints_editor(
            key=f"{phase_selected.uuid}_task_constraints",
            title="Add one or more predecessor rules for this task.",
            help_text="Choose the predecessor task in this phase that this task depends on.",
            constraints=[],
            predecessor_kind="task",
            labels_by_id=available_predecessors,
        )

        if constraints:
            earliest_start = max(
                earliest_start_from_constraint(
                    predecessor_start=phase_selected.tasks[constraint.predecessor_id].start_date,
                    predecessor_end=phase_selected.tasks[constraint.predecessor_id].end_date,
                    successor_duration=tdur,
                    relation=constraint.relation_type,
                    lag=constraint.lag,
                )
                for constraint in constraints
            )

            st.info(f":material/info: Earliest start based on constraints: *{earliest_start.strftime('%b %d, %Y %I:%M %p')}*")

    tz = session.project.timezone
    start_col, end_col = st.columns(2)
    if task_type:
        # planned task
        with start_col:
            planned_start_dt = st.datetime_input(
                label=f"Planned Start",
                value=to_datetime_input_value(earliest_start, tz),
                min_value=to_datetime_input_value(earliest_start, tz) if earliest_start else datetime(year=2000, month=1, day=1),
                key="task_start_date_single",
                disabled=not task_type,
                help="Planned start timestamp for this task."
            )
            planned_start_dt = from_datetime_input_value(planned_start_dt, tz)

        with end_col:        
            min_end_day = planned_start_dt + timedelta(seconds=1) if planned_start_dt else None
            
            planned_end_dt = st.datetime_input(
                label=f"Planned Finish",
                value=to_datetime_input_value(planned_start_dt + tdur, tz) if planned_start_dt else None,
                min_value=to_datetime_input_value(min_end_day, tz) if min_end_day else None,
                key="task_start_date",
                disabled=not task_type,
                help="Planned finish timestamp for this task."
            )
            planned_end_dt = from_datetime_input_value(planned_end_dt, tz)

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
                help="Actual start timestamp for this task."
            )
            actual_start_dt = from_datetime_input_value(actual_start_dt, tz)

        with end_col:        
            min_actual_end = actual_start_dt + timedelta(minutes=1) if actual_start_dt else None
            
            actual_end_dt = st.datetime_input(
                label=f"Actual Finish",
                value=to_datetime_input_value(min_actual_end, tz) if min_actual_end else None,
                min_value=to_datetime_input_value(actual_start_dt, tz) if actual_start_dt else None,
                key="task_actual_end",
                help="Actual finish timestamp for this task."
            )
            actual_end_dt = from_datetime_input_value(actual_end_dt, tz)

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
            index = len(task_uuids) - 1,
            format_func=lambda t: format_task_ids(tid=t, end_str=end_str) 
        )

        # insert at the end by default
        insert_idx = len(phase_selected.task_order)
       
        if before_task_id != end_str:
            insert_idx = task_uuids.index(before_task_id)


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
        try:
            draft_project = deepcopy(session.project)
            draft_phase = draft_project.phases[phase_selected.uuid]
            draft_project.add_task_to_phase(phase=draft_phase, task=new_task, position=insert_idx)
        except ValueError as exc:
            st.error(f"Unable to add task: {exc}")
            st.stop()

        session.project.add_task_to_phase(phase=phase_selected, task=new_task, position=insert_idx)

        st.info(f"'{task_name}' added successfully.")

        # Close dialog and refresh main view
        st.session_state.show_add_dialog = False
        time.sleep(1)
        st.rerun()
