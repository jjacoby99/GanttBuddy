import streamlit as st
from lib.project import Project

@st.dialog("Create a project")
def create_project(session):
    project_name = st.text_input(
        f"Project name",
        placeholder="Super aweseome project"
    )

    if not project_name:
        st.info("Enter a valid name for your project.")
        st.stop()

    project_description = None
    if st.checkbox(f"Add project description?"):
        project_description = st.text_input(
            label=f"Describe your project. This may be useful to recall later",
            placeholder="Constructing the death star..."
        )

    new_project = Project(
        name=project_name,
        description=project_description,
        tasks=[]
    )

    if st.button("Create Project"):
        session.project = new_project
        st.info(f"✅ New project created!")
        st.rerun()
        return

def load_project(session) -> Project:
    pass

def render_sidebar(session) -> Project:
    if st.button(f"Create Project", help="Create a new project from scratch"):
        create_project(session)
        return
    
    if st.button(f"Load Project", help="Load an existing project"):
        load_project(session)
        return