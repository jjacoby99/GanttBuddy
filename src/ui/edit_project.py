import streamlit as st

from models.session import SessionModel
from models.project import Project
from models.phase import Phase
from models.task import Task

@st.dialog("Edit Project")
def render_edit_project(session: SessionModel):

    project = session.project

    new_name = st.text_input("Project Name", value=project.name)

    if st.button("Save Changes"):
        project.name = new_name
        st.success("Project updated.")
        st.session_state.ui.show_rename_project = False
        st.rerun()