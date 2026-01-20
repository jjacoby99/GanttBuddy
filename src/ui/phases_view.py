import streamlit as st

from models.session import SessionModel

from ui.utils.project_info import render_project_info

# @st.cache_data: throws Unhashable Error for SessionModel
def render_phases_view(session: SessionModel):
    
    phases = session.project.phases
    if not phases:
        st.info("Add phases to your project to see the phases view.")
        return
    
    
    st.caption("Project at a glance")
    with st.container(border=True):
        render_project_info(session.project, resolution="Phase")
    
    st.divider()

    st.subheader("Project Phases Overview")
    
    
    phase_df = session.project.get_phase_df()
    phase_df = phase_df[["phase", "planned_start", "planned_end", "planned_duration", "num_tasks"]]
    phase_df.columns = ["Phase", "Planned Start", "Planned End", "Planned Duration (hrs)", "Number of Tasks"]
    st.data_editor(phase_df)