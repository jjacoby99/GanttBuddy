import streamlit as st
import os
from models.project import Project
from ui.add_phase import render_add_phase
from ui.edit_phase import render_phase_edit
from ui.add_task import render_task_add
from ui.edit_task import render_task_edit
from logic.load_project import ProjectLoader

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
        phases=[]
    )

    if st.button("Create Project"):
        session.project = new_project
        st.info(f"✅ New project created!")
        st.rerun()
        return

@st.dialog("Load a project")
def load_project(session) -> Project:
    projects = os.listdir(os.path.join(os.getcwd(), "projects"))
    if not projects:
        st.info("No saved projects found. Create a new project to get started.")
        st.stop()

    file = st.selectbox(
        label="Select a saved project",
        options=projects,
        help="Select a previously saved project to load",
        format_func=lambda x: x.replace(".json", "")
    )

    if st.button("Load Project"):
        file_path = os.path.join(os.getcwd(), "projects", file)
        try:
            proj_dict = ProjectLoader.load_json_file(file_path)
            project = ProjectLoader.load_project(proj_dict)
            session.project = project
            st.success(f"Project '{project.name}' loaded.")
        except (FileNotFoundError, ValueError) as e:
            st.error(str(e))
            return

def render_project_sidebar(session) -> Project:
    if st.button(f"Create Project", help="Create a new project from scratch"):
        create_project(session)
        return
    
    if st.button(f"Load Project", help="Load an existing project"):
        load_project(session)
        return
    

def render_project_buttons(session):
    if not session.project:
        return
    
    st.divider()
    st.caption(f"Plan your project")
    add_phase, add_task = st.columns(2)
    with add_phase:
        if st.button("➕ Phase", 
                     key="add_phase", 
                     help=f"Add a phase to {session.project.name}"):
            render_add_phase(session)
            st.session_state.ui.show_add_phase = False

    with add_task:
        if st.button("➕ Task", 
                     key="add_task", 
                     help=f"Add a task to {session.project.name}",
                     disabled= False if session.project.phases else True):
            render_task_add(session)
            st.session_state.ui.show_add_task = False
    
    

        