import streamlit as st

from models.session import SessionModel
from models.project import Project
from models.phase import Phase
from models.task import Task

from models.project_type import ProjectType
from logic.backend.project_permissions import project_is_read_only

@st.dialog("Edit Project")
def render_edit_project(session: SessionModel):
    if project_is_read_only():
        st.info("This project is read-only, so project details cannot be changed right now.")
        return

    project = session.project

    new_name = st.text_input("Name", value=project.name)

    description = st.text_area("Description", value=project.description)

    type = st.pills(
        label="Specify Project Type",
        options=list(ProjectType),
        format_func=lambda s: s.name.replace("_"," ").capitalize()
    )

    if st.button("Save Changes", disabled=project_is_read_only()):
        project.name = new_name
        project.description = description
        project.project_type = type
        st.success("Project updated.")
        st.session_state.ui.show_rename_project = False
        st.rerun()
