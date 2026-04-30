import time
from pathlib import Path

import streamlit as st
from PIL import Image

from logic.backend.api_client import fetch_project_summary_by_id, save_project
from logic.backend.project_permissions import current_project_access, project_is_read_only, read_only_project_message
from ui.compact_buttons import use_compact_buttons
from ui.edit_project import render_edit_project
from ui.settings_view import render_settings_view


@st.cache_data
def load_image(path: str):
    return Image.open(path)


def _current_import_overwrite_warning() -> dict | None:
    warning = st.session_state.get("import_overwrite_warning")
    project = getattr(st.session_state.session, "project", None)
    if not warning or project is None:
        return None
    if warning.get("project_id") != getattr(project, "uuid", None):
        return None
    return warning


def _render_save_overwrite_guard() -> bool:
    warning = _current_import_overwrite_warning()
    if warning is None:
        return True

    project_id = warning.get("project_id")
    imported_name = warning.get("imported_project_name") or st.session_state.session.project.name
    existing_name = warning.get("existing_project_name")

    headers = st.session_state.get("auth_headers")
    if headers and project_id:
        try:
            existing_project = fetch_project_summary_by_id(headers=headers, project_id=project_id, include_closed=True)
            if existing_project is not None:
                existing_name = existing_project.name
                warning["existing_project_name"] = existing_name
        except Exception:
            pass

    st.warning(
        f"You imported this workbook with existing project id `{project_id}`. Saving now will update "
        f"`{existing_name or imported_name}` rather than creating a separate project."
    )
    if existing_name and imported_name and existing_name.strip() != imported_name.strip():
        st.caption(
            f"Current in-app project name: `{imported_name}`. Existing backend project: `{existing_name}`."
        )

    return st.checkbox(
        "I want to save over the existing backend project tied to this imported workbook ID.",
        key=f"save_overwrite_ack_{project_id}",
    )


def render_workspace_buttons():
    use_compact_buttons()

    ui = st.session_state.ui

    if st.session_state.session.project is None:
        with st.container(horizontal_alignment="center"):
            st.info("Create or load a project to view.", icon=":material/info:", width=270)
            path = Path(__file__).parent.parent.parent.resolve() / "assets" / "ganttbuddy.png"
            st.space("large")
            st.image(load_image(path))
            st.stop()

    project_access = current_project_access()
    read_only = project_is_read_only()

    with st.container(horizontal=True):
        st.title(st.session_state.session.project.name)
        st.space("stretch")

        if st.button("Edit Project", icon=":material/edit:", disabled=read_only):
            ui.show_edit_project = True

    if read_only:
        st.info(read_only_project_message(), icon=":material/visibility:")

    if ui.show_edit_project:
        render_edit_project(st.session_state.session)
        ui.show_edit_project = False

    overwrite_save_acknowledged = _render_save_overwrite_guard()

    with st.container(horizontal=True):
        if st.button(
            "Save",
            icon=":material/save:",
            help="Save project to the server." if project_access.can_edit else "Read-only access: saving is disabled.",
            disabled=not project_access.can_edit,
        ):
            if not overwrite_save_acknowledged:
                st.error("Confirm the overwrite warning before saving this imported project.")
                return
            try:
                save_project(st.session_state.session.project, headers=st.session_state.get("auth_headers"))
                st.session_state.pop("import_overwrite_warning", None)
                success = st.success(":material/check: Project saved to server.", width=210)
                time.sleep(3)
                success.empty()
            except Exception as e:
                st.error(f"Failed to save project to server: {e}")

        st.space("stretch")
        if st.button(
            "Settings",
            icon=":material/settings:",
            help=(
                "View or edit settings: work days, hours, holidays, and more."
                if project_access.can_edit
                else "Read-only access: project settings are locked."
            ),
            disabled=not project_access.can_edit,
        ):
            st.session_state.ui.show_settings = True

    if st.session_state.ui.show_settings:
        render_settings_view(st.session_state.session)
        st.session_state.ui.show_settings = False
