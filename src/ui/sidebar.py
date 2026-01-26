import streamlit as st
from io import BytesIO

from models.project import Project
from ui.add_phase import render_add_phase
from ui.edit_phase import render_phase_edit
from ui.add_task import render_task_add
from ui.edit_task import render_task_edit
from ui.template_view import load_from_template
from logic.load_project import ProjectLoader, ExcelProjectLoader, ExcelParameters, DataColumn

from logic.backend.project_list import get_projects
from logic.backend.import_project import snapshot_to_project
from logic.backend.api_client import fetch_project_snapshot

from ui.compact_buttons import use_compact_buttons




@st.dialog(":material/add: Create a project")
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

    if st.button("Create", icon=":material/add:", type='primary'):
        session.project = new_project
        st.info(f"✅ New project created!")
        st.rerun()
        return


@st.dialog(":material/table_view: Import from Excel")
def load_from_excel(session) -> Project:

    st.caption("Import project schedule directly from a BTA Consulting template.")

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
    
@st.dialog(f":material/open_in_browser: Load Saved Project")
def render_load_project(session) -> Project:
    try:
        projects = get_projects(st.session_state.auth_headers)
    except Exception as e:
        st.error(f"Error fetching saved projects: {e}")
        st.stop()
    
    load_proj = False
    with st.form("load_project"):
        selected_project_id = st.selectbox(
            label="Project",
            options=[pid for pid in projects.keys()],
            format_func=lambda pid: projects[pid],
            help="Select a saved project to load."
        )

        if st.form_submit_button(f":material/open_in_browser: Load"):
            load_proj = True
    
    if not load_proj:
        st.stop()

    try:
        proj_snapshot = fetch_project_snapshot(
            project_id=selected_project_id,
            headers=st.session_state.auth_headers
        )
    except Exception as e:
        st.error(f"Error loading project *{projects[selected_project_id]}*")
        st.stop()
    
    session.project = snapshot_to_project(proj_snapshot)
    st.success(f"*{projects[selected_project_id]}* Loaded Successfully!")
    st.rerun()


def render_project_sidebar(session) -> Project:

    st.divider()
    st.subheader(f"Project Explorer")

    st.caption(f"Create")
    if st.button(f"New Project", icon=":material/add:",help="Create a new project from scratch", type="secondary"):
        create_project(session)
        return
    
    if st.button(f"From Template", icon=":material/dashboard_customize:",help="Create a new project from a predefined template", type="secondary"):
        load_from_template(session)
        return

    st.caption(f"Open")
    if st.button(f"Saved Project", icon=":material/open_in_browser:", help="Load a saved project from the cloud", type="secondary"):
        render_load_project(session)
        return

    if st.button(f"From Excel", icon=":material/table_view:", help="Import project data from a BTA Excel template", type="secondary"):
        load_from_excel(session)
        return
    

def render_project_buttons(session):
    if session.project is None:
        return
    
    st.divider()
    st.subheader("Build")
    st.caption(f"Plan")
    with st.container(horizontal=True):
        if st.button(":material/add_circle: Phase", 
                     key="add_phase", 
                     help=f"Add a phase to {session.project.name}"):
            render_add_phase(session)
            st.session_state.ui.show_add_phase = False
                
        if st.button(":material/add_circle: Task", 
                     key="add_task", 
                     help=f"Add a task to {session.project.name}",
                     disabled= False if session.project.phases else True):
            render_task_add(session)
            st.session_state.ui.show_add_task = False


    st.caption(f"Export")
    with st.container(horizontal=True):
        prepare_download = st.toggle(
            label="Prepare Excel",
            help="Prepare an Excel schedule for download.",
        )
        
        if prepare_download:
            from logic.write_project import ExcelProject, ExcelFormat
            with st.spinner("Preparing Excel Export..."):
                writer = ExcelProject(
                    project=session.project, 
                    excel_format=ExcelFormat()
                )
                wb = writer.write_project()
                buffer = BytesIO()
                wb.save(buffer)
                buffer.seek(0)
                if st.download_button(
                    ":material/file_download: Excel",
                    data=buffer,
                    file_name=f"{session.project.name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ):
                    st.success(f"BTA Excel Schedule Successfully Exported!")
            

    
    

        