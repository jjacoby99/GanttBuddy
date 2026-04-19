import streamlit as st

from models.session import SessionModel
from models.project import Project
from models.phase import Phase
from models.task import Task

from models.project_type import ProjectType

@st.dialog("Edit Project")
def render_edit_project(session: SessionModel):

    project = session.project

    new_name = st.text_input("Name", value=project.name)

    description = st.text_area("Description", value=project.description)

    type = st.pills(
        label="Specify Project Type",
        options=list(ProjectType),
        format_func=lambda s: s.name.replace("_"," ").capitalize()
    )

    if st.button("Save Changes"):
        project.name = new_name
        project.description = description
        project.project_type = type
        st.success("Project updated.")
        st.session_state.ui.show_rename_project = False
        st.rerun()