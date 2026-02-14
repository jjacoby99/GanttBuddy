import streamlit as st
from io import BytesIO

import datetime as dt

from models.project import Project
from models.project_type import ProjectType

from ui.add_phase import render_add_phase
from ui.edit_phase import render_phase_edit
from ui.add_task import render_task_add
from ui.edit_task import render_task_edit
from ui.project_metadata import render_reline_metadata_form

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

    st.caption("Edit")
    with st.container(horizontal=True):
        if session.project.project_type == ProjectType.MILL_RELINE:
            edit_reline_info = st.button(
                label=":material/tune: Reline Info", 
                help="Specify reline information", 
                key="edit_reline_metadata"
            )
            
            if edit_reline_info:
                existing = st.session_state.get("reline_metadata", None)
                render_reline_metadata_form(existing)

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
            

    
    

        