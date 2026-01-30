import streamlit as st
from models.project import Project

@st.dialog(":material/add: Create a project")
def create_project():
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
    )

    if st.button("Create", icon=":material/add:", type='primary'):
        st.session_state.session.project = new_project
        st.info(f"✅ New project created!")
        st.rerun()
        return