import streamlit as st
from copy import deepcopy
from models.phase import Phase
from models.task import Task, TaskType
from models.session import SessionModel
from models.constraint import Constraint, earliest_start_from_constraint
from ui.utils.constraints import build_constraint_target_labels, render_constraints_editor
from ui.utils.timezones import from_datetime_input_value, to_datetime_input_value
import time
from datetime import datetime, timedelta

from logic.gantt_builder import build_timeline, build_gantt_df # need to clear cache when task updated.

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
    
    dur, unit = st.columns(2)
    planned_duration = task.planned_duration
    duration_defaults = {
        "minutes": planned_duration.total_seconds() / 60,
        "hours": planned_duration.total_seconds() / 3600,
        "days": planned_duration.total_seconds() / 86400,
    }
    
    default_duration_unit = "hours"
    if planned_duration.total_seconds() % 86400 == 0:
        default_duration_unit = "days"
    

    task_duration = dur.number_input(
        label="Duration",
        min_value=0.0,
        value=float(duration_defaults[default_duration_unit]),
        step=0.25,
    )
    duration_unit = unit.selectbox(
        label="Unit",
        options=["minutes", "hours", "days"],
        index=["minutes", "hours", "days"].index(default_duration_unit),
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

    with st.container(horizontal=True):
        selected_task_type = st.pills(
            label="Planned / Unplanned",
            options=[":material/event_available: Planned", ":material/bolt: Unplanned"],
            default=":material/event_available: Planned" if task.planned else ":material/bolt: Unplanned",
            help="Select **'Planned'** for tasks known ahead of time. Use **'Unplanned'** when something unforeseen came up that had to be added."
        )

        task_planned = type_dict[selected_task_type]

        st.space("stretch")
        task_type_options = list(TaskType)
        task_type_index = task_type_options.index(task.task_type)
        task_type = st.selectbox(
            label="Task type",
            options=task_type_options,
            index=task_type_index,
            format_func=lambda t: t.value.replace("_", " ").title(),
            help="Specify what's going on in this task. This unlocks some powerful analytics.",
            key=f"{task.uuid}_type"
        )

    with st.container(horizontal=True):
        enter_actuals = st.checkbox(
            "Enter Actuals?",
            value=task.completed,
            disabled=not task_planned,
            help="Select to enter the actual start / end timestamps"
        )

        st.space(size="stretch")

        has_constraints = st.checkbox(
            label="Add predecessor constraints?",
            value=len(task.constraints) > 0,
            help="Select to add dependencies that this task has on other tasks."
        )

    constraints: list[Constraint] = []
    earliest_start = None
    if has_constraints:
        available_predecessors = build_constraint_target_labels(
            (candidate.uuid, candidate.name)
            for candidate in phase.tasks.values()
            if candidate.uuid != task.uuid
        )
        constraints = render_constraints_editor(
            key=f"{task.uuid}_constraints",
            title=f"Predecessor rules for {edited_task_name or task.name}.",
            help_text="Choose the predecessor task this task depends on.",
            constraints=task.constraints,
            predecessor_kind="task",
            labels_by_id=available_predecessors,
        )
        if constraints:
            earliest_start = max(
                earliest_start_from_constraint(
                    predecessor_start=phase.tasks[constraint.predecessor_id].start_date,
                    predecessor_end=phase.tasks[constraint.predecessor_id].end_date,
                    successor_duration=tdur,
                    relation=constraint.relation_type,
                    lag=constraint.lag,
                )
                for constraint in constraints
            )
            st.info(f":material/info: Earliest start based on constraints: *{earliest_start.strftime('%b %d, %Y %I:%M %p')}*")

    st.caption(f"*{edited_task_name}* time stamps")
    tz = session.project.timezone

    label_col, start_col, end_col = st.columns([1,2,2])
    with label_col:
        st.space("small")
        st.write("**Planned**")

        if enter_actuals or not task_planned:
            st.space("small")
            st.caption("")
            st.write("**Actual**")

    with start_col:
        planned_start_dt = st.datetime_input(
            label=f"Planned Start",
            value=to_datetime_input_value(task.start_date, tz),
            min_value=to_datetime_input_value(earliest_start, tz) if earliest_start else datetime(year=2000,month=1,day=1),
            key="task_start_date_single",
            disabled=not task_planned,
            help="**Planned start** timestamp for *{edited_task_name}*"
        )
        planned_start_dt = from_datetime_input_value(planned_start_dt, tz)


    with end_col:
        min_end_day = planned_start_dt + timedelta(seconds=1)
    
        planned_end_dt = st.datetime_input(
            label=f"Planned Finish",
            value=to_datetime_input_value(planned_start_dt + tdur, tz) if planned_start_dt else to_datetime_input_value(task.end_date, tz),
            min_value=to_datetime_input_value(min_end_day, tz) if planned_start_dt else None,
            disabled=not task_planned,
            key="task_start_date",
            help=f"**Planned end** timestamp for *{edited_task_name}*"
        )
        planned_end_dt = from_datetime_input_value(planned_end_dt, tz)

    actual_start_dt = None
    actual_end_dt = None
    if enter_actuals or not task_planned:
        actual_start_dt = start_col.datetime_input(
            label="Actual Start",
            value=to_datetime_input_value(task.actual_start, tz),
            help=f"**Actual start** timestamp for *{edited_task_name}*"
        )

        actual_start_dt = from_datetime_input_value(actual_start_dt, tz)

        actual_end_dt = end_col.datetime_input(
            label=f"Actual Finish",
            value=to_datetime_input_value(task.actual_end, tz),
            help=f"**Actual end** timestamp for *{edited_task_name}*"
        )
        actual_end_dt = from_datetime_input_value(actual_end_dt, tz)


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
            start_date=planned_start_dt, # if task_planned else actual_start_dt, 
            end_date=planned_end_dt, # if task_planned else actual_start_dt, 
            actual_start=actual_start_dt if enter_actuals or not task_planned else None,
            actual_end=actual_end_dt if enter_actuals or not task_planned else None,
            note=task_note if task_note else "",
            constraints=constraints,
            task_type=task_type,
            status=task_status,
            planned=task_planned,
        )
        try:
            draft_project = deepcopy(session.project)
            draft_phase = draft_project.phases[phase.uuid]
            draft_old_task = draft_phase.tasks[task.uuid]
            draft_project.update_task(phase=draft_phase, old_task=draft_old_task, new_task=new_task)
        except ValueError as exc:
            st.error(f"Unable to update task: {exc}")
            st.stop()
        session.project.update_task(phase=phase, old_task=task, new_task=new_task)

        st.info(f"'{edited_task_name}' updated successfully.")

        st.session_state.show_edit_dialog = False
        
        # clear timeline cache on edit to force regeneration of gantt.
        # previously, changes weren't reflected.
        build_timeline.clear()
        build_gantt_df.clear()

        time.sleep(1)
        st.rerun()

    if c2.button('Cancel'):
        st.rerun()

    if c3.button('Delete'):
        name = task.name
        predecessors_had = phase.delete_task(task)
        session.project.resolve_schedule()

        st.info(f'\'{name}\' deleted. {predecessors_had} Tasks were preceded.')

        build_timeline.clear()
        build_gantt_df.clear()
        time.sleep(1)
        st.rerun()


        

