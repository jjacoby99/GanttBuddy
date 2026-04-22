import streamlit as st
from io import BytesIO

import datetime as dt

from models.project import Project
from models.project_type import ProjectType
from models.plan_state import PlanState
from logic.backend.project_permissions import project_is_read_only


from ui.add_phase import render_add_phase
from ui.edit_phase import render_phase_edit
from ui.add_task import render_task_add
from ui.edit_task import render_task_edit
from ui.project_metadata import render_reline_metadata_form


def render_add_buttons(session):
    plan_state = st.session_state.get("plan_state", None)
    read_only = project_is_read_only()

    with st.container(horizontal=True):
        if st.button(":material/add_circle: Task", 
                     key="add_task", 
                     help=f"Add a task to {session.project.name}",
                     disabled=read_only or not session.project.phases,
                     type="primary",
                     ):
            render_task_add(session)
            st.session_state.ui.show_add_task = False
        
        st.space("stretch")
        if st.button(":material/add_circle: Phase", 
                     key="add_phase", 
                     help=f"Add a phase to {session.project.name}",
                     type="primary",
                     disabled=read_only,
                     ):
            render_add_phase(session, plan_state=plan_state)
            st.session_state.ui.show_add_phase = False
       

def render_project_buttons(session):
    if session.project is None:
        return
    read_only = project_is_read_only()
    
    st.divider()
    st.subheader("Build")
    st.caption(f"Plan")
    plan_state = st.session_state.get("plan_state", None)

    render_add_buttons(session)

    st.caption("Edit")
    with st.container(horizontal=True):
        if session.project.project_type == ProjectType.MILL_RELINE:
            edit_reline_info = st.button(
                label=":material/tune: Reline Info", 
                help="Specify reline information", 
                key="edit_reline_metadata",
                disabled=read_only,
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
