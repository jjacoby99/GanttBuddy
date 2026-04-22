from __future__ import annotations

from time import sleep

import streamlit as st

from logic.backend.api_client import delete_project, fetch_attention_tasks
from logic.feature_flags import signals_enabled
from logic.backend.project_delete import get_project_delete_impact
from logic.backend.project_permissions import project_can_delete
from models.plan_state import PlanState
from models.project_access import ProjectAccess
from models.project_delete import ProjectDeleteImpact
from models.session import SessionModel


def _render_impact_metrics(impact: ProjectDeleteImpact) -> None:
    primary_left, primary_mid, primary_right = st.columns(3)
    primary_left.metric("Phases", impact.phases_count)
    primary_mid.metric("Tasks", impact.tasks_count)
    primary_right.metric("Todos", impact.todos_count)

    related_left, related_mid, related_right = st.columns(3)
    related_left.metric("Events", impact.events_count)
    related_mid.metric("Members", impact.project_members_count)
    related_right.metric("Delays", impact.delays_count)

    links_left, links_mid, links_right = st.columns(3)
    links_left.metric("Phase Links", impact.phase_predecessor_links_count)
    links_mid.metric("Task Links", impact.task_predecessor_links_count)
    links_right.metric("Settings / Metadata", impact.project_settings_count + impact.project_metadata_count)

    if not signals_enabled():
        signals_left, signals_mid, signals_right = st.columns(3)
        signals_left.metric("Data Sources", impact.data_sources_count)
        signals_mid.metric("Signal Definitions", impact.signal_definitions_count)
        signals_right.metric("Observations", impact.signal_observations_count)

        extra_left, extra_mid, extra_right = st.columns(3)
        extra_left.metric("Ingestion Runs", impact.ingestion_runs_count)
        extra_mid.metric("Shift Definitions", impact.shift_definitions_count)
        extra_right.metric("Shift Assignments", impact.shift_assignments_count)
        return

    extra_left, extra_mid, extra_right = st.columns(3)
    extra_left.metric("Shift Definitions", impact.shift_definitions_count)
    extra_mid.metric("Shift Assignments", impact.shift_assignments_count)
    extra_right.metric("Metadata", impact.project_metadata_count)


def _reset_deleted_project_state() -> None:
    st.session_state.session.project = None
    st.session_state["selected_project_id"] = None
    st.session_state["project_access"] = ProjectAccess()
    st.session_state["plan_state"] = PlanState()
    st.session_state.pop("reline_metadata", None)


@st.dialog("Delete Project", width="large")
def render_project_delete_dialog(*, session: SessionModel, impact: ProjectDeleteImpact) -> None:
    if not project_can_delete():
        st.info("Project deletion is unavailable for your current role.")
        return

    st.error(
        ":material/warning: This is a HARD DELETE. The project and its related records will be permanently removed.",
    )
    st.caption("Review the impact carefully before continuing. This action cannot be undone.")

    with st.container(border=True):
        st.subheader(impact.project_name)
        st.caption(f"Project ID: `{impact.project_id}`")
        _render_impact_metrics(impact)

    st.write("Delete impact")
    impact_caption = (
        "Deleting this project may remove phases, tasks, links, events, members, settings, metadata, shifts, delays, "
        "and signal records tied to it."
        if not signals_enabled()
        else "Deleting this project may remove phases, tasks, links, events, members, settings, metadata, shifts, and delays tied to it."
    )
    st.caption(impact_caption)

    with st.container(border=True):
        st.write("Todo handling")
        delete_todos = st.checkbox(
            f"Also delete the {impact.todos_count} associated todos",
            value=impact.todos_count > 0,
            disabled=impact.todos_count == 0,
            help=(
                "This includes both project-level todos and todos linked to tasks in this project."
                if impact.todos_count > 0
                else "There are no associated todos for this project."
            ),
        )
        todo_left, todo_right = st.columns(2)
        todo_left.metric("Direct Todos", impact.todos_direct_count)
        todo_right.metric("Task-linked Todos", impact.todos_task_linked_count)

    st.write("Final confirmation")
    hard_delete_ack = st.checkbox(
        "I understand this permanently deletes the project and cannot be undone.",
        value=False,
    )
    typed_name = st.text_input(
        "Type the exact project name to enable deletion",
        placeholder=impact.project_name,
    )
    confirm_enabled = hard_delete_ack and typed_name.strip() == impact.project_name

    left, spacer, right = st.columns([1, 2, 1])
    cancel = left.button(
        ":material/cancel: Cancel",
        type="secondary",
        use_container_width=True,
    )
    confirm = right.button(
        ":material/delete_forever: Confirm Delete",
        type="primary",
        disabled=not confirm_enabled,
        use_container_width=True,
    )

    if cancel:
        st.rerun()

    if not confirm:
        return

    try:
        delete_project(
            headers=st.session_state.get("auth_headers", {}),
            project_id=impact.project_id,
            delete_todos=delete_todos,
        )
    except Exception as exc:
        st.error("Project deletion was rejected. Your role may no longer allow deletes, or the backend blocked the request.")
        st.caption(str(exc))
        return

    st.cache_data.clear()
    fetch_attention_tasks.clear()
    _reset_deleted_project_state()
    st.success(":material/check: Project deleted successfully.")
    sleep(1)
    st.switch_page("pages/projects.py")


def render_project_delete_action(session: SessionModel) -> None:
    project = session.project
    delete_disabled = not project_can_delete()

    delete_button = st.button(
        label=":material/delete: Delete Project",
        help=(
            "Review the permanent delete impact for this project."
            if not delete_disabled
            else "Your current project role does not allow deletion."
        ),
        type="primary",
        disabled=delete_disabled,
    )

    if not delete_button:
        return

    try:
        impact = get_project_delete_impact(
            headers=st.session_state.get("auth_headers", {}),
            project_id=project.uuid,
        )
    except Exception as exc:
        st.error(f"Error loading delete impact: {exc}")
        return

    render_project_delete_dialog(session=session, impact=impact)
