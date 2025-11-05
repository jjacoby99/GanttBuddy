import streamlit as st
import os
from models.project import Project
from ui.add_phase import render_add_phase
from ui.edit_phase import render_phase_edit
from ui.add_task import render_task_add
from ui.edit_task import render_task_edit
from logic.load_project import ProjectLoader, ExcelProjectLoader, ExcelParameters, DataColumn

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

@st.dialog("Import from Excel")
def load_from_excel(session) -> Project:
    file = st.file_uploader(
        label="Select an Excel file",
        type=["xls", "xlsx"],
        help="Select a BTA Excel template file to import project data from"
    )

    if not file:
        return # user has not uploaded a file yet

    params = ExcelParameters(
        columns=[
            DataColumn(name="ACTIVITY", column=2),
            DataColumn(name="PLANNED DURATION (HOURS)", column=3),
            DataColumn(name="PLANNED START", column=4),
            DataColumn(name="PLANNED END", column=5),
            DataColumn(name="ACTUAL DURATION", column=7),
            DataColumn(name="ACTUAL START", column=8),
            DataColumn(name="ACTUAL END", column=9),
            DataColumn(name="NOTES", column=10),
            DataColumn(name="PREDECESSOR", column=11),
            DataColumn(name="UUID", column=12),
        ]
    )

    try:
        session.project = ExcelProjectLoader.load_excel_project(file, params)
    except (FileNotFoundError, ValueError) as e:
        st.error(str(e))
        return
    st.success(f"Project '{session.project.name}' imported from Excel.")
    st.rerun()
    


def render_project_sidebar(session) -> Project:
    if st.button(f"Create Project", help="Create a new project from scratch"):
        create_project(session)
        return
    
    if st.button(f"Load Project", help="Load an existing project"):
        load_project(session)
        return
    
    if st.button(f"Import from Excel", help="Import project data from a BTA Excel template"):
        load_from_excel(session)
        return
    

def render_project_buttons(session):
    if not session.project:
        return
    
    st.divider()
    st.caption(f"Plan your project")
    add_phase, add_task = st.columns(2)
    with add_phase:
        if st.button(":material/add_circle: Phase", 
                     key="add_phase", 
                     help=f"Add a phase to {session.project.name}"):
            render_add_phase(session)
            st.session_state.ui.show_add_phase = False

    with add_task:
        if st.button(":material/add_circle: Task", 
                     key="add_task", 
                     help=f"Add a task to {session.project.name}",
                     disabled= False if session.project.phases else True):
            render_task_add(session)
            st.session_state.ui.show_add_task = False
    
    

        